# CCOPS fixture provenance — `tests/connectors/fixtures/ccops/`

Every fixture below excerpts a **public, legally-mandated** municipal
surveillance-ordinance disclosure (source class `government_mandated_disclosure`,
SIG-INGEST-049). The fixtures are committed excerpted captures — **never fetched
live** by the connector (all three sources stay `ingestion_permitted=false`,
HG-03; a `run --mode live` REFUSES at the loader gate, exit 3). Facts are verbatim
or paraphrased-faithful to the cited documents as retrieved **2026-08-20**
(R3 findings F3.19–F3.27, `docs/research/R3_eff_atlas_and_accountability.md`).

| fixture | disclosure | public URL | retrieved |
|---|---|---|---|
| `seattle_sir.json` | Seattle SPD **ALPR Surveillance Impact Report** under SMC 14.18 — the fixed ~50-field questionnaire (F3.20); Fiscal 1.1/1.2 cost tables sit blank (mandated ≠ populated); Fiscal 1.4 names the Seattle Police Foundation grant | `https://www.seattle.gov/Documents/Departments/Tech/Privacy/Final-2017-SIRs/SPD-ALPR-SIR-2017.pdf` (hub: `https://www.seattle.gov/tech/data-privacy/surveillance-technology`) | 2026-08-20 |
| `nyc_post_iup.json` | NYPD **POST Act impact & use policy** for ALPR — one of the 42 `post-final/*.pdf` policies carrying the synchronised 2026-02-04 revision (F3.24); the declared 10-field schema (retention, external access, audit & oversight, disparate impact, …) | `https://www.nyc.gov/site/nypd/about/about-nypd/policy/post-act.page` | 2026-08-20 |
| `sf_biannual_inventory.json` | SF **Biannual Surveillance Technology Inventory Report** (Chapter 19B), 2026-03-02, covering 2025-09-02→2026-03-01 — a representative excerpt of the four appendices (incl. the real Appendix C row and named Appendix D technologies) + the verbatim compliance breakdown (66% approved / **26% in use without an approved policy** = 37 technologies / 9 departments) (F3.21) | `https://media.api.sf.gov/documents/March_2_2026_Biannual_Surveillance_Technology_Inventory_Report.pdf` (index: `https://www.sf.gov/surveillance-technology-inventory`) | 2026-08-20 |

Honesty notes:

- All three outputs are **PDF only** — no CCOPS jurisdiction publishes a
  machine-readable inventory (F3.26); the fixture JSON is the pre-structured
  capture of the document facts, not a pretended API.
- The SF appendix **row set is a representative excerpt** (the report's real
  categories and named technologies); the compliance figures are the report's
  own published numbers, preserved verbatim as `raw_value`.
- Seattle's SIR is a **pre-acquisition commitment** document: it authorizes and
  constrains; it does not report measured use — no `disclosure_use` claim may
  come from it (`procured ≠ deployed`).

## P25.5 live-extraction fixtures (added 2026-09-17)

| fixture | disclosure | shape |
|---|---|---|
| `post_act_index.html` | NYC POST Act index page — the discovery surface for the 42 `post-final/*.pdf` IUP filings | Index HTML carrying the POST Act + "New York City Council" literals, three spec-matching filing links, and deliberately non-matching links (off-host, non-filing) |

The adapter resolves spec-matching links into bounded `disclosure_document`
targets (`max_documents` in `live_targets.toml`); a captured filing is read via
`pdf_text`/`selector_template`, and its claims carry page/byte locators into the
captured bytes. The IUP body text in tests is built by
`tests/support.py::minimal_pdf` — a deterministic one-font PDF — rather than a
committed binary.

## P31.13 (BREADTH.2) live-extraction fixtures (added 2026-09-26)

Three further CCOPS municipalities whose P29.3 GL-GATE-07 rights packets
flipped (LicenseRef-PublicRecord-FactualCompilation). Each fixture is a
committed **excerpt** of the reviewed index surface — the linked filing hrefs
and anchor texts are the page's own published literals verbatim; surrounding
page chrome is elided. All probed live 2026-09-26 (HTTP 200).

| fixture | disclosure index | canonical URL | retrieved |
|---|---|---|---|
| `oakland_pac_index.html` | Oakland **Privacy Advisory Commission** filing index — OMC Chapter 9.64; links every §9.64 filing under `/files/assets/city/v/1/boards-amp-commissions/documents/pac/*.pdf`: the ordinance itself plus `<technology> Annual Report (YYYY)` filings (ALPR 2019–2021, ShotSpotter 2020–2021, Mobile ID 2020) | `https://www.oaklandca.gov/Government/Boards-Commissions/Privacy-Advisory-Commission` | 2026-09-26 |
| `cambridge_legifile_index.html` | Cambridge **IQM2 LegiFile detail** page (ID 18518 — the Chapter 2.128 surveillance-oversight ordinance item); the `FileOpen.aspx?Type=4&ID=14080` attachment is the combined citywide **Annual Surveillance Report 02-27-2023** | `https://cambridgema.iqm2.com/Citizens/Detail_LegiFile.aspx?ID=18518&highlightTerms=surveillance` | 2026-09-26 |
| `somerville_legistar_index.html` | Somerville **Legistar LegislationDetail** page (GUID 11D1E64A-529B-4218-8F99-A3E07B0C1476 / ID 7350978 — the Chapter 10-66 ordinance item); six `View.ashx?M=F&ID=…` §10-66(b) annual-report filings with verbatim anchors | `https://somervillema.legistar.com/LegislationDetail.aspx?GUID=11D1E64A-529B-4218-8F99-A3E07B0C1476&ID=7350978` | 2026-09-26 |

Document bytes in the P31.13 tests are `tests/support.py::minimal_pdf`
syntheses carrying the filings' own field literals (`Date:` labels,
`Surveillance Technology:` fields, questionnaire headings) — verified against
the live documents 2026-09-26: Oakland ALPR/ShotSpotter memos cite `OMC 9.64`
and carry `DATE: <Month> <D>, <YYYY>`; the Cambridge combined report is the
eight-question Chapter 2.128 questionnaire repeated per department; each
Somerville filing is the nine-question §10-66(b) questionnaire verbatim.

The companion federal fixture `tests/connectors/fixtures/fema_hsgp_page1.json`
is a **synthetic** USAspending `spending_by_award` assistance-page shape
(display-label fields verified live 2026-09-26; award ids/recipients/amounts
invented) for the `fema_hsgp_allocations` source — the FEMA Homeland Security
Grant Program (assistance listing 97.067) prime-grant allocations surface.
Rights basis: USAspending is federal open data (public domain); the reviewed
bounded window is two pages under the documented POST endpoint
(ADR-083 allow-listed).
