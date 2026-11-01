# Description batch 15 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D15-01 | dhs_fusion_center_assessments | DHS Fusion Center Assessment — National Network of Fusion Centers governance reports — a government portal source. | 9cb7083d79a77f66aadae13eb5182fc9f761ed16d9e715ea83da4b8ac9a68c12 | pending |
| D15-02 | dhs_fusion_centers | DHS fusion centers — a government portal source. | 289ec319f98267ea24c0f88af1da7dd2350e3ff44355b7ffeadc43f158e2e242 | pending |
| D15-03 | dhs_oig_reports | DHS Office of Inspector General — oversight reports (fusion centers, grant programs, CBP/ICE surveillance) — a government portal source. | a810d39024098ded4e379bb3d233793869a8ef43637566f3883e96e125ae8f82 | pending |
| D15-04 | documentcloud | DocumentCloud — a records channel source. | db325221cd86bc71fdf2036885dde4546bc832bb505fdfbe390524e75a17a043 | pending |
| D15-05 | dossier_okc | City of Oklahoma City — ALPR dossier documents (usage page, council memo, amendment) — a government portal source. | e07d134e952670defd89e52628a094db63e12dd99ceb3dd01b64f77a8115fb5d | pending |
| D15-06 | dossier_san_diego | City of San Diego — surveillance-technology dossier documents (ASR, Ubicquia agreement, indexes) — a government portal source. | 2c7294f3e1839949767627af4f988168ee57e6fc85146d0fda6ba03a2e16ae71 | pending |
| D15-07 | dossier_tulsa | Tulsa Police Department — ALPR dossier documents (policies 113C/113E, MOU template) — a government portal source. | 96c69dad51b9550762e6b59a4942f9d1ea4fc77ec3fabd45f551d0d81e9832fc | pending |
| D15-08 | dot_511_al | ALDOT traffic cameras (ArcGIS registry) — a government portal source published by Alabama Department of Transportation. | c12c8092ad946466de29a13ec9441966a09ea23d4bac418007baec4f79fadad5 | pending |
| D15-09 | dot_511_dc | DDOT traffic cameras (DC GIS registry) — a government portal source published by District Department of Transportation / DC GIS (OCTO). | a98cadccba54eb46dc442f462af04c90ece1d68277a9aabdeef786e012d4903d | pending |
| D15-10 | dot_511_de | Traffic Devices - CAMERA (DE_Boundary_and_Point layer 26) — a government portal source published by Delaware Department of Transportation (DelDOT) via Delaware FirstMap (state ArcGIS Enterprise). | d0c613183292e0843b6aec902be6a828dc6f407b89e8ef1e2bf9aea8080fe99c | pending |
| D15-11 | dot_511_ga | GDOT 511 cameras (ArcGIS registry) — a government portal source published by Georgia Department of Transportation; rbagby_gema. | 5cbc269ba9f94f7d5a4f2bf6f03d7013014ae9b1fe82970df5b4f0bf57597e41 | pending |
| D15-12 | dot_511_gb | data.gov.uk CKAN package_search — CCTV (56 datasets) — a government portal source published by data.gov.uk (UK Government; per-dataset publishers). | ebbb067ea186edf3320e74b6b2345352b14b90799dee7b549807b0b3e5e8b184 | pending |
| D15-13 | dot_511_ia | Iowa DOT traffic cameras (ArcGIS registry) — a government portal source published by Iowa Department of Transportation. | 08160d23f9b9f0fc7840701302835f4d2cf06c2f2ad245e18ff5bcf4d054cd4b | pending |
| D15-14 | dot_511_id | Closed-Circuit Television (CCTV) (ITD IntelligentTransportationSystems layer 0) — a government portal source published by Idaho Transportation Department (ArcGIS Enterprise gisp.itd.idaho.gov; owner ITDGISdata). | a45265666032866636ea56baad691847bb394ae7a59374d059dd4df238441ee8 | pending |
| D15-15 | dot_511_il | IDOT Illinois Gateway traffic cameras (ArcGIS registry) — a government portal source published by Illinois Department of Transportation. | 66b7a070ff48c53539890384b99e0f8e51223548db63471f2fc9240564710495 | pending |
| D15-16 | dot_511_ky | KYTC traffic cameras (ArcGIS registry) — a government portal source published by Kentucky Transportation Cabinet. | ce451a9e17a82749eac3af46b540abd620e4f1592aadb98987024501eb804a6e | pending |
| D15-17 | dot_511_la | LDOTD traffic cameras (ArcGIS registry) — a government portal source published by Louisiana Department of Transportation and Development. | d6523963fe92fd15c3cc5faee9c6266966a9f97dc046f1a67c25604a3b7d903c | pending |
| D15-18 | dot_511_md | MD SHA CHART traffic cameras (ArcGIS registry) — a government portal source published by Maryland DOT SHA / CHART. | 135c0dc4d446097d438d5d037590d87618179de1c4d7b7eeeb5f37ff59ace9d0 | pending |
| D15-19 | dot_511_mi | MiDrive Cameras — a government portal source published by Michigan Department of Transportation (via ArcGIS Online, owner MDOT_GIS). | ae79c678b1ce8c9d54415132fdb49a5253ebaf7a14a6b18dd3ece3452bc820f6 | pending |
| D15-20 | dot_511_mo | MoDOT traffic cameras (ArcGIS registry) — a government portal source published by Missouri Department of Transportation. | ba5d6004f9e1558fdf4586ee8fbe5ece15fd333435596abfbd495e259999e6e0 | pending |
| D15-21 | dot_511_nc | NCDOT_Cameras — a government portal source published by North Carolina Department of Transportation (ArcGIS Online org NuWFvHYDMVmmxMeM, which hosts GISUnit.NCDOT.GOV items). | 235e41dd5a7e01154912f99e40fbd94124afe7455d583647c33276468673ef49 | pending |
| D15-22 | dot_511_nm | Statewide CCTV View — a government portal source published by NMDOT ITS CCTV inventory per item snippet (ArcGIS Online org short-name "ITS511", owner douglas.geusz_ITS511; org identi. | dd2ab22e02746d30bbbb37b7a980d6b27b0765d89660ecf2e1e9338691fca161 | pending |
| D15-23 | dot_511_nv | ITS_ATM - Existing Devices (NDOT Statewide ITS ATM Masterplan, layer 3) — a government portal source published by Nevada Department of Transportation (ArcGIS Online owner OpenData_NDOT). | 8d4b1c3adc2ffec87e7d2e0a8f40d3a94dfd90810b6c1dc3f454e76816329a49 | pending |
| D15-24 | dot_511_or | ODOT TripCheck cameras (ArcGIS registry) — a government portal source published by Oregon Department of Transportation (TripCheck). | 5f78d24b08939d2e426e01622e040f6437736446ffe45aa5eb35dc18d131dba5 | pending |
| D15-25 | dot_511_tx | TxDOT CCTV locations (ArcGIS registry) — a government portal source published by Texas Department of Transportation. | fb8c5e19642a40cdc0fb8628cfb2d3d072bb88a7cc2cbdfd07ccc6a8a69babce | pending |

## Confirmation log

(none yet)
