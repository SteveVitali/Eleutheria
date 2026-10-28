# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The scheduled restricted-corpus probe job — declaration, render, verify.

P35.23 (SIG-CONF-008/012/013). ``ops/rdc_probe.toml`` is the committed
``sig.rdc-probe/1`` declaration of the permanent ``sig-rdc-probe`` Cloud Run
job — the restricted half of the real-data regression corpus — and its
``sig-sched-rdc-probe`` Cloud Scheduler trigger. This module is the engine
``ops/gcp/rdc-slices.sh`` drives, sibling to ``quality_job.py`` (whose
window predicates, name regexes, and scheduler/trigger argv helpers it
reuses verbatim — same contract windows, same suppression semantics).

Per run the in-container command (``sig-ops rdc scheduled``):

1. re-checks the OM-19 windows — a fire inside 03:00–06:30Z or the monthly
   batch window records a ``skipped`` ``sig.probe-run/1`` instead of
   running (defence in depth for a drifted or manually invoked trigger);
2. fetches the restricted member bytes from the OCFL capture store under
   the conditioned ``evidence/captures/`` objectViewer scope — the path is
   deterministic (extension 0003), so the read is one bounded object fetch
   per member, never a bucket listing;
3. sha256-verifies every fetched member against the committed digest —
   content-addressed, never trusted;
4. runs the full corpus harness (oracle + pipeline + M-4/M-5/M-6) on an
   overlay corpus — the committed tree is never mutated;
5. writes ``sig.rdc-report/1`` + ``sig.probe-run/1`` as NEW timestamped
   objects under the conditioned ``ops/probes/`` objectCreator scope.

The job needs no database and no secrets: the corpus manifest and the
committed member bytes ride the workload image (``tests/rdc/`` is COPYed
into ``/app`` — the image digest pins the corpus version), and the bucket
API auth is the runtime service account's metadata-server token.

No function here opens a socket, shells out, or reads the environment.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, NoReturn

from .quality_job import (
    ENV_NAME_RE,
    JOB_NAME_RE,
    PREFIX_RE,
    RUN_INVOKER_ROLE,
    SA_ID_RE,
    TASK_TIMEOUT_RE,
    Scheduler,
    check_image_ref,
    sa_email,
    validate_schedule,
)

SCHEMA: Final = "sig.rdc-probe/1"
DEFAULT_DECLARATION_PATH: Final = Path(__file__).resolve().parents[2] / "rdc_probe.toml"

COMMAND_RE: Final = re.compile(r"^[a-zA-Z0-9_./-]+$")


def _fail(msg: str) -> NoReturn:
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# The parsed declaration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RdcProbe:
    """One parsed ``sig.rdc-probe/1`` declaration."""

    job: str
    service_account: str
    image_repo: str
    command: str
    container_args: tuple[str, ...]
    tasks: int
    max_retries: int
    task_timeout: str
    cpu: str
    memory: str
    corpus_root: str
    capture_prefix: str
    probe_prefix: str
    scheduler: Scheduler
    plain_env: tuple[str, ...]


