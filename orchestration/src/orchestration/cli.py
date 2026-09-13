# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `orchestration` stage (SIG-ENG-013).

The scheduling seam (SCHED.1, GL-SCHED-01, ADR-076): the cadence sub-commands
decide **which** sources are due for a re-ingest and expose the append-only
freshness ledger, so a minimal scheduler (the GitHub Actions cron in
``.github/workflows/reingest.yml``) can loop the due list and call
``sig-connectors run`` per source — the run itself stays gated (a non-green source
is refused, exit 3) and polite (``PoliteFetcher``). The disappearance sweep cadence
is exposed alongside so the scheduler paces re-checks proportional to volatility.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from . import __version__


def _parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `orchestration` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-orchestration",
        description="SIG orchestration stage — re-ingest cadence & freshness (SCHED.1).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")

    p_due = sub.add_parser("due", help="list the source ids due for a re-ingest now")
    p_due.add_argument("--freshness-dir", default=None, help="freshness ledger directory")
    p_due.add_argument("--now", default=None, help="ISO time to evaluate against (default: now)")

    p_interval = sub.add_parser(
        "interval", help="print a source's re-ingest interval in days (cadence)"
    )
    p_interval.add_argument("--source", required=True)

    p_fresh = sub.add_parser("freshness", help="print the freshness ledger for a source")
    p_fresh.add_argument("--source", required=True)
    p_fresh.add_argument("--freshness-dir", default=None)

    p_rec = sub.add_parser("record", help="append a freshness record after a scheduled run")
    p_rec.add_argument("--source", required=True)
    p_rec.add_argument("--claims", type=int, default=0)
    p_rec.add_argument("--mode", default="scheduled")
    p_rec.add_argument("--freshness-dir", default=None)
    p_rec.add_argument("--now", default=None)

    p_sweep = sub.add_parser(
        "sweep-cadence", help="print the disappearance-detection sweep cadence in days"
    )
    p_sweep.add_argument("--volatility", default="MODERATE")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the `orchestration` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Import lazily so `--help`/`--version` don't pull the connector stack.
    from .cadence import (
        FRESHNESS_DIR,
        FreshnessLedger,
        FreshnessRecord,
        disappearance_sweep_days,
        due_sources,
        reingest_interval_days,
    )

    if args.command == "due":
        ledger = FreshnessLedger(args.freshness_dir or FRESHNESS_DIR)
        for source_id in due_sources(ledger, _parse_now(args.now)):
            print(source_id)
        return 0

    if args.command == "interval":
        print(reingest_interval_days(args.source))
        return 0

    if args.command == "freshness":
        ledger = FreshnessLedger(args.freshness_dir or FRESHNESS_DIR)
        for record in ledger.records_for(args.source):
            print(f"{record.ingested_at}\t{record.claim_count}\t{record.mode}")
        return 0

    if args.command == "record":
        ledger = FreshnessLedger(args.freshness_dir or FRESHNESS_DIR)
        record = FreshnessRecord(
            source_id=args.source,
            ingested_at=_parse_now(args.now).isoformat(),
            mode=args.mode,
            claim_count=args.claims,
        )
        path = ledger.record(record)
        print(str(path))
        return 0

    if args.command == "sweep-cadence":
        print(disappearance_sweep_days(args.volatility))
        return 0

    parser.print_help()
    return 0
