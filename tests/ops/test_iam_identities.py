# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.42a / G1-01, F-272 (SIG-SEC-007, AR-8) — least-privilege runtime
identities for the three Cloud Run services.

Offline layer (fixture-verified): the ``sig.iam-identities/1`` declaration
parses and fails closed on drift (a basic role, an undeclared member, a named
member in a revoke list, a missing service binding); ``sig-ops iam plan``
renders the ordered leg with per-step rollbacks; ``sig-ops iam diff`` judges
the recorded pre/post IAM snapshots under ``tests/ops/fixtures/iam/`` — the
pre-leg shape (everything on the project-Editor default compute identity,
``sig-alerts`` open to allUsers) reports every missing piece, the post-leg
shape is clean; ``check-revisions`` gates the same-image rule. The shell
leg's ``--check`` plan and the OM-19 window guard (exit 42 inside the AR-3
freeze or the 03:00–06:30Z band, the ADC gate past it) run with no ADC and
no network. No production mutation ever runs from a test.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from ops.iam_identities import (
    BASIC_ROLES,
    SCHEMA,
    check_same_image,
    diff_snapshot,
    load_declaration,
    load_snapshot,
    plan_steps,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECLARATION = REPO_ROOT / "ops" / "iam_identities.toml"
IAM_SH = REPO_ROOT / "ops" / "gcp" / "iam-service-accounts.sh"
FIXTURES = REPO_ROOT / "tests" / "ops" / "fixtures" / "iam"
PROJECT = "sig-test-project"
COMPUTE_SA = "12345-compute@developer.gserviceaccount.com"

# Clock values injected as SIG_IAM_NOW into the window-guard apply tests
# (future-ok: scheduled — they reproduce the AR-3 + AR-2 contract window
# offline; no apply ever runs). SYNTHETIC_ names exempt them under B4 R5.
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


@pytest.fixture
def decl():
    return load_declaration(DECLARATION)


@pytest.fixture
def pre():
    return load_snapshot(FIXTURES / "pre")


@pytest.fixture
def post():
    return load_snapshot(FIXTURES / "post")


# --- the declaration ---------------------------------------------------------


def test_declaration_parses_and_declares_the_contract(decl) -> None:
    assert [sa.id for sa in decl.service_accounts] == [
        "sig-api-rt",
        "sig-web-rt",
        "sig-alerts-rt",
        "sig-ingest-rt",
        "sig-probe-rt",
        "sig-export-rt",
        "sig-materialize-rt",
        "sig-quality-probe-rt",
        "sig-release-rt",
        "sig-status-rt",
        "sig-scheduler",
    ]
    assert [sa.id for sa in decl.service_accounts if sa.reserved] == [
        "sig-release-rt",
        "sig-status-rt",
        "sig-scheduler",
    ]
    # P34.43: sig-quality-probe-rt is no longer reserved — the [[oneoff]]
    # exec family binds it (its grants were always declared as P34.43's;
    # the P34.44b scheduled probe may still land on the same identity).
    assert [o.service_account for o in decl.oneoffs] == ["sig-quality-probe-rt"]
    # The project grants are the P34.42a services set plus the exec leg's
    # Cloud SQL client binding on sig-quality-probe-rt (P34.43); P35.1a adds
    # the two read-only viewers the live-diff leg needs on the probe runtime
    # (roles/run.viewer + roles/cloudscheduler.viewer — SIG-OPS-005, ADR-174).
    assert [(r.service_account, r.role) for r in decl.project_roles] == [
        ("sig-api-rt", "roles/cloudsql.client"),
        ("sig-ingest-rt", "roles/cloudsql.client"),
        ("sig-probe-rt", "roles/cloudsql.client"),
        ("sig-probe-rt", "roles/run.viewer"),
        ("sig-probe-rt", "roles/cloudscheduler.viewer"),
        ("sig-export-rt", "roles/cloudsql.client"),
        ("sig-materialize-rt", "roles/cloudsql.client"),
        ("sig-quality-probe-rt", "roles/cloudsql.client"),
    ]
    assert ("sig-web-rt", "sig-web", "roles/storage.objectViewer") in [
        (r.service_account, r.bucket, r.role) for r in decl.bucket_roles
    ]
    assert [(s.name, s.service_account) for s in decl.services] == [
        ("sig-api", "sig-api-rt"),
        ("sig-web", "sig-web-rt"),
        ("sig-alerts", "sig-alerts-rt"),
    ]
    # sig-alerts: two leg-scoped invoker rules — the services-leg interim
    # (grant the recorded caller, revoke allUsers; G1-11) and the jobs-leg
    # end-state (grant the probe callers — P34.44b adds the nightly quality
    # probe's runtime identity — revoke allUsers + default-compute).
    assert len(decl.invokers) == 2
    services_rule = decl.invoker_rule("sig-alerts", "services")
    assert services_rule is not None
    assert services_rule.grant == ("default-compute",)
    assert services_rule.revoke == ("allUsers",)
    jobs_rule = decl.invoker_rule("sig-alerts", "jobs")
    assert jobs_rule is not None
    assert jobs_rule.grant == ("sig-probe-rt", "sig-quality-probe-rt")
    assert jobs_rule.revoke == ("allUsers", "default-compute")
    # The 14-secret consumer matrix is complete (P34.43 adds the two DB-login
    # credentials consumed by the exec identity alone; P34.45 adds the third —
    # the write-capable sig_materialize_login password); the services-leg
    # accessor grant set is unchanged (sig-api-rt on sig-pg-password), the
    # jobs-leg grants are the job-class consumers, and the five job-only
    # secrets carry a jobs_revoke on default-compute.
    assert len(decl.secrets) == 14
    api_env = next(s for s in decl.secrets if s.name == "sig-api-env")
    assert api_env.consumers == ()  # recorded, 0 versions, never deleted
    revoked = {s.name for s in decl.secrets if "default-compute" in s.jobs_revoke}
    assert revoked == {
        "sig-alert-webhook-token",
        "sig-data-gov-key",
        "sig-muckrock-refresh",
        "sig-openstates-key",
        "sig-sam-gov-key",
    }
    # default-compute stays a consumer of sig-pg-password only (the GCE host).
    pg = next(s for s in decl.secrets if s.name == "sig-pg-password")
    assert "default-compute" in pg.consumers


def test_declaration_declares_no_basic_role_no_public_grant(decl) -> None:
    # No role= assignment outside [[remove_role]] is ever a basic role
    # (remove_role names roles/editor — removal is the point, so the check
    # looks at grant positions only).
    for r in decl.project_roles:
        assert r.role not in BASIC_ROLES
    for b in decl.bucket_roles:
        assert b.role not in BASIC_ROLES
    # The only remove_role is the default-compute editor removal (G1-01).
    assert [(r.member, r.role) for r in decl.remove_roles] == [("default-compute", "roles/editor")]
    # allUsers may appear ONLY inside an [[invoker]] revoke list — never in
    # a grant or consumers position.
    for v in decl.invokers:
        for grant in v.grant:
            assert not grant.startswith("all")
        for revoked in v.revoke:
            assert revoked in {"allUsers", "allAuthenticatedUsers", "default-compute"}
    for s in decl.secrets:
        assert "allUsers" not in s.consumers


def test_declaration_fails_closed(tmp_path: Path) -> None:
    base = DECLARATION.read_text(encoding="utf-8")
    bad = tmp_path / "bad.toml"
    bad.write_text(base.replace(f'schema = "{SCHEMA}"', 'schema = "bogus"'))
    with pytest.raises(ValueError, match="schema"):
        load_declaration(bad)
    # A basic role can never be declared.
    bad.write_text(base.replace("roles/cloudsql.client", "roles/editor"))
    with pytest.raises(ValueError, match="basic role"):
        load_declaration(bad)
    # An undeclared SA in a binding refuses.
    bad.write_text(
        base.replace('service_account = "sig-api-rt"', 'service_account = "sig-x-rt"', 1)
    )
    with pytest.raises(ValueError, match="not a declared service account"):
        load_declaration(bad)
    # A named member in a revoke list refuses (revokes are public-only).
    bad.write_text(base.replace('revoke = ["allUsers"]', 'revoke = ["sig-api-rt"]'))
    with pytest.raises(ValueError, match="revoke"):
        load_declaration(bad)
    # allUsers can never be a grant or a consumer.
    bad.write_text(base.replace('grant = ["default-compute"]', 'grant = ["allUsers"]'))
    with pytest.raises(ValueError, match="never be granted"):
        load_declaration(bad)
    # A service bound to an undeclared SA refuses.
    bad.write_text(
        base.replace('service_account = "sig-alerts-rt"', 'service_account = "sig-q-rt"')
    )
    with pytest.raises(ValueError, match="not a declared service account"):
        load_declaration(bad)
    with pytest.raises(ValueError, match="not found"):
        load_declaration(tmp_path / "absent.toml")


def test_declaration_rejects_an_unbound_sa(tmp_path: Path) -> None:
    # Identities are per-workload: every SA binds to exactly one service.
    base = DECLARATION.read_text(encoding="utf-8")
    bad = tmp_path / "bad.toml"
    bad.write_text(
        base.replace('service_account = "sig-alerts-rt"', 'service_account = "sig-web-rt"')
    )
    with pytest.raises(ValueError, match="already bound|bound to no service"):
        load_declaration(bad)


# --- the plan ------------------------------------------------------------------


def test_plan_steps_cover_the_contract_mutation_list(decl) -> None:
    steps = plan_steps(decl, PROJECT, "us-central1", leg="services")
    flat = "\n".join(" ".join(s.command) for s in steps)
    # (1) create the three SAs
    for sa in ("sig-api-rt", "sig-web-rt", "sig-alerts-rt"):
        assert f"service-accounts create {sa}" in flat
    # (2) least-privilege bindings + the per-consumer secret accessor
    assert (
        "add-iam-policy-binding sig-test-project "
        "--member=serviceAccount:sig-api-rt@sig-test-project.iam.gserviceaccount.com "
        "--role=roles/cloudsql.client" in flat
    )
    assert "buckets add-iam-policy-binding gs://sig-test-project-sig-web" in flat
    assert (
        "sig-web-rt@sig-test-project.iam.gserviceaccount.com "
        "--role=roles/storage.objectViewer" in flat
    )
    assert "secrets add-iam-policy-binding sig-pg-password" in flat
    assert "roles/secretmanager.secretAccessor" in flat
    # No other secret gains a binding in this leg.
    assert flat.count("secrets add-iam-policy-binding") == 1
    # (3) one same-image revision per service with --service-account
    for svc, sa in (
        ("sig-api", "sig-api-rt"),
        ("sig-web", "sig-web-rt"),
        ("sig-alerts", "sig-alerts-rt"),
    ):
        assert (
            f"run services update {svc} --service-account={sa}@{PROJECT}.iam.gserviceaccount.com"
            in flat
        )
    # No deploy/roll ever — the image is never touched.
    assert "run deploy" not in flat
    assert "--image" not in flat
    # (4) the sig-alerts invoker change: grant to the caller, revoke allUsers.
    assert "add-iam-policy-binding sig-alerts" in flat
    assert "--role=roles/run.invoker" in flat
    assert "remove-iam-policy-binding sig-alerts --member=allUsers" in flat
    # The grant precedes the revoke (the receiver never loses its only caller).
    add_at = flat.index("add-iam-policy-binding sig-alerts")
    rm_at = flat.index("remove-iam-policy-binding sig-alerts")
    assert add_at < rm_at
    # allUsers appears only on the revoke line — never on a grant.
    for line in flat.splitlines():
        if "allUsers" in line:
            assert "remove-iam-policy-binding" in line
    for role in BASIC_ROLES:
        assert role not in flat


def test_plan_steps_carry_rollback_for_every_step(decl) -> None:
    steps = plan_steps(decl, PROJECT, "us-central1", leg="services")
    # Every mutating phase has a rollback command (the invoker revoke's
    # rollback is the recorded set-iam-policy on the grant step).
    for s in steps:
        if s.phase in {"identities", "bindings", "revisions", "invoker"}:
            if s.note.startswith("sig-alerts: revoke"):
                continue  # covered by the recorded-policy rollback
            assert s.rollback, s.note
    # Ordering: identities before bindings before revisions before invoker.
    phases = [s.phase for s in steps]
    assert phases == sorted(phases, key=["identities", "bindings", "revisions", "invoker"].index)


# --- the recorded-snapshot diff (the --verify half) ----------------------------


def test_diff_reports_every_missing_piece_on_the_pre_leg_snapshot(decl, pre) -> None:
    diffs = diff_snapshot(decl, pre, PROJECT, leg="services")
    joined = "\n".join(diffs)
    for sa in ("sig-api-rt", "sig-web-rt", "sig-alerts-rt"):
        assert f"missing service account {sa}@sig-test-project.iam.gserviceaccount.com" in joined
    assert (
        "missing project binding "
        "serviceAccount:sig-api-rt@sig-test-project.iam.gserviceaccount.com "
        "→ roles/cloudsql.client" in joined
    )
    assert "missing bucket binding" in joined and "roles/storage.objectViewer" in joined
    assert (
        "missing secret accessor "
        "serviceAccount:sig-api-rt@sig-test-project.iam.gserviceaccount.com "
        "on sig-pg-password" in joined
    )
    for svc in ("sig-api", "sig-web", "sig-alerts"):
        assert f"service {svc} runs as '{COMPUTE_SA}'" in joined
    assert "sig-alerts still invokable by allUsers" in joined
    assert (
        "missing invoker grant serviceAccount:12345-compute@developer.gserviceaccount.com "
        "on sig-alerts" in joined
    )


def test_diff_is_clean_on_the_post_leg_snapshot(decl, post) -> None:
    assert diff_snapshot(decl, post, PROJECT, leg="services") == []


def test_diff_flags_a_basic_role_on_a_runtime_sa(decl, post) -> None:
    snap = load_snapshot(FIXTURES / "post")
    policy = dict(snap.project_policy)
    policy["bindings"] = list(policy["bindings"]) + [
        {
            "role": "roles/editor",
            "members": ["serviceAccount:sig-api-rt@sig-test-project.iam.gserviceaccount.com"],
        }
    ]
    drifted = dataclasses.replace(snap, project_policy=policy)
    diffs = diff_snapshot(decl, drifted, PROJECT, leg="services")
    assert any("basic role on a runtime SA" in d for d in diffs)
    assert any("undeclared project role on a runtime SA" in d for d in diffs)


def test_diff_flags_a_runtime_sa_reading_a_foreign_secret(decl, post) -> None:
    snap = load_snapshot(FIXTURES / "post")
    policy = dict(snap.secret_policies["sig-pg-password"])
    policy["bindings"] = list(policy["bindings"]) + [
        {
            "role": "roles/secretmanager.secretAccessor",
            "members": ["serviceAccount:sig-alerts-rt@sig-test-project.iam.gserviceaccount.com"],
        }
    ]
    secrets = dict(snap.secret_policies)
    secrets["sig-pg-password"] = policy
    drifted = dataclasses.replace(snap, secret_policies=secrets)
    diffs = diff_snapshot(decl, drifted, PROJECT, leg="services")
    assert any("undeclared secret accessor" in d and "sig-alerts-rt" in d for d in diffs)


def test_diff_flags_an_undeclared_secret_accessor(decl, post) -> None:
    # The compute SA accessor is a declared consumer on sig-pg-password — but on
    # a secret where it is NOT declared it is drift (deliverable 2: readable
    # only by its consumers).
    snap = load_snapshot(FIXTURES / "post")
    secrets = dict(snap.secret_policies)
    secrets["sig-api-env"] = {
        "bindings": [
            {
                "role": "roles/secretmanager.secretAccessor",
                "members": ["serviceAccount:12345-compute@developer.gserviceaccount.com"],
            }
        ]
    }
    drifted = dataclasses.replace(snap, secret_policies=secrets)
    diffs = diff_snapshot(decl, drifted, PROJECT, leg="services")
    assert any("undeclared secret accessor" in d and "sig-api-env" in d for d in diffs)
    # And a public member on any secret is always drift.
    secrets["sig-api-env"] = {
        "bindings": [
            {
                "role": "roles/secretmanager.secretAccessor",
                "members": ["allUsers"],
            }
        ]
    }
    diffs = diff_snapshot(
        decl, dataclasses.replace(snap, secret_policies=secrets), PROJECT, leg="services"
    )
    assert any("public member on a secret" in d and "sig-api-env" in d for d in diffs)


def test_diff_flags_a_declared_sa_holding_an_undeclared_bucket_role(decl, post) -> None:
    # sig-web-rt with objectAdmin (not viewer) on the web bucket = delete on an
    # evidence store — flagged even though the declared viewer binding also sits.
    snap = load_snapshot(FIXTURES / "post")
    policy = dict(snap.bucket_policies["sig-web"])
    policy["bindings"] = list(policy["bindings"]) + [
        {
            "role": "roles/storage.objectAdmin",
            "members": ["serviceAccount:sig-web-rt@sig-test-project.iam.gserviceaccount.com"],
        }
    ]
    buckets = dict(snap.bucket_policies)
    buckets["sig-web"] = policy
    drifted = dataclasses.replace(snap, bucket_policies=buckets)
    diffs = diff_snapshot(decl, drifted, PROJECT, leg="services")
    assert any("undeclared bucket role on a runtime SA" in d and "objectAdmin" in d for d in diffs)


def test_diff_flags_a_lingering_allusers(decl, post) -> None:
    snap = load_snapshot(FIXTURES / "post")
    policies = dict(snap.service_policies)
    policies["sig-alerts"] = {"bindings": [{"role": "roles/run.invoker", "members": ["allUsers"]}]}
    drifted = dataclasses.replace(snap, service_policies=policies)
    diffs = diff_snapshot(decl, drifted, PROJECT, leg="services")
    assert any("sig-alerts still invokable by allUsers" in d for d in diffs)


def test_diff_output_names_only_iam_facts(decl, pre) -> None:
    # Every DRIFT line is an IAM-shape fact (a member, a role, a service, a
    # secret NAME) — the diff never invents or leaks anything else.
    diffs = diff_snapshot(decl, pre, PROJECT, leg="services")
    assert diffs
    for d in diffs:
        assert re.match(r"^(missing|undeclared|basic|service|sig-alerts|public|UNREADABLE)", d), d


# --- the same-image gate -------------------------------------------------------


def test_check_revisions_clean_when_digests_identical() -> None:
    assert check_same_image(FIXTURES / "pre", FIXTURES / "post") == []


def test_check_revisions_flags_a_changed_image(tmp_path: Path) -> None:
    drifted = tmp_path / "post"
    drifted.mkdir()
    desc = json.loads((FIXTURES / "post" / "service-sig-api.json").read_text())
    desc["spec"]["template"]["spec"]["containers"][0]["image"] = (
        "us-central1-docker.pkg.dev/sig-test-project/sig/sig-api@sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )
    (drifted / "service-sig-api.json").write_text(json.dumps(desc))
    problems = check_same_image(FIXTURES / "pre", drifted)
    assert len(problems) == 1
    assert "sig-api: image changed" in problems[0]
    assert "not a same-image revision" in problems[0]


# --- the CLI surface -------------------------------------------------------------


def test_iam_cli_plan_diff_and_check_revisions() -> None:
    plan = subprocess.run(
        ["uv", "run", "--quiet", "sig-ops", "iam", "plan", "--project", PROJECT],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert plan.returncode == 0, plan.stderr
    assert "service-accounts create sig-api-rt" in plan.stdout
    assert "rollback:" in plan.stdout

    diff = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "iam",
            "diff",
            "--state-dir",
            str(FIXTURES / "pre"),
            "--project",
            PROJECT,
            "--leg",
            "services",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert diff.returncode == 4
    assert "DRIFT:" in diff.stdout

    clean = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "iam",
            "diff",
            "--state-dir",
            str(FIXTURES / "post"),
            "--project",
            PROJECT,
            "--leg",
            "services",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert clean.returncode == 0, clean.stdout + clean.stderr

    rev = subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "sig-ops",
            "iam",
            "check-revisions",
            "--pre",
            str(FIXTURES / "pre"),
            "--post",
            str(FIXTURES / "post"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert rev.returncode == 0, rev.stdout + rev.stderr


# --- the leg script ------------------------------------------------------------


def test_iam_check_prints_the_full_plan() -> None:
    proc = _run(IAM_SH, "--check", "all")
    assert proc.returncode == 0, proc.stderr
    plan = proc.stdout
    for needle in (
        "projects get-iam-policy",
        "run services describe",
        "run jobs describe sig-probe",
        "secrets get-iam-policy",
        "service-accounts create sig-api-rt",
        "service-accounts create sig-web-rt",
        "service-accounts create sig-alerts-rt",
        "roles/cloudsql.client",
        "roles/storage.objectViewer",
        "roles/secretmanager.secretAccessor",
        "run services update sig-api --service-account",
        "run services update sig-web --service-account",
        "run services update sig-alerts --service-account",
        "add-iam-policy-binding sig-alerts",
        "remove-iam-policy-binding sig-alerts --member allUsers",
        "roles/run.invoker",
        "iam diff",
        "check-revisions",
        "route-compare verify",
        "check OK",
    ):
        assert needle in plan, needle


def test_iam_check_mode_mutates_nothing() -> None:
    # check mode prints PLAN lines and exits 0 without ADC or a network.
    proc = _run(IAM_SH, "--check", "bindings")
    assert proc.returncode == 0
    assert "PLAN:" in proc.stdout


def test_iam_apply_queues_inside_the_freeze() -> None:
    # 2026-10-08 is inside AR-3 — a mutating apply exits 42 with the re-run line.
    proc = _run(IAM_SH, "--apply", "identities", SIG_IAM_NOW=SYNTHETIC_INSIDE_FREEZE)
    assert proc.returncode == 42
    assert "implement-spec spec=docs/tickets/251_P34.42a" in proc.stdout
    for action in ("bindings", "revisions", "invoker", "all"):
        proc = _run(IAM_SH, "--apply", action, SIG_IAM_NOW=SYNTHETIC_INSIDE_FREEZE)
        assert proc.returncode == 42, action


def test_iam_apply_queues_in_the_0300_0630_band() -> None:
    proc = _run(IAM_SH, "--apply", "identities", SIG_IAM_NOW=SYNTHETIC_0330_BAND)
    assert proc.returncode == 42


def test_iam_apply_past_the_window_reaches_the_adc_gate() -> None:
    proc = _run(IAM_SH, "--apply", "identities", SIG_IAM_NOW=SYNTHETIC_PAST_WINDOW)
    assert proc.returncode == 3  # past the window → ADC gate fires, not 42


def test_iam_apply_refuses_without_adc_even_with_project() -> None:
    proc = _run(IAM_SH, "--apply", "revisions", SIG_IAM_NOW=SYNTHETIC_PAST_WINDOW)
    assert proc.returncode == 3
    out = proc.stdout + proc.stderr
    assert "gate pending" in out or "gcloud" in out


def test_iam_read_only_actions_are_never_window_gated() -> None:
    # prestate/verify/rollback are read-only or restores — they print their
    # plan inside the freeze too (exit 0 in check mode, never 42).
    for action in ("prestate", "verify", "rollback"):
        proc = _run(IAM_SH, "--check", action)
        assert proc.returncode == 0, action
        assert "PLAN:" in proc.stdout


def test_iam_rollback_plan_restores_the_recorded_prestate() -> None:
    proc = _run(IAM_SH, "--check", "rollback")
    assert proc.returncode == 0
    plan = proc.stdout
    assert "run services update <svc> --service-account <prior SA" in plan
    assert "set-iam-policy sig-alerts" in plan
    assert "service-accounts delete" in plan


def test_no_secret_value_or_project_literal_in_the_leg() -> None:
    # The script + declaration carry names and symbolic members only: the
    # project is env-parameterised, no credential literal, and no multi-digit
    # numeric literal that could be a leaked project number.
    text = IAM_SH.read_text(encoding="utf-8") + DECLARATION.read_text(encoding="utf-8")
    assert "SIG_GCP_PROJECT" in text
    assert "rhema" not in text and "zeta-medley" not in text
    assert not re.search(r"\b\d{7,}\b", text), "a long numeric literal — a project number?"
