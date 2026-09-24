# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Shared machinery for the three OKC document connectors (LIVE.1a, GL-LIVE-01, P23.5).

The OKC vertical slice (P06.1) encoded three document sources the fixtures assert
claims for but no live connector exercised — `okc_procurement` (executed contracts),
`okcpd_policy` (the OKCPD Operations Manual), and `ok_statute` (Oklahoma statutory
text). RIGHTS.1 (P21.1 re-run) flipped all three to `ingestion_permitted=true`
(HG-03), so the composed pipeline can now fetch → capture → parse → emit the same
claims the fixtures encode, byte-identically under shadow replay.

This module owns the machinery the three connector modules share so the eight-stage
framework boilerplate is not triplicated (the same reasoning as ADR-071's
one-connector-three-extractors, applied here as one base + three registered
subclasses because each OKC source is a distinct registry row with its own predicate
allowlist):

* **The document capture shape and the sig-parsing extractors** — a procurement
  document reaches this layer as an extracted text grid read by the layer-4 table
  engine (:mod:`parsing.tables`); a policy/statute document is prose organised into
  numbered clauses read by the layer-3 clause locator (:mod:`parsing.clauses`). The
  document genre is **re-derived from the text** (:func:`parsing.genre.classify_genre`),
  never trusted from a fixture label.
* **The predicate allowlist as a hard schema gate** (SIG-INGEST-033): each connector
  may write only its declared predicate surface; anything else is refused at ingest.
* **The Part VIII guard** (§0.7 / §43.2 / §43.3 / §43.4, RISK-P0-08): every parsed
  claim routes through :func:`okc_claim`, which (1) refuses any predicate/value that
  carries a plate / per-trip / per-person / per-search token or a categorically
  excluded kind (:func:`assert_part_viii_safe`), (2) routes any person-named claim
  through the five-prong officer-naming test and refuses it by default
  (:func:`assert_person_naming_permitted`), and (3) stamps the claim's sensitivity
  class + geospatial publication tier (:func:`policy.sensitivity`). A test fails if
  any prong of the guard is removed.

The three sources are green (RIGHTS.1); a `run --mode live` fetches through the
shared politeness layer into the OCFL capture store (P21.3 owns the transport), and
`replay`/`shadow` run over the committed fixtures under network isolation and never
fetch (SIG-INGEST-018/019).
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
from parsing.genre import DocumentGenre, classify_genre
from parsing.tables import parse_table, table_claims
from policy.officer import (
    OfficerNamingProngs,
    ReviewerConcurrence,
    evaluate_officer_naming,
)
from policy.publication import is_categorically_excluded
from policy.sensitivity import SensitivityClass, geo_tier_for

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext

__all__ = [
    "OKC_DOCUMENTS_VOCAB",
    "PartVIIIViolation",
    "PredicateNotAllowed",
    "OfficerNamingRefused",
    "DocumentContext",
    "OkcDocumentConnector",
    "assert_part_viii_safe",
    "assert_predicate_allowed",
    "assert_person_naming_permitted",
    "connector_config",
    "default_sensitivity_class",
    "forbidden_tokens",
    "okc_claim",
    "parse_okc_document",
    "person_naming_predicates",
    "predicate_allowlist",
    "vocab",
    "vocab_version",
]

OKC_DOCUMENTS_VOCAB = "okc_documents_vocab"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned OKC-document connector vocabulary (``data/okc_documents_vocab.toml``)."""
    return load_table(OKC_DOCUMENTS_VOCAB)


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def connector_config(connector_name: str) -> Mapping[str, Any]:
    """The per-connector config block (source id, genre, extractor, allowlist)."""
    connectors = vocab()["connectors"]
    if connector_name not in connectors:
        raise KeyError(
            f"no OKC document connector config for {connector_name!r}; known: {sorted(connectors)}"
        )
    return connectors[connector_name]


def predicate_allowlist(connector_name: str) -> frozenset[str]:
    """The predicates ``connector_name`` may write (§11/§46-flavoured, SIG-INGEST-033)."""
    return frozenset(connector_config(connector_name)["predicate_allowlist"])


def default_sensitivity_class() -> SensitivityClass:
    """The sensitivity class stamped on every OKC document claim (§43.3, SIG-PUB-006)."""
    return SensitivityClass(str(vocab()["default_sensitivity_class"]))


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: a connector tried to write outside its predicate allowlist."""


