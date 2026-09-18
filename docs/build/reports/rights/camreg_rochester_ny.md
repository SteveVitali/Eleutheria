# Rights-review packet — `camreg_rochester_ny` (Rochester NY BlueLight camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_rochester_ny`
- **Homepage:** https://services7.arcgis.com/wMvCpnbQEKXZsPSQ/arcgis/rest/services/Rochester_Cameras/FeatureServer/0
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/4df36db389e240efa672346101ede541 — retrieved 2026-09-18 (ArcGIS item metadata, owner `rpdny.pub`, title "Rochester Cameras"; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `services7.arcgis.com/robots.txt` answers 403 (no retrievable policy). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The ArcGIS item's `licenseInfo` carries an RPD accuracy disclaimer —
> **"These data are based upon preliminary information supplied to the
> Rochester Police Department by the reporting parties and have not been
> verified… The Rochester Police Department does not guarantee (either
> expressed or implied) the accuracy, completeness, or timeliness of the
> information."** — followed by the licence grant: **"This data is made
> available under the Open Database License:
> http://opendatacommons.org/licenses/odbl/1.0/ Any rights in individual
> contents of the database are licensed under the Database Contents License:
> http://opendatacommons.org/licenses/dbcl/1.0/"**
>
> The disclaimer is a data-quality statement about the police incident data
> this portal also hosts — it carries no rights restriction on the registry
> rows.

## SPDX candidate

`ODbL-1.0` (with DbCL-1.0 on contents — the standard ODC pairing).

## redistributable analysis

ODbL-1.0 is an explicit redistributable licence with share-alike + attribution obligations — honoured by the compartment below. → `redistributable = true`.

## derivative_permitted analysis

ODbL-1.0 permits derivatives (produced works carry notice + the derived-database share-alike rule applies to the database itself). → `derivative_permitted = true`.

## ODbL compartment implications

**This is the load-bearing decision.** ODbL-1.0 claims land in the
`osm_physical` compartment (the existing ODbL/OSM bucket in
`policy/src/policy/data/licenses.toml`) — never merged into the CC-BY
`sig_graph` compartment. Export keeps the share-alike boundary intact.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `ODbL-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — ODbL-1.0 + DbCL-1.0 declared verbatim; compartment routing follows the existing §42.3 ODbL policy.**
