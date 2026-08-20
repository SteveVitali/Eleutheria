# Appendix A — Requirement traceability matrix

This appendix is the **proof of the superset claim** made in §0.1. It walks all **480 atomic
obligations** extracted from `docs/1_deep_research_overview.md` into
`docs/research/_meta/OUTLINE_TRACE.md`, and records for each the section of this specification that
discharges it.

The matrix was produced by an **independent adversarial review** whose brief was to find gaps rather
than confirm coverage (`docs/research/_meta/GAP_ANALYSIS.md`), then updated twice as work completed.

## A.1 Summary

| Stage | COVERED | PARTIAL | GAP | CONTRADICTED |
|---|---|---|---|---|
| Adversarial review, first pass | 395 | 58 | 27 | 0 rows / 4 self-claims |
| After the gap-closure pass | 479 | 1 | 0 | 0 |
| **After the research-completion pass** | **480** | **0** | **0** | **0** |

Rows closed in each stage are marked *(closed in the gap-closure pass.)* or *(closed in the
completion pass.)* respectively.

**The final PARTIAL was `OL-2B-FP-04`** — temporal snapshotting of vendor transparency portals. It
was held open honestly for as long as no lawful access path existed, on the grounds that marking it
COVERED would be the synthetic certainty §3.1 forbids. The completion pass established that a public,
CC BY-SA 4.0 aggregator API supplies the layer (SC-18), so the obligation is now genuinely
dischargeable and Phase 11 is ungated.

## A.2 Reading the matrix

`Type` is the obligation class from the trace: `PURPOSE`, `REQ`, `ENTITY`, `FIELD`, `VOCAB`,
`PRINCIPLE`, `NONGOAL`, `Q`, `SOURCE`, `EXAMPLE`, `SURFACE`, `STAGE`.

`COVERED` means the obligation is discharged by the named section, and a coding agent executing that
section would produce what the outline requires — not merely that the words appear.

## A.3 The matrix


### 0. Executive summary

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-ES-01` | PURPOSE | COVERED | §1.3, §6 | SIG positioned as the missing reconciliation layer. |
| `OL-ES-02` | REQ | COVERED | §2.1 Q-1…Q-13 | All thirteen mapped to a carrier + acceptance query. |
| `OL-ES-03` | REQ | COVERED | SIG-CHART-007 | Joining burden stated as the central architectural obligation. |
| `OL-ES-04` | SOURCE | COVERED | §6, §22.2, §23.2 | OSM = upstream canonical device geography. |
| `OL-ES-05` | SOURCE | COVERED | §6, §22.2 | DeFlock role: contributors upstream to OSM; do not fork. |
| `OL-ES-06` | SOURCE | COVERED | §6, §22.5 | EoF = portal temporal layer; Phase 0 blocking dependency. |
| `OL-ES-07` | SOURCE | COVERED | §6, §23.7, N9 | HIBF = audit specialist; SIG holds structural aggregates only. |
| `OL-ES-08` | SOURCE | COVERED | §6, §22.2, G C-02 | Role preserved; scope corrected (now routing/offline, GitLab). |
| `OL-ES-09` | SOURCE | COVERED | §6, §23.3 | Atlas = primary deployment seed. |
| `OL-ES-10` | SOURCE | COVERED | §22.6 D, §23.9 | Registry row + dedicated connector + Phase 12. *(closed in the gap-closure pass.)* |
| `OL-ES-11` | SOURCE | COVERED | §6, §23.8, §10.4 R3 | Accountability Atlas epistemic labels adopted. |
| `OL-ES-12` | SOURCE | COVERED | §6, §23.9, §43.5 | Lead generation only; never confirmed device identification. |
| `OL-ES-13` | SOURCE | COVERED | §6, §22.2, §38 | Downstream consumer; publish reusable higher-order data. |
| `OL-ES-14` | SOURCE | COVERED | §6, §33.7, G C-03 | FlockReporter unreachable; SIG maintains its own registry. |
| `OL-ES-15` | SOURCE | COVERED | §6, §11.19, §23.5 | MuckRock modelled as RecordsRequest evidence substrate. |
| `OL-ES-16` | REQ | COVERED | §13.1 | `body-worn-video` domain added; 14 domains. *(closed in the gap-closure pass.)* |
| `OL-ES-17` | SOURCE | COVERED | §22.2, §12.3, G C-06/C-07 | Community Connect verified; Fusus/Flock link severed 2025. |
| `OL-ES-18` | SOURCE | COVERED | §11.4, §43.3, G C-08 | ShotSpotter→SoundThinking rename; 22,471 not 25,000; leak veto. |
| `OL-ES-19` | SOURCE | COVERED | §11.4, §22.7 | Named examples restored incl. Cellebrite UFED. *(closed in the gap-closure pass.)* |
| `OL-ES-20` | REQ | COVERED | §5.3, §13.7, §43.8, Phase 18 | Global physical layer; jurisdiction adapters. |
| `OL-ES-21` | PURPOSE | COVERED | SIG-CHART-001 (MUST NOT) | Explicit prohibition on being another surveillance map. |
| `OL-ES-22` | PURPOSE | COVERED | §1.1, §3.4, §3.5 | Six defining characteristics bound to sections. |
| `OL-ES-23` | PURPOSE | COVERED | §1.2 | Preserved verbatim. |
| `OL-ES-24` | PRINCIPLE | COVERED | §3.5 SIG-CHART-017 | Each characteristic bound to an enforcing section. |
| `OL-ES-25` | PRINCIPLE | COVERED | SIG-CHART-003 | Relationship, not device, as fundamental unit. |
| `OL-ES-26` | EXAMPLE | COVERED | §1.4 table | All seven manifestations enumerated with why each breaks device-centrism. |
| `OL-ES-27` | ENTITY | COVERED | §11.0 entity index | All 21 classes present; several split, four NEW. |
| `OL-ES-28` | PURPOSE | COVERED | SIG-CHART-002 | Joined evidence as the distinctive output. |
| `OL-ES-29` | EXAMPLE | COVERED | §2.2 J-1, Appendix D, Phase 6 | Full traversal is the Phase-6 gate. |
| `OL-ES-30` | EXAMPLE | COVERED | §2.2 J-2, §11.16, §32.2 | Coverage statement mandated on the result set. |
| `OL-ES-31` | EXAMPLE | COVERED | §39.5a | Evidence recommender specified with a Phase 15 criterion. *(closed in the gap-closure pass.)* |
| `OL-ES-32` | EXAMPLE | COVERED | §2.2 J-4, §13.4, §29.4 | replaced_by edge + integration classification. |

### 1. Project thesis

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-1.1-01` | PRINCIPLE | COVERED | SIG-CHART-004 | Point-only representation rejected. |
| `OL-1.1-02` | REQ | COVERED | SIG-CHART-005, §12.9 | All twelve mapped to carriers. |
| `OL-1.1-03` | EXAMPLE | COVERED | §1.4 rationale | Two-jurisdiction contrast stated verbatim. |
| `OL-1.1-04` | PRINCIPLE | COVERED | SIG-CHART-004 | Graph of capabilities and access. |
| `OL-1.2-01` | PRINCIPLE | COVERED | SIG-CHART-014 | Federation as MUST. |
| `OL-1.2-02` | NONGOAL | COVERED | SIG-CHART-015.1 | Do not fork DeFlock. |
| `OL-1.2-03` | NONGOAL | COVERED | SIG-CHART-015.2, SIG-CONTRIB-004 | Route device observations to OSM/DeFlock. |
| `OL-1.2-04` | NONGOAL | COVERED | SIG-CHART-015.3 |  |
| `OL-1.2-05` | NONGOAL | COVERED | SIG-CHART-015.4, N9 |  |
| `OL-1.2-06` | NONGOAL | COVERED | SIG-CHART-015.5, SIG-EPIS-008 |  |
| `OL-1.2-07` | NONGOAL | COVERED | SIG-CHART-015.6, SIG-CHART-019 |  |
| `OL-1.2-08` | REQ | COVERED | SIG-CHART-014.1–7 | All seven positive obligations enumerated. |
| `OL-1.2-09` | PURPOSE | COVERED | SIG-CHART-016, §6 | Compact with enforced ingestion_permitted flag. |

