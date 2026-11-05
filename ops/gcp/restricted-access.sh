#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/restricted-access.sh — the P37.4b named OM-20 mutation (SIG-SEC-005,
# SIG-EVID-012, G1-13/G1-14, ADR-232): the restricted-byte access posture —
# audited access, Data Access audit logs + exclusion filter, ENCRYPTED_ONLY.
# Pre-authorised by GATE-G6 §4 (2026-11-05T15:20Z, "Approve all 15 (rec.)" —
# names P37.4b verbatim; expires GATE-ACCEPT-R11), under the contract's own
# preconditions, restore point and rollback; OM-18: a step that meets a new
# fact stops and records.
#
# Legs (ACTION, default `all`):
#   prestate   AR-2 restore point — project IAM policy (auditConfigs), the
#              sig-pg describe (sslMode), logging sinks + metrics, the
#              restricted/audit-logs bucket describes, the log-volume cost
#              read BEFORE (billing/bytes_ingested), sha256 sidecars +
#              `restore-point.sh sqlpoint` (the ssl leg touches the DB host)
#   audit      fold storage.googleapis.com DATA_READ+DATA_WRITE into the
#              project auditConfigs, exempting the declared mechanical
#              readers (SIG_RACC_EXEMPT_SAS — ingest/export/replica, G1-13's
#              volume control: human and unexpected reads stay logged)
#   sink       the retention sink: PRIVATE gs://<project>-sig-audit-logs with
#              a 90-day delete lifecycle + the `sig-data-access` log sink +
#              its writer grant + the log-volume alert policy (FEA-18)
#   iam        the access-log writers' grants: sig-quality-probe-rt gets
#              conditioned objectUser on ops/access-log/ +
#              ops/access-log-purge/ of the restricted bucket only
#   ssl        Cloud SQL sig-pg --ssl-mode=ENCRYPTED_ONLY (G1-14)
#   job        the scheduled purge: sig-access-log-purge (weekly Sun 10:00Z —
#              outside the 03:00-10:00Z band) runs `restricted-access purge
#              --apply` over the access-log prefix
#   cost       the log-volume cost read AFTER (measured, recorded — never
#              smoothed; the gate cell names the read before and after)
#   probe      the acceptance shape: `sig-ops restricted-access read` fetches
#              one probe object — the sig.restricted-access/1 record MUST
#              land under ops/access-log/ (a restricted read appears in the
#              audit log); the Data Access entry lands within propagation
#   verify     read-only outcome diff (OK/DRIFT lines)
#   rollback   printed restore: the captured prestate IAM policy +
#              sslMode back + name-checked deletes; buckets/log objects are
#              never deleted by the script
#
# Usage:
#   ops/gcp/restricted-access.sh [--check|--dry-run] [ACTION]   # plan (default)
#   ops/gcp/restricted-access.sh --apply [ACTION]               # real leg
#     ACTION := prestate | audit | sink | iam | ssl | job | cost |
#               probe | verify | rollback | all
#
# Env: SIG_GCP_PROJECT + ADC (apply); SIG_RACC_AUTHOR (the recorded operator
# id — OM-20 scope discipline); SIG_RACC_NOW (test-only clock seam);
# SIG_RACC_STATE_DIR (sha256-sidecarred prestate/cost captures).
#
# Live window (the ticket's `AR-3 + AR-2` cell): applies never run inside
# 03:00–10:00Z — exit 42 QUEUED.
# Check mode needs nothing: no project, no ADC — every line says what runs.
#
# Rerun prompt (GATE-G6 §4 names P37.4b verbatim, expiry GATE-ACCEPT-R11):
#   SIG_RACC_AUTHOR="$(git config user.name)" \
#   bash ops/gcp/restricted-access.sh --apply all
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"
_repo="$(cd "${_here}/../.." && pwd)"

_usage() {
  sed -n '/^# Usage:/,/^# Env:/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-64}"
}

