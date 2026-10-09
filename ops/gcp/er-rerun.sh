#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/er-rerun.sh — the ONE append-only camera-site ER re-run leg of
# P34.45 (ADR-153 "derivation, not identity"; ADR-206; pre-authorised
# S5-3/OM-20 "Both + list + P34.45"). Under the v3-interim ruleset the
# inferential tiers [3,4,5] are REVIEW-ONLY until an independent human B5
# evaluation exists — the re-run demotes every still-queued inferential
# decision to `proposed` on a fresh run_key and enqueues the review items
# with the explicit `no_certifying_evaluation` demotion reason.
#
# The mutation is append-only by construction: the run connects as
# `sig_materialize_login` (P34.45's least-privilege LOGIN member of the
# NOLOGIN sig_materialize group) — INSERT+SELECT on the camera-site tables
# and review_item, UPDATE/DELETE/TRUNCATE revoked, no claim-spine write.
# ONE permitted execution: a `camera_site_run` row whose ruleset_version is
# already `3-interim` makes `run` exit 42 — a second re-run needs a new
# operator decision, not a flag.
#
#   ./er-rerun.sh --check [action]   # (default) plan-only: NO ADC, NO
#                                     # network — every command printed.
#   ./er-rerun.sh --apply <action>   # windowed + dependency-gated + the
#                                     # recorded SIG_ER_RERUN_AUTHOR.
#   ./er-rerun.sh --verify           # read-only poststate diff (ADC, never
#                                     # window-gated)
#
# Actions:
#   prestate   the restore point: pg_roles, the latest camera_site_run /
#              camera_site_execution rows, per-tier/disposition counts on
#              camera_site_match, the camera review queue depth. READ-ONLY.
#   deps       the live: edges — the exec SA (live:P34.42b/43), the
#              sig-er-rerun-password secret, the v3-interim API roll live
#              (sig-api's deployed image resolves to SIG_ER_RERUN_IMAGE's
#              digest — the ER run rides the SAME image, so a rolled-back or
#              un-rolled API fails the check). Missing edge → exit 42.
#   backup     AR-2: an on-demand Cloud SQL backup of sig-pg, waited to
#              SUCCESSFUL before the first mutation.
#   login      the sig_materialize_login catalog statements + its credential
#              (generated → Secret Manager → ALTER ROLE; env-only, HG-09).
#   run        the ONE re-run: a `sig-exec-er-rerun-<stamp>` one-off on the
#              P34.43 exec host running `python -m resolution camera-sites
#              --role sig_materialize_login` over the Cloud SQL socket.
#              Refuses (exit 42) when a 3-interim run_key already exists.
#   after      poststate capture + the before/after tier-disposition diff.
#   verify     poststate + `sig-ops db-login --role sig_materialize_login
#              verify` + the recorded diff. READ-ONLY.
#   rollback   guidance only — append-only means forward-only: re-run under
#              the prior ruleset digest or PITR to the AR-2 backup. Never
#              deletes; prints the options, exits 0.
#   all        prestate → deps → backup → login → run → after → verify.
#
# Live window (OM-19, AR-3 + AR-2): applies run ≥ ${SIG_ER_RERUN_EARLIEST},
# never 03:00–06:30Z, and never inside the monthly batch window (day 6
# 00:00Z → day 13 12:00Z). Every refusal exits 42 — queued; the RETURN PASS
# re-run prompt is printed. SIG_ER_RERUN_NOW overrides the clock for the
# offline guard test only. The mutating actions additionally require
# SIG_ER_RERUN_AUTHOR — the recorded operator id authorising THIS leg
# (OM-20's pre-authorisation is a scope, not a standing credential).
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

ACTION="all"
case "${1:-}" in
  --verify)
    SIG_GCP_MODE="verify"
    ACTION="verify"
    shift
    ;;
  *)
    parse_mode "${1:-}"
    shift || true
    ACTION="${1:-all}"
    ;;
esac
export SIG_GCP_MODE
STATE_DIR="${2:-${SIG_ER_RERUN_STATE_DIR}}"

_repo="$(cd "${_here}/../.." && pwd)"
: "${SIG_PROXY_PORT:=5434}"

RERUN='implement-spec spec=docs/tickets/257_P34.45__honest-evaluation-posture.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

_sa_email() { printf '%s@%s.iam.gserviceaccount.com' "$1" "${SIG_GCP_PROJECT}"; }

