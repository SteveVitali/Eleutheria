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
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from evidence.digest import multihash
from parsing.classification import FileFormat, classify
from parsing.clauses import clause_claim, find_clause, locate_clauses
from parsing.document import (
    byte_range_locator,
    html_links,
    html_text,
    page_locator_for,
    pdf_text_pages,
)
from parsing.genre import DEPLOYMENT_GENRES, DocumentGenre, classify_genre
from parsing.locator import Locator

from ._data import load_table
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

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


def adapter_key_for(source_id: str) -> str | None:
    """The ``[sources]`` key for a registry source id (``nyc_post``, ``seattle``, ``sf``)."""
    for key, sid in vocab()["sources"].items():
        if str(sid) == source_id:
            return str(key)
    return None


def source_adapter(source_id: str) -> Mapping[str, Any] | None:
    """The reviewed ``[adapters.<key>]`` spec for a source id (P25.5), or ``None``."""
    key = adapter_key_for(source_id)
    if key is None:
        return None
    return vocab().get("adapters", {}).get(key)


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
    """Run the aggregate schema gate over an emitted claim set (§18.1-analogue).

    ``evidence_document`` / ``quality_report`` rows are provenance artifacts, not
    per-agency aggregate claims — the gate does not apply to them.
    """
    for row in rows:
        if row.get("record_kind") in {"evidence_document", "quality_report", "index_page"}:
            continue
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


# --- the index→document adapter (P25.5) -----------------------------------------
#
# Each CCOPS index page IS the discovery surface for its mandated filings: the
# captured HTML's <a href> links are filtered through the reviewed
# ``[adapters.<key>]`` spec (same host, ``doc_url_contains``, ``doc_suffixes``,
# bounded by ``max_documents``) into ``disclosure_document`` targets — never an
# unbounded crawl. A captured filing is read at the P07.1-classified layer:
# digital-native PDFs via the layer-3 ``pdf_text`` engine, HTML filings via the
# layer-2 text helper. Every claim routes through ``disclosure_claim``, so all
# three guards (genre / use-predicate / aggregate schema) run on every row, and
# a filing with no text layer is an evidence artifact — never fabricated fields.


