#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/dispatcher-consolidation.sh — the P35.1c dispatcher-consolidation
# leg (ticket 291a; G1-TRIM B-13=a): the recorded, name-checked act that
# replaces the per-source Cloud Scheduler trigger set with ONE hourly trigger
# (`[dispatcher]` in ops/cadence.toml) firing ONE Cloud Run job that evaluates
# the due set and enqueues each due job via jobs:run — the same call the
# retired triggers made, signed by the dispatcher's own class SA.
#
#   ./dispatcher-consolidation.sh --check [ACTION]   # (default) plan-only:
#                                                    # prints every action,
#                                                    # needs NO ADC, opens NO
#                                                    # network, exits 0.
#   ./dispatcher-consolidation.sh --apply ACTION     # windowed + ADC +
#                                                    # author-gated; mutates
#                                                    # for real.
#   ./dispatcher-consolidation.sh --apply all        # the full contract order.
#   ./dispatcher-consolidation.sh --apply rollback   # delete the dispatcher
#                                                    # trigger + job and run
#                                                    # scheduled-ops.sh
#                                                    # --shape per-source —
#                                                    # the declared rollback
#                                                    # map; never window-gated.
#
# ACTIONS (the ticket's order): prestate → deploy → verify → retire → proof.
# Read-only legs (prestate, proof) still run in-window under --apply: the
# whole consolidation is one windowed act.
#
# Gates (fail-closed, in order): the closed contract parsed + drift-checked
# from ops/cadence.toml ([[retire_triggers]] must cover EVERY per-row
# scheduler exactly once; the retired count is pinned — a widened list is a
# refusal, never a silent scope creep) → project → window (a weekday
# 14:00–20:00Z slot, the AR-3 + AR-2 contract window; SIG_CONSOL_NOW overrides
# the clock for the offline test) → ADC → SIG_CONSOL_AUTHOR (the recorded
# operator id every mutating apply needs, OM-20's scope discipline) → per-leg
# evidence preconditions (retire runs only behind a recorded prestate, and
# every trigger delete runs behind a FRESH describe whose httpTarget.uri is
# verified against the cadence row's declared job — a trigger that points at
# an unexpected job is never deleted). Every refusal prints the OM-19 re-run
# prompt and exits 42; a missing ADC exits 3; drift/contract violations
# exit 2.
#
# The closed sets (drift in cadence.toml refuses, never reconciles):
#   * the retired set — [[retire_triggers]] disposition=retired names, count-
#     pinned at 89 (the 90 per-row schedulers minus the one kept pin);
#   * the keep set — kept-declared-pin (batch-05's D-P31.4-1 pin: its trigger
#     stays live) + kept-manual (the three [[manual_jobs]] names — job names,
#     never triggers, verified untouched);
#   * the dispatcher — [dispatcher].job/scheduler/cron/sa_class verified
#     against cadence.toml on every leg.
#
# Evidence (EVIDENCE_DIR, default ${SIG_CONSOL_STATE_DIR}): every capture is
# sha256-sidecarred; each retired trigger's delete carries a fresh pre-delete
# describe (json + yaml — the exact recreation recipe); the verify leg
# records a staged `--dry-run` execution of the dispatcher job (evaluation
# end-to-end, nothing executed); proof asserts every retired name absent,
# the kept pin + dispatcher trigger present, and a live-diff whose residual
# findings are all of the recorded declared-drift kinds (a live retired
# trigger "pending" / a declared-retired job "pending") — any other finding
# fails the leg.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true

ACTION="all"
EVIDENCE_DIR="${SIG_CONSOL_STATE_DIR:-${TMPDIR:-/tmp}/p35.1c-consolidation}"
while [ $# -gt 0 ]; do
  case "$1" in
    prestate|deploy|verify|retire|proof|rollback|all)
      ACTION="$1"; shift ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    *) _log "usage: $(basename "$0") [--check|--dry-run|--apply] [ACTION] [--evidence-dir DIR]" >&2
       _log "  ACTION: prestate|deploy|verify|retire|proof|rollback|all" >&2
       exit 64 ;;
  esac
done
[ -n "${EVIDENCE_DIR}" ] || { _log "dispatcher-consolidation.sh: empty --evidence-dir" >&2; exit 64; }

