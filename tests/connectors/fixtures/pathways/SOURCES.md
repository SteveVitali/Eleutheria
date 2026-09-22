# Stage-5 pathway fixtures — SOURCES (P21.9, §46, HG-03 gate pending)

These fixtures excerpt **public documents already cited in the research cache** to exercise
the `pathways` connector over committed fixtures (no live fetch — HG-03/HG-04 per source are
pending; see the gate-status block in the P21.9 commit). Each fixture document carries its
own `source_url` + `retrieved_date`; this file is the human-readable index the reviewer uses
to audit provenance (SIG-INGEST-015, §3.1). The excerpts are short, paraphrased fact carriers
— not verbatim re-hosting of copyrighted content (LINK posture; rights UNDETERMINED).

The three registry sources these fixtures are attributed to stay
`ingestion_permitted = false` / rights `UNDETERMINED` until a rights packet + operator flip
(`docs/build/rights/pathways_*.md`). A `run --mode live` against any of them REFUSES (exit 3).

## `rtcc_federation.json` — source `pathways_rtcc_federation` (P17.1)

| conformance pathway | genre | document | source URL | retrieved |
|---|---|---|---|---|
| private_camera_federation | vendor_disclosure | Fusus RTCC / Community Connect disclosure | https://www.eff.org/deeplinks/2022/06/fusus-real-time-crime-centers | 2026-08-20 |
| rtcc_hub | procurement_record | RTCC integration hub contract (procurement table) | https://www.documentcloud.org/documents/rtcc-integration-hub-contract | 2026-08-20 |
| broker_chain | vendor_disclosure | commercial data-broker location chain | https://www.eff.org/deeplinks/2023/10/data-brokers-location-chain | 2026-08-20 |

## `fr_css_forensics.json` — source `pathways_fr_css_forensics` (P17.2)

| conformance pathway | genre | document | source URL | retrieved |
|---|---|---|---|---|
| face_recognition | policy_document | state-police facial-recognition policy | https://www.documentcloud.org/documents/state-police-facial-recognition-policy | 2026-08-20 |
| css_and_forensics | deployment_report | county sheriff annual surveillance report 2024 | https://www.documentcloud.org/documents/county-sheriff-annual-surveillance-report-2024 | 2026-08-20 |
| federal_authorization | policy_document | federal CSS authorization court order | https://www.courtlistener.com/docket/federal-css-authorization-order | 2026-08-20 |

## `acoustic_drone_location.json` — source `pathways_acoustic_drone_location` (P17.3)

| conformance pathway | genre | document | source URL | retrieved |
|---|---|---|---|---|
| gunshot_detection | deployment_report | city PD ShotSpotter/SoundThinking annual report | https://www.documentcloud.org/documents/city-pd-shotspotter-annual-report | 2026-08-20 |
| drones | procurement_record | county sheriff DFR drone purchase order | https://www.documentcloud.org/documents/county-sheriff-dfr-drone-purchase-order | 2026-08-20 |
| commercial_location | vendor_disclosure | commercial location-data purchase disclosure | https://www.eff.org/deeplinks/2022/08/commercial-location-data-purchase | 2026-08-20 |

## Epistemic note (RISK-P21-16, §46)

Every **deployment** claim in these fixtures originates ONLY from a `deployment_report`
document (the county-sheriff and city-PD annual surveillance reports). The procurement-genre
fixtures (`rtcc_hub`, `drones`) emit `procurement` + `vendor_product` claims only — never a
`deployed` claim. `procured` never implies `deployed`.
