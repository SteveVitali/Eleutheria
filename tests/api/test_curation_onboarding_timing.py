# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The L0 form's opt-in, aggregate-only onboarding timing hook (P21.7, §34.2).

Part VIII §0.7: opting in folds ONE elapsed-minutes measurement into the aggregate;
the elapsed time is NEVER written to the append-only submission row (no per-user
timing row), and the aggregate endpoint returns only count + median.
"""

from __future__ import annotations

from api.curation import CurationLog, create_curation_app
from starlette.testclient import TestClient

_ANON = {"Authorization": "Bearer anon-demo-key"}


def _client() -> TestClient:
    app = create_curation_app(curation_log=CurationLog(), enabled=True)
    return TestClient(app, raise_server_exceptions=True)


def _submit(client: TestClient, **extra: str):
    data = {"kind": "report", "evidence_url": "https://e/doc", "claim": "x", **extra}
    return client.post("/v1/curation/submission", data=data, headers=_ANON)


def test_no_timing_recorded_without_opt_in() -> None:
    client = _client()
    resp = _submit(client, elapsed_minutes="7")  # no timing_opt_in -> ignored
    assert resp.status_code == 200
    agg = client.get("/v1/curation/onboarding-timing", headers=_ANON).json()
    assert agg["count"] == 0
    assert agg["median_minutes"] is None


def test_opt_in_folds_into_aggregate_only() -> None:
    client = _client()
    for minutes in ("5", "7", "9"):
        assert _submit(client, timing_opt_in="1", elapsed_minutes=minutes).status_code == 200
    agg = client.get("/v1/curation/onboarding-timing", headers=_ANON).json()
    assert agg["count"] == 3
    assert agg["aggregate_only"] is True
    assert agg["median_minutes"] is not None


def test_elapsed_time_never_written_to_the_submission_row() -> None:
    # The per-user append-only row must NOT carry the elapsed time (Part VIII §0.7).
    client = _client()
    resp = _submit(client, timing_opt_in="1", elapsed_minutes="8.5")
    row = resp.json()["recorded"]
    assert "elapsed_minutes" not in row
    assert "elapsed_minutes" not in row.get("payload", {})
    assert "8.5" not in str(row)


def test_opt_in_without_minutes_records_nothing() -> None:
    client = _client()
    assert _submit(client, timing_opt_in="1").status_code == 200
    agg = client.get("/v1/curation/onboarding-timing", headers=_ANON).json()
    assert agg["count"] == 0


def test_bad_elapsed_minutes_rejected() -> None:
    client = _client()
    resp = _submit(client, timing_opt_in="1", elapsed_minutes="abc")
    assert resp.status_code == 400
