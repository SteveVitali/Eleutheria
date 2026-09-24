# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `government_mandated_disclosure` connector — municipal surveillance-ordinance
(CCOPS) disclosures (§22.6 H3, SIG-INGEST-049*, P24.7 / CCOPS.1 / GL-CCOPS-01).

This is the one genuinely-missing connector class the P17-FLIP-01 deferral recorded:
municipal surveillance-ordinance disclosures are **their own source class** —
``government_mandated_disclosure`` (licence: public record, format: pdf, extraction:
document_pipeline) — distinct from both ``civil_society_dataset`` and
``vendor_portal`` (SIG-INGEST-049). The class is scoped **depth, not breadth**
(SIG-INGEST-049a): ~26 jurisdictions ≈ 5% of the US population and ~0.14% of US
law-enforcement agencies; zero machine-readable outputs; the canonical national list
is a JPEG on the ACLU page. Its highest use is **calibration, not coverage**
(SIG-INGEST-049d) — these jurisdictions are the only places SIG can check an inferred
picture against a legally compelled disclosure.

**ADR-080 — one connector, three paying source adapters** (SIG-INGEST-049c): the
city with quarterly reporting and the richest per-technology detail (Seattle — the
fixed 50-field SIR questionnaire), the city publishing 42 policies on a stable URL
pattern (NYC POST Act), and the city with a biannual citywide inventory carrying a
compliance metric (SF Chapter 19B). One connector class whose ``extract`` dispatches
to a per-document-``kind`` extractor — the same one-connector-three-extractors
reasoning as ADR-071 — because all three share the claim-shaping, the aggregate
schema gate, and the epistemic guard.

**Per-agency AGGREGATE rows only (Part VIII).** Every emitted claim is keyed to a
per-agency subject (``ccops:<jurisdiction>:<agency>``) and carries ``agency`` +
``reporting_period`` (+ ``technology`` for every non-ordinance claim). Person-level
or non-aggregate CCOPS data is FORBIDDEN: :func:`assert_aggregate_row` is the
schema gate that proves it — a row missing an aggregate field, or carrying any
plate / person / per-search / officer column or token, is a hard error
(§0.7/§43.2, RISK-P0-08).

**``procured ≠ deployed`` — modelled honestly (RISK-P21-16 applied to this class).**
A disclosure *authorizing* or *procuring* a system is not evidence it is deployed.
The mechanical form is two-layered, as in the pathways connector:

* **predicate level** — the use predicates (``in_use``, ``usage_count``,
  ``complaint_count``, ``deployment_location``, ``effectiveness_claim``) may ride
  ONLY on a ``disclosure_use`` claim (:func:`assert_use_predicate_has_use_claim`).
* **document level** — a ``disclosure_use`` / ``compliance_finding`` claim is
  admissible only where the disclosure **itself reports actual use**: a
  deployment-genre document unconditionally, or a mandated disclosure carrying
  ``reports_actual_use`` (e.g. SF's biannual inventory, whose own rows mark
  technologies "in use without an approved policy"). A procurement-record or
  vendor-disclosure genre can NEVER evidence use, however labelled
  (:func:`assert_claim_type_supported`). The genre is **re-derived from the
  document text** (:func:`parsing.genre.classify_genre`), never trusted from a
  fixture label — a procurement document cannot be relabelled into use evidence.

Within a use-reporting disclosure the distinction is **row-level**: an
``approved_policy`` / ``seeking_procurement_or_pilot`` status yields an
``inventory_entry`` claim and nothing more; only a status in
``in_use_statuses`` yields ``in_use``.

**Mandated ≠ populated.** A mandated questionnaire field is ``answered``,
``present_but_empty`` (the row exists but the city left it blank — Seattle's
unfilled Fiscal 1.1/1.2 tables), or ``absent`` — three distinct recorded states,
never conflated with an answer and never fabricated into a value
(:func:`field_state_of`).

**The non-compliance finding (SIG-INGEST-049e).** A mandated disclosure that
reports technologies in use *without* the policy the ordinance requires is a
finding class available nowhere else; it lands as a ``compliance_finding`` claim
carrying the disclosure's own metric (SF: 37 technologies / 26%).

