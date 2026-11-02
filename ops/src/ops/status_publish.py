# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.43 — the status lane's emit + status-scoped publish leg.

``sig-ops status-publish emit`` renders the lane file set from its inputs
(the dry-run publish that proves the artifact shape — the fixture leg this
ticket exercises). ``sig-ops status-publish --apply`` runs the same emit
then pushes ``status/**`` through the status-scoped half of the one
allow-listed publish path (P34.10 / SIG-OPS-003/004 — ACT-05/PKG-04 in J3's
vocabulary): the same assertion → record → sync → verify discipline, scoped
to the ``status/`` namespace by ``ops/public_routes_status.toml``. It writes
only ``status/**`` objects and deletes only stale ``status/`` objects it
does not emit — **except** ``status/archive/**``, which is append-only and
never deleted (P1–P3).

The job create itself (Cloud Run job + Cloud Scheduler trigger, 6 h) is the
OM-20 named mutation — ``ops/gcp/status-publish.sh`` owns that leg.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .gcs import GcsBucket
from .publish import (
    PublishError,
    assert_public_tree_content,
    assert_publish_set_secret_free,
)
from .status_lane import (
    ARCHIVE_PREFIX,
    STATUS_DIR,
    StatusLaneError,
    build_status_lane,
    cadence_crons,
    emit_status_files,
    load_run_records,
    load_scheduler_report,
    load_source_rows,
    parse_status_time,
)

#: The lane's scoped allow-list (``ops/public_routes_status.toml``): the only
#: top-level entry a status publish tree may carry.
STATUS_TOP_LEVEL = frozenset({STATUS_DIR})

#: Remote objects the status sync may delete when absent locally — everything
#: under ``status/`` EXCEPT the append-only archive prefix.
_DELETE_PREFIX = f"{STATUS_DIR}/"
_NEVER_DELETE_PREFIX = ARCHIVE_PREFIX


class StatusPublishError(PublishError):
    """The status publish leg refused."""


def emit_status_tree(
    *,
    runs_path: str | Path,
    sources_path: str | Path,
    out_dir: str | Path,
    cadence_path: str | Path | None = None,
    scheduler_report_path: str | Path | None = None,
    release: Mapping[str, Any] | None = None,
    status_time: str,
    known_issues_path: str | Path | None = None,
) -> dict[str, Path]:
    """Render the lane file set (``emit`` mode — the dry-run publish)."""
    from exports.known_issues import load_known_issues

    runs = load_run_records(runs_path)
    sources = load_source_rows(sources_path)
    lane = build_status_lane(
        runs=runs,
        sources_doc=sources,
        crons=cadence_crons(cadence_path),
        scheduler_report=load_scheduler_report(scheduler_report_path),
        release=release,
        status_time=parse_status_time(status_time),
        known_issues=load_known_issues(known_issues_path),
    )
    return emit_status_files(lane, out_dir)


def assert_status_tree(tree: Path) -> None:
    """The status-scoped allow-list assertion: the tree's top level is exactly
    ``status/`` and nothing else — plus the shared content + secret gates."""
    if not tree.is_dir():
        raise StatusPublishError(f"status tree {tree} is not a directory")
    top = {p.name for p in tree.iterdir()}
    if top != {STATUS_DIR}:
        raise StatusPublishError(
            "status publish refused — the tree's top level must be exactly "
            f"status/ (got {sorted(top)}); the lane publishes only status/**"
        )
    status = tree / STATUS_DIR
    files = [p for p in status.rglob("*") if p.is_file()]
    if not files:
        raise StatusPublishError("status publish refused — status/ is empty")
    if not (status / "state.json").is_file():
        raise StatusPublishError("status publish refused — status/state.json is required")
    assert_public_tree_content(tree)
    assert_publish_set_secret_free(tree)


def plan_status_sync(
    local_names: list[str],
    remote_names: list[str] | None,
) -> dict[str, list[str]]:
    """The bounded sync plan: writes for every local ``status/**`` object;
    deletes only remote ``status/`` objects absent locally and never under
    ``status/archive/`` (append-only). ``remote_names=None`` → deletions
    uncomputed (local-only plan)."""
    puts = [n for n in local_names if n.startswith(_DELETE_PREFIX)]
    if any(not n.startswith(_DELETE_PREFIX) for n in local_names):
        raise StatusPublishError(
            "status publish plan refused — a local file outside status/: "
            + ", ".join(n for n in local_names if not n.startswith(_DELETE_PREFIX))
        )
    deletes: list[str] = []
    if remote_names is not None:
        local = set(local_names)
        deletes = [
            n
            for n in remote_names
            if n.startswith(_DELETE_PREFIX)
            and not n.startswith(_NEVER_DELETE_PREFIX)
            and n not in local
        ]
    return {"put": sorted(puts), "delete": sorted(deletes)}


def publish_status_tree(
    tree: Path,
    *,
    bucket: GcsBucket | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """The status-scoped publish leg: assert → plan → (apply) sync → verify.

    ``apply=False`` prints the same plan read-only. A bucket handle is
    required for ``--apply`` — the hosted env carries it (SIG_STATUS_BUCKET);
    without one the apply refuses (the queue posture, never a soft pass).
    """
    assert_status_tree(tree)
    local_names = [p.relative_to(tree).as_posix() for p in sorted(tree.rglob("*")) if p.is_file()]
    remote: list[str] | None = None
    if bucket is not None:
        remote = bucket.list_objects(STATUS_DIR + "/")
    plan = plan_status_sync(local_names, remote)
    result: dict[str, Any] = {"plan": plan, "applied": False}
    if not apply:
        return result
    if bucket is None:
        raise StatusPublishError(
            "status publish --apply needs the destination bucket "
            "(SIG_STATUS_BUCKET) — the leg queues prepared_not_executed, "
            "never a partial write"
        )
    for name in plan["put"]:
        bucket.put_object(
            name,
            (tree / name).read_bytes(),
            content_type=_content_type(name),
        )
    for name in plan["delete"]:
        bucket.delete_object(name)
    # Verify: the heartbeat reads back and parses.
    raw = bucket.get_object(f"{STATUS_DIR}/state.json")
    doc = json.loads(raw)
    if doc.get("schema") != "sig.status-heartbeat/1":
        raise StatusPublishError(
            "status publish verify failed — state.json did not read back as sig.status-heartbeat/1"
        )
    result["applied"] = True
    result["verified"] = True
    return result


def _content_type(name: str) -> str:
    if name.endswith(".json"):
        return "application/json"
    if name.endswith(".html"):
        return "text/html; charset=utf-8"
    return "application/octet-stream"


def run_status_publish(args: Any) -> int:
    """``sig-ops status-publish`` — emit the lane file set, or emit + apply the
    scoped sync. Exit 0 ok · 2 usage/refusal."""
    out = Path(args.out)
    release: dict[str, Any] | None = None
    if args.release:
        release = json.loads(Path(args.release).read_text(encoding="utf-8"))
    try:
        written = emit_status_tree(
            runs_path=args.runs,
            sources_path=args.sources,
            out_dir=out,
            cadence_path=args.cadence,
            scheduler_report_path=args.scheduler_report,
            release=release,
            status_time=args.status_time,
            known_issues_path=args.known_issues,
        )
    except (StatusLaneError, OSError, json.JSONDecodeError) as exc:
        print(f"status-publish emit refused: {exc}")
        return 2
    print(f"status-publish emit: {len(written)} files under {out}/status/")
    if not args.apply:
        return 0
    bucket_name = args.bucket or os.environ.get("SIG_STATUS_BUCKET", "").strip()
    if not bucket_name:
        print(
            "status-publish --apply queued: SIG_STATUS_BUCKET unset — the "
            "hosted env is absent (prepared_not_executed; re-run prompt is "
            "the ticket's live_verification=true line)"
        )
        return 42
    try:
        result = publish_status_tree(out, bucket=GcsBucket(bucket_name), apply=True)
    except PublishError as exc:
        print(f"status-publish --apply refused: {exc}")
        return 2
    plan = result["plan"]
    print(
        f"status-publish --apply: {len(plan['put'])} put, "
        f"{len(plan['delete'])} delete (archive never deleted), verified heartbeat"
    )
    return 0
