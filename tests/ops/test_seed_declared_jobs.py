# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1a1 (manifest row 287a; D-P34.42b-2) — the declared-job seed bridge.

Offline layer (fixture-verified): ``ops/gcp/seed-declared-jobs.sh --check``
plans exactly the twelve contract mutations per row (job create, the
existing-sig-scheduler ``run.invoker`` binding, trigger create, immediate
pause, PAUSED read-back) with the contract-pinned digest and the labelled
temporary default-compute runtime identity — no ADC, no network, no fleet
reconcile. Cadence drift, a wrong/foreign/``:latest``/untagged
``SIG_JOB_IMAGE``, an existing target job or trigger, a missing
``sig-scheduler``, and a running target execution all refuse; a paused-on-create
ordering failure rolls back only this leg's creations. The production leg
itself is window-gated (a weekday 14:00–20:00Z slot; exit 42 otherwise) and
stays queued — these tests run the fail-closed checks only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "seed-declared-jobs.sh"
CADENCE = REPO_ROOT / "ops" / "cadence.toml"
PROJECT = "sig-test-project"
PINNED = "sha256:6ad5477d4aacde23d508f5eea765a6ad835e603ad794b10df56710acca4414f5"
API_IMAGE = f"us-central1-docker.pkg.dev/{PROJECT}/sig/sig-api"
SCHED_SA = f"sig-scheduler@{PROJECT}.iam.gserviceaccount.com"
COMPUTE_SA = "12345-compute@developer.gserviceaccount.com"

# The contract's closed twelve-row set (ticket 287a § Declared target set).
CONTRACT = [
    (
        "source",
        "camreg_tribal_all_leaders_directory",
        "sig-ingest-camreg-tribal-all-leaders-directory",
        "sig-sched-camreg-tribal-all-leaders-directory",
        "41 7 24 * *",
        "30m",
    ),
    (
        "source",
        "legis_tribal_tohono_oodham_notice",
        "sig-ingest-legis-tribal-tohono-oodham-notice",
        "sig-sched-legis-tribal-tohono-oodham-notice",
        "43 7 24 * *",
        "30m",
    ),
    ("batch", "r11-ate-01", "sig-ingest-r11-ate-01", "sig-sched-r11-ate-01", "17 7 18 * *", "6h"),
    (
        "batch",
        "r11-disclosures-01",
        "sig-ingest-r11-disclosures-01",
        "sig-sched-r11-disclosures-01",
        "27 7 21 * *",
        "6h",
    ),
    (
        "batch",
        "r11-disclosures-02",
        "sig-ingest-r11-disclosures-02",
        "sig-sched-r11-disclosures-02",
        "27 7 22 * *",
        "6h",
    ),
    (
        "batch",
        "r11-documents-01",
        "sig-ingest-r11-documents-01",
        "sig-sched-r11-documents-01",
        "27 7 23 * *",
        "6h",
    ),
    (
        "batch",
        "r11-layers-01",
        "sig-ingest-r11-layers-01",
        "sig-sched-r11-layers-01",
        "17 7 16 * *",
        "6h",
    ),
    (
        "batch",
        "r11-layers-02",
        "sig-ingest-r11-layers-02",
        "sig-sched-r11-layers-02",
        "17 7 17 * *",
        "6h",
    ),
    (
        "batch",
        "r11-procurement-01",
        "sig-ingest-r11-procurement-01",
        "sig-sched-r11-procurement-01",
        "17 7 19 * *",
        "6h",
    ),
    (
        "batch",
        "r11-tier2-01",
        "sig-ingest-r11-tier2-01",
        "sig-sched-r11-tier2-01",
        "37 7 25 * *",
        "6h",
    ),
    (
        "batch",
        "r11-tier2-02",
        "sig-ingest-r11-tier2-02",
        "sig-sched-r11-tier2-02",
        "37 7 26 * *",
        "6h",
    ),
    (
        "batch",
        "r11-tier2-03",
        "sig-ingest-r11-tier2-03",
        "sig-sched-r11-tier2-03",
        "37 7 27 * *",
        "6h",
    ),
]

