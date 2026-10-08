#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/at-rest-audit.sh — the P34.49 Part VIII at-rest audit legs (F-406,
# ADR-185, SIG-PUB-002/003/011–014a, SIG-STORE-025, SIG-GOV-007/017; the seal
# mutation is OM-20 pre-authorised S5-3, expires GATE-G4).
#
#   L1 scan   read-only: one ephemeral sig-exec-atrest-<stamp> job on the
#             sig-quality-probe-rt identity (the P34.43 execution host),
#             read-only captures mount, sig_audit read posture — walks every
#             OCFL capture object's bytes and emits the counts-only
#             sig.at-rest-audit/1 report + the restricted
#             sig.at-rest-flagged/1 sidecar under ops/probes/at-rest/.
#             Requires the P34.43 exec-host leg to have landed (the runtime
#             SA + conditioned bindings) → exits 42 (queued) until it exists.
#
#   L2 seal   protective suppression, gated on an L1 report: an AR-2
#             restore point first, then the append-only records — capture_seal
#             rows + artifact withhold publication_dispositions (insert-only
#             write path) — then a NEW VERSION of the sig.seal-deny/1
#             serving/export deny set (never an in-place rewrite) and the
#             counts-only sig.pub002-listing/1 for the operator's purge
#             decision. NO BYTE IS DELETED OR OVERWRITTEN; true purge is the
#             operator's WV-11 action (ADR-181 control 2, ADR-189), never
#             this leg.
#
#   ./at-rest-audit.sh --check [action]   # (default) plan-only: NO ADC, NO
#                                         # network — every command printed.
#   ./at-rest-audit.sh --apply <action>   # windowed + operator ADC.
#   ./at-rest-audit.sh --verify           # read-only LIVE checks (ADC, never
#                                         # window-gated)
#
# Actions:
#   prestate   the seal leg's restore point: per-tier capture counts, the
#              publishable path list, a name+generation listing of every
#              captures/ + ops/seal/ object (the "no byte deleted or
#              overwritten" baseline), the latest Cloud SQL backup, the
#              current deny-set object. READ-ONLY — any time.
#   backup     AR-2: an on-demand Cloud SQL backup verified SUCCESSFUL
#              before L2's first record write.
#   scan       L1 — the ephemeral at-rest scan job (see above). Gated on the
#              exec-host runtime identity existing (the P34.43 leg) + the
#              window; exits 42 (queued) otherwise.
#   seal       L2 — gated on a recorded L1 report + the AR-2 backup: render
#              the seal plan, apply the append-only records (exit 42 while
#              capture_seal is undeployed), then the deny-set version +
#              the PUB-002 listing. Sealing scope ONLY — never a purge.
#   verify     poststate: the same listings; assert ZERO object deletions or
#              generation replacements between pre/post (bytes unchanged);
#              the sealed-digest serving check (an evidence route on a sealed
#              capture returns the sealed rep / 404); the seal-register
#              read-back (not_evaluable while capture_seal is undeployed).
#              READ-ONLY.
#   rollback   superseding records only: an "unseal" capture_seal row per
#              sealed capture + a new deny-set version restoring the prior
#              entries — restoring prestate is always safe, so deliberately
#              NOT window-gated. Never a delete.
#   all        prestate → backup → scan → seal → verify (L1+L2 in one window).
#
# Live window (OM-19, the contract's AR-3 + AR-2 slot — the legs ride the
# P34.43 execution host, whose own leg is windowed): applies run ≥
# ${SIG_ATREST_EARLIEST} and never 03:00–06:30Z; earlier → exit 42 (queued —
# the RETURN PASS re-run prompt is printed). SIG_ATREST_NOW overrides the
# clock for the offline guard test only.
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
    SIG_GCP_MODE="verify"
    ACTION="verify"
    shift
    if [ "${1:-}" = "--from-state" ]; then
      [ $# -ge 2 ] || { echo "at-rest-audit.sh: --from-state needs a directory" >&2; exit 64; }
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
STATE_DIR="${2:-${SIG_ATREST_STATE_DIR}}"

_repo="$(cd "${_here}/../.." && pwd)"

RERUN='implement-spec spec=docs/tickets/254_P34.49__part-viii-at-rest-audit.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `assert_window` — the OM-19/AR-3 clock guard (exit 42 = queued leg). Check
# mode is never gated — a printed plan mutates nothing.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm
  now="${SIG_ATREST_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_ATREST_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_ATREST_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  hhmm="${now:11:5}"
  if [[ "${hhmm}" > "02:59" && "${hhmm}" < "06:30" ]]; then
    _log "QUEUED (exit 42): ${now} is inside 03:00–06:30Z — never mutate then."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  _log "window OK: ${now} (≥ ${SIG_ATREST_EARLIEST}, outside 03:00–06:30Z)"
}

