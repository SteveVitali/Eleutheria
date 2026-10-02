#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Single-writer closeout protocol — `closeout-op/1` (P32.8 / SIG-MEM-003, ADR-127).

Implements the shadow-mode writer protocol for implement-spec closeouts and
orchestrator repair paths, so interrupted closeout across worktrees resumes to
exactly one closeout — never a duplicated index row, a second PR, or invented
closure. ``LEDGER.md`` CURRENT STATE stays the control authority; this journal is
operational state only (host-local, not committed — it lives under the shared git
common directory so every worktree of one clone sees the same journal).

    closeout-op/1 state machine:  prepared → external-known → memory-committed → acknowledged

- ``prepare`` defines the operation id **before** any remote PR creation, from
  (schema, ticket_id, attempt, implementation commit, base commit). It acquires
  the scoped advisory lock, compares caller expected-state preconditions
  (``expected_next_ticket``, ``expected_last_completed``, ``expected_control_digest``,
  ``expected_chain_head``) against the **authoritative chain ref** (the main
  worktree's checkout — never merely the caller's stale files) and, only when they
  match, writes the operation record. A mismatch exits non-zero with the deltas
  named and writes nothing.
- ``external-known`` attaches the remote PR identity after creation; when the
  remote outcome was uncertain (network error, timeout) it reconciles by exact
  head/base first — an existing PR is adopted rather than a second one created.
- ``memory-committed`` validates the closeout git commit: it exists, descends
  from the expected chain head, its parent's control digest equals the recorded
  expected digest (compare-and-swap), it touches the memory files, and the
  validator passes. The validated commit is the memory transaction.
- ``acknowledge`` confirms the authoritative control state actually advanced
  (``lastCompleted`` = ticket, ``nextTicket`` moved on) — next dispatch is
  prohibited before acknowledgment.
- ``activation-check`` refuses cutover while any legacy-cell/event-chain
  divergence exists (legacy-only rows, event-only obligations, cell-vs-head
  disagreement). Shadow/available mode stays until the operator-approved
  entry-point cutover recorded on D-R10-MEMORY-1.

The scoped advisory lock is an ``mkdir`` (atomic) under
``<git-common-dir>/sig-closeout/locks/`` keyed to the stable build-chain id +
git common directory + repo-relative ledger path. **Single-host assumption:** PID
liveness is only meaningful on the lock's recorded host — a lock recorded on a
different host is never reclaimed here. A stale lock is surfaced with recovery
instructions (``--recover-stale``) and is never removed merely because time
elapsed; recovery also requires the recorded PID to be dead on this host.

Exit codes:
    0 ok · 1 state/validation failure · 2 stale expected-state or control-state
    divergence (re-sync and re-prepare) · 3 implementation/PR identity conflict
    (needs a new recorded ``--attempt`` + ``--reason``) · 4 lock contention /
    stale lock (recovery instructions printed) · 5 usage error ·
    6 activation-check BLOCKED.

Consume, don't fork: DEFERRALS/event-chain semantics come from
``obligation_events.py`` and ``audit_current_state.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOOLS = pathlib.Path(__file__).resolve().parent

LEDGER_REL = "docs/build/LEDGER.md"
INDEX_REL = "docs/build/BUILD_INDEX.md"
DEFERRALS_REL = "docs/tickets/DEFERRALS.md"
CONTROL_FILES = (LEDGER_REL, INDEX_REL, DEFERRALS_REL)
RUN_REL = "docs/build/runs/{}.md"
VALIDATOR_DEFAULT = (
    "bash scripts/docs/check-build-memory.sh . --json docs/build/logs/closeout-validator.json"
)

OP_SCHEMA = "closeout-op/1"
STATES = ("prepared", "external-known", "memory-committed", "acknowledged")
TERMINAL_LIKE = {"acknowledged", "aborted", "superseded"}

EXIT_OK = 0
EXIT_STATE = 1
EXIT_STALE = 2
EXIT_IDENTITY = 3
EXIT_LOCK = 4
EXIT_USAGE = 5
EXIT_BLOCKED = 6


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


obligation_events = _load("obligation_events")


