#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/evidence-store.sh — P37.3 (R11-OPS-04, SIG-STORE-048, ADR-177): the
# ONE named OM-14/OM-20 mutation set — the evidence-bucket retention-policy
# write + the off-instance replica/cross-project copy jobs. Pre-authorised by
# GATE-G6 §4 (2026-11-05T15:20Z, "Approve all 15 (rec.)" — names P37.3
# verbatim; expires GATE-ACCEPT-R11), under the contract's own preconditions,
# restore point and rollback; OM-18: a step that meets a new fact stops and
# records.
#
# Legs (ACTION, default `all`):
#   prestate   AR-2 restore point — bucket describe/IAM/lifecycle/retention
#              JSON + the ingest jobs' volume specs, sha256 sidecars
#   bucket     create gs://<project>-sig-evidence (PRIVATE, UBLA, versioning)
#              + retention policy 365 d UNLOCKED (B-14 = a — takedowns and the
#              WV-06 deletion path stay possible; lock only after review)
#   captures   copy evidence/captures/ from sig-restricted → sig-evidence
#              (server-side copy; source objects NEVER deleted — append-only;
#              the repoint leg makes the new bucket the write target)
#   iam        the evidence/DR grants + sig-replica-rt: sig-ingest-rt
#              objectCreator+objectViewer + conditioned objectUser under
#              evidence/captures/ on sig-evidence (the ADR-201 shape carried);
#              sig-quality-probe-rt conditioned read; sig-probe-rt
#              legacyBucketReader on both new buckets; sig-replica-rt viewer
#              on sig-restricted/sig-backups + creator+viewer on the DR bucket
#   dr-bucket  create gs://<project>-sig-restricted-dr (PRIVATE, UBLA,
#              versioning, dual-region US-CENTRAL1+US-EAST1 = nam4)
#   jobs       the two copy jobs + their schedulers (sig-restricted-replica
#              weekly Sun 09:00Z; sig-pg-export-copy monthly day-2 14:30Z —
#              created ENABLED: the jobs are the named mutation's deliverable)
#   repoint    every ingest job's `captures` volume → sig-evidence (refuses
#              while any ingest execution is RUNNING — fail-closed)
#   probe      acceptance: a retention-delete attempt on a fresh probe object
#              MUST fail (unlocked retention still forbids delete); the
#              restricted→evidence copy parity count; replica `verify`
#   poststate  read-back capture + `verify`
#   verify     read-only outcome diff (or --from-state DIR), OK/DRIFT lines
#   rollback   removes ONLY what this script created (the two new buckets are
#              left with their retention policy — a delete is the operator's
#              WV-06 act, never a script's); repoint rollback restores the
#              restricted mount from the recorded prestate
#
# Restore points (AR-2): the IAM policies are exported before any grant; the
# captures copy is additive (the source stays under versioning + its 90-day
# noncurrent lifecycle); every job update records its prior volume spec so
# `repoint`-rollback restores exactly it.
#
# Usage:
#   ops/gcp/evidence-store.sh [--check|--dry-run] [ACTION]   # plan only
#   ops/gcp/evidence-store.sh --apply [ACTION]               # the mutation(s)
#   ops/gcp/evidence-store.sh --verify [--from-state DIR]    # read-only diff
#
# Env: SIG_GCP_PROJECT + ADC (apply); SIG_EVSTORE_AUTHOR (OM-20's recorded
# operator id); SIG_BACKUP_PROJECT (the second project for the export-copy
# job — absent → the export-copy leg records QUEUED, the rest still run);
# SIG_EVSTORE_NOW (test-only clock seam).
#
# Exit: 0 ok · 2 usage/env · 3 unarmed · 4 verify drift · 42 QUEUED window.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

RERUN="implement-spec spec=docs/tickets/421_P37.3__evidence-store-hardening.md live_verification=true"
STATE_DIR="${SIG_EVSTORE_STATE_DIR}"
CAPTURES_PREFIX="evidence/captures"
DUAL_REGION="nam4"   # us-central1 + us-east1 — the contract's dual-region choice

_usage() {
  sed -n '/^# Usage:/,/^set -euo pipefail/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'
  exit "${1:-64}"
}

MODE="check"; ACTION="all"; FROM_STATE=""
case "${1:-}" in
  --apply)  MODE="apply"; ACTION="${2:-all}"; FROM_STATE="${4:-}" ;;
  --verify) MODE="verify"; FROM_STATE="${3:-}" ;;
  --check|--dry-run|"") MODE="check"; ACTION="${2:-all}" ;;
  -h|--help) _usage 0 ;;
  *) echo "evidence-store.sh: unknown mode '${1:-}'" >&2; _usage 64 ;;
