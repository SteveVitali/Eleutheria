# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The least-privilege identity declaration (P34.42a+b / G1-01, F-272, SIG-SEC-007).

``ops/iam_identities.toml`` is the committed record of every runtime
workload's identity: the three Cloud Run services' per-workload service
accounts (the services leg, applied by ``iam-service-accounts.sh``), the
job-class identities all 88 Cloud Run jobs move to (the jobs leg, applied by
``iam-job-identities.sh``), the exact IAM bindings each class is allowed, the
service/job → identity maps, the ``sig-alerts`` invoker change (G1-11), the
scheduler invoker identity, the ``roles/editor`` removal off the default
compute service account, and the 11-secret consumer matrix. This module is
the pure engine:

* ``load_declaration`` — parse + validate the TOML (fail-closed: a basic
  role grant, an undeclared identity, a named member in a public-only
  position, a conditioned grant on anything but the recorded OCFL-rewrite
  role, a job claimed by two classes, or an unbound non-reserved identity
  all refuse to load).
* ``resolve_job_map`` — the deterministic job → class map: cadence-owned
  jobs resolve from ``ops/cadence.toml`` (sources, batches, probes), the
  manual/cruft jobs from each class's explicit ``jobs`` list. A double-claim,
  an unclaimed cadence job, or a duplicate explicit entry refuses.
* ``plan_steps`` — the ordered mutation plan for one leg
  (``--leg services``/``jobs``/``all``). Every step carries its rollback
  command; values the contract requires be read live (the caller identity,
  recorded prior SAs) render as ``<...>`` placeholders the shell wrapper
  fills.
* ``diff_snapshot`` — the ``--verify`` half: a recorded IAM snapshot (the
  ``prestate``/``poststate`` JSON files the shell legs capture) judged
  against the declaration, scoped to the leg being judged. Reports every
  missing identity or binding, every wrong ``serviceAccountName`` on a
  service or job, a lingering ``allUsers``/stale invoker, a declared SA
  holding an undeclared or basic role, a runtime SA reading a secret it is
  not a consumer of, a scheduler trigger signing as the wrong identity, and
  the default compute SA still holding ``roles/editor`` — the read-only
  "proof without destruction" analysis (deliverable 5; the same shape
  P35.1a's live-diff reuses).
* ``check_same_image`` — the same-image gate: each service's container
  image digest and each job's container image must be byte-identical
  between the prestate and poststate describes (the leg is an identity
  change, never a code roll).

Offline only: nothing here shells out to gcloud; the shell wrappers own
every mutation and stay window-gated.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

SCHEMA = "sig.iam-identities/1"

DEFAULT_DECLARATION = Path(__file__).resolve().parents[2] / "iam_identities.toml"
DEFAULT_CADENCE = Path(__file__).resolve().parents[2] / "cadence.toml"

# Basic roles are the whole point of G1-01 — none may ever be granted to a
# runtime identity (SIG-SEC-007: no Owner/Editor/Viewer). They may appear in
# [[remove_role]] — removal is the point.
BASIC_ROLES = frozenset({"roles/owner", "roles/editor", "roles/viewer"})

# Symbolic members the declaration resolves at apply time. `default-compute`
# = <projectNumber>-compute@developer.gserviceaccount.com; `operator` = the
# human's account (records a consumer that is never a GCP SA binding).
SYMBOLIC_MEMBERS = frozenset({"default-compute", "operator"})

# Members that may appear ONLY in a revoke list — a public grant on an
# internal receiver is exactly the G1-11 defect.
PUBLIC_MEMBERS = frozenset({"allUsers", "allAuthenticatedUsers"})

SECRET_ACCESSOR_ROLE = "roles/secretmanager.secretAccessor"
RUN_INVOKER_ROLE = "roles/run.invoker"

LEGS = ("services", "jobs", "all")

# The one conditioned grant this declaration permits: the ingest class's
# OCFL inventory-head rewrite under evidence/captures/ (ADR-201). A
# condition on any other role refuses to load.
CONDITIONABLE_ROLES = frozenset({"roles/storage.objectUser"})


@dataclass(frozen=True)
class ServiceAccount:
    id: str
    display_name: str
    purpose: str
    reserved: bool = False  # created by the jobs leg; no workload/grant binds yet


@dataclass(frozen=True)
class ProjectRole:
    service_account: str
    role: str


@dataclass(frozen=True)
class BucketRole:
    service_account: str
    bucket: str  # the -suffixed derived name: "sig-web" → <project>-sig-web
    role: str
    condition_title: str | None = None
    condition_prefix: str | None = None  # objects/ prefix for the CEL expression


@dataclass(frozen=True)
class Secret:
    name: str
    consumers: tuple[str, ...]
    jobs_revoke: tuple[str, ...] = ()  # members the JOBS leg removes


@dataclass(frozen=True)
class ServiceMap:
    name: str
    service_account: str


@dataclass(frozen=True)
class InvokerRule:
    service: str
    grant: tuple[str, ...]
    revoke: tuple[str, ...]
    leg: str = "services"


@dataclass(frozen=True)
class JobClass:
    name: str
    service_account: str
    sources: bool = False  # claims every [[sources]] job in ops/cadence.toml
    batches: bool = False  # claims every [[batches]] job
    probes: bool = False  # claims [probes].job
    jobs: tuple[str, ...] = ()  # explicit job names (manual + cruft jobs)


@dataclass(frozen=True)
class JobInvoker:
    member: str  # a declared SA id (the scheduler invoker identity)
    targets: str  # "scheduled" — every cadence-scheduled job


@dataclass(frozen=True)
class RemoveRole:
    member: str  # symbolic member or declared SA id
    role: str


@dataclass(frozen=True)
class Declaration:
    service_accounts: tuple[ServiceAccount, ...]
    project_roles: tuple[ProjectRole, ...]
    bucket_roles: tuple[BucketRole, ...]
    services: tuple[ServiceMap, ...]
    invokers: tuple[InvokerRule, ...]
    secrets: tuple[Secret, ...]
    job_classes: tuple[JobClass, ...] = ()
    job_invokers: tuple[JobInvoker, ...] = ()
    remove_roles: tuple[RemoveRole, ...] = ()
    expected_job_count: int | None = None

    def sa(self, sa_id: str) -> ServiceAccount:
        for sa in self.service_accounts:
            if sa.id == sa_id:
                return sa
        raise KeyError(sa_id)

    def invoker_rule(self, service: str, leg: str) -> InvokerRule | None:
        """The invoker posture a leg judges: the rule declared for that leg;
        ``all`` judges the last-declared (jobs) rule when one exists."""
        matches = [v for v in self.invokers if v.service == service]
        if leg == "all":
            return matches[-1] if matches else None
        for v in matches:
            if v.leg == leg:
                return v
        return None


def _fail(msg: str) -> NoReturn:
    raise ValueError(f"iam_identities declaration: {msg}")


def _check_sa_id(raw: object) -> str:
    if not isinstance(raw, str):
        _fail(f"service-account id {raw!r} must be a string")
    if not (6 <= len(raw) <= 30):
        _fail(f"service-account id {raw!r} must be 6–30 chars")
    if not raw[0].islower() or not raw[-1].isalnum():
        _fail(f"service-account id {raw!r} must start lowercase, end alnum")
    if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in raw):
        _fail(f"service-account id {raw!r} has an illegal character")
    return raw


