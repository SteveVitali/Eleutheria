# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/lib.sh — the idempotent-`gcloud` plumbing shared by the IaC scripts
# (P24.1 / DEPLOY.1, ADR-075). The design goal is a validation path that runs to
# green WITHOUT Application Default Credentials (ADC): in `--check` mode every
# would-be side effect is PRINTED, not executed, and the script exits 0. The real
# `apply` is gate-pending on operator ADC (D-ACCT.1-1 / HG-12) and is never run by
# an isolated subagent.
#
# shellcheck shell=bash

set -euo pipefail

# --- mode --------------------------------------------------------------------
# MODE is `check` (default: plan-only, no ADC, no network, exit 0) or `apply`
# (requires ADC; the operator's gated path). Callers set it from their args.
: "${SIG_GCP_MODE:=check}"

# Colour-free, greppable log lines so the validation test can assert the plan.
_log()  { printf '%s\n' "$*"; }
_plan() { printf 'PLAN: %s\n' "$*"; }

# `run <cmd...>` — in check mode print the planned command and return 0 without
# touching gcloud or the network; in apply mode execute it for real.
run() {
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "$*"
    return 0
  fi
  _log "+ $*"
  "$@"
}

# `require_project` — fail closed if the env-parameterised project id is absent.
# In check mode a missing project is tolerated (the plan is still printable with
# an <unset> placeholder) so validation needs no credentials or project at all.
require_project() {
  if [ -z "${SIG_GCP_PROJECT:-}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      export SIG_GCP_PROJECT="<SIG_GCP_PROJECT-unset>"
      _log "note: SIG_GCP_PROJECT is unset — check mode uses a placeholder id."
    else
      _log "ERROR: SIG_GCP_PROJECT must be exported before an apply (GL-GATE-04)." >&2
      exit 2
    fi
  fi
}

# `require_adc` — the apply gate. In check mode this is a NO-OP (the whole point
# is to validate without credentials). In apply mode, if no ADC is present the
# script refuses with a gate-pending message and exits 3 (it NEVER fabricates a
# deploy). The operator provides ADC via `gcloud auth application-default login`.
require_adc() {
  [ "${SIG_GCP_MODE}" = "check" ] && return 0
  if ! command -v gcloud >/dev/null 2>&1; then
    _log "ERROR: gcloud is not on PATH; cannot apply." >&2
    exit 3
  fi
  if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    _log "gate pending: HG-12 / D-ACCT.1-1 — no Application Default Credentials." >&2
    _log "Run \`gcloud auth application-default login\` then re-run with --apply." >&2
    exit 3
  fi
}

# `parse_mode "$@"` — read a leading --check/--apply/--dry-run flag into MODE.
parse_mode() {
  case "${1:-}" in
    --apply)          SIG_GCP_MODE=apply ;;
    --check|--dry-run|"") SIG_GCP_MODE=check ;;
    *) _log "usage: $(basename "$0") [--check|--dry-run|--apply]" >&2; exit 64 ;;
  esac
  export SIG_GCP_MODE
}

# `pin_image_digest <ref>` — print the pinned `<repo>@sha256:<digest>` a Cloud Run job
# or service deploys (P31.4 / ADR-111): never `:latest`, never an untagged ref. A
# digest ref is printed as is; a tag is resolved through Artifact Registry. In check
# mode nothing is resolved: a placeholder digest is printed so the plan stays offline.
pin_image_digest() {
  local ref="$1"
  case "${ref}" in
    *@sha256:*) printf '%s' "${ref}"; return 0 ;;
    *:latest) _log "ERROR: ${ref} is :latest — deploy by pinned digest only (ADR-111)." >&2; return 2 ;;
  esac
  case "${ref##*/}" in
    *:*) ;;
    *) _log "ERROR: ${ref} has no tag or digest." >&2; return 2 ;;
  esac
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    printf '%s@sha256:<digest-of-%s>' "${ref%:*}" "${ref##*:}"
    return 0
  fi
  local digest
  digest="$(gcloud artifacts docker images describe "${ref}" --project "${SIG_GCP_PROJECT}" \
    --format='value(image_summary.fully_qualified_digest)')"
  case "${digest}" in
    *@sha256:*) printf '%s' "${digest}" ;;
    *) _log "ERROR: could not resolve ${ref} to a digest." >&2; return 2 ;;
  esac
}

# `security_sign_image <digest-ref>` — the P37.4a deploy-path signing hook
# (ADR-231). Armed when SIG_SECB_SIGNING=1: the caller signs the just-deployed
# digest with cosign under the Cloud KMS key (key material never leaves GCP)
# and verifies the signature lands. Unarmed: the planned commands are printed
# so every deploy plan honestly shows the pending baseline leg (never silently
# absent). A sign/verify failure refuses the deploy leg — an unsigned deploy is
# a loud failure once armed, never smoothed.
security_sign_image() {
  local image="$1"
  if [ "${SIG_SECB_SIGNING:-0}" != "1" ]; then
    _plan "cosign sign --yes --key ${SIG_COSIGN_KEY_URI} ${image}   # pending baseline leg (SIG_SECB_SIGNING!=1)"
    _plan "cosign verify --key ${SIG_COSIGN_KEY_URI} ${image} --insecure-ignore-tlog --insecure-ignore-sct"
    return 0
  fi
  run cosign sign --yes --key "${SIG_COSIGN_KEY_URI}" "${image}"
  run cosign verify --key "${SIG_COSIGN_KEY_URI}" "${image}" \
    --insecure-ignore-tlog --insecure-ignore-sct
}

# `banner <title>` — a stable header for the plan output.
banner() {
  _log "=============================================================="
  _log "SIG GCP IaC — $* (mode=${SIG_GCP_MODE})"
  _log "  project=${SIG_GCP_PROJECT:-<unset>} region=${SIG_GCP_REGION} zone=${SIG_GCP_ZONE}"
  _log "=============================================================="
}
