# Fixture provenance — `tests/connectors/fixtures/statrep/` (P36.8 / R11-ACQ-12)

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

**Part VIII note:** every literal a fixture claims emits is institutional and
aggregate — agency names, counts, statute citations, published fixed-location
strings. No plate, trip, per-person or officer-name literal exists in any
fixture, and none may be added.