The three sources stay ``ingestion_permitted=false`` / rights ``UNDETERMINED``
until a rights packet + operator flip (HG-03/HG-04): a ``run --mode live`` against
any of them REFUSES at the loader gate (exit 3); ``replay``/``shadow`` run over
committed fixtures with no network (SIG-INGEST-018/019).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from parsing.clauses import clause_claim, find_clause, locate_clauses
from parsing.genre import DEPLOYMENT_GENRES, DocumentGenre, classify_genre

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

__all__ = [
    "CCOPS_CONNECTOR",
    "USE_CLAIM_TYPES",
    "ClaimTypeNotPermitted",
    "DeploymentInferenceError",
    "DocumentContext",
    "GovernmentMandatedDisclosureConnector",
    "NonAggregateRow",
    "PartVIIIViolation",
    "PersonNamingRefused",
    "PredicateNotAllowed",
    "aggregate_level",
    "assert_aggregate_row",
    "assert_claim_type_supported",
    "assert_predicate_allowed",
    "assert_use_predicate_has_use_claim",
    "claim_types",
    "deployment_genres",
    "deployment_predicates",
    "disclosure_claim",
    "extract_documents",
    "field_state_of",
    "field_states",
    "genre_claim_types",
    "in_use_statuses",
    "never_use_genres",
    "parse_disclosure",
    "predicate_allowlist",
    "scope",
    "source_class",
    "source_id_for",
    "vocab",
    "vocab_version",
]

CCOPS_CONNECTOR = "government_mandated_disclosure"

#: The claim types that assert actual use / a use-derived finding — admissible
#: only where the disclosure itself reports use (see assert_claim_type_supported).
USE_CLAIM_TYPES: frozenset[str] = frozenset({"disclosure_use", "compliance_finding"})


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned connector vocabulary (``data/government_mandated_disclosure_vocab.toml``)."""
    return load_table("government_mandated_disclosure_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def claim_types() -> frozenset[str]:
    """The five claim types this connector may emit (SIG-INGEST-049*)."""
    return frozenset(vocab()["claim_types"])


def deployment_genres() -> frozenset[DocumentGenre]:
    """The genres from which a use claim may be asserted unconditionally."""
    return frozenset(DocumentGenre(g) for g in vocab()["deployment_genres"])


def never_use_genres() -> frozenset[DocumentGenre]:
    """The genres that can NEVER evidence actual use (procurement / vendor docs)."""
    return frozenset(DocumentGenre(g) for g in vocab()["never_use_genres"])


def deployment_predicates() -> frozenset[str]:
    """The predicates that may ride ONLY on a ``disclosure_use`` claim."""
    return frozenset(vocab()["deployment_predicates"])


def genre_claim_types() -> dict[DocumentGenre, frozenset[str]]:
    """The genre → permitted-claim-types gate (the mechanical epistemic form)."""
    return {
        DocumentGenre(genre): frozenset(types)
        for genre, types in vocab()["genre_claim_types"].items()
    }


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (SIG-INGEST-033, SIG-INGEST-049b)."""
    return frozenset(vocab()["predicate_allowlist"])


def in_use_statuses() -> frozenset[str]:
    """The inventory statuses that disclose actual use (every other status is authorization)."""
    return frozenset(str(s) for s in vocab()["in_use_statuses"])


def field_states() -> frozenset[str]:
    """The mandated != populated vocabulary: answered / present_but_empty / absent."""
    return frozenset(str(s) for s in vocab()["field_states"])


def aggregate_level() -> str:
    """The aggregate granularity stamped on every emitted row (Part VIII)."""
    return str(vocab()["aggregate"]["aggregate_level"])


def aggregate_required_fields() -> frozenset[str]:
    """The fields every emitted claim must carry to be a per-agency aggregate row."""
    return frozenset(str(f) for f in vocab()["aggregate"]["required_fields"])


def technology_exempt_claim_types() -> frozenset[str]:
    """The claim types exempt from the `technology` requirement (jurisdiction-scoped)."""
    return frozenset(str(t) for t in vocab()["aggregate"]["technology_exempt_claim_types"])


def forbidden_output_columns() -> frozenset[str]:
    """Column names/substrings that MUST NEVER appear on an emitted row (Part VIII)."""
    return frozenset(str(c).lower() for c in vocab()["aggregate"]["forbidden_output_columns"])


def forbidden_tokens() -> tuple[str, ...]:
    """Content tokens refused in a predicate id or raw value (§0.7/§43.2, RISK-P0-08)."""
    return tuple(str(t).lower() for t in vocab()["aggregate"]["forbidden_tokens"])


