# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.42b / G1-01, F-272 (SIG-SEC-007, AR-8) — least-privilege identities for
the whole Cloud Run job fleet + the roles/editor removal.

Offline layer (fixture-verified): the ``sig.iam-identities/1`` declaration's
job → class map resolves every live job deterministically against
``ops/cadence.toml`` and fails closed on drift (a double-claimed job, an
unclaimed cadence job, a conditioned grant on the wrong role, a bound
``reserved`` identity, a missing ``expected_job_count``); ``sig-ops iam plan
--leg jobs`` renders the ordered leg — identities → bindings (incl. the one
conditioned captures-prefix grant, ADR-201) → 98 same-image job updates →
scheduler/sig-alerts invokers → the editor removal LAST — with per-step
rollbacks; ``iam diff --leg jobs`` judges a recorded snapshot (jobs on their
class identities, schedulers signing as sig-scheduler, the editor binding
gone); ``check-revisions`` gates every job's image. The shell leg's
``--check`` plan, the OM-19 window guard (exit 42 inside the AR-3 freeze or
the 03:00–06:30Z band, the ADC gate past it), and the fail-closed
running-execution guard run with no ADC and no production mutation.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
from pathlib import Path

import pytest
from ops.iam_identities import (
    BASIC_ROLES,
    RUN_INVOKER_ROLE,
    Snapshot,
    check_same_image,
    condition_expression,
    diff_snapshot,
    load_cadence,
    load_declaration,
    plan_steps,
    resolve_job_map,
    sa_email,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECLARATION = REPO_ROOT / "ops" / "iam_identities.toml"
IAM_JOBS_SH = REPO_ROOT / "ops" / "gcp" / "iam-job-identities.sh"
PROJECT = "sig-test-project"
COMPUTE_SA = "12345-compute@developer.gserviceaccount.com"
COMPUTE_MEMBER = f"serviceAccount:{COMPUTE_SA}"

# Clock values injected as SIG_IAM_JOBS_NOW into the window-guard apply tests
# (future-ok: scheduled — they reproduce the contract window offline; no
# apply ever runs). SYNTHETIC_ names exempt them under B4 R5.
SYNTHETIC_INSIDE_FREEZE = "2026-10-08T14:00:00Z"  # inside AR-3 → queue exit 42
SYNTHETIC_PAST_WINDOW = "2026-10-14T14:00:00Z"  # past the window → ADC gate
SYNTHETIC_0330_BAND = "2026-10-14T03:30:00Z"  # the excluded 03:00–06:30Z band


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "SIG_GCP_PROJECT"}
    env.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    env["CLOUDSDK_CONFIG"] = "/nonexistent-sig-adc"
    env["SIG_GCP_PROJECT"] = PROJECT
    env.update(extra)
    return env


def _run(script: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(**env),
        cwd=str(REPO_ROOT),
    )


@pytest.fixture(scope="module")
def decl():
    return load_declaration(DECLARATION)


@pytest.fixture(scope="module")
def cadence():
    return load_cadence()


@pytest.fixture(scope="module")
def job_map(decl, cadence):
    return resolve_job_map(decl, cadence)


CLASS_SA = {
    "ingest": "sig-ingest-rt",
    "probe": "sig-probe-rt",
    "export": "sig-export-rt",
    "materialize": "sig-materialize-rt",
}


# --- the job → class map ------------------------------------------------------


def test_job_map_covers_every_live_job_exactly_once(decl, cadence, job_map) -> None:
    # G1-C07's 2026-09-30 read: 88 jobs — 70 per-source + 8 camreg batches +
    # P35.6/ACQ-01 adds the ten sig-ingest-r11-* batch jobs (created paused):
    # 88 -> 98.
    # sig-probe + 3 manual ingest + sig-export + sig-materialize + 4 cruft
    # egress probes (P35.1b deletes them; until then they hold probe-class
    # grants).
    assert len(job_map) == 98
    assert decl.expected_job_count == 98
    names = {s["job"] for s in cadence.get("sources", [])}
    names |= {b["job"] for b in cadence.get("batches", [])}
    names.add((cadence.get("probes") or {}).get("job"))
    assert set(names) <= set(job_map)
    for _job, cls in job_map.items():
        assert cls in CLASS_SA
    assert job_map["sig-probe"] == "probe"
    assert job_map["sig-export"] == "export"
    assert job_map["sig-materialize"] == "materialize"
    for cruft in (
        "aspi-egress-probe",
        "ccops-sf-egress-probe",
        "muckrock-egress-probe",
        "okc-doc-egress-probe",
    ):
        assert job_map[cruft] == "probe", cruft
    for job in names:
        assert job_map[job] == ("probe" if job == "sig-probe" else "ingest"), job


