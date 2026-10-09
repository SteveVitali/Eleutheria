# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.46 — the ``sig-ops roll-gate`` L2 go/no-go checker (FEA-07, plan §5.9).

The contract's acceptance: the checker **refuses L2 when any threshold
fails or the plan diff is not 0**, tested on recorded inputs. Every
criterion is exercised both ways — a green fixture, then each failure
class as its own case — plus the two invariants the gate exists for:
silence is never consent (no recorded go ⇒ refuse) and the slot does not
start without the P34.39a 10-10 read-back verdict.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from support import REPO_ROOT

from ops import roll_gate

FIXTURES = Path(__file__).parent / "fixtures" / "roll_gate"


def _go_inputs() -> dict:
    return json.loads((FIXTURES / "go.json").read_text(encoding="utf-8"))


def _ids(verdict: roll_gate.Verdict) -> dict[str, bool]:
    return {c.id: c.ok for c in verdict.criteria}


def test_green_inputs_decide_go() -> None:
    v = roll_gate.evaluate(_go_inputs())
    assert v.decision == "go"
    assert v.refusals == []
    record = v.to_record()
    assert record["kind"] == "sig.roll-gate/1"
    assert record["decision"] == "go"
    assert record["rerun_prompt"] is None
    ids = _ids(v)
    for cid in (
        "rehearsal_complete",
        "lock",
        "disk",
        "lock_timeout",
        "plan_diff",
        "readback",
        "backup",
        "go",
        "window",
    ):
        assert ids[cid], f"criterion {cid} should hold on the green fixture"


def test_failed_rehearsal_refuses() -> None:
    """A rehearsal that failed at intake_storage (the P34.24b record's
    shape) certifies nothing — deploy_exit 2 refuses even with a low
    measured lock."""
    inputs = _go_inputs()
    inputs["rehearsal"]["deploy_exit"] = 2
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["rehearsal_complete"]


def test_missing_rehearsal_refuses() -> None:
    inputs = _go_inputs()
    del inputs["rehearsal"]
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["rehearsal_complete"]
    assert not _ids(v)["lock"]  # no measurement to judge


def test_lock_over_twice_baseline_refuses() -> None:
    """The 2x P34.24b bound is the binding ceiling (27.688 s): a 30 s
    hold is far inside 20 min and still refuses — over threshold means
    stop, record, ask; never proceed."""
    inputs = _go_inputs()
    inputs["rehearsal"]["claim_evidence_lock"]["upper_bound_s"] = 30.0
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["lock"]
    assert "2x" in v.to_record()["criteria"][1]["detail"]


def test_lock_at_exact_ceiling_passes() -> None:
    inputs = _go_inputs()
    inputs["rehearsal"]["claim_evidence_lock"]["upper_bound_s"] = 2.0 * roll_gate.BASELINE_BOUND_S
    v = roll_gate.evaluate(inputs)
    assert _ids(v)["lock"]


def test_lock_over_twenty_minutes_refuses() -> None:
    inputs = _go_inputs()
    inputs["rehearsal"]["claim_evidence_lock"]["upper_bound_s"] = 1201.0
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["lock"]


def test_disk_under_twice_table_refuses() -> None:
    inputs = _go_inputs()
    inputs["disk"]["free_bytes"] = int(1.5 * inputs["disk"]["claim_evidence_bytes"])
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["disk"]


def test_lock_timeout_unset_refuses() -> None:
    for bad in (None, 0, "1200000", False):
        inputs = _go_inputs()
        inputs["deploy_session"]["lock_timeout_ms"] = bad
        v = roll_gate.evaluate(inputs)
        assert v.decision == "no-go", f"lock_timeout={bad!r} must refuse"
        assert not _ids(v)["lock_timeout"]


def test_plan_diff_nonzero_refuses() -> None:
    """The deploy set must equal the rehearsed tip — a moved tip queues a
    fresh-clone re-rehearsal, never a deploy of unmeasured changes."""
    inputs = _go_inputs()
    inputs["plan_diff"]["diff_lines"] = 4
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["plan_diff"]


