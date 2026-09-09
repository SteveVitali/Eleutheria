# Stage-5 connector coverage — P17 pathways (P21.9, §46)

Rendered by `python tests/connectors/test_pathway_coverage.py`;
`tests/connectors/test_pathway_coverage.py::test_stage5_connectors_report_is_present_and_consistent`
asserts this table stays consistent with live coverage (no stale doc). Every P17
conformance-suite pathway (the three `tests/ontology/generalization/test_stage5_*.py`
graphs) has **≥1 claim produced by a `pathways` connector fixture** — the mechanical
retirement of RISK-P17-03 ("expressibility, not ingestion"; now: ingested).

**Run mode:** all rows are **fixture replay** — no live fetch. The three registry
sources (`pathways_rtcc_federation`, `pathways_fr_css_forensics`,
`pathways_acoustic_drone_location`) stay `ingestion_permitted = false` / rights
`UNDETERMINED` pending a rights packet + operator flip (HG-03/HG-04 per source pending).
A `run --mode live` against any of them **REFUSES at the loader gate (exit 3)**.

**Epistemic rule (RISK-P21-16, §46):** every `deployment` claim originates ONLY from a
`deployment_report`-genre document; the procurement-genre fixtures (`rtcc_hub`, `drones`)
emit `procurement` + `vendor_product` claims only — `procured` never implies `deployed`.

| P17 pathway | family | claims | claim types | verdict |
|---|---|---|---|---|
| broker_chain | rtcc_federation | 3 | vendor_product | MET |
| commercial_location | acoustic_drone_location | 2 | vendor_product | MET |
| css_and_forensics | fr_css_forensics | 5 | deployment, vendor_product | MET |
| drones | acoustic_drone_location | 5 | procurement, vendor_product | MET |
| face_recognition | fr_css_forensics | 3 | policy, vendor_product | MET |
| federal_authorization | fr_css_forensics | 3 | policy | MET |
| gunshot_detection | acoustic_drone_location | 3 | deployment, vendor_product | MET |
| private_camera_federation | rtcc_federation | 5 | vendor_product | MET |
| rtcc_hub | rtcc_federation | 4 | procurement, vendor_product | MET |

## Live-run status (per source)

| source | pathway family | ingestion_permitted | live run | notes |
|---|---|---|---|---|
| pathways_rtcc_federation | rtcc_federation | false | REFUSED (exit 3) | HG-03 pending; fixtures only |
| pathways_fr_css_forensics | fr_css_forensics | false | REFUSED (exit 3) | HG-03 pending; fixtures only |
| pathways_acoustic_drone_location | acoustic_drone_location | false | REFUSED (exit 3) | HG-03 pending; fixtures only |

No source was flipped this ticket (operator gate answer: **SKIP — no source flipped**),
so there are no live captures/claims in PG; the conditional AC (HG-03 live run) does not
apply. Rights packets: `docs/build/rights/pathways_{rtcc_federation,fr_css_forensics,acoustic_drone_location}.md`.

## Parser layers exercised (ADR-033-deferred, LD-F17)

| layer | method | engine | pathway documents |
|---|---|---|---|
| 4 | `pdf_table` | `parsing.tables` | procurement records (`rtcc_hub`, `drones`) |
| 3 | `pdf_text` | `parsing.clauses` | policy documents (`face_recognition`, `federal_authorization`) |
| — | `structured_import` | assertions | vendor disclosures + deployment reports |

`sig-parsing classify <doc>` reports the document **genre** (procurement / policy /
deployment / vendor / agenda — `parsing.genre`), the axis the procured≠deployed rule keys off.
