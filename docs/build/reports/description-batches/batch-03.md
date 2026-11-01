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
| D03-01 | camreg_au_vic_geelong_closed_circuit | Closed Circuit Television (CCTV) Location — a government portal source published by City of Greater Geelong. | caa9677b65934c33eab665e5c0b290878af7439171bb2ee5cbb4a3b8c8695c81 | pending |
| D03-02 | camreg_au_wa_perth_security_cameras | Security Cameras — a government portal source published by City of Perth. | 8c26a4ae677920fc6c6fbb71110db3f7cc3e8d09341cd7a26d4c59c9d28e732b | pending |
| D03-03 | camreg_austin_tx | Austin traffic cameras (Socrata open-data registry) — a government portal source published by City of Austin Transportation and Public Works. | 2a9d89dd6cc5f5cde73e2352c802be75dc16d754fc8f0fc1c45fdb742e66b28e | pending |
| D03-04 | camreg_avctransport | Surveillance 2026 registry (avctransport ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 83a2deeb0be1de32caa809882a8e5a7219cc9596ceb64e8570277f4a4bf75352 | pending |
| D03-05 | camreg_az_mesa_city_of_expenditures | City of Mesa AZ - City Expenditures: payments to Flock Safety (Police) — a government portal source published by City of Mesa, AZ (Socrata). | ebf1e4e4b4a8c950c1876c679d11a84415202e8fc01ce60a455e9ffeef26e5c3 | pending |
| D03-06 | camreg_azdot_az | Arizona DOT CCTV cameras (ArcGIS registry) — a government portal source published by Arizona Department of Transportation (ADOT publisher account). | 839b24659f35d6565d6a8489d30ee988b074137cff0336510f89a8c2a6e69211 | pending |
| D03-07 | camreg_baltimore_atves_md | Baltimore ATVES speed/red-light cameras (ArcGIS registry) — a government portal source published by City of Baltimore (baltimore_city ArcGIS org). | 58b671160bbb88032b337fa7c5979bf69aee0d4686b75e2da6a223dec7b669bc | pending |
| D03-08 | camreg_baltimore_md | Baltimore CitiWatch cameras (ArcGIS registry) — a government portal source published by Baltimore City (CitiWatch). | f64f7d7bbc840ed1a1622df7129d84833b6672de6c35a3305761cc7269f9996b | pending |
| D03-09 | camreg_bangla_bd | Bangladesh camera locations (ArcGIS registry) — a government portal source published by Bangladesh community-published camera registry. | 468c1c876aa928e87dfdeb2a37e0d6b1e3f21216b83dc7769a79fa1efab54d9a | pending |
| D03-10 | camreg_batonrouge_la | Baton Rouge traffic cameras (Socrata open-data registry) — a government portal source published by City of Baton Rouge / East Baton Rouge Parish. | 52d148bc88db231d947f7c35a8d57499cdbb38f10e8c0b1563a4ee9c35715bca | pending |
| D03-11 | camreg_bedford_gb | Bedford external CCTV cameras (ArcGIS registry) — a government portal source published by Bedford Borough Council. | 3c7d749ecb46d255bda40f9c02ac8cd7835efcbf0bfba31df95d8645cb8f096d | pending |
| D03-12 | camreg_bellevue_wa | Bellevue traffic cameras (ArcGIS registry) — a government portal source published by City of Bellevue Transportation Department; City of Bellevue, WA (ArcGIS Online, owner <staff account id redacted>). | 8ffeb0283b9b12958a5086931c47b29b6048b323e326522949b430ffe0024db5 | pending |
| D03-13 | camreg_bettendorf_ia | Bettendorf traffic control / stop-light cameras (ArcGIS registry) — a government portal source published by City of Bettendorf, Iowa. | 7a44fc851083d9603813247ab2333e914cfa6f6898b9652e9cc98210f83678c5 | pending |
| D03-14 | camreg_bloomington_il_drone_flights | Police Drone Flights — a government portal source published by City of Bloomington, IL (via ArcGIS Online). | 6a3ae86d6c7b6fac6fcadeeeadbcc498934d3bccae25c5d94871a9bfcea8f48e | pending |
| D03-15 | camreg_bouhan_jp | Japanese bouhan (security) camera locations (ArcGIS registry) — a government portal source published by Japanese community-published camera registry. | 842a62264da53a974d509a6a3bedddba910dfc114ff1ac6e3762934c9fb7155f | pending |
| D03-16 | camreg_brea_ca | Brea PD camera locations and inventory (ArcGIS registry) — a government portal source published by City of Brea, California. | 1f32296e0f2ae77dc5649dd4612a8a4208b88c27ea555d9ea2ffa479aea9c714 | pending |
| D03-17 | camreg_ca_monterey_park_flock_camera | Flock camera locations / Flock Camera Map (Monterey Park, CA staff accounts) — a government portal source published by City of Monterey Park, CA (two city-staff accounts; org name not set). | 31826222b8baeaca2e92bac9d402d5ac8984c02c37d94bc275d15038049c0957 | pending |
| D03-18 | camreg_caledon_on | Caledon CCTV locations (ArcGIS registry) — a government portal source published by Town of Caledon, Ontario. | 99ed82802a85d93241949032bfb6f57c361e90a86007f2f01326f918aed48d17 | pending |
| D03-19 | camreg_calgary_ab | Calgary traffic + intersection safety cameras (Socrata registry) — a government portal source published by City of Calgary. | f0d1452eb6a1001f4f4f51964d2f34b86ea0aef582b6ae3dacea187f7c998040 | pending |
| D03-20 | camreg_caloes_ca | CalOES California webcams (ArcGIS registry) — a government portal source published by California Governor's Office of Emergency Services. | 1b0bfe3eb7327a95fe491c1923e3d7116db34685cdf998c7871e06a843feb89e | pending |
| D03-21 | camreg_camberwell_au | Camberwell-area CCTV cameras (ArcGIS registry) — a government portal source published by Camberwell Grammar School GIS org (community-published layer). | 501c8719e0b35eaf9d688d3ba934cb28e57cfeb06c65b795f62d4f387e6023d5 | pending |
| D03-22 | camreg_camilo_schools | CCTV locations (GIS-for-schools ArcGIS registry) — a government portal source published by ArcGIS community-published CCTV registry. | 052880e38e15843e1b7e62b86a01229503aad605647f6fdbf9e963e63ba041a5 | pending |
| D03-23 | camreg_carver_mn | Carver County traffic cameras (ArcGIS registry) — a government portal source published by Carver County, Minnesota. | f3ea50bbbe2334f1eddae551e1b23f6f1242105fb2db4636aefd4bf29ddc809f | pending |
| D03-24 | camreg_chattanooga_tn | Chattanooga public-safety cameras (CHATTGIS ArcGIS registry) — a government portal source published by Chattanooga-area GIS publisher (CHATTGIS). | dba699f28460291bc4b44b7a03472eb970b8f450e3bead2c01da04fd7de008fd | pending |
| D03-25 | camreg_chicago_il | Chicago speed + red-light cameras (Socrata open-data registry) — a government portal source published by City of Chicago Department of Transportation. | f4f2941ca20aef25c7bbd6322810fd109c7cbe785754bd5444270cb42428af25 | pending |

## Confirmation log

(none yet)
