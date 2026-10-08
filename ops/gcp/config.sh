# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/config.sh — shared, PARAMETERISED configuration for the GCP IaC
# (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075). Sourced by every script in this
# directory. It contains NO secret and NO literal project id: the project comes
# from the environment ($SIG_GCP_PROJECT, go-live spec D3 / RISK-P21-05), and
# every credential is a Secret Manager *reference* by name only (HG-09).
#
# shellcheck shell=bash

# --- project + location (env-parameterised) ----------------------------------
# The GCP project id is NEVER written literally in a tracked file (this repo is
# public). The operator exports SIG_GCP_PROJECT (name `eleutheria`, GL-GATE-04).
: "${SIG_GCP_PROJECT:=}"
# Region/zone default to an always-free-tier region (SIG-STORE-003 zero-cost):
# the e2-micro free instance is only free in us-west1 / us-central1 / us-east1.
: "${SIG_GCP_REGION:=us-central1}"
: "${SIG_GCP_ZONE:=us-central1-a}"

# --- resource names (derived from the project id) ----------------------------
# Buckets. Public-read is granted ONLY on the published compartment (sig-public)
# and the static site (sig-web); restricted compartments and backups stay
# private (Part VIII §42 compartment separation; GL-DEPLOY-01).
export SIG_BUCKET_WEB="${SIG_GCP_PROJECT}-sig-web"              # static Astro site (public-read)
export SIG_BUCKET_PUBLIC="${SIG_GCP_PROJECT}-sig-public"        # published compartment: exports/deposits/tiles (public-read)
export SIG_BUCKET_RESTRICTED="${SIG_GCP_PROJECT}-sig-restricted" # non-published compartments + mirrors (PRIVATE)
export SIG_BUCKET_BACKUPS="${SIG_GCP_PROJECT}-sig-backups"      # pg_dump + OCFL backup sync (PRIVATE)

# Artifact Registry (the API image) + Cloud Run service (min-instances 0).
export SIG_AR_REPO="sig"
export SIG_AR_HOST="${SIG_GCP_REGION}-docker.pkg.dev"
export SIG_API_IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-api"
export SIG_RUN_SERVICE="sig-api"

# The compute host (ADR-075 DECISION = a single always-free e2-micro running the
# compose stack; Cloud SQL + Cloud Run for the API is the documented alternative).
export SIG_GCE_INSTANCE="sig-stack"
export SIG_GCE_MACHINE_TYPE="e2-micro"

# Cloud SQL (the DOCUMENTED ALTERNATIVE, ADR-075). Named here so the alternative
# path in provision.sh is complete; NOT provisioned by the default DECISION path.
export SIG_SQL_INSTANCE="sig-pg"
export SIG_SQL_TIER="db-f1-micro"

# Secret Manager secret NAMES (references only — never values, HG-09). The
# operator creates the versions out-of-band; the runtime reads them by name.
export SIG_SECRET_PG_PASSWORD="sig-pg-password"
export SIG_SECRET_API_ENV="sig-api-env"

# The Astro static site + the export/tile bytes to sync (relative to repo root).
export SIG_WEB_DIST="web/dist"
export SIG_EXPORT_DIR="exports/out"

# --- recurring ingestion cadence (P25.7 / LIVE-OPS.7 d5) -----------------------
# The Cloud Run ingestion jobs exist (P25.2 created `sig-ingest-muckrock`); this
# wires ONLY the recurring trigger: a Cloud Scheduler HTTP job that invokes the
# job's :run endpoint with an OIDC-signed call from a dedicated service account
# (least-privilege: run.invoker on that job only). The cadence matches the
# source registry `cadence` field (`sig-orchestration interval --source
# muckrock` → 30 days); the job's targeted-lookup posture is unchanged
# (SIG-INGEST-036/037 — never a listing crawl).
export SIG_RUN_JOB_MUCKROCK="sig-ingest-muckrock"
export SIG_SCHEDULER_SA="sig-scheduler"
export SIG_SCHEDULER_JOB_MUCKROCK="sig-sched-muckrock"
export SIG_SCHEDULER_CRON_MUCKROCK="0 6 1 * *"   # monthly, 06:00 UTC

