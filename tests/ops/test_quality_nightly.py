# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The nightly probe run surface (P34.44b, SIG-CONF-006/007): the
in-container ``sig-ops quality nightly`` verb suppresses inside the
contract's windows (and still writes a ``sig.probe-run/1``), records land
as NEW timestamped objects under the conditioned prefix, a failed run
alerts through the recorded ledger, and ``baseline`` emits the
``sig.quality-baseline/1`` record + proposal. Everything here runs offline —
buckets, notifiers and ledgers are injected fakes; no socket opens."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from ops.alerts import AlertLedger
from ops.quality import (
    PROBE_PREFIX_DEFAULT,
    _fire_quality_alert,
    _object_stamp,
    _parse_gs_uri,
    error_probe_record,
    fetch_release,
    main,
    nightly_dsn,
    suppressed_probe_record,
    upload_probe_record,
    upload_records,
)


class FakeBucket:
    """A ``GcsBucket``-shaped fake: objects kept in memory, writes counted."""

    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects: dict[str, bytes] = dict(objects or {})
        self.puts: list[str] = []

    def put_object(self, name: str, body: bytes, content_type: str = "") -> None:
        assert name not in self.objects, f"overwrite refused: {name}"
        self.objects[name] = body
        self.puts.append(name)

    def get_object(self, name: str) -> bytes:
        return self.objects[name]

    def list_objects(self, prefix: str) -> list[str]:
        return [n for n in self.objects if n.startswith(prefix)]


# --- the record shapes --------------------------------------------------------


