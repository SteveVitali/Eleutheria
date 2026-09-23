#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/domain-mapping.sh — point the custom domain surveillancegraph.org
# (+ www→apex) at the sig-web Cloud Run service with Google-managed TLS, via an
# external HTTPS Application Load Balancer + a serverless NEG (P27.10 / LAUNCH.10,
# ADR-098). Parameterised by $SIG_GCP_PROJECT / $SIG_WEB_DOMAIN (config.sh).
#
#   ./domain-mapping.sh --check    # (default) plan-only: prints every action, needs
#                                  # NO ADC, opens NO network, exits 0. The
#                                  # deterministic validation path (like provision.sh).
#   ./domain-mapping.sh --apply    # operator-gated: requires ADC; creates for real,
#                                  # idempotently, then prints the exact DNS records.
#   ./domain-mapping.sh --records  # apply-adjacent: print the DNS records the operator
#                                  # must add at Squarespace, reading the realized IP
#                                  # (requires ADC; no resource is created).
#
# WHY an LB and not a Cloud Run domain mapping (ADR-098): a Cloud Run domain mapping
# is zero-cost but requires the domain to be VERIFIED for the account first
# (`gcloud domains verify` — an interactive Search Console step the cloud-platform
# ADC cannot perform). The LB path needs no verification and reserves a real static
# IP that IS the apex/www A-record value, so the mapping can be applied now under the
# operator's ADC. The *.run.app URL stays the documented fallback origin.
#
# The domain + its DNS records are PUBLIC config, never secrets (HG-09): a public
# domain name may be written literally; only credentials stay Secret Manager refs.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

# Extend the shared mode parser with a --records verb (apply-adjacent, read-only).
_want_records=0
case "${1:-}" in
  --records) SIG_GCP_MODE=apply; _want_records=1; export SIG_GCP_MODE ;;
  *)         parse_mode "${1:-}" ;;
esac

require_project
require_adc

banner "domain-mapping (surveillancegraph.org → sig-web via external HTTPS LB, ADR-098)"

REGION="${SIG_GCP_REGION}"
PROJECT="${SIG_GCP_PROJECT}"
BACKEND_LINK="projects/${PROJECT}/global/backendServices/${SIG_LB_BACKEND}"

# `_exists <describe-cmd...>` — apply-mode existence probe. ALWAYS false in check
# mode (never queries the network), so the plan prints the full create sequence.
_exists() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 1
  "$@" >/dev/null 2>&1
}

# `import_url_map <name> <yaml> <desc>` — idempotent create-or-replace of a url map
# from YAML (the only way to express a defaultUrlRedirect). Writes a temp file only
# in apply mode; check mode just prints the plan (no file, no network).
import_url_map() {
  local name="$1" yaml="$2" desc="$3"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud compute url-maps import ${name} --global  (${desc})"
    return 0
  fi
  local tmp
  tmp="$(mktemp)"
  printf '%s\n' "${yaml}" >"${tmp}"
  _log "+ gcloud compute url-maps import ${name} --global  (${desc})"
  gcloud compute url-maps import "${name}" --global --source "${tmp}" \
    --project "${PROJECT}" --quiet
  rm -f "${tmp}"
}

# 1. Reserve a global external IPv4 — the stable apex/www A-record value.
provision_ip() {
  _log "-- Global static IP (the apex + www A-record value) --"
  if ! _exists gcloud compute addresses describe "${SIG_LB_IP}" --global --project "${PROJECT}"; then
    run gcloud compute addresses create "${SIG_LB_IP}" \
      --global --ip-version IPV4 --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_IP} — skipping create"
  fi
}

# 2. Serverless NEG → the sig-web Cloud Run service (regional).
provision_neg() {
  _log "-- Serverless NEG → ${SIG_WEB_SERVICE} (Cloud Run, ${REGION}) --"
  if ! _exists gcloud compute network-endpoint-groups describe "${SIG_LB_NEG}" \
      --region "${REGION}" --project "${PROJECT}"; then
    run gcloud compute network-endpoint-groups create "${SIG_LB_NEG}" \
      --region "${REGION}" --network-endpoint-type=serverless \
      --cloud-run-service="${SIG_WEB_SERVICE}" --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_NEG} — skipping create"
  fi
}

# 3. Global backend service wrapping the NEG (managed external scheme).
provision_backend() {
  _log "-- Backend service (EXTERNAL_MANAGED) --"
  if ! _exists gcloud compute backend-services describe "${SIG_LB_BACKEND}" \
      --global --project "${PROJECT}"; then
    run gcloud compute backend-services create "${SIG_LB_BACKEND}" \
      --global --load-balancing-scheme=EXTERNAL_MANAGED --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_BACKEND} — skipping create"
  fi
  # add-backend errors if the NEG is already attached — guard on the current backends.
  if [ "${SIG_GCP_MODE}" = "apply" ] && \
     gcloud compute backend-services describe "${SIG_LB_BACKEND}" --global \
       --project "${PROJECT}" --format='value(backends[].group)' 2>/dev/null \
       | grep -q "${SIG_LB_NEG}"; then
    _log "exists: ${SIG_LB_NEG} already attached to ${SIG_LB_BACKEND} — skipping add-backend"
  else
    run gcloud compute backend-services add-backend "${SIG_LB_BACKEND}" \
      --global --network-endpoint-group="${SIG_LB_NEG}" \
      --network-endpoint-group-region="${REGION}" --project "${PROJECT}"
  fi
}

