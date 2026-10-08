#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/db-logins.sh — the database-login leg of P34.43 (SIG-CONF-013, L3
# CP-0; pre-authorised S5-3/OM-20 "Both + list + P34.45"). Two least-privilege
# LOGIN roles, provisioned over a cloud-sql-proxy session as the schema owner:
#
#   L1  sig_audit          — SELECT-only audit/quality login: member of
#                            sig_read_public (the §37 surface; tier-0 RLS
#                            binds), default_transaction_read_only=on,
#                            statement_timeout=60s, CONNECTION LIMIT 4, and —
#                            via the `audit_login` sqitch change (deployed by
#                            P34.46, never by this leg) — SELECT on the NEW-16
#                            ingest_run_capture + entity_identity_key. Its
#                            password is generated → stored in Secret Manager
#                            (sig-audit-password, one accessor: the exec SA)
#                            → set via ALTER ROLE — env-only end to end
#                            (HG-09, ADR-202). Until P34.46 deploys the
#                            change, verify reports the NEW-16 grants
#                            not_evaluable — a pending deploy is a named
#                            state, never a fabricated pass.
#   L2  sig_recovery_login — LOGIN member of the sig_recovery GROUP role L52
#                            (recovery_apply) creates; P34.46 deploys it on
#                            hosted. Until the group exists, `apply` exits 42
#                            — the live:P34.46 dependency is ENFORCED by a
#                            catalog read, not just recorded. For P35.61's
#                            bounded apply; CONNECTION LIMIT 2; same
#                            credential shape (sig-recovery-password).
#
# Every statement is catalog-only (role rows + memberships — never a table
# grant, never a table lock; lock_timeout is set first). The identical
# statements live in db/deploy/audit_login.sql so a hosted spine the leg ran
# early on converges at P34.46's deploy.
#
#   ./db-logins.sh --check [action]            # (default) plan-only: NO ADC,
#                                              # NO network, NO proxy.
#   ./db-logins.sh --apply <action> [--role r] # windowed + operator ADC.
#   ./db-logins.sh --verify --role r           # read-only catalog/privilege
#                                              # assertions over the owner
#                                              # conn (never window-gated)
#
# Actions:
#   prestate   start the proxy + record the catalog state (pg_roles /
#              memberships / rolconfig → ${STATE_DIR}/pre/pg-roles.json).
#              READ-ONLY — any time.
#   backup     AR-2: an on-demand Cloud SQL backup of sig-pg, waited to
#              SUCCESSFUL, BEFORE the first role statement. Windowed.
#   apply      the role's catalog statements (guarded CREATE — idempotent).
#              Exit 42 while a required group role is absent (L2's
#              live:P34.46 gate). Windowed.
#   credential generate the password (openssl, 32B) → `secrets versions add`
#              via stdin → ALTER ROLE PASSWORD via env — the value never
#              touches a file, argv or a log line. Windowed.
#   verify     `db-login verify` — posture flags, connection limit, session
#              defaults, memberships, the read surface, the refused-write
#              probes. READ-ONLY.
#   rollback   drop the login + remove its secret's accessor (never a blind
#              revert — the prestate is the record). NOT window-gated.
#   all        prestate → backup → apply → credential → verify.
#
# Live window (OM-19, AR-3 + AR-2): applies run ≥ ${SIG_DBLOGINS_EARLIEST} and
# never 03:00–06:30Z; earlier → exit 42 (queued — the RETURN PASS re-run
# prompt is printed). SIG_DBLOGINS_NOW overrides the clock for the offline
# guard test only.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

ACTION="all"
ROLE=""
case "${1:-}" in
  --verify)
    # Read-only catalog/privilege assertions (ADC + proxy, never gated).
    SIG_GCP_MODE="verify"
    ACTION="verify"
    shift
    ;;
  *)
    parse_mode "${1:-}"
    shift || true
    ACTION="${1:-all}"
    shift || true
    ;;
esac
# Remaining args: [--role <sig_audit|sig_recovery>] [state-dir]
while [ $# -gt 0 ]; do
  case "$1" in
    --role) ROLE="${2:?--role needs a value}"; shift 2 ;;
    *)      break ;;
  esac
