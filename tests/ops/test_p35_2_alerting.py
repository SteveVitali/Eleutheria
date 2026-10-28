# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.2 alerting as code + probe targets out of the image + escalation.

Covers the ticket's deterministic deliverables (SIG-OPS-006/007, G1 §3.5):

* **policy text renders the declared resources** — every alert-policy def
  carries ``alertStrategy.notificationRateLimit = 86400s`` (the >24 h daily
  re-notify, D-P34.4-3's hygiene leg) and binds the operator e-mail channel;
  the uptime defs declare 3 regions + the site content match.
* **the re-notify rule computes once-daily** — ``ops.alerting.renotify_due``.
* **the SLO readout** — ``slo_report`` over stored sweep rows: met/missed/
  no-data verdicts, error-budget math, SIG-ENG-042 gate (never a green on
  nothing).
* **uptime flag render** — the committed defs render the ``gcloud monitoring
  uptime`` argv the roll applies (``monitoring-defs render-uptime``).
* **probe targets out of the image** — ``load_cadence_external`` prefers the
  declaration bundle (``SIG_OPS_DECLARED_GCS``) over the baked file, never a
  silent fall-back on a bad bundle.
* **the roll runner** (``ops/gcp/alerting.sh``) — check-mode plan, the
  03:00–06:30Z + AR-3 window guard, the stubbed apply's mutation allowlist
  (the named set only), pre-state captures, the channel gate, post-apply
  verify convergence.
* **a no-op measurement makes the workflow red** — the counts/gate
  machinery ``observability.yml`` runs (``sig-ops observe-gate``) plus the
  workflow's own wiring.

``--apply`` never touches production in tests: the shared stub gcloud/uv
binaries (``tests/ops/fixtures/alerts/stubs``) record invocations and serve
canned state.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "alerting.sh"
DEFS_DIR = REPO_ROOT / "ops" / "monitoring"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "observability.yml"
FIXTURES = Path(__file__).parent / "fixtures" / "alerts"
STUBS = FIXTURES / "stubs"
LIVE_POST = FIXTURES / "live-post"

sys.path.insert(0, str(REPO_ROOT / "ops" / "src"))
from ops.scheduled import (  # noqa: E402
    CadenceError,
    load_cadence_external,
)

from ops import alerting as al  # noqa: E402
from ops import cli as ops_cli  # noqa: E402
from ops import monitoring_defs as md  # noqa: E402

INSIDE_FREEZE = "2026-10-26T04:00:00Z"  # 03:00–06:30Z daily AR-3 freeze
INSIDE_FREEZE_LATE = "2026-10-26T06:15:00Z"
OPEN_WINDOW = "2026-10-26T15:00:00Z"  # future-ok: synthetic: fixture instant outside the windows
INSIDE_AR3 = "2026-10-08T12:00:00Z"  # AR-3 batch window — future-ok: scheduled: AR-3 window

PROJECT = "sig-fixture-project"  # a fixture id — the real id is never committed (OP-07)
STALE_IMAGE = f"us-central1-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:" + "b" * 64
ALERTS_IMAGE = f"us-central1-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:" + "c" * 64
JOBFAIL_ID = "7285515107319155929"
DECLARED_URI = f"gs://{PROJECT}-sig-restricted/ops/declared/live-diff.json"


def _defs() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(DEFS_DIR.glob("*.json"))}


def _live_post() -> dict[str, list]:
    return md.load_live_dir(LIVE_POST)


# --- committed definitions ----------------------------------------------------


def test_every_policy_def_renotifies_once_daily() -> None:
    """D-P34.4-3's hygiene leg: notificationRateLimit = 86400s on every policy."""
    for slug, doc in _defs().items():
        if doc["_sig"]["kind"] != "policy":
            continue
        strategy = doc.get("alertStrategy") or {}
        assert strategy.get("notificationRateLimit", {}).get("period") == "86400s", (
            f"{slug}: every red condition re-notifies once daily (SIG-OPS-006)"
        )


