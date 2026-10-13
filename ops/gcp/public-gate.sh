#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/public-gate.sh — P34.21b leg L1: remove anonymous read/list on the
# sig-public bucket's 2026-09-27 published tree (the prefixes the live site
# fetches excluded), plus ONE tombstone note object (SIG-OPS-004 — no object is
# ever deleted; the access change is IAM, reversible by the saved policy).
#
# Authority: NEVER pre-authorised (OM-20). The apply requires the operator's
# verbatim A-0.2 go recorded in GATE DECISIONS (the ticket's "wait for P34.21"
# answer) exported as SIG_PUBLIC_GATE_GO — the recorded words are echoed into
# the apply's evidence record, never fabricated here.
#
# Mutation, pre-state and rollback (contract § Production mutations):
#   pre-state: `gcloud storage buckets get-iam-policy` JSON + a read-only
#              object listing + `describe` (the access mode + live:P34.3
#              versioning read) — saved under the evidence dir with sha256
#   mutation:  one `set-iam-policy` with the computed policy (the unconditional
#              anonymous bindings split into prefix/exact-object conditioned
#              `roles/storage.legacyObjectReader` bindings — get-only; a list
#              call's resource is the bucket itself so conditions cannot keep
#              anonymous LIST on a subset: anonymous list is removed wholesale)
#              + one `gcloud storage cp` of the tombstone note object
#   rollback:  `set-iam-policy` with the saved policy JSON (printed beside the
#              plan and recorded); the tombstone is additive — removing it is a
#              separate operator call, never this script's
#
# Usage:
#   ops/gcp/public-gate.sh [--check|--dry-run] [ACTION]     # plan only (default)
#   ops/gcp/public-gate.sh ACTION ...                       # same — bare action = plan
#   ops/gcp/public-gate.sh --verify [--from-state DIR] [--no-probe]
#   ops/gcp/public-gate.sh --apply apply --prestate DIR [--tombstone-id TB-01]
#
# ACTIONs:
#   prestate  (apply)  read-only capture: describe + get-iam-policy + the full
#                      object listing into the evidence dir, sha256 each
#   list      (check)  prefix summary of a saved listing (--listing FILE or the
#                      latest prestate dir): object count per top-level prefix
#   prefixes  (check)  derive the excluded fetch targets: the ops/cadence.toml
#                      sig-public probe URLs + --fetch-targets FILE (the deployed
#                      build's fetch targets, one URL/path per line) + --exclude
#                      extras + the tombstone prefix — written to exclusions.txt
#                      with per-line # reason= annotations
#   plan      (check)  the exact IAM diff (from a saved iam JSON, --prestate DIR
#                      required) + the tombstone object + the rollback line —
#                      nothing touches gcloud
#   apply     (apply)  the gated leg: window + live:P34.3 + verbatim go +
#                      sha256-verified pre-state → set-iam-policy + tombstone cp
#                      + post-checks (excluded object 200, a non-excluded object
#                      403/404, the tombstone 200 — all anonymous)
#   verify    (verify) read-only: the live (or --from-state) policy carries no
#                      unconditional anonymous binding and every excluded
#                      target is conditioned-in; --no-probe skips the anonymous
#                      fetches
#
# Env:
#   SIG_GCP_PROJECT              required for apply/live-verify (lib.sh)
#   SIG_PUBLIC_GATE_EVIDENCE_DIR where captures land
#                                (default <repo>/docs/build/logs/public-gate — gitignored)
#   SIG_PUBLIC_GATE_GO           the verbatim A-0.2 go text — REQUIRED for
#                                --apply; echoed into the apply evidence record
#   SIG_PUBLIC_GATE_FETCH_TARGETS deployed-build fetch targets file (one URL or
#                                gs://-style path per line; scanned for
#                                sig-public object names)
#   SIG_PUBLIC_GATE_EXCLUDE      extra exclusions, one per line (a file) or a
#                                comma list (a value) — deliberate keeps
#   SIG_PUBLIC_GATE_TOMBSTONE    tombstone object name (default
#                                tombstones/2026-09-27-tree.txt)
#   SIG_PUBLIC_GATE_NOW          ISO-8601 UTC override for the window guard only
#                                (test seam; the real clock is echoed beside it)
#
# Never: `rm`, `mv`, `objects delete`, `rsync --delete*` — SIG-OPS-004 means no
# release byte is deleted by this leg; the tombstone and the IAM binding are the
# ONLY writes.

set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
. "${_here}/config.sh"
# shellcheck source=lib.sh
. "${_here}/lib.sh"

_repo="$(cd "${_here}/../.." && pwd)"

_usage() {
  sed -n '/^# Usage:/,/^set -euo pipefail/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'
  exit "${1:-64}"
}

