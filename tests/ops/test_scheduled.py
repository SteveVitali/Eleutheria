# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Scheduled live operations (P26.1 / OPS.2): GCS run-log, probes, cadence.

Everything here is deterministic: the GCS client's opener + token provider are
injected fakes (no socket is ever opened), the probe checks are injected, and
``scheduled_ingest``'s connector runner is a stub — so the recorded-shapes and
the refusal-honesty paths are proven without network, credentials, or a real
upstream.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest
from ops.observe import ProbeResult

from ops import cli
from ops import gcs as G
from ops import scheduled as S

REPO_ROOT = Path(__file__).resolve().parents[2]
CADENCE = REPO_ROOT / "ops" / "cadence.toml"


# --- fake GCS transport -------------------------------------------------------


class FakeGcs:
    """An in-memory object store behind the GcsBucket call surface."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def bucket_client(self) -> G.GcsBucket:
        def opener(req: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
            assert req.headers.get("Authorization") == "Bearer fake-token"
            url = req.full_url
            if "/upload/storage/v1/" in url:
                name = _query(url)["name"]
                self.objects[name] = req.data or b""
                return 200, b"{}"
            if "alt=media" in url:
                name = url.split("/o/", 1)[1].split("?")[0]
                import urllib.parse

                return 200, self.objects[urllib.parse.unquote(name)]
            # list
            prefix = _query(url).get("prefix", "")
            items = [{"name": n} for n in sorted(self.objects) if n.startswith(prefix)]
            return 200, json.dumps({"items": items}).encode()

        return G.GcsBucket("fake-bucket", token_provider=lambda: "fake-token", opener=opener)


def _query(url: str) -> dict[str, str]:
    import urllib.parse

    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}


# --- GcsBucket -----------------------------------------------------------------


def test_put_object_posts_media_upload_with_bearer() -> None:
    store = FakeGcs()
    bucket = store.bucket_client()
    name = bucket.put_object("ops/probes/2026-09-16/t.jsonl", b"{}\n")
    assert name == "ops/probes/2026-09-16/t.jsonl"
    assert store.objects[name] == b"{}\n"


def test_list_and_get_round_trip() -> None:
    store = FakeGcs()
    bucket = store.bucket_client()
    bucket.put_object("ops/probes/2026-09-16/a.jsonl", b"one\n")
    bucket.put_object("ops/probes/2026-09-16/b.jsonl", b"two\n")
    bucket.put_object("ops/runs/x/2026-09-16/c.json", b"three\n")
    assert bucket.list_objects("ops/probes/") == [
        "ops/probes/2026-09-16/a.jsonl",
        "ops/probes/2026-09-16/b.jsonl",
    ]
    assert bucket.get_object("ops/runs/x/2026-09-16/c.json") == b"three\n"


def test_no_token_raises_gcs_error_never_silence() -> None:
    bucket = G.GcsBucket("b", token_provider=lambda: None, opener=lambda *a: (200, b""))
    with pytest.raises(G.GcsError, match="no GCS access token"):
        bucket.put_object("x", b"")


def test_http_error_raises_gcs_error() -> None:
    bucket = G.GcsBucket("b", token_provider=lambda: "t", opener=lambda *a: (403, b"denied"))
    with pytest.raises(G.GcsError, match="HTTP 403"):
        bucket.list_objects("ops/")


# --- cadence.toml --------------------------------------------------------------


def test_cadence_toml_covers_every_loadable_live_target_source() -> None:
    config = S.load_cadence(CADENCE)
    assert S.unscheduled_live_sources(config) == []


def test_cadence_toml_rows_are_well_formed() -> None:
    config = S.load_cadence(CADENCE)
    ids = [s.source for s in config.sources]
    assert len(ids) == len(set(ids)), "duplicate source rows"
    for s in config.sources:
        assert len(s.cron.split()) == 5, f"{s.source}: bad cron {s.cron!r}"
        assert s.cadence in {"weekly", "monthly", "quarterly"}
        assert s.job.startswith("sig-ingest-")
        assert s.scheduler.startswith("sig-sched-")
    existing = [s for s in config.sources if s.existing]
    assert [s.source for s in existing] == ["muckrock"]
    assert existing[0].scheduler == "sig-sched-muckrock"
    # The muckrock job keeps its refresh-token Secret Manager binding (name only)
    # when it is upserted onto the scheduled-ingest wrapper.
    assert existing[0].secrets == ("SIG_MUCKROCK_REFRESH=sig-muckrock-refresh",)


def test_cadence_cli_check_is_green() -> None:
    assert cli.main(["cadence", "--check"]) == 0


# --- hosted probe sweep ---------------------------------------------------------


def test_probe_hosted_probes_every_resolved_target() -> None:
    targets = [
        ("api", "http", "https://api.example/"),
        ("pg", "cloudsql", "postgresql://x"),
    ]
    seen: list[str] = []

    def fake_http(url: str) -> bool:
        seen.append(url)
        return True

    def fake_pg(dsn: str) -> bool:
        seen.append(dsn)
        return False

    rows = S.probe_hosted(
        targets, now="2026-09-16T12:00:00+00:00", check_http=fake_http, check_pg=fake_pg
    )
    assert [r.service for r in rows] == ["api", "pg"]
    assert rows[0].ok is True and rows[1].ok is False
    assert rows[1].detail == "unreachable"
    assert seen == ["https://api.example/", "postgresql://x"]


def test_resolve_targets_env_then_template_then_skip() -> None:
    config = S.load_cadence(CADENCE)
    env = {
        "SIG_PROBE_API_URL": "https://api.test/",
        "SIG_PROBE_WEB_URL": "https://web.test",
        "SIG_GCP_PROJECT": "proj-x",
        "SIG_PG_USER": "sig",
        "SIG_PG_DB": "sig",
        "SIG_CLOUDSQL_CONNECTION": "proj-x:us-central1:sig-pg",
    }
    resolved, skipped = S.resolve_targets(config, env)
    names = dict(resolved)
    assert skipped == []
    assert names["sig-api-root"] == "https://api.test/"
    assert names["sig-api-coverage-okc"] == "https://api.test/v1/coverage/okc"
    assert names["sig-web-root"] == "https://web.test/"
    assert (
        names["sig-public-okc-manifest"]
        == "https://storage.googleapis.com/proj-x-sig-public/okc/manifest.json"
    )
    assert names["sig-pg-cloudsql"].startswith("postgresql://sig:")


def test_resolve_targets_skips_unresolvable_never_placeholders() -> None:
    config = S.load_cadence(CADENCE)
    resolved, skipped = S.resolve_targets(config, {})
    names = {n for n, _ in resolved}
    assert names == set()  # nothing env-resolvable, no {project}
    assert set(skipped) == {s.name for s in config.probe_targets}


def test_hosted_pg_dsn_assembles_from_env_parts() -> None:
    env = {
        "SIG_PG_USER": "sig",
        "SIG_PG_DB": "sig",
        "SIG_PG_PASSWORD": "pw",
        "SIG_CLOUDSQL_CONNECTION": "p:r:i",
    }
    assert S.hosted_pg_dsn(env) == "postgresql://sig:pw@/sig?host=/cloudsql/p:r:i"
    assert S.hosted_pg_dsn({"SIG_PROBE_DSN": "postgresql://direct"}) == "postgresql://direct"
    assert S.hosted_pg_dsn({}) is None


def test_sweep_object_name_is_per_run_timestamped() -> None:
    name = S.sweep_object_name("ops/probes", "2026-09-16T18:30:00+00:00")
    assert name == "ops/probes/2026-09-16/2026-09-16T18-30-00+00-00.jsonl"


def test_upload_sweep_writes_one_jsonl_object() -> None:
    store = FakeGcs()
    bucket = store.bucket_client()
    rows = [
        ProbeResult("api", True, 12.0, "2026-09-16T18:30:00+00:00"),
        ProbeResult("pg", False, 3000.0, "2026-09-16T18:30:00+00:00", "unreachable"),
    ]
    name = S.upload_sweep(bucket, "ops/probes", rows, "2026-09-16T18:30:00+00:00")
    lines = store.objects[name].decode().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["ok"] is False


# --- probe history ---------------------------------------------------------------


def _sweep(ts: str, api_ok: bool = True, api_ms: float = 100.0) -> list[ProbeResult]:
    return [
        ProbeResult("api", api_ok, api_ms, ts),
        ProbeResult("web", True, 50.0, ts),
    ]


def test_fold_probe_history_counts_latest_and_p95() -> None:
    rows = _sweep("2026-09-16T00:00:00+00:00") + _sweep(
        "2026-09-16T06:00:00+00:00", api_ok=False, api_ms=3000.0
    )
    summaries = {s.target: s for s in S.fold_probe_history(rows)}
    api = summaries["api"]
    assert api.probes == 2 and api.ok == 1 and api.uptime_pct == 50.0
    assert api.latest_ok is False and api.latest_ts == "2026-09-16T06:00:00+00:00"
    assert api.p95_ms == 3000.0
    assert summaries["web"].uptime_pct == 100.0


def test_read_sweep_rows_flattens_stored_objects() -> None:
    store = FakeGcs()
    bucket = store.bucket_client()
    S.upload_sweep(
        bucket, "ops/probes", _sweep("2026-09-16T00:00:00+00:00"), "2026-09-16T00:00:00+00:00"
    )
    S.upload_sweep(
        bucket, "ops/probes", _sweep("2026-09-16T06:00:00+00:00"), "2026-09-16T06:00:00+00:00"
    )
    rows = S.read_sweep_rows(bucket, "ops/probes")
    assert len(rows) == 4
    summaries = {s.target: s for s in S.fold_probe_history(rows)}
    assert summaries["api"].probes == 2


# --- scheduled ingest ------------------------------------------------------------


class _Capture:
    def __init__(self, digest: str) -> None:
        self.digest = digest


class _FetchRecord:
    def to_dict(self) -> dict[str, object]:
        return {"claim_count": 3, "capture_digests": ["abc123"]}


class _Report:
    def __init__(self, claims: int = 3) -> None:
        self.claims = [{"id": i} for i in range(claims)]
        self.captures = [_Capture("abc123")]
        self.fetch_record = _FetchRecord()
        self.refusals: list[dict] = []
        self.disappearances: list[dict] = []


class LiveGateRefused(Exception):
    reasons = ["ingestion_permitted=false"]


class RobotsDisallowed(Exception):
    pass


def test_scheduled_ingest_ok_row() -> None:
    row = S.scheduled_ingest(
        "okcpd_policy",
        runner=lambda *a, **k: _Report(3),
        now="2026-09-16T20:00:00+00:00",
    )
    assert row.outcome == "ok" and row.exit_code == 0
    assert row.claims_added == 3 and row.capture_digests == ("abc123",)
    assert row.fetch_record["claim_count"] == 3


def test_scheduled_ingest_maps_refusals_to_the_cli_exit_codes() -> None:
    def refuse(*a: object, **k: object) -> None:
        raise LiveGateRefused("x", ["ingestion_permitted=false"])

    row = S.scheduled_ingest("gated_source", runner=refuse)
    # Class-name matching keeps the mapper dependency-free; a runner raising a
    # class NAMED LiveGateRefused maps to the connectors CLI's exit 3.
    assert row.outcome == "gate_refused" and row.exit_code == 3
    assert "ingestion_permitted" in row.refusal_reason

    def robots(*a: object, **k: object) -> None:
        raise RobotsDisallowed("Disallow: /")

    row = S.scheduled_ingest("ok_statute", runner=robots)
    assert row.outcome == "politeness_refusal" and row.exit_code == 6
    assert "Disallow: /" in row.refusal_reason


def test_scheduled_ingest_records_refusals_never_silence() -> None:
    row = S.scheduled_ingest("x", runner=lambda *a, **k: _Report(0))
    assert row.claims_added == 0 and row.outcome == "ok"
    # An error still produces a row — the run is recorded, then the exit code
    # carries the failure to the job.
    boom = S.scheduled_ingest(
        "x",
        runner=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kaput")),
    )
    assert boom.outcome == "error" and boom.exit_code == 1 and "kaput" in boom.detail


def test_store_run_row_writes_local_mirror_and_gcs_object(tmp_path: Path) -> None:
    store = FakeGcs()
    row = S.scheduled_ingest(
        "okcpd_policy", runner=lambda *a, **k: _Report(1), now="2026-09-16T20:00:00+00:00"
    )
    written = S.store_run_row(row, prefix="ops/runs", gcs=store.bucket_client(), local_dir=tmp_path)
    assert "local" in written and "gcs" in written
    gcs_name = written["gcs"].removeprefix("gs://fake-bucket/")
    stored = json.loads(store.objects[gcs_name])
    assert stored["kind"] == "scheduled-ingest" and stored["source"] == "okcpd_policy"
    assert stored["outcome"] == "ok"
    # WORM shape: two runs of the same source land at different object names.
    row2 = S.scheduled_ingest(
        "okcpd_policy", runner=lambda *a, **k: _Report(0), now="2026-09-17T20:00:00+00:00"
    )
    written2 = S.store_run_row(row2, prefix="ops/runs", gcs=store.bucket_client())
    assert written2["gcs"] != written["gcs"]


def test_run_object_name_layout() -> None:
    name = S.run_object_name("ops/runs", "okcpd_policy", "2026-09-16T20:00:00+00:00")
    assert name == "ops/runs/okcpd_policy/2026-09-16/2026-09-16T20-00-00+00-00.json"


# --- CLI end to end (local, deterministic) ---------------------------------------


def test_cli_probe_hosted_appends_log_and_uploads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIG_PROBE_LOG", str(tmp_path / "probes.jsonl"))
    monkeypatch.setenv("SIG_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setenv("SIG_PROBE_API_URL", "https://api.test")
    monkeypatch.setenv("SIG_PROBE_WEB_URL", "https://web.test")
    monkeypatch.setenv("SIG_GCP_PROJECT", "proj-x")
    monkeypatch.setenv("SIG_OPS_GCS_BUCKET", "proj-x-sig-restricted")
    for var in ("SIG_PG_USER", "SIG_PG_DB", "SIG_CLOUDSQL_CONNECTION", "SIG_PROBE_DSN"):
        monkeypatch.delenv(var, raising=False)

    store = FakeGcs()
    monkeypatch.setattr(cli, "_gcs_bucket", lambda _a: store.bucket_client())
    monkeypatch.setattr("ops.scheduled.http_ok", lambda url, **k: True)
    # The cloudsql target is unconfigured here -> honestly skipped, not probed.
    code = cli.main(["probe-hosted"])
    assert code == 0
    lines = (tmp_path / "probes.jsonl").read_text().splitlines()
    services = {json.loads(ln)["service"] for ln in lines}
    assert "sig-api-coverage-okc" in services and "sig-pg-cloudsql" not in services
    sweep_names = [n for n in store.objects if n.startswith("ops/probes/")]
    assert len(sweep_names) == 1


def test_cli_probe_hosted_down_target_fires_recorded_alert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIG_PROBE_LOG", str(tmp_path / "probes.jsonl"))
    monkeypatch.setenv("SIG_ALERT_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setenv("SIG_PROBE_API_URL", "https://api.test")
    monkeypatch.setattr("ops.scheduled.http_ok", lambda url, **k: "dead" not in url)
    code = cli.main(["probe-hosted", "--alert", "--extra-target", "dead=https://dead.invalid/"])
    assert code == 6  # an alert fired
    alerts = (tmp_path / "alerts.jsonl").read_text().splitlines()
    assert any("dead" in ln for ln in alerts)


def test_cli_probe_history_folds_a_local_log(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "probes.jsonl"
    log.write_text(
        "".join(
            json.dumps(r.as_json()) + "\n"
            for r in _sweep("2026-09-16T00:00:00+00:00")
            + _sweep("2026-09-16T06:00:00+00:00", api_ok=False)
        )
    )
    assert cli.main(["probe-history", "--local", str(log)]) == 0
    out = capsys.readouterr().out
    assert "| api | 2 | 1 | 50.0 |" in out


def test_cli_scheduled_ingest_writes_the_run_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FakeGcs()
    monkeypatch.setenv("SIG_RUN_LOG", str(tmp_path / "runs"))
    monkeypatch.setattr(cli, "_gcs_bucket", lambda _a: store.bucket_client())
    real = S.scheduled_ingest
    monkeypatch.setattr(
        "ops.scheduled.scheduled_ingest",
        lambda *a, **k: real(
            "okcpd_policy",
            runner=lambda *a2, **k2: _Report(2),
            now="2026-09-16T20:00:00+00:00",
        ),
    )
    code = cli.main(["scheduled-ingest", "--source", "okcpd_policy", "--sink", "memory"])
    assert code == 0
    run_names = [n for n in store.objects if n.startswith("ops/runs/okcpd_policy/")]
    assert len(run_names) == 1
    assert json.loads(store.objects[run_names[0]])["claims_added"] == 2


def test_cli_scheduled_ingest_refusal_still_stores_the_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = FakeGcs()
    monkeypatch.setenv("SIG_RUN_LOG", str(tmp_path / "runs"))
    monkeypatch.setattr(cli, "_gcs_bucket", lambda _a: store.bucket_client())

    def refuse(*a: object, **k: object) -> None:
        raise RobotsDisallowed("Disallow: /")

    real = S.scheduled_ingest
    monkeypatch.setattr(
        "ops.scheduled.scheduled_ingest",
        lambda *a, **k: real("ok_statute", runner=refuse),
    )
    code = cli.main(["scheduled-ingest", "--source", "ok_statute", "--sink", "memory"])
    assert code == 6  # the connector's own refusal exit code propagates
    stored = json.loads(next(iter(store.objects.values())))
    assert stored["outcome"] == "politeness_refusal"
