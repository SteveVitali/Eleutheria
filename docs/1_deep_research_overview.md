# Surveillance Infrastructure Graph
## Landscape Research, Project Definition, and Research Brief for a Downstream Technical Design Agent

**Research date:** 2026-08-20  
**Status:** Second-pass landscape synthesis and high-level project specification  
**Intended audience:** A subsequent deep-research / systems-design agent that will turn this document into a coding-agent-ready technical design and implementation specification.

---

# Executive summary

There is no authoritative public database of surveillance infrastructure in the United States, and no existing project currently solves the full problem we care about.

What exists instead is a surprisingly rich but fragmented ecosystem of projects, datasets, public-records archives, maps, vendor transparency pages, advocacy groups, investigative journalism, government procurement records, and field-observation systems. Different projects answer different questions:

- **Where is a physical surveillance device?**
- **Which organization owns or operates it?**
- **Which surveillance technology has a given agency adopted?**
- **Which vendor and product are involved?**
- **What did the deployment cost, and under what contract?**
- **How many devices were purchased or reported?**
- **What is the system configured to retain, search, or share?**
- **Which other organizations can access the data?**
- **Which organizations actually searched the data?**
- **For what stated reasons?**
- **What policies and legal restrictions govern the system?**
- **Has the deployment been suspended, canceled, replaced, challenged, or litigated?**
- **What documented abuses, false stops, security failures, or policy controversies have occurred?**
- **How does one deployment connect to broader regional or national surveillance networks?**

Today, these questions are answered by different systems.

For automated license plate readers (ALPRs), especially Flock Safety, the ecosystem is unusually developed:

- **OpenStreetMap (OSM)** is emerging as the best global commons for exact, field-observed physical surveillance hardware.
- **DeFlock** provides the most important specialized contribution and visualization interface for ALPR locations while writing observations into OSM rather than creating an isolated proprietary database.
- **Eyes on Flock** discovers Flock Transparency Portals, aggregates their changing statistics and sharing data, and critically preserves rolling public audit information that otherwise disappears.
- **Have I Been Flocked?** aggregates much richer Flock audit logs obtained through public-records requests, normalizes them, deduplicates overlapping records, performs officer/name resolution, and analyzes actual search behavior and network use.
- **ALPR Watch** demonstrates a reproducible public-records-to-SQL pipeline and publishes code, source records, normalized data, and exploratory analysis.
- **EFF's Atlas of Surveillance** remains the strongest broad U.S. dataset describing which law-enforcement agencies deploy which surveillance technologies.
- **EFF and MuckRock's earlier Data Driven projects** document Vigilant/Motorola ALPR networks and data-sharing behavior, showing that the problem predates Flock and cannot be modeled as vendor-specific.
- **ALPR Accountability Atlas** captures a different dimension: incidents, alleged abuses, court cases, regulatory decisions, policy changes, and local actions with explicit evidence labeling.
- **Flock Finder** and **Flock-You** explore radio-based detection and discovery of possible Flock devices, useful as lead-generation mechanisms but not as authoritative device identification.
- **Drivers Against Flock** consumes OSM device data for privacy-oriented routing, demonstrating the value of a stable common device layer and the importance of not duplicating OSM.
- **FlockReporter and many local DeFlock / Eyes Off organizations** form a growing decentralized research and advocacy network that creates public records, verifies hardware, identifies local policies, and discovers deployment changes.
- **MuckRock** and other document repositories are not just secondary resources: they are part of the primary-evidence substrate from which several surveillance datasets are constructed.

Beyond ALPRs, the landscape becomes even more fragmented:

- EFF's Atlas and Data Library incorporate or point to datasets on facial recognition, cell-site simulators, drones, mobile-device forensic tools, body cameras, electronic monitoring, ALPRs, Ring partnerships, and other technologies.
- **Axon Fusus / Community Connect** illustrates the rapidly growing problem of privately owned cameras becoming accessible to police through real-time crime-center platforms.
- **ShotSpotter/SoundThinking** has had sensor-location data exposed through investigative reporting.
- Historical and specialized datasets exist for **Clearview AI**, **Cellebrite and other mobile forensic tools**, **cell-site simulators**, **Vigilant Solutions**, public-safety drones, and other surveillance systems.
- Outside the United States, **OpenStreetMap**, **Surveillance under Surveillance**, **PanoptiCity**, **Technopolice**, and related European mapping communities demonstrate that the physical-device layer can be global, while policy, procurement, organizational, and legal layers need jurisdiction-specific adapters.

The opportunity is therefore **not** to build another surveillance map.

The project should build an **open, source-auditable, temporally aware surveillance infrastructure knowledge graph** that reconciles these fragmented datasets without attempting to replace the projects that already do individual parts well.

Its defining purpose should be:

> **To make the structure of surveillance infrastructure legible: what exists, where it exists, who controls it, who can access it, how it is connected, what capabilities it provides, what rules govern it, how those facts changed over time, and exactly what evidence supports every claim.**

The graph should be **vendor-agnostic**, **technology-agnostic**, **source-preserving**, **temporal**, **explicit about uncertainty**, and **designed for federation rather than appropriation**.

The core intellectual shift is this:

> A surveillance device is not the fundamental unit of surveillance infrastructure.  
> A **relationship among organizations, technologies, capabilities, physical assets, datasets, policies, and access rights** is.

A fixed Flock camera is one manifestation. A patrol-car ALPR is another. A Fusus integration exposing 5,000 private cameras to a real-time crime center is another. A Clearview license is a surveillance deployment without a roadside device. A Fog Reveal subscription exposes location histories without any locally owned sensor at all. A camera owned by a shopping center but searchable by a police department introduces ownership and access as separate relationships. A canceled Flock contract followed by an Axon replacement is not the disappearance of surveillance but a change in implementation.

The graph therefore needs to represent at least:

- organizations;
- organizational aliases and hierarchies;
- vendors;
- products and platforms;
- technologies and capabilities;
- deployments;
- physical devices/assets;
- contracts and procurements;
- data systems;
- access/sharing relationships;
- usage/search observations or aggregate usage metrics;
- configuration states;
- policies;
- laws and regulations;
- incidents and accountability events;
- source documents;
- source claims;
- provenance;
- temporal validity;
- confidence / evidentiary status;
- reconciliation links to upstream datasets.

The project's greatest value will come not from owning the largest raw dataset, but from **joining evidence that currently cannot be joined**.

A journalist should be able to begin with a city and traverse:

`city -> police agency -> Flock deployment -> contract -> 42 contracted cameras -> 31 field-observed OSM devices -> 38 currently reported portal cameras -> sharing relationships -> actual network searches -> retention settings -> policy -> related litigation -> replacement vendor`

A researcher should be able to ask:

> Which U.S. agencies operate ALPRs, share data outside their state, have retention periods over 30 days, and have documented immigration-related searches?

An advocate should be able to ask:

> Which municipalities are considering renewal in the next six months, how many cameras are physically mapped, what the current sharing network looks like, and which source documents would be useful at the next public meeting?

A systems researcher should be able to ask:

> Which vendors increasingly occupy the same integration layer as Flock, and where are cities replacing one vendor with another rather than reducing surveillance capability?

This document maps the ecosystem and defines how the proposed project should relate to it.

---

# 1. The project thesis

## 1.1 The real object is infrastructure, not cameras

A naïve surveillance map treats the world as points:

```text
camera
  latitude
  longitude
  manufacturer
```

That representation is useful but inadequate.

Modern surveillance systems are networked sociotechnical infrastructure. Their power is generated through combinations of:

- sensor density;
- historical retention;
- cross-jurisdictional sharing;
- centralized search;
- automated alerts;
- integration with other databases;
- private-public access relationships;
- analytics;
- identity resolution;
- institutional policy;
- legal permissibility;
- operator behavior.

For example, two jurisdictions with twenty cameras each may have radically different surveillance capabilities if:

- one retains data for seven days and does not share it;
- the other retains data for a year, participates in nationwide lookup, feeds an RTCC, receives private-camera streams, uses federal hotlists, and permits broad search.

Counting cameras alone obscures the difference.

The project must model **surveillance power as a graph of capabilities and access**, not merely a geography of sensors.

---

## 1.2 The right design principle is federation

Several existing projects are already excellent at their chosen tasks.

We should not:

- fork DeFlock's camera database into an independent competing dataset;
- ask users to report the same camera twice;
- replicate EFF's volunteer research workflow;
- re-host Have I Been Flocked's plate-level search tool;
- scrape normalized data while discarding their provenance;
- present ourselves as the authoritative replacement for existing civil-society projects.

Instead:

1. preserve upstream identifiers;
2. ingest or reference upstream datasets where legally and technically permissible;
3. contribute corrections upstream when possible;
4. attach our own derived reconciliation claims separately;
5. make provenance visible;
6. expose missing links and contradictions;
7. generate research tasks that improve upstream sources as well as our graph.

The project should become a **coordination and reconciliation layer** across a pluralistic ecosystem.

---

# 2. The existing ecosystem: a functional map

The clearest way to understand the landscape is to separate projects by the question they answer.

## Layer A — physical infrastructure

### OpenStreetMap

**Role:** global geographic commons for physical surveillance infrastructure.

OpenStreetMap supports `man_made=surveillance` and associated surveillance tags. Surveillance objects can carry information such as:

- surveillance type;
- zone;
- camera type;
- direction;
- operator;
- manufacturer;
- mounting;
- ALPR classification.

OSM matters because it provides:

- stable geographic primitives;
- edit history;
- contributor infrastructure;
- global coverage;
- machine-readable extraction;
- a mature collaborative mapping community;
- interoperability with Overpass and downstream GIS systems.

Most importantly, it provides a neutral substrate that is not owned by one surveillance-specific activist project.

