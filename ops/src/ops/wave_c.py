# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.2 Wave-C activation — the leg plan and the ``sig.wave-c-gate/1``
go/no-go checker (ticket 345, I8 §4.3/§7.4/§7.7 + §8 wave table, OM-19/OM-20).

Wave C is the single sequenced operation that turns OSM from
mirror-republisher into the origin of the national ALPR layer: **five
legs in order** inside the contract window
2026-11-16 → 2026-11-20 (future-ok: scheduled: window; earliest
2026-10-26 when P37.1, PKG-07 and
Q-23 are all recorded landed early) under the recorded ING-GO-C (GATE-G5
§3, verbatim ``"Approve ING-GO-C (rec.)"`` recorded 2026-10-25T18:40Z in
GATE DECISIONS):

* **L1 — pre-grow.** OM-14 pre-state capture → AR-2 on-demand backup
  verified ``SUCCESSFUL`` → Q-23's adopted posture (cap 40 GB, pre-grow
  25 GB, temporary tier bump) recorded → disk grown to 25 GB and the
  autoresize limit confirmed at 40 GB — the grow is one-way: a resumed
  run reads the current state, never re-grows blindly.
* **L2 — tier bump after the go.** The in-ticket pause: the operator's
  verbatim go asked when the leg is due (never pre-authorised — ING-GO-C
  is the wave's go, not the tier's) → ``--tier=db-custom-2-7680`` →
  read-back.
* **L3 — national run.** Wave-B r11 batch pause posture recorded for
  the window (FEA-15 — the four early-fire rows bound by the declared
  ``paused_until``) → ``osm_overpass`` retargeted to monthly
  ``12 8 24 * *`` + the fleet reconciled onto one pinned image digest
  (ADR-111 — ``sig-ingest-camreg-batch-05``'s rebuilt image carries the
  committed mirror-retirement diff) → the manual first national run
  (US-first ordering, non-US objects kept — S5-4) → the §7.7 verify set
  (tile totals ±2 % of discovery and within taginfo's 154,814; zero
  captures containing ``user``/``uid``; claims > 0) → the +0 re-run →
  the camera-site ER rematerialize (≥95 % of the 132,689 republish rows
  merged onto OSM origin sites; the measured net-new count reported;
  ``infer_lineages`` records republish↔origin as one lineage — never
  independent corroboration) → the mirror retirement recorded
  (``osm_surveillance_deflock`` + ``osm_surveillance_alpr_nationwide``
  out of ``camreg-batch-05`` before the next 10th-of-month fire;
  ``derived_from`` recorded under PKG-12 ED-49; the four small CCTV
  republish targets stay).
* **L4 — 24 h soak read.** The §7.7 read-back ≥ 24 h after the run's
  recorded end: instance state, run rows, no materialize overlap — a
  read-only leg; it may read inside the window or inside a 48 h grace
  after it (the revert that follows is a mutation and queues past the
  window per OM-19).
* **L5 — revert.** ``--tier=db-custom-1-3840`` → read-back → the
  closeout record.

This module judges **recorded inputs** — it never reads live state
itself; the driver (``ops/gcp/wave-c.sh``) captures the inputs and this
module refuses (exit 42) unless every criterion holds. A refused leg
queues with its re-run prompt — a missed leg is reported, never
silently skipped (OM-19). The gate runs twice per leg:
``action=admit`` before the leg's first mutation and ``action=close``
before the leg is recorded green — close re-judges admission and then
the leg's recorded evidence.

Criteria (each one refuse-on-fail; never a soft warn):

* ``order`` — ``completed`` is a list of ``{leg, day}`` records; every
  earlier leg is green or held-reported (``held_reports``); completed
  days are admissible window dates, non-decreasing in leg order; the
  requested leg is not already green. A missed leg refuses, never
  skips.
* ``window`` — the supplied ``now`` inside
  2026-11-16 → 2026-11-20 (future-ok: scheduled: span), or inside the
  earliest window
  2026-10-26 → 11-15 only when all three ``early_landings`` (P37.1,
  PKG-07, Q-23) are recorded — and never inside the AR-3 never-band
  03:00–06:30Z for a mutation leg. The read-only soak (L4) may read
  inside the 48 h grace after the window.
* ``go`` — the ING-GO-C verbatim recorded with a timestamp,
  **byte-equal** to the GATE DECISIONS selection ``"Approve ING-GO-C
  (rec.)"`` (silence is never consent; ING-GO-C is collected once and
  recorded byte-exact — a paraphrase is a refusal).
* ``q23`` — the Q-23 answer recorded answered (the adopted posture:
  autoresize cap 40 GB, pre-grow to 25 GB, temporary tier bump only).