done
STATE_DIR="${1:-${SIG_DBLOGINS_STATE_DIR}}"
export SIG_GCP_MODE
: "${ROLE:=${SIG_DB_ROLE_AUDIT}}"
ROLE="$(printf '%s' "${ROLE}" | tr 'A-Z' 'a-z')"
case "${ROLE}" in
  sig_audit)              ROLE_NAME="${SIG_DB_ROLE_AUDIT}";    SECRET="${SIG_SECRET_AUDIT_PASSWORD}";    PASSWORD_ENV="SIG_AUDIT_PASSWORD" ;;
  sig_recovery|sig_recovery_login)
                          ROLE_NAME="${SIG_DB_ROLE_RECOVERY}"; SECRET="${SIG_SECRET_RECOVERY_PASSWORD}"; PASSWORD_ENV="SIG_RECOVERY_PASSWORD" ;;
  *) _log "usage: --role sig_audit|sig_recovery" >&2; exit 64 ;;
esac

_repo="$(cd "${_here}/../.." && pwd)"
: "${SIG_PROXY_PORT:=5433}"

RERUN='implement-spec spec=docs/tickets/253_P34.43__execution-host-and-least-privilege-db-logins.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `assert_window` — the OM-19/AR-3 clock guard (exit 42 = queued leg).
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dow
  now="${SIG_DBLOGINS_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_DBLOGINS_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_DBLOGINS_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN} (scope: the ${ROLE_NAME} login leg only)"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN} (scope: the ${ROLE_NAME} login leg only)"
    exit 42
  fi
  dow="$(date -u -d "${now}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${now}" +%u 2>/dev/null \
        || echo 7)"
  if [[ "${hhmm}" > "13:59" && "${hhmm}" < "20:00" && "${dow}" -le 5 ]]; then
    _log "window OK: ${now} (the preferred 14:00–20:00Z weekday slot)"
  else
    _log "window OK: ${now} (≥ ${SIG_DBLOGINS_EARLIEST}, outside 03:00–06:30Z — note: outside the preferred 14:00–20:00Z weekday slot)"
  fi
}

# --- the owner connection ----------------------------------------------------
# cloud-sql-proxy on 127.0.0.1:${SIG_PROXY_PORT} (restore-drill.sh pattern);
# the owner password rides env (SIG_PG_PASSWORD), the DSN rides env
# (SIG_DB_LOGIN_DSN) — never argv, never a file.

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
  # The schema-owner password from Secret Manager → env only; the DSN the
  # module reads is SIG_DB_LOGIN_DSN (env), assembled here — never argv.
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "SIG_PG_PASSWORD=\$(gcloud secrets versions access latest --secret=${SIG_SECRET_PG_PASSWORD})  # env only"
    _plan "SIG_DB_LOGIN_DSN=postgresql://sig:<env>@127.0.0.1:${SIG_PROXY_PORT}/${SIG_PG_DB_NAME:-sig}    # env only, never argv"
    return 0
  fi
  # Unquoted command substitution: a scanner-safe assignment of a command's
  # output — the value lands in the environment, never a literal (HG-09;
  # the same shape as restore-drill.sh's _load_password).
  SIG_PG_PASSWORD=$(gcloud secrets versions access latest \
    --secret="${SIG_SECRET_PG_PASSWORD}" --project "${SIG_GCP_PROJECT}")
  export SIG_PG_PASSWORD
  export SIG_DB_LOGIN_DSN="postgresql://sig:${SIG_PG_PASSWORD}@127.0.0.1:${SIG_PROXY_PORT}/${SIG_PG_DB_NAME:-sig}"
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the catalog snapshot under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "cloud-sql-proxy → psql/SELECT pg_roles, pg_auth_members, rolconfig > pre/pg-roles.json"
    _plan "record: does ${ROLE_NAME} exist? does its required group role exist? (the L2 gate's input)"
    return 0
  fi
  _proxy_start
  _load_owner_dsn
  mkdir -p "${STATE_DIR}/pre"
  (cd "${_repo}" && uv run --quiet python -) <<'PY' > "${STATE_DIR}/pre/pg-roles.json"
import json, os, psycopg
conn = psycopg.connect(os.environ["SIG_DB_LOGIN_DSN"], connect_timeout=10)
cur = conn.execute(
    "SELECT rolname, rolcanlogin, rolconnlimit, rolconfig FROM pg_roles ORDER BY rolname")
roles = [
    {"rolname": r[0], "rolcanlogin": r[1], "rolconnlimit": r[2],
     "rolconfig": list(r[3] or [])}
    for r in cur.fetchall()
]
mem = conn.execute(
    "SELECT r.rolname, m.rolname FROM pg_auth_members am "
    "JOIN pg_roles r ON r.oid = am.member JOIN pg_roles m ON m.oid = am.roleid").fetchall()
