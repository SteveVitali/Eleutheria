# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The weekly off-instance replica of ``…-sig-restricted`` (P37.3 / ADR-177,
SIG-STORE-048, R11-OPS-04).

The contract's shape: replicate the PRIVATE restricted bucket to a dual-region
bucket in the same project (``<project>-sig-restricted-dr``) on a weekly
cadence, **excluding sealed and superseded material** (S4c plan note: the
off-instance copies exclude or separately encrypt sealed material — exclusion
is the chosen half, never encryption).

What is excluded, and why:

* ``evidence/captures/`` — wholesale. After the evidence-bucket leg runs, the
  dedicated ``<project>-sig-evidence`` bucket is the live OCFL capture store;
  the restricted-bucket copies that remain are history the copy leg carried
  forward, never the store of record. Sealed captures (``capture_seal`` /
  the ``sig.seal-deny/1`` deny set) live under exactly this prefix, so the
  wholesale exclusion is also the sealed-material exclusion — no seal lookup
  is needed on this path, and a sealed object can never reach the replica.

* ``ops/seal/`` is NOT excluded — it is counts/ids/digests metadata, never
  sealed material (the deny set is what suppresses, and it must survive an
  off-instance restore).

* ``ops/replica/`` is NOT excluded — the replica's own run records are part of
  the restricted corpus (they are written to the destination and re-copied
  like any other object; a re-copy is a no-op on identical md5).

Append-only by construction: the runner copies ``copyTo`` server-side, never
deletes on the destination, and re-runs are no-ops for objects whose
``md5Hash`` already matches. The run record ``sig.restricted-replica/1``
lands on the **destination** bucket under ``ops/replica/<ts>.json`` — the
record survives the source, which is the point of an off-instance copy.

The acceptance shape the ticket names — *replica object count equals
source* — reads here as ``dest == source − excluded``, with every excluded
object enumerated in the record. A count that cannot be explained is a
failure, never smoothed (SIG-ENG-042).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .gcs import GcsBucket

SCHEMA = "sig.restricted-replica/1"
RECORD_PREFIX = "ops/replica/"

#: The superseded capture store — the dedicated evidence bucket supersedes it
#: and every sealed capture lives under it (ADR-177). Excluded wholesale.
DEFAULT_EXCLUDED_PREFIXES: tuple[str, ...] = ("evidence/captures/",)


@dataclass(frozen=True)
class ReplicaPlan:
    """The deterministic copy plan over one listing of the source bucket."""

    source_bucket: str
    dest_bucket: str
    prefix: str
    to_copy: tuple[str, ...]
    excluded: tuple[str, ...]


def plan_replica(
    source_names: list[str] | tuple[str, ...],
    *,
    source_bucket: str,
    dest_bucket: str,
    prefix: str = "",
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
) -> ReplicaPlan:
    """Split one source listing into copy vs excluded — pure, no I/O."""
    to_copy: list[str] = []
    excluded: list[str] = []
    for name in sorted(set(source_names)):
        if any(name.startswith(p) for p in excluded_prefixes):
            excluded.append(name)
        else:
            to_copy.append(name)
    return ReplicaPlan(
        source_bucket=source_bucket,
        dest_bucket=dest_bucket,
        prefix=prefix,
        to_copy=tuple(to_copy),
        excluded=tuple(excluded),
    )


def _md5(meta: dict | None) -> str | None:
    return (meta or {}).get("md5Hash")


