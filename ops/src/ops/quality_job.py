# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The nightly graph-quality probe job — declaration, render, verify.

P34.44b (SIG-CONF-006/007/009, ADR-154/205). ``ops/quality_probe.toml`` is the
committed ``sig.quality-probe/1`` declaration of the permanent
``sig-quality-probe`` Cloud Run job and its ``sig-sched-quality-probe`` Cloud
Scheduler trigger. This module is the engine ``ops/gcp/quality-probe.sh``
drives:

* :func:`load_declaration` — fail-closed validation (one task, zero retries,
  a bounded timeout, the reserved runtime identity, and a schedule that can
  structurally never fire inside the contract's two suppression windows);
* the ``*_argv`` renderers — the exact ``gcloud`` mutation set (idempotent
  upserts: ``run jobs deploy``, a name-checked IAM binding, and the
  scheduler create/update the leg chooses between);
* :func:`verify_describe` / :func:`verify_trigger` — the recorded describes
  judged against the declaration (the live-diff half of the leg);
* the window math — :func:`suppression_reason` is the SAME predicate the
  in-container ``sig-ops quality nightly`` verb runs before connecting: a
  fire inside 03:00–06:30Z or the monthly batch window (day 6 00:00Z → day
  13 12:00Z) records a ``suppressed`` ``sig.probe-run/1`` instead of running
  — defence in depth against a drifted or manually-invoked trigger.

No function here opens a socket, shells out, or reads the environment.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Final, NoReturn

SCHEMA: Final = "sig.quality-probe/1"
DEFAULT_DECLARATION_PATH: Final = Path(__file__).resolve().parents[2] / "quality_probe.toml"

JOB_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
SA_ID_RE: Final = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
SECRET_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9_-]{0,127}$")
ENV_NAME_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")
PREFIX_RE: Final = re.compile(r"^[a-z0-9][a-z0-9._/-]*/$")
TASK_TIMEOUT_RE: Final = re.compile(r"^([0-9]+)s$")

# --- the contract's suppression windows (OM-19, row 256) --------------------
# The AR-3 daily quiet band: never 03:00–06:30Z.
QUIET_START_MIN: Final = 3 * 60
QUIET_END_MIN: Final = 6 * 60 + 30
# The monthly ingest-batch window: day 6 00:00Z → day 13 12:00Z (the batch
# jobs own those nights; the quality probe must not contend).
BATCH_START_DAY: Final = 6
BATCH_END_DAY: Final = 13
BATCH_END_MIN: Final = 12 * 60

RUN_INVOKER_ROLE: Final = "roles/run.invoker"


def _fail(msg: str) -> NoReturn:
    raise ValueError(msg)


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# The window predicates — shared by the leg script's contract, the
# declaration's static schedule validation, and the in-job suppression.
# ---------------------------------------------------------------------------


def _minute_of_day(now: datetime) -> int:
    return now.hour * 60 + now.minute


def in_quiet_hours(now: datetime) -> bool:
    """True inside the AR-3 daily band: 03:00Z ≤ t < 06:30Z (UTC)."""
    now = now.astimezone(UTC)
    return QUIET_START_MIN <= _minute_of_day(now) < QUIET_END_MIN


def in_batch_window(now: datetime) -> bool:
    """True inside the monthly ingest-batch window: day 6 00:00Z through
    day 13 12:00Z (exclusive) — the scheduled quality probe never runs then.
    """
    now = now.astimezone(UTC)
    if now.day < BATCH_START_DAY or now.day > BATCH_END_DAY:
        return False
    if now.day < BATCH_END_DAY:
        return True
    return _minute_of_day(now) < BATCH_END_MIN


