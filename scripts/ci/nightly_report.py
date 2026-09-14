#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Compose the nightly run report AND gate on the stage outcomes (CI.1).

The nightly workflow runs the composed e2e + the three scans with
``continue-on-error`` so every stage runs and reports even when an earlier one
failed — a report that only exists on green is exactly the wrong shape. This
script then writes ``nightly-report.md`` (uploaded as a workflow artifact
``if: always()``) and **exits non-zero if any stage outcome is not "success"** —
the report step is itself the gate, so a red nightly is loud, not silent.

Usage::

    nightly_report.py --out nightly-report.md [--log e2e=nightly-e2e.xml ...] \
        e2e=success secrets=failure licenses=success depaudit=success

Environment: ``GITHUB_RUN_ID``/``GITHUB_SHA``/``GITHUB_REPOSITORY`` are embedded
when present (CI) so the artifact is traceable back to its run.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

MAX_LOG_LINES = 40  # tail kept per stage — the artifact stays small and readable.


def _tail(path: Path, n: int = MAX_LOG_LINES) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return "(log unreadable)"
    if len(lines) > n:
        return f"(… {len(lines) - n} earlier lines omitted …)\n" + "\n".join(lines[-n:])
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="markdown report path")
    parser.add_argument(
        "--log",
        action="append",
        default=[],
        metavar="STAGE=PATH",
        help="embed the tail of a stage's log file in the report",
    )
    parser.add_argument(
        "outcomes",
        nargs="+",
        metavar="STAGE=OUTCOME",
        help="stage outcomes, e.g. e2e=success secrets=failure",
    )
    args = parser.parse_args(argv)

    stages: list[tuple[str, str]] = []
    for item in args.outcomes:
        if "=" not in item:
            print(f"nightly_report: malformed outcome {item!r} (want STAGE=OUTCOME)", file=sys.stderr)
            return 2
        name, outcome = item.split("=", 1)
        stages.append((name, outcome))

    logs: dict[str, Path] = {}
    for item in args.log:
        if "=" not in item:
            print(f"nightly_report: malformed --log {item!r}", file=sys.stderr)
            return 2
        name, path = item.split("=", 1)
        logs[name] = Path(path)

    failed = [name for name, outcome in stages if outcome != "success"]
    run_url = ""
    repo, run_id = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID")
    if repo and run_id:
        run_url = f"https://github.com/{repo}/actions/runs/{run_id}"
    sha = os.environ.get("GITHUB_SHA", "")

    lines = [
        "# SIG nightly report",
        "",
        f"- **Generated:** {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M:%SZ')} (UTC)",
        f"- **Run:** {run_url or '(local/manual)'}" + (f" @ `{sha[:12]}`" if sha else ""),
        f"- **Verdict:** {'GREEN — all stages passed' if not failed else 'RED — failed: ' + ', '.join(failed)}",
        "",
        "| stage | outcome |",
        "|---|---|",
        *[f"| {name} | {outcome} |" for name, outcome in stages],
        "",
    ]
    for name, path in logs.items():
        lines += [f"## {name}", "", "```", _tail(path), "```", ""]

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"nightly_report: wrote {args.out} — verdict {'GREEN' if not failed else 'RED (' + ', '.join(failed) + ')'}")

    # The report step IS the nightly gate: any failed stage turns the run red.
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
