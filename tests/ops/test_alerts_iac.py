# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.4 alerts that reach a human — `ops/monitoring/` + `ops/gcp/alerts.sh`.

Covers the ticket's deterministic acceptance criteria (QA-3/QA-4/QA-5 owned;
QA-8 disable engineered): the committed alert-set definitions, the read-only
verify diff (fixture-verified both directions — `live-post` mirrors the desired
post-leg state; the captured 2026-10-02T06:09Z pre-state drives the drift
assertions), the window guard, the sweep-gated jobfail ordering, the mutation
allowlist (only the five authorized mutations ever reach stubbed gcloud/gh),
and secret hygiene (the webhook token is never printed or persisted).
`--apply` never touches production in tests: stub gcloud/gh/curl/uv binaries on
PATH record invocations and serve canned state.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "alerts.sh"
DEFS_DIR = REPO_ROOT / "ops" / "monitoring"
FIXTURES = Path(__file__).parent / "fixtures" / "alerts"
STUBS = FIXTURES / "stubs"
LIVE_POST = FIXTURES / "live-post"
JOBFAIL_ID = "7285515107319155929"

sys.path.insert(0, str(REPO_ROOT / "ops" / "src"))
from ops import cli as ops_cli  # noqa: E402
from ops import monitoring_defs as md  # noqa: E402

INSIDE_BAND = "2026-10-02T05:00:00Z"  # 03:00–10:00Z never-band
OPEN_WINDOW = "2026-10-03T12:00:00Z"  # outside band + AR-3
INSIDE_AR3 = "2026-10-08T12:00:00Z"  # AR-3 window, outside the band

GREEN_EXEC = [{"status": {"conditions": [{"type": "Completed", "status": "True"}]}}]
RED_EXEC = [
    {
        "status": {
            "conditions": [
                {"type": "Completed", "status": "False"},
                {"type": "Failed", "status": "True"},
            ]
        }
    }
]
PROJECT = "sig-fixture-project"  # a fixture id — the real id is never committed (OP-07)
STALE_IMAGE = f"us-central1-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:" + "b" * 64


def _defs() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(DEFS_DIR.glob("*.json"))}


def _live_post() -> dict[str, list]:
    return md.load_live_dir(LIVE_POST)


def _jobfail_pre() -> dict:
    """The jobfail policy's live PRE-extension shape (captured 06:09Z)."""
    body = dict(_defs()["alert-policy.job-failures"])
    body.pop("_sig")
    body = json.loads(json.dumps(body).replace("{project}", PROJECT))
    body["displayName"] = "SIG — Cloud Run job execution failed (excl. sig-probe)"
    cond = body["conditions"][0]["conditionThreshold"]
    cond["filter"] += ' AND resource.labels.job_name != "sig-probe"'
    body["alertStrategy"].pop("notificationRateLimit")
    body["name"] = f"projects/{PROJECT}/alertPolicies/{JOBFAIL_ID}"
    return body


# --- committed definitions ---------------------------------------------------


def test_every_def_loads_with_a_sane_envelope() -> None:
    defs = md.load_definitions(DEFS_DIR)
    assert len(defs) == 9
    kinds = {d.kind for d in defs}
    assert kinds == {"channel", "uptime", "policy"}
    assert sum(1 for d in defs if d.apply == "create") == 2
    assert sum(1 for d in defs if d.apply == "update") == 4


def test_defs_have_no_volatile_fields_or_literal_project_or_email() -> None:
    for path in sorted(DEFS_DIR.glob("*.json")):
        text = path.read_text()
        doc = json.loads(text)
        assert "medley" not in json.dumps({k: v for k, v in doc.items() if k != "_sig"}), (
            f"{path.name}: the real project id is never committed"
        )
        assert "@" not in text, f"{path.name}: an address literal must never be committed"

        def _vol(o: object) -> bool:
            if isinstance(o, dict):
                return any(k in md.VOLATILE_KEYS or _vol(v) for k, v in o.items())
            if isinstance(o, list):
                return any(_vol(v) for v in o)
            return False

        assert not _vol(doc), path.name
        assert doc.get("enabled", True) is True, path.name


