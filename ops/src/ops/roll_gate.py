# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.46 L2 go/no-go checker — ``sig.roll-gate/1`` (FEA-07; plan §5.9).

The contract's L2 deploy slot is **never pre-authorised** (OM-20: L44
rewrites ``claim_evidence`` under ACCESS EXCLUSIVE). This module judges a
recorded set of inputs and emits a ``sig.roll-gate/1`` verdict — it never
reads live state itself; the caller captures the inputs (rehearsal record,
disk read, plan diff, read-back verdict, the verbatim go) and this module
refuses L2 unless **every** threshold holds. Over any threshold the leg
stops, records the measurement with ``date -u``, and asks the operator —
a longer announced window or a defer (contract § Go/no-go protocol).

Criteria (each one refuse-on-fail; never a soft warn):

* ``rehearsal_complete`` — a ``sig.sqitch-rehearsal/1`` record whose deploy
  and verify both exited 0 on a production-shaped clone (a failed or
  partial rehearsal certifies nothing about the unattempted tail).
* ``lock`` — the rehearsal's honest upper bound on ``claim_evidence``
  ACCESS EXCLUSIVE ≤ ``LOCK_CEILING_S`` (the FEA-07 20-minute ceiling)
  **and** ≤ 2× the P34.24b clone measurement (``BASELINE_BOUND_S``).
* ``disk`` — free disk ≥ 2× the ``claim_evidence`` total relation bytes.
* ``lock_timeout`` — the deploy session's ``lock_timeout`` is set (> 0).
* ``plan_diff`` — the deploy set's plan diff vs the rehearsed tip is 0
  (otherwise L1 first re-rehearses on a fresh clone).
* ``readback`` — the P34.39a 10-10 OSM-replay read-back verdict is present
  and ``pass`` (the slot does not start without it; a non-pass routes per
  that ticket's contract, never silently).
* ``backup`` — the AR-2 restore point: the newest ``sig-pg`` backup read is
  ``SUCCESSFUL``.
* ``go`` — the operator's verbatim in-ticket go recorded with a ``date -u``
  timestamp (OM-18: silence is never consent).
* ``window`` — ``now`` ≥ the contract's earliest instant, a weekday, inside
  the operator-present 14:00–20:00Z band (AR-3), evaluated against the
  *supplied* instant — never the wall clock, so a fixture can replay any
  hour.

Exit codes from the CLI: ``0`` = go · ``42`` = no-go (queued — the leg
refuses, never proceeds on a missing or failed input) · ``2`` = usage.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "sig.roll-gate/1"

#: FEA-07 / contract: the ACCESS EXCLUSIVE ceiling on ``claim_evidence``.
LOCK_CEILING_S = 20 * 60  # 20 minutes

#: The P34.24b clone measurement the contract binds the rehearsal to: the
#: honest upper bound of the observed ``claim_evidence`` lock hold
#: (docs/build/reports/p34.24b-l44-52-rehearsal/REHEARSAL.md — 13.344 s
#: observed, +0.5 s sampler bound). The go/no-go compares ≤ 2× this.
BASELINE_BOUND_S = 13.844

#: Contract § Live window: not before this instant (after the 10-10
#: read-back and outside the AR-3 batch window), then 14:00–20:00Z on a
#: weekday with the operator present.
WINDOW_EARLIEST = "2026-10-14T14:00:00Z"
WINDOW_START_HH = 14  # 14:00Z inclusive
WINDOW_END_HH = 20  # 20:00Z exclusive — the slot must fit inside it

#: Re-run prompt recorded on every refusal (the leg is never abandoned —
#: it queues with its verbatim line).
RERUN_L2 = (
    "implement-spec "
    "spec=docs/tickets/258_P34.46__round10-schema-allows-and-api-roll.md "
    "live_verification=true (scope: leg L2 only — the deploy slot, and only "
    "with the operator's verbatim in-ticket go recorded in GATE DECISIONS)"
)


class RollGateError(ValueError):
    """A malformed roll-gate input file (usage failure, exit 2)."""


@dataclass
class Criterion:
    id: str
    ok: bool
    detail: str
    value: Any = None


@dataclass
class Verdict:
    decision: str  # "go" | "no-go"
    criteria: list[Criterion] = field(default_factory=list)

    @property
    def refusals(self) -> list[str]:
        return [f"{c.id}: {c.detail}" for c in self.criteria if not c.ok]

    def to_record(self) -> dict:
        return {
            "kind": SCHEMA,
            "decision": self.decision,
            "leg": "L2",
            "criteria": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "value": c.value}
                for c in self.criteria
            ],
            "refusals": self.refusals,
            "rerun_prompt": None if self.decision == "go" else RERUN_L2,
            "thresholds": {
                "lock_ceiling_s": LOCK_CEILING_S,
                "baseline_bound_s": BASELINE_BOUND_S,
                "lock_multiplier": 2.0,
                "disk_multiplier": 2.0,
                "window_earliest": WINDOW_EARLIEST,
                "window_band_hh": [WINDOW_START_HH, WINDOW_END_HH],
                "window_weekdays": "Mon-Fri UTC",
            },
        }