def test_every_policy_def_binds_the_operator_channel() -> None:
    for slug, doc in _defs().items():
        if doc["_sig"]["kind"] != "policy":
            continue
        channels = doc.get("notificationChannels") or []
        assert channels, f"{slug}: no notification channel bound"
        assert all("notificationChannels/" in c for c in channels), slug


def test_uptime_defs_declare_three_regions_and_site_content_match() -> None:
    site = _defs()["uptime-check.site"]
    api = _defs()["uptime-check.api"]
    assert site["_sig"]["apply"] == "update"
    assert api["_sig"]["apply"] == "update"
    for slug, doc in (("site", site), ("api", api)):
        assert len(doc["selectedRegions"]) == 3, slug
        assert doc["period"] == "300s", slug  # 5-minute cadence
        assert doc["httpCheck"]["useSsl"] is True, slug
    matchers = site["httpCheck"]["contentMatchers"]
    assert matchers and matchers[0]["matcher"] == "CONTAINS_STRING"
    assert matchers[0]["content"] == "Surveillance Infrastructure Graph"


def test_channel_stays_diff_only_p34_4s_mechanism() -> None:
    channel = _defs()["channel.operator-email"]
    assert channel["_sig"]["apply"] == "diff-only"
    assert channel["enabled"] is True


def test_tls_policy_still_fires_21_days_before_expiry() -> None:
    doc = _defs()["alert-policy.tls-cert-expiry"]
    cond = doc["conditions"][0]["conditionThreshold"]
    assert cond["thresholdValue"] == 21.0
    assert "time_until_ssl_cert_expires" in cond["filter"]


def test_defs_have_no_literal_project_or_email() -> None:
    for path in sorted(DEFS_DIR.glob("*.json")):
        text = path.read_text()
        doc = json.loads(text)
        assert "eleutheria" not in json.dumps({k: v for k, v in doc.items() if k != "_sig"}), (
            f"{path.name}: the real project id is never committed"
        )
        assert "@" not in text, f"{path.name}: an address literal is never committed"


# --- the re-notify rule --------------------------------------------------------


def _dt(hours: float) -> datetime:
    return datetime(2026, 10, 26, 0, 0, tzinfo=UTC) + timedelta(hours=hours)


def test_renotify_due_computes_once_daily() -> None:
    opened = _dt(0)
    # Fresh condition: no re-notify inside the first 24 h.
    assert al.renotify_due(opened, opened, _dt(23)) is False
    # Red > 24 h, never re-notified since the open: due.
    assert al.renotify_due(opened, opened, _dt(30)) is True
    # Red > 24 h, notified 25 h ago: due again (once daily).
    assert al.renotify_due(opened, _dt(2), _dt(27)) is True
    # Red > 24 h, notified 2 h ago: NOT due — once daily, not every sweep.
    assert al.renotify_due(opened, _dt(25), _dt(27)) is False
    # Red > 24 h, never notified at all: due.
    assert al.renotify_due(opened, None, _dt(30)) is True
    # Boundary: exactly the period counts as due.
    assert al.renotify_due(opened, opened, _dt(48)) is True


# --- the measured-nothing gate (SIG-ENG-042) ------------------------------------


def test_measured_gate_fails_on_zero_evaluated() -> None:
    ok, report = al.measured_gate({"egress_offered": 1, "probe_offered": 1})
    assert ok is False
    assert "offered=2 evaluated=0" in report
    assert "SIG-ENG-042" in report


def test_measured_gate_fails_when_nothing_offered() -> None:
    ok, _ = al.measured_gate({})
    assert ok is False


def test_measured_gate_passes_when_anything_evaluated() -> None:
    ok, report = al.measured_gate({"egress_offered": 1, "egress_evaluated": 1, "probe_offered": 1})
    assert ok is True
    assert "offered=2 evaluated=1" in report


def test_parse_measured_counts_ignores_junk() -> None:
    counts = al.parse_measured_counts("probe_offered=1\njunk\nx_offered=2\n")
    assert counts == {"probe_offered": 1, "x_offered": 2}


