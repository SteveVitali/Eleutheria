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
    before_digest: str
    after_digest: str
    add_capture_store: bool = False
    after_image_verified: str = ""
    applied: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def changes(self) -> bool:
        return self.before_image != self.after_digest or self.add_capture_store


def _container(job: Mapping[str, Any]) -> Mapping[str, Any]:
    return job["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]


def _is_scheduled_ingest(job: Mapping[str, Any]) -> bool:
    return any("scheduled-ingest" in str(a) for a in _container(job).get("args", []) or [])


def _has_capture_store(job: Mapping[str, Any]) -> bool:
    spec = job["spec"]["template"]["spec"]["template"]["spec"]
    volumes = {v.get("name") for v in spec.get("volumes", []) or []}
    env = {e.get("name") for e in _container(job).get("env", []) or []}
    return CAPTURE_VOLUME in volumes and CAPTURE_ENV in env


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
        plan = JobPlan(
            job=name,
            before_image=before,
            before_digest=resolved[before],
            after_digest=image_digest,
            add_capture_store=bool(
                capture_bucket and _is_scheduled_ingest(job) and not _has_capture_store(job)
            ),
        )
        plans.append(plan)
    return plans


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
    if plan.add_capture_store and capture_bucket:
        args += [
            "--execution-environment=gen2",
            f"--add-volume=name={CAPTURE_VOLUME},type=cloud-storage,bucket={capture_bucket}",
            f"--add-volume-mount=volume={CAPTURE_VOLUME},mount-path={CAPTURE_MOUNT}",
            f"--update-env-vars={CAPTURE_ENV}={CAPTURE_MOUNT}/{CAPTURE_PREFIX}",
        ]
    return args


def apply_roll(
    plans: Sequence[JobPlan],
    *,
    project: str,
    region: str,
    gcloud: Gcloud,
    capture_bucket: str | None = None,
) -> list[JobPlan]:
    """Apply every plan that changes something, then verify each job's image."""
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
    return list(plans)


def roll_record(
    plans: Sequence[JobPlan], *, image_ref: str, image_digest: str, applied: bool
) -> dict[str, Any]:
    """The JSON record of a roll: every job's before/after digest (for rollback)."""
    return {
        "image_ref": image_ref,
        "image_digest": image_digest,
        "applied": applied,
        "jobs": [asdict(p) for p in plans],
    }


__all__ = [
    "CAPTURE_ENV",
    "CAPTURE_MOUNT",
    "CAPTURE_PREFIX",
    "CAPTURE_VOLUME",
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