# --- scheduled live operations (P26.1 / OPS.2) ---------------------------------
# The `sig-probe` hosted-sweep job (every 6h) plus the per-source
# `sig-ingest-<id>` jobs driven by Cloud Scheduler triggers. The per-source
# rows — cadence, cron, job/scheduler names — live in `ops/cadence.toml` (the
# single source of truth, read via tomllib by scheduled-ops.sh); only the
# job-level constants live here. Alerts route through the existing sig-alerts
# receiver (P25.8): URL resolved at apply time, token via Secret Manager.
export SIG_RUN_JOB_PROBE="sig-probe"
export SIG_SCHEDULER_JOB_PROBE="sig-sched-probe"
export SIG_SCHEDULER_CRON_PROBE="0 */6 * * *"    # every 6h UTC
# P31.6 / ADR-113: the asserting-replay job — `sig-ops replay-ingest` over the
# persisted OCFL captures (ingest_run_capture digests), writing a fresh
# is_replay ingest_run. Operator-invoked only: deployed here, NEVER scheduled
# (a replay is a named decision, not a cadence).
export SIG_RUN_JOB_REPLAY="sig-replay-ingest"
export SIG_ALERTS_SERVICE="sig-alerts"
export SIG_SECRET_ALERT_HOOK="sig-alert-webhook-token"
export SIG_WEB_SERVICE="sig-web"
export SIG_CADENCE_TOML="ops/cadence.toml"

# --- custom domain + HTTPS load balancer (P27.10 / LAUNCH.10, ADR-098) ----------
# The canonical public origin. The domain + its DNS records are PUBLIC config, not
# secrets (HG-09) — a public domain name is safe to write literally, unlike any
# credential (which stays a Secret Manager reference by name). Env-overridable so a
# staging/preview domain can reuse the same IaC.
export SIG_WEB_DOMAIN="${SIG_WEB_DOMAIN:-surveillancegraph.org}"
export SIG_WEB_DOMAIN_WWW="${SIG_WEB_DOMAIN_WWW:-www.${SIG_WEB_DOMAIN}}"

# The external HTTPS Application Load Balancer that fronts the sig-web Cloud Run
# service with Google-managed TLS (ADR-098 — chosen over a Cloud Run domain mapping
# because the mapping requires interactive Search Console domain verification the
# cloud-platform ADC cannot perform; the LB needs none and yields a real reserved
# static IP as the apex/www A-record value). Names are derived, no literal project.
export SIG_LB_IP="sig-web-ip"                       # reserved global external IPv4
export SIG_LB_NEG="sig-web-neg"                     # serverless NEG → sig-web (regional)
export SIG_LB_BACKEND="sig-web-backend"             # global backend service (EXTERNAL_MANAGED)
export SIG_LB_CERT="sig-web-cert"                   # Google-managed cert (apex + www)
export SIG_LB_URLMAP="sig-web-urlmap"               # HTTPS url map: apex→backend, www→apex 301
export SIG_LB_HTTPS_PROXY="sig-web-https-proxy"     # target HTTPS proxy
export SIG_LB_HTTPS_FR="sig-web-fr-https"           # :443 global forwarding rule
export SIG_LB_REDIRECT_URLMAP="sig-web-http-redirect" # HTTP url map: :80 → HTTPS 301
export SIG_LB_HTTP_PROXY="sig-web-http-proxy"       # target HTTP proxy
export SIG_LB_HTTP_FR="sig-web-fr-http"             # :80 global forwarding rule

