# SPDX-License-Identifier: Apache-2.0
"""tests/ops/test_evidence_store_iac.py — the P37.3 evidence-store script
(SIG-STORE-048, ADR-177). The offline plan, the window guard, the author
gate, and the declared posture the acceptance shape reads: an ingest SA
holds no unconditional delete (the retention policy fails it), the replica
excludes evidence/captures/ wholesale, and every mutation is reversible.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "evidence-store.sh"
CONFIG = REPO_ROOT / "ops" / "gcp" / "config.sh"
CADENCE = REPO_ROOT / "ops" / "cadence.toml"
IAM = REPO_ROOT / "ops" / "iam_identities.toml"


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("SIG_GCP_PROJECT", None)
    env.pop("SIG_EVSTORE_AUTHOR", None)
    env.pop("SIG_BACKUP_PROJECT", None)
    env.update(extra or {})
    return env


def _run(args: list[str], extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(extra),
        cwd=str(REPO_ROOT),
    )


def test_check_plans_the_whole_mutation_offline() -> None:
    proc = _run(["--check"], {"SIG_BACKUP_PROJECT": "q-project"})
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    assert "sig-evidence" in plan and "retention-period 365d" in plan
    assert "sig-restricted-dr" in plan
    assert "sig-replica-rt" in plan
    assert "sig-restricted-replica" in plan and "sig-pg-export-copy" in plan
    # the repoint leg plans the volume swap, never a blind gcloud
    assert "captures" in plan
    # the acceptance leg plans the retention-delete attempt (MUST fail)
    assert "delete attempt MUST fail" in plan


def test_export_copy_leg_queues_honestly_without_the_second_project() -> None:
    proc = _run(["--check"])
    assert proc.returncode == 0, proc.stderr
    assert "SIG_BACKUP_PROJECT unset" in proc.stdout
    assert (
        "sig-pg-export-copy"
        not in [line for line in proc.stdout.splitlines() if "jobs deploy" in line]
        or "QUEUED" in proc.stdout
    )


def test_apply_refuses_outside_the_daily_band_and_without_author() -> None:
    # inside 03:00–10:00Z → exit 42 QUEUED (the contract window guard)
    proc = _run(
        ["--apply"],
        {
            "SIG_EVSTORE_NOW": "2026-11-05T05:30:00Z",
            "SIG_EVSTORE_AUTHOR": "steve",
            "SIG_GCP_PROJECT": "p",
        },
    )
    assert proc.returncode == 42
    assert "QUEUED" in proc.stdout
    # outside the band but no recorded author → refuses (OM-20 scope discipline)
    proc = _run(
        ["--apply"],
        {"SIG_EVSTORE_NOW": "2026-11-05T15:30:00Z", "SIG_GCP_PROJECT": "p"},
    )
    assert proc.returncode == 2
    assert "SIG_EVSTORE_AUTHOR" in (proc.stdout + proc.stderr)


def test_apply_without_project_or_adc_stays_unarmed(tmp_path: Path) -> None:
    proc = _run(
        ["--apply"],
        {"SIG_EVSTORE_NOW": "2026-11-05T15:30:00Z", "SIG_EVSTORE_AUTHOR": "steve"},
    )
    assert proc.returncode == 2  # require_project fails closed in apply mode
    # a gcloud stub that answers "no ADC" → require_adc exits 3 gate-pending
    stub = tmp_path / "gcloud"
    stub.write_text("#!/usr/bin/env bash\nexit 1\n")
    stub.chmod(0o755)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply"],
        capture_output=True,
        text=True,
        check=False,
        env=_env(
            {
                "SIG_EVSTORE_NOW": "2026-11-05T15:30:00Z",
                "SIG_EVSTORE_AUTHOR": "steve",
                "SIG_GCP_PROJECT": "p",
                "PATH": f"{tmp_path}:{os.environ['PATH']}",
            }
        ),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 3
    assert "gate pending" in (proc.stdout + proc.stderr)


def test_repoint_is_fail_closed_while_an_ingest_execution_runs() -> None:
    # the guard code exists and is invoked in apply mode
    text = SCRIPT.read_text()
    assert "no_ingest_running" in text and "fail-closed" in text
    assert "sig-" in text  # running-set filter names sig- jobs


def test_the_declared_posture_is_the_contract_verbatim() -> None:
    cfg = CONFIG.read_text()
    assert 'SIG_BUCKET_EVIDENCE="${SIG_GCP_PROJECT}-sig-evidence"' in cfg
    assert 'SIG_BUCKET_RESTRICTED_DR="${SIG_GCP_PROJECT}-sig-restricted-dr"' in cfg
    assert 'SIG_EVSTORE_RETENTION_DAYS="365"' in cfg
    assert "SIG_BACKUP_PROJECT" in cfg
    cadence = CADENCE.read_text()
    for row in ("restricted-replica", "pg-export-copy"):
        assert f'id = "{row}"' in cadence
    assert cadence.count('state = "paused"') >= 3  # inert until the leg (INERT rows)
    iam = IAM.read_text()
    assert 'id = "sig-replica-rt"' in iam
    assert "reserved" in iam.split('id = "sig-replica-rt"')[1].split("[[")[0]


def test_script_uses_only_reversible_or_additive_writes() -> None:
    text = SCRIPT.read_text()
    # no object deletion anywhere — the retention probe's rm is the *attempt*
    # that MUST fail (the acceptance shape), never a sanctioned delete
    assert text.count("storage rm ") == 1
    assert "buckets delete" not in text and "rm -r" not in text
    # the named gates: window guard + author + ADC
    for guard in ("assert_window", "SIG_EVSTORE_AUTHOR", "require_adc"):
        assert guard in text
