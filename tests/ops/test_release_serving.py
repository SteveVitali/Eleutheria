# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.13 / ADR-132 (SIG-FIND-001/002) — the release-serving barrier verbs:
``sig-ops release-serve apply`` re-applies the current withdrawal registry to a
staged public tree (tombstones + the nginx deny map that evaluates BEFORE
origin access); ``check`` is the pure per-route access decision."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from exports.release import ReleaseRegistry
from ops.cli import main
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

from ops import release_serving

PUB = "p-" + "ab" * 32


def _staged(root: Path) -> Path:
    staged = root / "staged"
    rec_dir = staged / f"r/{PUB}/c/sig_graph/entity/deployment/ent-1"
    rec_dir.mkdir(parents=True)
    (rec_dir / "index.html").write_text("<html>record</html>")
    (staged / f"r/{PUB}/c/sig_graph/entity/deployment/ent-1.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (staged / f"r/{PUB}/c/sig_graph/entity/deployment/ent-1.json").write_text("{}")
    idx = staged / f"r/{PUB}/c/sig_graph/records.index.jsonl"
    idx.write_text(
        json.dumps(
            {
                "record_key": "sig_graph:deployment:ent-1",
                "entity_id": "ent-1",
                "entity_type": "deployment",
                "path": f"r/{PUB}/c/sig_graph/entity/deployment/ent-1/index.html",
                "json_path": f"r/{PUB}/c/sig_graph/entity/deployment/ent-1.json",
                "claim_ids": ["claim-1"],
                "jurisdiction": "OK",
                "label": "Site",
            }
        )
        + "\n"
    )
    return staged


def _registry(root: Path, withdraw: bool = False) -> Path:
    registry = root / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    if withdraw:
        reg = ReleaseRegistry(registry)
        reg.save_withdrawals(
            [
                new_disposition(
                    target_kind=TargetKind.ENTITY,
                    target_id="ent-1",
                    disposition=Disposition.WITHDRAW,
                    reason_category=ReasonCategory.RIGHTS_WITHDRAWAL,
                    authority="rights-holder request",
                    decided_at=datetime(2026, 9, 27, tzinfo=UTC),
                )
            ]
        )
    return registry


def test_apply_writes_tombstones_and_deny_map(tmp_path: Path) -> None:
    staged = _staged(tmp_path)
    registry = _registry(tmp_path, withdraw=True)
    out = release_serving.apply(registry, staged)
    assert out["denied"] >= 2
    html = (staged / f"r/{PUB}/c/sig_graph/entity/deployment/ent-1/index.html").read_text()
    assert "Record withdrawn" in html
    assert "rights_withdrawal" in html
    assert "rights-holder request" in html
    tomb = json.loads((staged / f"r/{PUB}/c/sig_graph/entity/deployment/ent-1.json").read_text())
    assert tomb["schema"] == "sig.tombstone/1"
    conf = (staged / "conf" / "withdrawn_routes.conf").read_text()
    assert "location =" in conf and "return 410" in conf
    assert f"/r/{PUB}/c/sig_graph/entity/deployment/ent-1/" in conf


def test_check_reports_current_disposition(tmp_path: Path) -> None:
    staged = _staged(tmp_path)
    registry = _registry(tmp_path, withdraw=True)
    release_serving.apply(registry, staged)
    route = f"r/{PUB}/c/sig_graph/entity/deployment/ent-1/"
    out = release_serving.check(registry, route)
    assert out["permitted"] is False
    assert out["tombstone"]["reason_category"] == "rights_withdrawal"
    other = release_serving.check(registry, f"r/{PUB}/c/sig_graph/entity/deployment/ent-2/")
    assert other["permitted"] is True


def test_cli_apply_and_check(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    staged = _staged(tmp_path)
    registry = _registry(tmp_path, withdraw=True)
    assert (
        main(
            [
                "release-serve",
                "apply",
                "--registry",
                str(registry),
                "--staged",
                str(staged),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "release-serve",
                "check",
                "--registry",
                str(registry),
                "--route",
                f"r/{PUB}/c/sig_graph/entity/deployment/ent-1/",
            ]
        )
        == 4
    )
    out = json.loads(capsys.readouterr().out)
    assert out["permitted"] is False


def test_apply_is_deterministic(tmp_path: Path) -> None:
    staged = _staged(tmp_path)
    registry = _registry(tmp_path, withdraw=True)
    a = release_serving.apply(registry, staged)
    b = release_serving.apply(registry, staged)
    assert a == b


def test_no_withdrawals_leaves_tree_untouched(tmp_path: Path) -> None:
    staged = _staged(tmp_path)
    registry = _registry(tmp_path, withdraw=False)
    out = release_serving.apply(registry, staged)
    assert out["denied"] == 0
    assert (
        "record" in (staged / f"r/{PUB}/c/sig_graph/entity/deployment/ent-1/index.html").read_text()
    )
    # an (empty) deny map still ships — nginx includes it unconditionally
    assert (staged / "conf" / "withdrawn_routes.conf").exists()
