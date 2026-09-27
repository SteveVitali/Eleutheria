# Rights-review packet — `camreg_sheffield_gb` (Sheffield CCTV + traffic-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_sheffield_gb`
- **Homepage:** https://utility.arcgis.com/usrsvcs/servers/c5b5971a1c1248faa95649d081849aa1/rest/services/AGOL/OpenData/MapServer/7
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/c5b5971a1c1248faa95649d081849aa1 — retrieved 2026-09-18 (ArcGIS item metadata, 'CCTV and Traffic Cameras', Sheffield City Council).
- **robots.txt:** honor — `utility.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **"This dataset is published under
> the Open Government license (OGL) by downloading this data you agree to the
> terms of the OGL. All use of the data must contain the acknowledgment
> 'Contains OS data © Crown Copyright [and database right] [year]'"** verbatim.

## SPDX candidate

`OGL-3.0` — the UK Open Government Licence v3.0; added to `policy/data/licenses.toml` this run (self-relicensable only pending counsel's compatibility mapping). The OS-attribution clause applies to OS-derived fields; the claim evidence carries the attribution string.

## redistributable analysis

OGL-3.0 is an explicit redistributable licence with attribution. → `redistributable = true`.

## derivative_permitted analysis

OGL-3.0 permits use "for any purpose" including derivatives, with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `OGL-3.0` is self-relicensable only → dedicated `ogl_uk3` compartment.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `OGL-3.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Open Government Licence declared by the publisher.**
