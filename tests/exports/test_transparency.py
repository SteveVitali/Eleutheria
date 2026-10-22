# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.33 — the ``transparency/`` release artifacts (J3 §3, K9 §5/§10,
K10 §10 C-13/C-14/C-15/C-18): fixture-verified scrub, honesty tokens,
robots-disregard disclosure and the J3 §7.3 issue classes.

Every assertion runs over fixture rows shaped like the transparency views'
tuples — no database, no secrets, no live values.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from exports.transparency import (
    CAPTURE_RECORD_SCHEMA,
    FRESHNESS_RECORD_SCHEMA,
    ISSUE_RECORD_SCHEMA,
    RUN_RECORD_SCHEMA,
    TRANSPARENCY_CAPTURES_PATH,
    TRANSPARENCY_FRESHNESS_PATH,
    TRANSPARENCY_ISSUES_PATH,
    TRANSPARENCY_QUERIES,
    TRANSPARENCY_RUNS_PATH,
    capture_record,
    emit_transparency_artifacts,
    load_cadence_sources,
    run_record,
)
from policy.transparency import (
    TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
    TRANSPARENCY_RUN_VIEW_COLUMNS,
)

AT = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)


def _row(columns: tuple[str, ...], **kw: Any) -> dict[str, Any]:
    base = dict.fromkeys(columns)
    base.update(kw)
    return base


def _run(**kw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "report_id": "rep-1",
        "run_id": "run-1",
        "source_id": "muckrock",
        "link_basis": "repo_record",
        "clock_basis": "db",
        "shared_run": False,
        "started_at": datetime(2026, 10, 1, 4, tzinfo=UTC),
        "finished_at": datetime(2026, 10, 1, 5, tzinfo=UTC),
        "completion_status": "ok",
        "records_emitted": 42,
        "code_commit": "abc123",
        "connector_name": "muckrock",
        "connector_version": "1.0",
        "recorded_at": datetime(2026, 10, 1, 6, tzinfo=UTC),
    }
    defaults.update(kw)
    return _row(TRANSPARENCY_RUN_VIEW_COLUMNS, **defaults)


# --- sig.run-record/1 (C-13: execution-keyed; C-14: link/clock basis) ----


def test_run_record_shared_run_never_borrows_owned_values():
    rec = run_record(
        _run(
            shared_run=True,
            code_commit=None,  # the view NULLs it; the record must not leak
            connector_name=None,
            connector_version=None,
            claims_considered=None,
            started_at=None,
            finished_at=None,
            completion_status=None,
            error_class=None,
            link_basis="backfill:sole-candidate",
        )
    )
    assert rec["shared_run"] is True
    for field in ("code_commit", "connector_name", "connector_version"):
        assert rec[field] == "not_recorded (shared run)"
    for field in ("claims_considered", "claims_inserted", "claims_duplicate"):
        assert rec[field] == "not_recorded (shared run)"
    assert rec["outcome"] == "not_recorded (shared run)"
    assert rec["link_basis"] == "backfill:sole-candidate"


def test_run_record_started_at_falls_back_to_finished_minus_duration():
    rec = run_record(
        _run(
            started_at=None, finished_at=datetime(2026, 10, 1, 5, tzinfo=UTC), duration_seconds=600
        )
    )
    assert rec["started_at"] == "2026-10-01T04:50:00Z"
    assert "derived" in rec["started_basis"]


def test_run_record_outcome_derivation():
    assert (
        run_record(_run(completion_status=None, error_class="upstream_http_503"))["outcome"]
        == "failed"
    )
    assert (
        run_record(_run(completion_status=None, error_class=None, quota_reached=True))["outcome"]
        == "quota_reached"
    )
    assert "not_recorded" in run_record(_run(completion_status=None, error_class=None))["outcome"]


def test_run_record_rejected_folds_off_vocabulary_reasons():
    rec = run_record(_run(refusal_classes={"bad_digest": 2, "operator_debug_note": 1, "weird": 3}))
    assert rec["rejected"] == {"bad_digest": 2, "other_unclassifiable": 4}
    assert "operator_debug_note" not in json.dumps(rec)


def test_run_record_off_vocabulary_error_maps_to_unclassified():
    rec = run_record(_run(completion_status=None, error_class="kernel_panic_xyz"))
    assert rec["error_class"] == "unclassified_error"
    assert "kernel_panic_xyz" not in json.dumps(rec)


