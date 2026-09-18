# Rights-review packet — `camreg_act_au` (ACT traffic safety camera registries)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_act_au`
- **Homepage:** https://www.data.act.gov.au/d/426s-vdu4
- **Terms URL(s) fetched:** https://api.us.socrata.com/api/catalog/v1?domains=www.data.act.gov.au&ids=426s-vdu4 and `ids=5ezj-yjxz` — retrieved 2026-09-18 (Socrata catalog metadata, owner ACT Government).
- **robots.txt:** honor — `www.data.act.gov.au/robots.txt` answers 200; `/resource/*` is not disallowed. API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> Both datasets' Socrata metadata declare **"Creative Commons Attribution 4.0"**
> (CC-BY-4.0) on the catalog records — `426s-vdu4` 'Traffic speed camera
> locations' and `5ezj-yjxz` 'Mobile Distraction camera locations'.

## SPDX candidate

`CC-BY-4.0` (already registered in `policy/data/licenses.toml`).

## redistributable analysis

CC-BY-4.0 is an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

CC-BY-4.0 permits derivatives with attribution (recorded in the rights row). → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `CC-BY-4.0` is `sig_graph`-compatible (same expression) — no separate compartment needed.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC-BY-4.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Creative Commons licence declared by the publisher.**
