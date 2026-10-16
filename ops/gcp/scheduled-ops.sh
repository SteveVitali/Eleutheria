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
# P35.1c (G1-TRIM B-13=a, ticket 291a) adds the consolidated trigger shape:
#   * `[dispatcher]` + `[[retire_triggers]]` in cadence.toml — when declared,
#     ONE hourly Cloud Scheduler trigger (`sig-sched-due`) fires ONE Cloud Run
#     job that evaluates the due set and enqueues each due job via jobs:run.
#     Per-row triggers named `retired` on the list are never reconciled here
#     (expected absent; the consolidation leg owns the deletes — the reconcile
#     reports them distinctly, never deletes, never recreates); a row's
#     `state = "paused"` rides the due-set, not a trigger pause. A per-row
#     scheduler missing from the retire list under this shape is a refusal —
#     the name-checked set covers every row (`retire_trigger_lint` enforces).
#   * `--shape per-source` — the rollback map: reconciles EVERY per-row
#     trigger from the same cadence rows (retire list ignored, paused rows
#     created/held PAUSED) and skips the dispatcher deploy entirely. The
#     dispatcher itself is never deleted here — the consolidation leg owns
#     its teardown.
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
# P35.1c: `--shape per-source` is the rollback map — every per-row trigger is
# reconciled from its cadence row and the dispatcher legs are skipped. The
# default `declared` shape follows cadence.toml's [dispatcher] table.
SIG_SHAPE="declared"
_prev=""
for _arg in "$@"; do
  case "${_prev}" in
    --shape) SIG_SHAPE="${_arg}" ;;
  esac
  case "${_arg}" in
    --paused) SIG_CREATE_PAUSED=1 ;;
  esac
  _prev="${_arg}"
done
case "${SIG_SHAPE}" in
  declared|per-source) ;;
  *) _log "ERROR: unknown --shape '${SIG_SHAPE}' (declared | per-source)" >&2; exit 64 ;;
esac
[ "${SIG_CREATE_PAUSED}" = "1" ] && _log "R6 create-paused: every NEW trigger is paused on create" || true
[ "${SIG_SHAPE}" = "per-source" ] && _log "shape: per-source (rollback — every per-row trigger reconciled)" || true

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
# (id|cadence|cron|job|scheduler|existing|extra-secrets|task_timeout|state).
# `task_timeout` (P35.6) is a per-row duration string; empty = 60m default.
# `state` (P35.1c) is the row-level posture the retired trigger's pause
# carried — "paused" rows stay inert until their wave resume flips the row.
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
                s.get("state", "enabled"),
            ]
        )
    )
PY
  )
}

# Read the grouped-batch table
# (id|cadence|cron|job|scheduler|member-count|task_timeout|state) —
# P26.16 (SOURCES.15): the GL-GATE-07 rights batch groups its newly-green
# camera-registry sources under ~10 sig-ingest-camreg-batch-* jobs; each batch
# job runs `scheduled-ingest --batch <id>` which appends one ops/runs row PER
# MEMBER source. `task_timeout` (P35.6) is a per-row duration string; empty =
# the 36h default (ADR-107's batch-05 ceiling). `state` (P35.1c) is the
# row-level pause posture the due-set honours.
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
                b.get("state", "enabled"),
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

# Read the [dispatcher] declaration (job|scheduler|cron|sa_class|task_timeout) —
# P35.1c: the single hourly trigger's job. Empty output when undeclared.
read_dispatcher_row() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
d = doc.get("dispatcher")
if d:
    print(
        "|".join(
            [
                d["job"],
                d["scheduler"],
                d["cron"],
                d.get("sa_class", ""),
                d.get("task_timeout", ""),
            ]
        )
    )
PY
  )
}

# Read the [[retire_triggers]] map (name|disposition) — P35.1c's name-checked
# set: retired = consolidated into the dispatcher (expected absent); kept-*
# stays live/manual.
read_retire_map() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
for r in doc.get("retire_triggers", []):
    print("|".join([r["name"], r.get("disposition", "")]))
PY
  )
}

