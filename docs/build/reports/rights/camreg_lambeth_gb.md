# Rights-review packet — `camreg_lambeth_gb` (Lambeth parking CCTV registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_lambeth_gb`
- **Homepage:** https://gis.lambeth.gov.uk/arcgis/rest/services/LambethParkingCCTVCameras/MapServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/2dd843a8605a4b2981790816ec1b4a57 — retrieved 2026-09-18 (ArcGIS item metadata, owner `opendata@lambeth.gov.uk`, title "Parking CCTV Cameras"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `gis.lambeth.gov.uk/robots.txt` answers 403 (no retrievable policy). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` carries the Open Government Licence URI
> verbatim — **"https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"** —
> as the item's licence statement from the council open-data account
> (`opendata@lambeth.gov.uk`).

## SPDX candidate

`OGL-3.0`.

## redistributable analysis

The licence field names the OGL v3.0 URI — an explicit redistributable licence. → `redistributable = true`.

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

**NO — the licence field carries the OGL v3.0 licence URI verbatim from the council's open-data account.**
