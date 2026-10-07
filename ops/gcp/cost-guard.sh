#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/cost-guard.sh — P34.5 cost guard (SIG-OPS-009): the budget alert at the
# operator's ceiling, the test-threshold budget, and the BigQuery billing-export
# dataset.
#
# The pre-authorised production mutations (contract docs/tickets/
# 206_P34.5__cost-guard-budget-alert-billing-export.md; OM-20 S5-3 11A list,
# LEDGER GATE DECISIONS 2026-10-01T04:28:49Z, expires GATE-G4, voided-by a red
# probe / failed restore point / a production read contradicting a record):
#
#   1. a Cloud Billing budget at the $300/month infrastructure ceiling (U-008,
#      A-2a — infrastructure only) with 50/90/100 % e-mail alerts, scoped to the
#      SIG project (the billing account also serves unrelated projects — the
#      ceiling covers SIG infrastructure, so the budget filters on
#      projects/$SIG_GCP_PROJECT). E-mail goes to the billing account's IAM
#      recipients (default; never disabled here) and to the committed operator
#      e-mail channel (ops/monitoring/channel.operator-email.json, resolved by
#      displayName — the address is never committed).
#   2. one temporary test-threshold budget ($0.01, 100 %) that fires against the
#      already-nonzero month-to-date spend; deleted by `testbudget-delete`
#      ONLY after its alert firing is confirmed (the e-mail receipt is the
#      human leg — an agent never asserts it, B-31/B-42).
#   3. the BigQuery billing-export dataset `sig_billing_export`. Enabling the
#      export link itself is an operator console step (OP-12 — Cloud Billing
#      export has no public API path): Billing → Billing export → BigQuery
#      export → this dataset. The first month's table lands as
#      `gcp_billing_export_v1_<billing-account-id>` within ~a day.
#
# Enabling step (a prerequisite of mutation 1, spend-neutral, reversible):
# `billingbudgets.googleapis.com` on the project — without it no budgets call
# (read or write) is possible. Rollback: `gcloud services disable`.
#
# Rollback per mutation (also printed by the script):
#   budget          → `gcloud billing budgets delete <id>`
#   test budget     → `gcloud billing budgets delete <id>` (same path)
#   export dataset  → `bq rm -r -d <project>:sig_billing_export` (the export
#                     link is disabled console-side first)
#
# Usage:
#   ops/gcp/cost-guard.sh [--check|--dry-run] [ACTION]   # plan only (default)
#   ops/gcp/cost-guard.sh --verify [--from-state DIR]    # read-only outcome diff
#   ops/gcp/cost-guard.sh --apply [ACTION] [--fired-confirmed "<evidence>"]
#
# ACTION (default `all`):
#   prestate            capture the billing link, the budgets list, the dataset
#                       list and the billingbudgets API state (read-only)
#   budget              enable billingbudgets API if needed, then create the
#                       $300 ceiling budget (SKIP when a budget with the same
#                       displayName already exists)
#   testbudget          create the temporary $0.01 test budget (SKIP if present)
#   testbudget-delete   delete the test budget — REFUSES unless
#                       --fired-confirmed "<where the firing is recorded>"
#                       is given (the delete happens only after the alert fired)
#   dataset             create the sig_billing_export BigQuery dataset
#   exportcheck         read-only: does the export table exist yet and how many
#                       rows does it hold (the OP-12-dependent leg)
#   all                 prestate -> budget -> testbudget -> dataset ->
#                       post-state capture -> --verify -> exportcheck
#
# Modes (same check/apply contract as lib.sh / protect.sh / alerts.sh):
#   check    no ADC, no network; prints PLAN lines + `check OK`
#   apply    requires ADC + SIG_GCP_PROJECT (lib.sh gates). The live window is
#            "any time (billing metadata)" per the contract — billing metadata
#            never touches running infrastructure, so there is NO daily band
#            guard here (unlike protect.sh/alerts.sh).
#   verify   read-only; diffs the desired set (ceiling budget shape, dataset)
#            against the live account — or --from-state recorded JSON — and
#            reports the test-budget and export-rows legs as observations.
#            Prints OK/DRIFT/MISSING + `verify: N OK, M not-OK`; exit 1 on any
#            non-OK counted row.
#
# Env:
#   SIG_GCP_PROJECT              required for apply/live-verify (lib.sh)
#   SIG_BILLING_ACCOUNT          billing account override (default: discovered
#                                live from the project's billing link — the id
#                                is never committed to the repo)
#   SIG_BUDGET_DATASET           export dataset id (default sig_billing_export)
#   SIG_BUDGET_LOCATION          dataset location (default US multi-region)
#   SIG_BUDGET_CHANNEL           monitoring channel resource override (default:
#                                resolved live by displayName
#                                "SIG operator email (Track 0.5)")
#   SIG_BUDGET_PROJECT_NUMBER    the project's number — GCP stores the budget's
#                                project filter in number form; the live verify
#                                resolves it, --from-state takes it from here
#   SIG_COST_GUARD_EVIDENCE_DIR  where captured JSON lands
#                                (default <repo>/docs/build/logs/cost-guard —
#                                gitignored)
#
# Credentials: none are read or written; the operator's e-mail address is never
# committed (the channel def carries `<redacted>`).

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
FIRED_CONFIRMED=""

