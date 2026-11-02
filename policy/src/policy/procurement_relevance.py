# SPDX-License-Identifier: Apache-2.0
"""Procurement-notice surveillance relevance — K2 GX-04 / H-13, ticket P36.30
(R11-K13-GX-04).

ONE classification derivation (the same posture as ``policy.labels``' L-1
law): the exporter, buyer pages, overview builders and the J2 capstone
journey all read this module's verdict — nothing re-derives whether a
procurement notice is surveillance-relevant.

The rule (K2 GX-04; the plan cell **D-K2-5 [B-22] = as recommended:
exclude unclassified procurement**, an answered decision carried verbatim —
implemented, never re-decided):

* **relevant** (``surveillance_related``) — the notice carries a
  ``matched_keyword`` claim (the extraction-time verbatim scan's match of
  record — a reviewed term id, never a recall hint) or a product/service
  classification claim (``products`` / ``cpv_code`` / ``naics`` /
  ``psc_code`` / ``product_or_service_code``) matching the **reviewed**
  vocabulary: the verified CPV code set and the reviewed keyword/pattern
  sets in the connectors' committed vocab tables, read as data — never a
  guessed code or a re-derived term list.
* **not classified** (``not_classified``) — everything else, including a
  notice with no classification claims at all. An unclassified notice is
  never silently dropped: it is excluded from the surveillance surfaces
  (the O1 supply graphs and surveillance collections landing under
  GX-08a/GX-06) and surfaces only as a buyer-page row carrying the K2
  H-13 label ``not classified as surveillance-related``.

Fail-closed posture: only a *reviewed* input classifies a notice. A code no
reviewed set names, a term the vocabulary does not carry, and a subject
outside the notice family all land on ``not_classified`` — the absence is
typed and visible, never a guess (SIG-ENG-042). The NAICS slot is declared
and empty today: no reviewed NAICS code set exists in the connector vocab
tables (the classification of new sources is I8's — ``data/k13_tickets.csv``
GX-04 depends); it joins ``naics_codes`` the day a reviewed set lands.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

#: The emitted ``web/procurement_relevance.json`` contract (P36.30).
SCHEMA = "sig.procurement-relevance/1"

#: K2 §7 H-13 — the buyer-page row label, verbatim. ONE string everywhere:
#: surfaces read ``buyer_label``, never reword it.
UNCLASSIFIED_LABEL = "not classified as surveillance-related"

#: The closed relevance vocabulary (a verdict, never an epistemic claim:
#: ``not_classified`` records "no reviewed signal found", never
#: "not surveillance" — NEW-7's honest surface).
RELEVANCE_VALUES: tuple[str, ...] = ("surveillance_related", "not_classified")

#: The closed basis vocabulary — which input kind fired the verdict.
BASIS_VALUES: tuple[str, ...] = ("matched_keyword", "product_code", "product_text", "none")

#: The claim predicates the rule reads. Today the connectors emit
#: ``matched_keyword`` (verbatim-scan term ids) and ``products`` (verbatim
#: product/service literals — CPV codes on TED, names elsewhere); the code
#: predicates join the input set the day a connector emits them (I8).
INPUT_PREDICATES: tuple[str, ...] = (
    "matched_keyword",
    "products",
    "cpv_code",
    "naics",
    "naics_code",
    "psc_code",
    "product_or_service_code",
)

#: Predicates whose values are *classification codes/literals* (matched
#: against the reviewed code sets + term patterns), distinct from
#: ``matched_keyword`` whose values are already reviewed term ids.
CODE_PREDICATES: tuple[str, ...] = tuple(p for p in INPUT_PREDICATES if p != "matched_keyword")

#: The subject families the rule covers — the K2 "procurement notice"
#: kind. ``contract:`` subjects are a different K2 kind whose data contract
#: lands under GX-05b; they are deliberately out of scope here.
NOTICE_SUBJECT_PREFIXES: tuple[str, ...] = ("procurement_notice:", "notice:")

#: The reviewed vocabulary tables the loader reads — data, not code (the
#: same posture ``exports.jurisdictions``/``boundary_pack`` take over the
#: committed connectors TOMLs; ``connectors`` is not a policy dependency).
_AGENDA_VOCAB = "agenda_content_vocab.toml"
_PROCUREMENT_VOCAB = "procurement_vocab.toml"

#: ``connectors/src/connectors/data`` resolved repo-relative — identical to
#: ``exports.jurisdictions.CONNECTOR_DATA_DIR``. Callers may override via
#: ``data_dir`` (tests inject fabricated tables instead).
_CONNECTOR_DATA_DIR = Path(__file__).resolve().parents[3] / "connectors/src/connectors/data"


def is_notice_subject(subject_key: str | None) -> bool:
    """True when ``subject_key`` names a procurement notice (the K2 kind)."""
    return bool(subject_key) and str(subject_key).startswith(NOTICE_SUBJECT_PREFIXES)


@dataclass(frozen=True)
class ReviewedTerm:
    """One reviewed surveillance term: its id, kind and compiled patterns."""

    id: str
    kind: str
    label: str
    patterns: tuple[re.Pattern[str], ...] = field(repr=False, compare=False)


@dataclass(frozen=True)
class ReviewedVocabulary:
    """The reviewed classification inputs — loaded from the connector vocab
    tables, never duplicated or re-derived (one vocabulary, one derivation)."""

    terms: tuple[ReviewedTerm, ...]
    #: Normalised code → reviewed label (CPV today).
    cpv_codes: Mapping[str, str]
    #: Normalised code → reviewed label. Empty by honest record — no
    #: reviewed NAICS set exists in the connector vocab tables today.
    naics_codes: Mapping[str, str]
    #: The vocabulary tables this set derives from (provenance).
    sources: tuple[str, ...]
    #: ``table name → vocab_version`` for each source table.
    versions: Mapping[str, str]
    #: sha256 over the source table bytes — the doc's evidence binding.
    digest: str = ""

    def scan_text(self, text: str) -> tuple[str, ...]:
        """The term ids whose reviewed patterns match ``text`` (deterministic)."""
        hits: list[str] = []
        for term in self.terms:
            if any(p.search(text) for p in term.patterns):
                hits.append(term.id)
        return tuple(hits)


def _normalise_code(value: str) -> str:
    """The leading classification-code digits — ``35120000-3`` → ``35120000``.

    TED values carry a CPV check digit after ``-``; the match is exact-only
    (a hierarchical-prefix guess is a classification the review never
    made), so only the code's own digits normalise, never the check digit.
    """
    m = re.match(r"\d+", str(value).strip())
    return m.group(0) if m else ""


def _compile_literals(literals: Sequence[str]) -> tuple[re.Pattern[str], ...]:
    """Word-boundary literal patterns — the reviewed false-positive class
    (a bare substring catches 'Brinc' inside 'Parsons Brinckerhoff')."""
    out: list[re.Pattern[str]] = []
    for lit in literals:
        text = str(lit).strip()
        if text:
            out.append(re.compile(r"\b" + re.escape(text) + r"\b", re.IGNORECASE))
    return tuple(out)


def _term(entry: Mapping[str, Any], *, id_fallback: str) -> ReviewedTerm | None:
    """One TOML term row (``id``/``kind``/``label``/``patterns``) → ReviewedTerm."""
    tid = str(entry.get("id") or id_fallback)
    pats = tuple(re.compile(str(p), re.IGNORECASE) for p in entry.get("patterns", ()))
    pats = pats + _compile_literals(tuple(str(t) for t in (entry.get("terms") or ())))
    if not pats:
        return None
    return ReviewedTerm(
        id=tid,
        kind=str(entry.get("kind") or ""),
        label=str(entry.get("label") or tid),
        patterns=pats,
    )


def vocabulary_from_tables(
    agenda_vocab: Mapping[str, Any],
    procurement_vocab: Mapping[str, Any],
    *,
    digest: str = "",
) -> ReviewedVocabulary:
    """Build the reviewed vocabulary from the two committed TOML tables.

    Pure: given the parsed tables the output is deterministic. The term set
    is the agenda-content verbatim-scan vocabulary (the ``matched_keyword``
    match of record) + the TED sweep's keyword patterns + the procurement
    acquisition-term classes' reviewed literals; the code set is the
    verified ``ted_eu_sweep.cpv_codes`` list. NAICS lands empty — no
    reviewed set exists today (recorded, never fabricated).
    """
    terms: list[ReviewedTerm] = []
    for entry in agenda_vocab.get("terms", ()):
        t = _term(entry, id_fallback="")
        if t is not None:
            terms.append(t)
    ted = procurement_vocab.get("ted_eu_sweep", {}) or {}
    for entry in ted.get("keywords", ()):
        t = _term(entry, id_fallback="")
        if t is not None:
            terms.append(t)
    for name, entry in (procurement_vocab.get("terms", {}) or {}).items():
        t = _term(entry, id_fallback=str(name))
        if t is not None:
            terms.append(t)
    cpv = {
        _normalise_code(str(row["code"])): str(row.get("label") or row["code"])
        for row in ted.get("cpv_codes", ())
        if row.get("code")
    }
    versions = {
        _AGENDA_VOCAB: str(agenda_vocab.get("vocab_version") or ""),
        _PROCUREMENT_VOCAB: str(procurement_vocab.get("vocab_version") or ""),
    }
    return ReviewedVocabulary(
        terms=tuple(terms),
        cpv_codes=cpv,
        naics_codes={},
        sources=(_AGENDA_VOCAB, _PROCUREMENT_VOCAB),
        versions=versions,
        digest=digest,
    )


def load_reviewed_vocabulary(data_dir: str | Path | None = None) -> ReviewedVocabulary:
    """Load the committed reviewed vocabulary tables (cached).

    ``data_dir`` defaults to the committed ``connectors/src/connectors/data``
    directory — read as data via stdlib ``tomllib`` (the
    ``exports.jurisdictions`` posture; ``connectors`` is not a policy
    dependency). The digest binds the emitted document to the exact
    reviewed bytes (SIG-ENG-042).
    """
    root = Path(data_dir) if data_dir is not None else _CONNECTOR_DATA_DIR
    return _load_cached(str(root))


@cache
def _load_cached(root: str) -> ReviewedVocabulary:
    data = Path(root)
    agenda_bytes = (data / _AGENDA_VOCAB).read_bytes()
    procurement_bytes = (data / _PROCUREMENT_VOCAB).read_bytes()
    digest = hashlib.sha256(agenda_bytes + procurement_bytes).hexdigest()
    return vocabulary_from_tables(
        tomllib.loads(agenda_bytes.decode("utf-8")),
        tomllib.loads(procurement_bytes.decode("utf-8")),
        digest=digest,
    )


@dataclass(frozen=True)
class NoticeRelevance:
    """One ``sig.procurement-relevance/1`` row — a notice's verdict."""

    entity_id: str | None
    subject_key: str
    kind: str
    relevance: str  # RELEVANCE_VALUES
    bases: tuple[str, ...]  # BASIS_VALUES — ("none",) when nothing fired
    matched: tuple[str, ...]  # the firing term ids / codes
    buyer_label: str | None  # UNCLASSIFIED_LABEL when not_classified, else None

    def row(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "subject_key": self.subject_key,
            "kind": self.kind,
            "relevance": self.relevance,
            "bases": list(self.bases),
            "matched": list(self.matched),
            "buyer_label": self.buyer_label,
        }