### 2. Ecosystem — Layer A (physical infrastructure)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2A-OSM-01` | SOURCE | COVERED | §19.1, §23.2 | man_made=surveillance population measured (SC-01). |
| `OL-2A-OSM-02` | VOCAB | COVERED | §23.2 SIG-INGEST-045 | Full measured tag vocabulary table. *(closed in the gap-closure pass.)* |
| `OL-2A-OSM-03` | REQ | COVERED | §22.2, §19.3, Q19 | Overpass, replication diffs, element history. |
| `OL-2A-OSM-04` | PRINCIPLE | COVERED | §6, §42.3 | Neutral substrate; never the canonical editing DB. |
| `OL-2A-OSM-05` | PRINCIPLE | COVERED | SIG-ONTO-006, N7 | Confirmed devices flow to OSM, not a SIG device table. |
| `OL-2A-OSM-06` | REQ | COVERED | §42.3, Q13/Q14 | Derivative vs Collective analysed from the actual guidelines. |
| `OL-2A-OSM-07` | SOURCE | COVERED | §22.6 A | URLs seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-2A-DF-01` | SOURCE | COVERED | §6, §22.2 |  |
| `OL-2A-DF-02` | PRINCIPLE | COVERED | §6, §42.3 |  |
| `OL-2A-DF-03` | REQ | COVERED | §6, SIG-CONTRIB-004 |  |
| `OL-2A-DF-04` | PRINCIPLE | COVERED | §6 (do not fork) |  |
| `OL-2A-DF-05` | SOURCE | COVERED | §22.6 A | `deflock-data` registered, marked existence-unverified. *(closed in the gap-closure pass.)* |
| `OL-2A-DF-06` | FIELD | COVERED | §11.8 | osm_version, upstream_id, first/last_observed all present. |
| `OL-2A-DF-07` | REQ | COVERED | §29.1, §29.2, §11.8 | Attribution + count reconciliation + orphan state. |
| `OL-2A-SUS-01` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-2A-SUS-02` | REQ | COVERED | SIG-CHART-030 | No US-only device schema. |
| `OL-2A-PC-01` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-2A-PC-02` | PRINCIPLE | COVERED | §19.3 SIG-GEO-006 | Derived geometry physically separate and labelled. |
| `OL-2A-DAF-01` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-2A-DAF-02` | REQ | COVERED | §38, §6 | Reusable higher-order exports; no re-scraping. |

### 2. Ecosystem — Layer B (official/vendor deployment + sharing metadata)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2B-FP-01` | SOURCE | COVERED | §22.2, §8.3 Layer B |  |
| `OL-2B-FP-02` | FIELD | COVERED | §23.4 | All twelve portal fields now have predicates. *(closed in the gap-closure pass.)* |
| `OL-2B-FP-03` | PRINCIPLE | COVERED | §10.2, §17.6, G C-04 | Portals incomplete; disappearance is data. |
| `OL-2B-FP-04` | REQ | COVERED | §22.5, §17, §29.7 | Portal snapshotting now fully dischargeable via the aggregator API (SC-18). *(closed in the completion pass.)* |
| `OL-2B-FP-05` | REQ | COVERED | §11.2, §12.2, §11.15 | Org types cover federal/university/private; direction required. |
| `OL-2B-FP-06` | SOURCE | COVERED | §22.6 B | Portal host + example slugs registered. *(closed in the gap-closure pass.)* |
| `OL-2B-EOF-01` | SOURCE | COVERED | §6, §22.5, R-02 | Foundational, Phase-0 blocking. |
| `OL-2B-EOF-02` | REQ | COVERED | §23.4 | The no-directory / brute-force-enumeration fact now stated. *(closed in the gap-closure pass.)* |
| `OL-2B-EOF-03` | FIELD | COVERED | §23.4 | `hotlist_hit_windowed_count` added. *(closed in the gap-closure pass.)* |
| `OL-2B-EOF-04` | REQ | COVERED | §22.5, §6 | Discovery/archiving/normalization/aggregation/edge extraction. |
| `OL-2B-EOF-05` | REQ | COVERED | SIG-INGEST-030/031 | Ordered fallback; challenge-defeating crawler forbidden. |
| `OL-2B-IND-01` | SOURCE | COVERED | §17.4 SIG-EVID-008, §29.7 | WACZ + screenshot + structured payload + raw HTML. |
| `OL-2B-IND-02` | PRINCIPLE | COVERED | §9.1–9.2, §10.2 | Four-way distinction encoded in the temporal model. |
| `OL-2B-IND-03` | PRINCIPLE | COVERED | §16.3, §17.3, SIG-EVID-006 | Immutability enforced by OCFL + Object Lock + role revocation. |

### 2. Ecosystem — Layer C (usage and audit behavior)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2C-HIBF-01` | SOURCE | COVERED | §6, §23.7 |  |
| `OL-2C-HIBF-02` | ENTITY | COVERED | §11.16 audit_source_type=organization_audit |  |
| `OL-2C-HIBF-03` | ENTITY | COVERED | §23.7 REQ-R2-07 | `Camera Count` ingested as an independent count claim. *(closed in the gap-closure pass.)* |
| `OL-2C-HIBF-04` | ENTITY | COVERED | §11.16 audit_source_type=portal_public_audit |  |
| `OL-2C-HIBF-05` | ENTITY | COVERED | §23.7, §12.2 configured_access | SharedNetworks.csv → directional configured-access edges. |
| `OL-2C-HIBF-06` | ENTITY | COVERED | §23.7, §29.4 SIG-RECON-039 | Event-log transitions preferred over inferred ones. |
| `OL-2C-HIBF-07` | ENTITY | COVERED | §11.15 observed_via=config_screenshot | All listed settings are ConfigurationState predicates. |
| `OL-2C-HIBF-08` | REQ | COVERED | §23.7 SIG-INGEST-046 | All six capabilities explicitly dispositioned. *(closed in the gap-closure pass.)* |
| `OL-2C-HIBF-09` | PRINCIPLE | COVERED | §11.16, §18.1, N9 |  |
| `OL-2C-AW-01` | SOURCE | COVERED | §6, G C-02 |  |
| `OL-2C-AW-02` | REQ | COVERED | §21.1 eight-stage pipeline | Connector architecture mirrors the ALPR Watch shape. |
| `OL-2C-AW-03` | REQ | COVERED | §23.5, §24, §17.7 | MuckRock corrected to api_v2; reproducibility enforced. |
| `OL-2C-AW-04` | PRINCIPLE | COVERED | §24.2 SIG-PARSE-005/006 | Versioned, inspectable, reversible; dropdown vs free text split. |
| `OL-2C-AW-05` | PRINCIPLE | COVERED | §10.3.5, §16.2 | raw_value NOT NULL; normalization_id/version; review_status. |
| `OL-2C-AJ-01` | SOURCE | COVERED | §22.6 C | Both registered; the academic citation carries `capture_status=paywalled`. *(closed in the gap-closure pass.)* |
| `OL-2C-AJ-02` | PRINCIPLE | COVERED | §39.4, §30.2, §12.9 | Topology as first-class surface. |

