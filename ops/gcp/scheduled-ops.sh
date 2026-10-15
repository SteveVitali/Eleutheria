#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/scheduled-ops.sh — scheduled live operations (P26.1 / OPS.2): the
# recurring probe sweep + the per-source reingestion triggers.
#
#   ./scheduled-ops.sh --check    # (default) plan-only: prints every action,
#                                 # needs NO ADC, opens NO network, exits 0.
#   SIG_JOB_IMAGE=<ref> ./scheduled-ops.sh --apply
#                                 # operator-gated: requires ADC; applies for real.
#
# P31.4 / ADR-111: every job is deployed BY PINNED DIGEST, never `:latest`.
# SIG_JOB_IMAGE names the image (a SHA tag such as `sig-api:ingest-<sha>`, or an
# `@sha256:` digest); the script resolves a tag to its digest through Artifact
# Registry and deploys the digest. `:latest` or an untagged reference is refused.
# (To roll NEW code onto the EXISTING jobs, prefer `sig-ops roll-jobs --image <ref>`,
# which changes only the image + capture store and preserves each job's other
# settings; this script (re)creates jobs from their cadence.toml rows.)
#
# Every scheduled-ingest job mounts the restricted bucket (gcsfuse, gen2) as its
# capture store and points SIG_CAPTURE_DIR into it, so the OCFL captures a run
# writes survive the execution and a restarted run re-processes them (ADR-111).
# The mount is removed-then-added, so a re-apply over an existing job is idempotent.
#
# What it wires:
#   * Cloud Run job `sig-probe` — `sig-ops probe-hosted --alert`: sweeps the
#     hosted read API (/ + /v1/coverage/okc), the public sig-web service, the
#     public export objects, and Cloud SQL reachability; appends the sweep as a
#     per-run timestamped object under gs://…-sig-restricted/ops/probes/ (WORM);
#     a DOWN target fires a recorded alert through the sig-alerts receiver.
#   * Cloud Scheduler `sig-sched-probe` — every 6h UTC.
#   * Per-source Cloud Run jobs `sig-ingest-<id>` — `sig-ops scheduled-ingest
#     --source <id> --sink pg`: the same gated `connectors.runner` path a manual
#     run takes (a non-green source is refused before any socket — HG-03 is
#     never bypassed); every execution appends a run row under
#     gs://…-sig-restricted/ops/runs/<source>/ (refusals + disappearances
#     recorded, never retried into silence — max-retries 0).
#   * Per-source Cloud Scheduler triggers `sig-sched-<id>` on the cadence.toml
#     cron. `existing = true` rows (muckrock, P25.7) have their TRIGGER verified,
#     not recreated; the run job is still upserted to the `scheduled-ingest`
#     wrapper so every scheduled execution appends an ops/runs row.
#
# P35.1a (SIG-OPS-005 / SIG-SEC-008, ADR-174) adds the scheduler-of-record legs:
#   * `[[maintenance]]` triggers — deployed and held PAUSED; the reconcile
#     never enables one (a paused row's own verbatim-go machinery owns its
#     enablement — e.g. D-P34.6-2's monthly export).
#   * The `[live_diff]` trigger — a daily Cloud Scheduler job that invokes the
#     probe job with an args OVERRIDE (`sig-ops live-diff --live --alert`), so
#     the read-only reconciler rides the probe identity + alert seam.
#   * The declaration bundle — `sig-ops live-diff --emit-declared` piped to
#     gs://…-sig-restricted/ops/declared/live-diff.json; the in-image diff reads
#     THAT object (SIG_OPS_DECLARED_GCS), so a cadence change takes effect at
#     the next reconcile without an image roll (SIG-OPS-005).
#   * The undeclared-trigger report — apply lists live Cloud Scheduler jobs
#     that are not declared (reported, never deleted here: deletion is the
#     P35.1b fleet-hygiene leg's call).
#
# P35.6 (I8 §7.1, R6 first-run protocol, NEW-4) adds:
#   * `--paused` — every trigger this run CREATES is created then immediately
#     paused (R6 step 1: no new source's first execution is an unobserved
#     scheduler first-fire). A trigger that already exists is UPDATED normally
#     and its state left untouched — `--paused` never pauses a live trigger.
#     The wave's verbatim-go leg resumes them (R6 step 5), never this script.
#   * per-row `task_timeout` on `[[sources]]`/`[[batches]]` rows — a cadence.toml
#     duration string (e.g. `3h`, `6h`) overrides the 60m/36h defaults; the
#     Round-11 documents/layers batches carry 6h (I8 §7.1). `--max-retries 0`
#     is unchanged — a timed-out run is resumed by `logical_run`, never retried
#     into silence.
#
# The per-source table comes from ops/cadence.toml via tomllib — that file is
# the single source of truth, and `sig-ops cadence --check` fails on drift.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
require_project
require_adc

