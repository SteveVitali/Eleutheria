#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/protect.sh — P34.3 ops data protection: make production hard to lose.
#
# One reversible, pre-authorized production change (contract docs/tickets/
# 204_P34.3__ops-data-protection.md; OM-20 S5-3 "Both + list + P34.45"
# 2026-10-01T04:28:49Z + B-11 autoresize cap 2026-10-01T04:35:53Z, expires GATE-G4):
#
#   1. sig-pg deletion protection + retain-backups-on-delete      (QA-1)
#   2. sig-pg maintenance window Sun 09:00 UTC                    (QA-2 — away
#      from the scheduled 03:00-06:00 UTC batch windows, per G1-14/SIG-OPS-002)
#   3. sig-pg storage autoresize hard cap 40 GB                   (B-11)
#   4. bucket versioning + noncurrent lifecycle:                  (QA-6 / SIG-STORE-048)
#        sig-restricted  noncurrent deleted after 90 days
#        sig-public      noncurrent deleted after 30 days
#        sig-web         noncurrent deleted after 30 days
#   5. allUsers removed from sig-web — the bucket stops being world-readable;
#      the sig-web Cloud Run service + Cloud CDN keep serving     (QA-7)
#
# Stop rules (contract § Production mutations): a non-UPDATE operation, a
# restart, an api /health failure, or a site route failing after QA-7 rolls
# THAT action back automatically (the inverse patch / re-add runs inline,
# reported, then the script exits non-zero — never continues past a red leg).
#
# Usage:
#   ops/gcp/protect.sh [--check|--dry-run] [ACTION]        # plan only (default)
#   ops/gcp/protect.sh [ACTION]                            # same — bare ACTION = plan
#   ops/gcp/protect.sh --verify [--from-state DIR]         # read-only outcome diff
#   ops/gcp/protect.sh --apply [ACTION]                    # run the mutation(s)
#
# ACTION (default `all`):
#   prestate  capture describe/IAM JSON + sha256 for sig-pg and the three buckets
#   backup    AR-2 restore point: on-demand Cloud SQL backup of sig-pg
#   instance  the three sig-pg patches (1)-(3): live-read first, SKIP when
#             already set, patch, poll the op to DONE asserting
#             operationType=UPDATE, then read the api /health endpoint
#   buckets   versioning + noncurrent lifecycle on the three buckets (4)
#   iam       allUsers removal on sig-web (5) + the QA-7 site checks
#   all       prestate -> backup -> instance -> buckets -> iam -> post-state
#             capture -> --verify -> the QA-7 site checks
#
# Modes (same check/apply contract as lib.sh):
#   check    no ADC, no network; prints PLAN lines + `check OK`
#   apply    requires ADC + SIG_GCP_PROJECT (lib.sh gates); enforces the live
#            window — refuses while inside the daily 03:00-10:00Z band; sig-pg
#            legs additionally refuse inside an AR-3 window or while a
#            sig-materialize execution is running (fail-closed when the check
#            cannot prove none is). Bucket legs may run inside AR-3 but never
#            inside the daily band.
#   verify   read-only; diffs live (or --from-state recorded JSON) against the
#            declared post-conditions; prints OK/DRIFT lines and a summary;
#            exit 1 on any drift — the shape P35.3's probe needs as a real eval.
#
# Env:
#   SIG_GCP_PROJECT        required for apply/live-verify (lib.sh require_project)
#   SIG_GCP_REGION         resource region (default us-central1, config.sh)
#   SIG_PROTECT_EVIDENCE_DIR  where captured JSON lands
#                          (default <repo>/docs/build/logs/protect — gitignored)
#   SIG_API_HEALTH_URL     api /health URL; if unset, resolved from the Cloud
#                          Run service $SIG_RUN_SERVICE
#   SIG_PROTECT_TILES_PATH the PMTiles path the QA-7 site check range-GETs
#                          (default /tiles/sig_graph-sites.pmtiles — verified
#                          206 on the canonical origin 2026-10-02)
#   SIG_PROTECT_NOW        ISO-8601 UTC override of `date -u` for the window
#                          guard ONLY (test seam; the guard echoes both clocks)
#
# Every mutation is reversible — the rollback command is printed beside each
# PLAN line and recorded in docs/build/runs/P34.3.md.

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

# ---- args -------------------------------------------------------------------

MODE="check"
ACTION="all"
FROM_STATE=""

