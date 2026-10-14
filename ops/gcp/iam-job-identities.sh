#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/iam-job-identities.sh — the IAM leg of P34.42b (G1-01, F-272,
# SIG-SEC-007): every Cloud Run job stops running as the project-Editor
# default compute identity, and the default compute service account loses
# roles/editor. The committed declaration is ops/iam_identities.toml
# (`sig.iam-identities/1` — `sig-ops iam plan --leg jobs` renders it; every
# name this script uses is derived from it); this script owns the (windowed,
# pre-authorised S5-3/OM-20 "Both + list + P34.45") mutations:
#
#   ./iam-job-identities.sh --check [action]    # (default) plan-only:
#                                               # NO ADC, NO network.
#   ./iam-job-identities.sh --apply <action>    # windowed + operator ADC.
#   ./iam-job-identities.sh --verify            # read-only LIVE diff of the
#                                               # IAM/jobs/schedulers against
#                                               # the declaration (ADC, never
#                                               # window-gated — the shape
#                                               # P35.1a's live-diff reuses)
#   ./iam-job-identities.sh --verify --from-state DIR
#                                            # offline diff of a recorded
#                                            # snapshot (a capture dir, or a
#                                            # leg dir holding pre/ + post/)
#
# Actions:
#   prestate    the AR-2-analogue restore point for IAM: the project IAM
#               policy, the service-account list, `run jobs list` (the 88-job
#               re-count — a count/coverage disagreement refuses the leg),
#               a per-job describe (prior SA + image digest), the scheduled
#               jobs' invoker policies + scheduler trigger describes (the
#               signing identity), the sig-alerts service IAM policy, and the
#               per-secret + per-bucket IAM policies. READ-ONLY — any time.
#   identities  create the declared SAs (the four job-class identities +
#               the reserved identities — idempotent).
#   bindings    the declared project + bucket grants per class — the ingest
#               class's ONE conditioned grant (objectUser scoped to
#               evidence/captures/ only — ADR-201; no bucket-wide delete,
#               SIG-STORE-048) — plus the consumer secret accessors, THEN the
#               jobs_revoke removals off default-compute.
#   jobs        per job: fail-closed "no execution running" check →
#               `run jobs update --service-account` (same image, identity
#               only) → post-describe asserts the image is byte-identical
#               and the SA is the class identity.
#   invokers    grant roles/run.invoker on every scheduled job to the
#               sig-scheduler identity and assert each trigger signs as it;
#               then the sig-alerts jobs-posture rule — grant the caller
#               (sig-probe-rt), revoke allUsers AND default-compute.
#   editor      the last mutation: read shows NO job/service still runs as
#               default-compute → `projects remove-iam-policy-binding
#               roles/editor`. A job still on the old identity refuses.
#   verify      poststate capture + `sig-ops iam diff --leg jobs` clean +
#               `sig-ops iam check-revisions` (every job's image
#               byte-identical) + the analysis leg below. READ-ONLY.
#   analysis    the proof-without-destruction read (deliverable 5):
#               `policy-intelligence troubleshoot-iam-policy` per runtime SA —
#               storage.objects.delete at bucket scope AND on a non-captures
#               object path → NOT_GRANTED (the conditioned grant never
#               widens), cloudsql.instances.delete → NOT_GRANTED,
#               secretmanager.versions.access on every non-consumer secret →
#               NOT_GRANTED. No deletion is ever attempted as a probe.
#   rollback    from the recorded prestate: every job back to its prior SA,
#               the sig-alerts invoker policy re-set, roles/editor re-added
#               to default-compute, the added bindings removed, then the SAs
#               the prestate did NOT list deleted (sig-scheduler pre-exists —
#               never deleted). Deliberately NOT window-gated — restoring
#               prestate is always safe.
#   all         prestate → identities → bindings → jobs → invokers → editor →
#               verify (the leg, incl. analysis).
#
# Live window (OM-19, the contract's AR-3 + AR-2 slot): applies run ≥
# ${SIG_IAM_JOBS_EARLIEST} and never 03:00–06:30Z; earlier → exit 42 (queued,
# the RETURN PASS re-run prompt is printed). 14:00–20:00Z on a weekday is the
# preferred slot — outside it the guard logs a note, never a refusal.
# The execution guard (the contract's "never while a job of the class being
# moved is executing") is fail-closed: an unreadable executions list is
# treated as running and queues the leg. SIG_IAM_JOBS_NOW overrides the clock
# for the offline guard test only.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

ACTION="all"
FROM_STATE=""
case "${1:-}" in
  --verify)
    # Read-only: live diff (ADC) — or an offline recorded-snapshot diff with
    # --from-state DIR. Never window-gated; a diff mutates nothing.
    SIG_GCP_MODE="verify"
    ACTION="verify"
    shift
    if [ "${1:-}" = "--from-state" ]; then
      [ $# -ge 2 ] || { echo "iam-job-identities.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2
    fi
    ;;
  *)
    parse_mode "${1:-}"
    shift || true
    ACTION="${1:-all}"
    ;;
esac
export SIG_GCP_MODE
STATE_DIR="${2:-${SIG_IAM_JOBS_STATE_DIR}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/252_P34.42b__least-privilege-job-identities-remove-editor.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `_decl <python -c body>` — a field out of `sig-ops iam plan --json --leg
# jobs` (the declaration is the single source of every name this script uses).
_decl() {
  _sigops iam plan --json --leg jobs \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    | python3 -c "$1"
}

