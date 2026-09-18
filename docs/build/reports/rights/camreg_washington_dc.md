# Rights-review packet — `camreg_washington_dc` (DC MPD CCTV street-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_washington_dc`
- **Homepage:** https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_Sensors_WebMercator/MapServer/11
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/2bb8375e31a94067a17911ea70f917ef — retrieved 2026-09-18 (ArcGIS item metadata, owner `DCGISopendata`, title "Closed Circuit TV Street Cameras"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `maps2.dcgis.dc.gov/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"This work is licensed under a
> Creative Commons Attribution 4.0 International License"** verbatim (linking
> https://creativecommons.org/licenses/by/4.0/).

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
