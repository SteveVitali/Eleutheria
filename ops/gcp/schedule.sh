#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/schedule.sh — recurring-cadence triggers for the Cloud Run ingestion
# jobs (P25.7 / LIVE-OPS.7 d5, SCHED.1 / GL-SCHED-01, ADR-076).
#
#   ./schedule.sh --check    # (default) plan-only: prints every action, needs
#                            # NO ADC, opens NO network, exits 0.
#   ./schedule.sh --apply    # operator-gated: requires ADC; provisions for real.
#
# The `sig-ingest-muckrock` Cloud Run job ran once on 2026-09-15 (P25.2: refresh
# → JWT → request 136412 → 6 claims). This script wires its RECURRING form: a
# Cloud Scheduler HTTP job that invokes the job's :run endpoint with an
# OIDC-signed call from a dedicated least-privilege service account
# (roles/run.invoker on that job only). The job itself — its command, secrets
# references, and targeted-lookup posture (SIG-INGEST-036/037, never a listing
# crawl) — is unchanged; the scheduler only decides WHEN it runs. The cadence
# mirrors the source registry `cadence` field (sources.toml → `sig-orchestration
# interval --source muckrock` = 30 days), so the offline cadence engine and the
# hosted trigger agree.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
require_project
require_adc

banner "scheduler (sig-ingest-muckrock recurring cadence)"

SIG_SCHEDULER_SA_EMAIL="${SIG_SCHEDULER_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
# The Cloud Run job :run endpoint (run.googleapis.com v1 REST surface).
SIG_JOB_RUN_URI="https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_RUN_JOB_MUCKROCK}:run"

# 1. The Scheduler API.
_log "-- APIs --"
run gcloud services enable cloudscheduler.googleapis.com \
  --project "${SIG_GCP_PROJECT}"

# 2. The dedicated invoker service account (least-privilege, HG-09: no keys —
#    OIDC-signed invocation only).
_log "-- invoker service account --"
run gcloud iam service-accounts create "${SIG_SCHEDULER_SA}" \
  --project "${SIG_GCP_PROJECT}" \
  --display-name="SIG Cloud Scheduler invoker (ingestion jobs)"
run gcloud run jobs add-iam-policy-binding "${SIG_RUN_JOB_MUCKROCK}" \
  --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
  --member="serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" \
  --role=roles/run.invoker

# 3. The recurring trigger — monthly (registry `cadence = "monthly"` → 30 days).
_log "-- Cloud Scheduler trigger --"
run gcloud scheduler jobs create http "${SIG_SCHEDULER_JOB_MUCKROCK}" \
  --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}" \
  --schedule "${SIG_SCHEDULER_CRON_MUCKROCK}" --time-zone=Etc/UTC \
  --uri "${SIG_JOB_RUN_URI}" \
  --http-method=POST \
  --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}"

_log ""
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. Real apply is"
  _log "gate-pending on operator ADC (HG-12 / D-ACCT.1-1). Exit 0."
else
  _log "apply complete — ${SIG_SCHEDULER_JOB_MUCKROCK} invokes ${SIG_RUN_JOB_MUCKROCK} on '${SIG_SCHEDULER_CRON_MUCKROCK}'."
fi
