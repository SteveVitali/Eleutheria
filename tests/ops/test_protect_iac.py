# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.3 ops data protection — `ops/gcp/protect.sh` offline contract.

Covers the ticket's deterministic acceptance criteria (SIG-OPS-002 owned;
SIG-STORE-048 cited): the script is dry-run-by-default with no ADC and no
network, `--verify` diffs recorded describe JSON (the AC's offline mechanism —
the `pre/` fixtures mirror the real 2026-10-02T04:10:28Z live capture whose
sha256 digests are recorded in `docs/build/runs/P34.3.md`), the live window
guard refuses inside the daily band / AR-3 windows, and a re-run is a safe
SKIP. `--apply` itself is never executed against production in tests: a stub
`gcloud` on PATH records invocations so the guard and idempotency paths run
fully offline.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "protect.sh"
FIXTURES = Path(__file__).parent / "fixtures" / "protect"

# The live window: mutations never inside 03:00–10:00Z; sig-pg legs additionally
# never inside an AR-3 window (from 2026-10-06T00:00Z; future-ok: scheduled: AR-3),
# sig-materialize runs.
INSIDE_DAILY_BAND = "2026-10-02T05:00:00Z"
INSIDE_AR3 = "2026-10-08T12:00:00Z"  # AR-3 window — future-ok: scheduled: AR-3 window
OPEN_WINDOW = "2026-10-03T12:00:00Z"  # outside both

_STUB_GCLOUD = """#!/usr/bin/env bash
# Offline gcloud stub: logs every invocation to $GCLOUD_STUB_LOG, then serves
# canned replies so apply-mode code paths run without ADC or network.
printf '%s\\n' "$*" >> "${GCLOUD_STUB_LOG:-/dev/null}"
case "$*" in
  "auth application-default print-access-token") echo stub-token ;;
  "sql instances patch --help")
    echo '--deletion-protection --retain-backups-on-delete'
    echo '--maintenance-window-day --maintenance-window-hour'
    echo '--storage-auto-increase-limit'
    ;;
  "sql instances describe"*)
    cat "$STUB_SQL_DESCRIBE"
    ;;
  "sql operations describe"*) echo '{"status":"DONE","operationType":"UPDATE"}' ;;
  "sql backups create --help") echo 'creates a backup' ;;
  "run jobs executions list"*) echo '[]' ;;
  "run services describe"*) echo 'https://sig-web-stub.run.app' ;;
  "storage buckets describe"*) cat "$STUB_BUCKET_DESCRIBE" ;;
  "storage buckets get-iam-policy"*) cat "$STUB_IAM" ;;
  *) echo '{}' ;;
esac
"""

_CURL_STUB = """#!/usr/bin/env bash
# Offline curl stub for the QA-7 site checks. The first CURL_STUB_GREEN calls
# answer green (200 pages / 206 ranged PMTiles — the pre-mutation baseline);
# every later call answers with the post-mutation outcome:
#   *_STUB_PAGE_AFTER  for the canonical/run.app pages (default 500)
#   *_STUB_TILES_AFTER for a *.pmtiles URL          (default same)
#   *_STUB_BUCKET_AFTER for the direct bucket URL   (default 403 — private)
count=$(cat "${CURL_STUB_COUNT:-/dev/null}" 2>/dev/null || echo 0)
count=$((count + 1)); printf '%s' "$count" > "${CURL_STUB_COUNT:-/dev/null}"
url="${!#}"
printf '%s\\n' "$url" >> "${CURL_STUB_LOG:-/dev/null}"
case "$url" in
  *storage.googleapis.com*)
    # The direct bucket URL is the privacy check, not a baseline page — it
    # always answers CURL_STUB_BUCKET_AFTER (403/404 = private).
    echo "${CURL_STUB_BUCKET_AFTER:-403}" ;;
  *)
    if [ "$count" -le "${CURL_STUB_GREEN:-6}" ]; then
      case "$url" in *.pmtiles) echo 206 ;; *) echo 200 ;; esac
    else
      echo "${CURL_STUB_PAGE_AFTER:-500}"
    fi ;;
esac
"""


def _env(**overrides: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env.update(overrides)
    return env


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env or _env(),
        cwd=str(REPO_ROOT),
    )


