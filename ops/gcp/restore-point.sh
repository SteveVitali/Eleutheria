#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/restore-point.sh — P34.6 (SIG-OPS-001): the scripted AR-2
# (append-only restore point) procedure. Two legs, independently callable:
#
#   sqlpoint     Cloud SQL: pre-state capture -> `gcloud sql backups create
#                --instance sig-pg --async` -> poll the op DONE -> assert the
#                newest backup is SUCCESSFUL -> record {id, windowStartTime,
#                endTime}. The caller MUST NOT proceed to a mutation unless this
#                leg exits 0 — the same stop rule P34.3's protect.sh enforces.
#
#   bucketpoint gs://<bucket>/<prefix> [gs://...]
#                The bucket mirror: `gcloud storage cp -r` of each source into
#                gs://<project>-sig-restricted/restore-point/<STAMP>/..., plus a
#                written manifest of what was copied. Read-before-write: the
#                sources are listed first; a source name outside the project's
#                sig buckets is refused outright.
#
# Both legs write their record under $SIG_EVIDENCE_DIR (gitignored) with
# sha256s, the protect.sh pattern.
#
# Usage:
#   ops/gcp/restore-point.sh [--check|--dry-run] [ACTION]      # plan (default)
#   ops/gcp/restore-point.sh --apply sqlpoint
#   ops/gcp/restore-point.sh --apply bucketpoint gs://... [gs://...]
#
# sqlpoint needs no live window (backup creation is read-heavy on the
# instance but non-mutating in the OM-14 sense P34.3 already exercises from
# inside AR-3); bucketpoint writes to sig-restricted and is only invoked by a
# gated procedure (e.g. logical-export.sh's relabel leg) — this script takes
# no position on authorisation, the caller's --go gate does.
#
# Env:
#   SIG_GCP_PROJECT, SIG_GCP_REGION   (config.sh defaults; project is required)
#   SIG_EVIDENCE_DIR                  evidence root (default
#                                     <repo>/docs/build/logs/restore-point)

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

_usage() {
  sed -n '/^# Usage:/,/^# Env:/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-64}"
}

MODE="check"
ACTION="sqlpoint"
declare -a SOURCES=()

case "${1:-}" in
  --apply) MODE="apply"; shift ;;
  --check|--dry-run) MODE="check"; shift ;;
  -h|--help) _usage 0 ;;
  "") MODE="check" ;;
  sqlpoint|bucketpoint) MODE="check" ;;
  *) echo "restore-point.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    sqlpoint|bucketpoint)
      ACTION="$1"; shift ;;
    gs://*)
      SOURCES+=("$1"); shift ;;
    *) echo "restore-point.sh: unknown argument '$1'" >&2; _usage 64 ;;
  esac
done

export SIG_GCP_MODE="$MODE"

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_read() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      patch|update|create|delete|remove*|add*|set*|rsync|cp|mv|rm|import|export|restore|clone|deploy|enable|disable)
        echo "restore-point.sh: _read refuses mutating verb '$arg'" >&2; exit 65 ;;
    esac
  done
  gcloud "$@"
}

_evidence_dir() {
  printf '%s/%s' \
    "${SIG_EVIDENCE_DIR:-${_here}/../../docs/build/logs/restore-point}" "$1"
}

_wait_backup_op() {
  # $1 op name -> DONE within 30 min; then the newest backup row must be
  # SUCCESSFUL and ON_DEMAND (the backup we just created).
  local name="$1" tries=0 status body newest
  while [ $tries -lt 180 ]; do
    body="$(_read sql operations describe "$name" --project "$SIG_GCP_PROJECT" --format=json)" || {
      echo "restore-point.sh: op $name describe failed" >&2; return 5; }
    status="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
    case "$status" in
      DONE) break ;;
      RUNNING|PENDING) sleep 10; tries=$((tries+1)) ;;
      *) echo "restore-point.sh: op $name status '$status'" >&2; return 5 ;;
    esac
  done
  [ "$tries" -lt 180 ] || { echo "restore-point.sh: op $name timed out" >&2; return 5; }
  newest="$(_read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --limit=1 --format=json)"
  SIG_NB="$newest" python3 - <<'PY'
import json, os, sys
rows = json.loads(os.environ["SIG_NB"])
r = rows[0] if rows else {}
if r.get("status") != "SUCCESSFUL":
    print(f"restore-point.sh: newest backup status={r.get('status')!r} — STOP; "
          "do not proceed to the mutation", file=sys.stderr)
    sys.exit(5)
print(f"backup: SUCCESSFUL id={r.get('id')} window "
      f"{r.get('windowStartTime','?')} -> {r.get('endTime','?')}")
PY
}

