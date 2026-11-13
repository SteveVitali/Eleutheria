# Description batch 05 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D05-01 | camreg_firemedic | `Traffic camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | 92be47774759587fa9ebb6aeeac5d61d8a66f8bae96967083b6a8e0e659e3a64 | pending |
| D05-02 | camreg_fl511_fl | `FL511/FDOT traffic cameras (ArcGIS republish layers)` — a government portal source published by `Florida Department of Transportation (republished layers)`. | c94024bed0f3ed6af778a8417a8d7f8a08837b23bb3ad2a8fcd9664feb0a1922 | pending |
| D05-03 | camreg_fl_broward_county_us_palm_beach | `D4 - Camera Survey (FDOT District 4 ROW camera inventory form)` — a government portal source published by `Florida Department of Transportation, District 4 (via ArcGIS Online)`. | f86b71a0909e767735568cc5d8064a787ced3d644576c41fd32e215cff38b058 | pending |
| D05-04 | camreg_forwardalliance | `CCTV camera registry (forwardalliance ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | c46b8c2cf7e7cda271bc54761e41890033b11830f6fddfc1bb9e23ab48a1b6cc | pending |
| D05-05 | camreg_fr_92_grand_paris_seine_ouest_vid | `Vidéoprotection` — a government portal source published by `Grand Paris Seine Ouest (établissement public territorial)`. | 3eca40c116ac463f92d059caae950ee47fd50d336c3b5894622873229a64e2b0 | pending |
| D05-06 | camreg_friendswood_tx | `Friendswood Flock Safety ALPR camera locations (ArcGIS registry)` — a government portal source published by `City of Friendswood, Texas`. | 2495d8c75d26d792d6579a9641131e11356886c2fdcb3f60fe824160311e0a20 | pending |
| D05-07 | camreg_ga_brookhaven_flock_camera | `Flock_Camera_Locations_Sep_2023 (City of Brookhaven, GA)` — a government portal source published by `City of Brookhaven, GA (via ArcGIS Online)`. | 23bc6c19620e62b22d4c023a079a79b696051c6db2bed0ecf01a5c3c583ba89e | pending |
| D05-08 | camreg_ga_flock_cameras_asof | `FLOCK_CAMERAS_ASOF_20240318 (CCSO, west Georgia, org unresolved)` — a government portal source published by `"CCSO" county sheriff's office (org name private, extent in west Georgia) (via ArcGIS Online)`. | 59a1c8f72ae625acb2960d467c37f591889e4f5d994f5bf44db781c2fce69c49 | pending |
| D05-09 | camreg_ga_peachtree_corners_flock_camera | `Flock_Camera_Location (City of Peachtree Corners, GA)` — a government portal source published by `City of Peachtree Corners, GA (via ArcGIS Online)`. | f8d47627173a1c2175228836282e7ef4cfaabe1b8ad60d42e037e373afafe545 | pending |
| D05-10 | camreg_ga_savannah_flock_camera | `Flock_Camera_Locations2 (Savannah Police Department)` — a government portal source published by `Savannah Police Department, GA (via ArcGIS Online)`. | 500169a5a7de79c5b2fefa6e70cf20dc54e2f6eb794012ef10971ef2b41aaa25 | pending |
| D05-11 | camreg_gainesville_fl | `Gainesville traffic cameras (ArcGIS registry)` — a government portal source published by `City of Gainesville, Florida`. | 39972d73b2918cd212931ee6aa63a3f4b7f9aa12a6151b518921b75a96aefa15 | pending |
| D05-12 | camreg_gastonia_nc_flock_condor_cameras | `City of Gastonia NC Flock layers: Condor Cameras, LPR, Flock OS integration layers` — a government portal source published by `City of Gastonia, NC (via ArcGIS Online)`. | cd2842321341c78464ab6bbecc157942da4a1a50360bcc7e962f9c3390145ba7 | pending |
| D05-13 | camreg_gb_eng_barnet_cctv_camera | `CCTV camera locations` — a government portal source published by `London Borough of Barnet`. | db470d0827a4b8fb91849ff85ac8d4b91a1aa1c6b4dfed176290f05c6c467547 | pending |
| D05-14 | camreg_gb_eng_barnet_cctv_traffic | `CCTV Traffic Enforcement - camera locations` — a government portal source published by `London Borough of Barnet`. | c200e07868a581c2478e315108e23032004a8e6cde9b5d0f1c7ad36e06af75bf | pending |
| D05-15 | camreg_gb_eng_brist_cctv_cameras | `Council CCTV cameras` — a government portal source published by `Bristol City Council`. | 4f5bcfa4d7f630546801c2aad11c7f513a1fd837ac7c8d2d238f8c011c25ee52 | pending |
| D05-16 | camreg_gb_eng_ipswich_cctv_camera | `CCTV Camera Locations in Ipswich` — a government portal source published by `Ipswich Borough Council`. | 8be5e6c33719b066db0a0057e4588d5be3baeaef6641fb0b398849f15182696e | pending |
| D05-17 | camreg_gb_eng_leice_cctv_cameras | `CCTV Cameras` — a government portal source published by `Leicester City Council`. | 72a2bb2388ba71b5eebae9e2be586b1471a07d92d1c898185cbf16db404f9e8b | pending |
| D05-18 | camreg_gb_eng_mansf_cctv_cameras | `CCTV Cameras` — a government portal source published by `Mansfield District Council`. | 41be1a707c4aa673ce7803076949189a746edf9be587c806559d51d68a60d2dc | pending |
| D05-19 | camreg_gb_eng_north_cctv_cameras | `CCTV cameras` — a government portal source published by `North Somerset Council`. | e9a3910724e2675df41f0fa9835ce8a10809611c9fd3af580c1f78cccabf819d | pending |
| D05-20 | camreg_gb_eng_runny_cctv_cameras | `CCTV Cameras` — a government portal source published by `Runnymede Borough Council`. | 5ef2c40f74237fb36864616c5ffb8cfda0d80dcabd0c0781891f01d89d77513e | pending |
| D05-21 | camreg_gb_eng_south_skdc_cctv | `SKDC CCTV` — a government portal source published by `South Kesteven District Council`. | 99edefb53035f56b750e773b4879962c1511acfbe60f106e6d3de1b1540531d4 | pending |
| D05-22 | camreg_gb_eng_traff_trafford_cctv | `Trafford Council - CCTV` — a government portal source published by `Trafford Council`. | 725a450c35b991b9180f7af153a484a90a22b6f4ea464be381cde05a6c574532 | pending |
| D05-23 | camreg_gb_sct_clackmannanshire_cctv | `Clackmannanshire - CCTV Cameras` — a government portal source published by `Clackmannanshire Council (via SpatialData.gov.scot)`. | 20d0363edfc2d2eb16700f30ee8e99ea6d1de0b2a28ae479b9eb63a7ebc388fe | pending |
| D05-24 | camreg_gb_sct_edinburgh_public_cctv | `Public CCTV locations - City of Edinburgh` — a government portal source published by `City of Edinburgh Council (via SpatialData.gov.scot)`. | a90114c16463269450d0df351d598b6d6da965e5e45b7dd54103343580699a47 | pending |
| D05-25 | camreg_gedling_gb | `Gedling CCTV locations (ArcGIS registry)` — a government portal source published by `Gedling Borough Council`. | 3ff2ab8b26abb217ca1cf3463ce4c9d2f32e2782871d7d434664c43d6a396230 | pending |

## Confirmation log

(none yet)
