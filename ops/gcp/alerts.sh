#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/alerts.sh — P34.4 alerts that reach a human: the alert-set leg runner.
#
# One pre-authorized production change (contract docs/tickets/
# 205_P34.4__alerts-that-reach-a-human.md; OM-20 S5-3 "Both + list + P34.45"
# 2026-10-01T04:28:49Z, expires GATE-G4) in five named mutations:
#
#   1. create the TLS-expiry alert policy — 21 days on the
#      time_until_ssl_cert_expires metric of the surveillancegraph.org
#      uptime check (QA-3)
#   2. create the SIG-ALERT log-based alert policy — textPayload:"SIG-ALERT"
#      on the sig-alerts service (QA-4)
#   3. re-roll sig-probe onto an image built at the current HEAD — the probe
#      targets live in ops/cadence.toml, baked into the image at
#      /app/ops/cadence.toml; the deployed image predates the retired
#      france/okc manifest targets (QA-5)
#   4. extend the failed-job policy 7285515107319155929 to sig-probe — only
#      AFTER the re-roll's next sweep goes green (contract ordering; the
#      update also adds daily re-notification, deliverable 5)
#   5. disable .github/workflows/reingest.yml — the irrelevant daily schedule
#      (QA-8; the committed schedule: block is already removed by this change)
#
# Stop rules: the jobfail extension refuses while the latest sig-probe
# execution is not green (exit 42 — queue, not failure). Every policy write is
# preceded by a full pre-state capture and is reversible: an update's rollback
# is the captured prior definition re-applied with --policy-from-file; a
# create's rollback is `gcloud alpha monitoring policies delete <id>`; the
# probe roll's rollback is the recorded before-digest via `sig-ops roll-jobs`;
# the workflow disable's rollback is `gh workflow enable reingest.yml` (with
# the schedule restored from git history, if ever wanted).
#
# Usage:
#   ops/gcp/alerts.sh [--check|--dry-run] [ACTION]    # plan only (default)
#   ops/gcp/alerts.sh [ACTION]                        # same — bare ACTION = plan
#   ops/gcp/alerts.sh --verify [--from-state DIR]     # read-only outcome diff
#   ops/gcp/alerts.sh --apply [ACTION]                # run the mutation(s)
#
# ACTION (default `all`):
#   prestate    capture the live alert set + sig-probe + cert + workflow state
#               (read-only — runs even inside the band)
#   monitoring  create the two new policies (1)(2); SKIP when a policy with the
#               same displayName already exists (updates it in place instead)
#   reingest    gh workflow disable reingest.yml when still active (5)
#   proberoll   build sig-api:p34-4-<head8> from `git archive HEAD` via Cloud
#               Build, pin the digest, `sig-ops roll-jobs --job sig-probe` (3)
#   delivery    POST a synthetic SIG-ALERT through the sig-alerts webhook and
#               read the SIG-ALERT-RECEIVED line back from Cloud Logging —
#               proves the QA-4 path end to end (the e-mail itself is the
#               human leg, D-P34.4-2)
#   jobfail     extend the failed-job policy (4) — REFUSES (exit 42) while the
#               latest sig-probe execution is not green
#   all         prestate -> monitoring -> reingest -> proberoll -> delivery ->
#               post-state capture -> --verify; then jobfail when its sweep
#               gate is green, else a printed queue note (second leg).
#
# Modes (same check/apply contract as lib.sh / protect.sh):
#   check    no ADC, no network; prints PLAN lines + `check OK`
#   apply    requires ADC + SIG_GCP_PROJECT (lib.sh gates); enforces the live
#            window — refuses while inside the daily 03:00-10:00Z band; the
#            proberoll leg additionally refuses inside an AR-3 window.
#            Monitoring-policy and workflow legs may run inside AR-3 (the
#            contract exempts them) but never inside the band. prestate and
#            verify are read-only and run any time.
#   verify   read-only; diffs the committed defs (ops/monitoring/) against the
#            live project — or --from-state recorded JSON — plus the workflow
#            state and the sig-probe digest pin; prints OK/DRIFT/MISSING/EXTRA
#            + `verify: N OK, M not-OK`; exit 1 on any non-OK (the P35.3-probe
#            shape, via `sig-ops monitoring-defs verify`).
#
# Env:
#   SIG_GCP_PROJECT          required for apply/live-verify (lib.sh require_project)
#   SIG_GCP_REGION           region (default us-central1, config.sh)
#   SIG_ALERTS_EVIDENCE_DIR  where captured JSON lands
#                            (default <repo>/docs/build/logs/alerts — gitignored)
#   SIG_ALERT_IMAGE_TAG      image ref for the probe roll
#                            (default ${SIG_API_IMAGE}:p34-4-<head8>)
#   SIG_ALERTS_NOW           ISO-8601 UTC override of `date -u` for the window
#                            guard ONLY (test seam; the guard echoes both clocks)
#   SIG_ALERTS_DELIVERY_WAIT seconds to wait before the delivery read-back
#                            (default 15; test seam)
#
# Credentials: the sig-alerts webhook token is read from Secret Manager into a
# variable that is never printed or persisted; no credential value is ever
# written to the evidence dirs.

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
  prestate|monitoring|reingest|proberoll|delivery|jobfail|all) MODE="check" ;;
  *) echo "alerts.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --from-state)
      [ $# -ge 2 ] || { echo "alerts.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    prestate|monitoring|reingest|proberoll|delivery|jobfail|all)
      [ "$ACTION" = "all" ] || { echo "alerts.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    *) echo "alerts.sh: unknown argument '$1'" >&2; _usage 64 ;;
  esac
done

export SIG_GCP_MODE="$MODE"
if [ "$MODE" = "verify" ] && [ -n "$FROM_STATE" ]; then
  # An offline from-state diff needs no ADC and tolerates an unset project —
  # the verify verb infers it from the captured resource names.
  : "${SIG_GCP_PROJECT:=}"
else
  require_project
fi
# config.sh derived SIG_API_IMAGE before require_project filled the placeholder;
# re-derive so check-mode PLANs name a real image path.
export SIG_API_IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-api"

# ---- constants --------------------------------------------------------------

# AR-3 windows (NEXT_PHASE_PLAN §8.4 backfill/catch-up table): the sig-probe
# image roll never runs here; monitoring/workflow legs may (contract exemption).
AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"

EVIDENCE_ROOT="${SIG_ALERTS_EVIDENCE_DIR:-${_here}/../../docs/build/logs/alerts}"
DEFS_DIR="${_here}/../monitoring"
JOBFAIL_POLICY_ID="7285515107319155929"
NEW_POLICY_SLUGS="alert-policy.tls-cert-expiry alert-policy.sig-alert-log"
WORKFLOW_FILE="${_here}/../../.github/workflows/reingest.yml"
RERUN_HINT="re-run: implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true"

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_iso_now() {
  # Test seam: SIG_ALERTS_NOW pins the guard's clock (ISO-8601 UTC); the real
  # clock is always echoed beside it.
  if [ -n "${SIG_ALERTS_NOW:-}" ]; then printf '%s\n' "$SIG_ALERTS_NOW";
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

_evidence_dir() {  # $1 = tag (pre|post|verify|apply)
  printf '%s/%s-%s\n' "$EVIDENCE_ROOT" "$1" "$(date -u +%Y%m%dT%H%M%SZ)"
}

# ---- window guard -----------------------------------------------------------
# The contract's live window: mutations never inside 03:00-10:00Z; the
# sig-probe image roll additionally never inside an AR-3 window (AR-3 covers
# hosted job rolls; monitoring/workflow legs are exempt by contract).

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
  # $1 = monitoring | proberoll   (the leg's window class)
  local leg="$1" now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=$leg"
  if _in_daily_band "$now"; then
    echo "alerts.sh: REFUSED — inside the global 03:00-10:00Z band ($now)" >&2
    echo "alerts.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  if [ "$leg" = "proberoll" ] && _in_ar3 "$now"; then
    echo "alerts.sh: REFUSED — the sig-probe roll inside an AR-3 window ($now)" >&2
    echo "alerts.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  echo "window-guard: OK"
}

# ---- helpers ----------------------------------------------------------------

_sigops() { (cd "${_here}/../.." && uv run "$@"); }

_policy_id_by_name() {  # $1 = exact displayName -> policy numeric id (empty if none)
  local display="$1" json
  json="$(gcloud alpha monitoring policies list \
    --project "$SIG_GCP_PROJECT" --format=json 2>/dev/null)" || return 0
  SIG_PLIST="$json" python3 - "$display" <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_PLIST"])
except Exception:
    sys.exit(0)
want = sys.argv[1]
for r in rows:
    if r.get("displayName") == want:
        print(str(r.get("name", "")).rsplit("/", 1)[-1])
        break
PY
}

_render_policy() {  # $1 = slug, $2 = out file — the --policy-from-file payload
  local slug="$1" out="$2"
  _sigops sig-ops monitoring-defs render --defs "$DEFS_DIR" --slug "$slug" \
    --project "$SIG_GCP_PROJECT" > "$out"
}

_render_prepared() {  # $1 = raw describe JSON, $2 = out — a rollback-ready body
  _sigops python - "$1" "$SIG_GCP_PROJECT" > "$2" <<'PY'
import json, sys
from ops.monitoring_defs import normalize
print(json.dumps(normalize("policy", json.load(open(sys.argv[1])), sys.argv[2]), indent=2, sort_keys=True))
PY
}

_probe_job_image() {
  gcloud run jobs describe "$SIG_RUN_JOB_PROBE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" --format=json \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]["image"])'
}