def _check_member(raw: object, *, declared: set[str], context: str) -> str:
    """A member in a grant/consumers list: a declared SA id or a symbolic
    member — never a public member, never a literal e-mail or project id."""
    if not isinstance(raw, str) or not raw:
        _fail(f"{context}: member {raw!r} must be a non-empty string")
    if raw in PUBLIC_MEMBERS:
        _fail(f"{context}: {raw} may never be granted — revokes only")
    if raw in SYMBOLIC_MEMBERS:
        return raw
    if "@" in raw or ":" in raw:
        _fail(f"{context}: member {raw!r} must be symbolic or a declared SA id")
    if raw not in declared:
        _fail(f"{context}: member {raw!r} is not a declared service account")
    return raw


def _check_name(raw: object, context: str) -> str:
    if not isinstance(raw, str) or not raw or "@" in raw or ":" in raw:
        _fail(f"{context}: name {raw!r} must be a bare job/scheduler name")
    return raw


def load_cadence(path: str | Path | None = None) -> dict[str, Any]:
    """Parse ops/cadence.toml — the authoritative cadence-owned job list."""
    p = Path(path) if path else DEFAULT_CADENCE
    if not p.is_file():
        _fail(f"{p} not found — the cadence file is required for the job map")
    return tomllib.loads(p.read_text(encoding="utf-8"))


def cadence_job_names(cadence: dict[str, Any]) -> dict[str, list[str]]:
    """The jobs ops/cadence.toml owns, by kind."""
    out: dict[str, list[str]] = {"sources": [], "batches": [], "probes": []}
    for s in cadence.get("sources") or []:
        out["sources"].append(_check_name(s.get("job"), "cadence sources"))
    for b in cadence.get("batches") or []:
        out["batches"].append(_check_name(b.get("job"), "cadence batches"))
    probe_job = (cadence.get("probes") or {}).get("job")
    if probe_job:
        out["probes"].append(_check_name(probe_job, "cadence probes"))
    return out


def cadence_scheduled_jobs(cadence: dict[str, Any]) -> list[str]:
    """Every job that carries a Cloud Scheduler trigger in cadence.toml."""
    names = cadence_job_names(cadence)
    return names["sources"] + names["batches"] + names["probes"]


def cadence_scheduler_triggers(cadence: dict[str, Any]) -> dict[str, str]:
    """The cadence job → Cloud Scheduler trigger-name map."""
    out: dict[str, str] = {}
    for row in (cadence.get("sources") or []) + (cadence.get("batches") or []):
        job = _check_name(row.get("job"), "cadence job")
        trig = row.get("scheduler")
        if trig:
            out[job] = _check_name(trig, "cadence scheduler")
    probes = cadence.get("probes") or {}
    if probes.get("job") and probes.get("scheduler"):
        out[_check_name(probes["job"], "cadence probes")] = _check_name(
            probes["scheduler"], "cadence probes"
        )
    return out


def resolve_job_map(decl: Declaration, cadence: dict[str, Any]) -> dict[str, str]:
    """The deterministic job → class map. Fail-closed: a cadence-owned job
    claimed by no class, an explicit job claimed twice, or a cadence job
    claimed both by a group flag and an explicit list refuses to resolve."""
    names = cadence_job_names(cadence)
    job_map: dict[str, str] = {}
    for cls in decl.job_classes:
        claimed: list[str] = []
        if cls.sources:
            claimed += names["sources"]
        if cls.batches:
            claimed += names["batches"]
        if cls.probes:
            claimed += names["probes"]
        claimed += list(cls.jobs)
        for job in claimed:
            if job in job_map:
                _fail(
                    f"job {job!r} claimed by both class {job_map[job]!r} "
                    f"and class {cls.name!r} — every job resolves exactly one class"
                )
            job_map[job] = cls.name
    unclaimed = [j for kind in names.values() for j in kind if j not in job_map]
    if unclaimed:
        _fail(f"cadence job(s) claimed by no class: {sorted(unclaimed)}")
    return job_map


