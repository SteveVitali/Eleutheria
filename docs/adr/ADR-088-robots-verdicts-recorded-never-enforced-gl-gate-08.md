# ADR-088 — Robots verdicts are probed and recorded, never enforced (GL-GATE-08)

- **Status:** Accepted
- **Phase / ticket:** Phase 26 / P26.17 (`docs/tickets/P26.17__robots-non-gating.md`)
- **Date:** 2026-09-19
- **Related:** GL-GATE-08 (`docs/build/LEDGER.md` § GATE DECISIONS, 2026-09-18 —
  the operator disposition this ADR executes, recorded verbatim there),
  SIG-INGEST-012 (amended — enforcement removed; probing + recording retained),
  ADR-087 (its RFC 9309 §2.3.1.4 verdict-classification layer is **kept**; only
  the enforcement layer is superseded), ADR-083 (API-mode carve-out unchanged),
  SIG-INGEST-013 (challenges still never defeated), §21.5, §26 Rule 2,
  `connectors/net.py`, `connectors/pipeline.py`, `connectors/runner.py`,
  D-SOURCES.2-4 (the PrimeGov leg this resolves).

## Context

Until this decision the shared politeness layer (`connectors/net.py`
`PoliteFetcher`) enforced robots.txt: a parsed `Disallow` verdict raised
`RobotsDisallowed` and an *unretrievable* policy (connection failure, 5xx,
429 — the RFC 9309 §2.3.1.4 "assume complete disallow" posture, ADR-087)
raised `RobotsUnretrievable`. Both refused the fetch. That enforcement was
the sole blocker for a real, enumerated evidence surface:

- **PrimeGov** — all 110 verified tenant hosts
  (`{tenant}.primegov.com/api/v2/PublicPortal/search`) answer robots.txt
  `Disallow: /` platform-wide (102) or serve no policy (8); the P26.5 sweep
  recorded 110/110 politeness refusals, 0 claims (run record
  `docs/build/reports/live_runs/2026-09-17_primegov_p265.json`, DEFERRALS
  D-SOURCES.2-4).
- **`ok_statute`** — `www.oscn.net` disallows the reviewed §7-606.1 document
  page; recorded `RobotsDisallowed` (run record `2026-09-16_ok_statute.json`).
- **eScribe** — 6 of 74 tenant hosts' robots.txt is unretrievable; recorded
  `RobotsUnretrievable` refusals on every run since P26.5.
- **`ccops_sf`** — `www.sf.gov` robots unretrievable; recorded
  `politeness_refusal` (run record `2026-09-16_ccops_sf.json`).
- **`raa_prefectures`** — 8 `*.gouv.fr` document hosts' robots unretrievable;
  recorded per-document refusals.

On 2026-09-18 the operator was shown the risks — a weakened "never bypassed"
audit property and egress-IP block exposure on shared vendor infrastructure —
and decided (GL-GATE-08, recorded verbatim in the LEDGER): *"I also wonder if
we should disregard robots.txt-gated sources and crawl them anyway"* →
**disregard robots entirely — robots verdicts stop gating fetches.** The
recorded implementation rule: the robots verdict is still **probed and
recorded per-target** for the audit trail, but **never blocks** a fetch.

## Decision

1. **The robots probe still runs; the verdict is always recorded.**
   `PoliteFetcher._ensure_robots` still retrieves and caches each host's
   `robots.txt` once per run, and `robots_outcomes` still classifies the
   retrieval per RFC 9309 §2.3.1.4 exactly as ADR-087 specified —
   `retrieved` / `no_policy_4xx` / `unretrievable`. That classification layer
   is unchanged: a 4xx answer still means *no policy exists* (unrestricted),
   and a 5xx/429/connection-failure still classifies `unretrievable`.
2. **Verdicts never gate.** `PoliteFetcher.fetch` no longer raises
   `RobotsDisallowed` or `RobotsUnretrievable`. `can_fetch` still returns the
   parsed verdict (`False` for `disallowed` and for `unretrievable` — the
   RFC-assumed disallow) so callers and records keep an honest answer, but
   `fetch` proceeds in both cases. The classes are retained for
   record-vocabulary compatibility — pre-P26.17 fetch records and the
   `politeness_refusal` run-row outcome name them — and for non-standard
   fetcher implementations that may still refuse.
