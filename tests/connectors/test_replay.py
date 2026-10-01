# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Backfill, replay, and shadow mode (SIG-INGEST-017/018/019)."""

from __future__ import annotations

import json

import pytest
from connectors.isolation import NetworkEgressBlocked
from connectors.replay import diff_claim_sets, replay, replay_fingerprint, shadow_replay


def _archive(ctx, payload: dict) -> object:  # type: ignore[no-untyped-def]
    """Archive a capture directly, as a prior fetch would have (SIG-INGEST-017)."""
    return ctx.captures.put(
        json.dumps(payload, sort_keys=True).encode("utf-8"),
        media_type="application/json",
        source_uri="https://portal.example/p1",
    )


def test_replay_over_pinned_captures_is_byte_identical(make_context, toy_connector) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-017/018: replay over pinned digests => byte-identical claims
    # modulo the generated id and sys_period.
    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 42})

    claims_a = replay(toy_connector, ctx, [capture])
    claims_b = replay(toy_connector, ctx, [capture])

    assert replay_fingerprint(claims_a) == replay_fingerprint(claims_b)
    # The only differences between the two runs are the excluded columns.
    assert claims_a[0]["claim_id"] != claims_b[0]["claim_id"]
    assert claims_a[0]["value_num"] == claims_b[0]["value_num"] == 42


def test_replay_never_asserts(make_context, toy_connector) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-018: replay produces claims but does not assert them.
    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 1})
    replay(toy_connector, ctx, [capture])
    assert list(ctx.claim_sink.claims) == []
    assert ctx.replay is True


def test_replay_is_network_isolated(make_context, leaky_connector) -> None:  # type: ignore[no-untyped-def]
    # AC: a network call during replay (after capture) fails the run.
    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 1})
    with pytest.raises(NetworkEgressBlocked):
        replay(leaky_connector, ctx, [capture])


def test_diff_claim_sets_ignores_generated_columns() -> None:
    # SIG-INGEST-019: the diff is over canonical value, not the generated id/time.
    current = [{"claim_id": "a", "sys_period": "[t1,)", "subject_id": "s", "value_num": 1}]
    new_same = [{"claim_id": "b", "sys_period": "[t2,)", "subject_id": "s", "value_num": 1}]
    diff = diff_claim_sets(current, new_same)
    assert diff.summary() == {"added": 0, "removed": 0, "unchanged": 1, "changed": 0}

    new_changed = [{"claim_id": "c", "sys_period": "[t3,)", "subject_id": "s", "value_num": 2}]
    diff2 = diff_claim_sets(current, new_changed)
    assert diff2.summary()["added"] == 1
    assert diff2.summary()["removed"] == 1


def test_shadow_replay_reports_delta_without_asserting(make_context, toy_connector) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-019: shadow mode diffs new vs current and reports, no assertion.
    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 99})
    # The "current" claim set has a different (stale) value: the parser changed it.
    current = [
        {
            "claim_id": "old",
            "sys_period": "[t0,)",
            "subject_id": "p1",
            "predicate_id": "camera_count",
            "raw_value": "5",
            "value_num": 5,
        }
    ]

    diff = shadow_replay(toy_connector, ctx, [capture], current)

    assert diff.asserted is False
    assert diff.summary()["added"] == 1  # the new value 99
    assert diff.summary()["removed"] == 1  # the stale value 5
    # Nothing was asserted to the sink in shadow mode.
    assert list(ctx.claim_sink.claims) == []
    assert ctx.shadow is True


# --- asserting replay (P31.6 / ADR-113) ---------------------------------------


def test_asserting_replay_asserts_each_captures_claims(make_context, toy_connector) -> None:  # type: ignore[no-untyped-def]
    # ADR-113: the NAMED asserting reinterpretation — claims the post-capture
    # stages re-derive ARE handed to the claim sink, under ctx.replay=True.
    from connectors.replay import asserting_replay

    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 7})
    report = asserting_replay(toy_connector, ctx, [capture])

    assert report.captures == 1
    assert report.claims > 0
    assert report.asserted == report.claims
    assert list(ctx.claim_sink.claims)  # the sink got the re-derived claims
    assert ctx.replay is True and ctx.shadow is False


def test_asserting_replay_is_network_isolated(make_context, leaky_connector) -> None:  # type: ignore[no-untyped-def]
    # ADR-113: asserting is still pure reinterpretation — a post-capture network
    # call is refused exactly like the non-asserting replay's (SIG-INGEST-018).
    from connectors.replay import asserting_replay

    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 1})
    report = asserting_replay(leaky_connector, ctx, [capture])
    # The leaky stage's egress is blocked; the failure is recorded per capture
    # (reported loudly) and nothing was asserted.
    assert report.captures == 0
    assert report.errors and report.errors[0]["digest"] == capture.digest
    assert list(ctx.claim_sink.claims) == []


def test_asserting_replay_reports_each_flushed_capture(make_context, toy_connector) -> None:  # type: ignore[no-untyped-def]
    # ADR-113: on_capture runs after each capture's claims commit so the driver
    # can write the replay run's own capture-lineage marks.
    from connectors.replay import asserting_replay

    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 3})
    seen: list[tuple[str, int]] = []
    asserting_replay(
        toy_connector,
        ctx,
        [capture],
        on_capture=lambda c, claims: seen.append((c.digest, len(claims))),
    )
    assert seen == [(capture.digest, len(ctx.claim_sink.claims))]
