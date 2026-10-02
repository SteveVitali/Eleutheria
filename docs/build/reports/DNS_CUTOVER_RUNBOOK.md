<!--
  docs/build/reports/DNS_CUTOVER_RUNBOOK.md — P34.50 (row 208), for OP-09.
  OPERATOR-EXECUTED runbook: the operator moves `surveillancegraph.org` from
  Squarespace DNS to Cloudflare DNS by GATE-G4 (plan §10.2, FEA-08 — the
  highest-blast-radius change in the plan). Agents never execute it. Every
  value cited is from the dated inventory `dns/zone_inventory_2026-10-02.md`
  (re-run its queries at execution time — this file names the shape, the
  inventory names the day-of facts). A test pins these sections:
  tests/unit/test_dns_cutover.py.
-->
# DNS cut-over runbook — OP-09: `surveillancegraph.org` → Cloudflare DNS

**Who:** the operator (OP-09). **When:** by GATE-G4, before P35.5's R2 leg.
**Blast radius:** highest in the plan (FEA-08) — a wrong record, a proxied LB
hostname, or a dropped DS breaks the public site and/or the Google-managed
certificate, which expires **2026-12-22** and must keep renewing.

**Inputs.** The dated zone inventory `dns/zone_inventory_<date>.md` (today's:
[`zone_inventory_2026-10-02.md`](dns/zone_inventory_2026-10-02.md)) — run the
queries it records again on the day and treat the fresher answers as truth.
Registrar + current DNS provider: **Squarespace Domains LLC**; current NS
`nsc1–nsc4.squarespacedns.com`; zone is **DNSSEC-signed** (DS `17039 8 2 …` at
the .org parent). One page of DNS changes nothing in GCP or Cloudflare.

## The grey-cloud rule — read first

The Google managed certificate (`sig-web-cert`, apex + www) renews only while
the load-balancer authorisation keeps seeing the domain resolve to the LB IP
`136.81.80.102`. **The `@` and `www` records stay DNS-only (grey cloud)
forever** — a proxied (orange-cloud) record makes Google see Cloudflare
anycast IPs, and renewal before 2026-12-22 can fail silently. Never proxy
them, not "temporarily", not to test.

## TTL step-down + pre-switch checklist — T‑48 h (start of the window)

| # | step | verify |
|---|---|---|
| 1 | Re-run the inventory queries; confirm the day-of answers match `dns/zone_inventory_<date>.md` (apex/www `A` → `136.81.80.102`, TXT `v=spf1 -all`, DS present, NS squarespacedns). | `dig +noall +answer surveillancegraph.org A` → `136.81.80.102`; `dig +noall +answer surveillancegraph.org DS` → `17039 8 2 …` |
| 2 | Add `surveillancegraph.org` to the Cloudflare account; note the two assigned `*.ns.cloudflare.com` nameservers. Do **not** change the registrar yet. | `dig +noall +answer surveillancegraph.org NS` still → `nsc1–nsc4.squarespacedns.com.` (nothing moved) |
| 3 | Recreate every record in the Cloudflare zone exactly as the inventory lists it: `@ A 136.81.80.102`, `www A 136.81.80.102`, `@ TXT "v=spf1 -all"` — plus anything the Squarespace console shows that public queries do not answer (the console, not the inventory, is complete). | In the Cloudflare dashboard each of `@`/`www` reads **"DNS only"**; `dig +noall +answer surveillancegraph.org A @<assigned>.ns.cloudflare.com` → `136.81.80.102` (answered by Cloudflare before the switch) |
| 4 | **TTL step-down:** in the Cloudflare zone the new records default to Auto TTL (≈300 s) — nothing to do there. At **Squarespace**, where the zone still serves, lower TTL on the `A` records (and any other records) to 300 s so caches clear fast through the change and a rollback propagates quickly. | `dig +noall +answer surveillancegraph.org A` → TTL field ≤ `300` (was `14400`) once the Squarespace edit serves |

## DNSSEC — the DS record at the registrar

The zone is a signed delegation today: the .org parent publishes
`DS 17039 8 2 3F5E85B0…` and the zone's `A` answer carries an RRSIG
(`zone_inventory_2026-10-02.md` § DNSKEY). A nameserver switch **with the old
DS left in place and Cloudflare unsigned breaks every validating resolver**
(SERVFAIL — worse than an outage, it looks like a lie to resolvers). Handle
the DS deliberately:

**Recommended — double-DS rollover (no unsigned window):**

| # | step | verify |
|---|---|---|
| 5 | In the Cloudflare zone: DNS → Settings → **enable DNSSEC**; copy the DS record Cloudflare issues (algorithm 13, its own key tag — *not* 17039). | dashboard shows DNSSEC on + a DS to publish; `dig +noall +answer surveillancegraph.org DNSKEY @<assigned>.ns.cloudflare.com` returns Cloudflare's keys |
| 6 | At **Squarespace registrar** (the DNSSEC/DS management panel): **add Cloudflare's DS alongside** the existing `17039` DS — two DS records at the parent is the correct rollover state; each side of the NS switch validates. | `dig +noall +answer surveillancegraph.org DS` → **two** DS answers (17039 + Cloudflare's key tag) |
| 7 | *(after the switch, below)* When the Cloudflare NS are live and validating, **remove the old `17039` DS** at the registrar. | `dig +noall +answer surveillancegraph.org DS` → only Cloudflare's DS remains; `dig +dnssec surveillancegraph.org A` answer carries the `ad` flag |

**Fallback — brief unsigned window** (if step 6's panel will not take a
second DS): at T‑24 h remove the `17039` DS at the registrar and confirm the
parent dropped it (`dig DS` → empty) *before* switching NS; the zone serves
unsigned until Cloudflare's DS is added in step 7. Never switch while the
`17039` DS is published and Cloudflare unsigned — that is the SERVFAIL case.