def test_internal_error_class_records_but_fires_no_issue():
    """db_connection_lost is a valid *error* class (S-4) but is not a
    J3 §7.3 *issue* class — it lands on the run row, never in issues.jsonl."""
    arts = _emit([_run(completion_status=None, error_class="db_connection_lost")])
    run = json.loads(arts[TRANSPARENCY_RUNS_PATH].decode().splitlines()[0])
    assert run["error_class"] == "db_connection_lost"
    classes = {
        json.loads(line)["issue_class"]
        for line in arts[TRANSPARENCY_ISSUES_PATH].decode().splitlines()
    }
    assert "db_connection_lost" not in classes


# --- the robots-disregard disclosure (B-19: host + count + GL-GATE-08) ---


def test_robots_disclosure_is_host_count_decision_ref_only():
    rec = run_record(
        _run(
            robots_outcomes={
                "muckrock.com": {"disregarded": 2, "obeyed": 5},
                "api.muckrock.com": {"disregarded": 1},
            }
        )
    )
    disregarded = [r for r in rec["robots"] if r["outcome"] == "disregarded"]
    assert {r["host"] for r in disregarded} == {"muckrock.com", "api.muckrock.com"}
    for r in disregarded:
        assert r["decision_ref"] == "GL-GATE-08"
        assert set(r) == {"host", "outcome", "count", "decision_ref"}
    for r in rec["robots"]:
        if r["outcome"] != "disregarded":
            assert "decision_ref" not in r
    # Never per-request detail: no path, no UA, no timestamp on a robots row.
    blob = json.dumps(rec["robots"])
    for forbidden in ("path", "user_agent", "fingerprint", "request_id"):
        assert forbidden not in blob


# --- sig.capture-record/1 (sealed stays sealed) --------------------------


def _capture(**kw: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "run_id": "run-1",
        "source_id": "muckrock",
        "target_key": "https://example.org/data.csv",
        "state": "flushed",
        "source_uri": "https://example.org/data.csv",
        "mark_digest": "sha256:aa",
        "byte_size": 1024,
        "media_type": "text/csv",
        "records": 42,
        "retrieved_at": datetime(2026, 10, 1, 4, 30, tzinfo=UTC),
        "mark_recorded_at": datetime(2026, 10, 1, 4, 31, tzinfo=UTC),
        "capture_classification": "actual",
        "storage_tier": "public",
        "bytes_retained": True,
        "shared_run": False,
    }
    defaults.update(kw)
    return _row(TRANSPARENCY_CAPTURE_VIEW_COLUMNS, **defaults)


def test_capture_record_sealed_emits_no_locator():
    rec = capture_record(
        _capture(
            storage_tier="sealed",
            source_uri="https://sealed.example.org/x",
            target_key="https://sealed.example.org/x",
        )
    )
    assert rec["storage_tier"] == "sealed"
    assert rec["target"] == "sealed"
    assert "sealed.example.org" not in json.dumps(rec)


def test_capture_record_mark_without_capture_row_uses_lane_floor():
    rec = capture_record(_capture(storage_tier=None))
    assert "derived" in rec["tier_basis"]
    assert rec["classification"] == "actual"


def test_order_capture_records_changed_vs_prior():
    from exports.transparency import order_capture_records

    recs = [
        capture_record(
            _capture(mark_digest="sha256:a2", retrieved_at=datetime(2026, 10, 2, tzinfo=UTC))
        ),
        capture_record(
            _capture(mark_digest="sha256:a1", retrieved_at=datetime(2026, 10, 1, tzinfo=UTC))
        ),
        capture_record(
            _capture(mark_digest="sha256:a2", retrieved_at=datetime(2026, 10, 3, tzinfo=UTC))
        ),
    ]
    ordered = order_capture_records(recs)
    assert [r["changed_vs_prior"] for r in ordered] == ["first", "changed", "unchanged"]


# --- sig.source-issue/1 (J3 §7.3) ----------------------------------------


_UNSET = object()


