# SPDX-License-Identifier: Apache-2.0
"""tests/ops/test_restricted_access.py — P37.4b (SIG-SEC-005/SIG-EVID-012,
ADR-232).

The audited restricted-byte access function (log-first, then fetch), the
scheduled purge of expired log rows, the auditConfig merge, and the named
mutation script's offline plan + gates.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ops.gcs import GcsBucket

from ops import restricted_access as ra

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ops" / "gcp" / "restricted-access.sh"
CONFIG = REPO_ROOT / "ops" / "gcp" / "config.sh"
LIFECYCLE = REPO_ROOT / "ops" / "gcp" / "audit-logs-lifecycle.json"
ALERT_DEF = REPO_ROOT / "ops" / "gcp" / "data-access-alert-policy.json"


class _FakeBucket(GcsBucket):
    """In-memory GcsBucket — no token, no network."""

    def __init__(self, name: str, objects: dict[str, bytes] | None = None) -> None:
        super().__init__(bucket=name, token_provider=lambda: "t", opener=lambda r, t: (200, b""))
        self.store: dict[str, bytes] = dict(objects or {})

    def put_object(self, name: str, body: bytes, *, content_type: str = "") -> str:
        self.store[name] = body
        return name

    def get_object(self, name: str) -> bytes:
        return self.store[name]

    def list_objects(self, prefix: str) -> list[str]:
        return sorted(n for n in self.store if n.startswith(prefix))

    def delete_object(self, name: str, *, generation: int | None = None) -> str:
        del self.store[name]
        return name


NOW = "2026-11-05T22:30:00Z"


# --- the audited access function -------------------------------------------- #


def test_a_restricted_read_appears_in_the_audit_log() -> None:
    """The catalog acceptance shape: a restricted read appears in the audit
    log — the record lands under ops/access-log/ BEFORE the bytes return."""
    bucket = _FakeBucket("p-sig-restricted", {"evidence/captures/c1.bin": b"BYTES"})
    data, record = ra.audited_read(
        bucket,
        "evidence/captures/c1.bin",
        requester="operator",
        purpose="takedown review",
        now=NOW,
    )
    assert data == b"BYTES"
    assert record["schema"] == "sig.restricted-access/1"
    assert record["requester"] == "operator" and record["purpose"] == "takedown review"
    logged = [n for n in bucket.store if n.startswith(ra.LOG_PREFIX)]
    assert len(logged) == 1
    logged_record = ra.parse_access_record(bucket.store[logged[0]])
    assert logged_record == record


def test_log_first_even_when_the_fetch_fails() -> None:
    bucket = _FakeBucket("p-sig-restricted")
    with pytest.raises(KeyError):
        ra.audited_read(bucket, "absent.bin", requester="op", purpose="audit", now=NOW)
    assert any(n.startswith(ra.LOG_PREFIX) for n in bucket.store)


def test_no_unaudited_read() -> None:
    bucket = _FakeBucket("p-sig-restricted", {"o": b"x"})
    for kwargs in ({"requester": "", "purpose": "p"}, {"requester": "r", "purpose": ""}):
        with pytest.raises(ValueError):
            ra.audited_read(bucket, "o", now=NOW, **kwargs)
    assert not any(n.startswith(ra.LOG_PREFIX) for n in bucket.store)


def test_record_name_is_worm_shaped() -> None:
    rec = ra.access_record("b", "o", requester="r", purpose="p", now=NOW)
    name = ra.record_name(rec)
    assert name.startswith(ra.LOG_PREFIX)
    assert name.endswith(".json") and "sig.restricted-access" in name


# --- the scheduled purge ----------------------------------------------------- #


def _log_obj(at: str) -> bytes:
    return json.dumps(
        {
            "schema": ra.SCHEMA,
            "accessed_at": at,
            "requester": "r",
            "purpose": "p",
            "bucket": "b",
            "object": "o",
        }
    ).encode()


def test_purge_deletes_only_expired_rows() -> None:
    fresh = _log_obj("2026-11-01T00:00:00Z")
    old = _log_obj("2026-01-01T00:00:00Z")  # >180d before NOW
    bucket = _FakeBucket(
        "p-sig-restricted",
        {
            f"{ra.LOG_PREFIX}fresh.json": fresh,
            f"{ra.LOG_PREFIX}old.json": old,
        },
    )
    record = ra.run_purge(bucket, now=NOW, apply_=True)
    assert record["schema"] == ra.PURGE_SCHEMA
    assert record["counts"]["deleted"] == 1
    assert record["counts"]["kept"] == 1
    assert f"{ra.LOG_PREFIX}fresh.json" in bucket.store
    assert f"{ra.LOG_PREFIX}old.json" not in bucket.store
    # the sweep itself is audited — a purge record lands under its own prefix
    assert any(n.startswith(ra.PURGE_PREFIX) for n in bucket.store)


def test_purge_plan_mode_deletes_nothing() -> None:
    bucket = _FakeBucket(
        "p-sig-restricted", {f"{ra.LOG_PREFIX}old.json": _log_obj("2026-01-01T00:00:00Z")}
    )
    record = ra.run_purge(bucket, now=NOW, apply_=False)
    assert record["applied"] is False
    assert record["counts"]["deleted"] == 0
    assert record["would_delete"] == [f"{ra.LOG_PREFIX}old.json"]
    assert f"{ra.LOG_PREFIX}old.json" in bucket.store
    assert not any(n.startswith(ra.PURGE_PREFIX) for n in bucket.store)


def test_purge_keeps_and_flags_what_it_cannot_explain() -> None:
    bucket = _FakeBucket(
        "p-sig-restricted",
        {
            f"{ra.LOG_PREFIX}junk.txt": b"not json",
            f"{ra.LOG_PREFIX}bad.json": b'{"schema": "sig.restricted-access/1"}',
        },
    )
    record = ra.run_purge(bucket, now=NOW, apply_=True)
    assert record["counts"]["flagged_unparsed"] == 2
    assert record["counts"]["deleted"] == 0
    assert f"{ra.LOG_PREFIX}junk.txt" in bucket.store


def test_purge_plan_pure() -> None:
    now = datetime(2026, 11, 5, tzinfo=UTC)
    items = [
        ("a", {"accessed_at": (now - timedelta(days=200)).isoformat()}),
        ("b", {"accessed_at": now.isoformat()}),
        ("c", None),
    ]
    plan = ra.purge_plan(items, now=now)
    assert plan.to_delete == ("a",) and plan.kept == ("b",) and plan.flagged == ("c",)


# --- the auditConfig merge ---------------------------------------------------- #


def test_audit_merge_adds_data_access_with_exempted() -> None:
    policy = {"bindings": [], "etag": "x", "version": 1}
    exempted = ra.sa_members("p", ("sig-ingest-rt", "sig-export-rt"))
    merged = ra.merge_audit_config(policy, exempted=exempted)
    ac = next(a for a in merged["auditConfigs"] if a["service"] == "storage.googleapis.com")
    log_types = {c["logType"] for c in ac["auditLogConfigs"]}
    assert {"DATA_READ", "DATA_WRITE"} <= log_types
    for c in ac["auditLogConfigs"]:
        if c["logType"] in ("DATA_READ", "DATA_WRITE"):
            assert "serviceAccount:sig-ingest-rt@p.iam.gserviceaccount.com" in c["exemptedMembers"]
    assert policy == {"bindings": [], "etag": "x", "version": 1}  # input untouched


def test_audit_merge_is_idempotent_and_preserves_others() -> None:
    policy = {
        "auditConfigs": [
            {"service": "allServices", "auditLogConfigs": [{"logType": "ADMIN_READ"}]},
            {
                "service": "storage.googleapis.com",
                "auditLogConfigs": [
                    {"logType": "DATA_READ", "exemptedMembers": ["serviceAccount:other@x"]}
                ],
            },
        ]
    }
    merged = ra.merge_audit_config(
        policy, exempted=["serviceAccount:sig-ingest-rt@p.iam.gserviceaccount.com"]
    )
    merged2 = ra.merge_audit_config(
        merged, exempted=["serviceAccount:sig-ingest-rt@p.iam.gserviceaccount.com"]
    )
    assert merged == merged2
    other = next(a for a in merged["auditConfigs"] if a["service"] == "allServices")
    assert other["auditLogConfigs"] == [{"logType": "ADMIN_READ"}]
    storage = next(a for a in merged["auditConfigs"] if a["service"] == "storage.googleapis.com")
    dr = next(c for c in storage["auditLogConfigs"] if c["logType"] == "DATA_READ")
    assert "serviceAccount:other@x" in dr["exemptedMembers"]  # never loses members


# --- CLI ---------------------------------------------------------------------- #


def test_cli_plan_and_audit_merge(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert ra.main(["plan"]) == 0
    policy = tmp_path / "p.json"
    policy.write_text('{"bindings": [], "version": 1}')
    out = tmp_path / "merged.json"
    assert (
        ra.main(["audit-merge", "--policy", str(policy), "--project", "p", "--out", str(out)]) == 0
    )
    merged = json.loads(out.read_text())
    assert any(a.get("service") == "storage.googleapis.com" for a in merged.get("auditConfigs", []))


def test_cli_read_requires_requester_purpose() -> None:
    assert ra.main(["read", "--object", "o", "--requester", "", "--purpose", "p"]) != 0


# --- the named mutation script ------------------------------------------------- #


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for k in ("SIG_GCP_PROJECT", "SIG_RACC_AUTHOR", "SIG_RACC_NOW"):
        env.pop(k, None)
    env.update(extra or {})
    return env


def _run(args: list[str], extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(extra),
        cwd=str(REPO_ROOT),
    )


def test_check_plans_the_whole_mutation_offline() -> None:
    proc = _run(["--check"])
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    for token in (
        "DATA_READ",
        "DATA_WRITE",
        "storage.googleapis.com",
        "sig-audit-logs",
        "sig-data-access",
        "ENCRYPTED_ONLY",
        "sig-access-log-purge",
        "sig.restricted-access/1",
        "ops/access-log/",
        "lifecycle",
        "sig-ingest-rt",
        "log-volume",
        "sqlpoint",
    ):
        assert token in plan, token


def test_apply_window_guard_and_author_gate() -> None:
    proc = _run(
        ["--apply"],
        {"SIG_RACC_NOW": "2026-11-05T05:30:00Z", "SIG_RACC_AUTHOR": "op", "SIG_GCP_PROJECT": "p"},
    )
    assert proc.returncode == 42 and "QUEUED" in proc.stdout
    proc = _run(["--apply"], {"SIG_RACC_NOW": "2026-11-05T15:30:00Z", "SIG_GCP_PROJECT": "p"})
    assert proc.returncode == 2 and "SIG_RACC_AUTHOR" in (proc.stdout + proc.stderr)


def test_apply_without_project_stays_unarmed() -> None:
    proc = _run(["--apply"], {"SIG_RACC_NOW": "2026-11-05T15:30:00Z", "SIG_RACC_AUTHOR": "op"})
    assert proc.returncode == 2


def test_no_destructive_writes_in_the_leg() -> None:
    text = SCRIPT.read_text()
    for banned in ("buckets delete", "keys destroy", "storage rm "):
        assert banned not in text
    for guard in ("assert_window", "SIG_RACC_AUTHOR", "require_adc"):
        assert guard in text
    cfg = CONFIG.read_text()
    assert 'SIG_RACC_AUTHOR="${SIG_RACC_AUTHOR:-}"' in cfg
    assert "sig-audit-logs" in cfg and "SIG_RACC_EXEMPT_SAS" in cfg


def test_lifecycle_and_alert_def_shapes() -> None:
    rules = json.loads(LIFECYCLE.read_text())["rule"]
    assert rules == [{"action": {"type": "Delete"}, "condition": {"age": 90}}]
    alert = json.loads(ALERT_DEF.read_text())
    assert alert["notificationChannels"][0].startswith("projects/{project}/")
    assert "byte_count" in alert["conditions"][0]["conditionThreshold"]["filter"]
    assert "data_access" in alert["conditions"][0]["conditionThreshold"]["filter"]
    assert "@" not in ALERT_DEF.read_text()  # never an address literal