# ---- args -------------------------------------------------------------------

MODE="check"
ACTION=""
FROM_STATE=""
PRESTATE_DIR=""
LISTING_FILE=""
FETCH_TARGETS=""
TOMBSTONE_ID=""
NO_PROBE=""
declare -a EXTRA_EXCLUDES=()

case "${1:-}" in
  --apply)  MODE="apply"; shift ;;
  --verify) MODE="verify"; shift ;;
  --check|--dry-run) MODE="check"; shift ;;
  -h|--help) _usage 0 ;;
  prestate|list|prefixes|plan|apply|verify) : ;;
  "") : ;;
  *) echo "public-gate.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --prestate)
      [ $# -ge 2 ] || { echo "public-gate.sh: --prestate needs a directory" >&2; exit 64; }
      PRESTATE_DIR="$2"; shift 2 ;;
    --prestate=*) PRESTATE_DIR="${1#--prestate=}"; shift ;;
    --listing)
      [ $# -ge 2 ] || { echo "public-gate.sh: --listing needs a file" >&2; exit 64; }
      LISTING_FILE="$2"; shift 2 ;;
    --listing=*) LISTING_FILE="${1#--listing=}"; shift ;;
    --fetch-targets)
      [ $# -ge 2 ] || { echo "public-gate.sh: --fetch-targets needs a file" >&2; exit 64; }
      FETCH_TARGETS="$2"; shift 2 ;;
    --fetch-targets=*) FETCH_TARGETS="${1#--fetch-targets=}"; shift ;;
    --exclude)
      [ $# -ge 2 ] || { echo "public-gate.sh: --exclude needs a value" >&2; exit 64; }
      EXTRA_EXCLUDES+=("$2"); shift 2 ;;
    --exclude=*) EXTRA_EXCLUDES+=("${1#--exclude=}"); shift ;;
    --tombstone-id)
      [ $# -ge 2 ] || { echo "public-gate.sh: --tombstone-id needs a batch row id" >&2; exit 64; }
      TOMBSTONE_ID="$2"; shift 2 ;;
    --tombstone-id=*) TOMBSTONE_ID="${1#--tombstone-id=}"; shift ;;
    --from-state)
      [ $# -ge 2 ] || { echo "public-gate.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    --no-probe) NO_PROBE=1; shift ;;
    prestate|list|prefixes|plan|apply|verify)
      [ -z "$ACTION" ] || { echo "public-gate.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    *) echo "public-gate.sh: unknown argument '$1'" >&2; _usage 64 ;;
  esac
done

# `--verify` as the leading mode flag maps onto ACTION=verify.
if [ "$MODE" = "verify" ] && [ -z "$ACTION" ]; then ACTION="verify"; fi
# Bare `--check` (no ACTION) is the dry-run apply: the full gate table + the
# plan shape, green without ADC or a saved pre-state.
[ -n "$ACTION" ] || ACTION="apply"
export SIG_GCP_MODE="$MODE"

# ---- constants --------------------------------------------------------------

EVIDENCE_ROOT="${SIG_PUBLIC_GATE_EVIDENCE_DIR:-${_repo}/docs/build/logs/public-gate}"
RELEASE_TAG="2026-09-27"
TOMBSTONE_NAME="${SIG_PUBLIC_GATE_TOMBSTONE:-tombstones/${RELEASE_TAG}-tree.txt}"

#: The notice-allowance default (N-6, B-2 — sha-pinned, ships without a batch
#: row): a copy-batch row supersedes it via --tombstone-id (status must read
#: `confirmed` in the batch — the verbatim confirmation, never agent-typed).
N6_TEXT="This page has been removed while a correction is made."

# Anonymous principal spellings a bucket policy may carry.
ANON_MEMBERS="allUsers allAuthenticatedUsers"

# IAM roles that grant object bytes or listings to the anonymous principal —
# the only ones the transform rewrites. Anything else anonymous is reported
# loudly, never silently preserved.
ANON_OBJECT_ROLES="roles/storage.objectViewer roles/storage.legacyObjectReader roles/storage.legacyBucketReader"
ANON_LIST_ROLES="roles/storage.objectViewer roles/storage.legacyBucketReader roles/storage.legacyBucketAndObjectReader"

_derive_names() {
  # config.sh derived the bucket names at source time; recompute once the
  # project id is final (check mode substitutes a placeholder).
  export SIG_BUCKET_PUBLIC="${SIG_GCP_PROJECT}-sig-public"
}

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_iso_now() {
  # Test seam: SIG_PUBLIC_GATE_NOW pins the guard's clock; the real `date -u`
  # is always echoed beside it.
  if [ -n "${SIG_PUBLIC_GATE_NOW:-}" ]; then printf '%s\n' "$SIG_PUBLIC_GATE_NOW";
  else date -u +%Y-%m-%dT%H:%M:%SZ; fi
}

_evidence_dir() {  # $1 = phase tag
  printf '%s/%s-%s' "$EVIDENCE_ROOT" "$1" "$(date -u +%Y%m%dT%H%M%SZ)"
}

# ---- window guard -------------------------------------------------------------
# PUB: bucket-IAM legs never run inside the daily 03:00-10:00Z band; AR-3 does
# not apply (an IAM change is not a hosted DB write — contract § Live window).

_in_daily_band() {
  local hh
  hh="$(printf '%s' "$1" | sed 's/.*T//; s/:.*//')"
  [ "$hh" -ge 3 ] && [ "$hh" -lt 10 ]
}

assert_window() {
  local now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=bucket-iam"
  if _in_daily_band "$now"; then
    echo "public-gate.sh: REFUSED — inside the daily 03:00-10:00Z band ($now)" >&2
    echo "public-gate.sh: re-run when the window is open:" >&2
    echo "  implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true" >&2
    exit 42
  fi
  echo "window-guard: OK"
}

# ---- read helper --------------------------------------------------------------
# The ONLY path non-apply modes may take to gcloud. Fail-closed verb allowlist.

_read() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      patch|update|create|delete|remove*|add*|set*|rsync|cp|mv|rm|import|export|restore)
        echo "public-gate.sh: _read refuses mutating verb '$arg'" >&2; exit 65 ;;
    esac
  done
  gcloud "$@"
}