def test_every_class_binds_a_declared_non_reserved_sa(decl) -> None:
    reserved = {s.id for s in decl.service_accounts if s.reserved}
    for cls in decl.job_classes:
        assert cls.service_account in {s.id for s in decl.service_accounts}
        assert cls.service_account not in reserved
        assert cls.name in CLASS_SA
        assert cls.service_account == CLASS_SA[cls.name]


def test_job_map_fails_closed_on_drift(decl, tmp_path: Path) -> None:
    base = DECLARATION.read_text(encoding="utf-8")
    bad = tmp_path / "bad.toml"
    # A job claimed by two classes refuses.
    bad.write_text(base.replace('jobs = ["sig-export"]', 'jobs = ["sig-export", "sig-probe"]'))
    with pytest.raises(ValueError, match="claimed by both"):
        resolve_job_map(load_declaration(bad), load_cadence())
    # A cadence-owned job claimed by no class refuses (drop the probe flag).
    bad.write_text(base.replace("probes = true", "probes = false", 1))
    with pytest.raises(ValueError, match="claimed by no class"):
        resolve_job_map(load_declaration(bad), load_cadence())
    # A duplicate explicit job inside one class refuses.
    manual = 'jobs = ["sig-replay-ingest", "sig-sink-bench", "sig-ingest-resume-test"]'
    bad.write_text(
        base.replace(
            manual,
            'jobs = ["sig-replay-ingest", "sig-replay-ingest", '
            '"sig-sink-bench", "sig-ingest-resume-test"]',
        )
    )
    with pytest.raises(ValueError, match="listed twice"):
        load_declaration(bad)


def test_no_ingest_identity_ever_holds_unconditional_delete(decl) -> None:
    # SIG-STORE-048: writers hold no object-delete. The ONLY storage grant
    # that can carry delete permission is the conditioned objectUser binding
    # on the captures prefix (ADR-201) — scoped, titled, and never
    # objectAdmin/objectUser-without-condition. P34.43 adds the exec leg's
    # conditioned grants (ADR-202): objectViewer/objectCreator carry no
    # delete permission at all, so their conditions scope READ/CREATE only.
    # (ADR-201's third trigger fired on this widening — evaluation appended.)
    exec_conditions = {
        ("p34-43-captures-readonly", "evidence/captures/"),
        ("p34-43-probe-records", "ops/probes/"),
    }
    for b in decl.bucket_roles:
        assert b.role not in BASIC_ROLES
        if b.role in {"roles/storage.objectUser", "roles/storage.objectAdmin"}:
            assert b.service_account == "sig-ingest-rt"
            assert b.bucket == "sig-restricted"
            assert b.condition_title == "p34-42b-capture-rewrite"
            assert b.condition_prefix == "evidence/captures/"
            assert b.role == "roles/storage.objectUser"
        elif (b.condition_title, b.condition_prefix) in exec_conditions:
            assert b.service_account == "sig-quality-probe-rt"
            assert b.bucket == "sig-restricted"
            # objectViewer/objectCreator hold no delete — the exec identity
            # can never remove or overwrite any object anywhere.
            assert b.role in {"roles/storage.objectViewer", "roles/storage.objectCreator"}
        else:
            assert b.condition_title is None


