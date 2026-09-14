#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tracked-file secret scan (CI.1 / GL-CI-01, ADR-078).

A zero-cost, deterministic, offline secret gate: scans every tracked file for
high-confidence credential shapes and exits non-zero on any hit. This is the
CI-front-door complement to the two checks that already exist:

* ``tests/connectors/test_secrets.py`` — no ``SIG_*`` token *literal* in
  ``.py``/``.toml`` (HG-09, RISK-P21-05) and ``.env*`` gitignored;
* ``scripts/docs/check-build-memory.sh`` — the same token shapes under
  ``docs/build``/``docs/tickets`` (BM-VALID-01).

This scanner covers **every tracked file** (workflows, shell, docs, fixtures)
with a superset of the build-memory shape set — a secret committed to a tracked
file is a permanent leak (append-only, P1–P3), so the gate runs on every PR,
not just nightly.

Usage::

    uv run python scripts/ci/secret_scan.py            # scan all tracked files
    uv run python scripts/ci/secret_scan.py PATH ...   # scan explicit files/dirs

Exit codes: 0 clean · 1 findings · 2 usage/environment error. Findings name the
file:line and the rule id — **never the matched text** (a scanner that echoes
the secret into the log is itself a leak).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# High-confidence credential shapes. A superset of the build-memory validator's
# grep set (AKIA…/sk-…/ghp_…/PEM/xox…) plus the other GitHub token prefixes, the
# Google API-key shape, and the repo's own SIG_* env-credential literal (the
# .py/.toml half is already gated by tests/connectors/test_secrets.py — this
# covers every other file type). All rules are deliberately *shape* rules: they
# fire on credential-shaped literals, never on env-var *names* or reads.
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "github-token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}"),
    ),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("pem-private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----")),
    # A repo env credential assigned a string literal — in ANY file type. The
    # `SIG_SECRET_*` prefix is carved out: by the P24.1 convention those vars
    # hold Secret Manager secret *names* (references, never values — see
    # ops/gcp/config.sh), so a literal there is a name, not a credential.
    ("sig-credential-literal", re.compile(r"SIG_(?!SECRET_)[A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)\s*[:=]\s*[\"'][^\"']{8,}")),
]

MAX_BYTES = 1 << 20  # 1 MiB — same per-file ceiling the build-memory scan uses.
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv"}


def _tracked_files(root: Path) -> list[Path]:
    """Every tracked file under ``root`` (``git ls-files`` — untracked scratch is out)."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    return [root / p for p in proc.stdout.decode().split("\0") if p]


def _expand(paths: list[Path]) -> list[Path]:
    """Expand explicit path args into files (dirs walked recursively)."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(
                f
                for f in p.rglob("*")
                if f.is_file() and not any(part in SKIP_PARTS for part in f.parts)
            )
        elif p.is_file():
            files.append(p)
        else:
            print(f"secret_scan: no such path: {p}", file=sys.stderr)
    return files


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return b"\x00" in fh.read(8192)
    except OSError:
        return True


def _scan_file(path: Path) -> list[tuple[int, str]]:
    """Return ``(lineno, rule_id)`` findings; the matched text is never kept."""
    try:
        if path.stat().st_size > MAX_BYTES or _is_binary(path):
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern in RULES:
            if pattern.search(line):
                findings.append((lineno, rule_id))
    return findings


def main(argv: list[str]) -> int:
    if argv:
        root = Path.cwd()
        files = _expand([Path(a) for a in argv])
    else:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        if proc.returncode != 0:
            print("secret_scan: not inside a git work tree", file=sys.stderr)
            return 2
        root = Path(proc.stdout.strip())
        files = _tracked_files(root)

    findings: list[str] = []
    scanned = 0
    for path in files:
        scanned += 1
        for lineno, rule_id in _scan_file(path):
            try:
                shown = path.relative_to(root)
            except ValueError:
                shown = path
            findings.append(f"{shown}:{lineno}: {rule_id}")

    if findings:
        print(f"secret_scan: {len(findings)} credential-shaped hit(s) in {scanned} file(s):", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        print("Remove the literal; credentials are environment-only (HG-09).", file=sys.stderr)
        return 1
    print(f"secret_scan: clean — {scanned} file(s) scanned, 0 credential shapes found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
