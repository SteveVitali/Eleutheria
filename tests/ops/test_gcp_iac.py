# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The GCP infra-as-code validates to green WITHOUT ADC (P24.1 / GL-DEPLOY-01).

These are the deterministic proxies the ticket requires for the written+validated
IaC (rule-6 FULL green): the `--check`/dry-run path of the `ops/gcp/` scripts runs
with no Application Default Credentials, opens no network, and exits 0 while
printing the plan; `sig-ops deploy --target gcp --dry-run` does the same; and no
secret/token literal (and no literal project id) lives in the IaC. The real
`apply`/deploy is gate-pending on operator ADC (D-DEPLOY.1-1 / HG-12).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GCP_DIR = REPO_ROOT / "ops" / "gcp"
SHELL_SCRIPTS = ["config.sh", "lib.sh", "provision.sh", "backup.sh", "schedule.sh"]
EXECUTABLE_SCRIPTS = ["provision.sh", "backup.sh", "schedule.sh"]


def _no_adc_env() -> dict[str, str]:
    """A subprocess env with any ADC / project id stripped, to prove no-creds green."""
    env = {k: v for k, v in os.environ.items() if k not in {"SIG_GCP_PROJECT"}}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    # Point gcloud's ADC search at an empty dir so a stray host credential can't leak in.
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    return env


def test_shell_scripts_parse_with_bash_n() -> None:
    for name in SHELL_SCRIPTS:
        proc = subprocess.run(
            ["bash", "-n", str(GCP_DIR / name)], capture_output=True, text=True, check=False
        )
        assert proc.returncode == 0, f"bash -n failed for {name}: {proc.stderr}"


@pytest.mark.parametrize("script", EXECUTABLE_SCRIPTS)
def test_check_dry_run_is_green_without_adc(script: str) -> None:
    """`--check` prints the plan, uses no ADC, opens no network, and exits 0."""
    proc = subprocess.run(
        ["bash", str(GCP_DIR / script), "--check"],
        capture_output=True,
        text=True,
        check=False,
        env=_no_adc_env(),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, f"{script} --check exited {proc.returncode}: {proc.stderr}"
    assert "PLAN:" in proc.stdout, f"{script} --check printed no plan"
    assert "check OK" in proc.stdout


def test_terraform_validates_if_present_else_gcloud_scripts_are_the_iac() -> None:
    """If terraform + .tf files are present, `terraform validate`; else the gcloud path.

    The IaC form (ADR-075) is idempotent gcloud scripts (terraform is not on PATH in
    this build). This test fails loudly if that ever changes without the tests keeping
    up: a committed `.tf` set must validate under a present `terraform`.
    """
    tf_files = list(GCP_DIR.glob("*.tf"))
    if shutil.which("terraform") and tf_files:
        proc = subprocess.run(
            ["terraform", "-chdir=" + str(GCP_DIR), "validate", "-no-color"],
            capture_output=True,
            text=True,
            check=False,
            env=_no_adc_env(),
        )
        assert proc.returncode == 0, f"terraform validate failed: {proc.stderr}"
    else:
        # The gcloud-script IaC is the chosen form: its dry-run path must be green.
        assert not tf_files, "found .tf files but terraform is absent — install terraform"
        proc = subprocess.run(
            ["bash", str(GCP_DIR / "provision.sh"), "--check"],
            capture_output=True,
            text=True,
            check=False,
            env=_no_adc_env(),
            cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0


def test_deploy_dry_run_exits_zero_and_prints_plan_without_network() -> None:
    proc = subprocess.run(
        ["uv", "run", "sig-ops", "deploy", "--target", "gcp", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        env=_no_adc_env(),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, f"deploy --dry-run exited {proc.returncode}: {proc.stderr}"
    assert "plan:" in proc.stdout
    assert "Artifact Registry" in proc.stdout
    assert "gs://" in proc.stdout  # the GCS sync steps are in the plan


# --- no secret / token / project-id literal in the IaC (RISK-P21-05, D3) ------

# A credential VALUE literal — a token/key/password variable assigned a non-empty,
# non-$var string. This deliberately does NOT match `SIG_SECRET_*` variables, which
# hold Secret Manager container names (references, not values) — the sanctioned
# pattern. It matches an actual leak: a token/key/PGPASSWORD var set to a raw string.
_CRED_LITERAL = re.compile(
    r"""(?x)
    \b(?:SIG_[A-Z0-9_]*(?:TOKEN|KEY)|PGPASSWORD|api_key)\b
    \s*=\s*["'][^"'$][^"']*["']
    """
)


def _iac_files() -> list[Path]:
    files = [GCP_DIR / n for n in SHELL_SCRIPTS]
    files.append(GCP_DIR / "README.md")
    files.append(REPO_ROOT / "ops" / "Dockerfile")
    files += [REPO_ROOT / "ops" / "src" / "ops" / f"{m}.py" for m in ("deploy", "backup")]
    return [f for f in files if f.is_file()]


def test_no_credential_literal_in_the_iac() -> None:
    offenders: list[str] = []
    for path in _iac_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "os.environ" in line or "getenv" in line:
                continue
            if _CRED_LITERAL.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, "credential literal(s) in the IaC:\n" + "\n".join(offenders)


def test_iac_references_secret_manager_and_env_project() -> None:
    """Secrets are Secret Manager references by NAME; the project is env-resolved."""
    provision = (GCP_DIR / "provision.sh").read_text(encoding="utf-8")
    assert "secrets create" in provision  # Secret Manager containers, names only
    assert "--set-secrets=" in provision  # Cloud Run reads secrets by name
    config = (GCP_DIR / "config.sh").read_text(encoding="utf-8")
    assert "SIG_GCP_PROJECT" in config  # the project id is env-parameterised