# Clock values injected as SIG_SEED_NOW into the window-guard apply tests —
# they reproduce the contract window offline; no apply ever runs for real.
# (The in-window value is a Thursday, the out-of-window one a Saturday.)
SYNTHETIC_IN_WINDOW = "2026-10-15T15:00:00Z"  # weekday inside 14:00-20:00Z
SYNTHETIC_WEEKEND = "2026-10-17T15:00:00Z"  # Saturday — excluded
SYNTHETIC_EARLY = "2026-10-15T09:00:00Z"  # weekday before 14:00Z
SYNTHETIC_LATE = "2026-10-15T21:00:00Z"  # weekday after 20:00Z


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"SIG_GCP_PROJECT", "SIG_JOB_IMAGE"}}
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
    text = CADENCE.read_text(encoding="utf-8")
    out = tmp_path / "cadence.toml"
    out.write_text(mutate(text), encoding="utf-8")
    return out


# --- the closed target set ---------------------------------------------------


def test_check_plans_exactly_the_twelve_contract_mutations(tmp_path: Path) -> None:
    proc = _run("--check", "--evidence-dir", str(tmp_path / "ev"))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    plan = proc.stdout
    assert "check OK" in plan
    assert "twelve" in plan

    plan_lines = [line for line in plan.splitlines() if line.startswith("PLAN:")]
    deploys = [line for line in plan_lines if "run jobs deploy" in line]
    bindings = [line for line in plan_lines if "add-iam-policy-binding" in line]
    creates = [line for line in plan_lines if "scheduler jobs create http" in line]
    pauses = [line for line in plan_lines if "scheduler jobs pause" in line]
    assert len(deploys) == 12 and len(bindings) == 12
    assert len(creates) == 12 and len(pauses) == 12
    # No other jobs are touched — the fleet reconcile is out of scope. The
    # rollback PLAN line names no gcloud verb (it replays created.txt), and
    # "rollback" prose mentions pre-existing resources only as what it never
    # touches.
    joined = "\n".join(plan_lines)
    for name in (
        "sig-probe",
        "sig-export",
        "sig-materialize",
        "sig-replay-ingest",
        "sig-ingest-muckrock",
    ):
        for line in plan_lines:
            assert not re.search(rf"run jobs deploy {name}\b", line), (name, line)
    for verb in (
        "run jobs update",
        "run jobs execute",
        "scheduler jobs update",
        "scheduler jobs resume",
        "scheduler jobs run",
        "services enable",
        "service-accounts create",
    ):
        assert verb not in joined, verb

    for kind, rid, job, sched, cron, ttimeout in CONTRACT:
        dep = next(line for line in deploys if f"jobs deploy {job} " in line)
        assert f"--task-timeout {ttimeout}" in dep
        flag = "--source" if kind == "source" else "--batch"
        assert f"scheduled-ingest {flag} {rid} --sink pg" in dep
        assert PINNED in dep
        assert f"--member=serviceAccount:{SCHED_SA}" in next(
            line for line in bindings if f"binding {job} " in line
        )
        crt = next(line for line in creates if f"create http {sched} " in line)
        assert f"--schedule {cron}" in crt
        assert f"--oauth-service-account-email={SCHED_SA}" in crt
        assert f"jobs/{job}:run" in crt

    # Evidence capture: the check plan + resolved contract table land on disk.
    ev = tmp_path / "ev"
    assert (ev / "check-plan.txt").is_file()
    assert (ev / "target-rows.txt").read_text().count("\n") == 12
    assert (ev / "sha256s.txt").read_text().count("\n") == 2


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


def test_no_existing_resource_is_planned_or_touched() -> None:
    proc = _run("--check")
    assert proc.returncode == 0
    # The only mutation verbs in the plan are deploy/create/binding/pause and
    # the read-back describe — every existing resource is verified-absent,
    # never updated, deleted, executed or enabled.
    for line in proc.stdout.splitlines():
        if not line.startswith("PLAN:"):
            continue
        assert any(
            v in line
            for v in (
                "run jobs deploy",
                "add-iam-policy-binding",
                "scheduler jobs create http",
                "scheduler jobs pause",
                "scheduler jobs describe",
                "rollback replays",
            )
        ), line