def test_suppressed_record_is_a_probe_run() -> None:
    rec = suppressed_probe_record(
        reason="quiet-hours-03:00-06:30Z",
        generated_at="2026-10-20T03:15:00Z",
        job="sig-quality-probe",
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "suppressed"
    assert rec["suppressed"] == "quiet-hours-03:00-06:30Z"
    assert rec["checks"] == []


def test_error_record_records_the_failure_never_silence() -> None:
    rec = error_probe_record(
        reason="connection refused",
        generated_at="2026-10-20T01:00:00Z",
        job="sig-quality-probe",
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "fail"
    assert rec["error"] == "connection refused"
    assert rec["checks"][0]["outcome"] == "fail"


# --- timestamped, append-only object names ------------------------------------


def test_object_stamp_partitions_by_day() -> None:
    assert _object_stamp("2026-10-20T01:00:00Z") == "2026-10-20/2026-10-20T01-00-00Z"


def test_upload_records_writes_two_new_objects() -> None:
    bucket = FakeBucket()
    report = {
        "generated_at": "2026-10-20T01:00:00Z",
        "version": "sig.quality-report/1",
        "target": "hosted-spine",
        "placement": "M",
        "registry": {},
        "checks": [],
        "summary": {"overall": "pass"},
        "totals": {"evaluated": 0, "offered": 0},
    }
    names = upload_records(bucket, PROBE_PREFIX_DEFAULT, report)
    assert names["report"].startswith(PROBE_PREFIX_DEFAULT + "2026-10-20/")
    assert names["report"].endswith("-quality-report.json")
    assert names["probe_run"].endswith("-probe-run.json")
    assert len(bucket.puts) == 2
    probe = json.loads(bucket.objects[names["probe_run"]])
    assert probe["version"] == "sig.probe-run/1"
    assert probe["overall"] == "pass"


def test_upload_probe_record_names_a_new_object() -> None:
    bucket = FakeBucket()
    rec = suppressed_probe_record(
        reason="batch-window", generated_at="2026-11-07T01:00:00Z", job="j"
    )
    name = upload_probe_record(bucket, PROBE_PREFIX_DEFAULT, rec)
    assert name.startswith(PROBE_PREFIX_DEFAULT + "2026-11-07/")
    assert json.loads(bucket.objects[name])["suppressed"] == "batch-window"


# --- the DSN — env-only credentials, fail closed --------------------------------


def test_nightly_dsn_prefers_the_explicit_dsn() -> None:
    assert nightly_dsn({"SIG_QUALITY_DSN": "host=x dbname=sig"}) == "host=x dbname=sig"
    assert nightly_dsn({"SIG_DB_DSN": "host=y dbname=sig"}) == "host=y dbname=sig"


def test_nightly_dsn_builds_the_cloudsql_socket_dsn() -> None:
    dsn = nightly_dsn(
        {
            "SIG_CLOUDSQL_CONNECTION": "proj:region:sig-pg",
            "SIG_AUDIT_PASSWORD": "secret",
            "SIG_PG_DB": "sig",
        }
    )
    assert dsn == "host=/cloudsql/proj:region:sig-pg dbname=sig user=sig_audit password=secret"


def test_nightly_dsn_is_empty_without_credentials() -> None:
    assert nightly_dsn({}) == ""
    assert nightly_dsn({"SIG_CLOUDSQL_CONNECTION": "p:r:i"}) == ""  # no password → no half-DSN


# --- the bounded release fetch ---------------------------------------------------


def test_fetch_release_is_bounded_and_deterministic(tmp_path: Path) -> None:
    objects = {
        "rel/b/file2.json": b"222",
        "rel/a/file1.json": b"111",
        "rel/dir/": b"",
        "rel/../escape": b"!!!",
    }
    bucket = FakeBucket(objects)
    dest = tmp_path / "out"
    acct = fetch_release(bucket, "rel/", dest)
    assert acct["objects_written"] == 2
    assert (dest / "a" / "file1.json").read_bytes() == b"111"
    assert not (dest / ".." / "escape").exists()
    assert not acct["truncated"]


def test_fetch_release_caps_objects_and_bytes(tmp_path: Path) -> None:
    objects = {f"rel/f{i}.bin": b"x" * 100 for i in range(10)}
    bucket = FakeBucket(objects)
    acct = fetch_release(bucket, "rel/", tmp_path, max_objects=3)
    assert acct["objects_written"] == 3 and acct["truncated"]
    acct = fetch_release(bucket, "rel/", tmp_path / "b", max_bytes=250)
    assert acct["objects_written"] == 2 and acct["truncated"]


def test_parse_gs_uri_refuses_non_gs() -> None:
    assert _parse_gs_uri("gs://bkt/releases/2026/") == ("bkt", "releases/2026/")
    with pytest.raises(ValueError, match="gs://"):
        _parse_gs_uri("https://bkt/releases/")


# --- the recorded alert path ------------------------------------------------------


def test_quality_alert_is_recorded_before_delivery(tmp_path: Path) -> None:
    ledger = AlertLedger(tmp_path / "alerts.jsonl")
    fired = _fire_quality_alert(
        "sig-quality-probe hosted-spine: fail",
        detail={"x": 1},
        ledger=ledger,
        notifiers=[],
    )
    rows = [json.loads(line) for line in ledger.path.read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["kind"] == "quality-probe"
    assert fired.kind == "quality-probe"


# --- the nightly verb end to end (offline) -----------------------------------------


def test_nightly_suppressed_writes_a_probe_run(tmp_path: Path, capsys) -> None:
    rc = main(
        [
            "nightly",
            "--now",
            "2026-10-20T03:15:00Z",
            "--out",
            str(tmp_path),
        ]
    )
    assert rc == 0
    rec = json.loads((tmp_path / "probe-run.json").read_text())
    assert rec["overall"] == "suppressed"
    assert "03:00" in rec["suppressed"]


def test_nightly_without_dsn_reports_partial_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SIG_QUALITY_DSN", raising=False)
    monkeypatch.delenv("SIG_DB_DSN", raising=False)
    monkeypatch.delenv("SIG_AUDIT_PASSWORD", raising=False)
    monkeypatch.delenv("SIG_CLOUDSQL_CONNECTION", raising=False)
    rc = main(
        [
            "nightly",
            "--now",
            "2026-10-20T01:00:00Z",
            "--out",
            str(tmp_path),
            "--no-alert",
        ]
    )
    assert rc == 3  # partial — spine checks not_evaluable, never a clean pass
    report = json.loads((tmp_path / "quality-report.json").read_text())
    assert report["summary"]["overall"] != "pass"
    probe = json.loads((tmp_path / "probe-run.json").read_text())
    assert probe["version"] == "sig.probe-run/1"
    assert probe["placement"] == "M"


def test_nightly_run_failure_is_recorded_and_alerted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused connection → the error probe-run + a fired (recorded) alert."""

    def _refuse(dsn: str) -> Any:
        raise RuntimeError("connection refused")

    monkeypatch.setattr("ops.quality.connect_readonly", _refuse)
    monkeypatch.setenv("SIG_QUALITY_DSN", "host=nowhere dbname=sig")
    monkeypatch.setenv("SIG_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    rc = main(["nightly", "--now", "2026-10-20T01:00:00Z"])
    assert rc != 0
    rows = (tmp_path / "alerts.jsonl").read_text().splitlines()
    assert rows and "run failed" in json.loads(rows[-1])["message"]


def test_nightly_suppression_needs_no_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window check runs BEFORE any credential/env is read — a suppressed
    run on a bare container still records."""
    monkeypatch.delenv("SIG_QUALITY_DSN", raising=False)
    monkeypatch.delenv("SIG_DB_DSN", raising=False)
    monkeypatch.delenv("SIG_AUDIT_PASSWORD", raising=False)
    rc = main(["nightly", "--now", "2026-11-07T01:00:00Z", "--out", str(tmp_path)])
    assert rc == 0
    rec = json.loads((tmp_path / "probe-run.json").read_text())
    assert "batch-window" in rec["suppressed"]


# --- the job verbs over the CLI -----------------------------------------------------


def test_job_plan_prints_the_declaration(capsys) -> None:
    assert main(["job", "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["schema"] == "sig.quality-probe/1"
    assert plan["scheduler"]["schedule"] == "0 1 1-5,14-31 * *"


def test_job_window_exits_42_when_queued(capsys) -> None:
    rc = main(
        ["job", "window", "--earliest", "2026-10-13T12:00:00Z", "--now", "2026-10-08T01:00:00Z"]
    )
    assert rc == 42
    assert "QUEUED" in capsys.readouterr().out
    rc = main(
        ["job", "window", "--earliest", "2026-10-13T12:00:00Z", "--now", "2026-10-14T01:00:00Z"]
    )
    assert rc == 0


# --- the baseline verb end to end -----------------------------------------------------


def test_baseline_emits_the_record_and_proposal(tmp_path: Path) -> None:
    scan = tmp_path / "scan" / "compartment"
    scan.mkdir(parents=True)
    (scan / "sites.jsonl").write_text('{"entity_id":"e1","label":"Cam 1"}\n')
    out = tmp_path / "out"
    rc = main(
        [
            "baseline",
            "--scan-dir",
            str(tmp_path / "scan"),
            "--out",
            str(out),
            "--run-id",
            "baseline-test",
            "--emit",
        ]
    )
    assert rc == 0
    record = json.loads((out / "quality-baseline.json").read_text())
    assert record["version"] == "sig.quality-baseline/1"
    assert record["run_id"] == "baseline-test"
    assert record["counts"]["measured"] >= 1
    assert (out / "quality-report-M.json").exists()
    assert (out / "quality-report-R.json").exists()
    # Every ratchet check carries a proposal row (measured or not_measured).
    assert all(
        r["state"] in {"baselined", "tightened", "kept", "regression_kept", "not_measured"}
        for r in record["proposal"]
    )