esac
export SIG_GCP_MODE="$MODE"

require_project
EVIDENCE_DIR="${STATE_DIR}/$(date -u +%Y%m%dT%H%M%SZ)"
INGEST_JOBS_FILE=""  # filled by the repoint leg's live read

die()  { _log "ERROR: $*" >&2; exit "${2:-4}"; }
_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}
_capture() {  # _capture <rel> <cmd...> — read-only JSON + sha256 sidecar
  local out="${EVIDENCE_DIR}/$1"; shift
  mkdir -p "$(dirname "${out}")"
  _log "+ (capture) $* > ${out}"
  if ! "$@" > "${out}" 2> "${out}.err"; then
    _log "   capture failed (recorded): $*"
    return 0
  fi
  printf '%s  %s\n' "$(_sha256 "${out}")" "${out}" >> "${EVIDENCE_DIR}/sha256s.txt"
}

_now() { printf '%s' "${SIG_EVSTORE_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"; }

assert_window() {  # never inside the daily 03:00-10:00Z QA metadata band
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local nowiso hhmm
  nowiso="$(_now)"; hhmm="${nowiso:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "10:00" ]]; then
    _log "QUEUED (exit 42): ${nowiso} is inside 03:00-10:00Z — the daily band"
    _log "every ops mutation holds outside of (AR-3 + AR-2)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  [ -n "${SIG_EVSTORE_AUTHOR}" ] || \
    die "set SIG_EVSTORE_AUTHOR to the recorded operator id (OM-20 scope discipline)" 2
}

# ---------------------------------------------------------------------------
sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

ingest_jobs() {  # the jobs whose captures volume must repoint (live read)
  gcloud run jobs list --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --format='value(metadata.name)' \
    --filter='metadata.name ~ ^sig-(ingest|replay-ingest|sink-bench)' 2>/dev/null
}

no_ingest_running() {  # fail-closed: refuse if the running-set cannot be read
  local running
  if ! running="$(gcloud run jobs executions list --project "${SIG_GCP_PROJECT}" \
      --region "${SIG_GCP_REGION}" --filter='status.running:true' \
      --format='value(spec.jobName)' 2>/dev/null)"; then
    _log "cannot prove no ingest execution runs — refusing the repoint (fail-closed)"
    return 1
  fi
  if printf '%s\n' "${running}" | grep -q 'sig-'; then
    _log "ingest executions running: ${running} — repoint QUEUED, not forced"
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------------------
leg_prestate() {
  banner "evidence-store prestate (AR-2 restore point)"
  mkdir -p "${EVIDENCE_DIR}"
  run _log "prestate → ${EVIDENCE_DIR}"
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    _capture buckets/restricted.json gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" --format=json
    _capture buckets/backups.json   gcloud storage buckets describe "gs://${SIG_BUCKET_BACKUPS}" --format=json
    _capture iam/restricted.json    gcloud storage buckets get-iam-policy "gs://${SIG_BUCKET_RESTRICTED}"
    _capture iam/backups.json       gcloud storage buckets get-iam-policy "gs://${SIG_BUCKET_BACKUPS}"
    _capture jobs/ingest-names.txt  ingest_jobs
    _log "prestate captured: $(find "${EVIDENCE_DIR}" -name '*.json' -o -name '*.txt' | wc -l | tr -d ' ') files + sha256s.txt"
  else
    _plan "gcloud storage buckets describe/get-iam-policy → ${EVIDENCE_DIR}/"
    _plan "capture ingest-job volume specs → jobs/ (the repoint restore point)"
  fi
}

leg_bucket() {
  banner "evidence bucket + 365d unlocked retention (B-14 = a)"
  run gcloud storage buckets create "gs://${SIG_BUCKET_EVIDENCE}" \
    --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}" \
    --uniform-bucket-level-access
  run gcloud storage buckets update "gs://${SIG_BUCKET_EVIDENCE}" --versioning
  run gcloud storage buckets update "gs://${SIG_BUCKET_EVIDENCE}" \
    --retention-period "${SIG_EVSTORE_RETENTION_DAYS}d"
  _log "  restore point: the bucket is NEW (nothing overwritten); removal is"
  _log "  the operator's WV-06 act — the script's rollback never deletes it."
}