# --- cadence drift refusal ----------------------------------------------------


def test_cadence_cron_drift_refuses(tmp_path: Path) -> None:
    bad = _mutated_cadence(
        tmp_path,
        lambda t: t.replace('cron = "41 7 24 * *"', 'cron = "42 7 24 * *"', 1),
    )
    proc = _run("--check", SIG_SEED_CADENCE_TOML=str(bad))
    assert proc.returncode == 2
    assert "cadence drift" in proc.stderr


def test_cadence_missing_row_refuses(tmp_path: Path) -> None:
    bad = _mutated_cadence(
        tmp_path, lambda t: t.replace('id = "r11-tier2-03"', 'id = "r11-tier2-04"', 1)
    )
    # The rename produces an undeclared r11-* batch AND a missing contract row.
    proc = _run("--check", SIG_SEED_CADENCE_TOML=str(bad))
    assert proc.returncode == 2
    assert "REFUSED" in proc.stderr


def test_cadence_extra_r11_batch_refuses(tmp_path: Path) -> None:
    extra = textwrap.dedent(
        """\n[[batches]]
        id = "r11-extra-01"
        cadence = "monthly"
        cron = "0 7 28 * *"
        job = "sig-ingest-r11-extra-01"
        scheduler = "sig-sched-r11-extra-01"
        task_timeout = "6h"
        members = ["muckrock"]
        """
    )
    bad = _mutated_cadence(tmp_path, lambda t: t + extra)
    proc = _run("--check", SIG_SEED_CADENCE_TOML=str(bad))
    assert proc.returncode == 2
    assert "undeclared r11-" in proc.stderr


def test_cadence_existing_mark_refuses(tmp_path: Path) -> None:
    def mutate(t: str) -> str:
        return t.replace(
            'id = "camreg_tribal_all_leaders_directory"',
            'id = "camreg_tribal_all_leaders_directory"\nexisting = true',
            1,
        )

    bad = _mutated_cadence(tmp_path, mutate)
    proc = _run("--check", SIG_SEED_CADENCE_TOML=str(bad))
    assert proc.returncode == 2
    assert "existing" in proc.stderr


# --- pinned digest enforcement ------------------------------------------------


def test_unset_image_uses_the_contract_pin() -> None:
    proc = _run("--check")
    assert proc.returncode == 0
    assert f"{API_IMAGE}@{PINNED}" in proc.stdout


def test_exact_pinned_ref_is_accepted() -> None:
    proc = _run("--check", SIG_JOB_IMAGE=f"{API_IMAGE}@{PINNED}")
    assert proc.returncode == 0


@pytest.mark.parametrize(
    "ref",
    [
        f"{API_IMAGE}@sha256:" + "ab" * 32,  # wrong digest
        "other.example.com/p/sig/sig-api@sha256:" + "6ad5477d" + "0" * 56,  # foreign repo
        f"{API_IMAGE}:latest",  # mutable tag
        f"{API_IMAGE}",  # untagged
        "ghcr.io/other/sig-api:v1",  # foreign repo tag
    ],
)
def test_wrong_image_refuses(ref: str) -> None:
    proc = _run("--check", SIG_JOB_IMAGE=ref)
    assert proc.returncode == 2
    assert "run jobs deploy" not in proc.stdout


