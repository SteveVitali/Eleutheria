#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Failure-injection fixtures for ``docs/build/tools/closeout_protocol.py``
(P32.8, SIG-MEM-003).

The single-writer closeout protocol must resume an interrupted closeout to
exactly one closeout at every boundary — code / PR / run-ledger / index /
deferral / ledger — reject a different implementation identity on an
already-closed ticket (unless a new recorded attempt explains it), refuse stale
expected-state without partial advancement, compare racing worktrees against one
authoritative chain head, reconcile ambiguous remote PR creation before retry,
and block activation on legacy-only/event-only divergence. Every fixture uses a
real git object store and real commits: a test that could not actually fail
would be a defect, not evidence.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess

from support import REPO_ROOT

TOOLS = REPO_ROOT / "docs" / "build" / "tools"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


closeout = _load_tool("closeout_protocol")
obligation_events = _load_tool("obligation_events")

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "sig-test",
    "GIT_AUTHOR_EMAIL": "sig-test@example.invalid",
    "GIT_COMMITTER_NAME": "sig-test",
    "GIT_COMMITTER_EMAIL": "sig-test@example.invalid",
}


def _git(root: pathlib.Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=GIT_ENV,
    )
    return r.stdout.strip()


def _lstate(next_ticket: str, last_completed: str) -> str:
    return (
        "# ledger\n\n## CURRENT STATE\n\n```\n"
        "projectStatus: IN_PROGRESS\n"
        f"nextTicket: {next_ticket}\n"
        f"lastCompleted: {last_completed}\n"
        "blockedOn: —\npauseRequested: false\nreturnPass: none\n"
        "manifest: docs/tickets/00_MANIFEST.md\n"
        "canonicalSpec: docs/2_canonical_design_spec.md\n"
        "memoryRoot: docs/build\ndispatchTarget: subagent\n"
        "buildWorktree: .\nbuildBranchBase: devin/base\npinnedBaseSha: deadbeef\n"
        "chainTip: devin/base\nbenchmarkSet: N/A\nautonomy: checkpoint\n"
        "mergePolicy: NONE\nround: 10\nupdatedAt: 2026-10-15\n```\n"
    )


def _lstate_r11(next_ticket: str, last_completed: str) -> str:
    """The Round-11 seed shape (B3 §3.4; layout BM-LEDGER-02/-08): values only,
    `harness` in its slot between `round` and `updatedAt`, an archive pointer
    comment inside the section, a PHASE LOG region per round."""
    return (
        "# ledger\n\n## CURRENT STATE\n\n```\n"
        "projectStatus: IN_PROGRESS\n"
        f"nextTicket: {next_ticket}\n"
        f"lastCompleted: {last_completed}\n"
        "blockedOn: (nothing)\npauseRequested: false\nreturnPass: (none)\n"
        "manifest: docs/tickets/00_MANIFEST.md\n"
        "canonicalSpec: docs/2_canonical_design_spec.md\n"
        "memoryRoot: docs/build\ndispatchTarget: subagent\n"
        "buildWorktree: .\nbuildBranchBase: devin/base\npinnedBaseSha: deadbeef\n"
        "chainTip: devin/base\nbenchmarkSet: N/A\nautonomy: checkpoint\n"
        "mergePolicy: NONE\nround: 11\nharness: devin-desktop/swe-2-high/subagent\n"
        "updatedAt: 2026-10-15T00:00:00Z\n```\n"
        "<!-- Rounds 1-10 head archived; sha256 pointer. -->\n\n"
        "## PHASE LOG — Round 11\n\n- 2026-10-15 — SEED-10 repair — head archived\n"
    )


MANIFEST = (
    "# manifest\n\ncompanions: _TEMPLATE.md\n\n## The chain\n\n"
    "| # | Ticket file | Phase |\n|---|---|---|\n"
    "| 1 | `167_P9.1__a.md` | 9 |\n"
    "| 2 | `168_P9.2__b.md` | 9 |\n"
    "| 3 | `169_P9.3__c.md` | 9 |\n"
)

DEFERRALS = (
    "# deferrals\n\n"
    "| id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |\n"
    "|---|---|---|---|---|---|---|---|\n"
    "| D-T9.1-1 | V | item | deferred | unblock | verify | proxy | OPEN cites BL-001 |\n"
)