# ── small helpers ─────────────────────────────────────────────────────────────


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _git(root: pathlib.Path, *args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return r.returncode, r.stdout.strip()


def common_dir(root: pathlib.Path) -> pathlib.Path:
    code, out = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if code != 0 or not out:
        raise SystemExit(f"{root}: cannot resolve --git-common-dir (not inside a git work tree?)")
    return pathlib.Path(out)


def state_dir(args) -> pathlib.Path:
    if getattr(args, "state_dir", None):
        return pathlib.Path(args.state_dir)
    return common_dir(pathlib.Path(args.root).resolve()) / "sig-closeout"


def ops_dir(sd: pathlib.Path) -> pathlib.Path:
    return sd / "operations"


def _load_op(sd: pathlib.Path, op_id: str) -> dict | None:
    p = ops_dir(sd) / f"{op_id}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def _all_ops(sd: pathlib.Path) -> list[dict]:
    out = []
    d = ops_dir(sd)
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                out.append(json.loads(p.read_text()))
            except json.JSONDecodeError:
                continue
    return out


def _save_op(sd: pathlib.Path, op: dict) -> None:
    d = ops_dir(sd)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{op['operation_id']}.json").write_text(json.dumps(op, indent=1) + "\n")


def operation_id(ticket: str, attempt: int, implementation: str, base: str) -> str:
    payload = json.dumps(
        {
            "schema": OP_SCHEMA,
            "ticket_id": ticket,
            "attempt": attempt,
            "implementation": implementation,
            "base": base,
        },
        sort_keys=True,
    )
    return "co-" + _sha256_text(payload)[:16]


def _now(args) -> str:
    return getattr(args, "at", None) or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _hist(op: dict, state: str, at: str, note: str) -> None:
    op["history"].append({"state": state, "at": at, "note": note})
    op["state"] = state
    op["updated_at"] = at


# ── authoritative state ───────────────────────────────────────────────────────


def _ledger_lval(root: pathlib.Path, key: str) -> str:
    p = root / LEDGER_REL
    if not p.is_file():
        return ""
    return obligation_events.audit_current_state._lval(p.read_text(), key)


def control_digest_at(root: pathlib.Path, rev: str | None) -> str:
    """sha256 over the control files (LEDGER + BUILD_INDEX + DEFERRALS). When
    ``rev`` is given the bytes come from that commit; otherwise the worktree."""
    digests = []
    for rel in CONTROL_FILES:
        if rev is None:
            p = root / rel
            data = p.read_bytes() if p.is_file() else b"<absent>"
        else:
            code, out = _git_bytes(root, "show", f"{rev}:{rel}")
            data = out if code == 0 else b"<absent>"
        digests.append(_sha256_bytes(data))
    return _sha256_text("|".join(digests))


def _git_bytes(root: pathlib.Path, *args: str) -> tuple[int, bytes]:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, b""
    return r.returncode, r.stdout


def chain_head(root: pathlib.Path) -> str:
    code, out = _git(root, "rev-parse", "HEAD")
    return out if code == 0 else ""


def authoritative_root(args, root: pathlib.Path) -> pathlib.Path:
    """The authoritative chain ref: the main worktree of the shared git common
    directory — the checkout all linked worktrees share object state with —
    unless the caller names a different authoritative checkout."""
    if getattr(args, "authoritative_root", None):
        return pathlib.Path(args.authoritative_root).resolve()
    common = common_dir(root)
    if common.name == ".git":
        return common.parent
    # .git/worktrees/<id> style common dirs: main worktree is common.parent
    return common.parent


def authoritative_state(auth_root: pathlib.Path) -> dict:
    return {
        "next_ticket": _ledger_lval(auth_root, "nextTicket"),
        "last_completed": _ledger_lval(auth_root, "lastCompleted"),
        "chain_tip": _ledger_lval(auth_root, "chainTip"),
        "control_digest": control_digest_at(auth_root, None),
        "chain_head": chain_head(auth_root),
    }


def worker_beliefs(root: pathlib.Path) -> dict:
    """What the caller's own (possibly stale) files claim — the default
    expected-state inputs when the caller doesn't pass explicit preconditions."""
    return {
        "next_ticket": _ledger_lval(root, "nextTicket"),
        "last_completed": _ledger_lval(root, "lastCompleted"),
        "control_digest": control_digest_at(root, None),
        "chain_head": chain_head(root),
    }


# ── scoped advisory lock ──────────────────────────────────────────────────────


def _scope_id(common: pathlib.Path, chain_id: str) -> str:
    return "lock-" + _sha256_text(f"{chain_id}|{common}|{LEDGER_REL}")[:16]


def _chain_id(root: pathlib.Path) -> str:
    """Stable build-chain id: the manifest path the ledger names (constant for
    the chain's life) — identical across worktrees of the same clone."""
    return _ledger_lval(root, "manifest") or "docs/tickets/00_MANIFEST.md"


def _lock_dir(sd: pathlib.Path, scope: str) -> pathlib.Path:
    return sd / "locks" / scope


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def lock_acquire(sd: pathlib.Path, scope: str, info: dict, recover_stale: bool) -> dict | None:
    """mkdir-atomic acquire. Returns the conflicting lock's info on refusal,
    or None on success. Never removes an existing lock on its own."""
    d = _lock_dir(sd, scope)
    d.parent.mkdir(parents=True, exist_ok=True)
    try:
        d.mkdir()
    except FileExistsError:
        held = {}
        try:
            held = json.loads((d / "info.json").read_text())
        except (OSError, json.JSONDecodeError):
            held = {"corrupt": True}
        if not recover_stale:
            return held
        # Recovery: same recorded host AND recorded pid dead. A PID on another
        # host proves nothing here — refuse and say how to recover there.
        host = held.get("host", "")
        pid = int(held.get("pid") or 0)
        if host != socket.gethostname():
            held["refusal"] = (
                f"lock was recorded on host {host!r}; PID liveness is only "
                "meaningful there — recover on that host or remove "
                f"{d} manually after confirming the holder is dead"
            )
            return held
        if _pid_alive(pid):
            held["refusal"] = f"recorded holder pid {pid} is alive on this host"
            return held
        # stale on this host: record the recovery event, then reclaim.
        rec = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scope": scope,
            "recovered_by_pid": os.getpid(),
            "stale_info": held,
        }
        with (sd / "recoveries.jsonl").open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        import shutil

        shutil.rmtree(d)
        d.mkdir()
    (d / "info.json").write_text(json.dumps(info, indent=1) + "\n")
    return None


