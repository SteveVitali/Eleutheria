# Rights-review packet — `camreg_glasgow_gb` (Glasgow CCTV camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_glasgow_gb`
- **Homepage:** https://www.mapping.glasgow.gov.uk/arcgis_web/rest/services/OPEN_DATA/CCTV/MapServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/669df23dcc5d48bb98ad1b5d180927c6 — retrieved 2026-09-18 (ArcGIS item metadata, owner `GlasgowGIS`, title "CCTV"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `www.mapping.glasgow.gov.uk/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"This information is supplied
> under the Open Government License v3.0"** (linking
> nationalarchives.gov.uk/doc/open-government-licence/version/3/) verbatim, and
> adds **"Licensed under the One Scotland Mapping Agreement (OSMA). All mapping
> data is subject Crown Copyright and database right 2022, all rights reserved.
> Ordnance Survey Licence number 100023379."**

## SPDX candidate

`OGL-3.0`.

## redistributable analysis

OGL v3.0 is an explicit redistributable licence; the OSMA/Ordnance-Survey licence-number note is the attribution trail, not a rights restriction. → `redistributable = true`.

## derivative_permitted analysis

OGL v3.0 permits derivatives with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `OGL-3.0` lands in the `ogl_uk3` compartment — not `sig_graph`.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `OGL-3.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — OGL v3.0 declared verbatim by the publishing council.**