def _values(fields: Mapping[str, Any] | None, *predicates: str) -> list[str]:
    """Every non-empty value across ``predicates`` — str or list-shaped."""
    out: list[str] = []
    for pred in predicates:
        raw = (fields or {}).get(pred)
        if raw is None:
            continue
        vals = raw if isinstance(raw, (list, tuple)) else [raw]
        for v in vals:
            text = str(v).strip()
            if text:
                out.append(text)
    return out


def classify_notice(
    subject_key: str,
    fields: Mapping[str, Any] | None = None,
    *,
    vocab: ReviewedVocabulary | None = None,
    entity_id: str | None = None,
    kind: str = "notice",
) -> NoticeRelevance:
    """The ONE classification — K2 GX-04 over a notice's claim fields.

    ``fields`` maps predicate → value or value list (the export feeds it the
    ``notice_relevance_facts`` read; ``matched_keyword`` values are the
    reviewed term ids, ``products``/code values the verbatim literals).
    The verdict is a pure function of the inputs + the reviewed vocabulary —
    the same notice classifies identically on every surface.
    """
    vocabulary = vocab if vocab is not None else load_reviewed_vocabulary()
    bases: list[str] = []
    matched: list[str] = []

    def _hit(base: str, value: str) -> None:
        if base not in bases:
            bases.append(base)
        if value not in matched:
            matched.append(value)

    # 1. ``matched_keyword`` — the extraction-time verbatim scan already
    #    decided relevance; the claim value IS a reviewed term id.
    for value in _values(fields, "matched_keyword"):
        _hit("matched_keyword", value)

    # 2. Product/service classifications — codes first (exact match only:
    #    a hierarchical-prefix guess is a classification the review never
    #    made), then the verbatim literal against the reviewed patterns.
    for value in _values(fields, *CODE_PREDICATES):
        code = _normalise_code(value)
        if code and code in vocabulary.cpv_codes:
            _hit("product_code", f"cpv:{code}")
            continue
        if code and code in vocabulary.naics_codes:
            _hit("product_code", f"naics:{code}")
            continue
        for term_id in vocabulary.scan_text(value):
            _hit("product_text", term_id)

    if bases:
        return NoticeRelevance(
            entity_id=entity_id,
            subject_key=subject_key,
            kind=kind,
            relevance="surveillance_related",
            bases=tuple(bases),
            matched=tuple(matched),
            buyer_label=None,
        )
    return NoticeRelevance(
        entity_id=entity_id,
        subject_key=subject_key,
        kind=kind,
        relevance="not_classified",
        bases=("none",),
        matched=(),
        buyer_label=UNCLASSIFIED_LABEL,
    )


