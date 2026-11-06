# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The monthly logical-export cross-project copy (P37.3 / ADR-177,
SIG-STORE-048, R11-OPS-04).

P34.6's monthly ``gcloud sql export sql`` lands at
``gs://<project>-sig-backups/pg/monthly/<YYYY-MM>/`` — a logical copy that
lives outside the Cloud SQL instance's lifecycle but inside the same
project's blast radius. This job carries it one step further: a copy under
``pg/monthly/`` on a bucket in the **second** project the operator names
(``SIG_BACKUP_PROJECT``, env-only — the id is never committed, GL-GATE-04's
rule). An off-instance, off-project logical dump is the last-resort restore
when the whole first project is unavailable.

Shape: server-side ``copyTo`` per object under ``pg/monthly/`` (no download
through the job), append-only (destination objects are never deleted; a
re-copy with equal ``md5Hash`` is a no-op), and the run record
``sig.pg-export-copy/1`` lands on the **destination** bucket under
``ops/pg-export-copy/<ts>.json``. ``verify`` is the count+md5 parity over
``pg/monthly/`` — ``dest == source`` under that prefix, nothing else.

The spine itself holds no Part VIII material by construction (claims are
evidence-referenced); the export contains no captures, so no sealed-material
exclusion is needed on this path (the restricted-bucket replica carries the
capture-store exclusion).
"""

from __future__ import annotations

import json
import os

from .gcs import GcsBucket

SCHEMA = "sig.pg-export-copy/1"
EXPORT_PREFIX = "pg/monthly/"
RECORD_PREFIX = "ops/pg-export-copy/"


def run_copy(
    source: GcsBucket,
    dest: GcsBucket,
    *,
    prefix: str = EXPORT_PREFIX,
    record_prefix: str = RECORD_PREFIX,
    now: str,
) -> dict:
    """Copy every object under ``prefix`` source → dest; write the record."""
    source_items = {str(i["name"]): i.get("md5Hash") for i in source.list_object_details(prefix)}
    dest_items = {str(i["name"]): i.get("md5Hash") for i in dest.list_object_details(prefix)}
    copied: list[str] = []
    skipped: list[str] = []
    for name in sorted(source_items):
        if source_items[name] and dest_items.get(name) == source_items[name]:
            skipped.append(name)
            continue
        source.copy_object_to(name, dest=dest)
        copied.append(name)

    verdict = verify_copy(source, dest, prefix=prefix)
    record = {
        "schema": SCHEMA,
        "run_at": now,
        "source_bucket": source.bucket,
        "dest_bucket": dest.bucket,
        "prefix": prefix,
        "counts": {
            "source": len(source_items),
            "copied": len(copied),
            "skipped_unchanged": len(skipped),
            "dest": verdict["dest_count"],
        },
        "verified": bool(verdict["ok"]),
        "mismatches": verdict["mismatches"],
        "missing": verdict["missing"],
        "note": (
            "append-only copyTo cross-project copy of the monthly logical "
            "export; dest == source under pg/monthly/ is the parity rule"
        ),
    }
    dest.put_object(
        f"{record_prefix}{now.replace(':', '').replace('-', '')}.json",
        json.dumps(record, indent=1, sort_keys=True).encode(),
        content_type="application/json",
    )
    return record


def verify_copy(
    source: GcsBucket,
    dest: GcsBucket,
    *,
    prefix: str = EXPORT_PREFIX,
) -> dict:
    """Parity: every source object under ``prefix`` is on ``dest`` with an
    equal ``md5Hash``."""
    source_items = {str(i["name"]): i.get("md5Hash") for i in source.list_object_details(prefix)}
    dest_items = {str(i["name"]): i.get("md5Hash") for i in dest.list_object_details(prefix)}
    missing = [n for n in source_items if n not in dest_items]
    mismatches = [
        n
        for n in source_items
        if n in dest_items and source_items[n] and dest_items[n] != source_items[n]
    ]
    return {
        "ok": not missing and not mismatches,
        "source_count": len(source_items),
        "dest_count": len(dest_items),
        "missing": sorted(missing),
        "mismatches": sorted(mismatches),
    }


def _utcnow() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    """``sig-ops pg-export-copy plan|run|verify`` — the monthly export copy."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops pg-export-copy",
        description=(
            "P37.3 (SIG-STORE-048, ADR-177): the cross-project copy of the "
            "monthly logical export — append-only copyTo of pg/monthly/ on "
            "<project>-sig-backups to the second project's bucket "
            "(SIG_BACKUP_PROJECT, env-only). The run record lands on the "
            "DESTINATION bucket."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _args(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--source-bucket",
            default=os.environ.get("SIG_EXPORT_COPY_SOURCE", ""),
            help="the backups bucket name (env SIG_EXPORT_COPY_SOURCE; "
            "default <project>-sig-backups)",
        )
        p.add_argument(
            "--dest-bucket",
            default=os.environ.get("SIG_EXPORT_COPY_DEST", ""),
            help="the second-project bucket name (env SIG_EXPORT_COPY_DEST; "
            "default <SIG_BACKUP_PROJECT>-sig-backups)",
        )
        p.add_argument("--prefix", default=EXPORT_PREFIX)
        p.add_argument("--now", default=None, help="ISO-8601 UTC stamp (test seam)")

    p_plan = sub.add_parser("plan", help="the copy plan — read-only")
    _args(p_plan)
    p_run = sub.add_parser("run", help="copy + write sig.pg-export-copy/1 on dest")
    _args(p_run)
    p_verify = sub.add_parser("verify", help="the dest == source parity read")
    _args(p_verify)

    args = parser.parse_args(argv)
    if not args.source_bucket or not args.dest_bucket:
        print(
            "sig-ops pg-export-copy: --source-bucket/--dest-bucket (or the "
            "SIG_EXPORT_COPY_SOURCE/SIG_EXPORT_COPY_DEST envs) are required",
            file=sys.stderr,
        )
        return 2
    try:
        source = GcsBucket(args.source_bucket)
        dest = GcsBucket(args.dest_bucket)
        if args.cmd == "plan":
            names = [i["name"] for i in source.list_object_details(args.prefix)]
            print(
                json.dumps(
                    {
                        "schema": "sig.pg-export-copy-plan/1",
                        "source_bucket": args.source_bucket,
                        "dest_bucket": args.dest_bucket,
                        "prefix": args.prefix,
                        "to_copy": len(names),
                    },
                    indent=1,
                )
            )
            return 0
        if args.cmd == "run":
            record = run_copy(source, dest, prefix=args.prefix, now=args.now or _utcnow())
            print(json.dumps(record, indent=1, sort_keys=True))
            return 0 if record["verified"] else 4
        verdict = verify_copy(source, dest, prefix=args.prefix)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["ok"] else 4
    except Exception as exc:  # noqa: BLE001 — honest ops record, never swallowed
        print(f"sig-ops pg-export-copy: {exc}", file=sys.stderr)
        return 3
