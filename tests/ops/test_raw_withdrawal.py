# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.36 (TX-12 / SIG-TRANSP-020) — the withdrawal delete/purge/tombstone
rehearsal over fixture roots (J3 §9.2: object deleted from mirror + origin,
CDN purge by URL, 410 + tombstone at the web path, 404 at the mirror)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from ops.raw_withdrawal import REHEARSAL_SCHEMA, RehearsalError, rehearse_withdrawal
from policy.eligibility import ReasonCategory


def _roots(tmp_path: Path) -> dict[str, Path]:
    mirror = tmp_path / "mirror"
    origin = tmp_path / "origin"
    staged = tmp_path / "staged"
    registry = tmp_path / "registry"
    for d in (mirror / "raw", origin / "raw", staged / "raw", registry):
        d.mkdir(parents=True)
    (staged / "conf").mkdir()
    return {"mirror": mirror, "origin": origin, "staged": staged, "registry": registry}


def test_rehearsal_delete_purge_tombstone(tmp_path) -> None:
    roots = _roots(tmp_path)
    digest = "b3fa3d7a1c"
    (roots["mirror"] / "raw" / digest).write_bytes(b"raw-bytes")
    (roots["origin"] / "raw" / digest).write_bytes(b"raw-bytes")
    (roots["staged"] / "raw" / digest).write_bytes(b"raw-bytes")
    purged: list[str] = []

    def cdn_purge(urls: list[str]) -> list[str]:
        purged.extend(urls)
        return list(urls)

    def web_probe(path: str) -> tuple[int, bytes]:
        body = roots["staged"] / "conf" / "tombstone"
        # the staged barrier answers 410 + the tombstone body for the route
        route_hash = None

        route_hash = __import__("hashlib").sha256(path.lstrip("/").encode()).hexdigest()[:24]
        tomb = body / f"{route_hash}.json"
        if tomb.is_file():
            return 410, tomb.read_bytes()
        return 404, b""

    def mirror_probe(path: str) -> tuple[int, bytes]:
        target = roots["mirror"] / path.lstrip("/")
        return (200, target.read_bytes()) if target.is_file() else (404, b"")

    result = rehearse_withdrawal(
        object_rel=f"raw/{digest}",
        mirror_root=roots["mirror"],
        origin_root=roots["origin"],
        staged_root=roots["staged"],
        registry_dir=roots["registry"],
        cdn_purge=cdn_purge,
        web_probe=web_probe,
        mirror_probe=mirror_probe,
        authority="operator rehearsal",
        reason_category=ReasonCategory.RIGHTS_WITHDRAWAL,
        decided_at=datetime(2026, 11, 11, 9, 0, 0),
    )
    doc = result.as_json()
    assert doc["schema"] == REHEARSAL_SCHEMA and doc["ok"]
    assert result.legs["delete"] == {"mirror": "deleted", "origin": "deleted", "ok": True}
    assert purged == [f"/raw/{digest}"]
    # tombstone disposition landed append-only + the route denied
    withdrawals = json.loads((roots["registry"] / "withdrawals.json").read_text())
    assert withdrawals["entries"][-1]["target_id"] == f"raw/{digest}"
    assert withdrawals["entries"][-1]["disposition"] == "withdraw"
    assert result.legs["tombstone"]["routes_denied"] == 1
    # 410 + tombstone at the web path; 404 at the mirror (the staged tree's
    # object was removed whole by the barrier)
    assert not (roots["staged"] / "raw" / digest).exists()
    assert result.legs["verify"]["web_status"] == 410
    assert result.legs["verify"]["mirror_status"] == 404


def test_rehearsal_absent_object_is_recorded(tmp_path) -> None:
    roots = _roots(tmp_path)
    digest = "b3ee00"
    result = rehearse_withdrawal(
        object_rel=f"raw/{digest}",
        mirror_root=roots["mirror"],
        origin_root=roots["origin"],
        staged_root=roots["staged"],
        registry_dir=roots["registry"],
        cdn_purge=lambda urls: list(urls),
        web_probe=lambda p: (404, b""),
        mirror_probe=lambda p: (404, b""),
        authority="operator rehearsal",
        decided_at=datetime(2026, 11, 11, 9, 0, 0),
    )
    assert result.legs["delete"]["mirror"] == "absent"
    assert result.legs["delete"]["origin"] == "absent"
    # the disposition lands append-only; a never-pushed object has no staged
    # route to deny (the barrier denies what the tree carries — honestly 0)
    assert result.legs["tombstone"]["routes_denied"] == 0
    assert result.legs["verify"]["ok"] is False  # the probe found no tombstone


def test_rehearsal_refuses_non_raw_path(tmp_path) -> None:
    roots = _roots(tmp_path)
    with pytest.raises(RehearsalError):
        rehearse_withdrawal(
            object_rel="r/pub-1/c/web/entity/site/x",
            mirror_root=roots["mirror"],
            origin_root=roots["origin"],
            staged_root=roots["staged"],
            registry_dir=roots["registry"],
            cdn_purge=lambda urls: list(urls),
            web_probe=lambda p: (404, b""),
            mirror_probe=lambda p: (404, b""),
            authority="operator rehearsal",
        )


def test_rehearsal_refuses_empty_authority(tmp_path) -> None:
    roots = _roots(tmp_path)
    with pytest.raises(RehearsalError):
        rehearse_withdrawal(
            object_rel="raw/b3aa",
            mirror_root=roots["mirror"],
            origin_root=roots["origin"],
            staged_root=roots["staged"],
            registry_dir=roots["registry"],
            cdn_purge=lambda urls: list(urls),
            web_probe=lambda p: (404, b""),
            mirror_probe=lambda p: (404, b""),
            authority="",
        )