def assert_predicate_allowed(connector_name: str, predicate: str) -> str:
    """Return ``predicate`` if in ``connector_name``'s allowlist, else raise (SIG-INGEST-033)."""
    allowed = predicate_allowlist(connector_name)
    if predicate not in allowed:
        raise PredicateNotAllowed(
            f"the {connector_name!r} connector may write only {sorted(allowed)} "
            f"(SIG-INGEST-033); {predicate!r} is outside the allowlist — the D6 "
            "admissibility filter enforced at ingest."
        )
    return predicate


# --- the Part VIII guard (§0.7 / §43.2 / §43.4, RISK-P0-08) --------------------


class PartVIIIViolation(Exception):
    """Raised when a claim carries plate / per-trip / per-person / per-search content.

    The mechanical form of the Part VIII §0.7 guarantee for the OKC document
    connectors: they emit institutional facts (contracts, policy clauses, statutes)
    ONLY. A predicate or a raw value carrying a plate, per-trip, per-person, or
    per-search token — or a categorically excluded kind (§43.2, SIG-PUB-002/003) —
    is refused at the ingest boundary, named so the P0 defect is auditable
    (RISK-P0-08).
    """


class OfficerNamingRefused(PartVIIIViolation):
    """Raised when a person-named claim fails the officer-naming test (§43.4).

    A subclass of :class:`PartVIIIViolation` (a person-named claim published without
    the five prongs + two-reviewer concurrence is a Part VIII breach). The default is
    no-publish, so a person-named claim with no recorded concurrence is refused.
    """


def forbidden_tokens() -> tuple[str, ...]:
    """The Part VIII forbidden content tokens (§0.7 / §43.2, RISK-P0-08)."""
    return tuple(str(t).lower() for t in vocab()["forbidden_tokens"])


def person_naming_predicates() -> frozenset[str]:
    """The predicates that name a natural person and trigger the officer test (§43.4)."""
    return frozenset(str(p) for p in vocab()["person_naming_predicates"])


def _offending_token(text: str) -> str | None:
    lowered = str(text).lower()
    for token in forbidden_tokens():
        if token in lowered:
            return token
    return None


def assert_part_viii_safe(predicate: str, raw_value: str) -> None:
    """Reject any plate / per-trip / per-person / per-search / excluded content (§0.7).

    Scans the predicate id AND the verbatim raw value for a forbidden token, and
    refuses a predicate whose name is a categorically excluded kind
    (:func:`policy.publication.is_categorically_excluded`). This is the hard
    mechanical form of "no plate/trip/per-person data" the OKC document connectors
    must hold: the guard runs for EVERY claim before it is built.
    """
    if is_categorically_excluded(predicate):
        raise PartVIIIViolation(
            f"predicate {predicate!r} is a categorically excluded kind (§43.2, "
            "SIG-PUB-002/003); no balancing test applies and it MUST NOT be stored."
        )
    for field_name, text in (("predicate", predicate), ("raw_value", raw_value)):
        token = _offending_token(text)
        if token is not None:
            raise PartVIIIViolation(
                f"OKC document {field_name} {text!r} matches the forbidden Part VIII "
                f"token {token!r}; the connectors emit institutional facts ONLY — no "
                "plate / per-trip / per-person / per-search data is ever stored "
                "(§0.7, §43.2, RISK-P0-08)."
            )


def assert_person_naming_permitted(
    predicate: str,
    *,
    prongs: OfficerNamingProngs | None = None,
    reviewers: tuple[ReviewerConcurrence, ...] = (),
) -> None:
    """Route a person-named claim through the five-prong officer-naming test (§43.4).

    A non-person-naming predicate is unaffected. A person-naming predicate MUST pass
    every prong of :func:`policy.officer.evaluate_officer_naming` with two independent
    reviewer concurrences (SIG-PUB-007/008); any failure — including the default of no
    prongs + no reviewers — refuses the claim (:class:`OfficerNamingRefused`). The OKC
    document connectors never emit a person-named claim; the gate is here so a future
    fixture cannot smuggle one past Part VIII.
    """
    if predicate not in person_naming_predicates():
        return
    decision = evaluate_officer_naming(
        prongs or OfficerNamingProngs(False, False, False, False, False),
        reviewers,
    )
    if not decision.permitted:
        raise OfficerNamingRefused(
            f"predicate {predicate!r} names a natural person; the officer-naming test "
            f"refuses publication (default no-publish): {decision.reason} "
            "(§43.4, SIG-PUB-007/008)."
        )


