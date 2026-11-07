# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.15 — the scheduled fixture-replay parser canary (BL-025 canary part).

The acceptance shape: **a mutated fixture raises the drift issue class**
(``parser_drift``) — a regression fails loud, never silently. Also pinned:
the committed spec validates, every declared family replays clean on the
sealed corpus, the OM-19 window guard suppresses and still records, the
declaration renders the whole mutation set, and the job script's ``--check``
plan stays ADC-free.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ops import parser_canary, parser_canary_job, probe_run

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "tests" / "parser_canary"
SPEC = CORPUS / "spec.toml"
DECLARATION = REPO_ROOT / "ops" / "parser_canary.toml"
SCRIPT = REPO_ROOT / "ops" / "gcp" / "parser-canary.sh"


def _spec() -> parser_canary.CanarySpec:
    return parser_canary.load_spec(SPEC)


def _corpus_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "corpus_copy"
    shutil.copytree(CORPUS, dst)
    return dst


# --- the spec (sig.parser-canary-spec/1) -------------------------------------


def test_committed_spec_validates() -> None:
    spec = _spec()
    assert spec.issue_classes >= {"parser_drift", "canary_error"}
    ids = [f.family_id for f in spec.families]
    assert len(ids) == len(set(ids))
    # Every declared fixture exists under the corpus — the check verb's contract.
    for f in spec.families:
        assert (CORPUS / f.fixture).is_file(), f"{f.family_id}: {f.fixture} missing"


def test_spec_covers_every_canary_findings_module() -> None:
    """Every connectors module shipping a SIG-PARSE-008 canary_findings core is
    a declared family — a parser family without a canary row is the gap the
    ticket exists to close."""
    spec = _spec()
    modules = {f.module for f in spec.families if f.kind == "module"}
    assert modules == {
        "connectors.osm",
        "connectors.atlas",
        "connectors.accountability",
        "connectors.audit_structural",
        "connectors.dot_511",
        "connectors.flock_portal",
    }
    # And the generic parsing.drift core is wired (the structural kind).
    assert any(f.kind == "structural" for f in spec.families)


def test_spec_refuses_an_unallowlisted_module(tmp_path: Path) -> None:
    bad = tmp_path / "spec.toml"
    bad.write_text(
        'schema = "sig.parser-canary-spec/1"\n'
        'issue_classes = ["parser_drift"]\n'
        "[[family]]\n"
        'id = "evil"\n'
        'module = "os"\n'
        'parse = "system"\n'
        'canary = "canary_findings"\n'
        'fixture = "x"\n'
    )
    with pytest.raises(parser_canary.CanarySpecError, match="allow-list"):
        parser_canary.load_spec(bad)


# --- the replay + the typed issue (the acceptance shape) ---------------------


def test_every_family_replays_clean_on_the_committed_corpus() -> None:
    report = parser_canary.run_canary(_spec(), CORPUS, now="2026-11-07T01:45:00Z")
    assert report["schema"] == "sig.parser-canary-report/1"
    assert report["verdict"] == "pass"
    assert report["issues"] == []
    assert report["families_evaluated"] == len(_spec().families) == report["families_ok"]
    assert {r["verdict"] for r in report["results"]} == {"ok"}


def test_a_mutated_fixture_raises_the_drift_issue_class(tmp_path: Path) -> None:
    """The catalog's acceptance shape, verbatim: a mutated fixture raises the
    drift issue class — ``parser_drift``, a typed ``sig.parser-canary-issue/1``
    entry, never a smoothed pass."""
    corpus = _corpus_copy(tmp_path)
    # Mutate the OSM sample: drop the top-level 'elements' list the canary
    # requires (the same drift test_osm's canary test asserts).
    (corpus / "corpus/osm/overpass_snapshot.json").write_text(json.dumps({"generator": "x"}))
    report = parser_canary.run_canary(_spec(), corpus, now="2026-11-07T01:45:00Z")
    assert report["verdict"] == "fail"
    drift = [i for i in report["issues"] if i["issue_class"] == "parser_drift"]
    assert len(drift) == 1
    assert drift[0]["schema"] == "sig.parser-canary-issue/1"
    assert drift[0]["family"] == "osm_overpass"
    assert "elements" in " ".join(drift[0]["findings"])


def test_a_mutated_csv_fixture_raises_drift(tmp_path: Path) -> None:
    corpus = _corpus_copy(tmp_path)
    (corpus / "corpus/atlas/adoption_feed.csv").write_text("City,Type\nX,ALPR\n")
    report = parser_canary.run_canary(_spec(), corpus)
    drift = [i for i in report["issues"] if i["issue_class"] == "parser_drift"]
    assert any(i["family"] == "atlas_adoption_feed" for i in drift)


