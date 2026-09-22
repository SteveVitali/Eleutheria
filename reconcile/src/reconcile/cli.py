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
from datetime import UTC, date, datetime
from typing import Any

from . import __version__
from .resolve import RESOLVE, Claim


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
    return parser


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date(1970, 1, 1)


def _value(kind: str, text: Any, num: Any, boolean: Any) -> object:
    if kind != "value":
        return None
    if boolean is not None:
        return bool(boolean)
    if num is not None:
        f = float(num)
        return int(f) if f.is_integer() else f
    return text


def _resolve(args: argparse.Namespace) -> int:
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(args.dsn, autocommit=True)
    if args.role:
        conn.execute(f"SET ROLE {args.role}")

    where = ["c.sensitivity_tier = 0"]
    params: list[Any] = []
    if args.subject:
        where.append("c.subject_id = %s")
        params.append(args.subject)
    if args.predicate:
        where.append("c.predicate_id = %s")
        params.append(args.predicate)
    if args.jurisdiction:
        where.append(
            "c.subject_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
        params.append(f"%{args.jurisdiction}%")

    rows = conn.execute(
        "SELECT c.subject_id, c.predicate_id, c.claim_id, c.value_kind, c.value_text, "
        "       c.value_num, c.value_bool, c.raw_value, c.observed_at, c.source_reliability, "
        "       c.artifact_integrity, c.review_status, ea.source_id, ea.artifact_type "
        "  FROM claim c "
        "  LEFT JOIN LATERAL ("
        "     SELECT ea.source_id, ea.artifact_type FROM claim_evidence ce "
        "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
        "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
        "      WHERE ce.claim_id = c.claim_id LIMIT 1) ea ON true "
        " WHERE " + " AND ".join(where) + " ORDER BY c.subject_id, c.predicate_id, c.claim_id",
        tuple(params),
    ).fetchall()

    groups: dict[tuple[str, str], list[Claim]] = {}
    for r in rows:
        key = (str(r[0]), str(r[1]))
        groups.setdefault(key, []).append(
            Claim(
                claim_id=str(r[2]),
                subject_id=str(r[0]),
                predicate_id=str(r[1]),
                value=_value(r[3], r[4], r[5], r[6]),
                reliability=r[9],
                integrity=r[10],
                genre=r[13] or "",
                observed_at=_as_date(r[8]) if r[8] else date(1970, 1, 1),
                raw_value=r[7] or "",
                review_status=r[11] or "active",
                source_id=r[12] or "",
                count_basis=str(r[1]).removesuffix("_device_count")
                if str(r[1]).endswith("_device_count")
                else None,
            )
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
    parser.print_help()
    return 0
