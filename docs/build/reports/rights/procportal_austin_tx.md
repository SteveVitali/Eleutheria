# Rights-review packet — `procportal_austin_tx` (City of Austin — Socrata 'Contracts')

> P26.10 (SOURCES.9) review 2026-09-18. Facts are separated from judgement; this
> packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `procportal_austin_tx`
- **Homepage:** https://data.austintexas.gov/d/84ih-p28j
- **Terms URL(s) fetched:** https://data.austintexas.gov/api/views/84ih-p28j — retrieved 2026-09-18
- **robots.txt:** honor — `User-agent: *` / `Crawl-delay: 1`; only `/browse?*`
  faceted-search paths are disallowed — the documented `/resource/*.json` rows
  API is allowed. API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

Dataset metadata (`/api/views/84ih-p28j`, retrieved 2026-09-18):

> `name`: "Contracts" — `license.name`: **"Public Domain"** (`licenseId`:
> `PUBLIC_DOMAIN`) — `attribution`: "City of Austin, Texas - data.austintexas.gov"

An explicit per-dataset public-domain dedication recorded by the publisher.

## SPDX candidate

`CC0-1.0` — a public-domain dedication maps onto the registry's public-domain
expression (same basis as other PUBLIC_DOMAIN government datasets).

## redistributable analysis

Public-domain dedication asserts no redistribution bar. → `redistributable = true`.

## derivative_permitted analysis

Public-domain dedication asserts no derivative condition. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK — municipal procurement records (authorized-spending register since
inception). One bounded SoQL slice per run, `?limit=500` ordered by
`efbgn_dt DESC`.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO** — explicit public-domain dedication recorded verbatim; resolved under
GL-GATE-06 (clear-licence flip, same basis as the P26.7/P26.9 open-data rows).
