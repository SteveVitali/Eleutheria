#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.41a (D1): the partitioned pytest runner the `python` CI job uses.

One serial `pytest` is the `python` job's long pole; this runner splits the
suite into the partitions the committed table `scripts/ci/pytest_partitions.txt`
names and launches one `pytest` process per partition, all at once. It adds no
dependency and changes no test. In the table each non-comment line is one
partition's whitespace-separated directories (each inside a
`[tool.pytest.ini_options] testpaths` entry); exactly one line is the single
token `*`, meaning "every testpaths entry minus the named directories".

`check` exits 0, or 2 with every reason on stderr: a named directory missing
or outside `testpaths`, a directory equal to or containing another, zero or
two `*` lines, no explicit line, or any other token. `run` runs `check`
first — a failure exits 2 and starts nothing — then launches every partition
at once: `$PYTEST_PARTITIONS_CMD` (default `uv run pytest`; the seam exists
only for this tool's self-tests and appears in neither `ci.yml` nor the
`Makefile`) plus `-p no:cacheprovider --basetemp <run>/p<k>` and the
partition's directories — or, for `*`, one `--ignore=<dir>` per named
directory plus the un-named testpaths entries. `<run>` is a fresh
`tempfile.mkdtemp(prefix="pytest-par-", dir=RUNNER_TEMP)` per invocation —
never a fixed name, because pytest deletes an existing `--basetemp`. The
environment is inherited unchanged. Each process writes stdout+stderr to its
own `p<k>.log` and its exit code to `p<k>.rc`. When all have ended, the logs
replay in partition order (`::group::` under GITHUB_ACTIONS), then a
one-line-per-partition summary (k, dirs, rc, seconds, pytest's final
`=… passed …=` line) plus `nproc=<os.cpu_count()>`.

Exit 0 only if every partition's recorded rc is 0 **and** its log holds
pytest's final summary line with at least one `passed` — no vacuous pass
(SIG-ENG-042): pytest's rc 5, a missing or unparsable rc file, a missing
summary line, or a runner crash all exit 1. It never retries.

Usage: `pytest_partitions.py check|run [--root DIR]` — `--root` (default: the
repo root) is where `pyproject.toml` and the table are read, so tests can
point it at a temporary tree. Python ≥ 3.11 (`tomllib`); run via `uv run`.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

STAR = "*"
PARTITION_FILE = Path("scripts/ci") / "pytest_partitions.txt"
DEFAULT_CMD = "uv run pytest"
_SUMMARY_LINE = re.compile(r"^=+.*\d+\s+passed\b.*=+\s*$")
_PASSED_COUNT = re.compile(r"(\d+)\s+passed")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _testpaths(root: Path) -> list[str]:
    cfg = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return list(cfg["tool"]["pytest"]["ini_options"]["testpaths"])


def _parse(root: Path) -> tuple[list[tuple[str, list[str]]], int, list[str]]:
    """Parse the table → ``(entries, star_count, problems)``; entries are
    ``("dirs", [tokens])`` / ``("star", [])`` in file order."""
    path = root / PARTITION_FILE
    entries: list[tuple[str, list[str]]] = []
    problems: list[str] = []
    star_count = 0
    if not path.is_file():
        return entries, star_count, [f"{PARTITION_FILE} is missing"]
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if tokens == [STAR]:
            star_count += 1
            entries.append(("star", []))
        elif STAR in tokens:
            problems.append(f"{PARTITION_FILE}:{lineno}: `{STAR}` must be its line's only token")
        else:
            entries.append(("dirs", tokens))
    return entries, star_count, problems


def check(root: Path) -> list[str]:
    """Validate the partition table; returns the violations (empty = valid)."""
    tp_resolved: list[tuple[str, Path]] = []
    problems: list[str] = []
    for tp in _testpaths(root):
        resolved = (root / tp).resolve()
        tp_resolved.append((tp, resolved))
        if not resolved.is_dir():
            problems.append(f"testpaths entry {tp!r} is not a directory under {root}")
    entries, star_count, problems = _parse(root)
    if star_count != 1:
        problems.append(f"exactly one `{STAR}` line required; found {star_count}")
    if not any(kind == "dirs" for kind, _ in entries):
        problems.append("at least one explicit partition line is required")
    named: list[tuple[str, Path]] = []
    for kind, tokens in entries:
        if kind != "dirs":
            continue
        for token in tokens:
            resolved = (root / token).resolve()
            if not resolved.is_dir():
                problems.append(f"{token!r} is not an existing directory under {root}")
                continue
            if not any(resolved == tp or tp in resolved.parents for _, tp in tp_resolved):
                problems.append(f"{token!r} lies outside every testpaths entry")
            named.append((token, resolved))
    for i, (tok_a, path_a) in enumerate(named):
        for tok_b, path_b in named[i + 1 :]:
            if path_a == path_b:
                problems.append(f"{tok_a!r} and {tok_b!r} name the same directory")
            elif path_a in path_b.parents or path_b in path_a.parents:
                problems.append(f"{tok_a!r} and {tok_b!r} nest — partitions must not overlap")
    return problems


def _final_summary_line(log_text: str) -> str | None:
    """Pytest's final ``=… passed …=`` line (last match wins), or None."""
    found = None
    for line in log_text.splitlines():
        if _SUMMARY_LINE.match(line.strip()):
            found = line.strip()
    return found


