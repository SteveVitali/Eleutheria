# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for document-genre classification (LD-F17, P21.9).

The genre axis is load-bearing for the P21.9 epistemic rule (RISK-P21-16, §46): a
deployment claim may be asserted only from a deployment-genre document. These tests pin
that a procurement record is NEVER classified as a deployment report, that each new genre
is recognised deterministically, and that an ambiguous document stays ``unknown``.
"""

from __future__ import annotations

from parsing.genre import (
    DEPLOYMENT_GENRES,
    DocumentGenre,
    classify_genre,
    genre_permits_deployment_claim,
)


def _g(text: str, filename: str = "doc.txt") -> DocumentGenre:
    return classify_genre(filename, text.encode("utf-8")).genre


def test_procurement_record_is_recognised() -> None:
    genre = _g("Purchase Order 12345\nVendor | Product | Unit Price\nsole source award")
    assert genre is DocumentGenre.PROCUREMENT_RECORD


def test_policy_document_is_recognised() -> None:
    genre = _g("Operations Manual §5-118\nThe retention period shall not exceed 30 days.")
    assert genre is DocumentGenre.POLICY_DOCUMENT


def test_deployment_report_is_recognised() -> None:
    genre = _g("Annual Surveillance Report: the system is live and currently operating.")
    assert genre is DocumentGenre.DEPLOYMENT_REPORT


def test_vendor_disclosure_is_recognised() -> None:
    genre = _g("Press release: our real-time crime center integration partner federated feed")
    assert genre is DocumentGenre.VENDOR_DISCLOSURE


def test_agenda_minutes_is_recognised() -> None:
    genre = _g("Agenda item 7: council meeting consent agenda; motion carried")
    assert genre is DocumentGenre.AGENDA_MINUTES


def test_ambiguous_document_is_unknown_never_guessed() -> None:
    # §3.1 — no synthetic certainty: nothing fires, so the genre is UNKNOWN, not a guess
    # that would unlock a stronger claim than the evidence supports.
    assert _g("Hello, this is a plain note with no markers whatsoever.") is DocumentGenre.UNKNOWN


def test_procurement_is_never_promoted_to_deployment() -> None:
    # RISK-P21-16 core: an itemised procurement record — even one that lists installed
    # line items — must NOT be classified as a deployment report. procured != deployed.
    text = (
        "Contract No. C-2024-001\nVendor | Product | Line Item | Total Price\n"
        "Fusus | RTCC platform | camera integration | $250,000"
    )
    genre = _g(text)
    assert genre is DocumentGenre.PROCUREMENT_RECORD
    assert not genre_permits_deployment_claim(genre)


def test_only_deployment_report_permits_a_deployment_claim() -> None:
    assert DEPLOYMENT_GENRES == frozenset({DocumentGenre.DEPLOYMENT_REPORT})
    assert genre_permits_deployment_claim(DocumentGenre.DEPLOYMENT_REPORT)
    for other in (
        DocumentGenre.PROCUREMENT_RECORD,
        DocumentGenre.POLICY_DOCUMENT,
        DocumentGenre.VENDOR_DISCLOSURE,
        DocumentGenre.AGENDA_MINUTES,
        DocumentGenre.UNKNOWN,
    ):
        assert not genre_permits_deployment_claim(other)


def test_classification_is_deterministic() -> None:
    text = b"Operations Manual section 3: warrant required."
    assert classify_genre("p.txt", text).genre is classify_genre("p.txt", text).genre