case "${1:-}" in
  --apply) MODE="apply"; shift ;;
  --verify) MODE="verify"; shift ;;
  --check|--dry-run) MODE="check"; shift ;;
  -h|--help) _usage 0 ;;
  "") MODE="check" ;;
  # A bare ACTION (no mode flag) is the plan path — the usage line's default.
  prestate|budget|testbudget|testbudget-delete|dataset|exportcheck|all) MODE="check" ;;
  *) echo "cost-guard.sh: unknown mode '$1'" >&2; _usage 64 ;;
esac

while [ $# -gt 0 ]; do
  case "$1" in
    --from-state)
      [ $# -ge 2 ] || { echo "cost-guard.sh: --from-state needs a directory" >&2; exit 64; }
      FROM_STATE="$2"; shift 2 ;;
    --from-state=*) FROM_STATE="${1#--from-state=}"; shift ;;
    --fired-confirmed)
      [ $# -ge 2 ] || { echo "cost-guard.sh: --fired-confirmed needs a value" >&2; exit 64; }
      FIRED_CONFIRMED="$2"; shift 2 ;;
    --fired-confirmed=*) FIRED_CONFIRMED="${1#--fired-confirmed=}"; shift ;;
    prestate|budget|testbudget|testbudget-delete|dataset|exportcheck|all)
      [ "$ACTION" = "all" ] || { echo "cost-guard.sh: only one ACTION" >&2; exit 64; }
      ACTION="$1"; shift ;;
    *) echo "cost-guard.sh: unknown argument '$1'" >&2; _usage 64 ;;
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

# ---- constants --------------------------------------------------------------

EVIDENCE_ROOT="${SIG_COST_GUARD_EVIDENCE_DIR:-${_here}/../../docs/build/logs/cost-guard}"
BUDGET_NAME="SIG infra ceiling — 300 USD per month (U-008)"
TEST_BUDGET_NAME="SIG-P34.5 test threshold — fires then deleted"
DATASET="${SIG_BUDGET_DATASET:-sig_billing_export}"
DATASET_LOCATION="${SIG_BUDGET_LOCATION:-US}"
CHANNEL_DISPLAY="SIG operator email (Track 0.5)"
BUDGET_API="billingbudgets.googleapis.com"
RERUN_HINT="re-run: implement-spec spec=docs/tickets/206_P34.5__cost-guard-budget-alert-billing-export.md live_verification=true"

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

_evidence_dir() {  # $1 = tag (pre|post|verify|apply)
  printf '%s/%s-%s\n' "$EVIDENCE_ROOT" "$1" "$(date -u +%Y%m%dT%H%M%SZ)"
}

# ---- live reads --------------------------------------------------------------

# The billing account the project pays through — discovered live, env-overridable,
# never committed (same posture as the project id itself).
_billing_acct() {
  if [ -n "${SIG_BILLING_ACCOUNT:-}" ]; then printf '%s\n' "$SIG_BILLING_ACCOUNT"; return 0; fi
  gcloud billing projects describe "$SIG_GCP_PROJECT" \
    --format='value(billingAccountName)' 2>/dev/null | sed 's|.*/||'
}

