# Description batch 10 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D10-01 | camreg_tacoma_wa_ate | Automated Enforcement Locations (Tacoma) — a government portal source published by City of Tacoma, Public Works (ArcGIS Online, owner IT.DataCurator). | be0ff3ff2ba790a93bf3f26d7d7fdc1042707c55b626f8a0feb93a29393ae4ad | pending |
| D10-02 | camreg_temecula_ca_flock_wfl1 | Flock_WFL1 (City of Temecula, CA) — a government portal source published by City of Temecula, CA (staff account, via ArcGIS Online). | e9dc378d160c228aca7ae567a51ea0031c73291279d930fbbd04e21546505345 | pending |
| D10-03 | camreg_thailand_th | Thailand CCTV camera layers (ArcGIS registry) — a government portal source published by Thai municipal/community camera registries. | 7a43419d29ee9878965968f483a8505035f7d9b15ecbb59288fdab50a762faf7 | pending |
| D10-04 | camreg_thomasville_ga_flock_location | FLOCK_Location (City of Thomasville, GA) — a government portal source published by City of Thomasville, GA (org name via ArcGIS portal self record). | 77c0b20066778c8288bb420b97fdcaf0d57e91f42a054356520d06ee84d5af63 | pending |
| D10-05 | camreg_toronto_on | Toronto camera locations (ArcGIS republish layer) — a government portal source published by City of Toronto (republished layer). | ac7ffa30c7f3af4478de714459fdaa4d049e0e8101ebfe74ebc128c064e2b460 | pending |
| D10-06 | camreg_townofws | ASE camera locations (Town of WS ArcGIS registry) — a government portal source published by ArcGIS community-published enforcement-camera registry. | 26f85f59a8f6b4b46d34d9f80ce39702acb1ffc8a314694063ef84b250fe3bca | pending |
| D10-07 | camreg_trafficops_ca | California highway CCTV cameras (TrafficOps.GIS ArcGIS registry) — a government portal source published by California traffic-operations publisher (Postmile schema). | 2262f844de883e1be5f50d54944e74dc328734c588975a1372c8c5b0be97b4e4 | pending |
| D10-08 | camreg_tribal_all_leaders_directory | Tribal Leaders Directory (BIA Branch of Geospatial Support, ArcGIS FeatureServer) — a government portal source published by Bureau of Indian Affairs, Branch of Geospatial Support (via ArcGIS Online). | 9ccd4d881cf0902dd2fb050a17997ac843e91505c812bb36798a086a4685b7bc | pending |
| D10-09 | camreg_trpa_us | Lake Tahoe SMART traffic cameras (TRPA ArcGIS registry) — a government portal source published by Tahoe Regional Planning Agency (bi-state compact). | 37695cceceb6e28592ce5a4e8ccfca0700ff5198f8130148d4e2bafc11e991ef | pending |
| D10-10 | camreg_tulane_la | New Orleans CCTV cameras (Tulane ArcGIS registry) — a government portal source published by Tulane University (republished municipal layer). | 83f2a63f16d9c429000fcdb9f4c99e244e3533c97acbb6dbb87d29717e4e40ab | pending |
| D10-11 | camreg_txdot_rep_tx | Texas DOT traffic cameras (ArcGIS republish layer) — a government portal source published by Texas Department of Transportation (republished layer). | b83b9c36c44dfdbaff4565876c0962ed32786a3a5b6146bf2eb9dd5560eb6471 | pending |
| D10-12 | camreg_ua_18_korosten | Дані про місцезнаходження камер відеоспостереження, що перебувають у комунальній власності Коростенської міської територ — a government portal source published by Korosten City Council. | cc1ffd5e2dbc491eab495d326c21d107da88bfe02ab6a57755553429ad3c5289 | pending |
| D10-13 | camreg_uchicago | Security camera registry (UChicago ArcGIS layer) — a government portal source published by University-community-published camera registry. | 000b6039552a4a48014f57f0a29d9618d9f178e5fb9eeb25b7d3c4ce45cda735 | pending |
| D10-14 | camreg_ucsd | Traffic camera registry (UCSD Online ArcGIS layers) — a government portal source published by University-community-published traffic-camera registry. | 3c8864ec757698737562451b0e2992a358682de42b5401407bad57484625403f | pending |
| D10-15 | camreg_ukm_my | UKM CCTV management system (ArcGIS registry) — a government portal source published by Universiti Kebangsaan Malaysia (community-published layer). | e221744adf983377f035bbd1d7145e506f20c7a1129599f310320f91b3e2a34d | pending |
| D10-16 | camreg_umbc_md | Maryland camera locations (UMBC ArcGIS registry) — a government portal source published by University of Maryland, Baltimore County (republished state layer). | 26e4db0553ecf5dc9aeb18559a424cc72cbb0bcf29bd9ced3aabff0120d4e04d | pending |
| D10-17 | camreg_und_001 | Traffic cameras (ArcGIS registry) — a government portal source published by ArcGIS community-published traffic-camera registry. | fc17aa43ecca162d263783d9e93a9e57685a5a83d3c09bd9e69158864388f1e2 | pending |
| D10-18 | camreg_und_002 | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D10-19 | camreg_und_003 | Public-safety cameras view (ArcGIS registry) — a government portal source published by ArcGIS community-published camera registry. | fe115df64eaba0359cee3a23fb57c120070a3567d90ffca6caa242306c7281f7 | pending |
| D10-20 | camreg_und_004 | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D10-21 | camreg_und_005 | Surveillance sites (ArcGIS registry) — a government portal source published by ArcGIS community-published surveillance-site registry. | 2a882ff2db4ea3dae7269f1cc7441577c40e9e63d927363776a3f7481e54f1fd | pending |
| D10-22 | camreg_und_006 | Flock ALPR locations (UA GIS ArcGIS registry) — a government portal source published by University-community-published ALPR camera registry. | 7ef11d429d63dae7ec09c2cfbfb21637720ca0009d6d9b7009c3a0d5c2d96f07 | pending |
| D10-23 | camreg_und_007 | CCTV_ camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 6bb63bfe62d77b0b47847ff302be27f2d913defbd852601bf7e832fa5cc52d8d | pending |
| D10-24 | camreg_und_008 | ITS CCTV camera layer (ArcGIS registry) — a government portal source published by ArcGIS community-published ITS camera registry. | 493e2e467e0511cfc23ea57356e591e767393f7b10682ed71137e3c5db849336 | pending |
| D10-25 | camreg_und_009 | CCTV cameras asset registry (3D-GIS ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV asset registry. | 77706d08c4dc9a0833bbf5f0622e5b51ddda643f6f1621e10aee0d2db4bb9cd9 | pending |

## Confirmation log

(none yet)
