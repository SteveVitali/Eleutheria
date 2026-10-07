# URL reconciliation — the 21 dossier return-pass targets (P34.38, E4 NEW-7)

`sig.url-reconciliation/1` · generated 2026-10-07 (`date -u`) · machine-readable
twin: [`url_reconciliation.json`](url_reconciliation.json)

For each of the 21 dossier targets in the three committed return passes
(`p32.18-okc-dossier`, `p32.19-tulsa-dossier`, `p32.20-san-diego-dossier`
`LIVE_RETURN_PASS.json`), the URL is compared against the research record —
`source-candidates.csv`, the E4 §4.2 per-target table, and the existing
green-source targets in `live_targets.toml`. **Documentary only: no URL was
fetched to reconcile it.** A `differs` or unrecorded URL is marked for the B1
binding, never silently replaced — the operator's E4-B1 answer ("a — GL-GATE-07
(US) applied batch-wide to all three lanes of the 23 new targets",
2026-10-01T04:03:25Z) binds the reconciled URL list through the prepared
HG-03 patch, which the operator applies (S6R-17).

| # | doc_id | return-pass URL | status | research record |
|---|---|---|---|---|
| O1 | `okc-flock-usage-2026` | `okc.gov/departments/police/flock-safety-lpr-usage` | **differs** | `okc.gov/Services/Public-Safety/Police/Flock-Safety-license-plate-reader-LPR-usage-in-Oklahoma-City` (SRC-001 primary) |
| O2 | `okc-council-memo-2026-08` | `okc.gov/files/police/flock-council-memo-august-2026.pdf` | **no research record** | packet mentions a "two-page council memo", no URL |
| O3 | `okc-flock-amendment-2026` | `okc.gov/files/police/flock-amendment-1-2026.pdf` | **differs** | `okc.gov/files/assets/city/v/1/police/documents/flock/flock-amendment-august-2026.pdf` (SRC-001 secondary; research recorded a 403) |
| O4 | `okc-statute-47-7-606-1` | `oscn.net/…DeliverDocument.asp?CiteID=478582` | **reconciled** | = SRC-007 secondary; `ok_statute` target (`live_targets.toml:311`) — rides a green source (B5) |
| O5 | `okc-ops-manual-5-118` | `okc.gov/files/assets/city/v/2/police/documents/operations-manual-6th-edition-june-15-2026.pdf` | **reconciled** | = `okcpd_policy` target (`live_targets.toml:328`) — green source (B5) |
| O6 | `okc-purchasing-index` | `okc.gov/departments/finance/purchasing` | **reconciled** | = `okc_procurement` target (`live_targets.toml:343`; edge WAF may refuse) — green source (B5) |
| T1 | `tulsa-mou-template` | `tulsapolice.org/files/camera-integration-mou-template.pdf` | **no research record** | review depth "three-page blank MOU", no URL |
| T2 | `tulsa-policy-113c` | `tulsapolice.org/files/policy-113c-alpr.pdf` | **no research record** | — |
| T3 | `tulsa-policy-113e` | `tulsapolice.org/files/policy-113e-alpr-sharing.pdf` | **no research record** | — |
| T4 | `tpd-flock-page` | `tulsapolice.org/flock-safety` | **reconciled** | = SRC-002 primary |
| T5 | `tpd-policies-index` | `tulsapolice.org/policies-and-procedures` | **reconciled** | = SRC-002 secondary |
| T6 | `tulsa-corridor-safety-guide` | `cityoftulsa.org/…/commercial-corridor-safety-guide/` | **no research record** | a P32.19 lead |
| S1 | `sd-asr-2025-vigilant` | `sandiego.gov/sites/default/files/sdpd-annual-surveillance-report-2025.pdf` | **differs** | `…/files/2026-02/sdpd-annual-surveillance-report-2025.pdf` (SRC-003 secondary) |
| S2 | `sd-ubicquia-agreement-2023` | `sandiego.gov/sites/default/files/cosd-public-safety-agreement-ubicquia.pdf` | **reconciled** | = SRC-004 secondary (signature blocks name persons — officer-naming gate applies) |
| S3 | `sd-technology-index` | `sandiego.gov/police/data-transparency/technology` | **reconciled** | = SRC-003 primary |
| S4 | `sd-pab-index` | `sandiego.gov/pab/reports` | **reconciled** | = SRC-005 primary |
| S5 | `sd-alpr-program-page` | `sandiego.gov/police/data-transparency/technology?tech=alpr` | **differs** | `…/technology/view?tech=Automated+License+Plate+Recognition+(ALPR)` (SRC-027 primary) |
| S6 | `sd-alpr-use-policy` | `sandiego.gov/sites/default/files/alpr-use-policy.pdf` | **no research record** | index-linked; recorded 403 — B4 byte bound + one bounded retry recorded on the target row |
| S7 | `sd-pab-recommendation-2025` | `sandiego.gov/sites/default/files/pab-final-recommendation-alpr-2025.pdf` | **differs** | `…/files/2026-05/pab-final-recommendation-alpr-2025-asr-00235352xbde34.pdf` (SRC-005 secondary, ~16 MB — over the byte bound) — B4 applies |
| S8 | `sd-council-memo-2025-12-10` | `sandiego.gov/city-clerk/officialdocs/council-documents` | **no research record** | a lead |
| S9 | `sd-network-audit-links` | `sandiego.gov/police/data-transparency/technology?tech=alpr` (metadata only) | **reconciled** | ≈ SRC-027 (link/label metadata only; workbook path rejected under E4-B3 = a) |

**Tally:** 9 reconciled · 5 differs (O1, O3, S1, S5, S7 — E4 §4.3) · 7 no
research record (O2, T1–T3, T6, S6, S8). No URL in `live_targets.toml` or in
any return pass was changed by this row — `differs` and unrecorded URLs are
marked for the B1 binding, never silently replaced.