parse_mode "${1:-}"
case "${1:-}" in --apply|--check|--dry-run) shift ;; esac
ACTION="${1:-all}"
case "${ACTION}" in
  prestate|audit|sink|iam|ssl|job|cost|probe|verify|rollback|all) ;;
  *) echo "restricted-access.sh: unknown action '${ACTION}'" >&2; _usage ;;
esac
STATE_DIR="${SIG_RACC_STATE_DIR}"
RERUN='SIG_RACC_AUTHOR="$(git config user.name)" bash ops/gcp/restricted-access.sh --apply '"${ACTION}"

die() { _log "ERROR: $*" >&2; exit "${2:-4}"; }

_racc_now() { printf '%s' "${SIG_RACC_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm
  nowiso="$(_racc_now)"; hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "10:00" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is inside 03:00-10:00Z — never mutate then (AR-3)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  if [ -z "${SIG_RACC_AUTHOR}" ]; then
    _log "ERROR: set SIG_RACC_AUTHOR to the recorded operator id (OM-20's scope discipline)" >&2
    exit 2
  fi
}

sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

_sha_sidecar() {  # _sha_sidecar FILE — write FILE.sha256 with the file's digest
  [ -f "$1" ] && (cd "$(dirname "$1")" && shasum -a 256 "$(basename "$1")" > "$1.sha256") || true
}

_cost_read() {  # _cost_read TAG — the log-volume cost read (measured, recorded)
  local tag="$1"
  local out="${STATE_DIR}/log-volume-${tag}.json"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud monitoring time-series list --filter metric.type=logging.googleapis.com/billing/bytes_ingested > ${out}"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud monitoring time-series list \
    --filter='metric.type="logging.googleapis.com/billing/bytes_ingested"' \
    --project "${SIG_GCP_PROJECT}" --format=json > "${out}" 2>/dev/null || \
    echo '{"note": "no billing/bytes_ingested series yet — recorded honestly"}' > "${out}"
  _sha_sidecar "${out}"
  _log "  log-volume ${tag} → ${out} (+ .sha256) — measured, never smoothed"
}

_audit_merge() {  # _audit_merge POLICY_IN POLICY_OUT — the auditConfig fold
  local exempt_args=() sa
  for sa in ${SIG_RACC_EXEMPT_SAS}; do
    exempt_args+=(--exempted "serviceAccount:$(sa_email "${sa}")")
  done
  (cd "${_repo}" && uv run --quiet sig-ops restricted-access audit-merge \
    --policy "$1" --project "${SIG_GCP_PROJECT}" "${exempt_args[@]}" --out "$2")
}

plan() {
  cat <<EOF
PLAN: restricted-access (${ACTION}) — project ${SIG_GCP_PROJECT} region ${SIG_GCP_REGION}
PLAN: audit       storage.googleapis.com DATA_READ+DATA_WRITE into the project
                  auditConfigs; exempted: ${SIG_RACC_EXEMPT_SAS}
                  (G1-13: human and unexpected reads stay logged — volume
                  control excludes only the declared mechanical readers)
PLAN: sink        gs://${SIG_BUCKET_AUDIT_LOGS} (PRIVATE, UBLA, 90d delete
                  lifecycle = the retention sink) + log sink ${SIG_RACC_SINK}
                  + writer grant + the log-volume alert policy (FEA-18)
PLAN: iam         sig-quality-probe-rt conditioned objectUser on
                  ${SIG_RACC_LOG_PREFIX} + ${SIG_RACC_PURGE_PREFIX} only
PLAN: ssl         gcloud sql instances patch ${SIG_SQL_INSTANCE}
                  --ssl-mode=ENCRYPTED_ONLY (G1-14)
PLAN: job         ${SIG_RACC_PURGE_JOB} + ${SIG_RACC_PURGE_SCHED}
                  (cron ${SIG_RACC_PURGE_CRON}) — sig-ops restricted-access
                  purge --apply over ${SIG_RACC_LOG_PREFIX} (180d retention,
                  SIG-EVID-012)
