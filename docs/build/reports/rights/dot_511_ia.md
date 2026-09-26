# Rights-review packet — `dot_511_ia` (Iowa DOT traffic-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_ia`
- **Homepage:** https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/Traffic_Cameras_View/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/c4063f200a7b4da5826e2ac86c677cf5 — retrieved 2026-09-17 (ArcGIS item metadata, owner `IowaDOT_OTO` — the Iowa DOT's own org account).
- **robots.txt:** honor — `services.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **Creative Commons Attribution 4.0**
> verbatim — an explicit licence grant by the publishing agency.

## SPDX candidate

`CC-BY-4.0` (already registered in `policy/data/licenses.toml`).

## redistributable analysis

CC-BY-4.0 is an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

CC-BY-4.0 permits derivatives with attribution (recorded in the rights row). → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. CC-BY-4.0 is `sig_graph`-compatible (same expression) — no separate compartment needed; attribution is carried on every emitted claim's evidence.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC-BY-4.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — explicit Creative Commons licence declared by the publisher.**