_budgets_list() {  # $1 = billing account id
  # --billing-project makes the project the consumer/quota project so the
  # billingbudgets API state on THIS project governs (never the CLI default).
  gcloud billing budgets list --billing-account="$1" \
    --billing-project="$SIG_GCP_PROJECT" --format=json
}

_budget_api_enabled() {
  # '[]' is a non-empty line — grep for the API's own name, not "any output".
  gcloud services list --enabled --project "$SIG_GCP_PROJECT" \
    --filter="config.name:${BUDGET_API}" --format='value(config.name)' \
    2>/dev/null | grep -q "^${BUDGET_API}$"
}

# Echo the id of the budget with an exact displayName, "" when none. A FAILED
# list read returns rc 3 — callers must NOT treat it as "absent" (creating on an
# unread list could duplicate an existing budget).
_budget_id_by_name() {  # $1 = budgets JSON text, $2 = exact displayName
  SIG_BLIST="$1" python3 - "$2" <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_BLIST"])
except Exception:
    sys.exit(0)
want = sys.argv[1]
for r in rows:
    if r.get("displayName") == want:
        print(str(r.get("name", "")).rsplit("/", 1)[-1])
        break
PY
}

_channel_ref() {  # -> projects/<p>/notificationChannels/<id> (empty if absent)
  if [ -n "${SIG_BUDGET_CHANNEL:-}" ]; then printf '%s\n' "$SIG_BUDGET_CHANNEL"; return 0; fi
  local json
  json="$(gcloud beta monitoring channels list --project "$SIG_GCP_PROJECT" \
    --format=json 2>/dev/null)" || return 0
  SIG_CHANNELS="$json" python3 - "$CHANNEL_DISPLAY" <<'PY'
import json, os, sys
try:
    rows = json.loads(os.environ["SIG_CHANNELS"])
except Exception:
    sys.exit(0)
want = sys.argv[1]
for r in rows:
    if r.get("displayName") == want and r.get("enabled", True):
        print(r.get("name", ""))
        break
PY
}

_datasets_list() {
  bq ls --project_id="$SIG_GCP_PROJECT" --format=json 2>/dev/null || echo '[]'
}

# ---- capture ----------------------------------------------------------------

act_prestate() {  # $1 = dir tag (pre|post)
  local tag="${1:-pre}"
  if [ "$MODE" = "check" ]; then
    _plan "capture: billing link, billingbudgets API state, budgets list,"
    _plan "  datasets list -> \$SIG_COST_GUARD_EVIDENCE_DIR/${tag}-<ts> (+sha256s)"
    return 0
  fi
  local dir; dir="$(_evidence_dir "$tag")"; mkdir -p "$dir"
  _log "prestate($tag): capturing live billing state -> $dir"
  gcloud billing projects describe "$SIG_GCP_PROJECT" --format=json \
    > "$dir/project-billing.json" 2>"$dir/project-billing.err" || echo '{}' > "$dir/project-billing.json"
  gcloud services list --enabled --project "$SIG_GCP_PROJECT" \
    --filter="config.name:${BUDGET_API}" --format=json \
    > "$dir/budgets-api.json" 2>"$dir/budgets-api.err" || echo '[]' > "$dir/budgets-api.json"
  local acct; acct="$(_billing_acct)"
  printf '%s\n' "${acct:-<none>}" > "$dir/billing-account.txt"
  if [ -n "$acct" ]; then
    _budgets_list "$acct" > "$dir/budgets.json" 2>"$dir/budgets.err" \
      || printf '{"error": true}\n' > "$dir/budgets.json"
  else
    printf '{"error": "no billing account"}\n' > "$dir/budgets.json"
  fi
  _datasets_list > "$dir/datasets.json" 2>"$dir/datasets.err" || echo '[]' > "$dir/datasets.json"
  (cd "$dir" && for f in *; do [ -f "$f" ] && _sha256 "$f"; done) > "$dir/sha256s.txt"
  _log "prestate($tag): sha256s recorded in $dir/sha256s.txt"
}

