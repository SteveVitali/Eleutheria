# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.41 / SIG-TRANSP-029/030/031 + K9 §5.1–5.5 — the shared verdict, the
two change dates, the all-predicate volatility basis, and honest staleness.

The freshness row emits, per source:

* ``freshness_verdict`` evaluated at the release as-of (never the reader's
  clock), carrying ``evaluated_at`` + ``run_record_missing``;
* ``last_upstream_change`` — the newest upstream-DECLARED instant, with the
  ``records_digest`` detected fallback and ``not_detectable`` honest
  absence; a byte-only change never moves it;
* ``last_sig_records_change`` — the record-set diff where comparable
  digests exist, else J3's labelled interim;
* ``volatility`` — the registry-class distribution over ALL published
  claims (never only the dated or site share), the dominant class for the
  chip, and the unregistered-predicate count;
* ``staleness`` — ``stale n of m evaluable``, or the honest
  ``not_evaluable`` counts; never "unknown", never a fabricated "0 stale".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from exports.transparency import (
    TRANSPARENCY_FRESHNESS_PATH,
    _last_sig_records_change,
    _last_upstream_change,
    _predicate_meta,
    _source_staleness,
    _source_volatility,
    capture_record,
    emit_transparency_artifacts,
    order_capture_records,
)

AT = datetime(2026, 10, 20, tzinfo=UTC)