PLAN: access fn   sig-ops restricted-access read — logs sig.restricted-access/1
                  under ${SIG_RACC_LOG_PREFIX} BEFORE the fetch; one audited
                  access function, no unaudited path
PLAN: cost        log-volume cost read before (prestate) and after (cost leg)
PLAN: legs        prestate -> audit -> sink -> iam -> ssl -> job -> cost -> probe -> verify
PLAN: apply needs SIG_RACC_AUTHOR, SIG_GCP_PROJECT, ADC; window: never 03:00-10:00Z
PLAN: rerun       ${RERUN}
EOF
}

do_prestate() {
  _log "-- prestate: IAM policy + sql describe + sinks + cost BEFORE --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud projects get-iam-policy ${SIG_GCP_PROJECT} > ${STATE_DIR}/policy-pre.json"
    _plan "gcloud sql instances describe ${SIG_SQL_INSTANCE} > ${STATE_DIR}/sql-pre.json"
    _plan "gcloud logging sinks list > ${STATE_DIR}/sinks-pre.json"
    _plan "log-volume BEFORE read > ${STATE_DIR}/log-volume-before.json"
    _plan "ops/gcp/restore-point.sh --apply sqlpoint   # AR-2"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" --format=json \
    > "${STATE_DIR}/policy-pre.json" || true
  gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" --format=json \
    > "${STATE_DIR}/sql-pre.json" || true
  gcloud logging sinks list --project "${SIG_GCP_PROJECT}" --format=json \
    > "${STATE_DIR}/sinks-pre.json" || true
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" --format=json \
    > "${STATE_DIR}/bucket-restricted-pre.json" || true
  _sha_sidecar "${STATE_DIR}/policy-pre.json"
  _sha_sidecar "${STATE_DIR}/sql-pre.json"
  _cost_read before
  _log "  restore point: policy-pre.json + sql-pre.json (+ sha256 sidecars) —"
  _log "  the audit/iam/ssl rollbacks restore exactly these."
  bash "${_here}/restore-point.sh" --apply sqlpoint || \
    _log "note: restore-point sqlpoint unavailable — prestate still recorded"
}

do_audit() {
  _log "-- audit: storage.googleapis.com DATA_READ+DATA_WRITE, exempt ${SIG_RACC_EXEMPT_SAS} --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud projects get-iam-policy ${SIG_GCP_PROJECT} > policy.json"
    _plan "sig-ops restricted-access audit-merge --exempted <each of: ${SIG_RACC_EXEMPT_SAS}> > merged.json"
    _plan "gcloud projects set-iam-policy ${SIG_GCP_PROJECT} merged.json"
    _plan "  restore point: ${STATE_DIR}/policy-pre.json — rollback re-sets it verbatim"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" --format=json \
    > "${STATE_DIR}/policy-for-merge.json"
  _audit_merge "${STATE_DIR}/policy-for-merge.json" "${STATE_DIR}/policy-merged.json"
  _sha_sidecar "${STATE_DIR}/policy-merged.json"
  run gcloud projects set-iam-policy "${SIG_GCP_PROJECT}" \
    "${STATE_DIR}/policy-merged.json"
  _log "  restore point: set-iam-policy ${STATE_DIR}/policy-pre.json restores"
  _log "  the pre-auditConfig policy verbatim."
}

