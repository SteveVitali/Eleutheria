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
