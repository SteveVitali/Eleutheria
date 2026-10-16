# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1b (ticket 291) — the fleet-hygiene sweep leg-runner.

Offline layer (fixture-verified): ``ops/gcp/fleet-sweep.sh --check`` plans the
whole contract order (prestate → backup → cron → export-guard → ar-dryrun →
delete → ar-apply → alerts → proof) with no ADC and no network. The closed
sets are drift-checked against ``ops/cadence.toml`` — an extra or missing
retired job, a corrected-row regression, a lingering ``cron_or_semantics_ok``
or a dropped manual job each refuse. Under a stub ``gcloud`` the apply legs
verify name-checked deletes (an unlisted job is never touched), the cron
read-back, the AR dry-run evidence and the backup/author/window gates. The
production run itself is window-gated (weekday 14:00–20:00Z; exit 42) and
stays queued — these tests run the fail-closed checks only.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "fleet-sweep.sh"
CADENCE = REPO_ROOT / "ops" / "cadence.toml"
PROJECT = "sig-test-project"

RETIRED = [
    "aspi-egress-probe",
    "ccops-sf-egress-probe",
    "muckrock-egress-probe",
    "okc-doc-egress-probe",
    "sig-ingest-resume-test",
    "sig-sink-bench",
]
CRONS = [
    ("sig-sched-eyes-on-flock", "0 5 * * 0", "0 5 23 * 0"),
    ("sig-sched-openstates", "0 5 * * 2", "0 5 2 * 2"),
    ("sig-sched-congress-gov", "0 5 3 * *", "0 5 3 * 2"),
    ("sig-sched-sam-gov", "0 5 * * 1", "0 5 1 * 1"),
]
MANUAL = ["sig-export", "sig-materialize", "sig-replay-ingest"]

# Clock values injected as SIG_SWEEP_NOW — they reproduce the contract window
# offline; no apply ever runs against real infrastructure.
IN_WINDOW = "2026-10-15T15:00:00Z"  # a Thursday inside 14:00–20:00Z
WEEKEND = "2026-10-17T15:00:00Z"  # a Saturday — excluded
EARLY = "2026-10-15T09:00:00Z"  # a weekday before 14:00Z


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"SIG_GCP_PROJECT"}}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env["SIG_GCP_PROJECT"] = PROJECT
    env.update(extra)
    return env


def _run(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(**env),
        cwd=str(REPO_ROOT),
    )


def _mutated_cadence(tmp_path: Path, mutate) -> Path:
    out = tmp_path / "cadence.toml"
    out.write_text(mutate(CADENCE.read_text(encoding="utf-8")), encoding="utf-8")
    return out


def _stub_gcloud(tmp_path: Path) -> Path:
    """A canned gcloud: ADC token, describe/delete state transitions over the
    stub log, scheduler schedules persisted under a state dir, empty lists."""
    bindir = tmp_path / "bin"
    statedir = tmp_path / "gcloud-state"
    bindir.mkdir()
    statedir.mkdir()
    (bindir / "gcloud").write_text(
        """#!/usr/bin/env bash
set -u
echo "GCLOUD $*" >> "${GCLOUD_STUB_LOG}"
case "${1:-} ${2:-} ${3:-}" in
  "auth application-default print-access-token") echo stub-token; exit 0 ;;
  "run jobs describe"*)
    name="${4:-}"
    if grep -q "run jobs delete ${name}\\b" "${GCLOUD_STUB_LOG}" 2>/dev/null; then
      echo "NOT_FOUND" >&2; exit 1
    fi
    printf '{"metadata":{"name":"%s"},"template":{"template":{"containers":[' "${name}"
    printf '"image":"i@sha256:%064d","args":["-c","echo guard && exit 64"]}]}}}\\n' 0
    exit 0 ;;
  "run jobs update"*) exit 0 ;;
  "run jobs delete"*) exit 0 ;;
  "run jobs get-iam-policy"*) echo '{"bindings":[]}'; exit 0 ;;
  "run jobs list"*) echo '[]'; exit 0 ;;
  "run services describe"*) echo '{}'; exit 0 ;;
  "run services get-iam-policy"*) echo '{"bindings":[]}'; exit 0 ;;
  "run services list"*) echo '[]'; exit 0 ;;
  "run revisions list"*) echo '[]'; exit 0 ;;
  "scheduler jobs describe"*)
    name="${4:-}"
    f="${GCLOUD_STUB_STATE}/sched-${name}"
    sched="0 0 0 0 0"
    [ -f "${f}" ] && sched="$(cat "${f}")"
    printf '{"name":"%s","schedule":"%s","state":"ENABLED"}\\n' "${name}" "${sched}"
    exit 0 ;;
  "scheduler jobs update"*)
    name="${5:-}"
    prev=""
    for a in "$@"; do
      [ "${prev}" = "--schedule" ] && echo "${a}" > "${GCLOUD_STUB_STATE}/sched-${name}"
      prev="${a}"
    done
    exit 0 ;;
  "scheduler jobs list"*) echo '[]'; exit 0 ;;
  "artifacts docker images"*) echo '[]'; exit 0 ;;
  "artifacts repositories"*) echo '{}'; exit 0 ;;
esac
exit 0
""",
        encoding="utf-8",
    )
    (bindir / "gcloud").chmod(0o755)
    return bindir, statedir