def lock_release(sd: pathlib.Path, scope: str) -> tuple[bool, str]:
    d = _lock_dir(sd, scope)
    if not d.is_dir():
        return True, "no lock held"
    try:
        held = json.loads((d / "info.json").read_text())
    except (OSError, json.JSONDecodeError):
        return False, f"lock {d} is corrupt — inspect manually"
    pid = int(held.get("pid") or 0)
    if pid != os.getpid():
        if _pid_alive(pid):
            return False, f"lock held by live pid {pid} on host {held.get('host')!r}"
        return (
            False,
            f"lock recorded a dead pid {pid} on host {held.get('host')!r} — "
            "reclaim it with --recover-stale (recovery is recorded, never silent)",
        )
    import shutil

    shutil.rmtree(d)
    return True, "released"


# ── remote PR lookup (ambiguous creation reconciliation) ─────────────────────


def lookup_pr(args, head: str, base: str) -> list[dict] | None:
    """Find remote PRs by exact head/base. In tests, ``--lookup-json`` supplies
    the candidate list so no network/gh is needed; otherwise `gh pr list`.
    Returns ``None`` when the lookup itself failed — an inconclusive lookup must
    NEVER read as "no PR exists": treating a failed lookup as absent is exactly
    how a retried create mints a duplicate PR."""
    if getattr(args, "lookup_json", None):
        try:
            data = json.loads(pathlib.Path(args.lookup_json).read_text())
        except (OSError, json.JSONDecodeError):
            return None
        rows = data if isinstance(data, list) else data.get("prs", [])
    else:
        try:
            r = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    head,
                    "--base",
                    base,
                    "--state",
                    "all",
                    "--json",
                    "number,url,headRefName,baseRefName",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if r.returncode != 0:
            return None
        try:
            rows = json.loads(r.stdout) if r.stdout.strip() else []
        except json.JSONDecodeError:
            return None
    return [
        p
        for p in rows
        if p.get("headRefName", p.get("head", "")) == head
        and p.get("baseRefName", p.get("base", "")) == base
    ]


# ── subcommands ───────────────────────────────────────────────────────────────


def cmd_prepare(args) -> int:
    root = pathlib.Path(args.root).resolve()
    sd = state_dir(args)
    scope = _scope_id(common_dir(root), _chain_id(root))
    ticket = args.ticket
    attempt = int(args.attempt)
    op_id = operation_id(ticket, attempt, args.implementation, args.base)

    held = lock_acquire(
        sd,
        scope,
        {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "worktree": str(root),
            "operation_id": op_id,
            "acquired_at": _now(args),
            "note": "closeout prepare critical section",
        },
        recover_stale=args.recover_stale,
    )
    if held is not None:
        print(f"prepare: lock {scope} is held — {json.dumps(held)}", file=sys.stderr)
        print(
            "prepare: a stale lock is recovered ONLY with --recover-stale after the "
            "holder is confirmed dead on the recorded host (never on timeout).",
            file=sys.stderr,
        )
        return EXIT_LOCK
    try:
        return _prepare_under_lock(args, root, sd, ticket, attempt, op_id, scope)
    finally:
        ok, why = lock_release(sd, scope)
        if not ok:
            print(f"prepare: could not release lock: {why}", file=sys.stderr)