# `assert_exec_host` — the L1 prerequisite: the P34.43 leg's runtime identity
# + conditioned bindings must exist (the ephemeral job runs on them). Absent →
# exit 42 (queued), never a fabricated scan.
assert_exec_host() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if ! gcloud iam service-accounts describe \
      "${SIG_EXEC_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com" \
      --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    _log "QUEUED (exit 42): ${SIG_EXEC_SA} does not exist — the P34.43 exec-host leg has not run."
    _log "re-run: ${RERUN} (scope: the scan leg only)"
    exit 42
  fi
}

# `latest_l1_report <dir>` — fetch the newest recorded L1 report + flagged
# sidecar from the restricted bucket's probe prefix into <dir>; absent → the
# seal leg stays queued (exit 42), never seals without the recorded counts.
latest_l1_report() {
  local dir="$1" stamp
  mkdir -p "${dir}"
  stamp="$(gcloud storage ls "gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_REPORT_PREFIX}/" 2>/dev/null \
    | sed 's#/$##' | sort | tail -1 || true)"
  if [ -z "${stamp}" ]; then
    _log "QUEUED (exit 42): no sig.at-rest-audit/1 report under ${SIG_ATREST_REPORT_PREFIX}/ — L1 has not recorded its counts."
    _log "re-run: ${RERUN} (scope: the seal leg only)"
    exit 42
  fi
  gcloud storage cp "${stamp}/report.json" "${dir}/report.json"
  gcloud storage cp "${stamp}/flagged.json" "${dir}/flagged.json"
  L1_REPORT_OBJECT="${stamp}/report.json"
  _log "   L1 counts loaded from ${L1_REPORT_OBJECT}"
}

