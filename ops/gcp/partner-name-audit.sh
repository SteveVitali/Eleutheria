#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/partner-name-audit.sh — P35.21: the hosted READ-ONLY
# `partner-name-audit` run that sizes the legacy `sig.org.name` key set for the
# operator's OP-15 dispositions (D-P32.3-1 — sized, never decided here).
#
# The leg:
#   1. cloud-sql-proxy → sig-pg (127.0.0.1:${SIG_PROXY_PORT}).
#   2. `sig-resolution partner-name-audit --dsn-env SIG_PARTNER_AUDIT_DSN
#      --role sig_read_public` — one read-only transaction
#      (`SET TRANSACTION READ ONLY`; SET ROLE to the least-privilege reader).
#      The report JSON names legacy keys, so it lands under the gitignored
#      docs/build/logs/ tree, never the committed reports tree (Part VIII).
#   3. `sig-resolution partner-name-packet --report <report> --spine "sig-pg
#      (read-only sig_read_public)" --started-at <T0> --finished-at <T1>`
#      emits the committed disposition packet
#      (`sig.partner-name-disposition-packet/1` — N, the OP-15 option blast
#      radii, the verbatim query + its sha256, the report sha256 and the
#      `date -u` bounds; per-key rows are entity_id + name_key_sha256 +
#      counts only). An empty result REFUSES (SIG-ENG-042 — no vacuous N).
#   4. The run ledger records the command, the `date -u` bounds and the
#      packet digest.
#
# Nothing here writes to production: the audit is read-only by construction
# and the packet writes only committed-report bytes. No AR-3 window guard —
# a read binds no mutation window (the contract's live window is none).
#
# Usage:
#   ops/gcp/partner-name-audit.sh [--check|--dry-run]   # plan only (default)
#   ops/gcp/partner-name-audit.sh --apply               # the read-only run
#
# Environment (apply):
#   SIG_GCP_PROJECT        the GCP project (GL-GATE-04)
#   ADC                    `gcloud auth application-default login`
#   SIG_PARTNER_AUDIT_DSN  the read path's DSN (env only — a DSN on argv or
#                          in a file leaks; e.g. postgresql://sig@127.0.0.1:
#                          <port>/sig over the proxy)
#   SIG_PROXY_PORT         proxy port (default 5433)
#   cloud-sql-proxy        on PATH (the leg connects through it)
#
# Exit codes: 0 ok · 2 usage/gate input absent · 3 unarmed (no ADC/tooling).

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

_usage() {
  sed -n '/^# Usage:/,/^set -euo pipefail/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'
  exit "${1:-64}"
}

MODE="check"
case "${1:-}" in
  --apply) MODE="apply" ;;
  --check|--dry-run|"") MODE="check" ;;
  -h|--help) _usage 0 ;;
  *) echo "partner-name-audit.sh: unknown mode '${1:-}'" >&2; _usage 64 ;;
esac

export SIG_GCP_MODE="$MODE"
require_project

: "${SIG_PROXY_PORT:=5433}"
AUDIT_DSN_ENV="SIG_PARTNER_AUDIT_DSN"
AUDIT_ROLE="sig_read_public"
SPINE_LABEL="sig-pg (read-only ${AUDIT_ROLE})"
REPORT_DIR="${SIG_PARTNER_AUDIT_LOG_DIR:-${_here}/../../docs/build/logs/partner-name-audit}"
PACKET_DIR="${SIG_PARTNER_AUDIT_PACKET_DIR:-${_here}/../../docs/build/reports/p35.21-partner-name-audit}"
RERUN="implement-spec spec=docs/tickets/347_P35.21__partner-name-audit-run.md live_verification=true"

_proxy_pid=""
_proxy_stop() {
  if [ -n "${_proxy_pid}" ]; then
    kill "${_proxy_pid}" 2>/dev/null || true
    wait "${_proxy_pid}" 2>/dev/null || true
    _proxy_pid=""
  fi
}
trap _proxy_stop EXIT

_proxy_start() {
  if [ "${MODE}" = "check" ]; then
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
  local tries=0
  while [ "${tries}" -lt 40 ]; do
    if (exec 3<>"/dev/tcp/127.0.0.1/${SIG_PROXY_PORT}") 2>/dev/null; then
      exec 3>&- 3<&-
      _log "proxy: ${SIG_SQL_INSTANCE} on 127.0.0.1:${SIG_PROXY_PORT} ready"
      return 0
    fi
    tries=$((tries + 1))
    sleep 0.5
  done
  _log "ERROR: cloud-sql-proxy never came up on :${SIG_PROXY_PORT}" >&2
  exit 3
}

_run() {
  if [ "${MODE}" = "check" ]; then
    _plan "$*"
  else
    _log "-- $*"
    "$@"
  fi
}

banner "partner-name audit — P35.21 (read-only; sizes D-P32.3-1)"

if [ "${MODE}" = "check" ]; then
  _plan "env required at --apply: ${AUDIT_DSN_ENV} (env only — never argv/file), ADC, cloud-sql-proxy on PATH"
  _proxy_start
  _plan "T0=\$(date -u +%FT%TZ)"
  _plan "uv run python -m resolution partner-name-audit --dsn-env ${AUDIT_DSN_ENV} --role ${AUDIT_ROLE} --out ${REPORT_DIR}/partner-name-audit-report-<ts>.json   (report names keys → gitignored logs tree only, Part VIII)"
  _plan "T1=\$(date -u +%FT%TZ)"
  _plan "uv run python -m resolution partner-name-packet --report <report>.json --spine \"${SPINE_LABEL}\" --started-at \${T0} --finished-at \${T1} --out-dir ${PACKET_DIR}   (REFUSES a 0-key report — SIG-ENG-042)"
  _plan "packet artifacts: ${PACKET_DIR}/{packet.json,packet.sha256,PACKET.md,keys.csv} — key ids + digests + counts only"
  _plan "record: the run ledger's command + date -u bounds + packet sha256"
  _plan "re-run (verbatim): ${RERUN}"
  _log "check OK"
  exit 0
fi

# --apply: the read-only hosted run.
require_adc

if [ -z "${!AUDIT_DSN_ENV:-}" ]; then
  _log "ERROR: ${AUDIT_DSN_ENV} is unset — the DSN rides env only (a literal on argv or in a file leaks into the process list / history)." >&2
  exit 3
fi

mkdir -p "${REPORT_DIR}" "${PACKET_DIR}"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
report_path="${REPORT_DIR}/partner-name-audit-report-${ts}.json"

_proxy_start
T0="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
_log "T0 (date -u): ${T0}"
_run uv run python -m resolution partner-name-audit \
  --dsn-env "${AUDIT_DSN_ENV}" \
  --role "${AUDIT_ROLE}" \
  --out "${report_path}"
T1="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
_log "T1 (date -u): ${T1}"

_run uv run python -m resolution partner-name-packet \
  --report "${report_path}" \
  --spine "${SPINE_LABEL}" \
  --started-at "${T0}" \
  --finished-at "${T1}" \
  --out-dir "${PACKET_DIR}"

_report_sha="$(shasum -a 256 "${report_path}" | awk '{print $1}')"
_packet_sha="$(shasum -a 256 "${PACKET_DIR}/packet.json" | awk '{print $1}')"
_log "report sha256 (name-bearing, logs tree only): sha256:${_report_sha}"
_log "packet sha256 (committed): sha256:${_packet_sha}"
_log "ledger line: partner-name-audit read-only over ${SPINE_LABEL} — bounds ${T0} → ${T1} (date -u); packet ${PACKET_DIR}/packet.json sha256:${_packet_sha}"
_log "done"
