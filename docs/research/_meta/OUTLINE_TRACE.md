# Outline Traceability Index

Mechanical extraction of every atomic obligation, entity, field, principle, question,
source, non-goal, and worked example in `docs/1_deep_research_overview.md`.

**Purpose.** `docs/2_canonical_design_spec.md` must be a *strict superset* of the outline.
Every `OL-*` id below must be discharged by an identified section of the canonical spec.
The gap analysis walks this file top to bottom and records, for each id, the spec section
that covers it plus how (VERBATIM-PRESERVED / DEEPENED / CORRECTED / EXTENDED).

**Legend for `Type`:**
- `PURPOSE` — mission/thesis statement that must survive intact
- `REQ` — a design obligation
- `ENTITY` / `FIELD` — ontology element the spec must define
- `VOCAB` — a controlled vocabulary the spec must enumerate
- `PRINCIPLE` — an invariant the architecture must not violate
- `NONGOAL` — an explicit prohibition
- `Q` — a mandatory research question (§20)
- `SOURCE` — a named external source the spec must place in its source registry
- `EXAMPLE` — a worked example the spec must be able to reproduce
- `SURFACE` — a product surface
- `STAGE` — a phasing obligation

---

## 0. Executive summary

| ID | Type | Obligation |
|---|---|---|
| OL-ES-01 | PURPOSE | There is no authoritative public database of US surveillance infrastructure; no existing project solves the full problem. The spec must position SIG against this. |
| OL-ES-02 | REQ | The system must answer all 13 enumerated questions: (1) where is a physical device; (2) which org owns/operates it; (3) which technology has an agency adopted; (4) which vendor/product; (5) deployment cost and contract; (6) how many devices purchased/reported; (7) what the system retains/searches/shares; (8) which orgs can access the data; (9) which orgs actually searched it; (10) for what stated reasons; (11) what policies/legal restrictions govern it; (12) has it been suspended/canceled/replaced/challenged/litigated; (13) how it connects to regional/national networks. |
| OL-ES-03 | REQ | Each of those 13 questions is answered today by a *different* system; SIG must join them. |
| OL-ES-04 | SOURCE | OpenStreetMap — best global commons for field-observed physical hardware. |
| OL-ES-05 | SOURCE | DeFlock — specialized ALPR contribution/visualization writing into OSM. |
| OL-ES-06 | SOURCE | Eyes on Flock — portal discovery, aggregation, preservation of rolling audit data. |
| OL-ES-07 | SOURCE | Have I Been Flocked? — FOIA audit logs, normalization, dedup, officer resolution, search-behavior analysis. |
| OL-ES-08 | SOURCE | ALPR Watch — reproducible public-records→SQL pipeline with published code/records/analysis. |
| OL-ES-09 | SOURCE | EFF Atlas of Surveillance — broad US agency×technology dataset. |
| OL-ES-10 | SOURCE | EFF + MuckRock Data Driven — Vigilant/Motorola ALPR networks; proves problem predates Flock and is not vendor-specific. |
| OL-ES-11 | SOURCE | ALPR Accountability Atlas — incidents, abuses, court cases, regulatory decisions, policy changes, local actions with explicit evidence labeling. |
| OL-ES-12 | SOURCE | Flock Finder and Flock-You — radio-based lead generation, NOT authoritative device identification. |
| OL-ES-13 | SOURCE | Drivers Against Flock — downstream consumer of OSM device data; demonstrates value of a stable common device layer. |
| OL-ES-14 | SOURCE | FlockReporter and local DeFlock/Eyes Off orgs — decentralized research/advocacy network. |
| OL-ES-15 | SOURCE | MuckRock — part of the primary-evidence substrate, not merely a secondary resource. |
| OL-ES-16 | REQ | Beyond ALPR the spec must accommodate: facial recognition, cell-site simulators, drones, mobile-device forensics, body cameras, electronic monitoring, Ring partnerships. |
| OL-ES-17 | SOURCE | Axon Fusus / Community Connect — privately owned cameras becoming police-accessible via RTCC platforms. |
| OL-ES-18 | SOURCE | ShotSpotter/SoundThinking — sensor locations exposed via investigative reporting. |
| OL-ES-19 | SOURCE | Historical/specialist datasets: Clearview AI, Cellebrite/mobile forensics, cell-site simulators, Vigilant, public-safety drones. |
| OL-ES-20 | REQ | International: OSM, Surveillance under Surveillance, PanoptiCity, Technopolice show the physical layer can be global while policy/procurement/org/legal layers need jurisdiction-specific adapters. |
| OL-ES-21 | PURPOSE | The opportunity is NOT to build another surveillance map. |
| OL-ES-22 | PURPOSE | Build an open, source-auditable, temporally aware surveillance infrastructure knowledge graph that reconciles fragmented datasets without replacing projects that already do parts well. |
| OL-ES-23 | PURPOSE | Defining purpose (must appear substantially verbatim): make the structure of surveillance infrastructure legible — what exists, where, who controls it, who can access it, how it is connected, what capabilities it provides, what rules govern it, how those facts changed over time, and exactly what evidence supports every claim. |
| OL-ES-24 | PRINCIPLE | The graph must be vendor-agnostic, technology-agnostic, source-preserving, temporal, explicit about uncertainty, and designed for federation rather than appropriation. |
| OL-ES-25 | PRINCIPLE | Core intellectual shift: a surveillance device is NOT the fundamental unit; a *relationship among organizations, technologies, capabilities, physical assets, datasets, policies, and access rights* is. |
| OL-ES-26 | EXAMPLE | The model must represent all of: fixed Flock camera; patrol-car ALPR; Fusus integration exposing 5,000 private cameras to an RTCC; a Clearview license (deployment with no roadside device); a Fog Reveal subscription (location histories with no locally owned sensor); a camera owned by a shopping center but searchable by police (ownership vs access as separate relationships); a canceled Flock contract followed by an Axon replacement (change in implementation, not disappearance). |
| OL-ES-27 | ENTITY | The graph must represent at least these 20: organizations; organizational aliases and hierarchies; vendors; products and platforms; technologies and capabilities; deployments; physical devices/assets; contracts and procurements; data systems; access/sharing relationships; usage/search observations or aggregate usage metrics; configuration states; policies; laws and regulations; incidents and accountability events; source documents; source claims; provenance; temporal validity; confidence/evidentiary status; reconciliation links to upstream datasets. |
| OL-ES-28 | PURPOSE | The greatest value comes from joining evidence that currently cannot be joined — not from owning the largest raw dataset. |
| OL-ES-29 | EXAMPLE | Journalist traversal must be executable: city → police agency → Flock deployment → contract → 42 contracted cameras → 31 field-observed OSM devices → 38 currently reported portal cameras → sharing relationships → actual network searches → retention settings → policy → related litigation → replacement vendor. |
| OL-ES-30 | EXAMPLE | Researcher query must be executable: which US agencies operate ALPRs, share data outside their state, have retention periods over 30 days, and have documented immigration-related searches? |
| OL-ES-31 | EXAMPLE | Advocate query must be executable: which municipalities are considering renewal in the next six months, how many cameras are physically mapped, what the current sharing network looks like, and which source documents would be useful at the next public meeting? |
| OL-ES-32 | EXAMPLE | Systems-researcher query must be executable: which vendors increasingly occupy the same integration layer as Flock, and where are cities replacing one vendor with another rather than reducing surveillance capability? |

---

## 1. Project thesis

| ID | Type | Obligation |
|---|---|---|
| OL-1.1-01 | PRINCIPLE | A point-only representation (camera/lat/lon/manufacturer) is useful but inadequate. |
| OL-1.1-02 | REQ | Model the 12 power-generating combinations: sensor density; historical retention; cross-jurisdictional sharing; centralized search; automated alerts; integration with other databases; private-public access relationships; analytics; identity resolution; institutional policy; legal permissibility; operator behavior. |
| OL-1.1-03 | EXAMPLE | Two jurisdictions with 20 cameras each can differ radically: one retains 7 days and does not share; the other retains a year, participates in nationwide lookup, feeds an RTCC, receives private-camera streams, uses federal hotlists, and permits broad search. The model must make this difference visible. |
| OL-1.1-04 | PRINCIPLE | Model surveillance power as a graph of capabilities and access, not merely a geography of sensors. |
| OL-1.2-01 | PRINCIPLE | The right design principle is federation. |
| OL-1.2-02 | NONGOAL | Do not fork DeFlock's camera database into a competing dataset. |
| OL-1.2-03 | NONGOAL | Do not ask users to report the same camera twice. |
| OL-1.2-04 | NONGOAL | Do not replicate EFF's volunteer research workflow. |
| OL-1.2-05 | NONGOAL | Do not re-host HIBF's plate-level search tool. |
| OL-1.2-06 | NONGOAL | Do not scrape normalized data while discarding provenance. |
| OL-1.2-07 | NONGOAL | Do not present SIG as the authoritative replacement for existing civil-society projects. |
| OL-1.2-08 | REQ | Instead: (1) preserve upstream identifiers; (2) ingest or reference upstream datasets where legally/technically permissible; (3) contribute corrections upstream when possible; (4) attach SIG-derived reconciliation claims separately; (5) make provenance visible; (6) expose missing links and contradictions; (7) generate research tasks that improve upstream sources as well as the graph. |
| OL-1.2-09 | PURPOSE | SIG becomes a coordination and reconciliation layer across a pluralistic ecosystem. |

---

## 2. Ecosystem — Layer A (physical infrastructure)