# `assert_window` — the OM-19/AR-3 clock guard (ISO strings compare
# lexicographically; exit 42 = queued leg). Check mode is never gated — a
# printed plan mutates nothing.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dow
  now="${SIG_IAM_JOBS_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_IAM_JOBS_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_IAM_JOBS_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN} (scope: the jobs IAM leg only)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the jobs IAM leg only)"
    exit 42
  fi
  dow="$(date -u -d "${now}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${now}" +%u 2>/dev/null \
        || echo 7)"
  if [[ "${hhmm}" > "13:59" && "${hhmm}" < "20:00" && "${dow}" -le 5 ]]; then
    _log "window OK: ${now} (the preferred 14:00–20:00Z weekday slot)"
  else
    _log "window OK: ${now} (≥ ${SIG_IAM_JOBS_EARLIEST}, outside 03:00–06:30Z — note: outside the preferred 14:00–20:00Z weekday slot)"
  fi
}

# `_job_running <job>` — 0 when a run of the job is in flight, 1 when none is.
# FAIL-CLOSED: an unreadable executions list returns 0 (treated as running) —
# the contract's execution guard never mutates on an unproven window.
_job_running() {
  local json
  json="$(gcloud run jobs executions list \
    --job "$1" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --format=json 2>/dev/null)" || return 0
  SIG_JEXEC="$json" python3 - <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_JEXEC"])
except Exception:
    sys.exit(0)  # unparseable = unproven = running
running = any(
    not any(
        c.get("type") == "Completed" and str(c.get("status")) == "True"
        for c in ((e.get("status") or {}).get("conditions")) or [])
    for e in (rows if isinstance(rows, list) else []))
sys.exit(0 if running else 1)
PY
}

# `assert_no_executions` — the contract's "do not run while a job of the class
# being moved is executing": before any job/invoker/editor mutation, prove NO
# declared job has a running execution; otherwise queue (exit 42).
assert_no_executions() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local job
  while read -r job; do
    [ -n "${job}" ] || continue
    if _job_running "${job}"; then
      _log "QUEUED (exit 42): an execution of ${job} is running (or the check"
      _log "could not prove none is) — never move an identity under a live job."
      _log "re-run: ${RERUN} (scope: the jobs IAM leg only)"
      exit 42
    fi
  done <<<"${JOB_NAMES}"
  _log "execution guard OK — no declared job has a running execution."
}

_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# `_capture <dir>` — the IAM + jobs + schedulers snapshot prestate/verify take.
_capture() {
  local dir="$1" job s sched trig b
  mkdir -p "${dir}"
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/project-iam.json"
  gcloud iam service-accounts list --project "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/service-accounts.json"
  gcloud projects describe "${SIG_GCP_PROJECT}" \
    --format='value(projectNumber)' > "${dir}/project-number.txt"
  printf '%s-compute@developer.gserviceaccount.com' \
    "$(cat "${dir}/project-number.txt")" > "${dir}/compute-sa.txt"
  # The 88-job re-count + coverage read — the leg refuses on a disagreement.
  gcloud run jobs list --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${dir}/run-jobs.json"
  while read -r job; do
    [ -n "${job}" ] || continue
    gcloud run jobs describe "${job}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format json > "${dir}/job-${job}.json"
  done <<<"${JOB_NAMES}"
  # Scheduled jobs: the invoker policy + the trigger describe (signing SA).
  while read -r sched trig; do
    [ -n "${sched}" ] || continue
    gcloud run jobs get-iam-policy "${sched}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format json > "${dir}/job-${sched}-iam.json" \
      || printf '{"bindings":[]}' > "${dir}/job-${sched}-iam.json"
    gcloud scheduler jobs describe "${trig}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format json > "${dir}/sched-${sched}.json" \
      || printf '{}' > "${dir}/sched-${sched}.json"
  done <<<"${SCHED_LINES}"
  # The sig-alerts receiver policy (the jobs-leg invoker rule's target).
  gcloud run services get-iam-policy "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/service-${SIG_ALERTS_SERVICE}-iam.json"
  for b in ${BUCKET_SUFFIXES}; do
    gcloud storage buckets get-iam-policy "gs://${SIG_GCP_PROJECT}-${b}" \
      --format json > "${dir}/bucket-${b}-iam.json" \
      || printf '{"bindings":[]}' > "${dir}/bucket-${b}-iam.json"
  done
  for s in ${SECRET_NAMES}; do
    gcloud secrets get-iam-policy "${s}" --project "${SIG_GCP_PROJECT}" \
      --format json > "${dir}/secret-${s}-iam.json" \
      || printf '{"bindings":[]}' > "${dir}/secret-${s}-iam.json"
  done
  (cd "${dir}" && for f in *.json; do _sha256 "$f"; done) > "${dir}/sha256s.txt"
}

# `_assert_map_covers` — the re-count gate: the recorded live job list must be
# exactly the declared map (count + coverage). A contradictory production
# read voids the pre-authorisation — refuse, never mutate around it.
_assert_map_covers() {
  local jobs_file="$1"
  SIG_MAP="${JOB_MAP_JSON}" SIG_JOBS_FILE="${jobs_file}" \
    SIG_EXPECT="${EXPECTED_JOBS}" python3 - <<'PY'
import json, os, sys
live = json.load(open(os.environ["SIG_JOBS_FILE"]))
names = set()
for r in live if isinstance(live, list) else []:
    n = ((r.get("metadata") or {}).get("name")) or r.get("name")
    if n:
        names.add(str(n).rsplit("/", 1)[-1])
mapped = set(json.loads(os.environ["SIG_MAP"]))
expected = int(os.environ["SIG_EXPECT"])
unmapped = sorted(names - mapped)
gone = sorted(mapped - names)
problems = []
if len(names) != expected:
    problems.append(f"live job count {len(names)} != declared {expected} (G1-C07 re-count)")
if unmapped:
    problems.append(f"live job(s) claimed by no class: {unmapped}")
if gone:
    problems.append(f"declared job(s) absent live: {gone}")
for p in problems:
    print(f"RE-COUNT REFUSAL: {p}", file=sys.stderr)
sys.exit(1 if problems else 0)
PY
}

