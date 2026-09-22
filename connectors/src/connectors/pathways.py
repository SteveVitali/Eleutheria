# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `pathways` connector — Stage-5 population of the Phase-17 pathways (§46, P21.9).

Phase 17 *proved* the frozen schema can express the broader-surveillance pathways
(private-camera federation / RTCC, facial recognition / cell-site simulators /
mobile-device forensics, gunshot detection / drones / commercial location data) as
conformance-suite instance graphs — "expressibility, not ingestion" (RISK-P17-03,
LD-V10). This connector does the ingestion half: it reads public procurement, policy,
federation, and deployment documents and emits the **same** P17 pathway claims as
dated, evidenced claim-spine rows.

**ADR-071 — one connector, three extractors.** The three pathway families all reuse the
same parser layers (the ADR-033-deferred layer-4 table extraction, :mod:`parsing.tables`,
and layer-3 clause locators, :mod:`parsing.clauses`), the same claim-shaping, and — most
importantly — the same **epistemic guard**. Splitting them into three connectors would
triplicate the eight-stage framework boilerplate around near-identical code, so this is a
single `pathways` connector whose ``extract`` dispatches to a per-family extractor
selected by the fixture's ``pathway_family``.

**The epistemic rule (§46, RISK-P21-16): ``procured`` NEVER implies ``deployed``.** A
procurement record — however itemised — evidences that a technology was *purchased*, not
that it is *operating*. A **deployment** claim may be asserted only from a
**deployment-genre** document (:data:`parsing.genre.DEPLOYMENT_GENRES`). Both a
genre-level and a predicate-level guard enforce it (:func:`assert_claim_type_supported_by_genre`,
:func:`assert_deployment_predicate_has_deployment_type`), and the document genre is
**re-derived from the document text** (:func:`parsing.genre.classify_genre`) rather than
trusted from a fixture label — so a procurement document cannot be relabelled into a
deployment claim.

The sources stay LINK-posture / ``ingestion_permitted = false`` until a rights packet +
operator flip (HG-03): a ``run --mode live`` against any of them REFUSES at the loader
gate (exit 3), exactly as every other gated source does; ``replay`` / ``shadow`` run over
committed fixtures with no network (SIG-INGEST-018/019).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from parsing.clauses import clause_claim, find_clause, locate_clauses
from parsing.genre import DEPLOYMENT_GENRES, DocumentGenre, classify_genre
from parsing.tables import parse_table, table_claims

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

__all__ = [
    "PATHWAYS_CONNECTOR",
    "ClaimTypeNotPermitted",
    "DeploymentInferenceError",
    "PredicateNotAllowed",
    "assert_claim_type_supported_by_genre",
    "assert_deployment_predicate_has_deployment_type",
    "assert_predicate_allowed",
    "claim_types",
    "conformance_pathways",
    "deployment_genres",
    "genre_claim_types",
    "pathway_claim",
    "pathway_family_source",
    "vocab",
    "vocab_version",
    "PathwaysConnector",
]