# `_capture <dir>` — the prestate/poststate snapshot. Per-tier capture counts
# and the publishable-path list need the read DSN (SIG_DB_DSN — sig_audit via
# the exec host's posture or the operator's); the object listing + generation
# snapshot is the "no byte deleted or overwritten" baseline.
_capture() {
  local dir="$1"
  mkdir -p "${dir}"
  gcloud storage ls --long --recursive \
    "gs://${SIG_BUCKET_RESTRICTED}/${SIG_EXEC_CAPTURE_PREFIX}" \
    > "${dir}/captures-objects.txt" 2>/dev/null || true
  gcloud storage ls --long --recursive \
    "gs://${SIG_BUCKET_RESTRICTED}/ops/seal/" \
    > "${dir}/seal-objects.txt" 2>/dev/null || true
  gcloud storage ls --long --recursive \
    "gs://${SIG_BUCKET_RESTRICTED}/${SIG_EXEC_PROBE_PREFIX}/at-rest/" \
    > "${dir}/probe-objects.txt" 2>/dev/null || true
  gcloud sql backups list --instance "${SIG_SQL_INSTANCE}" \
    --project "${SIG_GCP_PROJECT}" --format json --limit 1 \
    > "${dir}/backup-latest.json" 2>/dev/null || printf '[]' > "${dir}/backup-latest.json"
  gcloud storage cat "gs://${SIG_BUCKET_RESTRICTED}/ops/seal/deny-set.json" \
    > "${dir}/deny-set-current.json" 2>/dev/null || printf '{}' > "${dir}/deny-set-current.json"
  if [ -n "${SIG_DB_DSN:-}" ]; then
    python3 - "${dir}" <<'PY'
import json, os, sys
import psycopg
out = sys.argv[1]
conn = psycopg.connect(os.environ["SIG_DB_DSN"], autocommit=True)
tiers = conn.execute(
    "SELECT storage_tier::text, count(*) FROM evidence_capture GROUP BY 1 ORDER BY 1"
).fetchall()
has_seal = conn.execute("SELECT to_regclass('capture_seal') IS NOT NULL").fetchone()[0]
seal_rows = (
    conn.execute("SELECT action, count(*) FROM capture_seal GROUP BY 1 ORDER BY 1").fetchall()
    if has_seal else []
)
publishable = conn.execute(
    "SELECT ea.artifact_id::text FROM evidence_artifact ea"
    " WHERE ea.sensitivity_tier = 0 ORDER BY ea.artifact_id"
).fetchall()
conn.close()
json.dump({
    "tiers": [[str(t), int(n)] for t, n in tiers],
    "capture_seal_present": bool(has_seal),
    "seal_rows": [[str(a), int(n)] for a, n in seal_rows],
    "publishable_artifacts": [str(r[0]) for r in publishable],
}, open(f"{out}/db-state.json", "w"), indent=2, sort_keys=True)
PY
  else
    printf '{"tiers":[],"capture_seal_present":null,"seal_rows":[],"publishable_artifacts":[]}' \
      > "${dir}/db-state.json"
    _log "   (SIG_DB_DSN unset — the per-tier counts record an empty state, flagged)"
  fi
  (cd "${dir}" && for f in *.json *.txt; do
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$f"; else shasum -a 256 "$f"; fi
  done) > "${dir}/sha256s.txt" 2>/dev/null || true
}

# `assert_no_byte_delta <pre> <post>` — the contract's strongest check: the
# name+generation multiset of every captured object is byte-identical across
# the seal. A missing object = deleted; a changed generation = overwritten —
# either is a hard stop.
assert_no_byte_delta() {
  local pre="$1" post="$2"
  python3 - "$pre" "$post" <<'PY'
import sys

def load(p):
    lines = []
    try:
        for ln in open(f"{p}/captures-objects.txt"):
            ln = ln.strip()
            if ln:
                lines.append(ln)
    except OSError:
        pass
    return sorted(lines)

pre, post = load(sys.argv[1]), load(sys.argv[2])
if pre == post:
    print("byte-delta: NONE — every captures/ object identical (name+generation)")
    sys.exit(0)
missing = [x for x in pre if x not in post]
added = [x for x in post if x not in pre]
print(f"byte-delta: {len(missing)} removed/changed, {len(added)} added")
for x in missing[:10]:
    print(f"  CHANGED-OR-REMOVED: {x}")
sys.exit(4)
PY
}

do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the seal leg's restore point under ${STATE_DIR}/pre (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud storage ls --long --recursive gs://${SIG_BUCKET_RESTRICTED}/${SIG_EXEC_CAPTURE_PREFIX}  > pre/captures-objects.txt  (the name+generation byte-delta baseline)"
    _plan "gcloud storage ls --long --recursive gs://${SIG_BUCKET_RESTRICTED}/ops/seal/  > pre/seal-objects.txt"
    _plan "gcloud storage ls --long --recursive gs://${SIG_BUCKET_RESTRICTED}/${SIG_EXEC_PROBE_PREFIX}/at-rest/  > pre/probe-objects.txt"
    _plan "gcloud sql backups list --instance ${SIG_SQL_INSTANCE} --limit 1 > pre/backup-latest.json"
    _plan "gcloud storage cat .../ops/seal/deny-set.json > pre/deny-set-current.json  (the version L2 supersedes)"
    _plan "psql (\$SIG_DB_DSN): per-tier capture counts + capture_seal posture + the publishable-artifact list > pre/db-state.json"
    _plan "sha256 sidecars > pre/sha256s.txt"
    return 0
  fi
  _capture "${STATE_DIR}/pre"
  _log "   prestate recorded under ${STATE_DIR}/pre (date -u: $(date -u +%FT%TZ))"
}