conn.close()
print(json.dumps({"roles": roles, "memberships": [[a, b] for a, b in mem]},
                 indent=2, sort_keys=True))
PY
  _log "   prestate recorded under ${STATE_DIR}/pre ($(date -u +%FT%TZ))"
}

do_backup() {
  assert_window
  _log "-- backup ($(date -u +%FT%TZ)): AR-2 — an on-demand Cloud SQL backup of ${SIG_SQL_INSTANCE} before the first role statement --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud sql backups create --instance ${SIG_SQL_INSTANCE}  (blocks to completion) → gcloud sql backups list --limit 1 → assert SUCCESSFUL (recorded under ${STATE_DIR}/backup.json)"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  # `backups create` blocks until the operation completes; the read-back
  # asserts the newest row is SUCCESSFUL before any role statement runs.
  run gcloud sql backups create --instance "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}"
  gcloud sql backups list --instance "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" --format json --limit 1 \
    > "${STATE_DIR}/backup.json"
  local status
  status="$(python3 -c 'import json,sys
rows = json.load(open(sys.argv[1]))
print(rows[0].get("status","") if rows else "")' "${STATE_DIR}/backup.json" 2>/dev/null || true)"
  if [ "${status}" = "SUCCESSFUL" ]; then
    _log "   backup SUCCESSFUL (recorded at ${STATE_DIR}/backup.json)"
    return 0
  fi
  _log "ERROR: the on-demand backup did not reach SUCCESSFUL (got '${status}') — AR-2 blocks the role statements." >&2
  exit 5
}

# `_health_probe` — the contract's stop rule: a `/health` failure means stop,
# roll back and ask — never apply a role statement onto an unhealthy spine's
# serving path. Read-only; skips quietly when the API URL cannot be resolved.
_health_probe() {
  [ "${SIG_GCP_MODE}" = "check" ] && return 0
  local url
  url="$(gcloud run services describe sig-api --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format='value(status.url)' 2>/dev/null || true)"
  if [ -z "${url}" ]; then
    _log "   note: sig-api's URL unresolvable — /health probe skipped (recorded)"
    return 0
  fi
  if curl -fsS --max-time 15 "${url}/health" >/dev/null 2>&1; then
    _log "   /health OK (${url})"
  else
    _log "STOP RULE: ${url}/health failed — no role statement under an unhealthy serving path. Roll back + ask." >&2
    exit 4
  fi
}

do_apply() {
  assert_window
  _log "-- apply ($(date -u +%FT%TZ)): the ${ROLE_NAME} catalog statements (idempotent, guarded CREATE) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _sigops db-login --role "${ROLE_NAME}" plan
    _plan "sig-ops db-login --role ${ROLE_NAME} apply  (over SIG_DB_LOGIN_DSN — catalog-only; exit 42 while a required role is absent)"
    return 0
  fi
  _health_probe
  _proxy_start
  _load_owner_dsn
  local rc=0
  _sigops db-login --role "${ROLE_NAME}" apply || rc=$?
  if [ "${rc}" -eq 42 ]; then
    _log "QUEUED (exit 42): ${ROLE_NAME}'s required group role is absent — live:P34.46 has not deployed it yet."
    _log "re-run: ${RERUN} (scope: the ${ROLE_NAME} login leg only)"
    exit 42
  fi
  if [ "${rc}" -ne 0 ]; then
    _log "ERROR: db-login apply failed (rc=${rc})" >&2
    exit "${rc}"
  fi
}

do_credential() {
  assert_window
  _log "-- credential ($(date -u +%FT%TZ)): ${ROLE_NAME}'s password — generated → Secret Manager → ALTER ROLE (env-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "openssl rand -hex 32 → env (never a file, never argv)"
    _plan "gcloud secrets versions add ${SECRET} --data-file=-   (the value on stdin — Secret Manager is the only store, HG-09)"
    _plan "ALTER ROLE ${ROLE_NAME} PASSWORD <env>  (db-login apply with \${${PASSWORD_ENV}} set — never printed, never argv)"
    return 0
  fi
  _health_probe
  _proxy_start
  _load_owner_dsn
  # Apply first — the role must exist (and the L2 dependency must be
  # satisfied) before a credential is minted for it.
  local rc=0
  _sigops db-login --role "${ROLE_NAME}" apply || rc=$?
  if [ "${rc}" -eq 42 ]; then
    _log "QUEUED (exit 42): ${ROLE_NAME}'s required group role is absent — live:P34.46 has not deployed it yet."
    _log "re-run: ${RERUN} (scope: the ${ROLE_NAME} login leg only)"
    exit 42
  fi
  [ "${rc}" -eq 0 ] || { _log "ERROR: db-login apply failed (rc=${rc})" >&2; exit "${rc}"; }
  # The value lives only in the pipeline: generator → secrets stdin → env for
  # the ALTER. No file anywhere, never argv, never a log line.
  local pw
  pw="$(openssl rand -hex 32)"
  printf '%s' "${pw}" | gcloud secrets versions add "${SECRET}" \
    --data-file=- --project "${SIG_GCP_PROJECT}"
  export "${PASSWORD_ENV}=${pw}"
  unset pw
  _sigops db-login --role "${ROLE_NAME}" apply
  unset "${PASSWORD_ENV}"
  _log "   credential set — ${SECRET}'s only accessor is ${SIG_EXEC_SA} (bindings grant it)"
}

