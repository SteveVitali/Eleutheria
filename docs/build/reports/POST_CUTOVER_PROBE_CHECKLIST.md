<!--
  docs/build/reports/POST_CUTOVER_PROBE_CHECKLIST.md — P35.67 (row 263).
  The committed checklist the `sig-ops post-cutover-probe` verb executes:
  every check is a READ-ONLY probe (dig / curl -sSI / openssl s_client /
  gcloud … describe / whois) — the probe issues no mutating command, ever
  (tests/ops/test_post_cutover_probe.py pins the argv contract). The
  post-switch expectations come from DNS_CUTOVER_RUNBOOK.md (OP-09); a
  check whose tool or credential is absent reports "skipped", never a
  fabricated pass.
-->
# Post-DNS cutover probe checklist — P35.67

**Legs.** **L1** runs once, after the operator's OP-09 nameserver switch
(`D-P34.50-1`); **L2** is the managed-cert renewal read ≈ **2026-11-22**
(30 days before the `sig-web-cert` expiry **2026-12-22** — the P34.4
TLS-expiry alert firing ≈ 2026-12-01 is the tripwire if renewal slips).

**Run:**

```bash
# L1 — the full post-switch checklist (after OP-09; read-only)
SIG_GCP_PROJECT=$SIG_GCP_PROJECT \
  sig-ops post-cutover-probe --leg l1 \
    --capture docs/build/logs/post-cutover-L1 \
    --out    docs/build/logs/post-cutover-L1/probe-run.json

# L2 — the cert-renewal read (~2026-11-22)
SIG_GCP_PROJECT=$SIG_GCP_PROJECT \
  sig-ops post-cutover-probe --leg l2 \
    --capture docs/build/logs/post-cutover-L2 \
    --out    docs/build/logs/post-cutover-L2/probe-run.json

# replay a captured run offline (no commands executed):
sig-ops post-cutover-probe --leg l1 --from-capture docs/build/logs/post-cutover-L1
```

The record is a `sig.probe-run/1` document (SIG-OPS-011); its output +
`date -u` stamps land in this row's `docs/build/runs/P35.67.md` ledger
entry. `--domain` / `--expected-ip` / `--cert` / `--project` are
env-overridable (`SIG_WEB_DOMAIN`, `SIG_WEB_EXPECTED_IP`, `SIG_LB_CERT`,
`SIG_GCP_PROJECT`) so the same probe measures a staging endpoint per the
HG-12 convention.

## L1 checks ← runbook post-switch checklist

| runbook step | check | read | passes when |
|---|---|---|---|
| 8 (the switch) | `ns_pair` | `dig +noall +answer <apex> NS` | every NS is a `*.ns.cloudflare.com` host; `state: pre_cutover` when Squarespace still serves |
| 9/10 | `apex_a`, `www_a` | `dig +noall +answer {apex,www} A` | the answer is exactly `136.81.80.102` |
| 14 (grey-cloud) | inside `apex_a`/`www_a` | same A answers | a Cloudflare anycast address (104.\*/172.64.\*/188.114.\*/…) fails — the record must stay DNS-only or the managed cert's renewal can silently break |
| 11 | `www_redirect` | `curl -sSI https://www.<apex>/` | `301` → `https://<apex>/` (a `:443` port in Location is equivalent) |
| 12 | `apex_https` | `curl -sSI https://<apex>/` | `200` on the canonical origin |
| 12 | `apex_https_tls` | `openssl s_client … \| openssl x509 -noout -dates -ext subjectAltName` | SAN covers `{apex, www}`; `notAfter` recorded |
| 15 | `http_redirect` | `curl -sSI http://<apex>/` | `301` → `https://<apex>/` |
| 13 | `dnssec` | `dig +dnssec <apex> A` + `dig <apex> DS` | `ad` flag + RRSIG present; a non-`17039` (Cloudflare) DS at the parent — `rollover_in_progress` records the double-DS mid-state |
| cert renewal | `cert_status` | `gcloud compute ssl-certificates describe sig-web-cert --global --format=json` | `managed.status = ACTIVE` and every `domainStatus` ACTIVE; `expireTime` recorded (skipped when no ADC — never fabricated) |
| every public route | `routes` | `GET sitemap.xml`/`sitemap-index.xml` (+ one level of sub-sitemaps), then `curl -sSI` per `<loc>` | every advertised route serves 2xx/3xx; when no sitemap is served the sweep falls back to the `ops/public_routes.toml` allowlist, where deliberate 4xx answers record `absent` and 5xx/unreachable fails |
| mail | `mail` | `dig <apex> MX` + `dig <apex> TXT` | `no_mail` (empty MX + `v=spf1 -all`, the pre-OP-10 design) or `op10_configured` (MX present + an SPF record — the `contact@` alias landed); MX-without-SPF or missing-SPF-without-MX fails |
| registrar | `registrar_lock` | `whois <apex>` `Domain Status:` lines | no `pendingTransfer`/`serverHold`/`clientHold`/`redemptionPeriod`/`pendingDelete` (lock/transfer drift) |

## L2 checks (cert-renewal read)

| check | read | passes when |
|---|---|---|
| `ns_pair` | as L1 | the Cloudflare pair still serves (sanity) |
| `apex_https_tls` | as L1 | the served cert still covers `{apex, www}`; `notAfter` recorded — a renewed cert shows a later date than `2026-12-22T18:47:21Z` |
| `cert_status` | `gcloud … describe sig-web-cert` | `managed.status = ACTIVE` |
| `renewal_read` | derived from `cert_status` | `ACTIVE` → renewal on track; anything else fails and means the P34.4 ~21-day alert should already be firing — the record says which |

## Exit codes

`0` when `overall` is `pass` or `partial` (a `skipped` leg); `1` on `fail`.
A `fail` before OP-09 is the expected pre-cutover answer — `ns_pair` reports
`state: pre_cutover` and `cutover_detected: not_detected`.

## Evidence handling

`--capture <dir>` writes every raw command output (`dig_*.txt`,
`curl_*.txt`, `openssl_apex.txt`, `gcloud_cert.txt`, `whois.txt`,
`routes.tsv` + `route_*.txt`/`sitemap_*.txt`) under that directory;
`--from-capture <dir>` replays the identical record offline. The capture
directory is citable verbatim in the run ledger — the committed fixtures
under `tests/ops/fixtures/post_cutover/` are in exactly this format.
