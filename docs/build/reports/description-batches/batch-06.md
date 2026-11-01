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
| D06-01 | camreg_glasgow_gb | `Glasgow CCTV cameras (ArcGIS registry)` — a government portal source published by `Glasgow City Council`. | 20070ec8f557aca5938f134efda20d6e76fce8d43213f1d831d089cad5329262 | pending |
| D06-02 | camreg_gmh_emc_ga | `Georgia EMC CCTV cameras (ArcGIS registry)` — a government portal source published by `Georgia EMC (GMH_GA_emc publisher)`. | f237d39c67073967d21e0cae190360e525f1b87d1adeb11a2d7d79abbf78743c | pending |
| D06-03 | camreg_goldcoast_au | `City of Gold Coast Safety Camera Network (ArcGIS registry)` — a government portal source published by `City of Gold Coast (Safety Camera Network)`. | 94e7bde4b56f9542bdc77265964b3a9535fd5dbf199677e21982f815d68fc4dd | pending |
| D06-04 | camreg_guildford_gb | `Guildford CCTV cameras (ArcGIS registry)` — a government portal source published by `Guildford (rgsguildford publisher)`. | 5b4d9b0ef587522e29c05e5b78acfc3567a6b8fd8ce53dffe40aea0b08b87959 | pending |
| D06-05 | camreg_hk_hk | `Hong Kong CCTV camera locations (ArcGIS registry)` — a government portal source published by `Hong Kong Transport Department`. | 47c71345667e81893dc506315607fbf1729e4602655caa092c11884a89cfefe5 | pending |
| D06-06 | camreg_honolulu_hi | `Honolulu traffic camera locations (Socrata registry)` — a government portal source published by `City and County of Honolulu`. | 8a475db62117f65f48b34c2513a82a6fcfc07e5ff30c7e8d97fe0659b2a2aec8 | pending |
| D06-07 | camreg_howard_md_school_zone_ate | `SchZoneHighligh — Howard County school zones where automated enforcement is applied (zone polygons)` — a government portal source published by `Howard County, MD (Socrata)`. | 92bbfe16f6fe953dbc1c6ed6119ce82c9eb7eec7366c6e55f6f24e19bda6fb1e | pending |
| D06-08 | camreg_hyattsville_md_cctv_camera_2024 | `Hyattsville CCTV Camera Program 2024` — a government portal source published by `City of Hyattsville, MD (cohgis)`. | f560bf8c10e0fcbbe7a563d71bb6793f6ab27d25c681955bf332849247465e30 | pending |
| D06-09 | camreg_ie_d_dublin_traffic_poles_with | `Traffic Poles with CCTV DCC` — a government portal source published by `Dublin City Council (via data.gov.ie / Smart Dublin)`. | a7066a95bb14956f2170d9bbe5d58736c9fd4605dc591a0d39dd434e369ed980 | pending |
| D06-10 | camreg_il_chicago_violence_reduction | `Violence Reduction - Shotspotter Alerts - Historical` — a government portal source published by `City of Chicago, Chicago Police Department (Socrata)`. | d01aa0a52ab30a9e33788ecf46a146f0bc891ed124e0ab5fe8ce44eff0ea15aa | pending |
| D06-11 | camreg_indonesia_id | `Indonesia CCTV camera layers (ArcGIS registry)` — a government portal source published by `Indonesian community/municipal camera registries`. | f60a5e241608a80eaf73dbeb6ec3c760fce2de7b4cb9926b392c4823315ca203 | pending |
| D06-12 | camreg_infocemosa | `CCTV point registry (Infocemosa ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 0e5a5c9aa4e49baa553529b523379bf47c12d62460a8e4fd963876992b43e6fd | pending |
| D06-13 | camreg_infraestructura | `CCTV proyectado registry (ArcGIS, Spanish schema)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 5c81dbdb12b9909c2f9b6c45c8c9d5e4a28fe155533969428087d87007b2cb1e | pending |
| D06-14 | camreg_ira | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D06-15 | camreg_it_me_messina_videosorveglianza | `Videosorveglianza urbana` — a government portal source published by `Comune di Messina`. | 7059714ccafd177fdba1726a11154ce294ebbf283442856adc831272d3261e32 | pending |
| D06-16 | camreg_jcfd3_or | `Jackson County OR RoxyAnn camera (ArcGIS registry)` — a government portal source published by `Jackson County Fire District 3, Oregon`. | 7d8d4419ca33c3ca096cf070547702247e00df7069f087da924f47ad9750d2c1 | pending |
| D06-17 | camreg_jeffersonville_in_flock | `flock (City of Jeffersonville, IN)` — a government portal source published by `City of Jeffersonville, IN (staff account, via ArcGIS Online)`. | c4dd1b263ba16f6a7d03b24cfb41decf54909370d5816adbe35c480d9c9f7ea3 | pending |
| D06-18 | camreg_jmh_us | `MPD Flock camera locations (ArcGIS registry)` — a government portal source published by `US municipal police department (jmh_com publisher)`. | 427c5cb71a123356f50380306bc5aa9a64535cb5d87ad20122201dc42ce5411d | pending |
| D06-19 | camreg_kcmo_mo | `Kansas City traffic camera locations (ArcGIS registry)` — a government portal source published by `Kansas City, Missouri`. | 18f8ced203475ca3075c0566097b446c37e8c4165bf91c6b685d7e2222b1fa44 | pending |
| D06-20 | camreg_keizer_or | `Keizer traffic and graffiti cameras (ArcGIS registry)` — a government portal source published by `City of Keizer, Oregon`. | c58e4033590ac5dd1427b34cb36936a21942adbda2cacd2a74e19ea7e53fe901 | pending |
| D06-21 | camreg_kirkland_wa | `Kirkland traffic cameras (ArcGIS registry)` — a government portal source published by `City of Kirkland, Washington`. | acde15e1e27823ed1547b94c6323abd366e57f4180abb98c153e9901b3b5fb43 | pending |
| D06-22 | camreg_la_east_baton_rouge_parish_flock | `Flock_Location_Data view (East Baton Rouge Sheriff's Office)` — a government portal source published by `East Baton Rouge Parish Sheriff's Office, LA (staff account on the ebrso.org domain, via ArcGIS Online)`. | 579e8067f0f9429c184f64d3e8600984d27a534ad9d8d98df075268507163f92 | pending |
| D06-23 | camreg_la_new_orleans_eye_on | `Eye on Surveillance - New Orleans surveillance map (cameras, ALPR, Project NOLA)` — a government portal source published by `Eye on Surveillance (New Orleans NGO), production map.eyeonsurveillance.org`. | d6d7b940d13310d535e1f0a0a93cb6086ee8ecee0fc366f839440bb2756112f7 | pending |
| D06-24 | camreg_lakeland_fl_red_light | `Red Light Cameras and Direction (City of Lakeland, FL)` — a government portal source published by `City of Lakeland, FL (via ArcGIS Online)`. | 032900f8cd82f69204165e3bb2c90416ac02f106bbd1842fc0ca921c244d30d3 | pending |
| D06-25 | camreg_lambeth_gb | `Lambeth parking CCTV cameras (ArcGIS registry)` — a government portal source published by `London Borough of Lambeth`. | 38ef91bd6e76e01bfbab27bea8342c8ea6d71d987599831b3ead7a477928042e | pending |

## Confirmation log

(none yet)