def _emit(
    run_rows,
    cap_rows=(),
    claims=(),
    cadence=_UNSET,
    cadence_path=None,
    source_registry=None,
    site_source_ids=(),
    at=AT,
):
    raw = {
        "transparency_runs": [tuple(r[c] for c in TRANSPARENCY_RUN_VIEW_COLUMNS) for r in run_rows],
        "transparency_captures": [
            tuple(r[c] for c in TRANSPARENCY_CAPTURE_VIEW_COLUMNS) for r in cap_rows
        ],
        "transparency_source_rights": [],
        "transparency_sources": [],
        "transparency_predicates": [],
    }
    return emit_transparency_artifacts(
        raw,
        claims=claims,
        cadence_sources={} if cadence is _UNSET else cadence,
        cadence_path=cadence_path,
        source_registry=source_registry,
        site_source_ids=site_source_ids,
        at=at,
    )


def test_zero_records_and_capture_not_retained_fire():
    arts = _emit(
        [_run(records_emitted=0)],
        [_capture(bytes_retained=False, records=None, state="captured")],
        cadence={"muckrock": {"cron": "0 6 1 * *", "cadence": "monthly", "state": "enabled"}},
    )
    classes = {
        json.loads(line)["issue_class"]
        for line in arts[TRANSPARENCY_ISSUES_PATH].decode().splitlines()
    }
    assert "zero_records" in classes
    assert "capture_not_retained" in classes


def test_issues_close_on_first_clean_later_execution():
    bad = _run(
        report_id="r1",
        finished_at=datetime(2026, 10, 1, 5, tzinfo=UTC),
        completion_status=None,
        error_class="upstream_http_503",
    )
    good = _run(
        report_id="r2",
        finished_at=datetime(2026, 10, 2, 5, tzinfo=UTC),
        completion_status="ok",
        records_emitted=10,
    )
    arts = _emit([good, bad])  # unordered input — instances still order
    issues = [json.loads(line) for line in arts[TRANSPARENCY_ISSUES_PATH].decode().splitlines()]
    http = next(i for i in issues if i["issue_class"] == "upstream_http_503")
    assert http["count"] == 1
    assert http["closed_at"] == "2026-10-02T05:00:00Z"
    assert http["schema"] == ISSUE_RECORD_SCHEMA


def test_freshness_state_classes_and_never_run_issue():
    claims = [{"source_id": "muckrock", "predicate_id": "p", "observed_at": None}]
    arts = _emit(
        [],
        claims=claims,
        cadence={"muckrock": {"cron": "0 6 1 * *", "cadence": "monthly", "state": "enabled"}},
    )
    freshness = [
        json.loads(line) for line in arts[TRANSPARENCY_FRESHNESS_PATH].decode().splitlines()
    ]
    row = next(r for r in freshness if r["source_id"] == "muckrock")
    assert row["freshness_state"] == "never_run"
    assert row["run_record_missing"] is True  # C-7: records, no run record
    assert row["cadence_rule"] == "monthly, day 1"
    assert row["evaluated_at"] == "2026-10-19T08:00:00Z"  # the release as-of
    assert row["schema"] == FRESHNESS_RECORD_SCHEMA
    issues = {
        json.loads(line)["issue_class"]
        for line in arts[TRANSPARENCY_ISSUES_PATH].decode().splitlines()
    }
    assert "never_run" in issues


def test_cadence_unreadable_marks_basis_not_rule(tmp_path):
    arts = _emit(
        [],
        claims=[{"source_id": "s1", "predicate_id": "p", "observed_at": None}],
        cadence=None,
        cadence_path=tmp_path / "absent.toml",
        at=AT,
    )
    row = json.loads(arts[TRANSPARENCY_FRESHNESS_PATH].decode().splitlines()[0])
    assert row["cadence_basis"] == "not_recorded"
    assert "not_recorded" in row["cadence_rule"]


def test_no_release_artifact_shows_a_next_run():
    """K9 C-4: the cadence rule ships; 'next run' never does — check no
    record carries a next_run/next_fire field or a future timestamp."""
    arts = _emit(
        [_run()],
        cadence={"muckrock": {"cron": "0 6 1 * *", "cadence": "monthly", "state": "enabled"}},
    )
    for path, payload in arts.items():
        for line in payload.decode().splitlines():
            rec = json.loads(line)
            assert not any(k.startswith("next_") for k in rec), path


# --- artifact shape + determinism ----------------------------------------


