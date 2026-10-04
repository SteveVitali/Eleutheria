#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""CHANGELOG discipline gate — `changelog-gate/1` (SIG-REL-014, P34.23; G3 §9.4).

A public-behaviour change cannot merge without a CHANGELOG entry: a change
(a PR range) that touches any of the public-behaviour path set must also
change ``CHANGELOG.md``, unless at least one commit in the range carries a
``Changelog: none (<reason>)`` trailer.

**The path set** (G3 §9.4, verbatim):

- ``web/src/pages/**``, ``web/src/layouts/**``
- ``api/src/api/{routes,app,models}.py``
- ``exports/src/exports/{release*,spine_export,manifest}.py``
- ``ops/public_routes.toml``, ``ops/disclosures.toml``
- ``policy/**``, ``ontology/src/**``

**The trailer.** ``Changelog: none (<reason>)`` — read from the commit
message's **final paragraph**, the same lenient trailer grammar as
``check_trailers.py``; a quoted mention in the body does not count, and an
empty ``()`` reason does not count (a declared skip must say why).

Usage::

    changelog_gate.py --range BASE..HEAD | --range BASE...HEAD [--json PATH] [--repo DIR]

``BASE...HEAD`` (a PR: judged from the merge base) and ``BASE..HEAD`` both
judge the commits reachable from HEAD and not from BASE; the changed-file
set is the matching ``git diff`` name-only list.

Exit codes: 0 pass (no public path touched, CHANGELOG.md changed, or the
trailer present) · 1 violation · 2 usage · 3 vacuous (the range holds no
commit) · 5 unknown (unresolvable revision, git failure) — never green.
Python 3.9+, stdlib and `git` only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "changelog-gate/1"
EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_VACUOUS, EXIT_UNKNOWN = 0, 1, 2, 3, 5

CHANGELOG = "CHANGELOG.md"

#: The public-behaviour path set (G3 §9.4). A PR touching any of these owes
#: a CHANGELOG entry or a `Changelog: none (<reason>)` trailer.
_EXACT_PATHS = frozenset(
    {
        "api/src/api/routes.py",
        "api/src/api/app.py",
        "api/src/api/models.py",
        "exports/src/exports/spine_export.py",
        "exports/src/exports/manifest.py",
        "ops/public_routes.toml",
        "ops/disclosures.toml",
    }
)
_PREFIXES = (
    "web/src/pages/",
    "web/src/layouts/",
    "policy/",
    "ontology/src/",
)
_RELEASE_GLOB_RE = re.compile(r"^exports/src/exports/release[^/]*\.py$")

TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)[ \t]*:[ \t]*(.*?)\s*$")
CHANGELOG_NONE_RE = re.compile(r"^none\s*\(\s*([^)]*\S[^)]*)\)\s*$", re.S)


class Unknown(Exception):
    pass


def is_public_path(path: str) -> bool:
    """True when ``path`` is in the G3 §9.4 public-behaviour set."""
    if path in _EXACT_PATHS:
        return True
    if path.startswith(_PREFIXES):
        return True
    return bool(_RELEASE_GLOB_RE.match(path))


def final_paragraph(message: str) -> list[str]:
    """The message's last paragraph as logical lines (folded lines joined).

    Identical rule to ``check_trailers.final_paragraph``: a subject line
    alone has no trailer block.
    """
    paras = [p for p in re.split(r"\n[ \t]*\n", message.strip()) if p.strip()]
    if len(paras) < 2:
        return []
    lines: list[str] = []
    for raw in paras[-1].splitlines():
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += " " + raw.strip()
        else:
            lines.append(raw.rstrip())
    return lines


def changelog_trailer(message: str) -> str | None:
    """The ``Changelog: none (<reason>)`` trailer's reason, or None."""
    for line in final_paragraph(message):
        m = TRAILER_RE.match(line)
        if not m or m.group(1).lower() != "changelog":
            continue
        reason = CHANGELOG_NONE_RE.match(m.group(2))
        if reason:
            return reason.group(1).strip()
    return None


class Git:
    def __init__(self, repo: Path) -> None:
        self.repo = repo

    def run(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *args], capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise Unknown(
                f"git {' '.join(args[:3])} failed: {(proc.stderr or '').strip()[:200]}"
            )
        return proc.stdout


def evaluate(repo: Path, span: str) -> dict[str, Any]:
    """Judge ``span`` (BASE..HEAD or BASE...HEAD) under ``repo``."""
    if "..." in span:
        base, head = span.split("...", 1)
        two_dot = False
    elif ".." in span:
        base, head = span.split("..", 1)
        two_dot = True
    else:
        raise Unknown(f"bad range {span!r}")
    if not base or not head:
        raise Unknown(f"bad range {span!r}")

    git = Git(repo)
    git.run("rev-parse", "--verify", f"{base}^{{commit}}")
    git.run("rev-parse", "--verify", f"{head}^{{commit}}")
    if two_dot:
        commits = [c for c in git.run("rev-list", f"{base}..{head}").split() if c]
        files = [f for f in git.run("diff", "--name-only", base, head).split("\n") if f]
    else:
        mb = git.run("merge-base", base, head).strip()
        commits = [c for c in git.run("rev-list", f"{mb}..{head}").split() if c]
        files = [
            f for f in git.run("diff", "--name-only", mb, head).split("\n") if f
        ]
    if not commits:
        return {"verdict": "vacuous", "schema": SCHEMA, "range": span}

    public = sorted(p for p in files if is_public_path(p))
    changelog_changed = CHANGELOG in files
    trailer: dict[str, str] | None = None
    if public and not changelog_changed:
        for sha in commits:
            message = git.run("log", "-1", "--format=%B", sha)
            reason = changelog_trailer(message)
            if reason is not None:
                trailer = {"commit": sha[:12], "reason": reason[:120]}
                break

    verdict = "pass" if (not public or changelog_changed or trailer) else "fail"
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "range": span,
        "verdict": verdict,
        "commits": len(commits),
        "files_changed": len(files),
        "public_paths": public,
        "changelog_changed": changelog_changed,
    }
    if trailer:
        out["changelog_trailer"] = trailer
    if verdict == "fail":
        out["how_to_pass"] = (
            "add a CHANGELOG.md `## [Unreleased]` entry, or carry a "
            "`Changelog: none (<reason>)` trailer on a commit in the range"
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="changelog_gate.py")
    ap.add_argument("--range", dest="span", required=True, metavar="BASE..HEAD")
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    try:
        report = evaluate(args.repo.resolve(), args.span)
    except Unknown as exc:
        print(f"changelog_gate: unknown — {exc}", file=sys.stderr)
        return EXIT_UNKNOWN

    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if report["verdict"] == "vacuous":
        print(f"changelog_gate: vacuous — {args.span} holds no commit", file=sys.stderr)
        return EXIT_VACUOUS
    if report["verdict"] == "fail":
        print(
            f"changelog_gate: FAIL — public-behaviour paths touched without a "
            f"CHANGELOG.md change: {', '.join(report['public_paths'])}\n"
            f"  fix: {report['how_to_pass']}",
            file=sys.stderr,
        )
        return EXIT_FAIL
    detail = (
        "no public-behaviour path touched"
        if not report["public_paths"]
        else "CHANGELOG.md changed"
        if report["changelog_changed"]
        else f"Changelog trailer on {report['changelog_trailer']['commit']}"
    )
    print(f"changelog_gate: pass ({detail})")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
