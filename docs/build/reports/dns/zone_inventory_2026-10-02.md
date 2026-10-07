<!--
  docs/build/reports/dns/zone_inventory_2026-10-02.md — P34.50 (row 208)
  dated inventory of the PUBLIC `surveillancegraph.org` zone, read-only.
  Every value below is the verbatim answer of the named query at the named
  `date -u` (the answering resolver was the system resolver, DNSSEC-validating
  — `ad` flag set on positive answers). No DNS, registrar, Cloudflare or GCP
  change was made to produce it. Feeds `../DNS_CUTOVER_RUNBOOK.md` (OP-09).
-->
# Zone inventory — `surveillancegraph.org` — 2026-10-02

Read-only public DNS + HTTPS + WHOIS inventory taken before OP-09 (the
operator's move of the zone to Cloudflare DNS, by GATE-G4). Everything on
this page was answered by public resolvers/servers — nothing required or
used a credential. This is a **dated snapshot**: re-run the queries at
cut-over time; the runbook cites this file as `zone_inventory_<date>.md`.

## Summary

| fact | value | source (query below) |
|---|---|---|
| registrar | Squarespace Domains LLC | WHOIS |
| authoritative NS | `nsc1`–`nsc4.squarespacedns.com` (Squarespace DNS; SOA hostmaster `cloud-dns-hostmaster.google.com`) | apex NS + SOA |
| DNSSEC | **signed delegation** — DS `17039 8 2 …` at the parent; DNSKEY KSK+ZSK alg 8; apex A carries an RRSIG | DS, DNSKEY, `+dnssec`, WHOIS |
| apex / www | both `A 136.81.80.102` TTL 14400 — the Google HTTPS LB static IP (`ops/gcp/domain-mapping.sh`, ADR-098) | A queries |
| IPv6 | none (no AAAA on apex or www) | AAAA queries |
| mail | no MX anywhere probed; apex `TXT "v=spf1 -all"` (deny-all SPF) | MX/TXT queries |
| CAA | none | CAA queries |
| subdomains | `api`, `mail`, `contact`, `status`, `docs`, `app` → NXDOMAIN; zone transfer refused | AXFR + probes |
| TLS cert (live) | `CN=surveillancegraph.org`, issuer Google Trust Services `WR3`, SAN `{apex, www}`, `notAfter 2026-12-22T18:47:21Z` | `openssl s_client` |
| HTTPS behaviour | apex `200`; `www` `301`→apex; `:80` `301`→https | `curl -sI` |

## Registrar record (WHOIS, read-only)

Query: `whois surveillancegraph.org` — run at `date -u` 2026-10-02T11:46Z.

```
Updated Date: 2026-09-27T17:04:15Z
Registry Expiry Date: 2027-09-22T17:03:25Z
Registrar: Squarespace Domains LLC
Name Server: nsc1.squarespacedns.com   (×4: nsc1…nsc4.squarespacedns.com)
DNSSEC: signedDelegation
```

## Apex — `surveillancegraph.org`

All queries run 2026-10-02T11:44:17–11:44:18Z as
`dig +noall +answer +comments <name> <type>` (system resolver).

### A

Query: `dig +noall +answer +comments surveillancegraph.org A` — `date -u` 2026-10-02T11:44:17Z.

```
;; status: NOERROR, ANSWER: 1
surveillancegraph.org.	14400	IN	A	136.81.80.102
```

### AAAA

Query: `dig +noall +answer +comments surveillancegraph.org AAAA` — `date -u` 2026-10-02T11:44:17Z.

```
;; status: NOERROR, ANSWER: 0      (no AAAA — IPv4 only)
```

### CNAME

Query: `dig +noall +answer +comments surveillancegraph.org CNAME` — `date -u` 2026-10-02T11:44:17Z.

```
;; status: NOERROR, ANSWER: 0      (none — apex cannot be a CNAME)
```

### MX

Query: `dig +noall +answer +comments surveillancegraph.org MX` — `date -u` 2026-10-02T11:44:17Z.

```
;; status: NOERROR, ANSWER: 0      (no mail exchangers)
```

### TXT

Query: `dig +noall +answer +comments surveillancegraph.org TXT` — `date -u` 2026-10-02T11:44:17Z.

```
;; status: NOERROR, ANSWER: 1
surveillancegraph.org.	14400	IN	TXT	"v=spf1 -all"
```

### CAA

Query: `dig +noall +answer +comments surveillancegraph.org CAA` — `date -u` 2026-10-02T11:44:17Z.

```
;; status: NOERROR, ANSWER: 0      (no CAA — any CA may issue; see runbook § CAA note)
```

### DS

Query: `dig +noall +answer +comments surveillancegraph.org DS` — `date -u` 2026-10-02T11:44:18Z.

```
;; status: NOERROR, ANSWER: 1
surveillancegraph.org.	3600	IN	DS	17039 8 2 3F5E85B0E5893AD0906C5167D150A793F32ED37A2D4B4F6AC780426CA062B6D6
```

The DS lives **at the parent (.org)** — published through the registrar
(Squarespace). Key tag `17039`, algorithm 8 (RSA/SHA-256), digest type 2
(SHA-256). The zone is signed *now*; whoever serves the zone next must
either keep a valid DS↔DNSKEY↔RRSIG chain or have the DS removed first —
see the runbook's DNSSEC section.

### NS

Query: `dig +noall +answer +comments surveillancegraph.org NS` — `date -u` 2026-10-02T11:44:18Z.

```
;; status: NOERROR, ANSWER: 4
surveillancegraph.org.	21600	IN	NS	nsc1.squarespacedns.com.
surveillancegraph.org.	21600	IN	NS	nsc2.squarespacedns.com.
surveillancegraph.org.	21600	IN	NS	nsc3.squarespacedns.com.
surveillancegraph.org.	21600	IN	NS	nsc4.squarespacedns.com.
```

### SOA

Query: `dig +noall +answer +comments surveillancegraph.org SOA` — `date -u` 2026-10-02T11:44:18Z.

```
;; status: NOERROR, ANSWER: 1
surveillancegraph.org.	21600	IN	SOA	nsc1.squarespacedns.com. cloud-dns-hostmaster.google.com. 1 21600 3600 259200 300
```

(Serial `1`, refresh 21600, retry 3600, expire 259200, negative TTL 300.)

### DNSKEY + signature posture

Query: `dig +noall +answer +comments surveillancegraph.org DNSKEY` — `date -u` 2026-10-02T11:45Z (via the system resolver; the same query direct to `@nsc1.squarespacedns.com` timed out — TCP/53 to it is filtered from this network).

```
;; status: NOERROR, ANSWER: 2
surveillancegraph.org.	226	IN	DNSKEY	256 3 8 AwEAAfEttR5sIUbXB5TnPa/Qla94LAWa9YWyoDgHqAs4oZKAlcSd+Qby…   (ZSK, flags 256)
surveillancegraph.org.	226	IN	DNSKEY	257 3 8 AwEAAcd5CIUNszf0xr/GAO7SZkyvNzxomCjski9rm4j5JenojMZvSA2P…  (KSK, flags 257)
```

Query: `dig +dnssec +noall +answer surveillancegraph.org A` — `date -u` 2026-10-02T11:45Z.

```
surveillancegraph.org.	14333	IN	A	136.81.80.102
surveillancegraph.org.	14333	IN	RRSIG	A 8 2 14400 20261022215757 20260930215757 50430 surveillancegraph.org. 7+WrxeRZ2tf4D7l1xFuilIY7MnkjOoWeQQJwZZsQOq9BOc8/SmYSOjUT…
```

RRSIG validity 2026-09-30T21:57:57Z → 2026-10-22T21:57:57Z, signer
`surveillancegraph.org`, key tag 50430.

## `www` — `www.surveillancegraph.org`

All queries run 2026-10-02T11:44:18Z, same `dig +noall +answer +comments`
form.

| type | status | answer |
|---|---|---|
| A | NOERROR, 1 | `www.surveillancegraph.org. 14400 IN A 136.81.80.102` |
| AAAA | NOERROR, 0 | none |
| CNAME | NOERROR, 0 | none (www is an A record to the LB IP; the LB 301-redirects www→apex) |
| MX | NOERROR, 0 | none |
| TXT | NOERROR, 0 | none |
| CAA | NOERROR, 0 | none |

## Subdomains

Zone transfer refused — `dig axfr surveillancegraph.org
@nsc1.squarespacedns.com` at `date -u` 2026-10-02T11:44:39Z:

```
;; Connection to 216.239.32.108#53 for surveillancegraph.org failed: timed out.
;; connection timed out; no servers could be reached
```

Without AXFR, subdomains were probed by name —
`dig +noall +answer +comments <sub>.surveillancegraph.org A` at
`date -u` 2026-10-02T11:45:52Z:

| name | result |
|---|---|
| api, mail, contact, status, docs, app | **NXDOMAIN** (all six) |

No other subdomain is known to the project today (the API has no custom
domain — G1:82). Any record the operator sees inside the Squarespace DNS
console that is not on this page still has to be carried into the new zone
— the console view, not this inventory, is authoritative for names that do
not answer publicly (e.g. a wildcard or a private record).

## Load-balancer IP + managed certificate (read-only)

- LB IPv4 (the apex + www A-record value): **136.81.80.102**, matching
  `SIG_LB_IP = sig-web-ip` in `ops/gcp/config.sh` / `domain-mapping.sh`
  (ADR-098). The gcloud reads of the address/`sig-web-cert` objects are the
  operator's ADC path (`domain-mapping.sh --records`); this run used only
  the public paths below.
- Certificate as served on `surveillancegraph.org:443` —
  `openssl s_client -connect surveillancegraph.org:443 -servername
  surveillancegraph.org </dev/null | openssl x509 -noout -subject -issuer
  -dates -ext subjectAltName` at `date -u` 2026-10-02T11:45:53Z:

```
subject=CN=surveillancegraph.org
issuer=C=US, O=Google Trust Services, CN=WR3
notBefore=Sep 23 17:54:08 2026 GMT
notAfter=Dec 22 18:47:21 2026 GMT
X509v3 Subject Alternative Name:
    DNS:surveillancegraph.org, DNS:www.surveillancegraph.org
```

  The Google-managed cert (`sig-web-cert`, apex + www) expires
  **2026-12-22** — the FEA-08 renewal risk the runbook's grey-cloud rule
  protects.

## HTTPS behaviour (read-only)

`date -u` 2026-10-02T11:45:59Z:

```
curl -sSI https://surveillancegraph.org/        → HTTP/2 200 (text/html)
curl -sSI https://www.surveillancegraph.org/    → 301 → https://surveillancegraph.org/
curl -sSI http://surveillancegraph.org/         → 301 → https://surveillancegraph.org/
```

## What the cut-over must reproduce (frozen checklist for the runbook)

| name | type | value to carry | proxy state on Cloudflare |
|---|---|---|---|
| `@` | A | `136.81.80.102` | **DNS only (grey cloud) — never proxied** |
| `www` | A | `136.81.80.102` | **DNS only (grey cloud) — never proxied** |
| `@` | TXT | `v=spf1 -all` | n/a (TXT is never proxied) |
| `<r2-subdomain>` | (P35.5 sets) | R2 custom domain, e.g. `files.` | proxied is fine — it is not the Google LB |
| apex | DS @ registrar | `17039 8 2 …` today | handled per runbook § DNSSEC |
