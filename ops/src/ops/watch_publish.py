# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.33 (K7 WX-03, D-K7-2 [B-22] = the lane) — the watch lane's emit +
watch-scoped publish leg.

``sig-ops watch-publish emit`` renders the lane file set from a
``sig/watch/2`` payload (the dry-run publish that proves the artifact
shape — the fixture leg this ticket exercises). ``sig-ops watch-publish
--apply`` runs the same emit then pushes ``watch/**`` through the
watch-scoped half of the one allow-listed publish path (P34.10 /
SIG-OPS-003/004 — the G3 §4.4 publish class **status** extended to
``watch/**``, D-K7-2): the same assertion → record → sync → verify
discipline, scoped to the ``watch/`` namespace by
``ops/public_routes_watch.toml``. It writes only ``watch/**`` objects and
deletes only **lane-owned** ``watch/`` objects it does not emit — never
``watch/archive/**`` (append-only, P1–P3) and never the release web
build's facet/history/feed/pagination/citations paths (the lane owns the
index, place and item pages plus its three JSON documents — nothing
else, so a daily refresh can never remove a page it does not render).

The job + trigger create (Cloud Run job + Cloud Scheduler trigger, daily)
is the OM-20 named mutation — ``ops/gcp/watch-publish.sh`` owns that leg;
the lane job's scheduled `production` run is restore-pointed by pausing
the trigger ("lane job paused").
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
from .watch_lane import (
    ARCHIVE_PREFIX,
    HEARTBEAT_PATH,
    LANE_DOC_PATH,
    WATCH_DIR,
    WatchLaneError,
    build_watch_lane,
    emit_watch_files,
    lane_owns_object,
    load_watch_payload,
    parse_lane_time,
)

#: The lane's scoped allow-list (``ops/public_routes_watch.toml``): the only
#: top-level entry a watch publish tree may carry.
WATCH_TOP_LEVEL = frozenset({WATCH_DIR})

#: Remote objects the watch sync may delete when absent locally — everything
#: under ``watch/`` that is lane-owned (see ``lane_owns_object``) EXCEPT the
#: append-only archive prefix.
_DELETE_PREFIX = f"{WATCH_DIR}/"
_NEVER_DELETE_PREFIX = ARCHIVE_PREFIX


class WatchPublishError(PublishError):
    """The watch publish leg refused."""


def emit_watch_tree(
    *,
    watch_path: str | Path,
    out_dir: str | Path,
    release: Mapping[str, Any] | None = None,
    lane_time: str,
) -> dict[str, Path]:
    """Render the lane file set (``emit`` mode — the dry-run publish)."""
    payload = load_watch_payload(watch_path)
    lane = build_watch_lane(
        payload=payload,
        release=release,
        lane_time=parse_lane_time(lane_time),
    )
    return emit_watch_files(payload, lane, out_dir)


def assert_watch_tree(tree: Path) -> None:
    """The watch-scoped allow-list assertion: the tree's top level is exactly
    ``watch/`` and nothing else — plus the shared content + secret gates."""
    if not tree.is_dir():
        raise WatchPublishError(f"watch tree {tree} is not a directory")
    top = {p.name for p in tree.iterdir()}
    if top != {WATCH_DIR}:
        raise WatchPublishError(
            "watch publish refused — the tree's top level must be exactly "
            f"watch/ (got {sorted(top)}); the lane publishes only watch/**"
        )
    watch = tree / WATCH_DIR
    files = [p for p in watch.rglob("*") if p.is_file()]
    if not files:
        raise WatchPublishError("watch publish refused — watch/ is empty")
    for required in (HEARTBEAT_PATH, LANE_DOC_PATH):
        if not (tree / required).is_file():
            raise WatchPublishError(f"watch publish refused — {required} is required")
    assert_public_tree_content(tree)
    assert_publish_set_secret_free(tree)


def plan_watch_sync(
    local_names: list[str],
    remote_names: list[str] | None,
) -> dict[str, list[str]]:
    """The bounded sync plan: writes for every local ``watch/**`` object;
    deletes only remote objects that are lane-owned, absent locally and
    never under ``watch/archive/`` (append-only). The release web build's
    own watch pages (facets, history, pagination, citations, feeds) are
    never lane-owned — a refresh can never delete them.
    ``remote_names=None`` → deletions uncomputed (local-only plan)."""
    puts = [n for n in local_names if n.startswith(_DELETE_PREFIX)]
    if any(not n.startswith(_DELETE_PREFIX) for n in local_names):
        raise WatchPublishError(
            "watch publish plan refused — a local file outside watch/: "
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
            and lane_owns_object(n)
            and n not in local
        ]
    return {"put": sorted(puts), "delete": sorted(deletes)}


def publish_watch_tree(
    tree: Path,
    *,
    bucket: GcsBucket | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """The watch-scoped publish leg: assert → plan → (apply) sync → verify.

    ``apply=False`` prints the same plan read-only. A bucket handle is
    required for ``--apply`` — the hosted env carries it (SIG_WATCH_BUCKET);
    without one the apply refuses (the queue posture, never a soft pass).
    """
    assert_watch_tree(tree)
    local_names = [p.relative_to(tree).as_posix() for p in sorted(tree.rglob("*")) if p.is_file()]
    remote: list[str] | None = None
    if bucket is not None:
        remote = bucket.list_objects(WATCH_DIR + "/")
    plan = plan_watch_sync(local_names, remote)
    result: dict[str, Any] = {"plan": plan, "applied": False}
    if not apply:
        return result
    if bucket is None:
        raise WatchPublishError(
            "watch publish --apply needs the destination bucket "
            "(SIG_WATCH_BUCKET) — the leg queues prepared_not_executed, "
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
    raw = bucket.get_object(HEARTBEAT_PATH)
    doc = json.loads(raw)
    if doc.get("schema") != "sig.watch-heartbeat/1":
        raise WatchPublishError(
            "watch publish verify failed — state.json did not read back as sig.watch-heartbeat/1"
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


def run_watch_publish(args: Any) -> int:
    """``sig-ops watch-publish`` — emit the lane file set, or emit + apply the
    scoped sync. Exit 0 ok · 2 usage/refusal · 42 queued."""
    out = Path(args.out)
    release: dict[str, Any] | None = None
    if args.release:
        release = json.loads(Path(args.release).read_text(encoding="utf-8"))
    try:
        written = emit_watch_tree(
            watch_path=args.watch,
            out_dir=out,
            release=release,
            lane_time=args.lane_time,
        )
    except (WatchLaneError, OSError, json.JSONDecodeError) as exc:
        print(f"watch-publish emit refused: {exc}")
        return 2
    print(f"watch-publish emit: {len(written)} files under {out}/watch/")
    if not args.apply:
        return 0
    bucket_name = args.bucket or os.environ.get("SIG_WATCH_BUCKET", "").strip()
    if not bucket_name:
        print(
            "watch-publish --apply queued: SIG_WATCH_BUCKET unset — the "
            "hosted env is absent (prepared_not_executed; re-run prompt is "
            "the ticket's live_verification=true line)"
        )
        return 42
    try:
        result = publish_watch_tree(out, bucket=GcsBucket(bucket_name), apply=True)
    except PublishError as exc:
        print(f"watch-publish --apply refused: {exc}")
        return 2
    plan = result["plan"]
    print(
        f"watch-publish --apply: {len(plan['put'])} put, "
        f"{len(plan['delete'])} delete (archive never deleted; non-lane-owned "
        "watch paths never touched), verified heartbeat"
    )
    return 0
