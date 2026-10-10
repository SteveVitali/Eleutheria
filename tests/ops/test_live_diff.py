# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1a live-diff (SIG-OPS-005 / SIG-SEC-008, ADR-174).

Everything here is deterministic: the "live" side is an injected
``LiveState``/fixture bundle, the declared side is a synthetic cadence document
(or the real ``ops/cadence.toml`` for the parse/lint contract tests), the
fetchers are injected fakes, and ``today`` is pinned — no socket, no gcloud,
no wall-clock-dependent assertion.
"""

from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

import pytest
from ops.scheduled import load_cadence

from ops import live_diff as L

REPO_ROOT = Path(__file__).resolve().parents[2]
CADENCE = REPO_ROOT / "ops" / "cadence.toml"
ROLL_RECORD = REPO_ROOT / "docs" / "build" / "reports" / "p31.7-hosted" / "roll_record.json"

PROJECT = "test-proj"
REGION = "us-central1"
FLEET_REF = f"{REGION}-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:{'a' * 64}"
PINNED_REF = f"{REGION}-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:{'b' * 64}"

MINIMAL_CADENCE = """\
[probes]
job = "sig-probe"
scheduler = "sig-sched-probe"
schedule = "0 */6 * * *"
gcs_prefix = "ops/probes"

[runs]
gcs_prefix = "ops/runs"

[[sources]]
id = "demo_src"
cadence = "weekly"
cron = "30 4 * * 2"
job = "sig-ingest-demo-src"
scheduler = "sig-sched-demo-src"

[[maintenance]]
id = "pg-logical-export"
cadence = "monthly"
cron = "0 12 1 * *"
scheduler = "sig-sched-pg-logical-export"
state = "paused"
procedure = "ops/gcp/logical-export.sh --apply export --go <verbatim in-ticket go>"

[[manual_jobs]]
job = "sig-export"
sa_class = "export"
secrets = { SIG_PG_PASSWORD = "sig-pg-password" }

[[pins]]
job = "sig-ingest-pinned"
image = "{ar_host}/{project}/sig/sig-api@sha256:%s"
reason = "test pin"
expiry = "2999-01-01"

[fleet]
image_repo = "{ar_host}/{project}/sig/sig-api"
roll_record = "roll.json"

[live_diff]
scheduler = "sig-sched-live-diff"
cron = "30 11 * * *"
job = "sig-probe"
args = '["-c","exec sig-ops live-diff --live --alert"]'

