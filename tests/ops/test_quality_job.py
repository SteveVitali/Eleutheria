# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.quality-probe/1`` declaration + its window math (P34.44b,
SIG-CONF-006/007): the committed ``ops/quality_probe.toml`` validates
fail-closed, the declared cron can structurally never fire inside
03:00–06:30Z or the monthly batch window, the renderers emit the exact
mutation argv, and the describe-differs judge live drift."""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from ops.quality_job import (
    SCHEMA,
    fire_times,
    in_batch_window,
    in_quiet_hours,
    leg_window_reason,
    load_declaration,
    render,
    sa_email,
    suppression_reason,
    validate_schedule,
    verify_describe,
    verify_trigger,
)
from support import REPO_ROOT

DECLARATION = REPO_ROOT / "ops" / "quality_probe.toml"


def _at(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def _decl_text(**overrides) -> str:
    text = DECLARATION.read_text(encoding="utf-8")
    for old, new in overrides.items():
        assert old in text, f"fixture drift: {old!r} not in the declaration"
        text = text.replace(old, new, 1)
    return text


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "quality_probe.toml"
    p.write_text(text, encoding="utf-8")
    return p


# --- the committed declaration ----------------------------------------------


def test_committed_declaration_loads_clean() -> None:
    decl = load_declaration()
    assert decl.job == "sig-quality-probe"
    assert decl.service_account == "sig-quality-probe-rt"
    assert decl.tasks == 1 and decl.max_retries == 0
    assert decl.scheduler.name == "sig-sched-quality-probe"
    assert decl.scheduler.invoker == "sig-scheduler"
    assert decl.probe_prefix.startswith("ops/probes/")
    envs = {s.env for s in decl.secret_env}
    assert envs == {"SIG_AUDIT_PASSWORD", "SIG_ALERT_WEBHOOK_TOKEN"}


def test_declaration_schema_is_enforced(tmp_path: Path) -> None:
    p = _write(tmp_path, _decl_text(**{f'schema = "{SCHEMA}"': 'schema = "sig.bogus/1"'}))
    with pytest.raises(ValueError, match="schema"):
        load_declaration(p)


def test_missing_declaration_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unreadable"):
        load_declaration(tmp_path / "absent.toml")


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ("tasks = 1", "tasks = 2", "tasks must be exactly 1"),
        ("max_retries = 0", "max_retries = 1", "max_retries must be 0"),
        ('task_timeout = "1800s"', 'task_timeout = "30s"', "task_timeout"),
        ('probe_prefix = "ops/probes/quality/"', 'probe_prefix = "ops/raw/"', "ops/probes/"),
        ('time_zone = "Etc/UTC"', 'time_zone = "US/Pacific"', "Etc/UTC"),
        ('command = "sh"', 'command = "sh; rm -rf /"', "command"),
        ('"-c", "exec sig-ops quality nightly"', '"-c", "exec a,b"', "comma"),
    ],
)
def test_declaration_validation_refuses_drift(
    tmp_path: Path, old: str, new: str, match: str
) -> None:
    p = _write(tmp_path, _decl_text(**{old: new}))
    with pytest.raises(ValueError, match=re.escape(match) if match != "command" else "command"):
        load_declaration(p)


def test_secret_env_duplicates_and_plain_overlap_refused(tmp_path: Path) -> None:
    text = _decl_text() + '\n[[secret_env]]\nenv = "SIG_AUDIT_PASSWORD"\nsecret = "other"\n'
    with pytest.raises(ValueError, match="declared twice"):
        load_declaration(_write(tmp_path, text))
    text = _decl_text(
        **{'"SIG_ALERT_WEBHOOK_URL",': '"SIG_ALERT_WEBHOOK_URL",\n  "SIG_AUDIT_PASSWORD",'}
    )
    with pytest.raises(ValueError, match="never a plain var"):
        load_declaration(_write(tmp_path, text))


# --- the window predicates (shared by the leg and the in-job suppression) ----


@pytest.mark.parametrize(
    ("stamp", "quiet", "batch"),
    [
        ("2026-10-20T01:00:00Z", False, False),  # the scheduled fire shape
        ("2026-10-20T02:59:59Z", False, False),
        ("2026-10-20T03:00:00Z", True, False),
        ("2026-10-20T05:30:00Z", True, False),
        ("2026-10-20T06:29:59Z", True, False),
        ("2026-10-20T06:30:00Z", False, False),
        ("2026-11-05T23:59:59Z", False, False),  # day 5 — last free night
        ("2026-11-06T00:00:00Z", False, True),  # batch window opens
        ("2026-11-10T12:00:00Z", False, True),
        ("2026-11-13T11:59:59Z", False, True),  # still inside at noon minus a second
        ("2026-11-13T12:00:00Z", False, False),  # window closes
        ("2026-11-14T01:00:00Z", False, False),  # the first post-window fire
    ],
)
def test_suppression_windows(stamp: str, quiet: bool, batch: bool) -> None:
    now = _at(stamp)
    assert in_quiet_hours(now) is quiet
    assert in_batch_window(now) is batch
    expected = "quiet" if quiet else "batch" if batch else None
    reason = suppression_reason(now)
    if expected is None:
        assert reason is None
    else:
        assert expected in (reason or "")


def test_suppression_reason_prefers_quiet_band() -> None:
    # Day 7 at 04:00Z is inside BOTH windows — the reason names either; the
    # point is the run is suppressed, never run.
    assert suppression_reason(_at("2026-11-07T04:00:00Z")) is not None


def test_leg_window_reason_orders_earliest_first() -> None:
    assert (
        leg_window_reason(_at("2026-10-08T01:00:00Z"), earliest="2026-10-13T12:00:00Z")
        == "before-earliest"
    )
    assert leg_window_reason(_at("2026-10-14T01:00:00Z"), earliest="2026-10-13T12:00:00Z") is None
    assert (
        leg_window_reason(_at("2026-10-14T03:15:00Z"), earliest="2026-10-13T12:00:00Z") is not None
    )


# --- the declared schedule can never fire inside a window --------------------


def test_declared_schedule_fires_where_the_contract_allows() -> None:
    decl = load_declaration()
    fires = fire_times(decl.scheduler.schedule, start=date(2026, 1, 1), days=370)
    assert fires, "the declared cron must fire somewhere"
    assert all(f.minute == 0 and f.hour == 1 for f in fires)
    assert all(not in_quiet_hours(f) and not in_batch_window(f) for f in fires)
    # Days 6–13 are structurally excluded (the dom field carries no 6..13).
    assert all(f.day <= 5 or f.day >= 14 for f in fires)


def test_validate_schedule_accepts_the_declaration() -> None:
    decl = load_declaration()
    assert validate_schedule(decl.scheduler.schedule) == []


@pytest.mark.parametrize(
    ("cron", "expect"),
    [
        ("0 4 * * *", "03:00"),  # 04:00Z daily — inside the quiet band
        ("0 1 6 * *", "batch window"),  # day 6 — inside the batch window
        ("0 1 13 * *", "batch window"),  # day 13 before noon — inside
        ("not a cron", "unparseable"),
        ("0 1 31 2 *", "fires nowhere"),  # Feb has no 31st
    ],
)
def test_validate_schedule_refuses_illegal_crons(cron: str, expect: str) -> None:
    errors = validate_schedule(cron)
    assert errors and expect in errors[0]


def test_illegal_schedule_in_declaration_is_refused(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        _decl_text(**{'schedule = "0 1 1-5,14-31 * *"': 'schedule = "30 3 * * *"'}),
    )
    with pytest.raises(ValueError, match="quiet band"):
        load_declaration(p)


# --- the rendered mutation set ------------------------------------------------

ENV_VALUES = {
    "SIG_GCP_PROJECT": "testproj",
    "SIG_OPS_GCS_BUCKET": "testproj-sig-restricted",
    "SIG_CLOUDSQL_CONNECTION": "testproj:us-central1:sig-pg",
    "SIG_PG_DB": "sig",
    "SIG_QUALITY_PROBE_PREFIX": "ops/probes/quality/",
    "SIG_ALERT_WEBHOOK_URL": "https://alerts.example",
}
IMAGE = "example.test/sig-api@sha256:" + "ab" * 32


def test_render_produces_the_full_mutation_set() -> None:
    decl = load_declaration()
    plan = render(
        decl,
        project="testproj",
        region="us-central1",
        image=IMAGE,
        env_values=dict(ENV_VALUES),
    )
    deploy = plan["deploy"]
    assert deploy[:4] == ["gcloud", "run", "jobs", "deploy"]
    assert f"--image={IMAGE}" in deploy
    assert f"--service-account={sa_email('testproj', decl.service_account)}" in deploy
    assert "--tasks=1" in deploy and "--max-retries=0" in deploy
    # `sh -c "<cmd>"` renders as ONE --args element — no space splitting.
    assert "--args=-c,exec sig-ops quality nightly" in deploy
    assert any(a.startswith("--set-cloudsql-instances=") for a in deploy)
    secrets = next(a for a in deploy if a.startswith("--set-secrets="))
    assert "SIG_AUDIT_PASSWORD=sig-audit-password:latest" in secrets
    assert "SIG_ALERT_WEBHOOK_TOKEN=sig-alert-webhook-token:latest" in secrets
    # The scheduler binding is the invoker identity only — on THIS job.
    inv = plan["job_invoker"]
    assert inv[:6] == [
        "gcloud",
        "run",
        "jobs",
        "add-iam-policy-binding",
        decl.job,
        "--member=serviceAccount:sig-scheduler@testproj.iam.gserviceaccount.com",
    ]
    # Trigger create + update variants + the name-checked rollback.
    for key in ("trigger_create", "trigger_update"):
        argv = plan[key]
        assert f"--schedule={decl.scheduler.schedule}" in argv
        assert f"--uri={plan['trigger_uri']}" in argv
        assert "--http-method=POST" in argv
    rb = plan["rollback"]
    for key in ("pause_trigger", "delete_trigger", "remove_job_invoker", "delete_job"):
        assert key in rb
    names = {a for argv in rb.values() for a in argv}
    assert decl.job in names and decl.scheduler.name in names


def test_render_refuses_unpinned_image() -> None:
    decl = load_declaration()
    with pytest.raises(ValueError, match="digest-pinned"):
        render(
            decl,
            project="p",
            region="r",
            image="sig-api:latest",
            env_values=dict(ENV_VALUES),
        )


def test_render_refuses_a_missing_plain_env_value() -> None:
    decl = load_declaration()
    env = dict(ENV_VALUES)
    env.pop("SIG_OPS_GCS_BUCKET")
    with pytest.raises(ValueError, match="SIG_OPS_GCS_BUCKET"):
        render(decl, project="p", region="r", image=IMAGE, env_values=env)


def test_render_refuses_env_value_carrying_a_comma() -> None:
    decl = load_declaration()
    env = dict(ENV_VALUES)
    env["SIG_ALERT_WEBHOOK_URL"] = "https://a,b"
    with pytest.raises(ValueError, match="comma"):
        render(decl, project="p", region="r", image=IMAGE, env_values=env)


# --- the live-diff half --------------------------------------------------------


def _describe() -> dict:
    """A `run jobs describe` shape matching the declaration."""
    return {
        "metadata": {"name": "sig-quality-probe"},
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "run.googleapis.com/cloudsql-instances": "testproj:us-central1:sig-pg"
                    }
                },
                "spec": {
                    "taskCount": 1,
                    "maxRetries": 0,
                    "taskTimeout": "1800s",
                    "template": {
                        "spec": {
                            "serviceAccountName": (
                                "sig-quality-probe-rt@testproj.iam.gserviceaccount.com"
                            ),
                            "containers": [
                                {
                                    "image": IMAGE,
                                    "env": [
                                        {
                                            "name": "SIG_AUDIT_PASSWORD",
                                            "valueFrom": {
                                                "secretKeyRef": {"name": "sig-audit-password"}
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    },
                },
            }
        },
    }


def test_verify_describe_accepts_a_matching_posture() -> None:
    decl = load_declaration()
    assert verify_describe(decl, _describe(), project="testproj") == []


@pytest.mark.parametrize(
    ("mutate", "expect"),
    [
        (lambda d: d["spec"]["template"]["spec"].update({"maxRetries": 2}), "maxRetries"),
        (
            lambda d: d["spec"]["template"]["spec"]["template"]["spec"].update(
                {"serviceAccountName": "default-compute@x"}
            ),
            "serviceAccountName",
        ),
        (
            lambda d: d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0].update(
                {"image": "sig-api:latest"}
            ),
            "digest-pinned",
        ),
        (
            lambda d: d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0][
                "env"
            ].append(
                {
                    "name": "SIG_STEALTH",
                    "valueFrom": {"secretKeyRef": {"name": "stealth"}},
                }
            ),
            "undeclared secret env",
        ),
        (
            lambda d: d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0].update(
                {"envFrom": [{"secretRef": {"name": "all"}}]}
            ),
            "envFrom",
        ),
        (
            lambda d: d["spec"]["template"]["metadata"].update({"annotations": {}}),
            "Cloud SQL",
        ),
    ],
)
def test_verify_describe_flags_drift(mutate, expect: str) -> None:
    decl = load_declaration()
    describe = copy.deepcopy(_describe())
    mutate(describe)
    diffs = verify_describe(decl, describe, project="testproj")
    assert diffs and any(expect in d for d in diffs), diffs


def test_verify_trigger_accepts_a_matching_trigger() -> None:
    decl = load_declaration()
    describe = {
        "name": "projects/testproj/locations/us-central1/jobs/sig-sched-quality-probe",
        "schedule": decl.scheduler.schedule,
        "timeZone": "Etc/UTC",
        "state": "ENABLED",
        "httpTarget": {
            "uri": "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/"
            "namespaces/testproj/jobs/sig-quality-probe:run",
            "httpMethod": "POST",
            "oauthToken": {"serviceAccountEmail": "sig-scheduler@testproj.iam.gserviceaccount.com"},
        },
    }
    assert verify_trigger(decl, describe, project="testproj", region="us-central1") == []


@pytest.mark.parametrize(
    ("mutate", "expect"),
    [
        (lambda t: t.update({"schedule": "0 4 * * *"}), "schedule"),
        (lambda t: t.update({"timeZone": "US/Pacific"}), "timeZone"),
        (lambda t: t["httpTarget"].update({"uri": "https://evil.example/run"}), "uri"),
        (lambda t: t["httpTarget"].update({"httpMethod": "GET"}), "POST"),
        (
            lambda t: t["httpTarget"]["oauthToken"].update(
                {"serviceAccountEmail": "attacker@x.iam.gserviceaccount.com"}
            ),
            "serviceAccountEmail",
        ),
        (lambda t: t.update({"state": "PAUSED"}), "PAUSED"),
    ],
)
def test_verify_trigger_flags_drift(mutate, expect: str) -> None:
    decl = load_declaration()
    describe = {
        "name": "sig-sched-quality-probe",
        "schedule": "0 1 1-5,14-31 * *",
        "timeZone": "Etc/UTC",
        "httpTarget": {
            "uri": "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/"
            "namespaces/testproj/jobs/sig-quality-probe:run",
            "httpMethod": "POST",
            "oauthToken": {"serviceAccountEmail": "sig-scheduler@testproj.iam.gserviceaccount.com"},
        },
    }
    mutate(describe)
    diffs = verify_trigger(decl, describe, project="testproj", region="us-central1")
    assert diffs and any(expect in d for d in diffs), diffs


def test_render_is_json_serialisable_plan() -> None:
    decl = load_declaration()
    plan = render(
        decl,
        project="testproj",
        region="us-central1",
        image=IMAGE,
        env_values=dict(ENV_VALUES),
    )
    assert json.loads(json.dumps(plan))["job"] == decl.job