# ---- the IAM transform (embedded python — also the offline plan engine) -------
# $1 = saved policy JSON; $2 = exclusions file (one object name or trailing-/
# prefix per line); $3 = bucket name; stdout = the transformed policy JSON.

_transform_policy() {
  python3 - "$1" "$2" "$3" <<'PY'
import json, sys

policy_path, exclusions_path, bucket = sys.argv[1], sys.argv[2], sys.argv[3]
policy = json.loads(open(policy_path, encoding="utf-8").read())
exclusions = []
for line in open(exclusions_path, encoding="utf-8"):
    line = line.split("#", 1)[0].strip()
    if line:
        exclusions.append(line)

ANON = {"allUsers", "allAuthenticatedUsers"}
OBJECT_ROLES = {
    "roles/storage.objectViewer",
    "roles/storage.legacyObjectReader",
    "roles/storage.legacyBucketReader",
}
base = f"projects/_/buckets/{bucket}/objects"

bindings_out = []
removed = []
for b in policy.get("bindings", []):
    role = b.get("role", "")
    members = [m for m in b.get("members", []) if m not in ANON]
    anon_here = [m for m in b.get("members", []) if m in ANON]
    if anon_here and role in OBJECT_ROLES:
        removed.append((role, sorted(anon_here)))
        if members:
            bindings_out.append({**b, "members": sorted(members)})
        continue
    # anonymous on a non-object role: preserved verbatim + warned by the caller
    bindings_out.append(b)

conds = []
for x in sorted(set(exclusions)):
    x = x.lstrip("/")
    if x.endswith("/"):
        conds.append(f'resource.name.startsWith("{base}/{x}")')
    else:
        conds.append(f'resource.name == "{base}/{x}"')
expr = " || ".join(conds) if conds else 'false'

anon_members = sorted({m for r, ms in removed for m in ms})
keep = [b for b in bindings_out
        if b.get("role") == "roles/storage.legacyObjectReader"
        and (b.get("condition") or {}).get("title") == "p34-21b-live-prefixes"]
bindings_out = [b for b in bindings_out if b not in keep]
if anon_members and conds:
    bindings_out.append({
        "role": "roles/storage.legacyObjectReader",
        "members": anon_members,
        "condition": {
            "title": "p34-21b-live-prefixes",
            "description": (
                "P34.21b L1: anonymous GET survives only on the fetch targets "
                "the live site still needs; the rest of the 09-27 tree loses "
                "anonymous read/list (E2-12 misattribution; rollback = the "
                "saved policy)."
            ),
            "expression": expr,
        },
    })

out = dict(policy)
out["bindings"] = bindings_out
print(json.dumps(out, indent=2, sort_keys=True))
PY
}

# A readable one-line diff of the anonymous-grant change for PLAN/evidence.
_policy_diff_lines() {
  python3 - "$1" "$2" <<'PY'
import json, sys
before = json.loads(open(sys.argv[1], encoding="utf-8").read())
after = json.loads(open(sys.argv[2], encoding="utf-8").read())
ANON = {"allUsers", "allAuthenticatedUsers"}
def anon(b):
    return sorted((x.get("role"), sorted(set(x.get("members", [])) & ANON),
                   (x.get("condition") or {}).get("expression"))
                  for x in b.get("bindings", [])
                  if set(x.get("members", [])) & ANON)
for role, members, expr in anon(before):
    print(f"  BEFORE {role}: {', '.join(members)} (unconditional)")
for role, members, expr in anon(after):
    print(f"  AFTER  {role}: {', '.join(members)}")
    if expr:
        for part in expr.split(" || "):
            print(f"         keep  {part}")
PY
}