leg_captures() {
  banner "captures copy → sig-evidence (additive; source never deleted)"
  run gcloud storage cp -r \
    "gs://${SIG_BUCKET_RESTRICTED}/${CAPTURES_PREFIX}" \
    "gs://${SIG_BUCKET_EVIDENCE}/evidence/"
  _log "  verify: object-count parity is asserted by leg 'probe'."
}

leg_drbucket() {
  banner "dual-region replica bucket"
  run gcloud storage buckets create "gs://${SIG_BUCKET_RESTRICTED_DR}" \
    --project "${SIG_GCP_PROJECT}" --location "${DUAL_REGION}" \
    --uniform-bucket-level-access
  run gcloud storage buckets update "gs://${SIG_BUCKET_RESTRICTED_DR}" --versioning
}

leg_iam() {
  banner "IAM — ingest without delete; replica SA; conditioned grants"
  local cond_expr_ingest cond_expr_exec
  cond_expr_ingest="resource.name.startsWith('projects/_/buckets/${SIG_BUCKET_EVIDENCE}/objects/${CAPTURES_PREFIX}/')"
  cond_expr_exec="${cond_expr_ingest}"
  run gcloud iam service-accounts create sig-replica-rt \
    --display-name "sig replica jobs runtime" --project "${SIG_GCP_PROJECT}"
  # sig-ingest-rt on sig-evidence: create + read; the ONE conditioned
  # objectUser (create+delete verbs) under evidence/captures/ for the OCFL
  # inventory-head rewrite — the retention policy makes a delete fail anyway.
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_EVIDENCE}" \
    --member="serviceAccount:$(sa_email sig-ingest-rt)" --role=roles/storage.objectCreator
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_EVIDENCE}" \
    --member="serviceAccount:$(sa_email sig-ingest-rt)" --role=roles/storage.objectViewer
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_EVIDENCE}" \
    --member="serviceAccount:$(sa_email sig-ingest-rt)" --role=roles/storage.objectUser \
    --condition="title=p37-3-capture-rewrite,description=P37.3/ADR-201 carried: OCFL inventory-head rewrite under evidence/captures/ only (SIG-STORE-048),expression=${cond_expr_ingest}"
  # exec host: conditioned read on the moved capture store.
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_EVIDENCE}" \
    --member="serviceAccount:$(sa_email sig-quality-probe-rt)" --role=roles/storage.objectViewer \
    --condition="title=p37-3-captures-readonly,description=P37.3: the exec host reads the capture store under evidence/captures/ only,expression=${cond_expr_exec}"
  # live-diff bucket leg reads declared buckets.
  for b in "${SIG_BUCKET_EVIDENCE}" "${SIG_BUCKET_RESTRICTED_DR}"; do
    run gcloud storage buckets add-iam-policy-binding "gs://${b}" \
      --member="serviceAccount:$(sa_email sig-probe-rt)" --role=roles/storage.legacyBucketReader
  done
  # sig-replica-rt: read the two sources; create+read on the DR target.
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RESTRICTED}" \
    --member="serviceAccount:$(sa_email sig-replica-rt)" --role=roles/storage.objectViewer
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_BACKUPS}" \
    --member="serviceAccount:$(sa_email sig-replica-rt)" --role=roles/storage.objectViewer
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RESTRICTED_DR}" \
    --member="serviceAccount:$(sa_email sig-replica-rt)" --role=roles/storage.objectCreator
  run gcloud storage buckets add-iam-policy-binding "gs://${SIG_BUCKET_RESTRICTED_DR}" \
    --member="serviceAccount:$(sa_email sig-replica-rt)" --role=roles/storage.objectViewer
  _log "  restore point: the exported prestate IAM JSON (leg prestate);"
  _log "  rollback = remove-iam-policy-binding of the same members."
}

