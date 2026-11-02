# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.49 (TX-06, SIG-TRANSP-010): the curated known-issues registry."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from exports.known_issues import (
    CURATED_ISSUE_CLASSES,
    KNOWN_ISSUES_DATA,
    KnownIssuesError,
    curated_issue_records,
    load_known_issues,
)
from exports.transparency import issue_records


def _doc(body: str) -> str:
    return textwrap.dedent(body)


def test_committed_file_loads_and_validates() -> None:
    entries = load_known_issues()
    assert entries, "the committed registry is empty — the F-322 seed is owed"
    ids = [e["issue_id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        assert e["issue_class"] in CURATED_ISSUE_CLASSES
        assert e["status"] == "open" or e["closed_at"]
    assert KNOWN_ISSUES_DATA.name == "known_issues.toml"


def test_seed_covers_the_f322_sources(tmp_path: Path) -> None:
    entries = load_known_issues()
    sources = {e["source_id"] for e in entries}
    for sid in {
        "camreg_nottingham_gb",
        "camreg_mark43",
        "camreg_trafficops_ca",
        "camreg_gmh_emc_ga",
        "camreg_bangla_bd",
        "camreg_oosgis_nl",
        "dot_511_ga",
        "camreg_fl511_fl",
    }:
        assert sid in sources, f"F-322 source {sid} missing from the seed"


def test_pending_text_never_reaches_the_record(tmp_path: Path) -> None:
    entries = load_known_issues()
    recs = curated_issue_records(entries)
    for rec, entry in zip(recs, entries, strict=True):
        if entry["text_state"] == "pending_review":
            assert rec["text"] is None
            assert rec["text_state"] == "pending_review"
        assert rec["kind"] == "curated"
        assert rec["basis"] == "known_issues.toml"


def test_confirmed_text_flows(tmp_path: Path) -> None:
    p = tmp_path / "ki.toml"
    p.write_text(
        _doc(
            """
            schema = "sig.known-issues/1"
            [[issue]]
            source_id = "s1"
            issue_class = "misattribution"
            opened_at = "2026-01-01T00:00:00Z"
            status = "closed"
            closed_at = "2026-02-01T00:00:00Z"
            correction_ref = "corrections/2026-02"
            text = "confirmed sentence"
            text_state = "confirmed"
            """
        ),
        encoding="utf-8",
    )
    (rec,) = curated_issue_records(load_known_issues(p))
    assert rec["text"] == "confirmed sentence"
    assert rec["closed_at"] == "2026-02-01T00:00:00Z"
    assert rec["issue_id"] == "ki:s1:misattribution:2026-01-01"


def test_validation_refuses_bad_rows(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text(
        _doc(
            """
            schema = "sig.known-issues/1"
            [[issue]]
            source_id = "s1"
            issue_class = "invented_class"
            opened_at = "2026-01-01T00:00:00Z"
            status = "open"
            text_state = "pending_review"
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(KnownIssuesError):
        load_known_issues(bad)

    closed_no_date = tmp_path / "c.toml"
    closed_no_date.write_text(
        _doc(
            """
            schema = "sig.known-issues/1"
            [[issue]]
            source_id = "s1"
            issue_class = "axis_swap"
            opened_at = "2026-01-01T00:00:00Z"
            status = "closed"
            text_state = "pending_review"
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(KnownIssuesError):
        load_known_issues(closed_no_date)


def test_curated_rows_merge_into_issues_jsonl() -> None:
    from datetime import UTC, datetime

    issues = issue_records(
        run_records=[],
        capture_rows=[],
        freshness_rows=[],
        at=datetime(2026, 11, 2, tzinfo=UTC),
        known_issues=load_known_issues(),
    )
    kinds = {r["kind"] for r in issues}
    assert kinds == {"curated"}
    assert any(r["source_id"] == "camreg_nottingham_gb" for r in issues)
    assert all("text" in r and "correction_ref" in r for r in issues)


def test_append_only_no_updates() -> None:
    # closing an issue is a row-state change in the toml, never an edit
    entries = load_known_issues()
    recs = curated_issue_records(entries)
    assert all(r["opened_at"] for r in recs)
