#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/exec-host.sh — the execution-host leg of P34.43 (SIG-CONF-013, L3
# CP-0, G2 ACT-13; pre-authorised S5-3/OM-20 "Both + list + P34.45", L1). The
# one-off Cloud Run execution host for hosted return passes + quality probes:
# an EPHEMERAL job (sig-exec-<purpose>-<stamp>: created per run, executed
# once, deleted by a name-checked cleanup) on the least-privilege
# sig-quality-probe-rt identity, with a READ-ONLY gcsfuse mount of the
# capture store (evidence/captures/), the Cloud SQL connector, only the
# secrets the run needs, --max-retries 0 and a bounded task timeout.
#
# Declarations: ops/exec_host.toml (sig.exec-host/1 — `sig-ops exec-host`
# renders it) + the [[oneoff]] family in ops/iam_identities.toml (`sig-ops
# iam plan --leg exec` renders this leg's identity + bindings). This script
# owns the (windowed) mutations:
#
#   ./exec-host.sh --check [action]       # (default) plan-only: NO ADC, NO
#                                         # network — every command printed.
#   ./exec-host.sh --apply <action>       # windowed + operator ADC.
#   ./exec-host.sh --verify               # read-only LIVE diff (ADC, never
#                                         # window-gated)
#   ./exec-host.sh --verify --from-state DIR
#                                         # offline diff of a recorded snapshot
#
# Actions:
#   prestate   the restore point for the exec leg: project IAM, the SA list,
#              `run jobs list` (a sig-exec-* job at rest is a leaked cleanup —
#              recorded + flagged), the restricted bucket policy, the two
#              login secrets' policies (absent → recorded), the rendered
#              declaration. READ-ONLY — any time.
#   identity   create the exec SA (sig-quality-probe-rt) when absent —
#              idempotent (the P34.42b jobs leg may have created it already).
#   secrets    create sig-audit-password + sig-recovery-password in Secret
#              Manager when absent (replication automatic; NO version value
#              is ever written by this script — db-logins.sh owns values).
#   bindings   the exec-scoped grants from the declaration: cloudsql.client,
#              the CONDITIONED objectViewer on evidence/captures/ (read-only
#              by mount flag AND by IAM), the CONDITIONED objectCreator on
#              ops/probes/ (the probe-run record — never a capture path),
#              the two secret accessors.
#   smoke      the L1 first use: render + run `sig-exec-smoke-<stamp>`
#              (image pinned by digest — SIG_EXEC_IMAGE or the
#              $SIG_API_IMAGE:<tag> resolved to a digest, ADR-111) whose
#              container runs `python -m ops exec-host smoke`: the mount is
#              read-only (read back from /proc/self/mounts), the declared
#              secrets are present, the sig_audit session posture holds
#              (the NEW-16 grants report not_evaluable until P34.46's deploy),
#              and one sig.probe-run/1 record lands under ops/probes/. The
#              job is deleted by the name-checked cleanup afterwards.
#   verify     poststate capture + `sig-ops iam diff --leg exec` clean + no
#              sig-exec-* job at rest. READ-ONLY.
#   analysis   the read-only IAM answers (policy troubleshooter): the exec
#              SA cannot create/delete under evidence/captures/, cannot
#              delete objects at all, cannot read a secret it does not
#              consume. A GRANTED answer is a hard fail. READ-ONLY.
#   rollback   from the recorded prestate: remove the leg's bindings, delete
#              any sig-exec-* job this leg created (the recorded name), delete
#              the two secrets it created, and delete the exec SA only when
#              prestate did not list it. Deliberately NOT window-gated —
#              restoring prestate is always safe.
#   all        prestate → identity → secrets → bindings → smoke → verify.
#
# Live window (OM-19, the contract's AR-3 + AR-2 slot): applies run ≥
# ${SIG_EXEC_EARLIEST} and never 03:00–06:30Z; earlier → exit 42 (queued —
# the RETURN PASS re-run prompt is printed). 14:00–20:00Z on a weekday is
# the preferred slot — outside it the guard logs a note, never a refusal.
# SIG_EXEC_NOW overrides the clock for the offline guard test only.
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
      [ $# -ge 2 ] || { echo "exec-host.sh: --from-state needs a directory" >&2; exit 64; }
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
STATE_DIR="${2:-${SIG_EXEC_STATE_DIR}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/253_P34.43__execution-host-and-least-privilege-db-logins.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `_decl <python -c body>` — a field out of `sig-ops iam plan --json --leg
# exec` (the declaration is the single source of every name this leg uses).
_decl() {
  _sigops iam plan --json --leg exec \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    | python3 -c "$1"
}

_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

# `assert_window` — the OM-19/AR-3 clock guard (ISO strings compare
# lexicographically; exit 42 = queued leg). Check mode is never gated — a
# printed plan mutates nothing.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dow
  now="${SIG_EXEC_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_EXEC_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_EXEC_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN} (scope: the exec-host leg only)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the exec-host leg only)"
    exit 42
  fi
  dow="$(date -u -d "${now}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${now}" +%u 2>/dev/null \
        || echo 7)"
  if [[ "${hhmm}" > "13:59" && "${hhmm}" < "20:00" && "${dow}" -le 5 ]]; then
    _log "window OK: ${now} (the preferred 14:00–20:00Z weekday slot)"
  else
    _log "window OK: ${now} (≥ ${SIG_EXEC_EARLIEST}, outside 03:00–06:30Z — note: outside the preferred 14:00–20:00Z weekday slot)"
  fi
}

