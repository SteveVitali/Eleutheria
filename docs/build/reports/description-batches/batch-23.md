# Description batch 23 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D23-01 | statrep_de_diac | `Delaware Information and Analysis Center (DIAC) privacy SOP (28 C.F.R. Part 23)` — a government mandated disclosure source published by `Delaware Information and Analysis Center (Delaware State Police)`. | 6a3fb471160c9d62e6bc0539b191f80925e0dad7bcb4d80663888344564563c4 | pending |
| D23-02 | statrep_detroit_mi_frt_weekly | `Detroit Police Department Weekly Report on Facial Recognition (to the Board of Police Commissioners)` — a government mandated disclosure source published by `City of Detroit, MI - Detroit Police Department / Board of Police Commissioners`. | 3b7a28f2efc3569d44c65664ff453a80a32d022b1b37579f3427d1b7b2e4d7a6 | pending |
| D23-03 | statrep_fl_flhsmv_red_light | `Florida red light camera program annual reports (s. 316.0083(4), F.S. — FLHSMV summary + jurisdiction survey responses)` — a government mandated disclosure source published by `Florida Department of Highway Safety and Motor Vehicles (FLHSMV)`. | 40bac6007dd7329ded33b793fb8c2f5cb2f085e79de3c858739a02de84944006 | pending |
| D23-04 | statrep_fr_cnil_utilisation_de | `CNIL - 'Utilisation de BriefCam et d'autres logiciels d'analyse video par l'Etat et des communes : la CNIL prononce plus` — a government portal source published by `Commission nationale de l'informatique et des libertes (CNIL, France)`. | e78608eff24760715bb8edb943c21dd86ed95a3d5632492e0dbbf75e263a3b14 | pending |
| D23-05 | statrep_gb_enforcement_action | `Enforcement action (ICO register of enforcement notices, reprimands, monetary penalties)` — a government portal source published by `Information Commissioner's Office (UK)`. | e82db63b9adf71ba128d93a71a6750348ad054a6f0bf60b33bcbb522e147a80c | pending |
| D23-06 | statrep_gb_eng_seven_cctv_june_2026 | `CCTV Annual Report June 2026 (Sevenoaks District Council)` — a government portal source published by `Sevenoaks District Council`. | 0cd073ca5dabfad489152ced8e6a7df6ccb4bcb85532f9491f1a0aa16190d20f | pending |
| D23-07 | statrep_gb_sct_joint_assurance_review | `Joint assurance review: retrospective facial search (SBC/2025/02)` — a government portal source published by `Scottish Biometrics Commissioner (with HM Inspectorate of Constabulary in Scotland)`. | 73fdd38d6660587991e5673a0977605871751986dd910bb88bad89440b39451f | pending |
| D23-08 | statrep_gb_uk_algorithmic_transparency | `UK Algorithmic Transparency Recording Standard public-safety subset` — a government portal source published by `UK Government (GOV.UK — Algorithmic Transparency Recording Standard)`. | 132007bff32a63fc16ca1266230e968d801834faa0c33b2a07069939ee87704d | pending |
| D23-09 | statrep_hi_judiciary_interception | `Hawai'i Judiciary annual interception report (HRS § 803-47(b))` — a government mandated disclosure source published by `Hawai'i State Judiciary (communication to the Legislature)`. | d69bf4c9491dcf58ec016306a04da1a58b1fb49e0d78a63e3c583b5d326fc511 | pending |
| D23-10 | statrep_il_icjia_drone | `Illinois Freedom From Drone Surveillance Act annual report (725 ILCS 167)` — a government mandated disclosure source published by `Illinois Criminal Justice Information Authority`. | 4679e5b221a0894f5cc30fbb02ff508bc72465f2e7e4aaecfcb796503359ba42 | pending |
| D23-11 | statrep_il_isp_alpr | `Illinois State Police - Automated License Plate Reader Transparency Page and ALPR Annual Reports (Tamara Clayton Express` — a government mandated disclosure source published by `Illinois State Police, Division of Criminal Investigation`. | e5f95623bbb2fa50fc583044a7b17b408b3dd89c68bd98ef87604c73e3485f43 | pending |
| D23-12 | statrep_md_dls_mandated_reports | `Maryland Department of Legislative Services Library - Mandated Reports (State Government Article 2-1257 deposit and cata` — a government mandated disclosure source published by `Maryland General Assembly, Department of Legislative Services`. | 765a143e1b8cf41f2c53699741e74782e5b579039deb3c7714c590835e481c06 | pending |
| D23-13 | statrep_md_msp_css | `Maryland State Police cell-site simulator annual report (2020 Md. Laws chs. 222/223)` — a government mandated disclosure source published by `Maryland Department of State Police`. | 22b73fe866a4eed075e96cd2ad97156df1d19d3c429182305e13805056e1b9b5 | pending |
| D23-14 | statrep_me_dps_uav | `Annual Report of the Department of Public Safety on Maine Law Enforcement Agencies' Use of Unmanned Aerial Vehicles (25 ` — a government mandated disclosure source published by `Maine Department of Public Safety (report to the Joint Standing Committee on Judiciary), held by the Maine State Law and`. | de7e09d7ff673f8e146ff6c5361244731fcfe7be12c54e019ac8aaff8be73a2e | pending |
| D23-15 | statrep_mn_bca | `Agencies that use License Plate Readers (LPR) - Minnesota BCA statutory public list` — a government mandated disclosure source published by `Minnesota Department of Public Safety, Bureau of Criminal Apprehension`. | ccbf05e9d7260bc571ceb78e238b29c16ec11801b69084685a58a8d9074b1389 | pending |
| D23-16 | statrep_mn_court_interception | `Minnesota State Court Administrator interception report (Minn. Stat. § 626A.391 / Rules of Crim. Proc.)` — a government mandated disclosure source published by `Minnesota Judicial Branch, State Court Administrator's Office (filed with the Legislative Reference Library)`. | 580c665ef84f2ff1f837c312ccb1460f27a3ac5e2d42202fba96340b092e1be7 | pending |
| D23-17 | statrep_ne_crime_commission_alpr | `Nebraska Crime Commission - Automatic License Plate Reader Resources (per-agency ALPR Privacy Act reports, Neb. Rev. Sta` — a government mandated disclosure source published by `Nebraska Commission on Law Enforcement and Criminal Justice (Crime Commission)`. | 78e4e2bcf57364892d38a2432bf52fe85f56dae0838bbbd249b5ed34d7943a12 | pending |
| D23-18 | statrep_new_york_ny_nyc_doi_oig | `NYC DOI OIG-NYPD surveillance oversight` — a government portal source published by `NYC Department of Investigation — OIG-NYPD`. | d7e8a67b5fc5f8a7df281e0e78c31e89ae1ab6e7aa16de22c58173488037b879 | pending |
| D23-19 | statrep_pa_wzssc | `Pennsylvania Work Zone Speed Safety Camera (WZSSC) program annual report (75 Pa.C.S. § 3369(h)(4))` — a government mandated disclosure source published by `Pennsylvania Department of Transportation with the Pennsylvania Turnpike Commission and Pennsylvania State Police`. | 6f0942988949c55dc6585db190b1456c17ff69060f5a695193a2e5a74309c4bf | pending |
| D23-20 | statrep_seattle_wa_oig | `Seattle Office of Inspector General surveillance usage reviews (SMC 14.18)` — a government mandated disclosure source published by `Seattle Office of Inspector General (OIG)`. | 04ff8c4e46b75b7e74db45bc78c9941db06a752fd0ad44be540b5b612b325442 | pending |
| D23-21 | statrep_seattle_wa_sdot_ate | `Seattle automated traffic safety camera (ATSC) program annual reports (RCW 46.63.220)` — a government mandated disclosure source published by `City of Seattle, Seattle Department of Transportation`. | ce1a61edfc2b6fa74536d0cee785bbd0bdbcac60db71f4fe54f3397324589ace | pending |
| D23-22 | statrep_tx_ca_nm_ri_fl_il_eff_red_flag | `EFF Red Flag Machine — GoGuardian records research` — a government portal source published by `Electronic Frontier Foundation`. | 7a38e92c954b3731acdb70a02858d150ff8298d35ca9ea9f129e843d05213a03 | pending |
| D23-23 | statrep_tx_south_padre_island_faa | `FAA restricted-area rulemakings for CBP tethered aerostat sites (Federal Register)` — a government portal source published by `Federal Aviation Administration (via Federal Register)`. | 1af645b341e5ade538b2169207539c8899f79e87d30f2889ca8980311fb92bf3 | pending |
| D23-24 | statrep_us_2024_federal_agency | `2024 Federal Agency AI Use Case Inventory (consolidated CSV/XLS)` — a government portal source published by `Office of Management and Budget (via GitHub ombegov)`. | 5230e1abba6bd7e1a1aa1f88eb549780282b451f91afe017d32aa7d1c57475da | pending |
| D23-25 | statrep_us_dhs_ai_use | `DHS AI Use Case Inventory (2025)` — a government portal source published by `U.S. Department of Homeland Security (Office of the Chief Information Officer)`. | 6618d3c496e22d0b29f7d0330e29b9210840e4915962e6cb5d2f1735ca36b2ea | pending |

## Confirmation log

(none yet)
