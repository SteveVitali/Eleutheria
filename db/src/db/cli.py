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

    rd = sub.add_parser(
        "rights-decisions",
        help="record evidenced rights resolutions as append-only rights_decision "
        "rows (P27.2, ADR-095; default is a read-only plan)",
    )
    rd.add_argument("--dsn", required=True, help="PostgreSQL DSN for the spine")
    rd.add_argument(
        "--decisions",
        required=True,
        help="the committed dispositions artifact (JSON; docs/build/reports/rights/)",
    )
    rd.add_argument(
        "--apply",
        action="store_true",
        help="write the reviewed rights_record + rights_decision rows (default: plan only)",
    )
    rd.add_argument(
        "--capture-terms",
        action="store_true",
        help="fetch each terms_url once and archive it as evidence_capture "
        "(SIG-LIC-002); implies --apply",
    )
    rd.add_argument(
        "--code-commit",
        default="unknown",
        help="the code commit recorded on the review ingest_run",
    )

    bench = sub.add_parser(
        "sink-bench",
        help="time PgClaimSink passes over synthetic OSM-shaped claims: claims/min and "
        "round trips per claim (P31.3, ADR-110). Writes synthetic claims, so it needs "
        "--scratch-db and must never target the canonical spine",
    )
    bench.add_argument("--dsn", required=True, help="PostgreSQL DSN of a THROWAWAY database")
    bench.add_argument("--subjects", type=int, default=12_500, help="subjects (8 claims each)")
    bench.add_argument("--passes", type=int, default=2, help="1 land + (passes-1) +0 replays")
    bench.add_argument("--commit-chunk-size", type=int, default=10_000)
    bench.add_argument(
        "--insert-batch-size", type=int, default=None, help="rows per multi-row claim INSERT"
    )
    bench.add_argument("--tag", default="bench", help="subject-id tag (a new tag = new subjects)")
    bench.add_argument(
        "--scratch-db",
        action="store_true",
        help="acknowledge that --dsn is a throwaway database (required)",
    )

    return parser


def _run_sink_bench(args: argparse.Namespace) -> int:
    if not args.scratch_db:
        print("sink-bench writes synthetic claims: pass --scratch-db for a throwaway database")
        return 2
    from .sink_bench import run_synthetic

    run_synthetic(  # prints one JSON line per pass as it completes
        args.dsn,
        subjects=args.subjects,
        passes=args.passes,
        commit_chunk_size=args.commit_chunk_size,
        tag=args.tag,
        sink_kwargs=(
            {"insert_batch_size": args.insert_batch_size} if args.insert_batch_size else None
        ),
    )
    return 0


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


def _run_rights_decisions(args: argparse.Namespace) -> int:
    """Plan or apply append-only rights resolutions (P27.2 / ADR-095)."""
    import json

    import psycopg

    from .rights_decisions import (
        apply_resolutions,
        capture_terms,
        fetch_terms,
        load_resolutions,
        plan_resolutions,
    )

    resolutions = load_resolutions(args.decisions)
    apply = args.apply or args.capture_terms
    with psycopg.connect(args.dsn, autocommit=False) as conn:
        if not apply:
            report = plan_resolutions(conn, resolutions)
            print(json.dumps({"mode": "plan", "resolutions": report}, indent=2, sort_keys=True))
            return 0

        # --apply: terms captures first (each gets a rights_record to attach to),
        # then the decision rows that link the archived terms (SIG-LIC-002).
        terms_captures: dict[str, str] = {}
        capture_notes: list[dict[str, object]] = []
        if args.capture_terms:
            from .rights_decisions import _ensure_rights_record

            for res in resolutions:
                fetched = fetch_terms(res.terms_url)
                if fetched is None:
                    capture_notes.append(
                        {"source_id": res.source_id, "terms_url": res.terms_url, "captured": False}
                    )
                    continue
                rights_id = _ensure_rights_record(conn, res)
                terms_captures[res.source_id] = capture_terms(
                    conn, res, rights_id, fetched, code_commit=args.code_commit
                )
                capture_notes.append(
                    {"source_id": res.source_id, "terms_url": res.terms_url, "captured": True}
                )
        report = apply_resolutions(conn, resolutions, terms_captures=terms_captures)
        conn.commit()
    print(
        json.dumps(
            {
                "mode": "apply",
                "capture_terms": capture_notes,
                "resolutions": report,
                "claims_lifted": sum(r["claims_lifted"] for r in report),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `db` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analytics" and args.analytics_command is not None:
        return _run_analytics(args)
    if args.command == "rights-decisions":
        return _run_rights_decisions(args)
    if args.command == "sink-bench":
        return _run_sink_bench(args)
    parser.print_help()
    return 0