### 2. Ecosystem — Layer D (agency-level adoption)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2D-AT-01` | SOURCE | COVERED | §6, §23.3 |  |
| `OL-2D-AT-02` | REQ | COVERED | §23.3 | Nine methodology components enumerated with R/D consequences. *(closed in the gap-closure pass.)* |
| `OL-2D-AT-03` | PRINCIPLE | COVERED | §9.5, §32, SIG-ONTO-059 | Absence encoded; category retirement ≠ world change. |
| `OL-2D-AT-04` | REQ | COVERED | §20.3 SIG-STORE-039/040 | Crosswalks with SKOS relations and lossy flags. |
| `OL-2D-AT-05` | SOURCE | COVERED | §22.7 | Full Data Library roster as the Phase 17 backlog. *(closed in the gap-closure pass.)* |
| `OL-2D-AT-06` | REQ | COVERED | §23.3 | Attribution preserved; supersession allowed. |
| `OL-2D-DD-01` | SOURCE | COVERED | §23.9 | Connector specified. *(closed in the gap-closure pass.)* |
| `OL-2D-DD-02` | REQ | COVERED | §23.9 SIG-INGEST-043a | Measured values carried: 2.54bn detections, 99.552% non-hit, mean 160.2 partners. *(deepened in the completion pass.)* |
| `OL-2D-DD-03` | PRINCIPLE | COVERED | SIG-CHART-026, §13.1 | Vendor-neutral ALPR family; six vendors in initial scope. |

### 2. Ecosystem — Layer E (accountability, incidents, litigation, policy)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2E-AA-01` | SOURCE | COVERED | §6, §23.8 |  |
| `OL-2E-AA-02` | REQ | COVERED | §23.8 | Five published artifacts enumerated. *(closed in the gap-closure pass.)* |
| `OL-2E-AA-03` | VOCAB | COVERED | §11.17 event_type | All six categories map to event_type terms. |
| `OL-2E-AA-04` | PRINCIPLE | COVERED | SIG-ONTO-038 | epistemic_status vocabulary adopted directly. |
| `OL-2E-AA-05` | PRINCIPLE | COVERED | SIG-ONTO-038, SIG-UI-043/045 | Allegation never rendered with a factual verb. |
| `OL-2E-AL-01` | SOURCE | COVERED | §6, §23.8 |  |
| `OL-2E-AL-02` | PRINCIPLE | COVERED | SIG-EPIS-030 | Curated index held as an index. |
| `OL-2E-AL-03` | REQ | COVERED | SIG-ONTO-039 | All six source classes linkable with class recorded. |
| `OL-2E-AC-01` | SOURCE | COVERED | §22.6 E, §39.0 | Registered; and it defines the local-advocate persona. *(closed in the gap-closure pass.)* |
| `OL-2E-AC-02` | SURFACE | COVERED | §39.2, Appendix D | All twelve dossier elements present. |

### 2. Ecosystem — Layer F (records and primary evidence)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2F-MR-01` | SOURCE | COVERED | §6, §11.19 |  |
| `OL-2F-MR-02` | FIELD | COVERED | §11.19 | All eight fields present plus statutory_basis and platform. |
| `OL-2F-MR-03` | PRINCIPLE | COVERED | §6, §10.1 | Link to the exact released document. |
| `OL-2F-DC-01` | SOURCE | COVERED | §6, §10.2 | Evidence store, not a citation URL. |
| `OL-2F-DC-02` | FIELD | COVERED | §10.3.2, §10.3.3 | All ten metadata fields present. |
| `OL-2F-DC-03` | REQ | COVERED | §10.3.2 artifact_type | 24-term vocabulary covers all listed genres. |
| `OL-2F-GOV-01` | SOURCE | COVERED | §23.6 SIG-INGEST-047 | Procurement aggregator registered under LINK posture. *(closed in the gap-closure pass.)* |
| `OL-2F-GOV-02` | SOURCE | COVERED | §23.6 SIG-INGEST-047 | `state_auditor_survey` and `warrant` artifact types added. *(closed in the gap-closure pass.)* |
| `OL-2F-GOV-03` | PRINCIPLE | COVERED | §22.3 A-01/A-02, SIG-ONTO-064 | Procurement precedes mapping; free_trial path. |

### 2. Ecosystem — Layer G (lead generation and field detection)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-2G-FF-01` | SOURCE | COVERED | §11.9, §23.9 |  |
| `OL-2G-FF-02` | PRINCIPLE | COVERED | §11.9, SIG-PUB-011/014 | Never conflated with verified hardware. |
| `OL-2G-FF-03` | REQ | COVERED | SIG-ONTO-006 | Required flow reproduced verbatim, terminating at OSM. |
| `OL-2G-FY-01` | SOURCE | COVERED | §6, §23.9 |  |
| `OL-2G-FY-02` | FIELD | COVERED | SIG-ONTO-030 | Full observation protocol required. |
| `OL-2G-FY-03` | REQ | COVERED | SIG-PUB-013 | Residential-parcel candidate never published at any precision. |

### 3. Decentralized local research ecosystem

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-3-01` | SOURCE | COVERED | SIG-INGEST-039 | All named groups seeded, `status=unverified`. *(closed in the gap-closure pass.)* |
| `OL-3-02` | SOURCE | COVERED | §33.7, G C-03, R-12 | Corrected: directory unreachable; SIG builds its own. |
| `OL-3-03` | REQ | COVERED | §34, §33.2 | Contributor tiers + task catalog. |
| `OL-3-04` | REQ | COVERED | §17.6, §21.4, §29.7, §33.2 #8 | Disappearance/diff/change-feed machinery. |
| `OL-3-05` | REQ | COVERED | §33.5, §33.6 | Geographic queues, non-exclusive, expiring. |
| `OL-3-06` | EXAMPLE | COVERED | Appendix D.3a | The research-gap object worked end to end. *(closed in the gap-closure pass.)* |
| `OL-3-07` | PURPOSE | COVERED | Part VI preamble |  |

### 4. Beyond Flock — the broader surveillance stack

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-4-00` | PRINCIPLE | COVERED | §5.2, SIG-CHART-027/028 | Generalization conformance suite. |
| `OL-4.1-01` | REQ | COVERED | §29.4 SIG-RECON-041 | Vendor replacement rendered as replacement. |
| `OL-4.1-02` | REQ | COVERED | §13.1 | Body-camera live streams now representable. *(closed in the gap-closure pass.)* |
| `OL-4.1-03` | SOURCE | COVERED | §22.2 | Community Connect enumerated and verified. |
| `OL-4.1-04` | REQ | COVERED | G C-06 | Corrected: 321 communities; 850k sums incommensurable counters. |
| `OL-4.1-05` | PRINCIPLE | COVERED | §12.4 | Extended from four roles to fourteen. |
| `OL-4.1-06` | SOURCE | COVERED | §22.6 B/E | Guardian, Community Connect and the enumeration thread registered. *(closed in the gap-closure pass.)* |
| `OL-4.2-01` | REQ | COVERED | §23.9 | Data Driven connector + historical findings. *(closed in the gap-closure pass.)* |
| `OL-4.3-01` | REQ | COVERED | §12.4, §11.10 system_scope, SIG-ONTO-018 | Vendor default never substitutes for deployment evidence. |
| `OL-4.4-01` | REQ | COVERED | §11.6, SIG-ONTO-024 | Capability is first-class; export/disclosure class added. |
| `OL-4.5-01` | SOURCE | COVERED | §22.6 E | WIRED source registered; figure corrected; veto applies. *(closed in the gap-closure pass.)* |
| `OL-4.5-02` | FIELD | COVERED | §19.2, SIG-ONTO-027 | No camera abstraction forced; service-area polygons. |
| `OL-4.6-01` | REQ | COVERED | SIG-ONTO-026, §19.2 | Deployment with no PhysicalAsset row. |
| `OL-4.7-01` | SOURCE | COVERED | §22.7 | All four FR datasets in the backlog. *(closed in the gap-closure pass.)* |
| `OL-4.7-02` | ENTITY | COVERED | SIG-ONTO-031 | Reference databases as DataSystems. |
| `OL-4.8-01` | REQ | COVERED | §13.1 device-forensics, §11.6 extract.* | Investigative extraction capabilities modelled. |
| `OL-4.9-01` | REQ | COVERED | Appendix D.5 pathway 3 | Extended to six layers (aggregator ≠ productizer). |
| `OL-4.9-02` | PRINCIPLE | COVERED | §1.4, §12.3, SIG-ONTO-026 | Access relationships without hardware. |
| `OL-4.10-01` | REQ | COVERED | §13.1 | All nine RTCC inputs representable. *(closed in the gap-closure pass.)* |
| `OL-4.10-02` | REQ | COVERED | §12.3, §12.9 | Thirteen typed integration edges replace integrates_with. |