# R6 (P35.6): `--paused` anywhere in the args marks every trigger this run
# *creates* for an immediate pause — a newly-registered source's first
# execution is the observed manual run, never an unobserved first-fire.
SIG_CREATE_PAUSED=0
for _arg in "$@"; do
  case "${_arg}" in
    --paused) SIG_CREATE_PAUSED=1 ;;
  esac
done
[ "${SIG_CREATE_PAUSED}" = "1" ] && _log "R6 create-paused: every NEW trigger is paused on create" || true

banner "scheduled live operations (P26.1 / OPS.2)"

SIG_SCHEDULER_SA_EMAIL="${SIG_SCHEDULER_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
# The job-class runtime identities (P34.42b / G1-01): every upserted job runs
# as its class SA — sig-probe + the ingest fleet + the replay job. The jobs
# leg (iam-job-identities.sh) creates them and holds the IAM; passing the SA
# explicitly keeps a re-apply from falling back to the default compute SA.
SIG_PROBE_SA_EMAIL="${SIG_SA_PROBE}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
SIG_INGEST_SA_EMAIL="${SIG_SA_INGEST}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
: "${SIG_JOB_IMAGE:=}"

# The pinned digest every job deploys (ADR-111; `pin_image_digest`, lib.sh). Check
# mode needs no registry: an unset SIG_JOB_IMAGE plans with a placeholder digest.
resolve_job_image() {
  if [ -z "${SIG_JOB_IMAGE}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      printf '%s@sha256:<digest-of-SIG_JOB_IMAGE>' "${SIG_API_IMAGE}"
      return 0
    fi
    _log "ERROR: SIG_JOB_IMAGE must name the image to deploy (a SHA tag or @sha256 digest)." >&2
    return 2
  fi
  pin_image_digest "${SIG_JOB_IMAGE}"
}
IMAGE="$(resolve_job_image)"
case "${IMAGE}" in
  *@sha256:*) ;;
  *) _log "ERROR: could not resolve SIG_JOB_IMAGE to a digest (got '${IMAGE}')." >&2; exit 2 ;;
esac
_log "job image (pinned digest): ${IMAGE}"
CONN="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
CAPTURE_MOUNT="/mnt/captures"
# P35.1a: the cadence content hash rides every job's env (a run row records
# which declaration the fleet was deployed against) and the declaration bundle
# URI tells the in-image live-diff where the published declared side lives —
# config changes take effect at the reconcile, not the image roll (SIG-OPS-005).
CADENCE_SHA256="$(shasum -a 256 "${_here}/../cadence.toml" | awk '{print $1}')"
DECLARED_GCS_URI="gs://${SIG_BUCKET_RESTRICTED}/ops/declared/live-diff.json"
JOB_ENV="SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED},SIG_OPS_CADENCE=/app/ops/cadence.toml,SIG_OPS_CADENCE_SHA256=${CADENCE_SHA256},SIG_OPS_DECLARED_GCS=${DECLARED_GCS_URI},SIG_PG_USER=sig,SIG_PG_DB=${SIG_PG_DB_NAME:-sig},SIG_CLOUDSQL_CONNECTION=${CONN}"
# The ingest jobs' capture store (P31.4 / ADR-111): the restricted bucket, mounted.
# SIG_CODE_COMMIT = the deployed digest: runs record it as code_commit, and a restart
# resumes only the marks of runs on the same code (ADR-111).
INGEST_ENV="${JOB_ENV},SIG_CAPTURE_DIR=${CAPTURE_MOUNT}/evidence/captures,SIG_CODE_COMMIT=${IMAGE##*@}"

# Resolve a Cloud Run service's deployed URL — never a literal in the repo.
svc_url() {
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '<url-of-%s>' "$1"
  else
    gcloud run services describe "$1" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format='value(status.url)'
  fi
}

