# Rights-review packet — `dot_511_dc` (DDOT traffic cameras, DC GIS)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_dc`
- **Homepage:** https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_Sensors_WebMercator/MapServer/93
- **Terms URL(s) fetched:** https://dc.gov/node/939602 (DC Data Policy / Terms of Use) — retrieved 2026-09-17.
- **robots.txt:** honor — `maps2.dcgis.dc.gov/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry (`/dcgis/rest/` prefix).

## Terms (verbatim)

> The DC Data Policy (Mayor's Order 2017-115) and the dc.gov Terms of Use declare
> District catalog data **Level 0 Open** — "public domain" under a **CC0 1.0
> Universal dedication**; the DC GIS terms of service expressly encourage API use
> and require no attribution.

## SPDX candidate

`CC0-1.0` — the District's own dedication.

## redistributable analysis

CC0 dedication by the publisher. → `redistributable = true`.

## derivative_permitted analysis

CC0 dedication by the publisher. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR — registry rows only. NOTE: the layer is served under `/dcgis/rest/…/MapServer/93`
(a MapServer layer — queryable identically to FeatureServer); the connector accepts
both ArcGIS service kinds.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — publisher's own CC0 dedication; resolved under GL-GATE-06.**