### 5. International landscape

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-5-01` | REQ | COVERED | §5.1, §5.3 | US-first rationale; twelve wedge conditions. |
| `OL-5-02` | PRINCIPLE | COVERED | SIG-CHART-029 | International from the beginning. |
| `OL-5.1-01` | REQ | COVERED | SIG-CHART-030 |  |
| `OL-5.2-01` | SOURCE | COVERED | Phase 18 | Full technology coverage named. *(closed in the gap-closure pass.)* |
| `OL-5.2-02` | REQ | COVERED | Phase 18 | The OSM-vs-own-database debate recorded as federation precedent. *(closed in the gap-closure pass.)* |
| `OL-5.2-03` | REQ | COVERED | Phase 18 | The ~12,000-camera import is the studied precedent for contribution-back. *(closed in the gap-closure pass.)* |
| `OL-5.3-01` | SOURCE | COVERED | §22.7, SIG-ENG-036 | Registered; coarse granularity mandatory. *(closed in the gap-closure pass.)* |
| `OL-5.3-02` | REQ | COVERED | SIG-ONTO-021 | Record the coarsest level the evidence supports. |

### 6. What is missing from the ecosystem

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-6-00` | REQ | COVERED | §1.3 SIG-CHART-001 | General reconciliation layer. |
| `OL-6.1-01` | REQ | COVERED | §14.1 | LAPD example preserved verbatim. |
| `OL-6.1-02` | REQ | COVERED | §14.1, §14.2 | Per-class canonical identifier table. |
| `OL-6.1-03` | PRINCIPLE | COVERED | §14, P6, Phase 3/5 ordering | ER gates block analytics surfaces. |
| `OL-6.2-01` | EXAMPLE | COVERED | §8.5 SIG-ONTO-008 | Target statement reproduced verbatim in substance. |
| `OL-6.2-02` | PRINCIPLE | COVERED | SIG-ONTO-008 | Reconciliation as a first-class addressable object. |
| `OL-6.3-01` | REQ | COVERED | §9, §29.4 | Five temporal dimensions; lifecycle reconciliation. |
| `OL-6.3-02` | PRINCIPLE | COVERED | §9.2, §9.3, §12.1 | valid_*_kind corrects the NULL ambiguity. |
| `OL-6.4-01` | PRINCIPLE | COVERED | §10.1, §16.2 | Provenance attaches at claim level, not entity level. |
| `OL-6.5-01` | PRINCIPLE | COVERED | §31, §28.5, SIG-STORE-015 | UNRESOLVED publishable with all dissent attached. |
| `OL-6.5-02` | PRINCIPLE | COVERED | SIG-RECON-057 | Every detector emits a task with a closing condition. |
| `OL-6.6-01` | REQ | COVERED | §30.2, §12.3 | Access-path closure across vendors. |
| `OL-6.7-01` | VOCAB | COVERED | §13.4 | All fourteen states retained across four tracks; ten added. |
| `OL-6.7-02` | PRINCIPLE | COVERED | SIG-ONTO-062, SIG-RECON-041 | replaced is an edge, not a state. |