def test_observe_gate_verb_exit_codes(tmp_path: Path) -> None:
    counts = tmp_path / "counts"
    counts.write_text("egress_offered=1\nprobe_offered=1\n")
    assert ops_cli.main(["observe-gate", "--counts", str(counts)]) == 1
    counts.write_text("egress_offered=1\negress_evaluated=1\n")
    assert ops_cli.main(["observe-gate", "--counts", str(counts)]) == 0
    assert ops_cli.main(["observe-gate", "--counts", str(tmp_path / "nope")]) == 1


# --- the SLO readout ------------------------------------------------------------


def _rows(pairs: list[tuple[str, bool, str]]) -> list[dict]:
    return [
        {"service": s, "ok": ok, "latency_ms": 42.0, "ts": ts, "detail": ""} for s, ok, ts in pairs
    ]


def test_slo_report_met_missed_nodata() -> None:
    rows = _rows(
        [
            ("sig-web-root", True, "2026-10-05T00:00:00Z"),
            ("sig-web-root", True, "2026-10-05T06:00:00Z"),
            ("sig-web-root", False, "2026-10-05T12:00:00Z"),
            ("sig-api-health", False, "2026-10-05T00:00:00Z"),
            ("sig-web-root", True, "2026-09-05T00:00:00Z"),  # out of window
        ]
    )
    report = al.slo_report(rows, month="2026-10")
    by_name = {r.name: r for r in report.results}
    # site: 2/3 ok = 66.7% < 99.5 → missed
    assert by_name["site-root"].status == "missed"
    assert by_name["site-root"].probes == 3
    # api: 0/1 → missed
    assert by_name["api-health"].status == "missed"
    assert report.gate_ok is True


def test_slo_report_met_when_inside_budget() -> None:
    rows = _rows(
        [("sig-web-root", True, f"2026-10-{d:02d}T00:00:00Z") for d in range(1, 30)]
        + [("sig-api-health", True, "2026-10-05T00:00:00Z")]
    )
    report = al.slo_report(rows, month="2026-10")
    assert all(r.status == "met" for r in report.results)
    assert all(r.budget_consumed_pct == 0.0 for r in report.results)


def test_slo_report_no_rows_is_nodata_never_fabricated() -> None:
    report = al.slo_report([], month="2026-10")
    assert report.gate_ok is False
    assert all(r.status == "no-data" and r.uptime_pct is None for r in report.results)


def test_render_slo_readout_reports_offered_and_evaluated() -> None:
    report = al.slo_report([], month="2026-10")
    text = al.render_slo_readout(report)
    assert "SIG-OPS-007" in text
    assert "offered=2 evaluated=0" in text
    assert "no-data" in text


def test_slo_readout_verb_writes_the_readout(tmp_path: Path) -> None:
    log = tmp_path / "probes.jsonl"
    log.write_text(
        "".join(
            json.dumps(r) + "\n"
            for r in _rows(
                [
                    ("sig-web-root", True, "2026-10-05T00:00:00Z"),
                    ("sig-api-health", True, "2026-10-05T00:00:00Z"),
                ]
            )
        )
    )
    out = tmp_path / "slo.md"
    rc = ops_cli.main(["slo-readout", "--month", "2026-10", "--local", str(log), "--out", str(out)])
    assert rc == 0
    assert "met" in out.read_text()


def test_slo_readout_verb_fails_when_it_measured_nothing(tmp_path: Path) -> None:
    log = tmp_path / "empty.jsonl"
    log.write_text("")
    out = tmp_path / "slo.md"
    rc = ops_cli.main(["slo-readout", "--month", "2026-10", "--local", str(log), "--out", str(out)])
    assert rc == 3  # measured nothing → fail (SIG-ENG-042); readout still recorded
    assert out.exists()


# --- uptime flag render ---------------------------------------------------------


