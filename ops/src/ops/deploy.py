# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `sig-ops deploy --target gcp` path (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075).

`deploy` builds + pushes the API image (Artifact Registry) and syncs the static
site (`web/dist`) + the export bytes to GCS. In this isolated context there are no
Application Default Credentials (ADC), so the command runs in **dry-run / plan
mode**: it prints the ordered plan and exits 0 without opening the network. The
real push/sync is **gate-pending** on operator ADC (HG-12 / D-ACCT.1-1) and is
never performed by an isolated subagent.

The plan is a pure function of the environment-parameterised config (the project
comes from ``$SIG_GCP_PROJECT``; no secret and no literal project id live here,
RISK-P21-05 / go-live spec D3), so it is fully testable without credentials.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field


def _project() -> str:
    """The GCP project id from the env, or a placeholder for plan display."""
    return os.environ.get("SIG_GCP_PROJECT", "").strip() or "<SIG_GCP_PROJECT-unset>"


def _region() -> str:
    return os.environ.get("SIG_GCP_REGION", "us-central1").strip() or "us-central1"


@dataclass(frozen=True)
class DeployPlan:
    """An ordered, printable deploy plan for a target (no side effects)."""

    target: str
    project: str
    region: str
    steps: list[str] = field(default_factory=list)
    dry_run: bool = True
    adc_present: bool = False

    def as_lines(self) -> list[str]:
        lines = [
            f"sig-ops deploy — target={self.target} project={self.project} region={self.region}",
            f"mode={'dry-run (plan only)' if self.dry_run else 'apply'} "
            f"adc={'present' if self.adc_present else 'absent'}",
            "plan:",
        ]
        lines += [f"  {i + 1}. {s}" for i, s in enumerate(self.steps)]
        return lines


def _gcp_image(project: str, region: str) -> str:
    return f"{region}-docker.pkg.dev/{project}/sig/sig-api"


def _export_dir_display() -> str:
    """The national export dir the public build reads (env override → national default)."""
    return os.environ.get("SIG_EXPORT_DIR", "").strip() or "exports/out/national"


def build_gcp_plan(*, project: str | None = None, region: str | None = None) -> DeployPlan:
    """Build the ordered GCP deploy plan (image build+push, public build, GCS syncs).

    The public build + compartment partition (steps 5–6) run BEFORE the syncs so the real
    national export drives ``web/dist`` (fail-loud, never fixtures) and the public sync can
    only ever carry licence-separated, publishable compartments (§42; ADR-106;
    ``ops/src/ops/publish.py``).
    """
    proj = project or _project()
    reg = region or _region()
    image = _gcp_image(proj, reg)
    export_dir = _export_dir_display()
    steps = [
        f"gcloud auth configure-docker {reg}-docker.pkg.dev  (auth the AR host)",
        f"docker build -t {image}:api-<git-sha> -f ops/Dockerfile .  (build the API image; a "
        "SHA tag — `:latest` is never built, pushed or moved, ADR-111)",
        f"docker push {image}:api-<git-sha>  (push to Artifact Registry)",
        f"gcloud run deploy sig-api --image {image}@sha256:<digest of api-<git-sha>> "
        f"--region {reg} "
        "--min-instances=0  (scale-to-zero API; managed TLS; deployed BY PINNED DIGEST, resolved "
        "with `gcloud artifacts docker images describe` — ADR-107 §5, ADR-111)",
        f"sig-ops publish: build web/dist with SIG_DATA_SOURCE=export SIG_EXPORT_DIR={export_dir}  "
        "(the P27.4 national export — FAILS LOUD if absent, never a fixtures fall-back)",
        f"sig-ops publish: partition {export_dir} → exports/out/public (licence-separated "
        "compartments incl. the ODbL/CC-BY-SA layers, each single-licence — ADR-106) + "
        "exports/out/restricted (UNDETERMINED/excluded/mixed-licence, PRIVATE); assert public "
        "compartment clean; write LICENCES.json (SPDX licence + attribution per compartment)",
        f"gcloud storage rsync -r -c --delete-unmatched-destination-objects web/dist "
        f"gs://{proj}-sig-web  (static site, public-read; mirrors the build exactly — the "
        "prior demo pages and the non-public /curate/ shell are removed)",
        f"gcloud storage rsync -r -c exports/out/public "
        f"gs://{proj}-sig-public  (PUBLISHED compartment only, public-read)",
        f"gcloud storage rsync -r -c exports/out/restricted "
        f"gs://{proj}-sig-restricted  (non-published compartments, PRIVATE)",
    ]
    return DeployPlan(
        target="gcp",
        project=proj,
        region=reg,
        steps=steps,
        adc_present=adc_present(),
    )


def adc_present() -> bool:
    """True iff gcloud Application Default Credentials appear usable.

    Detection is best-effort and NON-NETWORKED: we only check that gcloud is on
    PATH and an ADC file exists; we never open a socket. Absent ADC forces
    dry-run (the isolated-context default), so this never fabricates a deploy.
    """
    if shutil.which("gcloud") is None:
        return False
    candidates = [
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip(),
        os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
    ]
    return any(p and os.path.isfile(p) for p in candidates)


def plan_for(target: str) -> DeployPlan:
    """Return the deploy plan for ``target`` (only ``gcp`` is supported today)."""
    if target != "gcp":
        raise ValueError(f"unsupported deploy target {target!r}; only 'gcp' is supported")
    return build_gcp_plan()


__all__ = ["DeployPlan", "adc_present", "build_gcp_plan", "plan_for"]