# Upsert a Cloud Scheduler HTTP trigger (create-or-update keeps --apply
# idempotent). `$4` is an optional JSON args array — embedded as the POST
# body's RunJobRequest `overrides.containerOverrides[].args`, which replaces
# the target job's baked args for this trigger's invocations only.
sched_upsert() {
  local name="$1" schedule="$2" job="$3" args_json="${4:-}"
  local uri="https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${job}:run"
  local body_args=()
  if [ -n "${args_json}" ]; then
    body_args=(--message-body "{\"overrides\":{\"containerOverrides\":[{\"args\":${args_json}}]}}")
  fi
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    local paused_note=""
    [ "${SIG_CREATE_PAUSED}" = "1" ] && paused_note="; NEW triggers paused on create (R6)"
    _plan "gcloud scheduler jobs create http ${name} --schedule '${schedule}' --time-zone=Etc/UTC --uri ${uri} --http-method=POST --oauth-service-account-email=${SIG_SCHEDULER_SA_EMAIL} ${body_args[*]:-}   # (update if already present${paused_note})"
    return 0
  fi
  if gcloud scheduler jobs describe "${name}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    run gcloud scheduler jobs update http "${name}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${schedule}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}" \
      ${body_args[@]+"${body_args[@]}"}
  else
    run gcloud scheduler jobs create http "${name}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${schedule}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${SIG_SCHEDULER_SA_EMAIL}" \
      ${body_args[@]+"${body_args[@]}"}
    # R6 step 1 (P35.6): a trigger that did not exist before this run is paused
    # immediately under --paused; an existing trigger's state is never touched.
    if [ "${SIG_CREATE_PAUSED}" = "1" ]; then
      sched_set_state "${name}" paused
    fi
  fi
}

# Hold a trigger at its declared state — a declared-paused (maintenance) row
# is created then immediately paused, and a re-apply re-pauses it: the
# reconcile NEVER enables a maintenance row (its own verbatim-go leg does).
sched_set_state() {
  local name="$1" state="$2"
  local verb
  case "${state}" in
    paused)  verb=pause ;;
    enabled) verb=resume ;;
    *) _log "ERROR: unknown declared scheduler state '${state}' for ${name}" >&2; return 2 ;;
  esac
  run gcloud scheduler jobs "${verb}" "${name}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
}

# Read the per-source cadence table
# (id|cadence|cron|job|scheduler|existing|extra-secrets|task_timeout).
# `task_timeout` (P35.6) is a per-row duration string; empty = 60m default.
read_cadence_rows() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
for s in doc.get("sources", []):
    extra = ",".join(f"{k}={v}:latest" for k, v in s.get("secrets", {}).items())
    print(
        "|".join(
            [
                s["id"],
                s["cadence"],
                s["cron"],
                s["job"],
                s["scheduler"],
                "1" if s.get("existing") else "0",
                extra,
                s.get("task_timeout", ""),
            ]
        )
    )
PY
  )
}

# Read the grouped-batch table
# (id|cadence|cron|job|scheduler|member-count|task_timeout) —
# P26.16 (SOURCES.15): the GL-GATE-07 rights batch groups its newly-green
# camera-registry sources under ~10 sig-ingest-camreg-batch-* jobs; each batch
# job runs `scheduled-ingest --batch <id>` which appends one ops/runs row PER
# MEMBER source. `task_timeout` (P35.6) is a per-row duration string; empty =
# the 36h default (ADR-107's batch-05 ceiling).
read_batch_rows() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
for b in doc.get("batches", []):
    print(
        "|".join(
            [
                b["id"],
                b["cadence"],
                b["cron"],
                b["job"],
                b["scheduler"],
                str(len(b.get("members", []))),
                b.get("task_timeout", ""),
            ]
        )
    )
PY
  )
}

# Read the maintenance table (id|cron|scheduler|state|target-job) — P35.1a:
# each row's trigger is deployed and held at its declared `state` (today's
# only row is PAUSED — the D-P34.6-2 monthly export stays inert until its
# verbatim in-ticket go; the reconcile never enables a maintenance row).
read_maintenance_rows() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
for m in doc.get("maintenance", []):
    if not m.get("scheduler"):
        continue  # a queued stub declares no trigger — nothing to reconcile
    print(
        "|".join(
            [
                m["id"],
                m["cron"],
                m["scheduler"],
                m.get("state", "paused"),
                m.get("target_job") or f"sig-{m['id']}",
            ]
        )
    )
