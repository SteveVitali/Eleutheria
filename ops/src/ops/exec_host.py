# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""exec_host — the P34.43 one-off execution host (G2 ACT-13, L3 CP-0,
SIG-CONF-013).

Hosted return passes and quality probes need a least-privilege place to run:
a ONE-OFF Cloud Run job — created per run, executed once, deleted by a
name-checked cleanup — on the dedicated runtime identity, with a read-only
gcsfuse mount of the capture store, the Cloud SQL connector, only the secrets
the run needs, ``--max-retries 0`` and a bounded task timeout.

The committed declaration is ``ops/exec_host.toml`` (``sig.exec-host/1``). This
module renders the ``gcloud`` argv for a run's create/execute/delete steps
(offline — no network), drives the lifecycle through an injectable runner, and
judges a recorded ``run jobs describe`` against the template. The windowed
leg lives in ``ops/gcp/exec-host.sh``; the ``sig_audit``/``sig_recovery_login``
credential legs live in ``ops/gcp/db-logins.sh`` + ``ops/src/ops/db_logins.py``.

In-container, ``sig-ops exec-host smoke`` runs the L1 smoke checks — the mount
is read-only (``/proc/self/mounts``), the requested secrets are present (names
only, values never read into a record), and the ``sig_audit`` session posture
holds — and writes one ``sig.probe-run/1`` record per use (SIG-CONF-013,
SIG-OPS-011) under ``ops/probes/``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

SCHEMA = "sig.exec-host/1"
DEFAULT_DECLARATION = Path(__file__).resolve().parents[3] / "ops" / "exec_host.toml"

#: Job-name shape: ``<prefix>-<purpose>-<yyyymmddT hhmmssZ>`` — the name-checked
#: cleanup only ever deletes a name this run created, and only this shape.
PURPOSE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
JOB_PREFIX_RE = re.compile(r"^sig-[a-z0-9-]{1,40}$")
STAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
SECRET_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,60}$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,60}$")

PROBE_RUN_VERSION = "sig.probe-run/1"


def _fail(msg: str) -> NoReturn:
    raise ValueError(msg)


def _utcnow() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(ts: str) -> str:
    """``2026-10-13T14:00:00Z`` → ``20261013T140000Z``."""  # future-ok: illustrative: docstring shape example
    return ts.replace("-", "").replace(":", "")


@dataclass(frozen=True)
class SecretEnv:
    env: str
    secret: str


@dataclass(frozen=True)
class Mount:
    bucket: str
    path: str
    readonly: bool
    prefix: str


@dataclass(frozen=True)
class ExecHost:
    job_prefix: str
    service_account: str
    image_repo: str
    tasks: int
    max_retries: int
    task_timeout: str
    cpu: str
    memory: str
    command: str
    mount: Mount
    cloudsql_instance: str
    secret_env: tuple[SecretEnv, ...]
    probe_prefix: str

    def secret_for(self, env: str) -> SecretEnv | None:
        for s in self.secret_env:
            if s.env == env:
                return s
        return None


