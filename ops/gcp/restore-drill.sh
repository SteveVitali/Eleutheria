#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/restore-drill.sh — P34.6 (SIG-OPS-001, ADR-175): prove the production
# spine restorable at scale. A point-in-time Cloud SQL clone of sig-pg into a
# disposable sig-pg-drill-<STAMP> instance; append-only row-count parity at the
# restore point T on both instances through the Cloud SQL Auth Proxy; measured
# RTO and RPO; then a NAME-CHECKED delete that can never name sig-pg.
#
# Pre-authorisation (contract docs/tickets/207_P34.6__restore-drill-and-logical-
# export.md; OM-20 S5-3 "Both + list + P34.45" 2026-10-01T04:28:49Z, expires
# GATE-G4): create + name-checked delete of sig-pg-drill-<stamp> ONLY.
# The full-backup variant (leg 3) and every leg of logical-export.sh need an
# in-ticket go or a GATE listing — fullrestore refuses without --go.
#
# Voided by (contract § Gate status): a red probe, a failed restore point, or a
# production read contradicting a record → the script stops; nothing proceeds
# on silence. The clone leg refuses while inside the daily 03:00-10:00Z band
# or while a sig-materialize execution is running (fail-closed when the check
# cannot prove none is); AR-3 windows do not bind the separate clone instance.
#
# Usage:
#   ops/gcp/restore-drill.sh [--check|--dry-run] [ACTION]   # plan only (default)
#   ops/gcp/restore-drill.sh --verify [--from-state DIR]    # read-only outcome diff
#   ops/gcp/restore-drill.sh --apply ACTION [flags]         # the gated live leg
#
# ACTION (default `all`):
#   prestate      capture instance/backup/operation/probe/materialize JSON +
#                 sha256 (read-only — allowed inside the band)
#   clone         leg 1: window guard -> newest-backup-SUCCESSFUL check -> red-
#                 probe review -> `sql instances clone sig-pg
#                 sig-pg-drill-<STAMP> --point-in-time <T=now-10min>` -> poll op
#                 DONE (CLONE) -> poll RUNNABLE; writes meta.env + clone.json
#   counts        parity: cloud-sql-proxy to both instances, then
#                 `uv run python -m ops cloudsql-drill` — per-table counts at T,
#                 spine_watermark row set, sqitch.changes tip, PostGIS, RTO/RPO
#                 -> record.json. SIG_PG_PASSWORD comes from env or Secret
#                 Manager by name (never argv, never a file).
#   smoke         local `sig-api serve --dsn <clone>` over the proxy:
#                 /health 200 + one /v1/coverage/<scope> call; merged into
#                 record.json
#   deleteclone NAME   the name-checked delete — refuses sig-pg outright and
#                 any name not matching sig-pg-drill(-b)?-<YYYYmmddtHHMMz>
#   fullrestore   leg 3 (queued): create an empty sig-pg-drill-b-<STAMP> and
#                 `gcloud sql backups restore` the newest AUTOMATED backup into
#                 it. Requires --go "<verbatim in-ticket go or GATE listing>".
#   all           prestate -> clone -> counts -> smoke -> deleteclone ->
#                 post-state -> --verify
#
# Env:
#   SIG_GCP_PROJECT        required for apply/live-verify (lib.sh require_project)
#   SIG_GCP_REGION         resource region (default us-central1, config.sh)
#   SIG_DRILL_EVIDENCE_DIR where captured JSON + the drill record land
#                          (default <repo>/docs/build/logs/restore-drill — gitignored)
#   SIG_DRILL_NOW          ISO-8601 UTC override of `date -u` for the window
#                          guard ONLY (test seam; the guard echoes both clocks)
#   SIG_DRILL_PROXY_PORT   base port for the two proxies (default 5441, clone 5442)
#   SIG_DRILL_API_PORT     port for the smoke-test api serve (default 8477)
#   SIG_PG_USER            PG login for the parity reads (default sig)
#   SIG_PG_DB_NAME         database name (default sig)
#   SIG_PG_PASSWORD        the PG password; when unset the script reads Secret
#                          Manager secret $SIG_SECRET_PG_PASSWORD into memory
#   --probe-note "<text>"  required on `clone` when the latest sig-probe sweep
#                          is red — the recorded judgment that it is the known
#                          class (the note lands in the evidence dir)
#   --go "<verbatim go>"   required on `fullrestore` (leg 3 is not on the S5-3
#                          list) and refused without it
#   --clone-name NAME      continue an existing drill instance (counts/smoke/
#                          deleteclone)
#   --at T                 override the restore point (ISO-8601; counts)
#
# Cleanup/rollback: the drill instance is always disposable — `deleteclone`
# is the rollback for clone/fullrestore, and it is name-checked.

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${_here}/../.." && pwd)"
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
GO=""
PROBE_NOTE=""
CLONE_NAME=""
AT=""