def load_declaration(path: str | Path | None = None) -> RdcProbe:
    """Load + validate the declaration — fail closed on any drift."""
    p = Path(path) if path else DEFAULT_DECLARATION_PATH
    try:
        doc = tomllib.loads(p.read_bytes().decode("utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        _fail(f"rdc-probe declaration unreadable: {e}")
    if str(doc.get("schema")) != SCHEMA:
        _fail(f"{p}: schema must be {SCHEMA!r}")

    def _str(key: str, where: str = "") -> str:
        v = doc.get(key)
        if not isinstance(v, str) or not v.strip():
            _fail(f"{p}: {where + '.' if where else ''}{key} must be a non-empty string")
        return str(v)

    job = _str("job")
    if not JOB_NAME_RE.match(job):
        _fail(f"{p}: job {job!r} must match {JOB_NAME_RE.pattern}")
    sa = _str("service_account")
    if not SA_ID_RE.match(sa):
        _fail(f"{p}: service_account {sa!r} is not a valid SA id")
    command = _str("command")
    if not COMMAND_RE.match(command):
        _fail(f"{p}: command {command!r} must be a simple command name/path (e.g. sh)")
    raw_args = doc.get("container_args")
    if not isinstance(raw_args, list) or not raw_args:
        _fail(f"{p}: container_args must be a non-empty list")
    container_args: list[str] = []
    for i, a in enumerate(raw_args):
        if not isinstance(a, str) or not a.strip():
            _fail(f"{p}: container_args[{i}] must be a non-empty string")
        if "," in a or "\n" in a:
            _fail(f"{p}: container_args[{i}] {a!r} carries a comma/newline — refused")
        container_args.append(str(a))
    if int(doc.get("tasks", 0) or 0) != 1:
        _fail(f"{p}: tasks must be exactly 1 — a single probe run, never a fleet")
    if "max_retries" not in doc or int(doc["max_retries"]) != 0:
        _fail(
            f"{p}: max_retries must be 0 — a failed run is recorded, "
            "never retried inside a suppression window"
        )
    timeout = _str("task_timeout")
    m = TASK_TIMEOUT_RE.match(timeout)
    if not m or not (60 <= int(m.group(1)) <= 86400):
        _fail(f"{p}: task_timeout {timeout!r} must be a bounded seconds value (60–86400s)")
    capture_prefix = _str("capture_prefix")
    if not PREFIX_RE.match(capture_prefix) or capture_prefix != "evidence/captures/":
        _fail(
            f"{p}: capture_prefix {capture_prefix!r} must be 'evidence/captures/' — "
            "the conditioned objectViewer scope is the only read the identity holds"
        )
    probe_prefix = _str("probe_prefix")
    if not PREFIX_RE.match(probe_prefix) or not probe_prefix.startswith("ops/probes/"):
        _fail(
            f"{p}: probe_prefix {probe_prefix!r} must be a bucket-relative prefix "
            "under ops/probes/ — the conditioned objectCreator scope"
        )
    corpus_root = _str("corpus_root")
    if not corpus_root.startswith("/app/"):
        _fail(
            f"{p}: corpus_root {corpus_root!r} must sit under /app — the corpus "
            "rides the workload image (its digest pins the corpus version)"
        )

    sraw = doc.get("scheduler")
    if not isinstance(sraw, dict):
        _fail(f"{p}: [scheduler] is required")
    scheduler = Scheduler(
        name=str(sraw.get("name") or _fail(f"{p}: scheduler.name required")),
        schedule=str(sraw.get("schedule") or _fail(f"{p}: scheduler.schedule required")),
        time_zone=str(sraw.get("time_zone") or _fail(f"{p}: scheduler.time_zone required")),
        invoker=str(sraw.get("invoker") or _fail(f"{p}: scheduler.invoker required")),
    )
    if not JOB_NAME_RE.match(scheduler.name):
        _fail(f"{p}: scheduler.name {scheduler.name!r} must match {JOB_NAME_RE.pattern}")
    if scheduler.time_zone != "Etc/UTC":
        _fail(
            f"{p}: scheduler.time_zone {scheduler.time_zone!r} must be Etc/UTC — "
            "the window contract is written in UTC"
        )
    if not SA_ID_RE.match(scheduler.invoker):
        _fail(f"{p}: scheduler.invoker {scheduler.invoker!r} is not a valid SA id")
    for sched_err in validate_schedule(scheduler.schedule):
        _fail(f"{p}: {sched_err}")

    if doc.get("secret_env"):
        _fail(
            f"{p}: the rdc probe declares NO secret_env — it needs no database "
            "and no credentials beyond the runtime identity's conditioned grants"
        )
    plain_env_raw = doc.get("plain_env") or []
    if not isinstance(plain_env_raw, list):
        _fail(f"{p}: plain_env must be a list of env names")
    plain_env: list[str] = []
    for name in plain_env_raw:
        if not isinstance(name, str) or not ENV_NAME_RE.match(name):
            _fail(f"{p}: plain_env name {name!r} is not an env name")
        plain_env.append(str(name))

    return RdcProbe(
        job=job,
        service_account=sa,
        image_repo=_str("image_repo"),
        command=command,
        container_args=tuple(container_args),
        tasks=1,
        max_retries=0,
        task_timeout=timeout,
        cpu=_str("cpu"),
        memory=_str("memory"),
        corpus_root=corpus_root,
        capture_prefix=capture_prefix,
        probe_prefix=probe_prefix,
        scheduler=scheduler,
        plain_env=tuple(plain_env),
    )


# ---------------------------------------------------------------------------
# The rendered mutation set
# ---------------------------------------------------------------------------


def deploy_argv(
    decl: RdcProbe,
    *,
    project: str,
    region: str,
    image: str,
    env_values: dict[str, str],
) -> list[str]:
    """The idempotent `gcloud run jobs deploy` argv — every declared plain
    env name must resolve to a value (no silent empty vars)."""
    check_image_ref(image)
    argv = [
        "gcloud",
        "run",
        "jobs",
        "deploy",
        decl.job,
        f"--image={image}",
        f"--region={region}",
        f"--project={project}",
        f"--service-account={sa_email(project, decl.service_account)}",
        f"--command={decl.command}",
        "--args=" + ",".join(decl.container_args),
        f"--tasks={decl.tasks}",
        f"--task-timeout={decl.task_timeout}",
        f"--max-retries={decl.max_retries}",
        f"--cpu={decl.cpu}",
        f"--memory={decl.memory}",
    ]
    env_pairs: list[str] = []
    for name in decl.plain_env:
        value = env_values.get(name)
        if value is None:
            _fail(f"plain env {name} has no rendered value — the leg supplies it")
        if "," in value or "\n" in value:
            _fail(f"plain env {name}: value carries a comma/newline — refused")
        env_pairs.append(f"{name}={value}")
    argv.append("--set-env-vars=" + ",".join(env_pairs))
    return argv


def invoker_argv(decl: RdcProbe, *, project: str, region: str) -> list[str]:
    """`run.invoker` on THIS job for the scheduler's OIDC identity only."""
    return [
        "gcloud",
        "run",
        "jobs",
        "add-iam-policy-binding",
        decl.job,
        f"--member=serviceAccount:{sa_email(project, decl.scheduler.invoker)}",
        f"--role={RUN_INVOKER_ROLE}",
        f"--region={region}",
        f"--project={project}",
    ]


def trigger_uri(decl: RdcProbe, *, project: str, region: str) -> str:
    """The Run API `:run` endpoint the scheduler POSTs (the jobs pattern)."""
    return (
        f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
        f"namespaces/{project}/jobs/{decl.job}:run"
    )


def trigger_argv(decl: RdcProbe, *, project: str, region: str, update: bool = False) -> list[str]:
    """The scheduler create-or-update argv (``update`` swaps the verb — the
    leg picks after a describe)."""
    return [
        "gcloud",
        "scheduler",
        "jobs",
        "update" if update else "create",
        "http",
        decl.scheduler.name,
        f"--schedule={decl.scheduler.schedule}",
        f"--time-zone={decl.scheduler.time_zone}",
        f"--uri={trigger_uri(decl, project=project, region=region)}",
        "--http-method=POST",
        f"--oauth-service-account-email={sa_email(project, decl.scheduler.invoker)}",
        f"--location={region}",
        f"--project={project}",
    ]


def rollback_argv(decl: RdcProbe, *, project: str, region: str) -> dict[str, list[str]]:
    """The name-checked unwind — pause the trigger, delete the trigger,
    delete the job, remove the scheduler's invoker binding (probe records
    stay: they are history)."""
    return {
        "pause_trigger": [
            "gcloud",
            "scheduler",
            "jobs",
            "pause",
            decl.scheduler.name,
            f"--location={region}",
            f"--project={project}",
        ],
        "delete_trigger": [
            "gcloud",
            "scheduler",
            "jobs",
            "delete",
            decl.scheduler.name,
            f"--location={region}",
            f"--project={project}",
            "--quiet",
        ],
        "remove_job_invoker": [
            "gcloud",
            "run",
            "jobs",
            "remove-iam-policy-binding",
            decl.job,
            f"--member=serviceAccount:{sa_email(project, decl.scheduler.invoker)}",
            f"--role={RUN_INVOKER_ROLE}",
            f"--region={region}",
            f"--project={project}",
        ],
        "delete_job": [
            "gcloud",
            "run",
            "jobs",
            "delete",
            decl.job,
            f"--region={region}",
            f"--project={project}",
            "--quiet",
        ],
    }


def render(
    decl: RdcProbe,
    *,
    project: str,
    region: str,
    image: str,
    env_values: dict[str, str],
) -> dict[str, Any]:
    """The whole declared mutation set as ordered argv — what the leg runs."""
    return {
        "schema": SCHEMA,
        "job": decl.job,
        "service_account": sa_email(project, decl.service_account),
        "image": image,
        "deploy": deploy_argv(
            decl, project=project, region=region, image=image, env_values=env_values
        ),
        "job_invoker": invoker_argv(decl, project=project, region=region),
        "trigger_uri": trigger_uri(decl, project=project, region=region),
        "trigger_create": trigger_argv(decl, project=project, region=region),
        "trigger_update": trigger_argv(decl, project=project, region=region, update=True),
        "rollback": rollback_argv(decl, project=project, region=region),
    }


# ---------------------------------------------------------------------------
# The live-diff half — recorded describes judged against the declaration
# ---------------------------------------------------------------------------


def _task_spec(describe: dict[str, Any]) -> dict[str, Any]:
    """``spec.template.spec.template.spec`` — the TaskTemplate of a job describe."""
    return (
        describe.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("template", {})
        .get("spec", {})
        or {}
    )


def verify_describe(decl: RdcProbe, describe: dict[str, Any], *, project: str) -> list[str]:
    """Judge one recorded `gcloud run jobs describe --format=json` against
    the declaration. Returns drift lines; empty = the posture holds."""
    diffs: list[str] = []
    meta_name = describe.get("metadata", {}).get("name")
    if meta_name is not None and str(meta_name).rsplit("/", 1)[-1] != decl.job:
        diffs.append(f"job name {meta_name!r} != declared {decl.job!r}")
    spec = _task_spec(describe)
    if not spec:
        return ["UNREADABLE: no spec.template.spec.template.spec in the describe"]
    want_sa = sa_email(project, decl.service_account)
    if spec.get("serviceAccountName") != want_sa:
        diffs.append(f"serviceAccountName {spec.get('serviceAccountName')!r} != {want_sa}")
    exec_tmpl = describe.get("spec", {}).get("template", {}).get("spec", {}) or {}
    if exec_tmpl.get("maxRetries") != decl.max_retries:
        diffs.append(f"maxRetries {exec_tmpl.get('maxRetries')!r} != 0")
    if exec_tmpl.get("taskTimeout") != decl.task_timeout:
        diffs.append(f"taskTimeout {exec_tmpl.get('taskTimeout')!r} != {decl.task_timeout}")
    containers = spec.get("containers") or []
    if len(containers) != 1:
        diffs.append(f"containers {len(containers)} != 1")
        containers = [{}]
    container = containers[0]
    image = str(container.get("image") or "")
    if "@sha256:" not in image:
        diffs.append(f"image {image!r} is not digest-pinned (ADR-111)")
    # The declaration carries no secret env — a mounted secret is drift.
    for e in container.get("env") or []:
        if (e.get("valueFrom") or {}).get("secretKeyRef"):
            diffs.append(f"secret env {e.get('name')!r} mounted — the job holds none")
    for e in container.get("envFrom") or []:
        diffs.append(f"envFrom {e!r} — the declaration admits named env vars only")
    # The job reads the capture store through the JSON API — no Cloud SQL
    # connector is declared; one appearing is drift.
    if spec.get("cloudSqlInstances"):
        diffs.append("a Cloud SQL connector is attached — the job declares none")
    return diffs


def verify_trigger(
    decl: RdcProbe, describe: dict[str, Any], *, project: str, region: str
) -> list[str]:
    """Judge a `gcloud scheduler jobs describe --format=json` against the
    declaration's trigger shape."""
    diffs: list[str] = []
    name = describe.get("name", "")
    if name and str(name).rsplit("/", 1)[-1] != decl.scheduler.name:
        diffs.append(f"trigger name {name!r} != declared {decl.scheduler.name!r}")
    if describe.get("schedule") != decl.scheduler.schedule:
        diffs.append(
            f"schedule {describe.get('schedule')!r} != declared {decl.scheduler.schedule!r}"
        )
    tz = describe.get("timeZone") or describe.get("time_zone")
    if tz != decl.scheduler.time_zone:
        diffs.append(f"timeZone {tz!r} != declared {decl.scheduler.time_zone!r}")
    http = describe.get("httpTarget") or {}
    want_uri = trigger_uri(decl, project=project, region=region)
    if http.get("uri") != want_uri:
        diffs.append(f"httpTarget.uri {http.get('uri')!r} != {want_uri}")
    if str(http.get("httpMethod", "")).upper() != "POST":
        diffs.append(f"httpTarget.httpMethod {http.get('httpMethod')!r} != POST")
    want_sa = sa_email(project, decl.scheduler.invoker)
    oauth = http.get("oauthToken") or {}
    if oauth.get("serviceAccountEmail") != want_sa:
        diffs.append(
            f"oauthToken.serviceAccountEmail {oauth.get('serviceAccountEmail')!r} != {want_sa}"
        )
    if describe.get("state") == "PAUSED":
        diffs.append("trigger is PAUSED — the scheduled corpus probe is not running")
    return diffs