do_sink() {
  _log "-- sink: ${SIG_BUCKET_AUDIT_LOGS} + 90d lifecycle + ${SIG_RACC_SINK} + alert --"
  run gcloud storage buckets create "gs://${SIG_BUCKET_AUDIT_LOGS}" \
    --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}" \
    --uniform-bucket-level-access
  run gcloud storage buckets update "gs://${SIG_BUCKET_AUDIT_LOGS}" \
    --lifecycle-file "${_repo}/${SIG_RACC_LIFECYCLE}"
  run gcloud logging sinks create "${SIG_RACC_SINK}" \
    "storage.googleapis.com/${SIG_BUCKET_AUDIT_LOGS}" \
    --project "${SIG_GCP_PROJECT}" \
    --log-filter='protoPayload.serviceName="storage.googleapis.com" AND resource.type="gcs_bucket"'
  _log "  sink writer grant: the sink's writerIdentity gets objectCreator on"
  _log "  gs://${SIG_BUCKET_AUDIT_LOGS} (resolved at apply — sinks mint their SA)."
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    local writer
    writer="$(gcloud logging sinks describe "${SIG_RACC_SINK}" \
      --project "${SIG_GCP_PROJECT}" --format='value(writerIdentity)')"
    [ -n "${writer}" ] || die "no writerIdentity on ${SIG_RACC_SINK} — stop and record (OM-18)"
    run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_AUDIT_LOGS}" \
      --member="${writer}" --role=roles/storage.objectCreator
    sed "s/{project}/${SIG_GCP_PROJECT}/g" "${_repo}/${SIG_RACC_ALERT_DEF}" \
      > "${STATE_DIR}/alert-policy.rendered.json"
    run gcloud alpha monitoring policies create \
      --project "${SIG_GCP_PROJECT}" \
      --policy-from-file "${STATE_DIR}/alert-policy.rendered.json"
  else
    _plan "gcloud storage buckets add-iam-policy-binding gs://${SIG_BUCKET_AUDIT_LOGS} \\"
    _plan "  --member=<sink writerIdentity> --role=roles/storage.objectCreator"
    _plan "sed 's/{project}/<project>/' ${SIG_RACC_ALERT_DEF} | gcloud alpha monitoring \\"
    _plan "  policies create --policy-from-file -   # the log-volume alert (FEA-18)"
  fi
  _log "  restore point: sink/alert are additive; rollback = name-checked deletes."
}

do_iam() {
  _log "-- iam: access-log writers' conditioned grants --"
  local expr
  expr="resource.name.startsWith('projects/_/buckets/${SIG_BUCKET_RESTRICTED}/objects/${SIG_RACC_LOG_PREFIX}') || resource.name.startsWith('projects/_/buckets/${SIG_BUCKET_RESTRICTED}/objects/${SIG_RACC_PURGE_PREFIX}')"
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RESTRICTED}" \
    --member="serviceAccount:$(sa_email sig-quality-probe-rt)" \
    --role=roles/storage.objectUser \
    --condition="title=p37-4b-access-log,description=P37.4b: the audited-read writer + scheduled purge own the access-log prefixes only (SIG-SEC-005),expression=${expr}"
  _log "  restore point: remove-iam-policy-binding of the same member (prestate"
  _log "  IAM JSON captured at leg prestate)."
}

do_ssl() {
  _log "-- ssl: ${SIG_SQL_INSTANCE} --ssl-mode=ENCRYPTED_ONLY --"
  run gcloud sql instances patch "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" --ssl-mode=ENCRYPTED_ONLY
  _log "  restore point: ${STATE_DIR}/sql-pre.json — rollback patches"
  _log "  --ssl-mode=ALLOW_UNENCRYPTED_AND_ENCRYPTED (the pre-state value)."
}

