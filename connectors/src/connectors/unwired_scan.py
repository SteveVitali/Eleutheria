# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The mechanical unwired-function scan (P37.5a; F2a-verdicts.md §6.5, F5 PKG-12).

A "public function with only test callers" is the built-but-unwired class the
ingestion-hardening audit exists to find: a module shipped and tested, never
reached by any production path. The scan is deliberately mechanical and
import-resolved but **conservative**:

* **Candidates** — top-level ``def``/``class`` names in a scanned package's
  ``src`` tree that do not start with ``_`` (nested defs and methods are out;
  they are reached only through their public container).
* **References** — import-resolved uses anywhere else in the repo's ``src``
  trees, ``tests/``, ``scripts/`` and ``docs/build/tools/``: a
  ``from <mod> import <name>`` binding (aliased or not), an ``import <mod>`` +
  ``<mod>.<name>`` chain, a ``from <pkg> import <submod>`` submodule handle, or
  a name the package's own ``__init__.py`` re-exports (a re-export propagates
  the name onto the package; it is never itself a caller).
* **A finding** — a candidate whose every reference lives under ``tests/``.
  A reference inside the **defining file counts** as wiring: a helper the
  module's own connector class calls is reachable through the connector, so
  the scan reports the *top* of each unwired cluster (a public surface whose
  whole subtree is test-only), not every helper under it.

The scan **under-approximates** on purpose: dynamic lookups (``getattr``, the
connector name registry's string keys, CLI-arg dispatch) and same-named
attributes on unrelated objects can mask real usage, so a finding is an *audit
row to adjudicate*, never a proof of deadness — the committed baseline
(``data/unwired_scan_baseline.toml``) records each finding's disposition (a
named seam owner, an honest-absence note, or a wiring fix), and the ratchet
test fails when the set drifts either way.
"""

from __future__ import annotations

import ast
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The ingestion-stack packages this audit scans (P37.5a scope). The F2a §6.5
#: named suspects outside the stack (``reconcile.lifecycle``,
#: ``evidence.redaction``, ``policy.crawler``) keep their own owners — the
#: report records them as adjudicated elsewhere, never silently re-scoped.
SCAN_PACKAGES: tuple[str, ...] = ("connectors", "parsing")

#: Non-``src`` trees searched for callers. ``tests/`` is counted separately:
#: a name whose only referers live there is exactly the unwired class.
CALLER_TREES_PROD: tuple[str, ...] = ("scripts", "docs/build/tools")


def repo_root() -> Path:
    """The workspace root (``<repo>/connectors/src/connectors/unwired_scan.py``)."""
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Candidate:
    """A public module-level def/class in a scanned package."""

    module: str  # dotted module path, e.g. "connectors.replay"
    name: str
    kind: str  # "function" | "class"
    path: str  # repo-relative defining file
    line: int

    @property
    def key(self) -> str:
        return f"{self.module}.{self.name}"


@dataclass(frozen=True)
class Finding:
    """A candidate plus its referer sets — one audit row."""

    candidate: Candidate
    #: Repo-relative non-test referer files (the wiring evidence).
    prod_referers: tuple[str, ...]
    #: Repo-relative test referer files.
    test_referers: tuple[str, ...]

    @property
    def unwired(self) -> bool:
        """Only-test-callers: no non-test referer outside the defining file."""
        return not self.prod_referers


def _iter_public_defs(path: Path, module: str, rel: str, out: list[Candidate]) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "function"
        elif isinstance(node, ast.ClassDef):
            kind = "class"
        else:
            continue
        if node.name.startswith("_"):
            continue
        out.append(Candidate(module=module, name=node.name, kind=kind, path=rel, line=node.lineno))


def _package_module(src_root: Path, package: str, path: Path) -> str:
    rel = path.relative_to(src_root).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join((package, *parts))


def candidates(repo: Path, packages: tuple[str, ...] = SCAN_PACKAGES) -> list[Candidate]:
    """Every public top-level def/class in the scanned packages' src trees."""
    out: list[Candidate] = []
    for package in packages:
        pkg_dir = repo / package / "src" / package
        if not pkg_dir.is_dir():
            continue
        for path in sorted(pkg_dir.rglob("*.py")):
            rel = path.relative_to(repo).as_posix()
            _iter_public_defs(path, _package_module(pkg_dir, package, path), rel, out)
    return out