_latest_probe_green() {
  # 0 when the latest sig-probe execution completed green; 1 otherwise (or when
  # the read fails — fail-closed: the extension never runs on an unproven sweep).
  local json
  json="$(gcloud run jobs executions list \
    --job "$SIG_RUN_JOB_PROBE" --region "$SIG_GCP_REGION" \
    --project "$SIG_GCP_PROJECT" --limit 1 --format=json 2>/dev/null)" || return 1
  SIG_PEXEC="$json" python3 - <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_PEXEC"])
except Exception:
    sys.exit(1)
if not rows:
    sys.exit(1)
conds = (rows[0].get("status") or {}).get("conditions") or []
completed = any(c.get("type") == "Completed" and str(c.get("status")) == "True" for c in conds)
failed = any(c.get("type") == "Failed" and str(c.get("status")) == "True" for c in conds)
sys.exit(0 if completed and not failed else 1)
PY
}

_capture_lists() {  # $1 = dir — the three list files verify consumes
  local dir="$1"; mkdir -p "$dir"
  gcloud beta monitoring channels list --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/channels.json"
  gcloud monitoring uptime list-configs --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/uptime-checks.json"
  gcloud alpha monitoring policies list --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/alert-policies.json"
}

# `gh workflow view` carries no --json (gh 2.88); `workflow list` does. One
# row filtered to reingest.yml — prints {"state":"unknown"} on any failure.
_wf_state_json() {
  gh workflow list --json name,state,path --limit 200 2>/dev/null \
    | python3 -c '
import json, sys
try:
    rows = [w for w in json.load(sys.stdin)
            if str(w.get("path", "")).endswith("reingest.yml")]
except Exception:
    rows = []
print(json.dumps(rows[0] if rows else {"state": "absent"}))' \
    || echo '{"state":"unknown"}'
}

