# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The scheduled parser-canary job — declaration, render, verify.

P37.15 (BL-025 canary part; SIG-PARSE-007/008, RISK-P7-06).
``ops/parser_canary.toml`` is the committed ``sig.parser-canary/1``
declaration of the permanent ``sig-parser-canary`` Cloud Run job — the daily
fixture-replay canary that re-runs every parser family's committed sample
through the family's own parse + ``canary_findings`` path and raises the
typed ``parser_drift`` issue (a recorded alert + the report's typed-issue
entries) on drift — plus its ``sig-sched-parser-canary`` Cloud Scheduler
trigger. This module is the engine ``ops/gcp/parser-canary.sh`` drives,
sibling to ``rdc_job.py``/``quality_job.py`` (whose window predicates, name
regexes, and scheduler/trigger argv helpers it reuses verbatim — same
contract windows, same suppression semantics).

Per run the in-container command (``sig-ops parser-canary scheduled``):

1. re-checks the OM-19 windows — a fire inside 03:00–06:30Z or the monthly
   batch window records a ``skipped`` ``sig.probe-run/1`` instead of
   running (defence in depth for a drifted or manually invoked trigger);
2. replays every declared parser family's committed corpus sample through
   the family's own parse + ``canary_findings`` path — the deployed image's
   parsers are what is verified, never a re-download;
3. writes ``sig.parser-canary-report/1`` + ``sig.probe-run/1`` as NEW
   timestamped objects under the conditioned ``ops/probes/`` objectCreator
   scope — every drifted family lands as a typed ``parser_drift`` issue
   entry in the report, and the run fires the recorded-alert seam.

The job needs no database and no capture-store read: the sealed corpus rides
the workload image (``tests/parser_canary/`` is COPYed into ``/app`` — the
image digest pins the corpus version), and the bucket API auth is the
runtime service account's metadata-server token. Its only secret is the
alert webhook token the recorded-alert channel consumes (HG-09 — mounted
as a Secret Manager binding, never a literal).

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
    SECRET_NAME_RE,
    TASK_TIMEOUT_RE,
    Scheduler,
    SecretEnv,
    check_image_ref,
    sa_email,
    validate_schedule,
)

SCHEMA: Final = "sig.parser-canary/1"
DEFAULT_DECLARATION_PATH: Final = Path(__file__).resolve().parents[2] / "parser_canary.toml"

COMMAND_RE: Final = re.compile(r"^[a-zA-Z0-9_./-]+$")
ALERT_KIND_RE: Final = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _fail(msg: str) -> NoReturn:
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# The parsed declaration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParserCanaryProbe:
    """One parsed ``sig.parser-canary/1`` declaration."""

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
    probe_prefix: str
    alert_kind: str
    scheduler: Scheduler
    secret_env: tuple[SecretEnv, ...]
    plain_env: tuple[str, ...]


