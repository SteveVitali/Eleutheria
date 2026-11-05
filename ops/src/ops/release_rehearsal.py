# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.70 (REL-11, manifest row 417) — the second-release acceptance rehearsal.

``D-G3-3 [B-9] = a`` (the plan cell, verbatim): *the first Class R promotion
runs under the standing go if it is still valid (renewed at GATE-G5);
otherwise as Class S (IN-TICKET PAUSE)*. The GATE-G5 sitting
(2026-10-25T18:40Z) renewed the go verbatim — it expires at GATE-G6 or
2026-11-24, whichever is first — and the contract's own live-window cell is
``after P36.72b promotes (>= 2026-11-13T12:00Z); weekday 14:00-20:00Z``. The
rehearsal leg's precondition is therefore the operator's HG-11 act at the
GATE-G6 sitting — exactly when the go expires — so the contract's fallback
applies and the leg runs **Class S** under operator authority records
(``registry/authorities/<name>.json``, ``sig.operator-authority/1`` — the
verbs verify them, never create them, SIG-SEC-010).

This module is the bounded, reversible machinery the OM-19 re-run executes
(``implement-spec spec=docs/tickets/417_P36.70__second-release-acceptance.md
live_verification=true``). Four legs, each timed against the G3 budgets the
measured run replaces (``[est]`` → measured):

1. **``rollback-to-prior``** — ``verb_rollback --to <prior promoted
   release|legacy floor>`` re-points ``latest`` at the predecessor under the
   CURRENT withdrawal set (§8.1; never a traffic reversion, RR-7).
2. **``rollback-restore``** — ``verb_rollback --to <the promoted release>``
   restores the pointer — the rehearsal leaves ``latest`` exactly where it
   found it.
3. **``withdraw-deny``** — ``verb_withdraw`` on a *low-stakes* rehearsal
   order (entity-kind targets only, ≤ 4, ``assert_bounded_orders`` refuses a
   wider blast radius) — the deny lands on every alias with a dated
   tombstone (SIG-REL-D13).
4. **``withdraw-reinstate``** — ``verb_withdraw`` with the matching
   ``allow`` order. Reinstatement is the documented append-only path: a NEW
   disposition, never an edit (the byte-level restore is the next release's
   staging — the record says so, never a smoothed claim).

Every leg is measured (injected ``monotonic``/``now_fn`` — the fixture tests
drive a deterministic clock) and judged against its budget: §8.1's ≤ 10 min
command→verified for the rollback pair and SIG-REL-D13's ≤ 15 min
every-alias SLA for the withdrawal pair. A measured overrun is recorded
(``within_budget: false``), never smoothed (SIG-ENG-042). The run emits one
``sig.release-rehearsal/1`` record — to ``--out`` always, and appended under
``registry/rehearsals/`` on ``--apply`` — and nothing runs without
``--apply``: check mode plans and reports blockers only.

Blockers (each a QUEUED reason, never a fabricated run): no promoted release
(P36.72b's ``D-P36.72b-1`` promote has not run), no rollback target (no
earlier promoted pub with a staged tree and no imported legacy floor), a
cleared ``latest`` pointer, an unverifiable go/authority record, or a
rehearsal target with no staged entity route. ``--apply`` exits 42 on any
blocker so a queued leg can never be forced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exports.manifest import canonical_json
from policy.eligibility import DENYING, Disposition, ReasonCategory, TargetKind

from . import release_conf as rc
from . import release_pipeline as rp
from . import release_reversal as rr

#: The rehearsal record schema id.
REHEARSAL_SCHEMA = "sig.release-rehearsal/1"

#: Append-only home for applied rehearsal records inside the registry.
REHEARSALS_PREFIX = "registry/rehearsals/"

#: The order schema the rehearsal emits (the §8.3 contract — same writer).
ORDER_SCHEMA = rr.ORDER_SCHEMA

#: The bounded blast radius: a rehearsal order carries at most this many
#: low-stakes entity targets — a wider order is a real withdrawal, never a
#: rehearsal, and the runner refuses it.
MAX_ORDER_ENTRIES = 4

