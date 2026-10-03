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
| `malformed_document.pdf` | — (negative control) | `%PDF-` magic with no valid objects — `pdf_text_pages` yields no pages → explicit `ContentDrift`, never a partial claim |

Oversized and encrypted documents are generated in-test (`tmp_path`), not
committed: an oversized file is just bytes over `max_document_bytes`, and an
encrypted PDF is produced with `pypdf.PdfWriter.encrypt`.

`golden_locators.json` is the committed golden **field→locator** output the
test compares against (regenerate with the helper in
`tests/connectors/test_dossier_documents.py` if the reviewed field map changes).