def _evaluate(run_dir: Path, metas: list[dict]) -> tuple[bool, list[dict]]:
    """Judge each partition from its rc file + log: rc 0 **and** a final
    ``=… passed …=`` line with ≥1 passed — every other shape (rc≠0 incl.
    pytest's 5, a missing/unparsable rc file, a missing summary) is red."""
    ok = True
    results: list[dict] = []
    for meta in metas:
        problems: list[str] = []
        rc: int | None = None
        try:
            rc = int((run_dir / meta["rc_name"]).read_text(encoding="utf-8").strip())
        except Exception:
            problems.append("missing or unparsable rc file")
        log_path = run_dir / meta["log_name"]
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        final = _final_summary_line(log_text)
        m = _PASSED_COUNT.search(final or "")
        passed = int(m.group(1)) if m else 0
        if rc is not None and rc != 0:
            problems.append(f"partition rc {rc}")
        if passed < 1:
            problems.append("no `passed` summary line (vacuous pass is red)")
        ok = ok and not problems
        results.append({**meta, "rc": rc, "passed": passed, "final": final, "problems": problems})
    return ok, results


def run(root: Path) -> int:
    """Validate, launch every partition at once, replay, summarise, judge."""
    problems = check(root)
    if problems:
        for problem in problems:
            print(f"pytest_partitions: {problem}", file=sys.stderr)
        return 2

    entries, _, _ = _parse(root)
    named = [tok for kind, toks in entries if kind == "dirs" for tok in toks]
    named_resolved = {(root / tok).resolve() for tok in named}
    star_testpaths = [tp for tp in _testpaths(root) if (root / tp).resolve() not in named_resolved]
    run_dir = Path(tempfile.mkdtemp(prefix="pytest-par-", dir=os.environ.get("RUNNER_TEMP")))
    base = shlex.split(os.environ.get("PYTEST_PARTITIONS_CMD", DEFAULT_CMD))

    metas: list[dict] = []
    for k, (kind, tokens) in enumerate(entries, 1):
        args = [*base, "-p", "no:cacheprovider", "--basetemp", str(run_dir / f"p{k}")]
        if kind == "star":
            args += [f"--ignore={d}" for d in named] + star_testpaths
            label = "* (testpaths minus the named directories)"
        else:
            args += tokens
            label = " ".join(tokens)
        metas.append(
            {
                "k": k,
                "label": label,
                "log_name": f"p{k}.log",
                "rc_name": f"p{k}.rc",
                "seconds": None,
                "proc": None,
                "logf": None,
                "args": args,
            }
        )

    start = time.monotonic()
    launch_failed = False
    for meta in metas:
        try:
            meta["logf"] = open(run_dir / meta["log_name"], "wb")
            meta["proc"] = subprocess.Popen(
                meta["args"], cwd=root, stdout=meta["logf"], stderr=subprocess.STDOUT
            )
        except Exception as exc:  # a crashed launch is red, never green
            launch_failed = True
            print(
                f"pytest_partitions: launch of partition {meta['k']} failed: {exc}",
                file=sys.stderr,
            )
            if meta["logf"] is not None:
                meta["logf"].close()

    pending = [m for m in metas if m["proc"] is not None]
    while pending:
        still: list[dict] = []
        for meta in pending:
            rc = meta["proc"].poll()
            if rc is None:
                still.append(meta)
                continue
            meta["seconds"] = time.monotonic() - start
            meta["logf"].close()
            (run_dir / meta["rc_name"]).write_text(f"{rc}\n", encoding="utf-8")
        pending = still
        if pending:
            time.sleep(0.2)

    gha = os.environ.get("GITHUB_ACTIONS") == "true"
    for meta in metas:
        header = f"partition {meta['k']}: {meta['label']}"
        print(f"::group::{header}" if gha else f"===== {header} =====")
        log_path = run_dir / meta["log_name"]
        if log_path.is_file():
            sys.stdout.write(log_path.read_text(encoding="utf-8", errors="replace"))
            sys.stdout.flush()
        else:
            print(f"<no log at {log_path}>")
        if gha:
            print("::endgroup::")

    ok, results = _evaluate(run_dir, metas)
    print(f"pytest-par summary (run dir {run_dir}):")
    for res in results:
        seconds = f"{res['seconds']:.1f}s" if res["seconds"] is not None else "n/a"
        rc = res["rc"] if res["rc"] is not None else "missing"
        final = res["final"] or "<no `passed` summary line>"
        flags = f"  FAIL: {'; '.join(res['problems'])}" if res["problems"] else ""
        print(f"  partition {res['k']} [{res['label']}] rc={rc} {seconds} — {final}{flags}")
    print(f"nproc={os.cpu_count()}")
    return 0 if (ok and not launch_failed) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pytest_partitions.py")
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument(
        "--root",
        type=Path,
        default=_repo_root(),
        help="tree holding pyproject.toml and the table (default: the repo root)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "check":
            problems = check(root)
            for problem in problems:
                print(f"pytest_partitions: {problem}", file=sys.stderr)
            return 0 if not problems else 2
        return run(root)
    except Exception as exc:  # a crash of the runner itself is red
        print(f"pytest_partitions: runner crashed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
