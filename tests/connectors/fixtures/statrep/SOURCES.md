# Fixture provenance — `tests/connectors/fixtures/statrep/` (P36.8 / R11-ACQ-12; P36.9a / R11-ACQ-13a; P36.9b / R11-ACQ-13b)

Every file in this directory is a **synthetic reconstruction** of the reviewed
upstream surface it models — written from the acquisition research notes
(I3/I4/I6/I9a candidates in
`docs/build/planning/2026-09-30-next-phase/research/` and the acquisition plan
rows `AP-T1-*`), never a re-hosted upstream capture (P8-2: documents are never
re-hosted; the connector emits derived facts + the upstream link). Where the
upstream document is large, the fixture carries the reviewed text-extract
shape (`*.txt`) — in a live acquisition the >1 MB original would be captured
upstream and its sha256 recorded on the artifact row; the committed fixture
stands in for the extraction layer only (§5.0).

| fixture | models | upstream surface (reviewed) |
|---|---|---|
| `wa_ago_index.html` | `statrep_wa_ago_alpr_registry` index | `https://www.atg.wa.gov/ALPR` — RCW 10.130 registration list (I9a-C036): page-carried registration rows; a `trail camera` row exercises the unmapped-literal path; a policy-link fan-out |
| `mn_bca_index.html` | `statrep_mn_bca` index (`lpr_agency_list`) | `https://dps.mn.gov/agencies-use-lprs-lpr` — Minn. Stat. 13.824 subd. 8(b) agency + fixed-location list (I3-C039); location strings stay literals |
| `ne_crime_index.html` | `statrep_ne_crime_commission_alpr` index | `https://ncc.nebraska.gov/automatic-license-plate-reader-resources` — per-agency 60-3206 filings (I9a-C011); agency rides the anchor |
| `ne_crime_report.txt` | a Nebraska per-agency annual report filing | the 60-3206(3)(a) report form shape — aggregate counts + retention + sharing fields |
| `il_isp_index.html` | `statrep_il_isp_alpr` index | `https://isp.illinois.gov/CriminalInvestigations/TransparencyPage` — 625 ILCS 5/11-208.3 reports (I9a-C019) |
| `md_dls_index.html` | `statrep_md_dls_mandated_reports` index | `https://dls.maryland.gov/library/mandated-reports` — the § 2-1257 deposit catalogue (I9a-C047); non-surveillance entries exercise the scope screen |
| `va_rga_index.html` | `statrep_va_rga` index | `https://rga.lis.virginia.gov/` — the Reports to the General Assembly deposit catalogue (I6-C040); same scope-screen shape |
| `va_vsp_spec.txt` | `statrep_va_vsp_alpr` filing | `https://vsp.es.virginia.gov/wp-content/uploads/2026/03/ALPR-Reporting-Requirements-v2.pdf` — the § 2.2-5517(J) required-metrics spec (I3-C042) |
| `va_vscc_report.txt` | `statrep_va_vscc_alpr` filing | `https://vscc.virginia.gov/2026/VSCC%20ALPR%20Report%20January%202026%20FINAL%20REVISED%20Jan%2021%202026.pdf` — the VSCC update report (I3-C043) |
| `vt_dps_report.txt` | `statrep_vt_dps_alpr` filing | `https://legislature.vermont.gov/assets/Legislative-Reports/2019-ALPR-Report.pdf` — the 23 V.S.A. § 1607 annual report (I9a-C012) |
| `austin_auditor_report.txt` | `statrep_austin_tx_auditor` filing | `https://services.austintexas.gov/edims/document.cfm?id=452710` — the May 2025 APD LPR audit (I9a-C042) |
| `co_frt_index.html` | `statrep_co_frt_accountability` index (`co_arvada_frt_accountability`) | `https://www.arvadaco.gov/917/Facial-Recognition-Technology` — the SB22-113 / C.R.S. 24-18-301..-309 accountability page (I4-C102 family; Arvada I4-C103 first target): the page carries the yearly use-statistics literal and links the filing under /DocumentCenter/ |
| `co_frt_arvada_report.txt` | an Arvada FR accountability-report filing | the DocumentCenter filing shape the index links — the filing's own `Technology:`/`Date:` fields + the 97-of-13,396 use literal |
| `wa_watech_index.html` | `statrep_wa_watech_frt` index | `https://watech.wa.gov/node/2066` — the RCW 43.386 TSB posting page (I4-C100): NOI + accountability-report links; the `biometric` NOI exercises the unmapped-literal path (SIG-ONTO-021) |
| `wa_watech_fr_accountability.txt` | a WaTech RCW 43.386 accountability-report filing | the accountability filing shape the TSB page posts — `Technology:`/`Date:` fields + the RCW 43.386 authority literal |
| `detroit_frt_index.html` | `statrep_detroit_mi_frt_weekly` index | `https://detroitmi.gov/boards/board-police-commissioners` — the DPD Directive 307.5-5.1 weekly-report posting surface (I4-C108); the agenda PDF exercises the `facial` document filter |
| `detroit_frt_weekly.txt` | a DPD weekly facial-recognition filing | the `251229 BOPC Facial Rec Report.pdf` shape — per-week + year-to-date search counts only; no per-incident fields, no officer names (Part VIII / §43.4) |
| `me_dps_uav_report.txt` | `statrep_me_dps_uav` filing | `https://lldc.mainelegislature.org/Open/Rpts/tl685_35_p23_2016.pdf` — the 25 M.R.S. § 4501 annual UAV-use report (I9b-C053); the statewide zero-use literal is the filing's own statement |
| `il_icjia_index.html` | `statrep_il_icjia_drone` index | `https://icjia.illinois.gov/about/publications/sfy-25-drone-surveillance-report` — the 725 ILCS 167 publications index (I4-C006); the firearms filing exercises the `/drone` path filter, the legacy `icjia.state.il.us` mirror the same-host rule |
| `il_icjia_report.txt` | an ICJIA SFY drone-surveillance filing | the SFY report shape — per-agency ownership rows are `inventory_entry` assertions (owning ≠ deploying; no use claim) |
| `mn_bca_uav_index.html` | `statrep_mn_bca` second index (`uav_annual_reports`) | `https://dps.mn.gov/divisions/bca/data-and-reports/uav-uav-annual-reports` — the Minn. Stat. 626.19 UAV annual-report series (I4-C005); the `lrl.mn.gov` mirror exercises the same-host rule |
| `mn_bca_uav_report.txt` | a BCA 626.19 UAV annual-report filing | the filing's own `Technology:` field types it `uas-unspecified` (never the source's LPR default); § 626.19 lands as `legal_authority`, the source-level § 13.824 citation does not stamp (`ordinance_literal_required`) |
| `wa_wtsc_index.html` | `statrep_wa_wtsc_ate` index | `https://wtsc.wa.gov/safe-driving/patient-driving/ase/` — the RCW 46.63.220(6) Automated Safety Enforcement page (I4-C067/068): the statewide report link + the municipal report links it enumerates; off-scope links exercise the scope/suffix/same-host screens |
| `wa_wtsc_ase_report.txt` | the WTSC statewide ASE filing | the 2026 statewide-report shape — the filing's own `Technology:`/`Date:` fields, the RCW 46.63.220 authority literal, the aggregate infraction count |
| `hi_interception_report.txt` | `statrep_hi_judiciary_interception` filing | `https://data.capitol.hawaii.gov/sessions//session2025/bills/JC35_.pdf` — the HRS § 803-47(b) communication to the Legislature (I9b-C078): the statutory "no applications" zero; appendix judge/prosecutor names are never extracted (§43.4) |
| `mn_court_interception.txt` | `statrep_mn_court_interception` filing | `https://www.leg.mn.gov/docs/2024/Mandated/241537.pdf` — the court administrator's interception/pen-register/mobile-tracking warrant report (I9b-C077): institution-level counts only |
| `md_msp_css_report.txt` | `statrep_md_msp_css` filing | `https://mdsp.prod.maryland.gov/media/290/download` — the Chapters 222/223 (2020) cell-site simulator annual report (I9b-C065): deployment/exigent aggregates only |
| `de_diac_privacy_sop.txt` | `statrep_de_diac` filing | `https://dediac.org/html/DIAC%20Privacy%20SOP.pdf` — the fusion center's published privacy SOP (I4-C274): a `policy_document` — governance claims only, never a use claim; typed `rtcc-unspecified` pending `fusion-center` (D-P36.9b-1) |
| `seattle_sdot_atsc_report.txt` | `statrep_seattle_wa_sdot_ate` filing | `https://seattle.gov/documents/Departments/SDOT/VisionZero/ATSC/2024_2025_ATSC_Annual_Report.pdf` — the ATSC program annual report (I4-C069): the appendix site literals emit verbatim `deployment_location` rows, never geocoded |
| `fl_flhsmv_index.html` | `statrep_fl_flhsmv_red_light` index | `https://www.flhsmv.gov/resources/cabinet-and-legislature-reports/red-light-camera-program-analysis/` — the s. 316.0083(4) cabinet-reports page (I9b-C056): `/pdf/cabinetreports/` + scope screens admit the FY reports only |
| `fl_flhsmv_rlc_report.txt` | an FLHSMV red-light camera summary filing | the FY summary report shape — the statute's own "traffic infraction detectors" literal types it `ate-red-light`; statewide violation aggregates only |
| `pa_wzssc_report.txt` | `statrep_pa_wzssc` filing | `https://workzonecameras.penndot.gov/wp-content/uploads/2026/05/2026-WZSSC-Annual-Report_04.02.2026.pdf` — the 75 Pa.C.S. § 3369(h)(4) annual report (I9b-C057); the oversized original lands as a text extract per §5.0 |
| `seattle_oig_index.html` | `statrep_seattle_wa_oig` index | `https://seattle.gov/inspector-general/reports` — the SMC 14.18 surveillance usage-review catalogue (SRC-012): the accountability-audit links exercise the scope screen |
| `seattle_oig_usage_review.txt` | an OIG usage-review filing | the usage-review shape — the reviewed subject agency is SPD (the operating department); program-level use statements, no officer/operator names (§43.4) |
| `dhs_pia_index.html` | `statrep_us_dhs_privacy_compliance` index (`dhs-pia-hub`) | `https://www.dhs.gov/privacy-impact-assessments` — the E-Government Act § 208 PIA hub (I4-C167): `/publication/` screen admits filing pages; nav links exercise it |
| `dhs_pia_telemetry.txt` | a DHS PIA filing | the DHS/CBP/PIA-080 commercial-telemetry assessment shape (I4-C260) — the filing's own `Technology:`/`Date:` literals + component id; no operational counts |
| `fr_sorn_cbp007_bci.txt` | a Federal Register SORN notice | `https://www.federalregister.gov/documents/2016/01/25/2016-01331/` — the DHS/CBP-007 Border Crossing Information notice (I3-C072): the verbatim "license plate readers" literal exercises the Part VIII suppression path |
| `fr_sorn_cbp006_ats.txt` | a Federal Register SORN notice | `https://www.federalregister.gov/documents/2012/05/22/2012-12396/` — the DHS/CBP-006 Automated Targeting System notice: the unmapped literal records on the artifact, mints no technology claim (SIG-ONTO-021) |