def test_declaration_rejects_a_conditioned_grant_on_the_wrong_role(
    tmp_path: Path,
) -> None:
    base = DECLARATION.read_text(encoding="utf-8")
    bad = tmp_path / "bad.toml"
    bad.write_text(
        base.replace(
            'role = "roles/storage.objectUser"',
            'role = "roles/storage.objectAdmin"',
        )
    )
    with pytest.raises(ValueError, match="a condition on"):
        load_declaration(bad)
    # A condition on a role outside CONDITIONABLE_ROLES refuses — the
    # allow-list is the recorded set (objectUser + the two P34.43 delete-free
    # roles, ADR-202); a legacy writer stays refused.
    viewer_role = 'role = "roles/storage.objectViewer"'
    viewer_block = viewer_role + '\n\n[[bucket_role]]\nservice_account = "sig-ingest-rt"'
    bad.write_text(
        base.replace(
            viewer_block,
            'role = "roles/storage.legacyBucketWriter"'
            + '\ncondition_title = "x"\ncondition_prefix = "ops/"'
            + '\ncondition_description = "x"'
            + '\n\n[[bucket_role]]\nservice_account = "sig-ingest-rt"',
            1,
        )
    )
    with pytest.raises(ValueError, match="a condition on"):
        load_declaration(bad)


def test_declaration_rejects_a_bound_reserved_identity(tmp_path: Path) -> None:
    base = DECLARATION.read_text(encoding="utf-8")
    bad = tmp_path / "bad.toml"
    # sig-scheduler is the declared invoker member — binding it to a class
    # makes it a workload identity, which P25.7 forbids.
    bad.write_text(
        base.replace(
            'service_account = "sig-materialize-rt"\njobs = ["sig-materialize"]',
            'service_account = "sig-scheduler"\njobs = ["sig-materialize"]',
        )
    )
    with pytest.raises(ValueError, match="reserved|never a runtime|workload"):
        load_declaration(bad)
    # A non-reserved SA bound to nothing refuses.
    bad.write_text(base.replace("reserved = true", "reserved = false", 1))
    with pytest.raises(ValueError, match="bound to no workload"):
        load_declaration(bad)
    # Removing expected_job_count with classes present refuses.
    bad.write_text(base.replace("expected_job_count = 98", ""))
    with pytest.raises(ValueError, match="expected_job_count"):
        load_declaration(bad)


def test_condition_expression_is_prefix_scoped() -> None:
    expr = condition_expression(PROJECT, "sig-restricted", "evidence/captures/")
    assert expr == (
        "resource.name.startsWith("
        "'projects/_/buckets/sig-test-project-sig-restricted/objects/evidence/captures/')"
    )


# --- the plan -----------------------------------------------------------------


def test_jobs_leg_plan_covers_the_contract_mutation_list(decl, cadence) -> None:
    steps = plan_steps(decl, PROJECT, "us-central1", cadence, "jobs")
    flat = "\n".join(" ".join(s.command) for s in steps)
    phases = [s.phase for s in steps]
    # Ordering: identities → bindings → jobs → invokers → editor.
    order = ["identities", "bindings", "jobs", "invokers", "editor"]
    assert phases == sorted(phases, key=order.index)
    # (1) the four class SAs + the four reserved identities are created.
    for sa in (
        "sig-ingest-rt",
        "sig-probe-rt",
        "sig-export-rt",
        "sig-materialize-rt",
        "sig-quality-probe-rt",
        "sig-release-rt",
        "sig-status-rt",
        "sig-scheduler",
    ):
        assert f"service-accounts create {sa}" in flat, sa
    # The services' identities are NOT this leg's.
    assert "service-accounts create sig-api-rt" not in flat
    # (2) least-privilege bindings per class; the conditioned grant present.
    # P35.1a adds the probe runtime's two live-diff viewers (run.viewer +
    # cloudscheduler.viewer — SIG-OPS-005, ADR-174): 4 -> 6.
    assert flat.count("projects add-iam-policy-binding") == 6
    assert "--condition-title=p34-42b-capture-rewrite" in flat
    assert "objects/evidence/captures/" in flat
    # Five job-only secrets drop the default-compute accessor.
    assert flat.count("secrets remove-iam-policy-binding") == 5
    # (3) 98 same-image job updates — identity only, never an image.
    job_updates = [s for s in steps if s.phase == "jobs"]
    assert len(job_updates) == 98
    for s in job_updates:
        assert "run jobs update" in " ".join(s.command)
        assert "--service-account=" in " ".join(s.command)
        assert "--image" not in " ".join(s.command)
        assert "run deploy" not in " ".join(s.command)
        assert s.rollback, s.note
    # (4) the scheduler invoker move: run.invoker on each scheduled job.
    sched = [s for s in steps if "run jobs add-iam-policy-binding" in " ".join(s.command)]
    # 70 source + 8 camreg-batch + 1 probe triggers, +10 P35.6 r11-* batch
    # triggers — 79 -> 89 scheduled-job invoker bindings.
    assert len(sched) == 89
    for s in sched:
        assert "--role=roles/run.invoker" in " ".join(s.command)
        assert "sig-scheduler@" in " ".join(s.command)
    # (5) sig-alerts: grant the declared callers (sig-probe-rt +
    # P34.44b's sig-quality-probe-rt) before the revokes.
    grants = [s for s in steps if "services add-iam-policy-binding" in " ".join(s.command)]
    assert len(grants) == 2 and all("sig-alerts" in " ".join(g.command) for g in grants)
    revokes = [s for s in steps if "services remove-iam-policy-binding" in " ".join(s.command)]
    assert len(revokes) == 2  # allUsers + default-compute
    assert steps.index(grants[0]) < min(steps.index(r) for r in revokes)
    # (6) roles/editor removal — the LAST mutation step.
    assert steps[-1].phase == "editor"
    assert "remove-iam-policy-binding" in " ".join(steps[-1].command)
    assert "--role=roles/editor" in " ".join(steps[-1].command)
    for role in BASIC_ROLES - {"roles/editor"}:
        assert role not in flat
    # roles/editor appears only on the removal line — never on a grant.
    for line in flat.splitlines():
        if "roles/editor" in line:
            assert "remove-iam-policy-binding" in line


