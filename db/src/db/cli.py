# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `db` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. The `analytics`
sub-command exposes the §18 analytics boundary: a data-quality gate that asserts
the analytics-store schema honours the bright line (no plate / no name column,
SIG-STORE-025/026/028), and a helper that prints the Hive partition path for a
`(audit_source_type, period)` (SIG-STORE-027).
"""

from __future__ import annotations

import argparse

from . import __version__
from .analytics import (
    ANALYTICS_COLUMNS,
    assert_analytics_schema,
    partition_relative_path,
)


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `db` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-db",
        description="SIG db stage: the claim spine and the §18 analytics boundary.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")

    analytics = sub.add_parser(
        "analytics",
        help="the §18 analytics boundary (Hive-partitioned Parquet on DuckDB)",
    )
    analytics_sub = analytics.add_subparsers(dest="analytics_command")

    analytics_sub.add_parser(
        "assert-schema",
        help="assert the analytics-store schema honours the §18.1/§18.3 bright line",
    )

    part = analytics_sub.add_parser(
        "partition-path",
        help="print the Hive partition path for an (audit_source_type, period)",
    )
    part.add_argument("--audit-source-type", required=True)
    part.add_argument("--period", required=True, help="a month, YYYY-MM (§18.4)")

    return parser


def _run_analytics(args: argparse.Namespace) -> int:
    if args.analytics_command == "assert-schema":
        assert_analytics_schema()
        print(
            "analytics-store schema OK (no plate/name column; UUID + period join keys): "
            + ", ".join(ANALYTICS_COLUMNS)
        )
        return 0
    if args.analytics_command == "partition-path":
        print(partition_relative_path(args.audit_source_type, args.period))
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `db` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analytics" and args.analytics_command is not None:
        return _run_analytics(args)
    parser.print_help()
    return 0