case "${1:-}" in
  --apply) MODE="apply"; shift ;;
  --verify) MODE="verify"; shift ;;
  --check|--dry-run) MODE="check"; shift ;;
  -h|--help) _usage 0 ;;
  "") MODE="check" ;;
  # A bare ACTION (no mode flag) is the plan path — the usage line's default.
  prestate|backup|instance|buckets|iam|all) MODE="check" ;;
  *) echo "protect.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --from-state)
      [ $# -ge 2 ] || { echo "protect.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    prestate|backup|instance|buckets|iam|all)
      [ "$ACTION" = "all" ] || { echo "protect.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    *) echo "protect.sh: unknown argument '$1'" >&2; _usage 64 ;;
  esac
done

export SIG_GCP_MODE="$MODE"

# ---- constants --------------------------------------------------------------

# AR-3 windows (NEXT_PHASE_PLAN §8.4 backfill/catch-up table): sig-pg legs never
# run here; bucket metadata legs may.
AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"

# bucket -> noncurrent retention days (SIG-STORE-048: ops/restricted >= 90;
# published + web surfaces 30 — a restore point only needs the last publish
# window).
BUCKET_RETENTION_DAYS="${SIG_BUCKET_RESTRICTED}:90 ${SIG_BUCKET_PUBLIC}:30 ${SIG_BUCKET_WEB}:30"

WEB_TILES_PATH="${SIG_PROTECT_TILES_PATH:-/tiles/sig_graph-sites.pmtiles}"

_derive_names() {
  # config.sh derived the bucket names at source time; in check mode
  # require_project substitutes a placeholder project id AFTER that, so the
  # derived names must be recomputed once the project id is final.
  export SIG_BUCKET_WEB="${SIG_GCP_PROJECT}-sig-web"
  export SIG_BUCKET_PUBLIC="${SIG_GCP_PROJECT}-sig-public"
  export SIG_BUCKET_RESTRICTED="${SIG_GCP_PROJECT}-sig-restricted"
  export SIG_BUCKET_BACKUPS="${SIG_GCP_PROJECT}-sig-backups"
  BUCKET_RETENTION_DAYS="${SIG_BUCKET_RESTRICTED}:90 ${SIG_BUCKET_PUBLIC}:30 ${SIG_BUCKET_WEB}:30"
}

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_iso_now() {
  # Test seam: SIG_PROTECT_NOW pins the guard's clock (ISO-8601 UTC); the real
  # clock is always echoed beside it.
  if [ -n "${SIG_PROTECT_NOW:-}" ]; then printf '%s\n' "$SIG_PROTECT_NOW";
  else date -u +%Y-%m-%dT%H:%M:%SZ; fi
}

_epoch() {
  local ts="$1"
  if date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$ts" +%s >/dev/null 2>&1; then
    date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$ts" +%s            # macOS
  else
    date -u -d "$ts" +%s                                  # GNU
  fi
}

# ---- window guard -----------------------------------------------------------
# The contract's live window: mutations never inside 03:00-10:00Z; sig-pg legs
# additionally never inside an AR-3 window and never while sig-materialize runs.

_in_daily_band() {
  local hh
  hh="$(printf '%s' "$1" | sed 's/.*T//; s/:.*//')"      # HH of an ISO instant
  [ "$hh" -ge 3 ] && [ "$hh" -lt 10 ]
}

_in_ar3() {
  local now_e; now_e="$(_epoch "$1")"
  printf '%s\n' "$AR3_WINDOWS" | while read -r start stop; do
    [ -n "${start:-}" ] || continue
    if [ "$(_epoch "$start")" -le "$now_e" ] && [ "$now_e" -lt "$(_epoch "$stop")" ]; then
      echo "inside $start..$stop"
    fi
  done | grep -q '^inside'
}

assert_window() {
  # $1 = sigpg | bucket
  local leg="$1" now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=$leg"
  if _in_daily_band "$now"; then
    echo "protect.sh: REFUSED — inside the global 03:00-10:00Z batch band ($now)" >&2
    echo "protect.sh: re-run when the window is open: implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true" >&2
    exit 42
  fi
  if [ "$leg" = "sigpg" ]; then
    if _in_ar3 "$now"; then
      echo "protect.sh: REFUSED — sig-pg leg inside an AR-3 window ($now)" >&2
      exit 42
    fi
    _materialize_not_running || {
      echo "protect.sh: REFUSED — a sig-materialize execution is running (or the check could not prove none is)" >&2
      exit 42
    }
  fi
  echo "window-guard: OK"
}

_materialize_not_running() {
  # 0 when no sig-materialize execution is running; 1 when one is — OR when the
  # read itself fails (fail-closed: sig-pg is not patched on an unproven window).
  local json
  json="$(gcloud run jobs executions list \
    --job sig-materialize --region "$SIG_GCP_REGION" --project "$SIG_GCP_PROJECT" \
    --format=json 2>/dev/null)" || return 1
  SIG_MEXEC="$json" python3 - <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_MEXEC"])
except Exception:
    sys.exit(1)
running = any(
    not any(
        c.get("type") == "Completed" and str(c.get("status")) == "True"
        for c in ((e.get("status") or {}).get("conditions")) or [])
    for e in (rows if isinstance(rows, list) else []))
sys.exit(1 if running else 0)
PY
}

# ---- flag availability check (contract: "verify flags at execution") ---------

_assert_sql_flags() {
  local help_text flag
  help_text="$(gcloud sql instances patch --help 2>/dev/null || true)"
  for flag in --deletion-protection --retain-backups-on-delete \
              --maintenance-window-day --maintenance-window-hour \
              --storage-auto-increase-limit; do
    printf '%s' "$help_text" | grep -q -- "$flag" || {
      echo "protect.sh: gcloud does not advertise '$flag' on 'sql instances patch' — check the CLI version before mutating" >&2
      exit 4; }
  done
  echo "flag-check: 'gcloud sql instances patch' supports all five flags"
}

# ---- read helper -------------------------------------------------------------
# The ONLY path verify mode may take to gcloud. Fail-closed verb allowlist:
# describe / get-iam-policy / list — a mutating verb here exits 65.

_read() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      patch|update|create|delete|remove*|add*|set*|rsync|cp|mv|rm|import|export|restore)
        echo "protect.sh: _read refuses mutating verb '$arg'" >&2; exit 65 ;;
    esac
  done
  gcloud "$@"
}