def test_services_leg_plan_is_unchanged(decl, cadence) -> None:
    # The P34.42a leg keeps its exact step list — the declaration grew, the
    # services leg didn't.
    steps = plan_steps(decl, PROJECT, "us-central1", cadence, "services")
    phases = [s.phase for s in steps]
    assert phases.count("identities") == 3
    assert "jobs" not in phases and "editor" not in phases
    flat = "\n".join(" ".join(s.command) for s in steps)
    assert "run jobs update" not in flat


# --- the recorded-snapshot diff (leg=jobs) --------------------------------------


def _post_jobs_snapshot(decl, cadence, job_map) -> Snapshot:
    """The post-leg posture: every identity exists, every grant in place,
    every job on its class SA, schedulers signing as sig-scheduler, the
    editor binding gone."""
    project = PROJECT
    emails = {sa.id: sa_email(project, sa.id) for sa in decl.service_accounts}
    class_sa = {c.name: c.service_account for c in decl.job_classes}

    project_bindings = [
        {
            "role": r.role,
            "members": [f"serviceAccount:{emails[r.service_account]}"],
        }
        for r in decl.project_roles
    ]
    restricted_bindings = []
    for b in decl.bucket_roles:
        if b.bucket != "sig-restricted":
            continue
        binding: dict = {
            "role": b.role,
            "members": [f"serviceAccount:{emails[b.service_account]}"],
        }
        if b.condition_title:
            binding["condition"] = {
                "title": b.condition_title,
                "expression": condition_expression(project, b.bucket, b.condition_prefix or ""),
            }
        restricted_bindings.append(binding)
    web_bindings = [
        {
            "role": "roles/storage.objectViewer",
            "members": [f"serviceAccount:{emails['sig-web-rt']}", "allUsers"],
        }
    ] + [
        # P35.1a: declared sig-web bucket roles beyond the web-rt reader grant
        # (the probe runtime's live-diff legacyBucketReader).
        {"role": b.role, "members": [f"serviceAccount:{emails[b.service_account]}"]}
        for b in decl.bucket_roles
        if b.bucket == "sig-web"
    ]
    other_bucket_policies: dict[str, dict] = {}
    for b in decl.bucket_roles:
        if b.bucket in ("sig-restricted", "sig-web"):
            continue
        other_bucket_policies.setdefault(b.bucket, {"bindings": []})["bindings"].append(
            {
                "role": b.role,
                "members": [f"serviceAccount:{emails[b.service_account]}"],
            }
        )
    secret_policies = {}
    for s in decl.secrets:
        members = [
            f"serviceAccount:{emails[c]}"
            for c in s.consumers
            if c not in ("default-compute", "operator")
        ]
        if "default-compute" in s.consumers:
            members.append(COMPUTE_MEMBER)
        if "operator" in s.consumers:
            members.append("user:operator@example.invalid")
        secret_policies[s.name] = {
            "bindings": [{"role": "roles/secretmanager.secretAccessor", "members": members}]
        }
    job_describes = {
        job: {
            "spec": {
                "template": {
                    "spec": {
                        "serviceAccountName": emails[class_sa[cls]],
                        "containers": [{"image": "img@sha256:" + "ab" * 32}],
                    }
                }
            }
        }
        for job, cls in job_map.items()
    }
    sched = {
        job: {"httpTarget": {"oauthToken": {"serviceAccountEmail": emails["sig-scheduler"]}}}
        for job in set(
            [s["job"] for s in cadence.get("sources", [])]
            + [b["job"] for b in cadence.get("batches", [])]
            + [(cadence.get("probes") or {}).get("job")]
        )
        if job
    }
    return Snapshot(
        service_accounts=set(emails.values()),
        project_policy={"bindings": project_bindings},
        bucket_policies={
            "sig-restricted": {"bindings": restricted_bindings},
            "sig-web": {"bindings": web_bindings},
            **other_bucket_policies,
        },
        secret_policies=secret_policies,
        service_describes={},
        service_policies={
            "sig-alerts": {
                "bindings": [
                    {
                        "role": RUN_INVOKER_ROLE,
                        # every member the jobs-leg [[invoker]] grants —
                        # sig-probe-rt + P34.44b's sig-quality-probe-rt
                        "members": [
                            f"serviceAccount:{emails[g]}"
                            for g in decl.invoker_rule("sig-alerts", "jobs").grant
                            if g != "default-compute"
                        ],
                    }
                ]
            }
        },
        job_describes=job_describes,
        scheduler_describes=sched,
        run_jobs=set(job_map),
        compute_sa=COMPUTE_SA,
    )