do_verify() {
  _log "-- verify ($(date -u +%FT%TZ)): the ${ROLE_NAME} catalog + privilege assertions (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "sig-ops db-login --role ${ROLE_NAME} verify  (over SIG_DB_LOGIN_DSN — posture, limits, memberships, read surface, refused-write probes; NEW-16 grants report not_evaluable until P34.46 deploys)"
    return 0
  fi
  _proxy_start
  _load_owner_dsn
  _sigops db-login --role "${ROLE_NAME}" verify
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): drop ${ROLE_NAME} + strip its secret accessor (recorded prestate is the record) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "DROP ROLE ${ROLE_NAME} (after revoking its memberships) — catalog-only"
    _plan "gcloud secrets remove-iam-policy-binding ${SECRET} --member serviceAccount:${SIG_EXEC_SA}@<project>.iam.gserviceaccount.com --role roles/secretmanager.secretAccessor"
    return 0
  fi
  _proxy_start
  _load_owner_dsn
  (cd "${_repo}" && SIG_ROLE_NAME="${ROLE_NAME}" uv run --quiet python -) <<'PY'
import os, psycopg
from psycopg import sql
conn = psycopg.connect(os.environ["SIG_DB_LOGIN_DSN"], connect_timeout=10, autocommit=True)
role = os.environ["SIG_ROLE_NAME"]
cur = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
if cur.fetchone() is None:
    print(f"role {role} already absent")
else:
    conn.execute("BEGIN")
    conn.execute("SET LOCAL lock_timeout = '5s'")
    conn.execute(
        sql.SQL("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {}")
        .format(sql.Identifier(role)))
    # Its memberships go too — DROP ROLE refuses a role still holding one.
    cur = conn.execute(
        "SELECT r.rolname FROM pg_auth_members am "
        "JOIN pg_roles r ON r.oid = am.roleid "
        "JOIN pg_roles m ON m.oid = am.member WHERE m.rolname = %s",
        (role,))
    for (parent,) in cur.fetchall():
        conn.execute(
            sql.SQL("REVOKE {} FROM {}").format(
                sql.Identifier(parent), sql.Identifier(role)))
    conn.execute("COMMIT")
    conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
    print(f"dropped {role}")
conn.close()
PY
  gcloud secrets remove-iam-policy-binding "${SECRET}" \
    --project "${SIG_GCP_PROJECT}" \
    --member "serviceAccount:${SIG_EXEC_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com" \
    --role roles/secretmanager.secretAccessor || true
  _log "   rollback applied — ${ROLE_NAME} dropped, its secret accessor removed."
}

require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
case "${ACTION}" in
  backup|apply|credential|all) assert_window ;;
esac
require_adc

banner "P34.43 — least-privilege DB logins (${ROLE_NAME}; SIG-CONF-013)"

case "${ACTION}" in
  prestate)   do_prestate ;;
  backup)     do_backup ;;
  apply)      do_apply ;;
  credential) do_credential ;;
  verify)     do_verify ;;
  rollback)   do_rollback ;;
  all)
    do_prestate
    do_backup
    do_apply
    do_credential
    do_verify ;;
  *) _log "usage: $(basename "$0") [--check|--apply|--verify] [--role sig_audit|sig_recovery] [prestate|backup|apply|credential|verify|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "db-logins ${ACTION} (${ROLE_NAME}): check OK (mode=${SIG_GCP_MODE})"
else
  _log "db-logins ${ACTION} (${ROLE_NAME}): done (mode=${SIG_GCP_MODE})"
fi
