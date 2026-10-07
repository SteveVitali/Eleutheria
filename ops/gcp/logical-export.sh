#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/logical-export.sh — P34.6 (SIG-OPS-001, ADR-175): the monthly logical
# export that lives OUTSIDE the Cloud SQL instance lifecycle, plus the
# sig-backups bucket lifecycle policy and the seed-dump relabel-by-copy.
#
#   export      `gcloud sql export sql sig-pg gs://<p>-sig-backups/pg/monthly/
#               <YYYY-MM>/sig-<STAMP>.sql --database sig` -> poll the EXPORT op
#               DONE -> object listing + size into the evidence dir.
#               The export loads sig-pg (1 vCPU) -> the window guard is the
#               strictest one: outside the 03:00-10:00Z band AND outside AR-3.
#   lifecycle   `gcloud storage buckets update` of a lifecycle.json holding the
#               two P34.6 rules ONLY: Delete pg/monthly/* at 100 days (keeps the
#               three newest monthly exports), Delete pg/adhoc/* at 30 days.
#               Read-then-compare: existing non-P34.6 rules -> REFUSE (never
#               silently overwrite someone else's rules).
#   relabel     copy the two 2026-09-15 seed dumps to pg/seed-2026-09-15/ and
#               write a README object naming the intent — the originals stay
#               put (nothing under pg/ is ever deleted by this script).
#
# AUTHORISATION: none of these is on the 11A S5-3 list. Every apply action
# other than `prestate` requires --go "<verbatim in-ticket go or GATE listing>"
# — without it the script refuses (exit 42) and the leg stays queued in
# docs/tickets/DEFERRALS.md (D-P34.6-2/3/4).
#
# Usage:
#   ops/gcp/logical-export.sh [--check|--dry-run] [ACTION]      # plan (default)
#   ops/gcp/logical-export.sh --verify [--from-state DIR]       # read-only diff
#   ops/gcp/logical-export.sh --apply ACTION --go "<verbatim go>"
#
# ACTION (default `all`): prestate | export | lifecycle | relabel | all
#
# Env: SIG_GCP_PROJECT (required for apply/live-verify), SIG_GCP_REGION,
#   SIG_EVIDENCE_DIR (default <repo>/docs/build/logs/logical-export),
#   SIG_EXPORT_NOW (ISO-8601 UTC clock seam for the window guard; tests only),
#   SIG_EXPORT_MONTHLY_AGE_DAYS (default 100), SIG_EXPORT_ADHOC_AGE_DAYS (30).

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${_here}/../.." && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

_usage() {
  sed -n '/^# Usage:/,/^# Env:/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-64}"
}

MODE="check"
ACTION="all"
FROM_STATE=""
GO=""

case "${1:-}" in
  --apply) MODE="apply"; shift ;;
  --verify) MODE="verify"; shift ;;
  --check|--dry-run) MODE="check"; shift ;;
  -h|--help) _usage 0 ;;
  "") MODE="check" ;;
  prestate|export|lifecycle|relabel|all) MODE="check" ;;
  *) echo "logical-export.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    --from-state)
      [ $# -ge 2 ] || { echo "logical-export.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    --go)
      [ $# -ge 2 ] || { echo "logical-export.sh: --go needs the verbatim go text" >&2; exit 64; }
      GO="$2"; shift 2 ;;
    --go=*) GO="${1#--go=}"; shift ;;
    prestate|export|lifecycle|relabel|all)
      [ "$ACTION" = "all" ] || { echo "logical-export.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    *) echo "logical-export.sh: unknown argument '$1'" >&2; _usage 64 ;;
  esac
done

export SIG_GCP_MODE="$MODE"

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_iso_now() {
  if [ -n "${SIG_EXPORT_NOW:-}" ]; then printf '%s\n' "$SIG_EXPORT_NOW";
  else date -u +%Y-%m-%dT%H:%M:%SZ; fi
}

_epoch() {
  if date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%s >/dev/null 2>&1; then
    date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%s
  else
    date -u -d "$1" +%s
  fi
}

_in_daily_band() {
  local hh
  hh="$(printf '%s' "$1" | sed 's/.*T//; s/:.*//')"
  [ "$hh" -ge 3 ] && [ "$hh" -lt 10 ]
}

_ar3_window_active() {
  # The scheduled sig-materialize window on the first weekend of the month
  # (AR-3): day-of-month <= 7, SAT or SUN. The export is gated on AR-3 as well
  # as the daily band (it loads sig-pg's 1 vCPU).
  local dow dom
  dom="$(printf '%s' "$1" | cut -dT -f1 | cut -d- -f3 | sed 's/^0//')"
  case "$1" in
    *T*[0-9]) : ;; # any ISO instant — the dow comes from date itself
  esac
  if date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%u >/dev/null 2>&1; then
    dow="$(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%u)"
  else
    dow="$(date -u -d "$1" +%u)"
  fi
  [ "$dom" -le 7 ] && { [ "$dow" = "6" ] || [ "$dow" = "7" ]; }
}