# `assert_window` — the OM-19/AR-3 clock guard (exit 42 = queued leg).
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dom
  now="${SIG_ER_RERUN_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_ER_RERUN_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_ER_RERUN_EARLIEST} — the AR-3/AR-2 freeze."
    _log "re-run: ${RERUN} (scope: the v3-interim ER re-run leg)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the v3-interim ER re-run leg)"
    exit 42
  fi
  dom="${now:8:2}"
  if [[ "${dom}" > "05" && "${dom}" < "14" ]]; then
    if [[ "${dom}" < "13" || "${hhmm}" < "12:00" ]]; then
      _log "QUEUED (exit 42): ${now} is inside the monthly batch window (day 6 00:00Z → day 13 12:00Z)."
      _log "re-run: ${RERUN} (scope: the v3-interim ER re-run leg)"
      exit 42
    fi
  fi
  _log "window OK: ${now} (≥ ${SIG_ER_RERUN_EARLIEST}, outside 03:00–06:30Z, outside the batch window)"
}

# `assert_author` — OM-20's pre-authorisation is a scope; the leg still needs
# the recorded operator id for THIS apply.
assert_author() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ -z "${SIG_ER_RERUN_AUTHOR:-}" ]; then
    _log "QUEUED (exit 42): SIG_ER_RERUN_AUTHOR is unset — the recorded operator authorisation."
    _log "re-run: ${RERUN} (scope: the v3-interim ER re-run leg)"
    exit 42
  fi
  _log "author: ${SIG_ER_RERUN_AUTHOR} (recorded)"
}

# `assert_deps` — the live: edges (apply only; each missing edge exits 42 —
# queued, not a partial apply).
assert_deps() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local missing=0
  if ! gcloud iam service-accounts describe "$(_sa_email "${SIG_SA_QUALITY_PROBE}")" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "  missing live edge: ${SIG_SA_QUALITY_PROBE} — the exec host's runtime SA (live:P34.42b/43)"
    missing=1
  fi
  if ! gcloud secrets describe "${SIG_SECRET_ER_RERUN_PASSWORD}" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "  missing live edge: secret ${SIG_SECRET_ER_RERUN_PASSWORD} does not exist yet"
    missing=1
  fi
  # The v3-interim API roll (live:P34.46 line of OM-20): the ER run rides the
  # SAME image the serving API carries — a rolled-back or un-rolled API is a
  # missing edge, never "documented".
  if [ -z "${SIG_ER_RERUN_IMAGE:-}" ]; then
    _log "  missing live edge: SIG_ER_RERUN_IMAGE unset — name the rolled v3-interim ${SIG_API_IMAGE}:<tag>"
    missing=1
  else
    local want got
    want="$(pin_image_digest "${SIG_ER_RERUN_IMAGE}")"
    got="$(gcloud run services describe sig-api --region "${SIG_GCP_REGION}" \
      --project "${SIG_GCP_PROJECT}" \
      --format='value(spec.template.spec.containers[0].image)' 2>/dev/null || true)"
    if [ -z "${got}" ]; then
      _log "  missing live edge: sig-api's deployed image unreadable (live:P34.46 roll unverifiable)"
      missing=1
    elif [ "${got}" != "${want}" ]; then
      _log "  missing live edge: sig-api serves ${got}, not the v3-interim ${want} — live:P34.46 has not rolled it"
      missing=1
    fi
  fi
  if [ "${missing}" -gt 0 ]; then
    _log "QUEUED (exit 42): a live edge has not landed — see above."
    _log "re-run: ${RERUN} (scope: the v3-interim ER re-run leg)"
    exit 42
  fi
}

# --- the owner connection (db-logins.sh pattern) ------------------------------
_proxy_pid=""
_proxy_start() {
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "cloud-sql-proxy ${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE} --address 127.0.0.1 --port ${SIG_PROXY_PORT}  (background; stopped on exit)"
    return 0
  fi
  if ! command -v cloud-sql-proxy >/dev/null 2>&1; then
    _log "ERROR: cloud-sql-proxy not on PATH — the leg connects through it (127.0.0.1:${SIG_PROXY_PORT})." >&2
    exit 3
  fi
  cloud-sql-proxy "${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}" \
    --address 127.0.0.1 --port "${SIG_PROXY_PORT}" --quiet &
  _proxy_pid=$!
  local i
  for i in $(seq 1 60); do
    if (exec 3<>"/dev/tcp/127.0.0.1/${SIG_PROXY_PORT}") 2>/dev/null; then
      exec 3>&- 3<&- 2>/dev/null || true
      _log "proxy: ${SIG_SQL_INSTANCE} on 127.0.0.1:${SIG_PROXY_PORT} ready"
      return 0
    fi
    sleep 1
  done
  _log "ERROR: cloud-sql-proxy never came up on :${SIG_PROXY_PORT}" >&2
  return 5
}
_proxy_stop() {
  [ -n "${_proxy_pid}" ] && kill "${_proxy_pid}" 2>/dev/null || true
}
trap _proxy_stop EXIT