def _prepare_under_lock(args, root, sd, ticket, attempt, op_id, scope) -> int:
    ops = _all_ops(sd)
    existing = _load_op(sd, op_id)
    if existing is not None:
        # Same identity → idempotent resume (crash before/after any later step).
        print(
            f"prepare: operation {op_id} already recorded "
            f"(state={existing['state']}) — idempotent resume, no re-preparation"
        )
        print(json.dumps(existing, indent=1))
        return EXIT_OK

    ticket_ops = [o for o in ops if o.get("ticket_id") == ticket]
    acknowledged = [o for o in ticket_ops if o.get("state") == "acknowledged"]
    in_flight = [o for o in ticket_ops if o.get("state") not in TERMINAL_LIKE]
    max_attempt = max([o.get("attempt", 1) for o in ticket_ops], default=0)
    is_new_attempt = attempt > max_attempt
    if (acknowledged or in_flight) and not is_new_attempt:
        kind = "acknowledged" if acknowledged else "in-flight"
        ids = [o["operation_id"] for o in (acknowledged or in_flight)]
        print(
            f"prepare: ticket {ticket} already has a {kind} operation {ids} with a "
            "DIFFERENT implementation/attempt identity — refused. A second identity "
            "is accepted only as a new recorded attempt: pass --attempt "
            f"{max_attempt + 1} --reason '<why the earlier attempt is superseded>'.",
            file=sys.stderr,
        )
        return EXIT_IDENTITY
    if (acknowledged or in_flight) and is_new_attempt and not args.reason:
        print(
            f"prepare: --attempt {attempt} supersedes an existing {ticket} "
            "operation — a new recorded attempt must carry --reason.",
            file=sys.stderr,
        )
        return EXIT_IDENTITY
    # Next dispatch is prohibited before acknowledgment: another ticket's
    # unacknowledged operation blocks this prepare.
    others = [
        o for o in ops if o.get("ticket_id") != ticket and o.get("state") not in TERMINAL_LIKE
    ]
    if others:
        print(
            "prepare: an earlier closeout operation is still unacknowledged — "
            + ", ".join(f"{o['ticket_id']}:{o['state']}" for o in others)
            + ". Finish or abort it before dispatching the next closeout.",
            file=sys.stderr,
        )
        return EXIT_STATE

    # Expected-state preconditions: caller belief vs the authoritative chain ref.
    auth_root = authoritative_root(args, root)
    auth = authoritative_state(auth_root)
    belief = worker_beliefs(root)
    expected = {
        "next_ticket": args.expected_next_ticket or belief["next_ticket"],
        "last_completed": args.expected_last_completed or belief["last_completed"],
        "control_digest": args.expected_control_digest or belief["control_digest"],
        "chain_head": args.expected_chain_head or belief["chain_head"],
    }
    deltas = {}
    if expected["next_ticket"] and expected["next_ticket"] != auth["next_ticket"]:
        deltas["next_ticket"] = (expected["next_ticket"], auth["next_ticket"])
    if expected["last_completed"] and expected["last_completed"] != auth["last_completed"]:
        deltas["last_completed"] = (expected["last_completed"], auth["last_completed"])
    if expected["control_digest"] and expected["control_digest"] != auth["control_digest"]:
        deltas["control_digest"] = (expected["control_digest"], auth["control_digest"])
    if expected["chain_head"] and expected["chain_head"] != auth["chain_head"]:
        deltas["chain_head"] = (expected["chain_head"], auth["chain_head"])
    if deltas:
        print(
            "prepare: STALE expected-state — caller belief != authoritative chain "
            f"ref ({auth_root}); nothing written:",
            file=sys.stderr,
        )
        for k, (exp, act) in deltas.items():
            print(f"  {k}: expected {exp!r}, authoritative {act!r}", file=sys.stderr)
        print(
            "prepare: re-sync the worktree to the authoritative chain head and "
            "re-prepare. Stale expected-state fails WITHOUT partial advancement.",
            file=sys.stderr,
        )
        return EXIT_STALE

    # A recorded new attempt supersedes in-flight predecessors for the ticket —
    # close them so they cannot block later dispatch, with the supersession
    # explained in their history (never silently dropped).
    if is_new_attempt:
        for o in in_flight:
            o["history"].append(
                {
                    "state": "superseded",
                    "at": _now(args),
                    "note": f"superseded by attempt {attempt} ({op_id}): {args.reason}",
                }
            )
            o["state"] = "superseded"
            _save_op(sd, o)

    code, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    op = {
        "schema": OP_SCHEMA,
        "operation_id": op_id,
        "ticket_id": ticket,
        "attempt": attempt,
        "implementation": args.implementation,
        "base": args.base,
        "branch": args.branch or (branch if code == 0 else ""),
        "state": "prepared",
        "expected": expected,
        "authoritative": {"root": str(auth_root), "next_ticket": auth["next_ticket"]},
        "pr": None,
        "memory_commit": None,
        "lock_scope": scope,
        "reason": args.reason or "",
        "created_at": _now(args),
        "updated_at": _now(args),
        "history": [
            {
                "state": "prepared",
                "at": _now(args),
                "note": f"operation id defined pre-PR from ticket={ticket} "
                f"attempt={attempt} implementation={args.implementation[:12]} "
                f"base={args.base[:12]}",
            }
        ],
    }
    _save_op(sd, op)
    print(f"prepare: recorded operation {op_id} (state=prepared)")
    print(json.dumps(op, indent=1))
    return EXIT_OK