# 4. Google-managed multi-domain TLS certificate (apex + www). Provisions to ACTIVE
#    only AFTER the DNS A records resolve to the LB IP (the gate-deferred half).
provision_cert() {
  _log "-- Google-managed TLS cert (${SIG_WEB_DOMAIN}, ${SIG_WEB_DOMAIN_WWW}) --"
  if ! _exists gcloud compute ssl-certificates describe "${SIG_LB_CERT}" \
      --global --project "${PROJECT}"; then
    run gcloud compute ssl-certificates create "${SIG_LB_CERT}" \
      --global --domains="${SIG_WEB_DOMAIN},${SIG_WEB_DOMAIN_WWW}" --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_CERT} — skipping create"
  fi
}

# 5. HTTPS url map: apex → backend; www → 301 redirect to apex (canonical origin).
provision_https_frontend() {
  _log "-- HTTPS url map + proxy + :443 forwarding rule --"
  import_url_map "${SIG_LB_URLMAP}" \
"name: ${SIG_LB_URLMAP}
defaultService: ${BACKEND_LINK}
hostRules:
- hosts:
  - ${SIG_WEB_DOMAIN}
  pathMatcher: apex
- hosts:
  - ${SIG_WEB_DOMAIN_WWW}
  pathMatcher: www-to-apex
pathMatchers:
- name: apex
  defaultService: ${BACKEND_LINK}
- name: www-to-apex
  defaultUrlRedirect:
    hostRedirect: ${SIG_WEB_DOMAIN}
    redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
    httpsRedirect: true
    stripQuery: false" \
    "apex→sig-web backend, www→apex 301"

  if ! _exists gcloud compute target-https-proxies describe "${SIG_LB_HTTPS_PROXY}" \
      --global --project "${PROJECT}"; then
    run gcloud compute target-https-proxies create "${SIG_LB_HTTPS_PROXY}" \
      --url-map="${SIG_LB_URLMAP}" --ssl-certificates="${SIG_LB_CERT}" \
      --global --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_HTTPS_PROXY} — skipping create"
  fi

  if ! _exists gcloud compute forwarding-rules describe "${SIG_LB_HTTPS_FR}" \
      --global --project "${PROJECT}"; then
    run gcloud compute forwarding-rules create "${SIG_LB_HTTPS_FR}" \
      --global --address="${SIG_LB_IP}" --target-https-proxy="${SIG_LB_HTTPS_PROXY}" \
      --ports=443 --load-balancing-scheme=EXTERNAL_MANAGED --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_HTTPS_FR} — skipping create"
  fi
}

# 6. HTTP :80 → HTTPS 301 redirect (never serve plaintext).
provision_http_redirect() {
  _log "-- HTTP→HTTPS redirect url map + proxy + :80 forwarding rule --"
  import_url_map "${SIG_LB_REDIRECT_URLMAP}" \
"name: ${SIG_LB_REDIRECT_URLMAP}
defaultUrlRedirect:
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  httpsRedirect: true
  stripQuery: false" \
    "all :80 → HTTPS 301"

  if ! _exists gcloud compute target-http-proxies describe "${SIG_LB_HTTP_PROXY}" \
      --global --project "${PROJECT}"; then
    run gcloud compute target-http-proxies create "${SIG_LB_HTTP_PROXY}" \
      --url-map="${SIG_LB_REDIRECT_URLMAP}" --global --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_HTTP_PROXY} — skipping create"
  fi

  if ! _exists gcloud compute forwarding-rules describe "${SIG_LB_HTTP_FR}" \
      --global --project "${PROJECT}"; then
    run gcloud compute forwarding-rules create "${SIG_LB_HTTP_FR}" \
      --global --address="${SIG_LB_IP}" --target-http-proxy="${SIG_LB_HTTP_PROXY}" \
      --ports=80 --load-balancing-scheme=EXTERNAL_MANAGED --project "${PROJECT}"
  else
    _log "exists: ${SIG_LB_HTTP_FR} — skipping create"
  fi
}

# The exact Squarespace DNS records, with realized values (the reserved static IP).
print_dns_records() {
  local ip="<reserved-after-apply — run with --apply or --records>"
  if [ "${SIG_GCP_MODE}" = "apply" ]; then
    ip="$(gcloud compute addresses describe "${SIG_LB_IP}" --global \
      --project "${PROJECT}" --format='value(address)' 2>/dev/null || echo "${ip}")"
  fi
  _log ""
  _log "=============================================================="
  _log "Squarespace DNS records the operator must add (HG-11 / Go-public)"
  _log "  registrar + DNS = Squarespace; these are PUBLIC config (HG-09)"
  _log "--------------------------------------------------------------"
  _log "  Host   Type   Value"
  _log "  @      A      ${ip}"
  _log "  www    A      ${ip}"
  _log "--------------------------------------------------------------"
  _log "  The apex (@) cannot be a CNAME, so it is an A record to the LB"
  _log "  static IP; www is an A record to the same IP and the LB 301-"
  _log "  redirects www→apex. No verification TXT is needed (LB path)."
  _log "  Google-managed TLS on ${SIG_LB_CERT} provisions to ACTIVE only"
  _log "  AFTER these records resolve (allow up to ~60 min) — check with:"
  _log "    gcloud compute ssl-certificates describe ${SIG_LB_CERT} \\"
  _log "      --global --format='value(managed.status)'"
  _log "=============================================================="
}

if [ "${_want_records}" = "1" ]; then
  print_dns_records
  exit 0
fi

provision_ip
provision_neg
provision_backend
provision_cert
provision_https_frontend
provision_http_redirect
print_dns_records

_log ""
if [ "${SIG_GCP_MODE}" = "check" ]; then
  _log "check OK — plan printed, no ADC used, no network touched. Real apply is"
  _log "gate-pending on operator ADC (HG-12) + the operator's Squarespace DNS add"
  _log "(HG-11 / Go-public). Exit 0."
else
  _log "apply complete — the LB fronts ${SIG_WEB_SERVICE}; add the DNS records above."
fi