PY
  )
}

# Read the [live_diff] trigger declaration (scheduler|cron|job|args-json) —
# the daily repo-vs-live reconciler that rides the probe job with an args
# override (P35.1a / SIG-OPS-005).
read_live_diff_row() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
ld = doc.get("live_diff")
if ld:
    print("|".join([ld["scheduler"], ld["cron"], ld["job"], ld["args"]]))
PY
  )
}

# Read every declared trigger name (probe + sources + batches + maintenance +
# live-diff) — the allow-list the undeclared-trigger report diffs live against.
read_declared_triggers() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
names = [doc.get("probes", {}).get("scheduler")]
names += [s.get("scheduler") for s in doc.get("sources", [])]
names += [b.get("scheduler") for b in doc.get("batches", [])]
names += [m.get("scheduler") for m in doc.get("maintenance", [])]
ld = doc.get("live_diff") or {}
names.append(ld.get("scheduler"))
for n in names:
    if n:
        print(n)
PY
  )
}

# 1. The Scheduler API + the dedicated least-privilege invoker SA (OIDC only —
#    no keys, HG-09). Both already exist from P25.7's muckrock wiring; the
#    describe-guard keeps the apply idempotent.
_log "-- APIs + invoker service account --"
run gcloud services enable cloudscheduler.googleapis.com \
  --project "${SIG_GCP_PROJECT}"
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _plan "gcloud iam service-accounts describe ${SIG_SCHEDULER_SA_EMAIL}  (create if absent)"
else
  if ! gcloud iam service-accounts describe "${SIG_SCHEDULER_SA_EMAIL}" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    run gcloud iam service-accounts create "${SIG_SCHEDULER_SA}" \
      --project "${SIG_GCP_PROJECT}" \
      --display-name="SIG Cloud Scheduler invoker (ingestion jobs)"
  else
    _log "  invoker SA ${SIG_SCHEDULER_SA_EMAIL} exists"
  fi
fi

# 2. The probe job + its 6-hourly trigger.
_log "-- sig-probe (hosted sweep → gs://…-sig-restricted/ops/probes/) --"
API_URL="$(svc_url "${SIG_RUN_SERVICE}")"
WEB_URL="$(svc_url "${SIG_WEB_SERVICE}")"
ALERTS_URL="$(svc_url "${SIG_ALERTS_SERVICE}")"
run gcloud run jobs deploy "${SIG_RUN_JOB_PROBE}" \
  --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
  --service-account "${SIG_PROBE_SA_EMAIL}" \
  --command sh \
  --args "-c,exec sig-ops probe-hosted --alert" \
  --tasks 1 --task-timeout 10m --max-retries 0 \
  --set-cloudsql-instances "${CONN}" \
  --set-env-vars "${JOB_ENV},SIG_PROBE_API_URL=${API_URL},SIG_PROBE_WEB_URL=${WEB_URL},SIG_ALERT_WEBHOOK_URL=${ALERTS_URL}" \
  --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest,SIG_ALERT_WEBHOOK_TOKEN=${SIG_SECRET_ALERT_HOOK}:latest"
run gcloud run jobs add-iam-policy-binding "${SIG_RUN_JOB_PROBE}" \
  --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
  --member="serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" \
  --role=roles/run.invoker
sched_upsert "${SIG_SCHEDULER_JOB_PROBE}" "${SIG_SCHEDULER_CRON_PROBE}" "${SIG_RUN_JOB_PROBE}"