def load_declaration(path: str | Path | None = None) -> ParserCanaryProbe:
    """Load + validate the declaration — fail closed on any drift."""
    p = Path(path) if path else DEFAULT_DECLARATION_PATH
    try:
        doc = tomllib.loads(p.read_bytes().decode("utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        _fail(f"parser-canary declaration unreadable: {e}")
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
        _fail(f"{p}: tasks must be exactly 1 — a single canary run, never a fleet")
    if "max_retries" not in doc or int(doc["max_retries"]) != 0:
        _fail(
            f"{p}: max_retries must be 0 — a drifted/failed run is recorded + "
            "alerted, never retried inside a suppression window"
        )
    timeout = _str("task_timeout")
    m = TASK_TIMEOUT_RE.match(timeout)
    if not m or not (60 <= int(m.group(1)) <= 86400):
        _fail(f"{p}: task_timeout {timeout!r} must be a bounded seconds value (60–86400s)")
    corpus_root = _str("corpus_root")
    if not corpus_root.startswith("/app/"):
        _fail(
            f"{p}: corpus_root {corpus_root!r} must sit under /app — the corpus "
            "rides the workload image (its digest pins the corpus version)"
        )
    probe_prefix = _str("probe_prefix")
    if not PREFIX_RE.match(probe_prefix) or not probe_prefix.startswith("ops/probes/"):
        _fail(
            f"{p}: probe_prefix {probe_prefix!r} must be a bucket-relative prefix "
            "under ops/probes/ — the conditioned objectCreator scope"
        )
    alert_kind = _str("alert_kind")
    if not ALERT_KIND_RE.match(alert_kind):
        _fail(f"{p}: alert_kind {alert_kind!r} is not a valid alert kind")

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

    secret_env: list[SecretEnv] = []
    seen: set[str] = set()
    for i, raw in enumerate(doc.get("secret_env") or []):
        if not isinstance(raw, dict):
            _fail(f"{p}: secret_env {i} must be a table")
        env, secret = str(raw.get("env") or ""), str(raw.get("secret") or "")
        if not ENV_NAME_RE.match(env):
            _fail(f"{p}: secret_env {i}.env {env!r} is not an env name")
        if not SECRET_NAME_RE.match(secret):
            _fail(f"{p}: secret_env {i}.secret {secret!r} is not a secret name")
        if env in seen:
            _fail(f"{p}: secret_env {i}: {env} declared twice")
        seen.add(env)
        secret_env.append(SecretEnv(env=env, secret=secret))

    plain_env_raw = doc.get("plain_env") or []
    if not isinstance(plain_env_raw, list):
        _fail(f"{p}: plain_env must be a list of env names")
    plain_env: list[str] = []
    for name in plain_env_raw:
        if not isinstance(name, str) or not ENV_NAME_RE.match(name):
            _fail(f"{p}: plain_env name {name!r} is not an env name")
        if name in seen:
            _fail(f"{p}: {name} is declared as a secret env — never a plain var")
        plain_env.append(str(name))

    return ParserCanaryProbe(
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
        probe_prefix=probe_prefix,
        alert_kind=alert_kind,
        scheduler=scheduler,
        secret_env=tuple(secret_env),
        plain_env=tuple(plain_env),
    )


# ---------------------------------------------------------------------------
# The rendered mutation set
# ---------------------------------------------------------------------------


def deploy_argv(
    decl: ParserCanaryProbe,
    *,
    project: str,
    region: str,
    image: str,
    env_values: dict[str, str],
) -> list[str]:
    """The idempotent `gcloud run jobs deploy` argv — every declared plain
    env name must resolve to a value (no silent empty vars), and every
    secret binding comes only from the declaration. No Cloud SQL
    connector — the corpus rides the image and the bucket API is the
    runtime identity's metadata-server token."""
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
    if decl.secret_env:
        argv.append(
            "--set-secrets=" + ",".join(f"{s.env}={s.secret}:latest" for s in decl.secret_env)
        )
    return argv


def invoker_argv(decl: ParserCanaryProbe, *, project: str, region: str) -> list[str]:
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


def trigger_uri(decl: ParserCanaryProbe, *, project: str, region: str) -> str:
    """The Run API `:run` endpoint the scheduler POSTs (the jobs pattern)."""
    return (
        f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
        f"namespaces/{project}/jobs/{decl.job}:run"
    )


def trigger_argv(
    decl: ParserCanaryProbe, *, project: str, region: str, update: bool = False
) -> list[str]:
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


def rollback_argv(decl: ParserCanaryProbe, *, project: str, region: str) -> dict[str, list[str]]:
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
    decl: ParserCanaryProbe,
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


def verify_describe(
    decl: ParserCanaryProbe, describe: dict[str, Any], *, project: str
) -> list[str]:
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
    # Secret envs: exactly the declared set, mounted by name — never envFrom,
    # never an undeclared secret.
    declared_secrets = {s.env for s in decl.secret_env}
    seen_secrets: set[str] = set()
    for e in container.get("env") or []:
        if "secretKeyRef" in (e.get("valueFrom") or {}):
            seen_secrets.add(str(e.get("name")))
    for e in seen_secrets:
        if e not in declared_secrets:
            diffs.append(f"undeclared secret env {e} mounted")
    for e in declared_secrets - seen_secrets:
        diffs.append(f"declared secret env {e} absent — the alert path is unarmed")
    for e in container.get("envFrom") or []:
        diffs.append(f"envFrom {e!r} — the allow-list only admits named env vars")
    # The job reads no database — a Cloud SQL connector is drift.
    if spec.get("cloudSqlInstances"):
        diffs.append("a Cloud SQL connector is attached — the job declares none")
    return diffs


def verify_trigger(
    decl: ParserCanaryProbe, describe: dict[str, Any], *, project: str, region: str
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
        diffs.append("trigger is PAUSED — the scheduled parser canary is not running")
    return diffs


__all__ = [
    "SCHEMA",
    "ParserCanaryProbe",
    "deploy_argv",
    "invoker_argv",
    "load_declaration",
    "render",
    "rollback_argv",
    "sa_email",
    "trigger_argv",
    "trigger_uri",
    "verify_describe",
    "verify_trigger",
]