| ID | Type | Obligation |
|---|---|---|
| OL-2A-OSM-01 | SOURCE | OSM supports `man_made=surveillance` and associated tags. |
| OL-2A-OSM-02 | VOCAB | Surveillance objects can carry: surveillance type; zone; camera type; direction; operator; manufacturer; mounting; ALPR classification. Spec must enumerate the real vocabulary. |
| OL-2A-OSM-03 | REQ | OSM provides: stable geographic primitives; edit history; contributor infrastructure; global coverage; machine-readable extraction; a mature collaborative mapping community; interoperability with Overpass and downstream GIS. |
| OL-2A-OSM-04 | PRINCIPLE | OSM is a neutral substrate not owned by one surveillance-specific activist project. |
| OL-2A-OSM-05 | PRINCIPLE | Strategic conclusion: exact physical-device observations should normally live in OSM first. |
| OL-2A-OSM-06 | REQ | ODbL is consequential. The design must determine whether a combined database is a Derivative Database, a Collective Database, or can keep OSM-derived material legally separable. Must not casually merge OSM data into a differently-licensed monolith without legal review. |
| OL-2A-OSM-07 | SOURCE | https://www.openstreetmap.org/copyright ; https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance |
| OL-2A-DF-01 | SOURCE | DeFlock — specialized ALPR discovery, mapping, education, contribution interface. |
| OL-2A-DF-02 | PRINCIPLE | DeFlock's key decision is using the OSM commons rather than an isolated proprietary DB. |
| OL-2A-DF-03 | REQ | DeFlock helps people: identify ALPR hardware; see known nearby devices; report devices; add manufacturer/operator info; contribute field observations. |
| OL-2A-DF-04 | PRINCIPLE | DeFlock is an upstream field-observation system, not a dataset SIG should replace. |
| OL-2A-DF-05 | SOURCE | `deflock-data` — extracts ALPR nodes from OSM, produces GeoJSON/vector-tile artifacts. |
| OL-2A-DF-06 | FIELD | SIG must preserve: OSM element ID; OSM version; observation/update timestamp; coordinates; surveillance tags; manufacturer; operator; device direction; relevant OSM provenance. |
| OL-2A-DF-07 | REQ | SIG adds: link device→deployment; deployment→agency/private owner; deployment→contract; compare physically observed count with contractual/portal counts; represent lifecycle status; attach evidence supporting attribution; surface unresolved attribution. |
| OL-2A-SUS-01 | SOURCE | Surveillance under Surveillance (https://sunders.uber.space/) — global OSM surveillance visualization. |
| OL-2A-SUS-02 | REQ | It evidences that (1) OSM already has an international surveillance community; (2) the physical layer scales outside the US; (3) SIG must avoid inventing a US-only device schema. |
| OL-2A-PC-01 | SOURCE | PanoptiCity (https://panopticity.fr/) — CCTV coverage / field-of-view analysis. |
| OL-2A-PC-02 | PRINCIPLE | Distinguish **source facts** (camera exists at coordinate X with direction Y) from **derived facts** (estimated FOV intersects area Z). Derived facts must never be confused with source observations. |
| OL-2A-DAF-01 | SOURCE | Drivers Against Flock (https://driversagainstflock.org/) — privacy routing on OSM camera data; corrections flow back to OSM. |
| OL-2A-DAF-02 | REQ | The ecosystem architecture to encourage: field observation → OpenStreetMap → many downstream applications (DeFlock, Drivers Against Flock, research, SIG). SIG must make reusable higher-order data available downstream rather than forcing every app to re-scrape upstreams. |

## 2. Ecosystem — Layer B (official/vendor deployment + sharing metadata)

| ID | Type | Obligation |
|---|---|---|
| OL-2B-FP-01 | SOURCE | Flock Transparency Portals — opt-in, agency-specific, vendor-hosted snapshots of configuration, usage, sharing. |
| OL-2B-FP-02 | FIELD | Portal fields to model: agency name; last-updated date; data-retention period; total cameras; vehicles detected during a recent interval; searches; hotlists; hotlist hits; organizations granted access; organizations sharing data inward; stated acceptable/prohibited uses; public search-audit CSV; links or text for agency policies. |
| OL-2B-FP-03 | PRINCIPLE | Portals are first-party evidence but NOT complete/authoritative: agencies can lack portals; there is no convenient master directory; values change; a portal may disappear; public audit logs are limited and redacted; statistics are rolling rather than immutable history. |
| OL-2B-FP-04 | REQ | This source demands snapshotting and temporal preservation. |
| OL-2B-FP-05 | REQ | Portal retention periods vary dramatically; portal records can include active/inactive organizations, bidirectional sharing, private organizations, federal organizations, universities, and other nontraditional entities. The model must accommodate all of these. |
| OL-2B-FP-06 | SOURCE | https://transparency.flocksafety.com/ ; example portals green-brook-twp-nj-pd, hagerstown-md-pd. |
| OL-2B-EOF-01 | SOURCE | Eyes on Flock — portal discovery, aggregation, historical preservation, sharing-network analysis. Explicitly *not peripheral*; a key player underweighted in the first pass. |
| OL-2B-EOF-02 | REQ | Portal discovery is by brute-force enumeration over locality/agency URL slugs because Flock publishes no complete directory. |
| OL-2B-EOF-03 | FIELD | EoF provides/described: searchable table of discovered portals; aggregated statistics across portals; reported camera totals; hotlist-hit statistics; search-reason aggregation; maps of organizations listed in portal sharing sections; historical retention of public search-audit entries that would otherwise roll off Flock's ~30-day public window. |
| OL-2B-EOF-04 | REQ | Its four+ infrastructural contributions: portal discovery; temporal archiving; normalization; cross-portal aggregation; sharing-relationship extraction. |
| OL-2B-EOF-05 | REQ | SIG should NOT independently build a competing portal-discovery crawler without first determining whether EoF can expose an API, data export, archive, or collaboration interface. If independent archival is still needed for reproducibility, coordinate conventions and preserve cross-identifiers. |
| OL-2B-IND-01 | SOURCE | Independent transparency-portal archival projects (e.g. a California sharing visualization) taking PDF snapshots; raw HTML snapshots; normalized JSON; daily portal captures; sharing edges; inferred agencies when the target lacked a visible portal. |
| OL-2B-IND-02 | PRINCIPLE | "Archival truth": the graph must distinguish *what the portal says now* / *what the portal said on date T* / *what our parser extracted on date T* / *what later evidence says about the same state*. |
| OL-2B-IND-03 | PRINCIPLE | The raw source snapshot must remain immutable. |

## 2. Ecosystem — Layer C (usage and audit behavior)

| ID | Type | Obligation |
|---|---|---|
| OL-2C-HIBF-01 | SOURCE | Have I Been Flocked? — large-scale public-records aggregation and analysis of Flock search activity; one of the most consequential projects in the ecosystem. |
| OL-2C-HIBF-02 | ENTITY | **Organization Audit** — searches by users belonging to the audited organization. |
| OL-2C-HIBF-03 | ENTITY | **Network Audit** — searches from other organizations that touched/shared against the audited org's data. Fields: organization; camera count; time frame; reason; case number; filters; search timestamp; search type; text prompt; moderation information. |
| OL-2C-HIBF-04 | ENTITY | **Portal/Public Audit** — the more heavily redacted, limited public audit tied to transparency portals. |
| OL-2C-HIBF-05 | ENTITY | **SharedNetworks.csv** — configuration snapshot expressing sharing edges in both directions. |
| OL-2C-HIBF-06 | ENTITY | **Event logs** — administrative changes: hotlist operations; network sharing changes; user/role changes; camera renaming; live-stream activity. |
| OL-2C-HIBF-07 | ENTITY | **Configuration screenshots** — sharing behavior; live-stream permissions; retention; third-party integrations; statewide/nationwide access; policies and feature controls. |
| OL-2C-HIBF-08 | REQ | HIBF also documents: officer/name resolution; police rosters; duplicate handling; source-agency provenance; anomaly detection; records-request templates. SIG must account for each. |
| OL-2C-HIBF-09 | PRINCIPLE | Treat HIBF as the authoritative upstream specialist for Flock *usage observations*; SIG represents aggregate and structural conclusions rather than reproducing a searchable corpus of sensitive plate-level records. |
| OL-2C-AW-01 | SOURCE | ALPR Watch — reproducible FOIA aggregation and analysis pipeline. |
| OL-2C-AW-02 | REQ | Its pipeline shape: MuckRock requests → raw documents → file classification → CSV/XLSX/ZIP parsing → normalized SQL → derived/coded fields → dashboard analysis. SIG's connector architecture must mirror this. |
| OL-2C-AW-03 | REQ | Its 2025 Flock FOIA work: pulls records through the MuckRock API; identifies Organization Audit and Network Audit exports; supports heterogeneous archive/file formats; preserves raw values; creates normalized/derived columns; makes reason-code mappings inspectable; publishes analysis code; links back to raw records. |
| OL-2C-AW-04 | PRINCIPLE | User-entered "Reason" fields are messy inconsistent free text; normalization requires judgment; derived categorization must remain inspectable and reversible. |
| OL-2C-AW-05 | PRINCIPLE | **Never overwrite source text with normalized semantics.** Store: `raw_claim`, `normalized_claim`, `normalization_method`, `normalization_version`, `review_status`. |
| OL-2C-AJ-01 | SOURCE | flock.ajith.fyi — visual network analysis of Flock relationships; cited in academic surveillance research (Monahan 2026). |
| OL-2C-AJ-02 | PRINCIPLE | Network topology is a first-class public-interest visualization; surveillance is edges across jurisdictions, not merely points. |

## 2. Ecosystem — Layer D (agency-level adoption)

| ID | Type | Obligation |
|---|---|---|
| OL-2D-AT-01 | SOURCE | EFF Atlas of Surveillance — broadest mature US OSINT database of police surveillance technology deployment. |
| OL-2D-AT-02 | REQ | Its methodology combines: OSINT; news reporting; government documents; meeting minutes; press releases; procurement leads; crowdsourcing; staff/intern review; imported specialist datasets. |
| OL-2D-AT-03 | PRINCIPLE | Atlas explicitly states its data is not a complete inventory. Absence from the Atlas is not evidence of absence. SIG must encode this. |
| OL-2D-AT-04 | REQ | Atlas's deepest contribution is a mature taxonomy and a precedent for evidence-reviewed surveillance research. |
| OL-2D-AT-05 | SOURCE | Atlas Data Library maps earlier specialist projects: Atlas Border Communities; Who Has Your Face?; public-safety drones; historical Ring/Neighbors partnerships; cell-site simulator datasets; AI Global Surveillance Index; federally funded body cameras; wiretap reports; Aaron Swartz Day Police Surveillance Project; California ALPR survey data; Vigilant ALPR Data Driven datasets; Upturn mobile-device forensic-tool research; Clearview AI usage data; electronic monitoring; state policy datasets; other specialized collections. |
| OL-2D-AT-06 | REQ | Atlas should seed the agency/deployment layer, but SIG must preserve its source attribution and allow subsequent evidence to supersede or temporally qualify a deployment. |
| OL-2D-DD-01 | SOURCE | EFF Data Driven / Data Driven 2 — Vigilant Solutions ALPR sharing research. |
| OL-2D-DD-02 | REQ | Documented: billions of plate observations; hundreds of participating agencies; very high proportions of non-watchlisted scans; sharing through Vigilant's LEARN ecosystem. |
| OL-2D-DD-03 | PRINCIPLE | A Flock-centric graph would mis-model the problem. ALPR capability must branch to Flock Safety, Motorola/Vigilant, Rekor, Axon, Genetec, other/local systems — with integration between them modeled separately when evidence exists. |

## 2. Ecosystem — Layer E (accountability, incidents, litigation, policy)

| ID | Type | Obligation |
|---|---|---|
| OL-2E-AA-01 | SOURCE | ALPR Accountability Atlas — structured, source-auditable catalog of ALPR incidents and policy/accountability events. |
| OL-2E-AA-02 | REQ | Publishes: issue-record CSV; source-index CSV; GeoJSON; data dictionary; research archive. |
| OL-2E-AA-03 | VOCAB | Record categories: local regulation/action; litigation; wrongful stop/false alert; immigration/data sharing; security/product issues; stakeholder/company context. |
| OL-2E-AA-04 | PRINCIPLE | It distinguishes allegations; findings; court actions; policy decisions; company statements. **SIG must adopt this model.** |
| OL-2E-AA-05 | PRINCIPLE | The graph must not flatten "X happened" when the evidence says "a plaintiff alleged X in a pending lawsuit." Those are different epistemic states. |
| OL-2E-AL-01 | SOURCE | ALPR Abuse Library / Kansas Watch — editorially reviewed index of published reporting documenting ALPR harms. |
| OL-2E-AL-02 | PRINCIPLE | Not every useful source must be normalized immediately into "facts"; a curated source index is valuable by itself. |
| OL-2E-AL-03 | REQ | The graph must link an incident node to: primary record; court record; agency statement; vendor statement; investigative article; advocacy analysis. |
| OL-2E-AC-01 | SOURCE | ACLU Get the Flock Out toolkit — advocacy toolkit / local organizing guidance; demonstrates a key downstream user. |
| OL-2E-AC-02 | SURFACE | The graph must support "local dossier" outputs containing: known deployments; vendor; contract; renewal date; camera count; mapped device count; sharing relationships; retention; audit activity; governing policy; upcoming decision points; documented incidents. |

## 2. Ecosystem — Layer F (records and primary evidence)

| ID | Type | Obligation |
|---|---|---|
| OL-2F-MR-01 | SOURCE | MuckRock — public-records request infrastructure and primary-source repository; foundational because many surveillance datasets originate in records requests. |
| OL-2F-MR-02 | FIELD | Model MuckRock as: `records_request`, `requesting_party`, `target_agency`, `request_text`, `date`, `response_status`, `released_documents`, `document_metadata` — not just a URL. |
| OL-2F-MR-03 | PRINCIPLE | Where possible, derived claims must link to the exact released document rather than a downstream article. |
| OL-2F-DC-01 | SOURCE | DocumentCloud and investigative archives — treat as **evidence stores**, not citation URLs. |
| OL-2F-DC-02 | FIELD | Useful metadata: document title; issuing organization; document date; acquisition method; page range; checksum; archive URL; parser/OCR status; relevant extracted claims. |
| OL-2F-DC-03 | REQ | The same principle applies to city agenda packets, procurement PDFs, contracts, invoices, policy manuals, court filings, and released spreadsheets. |
| OL-2F-GOV-01 | SOURCE | Government procurement and meeting records; Atlas notes many leads originate in procurement data including GovSpend. |
| OL-2F-GOV-02 | SOURCE | Other source classes: city/county procurement portals; state procurement systems; council/board agenda systems; budgets; warrants; grants; USAspending.gov; SAM.gov; state auditor surveys; public meeting minutes; police policies; public-records portals. |
| OL-2F-GOV-03 | PRINCIPLE | These sources frequently identify surveillance **before a device is mapped in the field**. |

## 2. Ecosystem — Layer G (lead generation and field detection)

| ID | Type | Obligation |
|---|---|---|
| OL-2G-FF-01 | SOURCE | Flock Finder — probable-device discovery via WiGLE radio observations and Flock-associated hardware OUI prefixes. |
| OL-2G-FF-02 | PRINCIPLE | Generates leads at scale but must NOT be conflated with verified hardware, because: WiGLE coverage is opportunistic; observations can be stale; an OUI indicates vendor-associated hardware not necessarily a currently installed ALPR at that point; radio-location estimates can be imprecise; devices may move; hardware identifiers can create false positives. |
| OL-2G-FF-03 | REQ | The required flow: radio observation → candidate surveillance asset → field verification / public record / imagery → confirmed physical device → OSM. |
| OL-2G-FY-01 | SOURCE | Flock-You — ESP32 local hardware detection of Flock-associated radio signatures. |
| OL-2G-FY-02 | FIELD | Reveals a future **observation protocol**: observation; observer/source type = passive radio; timestamp; location estimate; identifier prefix; confidence; verification status. |
| OL-2G-FY-03 | REQ | The design must include safeguards against publishing sensitive private-residence hypotheses or turning low-confidence radio observations into accusations. |

---

## 3. Decentralized local research ecosystem

| ID | Type | Obligation |
|---|---|---|
| OL-3-01 | SOURCE | Named local groups: DeFlock Atlanta, Idaho, Birmingham, Joplin, Lynnwood, Olympia, Redmond, Tucson, Vegas; Eyes Off Colorado, Indiana, Cedar Rapids; Live Free VA; Monterey Park activists; local county/city privacy organizations. |
| OL-3-02 | SOURCE | FlockReporter (https://flockreporter.org/) maintains a directory of such efforts. |
| OL-3-03 | REQ | §3.1 They generate evidence: file records requests, attend meetings, photograph devices, collect contracts, discover private deployments, verify whether systems are active. |
| OL-3-04 | REQ | §3.2 They detect state changes earlier than national databases: a camera removed yesterday; a renewal on next week's agenda; sharing disabled after controversy; a vendor switch; a portal disappearance; a private institution joining the network. National datasets inevitably lag. |
| OL-3-05 | REQ | §3.3 They are ideal consumers of reconciliation tasks. |
| OL-3-06 | EXAMPLE | The Cedar Rapids research-gap object must be producible: contract indicates 78 cameras; OSM has 61 probable ALPR devices; portal reports 75; 14 OSM devices have unknown operator; latest contract amendment missing; sharing snapshot 94 days old. |
| OL-3-07 | PURPOSE | This turns the graph into a **research coordination system**, not merely a passive database. |

---

## 4. Beyond Flock — the broader surveillance stack

| ID | Type | Obligation |
|---|---|---|
| OL-4-00 | PRINCIPLE | The project must resist letting Flock define the ontology. |
| OL-4.1-01 | REQ | Municipalities leaving Flock are replacing it with Axon or others rather than abandoning ALPR capability. |
| OL-4.1-02 | REQ | Fusus is an integration layer for RTCCs connecting: public cameras; private cameras; body-camera live streams; ALPRs; drones; other sensor/dispatch systems. |
| OL-4.1-03 | SOURCE | Axon Community Connect — public-facing community portals where private orgs/individuals register or share cameras. |
| OL-4.1-04 | REQ | A crowdsourced enumeration reported >850,000 privately owned cameras across 324 publicly listed communities. **This must be independently verified before being treated as canonical.** |
| OL-4.1-05 | PRINCIPLE | `camera owner != data controller != police accessor != platform provider` — all four must be represented separately. |
| OL-4.1-06 | SOURCE | Guardian 2026-08-20 vendor-replacement reporting; axoncommunityconnect.com; the Reddit enumeration discussion. |
| OL-4.2-01 | REQ | Vigilant/Motorola demonstrates: vendor-network sharing; private ALPR data; large-scale retention; cross-agency lookup; bulk location-history search. EFF Data Driven is a priority ingestion source for the first vendor-neutral ALPR model. |
| OL-4.3-01 | REQ | Rekor: distinguish device manufacturer; service vendor; data platform; agency operator; local-storage vs vendor-cloud architecture where evidence permits. Vendor-level assumptions must never substitute for deployment-specific evidence. |
| OL-4.4-01 | REQ | Genetec: the relevant fact may be a software integration rather than recognizable roadside hardware. **Capability must be first-class.** |
| OL-4.5-01 | SOURCE | ShotSpotter/SoundThinking; the WIRED leak of >25,000 sensor locations. |
| OL-4.5-02 | FIELD | Acoustic sensors need: acoustic sensor; installed location; service area; operating agency; vendor; historical status. The graph must allow physical acoustic sensors without forcing them into a "camera" abstraction. |
| OL-4.6-01 | REQ | Cell-site simulators may have no persistent public coordinate; represent as agency → deploys → cell-site simulator capability, with equipment, procurement, warrant policy, and known use represented separately. |
| OL-4.7-01 | SOURCE | Facial recognition datasets: EFF Who Has Your Face?; BuzzFeed Clearview AI usage table; Atlas FR deployments; country-level FR datasets. |
| OL-4.7-02 | ENTITY | Introduces **reference databases**: agency → can query → facial recognition system → searches against → image/reference database. The database is infrastructure even with no local sensor. |
| OL-4.8-01 | REQ | Upturn's *Mass Extraction* documents acquisition of tools such as Cellebrite; the graph must include **investigative extraction capabilities**, not just persistent sensors. |
| OL-4.9-01 | REQ | Commercial location-data systems (e.g. Fog Reveal): mobile apps → ad-tech/location brokers → commercial data vendor → law-enforcement investigative platform → agency. |
| OL-4.9-02 | PRINCIPLE | Surveillance infrastructure increasingly consists of **data-access relationships rather than locally deployed hardware**. A graph that cannot represent this has modeled the 20th-century surveillance state. |
| OL-4.10-01 | REQ | RTCCs form a convergence layer combining: cameras; ALPR; CAD/911; gunshot detection; drones; private-camera feeds; body cameras; databases; analytics. |
| OL-4.10-02 | REQ | Represent **integration hubs** as systems/deployments that consume other systems, e.g. Fusus Deployment integrates→camera registry, →Flock ALPR, →city CCTV, →drone program, and accessed_by→RTCC. More revealing than five disconnected "technology adoption" rows. |

---

## 5. International landscape

| ID | Type | Obligation |
|---|---|---|
| OL-5-01 | REQ | US is the initial focus because: public-records law creates rich primary evidence; EFF/MuckRock provide mature infrastructure; the Flock ecosystem is unusually observable; agency identifiers and jurisdiction structures are tractable; there is immediate public-interest demand. |
| OL-5-02 | PRINCIPLE | The data model must be international from the beginning. |
| OL-5.1-01 | REQ | OSM already supports surveillance nodes globally — the strongest reason not to create a bespoke US coordinate schema. |
| OL-5.2-01 | SOURCE | Technopolice (La Quadrature du Net) — documented/mapped CCTV; intelligent video; facial recognition experiments; drones; thermal cameras; acoustic sensors; "safe city" systems. |
| OL-5.2-02 | REQ | Technopolice communities explicitly discussed using OSM rather than isolated databases. |
| OL-5.2-03 | REQ | A historical French `sous-surveillance.net` dataset of ~12,000 cameras was imported into OSM for verification — a concrete path from local activist DB to common substrate. |
| OL-5.3-01 | SOURCE | International datasets: AI Global Surveillance Index; Facial Recognition World Map; Mapping China's Tech Giants — mostly country/vendor/deployment level. |
| OL-5.3-02 | REQ | Support them later as coarser claims with **explicit granularity**. |

---

## 6. What is missing from the ecosystem

| ID | Type | Obligation |
|---|---|---|
| OL-6-00 | REQ | Systems already exist for: physical camera mapping; agency adoption mapping; portal aggregation; Flock audit analysis; public-records acquisition; incident indexing; policy advocacy; avoidance routing. The missing piece is a **general reconciliation layer** across them. |
| OL-6.1-01 | REQ | Canonical entity resolution. The same org appears as e.g. Los Angeles Police Department / LAPD / Los Angeles CA PD / City of Los Angeles Police Dept. / Los Angeles Police Dept. |
| OL-6.1-02 | REQ | Flock organization identifiers may not match: EFF agency names; ORI codes; OSM operator values; procurement vendor/customer names; MuckRock jurisdiction records; police rosters; court documents. |
| OL-6.1-03 | PRINCIPLE | Entity resolution is foundational infrastructure, not ancillary. |
| OL-6.2-01 | EXAMPLE | Cross-source reconciliation must produce statements of the form: contract executed 2025-03-14 specifies 30 Falcon cameras; portal reported 28 active on 2026-07-01; OSM contains 24 field-observed nodes assigned to this agency as of 2026-08-20; three additional candidate devices unmapped to an operator; one local news story reports two relocations in June; therefore the graph currently estimates 28 active contracted devices, 24 physically mapped, 4 unresolved. |
| OL-6.2-02 | PRINCIPLE | This is reconciliation, not aggregation. |
| OL-6.3-01 | REQ | The graph must be fundamentally temporal, answering: when was the contract signed; when did deployment begin; when did sharing turn on; when was ICE access disabled; when did the city cancel; when were devices removed; when did another vendor replace them. |
| OL-6.3-02 | PRINCIPLE | A relationship must rarely be modeled as `A shares with B = true`; instead `A shared with B` + `valid_from` + `valid_to` + `observed_at` + `source`. |
| OL-6.4-01 | PRINCIPLE | Provenance must attach to **claims or assertions**, not only entities, because one source may support vendor identity, camera count, and contract date while not supporting exact coordinates, current active status, or retention period. |
| OL-6.5-01 | PRINCIPLE | Contradiction is a first-class state. Given portal=20, contract=25, city presentation=22, OSM=18, the system must not choose one silently; it must preserve all claims plus a resolution with value, confidence, and rationale. |
| OL-6.5-02 | PRINCIPLE | The disagreement itself is useful research information. |
| OL-6.6-01 | REQ | Network topology across vendors: modern policing integrates Flock; Fusus; state fusion centers; federal systems; Vigilant/Motorola; private cameras; commercial data providers; RTCCs. The graph must eventually reveal **multi-vendor surveillance pathways**. |
| OL-6.7-01 | VOCAB | Lifecycle states: proposed; pilot; approved; contracted; installation; active; expanded; restricted; suspended; nonrenewed; canceled; decommissioning; removed; replaced. |
| OL-6.7-02 | PRINCIPLE | Most datasets flatten this into "uses technology". Without lifecycle and replacement edges, analyses falsely count vendor churn as surveillance reduction. |

---

## 7. Project definition

| ID | Type | Obligation |
|---|---|---|
| OL-7-01 | PURPOSE | SIG is an open-source, public-interest knowledge system that continuously reconciles evidence about surveillance technologies, deployments, physical infrastructure, organizational access, procurement, policy, usage, and accountability events. |
| OL-7-02 | PRINCIPLE | It does not attempt to observe private individuals. It observes institutions and infrastructure. |
| OL-7.1-01 | REQ | Goal 1 Discover — identify deployments/infrastructure from heterogeneous public sources. |
| OL-7.1-02 | REQ | Goal 2 Reconcile — resolve duplicate organizations, devices, deployments, vendors, and claims across datasets. |
| OL-7.1-03 | REQ | Goal 3 Preserve provenance — every material fact traceable to source evidence. |
| OL-7.1-04 | REQ | Goal 4 Preserve time — record when a claim was true, when it was observed, and when it changed. |
| OL-7.1-05 | REQ | Goal 5 Expose relationships — ownership, operation, access, data sharing, integration, procurement, replacement as edges. |
| OL-7.1-06 | REQ | Goal 6 Quantify incompleteness — make coverage gaps visible rather than implying completeness. |
| OL-7.1-07 | REQ | Goal 7 Coordinate research — turn contradictions and missing evidence into structured research tasks. |
| OL-7.1-08 | REQ | Goal 8 Serve downstream users — stable open exports/API primitives for journalists; researchers; civil-liberties organizations; local communities; policy analysts; mapping applications; watchdog projects. |
| OL-7.2-01 | NONGOAL | Do not create a searchable database of ordinary people's movements. |
| OL-7.2-02 | NONGOAL | Do not re-publish plate-level audit data merely because it is public. |
| OL-7.2-03 | NONGOAL | Do not track individual law-enforcement officers unless necessary for a documented accountability claim and consistent with a carefully developed policy. |
| OL-7.2-04 | NONGOAL | Do not infer private individuals' identities from cameras or radio observations. |
| OL-7.2-05 | NONGOAL | Do not encourage trespass, vandalism, interference, or destruction of surveillance equipment. |
| OL-7.2-06 | NONGOAL | Do not publish speculative exact locations of sensitive private residences based only on weak RF observations. |
| OL-7.2-07 | NONGOAL | Do not replace OpenStreetMap as the physical-device editing system. |
| OL-7.2-08 | NONGOAL | Do not replace EFF's Atlas as the primary broad crowdsourced adoption-research project. |
| OL-7.2-09 | NONGOAL | Do not replace HIBF as the specialist audit-log analysis project. |
| OL-7.2-10 | NONGOAL | Do not represent SIG as exhaustive or "authoritative" when the evidence is incomplete. |

---

## 8. Conceptual graph model (every entity and field is an obligation)

| ID | Type | Obligation |
|---|---|---|
| OL-8.1-01 | ENTITY | **Organization**. Examples that must be representable: municipality; police department; sheriff; state police; federal agency; university police; school district; HOA; corporation; private security organization; hospital; vendor; fusion center; nonprofit. |
| OL-8.1-02 | FIELD | Organization fields: `id`, `canonical_name`, `aliases[]`, `organization_type`, `parent_organization`, `jurisdiction`, ORI/government identifiers, `addresses`, source identifiers, `valid_from`/`valid_to`. |
| OL-8.2-01 | ENTITY | **Vendor** — an organization with domain-specific relationships: offers Product; supplies Deployment; acquires Vendor. |
| OL-8.2-02 | EXAMPLE | `Axon acquired -> Fusus` must be representable. |
| OL-8.2-03 | PRINCIPLE | Temporal corporate history matters because product names and ownership change. |
| OL-8.3-01 | ENTITY | **Product**. Examples: Flock Falcon; Flock platform; Vigilant LEARN; Axon Fusus; Clearview AI; Fog Reveal; Cellebrite UFED; ShotSpotter. |
| OL-8.3-02 | PRINCIPLE | A Product is not equivalent to a Technology. |
| OL-8.4-01 | ENTITY | **Technology / capability**. Examples: ALPR; facial recognition; fixed CCTV; private camera federation; acoustic gunshot detection; cell-site simulation; mobile-device extraction; drone surveillance; real-time video; geolocation-data search; social-media monitoring; predictive policing. |
| OL-8.4-02 | PRINCIPLE | This abstraction allows vendor-independent queries. |
| OL-8.5-01 | ENTITY | **Deployment** — an organization has implemented or contracted for some product/capability; the bridge between organizational adoption and individual devices. |
| OL-8.5-02 | FIELD | Deployment fields: `organization`, `vendor`, `product`, `technologies[]`, `status`, `proposed_at`, `approved_at`, `contracted_at`, `active_from`, `inactive_at`, `quantity_claims[]`, `jurisdiction`. |
| OL-8.6-01 | ENTITY | **PhysicalAsset**. Examples: fixed ALPR; mobile ALPR; CCTV camera; gunshot sensor; drone; camera trailer; RTCC facility. |
| OL-8.6-02 | FIELD | PhysicalAsset fields: `asset_type`, `geometry`, `mobility`, `manufacturer`, `model`, `operator`, `owner`, `deployment`, `first_observed`, `last_observed`, `upstream_ids[]`. |
| OL-8.6-03 | PRINCIPLE | Coordinates must not be required for movable assets. |
| OL-8.7-01 | ENTITY | **DataSystem**. Examples: ALPR cloud dataset; image database; commercial location dataset; RTCC platform; integrated investigative platform. |
| OL-8.7-02 | FIELD | DataSystem fields: `operator`, `vendor`, `product`, `data_types`, `retention`. |
| OL-8.8-01 | ENTITY | **AccessRelationship** — one of the most important edges: Organization A can_access DataSystem / Deployment / Organization B data. |
| OL-8.8-02 | FIELD | Attributes: `scope`, `direction`, `automatic/manual`, `nationwide/statewide/local`, `valid_from`, `valid_to`, `observed_at`, `source`. |
| OL-8.8-03 | PRINCIPLE | Do not reduce all Flock network relationships to "shares_with". **Direction matters.** |
| OL-8.9-01 | ENTITY | **IntegrationRelationship**. Examples: Axon Fusus deployment integrates Flock deployment; RTCC consumes_feed_from private camera registry. |
| OL-8.10-01 | ENTITY | **Contract / Procurement**. |
| OL-8.10-02 | FIELD | Contract fields: `buyer`, `seller`, `amount`, `signed_date`, `start_date`, `end_date`, `renewal_options`, `products`, `quantities`, `document`. |
| OL-8.10-03 | REQ | A contract can produce or modify a deployment. |
| OL-8.11-01 | ENTITY | **Policy**. Examples: retention policy; acceptable use; warrant requirement; immigration restriction; reproductive-health restriction; audit requirement; external sharing policy. |
| OL-8.11-02 | FIELD | A policy must be scoped: `applies_to` Organization/Deployment/Product; effective period; `policy_type`; text/source. |
| OL-8.12-01 | ENTITY | **ConfigurationState** — policies and actual software configuration are different. HIBF's documentation makes this distinction extremely important. |
| OL-8.12-02 | EXAMPLE | Written policy "no immigration enforcement" vs software configuration "immigration hotlist enabled" must be representable **without editorially collapsing the contradiction**. |
| OL-8.13-01 | ENTITY | **UsageObservation / UsageAggregate**; the core graph should prefer aggregate or structural observations. |
| OL-8.13-02 | FIELD | `SearchAggregate`: `searching_org`, `source_org`, `period`, `count`, `search_scope`, `reason_category`. |
| OL-8.13-03 | PRINCIPLE | Raw sensitive audit data can remain in specialist repositories. |
| OL-8.14-01 | ENTITY | **Incident / AccountabilityEvent**. Examples: lawsuit; false stop; alleged stalking misuse; immigration-search controversy; policy violation; data breach; city moratorium; contract cancellation; public hearing; security finding. |
| OL-8.14-02 | FIELD | Fields must include epistemic state: `event_type`; `alleged / confirmed / adjudicated / policy_action / vendor_statement`; `date`; `organizations`; `deployments`; `sources`. |
| OL-8.15-01 | ENTITY | **EvidenceArtifact**. |
| OL-8.15-02 | FIELD | Fields: `url`, `source_type`, `publisher`, `title`, `date`, `retrieved_at`, `checksum`, `archived_copy`, `license`, `primary_or_secondary`. |
| OL-8.15-03 | REQ | Examples that must be supported: contract PDF; council minutes; audit CSV; portal snapshot; OSM observation; news article; court filing; agency policy. |
| OL-8.16-01 | ENTITY | **Claim** — possibly the most important object in the entire system. |
| OL-8.16-02 | FIELD | Fields: `subject`, `predicate`, `object/value`, `valid_time`, `observed_time`, `source`, `extraction_method`, `confidence`, `review_status`. |
| OL-8.16-03 | EXAMPLE | subject: Deployment ABC; predicate: active_camera_count; value: 38; valid_time: 2026-07-23; source: Flock portal snapshot XYZ. Another source may produce a competing claim. |

---

## 9. Epistemic architecture

| ID | Type | Obligation |
|---|---|---|
| OL-9-01 | PRINCIPLE | Design around the difference between: fact; observation; claim; inference; derived metric; unresolved contradiction. |
| OL-9.1-01 | VOCAB | **Tier A** direct primary operational evidence: exported audit logs; configuration exports/screenshots; signed contracts; invoices; official device inventories; government datasets; court records; direct field observation. |
| OL-9.1-02 | VOCAB | **Tier B** first-party public statements: transparency portals; official press releases; council presentations; vendor statements; agency policy pages. |
| OL-9.1-03 | VOCAB | **Tier C** reviewed specialist datasets: EFF Atlas; HIBF processed data; ALPR Accountability Atlas; Upturn; other transparent research datasets. |
| OL-9.1-04 | VOCAB | **Tier D** high-quality investigative reporting — for claims whose primary source is inaccessible and for contextual/accountability events. |
| OL-9.1-05 | VOCAB | **Tier E** community reports: local activist databases; user submissions; inferred locations. |
| OL-9.1-06 | VOCAB | **Tier F** heuristic discovery: RF/OUI matches; automated web extraction with unresolved entity matching; model-generated candidate matches. |
| OL-9.1-07 | PRINCIPLE | The hierarchy is a useful default, not a rigid ranking. Lower tier does not mean "bad"; it means the claim needs clearer uncertainty. |
| OL-9.2-01 | PRINCIPLE | **Never collapse observation time and validity time.** A portal captured Aug 20 saying "25 cameras" proves only that on Aug 20 the portal reported 25 — not that 25 were physically installed. This distinction must be encoded. |
| OL-9.3-01 | PRINCIPLE | Confidence must be explainable. Avoid opaque "87% confidence" unless probability is actually calibrated. |
| OL-9.3-02 | VOCAB | Prefer labels with reasons: `confirmed`, `strongly supported`, `probable`, `unverified`, `contradicted`, `historical` — plus machine-readable evidence counts. |
| OL-9.4-01 | PRINCIPLE | Negative claims need special treatment; absence from a dataset means little. |
| OL-9.4-02 | EXAMPLE | No OSM camera ≠ no camera exists. No Atlas row ≠ agency lacks the technology. No transparency portal ≠ not a Flock customer. No HIBF audit data ≠ never searched. |
| OL-9.4-03 | REQ | The UI **and** API must make coverage explicit. |

---

## 10. Source ingestion strategy

| ID | Type | Obligation |
|---|---|---|
| OL-10.1A-01 | STAGE | **Phase 1A canonical entities** — build a durable organization/vendor/jurisdiction registry first; without it every subsequent integration becomes duplicate-heavy. |
| OL-10.1A-02 | REQ | Identity aids: Atlas agency names; ORI identifiers where available; Census geographic identifiers; government domains; OSM operator strings; Flock portal slugs; MuckRock jurisdiction IDs. |
| OL-10.1B-01 | STAGE | **Phase 1B OSM/DeFlock physical ALPR layer** — ingest surveillance nodes retaining OSM ID; version; tags; coordinates; edit timestamp; attribution. |
| OL-10.1B-02 | PRINCIPLE | Do not make SIG the canonical editing database for physical devices. |
| OL-10.1C-01 | STAGE | **Phase 1C EFF Atlas** — import deployments and their source references. |
| OL-10.1C-02 | REQ | Do not overwrite Atlas taxonomy blindly; create mappings between Atlas technology categories and SIG's normalized technology ontology. |
| OL-10.1D-01 | STAGE | **Phase 1D Flock portal ecosystem** — prefer collaboration/API/export from Eyes on Flock if feasible. |
| OL-10.1D-02 | REQ | Capture: portal identity; portal snapshots; camera count; retention; usage metrics; outward/inward sharing; hotlists; policies; public audits. Create temporal observations rather than current-state overwrite. |
| OL-10.1E-01 | STAGE | **Phase 1E HIBF / ALPR Watch structural data** — do not initially ingest every plate/search record. |
| OL-10.1E-02 | REQ | Ingest or derive: organizations observed; audit source coverage; sharing edges; search counts; search-scope metrics; reason-category aggregates; configuration claims; source-document links. Keep specialist raw-data custody where it already exists. |
| OL-10.1F-01 | STAGE | **Phase 1F contracts / MuckRock / public records** — start with records already linked by upstream projects, then expand through MuckRock; government portals; procurement systems; city agenda systems. |
| OL-10.1G-01 | STAGE | **Phase 1G accountability events** — ingest/cross-reference ALPR Accountability Atlas; ALPR Abuse Library; court cases; policy actions; contract cancellations/replacements. |

---

## 11. Reconciliation workflows

| ID | Type | Obligation |
|---|---|---|
| OL-11.1-01 | REQ | **Camera-count reconciliation.** Inputs: contract quantity; portal reported count; OSM observed count; agency public statement; invoice quantity; local records inventory. |
| OL-11.1-02 | FIELD | Outputs: `reported_active_count`; `physically_mapped_count`; `contracted_count`; `unresolved_delta`; `evidence`. |
| OL-11.1-03 | PRINCIPLE | Do not produce a false single "true count" where evidence is ambiguous. |
| OL-11.2-01 | REQ | **Device attribution.** An OSM Flock camera with operator=unknown inside jurisdiction X, plus a deployment where agency X has 20 contracted devices, yields candidate relation `asset operated_by agency X` with status `probable, not confirmed`. |
| OL-11.2-02 | REQ | A field mapper or public-records researcher can resolve it. |
| OL-11.3-01 | REQ | **Sharing-edge reconciliation.** Potential sources: portal "sharing with"; portal "receiving from"; SharedNetworks.csv; network-audit actual queries; policy statements. |
| OL-11.3-02 | PRINCIPLE | These encode different concepts — **configured access**, **actual use**, **declared policy** — and must never be merged into one edge. |
| OL-11.4-01 | EXAMPLE | **Deployment lifecycle reconciliation** must produce timelines like: 2025-01 proposed; 2025-03 contract signed; 2025-06 20 devices active; 2026-04 sharing restricted; 2026-07 nonrenewal announced; 2026-08 cameras still physically present; 2026-09 Axon replacement scheduled. This is the historical record users actually need. |

---

## 12. Research task generation

| ID | Type | Obligation |
|---|---|---|
| OL-12-00 | REQ | Automatic creation of research leads must be one of the most distinctive project features. |
| OL-12-01 | REQ | Task: **missing physical devices** — portal reports 40; 27 mapped in OSM → locate/verify remaining devices. |
| OL-12-02 | REQ | Task: **missing contract** — Atlas and portal confirm deployment; no procurement evidence linked → find contract/invoice/council approval. |
| OL-12-03 | REQ | Task: **conflicting retention** — agency policy says 30 days; portal reports 365 → obtain current configuration or clarification. |
| OL-12-04 | REQ | Task: **stale evidence** — latest deployment source is 30 months old → verify active status. |
| OL-12-05 | REQ | Task: **orphaned device** — OSM camera has manufacturer but no operator → establish operator via public records/signage/field evidence. |
| OL-12-06 | REQ | Task: **new sharing node** — network logs contain an organization absent from the organization registry → resolve identity and jurisdiction. |
| OL-12-07 | REQ | Task: **vendor replacement** — Flock contract terminated; procurement record shows Axon ALPR → link a `replaced_by` lifecycle edge rather than mark surveillance removed. |
| OL-12-08 | PURPOSE | This turns the system into a living research network. |

---

## 13. Ethical and security constraints

| ID | Type | Obligation |
|---|---|---|
| OL-13-00 | PRINCIPLE | The project itself must not become a surveillance system. |
| OL-13.1-01 | PRINCIPLE | Bright-line default: the graph tracks public or institutionally relevant surveillance infrastructure and organizational behavior, not ordinary people's movements. |
| OL-13.1-02 | REQ | Plate-level search data should generally remain with projects explicitly designed and governed to handle it, such as HIBF. |
| OL-13.2-01 | REQ | Avoid storing: license plates; private-person names; individual travel histories; residential associations; officer personal addresses; unrelated personal identifiers. |
| OL-13.2-02 | REQ | Where an accountability event requires a named public official or officer, apply a clear public-interest standard. |
| OL-13.3-01 | REQ | Treat exact coordinates contextually. A publication policy must distinguish: publicly visible roadside device; hidden sensor on public infrastructure; private-residence candidate; confidential facility; mobile asset. |
| OL-13.4-01 | REQ | Preserve source without overexposing sensitive contents. The system may need: raw private archival storage; redacted public derivative; source hash; restricted access; metadata-only public representation. |
| OL-13.5-01 | REQ | Explicitly support: research; journalism; policy analysis; lawful field observation; public-records work. |
| OL-13.5-02 | NONGOAL | Do not provide instructions for damaging, disabling, tampering with, or evading lawful enforcement in the commission of wrongdoing. |

---

## 14. Licensing and data governance

| ID | Type | Obligation |
|---|---|---|
| OL-14.1-01 | REQ | OSM is share-alike database data; combining substantial OSM content with proprietary/incompatible datasets may attach distribution obligations. |
| OL-14.1-02 | REQ | Strategy A — keep OSM as a separable external layer (store identifiers, fetch/map separately). |
| OL-14.1-03 | REQ | Strategy B — publish the OSM-derived physical-asset table under ODbL; keep other evidence-graph tables under a separate compatible/open license. |
| OL-14.1-04 | REQ | Strategy C — license the entire public data graph compatibly. |
| OL-14.1-05 | REQ | The final design needs actual legal analysis, not assumptions. |
| OL-14.2-01 | FIELD | Every imported dataset must have first-class license metadata: `license`; `attribution requirement`; `redistribution permission`; `derivative permission`; `source terms`; `retrieval date`. |
| OL-14.2-02 | PRINCIPLE | Do not discover after launch that a key dataset cannot legally be redistributed. |
| OL-14.3-01 | PRINCIPLE | Open source code is not enough; the mission requires meaningfully reusable **data outputs**. |
| OL-14.3-02 | REQ | Provide: open code; open schemas; downloadable datasets where licensing permits; documented APIs; provenance; versioned snapshots; reproducible ingestion. |

---

## 15. Product surfaces

| ID | Type | Obligation |
|---|---|---|
| OL-15.1-01 | SURFACE | **Local surveillance dossier.** Input: city/county/agency. |
| OL-15.1-02 | FIELD | Output must include: technologies deployed; vendors; status; device counts; physical map; contracts; annual cost; retention; data sharing; inbound/outbound access; audit coverage; policy; incidents/litigation; historical timeline; missing evidence. |
| OL-15.1-03 | PRINCIPLE | This may be the single most powerful public-facing primitive. |
| OL-15.2-01 | SURFACE | **Infrastructure map** — not just dots. Layers: physical devices; organizational deployments; RTCCs; data-sharing edges; private-public camera networks; service areas; proposed/active/decommissioned status. |
| OL-15.3-01 | SURFACE | **Surveillance network explorer** — graph view answering: who can access whose data; which organizations serve as hubs; how a local camera becomes accessible nationally; which federal/private actors appear most often. |
| OL-15.4-01 | SURFACE | **Procurement / renewal watch** — for every contract: expiration; renewal window; council approval; replacement procurement. Transforms passive historical transparency into actionable civic timing. |
| OL-15.5-01 | SURFACE | **Evidence viewer** — every claim expandable to: Claim; Evidence; Source excerpt/page; Original document; Extraction method; Review status; Conflicting claims; History. |
| OL-15.6-01 | SURFACE | **Research queue** — contributors pick structured unresolved tasks rather than being asked to "research surveillance". |
| OL-15.7-01 | SURFACE | **Machine-readable API / exports** enabling: academic analysis; newsroom tools; local dashboards; route/privacy applications; policy trackers; visualizations. |

---

## 16. Initial release boundaries

| ID | Type | Obligation |
|---|---|---|
| OL-16-01 | REQ | The strongest initial wedge: US ALPR infrastructure, modeled completely enough that the ontology naturally generalizes. |
| OL-16-02 | REQ | Why it works (12 reasons): rich OSM device data; DeFlock contributor ecosystem; Flock portal data; Eyes on Flock; HIBF; ALPR Watch; historical Vigilant/EFF data; active public-records movement; current procurement activity; multiple vendors; strong network-sharing semantics; device + software + policy + access all present. |
| OL-16-03 | VOCAB | Initial technology scope must include at least: Flock; Motorola/Vigilant; Rekor; Axon ALPR where data exists; Genetec ALPR; unknown/other ALPR. |
| OL-16-04 | REQ | The schema must support the non-ALPR extensions from day one. |

---

## 17. Staged project plan

| ID | Type | Obligation |
|---|---|---|
| OL-17.0-01 | STAGE | **Stage 0 ecosystem coordination**, before writing ingestion code: contact/investigate collaboration interfaces with DeFlock; Eyes on Flock; Have I Been Flocked; ALPR Watch; EFF Atlas; ALPR Accountability Atlas; relevant local groups. |
| OL-17.0-02 | STAGE | Stage 0 also: determine data licenses; identify APIs/exports; avoid duplicating expensive work; define attribution and contribution-back mechanisms. |
| OL-17.1-01 | STAGE | **Stage 1 canonical graph nucleus** — build organizations; jurisdictions; vendors; products; technologies; deployments; source/evidence; claims; temporal assertions. Seed with Atlas; OSM ALPR; Flock portal organizations. |
| OL-17.1-02 | STAGE | Stage 1 goal: reliably answer "who, what technology, where, according to which evidence?" |
| OL-17.2-01 | STAGE | **Stage 2 ALPR reconciliation** — add camera counts; device attribution; contracts; lifecycle; sharing edges; portal snapshots; public-record links. |
| OL-17.2-02 | STAGE | Stage 2 goal: reliably answer "what is deployed and how do the independent sources agree/disagree?" |
| OL-17.3-01 | STAGE | **Stage 3 usage/network layer** — integrate aggregate structural information from HIBF; ALPR Watch; Flock network configuration; historical Vigilant sharing. |
| OL-17.3-02 | STAGE | Stage 3 goal: answer "who can access whose data, and who actually does?" |
| OL-17.4-01 | STAGE | **Stage 4 accountability and policy** — add policy; laws; incidents; litigation; restrictions; cancellations; replacements. |
| OL-17.4-02 | STAGE | Stage 4 goal: show the governance and consequence layer. |
| OL-17.5-01 | STAGE | **Stage 5 broader surveillance technologies**, prioritized: private-camera federation/Fusus; facial recognition; cell-site simulators; mobile-device forensic tools; gunshot detection; drones; commercial location-data access; RTCC integration systems. |
| OL-17.6-01 | STAGE | **Stage 6 international expansion** — global OSM physical surveillance; French/Belgian Technopolice data; country-level surveillance datasets; jurisdiction-specific organizational adapters. |

---

## 18. Relationship to existing projects (the whole table is an obligation)

| ID | Type | Obligation |
|---|---|---|
| OL-18-01 | REQ | OpenStreetMap — global physical-device commons → upstream canonical device geography. |
| OL-18-02 | REQ | DeFlock — ALPR discovery/reporting UX → direct contributors upstream to OSM; link/reconcile. |
| OL-18-03 | REQ | Eyes on Flock — portal discovery, aggregation, archival history → partner/ingest/reference portal temporal layer. |
| OL-18-04 | REQ | Have I Been Flocked — audit-log corpus and behavioral analysis → partner/reference structural aggregates and evidence. |
| OL-18-05 | REQ | ALPR Watch — reproducible FOIA normalization → reuse methods/code/data where compatible. |
| OL-18-06 | REQ | EFF Atlas — agency surveillance adoption taxonomy → primary seed for deployment layer. |
| OL-18-07 | REQ | EFF Data Driven — Vigilant ALPR sharing history → vendor-neutral ALPR network source. |
| OL-18-08 | REQ | ALPR Accountability Atlas — incident/legal/accountability records → link/integrate events, preserve evidence semantics. |
| OL-18-09 | REQ | MuckRock — public-records workflow and source files → primary evidence substrate. |
| OL-18-10 | REQ | Drivers Against Flock — privacy routing over OSM → downstream consumer; do not compete. |
| OL-18-11 | REQ | Flock Finder — RF-derived candidate discovery → lead generation only. |
| OL-18-12 | REQ | Flock-You — local RF detection → observation lead, never automatic confirmation. |
| OL-18-13 | REQ | FlockReporter — local ecosystem directory/coordination → discover collaborators and local evidence. |
| OL-18-14 | REQ | Local DeFlock/Eyes Off groups — field research and civic action → contributors, validators, consumers. |
| OL-18-15 | REQ | Technopolice — European surveillance mapping/research → international model and future data source. |
| OL-18-16 | REQ | Surveillance under Surveillance — global OSM visualization → downstream/peer visualization. |
| OL-18-17 | REQ | PanoptiCity — coverage/field-of-view analysis → possible downstream analytical consumer. |

---

## 19. Data-quality principles (each is an architectural invariant)

| ID | Type | Obligation |
|---|---|---|
| OL-19.1 | PRINCIPLE | **Provenance over convenience** — never store a "fact" if the evidence-backed claim that generated it can be stored. |
| OL-19.2 | PRINCIPLE | **Raw before normalized** — preserve source form. |
| OL-19.3 | PRINCIPLE | **Time before overwrite** — append state transitions. |
| OL-19.4 | PRINCIPLE | **Uncertainty before false precision** — unknown is legitimate. |
| OL-19.5 | PRINCIPLE | **Federation before duplication** — improve upstream commons. |
| OL-19.6 | PRINCIPLE | **Organization identity before graph analytics** — bad entity resolution makes every network statistic misleading. |
| OL-19.7 | PRINCIPLE | **Capability before vendor** — vendors change, capabilities persist. |
| OL-19.8 | PRINCIPLE | **Ownership is not access** — model separately: owner; operator; controller; platform provider; accessor; data recipient. |
| OL-19.9 | PRINCIPLE | **Configured access is not actual use** — model both. |
| OL-19.10 | PRINCIPLE | **Policy is not configuration** — model both. |
| OL-19.11 | PRINCIPLE | **Contracted is not installed** — model lifecycle. |
| OL-19.12 | PRINCIPLE | **Installed is not active** — preserve last observation. |

---

## 20. Mandatory research questions (all 37 must be answered in the spec)

| ID | Type | Question |
|---|---|---|
| OL-Q01 | Q | Does Eyes on Flock expose an API, downloadable database, or archival repository? |
| OL-Q02 | Q | Can we obtain its historical portal snapshots directly? |
| OL-Q03 | Q | What are its reuse/license terms? |
| OL-Q04 | Q | What exact exports does HIBF make available, under what license and update cadence? |
| OL-Q05 | Q | What APIs/exports does ALPR Watch publish? |
| OL-Q06 | Q | What stable machine-readable interfaces does EFF Atlas currently expose beyond CSV? |
| OL-Q07 | Q | What are MuckRock API constraints and redistribution terms? |
| OL-Q08 | Q | What data can be pulled from DocumentCloud programmatically? |
| OL-Q09 | Q | What is the best public canonical U.S. law-enforcement agency identifier? |
| OL-Q10 | Q | How complete are ORI codes, and how should non-law-enforcement entities be represented? |
| OL-Q11 | Q | Which public datasets provide canonical municipal/county/state identifiers? |
| OL-Q12 | Q | How should private organizations in Flock/Fusus networks be disambiguated? |
| OL-Q13 | Q | Precisely how does ODbL apply to a graph that joins OSM device records to non-OSM entities? |
| OL-Q14 | Q | Can an OSM physical-assets table remain logically/licensably separate? |
| OL-Q15 | Q | What licenses govern Atlas, HIBF, Eyes on Flock, ALPR Watch, and Accountability Atlas data? |
| OL-Q16 | Q | What source documents may be archived vs merely linked? |
| OL-Q17 | Q | What snapshot cadence is justified for transparency portals? |
| OL-Q18 | Q | How should deleted portals and inactive organizations be preserved? |
| OL-Q19 | Q | How should OSM edit history be represented without replicating the entire OSM history database? |
| OL-Q20 | Q | Should canonical storage be relational/PostGIS with graph projections, a property graph, RDF, or hybrid? |
| OL-Q21 | Q | Which model best supports claim-level provenance and bitemporal history? |
| OL-Q22 | Q | How should high-volume audit aggregates remain separate from the main knowledge graph? |
| OL-Q23 | Q | Which connectors can be incremental? |
| OL-Q24 | Q | Which sources require scraping? |
| OL-Q25 | Q | How should source snapshots be content-addressed? |
| OL-Q26 | Q | What parser architecture handles PDFs, HTML, CSV, XLSX, ZIP, JSON, meeting systems, and contracts? |
| OL-Q27 | Q | Which matches can be deterministic? |
| OL-Q28 | Q | Where should fuzzy/model-assisted matching generate review queues rather than writes? |
| OL-Q29 | Q | How should aliases and mergers be represented? |
| OL-Q30 | Q | What public-data publication policy should govern plate numbers, personal names, private-residence detections, and other sensitive content? |
| OL-Q31 | Q | Which raw public records should be stored privately but represented publicly only by metadata? |
| OL-Q32 | Q | How should takedown/correction requests work? |
| OL-Q33 | Q | How can corrections flow upstream to OSM/DeFlock? |
| OL-Q34 | Q | Could Atlas consume deployment corrections? |
| OL-Q35 | Q | Can research tasks link directly to HIBF/MuckRock workflows? |
| OL-Q36 | Q | Could local groups claim geographic research queues? |
| OL-Q37 | Q | What stable IDs would allow other projects to link back to graph entities? |

---

## 21. Priority source registry (every URL must appear in the spec's source registry)

| ID | Type | Source |
|---|---|---|
| OL-21-01 | SOURCE | OSM surveillance tagging — wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance |
| OL-21-02 | SOURCE | OSM license — openstreetmap.org/copyright |
| OL-21-03 | SOURCE | DeFlock |
| OL-21-04 | SOURCE | DeFlock data pipeline (`deflock-data`) |
| OL-21-05 | SOURCE | Surveillance under Surveillance — sunders.uber.space |
| OL-21-06 | SOURCE | PanoptiCity — panopticity.fr |
| OL-21-07 | SOURCE | Drivers Against Flock — driversagainstflock.org |
| OL-21-08 | SOURCE | Eyes on Flock — eyesonflock.com |
| OL-21-09 | SOURCE | Eyes on Flock project description (Reddit) |
| OL-21-10 | SOURCE | Have I Been Flocked — haveibeenflocked.com |
| OL-21-11 | SOURCE | HIBF methodology hub — /about |
| OL-21-12 | SOURCE | HIBF audit-log guide — /about/audit-logs |
| OL-21-13 | SOURCE | ALPR Watch — alprwatch.org |
| OL-21-14 | SOURCE | ALPR Watch Flock FOIA methodology — /news/2025-07-28_flock_foia/ |
| OL-21-15 | SOURCE | Flock Transparency Portals — transparency.flocksafety.com |
| OL-21-16 | SOURCE | EFF Atlas of Surveillance — atlasofsurveillance.org |
| OL-21-17 | SOURCE | Atlas methodology |
| OL-21-18 | SOURCE | Atlas Data Library |
| OL-21-19 | SOURCE | EFF Street-Level Surveillance — eff.org/issues/street-level-surveillance |
| OL-21-20 | SOURCE | ALPR Accountability Atlas — alpratlas.org |
| OL-21-21 | SOURCE | ALPR Abuse Library — library.kansas.watch |
| OL-21-22 | SOURCE | ACLU Get the Flock Out toolkit |
| OL-21-23 | SOURCE | MuckRock — muckrock.com |
| OL-21-24 | SOURCE | DocumentCloud — documentcloud.org |
| OL-21-25 | SOURCE | Flock Finder — github.com/simeononsecurity/flock-finder |
| OL-21-26 | SOURCE | Flock-You — github.com/colonelpanichacks/flock-you |
| OL-21-27 | SOURCE | FlockReporter — flockreporter.org |
| OL-21-28 | SOURCE | Technopolice — technopolice.fr |
| OL-21-29 | SOURCE | Technopolice mapping discussion — forum.technopolice.fr/topic/405 |
| OL-21-30 | SOURCE | Historical/specialist datasets via EFF Data Library: Vigilant/Data Driven ALPR data; California ALPR surveys; Who Has Your Face?; Clearview AI usage table; cell-site simulator datasets; public-safety drone datasets; Mass Extraction/mobile forensics; electronic monitoring; AI Global Surveillance Index; Ring/Neighbors historical partnerships. |
| OL-21-31 | SOURCE | ACLU Stingray tracking devices page |
| OL-21-32 | SOURCE | WIRED ShotSpotter sensor-location leak |
| OL-21-33 | SOURCE | Axon Community Connect — axoncommunityconnect.com/communities |
| OL-21-34 | SOURCE | Guardian 2026-08-20 Flock cameras surveillance |
| OL-21-35 | SOURCE | EFF/MuckRock Data Driven release (2018) |
| OL-21-36 | SOURCE | Monahan, "Grounding the Flock" (2026) |
| OL-21-37 | SOURCE | Reddit r/FlockSurveillance: California sharing visualization; ALPR abuse documentation announcement |

---

## 22. Critical conclusions

| ID | Type | Obligation |
|---|---|---|
| OL-22.1-01 | PRINCIPLE | There is no master surveillance database because the problem is inherently multi-layered. Different facts are generated by different systems: physical location by field observation; purchase by procurement; contractual quantity by contract; active quantity by operator/vendor; sharing by configuration; actual use by audit log; legality by statute/court; policy by agency documents; abuse by investigation/litigation; replacement by future procurement. |
| OL-22.1-02 | PRINCIPLE | The correct architecture cannot have a single "source of truth"; it needs **source-auditable reconciliation**. |
| OL-22.2-01 | PURPOSE | The graph should become authoritative about provenance, not omniscient about reality. The strongest responsible claim: "for every claim we publish, we can show where it came from, when it was observed, how it was normalized, what contradicts it, and how confident we are." |
| OL-22.3-01 | PRINCIPLE | Flock is the ideal starting laboratory but the wrong permanent boundary. The lasting ontology is `surveillance capability → deployment → assets / data / access`, not `Flock camera`. |
| OL-22.4-01 | PRINCIPLE | The most important graph edges may matter more than the nodes. Central questions: who can search them; who can receive alerts; which private cameras feed police; which local system connects to which national system; which vendor integrates which data; which agencies are high-centrality sharing hubs; which federal actors gain access through local relationships. |
| OL-22.4-02 | REQ | Treat network analytics as central, not ornamental. |
| OL-22.5-01 | PRINCIPLE | Temporal reconciliation is a major differentiator. As of Aug 2026 cities are canceling Flock; leaving hardware installed during transitions; reducing retention; changing sharing; adopting safeguards; moving to competing vendors. |
| OL-22.5-02 | REQ | A temporal graph must distinguish `surveillance removed` from `vendor replaced`, and `contract canceled` from `devices still deployed`. |
| OL-22.6-01 | PURPOSE | Success is measured partly by whether the system makes other projects stronger: DeFlock receives better operator attribution; Atlas receives newly documented deployments; HIBF receives more targeted records submissions; local groups learn which records are missing; journalists locate primary evidence faster; researchers reproduce national analyses without rebuilding entity resolution. |
| OL-22.6-02 | PURPOSE | The project becomes connective infrastructure for a movement of independent researchers. |

---

## 23. One-sentence specification

| ID | Type | Obligation |
|---|---|---|
| OL-23-01 | PURPOSE | Build an open, vendor-agnostic, temporally versioned, claim-level-provenance knowledge graph of surveillance infrastructure that federates existing public-interest datasets and primary records to show what surveillance capabilities exist, where and by whom they are deployed, how they are connected and accessed, what rules and contracts govern them, how they are actually used when evidence exists, how they change over time, and exactly which sources support or contradict every material claim. |

---

## 24. Guidance to the downstream design agent (all 18 are binding)

| ID | Type | Obligation |
|---|---|---|
| OL-24-01 | REQ | Re-verify the ecosystem yourself; projects move rapidly. |
| OL-24-02 | REQ | Inspect primary repositories, exports, licenses, schemas, and APIs. |
| OL-24-03 | REQ | Contact assumptions with evidence; do not assume data access because a website exists. |
| OL-24-04 | REQ | Solve entity identity before designing impressive graph visualizations. |
| OL-24-05 | REQ | Design provenance and temporal semantics before writing ingestion adapters. |
| OL-24-06 | REQ | Treat OSM licensing as a first-order architectural constraint. |
| OL-24-07 | REQ | Prefer federation to copying. |
| OL-24-08 | REQ | Preserve upstream IDs. |
| OL-24-09 | REQ | Separate raw evidence, extracted claims, normalized claims, and derived conclusions. |
| OL-24-10 | REQ | Keep sensitive person-level surveillance data outside the main graph unless a compelling, reviewed public-interest use requires it. |
| OL-24-11 | REQ | Make contradictions inspectable. |
| OL-24-12 | REQ | Design contributor workflows around concrete reconciliation tasks. |
| OL-24-13 | REQ | Make the first release narrowly excellent at U.S. ALPR infrastructure while keeping the ontology general. |
| OL-24-14 | REQ | Model private-public surveillance relationships from the start. |
| OL-24-15 | REQ | Model software/data access systems that have no fixed physical sensor. |
| OL-24-16 | REQ | Model replacement and lifecycle so vendor churn is not mistaken for surveillance reduction. |
| OL-24-17 | REQ | Produce stable public exports and APIs wherever licensing permits. |
| OL-24-18 | REQ | Make the final system reproducible enough that a journalist can defend a graph claim by tracing it back to evidence. |
| OL-24-19 | PRINCIPLE | **The defining standard: No unexplained dots. No unexplained edges. No silent overwrites. No synthetic certainty.** |
| OL-24-20 | PRINCIPLE | Every node has identity. Every edge has semantics. Every state has time. Every claim has evidence. Every inference says it is an inference. Every contradiction stays visible until resolved. |

---

## Appendix A — findings that changed the conception

| ID | Type | Obligation |
|---|---|---|
| OL-A.1 | REQ | Eyes on Flock is foundational, not peripheral: brute-force portal enumeration and historical preservation solve undocumented portal enumeration and loss of rolling audit history. Core prospective collaborator. |
| OL-A.2 | REQ | The local research network is itself infrastructure; the graph should organize and return useful research tasks to it. |
| OL-A.3 | REQ | Vendor replacement is already occurring; a Flock-specific system would become obsolete precisely when successful. |
| OL-A.4 | REQ | Private-camera federation is enormous; counting government-owned cameras severely understates police-accessible visual infrastructure. |
| OL-A.5 | REQ | The fundamental unit is an access relationship; hardware is increasingly one endpoint in a larger information network. |
| OL-A.6 | REQ | The graph needs a lifecycle model; "uses Flock" is too crude. |
| OL-A.7 | REQ | The graph needs claim-level provenance; row-level citations are inadequate for reconciling contradictory quantitative and temporal claims. |
| OL-A.8 | REQ | Avoid centralizing sensitive raw audit data unnecessarily; represent structural conclusions and provenance instead. |

---

## Appendix B — illustrative local dossier (the spec must be able to emit this exact object)

| ID | Type | Obligation |
|---|---|---|
| OL-B-01 | FIELD | `jurisdiction`: name, state. |
| OL-B-02 | FIELD | `organizations[]`. |
| OL-B-03 | FIELD | `deployments[]`: technology, vendor, status, contracted_quantity, portal_reported_quantity, osm_mapped_quantity. |
| OL-B-04 | FIELD | `contracts[]`: signed, expires, amount, evidence. |
| OL-B-05 | FIELD | `configuration.retention`: value, observed_at, source. |
| OL-B-06 | FIELD | `sharing`: outgoing_configured, incoming_configured, national_search_observed. |
| OL-B-07 | FIELD | `usage`: searches_last_30d, source, richer_audit_coverage_through, source_project. |
| OL-B-08 | FIELD | `physical_assets`: confirmed_mapped, unknown_operator_near_jurisdiction. |
| OL-B-09 | FIELD | `policies.immigration_enforcement`: written_policy, configuration_evidence (may be `unknown`). |
| OL-B-10 | FIELD | `accountability_events[]`: type, date. |
| OL-B-11 | FIELD | `research_gaps[]`: e.g. locate/verify unmapped units; obtain current SharedNetworks.csv; obtain current organization and network audit; reconcile contract vs portal units; determine whether inactive cameras were removed or retained. |
| OL-B-12 | REQ | "This kind of object is what the ecosystem currently cannot produce from one place." |

---

## Appendix C — illustrative surveillance pathways (all three must be representable and traversable)

| ID | Type | Obligation |
|---|---|---|
| OL-C-01 | EXAMPLE | Privately owned camera —owned_by→ Business —streams_via→ Axon Fusus —accessible_by→ Municipal RTCC —operated_by→ Police Department —participates_in→ Regional Fusion Center. |
| OL-C-02 | EXAMPLE | Roadside ALPR —operated_by→ Police Department —stores_in→ Vendor ALPR network —configured_share_to→ {Neighboring PD, State Police, Federal/task-force organization}. |
| OL-C-03 | EXAMPLE | Police Department —subscribes_to→ Commercial location-data product —sourced_from→ Broker/ad-tech ecosystem. |
| OL-C-04 | PURPOSE | The public-interest question is not "where is the sensor?" but "what chain of institutions and systems turns an observation into searchable power?" That is the graph's ultimate object of study. |

---

## Coverage ledger (filled by the gap-analysis pass)

Every id above must be marked with the spec section discharging it and the disposition:
`VERBATIM-PRESERVED` | `DEEPENED` | `CORRECTED` | `EXTENDED`. Any id without a
discharging section is a **gap** and must be closed before the spec is considered done.