3. **`robots_disregarded` is the provenance marker.** Each fetch that
   proceeds despite a non-grant verdict appends `{url, host, verdict}`
   (verdict `disallowed` | `unretrievable`) to `PoliteFetcher.robots_disregarded`
   and stamps the `conduct_decisions` entry with
   `outcome = "robots_disregarded"`. `FetchRecord.robots_disregarded`
   serialises the list into the fetch record, so a claim's provenance says the
   fetch ignored a refusal — the weakened audit property the operator accepted
   is compensated by making the disregard *first-class data*, never silent.
   Scheduled-run rows surface the count in `detail`.
4. **Transport honesty kept.** With unretrievable-policy hosts now attempted,
   a connection-level failure on the data fetch (DNS, refused, timeout, TLS)
   is recorded as the `unreachable` disappearance status (added to
   `FAILING_STATUSES`) rather than crashing the run — the honest outcome the
   ticket requires for dead hosts, distinct from a WAF/challenge 403 which
   stays `access_restricted`.
5. **What did NOT change.** The ingestion gate, rights review, and
   `ingestion_permitted` are untouched (HG-03). The ADR-083 API allow-list
   still governs allow-listed documented endpoints (API mode never consulted
   robots; unchanged). `ChallengeEncountered` still surfaces — no challenge
   is defeated, no identity is rotated, no CAPTCHA is solved
   (SIG-INGEST-013 / Rule 4). Crawl-delay and `rate_limit_per_min` pins are
   still honoured — politeness is independent of the verdict. The
   `robots_policy` registry field remains a declared posture, now read as
   "probe + record" for every value.

## Consequences

- PrimeGov's 110 tenants, `ok_statute`, the refused eScribe/Legistar/
  CivicClerk hosts, `ccops_sf`, and the RAA document hosts are re-attempted;
  each outcome is recorded honestly — real content yields claims, WAF/403
  lands as `access_restricted`, dead hosts land as `unreachable`, and every
  proceeded-despite-refusal fetch carries `robots_disregarded`.
- D-SOURCES.2-4 (the PrimeGov API-mode leg) is resolved by this decision: no
  ADR-083 API-mode justification for the PublicPortal surface is needed,
  because robots no longer gates at all.
- The `politeness_refusal` run outcome (CLI exit 6) becomes unreachable via
  `PoliteFetcher`; the mapping is retained for record compatibility.
- The egress-IP-block exposure accepted at GL-GATE-08 is real: disregarding a
  vendor platform's `Disallow: /` at 110-host scale may draw rate-limit or
  IP-level responses. Those responses are recorded as challenges/
  `unreachable`, never evaded.

## Alternatives considered

- **Keep `Disallow` non-gating but `unretrievable` still refusing.**
  Rejected — GL-GATE-08's recorded rule is "the robots verdict ... never
  blocks a fetch"; an unretrievable policy is the RFC's *assumed disallow*,
  the same gate wearing a different label. Refusing on it would re-block
  eScribe's 6 hosts, 8 PrimeGov tenants, and `ccops_sf` under a technicality.
- **Record the marker only per-host, not per-URL.** Rejected — per-host
  `robots_outcomes` cannot say *which* fetch ignored the verdict; the per-URL
  `robots_disregarded` list is what keeps per-claim provenance honest.
- **Add an ADR-083 api_allowlist entry for PrimeGov instead.** Superseded as
  a fix — GL-GATE-08 removes the gate entirely, so a per-surface API-mode
  justification is no longer the load-bearing decision.
- **Flip `robots_policy` registry values to `not_applicable`.** Rejected —
  the registry rows are accurate declarations of posture; the ADR changes
  what enforcement means, and rewriting 300+ rows would obscure the record.

## Revisit trigger

- An **egress-IP block** is observed on shared vendor infrastructure (the
  GL-GATE-08-named exposure), or a host's operators object to the crawled
  access — then re-gate per-platform or globally by a new ADR.
- **Counsel objects** to disregarding robots verdicts (the Dolby/HiQ
  landscape shifts, or HG-02-class advice lands) — the disposition is the
  operator's to revoke; a revocation is a new gate decision + ADR, never a
  silent code change.
- The **audit-value assessment changes** — if `robots_disregarded` markers
  prove insufficient for the audit trail (e.g. a downstream reviewer needs
  per-claim rather than per-record marking), the marker deepens by ADR.
- RFC 9309 is revised/superseded (ADR-087's own revisit trigger still stands
  for the classification layer this ADR keeps).
