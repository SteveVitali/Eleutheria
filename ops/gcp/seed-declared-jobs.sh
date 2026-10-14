#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/seed-declared-jobs.sh — P35.1a1 (ticket 287a; D-P34.42b-2 bridge):
# seed exactly the twelve declared-but-absent ingest rows — the ten `r11-*`
# batches + the two ADR-185 screened-lane sources — as Cloud Run jobs on the
# project default compute identity, each with an existing-`sig-scheduler`
# roles/run.invoker binding and a Cloud Scheduler trigger created then
# IMMEDIATELY paused (R6 step 1). The leg makes the declared 100-job fleet
# real so `P34.42b-live-2` can see 100/100 and migrate every job to
# `sig-ingest-rt`, after which `P35.1a-live-2 --apply --paused` retries the
# scheduler-of-record leg. This script never executes a job, never resumes or
# enables a trigger, creates no service account, and never calls the
# fleet-wide `scheduled-ops.sh` reconcile.
#
#   ./seed-declared-jobs.sh [--check|--dry-run] [--evidence-dir DIR]
#       plan-only: prints the closed target set + the 36 ordered mutations;
#       needs NO ADC, opens NO network, exits 0. With --evidence-dir the plan
#       + the resolved contract table are captured under DIR/.
#   ./seed-declared-jobs.sh --apply [--evidence-dir DIR]
#       the one authorized live leg. Window-gated: runs only on a weekday
#       inside 14:00–20:00Z (the contract's AR-3 slot); outside it exits 42
#       (queued — the RETURN PASS re-run prompt is printed). SIG_SEED_NOW
#       overrides the clock for the offline guard test only.
#   ./seed-declared-jobs.sh [--check|--apply] rollback --evidence-dir DIR
#       delete ONLY what the recorded leg created (triggers first, then the
#       added run.invoker bindings, then the jobs) replaying
#       DIR/created.txt — never a pre-existing resource. Deliberately NOT
#       window-gated: rolling back this leg's own creations is always safe.
#
# FAIL-CLOSED, narrow by contract (287a § Declared target set):
#   * the target set is the pinned twelve-row contract below — the script
#     reads ops/cadence.toml and REFUSES (exit 2) unless the selected rows
#     are exactly those twelve with exactly the declared job/scheduler/cron/
#     task_timeout values (cadence drift = refuse, never reconcile);
#   * the image is the contract-pinned digest only — an unset SIG_JOB_IMAGE
#     uses it; a ref under $SIG_API_IMAGE is accepted only when it resolves
#     to the same digest; any other resolved digest, a foreign repo,
#     `:latest`, or an untagged ref is refused (ADR-111);
#   * a target job or trigger that already exists refuses the leg — it never
#     updates, never upserts, and never deletes anything it did not create
#     this run; a mid-leg appearance likewise stops the leg and rolls back
#     this leg's creations;
#   * create-ok + pause-fail stops the leg and rolls back every resource
#     this run created (contract § Production mutations).
#
# Live window (OM-19, the contract's slot): a weekday 14:00–20:00Z.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true

ACTION="seed"
EVIDENCE_DIR="${SIG_SEED_STATE_DIR}"
while [ $# -gt 0 ]; do
  case "$1" in
    seed|rollback)  ACTION="$1"; shift ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    *) _log "usage: $(basename "$0") [--check|--dry-run|--apply] [seed|rollback] [--evidence-dir DIR]" >&2; exit 64 ;;
  esac
done
[ -n "${EVIDENCE_DIR}" ] || { _log "seed-declared-jobs.sh: empty --evidence-dir" >&2; exit 64; }