def _file_module(repo: Path, path: Path) -> str | None:
    """The dotted module of a ``<pkg>/src/<pkg>/…`` source file, else ``None``."""
    rel = path.relative_to(repo)
    if len(rel.parts) < 3 or rel.parts[1] != "src":
        return None
    package, rest = rel.parts[0], rel.parts[2:]
    if not rest or rest[0] != package:
        return None
    parts = [p for p in rest[1:] if p != "__init__.py"]
    stem = [p[:-3] if p.endswith(".py") else p for p in parts]
    return ".".join((package, *stem))


def _import_base(file_module: str | None, level: int, *, is_init: bool = False) -> str:
    """The package a ``from <level dots><mod> import …`` is relative to.

    level=1 → the file's own package. For a regular module the package drops
    the module's own name (``pack.cli`` → ``pack``); for ``__init__.py`` the
    module IS the package (``pack`` → ``pack``).
    """
    if file_module is None:
        return ""
    parts = file_module.split(".")
    drop = level if not is_init else level - 1
    keep = len(parts) - drop
    if keep <= 0:
        return ""
    return ".".join(parts[:keep])


@dataclass
class _FileIndex:
    """One file's resolved import bindings and name usage."""

    #: ``alias → dotted module`` usable as ``alias.<attr>`` (``import a.b``,
    #: ``import a.b as x``, and ``from a import b`` when ``b`` may be a
    #: submodule — both readings are kept).
    module_aliases: dict[str, str]
    #: ``local → (module, orig_name)`` for ``from <mod> import <orig> as <local>``.
    imported_names: dict[str, tuple[str, str]]
    #: ``"a.b.c"`` attribute chains anywhere in the file.
    chains: set[str]
    #: bare ``Name`` loads.
    names: set[str]


def _index_file(repo: Path, path: Path) -> _FileIndex | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None
    file_mod = _file_module(repo, path)
    module_aliases: dict[str, str] = {}
    imported_names: dict[str, tuple[str, str]] = {}
    chains: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                target = alias.name if alias.asname else alias.name.split(".")[0]
                module_aliases[bound] = target
        elif isinstance(node, ast.ImportFrom):
            # level=0 is an absolute import — the file's own package never
            # enters the resolution.
            base = (
                _import_base(file_mod, node.level, is_init=path.name == "__init__.py")
                if node.level
                else ""
            )
            if node.module:
                mod = f"{base}.{node.module}".strip(".")
            else:
                mod = base
            if not mod:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                imported_names[local] = (mod, alias.name)
                # `from a import b` may bind the submodule a.b — keep both
                # readings so `b.<name>` chains resolve either way.
                module_aliases.setdefault(local, f"{mod}.{alias.name}")
        elif isinstance(node, ast.Attribute):
            parts = [node.attr]
            cur = node.value
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
                chains.add(".".join(reversed(parts)))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return _FileIndex(
        module_aliases=module_aliases, imported_names=imported_names, chains=chains, names=names
    )


def _reexport_map(
    file_index: _FileIndex | None, file_module: str | None, is_init: bool
) -> dict[tuple[str, str], tuple[str, str]]:
    """A package ``__init__.py``'s re-exports: ``(pkg, local) → (mod, orig)``."""
    if file_index is None or file_module is None or not is_init:
        return {}
    out: dict[tuple[str, str], tuple[str, str]] = {}
    for local, (mod, orig) in file_index.imported_names.items():
        if mod.startswith(f"{file_module}.") or mod == file_module:
            out[(file_module, local)] = (mod, orig)
    return out


