# Oversight-report fixtures — `tests/connectors/fixtures/oversight_reports/` (P31.12 / BREADTH.1)

Committed captures for the four P29.3 rights-flipped accountability-breadth
sources, all running the `accountability` connector's `oversight_report` path
(targeted report lookup — one reviewed published document per target, never an
index, SIG-INGEST-036/037). The fixtures are never fetched live; the connector's
post-capture stages read the committed bytes only.

| fixture | source | reviewed document | canonical URL | retrieved |
|---|---|---|---|---|
| `gao-21-518.html` | `gao_surveillance_reports` | GAO-21-518, "Facial Recognition Technology: Federal Law Enforcement Agencies Should Better Assess Privacy and Other Risks" (published 2021-06-03) | `https://www.gao.gov/products/gao-21-518` | 2026-09-26 via the public Wayback capture of the canonical URL |
| `oig-09-12.pdf` | `dhs_oig_reports` | OIG-09-12, "DHS' Role in State and Local Fusion Centers Is Evolving" (Dec 2008) | `https://www.oig.dhs.gov/sites/default/files/assets/Mgmt/OIG_09-12_Dec08.pdf` | 2026-09-26 (HTTP 200) |
| `fusion-assessment-2021.pdf` | `dhs_fusion_center_assessments` | "2021 National Network of Fusion Centers Assessment — Summary of Findings" (FY2021) | `https://www.dhs.gov/sites/default/files/2022-12/2021%20Fusion%20Centers%20Assessment%20Summary%20of%20Findings.pdf` | 2026-09-26 (HTTP 200) |
| `bscc-ar-22-23.html` | `uk_surveillance_camera_commissioner` | Biometrics and Surveillance Camera Commissioner Annual Report 2022/2023 (published 2024-01-24) | `https://www.gov.uk/government/publications/biometrics-and-surveillance-camera-commissioner-report-2022-to-2023/biometrics-and-surveillance-camera-commissioners-annual-report-2022-to-2023-accessible` | 2026-09-26 (HTTP 200) |

Honesty notes:

- **GAO access posture.** `www.gao.gov` answers programmatic egress with HTTP
  403 (a NetScaler WAF challenge) as of 2026-09-25 — for the product page and
  the report PDF alike. The fixture is an excerpted capture of the page as
  served through the public Wayback Machine; the reviewed `live_targets.toml`
  row keeps the canonical URL and records the WAF posture in `review_note`. A
  hosted run that sees the same challenge records `access_restricted` honestly
  — SIG never defeats a challenge (SIG-INGEST-013, GL-GATE-08).
- **The HTML fixtures are trimmed excerpts** — the pages' real `<title>`, title
  block, metadata line, and lead text, verbatim; navigation/annex boilerplate
  removed. The reviewed `literals` in `live_targets.toml` are all present in
  the committed bytes.
- **The PDF fixtures are deterministic one-font PDFs** (the
  `tests/support.py::minimal_pdf` builder, committed as bytes) carrying the
  reports' verbatim cover/preface text — the full documents are ~3 MB /
  ~1.2 MB and are not committed. This is the same convention the CCOPS
  disclosure fixtures use for PDF-only surfaces
  (`tests/connectors/fixtures/ccops/SOURCES.md`).
- **Rights.** The GAO and both DHS documents are US-federal-government works
  (CC0-1.0, 17 U.S.C. §105; the P29.3 GL-GATE-07 packets). The GOV.UK page is
  Crown copyright under the Open Government Licence v3.0, carried under the
  operator-accepted `LicenseRef-OperatorAccepted-DBRight` basis — SIG derives
  facts + citations only, never re-hosts the document; the committed fixture
  is a trimmed excerpt for interpretation testing.