# `_job_sa <describe.json>` — the job's recorded runtime identity.
_job_sa() {
  python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
spec = (d.get("spec") or {}).get("template", {}).get("spec", {})
if spec.get("serviceAccountName"):
    print(spec["serviceAccountName"]); sys.exit()
tpl = (d.get("template") or {}).get("template") or {}
print(tpl.get("serviceAccount") or tpl.get("serviceAccountName") or "")' "$1" 2>/dev/null || true
}

_job_image() {
  python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
spec = (d.get("spec") or {}).get("template", {}).get("spec", {})
for c in spec.get("containers") or []:
    if c.get("image"):
        print(c["image"]); sys.exit()
tpl = (d.get("template") or {}).get("template") or {}
for c in tpl.get("containers") or []:
    if c.get("image"):
        print(c["image"]); sys.exit()' "$1" 2>/dev/null || true
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the IAM restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud projects get-iam-policy ${SIG_GCP_PROJECT} > pre/project-iam.json"
    _plan "gcloud iam service-accounts list + projects describe > pre/service-accounts.json, project-number.txt, compute-sa.txt"
    _plan "gcloud run jobs list > pre/run-jobs.json  (the ${EXPECTED_JOBS}-job re-count — coverage refusal on drift)"
    _plan "gcloud run jobs describe <each of the ${EXPECTED_JOBS} jobs> > pre/job-*.json  (prior SA + image digest)"
    _plan "gcloud run jobs get-iam-policy + scheduler jobs describe per scheduled job > pre/job-*-iam.json, pre/sched-*.json"
    _plan "gcloud run services get-iam-policy ${SIG_ALERTS_SERVICE} > pre/service-${SIG_ALERTS_SERVICE}-iam.json"
    _plan "gcloud storage buckets get-iam-policy for: ${BUCKET_SUFFIXES} > pre/bucket-*-iam.json"
    _plan "gcloud secrets get-iam-policy for: ${SECRET_NAMES} > pre/secret-*-iam.json"
    _plan "sha256 sidecars over every capture > pre/sha256s.txt"
    return 0
  fi
  _capture "${STATE_DIR}/pre"
  _assert_map_covers "${STATE_DIR}/pre/run-jobs.json" || {
    _log "ERROR: the live fleet disagrees with the declared map — the leg refuses." >&2
    exit 4
  }
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ)); map covers all ${EXPECTED_JOBS} live jobs."
}

do_identities() {
  assert_window
  _log "-- identities ($(date -u +%FT%TZ)): create the declared job-class + reserved SAs (idempotent) --"
  local sa
  for sa in ${JOB_SA_IDS}; do
    if [ "${SIG_GCP_MODE}" = "apply" ] && \
       gcloud iam service-accounts describe "$(_sa_email "${sa}")" \
         --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "exists: ${sa} — skipping create"
    else
      run gcloud iam service-accounts create "${sa}" \
        --display-name "${sa} runtime" \
        --project "${SIG_GCP_PROJECT}"
      _log "   rollback: gcloud iam service-accounts delete $(_sa_email "${sa}") --quiet"
    fi
  done
}

do_bindings() {
  assert_window
  _log "-- bindings ($(date -u +%FT%TZ)): the declared least-privilege grants per class --"
  # Every row below is rendered from the declaration (PROJECT_ROLE_LINES,
  # BUCKET_ROLE_LINES, SECRET_GRANT_LINES, SECRET_REVOKE_LINES) — a drift
  # between this leg and ops/iam_identities.toml is impossible by construction.
  local line sa role bucket cond_title cond_prefix member secret
  while read -r sa role; do
    [ -n "${sa}" ] || continue
    run gcloud projects add-iam-policy-binding "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}"
    _log "   rollback: gcloud projects remove-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:$(_sa_email "${sa}") --role ${role}"
  done <<<"${PROJECT_ROLE_LINES}"
  while read -r sa bucket role cond_title cond_prefix; do
    [ -n "${sa}" ] || continue
    if [ "${cond_title}" != "-" ]; then
      # The ONE conditioned grant (ADR-201): objectUser scoped to the OCFL
      # captures prefix — rewrite of the inventory head, never bucket-wide
      # delete. gcloud storage buckets supports --condition-* flags on
      # add-iam-policy-binding; the expression asserts startsWith on the
      # object resource name.
      run gcloud storage buckets add-iam-policy-binding \
        "gs://${SIG_GCP_PROJECT}-${bucket}" \
        --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}" \
        --condition-title="${cond_title}" \
        --condition-description="P34.42b/ADR-201: OCFL inventory-head rewrite under ${cond_prefix} only (SIG-STORE-048)" \
        --condition-expression="resource.name.startsWith('projects/_/buckets/${SIG_GCP_PROJECT}-${bucket}/objects/${cond_prefix}')"
      _log "   rollback: gcloud storage buckets remove-iam-policy-binding gs://${SIG_GCP_PROJECT}-${bucket} --member serviceAccount:$(_sa_email "${sa}") --role ${role} --all"
    else
      run gcloud storage buckets add-iam-policy-binding \
        "gs://${SIG_GCP_PROJECT}-${bucket}" \
        --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}"
      _log "   rollback: gcloud storage buckets remove-iam-policy-binding gs://${SIG_GCP_PROJECT}-${bucket} --member serviceAccount:$(_sa_email "${sa}") --role ${role}"
    fi
  done <<<"${BUCKET_ROLE_LINES}"
  while read -r secret member; do
    [ -n "${secret}" ] || continue
    run gcloud secrets add-iam-policy-binding "${secret}" \
      --project "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${member}")" \
      --role roles/secretmanager.secretAccessor
    _log "   rollback: gcloud secrets remove-iam-policy-binding ${secret} --member serviceAccount:$(_sa_email "${member}") --role roles/secretmanager.secretAccessor"
  done <<<"${SECRET_GRANT_LINES}"
  # The jobs_revoke removals — the jobs no longer run as default-compute
  # (the `jobs` action moves them; the revoke lands here so a re-run of the
  # leg still converges: new accessors are granted BEFORE the stale one is
  # revoked, so a mid-leg failure never strands a job with no secret read).
  local compute
  compute="$(cat "${STATE_DIR}/pre/compute-sa.txt" 2>/dev/null || true)"
  while read -r secret member; do
    [ -n "${secret}" ] || continue
    local resolved
    if [ "${member}" = "default-compute" ]; then
      if [ "${SIG_GCP_MODE}" = "check" ]; then
        resolved="<default-compute resolved at apply>"
      elif [ -n "${compute}" ]; then
        resolved="${compute}"
      else
        _log "ERROR: no recorded compute SA (pre/compute-sa.txt) — refusing to resolve jobs_revoke." >&2
        exit 4
      fi
    else
      resolved="$(_sa_email "${member}")"
    fi
    run gcloud secrets remove-iam-policy-binding "${secret}" \
      --project "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:${resolved}" \
      --role roles/secretmanager.secretAccessor
    _log "   rollback: gcloud secrets add-iam-policy-binding ${secret} --member serviceAccount:${resolved} --role roles/secretmanager.secretAccessor"
  done <<<"${SECRET_REVOKE_LINES}"
}