_wf_state() {  # just the state word
  _wf_state_json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("state","unknown"))' \
    2>/dev/null || echo unknown
}

# ---- actions ----------------------------------------------------------------

act_prestate() {
  # Read-only by construction — runs inside the band too (it changes nothing).
  if [ "$MODE" = "check" ]; then
    _plan "capture monitoring channel/uptime/policy lists, sig-probe describe +"
    _plan "image digest, sig-web-cert describe, gh workflow state + last runs,"
    _plan "recent SIG-ALERT lines -> \$SIG_ALERTS_EVIDENCE_DIR/pre-<ts> (+sha256s)"
    return 0
  fi
  local dir; dir="$(_evidence_dir pre)"; mkdir -p "$dir"
  _log "prestate: capturing live state -> $dir"
  _capture_lists "$dir"
  gcloud run jobs describe "$SIG_RUN_JOB_PROBE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" \
    --format=json > "$dir/sig-probe.job.json"
  _probe_job_image > "$dir/sig-probe.image.txt"
  gcloud compute ssl-certificates describe sig-web-cert --global \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/ssl-cert.json"
  _wf_state_json > "$dir/gh-workflow.json" || echo '{"state":"unknown"}' > "$dir/gh-workflow.json"
  gh run list --workflow reingest.yml --limit 5 \
    --json databaseId,status,conclusion,createdAt,headBranch \
    > "$dir/gh-runs.json" 2>/dev/null || echo '[]' > "$dir/gh-runs.json"
  gcloud logging read \
    'resource.labels.service_name="sig-alerts" AND textPayload:"SIG-ALERT"' \
    --project "$SIG_GCP_PROJECT" --freshness=24h --limit=20 \
    --format=json > "$dir/sig-alerts.log.json" 2>/dev/null || echo '[]' > "$dir/sig-alerts.log.json"
  (cd "$dir" && for f in *.json *.txt; do _sha256 "$f"; done) > "$dir/sha256s.txt"
  _log "prestate: sha256s recorded in $dir/sha256s.txt"
}