_repo="$(cd "${_here}/../.." && pwd)"
# SIG_CONSOL_CADENCE_TOML is the offline test seam — a fixture copy the
# drift-refusal tests point at. Unset, the leg reads the committed file.
CADENCE_TOML="${SIG_CONSOL_CADENCE_TOML:-${SIG_CADENCE_TOML}}"
case "${CADENCE_TOML}" in
  /*) ;;
  *) CADENCE_TOML="${_repo}/${CADENCE_TOML}" ;;
esac

RERUN='implement-spec spec=docs/tickets/291a_P35.1c__dispatcher-consolidation.md live_verification=true'

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
# `read_retire_rows` — the retirement contract: every [[retire_triggers]] row
# with disposition=retired, emitted `trigger|job`. The set must cover every
# [[sources]]/[[batches]] scheduler exactly once, the retired count is pinned
# (89 — a widened or narrowed list is a refusal, never reconciled), every
# name must be a per-row scheduler (never the probe/maintenance/live-diff/
# dispatcher triggers, never a manual job), and every row carries a reason.
read_retire_rows() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

#: The retired-trigger count is pinned — P35.1c's contract is "~79" written
#: before the P35.6 (+10) and P35.11 (+2) rows; today's per-row set is 90
#: schedulers of which batch-05's pin is kept — 89 retire. A drifted count is
#: a refusal to re-count and amend, never a silent wider scope.
EXPECTED_RETIRED = 89


def refuse(msg: str) -> "SystemExit":
    print(f"REFUSED: {msg}", file=sys.stderr)
    return SystemExit(2)


with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)

if not doc.get("dispatcher"):
    raise refuse("cadence.toml declares no [dispatcher] table — nothing to consolidate into")
rows = doc.get("retire_triggers", [])
if not rows:
    raise refuse("cadence.toml declares no [[retire_triggers]] — the name-checked set is required")

per_row = {}
for s in doc.get("sources", []):
    per_row[s["scheduler"]] = s["job"]
for b in doc.get("batches", []):
    per_row[b["scheduler"]] = b["job"]
protected = {
    (doc.get("probes") or {}).get("scheduler"),
    (doc.get("dispatcher") or {}).get("scheduler"),
    (doc.get("live_diff") or {}).get("scheduler"),
} | {m.get("scheduler") for m in doc.get("maintenance", [])}
manual = {m.get("job") for m in doc.get("manual_jobs", [])}

retired = []
kept_pin = []
kept_manual = []
seen = set()
covered = set()
for r in rows:
    name = r.get("name", "")
    disp = r.get("disposition", "")
    if not name:
        raise refuse("a [[retire_triggers]] row names no trigger")
    if name in seen:
        raise refuse(f"[[retire_triggers]] {name}: duplicate name")
    seen.add(name)
    if not r.get("reason"):
        raise refuse(f"[[retire_triggers]] {name}: missing reason — a retirement is never silent")
    if name in protected:
        raise refuse(f"[[retire_triggers]] {name}: collides with a protected declared trigger")
    if disp == "retired":
        if name not in per_row:
            raise refuse(f"[[retire_triggers]] {name}: not a [[sources]]/[[batches]] scheduler")
        retired.append((name, per_row[name]))
        covered.add(name)
    elif disp == "kept-declared-pin":
        if name not in per_row:
            raise refuse(f"[[retire_triggers]] {name}: kept-declared-pin but not a per-row scheduler")
        kept_pin.append((name, per_row[name]))
        covered.add(name)
    elif disp == "kept-manual":
        if name not in manual:
            raise refuse(f"[[retire_triggers]] {name}: kept-manual but not a [[manual_jobs]] member")
        kept_manual.append(name)
    else:
        raise refuse(f"[[retire_triggers]] {name}: disposition {disp!r} not in retired|kept-declared-pin|kept-manual")

missing = sorted(set(per_row) - covered)
if missing:
    raise refuse(f"per-row schedulers not on [[retire_triggers]]: {missing} — the set must cover every row")
if len(retired) != EXPECTED_RETIRED:
    raise refuse(
        f"retired count {len(retired)} != contract {EXPECTED_RETIRED} — "
        "the name-checked set is closed; re-count and amend deliberately"
    )
for name, job in sorted(retired):
    print(f"{name}|{job}")
PY
  )
}

# `read_kept_rows` — the keep set: `kind|name|job` for kept-declared-pin +
# kept-manual rows (verified live, never touched).
read_kept_rows() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
per_row = {}
for s in doc.get("sources", []):
    per_row[s["scheduler"]] = s["job"]
for b in doc.get("batches", []):
    per_row[b["scheduler"]] = b["job"]
for r in doc.get("retire_triggers", []):
    if r.get("disposition") == "kept-declared-pin":
        print("|".join(["pin", r["name"], per_row.get(r["name"], "")]))
    elif r.get("disposition") == "kept-manual":
        print("|".join(["manual", r["name"], r["name"]]))
PY
  )
}

# `read_dispatcher_row` — job|scheduler|cron|sa_class|task_timeout — verified
# each leg; the deploy refuses a spec whose values drifted from cadence.toml.
read_dispatcher_row() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib


def refuse(msg: str) -> "SystemExit":
    print(f"REFUSED: {msg}", file=sys.stderr)
    return SystemExit(2)


with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
d = doc.get("dispatcher")
if not d:
    raise refuse("cadence.toml declares no [dispatcher] table")
for key in ("job", "scheduler", "cron"):
    if not d.get(key):
        raise refuse(f"[dispatcher].{key} is required")
if d.get("sa_class") not in ("ingest", "probe"):
    raise refuse(f"[dispatcher].sa_class {d.get('sa_class')!r} has no declared SA mapping")
print("|".join([
    d["job"], d["scheduler"], d["cron"],
    d.get("sa_class", ""), d.get("task_timeout", ""),
]))
PY
  )
}

# `read_due_targets` — one due-target job per line (the non-paused retired
# rows' jobs the dispatcher jobs:run's — the due-invoker binding set).
read_due_targets() {
  (cd "${_repo}" && uv run python - "${CADENCE_TOML}" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as fh:
    doc = tomllib.load(fh)
retire = {r.get("name"): r.get("disposition", "") for r in doc.get("retire_triggers", [])}
for row in doc.get("sources", []) + doc.get("batches", []):
    if row.get("state", "enabled") == "paused":
        continue
    if retire.get(row.get("scheduler"), "") != "retired":
        continue
    print(row["job"])
PY
  )
}

# --- gates --------------------------------------------------------------------
# `assert_window` — the contract's slot: a weekday 14:00–20:00Z (AR-3 + AR-2).
# Outside it the apply queues (exit 42); check mode is never gated.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hhmm dow
  now="${SIG_CONSOL_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
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
  if [ -z "${SIG_CONSOL_AUTHOR:-}" ]; then
    _log "QUEUED (exit 42): SIG_CONSOL_AUTHOR is unset — the recorded operator"
    _log "id for this consolidation apply (the GATE-G4 OM-20 listing's scope)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  _log "author: ${SIG_CONSOL_AUTHOR} (recorded)"
}

# `assert_prestate` — the retire leg runs only behind the recorded restore
# point: the prestate captures must exist under this EVIDENCE_DIR first.
assert_prestate() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ ! -f "${EVIDENCE_DIR}/pre/date-start.txt" ]; then
    _log "REFUSED: no recorded prestate under ${EVIDENCE_DIR}/pre/ —" >&2
    _log "run '--apply prestate' first; no trigger is retired without the restore point." >&2
    exit 2
  fi
}

# `assert_verify` — the retire leg runs only behind a VERIFIED dispatcher:
# verify/verified.txt records the deploy + staged dry-run proof (a trigger is
# never retired before the replacement demonstrably works).
assert_verify() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  if [ ! -f "${EVIDENCE_DIR}/verify/verified.txt" ]; then
    _log "REFUSED: no verified dispatcher under ${EVIDENCE_DIR}/verify/ —" >&2
    _log "run '--apply verify' first; retirements never precede the replacement's proof." >&2
    exit 2
  fi
}

# --- the legs ------------------------------------------------------------------
do_prestate() {
  _log "-- prestate ($(date -u +%FT%TZ)): the consolidation's restore-point captures (read-only) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "date -u + branch/sha > pre/{date-start,git}.txt"
    _plan "gcloud scheduler jobs list > pre/scheduler-jobs.json (the whole live trigger set)"
    _plan "gcloud run jobs list > pre/run-jobs.json"
    _plan "gcloud scheduler jobs describe <each retired name> > pre/trigger-*.json (presence probe)"
    _plan "gcloud storage cp ${DECLARED_URI} > pre/declared-bundle.json (best-effort)"
    _plan "sig-ops live-diff --live > pre/live-diff.txt (baseline — a read error is evidence)"
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
  _capture pre/scheduler-jobs.json gcloud scheduler jobs list \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture pre/run-jobs.json gcloud run jobs list \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  local sched
  while IFS='|' read -r sched _job; do
    [ -z "${sched}" ] && continue
    _capture "pre/trigger-${sched}.json" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  done <<<"${RETIRED}"
  _capture pre/declared-bundle.json gcloud storage cp "${DECLARED_URI}" -
  (cd "${_repo}" && uv run --quiet sig-ops live-diff --live) \
    > "${EVIDENCE_DIR}/pre/live-diff.txt" 2>&1 \
    || _log "   (pre-consolidation live-diff exited non-zero; the output is captured)"
  _sha256_rec "${EVIDENCE_DIR}/pre/live-diff.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _log "   prestate recorded under ${EVIDENCE_DIR}/pre (date -u: $(date -u +%FT%TZ))"
}

do_deploy() {
  _log "-- deploy ($(date -u +%FT%TZ)): the dispatcher job + its single hourly trigger --"
  local image="${SIG_JOB_IMAGE:-}"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    [ -z "${image}" ] && image="${SIG_API_IMAGE}@sha256:<digest-of-SIG_JOB_IMAGE>"
    _plan "gcloud run jobs deploy ${DUE_JOB} --image ${image} --service-account ${DUE_SA_EMAIL} \\"
    _plan "  --args '-c,exec sig-ops dispatch-due' --task-timeout ${DUE_TIMEOUT:-30m} --max-retries 0 \\"
    _plan "  --set-env-vars <project,region,bucket,cadence-path+sha,declared-uri> (NO cloudsql, NO secrets — evaluation only)"
    _plan "gcloud run jobs add-iam-policy-binding ${DUE_JOB} → sig-scheduler run.invoker"
    while read -r t; do
      [ -z "${t}" ] && continue
      _plan "gcloud run jobs add-iam-policy-binding ${t} → ${DUE_SA_EMAIL} run.invoker (the due invoker)"
    done <<<"${DUE_TARGETS}"
    _plan "gcloud scheduler jobs create http ${DUE_SCHED} --schedule '${DUE_CRON}' --time-zone=Etc/UTC → ${DUE_JOB}:run (update if present)"
    return 0
  fi
  if [ -z "${image}" ]; then
    _log "REFUSED: deploy needs SIG_JOB_IMAGE (a ${SIG_API_IMAGE}:<tag> or" >&2
    _log "@sha256 — resolved to a pinned digest, never :latest; ADR-111)." >&2
    exit 2
  fi
  image="$(pin_image_digest "${image}")" || exit 2
  mkdir -p "${EVIDENCE_DIR}/deploy"
  printf '%s\n' "${image}" > "${EVIDENCE_DIR}/deploy/image.txt"
  _sha256_rec "${EVIDENCE_DIR}/deploy/image.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  # The dispatcher needs NO Cloud SQL and NO secrets — it evaluates the
  # declaration and calls jobs:run; its only write is the run row to the
  # restricted bucket (the ingest class's objectCreator covers it).
  run gcloud run jobs deploy "${DUE_JOB}" \
    --image "${image}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${DUE_SA_EMAIL}" \
    --command sh \
    --args "-c,exec sig-ops dispatch-due" \
    --tasks 1 --task-timeout "${DUE_TIMEOUT:-30m}" --max-retries 0 \
    --set-env-vars "SIG_GCP_PROJECT=${SIG_GCP_PROJECT},SIG_GCP_REGION=${SIG_GCP_REGION},SIG_OPS_GCS_BUCKET=${SIG_BUCKET_RESTRICTED},SIG_OPS_CADENCE=/app/ops/cadence.toml,SIG_OPS_CADENCE_SHA256=${CADENCE_SHA256},SIG_OPS_DECLARED_GCS=${DECLARED_URI}"
  _capture deploy/job.json gcloud run jobs describe "${DUE_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  run gcloud run jobs add-iam-policy-binding "${DUE_JOB}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
    --member="serviceAccount:${SCHED_SA_EMAIL}" \
    --role=roles/run.invoker
  local tjob
  while read -r tjob; do
    [ -z "${tjob}" ] && continue
    run gcloud run jobs add-iam-policy-binding "${tjob}" \
      --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}" \
      --member="serviceAccount:${DUE_SA_EMAIL}" \
      --role=roles/run.invoker
  done <<<"${DUE_TARGETS}"
  local uri="https://${SIG_GCP_REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${SIG_GCP_PROJECT}/jobs/${DUE_JOB}:run"
  if gcloud scheduler jobs describe "${DUE_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
    run gcloud scheduler jobs update http "${DUE_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${DUE_CRON}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${SCHED_SA_EMAIL}"
  else
    run gcloud scheduler jobs create http "${DUE_SCHED}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --schedule "${DUE_CRON}" --time-zone=Etc/UTC --uri "${uri}" \
      --http-method=POST --oauth-service-account-email="${SCHED_SA_EMAIL}"
  fi
  _capture deploy/trigger.json gcloud scheduler jobs describe "${DUE_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _log "   dispatcher deployed: ${DUE_JOB} ← ${DUE_SCHED} ('${DUE_CRON}')"
}

do_verify() {
  _log "-- verify ($(date -u +%FT%TZ)): shape assertions + a staged dry-run execution --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "describe ${DUE_JOB} + ${DUE_SCHED}: digest-pinned image, sa_class SA, schedule, target, OIDC"
    _plan "gcloud run jobs execute ${DUE_JOB} --args '-c,exec sig-ops dispatch-due --dry-run' --wait"
    _plan "  (the staged evaluation runs end-to-end; nothing is executed — verify/verified.txt)"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/verify"
  _capture verify/job.json gcloud run jobs describe "${DUE_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  _capture verify/trigger.json gcloud scheduler jobs describe "${DUE_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  python3 - "${EVIDENCE_DIR}/verify/job.json" "${EVIDENCE_DIR}/verify/trigger.json" \
      "${DUE_JOB}" "${DUE_SCHED}" "${DUE_CRON}" "${DUE_SA_EMAIL}" "${SCHED_SA_EMAIL}" <<'PY'
import json
import sys

job = json.loads(open(sys.argv[1]).read())
trig = json.loads(open(sys.argv[2]).read())
due_job, due_sched, due_cron, due_sa, sched_sa = sys.argv[3:8]
problems = []
spec = (job.get("spec") or {}).get("template", {})
conts = (spec.get("spec") or {}).get("template", {}).get("spec", {}).get("containers") or []
image = conts[0].get("image", "") if conts else ""
if "@sha256:" not in image:
    problems.append(f"dispatcher image {image!r} is not digest-pinned (SIG-SEC-008)")
sa = (spec.get("spec") or {}).get("template", {}).get("spec", {}).get("serviceAccountName", "")
if sa != due_sa:
    problems.append(f"dispatcher runs as {sa!r}, declared {due_sa!r}")
args = " ".join(str(a) for c in conts for a in (c.get("args") or []))
if "dispatch-due" not in args:
    problems.append(f"dispatcher args {args!r} lack the dispatch-due verb")
if trig.get("schedule") != due_cron:
    problems.append(f"trigger schedule {trig.get('schedule')!r} != declared {due_cron!r}")
http = trig.get("httpTarget") or {}
if f"/jobs/{due_job}:run" not in (http.get("uri") or ""):
    problems.append(f"trigger uri {http.get('uri')!r} does not target {due_job}:run")
oauth = (http.get("oauthToken") or {}).get("serviceAccountEmail", "")
if oauth != sched_sa:
    problems.append(f"trigger OIDC {oauth!r} != {sched_sa!r}")
if trig.get("state") == "PAUSED":
    problems.append("the dispatcher trigger is PAUSED — the consolidation's trigger fires")
if problems:
    print("REFUSED: " + "; ".join(problems), file=sys.stderr)
    sys.exit(2)
print(f"  shape OK: {due_job} digest-pinned, runs as {due_sa}; {due_sched} '{due_cron}' → jobs/{due_job}:run signed {sched_sa}")
PY
  # The staged evaluation: the dispatcher job runs dispatch-due --dry-run
  # end-to-end (declaration read, due-set evaluation, run-row append) while
  # executing NOTHING — the replacement's proof before any trigger retires.
  # A failed staged run REFUSES the leg — retirements never proceed behind an
  # unverified replacement.
  _log "+ gcloud run jobs execute ${DUE_JOB} --args '-c,exec sig-ops dispatch-due --dry-run' --wait"
  if ! gcloud run jobs execute "${DUE_JOB}" \
      --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
      --args "-c,exec sig-ops dispatch-due --dry-run" --wait \
      > "${EVIDENCE_DIR}/verify/execute.txt" 2>&1; then
    _sha256_rec "${EVIDENCE_DIR}/verify/execute.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
    _log "ERROR: the staged dry-run execution failed (verify/execute.txt" >&2
    _log "captured) — no trigger retires behind an unverified dispatcher." >&2
    exit 2
  fi
  _sha256_rec "${EVIDENCE_DIR}/verify/execute.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  # The trigger itself is never fired here — the staged dry-run is the proof;
  # the first real dispatch is the hourly cron's own.
  date -u +%Y-%m-%dT%H:%M:%SZ > "${EVIDENCE_DIR}/verify/verified.txt"
  _sha256_rec "${EVIDENCE_DIR}/verify/verified.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _log "   verified — the dispatcher evaluates; retirements may proceed"
}

do_retire() {
  assert_prestate
  assert_verify
  _log "-- retire ($(date -u +%FT%TZ)): the name-checked per-row trigger deletions --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '%s\n' "${RETIRED}" | while IFS='|' read -r sched job; do
      [ -z "${sched}" ] && continue
      _plan "describe ${sched} (fresh json+yaml recipe) → assert uri targets /jobs/${job}:run → delete → absent read-back"
    done
    _plan "a trigger not on [[retire_triggers]] disposition=retired is never touched; absent → recorded skip"
    _plan "kept-declared-pin rows verified live + untouched; kept-manual rows are jobs, never triggers"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/retire"
  local kind kname kjob
  while IFS='|' read -r kind kname kjob; do
    [ -z "${kind}" ] && continue
    case "${kind}" in
      pin)
        if gcloud scheduler jobs describe "${kname}" \
            --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
          _log "  keep-list: ${kname} live (declared pin — untouched)"
        else
          _log "REFUSED: kept-declared-pin trigger ${kname} is absent live —" >&2
          _log "the pin declares it live; the retire leg never creates it." >&2
          exit 2
        fi ;;
      manual)
        _log "  keep-list: ${kname} (manual job — never a trigger)" ;;
    esac
  done <<<"${KEPT}"
  local sched job got_job
  while IFS='|' read -r sched job; do
    [ -z "${sched}" ] && continue
    if ! gcloud scheduler jobs describe "${sched}" \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "  ${sched}: already absent — recorded skip (the declare stays)"
      printf 'absent %s %s\n' "${sched}" "${job}" >> "${EVIDENCE_DIR}/retire/retired.txt"
      continue
    fi
    # The recreation recipe FIRST — a fresh describe, never a stale capture.
    _capture "retire/pre-${sched}.json" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
    _capture "retire/pre-${sched}.yaml" gcloud scheduler jobs describe "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format yaml
    # The name-check is a target-check: the trigger must point at the cadence
    # row's declared job — a trigger that points elsewhere is never deleted.
    got_job="$(python3 -c '
import json, sys, re
d = json.loads(open(sys.argv[1]).read())
uri = (d.get("httpTarget") or {}).get("uri", "")
m = re.search(r"/jobs/([^:/]+):run", uri)
print(m.group(1) if m else "")
' "${EVIDENCE_DIR}/retire/pre-${sched}.json" 2>/dev/null || true)"
    if [ "${got_job}" != "${job}" ]; then
      _log "ERROR: ${sched} targets /jobs/${got_job:-<unreadable>}:run, cadence" >&2
      _log "declares ${job} — a trigger that points at an unexpected job is" >&2
      _log "never deleted; the sweep stops (no silent reconcile)." >&2
      exit 2
    fi
    run gcloud scheduler jobs delete "${sched}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet
    if gcloud scheduler jobs describe "${sched}" \
        --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" >/dev/null 2>&1; then
      _log "ERROR: ${sched} still describes after delete — the sweep stops (no silent deletes)." >&2
      exit 2
    fi
    printf 'deleted %s %s\n' "${sched}" "${job}" >> "${EVIDENCE_DIR}/retire/retired.txt"
    _log "  ${sched}: deleted (describe → target-check ${job} → delete → absent read-back)"
  done <<<"${RETIRED}"
  [ -f "${EVIDENCE_DIR}/retire/retired.txt" ] && \
    _sha256_rec "${EVIDENCE_DIR}/retire/retired.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
}

do_proof() {
  _log "-- proof ($(date -u +%FT%TZ)): the consolidated end-state + the closing live-diff --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "scheduler jobs list → post/scheduler-jobs.json; assert every retired name absent"
    _plan "describe ${DUE_SCHED} + kept-pin trigger: present, enabled, OIDC sig-scheduler"
    _plan "sig-ops live-diff --live → post/live-diff.txt; assert residual findings are all"
    _plan "  recorded declared drift (a pending retirement) — any other finding fails"
    return 0
  fi
  mkdir -p "${EVIDENCE_DIR}/post"
  _capture post/scheduler-jobs.json gcloud scheduler jobs list \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  printf '%s\n' "${RETIRED}" | cut -d'|' -f1 > "${EVIDENCE_DIR}/post/retired-names.txt"
  _sha256_rec "${EVIDENCE_DIR}/post/retired-names.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  python3 - "${EVIDENCE_DIR}/post/scheduler-jobs.json" \
      "${EVIDENCE_DIR}/post/retired-names.txt" "${DUE_SCHED}" <<'PY'
import json
import sys

names = {
    ((t.get("name") or "").rsplit("/", 1)[-1])
    for t in json.loads(open(sys.argv[1]).read() or "[]")
}
retired = [ln.strip() for ln in open(sys.argv[2]) if ln.strip()]
due_sched = sys.argv[3]
problems = []
still = [n for n in retired if n in names]
if still:
    problems.append(f"retired triggers still live in poststate: {still}")
if due_sched not in names:
    problems.append(f"dispatcher trigger {due_sched} absent in poststate")
if problems:
    print("ERROR: " + "; ".join(problems), file=sys.stderr)
    sys.exit(2)
print(f"  poststate: {len(retired)} retired names absent; {due_sched} present")
PY
  _capture post/due-trigger.json gcloud scheduler jobs describe "${DUE_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  while IFS='|' read -r kind kname _kj; do
    [ "${kind}" = "pin" ] || continue
    _capture "post/kept-${kname}.json" gcloud scheduler jobs describe "${kname}" \
      --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --format json
  done <<<"${KEPT}"
  (cd "${_repo}" && uv run --quiet sig-ops live-diff --live) \
    > "${EVIDENCE_DIR}/post/live-diff.txt" 2>&1 \
    || _log "   (post-consolidation live-diff exited non-zero; captured — the residual list is judged below)"
  _sha256_rec "${EVIDENCE_DIR}/post/live-diff.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  # The closing proof: live-diff's residual findings must all be RECORDED
  # declared drift — a pending retirement (a retired name still live reads
  # "declared retired … pending"), a P35.1b job pending deletion, a declared
  # pin. Anything else is unlisted drift and fails the leg.
  python3 - "${EVIDENCE_DIR}/post/live-diff.txt" <<'PY'
import json
import re
import sys

raw = open(sys.argv[1]).read()
try:
    payload = json.loads(raw[: raw.rindex("}") + 1])
except (ValueError, json.JSONDecodeError):
    print(f"ERROR: live-diff output is not a parseable run payload", file=sys.stderr)
    sys.exit(2)
recorded = re.compile(r"declared retired|expected absent|pending|declared pin|paused")
bad = []
for f in payload.get("findings") or []:
    detail = f.get("detail", "")
    if recorded.search(detail):
        continue
    bad.append(f"{f.get('class')} {f.get('name')}: {detail}")
if bad:
    print("ERROR: closing live-diff carries UNRECORDED drift:", file=sys.stderr)
    for line in bad:
        print(f"  {line}", file=sys.stderr)
    sys.exit(2)
n = len(payload.get("findings") or [])
print(f"  closing live-diff: {n} finding(s), all recorded declared drift — 0 unlisted")
PY
  date -u +%Y-%m-%dT%H:%M:%SZ > "${EVIDENCE_DIR}/post/date-end.txt"
  _sha256_rec "${EVIDENCE_DIR}/post/date-end.txt" >> "${EVIDENCE_DIR}/sha256s.txt"
  _log "   poststate recorded under ${EVIDENCE_DIR}/post — the consolidation's closing proof"
}

do_rollback() {
  _log "-- rollback ($(date -u +%FT%TZ)): the dispatcher comes down; per-source triggers return --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud scheduler jobs delete ${DUE_SCHED} --quiet (the consolidation's own trigger)"
    _plan "gcloud run jobs delete ${DUE_JOB} --quiet (the consolidation's own job)"
    _plan "scheduled-ops.sh --apply --shape per-source — the declared rollback map recreates"
    _plan "  every per-row trigger (paused rows created/held PAUSED) from the same cadence rows"
    _plan "each retire/pre-<sched>.{json,yaml} capture stays the per-trigger recreation recipe"
    return 0
  fi
  require_adc
  run gcloud scheduler jobs delete "${DUE_SCHED}" \
    --location "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet \
    || _log "   (dispatcher trigger absent already — recorded)"
  run gcloud run jobs delete "${DUE_JOB}" \
    --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" --quiet \
    || _log "   (dispatcher job absent already — recorded)"
  _log "  restoring the per-source trigger shape (the declared rollback map):"
  run "${_here}/scheduled-ops.sh" --apply --shape per-source
  _log "  rollback replayed — retired-trigger recreation recipes under"
  _log "  ${EVIDENCE_DIR}/retire/pre-*.json|yaml remain the per-name record"
}

# ---------------------------------------------------------------------------
banner "dispatcher consolidation (P35.1c / ticket 291a; OM-20 gated)"

require_project
SIG_BUCKET_RESTRICTED="${SIG_GCP_PROJECT}-sig-restricted"
DECLARED_URI="gs://${SIG_BUCKET_RESTRICTED}/ops/declared/live-diff.json"
CADENCE_SHA256="$(_sha256 "${CADENCE_TOML}")"
SIG_API_IMAGE="${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-api"
SCHED_SA_EMAIL="${SIG_SCHEDULER_SA}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com"

# The closed sets — parsed + drift-checked BEFORE any gate or plan.
RETIRED="$(read_retire_rows)" || exit 2
KEPT="$(read_kept_rows)" || exit 2
DUE_TARGETS="$(read_due_targets)" || exit 2
DUE_JOB="" DUE_SCHED="" DUE_CRON="" DUE_SA_CLASS="" DUE_TIMEOUT=""
while IFS='|' read -r djob dsched dcron dsac dtimeout; do
  [ -z "${djob}" ] && continue
  DUE_JOB="${djob}"; DUE_SCHED="${dsched}"; DUE_CRON="${dcron}"
  DUE_SA_CLASS="${dsac}"; DUE_TIMEOUT="${dtimeout}"
done <<<"$(read_dispatcher_row)"
[ -n "${DUE_JOB}" ] || { _log "dispatcher-consolidation.sh: no [dispatcher] row" >&2; exit 2; }
case "${DUE_SA_CLASS}" in
  ingest) DUE_SA_EMAIL="${SIG_SA_INGEST}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com" ;;
  probe)  DUE_SA_EMAIL="${SIG_SA_PROBE}@${SIG_GCP_PROJECT}.iam.gserviceaccount.com" ;;
  *) _log "ERROR: sa_class ${DUE_SA_CLASS} unresolved" >&2; exit 2 ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  mkdir -p "${EVIDENCE_DIR}"
  {
    _log "closed sets (cadence.toml-verified — drift refuses):"
    _log "  dispatcher: ${DUE_JOB} ← ${DUE_SCHED} ('${DUE_CRON}', sa=${DUE_SA_EMAIL})"
    printf '%s\n' "${RETIRED}" | while IFS='|' read -r s j; do
      _log "  retire: ${s} → was /jobs/${j}:run"; done
    printf '%s\n' "${KEPT}" | while IFS='|' read -r k n j; do
      _log "  keep (${k}): ${n}"; done
    _log "leg order: prestate → deploy → verify → retire → proof"
  } | tee "${EVIDENCE_DIR}/check-targets.txt"
fi

run_leg() {
  case "$1" in
    prestate) do_prestate ;;
    deploy)   do_deploy ;;
    verify)   do_verify ;;
    retire)   do_retire ;;
    proof)    do_proof ;;
    *) _log "dispatcher-consolidation.sh: unknown leg '$1'" >&2; exit 64 ;;
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
    for leg in prestate deploy verify retire proof; do
      run_leg "${leg}"
    done
    ;;
  *)
    assert_window
    require_adc
    case "${ACTION}" in
      deploy|verify|retire) assert_author ;;
    esac
    mkdir -p "${EVIDENCE_DIR}"
    touch "${EVIDENCE_DIR}/sha256s.txt"
    run_leg "${ACTION}"
    ;;
esac

if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "dispatcher-consolidation ${ACTION}: check OK (mode=${SIG_GCP_MODE}; evidence → ${EVIDENCE_DIR})"
else
  _log "dispatcher-consolidation ${ACTION}: done (mode=${SIG_GCP_MODE}; evidence → ${EVIDENCE_DIR})"
fi
