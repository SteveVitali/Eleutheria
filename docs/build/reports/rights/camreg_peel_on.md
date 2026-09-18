# Rights-review packet — `camreg_peel_on` (Peel Region red-light camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_peel_on`
- **Homepage:** https://services6.arcgis.com/ONZht79c8QWuX759/arcgis/rest/services/Red_Light_Cameras/FeatureServer/0
- **Terms URL(s) fetched:**
  - https://www.arcgis.com/sharing/rest/content/items/36dbfcb33aa2453c8de55e0a34ccfc6a — retrieved 2026-09-18 (ArcGIS item metadata, owner `RegionofPeel`, title "Red Light Cameras"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
  - https://data.peelregion.ca/pages/license — the licence page itself is JS-rendered; its terms text was captured from the Wayback Machine snapshot of the same page (retrieved 2026-09-18).
- **robots.txt:** honor — `services6.arcgis.com/robots.txt` answers 403 (no retrievable policy). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` names **"Open Data Licence for The Regional
> Municipality of Peel (Version 1.0)"** verbatim, linking
> `https://data.peelregion.ca/pages/license`.
>
> The captured licence page text states **"Our license allows you to copy,
> publish, redistribute, adapt, and use our data for personal or commercial
> purposes"** — the OGL-family permissive grant — alongside the Region's
> attribution requirement.

## SPDX candidate

`LicenseRef-Peel-ODL-1.0` — a municipal open-data licence (not an SPDX-listed
identifier and not the federal OGL-Canada expression); registered in
`policy/src/policy/data/licenses.toml` with its own `peel_odl1` compartment.

## redistributable analysis

The captured grant permits copy/publish/redistribute, personal or commercial. → `redistributable = true`.

## derivative_permitted analysis

The captured grant permits "adapt" explicitly. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived and not ODbL — the custom Peel licence gets its own
`peel_odl1` compartment; claims never merge into `sig_graph` or `osm_physical`.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `LicenseRef-Peel-ODL-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — the licence grant text was captured verbatim (Wayback snapshot of the named licence page); the custom licence is isolated in its own compartment pending any later counsel review of the municipal terms.**
