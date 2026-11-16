# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""intake_operation — the P37.59 dark ``sig-intake`` receiver service and its
operating posture declarations (G2-activation step 6 / ACT-23, D-P32.16-1).

The anonymous correction receiver ships **dark**: Q-27/OD-08 [B-8] answered
*"Email, no time promises"* — intake is e-mail-only and the receiver is
deployed but never exposed. This module is the single committed source for
the shape the windowed leg runner (``ops/gcp/intake-roll.sh``) plans, applies
and verifies:

* ``SERVICE`` — the Cloud Run service spec. ``SIG_INTAKE_ENABLED=1`` mounts
  the surface so it answers the honest ``503 receiver_not_operating``; the
  armed kill-switch ``SIG_INTAKE_OPERATIONAL`` is **never** set by the
  deploy — accepting reports stays the exposure path's flip, gated on
  ``[intake].operational`` + a named owner + ``staffed`` (D-P32.16-1, all
  operator acts). ``--no-allow-unauthenticated`` + ``internal`` ingress mean
  the service answers nothing off the GCP internal path — loopback only, no
  exposure; the ``/intake/*`` LB rule in ``ops/lb_routes.toml`` stays
  ``enabled = false`` regardless.
* ``LOG_EXCLUSIONS`` — the infra-side identifier-retention exclusions the
  packet's §7/§13 privacy claims require: a ``_Default``-sink exclusion
  dropping only the receiver's Cloud Run **request** logs (the
  ``run.googleapis.com/requests`` stream is the one that carries IP+UA in
  ``httpRequest`` fields); the app's own stdout/stderr — receipt ids only,
  by construction — stays logged. LB logging is declared off for the
  (still nonexistent) ``sig-intake-backend``.
* ``SECRETS`` — the three Secret Manager *names* the service mounts as env
  (never values, HG-09): the receiver DB-login credential plus the two
  operational-gate secrets. A missing version queues the deploy leg
  (exit 42) — the declared shape is applied whole or not at all.
* ``INFRA_POSTURE`` — the recorded disclosures the packet's "no durable
  network identifiers" claim needs outside app control: the monthly
  full-database logical export (``ops/gcp/logical-export.sh``, private
  ``pg/monthly/*``, 100-day lifecycle) and automated backups carry the
  intake schema — disclosed, retention-bounded, never "no copies".

The two DB logins the receiver/reviewer roles grant to are declared in
``ops/src/ops/db_logins.py`` (``SIG_INTAKE_RECEIVER_LOGIN`` /
``SIG_INTAKE_REVIEWER_LOGIN``) — the same catalog-only machinery P34.43
built; the dedicated runtime SA ``sig-intake-rt`` is declared in
``ops/iam_identities.toml``.

CLI: ``sig-ops intake-op plan`` prints this declaration (offline); the leg
runner is ``ops/gcp/intake-roll.sh`` (check/apply/verify — the named
mutation, OM-20 pre-authorised at GATE-G6 §4, executed only under
``live_verification=true`` in this dispatch shape).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field

#: The dedicated least-privilege runtime identity (AR-8), declared in
#: ``ops/iam_identities.toml`` — created by the leg's ``sa`` action.
INTAKE_SA = "sig-intake-rt"

#: The Cloud Run service name — the same name ``ops/lb_routes.toml``'s
#: written-not-applied ``/intake/*`` rule and ``ops/gcp/config.sh`` export.
INTAKE_SERVICE = "sig-intake"

#: The image the dark deploy pins: the serving ``sig-api`` revision's own
#: digest, read back at apply time (the receiver is the same codebase/image
#: — ``ops/Dockerfile``). Deploying the already-verified serving image is
#: stronger than re-resolving a tag and never deploys ``:latest`` (ADR-111).
INTAKE_IMAGE_SOURCE_SERVICE = "sig-api"

#: The env vars the deploy sets (non-secret). ``SIG_INTAKE_ENABLED=1`` mounts
#: the receiver surface so the service answers the honest
#: ``503 receiver_not_operating`` — the "ready" state the dark launch wants.
#: ``SIG_INTAKE_OPERATIONAL`` is *deliberately absent*: it is the armed
#: kill-switch and the deploy never arms it — flipping it is the exposure
#: path's act, not this one's.
SERVICE_ENV: dict[str, str] = {
    "SIG_INTAKE_ENABLED": "1",
    "SIG_PG_DB": "sig",
}

#: Secret Manager *names* → the env var the service mounts them as (HG-09 —
#: names only, never values). ``SIG_INTAKE_DB_PASSWORD`` is the receiver
#: DB-login credential the command's DSN assembly reads; the FORM/ABUSE pair
#: are the operational-gate secrets (mounted dark: harmless while
#: ``operational=false``, present so the declared revision is the operating
#: shape minus the kill-switch alone).
SECRET_ENV: dict[str, str] = {
    "SIG_INTAKE_DB_PASSWORD": "sig-intake-receiver-password",
    "SIG_INTAKE_FORM_SECRET": "sig-intake-form-secret",
    "SIG_INTAKE_ABUSE_SECRET": "sig-intake-abuse-secret",
}

#: The container entrypoint override. The same ``sh -c`` env-assembly idiom
#: as the image CMD: the DSN's password arrives only via the mounted
#: ``$SIG_INTAKE_DB_PASSWORD`` (HG-09) and ``$SIG_CLOUDSQL_CONNECTION`` names
#: the mounted socket — no credential is ever an argv literal or a file.
SERVICE_COMMAND = "sh"
SERVICE_ARGS = (
    "-c",
    "exec sig-api serve-intake --host 0.0.0.0 --port ${PORT:-8080} "
    '--dsn "postgresql://sig_intake_receiver_login:${SIG_INTAKE_DB_PASSWORD}'
    '@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}" '
    "--ops-config /app/ops/config.toml",
)

#: Ingress posture — ``internal`` admits only GCP-internal paths (VPC + the
#: project's external HTTPS LB). No LB path rule exists for ``/intake/*``
#: (``enabled = false`` in ``ops/lb_routes.toml``), so the service answers
#: nothing off the internal path — the "loopback only, no exposure" shape
#: the named mutation declares.
SERVICE_INGRESS = "internal"


@dataclass(frozen=True)
class LogExclusion:
    """One ``_Default``-sink exclusion (G1 NEW-4): drop only the named
    stream — never a whole-service blackout that would also eat the app's
    own receipt-id logs."""

    name: str
    sink: str
    filter: str
    reason: str


#: The receiver's Cloud Run *request* log carries the caller's network
#: identifiers (``httpRequest.remoteIp``, the user-agent) outside app
#: control — the one infra stream the packet's "no durable network
#: identifiers" claim needs excluded. App stdout/stderr (receipt ids only)
#: stays: the ``log_id`` clause keeps the exclusion scoped to exactly the
#: requests stream.
LOG_EXCLUSIONS: tuple[LogExclusion, ...] = (
    LogExclusion(
        name="sig-intake-request-logs",
        sink="_Default",
        filter=(
            'resource.type="cloud_run_revision" AND '
            'resource.labels.service_name="sig-intake" AND '
            'log_id("run.googleapis.com/requests")'
        ),
        reason=(
            "the requests stream carries caller IP + user-agent in "
            "httpRequest fields — excluded so no durable network identifier "
            "for the receiver exists in platform logs (packet §13)"
        ),
    ),
)

#: The (still nonexistent) backend service's logging posture — declared off.
#: ``sig-intake-backend`` is created only when the LB rule flips on (the
#: exposure path, never this row); the declaration pins the posture now so a
#: later apply cannot ship a default-on log config silently.
INTAKE_BACKEND = "sig-intake-backend"
LB_LOGGING_ENABLED = False

#: Recorded infra disclosures — the privacy claim's "outside app control"
#: half the packet records (§7 → §13): the intake schema rides the monthly
#: full-database export and managed backups under their own retention
#: lifecycles; the honest text says bounded copies, never "no copies".
INFRA_POSTURE: tuple[str, ...] = (
    "monthly gcloud sql export (ops/gcp/logical-export.sh): full-database "
    "`sig` export incl. the intake schema → gs://<p>-sig-backups/pg/monthly/*, "
    "private, object lifecycle Delete at 100 days",
    "Cloud SQL automated backups/PITR (≤7-day window disclosed): intake rows "
    "expire with the instance backup schedule; the receiver retention "
    "schedule applies to live rows, backup expiry is the operator's policy",
    "LB/proxy request logs for the receiver: none exist — the /intake/* URL-map "
    "rule is enabled=false and sig-intake-backend declares logConfig off",
)


@dataclass(frozen=True)
class DarkService:
    """The ``sig-intake`` Cloud Run service spec the leg plans/applies."""

    name: str = INTAKE_SERVICE
    service_account: str = INTAKE_SA
    image_source_service: str = INTAKE_IMAGE_SOURCE_SERVICE
    env: dict[str, str] = field(default_factory=lambda: dict(SERVICE_ENV))
    secret_env: dict[str, str] = field(default_factory=lambda: dict(SECRET_ENV))
    allow_unauthenticated: bool = False
    ingress: str = SERVICE_INGRESS
    min_instances: int = 0
    max_instances: int = 2
    port: int = 8080
    command: tuple[str, ...] = (SERVICE_COMMAND,)
    args: tuple[str, ...] = SERVICE_ARGS
    # Deliberately absent from env — the armed kill-switch (see module doc).
    never_env: tuple[str, ...] = ("SIG_INTAKE_OPERATIONAL",)


SERVICE = DarkService()


def plan() -> dict[str, object]:
    """The committed declaration ``sig-ops intake-op plan`` prints (offline)."""
    return {
        "schema": "sig.intake-operation/1",
        "ticket": "P37.59",
        "posture": "dark — deployed, receiver_not_operating, loopback-only ingress, no exposure",
        "named_mutation": "the dark intake-service deploy (ops/gcp/intake-roll.sh)",
        "service": asdict(SERVICE),
        "log_exclusions": [asdict(e) for e in LOG_EXCLUSIONS],
        "lb_logging_enabled": LB_LOGGING_ENABLED,
        "intake_backend": INTAKE_BACKEND,
        "infra_posture": list(INFRA_POSTURE),
        "gate_note": (
            "[intake].operational stays false; owner/staffed/secrets/logins/"
            "infra exclusions stay the operator's acts (D-P32.16-1) — the "
            "deploy queues (exit 42) on any missing declared secret rather "
            "than ship a partial shape"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops intake-op",
        description=(
            "P37.59: the dark sig-intake receiver declaration (G2 step 6 / "
            "ACT-23, D-P32.16-1). Offline; ops/gcp/intake-roll.sh owns the "
            "windowed named-mutation leg."
        ),
    )
    sub = parser.add_subparsers(dest="intake_command", required=True)
    sub.add_parser("plan", help="print the declaration (offline, no ADC)")
    args = parser.parse_args(argv)
    if args.intake_command == "plan":
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    return 2
