# Adversarial Gap Analysis — `2_canonical_design_spec.md` vs `1_deep_research_overview.md`

**Method.** Every one of the 480 `OL-*` obligations in `OUTLINE_TRACE.md` was walked against the
6,354-line spec. Keyword matches were not accepted as discharge; the test applied was *would a
coding agent executing only the spec produce what the outline requires?* Cross-references,
requirement identifiers, and named entities were additionally checked mechanically.

**Date:** 2026-08-20 · **Spec version reviewed:** 1.0.0

---

## 1. Summary

| Disposition | Count | Share |
|---|---:|---:|
| COVERED | 395 | 82.3% |
| **PARTIAL** | 58 | 12.1% |
| **GAP** | 27 | 5.6% |
| **CONTRADICTED** (OL-row level) | 0 | 0% |
| **Total** | **480** | |

**Plus four CONTRADICTED findings that are not OL-row dispositions** — they are contradictions of
the spec's *own* load-bearing self-claims, and one of them invalidates the superset proof itself.
See §3.

**The headline.** The spec is genuinely excellent on model, epistemics, temporality, resolution,
governance, and phasing — it deepens the outline substantially and its corrections in Appendix G are
well-evidenced. It fails in one systematic way and one structural way:

1. **The source layer evaporated.** The spec contains **exactly one URL in 6,354 lines**, and that
   one is a placeholder (`https://<host>/id/<type>/<uuid>`). OL-21's obligation is literally *"every
   URL must appear in the spec's source registry."* Fifteen of the 37 registry entries are absent
   entirely — including the ACLU *Get the Flock Out* toolkit, the entire EFF Data Library
   specialist-dataset roster, `flock.ajith.fyi`/Monahan 2026, the WIRED ShotSpotter leak, and the
   Guardian vendor-replacement reporting. Twenty-two more survive as bare names with no locator.
   Phase 0's deliverable "source registry seeded with every source in OL-21" is therefore
   **unexecutable from the spec alone**, which violates SIG-ENG-001.
2. **Three appendices are referenced and do not exist.** Appendix A is asserted in §0.1 as *the
   proof* of the superset claim. Appendix C is asserted in §16 as the home of every domain entity
   table's DDL. Neither exists. The spec has Appendices B, D, and G only.

---

## 2. The full 480-row coverage ledger

