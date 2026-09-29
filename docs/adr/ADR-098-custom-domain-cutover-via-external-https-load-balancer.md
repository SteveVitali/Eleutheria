# ADR-098 — Custom-domain cut-over to surveillancegraph.org via an external HTTPS load balancer + serverless NEG

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.10 (`docs/tickets/P27.10__domain-cutover-surveillancegraph.md`) — the final P27 launch row; the custom-domain cut-over that makes `https://surveillancegraph.org` the canonical public origin.
- **Date:** 2026-09-23
- **Related:** **ADR-075** (the GCP IaC form — idempotent `gcloud` scripts, `--check` green without ADC), **ADR-081** (the executed Cloud SQL + Cloud Run realization, and the precedent for a conscious low-cost departure from SIG-STORE-003), **ADR-090/096** (the national public surface + published-compartment cut-over this domain fronts), **SIG-UI-035** (belief-pinned permalink/citation origin — resolves against this domain), **SIG-STORE-003** (zero/low-cost posture), **§15** (web shell / canonical origin), **§38/§42.3** (public compartment served surface), the publication gates **HG-01/HG-11/HG-02** (Go-public), **HG-09/HG-12** (secrets-in-env / operator ADC), `web/astro.config.mjs` (`site`), `ops/gcp/config.sh` + `ops/cadence.toml` (probe targets), `D-P27.8-1` (the hosted national deploy this does **not** block on), `D-P27.10-1` (the operator DNS + post-DNS verification this opens).

## Context

P27.6 fixed `web/astro.config.mjs` `site = "https://surveillancegraph.org"` so belief-pinned
permalinks and citations (SIG-UI-035) never churn; the DNS/TLS cut-over was deferred to P27.10. The
production public surface is the `sig-web` Cloud Run service
(`https://sig-web-873541617837.us-central1.run.app`, project `zeta-medley-508121-u7`, region
`us-central1`) plus the public GCS objects. The domain `surveillancegraph.org` is registered at
Squarespace (registrar + DNS); it is **public config, never a secret** (HG-09).

The operator's Go-public gate answer (HG-11, GATE DECISIONS 2026-09-23) was **"Apply domain mapping
now"** — create the GCP mapping under the operator-armed ADC, produce the *real* Squarespace DNS
records, and point the domain at `sig-web` immediately, explicitly accepting that the domain serves
the OKC demo until the national deploy (`D-P27.8-1`, gated on the OSM land) completes. Google-managed
TLS provisions only after the DNS records resolve, so valid-TLS + `probe-hosted` verification is a
RETURN PASS, not a fabricated green.

GCP offers two ways to put Google-managed TLS on a custom domain in front of a Cloud Run service:

