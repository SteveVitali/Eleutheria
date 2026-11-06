# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The rights-record consistency rule (P37.6 / ADR-235, SIG-INGEST-028/038).

A flipped row asserts a recorded human review: its ``review_packet`` resolves,
its notes carry the recorded ``FLIPPED <date>`` marker plus the review date,
and the ADR-194 resolver tuple (attribution / terms_url / an explicit
retrieval_date) is complete. Every check names the offending id; a regression
fails loud, never silently.
"""

from __future__ import annotations

import contextlib
import io
from datetime import date

from connectors.cli import main
from connectors.registry import (
    CompactStatus,
    CustodyPosture,
    RobotsPolicy,
    SourceKind,
    SourceRecord,
    sources,
)
from connectors.review import rights_record_consistency_violations
from policy.rights import RightsRecord

#: A real committed packet — existence is checked against the repo root.
_PACKET = "docs/build/reports/rights/okc_procurement.md"
#: The loader's retrieval_date fallback (connectors.registry._rights_record).
_FALLBACK = date(2026, 8, 20)


def _record(
    source_id: str,
    *,
    permitted: bool = True,
    review_packet: str = _PACKET,
    notes: str = "FLIPPED 2026-09-10 (GL-GATE-03) — the recorded answer. Reviewed 2026-09-10.",
    reviewed_on: date | None = date(2026, 9, 10),
    attribution: str = "test upstream",
    terms_url: str = "https://example.test/terms",
    retrieval_date: date = date(2026, 9, 9),
) -> SourceRecord:
    rights = RightsRecord(
        source_id=source_id,
        spdx="CC0-1.0",
        attribution=attribution,
        redistributable=True,
        derivative_permitted=True,
        terms_url=terms_url,
        retrieval_date=retrieval_date,
    )
    return SourceRecord(
        id=source_id,
        name=f"test {source_id}",
        source_kind=SourceKind.GOVERNMENT_PORTAL,
        homepage_url="https://example.test/",
        default_tier="R1",
        custody_posture=CustodyPosture.REFERENCE,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
        robots_policy=RobotsPolicy.HONOR,
        rights=rights,
        ingestion_permitted=permitted,
        rights_reviewed_by="licensing reviewer",
        rights_reviewed_on=reviewed_on,
        last_verified=reviewed_on,
        notes=notes,
        review_packet=review_packet,
    )


def test_a_fully_consistent_flip_is_not_a_violation() -> None:
    assert rights_record_consistency_violations([_record("t_ok")]) == []


def test_unpermitted_rows_are_never_violations() -> None:
    row = _record("t_gated", permitted=False, review_packet="", notes="")
    assert rights_record_consistency_violations([row]) == []


def test_missing_review_packet_is_a_violation_naming_the_id() -> None:
    (msg,) = rights_record_consistency_violations([_record("t_no_packet", review_packet="")])
    assert "t_no_packet" in msg
    assert "review_packet" in msg


def test_a_dead_review_packet_path_is_a_violation() -> None:
    (msg,) = rights_record_consistency_violations(
        [_record("t_dead_packet", review_packet="docs/build/reports/rights/no_such_packet.md")]
    )
    assert "t_dead_packet" in msg
    assert "resolves" in msg


def test_notes_without_the_flip_marker_are_a_violation() -> None:
    (msg,) = rights_record_consistency_violations(
        [_record("t_no_marker", notes="reviewed 2026-09-10; no marker recorded")]
    )
    assert "t_no_marker" in msg
    assert "FLIPPED" in msg


def test_notes_without_the_review_date_are_a_violation() -> None:
    # The review act and the flip act are distinct recorded events: the notes
    # carry the FLIPPED marker's date but not the rights_reviewed_on date.
    row = _record(
        "t_no_date",
        reviewed_on=date(2026, 9, 22),
        notes="FLIPPED 2026-10-25 (GATE-G5) — the review date is absent",
    )
    (msg,) = rights_record_consistency_violations([row])
    assert "t_no_date" in msg
    assert "rights_reviewed_on" in msg


def test_reviewed_then_flipped_dates_both_present_is_consistent() -> None:
    # The state_alpr pattern: REVIEWED 2026-09-22 … FLIPPED 2026-10-25.
    row = _record(
        "t_two_dates",
        reviewed_on=date(2026, 9, 22),
        notes="REVIEWED 2026-09-22 (P27.2). FLIPPED 2026-10-25 (GATE-G5).",
    )
    assert rights_record_consistency_violations([row]) == []


def test_empty_attribution_is_a_violation() -> None:
    (msg,) = rights_record_consistency_violations([_record("t_no_attr", attribution="")])
    assert "t_no_attr" in msg
    assert "rights.attribution" in msg


def test_empty_terms_url_is_a_violation() -> None:
    (msg,) = rights_record_consistency_violations([_record("t_no_terms", terms_url="")])
    assert "t_no_terms" in msg
    assert "rights.terms_url" in msg


def test_the_loader_retrieval_fallback_is_a_violation() -> None:
    (msg,) = rights_record_consistency_violations([_record("t_fallback", retrieval_date=_FALLBACK)])
    assert "t_fallback" in msg
    assert "retrieval_date" in msg


def test_the_seeded_registry_has_no_consistency_violations() -> None:
    # The invariant over the committed registry — every flipped row's record is
    # complete and self-consistent (the P37.6 audit repaired the drift set).
    assert rights_record_consistency_violations(sources()) == []


def test_validate_fails_naming_the_inconsistent_id(monkeypatch) -> None:
    # Wiring: `sig-connectors validate` surfaces the rule and fails loud.
    bad = _record("t_wired", review_packet="")
    monkeypatch.setattr(
        "connectors.cli.rights_record_consistency_violations",
        lambda srcs: [
            f"source {bad.id!r} has ingestion_permitted=true but is missing review_packet"
        ],
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(["validate"])
    assert code == 1
    assert "VALIDATION FAILED" in buf.getvalue()
    assert "t_wired" in buf.getvalue()
