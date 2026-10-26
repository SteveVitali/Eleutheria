#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# ops/gcp/web-cutover.sh — the P35.59 (REL-09, OM-20-named) dark-cutover leg:
# the public site flips from the flat bucket-root serve to the release layout
# with ZERO visible change. One leg, in order:
#
#   AR-2 prestate  →  floor import  →  conf/0 compose + retirement record
#                 →  sig-web digest roll onto the templated image
#                 →  byte-compare every allow-listed route on both origins
#
# Any byte difference on any probed route fails the leg and prints the
# recorded rollback (a traffic move to the still-running prior revision —
# the whole pre-roll spec restores: image, env, mounts — never a traffic
# *reversion to edited config*, and RR-7's re-deny concern does not apply
# to the pre-cutover config the rollback restores).
#
#   ./web-cutover.sh --check [action]   # (default) plan-only: NO ADC, NO network.
#   ./web-cutover.sh --apply <action>   # windowed + operator ADC.
#
# Actions:
#   prestate   `run services describe sig-web` (revision + digest + env +
#              mounts), the URL map export (the P34.40 /v1/* evidence),
#              route-compare captures of every allow-listed route on the
#              canonical origin and the run.app URL, and the live-tree
#              snapshot (gcloud storage rsync → <state>/floor-src/) with its
#              object count + sha256 manifest. READ-ONLY on the bucket.
#   import     `sig-ops release import-floor` the snapshot under
#              staged/v/legacy-<date>/ (create-if-absent; resumable).
#   compose    `sig-ops release cutover` — genesis conf/0, the staged/conf
#              carry, registry/serving.json (the publish-class retirement
#              declaration), the roll intent.
#   roll       `ops/gcp/web.sh --apply image` (the templated image build by
#              git archive → pinned digest) then `gcloud run deploy` —
#              sig-web's volume-mounts read live and replaced (never
#              guessed): <project>-sig-release at /mnt/rel, env
#              SIG_LATEST_PUB=legacy-<date> SIG_CONF_GEN=0 SIG_STAGING=0,
#              min-instances=1.
#   poststate  describe again + capture + `route-compare verify` on BOTH
#              origins — 0 differences or the leg FAILS and the rollback
#              is printed.
#   rollback   print the recorded rollback (traffic → the prior revision).
#   all        prestate → import → compose → roll → poststate (the leg).
#
# Live window (OM-19/AR-3): applies run only on a weekday inside
# 14:00–20:00Z, never 03:00–06:30Z, and ≥ SIG_CUTOVER_EARLIEST; otherwise
# exit 42 (queued — the re-run prompt is printed). SIG_CUTOVER_NOW
# overrides the clock for the offline guard test only.
set -euo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/gcp/config.sh
. "${_here}/config.sh"
# shellcheck source=ops/gcp/lib.sh
. "${_here}/lib.sh"

parse_mode "${1:-}"
shift || true
ACTION="${1:-all}"
STATE_DIR="${2:-${SIG_CUTOVER_STATE_DIR:-${TMPDIR:-/tmp}/p35.59-cutover}}"

_repo="$(cd "${_here}/../.." && pwd)"

# The leg's own knobs (declared in config.sh's P34.40/P35.53 blocks):
#   SIG_CUTOVER_EARLIEST  the AR-3 window floor (default: the shared freeze end)
#   SIG_CUTOVER_LABEL     the floor label (default: legacy-<date -u +%Y%m%d>)
#   SIG_CUTOVER_GO        the registry/authorities/ record the verbs check
SIG_CUTOVER_EARLIEST="${SIG_CUTOVER_EARLIEST:-${SIG_LB_EARLIEST}}"
SIG_CUTOVER_LABEL="${SIG_CUTOVER_LABEL:-legacy-$(date -u +%Y%m%d)}"
SIG_CUTOVER_GO="${SIG_CUTOVER_GO:-}"