### 7. Project definition

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-7-01` | PURPOSE | COVERED | §1.1 |  |
| `OL-7-02` | PRINCIPLE | COVERED | §43.1 SIG-PUB-001 |  |
| `OL-7.1-01` | REQ | COVERED | §4.1 G1 | Bound to Phase 3 and a metric. |
| `OL-7.1-02` | REQ | COVERED | §4.1 G2 |  |
| `OL-7.1-03` | REQ | COVERED | §4.1 G3, §32.3 | Target 100% resolvable evidence. |
| `OL-7.1-04` | REQ | COVERED | §4.1 G4, §9 |  |
| `OL-7.1-05` | REQ | COVERED | §4.1 G5, §12 |  |
| `OL-7.1-06` | REQ | COVERED | §4.1 G6, §32.2 |  |
| `OL-7.1-07` | REQ | COVERED | §4.1 G7, §33 |  |
| `OL-7.1-08` | REQ | COVERED | §4.1 G8, §37–§39 | Seven audiences named. |
| `OL-7.2-01` | NONGOAL | COVERED | N1, SIG-STORE-026 | No plate-capable column; schema test. |
| `OL-7.2-02` | NONGOAL | COVERED | N2, §18.1, §24.2 |  |
| `OL-7.2-03` | NONGOAL | COVERED | N3, §43.4 | Five-prong test, two concurring reviewers. |
| `OL-7.2-04` | NONGOAL | COVERED | §30.3 | Pointer corrected. *(closed in the gap-closure pass.)* |
| `OL-7.2-05` | NONGOAL | COVERED | §46.3, SIG-CONTRIB-007 | Pointers corrected. *(closed in the gap-closure pass.)* |
| `OL-7.2-06` | NONGOAL | COVERED | §43.5 SIG-PUB-013 | Pointer corrected. *(closed in the gap-closure pass.)* |
| `OL-7.2-07` | NONGOAL | COVERED | N7, §35.2, SIG-CONTRIB-014 |  |
| `OL-7.2-08` | NONGOAL | COVERED | N8, §6, §35.3 |  |
| `OL-7.2-09` | NONGOAL | COVERED | N9, §11.16 |  |
| `OL-7.2-10` | NONGOAL | COVERED | N10, SIG-CHART-019, §32.2 |  |

### 8. Conceptual graph model (every entity and field is an obligation)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-8.1-01` | ENTITY | COVERED | §11.2 organization_type | All fourteen example classes present, namespaced. |
| `OL-8.1-02` | FIELD | COVERED | §11.2 | All listed fields present as predicates. |
| `OL-8.2-01` | ENTITY | COVERED | SIG-ONTO-012 | Corrected: vendor is a role, not a subtype. |
| `OL-8.2-02` | EXAMPLE | COVERED | §14.5 acquired, §11.4 | Axon→Fusus expressible with time bounds. |
| `OL-8.2-03` | PRINCIPLE | COVERED | §11.4 product_name/vendor time-bounded |  |
| `OL-8.3-01` | ENTITY | COVERED | §11.4 | Cellebrite UFED restored. *(closed in the gap-closure pass.)* |
| `OL-8.3-02` | PRINCIPLE | COVERED | SIG-ONTO-017 |  |
| `OL-8.4-01` | ENTITY | COVERED | §11.5, §11.6, §13.1 | All twelve examples present in the 13-domain taxonomy. |
| `OL-8.4-02` | PRINCIPLE | COVERED | P7, §11.5 |  |
| `OL-8.5-01` | ENTITY | COVERED | §11.7 |  |
| `OL-8.5-02` | FIELD | COVERED | §11.7 | All fields retained; counts split per §29.1. |
| `OL-8.6-01` | ENTITY | COVERED | §11.8, SIG-ONTO-027 | Including RTCC facility and camera trailer. |
| `OL-8.6-02` | FIELD | COVERED | §11.8 | All fields present; owner/operator expanded to 14 roles. |
| `OL-8.6-03` | PRINCIPLE | COVERED | SIG-GEO-004 | Coordinates optional; four cases specified. |
| `OL-8.7-01` | ENTITY | COVERED | §11.10 |  |
| `OL-8.7-02` | FIELD | COVERED | §11.10 | Plus system_scope and holds_data_collected_by. |
| `OL-8.8-01` | ENTITY | COVERED | §12.5 |  |
| `OL-8.8-02` | FIELD | COVERED | §12.5, §12.1 | All attributes present plus asserted_by. |
| `OL-8.8-03` | PRINCIPLE | COVERED | SIG-ONTO-049, §12.2 | Direction required; three edge types never merged. |
| `OL-8.9-01` | ENTITY | COVERED | §12.3 | Thirteen typed edges; integrates_with prohibited as stored. |
| `OL-8.10-01` | ENTITY | COVERED | §11.11 |  |
| `OL-8.10-02` | FIELD | COVERED | §11.11 | Plus acquisition_channel and parent_cooperative_contract. |
| `OL-8.10-03` | REQ | COVERED | §23.6, §13.4 track 1, amends_contract |  |
| `OL-8.11-01` | ENTITY | COVERED | §11.13 policy_type | All seven examples present. |
| `OL-8.11-02` | FIELD | COVERED | §11.13 applies_to polymorphic |  |
| `OL-8.12-01` | ENTITY | COVERED | §11.15 | Promoted to first-class time-versioned entity. |
| `OL-8.12-02` | EXAMPLE | COVERED | SIG-ONTO-043, §29.6, SIG-UI-045 | Canonical divergence case rendered without collapse. |
| `OL-8.13-01` | ENTITY | COVERED | §11.16 |  |
| `OL-8.13-02` | FIELD | COVERED | §11.16 | All SearchAggregate fields plus coverage_period. |
| `OL-8.13-03` | PRINCIPLE | COVERED | §18.1, N9 |  |
| `OL-8.14-01` | ENTITY | COVERED | §11.17 event_type | All ten examples present. |
| `OL-8.14-02` | FIELD | COVERED | §11.17 epistemic_status | Required and rendered everywhere. |
| `OL-8.15-01` | ENTITY | COVERED | §10.2 | Split four ways: Source/Artifact/Capture/Extraction. |
| `OL-8.15-02` | FIELD | COVERED | §10.3.2, §10.3.3 | All eleven fields present. |
| `OL-8.15-03` | REQ | COVERED | §10.3.2 artifact_type | All eight examples covered. |
| `OL-8.16-01` | ENTITY | COVERED | §10.3.5 |  |
| `OL-8.16-02` | FIELD | COVERED | §16.2 | `object_type` and `unit` added; `asserted_by` is now an FK. *(closed in the gap-closure pass.)* |
| `OL-8.16-03` | EXAMPLE | COVERED | Appendix D.4 | Worked provenance chain for exactly this shape. |

### 9. Epistemic architecture

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-9-01` | PRINCIPLE | COVERED | §10 | Six distinctions as concrete objects. |
| `OL-9.1-01` | VOCAB | COVERED | §10.4 R1/R2 | Tier A split by directness; mapping table retained. |
| `OL-9.1-02` | VOCAB | COVERED | §10.4 R2 |  |
| `OL-9.1-03` | VOCAB | COVERED | §10.4 R3 | Upturn restored to the R3 examples. *(closed in the gap-closure pass.)* |
| `OL-9.1-04` | VOCAB | COVERED | §10.4 R4 |  |
| `OL-9.1-05` | VOCAB | COVERED | §10.4 R5 |  |
| `OL-9.1-06` | VOCAB | COVERED | §10.4 R6, SIG-LLM-005 |  |
| `OL-9.1-07` | PRINCIPLE | COVERED | SIG-EPIS-015, §10.5 | Novelty ≠ unreliability; D6 is admissibility, not rank. |
| `OL-9.2-01` | PRINCIPLE | COVERED | §9.1, §9.2 SIG-TIME-002/003 | Portal example reproduced; T1 never inferred at ingest. |
| `OL-9.3-01` | PRINCIPLE | COVERED | SIG-EPIS-022 | Numeric confidence prohibited unless calibrated. |
| `OL-9.3-02` | VOCAB | COVERED | §10.7 | Three orthogonal fields; all six labels recoverable. |
| `OL-9.4-01` | PRINCIPLE | COVERED | §9.5, §32.1 | Four epistemic states; CoverageRecord. |
| `OL-9.4-02` | EXAMPLE | COVERED | §32.1, SIG-UI-012 | sources_searched[] required. |
| `OL-9.4-03` | REQ | COVERED | SIG-TIME-012, SIG-API-003, SIG-UI-007 |  |

### 10. Source ingestion strategy

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-10.1A-01` | STAGE | COVERED | Phase 3, §14 | Identity registry before anything is counted. |
| `OL-10.1A-02` | REQ | COVERED | §14.2 | All seven identity aids present. |
| `OL-10.1B-01` | STAGE | COVERED | §23.2, Phase 4 | ID, version, tags, coordinates, attribution preserved. |
| `OL-10.1B-02` | PRINCIPLE | COVERED | N7, SIG-CONTRIB-014 |  |
| `OL-10.1C-01` | STAGE | COVERED | §23.3, Phase 4 |  |
| `OL-10.1C-02` | REQ | COVERED | §20.3 SIG-STORE-039 | Explicit Atlas crosswalk with lossy flags. |
| `OL-10.1D-01` | STAGE | COVERED | §22.5, Phase 11 gate |  |
| `OL-10.1D-02` | REQ | COVERED | §23.4 | Hotlist hits and vehicles-detected added. *(closed in the gap-closure pass.)* |
| `OL-10.1E-01` | STAGE | COVERED | §18.1, §23.7 | No plate/search rows ingested. |
| `OL-10.1E-02` | REQ | COVERED | §23.7, §11.16 | Structural aggregates only; custody stays upstream. |
| `OL-10.1F-01` | STAGE | COVERED | §23.5, §23.6, Phase 7 |  |
| `OL-10.1G-01` | STAGE | COVERED | §23.8, Phase 13 |  |

