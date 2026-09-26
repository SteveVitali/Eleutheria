# Rights-review packet — `dot_511_or` (ODOT TripCheck camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_or`
- **Homepage:** https://services.arcgis.com/uUvqNMGPm7axC2dD/arcgis/rest/services/TripCheck_Cameras/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/1e3fb7169cd74127b9c1707258a6e6e9 — retrieved 2026-09-17 (ArcGIS item metadata, Oregon_OEM / ODOT org).
- **robots.txt:** honor — `services.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` reads `Public` — the publisher's own declaration
> that the layer is public. ODOT/OEM TripCheck camera locations are state public
> records the agencies published openly; no use restriction is asserted anywhere in
> the item or service metadata.

## SPDX candidate

`CC0-1.0` — state public record declared `Public` by the publisher with no asserted restriction.

## redistributable analysis

Publisher-declared `Public`; no restriction asserted. → `redistributable = true`.

## derivative_permitted analysis

No condition asserted. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — publisher-declared public state record; resolved under GL-GATE-06.**
