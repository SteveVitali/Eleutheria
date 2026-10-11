# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.11 — the ``sig-ops wave-a-gate`` leg go/no-go + the Wave-A step plan.

The contract's acceptance: the checker **refuses a leg when any criterion
fails** — no recorded ING-GO-A (silence is never consent), outside the
2026-10-19→23 14:00–20:00Z window, a skipped leg (``completed`` is not the
ordered prefix), an undeclared or never-in-wave source (``doj_ctas_awards``
/ AP-T2-093), a screened-lane source outside the wave-open HG-03 flip list
or without the no-human-review disclosure, the Legistar trigger un-paused
before its in-window fire, a concurrent ``sig-materialize`` or manual run,
and — on L1 — a missing/failed AR-2 backup or pre-state capture. The plan
itself is deterministic and serialises the manual first runs one at a
time. Every criterion is exercised both ways.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

from support import REPO_ROOT

from ops import wave_a

FIXTURES = Path(__file__).parent / "fixtures" / "wave_a"


def _go_inputs() -> dict:
    return json.loads((FIXTURES / "go.json").read_text(encoding="utf-8"))


def _ids(verdict: wave_a.Verdict) -> dict[str, bool]:
    return {c.id: c.ok for c in verdict.criteria}


def test_green_inputs_decide_go() -> None:
    v = wave_a.evaluate(_go_inputs())
    assert v.decision == "go"
    assert v.refusals == []
    record = v.to_record()
    assert record["kind"] == "sig.wave-a-gate/1"
    assert record["wave"] == "A"
    assert record["decision"] == "go"
    assert record["rerun_prompt"] is None
    ids = _ids(v)
    for cid in (
        "go",
        "window",
        "leg",
        "scope",
        "screened",
        "trigger",
        "serialize",
        "backup",
        "prestate",
    ):
        assert ids[cid], f"criterion {cid} should hold on the green fixture"


def test_screened_lane_with_flip_and_disclosure_goes() -> None:
    """The ADR-185 lane runs only as recorded: flip-listed + disclosed."""
    v = wave_a.evaluate(json.loads((FIXTURES / "go-screened.json").read_text(encoding="utf-8")))
    assert v.decision == "go"
    assert _ids(v)["screened"]


# --- silence is never consent -------------------------------------------------


def test_missing_go_refuses() -> None:
    inputs = _go_inputs()
    del inputs["go"]
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["go"]
    assert "implement-spec" in v.to_record()["rerun_prompt"]


def test_empty_verbatim_refuses() -> None:
    inputs = _go_inputs()
    inputs["go"]["verbatim"] = "   "
    assert wave_a.evaluate(inputs).decision == "no-go"


# --- the window ----------------------------------------------------------------


def test_before_window_refuses() -> None:
    inputs = _go_inputs()
    inputs["now"] = "2026-10-19T13:59:59Z"
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["window"]


def test_after_window_refuses() -> None:
    inputs = _go_inputs()
    inputs["now"] = "2026-10-24T15:00:00Z"
    assert not _ids(wave_a.evaluate(inputs))["window"]


def test_outside_daily_band_refuses() -> None:
    inputs = _go_inputs()
    inputs["now"] = "2026-10-20T06:00:00Z"  # in-window day, outside 14:00–20:00Z
    assert not _ids(wave_a.evaluate(inputs))["window"]


def test_window_edge_instants() -> None:
    inputs = _go_inputs()
    inputs["now"] = "2026-10-19T14:00:00Z"  # the opening instant — admitted
    assert _ids(wave_a.evaluate(inputs))["window"]
    inputs["now"] = "2026-10-23T19:59:59Z"  # the closing instant — admitted
    assert _ids(wave_a.evaluate(inputs))["window"]
    inputs["now"] = "2026-10-23T20:00:00Z"  # exclusive end — refused
    assert not _ids(wave_a.evaluate(inputs))["window"]


# --- leg order: a missed leg is reported, never silently skipped ------------------


def test_l2_requires_l1_green() -> None:
    inputs = _go_inputs()
    inputs["leg"] = "L2"
    assert not _ids(wave_a.evaluate(inputs))["leg"]
    inputs["completed"] = ["L1"]
    assert _ids(wave_a.evaluate(inputs))["leg"]