**Strategic conclusion:** exact physical-device observations should normally live in OSM first.

**Important licensing issue:** OSM data is distributed under the Open Database License (ODbL). A downstream technical design must carefully determine whether a combined database becomes a Derivative Database, a Collective Database, or can maintain OSM-derived material as a legally separable layer. The project should not casually merge OSM data into a differently licensed monolithic database without legal review.

Source:
- OpenStreetMap copyright/license: https://www.openstreetmap.org/copyright
- OSM surveillance tagging: https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance

---

### DeFlock

**Role:** specialized ALPR discovery, mapping, education, and contribution interface.

DeFlock's most important design decision is that it uses the OpenStreetMap commons instead of constructing an isolated proprietary camera database. Its web/mobile tools make it easier for people to:

- identify ALPR hardware;
- see known nearby devices;
- report devices;
- add manufacturer/operator information;
- contribute field observations.

This gives DeFlock a powerful relationship to our project:

> DeFlock is an upstream field-observation system, not a dataset we should replace.

A related open pipeline, `deflock-data`, demonstrates extracting ALPR nodes from OSM and producing downstream GeoJSON/vector-tile artifacts.

**What our graph should preserve:**

- OSM element ID;
- OSM version;
- observation/update timestamp;
- coordinates;
- surveillance tags;
- manufacturer;
- operator;
- device direction;
- relevant OSM provenance.

**What our graph adds:**

- link device to a deployment;
- link deployment to an agency/private owner;
- link deployment to a contract;
- compare physically observed count with contractual/portal counts;
- represent lifecycle status;
- attach evidence supporting attribution;
- surface unresolved attribution.

Sources:
- https://deflock.org/
- https://github.com/flockhopper3/deflock-data
- https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance

---

### Surveillance under Surveillance

**Role:** global visualization of OSM surveillance-camera data.

Surveillance under Surveillance demonstrates the international reach of OSM's surveillance schema. It renders OSM surveillance infrastructure and is used by surveillance-mapping communities in Europe.

It is valuable to us primarily as evidence that:

1. OSM already has an international surveillance community;
2. our physical-device layer can scale outside the U.S.;
3. we should avoid inventing a U.S.-only device schema.

Source:
- https://sunders.uber.space/

---

### PanoptiCity

**Role:** visualization/analysis of CCTV coverage and fields of view from mapped devices.

PanoptiCity illustrates that physical coordinates can support richer derived analysis than simple markers. Camera orientation and geometry can be transformed into approximations of observed space.

That suggests a useful future distinction in our graph:

- **source facts**: camera exists at coordinate X with direction Y;
- **derived facts**: estimated field of view intersects area Z.

Derived facts must never be confused with source observations.

Source:
- https://panopticity.fr/

---

### Drivers Against Flock

**Role:** consumer application built on the common device layer.

Drivers Against Flock uses OpenStreetMap camera data to provide navigation that can favor routes with fewer known ALPR/surveillance devices. It explicitly states that camera locations come from OSM and that corrections should flow back to OSM.

This is an excellent demonstration of the ecosystem architecture we should encourage:

```text
field observation
      ↓
OpenStreetMap
      ↓
many downstream applications
      ├── DeFlock
      ├── Drivers Against Flock
      ├── research
      └── our graph
```

The graph should make similarly reusable higher-order data available to downstream tools rather than forcing every application to scrape all upstream sources again.

Source:
- https://driversagainstflock.org/

---

## Layer B — official/vendor-generated deployment and sharing metadata

### Flock Transparency Portals

**Role:** opt-in, agency-specific vendor-hosted snapshots of system configuration, usage metrics, and sharing.

A current Flock portal can expose fields including:

- agency name;
- last-updated date;
- data-retention period;
- total cameras;
- vehicles detected during a recent interval;
- searches;
- hotlists;
- hotlist hits;
- organizations granted access;
- organizations sharing data inward;
- stated acceptable/prohibited uses;
- public search-audit CSV;
- links or text for agency policies.

The portals are extremely valuable because they are first-party evidence. But they are not authoritative in the sense of being complete:

- agencies can lack portals;
- portals are not published through a convenient master directory;
- values change;
- a portal may disappear;
- public audit logs are limited and redacted;
- statistics are rolling rather than immutable historical data.

This source therefore demands **snapshotting and temporal preservation**.

Examples observed in the second research pass show why the source must be modeled rather than blindly trusted. Portal retention periods vary dramatically, and portal records can include active/inactive organizations, bidirectional sharing relationships, private organizations, federal organizations, universities, and other nontraditional entities.

Sources:
- https://transparency.flocksafety.com/
- Example: https://transparency.flocksafety.com/green-brook-twp-nj-pd
- Example: https://transparency.flocksafety.com/hagerstown-md-pd

---

### Eyes on Flock

**Role:** Flock Transparency Portal discovery, aggregation, historical preservation, and sharing-network analysis.

This project was underweighted in the first research pass and is a key player.

The developer describes discovering transparency portals through brute-force enumeration over possible locality/agency URL slugs because Flock does not provide a complete public directory.

Eyes on Flock provides or has described providing:

- searchable table of discovered portals;
- aggregated statistics across portals;
- reported camera totals;
- hotlist-hit statistics;
- search-reason aggregation;
- maps of organizations listed in portal sharing sections;
- historical retention of public search-audit entries that would otherwise roll off Flock's roughly 30-day public window.

This is not merely an alternate UI over Flock portals.

Its important contributions are:

1. **portal discovery**;
2. **temporal archiving**;
3. **normalization**;
4. **cross-portal aggregation**;
5. **sharing-relationship extraction**.

Those functions make Eyes on Flock a natural upstream partner or data source.

**Strategic implication:** our project should not independently build a competing portal-discovery crawler without first determining whether Eyes on Flock can expose an API, data export, archive, or collaboration interface. If independent archival is still needed for reproducibility, we should coordinate conventions and preserve cross-identifiers.

Sources:
- https://eyesonflock.com/
- Project author's description: https://www.reddit.com/r/FlockSurveillance/comments/1ra26qw/eyes_on_flock_aggregating_flock_safety/

---

### Independent transparency-portal archival projects

A second ecosystem of smaller tools has emerged around scraping Flock portal pages. For example, a California sharing visualization described taking:

- PDF snapshots;
- raw HTML snapshots;
- normalized JSON;
- daily portal captures;
- sharing edges;
- inferred agencies when the target agency lacked its own visible portal.

This is important because it reveals a recurring research need: **archival truth**.

A future graph must distinguish:

```text
what portal says now
what portal said on date T
what our parser extracted on date T
what later evidence says about the same state
```

The raw source snapshot should remain immutable.

Example discussion/repository reference:
- https://www.reddit.com/r/FlockSurveillance/comments/1slvs6a/visualization_of_flock_sharing_in_calfiornia/

---

## Layer C — actual usage and audit behavior

### Have I Been Flocked?

**Role:** large-scale public-records aggregation and analysis of Flock search activity.

This is one of the most consequential projects in the ecosystem.

As of this research pass, the site reports hundreds of millions of known Flock searches and millions of plates represented in obtained public records. More important than the headline volume is the methodology.

Have I Been Flocked distinguishes:

#### Organization Audit

Searches performed by users belonging to the organization whose audit was exported.

#### Network Audit

Searches from other organizations that touched/shared against the audited organization's data. Fields can include:

- organization;
- camera count;
- time frame;
- reason;
- case number;
- filters;
- search timestamp;
- search type;
- text prompt;
- moderation information.

#### Portal/Public Audit

The more heavily redacted, limited public audit associated with transparency portals.

#### SharedNetworks.csv

A configuration snapshot expressing sharing edges in both directions.

#### Event logs

Administrative changes including:

- hotlist operations;
- network sharing changes;
- user/role changes;
- camera renaming;
- live-stream activity.

#### Configuration screenshots

Settings describing:

- sharing behavior;
- live-stream permissions;
- retention;
- third-party integrations;
- statewide/nationwide access;
- policies and feature controls.

The project also documents:

- officer/name resolution;
- police rosters;
- duplicate handling;
- source-agency provenance;
- anomaly detection;
- records-request templates.

This is effectively a specialized surveillance-data research laboratory.

**Strategic implication:** we should treat HIBF as an authoritative upstream specialist for Flock *usage observations*, while our graph should represent aggregate and structural conclusions rather than reproduce an unnecessary searchable corpus of sensitive plate-level records.

Sources:
- https://haveibeenflocked.com/
- https://haveibeenflocked.com/about
- https://haveibeenflocked.com/about/audit-logs

---

### ALPR Watch

**Role:** reproducible FOIA aggregation and analysis pipeline.

ALPR Watch is technically important because it shows a clean pipeline:

```text
MuckRock requests
    ↓
raw documents
    ↓
file classification
    ↓
CSV/XLSX/ZIP parsing
    ↓
normalized SQL
    ↓
derived/coded fields
    ↓
Superset/dashboard analysis
```

Its 2025 Flock FOIA work explicitly:

- pulls records through the MuckRock API;
- identifies Organization Audit and Network Audit exports;
- supports heterogeneous archive/file formats;
- preserves raw values;
- creates normalized/derived columns;
- makes reason-code mappings inspectable;
- publishes analysis code;
- links back to raw records.

ALPR Watch also demonstrates a crucial epistemic principle: user-entered “Reason” fields are messy, inconsistent free text. Normalization requires judgment. Derived categorization must therefore remain inspectable and reversible.

This should influence our graph's architecture:

> Never overwrite source text with normalized semantics.

Store:

```text
raw_claim
normalized_claim
normalization_method
normalization_version
review_status
```

Source:
- https://alprwatch.org/news/2025-07-28_flock_foia/

---

### flock.ajith.fyi

**Role:** visual network analysis of Flock surveillance relationships.

