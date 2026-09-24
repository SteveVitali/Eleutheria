<!-- SPDX-License-Identifier: Apache-2.0 -->
# OKC document-connector shadow fixtures (P23.5 / LIVE.1a / GL-LIVE-01)

Each fixture below is a faithful transcription of a cited **public** Oklahoma City
document, in the shape the sig-parsing layer that connector drives reads (a table
grid for the layer-4 `pdf_table` engine; numbered clauses for the layer-3 `pdf_text`
clause locator). The figures match the P06.1 vertical-slice evidence
(`tests/acceptance/fixtures/okc_sources.json`). The **live fetch** of each real
document is operator-gated (HG-09 tokens not provided) and DEFERRED as
`D-LIVE.1a-1`; these fixtures prove the connector code via shadow replay (diff = 0).

| fixture | source id | document (public) | retrieved | url |
|---|---|---|---|---|
| `okc_procurement.json` | `okc_procurement` | City of Oklahoma City — Master Agreement C241032 (Flock Safety); $270,000/yr, 90 cameras | 2026-09-01 | https://www.okc.gov/departments/finance/purchasing |
| `okcpd_policy.json` | `okcpd_policy` | OKCPD Operations Manual §5-118 (ALPR sharing restriction) | 2026-09-01 | https://www.okc.gov/departments/police |
| `ok_statute.json` | `ok_statute` | Oklahoma statute 47 O.S. §7-606.1 (limits ALPR to insurance enforcement) | 2026-09-01 | https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST47 |

All three sources were flipped to `ingestion_permitted=true` by RIGHTS.1 (P21.1
re-run, GL-GATE-03): government records / statutory text are public domain
(CC0-1.0, the registry-accepted expression). Part VIII §0.7 is honored on every
parsed claim: no plate/trip/per-person data, the officer-naming gate, and the
sensitivity tier travel with the claim (see `connectors.okc_documents`).