case "${1:-}" in
  --apply) MODE="apply"; shift ;;
  --verify) MODE="verify"; shift ;;
  --check|--dry-run) MODE="check"; shift ;;
  -h|--help) _usage 0 ;;
  "") MODE="check" ;;
  prestate|clone|counts|smoke|deleteclone|fullrestore|all) MODE="check" ;;
  *) echo "restore-drill.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --from-state)
      [ $# -ge 2 ] || { echo "restore-drill.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    --go)
      [ $# -ge 2 ] || { echo "restore-drill.sh: --go needs the verbatim go text" >&2; exit 64; }
      GO="$2"; shift 2 ;;
    --go=*) GO="${1#--go=}"; shift ;;
    --probe-note)
      [ $# -ge 2 ] || { echo "restore-drill.sh: --probe-note needs the recorded judgment" >&2; exit 64; }
      PROBE_NOTE="$2"; shift 2 ;;
    --probe-note=*) PROBE_NOTE="${1#--probe-note=}"; shift ;;
    --clone-name)
      [ $# -ge 2 ] || { echo "restore-drill.sh: --clone-name needs a name" >&2; exit 64; }
      CLONE_NAME="$2"; shift 2 ;;
    --clone-name=*) CLONE_NAME="${1#--clone-name=}"; shift ;;
    --at)
      [ $# -ge 2 ] || { echo "restore-drill.sh: --at needs an ISO-8601 instant" >&2; exit 64; }
      AT="$2"; shift 2 ;;
    --at=*) AT="${1#--at=}"; shift ;;
    prestate|clone|counts|smoke|deleteclone|fullrestore|all)
      [ "$ACTION" = "all" ] || { echo "restore-drill.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    sig-pg*|*)
      # A bare positional after the ACTION is the deleteclone/fullrestore name.
      if [ "$ACTION" = "deleteclone" ] || [ "$ACTION" = "fullrestore" ]; then
        CLONE_NAME="$1"; shift
      else
        echo "restore-drill.sh: unknown argument '$1'" >&2; _usage 64
      fi ;;
  esac
done

export SIG_GCP_MODE="$MODE"

# ---- constants + helpers ------------------------------------------------------

_derive_names() {
  export SIG_BUCKET_BACKUPS="${SIG_GCP_PROJECT}-sig-backups"
  export SIG_BUCKET_RESTRICTED="${SIG_GCP_PROJECT}-sig-restricted"
}

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_iso_now() {
  # Test seam: SIG_DRILL_NOW pins the guard's clock (ISO-8601 UTC); the real
  # clock is always echoed beside it.
  if [ -n "${SIG_DRILL_NOW:-}" ]; then printf '%s\n' "$SIG_DRILL_NOW";
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

_iso_minus_minutes() {
  # $1 = ISO instant, $2 = minutes back -> ISO instant (macOS + GNU date).
  local ts="$1" mins="$2" e
  e="$(_epoch "$ts")"
  e=$((e - mins * 60))
  if date -u -j -f '%s' "$e" +%Y-%m-%dT%H:%M:%SZ >/dev/null 2>&1; then
    date -u -j -f '%s' "$e" +%Y-%m-%dT%H:%M:%SZ
  else
    date -u -d "@$e" +%Y-%m-%dT%H:%M:%SZ
  fi
}

_in_daily_band() {
  local hh
  hh="$(printf '%s' "$1" | sed 's/.*T//; s/:.*//')"      # HH of an ISO instant
  [ "$hh" -ge 3 ] && [ "$hh" -lt 10 ]
}

# ---- window guard -------------------------------------------------------------
# The contract's live window for the drill clone: never 03:00-10:00Z, never
# concurrent with sig-materialize. (The clone is a separate instance, so AR-3
# does not bind it — row 207's window names AR-3 as allowed for the clone.)

assert_window() {
  local now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=drill"
  if _in_daily_band "$now"; then
    echo "restore-drill.sh: REFUSED — inside the global 03:00-10:00Z batch band ($now)" >&2
    echo "restore-drill.sh: re-run when the window is open: implement-spec spec=docs/tickets/207_P34.6__restore-drill-and-logical-export.md live_verification=true" >&2
    exit 42
  fi
  _materialize_not_running || {
    echo "restore-drill.sh: REFUSED — a sig-materialize execution is running (or the check could not prove none is)" >&2
    exit 42
  }
  echo "window-guard: OK"
}

_materialize_not_running() {
  # 0 when no sig-materialize execution is running; 1 when one is — OR when the
  # read itself fails (fail-closed: no clone while the backfill may write).
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
# Terminal = a `Completed` condition in either state (True = succeeded,
# False = failed/cancelled — both terminal) or a recorded completionTime.
# Running = neither marker — still executing (or never scheduled, which the
# fail-closed reading also refuses to clear).
def terminal(e):
    s = e.get("status") or {}
    if s.get("completionTime"):
        return True
    return any(
        c.get("type") == "Completed" for c in s.get("conditions") or [])
running = any(not terminal(e) for e in (rows if isinstance(rows, list) else []))
sys.exit(1 if running else 0)
PY
}

# ---- read-only path -----------------------------------------------------------
# The ONLY path verify/prestate/clone-reads may take to gcloud. Fail-closed verb
# allowlist: describe / get-iam-policy / list / ls(-l/-L) — a mutating verb exits 65.

_read() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      patch|update|create|delete|remove*|add*|set*|rsync|cp|mv|rm|import|export|restore|clone|deploy|enable|disable)
        echo "restore-drill.sh: _read refuses mutating verb '$arg'" >&2; exit 65 ;;
    esac
  done
  gcloud "$@"
}

