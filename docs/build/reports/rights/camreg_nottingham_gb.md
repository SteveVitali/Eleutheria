# Rights-review packet — `camreg_nottingham_gb` (Nottingham CCTV camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_nottingham_gb`
- **Homepage:** https://services.arcgis.com/yvqphKcf9bBSnjX1/arcgis/rest/services/CCTV_Cameras/FeatureServer/83
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/df2bf0314b184b449ff595df02e320cf — retrieved 2026-09-18 (ArcGIS item metadata, owner `nccgisteam`, title "CCTV Cameras"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `services.arcgis.com/robots.txt` answers 403 (no retrievable policy). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"Data is released under the terms
> of the Open Government Licence (OGL)
> https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"**
> verbatim, with the required attribution line **"Nottingham City Council.
> Contains OS data © Crown copyright [and database right] [year]."**

## SPDX candidate

`OGL-3.0`.

## redistributable analysis

OGL v3.0 is an explicit redistributable licence (copy, publish, distribute, adapt, commercial + non-commercial). → `redistributable = true`.

## derivative_permitted analysis

OGL v3.0 permits derivatives with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `OGL-3.0` lands in the `ogl_uk3` compartment (the UK-OGL export bucket), not `sig_graph` — the compartment split is honoured.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `OGL-3.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Open Government Licence declared by the publisher.**