This project has been cited in academic surveillance research as a visualization of Flock network access and audit information. It demonstrates the communicative value of showing surveillance as **edges across jurisdictions**, not merely points.

Even if the project is not our primary canonical source, its conceptual contribution is important: network topology is a first-class public-interest visualization.

Referenced in:
- Torin Monahan, “Grounding the Flock: Confronting Police Surveillance of Mobilities” (2026): https://journals.sagepub.com/doi/10.1177/20501579261453519

---

## Layer D — agency-level surveillance adoption

### EFF Atlas of Surveillance

**Role:** broadest mature U.S. open-source intelligence database of police surveillance technology deployment.

The Atlas records surveillance technology associated with agencies and jurisdictions. Its methodology combines:

- OSINT;
- news reporting;
- government documents;
- meeting minutes;
- press releases;
- procurement leads;
- crowdsourcing;
- staff/intern review;
- imported specialist datasets.

As of August 12, 2026, the Atlas methodology page explicitly states that its data is not a complete inventory. That limitation is essential: the Atlas documents claims supported by evidence; absence from the Atlas is not evidence of absence.

The Atlas's deepest contribution to our project is not only its rows. It provides a mature taxonomy and a precedent for evidence-reviewed surveillance research.

Its Data Library is also a map of earlier specialist projects, including:

- Atlas Border Communities;
- Who Has Your Face?;
- public-safety drones;
- historical Ring/Neighbors partnerships;
- cell-site simulator datasets;
- AI Global Surveillance Index;
- federally funded body cameras;
- wiretap reports;
- Aaron Swartz Day Police Surveillance Project;
- California ALPR survey data;
- Vigilant ALPR Data Driven datasets;
- Upturn's mobile-device forensic-tool research;
- Clearview AI usage data;
- electronic monitoring;
- state policy datasets;
- other specialized collections.

**Strategic implication:** Atlas should seed our agency/deployment layer, but we should preserve its source attribution and allow subsequent evidence to supersede or temporally qualify a deployment.

Sources:
- https://www.atlasofsurveillance.org/
- https://www.atlasofsurveillance.org/methodology
- https://www.atlasofsurveillance.org/data-library

---

### EFF Data Driven / Data Driven 2

**Role:** historical and still-relevant ALPR sharing research, especially Vigilant Solutions.

These projects matter because they prove that cross-agency ALPR networks are not unique to Flock.

EFF and MuckRock's earlier public-records work documented:

- billions of plate observations;
- hundreds of participating agencies;
- very high proportions of non-watchlisted scans;
- sharing relationships through Vigilant's LEARN ecosystem.

A Flock-centric graph would therefore mis-model the problem.

The graph should allow:

```text
ALPR capability
    ├── Flock Safety
    ├── Motorola/Vigilant
    ├── Rekor
    ├── Axon
    ├── Genetec
    └── other/local systems
```

and should separately model integration between them when evidence exists.

Sources:
- https://www.eff.org/deeplinks/2018/11/eff-and-muckrock-release-records-and-data-200-law-enforcement-agencies-automated
- Atlas Data Library entry: https://www.atlasofsurveillance.org/data-library

---

## Layer E — accountability, incidents, litigation, and policy change

### ALPR Accountability Atlas

**Role:** structured, source-auditable catalog of ALPR-related incidents and policy/accountability events.

As of the research pass, ALPR Accountability Atlas described itself as a living source-auditable map and made available:

- issue-record CSV;
- source-index CSV;
- GeoJSON;
- data dictionary;
- research archive.

Its records distinguish categories such as:

- local regulation/action;
- litigation;
- wrongful stop/false alert;
- immigration/data sharing;
- security/product issues;
- stakeholder/company context.

Most importantly, the project explicitly distinguishes:

- allegations;
- findings;
- court actions;
- policy decisions;
- company statements.

That is a model we should adopt.

A graph should not flatten:

> “X happened”

when the actual evidence says:

> “A plaintiff alleged X in a pending lawsuit.”

Those are different epistemic states.

Source:
- https://alpratlas.org/

---

### ALPR Abuse Library / Kansas Watch

**Role:** editorially reviewed index of published reporting documenting ALPR harms and abuses.

This project reflects another useful pattern: not every useful source should be normalized immediately into “facts.” A curated source index can be valuable by itself.

The graph should be capable of linking an incident node to:

- primary record;
- court record;
- agency statement;
- vendor statement;
- investigative article;
- advocacy analysis.

Source referenced by HIBF:
- https://library.kansas.watch/

Project announcement:
- https://www.reddit.com/r/FlockSurveillance/comments/1rsedl3/building_a_collaborative_alpr_abuse_documentation/

---

### ACLU Get the Flock Out

**Role:** advocacy toolkit and local organizing guidance.

This is not primarily a dataset. But it demonstrates an important downstream user of our graph: community advocates trying to understand a local deployment quickly enough to intervene in policy and contracting.

The graph should therefore eventually support “local dossier” outputs:

- known deployments;
- vendor;
- contract;
- renewal date;
- camera count;
- mapped device count;
- sharing relationships;
- retention;
- audit activity;
- governing policy;
- upcoming decision points;
- documented incidents.

Source:
- https://www.aclu.org/get-the-flock-out-toolkit

---

## Layer F — records and primary evidence

### MuckRock

**Role:** public-records request infrastructure and primary-source repository.

MuckRock is foundational to this ecosystem because many surveillance datasets ultimately originate in records requests.

For our purposes MuckRock should be modeled not just as a URL but as:

```text
records_request
requesting_party
target_agency
request_text
date
response_status
released_documents
document_metadata
```

When possible, derived claims should link to the exact released document rather than merely a downstream article.

ALPR Watch already demonstrates automated ingestion from MuckRock's API.

Sources:
- https://www.muckrock.com/
- ALPR Watch methodology: https://alprwatch.org/news/2025-07-28_flock_foia/

---

### DocumentCloud and investigative archives

Journalists and nonprofit researchers frequently publish source documents in document repositories such as DocumentCloud.

The graph should treat these as **evidence stores**, not merely citation URLs. Useful metadata includes:

- document title;
- issuing organization;
- document date;
- acquisition method;
- page range;
- checksum;
- archive URL;
- parser/OCR status;
- relevant extracted claims.

The same principle applies to city agenda packets, procurement PDFs, contracts, invoices, policy manuals, court filings, and released spreadsheets.

---

### Government procurement and meeting records

EFF's Atlas methodology notes that many research leads originate in government procurement data, including GovSpend.

Other useful public or semi-public source classes include:

- city/county procurement portals;
- state procurement systems;
- council/board agenda systems;
- budgets;
- warrants;
- grants;
- USAspending.gov for federal spending;
- SAM.gov for federal contracting context;
- state auditor surveys;
- public meeting minutes;
- police policies;
- public-records portals.

These sources are structurally important because they frequently identify surveillance **before a device is mapped in the field**.

---

## Layer G — lead generation and field detection

### Flock Finder

**Role:** probable-device discovery via WiGLE radio observations and known Flock-associated hardware prefixes.

Flock Finder queries WiGLE observations for matching OUIs and publishes suspected Flock device locations.

This can generate leads at a scale physical volunteers cannot match, but it must not be conflated with verified hardware.

Reasons include:

- WiGLE coverage is opportunistic;
- observations can be stale;
- an OUI indicates vendor-associated hardware, not necessarily a currently installed ALPR at that exact point;
- radio-location estimates can be imprecise;
- devices may move;
- hardware identifiers can create false positives.

The appropriate flow is:

```text
radio observation
      ↓
candidate surveillance asset
      ↓
field verification / public record / imagery
      ↓
confirmed physical device
      ↓
OSM
```

Source:
- https://github.com/simeononsecurity/flock-finder

---

### Flock-You

**Role:** local hardware experimentation for detecting Flock-associated radio signatures.

Flock-You is an ESP32-oriented project discussed in the DeFlock/FlockSurveillance community for detecting possible nearby Flock-associated MAC/radio activity.

Its importance to our system is not that we need to ingest every detection. Instead it reveals a possible future **observation protocol**:

```text
observation
observer/source type = passive radio
timestamp
location estimate
identifier prefix
confidence
verification status
```

A downstream design must include safeguards against publishing sensitive private-residence hypotheses or turning low-confidence radio observations into accusations.

Source:
- https://github.com/colonelpanichacks/flock-you

---

# 3. The decentralized local research ecosystem

A significant part of surveillance transparency is being generated by local organizations rather than national institutions.

Examples surfaced during research include:

- DeFlock Atlanta;
- DeFlock Idaho;
- DeFlock Birmingham;
- DeFlock Joplin;
- DeFlock Lynnwood;
- DeFlock Olympia;
- DeFlock Redmond;
- DeFlock Tucson;
- DeFlock Vegas;
- Eyes Off Colorado;
- Eyes Off Indiana;
- Eyes Off Cedar Rapids;
- Live Free VA;
- local Monterey Park activists;
- local county/city privacy organizations.

FlockReporter maintains a directory of multiple such efforts.

Source:
- https://flockreporter.org/

These groups matter for three reasons.

## 3.1 They generate evidence

Local researchers file records requests, attend meetings, photograph devices, collect contracts, discover private deployments, and verify whether systems are actually active.

## 3.2 They detect state changes earlier than national databases

A local organization may know that:

- a camera was physically removed yesterday;
- a contract renewal is on next week's agenda;
- sharing was disabled after controversy;
- a department has switched vendors;
- a portal disappeared;
- a private institution participates in the network.

National datasets inevitably lag.

## 3.3 They are ideal consumers of reconciliation tasks

Our graph can create structured “research gaps” such as:

