# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.2 — the ``sig-ops wave-c-gate`` leg go/no-go, the Wave-C step plan,
the cadence/registry diffs the wave carries and the ``paused_until``
due-set bound (FEA-15).

The contract's acceptance: the gate **refuses a leg when any criterion
fails** — no recorded verbatim ING-GO-C (silence is never consent; a
paraphrase is a refusal), outside the 2026-11-16→11-20 window (future-ok: scheduled: window) without
the recorded early landings, inside AR-3's 03:00–06:30Z never-band, a
skipped leg, a non-exact ``run_set``, Q-23 unrecorded, a non-green
``osm_overpass`` review-status (read, never written), a Wave-B pause
posture not recorded for all four early-fire batches, a concurrent
``sig-materialize``/G2/manual run, L1's missing prestate/backup, L2's
missing or borrowed tier-bump go (the tier leg is its own in-ticket
pause — ING-GO-C is never the tier's), L4's soak gap under 24 h, and
the leg-close evidence: the disk read-back (≥25 GB, cap 40), the tier
read-backs, the L3 rebuild/run/tiles/privacy/+0/ER/retire set (exactly
the two ALPR mirrors out, the four CCTV republish targets still
scheduled, ``derived_from`` recorded, the next-fire after the
retirement), the soak read and the revert post-state. Every criterion
is exercised both ways.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ops.scheduled import BatchCadence, parse_cadence_doc
from support import REPO_ROOT

from ops import dispatcher, wave_c

_TIER_GO = "go — bump sig-pg to db-custom-2-7680 for the Wave-C national run; temporary, L5 reverts"
_WIN_OPEN = "2026-11-16"  # future-ok: scheduled: window day (the contract window's first day)
_TIER_GO_AT = "2026-11-16T12:00:00Z"  # future-ok: scheduled: window day
_RUN_END = "2026-11-17T07:30:00Z"  # future-ok: scheduled: run end (>24h before the test now)
_RUN_END_L3 = "2026-11-18T12:00:00Z"  # future-ok: scheduled: soak-measured run end


def _pauses() -> dict:
    return {b: {"paused": True} for b in wave_c.EARLY_FIRE_BATCHES}


def _completed_upto(leg: str, *, start_day: int = 16) -> list[dict[str, str]]:
    days = {"L1": 16, "L2": 16, "L3": 17, "L4": 18, "L5": 19}
    return [
        {"leg": lid, "day": f"2026-11-{days[lid]:02d}"}  # future-ok: scheduled: window days
        for lid in wave_c.LEGS
        if wave_c.LEGS.index(lid) < wave_c.LEGS.index(leg)
    ]


def _admit(leg: str = "L1", **over) -> dict:
    """A green ``action=admit`` input for ``leg`` — all earlier legs green."""
    day = {row["leg"]: row["day"] for row in _completed_upto("L5")}.get(leg, _WIN_OPEN)
    inputs: dict = {
        "action": "admit",
        "leg": leg,
        "completed": _completed_upto(leg),
        "now": f"{day}T08:00:00Z",
        "go": {"verbatim": wave_c.GO_VERBATIM, "recorded_at": "2026-10-25T18:40:00Z"},
        "q23": {"answered": True, "answer": "a"},
        "review_status": {"osm_overpass": "green"},
        "run_set": [wave_c.OSM_SOURCE] if leg == "L3" else [],
        "materialize_active": False,
        "g2_slot_active": False,
        "release_cut_active": False,
        "active_manual_run": None,
        "wave_b_pauses": _pauses(),
    }
    if leg == "L1":
        inputs["prestate"] = {
            "captured": True,
            "cadence_check_ok": True,
            "path": "pre/wave-c-2026-11-16/",  # future-ok: scheduled: window day
        }
        inputs["backup"] = {"status": "SUCCESSFUL", "id": "1794000000001", "type": "ON_DEMAND"}
    if leg == "L2":
        inputs["tier_go"] = {
            "verbatim": _TIER_GO,
            "recorded_at": _TIER_GO_AT,
        }
    if leg == "L4":
        inputs["run"] = {"completed_at": _RUN_END}  # >24h before now
    inputs.update(over)
    return inputs


def _close(leg: str, **over) -> dict:
    """A green ``action=close`` input for ``leg``."""
    inputs = _admit(leg, action="close")
    if leg == "L1":
        inputs["disk"] = {"size_gb": 25, "autoresize_limit_gb": 40, "recorded": True}
    elif leg == "L2":
        inputs["tier"] = {"tier": wave_c.TIER_UP, "recorded": True}
    elif leg == "L3":
        inputs["rebuild"] = {
            "image_digest": "sha256:" + "a" * 64,
            "jobs": [wave_c.OSM_JOB, wave_c.MIRROR_BATCH_JOB],
            "declared_published": True,
        }
        inputs["retarget"] = {"cron": wave_c.NEW_CRON, "recorded": True}
        inputs["run"] = {
            "outcome": "ok",
            "claims_added": 1100000,
            "completed_at": "2026-11-17T07:30:00Z",  # future-ok: scheduled: run end
        }
        inputs["tiles"] = {"within_tolerance": True}
        inputs["privacy"] = {"user_uid_captures": 0}
        inputs["plus0"] = {"claims_added": 0}
        inputs["er"] = {"merge_pct": 97.0, "net_new": 22125, "lineage_recorded": True}
        inputs["retire"] = {
            "targets_retired": list(wave_c.MIRROR_TARGETS),
            "still_scheduled": list(wave_c.KEEP_TARGETS),
            "derived_from_recorded": True,
            # future-ok: scheduled: the batch's next dom-10 fire
            "next_fire": "2026-12-10T03:35:00Z",  # future-ok: scheduled: dom cron
        }
    elif leg == "L4":
        inputs["run"] = {"completed_at": "2026-11-17T07:30:00Z"}  # future-ok: scheduled: run end
        inputs["soak"] = {
            "read": True,
            "instance_ok": True,
            "no_materialize_overlap": True,
            "record_ref": "runs/P37.2.md#L4",
        }
    elif leg == "L5":
        inputs["tier"] = {"tier": wave_c.TIER_DOWN, "recorded": True}
        inputs["revert"] = {"post_state_recorded": True}
    inputs.update(over)
    return inputs


def _gate_cli(inputs: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    path = tmp_path / f"gate-{uuid.uuid4().hex}.json"
    path.write_text(json.dumps(inputs), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "ops", "wave-c-gate", "--inputs", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin", "HOME": "/tmp"},
    )


def _verdict(inputs: dict) -> wave_c.Verdict:
    return wave_c.evaluate(inputs)


def _refusal_ids(verdict: wave_c.Verdict) -> set[str]:
    return {c.id for c in verdict.criteria if not c.ok}


# ---------------------------------------------------------------------------
# admit-phase criteria
# ---------------------------------------------------------------------------


def test_l1_admit_green() -> None:
    v = _verdict(_admit("L1"))
    assert v.decision == "go", v.refusals


@pytest.mark.parametrize("leg", wave_c.LEGS)
def test_every_leg_admits_when_all_green(leg: str) -> None:
    v = _verdict(_admit(leg))
    assert v.decision == "go", (leg, v.refusals)


def test_no_go_without_ing_go_c() -> None:
    inputs = _admit("L1")
    del inputs["go"]
    v = _verdict(inputs)
    assert v.decision == "no-go"
    assert "go" in _refusal_ids(v)


def test_no_go_on_paraphrased_ing_go_c() -> None:
    """Byte-exact or refusal — 'Approve ING-GO-C' is not the recorded selection."""
    v = _verdict(
        _admit(
            "L1",
            go={"verbatim": "Approve ING-GO-C", "recorded_at": "2026-10-25T18:40:00Z"},
        )
    )
    assert v.decision == "no-go"
    assert "go" in _refusal_ids(v)


def test_no_go_when_go_recorded_at_missing() -> None:
    v = _verdict(_admit("L1", go={"verbatim": wave_c.GO_VERBATIM}))
    assert v.decision == "no-go"
    assert "go" in _refusal_ids(v)


@pytest.mark.parametrize(
    "now",
    [
        "2026-11-15T23:59:59Z",  # before the window — future-ok: scheduled: boundary instants
        "2026-11-21T00:00:00Z",  # past end — L1, no grace (future-ok: scheduled: edge)
        "2026-11-16T03:15:00Z",  # inside AR-3's never-band (future-ok: scheduled: window day)
    ],
)
def test_no_go_outside_window_or_never_band(now: str) -> None:
    v = _verdict(_admit("L1", now=now))
    assert v.decision == "no-go"
    assert "window" in _refusal_ids(v)


def test_earliest_window_needs_all_three_landings() -> None:
    """2026-10-26 admits only when P37.1 + PKG-07 + Q-23 are all recorded landed."""
    early = _admit("L1", now="2026-10-26T08:00:00Z")  # future-ok: scheduled: earliest day
    assert "window" in _refusal_ids(_verdict(early))
    early["early_landings"] = {"P37.1": True, "PKG-07": True, "Q-23": True}
    assert "window" not in _refusal_ids(_verdict(early))
    early["early_landings"]["PKG-07"] = False
    assert "window" in _refusal_ids(_verdict(early))


def test_l4_soak_grace_after_window() -> None:
    """The read-only soak may read inside the 48h grace — a mutation leg may not."""
    v = _verdict(_admit("L4", now="2026-11-21T12:00:00Z"))  # future-ok: scheduled: soak read
    assert "window" not in _refusal_ids(v)
    past = _verdict(_admit("L4", now="2026-11-22T00:00:00Z"))  # future-ok: scheduled: grace edge
    assert "window" in _refusal_ids(past)


def test_no_go_q23_unanswered() -> None:
    v = _verdict(_admit("L1", q23={"answered": False}))
    assert v.decision == "no-go"
    assert "q23" in _refusal_ids(v)


def test_no_go_review_status_not_green() -> None:
    """The fail-closed line is read, never written — a non-green read refuses."""
    v = _verdict(_admit("L3", review_status={"osm_overpass": "amber"}))
    assert v.decision == "no-go"
    assert "review" in _refusal_ids(v)


def test_no_go_wrong_run_set() -> None:
    """The only run is osm_overpass's national fetch."""
    v = _verdict(_admit("L3", run_set=["osm_overpass", "camreg_osm_surveillance"]))
    assert v.decision == "no-go"
    assert "scope" in _refusal_ids(v)


def test_no_go_run_set_on_wrong_leg() -> None:
    v = _verdict(_admit("L1", run_set=["osm_overpass"]))
    assert v.decision == "no-go"
    assert "scope" in _refusal_ids(v)


def test_no_go_skipped_leg() -> None:
    """L3 refuses when an earlier leg is neither green nor held-reported."""
    inputs = _admit("L3", completed=[{"leg": "L1", "day": _WIN_OPEN}])
    v = _verdict(inputs)
    assert v.decision == "no-go"
    assert "order" in _refusal_ids(v)


def test_held_leg_reports_satisfy_order() -> None:
    inputs = _admit(
        "L3",
        completed=[{"leg": "L1", "day": "2026-11-16"}],  # future-ok: scheduled: window day
        held_reports={"L2": "runs/P37.2.md#L2-held"},
    )
    v = _verdict(inputs)
    assert "order" not in _refusal_ids(v)


def test_no_go_leg_already_green() -> None:
    inputs = _admit(
        "L2",
        completed=[{"leg": "L1", "day": _WIN_OPEN}, {"leg": "L2", "day": _WIN_OPEN}],
    )
    v = _verdict(inputs)
    assert "order" in _refusal_ids(v)


def test_no_go_materialize_active() -> None:
    v = _verdict(_admit("L1", materialize_active=True))
    assert v.decision == "no-go"
    assert "exclusions" in _refusal_ids(v)


def test_no_go_second_manual_run() -> None:
    v = _verdict(_admit("L3", active_manual_run="sig-ingest-legistar"))
    assert v.decision == "no-go"
    assert "serialize" in _refusal_ids(v)


@pytest.mark.parametrize("missing", wave_c.EARLY_FIRE_BATCHES)
def test_no_go_wave_b_pause_incomplete(missing: str) -> None:
    """FEA-15 — every early-fire batch's pause posture must be recorded held."""
    pauses = _pauses()
    del pauses[missing]
    v = _verdict(_admit("L1", wave_b_pauses=pauses))
    assert v.decision == "no-go"
    assert "wave_b_pause" in _refusal_ids(v)


def test_no_go_l1_missing_prestate() -> None:
    inputs = _admit("L1")
    del inputs["prestate"]
    v = _verdict(inputs)
    assert "prestate" in _refusal_ids(v)


def test_no_go_l1_failed_backup() -> None:
    """A failed restore point stops the leg before the first mutation."""
    v = _verdict(_admit("L1", backup={"id": "b1", "status": "FAILED"}))
    assert "backup" in _refusal_ids(v)


def test_no_go_l2_missing_tier_go() -> None:
    """The tier leg is its own in-ticket pause — silence is never consent."""
    inputs = _admit("L2")
    del inputs["tier_go"]
    v = _verdict(inputs)
    assert "tier_go" in _refusal_ids(v)


def test_no_go_l2_tier_go_borrowed_from_wave_go() -> None:
    """ING-GO-C is the wave's go, never the tier's — a borrowed text refuses."""
    v = _verdict(
        _admit(
            "L2",
            tier_go={
                "verbatim": wave_c.GO_VERBATIM,
                "recorded_at": "2026-11-16T12:00:00Z",  # future-ok: scheduled: window day
            },
        )
    )
    assert "tier_go" in _refusal_ids(v)


def test_no_go_l4_soak_too_short() -> None:
    v = _verdict(_admit("L4", run={"completed_at": _RUN_END_L3}))
    assert "soak_ready" in _refusal_ids(v)


# ---------------------------------------------------------------------------
# close-phase evidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("leg", wave_c.LEGS)
def test_every_leg_closes_green(leg: str) -> None:
    v = _verdict(_close(leg))
    assert v.decision == "go", (leg, v.refusals)


def test_close_l1_wrong_disk() -> None:
    v = _verdict(_close("L1", disk={"size_gb": 15, "autoresize_limit_gb": 40, "recorded": True}))
    assert "disk" in _refusal_ids(v)
    v2 = _verdict(_close("L1", disk={"size_gb": 25, "autoresize_limit_gb": 0, "recorded": True}))
    assert "disk" in _refusal_ids(v2)


def test_close_l2_wrong_tier() -> None:
    v = _verdict(_close("L2", tier={"tier": wave_c.TIER_DOWN, "recorded": True}))
    assert "tier" in _refusal_ids(v)


@pytest.mark.parametrize(
    "key,bad",
    [
        (
            "rebuild",
            {
                "image_digest": "sig-api:latest",
                "jobs": [wave_c.OSM_JOB, wave_c.MIRROR_BATCH_JOB],
                "declared_published": True,
            },
        ),
        (
            "rebuild",
            {
                "image_digest": "sha256:" + "b" * 64,
                "jobs": [wave_c.OSM_JOB],
                "declared_published": True,
            },
        ),
        (
            "rebuild",
            {
                "image_digest": "sha256:" + "b" * 64,
                "jobs": [wave_c.OSM_JOB, wave_c.MIRROR_BATCH_JOB],
                "declared_published": False,
            },
        ),
        ("retarget", {"cron": "12 4 * * 1", "recorded": True}),
        (
            "run",
            {"outcome": "ok", "claims_added": 0, "completed_at": _RUN_END},
        ),
        (
            "run",
            {"outcome": "error", "claims_added": 100, "completed_at": _RUN_END},
        ),
        ("tiles", {"within_tolerance": False}),
        ("privacy", {"user_uid_captures": 3}),
        ("plus0", {"claims_added": 17}),
        ("er", {"merge_pct": 80.0, "net_new": 40000, "lineage_recorded": True}),
        ("er", {"merge_pct": 97.0, "net_new": "≈22k", "lineage_recorded": True}),
        ("er", {"merge_pct": 97.0, "net_new": 22125, "lineage_recorded": False}),
    ],
    ids=[
        "rebuild-unpinned",
        "rebuild-batch-job-missing",
        "rebuild-bundle-not-published",
        "retarget-old-cron",
        "run-zero-claims",
        "run-not-ok",
        "tiles-drift",
        "privacy-user-uid",
        "plus0-nonzero",
        "er-below-95",
        "er-net-new-not-measured",
        "er-lineage-missing",
    ],
)
def test_close_l3_each_evidence_input_fails_closed(key: str, bad: dict) -> None:
    v = _verdict(_close("L3", **{key: bad}))
    assert v.decision == "no-go"
    assert key in _refusal_ids(v), [c.id for c in v.criteria]


@pytest.mark.parametrize(
    "retire",
    [
        # a third target sneaking in — the diff is exactly the two mirrors
        {
            "targets_retired": [
                "osm_surveillance_deflock",
                "osm_surveillance_alpr_nationwide",
                "osm_surveillance_thailand",
            ],
            "still_scheduled": [
                "osm_surveillance_cctv_london",
                "osm_surveillance_ucp_amini",
                "osm_surveillance_ucp_osm",
            ],
            "derived_from_recorded": True,
            "next_fire": "2026-12-10T03:35:00Z",  # future-ok: scheduled: dom cron
        },
        # only one of the two retired
        {
            "targets_retired": ["osm_surveillance_deflock"],
            "still_scheduled": [
                "osm_surveillance_cctv_london",
                "osm_surveillance_thailand",
                "osm_surveillance_ucp_amini",
                "osm_surveillance_ucp_osm",
            ],
            "derived_from_recorded": True,
            "next_fire": "2026-12-10T03:35:00Z",  # future-ok: scheduled: dom cron
        },
        # the four CCTV targets dropped with them — they stay until each origin is checked
        {
            "targets_retired": ["osm_surveillance_deflock", "osm_surveillance_alpr_nationwide"],
            "still_scheduled": ["osm_surveillance_thailand"],
            "derived_from_recorded": True,
            "next_fire": "2026-12-10T03:35:00Z",  # future-ok: scheduled: dom cron
        },
        # derived_from not recorded (PKG-12 ED-49)
        {
            "targets_retired": ["osm_surveillance_deflock", "osm_surveillance_alpr_nationwide"],
            "still_scheduled": [
                "osm_surveillance_cctv_london",
                "osm_surveillance_thailand",
                "osm_surveillance_ucp_amini",
                "osm_surveillance_ucp_osm",
            ],
            "derived_from_recorded": False,
            "next_fire": "2026-12-10T03:35:00Z",  # future-ok: scheduled: dom cron
        },
        # no recorded next-fire
        {
            "targets_retired": ["osm_surveillance_deflock", "osm_surveillance_alpr_nationwide"],
            "still_scheduled": [
                "osm_surveillance_cctv_london",
                "osm_surveillance_thailand",
                "osm_surveillance_ucp_amini",
                "osm_surveillance_ucp_osm",
            ],
            "derived_from_recorded": True,
            "next_fire": "",
        },
    ],
    ids=["third-target", "only-one", "cctv-dropped", "no-derived-from", "no-next-fire"],
)
def test_close_l3_retire_exactly_two_targets(retire: dict) -> None:
    v = _verdict(_close("L3", retire=retire))
    assert v.decision == "no-go"
    assert "retire" in _refusal_ids(v)


def test_close_l4_incomplete_soak_read() -> None:
    v = _verdict(
        _close(
            "L4",
            soak={
                "read": True,
                "instance_ok": True,
                "no_materialize_overlap": False,
                "record_ref": "r",
            },
        )
    )
    assert "soak" in _refusal_ids(v)


def test_close_l5_wrong_tier_or_missing_post_state() -> None:
    v = _verdict(_close("L5", tier={"tier": wave_c.TIER_UP, "recorded": True}))
    assert "tier" in _refusal_ids(v)
    v2 = _verdict(_close("L5", revert={"post_state_recorded": False}))
    assert "revert" in _refusal_ids(v2)


def test_close_rejudges_admission() -> None:
    """A close that no longer admits refuses — evidence never overrides the gate."""
    inputs = _close("L1")
    inputs["materialize_active"] = True
    v = _verdict(inputs)
    assert v.decision == "no-go"


# ---------------------------------------------------------------------------
# the step plan + CLI surface
# ---------------------------------------------------------------------------


def test_plan_covers_five_legs_in_order() -> None:
    steps = wave_c.leg_plan()
    legs = [s["leg"] for s in steps]
    assert legs == sorted(legs, key=lambda lid: wave_c.LEGS.index(lid))
    assert set(legs) == set(wave_c.LEGS)


def test_plan_marks_the_operator_pause() -> None:
    ops = [s for s in wave_c.leg_plan() if s.get("operator")]
    assert ops and all(s["leg"] == "L2" for s in ops)


def test_plan_retire_names_exactly_the_two_targets() -> None:
    retire = next(s for s in wave_c.leg_plan() if s.get("targets"))
    assert set(retire["targets"]) == set(wave_c.MIRROR_TARGETS)
    assert set(retire["keep"]) == set(wave_c.KEEP_TARGETS)


def test_cli_gate_exit_codes(tmp_path: Path) -> None:
    green = _gate_cli(_admit("L1"), tmp_path)
    assert green.returncode == 0, green.stderr
    rec = json.loads(green.stdout)
    assert rec["kind"] == wave_c.SCHEMA and rec["decision"] == "go"

    bad = _admit("L1")
    del bad["go"]
    refused = _gate_cli(bad, tmp_path)
    assert refused.returncode == 42
    assert json.loads(refused.stdout)["decision"] == "no-go"


def test_cli_plan_json() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "ops", "wave-c-plan", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin", "HOME": "/tmp"},
    )
    assert proc.returncode == 0, proc.stderr
    rec = json.loads(proc.stdout)
    assert rec["kind"] == wave_c.PLAN_SCHEMA
    assert len(rec["steps"]) == len(wave_c.leg_plan())


def test_driver_check_mode_is_plan_only() -> None:
    """`--check` prints the plan without ADC or a network (exit 0)."""
    proc = subprocess.run(
        ["bash", "ops/gcp/wave-c.sh", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PLAN ONLY" in proc.stdout
    assert "gcloud" not in proc.stderr


def test_driver_propagates_gate_refusal(tmp_path: Path) -> None:
    """A gate no-go exits 42 before any step — production is never touched."""
    bad = _admit("L1")
    del bad["prestate"]
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    proc = subprocess.run(
        ["bash", "ops/gcp/wave-c.sh", "--apply", "--leg", "L1", "--inputs", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path),
            "SIG_GCP_PROJECT": "sig-test-project",
        },
    )
    # Without ADC the driver exits 3 at the credential gate; the gate's refusal
    # exits 42. Either way no production command runs — assert no mutation verb
    # reached the log.
    assert proc.returncode in (3, 42)
    assert "instances patch" not in proc.stdout
    assert "backups create" not in proc.stdout


# ---------------------------------------------------------------------------
# the cadence + registry diffs the wave carries (committed config, asserted)
# ---------------------------------------------------------------------------


def _cadence_doc() -> dict:
    import tomllib

    return tomllib.loads((REPO_ROOT / "ops" / "cadence.toml").read_text(encoding="utf-8"))


def _registry_doc() -> dict:
    import tomllib

    return tomllib.loads(
        (REPO_ROOT / "connectors/src/connectors/data/camera_registry_targets.toml").read_text(
            encoding="utf-8"
        )
    )


def test_cadence_osm_overpass_retargeted() -> None:
    """The declared retarget — monthly on the 24th, 08:12Z, a 3h task bound."""
    rows = {s["id"]: s for s in _cadence_doc()["sources"]}
    osm = rows[wave_c.OSM_SOURCE]
    assert osm["cadence"] == "monthly"
    assert osm["cron"] == wave_c.NEW_CRON == "12 8 24 * *"
    assert osm["job"] == wave_c.OSM_JOB


def test_cadence_wave_b_pause_lines_on_exactly_the_early_fires() -> None:
    """FEA-15 — the four batches whose monthly dom falls inside the window
    (16/17/18/19 of 2026-11) carry the declared bound; no other row does."""
    batches = {b["id"]: b for b in _cadence_doc()["batches"]}
    bound = {bid for bid, b in batches.items() if b.get("paused_until")}
    assert bound == set(wave_c.EARLY_FIRE_BATCHES)
    for bid in bound:
        assert batches[bid]["paused_until"] == "2026-11-20"  # future-ok: scheduled: bound
        dom = int(batches[bid]["cron"].split()[2])
        assert 16 <= dom <= 20, bid


def test_registry_mirror_diff_exactly_two() -> None:
    """The retirement diff is exactly the two ALPR mirrors — out of
    [[targets]] and preserved under [[enumerated]] as the restore record."""
    doc = _registry_doc()
    targets = {t["id"] for t in doc.get("targets", [])}
    enumerated = {e["id"]: e for e in doc.get("enumerated", [])}
    for mid in wave_c.MIRROR_TARGETS:
        assert mid not in targets
        row = enumerated[mid]
        assert row["status"] == "retired_mirror"
        # the declared-lineage shape (the ncdot_runneals_mirror precedent):
        # an enumerated row never resolves to a fetchable target — no
        # source_id; the origin is named by mirror_of/derived_from (PKG-12
        # ED-49 — republish↔origin rides one lineage, never independent
        # corroboration).
        assert "source_id" not in row
        assert row["prior_source_id"] == "camreg_osm_surveillance"
        assert row["mirror_of"] == "osm_overpass"
        assert row["derived_from"] in {"osm_overpass", "deflock_repo"}
        assert row["lineage_evidence"]
        # the committed restore record keeps the fetch fields verbatim
        for key in (
            "kind",
            "url",
            "layer_url",
            "observed_count",
            "object_id_field",
            "license_spdx",
            "technology",
        ):
            assert row.get(key), f"{mid}.{key}"
    for keep in wave_c.KEEP_TARGETS:
        assert keep in targets, keep


def test_registry_targets_excludes_the_retired_mirrors() -> None:
    """camreg_osm_surveillance's live fetch set drops exactly the two mirrors."""
    from connectors.dot_511 import registry_targets

    fetched = registry_targets("camreg_osm_surveillance")
    ids = {t["id"] for t in fetched}
    assert not ids & set(wave_c.MIRROR_TARGETS)
    # the four CCTV republish targets still expand
    assert set(wave_c.KEEP_TARGETS) <= ids


# ---------------------------------------------------------------------------
# the paused_until due-set bound (FEA-15 machinery)
# ---------------------------------------------------------------------------


def _batch(**over) -> BatchCadence:
    kw = {
        "id": "test-batch",
        "cadence": "monthly",
        "cron": "17 7 18 * *",
        "job": "sig-ingest-test",
        "scheduler": "sig-sched-test",
        "members": ("s1",),
    }
    kw.update(over)
    return BatchCadence(**kw)


def test_paused_until_parses_from_the_row() -> None:
    doc = {
        "dispatcher": {
            "job": "sig-sched-due",
            "scheduler": "sig-sched-due",
            "cron": "13 * * * *",
            "sa_class": "ingest",
        },
        "batches": [
            {
                "id": "b1",
                "cadence": "monthly",
                "cron": "17 7 18 * *",
                "job": "j",
                "scheduler": "s",
                "state": "enabled",
                "paused_until": "2026-11-20",  # future-ok: scheduled: bound
                "members": ["m"],
            }
        ],
    }
    cfg = parse_cadence_doc(doc)
    assert cfg.batches[0].paused_until == "2026-11-20"  # future-ok: scheduled: bound


def test_paused_until_binds_an_enabled_row_inside_the_window() -> None:
    """The FEA-15 guarantee: a Wave-B resume inside the covered span still
    cannot fire — the declared bound keeps the row inert."""
    doc = {
        "dispatcher": {
            "job": "sig-sched-due",
            "scheduler": "sig-sched-due",
            "cron": "13 * * * *",
            "sa_class": "ingest",
        },
        "batches": [
            {
                "id": "b1",
                "cadence": "monthly",
                "cron": "17 7 18 * *",
                "job": "j",
                "scheduler": "s",
                "state": "enabled",
                "paused_until": "2026-11-20",  # future-ok: scheduled: bound
                "members": ["m"],
            }
        ],
    }
    cfg = parse_cadence_doc(doc)
    ds = dispatcher.evaluate_due(cfg, now=datetime(2026, 11, 18, 7, 20, tzinfo=UTC))
    assert [s.id for s in ds.skipped if s.id == "b1"] == ["b1"]
    assert ds.skipped[0].reason == "declared-paused-until"
    assert not any(d.id == "b1" for d in ds.due)


def test_paused_until_expired_is_inert() -> None:
    doc = {
        "dispatcher": {
            "job": "sig-sched-due",
            "scheduler": "sig-sched-due",
            "cron": "13 * * * *",
            "sa_class": "ingest",
        },
        "batches": [
            {
                "id": "b1",
                "cadence": "monthly",
                "cron": "17 7 18 * *",
                "job": "j",
                "scheduler": "s",
                "state": "enabled",
                "paused_until": "2026-11-20",  # future-ok: scheduled: bound
                "members": ["m"],
            }
        ],
    }
    cfg = parse_cadence_doc(doc)
    ds = dispatcher.evaluate_due(cfg, now=datetime(2026, 12, 18, 7, 20, tzinfo=UTC))
    assert not any(s.id == "b1" and s.reason == "declared-paused-until" for s in ds.skipped)


def test_paused_until_malformed_is_a_refusal() -> None:
    doc = {
        "dispatcher": {
            "job": "sig-sched-due",
            "scheduler": "sig-sched-due",
            "cron": "13 * * * *",
            "sa_class": "ingest",
        },
        "batches": [
            {
                "id": "b1",
                "cadence": "monthly",
                "cron": "17 7 18 * *",
                "job": "j",
                "scheduler": "s",
                "state": "enabled",
                "paused_until": "not-a-date",
                "members": ["m"],
            }
        ],
    }
    cfg = parse_cadence_doc(doc)
    with pytest.raises(dispatcher.DispatcherError):
        dispatcher.evaluate_due(cfg, now=datetime(2026, 11, 18, 7, 20, tzinfo=UTC))