def _iso(text: Any) -> _dt.datetime:
    """Parse an ISO-8601 instant (Z or +offset) — raises RollGateError."""
    if not isinstance(text, str) or not text.strip():
        raise RollGateError(f"expected an ISO-8601 instant, got {text!r}")
    t = text.strip()
    try:
        if t.endswith("Z"):
            dt = _dt.datetime.fromisoformat(t[:-1] + "+00:00")
        else:
            dt = _dt.datetime.fromisoformat(t)
    except ValueError as exc:
        raise RollGateError(f"bad ISO-8601 instant {text!r}: {exc}") from exc
    if dt.tzinfo is None:
        raise RollGateError(f"instant {text!r} carries no timezone (UTC required)")
    return dt.astimezone(_dt.UTC)


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RollGateError(f"{name}: expected a number, got {value!r}")
    return float(value)


def evaluate(inputs: dict) -> Verdict:
    """Judge the recorded inputs — every criterion must hold for a ``go``."""
    if not isinstance(inputs, dict):
        raise RollGateError("the roll-gate input must be a JSON object")
    criteria: list[Criterion] = []

    # -- rehearsal_complete --------------------------------------------------
    reh = inputs.get("rehearsal")
    lock_bound: float | None = None
    if not isinstance(reh, dict):
        criteria.append(Criterion("rehearsal_complete", False, "no rehearsal record supplied"))
    else:
        rc, vrc = reh.get("deploy_exit"), reh.get("verify_exit")
        ok = rc == 0 and vrc == 0
        criteria.append(
            Criterion(
                "rehearsal_complete",
                ok,
                (
                    f"deploy_exit={rc!r} verify_exit={vrc!r} — a green tip "
                    "deploy+verify on a production-shaped clone is required"
                    if not ok
                    else "deploy+verify exited 0 to the rehearsed tip"
                ),
                {"deploy_exit": rc, "verify_exit": vrc},
            )
        )
        lock = reh.get("claim_evidence_lock") or {}
        bound = lock.get("upper_bound_s")
        if bound is not None:
            lock_bound = _num(bound, "rehearsal.claim_evidence_lock.upper_bound_s")

    # -- lock -----------------------------------------------------------------
    if lock_bound is None:
        criteria.append(
            Criterion(
                "lock",
                False,
                "no claim_evidence lock measurement in the rehearsal record",
            )
        )
    else:
        ceiling = min(LOCK_CEILING_S, 2.0 * BASELINE_BOUND_S)
        ok = lock_bound <= ceiling
        criteria.append(
            Criterion(
                "lock",
                ok,
                f"bound {lock_bound:.3f}s vs ceiling {ceiling:.3f}s "
                f"(min(20 min, 2x the {BASELINE_BOUND_S}s P34.24b bound))",
                lock_bound,
            )
        )

    # -- disk ------------------------------------------------------------------
    disk = inputs.get("disk")
    if not isinstance(disk, dict):
        criteria.append(Criterion("disk", False, "no disk read supplied"))
    else:
        free = _num(disk.get("free_bytes"), "disk.free_bytes")
        table = _num(disk.get("claim_evidence_bytes"), "disk.claim_evidence_bytes")
        ok = free >= 2.0 * table
        criteria.append(
            Criterion(
                "disk",
                ok,
                f"free {free:.0f} B vs required {2.0 * table:.0f} B "
                f"(2x claim_evidence {table:.0f} B)",
                {"free_bytes": free, "claim_evidence_bytes": table},
            )
        )

    # -- lock_timeout ------------------------------------------------------------
    session = inputs.get("deploy_session") or {}
    lt_raw = session.get("lock_timeout_ms")
    lt: float | None = (
        float(lt_raw) if isinstance(lt_raw, (int, float)) and not isinstance(lt_raw, bool) else None
    )
    ok = lt is not None and lt > 0
    criteria.append(
        Criterion(
            "lock_timeout",
            ok,
            (
                f"lock_timeout={lt_raw!r} ms — the deploy session must set it"
                if not ok
                else f"lock_timeout={lt:g} ms set for the deploy session"
            ),
            lt,
        )
    )

    # -- plan_diff ----------------------------------------------------------------
    diff = inputs.get("plan_diff")
    if not isinstance(diff, dict):
        criteria.append(Criterion("plan_diff", False, "no plan-diff read supplied"))
    else:
        n = diff.get("diff_lines")
        ok = n == 0
        criteria.append(
            Criterion(
                "plan_diff",
                ok,
                (
                    f"deploy set vs rehearsed tip differs by {n!r} lines — "
                    "L1 must re-rehearse on a fresh clone first"
                    if not ok
                    else "deploy set == rehearsed tip (diff 0)"
                ),
                n,
            )
        )

    # -- readback -----------------------------------------------------------------
    rb = inputs.get("readback")
    if not isinstance(rb, dict):
        criteria.append(
            Criterion(
                "readback",
                False,
                "no P34.39a 10-10 read-back verdict — the slot does not "
                "start without it (live:P34.39a still queued)",
            )
        )
    else:
        verdict = rb.get("verdict")
        ok = verdict == "pass"
        criteria.append(
            Criterion(
                "readback",
                ok,
                (
                    f"P34.39a verdict {verdict!r} — only 'pass' admits the "
                    "slot (a non-pass routes per that ticket's contract)"
                    if not ok
                    else "P34.39a 10-10 read-back verdict pass"
                ),
                verdict,
            )
        )

    # -- backup (AR-2) -------------------------------------------------------------
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
                    "point stops the leg before the first statement"
                    if not ok
                    else "newest sig-pg backup SUCCESSFUL (AR-2)"
                ),
                status,
            )
        )

    # -- go (the only authority) -----------------------------------------------------
    go = inputs.get("go")
    if not isinstance(go, dict) or not str(go.get("verbatim") or "").strip():
        criteria.append(
            Criterion(
                "go",
                False,
                "no verbatim in-ticket go recorded — L2 is never "
                "pre-authorised (silence is never consent)",
            )
        )
    else:
        try:
            recorded = _iso(go.get("recorded_at"))
        except RollGateError as exc:
            criteria.append(Criterion("go", False, f"go recorded_at: {exc}"))
        else:
            criteria.append(
                Criterion(
                    "go",
                    True,
                    f"verbatim go recorded {recorded.isoformat()} (GATE DECISIONS; OM-18)",
                    recorded.isoformat(),
                )
            )

    # -- window (the supplied instant, never the wall clock) -------------------------
    earliest = _iso(inputs.get("window_earliest") or WINDOW_EARLIEST)
    now_raw = inputs.get("now")
    if now_raw is None:
        criteria.append(
            Criterion(
                "window",
                False,
                "no 'now' instant supplied — the gate evaluates a recorded "
                "instant, never the wall clock",
            )
        )
    else:
        now = _iso(now_raw)
        weekday = now.weekday() < 5  # Mon..Fri
        band = WINDOW_START_HH <= now.hour < WINDOW_END_HH
        after = now >= earliest
        ok = weekday and band and after
        detail = (
            f"now {now.isoformat()} — weekday={weekday} "
            f"14:00-20:00Z={band} >= {earliest.isoformat()}={after}"
        )
        criteria.append(Criterion("window", ok, detail, now.isoformat()))

    decision = "go" if all(c.ok for c in criteria) else "no-go"
    return Verdict(decision=decision, criteria=criteria)


def load_inputs(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise RollGateError(f"cannot read inputs {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RollGateError(f"bad JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(
        prog="sig-ops roll-gate",
        description=(
            "P34.46 L2 go/no-go (sig.roll-gate/1): judges a recorded inputs "
            "JSON — refuses L2 (exit 42) unless every FEA-07 threshold, the "
            "plan diff, the P34.39a verdict, the AR-2 backup, the verbatim "
            "go and the window all hold."
        ),
    )
    ap.add_argument("--inputs", required=True, help="the recorded inputs JSON")
    ap.add_argument("--out", default=None, help="also write the verdict JSON here")
    args = ap.parse_args(argv)

    try:
        inputs = load_inputs(args.inputs)
        verdict = evaluate(inputs)
    except RollGateError as exc:
        print(f"sig-ops roll-gate: REFUSED — {exc}", file=sys.stderr)
        return 2

    record = verdict.to_record()
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"sig-ops roll-gate: -> {args.out}", file=sys.stderr)
    if verdict.decision != "go":
        print(
            "sig-ops roll-gate: NO-GO — the leg refuses; queued with its "
            "re-run prompt (see record).",
            file=sys.stderr,
        )
        return 42
    return 0
