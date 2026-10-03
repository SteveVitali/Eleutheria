#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""handle_crawl_check.py — the P34.18 handle-crawl (ADR-178, SIG-PUB-002, TS-04/TS-06).

Scans the repository tip and any given build/export/tiles trees for the retired
personal-handle identifiers recorded in the gitignored C3 list
(``docs/build/logs/next-phase/C3/personal_like_ids.txt``). Counts only — the
check never prints a handle, a matched token, or a file's matched line.

Hit classes (the ADR's public-vs-retained split):

* ``functional`` — identifiers that feed the public surface: registry data
  (``connectors/**/data``), runner/cadence config (``ops/cadence.toml``,
  ``docs/build/tools/p2616_batch.py``), web source (``web/src``), test fixtures
  (``tests/``, ``fixtures/``), and every scanned build/export/tiles tree.
  Any hit here fails the check.
* ``retained`` — records that legitimately keep historical strings: landed ADRs
  (``docs/adr`` — append-only, OD-20 discloses them), ticket contracts
  (``docs/tickets``), committed run/research records (``docs/build/runs``,
  ``docs/build/reports``, ``docs/research``), and the OCFL evidence store.
  Hits are counted and reported, never failed — that is the disclosed residue.
* ``other`` — everything else (code, docs). Counted; fails too, because an
  unclassifiable public hit is not a documented retention.

Live closure (bucket listing + the deployed site) is P34.47's; this check runs
against the repo tip and the local trees it is pointed at. Stdlib only.

Usage::

    python3 docs/build/tools/handle_crawl_check.py
    python3 docs/build/tools/handle_crawl_check.py --export-dir build/export --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_HANDLE_LIST = ROOT / "docs/build/logs/next-phase/C3/personal_like_ids.txt"

#: Path prefixes (repo-relative) whose hits are legitimately retained records —
#: landed ADRs and ticket contracts (append-only), committed run/report/PR
#: records, the recorded planning corpus (the C3 findings evidence itself),
#: recorded live-run outputs, and the OCFL evidence store. Rewriting any of
#: these would falsify the audit trail; OD-20's dated correction note is the
#: honest disclosure instead.
RETAINED_PREFIXES = (
    "docs/adr/",
    "docs/tickets/",
    "docs/build/runs/",
    "docs/build/reports/",
    "docs/build/planning/",
    "docs/build/pr/",
    "docs/research/",
    "live_runs/",
    "evidence/",
)

#: Paths never scanned at all (gitignored inputs and VCS internals).
SKIP_PREFIXES = (
    ".git/",
    "docs/build/logs/",
    "node_modules/",
    "web/node_modules/",
    "web/dist/",
    ".venv/",
    "__pycache__/",
)


def load_handles(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # The list may carry `camreg_<handle>` ids; keep them whole — a prefix
        # scan would over-match functional ids like `camreg_und_…`.
        out.append(line)
    return out


def classify(rel: str) -> str:
    if any(rel.startswith(p) for p in RETAINED_PREFIXES):
        return "retained"
    return "functional"


def scan_file(path: pathlib.Path, handles: list[str]) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return 0
    hits = 0
    for h in handles:
        hits += data.count(h.encode("utf-8"))
    return hits


def tracked_files(root: pathlib.Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [p for p in out.stdout.splitlines() if p.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="handle_crawl_check")
    ap.add_argument("--root", default=str(ROOT), help="repo root (tip scan)")
    ap.add_argument("--handle-list", default=str(DEFAULT_HANDLE_LIST))
    ap.add_argument("--export-dir", action="append", default=[])
    ap.add_argument("--tiles-dir", action="append", default=[])
    ap.add_argument("--build-dir", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root)
    handles = load_handles(pathlib.Path(args.handle_list))
    if not handles:
        print("handle_crawl_check: handle list absent — check not runnable")
        return 2

    counts = {"functional": 0, "retained": 0, "other": 0}
    files = {"functional": 0, "retained": 0, "other": 0}

    # 1. The repository tip (tracked files only — untracked scratch is not
    #    "the repository"; git HISTORY is retained-by-design per OD-20).
    #    Paths are scanned too: a directory or filename that carries a handle
    #    repeats it in every repo listing.
    for rel in tracked_files(root):
        if any(rel.startswith(p) for p in SKIP_PREFIXES):
            continue
        cls = classify(rel)
        hits = scan_file(root / rel, handles)
        hits += sum(rel.count(h) for h in handles)
        if not hits:
            continue
        counts[cls] += hits
        files[cls] += 1

    # 2. Pointed-at trees (export, tiles, build). Every hit there is
    #    functional by definition — those trees feed the public surface.
    for opt in ("export_dir", "tiles_dir", "build_dir"):
        for d in getattr(args, opt):
            dpath = pathlib.Path(d)
            if not dpath.is_dir():
                continue
            for f in sorted(dpath.rglob("*")):
                if not f.is_file():
                    continue
                hits = scan_file(f, handles)
                if hits:
                    counts["functional"] += hits
                    files["functional"] += 1

    verdict = "pass" if counts["functional"] == 0 and counts["other"] == 0 else "fail"
    report = {
        "verdict": verdict,
        "handles_checked": len(handles),
        "hits": counts,
        "files_with_hits": files,
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"handle_crawl_check: {verdict}")
        for cls in ("functional", "other", "retained"):
            print(f"  {cls}: {counts[cls]} hits in {files[cls]} files")
        print("  (counts only; matched strings are never printed)")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