# ---- mutations ----------------------------------------------------------------

_ensure_api() {
  if _budget_api_enabled; then
    _log "billingbudgets API: already enabled on $SIG_GCP_PROJECT"
    return 0
  fi
  _log "enabling ${BUDGET_API} on $SIG_GCP_PROJECT (spend-neutral; prerequisite of"
  _log "  the authorised budget mutation; rollback: gcloud services disable ${BUDGET_API})"
  run gcloud services enable "$BUDGET_API" --project "$SIG_GCP_PROJECT"
}

_create_budget() {  # $1 = acct, $2 = displayName, $3 = amountUSD, $4.. = threshold-rule flags
  local acct="$1" name="$2" amount="$3"; shift 3
  local json
  if ! json="$(_budgets_list "$acct" 2>/dev/null)"; then
    echo "cost-guard.sh: budgets list unreadable — not creating on a failed read" >&2
    return 3
  fi
  local existing; existing="$(_budget_id_by_name "$json" "$name")"
  if [ -n "$existing" ]; then
    _log "SKIP create — a budget named '$name' already exists (id $existing); --verify diffs it"
    return 0
  fi
  local channel=""; channel="$(_channel_ref)"
  if [ -z "$channel" ]; then
    _log "note: monitoring channel '$CHANNEL_DISPLAY' not resolved — default IAM"
    _log "  recipients (billing admins/users) still deliver the e-mail alerts"
  fi
  # bash-3.2-safe arg build: positional params, never mapfile.
  set -- "$@" "--filter-projects=projects/${SIG_GCP_PROJECT}"
  # Default IAM recipients stay ON (no --disable-default-iam-recipients): the
  # billing account's admins/users get the e-mail. The committed operator
  # channel is added as a second path when it resolves.
  if [ -n "$channel" ]; then
    set -- "$@" "--notifications-rule-monitoring-notification-channels=${channel}"
  fi
  run gcloud billing budgets create --billing-account="$acct" \
    --billing-project="$SIG_GCP_PROJECT" \
    --display-name="$name" --budget-amount="${amount}USD" "$@" \
    || return $?
  _log "  rollback: gcloud billing budgets delete <new id> --billing-account=$acct --billing-project=$SIG_GCP_PROJECT"
}

act_budget() {
  if [ "$MODE" = "check" ]; then
    _plan "gcloud services enable ${BUDGET_API} --project <p>   (if disabled; prerequisite)"
    _plan "gcloud billing budgets create --billing-account=<from project link>"
    _plan "  --display-name='${BUDGET_NAME}' --budget-amount=300USD"
    _plan "  --threshold-rule=percent=0.50 --threshold-rule=percent=0.90 --threshold-rule=percent=1.0"
    _plan "  (CURRENT_SPEND basis)"
    _plan "  --filter-projects=projects/\$SIG_GCP_PROJECT (infrastructure only, A-2a)"
    _plan "  default IAM recipients + the operator e-mail channel when resolvable"
    _plan "  rollback: gcloud billing budgets delete <id>"
    return 0
  fi
  _ensure_api
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  local acct; acct="$(_billing_acct)"
  if [ -z "$acct" ]; then
    echo "cost-guard.sh: no billing account link on $SIG_GCP_PROJECT — OP-12" >&2
    exit 3
  fi
  printf '%s\n' "$acct" > "$dir/billing-account.txt"
  _log "billing account: $acct (from the project link; not committed)"
  local rc=0
  _create_budget "$acct" "$BUDGET_NAME" 300 \
    --threshold-rule=percent=0.50 \
    --threshold-rule=percent=0.90 \
    --threshold-rule=percent=1.0 || {
    rc=$?
    echo "cost-guard.sh: budget create failed (rc=$rc) — billing-admin is the" >&2
    echo "cost-guard.sh: operator's role if this identity lacks it (OP-12)." >&2
    echo "cost-guard.sh: ${RERUN_HINT}" >&2
    exit "$rc"
  }
  _budgets_list "$acct" > "$dir/budgets.after.json" 2>/dev/null || true
}

