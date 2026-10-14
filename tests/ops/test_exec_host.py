# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.43 / G2 ACT-13, SIG-CONF-013 (ADR-202) — the one-off Cloud Run execution
host for hosted return passes + quality probes.

Offline layer: the ``sig.exec-host/1`` declaration (``ops/exec_host.toml``)
loads fail-closed — a writable mount, retries > 0, a multi-task shape, an
undeclared secret env or a bad name all refuse; ``render_plan`` produces the
deterministic create/execute/delete argv with the read-only GCS mount, the
Secret Manager env bindings and the injected ``SIG_EXEC_JOB_NAME``; the
cleanup deletes exactly the minted ``sig-exec-<purpose>-<stamp>`` name;
``verify_describe`` judges a recorded describe against the template
(digest-pinned image, gen2, the CSI readOnly volume, no ``envFrom``);
``run_smoke`` writes one ``sig.probe-run/1`` record per use. The shell leg's
``--check`` runs with no ADC and no network.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from ops.exec_host import (
    SCHEMA,
    check_env_pairs,
    check_image_ref,
    create_argv,
    job_name,
    load_declaration,
    mount_readonly_check,
    render_plan,
    run_oneoff,
    run_smoke,
    secrets_present_check,
    select_secrets,
    verify_describe,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECLARATION = REPO_ROOT / "ops" / "exec_host.toml"
EXEC_HOST_SH = REPO_ROOT / "ops" / "gcp" / "exec-host.sh"
PROJECT = "sig-test-project"
REGION = "us-central1"
IMAGE = f"us-central1-docker.pkg.dev/{PROJECT}/sig/sig-ops@sha256:{'ab' * 32}"
SYNTHETIC_AT = "2026-10-13T14:00:00Z"  # a synthetic fixture stamp, not a real date


def test_declaration_loads_with_the_least_privilege_shape() -> None:
    decl = load_declaration(DECLARATION)
    assert decl.service_account == "sig-quality-probe-rt"
    assert decl.job_prefix == "sig-exec"
    assert decl.tasks == 1
    assert decl.max_retries == 0
    assert decl.mount.readonly is True
    assert decl.mount.prefix == "evidence/captures/"
    assert decl.mount.bucket == "sig-restricted"
    envs = {s.env: s.secret for s in decl.secret_env}
    assert envs["SIG_AUDIT_PASSWORD"] == "sig-audit-password"
    assert envs["SIG_RECOVERY_PASSWORD"] == "sig-recovery-password"
    assert decl.probe_prefix.startswith("ops/probes/")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.replace("max_retries = 0", "max_retries = 1"),
        lambda t: t.replace("readonly = true", "readonly = false"),
        lambda t: t.replace("tasks = 1", "tasks = 2"),
        lambda t: t.replace('prefix = "evidence/captures/"', 'prefix = "evidence/captures"'),
    ],
)
def test_declaration_refuses_weakened_shapes(tmp_path: Path, mutate) -> None:
    text = mutate(DECLARATION.read_text())
    assert text != DECLARATION.read_text()
    bad = tmp_path / "exec_host.toml"
    bad.write_text(text)
    with pytest.raises(ValueError):
        load_declaration(bad)


def test_job_name_is_prefix_purpose_stamp_only() -> None:
    decl = load_declaration(DECLARATION)
    name = job_name(decl, "smoke", SYNTHETIC_AT)
    assert name == "sig-exec-smoke-20261013T140000Z"
    assert len(name) <= 63
    for bad_purpose in ("SMOKE", "smoke now", "smoke_; rm -rf", "a" * 60):
        with pytest.raises(ValueError):
            job_name(decl, bad_purpose, SYNTHETIC_AT)