# --- the OKC document claim shape ---------------------------------------------


@dataclass(frozen=True)
class DocumentContext:
    """The provenance of one OKC source document a claim was read from (P1–P3, §3.1)."""

    connector: str
    source_id: str
    source_url: str
    retrieved_date: str
    genre: DocumentGenre
    subject_id: str


def okc_claim(
    ctx: DocumentContext,
    *,
    predicate: str,
    value: Any,
    raw_value: str,
    extraction_method: str,
    locator: Mapping[str, Any],
    subject_id: str | None = None,
) -> dict[str, Any]:
    """Build one typed, evidenced, Part VIII-guarded OKC document claim.

    Every claim is **typed** (predicate in the connector's allowlist), **evidenced**
    (source url + retrieval date + the parser-layer locator + extraction method),
    **dated** (``observed_at``), and **Part VIII-safe** (the plate/trip/person guard
    and the officer-naming gate run HERE, so no per-source code path can bypass them),
    and carries its published **sensitivity class + geospatial tier** (§43.3). The raw
    literal is preserved verbatim beside the typed value (P2, SIG-PARSE-004).
    """
    assert_predicate_allowed(ctx.connector, predicate)
    assert_part_viii_safe(predicate, raw_value)
    assert_person_naming_permitted(predicate)
    sensitivity = default_sensitivity_class()
    return {
        "record_kind": "claim",
        "connector": ctx.connector,
        "source_id": ctx.source_id,
        "document_genre": ctx.genre.value,
        "subject_id": subject_id or ctx.subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,  # P2 — the source literal preserved verbatim
        "sensitivity_class": sensitivity.value,
        "geo_tier": geo_tier_for(sensitivity),
        "evidence": {
            "source_url": ctx.source_url,
            "retrieved_date": ctx.retrieved_date,
            "extraction_method": extraction_method,
            "locator": dict(locator),
        },
        "observed_at": ctx.retrieved_date,
        "source_attribution": ctx.source_id,
    }


# --- the per-kind sig-parsing extractors --------------------------------------


def _document_context(connector_name: str, doc: Mapping[str, Any]) -> DocumentContext:
    """Derive the document context, re-deriving the genre from the text (never a label).

    The genre is computed from the document's own text via
    :func:`parsing.genre.classify_genre`; a fixture ``genre`` label that disagrees
    with the derived genre is rejected, so a document cannot be relabelled to unlock a
    predicate surface it does not belong to.
    """
    cfg = connector_config(connector_name)
    text = str(doc.get("text", ""))
    derived = classify_genre(str(doc.get("id", "document")), text.encode("utf-8")).genre
    expected = DocumentGenre(str(cfg["genre"]))
    declared = doc.get("genre")
    if declared is not None and DocumentGenre(str(declared)) is not expected:
        raise ValueError(
            f"document {doc.get('id')!r} is labelled {declared!r} but the {connector_name!r} "
            f"connector reads {expected.value!r} documents (SIG-INGEST-033)."
        )
    if derived is not DocumentGenre.UNKNOWN and derived is not expected:
        raise ValueError(
            f"document {doc.get('id')!r} text classifies as {derived.value!r} but the "
            f"{connector_name!r} connector reads {expected.value!r}; the genre used is the "
            "one DERIVED from the text, not the fixture label (no relabelling)."
        )
    return DocumentContext(
        connector=connector_name,
        source_id=str(cfg["source_id"]),
        source_url=str(doc["source_url"]),
        retrieved_date=str(doc.get("retrieved_date", "2026-09-01")),
        genre=expected,
        subject_id=str(doc["subject_id"]),
    )


