# Description batch 24 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D24-01 | statrep_md_msp_css | `Maryland State Police cell-site simulator annual report (2020 Md. Laws chs. 222/223)` — a government mandated disclosure source published by `Maryland Department of State Police`. | 22b73fe866a4eed075e96cd2ad97156df1d19d3c429182305e13805056e1b9b5 | pending |
| D24-02 | statrep_me_dps_uav | `Annual Report of the Department of Public Safety on Maine Law Enforcement Agencies' Use of Unmanned Aerial Vehicles (25 ` — a government mandated disclosure source published by `Maine Department of Public Safety (report to the Joint Standing Committee on Judiciary), held by the Maine State Law and`. | de7e09d7ff673f8e146ff6c5361244731fcfe7be12c54e019ac8aaff8be73a2e | pending |
| D24-03 | statrep_mn_bca | `Agencies that use License Plate Readers (LPR) - Minnesota BCA statutory public list` — a government mandated disclosure source published by `Minnesota Department of Public Safety, Bureau of Criminal Apprehension`. | ccbf05e9d7260bc571ceb78e238b29c16ec11801b69084685a58a8d9074b1389 | pending |
| D24-04 | statrep_mn_court_interception | `Minnesota State Court Administrator interception report (Minn. Stat. § 626A.391 / Rules of Crim. Proc.)` — a government mandated disclosure source published by `Minnesota Judicial Branch, State Court Administrator's Office (filed with the Legislative Reference Library)`. | 580c665ef84f2ff1f837c312ccb1460f27a3ac5e2d42202fba96340b092e1be7 | pending |
| D24-05 | statrep_ne_crime_commission_alpr | `Nebraska Crime Commission - Automatic License Plate Reader Resources (per-agency ALPR Privacy Act reports, Neb. Rev. Sta` — a government mandated disclosure source published by `Nebraska Commission on Law Enforcement and Criminal Justice (Crime Commission)`. | 78e4e2bcf57364892d38a2432bf52fe85f56dae0838bbbd249b5ed34d7943a12 | pending |
| D24-06 | statrep_new_york_ny_nyc_doi_oig | `NYC DOI OIG-NYPD surveillance oversight` — a government portal source published by `NYC Department of Investigation — OIG-NYPD`. | d7e8a67b5fc5f8a7df281e0e78c31e89ae1ab6e7aa16de22c58173488037b879 | pending |
| D24-07 | statrep_pa_wzssc | `Pennsylvania Work Zone Speed Safety Camera (WZSSC) program annual report (75 Pa.C.S. § 3369(h)(4))` — a government mandated disclosure source published by `Pennsylvania Department of Transportation with the Pennsylvania Turnpike Commission and Pennsylvania State Police`. | 6f0942988949c55dc6585db190b1456c17ff69060f5a695193a2e5a74309c4bf | pending |
| D24-08 | statrep_seattle_wa_oig | `Seattle Office of Inspector General surveillance usage reviews (SMC 14.18)` — a government mandated disclosure source published by `Seattle Office of Inspector General (OIG)`. | 04ff8c4e46b75b7e74db45bc78c9941db06a752fd0ad44be540b5b612b325442 | pending |
| D24-09 | statrep_seattle_wa_sdot_ate | `Seattle automated traffic safety camera (ATSC) program annual reports (RCW 46.63.220)` — a government mandated disclosure source published by `City of Seattle, Seattle Department of Transportation`. | ce1a61edfc2b6fa74536d0cee785bbd0bdbcac60db71f4fe54f3397324589ace | pending |
| D24-10 | statrep_tx_ca_nm_ri_fl_il_eff_red_flag | `EFF Red Flag Machine — GoGuardian records research` — a government portal source published by `Electronic Frontier Foundation`. | 7a38e92c954b3731acdb70a02858d150ff8298d35ca9ea9f129e843d05213a03 | pending |
| D24-11 | statrep_tx_south_padre_island_faa | `FAA restricted-area rulemakings for CBP tethered aerostat sites (Federal Register)` — a government portal source published by `Federal Aviation Administration (via Federal Register)`. | 1af645b341e5ade538b2169207539c8899f79e87d30f2889ca8980311fb92bf3 | pending |
| D24-12 | statrep_us_2024_federal_agency | `2024 Federal Agency AI Use Case Inventory (consolidated CSV/XLS)` — a government portal source published by `Office of Management and Budget (via GitHub ombegov)`. | 5230e1abba6bd7e1a1aa1f88eb549780282b451f91afe017d32aa7d1c57475da | pending |
| D24-13 | statrep_us_dhs_ai_use | `DHS AI Use Case Inventory (2025)` — a government portal source published by `U.S. Department of Homeland Security (Office of the Chief Information Officer)`. | 6618d3c496e22d0b29f7d0330e29b9210840e4915962e6cb5d2f1735ca36b2ea | pending |
| D24-14 | statrep_us_dhs_privacy_compliance | `DHS privacy compliance documents — Privacy Impact Assessment hub, component indexes, and named-program PIAs (E-Government Act § 208)` — a government mandated disclosure source published by `U.S. Department of Homeland Security, Privacy Office`. | bcd567c8d798a0cb5c685e18614cccc587382a6ce5ce75942e6572b6e6ea0101 | pending |
| D24-15 | statrep_us_ice_287_monthly | `ICE 287(g) monthly encounter reports (monthlyEncounter_<Mon><YYYY>.pdf, FY2020-21 encounterReport series)` — a government portal source published by `U.S. Immigration and Customs Enforcement, ERO`. | 678e6f36ae2d7bdd19e027244ebfb4ced4d5c10f625334e5e2d840a3977cc259 | pending |
| D24-16 | statrep_us_ice_287_participating | `ICE 287(g) Participating Agencies (XLSX)` — a government portal source published by `U.S. Immigration and Customs Enforcement, ERO`. | d04a7699398176e83edcabc0bb261cad49ec8cfdc325e57c231b3f458f74193a | pending |
| D24-17 | statrep_us_upturn_mass_extraction_2020 | `Upturn - Mass Extraction (2020), Appendix C: Total Amounts Spent on MDFTs (agency table)` — a government portal source published by `Upturn, Inc.`. | 2d1ed4792d2dd75d2f77bb426f414dd4ec592a7e8d7ad6efd20b1fb3f24199ca | pending |
| D24-18 | statrep_us_wiretap_summary_tables | `Wiretap Report (annual, 18 U.S.C. §2519) - summary tables Wire 1-9` — a government portal source published by `Administrative Office of the U.S. Courts`. | c151da5c0d3f1fc488691433a793fd117a7349ca799702c2d08768c0c7252e51 | pending |
| D24-19 | statrep_va_rga | `Virginia Reports to the General Assembly (RGA) - published documents` — a government mandated disclosure source published by `Virginia Division of Legislative Automated Systems (LIS)`. | 954862ff0f8631170e00a3adf76ae5c01c19516689ad8dbae224daffb90d18fa | pending |
| D24-20 | statrep_va_vscc_alpr | `Virginia State Crime Commission - Law Enforcement Use of ALPR Update (Jan 2026) and 2025 Annual Report chapter` — a government mandated disclosure source published by `Virginia State Crime Commission`. | c13e5a647ac4b514d106f0277e5bfc5b98690551115674a4ca32085f657cb9f1 | pending |
| D24-21 | statrep_va_vsp_alpr | `Virginia State Police - ALPR Reporting Requirements (v2, 2026-03) and annual aggregate ALPR report (2.2-5517(J))` — a government mandated disclosure source published by `Virginia Department of State Police, CJIS Data Analysis & Reporting Team`. | 5498f067a5db16e83791aede53cacbc1642407545a6e6d61b8c6c5591c31c737 | pending |
| D24-22 | statrep_vt_dps_alpr | `Vermont Department of Public Safety - annual report on Automated License Plate Recognition Systems (23 V.S.A. 1607) to t` — a government mandated disclosure source published by `Vermont Department of Public Safety (deposited with the Vermont General Assembly)`. | 1f4f3fdc62b4f761e23471500d830596e9df72f44e89559cafd466079e4a95eb | pending |
| D24-23 | statrep_vt_vermont_law_enforcement | `Vermont Law Enforcement Agency Drone Use report (20 V.S.A. § 4624)` — a government portal source published by `Vermont Department of Public Safety (filed with the Vermont Legislature)`. | f10a77b2dd1129a939a5747a6b23c211c533ec57f7003e04c7b8b38ec69ee1d8 | pending |
| D24-24 | statrep_wa_ago_alpr_registry | `Washington Attorney General's Office - Automated License Plate Reader (ALPR) System Registration: Registered ALPR System` — a government mandated disclosure source published by `Washington State Office of the Attorney General`. | b6bad2e7fc52da82a242a83b02627afd8b27ad0d876f4e19289f9fe24b6eaaf0 | pending |
| D24-25 | statrep_wa_watech_frt | `Facial Recognition · WaTech (Technology Services Board posting of FR Notices of Intent and Accountability Reports, ch. 4` — a government mandated disclosure source published by `Washington Technology Solutions (WaTech) / Technology Services Board, State of Washington`. | 54e067d283b1a2b5a4be90b4e6ab985e8c347e4590f09068b4bfd3f651078681 | pending |

## Confirmation log

(none yet)