def cmd_external_known(args) -> int:
    root = pathlib.Path(args.root).resolve()
    sd = state_dir(args)
    op = _load_op(sd, args.operation)
    if op is None:
        print(f"external-known: no operation {args.operation}", file=sys.stderr)
        return EXIT_STATE
    if op["state"] == "acknowledged":
        print(f"external-known: {args.operation} already acknowledged — no-op")
        return EXIT_OK
    if op["state"] == "memory-committed":
        if args.pr is not None and op["pr"] and op["pr"].get("number") == args.pr:
            print("external-known: same PR identity already attached — no-op")
            return EXIT_OK
        print(
            "external-known: memory already committed; changing the PR identity "
            "now would be a second remote identity — refused",
            file=sys.stderr,
        )
        return EXIT_IDENTITY
    if op["state"] not in ("prepared", "external-known"):
        print(
            f"external-known: operation is {op['state']} — expected prepared",
            file=sys.stderr,
        )
        return EXIT_STATE
    if args.uncertain:
        head = args.head or op.get("branch", "")
        base = args.base_branch or _ledger_lval(root, "buildBranchBase") or ""
        candidates = lookup_pr(args, head, base)
        if candidates is None:
            print(
                "external-known: the remote PR lookup itself FAILED (gh error/"
                "network) — reconciliation is inconclusive, NOT 'no PR exists'. "
                "Retry the reconcile when the lookup works; do not create "
                "another PR blind.",
                file=sys.stderr,
            )
            return EXIT_STATE
        if not candidates:
            print(
                f"external-known: reconciliation found NO remote PR for "
                f"head={head!r} base={base!r} — creation genuinely failed; safe "
                "to (re)create. The operation id prevents duplicate bookkeeping "
                "on resume."
            )
            return EXIT_OK
        pr = candidates[0]
        if op["pr"] and op["pr"].get("number") != pr.get("number"):
            print(
                f"external-known: recorded PR #{op['pr'].get('number')} but "
                f"reconciliation found #{pr.get('number')} — conflicting remote "
                "identity; reconcile manually before retry",
                file=sys.stderr,
            )
            return EXIT_IDENTITY
        if op["state"] == "external-known":
            print("external-known: same reconciled PR already attached — no-op")
            return EXIT_OK
        op["pr"] = {
            "number": pr.get("number"),
            "url": pr.get("url", ""),
            "head": head,
            "base": base,
            "reconciled": True,
        }
        _hist(op, "external-known", _now(args), "uncertain creation reconciled by exact head/base")
        _save_op(sd, op)
        print(
            f"external-known: reconciled — PR #{pr.get('number')} already exists "
            f"for {head}→{base}; adopted instead of a duplicate create"
        )
        return EXIT_OK
    if args.pr is None:
        print("external-known: pass --pr N or --uncertain", file=sys.stderr)
        return EXIT_USAGE
    if op["pr"] and op["pr"].get("number") == args.pr:
        print("external-known: same PR identity already attached — no-op")
        return EXIT_OK
    if op["pr"] and op["pr"].get("number") != args.pr:
        print(
            f"external-known: operation already carries PR #{op['pr'].get('number')} "
            f"≠ {args.pr} — two remote identities for one operation is the "
            "duplicate-PR failure mode; refused",
            file=sys.stderr,
        )
        return EXIT_IDENTITY
    op["pr"] = {
        "number": args.pr,
        "url": args.url or "",
        "head": args.head or op.get("branch", ""),
        "base": args.base_branch or "",
        "reconciled": False,
    }
    _hist(op, "external-known", _now(args), f"remote PR identity attached: #{args.pr}")
    _save_op(sd, op)
    print(f"external-known: {args.operation} → PR #{args.pr}")
    return EXIT_OK