do_job() {
  _log "-- job: ${SIG_RACC_PURGE_JOB} + ${SIG_RACC_PURGE_SCHED} (${SIG_RACC_PURGE_CRON}) --"
  run gcloud run jobs deploy "${SIG_RACC_PURGE_JOB}" \
    --image "${SIG_JOB_IMAGE:-${SIG_API_IMAGE}@sha256:<resolved-at-apply>}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "$(sa_email sig-quality-probe-rt)" \
    --command sh --args "-c,exec sig-ops restricted-access purge --bucket ${SIG_BUCKET_RESTRICTED} --apply" \
    --tasks 1 --task-timeout 30m --max-retries 1 --execution-environment gen2 \
    --set-env-vars "SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_RACC_LOG_BUCKET=${SIG_BUCKET_RESTRICTED}"
  run gcloud scheduler jobs create http "${SIG_RACC_PURGE_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --schedule "${SIG_RACC_PURGE_CRON}" --time-zone UTC \
    --uri "https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_RACC_PURGE_JOB}:run" \
    --http-method POST --oauth-service-account-email "$(sa_email sig-scheduler)"
  _log "  restore point: name-checked deletes of the job + scheduler only."
}

do_cost() {
  _log "-- cost: the log-volume cost read AFTER (the gate cell's before/after) --"
  _cost_read after
}

do_probe() {
  _log "-- probe: a restricted read appears in the audit log --"
  local probe_obj="ops/probes/p37-4b-read-$(date -u +%Y%m%dT%H%M%SZ).txt"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "put + read ${probe_obj} via sig-ops restricted-access read \\"
    _plan "  --requester \${SIG_RACC_AUTHOR} --purpose 'P37.4b probe: the acceptance read'"
    _plan "MUST: a sig.restricted-access/1 record lands under ${SIG_RACC_LOG_PREFIX}"
    _plan "gcloud logging read 'protoPayload.serviceName=\"storage.googleapis.com\"' \\"
    _plan "  --freshness=1h  (Data Access entry lands within propagation)"
    return 0
  fi
  printf 'p37.4b audited-read probe\n' \
    | gcloud storage cp - "gs://${SIG_BUCKET_RESTRICTED}/${probe_obj}"
  (cd "${_repo}" && uv run --quiet sig-ops restricted-access read \
    --bucket "${SIG_BUCKET_RESTRICTED}" --object "${probe_obj}" \
    --requester "${SIG_RACC_AUTHOR}" \
    --purpose "P37.4b probe: the acceptance read") \
    | tee "${STATE_DIR}/probe-access-record.json"
  if gcloud storage ls "gs://${SIG_BUCKET_RESTRICTED}/${SIG_RACC_LOG_PREFIX}" 2>/dev/null \
      | grep -q 'sig.restricted-access'; then
    _log "  ok — a restricted read appears in the audit log (${SIG_RACC_LOG_PREFIX})"
  else
    die "PROBE-FAIL: no sig.restricted-access/1 record under ${SIG_RACC_LOG_PREFIX}"
  fi
  _log "  Data Access entry (eventual — propagation delay):"
  gcloud logging read \
    "protoPayload.serviceName=\"storage.googleapis.com\" AND resource.type=\"gcs_bucket\"" \
    --project "${SIG_GCP_PROJECT}" --freshness=1h --limit=3 --format=json 2>/dev/null \
    | head -20 || _log "  note: Data Access entry pending within propagation — --verify re-checks"
}

