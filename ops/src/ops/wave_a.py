# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.11 Wave-A activation — the leg plan and the ``sig.wave-a-gate/1`` go/no-go
checker (ticket 271, I8 ACQ-07, OM-19/OM-20).

Wave A is the first live ingestion wave of the Round-11 acquisition build-out.
Its three legs, **in order**, inside ``2026-10-19 → 2026-10-23 14:00–20:00Z``
under the recorded ING-GO-A (GATE-G4 §3 — "Window + flips at open"):

* **L1 — image roll + manual first runs.** Pre-state capture (job/trigger
  JSON, ``sources.toml`` sha, ``cadence --check``), an AR-2 on-demand backup,
  the Legistar-trigger mitigation (pause ``sig-sched-legistar`` before the
  roll, or roll after its ``2026-10-20 05:00Z`` fire — the only in-window
  fire of ``0 5 20 * *``), then ``sig-ops roll-jobs --record`` on one pinned
  digest, ``sig-connectors load-seed --source state_alpr_statute_inventory_2026``,
  and the three manual first runs — ``legistar``, ``usaspending``,
  ``procportal_nyc_ny`` (CROL) — **one at a time, each verified before the
  next starts** (the ticket's ``usa_spending`` is registry id ``usaspending``).
  The two ADR-185 S8 tribal screened-lane sources follow — also one at a
  time — **only** when the wave-open HG-03 flip list (OP-26) names them, and
  always with the recorded "no human review occurred" disclosure.
* **L2 — ``+0`` re-runs.** The same sources re-run immediately; each run row
  must show ``claims_added == 0`` on unchanged inputs.
* **L3 — resume schedules.** The paused ``scheduled-ops.sh --paused`` rows
  and ``sig-sched-legistar`` resume — only after L1/L2 are green, and a
  source's trigger only resumes when that source actually ran.

This module judges **recorded inputs** — it never reads live state itself;
the driver (``ops/gcp/wave-a.sh``) captures the inputs and this module
refuses (exit 42) unless every criterion holds. A refused leg queues with
its re-run prompt — a missed leg is reported, never silently skipped.

Criteria (each one refuse-on-fail; never a soft warn):

* ``go`` — the ING-GO-A verbatim decision recorded with a ``date -u``
  timestamp (GATE DECISIONS; silence is never consent; ING-GO-A is a
  one-shot authorisation for this window — a re-entry re-collects it).
* ``window`` — the supplied ``now`` inside 2026-10-19 → 10-23,
  14:00–20:00Z UTC, a weekday — evaluated against the *supplied* instant,
  never the wall clock.
* ``leg`` — the requested leg is the next un-greened leg in order:
  ``completed`` must be exactly the ordered prefix of ``("L1","L2","L3")``
  before ``leg`` (a missed leg refuses, never skips).
* ``scope`` — every source in ``run_set`` is a declared Wave-A source:
  the three manual sources, or a screened-lane source named by
  ``flip_list``. ``doj_ctas_awards`` (AP-T2-093 — not tribal,
  ``D-R11-LATER-09``) is never in scope. L3's ``run_set`` names triggers
  instead and is checked against the resume set.
* ``screened`` — a screened-lane source runs only when the wave-open
  HG-03 flip list names it AND the "no human review occurred" disclosure
  is recorded; trivially holds when none is in ``run_set``.
* ``trigger`` — L1 only: ``sig-sched-legistar`` recorded paused before the
  roll, or the roll instant is at/after ``2026-10-20T05:00Z``.
* ``serialize`` — no ``sig-materialize`` active and no other manual run in
  flight (one manual run at a time).
* ``backup`` — L1 only: the newest AR-2 backup read is ``SUCCESSFUL``.
* ``prestate`` — L1 only: the pre-state capture is recorded (job/trigger
  JSON + sources.toml sha + a green ``cadence --check``).

Exit codes from the CLI: ``0`` = go · ``42`` = no-go (queued — the leg
refuses, never proceeds on a missing or failed input) · ``2`` = usage.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "sig.wave-a-gate/1"
WAVE = "A"

#: Contract: the Wave-A window — 2026-10-19 → 10-23, each day 14:00–20:00Z.
WINDOW_START = "2026-10-19T14:00:00Z"  # future-ok: scheduled: the contract's window (OM-19)
WINDOW_END = "2026-10-23T20:00:00Z"  # future-ok: scheduled: exclusive end (OM-19)
WINDOW_START_HH = 14
WINDOW_END_HH = 20

#: The three legs, in order. A leg admits only when every earlier leg is
#: recorded green — a missed leg is reported, never silently skipped (OM-19).
LEGS: tuple[str, ...] = ("L1", "L2", "L3")

#: L1's three manual first runs, one at a time in this order (the ticket's
#: ``usa_spending`` is registry id ``usaspending``).
MANUAL_SOURCES: tuple[str, ...] = ("legistar", "usaspending", "procportal_nyc_ny")

#: The ADR-185 S8 tribal screened lane (plan AP-T2-201/AP-T2-210): facts +
#: citations only, and only when the wave-open HG-03 flip list (OP-26) names
#: the source. Screened-lane runs disclose that no human review occurred.
SCREENED_SOURCES: tuple[str, ...] = (
    "camreg_tribal_all_leaders_directory",
    "legis_tribal_tohono_oodham_notice",
)

#: Never in this wave: AP-T2-093 is not tribal and stays deferred under
#: D-R11-LATER-09.
NEVER_SOURCES: frozenset[str] = frozenset({"doj_ctas_awards"})

#: The Legistar trigger mitigation (ticket deliverable 4): ``0 5 20 * *``
#: fires once inside the window at 2026-10-20 05:00Z — pause the trigger
#: before the roll, or delay the roll until at/after that fire so a
#: scheduled execution can never overlap a manual first run.
LEGISTAR_TRIGGER = "sig-sched-legistar"
LEGISTAR_NEXT_FIRE = "2026-10-20T05:00:00Z"  # future-ok: scheduled: 0 5 20 * * (OM-19)

#: The committed 2026 statute seed asset L1 loads (the ticket's
#: ``sig-ops load-seed`` resolves to ``sig-connectors load-seed`` — the
#: packaged asset over the static transport into the PG spine).
SEED_SOURCE = "state_alpr_statute_inventory_2026"

#: Re-run prompt recorded on every refusal (the leg is never abandoned —
#: it queues with its verbatim line). ING-GO-A is a one-shot authorisation:
#: a re-entry re-collects the operator go verbatim.
RERUN = (
    "implement-spec "
    "spec=docs/tickets/271_P35.11__wave-a-activation.md "
    "live_verification=true (scope: the queued Wave-A legs only — each leg "
    "needs the recorded ING-GO-A, the window, and its own gate inputs; the "
    "wave-open HG-03 flip list is the operator's OP-26 action)"
)


class WaveGateError(ValueError):
    """A malformed wave-gate input (usage failure, exit 2)."""


@dataclass
class Criterion:
    id: str
    ok: bool
    detail: str
    value: Any = None


@dataclass
class Verdict:
    decision: str  # "go" | "no-go"
    leg: str
    criteria: list[Criterion] = field(default_factory=list)

    @property
    def refusals(self) -> list[str]:
        return [f"{c.id}: {c.detail}" for c in self.criteria if not c.ok]

    def to_record(self) -> dict:
        return {
            "kind": SCHEMA,
            "wave": WAVE,
            "decision": self.decision,
            "leg": self.leg,
            "criteria": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "value": c.value}
                for c in self.criteria
            ],
            "refusals": self.refusals,
            "rerun_prompt": None if self.decision == "go" else RERUN,
            "thresholds": {
                "window_start": WINDOW_START,
                "window_end": WINDOW_END,
                "window_band_hh": [WINDOW_START_HH, WINDOW_END_HH],
                "window_weekdays": "Mon-Fri UTC",
                "legs": list(LEGS),
                "manual_sources": list(MANUAL_SOURCES),
                "screened_sources": list(SCREENED_SOURCES),
                "never_sources": sorted(NEVER_SOURCES),
                "legistar_trigger": LEGISTAR_TRIGGER,
                "legistar_next_fire": LEGISTAR_NEXT_FIRE,
                "seed_source": SEED_SOURCE,
            },
        }