def test_a_missing_fixture_is_canary_error_not_drift(tmp_path: Path) -> None:
    corpus = _corpus_copy(tmp_path)
    (corpus / "corpus/flock_portal/snapshot_2026_09.json").unlink()
    report = parser_canary.run_canary(_spec(), corpus)
    assert report["verdict"] == "fail"
    err = [i for i in report["issues"] if i["issue_class"] == "canary_error"]
    assert len(err) == 1 and err[0]["family"] == "flock_portal"


def test_a_mutated_structural_fixture_raises_drift(tmp_path: Path) -> None:
    corpus = _corpus_copy(tmp_path)
    doc = json.loads((corpus / "corpus/records_index/records_index_ok.json").read_text())
    for rec in doc["records"]:
        rec.pop("attachments", None)
    (corpus / "corpus/records_index/records_index_ok.json").write_text(json.dumps(doc))
    report = parser_canary.run_canary(_spec(), corpus)
    drift = [i for i in report["issues"] if i["issue_class"] == "parser_drift"]
    assert any(i["family"] == "records_index" for i in drift)


# --- the scheduled leg --------------------------------------------------------


def _run_scheduled(tmp_path: Path, **kw) -> tuple[int, dict, dict | None]:
    out = tmp_path / "out"
    code = parser_canary.run_scheduled(
        SPEC,
        corpus_root=kw.pop("corpus", CORPUS),
        bucket=None,
        records_prefix="ops/probes/parser-canary/",
        out_dir=out,
        job_name="sig-parser-canary",
        no_alert=True,
        now=kw.pop("now", "2026-11-03T01:45:00Z"),
        **kw,
    )
    record = json.loads((out / "probe-run.json").read_text())
    report_path = out / "parser-canary-report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    return code, record, report


def test_scheduled_run_writes_report_and_probe_run(tmp_path: Path) -> None:
    code, record, report = _run_scheduled(tmp_path)
    assert code == 0
    assert record["version"] == "sig.probe-run/1"
    assert record["overall"] == "pass"
    assert report and report["verdict"] == "pass"
    # One check leg per family — all pass.
    for f in _spec().families:
        assert record["checks"][f"family:{f.family_id}"]["verdict"] == "pass"


def test_scheduled_run_suppresses_inside_the_quiet_band(tmp_path: Path) -> None:
    code, record, report = _run_scheduled(tmp_path, now="2026-11-03T03:30:00Z")
    assert code == 0
    assert report is None  # suppressed before any replay — never a fabricated pass
    assert record["checks"]["window"]["verdict"] == "skipped"
    assert "03:00" in record["checks"]["window"]["reason"]


def test_scheduled_run_suppresses_inside_the_batch_window(tmp_path: Path) -> None:
    code, record, _ = _run_scheduled(tmp_path, now="2026-11-08T01:45:00Z")  # future-ok: scheduled: a day-8 batch-window instant the clock guard must suppress
    assert code == 0
    assert record["checks"]["window"]["verdict"] == "skipped"
    assert "batch-window" in record["checks"]["window"]["reason"]


def test_scheduled_run_fails_loud_on_drift(tmp_path: Path) -> None:
    corpus = _corpus_copy(tmp_path / "c2")
    (corpus / "corpus/osm/overpass_snapshot.json").write_text('{"generator": "x"}')
    code, record, report = _run_scheduled(tmp_path, corpus=corpus)
    assert code == 1
    assert record["overall"] == "fail"
    assert record["checks"]["family:osm_overpass"]["issue_class"] == "parser_drift"
    assert report["issues"][0]["issue_class"] == "parser_drift"


def test_scheduled_run_records_the_alert_on_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = _corpus_copy(tmp_path / "c3")
    (corpus / "corpus/osm/overpass_snapshot.json").write_text('{"generator": "x"}')
    log = tmp_path / "alerts.jsonl"
    monkeypatch.setenv("SIG_ALERT_LOG", str(log))
    out = tmp_path / "out"
    code = parser_canary.run_scheduled(
        SPEC,
        corpus_root=corpus,
        bucket=None,
        records_prefix="ops/probes/parser-canary/",
        out_dir=out,
        job_name="sig-parser-canary",
        no_alert=False,
        now="2026-11-03T01:45:00Z",
    )
    assert code != 0
    rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    assert rows and rows[0]["kind"] == "parser-canary"
    assert "parser_drift" in json.dumps(rows[0])


# --- the declaration (sig.parser-canary/1) ------------------------------------


def test_committed_declaration_validates() -> None:
    decl = parser_canary_job.load_declaration(DECLARATION)
    assert decl.job == "sig-parser-canary"
    assert decl.scheduler.name == "sig-sched-parser-canary"
    assert decl.scheduler.schedule == "45 1 1-5,14-31 * *"
    assert decl.tasks == 1 and decl.max_retries == 0
    assert decl.corpus_root == "/app/tests/parser_canary"
    assert decl.probe_prefix.startswith("ops/probes/")
    assert {s.secret for s in decl.secret_env} == {"sig-alert-webhook-token"}
    assert "exec sig-ops parser-canary scheduled" in " ".join(decl.container_args)