def load_declaration(path: str | Path | None = None) -> Declaration:
    """Parse + validate ``ops/iam_identities.toml`` — fail-closed on drift."""
    p = Path(path) if path else DEFAULT_DECLARATION
    if not p.is_file():
        _fail(f"{p} not found — the identity declaration is required")
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    if raw.get("schema") != SCHEMA:
        _fail(f"schema must be {SCHEMA!r}, got {raw.get('schema')!r}")

    sas: list[ServiceAccount] = []
    seen_sa: set[str] = set()
    for i, s in enumerate(raw.get("service_account") or []):
        sa_id = _check_sa_id(s.get("id"))
        if sa_id in seen_sa:
            _fail(f"service_account {i}: {sa_id!r} declared twice")
        seen_sa.add(sa_id)
        display = s.get("display_name")
        if not isinstance(display, str) or not display:
            _fail(f"service_account {sa_id}: display_name must be non-empty")
        purpose = s.get("purpose")
        if not isinstance(purpose, str) or not purpose:
            _fail(f"service_account {sa_id}: purpose must be non-empty")
        reserved = bool(s.get("reserved", False))
        sas.append(
            ServiceAccount(id=sa_id, display_name=display, purpose=purpose, reserved=reserved)
        )
    if not sas:
        _fail("the declaration names no service accounts")

    project_roles: list[ProjectRole] = []
    for i, r in enumerate(raw.get("project_role") or []):
        sa = r.get("service_account")
        if sa not in seen_sa:
            _fail(f"project_role {i}: {sa!r} is not a declared service account")
        role = r.get("role")
        if not isinstance(role, str) or not role.startswith("roles/"):
            _fail(f"project_role {i}: role {role!r} must be a roles/* managed role")
        if role in BASIC_ROLES:
            _fail(f"project_role {i}: {role} is a basic role — never grantable (SIG-SEC-007)")
        project_roles.append(ProjectRole(service_account=sa, role=role))

    bucket_roles: list[BucketRole] = []
    for i, r in enumerate(raw.get("bucket_role") or []):
        sa = r.get("service_account")
        if sa not in seen_sa:
            _fail(f"bucket_role {i}: {sa!r} is not a declared service account")
        bucket = r.get("bucket")
        if not isinstance(bucket, str) or not bucket or "-" in bucket[0] + bucket[-1]:
            _fail(f"bucket_role {i}: bucket {bucket!r} must be a -suffixed bucket name")
        role = r.get("role")
        if not isinstance(role, str) or not role.startswith("roles/"):
            _fail(f"bucket_role {i}: role {role!r} must be a roles/* managed role")
        if role in BASIC_ROLES:
            _fail(f"bucket_role {i}: {role} is a basic role — never grantable (SIG-SEC-007)")
        cond_title = r.get("condition_title")
        cond_prefix = r.get("condition_prefix")
        if (cond_title is None) != (cond_prefix is None):
            _fail(
                f"bucket_role {i}: condition_title and condition_prefix "
                "are declared together or not at all"
            )
        if cond_title is not None:
            if not isinstance(cond_title, str) or not cond_title:
                _fail(f"bucket_role {i}: condition_title must be non-empty")
            cond_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            if any(c not in cond_chars for c in cond_title):
                _fail(f"bucket_role {i}: condition_title {cond_title!r} has an illegal character")
            if role not in CONDITIONABLE_ROLES:
                _fail(
                    f"bucket_role {i}: a condition on {role} — only "
                    f"{sorted(CONDITIONABLE_ROLES)} may carry one (ADR-201)"
                )
            if not isinstance(cond_prefix, str) or not cond_prefix.endswith("/"):
                _fail(f"bucket_role {i}: condition_prefix must be a trailing-slash prefix")
        bucket_roles.append(
            BucketRole(
                service_account=sa,
                bucket=bucket,
                role=role,
                condition_title=cond_title,
                condition_prefix=cond_prefix,
            )
        )

    services: list[ServiceMap] = []
    seen_svc: set[str] = set()
    bound_sa: set[str] = set()
    for i, s in enumerate(raw.get("service") or []):
        name = s.get("name")
        if not isinstance(name, str) or not name:
            _fail(f"service {i}: name must be a non-empty string")
        if name in seen_svc:
            _fail(f"service {i}: {name!r} declared twice")
        seen_svc.add(name)
        sa = s.get("service_account")
        if sa not in seen_sa:
            _fail(f"service {i}: {sa!r} is not a declared service account")
        if sa in bound_sa:
            _fail(f"service {i}: {sa!r} already bound — identities are per-workload (AR-8)")
        bound_sa.add(sa)
        services.append(ServiceMap(name=name, service_account=sa))

    invokers: list[InvokerRule] = []
    seen_invoker_leg: set[tuple[str, str]] = set()
    for i, v in enumerate(raw.get("invoker") or []):
        service = v.get("service")
        if service not in seen_svc:
            _fail(f"invoker {i}: {service!r} is not a declared service")
        leg = v.get("leg", "services")
        if leg not in ("services", "jobs"):
            _fail(f"invoker {i}: leg {leg!r} must be services|jobs")
        if (service, leg) in seen_invoker_leg:
            _fail(f"invoker {i}: a {leg} rule for {service!r} is already declared")
        seen_invoker_leg.add((service, leg))
        grant = tuple(
            _check_member(m, declared=seen_sa, context=f"invoker {i} grant")
            for m in v.get("grant") or []
        )
        revoke_raw = v.get("revoke") or []
        revoke: list[str] = []
        for m in revoke_raw:
            if not isinstance(m, str) or m not in PUBLIC_MEMBERS | SYMBOLIC_MEMBERS:
                _fail(
                    f"invoker {i} revoke: {m!r} — only allUsers/"
                    "allAuthenticatedUsers or a symbolic member"
                )
            revoke.append(m)
        if not grant and not revoke:
            _fail(f"invoker {i}: nothing granted or revoked")
        invokers.append(InvokerRule(service=service, grant=grant, revoke=tuple(revoke), leg=leg))

    job_classes: list[JobClass] = []
    seen_class: set[str] = set()
    class_bound_sa: set[str] = set()
    for i, c in enumerate(raw.get("job_class") or []):
        name = c.get("name")
        if not isinstance(name, str) or not name:
            _fail(f"job_class {i}: name must be a non-empty string")
        if name in seen_class:
            _fail(f"job_class {i}: {name!r} declared twice")
        seen_class.add(name)
        sa = c.get("service_account")
        if sa not in seen_sa:
            _fail(f"job_class {i}: {sa!r} is not a declared service account")
        if sa in bound_sa:
            _fail(
                f"job_class {i}: {sa!r} is a service identity — "
                "service and job identities never mix (AR-8)"
            )
        if sa in class_bound_sa:
            _fail(f"job_class {i}: {sa!r} already bound — one identity per class")
        sa_row = next(s for s in sas if s.id == sa)
        if sa_row.reserved:
            _fail(
                f"job_class {i}: {sa!r} is reserved — a reserved identity "
                "holds no workload until its owning row lands"
            )
        class_bound_sa.add(sa)
        jobs = tuple(_check_name(j, f"job_class {name} jobs") for j in c.get("jobs") or [])
        if not (c.get("sources") or c.get("batches") or c.get("probes") or jobs):
            _fail(f"job_class {name}: claims no jobs — sources/batches/probes/jobs")
        job_classes.append(
            JobClass(
                name=name,
                service_account=sa,
                sources=bool(c.get("sources")),
                batches=bool(c.get("batches")),
                probes=bool(c.get("probes")),
                jobs=jobs,
            )
        )

    # A group flag or explicit name may claim a cadence job only once — that
    # check needs cadence and runs in resolve_job_map; here we refuse explicit
    # duplicates inside one class.
    for cls in job_classes:
        if len(set(cls.jobs)) != len(cls.jobs):
            _fail(f"job_class {cls.name}: a job is listed twice")

    job_invokers: list[JobInvoker] = []
    for i, v in enumerate(raw.get("job_invoker") or []):
        member = v.get("member")
        if member not in seen_sa:
            _fail(f"job_invoker {i}: {member!r} is not a declared service account")
        if member in bound_sa or member in class_bound_sa:
            _fail(
                f"job_invoker {i}: {member!r} is a workload identity — "
                "the invoker SA is never a runtime identity (P25.7)"
            )
        targets = v.get("targets")
        if targets != "scheduled":
            _fail(f"job_invoker {i}: targets {targets!r} must be 'scheduled'")
        job_invokers.append(JobInvoker(member=member, targets=targets))

    remove_roles: list[RemoveRole] = []
    for i, r in enumerate(raw.get("remove_role") or []):
        member = r.get("member")
        if member not in SYMBOLIC_MEMBERS and member not in seen_sa:
            _fail(f"remove_role {i}: member {member!r} must be symbolic or a declared SA")
        role = r.get("role")
        if not isinstance(role, str) or not role.startswith("roles/"):
            _fail(f"remove_role {i}: role {role!r} must be a roles/* role")
        remove_roles.append(RemoveRole(member=member, role=role))

    secrets: list[Secret] = []
    seen_secret: set[str] = set()
    for i, s in enumerate(raw.get("secret") or []):
        name = s.get("name")
        if not isinstance(name, str) or not name:
            _fail(f"secret {i}: name must be a non-empty string")
        if name in seen_secret:
            _fail(f"secret {i}: {name!r} declared twice")
        seen_secret.add(name)
        consumers = tuple(
            _check_member(c, declared=seen_sa, context=f"secret {name} consumers")
            for c in s.get("consumers") or []
        )
        jobs_revoke = tuple(
            _check_member(m, declared=seen_sa, context=f"secret {name} jobs_revoke")
            for m in s.get("jobs_revoke") or []
        )
        for m in jobs_revoke:
            if m in consumers:
                _fail(
                    f"secret {name}: {m!r} is both a consumer and a jobs_revoke "
                    "member — revoke means the jobs leg removes it"
                )
        secrets.append(Secret(name=name, consumers=consumers, jobs_revoke=jobs_revoke))

    expected_raw = raw.get("expected_job_count")
    expected_job_count: int | None = None
    if expected_raw is not None:
        if not isinstance(expected_raw, int) or expected_raw <= 0:
            _fail("expected_job_count must be a positive integer")
        expected_job_count = expected_raw
    if job_classes and expected_job_count is None:
        _fail("job classes declared but expected_job_count is missing")

    # Identity/workload bookkeeping: a non-reserved SA binds to exactly one
    # service or one job class; a reserved SA binds nothing (the job_invoker
    # member is exempt — invoker is a grant, not a workload).
    unbound = seen_sa - bound_sa - class_bound_sa
    for sa in sas:
        if sa.id in unbound and not sa.reserved and sa.id not in {v.member for v in job_invokers}:
            _fail(
                f"service account {sa.id!r} bound to no workload — "
                "per-workload identities only (mark it reserved instead)"
            )
    for sa in sas:
        if sa.reserved and (
            sa.id in bound_sa
            or sa.id in class_bound_sa
            or any(r.service_account == sa.id for r in project_roles)
            or any(r.service_account == sa.id for r in bucket_roles)
            or any(sa.id in s.consumers for s in secrets)
        ):
            _fail(
                f"reserved service account {sa.id!r} carries a binding — "
                "reserved identities hold nothing until their owning row lands"
            )

    return Declaration(
        service_accounts=tuple(sas),
        project_roles=tuple(project_roles),
        bucket_roles=tuple(bucket_roles),
        services=tuple(services),
        invokers=tuple(invokers),
        secrets=tuple(secrets),
        job_classes=tuple(job_classes),
        job_invokers=tuple(job_invokers),
        remove_roles=tuple(remove_roles),
        expected_job_count=expected_job_count,
    )