def test_a_tag_ref_resolving_elsewhere_refuses_at_apply(tmp_path: Path) -> None:
    # A tag under the sig-api repo that resolves to a DIFFERENT digest is
    # refused in apply mode (the resolution needs ADC — stubbed here).
    stub = _install_gcloud_stub(tmp_path)
    env = _env(
        SIG_SEED_NOW=SYNTHETIC_IN_WINDOW,
        SIG_JOB_IMAGE=f"{API_IMAGE}:some-tag",
        GCLOUD_STUB_STATE=str(tmp_path / "gstate"),
        PATH=f"{stub}:{os.environ['PATH']}",
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--apply", "--evidence-dir", str(tmp_path / "ev")],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "not the contract pin" in proc.stderr


# --- temporary compute-SA labelling + pause ordering --------------------------


def test_jobs_are_labelled_temporary_default_compute() -> None:
    proc = _run("--check")
    assert proc.returncode == 0
    assert "runtimeIdentity: temporary-default-compute (migrated by P34.42b)" in proc.stdout
    deploys = [
        line
        for line in proc.stdout.splitlines()
        if line.startswith("PLAN:") and "run jobs deploy" in line
    ]
    assert len(deploys) == 12
    for dep in deploys:
        assert "--service-account <projectNumber>-compute@developer.gserviceaccount.com" in dep
        assert "runtime-identity=temporary-default-compute" in dep
        # The class identity is P34.42b-live-2's — never named on these jobs.
        assert "sig-ingest-rt" not in dep


def test_every_trigger_is_paused_immediately_after_create() -> None:
    proc = _run("--check")
    assert proc.returncode == 0
    lines = [line for line in proc.stdout.splitlines() if line.startswith("PLAN:")]
    for _, _, _, sched, _, _ in CONTRACT:
        idx = next(
            i for i, line in enumerate(lines) if f"scheduler jobs create http {sched} " in line
        )
        assert f"scheduler jobs pause {sched} " in lines[idx + 1]
        assert f"scheduler jobs describe {sched} " in lines[idx + 2]
        assert "PAUSED" in lines[idx + 2]


# --- apply-mode refusals (stubbed gcloud; no production contact) --------------


def _install_gcloud_stub(tmp_path: Path) -> Path:
    """A stateful fake gcloud: ADC token + the read/write calls the leg makes.

    Created jobs/triggers are recorded under GCLOUD_STUB_STATE so describes
    flip from NOT_FOUND to a synthesized spec after their create — letting the
    leg's poststate verification run end-to-end offline.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "gcloud"
    stub.write_text(GCLOUD_STUB, encoding="utf-8")
    stub.chmod(0o755)
    return bin_dir


def _apply(tmp_path: Path, **env: str) -> subprocess.CompletedProcess[str]:
    stub = _install_gcloud_stub(tmp_path)
    full = _env(
        SIG_SEED_NOW=SYNTHETIC_IN_WINDOW,
        GCLOUD_STUB_STATE=str(tmp_path / "gstate"),
        PATH=f"{stub}:{os.environ['PATH']}",
        **env,
    )
    return subprocess.run(
        ["bash", str(SCRIPT), "--apply", "--evidence-dir", str(tmp_path / "ev")],
        capture_output=True,
        text=True,
        check=False,
        env=full,
        cwd=str(REPO_ROOT),
    )


def test_apply_queues_outside_the_window() -> None:
    for now in (SYNTHETIC_WEEKEND, SYNTHETIC_EARLY, SYNTHETIC_LATE):
        proc = _run("--apply", SIG_SEED_NOW=now)
        assert proc.returncode == 42, now
        assert "287a_P35.1a1" in proc.stdout
        assert "run jobs deploy" not in proc.stdout


def test_apply_inside_the_window_reaches_the_adc_gate() -> None:
    proc = _run("--apply", SIG_SEED_NOW=SYNTHETIC_IN_WINDOW)
    assert proc.returncode == 3  # no ADC → gate-pending, never a fabrication


def test_existing_job_refuses_before_any_mutation(tmp_path: Path) -> None:
    gstate = tmp_path / "gstate"
    gstate.mkdir()
    (gstate / "job-sig-ingest-r11-ate-01.json").write_text(
        json.dumps({"metadata": {"name": "sig-ingest-r11-ate-01"}})
    )
    proc = _apply(tmp_path)
    assert proc.returncode == 2
    assert "already exists" in proc.stderr
    calls = (tmp_path / "gstate" / "calls.log").read_text()
    assert "run jobs deploy" not in calls
    assert "scheduler jobs create" not in calls


def test_existing_trigger_refuses_before_any_mutation(tmp_path: Path) -> None:
    gstate = tmp_path / "gstate"
    gstate.mkdir()
    (gstate / "sched-sig-sched-r11-ate-01.json").write_text(
        json.dumps({"name": "sig-sched-r11-ate-01", "state": "ENABLED"})
    )
    proc = _apply(tmp_path)
    assert proc.returncode == 2
    calls = (tmp_path / "gstate" / "calls.log").read_text()
    assert "run jobs deploy" not in calls


def test_missing_sig_scheduler_refuses(tmp_path: Path) -> None:
    proc = _apply(tmp_path, GCLOUD_STUB_NO_SCHED_SA="1")
    assert proc.returncode == 2
    assert "sig-scheduler" in proc.stderr
    calls = (tmp_path / "gstate" / "calls.log").read_text()
    assert "run jobs deploy" not in calls


def test_running_target_execution_refuses(tmp_path: Path) -> None:
    proc = _apply(tmp_path, GCLOUD_STUB_EXEC_RUNNING="1")
    assert proc.returncode == 2
    assert "execution" in proc.stderr
    calls = (tmp_path / "gstate" / "calls.log").read_text()
    assert "run jobs deploy" not in calls


def test_apply_happy_path_creates_pauses_and_verifies(tmp_path: Path) -> None:
    proc = _apply(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = (tmp_path / "gstate" / "calls.log").read_text().splitlines()
    deploys = [c for c in calls if " run jobs deploy " in f" {c} "]
    creates = [c for c in calls if "scheduler jobs create http" in c]
    pauses = [c for c in calls if "scheduler jobs pause" in c]
    binds = [c for c in calls if "add-iam-policy-binding" in c]
    assert len(deploys) == len(creates) == len(pauses) == len(binds) == 12
    for _, _, job, sched, _, _ in CONTRACT:
        di = next(i for i, c in enumerate(calls) if f"run jobs deploy {job} " in c)
        bi = next(i for i, c in enumerate(calls) if "add-iam-policy-binding" in c and job in c)
        ci = next(i for i, c in enumerate(calls) if f"create http {sched} " in c)
        pi = next(i for i, c in enumerate(calls) if f"pause {sched} " in c)
        assert di < bi < ci < pi
        post = json.loads((tmp_path / "ev" / "post" / f"trigger-{sched}.json").read_text())
        assert post["state"] == "PAUSED"
    assert "poststate verify OK" in proc.stdout
    # The temporary identity + paused triggers are the recorded interim state.
    job = json.loads((tmp_path / "ev" / "post" / "job-sig-ingest-r11-ate-01.json").read_text())
    spec = job["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == COMPUTE_SA
    assert spec["containers"][0]["image"].endswith(f"@{PINNED}")
    # Never any execution.
    assert all("jobs execute" not in c for c in calls)


def test_pause_failure_rolls_back_only_this_legs_creations(tmp_path: Path) -> None:
    proc = _apply(tmp_path, GCLOUD_STUB_PAUSE_FAIL="sig-sched-r11-ate-01")
    assert proc.returncode == 2
    calls = (tmp_path / "gstate" / "calls.log").read_text().splitlines()
    # The created trigger + job + binding are deleted; nothing else is.
    assert any("scheduler jobs delete sig-sched-r11-ate-01" in c for c in calls)
    assert any("run jobs delete sig-ingest-r11-ate-01" in c for c in calls)
    assert any("remove-iam-policy-binding sig-ingest-r11-ate-01" in c for c in calls)
    deleted = [c for c in calls if "delete" in c or "remove-iam-policy-binding" in c]
    assert deleted, "rollback deleted nothing"
    contract_names = {n for _, _, j, s, _, _ in CONTRACT for n in (j, s)}
    assert all(any(n in c for n in contract_names) for c in deleted), deleted


def test_rollback_action_replays_only_the_recorded_manifest(tmp_path: Path) -> None:
    ev = tmp_path / "ev"
    ev.mkdir()
    (ev / "created.txt").write_text(
        "job sig-ingest-r11-ate-01\nbinding sig-ingest-r11-ate-01\ntrigger sig-sched-r11-ate-01\n"
    )
    proc = _run("--check", "rollback", "--evidence-dir", str(ev))
    assert proc.returncode == 0
    assert "rollback replays" in proc.stdout


# --- the script never carries out-of-scope mutations --------------------------


def test_the_script_never_executes_or_enables() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "jobs execute",
        "scheduler jobs run",
        "scheduler jobs resume",
        "services enable",
        "service-accounts create",
    ):
        assert forbidden not in text, forbidden
    # The fleet-wide reconcile may be NAMED in a comment (as the deliberately
    # out-of-scope tool) but is never invoked — every mention is a comment.
    for line in text.splitlines():
        if "scheduled-ops.sh" in line:
            assert line.lstrip().startswith("#"), line


def test_no_secret_value_or_project_literal_in_the_script() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "gserviceaccount.com" in text  # derived, never a literal e-mail
    for forbidden in ("eleutheria", "postgres://", "token="):
        assert forbidden not in text.lower(), forbidden


# --- the stub -----------------------------------------------------------------

GCLOUD_STUB = r"""#!/usr/bin/env bash
set -u
state="${GCLOUD_STUB_STATE:?}"
mkdir -p "$state"
printf '%s\n' "$*" >> "$state/calls.log"
full="$*"

if [[ "$full" == *"auth application-default print-access-token"* ]]; then
  echo stub-token; exit 0
fi
if [[ "$full" == *"artifacts docker images describe"* ]]; then
  # A tag ref always resolves to a DIFFERENT digest — only the literal pin is
  # the contract image (used by the resolves-elsewhere refusal test).
  echo "registry.example/sig/sig-api@sha256:$(printf 'cd%.0s' {1..32})"; exit 0
fi
if [[ "$full" == *"scheduler jobs describe "* ]]; then
  name="${full#*jobs describe }"; name="${name%% *}"
  if [ -f "$state/sched-$name.json" ]; then
    if [[ "$full" == *"value(state)"* ]]; then
      python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' \
        "$state/sched-$name.json"
    else
      cat "$state/sched-$name.json"
    fi
    exit 0
  else echo "NOT_FOUND $name" >&2; exit 1; fi
fi
if [[ "$full" == *"scheduler jobs create http "* ]]; then
  python3 - "$state" "$@" <<'PYEOF'
import json, sys, pathlib
state = pathlib.Path(sys.argv[1]); args = sys.argv[2:]
name = args[args.index("http") + 1]
def val(flag):
    return args[args.index(flag) + 1] if flag in args else ""
def pre(prefix):
    return next((a[len(prefix):] for a in args if a.startswith(prefix)), "")
rec = {
    "state": "ENABLED",
    "schedule": val("--schedule"),
    "timeZone": pre("--time-zone="),
    "httpTarget": {
        "uri": val("--uri"),
        "httpMethod": "POST",
        "oauthToken": {"serviceAccountEmail": pre("--oauth-service-account-email=")},
    },
}
(state / f"sched-{name}.json").write_text(json.dumps(rec))
PYEOF
  exit 0
fi
if [[ "$full" == *"scheduler jobs pause "* ]]; then
  name="${full#*jobs pause }"; name="${name%% *}"
  if [ "${GCLOUD_STUB_PAUSE_FAIL:-}" = "$name" ]; then echo "boom" >&2; exit 1; fi
  python3 - "$state" "$name" <<'PYEOF'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]) / f"sched-{sys.argv[2]}.json"