# ---- evidence -----------------------------------------------------------------

_evidence_dir() {
  # $1 = phase tag
  printf '%s/%s-%s' \
    "${SIG_DRILL_EVIDENCE_DIR:-${_here}/../../docs/build/logs/restore-drill}" \
    "$1" "$(date -u +%Y%m%dT%H%M%SZ)"
}

_capture_state() {
  # $1 = phase tag. Read-only: instance list, sig-pg describe, backups, recent
  # ops, sig-materialize executions, latest sig-probe executions, the
  # sig-backups object listing.
  local dir f
  dir="$(_evidence_dir "$1")"; mkdir -p "$dir"
  _read sql instances list --project "$SIG_GCP_PROJECT" --format=json \
    > "$dir/instances.json"
  _read sql instances describe "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/sql-sig-pg.json"
  _read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/backups.json"
  _read sql operations list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --limit=10 --format=json > "$dir/operations.json"
  _read run jobs executions list --job sig-materialize \
    --region "$SIG_GCP_REGION" --project "$SIG_GCP_PROJECT" --format=json \
    > "$dir/materialize-execs.json" 2>/dev/null || echo "[]" > "$dir/materialize-execs.json"
  _read run jobs executions list --job "$SIG_RUN_JOB_PROBE" \
    --region "$SIG_GCP_REGION" --project "$SIG_GCP_PROJECT" --limit=2 \
    --format=json > "$dir/probe-execs.json" 2>/dev/null || echo "[]" > "$dir/probe-execs.json"
  _read storage ls -l "gs://${SIG_BUCKET_BACKUPS}/**" \
    > "$dir/sig-backups-objects.txt" 2>/dev/null || true
  _read storage buckets describe "gs://${SIG_BUCKET_BACKUPS}" --format=json \
    > "$dir/describe.sig-backups.json" 2>/dev/null || true
  for f in "$dir"/*; do
    [ -f "$f" ] && echo "STATE $1 $(basename "$f") sha256=$(_sha256 "$f")"
  done
  echo "state-dir: $dir"
}

# ---- stop rules (the contract's voided-by) --------------------------------------

_assert_restore_point() {
  # A failed restore point voids the pre-authorisation: the newest sig-pg
  # backup must be SUCCESSFUL before the clone may be issued.
  local newest status btype
  newest="$(_read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --limit=1 --format=json)"
  status="$(printf '%s' "$newest" | python3 -c '
import json,sys
rows=json.load(sys.stdin); r=rows[0] if rows else {}
print(r.get("status",""))')"
  btype="$(printf '%s' "$newest" | python3 -c '
import json,sys
rows=json.load(sys.stdin); r=rows[0] if rows else {}
print(r.get("type",""))')"
  echo "restore-point: newest backup status=$status type=$btype"
  if [ "$status" != "SUCCESSFUL" ]; then
    echo "restore-drill.sh: VOID — the newest sig-pg backup is not SUCCESSFUL" >&2
    echo "  (a failed restore point voids the pre-authorisation); stopped." >&2
    exit 5
  fi
}

_assert_probe_reviewed() {
  # A red probe voids the pre-authorisation. The probe is allowed to stay red
  # ONLY when the caller records, via --probe-note, that the red is the known
  # recorded class (the stale-targets failure documented since 2026-09-27).
  local json state
  json="$(_read run jobs executions list --job "$SIG_RUN_JOB_PROBE" \
    --region "$SIG_GCP_REGION" --project "$SIG_GCP_PROJECT" --limit=1 \
    --format=json 2>/dev/null)" || {
    echo "restore-drill.sh: VOID — could not read sig-probe's last execution" >&2
    echo "  (fail-closed: a red probe voids; an unreadable probe is not green)" >&2
    exit 42; }
  state="$(SIG_PJ="$json" python3 - <<'PY'
import json, os, sys
rows = json.loads(os.environ["SIG_PJ"])
if not rows:
    print("missing"); sys.exit(0)
conds = (rows[0].get("status") or {}).get("conditions") or []
done = [c for c in conds if c.get("type") == "Completed"]
print("green" if any(str(c.get("status")) == "True" for c in done)
      else "red:" + ";".join(str(c.get("message", ""))[:120] for c in done))
PY
)"
  case "$state" in
    green) echo "probe-check: latest sig-probe sweep green" ;;
    missing)
      echo "restore-drill.sh: VOID — no sig-probe executions readable" >&2; exit 42 ;;
    red:*)
      echo "probe-check: latest sig-probe sweep is RED — ${state#red:}" >&2
      if [ -z "$PROBE_NOTE" ]; then
        echo "restore-drill.sh: VOID — a red probe voids the pre-authorisation." >&2
        echo "  If this is the recorded known-red class, re-run with" >&2
        echo "  --probe-note \"<the recorded judgment>\" (it lands in the evidence dir)." >&2
        exit 42
      fi
      echo "probe-note (recorded): $PROBE_NOTE"
      ;;
  esac
}

_assert_clone_flags() {
  local help_text
  help_text="$(gcloud sql instances clone --help 2>/dev/null || true)"
  printf '%s' "$help_text" | grep -q -- '--point-in-time' || {
    echo "restore-drill.sh: gcloud does not advertise '--point-in-time' on 'sql instances clone' — check the CLI version before mutating" >&2
    exit 4; }
  echo "flag-check: 'gcloud sql instances clone' supports --point-in-time"
}

_name_check() {
  # The delete/verify name gate — the module is the single implementation.
  (cd "$REPO_ROOT" && uv run python - "$1") <<'PY'
import sys
from ops.cloudsql_drill import DrillNameError, assert_drill_name
try:
    assert_drill_name(sys.argv[1])
except DrillNameError as exc:
    print(f"restore-drill.sh: REFUSED — {exc}", file=sys.stderr)
    sys.exit(42)
PY
}

_newest_drill_instance() {
  # The newest sig-pg-drill-* instance (empty when none).
  _read sql instances list --project "$SIG_GCP_PROJECT" \
    --format='value(name)' | grep '^sig-pg-drill' | sort | tail -1 || true
}

_wait_op() {
  # $1 op name; $2 = expected operationType (ERE). Polls to DONE (<=30 min —
  # a clone can take a while). Returns 5 on failure.
  local name="$1" want="$2" tries=0 body status otype
  while [ $tries -lt 180 ]; do
    body="$(_read sql operations describe "$name" --project "$SIG_GCP_PROJECT" --format=json)" || {
      echo "restore-drill.sh: op $name describe failed" >&2; return 5; }
    status="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
    otype="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("operationType",""))')"
    if [ "$status" = "DONE" ]; then
      printf '%s' "$otype" | grep -Eq "^(${want})$" || {
        echo "restore-drill.sh: op $name finished with unexpected operationType '$otype' (wanted $want)" >&2
        return 5; }
      echo "op $name: DONE ($otype)"
      return 0
    fi
    case "$status" in
      RUNNING|PENDING) sleep 10; tries=$((tries+1)) ;;
      *) echo "restore-drill.sh: op $name unexpected status '$status'" >&2; return 5 ;;
    esac
  done
  echo "restore-drill.sh: op $name did not finish in 30 min" >&2; return 5
}

_wait_runnable() {
  # $1 instance — poll describe until state RUNNABLE (<=30 min).
  local name="$1" tries=0 state
  while [ $tries -lt 180 ]; do
    state="$(_read sql instances describe "$name" --project "$SIG_GCP_PROJECT" \
      --format='value(state)' 2>/dev/null || true)"
    if [ "$state" = "RUNNABLE" ]; then echo "instance $name: RUNNABLE"; return 0; fi
    sleep 10; tries=$((tries+1))
  done
  echo "restore-drill.sh: $name did not reach RUNNABLE in 30 min" >&2; return 5
}

# ---- plans ---------------------------------------------------------------------

plan_prestate() {
  cat <<EOF
PLAN: capture pre-state JSON under \$SIG_DRILL_EVIDENCE_DIR (gitignored):
PLAN:   gcloud sql instances list + describe $SIG_SQL_INSTANCE
PLAN:   gcloud sql backups list --instance $SIG_SQL_INSTANCE
PLAN:   gcloud sql operations list --instance $SIG_SQL_INSTANCE --limit=10
PLAN:   gcloud run jobs executions list --job sig-materialize / --job $SIG_RUN_JOB_PROBE
PLAN:   gcloud storage ls -l gs://$SIG_BUCKET_BACKUPS/** + buckets describe
EOF
}

plan_clone() {
  cat <<EOF
PLAN: leg 1 (S5-3 pre-authorised; expires GATE-G4) — the PITR drill clone:
PLAN:   window guard (never 03:00-10:00Z; no running sig-materialize — fail-closed)
PLAN:   newest sig-pg backup must be SUCCESSFUL (a failed restore point voids)
PLAN:   latest sig-probe sweep must be green, else --probe-note records the
PLAN:     judgment that the red is the known recorded class
PLAN:   T = now - 10min; STAMP = %Y%m%dt%H%Mz
PLAN:   gcloud sql instances clone $SIG_SQL_INSTANCE sig-pg-drill-<STAMP> \\
PLAN:     --point-in-time <T> --async ; poll op DONE (CLONE); poll RUNNABLE
PLAN:   rollback/cleanup: restore-drill.sh --apply deleteclone sig-pg-drill-<STAMP>
PLAN:     (name-checked — refuses $SIG_SQL_INSTANCE outright)
EOF
}

plan_counts() {
  cat <<EOF
PLAN: parity verification through the Cloud SQL Auth Proxy:
PLAN:   cloud-sql-proxy $SIG_GCP_PROJECT:$SIG_GCP_REGION:$SIG_SQL_INSTANCE --port <base>
PLAN:   cloud-sql-proxy $SIG_GCP_PROJECT:$SIG_GCP_REGION:sig-pg-drill-<STAMP> --port <base+1>
PLAN:   SIG_DRILL_DSN_{SOURCE,CLONE} env -> uv run python -m ops cloudsql-drill
PLAN:     --at <T> --clone-instance <name> --clone-started-at <recorded>
PLAN:   per-table counts at T (the shared_temporal_contract facet instants),
PLAN:   spine_watermark row set, sqitch.changes ordered tip, PostGIS version,
PLAN:   RTO (clone submit -> verified) + RPO (T - max lower(sys_period)) ->
PLAN:   record.json (sig.restore-drill/1). SELECTs only; the DSN stays in env.
EOF
}

plan_smoke() {
  cat <<EOF
PLAN: api smoke against the clone (read-only):
PLAN:   uv run python -m api serve --dsn <clone DSN> --host 127.0.0.1 --port <p>
PLAN:   GET http://127.0.0.1:<p>/health -> 200
PLAN:   GET http://127.0.0.1:<p>/v1/coverage/national -> recorded status
PLAN:   merge {api_smoke:{health,coverage}} into record.json; kill the server
EOF
}

plan_deleteclone() {
  cat <<EOF
PLAN: name-checked delete (the cleanup the whole drill is judged by):
PLAN:   assert_drill_name(<name>) — refuses $SIG_SQL_INSTANCE outright and any
PLAN:     name outside sig-pg-drill(-b)?-<YYYYmmddtHHMMz> (exit 42)
PLAN:   gcloud sql instances delete <name> --quiet ; poll gone
PLAN:   post-state: gcloud sql instances list — no sig-pg-drill-* remains
EOF
}

plan_fullrestore() {
  cat <<EOF
PLAN: leg 3 (QUEUED — not on the S5-3 list; needs an in-ticket --go or a
PLAN:   GATE-G4 OM-20 listing; --apply refuses with exit 42 otherwise):
PLAN:   create empty sig-pg-drill-b-<STAMP> (same tier family, POSTGRES_18)
PLAN:   gcloud sql backups restore <newest AUTOMATED id> \\
PLAN:     --backup-instance=$SIG_SQL_INSTANCE --restore-instance=sig-pg-drill-b-<STAMP>
PLAN:   poll op DONE (RESTORE_VOLUME) -> RUNNABLE -> counts/smoke/deleteclone
PLAN:   as in the PITR variant (T = the backup's window end).
EOF
}

# ---- actions -----------------------------------------------------------------

act_prestate() { _capture_state pre; }

_DRILL_DIR=""
_DRILL_NAME=""
_DRILL_T=""
_DRILL_STARTED=""

_drill_dir_init() {
  _DRILL_DIR="$(_evidence_dir drill)"
  mkdir -p "$_DRILL_DIR"
}

_drill_dir_save() {
  # Values are quoted — PROBE_NOTE carries prose (parens, dashes) and meta.env
  # is sourced back by _drill_dir_load (an unquoted note broke the 2026-10-02
  # live leg at the counts hand-off).
  cat > "$_DRILL_DIR/meta.env" <<EOF
STAMP="$(date -u +%Y%m%dt%H%Mz)"
NAME="$_DRILL_NAME"
T="$_DRILL_T"
CLONE_STARTED="$_DRILL_STARTED"
PROBE_NOTE="$PROBE_NOTE"
EOF
  echo "meta -> $_DRILL_DIR/meta.env"
}

_drill_dir_load() {
  # Locate the meta.env of the newest drill-* evidence dir (or the one the
  # caller's --clone-name/--at overrides).
  local d
  d="$(ls -dt "${SIG_DRILL_EVIDENCE_DIR:-${_here}/../../docs/build/logs/restore-drill}"/drill-* 2>/dev/null | head -1 || true)"
  if [ -n "$d" ] && [ -f "$d/meta.env" ]; then
    _DRILL_DIR="$d"
    # shellcheck disable=SC1090  # meta.env is this script's own written record
    . "$d/meta.env"
    _DRILL_NAME="${CLONE_NAME:-$NAME}"
    _DRILL_T="${AT:-$T}"
    _DRILL_STARTED="$CLONE_STARTED"
  fi
}

act_clone() {
  assert_window
  _assert_restore_point
  _assert_probe_reviewed
  _assert_clone_flags

  local stamp name existing
  stamp="$(date -u +%Y%m%dt%H%Mz)"
  name="sig-pg-drill-${stamp}"
  existing="$(_newest_drill_instance)"
  if [ -n "$existing" ]; then
    if [ "$existing" = "$name" ]; then
      echo "clone: $name already exists — re-run attaches (idempotent)"
    else
      echo "restore-drill.sh: a drill instance already exists: $existing" >&2
      echo "  delete it first: restore-drill.sh --apply deleteclone $existing" >&2
      echo "  (one drill instance at a time — the parity read must name its target)" >&2
      exit 43
    fi
  fi

  _drill_dir_init
  _DRILL_NAME="$name"
  _DRILL_T="${AT:-$(_iso_minus_minutes "$(_iso_now)" 10)}"
  _DRILL_STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [ "$existing" != "$name" ]; then
    local op opname
    op="$(gcloud sql instances clone "$SIG_SQL_INSTANCE" "$name" \
          --point-in-time "$_DRILL_T" --project "$SIG_GCP_PROJECT" \
          --async --format=json)" || {
      echo "restore-drill.sh: clone submit failed — nothing created" >&2; exit 6; }
    opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
    echo "clone: issued op $opname (T=$_DRILL_T)"
    _wait_op "$opname" "CLONE" || {
      echo "restore-drill.sh: clone op did not complete as CLONE — cleanup:" >&2
      echo "  restore-drill.sh --apply deleteclone $name" >&2
      exit 6; }
  fi
  _wait_runnable "$name" || exit 6
  _drill_dir_save
  _read sql instances describe "$name" --project "$SIG_GCP_PROJECT" \
    --format=json > "$_DRILL_DIR/clone.json"
  echo "clone: $_DRILL_NAME at T=$_DRILL_T (started $_DRILL_STARTED)"
}

# ---- proxy + parity ------------------------------------------------------------

_proxy_pids=()

_proxy_stop() {
  local p
  for p in "${_proxy_pids[@]:-}"; do
    [ -n "$p" ] && kill "$p" 2>/dev/null || true
  done
  _proxy_pids=()
}
trap _proxy_stop EXIT

_proxy_start() {
  # $1 instance-conn suffix, $2 port -> background cloud-sql-proxy; waits ready.
  local inst="$1" port="$2" i
  cloud-sql-proxy "${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${inst}" \
    --address 127.0.0.1 --port "$port" --quiet &
  _proxy_pids+=($!)
  for i in $(seq 1 60); do
    if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
      exec 3>&- 3<&- 2>/dev/null || true
      echo "proxy: $inst on 127.0.0.1:$port ready"
      return 0
    fi
    sleep 1
  done
  echo "restore-drill.sh: proxy to $inst never came up on :$port" >&2
  return 5
}

_dsn() {
  # $1 port — psycopg keyword DSN. The password comes from env, never argv.
  printf 'host=127.0.0.1 port=%s dbname=%s user=%s password=%s sslmode=disable' \
    "$1" "${SIG_PG_DB_NAME:-sig}" "${SIG_PG_USER:-sig}" "${SIG_PG_PASSWORD}"
}

_load_password() {
  if [ -z "${SIG_PG_PASSWORD:-}" ]; then
    SIG_PG_PASSWORD=$(gcloud secrets versions access latest \
      --secret="$SIG_SECRET_PG_PASSWORD" --project="$SIG_GCP_PROJECT" 2>/dev/null) || {
      echo "restore-drill.sh: could not read Secret Manager $SIG_SECRET_PG_PASSWORD" >&2
      echo "  (export SIG_PG_PASSWORD or grant secrets access; it stays in memory)" >&2
      exit 4; }
  fi
  export SIG_PG_PASSWORD
}

act_counts() {
  _drill_dir_load
  [ -n "$_DRILL_NAME" ] || _DRILL_NAME="${CLONE_NAME:-$(_newest_drill_instance)}"
  [ -n "$_DRILL_NAME" ] || {
    echo "restore-drill.sh: no drill instance — pass --clone-name or run clone first" >&2; exit 66; }
  _name_check "$_DRILL_NAME"
  [ -n "$_DRILL_T" ] || _DRILL_T="${AT:-}"
  [ -n "$_DRILL_T" ] || {
    echo "restore-drill.sh: no restore point recorded — pass --at <T> or run clone first" >&2; exit 66; }
  [ -n "$_DRILL_DIR" ] || { _drill_dir_init; _drill_dir_save; }
  _load_password

  local base="${SIG_DRILL_PROXY_PORT:-5441}"
  _proxy_start "$SIG_SQL_INSTANCE" "$base"
  _proxy_start "$_DRILL_NAME" "$((base + 1))"

  export SIG_DRILL_DSN_SOURCE="$(_dsn "$base")"
  export SIG_DRILL_DSN_CLONE="$(_dsn "$((base + 1))")"
  (cd "$REPO_ROOT" && uv run python -m ops cloudsql-drill \
    --at "$_DRILL_T" --clone-instance "$_DRILL_NAME" \
    --clone-started-at "${_DRILL_STARTED:-$_DRILL_T}" \
    --out "$_DRILL_DIR/record.json")
}

act_smoke() {
  _drill_dir_load
  [ -n "$_DRILL_NAME" ] || _DRILL_NAME="${CLONE_NAME:-$(_newest_drill_instance)}"
  _name_check "$_DRILL_NAME"
  _load_password
  local base="${SIG_DRILL_PROXY_PORT:-5441}" aport="${SIG_DRILL_API_PORT:-8477}"
  _proxy_start "$_DRILL_NAME" "$((base + 1))"

  SIG_API_DSN="$(_dsn "$((base + 1))")"
  (cd "$REPO_ROOT" && uv run python -m api serve --dsn "$SIG_API_DSN" \
    --host 127.0.0.1 --port "$aport") &
  local api_pid=$!
  _proxy_pids+=("$api_pid")
  local i code="" cov=""
  for i in $(seq 1 60); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$aport/health" 2>/dev/null || true)"
    [ "$code" = "200" ] && break
    sleep 1
  done
  echo "smoke: /health -> ${code:-<no answer>}"
  if [ "$code" != "200" ]; then
    echo "restore-drill.sh: clone api /health not 200" >&2; exit 5
  fi
  cov="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$aport/v1/coverage/national" 2>/dev/null || true)"
  echo "smoke: /v1/coverage/national -> ${cov:-<no answer>}"
  kill "$api_pid" 2>/dev/null || true
  # merge api_smoke into the record (append-only elsewhere; this is the record
  # being built — the smoke leg completes it before it is evidence).
  if [ -f "$_DRILL_DIR/record.json" ]; then
    SIG_REC="$_DRILL_DIR/record.json" SIG_H="$code" SIG_C="$cov" python3 - <<'PY'
import json, os
p = os.environ["SIG_REC"]
d = json.load(open(p))
d["api_smoke"] = {"health": int(os.environ["SIG_H"]), "coverage": int(os.environ["SIG_C"])}
with open(p, "w") as fh:
    fh.write(json.dumps(d, indent=2, sort_keys=True) + "\n")
print("record: api_smoke merged")
PY
  fi
  [ "$cov" = "200" ] || {
    echo "restore-drill.sh: clone api /v1/coverage/national not 200 ($cov)" >&2; exit 5; }
}

act_deleteclone() {
  local name="${CLONE_NAME:-${1:-}}"
  [ -n "$name" ] || name="$(_newest_drill_instance)"
  [ -n "$name" ] || {
    echo "restore-drill.sh: deleteclone needs a name (no sig-pg-drill-* exists)" >&2; exit 64; }
  _name_check "$name"   # refuses sig-pg outright; exit 42 on any non-drill name
  echo "delete: name-checked $name (the command can only ever name a drill instance)"
  gcloud sql instances delete "$name" --project "$SIG_GCP_PROJECT" --quiet || {
    echo "restore-drill.sh: delete of $name failed" >&2; exit 6; }
  local after
  after="$(_read sql instances list --project "$SIG_GCP_PROJECT" --format='value(name)')"
  echo "instances after delete: ${after:-<none>}"
  printf '%s\n' "$after" | grep -q '^sig-pg-drill' && {
    echo "restore-drill.sh: a drill instance remains after delete — inspect" >&2; exit 6; }
  echo "delete: no sig-pg-drill-* remains"
}

act_fullrestore() {
  if [ -z "$GO" ]; then
    echo "restore-drill.sh: REFUSED — leg 3 (the full-backup variant) is not on the" >&2
    echo "  S5-3 pre-authorisation; it needs a verbatim in-ticket --go or a GATE" >&2
    echo "  listing. Queued: see docs/tickets/DEFERRALS.md D-P34.6-*." >&2
    exit 42
  fi
  echo "fullrestore: go recorded — $GO"
  assert_window
  _assert_restore_point
  _assert_probe_reviewed

  local stamp name backup_id op opname
  stamp="$(date -u +%Y%m%dt%H%Mz)"
  name="sig-pg-drill-b-${stamp}"
  backup_id="$(_read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --format='value(id)' --limit=1)"
  [ -n "$backup_id" ] || { echo "restore-drill.sh: no backup id readable" >&2; exit 5; }
  _name_check "$name"

  _drill_dir_init
  _DRILL_NAME="$name"
  _DRILL_STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # T for the full-backup variant = the backup's window end.
  _DRILL_T="$(_read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --format=json --limit=1 \
    | python3 -c 'import json,sys; r=json.load(sys.stdin)[0]; print((r.get("endTime") or r.get("enqueuedTime") or "").replace("+00:00","Z"))')"

  op="$(gcloud sql instances create "$name" \
        --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" \
        --database-version=POSTGRES_18 --tier=db-custom-1-3840 \
        --storage-size=15 --no-backup --async --format=json)" || {
    echo "restore-drill.sh: empty drill-instance create failed" >&2; exit 6; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  _wait_op "$opname" "CREATE" || exit 6

  op="$(gcloud sql backups restore "$backup_id" \
        --backup-instance="$SIG_SQL_INSTANCE" --restore-instance="$name" \
        --project "$SIG_GCP_PROJECT" --async --format=json)" || {
    echo "restore-drill.sh: backups restore submit failed; cleanup:" >&2
    echo "  restore-drill.sh --apply deleteclone $name" >&2; exit 6; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  _wait_op "$opname" "RESTORE_VOLUME" || {
    echo "  cleanup: restore-drill.sh --apply deleteclone $name" >&2; exit 6; }
  _wait_runnable "$name" || exit 6
  _drill_dir_save
  _read sql instances describe "$name" --project "$SIG_GCP_PROJECT" \
    --format=json > "$_DRILL_DIR/clone.json"
  echo "fullrestore: $name from backup $backup_id (T=$_DRILL_T)"
}

# ---- verify (read-only outcome diff; live or recorded JSON) --------------------

_verify_python() {
  # $1 = dir holding record.json + instances-after.json (or live equivalents).
  SIG_STATE_DIR="$1" python3 - <<'PY'
import glob, json, os, sys

state = os.environ["SIG_STATE_DIR"]
ok = drift = 0

def load(*names):
    for n in names:
        for p in sorted(glob.glob(os.path.join(state, n))):
            try:
                return json.load(open(p))
            except Exception:
                continue
    return None

def report(good, check, detail=""):
    global ok, drift
    if good:
        ok += 1
        print(f"OK {check}" + (f" — {detail}" if detail else ""))
    else:
        drift += 1
        print(f"DRIFT {check}: {detail}")

rec = load("record.json", "record*.json")
if rec is None:
    report(False, "drill:record", "no record.json in state dir")
else:
    report(bool(rec.get("reproduced")), "drill:reproduced",
           f"reproduced={rec.get('reproduced')!r}")
    report(bool(rec.get("at")), "drill:restore-point-T",
           f"at={rec.get('at')!r}")
    report(isinstance(rec.get("rto_seconds"), (int, float)),
           "drill:rto", f"rto_seconds={rec.get('rto_seconds')!r}")
    report(isinstance(rec.get("rpo_seconds"), (int, float)),
           "drill:rpo", f"rpo_seconds={rec.get('rpo_seconds')!r}")
    tables = rec.get("tables") or []
    report(bool(tables) and all(t.get("equal") for t in tables),
           "drill:per-table-parity",
           f"{sum(1 for t in tables if t.get('equal'))}/{len(tables)} equal")
    report(rec.get("watermark_equal") is True, "drill:watermark-equal",
           f"watermark_equal={rec.get('watermark_equal')!r}")
    report(rec.get("sqitch_equal") is True, "drill:sqitch-tip-equal",
           f"sqitch_equal={rec.get('sqitch_equal')!r}")
    report(bool(rec.get("postgis_source")) and bool(rec.get("postgis_clone")),
           "drill:postgis",
           f"source={rec.get('postgis_source')!r} clone={rec.get('postgis_clone')!r}")
    smoke = rec.get("api_smoke") or {}
    report(smoke.get("health") == 200 and smoke.get("coverage") == 200,
           "drill:api-smoke", f"api_smoke={smoke!r}")

insts = load("instances-after.json", "post-instances.json", "instances.json")
if insts is None:
    report(False, "drill:no-instance-left", "no post-delete instance list in state dir")
else:
    names = [i.get("name", "") for i in insts]
    drills = [n for n in names if n.startswith("sig-pg-drill")]
    report(not drills, "drill:no-instance-left",
           f"instances={names}")
    report("sig-pg" in names, "drill:sig-pg-untouched",
           f"sig-pg present={('sig-pg' in names)}")

print(f"verify: {ok} OK, {drift} DRIFT")
print("probe: restore-drill-verify result=" + ("ok" if drift == 0 else "drift"))
sys.exit(1 if drift else 0)
PY
}

act_verify() {
  if [ -n "$FROM_STATE" ]; then
    [ -d "$FROM_STATE" ] || {
      echo "restore-drill.sh: --from-state '$FROM_STATE' is not a directory" >&2; exit 66; }
    echo "verify: from-state $FROM_STATE"
    _verify_python "$FROM_STATE"
    return $?
  fi
  local dir
  dir="$(_evidence_dir verify)"; mkdir -p "$dir"
  echo "verify: live reads -> $dir"
  _read sql instances list --project "$SIG_GCP_PROJECT" --format=json \
    > "$dir/instances-after.json"
  local rec
  rec="$(ls -t "${SIG_DRILL_EVIDENCE_DIR:-${_here}/../../docs/build/logs/restore-drill}"/drill-*/record.json 2>/dev/null | head -1 || true)"
  if [ -n "$rec" ]; then cp "$rec" "$dir/record.json"; fi
  _verify_python "$dir"
}

# ---- dispatch ------------------------------------------------------------------

case "$MODE" in
  check)
    echo "restore-drill.sh --check (action=$ACTION): plan only — no ADC, no network."
    require_project
    _derive_names
    case "$ACTION" in
      prestate)     plan_prestate ;;
      clone)        plan_clone ;;
      counts)       plan_counts ;;
      smoke)        plan_smoke ;;
      deleteclone)  plan_deleteclone ;;
      fullrestore)  plan_fullrestore ;;
      all)
        plan_prestate; plan_clone; plan_counts; plan_smoke; plan_deleteclone
        echo "PLAN: then post-state capture + '--verify' diff"
        plan_fullrestore
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
      prestate)     act_prestate ;;
      clone)        act_clone ;;
      counts)       act_counts ;;
      smoke)        act_smoke ;;
      deleteclone)  assert_window  # cleanup is still a mutation — gated like clone
                    act_deleteclone ;;
      fullrestore)  act_fullrestore ;;
      all)
        assert_window
        act_prestate
        act_clone
        act_counts
        act_smoke
        act_deleteclone
        _capture_state post
        act_verify || { echo "restore-drill.sh: post-verify reported drift — see DRIFT lines" >&2; exit 8; }
        ;;
    esac
    ;;
esac
