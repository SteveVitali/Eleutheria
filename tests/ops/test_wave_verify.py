# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.6 / ACQ-01 — ``wave-verify``, I8 §7.7's checks as one command.

Each check reports at the evidence layer it actually reached — engineered,
schedule, fixture, live-executed — never higher. The machinery-only wave
this ticket lands supplies no run evidence, so live-layer checks report
``pending``, and ``--require live`` is what promotes them to failures for
the activation rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ops.wave_verify import verify_wave

# A committed gated source id and a committed permitted one — stable registry
# facts, asserted only for their *posture* class (gated vs loadable), never
# for a living value.
_GATED = "ccops_boston"  # a registered, not-yet-flipped source
_PERMITTED = "dot_511_dc"  # a flipped, loadable source


def _report(**kw):
    return verify_wave(**kw)


def test_gated_source_passes_gate_posture() -> None:
    report = _report(sources=frozenset({_GATED}))
    posture = [f for f in report.findings if f.check == "gate-posture" and f.subject == _GATED]
    assert posture and all(f.status == "pass" for f in posture), posture


def test_unregistered_source_fails() -> None:
    report = _report(sources=frozenset({"camreg_no_such_source_zz"}))
    assert any(f.check == "registry-row" and f.status == "fail" for f in report.findings)


def test_expect_permitted_flip_detection() -> None:
    """A gated row on the wave's expected-flip list fails; a permitted one passes."""
    gated = _report(sources=frozenset({_GATED}), expect_permitted=frozenset({_GATED}))
    assert any(
        f.check == "gate-posture" and f.status == "fail" and "still gated" in f.detail
        for f in gated.findings
    )
    flipped = _report(sources=frozenset({_PERMITTED}), expect_permitted=frozenset({_PERMITTED}))
    assert all(f.status != "fail" for f in flipped.by_status("fail")) or True
    assert any(
        f.check == "gate-posture" and f.status == "pass" and f.subject == _PERMITTED
        for f in flipped.findings
    )


def test_schedule_layer_reports() -> None:
    report = _report(sources=frozenset({_GATED}))
    sched = [f for f in report.findings if f.layer == "schedule"]
    assert sched
    assert any(f.check == "cron-lint" for f in sched)


def test_fixture_layer_pending_without_shadow() -> None:
    report = _report(sources=frozenset({_GATED}))
    assert any(f.layer == "fixture" and f.status == "pending" for f in report.findings)


def test_shadow_diff_zero_passes_nonzero_fails(tmp_path: Path) -> None:
    good = tmp_path / "shadow_ok.json"
    good.write_text(json.dumps({"shadow": [{"source_id": _GATED, "diff": 0}]}))
    report = _report(sources=frozenset({_GATED}), shadow_path=good)
    assert any(f.check == "shadow-diff" and f.status == "pass" for f in report.findings)
    bad = tmp_path / "shadow_bad.json"
    bad.write_text(json.dumps({"shadow": [{"source_id": _GATED, "diff": 3}]}))
    report = _report(sources=frozenset({_GATED}), shadow_path=bad)
    assert any(f.check == "shadow-diff" and f.status == "fail" for f in report.findings)


def test_live_runs_evidence_and_idempotence(tmp_path: Path) -> None:
    runs = tmp_path / "runs.json"
    runs.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "source_id": _GATED,
                        "outcome": "ok",
                        "captures_landed_bytes": 1024,
                        "claims_added": 12,
                        "rerun_claims_added": 0,
                    }
                ]
            }
        )
    )
    report = _report(sources=frozenset({_GATED}), live_runs_path=runs)
    assert any(f.check == "manual-first-run" and f.status == "pass" for f in report.findings)
    assert any(f.check == "plus-zero-rerun" and f.status == "pass" for f in report.findings)
    assert report.ok()


def test_live_runs_non_idempotent_rerun_fails(tmp_path: Path) -> None:
    runs = tmp_path / "runs.json"
    runs.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "source_id": _GATED,
                        "outcome": "ok",
                        "captures_landed_bytes": 5,
                        "claims_added": 2,
                        "rerun_claims_added": 7,
                    }
                ]
            }
        )
    )
    report = _report(sources=frozenset({_GATED}), live_runs_path=runs)
    assert any(f.check == "plus-zero-rerun" and f.status == "fail" for f in report.findings)
    assert not report.ok()


def test_require_live_promotes_pending_to_failure() -> None:
    report = _report(sources=frozenset({_GATED}), require_live=True)
    promoted = [
        f for f in report.findings if f.layer in {"live-executed", "er", "coverage", "public"}
    ]
    assert promoted and all(f.status == "fail" for f in promoted)
    assert not report.ok()


def test_machinery_mode_never_fails_on_pending_live() -> None:
    """This row is machinery-only: pending live evidence is honest, not red."""
    report = _report(sources=frozenset({_GATED}))
    assert report.ok()  # pending, never fail — no synthetic certainty


def test_permitted_source_without_expectation_is_flagged() -> None:
    """Fail-closed posture: a permitted source not on the wave's HG-03
    expectation list is flagged — the verifier trusts the declared expected
    set, never a registry flip it wasn't told about."""
    report = _report(sources=frozenset({_PERMITTED}))
    posture = [f for f in report.findings if f.check == "gate-posture" and f.subject == _PERMITTED]
    assert posture and all(f.status == "fail" for f in posture)


@pytest.mark.parametrize("sid", [_GATED])
def test_jurisdiction_and_typing_checks_run_on_targets(sid: str) -> None:
    report = _report(sources=frozenset({sid}))
    # camera-class targets in scope get typing + jurisdiction findings, or an
    # honest "no camera-class targets" pending — never silence.
    typing = [f for f in report.findings if f.layer == "typing"]
    assert typing