def cmd_memory_committed(args) -> int:
    root = pathlib.Path(args.root).resolve()
    sd = state_dir(args)
    op = _load_op(sd, args.operation)
    if op is None:
        print(f"memory-committed: no operation {args.operation}", file=sys.stderr)
        return EXIT_STATE
    if op["state"] == "acknowledged":
        print(f"memory-committed: {args.operation} already acknowledged — no-op")
        return EXIT_OK
    if op["state"] == "memory-committed":
        if op["memory_commit"] == args.commit:
            print("memory-committed: same commit already recorded — no-op")
            return EXIT_OK
        print(
            f"memory-committed: a DIFFERENT memory commit {args.commit} vs recorded "
            f"{op['memory_commit']} — one memory transition per operation; refused",
            file=sys.stderr,
        )
        return EXIT_IDENTITY
    if op["state"] != "external-known":
        print(
            f"memory-committed: operation is {op['state']} — the protocol order is "
            "prepared → external-known → memory-committed",
            file=sys.stderr,
        )
        return EXIT_STATE
    commit = args.commit
    code, _ = _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    if code != 0:
        print(f"memory-committed: commit {commit} does not exist", file=sys.stderr)
        return EXIT_STATE
    expected = op["expected"]
    eh = expected.get("chain_head")
    if eh:
        code, _ = _git(root, "merge-base", "--is-ancestor", eh, commit)
        if code != 0:
            print(
                f"memory-committed: {commit} does not descend from the expected "
                f"chain head {eh} — the memory transition must apply ONTO the "
                "expected base, never beside it",
                file=sys.stderr,
            )
            return EXIT_STALE
    # Compare-and-swap: the commit's parent control files must equal what
    # prepare recorded — proof the transition applied onto the expected state.
    _, parent = _git(root, "rev-parse", f"{commit}^")
    parent_digest = control_digest_at(root, parent)
    if expected.get("control_digest") and parent_digest != expected["control_digest"]:
        print(
            "memory-committed: CONTROL-STATE CAS FAILED — the commit's parent "
            "digest does not match the recorded expected control digest "
            f"({parent_digest[:16]} != {expected['control_digest'][:16]}). "
            "Another writer moved the control files under this operation; "
            "re-sync and re-prepare. No partial advancement is recorded.",
            file=sys.stderr,
        )
        return EXIT_STALE
    _, touched = _git(root, "show", "--format=", "--name-only", commit)
    touched_set = set(touched.splitlines())
    required = {LEDGER_REL, INDEX_REL}
    missing = required - touched_set
    if missing:
        print(
            f"memory-committed: {commit} does not touch {sorted(missing)} — a "
            "closeout memory transaction must carry the control-state diff in "
            "the validated commit, not uncommitted files",
            file=sys.stderr,
        )
        return EXIT_STATE
    if not args.no_validator:
        validator = args.validator or VALIDATOR_DEFAULT
        rc = subprocess.run(validator, shell=True, cwd=root).returncode
        if rc != 0:
            print(
                f"memory-committed: validator {validator!r} exited {rc} — the "
                "memory transaction is a VALIDATED git commit; unvalidated "
                "state is not recorded",
                file=sys.stderr,
            )
            return EXIT_STATE
    op["memory_commit"] = commit
    op["memory_files"] = sorted(
        touched_set & set(CONTROL_FILES + (RUN_REL.format(op["ticket_id"]),))
    )
    _hist(op, "memory-committed", _now(args), f"validated memory transaction {commit[:12]}")
    _save_op(sd, op)
    print(f"memory-committed: {args.operation} → {commit[:12]}")
    return EXIT_OK