d = json.loads(p.read_text()); d["state"] = "PAUSED"; p.write_text(json.dumps(d))
PYEOF
  exit 0
fi
if [[ "$full" == *"scheduler jobs delete "* ]]; then
  name="${full#*jobs delete }"; name="${name%% *}"
  rm -f "$state/sched-$name.json"; exit 0
fi
if [[ "$full" == *"scheduler jobs list"* ]]; then echo '[]'; exit 0; fi
if [[ "$full" == *"run jobs executions list"* ]]; then
  if [ "${GCLOUD_STUB_EXEC_RUNNING:-}" = "1" ]; then
    echo '[{"status":{"conditions":[{"type":"Running","status":"True"}]}}]'
  else
    echo '[]'
  fi
  exit 0
fi
if [[ "$full" == *"run jobs describe "* ]]; then
  name="${full#*jobs describe }"; name="${name%% *}"
  if [ -f "$state/job-$name.json" ]; then cat "$state/job-$name.json"; exit 0
  else echo "NOT_FOUND $name" >&2; exit 1; fi
fi
if [[ "$full" == *"run jobs deploy "* ]]; then
  python3 - "$state" "$@" <<'PYEOF'
import json, re, sys, pathlib
state = pathlib.Path(sys.argv[1]); args = sys.argv[2:]
name = args[args.index("deploy") + 1]
def val(flag):
    return args[args.index(flag) + 1] if flag in args else ""
