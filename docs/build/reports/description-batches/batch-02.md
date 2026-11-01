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
| D02-01 | atlas_about | Atlas about / scope boundary — an upstream project source. | 3d72ddb21f01d54eb8a91be398c5a7c77820cd6e4f37c104d0dd5edfe88cb8ef | pending |
| D02-02 | atlas_data_library | Atlas Data Library — an upstream project source. | 3b1a754cc018077792571aec56b19f9da57ef865baf06824f3daaaac24870f7f | pending |
| D02-03 | atlas_methodology | Atlas methodology — an upstream project source. | 855aa9f98c6c02abbb54f428079c07c39ab66d317b013cfe9b0472883c67aefc | pending |
| D02-04 | austria_vidreg | Austria VidReg — video-surveillance register — a government portal source. | a3f34ca9083cd174111eb439785df84d2c2b7d41e3f718fdf34a7012dcce3dde | pending |
| D02-05 | axon_community_connect | Axon Community Connect — a vendor site source. | 2f177a68faefc6c6c4b2d45f0f43ce893fe128b710a7714904456045e37f78c0 | pending |
| D02-06 | axon_connect | Axon Fusus Connect <Place> sites — a vendor site source. | f5f527a0b6777f7d8d9aed8caca1caff1a5777dcaf9ec9fbda5995d2011ecbc2 | pending |
| D02-07 | bidnet_direct | BidNet Direct — public agency bid portal — a government portal source. | 7f3a2b2c8816ca75a37b1489871bebfec2af98dbcfa4436bcebe474b05d806c0 | pending |
| D02-08 | boarddocs | BoardDocs — a government portal source. | 2a1dc9ea1020b1b852acae37818fadf57325dc75db4f35415f34a04f8336b5d5 | pending |
| D02-09 | bonfire | Bonfire — per-tenant procurement portals (*.bonfirehub.com) — a government portal source. | 7fbd16fc118c952140387077eef4d4f2a4709588dea37d1d09b4d55dec95f675 | pending |
| D02-10 | buyboard | BuyBoard — a government portal source. | 43877b8a3b1bc94ca245043d444da333715bbcd2bc2da096ded2bdf2c867eb9c | pending |
| D02-11 | ca_sharing_visualization | CA sharing visualization (Reddit) — a news publisher source. | 1008c9490c2980b3b2f45a92b18333a49991b6bb352cae8653dbd79fa46d51b9 | pending |
| D02-12 | ca_state_auditor | California State Auditor — ALPR audit 2019-118 index + surveys (SRC-011) — a government portal source. | ef8458b07983c0809ab1e23dfbe8033e91fcdabd184f0c9251ce4b47fa009cc0 | pending |
| D02-13 | camreg_achd_id | Ada County Highway District traffic cameras (ArcGIS registry) — a government portal source published by Ada County Highway District, Idaho. | 010fbf7e9a039c8560e9493b6a2369ad892e5fd7194c364458e707f862cf6f7b | pending |
| D02-14 | camreg_act_au | ACT traffic safety cameras (Socrata open-data registry) — a government portal source published by ACT Government Justice and Community Safety. | 1c7f32d6563e92b3d87cfd66ebc6944d41b18f2a4cffebbe8ad7a935d317c08a | pending |
| D02-15 | camreg_alabaster_al_lpr_cameras | LPR_Cameras (City of Alabaster, AL staff account) — a government portal source published by City of Alabaster, AL (city-staff account). | c2c17afd35569870fdd7106fcc645511eaffff27714c99a5c6f0a71acbf1c039 | pending |
| D02-16 | camreg_amber_kh | Traffic monitoring cameras (ArcGIS registry) — a government portal source published by ArcGIS community-published traffic-camera registry. | e6f281ad9669899f4705388f4cc8d13caae438ee45e51439d1cd2fabb2afba1b | pending |
| D02-17 | camreg_apram_pt | Madeira CCTV cameras (APRAM ArcGIS registry) — a government portal source published by APRAM — Agência Regional para o Ambiente, Portugal. | c552fcd9738dd8a28dd6c67f6d266619addf83529781864672703013529c8668 | pending |
| D02-18 | camreg_arc_1975641302 | CCTV locations registry (ArcGIS, anonymous publisher) — a government portal source published by ArcGIS community-published CCTV registry. | 42bd7e8df1c05a11dc769a0813858223872014cfcb6d3a733495d91d0e39a77e | pending |
| D02-19 | camreg_arlington_va | Arlington County traffic + photo enforcement cameras (ArcGIS registry) — a government portal source published by Arlington County DES. | 31433cc5950a5a5cba734ce8e984c8c577d0265c59b7963ec581e6c5c25ac775 | pending |
| D02-20 | camreg_au_ckan_package_search | data.gov.au CKAN package_search — CCTV (164 hits) — a government portal source published by data.gov.au (Australian Government; per-dataset publishers). | 7c56f1455d04bb0eb9de26ed2d1c0478ae313f6363ab9aaaeb7848df69c8fee5 | pending |
| D02-21 | camreg_au_nsw_sydney_street_safety | Street safety cameras — a government portal source published by City of Sydney. | 943aa30245dde77161a056de6e0cb6e09f0d25aa9a504c825b84722ed871cc96 | pending |
| D02-22 | camreg_au_qld_towns_cctv_camera_register | CCTV Camera Register — a government portal source published by Townsville City Council. | 736e21a8f926beece6bccc8c3d166fd11aa58e37b1e52da3c371d33b1dce55c5 | pending |
| D02-23 | camreg_au_tas_emergency_closed_circuit | Emergency Services - Closed Circuit Television Camera (CCTV) Coverages — a government portal source published by Tasmanian Government (theLIST). | a6cb837b7167edc4066ab966c36fe4b38e5db3a1226b1c6dbbea44d2bb9fd10c | pending |
| D02-24 | camreg_au_tas_hobar_security_camera | Security Camera — a government portal source published by City of Hobart. | d34c7da3fff088941a0fcbd323bacf1d4eead4a18b91b4ebc7a2308caac64cd2 | pending |
| D02-25 | camreg_au_vic_ballarat_cctv_cameras | Ballarat CCTV Cameras — a government portal source published by City of Ballarat. | 9bee247af7891b594dac8e71e3f66326b6533b9c4a5b6b97cd6278b6f0af47c0 | pending |

## Confirmation log

(none yet)
