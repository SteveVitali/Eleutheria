# Real-data regression corpus — source register (P35.23 / SIG-CONF-008)

Every slice is a captured excerpt of upstream bytes. `committed` slices carry
bytes in this tree under licences whose recorded redistribution lane is
`raw-ok` (source registry `sources.toml`) and which are not ODbL-compartment
material. `restricted` slices commit only SHA-256 member digests; their bytes
live in the screened compartment bucket (`gs://…-sig-restricted/ops/rdc/slices/…`)
and run under the scheduled `sig-rdc-probe` job (SIG-CONF-013 posture).

Oracles (`ops/src/ops/rdc_oracles.py`) compute expected facts from the raw
bytes with pipeline-independent code. `snapshots/` pins the computed digests;
a drift outside an appended `approvals` entry refuses — snapshot changes land
only as explicit commits with rationale + diff summary.

## Committed slices

| slice | source (registry id) | licence | capture | records |
|---|---|---|---|---|
| `camreg_dc_multiview/` | `camreg_washington_dc` — DCGIS ArcGIS "Closed Circuit TV Street Cameras" layer | CC-BY-4.0 — District of Columbia CCTV street camera registry (DCGIS open data) | OCFL live run 2026-09-18, two ArcGIS query pages (`resultOffset` 0 + 1000) | 1,060 cameras |
| `camreg_nottingham_axis/` | `camreg_nottingham_gb` — Nottingham City Council "CCTV Cameras" FeatureServer/83 | OGL-UK-3.0 — Nottingham City Council. Contains OS data © Crown copyright | OCFL live run 2026-09-18, one query page | 562 cameras (all records carry the recorded Lat/Long transposition) |
| `eff_atlas_multistate/` | `eff_atlas_of_surveillance` — Atlas of Surveillance `download.csv` | CC-BY-4.0 — Electronic Frontier Foundation | OCFL live run 2026-09-15; excerpt = every row for the first 150 alphabetical normalised agency names asserted in ≥2 states | 736 rows, 150 multi-state names |
| `usaspending_topical/` | `usaspending` — `spending_by_award` sub-award page | CC0-1.0 — USAspending.gov (U.S. Department of the Treasury) | OCFL live run 2026-09-15 | 100 sub-award rows |

## Restricted slices (digest-only; bytes in the screened compartment bucket)

| slice | source (registry id) | why restricted | capture | members |
|---|---|---|---|---|
| `restricted/eff_data_driven_2016_2017/` | `eff_data_driven` (CC-BY-4.0, lane `derived-only`) | raw redistribution outside derived exports is not licensed for committed bytes | `sig:capture:bcnab3jd…` (live run 2026-09-15) | `alpr_2016-2017_update.zip` sha256 `e29950fe…` |
| `restricted/legistar_tenant_collision/` | `legistar` (CC0-1.0, lane `derived-only`) | same — raw pages stay in the compartment | live run 2026-09-17 (`?top=100` matters pages) | `albemarle_matters.json` sha256 `efee6e8a…`, `bart_matters.json` sha256 `a7837afb…` |
| `restricted/osm_okc_surveillance/` | `osm_overpass` (ODbL-1.0) | ODbL compartment material — never a committed fixture (§42.3) | `sig:capture:bcnaaosf…` (live run 2026-09-15) | `overpass_nodes.json` sha256 `34dd1d93…` (647 nodes) |

## Findings recorded by the corpus landing

* `camreg_dc_multiview`: the upstream `ID` field is non-unique (533 rows null,
  24 rows `0.0`, repeated floats) while `OBJECTID` is unique — under the
  P35.24/GQ-04 per-capture key uniqueness rule the connector run fails closed
  (`SubjectKeyCollision`). That fail-closed outcome is the pinned pipeline
  expectation; re-keying the target (`camera_ref_field = "OBJECTID"`) is a
  registry decision outside this ticket's scope.
* `camreg_nottingham_axis`: all 562 `Lat`/`Long` attribute pairs hold
  transposed values (the recorded axis-swap archetype); every entity asserts
  `geometry_defect` and no device coordinate.
* `legistar_tenant_collision`: 71 of 100 `MatterFile` keys collide across the
  albemarle/bart pair — tenant-scoped namespaces must stay apart.
