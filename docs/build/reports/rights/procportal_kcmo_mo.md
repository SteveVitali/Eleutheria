# Rights-review packet — `procportal_kcmo_mo` (Kansas City, MO — Socrata 'List of KCMO City Contracts')

> P26.10 (SOURCES.9) review 2026-09-18. Facts are separated from judgement; this
> packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `procportal_kcmo_mo`
- **Homepage:** https://data.kcmo.org/d/c46m-hv6s
- **Terms URL(s) fetched:** https://data.kcmo.org/api/views/c46m-hv6s — retrieved 2026-09-18
- **robots.txt:** honor — `User-agent: *` / `Crawl-delay: 1`; only `/browse?*`
  faceted-search paths are disallowed — the documented `/resource/*.json` rows
  API is allowed. API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

Dataset metadata (`/api/views/c46m-hv6s`, retrieved 2026-09-18):

> `name`: "List of KCMO City Contracts" — `license.name`: **"Creative Commons
> 1.0 Universal (Public Domain Dedication)"** (`licenseId`: `CC0_10`) —
> `attribution`: "City of Kansas City General Services - Procurement"

An explicit per-dataset CC0 public-domain dedication recorded by the publisher.

## SPDX candidate

`CC0-1.0` — the recorded dedication IS CC0 verbatim.

## redistributable analysis

CC0 asserts no redistribution bar. → `redistributable = true`.

## derivative_permitted analysis

CC0 asserts no derivative condition. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK — municipal procurement records. One bounded SoQL slice per run,
`?limit=500` ordered by `contract_date DESC`. The dataset's `description` field
carries contract-type labels rather than prose — expect honest zero-match
windows most runs (recorded, never padded).

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO** — explicit CC0 dedication recorded verbatim; resolved under GL-GATE-06
(clear-licence flip, same basis as the P26.7/P26.9 open-data rows).