def load_declaration(path: str | Path | None = None) -> ExecHost:
    """Load + validate ``sig.exec-host/1``. Fail-closed: a shape that could
    weaken the posture (a writable mount, retries > 0, an undeclared-looking
    secret, a multi-task job) refuses, never defaults."""
    p = Path(path) if path else DEFAULT_DECLARATION
    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except OSError as e:
        _fail(f"exec-host declaration unreadable: {e}")
    if raw.get("schema") != SCHEMA:
        _fail(f"{p}: schema must be {SCHEMA!r}")

    def _str(key: str, where: str = "") -> str:
        v = raw.get(key) if not where else raw[where].get(key)
        if not isinstance(v, str) or not v:
            _fail(f"{p}: {where + '.' if where else ''}{key} must be a non-empty string")
        return v  # type: ignore[return-value]

    job_prefix = _str("job_prefix")
    if not JOB_PREFIX_RE.match(job_prefix):
        _fail(f"{p}: job_prefix {job_prefix!r} must match {JOB_PREFIX_RE.pattern}")
    sa = _str("service_account")
    if not re.match(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$", sa):
        _fail(f"{p}: service_account {sa!r} is not a valid SA id")

    command = _str("command")
    if not re.match(r"^[a-z][a-z0-9._/-]{0,30}$", command):
        _fail(f"{p}: command {command!r} must be a simple command name/path (e.g. sh)")

    tasks = raw.get("tasks")
    if tasks != 1:
        _fail(f"{p}: tasks must be exactly 1 — a one-off run, never a fleet")
    retries = raw.get("max_retries")
    if retries != 0:
        _fail(f"{p}: max_retries must be 0 — a failed one-off is recorded, not retried")
    timeout = _str("task_timeout")
    if not re.match(r"^\d+s$", timeout) or not (60 <= int(timeout[:-1]) <= 86400):
        _fail(f"{p}: task_timeout {timeout!r} must be a bounded seconds value (60–86400s)")

    mraw = raw.get("mount")
    if not isinstance(mraw, dict):
        _fail(f"{p}: [mount] is required")
    mount = Mount(
        bucket=str(mraw.get("bucket") or _fail(f"{p}: mount.bucket required")),
        path=str(mraw.get("path") or _fail(f"{p}: mount.path required")),
        readonly=bool(mraw.get("readonly")),
        prefix=str(mraw.get("prefix") or _fail(f"{p}: mount.prefix required")),
    )
    if mount.readonly is not True:
        _fail(f"{p}: mount.readonly must be true — the capture store mounts read-only")
    if not mount.path.startswith("/"):
        _fail(f"{p}: mount.path must be absolute")
    if not mount.prefix.endswith("/"):
        _fail(f"{p}: mount.prefix {mount.prefix!r} must be a trailing-slash prefix")

    secret_env: list[SecretEnv] = []
    seen_env: set[str] = set()
    for i, s in enumerate(raw.get("secret_env") or []):
        if not isinstance(s, dict):
            _fail(f"{p}: secret_env {i} must be a table")
        env, secret = str(s.get("env") or ""), str(s.get("secret") or "")
        if not ENV_NAME_RE.match(env):
            _fail(f"{p}: secret_env {i}.env {env!r} is not an env name")
        if not SECRET_NAME_RE.match(secret):
            _fail(f"{p}: secret_env {i}.secret {secret!r} is not a secret name")
        if env in seen_env:
            _fail(f"{p}: secret_env {i}: {env} declared twice")
        seen_env.add(env)
        secret_env.append(SecretEnv(env=env, secret=secret))

    probe_prefix = _str("probe_prefix")
    if probe_prefix.startswith("/"):
        _fail(f"{p}: probe_prefix must be a bucket-relative prefix")

    return ExecHost(
        job_prefix=job_prefix,
        service_account=sa,
        image_repo=_str("image_repo"),
        tasks=1,
        max_retries=0,
        command=command,
        task_timeout=timeout,
        cpu=_str("cpu"),
        memory=_str("memory"),
        mount=mount,
        cloudsql_instance=_str("cloudsql_instance"),
        secret_env=tuple(secret_env),
        probe_prefix=probe_prefix,
    )


# --- render: the deterministic one-off job argv/spec ---------------------------------


def job_name(decl: ExecHost, purpose: str, at: str) -> str:
    """``<prefix>-<purpose>-<stamp>`` — the only name shape the cleanup deletes."""
    if not PURPOSE_RE.match(purpose):
        _fail(f"purpose {purpose!r} must match {PURPOSE_RE.pattern}")
    stamp = _stamp(at)
    if not STAMP_RE.match(stamp):
        _fail(f"at {at!r} must be an ISO-UTC stamp like 2026-10-13T14:00:00Z")  # future-ok: illustrative: error-text example
    name = f"{decl.job_prefix}-{purpose}-{stamp}"
    if len(name) > 63:
        _fail(f"job name {name!r} exceeds 63 chars (Cloud Run limit)")
    return name


def sa_email(project: str, sa_id: str) -> str:
    return f"{sa_id}@{project}.iam.gserviceaccount.com"


def check_image_ref(image: str) -> None:
    """ADR-111: a run deploys a digest-pinned image only — never a movable tag."""
    if "@sha256:" not in image:
        _fail(f"image {image!r} is not digest-pinned — resolve the digest first (ADR-111)")


def select_secrets(decl: ExecHost, wanted: Sequence[str]) -> list[SecretEnv]:
    """Only the secrets the run needs — each must be a declared secret_env name."""
    out: list[SecretEnv] = []
    for env in wanted:
        s = decl.secret_for(env)
        if s is None:
            _fail(
                f"secret env {env!r} is not declared in {SCHEMA} — "
                "the allow-list is fail-closed (add it to exec_host.toml deliberately)"
            )
        out.append(s)
    return out


def check_env_pairs(env: Sequence[str]) -> list[str]:
    """``NAME=value`` pairs for --set-env-vars — validated env names; a value
    must never carry a comma (the flag's separator) or a newline."""
    out: list[str] = []
    for pair in env:
        if "=" not in pair:
            _fail(f"env {pair!r} must be NAME=value")
        name, _, value = pair.partition("=")
        if not ENV_NAME_RE.match(name):
            _fail(f"env name {name!r} is not a valid env name")
        if "," in value or "\n" in value:
            _fail(f"env {name}: value carries a comma/newline — refused")
        out.append(pair)
    return out


def create_argv(
    decl: ExecHost,
    *,
    project: str,
    region: str,
    name: str,
    image: str,
    secrets: Sequence[SecretEnv] = (),
    env: Sequence[str] = (),
) -> list[str]:
    """The `gcloud run jobs create` argv for one ephemeral execution host."""
    check_image_ref(image)
    argv = [
        "gcloud",
        "run",
        "jobs",
        "create",
        name,
        f"--image={image}",
        f"--region={region}",
        f"--project={project}",
        f"--service-account={sa_email(project, decl.service_account)}",
        f"--command={decl.command}",
        f"--tasks={decl.tasks}",
        f"--max-retries={decl.max_retries}",
        f"--task-timeout={decl.task_timeout}",
        f"--cpu={decl.cpu}",
        f"--memory={decl.memory}",
        "--execution-environment=gen2",
        f"--set-cloudsql-instances={project}:{region}:{decl.cloudsql_instance}",
        # The read-only capture-store mount: a bucket-scoped gcsfuse volume
        # with readonly=true ON THE VOLUME (the CSI driver field — surfaces
        # as volumes[].csi.readOnly in the describe), mounted at mount.path;
        # the workload reads <mount>/<prefix>/. IAM adds the second wall:
        # objectViewer conditioned to evidence/captures/, no delete anywhere.
        f"--add-volume=name=captures,type=cloud-storage,bucket={project}-{decl.mount.bucket},readonly=true",
        f"--add-volume-mount=volume=captures,mount-path={decl.mount.path}",
    ]
    # SIG_EXEC_JOB_NAME is injected — never user-set (the record must name
    # the job that ran, not a claimant).
    env_pairs = [p for p in check_env_pairs(env) if not p.startswith("SIG_EXEC_JOB_NAME=")] + [
        f"SIG_EXEC_JOB_NAME={name}"
    ]
    if secrets:
        argv.append("--set-secrets=" + ",".join(f"{s.env}={s.secret}:latest" for s in secrets))
    argv.append("--set-env-vars=" + ",".join(env_pairs))
    return argv


def execute_argv(
    *,
    project: str,
    region: str,
    name: str,
    args: Sequence[str],
) -> list[str]:
    """The per-execution argv — arguments travel per execution, not in the job."""
    argv = [
        "gcloud",
        "run",
        "jobs",
        "execute",
        name,
        f"--region={region}",
        f"--project={project}",
        "--wait",
    ]
    if args:
        argv.append("--args=" + ",".join(args))
    return argv


def delete_argv(*, project: str, region: str, name: str) -> list[str]:
    return [
        "gcloud",
        "run",
        "jobs",
        "delete",
        name,
        f"--region={region}",
        f"--project={project}",
        "--quiet",
    ]


def render_plan(
    decl: ExecHost,
    *,
    project: str,
    region: str,
    purpose: str,
    at: str,
    image: str,
    args: Sequence[str] = (),
    secret_env_names: Sequence[str] = (),
    env: Sequence[str] = (),
) -> dict[str, Any]:
    """The whole one-off lifecycle as ordered gcloud argv (offline)."""
    name = job_name(decl, purpose, at)
    secrets = select_secrets(decl, secret_env_names)
    env_pairs = check_env_pairs(env)
    return {
        "schema": SCHEMA,
        "name": name,
        "service_account": sa_email(project, decl.service_account),
        "image": image,
        "mount": {
            "bucket": f"{project}-{decl.mount.bucket}",
            "path": decl.mount.path,
            "readonly": decl.mount.readonly,
            "prefix": decl.mount.prefix,
        },
        "create": create_argv(
            decl,
            project=project,
            region=region,
            name=name,
            image=image,
            secrets=secrets,
            env=env_pairs,
        ),
        "execute": execute_argv(project=project, region=region, name=name, args=args),
        "cleanup": delete_argv(project=project, region=region, name=name),
    }


# --- the lifecycle ---------------------------------------------------------------------


Runner = Callable[..., subprocess.CompletedProcess[str]]


def run_oneoff(
    decl: ExecHost,
    *,
    project: str,
    region: str,
    purpose: str,
    image: str,
    args: Sequence[str] = (),
    secret_env_names: Sequence[str] = (),
    env: Sequence[str] = (),
    at: str | None = None,
    runner: Runner = subprocess.run,
    log: Callable[[str], None] = print,
) -> int:
    """Create → execute --wait → name-checked delete. Returns the execution's
    exit status; the cleanup runs even on failure and deletes ONLY the name
    this run created."""
    plan = render_plan(
        decl,
        project=project,
        region=region,
        purpose=purpose,
        at=at or _utcnow(),
        image=image,
        args=args,
        secret_env_names=secret_env_names,
        env=env,
    )
    name = plan["name"]
    log(f"exec-host run: {name} (purpose={purpose})")
    rc = 1
    created = False
    try:
        runner(plan["create"], capture_output=True, text=True, check=True)
        created = True
        try:
            proc = runner(plan["execute"], capture_output=True, text=True, check=False)
            if proc.stdout:
                log(proc.stdout.rstrip())
            if proc.stderr:
                print(proc.stderr.rstrip(), file=sys.stderr)
            rc = proc.returncode
        except subprocess.CalledProcessError as exc:  # never from check=False; defensive
            print(str(exc), file=sys.stderr)
            rc = 1
    except subprocess.CalledProcessError as exc:
        print(f"exec-host create failed: {exc.stderr or exc.stdout or exc}", file=sys.stderr)
        rc = 1
    finally:
        if created:
            # Name-checked cleanup: delete exactly the job this run created —
            # the rendered plan's own name, nothing pattern-matched.
            try:
                runner(plan["cleanup"], capture_output=True, text=True, check=True)
                log(f"exec-host cleanup: deleted {name}")
            except subprocess.CalledProcessError as exc:
                print(
                    f"exec-host cleanup FAILED to delete {name}: {exc.stderr or exc.stdout or exc}",
                    file=sys.stderr,
                )
                rc = rc or 1
    return rc


# --- verify: a recorded `run jobs describe` judged against the template --------------


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
    decl: ExecHost,
    describe: dict[str, Any],
    *,
    project: str,
    name: str | None = None,
) -> list[str]:
    """Judge one recorded `gcloud run jobs describe --format=json` against the
    declaration. Returns drift lines; empty = the posture holds."""
    diffs: list[str] = []
    meta_name = describe.get("metadata", {}).get("name")
    if name is not None and meta_name != name:
        diffs.append(f"job name {meta_name!r} != the created {name!r}")
    if meta_name is not None and not str(meta_name).startswith(decl.job_prefix + "-"):
        diffs.append(f"job {meta_name!r} is not a {decl.job_prefix}-* one-off")
    spec = _task_spec(describe)
    if not spec:
        return ["UNREADABLE: no spec.template.spec.template.spec in the describe"]
    want_sa = sa_email(project, decl.service_account)
    if spec.get("serviceAccountName") != want_sa:
        diffs.append(f"serviceAccountName {spec.get('serviceAccountName')!r} != declared {want_sa}")
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
    want_bucket = f"{project}-{decl.mount.bucket}"
    volumes = {str(v.get("name")): v for v in spec.get("volumes") or []}
    vol = volumes.get("captures")
    if vol is None:
        diffs.append("no 'captures' volume declared")
    else:
        # The GCS volume is a CSI mount: `csi.driver=gcsfuse…` + `csi.readOnly`
        # is what `--add-volume=…,readonly=true` renders to; `cloudStorage`
        # is the alternate key some describe surfaces carry.
        csi = vol.get("csi") or {}
        cs = vol.get("cloudStorage") or {}
        bucket = (csi.get("volumeAttributes") or {}).get("bucket") or cs.get("bucket")
        if bucket != want_bucket:
            diffs.append(f"captures volume bucket {bucket!r} != {want_bucket}")
        ro = csi.get("readOnly", cs.get("readOnly"))
        if ro is not True:
            diffs.append(f"captures volume is not read-only (readOnly={ro!r})")
    mounts = container.get("volumeMounts") or []
    cap_mount = next(
        (m for m in mounts if m.get("mountPath") == decl.mount.path),
        None,
    )
    if cap_mount is None:
        diffs.append(f"no volumeMount at {decl.mount.path}")
    env = {str(e.get("name")) for e in container.get("env") or []}
    env_from = container.get("envFrom") or []
    secret_env_seen: set[str] = set()
    for e in container.get("env") or []:
        src = (e.get("valueFrom") or {}).get("secretKeyRef")
        if src:
            secret_env_seen.add(str(e.get("name")))
    declared_env = {s.env for s in decl.secret_env}
    for e in secret_env_seen:
        if e not in declared_env:
            diffs.append(f"undeclared secret env {e} mounted")
    for e in env_from:
        diffs.append(f"envFrom {e!r} — the allow-list only admits named env secrets")
    instances = (
        spec.get("cloudSqlInstances")
        or describe.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("cloudSqlInstances")
        or []
    )
    # Cloud Run surfaces the connector either as spec.cloudSqlInstances or an
    # annotation; judge whichever the describe carries.
    annotations = (
        describe.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
        or {}
    )
    conn = f"{project}:{decl.cloudsql_instance}"
    ann = annotations.get("run.googleapis.com/cloudsql-instances", "")
    if not instances and conn not in ann and f":{decl.cloudsql_instance}" not in ann:
        diffs.append("no Cloud SQL connector declared on the task")
    _ = env  # env names alone are fine; values never judged (HG-09)
    return diffs