## The switch — T‑0

| # | step | verify |
|---|---|---|
| 8 | At the registrar, change the domain's nameservers `nsc1–nsc4.squarespacedns.com` → the two Cloudflare-assigned nameservers. Save. | `dig +noall +answer surveillancegraph.org NS` → the Cloudflare pair once the parent picks it up (parent NS TTL up to ~48 h; resolvers converge faster) |
| 9 | Confirm the new zone actually serves the site records: | `dig +noall +answer surveillancegraph.org A @<assigned>.ns.cloudflare.com` → `136.81.80.102`; same for `www` |

## Post-switch checklist

| # | step | verify |
|---|---|---|
| 10 | Apex resolves through the public path: | `dig +noall +answer surveillancegraph.org A` → `136.81.80.102` (a Cloudflare anycast range here means a record was proxied — fix immediately, see grey-cloud rule) |
| 11 | `www` resolves and redirects: | `curl -sSI https://www.surveillancegraph.org/` → `301` → `https://surveillancegraph.org/` |
| 12 | Site serves on the canonical origin with valid TLS: | `curl -sSI https://surveillancegraph.org/` → `200`; `openssl s_client -connect surveillancegraph.org:443 -servername surveillancegraph.org </dev/null \| openssl x509 -noout -dates -ext subjectAltName` → SAN apex+www, `notAfter` unchanged |
| 13 | DNSSEC validates through the new zone: | `dig +dnssec surveillancegraph.org A` → RRSIG present **and** `ad` flag set; `dig +noall +answer surveillancegraph.org DS` → Cloudflare's DS only (step 7 done) |
| 14 | Grey-cloud check (the cert rule, forever): | `dig +noall +answer surveillancegraph.org A` answers `136.81.80.102`, never a `104.*`/`172.*`/`188.*` Cloudflare anycast address |
| 15 | HTTP→HTTPS redirect still works: | `curl -sSI http://surveillancegraph.org/` → `301` → `https://surveillancegraph.org/` |

## Certificate renewal

`sig-web-cert` (Google managed, SAN `{surveillancegraph.org,
www.surveillancegraph.org}`, expires **2026-12-22**) renews by the LB proving
it serves the domain — which requires public DNS to answer the LB IP. Grey
cloud on `@`/`www` keeps that true. There is **no CAA record** today; if one
is ever added it must allow `pki.goog` (Google Trust Services is the issuer,
`WR3`) or renewal fails. Renewal-window read ≈ 2026-11-22 is P35.67's second
leg; the P34.4 TLS-expiry alert fires at 21 days (≈ 2026-12-01) regardless.

## Mail (MX/SPF)

No `MX` exists today and apex `TXT` is `"v=spf1 -all"` — the domain sends and
receives no mail **by design** right now. After the switch the same queries
must show the same answers: `dig +noall +answer surveillancegraph.org MX` →
empty; `dig … TXT` → `v=spf1 -all`. **OP-10 (the `contact@` alias) runs right
after this change** — whatever mailbox provider the operator picks will hand
them new `MX`/`TXT` (and possibly `DKIM`/`DMARC`) records; those are added to
the **Cloudflare** zone (Squarespace DNS no longer serves), and SPF moves off
`-all` only as far as the provider's include requires.

## R2 subdomain (P35.5)

The zero-egress distribution host (P35.5, after OP-09) lives on a subdomain —
recommended name `files.surveillancegraph.org` (P35.5 may confirm another).
Attach it as an R2 **custom domain** from the Cloudflare dashboard; its
record may be Cloudflare-proxied — the grey-cloud rule binds **only** the
hostnames on the Google managed cert (`@`, `www`). Add its line to the
inventory's carry table when it exists.

## Rollback

The entire change is one registrar edit away from revert:

| # | step | verify |
|---|---|---|
| R1 | At the registrar, set nameservers back to `nsc1`–`nsc4.squarespacedns.com`. (Squarespace DNS keeps serving the zone — it was never deleted.) | `dig +noall +answer surveillancegraph.org NS` → the squarespacedns set |
| R2 | If the DS was changed: restore `DS 17039 8 2 3F5E85B0E5893AD0906C5167D150A793F32ED37A2D4B4F6AC780426CA062B6D6` at the registrar (re-add alongside or instead of Cloudflare's). | `dig +noall +answer surveillancegraph.org DS` → `17039` present again; `dig +dnssec surveillancegraph.org A` → `ad` flag returns |
| R3 | Confirm the site is back on the old path: | `dig A` → `136.81.80.102`; `curl -sSI https://surveillancegraph.org/` → `200`; www → `301` apex |

If TTLs were stepped down at T‑48 h, rollback visibility converges within
minutes, not days.

## Hand-offs

- **P35.67 — post-DNS cut-over probe** (row 263, after OP-09): TLS validity,
  managed-cert renewal status (`gcloud compute ssl-certificates describe
  sig-web-cert --global --format='value(managed.status)'` → `ACTIVE`),
  every public route, mail posture; second leg ≈ 2026-11-22 in the cert
  renewal window. This runbook's post-switch checklist is its read pattern.
- **P34.5 — spend ledger:** Cloudflare plan/R2/registrar figures sit outside
  the GCP budget alert — they are the `operator-reported` non-GCP lines of
  `docs/build/reports/spend/` (`D-P34.5-3`, `SPEND_LEDGER.md`). Record the
  Cloudflare plan tier chosen here (expected: free) and the registrar renewal
  ($, expires 2027-09-22 per WHOIS) at the next ledger check-in.
- **OP-10 — `contact@` alias:** runs right after OP-09 (C-8 alias-first);
  its records go into the Cloudflare zone, see § Mail.