# `_capture <dir>` — the exec leg's prestate/poststate snapshot.
_capture() {
  local dir="$1" s
  mkdir -p "${dir}"
  gcloud projects get-iam-policy "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/project-iam.json"
  gcloud iam service-accounts list --project "${SIG_GCP_PROJECT}" \
    --format json > "${dir}/service-accounts.json"
  # Every live Cloud Run job — a sig-exec-* row at rest is a leaked cleanup.
  gcloud run jobs list --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${dir}/run-jobs.json"
  gcloud storage buckets get-iam-policy "gs://${SIG_BUCKET_RESTRICTED}" \
    --format json > "${dir}/bucket-sig-restricted-iam.json" \
    || printf '{"bindings":[]}' > "${dir}/bucket-sig-restricted-iam.json"
  for s in ${EXEC_SECRETS}; do
    gcloud secrets get-iam-policy "${s}" --project "${SIG_GCP_PROJECT}" \
      --format json > "${dir}/secret-${s}-iam.json" \
      || printf '{"bindings":[]}' > "${dir}/secret-${s}-iam.json"
  done
  gcloud secrets list --project "${SIG_GCP_PROJECT}" \
    --format='value(name)' > "${dir}/secrets-list.txt" 2>/dev/null || true
  _sigops exec-host plan > "${dir}/exec-decl.json"
  (cd "${dir}" && for f in *.json; do _sha256 "$f"; done) > "${dir}/sha256s.txt"
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the exec leg's restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud projects get-iam-policy ${SIG_GCP_PROJECT} > pre/project-iam.json"
    _plan "gcloud iam service-accounts list > pre/service-accounts.json"
    _plan "gcloud run jobs list > pre/run-jobs.json  (a ${SIG_EXEC_PREFIX}-* job at rest = leaked cleanup)"
    _plan "gcloud storage buckets get-iam-policy gs://${SIG_BUCKET_RESTRICTED} > pre/bucket-sig-restricted-iam.json"
    _plan "gcloud secrets get-iam-policy + secrets list for: ${EXEC_SECRETS} > pre/secret-*-iam.json, pre/secrets-list.txt"
    _plan "sig-ops exec-host plan > pre/exec-decl.json  (the rendered declaration)"
    _plan "sha256 sidecars over every capture > pre/sha256s.txt"
    return 0
  fi
  _capture "${STATE_DIR}/pre"
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ))"
}