def relevance_doc(
    rows: Sequence[NoticeRelevance],
    *,
    generated_at: str,
    publication: str | None,
    vocab: ReviewedVocabulary | None = None,
) -> dict[str, Any]:
    """The ``sig.procurement-relevance/1`` document the export emits and
    every downstream surface filters through (D-K2-5 — unclassified
    procurement is excluded from the surveillance surfaces and shown only
    as a buyer-page row, never silently dropped).
    """
    vocabulary = vocab if vocab is not None else load_reviewed_vocabulary()
    emitted = [r.row() for r in rows]
    relevant = sum(1 for r in rows if r.relevance == "surveillance_related")
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "publication": publication,
        "rule": {
            "id": "R11-K13-GX-04",
            "decision": "D-K2-5 [B-22] = as recommended: exclude unclassified procurement",
            "inputs": list(INPUT_PREDICATES),
            "posture": (
                "unclassified notices appear only as buyer-page rows "
                "labelled 'not classified as surveillance-related' (K2 H-13)"
            ),
        },
        "vocabulary": {
            "sources": list(vocabulary.sources),
            "versions": dict(vocabulary.versions),
            "sha256": vocabulary.digest,
            "terms": len(vocabulary.terms),
            "cpv_codes": len(vocabulary.cpv_codes),
            "naics_codes": len(vocabulary.naics_codes),
        },
        "counts": {
            "notices": len(emitted),
            "surveillance_related": relevant,
            "not_classified": len(emitted) - relevant,
        },
        "rows": emitted,
    }


__all__ = [
    "BASIS_VALUES",
    "CODE_PREDICATES",
    "INPUT_PREDICATES",
    "NOTICE_SUBJECT_PREFIXES",
    "NoticeRelevance",
    "RELEVANCE_VALUES",
    "ReviewedTerm",
    "ReviewedVocabulary",
    "SCHEMA",
    "UNCLASSIFIED_LABEL",
    "classify_notice",
    "is_notice_subject",
    "load_reviewed_vocabulary",
    "relevance_doc",
    "vocabulary_from_tables",
]
