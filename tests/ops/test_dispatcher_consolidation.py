# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1c (ticket 291a) — the dispatcher-consolidation leg-runner.

Offline layer (fixture-verified): ``ops/gcp/dispatcher-consolidation.sh
--check`` plans the whole contract order (prestate → deploy → verify →
retire → proof) with no ADC and no network, and the closed sets are
drift-checked against ``ops/cadence.toml`` — an uncovered row, a widened
list, a bad disposition, a protected collision or a missing ``[dispatcher]``
each refuse (exit 2, never reconciled). Under a stub ``gcloud`` the apply
legs verify name-checked deletes (an unlisted trigger is never touched, a
trigger pointing at an unexpected job stops the sweep) and the window / ADC
/ author gates. The production run itself is window-gated (a weekday
14:00–20:00Z slot; exit 42) and stays queued — these tests run the
fail-closed checks only.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "dispatcher-consolidation.sh"
SCHED_OPS = REPO_ROOT / "ops" / "gcp" / "scheduled-ops.sh"
CADENCE = REPO_ROOT / "ops" / "cadence.toml"
PROJECT = "sig-test-project"
REGION = "us-central1"

# Clock values injected as SIG_CONSOL_NOW — they reproduce the contract
# window offline; no apply ever runs against real infrastructure.
IN_WINDOW = "2026-10-15T15:00:00Z"  # a Thursday inside 14:00–20:00Z
SATURDAY = "2026-10-17T15:00:00Z"
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


def _stub_gcloud(tmp_path: Path, *, wrong_target: str | None = None) -> Path:
    """A canned gcloud: ADC token; scheduler describe reads a per-name target
    file (``target-<sched>`` holds the job the trigger's httpTarget points at)
    and tracks deletions under ``deleted-<sched>``; everything else is a
    no-op capture into the stub log.
    """
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
  "scheduler jobs describe"*)
    name="${4:-}"
    [ -f "${GCLOUD_STUB_STATE}/deleted-${name}" ] && { echo "NOT_FOUND" >&2; exit 1; }
    [ -f "${GCLOUD_STUB_STATE}/absent-${name}" ] && { echo "NOT_FOUND" >&2; exit 1; }
    target="$(cat "${GCLOUD_STUB_STATE}/target-${name}" 2>/dev/null || echo "${name}")"
    sched="0 0 0 0 0"
    oauth=""
    if [ "${name}" = "sig-sched-due" ]; then
      sched="13 * * * *"
      oauth=',"oauthToken":{"serviceAccountEmail":"sig-scheduler@sig-test-project.iam.gserviceaccount.com"}'
    fi
    fmt=""
    for a in "$@"; do [ "${a}" = "yaml" ] && fmt="yaml"; done
    if [ "${fmt}" = "yaml" ]; then
      printf 'name: %s\\nschedule: "%s"\\nhttpTarget:\\n  uri: https://x/jobs/%s:run\\n' \
        "${name}" "${sched}" "${target}"
    else
      printf '{"name":"%s","schedule":"%s","state":"ENABLED"' \
        "${name}" "${sched}"
      printf ',"httpTarget":{"uri":"https://x/jobs/%s:run","httpMethod":"POST"%s}}\\n' \
        "${target}" "${oauth}"
    fi
    exit 0 ;;
  "scheduler jobs delete"*)
    name="${4:-}"
    touch "${GCLOUD_STUB_STATE}/deleted-${name}"
    exit 0 ;;
  "scheduler jobs list"*)
    printf '[{"name":"projects/p/locations/l/jobs/sig-sched-due"},'
    printf '{"name":"projects/p/locations/l/jobs/sig-sched-probe"}]\\n'
    exit 0 ;;
  "scheduler jobs create"*) exit 0 ;;
  "scheduler jobs update"*) exit 0 ;;
  "run jobs describe"*)
    printf '{"spec":{"template":{"spec":{"template":{"spec":{'
    printf '"serviceAccountName":"sig-ingest-rt@sig-test-project.iam.gserviceaccount.com",'
    printf '"containers":[{"image":"img@sha256:%064d",' 0
    printf '"args":["-c","exec sig-ops dispatch-due"]}]}}}}}}\\n'
    exit 0 ;;
  "run jobs list"*) echo '[]'; exit 0 ;;
  "run jobs deploy"*) exit 0 ;;
  "run jobs delete"*) exit 0 ;;
  "run jobs execute"*) exit 0 ;;
  "run jobs add-iam-policy-binding"*) exit 0 ;;
  "storage cp"*) echo '{}'; exit 0 ;;