_anon_binding_free() {  # $1 = policy JSON file → 0 when no UNCONDITIONAL anon object binding
  python3 - "$1" <<'PY'
import json, sys
policy = json.loads(open(sys.argv[1], encoding="utf-8").read())
ANON = {"allUsers", "allAuthenticatedUsers"}
OBJECT_ROLES = {"roles/storage.objectViewer", "roles/storage.legacyObjectReader",
                "roles/storage.legacyBucketReader"}
bad = [b for b in policy.get("bindings", [])
       if b.get("role") in OBJECT_ROLES
       and set(b.get("members", [])) & ANON
       and not b.get("condition")]
sys.exit(0 if not bad else 1)
PY
}

# ---- exclusions derivation -----------------------------------------------------

_derive_exclusions() {  # writes exclusion lines + # reason= on stdout
  {
    # 1. the committed sig-public probe targets (the 6-hourly sweep's fetches).
    python3 - "${_repo}/ops/cadence.toml" <<'PY'
import re, sys
try:
    import tomllib
except ModuleNotFoundError:  # python < 3.11 — the cadence read degrades empty
    sys.exit(0)
try:
    doc = tomllib.load(open(sys.argv[1], "rb"))
except OSError:
    sys.exit(0)
pat = re.compile(r"sig-public/(.+)$")
for t in doc.get("probes", {}).get("targets", []):
    url = str(t.get("url", ""))
    m = pat.search(url)
    if m:
        obj = m.group(1).split("?", 1)[0]
        print(f"{obj}  # reason=cadence sig-public probe target ({t.get('name')})")
PY
    # 2. the deployed build's fetch targets file (operator/agent-captured).
    if [ -n "$FETCH_TARGETS" ] && [ -f "$FETCH_TARGETS" ]; then
      grep -v '^[[:space:]]*#' "$FETCH_TARGETS" | while IFS= read -r line; do
        obj="$(printf '%s' "$line" | sed -n 's|.*sig-public/||p' | sed 's/[?#].*$//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
        [ -n "$obj" ] && printf '%s  # reason=deployed-build fetch target\n' "$obj"
      done
    fi
    if [ -n "${SIG_PUBLIC_GATE_FETCH_TARGETS:-}" ] && [ -f "${SIG_PUBLIC_GATE_FETCH_TARGETS}" ] && [ "${SIG_PUBLIC_GATE_FETCH_TARGETS}" != "$FETCH_TARGETS" ]; then
      grep -v '^[[:space:]]*#' "${SIG_PUBLIC_GATE_FETCH_TARGETS}" | while IFS= read -r line; do
        obj="$(printf '%s' "$line" | sed -n 's|.*sig-public/||p' | sed 's/[?#].*$//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
        [ -n "$obj" ] && printf '%s  # reason=deployed-build fetch target (env file)\n' "$obj"
      done
    fi
    # 3. deliberate extras: --exclude values + SIG_PUBLIC_GATE_EXCLUDE.
    for x in "${EXTRA_EXCLUDES[@]+"${EXTRA_EXCLUDES[@]}"}"; do
      printf '%s  # reason=operator --exclude\n' "$x"
    done
    if [ -n "${SIG_PUBLIC_GATE_EXCLUDE:-}" ]; then
      if [ -f "${SIG_PUBLIC_GATE_EXCLUDE}" ]; then
        while IFS= read -r line; do
          [ -n "$line" ] && printf '%s  # reason=SIG_PUBLIC_GATE_EXCLUDE file\n' "$line"
        done < "${SIG_PUBLIC_GATE_EXCLUDE}"
      else
        printf '%s' "${SIG_PUBLIC_GATE_EXCLUDE}" | tr ',' '\n' | while IFS= read -r line; do
          [ -n "$line" ] && printf '%s  # reason=SIG_PUBLIC_GATE_EXCLUDE\n' "$line"
        done
      fi
    fi
    # 4. the tombstone prefix itself — the note must stay readable.
    printf '%s  # reason=tombstone note object (L1)\n' "tombstones/"
  } | sed 's/[[:space:]]*#/#/' | sort -u | sed 's/#/  #/'
}

_require_exclusions_file() {  # $1 = path; refuse when empty
  [ -s "$1" ] || {
    echo "public-gate.sh: no exclusions derived — refusing to compute a policy "
    echo "   that would strip anonymous access from EVERYTHING. Derive the"
    echo "   fetch targets first (prefixes action / --fetch-targets / --exclude)." >&2
    exit 44; }
}