[[buckets]]
suffix = "sig-public"
public = true
ubla = true
versioning = true
noncurrent_days = 30
""" % ("b" * 64)


def _cadence(tmp_path: Path):
    """Parse the synthetic cadence and write the roll record it names."""
    (tmp_path / "roll.json").write_text(json.dumps({"image_digest": FLEET_REF, "jobs": []}))
    cadence_path = tmp_path / "cadence.toml"
    cadence_path.write_text(MINIMAL_CADENCE)
    return load_cadence(cadence_path), tmp_path


def _v1_job(image: str, sa: str = "sig-ingest-rt@test.iam.gserviceaccount.com", secrets=()):
    """A gcloud-v1-shaped ``run jobs describe`` body."""
    env = [
        {
            "name": name,
            "valueFrom": {"secretKeyRef": {"name": sec, "key": "latest"}},
        }
        for name, sec in secrets
    ]
    return {
        "spec": {
            "template": {
                "spec": {
                    "template": {
                        "spec": {
                            "serviceAccountName": sa,
                            "containers": [{"image": image, "env": env}],
                        }
                    }
                }
            }
        }
    }


def _sched_body(name: str, schedule: str, job: str, *, state="ENABLED", args=None):
    body = {}
    if args is not None:
        body = base64.b64encode(
            json.dumps({"overrides": {"containerOverrides": [{"args": args}]}}).encode()
        ).decode()
    return {
        "name": f"projects/{PROJECT}/locations/{REGION}/jobs/{name}",
        "schedule": schedule,
        "state": state,
        "httpTarget": {
            "uri": f"https://{REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{PROJECT}/jobs/{job}:run",
            "httpMethod": "POST",
            "body": body,
        },
    }


def _declared(tmp_path: Path):
    cadence, root = _cadence(tmp_path)
    fleet = L.read_roll_record(root / cadence.fleet.roll_record)
    return cadence, L.declared_fleet(cadence, fleet, project=PROJECT, region=REGION)


def _healthy_state(declared: L.DeclaredFleet) -> L.LiveState:
    """A live state that matches the declared side exactly."""
    state = L.LiveState()
    for t in declared.triggers:
        args = json.loads(t.args) if t.args else None
        state.schedulers[t.name] = _sched_body(
            t.name,
            t.cron,
            t.job,
            state="PAUSED" if t.paused else "ENABLED",
            args=args,
        )
    for j in declared.jobs:
        secrets = [tuple(s.split("=", 1)) for s in j.secrets]
        state.jobs[j.name] = _v1_job(j.image, secrets=secrets)
    for svc in declared.services:
        state.services[svc] = _v1_job(FLEET_REF)
    state.buckets[f"{PROJECT}-sig-public"] = {
        "iam": {"bindings": [{"role": "roles/storage.objectViewer", "members": ["allUsers"]}]},
        "info": {
            "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": True}},
            "versioning": {"enabled": True},
            "lifecycle": {
                "rule": [
                    {
                        "action": {"type": "Delete"},
                        "condition": {"daysSinceNoncurrentTime": 30},
                    }
                ]
            },
        },
    }
    return state


# --- cron lint ---------------------------------------------------------------


def test_cron_lint_rejects_dom_and_dow_restricted():
    problems = L.cron_lint("0 5 3 * 2", annotated="", owner="sources.x")
    assert problems and "OR-fires" in problems[0]


def test_cron_lint_accepts_annotated_with_owner():
    # The annotation value names the recorded exception's owner.
    problems = L.cron_lint("0 5 3 * 2", annotated="P35.1b", owner="sources.x")
    assert problems == []


def test_cron_lint_normal_specs_clean():
    assert L.cron_lint("0 5 3 * *", annotated="", owner="x") == []
    assert L.cron_lint("0 5 * * 2", annotated="", owner="x") == []
    assert L.cron_lint("*/15 * * * *", annotated="", owner="x") == []
    assert L.cron_lint("0 5 1 * *", annotated="", owner="x") == []


def test_cron_lint_malformed_fails_closed():
    assert L.cron_lint("0 5 *", annotated="", owner="x")
    assert L.cron_lint("", annotated="", owner="x")


def test_real_cadence_lints_clean():
    """The committed cadence.toml carries only annotated/owner-named exceptions."""
    cadence = load_cadence(CADENCE)
    assert L.lint_cadence_crons(cadence) == []
    assert L.pin_lint(cadence) == []


def test_real_cadence_new_sections_parse():
    cadence = load_cadence(CADENCE)
    assert cadence.maintenance, "[[maintenance]] rows must parse"
    export = next(m for m in cadence.maintenance if m.id == "pg-logical-export")
    assert export.state == "paused" and export.scheduler
    assert {j.job for j in cadence.manual_jobs} == {
        "sig-export",
        "sig-materialize",
        "sig-replay-ingest",
    }
    assert cadence.live_diff is not None and cadence.live_diff.scheduler
    assert cadence.fleet.image_repo and cadence.fleet.roll_record
    assert cadence.buckets and all(b.suffix for b in cadence.buckets)


# --- pins --------------------------------------------------------------------


def test_pin_lint_requires_reason_expiry_digest():
    cadence, _ = _cadence_from_text(
        """
        [[pins]]
        job = "sig-x"
        image = "repo/x@sha256:%s"
        """
        % ("c" * 64)
    )
    problems = L.pin_lint(cadence)
    assert any("reason" in p for p in problems)
    assert any("expiry" in p for p in problems)


def test_expired_pin_is_drift():
    cadence, _ = _cadence_from_text(
        """
        [[pins]]
        job = "sig-x"
        image = "repo/x@sha256:%s"
        reason = "held"
        expiry = "2000-01-01"
        """
        % ("c" * 64)
    )
    assert L.expired_pin_names(cadence, today=date(2026, 10, 10)) == ["sig-x"]
    assert L.expired_pin_names(cadence, today=date(1999, 1, 1)) == []


def _cadence_from_text(text: str):
    """Parse a cadence document given as TOML text (test helper)."""
    import tomllib

    from ops.scheduled import parse_cadence_doc

    return parse_cadence_doc(tomllib.loads(text)), None


# --- normalisers -------------------------------------------------------------


def test_live_scheduler_fields_parses_job_and_args():
    body = _sched_body("sig-sched-x", "0 5 * * *", "sig-ingest-x", args=["-c", "exec y"])
    fields = L.live_scheduler_fields(body)
    assert fields["schedule"] == "0 5 * * *"
    assert fields["job"] == "sig-ingest-x"
    assert fields["state"] == "ENABLED"
    assert json.loads(fields["args"]) == ["-c", "exec y"]


def test_live_image_and_sa_v1_and_v2():
    v1 = _v1_job(FLEET_REF, sa="sa@x", secrets=[("SIG_PG_PASSWORD", "sig-pg-password")])
    assert L.live_image(v1) == FLEET_REF
    assert L.live_service_account(v1) == "sa@x"
    assert L.live_secret_names(v1) == {"sig-pg-password"}
    v2 = {
        "name": f"projects/p/locations/{REGION}/jobs/j1",
        "template": {
            "template": {
                "serviceAccount": "sa2@x",
                "containers": [{"image": "img@sha256:" + "d" * 64}],
            }
        },
    }
    assert L.live_service_account(v2) == "sa2@x"
    assert L.live_image(v2).endswith("d" * 64)


# --- state fixture loading ----------------------------------------------------


def test_load_state_source_file_and_dir(tmp_path: Path):
    bundle = {
        "schedulers": {"t1": {"name": "t1", "schedule": "0 1 * * *"}},
        "jobs": [{"metadata": {"name": "j1"}}],
        "errors": [],
    }
    f = tmp_path / "state.json"
    f.write_text(json.dumps(bundle))
    st = L.load_state_source(str(f))
    assert st.schedulers["t1"]["schedule"] == "0 1 * * *"
    assert "j1" in st.jobs
    d = tmp_path / "statedir"
    d.mkdir()
    (d / "jobs.json").write_text(json.dumps({"j2": {"x": 1}}))
    st2 = L.load_state_source(str(d))
    assert "j2" in st2.jobs and not st2.schedulers
    with pytest.raises(L.LiveDiffError):
        L.load_state_source(str(tmp_path / "absent.json"))


# --- the diff engine ----------------------------------------------------------


def test_diff_clean_state_reports_nothing(tmp_path: Path):
    _, declared = _declared(tmp_path)
    report = L.diff(declared, _healthy_state(declared))
    assert not report.drift, report.text()
    assert report.checked_triggers == len(declared.triggers)
    assert report.checked_jobs == len(declared.jobs)


def test_diff_missing_and_extra_triggers(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    del state.schedulers["sig-sched-demo-src"]
    state.schedulers["sig-sched-rogue"] = _sched_body(
        "sig-sched-rogue", "0 0 * * *", "sig-ingest-demo-src"
    )
    report = L.diff(declared, state)
    text = report.text()
    assert "schedule sig-sched-demo-src: missing live" in text
    assert "schedule sig-sched-rogue: live trigger not declared" in text


def test_diff_cron_mismatch(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    state.schedulers["sig-sched-demo-src"]["schedule"] = "0 9 * * *"
    report = L.diff(declared, state)
    assert any(
        f.cls == "schedule" and f.name == "sig-sched-demo-src" and "cron" in f.detail
        for f in report.findings
    )


def test_diff_enabled_maintenance_trigger_is_drift(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    state.schedulers["sig-sched-pg-logical-export"]["state"] = "ENABLED"
    report = L.diff(declared, state)
    assert any(
        f.cls == "schedule" and f.name == "sig-sched-pg-logical-export" and "ENABLED" in f.detail
        for f in report.findings
    )


def test_diff_paused_cadence_trigger_is_drift(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    state.schedulers["sig-sched-demo-src"]["state"] = "PAUSED"
    report = L.diff(declared, state)
    assert any(
        f.cls == "schedule" and "PAUSED live but declared enabled" in f.detail
        for f in report.findings
    )


def test_diff_tag_image_and_digest_mismatch(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    state.jobs["sig-ingest-demo-src"] = _v1_job(
        f"{REGION}-docker.pkg.dev/{PROJECT}/sig/sig-api:latest"
    )
    state.jobs["sig-probe"] = _v1_job(
        f"{REGION}-docker.pkg.dev/{PROJECT}/sig/sig-api@sha256:{'9' * 64}"
    )
    report = L.diff(declared, state)
    assert any(
        f.cls == "image" and f.name == "sig-ingest-demo-src" and "digest-pinned" in f.detail
        for f in report.findings
    )
    assert any(
        f.cls == "image" and f.name == "sig-probe" and "!=" in f.detail for f in report.findings
    )


def test_diff_unlisted_and_manual_jobs(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    state.jobs["sig-cruft-job"] = _v1_job(FLEET_REF)
    report = L.diff(declared, state)
    assert any(
        f.cls == "job_config" and f.name == "sig-cruft-job" and "manual_jobs" in f.detail
        for f in report.findings
    )
    # The declared manual job carries no trigger and that is NOT drift.
    assert not any(f.name == "sig-export" for f in report.findings)


def test_diff_missing_secret_binding(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    state.jobs["sig-export"] = _v1_job(PINNED_REF)  # secrets stripped
    report = L.diff(declared, state)
    assert any(
        f.cls == "secrets" and f.name == "sig-export" and "sig-pg-password" in f.detail
        for f in report.findings
    )


def test_diff_bucket_posture(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    entry = state.buckets[f"{PROJECT}-sig-public"]
    entry["iam"]["bindings"] = []  # allUsers removed → declared public fails
    entry["info"]["versioning"]["enabled"] = False
    report = L.diff(declared, state)
    classes = {(f.cls, f.name) for f in report.findings}
    assert ("public_posture", f"{PROJECT}-sig-public") in classes
    assert ("versioning", f"{PROJECT}-sig-public") in classes


def test_diff_expired_pin_reported(tmp_path: Path):
    _, declared = _declared(tmp_path)
    report = L.diff(declared, _healthy_state(declared), expired_pins=["sig-ingest-pinned"])
    assert any("expiry passed" in f.detail for f in report.findings)


def test_diff_report_is_deterministic(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    del state.schedulers["sig-sched-probe"]
    state.jobs["zz-cruft"] = _v1_job("img")
    r1, r2 = L.diff(declared, state), L.diff(declared, state)
    assert r1.text() == r2.text()
    # class order follows DRIFT_CLASSES, names sorted inside a leg
    assert r1.ordered()[0].cls == "schedule"


# --- execute() + the run record ------------------------------------------------


def test_execute_from_state_writes_run_row(tmp_path: Path):
    cadence, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    bundle = {
        "schedulers": state.schedulers,
        "jobs": state.jobs,
        "services": state.services,
        "buckets": state.buckets,
    }
    sf = tmp_path / "live.json"
    sf.write_text(json.dumps(bundle))
    # repo_root doubles as the roll-record + cadence home
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "cadence.toml").write_text(MINIMAL_CADENCE)
    row, code = L.execute(
        mode="from-state",
        cadence_file=str(tmp_path / "cadence.toml"),
        state_source=str(sf),
        project=PROJECT,
        region=REGION,
        repo_root=tmp_path,
        today=date(2026, 10, 10),
    )
    assert code == 0
    rec = row.as_json()
    assert rec["kind"] == "live-diff" and rec["outcome"] == "ok"
    fr = rec["fetch_record"]
    assert fr["schema"] == L.SCHEMA and fr["mode"] == "from-state"
    assert fr["triggers_checked"] == len(declared.triggers)


def test_execute_from_state_drift_exit_1(tmp_path: Path):
    _, declared = _declared(tmp_path)
    state = _healthy_state(declared)
    del state.jobs["sig-export"]
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "cadence.toml").write_text(MINIMAL_CADENCE)
    sf = tmp_path / "live.json"
    sf.write_text(
        json.dumps(
            {
                "jobs": state.jobs,
                "schedulers": state.schedulers,
                "services": state.services,
                "buckets": state.buckets,
            }
        )
    )
    row, code = L.execute(
        mode="from-state",
        cadence_file=str(tmp_path / "cadence.toml"),
        state_source=str(sf),
        project=PROJECT,
        repo_root=tmp_path,
    )
    assert code == 1 and row.as_json()["outcome"] == "drift"


def test_execute_fails_closed_on_bad_cadence(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text(
        '[[sources]]\nid = "x"\ncron = "0 5 3 * 2"\njob = "j"\nscheduler = "s"\ncadence = "w"\n'
    )
    with pytest.raises(L.LiveDiffError):
        L.execute(
            mode="from-state",
            cadence_file=str(bad),
            state_source=str(tmp_path),
            project=PROJECT,
            repo_root=tmp_path,
        )


def test_execute_fails_closed_without_state_source(tmp_path: Path):
    cadence, _ = _cadence(tmp_path)
    with pytest.raises(L.LiveDiffError):
        L.execute(
            mode="from-state",
            cadence_file=str(tmp_path / "cadence.toml"),
            project=PROJECT,
            repo_root=tmp_path,
        )


def test_execute_missing_project_fails(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SIG_GCP_PROJECT", raising=False)
    with pytest.raises(L.LiveDiffError):
        L.execute(mode="from-state", cadence_file=str(tmp_path), project=None)


def test_declared_bundle_round_trip(tmp_path: Path):
    """The published bundle (emit → load) carries cadence + fleet — the
    no-image-roll config path (SIG-OPS-005)."""
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "cadence.toml").write_text(MINIMAL_CADENCE)
    (tmp_path / "roll.json").write_text(json.dumps({"image_digest": FLEET_REF, "jobs": []}))
    cadence = load_cadence(tmp_path / "ops" / "cadence.toml")
    bundle = L.build_declared_bundle(cadence, repo_root=tmp_path)
    bf = tmp_path / "bundle.json"
    bf.write_text(json.dumps(bundle))
    declared = L.load_declared(declared_source=str(bf))
    assert declared.cadence.probe_job == "sig-probe"
    assert declared.fleet.fleet_ref == FLEET_REF
    assert declared.cadence_sha256


def test_upload_run_row_local(tmp_path: Path):
    from ops.scheduled import RunRow

    row = RunRow(
        kind="live-diff",
        source="_live-diff",
        mode="from-state",
        outcome="ok",
        exit_code=0,
        started_at="2026-10-10T11:30:00+00:00",
        duration_seconds=0.1,
    )
    cadence, _ = _cadence(tmp_path)
    written = L.upload_run_row(row, cadence, local_dir=tmp_path / "runs")
    assert written["local"].endswith(".json")
    body = json.loads(Path(written["local"]).read_text())
    assert body["source"] == "_live-diff"


# --- the real roll record -----------------------------------------------------


def test_roll_record_parses():
    fleet = L.read_roll_record(ROLL_RECORD)
    assert fleet.fleet_ref.endswith("@sha256:" + fleet.fleet_ref.split("sha256:")[-1])
    assert "@sha256:" in fleet.fleet_ref
    assert fleet.jobs, "the committed record names per-job after_digests"
