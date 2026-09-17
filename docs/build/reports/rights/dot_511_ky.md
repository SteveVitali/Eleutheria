# Rights-review packet — `dot_511_ky` (KYTC traffic-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms/metadata page is permitted research, not ingestion; no source *content* was
> fetched beyond the metadata and the registry row count.

- **Source id:** `dot_511_ky`
- **Homepage:** https://services2.arcgis.com/CcI36Pduqd0OR4W9/arcgis/rest/services/trafficCamerasCur_Prd/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/00715d24d2bf42e5abc1fab8a08d45eb — retrieved 2026-09-17 (ArcGIS item metadata, owner `kytc.gis_KYTC` — the Kentucky Transportation Cabinet's own org account).
- **robots.txt:** honor — `services2.arcgis.com/robots.txt` answers 403 (no policy exists — RFC 9309 §2.3.1.4 / ADR-087). Access is API MODE under the recorded `api_allowlist.toml` entry (documented ArcGIS REST query API), not a crawl.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` is the KYTC no-warranty disclaimer: the data is
> provided "as is" without warranty; the text asserts **no use restriction** — no
> redistribution bar, no licence grant needed, no attribution condition. Kentucky
> Transportation Cabinet traffic-camera locations are state public records the
> agency itself published openly.

## SPDX candidate

`CC0-1.0` — state public record published with no asserted restriction (accepted per `policy/data/licenses.toml`).

## redistributable analysis

No restriction asserted by the publisher; state public record published openly on the agency's own org account. → `redistributable = true`.

## derivative_permitted analysis

No condition asserted; derived facts permitted. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR — the camera registry rows (location/roadway/jurisdiction/identifier) are the evidence; feed content URLs in the rows are never fetched or emitted.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**NO — state public record with no asserted use restriction; resolved under GL-GATE-06.**
