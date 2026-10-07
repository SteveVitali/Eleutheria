# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P34.39b — read-only read-backs for the first-fire wave and camreg peel-on.

``sig-ops scheduled-firstfire`` records the outcome of every scheduled-ingest
trigger whose **first fire** lands in the P34.35/P34.36 rollout wave, plus the
``camreg_peel_on`` first fire (P34.38's queue).  The contract
``docs/tickets/248_P34.39b__first-fire-read-backs.md`` names three monitoring
legs — all read-only, all clock-guarded, none blocking a GATE:

- ``l1`` — the first-fire wave's fleet table, read once the wave closes
  (window end 2026-10-21T06:09Z — future-ok: scheduled: the contract's L1
  bound; per-fire AR-4 still applies inside it),
- ``l2`` — the ``camreg_peel_on`` first fire
  on/after 2026-10-29T12:00Z (future-ok: scheduled: the contract's L2 bound), and
- ``l3`` — a final read after l2: the peel-on row plus every l1 row, with the
  routing rows the leg turns into DEFERRALS entries.

**First-fire membership.**  A trigger's first fire is the earliest of (a) the
first scheduled fire at/after the scheduler's ``userUpdateTime`` (its last
deploy) and (b) the scheduled fire its ``lastAttemptTime`` maps to — the
latter catches a trigger deployed earlier but re-pointed by a later apply.
Fires before the window start make the trigger a *repeat* trigger (P34.39a
reads them or they are covered by a named read); fires after the window end
fall to their own legs (peel-on → l2).

**AR-4 / AR-5.**  Before a leg's window opens the command exits
``FIRSTFIRE_QUEUED`` (42 — the protect.sh "queued, not failed" convention) and
prints the verbatim leg-rerun prompt; it never fabricates a verdict ahead of
the fact.  Every gather is a read — ``gcloud scheduler jobs list``,
``gcloud run jobs executions list``, GCS ``ops/runs`` listing/download, and a
read-only ``ingest_run_completion`` / ``pg_stat`` query.  Nothing here
re-executes a job, cancels an execution, or mutates production; the leg never
blocks a GATE.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .cadence_window import next_fire, previous_fire
from .scheduled_readback import (
    GcloudRunner,
    _load_json,
    _parse_ts,
    _utc,
    db_completions,
    db_counters,
    execution_summary,
    gcloud_cli,
    guard_failures,
    pick_execution,
)

FIRSTFIRE_QUEUED = 42
FIRSTFIRE_ERROR = 1

RERUN_PROMPT = (
    "implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true"
)

SCHEMA = "sig.scheduled-firstfire/1"
OBLIGATIONS = ("D-P31.4-1", "D-FEDERAL.1-1")

# Contract bounds — the first-fire wave's L1 window
# (G1 §3.7's planning range; the fema fire is its close).
L1_WINDOW_START = "2026-10-01T00:00Z"  # future-ok: scheduled: contract L1 window open
L1_WINDOW_END = "2026-10-21T06:09Z"  # future-ok: scheduled: contract L1 window close
PEEL_ON_SOURCE = "camreg_peel_on"
PEEL_ON_AFTER = "2026-10-29T12:00Z"  # future-ok: scheduled: contract L2 fire bound

# The two named reads the contract carries alongside the wave (first-day
# triggers whose evidence feeds the federal/owed-register rows).  Their
# scheduled times are real-world cron facts — future-ok: scheduled: contract
# named reads.
NAMED_READS: tuple[dict, ...] = (
    {
        "trigger": "sam_gov",
        "expected": "2026-10-01T05:00Z",  # future-ok: scheduled: contract named read
        "evidence_for": "D-FEDERAL.1-1",
    },
    {
        "trigger": "muckrock",
        "expected": "2026-10-01T06:00Z",  # future-ok: scheduled: contract named read
        # F1 NEW-7 — the owed-register note the contract names for muckrock;
        # evidence only, no DEFERRALS row of its own is invented (OM-03).
        "evidence_for": "F1 NEW-7",
    },
)

LEGS = ("l1", "l2", "l3")

EXECUTION_TIMEOUT_S = 36 * 3600  # ADR-107's 36h batch ceiling, applied per fire
ATTEMPT_SKEW = timedelta(minutes=2)

# Run-row outcomes that read as a clean first fire.  ``quota_reached`` /
# ``budget_reached`` / ``gate_refused`` / ``politeness_refusal`` /
# ``content_drift`` / ``no_live_targets`` / ``error`` are all surfaced
# verbatim and routed — never folded into ok.
OK_OUTCOMES = frozenset({"ok", "partial"})

# Routing owners per the contract: the row that owns the job — P35.1a/b for
# scheduler and fleet hygiene, the source's connector owner, or the operator
# for a credential.
OWNER_SCHEDULER = "P35.1a/P35.1b (scheduler and fleet hygiene)"
OWNER_SPINE = "the operator (stop-and-preserve; ADR-107/111)"
OWNER_COMPLETION = "P31.2 / P35.1b (completion evidence)"


def _owner_connector(fleet_id: str) -> str:
    return f"the {fleet_id} connector owner"


def _looks_credential(text: str) -> bool:
    """A quota/auth starvation signal routes to the operator's credential."""
    t = text.lower()
    return any(
        k in t for k in ("quota", "429", "401", "403", "unauthorized", "api key", "credential")
    )


@dataclass(frozen=True)
class FleetTrigger:
    """One scheduled-ingest trigger from ``ops/cadence.toml`` (a source or a batch)."""

    id: str
    kind: str  # "source" | "batch"
    cron: str
    job: str
    scheduler: str
    members: tuple[str, ...] = ()

    @property
    def run_row_sources(self) -> tuple[str, ...]:
        return self.members if self.kind == "batch" else (self.id,)


def fleet_from_cadence(config: Any) -> list[FleetTrigger]:
    """The full scheduled-ingest fleet: every ``[[sources]]`` + ``[[batches]]`` row."""
    out = [
        FleetTrigger(
            id=s.source,
            kind="source",
            cron=s.cron,
            job=s.job,
            scheduler=s.scheduler,
        )
        for s in config.sources
    ]
    out += [
        FleetTrigger(
            id=b.id,
            kind="batch",
            cron=b.cron,
            job=b.job,
            scheduler=b.scheduler,
            members=tuple(b.members),
        )
        for b in config.batches
    ]
    return sorted(out, key=lambda t: t.id)


def assess_first_fire(
    trigger: FleetTrigger,
    describe: Mapping[str, Any] | None,
) -> dict:
    """A trigger's first scheduled fire and how it was derived.

    Basis = the live ``userUpdateTime`` (the last deploy); the first-fire
    candidate is the cron's first fire at/after it.  When ``lastAttemptTime``
    exists the fire it maps to (≤ the attempt) wins when earlier — an
    earlier-deployed trigger re-pointed since still counts its real first
    fire.  ``None`` when the trigger is absent and never deployed.
    """
    cron = str((describe or {}).get("schedule") or trigger.cron)
    update = _parse_ts((describe or {}).get("userUpdateTime"))
    attempt = _parse_ts((describe or {}).get("lastAttemptTime"))
    candidates: list[tuple[str, datetime]] = []
    if update is not None:
        candidates.append(("deployed", next_fire(cron, update)))
    if attempt is not None:
        candidates.append(("attempted", previous_fire(cron, attempt + ATTEMPT_SKEW)))
    if not candidates:
        return {
            "cron": cron,
            "first_fire": None,
            "basis": None,
            "userUpdateTime": (describe or {}).get("userUpdateTime"),
            "lastAttemptTime": (describe or {}).get("lastAttemptTime"),
        }
    basis, first = min(candidates, key=lambda c: c[1])
    return {
        "cron": cron,
        "first_fire": first,
        "basis": basis,
        "userUpdateTime": (describe or {}).get("userUpdateTime"),
        "lastAttemptTime": (describe or {}).get("lastAttemptTime"),
    }


@dataclass
class FleetGathered:
    """Everything a leg needs — every field read-only, every gap recorded."""

    schedulers: dict[str, Mapping[str, Any] | None] = field(default_factory=dict)
    executions: dict[str, list[Mapping[str, Any]]] = field(default_factory=dict)  # job -> execs
    run_rows: dict[str, list[dict]] = field(default_factory=dict)  # source -> rows
    completions: list[dict] = field(default_factory=list)
    counters: dict[str, dict[str, int]] = field(default_factory=dict)
    counters_queried: bool = False
    completions_queried: bool = False
    untracked_schedulers: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Leg membership and guards


def leg_fleet(
    leg: str,
    fleet: Sequence[FleetTrigger],
    gathered: FleetGathered,
) -> list[tuple[FleetTrigger, dict]]:
    """``[(trigger, assessment)]`` the leg reads — the contract's membership.

    l1: every trigger whose first fire lands inside the wave window.
    l2: the ``camreg_peel_on`` first fire
    on/after 2026-10-29T12:00Z (future-ok: scheduled: the contract's L2 bound).
    l3: l2's peel-on row plus every l1 row.
    """
    if leg not in LEGS:
        raise ValueError(f"unknown leg {leg!r} (one of {LEGS})")
    assessments = {t.id: assess_first_fire(t, gathered.schedulers.get(t.scheduler)) for t in fleet}
    if leg == "l2":
        trig = next((t for t in fleet if t.id == PEEL_ON_SOURCE), None)
        if trig is None:
            return []
        bound = _parse_ts(PEEL_ON_AFTER)
        assert bound is not None  # contract constant
        fire = next_fire(trig.cron, bound)
        assess = assessments[trig.id]
        return [(trig, {**assess, "first_fire": fire, "basis": "contract-bound"})]
    start, end = _parse_ts(L1_WINDOW_START), _parse_ts(L1_WINDOW_END)
    assert start is not None and end is not None  # contract constants
    l1_rows = [
        (t, a)
        for t in fleet
        for a in (assessments[t.id],)
        if a["first_fire"] is not None and start <= a["first_fire"] <= end
    ]
    if leg == "l1":
        return l1_rows
    # l3 = l1's rows plus the peel-on first fire.
    rows = list(l1_rows)
    peel = next((t for t in fleet if t.id == PEEL_ON_SOURCE), None)
    if peel is not None:
        bound = _parse_ts(PEEL_ON_AFTER)
        assert bound is not None  # contract constant
        fire = next_fire(peel.cron, bound)
        rows.append((peel, {**assessments[peel.id], "first_fire": fire, "basis": "contract-bound"}))
    return sorted(rows, key=lambda r: (r[1]["first_fire"], r[0].id))


def leg_guard_failures(
    leg: str,
    rows: Sequence[tuple[FleetTrigger, dict]],
    gathered: FleetGathered,
    now: datetime,
) -> list[str]:
    """The clock guard for the leg itself — per-leg, before any verdict."""
    if leg == "l1":
        end = _parse_ts(L1_WINDOW_END)
        assert end is not None
        if _utc(now) < end:
            return [
                f"the L1 first-fire wave is still open — its window closes "
                f"{L1_WINDOW_END} (now {_utc(now).isoformat()})"
            ]
        return []
    # l2 / l3: the peel-on fire's own AR-4 — fire + lastAttemptTime + a
    # finished post-fire execution (the same guard P34.39a applies).
    peel = next((r for r in rows if r[0].id == PEEL_ON_SOURCE), None)
    if peel is None:
        return [f"{PEEL_ON_SOURCE} is not in the cadence fleet"]
    trigger, assess = peel
    fire = assess["first_fire"]
    assert fire is not None
    sched = gathered.schedulers.get(trigger.scheduler)
    sched_err = next(
        (
            e
            for e in gathered.errors
            if trigger.scheduler in e or e.startswith("scheduler jobs list")
        ),
        None,
    )
    executions = gathered.executions.get(trigger.job, [])
    exec_err = next((e for e in gathered.errors if e.startswith(f"executions {trigger.job}")), None)
    execution = pick_execution(executions, trigger.job, fire)
    return guard_failures(
        fire=fire,
        now=now,
        scheduler=sched,
        execution=execution,
        executions_error=exec_err,
        scheduler_error=sched_err,
    )


# ---------------------------------------------------------------------------
# Per-fire evaluation


def _fire_run_date(fire: datetime) -> date:
    return _utc(fire).date()


def _completion_for(
    completions: Sequence[dict], sources: Sequence[str], run_rows: Sequence[dict]
) -> dict | None:
    """The ingest_run_completion row matching this fire's run rows/sources."""
    uris = {str(r.get("_object")) for r in run_rows if r.get("_object")}
    run_ids = {str(r.get("ingest_run_id")) for r in run_rows if r.get("ingest_run_id")}
    wanted = set(sources)
    for c in completions:
        if str(c.get("run_record_uri")) in uris or str(c.get("run_id")) in run_ids:
            return c
    for c in completions:
        if str(c.get("source_id")) in wanted:
            return c
    return None


def evaluate_fire_row(
    trigger: FleetTrigger,
    assess: dict,
    gathered: FleetGathered,
    now: datetime,
) -> dict:
    """One fleet-table row — verdict + routing for a single first fire.

    Verdicts: ``ok`` (AR-4 held, execution completed, run row(s) clean),
    ``failed`` (missed/disabled fire, failed/cancelled/timed-out execution,
    an ``error`` run row), ``anomaly`` (non-ok non-error outcome, missing
    WORM row or completion once queried — evidence says something happened
    that the table must surface), ``pending`` (fired, execution still
    running), ``not_evaluable`` (evidence absent — the leg re-runs).
    """
    fire: datetime = assess["first_fire"]
    run_date = _fire_run_date(fire)
    sched = gathered.schedulers.get(trigger.scheduler)
    executions = gathered.executions.get(trigger.job, [])
    execution = pick_execution(executions, trigger.job, fire)
    ex_sum = execution_summary(execution)
    rows = {
        src: gathered.run_rows.get(f"{src}@{run_date.isoformat()}", [])
        for src in trigger.run_row_sources
    }
    all_rows = [r for rr in rows.values() for r in rr]
    completion = _completion_for(gathered.completions, trigger.run_row_sources, all_rows)

    verdict = "ok"
    routing: dict | None = None
    notes: list[str] = []

    def _route(owner: str, why: str) -> None:
        nonlocal routing
        routing = {"owner": owner, "trigger": f"{trigger.scheduler} — {why}"}

    if sched is None:
        verdict = "not_evaluable"
        _route(OWNER_SCHEDULER, "scheduler describe absent at read time")
        notes.append("scheduler describe absent — trigger deleted or the read failed")
    else:
        if sched.get("state") == "DISABLED":
            verdict = "failed"
            _route(OWNER_SCHEDULER, "first-fire trigger DISABLED — the fire never ran")
        last_attempt = _parse_ts(sched.get("lastAttemptTime"))
        if last_attempt is None or _utc(last_attempt) < fire - ATTEMPT_SKEW:
            if verdict == "ok":
                verdict = "failed"
            if routing is None:
                _route(OWNER_SCHEDULER, "no scheduler attempt for the first fire")
            notes.append("no lastAttemptTime at/after the first fire — a missed fire")
        elif not execution:
            verdict = "failed"
            _route(
                OWNER_SCHEDULER,
                "scheduler attempted but no Cloud Run execution exists at/after the fire",
            )
        elif not ex_sum.get("finished"):
            if (_utc(now) - _utc(fire)).total_seconds() >= EXECUTION_TIMEOUT_S:
                verdict = "failed"
                _route(
                    _owner_connector(trigger.id),
                    "execution still unfinished at the 36h ceiling "
                    "(deferral-row:execution-timeout)",
                )
            else:
                verdict = "pending"
                notes.append("execution in flight — the read is honest about waiting")
        elif not ex_sum.get("completed_ok"):
            verdict = "failed"
            cond = json.dumps(ex_sum.get("conditions") or {})
            detail = cond + " " + " ".join(str(r.get("detail") or "") for r in all_rows)
            owner = (
                "the operator (credential)"
                if _looks_credential(detail)
                else _owner_connector(trigger.id)
            )
            _route(
                owner,
                f"execution finished {ex_sum.get('failed') or 0} failed / "
                f"{ex_sum.get('cancelled') or 0} cancelled",
            )
        else:
            # The execution completed cleanly — judge the recorded evidence.
            missing_sources = [s for s, rr in rows.items() if not rr]
            if trigger.kind == "source" and missing_sources:
                verdict = "anomaly"
                _route(
                    OWNER_COMPLETION,
                    f"execution completed_ok but no WORM run row under ops/runs/{trigger.id}",
                )
            elif trigger.kind == "batch" and missing_sources:
                verdict = "anomaly"
                _route(
                    OWNER_COMPLETION,
                    f"{len(missing_sources)}/{len(trigger.run_row_sources)} member run "
                    "rows missing",
                )
            bad = [r for r in all_rows if str(r.get("outcome")) == "error"]
            odd = [
                r
                for r in all_rows
                if str(r.get("outcome")) not in OK_OUTCOMES and str(r.get("outcome")) != "error"
            ]
            if bad:
                verdict = "failed"
                detail = " ".join(
                    f"{r.get('detail') or ''} {r.get('refusal_reason') or ''}" for r in bad
                )
                owner = (
                    "the operator (credential)"
                    if _looks_credential(detail)
                    else _owner_connector(trigger.id)
                )
                _route(owner, f"run row outcome 'error' ({len(bad)} row(s))")
            elif odd:
                if verdict != "failed":
                    verdict = "anomaly"
                outcomes = sorted({str(r.get("outcome")) for r in odd})
                detail = " ".join(
                    f"{r.get('detail') or ''} {r.get('refusal_reason') or ''}" for r in odd
                )
                owner = (
                    "the operator (credential)"
                    if _looks_credential(detail)
                    else _owner_connector(trigger.id)
                )
                if routing is None:
                    _route(owner, f"non-ok run row outcome(s): {', '.join(outcomes)}")
            if gathered.completions_queried and completion is None and verdict in ("ok", "anomaly"):
                verdict = "anomaly"
                if routing is None:
                    _route(OWNER_COMPLETION, "no ingest_run_completion row for the fire")

    return {
        "fleet_id": trigger.id,
        "kind": trigger.kind,
        "scheduler": trigger.scheduler,
        "job": trigger.job,
        "cron": assess["cron"],
        "state": (sched or {}).get("state"),
        "first_fire": fire.isoformat(),
        "first_fire_basis": assess.get("basis"),
        "userUpdateTime": assess.get("userUpdateTime"),
        "lastAttemptTime": assess.get("lastAttemptTime"),
        "run_date": run_date.isoformat(),
        "verdict": verdict,
        "notes": notes,
        "execution": ex_sum,
        "run_rows": {
            src: [
                {
                    "object": r.get("_object"),
                    "outcome": r.get("outcome"),
                    "started_at": r.get("started_at"),
                    "duration_seconds": r.get("duration_seconds"),
                    "claims_added": r.get("claims_added"),
                    "ingest_run_id": r.get("ingest_run_id"),
                }
                for r in rr
            ]
            for src, rr in rows.items()
        },
        "run_row_count": len(all_rows),
        "completion": (
            {
                "queried": gathered.completions_queried,
                "found": completion is not None,
                "status": (completion or {}).get("status"),
                "claims_inserted": (completion or {}).get("claims_inserted"),
            }
        ),
        "routing": routing,
    }


def _named_read(entry: dict, fleet: Sequence[FleetTrigger], gathered: FleetGathered) -> dict:
    """One named read — the recorded evidence for a contract-named trigger."""
    expected = _parse_ts(entry["expected"])
    assert expected is not None  # contract constants
    trigger = next((t for t in fleet if t.id == entry["trigger"]), None)
    if trigger is None:
        return {**entry, "recorded": False, "reason": "not in the cadence fleet"}
    sched = gathered.schedulers.get(trigger.scheduler)
    last_attempt = _parse_ts((sched or {}).get("lastAttemptTime"))
    # The named read asks about one expected fire: the FIRST execution
    # created at/after it (not the newest — a repeat trigger keeps firing).
    execution = None
    for ex in gathered.executions.get(trigger.job, []):
        created = _parse_ts(ex.get("metadata", {}).get("creationTimestamp"))
        if created is None or _utc(created) < expected - ATTEMPT_SKEW:
            continue
        if execution is None or _utc(created) < _utc(
            _parse_ts(execution.get("metadata", {}).get("creationTimestamp")) or created
        ):
            execution = ex
    run_date = _fire_run_date(expected)
    rows = gathered.run_rows.get(f"{trigger.id}@{run_date.isoformat()}", [])
    fired = last_attempt is not None and _utc(last_attempt) >= expected - ATTEMPT_SKEW
    return {
        **entry,
        "recorded": bool(fired or execution or rows),
        "fire_seen": fired,
        "execution": execution_summary(execution),
        "run_rows": [
            {
                "object": r.get("_object"),
                "outcome": r.get("outcome"),
                "claims_added": r.get("claims_added"),
                "detail": r.get("detail"),
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Report assembly


def build_fleet_report(
    *,
    leg: str,
    fleet: Sequence[FleetTrigger],
    gathered: FleetGathered,
    now: datetime,
    project: str | None,
    region: str | None,
) -> dict:
    rows = leg_fleet(leg, fleet, gathered)
    fire_rows = [evaluate_fire_row(t, a, gathered, now) for t, a in rows]
    counts: dict[str, int] = {}
    for r in fire_rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    routing_rows = [
        {
            "fleet_id": r["fleet_id"],
            "scheduler": r["scheduler"],
            "first_fire": r["first_fire"],
            "verdict": r["verdict"],
            "owner": r["routing"]["owner"],
            "trigger": r["routing"]["trigger"],
        }
        for r in fire_rows
        if r.get("routing")
    ]
    named = [_named_read(e, fleet, gathered) for e in NAMED_READS] if leg in ("l1", "l3") else []

    counters_bad = {
        t: c
        for t, c in gathered.counters.items()
        if (c.get("n_tup_upd") or 0) or (c.get("n_tup_del") or 0)
    }
    if counters_bad:
        routing_rows.append(
            {
                "fleet_id": "(claim spine)",
                "scheduler": "-",
                "first_fire": "-",
                "verdict": "anomaly",
                "owner": OWNER_SPINE,
                "trigger": "claim-spine update/delete counters non-zero at read time — "
                "stop and preserve (never UPDATE/DELETE)",
            }
        )

    if counts.get("failed"):
        verdict = "failed"
    elif counts.get("anomaly") or counters_bad:
        verdict = "anomaly"
    elif not fire_rows or counts.get("not_evaluable"):
        verdict = "not_evaluable"
    elif counts.get("pending"):
        verdict = "partial"
    else:
        verdict = "ok"

    out_of_scope = sum(
        1 for t in fleet if t.id not in {tr.id for tr, _a in rows} and t.id != PEEL_ON_SOURCE
    )
    return {
        "kind": SCHEMA,
        "generated_at": _utc(now).isoformat(),
        "ticket": "P34.39b",
        "obligations": list(OBLIGATIONS),
        "leg": leg,
        "window": {
            "l1_start": L1_WINDOW_START,
            "l1_end": L1_WINDOW_END,
            "peel_on_after": PEEL_ON_AFTER,
        },
        "project": project,
        "region": region,
        "fleet_size": len(fleet),
        "fires_read": len(fire_rows),
        "out_of_scope": out_of_scope,
        "untracked_schedulers": gathered.untracked_schedulers,
        "verdict": verdict,
        "verdict_counts": counts,
        "fires": fire_rows,
        "named_reads": named,
        "routing_rows": routing_rows,
        "spine_counters": gathered.counters if gathered.counters_queried else None,
        "gather_errors": gathered.errors,
        "leg_status": {"status": "ran", "rerun_prompt": RERUN_PROMPT},
        "layer": "live",
        "read_only": True,
        "non_blocking": True,
    }


def queued_fleet_report(
    *,
    leg: str,
    fleet: Sequence[FleetTrigger],
    gathered: FleetGathered,
    failures: Sequence[str],
    now: datetime,
    project: str | None,
    region: str | None,
) -> dict:
    rows = leg_fleet(leg, fleet, gathered)
    return {
        "kind": SCHEMA,
        "generated_at": _utc(now).isoformat(),
        "ticket": "P34.39b",
        "obligations": list(OBLIGATIONS),
        "leg": leg,
        "window": {
            "l1_start": L1_WINDOW_START,
            "l1_end": L1_WINDOW_END,
            "peel_on_after": PEEL_ON_AFTER,
        },
        "project": project,
        "region": region,
        "guard": {
            "holds": False,
            "failures": list(failures),
            "now": _utc(now).isoformat(),
        },
        "queued_fires": [
            {
                "fleet_id": t.id,
                "scheduler": t.scheduler,
                "first_fire": a["first_fire"].isoformat() if a["first_fire"] else None,
                "state": (gathered.schedulers.get(t.scheduler) or {}).get("state"),
                "lastAttemptTime": (gathered.schedulers.get(t.scheduler) or {}).get(
                    "lastAttemptTime"
                ),
            }
            for t, a in rows
        ],
        "leg_status": {"status": "queued", "rerun_prompt": RERUN_PROMPT},
        "layer": "live",
        "read_only": True,
        "non_blocking": True,
    }


# ---------------------------------------------------------------------------
# Gathers — every call a permitted READ.  Nothing re-executes, cancels or
# writes.


def gather_schedulers_live(
    gcloud: GcloudRunner,
    *,
    project: str,
    region: str,
    fleet: Sequence[FleetTrigger],
    known_extra: Sequence[str] = (),
) -> tuple[dict[str, Mapping[str, Any] | None], list[str], list[str]]:
    """One ``scheduler jobs list`` read; the fleet joined on the job name.

    Returns ``(describes_by_scheduler, errors, untracked)``.  A fleet trigger
    absent from the list reads as ``None`` — a deleted/never-applied trigger
    is recorded, not hidden.  ``known_extra`` names repo-declared triggers
    outside the ingest fleet (the probe sweep) so only truly untracked
    triggers are surfaced.
    """
    try:
        doc = json.loads(
            gcloud(
                [
                    "scheduler",
                    "jobs",
                    "list",
                    "--location",
                    region,
                    "--project",
                    project,
                    "--format",
                    "json",
                ]
            )
        )
    except Exception as e:  # noqa: BLE001 — recorded, never swallowed
        return {}, [f"scheduler jobs list: {e}"], []
    jobs = doc if isinstance(doc, list) else []
    by_name = {str(j.get("name", "")).rsplit("/", 1)[-1]: j for j in jobs}
    known = {t.scheduler for t in fleet} | set(known_extra)
    untracked = sorted(n for n in by_name if n not in known)
    return {t.scheduler: by_name.get(t.scheduler) for t in fleet}, [], untracked


def gather_executions_live(
    gcloud: GcloudRunner, *, project: str, region: str, jobs: Sequence[str]
) -> tuple[dict[str, list[Mapping[str, Any]]], list[str]]:
    """``run jobs executions list`` per evaluated job (read-only)."""
    out: dict[str, list[Mapping[str, Any]]] = {}
    errs: list[str] = []
    for job in sorted(set(jobs)):
        try:
            doc = json.loads(
                gcloud(
                    [
                        "run",
                        "jobs",
                        "executions",
                        "list",
                        "--job",
                        job,
                        "--region",
                        region,
                        "--project",
                        project,
                        "--format",
                        "json",
                        "--limit",
                        "30",
                    ]
                )
            )
            out[job] = list(doc) if isinstance(doc, list) else []
        except Exception as e:  # noqa: BLE001 — recorded
            errs.append(f"executions {job}: {e}")
    return out, errs


def gather_run_rows(
    bucket: Any, sources: Sequence[str], run_dates: Sequence[date]
) -> tuple[dict[str, list[dict]], list[str]]:
    """The ``ops/runs/<source>/<YYYY-MM-DD>/`` WORM rows for each fire's day.

    Keys are ``"<source>@<run_date>"`` — a daily-cron source can appear in the
    table twice with different run dates.
    """
    rows: dict[str, list[dict]] = {}
    errs: list[str] = []
    for src in sorted(set(sources)):
        for rd in sorted(set(run_dates)):
            key = f"{src}@{rd.isoformat()}"
            found: list[dict] = []
            try:
                for name in bucket.list_objects(f"ops/runs/{src}/{rd.isoformat()}/"):
                    try:
                        doc = json.loads(bucket.get_object(name).decode("utf-8"))
                    except ValueError:
                        continue
                    if isinstance(doc, dict):
                        doc["_object"] = f"gs://{bucket.bucket}/{name}"
                        found.append(doc)
            except Exception as e:  # noqa: BLE001 — recorded, never swallowed
                errs.append(f"run rows {src} {rd.isoformat()}: {e}")
            rows[key] = sorted(found, key=lambda r: str(r.get("started_at", "")))
    return rows, errs


def gather_from_fixtures(
    fixtures: Path, fleet: Sequence[FleetTrigger], known_extra: Sequence[str] = ()
) -> FleetGathered:
    """Fixture replay — identical report shape, every gather from a directory.

    Layout: ``cadence.toml`` supplies the fleet (the CLI loads it through the
    normal path); ``schedulers.json`` is the ``jobs list`` document;
    ``executions/<job>.json`` per-job lists; ``run_rows/<src>/<date>/*.json``
    the WORM rows; ``db.json`` the completions/counters.
    """
    g = FleetGathered()
    doc = _load_json(fixtures / "schedulers.json")
    jobs = doc if isinstance(doc, list) else []
    by_name = {str(j.get("name", "")).rsplit("/", 1)[-1]: j for j in jobs}
    g.schedulers = {t.scheduler: by_name.get(t.scheduler) for t in fleet}
    known = {t.scheduler for t in fleet} | set(known_extra)
    g.untracked_schedulers = sorted(n for n in by_name if n not in known)
    exdir = fixtures / "executions"
    for t in fleet:
        ex = _load_json(exdir / f"{t.job}.json") if exdir.is_dir() else None
        if isinstance(ex, list):
            g.executions[t.job] = list(ex)
    rr = fixtures / "run_rows"
    if rr.is_dir():
        for src_dir in sorted(p for p in rr.iterdir() if p.is_dir()):
            for day_dir in sorted(p for p in src_dir.iterdir() if p.is_dir()):
                rows = []
                for f in sorted(day_dir.glob("*.json")):
                    d = _load_json(f)
                    if isinstance(d, dict):
                        d["_object"] = str(f.relative_to(fixtures))
                        rows.append(d)
                g.run_rows[f"{src_dir.name}@{day_dir.name}"] = sorted(
                    rows, key=lambda r: str(r.get("started_at", ""))
                )
    db = _load_json(fixtures / "db.json")
    if isinstance(db, dict):
        g.completions = list(db.get("completions") or [])
        g.counters = dict(db.get("counters") or {})
        g.completions_queried = "completions" in db
        g.counters_queried = "counters" in db
    return g


# ---------------------------------------------------------------------------
# Orchestration


def _evaluated_jobs(leg: str, fleet: Sequence[FleetTrigger], gathered: FleetGathered) -> list[str]:
    """The jobs whose executions a leg reads — its fires plus the named reads."""
    rows = leg_fleet(leg, fleet, gathered)
    jobs = {t.job for t, _a in rows}
    if leg in ("l1", "l3"):
        jobs |= {t.job for t in fleet if t.id in {e["trigger"] for e in NAMED_READS}}
    return sorted(jobs)


def _evaluated_row_sources(
    rows: Sequence[tuple[FleetTrigger, dict]],
) -> tuple[list[str], list[date]]:
    sources = [s for t, _a in rows for s in t.run_row_sources]
    dates = [a["first_fire"].date() for _t, a in rows if a["first_fire"] is not None]
    return sorted(set(sources)), sorted(set(dates))


def run_firstfire(
    *,
    leg: str,
    fleet: Sequence[FleetTrigger],
    now: datetime,
    project: str,
    region: str,
    bucket_name: str | None,
    dsn: str | None,
    fixtures_dir: Path | None = None,
    gcloud: GcloudRunner = gcloud_cli,
    query_factory: Any = None,
    bucket_factory: Any = None,
    known_schedulers: Sequence[str] = (),
) -> tuple[dict, int]:
    """Run the leg's read-back; return ``(report, exit_code)``.

    The clock guard runs first: before the leg's window opens the leg is
    *queued* (exit ``FIRSTFIRE_QUEUED``) with the verbatim re-run prompt —
    never a verdict fabricated ahead of the fact.  Fixture replay
    (``--fixtures-dir``) skips every live read and marks the report
    ``layer: fixture`` — a fixture green is never a live record.
    """
    if fixtures_dir is not None:
        gathered = gather_from_fixtures(fixtures_dir, fleet, known_schedulers)
    else:
        gathered = FleetGathered()
        scheds, errs, untracked = gather_schedulers_live(
            gcloud, project=project, region=region, fleet=fleet, known_extra=known_schedulers
        )
        gathered.schedulers = scheds
        gathered.untracked_schedulers = untracked
        gathered.errors.extend(errs)
        jobs = _evaluated_jobs(leg, fleet, gathered)
        gathered.executions, exec_errs = gather_executions_live(
            gcloud, project=project, region=region, jobs=jobs
        )
        gathered.errors.extend(exec_errs)

    rows = leg_fleet(leg, fleet, gathered)
    failures = leg_guard_failures(leg, rows, gathered, now)
    if failures:
        report = queued_fleet_report(
            leg=leg,
            fleet=fleet,
            gathered=gathered,
            failures=failures,
            now=now,
            project=project,
            region=region,
        )
        report["layer"] = "fixture" if fixtures_dir is not None else "live"
        return report, FIRSTFIRE_QUEUED

    # Past the leg guard — the remaining reads gather the run evidence.
    if fixtures_dir is None:
        sources, run_dates = _evaluated_row_sources(rows)
        named_sources = [e["trigger"] for e in NAMED_READS] if leg in ("l1", "l3") else []
        named_dates = [
            _fire_run_date(t) for e in NAMED_READS if (t := _parse_ts(e["expected"])) is not None
        ]
        if bucket_name:
            from .gcs import GcsBucket

            bf = bucket_factory or GcsBucket
            try:
                bucket = bf(bucket_name)
            except Exception as e:  # noqa: BLE001 — recorded
                gathered.errors.append(f"gcs bucket: {e}")
            else:
                rows_got, errs = gather_run_rows(
                    bucket,
                    sorted(set(sources) | set(named_sources)),
                    sorted(set(run_dates) | set(d for d in named_dates if d)),
                )
                gathered.run_rows = rows_got
                gathered.errors.extend(errs)
        else:
            gathered.errors.append("no restricted bucket resolved — ops/runs rows unread")
        if dsn:
            from .scheduled_readback import pg_query_factory

            qf = query_factory or pg_query_factory
            try:
                query = qf(dsn)
            except Exception as e:  # noqa: BLE001 — recorded
                gathered.errors.append(f"db connect: {e}")
            else:
                try:
                    gathered.counters = db_counters(query)
                    gathered.counters_queried = True
                except Exception as e:  # noqa: BLE001 — recorded
                    gathered.errors.append(f"pg_stat counters: {e}")
                try:
                    since = min(run_dates) if run_dates else now.date()
                    gathered.completions = db_completions(
                        query, datetime.combine(since, datetime.min.time(), tzinfo=UTC)
                    )
                    gathered.completions_queried = True
                except Exception as e:  # noqa: BLE001 — recorded
                    gathered.errors.append(f"ingest_run_completion: {e}")
        else:
            gathered.errors.append(
                "no read-only DSN provided — completion rows / spine counters unread"
            )

    report = build_fleet_report(
        leg=leg,
        fleet=fleet,
        gathered=gathered,
        now=now,
        project=project,
        region=region,
    )
    # A fixture replay is never a live record (SIG-OPS honest layers).
    report["layer"] = "fixture" if fixtures_dir is not None else "live"
    return report, 0