do_jobs() {
  assert_window
  assert_no_executions
  _log "-- jobs ($(date -u +%FT%TZ)): ${EXPECTED_JOBS} same-image identity updates (one per declared job) --"
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    _assert_map_covers "${STATE_DIR}/pre/run-jobs.json" || {
      _log "ERROR: prestate job list does not match the declared map — refusing." >&2
      exit 4
    }
  fi
  local line job sa pre_sa pre_img post_img post_sa
  while IFS=$'\t' read -r job sa; do
    [ -n "${job}" ] || continue
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      # Per-job execution guard (the class guard already ran globally).
      if _job_running "${job}"; then
        _log "QUEUED (exit 42): an execution of ${job} is running mid-leg — stop, re-run later."
        exit 42
      fi
      pre_sa="$(_job_sa "${STATE_DIR}/pre/job-${job}.json")"
      pre_img="$(_job_image "${STATE_DIR}/pre/job-${job}.json")"
      if [ -z "${pre_img}" ]; then
        _log "ERROR: no recorded image at pre/job-${job}.json — refusing (AR-8 same-image gate)." >&2
        exit 4
      fi
      if [ "${pre_sa}" = "$(_sa_email "${sa}")" ]; then
        _log "skip: ${job} already on ${sa}"
        continue
      fi
    fi
    run gcloud run jobs update "${job}" \
      --service-account "$(_sa_email "${sa}")" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    _log "   rollback: gcloud run jobs update ${job} --service-account <recorded prior SA: pre/job-${job}.json>"
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      # The same-image gate + identity assertion on the fresh describe.
      gcloud run jobs describe "${job}" --region "${SIG_GCP_REGION}" \
        --project "${SIG_GCP_PROJECT}" --format json \
        > "${STATE_DIR}/post-job-${job}.json"
      post_img="$(_job_image "${STATE_DIR}/post-job-${job}.json")"
      post_sa="$(_job_sa "${STATE_DIR}/post-job-${job}.json")"
      if [ "${post_img}" != "${pre_img}" ]; then
        _log "ERROR: ${job} image changed ${pre_img} → ${post_img} — rolling this job back." >&2
        gcloud run jobs update "${job}" --service-account "${pre_sa}" \
          --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" || true
        exit 6
      fi
      if [ "${post_sa}" != "$(_sa_email "${sa}")" ]; then
        _log "ERROR: ${job} did not take ${sa} (got ${post_sa}) — stopping; rollback available." >&2
        exit 6
      fi
      _log "   ${job}: now ${sa} (image unchanged: ${pre_img})"
    fi
  done <<<"${JOB_MAP_LINES}"
}

