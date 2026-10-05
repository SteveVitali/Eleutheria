#!/usr/bin/env python3
"""living_record_lint.py — the G6 AST lint (living-record-lint/1).

P34.31 (B4 §G6, SIG-ENG-040, BM-TEST-01, OM-15, ADR-197): no test may pin the
current value of a living build record. The policy
(`docs/build/tools/record_policy/living_records.toml`, schema
living-record-policy/1) declares which committed paths are living, which are
frozen artifacts, the LEDGER current-state keys, the status vocabulary, the
named-id shapes and the reviewed escape-hatch registry.

A test is *evaluated* when it reads a declared living path from the repository
tree — a `Path(__file__).resolve().parents[N]`/`REPO_ROOT`-anchored path
expression, `open()`/`read_text()`/`exists()`/`glob()` on one, a literal repo
relative path bound to a helper's path parameter, or a literal `git show
<sha>:<living>` snapshot read (recorded, always allowed). Reads rooted at
`tmp_path`, fixture trees or subprocess `--root <tmp>` arguments do not anchor
to the repository and are never evaluated — the fixture `KEYS` constants that
tripped the old `living-pin?` heuristic are not test-level reads at all.

An evaluated test is a violation when its subtree (itself plus the same-file
helpers it calls) contains:

  rule-1  a literal matching `key: value` for a declared current-state key;
  rule-2  an assertion holding a status-word literal together with a named-id
          literal (same assert or named elsewhere in the test), or a
          status-word literal asserted of a value derived from a living
          record;
  rule-3  `len(<living-derived>) == <int literal>`;
  rule-4  a literal row range (`"rows 1-200"`) or ISO date (`"2026-10-05"`)
          inside an assertion.

`@pytest.mark.living_record_invariant("<key>")` exempts one test when the key
is registered in the policy's `[invariants.allowed]`; an unregistered key is
itself a violation. Frozen-artifact reads may assert concrete facts freely.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = "living-record-lint/1"
POLICY_SCHEMA = "living-record-policy/1"
POLICY_REL = "docs/build/tools/record_policy/living_records.toml"
MARK = "living_record_invariant"

_READ_ATTRS = {
    "read_text",
    "read_bytes",
    "open",
    "exists",
    "is_file",
    "is_dir",
    "glob",
    "iterdir",
    "stat",
    "rglob",
}
_KEY_LIT = None  # built from the policy
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_ROWRANGE_RE = re.compile(r"\brows?\s+\d+\s*[-–—]\s*\d+\b", re.IGNORECASE)
# `git show <sha>:<path>` — literal sha or an f-string ({sha}:path → pseudo 'x:path')
_SNAPSHOT_RE = re.compile(r"(?:[0-9a-f]{6,64}|x):((?:docs/|README\.md|CHANGELOG\.md)[^\s'\"]*)")


@dataclass
class Policy:
    living_paths: set[str]
    living_globs: list[str]
    frozen_paths: set[str]
    frozen_globs: list[str]
    keys: list[str]
    statuses: set[str]
    id_res: list[re.Pattern]
    invariants: dict[str, str]

    def classify(self, rel: str) -> str | None:
        """'living', 'frozen', or None. Living wins over frozen."""
        rel = rel.replace(os.sep, "/").lstrip("/")
        if rel in self.living_paths:
            return "living"
        for g in self.living_globs:
            if fnmatch.fnmatchcase(rel, g):
                return "living"
        if rel in self.frozen_paths:
            return "frozen"
        for g in self.frozen_globs:
            if fnmatch.fnmatchcase(rel, g):
                return "frozen"
        return None


def load_policy(path: Path) -> Policy:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != POLICY_SCHEMA:
        raise SystemExit(f"{path}: schema must be {POLICY_SCHEMA!r}")
    return Policy(
        living_paths=set(raw["living"]["paths"]),
        living_globs=list(raw["living"]["globs"]),
        frozen_paths=set(raw["frozen"]["paths"]),
        frozen_globs=list(raw["frozen"]["globs"]),
        keys=list(raw["keys"]["current_state"]),
        statuses=set(raw["vocabulary"]["statuses"]),
        id_res=[re.compile(p) for p in raw["named_ids"]["patterns"]],
        invariants=dict(raw.get("invariants", {}).get("allowed", {})),
    )


# ── AST helpers ────────────────────────────────────────────────────────────


def _const(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                parts.append("x")  # opaque formatted value
        return "".join(parts)
    return None


def _seg_list(node: ast.AST) -> list[str] | None:
    """A '/'-joined literal like 'docs' / 'build' -> ['docs','build']."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = _seg_list(node.left), _seg_list(node.right)
        if left is not None and right is not None:
            return left + right
        return None
    c = _const(node)
    if c is not None:
        return [c]
    return None


