#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# sig-web-restore.sh — the P37.61a named scripted rollback (RULING H-1 /
# live leg P37.61a-L2, `prepared, conditional on rollback`): restore the
# sig-web bucket to a captured byte-level pre-copy.
#
# Bucket versioning is OFF on -sig-web (live:P34.3, D-P34.3-1 OPEN) — object
# generations cannot restore the site, so the rollback is a bounded re-sync
# from the committed pre-copy prefix:
#
#   UPLOADS  every object in the pre-copy EXCEPT lane-exclusive objects the
#            live listing also shows (the put-skip — a lane object freshened
#            after the capture is never rolled back over);
#   DELETES  only objects that are (i) ABSENT from the pre-copy AND
#            (ii) outside the protected release namespaces
#            (`r/`, `releases/`, `entity/`, `conf/` + `compat_index.json` /
#            `release.json`) AND (iii) outside the lane keep-set —
#            derived from the LIVE listing, never asserted
#            (`status/{state,lane}.json`, `status/sources/**`,
#            `status/archive/**`, `watch/{state,lane,watch}.json`,
#            `watch/archive/**`; shared namespaces like `watch/index.html`
#            are NOT lane objects).
#
# Bounded deletion ONLY — never `rsync --delete*`, `mv`, or an unscoped `rm`:
# every planned delete is a single `gcloud storage objects delete` on an
# enumerated name, and `--dry-run` prints the full plan against the LIVE
# bucket state before anything is touched.
#
# Usage:
#   sig-web-restore.sh <pre-copy-prefix> [--dry-run|--apply]
#
# <pre-copy-prefix> is a gs:// URI whose LAST path segment is the source
# bucket's own name, e.g.
#   gs://<project>-sig-restricted/rollback/sig-web-pre-P37.61a-2026-11-16/<project>-sig-web/
# The target bucket is that last segment. Default mode is --dry-run.
# Post-restore verification is the ticket's AC1 GET checks + artifact
# identity — this script performs the sync only.

set -euo pipefail

mode="dry-run"
prefix=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) mode="dry-run" ;;
    --apply) mode="apply" ;;
    --help|-h)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    gs://*) prefix="${arg%/}/" ;;
    *)
      echo "sig-web-restore: unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

if [ -z "$prefix" ]; then
  echo "sig-web-restore: a pre-copy gs:// prefix is required" >&2
  exit 2
fi

# The target bucket is the prefix's last path segment (the pre-copy carries
# the source bucket's own name).
bucket="$(basename "${prefix%/}")"
target="gs://${bucket}/"

case "$bucket" in
  *-sig-web) ;;
  *)
    echo "sig-web-restore: refusing — prefix last segment '${bucket}' is not a" >&2
    echo "  *-sig-web bucket name; the restore target must be a site bucket." >&2
    exit 2
    ;;
esac

if [ "$mode" = "apply" ] && ! gcloud storage ls "$prefix" >/dev/null 2>&1; then
  echo "sig-web-restore: cannot read pre-copy prefix ${prefix} — refusing." >&2
  exit 3
fi

