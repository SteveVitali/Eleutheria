# Rights-review packet — `camreg_qldc_au` (Queensland CCTV cameras, ArcGIS external view)

> P36.2 (row 350) staging packet. Facts are separated from judgement; this packet
> asserts no legal conclusion (defining standard §3.1). It records the operator's
> E4-R4c route-change answer — it does not flip anything (OP-26; HG-03 is the
> operator's gate).

- **Source id:** `camreg_qldc_au`
- **Homepage:** https://services1.arcgis.com/9YyqaQtDdDR8tupG/arcgis/rest/services/CCTV_Cameras_(External_View)/FeatureServer/0
- **Terms URL(s) fetched:** ArcGIS item `licenseInfo` captured (verbatim, below);
  the QLDTraffic API terms are P37.70's capture, not this row's
- **robots.txt:** honor — probe + record (ADR-222); ArcGIS REST item not
  reviewed this pass

## Terms (verbatim)

ArcGIS item `eebb997724054f8a816efde37a5b40a6` ("CCTV Cameras (External View)",
240 rows) `licenseInfo` says only:

> "Currently available for external use"

— an availability statement, **not a licence grant** (P26.9 record). The
authoritative QLDTraffic v1 API is token-gated and carries CC-BY-3.0/4.0 on the
CKAN dataset record (the API-key registration is the operator's B-18 / HG-09
act).

## SPDX candidate

`UNDETERMINED` — and it stays `UNDETERMINED`: the operator declined the flip
route for this registry row (see below).

## redistributable analysis

Unreviewed — `redistributable = false`; no flip is staged for this row.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false`; no flip is staged for this row.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

Unchanged (`MIRROR` declared; `not_contacted` compact). The Queensland camera
coverage moves to the QLDTraffic API connector at **P37.70** (row 434); the
ArcGIS republish row stays gated.

## Recorded operator answer — E4-R4c (GATE-P, 2026-10-01T04:49:27Z)

B-41 (ADR-169 §12): E4-R4c = **b — use the QLDTraffic API instead (key
registered by the operator, B-18)** — the decision lands at P37.70; the line
is recorded here.

This line records the operator's answer as DATA. Consequence staged in this
row: a registry note recording the route change (prepared on
`r11/sources-flips` alongside the batch's flip patch — `ingestion_permitted`
stays false regardless).

## Decision

- [x] **route recorded — no flip**: `camreg_qldc_au` coverage routes to the
  QLDTraffic API (CC-BY per CKAN) under P37.70; this ArcGIS row stays
  `ingestion_permitted=false` — recorded for the operator 2026-10-01
  (B-41, GATE-P)

## Counsel-needed flag

NO — the row was never flipped; the API route's terms land with P37.70.
