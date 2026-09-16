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