def _iso(text: Any) -> _dt.datetime:
    """Parse an ISO-8601 instant (Z or +offset) — raises WaveGateError."""
    if not isinstance(text, str) or not text.strip():
        raise WaveGateError(f"expected an ISO-8601 instant, got {text!r}")
    t = text.strip()
    try:
        if t.endswith("Z"):
            dt = _dt.datetime.fromisoformat(t[:-1] + "+00:00")
        else:
            dt = _dt.datetime.fromisoformat(t)
    except ValueError as exc:
        raise WaveGateError(f"bad ISO-8601 instant {text!r}: {exc}") from exc
    if dt.tzinfo is None:
        raise WaveGateError(f"instant {text!r} carries no timezone (UTC required)")
    return dt.astimezone(_dt.UTC)


def _source_ids(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise WaveGateError(f"{name}: expected a list of source/trigger ids, got {value!r}")
    return [v.strip() for v in value]


def evaluate(inputs: dict) -> Verdict:
    """Judge the recorded inputs — every criterion must hold for a ``go``."""
    if not isinstance(inputs, dict):
        raise WaveGateError("the wave-gate input must be a JSON object")
    criteria: list[Criterion] = []

    # -- leg -------------------------------------------------------------------
    leg = inputs.get("leg")
    completed = inputs.get("completed", [])
    if not isinstance(leg, str) or leg not in LEGS:
        criteria.append(
            Criterion(
                "leg", False, f"leg {leg!r} is not one of {LEGS} — the wave admits L1/L2/L3 only"
            )
        )
        leg = leg if isinstance(leg, str) else "?"
    elif not isinstance(completed, list) or completed != list(LEGS[: LEGS.index(leg)]):
        criteria.append(
            Criterion(
                "leg",
                False,
                f"completed={completed!r} — {leg} admits only after "
                f"{list(LEGS[: LEGS.index(leg)])} are recorded green "
                "(a missed leg is reported, never silently skipped)",
                completed,
            )
        )
    else:
        criteria.append(
            Criterion("leg", True, f"{leg} is the next un-greened leg (completed={completed!r})")
        )

    # -- go (ING-GO-A — the only authority) ---------------------------------------
    go = inputs.get("go")
    if not isinstance(go, dict) or not str(go.get("verbatim") or "").strip():
        criteria.append(
            Criterion(
                "go",
                False,
                "no recorded ING-GO-A verbatim — the wave is an in-ticket "
                "pause without it (silence is never consent; a re-entry "
                "re-collects the go verbatim)",
            )
        )
    else:
        try:
            recorded = _iso(go.get("recorded_at"))
        except WaveGateError as exc:
            criteria.append(Criterion("go", False, f"go recorded_at: {exc}"))
        else:
            criteria.append(
                Criterion(
                    "go",
                    True,
                    f"ING-GO-A verbatim recorded {recorded.isoformat()} (GATE DECISIONS; OM-18)",
                    recorded.isoformat(),
                )
            )

    # -- window (the supplied instant, never the wall clock) -----------------------
    start = _iso(WINDOW_START)
    end = _iso(WINDOW_END)
    now: _dt.datetime | None = None
    if inputs.get("now") is None:
        criteria.append(
            Criterion(
                "window",
                False,
                "no 'now' instant supplied — the gate evaluates a recorded "
                "instant, never the wall clock",
            )
        )
    else:
        now = _iso(inputs.get("now"))
        weekday = now.weekday() < 5
        band = WINDOW_START_HH <= now.hour < WINDOW_END_HH
        inside = start <= now < end
        ok = weekday and band and inside
        criteria.append(
            Criterion(
                "window",
                ok,
                f"now {now.isoformat()} — weekday={weekday} 14:00-20:00Z={band} in-window={inside}",
                now.isoformat(),
            )
        )

    # -- scope (every run-set member is a declared Wave-A source) -------------------
    run_set = _source_ids(inputs.get("run_set", []), "run_set")
    flip_list = set(_source_ids(inputs.get("flip_list", []), "flip_list"))
    declared = set(MANUAL_SOURCES) | set(SCREENED_SOURCES)
    bad = [s for s in run_set if s not in declared]
    never = [s for s in run_set if s in NEVER_SOURCES]
    if never:
        criteria.append(
            Criterion(
                "scope",
                False,
                f"{never} in run_set — AP-T2-093 (doj_ctas_awards) is not "
                "tribal and stays deferred under D-R11-LATER-09; it is never "
                "rolled in Wave A",
                never,
            )
        )
    elif bad:
        criteria.append(
            Criterion(
                "scope",
                False,
                f"{bad} not in the declared Wave-A set "
                f"{sorted(declared)} — an undeclared source is never run",
                bad,
            )
        )
    else:
        criteria.append(
            Criterion(
                "scope",
                True,
                f"run_set={run_set!r} ⊆ the declared Wave-A set; doj_ctas_awards absent",
                run_set,
            )
        )

    # -- screened (the ADR-185 lane is flip-list-gated + disclosed) ------------------
    screened_in_set = [s for s in run_set if s in SCREENED_SOURCES]
    unflipped = [s for s in screened_in_set if s not in flip_list]
    disclosure = bool(inputs.get("screened_disclosure"))
    if unflipped:
        criteria.append(
            Criterion(
                "screened",
                False,
                f"{unflipped} not in the recorded wave-open HG-03 flip list "
                "(OP-26) — a screened-lane source never runs unflipped; the "
                "screened lane is no rights clearance (ADR-185)",
                unflipped,
            )
        )
    elif screened_in_set and not disclosure:
        criteria.append(
            Criterion(
                "screened",
                False,
                "screened-lane sources in run_set but the 'no human review "
                "occurred' disclosure is not recorded — ADR-185's interim "
                "posture discloses, never hides",
            )
        )
    else:
        detail = (
            f"screened-lane sources {screened_in_set} flip-listed + "
            "no-human-review disclosure recorded"
            if screened_in_set
            else "no screened-lane source in run_set — criterion holds trivially"
        )
        criteria.append(Criterion("screened", True, detail, screened_in_set))

    # -- trigger (L1 only: the Legistar mitigation) ----------------------------------
    if leg == "L1":
        trig = inputs.get("legistar_trigger") or {}
        paused = trig.get("paused") is True
        after_fire = now is not None and now >= _iso(LEGISTAR_NEXT_FIRE)
        ok = paused or after_fire
        criteria.append(
            Criterion(
                "trigger",
                ok,
                f"{LEGISTAR_TRIGGER} paused={paused} · "
                f"now>={LEGISTAR_NEXT_FIRE}={after_fire} — pause the trigger "
                "before the roll or delay the roll past its 2026-10-20 "
                "05:00Z fire (a scheduled fire never overlaps a manual "
                "first run)",
                {"paused": paused, "after_fire": after_fire},
            )
        )

    # -- serialize (one manual run at a time; never overlapping sig-materialize) ------
    materialize = bool(inputs.get("materialize_active"))
    active = inputs.get("active_manual_run") or None
    ok = not materialize and active is None
    criteria.append(
        Criterion(
            "serialize",
            ok,
            f"materialize_active={materialize} active_manual_run={active!r} "
            "— one manual run at a time, never overlapping sig-materialize",
            {"materialize_active": materialize, "active_manual_run": active},
        )
    )

    # -- backup (L1 only: AR-2) --------------------------------------------------------
    if leg == "L1":
        backup = inputs.get("backup")
        if not isinstance(backup, dict):
            criteria.append(Criterion("backup", False, "no AR-2 backup read supplied"))
        else:
            status = backup.get("status")
            ok = status == "SUCCESSFUL"
            criteria.append(
                Criterion(
                    "backup",
                    ok,
                    (
                        f"newest sig-pg backup {status!r} — a failed restore "
                        "point stops the leg before the first mutation"
                        if not ok
                        else f"AR-2 on-demand backup {backup.get('id')!r} SUCCESSFUL"
                    ),
                    status,
                )
            )

    # -- prestate (L1 only: OM-14) -------------------------------------------------------
    if leg == "L1":
        prestate = inputs.get("prestate")
        if not isinstance(prestate, dict):
            criteria.append(Criterion("prestate", False, "no pre-state capture supplied"))
        else:
            captured = prestate.get("captured") is True and prestate.get("cadence_check_ok") is True
            criteria.append(
                Criterion(
                    "prestate",
                    captured,
                    (
                        "pre-state capture recorded (job/trigger JSON, "
                        "sources.toml sha, cadence --check green)"
                        if captured
                        else "the OM-14 pre-state capture (job/trigger JSON, "
                        "sources.toml sha, green cadence --check) is not "
                        "recorded — capture before the first mutation"
                    ),
                    prestate.get("path"),
                )
            )

    decision = "go" if all(c.ok for c in criteria) else "no-go"
    return Verdict(decision=decision, leg=leg, criteria=criteria)


def leg_plan() -> list[dict[str, Any]]:
    """The deterministic Wave-A step plan (``sig.wave-a-plan/1`` content).

    Every step is an admission-gated unit: the driver gates the leg, then
    runs the steps in order, verifying between manual runs. Check mode
    prints this plan; apply executes it step-by-step — a missed leg or a
    failed verification stops the driver and the refusal is recorded.
    """
    steps: list[dict[str, Any]] = []

    def step(leg: str, i: int, kind: str, text: str, **extra: Any) -> None:
        steps.append({"leg": leg, "seq": i, "kind": kind, "step": text, **extra})

    step(
        "L1",
        1,
        "prestate",
        "capture pre-state: per-source job + trigger JSON, sources.toml "
        "sha256, `sig-ops cadence --check` green",
        mutation=False,
    )
    step(
        "L1",
        2,
        "backup",
        "AR-2: on-demand Cloud SQL backup; record SUCCESSFUL before the first mutation",
        mutation=False,
    )
    step(
        "L1",
        3,
        "mitigate",
        f"pause {LEGISTAR_TRIGGER} before the roll, or delay the roll "
        f"until at/after {LEGISTAR_NEXT_FIRE}",
        mutation=True,
    )
    step(
        "L1",
        4,
        "roll",
        "sig-ops roll-jobs --image <pinned-digest> --record — one digest, every job (ADR-111)",
        mutation=True,
    )
    step(
        "L1",
        5,
        "seed",
        f"sig-connectors load-seed --source {SEED_SOURCE} --sink pg --dsn "
        "$SIG_PG_DSN (the ticket's `sig-ops load-seed` resolves to the "
        "connectors CLI)",
        mutation=True,
    )
    for i, sid in enumerate(MANUAL_SOURCES):
        job = f"sig-ingest-{sid.replace('_', '-')}"
        step(
            "L1",
            6 + i * 2,
            "manual",
            f"manual first run: gcloud run jobs execute {job} "
            f"--args=scheduled-ingest,--source,{sid},--sink,pg --wait",
            source=sid,
            mutation=True,
        )
        step(
            "L1",
            7 + i * 2,
            "verify",
            f"verify {sid}: run row ok, captures landed bytes, claims > 0, "
            "coverage-delta read — before the next source starts",
            source=sid,
            mutation=False,
        )
    for j, sid in enumerate(SCREENED_SOURCES):
        n = 6 + len(MANUAL_SOURCES) * 2 + j * 2
        job = f"sig-ingest-{sid.replace('_', '-')}"
        step(
            "L1",
            n,
            "screened",
            f"screened-lane manual run (only if the wave-open flip list "
            f"names it; disclosure recorded): gcloud run jobs execute {job} "
            f"--args=scheduled-ingest,--source,{sid},--sink,pg --wait",
            source=sid,
            mutation=True,
            contingent="flip_list",
        )
        step(
            "L1",
            n + 1,
            "verify",
            f"verify {sid}: facts/citations-only claims; the "
            "no-human-review disclosure in the run row",
            source=sid,
            mutation=False,
        )

    for i, sid in enumerate(MANUAL_SOURCES):
        step(
            "L2",
            i + 1,
            "rerun",
            f"+0 re-run {sid}: re-execute the same job; assert "
            "claims_added == 0 on unchanged inputs",
            source=sid,
            mutation=True,
            expect="claims_added==0",
        )
    for j, sid in enumerate(SCREENED_SOURCES):
        step(
            "L2",
            len(MANUAL_SOURCES) + j + 1,
            "rerun",
            f"+0 re-run {sid} (only if it ran in L1)",
            source=sid,
            mutation=True,
            contingent="ran_in_L1",
            expect="claims_added==0",
        )

    step(
        "L3",
        1,
        "resume",
        "resume the paused scheduled-ops.sh --paused rows — each trigger "
        "only when its source ran and verified",
        mutation=True,
    )
    step(
        "L3",
        2,
        "resume",
        f"resume {LEGISTAR_TRIGGER} (only if it was paused in L1)",
        mutation=True,
    )
    step(
        "L3",
        3,
        "record",
        "record the leg reports: run rows, changed_count, coverage-delta "
        "read, trigger state — a missed leg is reported, never silently "
        "skipped",
        mutation=False,
    )
    return steps


def load_inputs(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise WaveGateError(f"cannot read inputs {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WaveGateError(f"bad JSON in {path}: {exc}") from exc


def gate_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="sig-ops wave-a-gate",
        description=(
            "P35.11 Wave-A leg gate (sig.wave-a-gate/1): judges a recorded "
            "inputs JSON — refuses the leg (exit 42) unless ING-GO-A, the "
            "window, the leg order, the declared scope, the screened-lane "
            "gate, the Legistar mitigation, serialisation and (L1) backup + "
            "prestate all hold."
        ),
    )
    ap.add_argument("--inputs", required=True, help="the recorded inputs JSON")
    ap.add_argument("--out", default=None, help="also write the verdict JSON here")
    args = ap.parse_args(argv)

    try:
        inputs = load_inputs(args.inputs)
        verdict = evaluate(inputs)
    except WaveGateError as exc:
        print(f"sig-ops wave-a-gate: REFUSED — {exc}", file=sys.stderr)
        return 2

    record = verdict.to_record()
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"sig-ops wave-a-gate: -> {args.out}", file=sys.stderr)
    if verdict.decision != "go":
        print(
            "sig-ops wave-a-gate: NO-GO — the leg refuses; queued with its "
            "re-run prompt (see record).",
            file=sys.stderr,
        )
        return 42
    return 0


def plan_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="sig-ops wave-a-plan",
        description=(
            "P35.11 Wave-A step plan (sig.wave-a-plan/1): the deterministic "
            "ordered steps for L1/L2/L3 — plan-only output, never a mutation."
        ),
    )
    ap.add_argument("--json", action="store_true", help="emit the JSON record")
    args = ap.parse_args(argv)
    steps = leg_plan()
    if args.json:
        print(
            json.dumps(
                {
                    "kind": "sig.wave-a-plan/1",
                    "wave": WAVE,
                    "window": [WINDOW_START, WINDOW_END],
                    "steps": steps,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        f"Wave {WAVE} activation plan — window {WINDOW_START} → {WINDOW_END} "
        "(ING-GO-A, one manual run at a time)"
    )
    for s in steps:
        mark = " (mutation)" if s.get("mutation") else ""
        cont = f" [contingent: {s['contingent']}]" if s.get("contingent") else ""
        print(f"  {s['leg']}.{s['seq']:>2}  {s['step']}{mark}{cont}")
    return 0


__all__ = [
    "Criterion",
    "LEGISTAR_NEXT_FIRE",
    "LEGISTAR_TRIGGER",
    "LEGS",
    "MANUAL_SOURCES",
    "NEVER_SOURCES",
    "SCHEMA",
    "SCREENED_SOURCES",
    "SEED_SOURCE",
    "Verdict",
    "WaveGateError",
    "evaluate",
    "gate_main",
    "leg_plan",
    "plan_main",
]