_repo="$(cd "${_here}/../.." && pwd)"
# SIG_SEED_CADENCE_TOML is the offline test seam — it points the declaration
# read at a fixture copy of ops/cadence.toml (drift-refusal tests). Unset, the
# leg reads the committed declaration via SIG_CADENCE_TOML (config.sh).
CADENCE_TOML="${SIG_SEED_CADENCE_TOML:-${SIG_CADENCE_TOML}}"
case "${CADENCE_TOML}" in
  /*) ;;
  *) CADENCE_TOML="${_repo}/${CADENCE_TOML}" ;;
esac

RERUN='implement-spec spec=docs/tickets/287a_P35.1a1__seed-declared-jobs-paused.md live_verification=true'

# The contract-pinned image digest (287a § Pinned image) — the only image this
# leg may deploy. The repo path is derived from the env-parameterised project
# id (config.sh); the digest itself is the contract's literal pin.
PINNED_DIGEST="sha256:6ad5477d4aacde23d508f5eea765a6ad835e603ad794b10df56710acca4414f5"
CAPTURE_MOUNT="/mnt/captures"
RUNTIME_IDENTITY_LABEL="temporary-default-compute"
RUNTIME_IDENTITY_RECORD="runtimeIdentity: temporary-default-compute (migrated by P34.42b)"

# --- the closed twelve-row contract ------------------------------------------
# `read_seed_rows` parses ops/cadence.toml and emits `kind|id|job|scheduler|
# cron|task_timeout` for EXACTLY the contract's twelve rows — any drift
# (a missing row, a changed field, an extra r11-* batch or tribal row, an
# `existing = true` mark) is a refusal, never a reconcile (287a: "refuses if
# the selected set is not exactly the twelve above").
read_seed_rows() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

# kind|id|job|scheduler|cron|task_timeout — the contract table, verbatim.
CONTRACT = [
    ("source", "camreg_tribal_all_leaders_directory",
     "sig-ingest-camreg-tribal-all-leaders-directory",
     "sig-sched-camreg-tribal-all-leaders-directory", "41 7 24 * *", "30m"),
    ("source", "legis_tribal_tohono_oodham_notice",
     "sig-ingest-legis-tribal-tohono-oodham-notice",
     "sig-sched-legis-tribal-tohono-oodham-notice", "43 7 24 * *", "30m"),
    ("batch", "r11-ate-01", "sig-ingest-r11-ate-01", "sig-sched-r11-ate-01",
     "17 7 18 * *", "6h"),
    ("batch", "r11-disclosures-01", "sig-ingest-r11-disclosures-01",
     "sig-sched-r11-disclosures-01", "27 7 21 * *", "6h"),
    ("batch", "r11-disclosures-02", "sig-ingest-r11-disclosures-02",
     "sig-sched-r11-disclosures-02", "27 7 22 * *", "6h"),
    ("batch", "r11-documents-01", "sig-ingest-r11-documents-01",
     "sig-sched-r11-documents-01", "27 7 23 * *", "6h"),
    ("batch", "r11-layers-01", "sig-ingest-r11-layers-01",
     "sig-sched-r11-layers-01", "17 7 16 * *", "6h"),
    ("batch", "r11-layers-02", "sig-ingest-r11-layers-02",
     "sig-sched-r11-layers-02", "17 7 17 * *", "6h"),
    ("batch", "r11-procurement-01", "sig-ingest-r11-procurement-01",
     "sig-sched-r11-procurement-01", "17 7 19 * *", "6h"),
    ("batch", "r11-tier2-01", "sig-ingest-r11-tier2-01",
     "sig-sched-r11-tier2-01", "37 7 25 * *", "6h"),
    ("batch", "r11-tier2-02", "sig-ingest-r11-tier2-02",
     "sig-sched-r11-tier2-02", "37 7 26 * *", "6h"),
    ("batch", "r11-tier2-03", "sig-ingest-r11-tier2-03",
     "sig-sched-r11-tier2-03", "37 7 27 * *", "6h"),
]
EXPECTED_IDS = {row[1] for row in CONTRACT}
EXPECTED_JOBS = {row[2] for row in CONTRACT}
EXPECTED_SCHEDS = {row[3] for row in CONTRACT}


def refuse(msg: str) -> "SystemExit":
    print(f"REFUSED: {msg}", file=sys.stderr)
    return SystemExit(2)


with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)

sources = {s["id"]: s for s in doc.get("sources", [])}
batches = {b["id"]: b for b in doc.get("batches", [])}

# Extra-row guard: an r11-* batch or a tribal screened-lane source that is not
# in the contract widens the target set — refuse (closed set, 287a).
for b in doc.get("batches", []):
    if b["id"].startswith("r11-") and b["id"] not in EXPECTED_IDS:
        raise refuse(f"undeclared r11-* batch in cadence.toml: {b['id']}")
for s in doc.get("sources", []):
    if s.get("job") in EXPECTED_JOBS or s.get("scheduler") in EXPECTED_SCHEDS:
        if s["id"] not in EXPECTED_IDS:
            raise refuse(
                f"a cadence source names a contract job/scheduler under "
                f"another id: {s['id']}"
            )

rows = []
for kind, rid, job, sched, cron, timeout in CONTRACT:
    row = (sources if kind == "source" else batches).get(rid)
    if row is None:
        raise refuse(f"declared {kind} {rid!r} is absent from cadence.toml")
    for field, want in (
        ("job", job), ("scheduler", sched), ("cron", cron),
        ("task_timeout", timeout),
    ):
        got = row.get(field)
        if got != want:
            raise refuse(
                f"cadence drift on {rid}: {field}={got!r} != contract {want!r}"
            )
    if row.get("existing"):
        raise refuse(
            f"cadence marks {rid} existing — a present trigger is never this "
            "leg's target"
        )
    if row.get("secrets"):
        raise refuse(
            f"cadence declares extra secrets on {rid} — the contract payload "
            "carries SIG_PG_PASSWORD only"
        )
    if kind == "batch" and not row.get("members"):
        raise refuse(f"batch {rid} declares no members")
    rows.append((kind, rid, job, sched, cron, timeout))

if len(rows) != 12:
    raise refuse(f"selected {len(rows)} rows, contract says exactly 12")
for row in rows:
    print("|".join(row))
PY
  )
}

# `check_image` — the offline image gate (runs BEFORE the ADC gate so a
# mismatch refuses without credentials): unset → the contract pin; a digest
# ref must equal the pin exactly; a tag under $SIG_API_IMAGE is resolved at
# apply and must land on the pin; everything else refuses (exit 2).
resolve_seed_image() {
  local ref="${SIG_JOB_IMAGE:-}" pinned="${API_IMAGE}@${PINNED_DIGEST}"
  if [ -z "${ref}" ]; then
    printf '%s' "${pinned}"
    return 0
  fi
  case "${ref}" in
    "${API_IMAGE}@sha256:"*)
      if [ "${ref}" != "${pinned}" ]; then
        _log "ERROR: SIG_JOB_IMAGE=${ref} names a different digest — the contract" >&2
        _log "pin is ${PINNED_DIGEST} only (287a § Pinned image)." >&2
        return 2
      fi
      printf '%s' "${pinned}"
      return 0
      ;;
    *@sha256:*)
      _log "ERROR: SIG_JOB_IMAGE=${ref} resolves elsewhere — only ${API_IMAGE}@${PINNED_DIGEST} is authorized." >&2
      return 2
      ;;
    *:latest)
      _log "ERROR: SIG_JOB_IMAGE=${ref} is a mutable tag — deploy by the contract digest only (ADR-111)." >&2
      return 2
      ;;
  esac
  case "${ref##*/}" in
    *:*) ;;
    *)
      _log "ERROR: SIG_JOB_IMAGE=${ref} carries no tag or digest — refused (ADR-111)." >&2
      return 2
      ;;
  esac
  case "${ref}" in
    "${API_IMAGE}:"*) ;;
    *)
      _log "ERROR: SIG_JOB_IMAGE=${ref} is not a ${API_IMAGE} reference — refused." >&2
      return 2
      ;;
  esac
  # A tag under the sig-api repo: it must resolve to the contract digest. In
  # check mode nothing is resolved — the plan names the pin and notes the
  # resolution happens at apply.
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '%s' "${pinned}"
    return 0
  fi
  require_adc
  local resolved
  resolved="$(pin_image_digest "${ref}")" || {
    _log "ERROR: could not resolve SIG_JOB_IMAGE=${ref} to a digest." >&2
    return 2
  }
  if [ "${resolved}" != "${pinned}" ]; then
    _log "ERROR: SIG_JOB_IMAGE=${ref} resolves to ${resolved} — not the contract pin ${pinned}." >&2
    return 2
  fi
  printf '%s' "${resolved}"
}