| OL id | disposition | spec section | note |
|---|---|---|---|
| `OL-ES-01` | COVERED | §1.3, §6 | SIG positioned as the missing reconciliation layer. |
| `OL-ES-02` | COVERED | §2.1 Q-1…Q-13 | All thirteen mapped to a carrier + acceptance query. |
| `OL-ES-03` | COVERED | SIG-CHART-007 | Joining burden stated as the central architectural obligation. |
| `OL-ES-04` | COVERED | §6, §22.2, §23.2 | OSM = upstream canonical device geography. |
| `OL-ES-05` | COVERED | §6, §22.2 | DeFlock role: contributors upstream to OSM; do not fork. |
| `OL-ES-06` | COVERED | §6, §22.5 | EoF = portal temporal layer; Phase 0 blocking dependency. |
| `OL-ES-07` | COVERED | §6, §23.7, N9 | HIBF = audit specialist; SIG holds structural aggregates only. |
| `OL-ES-08` | COVERED | §6, §22.2, G C-02 | Role preserved; scope corrected (now routing/offline, GitLab). |
| `OL-ES-09` | COVERED | §6, §23.3 | Atlas = primary deployment seed. |
| `OL-ES-10` | **PARTIAL** | §6, §8.3 Layer D | **Named only.** EFF/MuckRock Data Driven has no §22.2 registry row, no access verification, no §23 connector (§6 cites §23.6, which is the procurement connector), and no phase assignment. |
| `OL-ES-11` | COVERED | §6, §23.8, §10.4 R3 | Accountability Atlas epistemic labels adopted. |
| `OL-ES-12` | COVERED | §6, §23.9, §43.5 | Lead generation only; never confirmed device identification. |
| `OL-ES-13` | COVERED | §6, §22.2, §38 | Downstream consumer; publish reusable higher-order data. |
| `OL-ES-14` | COVERED | §6, §33.7, G C-03 | FlockReporter unreachable; SIG maintains its own registry. |
| `OL-ES-15` | COVERED | §6, §11.19, §23.5 | MuckRock modelled as RecordsRequest evidence substrate. |
| `OL-ES-16` | **PARTIAL** | §13.1, §5.2 | Five of seven accommodated. **Body cameras have no home**: none of the 13 domains / 35 families in §13.1 covers body-worn video, and no capability term exists for body-cam live streaming. |
| `OL-ES-17` | COVERED | §22.2, §12.3, G C-06/C-07 | Community Connect verified; Fusus/Flock link severed 2025. |
| `OL-ES-18` | COVERED | §11.4, §43.3, G C-08 | ShotSpotter→SoundThinking rename; 22,471 not 25,000; leak veto. |
| `OL-ES-19` | **PARTIAL** | §11.4, §13.1 | Clearview, cell-site simulators, Vigilant and public-safety drones exist as products/technologies. **Cellebrite is never named**, and none of the historical/specialist *datasets* is a registry entry. |
| `OL-ES-20` | COVERED | §5.3, §13.7, §43.8, Phase 18 | Global physical layer; jurisdiction adapters. |
| `OL-ES-21` | COVERED | SIG-CHART-001 (MUST NOT) | Explicit prohibition on being another surveillance map. |
| `OL-ES-22` | COVERED | §1.1, §3.4, §3.5 | Six defining characteristics bound to sections. |
| `OL-ES-23` | COVERED | §1.2 | Preserved verbatim. |
| `OL-ES-24` | COVERED | §3.5 SIG-CHART-017 | Each characteristic bound to an enforcing section. |
| `OL-ES-25` | COVERED | SIG-CHART-003 | Relationship, not device, as fundamental unit. |
| `OL-ES-26` | COVERED | §1.4 table | All seven manifestations enumerated with why each breaks device-centrism. |
| `OL-ES-27` | COVERED | §11.0 entity index | All 21 classes present; several split, four NEW. |
| `OL-ES-28` | COVERED | SIG-CHART-002 | Joined evidence as the distinctive output. |
| `OL-ES-29` | COVERED | §2.2 J-1, Appendix D, Phase 6 | Full traversal is the Phase-6 gate. |
| `OL-ES-30` | COVERED | §2.2 J-2, §11.16, §32.2 | Coverage statement mandated on the result set. |
| `OL-ES-31` | **PARTIAL** | §2.2 J-3, §39.5 | Renewal watch and mapped counts are fully specified. The **'evidence recommender'** that J-3 depends on is named once in §2.2 and specified nowhere — no requirement id, no section, no phase. |
| `OL-ES-32` | COVERED | §2.2 J-4, §13.4, §29.4 | replaced_by edge + integration classification. |
| `OL-1.1-01` | COVERED | SIG-CHART-004 | Point-only representation rejected. |
| `OL-1.1-02` | COVERED | SIG-CHART-005, §12.9 | All twelve mapped to carriers. |
| `OL-1.1-03` | COVERED | §1.4 rationale | Two-jurisdiction contrast stated verbatim. |
| `OL-1.1-04` | COVERED | SIG-CHART-004 | Graph of capabilities and access. |
| `OL-1.2-01` | COVERED | SIG-CHART-014 | Federation as MUST. |
| `OL-1.2-02` | COVERED | SIG-CHART-015.1 | Do not fork DeFlock. |
| `OL-1.2-03` | COVERED | SIG-CHART-015.2, SIG-CONTRIB-004 | Route device observations to OSM/DeFlock. |
| `OL-1.2-04` | COVERED | SIG-CHART-015.3 |  |
| `OL-1.2-05` | COVERED | SIG-CHART-015.4, N9 |  |
| `OL-1.2-06` | COVERED | SIG-CHART-015.5, SIG-EPIS-008 |  |
| `OL-1.2-07` | COVERED | SIG-CHART-015.6, SIG-CHART-019 |  |
| `OL-1.2-08` | COVERED | SIG-CHART-014.1–7 | All seven positive obligations enumerated. |
| `OL-1.2-09` | COVERED | SIG-CHART-016, §6 | Compact with enforced ingestion_permitted flag. |
| `OL-2A-OSM-01` | COVERED | §19.1, §23.2 | man_made=surveillance population measured (SC-01). |
| `OL-2A-OSM-02` | **PARTIAL** | §23.2, §20.3 | Four surveillance keys and a crosswalk are required, but the spec **never enumerates the real OSM tag vocabulary** the outline demands (surveillance:zone values, camera:mount, camera:direction, ALPR classification). |
| `OL-2A-OSM-03` | COVERED | §22.2, §19.3, Q19 | Overpass, replication diffs, element history. |
| `OL-2A-OSM-04` | COVERED | §6, §42.3 | Neutral substrate; never the canonical editing DB. |
| `OL-2A-OSM-05` | COVERED | SIG-ONTO-006, N7 | Confirmed devices flow to OSM, not a SIG device table. |
| `OL-2A-OSM-06` | COVERED | §42.3, Q13/Q14 | Derivative vs Collective analysed from the actual guidelines. |
| `OL-2A-OSM-07` | **GAP** | — | Neither `https://www.openstreetmap.org/copyright` nor the `Tag:man_made=surveillance` wiki URL appears in the spec. §42.3 reasons from OSMF guidelines without citing a retrievable locator, which is exactly what SIG-LIC-002 requires of every *other* rights determination. |
| `OL-2A-DF-01` | COVERED | §6, §22.2 |  |
| `OL-2A-DF-02` | COVERED | §6, §42.3 |  |
| `OL-2A-DF-03` | COVERED | §6, SIG-CONTRIB-004 |  |
| `OL-2A-DF-04` | COVERED | §6 (do not fork) |  |
| `OL-2A-DF-05` | **GAP** | — | `deflock-data` — the pipeline that extracts ALPR nodes from OSM and produces the GeoJSON/vector-tile artifacts — is never named. §23.2 rebuilds OSM extraction from scratch with no reference to it. Appendix G.4 item 5 admits DeFlock's repository was never determined. |
| `OL-2A-DF-06` | COVERED | §11.8 | osm_version, upstream_id, first/last_observed all present. |
| `OL-2A-DF-07` | COVERED | §29.1, §29.2, §11.8 | Attribution + count reconciliation + orphan state. |
| `OL-2A-SUS-01` | **PARTIAL** | §6 row 18, §22.2 | Named and verified live. **URL `https://sunders.uber.space/` absent** (see OL-21-05). |
| `OL-2A-SUS-02` | COVERED | SIG-CHART-030 | No US-only device schema. |
| `OL-2A-PC-01` | **PARTIAL** | §6 row 19, §22.2 | Named and verified live. **URL absent** (OL-21-06). |
| `OL-2A-PC-02` | COVERED | §19.3 SIG-GEO-006 | Derived geometry physically separate and labelled. |
| `OL-2A-DAF-01` | **PARTIAL** | §6 row 12, §22.2 | Named and verified live. **URL absent** (OL-21-07). 'Corrections flow back to OSM' not restated. |
| `OL-2A-DAF-02` | COVERED | §38, §6 | Reusable higher-order exports; no re-scraping. |
| `OL-2B-FP-01` | COVERED | §22.2, §8.3 Layer B |  |
| `OL-2B-FP-02` | **PARTIAL** | §23.4, §11.15, §11.16 | Nine of twelve portal fields have a predicate. **No home for: 'vehicles detected during a recent interval', 'hotlist hits', and 'stated acceptable/prohibited uses'** (policy_type has `acceptable_use` but nothing binds the portal's own use statement to a deployment). |
| `OL-2B-FP-03` | COVERED | §10.2, §17.6, G C-04 | Portals incomplete; disappearance is data. |
| `OL-2B-FP-04` | **PARTIAL** | §22.5, Phase 11, G C-04 | The outline's REQ is answered with 'no lawful automated path exists'. Honest and well-reasoned, but the obligation is **discharged conditionally on an external outcome recorded as BLOCKED** (Q1/Q2/Q17). |
| `OL-2B-FP-05` | COVERED | §11.2, §12.2, §11.15 | Org types cover federal/university/private; direction required. |
| `OL-2B-FP-06` | **PARTIAL** | §10.2, §17.3 | `hagerstown-md-pd` appears as an example slug. **`green-brook-twp-nj-pd` absent; `https://transparency.flocksafety.com/` never given as a URL.** |
| `OL-2B-EOF-01` | COVERED | §6, §22.5, R-02 | Foundational, Phase-0 blocking. |
| `OL-2B-EOF-02` | **PARTIAL** | §14.4 SIG-IDENT-015 | Slug-grammar parsing is specified. **The load-bearing fact that Flock publishes no portal directory and discovery therefore requires brute-force slug enumeration is never stated**, so an implementer cannot size the discovery problem. |
| `OL-2B-EOF-03` | **PARTIAL** | §23.7, §11.16 | Six of seven EoF outputs modelled. **Hotlist-hit statistics have no predicate anywhere** (only `subscribed_hotlist_topic` configuration). |
| `OL-2B-EOF-04` | COVERED | §22.5, §6 | Discovery/archiving/normalization/aggregation/edge extraction. |
| `OL-2B-EOF-05` | COVERED | SIG-INGEST-030/031 | Ordered fallback; challenge-defeating crawler forbidden. |
| `OL-2B-IND-01` | COVERED | §17.4 SIG-EVID-008, §29.7 | WACZ + screenshot + structured payload + raw HTML. |
| `OL-2B-IND-02` | COVERED | §9.1–9.2, §10.2 | Four-way distinction encoded in the temporal model. |
| `OL-2B-IND-03` | COVERED | §16.3, §17.3, SIG-EVID-006 | Immutability enforced by OCFL + Object Lock + role revocation. |
| `OL-2C-HIBF-01` | COVERED | §6, §23.7 |  |
| `OL-2C-HIBF-02` | COVERED | §11.16 audit_source_type=organization_audit |  |
| `OL-2C-HIBF-03` | **PARTIAL** | §11.16, §23.7 | Organization/camera count/time frame/reason/search timestamp/search type are aggregatable. **Case number, filters, text prompt and moderation information are per-search fields that §18.1 forbids storing** — a defensible correction, but the spec never says so, so a reader cannot tell whether they were dropped deliberately. |
| `OL-2C-HIBF-04` | COVERED | §11.16 audit_source_type=portal_public_audit |  |
| `OL-2C-HIBF-05` | COVERED | §23.7, §12.2 configured_access | SharedNetworks.csv → directional configured-access edges. |
| `OL-2C-HIBF-06` | COVERED | §23.7, §29.4 SIG-RECON-039 | Event-log transitions preferred over inferred ones. |
| `OL-2C-HIBF-07` | COVERED | §11.15 observed_via=config_screenshot | All listed settings are ConfigurationState predicates. |
| `OL-2C-HIBF-08` | **PARTIAL** | §43.4, §36, §14.6 | Duplicate handling, source-agency provenance and records-request templates are covered. **Police rosters have no home**; **audit anomaly detection is absent** (§34.4 covers only contributor anomalies); officer/name resolution is handled by exclusion (SIG-PUB-010) without saying so. |
| `OL-2C-HIBF-09` | COVERED | §11.16, §18.1, N9 |  |
| `OL-2C-AW-01` | COVERED | §6, G C-02 |  |
| `OL-2C-AW-02` | COVERED | §21.1 eight-stage pipeline | Connector architecture mirrors the ALPR Watch shape. |
| `OL-2C-AW-03` | COVERED | §23.5, §24, §17.7 | MuckRock corrected to api_v2; reproducibility enforced. |
| `OL-2C-AW-04` | COVERED | §24.2 SIG-PARSE-005/006 | Versioned, inspectable, reversible; dropdown vs free text split. |
| `OL-2C-AW-05` | COVERED | §10.3.5, §16.2 | raw_value NOT NULL; normalization_id/version; review_status. |
| `OL-2C-AJ-01` | **GAP** | — | `flock.ajith.fyi` and the Monahan, *Grounding the Flock* (2026) academic citation appear nowhere. This is the outline's only scholarly citation and its only named network-visualization precedent. |
| `OL-2C-AJ-02` | COVERED | §39.4, §30.2, §12.9 | Topology as first-class surface. |
| `OL-2D-AT-01` | COVERED | §6, §23.3 |  |
| `OL-2D-AT-02` | **PARTIAL** | §10.4 R3 | Atlas is classified as a reviewed specialist dataset. **The nine methodology components (OSINT, news, government documents, minutes, press releases, procurement leads, crowdsourcing, staff/intern review, imported datasets) are never enumerated**, so the crosswalk's provenance granularity is unspecified. |
| `OL-2D-AT-03` | COVERED | §9.5, §32, SIG-ONTO-059 | Absence encoded; category retirement ≠ world change. |
| `OL-2D-AT-04` | COVERED | §20.3 SIG-STORE-039/040 | Crosswalks with SKOS relations and lossy flags. |
| `OL-2D-AT-05` | **GAP** | — | The entire Atlas Data Library roster is missing: Atlas of Surveillance Border Communities; Who Has Your Face?; public-safety drones; historical Ring/Neighbors partnerships; cell-site simulator datasets; AI Global Surveillance Index; federally funded body cameras; wiretap reports; Aaron Swartz Day Police Surveillance Project; California ALPR survey data; Vigilant Data Driven; Upturn mobile-forensics research; Clearview AI usage data; electronic monitoring; state policy datasets. Only Ring/Neighbors appears, and only as a vocabulary-retirement example. |
| `OL-2D-AT-06` | COVERED | §23.3 | Attribution preserved; supersession allowed. |
| `OL-2D-DD-01` | **PARTIAL** | §6, §8.3 | Named as 'Vendor-neutral ALPR network source'. No registry row, no connector, no phase. See GAP OL-2D-DD-02. |
| `OL-2D-DD-02` | **GAP** | — | None of the Data Driven findings survive: billions of plate observations; hundreds of participating agencies; the very high proportion of non-watchlisted scans; sharing through Vigilant's LEARN ecosystem. 'LEARN' appears only as a product name in an example. These are the empirical facts that justify vendor-neutrality. |
| `OL-2D-DD-03` | COVERED | SIG-CHART-026, §13.1 | Vendor-neutral ALPR family; six vendors in initial scope. |
| `OL-2E-AA-01` | COVERED | §6, §23.8 |  |
| `OL-2E-AA-02` | **PARTIAL** | §22.2, §23.8 | Verified live. **The five published artifacts (issue-record CSV, source-index CSV, GeoJSON, data dictionary, research archive) are never enumerated**, so the connector spec has no target shape. |
| `OL-2E-AA-03` | COVERED | §11.17 event_type | All six categories map to event_type terms. |
| `OL-2E-AA-04` | COVERED | SIG-ONTO-038 | epistemic_status vocabulary adopted directly. |
| `OL-2E-AA-05` | COVERED | SIG-ONTO-038, SIG-UI-043/045 | Allegation never rendered with a factual verb. |
| `OL-2E-AL-01` | COVERED | §6, §23.8 |  |
| `OL-2E-AL-02` | COVERED | SIG-EPIS-030 | Curated index held as an index. |
| `OL-2E-AL-03` | COVERED | SIG-ONTO-039 | All six source classes linkable with class recorded. |
| `OL-2E-AC-01` | **GAP** | — | The ACLU **Get the Flock Out** toolkit is absent from the entire document — not in the §6 federation compact (19 rows), not in §22.2, not in §22.3, no URL. The outline names it as the demonstration of SIG's key downstream user, and §39.2's dossier is built for exactly that user. |
| `OL-2E-AC-02` | COVERED | §39.2, Appendix D | All twelve dossier elements present. |
| `OL-2F-MR-01` | COVERED | §6, §11.19 |  |
| `OL-2F-MR-02` | COVERED | §11.19 | All eight fields present plus statutory_basis and platform. |
| `OL-2F-MR-03` | COVERED | §6, §10.1 | Link to the exact released document. |
| `OL-2F-DC-01` | COVERED | §6, §10.2 | Evidence store, not a citation URL. |
| `OL-2F-DC-02` | COVERED | §10.3.2, §10.3.3 | All ten metadata fields present. |
| `OL-2F-DC-03` | COVERED | §10.3.2 artifact_type | 24-term vocabulary covers all listed genres. |
| `OL-2F-GOV-01` | **PARTIAL** | §22.3, §23.6 | Procurement is deeply covered and materially extended. **GovSpend, which the outline names explicitly as a source of Atlas procurement leads, appears nowhere.** |
| `OL-2F-GOV-02` | **PARTIAL** | §10.3.2, §22.3 | Ten of twelve source classes covered. **'State auditor surveys' and 'warrants' have no artifact_type, no connector, and no registry entry.** |
| `OL-2F-GOV-03` | COVERED | §22.3 A-01/A-02, SIG-ONTO-064 | Procurement precedes mapping; free_trial path. |
| `OL-2G-FF-01` | COVERED | §11.9, §23.9 |  |
| `OL-2G-FF-02` | COVERED | §11.9, SIG-PUB-011/014 | Never conflated with verified hardware. |
| `OL-2G-FF-03` | COVERED | SIG-ONTO-006 | Required flow reproduced verbatim, terminating at OSM. |
| `OL-2G-FY-01` | COVERED | §6, §23.9 |  |
| `OL-2G-FY-02` | COVERED | SIG-ONTO-030 | Full observation protocol required. |
| `OL-2G-FY-03` | COVERED | SIG-PUB-013 | Residential-parcel candidate never published at any precision. |
| `OL-3-01` | **GAP** | — | None of the ~14 named local groups appears: DeFlock Atlanta / Idaho / Birmingham / Joplin / Lynnwood / Olympia / Redmond / Tucson / Vegas; Eyes Off Colorado / Indiana / Cedar Rapids; Live Free VA; Monterey Park. Only `eyesoffcr.org` survives, in a one-line §22.3 row. SIG-TASK-014 requires SIG to build its own registry but Phase 0 has nothing to seed it with. |
| `OL-3-02` | COVERED | §33.7, G C-03, R-12 | Corrected: directory unreachable; SIG builds its own. |
| `OL-3-03` | COVERED | §34, §33.2 | Contributor tiers + task catalog. |
| `OL-3-04` | COVERED | §17.6, §21.4, §29.7, §33.2 #8 | Disappearance/diff/change-feed machinery. |
| `OL-3-05` | COVERED | §33.5, §33.6 | Geographic queues, non-exclusive, expiring. |
| `OL-3-06` | **PARTIAL** | §33.2 #1/#2/#4/#5 | The detectors exist and the object is mechanically producible, but **the spec never produces it**, and **'latest contract amendment missing' has no detector** (`amends_contract` exists in §11.11; no task type fires on its absence). |
| `OL-3-07` | COVERED | Part VI preamble |  |
| `OL-4-00` | COVERED | §5.2, SIG-CHART-027/028 | Generalization conformance suite. |
| `OL-4.1-01` | COVERED | §29.4 SIG-RECON-041 | Vendor replacement rendered as replacement. |
| `OL-4.1-02` | **PARTIAL** | §12.3, §13.1 | Public cameras, private cameras, ALPRs, drones, sensor/dispatch all modelled. **Body-camera live streams are not** — no technology family, no capability term. |
| `OL-4.1-03` | COVERED | §22.2 | Community Connect enumerated and verified. |
| `OL-4.1-04` | COVERED | G C-06 | Corrected: 321 communities; 850k sums incommensurable counters. |
| `OL-4.1-05` | COVERED | §12.4 | Extended from four roles to fourteen. |
| `OL-4.1-06` | **GAP** | — | No source for the Axon/Fusus material: the Guardian 2026-08-20 vendor-replacement reporting, `axoncommunityconnect.com`, and the Reddit enumeration thread are all absent. G C-06 corrects the Reddit figure without citing it — an assertion with no retrievable locator, contrary to SIG-EPIS-002. |
| `OL-4.2-01` | **PARTIAL** | §5.1, §13.1 | Vendor-network sharing, private ALPR data, retention, cross-agency lookup and bulk location search are all modelled. **'EFF Data Driven is a priority ingestion source' is asserted in §6 and then never operationalized.** |
| `OL-4.3-01` | COVERED | §12.4, §11.10 system_scope, SIG-ONTO-018 | Vendor default never substitutes for deployment evidence. |
| `OL-4.4-01` | COVERED | §11.6, SIG-ONTO-024 | Capability is first-class; export/disclosure class added. |
| `OL-4.5-01` | **PARTIAL** | G C-08, §43.3 | Count corrected to 22,471 and a leak-provenance veto added. **The WIRED source is never named or linked** (OL-21-32). |
| `OL-4.5-02` | COVERED | §19.2, SIG-ONTO-027 | No camera abstraction forced; service-area polygons. |
| `OL-4.6-01` | COVERED | SIG-ONTO-026, §19.2 | Deployment with no PhysicalAsset row. |
| `OL-4.7-01` | **GAP** | — | None of the four facial-recognition datasets is named: EFF *Who Has Your Face?*, the BuzzFeed Clearview AI usage table, Atlas FR deployments, country-level FR datasets. Phase 17 lists facial recognition second in priority with no source to populate it from. |
| `OL-4.7-02` | COVERED | SIG-ONTO-031 | Reference databases as DataSystems. |
| `OL-4.8-01` | COVERED | §13.1 device-forensics, §11.6 extract.* | Investigative extraction capabilities modelled. |
| `OL-4.9-01` | COVERED | Appendix D.5 pathway 3 | Extended to six layers (aggregator ≠ productizer). |
| `OL-4.9-02` | COVERED | §1.4, §12.3, SIG-ONTO-026 | Access relationships without hardware. |
| `OL-4.10-01` | **PARTIAL** | §12.3, §13.1, §12.9 | Eight of nine RTCC inputs covered. **Body cameras missing.** |
| `OL-4.10-02` | COVERED | §12.3, §12.9 | Thirteen typed integration edges replace integrates_with. |
| `OL-5-01` | COVERED | §5.1, §5.3 | US-first rationale; twelve wedge conditions. |
| `OL-5-02` | COVERED | SIG-CHART-029 | International from the beginning. |
| `OL-5.1-01` | COVERED | SIG-CHART-030 |  |
| `OL-5.2-01` | **PARTIAL** | §6 row 17, Phase 18 | Named as an international model. **None of its documented technology coverage (intelligent video, FR experiments, drones, thermal cameras, acoustic sensors, 'safe city') is restated**, and no URL is given. |
| `OL-5.2-02` | **GAP** | — | The fact that Technopolice communities *explicitly discussed using OSM rather than isolated databases* is absent. This is the outline's strongest evidence that the OSM-first posture generalizes internationally, and Phase 18's design rests on it. |
| `OL-5.2-03` | **GAP** | — | The `sous-surveillance.net` import of ~12,000 French cameras into OSM is absent. It is the outline's only worked precedent for the local-activist-DB → common-substrate migration path, which is precisely what Phase 18 must execute. |
| `OL-5.3-01` | **GAP** | — | AI Global Surveillance Index, Facial Recognition World Map, and Mapping China's Tech Giants are all absent. Phase 18's acceptance criteria reference no international dataset at all. |
| `OL-5.3-02` | COVERED | SIG-ONTO-021 | Record the coarsest level the evidence supports. |
| `OL-6-00` | COVERED | §1.3 SIG-CHART-001 | General reconciliation layer. |
| `OL-6.1-01` | COVERED | §14.1 | LAPD example preserved verbatim. |
| `OL-6.1-02` | COVERED | §14.1, §14.2 | Per-class canonical identifier table. |
| `OL-6.1-03` | COVERED | §14, P6, Phase 3/5 ordering | ER gates block analytics surfaces. |
| `OL-6.2-01` | COVERED | §8.5 SIG-ONTO-008 | Target statement reproduced verbatim in substance. |
| `OL-6.2-02` | COVERED | SIG-ONTO-008 | Reconciliation as a first-class addressable object. |
| `OL-6.3-01` | COVERED | §9, §29.4 | Five temporal dimensions; lifecycle reconciliation. |
| `OL-6.3-02` | COVERED | §9.2, §9.3, §12.1 | valid_*_kind corrects the NULL ambiguity. |
| `OL-6.4-01` | COVERED | §10.1, §16.2 | Provenance attaches at claim level, not entity level. |
| `OL-6.5-01` | COVERED | §31, §28.5, SIG-STORE-015 | UNRESOLVED publishable with all dissent attached. |
| `OL-6.5-02` | COVERED | SIG-RECON-057 | Every detector emits a task with a closing condition. |
| `OL-6.6-01` | COVERED | §30.2, §12.3 | Access-path closure across vendors. |
| `OL-6.7-01` | COVERED | §13.4 | All fourteen states retained across four tracks; ten added. |
| `OL-6.7-02` | COVERED | SIG-ONTO-062, SIG-RECON-041 | replaced is an edge, not a state. |
| `OL-7-01` | COVERED | §1.1 |  |
| `OL-7-02` | COVERED | §43.1 SIG-PUB-001 |  |
| `OL-7.1-01` | COVERED | §4.1 G1 | Bound to Phase 3 and a metric. |
| `OL-7.1-02` | COVERED | §4.1 G2 |  |
| `OL-7.1-03` | COVERED | §4.1 G3, §32.3 | Target 100% resolvable evidence. |
| `OL-7.1-04` | COVERED | §4.1 G4, §9 |  |
| `OL-7.1-05` | COVERED | §4.1 G5, §12 |  |
| `OL-7.1-06` | COVERED | §4.1 G6, §32.2 |  |
| `OL-7.1-07` | COVERED | §4.1 G7, §33 |  |
| `OL-7.1-08` | COVERED | §4.1 G8, §37–§39 | Seven audiences named. |
| `OL-7.2-01` | COVERED | N1, SIG-STORE-026 | No plate-capable column; schema test. |
| `OL-7.2-02` | COVERED | N2, §18.1, §24.2 |  |
| `OL-7.2-03` | COVERED | N3, §43.4 | Five-prong test, two concurring reviewers. |
| `OL-7.2-04` | **PARTIAL** | N4 → §30.6 | The prohibition is real and enforced at **§30.3**. **N4's enforcement pointer §30.6 does not exist.** |
| `OL-7.2-05` | **PARTIAL** | N5 → §46.5, §34.6 | Enforced at **§46.3** and SIG-CONTRIB-007. **Both cited sections are wrong: §46.5 is 'Continuity and succession' and §34.6 does not exist.** |
| `OL-7.2-06` | **PARTIAL** | N6 → §43.6 | Enforced at **§43.5** (SIG-PUB-013). **§43.6 is 'Aggregate disclosure'** — the wrong section, and this mis-citation is repeated five times (§8.3, §11.9 ×2, §23.9, §25.2). |
| `OL-7.2-07` | COVERED | N7, §35.2, SIG-CONTRIB-014 |  |
| `OL-7.2-08` | COVERED | N8, §6, §35.3 |  |
| `OL-7.2-09` | COVERED | N9, §11.16 |  |
| `OL-7.2-10` | COVERED | N10, SIG-CHART-019, §32.2 |  |
| `OL-8.1-01` | COVERED | §11.2 organization_type | All fourteen example classes present, namespaced. |
| `OL-8.1-02` | COVERED | §11.2 | All listed fields present as predicates. |
| `OL-8.2-01` | COVERED | SIG-ONTO-012 | Corrected: vendor is a role, not a subtype. |
| `OL-8.2-02` | COVERED | §14.5 acquired, §11.4 | Axon→Fusus expressible with time bounds. |
| `OL-8.2-03` | COVERED | §11.4 product_name/vendor time-bounded |  |
| `OL-8.3-01` | **PARTIAL** | §11.4 | Seven of eight product examples present. **Cellebrite UFED is never named** anywhere in the spec. |
| `OL-8.3-02` | COVERED | SIG-ONTO-017 |  |
| `OL-8.4-01` | COVERED | §11.5, §11.6, §13.1 | All twelve examples present in the 13-domain taxonomy. |
| `OL-8.4-02` | COVERED | P7, §11.5 |  |
| `OL-8.5-01` | COVERED | §11.7 |  |
| `OL-8.5-02` | COVERED | §11.7 | All fields retained; counts split per §29.1. |
| `OL-8.6-01` | COVERED | §11.8, SIG-ONTO-027 | Including RTCC facility and camera trailer. |
| `OL-8.6-02` | COVERED | §11.8 | All fields present; owner/operator expanded to 14 roles. |
| `OL-8.6-03` | COVERED | SIG-GEO-004 | Coordinates optional; four cases specified. |
| `OL-8.7-01` | COVERED | §11.10 |  |
| `OL-8.7-02` | COVERED | §11.10 | Plus system_scope and holds_data_collected_by. |
| `OL-8.8-01` | COVERED | §12.5 |  |
| `OL-8.8-02` | COVERED | §12.5, §12.1 | All attributes present plus asserted_by. |
| `OL-8.8-03` | COVERED | SIG-ONTO-049, §12.2 | Direction required; three edge types never merged. |
| `OL-8.9-01` | COVERED | §12.3 | Thirteen typed edges; integrates_with prohibited as stored. |
| `OL-8.10-01` | COVERED | §11.11 |  |
| `OL-8.10-02` | COVERED | §11.11 | Plus acquisition_channel and parent_cooperative_contract. |
| `OL-8.10-03` | COVERED | §23.6, §13.4 track 1, amends_contract |  |
| `OL-8.11-01` | COVERED | §11.13 policy_type | All seven examples present. |
| `OL-8.11-02` | COVERED | §11.13 applies_to polymorphic |  |
| `OL-8.12-01` | COVERED | §11.15 | Promoted to first-class time-versioned entity. |
| `OL-8.12-02` | COVERED | SIG-ONTO-043, §29.6, SIG-UI-045 | Canonical divergence case rendered without collapse. |
| `OL-8.13-01` | COVERED | §11.16 |  |
| `OL-8.13-02` | COVERED | §11.16 | All SearchAggregate fields plus coverage_period. |
| `OL-8.13-03` | COVERED | §18.1, N9 |  |
| `OL-8.14-01` | COVERED | §11.17 event_type | All ten examples present. |
| `OL-8.14-02` | COVERED | §11.17 epistemic_status | Required and rendered everywhere. |
| `OL-8.15-01` | COVERED | §10.2 | Split four ways: Source/Artifact/Capture/Extraction. |
| `OL-8.15-02` | COVERED | §10.3.2, §10.3.3 | All eleven fields present. |
| `OL-8.15-03` | COVERED | §10.3.2 artifact_type | All eight examples covered. |
| `OL-8.16-01` | COVERED | §10.3.5 |  |
| `OL-8.16-02` | **PARTIAL** | §10.3.5, §10.3.6, §16.2 | Field spec is a superset. **The physical DDL in §16.2 drops `unit` and `object_type`** from the §10.3.5 spec, and `asserted_by` is `text` rather than a `Person` reference despite §11.3 existing. |
| `OL-8.16-03` | COVERED | Appendix D.4 | Worked provenance chain for exactly this shape. |
| `OL-9-01` | COVERED | §10 | Six distinctions as concrete objects. |
| `OL-9.1-01` | COVERED | §10.4 R1/R2 | Tier A split by directness; mapping table retained. |
| `OL-9.1-02` | COVERED | §10.4 R2 |  |
| `OL-9.1-03` | **PARTIAL** | §10.4 R3 | Tier C preserved. **Upturn is dropped from the R3 example list** even though the outline names it explicitly; Eyes on Flock was substituted. |
| `OL-9.1-04` | COVERED | §10.4 R4 |  |
| `OL-9.1-05` | COVERED | §10.4 R5 |  |
| `OL-9.1-06` | COVERED | §10.4 R6, SIG-LLM-005 |  |
| `OL-9.1-07` | COVERED | SIG-EPIS-015, §10.5 | Novelty ≠ unreliability; D6 is admissibility, not rank. |
| `OL-9.2-01` | COVERED | §9.1, §9.2 SIG-TIME-002/003 | Portal example reproduced; T1 never inferred at ingest. |
| `OL-9.3-01` | COVERED | SIG-EPIS-022 | Numeric confidence prohibited unless calibrated. |
| `OL-9.3-02` | COVERED | §10.7 | Three orthogonal fields; all six labels recoverable. |
| `OL-9.4-01` | COVERED | §9.5, §32.1 | Four epistemic states; CoverageRecord. |
| `OL-9.4-02` | COVERED | §32.1, SIG-UI-012 | sources_searched[] required. |
| `OL-9.4-03` | COVERED | SIG-TIME-012, SIG-API-003, SIG-UI-007 |  |
| `OL-10.1A-01` | COVERED | Phase 3, §14 | Identity registry before anything is counted. |
| `OL-10.1A-02` | COVERED | §14.2 | All seven identity aids present. |
| `OL-10.1B-01` | COVERED | §23.2, Phase 4 | ID, version, tags, coordinates, attribution preserved. |
| `OL-10.1B-02` | COVERED | N7, SIG-CONTRIB-014 |  |
| `OL-10.1C-01` | COVERED | §23.3, Phase 4 |  |
| `OL-10.1C-02` | COVERED | §20.3 SIG-STORE-039 | Explicit Atlas crosswalk with lossy flags. |
| `OL-10.1D-01` | COVERED | §22.5, Phase 11 gate |  |
| `OL-10.1D-02` | **PARTIAL** | §23.4 | Nine of ten capture targets specified. **Hotlist *hits* and 'vehicles detected' missing** (see OL-2B-FP-02). |
| `OL-10.1E-01` | COVERED | §18.1, §23.7 | No plate/search rows ingested. |
| `OL-10.1E-02` | COVERED | §23.7, §11.16 | Structural aggregates only; custody stays upstream. |
| `OL-10.1F-01` | COVERED | §23.5, §23.6, Phase 7 |  |
| `OL-10.1G-01` | COVERED | §23.8, Phase 13 |  |
| `OL-11.1-01` | COVERED | §29.1 | All six input classes as distinct predicates. |
| `OL-11.1-02` | COVERED | §29.1 SIG-RECON-029 | Every count predicate with its own resolution + deltas. |
| `OL-11.1-03` | COVERED | SIG-RECON-028/029, SIG-STORE-015 | PREDICATE_CONFLATION; no single true count. |
| `OL-11.2-01` | COVERED | §29.2 | Candidate generation spec + probable label at L4. |
| `OL-11.2-02` | COVERED | §29.2 SIG-RECON-033, §33.2 #5 | Human/documentary promotion only. |
| `OL-11.3-01` | COVERED | §29.3, §12.2 | All five source types kept distinct. |
| `OL-11.3-02` | COVERED | SIG-ONTO-042, SIG-RECON-034 | No operation merges the three edge types. |
| `OL-11.4-01` | COVERED | §29.4, §13.4 | Four-track timeline; unordered-within-window for fuzzy dates. |
| `OL-12-00` | COVERED | Part VI preamble, §33 |  |
| `OL-12-01` | COVERED | §33.2 #1 |  |
| `OL-12-02` | COVERED | §33.2 #2 |  |
| `OL-12-03` | COVERED | §33.2 #3, §29.5 |  |
| `OL-12-04` | COVERED | §33.2 #4, §28.3 |  |
| `OL-12-05` | COVERED | §33.2 #5, SIG-ONTO-028 |  |
| `OL-12-06` | COVERED | §33.2 #6, §14.4 |  |
| `OL-12-07` | COVERED | §33.2 #7, SIG-RECON-041 |  |
| `OL-12-08` | COVERED | Part VI, §7 leverage metrics |  |
| `OL-13-00` | COVERED | SIG-CHART-024, §44 |  |
| `OL-13.1-01` | COVERED | SIG-CHART-024, §43.1 |  |
| `OL-13.1-02` | COVERED | §18.1, N9 |  |
| `OL-13.2-01` | COVERED | §43.2 | All six categories excluded; addresses made categorical. |
| `OL-13.2-02` | COVERED | §43.4 | Five prongs + two concurring reviewers. |
| `OL-13.3-01` | COVERED | §43.3, §19.4 | Five-class matrix covering all five listed cases. |
| `OL-13.4-01` | COVERED | §17.5, SIG-EVID-010/011 | Sealed tier + public metadata + redacted derivative. |
| `OL-13.5-01` | COVERED | SIG-CHART-023 |  |
| `OL-13.5-02` | COVERED | SIG-CHART-023, SIG-GOV-018 |  |
| `OL-14.1-01` | COVERED | §42.3 |  |
| `OL-14.1-02` | COVERED | §42.3 point 4 | Strategy A analysed and rejected with the guideline text. |
| `OL-14.1-03` | COVERED | §42.3 SIG-LIC-006 | Strategy B adopted. |
| `OL-14.1-04` | COVERED | §42.3 point 5 | Strategy C analysed and rejected. |
| `OL-14.1-05` | COVERED | SIG-LIC-009 | Four residuals referred to counsel and in the risk register. |
| `OL-14.2-01` | COVERED | §42.1 SIG-LIC-001 | All six fields; redistributable separately reviewed. |
| `OL-14.2-02` | COVERED | SIG-LIC-004 | UNDETERMINED fails the export gate closed. |
| `OL-14.3-01` | COVERED | SIG-LIC-012 |  |
| `OL-14.3-02` | COVERED | SIG-LIC-012, §38 | All seven deliverables required for a release. |
| `OL-15.1-01` | COVERED | §39.2 |  |
| `OL-15.1-02` | COVERED | §39.2, Appendix D | All fifteen output elements present. |
| `OL-15.1-03` | COVERED | SIG-UI-002/010 | Dossier is the design center and primary artifact. |
| `OL-15.2-01` | COVERED | §39.3 | All seven layers plus a bound coverage underlay. |
| `OL-15.3-01` | COVERED | §39.4, §30.2 | Ego network; all four questions answerable. |
| `OL-15.4-01` | COVERED | §39.5 | Plus iCal/RSS subscriptions. |
| `OL-15.5-01` | COVERED | §39.6 | All eight expansions present. |
| `OL-15.6-01` | COVERED | §39.7, §33 | Task cards with closing conditions. |
| `OL-15.7-01` | **PARTIAL** | §37, §38, §39.0 | API and exports fully specified. **The six named downstream applications (academic analysis, newsroom tools, local dashboards, route/privacy applications, policy trackers, visualizations) are not enumerated as export design targets**; §39.0 personas cover four of six. |
| `OL-16-01` | COVERED | SIG-CHART-025 |  |
| `OL-16-02` | COVERED | §5.1 | All twelve conditions enumerated. |
| `OL-16-03` | COVERED | SIG-CHART-026 | All six vendors. |
| `OL-16-04` | COVERED | SIG-CHART-027/028 | Generalization conformance suite from Phase 4. |
| `OL-17.0-01` | COVERED | Phase 0 deliverable 4 | Extended from seven to nineteen projects. |
| `OL-17.0-02` | COVERED | Phase 0 deliverables 2–4, §22.1 |  |
| `OL-17.1-01` | COVERED | Phases 1–4 |  |
| `OL-17.1-02` | COVERED | Phase 4 / Phase 6 acceptance |  |
| `OL-17.2-01` | COVERED | Phase 8, §29 |  |
| `OL-17.2-02` | COVERED | Phase 8 acceptance |  |
| `OL-17.3-01` | COVERED | Phase 12, §23.7 |  |
| `OL-17.3-02` | COVERED | Phase 12, §30.2 |  |
| `OL-17.4-01` | COVERED | Phase 13, §11.13/11.14/11.17 |  |
| `OL-17.4-02` | COVERED | Phase 13 acceptance |  |
| `OL-17.5-01` | COVERED | Phase 17 | Priority order preserved exactly. |
| `OL-17.6-01` | COVERED | Phase 18 | (§5.3 mis-cites this as Phase 14 — see DEFECTS.) |
| `OL-18-01` | COVERED | §6 row 1 |  |
| `OL-18-02` | COVERED | §6 row 2 |  |
| `OL-18-03` | COVERED | §6 row 3, §22.5 |  |
| `OL-18-04` | COVERED | §6 row 4, §23.7 |  |
| `OL-18-05` | COVERED | §6 row 5, §24.2 |  |
| `OL-18-06` | COVERED | §6 row 6, §23.3 |  |
| `OL-18-07` | **PARTIAL** | §6 row 7 | Row present with a binding constraint that points at the wrong section (§23.6). No connector, no registry row, no phase. |
| `OL-18-08` | COVERED | §6 row 8, §23.8 |  |
| `OL-18-09` | COVERED | §6 row 10, §11.19 |  |
| `OL-18-10` | COVERED | §6 row 12, §38 |  |
| `OL-18-11` | COVERED | §6 row 13, §23.9 |  |
| `OL-18-12` | COVERED | §6 row 14, §43.5 |  |
| `OL-18-13` | COVERED | §6 row 15, §33.7 | Corrected: SIG maintains its own registry. |
| `OL-18-14` | COVERED | §6 row 16, §33.5 |  |
| `OL-18-15` | COVERED | §6 row 17, Phase 18 |  |
| `OL-18-16` | COVERED | §6 row 18 |  |
| `OL-18-17` | COVERED | §6 row 19, §30 labelling |  |
| `OL-19.1` | COVERED | §3.2 P1 | No writable current-value columns; no_orphan_facts CI check. |
| `OL-19.2` | COVERED | §3.2 P2 | raw_value NOT NULL. |
| `OL-19.3` | COVERED | §3.2 P3 | UPDATE revoked at role level; §45.4 adds suppression. |
| `OL-19.4` | COVERED | §3.2 P4 | UNRESOLVED first-class. |
| `OL-19.5` | COVERED | §3.2 P5 | Contribution-back is a funded phase. |
| `OL-19.6` | COVERED | §3.2 P6 | Phase ordering + ER quality gates + UI disclosure. |
| `OL-19.7` | COVERED | §3.2 P7 | No vendor name in any schema identifier. |
| `OL-19.8` | COVERED | §3.2 P8, §12.4 | Extended from six roles to fourteen. |
| `OL-19.9` | COVERED | §3.2 P9, §12.2 |  |
| `OL-19.10` | COVERED | §3.2 P10, §29.6 |  |
| `OL-19.11` | COVERED | §3.2 P11, §29.1 |  |
| `OL-19.12` | COVERED | §3.2 P12, §32.4, SIG-TIME-005 |  |
| `OL-Q01` | COVERED | Appendix B Q1 | BLOCKED, honestly; top Stage-0 item; Phase 11 gated. |
| `OL-Q02` | COVERED | Appendix B Q2 | BLOCKED; Wayback exclusion raises the stakes. |
| `OL-Q03` | COVERED | Appendix B Q3 | BLOCKED → UNDETERMINED → export gate closed. |
| `OL-Q04` | COVERED | Appendix B Q4 | Record types captured verbatim; licence/cadence open. |
| `OL-Q05` | COVERED | Appendix B Q5 | Artifacts enumerated; GitLab correction. |
| `OL-Q06` | COVERED | Appendix B Q6 | Bulk CSV; EFF device-layer delegation recorded. |
| `OL-Q07` | COVERED | Appendix B Q7 | api_v2, 401, JWT, rate limit — outline corrected. |
| `OL-Q08` | COVERED | Appendix B Q8 | Called successfully. |
| `OL-Q09` | COVERED | Appendix B Q9, §14.2 | ORI9 + LEAIC. |
| `OL-Q10` | COVERED | Appendix B Q10, §14.2/14.4 | Per-class identifiers + two ORI traps. |
| `OL-Q11` | COVERED | Appendix B Q11 | GEOID/GNIS/GeoNames; fixed-width + level. |
| `OL-Q12` | COVERED | Appendix B Q12, §14.4 | Surrogate + identity_basis + aggregate publication. |
| `OL-Q13` | COVERED | Appendix B Q13, §42.3 | Guideline conflict analysed; conservative reading. |
| `OL-Q14` | COVERED | Appendix B Q14 | Answered 'not by separation alone'; Strategy B. |
| `OL-Q15` | COVERED | Appendix B Q15 | Atlas resolved; four remain Stage-0 blockers. |
| `OL-Q16` | COVERED | Appendix B Q16, §8.4 | custody_posture enforced before fetch. |
| `OL-Q17` | **PARTIAL** | Appendix B Q17 | 'BLOCKED by F2.1 — cadence is moot.' **This dodges half the question**: the fallback channels (records requests, contributor captures, partner feeds) also need a justified cadence, and none is given. |
| `OL-Q18` | COVERED | Appendix B Q18, §17.6 |  |
| `OL-Q19` | COVERED | Appendix B Q19 | Design-only; flagged untested, in risk register. |
| `OL-Q20` | COVERED | Appendix B Q20, §15.1 | Hybrid with relational core; scored. |
| `OL-Q21` | COVERED | Appendix B Q21, §15.3 |  |
| `OL-Q22` | COVERED | Appendix B Q22, §18 |  |
| `OL-Q23` | COVERED | Appendix B Q23, §21.3 |  |
| `OL-Q24` | COVERED | Appendix B Q24, §26 | Reframed as four legal tracks. |
| `OL-Q25` | COVERED | Appendix B Q25, §17.2/17.3/17.4 |  |
| `OL-Q26` | COVERED | Appendix B Q26, §24 | Seven-layer ladder. |
| `OL-Q27` | COVERED | Appendix B Q27, §14.6 | Tiers 0–3. |
| `OL-Q28` | COVERED | Appendix B Q28, §14.6 | Tiers 4–5 to review; LLMs may not write. |
| `OL-Q29` | COVERED | Appendix B Q29, §14.5 | Rename ≠ succession; five fixtures. |
| `OL-Q30` | COVERED | Appendix B Q30, §43 |  |
| `OL-Q31` | COVERED | Appendix B Q31, SIG-EVID-010 |  |
| `OL-Q32` | COVERED | Appendix B Q32, §45 | Includes suppression as a distinct primitive. |
| `OL-Q33` | COVERED | Appendix B Q33, §35.2 | No automated writes; ADR gate; R-14. |
| `OL-Q34` | COVERED | Appendix B Q34 | PARTIAL answer, honestly labelled; Stage-0 item. |
| `OL-Q35` | COVERED | Appendix B Q35 | PARTIAL answer; task→RecordsRequest model specified regardless. |
| `OL-Q36` | COVERED | Appendix B Q36, §33.5 |  |
| `OL-Q37` | COVERED | Appendix B Q37, §14.8 |  |
| `OL-21-01` | **PARTIAL** | §22.2 / §6 (name only) | OSM surveillance tagging is used throughout and the tag is named once (§19.1); **the wiki URL is absent.** |
| `OL-21-02` | **GAP** | — | `https://www.openstreetmap.org/copyright` absent. |
| `OL-21-03` | **PARTIAL** | §22.2 / §6 (name only) | DeFlock named 22×; both hosts discussed in G C-01; **no URL.** |
| `OL-21-04` | **GAP** | — | `https://github.com/flockhopper3/deflock-data` absent; the project is never named. |
| `OL-21-05` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§22.2; **no URL.** |
| `OL-21-06` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§22.2; **no URL.** |
| `OL-21-07` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§22.2; **no URL.** |
| `OL-21-08` | **PARTIAL** | §22.2 / §6 (name only) | Named 14×, Phase-0 blocker; **no URL.** |
| `OL-21-09` | **GAP** | — | The Eyes on Flock Reddit project description is absent. Given Q1 is BLOCKED because the site is an opaque SPA, this is the one public description of what EoF actually holds. |
| `OL-21-10` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§23.7; **no URL.** |
| `OL-21-11` | **GAP** | — | `https://haveibeenflocked.com/about` absent. |
| `OL-21-12` | **PARTIAL** | §22.2 / §6 (name only) | Its *content* is captured verbatim (Appendix B Q4, F2.3); **the URL itself is absent.** |
| `OL-21-13` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§22.2 with a scope correction; **no URL.** |
| `OL-21-14` | **GAP** | — | `https://alprwatch.org/news/2025-07-28_flock_foia/` absent, although §21.1's eight-stage pipeline is derived from it. |
| `OL-21-15` | **PARTIAL** | §22.2 / §6 (name only) | Host named once in §22.2; **not given as a registry URL.** |
| `OL-21-16` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§23.3 with licence resolved; **no URL.** |
| `OL-21-17` | **GAP** | — | `https://www.atlasofsurveillance.org/methodology` absent. |
| `OL-21-18` | **GAP** | — | `https://www.atlasofsurveillance.org/data-library` absent from the spec (it appears only as prose in the §0.5 research-cache table's R3 row). |
| `OL-21-19` | **PARTIAL** | §22.2 / §6 (name only) | Named in §13.1/§20.3 as a crosswalk target; **no URL.** |
| `OL-21-20` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§23.8; **no URL.** |
| `OL-21-21` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§23.8; **no URL.** |
| `OL-21-22` | **GAP** | — | `https://www.aclu.org/get-the-flock-out-toolkit` absent; so is the project. |
| `OL-21-23` | **PARTIAL** | §22.2 / §6 (name only) | Named 15×, api_v2 corrected; **no URL.** |
| `OL-21-24` | **PARTIAL** | §22.2 / §6 (name only) | Named 9×, API verified; **no URL.** |
| `OL-21-25` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§23.9; **no repository URL.** |
| `OL-21-26` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§23.9; **no repository URL.** |
| `OL-21-27` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/§33.7 with C-03 correction; **no URL.** |
| `OL-21-28` | **PARTIAL** | §22.2 / §6 (name only) | Named in §6/Phase 18; **no URL.** |
| `OL-21-29` | **GAP** | — | `https://forum.technopolice.fr/topic/405/...` absent — the discussion that evidences OL-5.2-02. |
| `OL-21-30` | **GAP** | — | The ten historical/specialist dataset classes to inspect through the EFF Data Library are absent as a group (see OL-2D-AT-05). |
| `OL-21-31` | **GAP** | — | The ACLU Stingray tracking-devices page is absent. §13.1 has `comms-intercept` but no source to populate it. |
| `OL-21-32` | **GAP** | — | The WIRED ShotSpotter sensor-location leak is never cited. G C-08 corrects its figure to 22,471 without naming or linking the source. |
| `OL-21-33` | **PARTIAL** | §22.2 / §6 (name only) | Verified in §22.2 (321 communities); **no URL.** |
| `OL-21-34` | **GAP** | — | The Guardian 2026-08-20 article is absent, despite the spec being dated 2026-08-20 and asserting vendor replacement as a current dynamic (OL-22.5-01). |
| `OL-21-35` | **PARTIAL** | §22.2 / §6 (name only) | 'EFF Data Driven' named in §6/§8.3; **the 2018 release is not cited and has no URL.** |
| `OL-21-36` | **GAP** | — | Monahan, *Grounding the Flock* (2026) absent. |
| `OL-21-37` | **GAP** | — | Both r/FlockSurveillance threads (the California sharing visualization; the ALPR abuse-documentation announcement) are absent. |
| `OL-22.1-01` | COVERED | §3.7 SIG-CHART-020 | Full fact→generator table reproduced. |
| `OL-22.1-02` | COVERED | §3.7, Part V |  |
| `OL-22.2-01` | COVERED | §3.6 SIG-CHART-018 | Authority claim stated verbatim as a bounded claim. |
| `OL-22.3-01` | COVERED | §5.2 rationale | capability→deployment→assets/data/access. |
| `OL-22.4-01` | COVERED | §30.2, §12.9, §39.4 | All seven central questions answerable. |
| `OL-22.4-02` | COVERED | §39.4, §30.2, P6 | Central, but gated on ER quality. |
| `OL-22.5-01` | COVERED | §13.4, §28.3, Appendix G | Current dynamics modelled as state + edge changes. |
| `OL-22.5-02` | COVERED | SIG-RECON-041/042 | Canceled+installed stated plainly in UI and API. |
| `OL-22.6-01` | COVERED | §7, §32.6 | All six leverage measures instrumented. |
| `OL-22.6-02` | COVERED | SIG-CHART-035, §46.5 |  |
| `OL-23-01` | COVERED | §1.1 | Preserved verbatim. |
| `OL-24-01` | COVERED | Appendix G, §22.2 | Ecosystem re-verified; 14 factual corrections. |
| `OL-24-02` | COVERED | §22.2 access matrix | VERIFIED = a request was made and observed. |
| `OL-24-03` | COVERED | §22.2, SIG-INGEST-024 | Access verified, not assumed. |
| `OL-24-04` | COVERED | §14, Phase 3/5 before Phase 12 | ER precedes analytics by phase order. |
| `OL-24-05` | COVERED | Phases 1–2 before Phase 4 |  |
| `OL-24-06` | COVERED | §42.3, R-01, Phase 0/4 |  |
| `OL-24-07` | COVERED | SIG-CHART-014, §8.4 custody postures |  |
| `OL-24-08` | COVERED | SIG-STORE-043, §14.2 |  |
| `OL-24-09` | COVERED | §8.1 six layers | L0/L1/L3/L4 physically separated. |
| `OL-24-10` | COVERED | §18.1, N2, OL-A.8 |  |
| `OL-24-11` | COVERED | §31, SIG-EPIS-011, SIG-UI-009 |  |
| `OL-24-12` | COVERED | §33.1/§33.2, §39.7 |  |
| `OL-24-13` | COVERED | SIG-CHART-025/027 |  |
| `OL-24-14` | COVERED | §12.4, §12.3 enrolls_asset_into, §14.4 |  |
| `OL-24-15` | COVERED | SIG-ONTO-026/031, §19.2 |  |
| `OL-24-16` | COVERED | SIG-ONTO-062, SIG-RECON-041 |  |
| `OL-24-17` | COVERED | §37, §38, SIG-LIC-004 |  |
| `OL-24-18` | COVERED | §10.1, SIG-PARSE-003, Appendix D.4 |  |
| `OL-24-19` | COVERED | §3.1 | Preserved verbatim; §3.3 binds each clause. |
| `OL-24-20` | COVERED | §3.1, §3.3 | Preserved verbatim with enforcement points. |
| `OL-A.1` | COVERED | §22.5, R-02, Phase 0 gate |  |
| `OL-A.2` | COVERED | §33.5, §33.7, §34 |  |
| `OL-A.3` | COVERED | §5.2 rationale, §13.4 |  |
| `OL-A.4` | COVERED | §22.2, §12.4, §14.4 |  |
| `OL-A.5` | COVERED | §1.4, §12.5 |  |
| `OL-A.6` | COVERED | §13.4 |  |
| `OL-A.7` | COVERED | §10, §16.2 |  |
| `OL-A.8` | COVERED | §18.1, §8.4 DERIVE posture |  |
| `OL-B-01` | COVERED | Appendix D, §11.1 |  |
| `OL-B-02` | COVERED | Appendix D, §11.2 |  |
| `OL-B-03` | COVERED | Appendix D.2 | Split into three predicates with separate resolutions. |
| `OL-B-04` | COVERED | §11.11, §39.5, SIG-UI-015 |  |
| `OL-B-05` | COVERED | Appendix D.3, §29.5 | Split into three retention predicates. |
| `OL-B-06` | COVERED | Appendix D.3, §12.2 | Split configured vs observed. |
| `OL-B-07` | COVERED | Appendix D.3, §11.16, SIG-RECON-011 | Windowed predicate with explicit bounds. |
| `OL-B-08` | COVERED | Appendix D.3, §29.2 |  |
| `OL-B-09` | COVERED | Appendix D.3, §9.5, SIG-UI-015 | 'unknown' rendered, not omitted. |
| `OL-B-10` | COVERED | §11.17, SIG-UI-010 |  |
| `OL-B-11` | COVERED | Appendix D.2, §33.2 | Detectors 1,2,3,4,27 cover the five listed gaps. |
| `OL-B-12` | COVERED | §1.3, §39.2, SIG-CHART-002 |  |
| `OL-C-01` | COVERED | Appendix D.5 pathway 1 | enrolls_asset_into sharpens 'streams_via'. |
| `OL-C-02` | COVERED | Appendix D.5 pathway 2 | Directional, scoped, dated, separately evidenced. |
| `OL-C-03` | COVERED | Appendix D.5 pathway 3 | Six layers, not five. |
| `OL-C-04` | COVERED | Appendix D.5, §30.2 |  |
---

## 3. CONTRADICTED — the spec contradicts its own load-bearing claims

These are not OL-row dispositions. They are places where the spec asserts something about itself
that is false, and where the falsehood matters.

### X-01 — Appendix A does not exist, and it is the superset proof (CRITICAL)

§0.1 line 28–31:

> **Superset.** Every obligation in the outline is discharged here. The proof is Appendix A, a
> traceability matrix over 480 extracted obligations … each mapped to the section that discharges
> it and labelled `VERBATIM-PRESERVED`, `DEEPENED`, `CORRECTED`, or `EXTENDED`.

The document contains Appendix B, Appendix D, and Appendix G. **There is no Appendix A**, no
traceability matrix, and no disposition labels. The one property the spec is being audited on is
asserted on the strength of an artifact that was never written. §51.3 (SIG-ENG-031) further requires
"the traceability matrix is updated" at every phase gate — a gate condition on a nonexistent object.

**Fix.** Either write Appendix A (it can be generated from §2 of this file), or delete the claim in
§0.1 and re-point SIG-ENG-031 at `docs/research/_meta/GAP_ANALYSIS.md`.

### X-02 — Appendix C does not exist, and it holds every domain entity's DDL (CRITICAL)

§16 line 2594–2595:

> The domain entity tables follow from Part II §11 and are consolidated in Appendix C.

§16 gives normative DDL for exactly five tables: `entity`, `claim`, `resolution`, `claim_evidence`,
`claim_qualifier`. **There is no DDL anywhere for `organization`, `jurisdiction`, `deployment`,
`physical_asset`, `candidate_asset`, `contract`, `funding_instrument`, `policy`,
`legal_instrument`, `configuration_state`, `usage_aggregate`, `accountability_event`,
`legal_proceeding`, `records_request`, `research_task`, `coverage_record`, `contradiction`,
`source`, `evidence_artifact`, `evidence_capture`, `extraction`, or `rights_record`** — several of
which are foreign-key targets of the DDL that *is* given (`claim.rights_id REFERENCES
rights_record`, `claim.extraction_id REFERENCES extraction`, `claim_evidence.capture_id REFERENCES
evidence_capture`). Phase 2's "Load: §9, §10, §16, §17, §20" therefore does not contain the schema
Phase 2 must build.

**Fix.** Write Appendix C, or state explicitly that domain tables are generated from the LinkML
source (§20.1) and that §11's predicate surfaces are the normative input, in which case §16 must say
so and Phase 1/2 must cite §20.1.

### X-03 — The canonical schema contradicts the epistemic model it implements (HIGH)

§10.4 SIG-EPIS-013/014 normatively **replaces** the outline's Tier A–F with a six-value source
reliability scale `R1…R6`, and §13.3 registers the vocabulary as `source_reliability (R) = R1…R6`.
Appendix G M-06 restates this as a headline correction. But §16.2's claim DDL declares:

```sql
  source_tier       char(1) NOT NULL,       -- A..F: how good is the SOURCE generally
  support_strength  text NOT NULL,          -- how directly THIS artifact supports THIS claim
```

`char(1)` cannot hold `R1`, and the comment reinstates the A–F scale the spec just retired. The
§10.3.5 field spec calls the same field `evidence_tier` and points at §10.4. Three names, two
incompatible domains, for one column. Separately, **no column stores `D`, `I`, or the composed
`W`** — §10.6 says `C` is computed at query time, but `D` (a (genre × predicate) matrix lookup) and
`I` (assigned mechanically at capture) are per-claim facts with nowhere to live.

**Fix.** Rename to `source_reliability text NOT NULL REFERENCES vocab_source_reliability(r)`; add
`claim_directness text` and `artifact_integrity text`; make `§10.3.5` use the same field name.

### X-04 — "Every requirement is testable" is contradicted by at least six unfalsifiable MUSTs (MEDIUM)

§0.1 property 3: *"Every requirement is testable. Requirements that cannot be expressed as a test
are demoted to design rationale and marked as such."* The following are MUSTs, unmarked, with no
possible test:

| Id | Text | Why untestable |
|---|---|---|
| SIG-UI-042 | "MUST pass the hostile-reader test: a police chief or vendor counsel reading their own dossier should find it accurate, neutral, and hard to attack" | No adjudicator, no threshold, no procedure |
| SIG-RECON-023 | "The rationale MUST be quotable verbatim by a journalist without additional interpretation" | No definition of "quotable safely" |
| SIG-CONTRIB-003 | "MUST be able to make a useful contribution in under ten minutes without understanding the ontology" | No study protocol, no n, no success criterion |
| SIG-SEC-001 | "MUST be built on the assumption that it is adversarial by nature" | An attitude, not a behaviour |
| SIG-ENG-030 | "Phases MUST be ordered by risk retirement, not by visible value" | Not checkable against an artifact |
| Phase 6 gate | "A slice that surfaces no design problems is evidence the slice was too easy, and MUST be redone on a harder jurisdiction" | Unfalsifiable by construction — success is defined as failure |

**Fix.** Demote each to *Rationale* per §0.1, or give each a concrete test (e.g. SIG-UI-042 →
"editorial board review sign-off recorded per dossier template version"; SIG-CONTRIB-003 →
"moderated usability study, n≥5, median task time ≤10 min, published").

---

## 4. GAPS — all 27, with the text needed to close each

Ordered by severity.

### G-01 · `OL-21-01…37` (15 hard gaps + 22 partials) — the source registry has no URLs at all

**What is missing.** The spec contains one URL, a placeholder. OL-21's obligation is that every URL
appears in the spec's source registry. §22.2 is an *access matrix* keyed on prose names with
occasional API path fragments (`api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}`); it has no URL
column. §22.3 adds sources with no locators. Phase 0 deliverable 3 says "Source registry seeded with
every source in OL-21 plus §22.3" — but the implementing agent has no list of what OL-21 contains,
and SIG-ENG-001 forbids it reading outside the cited sections.

Entirely absent (15): `OL-21-02` OSM copyright · `OL-21-04` `deflock-data` · `OL-21-09` EoF Reddit
description · `OL-21-11` HIBF `/about` · `OL-21-14` ALPR Watch FOIA methodology · `OL-21-17` Atlas
methodology · `OL-21-18` Atlas Data Library · `OL-21-22` ACLU Get the Flock Out · `OL-21-29`
Technopolice forum thread · `OL-21-30` the ten Data Library specialist datasets · `OL-21-31` ACLU
Stingray page · `OL-21-32` WIRED ShotSpotter leak · `OL-21-34` Guardian 2026-08-20 · `OL-21-36`
Monahan 2026 · `OL-21-37` r/FlockSurveillance threads.

**Text needed.** Add **§22.6 — The seeded source registry** as a table with columns
`source_id | name | canonical_url | source_kind | R | custody_posture | rights (SPDX) | redistributable | compact_status | access status | OL-21 ref`, containing one row per OL-21 entry plus every §22.3 addition, with the literal URL. Add to Phase 0:

> - [ ] Every row of §22.6 exists in `sources.yaml` with a non-null `canonical_url`; a test asserts
>       the row count equals the §22.6 row count and that no `canonical_url` is null.

### G-02 · `OL-2E-AC-01` — the ACLU *Get the Flock Out* toolkit is absent from the entire spec

**What is missing.** Not in the §6 federation compact (19 rows), not in §22.2, not in §22.3, no URL,
no role. The outline names it as the demonstration case for SIG's most important downstream user —
and §39.2's dossier plus SIG-UI-002 ("the local advocate is the design center") are built for exactly
that user. The spec designs *for* the ACLU's audience while erasing the ACLU's artifact.

**Text needed.** A §6 compact row:

> | ACLU (Get the Flock Out toolkit) | National advocacy toolkit and local organizing guidance | Downstream consumer; align the dossier's content contract to what the toolkit asks organizers to gather | Do not duplicate the toolkit; link to it from every dossier (§39.2) |

plus a §22.6 registry row with `https://www.aclu.org/get-the-flock-out-toolkit`, and a sentence in
§39.2 binding the dossier's twelve sections to the toolkit's organizer checklist.

### G-03 · `OL-2D-AT-05` + `OL-21-30` — the entire EFF Data Library specialist-dataset roster is gone

**What is missing.** Fifteen named datasets: Atlas Border Communities; Who Has Your Face?;
public-safety drones; historical Ring/Neighbors partnerships; cell-site simulator datasets; AI Global
Surveillance Index; federally funded body cameras; wiretap reports; Aaron Swartz Day Police
Surveillance Project; California ALPR survey data; Vigilant Data Driven; Upturn mobile-forensics
research; Clearview AI usage data; electronic monitoring; state policy datasets. Only Ring/Neighbors
survives, and only as an example of vocabulary retirement (SIG-ONTO-059). **Phase 17 lists eight
technology families to populate and names no source for any of them.**

**Text needed.** A subsection **§23.10 `data_library` — EFF specialist datasets**, listing each
dataset with its technology-family target, its expected granularity (agency-level vs
device-level), and its ingestion phase; plus fifteen §22.6 registry rows. Add to Phase 17
acceptance: `- [ ] Each Stage-5 technology family is populated from at least one named registry source.`

### G-04 · `OL-2D-DD-01/02` + `OL-4.2-01` + `OL-18-07` — EFF Data Driven is named as a priority ingestion source and never implemented

**What is missing.** §6 row 7 says "Priority ingestion for the vendor-neutral model (§23.6)" —
**§23.6 is the procurement connector**. There is no `data_driven` connector, no §22.2 access row, no
rights record, no phase assignment. And none of the outline's Data Driven findings survive: billions
of plate observations, hundreds of participating agencies, the very high proportion of
non-watchlisted scans, sharing through Vigilant's LEARN ecosystem. Those facts are what *justify*
SIG-CHART-026's vendor-neutrality; without them SIG-CHART-026 is an assertion.

**Text needed.** §23.10 (or §23.6a) `vigilant_network`: writes historical `configured_access` edges
and `UsageAggregate` rows at R3/D2, with `valid_to_kind = 'unknown'` because the dataset is a
2018 snapshot; MUST NOT write current-state claims. Add a §22.2 row with verified access status. Add
to Phase 12 acceptance: `- [ ] At least one historical Vigilant sharing edge is loaded with correct valid-time semantics and does not resolve as current.` Fix §6 row 7's section pointer.

### G-05 · `OL-3-01` — every named local research group is gone

**What is missing.** DeFlock Atlanta, Idaho, Birmingham, Joplin, Lynnwood, Olympia, Redmond, Tucson,
Vegas; Eyes Off Colorado, Indiana, Cedar Rapids; Live Free VA; Monterey Park activists. Only
`eyesoffcr.org` appears, as a one-line §22.3 row. SIG-TASK-014 requires SIG to maintain its own
local-group registry precisely because FlockReporter is unreachable (G C-03) — **and then gives it
nothing to seed with.** Phase 0's acceptance criterion "The local-group registry exists and is
seeded" is unexecutable.

**Text needed.** A §33.7 table listing every group the outline names, with `name | jurisdiction |
known_url | status: unverified`, and a Phase 0 criterion: `- [ ] The local-group registry contains a row for each group named in §33.7, each with a contact attempt recorded (including "no response").`

### G-06 · `OL-5.2-02` + `OL-5.2-03` + `OL-5.3-01` — the international evidence base is absent

**What is missing.** Three distinct things:
- That Technopolice communities **explicitly discussed using OSM rather than isolated databases** —
  the outline's only external corroboration that the OSM-first posture generalizes.
- The `sous-surveillance.net` import of **~12,000 French cameras into OSM for verification** — the
  only worked precedent for the local-activist-DB → common-substrate migration that Phase 18 must
  perform.
- AI Global Surveillance Index, Facial Recognition World Map, Mapping China's Tech Giants.

Phase 18's acceptance criteria name no international dataset at all; they test only that the schema
does not assume US shapes. The phase can pass while ingesting nothing.

**Text needed.** In §5.3, a paragraph recording the Technopolice/OSM convergence and the
sous-surveillance import as the precedent SIG follows; three §22.6 rows; and a Phase 18 criterion:
`- [ ] At least one non-US dataset is ingested end-to-end with jurisdiction-namespaced organization types and a recorded rights record.`

### G-07 · `OL-4.7-01` — no facial-recognition source exists

**What is missing.** *Who Has Your Face?*, the BuzzFeed Clearview AI usage table, Atlas FR
deployments, country-level FR datasets. §13.1's `biometric-id` domain is well specified (face 1:1,
1:N, retrospective, live; iris; DNA; tattoo; gait; voice) and Phase 17 ranks FR second in priority,
with nothing to populate it.

**Text needed.** Four §22.6 registry rows and a line in §23.10 mapping each to `biometric-id` leaves
with its granularity.

### G-08 · `OL-2C-AJ-01` — `flock.ajith.fyi` and the only academic citation are gone

**What is missing.** The outline's single scholarly citation (Monahan, *Grounding the Flock*, 2026)
and the network-visualization precedent it cites. §39.4's network explorer is designed with no
reference to prior art.

**Text needed.** A §6 compact row (`Downstream/peer visualization; no competition`), a §22.6 row, and
a sentence in §39.4 acknowledging the precedent.

### G-09 · `OL-2A-OSM-07` + `OL-2A-DF-05` — OSM's own locators and `deflock-data` are absent

**What is missing.** The OSM copyright URL and the `Tag:man_made=surveillance` wiki URL. §42.3
reasons at length from the OSMF Collective Database and Horizontal Map Layers guidelines and cites
**no retrievable locator for either** — while SIG-LIC-002 requires that "the referenced terms text
MUST itself be archived as evidence" for every source. The spec's single most legally consequential
argument is unsourced by its own standard. Separately, `deflock-data` (the OSM→GeoJSON/vector-tile
extractor) is never named; §23.2 rebuilds extraction from scratch, and G.4 item 5 admits DeFlock's
repository was never located.

**Text needed.** §42.3 opening: "The guidelines relied on here are archived as evidence artifacts
`<id>` and `<id>`, captured `<date>`," plus registry rows for both URLs and for
`github.com/flockhopper3/deflock-data`. Add to Phase 0: `- [ ] The ODbL guideline texts relied on by §42.3 are captured in the evidence store.`

### G-10 · `OL-4.1-06` + `OL-21-32/34` — three corrections rest on uncited sources

**What is missing.** G C-06 corrects the 850,000-camera / 324-community figure to "321 communities"
and explains the counter conflation — citing nothing. G C-08 corrects the ShotSpotter leak to 22,471
— citing nothing. §5.2/§22.5 rest on vendor-replacement dynamics sourced to the Guardian — cited
nowhere. Under SIG-EPIS-002 every claim must reach an EvidenceArtifact; Appendix G's corrections
would all fail that rule if they were claims in the graph.

**Text needed.** Add a `source` column to Appendix G.1 with the artifact id / URL / capture date for
every one of the fourteen corrections, and a line: "Every correction in this table is backed by an
evidence capture registered in §22.6; corrections without one are marked `UNSOURCED` and are not
acted on."

---

## 5. PARTIALS — 58, ordered by severity

### P-01 · `OL-ES-16`, `OL-4.1-02`, `OL-4.10-01` — **body cameras have no home in the ontology**

The outline names body cameras three times: as a technology SIG must accommodate beyond ALPR
(OL-ES-16), as a Fusus input ("body-camera live streams", OL-4.1-02), and as an RTCC convergence
input (OL-4.10-01). §13.1's 13 domains / 35 families contain **no body-worn video family**;
`surveillance-video` covers "Fixed CCTV, PTZ, private-camera registry / integration / per-incident
request, video analytics, camera trailers". §11.6's capability list has `view.livestream.private_camera`
but nothing for officer-worn devices. This is a schema gap, not a data gap: SIG-CHART-028's
generalization suite would pass while the technology is unrepresentable.

**Fix.** Add family `body-worn` to `surveillance-video` with leaves `bwc-recorded`,
`bwc-livestream`, `bwc-unspecified`, and capability `view.livestream.officer`. Add to Phase 1
acceptance.

### P-02 · `OL-ES-31` — J-3's "evidence recommender" is named once and specified nowhere

§2.2 J-3 says the advocate's query "depends on the procurement/renewal layer (§11.10, §39.4) and on
the evidence recommender." **There is no evidence recommender** — no requirement id, no section, no
phase, no acceptance criterion. SIG-CHART-008 makes J-1…J-4 acceptance criteria for the system as a
whole; J-3 therefore cannot pass. (Both section pointers are also wrong: Contract is §11.11 and the
renewal watch is §39.5.)

**Fix.** Either add §39.5a specifying the recommender (rank artifacts by predicate directness,
recency, and the target meeting's agenda topics) with a Phase 15 acceptance criterion, or strike the
phrase and restate J-3 in terms of the existing evidence viewer.

### P-03 · `OL-7.2-04/05/06` — three non-goals' enforcement pointers are wrong or dangling

§4.2's table is the spec's own map from non-goal to enforcement. Three entries are broken:
N4 → §30.6 (**does not exist**; the real rule is §30.3); N5 → §46.5 and §34.6 (§46.5 is "Continuity
and succession"; **§34.6 does not exist**; the real rules are §46.3 and SIG-CONTRIB-007); N6 → §43.6
("Aggregate disclosure"; the real rule is §43.5/SIG-PUB-013, and this same mis-citation is repeated
five more times at §8.3, §11.9 ×2, §23.9, §25.2). The prohibitions themselves are properly enforced;
the bindings are not, and §0.4 SIG-ENG-001 means an agent loading only the cited sections gets the
wrong text or nothing.

### P-04 · `OL-2B-FP-02`, `OL-2B-EOF-03`, `OL-10.1D-02` — three portal fields have no predicate

"Vehicles detected during a recent interval", "hotlist hits", and the portal's own "stated
acceptable/prohibited uses" have no predicate in §23.4, §11.15 or §11.16. Hotlist-hit counts are one
of the two aggregate statistics Eyes on Flock exists to aggregate. `policy_type: acceptable_use`
exists but nothing binds a *portal-published* use statement to a deployment as a first-party claim
distinct from an agency policy document.

**Fix.** Add predicates `vehicles_detected_windowed_count`, `hotlist_hit_windowed_count` (both
VOLATILE, `h` = 1 mo, windowed per SIG-RECON-011), and `portal_stated_permitted_use` /
`portal_stated_prohibited_use` (R2 · D2). Add to §23.4's write list.

### P-05 · `OL-2B-EOF-02` — the portal-discovery problem is never stated

The spec gates Phase 11 on Eyes on Flock and specifies slug-grammar parsing (SIG-IDENT-015), but
never states the load-bearing fact that **Flock publishes no directory and portal discovery is
therefore brute-force enumeration over locality/agency slugs**. An implementer reading §22.5 cannot
size the fallback, and §22.3 states the analogous fact for *agenda platforms* while omitting it for
the source it actually matters for.

### P-06 · `OL-8.16-02` — the DDL drops two fields from its own field spec

§10.3.5 specifies `unit` (for quantities) and `object_type` (`literal | entity_ref | vocab_term |
quantity | money | geometry | duration | interval | document_ref`). Neither exists in §16.2's
`claim` DDL. `unit` is not recoverable from `value_json` by any stated rule, and without
`object_type` a consumer must infer the value's kind from which `value_*` column is non-null —
which is ambiguous for `quantity` vs `money` vs `duration`. Also, `asserted_by` is `text` rather
than a FK to the `Person` entity §11.3 was created for.

### P-07 · `OL-2C-HIBF-08` — three of six HIBF capabilities have no home

Police rosters (no entity, no source class), audit anomaly detection (§34.4 covers only contributor
anomalies), and officer/name resolution (handled by exclusion at SIG-PUB-010 — correct, but the spec
never says "this is how we discharge that obligation," so it reads as an omission).

### P-08 · `OL-3-06` — the Cedar Rapids research-gap object is never produced, and one detector is missing

Detectors 1, 2, 4, 5 cover four of the six listed gaps. **"Latest contract amendment missing" has no
detector**: §11.11 defines `amends_contract`, but no task type fires when a contract's amendment
chain is incomplete. And the outline's second worked example is never demonstrated — Appendix D
works only the Appendix B object.

**Fix.** Add task type 33, "Contract amendment chain incomplete" (detector: contract with
`renewal_options` exercised or `end_date` extended in another source but no `amends_contract`
child), and either extend Appendix D with the Cedar Rapids case or state that D generalizes.

### P-09 · `OL-2E-AA-02`, `OL-2D-AT-02` — two upstream methodologies are never characterized

The Accountability Atlas's five published artifacts (issue-record CSV, source-index CSV, GeoJSON,
data dictionary, research archive) and Atlas's nine methodology components are both unenumerated.
§23.8 and §23.3 therefore specify connectors with no described input shape, and the crosswalks of
§20.3 have no provenance granularity to preserve.

### P-10 · `OL-2F-GOV-01/02` — GovSpend, state auditor surveys, and warrants have no home

GovSpend is named by the outline as a specific origin of Atlas procurement leads and appears nowhere.
"State auditor surveys" and "warrants" have no `artifact_type`, connector, or registry entry, though
§10.3.2's 24-term vocabulary covers everything else in the list.

### P-11 · `OL-ES-19`, `OL-8.3-01`, `OL-9.1-03` — three named things dropped from example lists

Cellebrite (a named Product example, and the subject of OL-4.8-01) appears nowhere. Upturn is
dropped from §10.4's R3 examples despite being an outline Tier-C exemplar; Eyes on Flock was
substituted. These are small individually and matter cumulatively: they are the seams where the
spec's paraphrase quietly loses the outline's specificity.

### P-12 · `OL-2B-FP-04`, `OL-Q17` — the portal obligation is discharged conditionally

§22.5's gate and fallbacks are the right engineering answer to F2.1, and the honesty is a strength.
But OL-2B-FP-04 ("this source demands snapshotting and temporal preservation") is a REQ whose
discharge now depends on an external outcome recorded as BLOCKED, and Q17's answer ("cadence is
moot") does not answer the cadence question for the *fallback* channels, which do exist and do need
one.

### P-13 · `OL-2C-HIBF-03` — the per-search field drop is correct but undocumented

Case number, filters, text prompt and moderation information are per-search fields §18.1 forbids.
That is a defensible correction (and consistent with OL-8.13-01/OL-A.8) — but Appendix G's M-table
does not record it, so a reader auditing the superset claim cannot distinguish a principled
exclusion from an oversight.

### P-14 · `OL-15.7-01` — the six downstream application classes are not export design targets

Academic analysis, newsroom tools, local dashboards, route/privacy applications, policy trackers,
visualizations. §39.0's personas cover four; §38 specifies formats without mapping them to
consumers. Minor, but OL-7.1-08/Goal 8 is measured by "documented downstream reuse."

### P-15 · `OL-2A-OSM-02` — the OSM tag vocabulary is never enumerated

The outline is explicit: "Spec must enumerate the real vocabulary." §23.2 lists field *categories*
and §20.3 names three keys; the actual term values (`surveillance:zone`, `camera:mount`,
`camera:direction`, ALPR classification values) never appear. Phase 4's criterion "normalizes across
all four surveillance keys" names four keys the spec never lists.

### P-16 — remaining PARTIALs

`OL-ES-10`, `OL-2A-SUS-01`, `OL-2A-PC-01`, `OL-2A-DAF-01`, `OL-2B-FP-06`, `OL-2D-DD-01`,
`OL-4.5-01`, `OL-5.2-01`, `OL-18-07`, and the 22 `OL-21-*` name-without-URL rows. All are
instances of G-01: the project or artifact is named and correctly roled, but carries no locator,
so the Phase-0 registry cannot be built from the spec.

---

## 6. DEFECTS — internal inconsistencies in the spec

### D-01 · Seventeen internal `§` references point at sections that do not exist

`§13.9` · `§24.6` · `§25.4` · `§25.5` · `§26.3` · `§27.3` · `§27.9` · `§30.5` · `§30.6` · `§34.6` ·
`§40.5` · `§42.6` · `§42.7` · `§46.6` · `§48.3` · `§48.4` · `§50.4`

Several are load-bearing. `§13.9` is where the *predicate registry* is supposed to live and is the
type authority for `claim.predicate` (§10.3.5) — the registry is actually at §13.6. `§48.3` is cited
by SIG-ENG-004's Definition of Done as the home of pipeline data-quality checks. `§42.7` is cited
three times as the licence-computation rule (real home: §42.4). `§30.5` is cited four times as the
inference-labelling rule (real home: §30.4) and once in §8.2's layer-boundary enforcement table.
`§27.9` is cited twice as the ER quality gate (real home: §14.7). `§40.5` is cited twice as the
derived-vs-observed visual language and does not exist in any form.

### D-02 · At least twenty more `§` references point at the wrong existing section

The `§11` block is systematically off, consistent with entity numbering having shifted after Part I
was drafted and never being re-synced:

| Cited | Cited for | Actual |
|---|---|---|
| §11.2–11.3 | Vendor, Product | §11.2 is Organization; Product is §11.4 |
| §11.6 (×2) | PhysicalAsset | §11.6 is Capability; PhysicalAsset is §11.8 |
| §11.10 (×2) | Contract | §11.10 is DataSystem; Contract is §11.11 |
| §11.11 | Policy, LegalInstrument | §11.11 is Contract; those are §11.13/§11.14 |
| §11.12 | ConfigurationState | §11.12 is FundingInstrument; ConfigurationState is §11.15 |
| §11.13 (×3) | UsageAggregate | §11.13 is Policy; UsageAggregate is §11.16 |
| §11.14 | AccountabilityEvent | §11.14 is LegalInstrument; it is §11.17 |
| §11.15 | DocumentCloud capture metadata | §11.15 is ConfigurationState; the fields are §10.3.2 |
| §11.1 | Organization types | §11.1 is Jurisdiction; §11.2 |
| §11.4 | Technology/Capability independent of Product | §11.4 is Product; §11.5/§11.6 |

Plus: `§30.4` cited for access-path closure (actual §30.2) · `§12.6` for integration-layer
classification (actual §12.3) · `§32.5` for contradiction-resolution rate (actual §32.5 is
completeness estimation; no such metric is defined anywhere) · `§23.4` for Atlas supersession
(actual §23.3) · `§23.6` for Data Driven ingestion (actual §23.6 is procurement) · `§9.6` for
multilingual labels (actual §9.7) · `§13.7` for the jurisdiction model (actual §11.1) · `§39.5` ×2
for the evidence viewer (actual §39.6) · `§39.3` for the ER-quality analytics disclosure (actual
§39.4) · `§33.4` for research-task generation (actual §33.2) · `§33.5` for dispositions (actual
§33.4) · `§16.5` for "normalization stored beside" (actual §16.2) · **"Part X Phase 14" ×2 for the
first non-US adapter and Technopolice/Stage 6 (actual Phase 18; Phase 14 is API and exports)**.

**Why this is severe, not cosmetic.** SIG-ENG-001 requires every phase to be executable from Part 0,
Part I §3, the glossary, and the sections that phase cites. A phase that follows a wrong pointer
loads the wrong text. §11.20 and §11.23 are also declared in the §11.0 index but have no standalone
headings (they are folded into one), and **§11.21 and §11.22 have no heading at all** — `Claim` /
`Resolution` / `Contradiction` and `ResearchTask` are indexed but never sectioned.

**Fix.** Mechanical: regenerate every `§` reference from a heading map and add a CI link-check over
the spec itself as a Phase-0 deliverable.

### D-03 · Requirement-identifier defects

- **`SIG-TIME-002a`** violates the §0.3 grammar (`SIG-<AREA>-<nnn>`, no suffix) and appears **before**
  `SIG-TIME-002` in the document. Either it is a distinct requirement and needs a proper ordinal, or
  it is a sub-clause and should be `SIG-TIME-002.1`.
- **`SIG-ENG-006`…`009` and `SIG-ENG-028`…`029` are never defined.** §0.3 requires that a withdrawn
  id be "marked `WITHDRAWN` in place with the reason and the superseding id"; none is. Six ids are
  simply absent from an append-only namespace.
- **Area codes `A11Y` and `OPS` are declared in §0.3 and carry zero requirements.** Accessibility
  requirements live under `UI` (SIG-UI-005/037) and operations under `ENG` (SIG-ENG-019…027). Either
  the table is wrong or the requirements are mis-prefixed.
- Requirement inventory: **573 defined ids**, no dangling references, no true duplicates besides
  `SIG-TIME-002`/`002a`.

### D-04 · `§0.5`'s research cache lists thirteen workstreams; `§G.4` says seven were terminated

§0.5 presents R1–R13 as the evidentiary foundation and the spec cites them throughout as
corroboration (`R6-F17`, `R7-F7.43`, `R13`, …). G.4 item 6 discloses that **R1, R2, R3, R5, R9, R12
and R13 were terminated by a spend limit**, that R1/R2 were reconstructed "at reduced scope", and
that R3 is partial. That is seven of thirteen. Every `R<n>-F<m>` citation into those seven files is
of unknown standing, and the spec's second load-bearing property ("independently corroborated") is
materially weaker than §0.1 states. §0.1 should carry the caveat, not only G.4.

### D-05 · Stage→Phase mapping drops two outline stages

§51.2's table maps outline stages to phases. **Stage 1E (HIBF / ALPR Watch structural data) and
Stage 1G (accountability events) appear nowhere in the mapping column.** Their content lands (Phase
12 and Phase 13) but those phases are labelled Stage 3 and Stage 4. Stage 1A is mapped twice (Phases
3 and 5), which is correct and stated; 1E/1G are simply missing. Anyone auditing stage coverage from
the table will conclude two stages were dropped.

### D-06 · `§13.1` claims a term count the spec cannot verify

SIG-ONTO-052 asserts "13 domains, 35 families, 101 technologies at v1" and SIG-ONTO-060 asserts "~45
terms". The spec lists 13 domains and gives family-level prose; **the 101 technologies and 45
capabilities are never listed**, deferred to `ontology/vocab/`. That is a reasonable engineering
choice, but the counts are then unfalsifiable normative assertions, and SIG-ONTO-056's requirements
(distinguishing criterion, evidence signature, salience rating per technology) have no artifact in
the spec to check against. Phase 1's acceptance does not test the counts.

### D-07 · Miscellaneous

- **`§29.1`'s six count predicates vs `§11.7`'s "`contracted_device_count` …"** — §11.7 uses an
  ellipsis where §29.1 defines six. A generator reading §11.7 alone produces one predicate.
- **`§16.2`'s append-only trigger uses an illustrative `#` operator** that is not valid PostgreSQL
  and is flagged as such — correctly — but no conformant reference implementation is given, and
  Phase 2's acceptance ("UPDATE/DELETE on `claim` rejected except closing `sys_period`") depends on
  getting exactly this right.
- **`§10.5`'s directness matrix is illustrative only** ("the full matrix ships with the ruleset").
  SIG-ONTO-066 makes a directness row mandatory per predicate, and SIG-EPIS-018's normative
  consequences (the contract/portal case) depend on cells the spec does not publish.
- **`§32` defines no "contradiction resolution rate"** despite §4.1 G2 naming it as the metric that
  measures Goal 2, and citing "§32.5" for it.

---

## 7. TRACE-DEFECTS — what `OUTLINE_TRACE.md` itself under-captured

The trace is accurate and well-formed; every id maps to real outline text. Six things it missed:

1. **`OL-ES-16`'s "body cameras" is buried inside a compound obligation.** Because the trace folded
   seven technologies into one row, the spec could discharge six and fail one without the row
   turning red. Recommend splitting compound `REQ` rows whose members are independently
   satisfiable — this is exactly how the body-camera gap escaped.

2. **No trace row for outline §2 Layer A's "OSM matters because it provides" list beyond OL-2A-OSM-03.**
   The trace captures the seven properties as one row; "contributor infrastructure" and "a mature
   collaborative mapping community" are organizational obligations (they bear on §35.2's
   human-mediated write-back) that the row's granularity hides.

3. **Outline §22.4's seven central questions are captured as one row (`OL-22.4-01`).** They are
   seven independently testable queries and belong in §2.3's acceptance-query set alongside
   Q-1…Q-13. As one row, six of them could be missing invisibly.

4. **No row for outline §15.1's "This may be the single most powerful public-facing primitive" as a
   *prioritization* obligation.** `OL-15.1-03` captures the sentence but not its consequence — that
   the dossier should be built before the map and the network explorer. The spec happens to comply
   (Phase 15 lists the dossier first) but the trace could not have detected non-compliance.

5. **Appendix B's `sharing.incoming_configured: 312` is not separately traced.** `OL-B-06` covers
   `outgoing_configured`, `incoming_configured`, and `national_search_observed` as one row; the
   spec's Appendix D demonstrates outgoing and national but not incoming, and the trace cannot
   register that.

6. **The trace has no row for the outline's own framing of §20 as "mandatory research *tasks*", as
   distinct from questions to be answered in prose.** OL-Q01…Q37 are typed `Q`. Ten of the spec's
   answers are `BLOCKED` or `PARTIAL` — which is honest, but under the outline's framing those are
   *undone tasks*, not answers. A trace row asserting "every BLOCKED/PARTIAL answer must have a
   Stage-0 owner and a due phase" would make that checkable. (The spec mostly does this via §53;
   Q34 and Q35 have no risk-register entry.)

