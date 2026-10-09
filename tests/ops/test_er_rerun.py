# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P34.45 v3-interim camera-site ER re-run leg (ops/gcp/er-rerun.sh +
the ``sig_materialize_login`` LoginRole spec + the er_rerun_login sqitch
change; ADR-153/206).

``--check`` runs with no ADC and no network and prints the whole plan; every
mutating action is window-gated, needs the recorded ``SIG_ER_RERUN_AUTHOR``,
and exits 42 (queued — never a partial apply) on any missing edge. The
login's shape is ``sig_materialize``'s append-only surface and nothing else:
INSERT+SELECT on the camera-site tables, UPDATE/DELETE/TRUNCATE refused, no
claim-spine write.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from ops.db_logins import (
    QUEUED,
    SIG_MATERIALIZE_LOGIN,
    resolve_role,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ER_RERUN_SH = REPO_ROOT / "ops" / "gcp" / "er-rerun.sh"
EXEC_HOST_TOML = REPO_ROOT / "ops" / "exec_host.toml"
IAM_TOML = REPO_ROOT / "ops" / "iam_identities.toml"
SQITCH_PLAN = REPO_ROOT / "db" / "sqitch.plan"

#: A timestamp inside the AR-3 window: ≥ 2026-10-13T12:00Z, outside
#: 03:00–06:30Z, outside the day-6→13 batch window.
#: future-ok: scheduled: the AR-3 contract bound the fixture clock sits inside
WINDOW_OK = "2026-10-14T15:00:00Z"  # future-ok: scheduled: fixture clock inside the AR-3 window


def _run(*args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env.pop("SIG_ER_RERUN_AUTHOR", None)
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(ER_RERUN_SH), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )


def test_check_is_green_without_adc() -> None:
    proc = _run("--check")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PLAN:" in proc.stdout and "check OK" in proc.stdout
    # The plan names the write-capable login and the append-only command —
    # never a password literal.
    assert "sig_materialize_login" in proc.stdout
    assert "camera-sites" in proc.stdout


def test_check_prints_every_guard() -> None:
    proc = _run("--check")
    assert proc.returncode == 0, proc.stderr + proc.stdout
    # The exactly-once bound and the API-roll edge are printed, not skipped.
    assert "3-interim" in proc.stdout
    assert "sig-er-rerun-password" in proc.stdout


@pytest.mark.parametrize("action", ["backup", "login", "run"])
def test_mutating_actions_queue_inside_the_never_mutate_slot(action: str) -> None:
    proc = _run(
        "--apply",
        action,
        env_extra={
            "SIG_ER_RERUN_NOW": "2026-10-14T04:00:00Z",  # future-ok: scheduled: AR-3 window clock
            "SIG_ER_RERUN_AUTHOR": "operator-test",
        },
    )
    assert proc.returncode == QUEUED, proc.stderr + proc.stdout
    assert "QUEUED" in proc.stdout
    assert "re-run:" in proc.stdout


@pytest.mark.parametrize("action", ["backup", "login", "run"])
def test_mutating_actions_queue_before_the_earliest(action: str) -> None:
    proc = _run(
        "--apply",
        action,
        env_extra={
            "SIG_ER_RERUN_NOW": "2026-10-13T11:00:00Z",  # future-ok: scheduled: pre-earliest clock
            "SIG_ER_RERUN_AUTHOR": "operator-test",
        },
    )
    assert proc.returncode == QUEUED, proc.stderr + proc.stdout


@pytest.mark.parametrize("action", ["backup", "login", "run"])
def test_mutating_actions_queue_inside_the_batch_window(action: str) -> None:
    proc = _run(
        "--apply",
        action,
        env_extra={
            # ≥ earliest, outside 03:00–06:30Z — but day 8 is inside the
            # monthly day-6→13 ingest batch window.
            "SIG_ER_RERUN_NOW": "2026-11-08T15:00:00Z",  # future-ok: synthetic: batch-window clock
            "SIG_ER_RERUN_AUTHOR": "operator-test",
        },
    )
    assert proc.returncode == QUEUED, proc.stderr + proc.stdout


@pytest.mark.parametrize("action", ["backup", "login", "run"])
def test_mutating_actions_queue_without_a_recorded_author(action: str) -> None:
    # Window OK — the recorded operator authorisation is still required.
    proc = _run("--apply", action, env_extra={"SIG_ER_RERUN_NOW": WINDOW_OK})
    assert proc.returncode == QUEUED, proc.stderr + proc.stdout
    assert "SIG_ER_RERUN_AUTHOR" in proc.stdout


# --- the sig_materialize_login spec -------------------------------------------


def test_sig_materialize_login_is_a_member_of_the_group_never_the_group() -> None:
    """The group's Round-6 grants are the whole surface — never duplicated."""
    spec = SIG_MATERIALIZE_LOGIN
    assert spec.name == "sig_materialize_login"
    assert spec.name != "sig_materialize"
    stmts = "\n".join(spec.statements)
    assert "CREATE ROLE sig_materialize_login LOGIN" in stmts
    assert "GRANT sig_materialize TO sig_materialize_login" in stmts
    assert "CREATE ROLE sig_materialize " not in stmts
    assert spec.requires_roles == ("sig_materialize",)
    assert spec.connection_limit == 2
    assert spec.memberships == ("sig_materialize",)


def test_sig_materialize_login_is_write_capable_but_append_only() -> None:
    """No read-only session default (it is the one write-capable login) and
    the refused-write probes name every mutation it must NOT hold."""
    spec = SIG_MATERIALIZE_LOGIN
    assert spec.rolconfig == ()  # grants bound it, not a session flag
    probes = "\n".join(spec.write_refusal_probes)
    assert "UPDATE camera_site_match" in probes
    assert "DELETE FROM camera_site_match" in probes
    assert "TRUNCATE camera_site_match" in probes
    assert "claim" in probes  # the claim spine has no INSERT/UPDATE/DELETE for it
    # And no probe names a statement the role may legitimately run.
    assert "INSERT INTO camera_site_match" not in probes


def test_sig_materialize_login_reads_the_er_surface_it_writes() -> None:
    spec = SIG_MATERIALIZE_LOGIN
    # INSERT ... RETURNING needs SELECT on the same tables; the queue rows too.
    for table in (
        "camera_site_match",
        "camera_site_run",
        "camera_site_execution",
        "review_item",
        "review_decision",
    ):
        assert table in spec.select_tables


def test_resolve_role_gains_the_login_alias_not_the_group() -> None:
    assert resolve_role("sig_materialize_login") is SIG_MATERIALIZE_LOGIN
    assert resolve_role("sig_er_rerun") is SIG_MATERIALIZE_LOGIN
    # The NOLOGIN group itself is still not a credential you can resolve.
    with pytest.raises(ValueError):
        resolve_role("sig_materialize")


# --- the declarations ----------------------------------------------------------


def test_exec_host_declaration_mounts_the_er_rerun_secret() -> None:
    decl = tomllib.loads(EXEC_HOST_TOML.read_text(encoding="utf-8"))
    pairs = {(s["env"], s["secret"]) for s in decl["secret_env"]}
    assert ("SIG_ER_RERUN_PASSWORD", "sig-er-rerun-password") in pairs


def test_iam_declaration_names_the_secret_and_its_only_consumer() -> None:
    decl = tomllib.loads(IAM_TOML.read_text(encoding="utf-8"))
    rows = {s["name"]: s for s in decl["secret"]}
    assert "sig-er-rerun-password" in rows
    # Only the exec host's runtime identity reads it (HG-09).
    assert rows["sig-er-rerun-password"]["consumers"] == ["sig-quality-probe-rt"]


def test_sqitch_change_is_declared_with_deploy_revert_verify() -> None:
    plan = SQITCH_PLAN.read_text(encoding="utf-8")
    assert "\ner_rerun_login " in plan or plan.startswith("er_rerun_login ")
    for kind in ("deploy", "revert", "verify"):
        p = REPO_ROOT / "db" / kind / "er_rerun_login.sql"
        assert p.is_file(), p
    deploy = (REPO_ROOT / "db" / "deploy" / "er_rerun_login.sql").read_text(encoding="utf-8")
    assert "CREATE ROLE sig_materialize_login LOGIN" in deploy
    assert "GRANT sig_materialize TO sig_materialize_login" in deploy
    # Guarded CREATE — the leg may have minted the role ahead of the deploy.
    assert "IF NOT EXISTS" in deploy
