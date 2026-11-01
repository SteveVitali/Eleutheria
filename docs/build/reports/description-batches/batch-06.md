# Description batch 06 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D06-01 | camreg_glasgow_gb | Glasgow CCTV cameras (ArcGIS registry) — a government portal source published by Glasgow City Council. | 35d10bd1e9daa0ad7cab85bce92c3003e7c568fc9c1a3cdbe15389e3d0ca7a1d | pending |
| D06-02 | camreg_gmh_emc_ga | Georgia EMC CCTV cameras (ArcGIS registry) — a government portal source published by Georgia EMC (GMH_GA_emc publisher). | c894831fed892e6fa02d9bbe8c9bbf41d757d05ac7233abc4a49e4bfed25aed5 | pending |
| D06-03 | camreg_goldcoast_au | City of Gold Coast Safety Camera Network (ArcGIS registry) — a government portal source published by City of Gold Coast (Safety Camera Network). | 87de65dad4d259856f726aacd1ca41c1063e0557ecbcc3878403ef2e135224ce | pending |
| D06-04 | camreg_guildford_gb | Guildford CCTV cameras (ArcGIS registry) — a government portal source published by Guildford (rgsguildford publisher). | 1023e8db203ce6136ea3d472505185ef5bc5d239afbc44ba5a6247b20a044018 | pending |
| D06-05 | camreg_hk_hk | Hong Kong CCTV camera locations (ArcGIS registry) — a government portal source published by Hong Kong Transport Department. | 752e530c2afd9c1ff0b28d7f46b31eab6d4a9aa7aaee372844589c549853d08f | pending |
| D06-06 | camreg_honolulu_hi | Honolulu traffic camera locations (Socrata registry) — a government portal source published by City and County of Honolulu. | 5c9d853681a3d9268c6e0803df064016dfd078bf1468d96cba92112094feba5c | pending |
| D06-07 | camreg_howard_md_school_zone_ate | SchZoneHighligh — Howard County school zones where automated enforcement is applied (zone polygons) — a government portal source published by Howard County, MD (Socrata). | 25d82f2a00c2db7a929984d9ed7214b93a1677e631dd5d3cd108b0ef8f13e160 | pending |
| D06-08 | camreg_hyattsville_md_cctv_camera_2024 | Hyattsville CCTV Camera Program 2024 — a government portal source published by City of Hyattsville, MD (cohgis). | 29df378d93b6beb24cad7cc6327fe9dbb1423a3395420a3eb2d79a1f135e0e87 | pending |
| D06-09 | camreg_ie_d_dublin_traffic_poles_with | Traffic Poles with CCTV DCC — a government portal source published by Dublin City Council (via data.gov.ie / Smart Dublin). | da29de19934d43d195c33260a6e08fc99aca215e24572cdd8985f9b67c3ae783 | pending |
| D06-10 | camreg_il_chicago_violence_reduction | Violence Reduction - Shotspotter Alerts - Historical — a government portal source published by City of Chicago, Chicago Police Department (Socrata). | fa3a0420bd898767dd65491199871191f3d884e4e92efca721627542e950f5d2 | pending |
| D06-11 | camreg_indonesia_id | Indonesia CCTV camera layers (ArcGIS registry) — a government portal source published by Indonesian community/municipal camera registries. | 310fa5259160e87b458c6c4ca4dc648ef527df0b6dc9a3b2ea71a9b6d61d7584 | pending |
| D06-12 | camreg_infocemosa | CCTV point registry (Infocemosa ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | d9e33fafe4a3d60ddd413b7663d81ff0dfd16cf87795b094df5b147faaa84e34 | pending |
| D06-13 | camreg_infraestructura | CCTV proyectado registry (ArcGIS, Spanish schema) — a government portal source published by ArcGIS community-published CCTV registry. | 3c9ea9e1354117df9fa1194749f113e8d8b4bfa366064eda9f41863694d59590 | pending |
| D06-14 | camreg_ira | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D06-15 | camreg_it_me_messina_videosorveglianza | Videosorveglianza urbana — a government portal source published by Comune di Messina. | 03746123a4b4b5708c601e5a89a40688da69780b0f8a141471d594ffd4b1681b | pending |
| D06-16 | camreg_jcfd3_or | Jackson County OR RoxyAnn camera (ArcGIS registry) — a government portal source published by Jackson County Fire District 3, Oregon. | ce6a125eb501f52e377ee606fdd764db2538b5d9d98fcf895cecfc1d91ec6b34 | pending |
| D06-17 | camreg_jeffersonville_in_flock | flock (City of Jeffersonville, IN) — a government portal source published by City of Jeffersonville, IN (staff account, via ArcGIS Online). | 5c783ce7edc9503afc55fdd0ad7f643c44b9c2e89a8dda8b2134bf2fe7666642 | pending |
| D06-18 | camreg_jmh_us | MPD Flock camera locations (ArcGIS registry) — a government portal source published by US municipal police department (jmh_com publisher). | b9134395ec1999eafc962b2eda6623cdbae1ad9d10ef6e08b05a66a9c271b581 | pending |
| D06-19 | camreg_kcmo_mo | Kansas City traffic camera locations (ArcGIS registry) — a government portal source published by Kansas City, Missouri. | 73cc28cff8d864e8a10e4e3f19c502b51ed5c7cb18501cc95f87190be34114b3 | pending |
| D06-20 | camreg_keizer_or | Keizer traffic and graffiti cameras (ArcGIS registry) — a government portal source published by City of Keizer, Oregon. | abcdd861b1f8617e87579796407ae33a83fee8e83bbaf296b08c0476c574dc5b | pending |
| D06-21 | camreg_kirkland_wa | Kirkland traffic cameras (ArcGIS registry) — a government portal source published by City of Kirkland, Washington. | 405ba9a7c1dc9c8f248d3a76939d2f937489889830e42298036d62bf0d2bacc5 | pending |
| D06-22 | camreg_la_east_baton_rouge_parish_flock | Flock_Location_Data view (East Baton Rouge Sheriff's Office) — a government portal source published by East Baton Rouge Parish Sheriff's Office, LA (staff account on the ebrso.org domain, via ArcGIS Online). | 3b1075cacc75241fc3bd6d348b9a5976e3e2b1f223a3df476b11f7b84ca0f911 | pending |
| D06-23 | camreg_la_new_orleans_eye_on | Eye on Surveillance - New Orleans surveillance map (cameras, ALPR, Project NOLA) — a government portal source published by Eye on Surveillance (New Orleans NGO); production map.eyeonsurveillance.org. | 2803f8896bf1f61b45365e2176917e4b4b2ad8ab76f32a7be27225567f24d026 | pending |
| D06-24 | camreg_lakeland_fl_red_light | Red Light Cameras and Direction (City of Lakeland, FL) — a government portal source published by City of Lakeland, FL (via ArcGIS Online). | 3a119c1aae5401f5a0cabda89812d90986b412aeb0e7cc7da9845abe6cbfd43c | pending |
| D06-25 | camreg_lambeth_gb | Lambeth parking CCTV cameras (ArcGIS registry) — a government portal source published by London Borough of Lambeth. | 6c55e71c76f4a1423beda6f3bc5b70d25160c372b0db3bc5aa2092b9eeb227cb | pending |

## Confirmation log

(none yet)