# `assert_window` — the contract's slot: a weekday 14:00–20:00Z (AR-3 + AR-2).
# Outside it the apply queues (exit 42); check mode is never gated — a
# printed plan mutates nothing. SIG_SEED_NOW overrides the clock for the
# offline guard test only.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  [ "${ACTION}" = "rollback" ] && return 0  # rollback is always safe
  local now hhmm dow
  now="${SIG_SEED_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  hhmm="${now:11:5}"
  dow="$(date -u -d "${now}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${now}" +%u 2>/dev/null \
        || echo 7)"
  if [ "${dow}" -le 5 ] && [[ "${hhmm}" > "13:59" && "${hhmm}" < "20:00" ]]; then
    _log "window OK: ${now} (the contract's weekday 14:00–20:00Z slot)"
    return 0
  fi
  _log "QUEUED (exit 42): ${now} is outside a weekday 14:00–20:00Z slot — the"
  _log "contract's only authorized window. No production mutation ran."
  _log "re-run: ${RERUN} (scope: the declared-job seed leg only)"
  exit 42
}

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# `_sha256_rec <abs-path>` — append "<hash>  <path relative to EVIDENCE_DIR>"
# to sha256s.txt (the committed sidecar convention: hash + name, never a
# bare digest).
_sha256_rec() {
  printf '%s  %s\n' "$(_sha256 "$1")" "${1#"${EVIDENCE_DIR}/"}"
}

_capture() {  # _capture <file> <cmd...> — a read-only capture under evidence/
  local out="${EVIDENCE_DIR}/$1"
  shift
  mkdir -p "$(dirname "${out}")"
  _log "+ (capture) $* > ${out}"
  if ! "$@" > "${out}" 2> "${out}.err"; then
    # A read error is still evidence (an absent target's describe errs
    # NOT_FOUND); the caller decides whether the captured error is the
    # expected one.
    _log "   (captured non-zero exit; see ${out}.err)"
  fi
  _sha256_rec "${out}" >> "${EVIDENCE_DIR}/sha256s.txt"
}

_created_record() { printf '%s %s\n' "$1" "$2" >> "${EVIDENCE_DIR}/created.txt"; }