@dataclass
class PathExpr:
    """A path expression anchored at the repo root, plus its literal tail."""

    tail: tuple[str, ...]  # literal segments after the repo root
    anchored: bool = True


@dataclass
class Fn:
    node: ast.FunctionDef | ast.AsyncFunctionDef
    file_rel: str
    calls: list[tuple[ast.Call, str | None]] = field(default_factory=list)


class Analyzer:
    """Per-file analysis: anchors, constants, functions, read events."""

    def __init__(self, policy: Policy, rel: str, source: str, repo_root: Path):
        self.policy = policy
        self.rel = rel
        self.repo_root = repo_root
        self.file_dir = Path(os.path.dirname(rel))
        tree = ast.parse(source, filename=rel)
        self.tree = tree
        self.anchors: dict[str, tuple[str, ...] | None] = {}  # name -> tail or None
        self.str_consts: dict[str, str] = {}
        self.tuple_consts: dict[str, tuple[str, ...]] = {}
        self.fns: dict[str, Fn] = {}
        self._scan_module(tree)

    # ── module scan ────────────────────────────────────────────────────

    def _resolve_file_anchor(self, node: ast.AST) -> Path | None:
        """Path(__file__).resolve().parents[N] / .parent chains → the
        repo-root-relative directory they point at."""
        parents = 0
        cur = node
        while True:
            if isinstance(cur, ast.Call) and isinstance(cur.func, ast.Attribute):
                if cur.func.attr in ("resolve", "absolute"):
                    cur = cur.func.value
                    continue
                if cur.func.attr == "parent":
                    parents += 1
                    cur = cur.func.value
                    continue
            if (
                isinstance(cur, ast.Subscript)
                and isinstance(cur.value, ast.Attribute)
                and cur.value.attr == "parents"
            ):
                if isinstance(cur.slice, ast.Constant) and isinstance(cur.slice.value, int):
                    parents += cur.slice.value
                    cur = cur.value.value
                    continue
            break
        base = cur
        if isinstance(base, ast.Call):
            f = base.func
            is_path = (isinstance(f, ast.Name) and f.id == "Path") or (
                isinstance(f, ast.Attribute) and f.attr == "Path"
            )
            if (
                is_path
                and base.args
                and isinstance(base.args[0], ast.Name)
                and base.args[0].id == "__file__"
            ):
                p = self.file_dir
                for _ in range(parents):
                    p = p.parent
                return p
        return None

    def _pathexpr(self, node: ast.AST) -> PathExpr | None:
        """Resolve a path expression anchored at the repo root to its tail."""
        # __file__-anchored expression (Path(__file__).resolve().parents[N]…)
        anchor = self._resolve_file_anchor(node)
        if anchor is not None:
            return PathExpr(tuple(anchor.parts))
        # bare anchored name
        if isinstance(node, ast.Name):
            tail = self.anchors.get(node.id)
            if tail is not None:
                return PathExpr(tuple(tail))
            return None
        if isinstance(node, ast.Attribute):
            # .parent navigation on a resolved anchor: tail is shortened
            if node.attr == "parent":
                inner = self._pathexpr(node.value)
                if inner is not None and inner.tail:
                    return PathExpr(inner.tail[:-1])
                return None
            return None
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "Path" and node.args:
                inner = self._pathexpr(node.args[0])
                return inner
            if isinstance(f, ast.Attribute):
                if f.attr in ("resolve", "absolute"):
                    return self._pathexpr(f.value)
                if f.attr == "parent":
                    inner = self._pathexpr(f.value)
                    if inner is not None and inner.tail:
                        return PathExpr(inner.tail[:-1])
                    return None
            # f"{..}"-joined literals are not resolvable path tails
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = self._pathexpr(node.left)
            if left is None:
                return None
            segs = _seg_list(node.right)
            if segs is None:
                return PathExpr(left.tail, anchored=True)  # tail unknown
            return PathExpr(left.tail + tuple(segs))
        if isinstance(node, ast.Subscript):
            if (
                isinstance(node.value, ast.Attribute)
                and node.value.attr == "parents"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, int)
            ):
                inner = self._pathexpr(node.value.value)
                if inner is not None and len(inner.tail) >= node.slice.value:
                    return PathExpr(inner.tail[: len(inner.tail) - node.slice.value])
            return None
        return None

    def _scan_module(self, tree: ast.Module) -> None:
        # imports: `from support import REPO_ROOT` anchors the name at root
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module == "support":
                for a in n.names:
                    if a.name in ("REPO_ROOT", "ROOT"):
                        self.anchors[a.asname or a.name] = ()
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.fns[n.name] = Fn(node=n, file_rel=self.rel)
            elif isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.fns[f"{n.name}.{m.name}"] = Fn(node=m, file_rel=self.rel)
        # module-level simple assignments
        for n in tree.body:
            if (
                isinstance(n, ast.Assign)
                and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
            ):
                name = n.targets[0].id
                val = n.value
                anchor = self._resolve_file_anchor(val)
                if anchor is not None:
                    self.anchors[name] = self._tail_of(anchor)
                    continue
                pe = self._pathexpr(val)
                if pe is not None:
                    self.anchors[name] = pe.tail
                    continue
                c = _const(val)
                if c is not None:
                    self.str_consts[name] = c
                    continue
                if isinstance(val, (ast.Tuple, ast.List, ast.Set)):
                    items = [_const(e) for e in val.elts]
                    if all(i is not None for i in items):
                        self.tuple_consts[name] = tuple(items)  # type: ignore[arg-type]

    def _tail_of(self, p: Path) -> tuple[str, ...]:
        """Repo-root-relative tail (empty tuple = the repo root itself)."""
        return tuple(p.parts) if str(p) != "." else ()

    # ── function analysis ──────────────────────────────────────────────

    def _param_is_pathish(self, fn: Fn, pname: str, _depth: int = 0) -> bool:
        """A param fed a repo-relative literal: joined to an anchored base or
        used in a read position inside the helper (or forwarded to another
        same-file helper's pathish param)."""
        if _depth > 4:
            return False
        for node in ast.walk(fn.node):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                left = self._pathexpr(node.left)
                if left is not None and isinstance(node.right, ast.Name) and node.right.id == pname:
                    return True
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Attribute) and f.attr in _READ_ATTRS:
                    if isinstance(f.value, ast.Name) and f.value.id == pname:
                        return True
                if isinstance(f, ast.Name) and f.id in ("open", "Path"):
                    if (
                        node.args
                        and isinstance(node.args[0], ast.Name)
                        and node.args[0].id == pname
                    ):
                        return True
                # forwarded to a same-file helper's pathish param
                if isinstance(f, ast.Name):
                    key = self._fn_key(f.id)
                    if key:
                        helper = self.fns[key]
                        for i, arg in enumerate(node.args):
                            if (
                                i < len(helper.node.args.args)
                                and isinstance(arg, ast.Name)
                                and arg.id == pname
                                and self._param_is_pathish(
                                    helper, helper.node.args.args[i].arg, _depth + 1
                                )
                            ):
                                return True
        return False

    def _loop_consts(self, node: ast.AST) -> dict[str, tuple[str, ...]]:
        """for V in ('a','b') / module-constant tuple -> V values."""
        out: dict[str, tuple[str, ...]] = {}
        for n in ast.walk(node):
            if isinstance(n, (ast.For, ast.comprehension)):
                if isinstance(n.target, ast.Name):
                    it = n.iter
                    vals: tuple[str, ...] | None = None
                    if isinstance(it, (ast.Tuple, ast.List, ast.Set)):
                        items = [_const(e) for e in it.elts]
                        if all(i is not None for i in items):
                            vals = tuple(items)  # type: ignore[arg-type]
                    elif isinstance(it, ast.Name) and it.id in self.tuple_consts:
                        vals = self.tuple_consts[it.id]
                    if vals:
                        out[n.target.id] = vals
        return out

    def _fn_key(self, name: str) -> str | None:
        if name in self.fns:
            return name
        for k in self.fns:
            if k.endswith(f".{name}"):
                return k
        return None

    def subtree(self, fn: Fn, depth: int = 0) -> Iterable[tuple[str, ast.AST]]:
        """Yield (qualname, node) for fn plus same-file helpers it calls."""
        yield fn.node.name, fn.node
        if depth >= 6:
            return
        seen_calls = {fn.node.name}
        for node in ast.walk(fn.node):
            if isinstance(node, ast.Call):
                f = node.func
                name = None
                if isinstance(f, ast.Name):
                    name = f.id
                elif isinstance(f, ast.Attribute):
                    name = f.attr
                key = self._fn_key(name) if name else None
                if key and key not in seen_calls:
                    seen_calls.add(key)
                    yield from self.subtree(self.fns[key], depth + 1)

    def reads_in_subtree(self, fn: Fn) -> list[tuple[str, str, int, str]]:
        """(rel_path, channel, line, where) living/frozen reads in the subtree.

        channel: 'tree' | 'snapshot'. where is the owning function name.
        """
        events: list[tuple[str, str, int, str]] = []
        for where, node in self.subtree(fn):
            loop_consts = self._loop_consts(node)
            for sub in ast.walk(node):
                # anchored path expressions under read position
                if isinstance(sub, ast.Call):
                    f = sub.func
                    if isinstance(f, ast.Attribute) and f.attr in _READ_ATTRS:
                        pe = self._pathexpr(f.value)
                        if pe is not None and pe.tail:
                            events.append(("/".join(pe.tail), "tree", sub.lineno, where))
                    if isinstance(f, ast.Name) and f.id == "open" and sub.args:
                        pe = self._pathexpr(sub.args[0])
                        if pe is not None and pe.tail:
                            events.append(("/".join(pe.tail), "tree", sub.lineno, where))
                    # helper call with a literal arg bound to a pathish param
                    if isinstance(f, ast.Name) and f.id in self.fns:
                        helper = self.fns[f.id]
                        for i, arg in enumerate(sub.args):
                            if i < len(helper.node.args.args):
                                pname = helper.node.args.args[i].arg
                                if self._param_is_pathish(helper, pname):
                                    c = _const(arg)
                                    if c is not None:
                                        events.append((c, "tree", sub.lineno, where))
                                    else:
                                        pe = self._pathexpr(arg)
                                        if pe is not None and pe.tail:
                                            events.append(
                                                ("/".join(pe.tail), "tree", sub.lineno, where)
                                            )
                # anchored joins used as values (existence, open-args, asserts)
                if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Div):
                    pe = self._pathexpr(sub)
                    if pe is not None and pe.tail:
                        events.append(("/".join(pe.tail), "tree", sub.lineno, where))
                # loop-constant anchored names: `for rel in TUP: _read(rel)`
                if isinstance(sub, ast.Name) and sub.id in loop_consts:
                    for v in loop_consts[sub.id]:
                        events.append((v, "tree", sub.lineno, where))
                # explicit snapshot reads `git show <sha>:<path>`
                c = _const(sub)
                if c is not None:
                    for m in _SNAPSHOT_RE.finditer(c):
                        events.append((m.group(1), "snapshot", sub.lineno, where))
        # dedupe
        seen = set()
        uniq = []
        for e in events:
            key = (e[0], e[1], e[2])
            if key not in seen:
                seen.add(key)
                uniq.append(e)
        return uniq

    def invariant_key(self, fn: Fn) -> str | None:
        for dec in fn.node.decorator_list:
            node = dec
            args: list[ast.expr] = []
            if isinstance(node, ast.Call):
                args = node.args
                node = node.func
            if (
                isinstance(node, ast.Attribute)
                and node.attr == MARK
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "mark"
            ):
                if args:
                    return _const(args[0]) or ""
                return ""
        return None

    # ── taint: names derived from a living read ────────────────────────

    def _expr_living_names(self, node: ast.AST, tainted: set[str]) -> set[str]:
        names = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in tainted:
                names.add(n.id)
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name):
                    key = self._fn_key(f.id)
                    if key:
                        helper = self.fns[key]
                        living_call = self._fn_reads_living(helper)
                        # literal arg bound to a pathish helper param
                        for i, arg in enumerate(n.args):
                            if i < len(helper.node.args.args) and self._param_is_pathish(
                                helper, helper.node.args.args[i].arg
                            ):
                                c = _const(arg)
                                if c is not None and self.policy.classify(c) == "living":
                                    living_call = True
                        if living_call:
                            names.add(f"@{f.id}")
                if isinstance(f, ast.Attribute) and f.attr in _READ_ATTRS:
                    pe = self._pathexpr(f.value)
                    if pe is not None and pe.tail:
                        if self.policy.classify("/".join(pe.tail)) == "living":
                            names.add("@read")
                # any call fed a tainted argument yields a tainted result
                for arg in [*n.args, *(k.value for k in n.keywords)]:
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Name) and sub.id in tainted:
                            names.add("@call")
        return names

    def _fn_reads_living(self, fn: Fn) -> bool:
        for path, chan, _l, _w in self.reads_in_subtree(fn):
            if chan == "tree" and self.policy.classify(path) == "living":
                return True
        return False

    def tainted_names(self, fn: Fn) -> set[str]:
        """Names in the test's subtree bound to living-derived values."""
        tainted: set[str] = {"@read"}
        nodes = [n for _w, n in self.subtree(fn)]
        for _ in range(3):
            changed = False
            for node in nodes:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        targets = []
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                targets.append(t.id)
                            elif isinstance(t, (ast.Tuple, ast.List)):
                                targets += [e.id for e in t.elts if isinstance(e, ast.Name)]
                        if targets and self._expr_living_names(sub.value, tainted):
                            for t in targets:
                                if t not in tainted:
                                    tainted.add(t)
                                    changed = True
                    elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                        if self._expr_living_names(sub.value, tainted):
                            if sub.target.id not in tainted:
                                tainted.add(sub.target.id)
                                changed = True
                    elif isinstance(sub, ast.For) and isinstance(sub.target, ast.Name):
                        if self._expr_living_names(sub.iter, tainted):
                            if sub.target.id not in tainted:
                                tainted.add(sub.target.id)
                                changed = True
                    elif isinstance(sub, ast.comprehension) and isinstance(sub.target, ast.Name):
                        if self._expr_living_names(sub.iter, tainted):
                            if sub.target.id not in tainted:
                                tainted.add(sub.target.id)
                                changed = True
            if not changed:
                break
        return tainted

    # ── literal collection ─────────────────────────────────────────────

    def _docstrings(self, node: ast.AST) -> set[int]:
        """Node ids of docstring Expr nodes (module/class/function first
        statements) — prose is not an asserted literal."""
        out = set()
        for n in ast.walk(node):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if (
                    n.body
                    and isinstance(n.body[0], ast.Expr)
                    and isinstance(n.body[0].value, ast.Constant)
                    and isinstance(n.body[0].value.value, str)
                ):
                    out.add(id(n.body[0].value))
        return out

    def _literals(self, node: ast.AST) -> list[tuple[str, int]]:
        out = []
        joined_parts = {
            id(c) for n in ast.walk(node) if isinstance(n, ast.JoinedStr) for c in n.values
        }
        docstrings = self._docstrings(node)
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                if id(n) in joined_parts or id(n) in docstrings:
                    continue
                out.append((n.value, n.lineno))
            elif isinstance(n, ast.JoinedStr):
                c = _const(n)
                if c:
                    out.append((c, n.lineno))
            elif isinstance(n, ast.Name) and n.id in self.str_consts:
                out.append((self.str_consts[n.id], n.lineno))
        return out

    def _named_id(self, lit: str) -> str | None:
        for pat in self.policy.id_res:
            m = pat.search(lit)
            if m:
                return m.group(0)
        return None

    def _status_literal(self, lit: str) -> str | None:
        s = lit.strip()
        if s in self.policy.statuses:
            return s
        first = s.split(maxsplit=1)[0] if s.split() else ""
        if first in self.policy.statuses:
            return first
        return None

    # ── rule evaluation ────────────────────────────────────────────────

    def evaluate(self, fn: Fn) -> list[dict]:
        """Violations for one evaluated test."""
        viols: list[dict] = []
        nodes = [n for _w, n in self.subtree(fn)]
        tainted = self.tainted_names(fn)
        all_lits: list[tuple[str, int]] = []
        for n in nodes:
            all_lits += self._literals(n)
        subtree_has_id = any(self._named_id(lit) for lit, _ in all_lits)

        key_re = re.compile(
            r"(?:^|[\s'\"({,])(?:" + "|".join(re.escape(k) for k in self.policy.keys) + r")\s*:"
        )

        for n in nodes:
            # rule-1: current-state `key: value` literal anywhere in the test
            for lit, line in self._literals(n):
                m = key_re.search(lit)
                if m:
                    key = next(k for k in self.policy.keys if k in lit.split(":")[0])
                    viols.append(
                        {
                            "rule": "rule-1",
                            "line": line,
                            "detail": f"literal pins a current-state key ({key!r}): {lit[:80]!r}",
                        }
                    )
            # assert-scoped rules 2–4
            for sub in ast.walk(n):
                if isinstance(sub, ast.Assert):
                    alits = self._literals(sub)
                    status_lits = [s for lit, _ in alits if (s := self._status_literal(lit))]
                    id_lits = [i for lit, _ in alits if (i := self._named_id(lit))]
                    tainted_names = {
                        x.id for x in ast.walk(sub) if isinstance(x, ast.Name) and x.id in tainted
                    }
                    touched = tainted_names or bool(self._expr_living_names(sub, tainted))
                    if status_lits and (touched or id_lits or subtree_has_id):
                        viols.append(
                            {
                                "rule": "rule-2",
                                "line": sub.lineno,
                                "detail": (
                                    f"assertion pins a status ({status_lits[0]!r})"
                                    + (
                                        f" of named id {id_lits[0]!r}"
                                        if id_lits
                                        else " with a record name in the test"
                                    )
                                ),
                            }
                        )
                    # `derived == "<record id>"` pins a living value to a named
                    # record (presence/`in` membership is reference resolution).
                    for cmpn in ast.walk(sub):
                        if not isinstance(cmpn, ast.Compare):
                            continue
                        for op_i, op in enumerate(cmpn.ops):
                            if not isinstance(op, ast.Eq):
                                continue
                            sides = [cmpn.left, *cmpn.comparators]
                            l_side, r_side = sides[op_i], sides[op_i + 1]
                            for lit_side, der_side in ((l_side, r_side), (r_side, l_side)):
                                lit_c = _const(lit_side)
                                if lit_c is None or not self._named_id(lit_c):
                                    continue
                                der_names = {
                                    x.id
                                    for x in ast.walk(der_side)
                                    if isinstance(x, ast.Name) and x.id in tainted
                                }
                                der_call = any(
                                    isinstance(x, ast.Call) for x in ast.walk(der_side)
                                ) and bool(self._expr_living_names(der_side, tainted))
                                if der_names or der_call:
                                    viols.append(
                                        {
                                            "rule": "rule-2",
                                            "line": cmpn.lineno,
                                            "detail": (
                                                f"assertion pins a living-derived value "
                                                f"to record id {self._named_id(lit_c)!r}"
                                            ),
                                        }
                                    )
                    # rule-3: len(<living-derived>) == <int>
                    for cmp_node in ast.walk(sub):
                        if isinstance(cmp_node, ast.Compare):
                            sides = [cmp_node.left, *cmp_node.comparators]
                            for i, s_ in enumerate(sides):
                                if (
                                    isinstance(s_, ast.Call)
                                    and isinstance(s_.func, ast.Name)
                                    and s_.func.id == "len"
                                    and s_.args
                                    and isinstance(
                                        s_.args[0], (ast.Name, ast.Attribute, ast.Subscript)
                                    )
                                ):
                                    other = sides[1 - i] if len(sides) == 2 else None
                                    if isinstance(other, ast.Constant) and isinstance(
                                        other.value, int
                                    ):
                                        arg = s_.args[0]
                                        names_in = {
                                            x.id for x in ast.walk(arg) if isinstance(x, ast.Name)
                                        }
                                        if names_in & tainted:
                                            viols.append(
                                                {
                                                    "rule": "rule-3",
                                                    "line": cmp_node.lineno,
                                                    "detail": f"len(<living-derived>) == {other.value}",
                                                }
                                            )
                    # rule-4: literal row-range or calendar date in the assert
                    for lit, line in alits:
                        m = _DATE_RE.search(lit) or _ROWRANGE_RE.search(lit)
                        if m:
                            viols.append(
                                {
                                    "rule": "rule-4",
                                    "line": line,
                                    "detail": (
                                        f"literal row-range/date in assertion: {m.group(0)!r}"
                                    ),
                                }
                            )
        return viols