def test_diff_leg_jobs_is_clean_on_the_post_leg_posture(decl, cadence, job_map) -> None:
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    assert diff_snapshot(decl, snap, PROJECT, cadence=cadence, leg="jobs") == []


def test_diff_leg_jobs_flags_a_job_on_the_wrong_identity(decl, cadence, job_map) -> None:
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    bad = dict(snap.job_describes)
    d = json.loads(json.dumps(bad["sig-export"]))
    d["spec"]["template"]["spec"]["serviceAccountName"] = COMPUTE_SA
    bad["sig-export"] = d
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, job_describes=bad),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    assert any("job sig-export runs as" in x and "export" in x for x in diffs)


def test_diff_leg_jobs_flags_a_scheduler_signing_as_default_compute(decl, cadence, job_map) -> None:
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    bad = dict(snap.scheduler_describes)
    d = json.loads(json.dumps(bad["sig-probe"]))
    d["httpTarget"]["oauthToken"]["serviceAccountEmail"] = COMPUTE_SA
    bad["sig-probe"] = d
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, scheduler_describes=bad),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    assert any("scheduler trigger for sig-probe signs as" in x for x in diffs)


def test_diff_leg_jobs_flags_editor_still_on_default_compute(decl, cadence, job_map) -> None:
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    policy = dict(snap.project_policy)
    policy["bindings"] = list(policy["bindings"]) + [
        {"role": "roles/editor", "members": [COMPUTE_MEMBER]}
    ]
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, project_policy=policy),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    assert any("still holds roles/editor" in x for x in diffs)