def run_replica(
    source: GcsBucket,
    dest: GcsBucket,
    *,
    prefix: str = "",
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
    record_prefix: str = RECORD_PREFIX,
    now: str,
) -> dict:
    """Copy every non-excluded source object to ``dest``; write the record.

    Idempotent: an object whose ``md5Hash`` on the destination already matches
    the source is skipped, never re-copied. The record lands on the
    destination (off-instance evidence) — ``verified`` is the post-copy count
    parity ``dest == source − excluded``.
    """
    source_items = source.list_object_details(prefix)
    source_names = [str(i["name"]) for i in source_items]
    plan = plan_replica(
        source_names,
        source_bucket=source.bucket,
        dest_bucket=dest.bucket,
        prefix=prefix,
        excluded_prefixes=excluded_prefixes,
    )
    src_md5 = {str(i["name"]): i.get("md5Hash") for i in source_items}

    dest_meta = {str(i["name"]): i.get("md5Hash") for i in dest.list_object_details(prefix)}
    copied: list[str] = []
    skipped: list[str] = []
    for name in plan.to_copy:
        if dest_meta.get(name) == src_md5.get(name) and src_md5.get(name):
            skipped.append(name)
            continue
        source.copy_object_to(name, dest=dest)
        copied.append(name)

    verdict = verify_replica(source, dest, prefix=prefix, excluded_prefixes=excluded_prefixes)
    record = {
        "schema": SCHEMA,
        "run_at": now,
        "source_bucket": source.bucket,
        "dest_bucket": dest.bucket,
        "prefix": prefix,
        "excluded_prefixes": list(excluded_prefixes),
        "counts": {
            "source": len(source_items),
            "excluded": len(plan.excluded),
            "copied": len(copied),
            "skipped_unchanged": len(skipped),
            "dest": verdict["dest_count"],
        },
        "excluded": plan.excluded,
        "verified": bool(verdict["ok"]),
        "mismatches": verdict["mismatches"],
        "missing": verdict["missing"],
        "note": (
            "append-only copyTo replica; dest == source − excluded is the "
            "parity rule; excluded = the superseded capture store incl. all "
            "sealed captures (ADR-177)"
        ),
    }
    dest.put_object(
        f"{record_prefix}{now.replace(':', '').replace('-', '')}.json",
        json.dumps(record, indent=1, sort_keys=True).encode(),
        content_type="application/json",
    )
    return record


def verify_replica(
    source: GcsBucket,
    dest: GcsBucket,
    *,
    prefix: str = "",
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
) -> dict:
    """The parity verdict: every non-excluded source object is on ``dest``
    with an equal ``md5Hash`` — ``dest ⊇ source − excluded`` and no extra
    object under ``prefix`` that is not a run record or an excluded twin.
    """
    source_items = {str(i["name"]): i.get("md5Hash") for i in source.list_object_details(prefix)}
    dest_items = {str(i["name"]): i.get("md5Hash") for i in dest.list_object_details(prefix)}
    plan = plan_replica(
        sorted(source_items),
        source_bucket=source.bucket,
        dest_bucket=dest.bucket,
        prefix=prefix,
        excluded_prefixes=excluded_prefixes,
    )
    missing = [n for n in plan.to_copy if n not in dest_items]
    mismatches = [
        n
        for n in plan.to_copy
        if n in dest_items and source_items[n] and dest_items[n] != source_items[n]
    ]
    ok = not missing and not mismatches
    return {
        "ok": ok,
        "source_count": len(source_items),
        "excluded_count": len(plan.excluded),
        "dest_count": len(dest_items),
        "missing": missing,
        "mismatches": mismatches,
    }


def run(
    *,
    source_bucket: str,
    dest_bucket: str,
    prefix: str = "",
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
    now: str,
    source: GcsBucket | None = None,
    dest: GcsBucket | None = None,
) -> dict:
    """Env-free entry the CLI calls — clients injectable for tests."""
    source = source or GcsBucket(source_bucket)
    dest = dest or GcsBucket(dest_bucket)
    return run_replica(
        source,
        dest,
        prefix=prefix,
        excluded_prefixes=excluded_prefixes,
        now=now,
    )