_load_owner_dsn() {
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "SIG_PG_PASSWORD=\$(gcloud secrets versions access latest --secret=${SIG_SECRET_PG_PASSWORD})  # env only"
    _plan "SIG_DB_LOGIN_DSN=postgresql://sig:<env>@127.0.0.1:${SIG_PROXY_PORT}/${SIG_PG_DB_NAME:-sig}    # env only, never argv"
    return 0
  fi
  SIG_PG_PASSWORD=$(gcloud secrets versions access latest \
    --secret="${SIG_SECRET_PG_PASSWORD}" --project "${SIG_GCP_PROJECT}")
  export SIG_PG_PASSWORD
  export SIG_DB_LOGIN_DSN="postgresql://sig:${SIG_PG_PASSWORD}@127.0.0.1:${SIG_PROXY_PORT}/${SIG_PG_DB_NAME:-sig}"
}

# `_capture <dir>` — the leg's prestate/poststate snapshot (read-only):
# pg_roles + the camera-site ER state a diff can judge.
_capture() {
  local dir="$1"
  mkdir -p "${dir}"
  (cd "${_repo}" && uv run --quiet python -) <<'PY' > "${dir}/er-state.json"
import json, os, psycopg
conn = psycopg.connect(os.environ["SIG_DB_LOGIN_DSN"], connect_timeout=10)
roles = conn.execute(
    "SELECT rolname, rolcanlogin, rolconnlimit, rolconfig FROM pg_roles ORDER BY rolname"
).fetchall()
runs = conn.execute(
    "SELECT run_key, ruleset_version, auto_write_tiers, observation_count, cluster_count "
    "FROM camera_site_run ORDER BY run_key DESC LIMIT 5").fetchall()
execs = conn.execute(
    "SELECT execution_id, run_key, input_count FROM camera_site_execution "
    "ORDER BY execution_id DESC LIMIT 5").fetchall()
tiers = conn.execute(
    "SELECT run_key, match_tier, disposition, disposition_reason, count(*) "
    "FROM camera_site_match GROUP BY 1,2,3,4 ORDER BY 1 DESC,2,3").fetchall()
queue = conn.execute(
    "SELECT count(*) FROM review_item WHERE item_kind = 'camera_site_match' "
    "AND resolved_at IS NULL").fetchone()
conn.close()
print(json.dumps({
    "roles": [{"rolname": r[0], "rolcanlogin": r[1], "rolconnlimit": r[2],
               "rolconfig": list(r[3] or [])} for r in roles],
    "latest_runs": [{"run_key": r[0], "ruleset_version": r[1],
                     "auto_write_tiers": list(r[2] or []),
                     "observation_count": r[3], "cluster_count": r[4]} for r in runs],
    "latest_executions": [{"execution_id": e[0], "run_key": e[1],
                           "input_count": e[2]} for e in execs],
    "tier_dispositions": [{"run_key": t[0], "match_tier": t[1],
                           "disposition": t[2], "disposition_reason": t[3],
                           "n": t[4]} for t in tiers],
    "open_camera_review_items": queue[0] if queue else 0,
}, indent=2, sort_keys=True, default=str))
PY
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the leg's restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "cloud-sql-proxy → SELECT pg_roles + camera_site_run/-match/-execution counts > pre/er-state.json"
    _plan "record: does a ruleset_version='3-interim' run_key already exist? (the exactly-once input)"
    return 0
  fi
  _proxy_start
  _load_owner_dsn
  _capture "${STATE_DIR}/pre"
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ))"
}

do_deps() {
  _log "-- deps ($(date -u +%FT%TZ)): the live: edges (exec SA, the secret, the v3-interim API roll) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud iam service-accounts describe $(_sa_email "${SIG_SA_QUALITY_PROBE}")   (live:P34.42b/43)"
    _plan "gcloud secrets describe ${SIG_SECRET_ER_RERUN_PASSWORD}"
    _plan "gcloud run services describe sig-api image == pin_image_digest(SIG_ER_RERUN_IMAGE)   (live:P34.46 roll)"
    _plan "missing edge → exit 42 (queued), never a partial apply"
    return 0
  fi
  assert_deps
  _log "   deps OK — every live edge holds (date -u: $(date -u +%FT%TZ))"
}