def test_diff_leg_jobs_flags_an_unmapped_live_job_and_a_bad_count(decl, cadence, job_map) -> None:
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    live = set(snap.run_jobs) | {"sig-mystery-job"}
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, run_jobs=live),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    joined = "\n".join(diffs)
    assert "claimed by no class" in joined
    assert "99 != declared 98" in joined
    # And a job missing the conditioned binding's exact expression is drift.
    snap2 = _post_jobs_snapshot(decl, cadence, job_map)
    buckets = json.loads(json.dumps(snap2.bucket_policies))
    for b in buckets["sig-restricted"]["bindings"]:
        if (b.get("condition") or {}).get("title") == "p34-42b-capture-rewrite":
            b["condition"]["expression"] = (
                "resource.name.startsWith('projects/_/buckets/"
                "sig-test-project-sig-restricted/objects/')"  # widened!
            )
    diffs2 = diff_snapshot(
        decl,
        dataclasses.replace(snap2, bucket_policies=buckets),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    assert any("different expression" in x for x in diffs2)


def test_diff_leg_jobs_flags_a_stale_default_compute_secret_accessor(
    decl, cadence, job_map
) -> None:
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    secrets = json.loads(json.dumps(snap.secret_policies))
    secrets["sig-sam-gov-key"]["bindings"][0]["members"].append(COMPUTE_MEMBER)
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, secret_policies=secrets),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    assert any("stale secret accessor" in x and "sig-sam-gov-key" in x for x in diffs)


def test_diff_leg_jobs_still_judges_service_sas_and_bindings(decl, cadence, job_map) -> None:
    # leg=jobs judges the whole declaration posture minus the service
    # describes: a missing class SA or a missing conditioned grant is drift.
    snap = _post_jobs_snapshot(decl, cadence, job_map)
    sas = set(snap.service_accounts) - {sa_email(PROJECT, "sig-ingest-rt")}
    diffs = diff_snapshot(
        decl,
        dataclasses.replace(snap, service_accounts=sas),
        PROJECT,
        cadence=cadence,
        leg="jobs",
    )
    assert any("missing service account sig-ingest-rt" in x for x in diffs)


# --- the same-image gate --------------------------------------------------------


def test_check_revisions_gates_job_images(tmp_path: Path) -> None:
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    pre.mkdir()
    post.mkdir()
    img = "img@sha256:" + "cd" * 32
    job_desc = {
        "spec": {
            "template": {
                "spec": {
                    "serviceAccountName": "a@b.iam.gserviceaccount.com",
                    "containers": [{"image": img}],
                }
            }
        }
    }
    (pre / "job-sig-export.json").write_text(json.dumps(job_desc))
    (post / "job-sig-export.json").write_text(json.dumps(job_desc))
    assert check_same_image(pre, post) == []
    drifted = json.loads(json.dumps(job_desc))
    drifted["spec"]["template"]["spec"]["containers"][0]["image"] = "img@sha256:" + "ef" * 32
    (post / "job-sig-export.json").write_text(json.dumps(drifted))
    problems = check_same_image(pre, post)
    assert len(problems) == 1
    assert "sig-export: image changed" in problems[0]
    assert "identity move must not roll code" in problems[0]


# --- the leg script -------------------------------------------------------------


def test_jobs_leg_check_prints_the_full_plan() -> None:
    proc = _run(IAM_JOBS_SH, "--check", "all")
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    for needle in (
        "P34.42b",
        "projects get-iam-policy",
        "run jobs list",
        "98-job",
        "run jobs describe",
        "scheduler jobs describe",
        "secrets get-iam-policy",
        "service-accounts create sig-ingest-rt",
        "service-accounts create sig-probe-rt",
        "service-accounts create sig-export-rt",
        "service-accounts create sig-materialize-rt",
        "service-accounts create sig-scheduler",
        "roles/cloudsql.client",
        "--condition-title=p34-42b-capture-rewrite",
        "objects/evidence/captures/",
        "roles/secretmanager.secretAccessor",
        "run jobs update sig-ingest-osm-overpass --service-account",
        "run jobs update sig-probe --service-account",
        "run jobs update sig-export --service-account",
        "run jobs update sig-materialize --service-account",
        "run jobs update sig-replay-ingest --service-account",
        "run jobs add-iam-policy-binding sig-probe",
        "--role roles/run.invoker",
        "run services add-iam-policy-binding sig-alerts",
        "remove-iam-policy-binding sig-alerts --member allUsers",
        "remove-iam-policy-binding",
        "--role roles/editor",
        "iam diff",
        "--leg jobs",
        "check-revisions",
        "check OK",
    ):
        assert needle in plan, needle
    # The editor removal is the LAST mutation the plan prints.
    assert plan.rindex("--role roles/editor") > plan.rindex("run jobs update")


def test_jobs_leg_check_mutates_nothing() -> None:
    proc = _run(IAM_JOBS_SH, "--check", "bindings")
    assert proc.returncode == 0
    assert "PLAN:" in proc.stdout