RERUN='implement-spec spec=docs/tickets/336_P35.59__dark-cutover-to-release-layout.md live_verification=true'

_sigops() {
  (cd "${_repo}" && uv run --quiet sig-ops "$@")
}

# `assert_window` — the OM-19/AR-3 clock guard, stricter than web-roll's:
# a weekday inside the preferred 14:00–20:00Z band, never 03:00–06:30Z,
# and ≥ the freeze end. Check mode is never gated — a printed plan mutates
# nothing. Exit 42 = queued leg.
assert_window() {
  [ "${SIG_GCP_MODE}" = "apply" ] || return 0
  local now hour dow
  now="${SIG_CUTOVER_NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if [[ "${now}" < "${SIG_CUTOVER_EARLIEST}" ]]; then
    _log "QUEUED (exit 42): now=${now} < ${SIG_CUTOVER_EARLIEST} — the AR-3 freeze."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  dow="$(date -u -d "${now}" +%u 2>/dev/null || date -u -jf "%Y-%m-%dT%H:%M:%SZ" "${now}" +%u)"
  hour="${now:11:2}${now:14:2}"
  if [ "${dow}" -ge 6 ] || [ "${hour}" -lt 1400 ] || [ "${hour}" -ge 2000 ] \
    || { [ "${hour}" -ge 300 ] && [ "${hour}" -lt 630 ]; }; then
    _log "QUEUED (exit 42): ${now} is outside the AR-3 preferred window"
    _log "  (weekday 14:00–20:00Z, never 03:00–06:30Z)."
    _log "re-run: ${RERUN}"
    exit 42
  fi
  _log "window OK: ${now} (weekday ${dow}, inside 14:00–20:00Z, ≥ ${SIG_CUTOVER_EARLIEST})"
}

_go_args() {
  if [ -z "${SIG_CUTOVER_GO}" ]; then
    _log "ERROR: SIG_CUTOVER_GO must name the operator's registry/authorities/"
    _log "  go record (the OM-20 listing) — the verbs check it, never create it."
    exit 2
  fi
  printf -- '--go %s' "${SIG_CUTOVER_GO}"
}

_runapp_url() {
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"]["url"])' \
    "${STATE_DIR}/sig-web-$1.json"
}

do_prestate() {
  _log "-- prestate (AR-2): service spec + URL map + route baseline + live tree --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_WEB_SERVICE} --format json > ${STATE_DIR}/sig-web-pre.json"
    _plan "gcloud compute url-maps export ${SIG_LB_URLMAP} > ${STATE_DIR}/urlmap-pre.yaml  # the P34.40 /v1/* evidence"
    _plan "sig-ops route-compare capture --base https://${SIG_WEB_DOMAIN} --out ${STATE_DIR}/routes-canonical-pre.json"
    _plan "sig-ops route-compare capture --base <run.app> --out ${STATE_DIR}/routes-runapp-pre.json"
    _plan "gcloud storage rsync --recursive gs://${SIG_BUCKET_WEB} ${STATE_DIR}/floor-src/  # the then-live root tree"
    _plan "manifest: object count + sha256 map of floor-src/ > ${STATE_DIR}/floor-manifest.json"
    return 0
  fi
  mkdir -p "${STATE_DIR}"
  gcloud run services describe "${SIG_WEB_SERVICE}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/sig-web-pre.json"
  python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
c = s["spec"]["template"]["spec"]["containers"][0]
print("   prior image:", c["image"])
print("   prior revision:", s["status"]["latestReadyRevisionName"])
print("   prior env:", {e["name"]: e.get("value") for e in c.get("env", [])})
print("   prior mounts:", c.get("volumeMounts", []))' \
    "${STATE_DIR}/sig-web-pre.json"
  gcloud compute url-maps export "${SIG_LB_URLMAP}" \
    --project "${SIG_GCP_PROJECT}" --destination "${STATE_DIR}/urlmap-pre.yaml"
  _sigops route-compare capture --base "https://${SIG_WEB_DOMAIN}" \
    --out "${STATE_DIR}/routes-canonical-pre.json"
  _sigops route-compare capture --base "$(_runapp_url pre)" \
    --out "${STATE_DIR}/routes-runapp-pre.json"
  _log "-- snapshot: the then-live root tree (read-only on the bucket) --"
  rm -rf "${STATE_DIR}/floor-src"
  gcloud storage rsync --recursive "gs://${SIG_BUCKET_WEB}" "${STATE_DIR}/floor-src"
  python3 - "${STATE_DIR}" <<'PY'
import hashlib, json, sys
from pathlib import Path
state = Path(sys.argv[1])
src = state / "floor-src"
files = sorted(p for p in src.rglob("*") if p.is_file())
manifest = {
    "schema": "sig.floor-snapshot/1",
    "objects": len(files),
    "bytes": sum(p.stat().st_size for p in files),
    "tree_sha256": hashlib.sha256(
        b"".join(
            p.relative_to(src).as_posix().encode() + b"\0" + p.read_bytes() + b"\0"
            for p in files
        )
    ).hexdigest(),
    "entries": [
        {
            "name": p.relative_to(src).as_posix(),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "bytes": p.stat().st_size,
        }
        for p in files
    ],
}
(state / "floor-manifest.json").write_text(json.dumps(manifest, indent=1))
print(f"   floor snapshot: {manifest['objects']} objects, {manifest['bytes']} bytes,")
print(f"   tree sha256 {manifest['tree_sha256'][:24]}…")
PY
  _log "   prestate recorded under ${STATE_DIR} (date -u: $(date -u +%FT%TZ))"
}