---

## 8. What to fix first

| # | Item | Effort |
|---|---|---|
| 1 | Write Appendix A (traceability matrix) or delete the §0.1 claim + re-point SIG-ENG-031 | M |
| 2 | Write Appendix C (domain-entity DDL) or re-point §16 at §20.1 LinkML generation | L |
| 3 | Add §22.6, the seeded source registry with every OL-21 URL + the 15 absent sources | M |
| 4 | Regenerate all `§` cross-references; add a CI link-check over the spec | S |
| 5 | Fix `source_tier char(1) A..F` → `R1…R6`; add `claim_directness`, `artifact_integrity` | S |
| 6 | Add the body-worn video family + capability; add the ACLU toolkit, Data Driven connector, Data Library roster | M |
| 7 | Seed §33.7 with the outline's named local groups | S |
| 8 | Demote or make testable the six unfalsifiable MUSTs | S |
| 9 | Specify or strike J-3's "evidence recommender" | S |
| 10 | Map Stage 1E / 1G in §51.2; add the missing count/hotlist-hit predicates | S |

---

# 9. CLOSURE RECORD (appended after the fixes were applied)

**Date:** 2026-08-20. **Spec at closure:** 8,078 lines, 596 requirements, 87 distinct source URLs.

## 9.1 Final disposition

