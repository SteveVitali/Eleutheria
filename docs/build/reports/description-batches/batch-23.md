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
| D23-01 | statrep_il_isp_alpr | Illinois State Police - Automated License Plate Reader Transparency Page and ALPR Annual Reports (Tamara Clayton Express — a government mandated disclosure source published by Illinois State Police, Division of Criminal Investigation. | 0efc724c7b544bf74c9c89f36cd23cbf97e29a87dfee37af38c6af7adacef09f | pending |
| D23-02 | statrep_md_dls_mandated_reports | Maryland Department of Legislative Services Library - Mandated Reports (State Government Article 2-1257 deposit and cata — a government mandated disclosure source published by Maryland General Assembly, Department of Legislative Services. | 80680ded4504fe68a996fed7cbb939123a27adf09065df88ee86e625ba535984 | pending |
| D23-03 | statrep_md_msp_css | Maryland State Police cell-site simulator annual report (2020 Md. Laws chs. 222/223) — a government mandated disclosure source published by Maryland Department of State Police. | 6063673efa80cd9a0a064084398fa21f92e45a08d78cbe034e1020fdef4660ee | pending |
| D23-04 | statrep_me_dps_uav | Annual Report of the Department of Public Safety on Maine Law Enforcement Agencies' Use of Unmanned Aerial Vehicles (25  — a government mandated disclosure source published by Maine Department of Public Safety (report to the Joint Standing Committee on Judiciary); held by the Maine State Law and. | 80e3e181251758d446d98bd8ab4dcc2d47b436fa4c70ae56a06c3ec091298832 | pending |
| D23-05 | statrep_mn_bca | Agencies that use License Plate Readers (LPR) - Minnesota BCA statutory public list — a government mandated disclosure source published by Minnesota Department of Public Safety, Bureau of Criminal Apprehension. | 45dc221f1b641b0af35519544dda7213506d492ae2539246e1ed128db15beaad | pending |
| D23-06 | statrep_mn_court_interception | Minnesota State Court Administrator interception report (Minn. Stat. § 626A.391 / Rules of Crim. Proc.) — a government mandated disclosure source published by Minnesota Judicial Branch, State Court Administrator's Office (filed with the Legislative Reference Library). | c204b4d76873878bbcf5f006759c373315e4e8bf3d59dfa6839d97fc7f7bfa46 | pending |
| D23-07 | statrep_ne_crime_commission_alpr | Nebraska Crime Commission - Automatic License Plate Reader Resources (per-agency ALPR Privacy Act reports, Neb. Rev. Sta — a government mandated disclosure source published by Nebraska Commission on Law Enforcement and Criminal Justice (Crime Commission). | 1a76a4471a2570745515fc4a3dae9b193c3a249472158d36ab59eba9ce64baca | pending |
| D23-08 | statrep_new_york_ny_nyc_doi_oig | NYC DOI OIG-NYPD surveillance oversight — a government portal source published by NYC Department of Investigation — OIG-NYPD. | c7898dee036c44f517544061b4dc29cbc2534d50dd146aaaf69883afd16a48ef | pending |
| D23-09 | statrep_pa_wzssc | Pennsylvania Work Zone Speed Safety Camera (WZSSC) program annual report (75 Pa.C.S. § 3369(h)(4)) — a government mandated disclosure source published by Pennsylvania Department of Transportation with the Pennsylvania Turnpike Commission and Pennsylvania State Police. | 2dc056a4da9031a5bc050e30b3689a74d87e33a2b3ac7fece77a3ac9cc39051c | pending |
| D23-10 | statrep_seattle_wa_oig | Seattle Office of Inspector General surveillance usage reviews (SMC 14.18) — a government mandated disclosure source published by Seattle Office of Inspector General (OIG). | ceeadbc22d611705297246cd4d514beea32284327d9bc77be5a81f4a0366e151 | pending |
| D23-11 | statrep_seattle_wa_sdot_ate | Seattle automated traffic safety camera (ATSC) program annual reports (RCW 46.63.220) — a government mandated disclosure source published by City of Seattle, Seattle Department of Transportation. | 122626b5a4a50bd50a27770d3182dafbf1421337b5f60c37aaed04f3d056cb44 | pending |
| D23-12 | statrep_tx_ca_nm_ri_fl_il_eff_red_flag | EFF Red Flag Machine — GoGuardian records research — a government portal source published by Electronic Frontier Foundation. | 93d99cc285f0636faae149fcda4a02e1998048daae0e9584a8240338f223e0c4 | pending |
| D23-13 | statrep_tx_south_padre_island_faa | FAA restricted-area rulemakings for CBP tethered aerostat sites (Federal Register) — a government portal source published by Federal Aviation Administration (via Federal Register). | 48149cb0d522742d56355bbe2233178f3696491a6a8c2bb7c68e8da8f21391b8 | pending |
| D23-14 | statrep_us_2024_federal_agency | 2024 Federal Agency AI Use Case Inventory (consolidated CSV/XLS) — a government portal source published by Office of Management and Budget (via GitHub ombegov). | 977bab924f14b4402a111bf91cb2b5fc54edf94ee72d7193ea70ab0c1c72efef | pending |
| D23-15 | statrep_us_dhs_ai_use | DHS AI Use Case Inventory (2025) — a government portal source published by U.S. Department of Homeland Security (Office of the Chief Information Officer). | 98beca40f9affede2b1c9d28ce76425cf4b99b7a39826633efe23e4f852ca7f6 | pending |
| D23-16 | statrep_us_dhs_privacy_compliance | DHS privacy compliance documents — Privacy Impact Assessment hub, component indexes, and named-program PIAs (E-Government Act § 208) — a government mandated disclosure source published by U.S. Department of Homeland Security, Privacy Office. | d936ef7ef59ec04a2df2492528a75eb85809a4d8f0790dd18b3fb293e92a724c | pending |
| D23-17 | statrep_us_ice_287_monthly | ICE 287(g) monthly encounter reports (monthlyEncounter_<Mon><YYYY>.pdf; FY2020-21 encounterReport series) — a government portal source published by U.S. Immigration and Customs Enforcement, ERO. | 9beafabf639fd6f4b7ed1a47b18b19e2782cd66153650fa789bbf3ce4db72704 | pending |
| D23-18 | statrep_us_ice_287_participating | ICE 287(g) Participating Agencies (XLSX) — a government portal source published by U.S. Immigration and Customs Enforcement, ERO. | 55283a30b899ba8a6327d3d505d00d41cd81af6b67704fbd2abbaff091d629fa | pending |
| D23-19 | statrep_us_upturn_mass_extraction_2020 | Upturn - Mass Extraction (2020), Appendix C: Total Amounts Spent on MDFTs (agency table) — a government portal source published by Upturn, Inc.. | f0ee6e933685701e61e830f69751c583dee1b049708ff5ca84bdab4c3021a455 | pending |
| D23-20 | statrep_us_wiretap_summary_tables | Wiretap Report (annual, 18 U.S.C. §2519) - summary tables Wire 1-9 — a government portal source published by Administrative Office of the U.S. Courts. | 2ccf9fedaca6ab44417a175a96dd93e8792c760c0463f35d7c4d8fdfba52a25d | pending |
| D23-21 | statrep_va_rga | Virginia Reports to the General Assembly (RGA) - published documents — a government mandated disclosure source published by Virginia Division of Legislative Automated Systems (LIS). | 8abcf2b99ed830bb48aba7fb12d43fd99e6a4c3c7958db59aa6aefdd7b2e4d1a | pending |
| D23-22 | statrep_va_vscc_alpr | Virginia State Crime Commission - Law Enforcement Use of ALPR Update (Jan 2026) and 2025 Annual Report chapter — a government mandated disclosure source published by Virginia State Crime Commission. | 5aa33939cdd4b889c49f7bab8c064e8f289247f470c8c2dddf578eaf20af1529 | pending |
| D23-23 | statrep_va_vsp_alpr | Virginia State Police - ALPR Reporting Requirements (v2, 2026-03) and annual aggregate ALPR report (2.2-5517(J)) — a government mandated disclosure source published by Virginia Department of State Police, CJIS Data Analysis & Reporting Team. | e076d08560459d0101c35ab1133e1f5b1afa123991dbfa74af515367e69f8048 | pending |
| D23-24 | statrep_vt_dps_alpr | Vermont Department of Public Safety - annual report on Automated License Plate Recognition Systems (23 V.S.A. 1607) to t — a government mandated disclosure source published by Vermont Department of Public Safety (deposited with the Vermont General Assembly). | 08c349cd5f926bba035771f3794982dfd13737acf40b3cf2cfdf52b981272cc2 | pending |
| D23-25 | statrep_vt_vermont_law_enforcement | Vermont Law Enforcement Agency Drone Use report (20 V.S.A. § 4624) — a government portal source published by Vermont Department of Public Safety (filed with the Vermont Legislature). | 3950a2fee8b938cbbeb85e722138351f1cee8c2c4efeb4489d5bdf9ba8dd088d | pending |

## Confirmation log

(none yet)
