# Rights-review packet — `camreg_hk_hk` (Hong Kong CCTV camera locations, ArcGIS)

> P36.2 (row 350) staging packet. Facts are separated from judgement; this packet
> asserts no legal conclusion (defining standard §3.1). It stages the operator's
> recorded E4-R4b answer — it does not flip anything (OP-26; HG-03 is the
> operator's gate).

- **Source id:** `camreg_hk_hk`
- **Homepage:** https://services3.arcgis.com/6j1KwZfY2fZrfNMR/arcgis/rest/services/CCTV_Camera_Locations_in_Hong_Kong/FeatureServer/0
- **Terms URL(s) fetched:** not fetched — item `licenseInfo` defers to
  data.gov.hk "Terms and Conditions of Use" (verbatim metadata, below)
- **robots.txt:** honor — probe + record (ADR-222); ArcGIS REST item not
  reviewed this pass

## Terms (verbatim)

ArcGIS item `0b05a33ce41d4cb7b75436dabe592c5e` (32 rows): `licenseInfo` defers
to the data.gov.hk **"Terms and Conditions of Use"** — the terms body itself
was not captured verbatim (P26.9 record). No per-record licence field exists on
the layer.

## SPDX candidate

`UNDETERMINED` — staged basis per the operator's E4-R4b answer:
`LicenseRef-OperatorAccepted-DBRight` (GL-GATE-07 non-US rule).

## redistributable analysis

Unreviewed — `redistributable = false` until the operator's flip lands.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until the operator's flip lands.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR on flip (registry already declares MIRROR); `compact_status` becomes
`public_terms_only` per the E4 §2 flip recipe.

## Recorded operator answer — E4-R4b (GATE-P, 2026-10-01T04:49:27Z)

B-41 as presented (log round 26 record clarification, S6R-02): *"R4b Hong Kong
flip"*. E4-R4b = **a — flip `camreg_hk_hk` on the non-US basis (non-US kept by
S5-4, B-34)**.

This line records the operator's answer as DATA. The agent's half: the flip
patch is prepared on `r11/sources-flips` (staging only, unsigned); the operator
applies it (OP-26 / ADR-169 §14). Nearest flipped precedent: `camreg_polyu_hk`
(HK, licence "none" → DBRight, 176 claims live).

## Decision

- [ ] permit ingestion — staged for the operator: `FLIPPED under GL-GATE-07 (non-US) — "As listed, R3 flip" / B-41 "R4b Hong Kong flip" (2026-10-01T04:49:27Z)` — reviewer: operator · date: ____
- SPDX to record: `LicenseRef-OperatorAccepted-DBRight`   rights_reviewed_by (role, never a name): `maintainer (delegated)`   rights_reviewed_on: ____

## Counsel-needed flag

NO — decided class under GL-GATE-07 (non-US); the operator-accepted
database-right basis is disclosed, never counsel-cleared (ADR-167/ADR-182).
The row stays `ingestion_permitted=false` until the operator's act.
