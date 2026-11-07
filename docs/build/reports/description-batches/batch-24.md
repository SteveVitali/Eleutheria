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
| D24-01 | statrep_us_dhs_privacy_compliance | `DHS privacy compliance documents — Privacy Impact Assessment hub, component indexes, and named-program PIAs (E-Government Act § 208)` — a government mandated disclosure source published by `U.S. Department of Homeland Security, Privacy Office`. | bcd567c8d798a0cb5c685e18614cccc587382a6ce5ce75942e6572b6e6ea0101 | pending |
| D24-02 | statrep_us_ice_287_monthly | `ICE 287(g) monthly encounter reports (monthlyEncounter_<Mon><YYYY>.pdf, FY2020-21 encounterReport series)` — a government portal source published by `U.S. Immigration and Customs Enforcement, ERO`. | 678e6f36ae2d7bdd19e027244ebfb4ced4d5c10f625334e5e2d840a3977cc259 | pending |
| D24-03 | statrep_us_ice_287_participating | `ICE 287(g) Participating Agencies (XLSX)` — a government portal source published by `U.S. Immigration and Customs Enforcement, ERO`. | d04a7699398176e83edcabc0bb261cad49ec8cfdc325e57c231b3f458f74193a | pending |
| D24-04 | statrep_us_upturn_mass_extraction_2020 | `Upturn - Mass Extraction (2020), Appendix C: Total Amounts Spent on MDFTs (agency table)` — a government portal source published by `Upturn, Inc.`. | 2d1ed4792d2dd75d2f77bb426f414dd4ec592a7e8d7ad6efd20b1fb3f24199ca | pending |
| D24-05 | statrep_us_wiretap_summary_tables | `Wiretap Report (annual, 18 U.S.C. §2519) - summary tables Wire 1-9` — a government portal source published by `Administrative Office of the U.S. Courts`. | c151da5c0d3f1fc488691433a793fd117a7349ca799702c2d08768c0c7252e51 | pending |
| D24-06 | statrep_va_rga | `Virginia Reports to the General Assembly (RGA) - published documents` — a government mandated disclosure source published by `Virginia Division of Legislative Automated Systems (LIS)`. | 954862ff0f8631170e00a3adf76ae5c01c19516689ad8dbae224daffb90d18fa | pending |
| D24-07 | statrep_va_vscc_alpr | `Virginia State Crime Commission - Law Enforcement Use of ALPR Update (Jan 2026) and 2025 Annual Report chapter` — a government mandated disclosure source published by `Virginia State Crime Commission`. | c13e5a647ac4b514d106f0277e5bfc5b98690551115674a4ca32085f657cb9f1 | pending |
| D24-08 | statrep_va_vsp_alpr | `Virginia State Police - ALPR Reporting Requirements (v2, 2026-03) and annual aggregate ALPR report (2.2-5517(J))` — a government mandated disclosure source published by `Virginia Department of State Police, CJIS Data Analysis & Reporting Team`. | 5498f067a5db16e83791aede53cacbc1642407545a6e6d61b8c6c5591c31c737 | pending |
| D24-09 | statrep_vt_dps_alpr | `Vermont Department of Public Safety - annual report on Automated License Plate Recognition Systems (23 V.S.A. 1607) to t` — a government mandated disclosure source published by `Vermont Department of Public Safety (deposited with the Vermont General Assembly)`. | 1f4f3fdc62b4f761e23471500d830596e9df72f44e89559cafd466079e4a95eb | pending |
| D24-10 | statrep_vt_vermont_law_enforcement | `Vermont Law Enforcement Agency Drone Use report (20 V.S.A. § 4624)` — a government portal source published by `Vermont Department of Public Safety (filed with the Vermont Legislature)`. | f10a77b2dd1129a939a5747a6b23c211c533ec57f7003e04c7b8b38ec69ee1d8 | pending |
| D24-11 | statrep_wa_ago_alpr_registry | `Washington Attorney General's Office - Automated License Plate Reader (ALPR) System Registration: Registered ALPR System` — a government mandated disclosure source published by `Washington State Office of the Attorney General`. | b6bad2e7fc52da82a242a83b02627afd8b27ad0d876f4e19289f9fe24b6eaaf0 | pending |
| D24-12 | statrep_wa_watech_frt | `Facial Recognition · WaTech (Technology Services Board posting of FR Notices of Intent and Accountability Reports, ch. 4` — a government mandated disclosure source published by `Washington Technology Solutions (WaTech) / Technology Services Board, State of Washington`. | 54e067d283b1a2b5a4be90b4e6ab985e8c347e4590f09068b4bfd3f651078681 | pending |
| D24-13 | statrep_wa_wtsc_ate | `Washington automated safety enforcement reports (RCW 46.63.220(6)) — WTSC statewide report + municipal annual reports` — a government mandated disclosure source published by `Washington Traffic Safety Commission (with University of Washington), municipal reports filed by the ~29 operating jurisdictions`. | f0fbf90cc1c2e7f8c37789c11b82a27225873f1e9fe7edddf177a953418f0aed | pending |
| D24-14 | surveillance_under_surveillance | `Surveillance under Surveillance` — a community source. | b2f945ef71934ee1da08cb38765a9ff84d13f799443bbdce727b651233756b4e | pending |
| D24-15 | swagit | `Swagit — municipal meeting video/agenda portals` — a government portal source. | 8069b7eee3c48b412a7b91e64a80977d49c79ba0e076ad1dccd9d3d6765e8e4a | pending |
| D24-16 | technocarte_update | `Technocarte update` — an upstream project source. | 2d6e7193441ca385dc4b538d6b64c329ff715d04bdf9a444844f78a6b2ad58ad | pending |
| D24-17 | technopolice | `Technopolice` — an upstream project source. | 2e3f85b5fb7dad1f56594a6cc1930cfcab243d5cd84eda214b0f18c9f4d16e6a | pending |
| D24-18 | technopolice_forum | `Technopolice mapping discussion` — an upstream project source. | 73220f435b86717e0c160bab47897c739d734b31815afb249c8360c64a59d225 | pending |
| D24-19 | ted_eu | `TED — Tenders Electronic Daily (EU OJ S procurement notices)` — a government portal source. | 75935d6f13930e04a4ec05056f4126f7365a5a64c45d3d53a8bf6f4310e42c48 | pending |
| D24-20 | tips_usa | `TIPS` — a government portal source. | 811f1f59532e70975e351fb690e27de6a9d01afdf0556dcba332cb2e0b427523 | pending |
| D24-21 | uk_surveillance_camera_commissioner | `UK Biometrics & Surveillance Camera Commissioner — Surveillance Camera Code of Practice compliance & oversight` — a government portal source. | 8f5e39877fb41153f390eb0780a0a5021b9fa2cdd9b39630459fffc2adf65dd2 | pending |
| D24-22 | usaspending | `USAspending` — a government portal source. | cdadc87f686bbab30fcc64a5f945a26c1e863e99496e0119794aa8ccc321b148 | pending |
| D24-23 | wigle | `WiGLE` — a commercial source. | 340e94bb0c78b43ebb7e4fcfcb46eb71d3a2f26460532c4578bfe952d854b52d | pending |
| D24-24 | wikidata_sparql | `Wikidata SPARQL` — an upstream project source. | a71fa24b5fb56b95ee15d49f0df019dcb71ee0ae73e850787bfa2a2856cc2b72 | pending |
| D24-25 | wired_shotspotter_leak | `WIRED ShotSpotter sensor leak` — a news publisher source. | 9885eee4e10afb4992e55cccbe69b43a81a2230e77ba965d01fb850b6f74a96f | pending |

## Confirmation log

(none yet)