BASE_FILES = {
    "docs/tickets/00_MANIFEST.md": MANIFEST,
    "docs/tickets/DEFERRALS.md": DEFERRALS,
    "docs/tickets/167_P9.1__a.md": "# ticket\n",
    "docs/tickets/168_P9.2__b.md": "# ticket\n",
    "docs/tickets/169_P9.3__c.md": "# ticket\n",
    "docs/build/README.md": "# build\n\n<!-- build-memory: v2 -->\n",
    "docs/build/BUILD_INDEX.md": "# index\n\n| seq | ticket |\n|---|---|\n",
    "docs/2_canonical_design_spec.md": "# spec\n",
}


def _write(root: pathlib.Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _repo(tmp: pathlib.Path, name: str = "auth", lstate=_lstate) -> pathlib.Path:
    """A real git repo seeded with a minimal build-memory tree; one initial
    commit where LEDGER says lastCompleted=P9.1 / nextTicket=P9.2."""
    root = tmp / name
    root.mkdir(parents=True)
    for rel, text in BASE_FILES.items():
        _write(root, rel, text)
    _write(root, "docs/build/LEDGER.md", lstate("P9.2", "P9.1"))
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")
    return root


def _impl_commit(root: pathlib.Path) -> str:
    _write(root, "docs/build/tools/impl.txt", "implementation\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "impl")
    return _git(root, "rev-parse", "HEAD")


def _closeout_commit(root: pathlib.Path, done: str, nxt: str, lstate=_lstate) -> str:
    """The memory transaction: LEDGER advance + BUILD_INDEX row + run ledger."""
    _write(root, "docs/build/LEDGER.md", lstate(nxt, done))
    idx = root / "docs/build/BUILD_INDEX.md"
    idx.write_text(idx.read_text() + f"| 168 | {done} |\n")
    _write(root, f"docs/build/runs/{done}.md", "# run\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", f"close {done}")
    return _git(root, "rev-parse", "HEAD")


def _run(root: pathlib.Path, argv: list[str], state_dir: pathlib.Path | None = None) -> int:
    args = ["--root", str(root)]
    if state_dir is not None:
        args += ["--state-dir", str(state_dir)]
    return closeout.main(args + argv)


def _op(sd: pathlib.Path, op_id: str) -> dict:
    return json.loads((sd / "operations" / f"{op_id}.json").read_text())


def _prepare(root, sd, ticket="P9.2", impl="i" * 40, base="b" * 40, extra=None):
    argv = [
        "prepare",
        "--ticket",
        ticket,
        "--implementation",
        impl,
        "--base",
        base,
    ] + (extra or [])
    return _run(root, argv, sd)


def _full_closeout(root, sd, ticket="P9.2", impl=None, pr=42, nxt="P9.3", lstate=_lstate) -> str:
    """Drive one complete closeout; returns the operation id."""
    impl = impl or _impl_commit(root)
    assert _prepare(root, sd, ticket=ticket, impl=impl) == 0
    op_id = closeout.operation_id(ticket, 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", str(pr)], sd) == 0
    commit = _closeout_commit(root, ticket, nxt, lstate)
    assert (
        _run(
            root,
            ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
            sd,
        )
        == 0
    )
    assert _run(root, ["acknowledge", "--operation", op_id], sd) == 0
    return op_id


# ── prepare: preconditions + identity ─────────────────────────────────────────


def test_prepare_records_op_and_is_idempotent(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd) == 0
    op_id = closeout.operation_id("P9.2", 1, "i" * 40, "b" * 40)
    assert _op(sd, op_id)["state"] == "prepared"
    # crash/resume between prepare and PR creation: same identity → same record
    assert _prepare(root, sd) == 0
    assert len(list((sd / "operations").glob("*.json"))) == 1


def test_stale_expected_state_fails_without_partial_advancement(
    tmp_path: pathlib.Path,
) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    # caller believes the chain is one ticket behind reality
    rc = _prepare(
        root,
        sd,
        extra=["--expected-last-completed", "P9.0"],
    )
    assert rc == closeout.EXIT_STALE
    # nothing was written: no op record, no partial advancement
    assert not (sd / "operations").exists() or not list((sd / "operations").glob("*.json"))


def test_stale_chain_head_fails(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    rc = _prepare(root, sd, extra=["--expected-chain-head", "0" * 40])
    assert rc == closeout.EXIT_STALE


def test_stale_control_digest_fails(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    rc = _prepare(root, sd, extra=["--expected-control-digest", "f" * 64])
    assert rc == closeout.EXIT_STALE


def test_next_dispatch_prohibited_before_acknowledgment(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd, ticket="P9.2") == 0
    # a different ticket's closeout may not start while this one is in flight
    assert _prepare(root, sd, ticket="P9.3") == closeout.EXIT_STATE


def test_different_implementation_identity_rejected(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _full_closeout(root, sd, impl="a" * 40) is not None
    # already closed; a different implementation identity is refused
    rc = _prepare(root, sd, impl="c" * 40)
    assert rc == closeout.EXIT_IDENTITY


def test_new_recorded_attempt_explains_different_identity(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _full_closeout(root, sd, impl="a" * 40) is not None
    # a new recorded attempt (attempt 2 + reason) is the ONLY accepted path
    rc = _prepare(root, sd, impl="c" * 40, extra=["--attempt", "2"])
    assert rc == closeout.EXIT_IDENTITY  # no reason → still refused
    rc = _prepare(root, sd, impl="c" * 40, extra=["--attempt", "2", "--reason", "impl amended"])
    assert rc == 0
    ops = {json.loads(p.read_text())["operation_id"] for p in (sd / "operations").glob("*.json")}
    assert len(ops) == 2


def test_inflight_different_impl_rejected_then_superseded(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd, impl="a" * 40) == 0
    # a second identity mid-flight without a recorded attempt is refused
    assert _prepare(root, sd, impl="c" * 40) == closeout.EXIT_IDENTITY
    assert (
        _prepare(root, sd, impl="c" * 40, extra=["--attempt", "2", "--reason", "worker amended"])
        == 0
    )
    # the superseded in-flight op is closed out, not silently dropped
    old = closeout.operation_id("P9.2", 1, "a" * 40, "b" * 40)
    assert _op(sd, old)["state"] == "superseded"


# ── external-known: PR identity + ambiguous creation ──────────────────────────


def test_external_known_attaches_once(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd) == 0
    op_id = closeout.operation_id("P9.2", 1, "i" * 40, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # crash/resume: re-attaching the SAME identity is a no-op
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # a second PR number for the same op is the duplicate-creation failure mode
    assert (
        _run(root, ["external-known", "--operation", op_id, "--pr", "8"], sd)
        == closeout.EXIT_IDENTITY
    )
    assert _op(sd, op_id)["pr"]["number"] == 7


def test_uncertain_pr_reconciled_before_retry(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd, extra=["--branch", "devin/p9-2"]) == 0
    op_id = closeout.operation_id("P9.2", 1, "i" * 40, "b" * 40)
    lookup = tmp_path / "lookup.json"
    lookup.write_text(
        json.dumps(
            [
                {
                    "number": 162,
                    "url": "https://example.invalid/pr/162",
                    "headRefName": "devin/p9-2",
                    "baseRefName": "devin/base",
                }
            ]
        )
    )
    # ambiguous remote success: the PR was actually created — reconcile, don't retry
    rc = _run(
        root,
        [
            "external-known",
            "--operation",
            op_id,
            "--uncertain",
            "--head",
            "devin/p9-2",
            "--base-branch",
            "devin/base",
            "--lookup-json",
            str(lookup),
        ],
        sd,
    )
    assert rc == 0
    op = _op(sd, op_id)
    assert op["state"] == "external-known"
    assert op["pr"]["number"] == 162
    assert op["pr"]["reconciled"] is True


def test_uncertain_pr_failed_lookup_is_inconclusive(tmp_path: pathlib.Path) -> None:
    """A failed lookup must NOT read as 'no PR exists' — retrying a create on a
    failed lookup is how duplicate PRs are minted."""
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd, extra=["--branch", "devin/p9-2"]) == 0
    op_id = closeout.operation_id("P9.2", 1, "i" * 40, "b" * 40)
    rc = _run(
        root,
        [
            "external-known",
            "--operation",
            op_id,
            "--uncertain",
            "--head",
            "devin/p9-2",
            "--base-branch",
            "devin/base",
            "--lookup-json",
            str(tmp_path / "does-not-exist.json"),
        ],
        sd,
    )
    assert rc == closeout.EXIT_STATE
    assert _op(sd, op_id)["state"] == "prepared"


def test_uncertain_pr_absent_permits_retry(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _prepare(root, sd, extra=["--branch", "devin/p9-2"]) == 0
    op_id = closeout.operation_id("P9.2", 1, "i" * 40, "b" * 40)
    lookup = tmp_path / "lookup.json"
    lookup.write_text("[]")
    rc = _run(
        root,
        [
            "external-known",
            "--operation",
            op_id,
            "--uncertain",
            "--head",
            "devin/p9-2",
            "--base-branch",
            "devin/base",
            "--lookup-json",
            str(lookup),
        ],
        sd,
    )
    # genuinely-absent creation is reported, op stays prepared → caller may create
    assert rc == 0
    assert _op(sd, op_id)["state"] == "prepared"


# ── memory-committed: the validated git commit is the transaction ─────────────


def test_memory_commit_must_descend_from_expected_head(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    assert _prepare(root, sd, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # a closeout commit on an ORPHAN line never descends from the expected head
    _git(root, "checkout", "-q", "--orphan", "side")
    _git(root, "rm", "-qrf", ".")
    for rel, text in BASE_FILES.items():
        _write(root, rel, text)
    commit = _closeout_commit(root, "P9.2", "P9.3")
    rc = _run(
        root,
        ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
        sd,
    )
    assert rc == closeout.EXIT_STALE
    assert _op(sd, op_id)["state"] == "external-known"  # no advancement recorded


def test_memory_commit_cas_fails_when_control_moved(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    assert _prepare(root, sd, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # another writer lands a control-state change BETWEEN prepare and our commit
    _write(root, "docs/build/LEDGER.md", _lstate("P9.2", "P9.1") + "\n<!-- drift -->\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "other writer drift")
    commit = _closeout_commit(root, "P9.2", "P9.3")
    rc = _run(
        root,
        ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
        sd,
    )
    assert rc == closeout.EXIT_STALE  # compare-and-swap fails, no partial record
    assert _op(sd, op_id)["state"] == "external-known"


def test_memory_commit_requires_memory_files(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    assert _prepare(root, sd, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # a commit that touches no control files is NOT a memory transaction
    _write(root, "docs/build/tools/impl.txt", "more impl\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "not a memory commit")
    commit = _git(root, "rev-parse", "HEAD")
    rc = _run(
        root,
        ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
        sd,
    )
    assert rc == closeout.EXIT_STATE
    assert _op(sd, op_id)["state"] == "external-known"


def test_validator_failure_blocks_memory_transition(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    assert _prepare(root, sd, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    commit = _closeout_commit(root, "P9.2", "P9.3")
    # injected validator failure → the transaction is not recorded
    rc = _run(
        root,
        ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "false"],
        sd,
    )
    assert rc == closeout.EXIT_STATE
    assert _op(sd, op_id)["state"] == "external-known"
    # resume with a passing validator records exactly one transition
    rc = _run(
        root,
        ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
        sd,
    )
    assert rc == 0
    op = _op(sd, op_id)
    assert op["state"] == "memory-committed"
    assert [h["state"] for h in op["history"]].count("memory-committed") == 1


def test_memory_commit_different_commit_rejected(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    assert _prepare(root, sd, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    commit = _closeout_commit(root, "P9.2", "P9.3")
    assert (
        _run(
            root,
            ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
            sd,
        )
        == 0
    )
    # recording a SECOND different memory commit is refused
    _write(root, "docs/build/runs/P9.2.md", "# run v2\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "second")
    other = _git(root, "rev-parse", "HEAD")
    rc = _run(
        root,
        ["memory-committed", "--operation", op_id, "--commit", other, "--validator", "true"],
        sd,
    )
    assert rc == closeout.EXIT_IDENTITY


# ── acknowledge: the authoritative advance gate ───────────────────────────────


def test_acknowledge_requires_actual_advance(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    assert _prepare(root, sd, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # acknowledging before any memory commit is a protocol violation
    assert _run(root, ["acknowledge", "--operation", op_id], sd) == closeout.EXIT_STATE


def test_full_closeout_resumes_to_exactly_one(tmp_path: pathlib.Path) -> None:
    """Failure injection at each boundary: re-driving the protocol after a
    crash at every stage produces exactly one closeout."""
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    impl = _impl_commit(root)
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)

    # boundary 1: crash after prepare → resume is a no-op
    assert _prepare(root, sd, impl=impl) == 0
    assert _prepare(root, sd, impl=impl) == 0
    # boundary 2: crash after PR creation (before/after external-known)
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    assert _run(root, ["external-known", "--operation", op_id, "--pr", "7"], sd) == 0
    # boundary 3..5: crash after run-ledger/index/deferral/ledger edits — the
    # memory commit itself is the transaction boundary; recording it is idempotent
    commit = _closeout_commit(root, "P9.2", "P9.3")
    args = ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"]
    assert _run(root, args, sd) == 0
    assert _run(root, args, sd) == 0  # resume: no-op
    # boundary 6: crash after memory commit, before acknowledgment
    assert _run(root, ["acknowledge", "--operation", op_id], sd) == 0
    assert _run(root, ["acknowledge", "--operation", op_id], sd) == 0
    op = _op(sd, op_id)
    assert op["state"] == "acknowledged"
    # exactly one transition per state in history — no duplicate advancement
    states = [h["state"] for h in op["history"]]
    for s in ("prepared", "external-known", "memory-committed", "acknowledged"):
        assert states.count(s) == 1, states
    assert len(list((sd / "operations").glob("*.json"))) == 1


def test_full_closeout_on_the_round11_values_only_ledger(tmp_path: pathlib.Path) -> None:
    """The protocol reads the cursor from the Round-11 seed shape (values only,
    `harness` slot, archive pointer) exactly as from the legacy shape: a full
    closeout acknowledges once and the authoritative cursor advanced."""
    root = _repo(tmp_path, lstate=_lstate_r11)
    sd = tmp_path / "state"
    op_id = _full_closeout(root, sd, lstate=_lstate_r11)
    op = _op(sd, op_id)
    assert op["state"] == "acknowledged"
    assert [h["state"] for h in op["history"]].count("acknowledged") == 1
    assert closeout._ledger_lval(root, "lastCompleted") == "P9.2"
    assert closeout._ledger_lval(root, "nextTicket") == "P9.3"


# ── racing stale worktrees: one authoritative chain head ─────────────────────


def test_two_stale_worktrees_one_authoritative_head(tmp_path: pathlib.Path) -> None:
    """Two worktrees sharing one git common dir both carry stale control files;
    after the authoritative root advances, neither may prepare on stale belief."""
    auth = _repo(tmp_path, "auth")
    _git(auth, "worktree", "add", "-q", str(tmp_path / "wt-b"), "-b", "stale-b")
    wt_b = tmp_path / "wt-b"
    # shared state dir = the real common dir mechanism (no --state-dir override)
    shared = auth / ".git" / "sig-closeout"
    impl = _impl_commit(auth)
    assert _prepare(auth, None, impl=impl) == 0
    op_id = closeout.operation_id("P9.2", 1, impl, "b" * 40)
    assert _run(auth, ["external-known", "--operation", op_id, "--pr", "7"], None) == 0
    commit = _closeout_commit(auth, "P9.2", "P9.3")
    assert (
        _run(
            auth,
            ["memory-committed", "--operation", op_id, "--commit", commit, "--validator", "true"],
            None,
        )
        == 0
    )
    assert _run(auth, ["acknowledge", "--operation", op_id], None) == 0
    assert shared.is_dir()  # journal lives under the shared common dir
    # stale worktree B: its files still say nextTicket=P9.2/lastCompleted=P9.1,
    # but the authoritative root moved — belief-vs-authority mismatch refuses
    rc = _run(
        wt_b,
        ["prepare", "--ticket", "P9.3", "--implementation", "d" * 40, "--base", "b" * 40],
        None,
    )
    assert rc == closeout.EXIT_STALE
    # and a different implementation identity for the closed ticket is refused
    rc = _run(
        wt_b,
        ["prepare", "--ticket", "P9.2", "--implementation", "d" * 40, "--base", "b" * 40],
        None,
    )
    assert rc == closeout.EXIT_IDENTITY


# ── lock: scoped advisory lock + stale recovery ───────────────────────────────


def test_lock_contention_and_release(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    assert _run(root, ["lock", "acquire"], sd) == 0
    # a second writer cannot take the scoped lock
    assert _run(root, ["lock", "acquire"], sd) == closeout.EXIT_LOCK
    assert _run(root, ["lock", "release"], sd) == 0
    assert _run(root, ["lock", "acquire"], sd) == 0
    assert _run(root, ["lock", "release"], sd) == 0


def test_stale_lock_needs_explicit_recovery(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    scope = closeout._scope_id(closeout.common_dir(root), closeout._chain_id(root))
    ld = sd / "locks" / scope
    ld.mkdir(parents=True)
    dead = 2**22  # an implausibly high pid — no live process
    (ld / "info.json").write_text(
        json.dumps({"pid": dead, "host": closeout.socket.gethostname(), "worktree": str(root)})
    )
    # never removed merely because the holder looks old — explicit recovery only
    assert _run(root, ["lock", "acquire"], sd) == closeout.EXIT_LOCK
    assert _run(root, ["lock", "acquire", "--recover-stale"], sd) == 0
    rec = sd / "recoveries.jsonl"
    assert rec.is_file()
    assert json.loads(rec.read_text().splitlines()[-1])["stale_info"]["pid"] == dead
    assert _run(root, ["lock", "release"], sd) == 0


def test_foreign_host_lock_is_never_reclaimed_here(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    sd = tmp_path / "state"
    scope = closeout._scope_id(closeout.common_dir(root), closeout._chain_id(root))
    ld = sd / "locks" / scope
    ld.mkdir(parents=True)
    (ld / "info.json").write_text(
        json.dumps({"pid": 2**22, "host": "some.other.host", "worktree": "/elsewhere"})
    )
    # PID liveness is single-host only: even a dead pid on another host is
    # surfaced with instructions, never silently reclaimed here
    assert _run(root, ["lock", "acquire", "--recover-stale"], sd) == closeout.EXIT_LOCK
    assert ld.is_dir()


# ── activation-check: legacy/event divergence blocks cutover ─────────────────


def _events_tree(root: pathlib.Path, diverge: bool = False, event_only: bool = False) -> None:
    anchors, _ = obligation_events.build_anchors(root, "2026-10-15", "deadbeef")
    events_rel = root / obligation_events.EVENTS_PATH
    events_rel.parent.mkdir(parents=True, exist_ok=True)
    with events_rel.open("w") as fh:
        for ev in anchors:
            fh.write(json.dumps(ev) + "\n")
        if event_only:
            ev = dict(anchors[0])
            ev["event_id"] = "D-GHOST-1:e0"
            ev["obligation_id"] = "D-GHOST-1"
            fh.write(json.dumps(ev) + "\n")
    if diverge:
        # flip a compatibility cell without a matching transition event
        d = root / "docs/tickets/DEFERRALS.md"
        d.write_text(d.read_text().replace("OPEN cites BL-001", "DONE 2026-10-15 cites BL-001"))


def test_activation_check_ready_on_consistent_state(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    _events_tree(root)
    assert _run(root, ["activation-check"], tmp_path / "sd") == 0


def test_activation_check_blocks_on_cell_divergence(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    _events_tree(root, diverge=True)
    assert _run(root, ["activation-check"], tmp_path / "sd") == closeout.EXIT_BLOCKED


def test_activation_check_blocks_on_event_only_obligation(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    _events_tree(root, event_only=True)
    assert _run(root, ["activation-check"], tmp_path / "sd") == closeout.EXIT_BLOCKED


def test_activation_check_blocks_on_legacy_only_row(tmp_path: pathlib.Path) -> None:
    root = _repo(tmp_path)
    # no events.jsonl at all — every DEFERRALS row is legacy-only
    assert _run(root, ["activation-check"], tmp_path / "sd") == closeout.EXIT_BLOCKED
