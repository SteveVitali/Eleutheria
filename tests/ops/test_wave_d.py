# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.54 — Wave-D activation machinery (``ops/src/ops/wave_d.py``).

Fixture-layer tests: the deterministic plan, the fail-closed
``sig.wave-d-gate/1`` criteria over recorded inputs, and the registry
coherence of the declared leg sets against the committed cadence rows.
No test asserts the state of a living record (OM-15); the registry
reads assert the committed fail-closed baseline only.
"""

from __future__ import annotations

import datetime as _dt
import tomllib
from pathlib import Path

import pytest

from ops import wave_d

REPO = Path(__file__).resolve().parents[2]

DAY1 = "2026-11-23"  # future-ok: scheduled: window-1 date
DAY2 = "2026-11-24"  # future-ok: scheduled: window-1 date
DAY3 = "2026-11-25"  # future-ok: scheduled: window-1 date
NOW_W1 = "2026-11-23T15:00:00Z"  # future-ok: scheduled: inside window 1
NOW_W2 = "2026-12-16T15:00:00Z"  # future-ok: scheduled: inside window 2
GO = {"verbatim": wave_d.GO_VERBATIM, "recorded_at": "2026-11-05T15:20:00Z"}


def _base(leg: str = "L1", **kw):
    """A complete admit-shaped inputs dict for `leg` (mutate via kw).

    Earlier legs complete on sequential days from 2026-11-23 — future-ok: scheduled: window-1 dates;
    `now` defaults to the day after the last completed leg (still inside
    the window for every leg — the family legs fit 11-23…12-02).
    """
    idx = wave_d.LEGS.index(leg)
    base_day = _dt.date(2026, 11, 23)  # future-ok: scheduled: window-1 open
    completed = [
        {"leg": prior, "day": (base_day + _dt.timedelta(days=i)).isoformat()}
        for i, prior in enumerate(wave_d.LEGS[:idx])
    ]
    inputs = {
        "action": "admit",
        "leg": leg,
        "completed": completed,
        "held_reports": {},
        "now": (base_day + _dt.timedelta(days=idx)).isoformat() + "T15:00:00Z",
        "go": dict(GO),
        "run_set": sorted(wave_d.LEG_SCOPE.get(leg, {}).get("gated", ())),
        "flips": {
            leg: {
                "executed": sorted(wave_d.LEG_SCOPE.get(leg, {}).get("gated", ())),
                "confirmed": "OP-26 signed commit ref",
            }
        }
        if leg in wave_d.FAMILY_LEGS
        else {},
        "materialize_active": False,
        "g2_slot_active": False,
        "release_cut_active": False,
        "active_manual_run": None,
    }
    if leg == "L0":
        inputs["run_set"] = []
        inputs["prestate"] = {"captured": True, "cadence_check_ok": True}
        inputs["backup"] = {"status": "SUCCESSFUL", "id": "b1"}
    if leg == "L11":
        inputs["run_set"] = sorted(wave_d.BATCHES)
    inputs.update(kw)
    return inputs


def _family_close(leg: str, **kw):
    """A complete close-shaped inputs dict for a family leg."""
    inputs = _base(leg, action="close")
    run_set = sorted(wave_d.LEG_SCOPE[leg]["gated"])
    inputs["runs"] = {s: {"outcome": "ok", "claims_added": 5, "captures": 1} for s in run_set}
    inputs["plus0"] = {s: {"claims_added": 0} for s in run_set}
    inputs["changed_count"] = {"recorded": True, "value": 5 * len(run_set)}
    inputs.update(kw)
    return inputs


# ---------------------------------------------------------------- plan ----


def test_plan_schema_and_steps():
    steps = wave_d.leg_plan()
    assert steps, "the plan is never empty"
    legs = [s["leg"] for s in steps]
    assert legs[0] == "L0" and legs[-1] == "L11"
    for leg in wave_d.FAMILY_LEGS:
        leg_steps = [s for s in steps if s["leg"] == leg]
        assert leg_steps[0]["kind"] == "flips"
        assert leg_steps[-1]["kind"] == "record"
        manuals = [s for s in leg_steps if s["kind"] == "manual"]
        assert {s["source"] for s in manuals} == set(wave_d.LEG_SCOPE[leg]["gated"])
    mutations = [s for s in steps if s.get("mutation")]
    assert len(mutations) > 0


def test_plan_l0_is_opening_and_l11_is_closing():
    steps = wave_d.leg_plan()
    l0 = [s for s in steps if s["leg"] == "L0"]
    assert [s["kind"] for s in l0] == ["prestate", "backup", "roll", "jobs", "handoff"]
    l11 = [s for s in steps if s["leg"] == "L11"]
    assert [s["kind"] for s in l11] == [
        "materialize",
        "coverage",
        "resume",
        "record",
    ]


def test_every_gated_source_resolves_a_job_and_batch():
    assert set(wave_d.FLIP_SOURCES) == {
        s for leg in wave_d.FAMILY_LEGS for s in wave_d.LEG_SCOPE[leg]["gated"]
    }
    for sid in wave_d.FLIP_SOURCES:
        assert wave_d.EXECUTION_JOB[sid].startswith("sig-ingest-r11-tier2-")
    for sid in wave_d.LEG_SCOPE["L10"]["gated"]:
        assert wave_d.EXECUTION_JOB[sid] == wave_d.SEATLESS_JOB


def test_leg_scope_matches_committed_cadence_membership():
    """The declared sets partition the committed tier-2 members (minus the
    dossier seats) exactly — the machinery never drifts from the registry."""
    cad = tomllib.loads((REPO / "ops/cadence.toml").read_text(encoding="utf-8"))
    members = {
        m
        for b in cad.get("batches", [])
        if str(b.get("id", "")).startswith("r11-tier2")
        for m in b.get("members", [])
    }
    seatless = set(wave_d.LEG_SCOPE["L10"]["gated"])
    gated = set(wave_d.FLIP_SOURCES)
    assert members == (gated - seatless) | set(wave_d.DOSSIER_SEATS)
    assert not (members & seatless)
    assert len(gated) == 146
    for sid, batch in wave_d.SOURCE_BATCH.items():
        assert sid in members
        row = next(b for b in cad["batches"] if b["id"] == batch)
        assert sid in row["members"]
        assert row["state"] == "paused"  # R6 declared-inert until the resume


def test_never_sources_cover_dossier_and_deferred():
    for sid in wave_d.DOSSIER_SEATS:
        assert sid in wave_d.NEVER_SOURCES
    assert "doj_ctas_awards" in wave_d.NEVER_SOURCES
    assert "camreg_tribal_all_leaders_directory" in wave_d.NEVER_SOURCES


def test_committed_registry_rows_stay_fail_closed():
    """Every Wave-D gated source's committed row is not ingestion-permitted —
    the machinery flips nothing (HG-03 is the operator's)."""
    srcs = tomllib.loads(
        (REPO / "connectors/src/connectors/data/sources.toml").read_text(encoding="utf-8")
    )["sources"]
    for sid in wave_d.FLIP_SOURCES:
        assert sid in srcs, f"{sid} must be registered"
        assert srcs[sid].get("ingestion_permitted") is not True


# ---------------------------------------------------------------- gate ----


def test_admit_l0_green():
    assert wave_d.evaluate(_base("L0")).decision == "go"


@pytest.mark.parametrize("leg", wave_d.FAMILY_LEGS)
def test_admit_family_leg_green(leg):
    assert wave_d.evaluate(_base(leg)).decision == "go"


def test_window_both_spans_admit():
    # window-2 admit of a held leg: completed days are window-1, now in window 2
    inputs = _base("L5", now=NOW_W2)
    assert wave_d.evaluate(inputs).decision == "go"


def test_window_refuses_freeze_band_and_cut_day():
    assert (
        wave_d.evaluate(
            _base("L1", now="2026-12-08T15:00:00Z")  # future-ok: scheduled: freeze day
        ).decision
        == "no-go"
    )
    assert (
        wave_d.evaluate(
            _base("L1", now="2026-11-23T07:00:00Z")  # future-ok: scheduled: window day
        ).decision
        == "no-go"
    )  # outside the 14:00–20:00Z band
    assert (
        wave_d.evaluate(
            _base("L1", now="2026-12-15T15:00:00Z")  # future-ok: scheduled: cut day
        ).decision
        == "no-go"
    )


def test_completed_day_must_be_admissible():
    inputs = _base(
        "L1",
        completed=[{"leg": "L0", "day": "2026-12-10"}],  # future-ok: scheduled: freeze day
    )
    assert wave_d.evaluate(inputs).decision == "no-go"
    inputs = _base(
        "L1",
        completed=[{"leg": "L0", "day": "2026-12-15"}],  # future-ok: scheduled: cut day
    )
    assert wave_d.evaluate(inputs).decision == "no-go"


def test_go_must_be_byte_exact():
    bad = _base("L1", go={"verbatim": "approve ing-go-d", "recorded_at": "2026-11-05T15:20:00Z"})
    v = wave_d.evaluate(bad)
    assert v.decision == "no-go"
    assert any(c.id == "go" and not c.ok for c in v.criteria)
    assert v.refusals and "wave-d" in v.to_record()["rerun_prompt"]


def test_order_requires_every_earlier_leg():
    inputs = _base("L3", completed=[{"leg": "L0", "day": DAY1}])  # L1/L2 missing
    v = wave_d.evaluate(inputs)
    assert v.decision == "no-go"
    assert any(c.id == "order" and not c.ok for c in v.criteria)


def test_held_leg_unblocks_the_chain_but_not_itself():
    completed = [{"leg": "L0", "day": DAY1}, {"leg": "L1", "day": DAY2}]
    inputs = _base("L3", completed=completed, held_reports={"L2": "runs/P37.54.md#L2-held"})
    assert wave_d.evaluate(inputs).decision == "go"
    held_no_ref = _base("L3", completed=completed, held_reports={"L2": ""})
    assert wave_d.evaluate(held_no_ref).decision == "no-go"


def test_leg_recorded_twice_refuses():
    inputs = _base("L1", completed=[{"leg": "L0", "day": DAY1}, {"leg": "L1", "day": DAY2}])
    assert wave_d.evaluate(inputs).decision == "no-go"


def test_pacing_one_family_per_day():
    # L0's opening shares a family day freely; two family legs never do.
    assert wave_d.evaluate(_base("L4")).decision == "go"
    two_same_day = _base(
        "L3",
        completed=[
            {"leg": "L0", "day": DAY1},
            {"leg": "L1", "day": DAY2},
            {"leg": "L2", "day": DAY2},  # L1 + L2 share a family day — refused
        ],
        now=DAY3 + "T15:00:00Z",
    )
    assert wave_d.evaluate(two_same_day).decision == "no-go"


def test_scope_exact_set():
    run_set = sorted(wave_d.LEG_SCOPE["L1"]["gated"])
    assert wave_d.evaluate(_base("L1", run_set=run_set[:-1])).decision == "no-go"
    assert wave_d.evaluate(_base("L1", run_set=run_set + ["bogus_source"])).decision == "no-go"
    assert (
        wave_d.evaluate(_base("L1", run_set=run_set[:-1] + [wave_d.DOSSIER_SEATS[0]])).decision
        == "no-go"
    )
    assert (
        wave_d.evaluate(_base("L1", run_set=run_set[:-1] + ["doj_ctas_awards"])).decision == "no-go"
    )


def test_l0_scope_is_empty_and_l11_is_the_batches():
    assert wave_d.evaluate(_base("L0", run_set=["axon_connect"])).decision == "no-go"
    bad = _base("L11", run_set=["r11-tier2-01"])
    assert wave_d.evaluate(bad).decision == "no-go"


def test_flips_required_and_complete():
    v = wave_d.evaluate(_base("L1", flips={}))
    assert v.decision == "no-go"
    assert any(c.id == "flips" and not c.ok for c in v.criteria)
    partial = _base(
        "L1",
        flips={"L1": {"executed": ["axon_connect"], "confirmed": "ref"}},
    )
    assert wave_d.evaluate(partial).decision == "no-go"
    unconf = _base(
        "L1",
        flips={
            "L1": {
                "executed": sorted(wave_d.LEG_SCOPE["L1"]["gated"]),
                "confirmed": "",
            }
        },
    )
    assert wave_d.evaluate(unconf).decision == "no-go"


def test_serialize_one_manual_run():
    v = wave_d.evaluate(_base("L1", active_manual_run="sig-materialize"))
    assert v.decision == "no-go"
    assert any(c.id == "serialize" and not c.ok for c in v.criteria)


def test_l0_requires_prestate_and_successful_backup():
    v = wave_d.evaluate(_base("L0", prestate={"captured": False}))
    assert v.decision == "no-go"
    assert any(c.id == "prestate" and not c.ok for c in v.criteria)
    v = wave_d.evaluate(_base("L0", backup={"status": "FAILED"}))
    assert v.decision == "no-go"
    assert any(c.id == "backup" and not c.ok for c in v.criteria)


# --------------------------------------------------------------- close ----


def test_l0_close_requires_roll_jobs_handoff():
    inputs = _base(
        "L0",
        action="close",
        roll={
            "image_digest": "sha256:" + "a" * 64,
            "before_after_recorded": True,
        },
        jobs_created={b: {"created": True, "paused": True} for b in wave_d.BATCHES},
        flip_list=sorted(wave_d.FLIP_SOURCES),
        flip_handoff={"list_ref": "docs/build/reports/WAVE_D_FLIP_LIST.md"},
    )
    assert wave_d.evaluate(inputs).decision == "go"
    incomplete = dict(inputs, flip_list=["axon_connect"])
    assert wave_d.evaluate(incomplete).decision == "no-go"
    bad_digest = dict(inputs, roll={"image_digest": "latest", "before_after_recorded": True})
    assert wave_d.evaluate(bad_digest).decision == "no-go"


def test_family_close_requires_runs_plus0_evidence():
    inputs = _family_close("L6")
    assert wave_d.evaluate(inputs).decision == "go"
    zero = _family_close(
        "L6",
        runs={
            s: {"outcome": "ok", "claims_added": 0, "captures": 1}
            for s in wave_d.LEG_SCOPE["L6"]["gated"]
        },
        empty_run_notes={
            s: "the enumerated seat recorded a bounded outcome"
            for s in wave_d.LEG_SCOPE["L6"]["gated"]
        },
    )
    assert wave_d.evaluate(zero).decision == "go"
    no_note = dict(zero, empty_run_notes={})
    v = wave_d.evaluate(no_note)
    assert v.decision == "no-go"
    assert any(c.id == "runs" and not c.ok for c in v.criteria)
    no_plus0 = _family_close("L6", plus0={})
    assert wave_d.evaluate(no_plus0).decision == "no-go"


def test_l11_close_requires_resume_records():
    inputs = _base(
        "L11",
        action="close",
        materialize={
            "ran": True,
            "at": "2026-12-16T18:00:00Z",  # future-ok: scheduled: window-2 day
        },
        coverage_delta={"recorded": True, "ref": "delta-ref"},
        cadence_state_enabled={b: True for b in wave_d.BATCHES},
        declaration_republished=True,
        next_fires={b: s["next_fire"] for b, s in wave_d.BATCHES.items()},
    )
    assert wave_d.evaluate(inputs).decision == "go"
    for mutate in (
        lambda i: i.update(cadence_state_enabled={"r11-tier2-01": True}),
        lambda i: i.update(declaration_republished=False),
        lambda i: i.update(
            next_fires={
                "r11-tier2-01": "2026-12-26T07:37:00Z",  # future-ok: scheduled: wrong stamp refuses
            }
        ),
        lambda i: i.update(materialize={"ran": False}),
    ):
        bad = _base(
            "L11",
            action="close",
            materialize={
                "ran": True,
                "at": "2026-12-16T18:00:00Z",  # future-ok: scheduled: window-2 day
            },
            coverage_delta={"recorded": True},
            cadence_state_enabled={b: True for b in wave_d.BATCHES},
            declaration_republished=True,
            next_fires={b: s["next_fire"] for b, s in wave_d.BATCHES.items()},
        )
        mutate(bad)
        assert wave_d.evaluate(bad).decision == "no-go"


def test_verdict_record_shape_and_rerun_prompt():
    v = wave_d.evaluate(_base("L1", flips={}))
    rec = v.to_record()
    assert rec["kind"] == "sig.wave-d-gate/1"
    assert rec["wave"] == "D"
    assert rec["decision"] == "no-go"
    assert "live_verification=true" in rec["rerun_prompt"]
    assert "481_P37.54" in rec["rerun_prompt"]
    assert len(rec["thresholds"]["windows"]) == 2
    assert rec["thresholds"]["flip_source_count"] == 146
    go = wave_d.evaluate(_base("L0"))
    assert go.to_record()["rerun_prompt"] is None


def test_usage_errors_exit_2_via_main(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"action": "fly"}', encoding="utf-8")
    assert wave_d.gate_main(["--inputs", str(bad)]) == 2
    missing = wave_d.gate_main(["--inputs", str(tmp_path / "none.json")])
    assert missing == 2


def test_gate_main_go_and_nogo(tmp_path):
    good = tmp_path / "go.json"
    import json

    good.write_text(json.dumps(_base("L0")), encoding="utf-8")
    assert wave_d.gate_main(["--inputs", str(good)]) == 0
    bad = tmp_path / "nogo.json"
    bad.write_text(json.dumps(_base("L1", flips={})), encoding="utf-8")
    assert wave_d.gate_main(["--inputs", str(bad)]) == 42
