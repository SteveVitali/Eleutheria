# Rights-review packet — `camreg_siouxfalls_sd` (Sioux Falls traffic-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_siouxfalls_sd`
- **Homepage:** https://gis.siouxfalls.gov/arcgis/rest/services/Data/Traffic/MapServer/8
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/71ee3a06d0aa476d8c8545761dde916e — retrieved 2026-09-18 (ArcGIS item metadata, owner `cityofsiouxfallsgis`).
- **robots.txt:** honor — `gis.siouxfalls.gov/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"The City of Sioux Falls provides
> open data licensed under the Creative Commons Attribution 4.0 International
> License"** verbatim.

## SPDX candidate

`CC-BY-4.0`.

## redistributable analysis

CC-BY-4.0 is an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

CC-BY-4.0 permits derivatives with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `CC-BY-4.0` is `sig_graph`-compatible — no separate compartment needed.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC-BY-4.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Creative Commons licence declared by the publisher.**