def _apply_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    bindir, statedir = _stub_gcloud(tmp_path)
    env = _env(
        SIG_SWEEP_NOW=IN_WINDOW,
        SIG_SWEEP_AUTHOR="operator-test",
        PATH=f"{bindir}:{os.environ['PATH']}",
        GCLOUD_STUB_LOG=str(tmp_path / "gcloud.log"),
        GCLOUD_STUB_STATE=str(statedir),
        **extra,
    )
    return env


# --- the check plan -------------------------------------------------------------


def test_check_plans_the_whole_contract_order(tmp_path: Path) -> None:
    proc = _run("--check", "--evidence-dir", str(tmp_path / "ev"))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = proc.stdout
    assert "check OK" in out
    plans = [ln for ln in out.splitlines() if ln.startswith("PLAN:")]
    assert plans, "no PLAN lines emitted"
    joined = "\n".join(plans)
    # The six name-checked deletions — and only those.
    for name in RETIRED:
        assert f"run jobs delete {name}" in joined
    deletes = [ln for ln in plans if "run jobs delete" in ln]
    assert len(deletes) == len(RETIRED)
    # The four cron corrections with the declared schedules.
    for sched, cron, prior in CRONS:
        assert f"scheduler jobs update http {sched}" in joined
        assert cron in joined and prior in joined
    # The AR dry-run before apply, the export guard, both sig-alerts dispositions.
    assert "set-cleanup-policies" in joined and "--dry-run" in joined
    assert "--no-dry-run" in joined
    assert "run jobs update sig-export" in joined
    assert "retire" in joined and "rebuild" in joined
    # A job NOT on the retired list is never a delete target.
    for name in ("sig-probe", "sig-export", "sig-materialize", "sig-replay-ingest"):
        for ln in plans:
            assert not re.search(rf"run jobs delete {name}\b", ln), (name, ln)


def test_check_mode_needs_no_adc_or_project(tmp_path: Path) -> None:
    env = _env()
    env.pop("SIG_GCP_PROJECT")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check", "--evidence-dir", str(tmp_path / "ev")],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "PLAN:" in proc.stdout and "check OK" in proc.stdout


# --- closed-set drift refuses ----------------------------------------------------


def test_extra_retired_job_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path,
        lambda t: t + '\n[[retired_jobs]]\njob = "sig-ingest-muckrock"\nreason = "x"\n',
    )
    proc = _run("--check", SIG_SWEEP_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "REFUSED" in proc.stderr


def test_missing_retired_job_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path, lambda t: t.replace('job = "sig-sink-bench"', 'job = "sig-sink-bench-x"', 1)
    )
    proc = _run("--check", SIG_SWEEP_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2


def test_retired_row_without_reason_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path,
        lambda t: t.replace(
            'reason = "the P31.3 sink benchmark', 'x = "the P31.3 sink benchmark', 1
        ),
    )
    proc = _run("--check", SIG_SWEEP_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2


def test_cron_regression_in_cadence_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path, lambda t: t.replace('cron = "0 5 * * 0"', 'cron = "0 5 23 * 0"', 1)
    )
    proc = _run("--check", SIG_SWEEP_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "eyes_on_flock" in proc.stderr


def test_lingering_or_semantics_flag_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path,
        lambda t: t.replace(
            'cron = "0 5 * * 0"',
            'cron = "0 5 * * 0"\ncron_or_semantics_ok = "P35.1b"',
            1,
        ),
    )
    proc = _run("--check", SIG_SWEEP_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2


def test_dropped_manual_job_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path,
        lambda t: t.replace(
            'job = "sig-replay-ingest"\nsa_class = "ingest"',
            'job = "sig-replay-x"\nsa_class = "ingest"',
            1,
        ),
    )
    proc = _run("--check", SIG_SWEEP_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2


# --- the gates -------------------------------------------------------------------


def test_apply_outside_window_queues_42(tmp_path: Path) -> None:
    for now in (WEEKEND, EARLY):
        proc = _run(
            "--apply",
            "delete",
            "--evidence-dir",
            str(tmp_path / "ev"),
            SIG_SWEEP_NOW=now,
        )
        assert proc.returncode == 42, (now, proc.stdout)
        assert "QUEUED" in proc.stdout


def test_apply_in_window_needs_adc(tmp_path: Path) -> None:
    # CLOUDSDK_CONFIG points at a nonexistent dir, so `print-access-token`
    # fails even when gcloud is installed — the ADC gate refuses 3 (a
    # gate-pending, never a fabricated apply).
    proc = _run(
        "--apply", "delete", "--evidence-dir", str(tmp_path / "ev"), SIG_SWEEP_NOW=IN_WINDOW
    )
    assert proc.returncode == 3
    assert "gate pending" in proc.stderr or "gcloud" in proc.stderr


def test_apply_in_window_needs_the_recorded_author(tmp_path: Path) -> None:
    env = _apply_env(tmp_path)
    env.pop("SIG_SWEEP_AUTHOR")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "delete", "--evidence-dir", str(tmp_path / "ev")],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 42
    assert "SIG_SWEEP_AUTHOR" in proc.stdout