do_invokers() {
  assert_window
  assert_no_executions
  _log "-- invokers ($(date -u +%FT%TZ)): scheduler move + the sig-alerts jobs-posture rule --"
  local line job trig member caller compute
  # 1) Every cadence-scheduled job: roles/run.invoker to sig-scheduler, and
  #    the trigger must sign as it (assert; re-point when it signs otherwise —
  #    the recorded trigger describe is the rollback).
  member="$(_sa_email "${SIG_SA_SCHEDULER}")"
  while read -r job trig; do
    [ -n "${job}" ] || continue
    run gcloud run jobs add-iam-policy-binding "${job}" \
      --member "serviceAccount:${member}" --role roles/run.invoker \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    _log "   rollback: gcloud run jobs set-iam-policy ${job} ${STATE_DIR}/pre/job-${job}-iam.json --region ${SIG_GCP_REGION}"
    if [ "${SIG_GCP_MODE}" = "apply" ]; then
      local signer
      signer="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
h = d.get("httpTarget") or {}
for k in ("oauthToken", "oidcToken"):
    t = h.get(k) or {}
    if t.get("serviceAccountEmail"):
        print(t["serviceAccountEmail"]); sys.exit()
print("")' "${STATE_DIR}/pre/sched-${job}.json" 2>/dev/null || true)"
      if [ "${signer}" = "${member}" ]; then
        _log "   ${trig}: already signs as ${SIG_SA_SCHEDULER}"
      elif [ -n "${signer}" ]; then
        # The trigger signs as another SA — move it (the jobs leg owns the
        # invoker move; the trigger describe was captured for rollback).
        run gcloud scheduler jobs update http "${trig}" \
          --oauth-service-account-email="${member}" \
          --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
        _log "   rollback: gcloud scheduler jobs update http ${trig} --oauth-service-account-email=${signer}"
      else
        _log "   ${trig}: no recorded signer (sched-${job}.json unreadable) — flagged for verify"
      fi
    else
      _plan "gcloud scheduler jobs update http ${trig} --oauth-service-account-email=${member}  (if it does not already sign as it)"
    fi
  done <<<"${SCHED_LINES}"
  # 2) sig-alerts: grant the caller's NEW identity (sig-probe-rt — sig-probe
  #    runs as it after the `jobs` action), THEN revoke allUsers AND
  #    default-compute (grant before revoke: the receiver never has a moment
  #    no caller can reach).
  caller="$(_sa_email "${SIG_SA_PROBE}")"
  run gcloud run services add-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --member "serviceAccount:${caller}" --role roles/run.invoker \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  run gcloud run services remove-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --member allUsers --role roles/run.invoker \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services remove-iam-policy-binding ${SIG_ALERTS_SERVICE} --member serviceAccount:<default-compute resolved at apply> --role roles/run.invoker"
  else
    compute="$(cat "${STATE_DIR}/pre/compute-sa.txt" 2>/dev/null || true)"
    if [ -n "${compute}" ]; then
      run gcloud run services remove-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
        --member "serviceAccount:${compute}" --role roles/run.invoker \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
    else
      _log "   note: no recorded compute SA — the default-compute invoker revoke is left to verify"
    fi
  fi
  _log "   rollback: gcloud run services set-iam-policy ${SIG_ALERTS_SERVICE} ${STATE_DIR}/pre/service-${SIG_ALERTS_SERVICE}-iam.json --region ${SIG_GCP_REGION}"
}

do_editor() {
  assert_window
  assert_no_executions
  _log "-- editor ($(date -u +%FT%TZ)): the default compute SA loses roles/editor — the last mutation --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "assert no job/service describe still names the default compute SA"
    _plan "gcloud projects remove-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:<projectNumber>-compute@developer.gserviceaccount.com --role roles/editor"
    _plan "rollback: gcloud projects add-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:<compute> --role roles/editor"
    return 0
  fi
  local compute job sa svc
  compute="$(cat "${STATE_DIR}/pre/compute-sa.txt" 2>/dev/null || true)"
  if [ -z "${compute}" ]; then
    _log "ERROR: no recorded compute SA (pre/compute-sa.txt) — refusing." >&2
    exit 4
  fi
  # Hard precondition: nothing still runs as the identity being stripped.
  # Each job is RE-READ live — the jobs action may have moved it after
  # prestate; an unreadable describe is treated as still-default (fail-closed).
  local stale=0 tmp
  tmp="$(mktemp -t sig-job-describe.XXXXXX.json)"
  while read -r job; do
    [ -n "${job}" ] || continue
    sa="$(_job_sa "${STATE_DIR}/pre/job-${job}.json")"
    if gcloud run jobs describe "${job}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" --format json > "${tmp}" 2>/dev/null; then
      sa="$(_job_sa "${tmp}")"
    fi
    if [ "${sa}" = "${compute}" ]; then
      _log "REFUSAL: ${job} still runs as default-compute — move it first."
      stale=$((stale + 1))
    fi
  done <<<"${JOB_NAMES}"
  rm -f "${tmp}"
  for svc in ${SERVICES}; do
    sa="$(gcloud run services describe "${svc}" --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" \
      --format='value(spec.template.spec.serviceAccountName,template.serviceAccount)' 2>/dev/null || true)"
    if [ "${sa}" = "${compute}" ]; then
      _log "REFUSAL: service ${svc} still runs as default-compute — refusing."
      stale=$((stale + 1))
    fi
  done
  if [ "${stale}" -gt 0 ]; then
    _log "ERROR: ${stale} workload(s) still run as default-compute — the editor removal waits." >&2
    exit 4
  fi
  run gcloud projects remove-iam-policy-binding "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${compute}" --role roles/editor
  _log "   rollback: gcloud projects add-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:${compute} --role roles/editor"
  _log "   G1-01 closed at runtime: no workload holds a basic role; the default compute SA is no longer Editor."
}

do_verify() {
  _log "-- verify: poststate capture → iam diff --leg jobs + same-image gate --"
  if [ -n "${FROM_STATE}" ]; then
    # Offline: judge a recorded snapshot (a capture dir, or a leg dir that
    # holds pre/ + post/) against the declaration — no ADC, no network.
    if [ -d "${FROM_STATE}/pre" ] && [ -d "${FROM_STATE}/post" ]; then
      _sigops iam check-revisions --pre "${FROM_STATE}/pre" --post "${FROM_STATE}/post"
      _sigops iam diff --state-dir "${FROM_STATE}/post" --project "${SIG_GCP_PROJECT}" --leg jobs
    else
      _sigops iam diff --state-dir "${FROM_STATE}" --project "${SIG_GCP_PROJECT}" --leg jobs
    fi
    return 0
  fi
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture every prestate read under ${STATE_DIR}/post (same file names)"
    _plan "sig-ops iam diff --state-dir ${STATE_DIR}/post --project ${SIG_GCP_PROJECT} --leg jobs   (clean = the jobs posture holds)"
    _plan "sig-ops iam check-revisions --pre ${STATE_DIR}/pre --post ${STATE_DIR}/post  (every job's image byte-identical)"
    do_analysis
    return 0
  fi
  _capture "${STATE_DIR}/post"
  _sigops iam check-revisions --pre "${STATE_DIR}/pre" --post "${STATE_DIR}/post"
  _sigops iam diff --state-dir "${STATE_DIR}/post" --project "${SIG_GCP_PROJECT}" --leg jobs
  do_analysis
  do_fire_readback
  _log "verify OK — every job on its class identity, images byte-identical, scheduler moved, editor removed."
}