> **Cedar Rapids**
> - Contract indicates 78 cameras.
> - OSM currently has 61 probable ALPR devices.
> - transparency portal reports 75.
> - 14 OSM devices have unknown operator.
> - latest contract amendment is missing.
> - sharing snapshot is 94 days old.

That turns the graph into a **research coordination system**, not merely a passive database.

---

# 4. Beyond Flock: the broader surveillance stack

The project must resist the temptation to let Flock define the ontology.

## 4.1 Axon and Fusus

Current reporting shows municipalities leaving Flock while replacing it with Axon or other vendors rather than abandoning ALPR capability.

Axon's Fusus platform is particularly important because it is an integration layer for real-time crime centers and can connect:

- public cameras;
- private cameras;
- body-camera live streams;
- ALPRs;
- drones;
- other sensor/dispatch systems.

Axon Community Connect provides public-facing community portals through which private organizations and individuals can register or share cameras. A recent independent enumeration reported more than 850,000 privately owned cameras represented across just 324 publicly listed communities. This figure is crowdsourced research and should be independently verified before being treated as canonical, but it demonstrates the scale of the category.

This breaks a simplistic ownership model:

```text
camera owner != data controller != police accessor != platform provider
```

The graph must represent all four separately.

Sources:
- Current vendor-replacement reporting: https://www.theguardian.com/us-news/2026/aug/20/flock-cameras-surveillance
- Axon Community Connect: https://axoncommunityconnect.com/communities/
- Independent enumeration discussion: https://www.reddit.com/r/privacy/comments/1vp6yy3/i_found_over_850000_private_cameras_accessible/

---

## 4.2 Motorola / Vigilant

Vigilant Solutions' historical ALPR network, now associated with Motorola Solutions, demonstrates:

- vendor-network sharing;
- private ALPR data;
- large-scale retention;
- cross-agency lookup;
- bulk location-history search.

EFF's Data Driven work should be a priority ingestion source for the first vendor-neutral ALPR model.

---

## 4.3 Rekor

Rekor provides ALPR/smart-roadway systems and appears in contemporary municipal deployments. The graph should distinguish:

- device manufacturer;
- service vendor;
- data platform;
- agency operator;
- local-storage vs vendor-cloud architecture where evidence permits.

Vendor-level assumptions should never substitute for deployment-specific evidence.

---

## 4.4 Genetec

Genetec provides video-management and ALPR technology. In many deployments, the relevant fact may be a software integration rather than an easily recognized roadside hardware model.

Again, **capability** must be first-class.

---

## 4.5 ShotSpotter / SoundThinking

Investigative reporting has previously published a leaked dataset containing more than 25,000 ShotSpotter sensor locations.

This illustrates a category that OSM can theoretically represent but that has different source and sensitivity concerns:

- acoustic sensor;
- installed location;
- service area;
- operating agency;
- vendor;
- historical status.

The graph should allow physical acoustic sensors without forcing them into a “camera” abstraction.

Source:
- WIRED, “Here Are the Secret Locations of ShotSpotter Gunfire Sensors”: https://www.wired.com/story/shotspotter-secret-sensor-locations-leak

---

## 4.6 Cell-site simulators

The ACLU historically maintained a map of known law-enforcement agencies possessing cell-site simulators (Stingrays/IMSI catchers).

A cell-site simulator may have no persistent public coordinate. Its meaningful graph representation is:

```text
agency
  └── deploys
        └── cell-site simulator capability
```

with equipment, procurement, warrant policy, and known use represented separately.

Source:
- https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices

---

## 4.7 Facial recognition

Important specialist datasets include:

- EFF's Who Has Your Face?;
- BuzzFeed's historical Clearview AI usage table;
- Atlas facial-recognition deployments;
- country-level facial-recognition datasets.

This domain introduces a different object: **reference databases**.

A useful graph may need to represent:

```text
agency
  └── can query
        └── facial recognition system
              └── searches against
                    └── image/reference database
```

The database itself is infrastructure even if there is no local sensor.

EFF Data Library:
- https://www.atlasofsurveillance.org/data-library

---

## 4.8 Mobile-device forensic tools

Upturn's *Mass Extraction* research documented law-enforcement acquisition of tools such as Cellebrite.

This again reinforces that a surveillance infrastructure graph must include **investigative extraction capabilities**, not just persistent sensors.

Source via EFF Data Library:
- https://www.atlasofsurveillance.org/data-library

---

## 4.9 Commercial location-data systems

Systems such as Fog Reveal expose location histories assembled from commercially acquired mobile advertising/location data.

Their architecture can look like:

```text
mobile apps
   ↓
ad-tech / location brokers
   ↓
commercial data vendor
   ↓
law-enforcement investigative platform
   ↓
agency
```

This may be one of the most important long-term extensions because it reveals that surveillance infrastructure increasingly consists of **data-access relationships rather than locally deployed hardware**.

A graph that cannot represent this has modeled the twentieth-century surveillance state, not the contemporary one.

---

## 4.10 Real-time crime centers and integration platforms

RTCCs increasingly form a convergence layer combining:

- cameras;
- ALPR;
- CAD/911;
- gunshot detection;
- drones;
- private-camera feeds;
- body cameras;
- databases;
- analytics.

The project should therefore represent **integration hubs** as systems/deployments that consume other systems.

The future graph should support:

```text
Fusus Deployment
    ├── integrates -> camera registry
    ├── integrates -> Flock ALPR
    ├── integrates -> city CCTV
    ├── integrates -> drone program
    └── accessed_by -> RTCC
```

This is more revealing than five disconnected “technology adoption” rows.

---

# 5. International landscape

The U.S. should be the initial focus because:

- public-records law creates rich primary evidence;
- EFF and MuckRock provide mature infrastructure;
- the Flock ecosystem is currently unusually observable;
- agency identifiers and jurisdiction structures are tractable;
- there is immediate public-interest demand.

But the data model should be international from the beginning.

## 5.1 OpenStreetMap as global physical-device substrate

OSM already supports surveillance nodes globally. This is the strongest reason not to create a bespoke U.S. coordinate schema.

## 5.2 France and Belgium: Technopolice

La Quadrature du Net's Technopolice ecosystem has documented and mapped surveillance technologies in French cities, including:

- CCTV;
- intelligent video;
- facial recognition experiments;
- drones;
- thermal cameras;
- acoustic sensors;
- “safe city” systems.

Technopolice communities have explicitly discussed using OSM rather than creating isolated surveillance-camera databases.

A historical French `sous-surveillance.net` dataset of roughly 12,000 cameras was imported into OpenStreetMap for verification, demonstrating a concrete path from local activist database to common geographic substrate.

Sources:
- https://technopolice.fr/
- https://technopolice.fr/blog/mise-a-jour-de-la-technocarte/
- Mapping discussion: https://forum.technopolice.fr/topic/405/cartographier-la-surveillance

## 5.3 Other global datasets

EFF's Data Library points to international resources including:

- AI Global Surveillance Index;
- Facial Recognition World Map;
- Mapping China's Tech Giants.

These datasets operate mostly at country/vendor/deployment level rather than individual physical-device level.

The graph should support them later as coarser claims with explicit granularity.

---

# 6. What is missing from the ecosystem

After the second research pass, the central gap is clearer.

There are already systems for:

- physical camera mapping;
- agency surveillance-adoption mapping;
- transparency-portal aggregation;
- Flock audit-log analysis;
- public-records acquisition;
- incident/accountability indexing;
- policy advocacy;
- avoidance routing.

What is missing is a **general reconciliation layer across them**.

Specifically, no major project appears to provide all of the following simultaneously.

## 6.1 Canonical entity resolution

The same organization appears under many names:

```text
Los Angeles Police Department
LAPD
Los Angeles CA PD
City of Los Angeles Police Dept.
Los Angeles Police Dept
```

Flock organization identifiers may not match:

- EFF agency names;
- ORI codes;
- OSM operator values;
- procurement vendor/customer names;
- MuckRock jurisdiction records;
- police rosters;
- court documents.

Entity resolution is therefore not ancillary. It is foundational infrastructure.

---

## 6.2 Cross-source reconciliation

Existing systems generally show what their own source says.

The missing system should be able to say:

> Contract executed 2025-03-14 specifies 30 Falcon cameras.

> Transparency Portal reported 28 active cameras on 2026-07-01.

> OSM contains 24 field-observed Flock ALPR nodes assigned to this agency as of 2026-08-20.

> Three additional candidate devices are unmapped to an operator.

> One local news story reports two relocations in June.

> Therefore, the graph currently estimates 28 active contracted devices, 24 physically mapped, with 4 unresolved.

This is **reconciliation**, not aggregation.

---

## 6.3 Temporal history

Surveillance datasets often overwrite the present.

But these questions require history:

- When was the contract signed?
- When did deployment begin?
- When did sharing turn on?
- When was ICE access disabled?
- When did the city cancel?
- When were physical devices removed?
- When did another vendor replace them?

The graph must be fundamentally temporal.

A relationship should rarely be modeled as:

```text
A shares with B = true
```

Instead:

```text
A shared with B
valid_from = ?
valid_to = ?
observed_at = 2026-07-14
source = portal snapshot
```

---

## 6.4 Claim-level provenance

Most databases attach a citation to a row.

We need finer granularity.

A source might support:

- vendor identity;
- camera count;
- contract date;

while not supporting:

- exact coordinates;
- current active status;
- retention period.

Therefore provenance should attach to **claims or assertions**, not only entities.

---

## 6.5 Contradiction as a first-class state

Suppose:

- vendor portal says 20 cameras;
- contract says 25;
- city presentation says 22;
- OSM has 18.

The system should not choose one silently.

It should preserve:

```text
claim A: 20
claim B: 25
claim C: 22
observation count: 18

resolution:
  active_device_count = 20
  confidence = medium
  rationale = portal is most recent operational source
```

