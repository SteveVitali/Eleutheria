# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `sig-ops deploy` plan builder (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075)."""

from __future__ import annotations

import pytest

from ops import deploy as D


def test_gcp_plan_is_env_parameterised_by_project_and_region() -> None:
    plan = D.build_gcp_plan(project="my-proj", region="us-west1")
    assert plan.target == "gcp"
    assert plan.project == "my-proj"
    assert plan.region == "us-west1"
    joined = "\n".join(plan.steps)
    # image build + push to Artifact Registry, Cloud Run deploy, GCS syncs
    assert "us-west1-docker.pkg.dev/my-proj/sig/sig-api" in joined
    assert "docker push" in joined
    assert "run deploy sig-api" in joined and "--min-instances=0" in joined
    assert "gs://my-proj-sig-web" in joined
    assert "gs://my-proj-sig-public" in joined


def test_gcp_plan_keeps_published_public_and_restricted_private() -> None:
    plan = D.build_gcp_plan(project="p", region="r")
    joined = "\n".join(plan.steps)
    # the published compartment syncs to the public bucket; restricted to a PRIVATE one
    assert "sig-public  (PUBLISHED compartment only, public-read)" in joined
    assert "sig-restricted  (non-published compartments, PRIVATE)" in joined


def test_unset_project_uses_placeholder_never_a_literal() -> None:
    plan = D.build_gcp_plan(project="", region="")
    assert plan.project == "<SIG_GCP_PROJECT-unset>"
    assert plan.region == "us-central1"


def test_plan_for_rejects_unknown_target() -> None:
    with pytest.raises(ValueError):
        D.plan_for("aws")


def test_plan_lines_render_mode_and_steps() -> None:
    plan = D.build_gcp_plan(project="p", region="r")
    lines = plan.as_lines()
    assert any("sig-ops deploy" in ln for ln in lines)
    assert any("plan:" == ln.strip() for ln in lines)
    # steps are numbered
    assert any(ln.strip().startswith("1.") for ln in lines)


def test_adc_detection_is_non_networked(monkeypatch: pytest.MonkeyPatch) -> None:
    # No gcloud on PATH => ADC absent, regardless of any file.
    monkeypatch.setattr(D.shutil, "which", lambda _n: None)
    assert D.adc_present() is False