do_backup() {
  assert_window
  assert_author
  _log "-- backup ($(date -u +%FT%TZ)): AR-2 — an on-demand Cloud SQL backup of ${SIG_SQL_INSTANCE} before the first mutation --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud sql backups create --instance ${SIG_SQL_INSTANCE}  (blocks to completion) → assert SUCCESSFUL (recorded under ${STATE_DIR}/backup.json)"
    return 0
  fi
  run gcloud sql backups create --instance "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}"
  gcloud sql backups list --instance "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" --limit 1 --format json \
    > "${STATE_DIR}/backup.json"
  local status
  status="$(python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0].get("status","") if rows else "")' "${STATE_DIR}/backup.json" 2>/dev/null || true)"
  if [ "${status}" = "SUCCESSFUL" ]; then
    _log "   backup SUCCESSFUL (recorded at ${STATE_DIR}/backup.json)"
    return 0
  fi
  _log "ERROR: the on-demand backup did not reach SUCCESSFUL (got '${status}') — AR-2 blocks the mutation." >&2
  exit 4
}

do_login() {
  assert_window
  assert_author
  _log "-- login ($(date -u +%FT%TZ)): ${SIG_DB_ROLE_MATERIALIZE_LOGIN} — catalog statements + Secret Manager credential --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _sigops db-login --role "${SIG_DB_ROLE_MATERIALIZE_LOGIN}" plan
    _plan "sig-ops db-login --role ${SIG_DB_ROLE_MATERIALIZE_LOGIN} apply  (exit 42 while sig_materialize is absent)"
    _plan "openssl rand -hex 32 → env → gcloud secrets versions add ${SIG_SECRET_ER_RERUN_PASSWORD} --data-file=- → ALTER ROLE (env-only, HG-09)"
    return 0
  fi
  assert_deps
  _proxy_start
  _load_owner_dsn
  local rc=0
  _sigops db-login --role "${SIG_DB_ROLE_MATERIALIZE_LOGIN}" apply || rc=$?
  if [ "${rc}" -eq 42 ]; then
    _log "QUEUED (exit 42): the sig_materialize group role is absent on this spine."
    _log "re-run: ${RERUN} (scope: the ${SIG_DB_ROLE_MATERIALIZE_LOGIN} credential leg)"
    exit 42
  fi
  [ "${rc}" -eq 0 ] || { _log "ERROR: db-login apply failed (rc=${rc})" >&2; exit "${rc}"; }
  local pw
  pw="$(openssl rand -hex 32)"
  printf '%s' "${pw}" | gcloud secrets versions add "${SIG_SECRET_ER_RERUN_PASSWORD}" \
    --data-file=- --project "${SIG_GCP_PROJECT}"
  export SIG_ER_RERUN_PASSWORD="${pw}"
  unset pw
  _sigops db-login --role "${SIG_DB_ROLE_MATERIALIZE_LOGIN}" apply
  unset SIG_ER_RERUN_PASSWORD
  _log "   credential set — ${SIG_SECRET_ER_RERUN_PASSWORD}'s only accessor is ${SIG_EXEC_SA}"
}