# `rollback_created` — delete ONLY the resources this leg recorded creating
# (DIR/created.txt): triggers first, then the added sig-scheduler invoker
# bindings, then the jobs. Never touches a pre-existing resource.
rollback_created() {
  local dir="${EVIDENCE_DIR}" manifest="${EVIDENCE_DIR}/created.txt" line
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "rollback replays ${manifest} in reverse: delete the created triggers, remove the added run.invoker bindings, delete the created jobs — never a pre-existing resource"
    if [ -f "${manifest}" ]; then
      tac "${manifest}" 2>/dev/null || tail -r "${manifest}"
    fi
    return 0
  fi
  if [ ! -f "${manifest}" ]; then
    _log "rollback: no ${manifest} — nothing this leg created is recorded; nothing deleted."
    return 0
  fi
  _log "-- rollback: deleting only what ${manifest} records (never a pre-existing resource) --"
  # triggers first
  while read -r kind name; do
    [ "${kind}" = "trigger" ] || continue
    run gcloud scheduler jobs delete "${name}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet
  done < "${manifest}"
  while read -r kind name; do
    [ "${kind}" = "binding" ] || continue
    run gcloud run jobs remove-iam-policy-binding "${name}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --member="serviceAccount:${SCHED_SA_EMAIL}" \
      --role=roles/run.invoker
  done < "${manifest}"
  while read -r kind name; do
    [ "${kind}" = "job" ] || continue
    run gcloud run jobs delete "${name}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet
  done < "${manifest}"
  _log "rollback: complete — every resource this leg created is deleted."
}

_abort() {  # _abort <msg> — record + roll back this leg's creations, then fail
  _log "ERROR: $* — stopping the leg." >&2
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    rollback_created || _log "rollback itself failed — replay \`rollback --evidence-dir ${EVIDENCE_DIR}\`." >&2
  fi
  exit 2
}

# `_absent <kind> <name>` — fail-closed absence proof for a target job or
# trigger (apply only): present → the leg refuses (never updates/upserts).
_absent() {
  local kind="$1" name="$2" describe
  case "${kind}" in
    job)     describe=(gcloud run jobs describe "${name}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}") ;;
    trigger) describe=(gcloud scheduler jobs describe "${name}" --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}") ;;
  esac
  if "${describe[@]}" > "${EVIDENCE_DIR}/pre/${kind}-${name}.json" 2> "${EVIDENCE_DIR}/pre/${kind}-${name}.err"; then
    _log "REFUSED: ${kind} ${name} already exists — the leg never touches an existing target." >&2
    return 1
  fi
  _sha256_rec "${EVIDENCE_DIR}/pre/${kind}-${name}.err" >> "${EVIDENCE_DIR}/sha256s.txt"
  return 0
}

# `_no_executions <job>` — the contract's no-executions read: a job with any
# recorded execution fails the leg (fail-closed: an unreadable list is
# treated as an execution).
_no_executions() {
  local job="$1" json
  json="$(gcloud run jobs executions list --job "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --limit=5 --format=json 2>/dev/null)" || return 1
  [ "${json}" = "[]" ] || return 1
  return 0
}

# ---------------------------------------------------------------------------
banner "declared-job seed bridge (P35.1a1 / D-P34.42b-2; 287a)"

require_project
# SIG_API_IMAGE was derived at config.sh source time — possibly before
# require_project filled the check-mode placeholder — so the pinned image is
# recomputed here from the (now guaranteed) project id.
API_IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-api"
SCHED_SA_EMAIL="${SIG_SCHEDULER_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
PINNED_IMAGE="${API_IMAGE}@${PINNED_DIGEST}"

# The closed target set — resolved + drift-checked BEFORE any gate or plan.
ROWS="$(read_seed_rows)" || exit 2
NROWS="$(printf '%s\n' "${ROWS}" | grep -c .)"
[ "${NROWS}" = "12" ] || { _log "REFUSED: selected ${NROWS} rows, contract says exactly 12." >&2; exit 2; }

if [ "${ACTION}" = "rollback" ]; then
  require_adc
  rollback_created
  [ "${SIG_GCP_MODE}" = "check" ] && _log "seed-declared-jobs rollback: check OK (mode=${SIG_GCP_MODE})" \
    || _log "seed-declared-jobs rollback: done (mode=${SIG_GCP_MODE})"
  exit 0
fi

# The offline image gate fires before the window/ADC gates so a wrong-digest
# or malformed ref refuses without credentials (287a § Pinned image).
IMAGE="$(resolve_seed_image)" || exit 2
_log "job image (contract pin): ${IMAGE}"

CONN="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
CADENCE_SHA256="$(shasum -a 256 "${CADENCE_TOML}" | awk '{print $1}')"
DECLARED_GCS_URI="gs://${SIG_BUCKET_RESTRICTED}/ops/declared/live-diff.json"
JOB_ENV="SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED},SIG_OPS_CADENCE=/app/ops/cadence.toml,SIG_OPS_CADENCE_SHA256=${CADENCE_SHA256},SIG_OPS_DECLARED_GCS=${DECLARED_GCS_URI},SIG_PG_USER=sig,SIG_PG_DB=${SIG_PG_DB_NAME:-sig},SIG_CLOUDSQL_CONNECTION=${CONN}"
INGEST_ENV="${JOB_ENV},SIG_CAPTURE_DIR=${CAPTURE_MOUNT}/evidence/captures,SIG_CODE_COMMIT=${IMAGE##*@}"

