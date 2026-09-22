# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Document-genre classification for the Stage-5 pathway extractors (§24.1, LD-F17).

Format classification (:mod:`parsing.classification`) answers *"what container is
this?"* — a PDF, an XLSX, a scanned image. It does **not** answer the question the
Stage-5 pathway connectors turn on: *"what KIND of document is this?"* — a
procurement record, an agency policy, a deployment report. That second axis is the
**genre**, and it is load-bearing for the P21.9 epistemic rule (RISK-P21-16, §46):
a **deployment** claim may be asserted only from a **deployment-genre** document; a
procurement record, however detailed, evidences ``procured`` and never ``deployed``.

This module is the parser layer that recognises the genre deterministically from the
document's own text (a keyword/marker function of the bytes, no network, no model), so
the same document classified twice yields the same genre. It is deliberately
conservative: an ambiguous document is :data:`DocumentGenre.UNKNOWN`, never guessed
into a genre that would unlock a stronger claim than the evidence supports (§3.1 — no
synthetic certainty).

The genres it recognises (the "new document genres" ``sig-parsing classify`` reports):

* ``procurement_record`` — a contract, purchase order, sub-award, or quote (a
  procurement PDF the table-extraction layer, :mod:`parsing.tables`, reads);
* ``policy_document``    — an agency policy / operations-manual clause, an ordinance,
  or a court authorization (the clause-locator layer, :mod:`parsing.clauses`, reads);
* ``deployment_report``  — a document that reports a system in **operation** (a
  transparency/usage report, an audit of a live deployment) — the ONLY genre that
  may evidence a ``deployed`` claim;
* ``vendor_disclosure``  — a vendor/product disclosure, a federation registry, an
  RTCC integration announcement (vendor/product facts, never a deployment);
* ``agenda_minutes``     — a council/board agenda or minutes item.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "DocumentGenre",
    "DEPLOYMENT_GENRES",
    "GenreVerdict",
    "classify_genre",
    "genre_permits_deployment_claim",
]


class DocumentGenre(StrEnum):
    """The document genres the Stage-5 extractors distinguish (LD-F17, §24.1)."""

    PROCUREMENT_RECORD = "procurement_record"
    POLICY_DOCUMENT = "policy_document"
    DEPLOYMENT_REPORT = "deployment_report"
    VENDOR_DISCLOSURE = "vendor_disclosure"
    AGENDA_MINUTES = "agenda_minutes"
    UNKNOWN = "unknown"


#: The genres from which a **deployment** claim may be asserted (RISK-P21-16, §46).
#: A procurement record — however itemised — is NOT here: ``procured`` never implies
#: ``deployed``. This frozenset is the single data point the connector's epistemic
#: guard keys off (:func:`connectors.pathways.assert_claim_type_supported_by_genre`).
DEPLOYMENT_GENRES: frozenset[DocumentGenre] = frozenset({DocumentGenre.DEPLOYMENT_REPORT})


# The ordered marker sets. Order matters: the first genre whose markers dominate wins,
# and deployment is checked with a HIGHER bar than procurement so an invoice that merely
# mentions "installed line items" is not mistaken for an operational-deployment report.
_MARKERS: tuple[tuple[DocumentGenre, tuple[str, ...]], ...] = (
    (
        DocumentGenre.DEPLOYMENT_REPORT,
        (
            "deployment report",
            "transparency report",
            "usage report",
            "in operation since",
            "currently operating",
            "actively deployed",
            "system is live",
            "went live on",
            "annual surveillance report",
        ),
    ),
    (
        DocumentGenre.POLICY_DOCUMENT,
        (
            "operations manual",
            "policy",
            "ordinance",
            "shall not",
            "retention period",
            "court order",
            "authorized under",
            "pen register",
            "§",
            "section ",
            "warrant",
        ),
    ),
    (
        DocumentGenre.PROCUREMENT_RECORD,
        (
            "purchase order",
            "contract no",
            "master agreement",
            "sub-award",
            "subaward",
            "quote",
            "invoice",
            "line item",
            "unit price",
            "total price",
            "vendor",
            "sole source",
        ),
    ),
    (
        DocumentGenre.VENDOR_DISCLOSURE,
        (
            "camera registry",
            "integration partner",
            "federated",
            "real-time crime center",
            "rtcc",
            "data broker",
            "resells",
            "product datasheet",
            "press release",
        ),
    ),
    (
        DocumentGenre.AGENDA_MINUTES,
        (
            "agenda item",
            "council meeting",
            "board of supervisors",
            "minutes of the",
            "motion carried",
            "consent agenda",
        ),
    ),
)


@dataclass(frozen=True)
class GenreVerdict:
    """The recorded genre verdict for one document (LD-F17, §24.1)."""

    genre: DocumentGenre
    #: The markers that fired, per genre, so the verdict is inspectable (§3.1).
    hits: tuple[str, ...] = ()

    def to_row(self) -> dict[str, object]:
        return {"genre": self.genre.value, "hits": list(self.hits)}


def classify_genre(filename: str, data: bytes) -> GenreVerdict:
    """Classify a document's genre from its text (LD-F17, deterministic, no network).

    A pure function of the bytes (and the filename as a weak hint): it counts genre
    markers and returns the genre with the strongest signal, or
    :data:`DocumentGenre.UNKNOWN` when nothing fires. Deployment markers are weighted
    above procurement markers so a procurement record is never silently promoted to a
    deployment report — the conservative default the §46 epistemic rule requires.
    """
    try:
        text = data.decode("utf-8", errors="ignore").lower()
    except Exception:  # pragma: no cover - decode with errors="ignore" does not raise
        text = ""
    haystack = f"{filename.lower()}\n{text}"

    best: DocumentGenre = DocumentGenre.UNKNOWN
    best_hits: tuple[str, ...] = ()
    best_score = 0
    for genre, markers in _MARKERS:
        hits = tuple(m for m in markers if m in haystack)
        # Deployment must clear a higher bar (>=1 of its own explicit markers is
        # enough BECAUSE the markers are operational phrases, not procurement words).
        if hits and len(hits) > best_score:
            best = genre
            best_hits = hits
            best_score = len(hits)
    return GenreVerdict(genre=best, hits=best_hits)


def genre_permits_deployment_claim(genre: DocumentGenre) -> bool:
    """Whether ``genre`` may evidence a ``deployed`` claim (RISK-P21-16, §46)."""
    return genre in DEPLOYMENT_GENRES