esac
exit 0
""",
        encoding="utf-8",
    )
    (bindir / "gcloud").chmod(0o755)
    if wrong_target:
        (statedir / f"target-{wrong_target}").write_text("sig-ingest-impostor")
    return bindir, statedir


def _apply_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    bindir, _statedir = _stub_gcloud(tmp_path)
    env = _env(
        SIG_CONSOL_NOW=IN_WINDOW,
        SIG_CONSOL_AUTHOR="operator-test",
        SIG_JOB_IMAGE=f"{REGION}-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:{'a' * 64}",
        PATH=f"{bindir}:{os.environ['PATH']}",
        GCLOUD_STUB_LOG=str(tmp_path / "gcloud.log"),
        GCLOUD_STUB_STATE=str(tmp_path / "gcloud-state"),
        **extra,
    )
    return env


def _retired_names() -> list[str]:
    """The disposition=retired names on the committed contract."""
    import tomllib

    doc = tomllib.loads(CADENCE.read_text())
    return sorted(r["name"] for r in doc["retire_triggers"] if r.get("disposition") == "retired")


def _targets_map() -> dict[str, str]:
    """scheduler → job for the retired rows (the pre-delete target check)."""
    import tomllib

    doc = tomllib.loads(CADENCE.read_text())
    retired = {r["name"] for r in doc["retire_triggers"] if r.get("disposition") == "retired"}
    return {
        row["scheduler"]: row["job"]
        for row in doc["sources"] + doc["batches"]
        if row["scheduler"] in retired
    }


# --- the check plan -------------------------------------------------------------


def test_check_plans_the_whole_contract_order(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    proc = _run("--check", "--evidence-dir", str(ev))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = proc.stdout
    assert "check OK" in out
    # The closed-set banner names every retired trigger with its target job.
    for name, job in _targets_map().items():
        assert f"retire: {name} → was /jobs/{job}:run" in out
    assert "keep (pin): sig-sched-camreg-batch-05" in out
    assert "dispatcher: sig-sched-due ← sig-sched-due ('13 * * * *'" in out
    # Every leg plans: prestate → deploy → verify → retire → proof.
    plans = [ln for ln in out.splitlines() if ln.startswith("PLAN:")]
    joined = "\n".join(plans)
    assert "scheduler jobs list" in joined and "run jobs list" in joined
    assert "run jobs deploy sig-sched-due" in joined
    assert "run invoker" in joined.lower().replace("_", " ") or "run.invoker" in joined
    assert "scheduler jobs create http sig-sched-due" in joined
    assert "run jobs execute sig-sched-due" in joined  # the staged dry-run
    # The retire leg plans a describe→target-check→delete per retired name —
    # and only those names.
    retire_plans = [ln for ln in plans if "assert uri targets" in ln]
    assert len(retire_plans) == len(_retired_names()) == 89
    # Proof plans the poststate list + the closing live-diff.
    assert "post/scheduler-jobs.json" in joined
    assert "live-diff" in joined
    assert "leg order: prestate → deploy → verify → retire → proof" in out
    assert (ev / "check-targets.txt").is_file()


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


def test_rollback_check_mode_prints_the_declared_map(tmp_path: Path) -> None:
    proc = _run("--check", "rollback", "--evidence-dir", str(tmp_path / "ev"))
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "scheduler jobs delete sig-sched-due" in out
    assert "run jobs delete sig-sched-due" in out
    assert "per-source" in out


# --- closed-set drift refuses ----------------------------------------------------


def test_uncovered_row_refuses(tmp_path: Path) -> None:
    victim = _retired_names()[0]
    # Remove the whole [[retire_triggers]] block for `victim`.
    block_re = re.compile(
        rf'\n\[\[retire_triggers\]\]\nname = "{re.escape(victim)}"'
        rf".*?(?=\n\[\[retire_triggers\]\]|\Z)",
        re.S,
    )
    mutated = _mutated_cadence(tmp_path, lambda t: block_re.sub("\n", t))
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "not on [[retire_triggers]]" in proc.stderr or "count" in proc.stderr


def test_widened_list_refuses(tmp_path: Path) -> None:
    # Flipping the kept pin to retired widens the count 89 → 90 — a refusal,
    # never a silent scope change.
    mutated = _mutated_cadence(
        tmp_path,
        lambda t: t.replace('disposition = "kept-declared-pin"', 'disposition = "retired"', 1),
    )
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "count" in proc.stderr


def test_bad_disposition_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(
        tmp_path,
        lambda t: t.replace('disposition = "kept-manual"', 'disposition = "maybe"', 1),
    )
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2


def test_missing_reason_refuses(tmp_path: Path) -> None:
    text = CADENCE.read_text()
    idx = text.index('disposition = "retired"')
    end = text.index("\n", text.index("reason", idx)) + 1
    mutated = _mutated_cadence(tmp_path, lambda t: t[:idx] + t[end:])
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "reason" in proc.stderr


def _extra_retire_row(name: str) -> str:
    return f'\n[[retire_triggers]]\nname = "{name}"\ndisposition = "retired"\nreason = "x"\n'


def test_non_cadence_name_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(tmp_path, lambda t: t + _extra_retire_row("sig-sched-invented"))
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "sig-sched-invented" in proc.stderr


def test_protected_collision_refuses(tmp_path: Path) -> None:
    mutated = _mutated_cadence(tmp_path, lambda t: t + _extra_retire_row("sig-sched-probe"))
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "protected" in proc.stderr


def test_missing_dispatcher_table_refuses(tmp_path: Path) -> None:
    text = CADENCE.read_text()
    start = text.index("[dispatcher]")
    end = text.index("[[retire_triggers]]")
    mutated = _mutated_cadence(tmp_path, lambda t: t[:start] + t[end:])
    proc = _run("--check", SIG_CONSOL_CADENCE_TOML=str(mutated))
    assert proc.returncode == 2
    assert "[dispatcher]" in proc.stderr


# --- the gates -------------------------------------------------------------------


def test_apply_outside_window_queues_42(tmp_path: Path) -> None:
    for now in (SATURDAY, EARLY):
        proc = _run(
            "--apply",
            "retire",
            "--evidence-dir",
            str(tmp_path / "ev"),
            SIG_CONSOL_NOW=now,
        )
        assert proc.returncode == 42, (now, proc.stdout)
        assert "QUEUED" in proc.stdout


def test_apply_in_window_needs_adc(tmp_path: Path) -> None:
    proc = _run(
        "--apply",
        "retire",
        "--evidence-dir",
        str(tmp_path / "ev"),
        SIG_CONSOL_NOW=IN_WINDOW,
    )
    assert proc.returncode == 3
    assert "gate pending" in proc.stderr or "gcloud" in proc.stderr


def test_apply_in_window_needs_the_recorded_author(tmp_path: Path) -> None:
    env = _apply_env(tmp_path)
    env.pop("SIG_CONSOL_AUTHOR")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(tmp_path / "ev")],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 42
    assert "SIG_CONSOL_AUTHOR" in proc.stdout


def test_retire_refuses_without_the_recorded_prestate(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(tmp_path / "ev")],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "prestate" in proc.stderr


def test_retire_refuses_without_the_verified_dispatcher(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    (ev / "pre").mkdir(parents=True)
    (ev / "pre" / "date-start.txt").write_text("2026-10-15T15:00:00Z\n")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=_apply_env(tmp_path),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "verified dispatcher" in proc.stderr


# --- stubbed apply legs ----------------------------------------------------------


def _seed_apply_prereqs(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """pre/ + verify/ markers plus the per-trigger target map the stub reads."""
    ev = tmp_path / "ev"
    (ev / "pre").mkdir(parents=True)
    (ev / "verify").mkdir(parents=True)
    (ev / "pre" / "date-start.txt").write_text("2026-10-15T15:00:00Z\n")
    (ev / "verify" / "verified.txt").write_text("2026-10-15T15:05:00Z\n")
    env = _apply_env(tmp_path)
    statedir = tmp_path / "gcloud-state"
    for sched, job in _targets_map().items():
        (statedir / f"target-{sched}").write_text(job)
    kept = statedir / "target-sig-sched-camreg-batch-05"
    kept.write_text("sig-ingest-camreg-batch-05")
    return ev, env


def test_retire_leg_is_name_checked_describe_first(tmp_path: Path) -> None:
    ev, env = _seed_apply_prereqs(tmp_path)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (tmp_path / "gcloud.log").read_text()
    retired = _retired_names()
    deletes = re.findall(r"GCLOUD scheduler jobs delete (\S+)", log)
    assert sorted(deletes) == retired == sorted(_targets_map())
    for name in retired:
        assert log.index(f"scheduler jobs describe {name}") < log.index(
            f"scheduler jobs delete {name}"
        ), name
        assert (ev / "retire" / f"pre-{name}.json").is_file()
        assert (ev / "retire" / f"pre-{name}.yaml").is_file()
    retired_txt = (ev / "retire" / "retired.txt").read_text()
    assert retired_txt.count("deleted") == len(retired)
    # The kept pin was VERIFIED, never deleted; nothing else was mutated.
    assert "scheduler jobs delete sig-sched-camreg-batch-05" not in log
    assert "keep-list: sig-sched-camreg-batch-05 live" in proc.stdout
    for verb in ("run jobs delete", "scheduler jobs create", "jobs execute"):
        assert verb not in log
    assert (ev / "sha256s.txt").is_file()


def test_retire_leg_records_an_already_absent_trigger(tmp_path: Path) -> None:
    ev, env = _seed_apply_prereqs(tmp_path)
    statedir = tmp_path / "gcloud-state"
    victim = _retired_names()[0]
    (statedir / f"absent-{victim}").touch()
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert f"{victim}: already absent" in proc.stdout
    retired_txt = (ev / "retire" / "retired.txt").read_text()
    assert f"absent {victim}" in retired_txt


def test_retire_leg_refuses_a_trigger_on_an_unexpected_job(tmp_path: Path) -> None:
    ev, env = _seed_apply_prereqs(tmp_path)
    statedir = tmp_path / "gcloud-state"
    victim = _retired_names()[0]
    (statedir / f"target-{victim}").write_text("sig-ingest-impostor")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "never deleted" in proc.stderr
    # The sweep stopped AT the bad trigger — the impostor trigger was not deleted.
    log = (tmp_path / "gcloud.log").read_text()
    assert f"scheduler jobs delete {victim}" not in log


def test_retire_leg_refuses_an_absent_kept_pin(tmp_path: Path) -> None:
    ev, env = _seed_apply_prereqs(tmp_path)
    (tmp_path / "gcloud-state" / "absent-sig-sched-camreg-batch-05").touch()
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "retire", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2
    assert "kept-declared-pin" in proc.stderr


def test_verify_leg_stages_the_dry_run_execution(tmp_path: Path) -> None:
    ev, env = _seed_apply_prereqs(tmp_path)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "verify", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (tmp_path / "gcloud.log").read_text()
    assert "run jobs execute sig-sched-due" in log
    assert "--dry-run" in log
    assert (ev / "verify" / "verified.txt").is_file()
    assert (ev / "verify" / "execute.txt").is_file()


def test_deploy_leg_binds_the_due_invokers(tmp_path: Path) -> None:
    ev, env = _seed_apply_prereqs(tmp_path)
    # Pre-consolidation live state: the dispatcher trigger does not exist
    # yet — the deploy must take the create path.
    (tmp_path / "gcloud-state" / "absent-sig-sched-due").touch()
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "deploy", "--evidence-dir", str(ev)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    log = (tmp_path / "gcloud.log").read_text()
    assert "run jobs deploy sig-sched-due" in log
    # Scheduler OIDC invoker on the dispatcher itself.
    assert re.search(r"add-iam-policy-binding sig-sched-due .*sig-scheduler@sig-test-project", log)
    # One due-invoker binding per non-paused retired job — and only those.
    binds = re.findall(r"add-iam-policy-binding (\S+) .*serviceAccount:sig-ingest-rt@", log)
    due_jobs = {
        j
        for s, j in _targets_map().items()
        # the paused rows' jobs are never dispatcher-dispatched
    }
    import tomllib

    doc = tomllib.loads(CADENCE.read_text())
    retired = {r["name"] for r in doc["retire_triggers"] if r.get("disposition") == "retired"}
    due_jobs = {
        row["job"]
        for row in doc["sources"] + doc["batches"]
        if row["scheduler"] in retired and row.get("state", "enabled") != "paused"
    }
    assert set(binds) == due_jobs
    assert "scheduler jobs create http sig-sched-due" in log


# --- scheduled-ops.sh under both shapes ----------------------------------------


def test_scheduled_ops_check_consolidated_plans_the_dispatcher(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(SCHED_OPS), "--check"],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = proc.stdout
    assert "due dispatcher" in out
    assert "run jobs deploy sig-sched-due" in out
    assert "scheduler jobs create http sig-sched-due" in out
    # Consolidated shape: per-row triggers are reported as retired, never
    # reconciled — no `create http sig-sched-<row>` for a retired name.
    creates = re.findall(r"scheduler jobs create http (\S+)", out)
    retired = set(_retired_names())
    assert not retired & set(creates), retired & set(creates)


def test_scheduled_ops_check_per_source_restores_row_triggers(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(SCHED_OPS), "--check", "--shape", "per-source"],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = proc.stdout
    assert "shape: per-source" in out
    assert "due dispatcher" not in out
    # Every non-paused retired row's trigger is back on the create list —
    # except `existing = true` rows (muckrock, P25.7), which get the
    # verify-or-recreate plan (the rollback map recreates them from the
    # cadence row when the consolidation deleted them).
    import tomllib

    doc = tomllib.loads(CADENCE.read_text())
    retired = {r["name"] for r in doc["retire_triggers"] if r.get("disposition") == "retired"}
    creates = set(re.findall(r"scheduler jobs create http (\S+)", out))
    missing = {
        row["scheduler"]
        for row in doc["sources"] + doc["batches"]
        if row["scheduler"] in retired
        and row.get("state", "enabled") != "paused"
        and not row.get("existing")
    } - creates
    assert not missing, missing
    # The existing row's rollback plan is present and honest.
    assert re.search(
        r"verify sig-sched-muckrock .*recreate from the cadence row if absent",
        out,
    )