# 3. Per-source ingest jobs + triggers from ops/cadence.toml. Every job — new or
#    pre-existing — is upserted onto the `sig-ops scheduled-ingest` wrapper so
#    EVERY scheduled execution appends an ops/runs row (the muckrock job ran
#    `sig-connectors run` directly before P26.1; the command change preserves
#    the same gated runner path and its targeted-lookup posture, SIG-INGEST-036).
_log "-- per-source reingestion (run rows → gs://…-sig-restricted/ops/runs/) --"
while IFS='|' read -r src cad cron job sched existing extra ttimeout; do
  [ -z "${src}" ] && continue
  secrets="SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"
  [ -n "${extra}" ] && secrets="${secrets},${extra}"
  _log "  ${src} (${cad} ${cron}) -> ${job}"
  # P26.6: agenda-platform jobs now also fetch the bounded per-tenant document
  # window (≤ doc_per_tenant docs × tenants, ≤ doc_run_cap/run) on top of the
  # index sweep — the largest platform (CivicClerk, ~295 index + ≤350 docs)
  # ran past the 30m ceiling; 60m is the reviewed ingest task bound. A
  # per-row `task_timeout` (P35.6, e.g. legistar's widened keyword pass at 3h)
  # overrides it.
  run gcloud run jobs deploy "${job}" \
    --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${SIG_INGEST_SA_EMAIL}" \
    --command sh \
    --args "-c,exec sig-ops scheduled-ingest --source ${src} --sink pg" \
    --tasks 1 --task-timeout "${ttimeout:-60m}" --max-retries 0 \
    --execution-environment gen2 \
    --remove-volume-mount "${CAPTURE_MOUNT}" --remove-volume captures \
    --add-volume "name=captures,type=cloud-storage,bucket=${SIG_BUCKET_RESTRICTED}" \
    --add-volume-mount "volume=captures,mount-path=${CAPTURE_MOUNT}" \
    --set-cloudsql-instances "${CONN}" \
    --set-env-vars "${INGEST_ENV}" \
    --set-secrets "${secrets}"
  run gcloud run jobs add-iam-policy-binding "${job}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --member="serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" \
    --role=roles/run.invoker
  if [ "${existing}" = "1" ]; then
    # The scheduler trigger already exists (muckrock, P25.7 d5) — verify,
    # never duplicate. The JOB above is still upserted to the run-row wrapper.
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      _plan "verify ${sched} exists and invokes ${job} on '${cron}'  (existing trigger — not recreated)"
    else
      if gcloud scheduler jobs describe "${sched}" \
          --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
        _log "  verified existing ${sched} (${cron}) -> ${job}"
      else
        _log "ERROR: ${sched} is marked existing in cadence.toml but is absent" >&2
        exit 1
      fi
    fi
    continue
  fi
  sched_upsert "${sched}" "${cron}" "${job}"
done < <(read_cadence_rows)

# 4. Grouped batches ([[batches]] — P26.16 GL-GATE-07). One job per batch runs
#    `scheduled-ingest --batch <id>`; the wrapper appends one ops/runs row per
#    member source. 36h ceiling (ADR-107): batch-05 carries the ~1.37M-record OSM
#    mirror, and the live batch jobs already run 36h (P31.4 aligned this script,
#    which used to say 120m, with the deployed jobs so a re-apply cannot shrink it).
_log "-- grouped batches (run rows per member → ops/runs/<source>/) --"
while IFS='|' read -r bid bcad bcron bjob bsched bcount btimeout; do
  [ -z "${bid}" ] && continue
  _log "  batch ${bid} (${bcount} member sources, ${bcad} ${bcron}) -> ${bjob} (task-timeout ${btimeout:-36h})"
  run gcloud run jobs deploy "${bjob}" \
    --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${SIG_INGEST_SA_EMAIL}" \
    --command sh \
    --args "-c,exec sig-ops scheduled-ingest --batch ${bid} --sink pg" \
    --tasks 1 --task-timeout "${btimeout:-36h}" --max-retries 0 \
    --execution-environment gen2 \
    --remove-volume-mount "${CAPTURE_MOUNT}" --remove-volume captures \
    --add-volume "name=captures,type=cloud-storage,bucket=${SIG_BUCKET_RESTRICTED}" \
    --add-volume-mount "volume=captures,mount-path=${CAPTURE_MOUNT}" \
    --set-cloudsql-instances "${CONN}" \
    --set-env-vars "${INGEST_ENV}" \
    --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"
  run gcloud run jobs add-iam-policy-binding "${bjob}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --member="serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" \
    --role=roles/run.invoker
  sched_upsert "${bsched}" "${bcron}" "${bjob}"
done < <(read_batch_rows)