# The temporary runtime identity: the project default compute SA is resolved
# live at apply (projectNumber -> <n>-compute@developer.gserviceaccount.com);
# check mode prints the placeholder. P34.42b-live-2 migrates these twelve to
# sig-ingest-rt — this leg labels the interim state, never hides it.
resolve_compute_sa() {
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '<projectNumber>-compute@developer.gserviceaccount.com'
    return 0
  fi
  local num
  num="$(gcloud projects describe "${SIG_GCP_PROJECT}" --format='value(projectNumber)')" \
    || _abort "could not read the project number — cannot name the default compute identity"
  printf '%s-compute@developer.gserviceaccount.com' "${num}"
}

job_args_for() {  # the row's exact scheduled-ingest command (contract table)
  if [ "$1" = "source" ]; then
    printf -- "-c,exec sig-ops scheduled-ingest --source %s --sink pg" "$2"
  else
    printf -- "-c,exec sig-ops scheduled-ingest --batch %s --sink pg" "$2"
  fi
}

emit_plan() {
  _log "closed target set (exactly the contract's twelve; cadence.toml drift refuses):"
  printf '%s\n' "${ROWS}" | while IFS='|' read -r kind rid job sched cron ttimeout; do
    _log "  ${kind} ${rid}: ${job} + ${sched} @ '${cron}' (timeout ${ttimeout})"
  done
  _log "image: ${IMAGE} (contract pin — SIG_JOB_IMAGE must resolve to this digest)"
  _log "runtime identity: ${RUNTIME_IDENTITY_RECORD}"
  _log "-- prestate (read-only): date -u, branch/sha, run jobs list, scheduler jobs list,"
  _log "   sig-scheduler describe (must exist — never created here), the default"
  _log "   compute SA address, restricted-bucket + sig-pg-password secret IAM,"
  _log "   per-target job/trigger absence describes + a no-executions read --"
  _log "-- mutations (per row, in order): re-check absence -> run jobs deploy (create)"
  _log "   -> run jobs add-iam-policy-binding (sig-scheduler run.invoker) ->"
  _log "   scheduler jobs create http -> scheduler jobs pause -> describe PAUSED --"
  _log "-- poststate: 100 jobs exactly; 12 job describes match the declaration;"
  _log "   12 triggers PAUSED with the declared cron/target/invoker; no executions --"
  printf '%s\n' "${ROWS}" | while IFS='|' read -r kind rid job sched cron ttimeout; do
    _log "  row ${rid}:"
    run gcloud run jobs deploy "${job}" \
      --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --service-account "$(resolve_compute_sa)" \
      --command sh \
      --args "$(job_args_for "${kind}" "${rid}")" \
      --tasks 1 --task-timeout "${ttimeout}" --max-retries 0 \
      --execution-environment gen2 \
      --add-volume "name=captures,type=cloud-storage,bucket=${SIG_BUCKET_RESTRICTED}" \
      --add-volume-mount "volume=captures,mount-path=${CAPTURE_MOUNT}" \
      --set-cloudsql-instances "${CONN}" \
      --set-env-vars "${INGEST_ENV}" \
      --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest" \
      --labels "runtime-identity=${RUNTIME_IDENTITY_LABEL}"
    run gcloud run jobs add-iam-policy-binding "${job}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --member="serviceAccount:${SCHED_SA_EMAIL}" \
      --role=roles/run.invoker
    run gcloud scheduler jobs create http "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${cron}" --time-zone=Etc/UTC \
      --uri "https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${job}:run" \
      --http-method=POST --oauth-service-account-email="${SCHED_SA_EMAIL}"
    run gcloud scheduler jobs pause "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      _plan "gcloud scheduler jobs describe ${sched}  # read back state=PAUSED"
    fi
  done
  _log "rollback on any failure: delete only this leg's triggers, remove only"
  _log "this leg's run.invoker bindings, delete only this leg's jobs"
  _log "  (replay: $(basename "$0") --apply rollback --evidence-dir ${EVIDENCE_DIR})"
}

if [ "${SIG_GCP_MODE}" = "check" ]; then
  mkdir -p "${EVIDENCE_DIR}"
  emit_plan | tee "${EVIDENCE_DIR}/check-plan.txt"
  printf '%s\n' "${ROWS}" > "${EVIDENCE_DIR}/target-rows.txt"
  {
    _sha256_rec "${EVIDENCE_DIR}/check-plan.txt"
    _sha256_rec "${EVIDENCE_DIR}/target-rows.txt"
  } > "${EVIDENCE_DIR}/sha256s.txt"
  _log "seed-declared-jobs seed: check OK (mode=${SIG_GCP_MODE}; evidence → ${EVIDENCE_DIR})"
  exit 0
fi

# --- apply -------------------------------------------------------------------
# Gate order (fail-closed): project -> offline image gate (above) -> window ->
# ADC -> prestate -> per-row re-check + create + bind + create + pause.
assert_window
require_adc

