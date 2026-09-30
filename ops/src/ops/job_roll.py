# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Roll Cloud Run jobs onto an image **by pinned digest**, never ``:latest`` (P31.4 / ADR-111).

Until P31.4 every scheduled ingest job ran ``sig-api:latest``: a job picked up
whatever image the tag pointed at when the job was last deployed, and redeploying
from ``ops/gcp/scheduled-ops.sh`` silently re-resolved the tag. Rolling new code onto
the jobs is now one explicit, recorded act:

1. **Resolve** the image reference to a digest
   (``…/sig-api@sha256:<64 hex>``). A ``:latest`` or untagged reference is
   refused; a tag is resolved through Artifact Registry and the digest is what gets
   deployed.
2. **Plan** per job: the image it runs now (the rollback reference, resolved to its
   digest too) and the digest it will run. For a ``scheduled-ingest`` job the plan
   also mounts the GCS-backed capture store (the restricted bucket, gcsfuse) and
   points ``SIG_CAPTURE_DIR`` into it, so captures survive the execution and a
   restarted run can re-process them. A job already configured that way is not
   touched twice.
3. **Apply** with ``gcloud run jobs update`` (image, and the capture store where
   planned). ``update`` changes only what it is given: every other setting a job
   carries (its task timeout, its env such as ``SIG_COMMIT_CHUNK_SIZE``, its
   secrets) is preserved. That matters: the live batch jobs run a 36 h timeout that
   ``scheduled-ops.sh`` would reset.
4. **Verify** by describing each job again: its configured image must equal the
   planned digest.

The plan and the result are one JSON record (``--record``), so every roll keeps its
before/after digests for rollback. Rollback is the same command with the recorded
``before`` digest. ``gcloud`` is injected, so the planner is deterministic in tests.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

#: A deployable image reference: an Artifact Registry path pinned by sha256 digest.
DIGEST_REF = re.compile(r"^[a-z0-9.-]+/[^@\s]+@sha256:[0-9a-f]{64}$")

#: The capture-store volume every scheduled ingest job mounts (P31.4).
CAPTURE_VOLUME = "captures"
CAPTURE_MOUNT = "/mnt/captures"
#: Where the OCFL capture root lives inside the restricted bucket.
CAPTURE_PREFIX = "evidence/captures"
CAPTURE_ENV = "SIG_CAPTURE_DIR"
#: The code identity every rolled job carries (the image digest). A scheduled ingest
#: records it as its run's ``code_commit``, and a restart only resumes the marks of
#: executions that ran the same code (ADR-111).
CODE_COMMIT_ENV = "SIG_CODE_COMMIT"

#: ``gcloud`` runner: args -> stdout (raises on a non-zero exit).
Gcloud = Callable[[Sequence[str]], str]


class RollError(RuntimeError):
    """A roll that must not proceed (an unpinnable image, a failed verify)."""