act_monitoring() {
  if [ "$MODE" = "check" ]; then
    for slug in $NEW_POLICY_SLUGS; do
      _plan "render ops/monitoring/${slug}.json -> gcloud alpha monitoring policies"
      _plan "  create --policy-from-file=<rendered> (or update when displayName exists)"
      _plan "  rollback: gcloud alpha monitoring policies delete <created id>"
    done
    return 0
  fi
  assert_window monitoring
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  local slug body display pid
  for slug in $NEW_POLICY_SLUGS; do
    body="$dir/${slug}.rendered.json"
    _render_policy "$slug" "$body"
    display="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["displayName"])' "$body")"
    pid="$(_policy_id_by_name "$display")"
    if [ -n "$pid" ]; then
      _log "SKIP create $slug — a policy named '$display' exists (id $pid); updating in place"
      run gcloud alpha monitoring policies update "$pid" \
        --project "$SIG_GCP_PROJECT" --policy-from-file="$body"
    else
      _log "create $slug — $display"
      run gcloud alpha monitoring policies create \
        --project "$SIG_GCP_PROJECT" --policy-from-file="$body"
      _log "  rollback: gcloud alpha monitoring policies delete <new id> --project $SIG_GCP_PROJECT"
    fi
  done
  _capture_lists "$dir"
  _log "monitoring: post-state lists -> $dir"
}

act_reingest() {
  if [ "$MODE" = "check" ]; then
    _plan "gh workflow list --json name,state,path (row reingest.yml); if active:"
    _plan "  gh workflow disable reingest.yml"
    _plan "  rollback: gh workflow enable reingest.yml (+ restore schedule: from git)"
    return 0
  fi
  assert_window monitoring
  # The committed workflow must already lack schedule: — live+code move together.
  if grep -qE '^\s*schedule:' "$WORKFLOW_FILE"; then
    echo "alerts.sh: ${WORKFLOW_FILE} still carries a schedule: block — the committed" >&2
    echo "alerts.sh: change must remove it before the live disable runs." >&2
    exit 6
  fi
  local state dir
  dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  state="$(_wf_state)"
  _log "reingest workflow state: ${state:-unknown}"
  if [ "$state" = "active" ]; then
    run gh workflow disable reingest.yml
    _wf_state_json > "$dir/gh-workflow.json"
    _log "reingest: post-state -> $dir/gh-workflow.json"
  else
    _log "SKIP — reingest.yml state is '${state:-unknown}', not active"
    echo "{\"state\":\"${state:-unknown}\"}" > "$dir/gh-workflow.json"
  fi
}

