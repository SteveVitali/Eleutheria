#!/usr/bin/env python3
"""living_record_backtest.py — the nightly advance backtest (living-backtest/1).

P34.31 (B4 §G6, SIG-ENG-040, BM-TEST-01, OM-15, ADR-197): the AST lint
(living_record_lint.py) protects today's tree; this tool catches a pin by
*replaying history read-only*. For every first-parent transition C → C′
inside `--window` commits where C′ changed a declared living record, it:

  1. archives C′ into a scratch tree (git archive — the checkout is never
     touched; the run writes only under a temp dir and --json),
  2. computes which of C's test files were living-reading under the same
     policy the lint uses,
  3. materialises C's test files into the C′ tree and runs exactly those
     tests under the *caller's* interpreter (`sys.executable -m pytest`), and
  4. classifies every failure: the identical test still fails on C′ —
     "pin-broken" (a living-record pin caught at the transition that broke
     it); the test was edited or removed at C′ — "converted-in-head" (the
     pin was being fixed in that commit, expected); a collection/environment
     error — "infra" (counted, never a pin finding).

A pin fails exactly at such a transition — the #165/#179/#185 shape — so a
non-empty pin-broken set is a nightly failure (exit 1). A run with no
transitions or no replayed tests is vacuous (exit 3), never green.

Note: package imports in replayed tests resolve from the caller's
environment (the workspace at HEAD); build-memory paths resolve inside the
replayed tree — the evaluated set is docs-reading tests, so that is the
fidelity the gate needs (documented in ADR-197).
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from living_record_lint import (  # noqa: E402
    POLICY_REL,
    TEST_GLOBS,
    Analyzer,
    load_policy,
)

SCHEMA = "living-backtest/1"


def _git(root: Path, *args: str, binary: bool = False):
    out = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
    )
    return out.stdout if binary else out.stdout.decode()


def _show(root: Path, rev_path: str) -> str | None:
    out = subprocess.run(
        ["git", "-C", str(root), "show", rev_path],
        capture_output=True,
        check=False,
    )
    return out.stdout.decode() if out.returncode == 0 else None


def transitions(root: Path, policy, window: int) -> list[dict]:
    """First-parent pairs C → C′ (oldest first) where C′ touched a living path."""
    commits = _git(root, "rev-list", "--first-parent", "-n", str(window), "HEAD").split()
    commits.reverse()  # oldest → newest
    out = []
    for base, head in zip(commits, commits[1:], strict=False):
        changed = _git(root, "diff", "--name-only", base, head).split()
        living = [c for c in changed if policy.classify(c) == "living"]
        if living:
            out.append({"base": base, "head": head, "changed_living": living})
    return out


def _test_files_at(root: Path, rev: str) -> list[str]:
    files = _git(root, "ls-tree", "-r", "--name-only", rev).split()
    return [f for f in files if any(fnmatch.fnmatchcase(f, g) for g in TEST_GLOBS)]


def evaluated_tests_at(root: Path, rev: str, policy) -> list[tuple[str, str]]:
    """(file, test) pairs evaluated under the policy at `rev` — the same rule
    the lint applies (living tree reads; snapshot reads replay too)."""
    out = []
    for rel in _test_files_at(root, rev):
        src = _show(root, f"{rev}:{rel}")
        if src is None or "test" not in src:
            continue
        try:
            az = Analyzer(policy, rel, src, root)
        except SyntaxError:
            continue
        for name, fn in az.fns.items():
            if not name.split(".")[-1].startswith("test"):
                continue
            reads = az.reads_in_subtree(fn)
            living = [r for r in reads if r[1] == "tree" and policy.classify(r[0]) == "living"]
            snaps = [
                r
                for r in reads
                if r[1] == "snapshot" and policy.classify(r[0]) in ("living", "frozen")
            ]
            if living or snaps:
                out.append((rel, name))
    return out


def _materialize(root: Path, rev: str, dest: Path, paths: list[str]) -> None:
    """Overlay `paths` from `rev` into `dest` (C's test files onto C′'s tree)."""
    for rel in paths:
        src = _show(root, f"{rev}:{rel}")
        if src is None:
            continue
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src, encoding="utf-8")


def _fn_segment(src: str, qualname: str) -> str | None:
    """Source segment of the named test (for the same-source check)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    parts = qualname.split(".")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == parts[-1]:
                return ast.get_source_segment(src, node)
    return None