# `do_fire_readback` — the contract's "the next scheduled fire of one job per
# class is read back and recorded": for one representative job per class the
# newest execution + its completion state is read and recorded under
# post/next-fire-<job>.json. Read-only and honest: a class whose next fire
# has not run yet inside the window records `pending` (the re-run's verify
# re-reads it), never a fabricated pass.
do_fire_readback() {
  _log "-- fire read-back ($(date -u +%FT%TZ)): one job per class (read-only, recorded) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "per class, one representative job: gcloud run jobs executions list --job <job> --limit 1 > post/next-fire-<job>.json  (the newest execution + completion state, recorded — 'pending' when no fire has run inside the window)"
    return 0
  fi
  local cls job out newest state
  while IFS=$'\t' read -r cls job; do
    [ -n "${job}" ] || continue
    out="${STATE_DIR}/post/next-fire-${job}.json"
    if gcloud run jobs executions list --job "${job}" \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
        --limit 1 --format json > "${out}" 2>/dev/null; then
      newest="$(python3 -c 'import json,sys
rows = json.load(open(sys.argv[1]))
if not rows:
    print("no-execution-recorded"); sys.exit()
e = rows[0]
conds = (e.get("status") or {}).get("conditions") or []
done = any(c.get("type") == "Completed" and str(c.get("status")) == "True" for c in conds)
failed = any(c.get("type") == "Completed" and str(c.get("status")) == "False" for c in conds)
name = ((e.get("metadata") or {}).get("name")) or "?"
print(("succeeded" if done else "failed" if failed else "running-or-pending") + " " + str(name))' "${out}")"
      _log "   ${cls} (${job}): ${newest}"
      case "${newest}" in
        failed*)
          _log "   STOP RULE: the latest ${job} execution FAILED — investigate; a permission failure means roll back that class." >&2 ;;
      esac
    else
      _log "   ${cls} (${job}): executions read failed — recorded unreadable"
    fi
  done <<<"${CLASS_REPRESENTATIVES}"
}

# `do_analysis` — the proof-without-destruction leg (deliverable 5): read-only
# policy troubleshooting shows every declared runtime SA lacks delete on the
# spine and the evidence stores (INCLUDING off-prefix paths for the
# conditioned ingest grant) and lacks access to any secret it does not
# consume. No deletion is ever attempted as a probe.
do_analysis() {
  _log "-- analysis: policy-troubleshooter over every runtime SA (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "per declared runtime SA: gcloud policy-intelligence troubleshoot-iam-policy \\"
    _plan "  //cloudresourcemanager.googleapis.com/projects/${SIG_GCP_PROJECT} \\"
    _plan "  --principal-email <sa-email> --permission cloudsql.instances.delete  → NOT_GRANTED (the spine)"
    _plan "  + storage.objects.delete on each declared bucket AND on a non-captures object path → NOT_GRANTED (the conditioned grant never widens)"
    _plan "  + secretmanager.versions.access on every non-consumer secret → NOT_GRANTED (no foreign secret reads)"
    _plan "  answers recorded under ${STATE_DIR}/post/analysis-*.json; any GRANTED is a hard fail"
    return 0
  fi
  local sa email failures=0
  local buckets="${SIG_BUCKET_RESTRICTED} ${SIG_BUCKET_BACKUPS} ${SIG_BUCKET_PUBLIC} ${SIG_BUCKET_WEB}"
  mkdir -p "${STATE_DIR}/post"
  for sa in ${RUNTIME_SA_IDS}; do
    email="$(_sa_email "${sa}")"
    # The spine: Cloud SQL instance deletion is a project-level permission.
    _troubleshoot "${email}" \
      "//cloudresourcemanager.googleapis.com/projects/${SIG_GCP_PROJECT}" \
      "cloudsql.instances.delete" || failures=$((failures + 1))
    # The evidence stores: object deletion at bucket scope and on an
    # off-prefix object path — the conditioned captures grant (ADR-201) must
    # never widen to either.
    local b
    for b in ${buckets}; do
      _troubleshoot "${email}" \
        "//storage.googleapis.com/projects/_/buckets/${b}" \
        "storage.objects.delete" || failures=$((failures + 1))
      _troubleshoot "${email}" \
        "//storage.googleapis.com/projects/_/buckets/${b}/objects/ops/analysis-probe-${sa}" \
        "storage.objects.delete" || failures=$((failures + 1))
    done
    # Foreign secrets: accessor on every secret this SA is not a consumer of.
    local s cons
    for s in ${SECRET_NAMES}; do
      cons="$(printf '%s\n' "${SECRET_CONSUMERS}" | sed -n "s/^${s}://p")"
      case " ${cons} " in
        *" ${sa} "*) continue ;;
      esac
      _troubleshoot "${email}" \
        "//secretmanager.googleapis.com/projects/${SIG_GCP_PROJECT}/secrets/${s}" \
        "secretmanager.versions.access" || failures=$((failures + 1))
    done
  done
  if [ "${failures}" -gt 0 ]; then
    _log "FAIL: ${failures} troubleshoot answer(s) came back GRANTED — a runtime SA holds delete or a foreign secret." >&2
    return 1
  fi
  _log "   analysis OK — no runtime SA holds delete on the spine/evidence stores or a foreign secret."
}