act_proberoll() {
  local tag="${SIG_ALERT_IMAGE_TAG:-${SIG_API_IMAGE}:p34-4-$(git rev-parse --short=8 HEAD)}"
  if [ "$MODE" = "check" ]; then
    _plan "git archive --format=tar.gz HEAD > <tmp>/ctx.tgz && gcloud builds submit <tmp>/ctx.tgz"
    _plan "  --config <tmp>/cloudbuild.yaml   # docker build -f ops/Dockerfile -t ${tag}"
    _plan "pin_image_digest ${tag} -> <repo>@sha256:<digest>      (never :latest, ADR-111)"
    _plan "uv run sig-ops roll-jobs --job ${SIG_RUN_JOB_PROBE} --image <digest> --apply --record <dir>/proberoll.record.json"
    _plan "  rollback: sig-ops roll-jobs --job ${SIG_RUN_JOB_PROBE} --image <recorded before_digest>"
    return 0
  fi
  assert_window proberoll
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  _log "proberoll: building ${tag} from git archive HEAD"
  local tmp
  tmp="$(mktemp -d)"
  git -C "${_here}/../.." archive --format=tar.gz HEAD > "${tmp}/ctx.tgz"
  cat > "${tmp}/cloudbuild.yaml" <<YAML
steps:
- name: gcr.io/cloud-builders/docker
  args: ["build", "-f", "ops/Dockerfile", "-t", "${tag}", "."]
images: ["${tag}"]
timeout: 3600s
YAML
  if ! gcloud builds submit "${tmp}/ctx.tgz" --config "${tmp}/cloudbuild.yaml" \
      --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" > "$dir/build.log" 2>&1; then
    tail -20 "$dir/build.log" >&2
    rm -rf "${tmp}"
    echo "alerts.sh: image build failed — nothing rolled" >&2
    exit 5
  fi
  rm -rf "${tmp}"
  local digest
  digest="$(pin_image_digest "$tag")" || exit 5
  _log "proberoll: pinned ${digest}"
  if ! _sigops sig-ops roll-jobs --job "$SIG_RUN_JOB_PROBE" --image "$digest" \
      --record "$dir/proberoll.record.json" --apply; then
    echo "alerts.sh: roll-jobs failed; the record names the rollback digest" >&2
    exit 5
  fi
  _probe_job_image > "$dir/sig-probe.image.after.txt"
  _log "proberoll: job image now $(cat "$dir/sig-probe.image.after.txt")"
}

act_delivery() {
  if [ "$MODE" = "check" ]; then
    _plan "POST {\"text\":\"SIG-ALERT critical: P34.4 delivery test …\"} to the"
    _plan "  sig-alerts webhook (URL resolved from the service; token from Secret"
    _plan "  Manager, never printed) -> read SIG-ALERT-RECEIVED back from logging"
    return 0
  fi
  assert_window monitoring
  local url token dir
  dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  url="$(gcloud run services describe "$SIG_ALERTS_SERVICE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" \
    --format='value(status.url)')"
  token="$(gcloud secrets versions access latest \
    --secret="$SIG_SECRET_ALERT_HOOK" --project "$SIG_GCP_PROJECT" 2>/dev/null)"
  local body
  body="$(python3 -c '
import json
print(json.dumps({
  "text": "SIG-ALERT critical: P34.4 delivery test (synthetic) — confirm receipt at the operator channel",
  "alert": {"kind": "delivery-test", "severity": "critical", "source": "ops/gcp/alerts.sh"},
}))')"
  local -a auth=()
  [ -n "${token:-}" ] && auth=(-H "Authorization: Bearer ${token}")
  local status
  status="$(curl -sS -o "$dir/delivery.response.txt" -w 'HTTP %{http_code}' \
    -X POST "$url" -H 'Content-Type: application/json' \
    "${auth[@]}" -d "$body")"
  printf '%s\n' "$status" | tee "$dir/delivery.status.txt"
  case "$status" in
    "HTTP 2"*) ;;
    *) echo "alerts.sh: delivery POST returned $status — aborting before read-back" >&2
       exit 7 ;;
  esac
  _log "delivery: reading the SIG-ALERT-RECEIVED line back (wait ${SIG_ALERTS_DELIVERY_WAIT:-15}s)"
  sleep "${SIG_ALERTS_DELIVERY_WAIT:-15}"
  gcloud logging read \
    'resource.labels.service_name="sig-alerts" AND textPayload:"SIG-ALERT" AND textPayload:"delivery test"' \
    --project "$SIG_GCP_PROJECT" --freshness=10m --limit=5 \
    --format=json > "$dir/delivery.log.json" || true
  if ! python3 - "$dir/delivery.log.json" <<'PY'