| Disposition | At review | After closure |
|---|---|---|
| COVERED | 395 | **479** |
| PARTIAL | 58 | **1** |
| GAP | 27 | **0** |
| CONTRADICTED (rows) | 0 | 0 |
| CONTRADICTED (self-claims) | 4 | **0** |

## 9.2 The four self-claim contradictions

| # | Finding | Closure |
|---|---|---|
| X-01 | Appendix A did not exist, yet §0.1 rested the superset claim on it | **Written.** 480 rows, generated from `OUTLINE_TRACE.md` + this ledger, with SIG-ENG-037 requiring regeneration at every phase gate and CI failure on regression |
| X-02 | Appendix C did not exist; §16's DDL had dangling FK targets | **Written.** All 17 referenced tables now defined, plus relationships, roles, contradiction, coverage, tasks, and the `inference` schema. §C.7 lists what must *never* exist, with a schema test |
| X-03 | §16.2 declared `source_tier char(1) A..F`, which cannot hold the `R1…R6` scale §10.4 mandates | **Fixed.** Replaced with `source_reliability`, `claim_directness`, `artifact_integrity`; currency remains deliberately unstored; `legacy_source_tier` retained as nullable, non-resolving source data |
| X-04 | Six MUSTs were unfalsifiable, contradicting §0.1's testability claim | **Fixed.** Each given a concrete criterion (recorded hostile-reader review; template test suite; moderated usability study with n≥5 and a median target; maintained threat model with mapped mitigations; per-phase risk declarations; a pre-declared slice hardness precondition), with the aspirational statement retained as marked `Rationale` |