mkdir -p "${EVIDENCE_DIR}/pre" "${EVIDENCE_DIR}/post"
: > "${EVIDENCE_DIR}/sha256s.txt"
: > "${EVIDENCE_DIR}/created.txt"

_log "-- prestate (AR-2, read-only) --"
date -u +%Y-%m-%dT%H:%M:%SZ > "${EVIDENCE_DIR}/pre/date-start.txt"
{
  git -C "${_repo}" rev-parse --abbrev-ref HEAD
  git -C "${_repo}" rev-parse HEAD
} > "${EVIDENCE_DIR}/pre/git.txt"
_sha256_rec "${EVIDENCE_DIR}/pre/date-start.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
_sha256_rec "${EVIDENCE_DIR}/pre/git.txt" >> "${EVIDENCE_DIR}/sha256s.txt"

_capture pre/run-jobs.json gcloud run jobs list \
  --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
_capture pre/scheduler-jobs.json gcloud scheduler jobs list \
  --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
_capture pre/sig-scheduler-sa.json gcloud iam service-accounts describe \
  "${SCHED_SA_EMAIL}" --project "${SIG_GCP_PROJECT}"
_capture pre/project-number.txt gcloud projects describe "${SIG_GCP_PROJECT}" \
  --format='value(projectNumber)'
_capture pre/bucket-restricted-iam.json gcloud storage buckets get-iam-policy \
  "gs://${SIG_BUCKET_RESTRICTED}"
_capture pre/secret-sig-pg-password-iam.json gcloud secrets get-iam-policy \
  "${SIG_SECRET_PG_PASSWORD}" --project "${SIG_GCP_PROJECT}"

# sig-scheduler must already exist (this leg creates no service account).
if ! grep -q '"email"' "${EVIDENCE_DIR}/pre/sig-scheduler-sa.json" 2>/dev/null; then
  _log "REFUSED: ${SCHED_SA_EMAIL} is absent — this leg creates no service" >&2
  _log "account; the invoker identity must already exist (P34.42b's leg owns SAs)." >&2
  exit 2
fi

COMPUTE_SA="$(cat "${EVIDENCE_DIR}/pre/project-number.txt" | tr -d '[:space:]')-compute@developer.gserviceaccount.com"
_log "temporary runtime identity: ${COMPUTE_SA} (${RUNTIME_IDENTITY_RECORD})"
printf '%s\n' "${COMPUTE_SA}" > "${EVIDENCE_DIR}/pre/compute-sa.txt"
_sha256_rec "${EVIDENCE_DIR}/pre/compute-sa.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
printf '%s\n' "${RUNTIME_IDENTITY_RECORD}" > "${EVIDENCE_DIR}/runtime-identity.txt"

_log "-- absence sweep: every target job + trigger must be absent (fail-closed) --"
while IFS='|' read -r kind rid job sched cron ttimeout; do
  _absent job "${job}" || { _log "re-run: ${RERUN}" >&2; exit 2; }
  _absent trigger "${sched}" || { _log "re-run: ${RERUN}" >&2; exit 2; }
  if _no_executions "${job}"; then
    _log "  ${job}: absent, no executions"
  else
    _log "REFUSED: ${job} has a recorded/running execution (or the read failed)" >&2
    _log "  — a target must be absent AND never-running before the leg." >&2
    exit 2
  fi
done <<<"${ROWS}"

_log "-- seeding the twelve declared rows (job -> invoker -> trigger -> pause) --"
while IFS='|' read -r kind rid job sched cron ttimeout; do
  _log "  row ${rid}: ${job} / ${sched} @ '${cron}'"
  # Per-row re-check immediately before the create (contract: for each
  # declared row, re-check absence).
  _absent job "${job}" || _abort "target job ${job} appeared mid-leg"
  _absent trigger "${sched}" || _abort "target trigger ${sched} appeared mid-leg"
  run gcloud run jobs deploy "${job}" \
    --image "${IMAGE}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${COMPUTE_SA}" \
    --command sh \
    --args "$(job_args_for "${kind}" "${rid}")" \
    --tasks 1 --task-timeout "${ttimeout}" --max-retries 0 \
    --execution-environment gen2 \
    --add-volume "name=captures,type=cloud-storage,bucket=${SIG_BUCKET_RESTRICTED}" \
    --add-volume-mount "volume=captures,mount-path=${CAPTURE_MOUNT}" \
    --set-cloudsql-instances "${CONN}" \
    --set-env-vars "${INGEST_ENV}" \
    --set-secrets "SIG_PG_PASSWORD=${SIG_SECRET_PG_PASSWORD}:latest" \
    --labels "runtime-identity=${RUNTIME_IDENTITY_LABEL}" \
    || _abort "job create failed for ${job}"
  _created_record job "${job}"
  run gcloud run jobs add-iam-policy-binding "${job}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --member="serviceAccount:${SCHED_SA_EMAIL}" \
    --role=roles/run.invoker \
    || _abort "invoker binding failed for ${job}"
  _created_record binding "${job}"
  run gcloud scheduler jobs create http "${sched}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --schedule "${cron}" --time-zone=Etc/UTC \
    --uri "https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${job}:run" \
    --http-method=POST --oauth-service-account-email="${SCHED_SA_EMAIL}" \
    || _abort "trigger create failed for ${sched}"
  _created_record trigger "${sched}"
  run gcloud scheduler jobs pause "${sched}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    || _abort "pause failed for ${sched} (create succeeded — rolling back per contract)"
  # Read back PAUSED before the next row (contract ordering).
  state="$(gcloud scheduler jobs describe "${sched}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --format='value(state)' 2>/dev/null)" || _abort "could not read back ${sched} state"
  [ "${state}" = "PAUSED" ] || _abort "${sched} read-back state=${state} != PAUSED"
  _log "    ${sched}: created + PAUSED (read-back verified)"
