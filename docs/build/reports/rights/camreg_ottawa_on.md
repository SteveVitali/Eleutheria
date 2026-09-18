# Rights-review packet — `camreg_ottawa_on` (Ottawa enforcement-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_ottawa_on`
- **Homepage:** https://open.ottawa.ca/datasets/ottawa::red-light-camera-locations
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/adf1e7bd0338404196dc0d552aa6c79b and `…/d709c922c64b4c389afac3fb21d481fb` — retrieved 2026-09-18 (ArcGIS item metadata, owner City of Ottawa); the named licence URL `https://ottawa.ca/en/city-hall/get-know-your-city/open-data#open-data-licence-version-2-0` is JS-rendered, so the licence TEXT was verified via the Wayback Machine capture of the same page (retrieved 2026-09-18).
- **robots.txt:** honor — `services.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS items' `licenseInfo` names the **Open Government Licence - City of
> Ottawa (v2.0)**. The Wayback capture of the named licence page records:
> "The Information Provider grants you a worldwide, royalty-free, perpetual,
> non-exclusive licence to use the Information including for commercial
> purposes… You are free to: Copy, modify, publish, translate, adapt,
> distribute or otherwise use the Information in any medium, mode or format
> for any lawful purpose. You must… Acknowledge the source of the
> Information… 'Contains information licensed under the Open Government
> Licence – City of Ottawa'."

## SPDX candidate

`LicenseRef-Ottawa-ODL-2.0` — a municipal OGL-family licence, NOT the federal OGL-Canada expression; added to `policy/data/licenses.toml` this run (self-relicensable only pending counsel's compatibility mapping).

## redistributable analysis

The licence grants redistribution "in any medium, mode or format for any lawful purpose". → `redistributable = true`.

## derivative_permitted analysis

"Copy, modify, publish, translate, adapt, distribute or otherwise use" — derivatives permitted with attribution. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `LicenseRef-Ottawa-ODL-2.0` is self-relicensable only → dedicated `ottawa_odl2` compartment.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `LicenseRef-Ottawa-ODL-2.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — named OGL-family licence with verbatim grant text captured (via Wayback mirror of the same named URL).**
