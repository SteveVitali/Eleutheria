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
| D08-01 | camreg_nitro | Camera feeds registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 5ea2e4fe93e955574603e0cd90b8274c52c31333fe6d30d944b1b40b35acaa0d | pending |
| D08-02 | camreg_nj_new_jersey_yourmoney | New Jersey YourMoney - Agency Purchasing (ubnu-tqu7) — a government portal source published by State of New Jersey, Treasury - Division of Purchase and Property (via Socrata). | eb44bdc2c19c9f99013c58530e36b527195f2be432bddf10dd8d683b149e378a | pending |
| D08-03 | camreg_nola_la | New Orleans traffic cameras (Socrata open-data registry) — a government portal source published by City of New Orleans Department of Public Works. | 13866c001f2fdd36d9e5f028536a8e411acbf8d4204b51c1324d758dcfc7f0ed | pending |
| D08-04 | camreg_nola_safety_la | New Orleans traffic safety cameras (ArcGIS registry) — a government portal source published by City of New Orleans. | a4b46acaa75df58daa27f690eb343aa70b61f7535c23810ccaf0bec036368e30 | pending |
| D08-05 | camreg_northayrshire_gb | North Ayrshire CCTV cameras (ArcGIS registry) — a government portal source published by North Ayrshire Council. | bce1184dee82faf8ee4cfcb1918f54db825bb76d93676dc430973b5faca9211c | pending |
| D08-06 | camreg_nottingham_gb | Nottingham CCTV cameras (ArcGIS registry) — a government portal source published by Nottingham City Council. | 6d2ffeaa8129c9942ea5e0b312b44586ba122431aa86e4bd0f232d5877daf02b | pending |
| D08-07 | camreg_nv_las_vegas_us_clark_county | Shotspotter and Metrocams_WFL1 (layers METROCAMS, SHOTSPOTTER) — a government portal source published by Clark County (NV) GIS Management Office (via ArcGIS Online), mapping LVMPD equipment on municipal ROW facilities. | 5f8af3007fa418de0af17927f8d3e6879043cd7c074e277ff1c1ce0d0310cb40 | pending |
| D08-08 | camreg_nyc_mta_bus_lane_ate | MTA Bus Automated Camera Enforced Routes: Beginning October 2019 (route programme register) — a government portal source published by Metropolitan Transportation Authority (New York City Transit / MTA Bus) via data.ny.gov. | 7a1bbf81c2a243ed416ecbe495f40bda4038c7a8d194d452301266de396bcf2e | pending |
| D08-09 | camreg_nzta_nz | NZTA traffic cameras (ArcGIS public view) — a government portal source published by NZ Transport Agency Waka Kotahi; NZTA; NZTA, Eagle Technology Group; Open.Data_NZTA. | 5337de5c7909e8d21aabdb40027eef77e2bc16d5baff1c170a31d025eb8dd08f | pending |
| D08-10 | camreg_oakland_ca_shotspotter_2013_2015 | Oakland Police Department Shotspotter Data 2013-2015 (PRR 11288 release, 5 datasets) — a government portal source published by City of Oakland (attribution: Oakland Police Department). | b752cf35adeb354a78a3923e595d963b9df49457ebfaba6095a6d92e36861d4c | pending |
| D08-11 | camreg_oem_camera | Potential camera and gauge locations (OEM ArcGIS registry) — a government portal source published by ArcGIS community-published camera registry. | 1741194752b862d448dd3ef5b2711f7f0585aea71a125d7d87169b9fdcac2336 | pending |
| D08-12 | camreg_omaha_ne_parks_cameras | Parks_Cameras (City of Omaha-maintained cameras; College World Series) — a government portal source published by Douglas-Omaha GIS (DOGIS) for City of Omaha Parks (via ArcGIS Online org pDAi2YK0L0QxVJHj). | 7f7727403a75e310ef4687aaccee22d8e1295deb8440a627913c594d388794e3 | pending |
| D08-13 | camreg_oosgis_nl | Dutch camera registry (OOS GIS, CEVI schema) — a government portal source published by Dutch municipal camera registry (oosgis publisher). | 7f7d981f68b17ef0873b533602964a6330a3518ea51f38b532ea0affe5602162 | pending |
| D08-14 | camreg_osm_surveillance | OSM-derived surveillance-camera layers (DeFlock/OSM exports) — a government portal source published by OpenStreetMap contributors (republished man_made=surveillance nodes). | 80ddfbf362474c83019b6abda2c64de258489ae22c0705bb23e5b08bbee6adfb | pending |
| D08-15 | camreg_ottawa_on | Ottawa enforcement cameras (ArcGIS open-data registry) — a government portal source published by City of Ottawa. | 251eb3270f550c2d4bda4e48a4aa2ad65c9372d707a255e664417d1b58a11ef9 | pending |
| D08-16 | camreg_palmdesert_ca | Palm Desert license-plate-recognition camera locations (ArcGIS registry) — a government portal source published by City of Palm Desert, California. | 24fdb57f9bbe4086423159e0a61c6d3b69c54c8911af4bff7176e3e3a2317229 | pending |
| D08-17 | camreg_peel_on | Peel Region red-light cameras (ArcGIS registry) — a government portal source published by Regional Municipality of Peel. | cbe8c5bfa1ebb7f818351ac7cac8d08d7650b7a51c97cceca856a5565650f04c | pending |
| D08-18 | camreg_penndot_pa | PennDOT CCTV cameras (ArcGIS registry) — a government portal source published by Pennsylvania Department of Transportation (publisher account). | 18338a102e0b57733ca2feba33baec50ed3acea77933728e3a1a4a277aaeb5c5 | pending |
| D08-19 | camreg_peoria_il_drone_usage | Peoria Police Department Drone Usage — a government portal source published by City of Peoria, IL (via ArcGIS Online). | 82eca2ac54d8992303db4464069b2f2bcf8c4f58ef4ee1a94df1b5c372841c0d | pending |
| D08-20 | camreg_pgcounty_md | Prince George's County speed/red-light cameras (Socrata registry) — a government portal source published by Prince George's County, Maryland (PGPD). | f0b58bfbb7df0faa731368e74cb66d6dcdfde06c04419371d51bac5c76a17dd4 | pending |
| D08-21 | camreg_pipeline_sec | Traffic/security camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | ba98a184216ccc37bc6ee85615e95f07705f6e81776b1e8ec83fe03533ad248f | pending |
| D08-22 | camreg_plymouth_gb | Plymouth traffic cameras (ArcGIS registry) — a government portal source published by Plymouth City Council. | 5f78b6c795486156e094b874f386fbe18db7da40cc8cf47e166ea7e0de0cee36 | pending |
| D08-23 | camreg_polyu_hk | Hong Kong CCTV camera layers (esrichina.hk ArcGIS registry) — a government portal source published by Hong Kong PolyU/police CCTV layers (community-published). | e16d56d87deccd71778594ee71e50ab5b88ba993bbd9c220a51af575c8e06406 | pending |
| D08-24 | camreg_portland_or | Portland ITS cameras (portlandmaps ArcGIS registry) — a government portal source published by City of Portland, Oregon. | d472963a9277ee12a83e911d0f6c9469c937e36216b8ba9443f86d1359bf934e | pending |
| D08-25 | camreg_pt_11_lisboa_sistema_de | Sistema de Videovigilância Bairro Alto — a government portal source published by Município de Lisboa. | 27695a1ae0cfbb4dbc6478a3b978f4e0e60832f71e1da05fd327aafeb7d68359 | pending |

## Confirmation log

(none yet)