def suppression_reason(now: datetime | None = None) -> str | None:
    """Why a run at ``now`` must record ``suppressed`` rather than run, or
    None when the run may proceed. Checked in-container BEFORE any
    connection is opened — the in-job half of the window contract."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    if in_quiet_hours(now):
        return "quiet-hours-03:00-06:30Z"
    if in_batch_window(now):
        return "batch-window-day6T00:00Z-day13T12:00Z"
    return None


def leg_window_reason(now: datetime, *, earliest: str = "") -> str | None:
    """The leg script's clock guard as one predicate: ``earliest`` is the
    contract's ISO-UTC lower bound (the AR-3/AR-2 earliest); the quiet band
    and the batch window are the same predicates the job suppresses on.
    Returns a refusal reason or None."""
    now = now.astimezone(UTC)
    if earliest and now.isoformat().replace("+00:00", "Z") < earliest:
        return "before-earliest"
    return suppression_reason(now)


# ---------------------------------------------------------------------------
# Static schedule legality — the declaration's cron may never fire inside
# either window, independent of the in-job suppression.
# ---------------------------------------------------------------------------


def fire_times(cron: str, *, start: date, days: int = 400) -> list[datetime]:
    """Enumerate every fire the five-field cron schedules over ``days`` days
    from ``start`` (Vixie dom/dow OR-semantics — the same grammar
    ``ops.cadence_window`` parses)."""
    from .cadence_window import parse_cron

    minutes, hours, doms, months, dows = parse_cron(cron)
    fields = cron.split("#", 1)[0].split()
    dom_field, dow_field = fields[2], fields[4]
    out: list[datetime] = []
    for i in range(days):
        day = start + timedelta(days=i)
        if day.month not in months:
            continue
        in_dom = day.day in doms
        in_dow = (day.isoweekday() % 7) in dows
        # Vixie: two restricted day-fields match either; otherwise both must.
        if not dom_field.startswith("*") and not dow_field.startswith("*"):
            match = in_dom or in_dow
        else:
            match = in_dom and in_dow
        if match:
            out.extend(
                datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
                for hour in sorted(hours)
                for minute in sorted(minutes)
            )
    return out


def validate_schedule(schedule: str) -> list[str]:
    """Every way the cron could violate the contract's windows — the static
    half of 'never 03:00–06:30Z, skips the batch window'. Empty = legal."""
    try:
        fires = fire_times(schedule, start=date(2026, 1, 1), days=370)
    except ValueError as e:
        return [f"schedule {schedule!r} unparseable: {e}"]
    if not fires:
        return [f"schedule {schedule!r} fires nowhere in 370 days"]
    errors: list[str] = []
    for fire in fires:
        if in_quiet_hours(fire):
            errors.append(
                f"schedule {schedule!r} fires {fire:%Y-%m-%dT%H:%MZ} inside "
                "03:00–06:30Z — the AR-3 quiet band"
            )
            break
    for fire in fires:
        if in_batch_window(fire):
            errors.append(
                f"schedule {schedule!r} fires {fire:%Y-%m-%dT%H:%MZ} inside the "
                "monthly batch window (day 6 00:00Z → day 13 12:00Z)"
            )
            break
    return errors


# ---------------------------------------------------------------------------
# The parsed declaration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecretEnv:
    env: str
    secret: str


@dataclass(frozen=True)
class Scheduler:
    name: str
    schedule: str
    time_zone: str
    invoker: str


@dataclass(frozen=True)
class QualityProbe:
    """One parsed ``sig.quality-probe/1`` declaration."""

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
    cloudsql_instance: str
    db_name: str
    probe_prefix: str
    alert_kind: str
    scheduler: Scheduler
    secret_env: tuple[SecretEnv, ...]
    plain_env: tuple[str, ...]


def load_declaration(path: str | Path | None = None) -> QualityProbe:
    """Load + validate the declaration — fail closed on any drift."""
    p = Path(path) if path else DEFAULT_DECLARATION_PATH
    try:
        doc = tomllib.loads(p.read_bytes().decode("utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        _fail(f"quality-probe declaration unreadable: {e}")
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
    if not re.match(r"^[a-zA-Z0-9_./-]+$", command):
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
            f"{p}: max_retries must be 0 — a failed run is recorded + alerted, "
            "never retried inside a suppression window"
        )
    timeout = _str("task_timeout")
    m = TASK_TIMEOUT_RE.match(timeout)
    if not m or not (60 <= int(m.group(1)) <= 86400):
        _fail(f"{p}: task_timeout {timeout!r} must be a bounded seconds value (60–86400s)")
    prefix = _str("probe_prefix")
    if not PREFIX_RE.match(prefix) or not prefix.startswith("ops/probes/"):
        _fail(
            f"{p}: probe_prefix {prefix!r} must be a bucket-relative prefix under "
            "ops/probes/ — the conditioned objectCreator scope"
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
    if not secret_env:
        _fail(f"{p}: at least one [[secret_env]] is required (the audit credential)")

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

    return QualityProbe(
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
        cloudsql_instance=_str("cloudsql_instance"),
        db_name=_str("db_name"),
        probe_prefix=prefix,
        alert_kind=_str("alert_kind"),
        scheduler=scheduler,
        secret_env=tuple(secret_env),
        plain_env=tuple(plain_env),
    )


# ---------------------------------------------------------------------------
# The rendered mutation set
# ---------------------------------------------------------------------------


def sa_email(project: str, sa_id: str) -> str:
    return f"{sa_id}@{project}.iam.gserviceaccount.com"


def check_image_ref(image: str) -> None:
    """A job is deployed by digest only (ADR-111)."""
    if "@sha256:" not in image:
        _fail(f"image {image!r} is not digest-pinned — resolve the digest first (ADR-111)")


def deploy_argv(
    decl: QualityProbe,
    *,
    project: str,
    region: str,
    image: str,
    env_values: dict[str, str],
) -> list[str]:
    """The idempotent `gcloud run jobs deploy` argv — one per declared
    plain-env name must resolve to a value (no silent empty vars), and every
    secret binding comes only from the declaration."""
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
        f"--set-cloudsql-instances={project}:{region}:{decl.cloudsql_instance}",
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
    argv.append("--set-secrets=" + ",".join(f"{s.env}={s.secret}:latest" for s in decl.secret_env))
    return argv


def invoker_argv(decl: QualityProbe, *, project: str, region: str) -> list[str]:
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


def trigger_uri(decl: QualityProbe, *, project: str, region: str) -> str:
    """The Run API `:run` endpoint the scheduler POSTs (the jobs pattern)."""
    return (
        f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
        f"namespaces/{project}/jobs/{decl.job}:run"
    )


def trigger_argv(
    decl: QualityProbe, *, project: str, region: str, update: bool = False
) -> list[str]:
    """The scheduler create-or-update argv (`update` swaps `create` for
    `update` — the leg picks after a describe)."""
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


def rollback_argv(decl: QualityProbe, *, project: str, region: str) -> dict[str, list[str]]:
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
    decl: QualityProbe,
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


def verify_describe(decl: QualityProbe, describe: dict[str, Any], *, project: str) -> list[str]:
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
    secret_env_seen: set[str] = set()
    for e in container.get("env") or []:
        src = (e.get("valueFrom") or {}).get("secretKeyRef")
        if src:
            secret_env_seen.add(str(e.get("name")))
    for e in secret_env_seen:
        if e not in {s.env for s in decl.secret_env}:
            diffs.append(f"undeclared secret env {e} mounted")
    for e in container.get("envFrom") or []:
        diffs.append(f"envFrom {e!r} — the allow-list only admits named env secrets")
    # The Cloud SQL connector, surfaced as spec.cloudSqlInstances or the
    # annotation (same tolerance as the exec host's verify).
    annotations = (
        describe.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
        or {}
    )
    instances = spec.get("cloudSqlInstances") or []
    conn = f"{project}:{decl.cloudsql_instance}"
    ann = annotations.get("run.googleapis.com/cloudsql-instances", "")
    if not instances and conn not in ann and f":{decl.cloudsql_instance}" not in ann:
        diffs.append("no Cloud SQL connector declared on the task")
    return diffs


def verify_trigger(
    decl: QualityProbe, describe: dict[str, Any], *, project: str, region: str
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
        diffs.append("trigger is PAUSED — the nightly probe is not running")
    return diffs


__all__ = [
    "BATCH_END_DAY",
    "BATCH_END_MIN",
    "BATCH_START_DAY",
    "QUIET_END_MIN",
    "QUIET_START_MIN",
    "RUN_INVOKER_ROLE",
    "SCHEMA",
    "QualityProbe",
    "Scheduler",
    "SecretEnv",
    "check_image_ref",
    "deploy_argv",
    "fire_times",
    "in_batch_window",
    "in_quiet_hours",
    "invoker_argv",
    "leg_window_reason",
    "load_declaration",
    "render",
    "rollback_argv",
    "sa_email",
    "suppression_reason",
    "trigger_argv",
    "trigger_uri",
    "validate_schedule",
    "verify_describe",
    "verify_trigger",
]