def test_emit_returns_four_canonical_artifacts_deterministically():
    kwargs = dict(
        claims=[],
        cadence={"muckrock": {"cron": "0 6 1 * *", "cadence": "monthly", "state": "enabled"}},
        at=AT,
    )
    a1 = _emit([_run()], [_capture()], **kwargs)
    a2 = _emit([_run()], [_capture()], **kwargs)
    assert set(a1) == {
        TRANSPARENCY_RUNS_PATH,
        TRANSPARENCY_CAPTURES_PATH,
        TRANSPARENCY_ISSUES_PATH,
        TRANSPARENCY_FRESHNESS_PATH,
    }
    for path in a1:
        assert a1[path] == a2[path], f"{path} not byte-stable"
    run = json.loads(a1[TRANSPARENCY_RUNS_PATH].decode().splitlines()[0])
    cap = json.loads(a1[TRANSPARENCY_CAPTURES_PATH].decode().splitlines()[0])
    assert run["schema"] == RUN_RECORD_SCHEMA
    assert cap["schema"] == CAPTURE_RECORD_SCHEMA
    # JSONL canonicalisation: sorted keys, LF-terminated, no trailing junk.
    assert a1[TRANSPARENCY_RUNS_PATH].decode().endswith("\n")
    keys = list(run)
    assert keys == sorted(keys)


def test_missing_views_degrade_to_empty_artifacts():
    arts = emit_transparency_artifacts({}, claims=[], cadence_sources={}, at=AT)
    assert arts[TRANSPARENCY_RUNS_PATH] == b""
    assert arts[TRANSPARENCY_CAPTURES_PATH] == b""


def test_forbidden_fields_never_appear_in_any_artifact():
    rec = _run(
        parameters={"api_key": "secret-token-123"},
        detail={"note": "private quarantine payload"},
        notes="internal note",
    )
    arts = _emit([rec], [_capture()])
    blob = b"".join(arts.values()).decode()
    for forbidden in (
        "secret-token-123",
        "private quarantine payload",
        "internal note",
        "parameters",
        "notes",
        "payload",
    ):
        assert forbidden not in blob


def test_export_queries_are_explicit_column_selects():
    """TRANSPARENCY_QUERIES name the views and select the allow-listed
    columns — never ``SELECT *`` (the producer-check contract)."""
    for key, (_relation, sql) in TRANSPARENCY_QUERIES.items():
        assert "select *" not in sql.lower(), key
        assert " FROM " in sql
    assert "v_transparency_run" in TRANSPARENCY_QUERIES["transparency_runs"][0]
    assert "v_transparency_capture" in TRANSPARENCY_QUERIES["transparency_captures"][0]


def test_export_queries_keys_registered_in_spine_export():
    """Every transparency query key is reachable through EXPORT_QUERIES —
    the producer check counts on it (a dropped key = a missing artifact)."""
    from exports.spine_export import EXPORT_QUERIES

    for key in TRANSPARENCY_QUERIES:
        assert key in EXPORT_QUERIES


def test_load_cadence_sources_reads_ops_doc(tmp_path):
    p = tmp_path / "cadence.toml"
    p.write_text(
        '[[sources]]\nid = "muckrock"\ncron = "0 6 1 * *"\ncadence = "monthly"\nstate = "enabled"\n'
    )
    out = load_cadence_sources(p)
    assert out == {"muckrock": {"cron": "0 6 1 * *", "cadence": "monthly", "state": "enabled"}}


def test_load_cadence_sources_missing_file_returns_none(tmp_path):
    assert load_cadence_sources(tmp_path / "absent.toml") is None


@pytest.mark.parametrize(
    "cls",
    [
        "upstream_http_503",
        "robots_disallow",
        "quarantine_bad_digest",
        "rate_limited",
        "zero_records",
        "capture_not_retained",
    ],
)
def test_issue_classes_emit_with_valid_vocabulary(cls):
    runs = _run(
        completion_status="ok" if cls == "zero_records" else None,
        error_class="upstream_http_503" if cls == "upstream_http_503" else None,
        records_emitted=0 if cls == "zero_records" else 1,
        refusal_classes=(
            {cls.removeprefix("quarantine_"): 1} if cls.startswith("quarantine_") else None
        ),
        robots_outcomes=({"h.test": {"disallowed": 1}} if cls == "robots_disallow" else None),
        rate_limit_events=1 if cls == "rate_limited" else None,
    )
    caps = [_capture(bytes_retained=False)] if cls == "capture_not_retained" else []
    arts = _emit([runs], caps)
    classes = {
        json.loads(line)["issue_class"]
        for line in arts[TRANSPARENCY_ISSUES_PATH].decode().splitlines()
    }
    assert cls in classes