**Fixture digests (P36.9b):** the committed files' own sha256 (the extract
artifact's digest — for the oversized upstream models, PA WZSSC ~11.9 MB and
FL ~2.2 MB, the extract stands in for the extraction layer per §5.0 and the
original's sha256 lands on the artifact row at first live capture, never
re-hosted here):

- `wa_wtsc_index.html` sha256:31937a840d3d35d8803b55a42d84c0113caca3cee836afa2a178267684dcf850
- `wa_wtsc_ase_report.txt` sha256:aad9d31dcc86b1222a129077da829e26f3db1d8ead52746cfa0814b019dd693f
- `hi_interception_report.txt` sha256:6aa6b95c1abeb231aba5de164de92fa570f7e680100e65d7c7a61b1e169be40b
- `mn_court_interception.txt` sha256:51448a08786079bc61d9c69ac699ac4f8260ec2ee12468236965c7913faaa549
- `md_msp_css_report.txt` sha256:2b6bc688b3b709f1c480fb6172c82c3bdcb9bfced3546d811d2607554ebb928c
- `de_diac_privacy_sop.txt` sha256:9676518352501d31b4cc8789f15b5ad8987e8b36775afb0c302b2b609fcf8013
- `seattle_sdot_atsc_report.txt` sha256:f6d83320d4479454adcdc6c4eaed6b8a1f353e12ef4fffb779d119eef8448d67
- `fl_flhsmv_index.html` sha256:e01313a442a96b2724baa18cae149504b4828b7de4bc50409c00e511c0c35ed4
- `fl_flhsmv_rlc_report.txt` sha256:8d2829158990780e51d41cf24c2aa34aa01818b5c132d4b413e1144e4c766629
- `pa_wzssc_report.txt` sha256:6f754068eaba3aa5504765a7164f9432806acef311fd491f7e3b37687dc05d8a
- `seattle_oig_index.html` sha256:395d806ef6310b765d2918a8eb7747b6378209759330aa942ad08f0b3c06d24c
- `seattle_oig_usage_review.txt` sha256:3f802b41a8d3f2e678d3ed43123951c58de3b92c6893bc808cb9f1f44dcaca17
- `dhs_pia_index.html` sha256:d1de586dc87fbb2a765a02d17051cab7249fc86c0009f60c39d0a084f646634c
- `dhs_pia_telemetry.txt` sha256:64d2496d4152c719df751ce2a9540d8e71ba19a44e7190ada8a9daa24287953c
- `fr_sorn_cbp007_bci.txt` sha256:71933cd0c2e0726c5c1c4b2fe949ce3188bfb668f22c57af192ef1822b5c1bcd
- `fr_sorn_cbp006_ats.txt` sha256:1d8ff08e79b6fd8267c690c827b0ebc89d61d2ebeb8124770e89cc8f7cf42f05

**Part VIII note:** every literal a fixture claims emits is institutional and
aggregate — agency names, counts, statute citations, published fixed-location
strings. No plate, trip, per-person or officer-name literal exists in any
fixture, and none may be added.