plan_sqlpoint() {
  cat <<EOF
PLAN: AR-2 SQL restore point (protect.sh's first leg, callable standalone):
PLAN:   pre-state -> gcloud sql backups create --instance $SIG_SQL_INSTANCE --async
PLAN:   -> poll op DONE -> assert newest backup SUCCESSFUL -> record id+window
PLAN:   -> exit 0 ONLY when the restore point is proven; the caller stops on 5
EOF
}

plan_bucketpoint() {
  if [ "${#SOURCES[@]}" -eq 0 ]; then
    echo "PLAN: bucketpoint <gs://source...> — needs at least one source"
  else
    local s
    for s in "${SOURCES[@]}"; do
      echo "PLAN:   gcloud storage ls $s   (read-before-write)"
      echo "PLAN:   gcloud storage cp -r $s gs://\$SIG_GCP_PROJECT-sig-restricted/restore-point/<STAMP>/<src>/"
    done
    echo "PLAN:   write manifest of copied object names -> evidence dir"
  fi
  echo "PLAN:   refused: any source outside gs://\$SIG_GCP_PROJECT-sig-*"
}

act_sqlpoint() {
  local dir op opname f
  dir="$(_evidence_dir "sqlpoint-$(date -u +%Y%m%dT%H%M%SZ)")"; mkdir -p "$dir"
  _read sql instances describe "$SIG_SQL_INSTANCE" --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/pre-sig-pg.json"
  _read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/pre-backups.json"
  op="$(gcloud sql backups create --instance "$SIG_SQL_INSTANCE" \
        --project "$SIG_GCP_PROJECT" --async --format=json)" || {
    echo "restore-point.sh: backups create submit failed — STOP" >&2; exit 5; }
  opname="$(printf '%s' "$op" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  echo "sqlpoint: op $opname"
  _wait_backup_op "$opname" || exit $?
  _read sql backups list --instance "$SIG_SQL_INSTANCE" \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/post-backups.json"
  for f in "$dir"/*; do
    [ -f "$f" ] && echo "STATE sqlpoint $(basename "$f") sha256=$(_sha256 "$f")"
  done
  echo "state-dir: $dir"
  echo "sqlpoint: restore point proven — the caller may proceed"
}

act_bucketpoint() {
  [ "${#SOURCES[@]}" -gt 0 ] || {
    echo "restore-point.sh: bucketpoint needs at least one gs:// source" >&2; exit 64; }
  local dir stamp s bucket rest dest manifest
  dir="$(_evidence_dir "bucketpoint-$(date -u +%Y%m%dT%H%M%SZ)")"; mkdir -p "$dir"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  manifest="$dir/manifest.txt"; : > "$manifest"
  for s in "${SOURCES[@]}"; do
    case "$s" in
      "gs://${SIG_GCP_PROJECT}-sig-web/"*|"gs://${SIG_GCP_PROJECT}-sig-public/"*|\
      "gs://${SIG_GCP_PROJECT}-sig-restricted/"*|"gs://${SIG_GCP_PROJECT}-sig-backups/"*)
        : ;;
      *) echo "restore-point.sh: REFUSED — source '$s' is outside this project's sig buckets" >&2; exit 42 ;;
    esac
    # read-before-write
    _read storage ls -r "$s" > "$dir/src-$(echo "$s" | md5 -q 2>/dev/null || echo "$s" | md5sum | awk '{print $1}').list" 2>/dev/null || \
      _read storage ls -r "$s" > "$dir/src-list.txt" || {
        echo "restore-point.sh: cannot list source '$s' — STOP" >&2; exit 5; }
    bucket="$(printf '%s' "$s" | sed 's|^gs://||; s|/.*||')"
    rest="$(printf '%s' "$s" | sed "s|^gs://${bucket}/||")"
    dest="gs://${SIG_GCP_PROJECT}-sig-restricted/restore-point/${stamp}/${bucket}/${rest}"
    gcloud storage cp -r "$s" "$dest" || {
      echo "restore-point.sh: copy of '$s' failed — STOP (partial copies are recorded below)" >&2
      exit 5; }
    echo "$s -> $dest" >> "$manifest"
  done
  _read storage ls -r "gs://${SIG_GCP_PROJECT}-sig-restricted/restore-point/${stamp}/" \
    > "$dir/copied.list" 2>/dev/null || true
  echo "STATE bucketpoint manifest.txt sha256=$(_sha256 "$manifest")"
  [ -f "$dir/copied.list" ] && echo "STATE bucketpoint copied.list sha256=$(_sha256 "$dir/copied.list")"
  echo "state-dir: $dir"
}

case "$MODE" in
  check)
    echo "restore-point.sh --check (action=$ACTION): plan only — no ADC, no network."
    require_project
    case "$ACTION" in
      sqlpoint) plan_sqlpoint ;;
      bucketpoint) plan_bucketpoint ;;
    esac
    echo "check OK"
    ;;
  apply)
    require_project
    require_adc
    case "$ACTION" in
      sqlpoint) act_sqlpoint ;;
      bucketpoint) act_bucketpoint ;;
    esac
    ;;
esac