def test_uptime_update_render_from_committed_defs() -> None:
    site = _defs()["uptime-check.site"]
    body = {k: v for k, v in site.items() if k != "_sig"}
    argv = al.uptime_update_args(body, "sig-site-check-id", PROJECT)
    assert argv[:2] == ["update", "sig-site-check-id"]
    joined = " ".join(argv)
    assert "--set-regions usa-iowa,europe,asia-pacific" in joined
    assert "--matcher-type contains-string" in joined
    assert "--matcher-content 'Surveillance Infrastructure Graph'" not in joined
    assert "Surveillance Infrastructure Graph" in joined
    assert "--period 300" in joined and "--timeout 10" in joined
    assert "--path /" in joined


def test_uptime_create_render_carries_host_and_protocol() -> None:
    api = _defs()["uptime-check.api"]
    body = {k: v for k, v in api.items() if k != "_sig"}
    argv = al.uptime_create_args(body, PROJECT)
    assert argv[0] == "create"
    joined = " ".join(argv)
    assert "--resource-type uptime-url" in joined
    assert "host=sig-api-e5ctyx36jq-uc.a.run.app" in joined
    assert "--protocol https" in joined


def test_render_uptime_verb_prints_argv_json(capsys) -> None:
    rc = ops_cli.main(
        [
            "monitoring-defs",
            "render-uptime",
            "--defs",
            str(DEFS_DIR),
            "--slug",
            "uptime-check.site",
            "--project",
            PROJECT,
            "--check-id",
            "sig-site-check-id",
        ]
    )
    assert rc == 0
    argv = json.loads(capsys.readouterr().out)
    assert argv[:2] == ["update", "sig-site-check-id"]


def test_render_uptime_verb_rejects_a_policy_slug(capsys) -> None:
    rc = ops_cli.main(
        [
            "monitoring-defs",
            "render-uptime",
            "--defs",
            str(DEFS_DIR),
            "--slug",
            "alert-policy.job-failures",
            "--project",
            PROJECT,
        ]
    )
    assert rc == 2


# --- probe targets out of the image (G1-02a) -------------------------------------


def _bundle_bytes(cadence_toml: str) -> bytes:
    return json.dumps({"cadence_toml": cadence_toml, "cadence_sha256": "0" * 64}).encode()


def test_load_cadence_external_prefers_the_declaration_bundle() -> None:
    cadence = load_cadence_external(
        env={"SIG_OPS_DECLARED_GCS": "mem://bundle"},
        read_bytes=lambda _src: (
            (REPO_ROOT / "ops" / "cadence.toml").read_bytes()
            and _bundle_bytes((REPO_ROOT / "ops" / "cadence.toml").read_text())
        ),
    )
    cfg, provenance = cadence
    assert provenance.startswith("mem://bundle#sha256:")
    assert cfg.probe_job == "sig-probe"


def test_load_cadence_external_falls_back_to_the_file() -> None:
    cfg, provenance = load_cadence_external(env={})
    assert provenance.startswith("file:")
    assert cfg.probe_job == "sig-probe"


def test_load_cadence_external_explicit_path_wins(tmp_path: Path) -> None:
    copied = tmp_path / "cadence.toml"
    copied.write_text((REPO_ROOT / "ops" / "cadence.toml").read_text())
    cfg, provenance = load_cadence_external(
        copied,
        env={"SIG_OPS_DECLARED_GCS": "mem://bundle"},
        read_bytes=lambda _s: _bundle_bytes("bad toml = ["),
    )
    assert provenance == f"file:{copied}"
    assert cfg.probe_job == "sig-probe"


def test_load_cadence_external_fails_closed_on_a_bad_bundle() -> None:
    with pytest.raises(CadenceError):
        load_cadence_external(
            env={"SIG_OPS_DECLARED_GCS": "mem://bundle"},
            read_bytes=lambda _s: b'{"no_cadence": true}',
        )
    with pytest.raises(CadenceError):
        load_cadence_external(
            env={"SIG_OPS_DECLARED_GCS": "mem://bundle"},
            read_bytes=lambda _s: _bundle_bytes("[probes\nbroken"),
        )


