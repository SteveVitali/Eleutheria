# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.46 — ``sig.execution-record/1`` + per-source ``executions.jsonl``
(K10 §9 + §16.1, SIG-TRANSP-036): the execution-keyed history surface."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from exports.transparency import (
    EXECUTION_RECORD_FIELDS,
    EXECUTION_RECORD_SCHEMA,
    TRANSPARENCY_EXECUTIONS_GLOB,
    emit_transparency_artifacts,
    execution_record,
)


def _row(**kw: object) -> dict[str, object]:
    row: dict[str, object] = {
        "report_id": "11111111-1111-1111-1111-111111111111",
        "run_id": "22222222-2222-2222-2222-222222222222",
        "source_id": "src.exec.demo",
        "link_basis": "live",
        "clock_basis": "db",
        "shared_run": False,
        "started_at": datetime(2026, 9, 20, 1, 0, tzinfo=UTC),
        "finished_at": datetime(2026, 9, 20, 1, 10, tzinfo=UTC),
        "duration_seconds": 600.0,
        "completion_status": "ok",
        "claims_considered": 5,
        "claims_inserted": 4,
        "claims_duplicate": 1,
        "fetches": 2,
        "records_emitted": 5,
        "robots_outcomes": None,
        "refusal_classes": None,
        "rate_limit_events": 0,
        "disappearances": 0,
        "document_outcomes": None,
        "quota_reached": False,
        "budget_reached": False,
        "error_class": None,
        "per_fetch": None,
        "connector_name": "sig.test.connector",
        "connector_version": "1.2.3",
        "code_commit": "sha256:deadbeef",
        "recorded_at": datetime(2026, 9, 20, 1, 10, 1, tzinfo=UTC),
        "execution_key": "completion:33333333-3333-3333-3333-333333333333",
        "mode": "live",
        "kind": "scheduled-ingest",
    }
    row.update(kw)
    return row


def test_execution_record_carries_the_c14_shape() -> None:
    rec = execution_record(_row())
    assert rec["schema"] == EXECUTION_RECORD_SCHEMA
    assert rec["execution_key"] == "completion:33333333-3333-3333-3333-333333333333"
    assert rec["mode"] == "live"
    assert rec["kind"] == "scheduled-ingest"
    assert rec["link_basis"] == "live"
    assert rec["clock_basis"] == "db"
    identity = rec["code_identity"]
    assert identity == {
        "connector_name": "sig.test.connector",
        "connector_version": "1.2.3",
        "code_commit": "sha256:deadbeef",
        "basis": "ingest_run (the execution owns its run)",
    }
    assert set(rec) <= set(EXECUTION_RECORD_FIELDS)


def test_code_identity_shared_run_never_borrows() -> None:
    rec = execution_record(
        _row(shared_run=True, connector_name=None, connector_version=None, code_commit=None)
    )
    identity = rec["code_identity"]
    assert identity["basis"] == "not_recorded (shared run)"
    assert identity["code_commit"] == "not_recorded (shared run)"
    assert identity["connector_name"] == "not_recorded (shared run)"


def test_code_identity_unknown_commit_is_not_recorded() -> None:
    rec = execution_record(_row(code_commit="unknown"))
    identity = rec["code_identity"]
    assert identity["code_commit"] == "not_recorded"
    assert identity["basis"] == "ingest_run (the execution owns its run)"


def test_code_identity_no_run() -> None:
    rec = execution_record(
        _row(
            run_id=None,
            code_commit=None,
            connector_name=None,
            connector_version=None,
            execution_key="repo:docs/build/reports/live_runs/r.json",
            link_basis="repo_record",
            clock_basis="git_only",
        )
    )
    assert rec["code_identity"]["basis"] == "not_recorded (no linked run)"


def test_emit_writes_per_source_executions_jsonl() -> None:
    from policy.transparency import TRANSPARENCY_RUN_VIEW_COLUMNS

    a = _row(source_id="src.a")
    b = _row(source_id="src.b", report_id="x2")
    raw = {
        "transparency_runs": [
            tuple(a.get(c) for c in TRANSPARENCY_RUN_VIEW_COLUMNS),
            tuple(b.get(c) for c in TRANSPARENCY_RUN_VIEW_COLUMNS),
        ]
    }
    arts = emit_transparency_artifacts(raw, at=datetime(2026, 11, 1, tzinfo=UTC))
    pa = TRANSPARENCY_EXECUTIONS_GLOB.format(source_id="src.a")
    pb = TRANSPARENCY_EXECUTIONS_GLOB.format(source_id="src.b")
    assert pa in arts and pb in arts
    rows = [json.loads(line) for line in arts[pa].decode().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["schema"] == EXECUTION_RECORD_SCHEMA
    assert rows[0]["execution_key"].startswith("completion:")
    assert set(rows[0]) <= set(EXECUTION_RECORD_FIELDS)