def test_tls_policy_fires_21_days_before_expiry() -> None:
    cond = _defs()["alert-policy.tls-cert-expiry"]["conditions"][0]["conditionThreshold"]
    assert cond["comparison"] == "COMPARISON_LT"
    assert cond["thresholdValue"] == 21
    assert cond["duration"] == "0s"
    assert "monitoring.googleapis.com/uptime_check/time_until_ssl_cert_expires" in cond["filter"]
    assert 'resource.labels.host = "surveillancegraph.org"' in cond["filter"]
    pol = _defs()["alert-policy.tls-cert-expiry"]
    assert pol["alertStrategy"]["notificationRateLimit"] == {"period": "86400s"}
    assert pol["notificationChannels"] == [
        "projects/{project}/notificationChannels/10808426210098728267"
    ]


def test_sigalert_policy_matches_log_lines() -> None:
    pol = _defs()["alert-policy.sig-alert-log"]
    cond = pol["conditions"][0]
    assert "conditionMatchedLog" in cond
    flt = cond["conditionMatchedLog"]["filter"]
    assert 'resource.labels.service_name = "sig-alerts"' in flt
    assert '"SIG-ALERT"' in flt
    # Log-match policies require a notification rate limit + autoClose.
    assert pol["alertStrategy"]["notificationRateLimit"]["period"] == "86400s"
    assert "autoClose" in pol["alertStrategy"]


def test_jobfail_def_is_the_extended_policy() -> None:
    pol = _defs()["alert-policy.job-failures"]
    assert pol["_sig"]["id"] == JOBFAIL_ID
    assert pol["_sig"]["apply"] == "update"
    flt = pol["conditions"][0]["conditionThreshold"]["filter"]
    assert "sig-probe" not in flt, "the exclusion must be gone from the desired state"
    assert 'metric.labels.result = "failed"' in flt
    assert pol["alertStrategy"]["notificationRateLimit"]["period"] == "86400s"


def test_only_one_placeholder_leaf_exists_and_it_is_the_email() -> None:
    leaves = []
    for path in sorted(DEFS_DIR.glob("*.json")):
        name = path.name

        def _walk(o: object, _name: str = name) -> None:
            if isinstance(o, dict):
                for v in o.values():
                    _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)
            elif isinstance(o, str) and md.PLACEHOLDER_RE.match(o):
                leaves.append((_name, o))

        _walk(json.loads(path.read_text()))
    assert [name for name, _ in leaves] == ["channel.operator-email.json"]


# --- verify engine (fixture-verified both directions) ------------------------


def test_verify_zero_drift_on_the_post_leg_state() -> None:
    defs = md.load_definitions(DEFS_DIR)
    findings = md.verify_definitions(defs, _live_post(), PROJECT)
    assert md.verify_exit_code(findings) == 0
    assert len(findings) == 9
    assert all(f.status == "OK" for f in findings)


def test_verify_on_the_captured_pre_state_shows_exactly_the_queued_work() -> None:
    """Pre-state (the real 06:09Z capture shape): jobfail DRIFT + 2 MISSING."""
    live = _live_post()
    live["policies"] = [
        p
        for p in live["policies"]
        if "TLS certificate expiry" not in p.get("displayName", "")
        and "SIG-ALERT" not in p.get("displayName", "")
    ]
    live["policies"] = [
        _jobfail_pre() if str(p.get("name", "")).endswith(JOBFAIL_ID) else p
        for p in live["policies"]
    ]
    defs = md.load_definitions(DEFS_DIR)
    findings = md.verify_definitions(defs, live, PROJECT)
    by_slug = {f.slug: f.status for f in findings}
    assert by_slug["alert-policy.job-failures"] == "DRIFT"
    assert by_slug["alert-policy.tls-cert-expiry"] == "MISSING"
    assert by_slug["alert-policy.sig-alert-log"] == "MISSING"
    assert md.verify_exit_code(findings) == 1


def test_verify_flags_a_drifted_field() -> None:
    live = _live_post()
    for p in live["policies"]:
        if str(p.get("name", "")).endswith(JOBFAIL_ID):
            p["conditions"][0]["conditionThreshold"]["filter"] += (
                ' AND resource.labels.job_name != "sig-probe"'
            )
    findings = md.verify_definitions(md.load_definitions(DEFS_DIR), live, PROJECT)
    drift = [f for f in findings if f.status == "DRIFT"]
    assert [f.slug for f in drift] == ["alert-policy.job-failures"]
    assert "sig-probe" in drift[0].detail