The disagreement itself is useful research information.

---

## 6.6 Network topology across vendors

Existing Flock visualizations show Flock-sharing relationships.

But modern policing increasingly integrates:

- Flock;
- Fusus;
- state fusion centers;
- federal systems;
- Vigilant/Motorola;
- private cameras;
- commercial data providers;
- RTCCs.

The graph should eventually reveal **multi-vendor surveillance pathways**.

---

## 6.7 Procurement-to-deployment lifecycle

A surveillance system has lifecycle states:

```text
proposed
pilot
approved
contracted
installation
active
expanded
restricted
suspended
nonrenewed
canceled
decommissioning
removed
replaced
```

Most existing datasets flatten this into “uses technology.”

This is increasingly dangerous because current reporting shows cities canceling Flock while adopting replacement systems. Without lifecycle and replacement edges, analyses can falsely count these events as surveillance reductions.

---

# 7. Proposed project definition

## Working definition

**Surveillance Infrastructure Graph (SIG)** is an open-source, public-interest knowledge system that continuously reconciles evidence about surveillance technologies, deployments, physical infrastructure, organizational access, procurement, policy, usage, and accountability events.

It does not attempt to observe private individuals.

It observes **institutions and infrastructure**.

---

## 7.1 Primary goals

### Goal 1 — Discover

Identify surveillance deployments and infrastructure from heterogeneous public sources.

### Goal 2 — Reconcile

Resolve duplicate organizations, devices, deployments, vendors, and claims across datasets.

### Goal 3 — Preserve provenance

Make every material fact traceable to source evidence.

### Goal 4 — Preserve time

Record when a claim was true, when it was observed, and when it changed.

### Goal 5 — Expose relationships

Represent ownership, operation, access, data sharing, integration, procurement, and replacement as graph edges.

### Goal 6 — Quantify incompleteness

Make coverage gaps visible rather than implying completeness.

### Goal 7 — Coordinate research

Turn contradictions and missing evidence into structured research tasks.

### Goal 8 — Serve downstream users

Provide stable, open exports/API primitives for:

- journalists;
- researchers;
- civil-liberties organizations;
- local communities;
- policy analysts;
- mapping applications;
- watchdog projects.

---

## 7.2 Explicit non-goals

The project should **not**:

- create a searchable database of ordinary people's movements;
- re-publish plate-level audit data merely because it is public;
- track individual law-enforcement officers unless necessary for a documented accountability claim and consistent with a carefully developed policy;
- infer private individuals' identities from cameras or radio observations;
- encourage trespass, vandalism, interference, or destruction of surveillance equipment;
- publish speculative exact locations of sensitive private residences based only on weak RF observations;
- replace OpenStreetMap as the physical-device editing system;
- replace EFF's Atlas as the primary broad crowdsourced adoption-research project;
- replace HIBF as the specialist audit-log analysis project;
- represent itself as exhaustive or “authoritative” when the evidence is incomplete.

---

# 8. Conceptual graph model

The downstream agent should refine this, but the following ontology should guide the technical design.

## 8.1 Organization

Examples:

- municipality;
- police department;
- sheriff;
- state police;
- federal agency;
- university police;
- school district;
- HOA;
- corporation;
- private security organization;
- hospital;
- vendor;
- fusion center;
- nonprofit.

Fields/concepts:

```text
Organization
  id
  canonical_name
  aliases[]
  organization_type
  parent_organization
  jurisdiction
  ORI / government identifiers
  addresses
  source identifiers
  valid_from / valid_to
```

---

## 8.2 Vendor

A vendor is an organization but should have domain-specific relationships.

```text
Vendor
  └── offers Product
  └── supplies Deployment
  └── acquires Vendor
```

Example:

```text
Axon
  acquired -> Fusus
```

Temporal corporate history matters because product names and ownership change.

---

## 8.3 Product

Examples:

- Flock Falcon;
- Flock platform;
- Vigilant LEARN;
- Axon Fusus;
- Clearview AI;
- Fog Reveal;
- Cellebrite UFED;
- ShotSpotter.

A Product is not equivalent to a Technology.

---

## 8.4 Technology / capability

Examples:

- automated license plate recognition;
- facial recognition;
- fixed CCTV;
- private camera federation;
- acoustic gunshot detection;
- cell-site simulation;
- mobile-device extraction;
- drone surveillance;
- real-time video;
- geolocation-data search;
- social-media monitoring;
- predictive policing.

This abstraction allows vendor-independent queries.

---

## 8.5 Deployment

A Deployment means an organization has implemented or contracted for some product/capability.

```text
Deployment
  organization
  vendor
  product
  technologies[]
  status
  proposed_at
  approved_at
  contracted_at
  active_from
  inactive_at
  quantity_claims[]
  jurisdiction
```

The deployment is the bridge between organizational adoption and individual devices.

---

## 8.6 PhysicalAsset

Examples:

- fixed ALPR;
- mobile ALPR;
- CCTV camera;
- gunshot sensor;
- drone;
- camera trailer;
- RTCC facility.

```text
PhysicalAsset
  asset_type
  geometry
  mobility
  manufacturer
  model
  operator
  owner
  deployment
  first_observed
  last_observed
  upstream_ids[]
```

Coordinates must not be required for movable assets.

---

## 8.7 DataSystem

Some surveillance infrastructure is better modeled as a data system:

- ALPR cloud dataset;
- image database;
- commercial location dataset;
- RTCC platform;
- integrated investigative platform.

```text
DataSystem
  operator
  vendor
  product
  data_types
  retention
```

---

## 8.8 AccessRelationship

This is one of the most important graph edges.

```text
Organization A
   can_access
DataSystem / Deployment / Organization B data
```

Attributes:

```text
scope
direction
automatic/manual
nationwide/statewide/local
valid_from
valid_to
observed_at
source
```

Do not reduce all Flock network relationships to “shares_with.” Direction matters.

---

## 8.9 IntegrationRelationship

Example:

```text
Axon Fusus deployment
  integrates
Flock deployment
```

or:

```text
RTCC
  consumes_feed_from
private camera registry
```

---

## 8.10 Contract / Procurement

```text
Contract
  buyer
  seller
  amount
  signed_date
  start_date
  end_date
  renewal_options
  products
  quantities
  document
```

A contract can produce or modify a deployment.

---

## 8.11 Policy

Examples:

- retention policy;
- acceptable use;
- warrant requirement;
- immigration restriction;
- reproductive-health restriction;
- audit requirement;
- external sharing policy.

A policy must be scoped:

```text
Policy
  applies_to Organization / Deployment / Product
  effective period
  policy_type
  text/source
```

---

## 8.12 ConfigurationState

Policies and actual software configuration are different.

HIBF's documentation makes this distinction extremely important.

Example:

```text
written policy:
  no immigration enforcement

software configuration:
  immigration hotlist enabled
```

The graph should be able to represent that contradiction without editorially collapsing it.

---

## 8.13 UsageObservation / UsageAggregate

The core graph should prefer aggregate or structural observations where possible.

Examples:

```text
SearchAggregate
  searching_org
  source_org
  period
  count
  search_scope
  reason_category
```

Raw sensitive audit data can remain in specialist repositories.

---

## 8.14 Incident / AccountabilityEvent

Examples:

- lawsuit;
- false stop;
- alleged stalking misuse;
- immigration-search controversy;
- policy violation;
- data breach;
- city moratorium;
- contract cancellation;
- public hearing;
- security finding.

Fields should include epistemic state:

```text
event_type
alleged / confirmed / adjudicated / policy_action / vendor_statement
date
organizations
deployments
sources
```

---

## 8.15 EvidenceArtifact

```text
EvidenceArtifact
  url
  source_type
  publisher
  title
  date
  retrieved_at
  checksum
  archived_copy
  license
  primary_or_secondary
```

Examples:

- contract PDF;
- council minutes;
- audit CSV;
- portal snapshot;
- OSM observation;
- news article;
- court filing;
- agency policy.

---

## 8.16 Claim

This may be the most important object in the entire system.

```text
Claim
  subject
  predicate
  object/value
  valid_time
  observed_time
  source
  extraction_method
  confidence
  review_status
```

Example:

```text
subject: Deployment ABC
predicate: active_camera_count
value: 38
valid_time: 2026-07-23
source: Flock portal snapshot XYZ
```

Another source may produce a competing claim.

---

# 9. Epistemic architecture

The project should be designed around the difference between:

- fact;
- observation;
- claim;
- inference;
- derived metric;
- unresolved contradiction.

## 9.1 Suggested source hierarchy

Not a rigid ranking, but a useful default:

### Tier A — direct primary operational evidence

- exported audit logs;
- configuration exports/screenshots;
- signed contracts;
- invoices;
- official device inventories;
- government datasets;
- court records;
- direct field observation.

### Tier B — first-party public statements

- transparency portals;
- official press releases;
- council presentations;
- vendor statements;
- agency policy pages.

### Tier C — reviewed specialist datasets

- EFF Atlas;
- Have I Been Flocked processed data;
- ALPR Accountability Atlas;
- Upturn;
- other transparent research datasets.

### Tier D — high-quality investigative reporting

Useful for claims whose primary source is inaccessible and for contextual/accountability events.

### Tier E — community reports

- local activist databases;
- user submissions;
- inferred locations.

### Tier F — heuristic discovery

- RF/OUI matches;
- automated web extraction with unresolved entity matching;
- model-generated candidate matches.

Lower tier does not mean “bad.” It means the claim needs clearer uncertainty.

---

## 9.2 Never collapse observation time and validity time

Example:

A portal captured on August 20 may say:

> 25 cameras.

That proves:

> On August 20, the portal reported 25 cameras.

It does not necessarily prove:

> 25 cameras were physically installed on August 20.

