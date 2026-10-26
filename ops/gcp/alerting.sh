#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/alerting.sh — P35.2 alerting-as-code + escalation: the alert roll.
#
# The named-mutation set (contract docs/tickets/
# 346_P35.2__alerting-as-code-and-escalation.md — OM-20, the GATE-G5 list that
# names this row verbatim; codifies and extends P34.4, never re-creates it):
#
#   1. alert policies as code — every ops/monitoring/alert-policy.*.json def
#      with apply != diff-only reconciled: create when absent (matched on
#      displayName), update in place otherwise; the rendered bodies already
#      bind the operator e-mail channel (P34.4's mechanism — its creation is
#      never this roll's). The update carries the P35.2 addition:
#      alertStrategy.notificationRateLimit = 86400s (SIG-OPS-006's >24h-red
#      re-notifies-once-daily rule, D-P34.4-3's hygiene leg).
#   2. uptime checks as code — the two checks (site root content-match +
#      API /health, 5-minute cadence, 3 declared regions) applied via
#      `gcloud monitoring uptime update|create` with the argv rendered by
#      `sig-ops monitoring-defs render-uptime` — never hand-built flags.
#   3. log retention — `_Default` 30 → 90 days (the contract's first option;
#      the sig-restricted/ops/logs/ sink is the recorded alternative).
#   4. bucket versioning (G1-05) — gs://<project>-sig-restricted, which holds
#      ops/probes/ and ops/runs/ (append-only, tamper-evident).
#   5. probe targets out of the image (G1-02a) — the declaration bundle is
#      re-published to gs://<project>-sig-restricted/ops/declared/live-diff.json
#      (sig-ops live-diff --emit-declared), sig-probe's SIG_OPS_DECLARED_GCS
#      env is asserted, and the job rolls onto an image built at this HEAD —
#      the image that reads the bundle FIRST (ops.scheduled.load_cadence_
#      external), so a cadence edit needs no image roll (SIG-OPS-005).
#
# Stop rules: every mutating leg captures its own pre-state first (AR-2's
# restore point = the committed IaC text plus the recorded describes) and is
# reversible — a policy update's rollback is the captured prior definition
# re-applied with --policy-from-file; an uptime update's rollback is the
# prior config re-applied with the same flag render; a create's rollback is
# delete; retention's is the captured prior days; versioning's is
# --no-versioning; the job roll's is the recorded before-digest via
# `sig-ops roll-jobs`. The e-mail channel is P34.4's (apply=diff-only):
# when it is absent the policies leg refuses (exit 42 — queue, never a
# half-applied policy bound to a missing channel; its owner row re-runs
# 205's live_verification=true first).
#
# Usage:
#   ops/gcp/alerting.sh [--check|--dry-run] [ACTION]    # plan only (default)
#   ops/gcp/alerting.sh [ACTION]                        # same — bare ACTION = plan
#   ops/gcp/alerting.sh --verify [--from-state DIR]     # read-only outcome diff
#   ops/gcp/alerting.sh --apply [ACTION]                # run the mutation(s)
#
# ACTION (default `all`):
#   prestate    capture the live alert set + retention + bucket posture +
#               sig-probe/sig-alerts describes (read-only — runs any time)
#   bundle      publish the declaration bundle the probe targets ride (1 leg of 5)
#   policies    reconcile every non-diff-only alert-policy def (1) — REFUSES
#               (exit 42) while the operator e-mail channel is absent
#               (P34.4's mechanism is owed first)
#   uptime      reconcile the two uptime-check defs (2)
#   retention   _Default 30 -> 90 days (3)
#   versioning  sig-restricted versioning on — covers ops/probes/ + ops/runs/ (4)
#   proberoll   bundle publish + SIG_OPS_DECLARED_GCS env assert + image
#               rebuild + roll-jobs (5)
#   all         prestate -> bundle -> policies -> uptime -> retention ->
#               versioning -> proberoll -> post-state -> --verify
#
# Modes (same check/apply contract as lib.sh / alerts.sh):
#   check    no ADC, no network; prints PLAN lines + `check OK`
#   apply    requires ADC + SIG_GCP_PROJECT (lib.sh gates); enforces the live
#            window — refuses inside the daily 03:00-06:30Z AR-3 freeze and
#            inside the AR-3 batch windows (the contract's "outside the batch
#            windows"); AR-2's on-demand backup first is the operator's step
#            the prestate capture records. prestate and verify are read-only
#            and run any time.
#   verify   read-only; `sig-ops monitoring-defs verify` (live or --from-state)
#            plus the non-monitoring posture rows: _Default retention=90,
#            restricted-bucket versioning, sig-probe digest pin +
#            SIG_OPS_DECLARED_GCS env, sig-alerts digest pin (§3.3 — never
#            :latest); exit 1 on any non-OK.
#
# Env:
#   SIG_GCP_PROJECT            required for apply/live-verify (lib.sh require_project)
#   SIG_GCP_REGION             region (default us-central1, config.sh)
#   SIG_ALERTING_EVIDENCE_DIR  where captured JSON lands
#                              (default <repo>/docs/build/logs/alerting — gitignored)
#   SIG_ALERTING_IMAGE_TAG     image ref for the probe roll
#                              (default ${SIG_API_IMAGE}:p35-2-<head8>)
#   SIG_ALERTING_NOW           ISO-8601 UTC override of `date -u` for the window
#                              guard ONLY (test seam; the guard echoes both clocks)
#
# Credentials: none needed — this roll touches no secret. The operator's
# e-mail address is never read, printed or persisted (the channel def's
# <redacted …> leaf never compares).
#
# Re-run prompt (OM-19): the roll is idempotent-reconcile — a resumed run
# converges declared posture, never re-creates unnecessarily.
#   implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true

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
  prestate|bundle|policies|uptime|retention|versioning|proberoll|all) MODE="check" ;;
  *) echo "alerting.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --from-state)
      [ $# -ge 2 ] || { echo "alerting.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    prestate|bundle|policies|uptime|retention|versioning|proberoll|all)
      [ "$ACTION" = "all" ] || { echo "alerting.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    *) echo "alerting.sh: unknown argument '$1'" >&2; _usage 64 ;;
  esac
done

export SIG_GCP_MODE="$MODE"
if [ "$MODE" = "verify" ] && [ -n "$FROM_STATE" ]; then
  : "${SIG_GCP_PROJECT:=}"
else
  require_project
fi
export SIG_API_IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-api"

# ---- constants --------------------------------------------------------------

# AR-3 windows (the batch windows the contract's roll stays outside of):
AR3_WINDOWS="2026-10-06T00:00:00Z 2026-10-13T12:00:00Z
2026-11-06T00:00:00Z 2026-11-13T12:00:00Z
2026-12-06T00:00:00Z 2026-12-13T12:00:00Z"

EVIDENCE_ROOT="${SIG_ALERTING_EVIDENCE_DIR:-${_here}/../../docs/build/logs/alerting}"
DEFS_DIR="${_here}/../monitoring"
RETENTION_DAYS="90"
DECLARED_GCS_URI="gs://${SIG_BUCKET_RESTRICTED}/ops/declared/live-diff.json"
RERUN_HINT="re-run: implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true"
P344_HINT="the e-mail channel is P34.4's — queue and re-run: implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true"

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_iso_now() {
  if [ -n "${SIG_ALERTING_NOW:-}" ]; then printf '%s\n' "$SIG_ALERTING_NOW";
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
# The contract's live window (AR-3 + AR-2): no mutation inside the daily
# 03:00-06:30Z AR-3 freeze, and never inside an AR-3 batch window — the roll
# happens outside the batch windows.

_in_daily_freeze() {
  local hh mm
  hh="$(printf '%s' "$1" | sed 's/.*T//; s/:.*//')"
  mm="$(printf '%s' "$1" | sed 's/.*T[0-9]*://; s/:.*//')"
  [ "$hh" -gt 3 ] || { [ "$hh" -eq 3 ] && [ "$mm" -ge 0 ]; } || return 1
  { [ "$hh" -lt 6 ] || { [ "$hh" -eq 6 ] && [ "$mm" -lt 30 ]; }; }
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
  local leg="$1" now real_now
  now="$(_iso_now)"; real_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "window-guard: now=$now (date -u=$real_now) leg=$leg"
  if _in_daily_freeze "$now"; then
    echo "alerting.sh: REFUSED — inside the 03:00-06:30Z AR-3 freeze ($now)" >&2
    echo "alerting.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  if _in_ar3 "$now"; then
    echo "alerting.sh: REFUSED — inside an AR-3 batch window ($now);" >&2
    echo "alerting.sh: the roll happens outside the batch windows (AR-3 + AR-2)" >&2
    echo "alerting.sh: ${RERUN_HINT}" >&2
    exit 42
  fi
  echo "window-guard: OK"
}

# ---- helpers ----------------------------------------------------------------

_sigops() { (cd "${_here}/../.." && uv run "$@"); }

_capture_lists() {  # $1 = dir — the three list files verify consumes
  local dir="$1"; mkdir -p "$dir"
  gcloud beta monitoring channels list --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/channels.json"
  gcloud monitoring uptime list-configs --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/uptime-checks.json"
  gcloud alpha monitoring policies list --project "$SIG_GCP_PROJECT" \
    --format=json > "$dir/alert-policies.json"
}

_channel_present() {
  # The operator e-mail channel (P34.4's): present and enabled. Never reads the
  # address — the def's <redacted …> leaf is the contract.
  local json
  json="$(gcloud beta monitoring channels list \
    --project "$SIG_GCP_PROJECT" --format=json 2>/dev/null)" || return 1
  SIG_CLIST="$json" python3 - <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_CLIST"])
except Exception:
    sys.exit(1)
sys.exit(0 if any(
    str(r.get("displayName")) == "SIG operator email (Track 0.5)"
    and r.get("enabled", False)
    for r in rows
) else 1)
PY
}

_policy_slug_set() {
  # policy defs that reconcile (kind=policy AND apply != diff-only), slug-sorted.
  python3 - "$DEFS_DIR" <<'PY'
import json, sys
from pathlib import Path
for p in sorted(Path(sys.argv[1]).glob("alert-policy.*.json")):
    d = json.loads(p.read_text())
    if d["_sig"].get("apply") != "diff-only":
        print(p.stem)
PY
}

_uptime_slug_set() {
  python3 - "$DEFS_DIR" <<'PY'
import json, sys
from pathlib import Path
for p in sorted(Path(sys.argv[1]).glob("uptime-check.*.json")):
    d = json.loads(p.read_text())
    if d["_sig"].get("apply") != "diff-only":
        print(p.stem)
PY
}

_policy_id_for() {  # $1 = slug -> live policy numeric id (empty when absent)
  local slug="$1" json
  json="$(gcloud alpha monitoring policies list \
    --project "$SIG_GCP_PROJECT" --format=json 2>/dev/null)" || return 0
  SIG_PLIST="$json" python3 - "$DEFS_DIR/${slug}.json" <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_PLIST"])
    defn = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
rid = defn["_sig"].get("id")
display = defn["_sig"].get("displayName") or defn.get("displayName", "")
for r in rows:
    name_id = str(r.get("name", "")).rsplit("/", 1)[-1]
    if (rid and name_id == str(rid)) or (not rid and r.get("displayName") == display):
        print(name_id)
        break
PY
}

_uptime_id_for() {  # $1 = slug -> live uptime-check config id (empty when absent)
  local slug="$1" json
  json="$(gcloud monitoring uptime list-configs \
    --project "$SIG_GCP_PROJECT" --format=json 2>/dev/null)" || return 0
  SIG_ULIST="$json" python3 - "$DEFS_DIR/${slug}.json" <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_ULIST"])
    defn = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
rid = defn["_sig"].get("id")
display = defn["_sig"].get("displayName") or defn.get("displayName", "")
for r in rows:
    name_id = str(r.get("name", "")).rsplit("/", 1)[-1]
    if (rid and name_id == str(rid)) or r.get("displayName") == display:
        print(name_id)
        break
PY
}

_render_policy() {  # $1 = slug, $2 = out — the --policy-from-file payload
  _sigops sig-ops monitoring-defs render --defs "$DEFS_DIR" --slug "$1" \
    --project "$SIG_GCP_PROJECT" > "$2"
}

_render_prepared() {  # $1 = raw describe JSON, $2 = out — a rollback-ready body
  _sigops python - "$1" "$SIG_GCP_PROJECT" > "$2" <<'PY'
import json, sys
from ops.monitoring_defs import normalize
print(json.dumps(normalize("policy", json.load(open(sys.argv[1])), sys.argv[2]), indent=2, sort_keys=True))
PY
}

_render_uptime_args() {  # $1 = slug, $2 = check-id ("" => create), $3 = out argv file
  local cid_arg=()
  [ -n "$2" ] && cid_arg=(--check-id "$2")
  _sigops sig-ops monitoring-defs render-uptime --defs "$DEFS_DIR" \
    --slug "$1" --project "$SIG_GCP_PROJECT" "${cid_arg[@]}" > "$3"
}

_probe_job_image() {
  gcloud run jobs describe "$SIG_RUN_JOB_PROBE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" --format=json \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]["image"])'
}

_probe_job_env() {  # $1 = env name -> its value on sig-probe (empty if unset)
  gcloud run jobs describe "$SIG_RUN_JOB_PROBE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" --format=json \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
env = d["spec"]["template"]["spec"]["template"]["spec"]["containers"][0].get("env", [])
print(next((e.get("value", "") for e in env if e.get("name") == sys.argv[1]), ""))' "$1"
}

_service_image() {  # $1 = cloud run service -> image ref
  gcloud run services describe "$1" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" --format=json 2>/dev/null \
    | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d["spec"]["template"]["spec"]["containers"][0]["image"])
except Exception:
    print("")'
}

_retention_days() {
  gcloud logging buckets describe _Default --location=global \
    --project="$SIG_GCP_PROJECT" --format='value(retentionDays)' 2>/dev/null
}

_bucket_versioning() {
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
    --format='value(versioning.enabled)' 2>/dev/null
}

# ---- actions ----------------------------------------------------------------

act_prestate() {
  # Read-only by construction — runs inside the freeze too (it changes nothing).
  if [ "$MODE" = "check" ]; then
    _plan "capture monitoring channel/uptime/policy lists, _Default retention"
    _plan "describe, sig-restricted bucket describe (versioning), sig-probe job"
    _plan "describe + image + env, sig-alerts service describe (digest record),"
    _plan "sig-web-cert describe, declaration bundle head -> \$SIG_ALERTING_EVIDENCE_DIR/pre-<ts> (+sha256s)"
    return 0
  fi
  local dir; dir="$(_evidence_dir pre)"; mkdir -p "$dir"
  _log "prestate: capturing live state -> $dir"
  _capture_lists "$dir"
  gcloud logging buckets describe _Default --location=global \
    --project="$SIG_GCP_PROJECT" --format=json > "$dir/log-retention.json" \
    2>/dev/null || echo '{"retentionDays":null}' > "$dir/log-retention.json"
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
    --format=json > "$dir/restricted-bucket.json" \
    2>/dev/null || echo '{}' > "$dir/restricted-bucket.json"
  gcloud run jobs describe "$SIG_RUN_JOB_PROBE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" \
    --format=json > "$dir/sig-probe.job.json" \
    2>/dev/null || echo '{}' > "$dir/sig-probe.job.json"
  _probe_job_image > "$dir/sig-probe.image.txt" 2>/dev/null \
    || echo "unread" > "$dir/sig-probe.image.txt"
  _probe_job_env SIG_OPS_DECLARED_GCS > "$dir/sig-probe.declared-env.txt" \
    2>/dev/null || echo "" > "$dir/sig-probe.declared-env.txt"
  gcloud run services describe "$SIG_ALERTS_SERVICE" \
    --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" \
    --format=json > "$dir/sig-alerts.service.json" \
    2>/dev/null || echo '{}' > "$dir/sig-alerts.service.json"
  _service_image "$SIG_ALERTS_SERVICE" > "$dir/sig-alerts.image.txt" \
    2>/dev/null || echo "unread" > "$dir/sig-alerts.image.txt"
  gcloud compute ssl-certificates describe sig-web-cert --global \
    --project "$SIG_GCP_PROJECT" --format=json > "$dir/ssl-cert.json" \
    2>/dev/null || echo '{}' > "$dir/ssl-cert.json"
  (cd "$dir" && for f in *.json *.txt; do _sha256 "$f"; done) > "$dir/sha256s.txt"
  _log "prestate: sha256s recorded in $dir/sha256s.txt"
}

act_bundle() {
  if [ "$MODE" = "check" ]; then
    _plan "sig-ops live-diff --emit-declared | gcloud storage cp - ${DECLARED_GCS_URI}"
    _plan "  # the probe-target declaration the sig-probe job reads via"
    _plan "  # SIG_OPS_DECLARED_GCS — a cadence edit needs no image roll (G1-02a)"
    return 0
  fi
  assert_window bundle
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  _log "bundle: publishing declaration bundle -> $DECLARED_GCS_URI"
  gcloud storage cp "$DECLARED_GCS_URI" "$dir/declared-bundle.prior.json" \
    2>/dev/null || _log "  no prior bundle object (first publish)"
  _sigops sig-ops live-diff --emit-declared > "$dir/declared-bundle.json"
  run gcloud storage cp "$dir/declared-bundle.json" "$DECLARED_GCS_URI" \
    --content-type=application/json
  _log "  rollback: gcloud storage cp $dir/declared-bundle.prior.json $DECLARED_GCS_URI"
}

act_policies() {
  if [ "$MODE" = "check" ]; then
    _plan "gate: operator e-mail channel present+enabled (P34.4's; else exit 42)"
    for slug in $(_policy_slug_set); do
      _plan "render ops/monitoring/${slug}.json -> gcloud alpha monitoring policies"
      _plan "  update <id> --policy-from-file=<rendered> (or create when absent;"
      _plan "  rollback: re-apply the captured prior body / delete the new id)"
    done
    return 0
  fi
  assert_window policies
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  if ! _channel_present; then
    echo "alerting.sh: REFUSED — the operator e-mail channel is absent/disabled;" >&2
    echo "alerting.sh: ${P344_HINT}" >&2
    exit 42
  fi
  local slug body pid
  for slug in $(_policy_slug_set); do
    body="$dir/${slug}.rendered.json"
    _render_policy "$slug" "$body"
    pid="$(_policy_id_for "$slug")"
    if [ -n "$pid" ]; then
      gcloud alpha monitoring policies describe "$pid" \
        --project "$SIG_GCP_PROJECT" --format=json \
        > "$dir/policy.${pid}.prior.json"
      _render_prepared "$dir/policy.${pid}.prior.json" \
        "$dir/policy.${pid}.prior.rendered.json"
      _log "update $slug — id $pid (notificationRateLimit 86400s where declared)"
      run gcloud alpha monitoring policies update "$pid" \
        --project "$SIG_GCP_PROJECT" --policy-from-file="$body"
      _log "  rollback: gcloud alpha monitoring policies update $pid"
      _log "    --policy-from-file=$dir/policy.${pid}.prior.rendered.json"
    else
      _log "create $slug"
      run gcloud alpha monitoring policies create \
        --project "$SIG_GCP_PROJECT" --policy-from-file="$body"
      _log "  rollback: gcloud alpha monitoring policies delete <new id>"
    fi
  done
  _capture_lists "$dir"
  _log "policies: post-state lists -> $dir"
}

act_uptime() {
  if [ "$MODE" = "check" ]; then
    for slug in $(_uptime_slug_set); do
      _plan "resolve live uptime-check id for ${slug} (displayName match) ->"
      _plan "  sig-ops monitoring-defs render-uptime --slug ${slug} --check-id <id>"
      _plan "  gcloud monitoring uptime <rendered argv>  (create when absent)"
    done
    return 0
  fi
  assert_window uptime
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  local slug cid argv_file
  for slug in $(_uptime_slug_set); do
    cid="$(_uptime_id_for "$slug")"
    argv_file="$dir/${slug}.argv.json"
    _render_uptime_args "$slug" "$cid" "$argv_file"
    if [ -n "$cid" ]; then
      gcloud monitoring uptime describe "$cid" \
        --project "$SIG_GCP_PROJECT" --format=json \
        > "$dir/uptime.${cid}.prior.json" 2>/dev/null || true
      _log "update uptime-check $slug — id $cid (3 regions + content match per def)"
      _log "  rollback: re-apply $dir/uptime.${cid}.prior.json via the same flag render"
    else
      _log "create uptime-check $slug"
      _log "  rollback: gcloud monitoring uptime delete <new id>"
    fi
    local -a argv=()
    while IFS= read -r a; do argv+=("$a"); done < <(
      python3 -c 'import json,sys; [print(a) for a in json.load(open(sys.argv[1]))]' "$argv_file"
    )
    run gcloud monitoring uptime "${argv[@]}" --project "$SIG_GCP_PROJECT"
  done
  _capture_lists "$dir"
  _log "uptime: post-state lists -> $dir"
}

act_retention() {
  if [ "$MODE" = "check" ]; then
    _plan "gcloud logging buckets describe _Default --location=global  # capture prior days"
    _plan "gcloud logging buckets update _Default --location=global --retention-days=${RETENTION_DAYS}"
    _plan "  rollback: update --retention-days=<captured prior>"
    return 0
  fi
  assert_window retention
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  local prior
  gcloud logging buckets describe _Default --location=global \
    --project="$SIG_GCP_PROJECT" --format=json > "$dir/log-retention.prior.json"
  prior="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("retentionDays",""))' "$dir/log-retention.prior.json")"
  if [ "$prior" = "$RETENTION_DAYS" ]; then
    _log "SKIP retention — _Default already at ${RETENTION_DAYS} days (idempotent)"
    return 0
  fi
  _log "retention: _Default ${prior:-unknown} -> ${RETENTION_DAYS} days"
  run gcloud logging buckets update _Default --location=global \
    --project="$SIG_GCP_PROJECT" --retention-days="$RETENTION_DAYS"
  _log "  rollback: gcloud logging buckets update _Default --location=global --retention-days=${prior:-30}"
  gcloud logging buckets describe _Default --location=global \
    --project="$SIG_GCP_PROJECT" --format=json > "$dir/log-retention.after.json"
}

act_versioning() {
  if [ "$MODE" = "check" ]; then
    _plan "gcloud storage buckets describe gs://${SIG_BUCKET_RESTRICTED}  # capture versioning posture"
    _plan "gcloud storage buckets update gs://${SIG_BUCKET_RESTRICTED} --versioning"
    _plan "  # covers ops/probes/ + ops/runs/ on the restricted bucket (G1-05;"
    _plan "  # append-only — prior probe evidence stays tamper-evident)"
    _plan "  rollback: gcloud storage buckets update gs://${SIG_BUCKET_RESTRICTED} --no-versioning"
    return 0
  fi
  assert_window versioning
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
    --format=json > "$dir/restricted-bucket.prior.json"
  local prior
  prior="$(python3 -c 'import json,sys; print((json.load(open(sys.argv[1])).get("versioning") or {}).get("enabled", False))' "$dir/restricted-bucket.prior.json")"
  if [ "$prior" = "True" ]; then
    _log "SKIP versioning — gs://${SIG_BUCKET_RESTRICTED} already versioned (idempotent)"
    return 0
  fi
  _log "versioning: enabling on gs://${SIG_BUCKET_RESTRICTED} (ops/probes/ + ops/runs/)"
  run gcloud storage buckets update "gs://${SIG_BUCKET_RESTRICTED}" --versioning
  _log "  rollback: gcloud storage buckets update gs://${SIG_BUCKET_RESTRICTED} --no-versioning"
  gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
    --format=json > "$dir/restricted-bucket.after.json"
}

act_proberoll() {
  local tag="${SIG_ALERTING_IMAGE_TAG:-${SIG_API_IMAGE}:p35-2-$(git rev-parse --short=8 HEAD)}"
  if [ "$MODE" = "check" ]; then
    _plan "publish declaration bundle (bundle leg) + assert SIG_OPS_DECLARED_GCS"
    _plan "  env on ${SIG_RUN_JOB_PROBE}: --update-env-vars SIG_OPS_DECLARED_GCS=${DECLARED_GCS_URI}"
    _plan "git archive --format=tar.gz HEAD > <tmp>/ctx.tgz && gcloud builds submit <tmp>/ctx.tgz"
    _plan "  --config <tmp>/cloudbuild.yaml   # docker build -f ops/Dockerfile -t ${tag}"
    _plan "pin_image_digest ${tag} -> <repo>@sha256:<digest>      (never :latest, ADR-111)"
    _plan "uv run sig-ops roll-jobs --job ${SIG_RUN_JOB_PROBE} --image <digest> --apply --record <dir>/proberoll.record.json"
    _plan "  rollback: sig-ops roll-jobs --job ${SIG_RUN_JOB_PROBE} --image <recorded before_digest>"
    return 0
  fi
  assert_window proberoll
  act_bundle
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  local env_now
  env_now="$(_probe_job_env SIG_OPS_DECLARED_GCS)"
  if [ "$env_now" != "$DECLARED_GCS_URI" ]; then
    _log "proberoll: asserting SIG_OPS_DECLARED_GCS=${DECLARED_GCS_URI} (was '${env_now:-unset}')"
    run gcloud run jobs update "$SIG_RUN_JOB_PROBE" \
      --project "$SIG_GCP_PROJECT" --region "$SIG_GCP_REGION" \
      "--update-env-vars=SIG_OPS_DECLARED_GCS=${DECLARED_GCS_URI}"
  else
    _log "proberoll: SIG_OPS_DECLARED_GCS already set — env assert is idempotent"
  fi
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
    echo "alerting.sh: image build failed — nothing rolled" >&2
    exit 5
  fi
  rm -rf "${tmp}"
  local digest
  digest="$(pin_image_digest "$tag")" || exit 5
  _log "proberoll: pinned ${digest}"
  if ! _sigops sig-ops roll-jobs --job "$SIG_RUN_JOB_PROBE" --image "$digest" \
      --record "$dir/proberoll.record.json" --apply; then
    echo "alerting.sh: roll-jobs failed; the record names the rollback digest" >&2
    exit 5
  fi
  _probe_job_image > "$dir/sig-probe.image.after.txt"
  _log "proberoll: job image now $(cat "$dir/sig-probe.image.after.txt")"
  _log "proberoll: targets ride the bundle — the next sweep reads cadence from"
  _log "  ${DECLARED_GCS_URI} first, the image's baked copy last (G1-02a)"
}

act_verify() {
  local dir="$FROM_STATE"
  if [ -z "$dir" ]; then
    dir="$(_evidence_dir verify)"
    if [ "$MODE" = "check" ]; then
      _plan "capture the posture rows -> $dir, then"
      _plan "sig-ops monitoring-defs verify --from-state $dir --project <p>"
      _plan "+ _Default retention=90 + restricted versioning + sig-probe pin/env"
      _plan "+ sig-alerts digest pin (§3.3); exit 1 on any non-OK"
      return 0
    fi
    mkdir -p "$dir"
    _log "verify: live reads -> $dir"
    _capture_lists "$dir"
    gcloud logging buckets describe _Default --location=global \
      --project="$SIG_GCP_PROJECT" --format=json > "$dir/log-retention.json" \
      2>/dev/null || echo '{"retentionDays":null}' > "$dir/log-retention.json"
    gcloud storage buckets describe "gs://${SIG_BUCKET_RESTRICTED}" \
      --format=json > "$dir/restricted-bucket.json" \
      2>/dev/null || echo '{}' > "$dir/restricted-bucket.json"
    _probe_job_image > "$dir/sig-probe.image.txt" 2>/dev/null \
      || echo "unread" > "$dir/sig-probe.image.txt"
    _probe_job_env SIG_OPS_DECLARED_GCS > "$dir/sig-probe.declared-env.txt" \
      2>/dev/null || echo "" > "$dir/sig-probe.declared-env.txt"
    _service_image "$SIG_ALERTS_SERVICE" > "$dir/sig-alerts.image.txt" \
      2>/dev/null || echo "unread" > "$dir/sig-alerts.image.txt"
  else
    [ -d "$dir" ] || { echo "alerting.sh: --from-state '$dir' is not a directory" >&2; exit 66; }
    echo "verify: from-state $dir"
  fi
  local rc=0
  _sigops sig-ops monitoring-defs verify --defs "$DEFS_DIR" --from-state "$dir" \
    --project "$SIG_GCP_PROJECT" || rc=$?
  local extra_bad=0
  # _Default retention = 90
  if [ -f "$dir/log-retention.json" ]; then
    local days
    days="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("retentionDays",""))' \
      "$dir/log-retention.json" 2>/dev/null || echo unread)"
    if [ "$days" = "90" ]; then
      echo "OK retention/_Default — retentionDays=90"
    else
      echo "DRIFT retention/_Default — retentionDays=${days:-unread}"
      extra_bad=$((extra_bad + 1))
    fi
  fi
  # restricted bucket versioning (ops/probes/ + ops/runs/)
  if [ -f "$dir/restricted-bucket.json" ]; then
    local ver
    ver="$(python3 -c 'import json,sys; print((json.load(open(sys.argv[1])).get("versioning") or {}).get("enabled", False))' \
      "$dir/restricted-bucket.json" 2>/dev/null || echo unread)"
    if [ "$ver" = "True" ]; then
      echo "OK bucket/${SIG_BUCKET_RESTRICTED} — versioning enabled"
    else
      echo "DRIFT bucket/${SIG_BUCKET_RESTRICTED} — versioning=${ver}"
      extra_bad=$((extra_bad + 1))
    fi
  fi
  # sig-probe: pinned image + the declared-bundle env (targets out of the image)
  if [ -f "$dir/sig-probe.image.txt" ]; then
    local img
    img="$(cat "$dir/sig-probe.image.txt")"
    case "$img" in
      *@sha256:*) echo "OK job/sig-probe — pinned ${img}" ;;
      *) echo "DRIFT job/sig-probe — unpinned image ${img}"; extra_bad=$((extra_bad + 1)) ;;
    esac
  fi
  if [ -f "$dir/sig-probe.declared-env.txt" ]; then
    local declared
    declared="$(cat "$dir/sig-probe.declared-env.txt")"
    if [ "$declared" = "$DECLARED_GCS_URI" ]; then
      echo "OK job/sig-probe env — SIG_OPS_DECLARED_GCS=${declared}"
    else
      echo "DRIFT job/sig-probe env — SIG_OPS_DECLARED_GCS='${declared:-unset}'"
      extra_bad=$((extra_bad + 1))
    fi
  fi
  # sig-alerts: the record is digest-pinned (§3.3 — never :latest)
  if [ -f "$dir/sig-alerts.image.txt" ]; then
    local aimg
    aimg="$(cat "$dir/sig-alerts.image.txt")"
    case "$aimg" in
      *@sha256:*) echo "OK service/sig-alerts — digest-pinned ${aimg}" ;;
      unread|"") echo "SKIP service/sig-alerts — unread (record kept; P35.1b owns the service)" ;;
      *) echo "DRIFT service/sig-alerts — non-digest image ${aimg} (§3.3)"; extra_bad=$((extra_bad + 1)) ;;
    esac
  fi
  if [ "$extra_bad" -gt 0 ] || [ "$rc" -ne 0 ]; then
    return 1
  fi
  return 0
}

# ---- dispatch ---------------------------------------------------------------

_log "=============================================================="
_log "SIG alerting roll — P35.2 (mode=${MODE} action=${ACTION})"
_log "  project=${SIG_GCP_PROJECT:-<unset>} region=${SIG_GCP_REGION}"
_log "=============================================================="

case "$MODE" in
  check)
    require_project   # tolerates unset in check mode (placeholder in PLANs)
    case "$ACTION" in
      all)
        act_prestate; act_bundle; act_policies; act_uptime
        act_retention; act_versioning; act_proberoll; act_verify
        ;;
      prestate) act_prestate ;;
      bundle) act_bundle ;;
      policies) act_policies ;;
      uptime) act_uptime ;;
      retention) act_retention ;;
      versioning) act_versioning ;;
      proberoll) act_proberoll ;;
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
      bundle) act_bundle ;;
      policies) act_policies ;;
      uptime) act_uptime ;;
      retention) act_retention ;;
      versioning) act_versioning ;;
      proberoll) act_proberoll ;;
      all)
        act_prestate
        act_bundle
        act_policies
        act_uptime
        act_retention
        act_versioning
        act_proberoll
        _log "-- post-state capture + verify --"
        act_verify
        ;;
    esac
    ;;
esac
