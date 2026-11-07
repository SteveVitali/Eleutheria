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
| D15-01 | demandstar | `DemandStar — public agency bid portal` — a government portal source. | 87fc37f7b67cf0f0e63c87581f857e5661d575decc7796661d67453422e7ea00 | pending |
| D15-02 | denmark_politi_cctv | `Denmark National Police — official CCTV camera map` — a government portal source. | ddd18295b38bde4b574a9a5d36099ed0b3558aad9dfaa60876b0dc9dd16355db | pending |
| D15-03 | dhs_fusion_center_assessments | `DHS Fusion Center Assessment — National Network of Fusion Centers governance reports` — a government portal source. | 584cf212379abb5036c83a45f2fb5e453bc03421a0deacaebc2d6bc735e9f20d | pending |
| D15-04 | dhs_fusion_centers | `DHS fusion centers` — a government portal source. | afc86ebabaec998b814cbcdb3d73fd4371bdb5f52b2da7e824f7baecf0ce70e7 | pending |
| D15-05 | dhs_oig_reports | `DHS Office of Inspector General — oversight reports (fusion centers, grant programs, CBP/ICE surveillance)` — a government portal source. | d17ed014f4cd26ba134b6c31328c7f259d35494ddce5a9f31910bff93b3113e0 | pending |
| D15-06 | documentcloud | `DocumentCloud` — a records channel source. | f8d77b2dc18e525bcc4d7125f755cfca1ef69428832455ae03e3d4a017c703c4 | pending |
| D15-07 | dossier_okc | `City of Oklahoma City — ALPR dossier documents (usage page, council memo, amendment)` — a government portal source. | 9389b3586a350964692102ba5a9f80340372909faff0cf5fc9e9fb2a68205161 | pending |
| D15-08 | dossier_san_diego | `City of San Diego — surveillance-technology dossier documents (ASR, Ubicquia agreement, indexes)` — a government portal source. | c2d917ed24a6afb4ea32115104365bb2658f1145346c2e55648b111fcb4dc28d | pending |
| D15-09 | dossier_tulsa | `Tulsa Police Department — ALPR dossier documents (policies 113C/113E, MOU template)` — a government portal source. | b6c84a7c3e7148725436ea75858fe116e01073fba16a8b79c174df79686bce5b | pending |
| D15-10 | dot_511_ak | `511 Alaska camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Alaska Department of Transportation & Public Facilities (511 Alaska)`. | 21187d113cadf18a2d650192f73eb456666786cdba90f357a9d38bd1f13181c9 | pending |
| D15-11 | dot_511_al | `ALDOT traffic cameras (ArcGIS registry)` — a government portal source published by `Alabama Department of Transportation`. | e8ee9bee0493fe9aa8d3bdbc84850c2a57085a486beea207f3399b2e6f3de39e | pending |
| D15-12 | dot_511_az | `AZ511 camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Arizona Department of Transportation (AZ511)`. | 91116a5d7261d4c40e2704b262ab9c6f8b48abe098bf7c8a97dcb071ad19cd1e | pending |
| D15-13 | dot_511_ct | `CTroads camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Connecticut Department of Transportation (CTroads)`. | dac91357970f7935b21c3b166e3ee21ecae42dada6c752038cb004edd91d14d2 | pending |
| D15-14 | dot_511_dc | `DDOT traffic cameras (DC GIS registry)` — a government portal source published by `District Department of Transportation / DC GIS (OCTO)`. | d934c0ee65b1a437e8cfab37e8090b6b5cc9e43472cbf907d08b0181060815e2 | pending |
| D15-15 | dot_511_de | `Traffic Devices - CAMERA (DE_Boundary_and_Point layer 26)` — a government portal source published by `Delaware Department of Transportation (DelDOT) via Delaware FirstMap (state ArcGIS Enterprise)`. | 396ad2295f5b539bdf593b8b8041aef49a90154263f80d479be87221290d809a | pending |
| D15-16 | dot_511_fl | `Florida 511 (FL511) camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Florida Department of Transportation (FL511)`. | 0891787cb5656d7149a936ed83cf0dccff5def59d23ee5afeea9061488116a31 | pending |
| D15-17 | dot_511_ga | `GDOT 511 cameras (ArcGIS registry)` — a government portal source published by `Georgia Department of Transportation, rbagby_gema`. | 86d732d554972fa36f91118e2b6c7547763ece677bf189bf754f8686b6f2a58a | pending |
| D15-18 | dot_511_gb | `data.gov.uk CKAN package_search — CCTV (56 datasets)` — a government portal source published by `data.gov.uk (UK Government, per-dataset publishers)`. | e0487c85d9c53bb6e8499fdb4bf7d98090a3ecb9d0758eb84f72ded7c93a777b | pending |
| D15-19 | dot_511_ia | `Iowa DOT traffic cameras (ArcGIS registry)` — a government portal source published by `Iowa Department of Transportation`. | 45d6845a26d1fbedb7e72781622bcd0ee72fc731da333051400b604590f80076 | pending |
| D15-20 | dot_511_id | `Closed-Circuit Television (CCTV) (ITD IntelligentTransportationSystems layer 0)` — a government portal source published by `Idaho Transportation Department (ArcGIS Enterprise gisp.itd.idaho.gov, owner ITDGISdata)`. | 6244d07f8621d599324b367ea6fa4db3a43825041a678c417724a1f21ce0ccf1 | pending |
| D15-21 | dot_511_il | `IDOT Illinois Gateway traffic cameras (ArcGIS registry)` — a government portal source published by `Illinois Department of Transportation`. | 78aa288f53d6ffae3ade280eb895c01f38286576639e2331efd00df1ca6756c4 | pending |
| D15-22 | dot_511_ky | `KYTC traffic cameras (ArcGIS registry)` — a government portal source published by `Kentucky Transportation Cabinet`. | cf5babec1bc98f2a2924e060c0ea6597ea6e6a57c6cf085a812da36934113975 | pending |
| D15-23 | dot_511_la | `LDOTD traffic cameras (ArcGIS registry)` — a government portal source published by `Louisiana Department of Transportation and Development`. | 4a8782eae577798dcbba128a2ef25675acb0dde4125d6f34ae08c57b9bddc9ec | pending |
| D15-24 | dot_511_md | `MD SHA CHART traffic cameras (ArcGIS registry)` — a government portal source published by `Maryland DOT SHA / CHART`. | 787094955cb8820619bdf9ee340b9d80024c9f7b56083bcbde0d094c057b4fbd | pending |
| D15-25 | dot_511_mi | `MiDrive Cameras` — a government portal source published by `Michigan Department of Transportation (via ArcGIS Online, owner MDOT_GIS)`. | 1dee23f8a5ff60a8a53a2c7ce8aa3d56de62f3967340caf0fdfd957dfeaf8b49 | pending |

## Confirmation log

(none yet)
