# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.43 / SIG-CONF-013 (ADR-202) — the IAM declaration's `exec` leg.

The declaration gains a fourth leg for the ephemeral execution host:
``[[oneoff]]`` models the ``sig-exec-*`` job family on
``sig-quality-probe-rt``; ``plan --leg exec`` renders the identity +
exactly its bindings (cloudsql client, the two prefix-conditioned storage
grants — objectViewer on ``evidence/captures/``, objectCreator on
``ops/probes/`` — and the three secret accessors: the two DB-logins plus
P34.44b's ``sig-alert-webhook-token`` on the shared identity) and nothing
else;
``diff --leg exec`` judges only its own identities and flags a leaked
``sig-exec-*`` job at rest; a conditioned grant names its
``condition_description`` and stays confined to CONDITIONABLE_ROLES.
"""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest
from ops.iam_identities import (
    Snapshot,
    condition_expression,
    diff_snapshot,
    load_cadence,
    load_declaration,
    plan_steps,
    sa_email,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECLARATION = REPO_ROOT / "ops" / "iam_identities.toml"
CADENCE = REPO_ROOT / "ops" / "cadence.toml"
PROJECT = "sig-test-project"
EXEC_SA = "sig-quality-probe-rt"
EXEC_EMAIL = sa_email(PROJECT, EXEC_SA)
EXEC_MEMBER = f"serviceAccount:{EXEC_EMAIL}"


@pytest.fixture(scope="module")
def decl():
    return load_declaration(DECLARATION)


@pytest.fixture(scope="module")
def cadence():
    return load_cadence(CADENCE)


def test_the_oneoff_family_is_declared_on_the_probe_identity(decl) -> None:
    assert len(decl.oneoffs) == 1
    one = decl.oneoffs[0]
    assert one.name == "sig-exec" and one.job_prefix == "sig-exec"
    assert one.service_account == EXEC_SA


def test_exec_plan_is_identity_plus_exactly_its_bindings(decl, cadence) -> None:
    steps = plan_steps(decl, PROJECT, "us-central1", leg="exec", cadence=cadence)
    creates = [s for s in steps if s.phase == "identities"]
    assert [s.command[4] for s in creates] == [EXEC_SA]
    binding_cmds = [" ".join(s.command) for s in steps if s.phase == "bindings"]
    text = "\n".join(binding_cmds)
    assert "roles/cloudsql.client" in text
    assert "roles/storage.objectViewer" in text
    assert "roles/storage.objectCreator" in text
    assert "roles/secretmanager.secretAccessor" in text
    assert "sig-audit-password" in text and "sig-recovery-password" in text
    # The two conditioned grants carry the byte-exact prefix expressions.
    want_read = condition_expression(PROJECT, "sig-restricted", "evidence/captures/")
    want_write = condition_expression(PROJECT, "sig-restricted", "ops/probes/")
    assert want_read in text and want_write in text
    # No service/job/invoker/editor/cadence step — the leg is scoped.
    assert not any("run services update" in t or "run jobs update" in t for t in binding_cmds)
    # identity + cloudsql + the two conditioned bucket grants + the three
    # secret accessors (sig-audit-password, sig-recovery-password +
    # P34.44b's sig-alert-webhook-token on the shared identity)
    assert len(steps) == 1 + 6  # exactly the declared set
    assert all(EXEC_MEMBER in " ".join(s.command) for s in steps if s.phase == "bindings")


def test_exec_plan_never_renders_an_unconditioned_storage_grant(decl, cadence) -> None:
    for s in plan_steps(decl, PROJECT, "us-central1", leg="exec", cadence=cadence):
        cmd = " ".join(s.command)
        if "storage" in cmd and "objectViewer" in cmd or "objectCreator" in cmd:
            assert "--condition-expression=" in cmd, cmd


def _exec_posture_snapshot(decl) -> Snapshot:
    """The snapshot the exec leg produces: its identity + its declared bindings."""
    restricted = {"bindings": []}
    for b in decl.bucket_roles:
        if b.service_account != EXEC_SA:
            continue
        binding = {"role": b.role, "members": [EXEC_MEMBER]}
        if b.condition_title:
            binding["condition"] = {
                "title": b.condition_title,
                "expression": condition_expression(PROJECT, b.bucket, b.condition_prefix or ""),
            }
        restricted["bindings"].append(binding)
    secret_policies = {}
    for s in decl.secrets:
        if EXEC_SA in s.consumers:
            secret_policies[s.name] = {
                "bindings": [
                    {"role": "roles/secretmanager.secretAccessor", "members": [EXEC_MEMBER]}
                ]
            }
    project_bindings = [
        {"role": r.role, "members": [EXEC_MEMBER]}
        for r in decl.project_roles
        if r.service_account == EXEC_SA
    ]
    return Snapshot(
        service_accounts={EXEC_EMAIL},
        project_policy={"bindings": project_bindings},
        bucket_policies={"sig-restricted": restricted},
        secret_policies=secret_policies,
        service_describes={},
        service_policies={},
        job_describes={},
        scheduler_describes={},
        run_jobs=set(),
        compute_sa=None,
    )


def test_exec_diff_is_clean_on_its_own_posture(decl, cadence) -> None:
    snap = _exec_posture_snapshot(decl)
    assert diff_snapshot(decl, snap, PROJECT, cadence=cadence, leg="exec") == []


def test_exec_diff_flags_a_leaked_oneoff_job(decl, cadence) -> None:
    snap = _exec_posture_snapshot(decl)
    leaked = dataclasses.replace(snap, run_jobs={"sig-exec-smoke-20261013T140000Z"})
    diffs = diff_snapshot(decl, leaked, PROJECT, cadence=cadence, leg="exec")
    assert any("leaked one-off exec job" in d for d in diffs)


def test_exec_diff_ignores_other_legs_jobs(decl, cadence) -> None:
    snap = _exec_posture_snapshot(decl)
    ok = dataclasses.replace(snap, run_jobs={"sig-ingest-okc", "sig-materialize"})
    assert diff_snapshot(decl, ok, PROJECT, cadence=cadence, leg="exec") == []


def test_exec_diff_flags_a_missing_conditioned_binding(decl, cadence) -> None:
    snap = _exec_posture_snapshot(decl)
    empty = dataclasses.replace(snap, bucket_policies={"sig-restricted": {"bindings": []}})
    diffs = diff_snapshot(decl, empty, PROJECT, cadence=cadence, leg="exec")
    assert any("conditioned bucket binding" in d for d in diffs)


def test_exec_diff_flags_a_wrong_condition_expression(decl, cadence) -> None:
    snap = _exec_posture_snapshot(decl)
    bad = {"bindings": []}
    for b in snap.bucket_policies["sig-restricted"]["bindings"]:
        b = dict(b)
        if "condition" in b:
            b["condition"] = dict(b["condition"])
            b["condition"]["expression"] = b["condition"]["expression"].replace(
                "captures", "captures/../ops"
            )
        bad["bindings"].append(b)
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, bucket_policies={"sig-restricted": bad}),
        PROJECT,
        cadence=cadence,
        leg="exec",
    )
    assert any("different expression" in d for d in diffs)


def test_jobs_leg_does_not_judge_the_exec_bindings(decl, cadence) -> None:
    """Mid-stack honesty: a snapshot holding the jobs posture but none of the
    exec leg's bindings is clean for `--leg jobs` — the exec leg owns them."""
    # No sig-quality-probe-rt anywhere: not in SAs, no bindings, no secrets.
    snap = Snapshot(
        service_accounts=set(),
        project_policy={"bindings": []},
        bucket_policies={"sig-restricted": {"bindings": []}, "sig-web": {"bindings": []}},
        secret_policies={},
        service_describes={},
        service_policies={},
        job_describes={},
        scheduler_describes={},
        run_jobs=set(),
        compute_sa=None,
    )
    diffs = diff_snapshot(decl, snap, PROJECT, cadence=cadence, leg="jobs")
    # Exec-leg resources are absent but never flagged as missing exec work —
    # any diffs present belong to the jobs leg's own scope (missing class SAs
    # etc.), which this minimal snapshot does exercise: assert none name the
    # exec family.
    assert not any("sig-exec" in d for d in diffs)
    assert not any("sig-audit-password" in d or "sig-recovery-password" in d for d in diffs)


def test_a_condition_on_an_unlisted_role_refuses_to_load(tmp_path: Path) -> None:
    text = DECLARATION.read_text()
    text = text.replace(
        'role = "roles/storage.objectViewer"\ncondition_title = "p34-43-captures-readonly"',
        'role = "roles/storage.objectAdmin"\ncondition_title = "p34-43-captures-readonly"',
    )
    bad = tmp_path / "iam_identities.toml"
    bad.write_text(text)
    with pytest.raises(ValueError):
        load_declaration(bad)


def test_a_conditioned_grant_without_a_description_refuses(tmp_path: Path) -> None:
    import re

    text = DECLARATION.read_text()
    text = re.sub(r'condition_description = "[^"]*"\n', "", text, count=1)
    bad = tmp_path / "iam_identities.toml"
    bad.write_text(text)
    with pytest.raises(ValueError):
        load_declaration(bad)


def test_sig_ops_iam_plan_renders_the_exec_leg() -> None:
    proc = subprocess.run(
        ["uv", "run", "sig-ops", "iam", "plan", "--leg", "exec"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "sig-quality-probe-rt" in proc.stdout
    assert "evidence/captures/" in proc.stdout