def test_l3_requires_l1_and_l2_green() -> None:
    inputs = _go_inputs()
    inputs["leg"] = "L3"
    inputs["completed"] = ["L1"]
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["leg"]
    inputs["completed"] = ["L1", "L2"]
    assert _ids(wave_a.evaluate(inputs))["leg"]


def test_out_of_order_completed_refuses() -> None:
    inputs = _go_inputs()
    inputs["leg"] = "L3"
    inputs["completed"] = ["L2", "L1"]
    assert not _ids(wave_a.evaluate(inputs))["leg"]


def test_unknown_leg_refuses() -> None:
    inputs = _go_inputs()
    inputs["leg"] = "L4"
    assert not _ids(wave_a.evaluate(inputs))["leg"]


# --- scope: the declared wave set only ---------------------------------------------


def test_doj_ctas_awards_never_in_wave() -> None:
    """AP-T2-093 is not tribal — D-R11-LATER-09; never rolled in Wave A."""
    inputs = _go_inputs()
    inputs["run_set"] = ["legistar", "doj_ctas_awards"]
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["scope"]
    assert "doj_ctas_awards" in str(v.refusals)


def test_undeclared_source_refuses() -> None:
    inputs = _go_inputs()
    inputs["run_set"] = ["legistar", "nyc_cameras"]
    assert not _ids(wave_a.evaluate(inputs))["scope"]


# --- the screened lane: flip-list gated + disclosed ---------------------------------


def test_screened_without_flip_refuses() -> None:
    inputs = _go_inputs()
    inputs["flip_list"] = []  # the wave-open list did not name it
    inputs["run_set"] = ["camreg_tribal_all_leaders_directory"]
    inputs["screened_disclosure"] = True
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["screened"]


def test_screened_without_disclosure_refuses() -> None:
    inputs = _go_inputs()
    inputs["run_set"] = ["camreg_tribal_all_leaders_directory"]
    inputs["screened_disclosure"] = False
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["screened"]


# --- the Legistar trigger mitigation ---------------------------------------------------


def test_unpaused_trigger_before_fire_refuses() -> None:
    inputs = _go_inputs()
    inputs["legistar_trigger"] = {"paused": False}
    inputs["now"] = "2026-10-19T15:00:00Z"  # before the 10-20 05:00Z fire
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["trigger"]


def test_unpaused_trigger_after_fire_admits() -> None:
    inputs = _go_inputs()
    inputs["legistar_trigger"] = {"paused": False}
    inputs["now"] = "2026-10-20T15:00:00Z"  # the 05:00Z fire already happened
    assert _ids(wave_a.evaluate(inputs))["trigger"]


def test_trigger_criterion_is_l1_only() -> None:
    """L2/L3 don't re-judge the mitigation (L3 is the resume itself)."""
    inputs = _go_inputs()
    inputs["leg"] = "L2"
    inputs["completed"] = ["L1"]
    inputs["legistar_trigger"] = {"paused": False}
    ids = _ids(wave_a.evaluate(inputs))
    assert "trigger" not in ids


# --- serialisation ---------------------------------------------------------------------


def test_materialize_active_refuses() -> None:
    inputs = _go_inputs()
    inputs["materialize_active"] = True
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["serialize"]


def test_active_manual_run_refuses() -> None:
    inputs = _go_inputs()
    inputs["active_manual_run"] = "legistar"
    assert not _ids(wave_a.evaluate(inputs))["serialize"]


# --- L1-only prerequisites ---------------------------------------------------------------


def test_failed_backup_refuses_l1() -> None:
    inputs = _go_inputs()
    inputs["backup"]["status"] = "FAILED"
    v = wave_a.evaluate(inputs)
    assert v.decision == "no-go"
    assert not _ids(v)["backup"]


def test_missing_backup_refuses_l1() -> None:
    inputs = _go_inputs()
    del inputs["backup"]
    assert not _ids(wave_a.evaluate(inputs))["backup"]


def test_missing_prestate_refuses_l1() -> None:
    inputs = _go_inputs()
    del inputs["prestate"]
    assert not _ids(wave_a.evaluate(inputs))["prestate"]


def test_red_cadence_check_refuses_l1() -> None:
    inputs = _go_inputs()
    inputs["prestate"]["cadence_check_ok"] = False
    assert not _ids(wave_a.evaluate(inputs))["prestate"]