do_import() {
  _log "-- import: staged/v/${SIG_CUTOVER_LABEL}/ ← the live snapshot (create-if-absent) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "sig-ops release import-floor --registry <release-registry> --from ${STATE_DIR}/floor-src \\"
    _plan "  --label ${SIG_CUTOVER_LABEL} --apply --go <OM-20 authority record>"
    return 0
  fi
  # shellcheck disable=SC2046  # _go_args emits exactly two words
  _sigops release import-floor --registry "${SIG_RELEASE_REGISTRY_URI}" \
    --from "${STATE_DIR}/floor-src" --label "${SIG_CUTOVER_LABEL}" \
    --apply $(_go_args)
}

do_compose() {
  _log "-- compose: conf/0 + staged/conf carry + serving.json (the retirement) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "sig-ops release cutover --registry <release-registry> --label ${SIG_CUTOVER_LABEL} \\"
    _plan "  --apply --go <authority> --release-bucket ${SIG_BUCKET_RELEASE} --mount-path ${SIG_RELEASE_MOUNT}"
    return 0
  fi
  # shellcheck disable=SC2046  # _go_args emits exactly two words
  _sigops release cutover --registry "${SIG_RELEASE_REGISTRY_URI}" \
    --label "${SIG_CUTOVER_LABEL}" --apply $(_go_args) \
    --service "${SIG_WEB_SERVICE}" --release-bucket "${SIG_BUCKET_RELEASE}" \
    --mount-path "${SIG_RELEASE_MOUNT}" \
    --project "${SIG_GCP_PROJECT}" --region "${SIG_GCP_REGION}"
}