def pre(prefix):
    return next((a[len(prefix):] for a in args if a.startswith(prefix)), "")
def secs(d):
    return str(int(d[:-1]) * {"s": 1, "m": 60, "h": 3600}[d[-1]]) + "s"
env = [{"name": kv.split("=", 1)[0], "value": kv.split("=", 1)[1]}
       for kv in val("--set-env-vars").split(",") if kv]
for kv in val("--set-secrets").split(","):
    if not kv:
        continue
    k, ref = kv.split("=", 1)
    secret, _, ver = ref.partition(":")
    env.append({"name": k, "valueFrom": {"secretKeyRef": {"secret": secret, "key": ver}}})
bucket = re.search(r"bucket=([^,\"]+)", val("--add-volume"))
bucket = bucket.group(1) if bucket else ""
rec = {"spec": {"template": {"spec": {
    "serviceAccountName": val("--service-account"),
    "maxRetries": 0,
    "taskTimeout": secs(val("--task-timeout")),
    "containers": [{
        "image": val("--image"),
        "args": [val("--args")],
        "env": env,
        "volumeMounts": [{"name": "captures", "mountPath": "/mnt/captures"}],
    }],
    "volumes": [{"name": "captures", "cloudStorage": {"bucket": bucket}}],
}}}}
(state / f"job-{name}.json").write_text(json.dumps(rec))
print(f"created {name}")
PYEOF
  exit 0