# 5. The asserting-replay job (P31.6 / ADR-113). `sig-ops replay-ingest` re-runs a
#    source's PERSISTED captures (the ingest_run_capture digests resolved from the
#    mounted OCFL store) through the post-capture stages and asserts the new claim
#    set under a fresh is_replay ingest_run — never a fetch. The job mounts the same
#    restricted captures bucket the ingest jobs write, but has NO scheduler trigger
#    and NO invoker binding for the scheduler SA: a replay is a named, operator-run
#    decision, executed explicitly:
#      gcloud run jobs execute sig-replay-ingest \
#        --args "-c,exec sig-ops replay-ingest --source <id> [--run-id <uuid>]"
_log "-- sig-replay-ingest (asserting replay over persisted captures, operator-run) --"
run gcloud run jobs deploy "${SIG_RUN_JOB_REPLAY}" \
  --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
  --service-account "${SIG_INGEST_SA_EMAIL}" \
  --command sh \
  --args "-c,echo 'replay-ingest needs --source (operator-run; see ADR-113)' && exit 64" \
  --tasks 1 --task-timeout 60m --max-retries 0 \
  --execution-environment gen2 \
  --remove-volume-mount "${CAPTURE_MOUNT}" --remove-volume captures \
  --add-volume "name=captures,type=cloud-storage,bucket=${SIG_BUCKET_RESTRICTED}" \
  --add-volume-mount "volume=captures,mount-path=${CAPTURE_MOUNT}" \
  --set-cloudsql-instances "${CONN}" \
  --set-env-vars "${INGEST_ENV}" \
  --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"

# 6. Maintenance triggers ([[maintenance]] — P35.1a). Each declared row gets a
#    trigger held at its declared state; a `paused` row is created then
#    immediately paused (and re-paused on re-apply). The reconcile NEVER
#    enables a maintenance trigger — the row's own verbatim-go leg does
#    (D-P34.6-2's monthly export enables only inside `logical-export.sh
#    --apply export --go "<verbatim in-ticket go>"`).
_log "-- maintenance triggers (declared state; paused rows stay inert) --"
while IFS='|' read -r mid mcron msched mstate mjob; do
  [ -z "${mid}" ] && continue
  _log "  maintenance ${mid} (${mcron}) -> ${msched} state=${mstate} target=${mjob}"
  sched_upsert "${msched}" "${mcron}" "${mjob}"
  sched_set_state "${msched}" "${mstate}"
done < <(read_maintenance_rows)

# 7. The live-diff trigger ([live_diff] — P35.1a / SIG-OPS-005): a daily Cloud
#    Scheduler job invoking the probe job with an args override, so the
#    read-only reconciler rides the probe identity + alert seam without a new
#    job. The `--message-body` carries the RunJobRequest overrides payload.
_log "-- live-diff trigger (daily repo-vs-live reconcile) --"
while IFS='|' read -r ldsched ldcron ldjob ldargs; do
  [ -z "${ldsched}" ] && continue
  _log "  ${ldsched} (${ldcron}) -> ${ldjob} args ${ldargs}"
  sched_upsert "${ldsched}" "${ldcron}" "${ldjob}" "${ldargs}"
done < <(read_live_diff_row)

# 8. Publish the declaration bundle (SIG-OPS-005: config without an image
#    roll) + report undeclared live triggers (listed, never deleted — the
#    P35.1b fleet-hygiene leg owns deletions).
_log "-- declaration bundle + undeclared-trigger report --"
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _plan "sig-ops live-diff --emit-declared | gcloud storage cp - ${DECLARED_GCS_URI}  # cadence.toml + fleet images, content-hashed"
  _plan "gcloud scheduler jobs list --location ${SIG_GCP_REGION}  # diffed against the declared trigger set; extras reported, not deleted"
else
  (cd "${_here}/../.." && uv run sig-ops live-diff --emit-declared) \
    | gcloud storage cp - "${DECLARED_GCS_URI}" --content-type=application/json
  _log "  declaration bundle published: ${DECLARED_GCS_URI} (cadence sha256 ${CADENCE_SHA256})"
  declared="$(read_declared_triggers | sort -u)"
  live="$(gcloud scheduler jobs list --location "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format='value(name)' | sort -u)"
  undeclared="$(comm -23 <(printf '%s\n' "${live}") <(printf '%s\n' "${declared}"))"
  if [ -n "${undeclared}" ]; then
    _log "  UNDECLARED live scheduler triggers (reported, not deleted — P35.1b owns the disposition):"
    printf '%s\n' "${undeclared}" | sed 's/^/    /'
  else
    _log "  live trigger set matches cadence.toml — no undeclared triggers"
  fi
fi

_log ""
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. Real apply is"
  _log "gate-pending on operator ADC (HG-12 / D-ACCT.1-1). Exit 0."
else
  _log "apply complete — probe sweep every 6h; per-source ingest jobs on their cadence.toml crons."
fi
