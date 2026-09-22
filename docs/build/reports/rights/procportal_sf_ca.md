# Rights-review packet — `procportal_sf_ca` (City and County of San Francisco — Socrata 'Supplier Contracts')

> P26.10 (SOURCES.9) review 2026-09-18. Facts are separated from judgement; this
> packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `procportal_sf_ca`
- **Homepage:** https://data.sf.gov/d/cqi5-hm2d
- **Terms URL(s) fetched:** https://data.sf.gov/api/views/cqi5-hm2d — retrieved 2026-09-18
- **robots.txt:** honor — `User-agent: *` / `Crawl-delay: 1`; only `/browse?*`
  faceted-search paths are disallowed — the documented `/resource/*.json` rows
  API is allowed. API MODE under the recorded `api_allowlist.toml` entry.
  Canonical host `data.sf.gov` (the legacy `data.sfgov.org` redirects —
  recorded 2026-09-18).

## Terms (verbatim)

Dataset metadata (`/api/views/cqi5-hm2d`, retrieved 2026-09-18):

> `name`: "Supplier Contracts" — `license.name`: **"Open Data Commons Public
> Domain Dedication and License"** (`licenseId`: `PDDL`)

An explicit per-dataset public-domain dedication (ODC PDDL) recorded by the
publisher.

## SPDX candidate

`CC0-1.0` — the ODC Public Domain Dedication and License is a public-domain
dedication; it maps onto the registry's public-domain expression (the PDDL's
own text dedicates the database to the public domain).

## redistributable analysis

Public-domain dedication asserts no redistribution bar. → `redistributable = true`.

## derivative_permitted analysis

Public-domain dedication asserts no derivative condition. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication. (PDDL is an Open Data Commons instrument
but a *dedication*, not a share-alike licence — no share-alike compartment.)

## Custody posture recommendation

LINK — municipal procurement records (the Controller's contract register). One
bounded SoQL slice per run, `?limit=500` ordered by `term_start_date DESC`.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO** — explicit public-domain dedication recorded verbatim; resolved under
GL-GATE-06 (clear-licence flip, same basis as the P26.7/P26.9 open-data rows).
