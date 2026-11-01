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
| D04-01 | camreg_colgis | Traffic cameras view (COLGIS ArcGIS registry) — a government portal source published by ArcGIS community-published traffic-camera registry. | 1c242c0a60321b2f9a2b8e8ab7c94a1749371068c8f4267b7c874c38f5557521 | pending |
| D04-02 | camreg_cotgeo | Geospatial traffic camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published traffic-camera registry. | c2ce77c42e714f3ada65241c971330c27707649e0dddf51308a61baf0ca5e13f | pending |
| D04-03 | camreg_ctdot_speed_safety | Approximate Speed Safety Camera Locations Public (CTDOT Work Zone Speed Control pilot) — a government portal source published by Connecticut Department of Transportation (ArcGIS Online owner CTDOT_OpenData). | e94f1fc093d0f63cf7be4a8c90983311d34570ca48adb275a9dda3c83fabac91 | pending |
| D04-04 | camreg_cwarcgis | Camera registry (cwarcgis ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 1d372cfeb1525a85bf9ccbd527006c1ad954583e8ad7365c83a3b065cebcb004 | pending |
| D04-05 | camreg_dc_ddot_ate | DC Automated Safety Cameras (ASC) — locations layer + violations-by-month table (DDOT via DC GIS) — a government portal source published by District of Columbia, District Department of Transportation (via DC GIS / OCTO). | 3468c4cade4c31d812de6d23c419a5c13c4c51d4ca2a18dab8276e1b0126d85f | pending |
| D04-06 | camreg_dc_dot_dc | Washington DC traffic-camera ArcGIS republish layers — a government portal source published by District of Columbia (DDOT camera registries, republished layers). | 7dacaf76142bc0df56ef6437fc925f8be61b697906d14bf60cad8a8fbc78c3d2 | pending |
| D04-07 | camreg_dc_ovsjg_camera_rebate | DC Private Security Camera Rebate Program — per-PSA × month programme aggregates (OVSJG via DC GIS) — a government portal source published by District of Columbia Office of Victim Services and Justice Grants (DC GIS). | 51e69357bfaf05ae5f6cde281aaa44f0fef590cb4551693e24c015d1b18b1dea | pending |
| D04-08 | camreg_de_delaware_checkbook_expenditure | Delaware Checkbook Expenditure Details (+ State of Delaware Checkbook; Statewide Central Contract Spend) — a government portal source published by State of Delaware, Department of Finance, Division of Accounting (via data.delaware.gov). | 230a30085f3ec3c80dafafedddf15dca3e0b91b877c1f66b193a9ab6094ab500 | pending |
| D04-09 | camreg_denver_co | Denver automated license-plate-reader camera locations (ArcGIS registry) — a government portal source published by City and County of Denver; City and County of Denver (geospatialDENVER). | 3251b3f5d2889b76039f7ebd87dab7b5775b82302f8e66567fafb9f66ecb7b02 | pending |
| D04-10 | camreg_detroit_mi_project_green_light | Project Green Light Locations — a government portal source published by City of Detroit / Detroit Police Department (via ArcGIS Online org qvkbeam7Wirps6zC, data.detroitmi.gov). | 801a6770278aa61b63e44dab0e5db8595b99d505793b91afff3b598f7eb6fe30 | pending |
| D04-11 | camreg_donegal_ie | Donegal traffic cameras (ArcGIS registry) — a government portal source published by Donegal County Council / TII. | 80ada1e14768f4a871e3c89487d1d3a9f295cb0034e88a4ae83f3ff72834db2f | pending |
| D04-12 | camreg_dover_gb | Dover CCTV cameras (ArcGIS registry) — a government portal source published by Dover District Council. | 2a9ee257c8c60999da1ef7646a7dc7f9dcf35705796ba72f611fda6fb691c37f | pending |
| D04-13 | camreg_dubuque_ia | Dubuque public camera locations (ArcGIS registry) — a government portal source published by City of Dubuque, Iowa. | 5482c259cdc856ee1071c281a2de8dcbb9f3ee86e0ed2279f61f565e707557ba | pending |
| D04-14 | camreg_durham_gb | Durham County traffic web cameras (ArcGIS registry) — a government portal source published by Durham County Council. | c417ba4bb48df34910bb9b23ff69df938988bd902dfc9bb87d64fc7eabef7d75 | pending |
| D04-15 | camreg_eastdun_gb | East Dunbartonshire CCTV cameras (ArcGIS registry) — a government portal source published by East Dunbartonshire Council. | e81806e1ee9601cbbe6d92b6512057fe7f1cdc030de93393db10d0fcc5546c89 | pending |
| D04-16 | camreg_ebrgis_la | East Baton Rouge traffic cameras (EBRGIS ArcGIS registry) — a government portal source published by City of Baton Rouge / East Baton Rouge Parish. | 10740e0e288a03db4beb45326e802b788cb51e51a496bc257070d1c452e83729 | pending |
| D04-17 | camreg_edmonton_ab | Edmonton intersection safety device locations (Socrata registry) — a government portal source published by City of Edmonton. | 46884116932d81b9fefe0d2cc1c78c74c1ee0be8a0db1d8cbddd0b0081b5de37 | pending |
| D04-18 | camreg_elgin_il_lpr_cameras | LPR Cameras (City of Elgin, IL) — a government portal source published by City of Elgin, IL (via ArcGIS Online). | f3d66c92ced46f580a61517506df4eb4b05c3f7e8385517f8bf09f7775eabb0f | pending |
| D04-19 | camreg_es_md_madrid_c_maras_de | Cámaras de videovigilancia en la vía pública de Madrid — a government portal source published by Ayuntamiento de Madrid (Policía Municipal). | 17e990ff091a36d8141de95b7f7a2ae22546d26b3429da937ec6a8990c04bb64 | pending |
| D04-20 | camreg_esri_dash | Traffic cameras (Esri dashboard-publisher ArcGIS layer) — a government portal source published by ArcGIS community-published traffic-camera registry. | c5d92e9356cc4028bbfdc7d2e6def78558be8145106bf5fc3dab5f35d3386f4c | pending |
| D04-21 | camreg_esriukpolice_gb | UK police CCTV locations (Esri UK police ArcGIS registry) — a government portal source published by Esri UK police demonstration org (community-published layer). | 22a6ca98c4f772f7fb0e8adf010a5b7f8e2c889923f2b85068669bb581fa2d08 | pending |
| D04-22 | camreg_essex_gb | Essex safety cameras public view (ArcGIS registry) — a government portal source published by Essex County Council / Essex Safety Camera Partnership. | 18b34a0dd55dc96ccd5536cab424ae9daa6e5dea84acf058b7a219d02d7f83f7 | pending |
| D04-23 | camreg_eu_eea_data_europa_search_api | data.europa.eu search API — multilingual CCTV/video-surveillance datasets (148 hits) — a government portal source published by Publications Office of the EU (data.europa.eu; harvests national portals). | 9f748288ca8351e00c8ac8f7ea803cfe93f80794d1b7a9f8a1f89f6a2c5eae89 | pending |
| D04-24 | camreg_fdot_flock | FDOT District 3 Flock camera inventory + FLOCK removal status layers — a government portal source published by Florida Department of Transportation, District 3 (via ArcGIS Online). | a769604fa1312a4464f2c6e5d6f1794f75b388c49a7401aa5f4e1d28871309c0 | pending |
| D04-25 | camreg_firemedic | Traffic camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published traffic-camera registry. | c714242103ee52c787099a8e96cff0d4ac8f41455730c8daa67512008e131717 | pending |

## Confirmation log

(none yet)