#: The budgets the measured run judges (recorded per leg, never a pass/fail
#: rewrite): G3 §8.1 targets ≤ 10 min command→verified for a rollback;
#: SIG-REL-D13 (G3 §8.3/D-G3-9) gives a withdrawal ≤ 15 min to reach every
#: alias. Both were ``[est]`` until this row measures them.
ROLLBACK_BUDGET_S = 600.0
WITHDRAW_BUDGET_S = 900.0

#: The journal reason every rehearsal verb records — greppable, honest.
REHEARSAL_REASON = "P36.70 second-release acceptance rehearsal (REL-11)"

REASON_CATEGORY = ReasonCategory.SAFETY_WITHDRAWAL


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# The rehearsal orders — deterministic sig.withdrawal-order/1 pairs          #
# ---------------------------------------------------------------------------#


def rehearsal_orders(
    entity_ids: list[str],
    *,
    compartment: str | None = None,
    reason_category: str = REASON_CATEGORY.value,
    prefix: str = "rehearsal",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The deterministic ``sig.withdrawal-order/1`` pair for the rehearsal:
    one *deny* order (``withdraw`` on each named low-stakes entity record)
    and its matching *reinstate* order (``allow`` on exactly the same
    targets — a NEW disposition, the documented reinstatement path, never an
    edit). Byte-stable for a given input so a resumed run re-derives the
    same orders."""
    try:
        category = ReasonCategory(str(reason_category))
    except ValueError as exc:
        raise rp.PipelineError(
            "bad-reason-category", f"{reason_category!r} is not a ReasonCategory: {exc}"
        ) from exc
    ids = [str(e).strip() for e in entity_ids]
    if not ids or any(not e for e in ids):
        raise rp.PipelineError(
            "no-rehearsal-target", "the rehearsal needs ≥1 low-stakes entity id — never guessed"
        )
    if len(ids) > MAX_ORDER_ENTRIES:
        raise rp.PipelineError(
            "order-too-wide",
            f"{len(ids)} targets > the bounded rehearsal maximum {MAX_ORDER_ENTRIES} — "
            "a wider order is a real withdrawal, never a rehearsal",
        )

    def _doc(kind: str, disposition: Disposition) -> dict[str, Any]:
        entries = [
            {
                "target_kind": TargetKind.ENTITY.value,
                "target_id": eid,
                "disposition": disposition.value,
                "reason_category": category.value,
                "compartment": compartment,
                "evidence_claim_id": None,
                "supersedes": None,
            }
            for eid in ids
        ]
        return {
            "schema": ORDER_SCHEMA,
            "order_id": f"{prefix}-{kind}-" + "-".join(ids)[:48],
            "note": (
                f"P36.70 rehearsal {kind} order — bounded (entity-kind, ≤ "
                f"{MAX_ORDER_ENTRIES} targets) and reversible (the {kind} "
                "is answered by its twin order); never a real takedown"
            ),
            "entries": entries,
        }

    return _doc("deny", Disposition.WITHDRAW), _doc("allow", Disposition.ALLOW)


def assert_bounded_orders(
    deny_entries: list[dict[str, Any]], allow_entries: list[dict[str, Any]]
) -> None:
    """The rehearsal bound: every deny entry is an entity-kind *denying*
    disposition and the reinstate order is exactly the ``allow`` twin —
    same (target_kind, target_id, compartment) set, never a wider or
    mismatched pair. Anything else is a real withdrawal the rehearsal
    runner refuses to execute."""
    if not (1 <= len(deny_entries) <= MAX_ORDER_ENTRIES):
        raise rp.PipelineError(
            "order-too-wide",
            f"the deny order carries {len(deny_entries)} entries — the bounded rehearsal "
            f"maximum is {MAX_ORDER_ENTRIES} low-stakes targets",
        )
    for i, e in enumerate(deny_entries):
        if e["target_kind"] != TargetKind.ENTITY:
            raise rp.PipelineError(
                "order-too-wide",
                f"deny entry {i} targets {e['target_kind'].value} — the rehearsal withdraws "
                "low-stakes entity records only (never a release, compartment or artifact)",
            )
        if e["disposition"] not in DENYING:
            raise rp.PipelineError(
                "order-not-denying",
                f"deny entry {i} carries disposition {e['disposition'].value!r} — "
                "the deny order must deny",
            )

    def _key(e: dict[str, Any]) -> tuple[str, str, str | None]:
        return (e["target_kind"].value, e["target_id"], e.get("compartment"))

    if len(allow_entries) != len(deny_entries) or {_key(e) for e in allow_entries} != {
        _key(e) for e in deny_entries
    }:
        raise rp.PipelineError(
            "order-mismatch",
            "the reinstate order must name exactly the deny order's targets "
            "(kind + id + compartment) — a wider or narrower pair is refused",
        )
    for i, e in enumerate(allow_entries):
        if e["disposition"] != Disposition.ALLOW:
            raise rp.PipelineError(
                "order-not-allow",
                f"reinstate entry {i} carries {e['disposition'].value!r}, not 'allow' — "
                "the reinstatement is a NEW allow disposition, never anything else",
            )


# --------------------------------------------------------------------------- #
# plan — resolve the legs against the registry, read-only                    #
# ---------------------------------------------------------------------------#


def resolve(store: rp.Store) -> dict[str, Any]:
    """Resolve the rehearsal's two pointers read-only: the *current* latest
    publication (the release the rehearsal serves around — P36.72b's
    promoted core-surfaces release when it has run) and the *rollback
    target* (the recorded previous pointer, else the newest earlier promoted
    release with a staged tree, else an imported ``legacy-*`` floor). The
    verbs re-validate at apply time — this resolves what the plan names."""
    gen = rc.current_generation(store)
    latest = rc.read_generation(store, gen) if gen else None
    current_pub = str(latest.get("publication_id") or "") or None if latest else None
    promoted = rc.read_promoted_map(store, gen) if gen else set()
    candidates: list[str] = []
    if latest:
        prev = str(latest.get("previous") or "")
        if prev:
            candidates.append(prev)
    for g in range(gen - 1, 0, -1):
        doc = rc.read_generation(store, g) or {}
        pub = str(doc.get("publication_id") or "")
        if pub:
            candidates.append(pub)
    rollback_target: str | None = None
    target_kind: str | None = None
    for cand in candidates:
        if (
            rc.PUB_RE.match(cand)
            and cand != current_pub
            and cand in promoted
            and store.list(f"staged/v/{cand}/")
        ):
            rollback_target = cand
            target_kind = "pub"
            break
    if rollback_target is None:
        floors = [
            str(f.get("label") or "")
            for f in rr._floor_record(store).get("floors") or []
            if rr.LEGACY_LABEL_RE.match(str(f.get("label") or ""))
        ]
        if floors:
            rollback_target = floors[-1]
            target_kind = "floor"
    return {
        "conf_gen": gen,
        "latest": latest,
        "current_pub": current_pub,
        "promoted": sorted(promoted),
        "rollback_target": rollback_target,
        "target_kind": target_kind,
    }


def blockers(store: rp.Store, *, go: str | None = None, authority: str | None = None) -> list[str]:
    """The QUEUED reasons an ``--apply`` must refuse: each names why the
    leg cannot run yet — never a fabricated precondition. P36.72b's promote
    (``D-P36.72b-1``) is the first: without a promoted release there is no
    second release to rehearse on."""
    out: list[str] = []
    snap = resolve(store)
    if snap["conf_gen"] == 0:
        out.append(
            "no-promoted-release — registry/conf/ holds no generation; "
            "P36.72b's promote (D-P36.72b-1, the operator's HG-11 act) has not run"
        )
        return out
    if not snap["current_pub"]:
        out.append(
            "cleared-latest — the latest pointer names no publication; a rehearsal "
            "needs a promoted release to serve around"
        )
    if snap["rollback_target"] is None:
        out.append(
            "no-rollback-target — no earlier promoted release with a staged tree "
            "and no imported legacy floor (release import-floor lands it, §8.5)"
        )
    for label, name in (("go", go), ("authority", authority)):
        if name is None:
            out.append(
                f"{label}-unnamed — the Class S fallback needs the operator's "
                f"sig.operator-authority/1 record named for the {label} slot "
                f"(registry/authorities/<name>.json; the verbs verify it, never create it)"
            )
            continue
        try:
            rr.check_authority(store, name)
        except rp.PipelineError as exc:
            out.append(f"{label}-refused [{exc.code}] — {exc}")
    return out


def plan(store: rp.Store, *, go: str | None = None, authority: str | None = None) -> dict[str, Any]:
    """The read-only plan: resolved pointers + the four legs + every
    blocker. A blocked plan prints the QUEUED state, never a guess."""
    snap = resolve(store)
    found = blockers(store, go=go, authority=authority)
    legs = [
        {
            "leg": "rollback-to-prior",
            "verb": "rollback",
            "to": snap["rollback_target"],
            "budget_s": ROLLBACK_BUDGET_S,
        },
        {
            "leg": "rollback-restore",
            "verb": "rollback",
            "to": snap["current_pub"],
            "budget_s": ROLLBACK_BUDGET_S,
        },
        {
            "leg": "withdraw-deny",
            "verb": "withdraw",
            "order": "deny",
            "budget_s": WITHDRAW_BUDGET_S,
        },
        {
            "leg": "withdraw-reinstate",
            "verb": "withdraw",
            "order": "allow",
            "budget_s": WITHDRAW_BUDGET_S,
        },
    ]
    return {"snapshot": snap, "legs": legs, "blockers": found}


# --------------------------------------------------------------------------- #
# run — the timed legs over the landed verbs                                  #
# ---------------------------------------------------------------------------#


def run(
    store: rp.Store,
    *,
    apply_: bool,
    deny_order: str | Path | None = None,
    allow_order: str | Path | None = None,
    go: str | None = None,
    authority: str | None = None,
    out: str | Path | None = None,
    now_fn: Any = None,
    monotonic: Any = None,
    environment: str = "fixture",
    api_image: str | None = None,
    web_image: str | None = None,
    min_instances: int = 1,
    project: str | None = None,
    region: str | None = None,
    execute_rolls: bool = False,
    gcloud: Any = None,
    origins: Sequence[str] | None = None,
    fetch: Any = None,
    break_lock: str | None = None,
) -> dict[str, Any]:
    """The rehearsal. ``apply_=False`` plans (nothing written, no lock);
    ``apply_=True`` executes the four timed legs over the landed verbs and
    emits the ``sig.release-rehearsal/1`` record — to ``out`` and appended
    under ``registry/rehearsals/``. Any blocker refuses (exit-42 shape:
    ``rehearsal-blocked``) before the first write; a leg refusal stops the
    run and the partial record — every applied leg named — is emitted
    first, never smoothed."""
    now_fn = now_fn or _now
    monotonic = monotonic or time.monotonic
    origins = list(origins or [])
    snap = resolve(store)
    found = blockers(store, go=go, authority=authority)
    record: dict[str, Any] = {
        "schema": REHEARSAL_SCHEMA,
        "ticket": "P36.70",
        "family": "R11-REL-11",
        "recorded_at": _iso(now_fn()),
        "store": store.describe(),
        "environment": environment,
        "status": "planned",
        "pre": {
            "conf_gen": snap["conf_gen"],
            "latest": snap["current_pub"],
            "rollback_target": snap["rollback_target"],
            "target_kind": snap["target_kind"],
        },
        "post": None,
        "legs": [],
        "orders": None,
        "authority": {"go": go, "withdraw_authority": authority},
        "blockers": found,
        "note": (
            "bounded + reversible by construction: rollback-to-prior is answered by "
            "rollback-restore (latest ends where it started); withdraw-deny is "
            "answered by a NEW allow disposition (the documented append-only "
            "reinstatement — the byte-level restore is the next release's "
            "staging); entity-kind low-stakes targets only, ≤ "
            f"{MAX_ORDER_ENTRIES}"
        ),
    }
    if not apply_:
        record["plan"] = plan(store, go=go, authority=authority)["legs"]
        _emit(record, out)
        return record
    if found:
        _emit(record, out)
        raise rp.PipelineError(
            "rehearsal-blocked",
            "the rehearsal leg stays QUEUED — " + "; ".join(found),
        )
    if deny_order is None or allow_order is None:
        raise rp.PipelineError(
            "orders-required",
            "--apply needs --deny-order <file> + --allow-order <file> — emit the pair "
            "with `sig-ops release-rehearsal orders`",
        )
    deny_entries, deny_meta = rr.load_order(deny_order)
    allow_entries, allow_meta = rr.load_order(allow_order)
    assert_bounded_orders(deny_entries, allow_entries)
    _assert_targets_staged(store, deny_entries, snap["current_pub"])
    record["orders"] = {"deny": deny_meta, "reinstate": allow_meta}

    legs = record["legs"]

    def _leg(name: str, budget_s: float, fn: Any) -> dict[str, Any]:
        started = now_fn()
        t0 = monotonic()
        try:
            result = fn(now=started)
        except rp.PipelineError as exc:
            seconds = monotonic() - t0
            legs.append(
                {
                    "leg": name,
                    "started_at": _iso(started),
                    "seconds": round(seconds, 3),
                    "budget_s": budget_s,
                    "within_budget": seconds <= budget_s,
                    "outcome": "refused",
                    "refusal": {"code": exc.code, "detail": str(exc)},
                }
            )
            raise
        seconds = monotonic() - t0
        row = {
            "leg": name,
            "started_at": _iso(started),
            "seconds": round(seconds, 3),
            "budget_s": budget_s,
            "within_budget": seconds <= budget_s,
            "outcome": "applied",
            "conf_gen": result.get("conf_gen"),
        }
        if result.get("receipt"):
            row["receipt"] = result["receipt"]
        if result.get("events"):
            row["events"] = result["events"]
        if result.get("probes") is not None:
            row["probes"] = len(result["probes"])
            row["probe_failures"] = result.get("probe_failures", 0)
        legs.append(row)
        return result

    def _roll(now: datetime, to: str, why: str) -> dict[str, Any]:
        return rr.verb_rollback(
            store,
            apply_=True,
            to=to,
            reason=f"{REHEARSAL_REASON} — {why}",
            go=go,
            api_image=api_image,
            web_image=web_image,
            min_instances=min_instances,
            project=project,
            region=region,
            execute_rolls=execute_rolls,
            gcloud=gcloud,
            origins=origins,
            break_lock=break_lock,
            now=now,
        )

    def _wd(now: datetime, order: str | Path) -> dict[str, Any]:
        return rr.verb_withdraw(
            store,
            apply_=True,
            disposition=order,
            authority=authority,
            api_image=api_image,
            web_image=web_image,
            min_instances=min_instances,
            project=project,
            region=region,
            execute_rolls=execute_rolls,
            gcloud=gcloud,
            origins=origins,
            fetch=fetch,
            break_lock=break_lock,
            now=now,
        )

    try:
        _leg(
            "rollback-to-prior",
            ROLLBACK_BUDGET_S,
            lambda now: _roll(
                now, snap["rollback_target"], "prior-pointer rehearsal (restore follows)"
            ),
        )
        _leg(
            "rollback-restore",
            ROLLBACK_BUDGET_S,
            lambda now: _roll(now, snap["current_pub"], "restore latest to the promoted release"),
        )
        _leg("withdraw-deny", WITHDRAW_BUDGET_S, lambda now: _wd(now, deny_order))
        _leg("withdraw-reinstate", WITHDRAW_BUDGET_S, lambda now: _wd(now, allow_order))
    except rp.PipelineError:
        record["status"] = "failed"
        record["object"] = _emit(record, out, store=store, now=now_fn())
        raise
    post = resolve(store)
    effective = _effective_dispositions(store)
    record["post"] = {
        "conf_gen": post["conf_gen"],
        "latest": post["current_pub"],
        "latest_restored": post["current_pub"] == snap["current_pub"],
        "rehearsal_dispositions": {
            tid: eff
            for tid, eff in effective.items()
            if tid in {e["target_id"] for e in deny_entries}
        },
        "byte_restore": (
            "next-release — the allow dispositions lift the deny going forward; "
            "the tombstoned bytes of this release's namespaces restore at the "
            "next cut (the append-only contract, §8.3)"
        ),
    }
    record["status"] = (
        "rehearsed" if post["current_pub"] == snap["current_pub"] else "failed-restore"
    )
    total = sum(leg["seconds"] for leg in legs)
    record["timings"] = {
        "legs_seconds": {leg["leg"]: leg["seconds"] for leg in legs},
        "total_seconds": round(total, 3),
        "budgets": {"rollback_s": ROLLBACK_BUDGET_S, "withdraw_s": WITHDRAW_BUDGET_S},
        "all_within_budget": all(leg["within_budget"] for leg in legs),
    }
    record["object"] = _emit(record, out, store=store, now=now_fn())
    return record


def _effective_dispositions(store: rp.Store) -> dict[str, str]:
    """target_id → the effective disposition over the withdrawal registry —
    the honest reinstatement read (latest row wins by decided_at + seq)."""
    body = store.read("registry/withdrawals.json")
    if body is None:
        return {}
    try:
        doc = json.loads(body)
    except ValueError:
        return {}
    out: dict[str, str] = {}
    for e in sorted(
        doc.get("entries") or [], key=lambda r: (r.get("decided_at") or "", r.get("seq") or 0)
    ):
        tid = str(e.get("target_id") or "")
        if tid:
            out[tid] = str(e.get("disposition") or "")
    return out


def _assert_targets_staged(
    store: rp.Store, entries: list[dict[str, Any]], current_pub: str | None
) -> None:
    """Each rehearsal target must be a staged entity record route under the
    current release — a target with no staged route would withdraw nothing
    measurable (the rehearsal measures a real deny, never a no-op)."""
    if not current_pub:
        return
    staged = {
        name
        for name in store.list(f"staged/r/{current_pub}/")
        if "/entity/" in name and name.endswith("/index.html")
    }
    for e in entries:
        tid = e["target_id"]
        if not any(f"/{tid}/index.html" in name for name in staged):
            raise rp.PipelineError(
                "target-unstaged",
                f"rehearsal target {tid!r} has no staged entity route under "
                f"staged/r/{current_pub}/ — pick a low-stakes record the "
                "promoted release actually serves",
            )


def _emit(
    record: dict[str, Any],
    out: str | Path | None,
    *,
    store: rp.Store | None = None,
    now: datetime | None = None,
) -> str | None:
    """Write the record: to ``out`` (always when given) and, on an applied
    run, appended under ``registry/rehearsals/`` — a new object, never an
    edit (the registry's own append-only posture)."""
    body = canonical_json(record)
    if out is not None:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
    if store is None:
        return None
    stamp = (now or _now()).strftime("%Y%m%dT%H%M%SZ")
    name = f"{REHEARSALS_PREFIX}rehearsal-{stamp}-{hashlib.sha256(body).hexdigest()[:12]}.json"
    store.insert(name, body, content_type="application/json")
    return name


# --------------------------------------------------------------------------- #
# CLI — sig-ops release-rehearsal {plan,orders,run}                          #
# ---------------------------------------------------------------------------#


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops release-rehearsal",
        description=(
            "P36.70 (REL-11): the second-release acceptance rehearsal — "
            "prior-pointer rollback + restore and a bounded low-stakes "
            "withdrawal + reinstate, each timed and recorded as "
            "sig.release-rehearsal/1. Class S under operator authority "
            "records (the standing go expires at GATE-G6 — the contract's "
            "own fallback); --apply refuses (exit 42) on any unmet "
            "precondition."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _registry_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--registry",
            default=None,
            help="the release registry — gs://<bucket>[/<prefix>] or a local "
            "dir (env SIG_RELEASE_REGISTRY; never defaulted)",
        )

    p_plan = sub.add_parser("plan", help="resolve the legs + blockers read-only")
    _registry_arg(p_plan)
    p_plan.add_argument("--go", default=None, help="the rollback go record name (optional check)")
    p_plan.add_argument("--authority", default=None, help="the withdraw authority record name")

    p_ord = sub.add_parser(
        "orders",
        help="emit the deterministic sig.withdrawal-order/1 deny+reinstate pair",
    )
    p_ord.add_argument(
        "--entity", action="append", required=True, help="a low-stakes entity id (repeatable, ≤ 4)"
    )
    p_ord.add_argument("--compartment", default=None, help="optional c/<compartment>/ scope")
    p_ord.add_argument("--reason-category", default=REASON_CATEGORY.value)
    p_ord.add_argument("--out", required=True, help="the dir the pair lands in")

    p_run = sub.add_parser("run", help="the timed legs — --apply performs, absent plans")
    _registry_arg(p_run)
    p_run.add_argument("--deny-order", default=None)
    p_run.add_argument("--allow-order", default=None)
    p_run.add_argument("--go", default=None, help="the operator's go record name (rollback legs)")
    p_run.add_argument(
        "--authority", default=None, help="the operator's takedown-authority record name"
    )
    p_run.add_argument(
        "--out",
        default=None,
        help="the record path (registry/rehearsals/ copy is automatic on --apply)",
    )
    p_run.add_argument("--apply", action="store_true")
    p_run.add_argument(
        "--execute-rolls",
        action="store_true",
        help="execute the api→web digest rolls (the sitting's posture)",
    )
    p_run.add_argument("--api-image", default=None)
    p_run.add_argument("--web-image", default=None)
    p_run.add_argument("--project", default=None)
    p_run.add_argument("--region", default=None)
    p_run.add_argument("--min-instances", type=int, default=1)
    p_run.add_argument(
        "--origin", action="append", default=[], help="a public origin to probe (repeatable)"
    )
    p_run.add_argument(
        "--environment",
        default="production",
        choices=["production", "staging", "fixture", "replay"],
    )
    p_run.add_argument("--break-lock", default=None, metavar="REASON")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "orders":
            deny, allow = rehearsal_orders(
                list(args.entity),
                compartment=args.compartment,
                reason_category=args.reason_category,
            )
            outdir = Path(args.out)
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "rehearsal-deny.json").write_bytes(canonical_json(deny))
            (outdir / "rehearsal-allow.json").write_bytes(canonical_json(allow))
            print(
                f"sig-ops release-rehearsal orders: wrote {outdir}/rehearsal-{{deny,allow}}.json "
                f"({len(deny['entries'])} low-stakes target(s))"
            )
            return 0
        registry = args.registry or os.environ.get("SIG_RELEASE_REGISTRY", "")
        store = rp.open_store(registry)
        if args.cmd == "plan":
            result = plan(store, go=args.go, authority=args.authority)
            snap = result["snapshot"]
            print(
                f"sig-ops release-rehearsal plan: gen={snap['conf_gen']} "
                f"latest={snap['current_pub']} rollback_target={snap['rollback_target']} "
                f"({snap['target_kind']})"
            )
            for leg in result["legs"]:
                print(f"  leg {leg['leg']}: {leg['verb']} (budget {leg['budget_s']:.0f}s)")
            for b in result["blockers"]:
                print(f"  QUEUED: {b}")
            return 42 if result["blockers"] else 0
        record = run(
            store,
            apply_=bool(args.apply),
            deny_order=args.deny_order,
            allow_order=args.allow_order,
            go=args.go,
            authority=args.authority,
            out=args.out,
            environment=args.environment,
            api_image=args.api_image,
            web_image=args.web_image,
            min_instances=args.min_instances,
            project=args.project,
            region=args.region,
            execute_rolls=args.execute_rolls,
            origins=args.origin,
            break_lock=args.break_lock,
        )
    except rp.PipelineError as exc:
        print(
            f"sig-ops release-rehearsal {args.cmd}: REFUSED [{exc.code}] — {exc}", file=sys.stderr
        )
        if exc.code == "rehearsal-blocked":
            return 42
        if exc.code in {"no-registry", "bad-registry"}:
            return 3
        return 4
    status = record["status"]
    if status == "planned":
        print("sig-ops release-rehearsal run: PLANNED (no write — pass --apply)")
        for leg in record.get("plan") or []:
            print(f"  leg {leg['leg']}: {leg['verb']} → {leg.get('to') or leg.get('order')}")
        return 0
    t = record["timings"]
    print(
        f"sig-ops release-rehearsal run: {status} — {len(record['legs'])} legs, "
        f"total {t['total_seconds']}s, all_within_budget={t['all_within_budget']}, "
        f"latest_restored={record['post']['latest_restored']}"
    )
    for leg in record["legs"]:
        print(
            f"  {leg['leg']}: {leg['seconds']}s (budget {leg['budget_s']:.0f}s) "
            f"{leg['outcome']} gen={leg.get('conf_gen')}"
        )
    if record.get("object"):
        print(f"  record: {record['object']}")
    return 0 if status == "rehearsed" else 4


__all__ = [
    "MAX_ORDER_ENTRIES",
    "ORDER_SCHEMA",
    "REHEARSALS_PREFIX",
    "REHEARSAL_REASON",
    "REHEARSAL_SCHEMA",
    "ROLLBACK_BUDGET_S",
    "WITHDRAW_BUDGET_S",
    "assert_bounded_orders",
    "blockers",
    "main",
    "plan",
    "rehearsal_orders",
    "resolve",
    "run",
]