This distinction should be encoded.

---

## 9.3 Confidence should be explainable

Avoid opaque “87% confidence” values unless probability is actually calibrated.

Prefer labels with reasons:

```text
confirmed
strongly supported
probable
unverified
contradicted
historical
```

and machine-readable evidence counts.

---

## 9.4 Negative claims need special treatment

Absence from a dataset means little.

Examples:

- no OSM camera does not mean no camera exists;
- no Atlas row does not mean an agency lacks the technology;
- no transparency portal does not mean the agency is not a Flock customer;
- no HIBF audit data does not mean an agency never searched the system.

The UI/API should make coverage explicit.

---

# 10. Source ingestion strategy

The downstream design agent should develop exact connectors, but the high-level order should be:

## Phase 1A — canonical entities

Build a durable organization/vendor/jurisdiction registry.

Potential identity aids:

- Atlas agency names;
- ORI identifiers where available;
- Census geographic identifiers;
- government domains;
- OSM operator strings;
- Flock portal slugs;
- MuckRock jurisdiction IDs.

Without this, every subsequent integration becomes duplicate-heavy.

---

## Phase 1B — OpenStreetMap / DeFlock physical ALPR layer

Ingest ALPR/surveillance nodes while retaining:

- OSM ID;
- version;
- tags;
- coordinates;
- edit timestamp;
- attribution.

Do not make this the canonical editing database.

---

## Phase 1C — EFF Atlas

Import surveillance deployments and their source references.

Do not overwrite Atlas taxonomy blindly. Create mappings between:

- Atlas technology categories;
- our normalized technology ontology.

---

## Phase 1D — Flock portal ecosystem

Prefer collaboration/API/export from Eyes on Flock if feasible.

Capture:

- portal identity;
- portal snapshots;
- camera count;
- retention;
- usage metrics;
- outward/inward sharing;
- hotlists;
- policies;
- public audits.

Create temporal observations rather than current-state overwrite.

---

## Phase 1E — HIBF / ALPR Watch structural data

Do not initially ingest every plate/search record.

Ingest or derive:

- organizations observed;
- audit source coverage;
- sharing edges;
- search counts;
- search-scope metrics;
- reason-category aggregates;
- configuration claims;
- source-document links.

Keep specialist raw-data custody where it already exists.

---

## Phase 1F — contracts / MuckRock / public records

Start with records already linked by upstream projects.

Then expand acquisition through:

- MuckRock;
- government portals;
- procurement systems;
- city agenda systems.

---

## Phase 1G — accountability events

Ingest or cross-reference:

- ALPR Accountability Atlas;
- ALPR Abuse Library;
- court cases;
- policy actions;
- contract cancellations/replacements.

---

# 11. Reconciliation workflows

The project becomes valuable when it detects disagreement.

## 11.1 Camera-count reconciliation

Inputs:

```text
contract quantity
portal reported count
OSM observed count
agency public statement
invoice quantity
local records inventory
```

Output:

```text
reported_active_count
physically_mapped_count
contracted_count
unresolved_delta
evidence
```

Do not produce a false single “true count” where evidence is ambiguous.

---

## 11.2 Device attribution

Example:

```text
OSM Flock camera
  operator = unknown
  location = within jurisdiction X

deployment:
  agency X has 20 contracted devices

candidate relation:
  asset operated_by agency X

status:
  probable, not confirmed
```

A field mapper or public-records researcher can resolve it.

---

## 11.3 Sharing-edge reconciliation

Potential sources:

- portal “sharing with”;
- portal “receiving from”;
- SharedNetworks.csv;
- network-audit actual queries;
- policy statements.

These encode different concepts:

```text
configured access
actual use
declared policy
```

Never merge them into one edge.

---

## 11.4 Deployment lifecycle reconciliation

Example:

```text
2025-01 proposed
2025-03 contract signed
2025-06 20 devices active
2026-04 sharing restricted
2026-07 nonrenewal announced
2026-08 cameras still physically present
2026-09 Axon replacement scheduled
```

This is the historical record users actually need.

---

# 12. Research task generation

One of the most distinctive project features should be automatic creation of **research leads**.

Examples:

### Missing physical devices

> Portal reports 40 cameras; 27 are mapped in OSM.

Task:
- locate/verify remaining devices.

### Missing contract

> Atlas and portal confirm deployment; no procurement evidence linked.

Task:
- find contract/invoice/council approval.

### Conflicting retention

> agency policy says 30 days; portal reports 365 days.

Task:
- obtain current configuration or clarification.

### Stale evidence

> latest deployment source is 30 months old.

Task:
- verify active status.

### Orphaned device

> OSM camera has manufacturer but no operator.

Task:
- establish operator via public records / signage / field evidence.

### New sharing node

> network logs contain an organization absent from organization registry.

Task:
- resolve identity and jurisdiction.

### Vendor replacement

> Flock contract terminated; procurement record shows Axon ALPR.

Task:
- link `replaced_by` lifecycle edge rather than mark surveillance removed.

This turns the system into a living research network.

---

# 13. Ethical and security constraints

The project itself should not become a surveillance system.

## 13.1 Observe institutions, not individuals

A bright-line default:

> The graph tracks public or institutionally relevant surveillance infrastructure and organizational behavior, not ordinary people's movements.

Plate-level search data should generally remain with projects explicitly designed and governed to handle it, such as HIBF.

---

## 13.2 Minimize personal data

Avoid storing:

- license plates;
- private-person names;
- individual travel histories;
- residential associations;
- officer personal addresses;
- unrelated personal identifiers.

Where an accountability event requires a named public official or officer, apply a clear public-interest standard.

---

## 13.3 Treat exact coordinates contextually

Exact locations of visible public-road surveillance hardware are commonly mapped in OSM and DeFlock.

But not all sensor-location data has the same risk profile.

A publication policy should distinguish:

- publicly visible roadside device;
- hidden sensor on public infrastructure;
- private-residence candidate;
- confidential facility;
- mobile asset.

---

## 13.4 Preserve source without overexposing sensitive contents

A public-record file can contain data that is legally public but ethically sensitive.

The system may need:

- raw private archival storage;
- redacted public derivative;
- source hash;
- restricted access;
- metadata-only public representation.

---

## 13.5 No operational interference

The project should explicitly support:

- research;
- journalism;
- policy analysis;
- lawful field observation;
- public-records work.

It should not provide instructions for damaging, disabling, tampering with, or evading lawful enforcement in the commission of wrongdoing.

---

# 14. Licensing and data-governance problem

This deserves serious downstream legal/technical research.

## 14.1 OSM's ODbL is consequential

OSM is share-alike database data.

If we create a derived database by combining substantial OSM content with proprietary or incompatibly licensed datasets, distribution obligations may attach.

Possible design strategies include:

### Strategy A — keep OSM as a separable external layer

Store OSM identifiers and fetch/map data separately.

### Strategy B — publish OSM-derived physical-asset table under ODbL

Keep other evidence graph tables under a separate compatible/open license.

### Strategy C — license the entire public data graph compatibly

This may simplify openness but could complicate integration with other datasets.

The final design needs actual legal analysis, not assumptions.

---

## 14.2 Source licenses should be first-class metadata

Every imported dataset should have:

```text
license
attribution requirement
redistribution permission
derivative permission
source terms
retrieval date
```

Do not discover after launch that a key dataset cannot legally be redistributed.

---

## 14.3 Open source code is not enough

The project only fulfills its mission if the **data outputs** are meaningfully reusable.

Ideally provide:

- open code;
- open schemas;
- downloadable datasets where licensing permits;
- documented APIs;
- provenance;
- versioned snapshots;
- reproducible ingestion.

---

# 15. Product surfaces the graph should eventually enable

This memo is not prescribing implementation, but the project definition should anticipate downstream uses.

## 15.1 Local surveillance dossier

Input:

```text
city / county / agency
```

Output:

- technologies deployed;
- vendors;
- status;
- device counts;
- physical map;
- contracts;
- annual cost;
- retention;
- data sharing;
- inbound/outbound access;
- audit coverage;
- policy;
- incidents/litigation;
- historical timeline;
- missing evidence.

This may be the single most powerful public-facing primitive.

---

## 15.2 Infrastructure map

Not just dots.

Layers:

- physical devices;
- organizational deployments;
- RTCCs;
- data-sharing edges;
- private-public camera networks;
- service areas;
- proposed/active/decommissioned status.

---

## 15.3 Surveillance network explorer

Graph view:

```text
Who can access whose data?
Which organizations serve as hubs?
How does a local camera become accessible nationally?
Which federal/private actors appear most often?
```

---

## 15.4 Procurement / renewal watch

For every contract:

- expiration;
- renewal window;
- council approval;
- replacement procurement.

This transforms passive historical transparency into actionable civic timing.

---

## 15.5 Evidence viewer

Every claim should be expandable:

```text
Claim
Evidence
Source excerpt / page
Original document
Extraction method
Review status
Conflicting claims
History
```

---

## 15.6 Research queue

Allow contributors to pick structured unresolved tasks rather than asking them to “research surveillance.”

---

## 15.7 Machine-readable API / exports

The graph's long-term public value depends on enabling others to build:

- academic analysis;
- newsroom tools;
- local dashboards;
- route/privacy applications;
- policy trackers;
- visualizations.

---

# 16. Recommended project boundaries for an initial release

The project can become impossibly broad if it tries to model every surveillance technology immediately.

The strongest initial wedge is:

> **U.S. ALPR infrastructure, modeled completely enough that the ontology naturally generalizes to broader surveillance technology.**

Why this wedge works:

1. rich OSM device data;
2. DeFlock contributor ecosystem;
3. Flock portal data;
4. Eyes on Flock;
5. HIBF;
6. ALPR Watch;
7. historical Vigilant/EFF data;
8. active public-records movement;
9. current procurement activity;
10. multiple vendors;
11. strong network-sharing semantics;
12. device + software + policy + access all present.

