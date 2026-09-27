# Rights-review packet — `camreg_baltimore_md` (Baltimore CitiWatch camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_baltimore_md`
- **Homepage:** https://baltegis.baltimorecity.gov/mapping/rest/services/CityView/CitiWatchCamera/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/b676679350764f56a990c25a8ce2bda0 — retrieved 2026-09-18 (ArcGIS item metadata); the layer's service description carries the same licence text.
- **robots.txt:** honor — `baltegis.baltimorecity.gov/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"This work is licensed under a
> Creative Commons Attribution 3.0 Unported License"** verbatim.

## SPDX candidate

`CC-BY-3.0` — added to `policy/data/licenses.toml` this run (a different CC-BY version is a different licence; self-relicensable only).

## redistributable analysis

CC-BY-3.0 is an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

CC-BY-3.0 permits derivatives with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `CC-BY-3.0` is self-relicensable only → dedicated `ccby3` compartment (never merged into `sig_graph`'s CC-BY-4.0).

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC-BY-3.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Creative Commons licence declared by the publisher.**