def _extract_procurement_table(
    connector_name: str, doc: Mapping[str, Any], ctx: DocumentContext
) -> list[dict[str, Any]]:
    """Read a procurement table via the layer-4 engine into vendor/product/contract claims."""
    table = parse_table(str(doc["text"]).encode("utf-8"))
    subjects = [ctx.subject_id] * len(table.rows)
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
    out: list[dict[str, Any]] = []
    for pc in parsed_claims:
        out.append(
            okc_claim(
                ctx,
                predicate=pc.predicate,
                value=pc.value.parsed,
                raw_value=pc.value.raw_value,
                extraction_method=pc.extraction_method,
                locator=pc.locator.to_row(),
                subject_id=pc.subject,
            )
        )
    return out


def _extract_policy_clauses(
    connector_name: str, doc: Mapping[str, Any], ctx: DocumentContext
) -> list[dict[str, Any]]:
    """Read a policy/statute document via the layer-3 clause locator into clause claims."""
    clauses = locate_clauses(str(doc["text"]).encode("utf-8"))
    out: list[dict[str, Any]] = []
    for fact in doc["clauses"]:
        clause = find_clause(clauses, str(fact["clause"]))
        if clause is None:
            raise ValueError(
                f"clause fact cites clause {fact['clause']!r} not found in document "
                f"{doc.get('id')!r} (SIG-PARSE-003)"
            )
        pc = clause_claim(
            clause,
            subject=ctx.subject_id,
            predicate=str(fact["predicate"]),
            value=str(fact["value"]),
            value_kind=fact.get("value_kind", "text"),
        )
        out.append(
            okc_claim(
                ctx,
                predicate=pc.predicate,
                value=pc.value.parsed,
                raw_value=pc.value.raw_value,
                extraction_method=pc.extraction_method,
                locator=pc.locator.to_row(),
            )
        )
    return out


_EXTRACTORS = {
    "procurement_table": _extract_procurement_table,
    "policy_clauses": _extract_policy_clauses,
}


def parse_okc_document(data: bytes) -> dict[str, Any]:
    """Parse an OKC document capture (pure function of the bytes)."""
    payload = json.loads(data.decode("utf-8"))
    if "connector" not in payload or "documents" not in payload:
        raise ValueError(
            "an OKC document capture must carry a 'connector' and a 'documents' list "
            "(LIVE.1a, GL-LIVE-01)."
        )
    return payload


def extract_documents(connector_name: str, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Extract every claim from a fixture's document set (pure function of the capture).

    Each document's ``kind`` selects the sig-parsing extractor (table vs clause), and
    every claim routes through :func:`okc_claim`, so the predicate allowlist and the
    Part VIII guard run for every claim.
    """
    cfg = connector_config(connector_name)
    default_kind = str(cfg["extractor"])
    out: list[Mapping[str, Any]] = []
    for doc in parsed.get("documents", []):
        ctx = _document_context(connector_name, doc)
        kind = str(doc.get("kind", default_kind))
        extractor = _EXTRACTORS.get(kind)
        if extractor is None:
            raise ValueError(
                f"unknown OKC document kind {kind!r} (document {doc.get('id')!r}); "
                f"known: {sorted(_EXTRACTORS)}"
            )
        out.extend(extractor(connector_name, doc, ctx))
    return out


# --- the shared connector base ------------------------------------------------


class OkcDocumentConnector(Connector):
    """The shared eight-stage base for the three OKC document connectors (P23.5).

    A subclass sets :attr:`name` to its connector name (which keys its
    :func:`connector_config`). ``discover``/``fetch`` acquire the cited document
    through the shared politeness layer; ``parse``/``extract``/``normalize`` are pure
    functions of the capture that build typed, evidenced, Part VIII-guarded claims via
    the sig-parsing layers. The source is green (RIGHTS.1); replay/shadow run over the
    committed fixture with no network (SIG-INGEST-018/019).
    """

    name = "okc_document"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        return parse_okc_document(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return extract_documents(self.name, parsed)

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        # The claims are already typed + evidenced + guarded by okc_claim; normalize
        # stamps the connector vocabulary version so a versioned re-extraction is a new
        # interpretation (§20, SIG-INGEST-017).
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
