# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `reconcile` stage (SIG-ENG-013).

``reconcile resolve --dsn … [--jurisdiction okc]`` reads the L1 claims for a
jurisdiction out of the PostgreSQL claim spine, runs the §28 resolver
(:func:`reconcile.resolve.RESOLVE`) over each ``(subject, predicate)`` pair, and
prints the resolution envelope — **contradictions visible** (§3.1): a within-
predicate disagreement such as the 299-vs-190 ``claimed_device_count`` slice is
emitted as ``UNRESOLVED`` with both values retained, never collapsed to one number.
This is the read-only CLI anchor the capstone ``run_okc.sh`` (P21.4) needs; nothing
is persisted here (materializing the resolution is P21.2).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from . import __version__
from .resolve import RESOLVE


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `reconcile` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-reconcile",
        description="SIG reconcile stage: the §28 resolver over the claim spine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    resolve = sub.add_parser(
        "resolve",
        help="resolve claims from the PG spine and print the envelope (contradictions visible)",
    )
    resolve.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    resolve.add_argument(
        "--jurisdiction",
        default=None,
        help="jurisdiction token to filter subjects by (e.g. okc); matched on identifiers",
    )
    resolve.add_argument("--subject", default=None, help="restrict to one subject entity id")
    resolve.add_argument("--predicate", default=None, help="restrict to one predicate id")
    resolve.add_argument("--role", default=None, help="optional read role to SET ROLE to")

    materialize = sub.add_parser(
        "materialize",
        help="run the §28 resolver over the spine and WRITE the envelopes (P28.1, append-only)",
    )
    materialize.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    materialize.add_argument("--jurisdiction", default=None, help="jurisdiction token filter")
    materialize.add_argument("--subject", default=None, help="restrict to one subject entity id")
    materialize.add_argument("--predicate", default=None, help="restrict to one predicate id")
    materialize.add_argument("--role", default=None, help="optional role to SET ROLE to")

    edges = sub.add_parser(
        "materialize-edges",
        help="reconcile sharing/access edges (§29.3, P08.2) and WRITE the relationship "
        "network (P28.2, append-only, idempotent)",
    )
    edges.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    edges.add_argument("--jurisdiction", default=None, help="jurisdiction token filter")
    edges.add_argument("--subject", default=None, help="restrict to one subject entity id")
    edges.add_argument("--role", default=None, help="optional role to SET ROLE to")

    contradictions = sub.add_parser(
        "materialize-contradictions",
        help="run §29 reconciliation + the §28 resolver over the resolved spine and WRITE the "
        "VISIBLE §31 contradiction rows (P28.3, append-only, idempotent, lifecycle-aware)",
    )
    contradictions.add_argument("--dsn", required=True, help="PostgreSQL DSN of the claim spine")
    contradictions.add_argument("--jurisdiction", default=None, help="jurisdiction token filter")
    contradictions.add_argument("--subject", default=None, help="restrict to one subject entity id")
    contradictions.add_argument("--predicate", default=None, help="restrict to one predicate id")
    contradictions.add_argument("--role", default=None, help="optional role to SET ROLE to")
    return parser


def _resolve(args: argparse.Namespace) -> int:
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(args.dsn, autocommit=True)
    if args.role:
        conn.execute(f"SET ROLE {args.role}")

    # The same tier-0 read the materializer uses (one reader, so the read-only CLI and the
    # materialized envelope can never disagree — including the ADR-104 capture-time basis).
    from .materialize import read_claim_groups

    groups = read_claim_groups(
        conn, jurisdiction=args.jurisdiction, subject=args.subject, predicate=args.predicate
    )

    if not groups:
        print("no claims matched the given filters")
        return 0

    now = datetime.now(tz=UTC)
    for (subject, predicate), claims in sorted(groups.items()):
        try:
            resolved = RESOLVE(
                subject, predicate, claims, as_of_world=now.date(), as_of_belief=now.date()
            )
        except KeyError:
            print(f"# {subject} / {predicate}: predicate not in resolver ruleset — skipped")
            continue
        envelope = {
            "subject_id": subject,
            "predicate_id": predicate,
            "resolution_status": resolved.resolution_status,
            "value": resolved.value,
            "agreement": resolved.agreement,
            "contradiction_state": resolved.contradiction_state,
            "considered_claim_ids": list(resolved.considered_claim_ids),
            "claimed_values": [c.value for c in claims],
            "rationale": resolved.rationale_text,
        }
        print(json.dumps(envelope, default=str, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `reconcile` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "resolve":
        return _resolve(args)
    if args.command == "materialize":
        return _materialize(args)
    if args.command == "materialize-edges":
        return _materialize_edges(args)
    if args.command == "materialize-contradictions":
        return _materialize_contradictions(args)
    parser.print_help()
    return 0


def _materialize(args: argparse.Namespace) -> int:
    """Materialize resolution envelopes into the spine (P28.1, ADR-099)."""
    import sys
    import time

    from .materialize import materialize_from_dsn

    started = time.monotonic()

    def _progress(considered: int, total: int, inserted: int) -> None:
        # stderr, so stdout stays the one JSON summary a caller parses.
        elapsed = time.monotonic() - started
        print(
            f"progress: {considered}/{total} groups, {inserted} inserted, {elapsed:.0f}s",
            file=sys.stderr,
            flush=True,
        )

    summary = materialize_from_dsn(
        args.dsn,
        jurisdiction=args.jurisdiction,
        subject=args.subject,
        predicate=args.predicate,
        role=args.role,
        progress=_progress,
    )
    print(json.dumps(summary.as_dict(), indent=2))
    return 0


def _materialize_edges(args: argparse.Namespace) -> int:
    """Materialize the sharing/access relationship network into the spine (P28.2)."""
    from .materialize import materialize_sharing_edges_from_dsn

    summary = materialize_sharing_edges_from_dsn(
        args.dsn,
        jurisdiction=args.jurisdiction,
        subject=args.subject,
        role=args.role,
    )
    print(json.dumps(summary.as_dict(), indent=2))
    return 0


def _materialize_contradictions(args: argparse.Namespace) -> int:
    """Materialize the VISIBLE §31 contradiction rows into the spine (P28.3)."""
    from .materialize import materialize_contradictions_from_dsn

    summary = materialize_contradictions_from_dsn(
        args.dsn,
        jurisdiction=args.jurisdiction,
        subject=args.subject,
        predicate=args.predicate,
        role=args.role,
    )
    print(json.dumps(summary.as_dict(), indent=2))
    return 0
