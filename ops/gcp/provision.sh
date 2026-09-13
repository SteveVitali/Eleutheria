#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/provision.sh — idempotent GCP provisioning for the SIG hosted home
# (P24.1 / DEPLOY.1 / GL-DEPLOY-01, ADR-075). Parameterised by $SIG_GCP_PROJECT.
#
#   ./provision.sh --check    # (default) plan-only: prints every action, needs
#                             # NO ADC, opens NO network, exits 0. This is the
#                             # deterministic validation path.
#   ./provision.sh --apply    # operator-gated: requires ADC; provisions for real.
#
# The DECISION (ADR-075) is a single always-free e2-micro GCE running the compose
# stack (PG18+PostGIS + the read API) with GCS for the static site/exports; the
# Cloud SQL + Cloud Run alternative is emitted by `provision_alternative` (kept
# documented, not run by the default path). Buckets are public-read ONLY on the
# published compartment (sig-web + sig-public); restricted + backups stay private.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
require_project
require_adc

banner "provision (DECISION: e2-micro + GCS + Cloud Run API)"

# 1. Enable only the APIs this zero-cost design uses.
enable_apis() {
  _log "-- APIs --"
  run gcloud services enable \
    compute.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    --project "${SIG_GCP_PROJECT}"
}

# 2. GCS buckets. Public-read is granted ONLY on the published compartment.
provision_buckets() {
  _log "-- GCS buckets --"
  local b
  for b in "${SIG_BUCKET_WEB}" "${SIG_BUCKET_PUBLIC}" \
           "${SIG_BUCKET_RESTRICTED}" "${SIG_BUCKET_BACKUPS}"; do
    # `mb` is idempotent enough for IaC: it errors if the bucket exists, so the
    # apply path tolerates that (checked-create). Uniform bucket-level access.
    run gcloud storage buckets create "gs://${b}" \
      --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}" \
      --uniform-bucket-level-access --public-access-prevention
  done
  # Public-read: ONLY sig-web (static site) and sig-public (published exports).
  for b in "${SIG_BUCKET_WEB}" "${SIG_BUCKET_PUBLIC}"; do
    run gcloud storage buckets update "gs://${b}" --no-public-access-prevention
    run gcloud storage buckets add-iam-policy-binding "gs://${b}" \
      --member=allUsers --role=roles/storage.objectViewer
  done
  # sig-restricted + sig-backups are LEFT private (no allUsers binding) — the
  # ODbL / non-published compartments and backups are never world-readable.
  _log "note: ${SIG_BUCKET_RESTRICTED} and ${SIG_BUCKET_BACKUPS} stay PRIVATE."
}

# 3. Artifact Registry for the API image (built + pushed by `sig-ops deploy`).
provision_artifact_registry() {
  _log "-- Artifact Registry --"
  run gcloud artifacts repositories create "${SIG_AR_REPO}" \
    --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}" \
    --repository-format=docker --description="SIG API images"
}

# 4. Secret Manager — create the secret *containers* by name only. The operator
#    adds the versions (values) out-of-band; NO value is ever in this repo.
provision_secrets() {
  _log "-- Secret Manager (names only; no values) --"
  local s
  for s in "${SIG_SECRET_PG_PASSWORD}" "${SIG_SECRET_API_ENV}"; do
    run gcloud secrets create "${s}" \
      --project "${SIG_GCP_PROJECT}" --replication-policy=automatic
    _log "note: add a version out-of-band: gcloud secrets versions add ${s} --data-file=-"
  done
}

# 5a. DECISION path — the e2-micro GCE running the docker-compose stack.
provision_compute_decision() {
  _log "-- Compute (DECISION: e2-micro GCE running ops/docker-compose.yml) --"
  run gcloud compute instances create "${SIG_GCE_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" --zone "${SIG_GCP_ZONE}" \
    --machine-type "${SIG_GCE_MACHINE_TYPE}" \
    --image-family=cos-stable --image-project=cos-cloud \
    --boot-disk-size=30GB \
    --metadata=startup-script-url="gs://${SIG_BUCKET_RESTRICTED}/startup/compose-up.sh"
  _log "note: PG password is injected on the host from Secret Manager (${SIG_SECRET_PG_PASSWORD})."
  # The read API on Cloud Run (min-instances 0, scales to zero) fronts the GCE PG
  # over its internal IP; TLS is the Cloud Run managed default (GL-DEPLOY-01).
  run gcloud run deploy "${SIG_RUN_SERVICE}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --image "${SIG_API_IMAGE}:latest" \
    --min-instances=0 --max-instances=2 --allow-unauthenticated \
    --set-secrets="SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"
}

# 5b. DOCUMENTED ALTERNATIVE — Cloud SQL (managed PG+PostGIS) + Cloud Run only.
#     Emitted for completeness; the default DECISION path does NOT call this.
provision_alternative() {
  _log "-- ALTERNATIVE (documented, ADR-075; not run by default) --"
  _plan "gcloud sql instances create ${SIG_SQL_INSTANCE} --tier=${SIG_SQL_TIER} --database-version=POSTGRES_16 --region=${SIG_GCP_REGION} (then enable the postgis extension)"
  _plan "gcloud run deploy ${SIG_RUN_SERVICE} --add-cloudsql-instances ${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE} --min-instances=0"
  _log "note: Cloud SQL has automated backups built in but is NOT free-tier (~\$9+/mo)."
}

enable_apis
provision_buckets
provision_artifact_registry
provision_secrets
provision_compute_decision
provision_alternative

_log ""
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. Real apply is"
  _log "gate-pending on operator ADC (HG-12 / D-ACCT.1-1). Exit 0."
else
  _log "apply complete."
fi
