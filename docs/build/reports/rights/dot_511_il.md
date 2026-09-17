# Rights-review packet — `dot_511_il` (IDOT Illinois Gateway traffic cameras)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_il`
- **Homepage:** https://services2.arcgis.com/aIrBD8yn1TDTEXoz/arcgis/rest/services/TrafficCamerasTM_Public/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/8a885da23dfb46caaa1827ad920fb5b1 — retrieved 2026-09-17 (ArcGIS item metadata, owner `IDOTAdmin` — the Illinois DOT's own org account).
- **robots.txt:** honor — `services2.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` declares **Creative Commons Attribution-ShareAlike
> 2.0 Generic** verbatim — an explicit licence grant by the publishing agency, not a
> disclaimer and not an absence of terms.

## SPDX candidate

`CC-BY-SA-2.0` (row added to `policy/data/licenses.toml` this pass: `share_alike = true`, `relicensable_to = ["CC-BY-SA-2.0"]`).

## redistributable analysis

CC-BY-SA-2.0 is an explicit redistributable licence. → `redistributable = true`.

## derivative_permitted analysis

CC-BY-SA-2.0 permits derivatives under share-alike. → `derivative_permitted = true`.

## Compartment implications

Share-alike: Illinois Gateway claims land in the dedicated **`dot511_ccbysa2`**
compartment (`licenses.toml`), never merged into `sig_graph` (CC-BY-4.0) or
`portal` (CC-BY-SA-4.0 — a different version is a different licence).
Not OSM-derived; no ODbL implication.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC-BY-SA-2.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — explicit Creative Commons licence declared by the publisher; compartment math recorded in `licenses.toml`.**