import json, sys
try:
    rows = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
sys.exit(0 if any("SIG-ALERT" in str(r.get("textPayload", "")) for r in rows) else 1)
PY
  then
    echo "alerts.sh: no SIG-ALERT-RECEIVED line yet — notification may still be" >&2
    echo "alerts.sh: in flight; re-check with gcloud logging read (freshness 30m)." >&2
    exit 7
  fi
  _log "delivery: SIG-ALERT-RECEIVED observed on sig-alerts — the log-match"
  _log "  policy opens an incident; e-mail receipt is the human leg (D-P34.4-2)"
}

act_jobfail() {
  if [ "$MODE" = "check" ]; then
    _plan "gate: latest ${SIG_RUN_JOB_PROBE} execution must be green (the re-roll's"
    _plan "  sweep) — else exit 42, queued until the next sweep"
    _plan "gcloud alpha monitoring policies update ${JOBFAIL_POLICY_ID}"
    _plan "  --policy-from-file=<rendered alert-policy.job-failures.json>"
    _plan "  (drops the != sig-probe exclusion, renames the policy, adds daily"
    _plan "   re-notification) — rollback: re-apply the captured prior definition"
    return 0
  fi
  assert_window monitoring
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  # Capture the PRIOR definition — the update's rollback target — before writing.
  gcloud alpha monitoring policies describe "$JOBFAIL_POLICY_ID" \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/policy.${JOBFAIL_POLICY_ID}.prior.json"
  _render_prepared "$dir/policy.${JOBFAIL_POLICY_ID}.prior.json" \
    "$dir/policy.${JOBFAIL_POLICY_ID}.prior.rendered.json"
  if ! _latest_probe_green; then
    echo "alerts.sh: REFUSED — the latest ${SIG_RUN_JOB_PROBE} execution is not green" >&2
    echo "alerts.sh: (or the read failed). The extension lands only after the" >&2
    echo "alerts.sh: re-roll's sweep goes green — queue this leg. ${RERUN_HINT}" >&2
    exit 42
  fi
  local body="$dir/alert-policy.job-failures.rendered.json"
  _render_policy "alert-policy.job-failures" "$body"
  run gcloud alpha monitoring policies update "$JOBFAIL_POLICY_ID" \
    --project "$SIG_GCP_PROJECT" --policy-from-file="$body"
  _log "  rollback: gcloud alpha monitoring policies update ${JOBFAIL_POLICY_ID}"
  _log "    --policy-from-file=$dir/policy.${JOBFAIL_POLICY_ID}.prior.rendered.json"
  gcloud alpha monitoring policies describe "$JOBFAIL_POLICY_ID" \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/policy.${JOBFAIL_POLICY_ID}.after.json"
  _log "jobfail: read-back -> $dir/policy.${JOBFAIL_POLICY_ID}.after.json"
}