def person_naming_predicates() -> frozenset[str]:
    """Predicates that name a natural person — refused outright (§43.4 default)."""
    return frozenset(str(p) for p in vocab()["aggregate"]["person_naming_predicates"])


def source_class() -> Mapping[str, Any]:
    """The SIG-INGEST-049 source-class registration row."""
    return vocab()["source_class"]


def scope() -> Mapping[str, Any]:
    """The SIG-INGEST-049a depth-not-breadth scope numbers, carried honestly."""
    return vocab()["scope"]


def source_id_for(source_key: str) -> str:
    """The registry source id a paying source adapter draws its fixtures from (HG-03)."""
    return str(vocab()["sources"][source_key])


def disclosure_sources() -> frozenset[str]:
    """Every registry source id in the government_mandated_disclosure class."""
    return frozenset(str(s) for s in vocab()["sources"].values())


# --- the schema gates ---------------------------------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


class ClaimTypeNotPermitted(Exception):
    """Raised when a document's genre does not permit a claim type (the genre gate)."""


class DeploymentInferenceError(Exception):
    """Raised when a use claim is asserted from a disclosure reporting no actual use.

    The mechanical form of the epistemic rule for this class: a disclosure
    *authorizing* or *procuring* a system is not evidence it is deployed — a
    ``disclosure_use`` claim requires a document that itself reports use, and a
    procurement-record / vendor-disclosure genre can NEVER report use.
    """


class NonAggregateRow(Exception):
    """A schema error: an emitted row is not a per-agency aggregate row (Part VIII)."""


class PartVIIIViolation(Exception):
    """Raised when a row carries plate / per-person / per-search content (§0.7/§43.2)."""