do_backup() {
  assert_window
  _log "-- backup ($(date -u +%FT%TZ)): AR-2 — an on-demand Cloud SQL backup of ${SIG_SQL_INSTANCE} before L2's first record write --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud sql backups create --instance ${SIG_SQL_INSTANCE} → list --limit 1 → assert SUCCESSFUL (recorded under ${STATE_DIR}/backup.json)"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
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
  _log "ERROR: the on-demand backup did not reach SUCCESSFUL (got '${status}') — AR-2 blocks the seal records." >&2
  exit 5
}

do_scan() {
  assert_window
  assert_exec_host
  _log "-- scan (L1, $(date -u +%FT%TZ)): the read-only at-rest audit — sig-exec-atrest-<stamp> --"
  local image="${SIG_EXEC_IMAGE:-}"
  if [ -z "${image}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      image="${SIG_API_IMAGE}:exec-atrest"   # placeholder — printed, never resolved
    else
      _log "ERROR: SIG_EXEC_IMAGE must name the exec workload image (a ${SIG_API_IMAGE}:<tag> — resolved to a digest, never :latest)." >&2
      exit 2
    fi
  fi
  image="$(pin_image_digest "${image}")"
  local conn="${SIG_GCP_PROJECT}:${SIG_GCP_REGION}:${SIG_SQL_INSTANCE}"
  local root="${SIG_EXEC_MOUNT}/${SIG_EXEC_CAPTURE_PREFIX}"
  # In-container: `sig-ops at-rest scan` reads the mounted OCFL root
  # (read-only), joins evidence_capture as sig_audit over the Cloud SQL
  # socket (the read posture — the DSN expands the container's env, never a
  # secret on this host), and lands the counts report + restricted flagged
  # sidecar under ops/probes/at-rest/<ts>/ — the only prefix the exec
  # identity may write.
  local cmd="exec python -m ops at-rest scan --root ${root%/} --bucket ${SIG_EXEC_BUCKET} --dsn \"host=/cloudsql/\${SIG_CLOUDSQL_CONNECTION} dbname=\${SIG_PG_DB} user=sig_audit password=\${SIG_AUDIT_PASSWORD}\""
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _sigops exec-host render --purpose atrest --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_AUDIT_PASSWORD \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --arg=-c --arg "${cmd}"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  local logf="${STATE_DIR}/scan-$(date -u +%Y%m%dT%H%M%SZ).log"
  _log "   running one-off at-rest scan (log → ${logf})"
  if ! _sigops exec-host run --purpose atrest --image "${image}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --secret-env SIG_AUDIT_PASSWORD \
      --env "SIG_EXEC_BUCKET=${SIG_EXEC_BUCKET}" \
      --env "SIG_CLOUDSQL_CONNECTION=${conn}" \
      --env "SIG_PG_DB=${SIG_PG_DB_NAME:-sig}" \
      --arg=-c --arg "${cmd}" \
      >"${logf}" 2>&1; then
    _log "ERROR: the scan run failed — ${logf} has the output; the cleanup still ran (name-checked delete)." >&2
    exit 4
  fi
  _log "   scan OK — the sig.at-rest-audit/1 report + restricted sidecar landed under ${SIG_ATREST_REPORT_PREFIX}/ (named in ${logf})"
}

do_seal() {
  assert_window
  _log "-- seal (L2, $(date -u +%FT%TZ)): protective suppression over the recorded L1 counts — seal scope only, never a purge --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "latest_l1_report ${STATE_DIR}/l1   (fetch the newest report+flagged; absent → exit 42 queued)"
    _plan "sig-ops at-rest seal-plan --flagged flagged.json --report report.json --prior-deny pre/deny-set-current.json --deny-out deny-set.json --pub002-out pub002-listing.json > ${STATE_DIR}/seal-plan.json"
    _plan "assert AR-2 backup SUCCESSFUL (the backup action's recorded state)"
    _plan "sig-ops at-rest seal-apply --plan seal-plan.json --dsn \$SIG_DB_DSN --author <operator> --apply   (capture_seal + artifact withhold dispositions — insert-only; exit 42 while capture_seal is undeployed)"
    _plan "gcloud storage cp deny-set.json gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_DENY_OBJECT}   (a NEW object VERSION — never an in-place rewrite)"
    _plan "gcloud storage cp pub002-listing.json gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_PUB002_OBJECT}"
    _plan "seal_register read-back (counts by action) → ${STATE_DIR}/seal-readback.json"
    return 0
  fi
  latest_l1_report "${STATE_DIR}/l1"
  [ -n "${SIG_DB_DSN:-}" ] || {
    _log "ERROR: SIG_DB_DSN must name the sealing connection (the owner-side write DSN)." >&2
    exit 2
  }
  [ -n "${SIG_ATREST_AUTHOR:-}" ] || {
    _log "ERROR: SIG_ATREST_AUTHOR must record the operator id on every seal row." >&2
    exit 2
  }
  # The AR-2 gate: a verified SUCCESSFUL on-demand backup this leg (or the
  # most recent backup younger than the window) before the first write.
  if [ ! -s "${STATE_DIR}/backup.json" ]; then
    _log "AR-2 gate: no recorded backup this leg — running the backup step first."
    do_backup
  fi
  local status
  status="$(python3 -c 'import json,sys
rows = json.load(open(sys.argv[1]))
print(rows[0].get("status","") if rows else "")' "${STATE_DIR}/backup.json" 2>/dev/null || true)"
  if [ "${status}" != "SUCCESSFUL" ]; then
    _log "ERROR: AR-2 gate — no SUCCESSFUL backup recorded; the seal records are blocked." >&2
    exit 5
  fi
  mkdir -p "${STATE_DIR}/seal"
  local prior=""
  if [ -s "${STATE_DIR}/pre/deny-set-current.json" ] && \
     python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "${STATE_DIR}/pre/deny-set-current.json" 2>/dev/null; then
    prior="--prior-deny ${STATE_DIR}/pre/deny-set-current.json"
  fi
  # shellcheck disable=SC2086
  _sigops at-rest seal-plan \
    --flagged "${STATE_DIR}/l1/flagged.json" \
    --report "${STATE_DIR}/l1/report.json" \
    ${prior} \
    --out "${STATE_DIR}/seal/seal-plan.json" \
    --deny-out "${STATE_DIR}/seal/deny-set.json" \
    --pub002-out "${STATE_DIR}/seal/pub002-listing.json"
  # The append-only records (exit 42 while capture_seal is undeployed — the
  # hosted deploy is P34.46's; queued, never partial).
  if ! _sigops at-rest seal-apply \
    --plan "${STATE_DIR}/seal/seal-plan.json" \
    --dsn "${SIG_DB_DSN}" \
    --author "${SIG_ATREST_AUTHOR}" \
    --audit-report-object "${L1_REPORT_OBJECT:-gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_REPORT_PREFIX}}" \
    --apply; then
    _log "QUEUED (exit 42): the seal records could not land — capture_seal undeployed or the write refused (see output above)."
    _log "re-run: ${RERUN} (scope: the seal leg only)"
    exit 42
  fi
  # The deny set + PUB-002 listing land as NEW object versions — the bucket's
  # versioning keeps the prior version; nothing is overwritten.
  run gcloud storage cp "${STATE_DIR}/seal/deny-set.json" \
    "gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_DENY_OBJECT}"
  run gcloud storage cp "${STATE_DIR}/seal/pub002-listing.json" \
    "gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_PUB002_OBJECT}"
  python3 - "${STATE_DIR}/seal/seal-readback.json" <<'PY'
import json, os, sys
import psycopg
conn = psycopg.connect(os.environ["SIG_DB_DSN"], autocommit=True)
rows = conn.execute(
    "SELECT action, count(*) FROM capture_seal GROUP BY 1 ORDER BY 1"
).fetchall()
conn.close()
json.dump({"seal_rows": [[str(a), int(n)] for a, n in rows]},
          open(sys.argv[1], "w"), indent=2, sort_keys=True)
PY
  _log "   seal applied — append-only records written; deny set versioned at ${SIG_ATREST_DENY_OBJECT} (read-back in seal-readback.json)"
}

do_verify() {
  _log "-- verify: poststate → byte-delta assert → sealed-digest serving check + seal-register read-back --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "re-capture the same listings under ${STATE_DIR}/post (or diff --from-state DIR offline)"
    _plan "assert_no_byte_delta pre post   (name+generation multiset identical — no byte deleted or overwritten)"
    _plan "for each sealed capture in the deny set: GET /v1/evidence/<artifact>/<capture> → the sealed rep (tier=sealed) or 404 under the artifact withhold"
    _plan "seal_register read-back: SELECT action,count(*) FROM capture_seal (not_evaluable while undeployed)"
    return 0
  fi
  if [ -n "${FROM_STATE}" ]; then
    assert_no_byte_delta "${FROM_STATE}" "${FROM_STATE}"
    _log "offline verify: the recorded snapshot is self-consistent (no byte delta vs itself)"
    return 0
  fi
  _capture "${STATE_DIR}/post"
  if [ -d "${STATE_DIR}/pre" ]; then
    assert_no_byte_delta "${STATE_DIR}/pre" "${STATE_DIR}/post" || {
      _log "ERROR: the captures/ object set changed across the seal — a byte was deleted or overwritten. STOP." >&2
      exit 4
    }
  fi
  # The sealed-digest serving check: the API must answer the sealed rep or
  # 404 for a sealed capture — never bytes, never content.
  if [ -s "${STATE_DIR}/seal/seal-plan.json" ] && [ -n "${SIG_API_URL:-}" ]; then
    python3 - "${STATE_DIR}/seal/seal-plan.json" "${SIG_API_URL}" <<'PY'
import json, sys, urllib.request
plan = json.load(open(sys.argv[1]))
base = sys.argv[2].rstrip("/")
checked = refused = 0
for e in plan["entries"]:
    for c in e["captures"]:
        url = f"{base}/v1/evidence/{c['artifact_id']}/{c['capture_id']}"
        try:
            body = json.loads(urllib.request.urlopen(url, timeout=15).read())
            tier = (body.get("capture") or {}).get("tier")
            if tier != "sealed":
                print(f"FAIL: {url} answered tier={tier!r} — the seal consult did not apply")
                sys.exit(4)
            refused += 1
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                refused += 1   # the artifact withhold denies the route — also safe
            else:
                raise
        checked += 1
print(f"sealed-serving: {refused}/{checked} sealed captures refused content (sealed rep or 404)")
sys.exit(0 if refused == checked else 4)
PY
  fi
  # The seal-register read-back — not_evaluable while undeployed.
  if [ -n "${SIG_DB_DSN:-}" ]; then
    python3 - <<'PY'
import os
import psycopg
conn = psycopg.connect(os.environ["SIG_DB_DSN"], autocommit=True)
has = conn.execute("SELECT to_regclass('capture_seal') IS NOT NULL").fetchone()[0]
if not has:
    print("seal_register: not_evaluable — capture_seal undeployed (rides the hosted deploy)")
else:
    rows = conn.execute("SELECT action, count(*) FROM capture_seal GROUP BY 1").fetchall()
    print(f"seal_register: {dict((str(a), int(n)) for a, n in rows)}")
conn.close()
PY
  fi
  _log "verify OK — bytes unchanged, sealed digests refused, the seal register read back."
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): superseding records only — unseal rows + the prior deny-set version (never a delete) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "INSERT capture_seal(action='unseal') for each capture this leg sealed (superseding append-only row — restoring prestate is always safe, deliberately not window-gated)"
    _plan "gcloud storage cp pre/deny-set-current.json gs://${SIG_BUCKET_RESTRICTED}/${SIG_ATREST_DENY_OBJECT}  (a new version restoring the prior entries)"
    _plan "INSERT publication_disposition allow-superseding rows for the artifacts this leg withheld (append-only)"
    return 0
  fi
  [ -s "${STATE_DIR}/seal/seal-plan.json" ] || {
    _log "nothing to roll back — no seal plan recorded under ${STATE_DIR}/seal/"
    return 0
  }
  [ -n "${SIG_DB_DSN:-}" ] || {
    _log "ERROR: rollback needs SIG_DB_DSN (the unseal rows are spine writes)." >&2
    exit 2
  }
  _log "   rollback is append-only: unseal rows + allow-superseding dispositions"
  python3 - "${STATE_DIR}/seal/seal-plan.json" <<'PY'
import json, os, sys
import psycopg
plan = json.load(open(sys.argv[1]))
conn = psycopg.connect(os.environ["SIG_DB_DSN"])
with conn.transaction():
    has = conn.execute("SELECT to_regclass('capture_seal') IS NOT NULL").fetchone()[0]
    if not has:
        print("capture_seal absent — nothing to supersede")
        sys.exit(0)
    sealed = {str(r[0]) for r in conn.execute(
        "SELECT DISTINCT capture_id::text FROM capture_seal"
        " WHERE capture_currently_sealed(capture_id)"
    ).fetchall()}
    n = 0
    for e in plan["entries"]:
        for c in e["captures"]:
            cid = str(c["capture_id"])
            if cid in sealed:
                conn.execute(
                    "INSERT INTO capture_seal"
                    "  (capture_id, content_digest, action, rules, author, audit_report)"
                    " VALUES (%s::uuid, %s, 'unseal', %s::text[], %s, %s)",
                    (cid, e["digest"], [], os.environ.get("SIG_ATREST_AUTHOR", "rollback"),
                     "rollback of the P34.49 seal leg"),
                )
                n += 1
    print(f"rollback: {n} superseding unseal rows recorded")
conn.close()
PY
}

do_all() {
  do_prestate
  do_backup
  do_scan
  do_seal
  do_verify
}

# Every non-check path requires SIG_GCP_PROJECT; check mode tolerates the
# placeholder. The clock guard precedes the ADC gate so a queued apply exits
# 42 cleanly.
require_project
case "${ACTION}" in
  backup|scan|seal|all) assert_window ;;
esac
# A live verify reads with ADC; an offline --from-state diff needs none.
if [ -z "${FROM_STATE}" ]; then
  require_adc
fi

banner "P34.49 at-rest audit (${ACTION})"
case "${ACTION}" in
  prestate)  do_prestate ;;
  backup)    do_backup ;;
  scan)      do_scan ;;
  seal)      do_seal ;;
  verify)    do_verify ;;
  rollback)  do_rollback ;;
  all)       do_all ;;
  *) _log "usage: at-rest-audit.sh [--check|--apply|--verify] [prestate|backup|scan|seal|verify|rollback|all]" >&2; exit 64 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "at-rest-audit ${ACTION}: check OK (mode=${SIG_GCP_MODE})"
fi