def test_probe_hosted_reads_the_bundle_cadence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """probe-hosted's cadence source line names the bundle when it wins."""
    bundle = tmp_path / "declared.json"
    bundle.write_text(
        json.dumps(
            {
                "cadence_toml": (REPO_ROOT / "ops" / "cadence.toml").read_text(),
                "cadence_sha256": "0" * 64,
            }
        )
    )
    monkeypatch.setenv("SIG_OPS_DECLARED_GCS", str(bundle))
    monkeypatch.setenv("SIG_PROBE_LOG", str(tmp_path / "probes.jsonl"))
    monkeypatch.setenv("SIG_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    # No endpoints resolve → every target skipped; the run still records its
    # provenance (the partial/skip posture is honest — never a green on nothing).
    rc = ops_cli.main(["probe-hosted", "--gcs-bucket", ""])
    out = capsys.readouterr().out
    assert "cadence source:" in out
    assert "declared.json#sha256:" in out
    assert rc in (0, 1)


# --- the workflow truth fix ------------------------------------------------------


def test_observability_workflow_counts_and_gates() -> None:
    text = WORKFLOW.read_text()
    # The counts legs record offered/evaluated…
    assert "egress_offered=1" in text
    assert "egress_evaluated=1" in text
    assert "probe_offered=1" in text
    assert "probe_evaluated=1" in text
    # …and the observe-gate step goes red on a nothing-measured run.
    assert "observe-gate --counts .observe/counts" in text
    assert "SIG-ENG-042" in text
    # The vacuous-green message no longer claims a plain skip.
    assert "probe skipped (offline posture; nothing measured)" not in text


def test_counts_parse_as_the_gate_consumes_them() -> None:
    # The exact lines the workflow appends parse and gate correctly.
    for line in (
        "egress_offered=1",
        "egress_evaluated=1",
        "probe_offered=1",
        "probe_evaluated=1",
    ):
        assert al.parse_measured_counts(line)


# --- the roll runner --------------------------------------------------------------


def _env(tmp_path: Path, state: dict | None = None, **over: str) -> tuple[dict, Path]:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True, parents=True)
    for name in ("gcloud", "curl"):
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
        CURL_STUB_LOG=str(tmp_path / "curl.log"),
        UV_STUB_LOG=str(tmp_path / "uv.log"),
        SIG_ALERTING_EVIDENCE_DIR=str(ev),
    )
    env.update(over)
    return env, ev


def _default_state() -> dict:
    """The pre-roll posture: P34.4's create-defs absent, no rate-limit on the
    Track-0.5 policies, no regions/content match, retention 30, no versioning."""
    live = _live_post()
    policies = [
        p
        for p in live["policies"]
        if "TLS certificate expiry" not in p.get("displayName", "")
        and "SIG-ALERT" not in p.get("displayName", "")
    ]
    for p in policies:
        if p.get("displayName") in (
            "SIG — Cloud SQL sig-pg disk utilization > 85%",
            "SIG site uptime check failing",
            "SIG API uptime check failing",
        ):
            (p.get("alertStrategy") or {}).pop("notificationRateLimit", None)
    uptime = []
    for u in live["uptime_checks"]:
        u = dict(u)
        u.pop("selectedRegions", None)
        hc = dict(u.get("httpCheck") or {})
        hc.pop("contentMatchers", None)
        u["httpCheck"] = hc
        uptime.append(u)
    return {
        "project": PROJECT,
        "channels": live["channels"],
        "uptime": uptime,
        "policies": policies,
        "probe_image": STALE_IMAGE,
        "probe_commit": "sha256:" + "b" * 64,
        "alerts_image": ALERTS_IMAGE,
        "job_env": {},
        "retention_days": 30,
        "versioning": False,
        "log_rows": [],
    }


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
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
    assert _gcloud_calls(tmp_path) == []