### 11. Reconciliation workflows

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-11.1-01` | REQ | COVERED | §29.1 | All six input classes as distinct predicates. |
| `OL-11.1-02` | FIELD | COVERED | §29.1 SIG-RECON-029 | Every count predicate with its own resolution + deltas. |
| `OL-11.1-03` | PRINCIPLE | COVERED | SIG-RECON-028/029, SIG-STORE-015 | PREDICATE_CONFLATION; no single true count. |
| `OL-11.2-01` | REQ | COVERED | §29.2 | Candidate generation spec + probable label at L4. |
| `OL-11.2-02` | REQ | COVERED | §29.2 SIG-RECON-033, §33.2 #5 | Human/documentary promotion only. |
| `OL-11.3-01` | REQ | COVERED | §29.3, §12.2 | All five source types kept distinct. |
| `OL-11.3-02` | PRINCIPLE | COVERED | SIG-ONTO-042, SIG-RECON-034 | No operation merges the three edge types. |
| `OL-11.4-01` | EXAMPLE | COVERED | §29.4, §13.4 | Four-track timeline; unordered-within-window for fuzzy dates. |

### 12. Research task generation

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-12-00` | REQ | COVERED | Part VI preamble, §33 |  |
| `OL-12-01` | REQ | COVERED | §33.2 #1 |  |
| `OL-12-02` | REQ | COVERED | §33.2 #2 |  |
| `OL-12-03` | REQ | COVERED | §33.2 #3, §29.5 |  |
| `OL-12-04` | REQ | COVERED | §33.2 #4, §28.3 |  |
| `OL-12-05` | REQ | COVERED | §33.2 #5, SIG-ONTO-028 |  |
| `OL-12-06` | REQ | COVERED | §33.2 #6, §14.4 |  |
| `OL-12-07` | REQ | COVERED | §33.2 #7, SIG-RECON-041 |  |
| `OL-12-08` | PURPOSE | COVERED | Part VI, §7 leverage metrics |  |

### 13. Ethical and security constraints

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-13-00` | PRINCIPLE | COVERED | SIG-CHART-024, §44 |  |
| `OL-13.1-01` | PRINCIPLE | COVERED | SIG-CHART-024, §43.1 |  |
| `OL-13.1-02` | REQ | COVERED | §18.1, N9 |  |
| `OL-13.2-01` | REQ | COVERED | §43.2 | All six categories excluded; addresses made categorical. |
| `OL-13.2-02` | REQ | COVERED | §43.4 | Five prongs + two concurring reviewers. |
| `OL-13.3-01` | REQ | COVERED | §43.3, §19.4 | Five-class matrix covering all five listed cases. |
| `OL-13.4-01` | REQ | COVERED | §17.5, SIG-EVID-010/011 | Sealed tier + public metadata + redacted derivative. |
| `OL-13.5-01` | REQ | COVERED | SIG-CHART-023 |  |
| `OL-13.5-02` | NONGOAL | COVERED | SIG-CHART-023, SIG-GOV-018 |  |

### 14. Licensing and data governance

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-14.1-01` | REQ | COVERED | §42.3 |  |
| `OL-14.1-02` | REQ | COVERED | §42.3 point 4 | Strategy A analysed and rejected with the guideline text. |
| `OL-14.1-03` | REQ | COVERED | §42.3 SIG-LIC-006 | Strategy B adopted. |
| `OL-14.1-04` | REQ | COVERED | §42.3 point 5 | Strategy C analysed and rejected. |
| `OL-14.1-05` | REQ | COVERED | SIG-LIC-009 | Four residuals referred to counsel and in the risk register. |
| `OL-14.2-01` | FIELD | COVERED | §42.1 SIG-LIC-001 | All six fields; redistributable separately reviewed. |
| `OL-14.2-02` | PRINCIPLE | COVERED | SIG-LIC-004 | UNDETERMINED fails the export gate closed. |
| `OL-14.3-01` | PRINCIPLE | COVERED | SIG-LIC-012 |  |
| `OL-14.3-02` | REQ | COVERED | SIG-LIC-012, §38 | All seven deliverables required for a release. |

### 15. Product surfaces

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-15.1-01` | SURFACE | COVERED | §39.2 |  |
| `OL-15.1-02` | FIELD | COVERED | §39.2, Appendix D | All fifteen output elements present. |
| `OL-15.1-03` | PRINCIPLE | COVERED | SIG-UI-002/010 | Dossier is the design center and primary artifact. |
| `OL-15.2-01` | SURFACE | COVERED | §39.3 | All seven layers plus a bound coverage underlay. |
| `OL-15.3-01` | SURFACE | COVERED | §39.4, §30.2 | Ego network; all four questions answerable. |
| `OL-15.4-01` | SURFACE | COVERED | §39.5 | Plus iCal/RSS subscriptions. |
| `OL-15.5-01` | SURFACE | COVERED | §39.6 | All eight expansions present. |
| `OL-15.6-01` | SURFACE | COVERED | §39.7, §33 | Task cards with closing conditions. |
| `OL-15.7-01` | SURFACE | COVERED | §38.4 | Six downstream classes as validated design targets. *(closed in the gap-closure pass.)* |

### 16. Initial release boundaries

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-16-01` | REQ | COVERED | SIG-CHART-025 |  |
| `OL-16-02` | REQ | COVERED | §5.1 | All twelve conditions enumerated. |
| `OL-16-03` | VOCAB | COVERED | SIG-CHART-026 | All six vendors. |
| `OL-16-04` | REQ | COVERED | SIG-CHART-027/028 | Generalization conformance suite from Phase 4. |

### 17. Staged project plan

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-17.0-01` | STAGE | COVERED | Phase 0 deliverable 4 | Extended from seven to nineteen projects. |
| `OL-17.0-02` | STAGE | COVERED | Phase 0 deliverables 2–4, §22.1 |  |
| `OL-17.1-01` | STAGE | COVERED | Phases 1–4 |  |
| `OL-17.1-02` | STAGE | COVERED | Phase 4 / Phase 6 acceptance |  |
| `OL-17.2-01` | STAGE | COVERED | Phase 8, §29 |  |
| `OL-17.2-02` | STAGE | COVERED | Phase 8 acceptance |  |
| `OL-17.3-01` | STAGE | COVERED | Phase 12, §23.7 |  |
| `OL-17.3-02` | STAGE | COVERED | Phase 12, §30.2 |  |
| `OL-17.4-01` | STAGE | COVERED | Phase 13, §11.13/11.14/11.17 |  |
| `OL-17.4-02` | STAGE | COVERED | Phase 13 acceptance |  |
| `OL-17.5-01` | STAGE | COVERED | Phase 17 | Priority order preserved exactly. |
| `OL-17.6-01` | STAGE | COVERED | Phase 18 | (§5.3 mis-cites this as Phase 14 — see DEFECTS.) |

### 18. Relationship to existing projects (the whole table is an obligation)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-18-01` | REQ | COVERED | §6 row 1 |  |
| `OL-18-02` | REQ | COVERED | §6 row 2 |  |
| `OL-18-03` | REQ | COVERED | §6 row 3, §22.5 |  |
| `OL-18-04` | REQ | COVERED | §6 row 4, §23.7 |  |
| `OL-18-05` | REQ | COVERED | §6 row 5, §24.2 |  |
| `OL-18-06` | REQ | COVERED | §6 row 6, §23.3 |  |
| `OL-18-07` | REQ | COVERED | §23.9 | Connector + corrected pointer. *(closed in the gap-closure pass.)* |
| `OL-18-08` | REQ | COVERED | §6 row 8, §23.8 |  |
| `OL-18-09` | REQ | COVERED | §6 row 10, §11.19 |  |
| `OL-18-10` | REQ | COVERED | §6 row 12, §38 |  |
| `OL-18-11` | REQ | COVERED | §6 row 13, §23.9 |  |
| `OL-18-12` | REQ | COVERED | §6 row 14, §43.5 |  |
| `OL-18-13` | REQ | COVERED | §6 row 15, §33.7 | Corrected: SIG maintains its own registry. |
| `OL-18-14` | REQ | COVERED | §6 row 16, §33.5 |  |
| `OL-18-15` | REQ | COVERED | §6 row 17, Phase 18 |  |
| `OL-18-16` | REQ | COVERED | §6 row 18 |  |
| `OL-18-17` | REQ | COVERED | §6 row 19, §30 labelling |  |