# ---- tombstone text -------------------------------------------------------------
# --tombstone-id <row>: read the copy-batch row (batch-*.md): its text ships
# only when status=confirmed; anything else is a loud refusal (B-2 — an agent
# never types the sentence it ships).

_tombstone_text() {
  if [ -z "$TOMBSTONE_ID" ]; then printf '%s\n' "$N6_TEXT"; return 0; fi
  local row_status row_text
  row_status="$(awk -F'|' -v id="$TOMBSTONE_ID" '
    $0 ~ /^\|/ { gsub(/^ +| +$/, "", $2); if ($2 == id) { gsub(/^ +| +$/, "", $6); print $6 } }
  ' "${_repo}"/docs/build/reports/copy-batches/batch-*.md | head -1)"
  row_text="$(awk -F'|' -v id="$TOMBSTONE_ID" '
    $0 ~ /^\|/ { gsub(/^ +| +$/, "", $2); if ($2 == id) { gsub(/^ +| +$/, "", $4); print $4 } }
  ' "${_repo}"/docs/build/reports/copy-batches/batch-*.md | head -1)"
  [ -n "$row_text" ] || {
    echo "public-gate.sh: tombstone id '$TOMBSTONE_ID' has no copy-batch row" >&2; exit 45; }
  [ "$row_status" = "confirmed" ] || {
    echo "public-gate.sh: tombstone row '$TOMBSTONE_ID' is '$row_status' — only an"
    echo "   operator-confirmed batch sentence may ship (B-2); default is N-6." >&2; exit 45; }
  printf '%s\n' "$row_text"
}

# ---- state capture (apply-mode read-only leg) -----------------------------------

act_prestate() {
  local dir f
  dir="$(_evidence_dir pre)"; mkdir -p "$dir"
  _read storage buckets describe "gs://${SIG_BUCKET_PUBLIC}" --format=json \
    > "$dir/describe.${SIG_BUCKET_PUBLIC}.json"
  _read storage buckets get-iam-policy "gs://${SIG_BUCKET_PUBLIC}" --format=json \
    > "$dir/iam.${SIG_BUCKET_PUBLIC}.json"
  _read storage ls --recursive "gs://${SIG_BUCKET_PUBLIC}/" \
    > "$dir/listing.${SIG_BUCKET_PUBLIC}.txt"
  for f in "$dir"/*; do
    _sha256 "$f" > "$f.sha256"
    echo "STATE pre $(basename "$f") sha256=$(cat "$f.sha256")"
  done
  echo "state-dir: $dir"
  echo "prestate: commit-worthy summary — run \`list --listing $dir/listing.${SIG_BUCKET_PUBLIC}.txt\`"
}

# ---- offline actions ------------------------------------------------------------

_resolve_listing() {
  if [ -n "$LISTING_FILE" ]; then printf '%s\n' "$LISTING_FILE"; return; fi
  if [ -n "$PRESTATE_DIR" ]; then
    local f; f="$(ls "$PRESTATE_DIR"/listing.*.txt 2>/dev/null | head -1 || true)"
    [ -n "$f" ] && { printf '%s\n' "$f"; return; }
  fi
  local f; f="$(ls -t "$EVIDENCE_ROOT"/*/listing.*.txt 2>/dev/null | head -1 || true)"
  [ -n "$f" ] && printf '%s\n' "$f" || {
    echo "public-gate.sh: no listing found — pass --listing or --prestate, "
    echo "   or run 'public-gate.sh --apply prestate' first." >&2; exit 46; }
}

act_list() {
  local listing
  listing="$(_resolve_listing)"
  echo "listing: $listing"
  sed 's|^gs://[^/]*/||' "$listing" | grep -v '/$' | awk -F/ '
    { p = (NF > 1 ? $1 "/" : "(root)"); count[p]++ }
    END { for (p in count) printf "  %-40s %8d objects\n", p, count[p] }' | sort
  local total
  total="$(grep -cv '/$' "$listing" || true)"
  echo "listing: $total objects total (sha256=$(_sha256 "$listing"))"
}

act_prefixes() {
  local out
  out="${PRESTATE_DIR:+$PRESTATE_DIR/}exclusions.txt"
  [ -n "$PRESTATE_DIR" ] || out="$EVIDENCE_ROOT/exclusions.txt"
  mkdir -p "$(dirname "$out")"
  _derive_exclusions | tee "$out"
  echo "exclusions -> $out"
}

