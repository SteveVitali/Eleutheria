# Description batch 02 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D02-01 | aspi_mapping_chinas_tech_giants | `Mapping China's Tech Giants (ASPI)` — an academic source. | 1253544de3febff373d35d3bcf35a5e727252bda4f9e1e21497385f72fa5ca39 | pending |
| D02-02 | atlas_about | `Atlas about / scope boundary` — an upstream project source. | 48133c549bd678bf1aeb9fd86643f3ce5adc7d5fd79f5beea4b82758930652b6 | pending |
| D02-03 | atlas_data_library | `Atlas Data Library` — an upstream project source. | 74580886d47ee8a02111b5f849c4d432028cda0410c2c505c4d6dc1e6b7328df | pending |
| D02-04 | atlas_methodology | `Atlas methodology` — an upstream project source. | ec47f78b35878cb58e8a7edca20104e19ed6c43586420d5779d074f5f6095582 | pending |
| D02-05 | austria_vidreg | `Austria VidReg — video-surveillance register` — a government portal source. | 28ab3b3fff7fdf5acd65eb05df88941a23ac1dc86f4e92b89832af41fb18a913 | pending |
| D02-06 | axon_community_connect | `Axon Community Connect` — a vendor site source. | 2448f11de37aae991bed5523373702c1b132e5399b35fa31f91ecfb36e15101c | pending |
| D02-07 | axon_connect | `Axon Fusus Connect <Place> sites` — a vendor site source. | 5b950fb5626c5923cd30157579eb20bc4cebdee5704a2af4ce49dc748106ec28 | pending |
| D02-08 | bidnet_direct | `BidNet Direct — public agency bid portal` — a government portal source. | 4f182832e6fb3e55829c150bd01c7659e9e7e33044e7c48bc775398ce593ec80 | pending |
| D02-09 | boarddocs | `BoardDocs` — a government portal source. | f87135cc5d22d9d9300bec8348d0bd003f38834ddbdfe1e62a957692cbadfa89 | pending |
| D02-10 | bonfire | `Bonfire — per-tenant procurement portals (*.bonfirehub.com)` — a government portal source. | df9a7fce3d2e5e6c9e5dbb08f168659e9bbcaa50cc60fee6c9ecebcdef39505f | pending |
| D02-11 | buyboard | `BuyBoard` — a government portal source. | fc45746832f17f1871d1a7efa46ae5205fdeb20e8599e240a8dfe2cd5c461395 | pending |
| D02-12 | ca_sharing_visualization | `CA sharing visualization (Reddit)` — a news publisher source. | e74c88435684613438271d950e2a4574e67773df0491fb38251f05b1c5149c07 | pending |
| D02-13 | ca_state_auditor | `California State Auditor — ALPR audit 2019-118 index + surveys (SRC-011)` — a government portal source. | 99e938482bb56602cf628c1f1eb9810d8f942ba2aacf97f303d920062e3f5dc1 | pending |
| D02-14 | camreg_achd_id | `Ada County Highway District traffic cameras (ArcGIS registry)` — a government portal source published by `Ada County Highway District, Idaho`. | 3c5f0b704e8f802e7b7cc3a4e7ee7083e40835489ab1c761d494f2a5c8a2f2cb | pending |
| D02-15 | camreg_act_au | `ACT traffic safety cameras (Socrata open-data registry)` — a government portal source published by `ACT Government Justice and Community Safety`. | c2e780720badf6217f0028774e22491531b0645fbe6fd2233903330318584887 | pending |
| D02-16 | camreg_alabaster_al_lpr_cameras | `LPR_Cameras (City of Alabaster, AL staff account)` — a government portal source published by `City of Alabaster, AL (city-staff account)`. | e7450a584564989d2dab3438d78a6c86845c4d26cc845286b955678d702e937f | pending |
| D02-17 | camreg_amber_kh | `Traffic monitoring cameras (ArcGIS registry)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | f787eb0c25b627537989891aa7adab5fd5fd3bbbc9b8cad7095110366b480af7 | pending |
| D02-18 | camreg_apram_pt | `Madeira CCTV cameras (APRAM ArcGIS registry)` — a government portal source published by `APRAM — Agência Regional para o Ambiente, Portugal`. | 9587daace2cdee789259399e4e41c12fbfddc9a147d1ecc1ef28f9a15e29ccf7 | pending |
| D02-19 | camreg_arc_1975641302 | `CCTV locations registry (ArcGIS, anonymous publisher)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 814cba8c5f7ce1ac18a79267c9719e44e7e77901c065446956144c370790ff6c | pending |
| D02-20 | camreg_arlington_va | `Arlington County traffic + photo enforcement cameras (ArcGIS registry)` — a government portal source published by `Arlington County DES`. | 5320514c2d71c7044cfc966e3bd360a8e45bf062175b91c91d2c5857a9bd17b2 | pending |
| D02-21 | camreg_au_ckan_package_search | `data.gov.au CKAN package_search — CCTV (164 hits)` — a government portal source published by `data.gov.au (Australian Government, per-dataset publishers)`. | 97f78bc449970346e06ac549121a821cbab8897381e138bbac430356a20a88db | pending |
| D02-22 | camreg_au_nsw_sydney_street_safety | `Street safety cameras` — a government portal source published by `City of Sydney`. | bf1d62389f94a371030111125dbc3a249af809b19ba9168f2d5bbcedc4e65c39 | pending |
| D02-23 | camreg_au_qld_towns_cctv_camera_register | `CCTV Camera Register` — a government portal source published by `Townsville City Council`. | d64b64f8492fd6a463aed12ca7b1d75a69f69b9b410ca3391edf7be74449666f | pending |
| D02-24 | camreg_au_tas_emergency_closed_circuit | `Emergency Services - Closed Circuit Television Camera (CCTV) Coverages` — a government portal source published by `Tasmanian Government (theLIST)`. | b1cf729d89d577b0a1000d41444edba952a2aaa522575df131de23a347b531e3 | pending |
| D02-25 | camreg_au_tas_hobar_security_camera | `Security Camera` — a government portal source published by `City of Hobart`. | 3bbb8d2bdff565fbd57e4e596fc95a6c91e1a42e09a23cbe92fbc7a241adfaad | pending |

## Confirmation log

(none yet)