act_testbudget() {
  if [ "$MODE" = "check" ]; then
    _plan "create the temporary test budget '$TEST_BUDGET_NAME':"
    _plan "  --budget-amount=0.01USD --threshold-rule=percent=1.0, project-scoped —"
    _plan "  fires against existing month-to-date spend at the next evaluation;"
    _plan "  the firing e-mail is the human leg (D-P34.5-1), then it is deleted"
    _plan "  rollback: gcloud billing budgets delete <id>"
    return 0
  fi
  _ensure_api
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  local acct; acct="$(_billing_acct)"
  [ -n "$acct" ] || { echo "cost-guard.sh: no billing account link — OP-12" >&2; exit 3; }
  local rc=0
  _create_budget "$acct" "$TEST_BUDGET_NAME" 0.01 \
    --threshold-rule=percent=1.0 || {
    rc=$?
    echo "cost-guard.sh: test-budget create failed (rc=$rc) — OP-12 if role-lacking" >&2
    exit "$rc"
  }
  _log "testbudget: created; its alert fires at the next budget evaluation"
  _log "  (e-mail to billing IAM recipients + the operator channel) — the"
  _log "  receipt is the human leg; delete afterwards via 'testbudget-delete'"
  _log "  with --fired-confirmed \"<where the firing is recorded>\""
}

act_testbudget_delete() {
  if [ "$MODE" = "check" ]; then
    _plan "gcloud billing budgets delete <id of '$TEST_BUDGET_NAME'>"
    _plan "  — name-checked (only that exact displayName) and REFUSES without"
    _plan "  --fired-confirmed \"<evidence>\" (the alert must have fired first)"
    return 0
  fi
  if [ -z "$FIRED_CONFIRMED" ]; then
    echo "cost-guard.sh: REFUSED — the test budget is deleted only after its alert" >&2
    echo "cost-guard.sh: fired; pass --fired-confirmed \"<where the firing is" >&2
    echo "cost-guard.sh: recorded>\" once the operator's confirmation exists." >&2
    exit 42
  fi
  _ensure_api
  local acct; acct="$(_billing_acct)"
  [ -n "$acct" ] || { echo "cost-guard.sh: no billing account link — OP-12" >&2; exit 3; }
  local json
  if ! json="$(_budgets_list "$acct" 2>/dev/null)"; then
    echo "cost-guard.sh: budgets list unreadable — not deleting on a failed read" >&2
    exit 3
  fi
  local id; id="$(_budget_id_by_name "$json" "$TEST_BUDGET_NAME")"
  if [ -z "$id" ]; then
    _log "SKIP delete — no budget named '$TEST_BUDGET_NAME' (already gone)"
    return 0
  fi
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  printf '%s\n' "$FIRED_CONFIRMED" > "$dir/fired-confirmed.txt"
  _log "testbudget-delete: firing confirmed by '$FIRED_CONFIRMED' (recorded)"
  run gcloud billing budgets delete "$id" --billing-account="$acct" \
    --billing-project="$SIG_GCP_PROJECT"
  _budgets_list "$acct" > "$dir/budgets.after.json" 2>/dev/null || true
}

act_dataset() {
  if [ "$MODE" = "check" ]; then
    _plan "bq mk --dataset --project_id=\$SIG_GCP_PROJECT --location=${DATASET_LOCATION}"
    _plan "  --description='SIG Cloud Billing export (SIG-OPS-009, P34.5)' ${DATASET}"
    _plan "  (SKIP when present) — then the OPERATOR links Billing export → this"
    _plan "  dataset in the console (OP-12; there is no public API path)"
    _plan "  rollback: bq rm -r -d \$SIG_GCP_PROJECT:${DATASET}"
    return 0
  fi
  local dir; dir="$(_evidence_dir apply)"; mkdir -p "$dir"
  if _datasets_list | python3 -c '
import json, sys
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(1)
sys.exit(0 if any((r.get("datasetReference") or {}).get("datasetId") == sys.argv[1]
                  or str(r.get("id", "")).endswith(":" + sys.argv[1]) for r in rows) else 1)
' "$DATASET"; then
    _log "SKIP dataset — ${DATASET} already exists"
  else
    run bq mk --dataset --project_id="$SIG_GCP_PROJECT" \
      --location="$DATASET_LOCATION" \
      --description="SIG Cloud Billing export (SIG-OPS-009, P34.5)" "$DATASET"
    _log "  rollback: bq rm -r -d ${SIG_GCP_PROJECT}:${DATASET}"
  fi
  _datasets_list > "$dir/datasets.after.json"
  _log "dataset: next step is the operator's console link (OP-12) — Billing →"
  _log "  Billing export → BigQuery export → dataset ${DATASET} on ${SIG_GCP_PROJECT}"
}