def _referenced(
    idx: _FileIndex, reexports: dict[tuple[str, str], tuple[str, str]], cand: Candidate
) -> bool:
    """Whether this file's index references ``cand`` (import-resolved)."""
    full = f"{cand.module}.{cand.name}"
    if full in idx.chains:
        return True
    for local, (mod, orig) in idx.imported_names.items():
        if (mod, orig) == (cand.module, cand.name) and local in idx.names:
            return True
        # `from pkg import name` where pkg.__init__ re-exported mod.name.
        if reexports.get((mod, orig)) == (cand.module, cand.name) and local in idx.names:
            return True
        # `from a import b` where b IS the module: `b.<name>` chains.
        if f"{mod}.{orig}" == cand.module and f"{local}.{cand.name}" in idx.chains:
            return True
    for alias, mod in idx.module_aliases.items():
        if mod == cand.module and f"{alias}.{cand.name}" in idx.chains:
            return True
    return False


def _caller_files(repo: Path) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]]]:
    """``(prod, tests)`` caller files as ``(path, repo-relative)`` pairs."""
    prod: list[tuple[Path, str]] = []
    for child in sorted(repo.iterdir()):
        src = child / "src"
        if src.is_dir():
            for path in sorted(src.rglob("*.py")):
                prod.append((path, path.relative_to(repo).as_posix()))
    for tree in CALLER_TREES_PROD:
        root = repo / tree
        if root.is_dir():
            for path in sorted(root.rglob("*.py")):
                prod.append((path, path.relative_to(repo).as_posix()))
    tests: list[tuple[Path, str]] = []
    tests_root = repo / "tests"
    if tests_root.is_dir():
        for path in sorted(tests_root.rglob("*.py")):
            tests.append((path, path.relative_to(repo).as_posix()))
    return prod, tests


def scan(*, repo: Path | None = None, packages: tuple[str, ...] = SCAN_PACKAGES) -> list[Finding]:
    """Run the scan; one :class:`Finding` per public name, filtered to unwired.

    A candidate is *wired* the moment one non-test file — its own module
    included — references it; it is *unwired* when its only referers live
    under ``tests/``. Returns findings sorted by key.
    """
    repo = (repo or repo_root()).resolve()
    cands = candidates(repo, packages)
    prod_files, test_files = _caller_files(repo)

    # Pass 1: index every caller file once and merge every package
    # `__init__.py`'s re-exports into one global map — a `from pkg import f`
    # in a consumer resolves through the re-export the package declared.
    indexed: dict[str, _FileIndex] = {}
    reexports: dict[tuple[str, str], tuple[str, str]] = {}
    for path, rel in (*prod_files, *test_files):
        idx = _index_file(repo, path)
        if idx is None:
            continue
        indexed[rel] = idx
        reexports.update(_reexport_map(idx, _file_module(repo, path), path.name == "__init__.py"))

    prod_referers: dict[str, set[str]] = {c.key: set() for c in cands}
    test_referers: dict[str, set[str]] = {c.key: set() for c in cands}

    for files, referers in ((prod_files, prod_referers), (test_files, test_referers)):
        for _path, rel in files:
            idx = indexed.get(rel)
            if idx is None:
                continue
            for cand in cands:
                if cand.path == rel:
                    # The defining file wires a name when it uses it as a bare
                    # `Name` (a module-level helper the connector's own
                    # methods call, an annotation, a decorator argument…).
                    if cand.name in idx.names:
                        referers[cand.key].add(rel)
                    continue
                if _referenced(idx, reexports, cand):
                    referers[cand.key].add(rel)

    findings = [
        Finding(
            candidate=cand,
            prod_referers=tuple(sorted(prod_referers[cand.key])),
            test_referers=tuple(sorted(test_referers[cand.key])),
        )
        for cand in cands
        if not prod_referers[cand.key]
    ]
    findings.sort(key=lambda f: f.candidate.key)
    return findings