done <<<"${ROWS}"

_log "-- poststate (read-only) --"
_capture post/run-jobs.json gcloud run jobs list \
  --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
_capture post/scheduler-jobs.json gcloud scheduler jobs list \
  --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
while IFS='|' read -r kind rid job sched cron ttimeout; do
  _capture "post/job-${job}.json" gcloud run jobs describe "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture "post/trigger-${sched}.json" gcloud scheduler jobs describe "${sched}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture "post/executions-${job}.json" gcloud run jobs executions list \
    --job "${job}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --limit=5 --format json
done <<<"${ROWS}"
date -u +%Y-%m-%dT%H:%M:%SZ > "${EVIDENCE_DIR}/post/date-end.txt"
_sha256_rec "${EVIDENCE_DIR}/post/date-end.txt" >> "${EVIDENCE_DIR}/sha256s.txt"

# The declared expected count is read from ops/iam_identities.toml (the
# declaration is the source of truth — a drift there refuses loudly).
EXPECTED_COUNT="$(cd "${_repo}" && uv run python - <<'PY'
import tomllib
with open("ops/iam_identities.toml", "rb") as fh:
    doc = tomllib.load(fh)
print(doc.get("expected_job_count", 0))
PY
)"
_log "-- verifying: fleet count == declared ${EXPECTED_COUNT}, the twelve specs, PAUSED triggers, no executions --"
uv run python - "${EVIDENCE_DIR}" "${EXPECTED_COUNT}" "${IMAGE}" \
    "${COMPUTE_SA}" "${SCHED_SA_EMAIL}" "${SIG_GCP_REGION}" "${SIG_GCP_PROJECT}" \
    "${SIG_BUCKET_RESTRICTED}" "${CONN}" "${SIG_SECRET_PG_PASSWORD}" <<'PY'
import json
import pathlib
import sys

ev = pathlib.Path(sys.argv[1])
expected_count = int(sys.argv[2])
image, compute_sa, sched_sa = sys.argv[3], sys.argv[4], sys.argv[5]
region, project, bucket, conn, pg_secret = (
    sys.argv[6], sys.argv[7], sys.argv[8], sys.argv[9], sys.argv[10])

CONTRACT = [line.split("|") for line in """
source|camreg_tribal_all_leaders_directory|sig-ingest-camreg-tribal-all-leaders-directory|sig-sched-camreg-tribal-all-leaders-directory|41 7 24 * *|30m
source|legis_tribal_tohono_oodham_notice|sig-ingest-legis-tribal-tohono-oodham-notice|sig-sched-legis-tribal-tohono-oodham-notice|43 7 24 * *|30m
batch|r11-ate-01|sig-ingest-r11-ate-01|sig-sched-r11-ate-01|17 7 18 * *|6h
batch|r11-disclosures-01|sig-ingest-r11-disclosures-01|sig-sched-r11-disclosures-01|27 7 21 * *|6h
batch|r11-disclosures-02|sig-ingest-r11-disclosures-02|sig-sched-r11-disclosures-02|27 7 22 * *|6h
batch|r11-documents-01|sig-ingest-r11-documents-01|sig-sched-r11-documents-01|27 7 23 * *|6h
batch|r11-layers-01|sig-ingest-r11-layers-01|sig-sched-r11-layers-01|17 7 16 * *|6h
batch|r11-layers-02|sig-ingest-r11-layers-02|sig-sched-r11-layers-02|17 7 17 * *|6h
batch|r11-procurement-01|sig-ingest-r11-procurement-01|sig-sched-r11-procurement-01|17 7 19 * *|6h
batch|r11-tier2-01|sig-ingest-r11-tier2-01|sig-sched-r11-tier2-01|37 7 25 * *|6h
batch|r11-tier2-02|sig-ingest-r11-tier2-02|sig-sched-r11-tier2-02|37 7 26 * *|6h
batch|r11-tier2-03|sig-ingest-r11-tier2-03|sig-sched-r11-tier2-03|37 7 27 * *|6h
""".strip().splitlines()]

problems = []


def seconds(dur: str) -> int:
    unit = {"s": 1, "m": 60, "h": 3600}
    return int(dur[:-1]) * unit[dur[-1]]


