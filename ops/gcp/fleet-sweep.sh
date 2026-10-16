#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/fleet-sweep.sh — the P35.1b fleet-hygiene sweep (ticket 291, the
# sweep half of the split): the recorded, name-checked deletion of six cruft
# Cloud Run jobs, the Artifact Registry cleanup policy on the `sig` repo, the
# four live cron corrections, the sig-export stale-args guard roll, and the
# sig-alerts disposition — each a gated leg over one evidence dir.
#
#   ./fleet-sweep.sh --check [ACTION]            # (default) plan-only: prints
#                                                # every action, needs NO ADC,
#                                                # opens NO network, exits 0.
#   ./fleet-sweep.sh --apply ACTION              # windowed + ADC + author-gated;
#                                                # mutates for real.
#   ./fleet-sweep.sh --apply all                 # the full contract order.
#   ./fleet-sweep.sh --apply rollback            # replay the recorded recipes —
#                                                # restores prior cron schedules
#                                                # and prints per-job recreation
#                                                # specs; never window-gated.
#
# ACTIONS (the ticket's leg order): prestate → backup → cron → export-guard →
# ar-dryrun → delete → ar-apply → alerts → proof. Read-only legs (prestate,
# ar-dryrun's local evaluation, proof) still run in-window under --apply: the
# whole sweep is one windowed act.
#
# Gates (fail-closed, in order): closed target set parsed + drift-checked from
# ops/cadence.toml → project → window (a weekday 14:00–20:00Z slot, the AR-3 +
# AR-2 contract window; SIG_SWEEP_NOW overrides the clock for the offline test)
# → ADC → SIG_SWEEP_AUTHOR (the recorded operator id every mutating apply
# needs, OM-20's scope discipline) → per-leg evidence preconditions (a delete
# runs only behind a fresh describe; ar-apply runs only behind the recorded
# ar-dryrun candidates set). Every refusal prints the OM-19 re-run prompt and
# exits 42; a missing ADC exits 3; drift/contract violations exit 2.
#
# The closed sets (drift in cadence.toml refuses, never reconciles):
#   * six retired jobs — parsed from [[retired_jobs]] and required to equal
#     the contract's names exactly;
#   * four cron targets — scheduler + corrected cron pinned against cadence's
#     declared values (the prior offending schedules are recorded for the
#     delta column + rollback);
#   * three manual jobs — required on [[manual_jobs]], verified live, never
#     triggered or deleted;
#   * one service — sig-alerts, disposed per SIG_SWEEP_ALERTS_DISPOSITION.
#
# Evidence (EVIDENCE_DIR, default ${SIG_SWEEP_STATE_DIR}): every capture is
# sha256-sidecarred; deletes carry the pre-delete describe (json + yaml — the
# recreation recipe); the AR dry-run candidate set is recorded BEFORE apply;
# the sig-alerts teardown carries its last describe + IAM policy.
#
# SIG_SWEEP_ALERTS_DISPOSITION: `retire` (delete the service — refused unless
# live Monitoring coverage is captured: ≥1 alert policy AND ≥1 notification
# channel) or `rebuild` (redeploy on SIG_SWEEP_ALERT_IMAGE pinned to a digest
# running the repo-owned `sig-ops alert-serve` receiver, allUsers invoker
# removed, run.invoker bound to the probe SA — callers then need the OIDC
# path WebhookNotifier's SIG_ALERT_WEBHOOK_IAM=1 mode adds).
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true

ACTION="all"
EVIDENCE_DIR="${SIG_SWEEP_STATE_DIR}"
while [ $# -gt 0 ]; do
  case "$1" in
    prestate|backup|cron|export-guard|ar-dryrun|delete|ar-apply|alerts|proof|rollback|all)
      ACTION="$1"; shift ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    *) _log "usage: $(basename "$0") [--check|--dry-run|--apply] [ACTION] [--evidence-dir DIR]" >&2
       _log "  ACTION: prestate|backup|cron|export-guard|ar-dryrun|delete|ar-apply|alerts|proof|rollback|all" >&2
       exit 64 ;;
  esac
done
[ -n "${EVIDENCE_DIR}" ] || { _log "fleet-sweep.sh: empty --evidence-dir" >&2; exit 64; }