def sa_email(project: str, sa_id: str) -> str:
    return f"{sa_id}@{project}.iam.gserviceaccount.com"


def compute_sa_email(project_number: str | int) -> str:
    return f"{project_number}-compute@developer.gserviceaccount.com"


def resolve_member(member: str, project: str, compute_sa: str | None = None) -> str:
    """Resolve a declaration member to an IAM member string."""
    if member == "default-compute":
        if not compute_sa:
            _fail("default-compute needs --compute-sa or a recorded compute-sa.txt")
        return f"serviceAccount:{compute_sa}"
    if member == "operator":
        _fail("the operator consumer is a record only — never an IAM member")
    if member in PUBLIC_MEMBERS:
        return member
    return f"serviceAccount:{sa_email(project, member)}"


def condition_expression(project: str, bucket: str, prefix: str) -> str:
    """The CEL resource.name condition for a conditioned bucket grant."""
    return f"resource.name.startsWith('projects/_/buckets/{project}-{bucket}/objects/{prefix}')"


def _leg_includes(leg: str, *legs: str) -> bool:
    return leg == "all" or leg in legs


def _service_sa_ids(decl: Declaration) -> set[str]:
    return {s.service_account for s in decl.services}


def _job_sa_ids(decl: Declaration) -> set[str]:
    return {c.service_account for c in decl.job_classes}


