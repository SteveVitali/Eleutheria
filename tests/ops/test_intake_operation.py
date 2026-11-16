# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.59 — the dark ``sig-intake`` receiver declaration (offline legs).

The contract's engineering half is declaration discipline: the service spec
carries ``SIG_INTAKE_ENABLED=1`` (the honest ``503 receiver_not_operating``)
and **never** ``SIG_INTAKE_OPERATIONAL``; ingress is internal with no public
invoker; the three Secret Manager *names* mount as env (never values); the
``_Default``-sink exclusion is scoped to the requests stream alone; and the
``/intake/*`` LB rule plus ``[intake].operational`` stay dark in their
committed files. The windowed runner (``ops/gcp/intake-roll.sh``) is covered
by ``test_gcp_iac.py``'s no-ADC check sweep.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
from ops.intake_operation import (
    INFRA_POSTURE,
    INTAKE_SA,
    LOG_EXCLUSIONS,
    SERVICE,
    main,
    plan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
IAM_TOML = REPO_ROOT / "ops" / "iam_identities.toml"
LB_ROUTES = REPO_ROOT / "ops" / "lb_routes.toml"
OPS_CONFIG = REPO_ROOT / "ops" / "config.toml"
LEG = REPO_ROOT / "ops" / "gcp" / "intake-roll.sh"


def _iam() -> dict:
    return tomllib.loads(IAM_TOML.read_text())


def test_service_is_dark_and_never_arms_the_gate() -> None:
    assert SERVICE.name == "sig-intake"
    assert SERVICE.service_account == "sig-intake-rt"
    assert SERVICE.image_source_service == "sig-api"  # deploy-by-digest, ADR-111
    assert SERVICE.env["SIG_INTAKE_ENABLED"] == "1"
    # The armed kill-switch is absent from every declared surface.
    assert "SIG_INTAKE_OPERATIONAL" not in SERVICE.env
    assert "SIG_INTAKE_OPERATIONAL" not in SERVICE.secret_env
    assert "SIG_INTAKE_OPERATIONAL" in SERVICE.never_env
    assert SERVICE.allow_unauthenticated is False
    assert SERVICE.ingress == "internal"
    assert (SERVICE.min_instances, SERVICE.max_instances) == (0, 2)
    assert SERVICE.port == 8080
    # The serve-intake argv is env-assembled — no credential literal.
    argv = " ".join(SERVICE.command + SERVICE.args)
    assert "serve-intake" in argv
    assert "sig_intake_receiver_login" in argv
    assert "password" not in argv.lower().replace("_password", "")
    assert "ops/config.toml" in argv


def test_secret_env_mounts_names_only() -> None:
    expected = {
        "SIG_INTAKE_DB_PASSWORD": "sig-intake-receiver-password",
        "SIG_INTAKE_FORM_SECRET": "sig-intake-form-secret",
        "SIG_INTAKE_ABUSE_SECRET": "sig-intake-abuse-secret",
    }
    assert SERVICE.secret_env == expected


def test_log_exclusion_is_scoped_to_the_requests_stream_only() -> None:
    assert len(LOG_EXCLUSIONS) == 1
    excl = LOG_EXCLUSIONS[0]
    assert excl.sink == "_Default"
    assert excl.name == "sig-intake-request-logs"
    assert 'service_name="sig-intake"' in excl.filter
    # The log_id clause keeps the blackout scoped — stdout/stderr stay.
    assert 'log_id("run.googleapis.com/requests")' in excl.filter


def test_infra_posture_discloses_copies_never_no_copies() -> None:
    text = " ".join(INFRA_POSTURE).lower()
    assert "logical-export" in text or "sql export" in text
    assert "backup" in text
    # The disclosure is honest: it names retention bounds, never "no copies".
    assert "no copies" not in text


def test_iam_declarations_match_the_service() -> None:
    iam = _iam()
    sa_ids = [sa["id"] for sa in iam["service_account"]]
    assert INTAKE_SA in sa_ids
    svc = {s["name"]: s["service_account"] for s in iam["service"]}
    assert svc["sig-intake"] == INTAKE_SA
    secrets = {s["name"]: s["consumers"] for s in iam["secret"]}
    for name in SERVICE.secret_env.values():
        assert name in secrets, f"{name} missing from iam_identities.toml"
    assert secrets["sig-intake-receiver-password"] == [INTAKE_SA]
    assert secrets["sig-intake-reviewer-password"] == ["operator"]


def test_committed_posture_files_stay_dark() -> None:
    """The two files the dark posture lives in are asserted, not assumed."""
    routes = tomllib.loads(LB_ROUTES.read_text())
    intake = [r for r in routes["rule"] if r.get("service") == "intake"]
    assert intake, "lb_routes.toml lost its written-not-applied /intake/* rule"
    for rule in intake:
        assert rule.get("enabled") is False
    cfg = tomllib.loads(OPS_CONFIG.read_text())
    assert cfg["intake"]["operational"] is False
    assert cfg["intake"]["staffed"] is False
    assert cfg["intake"]["owner"] == ""


def test_leg_script_never_sets_the_operational_flag() -> None:
    src = LEG.read_text()
    # The flag may appear only inside comments / the verify assertion — never
    # in a deploy env assignment. Any --set-env-vars line must exclude it.
    for line in src.splitlines():
        if "--set-env-vars" in line or line.strip().startswith("ENV_VARS="):
            assert "SIG_INTAKE_OPERATIONAL" not in line
    assert re.search(r"SERV[IE]CE.*OPERATIONAL\s*=", src) is None


def test_plan_json_shape() -> None:
    doc = plan()
    assert doc["schema"] == "sig.intake-operation/1"
    assert doc["ticket"] == "P37.59"
    assert "dark" in doc["posture"]
    svc = doc["service"]
    assert svc["name"] == "sig-intake"
    assert svc["allow_unauthenticated"] is False
    assert "SIG_INTAKE_OPERATIONAL" not in svc["env"]
    assert doc["log_exclusions"][0]["name"] == "sig-intake-request-logs"
    assert doc["lb_logging_enabled"] is False


def test_cli_plan_prints_the_declaration(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["plan"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["schema"] == "sig.intake-operation/1"


def test_sig_ops_intake_op_plan_via_subprocess() -> None:
    proc = subprocess.run(
        ["uv", "run", "sig-ops", "intake-op", "plan"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["ticket"] == "P37.59"
    assert doc["service"]["ingress"] == "internal"