@dataclass(frozen=True)
class BaselineEntry:
    """One committed baseline row: the finding plus its recorded disposition."""

    key: str
    disposition: str
    owner: str = ""
    note: str = ""


@dataclass(frozen=True)
class Baseline:
    """The committed adjudicated set (``data/unwired_scan_baseline.toml``)."""

    entries: tuple[BaselineEntry, ...] = ()

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(e.key for e in self.entries)

    def entry_for(self, key: str) -> BaselineEntry | None:
        return next((e for e in self.entries if e.key == key), None)


def baseline_path(repo: Path | None = None) -> Path:
    repo = (repo or repo_root()).resolve()
    return repo / "connectors" / "src" / "connectors" / "data" / "unwired_scan_baseline.toml"


def load_baseline(path: Path | None = None) -> Baseline:
    """Load the committed adjudicated baseline (fail-closed on a bad row)."""
    path = path or baseline_path()
    if not path.exists():
        return Baseline()
    table = tomllib.loads(path.read_text(encoding="utf-8"))
    entries: list[BaselineEntry] = []
    for i, row in enumerate(table.get("finding", [])):
        key = str(row.get("key", "")).strip()
        disposition = str(row.get("disposition", "")).strip()
        if not key or not disposition:
            raise ValueError(
                f"unwired baseline row {i}: 'key' and 'disposition' are required "
                "(a finding without a recorded adjudication is not adjudicated)"
            )
        entries.append(
            BaselineEntry(
                key=key,
                disposition=disposition,
                owner=str(row.get("owner", "")).strip(),
                note=str(row.get("note", "")).strip(),
            )
        )
    keys = [e.key for e in entries]
    if len(keys) != len(set(keys)):
        raise ValueError("unwired baseline carries a duplicate 'key'")
    return Baseline(entries=tuple(entries))


def baseline_drift(findings: list[Finding], baseline: Baseline) -> dict[str, list[str]]:
    """The loud drift between the live scan and the committed adjudication.

    ``new`` = unwired names with no baseline row (a new unwired function must
    be wired or adjudicated in the same change — never silently added).
    ``resolved`` = baseline keys the scan no longer reports (a wiring fix or a
    removal; the baseline is regenerated in the same change).
    ``unchanged`` = still-open findings whose disposition stands.
    """
    current = {f.candidate.key for f in findings}
    committed = baseline.keys
    return {
        "new": sorted(current - committed),
        "resolved": sorted(committed - current),
        "unchanged": sorted(current & committed),
    }


def report(findings: list[Finding], baseline: Baseline | None = None) -> dict[str, Any]:
    """The ``sig.unwired-scan/1`` report shape the CLI prints and the record renders."""
    rows = []
    for f in findings:
        entry = baseline.entry_for(f.candidate.key) if baseline else None
        rows.append(
            {
                "key": f.candidate.key,
                "kind": f.candidate.kind,
                "path": f.candidate.path,
                "line": f.candidate.line,
                "test_referers": list(f.test_referers),
                "disposition": entry.disposition if entry else "unadjudicated",
                "owner": entry.owner if entry else "",
                "note": entry.note if entry else "",
            }
        )
    rows.sort(key=lambda r: str(r["key"]))
    return {
        "sig.unwired-scan/1": {
            "packages": list(SCAN_PACKAGES),
            "findings": len(rows),
            "rows": rows,
            "drift": (
                baseline_drift(findings, baseline)
                if baseline is not None
                else {"new": [], "resolved": [], "unchanged": sorted(r["key"] for r in rows)}
            ),
        }
    }


def render_json(findings: list[Finding], baseline: Baseline | None = None) -> str:
    return json.dumps(report(findings, baseline), indent=2, sort_keys=True) + "\n"


__all__ = [
    "Baseline",
    "BaselineEntry",
    "Candidate",
    "Finding",
    "SCAN_PACKAGES",
    "baseline_drift",
    "baseline_path",
    "candidates",
    "load_baseline",
    "render_json",
    "repo_root",
    "report",
    "scan",
]