# ---- state capture ------------------------------------------------------------

_evidence_dir() {
  # $1 = phase tag (pre|post|verify)
  printf '%s/%s-%s' \
    "${SIG_PROTECT_EVIDENCE_DIR:-${_here}/../../docs/build/logs/protect}" \
    "$1" "$(date -u +%Y%m%dT%H%M%SZ)"
}

_capture_state() {
  # $1 = phase tag; writes sql.json, describe.<bucket>.json, iam.<bucket>.json
  local dir b f
  dir="$(_evidence_dir "$1")"; mkdir -p "$dir"
  _read sql instances describe "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/sql.json"
  for b in "$SIG_BUCKET_RESTRICTED" "$SIG_BUCKET_PUBLIC" "$SIG_BUCKET_WEB"; do
    _read storage buckets describe "gs://$b" --format=json > "$dir/describe.$b.json"
    _read storage buckets get-iam-policy "gs://$b" --format=json > "$dir/iam.$b.json"
  done
  for f in "$dir"/*.json; do
    echo "STATE $1 $(basename "$f") sha256=$(_sha256 "$f")"
  done
  echo "state-dir: $dir"
}

plan_prestate() {
  cat <<EOF
PLAN: capture pre-state JSON under \$SIG_PROTECT_EVIDENCE_DIR (gitignored):
PLAN:   gcloud sql instances describe $SIG_SQL_INSTANCE --format=json
PLAN:   gcloud storage buckets describe  gs://{$SIG_BUCKET_RESTRICTED,$SIG_BUCKET_PUBLIC,$SIG_BUCKET_WEB} --format=json
PLAN:   gcloud storage buckets get-iam-policy gs://{same three} --format=json
EOF
}

act_prestate() { _capture_state pre; }

# ---- AR-2 restore point -------------------------------------------------------

plan_backup() {
  cat <<EOF
PLAN: AR-2 restore point — on-demand backup of $SIG_SQL_INSTANCE immediately
PLAN: before the first instance patch:
PLAN:   gcloud sql backups create --instance $SIG_SQL_INSTANCE --async
PLAN:   poll 'gcloud sql operations describe <op>' until DONE, then record the
PLAN:   backup id from 'gcloud sql backups list --instance $SIG_SQL_INSTANCE --limit=1'
PLAN: (rollback: none needed — a backup is additive; deleting it is a separate
PLAN:  operator call, never part of this script)
EOF
}

_wait_op() {
  # $1 op name; $2 = expected operationType (ERE). Polls to DONE (<=20 min).
  # Returns 5 on failure so the caller can run the contract's rollback first.
  local name="$1" want="$2" tries=0 body status otype
  while [ $tries -lt 120 ]; do
    body="$(_read sql operations describe "$name" --project "$SIG_GCP_PROJECT" --format=json)" || {
      echo "protect.sh: op $name describe failed" >&2; return 5; }
    status="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
    otype="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("operationType",""))')"
    if [ "$status" = "DONE" ]; then
      printf '%s' "$otype" | grep -Eq "^(${want})$" || {
        echo "protect.sh: op $name finished with unexpected operationType '$otype' (wanted $want)" >&2
        return 5; }
      echo "op $name: DONE ($otype)"
      return 0
    fi
    case "$status" in
      RUNNING|PENDING) sleep 10; tries=$((tries+1)) ;;
      *) echo "protect.sh: op $name unexpected status '$status'" >&2; return 5 ;;
    esac
  done
  echo "protect.sh: op $name did not finish in 20 min" >&2; return 5
}

act_backup() {
  local op opname f
  gcloud sql backups create --help >/dev/null 2>&1 || {
    echo "protect.sh: 'gcloud sql backups create' unavailable" >&2; exit 4; }
  op="$(gcloud sql backups create --instance "$SIG_SQL_INSTANCE" \
        --project "$SIG_GCP_PROJECT" --async --format=json)" || {
    echo "protect.sh: backup create call failed" >&2; exit 5; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  echo "backup: issued op $opname"
  _wait_op "$opname" "CREATE_BACKUP|BACKUP.*" || {
    echo "protect.sh: AR-2 restore point did not verify SUCCESSFUL — no instance patch may run on a failed restore point (OM-20 void); stopped" >&2
    exit 5; }
  f="$(_evidence_dir backup).json"
  mkdir -p "$(dirname "$f")"
  _read sql backups list --instance "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --limit=1 --format=json > "$f"
  echo "backup: newest backup row -> $f"
  cat "$f"
  # The contract requires the restore point verified SUCCESSFUL before any
  # instance patch runs (a failed restore point voids the pre-authorisation).
  printf '%s' "$(cat "$f")" | python3 -c "
import json,sys
rows=json.load(sys.stdin)
newest=rows[0] if rows else {}
ok=newest.get('status')=='SUCCESSFUL' and newest.get('type') in ('ON_DEMAND','AUTOMATED')
print(f\"backup: newest id={newest.get('id')} status={newest.get('status')} type={newest.get('type')}\")
sys.exit(0 if ok else 1)" || {
    echo "protect.sh: newest backup is not SUCCESSFUL — restore point failed; OM-20 voided, stopped" >&2
    exit 5; }
}

# ---- sig-pg instance legs -----------------------------------------------------

plan_instance() {
  cat <<EOF
PLAN: sig-pg patches — each: live-read, SKIP if already set, patch, poll op to
PLAN: DONE asserting operationType=UPDATE, then read the api /health endpoint:
PLAN: (1) gcloud sql instances patch $SIG_SQL_INSTANCE \\
PLAN:       --deletion-protection --retain-backups-on-delete --async
PLAN:     rollback: patch --no-deletion-protection --no-retain-backups-on-delete
PLAN: (2) gcloud sql instances patch $SIG_SQL_INSTANCE \\
PLAN:       --maintenance-window-day=SUN --maintenance-window-hour=9 --async
PLAN:     rollback: patch --maintenance-window-any
PLAN: (3) gcloud sql instances patch $SIG_SQL_INSTANCE \\
PLAN:       --storage-auto-increase-limit=40 --async
PLAN:     rollback: patch --storage-auto-increase-limit=0
EOF
}

_sql_settings_summary() {
  _read sql instances describe "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --format=json | python3 -c "
import json,sys
s=json.load(sys.stdin).get('settings',{})
for k in ('deletionProtectionEnabled','retainBackupsOnDelete',
          'storageAutoResize','storageAutoResizeLimit'):
    print(f'{k}={s.get(k)}')
mw=s.get('maintenanceWindow') or {}
print(f\"maintenanceWindow.day={mw.get('day')} hour={mw.get('hour')}\")
print(f\"finalBackup={(s.get('finalBackupConfig') or {}).get('enabled')}\")"
}

_api_health() {
  local url="${SIG_API_HEALTH_URL:-}" code
  if [ -z "$url" ]; then
    url="$(_read run services describe "$SIG_RUN_SERVICE" --region "$SIG_GCP_REGION" \
      --project "$SIG_GCP_PROJECT" --format='value(status.url)' 2>/dev/null || true)"
    [ -n "$url" ] && url="${url}/health"
  fi
  if [ -z "$url" ]; then
    echo "health: no api url resolvable (set SIG_API_HEALTH_URL) — skipping" >&2
    return 0
  fi
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$url" || true)"
  echo "health: GET $url -> $code"
  [ "$code" = "200" ]
}

_rollback_sql() {
  # $1 = label; rest = the inverse patch flags. Best-effort rollback per the
  # contract's stop rules; never masks the original failure.
  local label="$1"; shift
  echo "protect.sh: rolling back '$label': gcloud sql instances patch $SIG_SQL_INSTANCE $*" >&2
  local op opname
  if ! op="$(gcloud sql instances patch "$SIG_SQL_INSTANCE" "$@" --async \
            --project "$SIG_GCP_PROJECT" --format=json 2>/dev/null)"; then
    echo "protect.sh: ROLLBACK submit failed — run manually: gcloud sql instances patch $SIG_SQL_INSTANCE $*" >&2
    return 1
  fi
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("name","?"))')"
  if _wait_op "$opname" ".*"; then
    echo "rollback($label): op $opname DONE"
  else
    echo "protect.sh: ROLLBACK of '$label' did not finish cleanly — run manually: gcloud sql instances patch $SIG_SQL_INSTANCE $*" >&2
    return 1
  fi
}

_sql_patch() {
  # $1 = label; $2 = rollback flag string (the recorded prior value); rest =
  # patch flags. Runs the patch, waits, asserts op type, reads api /health.
  # Stop rule: non-UPDATE op, a restart, or a /health failure rolls the action
  # back before exiting (contract § Production mutations).
  local label="$1" rollback="$2"; shift 2
  local op opname
  op="$(gcloud sql instances patch "$SIG_SQL_INSTANCE" "$@" --async \
        --project "$SIG_GCP_PROJECT" --format=json)" || {
    echo "protect.sh: patch submit failed for '$label' — nothing applied" >&2
    exit 6; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  echo "patch($label): op $opname"
  if ! _wait_op "$opname" "UPDATE"; then
    # shellcheck disable=SC2086  # rollback flags are a fixed internal list
    _rollback_sql "$label" $rollback
    echo "protect.sh: '$label' stopped on a non-UPDATE/failed operation — rollback attempted above; blockedOn, ask" >&2
    exit 6
  fi
  if ! _api_health; then
    # shellcheck disable=SC2086
    _rollback_sql "$label" $rollback
    echo "protect.sh: api /health not 200 after '$label' — rollback attempted above; blockedOn, ask" >&2
    exit 6
  fi
}

act_instance() {
  _assert_sql_flags
  local cur; cur="$(_sql_settings_summary)"; printf '%s\n' "$cur" | sed 's/^/live: /'

  # (1) QA-1: deletion protection + retain-backups-on-delete
  if printf '%s\n' "$cur" | grep -q 'deletionProtectionEnabled=True' && \
     { printf '%s\n' "$cur" | grep -q 'retainBackupsOnDelete=True' || \
       printf '%s\n' "$cur" | grep -q 'finalBackup=True'; }; then
    echo "SKIP: deletion protection + backup retention already set"
  else
    _sql_patch qa-1 "--no-deletion-protection --no-retain-backups-on-delete" \
      --deletion-protection --retain-backups-on-delete
  fi

  # (2) QA-2: maintenance window SUN 09:00Z (API day 7 == Sunday)
  cur="$(_sql_settings_summary)"
  if printf '%s\n' "$cur" | grep -q 'maintenanceWindow.day=7 hour=9'; then
    echo "SKIP: maintenance window already SUN 09:00Z"
  else
    _sql_patch qa-2 "--maintenance-window-any" \
      --maintenance-window-day=SUN --maintenance-window-hour=9
  fi

  # (3) B-11: autoresize hard cap 40 GB
  cur="$(_sql_settings_summary)"
  if printf '%s\n' "$cur" | grep -q 'storageAutoResizeLimit=40'; then
    echo "SKIP: autoresize cap already 40 GB"
  else
    _sql_patch disk-cap "--storage-auto-increase-limit=0" \
      --storage-auto-increase-limit=40
  fi
}

# ---- bucket legs (QA-6 / SIG-STORE-048) ----------------------------------------

_lifecycle_file() {
  # $1 = days -> lifecycle JSON: delete versions noncurrent >= N days.
  local days="$1" f
  f="$(mktemp -t sig-lifecycle.XXXXXX.json)"
  cat > "$f" <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"daysSinceNoncurrentTime": $days}
      }
    ]
  }
}
EOF
  printf '%s\n' "$f"
}

plan_buckets() {
  local pair b days
  for pair in $BUCKET_RETENTION_DAYS; do
    b="${pair%%:*}"; days="${pair##*:}"
    cat <<EOF
PLAN: gs://$b — versioning + noncurrent lifecycle (${days}d)
PLAN:   gcloud storage buckets update gs://$b --versioning
PLAN:   gcloud storage buckets update gs://$b --lifecycle-file=<Delete when daysSinceNoncurrentTime>=$days>
PLAN:   (--lifecycle-file REPLACES the rule set; the script refuses rather than
PLAN:    overwrite when a foreign rule is present — pre-state shows none)
PLAN:   rollback: gcloud storage buckets update gs://$b --no-versioning
PLAN:             + re-apply the prior lifecycle file (pre-state kept it)
EOF
  done
}

_bucket_versioning_on() {
  _read storage buckets describe "gs://$1" --format=json \
    | python3 -c "
import json,sys
d=json.load(sys.stdin)
v=d.get('versioning') or {}
sys.exit(0 if v.get('enabled') in (True,'true','True') else 1)"
}

_bucket_has_our_rule() {
  # $1 bucket, $2 days — 0 if the lifecycle already deletes noncurrent >= N days.
  _read storage buckets describe "gs://$1" --format=json \
    | SIG_DAYS="$2" python3 -c "
import json,os,re,sys
d=json.load(sys.stdin); want=int(os.environ['SIG_DAYS'])
def norm(o):
    if isinstance(o,dict):
        return {re.sub(r'(?<=[a-z0-9])([A-Z])',r'_\1',k).lower():norm(v)
                for k,v in o.items()}
    if isinstance(o,list): return [norm(v) for v in o]
    return o
d=norm(d)
for r in ((d.get('lifecycle') or {}).get('rule')) or []:
    a,c=r.get('action') or {},r.get('condition') or {}
    if a.get('type')=='Delete' and (c.get('days_since_noncurrent_time',-1)>=want
        or (c.get('is_live') is False and c.get('age',-1)>=want)):
        sys.exit(0)
sys.exit(1)"
}

_bucket_rule_count() {
  # $1 bucket -> number of lifecycle rules currently set (0 when none).
  _read storage buckets describe "gs://$1" --format=json \
    | python3 -c "
import json,re,sys
d=json.load(sys.stdin)
def norm(o):
    if isinstance(o,dict):
        return {re.sub(r'(?<=[a-z0-9])([A-Z])',r'_\1',k).lower():norm(v)
                for k,v in o.items()}
    if isinstance(o,list): return [norm(v) for v in o]
    return o
d=norm(d)
print(len(((d.get('lifecycle') or {}).get('rule')) or []))"
}

act_buckets() {
  local pair b days f
  for pair in $BUCKET_RETENTION_DAYS; do
    b="${pair%%:*}"; days="${pair##*:}"
    if _bucket_versioning_on "$b"; then
      echo "SKIP: gs://$b versioning already on"
    else
      run gcloud storage buckets update "gs://$b" --versioning \
          --project "$SIG_GCP_PROJECT"
    fi
    if _bucket_has_our_rule "$b" "$days"; then
      echo "SKIP: gs://$b already deletes noncurrent >= ${days}d"
    else
      # --lifecycle-file REPLACES the whole rule set — never silently overwrite
      # a foreign rule (defining standard: no silent overwrites). Pre-state
      # (2026-10-02T04:10Z) shows zero rules on all three buckets.
      if [ "$(_bucket_rule_count "$b")" != "0" ]; then
        echo "protect.sh: gs://$b has lifecycle rules that are not this script's —" >&2
        echo "  refusing to replace them silently; inspect and re-apply the prior file to roll back" >&2
        exit 7
      fi
      f="$(_lifecycle_file "$days")"
      echo "lifecycle file for gs://$b:"; cat "$f"
      run gcloud storage buckets update "gs://$b" --lifecycle-file="$f" \
          --project "$SIG_GCP_PROJECT"
      rm -f "$f"
    fi
  done
}

# ---- sig-web IAM leg (QA-7) ----------------------------------------------------

plan_iam() {
  cat <<EOF
PLAN: gs://$SIG_BUCKET_WEB — drop public read (CDN + sig-web service keep serving)
PLAN:   gcloud storage buckets remove-iam-policy-binding gs://$SIG_BUCKET_WEB \\
PLAN:       --member=allUsers --role=roles/storage.objectViewer
PLAN:   then site checks: GET $SIG_WEB_CANONICAL_URL/ == 200,
PLAN:   $SIG_WEB_CANONICAL_URL/map/ == 200,
PLAN:   $SIG_WEB_CANONICAL_URL$WEB_TILES_PATH with a Range header == 206,
PLAN:   the same three against the sig-web run.app URL, and the direct bucket
PLAN:   URL https://storage.googleapis.com/$SIG_BUCKET_WEB/index.html == !200.
PLAN:   rollback: gcloud storage buckets add-iam-policy-binding gs://$SIG_BUCKET_WEB \\
PLAN:       --member=allUsers --role=roles/storage.objectViewer
EOF
}

_web_allusers_present() {
  _read storage buckets get-iam-policy "gs://$SIG_BUCKET_WEB" --format=json \
    | python3 -c "
import json,sys
p=json.load(sys.stdin)
public=any(b.get('role')=='roles/storage.objectViewer'
           and 'allUsers' in (b.get('members') or [])
           for b in p.get('bindings',[]))
sys.exit(0 if public else 1)"
}

_site_check() {
  # $1 origin. / == 200, /map/ == 200, PMTiles range == 206.
  local origin="$1" code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$origin/" || true)"
  echo "site-check: GET $origin/ -> $code"; [ "$code" = "200" ] || return 1
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$origin/map/" || true)"
  echo "site-check: GET $origin/map/ -> $code"; [ "$code" = "200" ] || return 1
  code="$(curl -sS -o /dev/null -w '%{http_code}' -H 'Range: bytes=0-99' \
            "$origin$WEB_TILES_PATH" || true)"
  echo "site-check: GET $origin$WEB_TILES_PATH (range) -> $code"; [ "$code" = "206" ] || return 1
}

_web_runapp_url() {
  _read run services describe "$SIG_WEB_SERVICE" --region "$SIG_GCP_REGION" \
    --project "$SIG_GCP_PROJECT" --format='value(status.url)' 2>/dev/null || true
}

_rollback_web_iam() {
  # QA-7 stop rule: a site route failing after the removal rolls the action
  # back — re-add the binding, then report.
  echo "protect.sh: rolling back QA-7 — re-adding allUsers:objectViewer on gs://$SIG_BUCKET_WEB" >&2
  if gcloud storage buckets add-iam-policy-binding "gs://$SIG_BUCKET_WEB" \
      --member=allUsers --role=roles/storage.objectViewer \
      --project "$SIG_GCP_PROJECT" >/dev/null; then
    echo "rollback: allUsers:objectViewer restored on gs://$SIG_BUCKET_WEB"
  else
    echo "protect.sh: ROLLBACK FAILED — run manually: gcloud storage buckets add-iam-policy-binding gs://$SIG_BUCKET_WEB --member=allUsers --role=roles/storage.objectViewer" >&2
  fi
}

act_iam() {
  # Baseline first: "serving unchanged afterwards" is only provable from a
  # green start — refuse to mutate on a red baseline.
  local runapp
  runapp="$(_web_runapp_url)"
  if ! _site_check "$SIG_WEB_CANONICAL_URL"; then
    echo "protect.sh: canonical origin already fails the site check BEFORE the IAM change — refusing on a red baseline" >&2
    exit 7
  fi
  if [ -n "$runapp" ]; then
    if ! _site_check "$runapp"; then
      echo "protect.sh: $SIG_WEB_SERVICE run.app URL already fails the site check BEFORE the IAM change — refusing on a red baseline" >&2
      exit 7
    fi
  else
    echo "site-check: $SIG_WEB_SERVICE URL not resolvable — canonical baseline only" >&2
  fi

  local removed=0
  if _web_allusers_present; then
    run gcloud storage buckets remove-iam-policy-binding "gs://$SIG_BUCKET_WEB" \
        --member=allUsers --role=roles/storage.objectViewer \
        --project "$SIG_GCP_PROJECT"
    removed=1
  else
    echo "SKIP: gs://$SIG_BUCKET_WEB has no allUsers:objectViewer binding"
  fi

  # Roll back ONLY when this leg actually removed the binding — on a SKIP a
  # failed site check is an unrelated outage and re-adding allUsers would
  # grant public read the pre-state never had (a mutation outside the list).
  if ! _site_check "$SIG_WEB_CANONICAL_URL"; then
    echo "protect.sh: canonical site check FAILED after QA-7" >&2
    [ "$removed" = "1" ] && _rollback_web_iam
    exit 7
  fi
  if [ -n "$runapp" ] && ! _site_check "$runapp"; then
    echo "protect.sh: sig-web run.app check FAILED after QA-7" >&2
    [ "$removed" = "1" ] && _rollback_web_iam
    exit 7
  fi
  local bcode
  bcode="$(curl -s -o /dev/null -w '%{http_code}' \
           "https://storage.googleapis.com/$SIG_BUCKET_WEB/index.html" || true)"
  echo "site-check: direct bucket URL -> $bcode (want 403/404)"
  case "$bcode" in 403|404) : ;;
    *) echo "protect.sh: bucket still publicly readable ($bcode) — IAM removal did not take" >&2
       [ "$removed" = "1" ] && _rollback_web_iam; exit 7 ;;
  esac
}

# ---- verify (read-only outcome diff; live or recorded JSON) --------------------

_verify_python() {
  # $1 = state dir. Files: sql.json | sql-*.json, describe.*<bucket>*.json,
  # iam.*<bucket>*.json. Same evaluator for live and recorded state.
  SIG_STATE_DIR="$1" python3 - <<'PY'
import glob, json, os, re, sys

state = os.environ["SIG_STATE_DIR"]
ok = drift = 0

def load(*patterns):
    # Accepts the script's own capture names (sql.json, describe.<bucket>.json,
    # iam.<bucket>.json) and the hand-captured pre-state names
    # (sql-<ts>.json, bucket-<suffix>-<ts>.json, iam-<suffix>-<ts>.json).
    paths = []
    for pattern in patterns:
        paths.extend(glob.glob(os.path.join(state, pattern)))
    paths = sorted(set(paths))
    if not paths:
        return None
    with open(paths[-1], "rb") as fh:
        return json.load(fh)

def report(good, check, detail=""):
    global ok, drift
    if good:
        ok += 1
        print(f"OK {check}" + (f" — {detail}" if detail else ""))
    else:
        drift += 1
        print(f"DRIFT {check}: {detail}")

sql = load("sql.json", "sql-*.json")
if sql is None:
    report(False, "sig-pg:state", "no sql*.json in state dir")
else:
    s = sql.get("settings") or {}
    report(s.get("deletionProtectionEnabled") is True, "qa-1:deletion-protection",
           f"live {s.get('deletionProtectionEnabled')!r}")
    retain = s.get("retainBackupsOnDelete") is True or \
             (s.get("finalBackupConfig") or {}).get("enabled") is True
    report(retain, "qa-1:retain-backups-on-delete",
           f"live retainBackupsOnDelete={s.get('retainBackupsOnDelete')!r} "
           f"finalBackup={(s.get('finalBackupConfig') or {}).get('enabled')!r}")
    mw = s.get("maintenanceWindow") or {}
    report(mw.get("day") == 7 and mw.get("hour") == 9, "qa-2:maintenance-window",
           f"live day={mw.get('day')!r} hour={mw.get('hour')!r} (want SUN=7, hour 9)")
    try:
        cap = int(s.get("storageAutoResizeLimit") or 0)
    except (TypeError, ValueError):
        cap = -1
    report(cap == 40, "disk-cap:autoresize-limit",
           f"live {s.get('storageAutoResizeLimit')!r} (want 40)")

def norm(o):
    # gcloud storage describe prints either JSON-API camelCase or snake_case.
    if isinstance(o, dict):
        return {re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", k).lower(): norm(v)
                for k, v in o.items()}
    if isinstance(o, list):
        return [norm(v) for v in o]
    return o

for suffix, days in (("sig-restricted", 90), ("sig-public", 30), ("sig-web", 30)):
    d = load(f"describe.*{suffix}*.json", f"bucket-*{suffix}*.json",
             f"describe-*{suffix}*.json")
    if d is None:
        report(False, f"qa-6:{suffix}", "no describe json in state dir")
        continue
    d = norm(d)
    v = d.get("versioning") or {}
    report(v.get("enabled") is True, f"qa-6:{suffix}:versioning",
           f"live {v.get('enabled')!r}")
    has_rule = any(
        (r.get("action") or {}).get("type") == "Delete" and (
            (r.get("condition") or {}).get("days_since_noncurrent_time", -1) >= days
            or ((r.get("condition") or {}).get("is_live") is False
                and (r.get("condition") or {}).get("age", -1) >= days))
        for r in ((d.get("lifecycle") or {}).get("rule")) or [])
    report(has_rule, f"qa-6:{suffix}:lifecycle",
           f"want a Delete rule on noncurrent versions >= {days}d")

iam = load("iam.*sig-web*.json", "iam-*sig-web*.json")
if iam is None:
    report(False, "qa-7:sig-web-iam", "no iam sig-web json in state dir")
else:
    public = any(b.get("role") == "roles/storage.objectViewer"
                 and "allUsers" in (b.get("members") or [])
                 for b in iam.get("bindings", []))
    report(not public, "qa-7:sig-web-no-allusers",
           f"live allUsers:objectViewer {'present' if public else 'absent'}")

print(f"verify: {ok} OK, {drift} DRIFT")
print("probe: protect-verify result=" + ("ok" if drift == 0 else "drift"))
sys.exit(1 if drift else 0)
PY
}

act_verify() {
  if [ -n "$FROM_STATE" ]; then
    [ -d "$FROM_STATE" ] || {
      echo "protect.sh: --from-state '$FROM_STATE' is not a directory" >&2; exit 66; }
    echo "verify: from-state $FROM_STATE"
    _verify_python "$FROM_STATE"
    return $?
  fi
  local dir b
  dir="$(_evidence_dir verify)"; mkdir -p "$dir"
  echo "verify: live reads -> $dir"
  _read sql instances describe "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/sql.json"
  for b in "$SIG_BUCKET_RESTRICTED" "$SIG_BUCKET_PUBLIC" "$SIG_BUCKET_WEB"; do
    _read storage buckets describe "gs://$b" --format=json > "$dir/describe.$b.json"
    _read storage buckets get-iam-policy "gs://$b" --format=json > "$dir/iam.$b.json"
  done
  _verify_python "$dir"
}

# ---- dispatch ------------------------------------------------------------------

case "$MODE" in
  check)
    echo "protect.sh --check (action=$ACTION): plan only — no ADC, no network."
    require_project   # substitutes a placeholder id so plan lines stay readable
    _derive_names     # re-derive bucket names under the (possibly placeholder) id
    case "$ACTION" in
      prestate) plan_prestate ;;
      backup)   plan_backup ;;
      instance) plan_instance ;;
      buckets)  plan_buckets ;;
      iam)      plan_iam ;;
      all)
        plan_prestate; plan_backup; plan_instance; plan_buckets; plan_iam
        echo "PLAN: then post-state describe captures + '--verify' diff + QA-7 site checks"
        ;;
    esac
    echo "check OK"
    ;;
  verify)
    if [ -z "$FROM_STATE" ]; then
      require_project
      require_adc
      _derive_names
    fi
    act_verify
    ;;
  apply)
    require_project
    require_adc
    _derive_names
    case "$ACTION" in
      prestate) act_prestate ;;   # read-only capture — allowed any time
      backup)   assert_window sigpg;  act_backup ;;
      instance) assert_window sigpg;  act_instance ;;
      buckets)  assert_window bucket; act_buckets ;;
      iam)      assert_window bucket; act_iam ;;
      all)
        assert_window sigpg       # strictest leg gates the sequence start
        act_prestate
        act_backup
        act_instance
        act_buckets
        act_iam
        _capture_state post
        act_verify || { echo "protect.sh: post-verify reported drift — see DRIFT lines" >&2; exit 8; }
        ;;
    esac
    ;;
esac