# Emit one job name per due-target row — the jobs the dispatcher invokes
# via jobs:run (P35.1c). Paused rows, kept-declared-pin and kept-manual
# names are never dispatched, so they are bound no dispatcher invoker.
due_target_jobs() {
  (cd "${_here}/../.." && uv run python - "${_here}/../cadence.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
retire = {
    r["name"]: r.get("disposition", "") for r in doc.get("retire_triggers", [])
}
for row in doc.get("sources", []) + doc.get("batches", []):
    sched = row.get("scheduler", "")
    if row.get("state", "enabled") == "paused":
        continue
    if retire.get(sched, "").startswith("kept"):
        continue
    print(row["job"])
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
# live-diff + the dispatcher under the consolidated shape) — the allow-list
# the undeclared-trigger report diffs live against. Under the dispatcher
# shape, retired per-row names are not declared triggers — they're reported
# through the retire map instead; kept-declared-pin names stay declared.
read_declared_triggers() {
  (cd "${_here}/../.." && SIG_SHAPE="${SIG_SHAPE}" uv run python - "${_here}/../cadence.toml" <<'PY'
import os
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
disp = doc.get("dispatcher") or {}
dispatched = bool(disp) and os.environ.get("SIG_SHAPE") != "per-source"
retire = {
    r["name"]: r.get("disposition", "") for r in doc.get("retire_triggers", [])
}
names = [doc.get("probes", {}).get("scheduler")]
names += [s.get("scheduler") for s in doc.get("sources", [])]
names += [b.get("scheduler") for b in doc.get("batches", [])]
names += [m.get("scheduler") for m in doc.get("maintenance", [])]
ld = doc.get("live_diff") or {}
names.append(ld.get("scheduler"))
if dispatched:
    names.append(disp.get("scheduler"))
for n in names:
    if not n:
        continue
    if dispatched and retire.get(n) == "retired":
        continue  # consolidated — expected absent, reported via the retire map
    print(n)
PY
  )
}

# Resolve the consolidated trigger shape (P35.1c): the [dispatcher] row and
# the [[retire_triggers]] name map. DISPATCHED=1 under the declared shape when
# a [dispatcher] table exists; --shape per-source forces the rollback map.
DUE_JOB="" DUE_SCHED="" DUE_CRON="" DUE_SA_CLASS="" DUE_TIMEOUT=""
while IFS='|' read -r djob dsched dcron dsac dtimeout; do
  [ -z "${djob}" ] && continue
  DUE_JOB="${djob}"; DUE_SCHED="${dsched}"; DUE_CRON="${dcron}"
  DUE_SA_CLASS="${dsac}"; DUE_TIMEOUT="${dtimeout}"
done < <(read_dispatcher_row)
# The retire map as `name|disposition` lines (bash 3.2 — no assoc arrays);
# `retire_disp_of` is the single lookup the per-row loops use.
RETIRE_MAP="$(read_retire_map)"
retire_disp_of() {
  printf '%s\n' "${RETIRE_MAP}" | awk -F'|' -v n="$1" '$1==n{print $2; exit}'
}
DISPATCHED=0
if [ "${SIG_SHAPE}" != "per-source" ] && [ -n "${DUE_JOB}" ]; then
  DISPATCHED=1
fi
# The dispatcher job's runtime identity — sa_class → the class SA email.
DUE_SA_EMAIL=""
if [ -n "${DUE_JOB}" ]; then
  case "${DUE_SA_CLASS}" in
    ingest) DUE_SA_EMAIL="${SIG_INGEST_SA_EMAIL}" ;;
    probe)  DUE_SA_EMAIL="${SIG_PROBE_SA_EMAIL}" ;;
    *) _log "ERROR: [dispatcher].sa_class '${DUE_SA_CLASS}' has no declared SA mapping" >&2; exit 2 ;;
  esac