Initial technology scope should include at least:

- Flock;
- Motorola/Vigilant;
- Rekor;
- Axon ALPR where data exists;
- Genetec ALPR;
- unknown/other ALPR.

But the schema should support the non-ALPR extensions from day one.

---

# 17. A staged project plan

## Stage 0 — ecosystem coordination

Before writing ingestion code:

1. contact / investigate collaboration interfaces with:
   - DeFlock;
   - Eyes on Flock;
   - Have I Been Flocked;
   - ALPR Watch;
   - EFF Atlas;
   - ALPR Accountability Atlas;
   - relevant local groups;
2. determine data licenses;
3. identify APIs/exports;
4. avoid duplicating expensive work;
5. define attribution and contribution-back mechanisms.

---

## Stage 1 — canonical graph nucleus

Build:

- organizations;
- jurisdictions;
- vendors;
- products;
- technologies;
- deployments;
- source/evidence;
- claims;
- temporal assertions.

Seed with:

- Atlas;
- OSM ALPR;
- Flock portal organizations.

Goal:

> reliably answer “who, what technology, where, according to which evidence?”

---

## Stage 2 — ALPR reconciliation

Add:

- camera counts;
- device attribution;
- contracts;
- lifecycle;
- sharing edges;
- portal snapshots;
- public-record links.

Goal:

> reliably answer “what is deployed and how do the independent sources agree/disagree?”

---

## Stage 3 — usage/network layer

Integrate aggregate structural information from:

- HIBF;
- ALPR Watch;
- Flock network configuration;
- historical Vigilant sharing.

Goal:

> answer “who can access whose data, and who actually does?”

---

## Stage 4 — accountability and policy

Add:

- policy;
- laws;
- incidents;
- litigation;
- restrictions;
- cancellations;
- replacements.

Goal:

> show the governance and consequence layer.

---

## Stage 5 — broader surveillance technologies

Prioritize technologies with strong existing datasets:

1. private-camera federation / Fusus;
2. facial recognition;
3. cell-site simulators;
4. mobile-device forensic tools;
5. gunshot detection;
6. drones;
7. commercial location-data access;
8. RTCC integration systems.

---

## Stage 6 — international expansion

Start with:

- global OSM physical surveillance;
- French/Belgian Technopolice data;
- country-level surveillance datasets;
- jurisdiction-specific organizational adapters.

---

# 18. How the project should interact with existing projects

| Existing project | Their strongest role | Our relationship |
|---|---|---|
| OpenStreetMap | Global physical-device commons | Upstream canonical device geography |
| DeFlock | ALPR discovery/reporting UX | Direct contributors upstream to OSM; link/reconcile |
| Eyes on Flock | Portal discovery, aggregation, archival history | Partner/ingest/reference portal temporal layer |
| Have I Been Flocked | Audit-log corpus and behavioral analysis | Partner/reference structural aggregates and evidence |
| ALPR Watch | Reproducible FOIA normalization | Reuse methods/code/data where compatible |
| EFF Atlas | Agency surveillance adoption taxonomy | Primary seed for deployment layer |
| EFF Data Driven | Vigilant ALPR sharing history | Vendor-neutral ALPR network source |
| ALPR Accountability Atlas | Incident/legal/accountability records | Link/integrate events, preserve evidence semantics |
| MuckRock | Public-records workflow and source files | Primary evidence substrate |
| Drivers Against Flock | Privacy routing over OSM | Downstream consumer; do not compete |
| Flock Finder | RF-derived candidate discovery | Lead generation only |
| Flock-You | Local RF detection | Observation lead, never automatic confirmation |
| FlockReporter | Local ecosystem directory/coordination | Discover collaborators and local evidence |
| Local DeFlock/Eyes Off groups | Field research and civic action | Contributors, validators, consumers |
| Technopolice | European surveillance mapping/research | International model and future data source |
| Surveillance under Surveillance | Global OSM visualization | Downstream/peer visualization |
| PanoptiCity | Coverage/field-of-view analysis | Possible downstream analytical consumer |

---

# 19. Data-quality principles the downstream system must preserve

## 19.1 Provenance over convenience

Never store a “fact” if we can store the evidence-backed claim that generated it.

## 19.2 Raw before normalized

Preserve source form.

## 19.3 Time before overwrite

Append state transitions.

## 19.4 Uncertainty before false precision

Unknown is legitimate.

## 19.5 Federation before duplication

Improve upstream commons.

## 19.6 Organization identity before graph analytics

Bad entity resolution makes every network statistic misleading.

## 19.7 Capability before vendor

Vendors change. Capabilities persist.

## 19.8 Ownership is not access

Model separately:

- owner;
- operator;
- controller;
- platform provider;
- accessor;
- data recipient.

## 19.9 Configured access is not actual use

Model both.

## 19.10 Policy is not configuration

Model both.

## 19.11 Contracted is not installed

Model lifecycle.

## 19.12 Installed is not active

Preserve last observation.

---

# 20. Questions the final technical-research/design pass must answer

The downstream agent should treat these as mandatory research tasks.

## Data access

1. Does Eyes on Flock expose an API, downloadable database, or archival repository?
2. Can we obtain its historical portal snapshots directly?
3. What are its reuse/license terms?
4. What exact exports does HIBF make available, under what license and update cadence?
5. What APIs/exports does ALPR Watch publish?
6. What stable machine-readable interfaces does EFF Atlas currently expose beyond CSV?
7. What are MuckRock API constraints and redistribution terms?
8. What data can be pulled from DocumentCloud programmatically?

## Identity

9. What is the best public canonical U.S. law-enforcement agency identifier?
10. How complete are ORI codes, and how should non-law-enforcement entities be represented?
11. Which public datasets provide canonical municipal/county/state identifiers?
12. How should private organizations in Flock/Fusus networks be disambiguated?

## Licensing

13. Precisely how does ODbL apply to a graph that joins OSM device records to non-OSM entities?
14. Can an OSM physical-assets table remain logically/licensably separate?
15. What licenses govern Atlas, HIBF, Eyes on Flock, ALPR Watch, and Accountability Atlas data?
16. What source documents may be archived vs merely linked?

## Temporal data

17. What snapshot cadence is justified for transparency portals?
18. How should deleted portals and inactive organizations be preserved?
19. How should OSM edit history be represented without replicating the entire OSM history database?

## Graph storage

20. Should canonical storage be relational/PostGIS with graph projections, a property graph, RDF, or hybrid?
21. Which model best supports claim-level provenance and bitemporal history?
22. How should high-volume audit aggregates remain separate from the main knowledge graph?

## Ingestion

23. Which connectors can be incremental?
24. Which sources require scraping?
25. How should source snapshots be content-addressed?
26. What parser architecture handles PDFs, HTML, CSV, XLSX, ZIP, JSON, meeting systems, and contracts?

## Entity resolution

27. Which matches can be deterministic?
28. Where should fuzzy/model-assisted matching generate review queues rather than writes?
29. How should aliases and mergers be represented?

## Safety/privacy

30. What public-data publication policy should govern plate numbers, personal names, private-residence detections, and other sensitive content?
31. Which raw public records should be stored privately but represented publicly only by metadata?
32. How should takedown/correction requests work?

## Collaboration

33. How can corrections flow upstream to OSM/DeFlock?
34. Could Atlas consume deployment corrections?
35. Can research tasks link directly to HIBF/MuckRock workflows?
36. Could local groups claim geographic research queues?
37. What stable IDs would allow other projects to link back to graph entities?

---

# 21. Priority source registry

The downstream research agent should individually inspect these rather than rely only on this synthesis.

## Core physical infrastructure

- OpenStreetMap surveillance tagging  
  https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance
- OpenStreetMap license  
  https://www.openstreetmap.org/copyright
- DeFlock  
  https://deflock.org/
- DeFlock data pipeline  
  https://github.com/flockhopper3/deflock-data
- Surveillance under Surveillance  
  https://sunders.uber.space/
- PanoptiCity  
  https://panopticity.fr/
- Drivers Against Flock  
  https://driversagainstflock.org/

## Flock-specific transparency / network / usage

- Eyes on Flock  
  https://eyesonflock.com/
- Eyes on Flock project description  
  https://www.reddit.com/r/FlockSurveillance/comments/1ra26qw/eyes_on_flock_aggregating_flock_safety/
- Have I Been Flocked  
  https://haveibeenflocked.com/
- HIBF methodology hub  
  https://haveibeenflocked.com/about
- HIBF audit-log guide  
  https://haveibeenflocked.com/about/audit-logs
- ALPR Watch  
  https://alprwatch.org/
- ALPR Watch Flock FOIA methodology  
  https://alprwatch.org/news/2025-07-28_flock_foia/
- Flock Transparency Portals  
  https://transparency.flocksafety.com/

## Broad U.S. surveillance infrastructure

- EFF Atlas of Surveillance  
  https://www.atlasofsurveillance.org/
- Atlas methodology  
  https://www.atlasofsurveillance.org/methodology
- Atlas Data Library  
  https://www.atlasofsurveillance.org/data-library
- EFF Street-Level Surveillance  
  https://www.eff.org/issues/street-level-surveillance

## Accountability / incidents

- ALPR Accountability Atlas  
  https://alpratlas.org/
- ALPR Abuse Library  
  https://library.kansas.watch/
- ACLU Get the Flock Out  
  https://www.aclu.org/get-the-flock-out-toolkit

## Public records

- MuckRock  
  https://www.muckrock.com/
- DocumentCloud  
  https://www.documentcloud.org/

## Discovery / RF

- Flock Finder  
  https://github.com/simeononsecurity/flock-finder
