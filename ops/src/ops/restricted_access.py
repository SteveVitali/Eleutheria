# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``sig-ops restricted-access`` — the audited restricted-byte access function
(P37.4b, R11-OPS-08, SIG-SEC-005 + SIG-EVID-012, ADR-232).

F2a group 9 + G1-13: one audited access function — every *direct* read of
``restricted``/``sealed`` bytes goes through :func:`audited_read`, which writes
a ``sig.restricted-access/1`` record (requester, purpose, time, object ref)
under ``ops/access-log/`` **before** returning the bytes, so a failed fetch is
still an audited attempt. The log is itself retained 180 days
(:data:`evidence.access_log.ACCESS_LOG_RETENTION_DAYS` — the SIG-EVID-012
bound, so it never becomes a surveillance record of SIG's own researchers,
§44.5) then purged by the scheduled ``sig-access-log-purge`` job:
:func:`run_purge` lists the prefix, deletes exactly the records whose
``accessed_at`` is past retention, and emits a ``sig.access-log-purge/1``
record under a sibling prefix of what it removed. A record that cannot be
parsed is KEPT and flagged — never delete what you cannot explain
(SIG-ENG-042).

The GCP-side half of the named mutation is planned here too:
:func:`merge_audit_config` is the pure policy merge the ``audit`` leg applies
to the project IAM policy — ``DATA_READ`` + ``DATA_WRITE`` on
``storage.googleapis.com`` with the declared mechanical readers exempted
(G1-13's volume control: ingest/export/replica bulk reads are excluded at
generation so human and unexpected reads are the signal). The sink, alert,
``ENCRYPTED_ONLY`` and purge-job legs are scripted in
``ops/gcp/restricted-access.sh``.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from evidence.access_log import ACCESS_LOG_RETENTION_DAYS, expired

from .gcs import GcsBucket

SCHEMA = "sig.restricted-access/1"
PURGE_SCHEMA = "sig.access-log-purge/1"
LOG_PREFIX = "ops/access-log/"
PURGE_PREFIX = "ops/access-log-purge/"
RETENTION_DAYS = ACCESS_LOG_RETENTION_DAYS  # 180 — the SIG-EVID-012 bound

#: The GCS audit service the named mutation turns DATA_READ/DATA_WRITE on for.
AUDIT_SERVICE = "storage.googleapis.com"
AUDIT_LOG_TYPES = ("DATA_READ", "DATA_WRITE")

#: The mechanical bulk readers the auditConfig exempts (G1-13 volume control).
#: sig-ingest-rt fetches captures; sig-export-rt stages exports; sig-replica-rt
#: is the P37.3 weekly off-instance copy. Human and unexpected readers stay
#: logged — the whole point of the audit turn-on.
DEFAULT_EXEMPT_SAS: tuple[str, ...] = ("sig-ingest-rt", "sig-export-rt", "sig-replica-rt")


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def access_record(
    bucket: str,
    name: str,
    *,
    requester: str,
    purpose: str,
    now: str,
) -> dict[str, Any]:
    """One ``sig.restricted-access/1`` row — requester/purpose/time/object.

    Refuses an empty requester or purpose exactly like
    ``evidence.access_log.AccessLogEntry`` (SIG-EVID-012): an unaudited access
    is a louder failure than no access at all.
    """
    if not requester or not purpose:
        raise ValueError(
            "restricted-byte access requires a requester and a purpose "
            "(SIG-SEC-005/SIG-EVID-012) — no unaudited read"
        )
    return {
        "schema": SCHEMA,
        "accessed_at": now,
        "requester": requester,
        "purpose": purpose,
        "bucket": bucket,
        "object": name,
    }


def record_name(record: dict[str, Any]) -> str:
    """The WORM-shaped object name for one access record.

    ``ops/access-log/<YYYY>/<MM>/sig.restricted-access-<ts>-<sha8>.json`` —
    objects are never rewritten in place (same posture as ``ops/probes/``).
    """
    digest = hashlib.sha256(
        f"{record['accessed_at']}|{record['requester']}|{record['object']}".encode()
    ).hexdigest()[:8]
    ts = str(record["accessed_at"]).replace("-", "").replace(":", "")
    ym = str(record["accessed_at"])[:7].replace("-", "/")
    return f"{LOG_PREFIX}{ym}/sig.restricted-access-{ts}-{digest}.json"


