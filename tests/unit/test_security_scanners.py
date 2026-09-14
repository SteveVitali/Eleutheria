# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Seeded-violation tests for the CI scanning gates (CI.1 / GL-CI-01, ADR-078).

"a seeded secret/license violation fails CI" is only meaningful if the scanner
demonstrably *catches* one — these tests run the real scripts
(`scripts/ci/secret_scan.py`, `license_scan.py`, `nightly_report.py`) as
subprocesses against seeded fixtures and assert the non-zero exit the CI step
would turn red. Remove a scanner or gut a rule and a test here fails.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from support import REPO_ROOT

SCRIPTS = REPO_ROOT / "scripts" / "ci"

# The canonical AWS documentation example key — a well-known *fake*, not a real
# credential (safe to seed; it is also exactly the shape the gate must catch).
# It is assembled so THIS test file carries no credential-shaped literal itself
# (the scanner scans tracked sources too — a seed in source would self-trip).
SEEDED_AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"


def _run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )


# --- secret_scan.py -----------------------------------------------------------


def test_secret_scan_real_tree_is_clean() -> None:
    """The committed tree passes the secret gate (baseline green)."""
    proc = _run("secret_scan.py")
    assert proc.returncode == 0, proc.stderr
    assert "0 credential shapes" in proc.stdout


def test_secret_scan_flags_a_seeded_aws_key(tmp_path: Path) -> None:
    leak = tmp_path / "leak.py"
    leak.write_text(f'AWS_KEY = "{SEEDED_AWS_KEY}"\n')
    proc = _run("secret_scan.py", str(leak))
    assert proc.returncode == 1, "a seeded AWS key must fail the scan"
    assert "leak.py:1" in proc.stderr
    assert "aws-access-key" in proc.stderr


def test_secret_scan_flags_seeded_pem_and_sig_literal(tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem_block = "-----BEGIN RSA " + "PRIVATE KEY-----\nMIIBOg==\n-----END RSA PRIVATE KEY-----\n"
    pem.write_text(pem_block)
    sig = tmp_path / "conf.sh"
    # The env-var name is assembled so THIS test file carries no credential-
    # shaped literal (tests/connectors/test_secrets.py gates .py sources); the
    # file written to disk still contains the full `SIG_*_TOKEN="…"` literal the
    # scanner must catch.
    var = "SIG_MUCKROCK" + "_TOKEN"
    sig.write_text(f'export {var}="a1b2c3d4e5f6"\n')
    proc = _run("secret_scan.py", str(pem), str(sig))
    assert proc.returncode == 1
    assert "pem-private-key" in proc.stderr
    assert "sig-credential-literal" in proc.stderr


def test_secret_scan_never_echoes_the_secret_itself(tmp_path: Path) -> None:
    """A scanner that prints the secret into the CI log is itself a leak."""
    leak = tmp_path / "leak.py"
    leak.write_text(f'AWS_KEY = "{SEEDED_AWS_KEY}"\n')
    proc = _run("secret_scan.py", str(leak))
    assert proc.returncode == 1
    assert SEEDED_AWS_KEY not in proc.stderr
    assert SEEDED_AWS_KEY not in proc.stdout


def test_secret_scan_clean_files_pass(tmp_path: Path) -> None:
    ok = tmp_path / "ok.py"
    ok.write_text('TOKEN = "short"\nname = "SIG_MUCKROCK_TOKEN"  # a name, not a value\n')
    proc = _run("secret_scan.py", str(ok))
    assert proc.returncode == 0, proc.stderr


# --- license_scan.py -----------------------------------------------------------


def _records(tmp_path: Path, records: list[dict]) -> Path:
    f = tmp_path / "records.json"
    f.write_text(json.dumps(records))
    return f


def test_license_scan_real_env_is_green() -> None:
    """The synced workspace env passes the licence gate (baseline green)."""
    proc = _run("license_scan.py")
    assert proc.returncode == 0, proc.stderr


def test_license_scan_rejects_a_denied_category(tmp_path: Path) -> None:
    """A seeded BUSL (source-available) dep must fail — the SIG-UI-039 exclusion."""
    f = _records(tmp_path, [{"name": "evil-dep", "licenses": ["BUSL-1.1"]}])
    proc = _run("license_scan.py", "--records-json", str(f))
    assert proc.returncode == 1
    assert "evil-dep" in proc.stderr and "EXCLUDED" in proc.stderr


def test_license_scan_rejects_an_unresolvable_license(tmp_path: Path) -> None:
    f = _records(tmp_path, [{"name": "mystery-dep", "licenses": ["Proprietary-Internal-v9"]}])
    proc = _run("license_scan.py", "--records-json", str(f))
    assert proc.returncode == 1  # PROPRIETARY is a denied category anyway
    f2 = _records(tmp_path, [{"name": "mystery-dep", "licenses": ["Some Weird License 9"]}])
    proc = _run("license_scan.py", "--records-json", str(f2))
    assert proc.returncode == 1, "an unresolvable licence must fail (review required)"
    assert "unresolvable" in proc.stderr or "could not be resolved" in proc.stderr


def test_license_scan_rejects_new_strong_copyleft(tmp_path: Path) -> None:
    """A NEW GPL/AGPL dep (not in the frozen expected set) fails the gate."""
    f = _records(
        tmp_path,
        [
            {"name": "new-gpl-dep", "licenses": ["GPL-3.0-only"]},
            {"name": "ok", "licenses": ["MIT"]},
        ],
    )
    proc = _run("license_scan.py", "--records-json", str(f))
    assert proc.returncode == 1
    assert "new-gpl-dep" in proc.stderr


def test_license_scan_accepts_clean_records(tmp_path: Path) -> None:
    f = _records(
        tmp_path,
        [
            {"name": "a", "licenses": ["MIT"]},
            {"name": "b", "licenses": ["(Apache-2.0 OR BSD-2-Clause)"]},
            {"name": "c", "licenses": ["License :: OSI Approved :: ISC License (ISCL)"]},
            {"name": "d", "licenses": ["LGPL-3.0-only"]},  # weak copyleft is allowed
        ],
    )
    proc = _run("license_scan.py", "--records-json", str(f))
    assert proc.returncode == 0, proc.stderr


# --- nightly_report.py ----------------------------------------------------------


def test_nightly_report_green_when_all_stages_pass(tmp_path: Path) -> None:
    out = tmp_path / "nightly-report.md"
    proc = _run(
        "nightly_report.py",
        "--out",
        str(out),
        "e2e=success",
        "secrets=success",
        "licenses=success",
        "depaudit=success",
    )
    assert proc.returncode == 0, proc.stderr
    text = out.read_text()
    assert "GREEN" in text and "| e2e | success |" in text


def test_nightly_report_fails_the_run_when_a_stage_fails(tmp_path: Path) -> None:
    """The report step is the gate: any non-success stage → exit 1 + a written report."""
    out = tmp_path / "nightly-report.md"
    proc = _run(
        "nightly_report.py",
        "--out",
        str(out),
        "e2e=success",
        "secrets=failure",
        "licenses=success",
        "depaudit=success",
    )
    assert proc.returncode == 1, "a failed stage must fail the nightly"
    text = out.read_text()
    assert "RED" in text and "secrets" in text