## 9.3 The single remaining PARTIAL

`OL-2B-FP-04` — temporal snapshotting of vendor transparency portals. **Deliberately left PARTIAL.**
The architecture is fully specified (§17, §29.7, §17.6) and the fallback channels are defined
(§22.5), but lawful automated access to the source does not exist (F2.1). Marking it COVERED would
be the synthetic certainty §3.1 forbids. It is Phase-0 gated and carried as risk R-02.

## 9.4 Notable closures

- **The source registry went from 1 URL to 87.** §22.6 seeds every OL-21 source plus the sources
  research added; §22.7 adds the specialist-dataset backlog as the Phase 17 ingestion plan.
- **Three named things that had vanished were restored with roles**, not just mentions: the ACLU
  toolkit (which now defines the local-advocate persona the dossier is designed for), EFF Data
  Driven (now a connector with its four substantive findings), and the ~14 local research groups.
- **Body-worn video was genuinely unrepresentable** and is now a technology domain with a capability;
  the domain count moved 13 → 14 and every dependent count was re-synced.
- **The evidence recommender**, on which journey J-3 depended, was named once and specified nowhere;
  §39.5a now specifies it, including a prohibition on ranking by persuasiveness.
- **~40 broken or mis-targeted cross-references** were corrected, and a reference convention plus a
  CI link-check requirement were added so the class of defect cannot silently recur.