def test_jobs_leg_apply_queues_inside_the_freeze() -> None:
    for action in ("identities", "bindings", "jobs", "invokers", "editor", "all"):
        proc = _run(IAM_JOBS_SH, "--apply", action, SIG_IAM_JOBS_NOW=SYNTHETIC_INSIDE_FREEZE)
        assert proc.returncode == 42, action
        assert "implement-spec spec=docs/tickets/252_P34.42b" in proc.stdout


def test_jobs_leg_apply_queues_in_the_0330_band() -> None:
    proc = _run(IAM_JOBS_SH, "--apply", "jobs", SIG_IAM_JOBS_NOW=SYNTHETIC_0330_BAND)
    assert proc.returncode == 42


def test_jobs_leg_apply_past_the_window_reaches_the_adc_gate() -> None:
    proc = _run(IAM_JOBS_SH, "--apply", "identities", SIG_IAM_JOBS_NOW=SYNTHETIC_PAST_WINDOW)
    assert proc.returncode == 3  # past the window → ADC gate fires, not 42


def test_jobs_leg_read_only_actions_are_never_window_gated() -> None:
    for action in ("prestate", "verify", "rollback"):
        proc = _run(IAM_JOBS_SH, "--check", action)
        assert proc.returncode == 0, action
        assert "PLAN:" in proc.stdout