act_verify() {
  local dir="$FROM_STATE"
  if [ -z "$dir" ]; then
    dir="$(_evidence_dir verify)"
    if [ "$MODE" = "check" ]; then
      _plan "capture channel/uptime/policy lists -> $dir, then"
      _plan "sig-ops monitoring-defs verify --from-state $dir --project <p>"
      _plan "+ workflow state + sig-probe digest checks; exit 1 on any non-OK"
      return 0
    fi
    mkdir -p "$dir"
    _log "verify: live reads -> $dir"
    _capture_lists "$dir"
    _wf_state_json > "$dir/gh-workflow.json" || echo '{"state":"unknown"}' > "$dir/gh-workflow.json"
    _probe_job_image > "$dir/sig-probe.image.txt" || true
  else
    [ -d "$dir" ] || { echo "alerts.sh: --from-state '$dir' is not a directory" >&2; exit 66; }
    echo "verify: from-state $dir"
  fi
  local rc=0
  _sigops sig-ops monitoring-defs verify --defs "$DEFS_DIR" --from-state "$dir" \
    --project "$SIG_GCP_PROJECT" || rc=$?
  # Extra rows the defs diff does not cover: the workflow state and the
  # sig-probe image pin (an unpinned or stale image is drift by contract).
  local extra_bad=0
  if [ -f "$dir/gh-workflow.json" ]; then
    local wf
    wf="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("state",""))' \
      "$dir/gh-workflow.json" 2>/dev/null || echo unknown)"
    case "$wf" in
      active)
        echo "DRIFT workflow/reingest — state=active (the disable leg has not run)"
        extra_bad=$((extra_bad + 1)) ;;
      unknown|"")
        echo "DRIFT workflow/reingest — state unread (gh view failed or not captured)"
        extra_bad=$((extra_bad + 1)) ;;
      *) echo "OK workflow/reingest — state=$wf" ;;
    esac
  fi
  if [ -f "$dir/sig-probe.image.txt" ]; then
    local img
    img="$(cat "$dir/sig-probe.image.txt")"
    case "$img" in
      *@sha256:*) echo "OK job/sig-probe — pinned ${img}" ;;
      *) echo "DRIFT job/sig-probe — unpinned image ${img}"; extra_bad=$((extra_bad + 1)) ;;
    esac
  fi
  if [ "$extra_bad" -gt 0 ] || [ "$rc" -ne 0 ]; then
    return 1
  fi
  return 0
}

# ---- dispatch ---------------------------------------------------------------

_log "=============================================================="
_log "SIG alerts leg-runner — P34.4 (mode=${MODE} action=${ACTION})"
_log "  project=${SIG_GCP_PROJECT:-<unset>} region=${SIG_GCP_REGION}"
_log "=============================================================="

case "$MODE" in
  check)
    require_project   # tolerates unset in check mode (placeholder in PLANs)
    case "$ACTION" in
      all)
        act_prestate; act_monitoring; act_reingest; act_proberoll
        act_delivery; act_jobfail; act_verify
        ;;
      prestate) act_prestate ;;
      monitoring) act_monitoring ;;
      reingest) act_reingest ;;
      proberoll) act_proberoll ;;
      delivery) act_delivery ;;
      jobfail) act_jobfail ;;
    esac
    _log "check OK"
    ;;
  verify)
    [ -n "$FROM_STATE" ] || require_adc   # live reads need ADC; from-state doesn't
    act_verify
    ;;
  apply)
    require_project; require_adc
    case "$ACTION" in
      prestate) act_prestate ;;
      monitoring) act_monitoring ;;
      reingest) act_reingest ;;
      proberoll) act_proberoll ;;
      delivery) act_delivery ;;
      jobfail) act_jobfail ;;
      all)
        act_prestate
        act_monitoring
        act_reingest
        act_proberoll
        act_delivery
        _log "-- post-state capture + verify --"
        if ! act_verify; then
          _log "verify mid-run: drift is expected until the jobfail leg lands"
        fi
        _log "-- jobfail extension (sweep-gated) --"
        if act_jobfail; then
          act_verify
        else
          rc=$?
          if [ "$rc" -eq 42 ]; then
            _log "jobfail: QUEUED until the re-roll's next sweep is green —"
            _log "  second leg: ops/gcp/alerts.sh --apply jobfail && ops/gcp/alerts.sh --verify"
            exit 0
          fi
          exit "$rc"
        fi
        ;;
    esac
    ;;
esac