act_plan() {
  [ -n "$PRESTATE_DIR" ] || {
    echo "public-gate.sh: plan needs --prestate DIR (the saved iam JSON);" >&2
    echo "   run 'public-gate.sh --apply prestate' first." >&2; exit 46; }
  local iam describe listing excl new
  iam="$(ls "$PRESTATE_DIR"/iam.*.json 2>/dev/null | head -1 || true)"
  describe="$(ls "$PRESTATE_DIR"/describe.*.json 2>/dev/null | head -1 || true)"
  listing="$(ls "$PRESTATE_DIR"/listing.*.txt 2>/dev/null | head -1 || true)"
  excl="$PRESTATE_DIR/exclusions.txt"
  [ -f "$excl" ] || { _derive_exclusions > "$excl"; }
  _require_exclusions_file "$excl"
  [ -n "$iam" ] || { echo "public-gate.sh: $PRESTATE_DIR has no iam.*.json" >&2; exit 46; }
  new="$PRESTATE_DIR/policy.new.json"
  _transform_policy "$iam" "$excl" "$SIG_BUCKET_PUBLIC" > "$new"
  echo "computed policy -> $new (sha256=$(_sha256 "$new"))"
  _sha256 "$new" > "$new.sha256"
  echo "IAM diff (anonymous grants):"
  _policy_diff_lines "$iam" "$new"
  if [ -n "$describe" ]; then
    python3 - "$describe" <<'PY'
import json, sys
d = json.loads(open(sys.argv[1], encoding="utf-8").read())
uba = ((d.get("iamConfiguration") or {})
       .get("uniformBucketLevelAccess") or {}).get("enabled")
ver = (d.get("versioning") or {}).get("enabled")
pap = (d.get("iamConfiguration") or {}).get("publicAccessPrevention")
print(f"  access mode: uniformBucketLevelAccess={uba} publicAccessPrevention={pap} versioning={ver}")
if uba is not True:
    print("  RE-CONFIRM: the bucket is NOT uniform-access — anonymous access may")
    print("  also ride object ACLs the IAM policy does not show; the leg-runner")
    print("  must verify the access mode before --apply (contract re-confirm).")
if ver is not True:
    print("  WARNING: versioning is OFF — live:P34.3 is not met; --apply refuses.")
PY
  fi
  echo "tombstone: gs://${SIG_BUCKET_PUBLIC}/${TOMBSTONE_NAME}"
  echo "  text: $(_tombstone_text)"
  echo "rollback: gcloud storage buckets set-iam-policy 'gs://${SIG_BUCKET_PUBLIC}' '$iam'"
}