do_roll() {
  assert_window
  _log "-- roll: templated sig-web by digest; mounts read live + replaced --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "ops/gcp/web.sh --apply image   # Cloud Build sig-web:<sha12> (the templated image)"
    _plan "gcloud run deploy ${SIG_WEB_SERVICE} --image <pinned digest> \\"
    _plan "  --remove-volume-mount <each live> --remove-volume <each live> \\"
    _plan "  --add-volume name=rel,type=cloud-storage,bucket=${SIG_BUCKET_RELEASE} \\"
    _plan "  --add-volume-mount volume=rel,mount-path=${SIG_RELEASE_MOUNT} \\"
    _plan "  --update-env-vars SIG_CONF_GEN=0,SIG_LATEST_PUB=${SIG_CUTOVER_LABEL},SIG_STAGING=0,SIG_LATEST_LABEL=${SIG_CUTOVER_LABEL} \\"
    _plan "  --min-instances 1 --port 8080 --ingress all --allow-unauthenticated \\"
    _plan "  --service-account ${SIG_WEB_SA_EMAIL}"
    return 0
  fi
  # Build the templated image (same image web.sh deploys — the Dockerfile
  # ships the template + the legacy config the entrypoint selects between).
  "${_here}/web.sh" --apply image
  local _sha pinned
  _sha="$(git -C "${_repo}" rev-parse --short=12 HEAD)"
  pinned="$(pin_image_digest "${SIG_AR_HOST}/${SIG_GCP_PROJECT}/${SIG_AR_REPO}/sig-web:${_sha}")"
  _log "   pinned: ${pinned}"
  # Remove every LIVE volume-mount + volume by its live name/path (read
  # back from the service — never guessed), then declare the release mount.
  local -a rm_args=()
  local mp vn
  while IFS= read -r mp; do
    [ -n "${mp}" ] && rm_args+=(--remove-volume-mount "${mp}")
  done < <(python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
for c in s["spec"]["template"]["spec"].get("containers", []):
    for m in c.get("volumeMounts", []):
        print(m["mountPath"])' "${STATE_DIR}/sig-web-pre.json")
  while IFS= read -r vn; do
    [ -n "${vn}" ] && rm_args+=(--remove-volume "${vn}")
  done < <(python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
for v in s["spec"]["template"]["spec"].get("volumes", []):
    print(v["name"])' "${STATE_DIR}/sig-web-pre.json")
  _log "   live mounts/volumes to replace: ${rm_args[*]:-none}"
  run gcloud run deploy "${SIG_WEB_SERVICE}" \
    --image "${pinned}" --region "${SIG_GCP_REGION}" --project "${SIG_GCP_PROJECT}" \
    --service-account "${SIG_WEB_SA_EMAIL}" \
    --port 8080 --ingress all --allow-unauthenticated --min-instances 1 \
    ${rm_args[@]+"${rm_args[@]}"} \
    --add-volume "name=rel,type=cloud-storage,bucket=${SIG_BUCKET_RELEASE}" \
    --add-volume-mount "volume=rel,mount-path=${SIG_RELEASE_MOUNT}" \
    --update-env-vars "SIG_CONF_GEN=0,SIG_LATEST_PUB=${SIG_CUTOVER_LABEL},SIG_STAGING=0,SIG_LATEST_LABEL=${SIG_CUTOVER_LABEL}"
}

do_poststate() {
  _log "-- poststate: describe + byte-compare verify on BOTH origins (0 diffs) --"
  if [ "${SIG_GCP_MODE}" = "check" ]; then
    _plan "gcloud run services describe ${SIG_WEB_SERVICE} --format json > ${STATE_DIR}/sig-web-post.json"
    _plan "sig-ops route-compare capture → verify: canonical + run.app, pre vs post"
    _plan "any difference → do_rollback (the leg FAILS — nothing is patched over)"
    return 0
  fi
  gcloud run services describe "${SIG_WEB_SERVICE}" --region "${SIG_GCP_REGION}" \
    --project "${SIG_GCP_PROJECT}" --format json > "${STATE_DIR}/sig-web-post.json"
  python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
c = s["spec"]["template"]["spec"]["containers"][0]
print("   new image:", c["image"])
print("   new revision:", s["status"]["latestReadyRevisionName"])
print("   new env:", {e["name"]: e.get("value") for e in c.get("env", [])})
print("   new mounts:", c.get("volumeMounts", []))' \
    "${STATE_DIR}/sig-web-post.json"
  _sigops route-compare capture --base "https://${SIG_WEB_DOMAIN}" \
    --out "${STATE_DIR}/routes-canonical-post.json"
  _sigops route-compare capture --base "$(_runapp_url post)" \
    --out "${STATE_DIR}/routes-runapp-post.json"
  local failed=0
  _sigops route-compare verify \
    --a "${STATE_DIR}/routes-canonical-pre.json" \
    --b "${STATE_DIR}/routes-canonical-post.json" || failed=1
  _sigops route-compare verify \
    --a "${STATE_DIR}/routes-runapp-pre.json" \
    --b "${STATE_DIR}/routes-runapp-post.json" || failed=1
  if [ "${failed}" -ne 0 ]; then
    _log "FAIL: a byte difference was measured — the leg fails, nothing is"
    _log "  patched over. Run the recorded rollback NOW:"
    do_rollback || true
    exit 1
  fi
  _log "poststate OK — every allow-listed route byte-identical on both origins."
  _log "serving path retired by registry/serving.json; the legacy bucket stays"
  _log "  untouched as the 90-day rollback floor (D-R11-LATER-20 clock starts"
  _log "  from the landing record's date -u: $(date -u +%FT%TZ))."
}

do_rollback() {
  _log "-- rollback: traffic back to the still-running prior revision --"
  local prior_rev prior_img
  prior_rev="$(python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
print(s["status"]["latestReadyRevisionName"])' \
    "${STATE_DIR}/sig-web-pre.json" 2>/dev/null || true)"
  prior_img="$(python3 -c 'import json,sys
s = json.load(open(sys.argv[1]))
print(s["spec"]["template"]["spec"]["containers"][0]["image"])' \
    "${STATE_DIR}/sig-web-pre.json" 2>/dev/null || true)"
  if [ -z "${prior_rev}" ]; then
    if [ "${SIG_GCP_MODE}" = "check" ]; then
      prior_rev="<latestReadyRevisionName recorded in ${STATE_DIR}/sig-web-pre.json>"
      prior_img="<image@sha256 recorded in ${STATE_DIR}/sig-web-pre.json>"
    else
      _log "ERROR: no recorded prior revision at ${STATE_DIR}/sig-web-pre.json" >&2
      exit 4
    fi
  fi
  _log "PRIMARY — instant, restores image+env+mounts wholesale (the prior"
  _log "  revision still exists; the floor import is additive and stays):"
  _log "  gcloud run services update-traffic ${SIG_WEB_SERVICE} \\"
  _log "    --to-revisions ${prior_rev}=100 \\"
  _log "    --region ${SIG_GCP_REGION} --project ${SIG_GCP_PROJECT}"
  _log "FALLBACK — only if the prior revision was purged: redeploy the"
  _log "  recorded prior image with the prestate env/mounts restored from"
  _log "  ${STATE_DIR}/sig-web-pre.json:"
  _log "  gcloud run deploy ${SIG_WEB_SERVICE} --image ${prior_img} \\"
  _log "    --region ${SIG_GCP_REGION} --project ${SIG_GCP_PROJECT} \\"
  _log "    (then re-declare the prestate volume-mounts + env verbatim)"
}

require_project
# The clock guard precedes the ADC gate so a queued apply exits 42 cleanly.
case "${ACTION}" in
  import|compose|roll|all) assert_window ;;
esac
require_adc

banner "P35.59 — dark cutover to the release layout (REL-09, OM-20-named)"

case "${ACTION}" in
  prestate)  do_prestate ;;
  import)    do_import ;;
  compose)   do_compose ;;
  roll)      do_roll ;;
  poststate) do_poststate ;;
  rollback)  do_rollback ;;
  all)
    do_prestate
    do_import
    do_compose
    do_roll
    do_poststate ;;
  *) _log "usage: $(basename "$0") [--check|--apply] [prestate|import|compose|roll|poststate|rollback|all] [state-dir]" >&2; exit 64 ;;
esac

_log "web-cutover ${ACTION}: done (mode=${SIG_GCP_MODE})"
