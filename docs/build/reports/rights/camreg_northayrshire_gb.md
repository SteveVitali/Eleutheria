# Rights-review packet — `camreg_northayrshire_gb` (North Ayrshire CCTV registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_northayrshire_gb`
- **Homepage:** https://www.maps.north-ayrshire.gov.uk/arcgis/rest/services/AGOL/Open_Data_Portal4/MapServer/12
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/082112796ccd448bb1abba9e9603e9f0 — retrieved 2026-09-18 (ArcGIS item metadata, owner `NAC_OpenData`, title "CCTV Locations"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `www.maps.north-ayrshire.gov.uk/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"This information is supplied
> under the Open Government License v3.0
> (http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3)"**
> verbatim, and requires the attribution statement **"Copyright North Ayrshire
> Council, contains Ordnance Survey data © Crown copyright and database right
> (2018)"** — preserved on the source row's `rights.attribution`.

## SPDX candidate

`OGL-3.0`.

## redistributable analysis

OGL v3.0 is an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

OGL v3.0 permits derivatives with attribution; the named attribution statement is recorded. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `OGL-3.0` lands in the `ogl_uk3` compartment — not `sig_graph`.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `OGL-3.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — OGL v3.0 declared verbatim by the publishing council.**