leg_jobs() {
  banner "the off-instance copy jobs + schedulers"
  run gcloud run jobs deploy "${SIG_REPLICA_JOB}" \
    --image "${SIG_JOB_IMAGE:-${SIG_API_IMAGE}@sha256:<resolved-at-apply>}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "$(sa_email sig-replica-rt)" \
    --command sh --args "-c,exec sig-ops restricted-replica run" \
    --tasks 1 --task-timeout 2h --max-retries 1 --execution-environment gen2 \
    --set-env-vars "SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_REPLICA_SOURCE=${SIG_BUCKET_RESTRICTED},SIG_REPLICA_DEST=${SIG_BUCKET_RESTRICTED_DR}"
  run gcloud scheduler jobs create http "${SIG_REPLICA_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --schedule "0 9 * * 0" --time-zone UTC \
    --uri "https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_REPLICA_JOB}:run" \
    --http-method POST --oauth-service-account-email "$(sa_email sig-scheduler)"
  if [ -n "${SIG_BACKUP_PROJECT}" ]; then
    run gcloud run jobs deploy "${SIG_EXPORT_COPY_JOB}" \
      --image "${SIG_JOB_IMAGE:-${SIG_API_IMAGE}@sha256:<resolved-at-apply>}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --service-account "$(sa_email sig-replica-rt)" \
      --command sh --args "-c,exec sig-ops pg-export-copy run" \
      --tasks 1 --task-timeout 1h --max-retries 1 --execution-environment gen2 \
      --set-env-vars "SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_EXPORT_COPY_SOURCE=${SIG_BUCKET_BACKUPS},SIG_EXPORT_COPY_DEST=${SIG_EXPORT_COPY_DEST}"
    run gcloud scheduler jobs create http "${SIG_EXPORT_COPY_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "30 14 2 * *" --time-zone UTC \
      --uri "https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${SIG_EXPORT_COPY_JOB}:run" \
      --http-method POST --oauth-service-account-email "$(sa_email sig-scheduler)"
    _log "  second-project binding owed: grant sig-replica-rt objectCreator on"
    _log "  gs://${SIG_EXPORT_COPY_DEST} (applied on the second project's IAM)."
  else
    _log "QUEUED inside the leg: SIG_BACKUP_PROJECT unset — the cross-project"
    _log "copy job+scheduler stay uncreated until the second project is named."
  fi
}

leg_repoint() {
  banner "repoint the captures volume → sig-evidence"
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    no_ingest_running || die "an ingest execution is running or unprovable — repoint refused" 42
  fi
  local job
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    while IFS= read -r job; do
      [ -z "${job}" ] && continue
      _log "  repoint ${job}"
      gcloud run jobs update "${job}" \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --remove-volume-mount "/mnt/captures" --remove-volume captures \
        --add-volume "name=captures,type=cloud-storage,bucket=${SIG_BUCKET_EVIDENCE}" \
        --add-volume-mount "volume=captures,mount-path=/mnt/captures"
    done < <(ingest_jobs)
    _log "  restore point: each job's prior volume spec is in the prestate;"
    _log "  rollback re-points bucket=${SIG_BUCKET_RESTRICTED}."
  else
    _plan "for each ingest-class job: gcloud run jobs update <job> \\"
    _plan "  --remove-volume-mount /mnt/captures --remove-volume captures \\"
    _plan "  --add-volume name=captures,type=cloud-storage,bucket=${SIG_BUCKET_EVIDENCE} \\"
    _plan "  --add-volume-mount volume=captures,mount-path=/mnt/captures"
    _plan "  (refuses while any ingest execution runs — fail-closed)"
  fi
}

leg_probe() {
  banner "acceptance — retention delete MUST fail; copy parity; replica verify"
  local probe_obj="ops/retention-probe/p37-3-$(date -u +%Y%m%dT%H%M%SZ).txt"
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    printf 'p37.3 retention probe — deleting this object must fail (365d unlocked retention)\n' \
      | gcloud storage cp - "gs://${SIG_BUCKET_EVIDENCE}/${probe_obj}"
    _log "  retention delete attempt on ${probe_obj} (as ADC — unlocked retention binds every principal):"
    if gcloud storage rm "gs://${SIG_BUCKET_EVIDENCE}/${probe_obj}" 2>/dev/null; then
      die "the delete SUCCEEDED — retention is not in force; stop and record (OM-18)" 4
    else
      _log "  delete refused as designed — an ingest SA delete attempt on a capture fails a fortiori"
    fi
    local src dst
    src="$(gcloud storage ls --recursive "gs://${SIG_BUCKET_RESTRICTED}/${CAPTURES_PREFIX}/" 2>/dev/null | wc -l | tr -d ' ')"
    dst="$(gcloud storage ls --recursive "gs://${SIG_BUCKET_EVIDENCE}/${CAPTURES_PREFIX}/" 2>/dev/null | wc -l | tr -d ' ')"
    _log "  captures parity: restricted=${src} evidence=${dst}"
    [ "${src}" = "${dst}" ] || die "capture copy parity mismatch ${src} != ${dst}" 4
  else
    _plan "write ops/retention-probe/<ts>.txt on sig-evidence; delete attempt MUST fail"
    _plan "capture-count parity restricted:${CAPTURES_PREFIX}/ == evidence:${CAPTURES_PREFIX}/"
    _plan "sig-ops restricted-replica verify (after the first replica run)"
  fi
}