def test_verify_flags_an_undeclared_live_policy() -> None:
    live = _live_post()
    extra = dict(live["policies"][0])
    extra["name"] = f"projects/{PROJECT}/alertPolicies/1"
    extra["displayName"] = "someone added this in the console"
    live["policies"] = [*live["policies"], extra]
    findings = md.verify_definitions(md.load_definitions(DEFS_DIR), live, PROJECT)
    assert any(f.status == "EXTRA" and f.kind == "policy" for f in findings)
    assert md.verify_exit_code(findings) == 1


def test_redacted_placeholder_never_compares() -> None:
    live = _live_post()
    live["channels"][0]["labels"]["email_address"] = "someone-else@example.invalid"
    findings = md.verify_definitions(md.load_definitions(DEFS_DIR), live, PROJECT)
    assert md.verify_exit_code(findings) == 0


def test_project_substitution_binds_the_live_project() -> None:
    live = _live_post()
    defs = md.load_definitions(DEFS_DIR)
    assert md.verify_exit_code(md.verify_definitions(defs, live, "other-project")) == 1
    assert md.infer_project(live) == PROJECT


def test_render_produces_a_valid_policy_body() -> None:
    defn = next(
        d for d in md.load_definitions(DEFS_DIR) if d.slug == "alert-policy.tls-cert-expiry"
    )
    body = md.render_policy_body(defn, PROJECT)
    assert "_sig" not in body and "name" not in body
    assert "{project}" not in json.dumps(body)
    assert body["displayName"].startswith("SIG —")
    assert body["notificationChannels"][0].startswith(f"projects/{PROJECT}/notificationChannels/")


def test_cli_verify_verb_exit_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    # SIG_GCP_PROJECT may be set session-wide (the leak-check gate exports a
    # sentinel); the fixture's project must come from the captured names.
    monkeypatch.delenv("SIG_GCP_PROJECT", raising=False)
    rc = ops_cli.main(["monitoring-defs", "verify", "--from-state", str(LIVE_POST)])
    assert rc == 0  # project inferred from the captured names


# --- the script: check mode + window guard + mutation allowlist --------------