## 9.5 Trace defects accepted

The review's TRACE-DEFECTS section is correct: compound trace rows can hide a partial failure, which
is exactly how the body-camera gap escaped detection. `OUTLINE_TRACE.md` is retained as-is for
auditability against the review that used it; **SIG-ENG-037's regeneration requirement should split
compound rows on the next pass.** Recorded here rather than silently fixed, so the trace and the
review that consumed it stay comparable.

---

# 10. COMPLETION-PASS RECORD (2026-08-20, after the spend limit was lifted)

## 10.1 What was finished

Seven workstreams had been terminated mid-run. All are now complete.

| File | Before | After | Findings |
|---|---|---|---|
| R1 OSM / ODbL | 437 | **1,908** | 39 |
| R2 Flock ecosystem | 250 | **1,708** | 20 |
| R3 EFF / accountability | 546 | **1,760** | 54 |
| R12 community | 1,546 | **2,385** | 34 |
| R13 reconciliation | 1,904 | **2,791** | 34 |

Cache total: **26,818 lines · 501 findings · 667 requirements.**

## 10.2 Final disposition

| Stage | COVERED | PARTIAL | GAP | CONTRADICTED |
|---|---|---|---|---|
| Adversarial review | 395 | 58 | 27 | 0 rows / 4 self-claims |
| Gap-closure pass | 479 | 1 | 0 | 0 |
| **Completion pass** | **480** | **0** | **0** | **0** |