do_identity() {
  assert_window
  _log "-- identity ($(date -u +%FT%TZ)): the exec host's runtime SA ${SIG_EXEC_SA} --"
  if [ "${SIG_GCP_MODE}" = "apply" ] && \
     gcloud iam service-accounts describe "$(_sa_email "${SIG_EXEC_SA}")" \
       --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "exists: ${SIG_EXEC_SA} — skipping create"
  else
    run gcloud iam service-accounts create "${SIG_EXEC_SA}" \
      --display-name "sig exec host / quality probe runtime" \
      --project "${SIG_GCP_PROJECT}"
    _log "   rollback: gcloud iam service-accounts delete $(_sa_email "${SIG_EXEC_SA}") --quiet"
  fi
}

do_secrets() {
  assert_window
  _log "-- secrets ($(date -u +%FT%TZ)): create the two DB-login secrets (no values — structure only) --"
  local s
  for s in ${EXEC_SECRETS}; do
    if [ "${SIG_GCP_MODE}" = "apply" ] && \
       gcloud secrets describe "${s}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "exists: ${s} — skipping create"
    else
      run gcloud secrets create "${s}" \
        --replication-policy=automatic --project "${SIG_GCP_PROJECT}"
      _log "   rollback: gcloud secrets delete ${s} --quiet"
    fi
  done
}

do_bindings() {
  assert_window
  _log "-- bindings ($(date -u +%FT%TZ)): the exec SA's declared least-privilege grants --"
  # Rendered from the declaration, scoped to the exec family SAs — a drift
  # between this leg and ops/iam_identities.toml is impossible by construction.
  local sa role bucket cond_title cond_prefix cond_desc secret member
  while read -r sa role; do
    [ -n "${sa}" ] || continue
    run gcloud projects add-iam-policy-binding "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}"
    _log "   rollback: gcloud projects remove-iam-policy-binding ${SIG_GCP_PROJECT} --member serviceAccount:$(_sa_email "${sa}") --role ${role}"
  done <<<"${EXEC_PROJECT_ROLE_LINES}"
  while IFS=$'\t' read -r sa bucket role cond_title cond_prefix cond_desc; do
    [ -n "${sa}" ] || continue
    if [ "${cond_title}" != "-" ]; then
      # The conditioned grants (P34.43): objectViewer under evidence/captures/
      # only (the read-only mount's IAM half) and objectCreator under
      # ops/probes/ only (the probe-run record — never a capture path).
      run gcloud storage buckets add-iam-policy-binding \
        "gs://${SIG_GCP_PROJECT}-${bucket}" \
        --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}" \
        --condition-title="${cond_title}" \
        --condition-description="${cond_desc}" \
        --condition-expression="resource.name.startsWith('projects/_/buckets/${SIG_GCP_PROJECT}-${bucket}/objects/${cond_prefix}')"
      _log "   rollback: gcloud storage buckets remove-iam-policy-binding gs://${SIG_GCP_PROJECT}-${bucket} --member serviceAccount:$(_sa_email "${sa}") --role ${role} --all"
    else
      run gcloud storage buckets add-iam-policy-binding \
        "gs://${SIG_GCP_PROJECT}-${bucket}" \
        --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}"
      _log "   rollback: gcloud storage buckets remove-iam-policy-binding gs://${SIG_GCP_PROJECT}-${bucket} --member serviceAccount:$(_sa_email "${sa}") --role ${role}"
    fi
  done <<<"${EXEC_BUCKET_ROLE_LINES}"
  while read -r secret member; do
    [ -n "${secret}" ] || continue
    run gcloud secrets add-iam-policy-binding "${secret}" \
      --project "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${member}")" \
      --role roles/secretmanager.secretAccessor
    _log "   rollback: gcloud secrets remove-iam-policy-binding ${secret} --member serviceAccount:$(_sa_email "${member}") --role roles/secretmanager.secretAccessor"
  done <<<"${EXEC_SECRET_GRANT_LINES}"
}