def _emit_freshness(
    *,
    claims: list[dict[str, Any]] | None = None,
    captures: list[dict[str, Any]] | None = None,
    executions: list[dict[str, Any]] | None = None,
    predicates: list[tuple] | None = None,
    freshness_predicates: list[tuple] | None = None,
    freshness_observations: list[tuple] | None = None,
    cadence: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    if captures is not None:
        # _rows() maps positionally against the view column list; the helper
        # accepts dicts directly when they carry named keys — use the run
        # pipeline's view-row shape via ``transparency_captures`` as dicts is
        # not how ``_rows`` works, so build tuple rows instead.
        raise AssertionError("use _view_capture() tuple rows")
    for key, rows in (
        ("freshness_predicates", freshness_predicates),
        ("freshness_observations", freshness_observations),
        ("transparency_predicates", predicates),
    ):
        if rows is not None:
            raw[key] = rows
    arts = emit_transparency_artifacts(
        raw,
        claims=claims or [],
        cadence_sources=cadence if cadence is not None else {},
        at=AT,
    )
    rows = [
        json.loads(line)
        for line in arts[TRANSPARENCY_FRESHNESS_PATH].decode().splitlines()
        if line.strip()
    ]
    return {r["source_id"]: r for r in rows}


def test_verdict_carries_evaluated_at_and_release_clock() -> None:
    rows = _emit_freshness(
        claims=[{"source_id": "s1", "predicate_id": "p1", "observed_at": AT}],
        cadence={"s1": {"cadence": "monthly", "cron": "0 5 6 * *", "state": "enabled"}},
    )
    row = rows["s1"]
    assert row["evaluated_at"].startswith("2026-10-20T")
    # Every freshness value carries its evaluation time — the release as-of,
    # not the reader's now.
    assert "evaluated_at" in row and row["freshness_state"] in {
        "on_time",
        "late",
        "overdue",
        "never_run",
        "not_scheduled",
        "last_run_failed",
        "one_time_load",
        "not_applicable",
    }


def test_run_record_missing_flag() -> None:
    rows = _emit_freshness(
        claims=[{"source_id": "s1", "predicate_id": "p1", "observed_at": AT}],
        cadence={"s1": {"cadence": "monthly", "cron": "0 5 6 * *", "state": "enabled"}},
    )
    # Published records exist but no execution record does — the C-7 flag,
    # never a fabricated run.
    assert rows["s1"]["run_record_missing"] is True
    assert rows["s1"]["freshness_state"] == "never_run"


def test_one_time_load_is_disclosed() -> None:
    rows = _emit_freshness(
        claims=[{"source_id": "s1", "predicate_id": "p1", "observed_at": AT}],
        cadence={"s1": {"cadence": "one_time_load", "state": "enabled"}},
    )
    row = rows["s1"]
    assert row["one_time_load"] is True
    assert row["freshness_state"] == "one_time_load"


# --- the two change dates (K9 §5.4, SIG-TRANSP-031) ---------------------------


def _cap(**kw: Any) -> dict[str, Any]:
    base = {
        "target_key": "t1",
        "state": "flushed",
        "source_uri": "https://upstream.example/dataset",
        "mark_recorded_at": "2026-10-01T00:00:00Z",
    }
    base.update(kw)
    return base


def test_upstream_change_prefers_the_declared_instant() -> None:
    caps = [
        _cap(upstream_modified_at="2026-09-15T00:00:00Z", upstream_modified_basis="rowsUpdatedAt"),
        _cap(
            target_key="t2",
            upstream_modified_at="2026-10-10T00:00:00Z",
            upstream_modified_basis="editingInfo.lastEditDate",
        ),
    ]
    out = _last_upstream_change(caps)
    assert out["value"] == "2026-10-10T00:00:00Z"
    assert "editingInfo.lastEditDate" in out["basis"]


def test_upstream_change_digest_fallback_detects_record_set_change() -> None:
    caps = [
        _cap(mark_recorded_at="2026-10-01T00:00:00Z", records_digest="aaa"),
        _cap(mark_recorded_at="2026-10-05T00:00:00Z", records_digest="bbb"),
    ]
    out = _last_upstream_change(caps)
    assert out["value"] == "2026-10-05T00:00:00Z"
    assert "records_digest" in out["basis"]


def test_upstream_change_byte_only_change_never_moves_the_date() -> None:
    # The mark digest moved (bytes differ) but the record set did not —
    # a formatting change never advances the upstream-change date.
    caps = [
        _cap(mark_recorded_at="2026-10-01T00:00:00Z", records_digest="aaa", mark_digest="x1"),
        _cap(mark_recorded_at="2026-10-05T00:00:00Z", records_digest="aaa", mark_digest="x2"),
    ]
    out = _last_upstream_change(caps)
    assert out["value"] is None and "records_digest" in out["basis"]


def test_upstream_change_token_only_is_not_detectable_never_a_date() -> None:
    out = _last_upstream_change([_cap(upstream_token='"v3"', upstream_modified_basis="ETag")])
    assert out["value"] is None and "not_detectable" in out["basis"]


def test_upstream_change_no_captures_is_not_detectable() -> None:
    out = _last_upstream_change([])
    assert "not_detectable" in out["basis"]


def test_sig_records_change_uses_digest_diff_when_comparable() -> None:
    caps = [
        _cap(mark_recorded_at="2026-10-01T00:00:00Z", records_digest="aaa"),
        _cap(mark_recorded_at="2026-10-05T00:00:00Z", records_digest="bbb"),
    ]
    out = _last_sig_records_change(caps, [], published_claims=10)
    assert out["value"] == "2026-10-05T00:00:00Z"
    assert "records_digest" in out["basis"]


def test_sig_records_change_interm_is_labelled_not_a_content_measure() -> None:
    out = _last_sig_records_change(
        [],
        [
            {
                "finished_at": "2026-10-03T00:00:00Z",
                "claims_inserted": 4,
                "completion_status": "ok",
            },
            {
                "finished_at": "2026-10-04T00:00:00Z",
                "claims_inserted": 0,
                "completion_status": "ok",
            },
        ],
        published_claims=4,
    )
    # The last claim-adding execution — labelled honestly as not a
    # content-change measure (the +0 run changed nothing).
    assert out["value"] == "2026-10-03T00:00:00Z"
    assert "not a content-change measure" in out["basis"]


def test_sig_records_change_no_evidence_is_honest_token() -> None:
    assert _last_sig_records_change([], [], published_claims=7)["value"] == "first_release"
    assert _last_sig_records_change([], [], published_claims=0)["value"] == "not_published"


# --- the capture record + changed_vs_prior -------------------------------------


def test_capture_record_carries_digest_and_declared_block() -> None:
    row = {
        "run_id": "r1",
        "source_id": "s1",
        "target_key": "t1",
        "state": "flushed",
        "records_digest": "d" * 64,
        "upstream_modified_at": "2026-09-15T00:00:00Z",
        "upstream_token": None,
        "upstream_modified_basis": "rowsUpdatedAt",
        "source_uri": "https://upstream.example/dataset",
    }
    rec = capture_record(row)
    assert rec["records_digest"] == "d" * 64
    assert rec["upstream_declared"]["modified_at"].startswith("2026-09-15T")
    assert rec["upstream_declared"]["basis"] == "rowsUpdatedAt"
    # A transport declaring nothing renders the honest marker, never a date.
    rec2 = capture_record({"run_id": "r2", "source_id": "s1", "state": "captured"})
    assert rec2["upstream_declared"]["basis"] == "not_detectable"
    assert rec2["upstream_declared"]["modified_at"] is None


def test_changed_vs_prior_formatting_change_only() -> None:
    recs = order_capture_records(
        [
            {
                "source_id": "s1",
                "target": "t",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "mark_recorded_at": "2026-10-01T00:00:00Z",
                "digest": "b1",
                "records_digest": "aaa",
            },
            {
                "source_id": "s1",
                "target": "t",
                "retrieved_at": "2026-10-05T00:00:00Z",
                "mark_recorded_at": "2026-10-05T00:00:00Z",
                "digest": "b2",  # bytes differ…
                "records_digest": "aaa",  # …the record set did not
            },
            {
                "source_id": "s1",
                "target": "t",
                "retrieved_at": "2026-10-09T00:00:00Z",
                "mark_recorded_at": "2026-10-09T00:00:00Z",
                "digest": "b3",
                "records_digest": "ccc",  # a real record-set change
            },
        ]
    )
    assert [r["changed_vs_prior"] for r in recs] == [
        "first",
        "formatting change only",
        "changed",
    ]


# --- the all-predicate volatility basis + staleness -----------------------------


def test_volatility_distribution_covers_all_published_claims() -> None:
    # Two registered predicates + one the registry does not declare —
    # dated AND undated alike are in the distribution's denominator.
    meta = _predicate_meta(
        [
            ("p_fast", "FAST", 7.0),
            ("p_slow", "SLOW", 730.0),
        ]
    )
    rows = [
        ("s1", "p_fast", 10, 8),  # 10 claims, 8 dated
        ("s1", "p_slow", 30, 30),
        ("s1", "p_unreg", 5, 0),
    ]
    vol = _source_volatility(rows, meta)["s1"]
    assert vol["distribution"] == {"FAST": 10, "SLOW": 30}
    assert vol["unregistered_predicate"] == 5
    assert vol["undated"] == 7
    assert vol["dated"] == 38
    assert vol["dominant"] == {"class": "SLOW", "half_life_days": 730.0}


def test_staleness_ages_against_the_predicate_half_life() -> None:
    meta = _predicate_meta(
        [
            ("p_fast", "FAST", 7.0),
            ("p_slow", "SLOW", 730.0),
        ]
    )
    obs = [
        # Latest dated obs per (source, subject, predicate), deduped upstream.
        ("s1", "p_fast", datetime(2026, 9, 1, tzinfo=UTC)),  # ~49 d > 7 d → stale
        ("s1", "p_slow", datetime(2026, 9, 1, tzinfo=UTC)),  # ~49 d < 730 d → fresh
        ("s1", "p_unreg", datetime(2026, 10, 1, tzinfo=UTC)),  # unevaluable
    ]
    out = _source_staleness(obs, meta, at=AT)["s1"]
    assert out == {"evaluable": 2, "stale": 1, "dated_unevaluable": 1}


def test_freshness_row_emits_stale_n_of_m_never_fake_zero() -> None:
    rows = _emit_freshness(
        claims=[],  # no shaping-claim fallback — the reads carry everything
        freshness_predicates=[("s1", "p_slow", 30, 30)],
        freshness_observations=[
            ("s1", "p_slow", datetime(2026, 10, 1, tzinfo=UTC)),
        ],
        predicates=[("p_slow", "SLOW", 730.0)],
        cadence={"s1": {"cadence": "monthly", "cron": "0 5 6 * *", "state": "enabled"}},
    )
    st = rows["s1"]["staleness"]
    assert st["evaluable"] == 1 and st["stale"] == 0  # measured, honestly
    assert "unknown" not in json.dumps(rows["s1"]).lower()


def test_freshness_row_unevaluable_never_prints_stale() -> None:
    rows = _emit_freshness(
        claims=[],
        freshness_predicates=[("s1", "p_undated_only", 12, 0)],
        freshness_observations=[],
        predicates=[("p_undated_only", "SLOW", 730.0)],
        cadence={"s1": {"cadence": "monthly", "cron": "0 5 6 * *", "state": "enabled"}},
    )
    st = rows["s1"]["staleness"]
    # "not evaluable: m undated" — no stale figure, not "0 stale".
    assert "stale" not in st
    assert st["evaluable"] == 0 and st["not_evaluable"] == 12
    vol = rows["s1"]["volatility"]
    assert vol["distribution"] == {"SLOW": 12}
    assert vol["dominant"] == {"class": "SLOW", "half_life_days": 730.0}
