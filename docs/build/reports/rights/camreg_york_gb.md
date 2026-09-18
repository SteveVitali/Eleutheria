# Rights-review packet — `camreg_york_gb` (City of York CCTV camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_york_gb`
- **Homepage:** https://maps.york.gov.uk/arcgis/rest/services/Public/LV_TranStreetCare/MapServer/26
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/25888f6f64e64cc6a938115a8f12f333 — retrieved 2026-09-18 (ArcGIS item metadata, owner `gis_CYC`, title "CCTV"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `maps.york.gov.uk/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"© Crown copyright and database
> rights 2017 Ordnance Survey 100020818"**, states **"The licensing for this
> dataset is listed as Derived data exemption - streamlined process"** (OS
> public-sector derived-data guidance), and cites **"the Open Government
> Licence (OGL v3.0) - see the National Archives"** verbatim.

## SPDX candidate

`OGL-3.0`.

## redistributable analysis

The OS derived-data exemption publishes council data under OGL v3.0, an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

OGL v3.0 permits derivatives with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived (Ordnance Survey GB — unrelated to OpenStreetMap). `OGL-3.0` lands in the `ogl_uk3` compartment — not `sig_graph`.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `OGL-3.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — OGL v3.0 cited verbatim via the OS derived-data exemption, with the attribution statement preserved.**