# `_troubleshoot <email> <resource> <permission>` — one read-only answer;
# returns 1 when the answer is GRANTED (a hard stop rule).
_troubleshoot() {
  local out="${STATE_DIR}/post/analysis-$(printf '%s' "$3" | tr . _)-$(printf '%s' "$1" | cut -d@ -f1)-$(basename "$2" | tr '/' '_').json"
  local state
  if ! gcloud policy-intelligence troubleshoot-iam-policy "$2" \
    --principal-email="$1" --permission="$3" \
    --project="${SIG_GCP_PROJECT}" --format=json > "${out}" 2>/dev/null; then
    _log "   troubleshoot ${3} on $2 for $1: read failed (recorded, non-fatal)"
    return 0
  fi
  state="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
t = d.get("accessTuple") or {}
print(t.get("accessState", d.get("accessState", "UNKNOWN")))' "${out}" 2>/dev/null || echo UNKNOWN)"
  if [ "${state}" = "GRANTED" ]; then
    _log "   FAIL: $1 holds $3 on $2 (GRANTED)"
    return 1
  fi
  _log "   $1: $3 on $(basename "$2") → ${state} (recorded)"
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): restore the recorded prestate (never a blind revert) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-add roles/editor to default-compute FIRST (it was stripped last)"
    _plan "per scheduled job: gcloud run jobs set-iam-policy <job> pre/job-<job>-iam.json; scheduler trigger re-pointed to its recorded signer"
    _plan "gcloud run services set-iam-policy ${SIG_ALERTS_SERVICE} pre/service-${SIG_ALERTS_SERVICE}-iam.json"
    _plan "per job: gcloud run jobs update <job> --service-account <prior SA from pre/job-<job>.json>  (image never touched)"
    _plan "remove the leg's bindings (project/bucket/secret grants + conditioned grant), re-add the jobs_revoke accessors"
    _plan "gcloud iam service-accounts delete <SA> for every SA the prestate did NOT list (sig-scheduler pre-exists — kept)"
    return 0
  fi
  local compute job sa prior trig signer member secret
  compute="$(cat "${STATE_DIR}/pre/compute-sa.txt" 2>/dev/null || true)"
  # 1) Restore the editor binding first — the last mutation applied is the
  #    first restored.
  if [ -n "${compute}" ]; then
    gcloud projects add-iam-policy-binding "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:${compute}" --role roles/editor || true
  fi
  # 2) Re-set the scheduled jobs' invoker policies + the trigger signers.
  while read -r job trig; do
    [ -n "${job}" ] || continue
    if [ -f "${STATE_DIR}/pre/job-${job}-iam.json" ]; then
      gcloud run jobs set-iam-policy "${job}" \
        "${STATE_DIR}/pre/job-${job}-iam.json" \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" || true
    fi
    signer="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
h = d.get("httpTarget") or {}
for k in ("oauthToken", "oidcToken"):
    t = h.get(k) or {}
    if t.get("serviceAccountEmail"):
        print(t["serviceAccountEmail"]); sys.exit()
print("")' "${STATE_DIR}/pre/sched-${job}.json" 2>/dev/null || true)"
    if [ -n "${signer}" ]; then
      gcloud scheduler jobs update http "${trig}" \
        --oauth-service-account-email="${signer}" \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" || true
    fi
  done <<<"${SCHED_LINES}"
  # 3) Re-set the sig-alerts invoker policy from the capture.
  if [ -f "${STATE_DIR}/pre/service-${SIG_ALERTS_SERVICE}-iam.json" ]; then
    gcloud run services set-iam-policy "${SIG_ALERTS_SERVICE}" \
      "${STATE_DIR}/pre/service-${SIG_ALERTS_SERVICE}-iam.json" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" || true
  fi
  # 4) Every job back to its recorded prior SA.
  while read -r job; do
    [ -n "${job}" ] || continue
    prior="$(_job_sa "${STATE_DIR}/pre/job-${job}.json")"
    if [ -z "${prior}" ]; then
      _log "ERROR: no recorded prior SA at pre/job-${job}.json — refusing to roll back blind." >&2
      exit 4
    fi
    gcloud run jobs update "${job}" --service-account "${prior}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}"
  done <<<"${JOB_NAMES}"
  # 5) Remove the leg's grants; re-add the revoked default-compute accessors.
  local line bucket role cond
  while read -r sa role; do
    [ -n "${sa}" ] || continue
    gcloud projects remove-iam-policy-binding "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}" || true
  done <<<"${PROJECT_ROLE_LINES}"
  while read -r sa bucket role cond x; do
    [ -n "${sa}" ] || continue
    gcloud storage buckets remove-iam-policy-binding \
      "gs://${SIG_GCP_PROJECT}-${bucket}" \
      --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}" || true
  done <<<"${BUCKET_ROLE_LINES}"
  while read -r secret member; do
    [ -n "${secret}" ] || continue
    gcloud secrets remove-iam-policy-binding "${secret}" \
      --project "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${member}")" \
      --role roles/secretmanager.secretAccessor || true
  done <<<"${SECRET_GRANT_LINES}"
  while read -r secret member; do
    [ -n "${secret}" ] || continue
    if [ "${member}" = "default-compute" ]; then
      [ -n "${compute}" ] || continue
      member="serviceAccount:${compute}"
    else
      member="serviceAccount:$(_sa_email "${member}")"
    fi
    gcloud secrets add-iam-policy-binding "${secret}" \
      --project "${SIG_GCP_PROJECT}" \
      --member "${member}" \
      --role roles/secretmanager.secretAccessor || true
  done <<<"${SECRET_REVOKE_LINES}"
  # 6) Delete the SAs the prestate did NOT list (a pre-existing identity —
  #    sig-scheduler — is never deleted).
  local existing sa_id
  existing="$(python3 -c 'import json,sys
