# Dossier pilot fixtures (P32.12, ticket 172, SIG-ACQ-003)

Ten **representative allowed/redacted stand-in documents** across the three
pilot cities, plus one negative-control file. These are hand-authored review
fixtures — they reproduce the *shape* of the published artifacts the S2 source
strategy reviewed (same clauses, same blanks, same distinctions) without
re-hosting upstream bytes. They are compact by design (each < 4 KB) and carry
no personal, plate-, trip-, or per-search data (Part VIII).

None of these files is a fetched capture of the real artifact: the fixture-run
contract is the same eight-stage pipeline over the static transport — fixture
success is an engineering check, never a live-access proof or a rights decision
(the `dossier_*` registry rows stay `ingestion_permitted=false`).

| file | dossier target | models |
|---|---|---|
| `okc_usage_page.html` | `okc-flock-usage-2026` | City usage page: scoped counts (city-owned vs partner agencies), an `as of` date, and a **future-effective retention change with its exception clause** |
| `okc_council_memo_2026.pdf` | `okc-council-memo-2026-08` | A **posted** governance memo (publication date) describing an amendment — posting ≠ execution |
| `okc_amendment_1_2026.pdf` | `okc-flock-amendment-2026` | Amendment 1 to contract C241032: `amends_contract`, actor-specific federal-disclosure restriction + compulsory-process carve-out, **incomplete signature block** (genre `contract`, never `executed_contract`) |
| `tulsa_mou_template.pdf` | `tulsa-mou-template` | A **blank MOU template** — proves structure only; party/date fields are `present_but_empty`; every claim is D6 |
| `tulsa_policy_113c.pdf` | `tulsa-policy-113c` | TPD Policy 113C: **two distinct ALPR products** (Flock fixed + Axon Fleet 3 in-car), retention scoped to *manually entered* data only |
| `tulsa_policy_113e.pdf` | `tulsa-policy-113e` | TPD Policy 113E: approval-based sharing; **no uniform numeric retention period** (reviewed `absent`) |
| `sd_asr_2025_vigilant.pdf` | `sd-asr-2025-vigilant` | SDPD ASR 2025: **subscription access** to the hosted Vigilant LEARN database — access ≠ hardware |
| `sd_ubicquia_agreement_2023.pdf` | `sd-ubicquia-agreement-2023` | Public-safety agreement: parties, not-to-exceed ceiling, contracted unit count, vendor-only signature date (city execution **not visually verified**) |
| `sd_technology_index.html` | `sd-technology-index` | Technology index page — three reviewed links + one posted date |
| `sd_pab_index.html` | `sd-pab-index` | Privacy Advisory Board reports index — the ALPR recommendation listing (existence + link only) |
| `bia_tribal_leadership_layer.html` | `camreg_tribal_all_leaders_directory` → `bia-tld-layer-metadata` | **P35.11 / ADR-185 S8 screened lane:** the ArcGIS REST layer-metadata page for the BIA Tribal Leaders Directory — stated name + the verbatim BIA use disclaimer; **facts + citations only**, no row data ever |
| `tolc_lgds_ast_hearing_notice.pdf` | `legis_tribal_tohono_oodham_notice` → `tolc-lgds-ast-hearing-notice-2025-11-19` | **P35.11 / ADR-185 S8 screened lane:** the Tohono O'odham Legislative Branch public-hearing notice on the Border Patrol LGDS + Automated Surveillance Tower proposals — committee, technology names, hearing date; **the named chairperson is deliberately absent** (screened lane) |
| `malformed_document.pdf` | — (negative control) | `%PDF-` magic with no valid objects — `pdf_text_pages` yields no pages → explicit `ContentDrift`, never a partial claim |

P36.11 / R11-ACQ-15 fixtures (ticket 285 — the `r11-documents-01` document
family). Same stand-in contract as the pilots: hand-authored review fixtures
reproducing the *shape* of the published documents (programme/agency names,
award amounts, instrument numbers as the upstream pages publish them) without
re-hosting upstream bytes; no personal, plate-, trip- or per-person data. The
sources stay `ingestion_permitted=false` — fixture success is an engineering
check, never a rights decision or a live-access proof.

| file | dossier target | models |
|---|---|---|
| `txdmv_mvcpa_grant_listing.pdf` | `grant_tx_txdmv_mvcpa` → `txdmv-mvcpa-fy2026-grant-listing` | MVCPA FY2026 published grant listing: funder, programme, one grantee row (agency + amount + ALPR purpose) — an **award**, never a deployment |
| `bscc_ort_program.html` | `grant_ca_bscc_ort` → `bscc-ort-grant-program` | BSCC Organized Retail Theft programme page: funder, programme, one grantee award + purpose |
| `fl_senate_lfir_s3177.pdf` | `grant_fl_senate_lfir` → `fl-senate-lfir-s3177` | A Local Funding Initiative Request form: requesting entity, amount requested, ALPR purpose — a **request**, not an award |
| `adeca_psn_grants.html` | `grant_al_adeca_psn` → `adeca-psn-grants-2025-07-16` | ADECA governor's-office announcement of PSN awards: funder, programme, recipient, amount, posted date |
| `nj_oag_bwc_guidelines.pdf` | `grant_nj_oag_bwc` → `nj-oag-bwc-sfy21-guidelines` | NJ OAG SFY21 Body-Worn Camera Grant Program guidelines: programme funder, total appropriation, funded equipment class |
| `ok_dac_jag_lle.html` | `grant_ok_dac_jag_lle` → `ok-dac-jag-lle-program` | OK DAC JAG-LLE programme page: funder, programme, eligible-equipment purpose; **no award amount** (reviewed `absent` → field-state, never fabricated) |
| `haskell_resolution_19_2025.pdf` | `agenda_haskell_ar_council` → `haskell-resolution-19-2025` | Resolution 19-2025 **authorizing** the Mayor to execute a Flock Safety LPR agreement — authorization, never execution |
| `des_moines_26_235.pdf` | `agenda_des_moines_ia_council` → `des-moines-communication-26-235` | Council Communication 26-235 **recommending approval** of a Motorola Solutions LPR agreement — a recommendation under consideration |
| `jasper_sc_agenda_cellebrite.pdf` | `agenda_jasper_sc_council` → `jasper-sc-agenda-cellebrite-2024` | Council agenda item for the Sheriff's Cellebrite software purchase — consideration only |
| `davie_ntss_2018_026.pdf` | `procportal_davie_fl_purchasing` → `davie-ntss-2018-026-cellebrite` | Notice of Intent to Award NTSS-2018-026 (Cellebrite sole-source) — an intent notice, never an executed contract |
| `forsyth_rfp2449.pdf` | `procportal_forsyth_nc_purchasing` → `forsyth-rfp2449-rtic` | RFP2449 cover for a Real-Time Intelligence Center enterprise solution — solicitation metadata only |
| `guam_governor_bill_132_35.html` | `legis_gu_governor` → `guam-governor-bill-132-35-signing` | Governor of Guam press release: Bill 132-35 (GPD security cameras) signed — publication facts only (RB-06) |

Oversized and encrypted documents are generated in-test (`tmp_path`), not
committed: an oversized file is just bytes over `max_document_bytes`, and an
encrypted PDF is produced with `pypdf.PdfWriter.encrypt`.

`golden_locators.json` is the committed golden **field→locator** output the
test compares against (regenerate with the helper in
`tests/connectors/test_dossier_documents.py` if the reviewed field map changes).
