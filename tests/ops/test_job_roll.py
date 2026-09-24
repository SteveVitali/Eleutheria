# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.4 / ADR-111: jobs roll onto a pinned digest, recorded before/after, verified."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pytest
from ops.job_roll import (
    CAPTURE_ENV,
    RollError,
    apply_roll,
    plan_roll,
    resolve_digest,
    roll_record,
    update_args,
)

REPO = "us-central1-docker.pkg.dev/proj/sig/sig-api"
OLD = f"{REPO}@sha256:{'a' * 64}"
NEW = f"{REPO}@sha256:{'b' * 64}"


def _job(image: str, *, ingest: bool = True, store: bool = False) -> dict[str, Any]:
    container: dict[str, Any] = {
        "image": image,
        "args": ["-c", "exec sig-ops scheduled-ingest --batch b --sink pg" if ingest else "x"],
        "env": [{"name": "SIG_COMMIT_CHUNK_SIZE", "value": "10000"}],
    }
    spec: dict[str, Any] = {"containers": [container], "timeoutSeconds": "129600"}
    if store:
        spec["volumes"] = [{"name": "captures"}]
        container["env"].append({"name": CAPTURE_ENV, "value": "/mnt/captures/evidence/captures"})
    return {"spec": {"template": {"spec": {"template": {"spec": spec}}}}}


class FakeGcloud:
    """Models Artifact Registry + Cloud Run jobs; records every call."""

    def __init__(self, jobs: dict[str, dict[str, Any]], tags: dict[str, str]) -> None:
        self.jobs = jobs
        self.tags = tags
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        self.calls.append(list(args))
        if args[:3] == ["artifacts", "docker", "images"]:
            return self.tags.get(args[4], "") + "\n"
        if args[:3] == ["run", "jobs", "describe"]:
            return json.dumps(self.jobs[args[3]])
        if args[:3] == ["run", "jobs", "update"]:
            job = self.jobs[args[3]]
            spec = job["spec"]["template"]["spec"]["template"]["spec"]
            for a in args:
                if a.startswith("--image="):
                    spec["containers"][0]["image"] = a.split("=", 1)[1]
                if a.startswith("--add-volume="):
                    spec.setdefault("volumes", []).append({"name": "captures"})
                if a.startswith("--update-env-vars="):
                    name, value = a.split("=", 1)[1].split("=", 1)
                    spec["containers"][0]["env"].append({"name": name, "value": value})
            return ""
        raise AssertionError(args)


def test_latest_and_untagged_refs_are_refused() -> None:
    gcloud = FakeGcloud({}, {})
    for ref in (f"{REPO}:latest", REPO):
        with pytest.raises(RollError):
            resolve_digest(ref, project="proj", gcloud=gcloud)
    assert gcloud.calls == []  # refused before any registry call


def test_a_sha_tag_resolves_to_its_digest() -> None:
    gcloud = FakeGcloud({}, {f"{REPO}:ingest-abc": NEW})
    assert resolve_digest(f"{REPO}:ingest-abc", project="proj", gcloud=gcloud) == NEW
    assert resolve_digest(NEW, project="proj", gcloud=gcloud) == NEW
    with pytest.raises(RollError):
        resolve_digest(f"{REPO}:missing", project="proj", gcloud=gcloud)


def test_roll_records_before_after_adds_the_store_once_and_verifies() -> None:
    jobs = {
        "sig-ingest-camreg-batch-05": _job(f"{REPO}:latest"),
        "sig-ingest-dot-511-ut": _job(OLD, store=True),
        "sig-probe": _job(f"{REPO}:latest", ingest=False),
    }
    gcloud = FakeGcloud(jobs, {f"{REPO}:latest": OLD})
    plans = plan_roll(
        list(jobs), NEW, project="proj", region="r", gcloud=gcloud, capture_bucket="bkt"
    )
    by = {p.job: p for p in plans}
    assert by["sig-ingest-camreg-batch-05"].before_digest == OLD  # :latest, resolved for rollback
    assert by["sig-ingest-camreg-batch-05"].add_capture_store is True
    assert by["sig-ingest-dot-511-ut"].add_capture_store is False  # already configured
    assert by["sig-probe"].add_capture_store is False  # not an ingest job
    apply_roll(plans, project="proj", region="r", gcloud=gcloud, capture_bucket="bkt")
    assert all(p.after_image_verified == NEW for p in plans)
    updates = [c for c in gcloud.calls if c[:3] == ["run", "jobs", "update"]]
    assert len(updates) == 3
    # update never re-sets the timeout/env/secrets: the job keeps its 36 h timeout.
    assert not any(
        a.startswith(("--task-timeout", "--set-env-vars", "--set-secrets"))
        for c in updates
        for a in c
    )
    spec = jobs["sig-ingest-camreg-batch-05"]["spec"]["template"]["spec"]["template"]["spec"]
    assert spec["timeoutSeconds"] == "129600"
    record = roll_record(plans, image_ref="tag", image_digest=NEW, applied=True)
    assert {j["job"]: j["before_digest"] for j in record["jobs"]}["sig-probe"] == OLD


def test_a_roll_is_idempotent() -> None:
    jobs = {"sig-ingest-x": _job(NEW, store=True)}
    gcloud = FakeGcloud(jobs, {})
    plans = plan_roll(list(jobs), NEW, project="p", region="r", gcloud=gcloud, capture_bucket="b")
    assert not plans[0].changes
    apply_roll(plans, project="p", region="r", gcloud=gcloud, capture_bucket="b")
    assert not [c for c in gcloud.calls if c[:3] == ["run", "jobs", "update"]]


def test_a_failed_verify_raises() -> None:
    jobs = {"sig-ingest-x": _job(OLD)}

    class Stuck(FakeGcloud):
        def __call__(self, args: Sequence[str]) -> str:
            if args[:3] == ["run", "jobs", "update"]:
                self.calls.append(list(args))
                return ""  # the update silently did nothing
            return super().__call__(args)

    gcloud = Stuck(jobs, {})
    plans = plan_roll(list(jobs), NEW, project="p", region="r", gcloud=gcloud)
    with pytest.raises(RollError, match="configured image"):
        apply_roll(plans, project="p", region="r", gcloud=gcloud)


def test_update_args_carry_the_capture_store() -> None:
    jobs = {"sig-ingest-x": _job(OLD)}
    plans = plan_roll(
        list(jobs), NEW, project="p", region="r", gcloud=FakeGcloud(jobs, {}), capture_bucket="b"
    )
    args = update_args(plans[0], project="p", region="r", capture_bucket="b")
    assert f"--image={NEW}" in args
    assert "--add-volume=name=captures,type=cloud-storage,bucket=b" in args
    assert f"--update-env-vars={CAPTURE_ENV}=/mnt/captures/evidence/captures" in args