# --- the mutation plan ---------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """One planned mutation with its rollback (printed, then executed by
    ``run`` in apply mode). ``command``/``rollback`` are gcloud argv lists
    rendered for display; ``placeholder`` marks values resolved at apply
    time (the caller identity, the recorded prior SA)."""

    phase: str
    note: str
    command: list[str]
    rollback: list[str] | None = None


def _sa_steps(sa: ServiceAccount, project: str) -> Step:
    return Step(
        phase="identities",
        note=f"create {sa.id} — {sa.purpose}",
        command=[
            "gcloud",
            "iam",
            "service-accounts",
            "create",
            sa.id,
            f"--display-name={sa.display_name}",
            f"--project={project}",
        ],
        rollback=[
            "gcloud",
            "iam",
            "service-accounts",
            "delete",
            sa_email(project, sa.id),
            f"--project={project}",
            "--quiet",
        ],
    )


def _binding_steps(decl: Declaration, project: str, sa_ids: set[str]) -> list[Step]:
    steps: list[Step] = []
    for r in decl.project_roles:
        if r.service_account not in sa_ids:
            continue
        steps.append(
            Step(
                phase="bindings",
                note=f"project: {r.service_account} → {r.role}",
                command=[
                    "gcloud",
                    "projects",
                    "add-iam-policy-binding",
                    project,
                    f"--member=serviceAccount:{sa_email(project, r.service_account)}",
                    f"--role={r.role}",
                ],
                rollback=[
                    "gcloud",
                    "projects",
                    "remove-iam-policy-binding",
                    project,
                    f"--member=serviceAccount:{sa_email(project, r.service_account)}",
                    f"--role={r.role}",
                ],
            )
        )
    for b in decl.bucket_roles:
        if b.service_account not in sa_ids:
            continue
        cmd = [
            "gcloud",
            "storage",
            "buckets",
            "add-iam-policy-binding",
            f"gs://{project}-{b.bucket}",
            f"--member=serviceAccount:{sa_email(project, b.service_account)}",
            f"--role={b.role}",
        ]
        note = f"bucket {project}-{b.bucket}: {b.service_account} → {b.role}"
        if b.condition_title:
            expr = condition_expression(project, b.bucket, b.condition_prefix or "")
            cmd += [
                f"--condition-title={b.condition_title}",
                f"--condition-description=P34.42b/ADR-201: OCFL inventory-head "
                f"rewrite under {b.condition_prefix} only (SIG-STORE-048)",
                f"--condition-expression={expr}",
            ]
            note += f" (conditioned: {b.condition_title} on {b.condition_prefix})"
        steps.append(
            Step(
                phase="bindings",
                note=note,
                command=cmd,
                rollback=[
                    "gcloud",
                    "storage",
                    "buckets",
                    "remove-iam-policy-binding",
                    f"gs://{project}-{b.bucket}",
                    f"--member=serviceAccount:{sa_email(project, b.service_account)}",
                    f"--role={b.role}",
                    "--all",  # removes the conditioned binding wholesale on rollback
                ],
            )
        )
    for s in decl.secrets:
        for consumer in s.consumers:
            if consumer not in sa_ids:
                continue
            if consumer in SYMBOLIC_MEMBERS or consumer in PUBLIC_MEMBERS:
                continue
            steps.append(
                Step(
                    phase="bindings",
                    note=f"secret {s.name}: {consumer} → {SECRET_ACCESSOR_ROLE}",
                    command=[
                        "gcloud",
                        "secrets",
                        "add-iam-policy-binding",
                        s.name,
                        f"--project={project}",
                        f"--member=serviceAccount:{sa_email(project, consumer)}",
                        f"--role={SECRET_ACCESSOR_ROLE}",
                    ],
                    rollback=[
                        "gcloud",
                        "secrets",
                        "remove-iam-policy-binding",
                        s.name,
                        f"--project={project}",
                        f"--member=serviceAccount:{sa_email(project, consumer)}",
                        f"--role={SECRET_ACCESSOR_ROLE}",
                    ],
                )
            )
    return steps


def plan_steps(
    decl: Declaration,
    project: str,
    region: str,
    cadence: dict[str, Any] | None = None,
    leg: str = "all",
) -> list[Step]:
    """The ordered leg: identities → bindings → revisions/jobs → invokers →
    editor removal.

    ``leg`` scopes the plan: ``services`` = the P34.42a leg (the three
    service identities, their bindings, the same-image revisions, the
    leg=services invoker rule); ``jobs`` = the P34.42b leg (the job-class
    and reserved identities, their bindings + conditioned grants + secret
    revokes, the 88 same-image job updates, the scheduler-invoker move, the
    leg=jobs invoker rule, the roles/editor removal); ``all`` = the full
    end-state plan. Pure: values the contract requires be read live render
    as ``<...>`` placeholders the shell wrapper fills.
    """
    if leg not in LEGS:
        _fail(f"leg {leg!r} must be one of {LEGS}")
    steps: list[Step] = []
    service_sas = _service_sa_ids(decl)
    job_sas = _job_sa_ids(decl)

    if _leg_includes(leg, "services", "jobs"):
        if leg == "services":
            want_sas = [s for s in decl.service_accounts if s.id in service_sas]
        elif leg == "jobs":
            want_sas = [s for s in decl.service_accounts if s.id not in service_sas]
        else:
            want_sas = list(decl.service_accounts)
        for sa in want_sas:
            steps.append(_sa_steps(sa, project))

        if leg == "services":
            sa_ids = service_sas
        elif leg == "jobs":
            sa_ids = (set(s.id for s in decl.service_accounts) - service_sas) | {
                c for s in decl.secrets for c in s.consumers if c in job_sas
            }
        else:
            sa_ids = {s.id for s in decl.service_accounts}
        steps += _binding_steps(decl, project, sa_ids)

    if _leg_includes(leg, "jobs"):
        # The jobs leg also removes the stale secret accessors the jobs no
        # longer run as (jobs_revoke members — resolved at apply time).
        for s in decl.secrets:
            for member in s.jobs_revoke:
                resolved = (
                    "<default-compute resolved at apply>"
                    if member == "default-compute"
                    else resolve_member(member, project)
                )
                steps.append(
                    Step(
                        phase="bindings",
                        note=f"secret {s.name}: revoke {SECRET_ACCESSOR_ROLE} from {member}",
                        command=[
                            "gcloud",
                            "secrets",
                            "remove-iam-policy-binding",
                            s.name,
                            f"--project={project}",
                            f"--member=<{member} resolved at apply — {resolved}>",
                            f"--role={SECRET_ACCESSOR_ROLE}",
                        ],
                        rollback=[
                            "gcloud",
                            "secrets",
                            "add-iam-policy-binding",
                            s.name,
                            f"--project={project}",
                            f"--member=<{member} resolved at apply — {resolved}>",
                            f"--role={SECRET_ACCESSOR_ROLE}",
                        ],
                    )
                )

    if _leg_includes(leg, "services"):
        for svc in decl.services:
            steps.append(
                Step(
                    phase="revisions",
                    note=(
                        f"{svc.name}: one same-image revision on "
                        f"{svc.service_account} (image digest unchanged)"
                    ),
                    command=[
                        "gcloud",
                        "run",
                        "services",
                        "update",
                        svc.name,
                        f"--service-account={sa_email(project, svc.service_account)}",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                    rollback=[
                        "gcloud",
                        "run",
                        "services",
                        "update",
                        svc.name,
                        "--service-account=<recorded prior SA — prestate service describe>",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                )
            )

    if _leg_includes(leg, "jobs"):
        if cadence is None and decl.job_classes:
            _fail("the jobs leg needs the cadence file for the job map")
        job_map = resolve_job_map(decl, cadence or {})
        class_sa = {c.name: c.service_account for c in decl.job_classes}
        for job in sorted(job_map):
            job_sa = class_sa[job_map[job]]
            steps.append(
                Step(
                    phase="jobs",
                    note=(
                        f"{job}: update --service-account={job_sa} "
                        f"(class {job_map[job]}; image unchanged)"
                    ),
                    command=[
                        "gcloud",
                        "run",
                        "jobs",
                        "update",
                        job,
                        f"--service-account={sa_email(project, job_sa)}",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                    rollback=[
                        "gcloud",
                        "run",
                        "jobs",
                        "update",
                        job,
                        "--service-account=<recorded prior SA — prestate job describe>",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                )
            )
        for v in decl.job_invokers:
            if v.targets == "scheduled":
                if cadence is None:
                    _fail("the scheduler invoker move needs the cadence file")
                for job in sorted(set(cadence_scheduled_jobs(cadence))):
                    steps.append(
                        Step(
                            phase="invokers",
                            note=(
                                f"{job}: {RUN_INVOKER_ROLE} to {v.member} "
                                "(scheduler OIDC stays sig-scheduler)"
                            ),
                            command=[
                                "gcloud",
                                "run",
                                "jobs",
                                "add-iam-policy-binding",
                                job,
                                f"--member=serviceAccount:{sa_email(project, v.member)}",
                                f"--role={RUN_INVOKER_ROLE}",
                                f"--region={region}",
                                f"--project={project}",
                            ],
                            rollback=[
                                "gcloud",
                                "run",
                                "jobs",
                                "remove-iam-policy-binding",
                                job,
                                f"--member=serviceAccount:{sa_email(project, v.member)}",
                                f"--role={RUN_INVOKER_ROLE}",
                                f"--region={region}",
                                f"--project={project}",
                            ],
                        )
                    )

    # Service invoker rules: the leg-matched rule per service (`all` judges
    # the last-declared jobs posture).
    for svc in decl.services:
        rule = decl.invoker_rule(svc.name, leg)
        if rule is None:
            continue
        inv_phase = "invokers" if _leg_includes(leg, "jobs") and rule.leg == "jobs" else "invoker"
        for member in rule.grant:
            steps.append(
                Step(
                    phase=inv_phase,
                    note=f"{rule.service}: grant {RUN_INVOKER_ROLE} to the caller ({member})",
                    command=[
                        "gcloud",
                        "run",
                        "services",
                        "add-iam-policy-binding",
                        rule.service,
                        f"--member=<{member} resolved at apply>",
                        f"--role={RUN_INVOKER_ROLE}",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                    rollback=[
                        "gcloud",
                        "run",
                        "services",
                        "set-iam-policy",
                        rule.service,
                        "<recorded invoker policy — prestate get-iam-policy>",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                )
            )
        for member in rule.revoke:
            steps.append(
                Step(
                    phase=inv_phase,
                    note=f"{rule.service}: revoke {RUN_INVOKER_ROLE} from {member}",
                    command=[
                        "gcloud",
                        "run",
                        "services",
                        "remove-iam-policy-binding",
                        rule.service,
                        f"--member=<{member} resolved at apply>"
                        if member in SYMBOLIC_MEMBERS
                        else f"--member={member}",
                        f"--role={RUN_INVOKER_ROLE}",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                    rollback=None,  # covered by the recorded set-iam-policy above
                )
            )

    if _leg_includes(leg, "jobs"):
        for r in decl.remove_roles:
            steps.append(
                Step(
                    phase="editor",
                    note=(
                        f"remove {r.role} from {r.member} — the last mutation, "
                        "only after no workload still runs as it (G1-01)"
                    ),
                    command=[
                        "gcloud",
                        "projects",
                        "remove-iam-policy-binding",
                        project,
                        f"--member=<{r.member} resolved at apply>",
                        f"--role={r.role}",
                    ],
                    rollback=[
                        "gcloud",
                        "projects",
                        "add-iam-policy-binding",
                        project,
                        f"--member=<{r.member} resolved at apply>",
                        f"--role={r.role}",
                    ],
                )
            )
    return steps


# --- the recorded-snapshot diff (the --verify half) ----------------------------


@dataclass(frozen=True)
class Snapshot:
    """A recorded IAM snapshot directory (the prestate/poststate capture)."""

    service_accounts: set[str] | None  # emails from `iam service-accounts list`
    project_policy: dict[str, Any] | None
    bucket_policies: dict[str, dict[str, Any]]  # bucket suffix → policy
    secret_policies: dict[str, dict[str, Any]]  # secret name → policy
    service_describes: dict[str, dict[str, Any]]  # service name → describe JSON
    service_policies: dict[str, dict[str, Any]]  # service name → IAM policy
    job_describes: dict[str, dict[str, Any]]  # job name → describe JSON
    scheduler_describes: dict[str, dict[str, Any]]  # job name → trigger describe
    run_jobs: set[str] | None  # every live Cloud Run job name (`run jobs list`)
    compute_sa: str | None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _job_names_from_listing(raw: Any) -> set[str]:
    """`gcloud run jobs list --format=json` rows → names (v1 metadata.name
    or the resource path's last segment)."""
    out: set[str] = set()
    for r in raw or []:
        name = ((r.get("metadata") or {}).get("name")) or r.get("name")
        if name:
            out.add(str(name).rsplit("/", 1)[-1])
    return out


def load_snapshot(state_dir: str | Path) -> Snapshot:
    """Read a capture dir (files named by the shell legs' prestate)."""
    d = Path(state_dir)
    sas: set[str] | None = None
    sa_file = d / "service-accounts.json"
    if sa_file.is_file():
        sas = {str(r.get("email")) for r in _load_json(sa_file) if r.get("email")}
    pj = d / "project-iam.json"
    project_policy = _load_json(pj) if pj.is_file() else None
    buckets: dict[str, dict[str, Any]] = {}
    secrets: dict[str, dict[str, Any]] = {}
    describes: dict[str, dict[str, Any]] = {}
    policies: dict[str, dict[str, Any]] = {}
    jobs: dict[str, dict[str, Any]] = {}
    schedulers: dict[str, dict[str, Any]] = {}
    run_jobs: set[str] | None = None
    for f in sorted(d.glob("*.json")):
        if f.name.startswith("bucket-") and f.name.endswith("-iam.json"):
            buckets[f.name[len("bucket-") : -len("-iam.json")]] = _load_json(f)
        elif f.name.startswith("secret-") and f.name.endswith("-iam.json"):
            secrets[f.name[len("secret-") : -len("-iam.json")]] = _load_json(f)
        elif f.name.startswith("service-") and f.name.endswith("-iam.json"):
            policies[f.name[len("service-") : -len("-iam.json")]] = _load_json(f)
        elif f.name == "run-jobs.json":
            run_jobs = _job_names_from_listing(_load_json(f))
        elif f.name.startswith("job-") and f.name.endswith("-iam.json"):
            pass  # per-job invoker policy — judged via scheduler describes
        elif f.name.startswith("job-") and f.name.endswith(".json"):
            jobs[f.name[len("job-") : -len(".json")]] = _load_json(f)
        elif f.name.startswith("sched-") and f.name.endswith(".json"):
            schedulers[f.name[len("sched-") : -len(".json")]] = _load_json(f)
        elif (
            f.name.startswith("service-")
            and not f.name.endswith("-iam.json")
            and f.name != "service-accounts.json"
        ):
            describes[f.name[len("service-") : -len(".json")]] = _load_json(f)
    compute = None
    cfile = d / "compute-sa.txt"
    if cfile.is_file():
        compute = cfile.read_text(encoding="utf-8").strip() or None
    return Snapshot(
        service_accounts=sas,
        project_policy=project_policy,
        bucket_policies=buckets,
        secret_policies=secrets,
        service_describes=describes,
        service_policies=policies,
        job_describes=jobs,
        scheduler_describes=schedulers,
        run_jobs=run_jobs,
        compute_sa=compute,
    )


def _policy_members(policy: dict[str, Any], role: str) -> set[str]:
    out: set[str] = set()
    for b in policy.get("bindings") or []:
        if b.get("role") == role:
            out.update(str(m) for m in b.get("members") or [])
    return out


def _conditioned_members(
    policy: dict[str, Any], role: str, title: str
) -> tuple[set[str], str | None]:
    """Members of the binding carrying condition `title`, plus its expression."""
    out: set[str] = set()
    expr: str | None = None
    for b in policy.get("bindings") or []:
        if b.get("role") != role:
            continue
        cond = b.get("condition") or {}
        if cond.get("title") == title:
            out.update(str(m) for m in b.get("members") or [])
            expr = cond.get("expression")
    return out, expr


def _all_members(policy: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for b in policy.get("bindings") or []:
        out.update(str(m) for m in b.get("members") or [])
    return out


def _service_account_name(desc: dict[str, Any]) -> str | None:
    """The runtime identity off a `run services describe` — v1
    (spec.template.spec.serviceAccountName) or v2 (template.serviceAccount)."""
    spec = ((desc.get("spec") or {}).get("template") or {}).get("spec") or {}
    if spec.get("serviceAccountName"):
        return str(spec["serviceAccountName"])
    v2 = (desc.get("template") or {}).get("serviceAccount")
    return str(v2) if v2 else None


def _service_image(desc: dict[str, Any]) -> str | None:
    spec = ((desc.get("spec") or {}).get("template") or {}).get("spec") or {}
    for c in spec.get("containers") or []:
        if c.get("image"):
            return str(c["image"])
    for c in ((desc.get("template") or {}).get("containers")) or []:
        if c.get("image"):
            return str(c["image"])
    return None


def _job_template(desc: dict[str, Any]) -> dict[str, Any]:
    """The job's task-template spec — v1 (spec.template.spec) or v2
    (template.template)."""
    spec = ((desc.get("spec") or {}).get("template") or {}).get("spec")
    if isinstance(spec, dict):
        return spec
    inner = ((desc.get("template") or {}).get("template")) or {}
    return inner if isinstance(inner, dict) else {}


def _job_service_account(desc: dict[str, Any]) -> str | None:
    tpl = _job_template(desc)
    sa = tpl.get("serviceAccountName") or tpl.get("serviceAccount")
    return str(sa) if sa else None


def _job_image(desc: dict[str, Any]) -> str | None:
    tpl = _job_template(desc)
    for c in tpl.get("containers") or []:
        if c.get("image"):
            return str(c["image"])
    return None


def _scheduler_identity(desc: dict[str, Any]) -> str | None:
    """The SA a Cloud Scheduler trigger signs as (OAuth or OIDC token)."""
    http = desc.get("httpTarget") or {}
    for key in ("oauthToken", "oidcToken"):
        tok = http.get(key) or {}
        if tok.get("serviceAccountEmail"):
            return str(tok["serviceAccountEmail"])
    return None


def diff_snapshot(
    decl: Declaration,
    snap: Snapshot,
    project: str,
    compute_sa: str | None = None,
    cadence: dict[str, Any] | None = None,
    leg: str = "all",
) -> list[str]:
    """Judge a recorded snapshot against the declaration, scoped to `leg`.
    Empty = the declaration holds exactly for that leg's posture. Each line
    names one DRIFT/UNREADABLE finding — the read-only audit (deliverable 5):
    a missing identity or binding, a wrong runtime SA on a service or job, a
    lingering allUsers/stale invoker, a declared SA holding an undeclared or
    basic role, a runtime SA reading a foreign secret, a scheduler trigger
    signing as the wrong identity, or the default compute SA still holding
    roles/editor.
    """
    if leg not in LEGS:
        _fail(f"leg {leg!r} must be one of {LEGS}")
    compute = compute_sa or snap.compute_sa
    diffs: list[str] = []
    declared_emails = {sa.id: sa_email(project, sa.id) for sa in decl.service_accounts}
    declared_set = set(declared_emails.values())
    service_sas = _service_sa_ids(decl)
    if leg == "services":
        judged_sas = [s for s in decl.service_accounts if s.id in service_sas]
        judged_sa_ids = service_sas
    else:
        judged_sas = list(decl.service_accounts)
        judged_sa_ids = {s.id for s in decl.service_accounts}

    if snap.service_accounts is not None:
        for sa in judged_sas:
            if declared_emails[sa.id] not in snap.service_accounts:
                diffs.append(f"missing service account {declared_emails[sa.id]}")
    else:
        diffs.append("UNREADABLE: no service-accounts.json in the snapshot")

    if snap.project_policy is None:
        diffs.append("UNREADABLE: no project-iam.json in the snapshot")
    else:
        for r in decl.project_roles:
            if r.service_account not in judged_sa_ids:
                continue
            want = f"serviceAccount:{declared_emails[r.service_account]}"
            if want not in _policy_members(snap.project_policy, r.role):
                diffs.append(f"missing project binding {want} → {r.role}")
        # A declared SA must hold ONLY its declared project roles — anything
        # else (esp. a basic role) is exactly the G1-01 defect re-appearing.
        declared_roles = {
            (f"serviceAccount:{declared_emails[r.service_account]}", r.role)
            for r in decl.project_roles
        }
        for b in snap.project_policy.get("bindings") or []:
            role = str(b.get("role"))
            for m in b.get("members") or []:
                m = str(m)
                if m.startswith("serviceAccount:") and m[len("serviceAccount:") :] in declared_set:
                    if (m, role) not in declared_roles:
                        diffs.append(f"undeclared project role on a runtime SA: {m} → {role}")
                    if role in BASIC_ROLES:
                        diffs.append(f"basic role on a runtime SA: {m} → {role}")
        if _leg_includes(leg, "jobs"):
            for rr in decl.remove_roles:
                if rr.member == "default-compute":
                    if not compute:
                        diffs.append(
                            "UNREADABLE: the roles/editor removal needs compute-sa resolution"
                        )
                        continue
                    member = f"serviceAccount:{compute}"
                else:
                    member = resolve_member(rr.member, project, compute)
                if member in _policy_members(snap.project_policy, rr.role):
                    diffs.append(f"{rr.member} still holds {rr.role} — the removal did not land")

    for br in decl.bucket_roles:
        if br.service_account not in judged_sa_ids:
            continue
        policy = snap.bucket_policies.get(br.bucket)
        want = f"serviceAccount:{declared_emails[br.service_account]}"
        if policy is None:
            diffs.append(f"UNREADABLE: no bucket-{br.bucket}-iam.json in the snapshot")
            continue
        if br.condition_title:
            members, expr = _conditioned_members(policy, br.role, br.condition_title)
            if want not in members:
                diffs.append(
                    f"missing conditioned bucket binding {want} → {br.role} "
                    f"(condition {br.condition_title}) on {project}-{br.bucket}"
                )
            want_expr = condition_expression(project, br.bucket, br.condition_prefix or "")
            if expr is not None and expr != want_expr:
                diffs.append(
                    f"conditioned binding on {project}-{br.bucket} carries a "
                    f"different expression: {expr!r} != {want_expr!r}"
                )
        elif want not in _policy_members(policy, br.role):
            diffs.append(f"missing bucket binding {want} → {br.role} on {project}-{br.bucket}")
        # A declared SA must hold ONLY its declared role on a declared bucket —
        # objectAdmin on the evidence stores is exactly the G1-01 defect.
        # Public members keep viewer only (the site's public posture).
        declared_bucket_roles = {
            (f"serviceAccount:{declared_emails[b.service_account]}", b.role)
            for b in decl.bucket_roles
            if b.bucket == br.bucket
        }
        for bb in policy.get("bindings") or []:
            role = str(bb.get("role"))
            for m in bb.get("members") or []:
                m = str(m)
                if m.startswith("serviceAccount:") and m[len("serviceAccount:") :] in declared_set:
                    if (m, role) not in declared_bucket_roles:
                        diffs.append(
                            f"undeclared bucket role on a runtime SA: {m} → {role} "
                            f"on {project}-{br.bucket}"
                        )
                if m in PUBLIC_MEMBERS and role != "roles/storage.objectViewer":
                    diffs.append(
                        f"public member holds a non-viewer role on {project}-{br.bucket}: "
                        f"{m} → {role}"
                    )

    for s in decl.secrets:
        policy = snap.secret_policies.get(s.name)
        if policy is None:
            # Only secrets the snapshot recorded are judged — the leg reads
            # all eleven, but a partial snapshot judges what it carries.
            continue
        accessors = _policy_members(policy, SECRET_ACCESSOR_ROLE)
        # "readable only by its consumers": the allowed set is the declared
        # consumers resolved, plus — under the services leg only — the
        # jobs_revoke members still holding the accessor (the jobs still run
        # as them until the jobs leg moves + revokes).
        allowed: set[str] = set()
        required: set[str] = set()
        for consumer in s.consumers:
            if consumer == "default-compute":
                if compute:
                    allowed.add(f"serviceAccount:{compute}")
                    if leg == "services":
                        required.add(f"serviceAccount:{compute}")
            elif consumer == "operator":
                continue  # honoured below via the user: prefix rule
            elif consumer in PUBLIC_MEMBERS:
                continue  # the fail-closed loader already refuses it
            else:
                allowed.add(f"serviceAccount:{declared_emails[consumer]}")
                if leg != "services" or consumer in service_sas:
                    required.add(f"serviceAccount:{declared_emails[consumer]}")
        for member in s.jobs_revoke:
            resolved = (
                f"serviceAccount:{compute}" if member == "default-compute" and compute else None
            )
            if member != "default-compute":
                resolved = resolve_member(member, project, compute)
            if resolved is None:
                continue
            if leg == "services":
                allowed.add(resolved)
            elif resolved in accessors:
                diffs.append(
                    f"stale secret accessor {resolved} on {s.name} — the jobs leg revokes it"
                )
        for want in required:
            if want not in accessors:
                diffs.append(f"missing secret accessor {want} on {s.name}")
        for m in accessors:
            if m in PUBLIC_MEMBERS:
                diffs.append(f"public member on a secret: {m} on {s.name}")
            elif m in allowed:
                continue
            elif m.startswith("user:") and "operator" in s.consumers:
                continue  # the operator's own account — a record, never named
            else:
                diffs.append(f"undeclared secret accessor {m} on {s.name}")

    if _leg_includes(leg, "services"):
        for svc in decl.services:
            desc = snap.service_describes.get(svc.name)
            want = declared_emails[svc.service_account]
            if desc is None:
                diffs.append(f"UNREADABLE: no service-{svc.name}.json describe in the snapshot")
                continue
            got = _service_account_name(desc)
            if got != want:
                diffs.append(f"service {svc.name} runs as {got!r}, declared {want}")

    if _leg_includes(leg, "jobs") and decl.job_classes:
        if cadence is None:
            _fail("the jobs leg needs the cadence file for the job map")
        job_map = resolve_job_map(decl, cadence)
        class_sa = {c.name: c.service_account for c in decl.job_classes}
        if snap.run_jobs is not None:
            missing_from_map = sorted(snap.run_jobs - set(job_map))
            if missing_from_map:
                diffs.append(
                    f"live job(s) claimed by no class: {missing_from_map} — "
                    "re-count and extend the map before applying"
                )
            gone = sorted(set(job_map) - snap.run_jobs)
            if gone:
                diffs.append(f"declared job(s) absent live: {gone}")
            if decl.expected_job_count is not None and len(snap.run_jobs) != (
                decl.expected_job_count
            ):
                diffs.append(
                    f"live job count {len(snap.run_jobs)} != declared "
                    f"{decl.expected_job_count} — re-count before applying (G1-C07)"
                )
        else:
            diffs.append("UNREADABLE: no run-jobs.json in the snapshot")
        for job, cls in sorted(job_map.items()):
            desc = snap.job_describes.get(job)
            want = declared_emails[class_sa[cls]]
            if desc is None:
                diffs.append(f"UNREADABLE: no job-{job}.json describe in the snapshot")
                continue
            got = _job_service_account(desc)
            if got != want:
                diffs.append(f"job {job} runs as {got!r}, declared {want} (class {cls})")
        for v in decl.job_invokers:
            if v.targets != "scheduled":
                continue
            want = sa_email(project, v.member)
            for job in sorted(set(cadence_scheduled_jobs(cadence))):
                desc = snap.scheduler_describes.get(job)
                if desc is None:
                    diffs.append(
                        f"UNREADABLE: no sched-{job}.json trigger describe in the snapshot"
                    )
                    continue
                got = _scheduler_identity(desc)
                if got != want:
                    diffs.append(f"scheduler trigger for {job} signs as {got!r}, declared {want}")

    for svc in decl.services:
        rule = decl.invoker_rule(svc.name, leg)
        if rule is None:
            continue
        policy = snap.service_policies.get(rule.service)
        if policy is None:
            diffs.append(f"UNREADABLE: no service-{rule.service}-iam.json in the snapshot")
            continue
        public = _all_members(policy) & PUBLIC_MEMBERS
        for m in public:
            if m in rule.revoke:
                diffs.append(f"{rule.service} still invokable by {m}")
        invoker_members = _policy_members(policy, RUN_INVOKER_ROLE)
        for member in rule.revoke:
            if member in SYMBOLIC_MEMBERS:
                if member == "default-compute" and not compute:
                    continue
                resolved = resolve_member(member, project, compute) if compute else None
                if resolved and resolved in invoker_members:
                    diffs.append(f"{rule.service} still invokable by {resolved}")
        for member in rule.grant:
            if member == "operator":
                continue
            if member == "default-compute" and not compute:
                diffs.append(
                    f"UNREADABLE: {rule.service} invoker grant needs compute-sa resolution"
                )
                continue
            want = resolve_member(member, project, compute)
            if want not in invoker_members:
                diffs.append(f"missing invoker grant {want} on {rule.service}")
    return diffs


def check_same_image(pre_dir: str | Path, post_dir: str | Path) -> list[str]:
    """The same-image gate: every service's container image and every job's
    container image must be byte-identical between the two recorded describes
    (the leg changes the identity only). Returns the violations; empty = same
    image everywhere.
    """
    problems: list[str] = []
    pre = Path(pre_dir)
    post = Path(post_dir)
    compared = 0
    describes = [
        f
        for f in sorted(post.glob("service-*.json"))
        if not f.name.endswith("-iam.json") and f.name != "service-accounts.json"
    ]
    for f in describes:
        pf = pre / f.name
        if not pf.is_file():
            problems.append(f"no recorded prestate describe for {f.name}")
            continue
        a = _service_image(_load_json(pf))
        b = _service_image(_load_json(f))
        svc = f.name[len("service-") : -len(".json")]
        if a != b:
            problems.append(f"{svc}: image changed {a!r} → {b!r} — not a same-image revision")
        compared += 1
    for f in sorted(post.glob("job-*.json")):
        if f.name.endswith("-iam.json"):
            continue
        pf = pre / f.name
        if not pf.is_file():
            problems.append(f"no recorded prestate describe for {f.name}")
            continue
        a = _job_image(_load_json(pf))
        b = _job_image(_load_json(f))
        job = f.name[len("job-") : -len(".json")]
        if a != b:
            problems.append(
                f"{job}: image changed {a!r} → {b!r} — identity move must not roll code"
            )
        compared += 1
    if compared == 0:
        problems.append("no poststate service/job describes to compare")
    return problems


# --- CLI (the `sig-ops iam` verb surface) --------------------------------------


def _write(out: str | None, text: str) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        sys.stdout.write(text)


def _load_cadence_arg(raw: str | None, decl: Declaration, leg: str) -> dict[str, Any] | None:
    needs = leg != "services" and (decl.job_classes or decl.job_invokers)
    if raw is None and not needs:
        return None
    return load_cadence(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops iam",
        description="P34.42a+b / G1-01: the least-privilege identity "
        "declaration (ops/iam_identities.toml) — plan a leg, diff a "
        "recorded IAM snapshot, gate the same-image check. Offline; "
        "ops/gcp/iam-service-accounts.sh + iam-job-identities.sh own the "
        "(windowed) mutations.",
    )
    sub = parser.add_subparsers(dest="iam_command", required=True)

    plan = sub.add_parser("plan", help="print the declaration + ordered steps (offline)")
    plan.add_argument("--declaration", default=None)
    plan.add_argument("--cadence", default=None, help="defaults to ops/cadence.toml")
    plan.add_argument("--leg", choices=LEGS, default="all")
    plan.add_argument(
        "--project",
        default=os.environ.get("SIG_GCP_PROJECT", "<SIG_GCP_PROJECT>"),
        help="defaults to $SIG_GCP_PROJECT (env-overridable, like every ops surface)",
    )
    plan.add_argument(
        "--region",
        default=os.environ.get("SIG_GCP_REGION", "us-central1"),
        help="defaults to $SIG_GCP_REGION",
    )
    plan.add_argument("--json", action="store_true", help="machine-readable output")

    diff = sub.add_parser(
        "diff", help="judge a recorded IAM snapshot vs the declaration (exit 4 on drift)"
    )
    diff.add_argument("--state-dir", required=True)
    diff.add_argument("--project", required=True)
    diff.add_argument("--compute-sa", default=None)
    diff.add_argument("--declaration", default=None)
    diff.add_argument("--cadence", default=None, help="defaults to ops/cadence.toml")
    diff.add_argument("--leg", choices=LEGS, default="all")

    rev = sub.add_parser(
        "check-revisions",
        help="same-image gate: pre/post service+job describes must carry identical images",
    )
    rev.add_argument("--pre", required=True)
    rev.add_argument("--post", required=True)

    args = parser.parse_args(argv)
    try:
        decl = load_declaration(getattr(args, "declaration", None))
        leg = getattr(args, "leg", "all")
        cadence = _load_cadence_arg(getattr(args, "cadence", None), decl, leg)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.iam_command == "plan":
        try:
            steps = plan_steps(decl, args.project, args.region, cadence, leg)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        if args.json:
            doc = {
                "schema": SCHEMA,
                "leg": leg,
                "service_accounts": [vars(s) for s in decl.service_accounts],
                "project_roles": [vars(r) for r in decl.project_roles],
                "bucket_roles": [vars(r) for r in decl.bucket_roles],
                "services": [vars(s) for s in decl.services],
                "job_classes": [
                    {
                        "name": c.name,
                        "service_account": c.service_account,
                        "sources": c.sources,
                        "batches": c.batches,
                        "probes": c.probes,
                        "jobs": list(c.jobs),
                    }
                    for c in decl.job_classes
                ],
                "job_invokers": [vars(v) for v in decl.job_invokers],
                "remove_roles": [vars(r) for r in decl.remove_roles],
                "expected_job_count": decl.expected_job_count,
                "job_map": resolve_job_map(decl, cadence) if cadence else {},
                "scheduler_triggers": (cadence_scheduler_triggers(cadence) if cadence else {}),
                "invokers": [
                    {
                        "service": v.service,
                        "grant": list(v.grant),
                        "revoke": list(v.revoke),
                        "leg": v.leg,
                    }
                    for v in decl.invokers
                ],
                "secrets": [
                    {
                        "name": s.name,
                        "consumers": list(s.consumers),
                        "jobs_revoke": list(s.jobs_revoke),
                    }
                    for s in decl.secrets
                ],
                "steps": [
                    {
                        "phase": s.phase,
                        "note": s.note,
                        "command": s.command,
                        "rollback": s.rollback,
                    }
                    for s in steps
                ],
            }
            print(json.dumps(doc, indent=2))
            return 0
        lines = [f"schema: {SCHEMA}", f"leg: {leg}", "", "steps (ordered):"]
        for i, s in enumerate(steps, 1):
            lines.append(f"  {i}. [{s.phase}] {s.note}")
            lines.append(f"       {' '.join(s.command)}")
            if s.rollback:
                lines.append(f"       rollback: {' '.join(s.rollback)}")
        _write(None, "\n".join(lines) + "\n")
        return 0

    if args.iam_command == "diff":
        snap = load_snapshot(args.state_dir)
        try:
            diffs = diff_snapshot(decl, snap, args.project, args.compute_sa, cadence, args.leg)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        if diffs:
            for d in diffs:
                print(f"DRIFT: {d}")
            return 4
        print(f"iam diff ({args.leg}): clean — the snapshot carries the declared posture")
        return 0

    if args.iam_command == "check-revisions":
        problems = check_same_image(args.pre, args.post)
        if problems:
            for p in problems:
                print(f"DRIFT: {p}")
            return 4
        print("check-revisions: clean — every workload kept its recorded image")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