### 19. Data-quality principles (each is an architectural invariant)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-19.1` | PRINCIPLE | COVERED | §3.2 P1 | No writable current-value columns; no_orphan_facts CI check. |
| `OL-19.2` | PRINCIPLE | COVERED | §3.2 P2 | raw_value NOT NULL. |
| `OL-19.3` | PRINCIPLE | COVERED | §3.2 P3 | UPDATE revoked at role level; §45.4 adds suppression. |
| `OL-19.4` | PRINCIPLE | COVERED | §3.2 P4 | UNRESOLVED first-class. |
| `OL-19.5` | PRINCIPLE | COVERED | §3.2 P5 | Contribution-back is a funded phase. |
| `OL-19.6` | PRINCIPLE | COVERED | §3.2 P6 | Phase ordering + ER quality gates + UI disclosure. |
| `OL-19.7` | PRINCIPLE | COVERED | §3.2 P7 | No vendor name in any schema identifier. |
| `OL-19.8` | PRINCIPLE | COVERED | §3.2 P8, §12.4 | Extended from six roles to fourteen. |
| `OL-19.9` | PRINCIPLE | COVERED | §3.2 P9, §12.2 |  |
| `OL-19.10` | PRINCIPLE | COVERED | §3.2 P10, §29.6 |  |
| `OL-19.11` | PRINCIPLE | COVERED | §3.2 P11, §29.1 |  |
| `OL-19.12` | PRINCIPLE | COVERED | §3.2 P12, §32.4, SIG-TIME-005 |  |

### 20. Mandatory research questions (all 37 must be answered in the spec)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-Q01` | Q | COVERED | Appendix B Q1 | **ANSWERED** — public unauthenticated JSON API verified (SC-18). Phase 11 ungated. *(closed in the completion pass.)* |
| `OL-Q02` | Q | COVERED | Appendix B Q2 | **ANSWERED** — ~9.5mo per-portal history + 29 archived API captures. *(closed in the completion pass.)* |
| `OL-Q03` | Q | COVERED | Appendix B Q3 | **ANSWERED: CC BY-SA 4.0.** ShareAlike forced the N-compartment licence model. *(closed in the completion pass.)* |
| `OL-Q04` | Q | COVERED | Appendix B Q4 | **ANSWERED** — record types + fields documented; licence: none stated. *(closed in the completion pass.)* |
| `OL-Q05` | Q | COVERED | Appendix B Q5 | **ANSWERED** — 15 GitLab repos, REST API, open bulk archive. *(closed in the completion pass.)* |
| `OL-Q06` | Q | COVERED | Appendix B Q6 | Bulk CSV; EFF device-layer delegation recorded. |
| `OL-Q07` | Q | COVERED | Appendix B Q7 | api_v2, 401, JWT, rate limit — outline corrected. |
| `OL-Q08` | Q | COVERED | Appendix B Q8 | Called successfully. |
| `OL-Q09` | Q | COVERED | Appendix B Q9, §14.2 | ORI9 + LEAIC. |
| `OL-Q10` | Q | COVERED | Appendix B Q10, §14.2/14.4 | Per-class identifiers + two ORI traps. |
| `OL-Q11` | Q | COVERED | Appendix B Q11 | GEOID/GNIS/GeoNames; fixed-width + level. |
| `OL-Q12` | Q | COVERED | Appendix B Q12, §14.4 | Surrogate + identity_basis + aggregate publication. |
| `OL-Q13` | Q | COVERED | Appendix B Q13, §42.3 | Guideline conflict analysed; conservative reading. |
| `OL-Q14` | Q | COVERED | Appendix B Q14 | Answered 'not by separation alone'; Strategy B. |
| `OL-Q15` | Q | COVERED | Appendix B Q15 | **ANSWERED** — 4 of 6 have no licence or an affirmative refusal; export gate closed against them. *(closed in the completion pass.)* |
| `OL-Q16` | Q | COVERED | Appendix B Q16, §8.4 | custody_posture enforced before fetch. |
| `OL-Q17` | Q | COVERED | Appendix B Q17 | **ANSWERED** — cadence set by the upstream refresh (~monthly), not by SIG. *(closed in the completion pass.)* |
| `OL-Q18` | Q | COVERED | Appendix B Q18, §17.6 |  |
| `OL-Q19` | Q | COVERED | Appendix B Q19 | **VERIFIED** — history API tested; surfaced the element-repurposing dating trap. *(closed in the completion pass.)* |
| `OL-Q20` | Q | COVERED | Appendix B Q20, §15.1 | Hybrid with relational core; scored. |
| `OL-Q21` | Q | COVERED | Appendix B Q21, §15.3 |  |
| `OL-Q22` | Q | COVERED | Appendix B Q22, §18 |  |
| `OL-Q23` | Q | COVERED | Appendix B Q23, §21.3 |  |
| `OL-Q24` | Q | COVERED | Appendix B Q24, §26 | Reframed as four legal tracks. |
| `OL-Q25` | Q | COVERED | Appendix B Q25, §17.2/17.3/17.4 |  |
| `OL-Q26` | Q | COVERED | Appendix B Q26, §24 | Seven-layer ladder. |
| `OL-Q27` | Q | COVERED | Appendix B Q27, §14.6 | Tiers 0–3. |
| `OL-Q28` | Q | COVERED | Appendix B Q28, §14.6 | Tiers 4–5 to review; LLMs may not write. |
| `OL-Q29` | Q | COVERED | Appendix B Q29, §14.5 | Rename ≠ succession; five fixtures. |
| `OL-Q30` | Q | COVERED | Appendix B Q30, §43 |  |
| `OL-Q31` | Q | COVERED | Appendix B Q31, SIG-EVID-010 |  |
| `OL-Q32` | Q | COVERED | Appendix B Q32, §45 | Includes suppression as a distinct primitive. |
| `OL-Q33` | Q | COVERED | Appendix B Q33 | **ANSWERED** — CoC read; human review is outside its scope; MapRoulette verified. *(closed in the completion pass.)* |
| `OL-Q34` | Q | COVERED | Appendix B Q34 | PARTIAL answer, honestly labelled; Stage-0 item. |
| `OL-Q35` | Q | COVERED | Appendix B Q35 | PARTIAL answer; task→RecordsRequest model specified regardless. |
| `OL-Q36` | Q | COVERED | Appendix B Q36, §33.5 |  |
| `OL-Q37` | Q | COVERED | Appendix B Q37, §14.8 |  |