class PersonNamingRefused(PartVIIIViolation):
    """Raised when a predicate names a natural person (§43.4 default no-publish)."""


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`."""
    if predicate not in predicate_allowlist():
        raise PredicateNotAllowed(
            f"the {CCOPS_CONNECTOR} connector may write only {sorted(predicate_allowlist())} "
            f"(SIG-INGEST-033/049b); {predicate!r} is outside the allowlist."
        )
    return predicate


def assert_claim_type_supported(
    claim_type: str, genre: DocumentGenre, *, reports_actual_use: bool = False
) -> None:
    """Reject a claim type a disclosure of this nature cannot support.

    The document-level epistemic guard. A ``disclosure_use`` / ``compliance_finding``
    claim is admissible only where the disclosure **itself reports actual use**: a
    deployment-genre document unconditionally, or a mandated disclosure carrying
    ``reports_actual_use``. A procurement-record or vendor-disclosure genre can
    NEVER evidence use — that is the procured→deployed over-inference, refused
    (:class:`DeploymentInferenceError`). Any other genre/claim-type mismatch raises
    :class:`ClaimTypeNotPermitted`.
    """
    if claim_type not in claim_types():
        raise ClaimTypeNotPermitted(
            f"{claim_type!r} is not a {CCOPS_CONNECTOR} claim type; must be one of "
            f"{sorted(claim_types())} (SIG-INGEST-049)."
        )
    if claim_type in USE_CLAIM_TYPES:
        if genre in never_use_genres():
            raise DeploymentInferenceError(
                f"a {genre.value!r} document can NEVER evidence actual use; a "
                f"{claim_type!r} claim from it is the procured→deployed over-inference "
                "this class refuses (RISK-P21-16, Part VIII)."
            )
        if genre in DEPLOYMENT_GENRES or reports_actual_use:
            return
        raise DeploymentInferenceError(
            f"a {claim_type!r} claim requires a disclosure that itself reports actual "
            f"use (a deployment-genre document, or a mandated inventory carrying "
            f"reports_actual_use); this {genre.value!r} document reports none — "
            "authorizing/procuring a system is not evidence it is deployed."
        )
    permitted = genre_claim_types().get(genre, frozenset())
    if claim_type not in permitted:
        raise ClaimTypeNotPermitted(
            f"a {genre.value!r} document may not assert a {claim_type!r} claim "
            f"(permitted: {sorted(permitted)}) — SIG-INGEST-049*."
        )


def assert_use_predicate_has_use_claim(predicate: str, claim_type: str) -> None:
    """Reject a use predicate carried by a non-use claim (the predicate-level guard).

    ``in_use`` / ``usage_count`` / ``complaint_count`` / ``deployment_location`` /
    ``effectiveness_claim`` may ride ONLY on a ``disclosure_use`` claim, so a
    disclosure or inventory claim can never smuggle a deployment fact.
    """
    if predicate in deployment_predicates() and claim_type != "disclosure_use":
        raise DeploymentInferenceError(
            f"predicate {predicate!r} is an actual-use fact; it may ride only on a "
            f"'disclosure_use' claim, not a {claim_type!r} claim — procured NEVER "
            "implies deployed (RISK-P21-16, Part VIII)."
        )


def _person_naming_check(predicate: str) -> None:
    if predicate in person_naming_predicates():
        raise PersonNamingRefused(
            f"predicate {predicate!r} names a natural person; the connector emits "
            "per-agency aggregate facts ONLY and refuses person-named claims outright "
            "(§43.4 default no-publish, Part VIII §0.7)."
        )


def _offending_token(text: str) -> str | None:
    lowered = str(text).lower()
    for token in forbidden_tokens():
        if token in lowered:
            return token
    return None


def assert_aggregate_row(row: Mapping[str, Any]) -> None:
    """Assert an emitted row is a per-agency AGGREGATE row (Part VIII, §18.1-analogue).

    The schema gate that makes "per-agency aggregate rows only" mechanical rather
    than a policy note: the row must carry every required aggregate field
    (``agency`` + ``reporting_period``, plus ``technology`` for every
    non-``ordinance`` claim); no key may collide with the forbidden person-level /
    non-aggregate columns; and neither the predicate id nor the verbatim raw value
    may carry a Part VIII forbidden token. Person-naming predicates are refused.
    """
    _person_naming_check(str(row.get("predicate_id", "")))
    missing = [f for f in sorted(aggregate_required_fields()) if not row.get(f)]
    if missing:
        raise NonAggregateRow(
            f"row {row.get('predicate_id', '?')!r} lacks the required per-agency "
            f"aggregate field(s) {missing}; every {CCOPS_CONNECTOR} claim is a "
            "per-agency aggregate row (Part VIII — person-level or non-aggregate "
            "CCOPS data is FORBIDDEN)."
        )
    if row.get("claim_type") not in technology_exempt_claim_types() and not row.get("technology"):
        raise NonAggregateRow(
            f"{row.get('claim_type')!r} claim {row.get('predicate_id', '?')!r} lacks "
            "the required `technology` aggregate field (Part VIII)."
        )
    banned = forbidden_output_columns()
    for key in row:
        k = str(key).lower()
        if k in banned or any(b in k for b in banned):
            raise NonAggregateRow(
                f"row {row.get('predicate_id', '?')!r} carries forbidden "
                f"person-level/non-aggregate column {key!r} (Part VIII); "
                "per-agency aggregate rows only."
            )
    for field_name, text in (
        ("predicate", str(row.get("predicate_id", ""))),
        ("raw_value", str(row.get("raw_value", ""))),
    ):
        token = _offending_token(text)
        if token is not None:
            raise PartVIIIViolation(
                f"{field_name} {text!r} matches the forbidden Part VIII token "
                f"{token!r}; the connector emits institutional aggregate facts ONLY — "
                "no plate / per-trip / per-person / per-search data is ever stored "
                "(§0.7, §43.2, RISK-P0-08)."
            )


def assert_no_forbidden_output(rows: Iterable[Mapping[str, Any]]) -> None:
    """Run the aggregate schema gate over an emitted claim set (§18.1-analogue)."""
    for row in rows:
        assert_aggregate_row(row)


# --- the field-state distinction (mandated != populated, F3.20) ----------------


def field_state_of(value: Any, *, present: bool = True) -> str:
    """Classify one mandated questionnaire field: ``answered`` / ``present_but_empty`` / ``absent``.

    A mandated field the city left blank (the row exists, the value does not —
    Seattle's unfilled Fiscal 1.1/1.2 cost tables) is ``present_but_empty``, a
    state distinct from both an answer and an absent field; a field not in the
    filing at all is ``absent``. The three are never conflated (mandated ≠
    populated, F3.20).
    """
    if not present:
        return "absent"
    if value is None or str(value).strip() == "":
        return "present_but_empty"
    return "answered"


# --- the per-agency aggregate claim shape --------------------------------------


@dataclass(frozen=True)
class DocumentContext:
    """The provenance of one source disclosure a claim was read from (P1–P3, §3.1)."""

    source_id: str
    source_url: str
    retrieved_date: str
    genre: DocumentGenre
    jurisdiction: str
    reporting_period: str
    agency: str
    technology: str | None = None
    reports_actual_use: bool = False


def _subject_id(ctx: DocumentContext, claim_type: str, agency: str | None) -> str:
    """The per-agency subject id (``ccops:<jur>:<agency>``; ordinance is jurisdiction-scoped)."""
    if claim_type == "ordinance":
        return f"ccops:{ctx.jurisdiction}"
    return f"ccops:{ctx.jurisdiction}:{agency or ctx.agency}"


def disclosure_claim(
    ctx: DocumentContext,
    *,
    claim_type: str,
    predicate: str,
    value: Any,
    raw_value: str,
    extraction_method: str,
    locator: Mapping[str, Any],
    agency: str | None = None,
    technology: str | None = None,
    reporting_period: str | None = None,
    field_state: str | None = None,
) -> dict[str, Any]:
    """Build one typed, evidenced, aggregate-guarded CCOPS disclosure claim.

    Every claim is **typed** (``claim_type``), **evidenced** (source url +
    retrieval date + the parser-layer locator + extraction method), **dated**
    (``observed_at``), a **per-agency aggregate row** (``agency`` /
    ``reporting_period`` / ``technology`` + the stamped ``aggregate_level``), and
    routed through **all three guards HERE** so they cannot be bypassed: the
    genre gate (procured≠deployed), the predicate-level use guard, and the
    Part VIII aggregate schema gate. The raw literal is preserved verbatim (P2).
    """
    _person_naming_check(predicate)
    assert_predicate_allowed(predicate)
    assert_claim_type_supported(claim_type, ctx.genre, reports_actual_use=ctx.reports_actual_use)
    assert_use_predicate_has_use_claim(predicate, claim_type)
    if field_state is not None and field_state not in field_states():
        raise ValueError(
            f"field_state {field_state!r} is not in the mandated!=populated vocabulary "
            f"{sorted(field_states())}"
        )
    tech = technology if technology is not None else ctx.technology
    row: dict[str, Any] = {
        "record_kind": "claim",
        "connector": CCOPS_CONNECTOR,
        "source_id": ctx.source_id,
        "source_class": source_class()["name"],
        "claim_type": claim_type,
        "document_genre": ctx.genre.value,
        "subject_id": _subject_id(ctx, claim_type, agency),
        "jurisdiction": ctx.jurisdiction,
        "agency": agency or ctx.agency,
        "reporting_period": reporting_period or ctx.reporting_period,
        "aggregate_level": aggregate_level(),
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,  # P2 — the source literal preserved verbatim
        "evidence": {
            "source_url": ctx.source_url,
            "retrieved_date": ctx.retrieved_date,
            "extraction_method": extraction_method,
            "locator": dict(locator),
        },
        "observed_at": ctx.retrieved_date,
        "source_attribution": ctx.source_id,
    }
    if tech is not None:
        row["technology"] = tech
    if field_state is not None:
        row["field_state"] = field_state
    assert_aggregate_row(row)
    return row


# --- the per-document extractors ----------------------------------------------


def _document_context(doc: Mapping[str, Any], source_id: str) -> DocumentContext:
    """Derive the document context, re-deriving the genre from the text (never a label).

    The genre the epistemic guard keys off is computed from the document's own
    text via :func:`parsing.genre.classify_genre`; a fixture ``genre`` label that
    disagrees with the derived genre is rejected, so a document cannot be
    relabelled to unlock a claim surface it does not belong to. When the text
    classifies to no genre the declared label stands (the pathways rule).
    """
    text = str(doc.get("text", ""))
    derived = classify_genre(str(doc.get("id", "document")), text.encode("utf-8")).genre
    declared = doc.get("genre")
    if declared is not None and derived is not DocumentGenre.UNKNOWN:
        if DocumentGenre(str(declared)) is not derived:
            raise ClaimTypeNotPermitted(
                f"document {doc.get('id')!r} is labelled {declared!r} but its text "
                f"classifies as {derived.value!r}; the genre used for the epistemic "
                "guard is the derived one — relabel the fixture or fix the text."
            )
    genre = (
        derived
        if derived is not DocumentGenre.UNKNOWN
        else DocumentGenre(str(declared or "unknown"))
    )
    return DocumentContext(
        source_id=source_id,
        source_url=str(doc["source_url"]),
        retrieved_date=str(doc.get("retrieved_date", "2026-08-20")),
        genre=genre,
        jurisdiction=str(doc["jurisdiction"]),
        reporting_period=str(doc["reporting_period"]),
        agency=str(doc["agency"]),
        technology=doc.get("technology"),
        reports_actual_use=bool(doc.get("reports_actual_use", False)),
    )


def _ordinance_claims(doc: Mapping[str, Any], ctx: DocumentContext) -> list[dict[str, Any]]:
    """Emit the ordinance (legal-instrument) facts a document carries (jurisdiction-scoped)."""
    block = doc.get("ordinance")
    if not block:
        return []
    out: list[dict[str, Any]] = []
    for i, (predicate, value) in enumerate(block.items()):
        out.append(
            disclosure_claim(
                ctx,
                claim_type="ordinance",
                predicate=str(predicate),
                value=value,
                raw_value=str(value),
                extraction_method="structured_import",
                locator={"kind": "row", "row": i},
                agency=str(block.get("enacting_body", ctx.agency)),
                technology=None,
            )
        )
    return out


def _extract_field_questionnaire(
    doc: Mapping[str, Any], ctx: DocumentContext
) -> list[dict[str, Any]]:
    """Read a mandated field questionnaire (e.g. Seattle's fixed 50-field SIR).

    Each ``fields`` row cites the mandated field number, the dossier predicate it
    populates, and its state — ``answered`` fields become dossier-field
    ``disclosure`` claims; ``present_but_empty`` / ``absent`` fields become
    ``disclosure_field_state`` claims recording the mandated != populated state,
    never a fabricated value (F3.20).
    """
    out = _ordinance_claims(doc, ctx)
    for i, field in enumerate(doc["fields"]):
        state = str(field.get("state", field_state_of(field.get("value"))))
        if state != "answered":
            out.append(
                disclosure_claim(
                    ctx,
                    claim_type="disclosure",
                    predicate="disclosure_field_state",
                    value=state,
                    raw_value=str(field["field"]),
                    extraction_method="structured_import",
                    locator={"kind": "row", "row": i},
                    field_state=state,
                )
            )
            continue
        out.append(
            disclosure_claim(
                ctx,
                claim_type="disclosure",
                predicate=str(field["predicate"]),
                value=field["value"],
                raw_value=str(field.get("raw_value", field["value"])),
                extraction_method="structured_import",
                locator={"kind": "row", "row": i},
                field_state="answered",
            )
        )
    return out


def _extract_policy_clauses(doc: Mapping[str, Any], ctx: DocumentContext) -> list[dict[str, Any]]:
    """Read a disclosure policy document via the layer-3 clause locator (NYC POST)."""
    clauses = locate_clauses(str(doc["text"]).encode("utf-8"))
    out = _ordinance_claims(doc, ctx)
    for fact in doc["clauses"]:
        clause = find_clause(clauses, str(fact["clause"]))
        if clause is None:
            raise ValueError(
                f"disclosure fact cites clause {fact['clause']!r} not found in document "
                f"{doc.get('id')!r} (SIG-PARSE-003)"
            )
        pc = clause_claim(
            clause,
            subject=f"ccops:{ctx.jurisdiction}:{ctx.agency}",
            predicate=str(fact["predicate"]),
            value=str(fact["value"]),
            value_kind=fact.get("value_kind", "text"),
        )
        out.append(
            disclosure_claim(
                ctx,
                claim_type=str(fact.get("claim_type", "disclosure")),
                predicate=pc.predicate,
                value=pc.value.parsed,
                raw_value=pc.value.raw_value,
                extraction_method=pc.extraction_method,
                locator=pc.locator.to_row(),
            )
        )
    return out


def _extract_inventory_table(doc: Mapping[str, Any], ctx: DocumentContext) -> list[dict[str, Any]]:
    """Read a mandated inventory's status rows + compliance metric (SF Chapter 19B).

    Per-row: an ``inventory_entry`` claim pair (technology + approval_status,
    agency-keyed). A row whose status is in ``in_use_statuses`` additionally
    yields a ``disclosure_use`` ``in_use`` claim — the disclosure's own
    row-level statement of use (never an inference); every other status
    (approved / draft / seeking-procurement / deprecated) yields no use claim —
    the row-level form of procured ≠ deployed. The document's
    ``reported_compliance`` block lands the non-compliance metric as
    ``compliance_finding`` claims (SIG-INGEST-049e).
    """
    out = _ordinance_claims(doc, ctx)
    for i, row in enumerate(doc["rows"]):
        agency = str(row["department"])
        technology = str(row["technology"])
        status = str(row["status"])
        for predicate, value in (
            ("technology", technology),
            ("technology_category", row.get("technology_category")),
            ("approval_status", status),
        ):
            if value is None:
                continue
            out.append(
                disclosure_claim(
                    ctx,
                    claim_type="inventory_entry",
                    predicate=predicate,
                    value=value,
                    raw_value=str(value),
                    extraction_method="structured_import",
                    locator={"kind": "row", "row": i},
                    agency=agency,
                    technology=technology,
                )
            )
        if status in in_use_statuses():
            out.append(
                disclosure_claim(
                    ctx,
                    claim_type="disclosure_use",
                    predicate="in_use",
                    value=True,
                    raw_value=status,
                    extraction_method="structured_import",
                    locator={"kind": "row", "row": i},
                    agency=agency,
                    technology=technology,
                )
            )
    compliance = doc.get("reported_compliance") or {}
    for i, (predicate, value) in enumerate(compliance.items()):
        out.append(
            disclosure_claim(
                ctx,
                claim_type="compliance_finding",
                predicate=str(predicate),
                value=value,
                raw_value=str(value),
                extraction_method="structured_import",
                locator={"kind": "row", "row": i},
                technology="(citywide inventory)",
            )
        )
    return out


_EXTRACTORS = {
    "field_questionnaire": _extract_field_questionnaire,
    "policy_clauses": _extract_policy_clauses,
    "inventory_table": _extract_inventory_table,
}


def extract_documents(parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Extract every claim from a fixture's document set (the ADR-080 dispatcher).

    A pure function of the parsed capture: the ``disclosure_source`` selects the
    registry source id, and each document's ``kind`` selects the per-source
    extractor. Every claim routes through :func:`disclosure_claim`, so all three
    guards (genre, use-predicate, aggregate schema) run for every claim.
    """
    source_id = source_id_for(str(parsed["disclosure_source"]))
    out: list[Mapping[str, Any]] = []
    for doc in parsed.get("documents", []):
        ctx = _document_context(doc, source_id)
        kind = str(doc["kind"])
        extractor = _EXTRACTORS.get(kind)
        if extractor is None:
            raise ValueError(
                f"unknown disclosure document kind {kind!r} (document {doc.get('id')!r}); "
                f"known: {sorted(_EXTRACTORS)}"
            )
        out.extend(extractor(doc, ctx))
    return out


def parse_disclosure(data: bytes) -> dict[str, Any]:
    """Parse a disclosure fixture capture (pure function of the bytes)."""
    payload = json.loads(data.decode("utf-8"))
    if "disclosure_source" not in payload:
        raise ValueError(
            "a government_mandated_disclosure capture must carry a 'disclosure_source' "
            "(SIG-INGEST-049, P24.7)"
        )
    return payload


# --- the connector ------------------------------------------------------------


@register
class GovernmentMandatedDisclosureConnector(Connector):
    """The `government_mandated_disclosure` connector: CCOPS disclosures (SIG-INGEST-049*).

    One connector, three paying source adapters (ADR-080: Seattle 50-field SIR,
    NYC POST Act policies, SF Chapter 19B biannual inventory). Runs on the P04.1
    eight-stage framework; ``parse``/``extract``/``normalize`` are pure functions
    of the capture that build typed, evidenced, per-agency aggregate claims
    through the sig-parsing layers and the procured≠deployed epistemic guard.
    The sources stay ``ingestion_permitted=false`` until a packet + flip, so a
    live run against them is refused at the loader gate (exit 3); replay/shadow
    run over committed fixtures with no network (SIG-INGEST-018/019).
    """

    name = CCOPS_CONNECTOR
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        return parse_disclosure(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return extract_documents(parsed)

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        # The claims are already typed + evidenced + guarded by disclosure_claim;
        # the post-hoc aggregate sweep re-proves it over the emitted set (a future
        # extractor bypassing disclosure_claim still fails closed), then
        # normalize stamps the connector vocabulary version so a versioned
        # re-extraction is a new interpretation (§20, SIG-INGEST-017).
        assert_no_forbidden_output(raw_claims)
        version = vocab_version()
        return [{**claim, "vocab_version": version} for claim in raw_claims]

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for claim in linked:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        return out