def cmd_acknowledge(args) -> int:
    root = pathlib.Path(args.root).resolve()
    sd = state_dir(args)
    op = _load_op(sd, args.operation)
    if op is None:
        print(f"acknowledge: no operation {args.operation}", file=sys.stderr)
        return EXIT_STATE
    if op["state"] == "acknowledged":
        print(f"acknowledge: {args.operation} already acknowledged — no-op")
        return EXIT_OK
    if op["state"] != "memory-committed":
        print(
            f"acknowledge: operation is {op['state']} — only memory-committed "
            "operations may be acknowledged",
            file=sys.stderr,
        )
        return EXIT_STATE
    auth_root = authoritative_root(args, root)
    auth = authoritative_state(auth_root)
    ticket = op["ticket_id"]
    if auth["last_completed"] != ticket:
        if (
            auth["last_completed"] == op["expected"]["last_completed"]
            and op["expected"]["last_completed"] != ticket
        ):
            print(
                f"acknowledge: authoritative lastCompleted is still "
                f"{auth['last_completed']!r} — the memory commit has not taken "
                "effect on the authoritative chain ref; refusing to acknowledge",
                file=sys.stderr,
            )
            return EXIT_STALE
        print(
            f"acknowledge: authoritative lastCompleted is "
            f"{auth['last_completed']!r}, not {ticket} — the chain moved past or "
            "sideways; reconcile before dispatch",
            file=sys.stderr,
        )
        return EXIT_STALE
    if auth["next_ticket"] == ticket:
        print(
            f"acknowledge: lastCompleted advanced but nextTicket still names "
            f"{ticket} — the control advance is incomplete",
            file=sys.stderr,
        )
        return EXIT_STATE
    _hist(
        op,
        "acknowledged",
        _now(args),
        f"authoritative lastCompleted={ticket}, nextTicket={auth['next_ticket']} "
        "— dispatch of the next closeout is now permitted",
    )
    _save_op(sd, op)
    print(f"acknowledge: {args.operation} acknowledged — next dispatch permitted")
    return EXIT_OK


def cmd_abort(args) -> int:
    sd = state_dir(args)
    op = _load_op(sd, args.operation)
    if op is None:
        print(f"abort: no operation {args.operation}", file=sys.stderr)
        return EXIT_STATE
    if op["state"] == "acknowledged":
        print("abort: an acknowledged closeout cannot be aborted", file=sys.stderr)
        return EXIT_STATE
    _hist(op, "aborted", _now(args), args.reason or "operator/worker abort")
    _save_op(sd, op)
    print(f"abort: {args.operation} recorded aborted")
    return EXIT_OK


def cmd_status(args) -> int:
    sd = state_dir(args)
    ops = _all_ops(sd)
    if args.operation:
        ops = [o for o in ops if o.get("operation_id") == args.operation]
    if args.ticket:
        ops = [o for o in ops if o.get("ticket_id") == args.ticket]
    if not ops:
        print("status: no closeout operations recorded")
        return EXIT_OK
    for o in ops:
        print(
            f"{o['operation_id']}  {o['ticket_id']}  attempt={o.get('attempt')} "
            f"state={o['state']}  impl={o.get('implementation', '')[:12]} "
            f"pr={o.get('pr') and o['pr'].get('number')} "
            f"mem={o.get('memory_commit') and o['memory_commit'][:12]}"
        )
    return EXIT_OK


def cmd_lock(args) -> int:
    root = pathlib.Path(args.root).resolve()
    sd = state_dir(args)
    scope = _scope_id(common_dir(root), _chain_id(root))
    d = _lock_dir(sd, scope)
    if args.lock_cmd == "inspect":
        if not d.is_dir():
            print(f"lock: no lock at {d}")
            return EXIT_OK
        print((d / "info.json").read_text() if (d / "info.json").is_file() else "<corrupt>")
        return EXIT_OK
    if args.lock_cmd == "release":
        ok, why = lock_release(sd, scope)
        print(f"lock release: {why}")
        return EXIT_OK if ok else EXIT_LOCK
    # acquire
    held = lock_acquire(
        sd,
        scope,
        {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "worktree": str(root),
            "operation_id": args.operation or None,
            "acquired_at": _now(args),
            "note": args.note or "manual lock",
        },
        recover_stale=args.recover_stale,
    )
    if held is not None:
        print(f"lock acquire: refused — held/corrupt: {json.dumps(held)}", file=sys.stderr)
        if held.get("refusal"):
            print(f"lock acquire: {held['refusal']}", file=sys.stderr)
        return EXIT_LOCK
    print(f"lock acquire: {scope} held by pid {os.getpid()}")
    return EXIT_OK