act_exportcheck() {
  # Read-only — the first monthly report's verification query (D-P34.5-3).
  if [ "$MODE" = "check" ]; then
    _plan "bq query 'SELECT COUNT(*) FROM <p>.${DATASET}.gcp_billing_export_v1_<acct>'"
    _plan "  — 'table absent' is honest until the OP-12 link exists; never fabricate"
    return 0
  fi
  local acct; acct="$(_billing_acct)"
  if [ -z "$acct" ]; then
    _log "exportcheck: no billing account link — OP-12 pending"
    return 0
  fi
  local table="${SIG_GCP_PROJECT}.${DATASET}.gcp_billing_export_v1_$(printf '%s' "$acct" | tr '-' '_')"
  _log "exportcheck: querying \`$table\`"
  if bq query --nouse_legacy_sql --format=json \
      "SELECT COUNT(*) AS rows_in_export FROM \`$table\`" 2>/dev/null; then
    _log "exportcheck: the export holds rows — the first monthly report leg may run"
  else
    _log "exportcheck: no export table yet — expected until the operator enables"
    _log "  the Billing export link (OP-12); rows appear within ~a day of linking"
  fi
}

# ---- verify ------------------------------------------------------------------

# $1 = budgets json path, $2 = datasets json path, $3 = project number (may be "")
_emit_verdicts() {
  python3 - "$1" "$2" "$SIG_GCP_PROJECT" "$3" "$BUDGET_NAME" "$TEST_BUDGET_NAME" "$DATASET" <<'PY'
import json, sys

budgets_path, datasets_path, project, project_number, budget_name, test_name, dataset = sys.argv[1:8]

def _load(path):
    try:
        return json.load(open(path))
    except Exception:
        return {"__error__": True}

budgets = _load(budgets_path)
datasets = _load(datasets_path)
not_ok = 0

def _thresholds(b):
    return sorted(
        float(t.get("thresholdPercent", 0))
        for t in (b.get("thresholdRules") or [])
    )

if isinstance(budgets, dict) or budgets is None:
    print("ceiling-budget MISSING  (budgets list unreadable)")
    print("test-budget    ?        (budgets list unreadable)")
    not_ok += 1
else:
    ceiling = [b for b in budgets if b.get("displayName") == budget_name]
    test = [b for b in budgets if b.get("displayName") == test_name]
    if not ceiling:
        print("ceiling-budget MISSING  (no '%s')" % budget_name)
        not_ok += 1
    else:
        b = ceiling[0]
        amt = (b.get("amount") or {}).get("specifiedAmount") or {}
        units = int(amt.get("units", 0))
        ccy = amt.get("currencyCode", "")
        thr = _thresholds(b)
        projs = (b.get("budgetFilter") or {}).get("projects") or []
        # GCP stores the scope as the project NUMBER (projects/<num>) even when
        # the create flag named the id — both forms are the same project.
        scope_names = {x for x in (project, project_number) if x}
        if not scope_names and projs:
            # --from-state with SIG_GCP_PROJECT unset: infer the scope from the
            # captured budget itself (never a committed literal).
            scope_names = {str(projs[0]).rsplit("/", 1)[-1]}
        proj_ok = any(
            str(p).rsplit("/", 1)[-1] in scope_names for p in projs
        )
        if units == 300 and ccy == "USD" and thr == [0.5, 0.9, 1.0] and proj_ok:
            print("ceiling-budget OK      (300 USD, thresholds 50/90/100 %, project-scoped)")
        else:
            print("ceiling-budget DRIFT   (units=%s ccy=%s thresholds=%s projects=%s)"
                  % (units, ccy, thr, projs))
            not_ok += 1
    if test:
        print("test-budget    present (fires at next evaluation; delete leg owed)")
    else:
        print("test-budget    gone    (expected once the fired alert is confirmed+deleted)")

if isinstance(datasets, dict) or datasets is None:
    print("export-dataset MISSING  (datasets list unreadable)")
    not_ok += 1
else:
    found = any((d.get("datasetReference") or {}).get("datasetId") == dataset
                or str(d.get("id", "")).endswith(":" + dataset) for d in datasets)
    if found:
        print("export-dataset OK      (%s exists)" % dataset)
    else:
        print("export-dataset MISSING (no dataset '%s')" % dataset)
        not_ok += 1

print("export-rows    observed-only — see 'exportcheck' (the OP-12 link leg)")
sys.exit(1 if not_ok else 0)
PY
}