1. **A Cloud Run domain mapping** — zero-cost, one resource, automatic managed TLS. But it requires
   the domain to be **verified for the account first** (`gcloud domains verify`), which is an
   interactive Google Search Console step needing the `siteverification` OAuth scope. Empirically
   confirmed on 2026-09-23 under the operator ADC: `gcloud beta run domain-mappings create --service
   sig-web --domain surveillancegraph.org` **errors** ("the provided domain does not appear to be
   verified"), creating no resource, and the Site Verification API returns `403
   ACCESS_TOKEN_SCOPE_INSUFFICIENT` for the cloud-platform ADC token. Verification cannot be
   completed non-interactively from this shell.
2. **An external HTTPS Application Load Balancer + a serverless NEG** — needs **no** domain
   verification. It reserves a global static IP (the real apex/`www` `A`-record value), wraps the
   Cloud Run service in a serverless NEG + backend service, and terminates a Google-managed
   multi-domain certificate. It costs ~$18/mo (one global forwarding rule + the static IP).

The gate's operative instruction was "apply **now**, with real values from real created resources."
Only path (2) is realizable now under the available ADC.

## Decision

1. **Front `sig-web` with an external HTTPS Application Load Balancer + a serverless NEG**, not a
   Cloud Run domain mapping. Rationale: it is the only path that can be **created now** under the
   operator-armed cloud-platform ADC (path (1) is hard-blocked on interactive Search Console
   verification the ADC scope cannot perform), and it yields a **real reserved static IP** as the
   concrete DNS-record value the operator adds at Squarespace — fulfilling the gate's "apply the
   mapping now, real values from real created resources."
2. **Land it as idempotent IaC** at `ops/gcp/domain-mapping.sh`, in the ADR-075 form: `--check` /
   `--dry-run` prints the full plan with no ADC and no network and exits 0 (the deterministic
   validation path, asserted by `tests/ops/test_gcp_iac.py`); `--apply` creates the resources for
   real under operator ADC, re-runnable (each create is existence-guarded); `--records` prints the
   exact Squarespace records from the realized static IP. Resource names + the domain live in
   `ops/gcp/config.sh` (`SIG_WEB_DOMAIN`, the LB resource names) — the domain a literal (public
   config), never a credential.
3. **`www` → apex, HTTP → HTTPS, both at the edge.** The HTTPS url map serves the apex from the
   backend and 301-redirects `www.surveillancegraph.org` to the apex canonical origin; a second url
   map 301-redirects all `:80` traffic to HTTPS. The managed certificate covers both apex and `www`.
   This keeps `https://surveillancegraph.org` the single canonical origin (SIG-UI-035), matching the
   already-fixed astro `site`.
4. **The exact Squarespace DNS records** the operator adds (HG-11 human step): apex `@` `A` → the LB
   static IP, and `www` `A` → the same IP. No verification TXT (the LB path needs none); the apex
   cannot be a CNAME, so both are `A` records. Recorded with realized values in
   `docs/build/PUBLICATION_CHECKLIST.md` and the RETURN PASS row.
5. **Probe/uptime targets watch the canonical origin.** `ops/cadence.toml`'s `sig-web-root` probe
   resolves `SIG_PROBE_WEB_URL` to the custom domain once TLS provisions; the `*.run.app` URL stays
   the documented fallback (no host literal baked in — HG-12).
6. **The `*.run.app` origin remains a documented fallback.** The Cloud Run service keeps its direct
   URL; the LB is additive and reversible.

## Consequences

- `surveillancegraph.org` (+ `www`→apex) serves the `sig-web` Cloud Run content with Google-managed
  TLS once the operator adds the two `A` records at Squarespace and the certificate provisions to
  ACTIVE (typically ≤ ~60 min after DNS resolves). Until then the certificate sits in
  `PROVISIONING`; this is the gate-deferred half (`D-P27.10-1`), a RETURN PASS, never a fabricated
  green.
- **Cost:** ~$18/mo (a global forwarding rule + the reserved static IP) on top of the ADR-081
  ~$9/mo Cloud SQL — a conscious low-cost departure from SIG-STORE-003's zero-cost posture,
  consistent with the ADR-081 precedent. The zero-cost Cloud Run domain mapping is the documented
  migration target once the domain is verified (see Revisit trigger).
- Deploy still only reads/serves; nothing here mutates the claim spine, and the published-vs-
  restricted compartment separation (ADR-096) is unchanged — the LB fronts exactly the bytes the
  cut-over already published.
- The operator explicitly accepts (HG-11) that the domain serves the current OKC demo until the
  national deploy (`D-P27.8-1`, gated on the OSM land) completes; the domain cut-over does **not**
  block on it.
- The LB is a superset of the Cloud Run domain mapping's capability (it can later carry Cloud
  Armor / Cloud CDN / multi-region), at the stated cost.

## Alternatives considered

- **Cloud Run domain mapping (zero-cost).** Preferred on cost (SIG-STORE-003) and simplicity, but
  **not realizable now**: it requires interactive Search Console domain verification the
  cloud-platform ADC cannot perform (empirically confirmed — the create errors and the Site
  Verification API is scope-blocked). Kept as the explicit zero-cost migration target once the
  operator verifies the domain (Revisit trigger).
- **Staging the IaC and deferring the whole apply** (the ADC-absent fallback in the gate answer).
  Rejected here because the ADC **is** present and the LB path can be genuinely applied now — the
  gate asked for real values from real created resources, which staging-only would not deliver.
- **A third-party TLS/CDN front (e.g. Cloudflare) proxying the run.app origin.** Rejected: it adds a
  hard third-party dependency on the public origin and moves TLS/DNS trust off the operator's own
  GCP + registrar, for no gain over the managed LB cert.
- **Serving plaintext `:80` directly.** Rejected: the LB 301-redirects all HTTP to HTTPS; the public
  surface is HTTPS-only.

## Revisit trigger

- **Cost pressure or a return to the zero-cost posture (SIG-STORE-003):** once the operator verifies
  `surveillancegraph.org` in Google Search Console (adds the verification TXT + confirms — a step the
  ADC scope cannot do), migrate to a **Cloud Run domain mapping** (zero-cost), swap the Squarespace
  `A` records for the mapping's apex `A`/`AAAA` + `www` `CNAME`, and delete the LB — recorded in a
  **new ADR** (SIG-ENG-003), never a silent swap.
- A **CDN / WAF / multi-region** need arises — enable Cloud CDN / Cloud Armor on the existing backend
  (config, within this ADR) rather than re-architecting.
- The Cloud Run service `sig-web` is renamed, moved region, or replaced by a GCS-bucket origin — the
  serverless NEG target changes; re-point it (config) and re-verify the cert.
- Google-managed Cloud Run domain mappings reach GA parity for apex + managed multi-domain certs +
  `www`→apex redirect in `us-central1` — reconsider the LB for a new deployment (new ADR).
- The domain must ever front **restricted** compartment bytes — a hard stop requiring a governance
  decision (Part VIII / §42.3), never a config change.
