# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.1a live-diff — ``sig.live-diff/1`` (SIG-OPS-005, SIG-SEC-008; ADR-174).

The read-only reconciler that makes ``ops/cadence.toml`` the **scheduler of
record**: once a day (the ``[live_diff]`` trigger invokes the probe job with
its args overridden) and on demand from an operator's terminal, this module
compares the *declared* state in the repo against the *live* state in GCP and
emits a machine-readable diff plus a WORM run row:

* **declared** — ``cadence.toml`` ``[[sources]]``/``[[batches]]``/``[probes]``
  triggers and jobs, ``[[maintenance]]`` triggers (deployed/kept ``paused``,
  never enabled), ``[[manual_jobs]]`` (legitimate untriggered jobs),
  ``[[pins]]`` (bounded holds off the fleet digest), ``[fleet]`` (the newest
  committed roll record's fleet digest + per-job after_digests), ``[live_diff]``
  (this check's own trigger) and ``[[buckets]]`` (the declared bucket posture).
* **live** — Cloud Scheduler jobs, Cloud Run jobs and services, their images
  and service-account bindings, and the declared buckets' IAM / UBLA /
  versioning / lifecycle — read via ``gcloud … --format=json`` when the
  binary exists (the operator path) or the GCP REST APIs over ADC when it
  doesn't (the probe-image path). Both paths are strictly read-only; every
  fetcher is injectable for fixtures.

Drift classes are named in ``DRIFT_CLASSES``; the report is deterministic —
legs run in a fixed order and names sort inside each leg — so a fixture run
diffs byte-for-byte. Exit codes: ``0`` clean · ``1`` drift found · ``2``
usage/error (an unreadable cadence file, missing ``--from-state`` fixture, or
a live read that fails — fail-closed, never a soft pass).

SIG-OPS-005's config rule — *configuration must not require an image roll* —
is met by the **declaration bundle**: ``scheduled-ops.sh --apply`` uploads
``{"cadence_toml": …, "fleet": …}`` next to the run rows (``gs://…-sig-
restricted/ops/declared/live-diff.json``) and the in-image run reads that
published copy (``SIG_OPS_DECLARED_GCS``), so a cadence edit takes effect at
reconcile time without rebuilding the image. On an operator host the declared
side falls back to the checked-out repo files.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tomllib
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .gcs import GcsBucket, default_token_provider
from .job_roll import DIGEST_REF
from .scheduled import (
    DEFAULT_CADENCE_PATH,
    RUN_PREFIX,
    CadenceConfig,
    RunRow,
    load_cadence,
    parse_cadence_doc,
    store_run_row,
)

SCHEMA = "sig.live-diff/1"

#: Diff leg order — the emitted finding list follows this, names sorted inside.
DRIFT_CLASSES = (
    "schedule",
    "job_config",
    "image",
    "service_account",
    "secrets",
    "public_posture",
    "ubla",
    "versioning",
    "lifecycle",
)


class LiveDiffError(RuntimeError):
    """The declared side or the live read was unusable — exit 2, fail-closed."""


# ---------------------------------------------------------------------------
# Declared state — the cadence.toml side


@dataclass(frozen=True)
class DeclaredTrigger:
    """One Cloud Scheduler trigger the repo declares."""

    name: str
    cron: str
    job: str  # target Cloud Run job name
    args: str = ""  # "" → the job's baked args; else a scheduler --uri-args override
    paused: bool = False  # declared inert (maintenance rows are never enabled)
    maintenance: bool = False


@dataclass(frozen=True)
class DeclaredJob:
    """One Cloud Run job the repo declares (scheduled or manual)."""

    name: str
    image: str  # declared digest-pinned ref; "" → no expectation recorded
    sa_class: str = ""  # ops/iam_identities.toml class for this job, "" if unset
    secrets: tuple[str, ...] = ()  # "ENV=secret-name" names only
    manual: bool = False  # on the [[manual_jobs]] allow-list — no trigger expected


@dataclass(frozen=True)
class DeclaredFleet:
    """The whole repo-side expectation passed to the diff engine."""

    triggers: tuple[DeclaredTrigger, ...]
    jobs: tuple[DeclaredJob, ...]  # cadence-owned + declared-manual
    cadence_job_names: frozenset[str]  # jobs that must carry a trigger
    manual_job_names: frozenset[str]  # declared-untriggered allow-list
    services: tuple[str, ...] = ("sig-api", "sig-web")
    service_images: dict[str, str] = field(default_factory=dict)  # svc → expected ref
    buckets: tuple[Any, ...] = ()  # scheduled.BucketPosture


@dataclass(frozen=True)
class FleetImages:
    """The fleet image contract resolved off the roll record: the record's
    top-level fleet digest ref plus any per-job ``after_digest`` overrides
    (a job the roll held mid-flight records its own)."""

    fleet_ref: str = ""  # every non-pinned workload's expected image ref
    jobs: dict[str, str] = field(default_factory=dict)  # job → declared ref


def _resolve_ref(ref: str, *, project: str, ar_host: str) -> str:
    """Fill ``{project}``/``{ar_host}`` placeholders in a declared image ref."""
    return ref.format(project=project, ar_host=ar_host)


def read_roll_record(path: Path) -> FleetImages:
    """Read the newest committed roll record → the fleet image contract.

    The record is the ``sig.ops.roll-jobs/1`` JSON the last ``roll-jobs
    --record`` leg committed: ``image_digest`` is the fleet ref every job was
    rolled to; the ``jobs`` list's per-job ``after_digest`` records any job
    the roll held elsewhere.
    """
    try:
        rec = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise LiveDiffError(f"fleet.roll_record not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LiveDiffError(f"fleet.roll_record unreadable: {path}: {exc}") from exc
    jobs: dict[str, str] = {}
    for row in rec.get("jobs", []) or []:
        if not isinstance(row, dict):
            continue
        name = row.get("job") or row.get("name")
        ref = row.get("after_digest")
        if isinstance(name, str) and name and isinstance(ref, str) and ref:
            jobs[name] = ref
    fleet_ref = str(rec.get("image_digest", "") or "")
    return FleetImages(fleet_ref=fleet_ref, jobs=jobs)


def expected_image(
    name: str,
    cadence: CadenceConfig,
    fleet: FleetImages,
    *,
    project: str,
    ar_host: str,
) -> str:
    """The full image ref a declared job/service is expected to run.

    A ``[[pins]]`` row wins; then the roll record's per-job ``after_digest``;
    then the fleet ref. ``""`` when no expectation exists — that surfaces as
    ``image`` drift, never a silent pass.
    """
    for pin in cadence.pins:
        if pin.job == name or pin.service == name:
            return _resolve_ref(pin.image, project=project, ar_host=ar_host)
    return fleet.jobs.get(name, fleet.fleet_ref)


def declared_fleet(
    cadence: CadenceConfig,
    fleet: FleetImages,
    *,
    project: str,
    region: str,
) -> DeclaredFleet:
    """Build the repo-side expectation from the parsed cadence + roll record."""
    ar_host = f"{region}-docker.pkg.dev"

    triggers: list[DeclaredTrigger] = [
        DeclaredTrigger(
            name=cadence.probe_scheduler,
            cron=cadence.probe_schedule,
            job=cadence.probe_job,
        )
    ]
    jobs: dict[str, DeclaredJob] = {}

    def _expect(name: str) -> str:
        return expected_image(name, cadence, fleet, project=project, ar_host=ar_host)

    for src in cadence.sources:
        triggers.append(DeclaredTrigger(name=src.scheduler, cron=src.cron, job=src.job))
        jobs[src.job] = DeclaredJob(
            name=src.job,
            image=_expect(src.job),
            secrets=src.secrets,
        )
    for batch in cadence.batches:
        triggers.append(DeclaredTrigger(name=batch.scheduler, cron=batch.cron, job=batch.job))
        jobs[batch.job] = DeclaredJob(name=batch.job, image=_expect(batch.job))
    jobs[cadence.probe_job] = DeclaredJob(
        name=cadence.probe_job, image=_expect(cadence.probe_job), sa_class="sig-probe-rt"
    )
    for maint in cadence.maintenance:
        if not maint.scheduler:
            continue  # a queued row with no declared trigger — nothing to reconcile
        triggers.append(
            DeclaredTrigger(
                name=maint.scheduler,
                cron=maint.cron,
                job=maint.target_job or f"sig-{maint.id}",
                paused=maint.state != "enabled",
                maintenance=True,
            )
        )
    for mj in cadence.manual_jobs:
        jobs[mj.job] = DeclaredJob(
            name=mj.job,
            image=_expect(mj.job),
            sa_class=mj.sa_class,
            secrets=mj.secrets,
            manual=True,
        )
    if cadence.live_diff is not None:
        ld = cadence.live_diff
        triggers.append(DeclaredTrigger(name=ld.scheduler, cron=ld.cron, job=ld.job, args=ld.args))
    return DeclaredFleet(
        triggers=tuple(triggers),
        jobs=tuple(jobs[k] for k in sorted(jobs)),
        cadence_job_names=frozenset(
            {cadence.probe_job}
            | {s.job for s in cadence.sources}
            | {b.job for b in cadence.batches}
        ),
        manual_job_names=frozenset(m.job for m in cadence.manual_jobs),
        services=("sig-api", "sig-web"),
        service_images={svc: _expect(svc) for svc in ("sig-api", "sig-web")},
        buckets=cadence.buckets,
    )


# ---------------------------------------------------------------------------
# Lints — run before any compare; a failing declaration is fail-closed


def _cron_field_restricted(f: str) -> bool:
    """True when a cron field is restricted (not ``*`` / ``*/n`` / ``?``)."""
    f = f.strip()
    if not f or f in {"*", "?"}:
        return False
    return not f.startswith("*/")


def cron_lint(cron: str, *, annotated: str, owner: str) -> list[str]:
    """Lint one 5-field cron spec; returns violations ([] = clean).

    Rules (fail-closed — an unparseable spec is a violation, never a pass):
    * exactly five whitespace-separated fields;
    * day-of-month AND day-of-week both restricted → rejected unless the row
      carries ``cron_or_semantics_ok = "<owner>"`` — the annotation value
      names the recorded exception's owner (e.g. ``"P35.1b"``), so an
      exception is never anonymous.
    """
    fields = cron.split()
    if len(fields) != 5:
        return [f"malformed cron {cron!r}: expected 5 fields, got {len(fields)}"]
    dom, dow = fields[2], fields[4]
    problems: list[str] = []
    if _cron_field_restricted(dom) and _cron_field_restricted(dow) and not annotated:
        problems.append(
            f"{owner}: cron {cron!r} restricts day-of-month AND day-of-week — "
            "cron OR-fires on both (extra runs); annotate "
            'cron_or_semantics_ok = "<owning row>" or fix the schedule'
        )
    return problems


def lint_cadence_crons(cadence: CadenceConfig) -> list[str]:
    """Cron-lint every declared trigger row (probes, sources, batches,
    maintenance triggers, live-diff). Returns the deterministic violation list."""
    rows: list[tuple[str, str, str]] = [("[probes]", cadence.probe_schedule, "")]
    rows += [(f"sources.{s.source}", s.cron, s.cron_or_semantics_ok) for s in cadence.sources]
    rows += [(f"batches.{b.id}", b.cron, b.cron_or_semantics_ok) for b in cadence.batches]
    rows += [
        (f"maintenance.{m.id}", m.cron, m.cron_or_semantics_ok)
        for m in cadence.maintenance
        if m.scheduler  # only a row declaring a trigger is linted
    ]
    if cadence.live_diff is not None:
        rows.append(("[live_diff]", cadence.live_diff.cron, ""))
    problems: list[str] = []
    for owner, cron, annotated in rows:
        problems.extend(cron_lint(cron, annotated=annotated, owner=owner))
    return problems


def pin_lint(cadence: CadenceConfig) -> list[str]:
    """Schema lint for ``[[pins]]`` — every declared hold carries a reason and
    an expiry; a hold is never silent and never forever."""
    problems: list[str] = []
    for pin in cadence.pins:
        who = pin.job or pin.service or "<unnamed>"
        if not (pin.job or pin.service):
            problems.append("[[pins]] row names neither job nor service")
        if not pin.image or "@sha256:" not in pin.image:
            problems.append(f"pin {who}: image must be a digest-pinned ref")
        if not pin.reason:
            problems.append(f"pin {who}: missing reason — a hold is never silent")
        if not pin.expiry:
            problems.append(f"pin {who}: missing expiry — a pin is never forever")
        else:
            try:
                date.fromisoformat(pin.expiry)
            except ValueError:
                problems.append(f"pin {who}: expiry {pin.expiry!r} is not YYYY-MM-DD")
    return problems


def expired_pin_names(cadence: CadenceConfig, *, today: date | None = None) -> list[str]:
    """``[[pins]]`` rows whose expiry has passed — declared drift, fail-visible."""
    today = today or datetime.now(UTC).date()
    out = []
    for pin in cadence.pins:
        who = pin.job or pin.service or "<unnamed>"
        try:
            exp = date.fromisoformat(pin.expiry)
        except ValueError:
            continue  # malformed expiry is a pin_lint violation already
        if exp < today:
            out.append(who)
    return sorted(out)


# ---------------------------------------------------------------------------
# Live state — gcloud JSON or REST reads, both injectable

GcloudRunner = Callable[..., Any]
Opener = Callable[[str], Any]
TokenProvider = Callable[[], str | None]


@dataclass
class LiveState:
    """The live side, shaped like the fixture bundle.

    ``jobs``/``services`` values are decoded ``gcloud … describe --format=json``
    (v1) or REST v2 bodies — the normalisers read either shape. ``buckets``
    values are ``{"iam": <policy>, "info": <bucket>}`` pairs.
    """

    schedulers: dict[str, dict] = field(default_factory=dict)
    jobs: dict[str, dict] = field(default_factory=dict)
    services: dict[str, dict] = field(default_factory=dict)
    buckets: dict[str, dict] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def load_state_source(source: str) -> LiveState:
    """Load a live-state bundle from a ``--from-state`` path.

    Two shapes: a single JSON file holding the bundle, or a directory holding
    ``schedulers.json`` / ``jobs.json`` / ``services.json`` / ``buckets.json``
    (any subset — a missing file is an empty map; every map may be a
    ``{name: body}`` object or a list of bodies with ``name`` fields).
    """

    def _named(raw: Any, key: str) -> dict[str, dict]:
        if isinstance(raw, dict):
            return {str(k): v for k, v in raw.items()}
        if isinstance(raw, list):
            named: dict[str, dict] = {}
            for body in raw:
                if not isinstance(body, dict):
                    continue
                name = str(
                    body.get("name") or (body.get("metadata", {}) or {}).get("name") or ""
                ).rsplit("/", 1)[-1]
                if name:
                    named[name] = body
            return named
        raise LiveDiffError(f"--from-state `{key}` must be an object or list")

    def _bundle(raw: Any) -> LiveState:
        if not isinstance(raw, dict):
            raise LiveDiffError(f"--from-state bundle must be a JSON object: {source}")
        return LiveState(
            schedulers=_named(raw.get("schedulers", {}), "schedulers"),
            jobs=_named(raw.get("jobs", {}), "jobs"),
            services=_named(raw.get("services", {}), "services"),
            buckets=(
                {str(k): v for k, v in raw["buckets"].items()}
                if isinstance(raw.get("buckets"), dict)
                else {}
            ),
            errors=[str(e) for e in raw.get("errors", []) or []],
        )

    p = Path(source)
    if not p.exists():
        raise LiveDiffError(f"--from-state not found: {source}")
    if p.is_file():
        try:
            return _bundle(json.loads(p.read_text()))
        except json.JSONDecodeError as exc:
            raise LiveDiffError(f"--from-state unreadable JSON: {source}: {exc}") from exc
    raw: dict[str, Any] = {}
    for key in ("schedulers", "jobs", "services", "buckets", "errors"):
        f = p / f"{key}.json"
        if f.exists():
            try:
                raw[key] = json.loads(f.read_text())
            except json.JSONDecodeError as exc:
                raise LiveDiffError(f"--from-state unreadable JSON: {f}: {exc}") from exc
    return _bundle(raw)


def gcloud_json_runner(*, timeout: int = 120) -> GcloudRunner:
    """A ``gcloud … --format=json`` runner → decoded body; raises on failure."""

    def run(*argv: str) -> Any:
        try:
            proc = subprocess.run(
                ["gcloud", *argv, "--format=json"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LiveDiffError(f"gcloud {' '.join(argv[:3])} failed: {exc}") from exc
        if proc.returncode != 0:
            raise LiveDiffError(
                f"gcloud {' '.join(argv[:3])} exited {proc.returncode}: {proc.stderr.strip()[:300]}"
            )
        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise LiveDiffError(f"gcloud {' '.join(argv[:3])} returned non-JSON output") from exc

    return run


def rest_json_opener(*, token: TokenProvider | None = None) -> Opener:
    """A URL→JSON opener that GETs a GCP REST endpoint with an ADC-token
    (``ops.gcs.default_token_provider``: env override → metadata server →
    gcloud ADC). A missing token fails closed."""
    provider = token or default_token_provider

    def open_json(url: str) -> Any:
        tok = provider()
        if not tok:
            raise LiveDiffError(
                "no GCP access token (metadata server + gcloud ADC + "
                "SIG_GCS_ACCESS_TOKEN all absent) — the live read cannot run"
            )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                return json.loads(resp.read().decode())
        except LiveDiffError:
            raise
        except Exception as exc:
            raise LiveDiffError(f"GET {url} failed: {exc}") from exc

    return open_json


def _short_name(body: Mapping[str, Any]) -> str:
    return str(body.get("name", "")).rsplit("/", 1)[-1]


def fetch_live(
    *,
    project: str,
    region: str,
    bucket_names: Sequence[str],
    gcloud: GcloudRunner | None = None,
    opener: Opener | None = None,
) -> LiveState:
    """Read the live side. Prefers the ``gcloud`` runner (operator path); falls
    back to REST (probe-image path). A failed read raises ``LiveDiffError`` —
    the run records an error row, never a fabricated clean pass."""
    state = LiveState()
    if gcloud is not None:
        for body in (
            gcloud("scheduler", "jobs", "list", "--location", region, "--project", project) or []
        ):
            name = _short_name(body)
            if name:
                state.schedulers[name] = body
        for body in gcloud("run", "jobs", "list", "--region", region, "--project", project) or []:
            meta = body.get("metadata", body) if isinstance(body, dict) else {}
            name = str(meta.get("name", ""))
            if name:
                state.jobs[name] = body
        for body in (
            gcloud("run", "services", "list", "--region", region, "--project", project) or []
        ):
            meta = body.get("metadata", body) if isinstance(body, dict) else {}
            name = str(meta.get("name", ""))
            if name:
                state.services[name] = body
        for b in bucket_names:
            iam = gcloud("storage", "buckets", "get-iam-policy", f"gs://{b}")
            info = gcloud("storage", "buckets", "describe", f"gs://{b}")
            state.buckets[b] = {"iam": iam, "info": info}
        return state

    if opener is None:
        raise LiveDiffError("no live fetcher: neither gcloud runner nor REST opener")
    scheds = opener(
        "https://cloudscheduler.googleapis.com/v1/"
        f"projects/{project}/locations/{region}/jobs?pageSize=500"
    )
    for body in scheds.get("jobs", []):
        name = _short_name(body)
        if name:
            state.schedulers[name] = body
    jobs = opener(
        f"https://run.googleapis.com/v2/projects/{project}/locations/{region}/jobs?pageSize=500"
    )
    for body in jobs.get("jobs", []):
        name = _short_name(body)
        if name:
            state.jobs[name] = body
    svcs = opener(
        f"https://run.googleapis.com/v2/projects/{project}/locations/{region}/services?pageSize=100"
    )
    for body in svcs.get("services", []):
        name = _short_name(body)
        if name:
            state.services[name] = body
    for b in bucket_names:
        iam = opener(f"https://storage.googleapis.com/storage/v1/b/{b}/iam")
        info = opener(f"https://storage.googleapis.com/storage/v1/b/{b}")
        state.buckets[b] = {"iam": iam, "info": info}
    return state


# ---------------------------------------------------------------------------
# Normalisation — live bodies → comparable fields


def _container_specs(body: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Pull the container spec list out of either the gcloud v1 describe shape
    or the REST v2 shape."""
    for path in (
        ("spec", "template", "spec", "template", "spec", "containers"),  # v1 job
        ("spec", "template", "spec", "containers"),  # v1 service
        ("template", "template", "containers"),  # REST v2 job
        ("template", "containers"),  # REST v2 service
    ):
        node: Any = body
        for key in path:
            node = node.get(key, {}) if isinstance(node, Mapping) else {}
        if isinstance(node, list) and node:
            return [c for c in node if isinstance(c, Mapping)]
    return []


def live_image(body: Mapping[str, Any]) -> str:
    for spec in _container_specs(body):
        img = spec.get("image")
        if img:
            return str(img)
    return ""


def live_service_account(body: Mapping[str, Any]) -> str:
    """The runtime SA on a job/service — v1 describe or v2 REST shape."""
    for path in (
        ("spec", "template", "spec", "template", "spec", "serviceAccountName"),
        ("template", "template", "serviceAccount"),
        ("template", "serviceAccount"),
    ):
        node: Any = body
        for key in path:
            node = node.get(key, {}) if isinstance(node, Mapping) else {}
        if isinstance(node, str) and node:
            return node
    return ""


def live_secret_names(body: Mapping[str, Any]) -> set[str]:
    """Secret-Manager secret names bound to the job's containers (names only)."""
    names: set[str] = set()
    for spec in _container_specs(body):
        for env in spec.get("env", []) or []:
            src = (
                env.get("valueSource")  # REST v2
                or env.get("value_source")
                or env.get("valueFrom")  # gcloud v1 describe
                or env.get("value_from")
                or {}
            )
            sec = src.get("secretKeyRef") or src.get("secret_key_ref") or {}
            secret = sec.get("secret") or sec.get("name")  # v2 / v1 field names
            if secret:
                names.add(str(secret).rsplit("/", 1)[-1])
    return names


def live_scheduler_fields(body: Mapping[str, Any]) -> dict[str, str]:
    """Normalise a Cloud Scheduler job body → {schedule, job, args, state}.

    ``job`` is the invoked Cloud Run job name parsed out of the ``:run`` URI
    ("" when the target isn't a Cloud Run job). ``args`` is the args-override
    the trigger's POST body carries — ``httpTarget.body`` decodes (base64 in
    API responses, plain JSON in describe output) as a RunJobRequest whose
    ``overrides.containerOverrides[].args`` replace the job's baked args;
    emitted as canonical JSON for the declared compare.
    """
    schedule = str(body.get("schedule", ""))
    state = str(body.get("state", "ENABLED")).upper()
    http = body.get("httpTarget", {}) or {}
    uri = str(http.get("uri", ""))
    raw_body = http.get("body", "")
    args = ""
    if raw_body:
        decoded: Any = None
        try:
            decoded = json.loads(base64.b64decode(str(raw_body)).decode())
        except Exception:
            try:
                decoded = json.loads(str(raw_body))
            except Exception:
                decoded = None
        if isinstance(decoded, dict):
            overrides = decoded.get("overrides", {}) or {}
            containers = overrides.get("containerOverrides", []) or []
            if containers and isinstance(containers[0], dict):
                a = containers[0].get("args")
                if isinstance(a, list):
                    args = json.dumps([str(x) for x in a])
    m = re.search(r"/jobs/([^/:]+):run", uri)
    return {
        "schedule": schedule,
        "job": m.group(1) if m else "",
        "args": args,
        "state": state,
    }


def _bucket_iam_members(iam: Mapping[str, Any], role: str) -> set[str]:
    members: set[str] = set()
    for b in iam.get("bindings", []) or []:
        if b.get("role") == role:
            members.update(str(m) for m in b.get("members", []) or [])
    return members


def _bucket_is_public(iam: Mapping[str, Any]) -> bool:
    return "allUsers" in _bucket_iam_members(
        iam, "roles/storage.objectViewer"
    ) or "allUsers" in _bucket_iam_members(iam, "roles/storage.legacyObjectReader")


def _bucket_info_fields(info: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise a bucket describe/REST body → {ubla, versioning, noncurrent}."""
    iam_cfg = info.get("iamConfiguration", {}) or {}
    ubla = iam_cfg.get("uniformBucketLevelAccess", {}) or {}
    versioning = info.get("versioning", {}) or {}
    noncurrent: int | None = None
    for rule in (info.get("lifecycle", {}) or {}).get("rule", []) or []:
        action = rule.get("action", {}) or {}
        cond = rule.get("condition", {}) or {}
        if action.get("type") == "Delete" and "daysSinceNoncurrentTime" in cond:
            noncurrent = int(cond["daysSinceNoncurrentTime"])
    return {
        "ubla": bool(ubla.get("enabled", False)),
        "versioning": bool(versioning.get("enabled", False)),
        "noncurrent": noncurrent,
    }


# ---------------------------------------------------------------------------
# The diff engine


@dataclass(frozen=True)
class Finding:
    cls: str
    name: str
    detail: str


@dataclass
class DiffReport:
    """The emitted result — findings plus the per-leg checked counts."""

    findings: list[Finding] = field(default_factory=list)
    checked_triggers: int = 0
    checked_jobs: int = 0
    checked_services: int = 0
    checked_buckets: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def drift(self) -> bool:
        return bool(self.findings or self.errors)

    def add(self, cls: str, name: str, detail: str) -> None:
        self.findings.append(Finding(cls, name, detail))

    def ordered(self) -> list[Finding]:
        order = {c: i for i, c in enumerate(DRIFT_CLASSES)}
        return sorted(self.findings, key=lambda f: (order.get(f.cls, 99), f.name, f.detail))

    def text(self) -> str:
        lines = [f"{f.cls} {f.name}: {f.detail}" for f in self.ordered()]
        lines += [f"error: {e}" for e in self.errors]
        return "\n".join(lines)


def _digest_of(ref: str) -> str:
    m = re.search(r"@sha256:([0-9a-f]{64})$", ref)
    return m.group(1) if m else ""


def _check_image(name: str, live_ref: str, declared_ref: str, report: DiffReport) -> None:
    """The SIG-SEC-008 leg: digest-pin + declared-digest match."""
    if not live_ref:
        report.add("image", name, "no container image readable on the live spec")
        return
    if not DIGEST_REF.match(live_ref):
        report.add(
            "image",
            name,
            f"live image {live_ref!r} is not a digest-pinned Artifact Registry ref",
        )
        return
    if not declared_ref:
        report.add(
            "image",
            name,
            "no declared image (not on the fleet roll record and no [[pins]] row)",
        )
        return
    live_d, decl_d = _digest_of(live_ref), _digest_of(declared_ref)
    if live_d and decl_d and live_d != decl_d:
        report.add(
            "image",
            name,
            f"live sha256:{live_d[:12]}… != declared sha256:{decl_d[:12]}…",
        )


def _check_trigger(live: Mapping[str, str], declared: DeclaredTrigger, report: DiffReport) -> None:
    if live["schedule"] != declared.cron:
        report.add(
            "schedule",
            declared.name,
            f"cron live={live['schedule']!r} declared={declared.cron!r}",
        )
    if declared.maintenance:
        if live["state"] == "ENABLED":
            report.add(
                "schedule",
                declared.name,
                "maintenance trigger is ENABLED live — declared paused; a "
                "maintenance row is never enabled by the reconcile",
            )
        elif live["state"] != "PAUSED":
            report.add(
                "schedule",
                declared.name,
                f"maintenance trigger state={live['state']!r} (declared paused)",
            )
    elif live["state"] == "PAUSED":
        report.add(
            "schedule",
            declared.name,
            "trigger is PAUSED live but declared enabled",
        )
    if declared.args:
        # Declared args are a JSON array (the containerOverrides payload);
        # compare parsed so whitespace never false-fires.
        try:
            declared_args = json.loads(declared.args)
        except json.JSONDecodeError:
            declared_args = declared.args
        try:
            live_args = json.loads(live["args"]) if live["args"] else None
        except json.JSONDecodeError:
            live_args = live["args"]
        if live_args != declared_args:
            report.add(
                "schedule",
                declared.name,
                f"args override live={live['args']!r} declared={declared.args!r}",
            )
    if live["job"] and declared.job and live["job"] != declared.job:
        report.add(
            "schedule",
            declared.name,
            f"invokes job {live['job']!r} live; declared {declared.job!r}",
        )


def diff(
    declared: DeclaredFleet,
    live: LiveState,
    *,
    expired_pins: Sequence[str] = (),
) -> DiffReport:
    """Compare declared vs live → the deterministic drift report."""
    report = DiffReport(errors=list(live.errors))

    live_trigs = {name: live_scheduler_fields(body) for name, body in live.schedulers.items()}
    declared_names = {t.name for t in declared.triggers}
    for t in declared.triggers:
        report.checked_triggers += 1
        live_t = live_trigs.get(t.name)
        if live_t is None:
            report.add("schedule", t.name, "missing live — declared trigger not deployed")
            continue
        _check_trigger(live_t, t, report)
    for name in sorted(set(live_trigs) - declared_names):
        report.add(
            "schedule",
            name,
            "live trigger not declared in cadence.toml — drift or cruft",
        )

    declared_job_names = {j.name for j in declared.jobs}
    for j in declared.jobs:
        report.checked_jobs += 1
        body = live.jobs.get(j.name)
        if body is None:
            report.add("job_config", j.name, "missing live — declared job not deployed")
            continue
        _check_image(j.name, live_image(body), j.image, report)
        live_sa = live_service_account(body)
        if j.sa_class and not live_sa:
            report.add(
                "service_account",
                j.name,
                f"declared sa_class {j.sa_class!r} but no runtime SA bound live",
            )
        declared_secrets = {s.split("=", 1)[-1] for s in j.secrets}
        for sec in sorted(declared_secrets - live_secret_names(body)):
            report.add("secrets", j.name, f"declared secret binding {sec!r} absent live")
    for name in sorted(set(live.jobs) - declared_job_names):
        report.add(
            "job_config",
            name,
            "live job neither cadence-owned nor on [[manual_jobs]] — "
            "unlisted drift (fleet hygiene owns the disposition)",
        )

    for svc in declared.services:
        report.checked_services += 1
        body = live.services.get(svc)
        if body is None:
            report.add("job_config", svc, "declared service missing live")
            continue
        _check_image(svc, live_image(body), declared.service_images.get(svc, ""), report)

    for expired in expired_pins:
        report.add("image", expired, "[[pins]] expiry passed — re-declare or sweep the hold")

    for spec in declared.buckets:
        report.checked_buckets += 1
        match = next((n for n in live.buckets if n.endswith(spec.suffix)), None)
        entry = live.buckets.get(match) if match else None
        if entry is None:
            report.add(
                "job_config",
                f"bucket:{spec.suffix}",
                "declared bucket unreadable/missing live",
            )
            continue
        iam = entry.get("iam", {})
        info = _bucket_info_fields(entry.get("info", {}))
        full = match or spec.suffix
        if spec.public is not None:
            is_pub = _bucket_is_public(iam)
            if is_pub != spec.public:
                report.add(
                    "public_posture",
                    full,
                    f"allUsers object access live={is_pub} declared={spec.public}",
                )
        if spec.ubla is not None and info["ubla"] != spec.ubla:
            report.add(
                "ubla",
                full,
                f"uniform bucket-level access live={info['ubla']} declared={spec.ubla}",
            )
        if spec.versioning is not None and info["versioning"] != spec.versioning:
            report.add(
                "versioning",
                full,
                f"versioning live={info['versioning']} declared={spec.versioning}",
            )
        if spec.noncurrent_days is not None and info["noncurrent"] != spec.noncurrent_days:
            report.add(
                "lifecycle",
                full,
                f"noncurrent-days live={info['noncurrent']} declared={spec.noncurrent_days}",
            )
    return report


# ---------------------------------------------------------------------------
# The declared-side loader — repo files or the published declaration bundle


@dataclass(frozen=True)
class DeclaredSource:
    """Where the declared side came from plus the parsed payload."""

    cadence: CadenceConfig
    fleet: FleetImages
    cadence_sha256: str
    provenance: str  # "repo" | path | gs:// URI


def _read_bundle_bytes(source: str, *, bucket_factory: Callable[[str], GcsBucket]) -> bytes:
    """Read a declaration bundle from a local path or a ``gs://`` URI."""
    if source.startswith("gs://"):
        bucket, _, name = source[5:].partition("/")
        return bucket_factory(bucket).get_object(name)
    return Path(source).read_bytes()


def load_declared(
    *,
    declared_source: str | None = None,
    cadence_file: str | None = None,
    repo_root: Path | None = None,
    bucket_factory: Callable[[str], GcsBucket] = GcsBucket,
) -> DeclaredSource:
    """Resolve the declared side.

    Order: explicit ``--declared`` → ``$SIG_OPS_DECLARED_GCS`` (the bundle the
    reconcile publishes — the in-image path, no image roll for config) → the
    checked-out repo files (``ops/cadence.toml`` + ``[fleet].roll_record``).
    """
    source = declared_source or os.environ.get("SIG_OPS_DECLARED_GCS", "").strip()
    if source:
        try:
            bundle = json.loads(_read_bundle_bytes(source, bucket_factory=bucket_factory))
        except Exception as exc:  # noqa: BLE001 - any read failure fails closed
            raise LiveDiffError(f"declaration bundle unreadable ({source}): {exc}") from exc
        if not isinstance(bundle, dict) or "cadence_toml" not in bundle:
            raise LiveDiffError(f"declaration bundle at {source} has no `cadence_toml` member")
        try:
            cadence = parse_cadence_doc(tomllib.loads(bundle["cadence_toml"]))
        except (tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
            raise LiveDiffError(
                f"declaration bundle cadence unparseable ({source}): {exc}"
            ) from exc
        fleet_raw = bundle.get("fleet", {}) or {}
        fleet = FleetImages(
            fleet_ref=str(fleet_raw.get("fleet_ref", "")),
            jobs={str(k): str(v) for k, v in (fleet_raw.get("jobs") or {}).items()},
        )
        sha = (
            str(bundle.get("cadence_sha256", ""))
            or hashlib.sha256(bundle["cadence_toml"].encode()).hexdigest()
        )
        return DeclaredSource(cadence=cadence, fleet=fleet, cadence_sha256=sha, provenance=source)

    try:
        cadence = load_cadence(cadence_file) if cadence_file else load_cadence()
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise LiveDiffError(f"cadence unreadable: {exc}") from exc
    root = repo_root or DEFAULT_CADENCE_PATH.resolve().parents[1]
    fleet = FleetImages()
    if cadence.fleet.roll_record:
        fleet = read_roll_record(root / cadence.fleet.roll_record)
    cadence_path = root / "ops" / "cadence.toml"
    try:
        sha = hashlib.sha256(cadence_path.read_bytes()).hexdigest()
    except OSError:
        sha = ""
    return DeclaredSource(cadence=cadence, fleet=fleet, cadence_sha256=sha, provenance="repo")


def build_declared_bundle(
    cadence: CadenceConfig, *, repo_root: Path | None = None
) -> dict[str, Any]:
    """The JSON the reconcile publishes to ``ops/declared/live-diff.json`` —
    cadence text + resolved fleet images + the cadence content hash. The
    in-image run reads THIS object, so a cadence change takes effect at the
    next reconcile without an image roll (SIG-OPS-005).
    """
    root = repo_root or DEFAULT_CADENCE_PATH.resolve().parents[1]
    cadence_path = root / "ops" / "cadence.toml"
    text = cadence_path.read_text()
    fleet = (
        read_roll_record(root / cadence.fleet.roll_record)
        if cadence.fleet.roll_record
        else FleetImages()
    )
    return {
        "schema": f"{SCHEMA}-declared",
        "cadence_toml": text,
        "cadence_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "fleet": {"fleet_ref": fleet.fleet_ref, "jobs": fleet.jobs},
        "generated_by": "ops/gcp/scheduled-ops.sh --apply (P35.1a)",
    }


# ---------------------------------------------------------------------------
# The run record — one WORM row per execution (ops/runs/_live-diff/…)


def run_record(
    *,
    report: DiffReport,
    mode: str,
    project: str,
    region: str,
    cadence_sha: str,
    provenance: str,
    started_at: str,
    duration_seconds: float,
) -> RunRow:
    """Shape the diff into the standard scheduled-ops run row; the
    ``sig.live-diff/1`` payload rides in ``fetch_record``."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": mode,  # "live" | "from-state"
        "project": project,
        "region": region,
        "declared_provenance": provenance,
        "cadence_sha256": cadence_sha,
        "triggers_checked": report.checked_triggers,
        "jobs_checked": report.checked_jobs,
        "services_checked": report.checked_services,
        "buckets_checked": report.checked_buckets,
        "drift_classes": sorted({f.cls for f in report.findings}),
        "findings": [
            {"class": f.cls, "name": f.name, "detail": f.detail} for f in report.ordered()
        ],
        "errors": list(report.errors),
    }
    return RunRow(
        kind="live-diff",
        source="_live-diff",
        mode=mode,
        outcome="drift" if report.drift else "ok",
        exit_code=1 if report.drift else 0,
        started_at=started_at,
        duration_seconds=duration_seconds,
        detail=(f"{len(report.findings)} finding(s), {len(report.errors)} error(s)"),
        fetch_record=payload,
    )


# ---------------------------------------------------------------------------
# The top-level entry used by the CLI


def execute(
    *,
    mode: str,
    declared_source: str | None = None,
    cadence_file: str | None = None,
    state_source: str | None = None,
    project: str | None = None,
    region: str = "us-central1",
    repo_root: Path | None = None,
    gcloud: GcloudRunner | None = None,
    opener: Opener | None = None,
    bucket_factory: Callable[[str], GcsBucket] = GcsBucket,
    today: date | None = None,
    now: datetime | None = None,
) -> tuple[RunRow, int]:
    """Run one diff → (run row, exit code). Raises ``LiveDiffError`` → exit 2."""
    project = project or os.environ.get("SIG_GCP_PROJECT", "").strip()
    if not project:
        raise LiveDiffError("no project: pass --project or set SIG_GCP_PROJECT")
    t0 = datetime.now(UTC)
    started = t0.isoformat()

    declared = load_declared(
        declared_source=declared_source,
        cadence_file=cadence_file,
        repo_root=repo_root,
        bucket_factory=bucket_factory,
    )
    cadence = declared.cadence
    lint = lint_cadence_crons(cadence) + pin_lint(cadence)
    if lint:
        raise LiveDiffError("cadence lint failed:\n  " + "\n  ".join(lint))
    ar_host = f"{region}-docker.pkg.dev"
    fleet = declared.fleet
    # Resolve placeholder refs in the record's fleet ref when it carries them.
    fleet = FleetImages(
        fleet_ref=_resolve_ref(fleet.fleet_ref, project=project, ar_host=ar_host),
        jobs={k: _resolve_ref(v, project=project, ar_host=ar_host) for k, v in fleet.jobs.items()},
    )
    declared_side = declared_fleet(cadence, fleet, project=project, region=region)
    bucket_names = [f"{project}-{b.suffix}" for b in cadence.buckets]

    if mode == "from-state":
        if not state_source:
            raise LiveDiffError("--from-state requires a state fixture path")
        live = load_state_source(state_source)
    else:
        runner = gcloud
        if runner is None and opener is None:
            try:
                subprocess.run(
                    ["gcloud", "--version"],
                    capture_output=True,
                    timeout=15,
                    check=True,
                )
                runner = gcloud_json_runner()
            except Exception:
                opener = rest_json_opener()
        live = fetch_live(
            project=project,
            region=region,
            bucket_names=bucket_names,
            gcloud=runner,
            opener=opener,
        )

    report = diff(
        declared_side,
        live,
        expired_pins=expired_pin_names(cadence, today=today),
    )
    row = run_record(
        report=report,
        mode=mode,
        project=project,
        region=region,
        cadence_sha=declared.cadence_sha256,
        provenance=declared.provenance,
        started_at=started,
        duration_seconds=(datetime.now(UTC) - t0).total_seconds(),
    )
    return row, (1 if report.drift else 0)


def upload_run_row(
    row: RunRow,
    cadence: CadenceConfig,
    *,
    gcs: GcsBucket | None = None,
    local_dir: Path | None = None,
) -> dict[str, str]:
    """Persist the run row (``store_run_row`` semantics): local mirror first,
    then the per-run timestamped GCS object under ``ops/runs/_live-diff/``.
    A GCS failure raises GcsError — the caller fails loud rather than losing
    the audit row."""
    return store_run_row(
        row,
        prefix=cadence.runs_gcs_prefix or RUN_PREFIX,
        gcs=gcs,
        local_dir=local_dir,
    )


__all__ = [
    "DRIFT_CLASSES",
    "DeclaredFleet",
    "DeclaredJob",
    "DeclaredSource",
    "DeclaredTrigger",
    "DiffReport",
    "Finding",
    "FleetImages",
    "LiveDiffError",
    "LiveState",
    "SCHEMA",
    "build_declared_bundle",
    "cron_lint",
    "declared_fleet",
    "diff",
    "execute",
    "expired_pin_names",
    "expected_image",
    "fetch_live",
    "gcloud_json_runner",
    "lint_cadence_crons",
    "load_declared",
    "load_state_source",
    "pin_lint",
    "read_roll_record",
    "rest_json_opener",
    "run_record",
    "upload_run_row",
]