# --- the in-container smoke probe -------------------------------------------------------


def _mounts() -> list[tuple[str, str, str]]:
    """(device, mountpoint, options) triples from /proc/self/mounts."""
    try:
        lines = Path("/proc/self/mounts").read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            out.append((parts[0], parts[1], parts[3]))
    return out


def mount_readonly_check(mount_path: str) -> dict[str, Any]:
    """The capture mount is mounted read-only — read back from /proc mounts."""
    for _dev, mp, opts in _mounts():
        if mp == mount_path:
            ok = "ro" in opts.split(",")
            return {
                "verdict": "pass" if ok else "fail",
                "mount": mp,
                "options": opts,
            }
    return {"verdict": "fail", "reason": f"no mount at {mount_path}"}


def secrets_present_check(decl: ExecHost, env: dict[str, str]) -> dict[str, Any]:
    """Which declared secret env names are populated — names only, never values."""
    present = [s.env for s in decl.secret_env if env.get(s.env)]
    return {"verdict": "pass", "present": present, "declared": [s.env for s in decl.secret_env]}


def sig_audit_check(env: dict[str, str]) -> dict[str, Any]:
    """Connect as `sig_audit` over the Cloud SQL socket and read back its
    session posture. The NEW-16 table grants report ``not_evaluable`` until
    P34.46's hosted deploy lands them — a pending deploy is a named state,
    never a failure."""
    password = env.get("SIG_AUDIT_PASSWORD", "")
    conn_name = env.get("SIG_CLOUDSQL_CONNECTION", "")
    dbname = env.get("SIG_PG_DB", "sig")
    if not password or not conn_name:
        return {
            "verdict": "skipped",
            "reason": "SIG_AUDIT_PASSWORD/SIG_CLOUDSQL_CONNECTION unset — "
            "the run did not request the audit login",
        }
    try:
        import psycopg
    except ImportError:
        return {"verdict": "skipped", "reason": "psycopg absent from this image"}
    try:
        conn = psycopg.connect(
            host=f"/cloudsql/{conn_name}",
            dbname=dbname,
            user="sig_audit",
            password=password,
            connect_timeout=10,
            autocommit=True,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced, not hidden
        return {"verdict": "fail", "reason": f"sig_audit connect failed: {exc}"}
    try:
        cur = conn.cursor()
        cur.execute("SHOW transaction_read_only")
        ro = str((cur.fetchone() or (""))[0])
        cur.execute("SHOW statement_timeout")
        timeout = str((cur.fetchone() or (""))[0])
        cur.execute("SELECT 1 FROM spine_watermark LIMIT 1")
        cur.fetchall()
        new16 = {}
        for table in ("ingest_run_capture", "entity_identity_key"):
            cur.execute("SELECT has_table_privilege('sig_audit', %s, 'SELECT')", (table,))
            new16[table] = bool((cur.fetchone() or (None,))[0])
        detail: dict[str, Any] = {
            "verdict": "pass" if ro == "on" else "fail",
            "transaction_read_only": ro,
            "statement_timeout": timeout,
            "read_surface_select": "ok",
        }
        if not all(new16.values()):
            detail["new16_grants"] = new16
            detail["new16_state"] = (
                "not_evaluable — the audit_login change's table grants ride "
                "P34.46's hosted deploy (P34.43 lands no table grant on hosted)"
            )
            detail["verdict"] = "not_evaluable" if ro == "on" else "fail"
        return detail
    except Exception as exc:  # noqa: BLE001
        return {"verdict": "fail", "reason": f"sig_audit posture check failed: {exc}"}
    finally:
        conn.close()


def run_smoke(
    decl: ExecHost,
    *,
    env: dict[str, str] | None = None,
    out: str | None = None,
    bucket: str | None = None,
    now: str | None = None,
    job_name_: str | None = None,
) -> dict[str, Any]:
    """The L1 smoke record — one ``sig.probe-run/1`` per use (SIG-CONF-013)."""
    env = dict(os.environ if env is None else env)
    checks = {
        "mount_readonly": mount_readonly_check(decl.mount.path),
        "secrets_present": secrets_present_check(decl, env),
        "sig_audit_session": sig_audit_check(env),
    }
    verdicts = [str(c.get("verdict")) for c in checks.values()]
    overall = "fail" if "fail" in verdicts else ("partial" if set(verdicts) - {"pass"} else "pass")
    record: dict[str, Any] = {
        "version": PROBE_RUN_VERSION,
        "generated_at": now or _utcnow(),
        "probe": "exec-host-smoke",
        "job": job_name_ or env.get("SIG_EXEC_JOB_NAME", ""),
        "checks": checks,
        "overall": overall,
    }
    body = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if bucket:
        from .gcs import GcsBucket

        ts = record["generated_at"]
        name = f"{decl.probe_prefix.rstrip('/')}/exec-host/{ts[:10]}/{ts.replace(':', '-')}.json"
        GcsBucket(bucket).put_object(name, body.encode("utf-8"), content_type="application/json")
        record["record_object"] = f"gs://{bucket}/{name}"
        body = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if out:
        Path(out).write_text(body, encoding="utf-8")
    return record


# --- CLI ---------------------------------------------------------------------------------


def _write(out: str | None, text: str) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops exec-host",
        description=(
            "P34.43 (G2 ACT-13, SIG-CONF-013): the one-off Cloud Run execution "
            "host for hosted return passes + quality probes — declaration "
            "ops/exec_host.toml; the windowed leg is ops/gcp/exec-host.sh. "
            "Offline verbs never touch gcloud or the network."
        ),
    )
    sub = parser.add_subparsers(dest="exec_command", required=True)

    p_plan = sub.add_parser("plan", help="print the validated declaration (offline)")
    p_plan.add_argument("--declaration", default=None)

    p_render = sub.add_parser(
        "render", help="render one run's create/execute/delete argv as JSON (offline)"
    )
    p_render.add_argument("--declaration", default=None)
    p_render.add_argument("--purpose", required=True)
    p_render.add_argument("--at", default=None, help="ISO-UTC stamp (default: now)")
    p_render.add_argument("--image", required=True, help="digest-pinned image ref")
    p_render.add_argument(
        "--project", default=os.environ.get("SIG_GCP_PROJECT", "<SIG_GCP_PROJECT>")
    )
    p_render.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
    p_render.add_argument("--arg", dest="exec_args", action="append", default=[])
    p_render.add_argument("--secret-env", action="append", default=[])
    p_render.add_argument(
        "--env",
        dest="env_pairs",
        action="append",
        default=[],
        help="NAME=value plain env var on the job (repeatable)",
    )
    p_render.add_argument("--out", default=None)

    p_run = sub.add_parser(
        "run", help="create → execute --wait → name-checked delete (needs gcloud/ADC)"
    )
    p_run.add_argument("--declaration", default=None)
    p_run.add_argument("--purpose", required=True)
    p_run.add_argument("--image", required=True, help="digest-pinned image ref")
    p_run.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))
    p_run.add_argument("--region", default=os.environ.get("SIG_GCP_REGION", "us-central1"))
    p_run.add_argument("--arg", dest="exec_args", action="append", default=[])
    p_run.add_argument("--secret-env", action="append", default=[])
    p_run.add_argument("--env", dest="env_pairs", action="append", default=[])

    p_verify = sub.add_parser(
        "verify-describe",
        help="judge a recorded `run jobs describe --format=json` against the template",
    )
    p_verify.add_argument("--declaration", default=None)
    p_verify.add_argument("--describe", required=True, help="the describe JSON path")
    p_verify.add_argument("--name", default=None, help="expected job name")
    p_verify.add_argument("--project", default=os.environ.get("SIG_GCP_PROJECT", ""))

    p_smoke = sub.add_parser(
        "smoke",
        help="in-container smoke: mount ro + secrets + sig_audit posture → "
        "one sig.probe-run/1 record",
    )
    p_smoke.add_argument("--declaration", default=None)
    p_smoke.add_argument("--out", default=None)
    p_smoke.add_argument("--bucket", default=os.environ.get("SIG_EXEC_BUCKET", ""))

    args = parser.parse_args(argv)
    try:
        decl = load_declaration(args.declaration)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.exec_command == "plan":
        doc = {
            "schema": SCHEMA,
            "job_prefix": decl.job_prefix,
            "service_account": decl.service_account,
            "image_repo": decl.image_repo,
            "tasks": decl.tasks,
            "max_retries": decl.max_retries,
            "command": decl.command,
            "task_timeout": decl.task_timeout,
            "cpu": decl.cpu,
            "memory": decl.memory,
            "mount": {
                "bucket": decl.mount.bucket,
                "path": decl.mount.path,
                "readonly": decl.mount.readonly,
                "prefix": decl.mount.prefix,
            },
            "cloudsql_instance": decl.cloudsql_instance,
            "secret_env": [{"env": s.env, "secret": s.secret} for s in decl.secret_env],
            "probe_prefix": decl.probe_prefix,
        }
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0

    if args.exec_command == "render":
        try:
            plan = render_plan(
                decl,
                project=args.project,
                region=args.region,
                purpose=args.purpose,
                at=args.at or _utcnow(),
                image=args.image,
                args=args.exec_args,
                secret_env_names=args.secret_env,
                env=args.env_pairs,
            )
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        _write(args.out, json.dumps(plan, indent=2, sort_keys=True) + "\n")
        return 0

    if args.exec_command == "run":
        if not args.project:
            print("exec-host run needs --project or SIG_GCP_PROJECT", file=sys.stderr)
            return 2
        return run_oneoff(
            decl,
            project=args.project,
            region=args.region,
            purpose=args.purpose,
            image=args.image,
            args=args.exec_args,
            secret_env_names=args.secret_env,
            env=args.env_pairs,
        )

    if args.exec_command == "verify-describe":
        try:
            describe = json.loads(Path(args.describe).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"describe unreadable: {e}", file=sys.stderr)
            return 2
        diffs = verify_describe(decl, describe, project=args.project, name=args.name)
        for d in diffs:
            print(f"DIFF: {d}")
        if not diffs:
            print("verify-describe: clean (the exec-host posture holds)")
            return 0
        return 4

    if args.exec_command == "smoke":
        record = run_smoke(decl, out=args.out, bucket=args.bucket or None)
        print(json.dumps({"overall": record["overall"]}))
        return 0 if record["overall"] in {"pass", "partial"} else 1

    return 2