def test_backup_and_prestate_not_required_on_l2() -> None:
    inputs = _go_inputs()
    inputs["leg"] = "L2"
    inputs["completed"] = ["L1"]
    del inputs["backup"]
    del inputs["prestate"]
    ids = _ids(wave_a.evaluate(inputs))
    assert "backup" not in ids and "prestate" not in ids


# --- the deterministic plan -----------------------------------------------------------------


def test_plan_serialises_manual_runs_one_at_a_time() -> None:
    steps = wave_a.leg_plan()
    # the plan is ordered within each leg
    for i, s in enumerate(steps[1:], 1):
        assert s["leg"] != steps[i - 1]["leg"] or s["seq"] > steps[i - 1]["seq"]
    # every manual/screened run step is followed by a verify step
    for i, s in enumerate(steps):
        if s["kind"] in ("manual", "screened"):
            assert steps[i + 1]["kind"] == "verify"
            assert steps[i + 1]["source"] == s["source"]


def test_plan_order_and_leg_membership() -> None:
    steps = wave_a.leg_plan()
    legs = [s["leg"] for s in steps]
    assert legs == sorted(legs, key=lambda leg: wave_a.LEGS.index(leg))
    manual_l1 = [s["source"] for s in steps if s["kind"] == "manual"]
    assert manual_l1 == ["legistar", "usaspending", "procportal_nyc_ny"]
    screened = [s["source"] for s in steps if s["kind"] == "screened"]
    assert screened == list(wave_a.SCREENED_SOURCES)
    # the screened steps are marked contingent on the wave-open flip list
    for s in steps:
        if s["kind"] == "screened":
            assert s["contingent"] == "flip_list"
    # doj_ctas_awards (AP-T2-093) never appears anywhere in the plan
    assert "doj_ctas_awards" not in json.dumps(steps)


def test_plan_names_the_seed_and_trigger() -> None:
    steps = wave_a.leg_plan()
    blob = json.dumps(steps)
    assert wave_a.SEED_SOURCE in blob
    assert wave_a.LEGISTAR_TRIGGER in blob


# --- the CLI surface ---------------------------------------------------------------------------


def _cli(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ops", *argv],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin", "HOME": "/tmp"},
    )


def test_cli_go_exits_zero() -> None:
    proc = _cli("wave-a-gate", "--inputs", str(FIXTURES / "go.json"))
    assert proc.returncode == 0, proc.stderr
    record = json.loads(proc.stdout)
    assert record["kind"] == "sig.wave-a-gate/1"
    assert record["decision"] == "go"


def test_cli_nogo_exits_42() -> None:
    bad = dict(_go_inputs())
    bad["leg"] = "L3"  # L1/L2 never recorded — the leg refuses, never skips
    path = FIXTURES / f"_tmp_{uuid.uuid4().hex}.json"
    path.write_text(json.dumps(bad))
    try:
        proc = _cli("wave-a-gate", "--inputs", str(path))
    finally:
        path.unlink()
    assert proc.returncode == 42
    assert "NO-GO" in proc.stderr
    assert "implement-spec" in proc.stdout


def test_cli_bad_inputs_exit_2() -> None:
    path = FIXTURES / f"_tmp_{uuid.uuid4().hex}.json"
    path.write_text("{not json")
    try:
        proc = _cli("wave-a-gate", "--inputs", str(path))
    finally:
        path.unlink()
    assert proc.returncode == 2


def test_cli_plan_prints_all_legs() -> None:
    proc = _cli("wave-a-plan")
    assert proc.returncode == 0
    assert "L1" in proc.stdout and "L2" in proc.stdout and "L3" in proc.stdout
    proc = _cli("wave-a-plan", "--json")
    record = json.loads(proc.stdout)
    assert record["kind"] == "sig.wave-a-plan/1"
    assert record["wave"] == "A"


def test_check_mode_driver_needs_no_adc() -> None:
    """`wave-a.sh --check` is plan-only: no ADC, no network, exit 0."""
    proc = subprocess.run(
        ["bash", "ops/gcp/wave-a.sh", "--check"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PLAN ONLY" in proc.stdout
    assert "implement-spec" in proc.stdout