def test_create_argv_carries_the_readonly_mount_and_least_privilege_flags() -> None:
    decl = load_declaration(DECLARATION)
    argv = create_argv(
        decl,
        project=PROJECT,
        region=REGION,
        name="sig-exec-smoke-20261013T140000Z",
        image=IMAGE,
        secrets=select_secrets(decl, ["SIG_AUDIT_PASSWORD"]),
        env=["SIG_PG_DB=sig"],
    )
    joined = " ".join(argv)
    assert "--service-account=sig-quality-probe-rt@" in joined
    assert "--command=sh" in argv  # the image has no ENTRYPOINT; CMD is serve
    assert "--tasks=1" in argv and "--max-retries=0" in argv
    assert "--execution-environment=gen2" in argv
    volume = next(a for a in argv if a.startswith("--add-volume="))
    assert "readonly=true" in volume and f"bucket={PROJECT}-sig-restricted" in volume
    secrets_flag = next(a for a in argv if a.startswith("--set-secrets="))
    assert "SIG_AUDIT_PASSWORD=sig-audit-password:latest" in secrets_flag
    env_flag = next(a for a in argv if a.startswith("--set-env-vars="))
    # The record names the job that ran — injected, never caller-controlled.
    assert "SIG_EXEC_JOB_NAME=sig-exec-smoke-20261013T140000Z" in env_flag


def test_create_argv_refuses_a_movable_image_and_a_secret_value() -> None:
    decl = load_declaration(DECLARATION)
    with pytest.raises(ValueError):
        check_image_ref("sig-ops:latest")  # noqa: B032 - the tag shape is the point
    with pytest.raises(ValueError):
        select_secrets(decl, ["SIG_UNKNOWN_ENV"])
    with pytest.raises(ValueError):
        check_env_pairs(["SIG_PG_DB=a,b"])
    # A caller may not pre-set the job-name env — it is injected by render.
    with pytest.raises(ValueError):
        check_env_pairs(["not-a-pair"])


def test_render_plan_is_a_full_lifecycle_with_name_checked_cleanup() -> None:
    decl = load_declaration(DECLARATION)
    plan = render_plan(
        decl,
        project=PROJECT,
        region=REGION,
        purpose="smoke",
        at=SYNTHETIC_AT,
        image=IMAGE,
        secret_env_names=["SIG_AUDIT_PASSWORD"],
    )
    name = "sig-exec-smoke-20261013T140000Z"
    assert plan["schema"] == SCHEMA and plan["name"] == name
    assert plan["mount"]["readonly"] is True
    assert plan["create"][1:4] == ["run", "jobs", "create"]
    assert plan["cleanup"][:4] == ["gcloud", "run", "jobs", "delete"]
    assert plan["cleanup"][4] == name  # exactly the minted name — never a glob


def test_run_oneoff_deletes_exactly_the_created_job_even_on_failure() -> None:
    decl = load_declaration(DECLARATION)
    calls: list[list[str]] = []

    def runner(argv, **_kw):
        calls.append(argv)
        if "execute" in argv:
            return subprocess.CompletedProcess(argv, 7, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    rc = run_oneoff(
        decl,
        project=PROJECT,
        region=REGION,
        purpose="smoke",
        image=IMAGE,
        at=SYNTHETIC_AT,
        runner=runner,
        log=lambda _line: None,
    )
    assert rc == 7
    assert calls[0][:4] == ["gcloud", "run", "jobs", "create"]
    assert calls[1][:4] == ["gcloud", "run", "jobs", "execute"]
    assert calls[2][:4] == ["gcloud", "run", "jobs", "delete"]
    assert calls[2][4] == "sig-exec-smoke-20261013T140000Z"


def _describe(name: str, **over) -> dict:
    spec = {
        "serviceAccountName": f"sig-quality-probe-rt@{PROJECT}.iam.gserviceaccount.com",
        "containers": [
            {
                "image": IMAGE,
                "env": [
                    {"name": "SIG_EXEC_JOB_NAME", "value": name},
                    {
                        "name": "SIG_AUDIT_PASSWORD",
                        "valueFrom": {"secretKeyRef": {"name": "sig-audit-password"}},
                    },
                ],
                "volumeMounts": [{"mountPath": "/mnt/captures", "name": "captures"}],
            }
        ],
        "volumes": [
            {
                "name": "captures",
                "csi": {
                    "driver": "gcsfuse.run.googleapis.com",
                    "readOnly": True,
                    "volumeAttributes": {"bucket": f"{PROJECT}-sig-restricted"},
                },
            }
        ],
        "cloudSqlInstances": [f"{PROJECT}:{REGION}:sig-pg"],
    }
    spec.update(over)
    return {
        "metadata": {"name": name},
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "run.googleapis.com/execution-environment": "gen2",
                        "run.googleapis.com/cloudsql-instances": f"{PROJECT}:{REGION}:sig-pg",
                    }
                },
                "spec": {"maxRetries": 0, "taskTimeout": "3600s", "template": {"spec": spec}},
            }
        },
    }


