# Description batch 03 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D03-01 | camreg_au_vic_geelong_closed_circuit | `Closed Circuit Television (CCTV) Location` — a government portal source published by `City of Greater Geelong`. | 2d47eca2226abe103573eede8025aa440df55b91efd2d288968ceca50c4f5a43 | pending |
| D03-02 | camreg_au_wa_perth_security_cameras | `Security Cameras` — a government portal source published by `City of Perth`. | 3d7fddeb5774b937339285c2921764ea1a83670fafcd4c6a739990d994099aba | pending |
| D03-03 | camreg_austin_tx | `Austin traffic cameras (Socrata open-data registry)` — a government portal source published by `City of Austin Transportation and Public Works`. | 40e1719b1c1db81a27af8e301cf15a797f9cfe07ad4be6b17df856862acea9cf | pending |
| D03-04 | camreg_avctransport | `Surveillance 2026 registry (avctransport ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | dd1bfeaf47cc5f3cc912c85f644ecefc20222015bc6260645138c52090a292b9 | pending |
| D03-05 | camreg_az_mesa_city_of_expenditures | `City of Mesa AZ - City Expenditures: payments to Flock Safety (Police)` — a government portal source published by `City of Mesa, AZ (Socrata)`. | bffc0674c0660d4a81b736702c5cbd09ef923a0ffa991b6150b441a4236de7c0 | pending |
| D03-06 | camreg_azdot_az | `Arizona DOT CCTV cameras (ArcGIS registry)` — a government portal source published by `Arizona Department of Transportation (ADOT publisher account)`. | 662f7ffe28415cabc270d362d18c9327dfb254b502ae9b11fa70d62f9583d5c4 | pending |
| D03-07 | camreg_baltimore_atves_md | `Baltimore ATVES speed/red-light cameras (ArcGIS registry)` — a government portal source published by `City of Baltimore (baltimore_city ArcGIS org)`. | 572b4202281c4f70a60ec5d3826e0acf9da269eece6e6dde0ea87012587a9148 | pending |
| D03-08 | camreg_baltimore_md | `Baltimore CitiWatch cameras (ArcGIS registry)` — a government portal source published by `Baltimore City (CitiWatch)`. | 052a1731a3a6b17b818e9457a9f580674fe15b18fdd7b1e0c51bb0f7522e9a4e | pending |
| D03-09 | camreg_bangla_bd | `Bangladesh camera locations (ArcGIS registry)` — a government portal source published by `Bangladesh community-published camera registry`. | 786609052851c6f6451192dd6c8d31edefaa0a72d192b45a9c78085451513a11 | pending |
| D03-10 | camreg_batonrouge_la | `Baton Rouge traffic cameras (Socrata open-data registry)` — a government portal source published by `City of Baton Rouge / East Baton Rouge Parish`. | f83c915830362b6fb752bab94f3fce29e5192ddcf081d7ed3ca56eddedf6cdbc | pending |
| D03-11 | camreg_bedford_gb | `Bedford external CCTV cameras (ArcGIS registry)` — a government portal source published by `Bedford Borough Council`. | 576c1553f54073d5a79a049fcddcbbbeb975cc3225e9d2259a98e5154120714f | pending |
| D03-12 | camreg_bellevue_wa | `Bellevue traffic cameras (ArcGIS registry)` — a government portal source published by `City of Bellevue Transportation Department, City of Bellevue, WA (ArcGIS Online, owner <staff account id redacted>)`. | 58981a11a434897e16964569cd54d6241046fb2b561ef4a66c208de675143365 | pending |
| D03-13 | camreg_bettendorf_ia | `Bettendorf traffic control / stop-light cameras (ArcGIS registry)` — a government portal source published by `City of Bettendorf, Iowa`. | 42b71836c957ddb301b7c5dd50710017b6f0bf2a57297de1162112cd337ee3db | pending |
| D03-14 | camreg_bloomington_il_drone_flights | `Police Drone Flights` — a government portal source published by `City of Bloomington, IL (via ArcGIS Online)`. | 79dee24171e961b7fbc3016481ce126b6e3567cd8cfefeba76f7b5951b5cd014 | pending |
| D03-15 | camreg_bouhan_jp | `Japanese bouhan (security) camera locations (ArcGIS registry)` — a government portal source published by `Japanese community-published camera registry`. | 7843789f170adf6062a6d441c088658797d7b90d4f9aa4e58f766373659c5b2f | pending |
| D03-16 | camreg_brea_ca | `Brea PD camera locations and inventory (ArcGIS registry)` — a government portal source published by `City of Brea, California`. | a9f090915cb33863548c4439e8bdeaba673b335936fc02ddb2456bed92591aa0 | pending |
| D03-17 | camreg_ca_monterey_park_flock_camera | `Flock camera locations / Flock Camera Map (Monterey Park, CA staff accounts)` — a government portal source published by `City of Monterey Park, CA (two city-staff accounts, org name not set)`. | f46b45d6810ad9a2dccf05e661e09c81c3aaa77927983b1fb387eeb5b013bc10 | pending |
| D03-18 | camreg_caledon_on | `Caledon CCTV locations (ArcGIS registry)` — a government portal source published by `Town of Caledon, Ontario`. | 25315e3bbf2213ea52a1de89889080fd4578a307199cb0a8c3695e61e007efdb | pending |
| D03-19 | camreg_calgary_ab | `Calgary traffic + intersection safety cameras (Socrata registry)` — a government portal source published by `City of Calgary`. | 9757b1b02745cb36c47c735796142deef1f957f3cd2f6b60ad875fee41c99d1a | pending |
| D03-20 | camreg_caloes_ca | `CalOES California webcams (ArcGIS registry)` — a government portal source published by `California Governor's Office of Emergency Services`. | 20e148313f97d551fb5fc1f2352f967a7c3cdef28c6c6a2a0804bd516e7917df | pending |
| D03-21 | camreg_camberwell_au | `Camberwell-area CCTV cameras (ArcGIS registry)` — a government portal source published by `Camberwell Grammar School GIS org (community-published layer)`. | 2b6169c0d7f02a37d13e1e54e6820ab2c9764c36dbfe5bf45165db11c046c21b | pending |
| D03-22 | camreg_camilo_schools | `CCTV locations (GIS-for-schools ArcGIS registry)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 6ecf3a7fee516d512d443abec60bc51124cf4693d3c875ca536a625973281a08 | pending |
| D03-23 | camreg_carver_mn | `Carver County traffic cameras (ArcGIS registry)` — a government portal source published by `Carver County, Minnesota`. | d89848998df8a7531a32e1ecb5357ce414069863b0a8445e4be78eccb5d192f6 | pending |
| D03-24 | camreg_chattanooga_tn | `Chattanooga public-safety cameras (CHATTGIS ArcGIS registry)` — a government portal source published by `Chattanooga-area GIS publisher (CHATTGIS)`. | bf0205e15d71493458e55088a9ca8fd9084d2822abd3f2ab06efb0116f28937b | pending |
| D03-25 | camreg_chicago_il | `Chicago speed + red-light cameras (Socrata open-data registry)` — a government portal source published by `City of Chicago Department of Transportation`. | 4d06f831474021077a57a6739afb83f53ff624fb80ea43d1df57b04d00edf224 | pending |

## Confirmation log

(none yet)