def test_jobs_leg_execution_guard_queues_on_a_running_job(tmp_path: Path) -> None:
    # The contract's "never while a job of the class being moved is executing":
    # with a stubbed gcloud reporting a running execution, --apply jobs past
    # the window exits 42 — fail-closed, before ANY mutation.
    stub = tmp_path / "bin"
    stub.mkdir()
    gcloud = stub / "gcloud"
    running_exec = json.dumps([{"status": {"conditions": [{"type": "Running", "status": "True"}]}}])
    gcloud.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in\n'
        '  *"application-default print-access-token"*) echo stub-token ;;\n'
        f"  *\"run jobs executions list\"*) echo '{running_exec}' ;;\n"
        "  *) echo '[]' ;;\n"
        "esac\n"
    )
    gcloud.chmod(0o755)
    env = _env(
        SIG_IAM_JOBS_NOW=SYNTHETIC_PAST_WINDOW,
        PATH=f"{stub}:{os.environ['PATH']}",
    )
    proc = subprocess.run(
        ["bash", str(IAM_JOBS_SH), "--apply", "jobs"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 42
    assert "running" in proc.stdout
    # And an unreadable executions list is treated the same (fail-closed).
    gcloud.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in\n'
        '  *"application-default print-access-token"*) echo stub-token ;;\n'
        '  *"run jobs executions list"*) exit 1 ;;\n'
        "  *) echo '[]' ;;\n"
        "esac\n"
    )
    proc = subprocess.run(
        ["bash", str(IAM_JOBS_SH), "--apply", "jobs"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 42


def test_jobs_leg_rollback_plan_restores_the_recorded_prestate() -> None:
    proc = _run(IAM_JOBS_SH, "--check", "rollback")
    assert proc.returncode == 0
    plan = proc.stdout
    assert "roles/editor" in plan  # editor restored first
    assert "set-iam-policy" in plan
    assert "run jobs update <job> --service-account <prior SA" in plan
    assert "pre/job-<job>.json" in plan
    assert "service-accounts delete" in plan


def test_jobs_leg_offline_verify_from_state(tmp_path: Path, decl, cadence, job_map) -> None:
    # --verify --from-state DIR judges a recorded snapshot offline: build a
    # post-leg capture dir the same shape the leg writes.
    state = tmp_path / "state"
    state.mkdir()
    emails = {sa.id: sa_email(PROJECT, sa.id) for sa in decl.service_accounts}
    class_sa = {c.name: c.service_account for c in decl.job_classes}
    (state / "service-accounts.json").write_text(
        json.dumps([{"email": e} for e in emails.values()])
    )
    (state / "project-iam.json").write_text(
        json.dumps(
            {
                "bindings": [
                    {"role": r.role, "members": [f"serviceAccount:{emails[r.service_account]}"]}
                    for r in decl.project_roles
                ]
            }
        )
    )
    (state / "compute-sa.txt").write_text(COMPUTE_SA)
    (state / "run-jobs.json").write_text(
        json.dumps([{"metadata": {"name": j}} for j in sorted(job_map)])
    )
    for job, cls in job_map.items():
        (state / f"job-{job}.json").write_text(
            json.dumps(
                {
                    "spec": {
                        "template": {
                            "spec": {
                                "serviceAccountName": emails[class_sa[cls]],
                                "containers": [{"image": "img@sha256:" + "ab" * 32}],
                            }
                        }
                    }
                }
            )
        )
    scheduled = set(
        [s["job"] for s in cadence.get("sources", [])]
        + [b["job"] for b in cadence.get("batches", [])]
        + [(cadence.get("probes") or {}).get("job")]
    )
    for job in scheduled:
        (state / f"sched-{job}.json").write_text(
            json.dumps(
                {"httpTarget": {"oauthToken": {"serviceAccountEmail": emails["sig-scheduler"]}}}
            )
        )
    (state / "service-sig-alerts-iam.json").write_text(
        json.dumps(
            {
                "bindings": [
                    {
                        "role": "roles/run.invoker",
                        "members": [
                            f"serviceAccount:{emails[g]}"
                            for g in decl.invoker_rule("sig-alerts", "jobs").grant
                            if g != "default-compute"
                        ],
                    }
                ]
            }
        )
    )
    restricted = []
    for b in decl.bucket_roles:
        if b.bucket != "sig-restricted":
            continue
        binding = {
            "role": b.role,
            "members": [f"serviceAccount:{emails[b.service_account]}"],
        }
        if b.condition_title:
            binding["condition"] = {
                "title": b.condition_title,
                "expression": condition_expression(PROJECT, b.bucket, b.condition_prefix or ""),
            }
        restricted.append(binding)
    (state / "bucket-sig-restricted-iam.json").write_text(json.dumps({"bindings": restricted}))
    web_iam = [
        {
            "role": "roles/storage.objectViewer",
            "members": [
                f"serviceAccount:{emails['sig-web-rt']}",
                "allUsers",
            ],
        }
    ] + [
        # P35.1a: the probe runtime's live-diff legacyBucketReader on sig-web.
        {"role": b.role, "members": [f"serviceAccount:{emails[b.service_account]}"]}
        for b in decl.bucket_roles
        if b.bucket == "sig-web"
    ]
    (state / "bucket-sig-web-iam.json").write_text(json.dumps({"bindings": web_iam}))
    # P35.1a: the remaining declared buckets carry the probe reader grant.
    seen_other: set[str] = set()
    for b in decl.bucket_roles:
        if b.bucket in ("sig-restricted", "sig-web") or b.bucket in seen_other:
            continue
        seen_other.add(b.bucket)
        (state / f"bucket-{b.bucket}-iam.json").write_text(
            json.dumps(
                {
                    "bindings": [
                        {
                            "role": x.role,
                            "members": [f"serviceAccount:{emails[x.service_account]}"],
                        }
                        for x in decl.bucket_roles
                        if x.bucket == b.bucket
                    ]
                }
            )
        )
    for s in decl.secrets:
        members = [
            f"serviceAccount:{emails[c]}"
            for c in s.consumers
            if c not in ("default-compute", "operator")
        ]
        if "default-compute" in s.consumers:
            members.append(COMPUTE_MEMBER)
        if "operator" in s.consumers:
            members.append("user:operator@example.invalid")
        (state / f"secret-{s.name}-iam.json").write_text(
            json.dumps(
                {"bindings": [{"role": "roles/secretmanager.secretAccessor", "members": members}]}
            )
        )
    proc = _run(IAM_JOBS_SH, "--verify", "--from-state", str(state))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "iam diff (jobs): clean" in proc.stdout


def test_no_secret_value_or_project_literal_in_the_jobs_leg() -> None:
    text = IAM_JOBS_SH.read_text(encoding="utf-8")
    assert "gserviceaccount.com" in text  # derived, never a literal e-mail
    for forbidden in ("eleutheria", "postgres://", "token="):
        # The script must name no host-specific project id or secret material.
        assert forbidden not in text.lower(), forbidden