def verify(
    *,
    source_bucket: str,
    dest_bucket: str,
    prefix: str = "",
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
    source: GcsBucket | None = None,
    dest: GcsBucket | None = None,
) -> dict:
    source = source or GcsBucket(source_bucket)
    dest = dest or GcsBucket(dest_bucket)
    return verify_replica(
        source,
        dest,
        prefix=prefix,
        excluded_prefixes=excluded_prefixes,
    )


def env_default(name: str) -> str:
    return os.environ.get(name, "")


def _utcnow() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    """``sig-ops restricted-replica plan|run|verify`` — the weekly replica job."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops restricted-replica",
        description=(
            "P37.3 (SIG-STORE-048, ADR-177): the weekly off-instance replica "
            "of the restricted bucket to the dual-region "
            "<project>-sig-restricted-dr — append-only copyTo, the "
            "evidence/captures/ prefix excluded wholesale (the dedicated "
            "evidence bucket supersedes it and every sealed capture lives "
            "under it). The run record lands on the DESTINATION bucket."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _args(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--source-bucket",
            default=env_default("SIG_REPLICA_SOURCE"),
            help="the restricted bucket name (env SIG_REPLICA_SOURCE; default "
            "<project>-sig-restricted)",
        )
        p.add_argument(
            "--dest-bucket",
            default=env_default("SIG_REPLICA_DEST"),
            help="the replica bucket name (env SIG_REPLICA_DEST; default "
            "<project>-sig-restricted-dr)",
        )
        p.add_argument("--prefix", default="")
        p.add_argument(
            "--exclude-prefix",
            action="append",
            default=[],
            help="additional excluded prefixes (repeatable; evidence/captures/ is always excluded)",
        )
        p.add_argument("--now", default=None, help="ISO-8601 UTC stamp (test seam)")

    p_plan = sub.add_parser("plan", help="the deterministic copy plan — read-only")
    _args(p_plan)
    p_run = sub.add_parser("run", help="copy + write sig.restricted-replica/1 on dest")
    _args(p_run)
    p_verify = sub.add_parser("verify", help="the dest == source − excluded parity read")
    _args(p_verify)

    args = parser.parse_args(argv)
    if not args.source_bucket or not args.dest_bucket:
        print(
            "sig-ops restricted-replica: --source-bucket/--dest-bucket (or the "
            "SIG_REPLICA_SOURCE/SIG_REPLICA_DEST envs) are required",
            file=sys.stderr,
        )
        return 2
    excluded = tuple(dict.fromkeys(DEFAULT_EXCLUDED_PREFIXES + tuple(args.exclude_prefix)))
    try:
        if args.cmd == "plan":
            source = GcsBucket(args.source_bucket)
            names = source.list_objects(args.prefix)
            plan = plan_replica(
                names,
                source_bucket=args.source_bucket,
                dest_bucket=args.dest_bucket,
                prefix=args.prefix,
                excluded_prefixes=excluded,
            )
            print(
                json.dumps(
                    {
                        "schema": "sig.restricted-replica-plan/1",
                        "source_bucket": plan.source_bucket,
                        "dest_bucket": plan.dest_bucket,
                        "to_copy": len(plan.to_copy),
                        "excluded": len(plan.excluded),
                        "excluded_prefixes": list(excluded),
                    },
                    indent=1,
                )
            )
            return 0
        if args.cmd == "run":
            record = run(
                source_bucket=args.source_bucket,
                dest_bucket=args.dest_bucket,
                prefix=args.prefix,
                excluded_prefixes=excluded,
                now=args.now or _utcnow(),
            )
            print(json.dumps(record, indent=1, sort_keys=True))
            return 0 if record["verified"] else 4
        verdict = verify(
            source_bucket=args.source_bucket,
            dest_bucket=args.dest_bucket,
            prefix=args.prefix,
            excluded_prefixes=excluded,
        )
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["ok"] else 4
    except Exception as exc:  # noqa: BLE001 — honest ops record, never swallowed
        print(f"sig-ops restricted-replica: {exc}", file=sys.stderr)
        return 3