* ``review`` — ``osm_overpass``'s review-status recorded green
  (SIG-INGEST-036: the run refuses without it; review-status is read,
  never written — no ``ingestion_permitted`` flip is this row's).
* ``scope`` — the only run is ``osm_overpass``'s national fetch;
  ``run_set`` is exactly ``["osm_overpass"]`` at L3 and empty on every
  other leg. The two mirror *target* ids are never a run input — their
  retirement rides the committed registry diff, not a fetch.
* ``serialize`` — no ``sig-materialize`` active (except the L3
  rematerialize step's own recorded execution), no G2 slot, no cut day,
  and no other manual run in flight (one manual run at a time —
  P36.12's rule rides this wave).
* ``wave_b_pause`` — the four early-fire r11 batch rows recorded held
  for the window (``paused_until`` declared on the row, or the live
  scheduler recorded paused/absent-consolidated; FEA-15).
* ``prestate`` / ``backup`` — L1 only: the OM-14 capture and the AR-2
  ``SUCCESSFUL`` read recorded before the first mutation.
* ``disk`` — L1 close: ``dataDiskSizeGb ≥ 25`` and
  ``storageAutoResizeLimit == 40`` recorded from the live read-back.
* ``tier_go`` — L2 admit: the operator's verbatim in-ticket go recorded
  (non-empty, timestamped, and never the ING-GO-C text — the tier leg
  is its own pause).
* ``tier`` — L2 close ``db-custom-2-7680``, L5 close
  ``db-custom-1-3840`` recorded from the describe read-back.
* ``soak_ready`` — L4 admit: the recorded run end is ≥ 24 h before
  ``now``.
* ``rebuild`` / ``run`` / ``tiles`` / ``privacy`` / ``plus0`` / ``er``
  / ``retire`` — L3 close: the fleet on one pinned digest with the
  declared cron + bundle published; the national run's row ``ok`` with
  ``claims_added > 0``; tile totals inside tolerance; zero ``user`` /
  ``uid`` in captures; the +0 re-run inserting 0; ≥95 % merge with the
  measured net-new count and the lineage record; and the retirement
  record — exactly the two mirrors out, ``derived_from`` recorded, the
  four CCTV targets still scheduled, the next-fire recorded.
* ``soak`` — L4 close: the read recorded (instance ok, no overlap, a
  record ref).
* ``revert`` — L5 close: the post-state recorded.

Exit codes from the CLI: ``0`` = go · ``42`` = no-go (queued — the leg
refuses, never proceeds on a missing or failed input) · ``2`` = usage.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "sig.wave-c-gate/1"
PLAN_SCHEMA = "sig.wave-c-plan/1"
WAVE = "C"

#: Contract: window 2026-11-16 → 2026-11-20 (future-ok: scheduled: the
#: contract window); earliest 2026-10-26 when P37.1, PKG-07 and Q-23 are
#: all recorded landed early. The legs carry no hour band of their own —
#: AR-3's daily never-band 03:00–06:30Z binds every mutation leg.
WINDOW_START = "2026-11-16T00:00:00Z"  # future-ok: scheduled: the contract's window (OM-19)
WINDOW_END = "2026-11-21T00:00:00Z"  # future-ok: scheduled: exclusive end (OM-19)
#: the earliest window opens only when P37.1 + PKG-07 + Q-23 all land early
EARLIEST_START = "2026-10-26T00:00:00Z"  # future-ok: scheduled: the earliest window
#: The read-only soak may read inside the window or inside a 48 h grace
#: after it (a run landing 11-19 soaks 11-20; a run landing 11-20 soaks
#: inside the grace — the mutation legs keep the strict window).
SOAK_GRACE_END = "2026-11-22T00:00:00Z"  # future-ok: scheduled: the soak's read-only grace
WINDOW_FIRST_DATE = _dt.date(2026, 10, 26)  # future-ok: scheduled: the earliest admissible leg day
WINDOW_LAST_DATE = _dt.date(2026, 11, 20)  # future-ok: scheduled: the last admissible leg day

#: AR-3's daily never-band: no leg — mutation or read — starts inside
#: 03:00–06:30Z (the Cloud SQL maintenance band).
NEVER_BAND_START_MIN = 3 * 60
NEVER_BAND_END_MIN = 6 * 60 + 30

#: The five legs, in order. A leg admits only when every earlier leg is
#: recorded green or held-reported — a missed leg is reported, never
#: silently skipped (OM-19).
LEGS: tuple[str, ...] = ("L1", "L2", "L3", "L4", "L5")

#: The legs that mutate production (the never-band binds them; L4's
#: read-only soak is the sole read leg).
MUTATION_LEGS: tuple[str, ...] = ("L1", "L2", "L3", "L5")

#: The recorded ING-GO-C verbatim (GATE DECISIONS, 2026-10-25T18:40Z —
#: the GATE-G5 §3 AskUserQuestion selection; the gate requires
#: byte-equality, never a paraphrase).
GO_VERBATIM = "Approve ING-GO-C (rec.)"

#: The earliest-window prerequisites: all three recorded landed for the
#: 2026-10-26 start to be admissible.
EARLY_LANDINGS: tuple[str, ...] = ("P37.1", "PKG-07", "Q-23")

#: Q-23's adopted posture (B-11 "As stated (Recommended)", GATE-P log
#: 2026-10-01T04:35:53Z): autoresize cap 40 GB, pre-grow to 25 GB,
#: temporary tier bumps only.
DISK_GB = 25
AUTORESIZE_LIMIT_GB = 40
TIER_UP = "db-custom-2-7680"
TIER_DOWN = "db-custom-1-3840"

#: The retarget + the single run source.
OSM_SOURCE = "osm_overpass"
OSM_JOB = "sig-ingest-osm-overpass"
OSM_SCHEDULER = "sig-sched-osm-overpass"
NEW_CRON = "12 8 24 * *"

#: FEA-15 — the four Wave-B r11 batch rows whose monthly dom-16…19 crons
#: would fire inside the window; each carries the declared
#: ``paused_until`` bound (ops/cadence.toml) and its live posture is
#: recorded paused (or absent-consolidated under the dispatcher shape)
#: before the national run starts.
EARLY_FIRE_BATCHES: tuple[str, ...] = (
    "r11-layers-01",
    "r11-layers-02",
    "r11-ate-01",
    "r11-procurement-01",
)

#: The mirror retirement — exactly these two camreg_osm_surveillance
#: targets leave camreg-batch-05's fetch set; the four small CCTV
#: republish targets stay (each origin checked separately).
MIRROR_BATCH = "camreg-batch-05"
MIRROR_BATCH_JOB = "sig-ingest-camreg-batch-05"
MIRROR_TARGETS: tuple[str, ...] = (
    "osm_surveillance_deflock",
    "osm_surveillance_alpr_nationwide",
)
KEEP_TARGETS: tuple[str, ...] = (
    "osm_surveillance_cctv_london",
    "osm_surveillance_thailand",
    "osm_surveillance_ucp_amini",
    "osm_surveillance_ucp_osm",
)
MIRROR_REPUBLISH_ROWS = 132689
TAGINFO_TOTAL = 154814
TILE_TOLERANCE_PCT = 0.02
ER_MERGE_MIN_PCT = 95.0
SOAK_HOURS = 24

#: Re-run prompt recorded on every refusal (the leg is never abandoned —
#: it queues with its verbatim line).
RERUN = (
    "implement-spec "
    "spec=docs/tickets/345_P37.2__wave-c-osm-national-alpr-layer.md "
    "live_verification=true (scope: the queued Wave-C legs only — each leg "
    "needs the recorded ING-GO-C, the window, its own gate inputs and, "
    "for the tier leg, the operator's verbatim in-ticket go; the disk "
    "pre-grow is one-way — a resumed run reads the current state, never "
    "re-grows blindly)"
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
    action: str
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
            "action": self.action,
            "criteria": [
                {"id": c.id, "ok": c.ok, "detail": c.detail, "value": c.value}
                for c in self.criteria
            ],
            "refusals": self.refusals,
            "rerun_prompt": None if self.decision == "go" else RERUN,
            "thresholds": {
                "window_start": WINDOW_START,
                "window_end": WINDOW_END,
                "earliest_start": EARLIEST_START,
                "soak_grace_end": SOAK_GRACE_END,
                "never_band_minutes": [NEVER_BAND_START_MIN, NEVER_BAND_END_MIN],
                "legs": list(LEGS),
                "mutation_legs": list(MUTATION_LEGS),
                "early_landings": list(EARLY_LANDINGS),
                "disk_gb": DISK_GB,
                "autoresize_limit_gb": AUTORESIZE_LIMIT_GB,
                "tier_up": TIER_UP,
                "tier_down": TIER_DOWN,
                "osm_source": OSM_SOURCE,
                "new_cron": NEW_CRON,
                "early_fire_batches": list(EARLY_FIRE_BATCHES),
                "mirror_batch": MIRROR_BATCH,
                "mirror_targets": list(MIRROR_TARGETS),
                "keep_targets": list(KEEP_TARGETS),
                "mirror_republish_rows": MIRROR_REPUBLISH_ROWS,
                "taginfo_total": TAGINFO_TOTAL,
                "tile_tolerance_pct": TILE_TOLERANCE_PCT,
                "er_merge_min_pct": ER_MERGE_MIN_PCT,
                "soak_hours": SOAK_HOURS,
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


def _day(text: Any, where: str) -> _dt.date:
    """Parse an ISO-8601 *date* (YYYY-MM-DD) — raises WaveGateError."""
    if not isinstance(text, str) or not text.strip():
        raise WaveGateError(f"{where}: expected an ISO-8601 date, got {text!r}")
    try:
        return _dt.date.fromisoformat(text.strip()[:10])
    except ValueError as exc:
        raise WaveGateError(f"{where}: bad ISO-8601 date {text!r}") from exc


def _source_ids(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise WaveGateError(f"{name}: expected a list of source/trigger ids, got {value!r}")
    return [v.strip() for v in value]


def _completed_entries(inputs: dict) -> tuple[list[tuple[str, _dt.date]], list[str]]:
    """Validate the ``completed`` record list — returns (entries, errors).

    Each entry is a ``{"leg": "L1", "day": "..."}`` pair — the recorded
    green legs in run order. Malformed entries are usage-shape errors the
    gate reports as refusals (recorded inputs are judged, never trusted).
    """
    entries: list[tuple[str, _dt.date]] = []
    errors: list[str] = []
    raw = inputs.get("completed", [])
    if not isinstance(raw, list):
        return [], [f"completed: expected a list of {{leg, day}} records, got {raw!r}"]
    seen: set[str] = set()
    for i, item in enumerate(raw):
        where = f"completed[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected {{leg, day}}, got {item!r}")
            continue
        leg, day = item.get("leg"), item.get("day")
        if leg not in LEGS:
            errors.append(f"{where}: leg {leg!r} is not one of {LEGS}")
            continue
        if leg in seen:
            errors.append(f"{where}: leg {leg!r} recorded green twice")
            continue
        try:
            d = _day(day, where)
        except WaveGateError as exc:
            errors.append(str(exc))
            continue
        if not (WINDOW_FIRST_DATE <= d <= WINDOW_LAST_DATE):
            errors.append(
                f"{where}: day {d.isoformat()} outside the admissible dates "
                f"{WINDOW_FIRST_DATE.isoformat()}→{WINDOW_LAST_DATE.isoformat()} "
                "(the window plus the recorded-early path)"
            )
            continue
        seen.add(leg)
        entries.append((leg, d))
    return entries, errors


def _held(inputs: dict) -> tuple[set[str], list[str]]:
    """Validate ``held_reports`` — {leg: report-ref}; returns (legs, errors)."""
    raw = inputs.get("held_reports", {})
    if not isinstance(raw, dict):
        return set(), [f"held_reports: expected a {{leg: report-ref}} object, got {raw!r}"]
    legs: set[str] = set()
    errors: list[str] = []
    for leg, ref in raw.items():
        if leg not in LEGS:
            errors.append(f"held_reports: leg {leg!r} is not one of {LEGS}")
            continue
        if not isinstance(ref, str) or not ref.strip():
            errors.append(
                f"held_reports[{leg!r}]: a held leg needs a non-empty report ref "
                "(held = queued AND reported, never silently skipped)"
            )
            continue
        legs.add(leg)
    return legs, errors


def _in_never_band(now: _dt.datetime) -> bool:
    minutes = now.hour * 60 + now.minute
    return NEVER_BAND_START_MIN <= minutes < NEVER_BAND_END_MIN


def evaluate(inputs: dict) -> Verdict:
    """Judge the recorded inputs — every criterion must hold for a ``go``."""
    if not isinstance(inputs, dict):
        raise WaveGateError("the wave-gate input must be a JSON object")
    action = inputs.get("action")
    if action not in ("admit", "close"):
        raise WaveGateError(
            f"action {action!r} — expected 'admit' (before the leg's first "
            "mutation) or 'close' (before the leg is recorded green)"
        )
    criteria: list[Criterion] = []

    # -- leg + order --------------------------------------------------------------
    leg = inputs.get("leg")
    entries, order_errors = _completed_entries(inputs)
    held, held_errors = _held(inputs)
    done = {lid for lid, _ in entries} | held
    both = {lid for lid, _ in entries} & held
    if both:
        order_errors.append(
            f"{sorted(both)} recorded both green and held — a leg is one or the other"
        )
    if not isinstance(leg, str) or leg not in LEGS:
        criteria.append(
            Criterion(
                "order",
                False,
                f"leg {leg!r} is not one of {LEGS} — the wave admits L1…L5 only",
            )
        )
        leg = leg if isinstance(leg, str) else "?"
    else:
        missing = [lid for lid in LEGS[: LEGS.index(leg)] if lid not in done]
        already = leg in {lid for lid, _ in entries}
        if already:
            criteria.append(
                Criterion(
                    "order",
                    False,
                    f"{leg} is already recorded green — a leg runs once; a "
                    "re-entry re-collects the operator go verbatim",
                )
            )
        elif missing:
            criteria.append(
                Criterion(
                    "order",
                    False,
                    f"{missing} neither green nor held-reported — {leg} admits "
                    "only after every earlier leg is green or held (a missed "
                    "leg is reported, never silently skipped)",
                    missing,
                )
            )
        elif order_errors or held_errors:
            criteria.append(Criterion("order", False, "; ".join(order_errors + held_errors)))
        else:
            criteria.append(
                Criterion(
                    "order",
                    True,
                    f"{leg} is next in order (green={sorted(lid for lid, _ in entries)}, "
                    f"held={sorted(held)})",
                )
            )

    # -- leg-day ordering -----------------------------------------------------------
    ordered = sorted(entries, key=lambda e: LEGS.index(e[0]))
    day_errors: list[str] = []
    for prev, nxt in zip(ordered, ordered[1:], strict=False):
        if nxt[1] < prev[1]:
            day_errors.append(
                f"{nxt[0]} day {nxt[1].isoformat()} precedes {prev[0]} day "
                f"{prev[1].isoformat()} — leg days never run backwards"
            )
    if day_errors:
        criteria.append(Criterion("order", False, "; ".join(day_errors)))

    # -- now + window -----------------------------------------------------------------
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
        start, end = _iso(WINDOW_START), _iso(WINDOW_END)
        earliest = _iso(EARLIEST_START)
        early_landings = inputs.get("early_landings") or {}
        early_ok = all(early_landings.get(k) is True for k in EARLY_LANDINGS)
        in_window = start <= now < end
        in_earliest = earliest <= now < start and early_ok
        in_grace = leg == "L4" and end <= now < _iso(SOAK_GRACE_END)
        in_band = _in_never_band(now) and leg in MUTATION_LEGS
        ok = (in_window or in_earliest or in_grace) and not in_band
        detail = (
            f"now {now.isoformat()} — in-window={in_window} "
            f"earliest(landings={early_ok})={in_earliest} "
            f"soak-grace={in_grace} never-band-03:00-06:30Z={in_band}"
        )
        if earliest <= now < start and not early_ok:
            detail += f" — the earliest window needs all of {list(EARLY_LANDINGS)} recorded landed"
        criteria.append(Criterion("window", ok, detail, now.isoformat()))

    # -- go (ING-GO-C — byte-exact, GATE-G5 §3) ----------------------------------------
    go = inputs.get("go")
    if not isinstance(go, dict) or not str(go.get("verbatim") or "").strip():
        criteria.append(
            Criterion(
                "go",
                False,
                "no recorded ING-GO-C verbatim — the wave does not run without "
                "it (silence is never consent; the GATE-G5 selection is recorded "
                "byte-exact)",
            )
        )
    elif go.get("verbatim") != GO_VERBATIM:
        criteria.append(
            Criterion(
                "go",
                False,
                "the recorded go is not the verbatim ING-GO-C — GATE DECISIONS "
                f"carries {GO_VERBATIM!r} byte-exact; a paraphrase is a refusal "
                "(silence is never consent)",
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
                    f"ING-GO-C verbatim recorded {recorded.isoformat()} "
                    "(GATE-G5 §3; the tier-bump go stays its own in-ticket pause)",
                    recorded.isoformat(),
                )
            )

    # -- Q-23 recorded answered ----------------------------------------------------------
    q23 = inputs.get("q23") or {}
    q23_ok = q23.get("answered") is True
    criteria.append(
        Criterion(
            "q23",
            q23_ok,
            (
                "Q-23 recorded answered — the adopted posture binds (cap "
                f"{AUTORESIZE_LIMIT_GB} GB, pre-grow to {DISK_GB} GB, temporary "
                "tier bump only; B-11 'As stated (Recommended)', GATE-P log "
                "2026-10-01T04:35:53Z)"
                if q23_ok
                else "Q-23's answer is not recorded — the disk posture (cap "
                "40 GB, pre-grow 25 GB, temporary tier bump) is a gate input, "
                "never assumed"
            ),
            q23.get("answer"),
        )
    )

    # -- review-status green (read, never written) ---------------------------------------
    review = inputs.get("review_status") or {}
    osm_review = str(review.get(OSM_SOURCE) or "")
    criteria.append(
        Criterion(
            "review",
            osm_review == "green",
            (
                f"{OSM_SOURCE} review-status recorded green — the run may fetch "
                "(SIG-INGEST-036; the fail-closed line was read, never written)"
                if osm_review == "green"
                else f"{OSM_SOURCE} review-status recorded {osm_review!r} ≠ "
                "'green' — the run refuses without the green read; nothing "
                "is flipped to reach it"
            ),
            osm_review,
        )
    )

    # -- exclusions + serialisation -------------------------------------------------------
    materialize = bool(inputs.get("materialize_active"))
    g2 = bool(inputs.get("g2_slot_active"))
    cut = bool(inputs.get("release_cut_active"))
    ex_bad = []
    if materialize:
        ex_bad.append("sig-materialize active")
    if g2:
        ex_bad.append("a G2 slot is active")
    if cut:
        ex_bad.append("a release-cut day is recorded")
    criteria.append(
        Criterion(
            "exclusions",
            not ex_bad,
            (
                f"materialize_active={materialize} g2_slot_active={g2} "
                f"release_cut_active={cut} — no leg runs while materialize, "
                "a G2 slot or a cut day is active"
                if not ex_bad
                else "; ".join(ex_bad)
            ),
        )
    )
    active = inputs.get("active_manual_run") or None
    criteria.append(
        Criterion(
            "serialize",
            active is None,
            f"active_manual_run={active!r} — one manual run at a time, "
            "across waves (P36.12's sequencing rule rides Wave C)",
            active,
        )
    )

    # -- scope (run_set == the declared set, exactly) -------------------------------------
    run_set = _source_ids(inputs.get("run_set", []), "run_set")
    expected = {OSM_SOURCE} if leg == "L3" else set()
    if set(run_set) != expected or len(run_set) != len(set(run_set)):
        criteria.append(
            Criterion(
                "scope",
                False,
                f"run_set {run_set} ≠ the declared {leg} set {sorted(expected)} — "
                "the only run is osm_overpass's national fetch; the mirror "
                "targets are never a run input (their retirement rides the "
                "committed registry diff)",
                run_set,
            )
        )
    else:
        criteria.append(
            Criterion(
                "scope",
                True,
                f"run_set == the declared {leg} set ({len(run_set)} entries)",
                run_set,
            )
        )

    # -- the Wave-B pause posture (FEA-15) ---------------------------------------------------
    pauses = inputs.get("wave_b_pauses") or {}
    unheld = [
        b
        for b in EARLY_FIRE_BATCHES
        if not (isinstance(pauses.get(b), dict) and pauses[b].get("paused") is True)
    ]
    criteria.append(
        Criterion(
            "wave_b_pause",
            not unheld,
            (
                "the four early-fire r11 batch rows recorded held for the "
                "window (paused_until declared; live schedulers paused or "
                "absent-consolidated — FEA-15)"
                if not unheld
                else f"{unheld} not recorded held for 11-16→11-20 — the Wave-B "
                "r11 batch crons pause for the window (FEA-15); a resumed "
                "early fire is never silently allowed"
            ),
            {"unheld": unheld},
        )
    )

    # -- L1 admission: prestate + backup -----------------------------------------------------
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
                        "pre-state capture recorded (instance describe, "
                        "job/trigger JSON, sources.toml sha, cadence --check green)"
                        if captured
                        else "the OM-14 pre-state capture (instance describe, "
                        "job/trigger JSON, green cadence --check) is not "
                        "recorded — capture before the first mutation"
                    ),
                    prestate.get("path"),
                )
            )
        backup = inputs.get("backup")
        if not isinstance(backup, dict):
            criteria.append(Criterion("backup", False, "no AR-2 backup read supplied"))
        else:
            status = backup.get("status")
            criteria.append(
                Criterion(
                    "backup",
                    status == "SUCCESSFUL",
                    (
                        f"AR-2 on-demand backup {backup.get('id')!r} SUCCESSFUL"
                        if status == "SUCCESSFUL"
                        else f"newest sig-pg backup {status!r} — a failed "
                        "restore point stops the leg before the first mutation"
                    ),
                    status,
                )
            )

    # -- L2 admission: the in-ticket tier go ---------------------------------------------------
    if leg == "L2":
        tier_go = inputs.get("tier_go")
        if not isinstance(tier_go, dict) or not str(tier_go.get("verbatim") or "").strip():
            criteria.append(
                Criterion(
                    "tier_go",
                    False,
                    "no recorded tier-bump go — the tier leg is its own "
                    "in-ticket pause, asked when the leg is due (ING-GO-C is "
                    "the wave's go, never the tier's)",
                )
            )
        elif str(tier_go.get("verbatim")).strip() == GO_VERBATIM:
            criteria.append(
                Criterion(
                    "tier_go",
                    False,
                    "the tier go repeats the ING-GO-C text — the tier leg's "
                    "go is its own operator answer, asked in-ticket; "
                    "re-collect it verbatim",
                )
            )
        else:
            try:
                recorded = _iso(tier_go.get("recorded_at"))
            except WaveGateError as exc:
                criteria.append(Criterion("tier_go", False, f"tier_go recorded_at: {exc}"))
            else:
                criteria.append(
                    Criterion(
                        "tier_go",
                        True,
                        f"the in-ticket tier go recorded {recorded.isoformat()} "
                        f"({str(tier_go.get('verbatim'))[:60]!r}…)",
                        recorded.isoformat(),
                    )
                )

    # -- L4 admission: the soak gap --------------------------------------------------------------
    if leg == "L4":
        run = inputs.get("run") or {}
        ended = run.get("completed_at")
        try:
            run_end = _iso(ended)
        except WaveGateError:
            criteria.append(
                Criterion(
                    "soak_ready",
                    False,
                    f"the national run's completed_at {ended!r} is not a "
                    "recorded instant — the 24 h soak cannot be measured",
                )
            )
        else:
            if now is None:
                criteria.append(Criterion("soak_ready", False, "no 'now' to measure the gap"))
            else:
                gap_h = (now - run_end).total_seconds() / 3600.0
                criteria.append(
                    Criterion(
                        "soak_ready",
                        gap_h >= SOAK_HOURS,
                        (
                            f"{gap_h:.1f} h since the recorded run end — the 24 h soak bound holds"
                            if gap_h >= SOAK_HOURS
                            else f"{gap_h:.1f} h since the recorded run end < "
                            f"{SOAK_HOURS} h — the soak waits; a short soak is "
                            "never smoothed over"
                        ),
                        gap_h,
                    )
                )

    if action == "close":
        _close_criteria(leg, inputs, criteria)

    decision = "go" if all(c.ok for c in criteria) else "no-go"
    return Verdict(decision=decision, leg=leg, action=action, criteria=criteria)


def _close_criteria(leg: str, inputs: dict, criteria: list[Criterion]) -> None:
    """The leg-close evidence checks — re-judged on top of admission."""

    # -- L1 closing: the disk read-back ---------------------------------------------------
    if leg == "L1":
        disk = inputs.get("disk") or {}
        size = disk.get("size_gb")
        limit = disk.get("autoresize_limit_gb")
        recorded = disk.get("recorded") is True
        size_ok = isinstance(size, (int, float)) and size >= DISK_GB
        limit_ok = limit == AUTORESIZE_LIMIT_GB
        criteria.append(
            Criterion(
                "disk",
                size_ok and limit_ok and recorded,
                (
                    f"dataDiskSizeGb={size} ≥ {DISK_GB} and "
                    f"storageAutoResizeLimit={limit} == {AUTORESIZE_LIMIT_GB} "
                    "recorded from the live read-back"
                    if size_ok and limit_ok and recorded
                    else f"the disk read-back is not recorded at the Q-23 "
                    f"posture (size_gb={size!r} ≥ {DISK_GB}? "
                    f"limit={limit!r} == {AUTORESIZE_LIMIT_GB}? "
                    f"recorded={recorded}) — the grow is one-way: read the "
                    "current state, never re-grow blindly"
                ),
                disk,
            )
        )
        return

    # -- L2 closing: the tier read-back ----------------------------------------------------
    if leg == "L2":
        tier = inputs.get("tier") or {}
        got = str(tier.get("tier") or "")
        criteria.append(
            Criterion(
                "tier",
                got == TIER_UP and tier.get("recorded") is True,
                (
                    f"settings.tier={got} recorded — the bump holds"
                    if got == TIER_UP and tier.get("recorded") is True
                    else f"settings.tier recorded {got!r} ≠ {TIER_UP!r} — the "
                    "bump's read-back is the close evidence"
                ),
                tier,
            )
        )
        return

    # -- L3 closing: the national-run evidence set -------------------------------------------
    if leg == "L3":
        rebuild = inputs.get("rebuild") or {}
        digest = str(rebuild.get("image_digest") or "")
        pinned = bool(re.fullmatch(r"sha256:[0-9a-f]{64}", digest))
        jobs = set(_source_ids(rebuild.get("jobs", []), "rebuild.jobs"))
        jobs_ok = {OSM_JOB, MIRROR_BATCH_JOB} <= jobs
        criteria.append(
            Criterion(
                "rebuild",
                pinned and jobs_ok and rebuild.get("declared_published") is True,
                (
                    f"the fleet reconciled on {digest[:19]}… — {OSM_JOB} + "
                    f"{MIRROR_BATCH_JOB} rebuilt; the declaration bundle "
                    f"published ({NEW_CRON} + the FEA-15 pauses live)"
                    if pinned and jobs_ok and rebuild.get("declared_published") is True
                    else f"the reconcile is not recorded on one pinned digest "
                    f"carrying both jobs (pinned={pinned} jobs={sorted(jobs)} "
                    f"published={rebuild.get('declared_published')}) — one "
                    "digest, every job (ADR-111); the batch's rebuilt image is "
                    "what carries the mirror-retirement diff"
                ),
                {"image_digest": digest, "jobs": sorted(jobs)},
            )
        )
        retarget = inputs.get("retarget") or {}
        criteria.append(
            Criterion(
                "retarget",
                retarget.get("cron") == NEW_CRON and retarget.get("recorded") is True,
                (
                    f"{OSM_SOURCE} retargeted monthly {NEW_CRON!r} recorded"
                    if retarget.get("cron") == NEW_CRON and retarget.get("recorded") is True
                    else f"the {NEW_CRON!r} monthly retarget is not recorded "
                    f"(recorded cron {retarget.get('cron')!r}) — the weekly "
                    f"12 4 * * 1 → monthly {NEW_CRON} change is the leg's "
                    "cadence mutation"
                ),
                retarget,
            )
        )
        run = inputs.get("run") or {}
        added = run.get("claims_added")
        run_ok = run.get("outcome") == "ok" and isinstance(added, int) and added > 0
        criteria.append(
            Criterion(
                "run",
                run_ok,
                (
                    f"the national run row ok with claims_added={added}"
                    if run_ok
                    else f"the national run is not recorded ok with "
                    f"claims_added > 0 (outcome={run.get('outcome')!r} "
                    f"claims_added={added!r}) — the ≈1.1M-claim first run is "
                    "the leg's core evidence"
                ),
                run,
            )
        )
        tiles = inputs.get("tiles") or {}
        tile_ok = tiles.get("within_tolerance") is True
        criteria.append(
            Criterion(
                "tiles",
                tile_ok,
                (
                    "tile totals within ±2 % of discovery counts and within "
                    f"taginfo's {TAGINFO_TOTAL} for the same date"
                    if tile_ok
                    else "the tile reconciliation is not recorded inside "
                    "tolerance — an unexplained ContentDrift fails the run "
                    "rather than being smoothed (SIG-ENG-042)"
                ),
                tiles,
            )
        )
        privacy = inputs.get("privacy") or {}
        hits = privacy.get("user_uid_captures")
        priv_ok = hits == 0
        criteria.append(
            Criterion(
                "privacy",
                priv_ok,
                (
                    "zero captures containing user/uid — SIG-INGEST-045e on the live leg"
                    if priv_ok
                    else f"user/uid found in {hits!r} captures — the "
                    "mapper-identity stop failed; the run halts, never "
                    "proceeds past a Part VIII edge"
                ),
                privacy,
            )
        )
        plus0 = inputs.get("plus0") or {}
        criteria.append(
            Criterion(
                "plus0",
                plus0.get("claims_added") == 0,
                (
                    "the +0 re-run inserted 0 claims on unchanged input"
                    if plus0.get("claims_added") == 0
                    else f"the +0 re-run shows claims_added="
                    f"{plus0.get('claims_added')!r} ≠ 0 — idempotence is "
                    "proven before the leg closes"
                ),
                plus0,
            )
        )
        er = inputs.get("er") or {}
        merge = er.get("merge_pct")
        net_new = er.get("net_new")
        merge_ok = isinstance(merge, (int, float)) and merge >= ER_MERGE_MIN_PCT
        net_new_ok = isinstance(net_new, int) and net_new >= 0
        lineage_ok = er.get("lineage_recorded") is True
        criteria.append(
            Criterion(
                "er",
                merge_ok and net_new_ok and lineage_ok,
                (
                    f"ER rematerialize: {merge}% of the {MIRROR_REPUBLISH_ROWS} "
                    f"republish rows merged (≥{ER_MERGE_MIN_PCT}%), net-new "
                    f"{net_new} measured, republish↔origin recorded one lineage"
                    if merge_ok and net_new_ok and lineage_ok
                    else f"the ER evidence is incomplete/red (merge_pct="
                    f"{merge!r} net_new={net_new!r} lineage_recorded="
                    f"{er.get('lineage_recorded')}) — below {ER_MERGE_MIN_PCT}% "
                    "the mirrors stay scheduled and the retirement step does "
                    "not close (I8 §7.8)"
                ),
                er,
            )
        )
        retire = inputs.get("retire") or {}
        retired = set(_source_ids(retire.get("targets_retired", []), "retire.targets_retired"))
        still = set(_source_ids(retire.get("still_scheduled", []), "retire.still_scheduled"))
        retire_ok = (
            retired == set(MIRROR_TARGETS)
            and still == set(KEEP_TARGETS)
            and retire.get("derived_from_recorded") is True
            and bool(str(retire.get("next_fire") or "").strip())
        )
        criteria.append(
            Criterion(
                "retire",
                retire_ok,
                (
                    f"the mirror-retirement record: exactly {sorted(MIRROR_TARGETS)} "
                    f"out of {MIRROR_BATCH} (the four CCTV republish targets "
                    "stay), derived_from recorded under PKG-12 ED-49, "
                    f"next-fire {retire.get('next_fire')!r} after the retirement"
                    if retire_ok
                    else f"the retirement record is not exactly the two "
                    f"targets (retired={sorted(retired)} still={sorted(still)} "
                    f"derived_from={retire.get('derived_from_recorded')} "
                    f"next_fire={retire.get('next_fire')!r}) — the diff is "
                    "exactly two targets and the recorded next-fire is after "
                    "the retirement, never before"
                ),
                {"retired": sorted(retired), "still_scheduled": sorted(still)},
            )
        )
        return

    # -- L4 closing: the soak read ----------------------------------------------------------
    if leg == "L4":
        soak = inputs.get("soak") or {}
        soak_ok = (
            soak.get("read") is True
            and soak.get("instance_ok") is True
            and soak.get("no_materialize_overlap") is True
            and bool(str(soak.get("record_ref") or "").strip())
        )
        criteria.append(
            Criterion(
                "soak",
                soak_ok,
                (
                    f"the 24 h soak read recorded ({soak.get('record_ref')!r}): "
                    "instance healthy, no materialize overlap"
                    if soak_ok
                    else "the soak read is not recorded complete (read, "
                    "instance_ok, no_materialize_overlap, record_ref) — the "
                    "revert waits on the recorded read"
                ),
                soak,
            )
        )
        return

    # -- L5 closing: the revert evidence -------------------------------------------------------
    if leg == "L5":
        tier = inputs.get("tier") or {}
        got = str(tier.get("tier") or "")
        criteria.append(
            Criterion(
                "tier",
                got == TIER_DOWN and tier.get("recorded") is True,
                (
                    f"settings.tier={got} recorded — the temporary bump is reverted"
                    if got == TIER_DOWN and tier.get("recorded") is True
                    else f"settings.tier recorded {got!r} ≠ {TIER_DOWN!r} — the "
                    "revert's read-back is the close evidence; the bump is "
                    "temporary-only (Q-23)"
                ),
                tier,
            )
        )
        revert = inputs.get("revert") or {}
        criteria.append(
            Criterion(
                "revert",
                revert.get("post_state_recorded") is True,
                (
                    "the post-revert state recorded (instance describe, "
                    "schedulers, health) — the wave closes on the read-back"
                    if revert.get("post_state_recorded") is True
                    else "the post-revert state capture is not recorded — the "
                    "wave's last leg closes on evidence, never on the patch "
                    "call alone"
                ),
                revert,
            )
        )
        return


def leg_plan() -> list[dict[str, Any]]:
    """The deterministic Wave-C step plan (``sig.wave-c-plan/1`` content).

    Every step is an admission-gated unit: the driver gates the leg
    (``admit``), runs the steps in order, then gates the leg close
    (``close``) before the next leg. Check mode prints this plan; apply
    executes it — a missed leg or a failed verification stops the driver
    and the refusal is recorded.
    """
    steps: list[dict[str, Any]] = []

    def step(leg: str, i: int, kind: str, text: str, **extra: Any) -> None:
        steps.append({"leg": leg, "seq": i, "kind": kind, "step": text, **extra})

    # -- L1 — pre-grow ----------------------------------------------------------------------
    step(
        "L1",
        1,
        "prestate",
        "capture pre-state: `gcloud sql instances describe`, the osm + "
        "camreg-batch-05 job JSON, the scheduler list, sources.toml sha256, "
        "`sig-ops cadence --check` green (OM-14)",
        mutation=False,
    )
    step(
        "L1",
        2,
        "backup",
        "AR-2: on-demand Cloud SQL backup; poll the op to DONE and record "
        "SUCCESSFUL before the first mutation",
        mutation=False,
    )
    step(
        "L1",
        3,
        "disk",
        f"pre-grow the disk: `gcloud sql instances patch sig-pg "
        f"--storage-size={DISK_GB} --async` → poll UPDATE → read "
        "dataDiskSizeGb; one-way — a resumed run reads the current size "
        "and records a SKIP, never re-grows blindly",
        mutation=True,
    )
    step(
        "L1",
        4,
        "limit",
        f"confirm the autoresize limit: patch "
        f"--storage-auto-increase-limit={AUTORESIZE_LIMIT_GB} only if the "
        "read differs (already 40 under B-11 → recorded SKIP); read-back "
        "storageAutoResizeLimit",
        mutation=True,
    )
    step(
        "L1",
        5,
        "record",
        "record the leg: before/after sizes + limits, backup id, `date -u` "
        "start/end — the pre-grow is one-way and recorded",
        mutation=False,
    )

    # -- L2 — tier bump after the go ------------------------------------------------------------
    step(
        "L2",
        1,
        "tier_go",
        "OPERATOR PAUSE — ask the verbatim in-ticket go for the tier bump "
        f"({TIER_UP}, temporary, reverted at L5); the leg refuses on "
        "silence — ING-GO-C is never the tier's go",
        mutation=False,
        operator=True,
    )
    step(
        "L2",
        2,
        "tier",
        f"`gcloud sql instances patch sig-pg --tier={TIER_UP} --async` → "
        "poll UPDATE (the change restarts the instance — one 503 class "
        "is the recorded risk) → api /health",
        mutation=True,
    )
    step(
        "L2",
        3,
        "read",
        "read-back settings.tier + record before/after and `date -u`",
        mutation=False,
    )

    # -- L3 — the national run --------------------------------------------------------------------
    step(
        "L3",
        1,
        "wave_b_pause",
        "record the Wave-B pause posture: the four early-fire r11 batch "
        "schedulers described (absent-consolidated or paused) and the "
        "declared paused_until rows — FEA-15 for the window",
        batches=list(EARLY_FIRE_BATCHES),
        mutation=False,
    )
    step(
        "L3",
        2,
        "rebuild",
        "reconcile the fleet on one pinned digest: "
        "`scheduled-ops.sh --apply` with SIG_JOB_IMAGE=<sha256 digest> — "
        f"{OSM_JOB} rebuilt (the new image carries P37.1's national-tile "
        f"code), {MIRROR_BATCH_JOB} rebuilt (carrying the committed "
        "mirror-retirement diff), the declaration bundle republished "
        f"({NEW_CRON} + the paused_until rows live — the retarget + the "
        "pause bind at publish)",
        mutation=True,
    )
    step(
        "L3",
        3,
        "run",
        f"the first national run (manual, one at a time): `gcloud run "
        f"jobs execute {OSM_JOB} --args "
        f"scheduled-ingest,--source,{OSM_SOURCE},--sink,pg --wait` — "
        "US-first ordering, non-US objects kept (S5-4)",
        source=OSM_SOURCE,
        job=OSM_JOB,
        mutation=True,
    )
    step(
        "L3",
        4,
        "verify",
        "the §7.7 verify set: run row ok + captures landed bytes; tile "
        "totals within ±2 % of discovery counts and within taginfo's "
        f"{TAGINFO_TOTAL}; zero captures containing user/uid "
        "(SIG-INGEST-045e); claims > 0",
        source=OSM_SOURCE,
        mutation=False,
    )
    step(
        "L3",
        5,
        "rerun",
        f"+0 re-run {OSM_SOURCE}: re-execute the same job; assert "
        "claims_added == 0 on unchanged input",
        source=OSM_SOURCE,
        job=OSM_JOB,
        mutation=True,
        expect="claims_added==0",
    )
    step(
        "L3",
        6,
        "er",
        "the camera-site ER rematerialize: `gcloud run jobs execute "
        "sig-materialize --wait` → the counts read — ≥95 % of the "
        f"{MIRROR_REPUBLISH_ROWS} republish rows merged onto OSM origin "
        "sites, the measured net-new count reported, infer_lineages "
        "recording republish↔origin as one lineage (R5 — no corroboration "
        "between them)",
        mutation=True,
    )
    step(
        "L3",
        7,
        "retire",
        f"record the mirror retirement: {MIRROR_BATCH_JOB}'s deployed "
        "image carries the committed diff — exactly the two ALPR mirror "
        "targets out of camreg-batch-05, the four CCTV republish targets "
        "still scheduled, derived_from recorded under PKG-12 ED-49, the "
        "next-fire (12-10 03:35Z) recorded after the retirement",
        targets=list(MIRROR_TARGETS),
        keep=list(KEEP_TARGETS),
        mutation=False,
    )
    step(
        "L3",
        8,
        "record",
        "record the leg: run rows, the verify set, the +0 diff, the ER "
        "counts, the retirement record — a missed leg is reported, never "
        "silently skipped",
        mutation=False,
    )

    # -- L4 — the 24 h soak read ------------------------------------------------------------------
    step(
        "L4",
        1,
        "soak",
        "the §7.7 soak read (≥24 h after the recorded run end; read-only — "
        "inside the window or the 48 h grace): instance describe healthy, "
        "run rows stable, no sig-materialize execution overlapping, the "
        "record ref captured",
        mutation=False,
    )

    # -- L5 — revert -------------------------------------------------------------------------------
    step(
        "L5",
        1,
        "tier",
        f"`gcloud sql instances patch sig-pg --tier={TIER_DOWN} --async` → "
        "poll UPDATE → api /health — the bump is temporary-only (Q-23)",
        mutation=True,
    )
    step(
        "L5",
        2,
        "record",
        "post-state capture + closeout record: tier read-back, scheduler "
        "posture, run ledger closed — every leg's command, start/end "
        "and outcome receipted",
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
        prog="sig-ops wave-c-gate",
        description=(
            "P37.2 Wave-C leg gate (sig.wave-c-gate/1): judges a recorded "
            "inputs JSON — refuses the leg (exit 42) unless the verbatim "
            "ING-GO-C, the window, the leg order, Q-23, review-status "
            "green, the Wave-B pause, serialisation and the leg's "
            "prerequisites/evidence (prestate/backup/disk, the in-ticket "
            "tier go, the national-run verify set + ER + retirement "
            "record, the 24 h soak, the revert) all hold."
        ),
    )
    ap.add_argument("--inputs", required=True, help="the recorded inputs JSON")
    ap.add_argument("--out", default=None, help="also write the verdict JSON here")
    args = ap.parse_args(argv)

    try:
        inputs = load_inputs(args.inputs)
        verdict = evaluate(inputs)
    except WaveGateError as exc:
        print(f"sig-ops wave-c-gate: REFUSED — {exc}", file=sys.stderr)
        return 2

    record = verdict.to_record()
    text = json.dumps(record, indent=2, sort_keys=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"sig-ops wave-c-gate: -> {args.out}", file=sys.stderr)
    if verdict.decision != "go":
        print(
            "sig-ops wave-c-gate: NO-GO — the leg refuses; queued with its "
            "re-run prompt (see record).",
            file=sys.stderr,
        )
        return 42
    return 0


def plan_main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="sig-ops wave-c-plan",
        description=(
            "P37.2 Wave-C step plan (sig.wave-c-plan/1): the deterministic "
            "ordered steps for L1…L5 — plan-only output, never a mutation."
        ),
    )
    ap.add_argument("--json", action="store_true", help="emit the JSON record")
    args = ap.parse_args(argv)
    steps = leg_plan()
    if args.json:
        print(
            json.dumps(
                {
                    "kind": PLAN_SCHEMA,
                    "wave": WAVE,
                    "window": [WINDOW_START, WINDOW_END],
                    "earliest_start": EARLIEST_START,
                    "steps": steps,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        f"Wave {WAVE} activation plan — window {WINDOW_START} → {WINDOW_END} "
        "(ING-GO-C; the tier bump on its own in-ticket go; one manual run "
        "at a time)"
    )
    for s in steps:
        mark = " (mutation)" if s.get("mutation") else ""
        op = " [OPERATOR]" if s.get("operator") else ""
        print(f"  {s['leg']}.{s['seq']:>2}  {s['step']}{mark}{op}")
    return 0


__all__ = [
    "AUTORESIZE_LIMIT_GB",
    "Criterion",
    "DISK_GB",
    "EARLIEST_START",
    "EARLY_FIRE_BATCHES",
    "EARLY_LANDINGS",
    "ER_MERGE_MIN_PCT",
    "GO_VERBATIM",
    "KEEP_TARGETS",
    "LEGS",
    "MIRROR_BATCH",
    "MIRROR_BATCH_JOB",
    "MIRROR_REPUBLISH_ROWS",
    "MIRROR_TARGETS",
    "MUTATION_LEGS",
    "NEW_CRON",
    "OSM_JOB",
    "OSM_SCHEDULER",
    "OSM_SOURCE",
    "PLAN_SCHEMA",
    "RERUN",
    "SCHEMA",
    "SOAK_GRACE_END",
    "SOAK_HOURS",
    "TAGINFO_TOTAL",
    "TIER_DOWN",
    "TIER_UP",
    "TILE_TOLERANCE_PCT",
    "Verdict",
    "WINDOW_END",
    "WINDOW_FIRST_DATE",
    "WINDOW_LAST_DATE",
    "WINDOW_START",
    "WaveGateError",
    "evaluate",
    "gate_main",
    "leg_plan",
    "plan_main",
]