## 10.3 A second independent audit was run, and it found regressions

After the completion pass a **fresh adversarial audit** was run specifically to catch damage done by
the edits themselves. It found six real defects, all now fixed:

| # | Defect | Fix |
|---|---|---|
| 1 | §0.1 and G.4 asserted **26,862 lines / 541 findings**; actual was **26,818 / 501** | Corrected. The requirement count (667) was right |
| 2 | **Appendix B never updated** — Q1/Q2/Q3/Q15/Q17 still read `BLOCKED` while §22.5 read `RESOLVED` | All five rewritten |
| 3 | **Phase 11 gating language persisted** in four places — the phase heading, the §23.4 connector heading, SIG-INGEST-035, SIG-ENG-035 | All ungated; SIG-ENG-035 reframed to keep the *ordering* constraint while noting the dependency is satisfied |
| 4 | **G.1 rows C-01/C-04 stale** — C-01 still asserted the withdrawn `deflock.me` claim that G.4.2 withdraws 97 lines later | Both corrected; C-01 now records the withdrawal in place |
| 5 | Two pass-3 requirements were **unfalsifiable MUSTs** (SIG-INGEST-044, -045b) | Demoted to `(RATIONALE)` per §0.2 |
| 6 | `SIG-UI-015` said "Appendix B's content contract", ambiguous between this document's Appendix B and the outline's | Disambiguated |

**Defect 4 is the instructive one.** G.4.2 exists precisely to record self-corrections — and the
correction it records had not been propagated to the table 97 lines earlier. That is the exact
failure mode the section is designed to prevent, occurring inside the section designed to prevent
it. It is the strongest available argument for SIG-ENG-037's requirement that the traceability
matrix be **regenerated and CI-checked** at every phase gate rather than maintained by hand.

## 10.4 Final integrity state

Zero unresolved cross-references · zero duplicate definitions · zero dangling requirement
references · 668 requirements · 106 source URLs · 8,889 lines · Appendix A 480/480 COVERED.