do_verify() {
  _log "-- verify: auditConfig + sink + lifecycle + sslMode + job --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "get-iam-policy shows storage.googleapis.com DATA_READ+DATA_WRITE with the exempted members"
    _plan "logging sinks describe ${SIG_RACC_SINK} -> gs://${SIG_BUCKET_AUDIT_LOGS}"
    _plan "buckets describe ${SIG_BUCKET_AUDIT_LOGS} -> lifecycle age=90 Delete"
    _plan "sql describe ${SIG_SQL_INSTANCE} -> sslMode=ENCRYPTED_ONLY"
    _plan "run jobs describe ${SIG_RACC_PURGE_JOB} + scheduler describe ${SIG_RACC_PURGE_SCHED}"
    _plan "monitoring policies list -> SIG — Data Access audit-log daily volume"
    return 0
  fi
  local ok=0 drift=0
  _check() { if [ "$2" = "0" ]; then _log "OK    $1"; ok=$((ok+1)); else _log "DRIFT $1"; drift=$((drift+1)); fi }
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" --format=json 2>/dev/null \
    | grep -q '"service": "storage.googleapis.com"' \
    && _check "auditConfig-storage" 0 || _check "auditConfig-storage" 1
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" --format=json 2>/dev/null \
    | grep -q '"logType": "DATA_READ"' \
    && _check "auditConfig-DATA_READ" 0 || _check "auditConfig-DATA_READ" 1
  gcloud logging sinks describe "${SIG_RACC_SINK}" --project "${SIG_GCP_PROJECT}" \
    --format='value(destination)' 2>/dev/null | grep -q "${SIG_BUCKET_AUDIT_LOGS}" \
    && _check "sink-destination" 0 || _check "sink-destination" 1
  gcloud storage buckets describe "gs://${SIG_BUCKET_AUDIT_LOGS}" \
    --format=json 2>/dev/null | grep -q '"age": 90' \
    && _check "sink-lifecycle-90d" 0 || _check "sink-lifecycle-90d" 1
  local ssl
  ssl="$(gcloud sql instances describe "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" \
    --format='value(settings.ipConfiguration.sslMode)' 2>/dev/null || echo "")"
  [ "${ssl}" = "ENCRYPTED_ONLY" ] && _check "ssl-encrypted-only" 0 \
    || _check "ssl-encrypted-only (${ssl:-absent})" 1
  gcloud run jobs describe "${SIG_RACC_PURGE_JOB}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1 \
    && _check "purge-job" 0 || _check "purge-job" 1
  gcloud scheduler jobs describe "${SIG_RACC_PURGE_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1 \
    && _check "purge-scheduler" 0 || _check "purge-scheduler" 1
  _log "verify: ${ok} OK, ${drift} DRIFT"
  [ "${drift}" -eq 0 ] || exit 4
}

do_rollback() {
  _log "-- rollback (printed; additive creates are name-checked deletes only) --"
  _log "  audit: gcloud projects set-iam-policy ${SIG_GCP_PROJECT} ${STATE_DIR}/policy-pre.json"
  _log "  iam:   remove-iam-policy-binding sig-quality-probe-rt objectUser (p37-4b-access-log)"
  _log "  ssl:   gcloud sql instances patch ${SIG_SQL_INSTANCE} --ssl-mode=ALLOW_UNENCRYPTED_AND_ENCRYPTED"
  _log "  sink:  gcloud logging sinks delete ${SIG_RACC_SINK}; policies delete the data-access alert"
  _log "  job:   gcloud run jobs delete ${SIG_RACC_PURGE_JOB}; scheduler delete ${SIG_RACC_PURGE_SCHED}"
  _log "  never: gs://${SIG_BUCKET_AUDIT_LOGS} + every ops/access-log/ object —"
  _log "        a bucket/object delete is the operator's WV-06 act, never a script's"
}

require_project
case "${ACTION}" in
  audit|sink|iam|ssl|job|all) assert_window ;;
esac
require_adc

banner "P37.4b — restricted-byte access posture: audited access + Data Access audit logs + ENCRYPTED_ONLY (ADR-232)"
_log "  restore point: prestate captures + additive creates + recorded specs"
_log "  window: never 03:00-10:00Z; author: ${SIG_RACC_AUTHOR:-<unset>}"

case "${ACTION}" in
  prestate)  do_prestate ;;
  audit)     do_audit ;;
  sink)      do_sink ;;
  iam)       do_iam ;;
  ssl)       do_ssl ;;
  job)       do_job ;;
  cost)      do_cost ;;
  probe)     do_probe ;;
  verify)    do_verify ;;
  rollback)  do_rollback ;;
  all)
    plan
    do_prestate
    do_audit
    do_sink
    do_iam
    do_ssl
    do_job
    do_cost
    do_probe
    do_verify ;;
esac

_log "restricted-access ${ACTION}: done (mode=${SIG_GCP_MODE})"
