# Description batch 04 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D04-01 | camreg_colgis | `Traffic cameras view (COLGIS ArcGIS registry)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | 08af96a6b0a2fc2993451b490f59766daf9e646a15925ce36f3dbe5809112ca4 | pending |
| D04-02 | camreg_cotgeo | `Geospatial traffic camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | 65c41e40023581b4eb135062bd026bb39b82a29a378d92e1580c789f0876704e | pending |
| D04-03 | camreg_ctdot_speed_safety | `Approximate Speed Safety Camera Locations Public (CTDOT Work Zone Speed Control pilot)` — a government portal source published by `Connecticut Department of Transportation (ArcGIS Online owner CTDOT_OpenData)`. | e2492a9d0e753650fa9a82f7dddb42c04579c4d05fd1b85dcf9a6a0c48020a99 | pending |
| D04-04 | camreg_cwarcgis | `Camera registry (cwarcgis ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 3ea574a53d8d8ca2ff61d0896a436623f597127f967c82f3ce7a2ff032f7e781 | pending |
| D04-05 | camreg_dc_ddot_ate | `DC Automated Safety Cameras (ASC) — locations layer + violations-by-month table (DDOT via DC GIS)` — a government portal source published by `District of Columbia, District Department of Transportation (via DC GIS / OCTO)`. | 281201ea34ecdd7371881055686d9be87ed12d48e3568a991ca8e4226b4ce5be | pending |
| D04-06 | camreg_dc_dot_dc | `Washington DC traffic-camera ArcGIS republish layers` — a government portal source published by `District of Columbia (DDOT camera registries, republished layers)`. | a8bce2e58483ddfd294101344a475570255017f7a78813ec536407ad5c4cf972 | pending |
| D04-07 | camreg_dc_ovsjg_camera_rebate | `DC Private Security Camera Rebate Program — per-PSA × month programme aggregates (OVSJG via DC GIS)` — a government portal source published by `District of Columbia Office of Victim Services and Justice Grants (DC GIS)`. | fea81c7555e4139c86f7fcfcc66b4862aa4335d408e6d1424d10c0facc895cc8 | pending |
| D04-08 | camreg_de_delaware_checkbook_expenditure | `Delaware Checkbook Expenditure Details (+ State of Delaware Checkbook, Statewide Central Contract Spend)` — a government portal source published by `State of Delaware, Department of Finance, Division of Accounting (via data.delaware.gov)`. | 7596e70e4437b68cb99f2a31ceb656bed2cc318155514ea35a4d080d4fad6da3 | pending |
| D04-09 | camreg_denver_co | `Denver automated license-plate-reader camera locations (ArcGIS registry)` — a government portal source published by `City and County of Denver, City and County of Denver (geospatialDENVER)`. | c6ed91b789dcece5b981897e8596f0443c2049f12fc3cb2d3ad7a9f000bc3833 | pending |
| D04-10 | camreg_detroit_mi_project_green_light | `Project Green Light Locations` — a government portal source published by `City of Detroit / Detroit Police Department (via ArcGIS Online org qvkbeam7Wirps6zC, data.detroitmi.gov)`. | 54110f1ea9009c48e5ec2a6d892fb995d0e987b97d6fa9d3f1a584afc4973bea | pending |
| D04-11 | camreg_donegal_ie | `Donegal traffic cameras (ArcGIS registry)` — a government portal source published by `Donegal County Council / TII`. | 8671c56ad64aacbb26f474ac6541006bec79f67d818d55f8ffa6491bc5e0e2f2 | pending |
| D04-12 | camreg_dover_gb | `Dover CCTV cameras (ArcGIS registry)` — a government portal source published by `Dover District Council`. | 407aee36e6b8a38f89e9b25ec25b1d3ae72283e11ee865e9c0af54899b25ca70 | pending |
| D04-13 | camreg_dubuque_ia | `Dubuque public camera locations (ArcGIS registry)` — a government portal source published by `City of Dubuque, Iowa`. | e99e295e363898f6d95c0ae4eab3e9e7f4d5bcf734d576ab227949d1d4dade5e | pending |
| D04-14 | camreg_durham_gb | `Durham County traffic web cameras (ArcGIS registry)` — a government portal source published by `Durham County Council`. | 1413e57b9e020198824c94e4d505e0839e13244e117bcee8934be1a0f9f8ba33 | pending |
| D04-15 | camreg_eastdun_gb | `East Dunbartonshire CCTV cameras (ArcGIS registry)` — a government portal source published by `East Dunbartonshire Council`. | 345f6c934d15e205dd2002c3c684c3df1fb186ec38caa723478ac87443bb50c3 | pending |
| D04-16 | camreg_ebrgis_la | `East Baton Rouge traffic cameras (EBRGIS ArcGIS registry)` — a government portal source published by `City of Baton Rouge / East Baton Rouge Parish`. | 1b8207756eb1d89af22caa132413fa696a110a57ffd8609dc1fff67b97c6af46 | pending |
| D04-17 | camreg_edmonton_ab | `Edmonton intersection safety device locations (Socrata registry)` — a government portal source published by `City of Edmonton`. | 8352e41b27725a45e96cdd28422d598cdcc7febd3bfcfb1327e04a478b971f0d | pending |
| D04-18 | camreg_elgin_il_lpr_cameras | `LPR Cameras (City of Elgin, IL)` — a government portal source published by `City of Elgin, IL (via ArcGIS Online)`. | 289fcad902a56edebee8c559b43aa9b72c048009bfa997106867bc4a64cf343b | pending |
| D04-19 | camreg_es_md_madrid_c_maras_de | `Cámaras de videovigilancia en la vía pública de Madrid` — a government portal source published by `Ayuntamiento de Madrid (Policía Municipal)`. | 1be7a083229832684dcab0d4958d90e93018edea0c25490966964e2a7676e90f | pending |
| D04-20 | camreg_esri_dash | `Traffic cameras (Esri dashboard-publisher ArcGIS layer)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | d4cc8f83c7233c63eb8c024fe44d76c75b19c4509869655c311e9f01d9c293d0 | pending |
| D04-21 | camreg_esriukpolice_gb | `UK police CCTV locations (Esri UK police ArcGIS registry)` — a government portal source published by `Esri UK police demonstration org (community-published layer)`. | 9322f26b5fc159745e26f56c8dc3010cfaddf21eae191240c4f000362e41c706 | pending |
| D04-22 | camreg_essex_gb | `Essex safety cameras public view (ArcGIS registry)` — a government portal source published by `Essex County Council / Essex Safety Camera Partnership`. | f5eb14f32b46ec0d7bcc0667da9f17f4ab51453ea625661b12ebda86b9fc0137 | pending |
| D04-23 | camreg_eu_eea_data_europa_search_api | `data.europa.eu search API — multilingual CCTV/video-surveillance datasets (148 hits)` — a government portal source published by `Publications Office of the EU (data.europa.eu, harvests national portals)`. | bb9011053e0d27a1131c386edc8f02f89df754bce5f7c5eeae97f51fb7ada3dd | pending |
| D04-24 | camreg_fdot_flock | `FDOT District 3 Flock camera inventory + FLOCK removal status layers` — a government portal source published by `Florida Department of Transportation, District 3 (via ArcGIS Online)`. | 94c11c7187a4076f1436bdacd1e0733aef9d9d286d8dbe6d8feaf7a50a0a59ff | pending |
| D04-25 | camreg_firemedic | `Traffic camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | 92be47774759587fa9ebb6aeeac5d61d8a66f8bae96967083b6a8e0e659e3a64 | pending |

## Confirmation log

(none yet)