def test_declaration_schedule_never_fires_inside_a_window() -> None:
    """validate_schedule already ran at load — assert the enumerated fires stay
    outside both OM-19 windows (the static half of the contract)."""
    from ops.quality_job import fire_times, in_batch_window, in_quiet_hours

    decl = parser_canary_job.load_declaration(DECLARATION)
    fires = fire_times(decl.scheduler.schedule, start=__import__("datetime").date(2026, 1, 1))
    assert fires
    assert all(not in_quiet_hours(f) and not in_batch_window(f) for f in fires)


def test_render_produces_the_whole_mutation_set() -> None:
    decl = parser_canary_job.load_declaration(DECLARATION)
    image = "example.com/sig-api@sha256:" + "a" * 64
    env = {name: "v" for name in decl.plain_env}
    rendered = parser_canary_job.render(decl, project="p", region="r", image=image, env_values=env)
    for key in ("deploy", "job_invoker", "trigger_create", "trigger_update", "rollback"):
        assert rendered[key]
    assert "sig-parser-canary" in " ".join(rendered["deploy"])
    assert (
        "--set-secrets=SIG_ALERT_WEBHOOK_TOKEN=sig-alert-webhook-token:latest" in rendered["deploy"]
    )
    assert rendered["rollback"]["delete_job"]


def test_render_refuses_an_unpinned_image() -> None:
    decl = parser_canary_job.load_declaration(DECLARATION)
    with pytest.raises(ValueError, match="digest"):
        parser_canary_job.render(
            decl,
            project="p",
            region="r",
            image="example.com/sig-api:latest",
            env_values={n: "v" for n in decl.plain_env},
        )


def _describe(**over) -> dict:
    spec = {
        "containers": [
            {
                "image": "x@sha256:abc",
                "env": [
                    {"name": "SIG_ALERT_WEBHOOK_TOKEN", "valueFrom": {"secretKeyRef": {}}},
                ],
            }
        ],
        "serviceAccountName": "sig-quality-probe-rt@p.iam.gserviceaccount.com",
    }
    doc = {
        "metadata": {"name": "sig-parser-canary"},
        "spec": {
            "template": {
                "spec": {
                    "maxRetries": 0,
                    "taskTimeout": "600s",
                    "template": {"spec": spec},
                }
            }
        },
    }
    for k, v in over.items():
        doc[k] = v
    return doc


def test_verify_describe_clean_and_drifted() -> None:
    decl = parser_canary_job.load_declaration(DECLARATION)
    assert parser_canary_job.verify_describe(decl, _describe(), project="p") == []
    # An undeclared secret env is drift; a missing declared one is drift.
    bad = _describe()
    bad["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]["env"] = []
    diffs = parser_canary_job.verify_describe(decl, bad, project="p")
    assert any("secret env" in d for d in diffs)


def test_verify_trigger_clean_and_paused() -> None:
    decl = parser_canary_job.load_declaration(DECLARATION)
    trig = {
        "name": "x/sig-sched-parser-canary",
        "schedule": "45 1 1-5,14-31 * *",
        "timeZone": "Etc/UTC",
        "httpTarget": {
            "uri": (
                "https://r-run.googleapis.com/apis/run.googleapis.com/v1/"
                "namespaces/p/jobs/sig-parser-canary:run"
            ),
            "httpMethod": "POST",
            "oauthToken": {"serviceAccountEmail": "sig-scheduler@p.iam.gserviceaccount.com"},
        },
    }
    assert parser_canary_job.verify_trigger(decl, trig, project="p", region="r") == []
    diffs = parser_canary_job.verify_trigger(
        decl, {**trig, "state": "PAUSED"}, project="p", region="r"
    )
    assert any("PAUSED" in d for d in diffs)


# --- the CLI + the leg script's offline path ----------------------------------


def test_cli_check_and_run_are_green() -> None:
    proc = subprocess.run(
        ["uv", "run", "sig-ops", "parser-canary", "check"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "check OK" in proc.stdout


def test_job_script_check_is_green_without_adc() -> None:
    """`--check` prints the plan, uses no ADC, opens no network, exits 0."""
    import os

    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PLAN:" in proc.stdout
    assert "check OK" in proc.stdout


def test_probe_run_record_shape_is_the_shared_schema(tmp_path: Path) -> None:
    """The canary's envelope is sig.probe-run/1 — never a parallel schema."""
    record = probe_run.build_record("sig-parser-canary", {"leg": probe_run.CheckResult("pass", {})})
    assert record["version"] == "sig.probe-run/1"
