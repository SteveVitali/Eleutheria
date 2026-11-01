# Description batch 22 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D22-01 | publicpurchase | PublicPurchase — public agency bid portal — a government portal source. | 0343f7fe40261c469c89e51033ad6416d6e2c3ac85d9e41d616d2cb6fc3477c1 | pending |
| D22-02 | r_flocksurveillance | r/FlockSurveillance — a community source. | 62204915928d525b5370d6ef21cb49c895bc20eb0c5dc5558f4440a54d1e0cb3 | pending |
| D22-03 | raa_prefectures | RAA des préfectures (arrêtés préfectoraux) — a government portal source. | 85152119536544d1063a178ede32b46bd926124f6d0a29592f5ed818fed7d3e8 | pending |
| D22-04 | ringmast4r_flock | Ringmast4r/FLOCK — a community source. | 1eb57c32063f89f3a5faa317c596d0d52018256691f67ebfde5fa779dadc845f | pending |
| D22-05 | rotterdam_cameraregister | Rotterdam cameraregister — municipal camera disclosures — a government portal source. | f5962becadd365849ecb56d9889ae3459a6c3005252bb72f8069c79beee9603e | pending |
| D22-06 | sam_gov | SAM.gov — a government portal source. | 2b6d2866ccf20738612688439623e198722b279757ce45e565d13b3307c0f292 | pending |
| D22-07 | sm_alpr | none-below/sm-alpr — an upstream project source. | fab486836ba4697d12c850eaed3ab2f82353714067fd888c8f4280245903d36c | pending |
| D22-08 | sourcewell | Sourcewell — a government portal source. | 7788e7c4ad9c95c3602a25b187d2825c77c70a201d42bc565b61607b6fd1a3dc | pending |
| D22-09 | sous_surveillance_osm_import | sous-surveillance.net → OSM import — an upstream project source. | 7328e8ff456e59211bc62f11ed9f7ab3ff4298d1698cd7934f1b4b2c686cb400 | pending |
| D22-10 | state_alpr_statute_inventory | State ALPR statute national inventory — a government portal source. | 873a97d8a129dc631f2c2dc896334efe2f644f6648a6830be56a33e318006147 | pending |
| D22-11 | state_alpr_statute_inventory_2026 | State ALPR statute inventory — 2026 origin-verified refresh — a government portal source. | 208215d2af26d5907659aeaa6cb7ecaf5da03e97625c63af58f120bc6c001c5c | pending |
| D22-12 | statrep_austin_tx_auditor | City of Austin Office of the City Auditor - 'APD License Plate Reader Audit Report' (May 2025) — a government mandated disclosure source published by City of Austin, TX Office of the City Auditor. | 5eb95e4ddb5ce29a6f6f108e336ed0f28162393069e45208e07464f1d81f6e19 | pending |
| D22-13 | statrep_ca_california_auditor_alpr | California State Auditor ALPR audit survey and follow-up — a government portal source published by California State Auditor. | e71f9c6a7798d25a0f6db79f05f8d743349b7cb52c8a6635b8816b89d9d4a19e | pending |
| D22-14 | statrep_ca_special_parliament_use | Special report to Parliament: Police use of Facial Recognition Technology in Canada and the way forward (RCMP / Clearvie — a government portal source published by Office of the Privacy Commissioner of Canada. | aff0fde79d4e7a3e9e345ec82ac42eed30b2c1c5945f37534072d396bf74c32e | pending |
| D22-15 | statrep_co_frt_accountability | Colorado agency facial recognition accountability reports (C.R.S. 24-18-301 to -309, SB22-113) — a government mandated disclosure source published by Colorado state and local agencies using FR (statutory family; exemplar City of Arvada). | 82e43efab147c512ad1a0ab3d685ea3bef830633dd37695a9fef3f9551531967 | pending |
| D22-16 | statrep_de_diac | Delaware Information and Analysis Center (DIAC) privacy SOP (28 C.F.R. Part 23) — a government mandated disclosure source published by Delaware Information and Analysis Center (Delaware State Police). | ae34fe2939213d408964e37735cd3796246ee39e896619873332fef71c379a55 | pending |
| D22-17 | statrep_detroit_mi_frt_weekly | Detroit Police Department Weekly Report on Facial Recognition (to the Board of Police Commissioners) — a government mandated disclosure source published by City of Detroit, MI - Detroit Police Department / Board of Police Commissioners. | 6d088973f1bf902601458f1986dfbacd8013f7b9241e13ff9585d916498397e9 | pending |
| D22-18 | statrep_fl_flhsmv_red_light | Florida red light camera program annual reports (s. 316.0083(4), F.S. — FLHSMV summary + jurisdiction survey responses) — a government mandated disclosure source published by Florida Department of Highway Safety and Motor Vehicles (FLHSMV). | b9bb5e3900257b612d160e2e5df0c6be16d707562311037851f9e7fe902e96ee | pending |
| D22-19 | statrep_fr_cnil_utilisation_de | CNIL - 'Utilisation de BriefCam et d'autres logiciels d'analyse video par l'Etat et des communes : la CNIL prononce plus — a government portal source published by Commission nationale de l'informatique et des libertes (CNIL, France). | 5601bdabed4557fba604de1e90c1c996f05ca2593a40ee7c83833e263a81af35 | pending |
| D22-20 | statrep_gb_enforcement_action | Enforcement action (ICO register of enforcement notices, reprimands, monetary penalties) — a government portal source published by Information Commissioner's Office (UK). | 96701993114b07b3527f7929499e194613010880f6c610a28c69b25678cf660e | pending |
| D22-21 | statrep_gb_eng_seven_cctv_june_2026 | CCTV Annual Report June 2026 (Sevenoaks District Council) — a government portal source published by Sevenoaks District Council. | f8a7526dcbd2737a477cfadc5e811ff4a127e174a08eb07aa9b8577f941a4bbd | pending |
| D22-22 | statrep_gb_sct_joint_assurance_review | Joint assurance review: retrospective facial search (SBC/2025/02) — a government portal source published by Scottish Biometrics Commissioner (with HM Inspectorate of Constabulary in Scotland). | 58c84cf3ca754f4009743676fea472da15205528b0472b32cea86da3867b3df1 | pending |
| D22-23 | statrep_gb_uk_algorithmic_transparency | UK Algorithmic Transparency Recording Standard public-safety subset — a government portal source published by UK Government (GOV.UK — Algorithmic Transparency Recording Standard). | c42dd0e0c2adf46f8719c7d24689880a208b2abc3e3a93cbcdb2ea91da794f7c | pending |
| D22-24 | statrep_hi_judiciary_interception | Hawai'i Judiciary annual interception report (HRS § 803-47(b)) — a government mandated disclosure source published by Hawai'i State Judiciary (communication to the Legislature). | 5086ba0e0120cc4f6051cc861e9b0513a12fc1dc58913c279fecbb450862c9ca | pending |
| D22-25 | statrep_il_icjia_drone | Illinois Freedom From Drone Surveillance Act annual report (725 ILCS 167) — a government mandated disclosure source published by Illinois Criminal Justice Information Authority. | fd936b1c8dc1f2f0a698fd54318e13a1535dc40210a20a51b21f894e7208a82e | pending |

## Confirmation log

(none yet)
