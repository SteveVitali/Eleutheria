# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Recorded alerts + the notifier seam (OBS.1 / GL-OBS-01, ADR-077).

The acceptance contract: an egress-threshold breach and a keepalive failure each
fire a RECORDED alert (an append-only ledger row, not just a log line), and no env
secret ever reaches a log, the ledger, or the wire (HG-09).
"""

from __future__ import annotations

import io
import json
import subprocess
import urllib.request
from pathlib import Path

import pytest

from ops import alerts as A
from ops import cli
from ops import observe as O


@pytest.fixture()
def ledger_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "alerts.jsonl"
    monkeypatch.setenv("SIG_ALERT_LOG", str(path))
    return path


def _read(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


# --- ACCEPTANCE: an egress-threshold breach fires a RECORDED alert -------------


def test_egress_breach_fires_a_recorded_alert(ledger_path: Path) -> None:
    # INFRA.1's alarm (ops.egress.build_report) consumed, not re-implemented:
    # 120 GB of a 100 GB budget is level=alarm (exit 5) AND records the alert.
    rc = cli.main(["egress-report", "--usage-gb", "120", "--alert"])
    assert rc == 5
    rows = _read(ledger_path)
    assert len(rows) == 1
    assert rows[0]["kind"] == "egress-budget"
    assert rows[0]["severity"] == "alarm"
    assert rows[0]["detail"]["usage_gb"] == 120.0


def test_egress_warn_band_records_a_warn_alert(ledger_path: Path) -> None:
    # 85 GB of 100 GB crosses the 0.8 alarm_ratio -> warn: still a threshold breach.
    rc = cli.main(["egress-report", "--usage-gb", "85", "--alert"])
    assert rc == 0
    rows = _read(ledger_path)
    assert [r["severity"] for r in rows] == ["warn"]


def test_egress_below_threshold_records_no_alert(ledger_path: Path) -> None:
    rc = cli.main(["egress-report", "--usage-gb", "50", "--alert"])
    assert rc == 0
    assert not ledger_path.exists()  # nothing breached -> nothing recorded


def test_egress_gate_pending_fires_no_false_alarm(ledger_path: Path) -> None:
    # HG-07: no live usage API -> gate-pending, never a fabricated breach (§3.1).
    rc = cli.main(["egress-report", "--alert"])
    assert rc == 0
    assert not ledger_path.exists()


# --- ACCEPTANCE: a keepalive failure fires a RECORDED alert --------------------


def test_keepalive_failure_fires_a_recorded_alert(
    ledger_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        O,
        "verify_keepalive",
        lambda **kw: O.KeepaliveResult(ok=False, checks={"rebuild": "FAIL: boom"}),
    )
    rc = cli.main(["keepalive-check"])
    assert rc == 6
    rows = _read(ledger_path)
    assert len(rows) == 1
    assert rows[0]["kind"] == "keepalive"
    assert rows[0]["severity"] == "critical"
    assert "rebuild" in rows[0]["detail"]["checks"]


def test_verify_keepalive_reports_a_failed_rebuild(tmp_path: Path) -> None:
    # Module level: the check itself, with the keepalive workflow intact and the
    # degraded build failing (stubbed runner) -> not ok, and the reason is named.
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "keepalive.yml").write_text(
        "on:\n  schedule:\n    - cron: '0 7 1 * *'\n  # sig-ops degraded\n"
    )
    (tmp_path / "web").mkdir()

    def failing(cmd, **kw):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")

    result = O.verify_keepalive(repo_root=tmp_path, runner=failing)
    assert result.ok is False
    assert result.checks["workflow"] == "ok"
    assert result.checks["rebuild"].startswith("FAIL")


def test_verify_keepalive_reports_a_missing_or_gutted_workflow(tmp_path: Path) -> None:
    result = O.verify_keepalive(repo_root=tmp_path, runner=lambda *a, **k: None)
    assert result.ok is False
    assert result.checks["workflow"].startswith("FAIL")


def test_committed_keepalive_workflow_is_intact() -> None:
    # The real repo's keepalive.yml still schedules + runs `sig-ops degraded`.
    repo = Path(__file__).resolve().parents[2]
    text = (repo / ".github" / "workflows" / "keepalive.yml").read_text()
    assert "cron:" in text and "sig-ops degraded" in text
    # ...and a keepalive failure is wired to the notifier (OBS.1).
    assert "sig-ops alert" in text and "if: failure()" in text


# --- ACCEPTANCE: no secrets appear in logs --------------------------------------


def test_no_env_secret_reaches_the_ledger_or_log(
    ledger_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("SIG_MUCKROCK_TOKEN", "muck-SECRET-111")
    monkeypatch.setenv("SIG_OBJECT_STORE_SECRET", "r2-SECRET-222")
    monkeypatch.setenv("SIG_ALERT_WEBHOOK_URL", "https://hooks.invalid/T0K3N-path-333")
    rc = cli.main(
        [
            "alert",
            "--kind",
            "test",
            "--message",
            "bad deploy leaked muck-SECRET-111 via https://hooks.invalid/T0K3N-path-333",
        ]
    )
    assert rc == 0
    emitted = ledger_path.read_text() + capsys.readouterr().err
    for secret in ("muck-SECRET-111", "r2-SECRET-222", "T0K3N-path-333"):
        assert secret not in emitted
    assert A.REDACTED in emitted


def test_scrub_secrets_masks_env_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIG_SOME_TOKEN", "tok-xyz")
    assert A.scrub_secrets("value=tok-xyz ok") == f"value={A.REDACTED} ok"
    # A non-secret-looking env var is not masked.
    monkeypatch.setenv("SIG_STAGING_API_URL", "http://127.0.0.1:8000")
    assert A.scrub_secrets("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


def test_webhook_posts_scrubbed_json_and_never_logs_the_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setenv("SIG_ALERT_WEBHOOK_URL", "https://hooks.invalid/SECRET-PATH")
    monkeypatch.setenv("SIG_ALERT_WEBHOOK_TOKEN", "bearer-SECRET")
    posted: list[urllib.request.Request] = []

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, **kw: posted.append(req) or _Resp())
    notifier = A.WebhookNotifier()
    assert notifier.configured
    ok = notifier.send(A.Alert.create("test", "warn", "pwned bearer-SECRET"))
    assert ok is True
    assert len(posted) == 1
    body = posted[0].data.decode()
    assert "bearer-SECRET" not in body and A.REDACTED in body
    assert posted[0].get_header("Authorization") == "Bearer bearer-SECRET"
    out = capsys.readouterr()
    assert "SECRET-PATH" not in out.err + out.out  # the URL itself is never logged


def test_unconfigured_webhook_delivers_nothing_but_the_record_stands(
    ledger_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SIG_ALERT_WEBHOOK_URL", raising=False)
    notifier = A.WebhookNotifier(url="")
    assert not notifier.configured and notifier.send(A.Alert.create("t", "warn", "m")) is False
    # ...while the recorded half never depends on delivery:
    sinks = A.notifiers_from_env(env={}, stream=io.StringIO())
    alert = A.fire(
        A.Alert.create("t", "warn", "recorded anyway"),
        ledger=A.AlertLedger(ledger_path),
        notifiers=sinks,
    )
    assert _read(ledger_path)[0]["message"] == alert.message


# --- units ----------------------------------------------------------------------


def test_alert_ledger_is_append_only(ledger_path: Path) -> None:
    ledger = A.AlertLedger(ledger_path)
    ledger.record(A.Alert.create("a", "warn", "first"))
    first = ledger_path.read_text()
    ledger.record(A.Alert.create("b", "alarm", "second"))
    assert ledger_path.read_text().startswith(first)  # history never rewritten


def test_alert_rejects_an_unknown_severity() -> None:
    with pytest.raises(ValueError):
        A.Alert.create("t", "bogus", "m")


def test_cli_alert_records_and_notifies(ledger_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = cli.main(["alert", "--kind", "operator", "--severity", "warn", "--message", "check"])
    assert rc == 0
    assert _read(ledger_path)[0]["kind"] == "operator"
    assert "SIG-ALERT WARN operator: check" in capsys.readouterr().err


def test_cli_alerts_lists_the_ledger(ledger_path: Path, capsys: pytest.CaptureFixture) -> None:
    cli.main(["alert", "--kind", "k1", "--message", "one"])
    cli.main(["alert", "--kind", "k2", "--message", "two"])
    capsys.readouterr()
    assert cli.main(["alerts", "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert '"k2"' in out and '"k1"' not in out