_repo="$(cd "${_here}/../.." && pwd)"
# SIG_SWEEP_CADENCE_TOML is the offline test seam — a fixture copy the
# drift-refusal tests point at. Unset, the leg reads the committed file.
CADENCE_TOML="${SIG_SWEEP_CADENCE_TOML:-${SIG_CADENCE_TOML}}"
case "${CADENCE_TOML}" in
  /*) ;;
  *) CADENCE_TOML="${_repo}/${CADENCE_TOML}" ;;
esac
POLICY_FILE="${_here}/ar-cleanup-policy.json"
# AR_REPO_URI is recomputed after require_project — config.sh expanded it with
# a possibly-unset SIG_GCP_PROJECT before the check-mode placeholder lands.

RERUN='implement-spec spec=docs/tickets/291_P35.1b__fleet-hygiene.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

_sha256() {
  if command -v sha256sum >/dev/null 2>/dev/null; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_sha256_rec() {
  printf '%s  %s\n' "$(_sha256 "$1")" "${1#"${EVIDENCE_DIR}/"}"
}

_capture() {  # _capture <file> <cmd...> — a read-only capture under evidence/
  local out="${EVIDENCE_DIR}/$1"
  shift
  mkdir -p "$(dirname "${out}")"
  _log "+ (capture) $* > ${out}"
  if ! "$@" > "${out}" 2> "${out}.err"; then
    _log "   (captured non-zero exit; see ${out}.err)"
  fi
  _sha256_rec "${out}" >> "${EVIDENCE_DIR}/sha256s.txt"
}

# --- the closed contract tables ----------------------------------------------
# `read_retired_jobs` — the six-name deletion contract: [[retired_jobs]] must
# equal EXACTLY these names (any drift — missing, renamed, extra — refuses;
# a name-checked set can never widen silently).
read_retired_jobs() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

CONTRACT = [
    "aspi-egress-probe",
    "ccops-sf-egress-probe",
    "muckrock-egress-probe",
    "okc-doc-egress-probe",
    "sig-ingest-resume-test",
    "sig-sink-bench",
]


def refuse(msg: str) -> "SystemExit":
    print(f"REFUSED: {msg}", file=sys.stderr)
    return SystemExit(2)


with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)

rows = doc.get("retired_jobs", [])
names = [r.get("job", "") for r in rows]
if sorted(names) != sorted(CONTRACT):
    raise refuse(
        f"[[retired_jobs]] names {sorted(names)} — the contract set is exactly "
        f"{sorted(CONTRACT)}; the sweep deletes names, never a pattern"
    )
for r in rows:
    if not r.get("reason"):
        raise refuse(f"[[retired_jobs]] {r.get('job', '?')}: missing reason — a retirement is never silent")
for name in CONTRACT:
    print(name)
PY
  )
}

# `read_cron_targets` — the four OR-semantics corrections: id|scheduler|
# declared-cron|prior-offending-cron. cadence.toml must declare the corrected
# cron on the contract's scheduler name; a row already-correct live reads the
# same declared value (idempotent), the prior column is evidence only.
read_cron_targets() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

# id | scheduler | declared cron | the live-offending schedule this corrects
CONTRACT = [
    ("eyes_on_flock", "sig-sched-eyes-on-flock", "0 5 * * 0", "0 5 23 * 0"),
    ("openstates", "sig-sched-openstates", "0 5 * * 2", "0 5 2 * 2"),
    ("congress_gov", "sig-sched-congress-gov", "0 5 3 * *", "0 5 3 * 2"),
    ("sam_gov", "sig-sched-sam-gov", "0 5 * * 1", "0 5 1 * 1"),
]


def refuse(msg: str) -> "SystemExit":
    print(f"REFUSED: {msg}", file=sys.stderr)
    return SystemExit(2)


with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
sources = {s["id"]: s for s in doc.get("sources", [])}
for sid, sched, cron, _prior in CONTRACT:
    row = sources.get(sid)
    if row is None:
        raise refuse(f"cadence.toml has no [[sources]] row for {sid}")
    if row.get("scheduler") != sched:
        raise refuse(f"{sid}: scheduler={row.get('scheduler')!r} != contract {sched!r}")
    if row.get("cron") != cron:
        raise refuse(
            f"{sid}: cadence declares cron={row.get('cron')!r} — the contract's "
            f"corrected schedule is {cron!r} (fix the declaration, not the script)"
        )
    if "cron_or_semantics_ok" in row:
        raise refuse(
            f"{sid} still carries cron_or_semantics_ok — the corrected row "
            "needs no recorded exception"
        )
for row in CONTRACT:
    print("|".join(row))
PY
  )
}

# `read_manual_jobs` — the keep-list: [[manual_jobs]] must name all three.
read_manual_jobs() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

CONTRACT = ["sig-export", "sig-materialize", "sig-replay-ingest"]
with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
names = {m.get("job", "") for m in doc.get("manual_jobs", [])}
missing = [n for n in CONTRACT if n not in names]
if missing:
    print(
        f"REFUSED: [[manual_jobs]] does not declare {missing} — the keep-list "
        "is a contract set",
        file=sys.stderr,
    )
    raise SystemExit(2)
for n in CONTRACT:
    print(n)
PY
  )
}

# --- gates --------------------------------------------------------------------
# `assert_window` — the contract's slot: a weekday 14:00–20:00Z (AR-3 + AR-2).
# Outside it the apply queues (exit 42); check mode is never gated.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dow
  now="${SIG_SWEEP_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  hhmm="${now:11:5}"
  dow="$(date -u -d "${now}" +%u 2>/dev/null \
        || date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${now}" +%u 2>/dev/null \
        || echo 7)"
  if [ "${dow}" -le 5 ] && [[ "${hhmm}" > "13:59" && "${hhmm}" < "20:00" ]]; then
    _log "window OK: ${now} (the contract's weekday 14:00–20:00Z slot)"
    return 0
  fi
  _log "QUEUED (exit 42): ${now} is outside a weekday 14:00–20:00Z slot — the"
  _log "contract's only authorized window. No production mutation ran."
  _log "re-run: ${RERUN}"
  exit 42
}

# `assert_author` — OM-20's pre-authorisation is a scope; every mutating leg
# still records the operator id for THIS apply (silence is never consent).
assert_author() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ -z "${SIG_SWEEP_AUTHOR:-}" ]; then
    _log "QUEUED (exit 42): SIG_SWEEP_AUTHOR is unset — the recorded operator"
    _log "id for this sweep apply (the GATE-G4 OM-20 listing's scope)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  _log "author: ${SIG_SWEEP_AUTHOR} (recorded)"
}

# `assert_backup` — AR-2: the destructive legs run only behind the recorded,
# verified-SUCCESSFUL on-demand backup.
assert_backup() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ ! -f "${EVIDENCE_DIR}/backup/verified.txt" ]; then
    _log "REFUSED: no verified AR-2 backup under ${EVIDENCE_DIR}/backup/ —" >&2
    _log "run '--apply backup' first; destructive legs never precede the restore point." >&2
    exit 2
  fi
}

# `assert_describe <job>` — every delete is preceded by a fresh describe
# (json + yaml) saved verbatim — the recreation recipe (OM-14 / AR-2).
capture_job_prestate() {
  local name="$1"
  _capture "delete/pre-${name}.json" gcloud run jobs describe "${name}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture "delete/pre-${name}.yaml" gcloud run jobs describe "${name}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format yaml
}

# --- the legs ------------------------------------------------------------------
do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the sweep's restore-point captures (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "date -u + branch/sha > pre/{date-start,git}.txt"
    _plan "gcloud run jobs list > pre/run-jobs.json"
    _plan "gcloud run jobs describe <six retired + three manual> > pre/job-*.json|.yaml"
    _plan "gcloud run jobs get-iam-policy <six retired> > pre/iam-job-*.json"
    _plan "gcloud scheduler jobs list > pre/scheduler-jobs.json"
    _plan "gcloud scheduler jobs describe <four cron targets> > pre/trigger-*.json"
    _plan "gcloud artifacts docker images list ${AR_REPO_URI} --include-tags > pre/ar-images.json"
    _plan "gcloud run services describe + get-iam-policy ${SIG_ALERTS_SERVICE} > pre/alerts-*"
    _plan "sig-ops live-diff --live > pre/live-diff.txt (best-effort — a read error is evidence)"
    _plan "sha256 sidecars over every capture > sha256s.txt"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/pre"
  : > "${EVIDENCE_DIR}/sha256s.txt"
  date -u +%Y-%m-%dT%H:%M:%SZ > "${EVIDENCE_DIR}/pre/date-start.txt"
  { git -C "${_repo}" rev-parse --abbrev-ref HEAD
    git -C "${_repo}" rev-parse HEAD; } > "${EVIDENCE_DIR}/pre/git.txt"
  _sha256_rec "${EVIDENCE_DIR}/pre/date-start.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _sha256_rec "${EVIDENCE_DIR}/pre/git.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _capture pre/run-jobs.json gcloud run jobs list \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture pre/scheduler-jobs.json gcloud scheduler jobs list \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture pre/ar-images.json gcloud artifacts docker images list "${AR_REPO_URI}" \
    --project "${SIG_GCP_PROJECT}" --include-tags --format json
  local job
  while read -r job; do
    _capture "pre/job-${job}.json" gcloud run jobs describe "${job}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
    _capture "pre/job-${job}.yaml" gcloud run jobs describe "${job}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format yaml
    _capture "pre/iam-job-${job}.json" gcloud run jobs get-iam-policy "${job}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  done <<<"${RETIRED}"
  while read -r job; do
    _capture "pre/job-${job}.json" gcloud run jobs describe "${job}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  done <<<"${MANUAL}"
  local sid sched cron prior
  while IFS='|' read -r sid sched cron prior; do
    _capture "pre/trigger-${sched}.json" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  done <<<"${CRONS}"
  _capture pre/alerts-service.json gcloud run services describe "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture pre/alerts-service.yaml gcloud run services describe "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format yaml
  _capture pre/alerts-iam.json gcloud run services get-iam-policy "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  # The pre-sweep live-diff baseline — best-effort (a read error is recorded,
  # never converted to clean state).
  (cd "${_repo}" && uv run --quiet sig-ops live-diff --live) \
    > "${EVIDENCE_DIR}/pre/live-diff.txt" 2>&1 \
    || _log "   (pre-sweep live-diff exited non-zero; the output is captured)"
  _sha256_rec "${EVIDENCE_DIR}/pre/live-diff.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _log "   prestate recorded under ${EVIDENCE_DIR}/pre (date -u: $(date -u +%FT%TZ))"
}

do_backup() {
  _log "-- backup ($(date -u +%FT%TZ)): the AR-2 on-demand restore point --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud sql backups create --instance ${SIG_SQL_INSTANCE} --async → poll → SUCCESSFUL"
    _plan "gcloud sql backups list -l1 > backup/backup.json; status!=SUCCESSFUL → exit 5 (OM-20 void)"
    _plan "gcloud storage buckets describe gs://${SIG_BUCKET_RESTRICTED} versioning (AR-2's bucket clause)"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/backup"
  _capture backup/bucket-versioning.txt gcloud storage buckets describe \
    "gs://${SIG_BUCKET_RESTRICTED}" --format='value(versioning.enabled)'
  local ver; ver="$(cat "${EVIDENCE_DIR}/backup/bucket-versioning.txt" 2>/dev/null || true)"
  if [ "${ver}" != "Enabled" ] && [ "${ver}" != "True" ] && [ "${ver}" != "true" ]; then
    _log "ERROR: versioning on gs://${SIG_BUCKET_RESTRICTED} reads '${ver}' — AR-2's" >&2
    _log "bucket clause requires it ON before the first sweep record lands. Refusing." >&2
    exit 4
  fi
  local op opname
  op="$(gcloud sql backups create --instance "${SIG_SQL_INSTANCE}" \
        --project "${SIG_GCP_PROJECT}" --async --format=json)" || {
    _log "ERROR: backup create call failed" >&2; exit 5; }
  opname="$(printf '%s' "${op}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
  _log "backup: issued op ${opname} — polling to DONE"
  local i status
  for i in $(seq 1 60); do
    status="$(gcloud sql operations describe "${opname}" \
      --project "${SIG_GCP_PROJECT}" --format='value(status)' 2>/dev/null || true)"
    [ "${status}" = "DONE" ] && break
    sleep 20
  done
  [ "${status:-}" = "DONE" ] || {
    _log "ERROR: backup op ${opname} did not finish — no destructive leg may run (OM-20 void)." >&2
    exit 5; }
  _capture backup/backup.json gcloud sql backups list \
    --instance "${SIG_SQL_INSTANCE}" --project "${SIG_GCP_PROJECT}" \
    --limit=1 --format json
  local rc=0
  python3 - "${EVIDENCE_DIR}/backup/backup.json" <<'PY' || rc=$?
import json
import sys

rows = json.loads(open(sys.argv[1]).read())
newest = rows[0] if rows else {}
ok = newest.get("status") == "SUCCESSFUL" and newest.get("type") in ("ON_DEMAND", "AUTOMATED")
print(f"backup: newest id={newest.get('id')} status={newest.get('status')} type={newest.get('type')}")
if ok:
    open(sys.argv[1].replace("backup.json", "verified.txt"), "w").write(
        f"{newest.get('id')}\n")
sys.exit(0 if ok else 1)
PY
  if [ "${rc}" -ne 0 ]; then
    _log "ERROR: newest backup is not SUCCESSFUL — the restore point failed;" >&2
    _log "OM-20 voided, the sweep stops before any destructive leg." >&2
    exit 5
  fi
  _sha256_rec "${EVIDENCE_DIR}/backup/verified.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _log "   restore point verified (AR-2): $(cat "${EVIDENCE_DIR}/backup/verified.txt")"
}

do_cron() {
  _log "-- cron ($(date -u +%FT%TZ)): the four OR-semantics corrections + keep-list verify --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "verify ${MANUAL//$'\n'/, } on [[manual_jobs]] and live (kept, never triggered)"
    printf '%s\n' "${CRONS}" | while IFS='|' read -r sid sched cron prior; do
      _plan "gcloud scheduler jobs describe ${sched} — if schedule=='${cron}' SKIP; if '${prior}' →"
      _plan "  gcloud scheduler jobs update http ${sched} --schedule '${cron}' --time-zone=Etc/UTC"
    done
    return 0
  fi
  local job sid sched cron prior got
  while read -r job; do
    _capture "cron/keep-${job}.json" gcloud run jobs describe "${job}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --format='value(metadata.name)'
    grep -q "${job}" "${EVIDENCE_DIR}/cron/keep-${job}.json" \
      || { _log "REFUSED: keep-list job ${job} is not live — the manual allow-list" >&2
           _log "covers only a real, deployed manual job." >&2; exit 2; }
    _log "  keep-list: ${job} live + on [[manual_jobs]]"
  done <<<"${MANUAL}"
  while IFS='|' read -r sid sched cron prior; do
    _capture "cron/pre-${sched}.json" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
    got="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("schedule",""))' \
      "${EVIDENCE_DIR}/cron/pre-${sched}.json" 2>/dev/null || true)"
    if [ "${got}" = "${cron}" ]; then
      _log "  ${sched} (${sid}): already '${cron}' — skip (idempotent)"
      continue
    fi
    _log "  ${sched} (${sid}): live '${got:-<unreadable>}' → '${cron}' (was '${prior}')"
    run gcloud scheduler jobs update http "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${cron}" --time-zone=Etc/UTC
    _capture "cron/post-${sched}.json" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
    local rb
    rb="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("schedule",""))' \
      "${EVIDENCE_DIR}/cron/post-${sched}.json" 2>/dev/null || true)"
    if [ "${rb}" != "${cron}" ]; then
      _log "ERROR: ${sched} read-back '${rb}' != applied '${cron}' — the sweep stops" >&2
      _log "(no silent reconcile; rollback replays the recorded pre-state)." >&2
      exit 2
    fi
    _log "  ${sched}: read-back '${rb}' verified"
    printf '%s|%s|%s|%s\n' "${sid}" "${sched}" "${got}" "${cron}" \
      >> "${EVIDENCE_DIR}/cron/corrections.txt"
    _sha256_rec "${EVIDENCE_DIR}/cron/corrections.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  done <<<"${CRONS}"
}

do_export_guard() {
  _log "-- export-guard ($(date -u +%FT%TZ)): roll the exit-64 baked args onto ${SIG_EXPORT_JOB:-sig-export} --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run jobs update ${SIG_EXPORT_JOB:-sig-export} --command sh --args '-c,<SIG_EXPORT_GUARD>'"
    _plan "  (the guard: a bare execute exits 64 — export.sh run supplies the real args)"
    return 0
  fi
  local job="${SIG_EXPORT_JOB:-sig-export}"
  _capture export-guard/pre.json gcloud run jobs describe "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  run gcloud run jobs update "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --command sh --args "-c,${SIG_EXPORT_GUARD}"
  _capture export-guard/post.json gcloud run jobs describe "${job}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  python3 - "${EVIDENCE_DIR}/export-guard/post.json" <<'PY'
import json
import sys

d = json.loads(open(sys.argv[1]).read())
args = d.get("template", {}).get("template", {}).get("containers", [{}])[0].get("args", [])
joined = " ".join(args)
if "exit 64" not in joined:
    print(f"REFUSED: post-state args for the export job lack the exit-64 guard: {args!r}",
          file=sys.stderr)
    sys.exit(2)
print("  export-guard: post-state args carry the exit-64 refusal")
PY
}

do_ar_dryrun() {
  _log "-- ar-dryrun ($(date -u +%FT%TZ)): the candidate delete set, recorded before apply --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "capture AR image list → ar/images.json; live-referenced digests → ar/digests.txt"
    _plan "sig-ops ar-cleanup merged-policy → ar/merged-policy.json (static + keep-live-referenced)"
    _plan "sig-ops ar-cleanup candidates → ar/candidates.json (the eyeballed set)"
    _plan "refuse when a candidate is live-referenced (the merged keep must cover it)"
    _plan "gcloud artifacts repositories set-cleanup-policies ${SIG_AR_REPO} --policy=... --dry-run"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/ar"
  _capture ar/images.json gcloud artifacts docker images list "${AR_REPO_URI}" \
    --project "${SIG_GCP_PROJECT}" --include-tags --format json
  _capture ar/run-jobs.json gcloud run jobs list \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture ar/run-services.json gcloud run services list \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture ar/run-revisions.json gcloud run revisions list \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  (cd "${_repo}" && uv run python - "${EVIDENCE_DIR}/ar" <<'PY'
import pathlib
import sys

from ops.ar_cleanup import referenced_digests

d = pathlib.Path(sys.argv[1])
bodies = [
    (d / "run-jobs.json").read_text(),
    (d / "run-services.json").read_text(),
    (d / "run-revisions.json").read_text(),
]
(d / "digests.txt").write_text("\n".join(referenced_digests(*bodies)) + "\n")
PY
  ) || { _log "ERROR: digest extraction failed" >&2; exit 2; }
  _sha256_rec "${EVIDENCE_DIR}/ar/digests.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _sigops ar-cleanup merged-policy --policy "${POLICY_FILE}" \
    --digests "${EVIDENCE_DIR}/ar/digests.txt" > "${EVIDENCE_DIR}/ar/merged-policy.json"
  _sha256_rec "${EVIDENCE_DIR}/ar/merged-policy.json" >> "${EVIDENCE_DIR}/sha256s.txt"
  _sigops ar-cleanup candidates --policy "${EVIDENCE_DIR}/ar/merged-policy.json" \
    --images "${EVIDENCE_DIR}/ar/images.json" > "${EVIDENCE_DIR}/ar/candidates.json"
  _sha256_rec "${EVIDENCE_DIR}/ar/candidates.json" >> "${EVIDENCE_DIR}/sha256s.txt"
  # Fail closed: a candidate that is live-referenced means the merged keep did
  # not cover it — never apply on top of that.
  python3 - "${EVIDENCE_DIR}/ar/candidates.json" "${EVIDENCE_DIR}/ar/digests.txt" <<'PY'
import json
import sys

cands = json.loads(open(sys.argv[1]).read())["candidates"]
refs = {ln.strip() for ln in open(sys.argv[2]) if ln.strip()}
clash = [c for c in cands if c["version"] in refs]
if clash:
    print(
        f"REFUSED: {len(clash)} candidate(s) are live-referenced — the merged "
        "keep-live-referenced policy did not cover them; ar-apply must not run.",
        file=sys.stderr,
    )
    sys.exit(2)
print(f"  dry-run: {len(cands)} candidate(s), 0 live-referenced — the eyeball record")
PY
  run gcloud artifacts repositories set-cleanup-policies "${SIG_AR_REPO}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --policy "${EVIDENCE_DIR}/ar/merged-policy.json" --dry-run
}

do_delete() {
  assert_backup
  _log "-- delete ($(date -u +%FT%TZ)): the six name-checked cruft jobs --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '%s\n' "${RETIRED}" | while read -r job; do
      _plan "describe ${job} (fresh json+yaml recreation recipe) → gcloud run jobs delete ${job} --quiet"
    done
    _plan "a job not on the [[retired_jobs]] contract list is never touched; absent → recorded skip"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/delete"
  local job
  while read -r job; do
    if ! gcloud run jobs describe "${job}" --region "${SIG_GCP_REGION}" \
        --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "  ${job}: already absent — recorded skip (the declare stays)"
      printf 'absent %s\n' "${job}" >> "${EVIDENCE_DIR}/delete/deleted.txt"
      continue
    fi
    capture_job_prestate "${job}"
    run gcloud run jobs delete "${job}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet
    # The absence read-back is the deletion's proof.
    if gcloud run jobs describe "${job}" --region "${SIG_GCP_REGION}" \
        --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "ERROR: ${job} still describes after delete — the sweep stops (no silent deletes)." >&2
      exit 2
    fi
    printf 'deleted %s\n' "${job}" >> "${EVIDENCE_DIR}/delete/deleted.txt"
    _log "  ${job}: deleted (describe → delete → absent read-back)"
  done <<<"${RETIRED}"
  [ -f "${EVIDENCE_DIR}/delete/deleted.txt" ] && \
    _sha256_rec "${EVIDENCE_DIR}/delete/deleted.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
}

do_ar_apply() {
  assert_backup
  _log "-- ar-apply ($(date -u +%FT%TZ)): the cleanup policy goes live --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "require ar/candidates.json (the recorded dry-run) then:"
    _plan "gcloud artifacts repositories describe ${SIG_AR_REPO} → ar/pre-policy.json"
    _plan "gcloud artifacts repositories set-cleanup-policies ${SIG_AR_REPO} --policy=ar/merged-policy.json --no-dry-run"
    _plan "describe → ar/post-policy.json; assert cleanupPolicyDryRun=false + policies present"
    return 0
  fi
  if [ ! -f "${EVIDENCE_DIR}/ar/candidates.json" ] || [ ! -f "${EVIDENCE_DIR}/ar/merged-policy.json" ]; then
    _log "REFUSED: no recorded dry-run under ${EVIDENCE_DIR}/ar/ — run '--apply ar-dryrun'" >&2
    _log "first; the candidate set must be recorded before apply (the eyeball gate)." >&2
    exit 2
  fi
  _capture ar/pre-policy.json gcloud artifacts repositories describe "${SIG_AR_REPO}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  run gcloud artifacts repositories set-cleanup-policies "${SIG_AR_REPO}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --policy "${EVIDENCE_DIR}/ar/merged-policy.json" --no-dry-run
  _capture ar/post-policy.json gcloud artifacts repositories describe "${SIG_AR_REPO}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  python3 - "${EVIDENCE_DIR}/ar/post-policy.json" <<'PY'
import json
import sys

d = json.loads(open(sys.argv[1]).read())
policies = d.get("cleanupPolicies") or {}
dry = d.get("cleanupPolicyDryRun", True)
if dry or not policies:
    print(
        f"REFUSED: post-apply describe shows dryRun={dry}, policies={list(policies)} — "
        "the policy did not land as expected",
        file=sys.stderr,
    )
    sys.exit(2)
print(f"  ar-apply: {len(policies)} policies live, dryRun=false")
PY
}

do_alerts() {
  assert_backup
  local disp="${SIG_SWEEP_ALERTS_DISPOSITION:-}"
  _log "-- alerts ($(date -u +%FT%TZ)): the ${SIG_ALERTS_SERVICE} disposition (${disp:-unset}) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "capture ${SIG_ALERTS_SERVICE} describe json+yaml + IAM policy → alerts/pre-*"
    _plan "capture gcloud monitoring policies + beta monitoring channels → alerts/monitoring-*"
    _plan "SIG_SWEEP_ALERTS_DISPOSITION=retire → delete the service (refused when"
    _plan "  the captured Monitoring coverage is empty — nothing would deliver)"
    _plan "SIG_SWEEP_ALERTS_DISPOSITION=rebuild → gcloud run deploy ${SIG_ALERTS_SERVICE}"
    _plan "  --image <SIG_SWEEP_ALERT_IMAGE pinned digest> --command sig-ops --args alert-serve"
    _plan "  --no-allow-unauthenticated --service-account ${SIG_ALERTS_SA_EMAIL}"
    _plan "  + remove-iam-policy-binding allUsers + add run.invoker for ${SIG_SA_PROBE}"
    _plan "  + run jobs update ${SIG_RUN_JOB_PROBE} --update-env-vars SIG_ALERT_WEBHOOK_IAM=1"
    _plan "    (the probe's alert POSTs then carry a metadata-server OIDC id token)"
    return 0
  fi
  case "${disp}" in
    retire|rebuild) ;;
    *) _log "REFUSED: SIG_SWEEP_ALERTS_DISPOSITION must name retire|rebuild —" >&2
       _log "the disposition is a recorded decision, never a default." >&2
       exit 2 ;;
  esac
  mkdir -p "${EVIDENCE_DIR}/alerts"
  printf '%s %s\n' "$(date -u +%FT%TZ)" "${disp}" > "${EVIDENCE_DIR}/alerts/disposition.txt"
  _sha256_rec "${EVIDENCE_DIR}/alerts/disposition.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _capture alerts/pre.json gcloud run services describe "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture alerts/pre.yaml gcloud run services describe "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format yaml
  _capture alerts/pre-iam.json gcloud run services get-iam-policy "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture alerts/monitoring-policies.json gcloud monitoring policies list \
    --project "${SIG_GCP_PROJECT}" --format json
  # notificationChannels lives on the beta surface (verified live 2026-10-16 —
  # `gcloud monitoring channels` is an invalid choice on the GA track).
  _capture alerts/monitoring-channels.json gcloud beta monitoring channels list \
    --project "${SIG_GCP_PROJECT}" --format json
  if [ "${disp}" = "retire" ]; then
    python3 - "${EVIDENCE_DIR}/alerts/monitoring-policies.json" \
        "${EVIDENCE_DIR}/alerts/monitoring-channels.json" <<'PY'
import json
import sys

policies = json.loads(open(sys.argv[1]).read() or "[]")
channels = json.loads(open(sys.argv[2]).read() or "[]")
if not policies or not channels:
    print(
        "REFUSED: retire needs the Monitoring path demonstrably delivering — "
        f"captured {len(policies)} alert policies / {len(channels)} channels; "
        "with either empty, rebuild is the disposition (or the retire waits "
        "on P34.4's coverage).",
        file=sys.stderr,
    )
    sys.exit(2)
print(f"  retire gate: {len(policies)} policies / {len(channels)} channels — Monitoring covers")
PY
    run gcloud run services delete "${SIG_ALERTS_SERVICE}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet
    if gcloud run services describe "${SIG_ALERTS_SERVICE}" \
        --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "ERROR: ${SIG_ALERTS_SERVICE} still describes after delete." >&2
      exit 2
    fi
    _log "  ${SIG_ALERTS_SERVICE}: retired (deleted; pre-state + IAM captured)"
    return 0
  fi
  # rebuild — the repo-owned receiver on a pinned digest, private invoker.
  local image="${SIG_SWEEP_ALERT_IMAGE:-}"
  if [ -z "${image}" ]; then
    _log "REFUSED: rebuild needs SIG_SWEEP_ALERT_IMAGE (a ${SIG_API_IMAGE}:<tag>" >&2
    _log "or @sha256 — resolved to a pinned digest, never :latest)." >&2
    exit 2
  fi
  image="$(pin_image_digest "${image}")" || exit 2
  run gcloud run deploy "${SIG_ALERTS_SERVICE}" \
    --image "${image}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${SIG_ALERTS_SA_EMAIL}" \
    --command sig-ops --args alert-serve \
    --set-secrets "SIG_ALERT_WEBHOOK_TOKEN=${SIG_SECRET_ALERT_HOOK}:latest" \
    --no-allow-unauthenticated --ingress all --port 8080
  # allUsers off (idempotent — an absent binding's remove is tolerated, recorded).
  run gcloud run services remove-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --member="allUsers" --role=roles/run.invoker || true
  run gcloud run services add-iam-policy-binding "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --member="serviceAccount:${SIG_PROBE_SA_EMAIL}" \
    --role=roles/run.invoker
  # The probe job's alert path flips to the OIDC shape: its POSTs to the
  # now-private service carry a metadata-server id token in Authorization
  # (WebhookNotifier's SIG_ALERT_WEBHOOK_IAM mode, ops/src/ops/alerts.py).
  run gcloud run jobs update "${SIG_RUN_JOB_PROBE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --update-env-vars "SIG_ALERT_WEBHOOK_IAM=1"
  _capture alerts/post.json gcloud run services describe "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture alerts/post-iam.json gcloud run services get-iam-policy "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  python3 - "${EVIDENCE_DIR}/alerts/post.json" "${EVIDENCE_DIR}/alerts/post-iam.json" <<'PY'
import json
import sys

svc = json.loads(open(sys.argv[1]).read())
iam = json.loads(open(sys.argv[2]).read())
image = (
    svc.get("spec", {}).get("template", {}).get("spec", {})
    .get("containers", [{}])[0].get("image", "")
)
members = [
    m
    for b in iam.get("bindings", [])
    if b.get("role") == "roles/run.invoker"
    for m in b.get("members", [])
]
problems = []
if "@sha256:" not in image:
    problems.append(f"post-state image {image!r} is not digest-pinned (SIG-SEC-008)")
if "allUsers" in members:
    problems.append("allUsers still holds run.invoker — the public surface did not close")
if problems:
    print("REFUSED: " + "; ".join(problems), file=sys.stderr)
    sys.exit(2)
print(f"  rebuild verified: {image} digest-pinned; invokers {sorted(members)}")
PY
}

do_proof() {
  _log "-- proof ($(date -u +%FT%TZ)): post-sweep state + the partial live-diff --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "run jobs list → post/run-jobs.json; assert the six names absent"
    _plan "scheduler describes → post/trigger-*.json; assert the four corrected crons"
    _plan "sig-alerts describe + IAM → post/alerts-*; live-diff → post/live-diff.txt"
    _plan "(partial proof: the sweep's own footprint — the dispatcher's 0-drift close is P35.1c's)"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/post"
  _capture post/run-jobs.json gcloud run jobs list \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  local job sid sched cron prior
  while read -r job; do
    if gcloud run jobs describe "${job}" --region "${SIG_GCP_REGION}" \
        --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "ERROR: retired job ${job} still live in poststate — the sweep's proof fails." >&2
      exit 2
    fi
  done <<<"${RETIRED}"
  _log "  retired set: all six absent in poststate"
  while IFS='|' read -r sid sched cron prior; do
    _capture "post/trigger-${sched}.json" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
    local got
    got="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("schedule",""))' \
      "${EVIDENCE_DIR}/post/trigger-${sched}.json" 2>/dev/null || true)"
    [ "${got}" = "${cron}" ] || {
      _log "ERROR: ${sched} poststate schedule '${got}' != declared '${cron}'." >&2; exit 2; }
  done <<<"${CRONS}"
  _log "  cron set: all four read corrected"
  _capture post/alerts-service.json gcloud run services describe "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture post/alerts-iam.json gcloud run services get-iam-policy "${SIG_ALERTS_SERVICE}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  (cd "${_repo}" && uv run --quiet sig-ops live-diff --live) \
    > "${EVIDENCE_DIR}/post/live-diff.txt" 2>&1 \
    || _log "   (post-sweep live-diff exited non-zero; captured — the residual drift list is evidence)"
  _sha256_rec "${EVIDENCE_DIR}/post/live-diff.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  date -u +%Y-%m-%dT%H:%M:%SZ > "${EVIDENCE_DIR}/post/date-end.txt"
  _sha256_rec "${EVIDENCE_DIR}/post/date-end.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _log "   poststate recorded under ${EVIDENCE_DIR}/post"
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): replay the recorded recipes (never window-gated) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "restore each cron/pre-<sched>.json's recorded schedule via scheduler update"
    _plan "print each delete/pre-<job>.yaml + json as the per-job recreation recipe"
    _plan "print the alerts pre-state recipe; AR policies remove via delete-cleanup-policies"
    return 0
  fi
  require_adc
  # Cron restore — non-destructive, run for real.
  local sid sched cron prior f old
  while IFS='|' read -r sid sched cron prior; do
    f="${EVIDENCE_DIR}/cron/pre-${sched}.json"
    [ -f "${f}" ] || { _log "  ${sched}: no recorded pre-state — skipped"; continue; }
    old="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("schedule",""))' "${f}")"
    [ -n "${old}" ] || continue
    run gcloud scheduler jobs update http "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${old}" --time-zone=Etc/UTC
    _log "  ${sched}: restored to recorded '${old}'"
  done <<<"${CRONS}"
  # Deleted jobs — the recorded recipe, never an auto-recreate (a restored
  # cruft job is an operator decision; the recipe is exact).
  local job
  while read -r job; do
    if [ -f "${EVIDENCE_DIR}/delete/pre-${job}.yaml" ]; then
      _log "  recreate recipe for ${job}: ${EVIDENCE_DIR}/delete/pre-${job}.{json,yaml}"
      _log "    (rebuild via \`gcloud run jobs deploy ${job} --image <recorded> …\`"
      _log "     from the captured spec — an operator act, recorded)"
    fi
  done <<<"${RETIRED}"
  # The AR policy — remove exactly the policy names the sweep applied.
  if [ -f "${EVIDENCE_DIR}/ar/merged-policy.json" ]; then
    local names
    names="$(python3 -c 'import json,sys; print(",".join(p["name"] for p in json.load(open(sys.argv[1]))))' \
      "${EVIDENCE_DIR}/ar/merged-policy.json")"
    _plan "AR rollback: gcloud artifacts repositories delete-cleanup-policies ${SIG_AR_REPO} --policynames=${names}"
    run gcloud artifacts repositories delete-cleanup-policies "${SIG_AR_REPO}" \
      --policynames="${names}" --project "${SIG_GCP_PROJECT}" --location "${SIG_GCP_REGION}"
  fi
  if [ -f "${EVIDENCE_DIR}/alerts/pre.yaml" ]; then
    _log "  ${SIG_ALERTS_SERVICE} recipe: ${EVIDENCE_DIR}/alerts/pre.{json,yaml} + pre-iam.json"
  fi
}

# ---------------------------------------------------------------------------
banner "fleet-hygiene sweep (P35.1b / ticket 291; OM-20 gated)"

require_project
AR_REPO_URI="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}"

# The closed sets — parsed + drift-checked BEFORE any gate or plan.
RETIRED="$(read_retired_jobs)" || exit 2
CRONS="$(read_cron_targets)" || exit 2
MANUAL="$(read_manual_jobs)" || exit 2
SIG_EXPORT_JOB="${SIG_EXPORT_JOB:-sig-export}"
SIG_PROBE_SA_EMAIL="${SIG_SA_PROBE}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
# config.sh expanded these before require_project filled the placeholder —
# recompute so the check plan and applies name the real identity/bucket/image.
SIG_ALERTS_SA_EMAIL="${SIG_SA_ALERTS}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"
SIG_BUCKET_RESTRICTED="${SIG_GCP_PROJECT}-sig-restricted"
SIG_API_IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-api"

if [ "${SIG_GCP_MODE}" = "check" ]; then
  mkdir -p "${EVIDENCE_DIR}"
  {
    _log "closed sets (cadence.toml-verified — drift refuses):"
    printf '%s\n' "${RETIRED}" | while read -r j; do _log "  retired: ${j}"; done
    printf '%s\n' "${CRONS}" | while IFS='|' read -r s sc c p; do
      _log "  cron: ${s} ${sc} '${c}' (was '${p}')"; done
    printf '%s\n' "${MANUAL}" | while read -r j; do _log "  manual keep: ${j}"; done
    _log "  service: ${SIG_ALERTS_SERVICE} (SIG_SWEEP_ALERTS_DISPOSITION=retire|rebuild)"
    _log "leg order: prestate → backup → cron → export-guard → ar-dryrun → delete → ar-apply → alerts → proof"
  } | tee "${EVIDENCE_DIR}/check-targets.txt"
fi

run_leg() {
  case "$1" in
    prestate)     do_prestate ;;
    backup)       do_backup ;;
    cron)         do_cron ;;
    export-guard) do_export_guard ;;
    ar-dryrun)    do_ar_dryrun ;;
    delete)       do_delete ;;
    ar-apply)     do_ar_apply ;;
    alerts)       do_alerts ;;
    proof)        do_proof ;;
    *) _log "fleet-sweep.sh: unknown leg '$1'" >&2; exit 64 ;;
  esac
}

case "${ACTION}" in
  rollback)
    do_rollback
    ;;
  all)
    assert_window
    require_adc
    assert_author
    mkdir -p "${EVIDENCE_DIR}"
    : > "${EVIDENCE_DIR}/sha256s.txt"
    for leg in prestate backup cron export-guard ar-dryrun delete ar-apply alerts proof; do
      run_leg "${leg}"
    done
    ;;
  *)
    assert_window
    require_adc
    case "${ACTION}" in
      cron|export-guard|delete|ar-apply|alerts) assert_author ;;
    esac
    mkdir -p "${EVIDENCE_DIR}"
    touch "${EVIDENCE_DIR}/sha256s.txt"
    run_leg "${ACTION}"
    ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "fleet-sweep ${ACTION}: check OK (mode=${SIG_GCP_MODE}; evidence → ${EVIDENCE_DIR})"
else
  _log "fleet-sweep ${ACTION}: done (mode=${SIG_GCP_MODE}; evidence → ${EVIDENCE_DIR})"
fi