def _env(tmp_path: Path, state: dict | None = None, **over: str) -> tuple[dict, Path]:
    """PATH with the offline stubs; returns (env, evidence-root)."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    for name in ("gcloud", "gh", "curl"):
        shutil.copy(STUBS / name, bindir / name)
        (bindir / name).chmod(0o755)
    uv_stub = (STUBS / "uv").read_text().replace("@REPO_ROOT@", str(REPO_ROOT))
    (bindir / "uv").write_text(uv_stub)
    (bindir / "uv").chmod(0o755)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state or _default_state()))
    ev = tmp_path / "evidence"
    env = dict(
        os.environ,
        PATH=f"{bindir}:{os.environ['PATH']}",
        SIG_GCP_PROJECT=PROJECT,
        GCLOUD_STUB_STATE=str(state_path),
        GCLOUD_STUB_LOG=str(tmp_path / "gcloud.log"),
        GH_STUB_LOG=str(tmp_path / "gh.log"),
        CURL_STUB_LOG=str(tmp_path / "curl.log"),
        UV_STUB_LOG=str(tmp_path / "uv.log"),
        SIG_ALERTS_EVIDENCE_DIR=str(ev),
        SIG_ALERTS_DELIVERY_WAIT="0",
    )
    env.update(over)
    return env, ev


def _default_state() -> dict:
    live = _live_post()
    policies = [
        p
        for p in live["policies"]
        if "TLS certificate expiry" not in p.get("displayName", "")
        and "SIG-ALERT" not in p.get("displayName", "")
    ]
    policies = [
        _jobfail_pre() if str(p.get("name", "")).endswith(JOBFAIL_ID) else p for p in policies
    ]
    return {
        "project": PROJECT,
        "channels": live["channels"],
        "uptime": live["uptime_checks"],
        "policies": policies,
        "probe_image": STALE_IMAGE,
        "probe_commit": "sha256:" + "b" * 64,
        "probe_execs": GREEN_EXEC,
        "wf_state": "active",
        "log_rows": [{"textPayload": "SIG-ALERT-RECEIVED … delivery test …"}],
    }


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _gcloud_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "gcloud.log"
    return log.read_text().splitlines() if log.exists() else []


def test_no_args_is_a_plan_only_check(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    env.pop("SIG_GCP_PROJECT")
    proc = _run([], env)
    assert proc.returncode == 0
    assert "check OK" in proc.stdout
    assert "PLAN:" in proc.stdout
    # Check mode makes no tool calls at all.
    assert _gcloud_calls(tmp_path) == []
    assert not (tmp_path / "gh.log").exists()


def test_plan_names_every_mutation_and_rollback(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    proc = _run(["--check"], env)
    out = proc.stdout
    assert "tls-cert-expiry" in out and "sig-alert-log" in out
    assert "gh workflow disable reingest.yml" in out
    assert "roll-jobs --job sig-probe" in out
    assert f"policies update {JOBFAIL_ID}" in out
    assert out.count("rollback") >= 4


@pytest.mark.parametrize(
    "action", ["monitoring", "reingest", "proberoll", "delivery", "jobfail", "all"]
)
def test_apply_refuses_inside_the_daily_band(tmp_path: Path, action: str) -> None:
    env, _ = _env(tmp_path, SIG_ALERTS_NOW=INSIDE_BAND)
    proc = _run(["--apply", action], env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "03:00-10:00Z" in proc.stderr
    mutating = [
        line
        for line in _gcloud_calls(tmp_path)
        if any(w in line for w in ("create", "update", "delete", "submit", "patch"))
        and "describe" not in line
    ]
    # `executions list`/`policies list` are reads; nothing mutating may run.
    assert mutating == [], mutating


def test_proberoll_alone_refuses_inside_ar3(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTS_NOW=INSIDE_AR3)
    proc = _run(["--apply", "proberoll"], env)
    assert proc.returncode == 42
    assert "AR-3" in proc.stderr


def test_monitoring_leg_may_run_inside_ar3(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTS_NOW=INSIDE_AR3)
    proc = _run(["--apply", "monitoring"], env)
    assert proc.returncode == 0, proc.stderr
    creates = [line for line in _gcloud_calls(tmp_path) if "policies create" in line]
    assert len(creates) == 2


def test_prestate_runs_inside_the_band_read_only(tmp_path: Path) -> None:
    env, ev = _env(tmp_path, SIG_ALERTS_NOW=INSIDE_BAND)
    proc = _run(["--apply", "prestate"], env)
    assert proc.returncode == 0, proc.stderr
    pre = list(ev.glob("pre-*"))
    assert pre and (pre[0] / "sha256s.txt").exists()
    assert not any(
        "policies create" in line or "policies update" in line or "jobs update" in line
        for line in _gcloud_calls(tmp_path)
    )


def test_apply_all_runs_only_the_five_authorized_mutations(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTS_NOW=OPEN_WINDOW)
    proc = _run(["--apply", "all"], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _gcloud_calls(tmp_path)
    allowed = (
        "gcloud auth application-default print-access-token",
        "gcloud beta monitoring channels list",
        "gcloud monitoring uptime list",
        "gcloud alpha monitoring policies list",
        "gcloud alpha monitoring policies describe",
        "gcloud alpha monitoring policies create",
        "gcloud alpha monitoring policies update",
        "gcloud run jobs describe",
        "gcloud run jobs update",
        "gcloud run jobs executions list",
        "gcloud run services describe",
        "gcloud compute ssl-certificates describe",
        "gcloud secrets versions access",
        "gcloud builds submit",
        "gcloud artifacts docker images describe",
        "gcloud logging read",
    )
    assert calls, "the stub saw no gcloud calls"
    for line in calls:
        assert line.startswith(allowed), f"unauthorized gcloud call: {line}"
    gh = (tmp_path / "gh.log").read_text().splitlines()
    for line in gh:
        assert line.startswith(("gh workflow list", "gh workflow disable", "gh run list")), line
    # Exactly the authorized writes:
    assert sum("policies create" in line for line in calls) == 2
    assert sum(f"policies update {JOBFAIL_ID}" in line for line in calls) == 1
    assert sum("jobs update" in line for line in calls) == 1
    assert sum("builds submit" in line for line in calls) == 1
    assert sum("workflow disable reingest.yml" in line for line in gh) == 1
    # The roll went through the pinned-digest machinery, probe job only.
    uv = (tmp_path / "uv.log").read_text()
    assert "roll-jobs --job sig-probe --image" in uv
    assert "@sha256:" in uv and ":latest" not in uv
    # Post-state verify converged to zero drift.
    assert "result=ok" in proc.stdout


def test_jobfail_refuses_while_the_sweep_is_red(tmp_path: Path) -> None:
    state = _default_state()
    state["probe_execs"] = RED_EXEC
    env, _ = _env(tmp_path, state=state, SIG_ALERTS_NOW=OPEN_WINDOW)
    proc = _run(["--apply", "jobfail"], env)
    assert proc.returncode == 42
    assert "not green" in proc.stderr
    assert not any("policies update" in line for line in _gcloud_calls(tmp_path))


def test_monitoring_create_is_idempotent(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTS_NOW=OPEN_WINDOW)
    assert _run(["--apply", "monitoring"], env).returncode == 0
    proc = _run(["--apply", "monitoring"], env)
    assert proc.returncode == 0
    assert "SKIP create" in proc.stdout
    calls = _gcloud_calls(tmp_path)
    assert sum("policies create" in line for line in calls) == 2  # only the first run
    assert sum("policies update" in line for line in calls) >= 2  # the second run updates


def test_delivery_never_prints_or_persists_the_token(tmp_path: Path) -> None:
    env, ev = _env(tmp_path, SIG_ALERTS_NOW=OPEN_WINDOW, STUB_SECRET_VALUE="STUBTOKEN-XYZ-SECRET")
    proc = _run(["--apply", "delivery"], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "STUBTOKEN-XYZ-SECRET" not in proc.stdout + proc.stderr
    for f in ev.rglob("*"):
        if f.is_file():
            assert "STUBTOKEN-XYZ-SECRET" not in f.read_text(errors="replace"), f


def test_verify_live_diff_after_stubbed_apply(tmp_path: Path) -> None:
    """The queued-work diff pre-leg vs the zero-drift post-leg (AC wording)."""
    env, _ = _env(tmp_path, SIG_ALERTS_NOW=OPEN_WINDOW)
    proc = _run(["--verify"], env)
    assert proc.returncode == 1
    assert "MISSING" in proc.stdout and "DRIFT" in proc.stdout
    assert _run(["--apply", "all"], env).returncode == 0
    proc = _run(["--verify"], env)
    assert proc.returncode == 0, proc.stdout
    assert "9 OK" in proc.stdout


def test_verify_from_state_green_and_missing_dir(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    proc = _run(["--verify", "--from-state", str(LIVE_POST)], env)
    assert proc.returncode == 0
    assert "9 OK" in proc.stdout
    assert "OK workflow/reingest" in proc.stdout
    assert "OK job/sig-probe" in proc.stdout
    proc = _run(["--verify", "--from-state", str(tmp_path / "nope")], env)
    assert proc.returncode == 66


# --- committed workflow + cadence invariants ---------------------------------


def test_reingest_schedule_removed_dispatch_kept() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "reingest.yml").read_text()
    assert "schedule:" not in text
    assert "cron:" not in text
    assert "workflow_dispatch:" in text


def test_probe_cadence_unchanged_and_sane() -> None:
    """The re-roll target = the committed cadence — pin invariants, not the
    living list (the retired france/okc manifest targets the stale image still
    probes must never return)."""
    import tomllib

    cadence = tomllib.loads((REPO_ROOT / "ops" / "cadence.toml").read_text())
    probes = cadence["probes"]
    assert probes["job"] == "sig-probe"
    assert probes["scheduler"] == "sig-sched-probe"
    names = {t["name"] for t in probes["targets"]}
    assert "sig-api-health" in names
    assert not any("france" in n or "okc-manifest" in n for n in names), (
        "a retired manifest target is back in the cadence"
    )