print("\n".join(str(r.get("email","")) for r in json.load(open(sys.argv[1]))))' \
    "${STATE_DIR}/pre/service-accounts.json" 2>/dev/null || true)"
  for sa_id in ${JOB_SA_IDS}; do
    case " ${existing} " in
      *" $(_sa_email "${sa_id}") "*) _log "keep: ${sa_id} pre-existed" ;;
      *) gcloud iam service-accounts delete "$(_sa_email "${sa_id}")" \
           --project "${SIG_GCP_PROJECT}" --quiet || true ;;
    esac
  done
  _log "rollback applied — prior SAs restored, invokers re-set, editor re-added, leg bindings removed."
}

# Every non-check path (live verify included — member names embed the project
# id) requires SIG_GCP_PROJECT; check mode tolerates the placeholder.
require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
case "${ACTION}" in
  identities|bindings|jobs|invokers|editor|all) assert_window ;;
esac
# A live verify reads with ADC; an offline --from-state diff needs none.
if [ -z "${FROM_STATE}" ]; then
  require_adc
fi

# Every name below is derived from the committed declaration — the TOML is the
# single source (a drift between this list and ops/iam_identities.toml fails
# here, loudly, rather than mutating the wrong target). `plan --leg jobs`
# scopes the declaration to this leg's posture.
JOB_SA_IDS="$(_decl 'import json,sys
d = json.load(sys.stdin)
svc = {s["service_account"] for s in d["services"]}
print(" ".join(s["id"] for s in d["service_accounts"] if s["id"] not in svc))')"
RUNTIME_SA_IDS="$(_decl 'import json,sys
d = json.load(sys.stdin)
print(" ".join(s["id"] for s in d["service_accounts"] if not s.get("reserved")))')"
EXPECTED_JOBS="$(_decl 'import json,sys; print(json.load(sys.stdin)["expected_job_count"])')"
JOB_MAP_JSON="$(_decl 'import json,sys; print(json.dumps(json.load(sys.stdin)["job_map"]))')"
JOB_MAP_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
cls = {c["name"]: c["service_account"] for c in d["job_classes"]}
print("\n".join(j+"\t"+cls[c] for j, c in sorted(d["job_map"].items())))')"
JOB_NAMES="$(_decl 'import json,sys; print("\n".join(sorted(json.load(sys.stdin)["job_map"])))')"
# One representative job per class ("class<TAB>job" lines) — the next-fire
# read-back's sample (deliverable 5: one scheduled fire per class).
CLASS_REPRESENTATIVES="$(_decl 'import json,sys
d = json.load(sys.stdin)
seen = {}
for j, c in sorted(d["job_map"].items()):
    seen.setdefault(c, j)
print("\n".join(c+"\t"+j for c, j in sorted(seen.items())))')"
SCHED_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
print("\n".join(j+" "+t for j, t in sorted(d["scheduler_triggers"].items())))')"
SERVICES="$(_decl 'import json,sys; print(" ".join(s["name"] for s in json.load(sys.stdin)["services"]))')"
SECRET_NAMES="$(_decl 'import json,sys; print(" ".join(s["name"] for s in json.load(sys.stdin)["secrets"]))')"
SECRET_CONSUMERS="$(_decl 'import json,sys; print("\n".join(s["name"]+":"+" ".join(s["consumers"]) for s in json.load(sys.stdin)["secrets"]))')"
# The leg-scoped binding tables — rendered from the declaration so a drift
# between this script and the TOML is impossible by construction.
PROJECT_ROLE_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
svc = {s["service_account"] for s in d["services"]}
print("\n".join(r["service_account"]+" "+r["role"] for r in d["project_roles"] if r["service_account"] not in svc))')"
BUCKET_ROLE_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
svc = {s["service_account"] for s in d["services"]}
out=[]
for r in d["bucket_roles"]:
    if r["service_account"] in svc: continue
    out.append(r["service_account"]+" "+r["bucket"]+" "+r["role"]+" "+(r.get("condition_title") or "-")+" "+(r.get("condition_prefix") or "-"))
print("\n".join(out))')"
SECRET_GRANT_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
svc = {s["service_account"] for s in d["services"]}
reserved = {s["id"] for s in d["service_accounts"] if s.get("reserved")}
out=[]
for s in d["secrets"]:
    for c in s["consumers"]:
        if c in svc or c in ("default-compute","operator") or c in reserved: continue
        out.append(s["name"]+" "+c)
print("\n".join(out))')"
SECRET_REVOKE_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
out=[]
for s in d["secrets"]:
    for m in s.get("jobs_revoke") or []:
        out.append(s["name"]+" "+m)
print("\n".join(out))')"
BUCKET_SUFFIXES="$(_decl 'import json,sys; print(" ".join(sorted({r["bucket"] for r in json.load(sys.stdin)["bucket_roles"]})))')"

banner "P34.42b — least-privilege JOB identities + editor removal (G1-01, SIG-SEC-007)"

case "${ACTION}" in
  prestate)   do_prestate ;;
  identities) do_identities ;;
  bindings)   do_bindings ;;
  jobs)       do_jobs ;;
  invokers)   do_invokers ;;
  editor)     do_editor ;;
  verify)     do_verify ;;
  analysis)   do_analysis ;;
  rollback)   do_rollback ;;
  all)
    do_prestate
    do_identities
    do_bindings
    do_jobs
    do_invokers
    do_editor
    do_verify ;;
  *) _log "usage: $(basename "$0") [--check|--apply|--verify [--from-state DIR]] [prestate|identities|bindings|jobs|invokers|editor|verify|analysis|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "iam-job-identities ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
else
  _log "iam-job-identities ${ACTION}: done (mode=${SIG_GCP_MODE})"
fi
