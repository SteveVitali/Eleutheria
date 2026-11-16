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
| D15-01 | datalib_clearview_ai_table | `Clearview AI Table (BuzzFeed News — entities whose employees ran Clearview facial-recognition searches)` — a news publisher source published by `BuzzFeed News`. | bd384a1807b6de1a17bd6576935787c093da2547a74ceb2b2caadababfc12526 | pending |
| D15-02 | datalib_federally_funded_bwc | `Federally Funded Body-Worn Cameras (EFF-compiled — DOJ/BJA grant-recipient agencies)` — an upstream project source published by `Electronic Frontier Foundation (upstream: US DOJ Bureau of Justice Assistance)`. | 56148884aa20f316ab9e6f0ab8a5e83f83669e01954894f6ca3d5f41039c413b | pending |
| D15-03 | datalib_mediajustice_em_map | `Electronic Monitoring Hotspot Map (MediaJustice Challenging E-Carceration project)` — an upstream project source published by `MediaJustice`. | 5394e9909ff52e7ec25148e812ed3f9858b8ff46961bf9dc22a574b709c48b6d | pending |
| D15-04 | datalib_public_safety_drones | `Public Safety Drones (Bard College Center for the Study of the Drone — law-enforcement / fire UAS dataset)` — an academic source published by `Bard College — Center for the Study of the Drone`. | f9945f1d73de08771f38f62846c9a6cc0495728e9af0c50c9c84396c07b0094c | pending |
| D15-05 | datalib_ring_neighbors_partnerships | `Ring/Neighbors Partnerships (EFF-compiled map of Ring law-enforcement partnerships — historical)` — an upstream project source published by `Electronic Frontier Foundation (upstream: Ring Inc.)`. | 9fd23507ed7098ce4ae0cb3a26e245cf25009c0fe4a873edd169d33c3e988e7c | pending |
| D15-06 | datalib_who_has_your_face | `Who Has Your Face? (EFF — government photo databases shared for facial recognition)` — an upstream project source published by `Electronic Frontier Foundation`. | ce871469b8b5ab122f20ee55340d4ea3a245e65cf3490faeb595eaf843a240c4 | pending |
| D15-07 | declarationcamera_be | `declarationcamera.be (BE national camera register)` — a government portal source. | d6b45e7523d732706e027eea94900a1cd216a15a3bb21610592d3ee5d2fb8b9a | pending |
| D15-08 | decp_fr | `DECP (FR procurement)` — a government portal source. | 48e1e557b2a6e71b65eefc05ff414cfa2a4e53103786a64f1d43ef67c7fc3a64 | pending |
| D15-09 | deflock | `DeFlock` — an upstream project source. | 8c887b69e4c3caee214e7270538c8aeff2799abd3eff08b4295f6f2046c8ba29 | pending |
| D15-10 | deflock_app_repo | `DeFlock — app repo (FoggedLens/deflock-app)` — an upstream project source. | e1e5c030fb888b4543c05c6a161d0b78a323761b7fa315f196facae3fadac4ea | pending |
| D15-11 | deflock_repo | `DeFlock — canonical repo (FoggedLens/deflock)` — an upstream project source. | b48a68888729a6afa3eb7e45ee9a51fef77c11e4099605b6c04f6b7e20105961 | pending |
| D15-12 | demandstar | `DemandStar — public agency bid portal` — a government portal source. | 87fc37f7b67cf0f0e63c87581f857e5661d575decc7796661d67453422e7ea00 | pending |
| D15-13 | denmark_politi_cctv | `Denmark National Police — official CCTV camera map` — a government portal source. | ddd18295b38bde4b574a9a5d36099ed0b3558aad9dfaa60876b0dc9dd16355db | pending |
| D15-14 | dhs_fusion_center_assessments | `DHS Fusion Center Assessment — National Network of Fusion Centers governance reports` — a government portal source. | 584cf212379abb5036c83a45f2fb5e453bc03421a0deacaebc2d6bc735e9f20d | pending |
| D15-15 | dhs_fusion_centers | `DHS fusion centers` — a government portal source. | afc86ebabaec998b814cbcdb3d73fd4371bdb5f52b2da7e824f7baecf0ce70e7 | pending |
| D15-16 | dhs_oig_reports | `DHS Office of Inspector General — oversight reports (fusion centers, grant programs, CBP/ICE surveillance)` — a government portal source. | d17ed014f4cd26ba134b6c31328c7f259d35494ddce5a9f31910bff93b3113e0 | pending |
| D15-17 | documentcloud | `DocumentCloud` — a records channel source. | f8d77b2dc18e525bcc4d7125f755cfca1ef69428832455ae03e3d4a017c703c4 | pending |
| D15-18 | dossier_okc | `City of Oklahoma City — ALPR dossier documents (usage page, council memo, amendment)` — a government portal source. | 9389b3586a350964692102ba5a9f80340372909faff0cf5fc9e9fb2a68205161 | pending |
| D15-19 | dossier_san_diego | `City of San Diego — surveillance-technology dossier documents (ASR, Ubicquia agreement, indexes)` — a government portal source. | c2d917ed24a6afb4ea32115104365bb2658f1145346c2e55648b111fcb4dc28d | pending |
| D15-20 | dossier_tulsa | `Tulsa Police Department — ALPR dossier documents (policies 113C/113E, MOU template)` — a government portal source. | b6c84a7c3e7148725436ea75858fe116e01073fba16a8b79c174df79686bce5b | pending |
| D15-21 | dot_511_ak | `511 Alaska camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Alaska Department of Transportation & Public Facilities (511 Alaska)`. | 21187d113cadf18a2d650192f73eb456666786cdba90f357a9d38bd1f13181c9 | pending |
| D15-22 | dot_511_al | `ALDOT traffic cameras (ArcGIS registry)` — a government portal source published by `Alabama Department of Transportation`. | e8ee9bee0493fe9aa8d3bdbc84850c2a57085a486beea207f3399b2e6f3de39e | pending |
| D15-23 | dot_511_az | `AZ511 camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Arizona Department of Transportation (AZ511)`. | 91116a5d7261d4c40e2704b262ab9c6f8b48abe098bf7c8a97dcb071ad19cd1e | pending |
| D15-24 | dot_511_ct | `CTroads camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Connecticut Department of Transportation (CTroads)`. | dac91357970f7935b21c3b166e3ee21ecae42dada6c752038cb004edd91d14d2 | pending |
| D15-25 | dot_511_dc | `DDOT traffic cameras (DC GIS registry)` — a government portal source published by `District Department of Transportation / DC GIS (OCTO)`. | d934c0ee65b1a437e8cfab37e8090b6b5cc9e43472cbf907d08b0181060815e2 | pending |

## Confirmation log

(none yet)