jobs = json.loads((ev / "post/run-jobs.json").read_text())
if len(jobs) != expected_count:
    problems.append(
        f"poststate job count {len(jobs)} != declared {expected_count}")

for kind, rid, job, sched, cron, timeout in CONTRACT:
    desc_path = ev / f"post/job-{job}.json"
    if not desc_path.is_file() or not desc_path.read_text().strip():
        problems.append(f"{job}: no poststate describe")
        continue
    d = json.loads(desc_path.read_text())
    spec = (((d.get("spec") or {}).get("template") or {}).get("spec") or {})
    containers = spec.get("containers") or []
    c = containers[0] if containers else {}
    if c.get("image") != image:
        problems.append(f"{job}: image {c.get('image')!r} != contract pin")
    if spec.get("serviceAccountName") != compute_sa:
        problems.append(
            f"{job}: serviceAccount {spec.get('serviceAccountName')!r} != "
            "the temporary default compute SA")
    if spec.get("maxRetries") not in (0, "0"):
        problems.append(f"{job}: maxRetries != 0")
    got_timeout = str(spec.get("taskTimeout") or "")
    try:
        got_secs = int(got_timeout[:-1]) if got_timeout.endswith("s") else seconds(got_timeout)
    except (ValueError, KeyError):
        got_secs = -1
    if got_secs != seconds(timeout):
        problems.append(
            f"{job}: taskTimeout {got_timeout!r} != declared {timeout}")
    args = " ".join(str(a) for a in (c.get("args") or []))
    want_flag = "--source" if kind == "source" else "--batch"
    if f"scheduled-ingest {want_flag} {rid}" not in args:
        problems.append(f"{job}: args {args!r} miss the declared command")
    env = {e.get("name"): e.get("value") for e in (c.get("env") or [])}
    if env.get("SIG_CAPTURE_DIR") != "/mnt/captures/evidence/captures":
        problems.append(f"{job}: SIG_CAPTURE_DIR missing/wrong")
    if env.get("SIG_CODE_COMMIT") != image.split("@", 1)[1]:
        problems.append(f"{job}: SIG_CODE_COMMIT != the pinned digest")
    if env.get("SIG_CLOUDSQL_CONNECTION") != conn:
        problems.append(f"{job}: SIG_CLOUDSQL_CONNECTION != {conn}")
    vols = {v.get("name"): v for v in (spec.get("volumes") or [])}
    cs = (vols.get("captures") or {}).get("cloudStorage") or {}
    if cs.get("bucket") != bucket:
        problems.append(f"{job}: captures volume != the restricted bucket")
    mounts = [m for m in (c.get("volumeMounts") or [])
              if m.get("mountPath") == "/mnt/captures"]
    if not mounts:
        problems.append(f"{job}: /mnt/captures mount missing")
    pg_env = [e for e in (c.get("env") or []) if e.get("name") == "SIG_PG_PASSWORD"]
    if not pg_env or pg_secret not in json.dumps(pg_env[0].get("valueFrom") or {}):
        problems.append(f"{job}: SIG_PG_PASSWORD secret ref missing")
    # the scheduler trigger
    tpath = ev / f"post/trigger-{sched}.json"
    if not tpath.is_file() or not tpath.read_text().strip():
        problems.append(f"{sched}: no poststate describe")
        continue
    t = json.loads(tpath.read_text())
    if t.get("state") != "PAUSED":
        problems.append(f"{sched}: state {t.get('state')!r} != PAUSED")
    if t.get("schedule") != cron:
        problems.append(f"{sched}: schedule {t.get('schedule')!r} != {cron!r}")
    if t.get("timeZone") != "Etc/UTC":
        problems.append(f"{sched}: timeZone != Etc/UTC")
    uri = ((t.get("httpTarget") or {}).get("uri")) or ""
    want_uri = (f"https://{region}-run.googleapis.com/apis/"
                f"run.googleapis.com/v1/namespaces/{project}/jobs/{job}:run")
    if uri != want_uri:
        problems.append(f"{sched}: uri {uri!r} != {want_uri!r}")
    oauth = ((t.get("httpTarget") or {}).get("oauthToken") or {})
    if oauth.get("serviceAccountEmail") != sched_sa:
        problems.append(f"{sched}: oauth SA != {sched_sa}")
    epath = ev / f"post/executions-{job}.json"
    if not epath.is_file() or json.loads(epath.read_text() or "null") not in ([], None):
        problems.append(f"{job}: an execution exists — the leg runs no job")

if problems:
    for p in problems:
        print(f"POSTSTATE FAIL: {p}", file=sys.stderr)
    sys.exit(2)
print("poststate verify OK — fleet count, twelve specs, PAUSED triggers, no executions")
PY

_log "seed-declared-jobs seed: done — evidence → ${EVIDENCE_DIR}"
_log "next: P34.42b-live-2 migrates these twelve to sig-ingest-rt on its own"
_log "authorization; P35.1a-live-2 --apply --paused follows it."
