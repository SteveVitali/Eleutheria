# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""CI workflow structure gates (CI.1 / GL-CI-01, ADR-078).

These tests pin the `.github/workflows/ci.yml` + `nightly.yml` job structure:
if the composed job, the security scans, the PR doc gates, or the nightly
reporting steps are removed or gutted, a test here fails — the CI hardening
cannot silently rot. (The scanners themselves are exercised in
`test_security_scanners.py`.)
"""

from __future__ import annotations

from pathlib import Path

import yaml
from support import REPO_ROOT

CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
NIGHTLY_YML = REPO_ROOT / ".github" / "workflows" / "nightly.yml"


def _doc(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _runs(job: dict) -> list[str]:
    """Every `run:` body in a job's steps."""
    return [s.get("run", "") or "" for s in job.get("steps", [])]


def _uses(job: dict) -> list[str]:
    return [s.get("uses", "") or "" for s in job.get("steps", [])]


def _step_env(job: dict, needle: str) -> dict:
    """The env block of the step whose `run:` contains `needle`."""
    for s in job.get("steps", []):
        if needle in (s.get("run") or ""):
            return s.get("env") or {}
    return {}


# --- the composed job: tests/e2e FOR REAL, with Node + web deps --------------


def test_ci_composed_job_exists_and_runs_e2e() -> None:
    doc = _doc(CI_YML)
    job = doc["jobs"].get("composed")
    assert job is not None, "ci.yml must carry the `composed` job (GL-CI-01)"
    runs = _runs(job)
    assert any("pytest tests/e2e" in r for r in runs), "the composed job must run tests/e2e"


def test_ci_composed_job_fails_loudly_without_docker() -> None:
    """SIG_REQUIRE_DB_TESTS=1 on the pytest step → a missing daemon fails, never skips."""
    job = _doc(CI_YML)["jobs"]["composed"]
    env = _step_env(job, "pytest tests/e2e")
    assert env.get("SIG_REQUIRE_DB_TESTS") == "1", (
        "the composed e2e step must set SIG_REQUIRE_DB_TESTS=1"
    )


def test_ci_composed_job_installs_node_and_web_deps() -> None:
    """S8's web-build fixtures only run when npm + web/node_modules exist."""
    job = _doc(CI_YML)["jobs"]["composed"]
    assert any("setup-node" in u for u in _uses(job)), "composed job needs setup-node"
    runs = _runs(job)
    assert any("npm" in r and "ci" in r and "web" in r for r in runs), (
        "composed job must install web/node_modules (npm --prefix web ci)"
    )


def test_ci_composed_job_installs_the_workspace() -> None:
    job = _doc(CI_YML)["jobs"]["composed"]
    assert any("make sync" in r for r in _runs(job))


# --- the doc gates on PRs -----------------------------------------------------


def test_ci_docs_job_runs_only_on_pull_requests() -> None:
    doc = _doc(CI_YML)
    job = doc["jobs"].get("docs")
    assert job is not None
    assert "pull_request" in (job.get("if") or "")


def test_ci_docs_job_enforces_docs_check_and_build_memory() -> None:
    """Both `make docs-check` AND the explicit check-build-memory.sh step."""
    job = _doc(CI_YML)["jobs"]["docs"]
    runs = _runs(job)
    assert any("make docs-check" in r for r in runs), "docs job must run make docs-check"
    assert any("check-build-memory.sh" in r for r in runs), (
        "docs job must run check-build-memory.sh explicitly (GL-CI-01)"
    )


# --- the security job: secret + licence scans on every PR --------------------


def test_ci_security_job_runs_secret_and_license_scans() -> None:
    doc = _doc(CI_YML)
    job = doc["jobs"].get("security")
    assert job is not None, "ci.yml must carry the `security` job (GL-CI-01)"
    runs = _runs(job)
    assert any("scan-secrets" in r or "secret_scan" in r for r in runs)
    assert any("scan-licenses" in r or "license_scan" in r for r in runs)


# --- nightly: scheduled composed run + all three scans + a report -------------


def test_nightly_is_scheduled_and_manually_dispatchable() -> None:
    doc = _doc(NIGHTLY_YML)
    # PyYAML parses the bare `on:` key as boolean True (YAML 1.1).
    triggers = doc.get("on") or doc.get(True)
    assert triggers.get("schedule"), "nightly.yml must carry a cron schedule"
    assert any(s.get("cron") for s in triggers["schedule"])
    assert "workflow_dispatch" in triggers


def test_nightly_runs_composed_e2e_and_all_three_scans() -> None:
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    runs = _runs(job)
    assert any("pytest tests/e2e" in r for r in runs), "nightly must run tests/e2e"
    assert any("secret_scan" in r or "scan-secrets" in r for r in runs)
    assert any("license_scan" in r or "scan-licenses" in r for r in runs)
    assert any("dep_audit" in r or "audit-deps" in r for r in runs)


def test_nightly_e2e_fails_loudly_without_docker() -> None:
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    env = _step_env(job, "pytest tests/e2e")
    assert env.get("SIG_REQUIRE_DB_TESTS") == "1"


def test_nightly_reports_an_artifact_and_gates_on_failures() -> None:
    """The report step is the gate (exits non-zero on a failed stage); the
    artifact upload runs `if: always()` so a red nightly still carries evidence."""
    doc = _doc(NIGHTLY_YML)
    job = next(iter(doc["jobs"].values()))
    steps = job.get("steps", [])
    report = [s for s in steps if "nightly_report" in (s.get("run") or "")]
    assert report, "nightly must compose nightly-report.md via scripts/ci/nightly_report.py"
    uploads = [s for s in steps if "upload-artifact" in (s.get("uses") or "")]
    assert uploads, "nightly must upload the report artifact"
    assert any("always()" in (s.get("if") or "") for s in uploads), (
        "the report artifact must upload even when a stage failed"
    )
    paths = uploads[0].get("with", {}).get("path", "")
    assert "nightly-report.md" in paths


# --- workflows themselves carry no credential literals ------------------------


def test_workflow_files_have_no_credential_literals() -> None:
    """Workflows reference secrets only via ${{ secrets.* }} — the scanner itself
    asserts it (also covered by the tree-wide secret scan)."""
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/ci/secret_scan.py"),
            str(REPO_ROOT / ".github" / "workflows"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