leg_rollback() {
  banner "rollback — removes ONLY this leg's own creations"
  _log "  jobs:    gcloud run jobs delete ${SIG_REPLICA_JOB} ${SIG_EXPORT_COPY_JOB} (name-checked)"
  _log "  sched:   gcloud scheduler jobs delete ${SIG_REPLICA_SCHED} ${SIG_EXPORT_COPY_SCHED}"
  _log "  iam:     remove-iam-policy-binding of every grant leg 'iam' added"
  _log "  repoint: --add-volume bucket=${SIG_BUCKET_RESTRICTED} (the prestate spec)"
  _log "  buckets: NEVER deleted — retention is the operator's WV-06 act"
  _log "  captures: the restricted-bucket originals were never touched"
}

leg_verify() {
  banner "verify — read-only outcome diff"
  local ok=0 drift=0
  _check() { if [ "$2" = "0" ]; then _log "OK    $1"; ok=$((ok+1)); else _log "DRIFT $1"; drift=$((drift+1)); fi }
  if [ "${SIG_GCP_MODE}" = "verify" ] || [ "${SIG_GCP_MODE}" = "apply" ]; then
    gcloud storage buckets describe "gs://${SIG_BUCKET_EVIDENCE}" --format='value(retention_policy.isLocked)' >/dev/null 2>&1 \
      && _check "evidence-bucket-exists" 0 || _check "evidence-bucket-exists" 1
    local rp
    rp="$(gcloud storage buckets describe "gs://${SIG_BUCKET_EVIDENCE}" --format='value(retention_policy.retention_period_seconds)' 2>/dev/null || echo "")"
    [ "${rp}" = "31536000" ] && _check "retention-365d" 0 || _check "retention-365d (${rp:-absent})" 1
    local locked
    locked="$(gcloud storage buckets describe "gs://${SIG_BUCKET_EVIDENCE}" --format='value(retention_policy.is_locked)' 2>/dev/null || echo "")"
    { [ "${locked}" = "False" ] || [ "${locked}" = "false" ]; } && _check "retention-unlocked" 0 || _check "retention-unlocked (${locked:-absent})" 1
    gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED_DR}" >/dev/null 2>&1 \
      && _check "dr-bucket-exists" 0 || _check "dr-bucket-exists" 1
    gcloud run jobs describe "${SIG_REPLICA_JOB}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1 \
      && _check "replica-job" 0 || _check "replica-job" 1
    _log "verify: ${ok} OK, ${drift} DRIFT"
    [ "${drift}" -eq 0 ] || exit 4
  else
    _plan "describe both new buckets; retention_period_seconds==31536000 && isLocked==false; replica job present"
  fi
}

# ---------------------------------------------------------------------------
banner "evidence-store (P37.3 — GATE-G6 §4 pre-authorised; legs=${ACTION})"
_log "  restore point: prestate captures + additive copies + recorded volume specs"
_log "  window: never 03:00-10:00Z; repoint refuses while an ingest execution runs"
_log "  author: ${SIG_EVSTORE_AUTHOR:-<unset>}  backup-project: ${SIG_BACKUP_PROJECT:-<unset>}"

assert_window
[ "${SIG_GCP_MODE}" = "apply" ] && require_adc

run_all() {
  leg_prestate; leg_bucket; leg_captures; leg_drbucket; leg_iam
  leg_jobs; leg_repoint; leg_probe; leg_verify
}

case "${ACTION}" in
  prestate)  leg_prestate ;;
  bucket)    leg_bucket ;;
  captures)  leg_captures ;;
  dr-bucket) leg_drbucket ;;
  iam)       leg_iam ;;
  jobs)      leg_jobs ;;
  repoint)   leg_repoint ;;
  probe)     leg_probe ;;
  poststate) leg_verify ;;
  rollback)  leg_rollback ;;
  verify)    leg_verify ;;
  all)       run_all ;;
  *) _log "unknown ACTION '${ACTION}'"; _usage 64 ;;
esac
_log "evidence-store.sh ${ACTION}: done (mode=${SIG_GCP_MODE})"
