# Description batch 08 — agent-drafted source descriptions awaiting operator verbatim confirmation

<!-- P36.45 (R11-K13-UX10-1; D-J3-12 / OD-07 a — 'batches of ~25 confirmed verbatim; description pending review until then'). Append-only: a status change is recorded in the confirmation log below with a `date -u` stamp; rows are never deleted. -->

## Convention

One row per agent-drafted per-source description — the **source** id,
the exact **text** as it will render, its **sha256** (UTF-8, no trailing
newline), and a **status** (`pending` · `confirmed`). Only `confirmed`
descriptions may land on the registry `description` field — the
publish-matrix lint fails a declared description whose sha256 matches
no confirmed row here. An unconfirmed source publishes
`description_pending_review`.

## Rows

| id | source | text | sha256 | status |
|---|---|---|---|---|
| D08-01 | camreg_nitro | `Camera feeds registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | f3bb5af4a590a3b7d5a3ce32c5edfb32ae5487814442f7088691220d41a82228 | pending |
| D08-02 | camreg_nj_new_jersey_yourmoney | `New Jersey YourMoney - Agency Purchasing (ubnu-tqu7)` — a government portal source published by `State of New Jersey, Treasury - Division of Purchase and Property (via Socrata)`. | 733b9923acb31eb5d2f1dd9c1b09a55878e889a7d8752807f7913ca5f68a6776 | pending |
| D08-03 | camreg_nola_la | `New Orleans traffic cameras (Socrata open-data registry)` — a government portal source published by `City of New Orleans Department of Public Works`. | 56a492f1518395f69dea476dc4c3a104f6b01188947eaf4b903aa376b4428ac5 | pending |
| D08-04 | camreg_nola_safety_la | `New Orleans traffic safety cameras (ArcGIS registry)` — a government portal source published by `City of New Orleans`. | 3314acefd630ee92af90768b37b8f2a9b9b6cd9a3bb0e49be84f1c9679770574 | pending |
| D08-05 | camreg_northayrshire_gb | `North Ayrshire CCTV cameras (ArcGIS registry)` — a government portal source published by `North Ayrshire Council`. | 14941f416c5009bf0dfa1897639de4cddbbef49fbf29924d975309bf3754ecc3 | pending |
| D08-06 | camreg_nottingham_gb | `Nottingham CCTV cameras (ArcGIS registry)` — a government portal source published by `Nottingham City Council`. | b41b9bd3e23cdb9ff7064aca239441c0b5e859c6b11cdebd2a65f3cac9297a74 | pending |
| D08-07 | camreg_nv_las_vegas_us_clark_county | `Shotspotter and Metrocams_WFL1 (layers METROCAMS, SHOTSPOTTER)` — a government portal source published by `Clark County (NV) GIS Management Office (via ArcGIS Online), mapping LVMPD equipment on municipal ROW facilities`. | ad1a0009b6e0546e1794e507995f21c7c800849755a0d13d59c368158a90ad45 | pending |
| D08-08 | camreg_nyc_mta_bus_lane_ate | `MTA Bus Automated Camera Enforced Routes: Beginning October 2019 (route programme register)` — a government portal source published by `Metropolitan Transportation Authority (New York City Transit / MTA Bus) via data.ny.gov`. | 3ee66012338085488b9c4e24b1fac73197f23204c702f5fa7708bf5ca769b329 | pending |
| D08-09 | camreg_nzta_nz | `NZTA traffic cameras (ArcGIS public view)` — a government portal source published by `NZ Transport Agency Waka Kotahi, NZTA, NZTA, Eagle Technology Group, Open.Data_NZTA`. | 9d15a0d6c039df070b83a3d10ef81fff6a42769f20db5f5d72ba574d78f6ac6b | pending |
| D08-10 | camreg_oakland_ca_shotspotter_2013_2015 | `Oakland Police Department Shotspotter Data 2013-2015 (PRR 11288 release, 5 datasets)` — a government portal source published by `City of Oakland (attribution: Oakland Police Department)`. | a03b216c6fc73d89c4da8f25c7ed53db9de723c6fc66a73983a3cbc40807a06e | pending |
| D08-11 | camreg_oem_camera | `Potential camera and gauge locations (OEM ArcGIS registry)` — a government portal source published by `ArcGIS community-published camera registry`. | 80159db1642b08bbc5f4f99ecee07588f75820e01baaca134c8a80d1f7e46d6e | pending |
| D08-12 | camreg_omaha_ne_parks_cameras | `Parks_Cameras (City of Omaha-maintained cameras, College World Series)` — a government portal source published by `Douglas-Omaha GIS (DOGIS) for City of Omaha Parks (via ArcGIS Online org pDAi2YK0L0QxVJHj)`. | 25434c3a071dc9c717cd273ec6bd8f69d4e563d70f0165d889de18e39946d703 | pending |
| D08-13 | camreg_oosgis_nl | `Dutch camera registry (OOS GIS, CEVI schema)` — a government portal source published by `Dutch municipal camera registry (oosgis publisher)`. | 3d81f423e87a1b140d0ce77962a482adb7e1de189f2a197d28cd56711d8df24b | pending |
| D08-14 | camreg_osm_surveillance | `OSM-derived surveillance-camera layers (DeFlock/OSM exports)` — a government portal source published by `OpenStreetMap contributors (republished man_made=surveillance nodes)`. | 72ff58a0a72d6598c7bd140d3be28b96001b88c3b1ef9f3139ba3a9afd4bc673 | pending |
| D08-15 | camreg_ottawa_on | `Ottawa enforcement cameras (ArcGIS open-data registry)` — a government portal source published by `City of Ottawa`. | 9d9776a58978138d0dce3a9a8487ded0fe4ef4c305c46625e7b3f73eb808bc58 | pending |
| D08-16 | camreg_palmdesert_ca | `Palm Desert license-plate-recognition camera locations (ArcGIS registry)` — a government portal source published by `City of Palm Desert, California`. | 8eb419af74b84fc7847aba3bcdb554f0e173a6533d83fb796fb72289db1aae61 | pending |
| D08-17 | camreg_peel_on | `Peel Region red-light cameras (ArcGIS registry)` — a government portal source published by `Regional Municipality of Peel`. | dca6b262054ca840685dbfd75612be0c8f0ab31832f6985504f89852622c16fd | pending |
| D08-18 | camreg_penndot_pa | `PennDOT CCTV cameras (ArcGIS registry)` — a government portal source published by `Pennsylvania Department of Transportation (publisher account)`. | a0f531637cc79f56757cdcd95decfac5e6ef9c931116a784bb2b79b0ee8293d8 | pending |
| D08-19 | camreg_peoria_il_drone_usage | `Peoria Police Department Drone Usage` — a government portal source published by `City of Peoria, IL (via ArcGIS Online)`. | bc92faa07c2a9d45188dd4892eb3b63e8140f653ffd328d853fc9c71ebadac9c | pending |
| D08-20 | camreg_pgcounty_md | `Prince George's County speed/red-light cameras (Socrata registry)` — a government portal source published by `Prince George's County, Maryland (PGPD)`. | 9dddadf23c9b463b6af1b78ea2a33adceee6fb7d8cb2395ef8eae32b38e90112 | pending |
| D08-21 | camreg_pipeline_sec | `Traffic/security camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 546f2034bbb36d91e5b22097da54d6e2c9a78021222e7aa595f9b705cffa4738 | pending |
| D08-22 | camreg_plymouth_gb | `Plymouth traffic cameras (ArcGIS registry)` — a government portal source published by `Plymouth City Council`. | f766b70d464342cc4c9c7f9f50c46a38e36a95089d30c4c0e0f2f5dfff6293a5 | pending |
| D08-23 | camreg_polyu_hk | `Hong Kong CCTV camera layers (esrichina.hk ArcGIS registry)` — a government portal source published by `Hong Kong PolyU/police CCTV layers (community-published)`. | 56a1cf1d1bffde428188e4ce25a78790ec462d42ae0bffcb528dafd41b32f82e | pending |
| D08-24 | camreg_portland_or | `Portland ITS cameras (portlandmaps ArcGIS registry)` — a government portal source published by `City of Portland, Oregon`. | 3c5005412506bc62bf4864bd1878889ee763d84f10b28db4816e04268d692e8d | pending |
| D08-25 | camreg_pt_11_lisboa_sistema_de | `Sistema de Videovigilância Bairro Alto` — a government portal source published by `Município de Lisboa`. | e1c151793fb120d4f55ca9bceaadde7eb1bcd63b39c75ae6b21a993407de8364 | pending |

## Confirmation log

(none yet)