def replay_transition(root: Path, policy, trans: dict, work: Path, timeout: int) -> dict:
    base, head = trans["base"], trans["head"]
    result = {
        "base": base[:12],
        "head": head[:12],
        "changed_living": trans["changed_living"],
        "tests_evaluated": 0,
        "tests_replayed": 0,
        "failures": [],
        "infra": 0,
    }
    tests = evaluated_tests_at(root, base, policy)
    result["tests_evaluated"] = len(tests)
    if not tests:
        return result
    tree = work / "tree"
    tree.mkdir(parents=True, exist_ok=True)
    archive = _git(root, "archive", head, binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        tf.extractall(tree, filter="data")
    # C's evaluated test files replace C′'s — "C's tests against C′'s tree".
    # C′-only test files stay in place (the coverage checker cites tests as
    # evidence — removing them would fabricate a red the tree never had);
    # they simply are not asked to run.
    _materialize(root, base, tree, sorted({rel for rel, _ in tests}))
    # conftest/support modules must come from C too (C's harness).
    _materialize(
        root,
        base,
        tree,
        [f for f in _test_files_at(root, base) if f.endswith(("conftest.py", "support.py"))],
    )
    nodeids = [f"{tree / rel}::{name.replace('.', '::')}" for rel, name in sorted(set(tests))]
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--tb=line",
            "-rf",
            "-q",
            *nodeids,
        ],
        capture_output=True,
        text=True,
        cwd=tree,
        timeout=timeout,
    )
    known = {rel for rel, _ in tests}
    failed = []
    for ln in out.stdout.splitlines():
        if ln.startswith("FAILED "):
            node = ln.split(maxsplit=2)[1]
            path_part, _, qual = node.partition("::")
            # pytest rewrites the nodeid against its own rootdir — map back by
            # suffix against the nodeids we actually asked for.
            rel = next(
                (k for k in known if path_part.replace(os.sep, "/").endswith(k)),
                path_part,
            )
            failed.append((rel, qual.replace("::", "."), node))
    result["infra"] = sum(1 for ln in out.stdout.splitlines() if ln.startswith("ERROR "))
    result["tests_replayed"] = len(nodeids)
    for rel, qual, node in failed:
        src_c = _show(root, f"{base}:{rel}")
        src_h = _show(root, f"{head}:{rel}")
        if src_h is None:
            cls = "removed-in-head"
        elif src_c is not None and _fn_segment(src_c, qual) != _fn_segment(src_h, qual):
            cls = "converted-in-head"
        else:
            cls = "pin-broken"
        result["failures"].append({"test": node, "class": cls})
    return result


def run(
    root: Path, window: int, max_transitions: int, timeout: int, policy_path: Path | None = None
) -> dict:
    root = Path(root).resolve()
    policy = load_policy(policy_path or (root / POLICY_REL))
    trans = transitions(root, policy, window)
    report = {
        "schema": SCHEMA,
        "root": str(root),
        "head": _git(root, "rev-parse", "HEAD").strip(),
        "window": window,
        "transitions": [],
        "totals": {
            "first_parent_scanned": 0,
            "transitions_with_living_change": len(trans),
            "transitions_replayed": 0,
            "tests_replayed": 0,
            "pin_broken": 0,
            "converted_in_head": 0,
            "removed_in_head": 0,
            "infra": 0,
        },
    }
    report["totals"]["first_parent_scanned"] = len(
        _git(root, "rev-list", "--first-parent", "-n", str(window), "HEAD").split()
    )
    for t in trans[:max_transitions]:
        with tempfile.TemporaryDirectory() as td:
            result = replay_transition(root, policy, t, Path(td), timeout)
        report["transitions"].append(result)
        report["totals"]["transitions_replayed"] += 1
        report["totals"]["tests_replayed"] += result["tests_replayed"]
        report["totals"]["infra"] += result["infra"]
        for f_ in result["failures"]:
            report["totals"][f_["class"].replace("-", "_")] += 1
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument(
        "--window", type=int, default=200, help="first-parent commits to scan for transitions"
    )
    ap.add_argument(
        "--max-transitions", type=int, default=20, help="most recent transitions to actually replay"
    )
    ap.add_argument("--timeout", type=int, default=600, help="seconds per replayed pytest run")
    ap.add_argument("--policy", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)
    report = run(Path(args.root), args.window, args.max_transitions, args.timeout, args.policy)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    t = report["totals"]
    print(
        f"living-backtest: {t['transitions_replayed']} transitions replayed "
        f"({t['transitions_with_living_change']} with a living change in the last "
        f"{report['window']} first-parent commits), {t['tests_replayed']} tests "
        f"replayed, {t['pin_broken']} pin-broken, "
        f"{t['converted_in_head']} converted-in-head, "
        f"{t['removed_in_head']} removed-in-head, {t['infra']} infra"
    )
    for tr in report["transitions"]:
        for f_ in tr["failures"]:
            print(
                f"  {f_['class']}: {f_['test']} "
                f"({tr['base']}..{tr['head']} — changed: {', '.join(tr['changed_living'][:3])})"
            )
    if t["pin_broken"]:
        return 1
    if t["transitions_replayed"] == 0 or t["tests_replayed"] == 0:
        print("living-backtest: VACUOUS — no transitions or no replayed tests", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
