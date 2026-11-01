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
| D22-01 | publicpurchase | `PublicPurchase — public agency bid portal` — a government portal source. | 2c6210fcb12ca7f3b11f0267f154dc927593c679007a7c13554ee7d49bc5e51d | pending |
| D22-02 | r_flocksurveillance | `r/FlockSurveillance` — a community source. | 4fe610cbb5e99bda47e7480a9c4a0c558b65ab7dab98cec89df525a0a567cc87 | pending |
| D22-03 | raa_prefectures | `RAA des préfectures (arrêtés préfectoraux)` — a government portal source. | 04907dc2f88758d9ccaa0415ab7ebcacc2410e571b8a54dd2e4f300142929efa | pending |
| D22-04 | ringmast4r_flock | `Ringmast4r/FLOCK` — a community source. | ebacd79d5852399a379ea7c47b327a6deac7be2fddff3f88ecada6b43d157ade | pending |
| D22-05 | rotterdam_cameraregister | `Rotterdam cameraregister — municipal camera disclosures` — a government portal source. | fe2060d91d70503686b4f6149515ed98ad969de7d0730dd3d9e07fcbe376d601 | pending |
| D22-06 | sam_gov | `SAM.gov` — a government portal source. | 36a49fdcbfab387104ee0de0ee49d24ba8a0baafc1ab6caacffc4473ed5bef7c | pending |
| D22-07 | sm_alpr | `none-below/sm-alpr` — an upstream project source. | 9058d70f537604d4243ae4f6b964d6239cf6f62db65355a1d2de3c583cf22f89 | pending |
| D22-08 | sourcewell | `Sourcewell` — a government portal source. | e8daa8f1fbdf4f38fd248adc2869a64779f4bad68423ff26939684d3dc04321e | pending |
| D22-09 | sous_surveillance_osm_import | `sous-surveillance.net → OSM import` — an upstream project source. | ad3372d8984401e7c876823bfdff5166fbb97f19619f0eb74cce88cb7b486531 | pending |
| D22-10 | state_alpr_statute_inventory | `State ALPR statute national inventory` — a government portal source. | 183ef3a2647e9914a03bd7a42eefe314a91cff379692accf539063a90fd541d0 | pending |
| D22-11 | state_alpr_statute_inventory_2026 | `State ALPR statute inventory — 2026 origin-verified refresh` — a government portal source. | 27dcb0ca0ce5a1547e002f2ca857acd37f673aa988031bc5a472bedc199e8e55 | pending |
| D22-12 | statrep_austin_tx_auditor | `City of Austin Office of the City Auditor - 'APD License Plate Reader Audit Report' (May 2025)` — a government mandated disclosure source published by `City of Austin, TX Office of the City Auditor`. | 5b621a19919ed18e20d6b80a6240a71fa0994e617ea5c72a08cc2fe0661d07c4 | pending |
| D22-13 | statrep_ca_california_auditor_alpr | `California State Auditor ALPR audit survey and follow-up` — a government portal source published by `California State Auditor`. | b607a475fadaba9709c17a2b84f99acf47e0c146d61375b8bce496009bb06688 | pending |
| D22-14 | statrep_ca_special_parliament_use | `Special report to Parliament: Police use of Facial Recognition Technology in Canada and the way forward (RCMP / Clearvie` — a government portal source published by `Office of the Privacy Commissioner of Canada`. | 3e073ab0dfb0a3a8ce9ebd06469bb7f99af22b9f63590a017dc3d5510b15f1c7 | pending |
| D22-15 | statrep_co_frt_accountability | `Colorado agency facial recognition accountability reports (C.R.S. 24-18-301 to -309, SB22-113)` — a government mandated disclosure source published by `Colorado state and local agencies using FR (statutory family, exemplar City of Arvada)`. | c56f244f9f7c0860ec8705fd67fc764fcad91916718746db0a88679bb85c37d6 | pending |
| D22-16 | statrep_de_diac | `Delaware Information and Analysis Center (DIAC) privacy SOP (28 C.F.R. Part 23)` — a government mandated disclosure source published by `Delaware Information and Analysis Center (Delaware State Police)`. | 6a3fb471160c9d62e6bc0539b191f80925e0dad7bcb4d80663888344564563c4 | pending |
| D22-17 | statrep_detroit_mi_frt_weekly | `Detroit Police Department Weekly Report on Facial Recognition (to the Board of Police Commissioners)` — a government mandated disclosure source published by `City of Detroit, MI - Detroit Police Department / Board of Police Commissioners`. | 3b7a28f2efc3569d44c65664ff453a80a32d022b1b37579f3427d1b7b2e4d7a6 | pending |
| D22-18 | statrep_fl_flhsmv_red_light | `Florida red light camera program annual reports (s. 316.0083(4), F.S. — FLHSMV summary + jurisdiction survey responses)` — a government mandated disclosure source published by `Florida Department of Highway Safety and Motor Vehicles (FLHSMV)`. | 40bac6007dd7329ded33b793fb8c2f5cb2f085e79de3c858739a02de84944006 | pending |
| D22-19 | statrep_fr_cnil_utilisation_de | `CNIL - 'Utilisation de BriefCam et d'autres logiciels d'analyse video par l'Etat et des communes : la CNIL prononce plus` — a government portal source published by `Commission nationale de l'informatique et des libertes (CNIL, France)`. | e78608eff24760715bb8edb943c21dd86ed95a3d5632492e0dbbf75e263a3b14 | pending |
| D22-20 | statrep_gb_enforcement_action | `Enforcement action (ICO register of enforcement notices, reprimands, monetary penalties)` — a government portal source published by `Information Commissioner's Office (UK)`. | e82db63b9adf71ba128d93a71a6750348ad054a6f0bf60b33bcbb522e147a80c | pending |
| D22-21 | statrep_gb_eng_seven_cctv_june_2026 | `CCTV Annual Report June 2026 (Sevenoaks District Council)` — a government portal source published by `Sevenoaks District Council`. | 0cd073ca5dabfad489152ced8e6a7df6ccb4bcb85532f9491f1a0aa16190d20f | pending |
| D22-22 | statrep_gb_sct_joint_assurance_review | `Joint assurance review: retrospective facial search (SBC/2025/02)` — a government portal source published by `Scottish Biometrics Commissioner (with HM Inspectorate of Constabulary in Scotland)`. | 73fdd38d6660587991e5673a0977605871751986dd910bb88bad89440b39451f | pending |
| D22-23 | statrep_gb_uk_algorithmic_transparency | `UK Algorithmic Transparency Recording Standard public-safety subset` — a government portal source published by `UK Government (GOV.UK — Algorithmic Transparency Recording Standard)`. | 132007bff32a63fc16ca1266230e968d801834faa0c33b2a07069939ee87704d | pending |
| D22-24 | statrep_hi_judiciary_interception | `Hawai'i Judiciary annual interception report (HRS § 803-47(b))` — a government mandated disclosure source published by `Hawai'i State Judiciary (communication to the Legislature)`. | d69bf4c9491dcf58ec016306a04da1a58b1fb49e0d78a63e3c583b5d326fc511 | pending |
| D22-25 | statrep_il_icjia_drone | `Illinois Freedom From Drone Surveillance Act annual report (725 ILCS 167)` — a government mandated disclosure source published by `Illinois Criminal Justice Information Authority`. | 4679e5b221a0894f5cc30fbb02ff508bc72465f2e7e4aaecfcb796503359ba42 | pending |

## Confirmation log

(none yet)
