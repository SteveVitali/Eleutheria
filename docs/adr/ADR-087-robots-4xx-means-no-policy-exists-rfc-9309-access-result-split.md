# ADR-087 — A 4xx robots.txt response means no policy exists (RFC 9309 §2.3.1.4 access-result split)

- **Status:** Accepted
- **Phase / ticket:** Phase 26 / P26.3 (`docs/tickets/P26.3__ungate-and-multitenant-expansion.md`)
- **Date:** 2026-09-17
- **Related:** SIG-INGEST-012 (amended — this is the recorded amendment, not a bypass),
  SIG-INGEST-013 (challenges still never defeated), §21.5, §26 Rule 2,
  `policy/crawler.robots_access_permits`, `connectors/net.py`, RFC 9309 §2.3.1.4,
  P26.2 (the CivicClerk refusal this corrects), D-SOURCES.2-3.

## Context

SIG-INGEST-012 as originally worded — "where `robots.txt` cannot be retrieved,
crawl permission MUST be treated as **not granted**" — was implemented by
collapsing every non-2xx robots outcome into one bucket: `RobotsResult` carried
only `text: str | None`, and `None` (whether a connection failure *or* an HTTP
404) refused the run.

RFC 9309 §2.3.1.4 ("Access Results") draws a sharper split that the original
reading conflated:

- **2xx** — a policy was retrieved; its parsed verdict governs.
- **4xx (other than 429)** — the server answered "no such resource": *no policy
  exists*, and access is unrestricted. This is not a refusal and not an
  unavailability — it is the affirmative absence of a policy.
- **429** — rate limiting; treated as *unavailable*, not "no policy".
- **5xx, connection failures, timeouts, redirect-chain exhaustion** — the file
  is *unavailable*: the crawler assumes complete disallow (the original
  SIG-INGEST-012 posture, retained).

The distinction is live, not academic: the CivicClerk tenant API surface
(`{tenant}.api.civicclerk.com`) answers `/robots.txt` with **HTTP 404** while
serving the documented public `/v1/Events` index — under the conflated reading,
every CivicClerk tenant was refused as "unretrievable" (P26.2 run record
`docs/build/reports/live_runs/2026-09-17_civicclerk.json`). Thirty-plus verified
tenants sat behind a wording error, not behind a real policy.

A hard `Disallow: /` retrieved over 2xx — e.g. every probed PrimeGov tenant
(`lacity.primegov.com` et al., 2026-09-17) — is untouched by this amendment: it
remains a parsed refusal, honoured.

## Decision

1. **`RobotsResult` carries the access signal.** `text` holds the policy body
   only on a 2xx; `status` holds the HTTP status the server returned (`None` on
   a connection-level failure). The transport (`HttpxTransport.robots`)
   preserves the status; an error body is never parsed as a policy.
2. **`policy.crawler.robots_access_permits(retrieved, status)` is the split.**
   `retrieved` → a policy exists (its verdict governs via `robots_permits`);
   `status` 4xx except 429 → "no policy exists" → permitted; `status` `None`,
   5xx, 429, or a residual 1xx/3xx → unavailable → refused.
3. **`PoliteFetcher` records the per-host outcome.** `fetcher.robots_outcomes`
   maps each host to `{robots_url, status, outcome}` where outcome is
   `retrieved` / `no_policy_4xx` / `unretrievable`; the live runner writes it
   into the fetch record's `robots_decisions` so every per-host robots verdict
   is auditable (claims / refused / unretrievable are all recorded).
4. **SIG-INGEST-012's spec text is amended** (§21.5 and §26 Rule 2 source) to
   name the split: unavailable → refuse; 4xx → no policy → unrestricted.
5. **No protection is lost.** A host whose robots 403 is itself a managed
   challenge (F2.1's Flock portals) still surfaces the challenge on the data
   path — `ChallengeEncountered` is recorded as `access_restricted`
   (SIG-INGEST-013), never defeated. Robots was never the challenge gate.

## Consequences

- CivicClerk tenants answering robots-404 become fetchable through the shared
  politeness layer — the central P26.3 beneficiary — while PrimeGov's real
  `Disallow: /` and every connection-failure/5xx/429 posture remain refusals.
- Every fetch record now carries the per-host robots outcome, so "which host
  refused and why" is data, not inference.
- The amendment narrows *retrieval-failure semantics* only; it does not touch
  the ingestion gate, rights review, the API allow-list, or challenge posture.

## Alternatives considered

- **Treat 4xx as unavailable (status quo).** Rejected — it contradicts RFC 9309
  §2.3.1.4 and silently refused every robots-404 tenant.
- **Permit only 404.** Rejected — the RFC's carve-out is the 4xx class (minus
  429); enumerating codes invites drift (410, 403, 451 are all client errors).
- **Use the ADR-083 API allow-list for CivicClerk instead.** Not chosen as the
  fix: the allow-list names documented API endpoints under ToS review; the 404
  was a *misreading of the RFC*, and repairing the reading is the honest fix.
  The allow-list remains available for hosts that genuinely publish robots
  policies that disallow (PrimeGov), where an API-mode basis must still be
  reviewed.

## Revisit trigger

RFC 9309 is revised or superseded; a tenant host answers 4xx on robots.txt but
its operators publish a policy elsewhere that clearly binds (then honour it);
or a 4xx-permitted fetch surfaces an access control on the data path that the
recorded outcome would have masked (review whether the challenge/refusal was
correctly recorded).