def gcloud_cli(args: Sequence[str]) -> str:
    """Run ``gcloud`` for real and return its stdout (the production runner)."""
    proc = subprocess.run(["gcloud", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RollError(f"gcloud {' '.join(args[:3])} … failed: {proc.stderr.strip()[:500]}")
    return proc.stdout


def resolve_digest(ref: str, *, project: str, gcloud: Gcloud) -> str:
    """Resolve an image reference to ``<repo>@sha256:<digest>`` (never ``:latest``)."""
    ref = ref.strip()
    if DIGEST_REF.match(ref):
        return ref
    name = ref.rsplit("/", 1)[-1]
    if ":" not in name:
        raise RollError(f"{ref!r} has no tag or digest; pass a SHA tag or a digest")
    if name.endswith(":latest"):
        raise RollError(f"{ref!r} is :latest; jobs are rolled by pinned digest only (ADR-111)")
    out = gcloud(
        [
            "artifacts",
            "docker",
            "images",
            "describe",
            ref,
            f"--project={project}",
            "--format=value(image_summary.fully_qualified_digest)",
        ]
    ).strip()
    if not DIGEST_REF.match(out):
        raise RollError(f"could not resolve {ref!r} to a digest (got {out!r})")
    return out


@dataclass
class JobPlan:
    """What one job runs now, and what it will run after the roll."""

    job: str
    before_image: str
    #: The digest ``before_image`` resolved to AT ROLL TIME (for a movable tag such as
    #: ``:latest`` that is the tag's digest then, the best available rollback target).
    before_digest: str
    after_digest: str
    add_capture_volume: bool = False
    add_capture_env: bool = False
    set_code_commit: bool = False
    after_image_verified: str = ""
    applied: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def add_capture_store(self) -> bool:
        return self.add_capture_volume or self.add_capture_env

    @property
    def changes(self) -> bool:
        return (
            self.before_image != self.after_digest or self.add_capture_store or self.set_code_commit
        )

    @property
    def rollback_resolved(self) -> bool:
        return bool(DIGEST_REF.match(self.before_digest))


def _container(job: Mapping[str, Any]) -> Mapping[str, Any]:
    return job["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]


def _is_scheduled_ingest(job: Mapping[str, Any]) -> bool:
    return any("scheduled-ingest" in str(a) for a in _container(job).get("args", []) or [])


def _has_capture_volume(job: Mapping[str, Any]) -> bool:
    spec = job["spec"]["template"]["spec"]["template"]["spec"]
    return CAPTURE_VOLUME in {v.get("name") for v in spec.get("volumes", []) or []}


def _env(job: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(e.get("name")): str(e.get("value", "")) for e in _container(job).get("env", []) or []
    }


def _has_capture_store(job: Mapping[str, Any]) -> bool:
    return _has_capture_volume(job) and CAPTURE_ENV in _env(job)


def describe_job(job: str, *, project: str, region: str, gcloud: Gcloud) -> dict[str, Any]:
    out = gcloud(
        [
            "run",
            "jobs",
            "describe",
            job,
            f"--project={project}",
            f"--region={region}",
            "--format=json",
        ]
    )
    return dict(json.loads(out))


def plan_roll(
    jobs: Iterable[str],
    image_digest: str,
    *,
    project: str,
    region: str,
    gcloud: Gcloud,
    capture_bucket: str | None = None,
) -> list[JobPlan]:
    """Describe each job and plan its roll onto ``image_digest`` (read-only)."""
    if not DIGEST_REF.match(image_digest):
        raise RollError(f"{image_digest!r} is not a pinned digest reference")
    plans: list[JobPlan] = []
    resolved: dict[str, str] = {}
    for name in jobs:
        job = describe_job(name, project=project, region=region, gcloud=gcloud)
        before = str(_container(job)["image"])
        if before not in resolved:
            resolved[before] = (
                before if DIGEST_REF.match(before) else _resolve_any(before, project, gcloud)
            )
        store = bool(capture_bucket and _is_scheduled_ingest(job))
        plan = JobPlan(
            job=name,
            before_image=before,
            before_digest=resolved[before],
            after_digest=image_digest,
            add_capture_volume=store and not _has_capture_volume(job),
            add_capture_env=store and CAPTURE_ENV not in _env(job),
            set_code_commit=_env(job).get(CODE_COMMIT_ENV) != _digest_of(image_digest),
        )
        plans.append(plan)
    return plans


def _digest_of(ref: str) -> str:
    """``sha256:<hex>`` of a pinned reference — the code identity a job records."""
    return ref.rsplit("@", 1)[-1]


def _resolve_any(ref: str, project: str, gcloud: Gcloud) -> str:
    """Resolve the CURRENT image (possibly ``:latest``) to a digest, for rollback."""
    out = gcloud(
        [
            "artifacts",
            "docker",
            "images",
            "describe",
            ref,
            f"--project={project}",
            "--format=value(image_summary.fully_qualified_digest)",
        ]
    ).strip()
    return out if DIGEST_REF.match(out) else f"<unresolved:{ref}>"


def update_args(
    plan: JobPlan, *, project: str, region: str, capture_bucket: str | None
) -> list[str]:
    """The ``gcloud run jobs update`` arguments for one plan (image + capture store)."""
    args = [
        "run",
        "jobs",
        "update",
        plan.job,
        f"--project={project}",
        f"--region={region}",
        f"--image={plan.after_digest}",
    ]
    env: list[str] = []
    if plan.add_capture_volume and capture_bucket:
        args += [
            "--execution-environment=gen2",
            f"--add-volume=name={CAPTURE_VOLUME},type=cloud-storage,bucket={capture_bucket}",
            f"--add-volume-mount=volume={CAPTURE_VOLUME},mount-path={CAPTURE_MOUNT}",
        ]
    if plan.add_capture_env and capture_bucket:
        env.append(f"{CAPTURE_ENV}={CAPTURE_MOUNT}/{CAPTURE_PREFIX}")
    if plan.set_code_commit:
        env.append(f"{CODE_COMMIT_ENV}={_digest_of(plan.after_digest)}")
    if env:
        args.append("--update-env-vars=" + ",".join(env))
    return args


def apply_roll(
    plans: Sequence[JobPlan],
    *,
    project: str,
    region: str,
    gcloud: Gcloud,
    capture_bucket: str | None = None,
    allow_unresolved_rollback: bool = False,
) -> list[JobPlan]:
    """Apply every plan that changes something, then verify each job's image.

    Refuses (before touching any job) when a job's current image could not be
    resolved to a digest, since the roll would then have no rollback target, unless
    ``allow_unresolved_rollback`` is set.
    """
    unresolved = [p.job for p in plans if not p.rollback_resolved]
    if unresolved and not allow_unresolved_rollback:
        raise RollError(f"no rollback digest for {unresolved}; pass the explicit override")
    for plan in plans:
        if plan.changes:
            gcloud(update_args(plan, project=project, region=region, capture_bucket=capture_bucket))
            plan.applied = True
        job = describe_job(plan.job, project=project, region=region, gcloud=gcloud)
        plan.after_image_verified = str(_container(job)["image"])
        if plan.after_image_verified != plan.after_digest:
            raise RollError(
                f"{plan.job}: configured image {plan.after_image_verified!r} != "
                f"planned {plan.after_digest!r}"
            )
        if plan.add_capture_store and not _has_capture_store(job):
            raise RollError(f"{plan.job}: the capture store is not configured after the update")
        if _env(job).get(CODE_COMMIT_ENV) != _digest_of(plan.after_digest):
            raise RollError(f"{plan.job}: {CODE_COMMIT_ENV} is not the rolled digest")
    return list(plans)


def roll_record(
    plans: Sequence[JobPlan], *, image_ref: str, image_digest: str, applied: bool
) -> dict[str, Any]:
    """The JSON record of a roll: every job's before/after digest (for rollback).

    ``applied`` is what the caller asked for; each job's own ``applied`` says whether
    its update actually ran (a roll that failed part-way still records every job).
    """
    return {
        "image_ref": image_ref,
        "image_digest": image_digest,
        "applied": applied,
        "jobs": [{**asdict(p), "add_capture_store": p.add_capture_store} for p in plans],
    }


__all__ = [
    "CAPTURE_ENV",
    "CAPTURE_MOUNT",
    "CAPTURE_PREFIX",
    "CAPTURE_VOLUME",
    "CODE_COMMIT_ENV",
    "DIGEST_REF",
    "JobPlan",
    "RollError",
    "apply_roll",
    "gcloud_cli",
    "plan_roll",
    "resolve_digest",
    "roll_record",
    "update_args",
]
