# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.12 — the ``sig-ops wave-b-gate`` leg go/no-go + the Wave-B step plan.

The contract's acceptance: the gate **refuses a leg when any criterion
fails** — no recorded verbatim ING-GO-B (silence is never consent; a
paraphrase is a refusal), outside the 2026-10-26→11-05 14:00–20:00Z (future-ok: scheduled: w)
window (future-ok: scheduled: the contract window), inside an AR-3
freeze/cut day/the 03:00–06:30Z band, a skipped leg (``completed``
doesn't cover every earlier leg — green *or held*), a non-exact
``run_set``, a family leg whose OP-26 flips are absent/incomplete/
unconfirmed, a second family on one day (only L4+L8 may share), a
concurrent ``sig-materialize``/G2/manual run, the uncleared 10-29
peel-on fire, L0's missing prestate/backup, and L3's unregistered
``enforcement_count``. Every criterion is exercised both ways.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

from support import REPO_ROOT

from ops import wave_b

FIXTURES = Path(__file__).parent / "fixtures" / "wave_b"

_DAYS = {
    "L0": "2026-10-26",  # future-ok: scheduled: window day
    "L1": "2026-10-26",  # future-ok: scheduled: window day
    "L2": "2026-10-27",  # future-ok: scheduled: window day
    "L3": "2026-10-28",  # future-ok: scheduled: window day
    "L4": "2026-10-29",  # future-ok: scheduled: window day
    "L5": "2026-10-30",  # future-ok: scheduled: window day
    "L6": "2026-10-31",  # future-ok: scheduled: window day
    "L7": "2026-11-01",  # future-ok: scheduled: window day
    "L8": "2026-11-02",  # future-ok: scheduled: window day
    "L9": "2026-11-03",  # future-ok: scheduled: window day
    "L10": "2026-11-04",  # future-ok: scheduled: window day
}


def _declared(leg: str) -> tuple[str, ...]:
    scope = wave_b.LEG_SCOPE[leg]
    return scope["gated"] + scope["hosted"] + scope["widen"]


def _flip_rows(leg: str) -> tuple[str, ...]:
    scope = wave_b.LEG_SCOPE[leg]
    return scope["gated"] + scope["hosted"]


def _schedulers() -> list[str]:
    return [spec["scheduler"] for spec in wave_b.BATCHES.values()]


def _completed_upto(leg: str) -> list[dict[str, str]]:
    return [
        {"leg": lid, "day": _DAYS[lid]}
        for lid in wave_b.LEGS
        if wave_b.LEGS.index(lid) < wave_b.LEGS.index(leg)
    ]


def _admit(leg: str = "L0", **over) -> dict:
    """A green ``action=admit`` input for ``leg`` — all earlier legs green."""
    inputs: dict = {
        "action": "admit",
        "leg": leg,
        "completed": _completed_upto(leg),
        "now": f"{_DAYS[leg]}T15:00:00Z",
        "go": {"verbatim": wave_b.GO_VERBATIM, "recorded_at": "2026-10-15T15:26:00Z"},
        "peel_fire_cleared": True,
        "materialize_active": False,
        "g2_slot_active": False,
        "release_cut_active": False,
        "active_manual_run": None,
    }
    if leg == "L10":
        inputs["run_set"] = _schedulers()
    elif leg in wave_b.LEG_SCOPE:
        inputs["run_set"] = list(_declared(leg))
    if leg in wave_b.FAMILY_LEGS:
        inputs["flips"] = {
            leg: {
                "executed": list(_flip_rows(leg)),
                "confirmed": f"docs/build/reports/WAVE_B_FLIP_LIST.md#{leg.lower()}",
            }
        }
    if leg == "L3":
        inputs["vocab"] = {"enforcement_count": {"registered": True, "verified": True}}
    if leg == "L0":
        inputs["prestate"] = {
            "captured": True,
            "cadence_check_ok": True,
            "path": "pre/wave-b-2026-10-26/",  # future-ok: scheduled: window day
        }
        inputs["backup"] = {
            "status": "SUCCESSFUL",
            "id": "1793000000001",
            "type": "ON_DEMAND",
        }
    inputs.update(over)
    return inputs


def _close_family(leg: str = "L1", **over) -> dict:
    """A green ``action=close`` input for a family leg (L1–L8)."""
    inputs = _admit(leg, action="close")
    inputs["runs"] = {sid: {"outcome": "ok", "claims_added": 5} for sid in _declared(leg)}
    inputs["plus0"] = {sid: {"claims_added": 0} for sid in _declared(leg)}
    inputs["changed_count"] = {"recorded": True}
    inputs.update(over)
    return inputs


def _close_l0(**over) -> dict:
    inputs = _admit("L0", action="close")
    inputs["roll"] = {
        "image_digest": "sha256:" + "a" * 64,
        "before_after_recorded": True,
    }
    inputs["jobs_created"] = {b: {"created": True, "paused": True} for b in wave_b.BATCHES}
    inputs["vocab"] = {"enforcement_count": {"registered": True, "verified": True}}
    inputs["flip_list"] = list(wave_b.FLIP_SOURCES)
    inputs["flip_handoff"] = {"list_ref": "docs/build/reports/WAVE_B_FLIP_LIST.md"}
    inputs.update(over)
    return inputs


def _probe_record(*, served: int = 0, challenged_at: int | None = None) -> dict:
    """A synthetic sig.probe-run/1 record in the connector's real shape.

    ``challenged_at`` models WV-10's stop-and-record: the sweep halts at
    that portal and the rest land ``not_attempted``.
    """
    n = wave_b.PROBE_INVENTORY
    results: list[dict] = []
    refused_n = n - served
    if challenged_at is not None:
        refused_n = 1
    for i in range(n):
        if i < served:
            results.append({"portal": f"portal-{i:04d}", "result": "served"})
        elif i < served + refused_n:
            results.append(
                {
                    "portal": f"portal-{i:04d}",
                    "result": "refused",
                    "refusal_kind": "challenge",
                }
            )
        else:
            results.append({"portal": f"portal-{i:04d}", "result": "not_attempted"})
    attempted = served + refused_n
    return {
        "version": "sig.probe-run/1",
        "inventory": {"portal_count": n},
        "results": results,
        "checks": {
            "coverage": {"verdict": "pass", "attempted": attempted},
            "served": {"count": served},
            "refusals": {"count": refused_n, "deferred": 0},
        },
    }


def _close_l9(**over) -> dict:
    inputs = _admit("L9", action="close")
    inputs["probe_run"] = _probe_record()
    inputs.update(over)
    return inputs


def _close_l10(**over) -> dict:
    inputs = _admit("L10", action="close")
    inputs["materialize"] = {
        "ran": True,
        "at": "2026-11-04T17:00:00Z",  # future-ok: scheduled: window day
    }
    inputs["coverage_delta"] = {"recorded": True}
    inputs["triggers_resumed"] = {s: True for s in _schedulers()}
    inputs["next_fires"] = {b: spec["next_fire"] for b, spec in wave_b.BATCHES.items()}
    inputs["early_fire_dispositions"] = {
        b: "fire lands inside Wave C's 11-16→11-20 pause — deferred "
        "per the Wave-C P1 note (surfaced, never silently accepted)"
        for b in wave_b.EARLY_FIRE_BATCHES
    }
    inputs.update(over)
    return inputs


def _ids(verdict: wave_b.Verdict) -> dict[str, bool]:
    return {c.id: c.ok for c in verdict.criteria}


# --- the green paths ----------------------------------------------------------


def test_l0_admit_goes() -> None:
    v = wave_b.evaluate(_admit("L0"))
    assert v.decision == "go" and v.refusals == []
    record = v.to_record()
    assert record["kind"] == "sig.wave-b-gate/1"
    assert record["wave"] == "B"
    for cid in (
        "go",
        "window",
        "exclusions",
        "order",
        "pacing",
        "scope",
        "serialize",
        "prestate",
        "backup",
    ):
        assert _ids(v)[cid], f"criterion {cid} should hold"


def test_family_leg_admit_goes() -> None:
    for leg in wave_b.FAMILY_LEGS:
        v = wave_b.evaluate(_admit(leg))
        assert v.decision == "go", f"{leg}: {v.refusals}"


def test_family_close_goes_with_full_evidence() -> None:
    for leg in wave_b.FAMILY_LEGS[:8]:
        v = wave_b.evaluate(_close_family(leg))
        assert v.decision == "go", f"{leg}: {v.refusals}"


def test_l0_close_goes() -> None:
    assert wave_b.evaluate(_close_l0()).decision == "go"


def test_l9_close_goes_even_when_nothing_served() -> None:
    """served=0 across all 917 is an honest recorded outcome, never a failure."""
    v = wave_b.evaluate(_close_l9())
    assert v.decision == "go", v.refusals


def test_l9_close_goes_with_partial_yield() -> None:
    inputs = _close_l9(probe_run=_probe_record(served=42))
    assert wave_b.evaluate(inputs).decision == "go"


def test_l9_close_goes_when_a_challenge_stops_the_sweep() -> None:
    """WV-10 stop-and-record: one challenge halts the sweep; the remaining
    portals land ``not_attempted`` — every outcome recorded, honestly."""
    inputs = _close_l9(probe_run=_probe_record(served=3, challenged_at=3))
    assert wave_b.evaluate(inputs).decision == "go"


def test_l10_admit_goes() -> None:
    assert wave_b.evaluate(_admit("L10")).decision == "go"


def test_l10_close_goes() -> None:
    assert wave_b.evaluate(_close_l10()).decision == "go"


def test_widen_hosts_ride_existing_flips() -> None:
    """L1's flips carry only the gated rows — the widen hosts' seats are
    already permitted; they are never demanded in the OP-26 record."""
    inputs = _admit("L1")
    assert "camreg_denver_co" in inputs["run_set"]
    assert "camreg_denver_co" not in inputs["flips"]["L1"]["executed"]
    assert wave_b.evaluate(inputs).decision == "go"


def test_held_leg_can_admit_again() -> None:
    """A held leg re-admits once its family's flips land — the hold is
    reported, never a dead end (OM-19)."""
    inputs = _admit("L5")
    inputs["held_reports"] = {"L5": "flips pending at 10-30 close"}
    assert wave_b.evaluate(inputs).decision == "go"


def test_l10_admits_with_held_family_legs() -> None:
    """Held-but-reported legs do not block the closing leg."""
    inputs = _admit("L10")
    inputs["completed"] = [e for e in _completed_upto("L10") if e["leg"] not in {"L4", "L6"}]
    inputs["held_reports"] = {
        "L4": "flips pending — held at 10-29 close",
        "L6": "report parse drift — held at 10-31 close",
    }
    assert wave_b.evaluate(inputs).decision == "go"


# --- silence is never consent -------------------------------------------------


def test_missing_go_refuses() -> None:
    inputs = _admit("L0")
    del inputs["go"]
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["go"]
    assert "implement-spec" in v.to_record()["rerun_prompt"]


def test_empty_verbatim_refuses() -> None:
    inputs = _admit("L0")
    inputs["go"]["verbatim"] = "   "
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_paraphrased_go_refuses() -> None:
    """The verbatim go is byte-exact — a paraphrase is a refusal."""
    inputs = _admit("L0")
    inputs["go"]["verbatim"] = "Wave B approved for the October window"
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_go_for_other_window_refuses() -> None:
    inputs = _admit("L0")
    inputs["go"]["verbatim"] = wave_b.GO_VERBATIM.replace(
        "2026-10-26→11-05",  # future-ok: scheduled: window
        "2026-10-27→11-05",  # future-ok: scheduled: window
    )
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_missing_recorded_at_refuses() -> None:
    inputs = _admit("L0")
    del inputs["go"]["recorded_at"]
    assert wave_b.evaluate(inputs).decision == "no-go"


# --- the window ---------------------------------------------------------------


def test_before_window_refuses() -> None:
    inputs = _admit("L0", now="2026-10-26T13:59:59Z")  # future-ok: scheduled: edge
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["window"]


def test_after_window_refuses() -> None:
    inputs = _admit("L0", now="2026-11-05T20:00:00Z")  # future-ok: scheduled: edge
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_overnight_band_refuses() -> None:
    inputs = _admit("L0", now="2026-10-26T04:00:00Z")  # future-ok: scheduled: edge
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_freeze_refuses() -> None:
    inputs = _admit("L0", now="2026-11-06T15:00:00Z")  # future-ok: scheduled: edge
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_window_edge_instants() -> None:
    now = "2026-10-26T14:00:00Z"  # future-ok: scheduled: window open edge
    assert _ids(wave_b.evaluate(_admit("L0", now=now)))["window"]
    now = "2026-11-05T19:59:59Z"  # future-ok: scheduled: window close edge
    assert _ids(wave_b.evaluate(_admit("L0", now=now)))["window"]


def test_weekend_days_are_in_window() -> None:
    """10-31 (Sat) and 11-01 (Sun) are in-window — no weekday rule."""
    assert wave_b.evaluate(_admit("L6")).decision == "go"
    assert wave_b.evaluate(_admit("L7")).decision == "go"


# --- the exclusions -----------------------------------------------------------


def test_materialize_active_refuses() -> None:
    inputs = _admit("L1", materialize_active=True)
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["exclusions"]


def test_g2_slot_refuses() -> None:
    inputs = _admit("L1", g2_slot_active=True)
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_release_cut_refuses() -> None:
    inputs = _admit("L1", release_cut_active=True)
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_peel_day_without_clearance_refuses() -> None:
    """2026-10-29T12:00Z (future-ok: scheduled: fire) is the peel-on first fire —
    a leg that day needs the recorded clearance (L4's default day IS the peel day)."""
    inputs = _admit("L4", peel_fire_cleared=False)
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["exclusions"]


def test_active_manual_run_refuses() -> None:
    inputs = _admit("L1", active_manual_run="sig-ingest-dot-511-de")
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["serialize"]


# --- leg order / held legs ----------------------------------------------------


def test_l1_requires_l0() -> None:
    inputs = _admit("L1", completed=[])
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["order"]


def test_missing_earlier_leg_refuses() -> None:
    inputs = _admit("L5")
    inputs["completed"] = [e for e in inputs["completed"] if e["leg"] != "L2"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_malformed_completed_refuses() -> None:
    inputs = _admit("L1", completed=[{"leg": "L0"}])
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_duplicate_completed_refuses() -> None:
    inputs = _admit(
        "L1",
        completed=[{"leg": "L0", "day": "2026-10-26"}] * 2,  # future-ok: scheduled: window day
    )
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_held_and_green_same_leg_refuses() -> None:
    inputs = _admit("L5")
    inputs["held_reports"] = {"L4": "…"}
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_unknown_leg_refuses() -> None:
    inputs = _admit("L0")
    inputs["leg"] = "L11"
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["order"]


def test_already_completed_leg_refuses() -> None:
    inputs = _admit(
        "L0",
        completed=[{"leg": "L0", "day": "2026-10-26"}],  # future-ok: scheduled: window day
    )
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_non_monotonic_day_refuses() -> None:
    inputs = _admit("L3")
    inputs["completed"][0]["day"] = "2026-11-02"  # after L2 — future-ok: scheduled: window day
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_completed_day_outside_window_refuses() -> None:
    inputs = _admit(
        "L1",
        completed=[{"leg": "L0", "day": "2026-10-20"}],  # future-ok: scheduled: off-window day
    )
    assert wave_b.evaluate(inputs).decision == "no-go"


# --- one family per day -------------------------------------------------------


def test_two_families_one_day_refuses() -> None:
    inputs = _admit("L2", now="2026-10-27T15:00:00Z")  # future-ok: scheduled: window day
    inputs["completed"] = [
        {"leg": "L0", "day": "2026-10-26"},  # future-ok: scheduled: window day
        {"leg": "L1", "day": "2026-10-27"},  # future-ok: scheduled: window day
    ]
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["pacing"]


def test_l4_l8_may_share_a_day() -> None:
    """The contract's single exception: ACQ-11 + ACQ-15 may share. Model the
    honest path — L5/L6/L7 held, L4 green today, L8 admits the same day."""
    inputs = _admit("L8", now="2026-10-30T15:00:00Z")  # future-ok: scheduled: window day
    inputs["completed"] = _completed_upto("L4") + [
        {"leg": "L4", "day": "2026-10-30"}  # future-ok: scheduled: shared day
    ]
    inputs["held_reports"] = {"L5": "held", "L6": "held", "L7": "held"}
    assert wave_b.evaluate(inputs).decision == "go"


def test_other_family_pairs_may_not_share() -> None:
    inputs = _admit("L5", now="2026-10-30T15:00:00Z")  # future-ok: scheduled: window day
    inputs["completed"] = _completed_upto("L5")
    inputs["completed"][4]["day"] = "2026-10-30"  # L4 same day — future-ok: scheduled: window day
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["pacing"]


# --- scope --------------------------------------------------------------------


def test_exact_run_set_required() -> None:
    inputs = _admit("L1", run_set=list(_declared("L1"))[:-1])
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_extra_source_refuses() -> None:
    inputs = _admit("L1", run_set=[*_declared("L1"), "openstates"])
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["scope"]


def test_duplicate_run_set_refuses() -> None:
    inputs = _admit("L1", run_set=[*_declared("L1"), "dot_511_de"])
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_doj_ctas_awards_never_in_wave() -> None:
    inputs = _admit("L1", run_set=[*_declared("L1"), "doj_ctas_awards"])
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_tribal_screened_lane_never_in_wave_b() -> None:
    """The ADR-185 lane landed at P35.11 — it is never a Wave-B source."""
    for sid in ("camreg_tribal_all_leaders_directory", "legis_tribal_tohono_oodham_notice"):
        inputs = _admit("L1", run_set=[*_declared("L1"), sid])
        assert wave_b.evaluate(inputs).decision == "no-go"
        assert sid not in wave_b.FLIP_SOURCES


# --- the OP-26 flips ----------------------------------------------------------


def test_missing_flips_refuses() -> None:
    inputs = _admit("L1")
    del inputs["flips"]
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["flips"]


def test_partial_flips_refuse() -> None:
    inputs = _admit("L1")
    inputs["flips"]["L1"]["executed"] = inputs["flips"]["L1"]["executed"][:-1]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_unconfirmed_flips_refuse() -> None:
    inputs = _admit("L1")
    inputs["flips"]["L1"]["confirmed"] = "   "
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_flips_for_wrong_leg_refuse() -> None:
    inputs = _admit("L1")
    inputs["flips"] = {"L2": inputs["flips"]["L1"]}
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_hosted_ccops_rows_are_flip_rows() -> None:
    """L7's six already-registered ccops_* rows are flag rows too — hosted,
    seatless, still gated until OP-26."""
    flips = _admit("L7")["flips"]["L7"]["executed"]
    for sid in wave_b.LEG_SCOPE["L7"]["hosted"]:
        assert sid in flips
    inputs = _admit("L7")
    inputs["flips"]["L7"]["executed"] = [s for s in flips if s != "ccops_berkeley"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_non_family_legs_need_no_flips() -> None:
    assert "flips" not in _admit("L0")
    assert "flips" not in _admit("L10")


# --- L0 admit: prestate + backup ----------------------------------------------


def test_missing_prestate_refuses_l0() -> None:
    inputs = _admit("L0")
    del inputs["prestate"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_red_cadence_check_refuses_l0() -> None:
    inputs = _admit("L0")
    inputs["prestate"]["cadence_check_ok"] = False
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_failed_backup_refuses_l0() -> None:
    inputs = _admit("L0")
    inputs["backup"]["status"] = "FAILED"
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_prestate_backup_l0_only() -> None:
    ids = _ids(wave_b.evaluate(_admit("L1")))
    assert "prestate" not in ids and "backup" not in ids


# --- the L3 vocab gate --------------------------------------------------------


def test_l3_requires_vocab_registered() -> None:
    """``enforcement_count`` must be hosted-registered before the first
    ATE-family emit — even when L0 recorded it (the gate insists)."""
    inputs = _admit("L3")
    del inputs["vocab"]
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["vocab_gate"]


def test_l3_unverified_vocab_refuses() -> None:
    inputs = _admit(
        "L3",
        vocab={"enforcement_count": {"registered": True, "verified": False}},
    )
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_vocab_gate_is_l3_only() -> None:
    assert "vocab_gate" not in _ids(wave_b.evaluate(_admit("L2")))
    assert "vocab_gate" not in _ids(wave_b.evaluate(_admit("L4")))


# --- close: L0 ----------------------------------------------------------------


def test_l0_close_requires_roll() -> None:
    inputs = _close_l0()
    del inputs["roll"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l0_close_roll_needs_a_pinned_digest() -> None:
    inputs = _close_l0()
    inputs["roll"]["image_digest"] = "sig-jobs:latest"
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l0_close_requires_all_seven_jobs() -> None:
    inputs = _close_l0()
    inputs["jobs_created"]["r11-documents-01"]["paused"] = False
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l0_close_requires_vocab_and_handoff() -> None:
    for key in ("vocab", "flip_handoff"):
        inputs = _close_l0()
        del inputs[key]
        assert wave_b.evaluate(inputs).decision == "no-go", key


def test_l0_close_flip_list_must_be_complete() -> None:
    inputs = _close_l0()
    inputs["flip_list"] = inputs["flip_list"][:-1]
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["handoff"]


def test_l0_close_flip_list_with_strangers_refuses() -> None:
    inputs = _close_l0()
    inputs["flip_list"] = [*inputs["flip_list"], "doj_ctas_awards"]
    assert wave_b.evaluate(inputs).decision == "no-go"


# --- close: family legs -------------------------------------------------------


def test_close_requires_every_run_source() -> None:
    inputs = _close_family("L1")
    del inputs["runs"]["dot_511_mi"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_close_refuses_failed_run() -> None:
    inputs = _close_family("L1")
    inputs["runs"]["dot_511_de"]["outcome"] = "error"
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_zero_claim_run_needs_a_recorded_reason() -> None:
    inputs = _close_family("L1")
    inputs["runs"]["dot_511_de"]["claims_added"] = 0
    assert wave_b.evaluate(inputs).decision == "no-go"
    inputs["empty_run_notes"] = {"dot_511_de": "empty source day — verified upstream"}
    assert wave_b.evaluate(inputs).decision == "go"


def test_plus0_must_read_zero() -> None:
    inputs = _close_family("L1")
    inputs["plus0"]["dot_511_de"]["claims_added"] = 3
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_plus0_must_cover_every_source() -> None:
    inputs = _close_family("L1")
    del inputs["plus0"]["dot_511_wv"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_changed_count_must_be_recorded() -> None:
    inputs = _close_family("L1")
    del inputs["changed_count"]
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["evidence"]


# --- close: the probe ----------------------------------------------------------


def test_probe_record_must_cover_all_917() -> None:
    inputs = _close_l9()
    inputs["probe_run"]["results"] = inputs["probe_run"]["results"][:500]
    assert wave_b.evaluate(inputs).decision == "no-go"
    inputs = _close_l9()
    inputs["probe_run"]["inventory"]["portal_count"] = 500
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_probe_checks_must_reconcile() -> None:
    inputs = _close_l9()
    inputs["probe_run"]["checks"]["refusals"]["count"] = 899  # ≠ refused results
    v = wave_b.evaluate(inputs)
    assert v.decision == "no-go" and not _ids(v)["probe"]


def test_probe_refusal_without_kind_refuses() -> None:
    inputs = _close_l9()
    del inputs["probe_run"]["results"][0]["refusal_kind"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_probe_wrong_version_refuses() -> None:
    inputs = _close_l9()
    inputs["probe_run"]["version"] = "sig.probe-run/0"
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_probe_red_coverage_refuses() -> None:
    inputs = _close_l9()
    inputs["probe_run"]["checks"]["coverage"]["verdict"] = "fail"
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_probe_missing_record_refuses() -> None:
    inputs = _close_l9()
    del inputs["probe_run"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_probe_needs_no_runs_or_plus0() -> None:
    """WV-10: no +0 re-probe — the sig.probe-run/1 record is the evidence."""
    ids = _ids(wave_b.evaluate(_close_l9()))
    assert "runs" not in ids and "plus0" not in ids and "evidence" not in ids


# --- close: L10 ---------------------------------------------------------------


def test_l10_requires_materialize() -> None:
    inputs = _close_l10()
    inputs["materialize"]["ran"] = False
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l10_requires_coverage_delta() -> None:
    inputs = _close_l10()
    del inputs["coverage_delta"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l10_requires_all_triggers_resumed() -> None:
    inputs = _close_l10()
    del inputs["triggers_resumed"]["sig-sched-r11-documents-01"]
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l10_next_fires_must_match_computed() -> None:
    inputs = _close_l10()
    inputs["next_fires"]["r11-layers-01"] = "2026-11-01T07:00:00Z"  # future-ok: scheduled: next
    assert wave_b.evaluate(inputs).decision == "no-go"


def test_l10_requires_early_fire_dispositions() -> None:
    """The four dom-16…19 crons land 11-16…19 — inside Wave C's pause; each
    carries a recorded FEA-15 disposition at resume."""
    inputs = _close_l10()
    del inputs["early_fire_dispositions"]["r11-ate-01"]
    assert wave_b.evaluate(inputs).decision == "no-go"
    # a post-11-20 batch (dom-23) carrying an extra disposition is fine —
    # only the four early fires are required
    inputs = _close_l10()
    inputs["early_fire_dispositions"]["r11-documents-01"] = "fires after 11-20"
    assert wave_b.evaluate(inputs).decision == "go"


# --- the deterministic plan ----------------------------------------------------


def test_plan_orders_legs() -> None:
    steps = wave_b.leg_plan()
    legs = [s["leg"] for s in steps]
    assert legs == sorted(legs, key=wave_b.LEGS.index)
    for i, s in enumerate(steps[1:], 1):
        assert s["leg"] != steps[i - 1]["leg"] or s["seq"] > steps[i - 1]["seq"]


def test_plan_serialises_runs_one_at_a_time() -> None:
    """Every manual/widen run step is followed by its verify step — one
    source at a time, verified between."""
    steps = wave_b.leg_plan()
    for i, s in enumerate(steps):
        if s["kind"] in ("manual", "widen") and s["leg"] != "L9":
            assert steps[i + 1]["kind"] == "verify"
            assert steps[i + 1]["source"] == s["source"]
    # L9's probe run is followed by the sig.probe-run/1 record step —
    # the record IS the verification (WV-10: no +0 re-probe)
    l9 = [s for s in steps if s["leg"] == "L9"]
    assert [s["kind"] for s in l9] == ["flips", "manual", "record"]


def test_plan_covers_the_contract_inventory() -> None:
    steps = wave_b.leg_plan()
    run_sources = {s["source"] for s in steps if s["kind"] in ("manual", "widen")}
    for leg in wave_b.FAMILY_LEGS[:8]:
        assert set(_declared(leg)) <= run_sources
    blob = json.dumps(steps)
    for forbidden in wave_b.NEVER_SOURCES:
        assert forbidden not in blob
    assert "917" in blob


def test_plan_marks_the_operator_step() -> None:
    """The hosted vocabulary registration is OPERATOR-RUN — the plan marks
    it, the driver never executes it."""
    ops = [s for s in wave_b.leg_plan() if s.get("operator")]
    assert len(ops) == 1
    assert "vocab_enforcement_count" in ops[0]["step"]
    assert "INSERT-only" in ops[0]["step"]


def test_plan_resume_names_the_seven_batches() -> None:
    resume = [s for s in wave_b.leg_plan() if s["kind"] == "resume"]
    assert len(resume) == 1
    assert resume[0]["batches"] == sorted(wave_b.BATCHES)
    next_fires = {b: spec["next_fire"] for b, spec in wave_b.BATCHES.items()}
    assert len(set(next_fires.values())) == 7
    for b in wave_b.EARLY_FIRE_BATCHES:
        assert next_fires[b] < wave_b.FEA15_CUTOVER


def test_plan_is_deterministic() -> None:
    assert wave_b.leg_plan() == wave_b.leg_plan()


# --- the CLI surface -----------------------------------------------------------


def _cli(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ops", *argv],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin", "HOME": "/tmp"},
    )


def _tmp_inputs(payload: dict) -> Path:
    path = FIXTURES / f"_tmp_{uuid.uuid4().hex}.json"
    path.write_text(json.dumps(payload))
    return path


def test_cli_go_exits_zero() -> None:
    proc = _cli("wave-b-gate", "--inputs", str(FIXTURES / "go_l0_admit.json"))
    assert proc.returncode == 0, proc.stderr
    record = json.loads(proc.stdout)
    assert record["kind"] == "sig.wave-b-gate/1"
    assert record["decision"] == "go"


def test_cli_nogo_exits_42() -> None:
    bad = _admit("L1")
    del bad["flips"]
    path = _tmp_inputs(bad)
    try:
        proc = _cli("wave-b-gate", "--inputs", str(path))
    finally:
        path.unlink()
    assert proc.returncode == 42
    assert "NO-GO" in proc.stderr
    assert "implement-spec" in proc.stdout


def test_cli_bad_inputs_exit_2() -> None:
    path = FIXTURES / f"_tmp_{uuid.uuid4().hex}.json"
    path.write_text("{not json")
    try:
        proc = _cli("wave-b-gate", "--inputs", str(path))
    finally:
        path.unlink()
    assert proc.returncode == 2


def test_cli_plan_prints_all_legs() -> None:
    proc = _cli("wave-b-plan")
    assert proc.returncode == 0
    for leg in wave_b.LEGS:
        assert leg in proc.stdout
    proc = _cli("wave-b-plan", "--json")
    record = json.loads(proc.stdout)
    assert record["kind"] == "sig.wave-b-plan/1"
    assert record["wave"] == "B"


def test_check_mode_driver_needs_no_adc() -> None:
    """`wave-b.sh --check` is plan-only: no ADC, no network, exit 0."""
    proc = subprocess.run(
        ["bash", "ops/gcp/wave-b.sh", "--check"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PLAN ONLY" in proc.stdout
    assert "implement-spec" in proc.stdout
