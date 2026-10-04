#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Bump every version source together (SIG-REL-014, P34.23; G3 §9.3).

One version source means one *bump*: this script rewrites the ``[project]
version`` line of all 14 workspace-member ``pyproject.toml`` files and the
``"version"`` field of ``web/package.json`` to the same ``x.y.z``. Every
package's ``__version__`` derives from its installed distribution metadata,
so the pyproject bump is the only edit needed — run ``uv sync`` (and
``make gen`` for the lock export) afterwards so the metadata catches up.

Used in the stack PR that precedes an operator tag (G3 §9.2): the agent
bumps the versions + updates the CHANGELOG section; the operator places the
annotated tag on ``main``. Agents never tag or push ``main``.

Dry-run is the default — it prints every planned change and writes nothing.
``--apply`` writes. ``0.0.0`` is refused outright (SIG-REL-014: no package
may report it), as is any non-``x.y.z`` argument.

Usage::

    python3 scripts/bump_version.py 0.1.1             # dry run
    python3 scripts/bump_version.py 0.1.1 --apply     # write
    python3 scripts/bump_version.py 0.1.1 --root DIR  # operate on DIR (tests)

Exit codes: 0 ok · 1 a target file is missing or has no version line ·
2 usage / bad version.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

#: The 14 Python workspace members (the §47 layout + ADR-023's `evidence`) —
#: read live from the root pyproject's `tool.uv.workspace.members` so a new
#: member is bumped automatically. `web/` is not a member; it is added below.
PY_VERSION_RE = re.compile(r'^(version\s*=\s*")([^"]+)(".*)$')
JSON_VERSION_RE = re.compile(r'^(\s*"version"\s*:\s*")([^"]+)(".*)$')
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _workspace_members(root: Path) -> list[str]:
    with (root / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return list(data["tool"]["uv"]["workspace"]["members"])


def _bump_pyproject(path: Path, new: str, apply: bool) -> tuple[str, str] | None:
    """Bump the ``[project] version`` line; returns (old, new) or None."""
    if not path.is_file():
        print(f"bump_version: missing {path}", file=sys.stderr)
        return None
    lines = path.read_text(encoding="utf-8").split("\n")
    in_project = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
            continue
        if in_project:
            m = PY_VERSION_RE.match(line)
            if m:
                old = m.group(2)
                if apply and old != new:
                    lines[i] = f"{m.group(1)}{new}{m.group(3)}"
                    path.write_text("\n".join(lines), encoding="utf-8")
                return (old, new)
    print(f"bump_version: no [project] version line in {path}", file=sys.stderr)
    return None


def _bump_package_json(path: Path, new: str, apply: bool) -> tuple[str, str] | None:
    """Bump ``web/package.json``'s ``"version"`` field (line-preserving)."""
    if not path.is_file():
        print(f"bump_version: missing {path}", file=sys.stderr)
        return None
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    old = str(data.get("version", ""))
    if not old:
        print(f'bump_version: no "version" field in {path}', file=sys.stderr)
        return None
    if apply and old != new:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            m = JSON_VERSION_RE.match(line)
            if m:
                lines[i] = f"{m.group(1)}{new}{m.group(3)}"
                break
        path.write_text("\n".join(lines), encoding="utf-8")
    return (old, new)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bump_version.py",
        description="Bump all 14 pyprojects + web/package.json to one x.y.z "
        "(SIG-REL-014). Dry-run unless --apply.",
    )
    parser.add_argument("version", help="the new x.y.z version (never 0.0.0)")
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry-run)")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root to operate on (default: this repo)",
    )
    args = parser.parse_args(argv)

    if not SEMVER_RE.match(args.version):
        print(
            f"bump_version: {args.version!r} is not x.y.z semver (0.0.0 is refused)",
            file=sys.stderr,
        )
        return 2
    if args.version == "0.0.0":
        print(
            "bump_version: 0.0.0 is refused — no package may report it (SIG-REL-014)",
            file=sys.stderr,
        )
        return 2

    root: Path = args.root
    members = _workspace_members(root)
    targets = [(root / m / "pyproject.toml", "py") for m in members]
    targets.append((root / "web" / "package.json", "json"))

    mode = "APPLY" if args.apply else "dry-run"
    failures = 0
    changed = 0
    for path, kind in targets:
        result = (
            _bump_pyproject(path, args.version, args.apply)
            if kind == "py"
            else _bump_package_json(path, args.version, args.apply)
        )
        if result is None:
            failures += 1
            continue
        old, new = result
        mark = "rewrite" if old != new else "already"
        if old != new:
            changed += 1
        print(f"{mode} {mark}: {path.relative_to(root)}: {old} -> {new}")

    if failures:
        print(f"bump_version: {failures} target(s) failed", file=sys.stderr)
        return 1
    print(
        f"bump_version: {len(targets)} files checked, {changed} "
        f"{'written' if args.apply else 'would change'}"
    )
    if args.apply:
        print(
            "next: `uv sync` (installed metadata), `make gen` (pylock.toml), "
            "CHANGELOG [Unreleased] -> [x.y.z] at tag time",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
