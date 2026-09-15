# ADR-083 — Crawler conduct: documented API access is not crawling (an auditable, allow-listed carve-out to strict robots-honouring)

- **Status:** Accepted
- **Phase / ticket:** operator determination (2026-09-15), during the P24.1 live deploy follow-on; implemented by P25.1
- **Date:** 2026-09-15
- **Related:** SIG-INGEST-037 / §26 (crawler conduct — rate limits, robots, no circumvention, RISK-P0-06), ADR-082 (the Overpass robots finding that forced this decision), `connectors.net.PoliteFetcher`, `policy.crawler`, HG-02 (counsel — see Consequences), the defining standard.

## Context

SIG binds itself to honour `robots.txt` with no circumvention (SIG-INGEST-037). A real `osm_overpass` live fetch (ADR-082) was refused because `overpass-api.de`'s `robots.txt` disallows `/api/`. That rule is aimed at **web crawlers** (spiders following links); it also blocks SIG from using a **documented public API** the way the API's own terms of service intend — rate-limited, single documented endpoint, no link-following. Every API-backed source (Overpass, data.gov, MuckRock, USAspending, CivicClerk) hits the same wall. Strict robots-everywhere would block legitimate, ToS-permitted API use across the whole program.

## Decision (operator determination, 2026-09-15)

Adopt an **auditable carve-out**: `robots.txt` governs **crawling**; it does **not** govern **documented API access** to a **named, allow-listed host** used under that API's ToS with SIG's rate-limiting.

- SIG keeps two conduct modes: **CRAWL** (default) — honour `robots.txt` strictly, no circumvention, unchanged; **API** — permitted only for a host on an explicit allow-list (`policy.crawler` / a `data/api_allowlist.toml`), each entry naming the host, the documented endpoint, the ToS basis, and the rate limit. A host not on the allow-list is treated as CRAWL (robots binds).
- This is **not** a `robots.txt` bypass: it is a per-host, ToS-grounded, recorded declaration that the access is API use, not crawling. `PoliteFetcher` consults the allow-list; rate-limiting/backoff/no-circumvention still apply; the allow-list decision is stamped into the fetch record (auditable).
- The allow-list is **narrow and reviewed**: a new host is a reviewed data change with its ToS basis, never a blanket wildcard.

## Consequences

- Unblocks live fetch for the allow-listed API sources (implemented in P25.1: `policy.crawler` allow-list + `PoliteFetcher` wiring + a test that a non-allow-listed host still refuses). The first entries: `overpass-api.de` (OSM, ODbL), `api.data.gov`/`catalog.data.gov` (data.gov), `www.muckrock.com` (records), `api.usaspending.gov` (procurement), the CivicClerk tenant host (agenda) — each with its ToS basis recorded.
- **Firm decision, not pending-counsel** (operator's call). It rests on the standard industry distinction (robots = crawling; APIs = ToS). Counsel (HG-02) should still confirm it before *real public exposure*, and the allow-list carries a `counsel_reviewed: no` flag until then; nothing about the carve-out loosens Part VIII or the rights/licence gates.
- CRAWL-mode sources are unaffected — strict robots-honouring remains the default and the only behaviour for anything off the allow-list.

## Revisit trigger

Revisit if: counsel (HG-02) reviews the carve-out (flip `counsel_reviewed`); **or** a host on the allow-list changes its ToS to forbid programmatic access (remove it); **or** the distinction proves insufficient for an authenticated-API source (extend the allow-list schema with the auth model, which stays env-only per HG-09).