def test_missing_readback_refuses() -> None:
    """live:P34.39a is still queued — no verdict exists; the slot does
    not start without it."""
    inputs = _go_inputs()
    del inputs["readback"]
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["readback"]
    assert "P34.39a" in v.to_record()["criteria"][5]["detail"]


def test_nonpass_readback_refuses() -> None:
    inputs = _go_inputs()
    inputs["readback"]["verdict"] = "fail"
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["readback"]


def test_no_go_recorded_refuses() -> None:
    """Silence is never consent (OM-18): the missing verbatim go is a
    refusal, not a default."""
    inputs = _go_inputs()
    del inputs["go"]
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["go"]

    inputs = _go_inputs()
    inputs["go"]["verbatim"] = "   "
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["go"]


def test_backup_not_successful_refuses() -> None:
    inputs = _go_inputs()
    inputs["backup"]["status"] = "RUNNING"
    v = roll_gate.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["backup"]


@pytest.mark.parametrize(
    "now,ok",
    [
        # future-ok: scheduled: the contract's real L2 window instants (OM-19/AR-3)
        ("2026-10-13T15:00:00Z", False),  # future-ok: scheduled: before the earliest instant
        ("2026-10-14T13:59:59Z", False),  # future-ok: scheduled: inside the day, before the band
        ("2026-10-14T14:00:00Z", True),  # future-ok: scheduled: band opens on the earliest instant
        ("2026-10-14T19:59:59Z", True),  # future-ok: scheduled: inside the band
        ("2026-10-14T20:00:00Z", False),  # future-ok: scheduled: band closed
        ("2026-10-17T15:00:00Z", False),  # future-ok: scheduled: Saturday — operator present rule
        ("2026-10-18T15:00:00Z", False),  # future-ok: scheduled: Sunday
        ("2026-10-19T15:00:00Z", True),  # future-ok: scheduled: a later weekday still holds
    ],
)
def test_window(now: str, ok: bool) -> None:
    inputs = _go_inputs()
    inputs["now"] = now
    v = roll_gate.evaluate(inputs)
    assert _ids(v)["window"] is ok, f"now={now}: window={_ids(v)['window']}"
    if not ok:
        assert v.decision == "no-go"


def test_window_needs_an_instant() -> None:
    inputs = _go_inputs()
    del inputs["now"]
    v = roll_gate.evaluate(inputs)
    assert not _ids(v)["window"]
    assert v.decision == "no-go"


def test_record_shape_and_rerun_prompt() -> None:
    inputs = _go_inputs()
    del inputs["go"]
    record = roll_gate.evaluate(inputs).to_record()
    assert record["decision"] == "no-go"
    assert record["rerun_prompt"].startswith("implement-spec spec=docs/tickets/258_")
    assert any(r.startswith("go:") for r in record["refusals"])
    assert record["thresholds"]["lock_ceiling_s"] == 1200


def test_malformed_inputs_raise() -> None:
    inputs = _go_inputs()
    inputs["now"] = "not-a-date"
    with pytest.raises(roll_gate.RollGateError):
        roll_gate.evaluate(inputs)
    with pytest.raises(roll_gate.RollGateError):
        roll_gate.evaluate({"disk": {"free_bytes": "lots", "claim_evidence_bytes": 1}})


def test_cli_green_and_queued(tmp_path: Path) -> None:
    out = tmp_path / "verdict.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ops",
            "roll-gate",
            "--inputs",
            str(FIXTURES / "go.json"),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["decision"] == "go"

    bad = tmp_path / "no-go.json"
    inputs = _go_inputs()
    inputs["plan_diff"]["diff_lines"] = 7
    bad.write_text(json.dumps(inputs), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "ops", "roll-gate", "--inputs", str(bad)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 42, (proc.returncode, proc.stderr, proc.stdout)
    assert "NO-GO" in proc.stderr
