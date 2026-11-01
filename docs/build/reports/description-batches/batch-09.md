# Description batch 09 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D09-01 | camreg_pueblo_co_flock | Flock (City of Pueblo, CO) — a government portal source published by City of Pueblo, CO (via ArcGIS Online). | 6dfb733b4e9c6964132865c51087316725353d62aa71804ba04986ca876726b8 | pending |
| D09-02 | camreg_puertogaitan_co | Puerto Gaitán municipal CCTV map (datos.gov.co Socrata registry) — a government portal source published by Alcaldía de Puerto Gaitán, Meta. | 0016d9222ac0325a98f20ca5d7ab21cbb2f30ae7dbc0926d8e4a451b8e3d5df0 | pending |
| D09-03 | camreg_qldc_au | Queensland CCTV cameras external view (ArcGIS registry) — a government portal source published by Queensland Government (QLDCGIS external view). | 3e7e2b4a386c72d07ffd644fc13984f25b28a47902a220bec851b215047fc732 | pending |
| D09-04 | camreg_raleigh_nc | Raleigh traffic cameras (ArcGIS registry) — a government portal source published by City of Raleigh, North Carolina. | 3ddd49275775e981406f692cd42d67969c0a26670ba6786cd876a4fd1084cab6 | pending |
| D09-05 | camreg_ramallah_ps | Ramallah surveillance camera network (ArcGIS registry) — a government portal source published by Ramallah municipal camera registry (community-published layer). | aff290154e95f1d2a365677a16f2877ebe449864a86d78dfc8ee33e6e4c9ed41 | pending |
| D09-06 | camreg_redmond_wa | Redmond traffic cameras (ArcGIS registry) — a government portal source published by City of Redmond, Washington. | e071a0d0c2cd55314a03a35800945d5a601aa85158514541a7be2c8094ed6b09 | pending |
| D09-07 | camreg_riyadh_sa | Riyadh camera-control registry (ArcGIS registry) — a government portal source published by Riyadh municipal camera registry (rematalriyadh publisher). | da8ea7979ec8d24fbc2f8c3fc9290d3c3009e750bd71e4ea6c7032191307a1c5 | pending |
| D09-08 | camreg_rochester_ny | Rochester NY BlueLight cameras (ArcGIS registry) — a government portal source published by Rochester Police Department (City of Rochester, NY). | 90a6fa4f6d6358f69eb2fada69db1eed6f80d0d1b39456ecb2173907c13a33c6 | pending |
| D09-09 | camreg_rocky_mount_nc_lpr_cameras | LPR_Cameras (City of Rocky Mount, NC) — a government portal source published by City of Rocky Mount, NC (via ArcGIS Online). | 410ab662c74d1931f153b02faee2c18f791ac4a2ed368a1c866004fa2f3690ed | pending |
| D09-10 | camreg_salisbury_nc | Salisbury NC traffic cameras (ArcGIS registry) — a government portal source published by City of Salisbury, North Carolina. | ae3e57e5687021e01a2d9542d272cce97a0fb9d409f1731d535d9e06e2594005 | pending |
| D09-11 | camreg_santa_fe_nm_park_cameras | Park Cameras (City of Santa Fe park camera locations) — a government portal source published by City of Santa Fe, NM Parks (layer published by WSP consultant account Jay.puckett_wsp5). | b6260afc502c610c3054a371c242f91201f25f2cde78fa84aba60a66985cfcad | pending |
| D09-12 | camreg_sarasota_fl | Sarasota County traffic cameras (Cartegraph ArcGIS registry) — a government portal source published by Sarasota County, Florida. | 5acab918d6c2bbecf65c640ed3da0039ad051aac432de64aec4d99f88e6e0ed2 | pending |
| D09-13 | camreg_seattle_wa | Seattle traffic + safety cameras (SDOT ArcGIS registry) — a government portal source published by City of Seattle (SPD GIS); Seattle Department of Transportation. | d213d07da489ce654177269f028ed43e9044aaa7c3a9e0dc19c4e8e29c55ee68 | pending |
| D09-14 | camreg_sensenet | Camera view registry (SenseNet ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 391a5de2748c31a1836202658248d6e426f046f69021455131dd9bacdecb3b16 | pending |
| D09-15 | camreg_sheffield_gb | Sheffield CCTV and traffic cameras (ArcGIS registry) — a government portal source published by Sheffield City Council. | be6ea77ce93eb2402a014ce5187194f83587d16deb2d96e9eca55f5e14233802 | pending |
| D09-16 | camreg_shelbyville_tn_flock_cameras | Flock Cameras - Public (City of Shelbyville, TN) — a government portal source published by City of Shelbyville, TN (via ArcGIS Online). | 5de48e4fe556f6c891e858c66f5fbf422efb003c0b3fc5fe29955caefeb06af0 | pending |
| D09-17 | camreg_si_048_ko_evje_videonadzor_na | Videonadzor na javnih površinah na območju Občine Kočevje — a government portal source published by Občina Kočevje (via podatki.gov.si). | 2711e5538ca24fff5cdc34b4821e20ea90bde99818b3aaace160061dadc0663c | pending |
| D09-18 | camreg_siouxfalls_sd | Sioux Falls traffic surveillance cameras (ArcGIS registry) — a government portal source published by City of Sioux Falls / Sioux Falls Traffic Management. | 22221076e57bb15b3509b6851cfe0e8c4fcbb1a4a2063a8009718b39776b5db6 | pending |
| D09-19 | camreg_smart_sky | Camera registry (Smart Sky ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | ce42aaa76f19a304831652a15f2781dc80feafc048500a0286798c0cd37db9fe | pending |
| D09-20 | camreg_south_fulton_ga_lpr_cameras | LPR Cameras (City of South Fulton, GA) — a government portal source published by City of South Fulton, GA (via ArcGIS Online). | 0a7ab19043fab8a4fa173bc00461f9de44a29c936dccd20464d15da096345d7e | pending |
| D09-21 | camreg_squan | Stephen camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | ed120cd7d86f4471b2c8719c894259783c94b9ab99b7a0c376e01b1129759ac5 | pending |
| D09-22 | camreg_stalbert_ab | St. Albert photo enforcement camera sites (ArcGIS registry) — a government portal source published by City of St. Albert. | 618eccf23819c995820e1a81bfd2ef73e9b7e426bec7527f7196fe92820998f0 | pending |
| D09-23 | camreg_stanford_us | US-nationwide surveillance-tower / ALPR-checkpoint research layers (Stanford) — a government portal source published by Stanford University research-compiled camera locations. | 7c1f8e95f16e3ef59db17c6c3257ec1782d1648760fe91f3934f6e2e7ba1cee6 | pending |
| D09-24 | camreg_suffolk_ny_red_light | TPVA Red Light Camera Locations 2015 (Suffolk County, NY Traffic and Parking Violations Agency; SCOpenData) — a government portal source published by Suffolk County, NY (SCOpenData via ArcGIS Online). | 0ff95151f911d36230516b9bd1611cd3631e185cbadd3c722cd793c82192a252 | pending |
| D09-25 | camreg_surrey_bc | Surrey traffic cameras (ArcGIS registry) — a government portal source published by City of Surrey, British Columbia. | 39ba27bc5de2393aa66198a93f80b11cc78cbcc66cbb6f7b35255a3a80125a17 | pending |

## Confirmation log

(none yet)