# P34.40 / ACT-17 (G3 §4.3 option 3a): the L2 `/v1/*` path rule — a serverless
# NEG + backend service for `sig-api`, then a URL-map path rule on the apex
# matcher. The `/intake/*` rule is DECLARED in ops/lb_routes.toml behind
# `enabled = false` (no `sig-intake` service exists; P37.59 owns it) — these
# names exist so the written-not-applied rule and its eventual service have
# stable, parameterised names. The release-registry bucket is P35.53's; named
# here so the (unrolled) registry-mount command is derived, never literal.
export SIG_LB_API_NEG="sig-api-neg"                 # serverless NEG → sig-api (regional)
export SIG_LB_API_BACKEND="sig-api-backend"         # global backend service
export SIG_INTAKE_SERVICE="sig-intake"              # the (nonexistent) receiver service
export SIG_LB_INTAKE_NEG="sig-intake-neg"           # serverless NEG → sig-intake
export SIG_LB_INTAKE_BACKEND="sig-intake-backend"   # global backend service
export SIG_BUCKET_RELEASE="${SIG_GCP_PROJECT}-sig-release"  # release registry (PRIVATE, P35.53)
export SIG_RELEASE_MOUNT="/mnt/rel"                 # sig-api's registry mount root
export SIG_RELEASE_REGISTRY_DIR="${SIG_RELEASE_MOUNT}/registry"  # --release-registry value

# The P34.40 live window (OM-19): both legs ≥ the SIG_LB_EARLIEST bound below
# and never 03:00–10:00Z (the contract's named window open, row 249).
# lb-routes.sh + web-roll.sh enforce it in --apply; the override
# exists for the offline guard test only.
export SIG_LB_EARLIEST="2026-10-13T12:00:00Z"  # future-ok: scheduled: contract window
# The legs' restore-point + byte-compare capture dir (each script defaults to
# ${TMPDIR}/p34.40-l{1,2}); export to keep a run's prestate across invocations.
export SIG_LB_STATE_DIR="${SIG_LB_STATE_DIR:-${TMPDIR:-/tmp}/p34.40}"

# --- least-privilege runtime identities (P34.42a / G1-01, F-272, SIG-SEC-007) --
# One per-workload service account per Cloud Run service (AR-8). The committed
# declaration ops/iam_identities.toml (`sig.iam-identities/1`, read by
# `sig-ops iam`) carries the bindings + the sig-alerts invoker change; the
# windowed leg ops/gcp/iam-service-accounts.sh creates the SAs and makes the
# mutations — it must run BEFORE any deploy that names these accounts.
export SIG_SA_API="sig-api-rt"          # cloudsql.client + sig-pg-password accessor only
export SIG_SA_WEB="sig-web-rt"          # objectViewer on ${SIG_BUCKET_WEB} only
export SIG_SA_ALERTS="sig-alerts-rt"    # no project roles, no secret access
export SIG_API_SA_EMAIL="${SIG_SA_API}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_WEB_SA_EMAIL="${SIG_SA_WEB}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_ALERTS_SA_EMAIL="${SIG_SA_ALERTS}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
export SIG_IAM_TOML="ops/iam_identities.toml"
# The P34.42a live window (OM-19): the IAM leg applies ≥ the bound below and
# never 03:00–06:30Z (the contract's AR-3 + AR-2 window, row 251 — narrower
# than P34.40's band, matching the AR-3 daily freeze). SIG_IAM_NOW overrides
# the clock for the offline guard test only.
export SIG_IAM_EARLIEST="2026-10-13T12:00:00Z"  # future-ok: scheduled: contract window
export SIG_IAM_STATE_DIR="${SIG_IAM_STATE_DIR:-${TMPDIR:-/tmp}/p34.42a-iam}"

