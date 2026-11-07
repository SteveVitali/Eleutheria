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
| D09-01 | camreg_pt_11_lisboa_sistema_de | `Sistema de Videovigilância Bairro Alto` — a government portal source published by `Município de Lisboa`. | e1c151793fb120d4f55ca9bceaadde7eb1bcd63b39c75ae6b21a993407de8364 | pending |
| D09-02 | camreg_pueblo_co_flock | `Flock (City of Pueblo, CO)` — a government portal source published by `City of Pueblo, CO (via ArcGIS Online)`. | 036fb5466f94030af3a9ef2b10358b39bd63b7a70596e6c9ef1a01ca0e1336d1 | pending |
| D09-03 | camreg_puertogaitan_co | `Puerto Gaitán municipal CCTV map (datos.gov.co Socrata registry)` — a government portal source published by `Alcaldía de Puerto Gaitán, Meta`. | 9575f99b8995e03672918563cce8833a44c8c1a937cc055360a184d409a25d66 | pending |
| D09-04 | camreg_qldc_au | `Queensland CCTV cameras external view (ArcGIS registry)` — a government portal source published by `Queensland Government (QLDCGIS external view)`. | 72c9946d7e8752ab63a944c224f8bfcff6eefaf727b4d96048c4dc067f8e3d06 | pending |
| D09-05 | camreg_qldtraffic_au | `QLDTraffic v1 webcams API — TMR keyed GeoJSON feed` — a government portal source published by `Queensland Government (QLDTraffic / TMR)`. | 413d1239f1b0090a749787d99f74935125af975234d89ebffe22d5d43d7ec72d | pending |
| D09-06 | camreg_raleigh_nc | `Raleigh traffic cameras (ArcGIS registry)` — a government portal source published by `City of Raleigh, North Carolina`. | 0a400b5c590e9955ddfea2fd3e3682b1baedb04376b5149574f8cfaf2ea5b49a | pending |
| D09-07 | camreg_ramallah_ps | `Ramallah surveillance camera network (ArcGIS registry)` — a government portal source published by `Ramallah municipal camera registry (community-published layer)`. | 5b5a5245a66f07abff3ddb6a67ca7453a881e0b8cadb90cf782b3d23f7634a8f | pending |
| D09-08 | camreg_redmond_wa | `Redmond traffic cameras (ArcGIS registry)` — a government portal source published by `City of Redmond, Washington`. | 82d7781f46c29916278bb7324b872c780e77ec75ed566c4b835d41d423c74975 | pending |
| D09-09 | camreg_riyadh_sa | `Riyadh camera-control registry (ArcGIS registry)` — a government portal source published by `Riyadh municipal camera registry (rematalriyadh publisher)`. | 7926ca2368ebaab8313d9652c1322bb4b29c330a64a34962fbd8689116785e42 | pending |
| D09-10 | camreg_rochester_ny | `Rochester NY BlueLight cameras (ArcGIS registry)` — a government portal source published by `Rochester Police Department (City of Rochester, NY)`. | 013a8f102d077fc4156ed643e5a85a806ce96bc08c03e153a68f524be42f567a | pending |
| D09-11 | camreg_rocky_mount_nc_lpr_cameras | `LPR_Cameras (City of Rocky Mount, NC)` — a government portal source published by `City of Rocky Mount, NC (via ArcGIS Online)`. | 970c840dbee8264b97af97bb14a2e5d14be1a4896908d07aa7b850e35ab0e6e7 | pending |
| D09-12 | camreg_salisbury_nc | `Salisbury NC traffic cameras (ArcGIS registry)` — a government portal source published by `City of Salisbury, North Carolina`. | cbbaa0cfb70350d2182a2faec0e06773d9cb2f6f52754a085b5281c9fcf63b42 | pending |
| D09-13 | camreg_santa_fe_nm_park_cameras | `Park Cameras (City of Santa Fe park camera locations)` — a government portal source published by `City of Santa Fe, NM Parks (layer published by WSP consultant account Jay.puckett_wsp5)`. | 4bf5b7fa8b3acf519669e20492dd5d35ce3a482944b1b6ea6270dce55abb2b73 | pending |
| D09-14 | camreg_sarasota_fl | `Sarasota County traffic cameras (Cartegraph ArcGIS registry)` — a government portal source published by `Sarasota County, Florida`. | 194ea11fe2361e457c41bd46ef212316f373964420754cafc62bee11c28bc7ee | pending |
| D09-15 | camreg_seattle_wa | `Seattle traffic + safety cameras (SDOT ArcGIS registry)` — a government portal source published by `City of Seattle (SPD GIS), Seattle Department of Transportation`. | 0c7449107bdff89f95bd027934c6de1840ce77890a8eb0bcb0196098b661129d | pending |
| D09-16 | camreg_sensenet | `Camera view registry (SenseNet ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 70ab36400ca888cf8ee6aa34f6df9f0c7f9846a9f6581050312cec952bce9182 | pending |
| D09-17 | camreg_sheffield_gb | `Sheffield CCTV and traffic cameras (ArcGIS registry)` — a government portal source published by `Sheffield City Council`. | 5f0222c920213faa21e4ad48369c62925fe294e6ab3bcf029508dce5c6dfeab5 | pending |
| D09-18 | camreg_shelbyville_tn_flock_cameras | `Flock Cameras - Public (City of Shelbyville, TN)` — a government portal source published by `City of Shelbyville, TN (via ArcGIS Online)`. | d29d0825c73e1773c47866f32cd1f4cabdc822e6722cc8c336ac691ba6c61000 | pending |
| D09-19 | camreg_si_048_ko_evje_videonadzor_na | `Videonadzor na javnih površinah na območju Občine Kočevje` — a government portal source published by `Občina Kočevje (via podatki.gov.si)`. | ba7eb521c4b8460a961daa80a4339888679779039b1785a8a2ec231ed736dd61 | pending |
| D09-20 | camreg_siouxfalls_sd | `Sioux Falls traffic surveillance cameras (ArcGIS registry)` — a government portal source published by `City of Sioux Falls / Sioux Falls Traffic Management`. | bf686bb956b30be4ec571e90f3d007f05a622a534c8294a003b4390a7b00608a | pending |
| D09-21 | camreg_smart_sky | `Camera registry (Smart Sky ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 29a1130430f6b2691acf8907ce9e72746298d911758639e3eb0089c1468b670c | pending |
| D09-22 | camreg_south_fulton_ga_lpr_cameras | `LPR Cameras (City of South Fulton, GA)` — a government portal source published by `City of South Fulton, GA (via ArcGIS Online)`. | 06409b9bcfff9088a7d69a222116f5281d20f62c18c4ae7f1b32e6b4618c1eee | pending |
| D09-23 | camreg_squan | `Stephen camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | b679ccb084d55118270b7bb52adefcdecfef7f871bcf949edc533f41845bda93 | pending |
| D09-24 | camreg_stalbert_ab | `St. Albert photo enforcement camera sites (ArcGIS registry)` — a government portal source published by `City of St. Albert`. | 8a4134515ec6b00ed586952cd56ed735aa45f0f41b2772b372461549e5702053 | pending |
| D09-25 | camreg_stanford_us | `US-nationwide surveillance-tower / ALPR-checkpoint research layers (Stanford)` — a government portal source published by `Stanford University research-compiled camera locations`. | 11ada410c9f826231bcc470b8a8c7f9914fa5ebc2410acbbb5edae87eb4e576f | pending |

## Confirmation log

(none yet)