# ── tree driver ────────────────────────────────────────────────────────────

TEST_GLOBS = ("tests/*.py", "tests/**/*.py", "docs/build/tools/test_*.py")


def _repo_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", *TEST_GLOBS],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return sorted(out)


def lint_tree(root: Path, policy_path: Path | None = None) -> dict:
    root = Path(root).resolve()
    policy_path = policy_path or (root / POLICY_REL)
    policy = load_policy(policy_path)
    report = {
        "schema": SCHEMA,
        "policy": str(
            policy_path.relative_to(root) if policy_path.is_relative_to(root) else policy_path
        ),
        "root": str(root),
        "files_scanned": 0,
        "tests_evaluated": 0,
        "snapshot_reads": 0,
        "evaluated": [],
        "exempted": [],
        "violations": [],
    }
    for rel in _repo_files(root):
        src = (root / rel).read_text(encoding="utf-8")
        if "test_" not in src:
            continue
        report["files_scanned"] += 1
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
            report["snapshot_reads"] += len(snaps)
            if not living and not snaps:
                continue
            report["tests_evaluated"] += 1
            key = az.invariant_key(fn)
            viols = az.evaluate(fn) if living else []
            entry = {"file": rel, "test": name, "reads": sorted({r[0] for r in living + snaps})}
            unregistered = key is not None and key not in policy.invariants
            if viols:
                for v in viols:
                    v.update({"file": rel, "test": name})
                if key is not None and not unregistered:
                    entry["status"] = "exempt"
                    entry["invariant"] = key
                    entry["waived"] = [{k: v[k] for k in ("rule", "line", "detail")} for v in viols]
                    report["exempted"].append(entry)
                else:
                    entry["status"] = "violation"
                    report["violations"] += viols
            else:
                entry["status"] = "exempt" if key else "clean"
                if key:
                    entry["invariant"] = key
            if unregistered:
                report["violations"].append(
                    {
                        "rule": "unregistered-invariant",
                        "line": fn.node.lineno,
                        "detail": f"mark {MARK}({key!r}) is not in [invariants.allowed]",
                        "file": rel,
                        "test": name,
                    }
                )
                entry["status"] = "violation"
            report["evaluated"].append(entry)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default=".", help="repository root")
    ap.add_argument("--policy", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None, help="write the JSON report here")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)
    report = lint_tree(Path(args.root), args.policy)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not args.quiet:
        for v in report["violations"]:
            print(f"{v['file']}:{v['line']} [{v['rule']}] {v['test']}: {v['detail']}")
        print(
            f"living-record-lint: {report['files_scanned']} test files scanned, "
            f"{report['tests_evaluated']} tests evaluated "
            f"({len(report['exempted'])} exempt, {len(report['violations'])} violations, "
            f"{report['snapshot_reads']} snapshot reads)"
        )
    if report["violations"]:
        return 1
    if report["files_scanned"] == 0 or report["tests_evaluated"] == 0:
        print("living-record-lint: VACUOUS — no test files or no evaluated tests", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