def audited_read(
    bucket: GcsBucket,
    name: str,
    *,
    requester: str,
    purpose: str,
    now: str | None = None,
    log_bucket: GcsBucket | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """The ONE sanctioned direct read of restricted/sealed bytes.

    Logs FIRST — the ``sig.restricted-access/1`` record lands under
    ``ops/access-log/`` on ``log_bucket`` (default: the byte bucket itself)
    before ``name`` is fetched, so a failed fetch is still an audited attempt.
    Returns ``(bytes, record)``.
    """
    stamp = now or _utcnow()
    record = access_record(bucket.bucket, name, requester=requester, purpose=purpose, now=stamp)
    (log_bucket or bucket).put_object(
        record_name(record),
        (json.dumps(record, indent=1, sort_keys=True) + "\n").encode(),
        content_type="application/json",
    )
    return bucket.get_object(name), record


def parse_access_record(payload: bytes | str | dict | None) -> dict[str, Any] | None:
    """Best-effort parse of one access-log object; ``None`` when unreadable."""
    if isinstance(payload, dict):
        doc = payload
    else:
        try:
            doc = json.loads(payload or "")
        except (TypeError, ValueError):
            return None
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        return None
    return doc


def _parse_when(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


@dataclass(frozen=True)
class PurgePlan:
    """The deterministic partition of one access-log listing."""

    to_delete: tuple[str, ...]
    kept: tuple[str, ...]
    flagged: tuple[str, ...]  # unparseable — kept, never deleted unexplained


def purge_plan(
    items: list[tuple[str, dict[str, Any] | None]],
    *,
    now: datetime,
    retention_days: int = RETENTION_DAYS,
) -> PurgePlan:
    """Partition ``(name, parsed-record-or-None)`` into delete / keep / flag.

    ``None`` (unparseable payload or a missing ``accessed_at``) is flagged and
    kept — the sweep deletes only rows it can prove are expired.
    """
    to_delete: list[str] = []
    kept: list[str] = []
    flagged: list[str] = []
    for name, record in sorted(items, key=lambda i: i[0]):
        when = _parse_when(record.get("accessed_at")) if record else None
        if when is None:
            flagged.append(name)
        elif expired(when, now, retention_days):
            to_delete.append(name)
        else:
            kept.append(name)
    return PurgePlan(tuple(to_delete), tuple(kept), tuple(flagged))


def run_purge(
    log_bucket: GcsBucket,
    *,
    now: str | None = None,
    apply_: bool = False,
    retention_days: int = RETENTION_DAYS,
    prefix: str = LOG_PREFIX,
    purge_prefix: str = PURGE_PREFIX,
) -> dict[str, Any]:
    """The scheduled retention sweep over ``ops/access-log/``.

    Lists the prefix, reads every record, deletes exactly the expired ones
    (only with ``apply_``), then lands a ``sig.access-log-purge/1`` record
    under ``ops/access-log-purge/`` so the sweep itself is audited. The
    returned dict is the record; in plan mode ``applied`` is False and no
    delete or record write happens.
    """
    stamp = now or _utcnow()
    now_dt = _parse_when(stamp)
    if now_dt is None:  # pragma: no cover — the clock seam is ISO by contract
        raise ValueError(f"unparseable now: {stamp!r}")
    items: list[tuple[str, dict[str, Any] | None]] = []
    for name in sorted(log_bucket.list_objects(prefix)):
        parsed = parse_access_record(log_bucket.get_object(name))
        items.append((name, parsed))
    plan = purge_plan(items, now=now_dt, retention_days=retention_days)
    if apply_:
        for name in plan.to_delete:
            log_bucket.delete_object(name)
    record: dict[str, Any] = {
        "schema": PURGE_SCHEMA,
        "run_at": stamp,
        "bucket": log_bucket.bucket,
        "prefix": prefix,
        "retention_days": retention_days,
        "applied": apply_,
        "counts": {
            "listed": len(items),
            "deleted": len(plan.to_delete) if apply_ else 0,
            "kept": len(plan.kept),
            "flagged_unparsed": len(plan.flagged),
        },
        "deleted": list(plan.to_delete) if apply_ else [],
        "would_delete": [] if apply_ else list(plan.to_delete),
        "flagged": list(plan.flagged),
    }
    if apply_:
        ts = stamp.replace("-", "").replace(":", "")
        log_bucket.put_object(
            f"{purge_prefix}sig.access-log-purge-{ts}.json",
            (json.dumps(record, indent=1, sort_keys=True) + "\n").encode(),
            content_type="application/json",
        )
    return record


# --- the Data Access auditConfig merge (the audit leg) ---------------------- #


def audit_config_block(
    exempted_members: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """The ``auditConfigs`` entry for ``storage.googleapis.com`` — DATA_READ +
    DATA_WRITE, each carrying the declared exempted mechanical readers."""
    return {
        "service": AUDIT_SERVICE,
        "auditLogConfigs": [
            {"logType": lt, "exemptedMembers": sorted(exempted_members)} for lt in AUDIT_LOG_TYPES
        ],
    }


def merge_audit_config(
    policy: dict[str, Any],
    *,
    service: str = AUDIT_SERVICE,
    log_types: tuple[str, ...] = AUDIT_LOG_TYPES,
    exempted: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Idempotently merge the Data Access auditConfig into an IAM policy doc.

    Other services' entries and other logTypes on the same service are
    preserved; the named logTypes gain (never lose) the exempted members.
    """
    out = json.loads(json.dumps(policy))  # deep copy — pure over the input
    acs = out.setdefault("auditConfigs", [])
    target = next((a for a in acs if a.get("service") == service), None)
    if target is None:
        target = {"service": service, "auditLogConfigs": []}
        acs.append(target)
    configs = target.setdefault("auditLogConfigs", [])
    for lt in log_types:
        entry = next((c for c in configs if c.get("logType") == lt), None)
        if entry is None:
            configs.append({"logType": lt, "exemptedMembers": sorted(exempted)})
        else:
            merged = sorted(set(entry.get("exemptedMembers") or []) | set(exempted))
            if merged:
                entry["exemptedMembers"] = merged
    return out


def sa_members(project: str, sa_names: tuple[str, ...] = DEFAULT_EXEMPT_SAS) -> list[str]:
    """The ``serviceAccount:`` member strings for the exempted class SAs."""
    return [f"serviceAccount:{name}@{project}.iam.gserviceaccount.com" for name in sa_names]


def main(argv: list[str] | None = None) -> int:
    """``sig-ops restricted-access plan|read|purge|audit-merge``."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="sig-ops restricted-access",
        description=(
            "P37.4b (SIG-SEC-005/SIG-EVID-012, ADR-232): the single audited "
            "restricted-byte access function — every direct read logs "
            "sig.restricted-access/1 under ops/access-log/ first, then reads. "
            "`purge` is the scheduled retention sweep (180d); `audit-merge` "
            "folds the storage.googleapis.com DATA_READ/DATA_WRITE auditConfig "
            "into a fetched project IAM policy."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="print the named mutation's leg plan (offline)")

    p_read = sub.add_parser("read", help="one audited restricted-byte read")
    p_read.add_argument("--bucket", default=os.environ.get("SIG_RACC_BUCKET", ""))
    p_read.add_argument("--object", required=True)
    p_read.add_argument("--requester", required=True)
    p_read.add_argument("--purpose", required=True)
    p_read.add_argument("--log-bucket", default=os.environ.get("SIG_RACC_LOG_BUCKET", ""))
    p_read.add_argument("--out", default=None, help="write the fetched bytes here")
    p_read.add_argument("--now", default=None, help="ISO-8601 UTC stamp (test seam)")

    p_purge = sub.add_parser("purge", help="the scheduled access-log retention sweep")
    p_purge.add_argument("--bucket", default=os.environ.get("SIG_RACC_LOG_BUCKET", ""))
    p_purge.add_argument("--apply", action="store_true", help="delete expired records")
    p_purge.add_argument("--retention-days", type=int, default=RETENTION_DAYS)
    p_purge.add_argument("--now", default=None, help="ISO-8601 UTC stamp (test seam)")

    p_merge = sub.add_parser(
        "audit-merge", help="merge the auditConfig block into a project IAM policy JSON"
    )
    p_merge.add_argument("--policy", required=True, help="the fetched get-iam-policy JSON")
    p_merge.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_merge.add_argument(
        "--exempted",
        action="append",
        default=[],
        help="member to exempt (repeatable); default: the declared class SAs",
    )
    p_merge.add_argument("--out", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "plan":
        print(
            "P37.4b restricted-byte access posture — legs: prestate -> audit -> "
            "sink -> iam -> ssl -> job -> cost -> probe -> verify\n"
            "auditConfig: storage.googleapis.com DATA_READ+DATA_WRITE, exempted: "
            + ", ".join(DEFAULT_EXEMPT_SAS)
        )
        return 0

    if args.cmd == "audit-merge":
        if not args.project:
            print(
                "sig-ops restricted-access audit-merge: --project or SIG_GCP_PROJECT required",
                file=sys.stderr,
            )
            return 2
        from pathlib import Path

        policy = json.loads(Path(args.policy).read_text())
        exempted = args.exempted or sa_members(args.project)
        merged = merge_audit_config(policy, exempted=exempted)
        text = json.dumps(merged, indent=1, sort_keys=True) + "\n"
        if args.out:
            from pathlib import Path

            Path(args.out).write_text(text)
            print(f"merged -> {args.out}")
        else:
            print(text, end="")
        return 0

    if args.cmd == "read":
        if not args.bucket:
            print(
                "sig-ops restricted-access read: --bucket (or SIG_RACC_BUCKET) required",
                file=sys.stderr,
            )
            return 2
        try:
            data, record = audited_read(
                GcsBucket(args.bucket),
                args.object,
                requester=args.requester,
                purpose=args.purpose,
                now=args.now,
                log_bucket=GcsBucket(args.log_bucket) if args.log_bucket else None,
            )
        except Exception as exc:  # noqa: BLE001 — honest record, never swallowed
            print(f"sig-ops restricted-access read: {exc}", file=sys.stderr)
            return 3
        if args.out:
            from pathlib import Path

            Path(args.out).write_bytes(data)
            print(f"bytes -> {args.out} ({len(data)} B)")
        print(json.dumps(record, indent=1, sort_keys=True))
        return 0

    if args.cmd == "purge":
        if not args.bucket:
            print(
                "sig-ops restricted-access purge: --bucket (or SIG_RACC_LOG_BUCKET) required",
                file=sys.stderr,
            )
            return 2
        try:
            record = run_purge(
                GcsBucket(args.bucket),
                now=args.now,
                apply_=bool(args.apply),
                retention_days=args.retention_days,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"sig-ops restricted-access purge: {exc}", file=sys.stderr)
            return 3
        print(json.dumps(record, indent=1, sort_keys=True))
        return 0

    return 64  # pragma: no cover


__all__ = [
    "ACCESS_LOG_RETENTION_DAYS",
    "AUDIT_LOG_TYPES",
    "AUDIT_SERVICE",
    "DEFAULT_EXEMPT_SAS",
    "LOG_PREFIX",
    "PURGE_PREFIX",
    "PURGE_SCHEMA",
    "RETENTION_DAYS",
    "SCHEMA",
    "PurgePlan",
    "access_record",
    "audit_config_block",
    "audited_read",
    "merge_audit_config",
    "parse_access_record",
    "purge_plan",
    "record_name",
    "run_purge",
    "sa_members",
]
