# Rights-review packet — `camreg_winnipeg_mb` (Winnipeg traffic-signal camera inventory)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_winnipeg_mb`
- **Homepage:** https://data.winnipeg.ca/d/42pk-2u2c
- **Terms URL(s) fetched:** https://api.us.socrata.com/api/catalog/v1?domains=data.winnipeg.ca&ids=42pk-2u2c — retrieved 2026-09-18 (Socrata catalog metadata, owner City of Winnipeg).
- **robots.txt:** honor — `data.winnipeg.ca/robots.txt` answers 200; `/resource/*` is not disallowed. API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The dataset's Socrata metadata declares licence **"Open Government Licence -
> Canada"** (OGL-Canada 2.0) on the catalog record (dataset `42pk-2u2c`
> 'Traffic Signal Inventory - Cameras Detail'). OGL-Canada 2.0 grants a
> worldwide, royalty-free, perpetual, non-exclusive licence to use the
> information for any lawful purpose, with an attribution condition.

## SPDX candidate

`OGL-Canada-2.0` — added to `policy/data/licenses.toml` this run (self-relicensable only pending counsel's CC-BY compatibility mapping).

## redistributable analysis

OGL-Canada-2.0 is an explicit redistributable licence with attribution. → `redistributable = true`.

## derivative_permitted analysis

OGL-Canada-2.0 permits derivatives ("copy, modify, publish, translate, adapt, distribute or otherwise use"). → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `OGL-Canada-2.0` is self-relicensable only → dedicated `ogc_canada2` compartment (never merged into `sig_graph`).

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `OGL-Canada-2.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Open Government Licence declared by the publisher.**