do_run() {
  assert_window
  assert_author
  _log "-- run ($(date -u +%FT%TZ)): the ONE v3-interim camera-site ER re-run as ${SIG_DB_ROLE_MATERIALIZE_LOGIN} --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "assert no camera_site_run row with ruleset_version='3-interim' yet (exactly once — else exit 42)"
    _plan "sig-ops exec-host run --purpose er-rerun --secret-env SIG_ER_RERUN_PASSWORD \\"
    _plan "  --env SIG_PG_USER=${SIG_DB_ROLE_MATERIALIZE_LOGIN} --env SIG_PG_DB=... --env SIG_CLOUDSQL_CONNECTION=... \\"
    _plan "  --arg=-c --arg 'export SIG_PG_PASSWORD=\"\$SIG_ER_RERUN_PASSWORD\"; exec python -m resolution camera-sites --dsn \"postgresql://\${SIG_PG_USER}:\${SIG_PG_PASSWORD}@/\${SIG_PG_DB}?host=/cloudsql/\${SIG_CLOUDSQL_CONNECTION}\" --role ${SIG_DB_ROLE_MATERIALIZE_LOGIN}'"
    return 0
  fi
  assert_deps
  # Exactly once: a 3-interim run_key already on the spine means the one
  # pre-authorised re-run already happened — a second needs a new operator
  # decision, not a flag. +0 rows is safe, but the leg still stops.
  _proxy_start
  _load_owner_dsn
  local already
  already="$(cd "${_repo}" && uv run --quiet python - <<'PY'
import os, psycopg
conn = psycopg.connect(os.environ["SIG_DB_LOGIN_DSN"], connect_timeout=10)
n = conn.execute("SELECT count(*) FROM camera_site_run WHERE ruleset_version = '3-interim'").fetchone()[0]
conn.close()
print(n)
PY
)"
  if [ "${already}" != "0" ]; then
    _log "QUEUED (exit 42): ${already} camera_site_run row(s) already carry ruleset_version='3-interim' — the one OM-20 re-run already executed; a second needs a NEW operator decision."
    _log "re-run: ${RERUN} (scope: the v3-interim ER re-run leg)"
    exit 42
  fi
  local image="${SIG_ER_RERUN_IMAGE:-}"
  if [ -z "${image}" ]; then
    _log "ERROR: SIG_ER_RERUN_IMAGE must name the rolled v3-interim image." >&2
    exit 2
  fi
  image="$(pin_image_digest "${image}")"
  local conn="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
  mkdir -p "${STATE_DIR}"
  local logf="${STATE_DIR}/run-$(date -u +%Y%m%dT%H%M%SZ).log"
  _log "   running sig-exec-er-rerun-<stamp> (log → ${logf})"
  # shellcheck disable=SC2016
  if ! _sigops exec-host run --purpose er-rerun --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_ER_RERUN_PASSWORD \
      --env "SIG_PG_USER=${SIG_DB_ROLE_MATERIALIZE_LOGIN}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --arg=-c --arg 'export SIG_PG_PASSWORD="$SIG_ER_RERUN_PASSWORD"; exec python -m resolution camera-sites --dsn "postgresql://${SIG_PG_USER}:${SIG_PG_PASSWORD}@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}" --role sig_materialize_login' \
      >"${logf}" 2>&1; then
    _log "ERROR: the ER re-run failed — ${logf} has the output; the cleanup still ran (name-checked delete)." >&2
    exit 4
  fi
  _log "   ER re-run OK — the sig.probe-run/1 record landed under ${SIG_EXEC_PROBE_PREFIX}/"
}

do_after() {
  _log "-- after ($(date -u +%FT%TZ)): poststate capture + the before/after diff --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture under ${STATE_DIR}/post (same reads as prestate)"
    _plan "diff pre/er-state.json ↔ post/er-state.json: the new 3-interim run_key, the demoted inferential dispositions, the queued review items"
    return 0
  fi
  _proxy_start
  _load_owner_dsn
  _capture "${STATE_DIR}/post"
  _log "   poststate recorded under ${STATE_DIR}/post — diff pre/er-state.json ↔ post/er-state.json and commit it as evidence"
}

do_verify() {
  _log "-- verify ($(date -u +%FT%TZ)): poststate + the ${SIG_DB_ROLE_MATERIALIZE_LOGIN} catalog/privilege assertions (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture under ${STATE_DIR}/post (same reads as prestate)"
    _plan "sig-ops db-login --role ${SIG_DB_ROLE_MATERIALIZE_LOGIN} verify  (posture, cap, membership, camera-site surface, refused-write probes)"
    _plan "diff pre ↔ post ER state"
    return 0
  fi
  _proxy_start
  _load_owner_dsn
  _capture "${STATE_DIR}/post"
  _sigops db-login --role "${SIG_DB_ROLE_MATERIALIZE_LOGIN}" verify
  _log "   verify OK — commit ${STATE_DIR}/{pre,post}/er-state.json + the diff as the leg's evidence"
}

do_rollback() {
  _log "-- rollback: append-only means FORWARD-only — no delete exists --"
  _log "   Options: (a) re-run under the PRIOR ruleset digest (a new run_key, the"
  _log "   v3-interim decisions stay as history), or (b) PITR to the AR-2 on-demand"
  _log "   backup recorded at ${STATE_DIR}/backup.json. Either is a NEW operator"
  _log "   decision — this leg never deletes rows."
}

case "${ACTION}" in
  prestate) do_prestate ;;
  deps)     do_deps ;;
  backup)   do_backup ;;
  login)    do_login ;;
  run)      do_run ;;
  after)    do_after ;;
  verify)   do_verify ;;
  rollback) do_rollback ;;
  all)
    do_prestate
    do_deps
    do_backup
    do_login
    do_run
    do_after
    do_verify
    ;;
  *) _log "usage: $(basename "$0") [--check|--apply|--verify] [prestate|deps|backup|login|run|after|verify|rollback|all] [state-dir]" >&2; exit 64 ;;
esac
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "er-rerun ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
else
  _log "er-rerun ${ACTION}: done (mode=${SIG_GCP_MODE})"
fi