fi
if [[ "$full" == *"run jobs delete "* ]]; then
  name="${full#*jobs delete }"; name="${name%% *}"
  rm -f "$state/job-$name.json"; exit 0
fi
if [[ "$full" == *"run jobs add-iam-policy-binding"* ]] || \
  [[ "$full" == *"run jobs remove-iam-policy-binding"* ]]; then
  exit 0
fi
if [[ "$full" == *"run jobs list"* ]]; then
  python3 - "$state" <<'PYEOF'
import json, sys, pathlib
state = pathlib.Path(sys.argv[1])
names = [f"sig-preexisting-{i:02d}" for i in range(88)]
names += sorted(p.name[4:-5] for p in state.glob("job-*.json"))
print(json.dumps([{"metadata": {"name": n}} for n in names]))
PYEOF
  exit 0
fi
if [[ "$full" == *"iam service-accounts describe"* ]]; then
  if [ "${GCLOUD_STUB_NO_SCHED_SA:-}" = "1" ]; then echo "NOT_FOUND" >&2; exit 1; fi
  echo '{"email":"sig-scheduler@x.iam.gserviceaccount.com"}'; exit 0
fi
if [[ "$full" == *"projects describe"* ]]; then echo '12345'; exit 0; fi
if [[ "$full" == *"storage buckets get-iam-policy"* ]]; then echo '{"bindings":[]}'; exit 0; fi
if [[ "$full" == *"secrets get-iam-policy"* ]]; then echo '{"bindings":[]}'; exit 0; fi
echo '[]'
exit 0
"""