# --- least-privilege JOB identities (P34.42b / G1-01, F-272) -------------------
# One service account per job CLASS — ingest / probe / export / materialize —
# plus the reserved identities the jobs leg creates with no grants (the
# scheduler invoker + P34.44b/P35.53/P36.43's future runtime SAs). The job→class
# map + bindings live in ops/iam_identities.toml (read via `sig-ops iam plan
# --leg jobs`); ops/gcp/iam-job-identities.sh owns the (windowed) mutations:
# prestate → identities → bindings → jobs (88 same-image updates) → invokers
# (the scheduler move + the sig-alerts jobs-posture rule) → editor (the
# roles/editor removal — LAST, only after no workload still runs as it).
export SIG_SA_INGEST="sig-ingest-rt"
export SIG_SA_PROBE="sig-probe-rt"
export SIG_SA_EXPORT="sig-export-rt"
export SIG_SA_MATERIALIZE="sig-materialize-rt"
export SIG_SA_QUALITY_PROBE="sig-quality-probe-rt"  # reserved: P34.44b
export SIG_SA_RELEASE="sig-release-rt"              # reserved: P35.53
export SIG_SA_STATUS="sig-status-rt"                # reserved: P36.43
export SIG_SA_SCHEDULER="sig-scheduler"             # invoker only, never a runtime
# Same contract window as the services leg (OM-19, row 252): applies ≥
# SIG_IAM_EARLIEST and never 03:00–06:30Z; SIG_IAM_JOBS_NOW overrides the
# clock for the offline guard test only.
export SIG_IAM_JOBS_EARLIEST="${SIG_IAM_EARLIEST}"
export SIG_IAM_JOBS_STATE_DIR="${SIG_IAM_JOBS_STATE_DIR:-${TMPDIR:-/tmp}/p34.42b-iam}"

# --- execution host + least-privilege DB logins (P34.43 / SIG-CONF-013) ------
# The one-off Cloud Run execution host (ops/exec_host.toml, rendered by
# `sig-ops exec-host`; the windowed leg is ops/gcp/exec-host.sh) and the two
# least-privilege DB logins (ops/gcp/db-logins.sh): sig_audit (L1) and
# sig_recovery_login (L2 — gated live:P34.46, enforced by the catalog read).
# Same contract window as the IAM legs (OM-19, row 253): applies ≥
# SIG_EXEC_EARLIEST and never 03:00–06:30Z; SIG_EXEC_NOW /
# SIG_DBLOGINS_NOW override the clock for the offline guard tests only.
export SIG_EXEC_EARLIEST="2026-10-13T12:00:00Z"  # future-ok: scheduled: contract window
export SIG_EXEC_STATE_DIR="${SIG_EXEC_STATE_DIR:-${TMPDIR:-/tmp}/p34.43-exec}"
export SIG_DBLOGINS_STATE_DIR="${SIG_DBLOGINS_STATE_DIR:-${TMPDIR:-/tmp}/p34.43-db}"
export SIG_EXEC_SA="${SIG_SA_QUALITY_PROBE}"    # the exec host's runtime identity
export SIG_EXEC_PREFIX="sig-exec"               # every one-off job is <prefix>-<purpose>-<stamp>
export SIG_EXEC_BUCKET="${SIG_BUCKET_RESTRICTED}"
export SIG_EXEC_MOUNT="/mnt/captures"           # the read-only captures mount
export SIG_EXEC_CAPTURE_PREFIX="evidence/captures/"
export SIG_EXEC_PROBE_PREFIX="ops/probes"       # one sig.probe-run/1 per use
export SIG_SECRET_AUDIT_PASSWORD="sig-audit-password"
export SIG_SECRET_RECOVERY_PASSWORD="sig-recovery-password"
export SIG_DB_ROLE_AUDIT="sig_audit"
export SIG_DB_ROLE_RECOVERY="sig_recovery_login"
export SIG_DBLOGINS_EARLIEST="${SIG_EXEC_EARLIEST}"

# The canonical public origin + the run.app fallback the probe/uptime sweeps watch
# (P27.10 d4). No host literal is baked into cadence.toml — the operator resolves
# SIG_PROBE_WEB_URL from this at apply time (the *.run.app URL stays the documented
# fallback until Google-managed TLS provisions on the domain).
export SIG_WEB_CANONICAL_URL="https://${SIG_WEB_DOMAIN}"