_read() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      patch|update|create|delete|remove*|add*|set*|rsync|cp|mv|rm|import|export|restore|clone|deploy|enable|disable)
        echo "logical-export.sh: _read refuses mutating verb '$arg'" >&2; exit 65 ;;
    esac
  done
  gcloud "$@"
}

_require_go() {
  if [ -z "$GO" ]; then
    echo "logical-export.sh: REFUSED — '$ACTION' is not on the S5-3 pre-authorisation list." >&2
    echo "  The monthly export, the bucket lifecycle, and the seed relabel each need" >&2
    echo "  a verbatim in-ticket --go (or a GATE listing). Until then they are queued:" >&2
    echo "  docs/tickets/DEFERRALS.md D-P34.6-2 (export) / -3 (lifecycle) / -4 (relabel)." >&2
    exit 42
  fi
  echo "go (recorded verbatim): $GO"
}

assert_window() {
  local now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=sigpg-export"
  if _in_daily_band "$now"; then
    echo "logical-export.sh: REFUSED — inside the 03:00-10:00Z batch band ($now)" >&2
    exit 42
  fi
  if _ar3_window_active "$now"; then
    echo "logical-export.sh: REFUSED — the AR-3 materialize window is active ($now)" >&2
    exit 42
  fi
  echo "window-guard: OK"
}

_evidence_dir() {
  printf '%s/%s-%s' \
    "${SIG_EVIDENCE_DIR:-${_here}/../../docs/build/logs/logical-export}" \
    "$1" "$(date -u +%Y%m%dT%H%M%SZ)"
}

_wait_export_op() {
  # $1 op name -> DONE within 30 min, operationType EXPORT.
  local name="$1" tries=0 body status otype
  while [ $tries -lt 180 ]; do
    body="$(_read sql operations describe "$name" --project "$SIG_GCP_PROJECT" --format=json)" || return 5
    status="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
    otype="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("operationType",""))')"
    if [ "$status" = "DONE" ]; then
      printf '%s' "$otype" | grep -q "^EXPORT" || {
        echo "logical-export.sh: op $name opType '$otype' — unexpected" >&2; return 5; }
      echo "op $name: DONE ($otype)"; return 0
    fi
    case "$status" in
      RUNNING|PENDING) sleep 10; tries=$((tries+1)) ;;
      *) echo "logical-export.sh: op $name status '$status'" >&2; return 5 ;;
    esac
  done
  return 5
}

_lifecycle_rules() {
  # The two P34.6 rules (and only ours) as JSON on stdout.
  python3 - <<PY
import json
rules = [
    {"action": {"type": "Delete"},
     "condition": {"age": ${SIG_EXPORT_MONTHLY_AGE_DAYS:-100},
                   "matchesPrefix": ["pg/monthly/"]}},
    {"action": {"type": "Delete"},
     "condition": {"age": ${SIG_EXPORT_ADHOC_AGE_DAYS:-30},
                   "matchesPrefix": ["pg/adhoc/"]}},
]
print(json.dumps({"rule": rules}, indent=2, sort_keys=True))
PY
}

_existing_rules() {
  # stdout: existing lifecycle rule count (0 when none / unreadable-describe
  # reports a missing lifecycle block as 'None').
  _read storage buckets describe "gs://${SIG_GCP_PROJECT}-sig-backups" \
    --format=json 2>/dev/null | python3 -c '
import json,sys
try:
    b = json.load(sys.stdin)
except Exception:
    print(-1); sys.exit(0)
rules = ((b.get("lifecycle") or {}).get("rule")) or []
print(len(rules))'
}

# ---- plans --------------------------------------------------------------------

plan_prestate() {
  cat <<'EOF'
PLAN: capture pre-state (read-only):
PLAN:   gcloud storage buckets describe gs://$SIG_GCP_PROJECT-sig-backups
PLAN:   gcloud storage ls -l gs://$SIG_GCP_PROJECT-sig-backups/**
EOF
}

