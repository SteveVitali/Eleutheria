# Rights-review packet — `dot_511_ut` (UDOT Live View camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_ut`
- **Homepage:** https://services.arcgis.com/pA2nEVnB6tquxgOW/arcgis/rest/services/Live_View_Cameras/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/d3f7dae59eba45459bd9ba6a37f6ba56 — retrieved 2026-09-17 (ArcGIS item metadata, owner `nlucchetti@utah.gov_uplan` — a Utah state org account).
- **robots.txt:** honor — `services.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` is an informational-use / no-warranty notice: the
> data is provided for information purposes without warranty; the text asserts **no
> use restriction** — no redistribution bar, no licence grant needed, no attribution
> condition. UDOT camera locations are state public records the agency published
> openly.

## SPDX candidate

`CC0-1.0` — state public record published with no asserted restriction.

## redistributable analysis

No restriction asserted by the publisher; state public record. → `redistributable = true`.

## derivative_permitted analysis

No condition asserted. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR — registry rows only. NOTE: this layer carries **geometry-only coordinates**
(coordinates in `geometry`, sparse attributes) — the connector emits location claims
with the row locator and marks absent roadway/jurisdiction fields honestly rather
than fabricating them.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — state public record with no asserted use restriction; resolved under GL-GATE-06.**
