# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.44 (REL-07; SIG-REL-011, SIG-OPS-008; D-G3-4 [B-9] = yes) — the release
cadence evaluator.

The ``sig-sched-release-cut`` job's deterministic core — the cadence contract
verbatim (SIG-REL-011 / G3 §7.2, the ticket's live-window cell):

* **scheduled** — the cut fires on the *first weekday on/after the 15th at
  14:00Z*. Cloud Scheduler cannot express that in one cron field, so
  ``sig-sched-release-cut`` fires ``0 14 15-17 * *`` (the three candidate
  days) and this evaluator suppresses the non-first weekdays
  (future-ok: scheduled: window-cell instances 2026-11-16 / 2026-12-15).
* **suppressed** — the scheduled cut is SUPPRESSED when a Class S promotion
  landed within the previous 14 days (a recorded fact off the registry
  journal — the ``promoted`` event's ``class`` — never a guess);
* **early** — net-new publishable claims ≥ 10 % of the release's published
  claims AND ≥ 14 days since the last promotion (of either class — the gap
  condition already excludes a fresh promotion's fortnight);
* **max age** — a release older than 35 days alerts through the
  recorded-alert seam (``ops.alerts``; G3 §7.2 adds: *cut* at 35 days if no
  cut is running — a running candidate is never double-cut);
* **freeze** — no ``cut`` starts inside an AR-3 window (the daily
  03:00–06:30Z band plus the monthly batch window day 6 00:00Z →
  day 13 12:00Z, :func:`exports.release_identity.freeze_window`); the freeze
  is a *recorded check* on every evaluation, and ``release cut``'s own
  ``assert_not_frozen`` refuses too — two layers, one rule;
* **weekly ``sig-materialize``** — G1 §3.6 verbatim: Sundays 08:00 UTC
  (``0 8 * * 0``) so the materialized read models lag live claims by at most
  7 days (SIG-OPS-008). The scheduler trigger is the deferred leg; this row
  ships the declared cron + driver.

The evaluator is the *shared* drift half TX-07 (P36.43) names: the status
lane reads the same ``evaluate`` result shape when it reports release drift
— one evaluator, never two rules.

Honest inputs only: an absent ``latest.json`` decides ``no_release``; an
absent delta input marks the early trigger ``not_evaluable`` — the record
says so, never a fabricated 0 or a guessed denominator (SIG-ENG-042).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any

from exports.release_identity import freeze_window

from .alerts import Alert, AlertLedger, fire, notifiers_from_env

# --------------------------------------------------------------------------- #
# The contract constants — SIG-REL-011 / G3 §7.2 / D-G3-4 [B-9] = yes, verbatim
# --------------------------------------------------------------------------- #

#: The decision record this module emits per evaluation.
CADENCE_SCHEMA = "sig.release-cadence/1"

#: The cut's day-of-month anchor: the first weekday on/after the 15th.
CUT_DAY_OF_MONTH = 15
#: The cut instant on that day (UTC).
CUT_TIME_UTC = time(14, 0)
#: The scheduler trigger's cron — the three days a "first weekday on/after
#: the 15th" can land on (15th weekday → itself; 15th Sat → Mon 17th;
#: 15th Sun → Mon 16th). The evaluator suppresses the off days.
RELEASE_CRON = "0 14 15-17 * *"
#: The weekly sig-materialize trigger's cron — G1 §3.6 verbatim
#: "weekly (Sundays 08:00 UTC)".
MATERIALIZE_CRON = "0 8 * * 0"

#: Early cut: net-new publishable claims reach this fraction of the release's
#: published claims …
EARLY_NET_NEW_FRACTION = 0.10
#: … AND this many days have passed since the last promotion.
EARLY_MIN_PROMOTION_GAP_DAYS = 14
#: A Class S promotion within this many days suppresses the scheduled cut.
CLASS_S_SUPPRESSION_DAYS = 14
#: Release age that alerts (and cuts when no cut is running — G3 §7.2).
MAX_AGE_DAYS = 35

#: The decision vocabulary (closed; a regression over it fails tests loud).
DECISIONS = ("cut", "suppressed", "alert", "frozen", "hold", "no_release")

#: §3.4 fold states a candidate occupies between cut and promote — any
#: publication in one means a cut is in flight and the max-age leg alerts
#: without double-cutting.
IN_FLIGHT_STATES = frozenset({"cut", "built", "staged", "verified", "classified"})

#: The recorded alert kind a stale release fires.
MAX_AGE_ALERT_KIND = "release-max-age"


class CadenceError(RuntimeError):
    """The cadence leg refused — bad inputs, never a silent skip."""


# --------------------------------------------------------------------------- #
# The calendar half — pure functions, no I/O
# --------------------------------------------------------------------------- #


def cut_day(year: int, month: int) -> Any:
    """The month's cut day: the first weekday (Mon–Fri) on/after the 15th.

    15th Mon–Fri → the 15th itself; 15th Saturday → Monday the 17th; 15th
    Sunday → Monday the 16th.
    """
    from datetime import date

    day = date(year, month, CUT_DAY_OF_MONTH)
    while day.isoweekday() > 5:  # Sat=6, Sun=7
        day += timedelta(days=1)
    return day


def cut_instant(year: int, month: int) -> datetime:
    """The cut slot: ``cut_day`` at 14:00Z."""
    return datetime.combine(cut_day(year, month), CUT_TIME_UTC, tzinfo=UTC)


def scheduled_due(now: datetime) -> bool:
    """Whether ``now`` sits inside this month's cut slot — the cut day at or
    after 14:00Z (a delayed 14:0x execution still counts; the next day does
    not — that slot has passed)."""
    now = now.astimezone(UTC)
    slot = cut_instant(now.year, now.month)
    return now.date() == slot.date() and now >= slot


@dataclass(frozen=True)
class Promotion:
    """One recorded promotion: its publication, its class, its instant."""

    publication_id: str
    release_class: str | None  # "R" | "S" (or None when the record carries none)
    activated_at: datetime


def _parse_ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def promotions_from_events(events: Iterable[Mapping[str, Any]]) -> list[Promotion]:
    """The promotion history off the release journal: every ``promoted``
    event carries ``publication_id`` + ``class`` (``class_r``/``class_s``) +
    ``recorded_at`` — the recorded promotion instant. Ordered by instant."""
    out: list[Promotion] = []
    for ev in events:
        if ev.get("verb") != "promoted":
            continue
        pub = str(ev.get("publication_id") or "")
        ts = ev.get("recorded_at") or ev.get("utc_instant")
        if not pub or not ts:
            continue
        cls_raw = str(ev.get("class") or "")
        cls = {"class_r": "R", "class_s": "S", "R": "R", "S": "S"}.get(cls_raw)
        out.append(
            Promotion(publication_id=pub, release_class=cls, activated_at=_parse_ts(str(ts)))
        )
    out.sort(key=lambda p: p.activated_at)
    return out


def last_promotion(promotions: Iterable[Promotion]) -> Promotion | None:
    """The newest promotion in the history (``None`` when never promoted)."""
    items = list(promotions)
    return items[-1] if items else None


def in_flight_publications(events: Iterable[Mapping[str, Any]]) -> list[str]:
    """Publications whose journal fold leaves them between ``cut`` and a
    terminal state — a cut in flight (the max-age leg alerts, never
    double-cuts)."""
    from .release_pipeline import fold_state

    pubs: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        pub = ev.get("publication_id")
        if pub:
            pubs.setdefault(str(pub), []).append(dict(ev))
    return sorted(
        pub for pub, evs in pubs.items() if fold_state(evs, pub)["state"] in IN_FLIGHT_STATES
    )


# --------------------------------------------------------------------------- #
# The evaluation — one pure function over the recorded facts
# --------------------------------------------------------------------------- #


def evaluate(
    now: datetime,
    *,
    promotions: Iterable[Promotion],
    latest: Mapping[str, Any] | None,
    spine_eligible: int | None,
    release_published: int | None,
    cut_running: bool,
) -> dict[str, Any]:
    """Evaluate the cadence rules at ``now`` → a ``sig.release-cadence/1``
    record. Every rule the contract names is a computed field; the decision
    is their fold. ``latest`` is the registry's ``latest.json`` (or ``None``);
    ``spine_eligible``/``release_published`` are the delta inputs (``None``
    marks the early trigger not_evaluable)."""
    now = now.astimezone(UTC)
    promos = sorted(promotions, key=lambda p: p.activated_at)
    last = promos[-1] if promos else None
    window = freeze_window(now)
    slot = cut_instant(now.year, now.month)
    due = scheduled_due(now)

    days_since = (now - last.activated_at).total_seconds() / 86400.0 if last is not None else None
    class_s_recent = bool(
        last is not None
        and last.release_class == "S"
        and days_since is not None
        and days_since < CLASS_S_SUPPRESSION_DAYS
    )

    # release age off the latest pointer's activated_at
    age_days: float | None = None
    if latest is not None:
        activated = latest.get("activated_at")
        if activated:
            age_days = (now - _parse_ts(str(activated))).total_seconds() / 86400.0

    # the delta trigger — never a fabricated denominator
    delta_evaluable = spine_eligible is not None and release_published is not None
    net_new: int | None = None
    fraction: float | None = None
    if spine_eligible is not None and release_published is not None:
        net_new = spine_eligible - release_published
        if release_published:
            fraction = net_new / release_published
    early_due = bool(
        delta_evaluable
        and fraction is not None
        and fraction >= EARLY_NET_NEW_FRACTION
        and days_since is not None
        and days_since >= EARLY_MIN_PROMOTION_GAP_DAYS
    )
    max_age = bool(age_days is not None and age_days > MAX_AGE_DAYS)

    triggers: list[str] = []
    if due and not window and not class_s_recent:
        triggers.append("scheduled")
    if early_due and not window:
        triggers.append("early")
    if max_age and not window and not cut_running:
        triggers.append("max_age")

    if last is None:
        decision = "no_release"
    elif window:
        decision = "frozen"
    elif due and class_s_recent:
        decision = "suppressed"
    elif triggers:
        decision = "cut"
    elif max_age:
        decision = "alert"
    else:
        decision = "hold"

    record: dict[str, Any] = {
        "schema": CADENCE_SCHEMA,
        "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contract": {
            "scheduled": "first weekday on/after the 15th at 14:00Z",
            "early": "net-new publishable claims ≥ 10 % of the release's published claims "
            "AND ≥ 14 days since the last promotion",
            "suppression": "a Class S promotion within the previous 14 days "
            "suppresses the scheduled cut",
            "max_age": "a release older than 35 days alerts; it cuts only when no cut is running",
            "freeze": "no cut starts inside an AR-3 window",
            "decision": "D-G3-4 [B-9] = yes (carried verbatim)",
        },
        "cut_slot": {
            "cron": RELEASE_CRON,
            "day": slot.date().isoformat(),
            "instant": slot.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "due": due,
        },
        "materialize": {
            "cron": MATERIALIZE_CRON,
            "note": "G1 §3.6 verbatim — weekly Sundays 08:00 UTC; the "
            "materialized views lag live claims by at most 7 days",
        },
        "window": {"frozen": window is not None, "ar3": window},
        "release": {
            "publication_id": (latest or {}).get("publication_id"),
            "label": (latest or {}).get("label"),
            "class": (latest or {}).get("class"),
            "activated_at": (latest or {}).get("activated_at"),
            "age_days": round(age_days, 4) if age_days is not None else None,
            "published_claims": release_published,
        },
        "promotion": {
            "last_publication_id": last.publication_id if last else None,
            "last_class": last.release_class if last else None,
            "last_activated_at": (
                last.activated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if last else None
            ),
            "days_since": round(days_since, 4) if days_since is not None else None,
        },
        "delta": {
            "spine_eligible": spine_eligible,
            "release_published": release_published,
            "net_new": net_new,
            "net_new_fraction": round(fraction, 6) if fraction is not None else None,
            "evaluable": delta_evaluable,
        },
        "triggers": {
            "scheduled": due and not window,
            "early": early_due if delta_evaluable else "not_evaluable",
            "max_age": max_age,
        },
        "suppressions": {
            "class_s_recent": class_s_recent,
            "ar3_freeze": window is not None,
        },
        "cut_running": cut_running,
        "triggered_by": triggers,
        "decision": decision,
        "alert": (
            {
                "kind": MAX_AGE_ALERT_KIND,
                "severity": "alarm",
                "message": (
                    "release "
                    f"{(latest or {}).get('label') or (latest or {}).get('publication_id')} "
                    f"is {age_days:.1f} days old (> {MAX_AGE_DAYS})"
                ),
            }
            if max_age
            else None
        ),
    }
    return record


def fire_max_age_alert(
    record: Mapping[str, Any],
    *,
    ledger: AlertLedger,
    notifiers: list[Any] | None = None,
) -> Alert | None:
    """Fire the recorded max-age alert the record's ``alert`` block names —
    the ledger write stands even when no notifier is configured (OBS.1)."""
    spec = record.get("alert")
    if not spec:
        return None
    alert = Alert.create(
        str(spec["kind"]),
        str(spec["severity"]),
        str(spec["message"]),
        detail={
            "release": record.get("release"),
            "evaluated_at": record.get("evaluated_at"),
            "decision": record.get("decision"),
        },
        now=str(record.get("evaluated_at") or ""),
    )
    return fire(alert, ledger=ledger, notifiers=notifiers or notifiers_from_env())


# --------------------------------------------------------------------------- #
# Registry reads + the emit leg
# --------------------------------------------------------------------------- #


def registry_facts(store: Any) -> dict[str, Any]:
    """The recorded facts the evaluator needs: the latest pointer, the
    promotion history off the journal, and whether a cut is in flight."""
    from .release_pipeline import list_events

    events = list_events(store)
    latest_body = store.read("registry/latest.json")
    latest: dict[str, Any] | None = None
    if latest_body is not None:
        try:
            latest = json.loads(latest_body)
        except ValueError:
            latest = {"_unreadable": True}
    return {
        "latest": latest,
        "promotions": promotions_from_events(events),
        "in_flight": in_flight_publications(events),
        "events": len(events),
    }


def emit_decision(record: Mapping[str, Any], out_dir: str | Path) -> dict[str, Path]:
    """Write the decision record append-only under
    ``<out>/cadence/<evaluated_at>.json`` plus one JSONL line in
    ``decisions.jsonl`` (the run-row pattern — a same-instant re-emit is
    byte-identical)."""
    out = Path(out_dir)
    ts = str(record["evaluated_at"]).replace(":", "").replace("-", "")
    dest = out / "cadence" / f"{ts}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(record, indent=2, sort_keys=True) + "\n"
    dest.write_text(body, encoding="utf-8")
    jsonl = out / "cadence" / "decisions.jsonl"
    with jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return {"decision": dest, "jsonl": jsonl}


# --------------------------------------------------------------------------- #
# The verb — sig-ops release-cadence
# --------------------------------------------------------------------------- #


def _alert_ledger(path: str | None) -> AlertLedger:
    return AlertLedger(path or os.environ.get("SIG_ALERT_LOG", ".sig/ops/alerts.jsonl"))


def run_release_cadence(args: Any) -> int:
    """``sig-ops release-cadence`` — evaluate the cadence over the release
    registry, optionally emit + journal + (decision=cut) run ``release cut``.
    Exit 0 ok · 2 refusal · 6 a recorded alert fired."""
    from .release_pipeline import PipelineError, open_store

    registry = getattr(args, "registry", None) or os.environ.get("SIG_RELEASE_REGISTRY", "")
    if not registry:
        print(
            "release-cadence: needs --registry / SIG_RELEASE_REGISTRY — the "
            "release registry the journal + latest.json live in (a local dir "
            "for the fixture leg)"
        )
        return 2
    try:
        store = open_store(registry)
        facts = registry_facts(store)
    except (PipelineError, OSError, ValueError) as exc:
        print(f"release-cadence: refused — {exc}")
        return 2

    facts_in: dict[str, Any] = {}
    if getattr(args, "facts", None):
        try:
            facts_in = json.loads(Path(args.facts).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"release-cadence: --facts unreadable — {exc}")
            return 2
    spine_eligible = facts_in.get("spine_eligible", getattr(args, "spine_eligible", None))
    release_published = facts_in.get("release_published", getattr(args, "release_published", None))
    cut_running = bool(facts_in.get("cut_running", getattr(args, "cut_running", None))) or bool(
        facts["in_flight"]
    )

    now = _parse_ts(args.at) if getattr(args, "at", None) else datetime.now(UTC)
    record = evaluate(
        now,
        promotions=facts["promotions"],
        latest=facts["latest"],
        spine_eligible=spine_eligible,
        release_published=release_published,
        cut_running=cut_running,
    )
    print(
        f"release-cadence {record['evaluated_at']}: decision={record['decision']} "
        f"triggers={record['triggered_by'] or '—'} "
        f"cut_day={record['cut_slot']['day']} window={record['window']['ar3'] or 'open'}"
    )

    if getattr(args, "out", None):
        written = emit_decision(record, args.out)
        print(f"release-cadence: emitted {written['decision']}")

    fired = None
    if record["alert"] and (getattr(args, "alert", False) or getattr(args, "apply", False)):
        fired = fire_max_age_alert(record, ledger=_alert_ledger(getattr(args, "ledger", None)))
        if fired is not None:
            print(f"release-cadence: RECORDED alert {fired.kind} — {fired.message}")

    if getattr(args, "apply", False):
        from .release_pipeline import emit_event

        name = emit_event(
            store,
            "cadence",
            (facts["latest"] or {}).get("publication_id"),
            {
                "outcome": "evaluated",
                "decision": record["decision"],
                "triggered_by": record["triggered_by"],
                "in_flight": facts["in_flight"],
            },
            now=now,
        )
        print(f"release-cadence: journaled {name}")
        if record["decision"] == "cut":
            from .release_pipeline import verb_cut

            try:
                result = verb_cut(
                    store,
                    apply_=True,
                    now=now,
                    skip_host_clock=bool(getattr(args, "skip_host_clock_check", False)),
                )
            except PipelineError as exc:
                print(f"release-cadence: the cut refused — {exc}")
                return 2
            print(
                f"release-cadence: cut recorded (event {result.get('event')}); "
                "the hosted legs run as the job's chained script calls"
            )

    from .alerts import alert_exit_code

    return alert_exit_code(fired)