act_verify() {
  local iam_dir
  if [ -n "$FROM_STATE" ]; then
    iam_dir="$FROM_STATE"
  else
    iam_dir="$(_evidence_dir verify)"; mkdir -p "$iam_dir"
    _read storage buckets get-iam-policy "gs://${SIG_BUCKET_PUBLIC}" --format=json \
      > "$iam_dir/iam.${SIG_BUCKET_PUBLIC}.json"
  fi
  local iam drift=0
  iam="$(ls "$iam_dir"/iam.*.json 2>/dev/null | head -1 || true)"
  [ -n "$iam" ] || { echo "public-gate.sh: no iam JSON under $iam_dir" >&2; exit 46; }
  if _anon_binding_free "$iam"; then
    echo "verify: no unconditional anonymous object binding — OK"
  else
    echo "verify: DRIFT — an unconditional anonymous object binding survives" >&2; drift=1
  fi
  local excl
  excl="$(ls "$iam_dir"/exclusions.txt 2>/dev/null || true)"
  if [ -z "$excl" ] && [ -n "$PRESTATE_DIR" ]; then excl="$PRESTATE_DIR/exclusions.txt"; fi
  if [ -n "$excl" ] && [ -f "$excl" ]; then
    python3 - "$iam" "$excl" "$SIG_BUCKET_PUBLIC" <<'PY' || drift=1
import json, sys
policy = json.loads(open(sys.argv[1], encoding="utf-8").read())
excl = [l.split("#", 1)[0].strip() for l in open(sys.argv[2], encoding="utf-8")]
excl = [x for x in excl if x]
bucket = sys.argv[3]
base = f"projects/_/buckets/{bucket}/objects"
exprs = " ".join(
    (b.get("condition") or {}).get("expression", "")
    for b in policy.get("bindings", [])
    if set(b.get("members", [])) & {"allUsers", "allAuthenticatedUsers"})
missing = []
for x in excl:
    x = x.lstrip("/")
    frag = f'{base}/{x}'
    if frag not in exprs:
        missing.append(x)
if missing:
    print(f"verify: DRIFT — exclusions not conditioned-in: {missing}", file=sys.stderr)
    sys.exit(1)
print(f"verify: all {len(excl)} exclusion(s) conditioned-in — OK")
PY
  else
    echo "verify: no exclusions.txt recorded — the conditioned-prefix check skipped" >&2
  fi
  if [ -z "$NO_PROBE" ] && [ -z "$FROM_STATE" ]; then
    local obj code
    # anonymous probes: one excluded object (200) + the tombstone (200) + one
    # non-excluded object from the saved listing (403/404).
    local excl_objs=""
    if [ -n "$excl" ] && [ -f "$excl" ]; then
      excl_objs="$(grep -v '/$' "$excl" | sed 's/[[:space:]]*#.*//' | head -2 || true)"
    fi
    for obj in $excl_objs "$TOMBSTONE_NAME"; do
      [ -n "$obj" ] || continue
      code="$(curl -s -o /dev/null -w '%{http_code}' \
        "https://storage.googleapis.com/${SIG_BUCKET_PUBLIC}/${obj}" || true)"
      echo "probe: GET $obj -> $code (want 200)"
      [ "$code" = "200" ] || drift=1
    done
    local listing sample
    listing="$(ls "$iam_dir"/listing.*.txt 2>/dev/null | head -1 || true)"
    if [ -z "$listing" ] && [ -n "$PRESTATE_DIR" ]; then
      listing="$(ls "$PRESTATE_DIR"/listing.*.txt 2>/dev/null | head -1 || true)"
    fi
    if [ -z "$listing" ]; then listing="${LISTING_FILE:-}"; fi
    if [ -n "$listing" ] && [ -f "$listing" ]; then
      sample="$(python3 - "$listing" "$excl" <<'PY'
import sys
excl = set()
try:
    for l in open(sys.argv[2], encoding="utf-8"):
        x = l.split("#", 1)[0].strip().lstrip("/")
        if x: excl.add(x)
except OSError:
    pass
for line in open(sys.argv[1], encoding="utf-8"):
    name = line.strip().split("/", 3)[-1] if line.startswith("gs://") else line.strip()
    if not name or name.endswith("/"):
        continue
    if any(name == x or (x.endswith("/") and name.startswith(x)) for x in excl):
        continue
    print(name)
    break
PY
)"
      if [ -n "$sample" ]; then
        code="$(curl -s -o /dev/null -w '%{http_code}' \
          "https://storage.googleapis.com/${SIG_BUCKET_PUBLIC}/${sample}" || true)"
        case "$code" in
          403|404) echo "probe: GET $sample -> $code (want 403/404)" ;;
          *) echo "probe: GET $sample -> $code — expected 403/404" >&2; drift=1 ;;
        esac
      fi
    fi
  fi
  if [ "$drift" = "0" ]; then echo "verify: OK"; return 0; fi
  echo "verify: DRIFT" >&2
  return 1
}

# ---- the gated apply ------------------------------------------------------------

