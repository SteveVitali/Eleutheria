# Rights-review packet — `camreg_bellevue_wa` (City of Bellevue traffic cameras, ArcGIS)

> P36.2 (row 350) staging packet. Facts are separated from judgement; this packet
> asserts no legal conclusion (defining standard §3.1). It records the operator's
> E4-R4d decline answer — the source stays REFUSED.

- **Source id:** `camreg_bellevue_wa`
- **Homepage:** https://services1.arcgis.com/EYzEZbDhXZjURPbP/arcgis/rest/services/TrafficCameras_Public_View/FeatureServer/0
- **Terms URL(s) fetched:** ArcGIS item `licenseInfo` captured verbatim
  (P26.9, below)
- **robots.txt:** honor — probe + record (ADR-222); ArcGIS REST item not
  reviewed this pass

## Terms (verbatim)

ArcGIS item `d47e172d8d184a208121c69ac7f6d088` (234 cameras) `licenseInfo`
carries a no-warranty disclaimer PLUS:

> "Any commercial use or sale of this map or portions thereof, is prohibited
> without express written authorization by the City of Bellevue"

— an express non-commercial restriction, **not** a resolved-clear permissive
grant.

## SPDX candidate

`UNDETERMINED` — and it stays `UNDETERMINED` (declined). Under A-9 SIG's use is
or may be commercial, so a NEW non-commercial source is facts + pointers only;
no captured-terms exception applies (the ≈8,088 already-public express-terms
rows stay under ADR-183 — Bellevue is not among them).

## redistributable analysis

`redistributable = false` — declined; the express NC clause stands.

## derivative_permitted analysis

`derivative_permitted = false` — declined; no derivative grant was ever
evidenced.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

Unchanged (`MIRROR` declared; `not_contacted` compact) — the row stays REFUSED
end-to-end.

## Recorded operator answer — E4-R4d (GATE-P, 2026-10-01T04:49:27Z)

B-41 (ADR-169 §12): E4-R4d = **c — decline `camreg_bellevue_wa` (A-9 — SIG's
use is or may be commercial)**. The DECLINE is the operator's recorded
decision; this row keeps `ingestion_permitted=false` permanently unless a
future HG-03 line reverses it.

This line records the operator's answer as DATA. The agent's half: a
`DECLINED 2026-10-01 (operator, HG-03)` registry note is prepared on
`r11/sources-flips` alongside the batch's flip patch; the packet's Decision
line below records the decline.

## Decision

- [x] **declined** — `DECLINED 2026-10-01 (operator, HG-03)` — E4-R4d = c,
  B-41 (GATE-P 2026-10-01T04:49:27Z); SIG's use is or may be commercial (A-9)
  and the item's express NC clause prohibits it without written authorization
- SPDX recorded: `UNDETERMINED`   ingestion: stays `false` (REFUSED —
  `gate --source camreg_bellevue_wa` exit 1; `run --mode live` exit 3)

## Counsel-needed flag

NO — declined; a decline is a valid close (obligation event precedent:
D-SOURCES.2-2).