act_verify() {
  if [ "$MODE" = "check" ]; then
    _plan "diff desired vs live: ceiling budget (300 USD, 50/90/100 %, project-"
    _plan "  scoped), the export dataset; test-budget + export-rows reported as"
    _plan "  observations — exit 1 on a non-OK counted row"
    return 0
  fi
  if [ -n "$FROM_STATE" ]; then
    [ -d "$FROM_STATE" ] || {
      echo "cost-guard.sh: --from-state '$FROM_STATE' is not a directory" >&2
      return 66
    }
    _emit_verdicts "$FROM_STATE/budgets.json" "$FROM_STATE/datasets.json" \
        "${SIG_BUDGET_PROJECT_NUMBER:-}" && {
      _log "verify: all counted rows OK"; return 0; } || {
      echo "cost-guard.sh: verify found non-OK rows" >&2; return 1; }
  fi
  # Verify is read-only: it never enables the API — it reports the state.
  if ! _budget_api_enabled; then
    echo "cost-guard.sh: ${BUDGET_API} is not enabled on $SIG_GCP_PROJECT —" >&2
    echo "cost-guard.sh: the budgets read is impossible until the apply leg runs" >&2
    return 1
  fi
  local dir; dir="$(_evidence_dir verify)"; mkdir -p "$dir"
  local acct; acct="$(_billing_acct)"
  if [ -z "$acct" ]; then
    echo "cost-guard.sh: no billing account link — OP-12" >&2; return 1
  fi
  printf '%s\n' "$acct" > "$dir/billing-account.txt"
  # The budget filter stores the project NUMBER — resolve it for the diff.
  local pnum
  pnum="$(gcloud projects describe "$SIG_GCP_PROJECT" \
    --format='value(projectNumber)' 2>/dev/null || true)"
  _budgets_list "$acct" > "$dir/budgets.json"
  _datasets_list > "$dir/datasets.json"
  if _emit_verdicts "$dir/budgets.json" "$dir/datasets.json" "$pnum"; then
    _log "verify: all counted rows OK ($dir)"
  else
    echo "cost-guard.sh: verify found non-OK rows ($dir)" >&2; return 1
  fi
}

# ---- dispatch -----------------------------------------------------------------

banner "cost guard (P34.5 / SIG-OPS-009)"

case "$MODE" in
  check)
    for a in prestate budget testbudget testbudget-delete dataset exportcheck; do
      "act_${a//-/_}"
    done
    _log "check OK"
    ;;
  verify)
    act_verify ;;
  apply)
    require_adc
    case "$ACTION" in
      prestate) act_prestate pre ;;
      budget) act_budget ;;
      testbudget) act_testbudget ;;
      testbudget-delete) act_testbudget_delete ;;
      dataset) act_dataset ;;
      exportcheck) act_exportcheck ;;
      all)
        act_prestate pre
        act_budget
        act_testbudget
        act_dataset
        act_prestate post
        MODE=verify act_verify || true
        act_exportcheck
        ;;
      *) echo "cost-guard.sh: unknown action '$ACTION'" >&2; _usage 64 ;;
    esac
    ;;
esac