act_apply() {
  if [ "$SIG_GCP_MODE" != "apply" ]; then
    # Check-mode apply: the exact same computation against a saved pre-state —
    # every gate named, every command a PLAN line, nothing applied.
    echo "dry-run apply: every gate + command, nothing touched"
    echo "PLAN: gate SIG_PUBLIC_GATE_GO — $([ -n "${SIG_PUBLIC_GATE_GO:-}" ] && echo "set" || echo "UNSET (verbatim A-0.2 go required)")"
    echo "PLAN: gate window — $(_in_daily_band "$(_iso_now)" && echo "INSIDE 03:00-10:00Z (would refuse)" || echo "open ($(_iso_now))")"
    if [ -z "$PRESTATE_DIR" ] || [ ! -d "$PRESTATE_DIR" ]; then
      echo "PLAN: gate --prestate DIR — MISSING (saved describe/iam/listing required;"
      echo "      run 'public-gate.sh --apply prestate' under ADC first)"
      echo "PLAN: gcloud storage buckets get-iam-policy gs://${SIG_BUCKET_PUBLIC} (via prestate)"
      echo "PLAN: gcloud storage buckets set-iam-policy gs://${SIG_BUCKET_PUBLIC} <computed>"
      echo "PLAN: gcloud storage cp <tombstone> gs://${SIG_BUCKET_PUBLIC}/${TOMBSTONE_NAME}"
      echo "PLAN: anonymous post-checks (excluded 200 / non-excluded 403/404 / tombstone 200)"
      echo "PLAN: rollback = set-iam-policy with the saved iam JSON (never a delete)"
      return 0
    fi
    act_plan
    return 0
  fi
  # 1. the verbatim go (OM-20: silence is never consent — the recorded words).
  [ -n "${SIG_PUBLIC_GATE_GO:-}" ] || {
    echo "public-gate.sh: REFUSED — SIG_PUBLIC_GATE_GO is unset." >&2
    echo "   The leg needs the operator's verbatim A-0.2 go recorded in GATE" >&2
    echo "   DECISIONS exported here; silence is never consent (OM-18/20)." >&2
    exit 43; }
  # 2. the PUB window.
  assert_window
  # 3. the saved pre-state — refuse without it (the apply reverts to it).
  [ -n "$PRESTATE_DIR" ] && [ -d "$PRESTATE_DIR" ] || {
    echo "public-gate.sh: REFUSED — --apply needs --prestate DIR holding the" >&2
    echo "   saved describe/iam/listing (run '--apply prestate' first)." >&2
    exit 44; }
  local iam describe listing excl f
  iam="$(ls "$PRESTATE_DIR"/iam.*.json 2>/dev/null | head -1 || true)"
  describe="$(ls "$PRESTATE_DIR"/describe.*.json 2>/dev/null | head -1 || true)"
  listing="$(ls "$PRESTATE_DIR"/listing.*.txt 2>/dev/null | head -1 || true)"
  for f in "$iam" "$describe" "$listing"; do
    [ -n "$f" ] && [ -f "$f" ] || {
      echo "public-gate.sh: REFUSED — pre-state file missing under $PRESTATE_DIR" >&2; exit 44; }
    [ -f "$f.sha256" ] || {
      echo "public-gate.sh: REFUSED — $f has no recorded sha256 sidecar" >&2; exit 44; }
    [ "$(_sha256 "$f")" = "$(cat "$f.sha256")" ] || {
      echo "public-gate.sh: REFUSED — $f sha256 mismatch (the saved pre-state" >&2
      echo "   must be the untampered capture — recapture with '--apply prestate')" >&2
      exit 44; }
  done
  # 4. live:P34.3 — versioning on (the restore point the contract requires).
  python3 - "$describe" <<'PY' || {
import json, sys
d = json.loads(open(sys.argv[1], encoding="utf-8").read())
ver = (d.get("versioning") or {}).get("enabled")
uba = ((d.get("iamConfiguration") or {}).get("uniformBucketLevelAccess") or {}).get("enabled")
sys.exit(0 if (ver is True and uba is True) else 1)
PY
    echo "public-gate.sh: REFUSED — the saved describe does not prove" >&2
    echo "   versioning+uniform access on (live:P34.3 / the re-confirm); recheck." >&2
    exit 44; }
  echo "live:P34.3: versioning + uniform bucket-level access on (saved describe)"
  # 5. derive + apply the policy.
  excl="$PRESTATE_DIR/exclusions.txt"
  [ -f "$excl" ] || { _derive_exclusions > "$excl"; }
  _require_exclusions_file "$excl"
  local new="$PRESTATE_DIR/policy.new.json"
  _transform_policy "$iam" "$excl" "$SIG_BUCKET_PUBLIC" > "$new"
  _sha256 "$new" > "$new.sha256"
  echo "go: ${SIG_PUBLIC_GATE_GO}"
  echo "computed policy -> $new (sha256=$(cat "$new.sha256"))"
  _policy_diff_lines "$iam" "$new"
  if _anon_binding_free "$iam"; then
    echo "apply: SKIP set-iam-policy — the saved policy already carries no"
    echo "       unconditional anonymous object binding (the leg is idempotent)"
  else
    run gcloud storage buckets set-iam-policy "gs://${SIG_BUCKET_PUBLIC}" "$new"
    echo "rollback: gcloud storage buckets set-iam-policy 'gs://${SIG_BUCKET_PUBLIC}' '$iam'"
  fi
  # 6. the tombstone note object (additive — never a delete).
  local tmp
  tmp="$(mktemp)"
  _tombstone_text > "$tmp"
  run gcloud storage cp --content-type=text/plain "$tmp" \
    "gs://${SIG_BUCKET_PUBLIC}/${TOMBSTONE_NAME}"
  rm -f "$tmp"
  # 7. post-checks — the apply records its own probe lines (the leg's AC).
  echo "post-checks: re-running --verify in-place"
  act_verify || {
    echo "public-gate.sh: post-checks FAILED — roll back now:" >&2
    echo "  gcloud storage buckets set-iam-policy 'gs://${SIG_BUCKET_PUBLIC}' '$iam'" >&2
    exit 6; }
}

# ---- dispatch -------------------------------------------------------------------

require_project
_derive_names

banner "sig-public 09-27 anonymous-access gate (P34.21b leg L1)"

case "$ACTION" in
  prestate)  require_adc; act_prestate ;;
  list)      act_list ;;
  prefixes)  act_prefixes ;;
  plan)      act_plan ;;
  apply)     require_adc; act_apply ;;
  verify)    act_verify ;;
  *) echo "public-gate.sh: unknown action '$ACTION'" >&2; exit 64 ;;
esac

_log "public-gate ${ACTION}: ${MODE} OK"