def cmd_activation_check(args) -> int:
    root = pathlib.Path(args.root).resolve()
    diags: list[dict] = []
    events, errs = obligation_events.load_jsonl(root / obligation_events.EVENTS_PATH)
    for e in errs:
        diags.append(
            obligation_events.diag(
                "events/malformed", "error", obligation_events.EVENTS_PATH, "—", "jsonl", e
            )
        )
    assessments, aerrs = obligation_events.load_jsonl(root / obligation_events.ASSESSMENTS_PATH)
    for e in aerrs:
        diags.append(
            obligation_events.diag(
                "coverage/malformed", "error", obligation_events.ASSESSMENTS_PATH, "—", "jsonl", e
            )
        )
    # assessments are loaded so corrections naming the coverage ledger resolve
    diags += obligation_events.check_event_chain(root, events, assessments)
    diags += obligation_events.check_assessments(root, assessments)
    errors = [d for d in diags if d["severity"] == "error"]
    if errors:
        print("activation-check: BLOCKED — legacy-only/event-only divergence:")
        for d in errors:
            print(f"  {d['check']:34} {d['obligation']:20} {d['message']}")
        print(
            "activation-check: reconcile every divergence before the entry-point "
            "cutover; shadow/available mode continues meanwhile (D-R10-MEMORY-1)."
        )
        return EXIT_BLOCKED
    print(
        f"activation-check: READY — {len(events)} events, every DEFERRALS row has "
        "exactly one anchor, every event head agrees with its compatibility cell, "
        "no legacy-only/event-only divergence."
    )
    print(
        "activation-check: still SHADOW mode — enforcement begins only at the "
        "operator-approved ticket-boundary cutover recorded on D-R10-MEMORY-1."
    )
    return EXIT_OK


# ── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[4])
    ap.add_argument("--root", default=str(ROOT), help="the worktree running this command")
    ap.add_argument(
        "--state-dir",
        default=None,
        help="override the journal/lock dir (default <git-common-dir>/sig-closeout)",
    )
    ap.add_argument("--at", default=None, help="fixed timestamp for recorded events")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("prepare", help="define the op id + check expected-state preconditions")
    p.add_argument("--ticket", required=True)
    p.add_argument("--implementation", required=True, help="implementation commit sha")
    p.add_argument("--base", required=True, help="base commit sha the ticket forked from")
    p.add_argument("--branch", default=None)
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--reason", default=None, help="required when --attempt > prior attempts")
    p.add_argument("--expected-next-ticket", default=None)
    p.add_argument("--expected-last-completed", default=None)
    p.add_argument("--expected-control-digest", default=None)
    p.add_argument("--expected-chain-head", default=None)
    p.add_argument("--authoritative-root", default=None)
    p.add_argument(
        "--recover-stale",
        action="store_true",
        help="reclaim a stale lock whose recorded pid is dead on THIS host",
    )

    p = sub.add_parser("external-known", help="attach/reconcile the remote PR identity")
    p.add_argument("--operation", required=True)
    p.add_argument("--pr", type=int, default=None)
    p.add_argument("--url", default=None)
    p.add_argument("--head", default=None)
    p.add_argument("--base-branch", default=None)
    p.add_argument(
        "--uncertain", action="store_true", help="reconcile an ambiguous create by exact head/base"
    )
    p.add_argument(
        "--lookup-json", default=None, help="test seam: candidate PR list instead of `gh pr list`"
    )

    p = sub.add_parser("memory-committed", help="validate + record the memory commit")
    p.add_argument("--operation", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--validator", default=None, help=f"default: {VALIDATOR_DEFAULT!r}")
    p.add_argument("--no-validator", action="store_true")

    p = sub.add_parser(
        "acknowledge", help="confirm the authoritative advance; permit next dispatch"
    )
    p.add_argument("--operation", required=True)
    p.add_argument("--authoritative-root", default=None)

    p = sub.add_parser("abort", help="record an aborted operation")
    p.add_argument("--operation", required=True)
    p.add_argument("--reason", default=None)

    p = sub.add_parser("status", help="list recorded operations")
    p.add_argument("--operation", default=None)
    p.add_argument("--ticket", default=None)

    p = sub.add_parser("lock", help="manual lock ops (inspect/acquire/release)")
    p.add_argument("lock_cmd", choices=["acquire", "release", "inspect"])
    p.add_argument("--operation", default=None)
    p.add_argument("--note", default=None)
    p.add_argument("--recover-stale", action="store_true")

    p = sub.add_parser("activation-check", help="legacy/event divergence gate for cutover")

    args = ap.parse_args(argv)
    if args.cmd == "prepare":
        return cmd_prepare(args)
    if args.cmd == "external-known":
        return cmd_external_known(args)
    if args.cmd == "memory-committed":
        return cmd_memory_committed(args)
    if args.cmd == "acknowledge":
        return cmd_acknowledge(args)
    if args.cmd == "abort":
        return cmd_abort(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "lock":
        return cmd_lock(args)
    if args.cmd == "activation-check":
        return cmd_activation_check(args)
    ap.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