def _stubbed_env(tmp_path: Path, **overrides: str) -> tuple[dict[str, str], Path]:
    """A PATH whose `gcloud` is the offline stub; returns (env, stub log)."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "gcloud"
    stub.write_text(_STUB_GCLOUD)
    stub.chmod(0o755)
    log = tmp_path / "gcloud.log"
    log.touch()
    base = _env(
        PATH=f"{bindir}:{os.environ['PATH']}",
        SIG_GCP_PROJECT="example-proj",
        GCLOUD_STUB_LOG=str(log),
        STUB_SQL_DESCRIBE=str(FIXTURES / "desired" / "sql.json"),
        STUB_BUCKET_DESCRIBE=str(FIXTURES / "desired" / "describe.example-proj-sig-web.json"),
        STUB_IAM=str(FIXTURES / "desired" / "iam.example-proj-sig-web.json"),
    )
    base.update(overrides)
    return base, log


def _mutations_in(log: Path) -> list[str]:
    """Stub invocations that would mutate — a patch/update/create/remove/add."""
    out = []
    for line in log.read_text().splitlines():
        if (
            any(
                tok in line.split()
                for tok in (
                    "patch",
                    "update",
                    "create",
                    "remove-iam-policy-binding",
                    "add-iam-policy-binding",
                    "delete",
                )
            )
            and "--help" not in line
        ):
            out.append(line)
    return out


# --- dry-run default -----------------------------------------------------------


def test_no_args_is_a_plan_only_check() -> None:
    proc = _run([])
    assert proc.returncode == 0, proc.stderr
    assert "PLAN:" in proc.stdout and "check OK" in proc.stdout


def test_dry_run_flag_accepted() -> None:
    proc = _run(["--dry-run"])
    assert proc.returncode == 0, proc.stderr
    assert "check OK" in proc.stdout


@pytest.mark.parametrize("action", ["prestate", "backup", "instance", "buckets", "iam", "all"])
def test_bare_action_is_the_plan_path(action: str) -> None:
    proc = _run([action])
    assert proc.returncode == 0, f"{action}: {proc.stderr}"
    assert "check OK" in proc.stdout


def test_plan_names_every_mutation_and_its_rollback() -> None:
    proc = _run(["--check"], env=_env(SIG_GCP_PROJECT="example-proj"))
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    assert "gs://example-proj-sig-web" in plan  # derived names, not the empty prefix
    for needle in (
        "--deletion-protection --retain-backups-on-delete",
        "--maintenance-window-day=SUN --maintenance-window-hour=9",
        "--storage-auto-increase-limit=40",
        "sql backups create --instance sig-pg --async",
        "gs://example-proj-sig-restricted",
        "gs://example-proj-sig-public",
        "remove-iam-policy-binding",
        "rollback:",
    ):
        assert needle in plan, needle


# --- verify --from-state against recorded describe JSON ------------------------


def test_verify_from_state_reports_every_drift_on_the_recorded_pre_state() -> None:
    """The 2026-10-02T04:10:28Z pre-state capture (mirrored in fixtures) must read
    as drift on all eleven checks — the pre-mutation truth."""
    proc = _run(["--verify", "--from-state", str(FIXTURES / "pre")])
    assert proc.returncode == 1, proc.stdout + proc.stderr
    for check in (
        "qa-1:deletion-protection",
        "qa-1:retain-backups-on-delete",
        "qa-2:maintenance-window",
        "disk-cap:autoresize-limit",
        "qa-6:sig-restricted:versioning",
        "qa-6:sig-restricted:lifecycle",
        "qa-6:sig-public:versioning",
        "qa-6:sig-public:lifecycle",
        "qa-6:sig-web:versioning",
        "qa-6:sig-web:lifecycle",
        "qa-7:sig-web-no-allusers",
    ):
        assert f"DRIFT {check}" in proc.stdout, check
    assert "result=drift" in proc.stdout


def test_verify_from_state_is_green_on_the_desired_state() -> None:
    proc = _run(["--verify", "--from-state", str(FIXTURES / "desired")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 DRIFT" in proc.stdout
    assert "result=ok" in proc.stdout
    assert "OK qa-7:sig-web-no-allusers" in proc.stdout


def test_verify_from_state_refuses_a_missing_dir() -> None:
    proc = _run(["--verify", "--from-state", str(FIXTURES / "nonexistent")])
    assert proc.returncode == 66, proc.stderr


# --- window guard (apply mode, stubbed gcloud) -----------------------------------


def test_apply_refuses_inside_the_daily_band(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PROTECT_NOW=INSIDE_DAILY_BAND)
    proc = _run(["--apply", "all"], env=env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "REFUSED" in proc.stderr
    assert _mutations_in(log) == []


def test_sigpg_leg_refuses_inside_ar3(tmp_path: Path) -> None:
    env, log = _stubbed_env(tmp_path, SIG_PROTECT_NOW=INSIDE_AR3)
    proc = _run(["--apply", "instance"], env=env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "AR-3" in proc.stderr
    assert _mutations_in(log) == []


def test_bucket_leg_may_run_inside_ar3_outside_the_daily_band(tmp_path: Path) -> None:
    env, log = _stubbed_env(
        tmp_path,
        SIG_PROTECT_NOW=INSIDE_AR3,
        # 120-day noncurrent rule satisfies every bucket's floor (>=), so all legs SKIP.
        STUB_BUCKET_DESCRIBE=str(FIXTURES / "stub" / "bucket-already.json"),
    )
    proc = _run(["--apply", "buckets"], env=env)
    # Bucket describe returns a stricter-than-required state -> every step SKIPs.
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.count("SKIP") >= 6  # versioning + lifecycle, three buckets
    assert _mutations_in(log) == []


def test_prestate_capture_is_read_only_and_runs_inside_the_band(tmp_path: Path) -> None:
    """Pre-state capture is a read-only leg — allowed even inside 03:00–10:00Z."""
    evidence = tmp_path / "evidence"
    env, _log = _stubbed_env(
        tmp_path,
        SIG_PROTECT_NOW=INSIDE_DAILY_BAND,
        SIG_PROTECT_EVIDENCE_DIR=str(evidence),
    )
    proc = _run(["--apply", "prestate"], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert list(evidence.glob("pre-*/sql.json")), "pre-state capture not written"


def test_sigpg_leg_is_idempotent_when_already_set(tmp_path: Path) -> None:
    """A re-run after a landed apply reads live state and SKIPs — no patch."""
    env, log = _stubbed_env(tmp_path, SIG_PROTECT_NOW=OPEN_WINDOW)
    proc = _run(["--apply", "instance"], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.count("SKIP") == 3
    assert _mutations_in(log) == []


def test_apply_needs_adc_even_in_a_window(tmp_path: Path) -> None:
    """With no ADC resolvable, apply exits at the credential gate (rc 3) before
    any mutation path. A `gcloud` that fails every call shadows any real one —
    deterministic whether or not the host has gcloud or credentials."""
    bindir = tmp_path / "bin-noadc"
    bindir.mkdir()
    stub = bindir / "gcloud"
    stub.write_text("#!/usr/bin/env bash\nexit 1\n")
    stub.chmod(0o755)
    proc = _run(
        ["--apply", "instance"],
        env=_env(
            PATH=f"{bindir}:{os.environ['PATH']}",
            SIG_GCP_PROJECT="example-proj",
            SIG_PROTECT_NOW=OPEN_WINDOW,
        ),
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr


# --- QA-7 IAM leg: baseline gate, removal, rollback scope ------------------------

# act_iam's curl call order: canonical baseline (3), run.app baseline (3),
# canonical post (3), run.app post (3), direct bucket URL (1). The gcloud stub
# resolves the run.app service URL, so the baseline is exactly 6 calls.
BASELINE_CALLS = 6


def _iam_env(
    tmp_path: Path,
    *,
    iam_fixture: Path,
    green_calls: int,
    page_after: int = 500,
    bucket_after: int = 403,
) -> tuple[dict[str, str], Path, Path]:
    """gcloud + curl stubs on PATH; returns (env, gcloud log, curl log)."""
    env, glog = _stubbed_env(
        tmp_path,
        SIG_PROTECT_NOW=OPEN_WINDOW,
        STUB_IAM=str(iam_fixture),
        CURL_STUB_GREEN=str(green_calls),
        CURL_STUB_PAGE_AFTER=str(page_after),
        CURL_STUB_BUCKET_AFTER=str(bucket_after),
    )
    bindir = tmp_path / "bin"
    curl = bindir / "curl"
    curl.write_text(_CURL_STUB)
    curl.chmod(0o755)
    clog = tmp_path / "curl.log"
    clog.touch()
    counter = tmp_path / "curl.count"
    counter.write_text("0")
    env["CURL_STUB_LOG"] = str(clog)
    env["CURL_STUB_COUNT"] = str(counter)
    return env, glog, clog


def test_iam_leg_removes_allusers_and_site_stays_green(tmp_path: Path) -> None:
    env, glog, clog = _iam_env(
        tmp_path,
        iam_fixture=FIXTURES / "pre" / "iam-sig-web-20261002T041028Z.json",
        green_calls=13,  # everything green; direct bucket URL must read private
    )
    proc = _run(["--apply", "iam"], env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    mutations = _mutations_in(glog)
    assert any("remove-iam-policy-binding" in m and "allUsers" in m for m in mutations)
    assert not any("add-iam-policy-binding" in m for m in mutations)
    assert "403" in proc.stdout or "404" in proc.stdout  # direct bucket URL check
    assert clog.read_text().count("sig-web-stub.run.app") >= 2  # run.app checked


def test_iam_leg_rolls_back_the_removal_on_a_post_site_failure(tmp_path: Path) -> None:
    """Stop rule: a site route failing after the removal rolls THAT action back."""
    env, glog, _clog = _iam_env(
        tmp_path,
        iam_fixture=FIXTURES / "pre" / "iam-sig-web-20261002T041028Z.json",
        green_calls=BASELINE_CALLS,  # baseline green; the post-check goes red
    )
    proc = _run(["--apply", "iam"], env=env)
    assert proc.returncode == 7, proc.stdout + proc.stderr
    mutations = _mutations_in(glog)
    assert any("remove-iam-policy-binding" in m for m in mutations)
    assert any("add-iam-policy-binding" in m and "allUsers" in m for m in mutations)


def test_iam_leg_rolls_back_when_the_bucket_stays_public(tmp_path: Path) -> None:
    env, glog, _clog = _iam_env(
        tmp_path,
        iam_fixture=FIXTURES / "pre" / "iam-sig-web-20261002T041028Z.json",
        green_calls=12,  # all site checks green…
        bucket_after=200,  # …but the bucket URL still answers publicly
    )
    proc = _run(["--apply", "iam"], env=env)
    assert proc.returncode == 7, proc.stdout + proc.stderr
    assert "still publicly readable" in proc.stderr
    assert any("add-iam-policy-binding" in m for m in _mutations_in(glog))


def test_iam_leg_skip_never_re_adds_allusers_on_an_unrelated_outage(
    tmp_path: Path,
) -> None:
    """With the binding already absent (SKIP) a post-check failure must NOT
    re-add allUsers — that would grant public read the pre-state never had."""
    env, glog, _clog = _iam_env(
        tmp_path,
        iam_fixture=FIXTURES / "desired" / "iam.example-proj-sig-web.json",
        green_calls=BASELINE_CALLS,
    )
    proc = _run(["--apply", "iam"], env=env)
    assert proc.returncode == 7, proc.stdout + proc.stderr
    assert "SKIP" in proc.stdout
    mutations = _mutations_in(glog)
    assert not any("remove-iam-policy-binding" in m for m in mutations)
    assert not any("add-iam-policy-binding" in m for m in mutations)


def test_iam_leg_refuses_on_a_red_baseline(tmp_path: Path) -> None:
    """A red baseline is never mutated on: 0 green calls, exit 7, no writes."""
    env, glog, _clog = _iam_env(
        tmp_path,
        iam_fixture=FIXTURES / "pre" / "iam-sig-web-20261002T041028Z.json",
        green_calls=0,
    )
    proc = _run(["--apply", "iam"], env=env)
    assert proc.returncode == 7, proc.stdout + proc.stderr
    assert "red baseline" in proc.stderr
    assert _mutations_in(glog) == []