PATHWAYS_CONNECTOR = "pathways"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `pathways` connector vocabulary (``data/pathways_vocab.toml``)."""
    return load_table("pathways_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def claim_types() -> frozenset[str]:
    """The four P17 claim types this connector may emit (§46)."""
    return frozenset(vocab()["claim_types"])


def deployment_genres() -> frozenset[DocumentGenre]:
    """The genres from which a ``deployment`` claim may be asserted (RISK-P21-16)."""
    return frozenset(DocumentGenre(g) for g in vocab()["deployment_genres"])


def deployment_predicates() -> frozenset[str]:
    """The predicates that may ride ONLY on a ``deployment`` claim (RISK-P21-16)."""
    return frozenset(vocab()["deployment_predicates"])


def genre_claim_types() -> dict[DocumentGenre, frozenset[str]]:
    """The genre → permitted-claim-types gate (the §46 mechanical form)."""
    return {
        DocumentGenre(genre): frozenset(types)
        for genre, types in vocab()["genre_claim_types"].items()
    }


def conformance_pathways() -> dict[str, tuple[str, ...]]:
    """The P17 conformance pathways per family (the coverage roster, ADR-071)."""
    return {family: tuple(paths) for family, paths in vocab()["conformance_pathways"].items()}


def all_conformance_pathways() -> frozenset[str]:
    """Every P17 conformance pathway, across all families (coverage target)."""
    return frozenset(p for paths in conformance_pathways().values() for p in paths)


def pathway_family_source(family: str) -> str:
    """The registry source id a pathway family draws its fixtures from (HG-03)."""
    return str(vocab()["sources"][family])


# --- the epistemic guard: procured != deployed (§46, RISK-P21-16) -------------


class DeploymentInferenceError(Exception):
    """Raised when a ``deployment`` claim is asserted from a non-deployment document.

    The mechanical form of the §46 epistemic rule (RISK-P21-16): ``procured`` NEVER
    implies ``deployed``. A deployment claim requires a **deployment-genre** document
    (:data:`parsing.genre.DEPLOYMENT_GENRES`); asserting one from a procurement record,
    a policy document, an agenda item, or a vendor disclosure raises this — the
    over-inference is refused at the ingest boundary, named so the defect is auditable.
    """


class ClaimTypeNotPermitted(Exception):
    """Raised when a document's genre does not permit a claim type (the genre gate)."""


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§46, SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`."""
    if predicate not in predicate_allowlist():
        raise PredicateNotAllowed(
            f"the pathways connector may write only {sorted(predicate_allowlist())} "
            f"(§46, SIG-INGEST-033); {predicate!r} is outside the allowlist."
        )
    return predicate


def assert_claim_type_supported_by_genre(claim_type: str, genre: DocumentGenre) -> None:
    """Reject a claim type a document's genre does not support (§46, RISK-P21-16).

    The genre-level guard. A ``deployment`` claim from a non-deployment-genre document
    raises :class:`DeploymentInferenceError` specifically (the procured≠deployed rule);
    any other genre/claim-type mismatch raises :class:`ClaimTypeNotPermitted`.
    """
    if claim_type not in claim_types():
        raise ClaimTypeNotPermitted(
            f"{claim_type!r} is not a P17 claim type; must be one of {sorted(claim_types())} (§46)."
        )
    if claim_type == "deployment" and genre not in DEPLOYMENT_GENRES:
        raise DeploymentInferenceError(
            f"a 'deployment' claim requires a deployment-genre document "
            f"({sorted(g.value for g in DEPLOYMENT_GENRES)}); this document is {genre.value!r} — "
            "'procured' NEVER implies 'deployed' (§46, RISK-P21-16). The over-inference is refused."
        )
    permitted = genre_claim_types().get(genre, frozenset())
    if claim_type not in permitted:
        raise ClaimTypeNotPermitted(
            f"a {genre.value!r} document may not assert a {claim_type!r} claim "
            f"(permitted: {sorted(permitted)}) — §46, RISK-P21-16."
        )


def assert_deployment_predicate_has_deployment_type(predicate: str, claim_type: str) -> None:
    """Reject a deployment predicate carried by a non-deployment claim (RISK-P21-16).

    The predicate-level guard behind the genre gate: ``deployed`` /
    ``actually_provides_capability`` / ``in_operation`` may ride ONLY on a ``deployment``
    claim, so a procurement or policy claim can never smuggle a deployment fact.
    """
    if predicate in deployment_predicates() and claim_type != "deployment":
        raise DeploymentInferenceError(
            f"predicate {predicate!r} is a deployment fact; it may ride only on a 'deployment' "
            f"claim, not a {claim_type!r} claim — 'procured' NEVER implies 'deployed' "
            "(§46, RISK-P21-16)."
        )


# --- the P17 pathway claim shape ----------------------------------------------


@dataclass(frozen=True)
class DocumentContext:
    """The provenance of one source document a claim was read from (P1–P3, §3.1)."""

    source_id: str
    source_url: str
    retrieved_date: str
    genre: DocumentGenre
    conformance_pathway: str
    pathway_family: str


def pathway_claim(
    ctx: DocumentContext,
    *,
    claim_type: str,
    subject_kind: str,
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: str,
    extraction_method: str,
    locator: Mapping[str, Any],
    technology: str | None = None,
) -> dict[str, Any]:
    """Build one typed, evidenced P17 pathway claim, routing through both guards (§46).

    Every claim is **typed** (``claim_type``), **evidenced** (source url + retrieval date +
    the parser-layer locator + extraction method), and **dated** (``observed_at``). The two
    epistemic guards run HERE so the procured≠deployed rule cannot be bypassed: the genre
    must support the claim type, and a deployment predicate must ride a deployment claim.
    """
    assert_predicate_allowed(predicate)
    assert_claim_type_supported_by_genre(claim_type, ctx.genre)
    assert_deployment_predicate_has_deployment_type(predicate, claim_type)
    return {
        "record_kind": "claim",
        "connector": PATHWAYS_CONNECTOR,
        "source_id": ctx.source_id,
        "pathway_family": ctx.pathway_family,
        "conformance_pathway": ctx.conformance_pathway,
        "claim_type": claim_type,
        "document_genre": ctx.genre.value,
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,  # P2 — the source literal preserved verbatim
        "technology": technology,
        "evidence": {
            "source_url": ctx.source_url,
            "retrieved_date": ctx.retrieved_date,
            "extraction_method": extraction_method,
            "locator": dict(locator),
        },
        "observed_at": ctx.retrieved_date,
        "source_attribution": ctx.source_id,
    }


# --- the per-document extractors ----------------------------------------------


def _document_context(doc: Mapping[str, Any], family: str, source_id: str) -> DocumentContext:
    """Derive the document context, re-deriving the genre from the text (never trusting a label).

    The genre the epistemic guard keys off is computed from the document's own text via
    :func:`parsing.genre.classify_genre` — so a fixture cannot mislabel a procurement
    document as a deployment report to unlock a deployment claim (RISK-P21-16).
    """
    text = str(doc.get("text", ""))
    derived = classify_genre(str(doc.get("id", "document")), text.encode("utf-8")).genre
    declared = doc.get("genre")
    if declared is not None and derived is not DocumentGenre.UNKNOWN:
        if DocumentGenre(str(declared)) is not derived:
            raise ClaimTypeNotPermitted(
                f"document {doc.get('id')!r} is labelled {declared!r} but its text classifies as "
                f"{derived.value!r}; the genre used for the epistemic guard is the derived one "
                "(RISK-P21-16) — relabel the fixture or fix the text."
            )
    genre = derived if derived is not DocumentGenre.UNKNOWN else DocumentGenre(str(declared))
    return DocumentContext(
        source_id=source_id,
        source_url=str(doc["source_url"]),
        retrieved_date=str(doc.get("retrieved_date", "2026-08-20")),
        genre=genre,
        conformance_pathway=str(doc["conformance_pathway"]),
        pathway_family=family,
    )


def _extract_procurement_table(
    doc: Mapping[str, Any], ctx: DocumentContext
) -> list[dict[str, Any]]:
    """Read a procurement table via the layer-4 engine into vendor/product/procurement claims."""
    table = parse_table(str(doc["text"]).encode("utf-8"))
    subject_id = str(doc["subject_id"])
    subjects = [subject_id] * len(table.rows)
    predicate_columns = {col: spec["predicate"] for col, spec in doc["columns"].items()}
    typed_columns = {
        col: spec["value_kind"] for col, spec in doc["columns"].items() if "value_kind" in spec
    }
    parsed_claims = table_claims(
        table,
        subject_of_row=subjects,
        predicate_columns=predicate_columns,
        typed_columns=typed_columns,
    )
    claim_type_for = {spec["predicate"]: spec["claim_type"] for spec in doc["columns"].values()}
    out: list[dict[str, Any]] = []
    for pc in parsed_claims:
        out.append(
            pathway_claim(
                ctx,
                claim_type=claim_type_for[pc.predicate],
                subject_kind=str(doc.get("subject_kind", "deployment")),
                subject_id=pc.subject,
                predicate=pc.predicate,
                value=pc.value.parsed,
                raw_value=pc.value.raw_value,
                extraction_method=pc.extraction_method,
                locator=pc.locator.to_row(),
                technology=doc.get("technology"),
            )
        )
    return out


def _extract_policy_clauses(doc: Mapping[str, Any], ctx: DocumentContext) -> list[dict[str, Any]]:
    """Read a policy document via the layer-3 clause locator into policy claims."""
    clauses = locate_clauses(str(doc["text"]).encode("utf-8"))
    subject_id = str(doc["subject_id"])
    out: list[dict[str, Any]] = []
    for fact in doc["clauses"]:
        clause = find_clause(clauses, str(fact["clause"]))
        if clause is None:
            raise ValueError(
                f"policy fact cites clause {fact['clause']!r} not found in document "
                f"{doc.get('id')!r} (SIG-PARSE-003)"
            )
        pc = clause_claim(
            clause,
            subject=subject_id,
            predicate=str(fact["predicate"]),
            value=str(fact["value"]),
            value_kind=fact.get("value_kind", "text"),
        )
        out.append(
            pathway_claim(
                ctx,
                claim_type=str(fact.get("claim_type", "policy")),
                subject_kind=str(doc.get("subject_kind", "deployment")),
                subject_id=pc.subject,
                predicate=pc.predicate,
                value=pc.value.parsed,
                raw_value=pc.value.raw_value,
                extraction_method=pc.extraction_method,
                locator=pc.locator.to_row(),
                technology=doc.get("technology"),
            )
        )
    return out


def _extract_assertions(doc: Mapping[str, Any], ctx: DocumentContext) -> list[dict[str, Any]]:
    """Read explicit assertions (vendor disclosure, integration facts, deployment report).

    Each assertion is a row-located claim (SIG-PARSE-003 ROW locator). A deployment
    assertion is admitted ONLY because the document's derived genre is deployment_report;
    the same assertion in a vendor/procurement document raises DeploymentInferenceError.
    """
    subject_id = str(doc["subject_id"])
    out: list[dict[str, Any]] = []
    for i, fact in enumerate(doc["assertions"]):
        raw = str(fact.get("raw_value", fact["value"]))
        out.append(
            pathway_claim(
                ctx,
                claim_type=str(fact["claim_type"]),
                subject_kind=str(fact.get("subject_kind", doc.get("subject_kind", "deployment"))),
                subject_id=str(fact.get("subject_id", subject_id)),
                predicate=str(fact["predicate"]),
                value=fact["value"],
                raw_value=raw,
                extraction_method="structured_import",
                locator={"kind": "row", "row": i},
                technology=fact.get("technology", doc.get("technology")),
            )
        )
    return out


_EXTRACTORS = {
    "procurement_table": _extract_procurement_table,
    "policy_clauses": _extract_policy_clauses,
    "assertions": _extract_assertions,
}


def extract_documents(parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Extract every P17 claim from a fixture's document set (the ADR-071 dispatcher).

    A pure function of the parsed capture: the ``pathway_family`` selects the family, and
    each document's ``kind`` selects the parser-layer extractor. Every claim routes through
    :func:`pathway_claim`, so both epistemic guards run for every claim.
    """
    family = str(parsed["pathway_family"])
    source_id = pathway_family_source(family)
    out: list[Mapping[str, Any]] = []
    for doc in parsed.get("documents", []):
        ctx = _document_context(doc, family, source_id)
        kind = str(doc["kind"])
        extractor = _EXTRACTORS.get(kind)
        if extractor is None:
            raise ValueError(f"unknown pathway document kind {kind!r} (document {doc.get('id')!r})")
        out.extend(extractor(doc, ctx))
    return out


def parse_pathways(data: bytes) -> dict[str, Any]:
    """Parse a pathways fixture capture (pure function of the bytes)."""
    payload = json.loads(data.decode("utf-8"))
    if "pathway_family" not in payload:
        raise ValueError("a pathways capture must carry a 'pathway_family' (§46, P21.9)")
    return payload


# --- the connector ------------------------------------------------------------


@register
class PathwaysConnector(Connector):
    """The `pathways` connector: Stage-5 P17 pathway population (§46, P21.9, ADR-071).

    One connector, three per-family extractors (ADR-071). Runs on the P04.1 eight-stage
    framework; ``parse``/``extract``/``normalize`` are pure functions of the capture that
    build typed, evidenced P17 claims through the ADR-033-deferred parser layers and the
    procured≠deployed epistemic guard (RISK-P21-16). The sources stay LINK-posture until a
    packet + flip, so a live run against them is refused at the loader gate (exit 3);
    replay/shadow run over committed fixtures with no network.
    """

    name = "pathways"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        return parse_pathways(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return extract_documents(parsed)

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        # The claims are already typed+evidenced by pathway_claim; normalize stamps the
        # connector vocabulary version so a versioned re-extraction is a new interpretation.
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
