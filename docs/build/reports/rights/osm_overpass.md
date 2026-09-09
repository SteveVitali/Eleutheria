# Rights-review packet — `osm_overpass` (OSM Overpass API)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `osm_overpass`
- **Homepage:** https://overpass-api.de/api/interpreter
- **Terms URL(s):** https://www.openstreetmap.org/copyright
- **robots.txt:** honor (OSM/OSMF API + tile usage policies apply; §26 etiquette).

## Terms (verbatim)

> Fetched from https://www.openstreetmap.org/copyright on 2026-09-09 (terms page,
> not source content — permitted research):
>
> "OpenStreetMap is *open* data, licensed under the Open Data Commons Open Database
> License (ODbL) by the OpenStreetMap Foundation (OSMF). In summary: You are free to
> copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap
> and its contributors. If you alter or build upon our data, you may distribute the
> result only under the same license. The full legal code at Open Data Commons
> explains your rights and responsibilities."
>
> "Where you use OpenStreetMap data, you are required to do the following two things:
> Provide credit to OpenStreetMap by displaying our attribution notice. Make clear
> that the data is available under the Open Database License."
>
> "Although OpenStreetMap is open data, we cannot provide a free-of-charge map API or
> map tiles for third-parties. See our API Usage Policy, Tile Usage Policy and
> Nominatim Usage Policy." (§26 crawler-conduct / etiquette applies.)

## SPDX candidate

`ODbL-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Redistributable under ODbL-1.0 with the two required credit/licence-notice conditions. redistributable=true is separately reviewed (SIG-LIC-003), not derived from the SPDX string.  → registry `redistributable = true`.

## derivative_permitted analysis

Derivatives permitted; a derived database inherits the ODbL share-alike obligation (SIG-LIC-009a). derivative_permitted=true.  → registry `derivative_permitted = true`.

## ODbL compartment implications

OSM-derived ⇒ ODbL compartment (RISK-P0-01/02). The share-alike/attribution and §4.4(b) sui-generis questions are for counsel (HG-02); until dispositioned the OSM-derived layer is export/link-only.

## Custody posture recommendation

REFERENCE (fetch + hold derived facts); never the canonical editing DB (N7).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `ODbL-1.0`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**YES — ODbL §4.4(b) sui-generis + share-alike travel (RISK-P0-01/02, HG-02).**