def test_plan_names_every_leg_and_rollback(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    proc = _run(["--check"], env)
    out = proc.stdout
    for leg in (
        "live-diff --emit-declared",
        "alert-policy.job-failures",
        "uptime-check.site",
        "retention-days=90",
        "--versioning",
        "roll-jobs --job sig-probe",
        "SIG_OPS_DECLARED_GCS",
    ):
        assert leg in out, leg
    assert out.count("rollback") >= 5


@pytest.mark.parametrize(
    "action",
    ["bundle", "policies", "uptime", "retention", "versioning", "proberoll", "all"],
)
def test_apply_refuses_inside_the_daily_freeze(tmp_path: Path, action: str) -> None:
    env, _ = _env(tmp_path, SIG_ALERTING_NOW=INSIDE_FREEZE)
    proc = _run(["--apply", action], env)
    assert proc.returncode == 42, proc.stdout + proc.stderr
    assert "03:00-06:30Z" in proc.stderr
    mutating = [
        line
        for line in _gcloud_calls(tmp_path)
        if any(w in line for w in ("create", "update", "delete", "submit", " cp "))
        and "describe" not in line
    ]
    assert mutating == [], mutating


@pytest.mark.parametrize(
    "action", ["bundle", "policies", "uptime", "retention", "versioning", "proberoll"]
)
def test_apply_refuses_inside_an_ar3_window(tmp_path: Path, action: str) -> None:
    env, _ = _env(tmp_path, SIG_ALERTING_NOW=INSIDE_AR3)
    proc = _run(["--apply", action], env)
    assert proc.returncode == 42
    assert "batch window" in proc.stderr


def test_freeze_edge_0615_refuses_0630_opens(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTING_NOW=INSIDE_FREEZE_LATE)
    assert _run(["--apply", "retention"], env).returncode == 42
    env2, _ = _env(tmp_path / "b", SIG_ALERTING_NOW="2026-10-26T06:31:00Z")
    assert _run(["--apply", "retention"], env2).returncode == 0


def test_prestate_runs_inside_the_freeze_read_only(tmp_path: Path) -> None:
    env, ev = _env(tmp_path, SIG_ALERTING_NOW=INSIDE_FREEZE)
    proc = _run(["--apply", "prestate"], env)
    assert proc.returncode == 0, proc.stderr
    pre = list(ev.glob("pre-*"))
    assert pre and (pre[0] / "sha256s.txt").exists()
    assert (pre[0] / "log-retention.json").exists()
    assert (pre[0] / "restricted-bucket.json").exists()
    assert (pre[0] / "sig-alerts.service.json").exists()
    assert not any(
        w in line
        for line in _gcloud_calls(tmp_path)
        for w in ("create", "update", "delete", "submit", " cp ")
        if "describe" not in line
    )


def test_apply_all_runs_only_the_named_mutations(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTING_NOW=OPEN_WINDOW)
    proc = _run(["--apply", "all"], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _gcloud_calls(tmp_path)
    allowed = (
        "gcloud auth application-default print-access-token",
        "gcloud beta monitoring channels list",
        "gcloud monitoring uptime list-configs",
        "gcloud monitoring uptime describe",
        "gcloud monitoring uptime update",
        "gcloud monitoring uptime create",
        "gcloud alpha monitoring policies list",
        "gcloud alpha monitoring policies describe",
        "gcloud alpha monitoring policies create",
        "gcloud alpha monitoring policies update",
        "gcloud logging buckets describe",
        "gcloud logging buckets update",
        "gcloud storage buckets describe",
        "gcloud storage buckets update",
        "gcloud storage cp",
        "gcloud run jobs describe",
        "gcloud run jobs update",
        "gcloud run services describe",
        "gcloud compute ssl-certificates describe",
        "gcloud builds submit",
        "gcloud artifacts docker images describe",
    )
    assert calls, "the stub saw no gcloud calls"
    for line in calls:
        assert line.startswith(allowed), f"unauthorized gcloud call: {line}"
    # Exactly the authorized writes:
    assert sum("policies create" in line for line in calls) == 2  # the two create-defs
    assert sum("policies update" in line for line in calls) == 4  # the update-defs
    assert sum("monitoring uptime update" in line for line in calls) == 2
    assert sum("logging buckets update" in line for line in calls) == 1
    assert sum("buckets update" in line for line in calls if "storage" in line) == 1
    assert sum("builds submit" in line for line in calls) == 1
    # The declaration bundle published + the env asserted + the pinned roll.
    uv = (tmp_path / "uv.log").read_text()
    assert "live-diff --emit-declared" in uv
    assert "roll-jobs --job sig-probe --image" in uv
    assert "@sha256:" in uv and ":latest" not in uv
    assert "render-uptime" in uv and "--slug uptime-check.site" in uv
    # Post-state verify converged.
    assert "result=ok" in proc.stdout
    assert "DRIFT" not in proc.stdout


def test_policies_leg_refuses_without_the_channel(tmp_path: Path) -> None:
    state = _default_state()
    state["channels"] = []
    env, _ = _env(tmp_path, state=state, SIG_ALERTING_NOW=OPEN_WINDOW)
    proc = _run(["--apply", "policies"], env)
    assert proc.returncode == 42
    assert "P34.4" in proc.stderr
    assert not any("policies update" in line for line in _gcloud_calls(tmp_path))


def test_apply_is_idempotent_reconcile(tmp_path: Path) -> None:
    """A resumed run converges declared posture — never re-creates (OM-19)."""
    env, _ = _env(tmp_path, SIG_ALERTING_NOW=OPEN_WINDOW)
    assert _run(["--apply", "all"], env).returncode == 0
    calls_before = len(_gcloud_calls(tmp_path))
    proc = _run(["--apply", "all"], env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = _gcloud_calls(tmp_path)[calls_before:]
    # Re-run: creates become updates in place; retention/versioning skip.
    assert sum("policies create" in line for line in calls) == 0
    assert "SKIP retention" in proc.stdout
    assert "SKIP versioning" in proc.stdout


def test_verify_converges_post_apply(tmp_path: Path) -> None:
    env, _ = _env(tmp_path, SIG_ALERTING_NOW=OPEN_WINDOW)
    proc = _run(["--verify"], env)
    assert proc.returncode == 1  # the pre-roll state drifts
    assert _run(["--apply", "all"], env).returncode == 0
    proc = _run(["--verify"], env)
    assert proc.returncode == 0, proc.stdout
    assert "9 OK" in proc.stdout
    assert "OK retention/_Default" in proc.stdout
    assert "OK bucket/" in proc.stdout
    assert "OK job/sig-probe" in proc.stdout
    assert "OK service/sig-alerts" in proc.stdout


def test_verify_flags_a_latest_tagged_sig_alerts(tmp_path: Path) -> None:
    state = _default_state()
    state["alerts_image"] = f"us-central1-docker.pkg.dev/{PROJECT}/sig/sig-api:latest"
    env, _ = _env(tmp_path, state=state, SIG_ALERTING_NOW=OPEN_WINDOW)
    proc = _run(["--apply", "all"], env)
    # The roll lands its mutations but the post-state verify stays red —
    # sig-alerts' :latest is G1 §3.3's finding made visible (P35.1b owns the
    # service; this row's posture check names it, never silently rolls it).
    assert proc.returncode == 1
    assert "DRIFT service/sig-alerts" in proc.stdout
    proc = _run(["--verify"], env)
    assert proc.returncode == 1
    assert "DRIFT service/sig-alerts" in proc.stdout
    assert ":latest" in proc.stdout


def test_verify_from_state_green_on_the_post_fixture(tmp_path: Path) -> None:
    env, _ = _env(tmp_path)
    proc = _run(["--verify", "--from-state", str(LIVE_POST)], env)
    # The posture rows are absent from the old fixture → the defs pass but the
    # posture files don't exist (SKIPs, not DRIFTs) → defs-only verdict.
    assert proc.returncode == 0
    assert "9 OK" in proc.stdout


# --- cadence sanity --------------------------------------------------------------


def test_probe_cadence_stays_the_declared_source() -> None:
    import tomllib

    cadence = tomllib.loads((REPO_ROOT / "ops" / "cadence.toml").read_text())
    probes = cadence["probes"]
    assert probes["job"] == "sig-probe"
    names = {t["name"] for t in probes["targets"]}
    # The SLO objectives' surfaces stay declared probe targets.
    assert {"sig-web-root", "sig-api-health"} <= names