plan_export() {
  cat <<'EOF'
PLAN: leg 2a — the monthly logical export (QUEUED until an in-ticket --go):
PLAN:   window guard (outside 03:00-10:00Z AND outside AR-3; the export loads
PLAN:     sig-pg's single vCPU)
PLAN:   gcloud sql export sql sig-pg \
PLAN:     gs://$SIG_GCP_PROJECT-sig-backups/pg/monthly/<YYYY-MM>/sig-<STAMP>.sql \
PLAN:     --database sig --async ; poll op DONE (EXPORT)
PLAN:   object listing + size -> evidence dir; the dump lives in the bucket, so
PLAN:     deleting sig-pg does not take the dump with it (outside the instance
PLAN:     lifecycle — the contract's point).
EOF
}

plan_lifecycle() {
  cat <<'EOF'
PLAN: leg 2b — sig-backups lifecycle (QUEUED until an in-ticket --go):
PLAN:   read existing rules first; if any are not exactly the two P34.6 rules
PLAN:     -> REFUSE (never overwrite foreign rules silently)
PLAN:   gcloud storage buckets update gs://...-sig-backups --lifecycle-file <tmp>
PLAN:   rules: Delete pg/monthly/* at 100d (keeps the three newest monthly
PLAN:     exports), Delete pg/adhoc/* at 30d; pg/seed-*/ is never matched —
PLAN:     seed dumps are preserved.
EOF
}

plan_relabel() {
  cat <<'EOF'
PLAN: leg 2c — seed-dump relabel BY COPY (QUEUED until an in-ticket --go):
PLAN:   gcloud storage ls gs://...-sig-backups/pg/ -> each pg/sig-2026*.sql
PLAN:   gcloud storage cp <obj> gs://...-sig-backups/pg/seed-2026-09-15/<obj>
PLAN:   write pg/seed-2026-09-15/README.md explaining the copies
PLAN:   the originals are NEVER deleted; an already-copied object is SKIP
EOF
}

# ---- actions -------------------------------------------------------------------

act_prestate() {
  local dir f
  dir="$(_evidence_dir pre)"; mkdir -p "$dir"
  _read storage buckets describe "gs://${SIG_GCP_PROJECT}-sig-backups" \
    --format=json > "$dir/describe.sig-backups.json"
  _read storage ls -l "gs://${SIG_GCP_PROJECT}-sig-backups/**" \
    > "$dir/objects.txt" 2>/dev/null || true
  _read sql instances describe "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/sql-sig-pg.json"
  for f in "$dir"/*; do
    [ -f "$f" ] && echo "STATE pre $(basename "$f") sha256=$(_sha256 "$f")"
  done
  echo "state-dir: $dir"
}

act_export() {
  _require_go
  assert_window
  local dir stamp month obj op opname f
  dir="$(_evidence_dir export)"; mkdir -p "$dir"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  month="$(date -u +%Y-%m)"
  obj="gs://${SIG_GCP_PROJECT}-sig-backups/pg/monthly/${month}/sig-${stamp}.sql"
  op="$(gcloud sql export sql "$SIG_SQL_INSTANCE" "$obj" \
        --database="${SIG_PG_DB_NAME:-sig}" --project "$SIG_GCP_PROJECT" \
        --async --format=json)" || {
    echo "logical-export.sh: export submit failed" >&2; exit 5; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  echo "export: op $opname -> $obj"
  _wait_export_op "$opname" || exit $?
  _read storage ls -l "$obj" > "$dir/object.txt" || {
    echo "logical-export.sh: op DONE but the object is not listable — STOP" >&2; exit 5; }
  echo "export object: $(cat "$dir/object.txt")"
  for f in "$dir"/*; do
    [ -f "$f" ] && echo "STATE export $(basename "$f") sha256=$(_sha256 "$f")"
  done
  echo "state-dir: $dir"
}

act_lifecycle() {
  _require_go
  local dir existing tmp
  dir="$(_evidence_dir lifecycle)"; mkdir -p "$dir"
  _read storage buckets describe "gs://${SIG_GCP_PROJECT}-sig-backups" \
    --format=json > "$dir/describe.before.json"
  existing="$(_existing_rules)"
  if [ "$existing" = "-1" ]; then
    echo "logical-export.sh: REFUSED — bucket lifecycle unreadable; not overwriting blind" >&2
    exit 42
  fi
  tmp="$(mktemp -t sig-lifecycle.XXXXXX)"
  _lifecycle_rules > "$tmp"
  if [ "$existing" != "0" ]; then
    # Rules exist: only proceed if they are already exactly ours (idempotent SKIP).
    if SIG_DESC="$dir/describe.before.json" SIG_WANT="$tmp" python3 - <<'PY'
import json, os, sys
canon = lambda rules: sorted(json.dumps(r, sort_keys=True) for r in rules)
want = canon(json.load(open(os.environ["SIG_WANT"]))["rule"])
have = canon(
    ((json.load(open(os.environ["SIG_DESC"])).get("lifecycle") or {}).get("rule")) or []
)
sys.exit(0 if have == want else 1)
PY
    then
      echo "lifecycle: the two P34.6 rules already present — SKIP"
      rm -f "$tmp"; return 0
    fi
    echo "logical-export.sh: REFUSED — the bucket has $existing lifecycle rule(s) that" >&2
    echo "  are not the P34.6 pair; never overwriting foreign rules silently." >&2
    echo "  Inspect: gcloud storage buckets describe gs://${SIG_GCP_PROJECT}-sig-backups" >&2
    rm -f "$tmp"; exit 42
  fi
  gcloud storage buckets update "gs://${SIG_GCP_PROJECT}-sig-backups" \
    --lifecycle-file="$tmp" || {
    echo "logical-export.sh: buckets update failed" >&2; rm -f "$tmp"; exit 6; }
  rm -f "$tmp"
  _read storage buckets describe "gs://${SIG_GCP_PROJECT}-sig-backups" \
    --format=json > "$dir/describe.after.json"
  echo "STATE lifecycle describe.after.json sha256=$(_sha256 "$dir/describe.after.json")"
  echo "lifecycle: P34.6 rules applied (pg/monthly 100d, pg/adhoc 30d)"
}

act_relabel() {
  _require_go
  local dir bucket seed_prefix list obj base target readme
  dir="$(_evidence_dir relabel)"; mkdir -p "$dir"
  bucket="gs://${SIG_GCP_PROJECT}-sig-backups"
  seed_prefix="${bucket}/pg/seed-2026-09-15"
  _read storage ls "${bucket}/pg/" > "$dir/objects.txt" || {
    echo "logical-export.sh: cannot list ${bucket}/pg/ — STOP" >&2; exit 5; }
  list="$(grep -E "/pg/sig-[0-9T]+Z\.sql$" "$dir/objects.txt" || true)"
  if [ -z "$list" ]; then
    echo "relabel: no pg/sig-*.sql objects under ${bucket}/pg/ — SKIP (nothing to relabel)"
    return 0
  fi
  while IFS= read -r obj; do
    base="$(basename "$obj")"
    target="${seed_prefix}/${base}"
    if _read storage ls "$target" >/dev/null 2>&1; then
      echo "relabel: $base already under seed-2026-09-15/ — SKIP"
      continue
    fi
    gcloud storage cp "$obj" "$target" || {
      echo "logical-export.sh: copy of $obj failed — STOP (source untouched)" >&2; exit 5; }
    echo "relabel: copied $base -> pg/seed-2026-09-15/$base (original preserved)"
  done <<< "$list"
  readme="$(mktemp -t sig-seed-readme.XXXXXX)"
  cat > "$readme" <<'EOF'
P34.6 seed-dump relabel (copy, never delete)

The objects in this prefix are byte-copies of the early pg/sig-*.sql dumps
(taken 2026-09-15 while ADR-075's e2-micro compose path was still the live
deployment). They are SEED artefacts — not the monthly logical export and not
the Cloud SQL managed-backup evidence — relabelled under pg/seed-2026-09-15/
by ops/gcp/logical-export.sh so the pg/monthly/ and pg/adhoc/ lifecycle rules
never confuse them with exports. The originals under pg/ were left in place.
EOF
  gcloud storage cp "$readme" "${seed_prefix}/README.md" || {
    echo "logical-export.sh: README copy failed" >&2; rm -f "$readme"; exit 5; }
  rm -f "$readme"
  _read storage ls -l "${seed_prefix}/**" > "$dir/seed-objects.txt" 2>/dev/null || true
  echo "STATE relabel objects.txt sha256=$(_sha256 "$dir/objects.txt")"
  [ -f "$dir/seed-objects.txt" ] && \
    echo "STATE relabel seed-objects.txt sha256=$(_sha256 "$dir/seed-objects.txt")"
  echo "relabel: originals under pg/ untouched; copies live under pg/seed-2026-09-15/"
}

# ---- verify --------------------------------------------------------------------

_verify_python() {
  SIG_STATE_DIR="$1" python3 - <<'PY'
import glob, json, os, sys

state = os.environ["SIG_STATE_DIR"]
ok = drift = 0

def load_json(*names):
    for n in names:
        for p in sorted(glob.glob(os.path.join(state, n))):
            try:
                return json.load(open(p))
            except Exception:
                continue
    return None

def load_text(*names):
    for n in names:
        for p in sorted(glob.glob(os.path.join(state, n))):
            try:
                return open(p).read()
            except Exception:
                continue
    return ""

def report(good, check, detail=""):
    global ok, drift
    if good:
        ok += 1
        print(f"OK {check}" + (f" — {detail}" if detail else ""))
    else:
        drift += 1
        print(f"DRIFT {check}: {detail}")

desc = load_json("describe*.json", "*describe*.json")
if desc is None:
    report(False, "export:lifecycle-rules", "no bucket describe in state dir")
else:
    rules = ((desc.get("lifecycle") or {}).get("rule")) or []
    monthly = any(
        (r.get("action") or {}).get("type") == "Delete"
        and (r.get("condition") or {}).get("age") == 100
        and "pg/monthly/" in ((r.get("condition") or {}).get("matchesPrefix") or [])
        for r in rules)
    adhoc = any(
        (r.get("action") or {}).get("type") == "Delete"
        and (r.get("condition") or {}).get("age") == 30
        and "pg/adhoc/" in ((r.get("condition") or {}).get("matchesPrefix") or [])
        for r in rules)
    report(monthly, "export:lifecycle-monthly-100d", f"rules={rules!r}")
    report(adhoc, "export:lifecycle-adhoc-30d", f"rules={rules!r}")

objects = load_text("objects*.txt", "*objects*.txt", "seed-objects*.txt")
report("pg/seed-2026-09-15/" in objects, "export:seed-prefix",
       f"{sum(1 for l in objects.splitlines() if 'pg/seed' in l)} seed rows")
report("pg/monthly/" in objects, "export:monthly-export-object",
       f"{sum(1 for l in objects.splitlines() if 'pg/monthly/' in l)} monthly rows")

print(f"verify: {ok} OK, {drift} DRIFT")
print("probe: logical-export-verify result=" + ("ok" if drift == 0 else "drift"))
sys.exit(1 if drift else 0)
PY
}

act_verify() {
  if [ -n "$FROM_STATE" ]; then
    [ -d "$FROM_STATE" ] || {
      echo "logical-export.sh: --from-state '$FROM_STATE' is not a directory" >&2; exit 66; }
    echo "verify: from-state $FROM_STATE"
    _verify_python "$FROM_STATE"
    return $?
  fi
  local dir
  dir="$(_evidence_dir verify)"; mkdir -p "$dir"
  echo "verify: live reads -> $dir"
  _read storage buckets describe "gs://${SIG_GCP_PROJECT}-sig-backups" \
    --format=json > "$dir/describe.sig-backups.json"
  _read storage ls -l "gs://${SIG_GCP_PROJECT}-sig-backups/**" \
    > "$dir/objects.txt" 2>/dev/null || true
  _verify_python "$dir"
}

# ---- dispatch -------------------------------------------------------------------

case "$MODE" in
  check)
    echo "logical-export.sh --check (action=$ACTION): plan only — no ADC, no network."
    require_project
    case "$ACTION" in
      prestate)  plan_prestate ;;
      export)    plan_export ;;
      lifecycle) plan_lifecycle ;;
      relabel)   plan_relabel ;;
      all) plan_prestate; plan_export; plan_lifecycle; plan_relabel ;;
    esac
    echo "check OK"
    ;;
  verify)
    if [ -z "$FROM_STATE" ]; then
      require_project
      require_adc
    fi
    act_verify
    ;;
  apply)
    require_project
    require_adc
    case "$ACTION" in
      prestate)  act_prestate ;;
      export)    act_export ;;
      lifecycle) act_lifecycle ;;
      relabel)   act_relabel ;;
      all)
        _require_go
        act_prestate
        act_export
        act_lifecycle
        act_relabel
        act_verify || { echo "logical-export.sh: post-verify drift" >&2; exit 8; }
        ;;
    esac
    ;;
esac