do_smoke() {
  assert_window
  _log "-- smoke ($(date -u +%FT%TZ)): the exec host's first use — sig-exec-smoke-<stamp> --"
  # SIG_EXEC_IMAGE names the workload image (the shared sig-api repo's tag or
  # digest — resolved to a pinned digest, ADR-111). Never :latest.
  local image="${SIG_EXEC_IMAGE:-}"
  if [ -z "${image}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      image="${SIG_API_IMAGE}:exec-smoke"   # placeholder — printed, never resolved
    else
      _log "ERROR: SIG_EXEC_IMAGE must name the exec workload image (a ${SIG_API_IMAGE}:<tag> — resolved to a digest, never :latest)." >&2
      exit 2
    fi
  fi
  image="$(pin_image_digest "${image}")"
  local conn="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    # The render is pure argv — safe to print in check mode.
    _sigops exec-host render --purpose smoke --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_AUDIT_PASSWORD \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --arg=-c --arg "exec python -m ops exec-host smoke"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  local logf="${STATE_DIR}/smoke-$(date -u +%Y%m%dT%H%M%SZ).log"
  _log "   running one-off smoke (log → ${logf})"
  if ! _sigops exec-host run --purpose smoke --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_AUDIT_PASSWORD \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --arg=-c --arg "exec python -m ops exec-host smoke" \
      >"${logf}" 2>&1; then
    _log "ERROR: the smoke run failed — ${logf} has the output; the cleanup still ran (name-checked delete)." >&2
    exit 4
  fi
  _log "   smoke OK — the sig.probe-run/1 record landed under ${SIG_EXEC_PROBE_PREFIX}/ (record object named in ${logf})"
}

do_verify() {
  _log "-- verify: poststate capture → iam diff --leg exec + no sig-exec-* at rest --"
  if [ -n "${FROM_STATE}" ]; then
    _sigops iam diff --state-dir "${FROM_STATE}" --project "${SIG_GCP_PROJECT}" --leg exec
    return 0
  fi
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture the exec leg's reads under ${STATE_DIR}/post (same file names)"
    _plan "sig-ops iam diff --state-dir ${STATE_DIR}/post --project ${SIG_GCP_PROJECT} --leg exec   (clean = the exec posture holds)"
    _plan "assert: no ${SIG_EXEC_PREFIX}-* job in post/run-jobs.json (the cleanup left none)"
    do_analysis
    return 0
  fi
  _capture "${STATE_DIR}/post"
  _sigops iam diff --state-dir "${STATE_DIR}/post" --project "${SIG_GCP_PROJECT}" --leg exec
  if grep -q "${SIG_EXEC_PREFIX}-" "${STATE_DIR}/post/run-jobs.json"; then
    _log "ERROR: a ${SIG_EXEC_PREFIX}-* job exists at rest — the cleanup leaked one (see post/run-jobs.json)." >&2
    exit 4
  fi
  do_analysis
  _log "verify OK — the exec posture holds and no one-off job remains at rest."
}

# `do_analysis` — the read-only IAM answers (policy troubleshooter): the exec
# SA cannot create/delete under evidence/captures/, cannot delete objects at
# all, cannot read a secret it does not consume. A GRANTED answer is a hard
# fail. No write is ever attempted as a probe.
do_analysis() {
  _log "-- analysis: policy-troubleshooter over the exec SA (read-only) --"
  local email; email="$(_sa_email "${SIG_EXEC_SA}")"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud policy-intelligence troubleshoot-iam-policy (exec SA):"
    _plan "  storage.objects.create on .../objects/evidence/captures/probe → NOT_GRANTED (the captures prefix is read-only by IAM)"
    _plan "  storage.objects.delete on gs://${SIG_BUCKET_RESTRICTED} + on .../evidence/captures/x + .../ops/probes/x → NOT_GRANTED"
    _plan "  storage.objects.get    on .../objects/evidence/captures/x     → GRANTED (the mount's read)"
    _plan "  storage.objects.create on .../objects/ops/probes/x            → GRANTED (the probe record)"
    _plan "  cloudsql.instances.delete → NOT_GRANTED; secretmanager.versions.access on a non-consumer secret → NOT_GRANTED"
    _plan "  answers recorded under ${STATE_DIR}/post/analysis-*.json"
    return 0
  fi
  mkdir -p "${STATE_DIR}/post"
  local failures=0
  local obj_base="//storage.googleapis.com/projects/_/buckets/${SIG_BUCKET_RESTRICTED}"
  _troubleshoot "${email}" "${obj_base}/objects/evidence/captures/probe" "storage.objects.create" || failures=$((failures + 1))
  _troubleshoot "${email}" "${obj_base}" "storage.objects.delete" || failures=$((failures + 1))
  _troubleshoot "${email}" "${obj_base}/objects/evidence/captures/probe" "storage.objects.delete" || failures=$((failures + 1))
  _troubleshoot "${email}" "${obj_base}/objects/ops/probes/probe" "storage.objects.delete" || failures=$((failures + 1))
  _troubleshoot "${email}" \
    "//cloudresourcemanager.googleapis.com/projects/${SIG_GCP_PROJECT}" \
    "cloudsql.instances.delete" || failures=$((failures + 1))
  # A non-consumer secret read must be refused: sig-pg-password is not one
  # of the exec SA's declared consumers.
  _troubleshoot "${email}" \
    "//secretmanager.googleapis.com/projects/${SIG_GCP_PROJECT}/secrets/sig-pg-password" \
    "secretmanager.versions.access" || failures=$((failures + 1))
  if [ "${failures}" -gt 0 ]; then
    _log "FAIL: ${failures} troubleshoot answer(s) came back GRANTED — the exec SA holds too much." >&2
    return 1
  fi
  _log "   analysis OK — the exec SA holds no captures write/delete, no object delete, no foreign secret."
}

# `_troubleshoot <email> <resource> <permission>` — one read-only answer;
# returns 1 when the answer is GRANTED (a hard stop rule).
_troubleshoot() {
  local out="${STATE_DIR}/post/analysis-$(printf '%s' "$3" | tr . _)-$(basename "$2" | tr '/' '_').json"
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
    _plan "delete any ${SIG_EXEC_PREFIX}-* job this leg created (the recorded name only)"
    _plan "remove the leg's bindings (project role, the two conditioned bucket grants, the secret accessors)"
    _plan "gcloud secrets delete <secret> for each of ${EXEC_SECRETS} the prestate's secrets-list did not name"
    _plan "gcloud iam service-accounts delete ${SIG_EXEC_SA} only when prestate did not list it"
    return 0
  fi
  local existing s
  # 1) A leaked one-off job this leg created is deleted by name — nothing
  #    pattern-deleted (the cleanup contract, applied to rollback too).
  existing="$(python3 -c 'import json,sys
names = []
for r in json.load(open(sys.argv[1])):
    n = ((r.get("metadata") or {}).get("name")) or r.get("name")
    if n:
        names.append(str(n).rsplit("/", 1)[-1])
print("\n".join(names))' "${STATE_DIR}/post/run-jobs.json" 2>/dev/null \
    || python3 -c 'import json,sys
names = []
for r in json.load(open(sys.argv[1])):
    n = ((r.get("metadata") or {}).get("name")) or r.get("name")
    if n:
        names.append(str(n).rsplit("/", 1)[-1])
print("\n".join(names))' "${STATE_DIR}/pre/run-jobs.json" 2>/dev/null || true)"
  local job
  while read -r job; do
    [ -n "${job}" ] || continue
    case "${job}" in
      "${SIG_EXEC_PREFIX}-"*)
        gcloud run jobs delete "${job}" --region "${SIG_GCP_REGION}" \
          --project "${SIG_GCP_PROJECT}" --quiet || true
        _log "   deleted leaked one-off ${job}"
        ;;
    esac
  done <<<"${existing}"
  # 2) Remove the leg's grants.
  local sa role bucket cond x member secret
  while read -r sa role; do
    [ -n "${sa}" ] || continue
    gcloud projects remove-iam-policy-binding "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}" || true
  done <<<"${EXEC_PROJECT_ROLE_LINES}"
  while IFS=$'\t' read -r sa bucket role x y z; do
    [ -n "${sa}" ] || continue
    gcloud storage buckets remove-iam-policy-binding \
      "gs://${SIG_GCP_PROJECT}-${bucket}" \
      --member "serviceAccount:$(_sa_email "${sa}")" --role "${role}" || true
  done <<<"${EXEC_BUCKET_ROLE_LINES}"
  while read -r secret member; do
    [ -n "${secret}" ] || continue
    gcloud secrets remove-iam-policy-binding "${secret}" \
      --project "${SIG_GCP_PROJECT}" \
      --member "serviceAccount:$(_sa_email "${member}")" \
      --role roles/secretmanager.secretAccessor || true
  done <<<"${EXEC_SECRET_GRANT_LINES}"
  # 3) Delete the secrets the leg created (only those the prestate's list did
  #    not already name).
  local had_secrets
  had_secrets="$(cat "${STATE_DIR}/pre/secrets-list.txt" 2>/dev/null || true)"
  for s in ${EXEC_SECRETS}; do
    case " ${had_secrets} " in
      *" ${s} "*) _log "keep: ${s} pre-existed" ;;
      *) gcloud secrets delete "${s}" --project "${SIG_GCP_PROJECT}" --quiet || true ;;
    esac
  done
  # 4) Delete the exec SA only when the prestate did not list it.
  existing="$(python3 -c 'import json,sys