- Flock-You  
  https://github.com/colonelpanichacks/flock-you

## Community ecosystem

- FlockReporter  
  https://flockreporter.org/

## International

- Technopolice  
  https://technopolice.fr/
- Technopolice mapping discussion  
  https://forum.technopolice.fr/topic/405/cartographier-la-surveillance

## Historical/specialist datasets to inspect through EFF Data Library

- Vigilant / Data Driven ALPR data
- California ALPR surveys
- Who Has Your Face?
- Clearview AI usage table
- cell-site simulator datasets
- public-safety drone datasets
- Mass Extraction / mobile-device forensic tools
- electronic monitoring
- AI Global Surveillance Index
- Ring/Neighbors historical partnerships

Index:
- https://www.atlasofsurveillance.org/data-library

---

# 22. Critical conclusions

## 22.1 There is no master surveillance database because the problem is inherently multi-layered

The absence of a single authoritative dataset is not merely an organizational failure.

Different facts are generated by different systems:

- physical location by field observation;
- purchase by procurement;
- contractual quantity by contract;
- active quantity by operator/vendor;
- sharing by configuration;
- actual use by audit log;
- legality by statute/court;
- policy by agency documents;
- abuse by investigation/litigation;
- replacement by future procurement.

The correct architecture therefore cannot have a single “source of truth.”

It needs **source-auditable reconciliation**.

---

## 22.2 The graph should become authoritative about provenance, not omniscient about reality

The strongest claim the project can responsibly make is not:

> “We know every surveillance device.”

It is:

> “For every claim we publish, we can show where it came from, when it was observed, how it was normalized, what contradicts it, and how confident we are.”

That is a much more defensible form of authority.

---

## 22.3 Flock is the ideal starting laboratory but the wrong permanent boundary

Flock currently has an unusually observable ecosystem:

- cameras;
- portals;
- audits;
- sharing;
- public records;
- activist mapping;
- investigative reporting;
- controversy;
- replacement pressure.

That makes it ideal for developing the graph.

But vendor substitution is already occurring.

The lasting ontology must be:

```text
surveillance capability
      ↓
deployment
      ↓
assets / data / access
```

not:

```text
Flock camera
```

---

## 22.4 The most important graph edges may eventually matter more than the nodes

A map of 100,000 cameras is visually powerful.

But the more consequential questions are:

- Who can search them?
- Who can receive alerts?
- Which private cameras feed police?
- Which local system is connected to which national system?
- Which vendor integrates which data?
- Which agencies are high-centrality sharing hubs?
- Which federal actors gain access through local relationships?

The project should therefore treat network analytics as central, not ornamental.

---

## 22.5 Temporal reconciliation is a major differentiator

The ecosystem is moving quickly.

As of August 2026, cities are:

- canceling Flock;
- leaving hardware physically installed during transitions;
- reducing retention;
- changing sharing;
- adopting safeguards;
- moving to competing vendors.

A static adoption map can easily produce the wrong political conclusion.

A temporal graph can distinguish:

```text
surveillance removed
```

from:

```text
vendor replaced
```

and:

```text
contract canceled
```

from:

```text
devices still deployed
```

This is a core research capability.

---

## 22.6 The system should create leverage for existing public-interest work

Its success should be measured partly by whether it makes other projects stronger.

Examples:

- DeFlock receives better operator attribution.
- Atlas receives newly documented deployments.
- HIBF receives more targeted records submissions.
- local groups learn exactly which records are missing.
- journalists locate primary evidence faster.
- researchers can reproduce national analyses without rebuilding entity resolution from scratch.

The project becomes connective infrastructure for a movement of independent researchers.

---

# 23. One-sentence specification

> **Build an open, vendor-agnostic, temporally versioned, claim-level-provenance knowledge graph of surveillance infrastructure that federates existing public-interest datasets and primary records to show what surveillance capabilities exist, where and by whom they are deployed, how they are connected and accessed, what rules and contracts govern them, how they are actually used when evidence exists, how they change over time, and exactly which sources support or contradict every material claim.**

---

# 24. Guidance to the downstream deep-research / technical-design agent

Do not treat this document as the final implementation specification.

Your task is to convert its research thesis into an implementable architecture.

In doing so:

1. **Re-verify the ecosystem yourself.** Projects are moving rapidly.
2. **Inspect primary repositories, exports, licenses, schemas, and APIs.**
3. **Contact assumptions with evidence.** Do not assume data access because a website exists.
4. **Solve entity identity before designing impressive graph visualizations.**
5. **Design provenance and temporal semantics before writing ingestion adapters.**
6. **Treat OSM licensing as a first-order architectural constraint.**
7. **Prefer federation to copying.**
8. **Preserve upstream IDs.**
9. **Separate raw evidence, extracted claims, normalized claims, and derived conclusions.**
10. **Keep sensitive person-level surveillance data outside the main graph unless a compelling, reviewed public-interest use requires it.**
11. **Make contradictions inspectable.**
12. **Design contributor workflows around concrete reconciliation tasks.**
13. **Make the first release narrowly excellent at U.S. ALPR infrastructure while keeping the ontology general.**
14. **Model private-public surveillance relationships from the start.**
15. **Model software/data access systems that have no fixed physical sensor.**
16. **Model replacement and lifecycle so that vendor churn is not mistaken for surveillance reduction.**
17. **Produce stable public exports and APIs wherever licensing permits.**
18. **Make the final system reproducible enough that a journalist can defend a graph claim by tracing it back to evidence.**

The defining standard should be:

> **No unexplained dots. No unexplained edges. No silent overwrites. No synthetic certainty.**

Every node should have identity.  
Every edge should have semantics.  
Every state should have time.  
Every claim should have evidence.  
Every inference should say that it is an inference.  
Every contradiction should remain visible until resolved.

That is the project.

---

# Appendix A — Research findings that materially changed the first-pass conception

The first pass correctly identified DeFlock/OSM, EFF Atlas, HIBF, MuckRock, ALPR Watch, Flock portals, the Accountability Atlas, and international OSM surveillance mapping.

The second pass changed the conception in several important ways.

## A.1 Eyes on Flock is foundational, not peripheral

Its role is not merely “another Flock website.” Its brute-force portal discovery and historical preservation solve two infrastructural gaps:

- undocumented portal enumeration;
- loss of rolling portal audit history.

This makes it a core prospective collaborator.

## A.2 The local research network is itself infrastructure

Local DeFlock/Eyes Off groups generate data national systems cannot generate centrally. The graph should organize and return useful research tasks to them.

## A.3 Vendor replacement is already occurring

A Flock-specific system would become obsolete precisely when it became successful. The goal must be surveillance-capability transparency.

## A.4 Private-camera federation is enormous

Fusus/Community Connect demonstrates that counting government-owned cameras severely understates police-accessible visual infrastructure.

## A.5 The fundamental unit is an access relationship

Hardware is increasingly only one endpoint in a larger information network.

## A.6 The graph needs a lifecycle model

“Uses Flock” is too crude for rapidly changing deployments.

## A.7 The graph needs claim-level provenance

Row-level citations are inadequate for reconciling contradictory quantitative and temporal claims.

## A.8 The project should avoid centralizing sensitive raw audit data unnecessarily

Specialized projects already handle it. Our graph can represent structural conclusions and provenance without building a second repository of ordinary people's plate searches.

---

# Appendix B — Illustrative local dossier

The following is conceptual, not a statement about a specific real municipality.

```yaml
jurisdiction:
  name: Example City
  state: XX

organizations:
  - Example City Police Department

deployments:
  - technology: ALPR
    vendor: Flock Safety
    status: active
    contracted_quantity: 42
    portal_reported_quantity: 38
    osm_mapped_quantity: 31

contracts:
  - signed: 2025-04-03
    expires: 2027-04-02
    amount: 126000
    evidence: city-contract.pdf

configuration:
  retention:
    value: 30 days
    observed_at: 2026-07-15
    source: transparency portal

sharing:
  outgoing_configured: 147 organizations
  incoming_configured: 312 organizations
  national_search_observed: true

usage:
  searches_last_30d: 412
  source: transparency portal
  richer_audit_coverage_through: 2026-05-31
  source_project: Have I Been Flocked

physical_assets:
  confirmed_mapped: 31
  unknown_operator_near_jurisdiction: 4

policies:
  immigration_enforcement:
    written_policy: prohibited
    configuration_evidence: unknown

accountability_events:
  - type: public hearing
    date: 2026-06-11
  - type: contract review
    date: 2026-08-04

research_gaps:
  - locate/verify 7+ unmapped contracted/reported units
  - obtain current SharedNetworks.csv
  - obtain current organization and network audit
  - reconcile 42 contract units vs 38 portal units
  - determine whether inactive cameras were removed or retained
```

This kind of object is what the ecosystem currently cannot produce from one place.

---

# Appendix C — Illustrative surveillance pathway

A mature graph should eventually be able to represent:

```text
Privately owned camera
      │ owned_by
      ▼
Business
      │ streams_via
      ▼
Axon Fusus
      │ accessible_by
      ▼
Municipal RTCC
      │ operated_by
      ▼
Police Department
      │ participates_in
      ▼
Regional Fusion Center
```

alongside:

```text
Roadside ALPR
      │ operated_by
      ▼
Police Department
      │ stores_in
      ▼
Vendor ALPR network
      │ configured_share_to
      ├── Neighboring Police Department
      ├── State Police
      └── Federal / task-force organization
```

and:

```text
Police Department
      │ subscribes_to
      ▼
Commercial location-data product
      │ sourced_from
      ▼
Broker / ad-tech ecosystem
```

The public-interest question is not merely *where is the sensor?*

It is:

> **What chain of institutions and systems turns an observation into searchable power?**

That is the graph's ultimate object of study.
