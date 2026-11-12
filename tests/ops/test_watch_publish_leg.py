# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.33 — the `sig-ops watch-publish` scoped leg + the gcp leg driver's posture."""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
import test_watch_lane as FIX
from ops.watch_lane import emit_watch_files

from ops import watch_publish as P

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ops/gcp/watch-publish.sh"
ALLOW = REPO / "ops/public_routes_watch.toml"


def _tree(tmp_path: Path) -> Path:
    payload = FIX._payload()
    emit_watch_files(payload, FIX._lane(payload), tmp_path)
    return tmp_path


def test_emit_then_assert_tree(tmp_path: Path) -> None:
    tree = _tree(tmp_path / "tree")
    P.assert_watch_tree(tree)
    bad = tmp_path / "bad"
    (bad / "watch").mkdir(parents=True)
    (bad / "status").mkdir()
    (bad / "watch" / "state.json").write_text("{}")
    with pytest.raises(P.WatchPublishError, match="top level"):
        P.assert_watch_tree(bad)


def test_plan_sync_never_deletes_non_lane_owned(tmp_path: Path) -> None:
    tree = _tree(tmp_path / "tree")
    local = [p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file()]
    remote = local + [
        "watch/kind/agenda_item/index.html",  # web build facet — never lane's
        "watch/tx.ics",  # web build feed — never lane's
        "watch/item/W-x/citations.txt",  # web build citation — never lane's
        "watch/archive/2026-11-09.json",  # archive — append-only, never deleted
        "watch/place/usa/ny/index.html",  # lane-owned, absent locally → delete
        "watch/item/W-old/index.html",  # lane-owned, absent locally → delete
    ]
    plan = P.plan_watch_sync(local, remote)
    assert plan["delete"] == [
        "watch/item/W-old/index.html",
        "watch/place/usa/ny/index.html",
    ]
    assert set(plan["put"]) == set(local)


def test_plan_sync_refuses_outside_watch(tmp_path: Path) -> None:
    with pytest.raises(P.WatchPublishError, match="outside watch/"):
        P.plan_watch_sync(["status/state.json"], None)


def test_allowlist_file_scopes_watch_only() -> None:
    doc = tomllib.loads(ALLOW.read_text())
    assert doc["allowlist"]["top_level"] == ["watch"]
    assert doc["allowlist"]["required"] == ["watch"]


def test_cli_emit_and_queued_apply(tmp_path: Path) -> None:
    payload_file = tmp_path / "watch.json"
    payload_file.write_text(json.dumps(FIX._payload()))
    out = tmp_path / "out"
    env = dict(os.environ)
    env.pop("SIG_WATCH_BUCKET", None)
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "ops",
            "watch-publish",
            "--watch",
            str(payload_file),
            "--lane-time",
            "2026-11-10T07:30:00Z",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "watch/state.json").is_file()
    proc2 = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "ops",
            "watch-publish",
            "--watch",
            str(payload_file),
            "--lane-time",
            "2026-11-10T07:30:00Z",
            "--out",
            str(out),
            "--apply",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO,
    )
    assert proc2.returncode == 42
    assert "queued" in proc2.stdout.lower()


# --- the gcp leg driver's offline posture -------------------------------------


def _run(args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("SIG_GCP_PROJECT", "test-project")
    env.pop("SIG_WATCH_AUTHOR", None)
    env.pop("SIG_JOB_IMAGE", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO
    )


def test_check_prints_plan_and_never_mutates() -> None:
    proc = _run(["--check"])
    assert proc.returncode == 0, proc.stderr
    assert "gcloud run jobs deploy sig-watch-publish" in proc.stdout
    assert "sig-sched-watch-publish" in proc.stdout
    assert "30 7 * * *" in proc.stdout  # the daily cron
    assert "prepared_not_executed" in proc.stdout


def test_check_carries_the_verbatim_rerun() -> None:
    proc = _run(["--check"])
    assert (
        "implement-spec spec=docs/tickets/457_P37.33__watch-lane-and-cadence.md"
        " live_verification=true"
    ) in proc.stdout


def test_apply_queues_when_env_absent() -> None:
    env = dict(os.environ)
    env["SIG_GCP_PROJECT"] = "test-project"
    env["SIG_WATCH_AUTHOR"] = "operator-2026-11-10"
    env["SIG_JOB_IMAGE"] = "sig-api@sha256:" + "a" * 64
    env["SIG_WATCH_SA_EMAIL"] = "sig-watch@test.iam.gserviceaccount.com"
    env["SIG_SCHEDULER_SA_EMAIL"] = "sig-sched@test.iam.gserviceaccount.com"
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply"], capture_output=True, text=True, env=env, cwd=REPO
    )
    assert proc.returncode in (42, 2, 3)
    if proc.returncode == 42:
        assert "QUEUED" in proc.stdout