# --- stubbed apply legs -----------------------------------------------------------


def test_delete_leg_is_name_checked_and_describe_first(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    (ev / "backup").mkdir(parents=True)
    (ev / "backup" / "verified.txt").write_text("12345\n")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "delete", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (tmp_path / "gcloud.log").read_text()
    deletes = re.findall(r"GCLOUD run jobs delete (\S+)", log)
    assert sorted(deletes) == sorted(RETIRED)
    # Every delete was preceded by a describe of the same job (the recreation
    # recipe) — and a json+yaml pair landed per job.
    for name in RETIRED:
        describe_pos = log.index(f"run jobs describe {name}")
        delete_pos = log.index(f"run jobs delete {name}")
        assert describe_pos < delete_pos, name
        assert (ev / "delete" / f"pre-{name}.json").is_file()
        assert (ev / "delete" / f"pre-{name}.yaml").is_file()
    assert (ev / "delete" / "deleted.txt").read_text().count("deleted") == 6
    # Nothing outside the list was touched — `deletes` IS the complete set of
    # run-jobs deletions, and no other mutating verb ran at all.
    for verb in ("jobs execute", "scheduler jobs delete", "services delete", "jobs update"):
        assert verb not in log


def test_delete_leg_refuses_without_the_recorded_backup(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    ev.mkdir()
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "delete", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "backup" in proc.stderr


def test_cron_leg_updates_only_offenders_and_read_backs(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    env = _apply_env(tmp_path)
    statedir = tmp_path / "gcloud-state"
    # Live state: the four offenders still carry the OR-semantics schedules.
    for sched, _cron, prior in CRONS:
        (statedir / f"sched-{sched}").write_text(prior)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "cron", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (tmp_path / "gcloud.log").read_text()
    for sched, cron, _prior in CRONS:
        upd = [
            ln
            for ln in log.splitlines()
            if f"scheduler jobs update http {sched} " in ln and f"--schedule {cron} " in ln
        ]
        assert upd, (sched, log)
        assert (statedir / f"sched-{sched}").read_text().strip() == cron
        assert (ev / "cron" / f"post-{sched}.json").is_file()
    corrections = (ev / "cron" / "corrections.txt").read_text()
    assert corrections.count("\n") == 4


def test_cron_leg_skips_an_already_correct_trigger(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    env = _apply_env(tmp_path)
    statedir = tmp_path / "gcloud-state"
    for sched, cron, prior in CRONS:
        # three already-correct; one still offending
        (statedir / f"sched-{sched}").write_text(cron if sched != "sig-sched-sam-gov" else prior)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "cron", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (tmp_path / "gcloud.log").read_text()
    assert "scheduler jobs update http sig-sched-sam-gov" in log
    for sched, _cron, _prior in CRONS:
        if sched != "sig-sched-sam-gov":
            assert f"scheduler jobs update http {sched}" not in log


def test_ar_dryrun_records_the_candidate_set(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "ar-dryrun", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (ev / "ar" / "merged-policy.json").is_file()
    assert (ev / "ar" / "candidates.json").is_file()
    assert (ev / "ar" / "digests.txt").is_file()
    log = (tmp_path / "gcloud.log").read_text()
    assert "set-cleanup-policies" in log and "--dry-run" in log


def test_ar_apply_refuses_without_the_recorded_dryrun(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    (ev / "backup").mkdir(parents=True)
    (ev / "backup" / "verified.txt").write_text("9\n")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "ar-apply", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "dry-run" in proc.stderr


def test_alerts_leg_refuses_without_the_recorded_disposition(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    (ev / "backup").mkdir(parents=True)
    (ev / "backup" / "verified.txt").write_text("9\n")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "alerts", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "SIG_SWEEP_ALERTS_DISPOSITION" in proc.stderr


def test_rollback_check_mode_prints_recipes(tmp_path: Path) -> None:
    proc = _run("--check", "rollback", "--evidence-dir", str(tmp_path / "ev"))
    assert proc.returncode == 0
    assert "delete-cleanup-policies" in proc.stdout or "recreation" in proc.stdout
