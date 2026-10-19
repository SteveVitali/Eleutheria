# Fixture provenance — `tests/connectors/fixtures/statrep/` (P36.8 / R11-ACQ-12; P36.9a / R11-ACQ-13a)

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

**Part VIII note:** every literal a fixture claims emits is institutional and
aggregate — agency names, counts, statute citations, published fixed-location
strings. No plate, trip, per-person or officer-name literal exists in any
fixture, and none may be added.