fi
# One helper for both per-row loops: is this scheduler retired under the
# declared shape? `retired` → never reconciled; missing from the list → a
# refusal (the name-checked set must cover every row); kept-* → reconciled.
row_trigger_retired() {
  local sched="$1" disp
  disp="$(retire_disp_of "${sched}")"
  if [ -z "${disp}" ]; then
    _log "ERROR: ${sched} is not on [[retire_triggers]] under the dispatcher shape — the retire list must name every per-row scheduler (sig-ops cadence --check enforces)" >&2
    exit 2
  fi
  [ "${disp}" = "retired" ]
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
#    Under the P35.1c dispatcher shape the jobs still deploy — the dispatcher
#    invokes them — but their per-row triggers are consolidated away; the row's
#    `state` rides the due-set. Under per-source shape (rollback) every
#    trigger is reconciled, and a declared-paused row's trigger is created
#    then held PAUSED (its own wave resume enables it, never this script).
_log "-- per-source reingestion (run rows → gs://…-sig-restricted/ops/runs/) --"
while IFS='|' read -r src cad cron job sched existing extra ttimeout sstate; do
  [ -z "${src}" ] && continue
  secrets="SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest"
  [ -n "${extra}" ] && secrets="${secrets},${extra}"
  _log "  ${src} (${cad} ${cron}${sstate:+ state=${sstate}}) -> ${job}"
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
  if [ "${DISPATCHED}" = "1" ] && row_trigger_retired "${sched}"; then
    _log "    trigger ${sched} → consolidated into ${DUE_SCHED} (retired on [[retire_triggers]] — never reconciled here)"
    continue
  fi
  if [ "${existing}" = "1" ]; then
    # The scheduler trigger already exists (muckrock, P25.7 d5) — verify,
    # never duplicate. The JOB above is still upserted to the run-row wrapper.
    # Under the per-source shape (P35.1c's rollback map) an ABSENT existing
    # trigger is recreated from this cadence row — the consolidation deleted
    # it and the declared map restores it; under the declared shape its
    # absence stays a hard error (it was created out-of-band, P25.7).
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      if [ "${SIG_SHAPE}" = "per-source" ]; then
        _plan "verify ${sched} exists and invokes ${job} on '${cron}'  (existing trigger — recreate from the cadence row if absent, the rollback map)"
      else
        _plan "verify ${sched} exists and invokes ${job} on '${cron}'  (existing trigger — not recreated)"
      fi
    else
      if gcloud scheduler jobs describe "${sched}" \
          --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
        _log "  verified existing ${sched} (${cron}) -> ${job}"
      elif [ "${SIG_SHAPE}" = "per-source" ]; then
        _log "  existing ${sched} is absent — recreating from the cadence row (the rollback map)"
        sched_upsert "${sched}" "${cron}" "${job}"
      else
        _log "ERROR: ${sched} is marked existing in cadence.toml but is absent" >&2
        exit 1
      fi
    fi
    continue
  fi
  sched_upsert "${sched}" "${cron}" "${job}"
  # A declared-paused row's trigger is held PAUSED — the row's own wave
  # resume enables it, never this script (same rule as maintenance rows).
  if [ "${sstate:-enabled}" = "paused" ]; then
    sched_set_state "${sched}" paused
  fi
done < <(read_cadence_rows)

# 4. Grouped batches ([[batches]] — P26.16 GL-GATE-07). One job per batch runs
#    `scheduled-ingest --batch <id>`; the wrapper appends one ops/runs row per
#    member source. 36h ceiling (ADR-107): batch-05 carries the ~1.37M-record OSM
#    mirror, and the live batch jobs already run 36h (P31.4 aligned this script,
#    which used to say 120m, with the deployed jobs so a re-apply cannot shrink it).
_log "-- grouped batches (run rows per member → ops/runs/<source>/) --"
while IFS='|' read -r bid bcad bcron bjob bsched bcount btimeout bstate; do
  [ -z "${bid}" ] && continue
  _log "  batch ${bid} (${bcount} member sources, ${bcad} ${bcron}${bstate:+ state=${bstate}}) -> ${bjob} (task-timeout ${btimeout:-36h})"
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
  if [ "${DISPATCHED}" = "1" ] && row_trigger_retired "${bsched}"; then
    _log "    trigger ${bsched} → consolidated into ${DUE_SCHED} (retired on [[retire_triggers]] — never reconciled here)"
    continue
  fi
  sched_upsert "${bsched}" "${bcron}" "${bjob}"
  if [ "${bstate:-enabled}" = "paused" ]; then
    sched_set_state "${bsched}" paused
  fi
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

# 7b. The due dispatcher ([dispatcher] — P35.1c / G1-TRIM B-13=a): ONE Cloud
#    Run job evaluating the due set + ONE hourly trigger, replacing the
#    per-row trigger set. The job runs `sig-ops dispatch-due` against the
#    published declaration bundle (SIG_OPS_DECLARED_GCS rides JOB_ENV — config
#    without an image roll), writes its run row to the restricted bucket, and
#    enqueues each due job via jobs:run — so its runtime SA (sa_class) holds
#    roles/run.invoker on every due-target job, bound name-checked below.
#    `state = "paused"` rows and kept-declared-pin names are never due —
#    they are bound no invoker (the dispatcher never calls them). Under
#    `--shape per-source` this whole section is skipped: the dispatcher is
#    the consolidation's shape, not the rollback's.
if [ "${DISPATCHED}" = "1" ]; then
  _log "-- due dispatcher (P35.1c — one hourly trigger → sig-ops dispatch-due) --"
  # The dispatcher needs NO Cloud SQL and NO secrets — it evaluates the
  # declaration and calls jobs:run; its only write is the run row to the
  # restricted bucket (the class SA's bucket grants cover it). Same env the
  # consolidation leg deploys.
  DUE_ENV="SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_GCP_REGION=${SIG_GCP_REGION},SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED},SIG_OPS_CADENCE=/app/ops/cadence.toml,SIG_OPS_CADENCE_SHA256=${CADENCE_SHA256},SIG_OPS_DECLARED_GCS=${DECLARED_GCS_URI}"
  run gcloud run jobs deploy "${DUE_JOB}" \
    --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${DUE_SA_EMAIL}" \
    --command sh \
    --args "-c,exec sig-ops dispatch-due" \
    --tasks 1 --task-timeout "${DUE_TIMEOUT:-30m}" --max-retries 0 \
    --set-env-vars "${DUE_ENV}"
  run gcloud run jobs add-iam-policy-binding "${DUE_JOB}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --member="serviceAccount:${SIG_SCHEDULER_SA_EMAIL}" \
    --role=roles/run.invoker
  # The dispatcher's SA invokes each due job — the same jobs:run call the
  # retired triggers signed as sig-scheduler. Bound name-checked on the
  # due-target set (non-paused, non-kept rows); declared on
  # [[job_invoker]] in iam_identities.toml for the jobs-iam leg's diff.
  while IFS='|' read -r tjob _rest; do
    [ -z "${tjob}" ] && continue
    run gcloud run jobs add-iam-policy-binding "${tjob}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --member="serviceAccount:${DUE_SA_EMAIL}" \
      --role=roles/run.invoker
  done < <(due_target_jobs)
  sched_upsert "${DUE_SCHED}" "${DUE_CRON}" "${DUE_JOB}"
fi

# 8. Publish the declaration bundle (SIG-OPS-005: config without an image
#    roll) + report undeclared live triggers (listed, never deleted — the
#    P35.1b fleet-hygiene leg owns deletions). Under the dispatcher shape a
#    retired name still live is NOT undeclared drift — it is a declared
#    retirement pending the consolidation leg's name-checked deletes, and is
#    reported under its own heading.
_log "-- declaration bundle + undeclared-trigger report --"
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _plan "sig-ops live-diff --emit-declared | gcloud storage cp - ${DECLARED_GCS_URI}  # cadence.toml + fleet images, content-hashed"
  _plan "gcloud scheduler jobs list --location ${SIG_GCP_REGION}  # diffed against the declared trigger set; retired-pending vs undeclared reported, nothing deleted"
else
  (cd "${_here}/../.." && uv run sig-ops live-diff --emit-declared) \
    | gcloud storage cp - "${DECLARED_GCS_URI}" --content-type=application/json
  _log "  declaration bundle published: ${DECLARED_GCS_URI} (cadence sha256 ${CADENCE_SHA256})"
  declared="$(read_declared_triggers | sort -u)"
  retired="$(read_retire_map | awk -F'|' '$2=="retired"{print $1}' | sort -u)"
  live="$(gcloud scheduler jobs list --location "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format='value(name)' | sort -u)"
  extras="$(comm -23 <(printf '%s\n' "${live}") <(printf '%s\n' "${declared}"))"
  pending="$(comm -12 <(printf '%s\n' "${extras}") <(printf '%s\n' "${retired}"))"
  undeclared="$(comm -23 <(printf '%s\n' "${extras}") <(printf '%s\n' "${retired}"))"
  if [ -n "${pending}" ]; then
    _log "  DECLARED-RETIRED live triggers pending consolidation (name-checked; the dispatcher-consolidation leg deletes them, never this script):"
    printf '%s\n' "${pending}" | sed 's/^/    /'
  fi
  if [ -n "${undeclared}" ]; then
    _log "  UNDECLARED live scheduler triggers (reported, not deleted — P35.1b owns the disposition):"
    printf '%s\n' "${undeclared}" | sed 's/^/    /'
  fi
  if [ -z "${pending}" ] && [ -z "${undeclared}" ]; then
    _log "  live trigger set matches cadence.toml — no undeclared or pending-retired triggers"
  fi
fi

_log ""
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. Real apply is"
  _log "gate-pending on operator ADC (HG-12 / D-ACCT.1-1). Exit 0."
else
  _log "apply complete — probe sweep every 6h; per-source ingest jobs on their cadence.toml crons."
fi