is_protected() {
  case "$1" in
    r/*|releases/*|entity/*|conf/*|compat_index.json|release.json) return 0 ;;
  esac
  return 1
}

is_lane() {
  case "$1" in
    status/state.json|status/lane.json|status/sources/*|status/archive/*) return 0 ;;
    watch/state.json|watch/lane.json|watch/watch.json|watch/archive/*) return 0 ;;
  esac
  return 1
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# The pre-copy object set (names relative to the bucket root).
gcloud storage ls --recursive "${prefix}**" \
  | grep -v ':$' \
  | sed "s|^${prefix}||" \
  | grep -v '^$' \
  | sort > "$tmp/precopy.txt"

if [ ! -s "$tmp/precopy.txt" ]; then
  echo "sig-web-restore: pre-copy prefix ${prefix} lists ZERO objects — refusing" >&2
  echo "  (an empty restore would delete everything; the bound is the point)." >&2
  exit 3
fi

# The live object set.
gcloud storage ls --recursive "${target}**" \
  | grep -v ':$' \
  | sed "s|^${target}||" \
  | grep -v '^$' \
  | sort > "$tmp/live.txt"

# planned deletes = live − precopy − protected − lane.
comm -13 "$tmp/precopy.txt" "$tmp/live.txt" > "$tmp/absent_from_precopy.txt"
: > "$tmp/deletes.txt"
: > "$tmp/kept_protected.txt"
: > "$tmp/kept_lane.txt"
while IFS= read -r name; do
  if is_protected "$name"; then
    echo "$name" >> "$tmp/kept_protected.txt"
  elif is_lane "$name"; then
    echo "$name" >> "$tmp/kept_lane.txt"
  else
    echo "$name" >> "$tmp/deletes.txt"
  fi
done < "$tmp/absent_from_precopy.txt"

# planned uploads = precopy − lane objects the live listing also shows.
: > "$tmp/uploads.txt"
: > "$tmp/skipped_puts.txt"
while IFS= read -r name; do
  if is_lane "$name" && grep -qxF "$name" "$tmp/live.txt"; then
    echo "$name" >> "$tmp/skipped_puts.txt"
  else
    echo "$name" >> "$tmp/uploads.txt"
  fi
done < "$tmp/precopy.txt"

n_uploads=$(wc -l < "$tmp/uploads.txt" | tr -d ' ')
n_deletes=$(wc -l < "$tmp/deletes.txt" | tr -d ' ')
n_put_skips=$(wc -l < "$tmp/skipped_puts.txt" | tr -d ' ')
n_prot=$(wc -l < "$tmp/kept_protected.txt" | tr -d ' ')
n_lane=$(wc -l < "$tmp/kept_lane.txt" | tr -d ' ')

echo "sig-web-restore $(printf '%s' "$mode" | tr '[:lower:]' '[:upper:]'): ${target} <- ${prefix}"
echo "  uploads:            ${n_uploads}"
echo "  deletes:            ${n_deletes} (bounded: absent from pre-copy, unprotected, non-lane)"
echo "  protected kept:     ${n_prot}"
echo "  lane kept:          ${n_lane} deletes-skipped, ${n_put_skips} put-skipped"
echo "  planned deletes:"
sed 's/^/    DELETE /' "$tmp/deletes.txt" || true
echo "  planned put-skips (lane):"
sed 's/^/    SKIP-PUT /' "$tmp/skipped_puts.txt" || true

if [ "$mode" != "apply" ]; then
  echo "dry-run: nothing written; re-run with --apply to restore." >&2
  exit 0
fi

# --- apply: uploads first (additive), then the bounded deletes -------------
fails=0
while IFS= read -r name; do
  echo "  PUT ${name}"
  gcloud storage cp "${prefix}${name}" "${target}${name}" || fails=$((fails+1))
done < "$tmp/uploads.txt"

while IFS= read -r name; do
  # Belt-and-suspenders: never delete a protected or lane object even if the
  # plan file drifted.
  if is_protected "$name" || is_lane "$name"; then
    echo "sig-web-restore: REFUSING unplanned protected/lane delete ${name}" >&2
    exit 4
  fi
  echo "  DELETE ${name}"
  gcloud storage objects delete "${target}${name}" || fails=$((fails+1))
done < "$tmp/deletes.txt"

if [ "$fails" -gt 0 ]; then
  echo "sig-web-restore: ${fails} operation(s) failed — the bucket may be in a" >&2
  echo "  partial state; re-run this script (idempotent by construction)." >&2
  exit 5
fi

echo "sig-web-restore: DONE — ${n_uploads} uploaded, ${n_deletes} deleted," \
     "${n_put_skips} lane put-skips. Post-restore verification = the ticket's" \
     "AC1 GET checks + artifact identity (run separately)."