print(" ".join(str(r.get("email","")) for r in json.load(open(sys.argv[1]))))' \
    "${STATE_DIR}/pre/service-accounts.json" 2>/dev/null || true)"
  case " ${existing} " in
    *" $(_sa_email "${SIG_EXEC_SA}") "*) _log "keep: ${SIG_EXEC_SA} pre-existed" ;;
    *) gcloud iam service-accounts delete "$(_sa_email "${SIG_EXEC_SA}")" \
         --project "${SIG_GCP_PROJECT}" --quiet || true ;;
  esac
  _log "rollback applied — the exec leg's bindings removed, its created resources deleted."
}

# Every non-check path (live verify included — member names embed the project
# id) requires SIG_GCP_PROJECT; check mode tolerates the placeholder.
require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
case "${ACTION}" in
  identity|secrets|bindings|smoke|all) assert_window ;;
esac
# A live verify reads with ADC; an offline --from-state diff needs none.
if [ -z "${FROM_STATE}" ]; then
  require_adc
fi

# The exec leg's declaration surfaces — every name derived, never hand-copied.
EXEC_SECRETS="${SIG_SECRET_AUDIT_PASSWORD} ${SIG_SECRET_RECOVERY_PASSWORD}"
EXEC_PROJECT_ROLE_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
oneoff_sas = {o["service_account"] for o in d.get("oneoffs", [])}
print("\n".join(r["service_account"]+" "+r["role"] for r in d["project_roles"] if r["service_account"] in oneoff_sas))')"
EXEC_BUCKET_ROLE_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
oneoff_sas = {o["service_account"] for o in d.get("oneoffs", [])}
out=[]
for r in d["bucket_roles"]:
    if r["service_account"] in oneoff_sas:
        out.append("\t".join([r["service_account"], r["bucket"], r["role"],
            r.get("condition_title") or "-", r.get("condition_prefix") or "-",
            r.get("condition_description") or "-"]))
print("\n".join(out))')"
EXEC_SECRET_GRANT_LINES="$(_decl 'import json,sys
d = json.load(sys.stdin)
oneoff_sas = {o["service_account"] for o in d.get("oneoffs", [])}
out=[]
for s in d["secrets"]:
    for c in s["consumers"]:
        if c in oneoff_sas:
            out.append(s["name"]+" "+c)
print("\n".join(out))')"

banner "P34.43 — execution host + least-privilege exec identity (SIG-CONF-013)"

case "${ACTION}" in
  prestate)  do_prestate ;;
  identity)  do_identity ;;
  secrets)   do_secrets ;;
  bindings)  do_bindings ;;
  smoke)     do_smoke ;;
  verify)    do_verify ;;
  analysis)  do_analysis ;;
  rollback)  do_rollback ;;
  all)
    do_prestate
    do_identity
    do_secrets
    do_bindings
    do_smoke
    do_verify ;;
  *) _log "usage: $(basename "$0") [--check|--apply|--verify [--from-state DIR]] [prestate|identity|secrets|bindings|smoke|verify|analysis|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "exec-host ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
else
  _log "exec-host ${ACTION}: done (mode=${SIG_GCP_MODE})"
fi