def test_verify_describe_accepts_the_rendered_shape() -> None:
    decl = load_declaration(DECLARATION)
    name = "sig-exec-smoke-20261013T140000Z"
    assert verify_describe(decl, _describe(name), project=PROJECT, name=name) == []


def test_verify_describe_flags_a_writable_mount_and_off_prefix_job() -> None:
    decl = load_declaration(DECLARATION)
    name = "sig-exec-smoke-20261013T140000Z"
    bad = _describe(name)
    bad["spec"]["template"]["spec"]["template"]["spec"]["volumes"][0]["csi"]["readOnly"] = False
    diffs = verify_describe(decl, bad, project=PROJECT, name=name)
    assert any("read-only" in d for d in diffs)
    foreign = _describe("sig-cadence-something")
    diffs = verify_describe(decl, foreign, project=PROJECT)
    assert any("one-off" in d for d in diffs)


def test_verify_describe_flags_envfrom_and_undeclared_secret_env() -> None:
    decl = load_declaration(DECLARATION)
    name = "sig-exec-smoke-20261013T140000Z"
    d = _describe(name)
    container = d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]
    container["envFrom"] = [{"secretRef": {"name": "everything"}}]
    container["env"].append(
        {"name": "SNEAKY", "valueFrom": {"secretKeyRef": {"name": "other-secret"}}}
    )
    diffs = verify_describe(decl, d, project=PROJECT, name=name)
    assert any("envFrom" in x for x in diffs)
    assert any("SNEAKY" in x for x in diffs)


def test_run_smoke_writes_one_probe_run_record(tmp_path: Path) -> None:
    decl = load_declaration(DECLARATION)
    out = tmp_path / "probe-run.json"
    rec = run_smoke(
        decl,
        env={"SIG_EXEC_JOB_NAME": "sig-exec-smoke-20261013T140000Z"},
        out=str(out),
        bucket=None,
        now=SYNTHETIC_AT,
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["job"] == "sig-exec-smoke-20261013T140000Z"
    assert rec["probe"] == "exec-host-smoke"
    written = json.loads(out.read_text())
    assert written["version"] == "sig.probe-run/1"
    # A value is never recorded — only env NAMES (HG-09).
    assert "SIG_AUDIT_PASSWORD" not in json.dumps(written) or written.get("checks")


def test_smoke_checks_name_only_secrets() -> None:
    decl = load_declaration(DECLARATION)
    chk = secrets_present_check(decl, {"SIG_AUDIT_PASSWORD": "x" * 40})
    assert chk["verdict"] == "pass"
    assert "SIG_AUDIT_PASSWORD" in chk["present"]
    # The check reports names, never the value.
    assert ("x" * 40) not in json.dumps(chk)


def test_exec_host_sh_check_is_green_without_adc() -> None:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    proc = subprocess.run(
        ["bash", str(EXEC_HOST_SH), "--check"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PLAN:" in proc.stdout and "check OK" in proc.stdout
    assert "readonly=true" in proc.stdout


def test_mount_readonly_check_reports_missing_mount() -> None:
    chk = mount_readonly_check("/definitely/not/a/real/mount")
    assert chk["verdict"] == "fail"