def _configured_target(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The run-context target spec for a capture URI (configured or resolved)."""
    resolved = ctx.resolved_targets.get(uri)
    if resolved is not None:
        return resolved
    for target in ctx.parameters.get("targets", []) or ():
        if str(target.get("url") or "") == uri:
            return target
    return None


def _retrieved_date(capture: CaptureRef) -> str:
    if capture.retrieved_at is not None:
        return capture.retrieved_at.date().isoformat()
    return datetime.now(UTC).date().isoformat()


def _same_host(url: str, host: str) -> bool:
    netloc = urlparse(url).netloc.lower()
    return netloc == host or netloc.endswith(f".{host}")


def _matching_doc_links(
    data: bytes, index_url: str, adapter: Mapping[str, Any], spec: Mapping[str, Any]
) -> list[Any]:
    """The document links on a captured index page matching the reviewed spec."""
    url_contains = str(
        spec.get("doc_url_contains") or adapter.get("doc_url_contains") or ""
    ).lower()
    suffixes = tuple(
        str(s).lower() for s in (spec.get("doc_suffixes") or adapter.get("doc_suffixes") or ())
    )
    same_host = bool(spec.get("same_host", True))
    host = urlparse(index_url).netloc.lower()
    anchor_re = spec.get("anchor_pattern")
    anchor_pattern = re.compile(str(anchor_re), re.I) if anchor_re else None
    out = []
    for link in html_links(data, index_url):
        lowered = link.url.lower()
        path = urlparse(link.url).path.lower()
        if same_host and not _same_host(link.url, host):
            continue
        if url_contains and url_contains not in lowered:
            continue
        if suffixes and not path.endswith(suffixes):
            continue
        if anchor_pattern is not None and not anchor_pattern.search(link.anchor):
            continue
        out.append(link)
    return out


def resolve_index_targets(
    ctx: RunContext,
    index_capture: CaptureRef,
    spec: Mapping[str, Any],
    adapter: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Resolve the bounded ``disclosure_document`` targets off an index page (P25.5).

    The resolved child carries its index provenance (index URL + link ordinal +
    anchor text) and registers on ``ctx.resolved_targets``; the cap comes from
    the live-target row's ``max_documents`` (default 8) — bounded fan-out, never
    the whole filing archive.
    """
    data = ctx.captures.get(index_capture.digest)
    max_documents = int(spec.get("max_documents", 8))
    out: list[dict[str, Any]] = []
    for link in _matching_doc_links(data, index_capture.source_uri, adapter, spec):
        if len(out) >= max_documents:
            break
        out.append(
            {
                "id": f"{ctx.source.id}-doc:{link.ordinal}",
                "url": link.url,
                "kind": "disclosure_document",
                "index_url": index_capture.source_uri,
                "link_ordinal": link.ordinal,
                "anchor": link.anchor,
            }
        )
    return out


#: A NYC POST Act IUP carries its revision as ``UPDATED: <Month> <D>, <YYYY>``.
_RE_UPDATED = re.compile(r"UPDATED:\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", re.IGNORECASE)
_RE_FILENAME_PERIOD = re.compile(r"_(\d{1,2})\.(\d{1,2})\.(\d{2})(?=[_.]|$)")
#: A filing's own ``Date:``/``DATE:`` field label — the Cambridge annual
#: surveillance report carries ``Date: 02/27/2023``, the Somerville mandated
#: annual report ``Date: 2/19/25`` (a two-digit year). The document's declared
#: date stands in for the reporting period the way the NYC UPDATED: revision
#: does — verbatim, never inferred (P2).
_RE_DATE_FIELD_NUMERIC = re.compile(
    r"\bdate\s*:\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b", re.IGNORECASE
)
#: The same field label with a named month — Oakland's ALPR annual report
#: memorandum carries ``DATE: March 22, 2022``.
_RE_DATE_FIELD_NAMED = re.compile(
    r"\bdate\s*:\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", re.IGNORECASE
)
#: A date the index link's own anchor text carries — Cambridge's attachment is
#: titled ``Annual Surveillance Report 02-27-2023`` (M-D-YYYY).
_RE_ANCHOR_DATE = re.compile(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})")
#: A bare four-digit year — annual-report filings name their covered year in
#: the filename slug (``...-annual-report-2021.pdf``) or the anchor
#: (``... Annual Report (2019)``). Year granularity is the filing's own
#: literal, recorded as-is — never re-dated.
_RE_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_MONTHS = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def _reporting_period(text: str, filename: str, anchor: str = "") -> str | None:
    """The filing's own declared date — the disclosure's reporting period (ISO).

    Read from the document's own literals in precedence order: the ``UPDATED:``
    revision (NYC), a ``Date:``/``DATE:`` field label in numeric or named-month
    form (Cambridge ``Date: 02/27/2023``, Somerville ``Date: 2/19/25``, Oakland
    ``DATE: March 22, 2022``), a filename ``_M.D.YY`` component, an anchor-carried
    ``M-D-YYYY`` date (``Annual Surveillance Report 02-27-2023``), then a bare
    covered year in the filename slug or anchor (``...-report-2021.pdf``,
    ``Annual Report (2019)``). ``None`` when the document carries none — a claim
    with no reporting period cannot satisfy the aggregate gate and is not
    emitted; nothing is ever inferred (§3.1).
    """
    match = _RE_UPDATED.search(text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        if month:
            return f"{match.group(3)}-{month}-{int(match.group(2)):02d}"
    match = _RE_DATE_FIELD_NUMERIC.search(text)
    if match:
        month, day, year = match.groups()
        year_num = int(year) + 2000 if len(year) == 2 else int(year)
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{year_num}-{int(month):02d}-{int(day):02d}"
    match = _RE_DATE_FIELD_NAMED.search(text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        if month:
            return f"{match.group(3)}-{month}-{int(match.group(2)):02d}"
    match = _RE_FILENAME_PERIOD.search(filename)
    if match:
        month, day, year = match.groups()
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"20{year}-{int(month):02d}-{int(day):02d}"
    match = _RE_ANCHOR_DATE.search(anchor)
    if match:
        month, day, year = match.groups()
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{year}-{int(month):02d}-{int(day):02d}"
    for source in (filename, anchor):
        match = _RE_YEAR.search(source)
        if match:
            return match.group(1)
    return None


def _clean_tech_literal(text: str) -> str:
    """Strip questionnaire bullets/trailing punctuation off a technology literal."""
    return re.sub(r"[\s;,.]+$", "", re.sub(r"^[•\-*▪◦\s]+", "", text.strip()))


#: The aggregate ``technology`` value a combined multi-department filing carries
#: on its filing-level claims (the SF ``(citywide inventory)`` precedent): the
#: disclosure-level claims each name their own technology; the mandated-section
#: field states belong to the filing, not to any one listed system.
_COMBINED_FILING_TECH = "(combined filing)"


def _document_technologies(
    filename: str,
    pages: tuple[str, ...],
    adapter: Mapping[str, Any],
    anchor: str = "",
) -> list[tuple[str, str]]:
    """Every technology the filing itself names — ``(display, raw literal)`` pairs.

    Read in precedence order, all verbatim from the document (never a fixture
    label): the first ALL-CAPS title heading on page 1 (NYC IUP — e.g.
    ``CELL-SITE SIMULATORS:`` → ``Cell-Site Simulators``); the adapter's
    ``technology_field_pattern`` (the filing's own questionnaire field —
    Cambridge/Somerville's ``Surveillance Technology: <name>``; captures every
    occurrence when ``technology_field_multi`` is set — a combined
    multi-department report names each department's technology); the reviewed
    ``technology_anchor_pattern`` over the index link's anchor text (Oakland's
    ``<technology> Annual Report (YYYY)`` / Somerville's
    ``... Annual Report <technology>`` attachments); then the filename slug
    before ``technology_filename_marker`` (NYC). An anchor-derived name that is
    a bare year is dropped — it is the covered year, not a technology. An empty
    list means the document supplies no technology — a claim with no technology
    cannot satisfy the aggregate gate.
    """
    if pages:
        for line in pages[0].splitlines()[:12]:
            stripped = line.strip()
            if (
                6 < len(stripped) < 60
                and stripped.endswith(":")
                and stripped == stripped.upper()
                and re.search(r"[A-Z]{3}", stripped)
            ):
                literal = stripped[:-1].strip()
                return [(literal.title(), literal)]
    field_pattern = adapter.get("technology_field_pattern")
    if field_pattern:
        pattern = re.compile(str(field_pattern))
        found: list[tuple[str, str]] = []
        for page in pages:
            for match in pattern.finditer(page):
                raw = match.group(1).strip()
                cleaned = _clean_tech_literal(raw)
                if cleaned and not re.fullmatch(r"\d{4}", cleaned):
                    found.append((cleaned, raw))
        if found:
            seen: set[str] = set()
            dedup: list[tuple[str, str]] = []
            for pair in found:
                if pair[0].lower() not in seen:
                    seen.add(pair[0].lower())
                    dedup.append(pair)
            return dedup if adapter.get("technology_field_multi") else dedup[:1]
    anchor_pattern = adapter.get("technology_anchor_pattern")
    if anchor_pattern and anchor:
        anchor_match = re.search(str(anchor_pattern), anchor)
        if anchor_match:
            if "tech" in anchor_match.groupdict():
                raw = anchor_match.group("tech")
            elif anchor_match.lastindex:
                raw = anchor_match.group(1)
            else:
                raw = anchor_match.group(0)
            cleaned = _clean_tech_literal(str(raw or ""))
            if cleaned and not re.fullmatch(r"\d{4}", cleaned):
                return [(cleaned, str(raw).strip())]
    marker = str(adapter.get("technology_filename_marker") or "")
    if marker:
        stem, sep, _ = filename.lower().rsplit("/", 1)[-1].partition(marker)
        if sep and stem:
            return [(stem.replace("-", " ").strip().title(), stem)]
    return []


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("&", "&").upper().strip()


def _section_state(text: str, heading: str, all_headings: list[str]) -> tuple[str, str]:
    """One mandated section's field state + the body text it carried (F3.20).

    ``answered`` = the heading is present and carries a non-trivial body before
    the next mandated heading; ``present_but_empty`` = the heading is present but
    the body is empty or an explicit N/A; ``absent`` = the mandated heading is
    not in the filing at all.
    """
    folded = _normalize_heading(text)
    head = _normalize_heading(heading)
    idx = folded.find(head)
    if idx < 0:
        return "absent", ""
    rest = folded[idx + len(head) :]
    # The body ends at the next mandated heading (headings may carry a section
    # number prefix — "VI. EXTERNAL ENTITIES" — which is markup, not body).
    nxt = len(rest)
    for other in all_headings:
        o = _normalize_heading(other)
        if o == head:
            continue
        match = re.search(
            r"(?:^|\s)(?:[IVXLCDM]+|\d+)[.)]\s*" + re.escape(o) + r"|" + re.escape(o),
            rest,
        )
        if match and match.start() < nxt:
            nxt = match.start()
    body = rest[:nxt].strip(" :—-.")
    if not body or re.fullmatch(r"(n/?a|none|[ivxlcdm]+)[.]?", body, re.IGNORECASE):
        return "present_but_empty", ""
    return "answered", body


_RE_DURATION = re.compile(
    r"((?:within|for up to|for a period of|for|after)\s+\d+\s+(?:days?|months?|years?))",
    re.IGNORECASE,
)


def _retention_literal(section_body: str) -> str | None:
    """A duration literal inside a retention section body — ``None`` when absent."""
    match = _RE_DURATION.search(section_body)
    return match.group(1) if match else None


_RE_LEGAL_AUTHORITY = re.compile(
    r"(POST Act|Public Oversight of Surveillance Technology[^\n.]*|"
    r"Administrative Code\s*§?\s*14-1\d\d|Local Law\s+\d+\s+of\s+\d{4})",
    re.IGNORECASE,
)


def _document_text(parsed: Mapping[str, Any]) -> tuple[str, tuple[str, ...], str]:
    """The extracted text + page tuple + extraction method for a parsed document."""
    pages = tuple(str(p) for p in parsed.get("pages") or ())
    if pages:
        return "\n".join(pages), pages, "pdf_text"
    text = str(parsed.get("text") or "")
    return text, (text,) if text else (), "selector_template"


def _evidence_record(
    capture: CaptureRef, parsed: Mapping[str, Any], genre: DocumentGenre
) -> dict[str, Any]:
    return {
        "record_kind": "evidence_document",
        "source_uri": capture.source_uri,
        "capture_digest": capture.digest,
        "media_type": capture.media_type,
        "byte_size": parsed["byte_size"],
        "verdict": parsed["verdict"],
        "genre": genre.value,
    }


def _extract_index_page(ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Field-level claims off a captured CCOPS index page (P25.5).

    The index page is evidence for the ordinance it publishes under: the
    ordinance-citation literal (``SMC 14.18`` / ``POST Act`` / ``Chapter 19B``)
    and the enacting-body literal are located verbatim in the captured bytes
    (``byte_range`` locators). The page is also recorded as an ``index_page``
    provenance row carrying the resolved-link count so a silently-emptied index
    is visible downstream (and a link-less index never reaches here — parse
    fails closed with :class:`ContentDrift`).
    """
    capture = parsed["capture"]
    data = ctx.captures.get(capture.digest)
    adapter = source_adapter(ctx.source.id) or {}
    genre = classify_genre(capture.source_uri, data).genre
    out: list[Mapping[str, Any]] = [_evidence_record(capture, parsed, genre)]
    permitted = genre_claim_types().get(genre, frozenset())
    literals_found: list[str] = []
    doc = DocumentContext(
        source_id=ctx.source.id,
        source_url=capture.source_uri,
        retrieved_date=_retrieved_date(capture),
        genre=genre,
        jurisdiction=str(adapter.get("jurisdiction", "")),
        reporting_period=_retrieved_date(capture),
        agency=str(adapter.get("agency", "")),
    )
    if adapter and "ordinance" in permitted:
        for literal in adapter.get("ordinance_literals", ()):
            loc = byte_range_locator(data, str(literal))
            if loc is None:
                continue
            literals_found.append(str(literal))
            out.append(
                disclosure_claim(
                    doc,
                    claim_type="ordinance",
                    predicate="ordinance_citation",
                    value=str(adapter["ordinance_citation"]),
                    raw_value=str(literal),
                    extraction_method="selector_template",
                    locator=loc,
                    agency=str(adapter.get("enacting_body") or doc.agency),
                    technology=None,
                )
            )
            break
        body_literal = str(adapter.get("enacting_body_literal") or "")
        loc = byte_range_locator(data, body_literal) if body_literal else None
        if loc is not None:
            out.append(
                disclosure_claim(
                    doc,
                    claim_type="ordinance",
                    predicate="enacting_body",
                    value=str(adapter.get("enacting_body") or body_literal),
                    raw_value=body_literal,
                    extraction_method="selector_template",
                    locator=loc,
                    agency=str(adapter.get("enacting_body") or doc.agency),
                    technology=None,
                )
            )
    out.append(
        {
            "record_kind": "index_page",
            "source_uri": capture.source_uri,
            "capture_digest": capture.digest,
            "media_type": capture.media_type,
            "byte_size": parsed["byte_size"],
            "verdict": parsed["verdict"],
            "genre": genre.value,
            "link_count": int(parsed.get("link_count", 0)),
            "ordinance_literals_found": literals_found,
        }
    )
    return out


def _extract_disclosure_document(
    ctx: RunContext, parsed: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """Field-level claims off a captured disclosure filing (P25.5).

    A digital-native filing yields: the ordinance citation + enacting body it
    carries (``ordinance`` claims — jurisdiction-scoped), its technology name
    (derived from the document's own title heading or filename slug — never
    trusted from a fixture label), its legal-authority literal, a retention
    literal where the retention section carries one, and one
    ``disclosure_field_state`` claim per reviewed mandated section recording
    ``answered`` / ``present_but_empty`` / ``absent`` (mandated != populated).
    A filing with no text layer, no derivable reporting period, or no
    technology is an evidence artifact + index record ONLY — fields are never
    fabricated to fill the schema.
    """
    capture = parsed["capture"]
    data = ctx.captures.get(capture.digest)
    adapter = source_adapter(ctx.source.id) or {}
    genre = DocumentGenre(str(parsed.get("genre", "unknown")))
    artifact = _evidence_record(capture, parsed, genre)
    out: list[Mapping[str, Any]] = [artifact]
    text, pages, method = _document_text(parsed)
    if not adapter or not text.strip():
        return out

    suppressed: list[str] = []

    def emit(make: Any) -> None:
        """Append a claim; a Part VIII token collision suppresses it, recorded.

        A verbatim literal may itself carry a forbidden token (the real ALPR
        filing's technology name literally reads "AUTOMATIC LICENSE PLATE
        READERS"): the aggregate gate refuses that raw literal, and the adapter
        drops the claim — recorded on the artifact row — rather than crash the
        run or weaken the sweep (Part VIII, fail closed).
        """
        try:
            out.append(make())
        except PartVIIIViolation as exc:
            suppressed.append(str(exc))

    def finish() -> list[Mapping[str, Any]]:
        if suppressed:
            artifact["part_viii_suppressions"] = list(suppressed)
        return out

    filename = _filename_from_uri(capture.source_uri)
    # The resolved index→document target carries the index link's anchor text —
    # the reviewed literal an Oakland/Somerville filing derives its technology
    # and covered-year from when the document itself has no field literal.
    spec = _configured_target(ctx, capture.source_uri) or {}
    anchor = str(spec.get("anchor") or "")
    period = _reporting_period(text, filename, anchor)
    techs = _document_technologies(filename, pages if pages else (text,), adapter, anchor)
    permitted = genre_claim_types().get(genre, frozenset())
    doc = DocumentContext(
        source_id=ctx.source.id,
        source_url=capture.source_uri,
        retrieved_date=_retrieved_date(capture),
        genre=genre,
        jurisdiction=str(adapter.get("jurisdiction", "")),
        reporting_period=period or _retrieved_date(capture),
        agency=str(adapter.get("agency", "")),
        technology=(techs[0][0] if len(techs) == 1 else (_COMBINED_FILING_TECH if techs else None)),
        # A deployment-genre filing IS a use report; every other genre reports
        # none (the epistemic guard independently refuses a use claim that
        # slips through).
        reports_actual_use=genre in DEPLOYMENT_GENRES,
    )
    if "ordinance" in permitted:
        literal = next(
            (
                str(literal)
                for literal in adapter.get("ordinance_literals", ())
                if str(literal).lower() in text.lower()
            ),
            None,
        )
        loc = (
            page_locator_for(pages, literal)
            if literal and pages
            else (byte_range_locator(data, literal) if literal else None)
        )
        emit(
            lambda: disclosure_claim(
                doc,
                claim_type="ordinance",
                predicate="ordinance_citation",
                value=str(adapter["ordinance_citation"]),
                raw_value=literal or str(adapter["ordinance_citation"]),
                extraction_method=method,
                locator=loc or Locator.page(1).to_row(),
                agency=str(adapter.get("enacting_body") or doc.agency),
                technology=None,
            )
        )
        body_literal = str(adapter.get("enacting_body_literal") or "")
        body_loc = (
            page_locator_for(pages, body_literal)
            if body_literal and pages
            else (byte_range_locator(data, body_literal) if body_literal else None)
        )
        if body_loc is not None:
            emit(
                lambda: disclosure_claim(
                    doc,
                    claim_type="ordinance",
                    predicate="enacting_body",
                    value=str(adapter.get("enacting_body") or body_literal),
                    raw_value=body_literal,
                    extraction_method=method,
                    locator=body_loc,
                    agency=str(adapter.get("enacting_body") or doc.agency),
                    technology=None,
                )
            )
    if "disclosure" not in permitted or not techs or period is None:
        return finish()
    for tech in techs:
        tech_loc = page_locator_for(pages, tech[1]) or Locator.page(1).to_row()
        emit(
            lambda tech=tech, tech_loc=tech_loc: disclosure_claim(
                doc,
                claim_type="disclosure",
                predicate="technology",
                value=tech[0],
                raw_value=tech[1],
                extraction_method=method,
                locator=tech_loc,
                technology=tech[0],
            )
        )
    authority_pattern = (
        re.compile(str(adapter["legal_authority_pattern"]), re.IGNORECASE)
        if adapter.get("legal_authority_pattern")
        else _RE_LEGAL_AUTHORITY
    )
    authority = authority_pattern.search(text)
    if authority:
        literal = authority.group(1) if authority.lastindex else authority.group(0)
        emit(
            lambda literal=literal: disclosure_claim(
                doc,
                claim_type="disclosure",
                predicate="legal_authority",
                value=literal,
                raw_value=literal,
                extraction_method=method,
                locator=page_locator_for(pages, literal) or Locator.page(1).to_row(),
            )
        )
    sections = [dict(s) for s in adapter.get("mandated_sections", ())]
    headings = [str(s["heading"]) for s in sections]
    for i, section in enumerate(sections):
        state, body = _section_state(text, str(section["heading"]), headings)
        loc = (
            page_locator_for(pages, str(section["heading"])) if state != "absent" else None
        ) or Locator.row(i).to_row()
        emit(
            lambda loc=loc, state=state, section=section: disclosure_claim(
                doc,
                claim_type="disclosure",
                predicate="disclosure_field_state",
                value=state,
                raw_value=str(section["field"]),
                extraction_method=method,
                locator=loc,
                field_state=state,
            )
        )
        if state == "answered" and str(section["field"]) == "retention_access_use":
            duration = _retention_literal(body)
            if duration:
                emit(
                    lambda loc=loc, duration=duration: disclosure_claim(
                        doc,
                        claim_type="disclosure",
                        predicate="retention_period",
                        value=duration,
                        raw_value=duration,
                        extraction_method=method,
                        locator=loc,
                    )
                )
    return finish()


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
    if parsed.get("kind") == "document":
        # A non-JSON capture is an upstream disclosure document: one evidence record
        # carrying its capture provenance + P07.1 verdict; field claims still
        # require the curated path (mandated-disclosure ≠ populated field).
        capture = parsed["capture"]
        return [
            {
                "record_kind": "evidence_document",
                "source_uri": capture.source_uri,
                "capture_digest": capture.digest,
                "media_type": capture.media_type,
                "byte_size": parsed["byte_size"],
                "verdict": parsed["verdict"],
            }
        ]
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


def _is_json_media(media_type: str) -> bool:
    # Only a JSON content type is the curated fixture payload; everything else —
    # including application/pdf — is an upstream document routed to the P07.1 classifier.
    return "json" in media_type.lower()


def _filename_from_uri(uri: str) -> str:
    tail = uri.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or "document"


def document_artifact_id(source_uri: str) -> str:
    """The stable EvidenceArtifact id for an upstream document at ``source_uri``.

    Keyed on the source URI, not the bytes, so the id is stable across
    re-captures and never depends on capture order (§10.2). Deterministic.
    """
    return f"gmd:artifact:{multihash(source_uri.encode('utf-8'))}"


def _document_artifact_row(
    source_id: str,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """An upstream document capture as an EvidenceArtifact row (§10.2).

    The connector **never re-hosts** the document (the source licence is
    ``LicenseRef-DerivedFacts-Citations``, redistributable=false): the row carries
    provenance — source URI, content-addressed capture digest, media type, size —
    and the P07.1 classification verdict, which is recorded but not run to a layer
    engine here (SIG-PARSE-001/002).
    """
    source_uri = str(record["source_uri"])
    row = {
        "record_kind": "evidence_artifact",
        "subject_id": document_artifact_id(source_uri),
        "predicate_id": assert_predicate_allowed("document"),
        "published_by": source_id,
        "source_uri": source_uri,
        "capture_digest": str(record["capture_digest"]),
        "media_type": str(record["media_type"]),
        "byte_size": int(record["byte_size"]),
        "integrity": "captured",
        "classification": dict(record["verdict"]),
        "raw_value": source_uri,
    }
    if record.get("genre"):
        row["document_genre"] = str(record["genre"])
    if record.get("part_viii_suppressions"):
        # A raw literal the Part VIII sweep refused (e.g. a technology name that
        # literally contains a forbidden token): the claim was suppressed and the
        # suppression is recorded, never silently dropped.
        row["part_viii_suppressions"] = list(record["part_viii_suppressions"])
    return row


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

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Bounded index→filing fan-out (P25.5).

        Every captured ``index_page`` target resolves its spec-matching document
        links into ``disclosure_document`` targets — bounded by the reviewed
        ``max_documents``, each carrying its index provenance — registered on
        ``ctx.resolved_targets`` so the fetch/parse stages see the same spec a
        configured target would carry.
        """
        out: list[Mapping[str, Any]] = []
        for capture in captures:
            spec = _configured_target(ctx, capture.source_uri)
            if spec is None or str(spec.get("kind")) != "index_page":
                continue
            adapter = source_adapter(ctx.source.id)
            if adapter is None:
                continue
            for target in resolve_index_targets(ctx, capture, spec, adapter):
                ctx.resolved_targets[str(target["url"])] = target
                out.append(target)
        return out

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a curated fixture payload, or an upstream document.

        A JSON capture is the curated ``disclosure_source`` payload. An
        ``index_page`` target parses its links + visible text and fails closed
        (:class:`ContentDrift`) when the page carries no spec-matching filing
        links — the upstream page shape changed. A ``disclosure_document`` /
        ``document`` target is classified (P07.1 + genre re-derived from the
        bytes) and read at its text layer — ``pdf_text`` for a digital-native
        PDF, ``selector_template`` for HTML; a filing with no text layer parses
        to the document it is and extracts as an artifact only.
        """
        data = ctx.captures.get(capture.digest)
        if _is_json_media(capture.media_type):
            return parse_disclosure(data)
        verdict = classify(_filename_from_uri(capture.source_uri), data)
        spec = _configured_target(ctx, capture.source_uri)
        configured_kind = str(spec.get("kind") or "") if spec else ""
        if configured_kind == "index_page":
            adapter = source_adapter(ctx.source.id)
            links = (
                _matching_doc_links(data, capture.source_uri, adapter, spec or {})
                if adapter is not None
                else []
            )
            if not links:
                raise ContentDrift(
                    ctx.source.id,
                    f"index page {capture.source_uri} carries no filing links "
                    "matching the reviewed discovery spec; the upstream page "
                    "shape changed — refusing to emit from a drifted index.",
                )
            return {
                "kind": "index_page",
                "capture": capture,
                "verdict": verdict.to_row(),
                "byte_size": len(data),
                "text": html_text(data),
                "link_count": len(links),
            }
        if configured_kind in {"disclosure_document", "document"}:
            genre = classify_genre(capture.source_uri, data).genre
            out: dict[str, Any] = {
                "kind": "disclosure_document",
                "capture": capture,
                "verdict": verdict.to_row(),
                "byte_size": len(data),
                "genre": genre.value,
            }
            if verdict.file_format is FileFormat.PDF:
                pages = pdf_text_pages(data)
                if any(pages):
                    out["pages"] = pages
            elif verdict.file_format is FileFormat.HTML:
                text = html_text(data)
                if text:
                    out["text"] = text
            return out
        return {
            "kind": "document",
            "capture": capture,
            "verdict": verdict.to_row(),
            "byte_size": len(data),
        }

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        kind = str(parsed.get("kind") or "")
        if kind == "index_page":
            return _extract_index_page(ctx, parsed)
        if kind == "disclosure_document":
            return _extract_disclosure_document(ctx, parsed)
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
        source_id = ctx.source.id
        out: list[dict[str, Any]] = []
        artifact_count = 0
        for claim in raw_claims:
            if claim.get("record_kind") == "evidence_document":
                out.append(
                    {
                        **_document_artifact_row(source_id, claim),
                        "vocab_version": version,
                        "license_spdx": ctx.source.rights.spdx,
                    }
                )
                artifact_count += 1
                continue
            out.append({**claim, "vocab_version": version})
        if artifact_count:
            out.append(
                {
                    "record_kind": "quality_report",
                    "source_id": source_id,
                    "capture_digest": str(raw_claims[0].get("capture_digest", "")),
                    "media_type": str(raw_claims[0].get("media_type", "")),
                    "byte_size": int(raw_claims[0].get("byte_size", 0)),
                    "capture_kind": "document",
                    "connector_name": self.name,
                    "connector_version": self.version,
                    "vocab_version": version,
                    "evidence_artifact_count": artifact_count,
                    "claim_count": len(raw_claims) - artifact_count,
                    "classification": raw_claims[0].get("verdict"),
                }
            )
        return out

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
