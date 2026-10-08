# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The least-privilege identity declaration (P34.42a / G1-01, F-272, SIG-SEC-007).

``ops/iam_identities.toml`` is the committed record of the three Cloud Run
services' per-workload service accounts, the exact IAM bindings each is
allowed, the service → identity map, the ``sig-alerts`` invoker change
(G1-11), and the 11-secret consumer matrix. This module is the pure engine:

* ``load_declaration`` — parse + validate the TOML (fail-closed: a basic
  role, an undeclared identity, a named member in a revoke list, or a
  missing service binding all refuse to load).
* ``plan_steps`` — the ordered mutation plan the leg applies: create the
  three SAs → project/bucket/secret bindings → one same-image
  ``--service-account`` revision per service → the ``sig-alerts`` invoker
  grant-then-revoke. Every step carries its rollback command.
* ``diff_snapshot`` — the ``--verify`` half: a recorded IAM snapshot (the
  ``prestate``/``poststate`` JSON files ``iam-service-accounts.sh`` captures)
  judged against the declaration. Reports every missing identity or
  binding, every wrong ``serviceAccountName``, a lingering ``allUsers``
  invoker, a declared SA holding an undeclared or basic role, and a
  runtime SA reading a secret it is not a consumer of — the read-only
  "proof without destruction" analysis (deliverable 5; the same shape
  P35.1a's live-diff reuses).
* ``check_same_image`` — the same-image-revision gate: each service's
  container image digest must be byte-identical between the prestate and
  poststate describes (the leg is an identity change, never a code roll).

Offline only: nothing here shells out to gcloud; the shell wrapper
(``ops/gcp/iam-service-accounts.sh``) owns every mutation and stays
window-gated.
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

# Basic roles are the whole point of G1-01 — none may ever be declared or
# observed on a runtime identity (SIG-SEC-007: no Owner/Editor/Viewer).
BASIC_ROLES = frozenset({"roles/owner", "roles/editor", "roles/viewer"})

# Symbolic members the declaration resolves at apply time. `default-compute`
# = <projectNumber>-compute@developer.gserviceaccount.com (the caller identity
# sig-probe runs as until P34.42b); `operator` = the human's account (records
# a consumer that is never a GCP SA binding).
SYMBOLIC_MEMBERS = frozenset({"default-compute", "operator"})

# Members that may appear ONLY in an [[invoker]] revoke list — a public grant
# on an internal receiver is exactly the G1-11 defect.
PUBLIC_MEMBERS = frozenset({"allUsers", "allAuthenticatedUsers"})

SECRET_ACCESSOR_ROLE = "roles/secretmanager.secretAccessor"
RUN_INVOKER_ROLE = "roles/run.invoker"


@dataclass(frozen=True)
class ServiceAccount:
    id: str
    display_name: str
    purpose: str


@dataclass(frozen=True)
class ProjectRole:
    service_account: str
    role: str


@dataclass(frozen=True)
class BucketRole:
    service_account: str
    bucket: str  # the -suffixed derived name: "sig-web" → <project>-sig-web
    role: str


@dataclass(frozen=True)
class Secret:
    name: str
    consumers: tuple[str, ...]


@dataclass(frozen=True)
class ServiceMap:
    name: str
    service_account: str


@dataclass(frozen=True)
class InvokerRule:
    service: str
    grant: tuple[str, ...]
    revoke: tuple[str, ...]


@dataclass(frozen=True)
class Declaration:
    service_accounts: tuple[ServiceAccount, ...]
    project_roles: tuple[ProjectRole, ...]
    bucket_roles: tuple[BucketRole, ...]
    services: tuple[ServiceMap, ...]
    invokers: tuple[InvokerRule, ...]
    secrets: tuple[Secret, ...]

    def sa(self, sa_id: str) -> ServiceAccount:
        for sa in self.service_accounts:
            if sa.id == sa_id:
                return sa
        raise KeyError(sa_id)


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
        sas.append(ServiceAccount(id=sa_id, display_name=display, purpose=purpose))
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
        bucket_roles.append(BucketRole(service_account=sa, bucket=bucket, role=role))

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
    unbound = seen_sa - bound_sa
    if unbound:
        _fail(f"service account(s) {sorted(unbound)} bound to no service — per-workload 1:1")

    invokers: list[InvokerRule] = []
    for i, v in enumerate(raw.get("invoker") or []):
        service = v.get("service")
        if service not in seen_svc:
            _fail(f"invoker {i}: {service!r} is not a declared service")
        grant = tuple(
            _check_member(m, declared=seen_sa, context=f"invoker {i} grant")
            for m in v.get("grant") or []
        )
        revoke_raw = v.get("revoke") or []
        revoke: list[str] = []
        for m in revoke_raw:
            if not isinstance(m, str) or m not in PUBLIC_MEMBERS:
                _fail(f"invoker {i} revoke: {m!r} — only allUsers/allAuthenticatedUsers")
            revoke.append(m)
        if not grant and not revoke:
            _fail(f"invoker {i}: nothing granted or revoked")
        invokers.append(InvokerRule(service=service, grant=grant, revoke=tuple(revoke)))

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
        secrets.append(Secret(name=name, consumers=consumers))

    return Declaration(
        service_accounts=tuple(sas),
        project_roles=tuple(project_roles),
        bucket_roles=tuple(bucket_roles),
        services=tuple(services),
        invokers=tuple(invokers),
        secrets=tuple(secrets),
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


def plan_steps(decl: Declaration, project: str, region: str) -> list[Step]:
    """The ordered leg: identities → bindings → revisions → invoker.

    Pure: the returned commands carry the declared values; the two values the
    contract requires be read live (the caller identity, the recorded prior
    SA) are rendered as ``<...>`` placeholders the shell wrapper fills.
    """
    steps: list[Step] = []

    for sa in decl.service_accounts:
        steps.append(
            Step(
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
        )

    for r in decl.project_roles:
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
        steps.append(
            Step(
                phase="bindings",
                note=f"bucket {project}-{b.bucket}: {b.service_account} → {b.role}",
                command=[
                    "gcloud",
                    "storage",
                    "buckets",
                    "add-iam-policy-binding",
                    f"gs://{project}-{b.bucket}",
                    f"--member=serviceAccount:{sa_email(project, b.service_account)}",
                    f"--role={b.role}",
                ],
                rollback=[
                    "gcloud",
                    "storage",
                    "buckets",
                    "remove-iam-policy-binding",
                    f"gs://{project}-{b.bucket}",
                    f"--member=serviceAccount:{sa_email(project, b.service_account)}",
                    f"--role={b.role}",
                ],
            )
        )
    for s in decl.secrets:
        for consumer in s.consumers:
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

    for v in decl.invokers:
        for member in v.grant:
            steps.append(
                Step(
                    phase="invoker",
                    note=f"{v.service}: grant {RUN_INVOKER_ROLE} to the caller ({member})",
                    command=[
                        "gcloud",
                        "run",
                        "services",
                        "add-iam-policy-binding",
                        v.service,
                        f"--member=<{member} resolved at apply — sig-probe's "
                        "recorded serviceAccountName>",
                        f"--role={RUN_INVOKER_ROLE}",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                    rollback=[
                        "gcloud",
                        "run",
                        "services",
                        "set-iam-policy",
                        v.service,
                        "<recorded invoker policy — prestate get-iam-policy>",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                )
            )
        for member in v.revoke:
            steps.append(
                Step(
                    phase="invoker",
                    note=f"{v.service}: revoke {RUN_INVOKER_ROLE} from {member} (G1-11)",
                    command=[
                        "gcloud",
                        "run",
                        "services",
                        "remove-iam-policy-binding",
                        v.service,
                        f"--member={member}",
                        f"--role={RUN_INVOKER_ROLE}",
                        f"--region={region}",
                        f"--project={project}",
                    ],
                    rollback=None,  # covered by the recorded set-iam-policy above
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
    compute_sa: str | None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_snapshot(state_dir: str | Path) -> Snapshot:
    """Read a capture dir (files named by iam-service-accounts.sh's prestate)."""
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
    for f in sorted(d.glob("*.json")):
        if f.name.startswith("bucket-") and f.name.endswith("-iam.json"):
            buckets[f.name[len("bucket-") : -len("-iam.json")]] = _load_json(f)
        elif f.name.startswith("secret-") and f.name.endswith("-iam.json"):
            secrets[f.name[len("secret-") : -len("-iam.json")]] = _load_json(f)
        elif f.name.startswith("service-") and f.name.endswith("-iam.json"):
            policies[f.name[len("service-") : -len("-iam.json")]] = _load_json(f)
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
        compute_sa=compute,
    )


def _policy_members(policy: dict[str, Any], role: str) -> set[str]:
    out: set[str] = set()
    for b in policy.get("bindings") or []:
        if b.get("role") == role:
            out.update(str(m) for m in b.get("members") or [])
    return out


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


def diff_snapshot(
    decl: Declaration,
    snap: Snapshot,
    project: str,
    compute_sa: str | None = None,
) -> list[str]:
    """Judge a recorded snapshot against the declaration. Empty = the
    declaration holds exactly. Each line names one DRIFT/UNREADABLE finding —
    the read-only audit (deliverable 5): a missing identity or binding, a
    wrong runtime SA, a lingering allUsers invoker, a declared SA holding an
    undeclared/basic role, or a runtime SA reading a foreign secret.
    """
    compute = compute_sa or snap.compute_sa
    diffs: list[str] = []
    declared_emails = {sa.id: sa_email(project, sa.id) for sa in decl.service_accounts}
    declared_set = set(declared_emails.values())

    if snap.service_accounts is not None:
        for sa in decl.service_accounts:
            if declared_emails[sa.id] not in snap.service_accounts:
                diffs.append(f"missing service account {declared_emails[sa.id]}")
    else:
        diffs.append("UNREADABLE: no service-accounts.json in the snapshot")

    if snap.project_policy is None:
        diffs.append("UNREADABLE: no project-iam.json in the snapshot")
    else:
        for r in decl.project_roles:
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

    for br in decl.bucket_roles:
        policy = snap.bucket_policies.get(br.bucket)
        want = f"serviceAccount:{declared_emails[br.service_account]}"
        if policy is None:
            diffs.append(f"UNREADABLE: no bucket-{br.bucket}-iam.json in the snapshot")
            continue
        if want not in _policy_members(policy, br.role):
            diffs.append(f"missing bucket binding {want} → {br.role} on {project}-{br.bucket}")
        # A declared SA must hold ONLY its declared role on a declared bucket —
        # objectAdmin on the web bucket is exactly the 'delete on the evidence
        # stores' defect. Public members keep viewer only (the site's public
        # posture), anything stronger is flagged.
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
            # Only secrets the snapshot recorded are judged — the leg reads all
            # eleven, but a partial snapshot (e.g. a focused fixture) judges
            # what it carries.
            continue
        accessors = _policy_members(policy, SECRET_ACCESSOR_ROLE)
        # "readable only by its consumers": the allowed set is the declared SA
        # consumers resolved, plus the symbolic members honoured where declared
        # (the compute SA while it holds the jobs; the operator's user: account
        # — the member itself is never named in the declaration).
        allowed: set[str] = set()
        for consumer in s.consumers:
            if consumer == "default-compute":
                if compute:
                    allowed.add(f"serviceAccount:{compute}")
            elif consumer == "operator":
                continue  # honoured below via the user: prefix rule
            elif consumer in PUBLIC_MEMBERS:
                continue  # the fail-closed loader already refuses it
            else:
                allowed.add(f"serviceAccount:{declared_emails[consumer]}")
        required = allowed - ({f"serviceAccount:{compute}"} if compute else set())
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

    for svc in decl.services:
        desc = snap.service_describes.get(svc.name)
        want = declared_emails[svc.service_account]
        if desc is None:
            diffs.append(f"UNREADABLE: no service-{svc.name}.json describe in the snapshot")
            continue
        got = _service_account_name(desc)
        if got != want:
            diffs.append(f"service {svc.name} runs as {got!r}, declared {want}")

    for v in decl.invokers:
        policy = snap.service_policies.get(v.service)
        if policy is None:
            diffs.append(f"UNREADABLE: no service-{v.service}-iam.json in the snapshot")
            continue
        public = _all_members(policy) & PUBLIC_MEMBERS
        for m in public:
            if m in v.revoke:
                diffs.append(f"{v.service} still invokable by {m}")
        invoker_members = _policy_members(policy, RUN_INVOKER_ROLE)
        for member in v.grant:
            if member == "operator":
                continue
            if member == "default-compute" and not compute:
                diffs.append(f"UNREADABLE: {v.service} invoker grant needs compute-sa resolution")
                continue
            want = resolve_member(member, project, compute)
            if want not in invoker_members:
                diffs.append(f"missing invoker grant {want} on {v.service}")
    return diffs


def check_same_image(pre_dir: str | Path, post_dir: str | Path) -> list[str]:
    """The same-image-revision gate: every service's container image must be
    byte-identical between the two recorded describes (the leg changes the
    identity only). Returns the violations; empty = same image everywhere.
    """
    problems: list[str] = []
    pre = Path(pre_dir)
    post = Path(post_dir)
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
    if not problems and not describes:
        problems.append("no poststate service describes to compare")
    return problems


# --- CLI (the `sig-ops iam` verb surface) --------------------------------------


def _write(out: str | None, text: str) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops iam",
        description="P34.42a / G1-01: the least-privilege identity "
        "declaration (ops/iam_identities.toml) — plan the leg, diff a "
        "recorded IAM snapshot, gate the same-image revision. Offline; "
        "ops/gcp/iam-service-accounts.sh owns the (windowed) mutations.",
    )
    sub = parser.add_subparsers(dest="iam_command", required=True)

    plan = sub.add_parser("plan", help="print the declaration + ordered steps (offline)")
    plan.add_argument("--declaration", default=None)
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

    rev = sub.add_parser(
        "check-revisions",
        help="same-image gate: pre/post service describes must carry identical digests",
    )
    rev.add_argument("--pre", required=True)
    rev.add_argument("--post", required=True)

    args = parser.parse_args(argv)
    decl = load_declaration(getattr(args, "declaration", None))

    if args.iam_command == "plan":
        steps = plan_steps(decl, args.project, args.region)
        if args.json:
            doc = {
                "schema": SCHEMA,
                "service_accounts": [vars(s) for s in decl.service_accounts],
                "project_roles": [vars(r) for r in decl.project_roles],
                "bucket_roles": [vars(r) for r in decl.bucket_roles],
                "services": [vars(s) for s in decl.services],
                "invokers": [
                    {"service": v.service, "grant": list(v.grant), "revoke": list(v.revoke)}
                    for v in decl.invokers
                ],
                "secrets": [{"name": s.name, "consumers": list(s.consumers)} for s in decl.secrets],
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
        lines = [f"schema: {SCHEMA}", "", "steps (ordered):"]
        for i, s in enumerate(steps, 1):
            lines.append(f"  {i}. [{s.phase}] {s.note}")
            lines.append(f"       {' '.join(s.command)}")
            if s.rollback:
                lines.append(f"       rollback: {' '.join(s.rollback)}")
        _write(None, "\n".join(lines) + "\n")
        return 0

    if args.iam_command == "diff":
        snap = load_snapshot(args.state_dir)
        diffs = diff_snapshot(decl, snap, args.project, args.compute_sa)
        if diffs:
            for d in diffs:
                print(f"DRIFT: {d}")
            return 4
        print("iam diff: clean — the snapshot carries the declared posture")
        return 0

    if args.iam_command == "check-revisions":
        problems = check_same_image(args.pre, args.post)
        if problems:
            for p in problems:
                print(f"DRIFT: {p}")
            return 4
        print("check-revisions: clean — every service kept its recorded image digest")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