### 21. Priority source registry (every URL must appear in the spec's source registry)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-21-01` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-02` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-03` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-04` | SOURCE | COVERED | §22.6 A | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-05` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-06` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-07` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-08` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-09` | SOURCE | COVERED | §22.6 B | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-10` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-11` | SOURCE | COVERED | §22.6 C | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-12` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-13` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-14` | SOURCE | COVERED | §22.6 C | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-15` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-16` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-17` | SOURCE | COVERED | §22.6 D | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-18` | SOURCE | COVERED | §22.6 D, §22.7 | URL seeded + roster. *(closed in the gap-closure pass.)* |
| `OL-21-19` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-20` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-21` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-22` | SOURCE | COVERED | §22.6 E | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-23` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-24` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-25` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-26` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-27` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-28` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-29` | SOURCE | COVERED | §22.6 I | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-30` | SOURCE | COVERED | §22.7 | All ten classes enumerated. *(closed in the gap-closure pass.)* |
| `OL-21-31` | SOURCE | COVERED | §22.6 E | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-32` | SOURCE | COVERED | §22.6 E | URL seeded + leak-provenance veto. *(closed in the gap-closure pass.)* |
| `OL-21-33` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-34` | SOURCE | COVERED | §22.6 E | URL seeded. *(closed in the gap-closure pass.)* |
| `OL-21-35` | SOURCE | COVERED | §22.6 | URL seeded in the registry. *(closed in the gap-closure pass.)* |
| `OL-21-36` | SOURCE | COVERED | §22.6 C | URL seeded, paywalled. *(closed in the gap-closure pass.)* |
| `OL-21-37` | SOURCE | COVERED | §22.6 B/H | Both threads registered; Reddit is manual-reference only. *(closed in the gap-closure pass.)* |

### 22. Critical conclusions

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-22.1-01` | PRINCIPLE | COVERED | §3.7 SIG-CHART-020 | Full fact→generator table reproduced. |
| `OL-22.1-02` | PRINCIPLE | COVERED | §3.7, Part V |  |
| `OL-22.2-01` | PURPOSE | COVERED | §3.6 SIG-CHART-018 | Authority claim stated verbatim as a bounded claim. |
| `OL-22.3-01` | PRINCIPLE | COVERED | §5.2 rationale | capability→deployment→assets/data/access. |
| `OL-22.4-01` | PRINCIPLE | COVERED | §30.2, §12.9, §39.4 | All seven central questions answerable. |
| `OL-22.4-02` | REQ | COVERED | §39.4, §30.2, P6 | Central, but gated on ER quality. |
| `OL-22.5-01` | PRINCIPLE | COVERED | §13.4, §28.3, Appendix G | Current dynamics modelled as state + edge changes. |
| `OL-22.5-02` | REQ | COVERED | SIG-RECON-041/042 | Canceled+installed stated plainly in UI and API. |
| `OL-22.6-01` | PURPOSE | COVERED | §7, §32.6 | All six leverage measures instrumented. |
| `OL-22.6-02` | PURPOSE | COVERED | SIG-CHART-035, §46.5 |  |

### 23. One-sentence specification

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-23-01` | PURPOSE | COVERED | §1.1 | Preserved verbatim. |

### 24. Guidance to the downstream design agent (all 18 are binding)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-24-01` | REQ | COVERED | Appendix G, §22.2 | Ecosystem re-verified; 14 factual corrections. |
| `OL-24-02` | REQ | COVERED | §22.2 access matrix | VERIFIED = a request was made and observed. |
| `OL-24-03` | REQ | COVERED | §22.2, SIG-INGEST-024 | Access verified, not assumed. |
| `OL-24-04` | REQ | COVERED | §14, Phase 3/5 before Phase 12 | ER precedes analytics by phase order. |
| `OL-24-05` | REQ | COVERED | Phases 1–2 before Phase 4 |  |
| `OL-24-06` | REQ | COVERED | §42.3, R-01, Phase 0/4 |  |
| `OL-24-07` | REQ | COVERED | SIG-CHART-014, §8.4 custody postures |  |
| `OL-24-08` | REQ | COVERED | SIG-STORE-043, §14.2 |  |
| `OL-24-09` | REQ | COVERED | §8.1 six layers | L0/L1/L3/L4 physically separated. |
| `OL-24-10` | REQ | COVERED | §18.1, N2, OL-A.8 |  |
| `OL-24-11` | REQ | COVERED | §31, SIG-EPIS-011, SIG-UI-009 |  |
| `OL-24-12` | REQ | COVERED | §33.1/§33.2, §39.7 |  |
| `OL-24-13` | REQ | COVERED | SIG-CHART-025/027 |  |
| `OL-24-14` | REQ | COVERED | §12.4, §12.3 enrolls_asset_into, §14.4 |  |
| `OL-24-15` | REQ | COVERED | SIG-ONTO-026/031, §19.2 |  |
| `OL-24-16` | REQ | COVERED | SIG-ONTO-062, SIG-RECON-041 |  |
| `OL-24-17` | REQ | COVERED | §37, §38, SIG-LIC-004 |  |
| `OL-24-18` | REQ | COVERED | §10.1, SIG-PARSE-003, Appendix D.4 |  |
| `OL-24-19` | PRINCIPLE | COVERED | §3.1 | Preserved verbatim; §3.3 binds each clause. |
| `OL-24-20` | PRINCIPLE | COVERED | §3.1, §3.3 | Preserved verbatim with enforcement points. |

### Appendix A — findings that changed the conception

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-A.1` | REQ | COVERED | §22.5, R-02, Phase 0 gate |  |
| `OL-A.2` | REQ | COVERED | §33.5, §33.7, §34 |  |
| `OL-A.3` | REQ | COVERED | §5.2 rationale, §13.4 |  |
| `OL-A.4` | REQ | COVERED | §22.2, §12.4, §14.4 |  |
| `OL-A.5` | REQ | COVERED | §1.4, §12.5 |  |
| `OL-A.6` | REQ | COVERED | §13.4 |  |
| `OL-A.7` | REQ | COVERED | §10, §16.2 |  |
| `OL-A.8` | REQ | COVERED | §18.1, §8.4 DERIVE posture |  |

### Appendix B — illustrative local dossier (the spec must be able to emit this exact object)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-B-01` | FIELD | COVERED | Appendix D, §11.1 |  |
| `OL-B-02` | FIELD | COVERED | Appendix D, §11.2 |  |
| `OL-B-03` | FIELD | COVERED | Appendix D.2 | Split into three predicates with separate resolutions. |
| `OL-B-04` | FIELD | COVERED | §11.11, §39.5, SIG-UI-015 |  |
| `OL-B-05` | FIELD | COVERED | Appendix D.3, §29.5 | Split into three retention predicates. |
| `OL-B-06` | FIELD | COVERED | Appendix D.3, §12.2 | Split configured vs observed. |
| `OL-B-07` | FIELD | COVERED | Appendix D.3, §11.16, SIG-RECON-011 | Windowed predicate with explicit bounds. |
| `OL-B-08` | FIELD | COVERED | Appendix D.3, §29.2 |  |
| `OL-B-09` | FIELD | COVERED | Appendix D.3, §9.5, SIG-UI-015 | 'unknown' rendered, not omitted. |
| `OL-B-10` | FIELD | COVERED | §11.17, SIG-UI-010 |  |
| `OL-B-11` | FIELD | COVERED | Appendix D.2, §33.2 | Detectors 1,2,3,4,27 cover the five listed gaps. |
| `OL-B-12` | REQ | COVERED | §1.3, §39.2, SIG-CHART-002 |  |

### Appendix C — illustrative surveillance pathways (all three must be representable and traversable)

| OL id | Type | Disposition | Discharged by | Note |
|---|---|---|---|---|
| `OL-C-01` | EXAMPLE | COVERED | Appendix D.5 pathway 1 | enrolls_asset_into sharpens 'streams_via'. |
| `OL-C-02` | EXAMPLE | COVERED | Appendix D.5 pathway 2 | Directional, scoped, dated, separately evidenced. |
| `OL-C-03` | EXAMPLE | COVERED | Appendix D.5 pathway 3 | Six layers, not five. |
| `OL-C-04` | PURPOSE | COVERED | Appendix D.5, §30.2 |  |
## A.4 Maintenance

**SIG-ENG-037 (MUST).** This matrix MUST be regenerated at every phase gate (SIG-ENG-031) from
`OUTLINE_TRACE.md` plus the current spec, and a CI check MUST fail if any row's disposition
regresses from `COVERED`. The superset property is not a one-time claim; it is an invariant a later
edit can break.

**SIG-ENG-038 (SHOULD).** The regeneration SHOULD first **split compound trace rows** whose members
are independently satisfiable. The adversarial review identified this as a real weakness: a row
folding seven technologies into one obligation can be six-sevenths discharged without turning red,
which is precisely how one missing technology escaped detection in the first pass.

