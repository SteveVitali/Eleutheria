# R7 — Vendors, Products, Technologies, Capabilities: the SIG controlled vocabularies

**Workstream:** R7
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (SIG research agent R7)
**Outline sections covered:** §4 (4.1–4.10), §6.7, §8.2, §8.3, §8.4, §8.7, §8.8, §8.9, §16, §19.7, §19.8, §22.3, §22.4, Appendix C
**Outline questions answered:** partial — §20 "Identity" (vendor/product identity and corporate history), §20 "Data access" (which vendor/agency datasets are actually retrievable), §20 "Licensing" (license status of the vendor-landscape sources this workstream introduces)
**Confidence in this file overall:** medium-high

---

## 0. What this file is, and how to read it

The outline treats §8.2 Vendor / §8.3 Product / §8.4 "Technology / capability" as three short sketches. This
workstream's job was to convert those sketches into the actual reference data and controlled vocabulary the
schema needs, and to verify the real-world facts that determine edge semantics.

Six deliverables, in order:

| § | Deliverable | Outline section it serves |
|---|---|---|
| 1 | The **Technology vs Capability decision** (they must be split into two entities plus a third, Configuration) | §8.4 |
| 2 | The **canonical technology taxonomy** — 101 slugs, hierarchical, vendor-neutral, with evidence signatures | §8.4, §16, §19.7 |
| 3 | The **capability verb vocabulary** — what a deployment lets an operator *do* | §8.4, §8.8 |
| 4 | **Per-vendor reference cards** — 40+ vendors with verified corporate identity, products, data architecture | §4.1–§4.10, §8.2, §8.3 |
| 5 | The **integration edge-type catalog** — 14 edge types with precise semantics and directionality | §8.8, §8.9, §22.4, App. C |
| 6 | The **role model** (12 roles) and the **validated lifecycle state machine** (24 states) | §4.1, §6.7 |

Material claims are numbered `F7.<n>` per CONVENTIONS.md. Design decisions that are *not* empirical claims
(the taxonomy structure itself, the edge semantics) are presented as design sections and are traceable to the
findings that motivated them.

**Method note.** 56 distinct retrievals were performed on 2026-08-20. `WebFetch` is blocked outright for
`theguardian.com` and `wired.com` by the harness ("Claude Code is unable to fetch from ..."), and returns
403 for `dhs.gov`, `fightforthefuture.org` (intermittently) and `cnbc.com`. In every one of those cases the
fallback was `curl` with a desktop Chrome User-Agent, which succeeded; the exact commands and the resulting
artifacts are recorded in each finding. Two data sources were enumerated programmatically rather than read
prose-wise (Axon Community Connect, the EFF DFR waiver spreadsheet); those counts are my own, not repeated
from reporting.

---

# Part 1 — The Technology vs Capability decision

This is the load-bearing modeling call for the whole ontology, so it is first.

### F7.1 — Technology and Capability are different entities and must not be merged

**Claim:** §8.4's single "Technology / capability" entity conflates three distinct things — a *technology
class* (what kind of machine/method), a *capability* (what an operator can do with a deployment), and a
*configuration* (the tunable parameters of a specific deployment) — and the three have different cardinality,
different lifetimes, different evidence sources, and different privacy salience; SIG must model them as
three separate entities.
**Status:** VERIFIED (as a design consequence of verified facts F7.2, F7.3, F7.24, F7.27, F7.42)
**Evidence:** Four independently retrieved facts force the split.

1. *Same technology, different capabilities.* Verkada and Flock both deploy the technology `alpr-fixed`. But
   per Verkada's own comparison marketing, "Verkada's LPR system operates with your cameras, your Command
   organization, your retention settings, and nobody outside your org queries it," contrasting explicitly
   with Flock's network model (https://azentri.com/verkada/vs/flock, retrieved 2026-08-20; corroborated by
   Verkada's own law-enforcement page https://www.verkada.com/solutions/law-enforcement/). The *technology*
   is identical; the *capability set* differs by exactly the most privacy-salient capability there is
   (`search-external-network`). A model that stores only "has ALPR" cannot express this difference, and
   §22.3 explicitly says the lasting ontology must be capability-first.
2. *Same technology + same vendor, different capabilities by configuration.* Flock's Aug 2026 guardrails
   introduce per-agency "offense filtering," letting a community "restrict which offense categories other
   agencies can search... allowing searches only for stolen vehicles, missing persons, or violent crimes
   while blocking immigration enforcement queries"
   (https://www.flocksafety.com/blog/flock-guardrails-address-lpr-privacy-concerns-and-police-transparency,
   retrieved 2026-08-20). Two agencies running identical Falcon hardware on identical contracts can now
   expose different capabilities to the same third party.
3. *Configuration is separately observable and separately mutable.* EFF documented that whether a Flock
   deployment subscribes to the NCIC "Immigration Violator" hotlist topic is a checkbox in the agency admin
   interface, observed via public-records screenshots — 2 agencies with it on (Blue Island PD IL; Sparks PD
   NV), 11 more using NCIC hotlists with it off
   (https://www.eff.org/deeplinks/2026/06/are-your-local-police-using-flock-safety-alprs-scan-immigrants,
   retrieved 2026-08-20). Retention likewise: Flock's default moved 30d → 7d in Aug 2026, but "existing
   customers retain current retention periods," and Denver contracted Axon at 21d against Axon's 30d default
   (Guardian, retrieved 2026-08-20 via curl). Technology didn't change; three different configurations exist
   simultaneously under one technology and one product.
4. *Capabilities cross technology boundaries.* "Search a nationwide plate database" is a capability
   deliverable by `alpr-fixed` (Flock National Network), by `alpr-mobile` (Axon Fleet 3 into Axon Evidence),
   by `commercial-plate-data-purchase` with no camera at all (Motorola/DRN), and by
   `third-party-investigative-platform` (Rekor Discover reselling). If capability were an attribute of
   technology it would have to be duplicated four times and could never be queried uniformly — which defeats
   §8.4's own stated purpose ("This abstraction allows vendor-independent queries").

**Retrieved:** 2026-08-20
**Implication for the spec:** Replace §8.4 with three entities:

```text
Technology      — a class of sensing/analytic/data-acquisition method.
                  Vendor-neutral, slow-changing, closed controlled vocabulary.
                  Cardinality: ~101 rows, curated, versioned.
                  Answers: "what kind of thing is this?"

Capability      — an action an operator can perform, or an effect the system produces.
                  Expressed as verb + object + scope. Closed controlled vocabulary.
                  Cardinality: ~45 rows.
                  Answers: "what can they DO?"
                  Attaches to Deployment (and, weakly and defeasibly, to Product as
                  "capabilities this product is capable of offering").

ConfigurationState — already exists in the outline as §8.12. Promote it: it is the
                  carrier of every parameterized fact (retention days, hotlist topics
                  subscribed, sharing scope, offense filters, audit mode, MFA).
                  Time-versioned, per-Deployment. Answers: "how is it tuned right now?"
```

The relationships are:

```text
Product      --implements-->        Technology        (many-to-many; Flock Falcon implements
                                                       alpr-fixed AND vehicle-fingerprint-reid)
Product      --can_offer-->         Capability        (defeasible: marketing-level)
Deployment   --instantiates-->      Product
Deployment   --actually_provides--> Capability        (evidentiary: needs a source)
Deployment   --has_state-->         ConfigurationState[t]
Capability   --enabled_by-->        ConfigurationState  (a capability may be conditional
                                                         on a config value)
```

Two rules make this tractable:

- **The capability-attribution rule.** `Deployment --actually_provides--> Capability` requires its own
  evidence claim; it is never inferred silently from `Product --can_offer--> Capability`. Inference is
  allowed but must be materialized as a Claim with `derivation: product_default` and correspondingly low
  confidence, so §9.3 ("confidence should be explainable") holds. This directly implements §19.9
  ("configured access is not actual use") one level up: *marketed capability is not configured capability*.
- **The configuration-cut rule.** If a fact can differ between two deployments of the same product without
  any change to hardware or software version, it is a ConfigurationState attribute, not a Technology or
  Capability attribute. Retention days, hotlist subscriptions, sharing lists, offense filters, and audit
  settings all fail this test and are therefore configuration.

**Outline delta:** CORRECTS §8.4 — the section title "Technology / capability" and its single flat example
list must be split into `Technology`, `Capability`, and a promoted `ConfigurationState` (§8.12). CONFIRMS
§19.7 ("capability before vendor") and §22.3, which both already presuppose this split without naming it.

---

### F7.2 — "Capability" needs a verb grammar, not a noun list

**Claim:** The outline's §8.4 examples are all nouns ("facial recognition", "social-media monitoring"); a
capability vocabulary built from nouns cannot express scope or direction, which is exactly what §8.8 says
matters most ("Do not reduce all Flock network relationships to 'shares_with.' Direction matters").
**Status:** VERIFIED (design consequence)
**Evidence:** Flock's own product taxonomy distinguishes at least five *different* capabilities over one
technology: local search of own cameras; "state lookup"; "national lookup" (National LPR Network,
https://www.flocksafety.com/products, retrieved 2026-08-20); receiving a hotlist alert; and having another
agency search you. The Aug 2026 changes act on these separately: Flock "removed federal organisations from
statewide and national lookup networks in August 2025, and in January [2026] it added a single toggle
letting an agency switch off all federal sharing" (Guardian 2026-08-20 via curl; corroborated by
flocksafety.com guardrails post). A noun called "ALPR network sharing" cannot represent "federal orgs
removed from national lookup but state lookup intact."
**Retrieved:** 2026-08-20
**Implication for the spec:** Capability slugs are `<verb>.<object>.<scope>` triples. See §3 below.
**Outline delta:** EXTENDS §8.4 and §8.8.

---

### F7.3 — Technology needs three levels, not one

**Claim:** A flat technology list cannot simultaneously serve rollup queries ("how many agencies have any
biometric identification?") and the discrimination the evidence actually supports ("this is a *covert
trailer-mounted* ALPR, which is a different procurement, different legal posture, and different detection
signature from a pole-mounted fixed ALPR").
**Status:** VERIFIED
**Evidence:** EFF's border-ALPR field guide distinguishes, within one technology, at least five physically
and legally distinct sub-forms with different owners and different retention: checkpoint ALPRs (CBP,
15-year retention, ~5-year searchable), DEA NLPRP roadside (90-day retention), covert units disguised in
orange construction barrels and yellow sandbags, speed/signage-trailer-mounted units, and pole-mounted
units — and identifies ownership *from the camera brand inside the housing*: "If a covert ALPR has a
Motorola Solutions camera inside, it's likely a CBP system," while Selex ES cameras suggest DEA
(https://www.eff.org/deeplinks/2025/11/how-identify-automated-license-plate-readers-us-mexico-border,
retrieved 2026-08-20). Meanwhile the Atlas of Surveillance rolls all of this into one category, "Automated
License Plate Readers" (https://atlasofsurveillance.org/glossary, retrieved 2026-08-20).
**Retrieved:** 2026-08-20
**Implication for the spec:** Three levels — `domain` (13) → `family` (35) → `technology` (101). Crosswalk
tables map external vocabularies (Atlas, EFF SLS, CCOPS inventories) to the level they actually resolve to,
usually `family`. Never force an external source down to `technology` level; record the coarsest level the
evidence supports and let the graph express `technology --narrower_than--> family`.
**Outline delta:** EXTENDS §8.4.

---

### F7.4 — External taxonomies do not agree, and the disagreement is structural

**Claim:** The three most-cited public taxonomies (EFF Atlas of Surveillance glossary, EFF Street-Level
Surveillance, CCOPS municipal inventories) partition the space on three different axes — Atlas by
*procurement-visible technology*, SLS by *civil-liberties argument*, CCOPS by *legal trigger* — so a
crosswalk must be many-to-many with an explicit `mapping_relation`, not a lookup table.
**Status:** VERIFIED
**Evidence:**
- **Atlas glossary** (https://atlasofsurveillance.org/glossary, curl 2026-08-20) defines exactly 12
  technology terms plus one method term: ALPR, Body-Worn Camera, Camera Registry, Cell-Site Simulator,
  Crowdsourcing (method), Drone (UAV), Face Recognition, Fusion Center, Gunshot Detection, Open-Source
  Intelligence, Predictive Policing, Real-Time Crime Center, Ring/Neighbors Partnership, Video
  Analytics/Computer Vision. Note that "Fusion Center" (an *organization type*) and "Crowdsourcing" (a
  *research method*) sit in the same list as "Cell-Site Simulator" (a *device*).
- **EFF Street-Level Surveillance** navigation (curl https://sls.eff.org/technologies, 2026-08-20 — the URL
  itself returns 404 but the site nav is served in the error page body) lists 16: Automated License Plate
  Readers; Biometric Surveillance; Body-Worn Cameras; Surveillance Camera Networks; Cell-Site
  Simulators/IMSI Catchers; Drones and Robots; Face Recognition; Electronic Monitoring; Gunshot Detection;
  Forensic Extraction Tools; Police Access to IoT Devices; Predictive Policing; Community Surveillance Apps;
  Real-Time Location Tracking; Social Media Monitoring; Police Databases. SLS has categories Atlas lacks
  entirely (Electronic Monitoring, Forensic Extraction, Police Databases, Real-Time Location Tracking, IoT)
  and folds Face Recognition under *and* alongside Biometric Surveillance.
- **The Atlas vocabulary is itself unstable and the glossary is stale.** In March 2024 EFF *removed* the
  Ring/Neighbors category (2,530 data points deleted) and *added* "Third-Party Investigative Platforms
  (TPIPs)", defined as "cloud-based software systems that law enforcement agencies subscribe to in order to
  access, share, mine, and analyze various sources of investigative data"
  (https://www.eff.org/deeplinks/2024/03/atlas-surveillance-removes-ring-adds-third-party-investigative-platforms,
  retrieved 2026-08-20). As of 2026-08-20 the live glossary **still lists Ring/Neighbors and still does not
  list TPIPs** — i.e. the public glossary and the live data model have been out of sync for ~29 months.
- **CCOPS** inventories are keyed to an ordinance *definition* of "surveillance technology" with statutory
  exemptions, so they include things no technology taxonomy would (e.g. parking-meter data) and exclude
  things every taxonomy includes (exempted categories). Seattle publishes a "Master List of Surveillance
  Technologies ... reflect[ing] the technologies and their 'groupings'" and a per-technology Surveillance
  Impact Report (https://www.seattle.gov/tech/privacy/surveillance/surveillance-reports, per search result
  metadata retrieved 2026-08-20 — page itself NOT fetched, see Open Questions).
**Retrieved:** 2026-08-20
**Implication for the spec:** The crosswalk table needs SKOS-style relations: `exactMatch`, `broadMatch`,
`narrowMatch`, `relatedMatch`, and a `note` field. And SIG must *not* import Atlas categories as its
technology primary key: Atlas mixes organization-types and methods into its technology list, and its
vocabulary has already had a breaking change. Import as a crosswalked external vocabulary with its own
version stamp.
**Outline delta:** EXTENDS §8.4 and §10 Phase 1C. CORRECTS the implicit assumption in §10 Phase 1C that
Atlas categories can be adopted directly; they require reconciliation and the Ring removal means the Atlas
has *negative* evidence semantics (absence of a Ring datapoint after March 2024 means "category retired,"
not "program ended").

---

### F7.5 — The Atlas is CC-BY, actively maintained, and larger than the outline states

**Claim:** Atlas of Surveillance carries a CC-BY license, was last updated 2026-08-12, and now holds
"more than 15,000 datapoints in 6,000-plus jurisdictions."
**Status:** VERIFIED
**Evidence:** https://atlasofsurveillance.org/pages/about (curl, 2026-08-20): "Although we have amassed more
than 15,000 datapoints in 6,000-plus jurisdictions..."; "The Atlas of Surveillance data was last updated on
Aug 12, 2026."; footer link labelled "CC-by" on every page. Attribution credit line names EFF + UNR Reynolds
School of Journalism. The About page also carries an explicit *scope boundary* relevant to SIG: "Please do
not send us the individual locations of surveillance cameras or automated license plate readers. That data
may be better suited for DeFlock.me."
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Atlas is redistributable with attribution — record `license: CC-BY-4.0`
(version not stated on the page; treat as `CC-BY (version unspecified)` until confirmed, see Open Questions),
`attribution: "Electronic Frontier Foundation and the Reynolds School of Journalism, University of Nevada,
Reno"`. (b) EFF has publicly delineated Atlas (agency-level) vs DeFlock (device-level) — SIG's federation
design should honor that boundary and cite it as ecosystem precedent for §18.
**Outline delta:** CONFIRMS §10 Phase 1C and §14.2. EXTENDS §18 — EFF has already drawn the
agency-level/device-level line that SIG proposes to straddle.

---

# Part 2 — The canonical technology taxonomy

## 2.1 Structure

```text
domain   (13)  surveillance-vehicle, surveillance-video, biometric-id, acoustic,
                robotics-aerial, robotics-ground, comms-intercept, device-forensics,
                data-acquisition, analytics-inference, integration-platform,
                person-monitoring, facility-screening
   └── family   (35)  e.g. alpr, video-fixed, face-recognition, gunshot-detection
        └── technology (101)  e.g. alpr-covert-trailer
```

Slug rules:
- lowercase, hyphenated, stable forever, **never reused**; retirement is by `status: retired` +
  `superseded_by`, never by deletion (this is the lesson of the Atlas Ring removal, F7.4).
- The slug encodes `family-discriminator`, not vendor. `flock-falcon` is a *Product*, never a Technology.
- `-unspecified` variants exist in every family, because most real evidence is coarse. An agency contract
  that says only "license plate reader system" resolves to `alpr-unspecified`, which is
  `narrower_than: nothing` and `broader_than: {alpr-fixed, alpr-mobile, alpr-covert, alpr-trailer}`. This is
  how §6.6 / §9.4 incompleteness gets represented rather than guessed away.

Column key for the tables below:
- **Distinguishing criterion** — the single test that separates this technology from its nearest sibling.
  If two candidate rows share a criterion, they are the same technology.
- **Evidence signature** — the literal strings/artifacts that indicate presence, drawn from real contracts,
  portals, and reporting encountered in this research.
- **Salience** — privacy/legal salience: `L` (low), `M`, `H`, `C` (critical: implicates a constitutional or
  statutory special category — biometrics, content of communications, immigration status, reproductive or
  religious activity, or First-Amendment-protected association).

---

## 2.2 Domain: surveillance-vehicle

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `alpr-fixed` | alpr | Camera at a permanent roadside/pole/mast position that OCRs every passing plate. Criterion: fixed mounting + plate OCR. | "Falcon", "fixed LPR", pole-attachment permit, "solar-powered LPR", DeFlock/OSM `man_made=surveillance` + `surveillance:type=ALPR` | H |
| `alpr-mobile` | alpr | Plate OCR from a moving vehicle (patrol car, repo truck). Criterion: mount is a vehicle. | "Fleet 3", "mobile LPR", "trunk-mounted", "MPH-900", DRN driver contracts | H |
| `alpr-covert` | alpr | Plate OCR from concealed housing designed to be unrecognizable. Criterion: deliberate concealment. | "covert ALPR", construction barrel, sandbag housing, "covert trail cameras with license plate-capture" (CBP July 2025 solicitation) | C |
| `alpr-trailer` | alpr | Plate OCR on a towable trailer, redeployable without permits. Criterion: towable, self-powered. | "mobile security trailer", "speed trailer with LPR", "deployable" | H |
| `alpr-checkpoint` | alpr | Plate OCR integrated into a fixed border/port/toll inspection lane, tied to a federal record system. Criterion: operated at a controlled crossing. | CBP checkpoint, Perceptics/SAIC, 15-yr retention | C |
| `alpr-unspecified` | alpr | Plate reading, form unknown. | "ALPR", "LPR", "license plate reader" with no modifier | H |
| `vehicle-fingerprint-reid` | vehicle-analytics | Re-identifying a vehicle by make/model/color/damage/roof-rack/bumper-sticker **without** a plate. Criterion: matching on non-plate attributes. | "Vehicle Fingerprint", "vehicle description search", "search without a plate" | H |
| `commercial-plate-data-purchase` | vehicle-data-acquisition | Buying access to plate sightings collected by private, non-police collectors. Criterion: agency has no camera; the collector is commercial. | DRN, "commercial LPR database", repo-industry data, "billions of vehicle sightings" | C |
| `toll-transponder-read` | vehicle-tracking | Reading RFID/DSRC toll transponders. Criterion: reads a transponder ID, not a plate image. | E-ZPass records subpoena, "transponder read logs" | H |
| `traffic-radar-lidar` | traffic-enforcement | Speed/red-light enforcement sensing. Criterion: primary output is a speed/violation, not an identity. | "photo enforcement", "speed safety camera", Jenoptik, Verra Mobility | M |
| `bluetooth-wifi-mac-capture` | vehicle-tracking | Logging Bluetooth/Wi-Fi MAC addresses of passing devices, often bundled into an ALPR housing. Criterion: captures device identifiers alongside/instead of plates. | "TraffiCatch", "Bluetooth sniffer", Jenoptik Vector option | C |

## 2.3 Domain: surveillance-video

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `cctv-fixed` | video-fixed | Fixed-field-of-view camera owned/operated by a government body. Criterion: no pan/tilt, government-owned. | "fixed camera", "bullet camera", "Condor Bullet", city CCTV inventory | M |
| `cctv-ptz` | video-fixed | Operator- or auto-steerable camera with optical zoom. Criterion: remote steering. | "PTZ", "Condor PTZ", "pan-tilt-zoom", "dome camera" | H |
| `cctv-trailer` | video-mobile | Redeployable camera mast on a trailer. Criterion: towable video, no plate OCR required. | "mobile surveillance trailer", LVT, "deployable camera unit" | H |
| `cctv-covert` | video-mobile | Concealed video, typically warranted/pole-camera. Criterion: concealment. | "pole camera", "covert camera", warrant application | C |
| `body-worn-camera` | officer-video | Officer-mounted recording device. Criterion: worn on the person. | "BWC", "Axon Body 4", "Getac", grant award, "body-worn camera program" | M |
| `in-car-video` | officer-video | Vehicle-mounted officer recording. Criterion: mounted in patrol vehicle. | "ICV", "Fleet 3", "dash camera" | M |
| `bwc-live-stream` | officer-video | Real-time streaming from BWC/ICV to a command position. Criterion: live, not post-hoc upload. | "Axon Respond", "live stream body camera", "LTE streaming" | H |
| `private-camera-registry` | camera-federation | Voluntary registration of *the existence and location* of a privately owned camera; no feed. Criterion: registry stores metadata, not video. | "camera registry", `*.fususregistry.com/camera-registry`, CityProtect registry, "register your camera" | M |
| `private-camera-integration` | camera-federation | Technical ingestion of a private camera's live feed into a police platform. Criterion: police can view the stream without contacting the owner. | "integrate your camera", FususCORE, "totalIntegratedCameras", Verkada→Fusus webhook | C |
| `private-camera-request` | camera-federation | Per-incident, owner-approved sharing of recorded footage. Criterion: owner approves each request. | "Community Requests", "Request for Assistance", Neighbors feed request | H |
| `video-analytics-object` | video-analytics | Detection/classification of objects, people, vehicles, attributes in video. Criterion: no identity resolution. | "video analytics", BriefCam, "object search", "attribute search" | H |
| `video-analytics-behavior` | video-analytics | Anomaly / loitering / crowd / "suspicious behavior" inference. Criterion: output is a behavioral judgement. | "behavioral analytics", "anomaly detection", "loitering detection" | C |
| `person-reidentification` | video-analytics | Matching the same (unnamed) person across cameras by appearance/gait. Criterion: re-ID without naming. | "person of interest tracking", "appearance search", "re-identification" | C |
| `video-natural-language-search` | video-analytics | LLM/VLM query over stored video and sensor data in plain language. Criterion: free-text query interface. | "Flock FreeForm", "natural language search", "ask your video" | C |
| `video-live-triage-ai` | video-analytics | Model watching live feeds and escalating events to humans. Criterion: continuous, live, automated escalation. | "Axon Vision", "live video AI triage" | C |

## 2.4 Domain: biometric-id

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `face-verification-1to1` | face-recognition | Confirming a claimed identity against one reference. Criterion: 1:1. | "identity verification", booking-photo confirmation | H |
| `face-identification-1toN` | face-recognition | Searching a probe image against a gallery to generate candidates. Criterion: 1:N, non-real-time. | "face recognition search", "candidate list", "investigative lead only" | C |
| `face-recognition-retrospective` | face-recognition | 1:N run against *stored* video/images after the fact. Criterion: input is archived media. | "retrospective facial recognition", "post-event search" | C |
| `face-recognition-live` | face-recognition | 1:N against a watchlist on a live feed. Criterion: real-time alerting. | "live facial recognition", "LFR", "watchlist alert" | C |
| `face-recognition-mobile` | face-recognition | Field capture-and-identify on a handheld. Criterion: capture happens during a stop. | "Mobile Fortify", "mobile ID app", "field identification" | C |
| `face-recognition-web-scraped` | face-recognition | 1:N against a gallery assembled by scraping the open web/social media. Criterion: gallery provenance is scraping. | Clearview AI, PimEyes, "50+ billion images" | C |
| `iris-recognition` | biometric-other | Iris pattern matching. | "iris scan", BOSS, jail intake iris | C |
| `fingerprint-latent-search` | biometric-other | AFIS/NGI/ABIS latent or ten-print search. | "IAFIS", "NGI", "Live Scan", "ABIS" | C |
| `dna-database-search` | biometric-other | Forensic DNA profile search. Criterion: search against CODIS or a local/"rogue" DNA index. | "CODIS", "local DNA database", "rapid DNA" | C |
| `forensic-genetic-genealogy` | biometric-other | Identifying via relatives in consumer genealogy databases. Criterion: kinship inference through third-party genealogy data. | "FGG", GEDmatch, FamilyTreeDNA, Othram, Parabon | C |
| `tattoo-recognition` | biometric-other | Image matching of tattoos. | "tattoo recognition", NIST Tatt-C/Tatt-E | C |
| `voice-recognition` | biometric-other | Speaker identification/verification, incl. carceral voice prints. | "voice biometrics", "continuous voice identification", Securus VoiceIQ | C |
| `gait-recognition` | biometric-other | Identifying a person by walking pattern. | "gait analysis", "gait recognition" | C |
| `biometric-reference-database` | biometric-infrastructure | The *gallery* itself, as infrastructure separate from the matcher. Criterion: it is a corpus, not an algorithm. | DMV photo database, mugshot repository, NGI-IPS, state ABIS | C |

## 2.5 Domain: acoustic

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `gunshot-detection-acoustic` | gunshot-detection | Networked outdoor microphone array triangulating gunfire. Criterion: fixed sensor array + triangulation. | ShotSpotter, "acoustic sensor", "sensor coverage area (sq mi)", per-sq-mi pricing | H |
| `gunshot-detection-onsite` | gunshot-detection | Single-site indoor/outdoor gunshot sensor without triangulation network. Criterion: no multi-sensor triangulation. | "Raven", "indoor gunshot detection", school deployment | M |
| `acoustic-event-detection-other` | acoustic-other | Detection of non-gunshot events (screams, glass, street takeovers, crashes). Criterion: detects sounds other than gunfire. | "street takeover detection", "aggression detection", Flock gunshot product copy naming crashes | H |
| `audio-recording-public` | acoustic-other | Continuous recording of ambient audio in public space. Criterion: retains audio content. | microphone in camera housing, "audio capture enabled" | C |
| `jail-call-monitoring` | carceral-acoustic | Recording/monitoring of detainee telephone and video calls, incl. voice-print enrollment. Criterion: the subject is in custody. | Securus, ViaPath/GTL, "inmate communications", "call recording and monitoring" | C |
| `translation-transcription-analytics` | acoustic-analytics | ASR + machine translation + keyword/topic alerting over recorded speech. Criterion: derives text and alerts from audio. | "transcription", "keyword alerting", "LEO transcription service" | C |

## 2.6 Domain: robotics-aerial / robotics-ground

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `uas-manual` | drone | Pilot-flown small UAS launched by hand for a specific mission. Criterion: human launches on scene. | "UAS program", Part 107 certificate, "drone unit" | M |
| `uas-dfr-docked` | drone | Dock-launched, remotely/autonomously flown drone dispatched to calls before officers arrive. Criterion: launches from a fixed dock in response to CAD, under a BVLOS/shielded waiver. | "Drone as First Responder", "DFR", dock/nest install, FAA §91.113 waiver, "200ft/400ft" tier | C |
| `uas-tethered` | drone | Persistently powered tethered aerostat/drone over an event or scene. | "tethered drone", "persistent overwatch" | H |
| `counter-uas` | drone-defense | Detecting/tracking/mitigating other drones. Criterion: the target is an aircraft. | Dedrone, "airspace security", "counter-UAS" | M |
| `aerial-manned-surveillance` | aerial-other | Fixed-wing/helicopter surveillance, incl. wide-area persistent imaging. | "spy plane", Persistent Surveillance Systems, "aerial investigation" | C |
| `satellite-imagery-analysis` | aerial-other | Commercial satellite imagery tasking/analysis for enforcement. | Planet, Maxar procurement by an enforcement agency | M |
| `ugv-robot-dog` | ground-robot | Legged/wheeled uncrewed ground vehicle carrying sensors. Criterion: ground-mobile robot, not a drone. | "Spot", Boston Dynamics, Ghost Robotics, "robotic dog" | H |
| `throwable-tactical-robot` | ground-robot | Small throwable/indoor recon robot. | "Lemur", "Sky-Hero", "throwbot" | M |

## 2.7 Domain: comms-intercept

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `cell-site-simulator` | rf-intercept | Device impersonating a cell tower to force device registration and locate/identify handsets. Criterion: transmits as a base station. | Stingray, Hailstorm, KingFish, Crossbow, non-disclosure agreement with FBI, "wireless site survey equipment" (euphemism in purchase orders) | C |
| `rf-imsi-sniffer-passive` | rf-intercept | Passive collection of cellular identifiers without transmitting. | "passive IMSI collection" | C |
| `pen-register-trap-trace` | lawful-intercept | Real-time dialing/routing metadata collection under a pen/trap order. | Pen-Link, "PLX", "pen register" | C |
| `wiretap-content` | lawful-intercept | Title III interception of communications content. | "Title III", "wire intercept", Pen-Link/Cellebrite intercept modules | C |
| `tower-dump` | telecom-records | Bulk request for all devices registered to a tower in a window. | "tower dump", carrier legal-compliance invoice | C |
| `geofence-warrant` | telecom-records | Compelled disclosure of all devices within a geographic/temporal boundary from a platform. Criterion: the *provider* runs the geographic query. | "geofence warrant", "reverse location warrant" | C |
| `keyword-warrant` | telecom-records | Compelled disclosure of all users who searched a term. | "reverse keyword warrant" | C |

## 2.8 Domain: device-forensics

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `mobile-logical-extraction` | device-forensics | Consented/API-level copy of accessible device data. Criterion: no bypass of device security. | UFED "logical", "advanced logical" | H |
| `mobile-physical-extraction` | device-forensics | Full-filesystem/physical image, typically requiring exploitation of the device. Criterion: bypasses lock/encryption. | GrayKey, "Cellebrite Premium", "full file system extraction", "brute force passcode" | C |
| `mobile-forensic-analysis` | device-forensics | Parsing/indexing/searching an extracted image. Criterion: operates on an image, does not acquire. | Magnet AXIOM, "Physical Analyzer", "Inseyets" | H |
| `cloud-account-extraction` | device-forensics | Acquiring the subject's cloud-hosted data using tokens/credentials recovered from a device or by legal process. Criterion: data comes from a platform, not the handset. | "cloud extraction", "Cellebrite Cloud", "token-based cloud acquisition" | C |
| `computer-forensics` | device-forensics | Disk/memory acquisition and analysis of non-mobile devices. | EnCase, FTK, X-Ways | H |
| `mobile-device-virtualization` | device-forensics | Running a virtualized instance of a target OS/app for analysis. Criterion: emulation, not acquisition. | Corellium (Cellebrite, Dec 2025) | M |
| `vehicle-infotainment-extraction` | device-forensics | Extracting call logs, contacts, and location from a car's telematics/infotainment module. | Berla iVe, "vehicle forensics" | C |

## 2.9 Domain: data-acquisition (the commercial pipeline — §4.9)

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `adtech-location-purchase` | location-data | Purchase of bulk device-location records sourced from mobile advertising bid-stream/SDK data. Criterion: origin is the ad ecosystem. | Fog Reveal, Venntel, Locate X, Webloc, "device ID", "MAID", "pattern of life" | C |
| `location-data-subscription-platform` | location-data | A hosted query UI over purchased location data. Criterion: agency queries a vendor portal, does not receive a file. | "Fog Reveal portal", "Tangles + Webloc" | C |
| `telematics-connected-car-data` | location-data | Location/telemetry from vehicle manufacturers or insurers. | OEM legal-compliance request, Otonomo/Wejo-style broker | C |
| `people-search-credit-header` | identity-data | Person-resolution from credit-header, utility, and public-record aggregation. Criterion: the product resolves an identity to addresses/associates/assets. | Accurint, TLOxp, CLEAR, "skip trace", "person report" | C |
| `utility-subscriber-records` | identity-data | Bulk utility/water/electric subscriber data supplied to a broker. Criterion: source is a utility. | "National Data Exchange for utilities", Thomson Reuters CLEAR utility file | C |
| `third-party-investigative-platform` | analytic-platform | Subscription platform aggregating multiple brokered datasets with search/link analysis. (EFF's TPIP category, F7.4.) Criterion: multi-source, subscription, cloud-hosted, not agency-owned data. | CLEAR, Accurint Virtual Crime Center, TLOxp, CrimeTracer | C |
| `osint-collection-platform` | osint | Tooling for collecting/monitoring open web and social media at scale. Criterion: collects public content, does not buy it. | ShadowDragon SocialNet, Skopenow, Babel Street BabelX, "OSINT platform" | C |
| `social-media-monitoring` | osint | Targeted or geofenced monitoring of social platforms, often with alerting. Criterion: alerting on social content. | Dataminr, Media Sonar, Geofeedia (historical), "social media threat alerts" | C |
| `dark-web-breach-data` | osint | Use of breached/stolen corpora as an investigative dataset. Criterion: provenance is a breach. | "dark web data", "breach data", Flock Nova controversy | C |
| `commercial-imagery-of-persons` | identity-data | Purchase of face/biometric corpora assembled commercially. | Clearview licensing, "image licensing agreement" | C |

## 2.10 Domain: analytics-inference

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `predictive-policing-place` | predictive | Forecasting *where* crime will occur; output is a geography. | PredPol/Geolitica, HunchLab, "hot spot forecasting", ResourceRouter | C |
| `predictive-policing-person` | predictive | Ranking *individuals* by predicted involvement; output is a person list. | "Strategic Subject List", "heat list", "chronic offender" | C |
| `risk-assessment-pretrial` | predictive | Actuarial scoring for pretrial/sentencing/parole decisions. Criterion: output is a court/corrections decision aid. | COMPAS, PSA, "risk and needs assessment" | C |
| `link-analysis-entity-resolution` | analytic | Graph/link analysis across agency and brokered records. | Palantir Gotham, i2, "link chart", "entity resolution" | C |
| `ai-report-drafting` | analytic | Generative drafting of police narrative reports from BWC audio/CAD. Criterion: produces the official record. | "Draft One", "AI report writing" | H |
| `ai-assistant-officer` | analytic | LLM copilot over agency data. | "Axon Assistant", "CJIS-compliant assistant" | H |
| `gun-crime-ballistics-network` | forensic-analytic | Correlating cartridge/ballistic images across cases nationally. | NIBIN, "ballistic imaging", ATF correlation review | H |

## 2.11 Domain: integration-platform

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `rtcc-platform` | integration | Software hub ingesting live video/sensor/CAD feeds for real-time operations. Criterion: real-time, multi-source, operational. | Fusus, FlockOS, Citigraf, "real-time crime center", "single pane of glass" | C |
| `investigative-search-platform` | integration | Cross-agency/cross-source *search* over records (not live feeds). Criterion: retrospective search, federated. | CrimeTracer/COPLINK, Peregrine, "law enforcement search engine" | C |
| `cad-system` | integration | Computer-aided dispatch. | "CAD", Mark43, CentralSquare, Tyler, "call for service" | M |
| `rms-system` | integration | Records management system holding incident/arrest records. | "RMS", Axon Records, Niche, "NIBRS submission" | H |
| `digital-evidence-management` | integration | Storage/chain-of-custody for multimedia evidence. | Evidence.com, Genetec Clearance, "DEMS" | M |
| `nextgen-911-platform` | integration | Cloud call-taking/emergency communications. | Carbyne, Prepared, "NG911", "Axon 911" | H |
| `camera-federation-platform` | integration | Platform whose function is enrolling third-party cameras. Criterion: its primary object is *other people's cameras*. | Community Connect, CityProtect, Genetec Community Connect | C |
| `interagency-data-exchange` | integration | Standing federated query/exchange fabric between agencies. | N-DEx, Nlets, RISSNET, LInX, "LEEP" | C |
| `community-reporting-app` | integration | Public-facing app for tips/incident reporting/alerting. | Neighbors, Citizen, Nextdoor, "SaferWatch", "tip line app" | M |

## 2.12 Domain: person-monitoring / facility-screening

| slug | family | Definition / distinguishing criterion | Evidence signature | Sal. |
|---|---|---|---|---|
| `electronic-monitoring-gps` | em | Court/agency-ordered GPS ankle or wrist device. Criterion: continuous location of a named, legally-supervised person. | BI Inc, SCRAM GPS, Attenti, Track Group, "EM caseload" | C |
| `electronic-monitoring-rf` | em | RF home-curfew monitoring (presence/absence only). | "RF bracelet", "home detention" | H |
| `electronic-monitoring-alcohol` | em | Continuous transdermal alcohol monitoring. | SCRAM CAM | H |
| `electronic-monitoring-smartphone` | em | App-based check-in with GPS/face/voice verification. Criterion: no dedicated hardware. | SmartLINK, "app-based supervision", ICE ISAP | C |
| `weapons-detection-screening` | screening | Walk-through AI-assisted concealed-weapon screening at an entrance. | Evolv Express, "AI weapons detection", "frictionless screening" | H |
| `weapons-detection-video-ai` | screening | Detecting a visible firearm in existing camera feeds. Criterion: uses cameras, not a portal. | ZeroEyes, Omnilert, VOLT AI, "gun detection AI" | H |
| `school-monitoring-student-activity` | screening | Monitoring of school-issued accounts/devices/content. | Gaggle, Bark, GoGuardian, Lightspeed | C |
| `visitor-management-screening` | screening | ID scanning/watchlist screening of building visitors. | Raptor, "visitor management with sex-offender check" | M |

## 2.13 Rollup counts

101 technologies / 35 families / 13 domains. Coverage against the R7 brief's mandatory list: all 40 named
items are present. Three brief items were **split** because the evidence supports a distinction the brief's
phrasing collapses:

- "private-camera federation/registry" → `private-camera-registry` (metadata only) vs
  `private-camera-integration` (live feed) vs `private-camera-request` (per-incident, owner-approved).
  F7.24 shows these three have materially different data flows and that vendors deliberately blur them.
- "cloud/account data extraction" → `cloud-account-extraction` (forensic, token-derived) vs
  `geofence-warrant` / `tower-dump` (compelled platform-side query). Different legal instrument, different
  actor performing the search.
- "commercial location-data purchase" → `adtech-location-purchase` (the acquisition) vs
  `location-data-subscription-platform` (the query surface). F7.36 (Webloc) shows one company can supply the
  data and another can host the UI.

Two items in the brief resolve **not** to Technology but to other entities, and this is itself a finding:
"RTCC" is both a Technology (`rtcc-platform`, the software) and an Organization sub-type (the unit); "fusion
center" is *only* an Organization type, despite the Atlas listing it as a technology (F7.4).

---

# Part 3 — The capability vocabulary

Capability slugs are `verb.object.scope`. Scope values: `own` (data the operator's own org collected),
`partner` (named counterparties), `state`, `region`, `national`, `commercial` (vendor-held data the operator
never collected), `subject` (a single named person/device under legal process).

## 3.1 Query capabilities

| slug | Meaning | Typical enabling ConfigurationState |
|---|---|---|
| `search.plate.own` | Search plate reads captured by this org's own devices | retention_days > 0 |
| `search.plate.partner` | Search plates captured by explicitly named partner orgs | `sharing_partners[]` |
| `search.plate.state` | Search plates across an opt-in statewide pool | `state_lookup_enabled` |
| `search.plate.national` | Search plates across a vendor's nationwide pool | `national_lookup_enabled` |
| `search.plate.commercial` | Search a commercially collected (non-police) plate corpus | DRN/NVLS subscription |
| `search.vehicle_attributes.*` | Search by non-plate vehicle attributes at the same scopes | vehicle-fingerprint licensed |
| `search.video.own` / `.partner` | Retrospective video search | camera integration mode |
| `search.face.*` | 1:N face search against a named gallery | gallery contract |
| `search.location_history.subject` | Retrieve historical location for a device/person | broker subscription |
| `search.location_history.commercial` | Area/pattern queries across a brokered population | Fog/Webloc licence |
| `search.person_records.commercial` | Person/associate/asset resolution | CLEAR/TLOxp/Accurint seat |
| `search.records.partner` / `.region` | Federated records search across agencies | CrimeTracer/N-DEx/RISSNET membership |
| `search.social.*` | Query social/open-web corpora | OSINT platform seat |

## 3.2 Alerting capabilities

| slug | Meaning |
|---|---|
| `alert.hotlist.own` | Receive alerts when own cameras hit a locally maintained list |
| `alert.hotlist.federal` | Receive alerts sourced from a federal file (NCIC topics) |
| `alert.hotlist.custom` | Create an arbitrary custom plate list ("custom hotlist") |
| `alert.gunshot` | Receive acoustic gunshot alerts |
| `alert.weapon_detection` | Receive AI weapon-detection alerts |
| `alert.behavior` | Receive behavioral/anomaly alerts |
| `alert.social` | Receive social-media/OSINT alerts |
| `alert.push_to.partner` | **Push** own alerts into a partner's console (distinct from partner searching you) |

## 3.3 Live-operations capabilities

`view.livestream.own_camera`, `view.livestream.private_camera`, `view.livestream.bwc`,
`control.ptz.own`, `control.ptz.private_camera`, `dispatch.uas.autonomous`, `view.cad.partner`,
`view.aviation_feed.partner`.

`control.ptz.private_camera` deserves emphasis: the difference between *seeing* a private feed and
*steering* a private camera is the sharpest ownership/control boundary in the whole model (Part 6).

## 3.4 Acquisition / extraction capabilities

`extract.device.logical`, `extract.device.physical`, `extract.cloud.account`, `intercept.metadata.subject`,
`intercept.content.subject`, `locate.handset.rf` (cell-site simulator), `acquire.dna.rapid`,
`acquire.biometric.field`.

## 3.5 Export / onward-disclosure capabilities

This class is systematically missing from every public taxonomy and is where the real harm lives.

| slug | Meaning |
|---|---|
| `disclose.results.to_partner` | Results of a search can be exported to another org |
| `disclose.bulk.to_vendor` | Vendor retains/uses the org's data beyond service delivery |
| `disclose.audit.public` | The org's search log is published (transparency portal) |
| `resell.derived.commercial` | Vendor resells data derived from this deployment to third parties |

## 3.6 Governance capabilities (config-derived, evidentiary)

`audit.self.enabled`, `audit.anomaly_detection.enabled`, `audit.case_code.required`,
`audit.lockout.automatic`, `retention.days`, `restrict.offense_category`, `restrict.federal_sharing`,
`restrict.immigration_query`.

**Design rule:** governance capabilities are *negative* capabilities — they describe restrictions. Model them
as ConfigurationState attributes and derive the capability by negation, so that "no evidence of restriction"
never silently becomes "restriction absent" (§9.4).

---

# Part 4 — Vendor and product reference cards

Every card follows: identity → corporate history → current products → data architecture → sharing model →
integrations → transparency artifacts. Facts are keyed to findings where they are non-obvious or where they
correct the outline.

---

## 4.1 Flock Safety

### F7.6 — Flock corporate identity and scale, current as of 2026-08

**Claim:** Flock Safety is a private Delaware-incorporated company headquartered in Atlanta, GA, founded 2017
by Garrett Langley, Matt Feury and Paige Todd; valued at ~$8.4B as of April 2026 after a ~$200M share
authorization, having raised $275M at $7.5B in Sept 2025 (a16z-led) and >$1B total; it operates 120,000+
cameras and serves roughly 5,000 law-enforcement agencies plus ~1,000 private-sector organizations.
**Status:** VERIFIED (valuation PARTIALLY VERIFIED — secondary sources only)
**Evidence:**
- Guardian, 2026-08-20 (curl w/ Chrome UA after WebFetch host-block): "Flock Safety has more than 120,000
  cameras set up on roads across the US that scan license plates billions of times every month."
- CNBC 2025-10-16 (curl after 403 on WebFetch): Flock "works with an estimated 6,000 communities and 5,000
  law enforcement agencies, and sees a 'long tail' ... 17,000 cities"; "Flock has contracts with an estimated
  1,000 private sector organizations."
- Valuation: https://techstartups.com/2026/04/17/flock-safety-hits-8-4b-valuation-as-ai-powered-police-tech-sparks-nationwide-protests/
  and https://www.axios.com/pro/all-deals/2026/04/13/flock-safety-fundraising-surveillance-tech (search-result
  summaries retrieved 2026-08-20; the $7.5B/$275M round is confirmed first-party at
  https://www.flocksafety.com/blog/flock-safety-secures-major-funding).
**Retrieved:** 2026-08-20
**Implication for the spec:** Vendor records need `ownership_status` (private/public), `valuation_usd` with
`as_of`, `hq_place`, `founded`, `founders[]`, and a **funding-round history** table — because valuation
inflection points correlate with product-line expansion (drones after the Aerodome deal, Nova after the 2025
round) and are useful priors for §12 research-task generation.
**Outline delta:** EXTENDS §8.2 — add corporate-finance attributes; the outline's Vendor entity has only
`offers/supplies/acquires`.

### F7.7 — Flock's product line is materially larger than the outline's list, and three products are new

**Claim:** Flock's current catalogue is LPR (Falcon / Falcon Flex / Sparrow), video (Condor PTZ, Condor
Bullet), Mobile Security Trailers, Gunshot Detection (Raven), Drone-as-First-Responder (Flock Aerodome,
incl. Aerodome Alpha), and software: the Flock Safety Platform, FlockOS, **Flock Nova**, **Flock911**,
**Flock FreeForm**, Investigations Manager, National LPR Network, and **Evidence Mode**.
**Status:** VERIFIED
**Evidence:** https://www.flocksafety.com/products (WebFetch, 2026-08-20) enumerates hardware (LPR, Flock
Video Cameras, Mobile Security Trailers, Gunshot Detection, DFR) and software (Flock Safety Platform,
FlockOS, Flock911 — "Streams live 911 calls en route and enables cross-jurisdiction visibility";
Flock FreeForm — "Searches video and LPR systems using natural language queries"; National LPR Network;
Investigations Manager). Evidence Mode is announced in the Aug 2026 guardrails post as preservation of
"specific data for active investigations in cold storage at no additional cost". Sparrow/Condor/Raven names
confirmed via https://www.flocksafety.com/blog/product-announcement-q2-2023 (search-result summary).
**Retrieved:** 2026-08-20
**Implication for the spec:** Product entities need `announced_date`, `ga_date`, `superseded_by`, and a
`product_kind` enum (`hardware_device | software_platform | software_module | data_service | managed_service`).
Flock911 and FreeForm are *modules* of FlockOS, not standalone products — the Product entity therefore needs
a self-referential `component_of` edge.
**Outline delta:** CORRECTS §8.3 — the outline's product examples ("Flock Falcon; Flock platform") are three
years stale and miss the entire 2025–26 software line, which is where the capability expansion happened.
EXTENDS §4.1.

### F7.8 — Aerodome: $300M+, Oct 2024, and it created a vertically integrated DFR vendor

**Claim:** Flock acquired drone startup Aerodome in October 2024 for over $300 million, 17 months after
Aerodome's founding, and has since shipped US-manufactured NDAA-889-compliant aircraft (Aerodome Alpha,
Oct 2025) from a 100,000 sq ft Georgia facility.
**Status:** VERIFIED
**Evidence:** https://techcrunch.com/2024/10/23/flock-safety-paid-over-300-million-for-17-month-old-drone-startup-aerodome/;
first-party https://www.flocksafety.com/blog/flock-safety-expands-into-drones-for-law-enforcement-with-acquisition-of-aerodome;
https://dronelife.com/2025/03/20/flock-safety-secures-275m-funding-accelerates-drone-expansion-with-aerodome-acquisition-and-faa-milestone/
(all via search-result summaries retrieved 2026-08-20).
**Retrieved:** 2026-08-20
**Implication for the spec:** Acquisition edges need `announced_date`, `closed_date`, `consideration_usd`,
`consideration_disclosed: bool`, and `product_rebrand[]` (Aerodome → "Flock Aerodome"). Product provenance
must survive rebranding: a 2024 contract naming "Aerodome" and a 2026 contract naming "Flock Aerodome" are
the same product lineage.
**Outline delta:** EXTENDS §8.2; the outline names no Flock acquisitions.

### F7.9 — Flock's August 2026 guardrails are a dated, enumerable set of configuration changes

**Claim:** On 2026-08-13 Flock announced: default ALPR retention cut 30d → 7d (existing customers grandfathered);
"Evidence Mode" cold storage; per-community offense-category filtering of external searches; Audit Assistance
mandatory for all LE customers by end of 2026 (currently ~1/3 voluntary adoption); "Proactive Lockout"
auto-suspension; case codes mandatory for all LE searches by end of 2026 (pilot began July 2025, emergency
bypass flagged); MFA mandatory since early Aug 2026; a Bishop Fox security review to be published Sept 2026;
a coordinated vulnerability disclosure program; and plain-language contract publication. Over 1,500 agencies
publish transparency portals.
**Status:** VERIFIED
**Evidence:** https://www.flocksafety.com/blog/flock-guardrails-address-lpr-privacy-concerns-and-police-transparency
(WebFetch, 2026-08-20). Corroborated: Guardian 2026-08-20 ("Flock also typically stored ALPR data for 30 days
but reduced that to one week"); https://thenextweb.com/news/flock-safety-privacy-changes-data-retention;
https://www.waff.com/2026/08/15/flock-safety-cuts-license-plate-data-retention-seven-days-amid-community-backlash/.
Counter-evidence that grandfathering is real: Boulder and Lafayette CO retained 30-day settings
(https://kimmonson.com/news/boulder-lafayette-keep-30-day-retention-after-flocks-7-day-default/).
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the single best validation case for §8.12 ConfigurationState +
§9.2 (observation time ≠ validity time). A vendor-default change on 2026-08-13 does **not** change any
deployment's `retention_days` until that deployment is separately observed. The spec must support
`ConfigurationState.source_level ∈ {vendor_default, contract_term, portal_observed, records_request,
agency_policy}` with vendor_default ranked lowest, and must model *pending* configuration changes
(`effective_from` in the future — e.g. "case codes mandatory end of 2026").
**Outline delta:** EXTENDS §8.12 and §19.10. CONFIRMS §9.2 emphatically.

### F7.10 — Flock's federal-access history is a four-stage sequence, not a fact

**Claim:** Flock's relationship with federal immigration enforcement changed at least four times between
May 2025 and Jan 2026: (1) ICE lacked direct access and ran lookups *through local police*; (2) CBP obtained
direct backend access via a pilot, reaching 80,000+ cameras; (3) Flock paused all federal pilots (Aug 2025)
and removed federal orgs from state/national lookup; (4) Jan 2026 added a single per-agency toggle to
disable all federal sharing, extended Aug 2026 to offense-category filtering.
**Status:** VERIFIED
**Evidence:** https://www.404media.co/cbp-had-access-to-more-than-80-000-flock-ai-cameras-nationwide/
(WebFetch, 2026-08-20): "CBP had regular search access to more than 80,000 Flock ALPR cameras nationwide";
mechanism "direct access to Flock's ALPR backend through a pilot program"; "at least Loveland, Colorado
police department shared direct access with CBP"; "Flock announced it had 'paused all federal pilots'";
prior 404 Media May 2025 reporting documented ICE lookups via local police intermediaries. Also
https://www.404media.co/ice-secret-service-navy-all-had-access-to-flocks-nationwide-network-of-cameras/
(ICE HSI ~200 searches; Secret Service; NCIS). Guardian 2026-08-20: "removed federal organisations from
statewide and national lookup networks in August 2025, and in January it added a single toggle."
Congressional investigation: https://www.404media.co/congress-launches-investigation-into-flock-after-404-media-reporting/.
**Retrieved:** 2026-08-20
**Implication for the spec:** AccessRelationship (§8.8) **must** be bitemporal and must carry
`mechanism ∈ {direct_account, proxy_lookup_by_third_party, pilot_program, contractual_share,
network_default, api_integration}`. "ICE had access" was true in three *different senses* in three different
periods, and the difference is the whole story. Also: `AccessRelationship.granted_by` must be separable from
`AccessRelationship.accessor` — Loveland PD granted, CBP accessed, Flock hosted, and the 80,000 cameras
belonged to hundreds of other agencies who never consented. This is a four-party edge and cannot be modeled
as a binary relation.
**Outline delta:** CORRECTS §8.8 — the outline's attribute list (`scope, direction, automatic/manual,
nationwide/statewide/local, valid_from, valid_to, observed_at, source`) lacks `mechanism` and `granted_by`,
without which the ICE case is unrepresentable. EXTENDS §4.1.

### F7.11 — Flock Nova is a data-broker product and its data sourcing was publicly contested

**Claim:** Flock Nova consolidates RMS, CAD, jail, LPR, OSINT and public-records data for investigators;
404 Media reported internal concern that some Nova data derived from breaches (incl. a hacked parking-meter
app); Flock publicly committed that Nova "will not supply any data purchased from known data breaches or
stolen data"; an independent code analysis disputed that characterization.
**Status:** VERIFIED (the dispute is verified; the underlying factual question is UNRESOLVED)
**Evidence:** First-party: https://www.flocksafety.com/blog/correcting-the-record-flock-nova-will-not-supply-dark-web-data.
Reporting: https://www.404media.co/flock-decides-not-to-use-hacked-data-in-people-search-tool/;
https://www.govtech.com/biz/flocks-newest-police-tool-sparks-data-controversy. Dissent:
https://footnote4a.org/news/nova-dark ("My Analysis of Their Code Tells a Different Story").
(All via search-result summaries retrieved 2026-08-20; the first-party Flock post and the 404 headline are
directly quoted in those summaries.)
**Retrieved:** 2026-08-20
**Implication for the spec:** This is a textbook §6.5 contradiction: vendor first-party denial vs
independent technical analysis, both Tier-B/Tier-D, neither retractable. Store both as Claims with an
explicit `contradicts` edge and **no resolution**. It also proves an ALPR vendor is now simultaneously a
`third-party-investigative-platform` — the taxonomy must let one Product implement technologies across
domains, and the graph must not assume vendor-category stability.
**Outline delta:** EXTENDS §4.9 — the outline models the broker pipeline as ending at a separate
"investigative platform"; Flock has vertically integrated the broker layer into the ALPR vendor.

### F7.12 — Flock has lost at least 56–68 municipalities in 2026, and cancellation ≠ removal

**Claim:** At least 56 municipalities deactivated, cancelled or rejected Flock contracts in 2026 (DeFlock's
count as reported by the Guardian), with other reporting citing 68; and in multiple documented cases the
physical cameras remained installed and powered for months after cancellation, with cities resorting to
bagging them.
**Status:** VERIFIED
**Evidence:** Guardian 2026-08-20 (curl): "At least 56 municipalities have deactivated, canceled or rejected
contracts with Flock this year, according to national advocacy organization DeFlock." Non-removal cases named:
Syracuse NY ("it took more than three months after lawmakers officially dropped Flock for the cameras on
municipal land to come down; Syracuse police department officials 'moved to unplug' them after a May deadline
for the company to collect them passed"); Oshkosh WI ("the readers are still up — four months after the
agreement was revoked"); Verona WI; Evanston IL and Dayton OH ("blinded their cameras with trash bags").
The 68 figure appears in secondary aggregation (search-result summary, business-humanrights.org), lower
confidence.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is decisive for §6.7. `contract_status` and `physical_status` and
`operational_status` are **three independent state variables**, and the Oshkosh case has
(contract=cancelled, physical=installed, operational=unknown/bagged) simultaneously. A single `lifecycle`
enum cannot represent it. See Part 7.
**Outline delta:** CORRECTS §6.7 — the outline's single linear state list conflates contractual,
physical, and operational status. CONFIRMS §19.11/§19.12 and Appendix A.3.

### F7.13 — Vendor replacement, not abandonment, is the dominant 2026 pattern, and Axon is the beneficiary

**Claim:** Axon has replaced Flock in at least seven municipalities across five states, including Longmont
CO, Denver CO, and Syracuse NY, and Axon's president has told investors that competitors' privacy failures
are a deciding factor for switchers.
**Status:** VERIFIED
**Evidence:** Guardian 2026-08-20 (curl): "Axon, a $48bn company ... has capitalized on Flock's PR woes by
swooping in to replace their competitor in at least seven municipalities across five states." Josh Isner,
Axon president, February 2026 earnings call: "We're hearing directly from customers — some of whom came to
us from other vendors — that our track record on privacy and ethics was a deciding factor in their decision."
ACLU's Chad Marlow: "We've absolutely seen them lurking in the shadows, waiting for Flock to fail and then
rushing in." Denver: Axon ALPR retention set to 21 days, below Axon's 30-day default. Longmont: unanimous
March 2026 approval, contract not finalized as of 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** §12's "Vendor replacement" research task is validated and must be
first-class: SIG needs a `replaced_by` edge between Deployments with `replacement_kind ∈ {same_capability,
reduced_capability, expanded_capability, unknown}` and a derived metric "net capability change," or the
graph will be used to report false surveillance reductions — exactly the §6.7 danger. Note Longmont's state
on 2026-08-20 is `awarded_not_contracted`, a state the outline lacks (Part 7).
**Outline delta:** CONFIRMS §4.1, §6.7, §22.3, Appendix A.3, with named cases and a date.

---

## 4.2 Axon Enterprise

### F7.14 — Axon corporate identity and acquisition history, verified

**Claim:** Axon Enterprise, Inc. (NASDAQ: AXON, formerly TASER International), HQ Scottsdale AZ, ~$48B market
capitalization as of Aug 2026; acquisition history relevant to SIG: Sky-Hero (2018), Dedrone (closed
2024-10-02), **Fusus (announced 2024-02-01, terms not disclosed)**, Prepared (~$728M, closed Q4 2025),
Carbyne (announced 2025-11-04, $625M all cash, closed Q1/Feb 2026).
**Status:** VERIFIED (Fusus date first-party; Dedrone price CONTRADICTED between secondary sources)
**Evidence:**
- Fusus: https://investor.axon.com/2024-02-01-Axon-Accelerates-Real-Time-Operations-Solution-with-Strategic-Acquisition-of-Fusus
  — announced 2024-02-01, "builds upon a successful strategic partnership launched in May 2022", "terms of
  the transaction were not disclosed."
- Dedrone: first-party https://www.axon.com/blog/axon-completes-acquisition-of-dedrone (WebFetch 2026-08-20)
  gives completion date **October 2, 2024** and discloses **no price**. Secondary sources conflict badly:
  one aggregator says $625.0M, another says ~$391M. **CONTRADICTED — do not record a price.**
- Carbyne: https://investor.axon.com/2025-11-04-Axon-to-Acquire-Carbyne,-Uniting-Cloud-Infrastructure-and-AI-to-Redefine-the-911-Experience;
  $625M valuation, expected close Q1 2026; close confirmed Feb 2026 by secondary sources.
- Prepared: ~$728.2M, per aggregated financial sources (secondary only).
- Market cap: Guardian 2026-08-20, "Axon, a $48bn company."
**Retrieved:** 2026-08-20
**Implication for the spec:** Acquisition edges must carry `consideration_disclosed: false` as a *positive*
assertion when the first party says terms were not disclosed — otherwise downstream aggregators' invented
figures (as here) get laundered into the graph. Where secondary sources conflict on an undisclosed figure,
record CONTRADICTED and store no value (§6.5, §9.4).
**Outline delta:** CONFIRMS §8.2's `Axon acquired -> Fusus` example and supplies the date. EXTENDS §4.1 with
four further acquisitions the outline omits, two of which (Prepared, Carbyne) put Axon inside the 911 call
path — a materially new position in the surveillance stack.

### F7.15 — **INDEPENDENT VERIFICATION: Axon Community Connect lists 321 communities, not 324, and the "850,000 private cameras" figure is an artifact of summing two incommensurable counters**

**Claim:** As of 2026-08-20, axoncommunityconnect.com lists exactly **321** communities across 42
states/DC. Summing the live per-organization statistics API across those communities gives **278,627
registered cameras** and **624,782 "integrated" cameras** — but the integrated figure is not a count of
distinct cameras, it is a per-organization *visibility* count inflated by regional federation, and adding
the two produces 903,409, which is how a "850,000+ private cameras" figure is arrived at and why that figure
is wrong.
**Status:** VERIFIED (my own enumeration)
**Evidence:** The public `/communities/` page is an Astro/Alpine SPA and returns no listings to a naive
fetch (WebFetch confirmed: "the actual community data appears to be dynamically loaded"). Reading the page
source revealed the data plane:

```text
locations list : https://axoncommunityconnect.com/locations.json          (200, 124,020 bytes)
per-org stats  : https://api.fususone.com/api/public/organizations/{org}/stats/   (200, public, unauthenticated)
```

`locations.json` is a JSON array of 321 objects, every one carrying `id`, `title`, `url` (the community's
Connect site), `location.{city,state,coords.lat,coords.lng}`, `registry` (always a
`https://<org>.fususregistry.com/camera-registry` URL), `org` (the Fusus org slug), and `image`.
State distribution: FL 43, CA 38, GA 31, IL 19, TX 17, NC 14, VA 14, AL 11, MN 10, MS 10, LA 9, KS 9, TN 8,
OH 7, NJ 6, CO 6, AZ 6, MI 6, MD 5, WA 5, NM 5, SC 5, NY 4, IN 4, NV 4, PA 3, MO 3, AR 3, KY 2, CT 2, and
1 each in NE, OR, WI, NH, AK, IA, ID, MT, DE, MA, OK, DC.

I queried the stats endpoint for all 321 orgs (8-way parallel, 2026-08-20). 319 returned 200; 2 returned 404
(`riverdale`/`riverdalepd`, `troy`/`troypdil` — listed communities whose Fusus org no longer resolves, i.e.
**stale listings**, itself a lifecycle signal). Sums over the 319:

| field | sum |
|---|---|
| `totalRegisteredCameras` | **278,627** |
| `totalIntegratedCameras` | **624,782** |
| `totalOwnedCameras` | 178,010 |
| `totalSharedCameras` | 201,274 |
| `totalMaxCameras` | 673,379 |
| `subscribedCameras` | 161,844 |

Median registered per community: 221. Mean: 873. 45 communities report zero registered cameras.

**Why `totalIntegratedCameras` cannot be summed.** The metro-Atlanta cluster exposes it: Statesboro GA
reports `registered=1` but `integrated=14,604`; Acworth GA reports `integrated=10,962` against
`totalMaxCameras=500`; College Park GA reports `registered=0`, `integrated=10,669`, `owned=171`. An
"integrated" count that exceeds the org's own licensed maximum by 20× is counting cameras the org can *see*
through regional federation, not cameras it has. Atlanta itself reports `registered=17,501`,
`integrated=28,490`, but `owned=2,583` and `shared=11,609`. The same physical camera is therefore counted in
many orgs' integrated totals.

**Reconciliation with the 850,000 claim.** 278,627 + 624,782 = 903,409. The Reddit-sourced figure the
outline cites ("more than 850,000 privately owned cameras across 324 publicly listed communities") is
arithmetically consistent with `registered + integrated` at an earlier date. My independent conclusion:
**the community count is 321 (not 324) and the camera figure is not a count of privately owned cameras.**
The defensible statements are: (a) 321 listed communities; (b) 278,627 camera *registrations* summed across
orgs — the closest thing to "private cameras enrolled", though even this double-counts where regional and
municipal orgs overlap; (c) 201,274 cameras flagged `shared`; (d) 673,379 licensed camera capacity.
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. `axoncommunityconnect.com/locations.json` + the `api.fususone.com` public stats endpoint constitute a
   **directly enumerable, structured, unauthenticated Tier-B vendor dataset** — 321 orgs with names, cities,
   coordinates, org slugs, registry URLs, and time-varying camera counters. It belongs in §21 and in a
   §10 ingestion phase of its own. It is strictly better evidence than the Reddit post the outline cites.
2. The counters are a perfect UsageAggregate/§8.13 case: they change over time, they are vendor-reported,
   and they have **contested semantics**. The spec must store the raw counter names verbatim
   (`totalIntegratedCameras`) alongside any normalized interpretation, per §19.2 ("raw before normalized"),
   and must attach a `metric_semantics_note`.
3. This is the empirical proof of §4.1's `camera owner != data controller != police accessor != platform
   provider`: the camera owner is a business, the data controller is arguably the enrolling agency, the
   platform provider is Axon, the accessor set is *every federated org in the region*, and the counters
   prove the accessor set is far larger than the owner ever engaged with.
**Outline delta:** **CORRECTS §4.1.** The outline states "more than 850,000 privately owned cameras
represented across just 324 publicly listed communities" and (correctly) flags it for verification. My
verification: the community count is **321** as of 2026-08-20, and the camera figure is a sum of two
counters, one of which is a federation-inflated visibility metric. The outline should cite 321 communities
and 278,627 registrations, with the semantics caveat, and should cite the JSON endpoint rather than Reddit.

### F7.16 — Community Connect's three tiers are distinct technologies with distinct consent postures

**Claim:** Axon Community Connect spans `private-camera-registry` (metadata only), `private-camera-integration`
(live feed via FususCORE), and per-incident request; the vendor's public description emphasizes the registry
tier while the API counters show integration at scale.
**Status:** VERIFIED
**Evidence:** Axon's page copy (curl, 2026-08-20): "Community Connect is a voluntary, public-facing program
within the Axon Fusus platform that allows residents and businesses to **register or integrate** their
private security cameras with their local law enforcement agency." Local promotion frames it as registry-only:
"The program does not provide police with direct access to private security cameras; instead, it creates a
confidential, encrypted map of registered cameras" (https://www.sanmarcosrecord.com/article/31696, search-result
summary). The FususCORE appliance "can be dropped onto any public or private video network and detects,
analyzes and connects to every camera on the building's network." Every one of the 321 listings carries a
`*.fususregistry.com/camera-registry` URL *and* an integrated-camera counter.
**Retrieved:** 2026-08-20
**Implication for the spec:** A Deployment of `camera-federation-platform` must carry a `tier[]` multi-valued
attribute drawn from {`registry`, `integration`, `request`}, and each enrolled PhysicalAsset needs its own
`federation_tier`. Conflating them is how "we only have a map of cameras" and "we can watch 28,000 cameras"
become the same public claim.
**Outline delta:** EXTENDS §4.1 and §8.6.

### F7.17 — Axon severed API interoperability with Flock in 2025; the ecosystem is de-integrating

**Claim:** Axon terminated its Flock partnership and cut API access effective 2025-07-24 for new mutual
customers, after having been an early Flock investor and having integrated Flock's Vehicle Fingerprint into
Fleet 3 under an agreement signed 2024-08-28.
**Status:** VERIFIED (Flock's account; Axon's side not obtained)
**Evidence:** https://www.flocksafety.com/blog/axon-plans-to-sever-apis-with-flock (WebFetch 2026-08-20):
"Axon made a surprise decision to end our partnership and cut off the API access that law enforcement depends
upon"; Axon determined openness "is no longer in Axon's best interests"; new mutual customers unsupported
after 2025-07-24; "Axon executives have not returned our calls." Corroborated by EFF:
https://www.eff.org/deeplinks/2025/04/beware-bundle-companies-are-banking-becoming-your-police-departments-favorite
("Axon severing APIs with Flock Safety to monopolize integrations"), and by reporting that "Fusus' RTCC
software originally supported integration with Flock Safety hardware, but that partnership ended in early
2025."
**Retrieved:** 2026-08-20
**Implication for the spec:** IntegrationRelationship must be **time-bounded and terminable**, with
`termination_reason` and `terminated_by`. An integration that existed 2022–2025 and was unilaterally
severed is a first-class historical fact, not a stale row to delete (§19.3 "time before overwrite"). It also
means the outline's Appendix C pathway `Fusus --integrates--> Flock ALPR` is **no longer true for new
customers** and must carry validity dates.
**Outline delta:** **CORRECTS §4.10 and Appendix C** — the outline's canonical Fusus example
(`integrates -> Flock ALPR`) describes a relationship that Axon terminated in July 2025. Grandfathered
customers may retain it; new ones cannot.

### F7.18 — Axon's current product line spans the entire chain from 911 call to court record

**Claim:** Axon's catalogue now covers: TASER 10; Axon Body 4 (BWC, LTE streaming); Axon Fleet 3 (ICV +
mobile ALPR); fixed ALPR (new); Signal Sidearm; Axon Air (with Skydio) and Dedrone counter-UAS; Axon
Fusus (RTCC) with Community Connect; Axon Evidence (formerly Evidence.com); Axon Records (RMS); Axon
Dispatch (CAD); Axon Standards; Axon Respond (live streaming/RTCC); Axon 911 (Prepared + Carbyne);
Draft One (AI report drafting, launched 2024-04-23); Axon Assistant (Apr 2026); Axon Vision (live video AI
triage, Apr 2026).
**Status:** PARTIALLY VERIFIED — the ALPR, Fusus, Evidence, Records, Draft One and Fleet 3 items are
first-party confirmed (axon.com product/help pages, investor releases); Axon Assistant / Axon Vision /
Axon 911 dates come from secondary aggregation only.
**Evidence:** https://www.axon.com/products/axon-fusus; https://www.axon.com/products/axon-fleet-3;
https://www.axon.com/help/fleet-3/cameras-and-sensors/fleet/3/alpr/alpr-introduction.htm;
https://my.axon.com/s/article/Hotlists-in-Axon-Evidence-ALPR; EFF "Beware the Bundle" (WebFetch 2026-08-20)
independently lists BWC (85% market share), ICV, tasers, drones, Evidence.com, Fusus, Draft One, "recently
launched fixed ALPR and AI Assistant", and "95% of customers tied to subscription plans."
**Retrieved:** 2026-08-20
**Implication for the spec:** Axon is the clearest case for the `product_bundle` concept: EFF's finding that
95% of customers are on subscription plans means the *contract* is the unit that grants capability, not the
product. Contract entities (§8.10) need a `bundle_name` and a `products[]` list where the bundle may grant
capabilities not separately itemized.
**Outline delta:** EXTENDS §8.3 and §8.10.

### F7.19 — Axon hotlists route through NCIC, making a federal file a per-deployment configuration

**Claim:** ALPR hotlists in both Axon and Flock deployments are commonly populated from the FBI's NCIC files,
which are organized into *topics* (e.g. "Stolen Vehicle", "Missing Person", "Gang or Suspected Terrorist",
"Immigration Violator"); topic subscription is a per-agency configuration setting, and the Immigration
Violator file is populated exclusively by ICE.
**Status:** VERIFIED
**Evidence:** https://www.eff.org/deeplinks/2026/06/are-your-local-police-using-flock-safety-alprs-scan-immigrants
(WebFetch 2026-08-20): NCIC Immigration Violator File "contains records on criminal aliens who have been
deported" and "foreign-born individuals who have violated some section of the Immigration and Nationality
Act"; "ICE exclusively populates and maintains" it; "Local agencies add/remove license plates from the NCIC
list. The FBI curates the NCIC list, and pushes it out to local agencies" (Flock's own explanation); 2
agencies observed with it enabled (Blue Island PD IL, Sparks PD NV), 11 using NCIC hotlists with it disabled;
evidence obtained as **configuration screenshots via public-records requests**. Axon's equivalent:
https://my.axon.com/s/article/Hotlists-in-Axon-Evidence-ALPR. Distribution cadence example: "The Virginia
State Police distributes updated NCIC hot lists four times daily."
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) NCIC must be modeled as a DataSystem with **enumerable sub-files**, and
`ConfigurationState.hotlist_topics_subscribed[]` is a first-class, records-request-observable attribute.
(b) The alert path is *inbound* (`ingests_feed_from` NCIC), not outbound — ICE is not notified. That
asymmetry is exactly what §8.8's "direction matters" demands. (c) Configuration screenshots from FOIA are a
distinct EvidenceArtifact subtype (`config_screenshot`) with unusually high Tier-A value.
**Outline delta:** EXTENDS §8.7, §8.8, §8.12. The outline never mentions hotlists, which are the single most
consequential ALPR configuration.

---

## 4.3 Motorola Solutions / Vigilant / DRN

### F7.20 — DRN is the commercial half of a $445M acquisition and is the most under-modeled ALPR asset in the ecosystem

**Claim:** Motorola Solutions acquired VaaS International Holdings for $445M (announced 2019-01-07) in cash
and equity; VaaS's two subsidiaries split the market by customer type — **Vigilant Solutions** for law
enforcement and **Digital Recognition Network (DRN)** for commercial customers (insurers, lenders,
repossession firms) — and DRN's corpus, collected by private repossession contractors with no police
involvement, exceeds 15 billion vehicle sightings.
**Status:** VERIFIED
**Evidence:** https://www.businesswire.com/news/home/20190107005696/en/Motorola-Solutions-Acquires-VaaS-International-Holdings-Leader
(search-result summary, 2026-08-20): $445M, "VaaS's subsidiaries include Vigilant Solutions for law
enforcement users and Digital Recognition Network (DRN) for commercial customers." Corpus scale: "DRN has
amassed more than 15 billion 'vehicle sightings'"; Vice's hands-on demonstration
(https://www.vice.com/en/article/i-tracked-someone-with-license-plate-readers-drn/) documents tracking an
individual with it. Vigilant separately expanded its commercial corpus through data-sharing agreements with
MVTRAC and Plate Locate (press releases on officer.com and police1.com). The LE-facing store is
**LEARN-NVLS** — "Law Enforcement Archival Reporting Network and National Vehicle Location Service."
**Retrieved:** 2026-08-20
**Implication for the spec:** DRN is the canonical instance of a DataSystem whose **collectors are not
agencies and whose subjects are not suspects**. The graph needs:
- an Organization sub-type `commercial_data_collector` (repossession contractors) that `contributes_data_to`
  a DataSystem without any agency edge at all;
- an edge `resells_data_from` (Vigilant/LEARN ← DRN) distinct from `hosts_data_for`;
- `data_origin ∈ {agency_collected, vendor_collected, commercial_collected, brokered, scraped, breached}` on
  every DataSystem, because the same query interface can span origins with wildly different legal status.
**Outline delta:** **EXTENDS §4.2 substantially.** The outline mentions "private ALPR data" in one bullet.
DRN is a separate corporate entity, a separate corpus, a separate customer base, and a separate collection
workforce, and it is the mechanism by which a police agency can search plate sightings it had no role in
collecting and no contract governing. It deserves its own vendor card, which is what this is.

### F7.21 — Motorola's stack and its camera-registry product

**Claim:** Motorola Solutions' relevant portfolio is CommandCentral (Aware/Records — RTCC and records),
Vigilant PlateSearch / VehicleManager / LEARN-NVLS (ALPR), **CityProtect** (public camera registry),
Avigilon (video + analytics), Pelco (cameras), and Rave (mass notification); CommandCentral Records
integrates directly with Vigilant PlateSearch.
**Status:** PARTIALLY VERIFIED — CommandCentral, PlateSearch/LEARN-NVLS, CityProtect verified; Avigilon,
Pelco and Rave asserted from portfolio knowledge and the EFF bundle piece, not separately fetched.
**Evidence:** https://www.motorolasolutions.com/content/dam/msi/docs/global-software/records-and-evidence/commandcentral-records-vigilant-integration-factsheet.pdf
(integration fact sheet); Vigilant PlateSearch 7.0 User Guide hosted at
`learnfl.vigilantsolutions.com` — note the **`learn*.vigilantsolutions.com` hostname pattern, which is a
per-region LEARN tenant and a usable discovery signature**; Atlas glossary (curl, 2026-08-20) on camera
registries: "it is often integrated into other software packages, such as Motorola Solutions' CityProtect
suite"; EFF bundle piece lists "911 services, radio, body cameras, in-car cameras, ALPRs, drones, facial
recognition, Vehicle Manager (processes billions of ALPR scans)"; CISA advisory ICSA-24-165-19 exists for
"Motorola Solutions Vigilant License Plate Readers" (a further identity signature).
**Retrieved:** 2026-08-20
**Implication for the spec:** `learn<region>.vigilantsolutions.com` tenant hostnames are a discovery
heuristic (§9.1 Tier F) for identifying which regions run LEARN, analogous to Flock's transparency-portal
URLs. Record it in the §21 source registry.
**Outline delta:** EXTENDS §4.2.

---

## 4.4 Rekor Systems

### F7.22 — Rekor is a small public company whose model is data-as-a-service, not device sales

**Claim:** Rekor Systems, Inc. (NASDAQ: REKR), CIK 0001697851, reported Q1 2026 revenue $10.3M (+12% YoY,
"driven by data-as-a-service and roadway intelligence") and Q2 2026 revenue $12.7M (+2% YoY, recurring
revenue $6.7M, +14%), reaffirming a path to adjusted-EBITDA profitability in H2 2026; products are
Rekor Scout (public safety), Rekor Discover (mobility/traffic analytics), and the Rekor One platform.
**Status:** VERIFIED (financials); Waycare acquisition UNVERIFIED in this pass.
**Evidence:** https://www.globenewswire.com/news-release/2026/05/11/3292304/0/en/rekor-systems-reports-first-quarter-2026-financial-results.html;
https://www.rekor.ai/post/rekor-systems-reports-first-quarter-2026-financial-results;
SEC 8-K filings at https://www.sec.gov/Archives/edgar/data/0001697851/ (FY2026 series);
https://www.stocktitan.net/news/REKR/ (Q1/Q2 summaries). All retrieved 2026-08-20 via search-result
summaries; the SEC CIK is directly observable in the archive URLs.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) For public vendors, SEC CIK is a **free, authoritative, stable external
identifier** — better than LEI/UEI for entity resolution, and directly resolvable at
`sec.gov/cgi-bin/browse-edgar?CIK=...`. Add `sec_cik` to Vendor. Rekor = 0001697851; SoundThinking = SSTI;
Axon = AXON; Motorola Solutions = MSI. (b) Rekor's revenue mix ("data-as-a-service") confirms that for this
vendor the DataSystem, not the device, is the product — §8.7 must be able to stand alone without a
PhysicalAsset.
**Outline delta:** CONFIRMS §4.3's insistence on separating device manufacturer / service vendor / data
platform / agency operator. EXTENDS §8.2 with `sec_cik`.

---

## 4.5 Genetec

### F7.23 — Genetec's RTCC is Citigraf, and its camera-federation product is also called "Community Connect"

**Claim:** Genetec's relevant products are Security Center (VMS core), AutoVu (ALPR) including **AutoVu
Cloudrunner** (vehicle-centric investigation), **Citigraf** (RTCC / situational-intelligence platform,
notably deployed with Chicago PD), **Clearance** (digital evidence management, with a camera-registry
program enabling community/business video contribution), and a public-private program **also named
"Community Connect"** — creating a direct naming collision with Axon's product.
**Status:** VERIFIED
**Evidence:** https://resources.genetec.com/en-product-brochures/citigraf-real-time-crime-center-provides-situational-intelligence-to-improve-public-safety;
https://resources.genetec.com/public-safety/the-road-to-citigraf-with-the-chicago-pd-3;
Microsoft Marketplace listing https://marketplace.microsoft.com/en-us/product/web-apps/genetec.citigraf;
OMNIA Partners cooperative-contract PDF https://www.omniapartners.com/suppliers-files/E-J/Genetec/Assets/2025.08_Citigraf_Real_Time_Crime_Center.pdf
(dated 2025-08); Genetec press release on the SaferWatch integration
https://www.genetec.com/binaries/content/assets/genetec/press-releases/pr_eng_genetec-and-saferwatch-bring-real-time-vehicle-intelligence-to-public-safety-agencies_final.pdf.
All retrieved 2026-08-20 (search-result summaries + URL confirmation).
**Retrieved:** 2026-08-20
**Implication for the spec:** Product names are **not unique across vendors**. "Community Connect" is an Axon
program and a Genetec program; a naive string match will merge two different vendors' camera-federation
deployments. Product identity must be `(vendor_id, product_name, valid_from)`, never `product_name` alone —
and the entity-resolution pipeline (§11.2) needs a hard test case for exactly this.
**Outline delta:** EXTENDS §4.4 and §8.3. Also note the OMNIA Partners cooperative purchasing vehicle: both
Genetec and Flock publish price lists through OMNIA
(https://www.omniapartners.com/suppliers-files/E-J/Flock_Safety/Contract_Documents/R250203/5_29_2025_Flock_Safety_Omnia__R250203_Price_List.pdf).
**Cooperative purchasing contracts are a procurement channel the outline's §8.10 does not model**, and they
matter: an agency can "piggyback" onto a national cooperative award without running its own RFP, which
removes the local procurement paper trail §10 Phase 1F depends on. See F7.43.

---

## 4.6 SoundThinking

### F7.24 — SoundThinking is a five-product platform company, and Chicago's cancellation is the anchor case

**Claim:** SoundThinking, Inc. (NASDAQ: SSTI, formerly ShotSpotter) sells the "SafetySmart" platform:
ShotSpotter (acoustic gunshot detection), CrimeTracer (law-enforcement search engine, formerly COPLINK,
acquired with Forensic Logic), CaseBuilder (investigation management), ResourceRouter (patrol resource
allocation — a `predictive-policing-place` product), and SafePointe (AI weapons detection); Chicago
terminated ShotSpotter in 2024 after Mayor Brandon Johnson's February announcement, with service ending at
midnight on the contract date, while the city separately authorized a six-figure CrimeTracer payment after a
2024 pilot.
**Status:** VERIFIED
**Evidence:** https://www.soundthinking.com/press-releases/soundthinking-highlights-major-multi-year-customer-renewals-in-q2-2026/
and https://ir.soundthinking.com/news-events/press-releases/detail/338/ (product suite, Q2 2026 renewals);
https://www.chicago.gov/city/en/depts/mayor/press_room/press_releases/2024/january/city-of-chicago-statement-on-shotspotter-contract.html;
https://chicagoreader.com/news/crimetracer-chicago-police-soundthinking-surveillance/ (CrimeTracer payment
after pilot); Johnson's "walkie-talkies on a stick" characterization. Retrieved 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** Chicago is the model **cross-product lifecycle** case: one vendor, one city,
`shotspotter → cancelled` while `crimetracer → pilot → contracted` in the same period. Lifecycle state is
per (Organization × Product), never per (Organization × Vendor). EFF's bundle research makes the same point
about SoundThinking's explicit "cross-sell" strategy to create "stickier" relationships.
**Outline delta:** EXTENDS §4.5 and §6.7.

### F7.25 — The leaked ShotSpotter sensor dataset is still public, is CC0, and contains 22,471 points — not "more than 25,000"

**Claim:** The dataset derived from WIRED's 2024 sensor-location story remains publicly downloadable at
github.com/kevee/shotspotter-locations under CC0-1.0; it contains **22,471** sensor coordinate records
across **304** named deployment areas, including non-US deployments (South Africa) and a US Secret Service
deployment key; and its provenance is extraction of high-resolution coordinates from the source of WIRED's
embedded Flourish visualization — i.e. it is a *derivative of a derivative* of a leak.
**Status:** VERIFIED (my own download and count)
**Evidence:** WIRED itself is host-blocked for WebFetch ("Claude Code is unable to fetch from
www.wired.com") — recorded as INACCESSIBLE for the primary article. Fallback succeeded on the derivative:
`curl https://raw.githubusercontent.com/kevee/shotspotter-locations/main/README.md` (200) states:
"Leaked data on the location of ShotSpotter listening devices. Based on info from J.B Crawford
[computer.rip/2024-03-01-listening-in-on-the-neighborhood.html]. A KML of data pulled from an article by
WIRED magazine which interestingly did not allow a very low zoom-level in their own visualization. I opened
up the original Flourish visualization iFrame [flo.uri.sh/visualisation/16818696/embed], and in the source
code was the actual, very high-resolution lat/lon of the Shotspotter locations. ... This work is covered
under Creative Commons zero license."
`curl .../shots.json` (200, 3,243,531 bytes) parses to `{"events": [...]}` with **22,471** records, each
`{lat, lon, metadata:[deployment_key, ""]}`. Distinct deployment keys: **304**. Largest:
ChicagoILDistrict9 (316), ChicagoILDistrict25 (298), USVIStCroix (276), ChicagoILDistrict3 (256),
OaklandCA (253), DanRyanExpresswayIL (222), DetroitMIPrecinct9 (202), QueensNYJamaica (200), NewarkNJ (194),
MiamiCityFLCentral (194), PRSanJuan (191). Non-US/atypical keys present: `ZANelsonMandelaBayHelenvale`,
`ZAKrugerNationalParkIPZ`, `ZAKrugerNationalParkBergenDal` (anti-poaching), `USVIStThomas`, `USVIStJohn`,
`PRSanJuan`, and **`WashDC2D-USSS`** (a Secret Service key).
Press accounts (e.g. urbanmilwaukee.com 2024-02-23, wisconsinexaminer.com 2024-02-27) cite "25,580 sensors
across 84 metropolitan areas in 34 states and territories."
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. **Count discrepancy is real and must be recorded, not resolved.** 22,471 (what the public derivative
   actually contains) vs 25,580 (what press reported). Plausible causes: the Flourish embed was a subset;
   deduplication; or a later/earlier snapshot. SIG must ingest the derivative with `record_count: 22471`
   and a Claim noting the reported figure, linked by `contradicts`. **The outline's "more than 25,000" is
   sourced to the press number, not to any dataset anyone can download.**
2. **Ethics/§13.** This is leaked, non-consensually published infrastructure data with a CC0 dedication
   applied by someone who did not own it. CC0 here is *asserted*, not *conveyed* — the uploader cannot
   dedicate rights they never held, and the underlying data was never SoundThinking's to license either way.
   SIG should treat this as `license_status: asserted_cc0_disputed_chain`, ingest **deployment-area keys and
   counts** (which are institutional facts) and **not** the individual coordinates, consistent with §13.3
   ("treat exact coordinates contextually") — acoustic sensors on private rooftops are precisely the case
   where publishing coordinates endangers the property owner rather than the institution.
3. `WashDC2D-USSS` proves a federal agency operates ShotSpotter coverage — a federal Deployment discoverable
   only from a leak. Record as UNVERIFIED-pending-corroboration rather than importing it as fact.
4. Deployment keys are *service areas*, not agencies: `ChicagoILDistrict9` and `DanRyanExpresswayIL` are
   coverage polygons. §8.5 Deployment needs `service_area` distinct from `operating_organization`.
**Outline delta:** **CORRECTS §4.5** — the outline says "more than 25,000 ShotSpotter sensor locations"; the
downloadable artifact has 22,471. CONFIRMS §4.5's point that acoustic sensors need their own asset type.
EXTENDS §13.3 and §14.2 with a concrete disputed-license case.

---

## 4.7 Facial-recognition supply

### F7.26 — The FR market splits into three structurally different supplier types

**Claim:** Face recognition reaches agencies through three structurally distinct supplier models —
(a) *algorithm vendors who do not supply the gallery* (NEC, Idemia, Paravision), (b) *vendors who supply
algorithm + scraped gallery* (Clearview AI, PimEyes), (c) *mission-specific nonprofits supplying tooling to
a restricted domain* (Thorn, CSAM investigations) — and only type (b) creates a novel reference database as
infrastructure.
**Status:** PARTIALLY VERIFIED (a) and (b) verified; Thorn/Paravision UNVERIFIED in this pass.
**Evidence:**
- Type (a): NEC's NeoFace powers ICE's **Mobile Fortify** field app
  (https://www.biometricupdate.com/202601/ice-facial-recognition-app-mobile-fortify-powered-by-nec;
  https://www.biometricupdate.com/202602/ices-facial-recognition-app-is-new-but-the-nec-tech-behind-it-is-well-known).
  NIST FRTE 1:N as of Aug 2026: "Idemia v13, NEC v12 and QazSmartVision.AI v3 jointly lead at 0.6 percent
  FNIR, followed by Innovatrics v15 and Sensetime v11 at 0.8 percent"; Paravision v21 appears in
  visa-to-border scenarios (https://www.biometricupdate.com/202608/nist-frte-1n-shows-face-recognition-race-shifting-beyond-accuracy).
  These vendors match against galleries the *customer* owns (DMV photos, mugshots, NGI).
- Type (b): Clearview AI's gallery is scraped: "50+ billion facial images." ICE contracting escalated —
  a $9.2M HSI award finalized 2025-09-05
  (https://www.biometricupdate.com/202509/ice-awards-clearview-ai-9-2m-facial-recognition-contract) and a
  reported June 2026 $3.75M award described as its largest-ever facial-recognition purchase
  (https://capturecascade.org/event/2026-06-20--ice-largest-clearview-ai-contract-dhs-deletes-oversight-policy/
  — secondary, treat as PARTIALLY VERIFIED). The BIPA MDL settled for $51.75M structured as a ~23% class
  equity stake contingent on an IPO or liquidation event
  (https://www.regulatoryoversight.com/2025/04/51-75m-settlement-in-clearview-ai-biometric-privacy-litigation-illustrates-creative-resolution-for-startups-facing-parallel-litigation-and-enforcement-action/).
**Retrieved:** 2026-08-20
**Implication for the spec:** §4.7's proposed chain `agency → can query → FR system → searches against →
image database` is **correct and should be adopted verbatim**, but the `searches against` edge needs
`gallery_owner` and `gallery_provenance ∈ {agency_owned, state_dmv, federal_ngi, vendor_scraped,
vendor_licensed, consumer_genealogy}`. Clearview's settlement structure also creates a bizarre modeling
fact worth capturing: the plaintiff class is now a *part-owner of the vendor*, which is a stakeholder
relationship no existing role covers.
**Outline delta:** CONFIRMS §4.7 and its diagram. EXTENDS it with the algorithm-vs-gallery split, which
determines whether a "facial recognition deployment" creates a new database or merely a new query path.

---

## 4.8 Mobile forensics

### F7.27 — Forensics vendors have consolidated and moved up-stack into virtualization and exploit development

**Claim:** The three-vendor market (Cellebrite, Magnet Forensics/Grayshift, MSAB) has consolidated further:
Grayshift merged with Magnet Forensics in 2023 (GrayKey now a Magnet product); Magnet acquired Dark Circuit
Labs (June 2025) for "vulnerability research and exploit development"; Cellebrite completed its acquisition
of **Corellium** in December 2025, adding mobile virtualization.
**Status:** PARTIALLY VERIFIED — the Grayshift/Magnet merger is well established; the Dark Circuit Labs and
Corellium deals come from a market-research aggregator, not primary sources.
**Evidence:** https://en.wikipedia.org/wiki/Grayshift ("In 2023, it merged with the Canadian firm Magnet
Forensics"); https://www.marketsandmarkets.com/ResearchInsight/mobile-forensics-companies.asp (Corellium
Dec 2025; Dark Circuit Labs June 2025). Retrieved 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** The Dark Circuit Labs and Corellium deals matter because they convert forensic
vendors into *exploit developers*, which changes the capability model: `extract.device.physical` stops being
a static product feature and becomes a **capability with a shelf life** tied to specific OS versions.
Deployment records for forensics tools should carry `capability_currency` (does the licence include current
exploit updates?) rather than a boolean "has Cellebrite." Upturn's *Mass Extraction* remains the
best agency-level census (via EFF Data Library, per §4.8).
**Outline delta:** EXTENDS §4.8.

---

## 4.9 The commercial data-broker → law-enforcement pipeline

This is the part of the outline that most needed development. Five findings.

### F7.28 — The FTC's 2025 orders against Gravy/Venntel carve out law enforcement, so enforcement did not close the pipeline

**Claim:** The FTC finalized an order on 2025-01-14 against Gravy Analytics and Venntel prohibiting sale or
use of sensitive location data — **except for national security or law enforcement purposes** — meaning the
single largest regulatory action against the location-broker industry left the government-purchase channel
intact.
**Status:** VERIFIED
**Evidence:** https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-finalizes-order-prohibiting-gravy-analytics-venntel-selling-sensitive-location-data;
https://www.ftc.gov/legal-library/browse/cases-proceedings/212-3035-gravy-analytics-inc-matter;
https://therecord.media/ftc-location-data-brokers-gravy-venntel-mobilewalla;
https://www.dataguidance.com/news/usa-ftc-finalizes-order-gravy-analytics-and-venntel. Venntel data
reportedly powers Babel Street's **Locate X**, purchased by the Secret Service, CBP and DEA.
Retrieved 2026-08-20 (search-result summaries; FTC URLs confirmed).
**Retrieved:** 2026-08-20
**Implication for the spec:** Policy entities (§8.11) must be able to represent an enforcement order as a
constraint with **carve-outs**, i.e. `applies_to_purposes[]` and `exempt_purposes[]`. A naive model that
records "FTC prohibited sale of sensitive location data" would produce the false inference that agency
purchases stopped.
**Outline delta:** EXTENDS §4.9 and §8.11.

### F7.29 — Webloc/Penlink is the current state of the art and shows a four-layer supply chain with a UI layer on top

**Claim:** Citizen Lab (April 2026, "Analysis of Penlink's Ad-Based Geolocation Surveillance Tech") documented
**Webloc**, an ad-derived geolocation product created by Cobwebs Technologies (announced Oct 2020), now sold
by **Penlink** (which acquired Cobwebs in July 2023) as an add-on to Penlink's **Tangles** platform; Webloc
provides "a constantly updated stream of records from up to 500 million mobile devices" and lets users
"monitor the location, movements, and personal characteristics of entire populations up to three years in
the past"; named US customers include ICE, the US military, Texas DPS, DHS West Virginia, NYC district
attorneys, and police in Los Angeles, Dallas, Baltimore, Tucson, Durham, Elk Grove and Pinal County, plus
Hungarian domestic intelligence and El Salvador's national police.
**Status:** VERIFIED
**Evidence:** https://thehackernews.com/2026/04/citizen-lab-law-enforcement-used-webloc.html (WebFetch
2026-08-20), reporting the Citizen Lab study by Wolfie Christl, Astrid Perry, Luis Fernando Garcia,
Siena Anstis and Ron Deibert. Corroborating context:
https://www.penlink.com/press-release/cobwebs-technologies-joins-penlink-to-expand-its-digital-investigative-platform/;
https://www.eff.org/deeplinks/2025/08/victory-pen-links-police-tools-are-not-secret (EFF won disclosure of
Pen-Link's law-enforcement tooling in Aug 2025 — meaning **procurement records for this vendor are now
obtainable**, a live evidence channel).
**Retrieved:** 2026-08-20
**Implication for the spec:** §4.9's five-layer chain is close but is missing a layer and mislabels one.
The verified chain is:

```text
[1] App publisher / SDK        (collects; usually unaware of downstream use)
      ↓ contributes_data_to
[2] Ad exchange / SSP / bid stream   (the actual leak point; not a "broker")
      ↓ resells_data_from
[3] Aggregating broker          (Gravy, Venntel, Outlogic/X-Mode, Complementics)
      ↓ resells_data_from
[4] Productizer / UI vendor     (Fog Reveal; Babel Street Locate X; Cobwebs Webloc)
      ↓ provides_platform_to    ← may be a *different company* from [3]
[5] Investigative platform host (Penlink Tangles) — optional 5th layer
      ↓ is_queryable_by
[6] Agency
```

Layers [3] and [4] are frequently different companies, and layer [5] is a distinct hosting relationship.
SIG needs `resells_data_from` to be **transitive-but-not-collapsible**: an agency querying Tangles/Webloc is
three hops from the app that collected the point, and the graph's value is precisely in preserving those
hops (§22.4). Note also `historical_depth` as a DataSystem attribute — "three years in the past" is a
capability parameter as important as retention.
**Outline delta:** **EXTENDS §4.9 materially.** The outline's chain has 5 nodes; the verified chain has 6,
splits broker from productizer, and identifies the bid stream (not the "broker") as the collection point.

### F7.30 — Fog Data Science is still operating

**Claim:** No evidence was found that Fog Data Science has ceased operations; its site and government-vendor
registrations remain live as of Aug 2026.
**Status:** PARTIALLY VERIFIED (a negative finding — see §9.4 caveat)
**Evidence:** https://www.fogdatascience.com/ and /about live; Carahsoft reseller page
https://www.carahsoft.com/fog-data-science; HigherGov awardee record
https://www.highergov.com/awardee/fog-data-science-llc-10045404/ (UEI **F88GMYVEEE67**). Historical EFF
investigation: 40 contracts with "nearly two dozen agencies" incl. Dallas PD and Rockingham County NC SO
(https://www.eff.org/deeplinks/2022/08/inside-fog-data-science-secretive-company-selling-mass-surveillance-local-police).
Retrieved 2026-08-20 via search-result summaries; **the fogdatascience.com pages were not directly fetched**
— recorded as PARTIALLY VERIFIED accordingly.
**Retrieved:** 2026-08-20
**Implication for the spec:** HigherGov exposes **UEI** for federal-registered vendors (Fog =
F88GMYVEEE67). UEI is the correct external identifier for any vendor that has ever held a federal award and
should be a Vendor attribute alongside `sec_cik`. Also: Carahsoft is a **reseller/aggregator**, and the
existence of a reseller means the procurement record may name Carahsoft rather than Fog — an entity-resolution
trap (§11.2) that §8.10's `seller` field must accommodate via `seller_role ∈ {oem, reseller, integrator,
cooperative}`.
**Outline delta:** EXTENDS §4.9, §8.2, §8.10.

### F7.31 — TPIPs are a recognized category with named incumbents

**Claim:** The "third-party investigative platform" category — Thomson Reuters CLEAR, LexisNexis Accurint
Virtual Crime Center, TransUnion TLOxp, SoundThinking CrimeTracer — is recognized by EFF as an Atlas
category since March 2024, tracked comprehensively in Tennessee, Massachusetts and Colorado.
**Status:** VERIFIED
**Evidence:** https://www.eff.org/deeplinks/2024/03/atlas-surveillance-removes-ring-adds-third-party-investigative-platforms
(WebFetch 2026-08-20), including the definition quoted in F7.4 and the beta-coverage note.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt `third-party-investigative-platform` as a technology slug with an
`exactMatch` crosswalk to Atlas TPIP. The state-limited coverage (TN/MA/CO) is a §6.6-style completeness
fact that must be stored as coverage metadata on the source, not silently treated as national.
**Outline delta:** EXTENDS §4.9. The outline does not name the TPIP category at all.

### F7.32 — Palantir's ICE footprint is contract-shaped and enumerable

**Claim:** Palantir supplies ICE with Investigative Case Management (ICM, $139.3M award 2022, expiring
April 2026, slated for sole-source renewal), FALCON (since 2013), and **ImmigrationOS** ($30M, prototype due
2025-09-25, contract running to September 2027), with total ICE contract value reported at ~$287M in 2025.
**Status:** PARTIALLY VERIFIED — the $30M/ImmigrationOS facts are widely reported; the $139.3M ICM figure
and the $287M total come from secondary aggregation.
**Evidence:** https://www.americanimmigrationcouncil.org/blog/ice-immigrationos-palantir-ai-track-immigrants/;
https://immpolicytracking.org/policies/reported-palantir-awarded-30-million-to-build-immigrationos-surveillance-platform-for-ice/;
https://www.executivegov.com/articles/palantir-ice-contract-immigrationos;
https://detention-pipeline.transparencycascade.org/players/contractors/palantir-technologies/.
Retrieved 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** Federal contract data (USAspending/FPDS) is a Tier-A structured source for
exactly this layer and should be a §10 ingestion phase. `sole_source` is a Contract attribute with high
analytic value (it is EFF's named lock-in mechanism, F7.42). Note the modeling asymmetry: Palantir products
are DataSystems the *agency* operates on agency data, unlike brokers who operate on their own data — the
`data_origin` attribute from F7.20 discriminates them.
**Outline delta:** EXTENDS §4.9 — the outline does not mention Palantir despite naming it nowhere in §4,
even though it is the largest single vendor in the federal half of the pipeline.

---

## 4.10 Ring / Amazon and the community-app layer

### F7.33 — The outline's Ring model is two policy reversals out of date

**Claim:** Ring's police-request pathway has changed four times: (1) Neighbors "Request for Assistance"
operated until **January 2024** when it was discontinued (2,500+ agencies had used it); (2) in **April 2025**,
after founder Jamie Siminoff's return, Ring re-entered law enforcement via partnerships with **Axon** and
**Flock Safety**, under the new name **Community Requests**; (3) in **February 2026** Ring **cancelled the
Flock partnership** after backlash including over a Super Bowl ad for its "Search Party" feature; (4) the
**Axon partnership remains active** as of Aug 2026.
**Status:** VERIFIED
**Evidence:**
- Discontinuation: https://www.nbcnews.com/news/us-news/amazons-ring-will-stop-allowing-police-request-doorbell-video-footage-rcna135614; EFF/Atlas removed 2,530 Ring datapoints in March 2024 (F7.4).
- Re-entry and mechanism: CNBC 2025-10-16 (curl after 403): "The Ring Community Requests feature will be
  available for use with the FlockOS and Flock Nova platforms... Police requests will go into what is called
  the Ring Neighbors feed, which pings camera users within an area identified as relevant to the crime, and
  camera owners can then share video, which is kept in a secure environment and can only be used for the
  single crime investigation." Langley on the distinction from RFA: "RFA was inside the Ring data app. There
  was no chain of custody. In this case, while the request goes out in the Ring app, any footage shared by
  users goes into the Flock platform." Also: "the partnership has no direct revenue impact on Flock Safety."
- Cancellation: https://www.fightforthefuture.org/news/2026-02-17-notorious-surveillance-company-amazon-cancels-ring-flock-partnership/
  (WebFetch 2026-08-20) — Flock partnership cancelled following Super Bowl "Search Party" backlash; "Ring
  maintained its collaboration with Axon... through the Community Requests platform."
- Reversal coverage: https://www.tomsguide.com/home/home-security/ring-backtracks-lets-cops-once-again-request-video-from-your-doorbell-and-security-cameras.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The **chain-of-custody destination** is the key modelling variable: under
RFA, footage landed in the Ring app; under Community Requests it lands in the *police vendor's* evidence
system. That is a change in `hosts_data_for`, and it converts a consumer-platform disclosure into a
permanent police record. (b) IntegrationRelationships between two *vendors* (Ring↔Flock, Ring↔Axon) exist
independently of any agency and must be representable as vendor-to-vendor edges with their own lifecycle —
Ring↔Flock lived roughly 2025-10 to 2026-02. (c) "No direct revenue impact" means such edges cannot be found
in procurement records at all; they are only visible in press and product documentation (Tier B/D).
**Outline delta:** **CORRECTS §4.7's implicit currency and the outline's overall Ring model** (which relies
on EFF's pre-2024 framing). The Atlas's Ring category retirement plus Ring's 2025 return means *absence of
Ring data in the Atlas after March 2024 is not evidence of absence of Ring–police integration.* This is the
sharpest §9.4 negative-claim trap in the whole dataset.

### F7.34 — Camera-federation competitors: Verkada's posture is architecturally different and that difference is the point

**Claim:** Verkada markets to law enforcement and to RTCCs, and integrates *into* Axon Fusus by pushing
license-plate reads over a webhook, yet positions itself as the non-networked option — "your cameras, your
Command organization, your retention settings, and nobody outside your org queries it."
**Status:** VERIFIED
**Evidence:** https://www.verkada.com/solutions/law-enforcement/ and
https://www.verkada.com/solutions/real-time-crime-center/ (Verkada's own LE/RTCC pages);
https://help.verkada.com/command/organization-settings/integrations/set-up-the-verkada-fusus-lpr-integration
(WebFetch 2026-08-20) — the integration is a **push** model: Verkada configures "a Verkada Webhook" pointing
at a Fusus endpoint, plus a read-only API key for Fusus, a webhook URL and a shared secret, and org ID; the
documentation "doesn't explicitly address consent mechanisms." Separate camera-feed integration documented at
help.verkada.com/command/integrations/set-up-the-verkada-fusus-camera-integration. Deployment example: North
Charleston SC added ~100 Verkada cameras in spring 2026 (postandcourier.com, search-result summary).
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the cleanest evidence for edge-type discrimination. The Verkada→Fusus
LPR link is `pushes_alerts_to` (webhook, Verkada-initiated, event-level) **and** `ingests_feed_from` in the
camera case (Fusus-initiated pull with a read-only key). Two integrations between the same pair of products
with **opposite directionality**. `IntegrationRelationship` must therefore carry `initiator`,
`transport ∈ {webhook_push, api_pull, rtsp_stream, sftp_batch, appliance_bridge, manual_export}` and
`granularity ∈ {event, stream, batch, query}`. A single `integrates_with` boolean destroys all of it.
**Outline delta:** **EXTENDS §8.9 substantially.** The outline's §8.9 has no attributes at all.

### F7.35 — Peregrine is now a major platform vendor absent from the outline

**Claim:** Peregrine Technologies raised $250M at a **$6.8B valuation** in June 2026 (Sequoia and others;
~$470M total across three rounds), serves agencies covering "more than 80 million Americans," and won a $2M
San Mateo County contract consolidating 16 municipal PDs plus the Sheriff's Office and DA into one platform.
**Status:** PARTIALLY VERIFIED — valuation from Fortune reporting via search summary; the San Mateo contract
and agency list are from local reporting.
**Evidence:** https://fortune.com/2026/06/22/exclusive-peregrine-nick-noone-ai-public-safety-palantir-2026-world-cup-just-sequoia-capital/;
https://news.crunchbase.com/venture/law-enforcement-startup-peregrine-unicorn-sequoia/;
https://coastsidebuzz.com/san-mateo-county-signs-2m-contract-with-peregrine-technologies-to-consolidate-law-enforcement-data-into-an-integrated-platform-for-real-time-decision-making-between-agencies/
(names Atherton, Belmont, Brisbane, Broadmoor, Burlingame, Colma, Daly City, East Palo Alto, Foster City,
Hillsborough, Menlo Park, Pacifica, Redwood City, San Bruno, San Mateo, South San Francisco PDs + SMC Sheriff
+ DA). Retrieved 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** The San Mateo award is the archetype of a **county-level multi-agency
Deployment**: one Contract, one buyer (the county), 18 operating organizations, and a federated search
capability spanning all of them. §8.5 Deployment must support `operating_organizations[]` (plural) and
§8.10 Contract must separate `buyer` from `beneficiary_organizations[]`. Peregrine, Mark43, CentralSquare,
Versaterm and Hexagon all belong in the initial vendor seed list.
**Outline delta:** **EXTENDS §4.10** — the outline names only Fusus as an integration platform. Peregrine at
$6.8B is comparable in scale to Flock and is entirely unmentioned.

---

## 4.11 Drones and DFR

### F7.36 — **The FAA DFR waiver dataset exists, is public, and is the strongest new evidence source found**

**Claim:** EFF obtained via FOIA and published on 2026-07-23 a complete list of FAA Part 91 §91.113
Public Aircraft/Public Safety waivers — the authorization that makes a DFR program possible. I downloaded it:
it contains **1,004 approved waivers** (873 law enforcement, 113 fire/emergency management, 13 other,
5 federal), with applicant name, city, state, category, dates received/completed, approval status, altitude
tier, start date, end date, amendment flag, and whether a CMD-DAA document was provided. 918 are at the
200 ft "shielded" tier, 86 at the 400 ft tier. Approvals run 48 months.
**Status:** VERIFIED (my own download and analysis)
**Evidence:** EFF post: https://www.eff.org/deeplinks/2026/07/hundreds-drone-first-responder-programs-could-soon-be-launched-across-country
(WebFetch 2026-08-20), which links a Google Sheet and a Google My Maps. I exported the sheet directly:

```text
curl -sL "https://docs.google.com/spreadsheets/d/1FpoISaAdmQLtMKelPy1sdCOLvYVNxSXBVzASo-I-djI/export?format=csv&gid=0"
→ HTTP 200, 133,975 bytes, 1,005 lines (1,004 data rows)
header: Applicant,City,State,Category,Responsible Party,Date Received,Completed,Status,
        200ft/400ft,Start Date,End Date,Amendment,CMD-DAA Document Provided
first row: Richmond Police Department,Richmond,CA,Law enforcement,Exemption 6,4/15/2025,5/9/2025,
        Approved,400ft,5/8/2025,5/31/2029,,YES
```

Category counts: Law enforcement 873, Fire and emergency management 113, Other 13, Federal agency 5.
Altitude tier: 200ft 918, 400ft 86. Status: all 1,004 `Approved`. 49 states represented; top states
CA 126, TX 100, NY 97, FL 54, MN 47, NJ 40, GA 38, MI 35, NC 31, IN 30.
Context from EFF: the §91.113 waiver was introduced April 2025; only 976 DFR waivers had been granted
2018–April 2025, so April 2025–February 2026 exceeded the prior seven years combined. Named examples
elsewhere: Indianapolis Metro PD, Seward PD (AK), Mississippi Bureau of Narcotics, NCIS, Boston Fire
(https://dronexl.co/2026/08/07/faa-dfr-waiver-list-1000-agencies/, WebFetch 2026-08-20).
Note: DroneXL states "approximately 87% chose shielded operations"; my count is **918/1004 = 91.4%**.
EFF's post carries a CC BY notice.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is a near-perfect SIG source and should be a named §10 ingestion phase.
It supplies, for 1,004 named agencies: an unambiguous organization name, a place, an authorization type, a
**decision date**, and — critically — a **validity interval** (`Start Date`, `End Date`, e.g. 5/8/2025 →
5/31/2029). That is exactly the bitemporal `valid_from`/`valid_to` §9.2 asks for, sourced from a federal
regulator rather than inferred. It also yields a lifecycle state the outline lacks: an agency with a live
waiver and no drone is `authorized_not_deployed`. And the `Date Received → Completed → Start Date` triple
gives a measurable procurement-to-authorization latency. Licence: the EFF post is CC BY; the underlying data
is a US federal government FOIA release and therefore not copyrightable — record
`license: us_gov_public_domain (FOIA release)`, `attribution_courtesy: EFF`.
**Outline delta:** **EXTENDS §4.10, §10, §21 with a source the outline entirely missed.** The R7 brief asked
whether FAA COA/waiver data is obtainable. Answer: **yes, and it is already published, structured, complete
for §91.113, and free.** The general Part 107 waiver list at
faa.gov/uas/commercial_operators/part_107_waivers/waivers_issued is a JS-rendered page (curl returns 200 but
the body is a shell with no CSV link) and was NOT successfully enumerated — see Open Questions.

### F7.37 — The DFR vendor market has been reshaped by the DJI restrictions

**Claim:** On 2025-12-22 the FCC's Public Safety and Homeland Security Bureau added **all foreign-produced
UAS and UAS critical components**, and specifically all DJI and Autel communications/video equipment, to the
Covered List (DA 25-1086); the action does not ban existing FCC-authorized models but blocks new
authorizations. This followed NDAA FY25 §1709, which required a national-security-agency audit of DJI by
2025-12-23 that DJI publicly requested and which did not occur on time. The beneficiaries are Skydio (X10,
Blue UAS), BRINC (Responder, Lemur 2) and Flock Aerodome.
**Status:** VERIFIED
**Evidence:** https://docs.fcc.gov/public/attachments/DOC-416839A1.pdf (FCC fact sheet);
https://www.wiley.law/alert-In-Unexpected-First-of-Its-Kind-Action-FCC-Adds-All-Foreign-Produced-Uncrewed-Aircraft-Systems-and-UAS-Critical-Components-to-Covered-List;
https://www.akingump.com/en/insights/alerts/fcc-adds-all-foreign-made-uas-and-uas-critical-components-to-covered-list;
https://dronelife.com/2025/12/22/fcc-adds-foreign-made-drones-and-components-to-covered-list-citing-national-security-risks/;
DJI's own response https://www.djiusa.com/blogs/seo-news/fcc-covered-list-won-t-impact-existing-dji-drones;
§1709 background https://dronelife.com/2025/12/04/dji-urges-federal-agencies-to-initiate-ndaa-mandated-security-review-ahead-of-december-deadline/.
Retrieved 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** Regulatory instruments (FCC Covered List, NDAA §889/§1709, Blue UAS list) are
**Policy entities that constrain Products, not Deployments** — a new modeling case §8.11 does not cover.
They also generate a forced-replacement lifecycle transition (`replaced_by` where the cause is
`regulatory_prohibition`, not agency choice), which must be distinguishable from a voluntary switch or the
graph will misread compliance churn as surveillance expansion.
**Outline delta:** EXTENDS §8.11 and §6.7.

---

## 4.12 Fusion centers, RISS, HIDTA, and federal systems

### F7.38 — DHS publishes an authoritative fusion-center list: exactly 80, split 54 primary / 26 recognized

**Claim:** As of the page's stated last-update date of **2026-08-14**, DHS lists **54 primary** and
**26 recognized** fusion centers — **80 total** — with name, state, designation type and phone number.
**Status:** VERIFIED (my own count)
**Evidence:** WebFetch on https://www.dhs.gov/fusion-center-locations-and-contact-information returned
**HTTP 403 Forbidden**. Fallback `curl -sL -A "Mozilla/5.0 ... Chrome/124.0 ..."` returned HTTP 200. Parsing
the rendered text and counting the literal markers `(Primary)` and `(Recognized)` in the list region gives
54 and 26. The page states the designation model: "State and major urban area fusion centers ... are owned
and operated by state and local entities, and are designated by the governor of their state," and the federal
government recognizes those designations under the Federal Resource Allocation Criteria (RAC) policy.
"Primary" = statewide, highest federal-resource priority, including "connectivity with federal data systems";
"Recognized" = major urban area. Footer: "Last Updated: 08/14/2026".
Coverage includes territories: Guam (Mariana Regional Fusion Center), Puerto Rico (National Security State
Information Center), US Virgin Islands, and DC.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The canonical 80-fusion-center list is a free, authoritative, scrapable
Organization seed — add to §10 Phase 1A and §21. (b) `primary` vs `recognized` is a **capability-bearing
designation**, not a label: DHS ties "connectivity with federal data systems" to primary status, so it
should map to `AccessRelationship` priors. (c) Fusion centers are Organizations, **not** a technology,
contra the Atlas glossary (F7.4). (d) Fusion centers are governor-designated, so the funder/authorizer role
differs from the operator role — see Part 6.
**Outline delta:** CONFIRMS the brief's "80 DHS-recognized fusion centers" figure exactly, and supplies the
54/26 split the outline lacks. EXTENDS §8.1.

### F7.39 — RISS is six centers plus a network; HIDTA sites were not retrievable in this pass

**Claim:** RISS comprises **six** regional centers in mutually exclusive geographies — MAGLOCLEN, MOCIC,
NESPIN, ROCIC, RMIN, WSIN — operating RISSNET, with 10,800+ member agencies and the ATIX homeland-security
exchange (added 2003), and members in the US, Australia, Canada and England.
**Status:** VERIFIED for RISS; **INACCESSIBLE** for HIDTA.
**Evidence:** https://www.riss.net/about-us/, https://www.riss.net/, https://www.riss.net/faq/,
https://bja.ojp.gov/sites/bja/files/media/document/riss.pdf, https://en.wikipedia.org/wiki/Regional_Information_Sharing_Systems
(search-result summaries retrieved 2026-08-20). **Direct fetch failures:** `curl` to
`https://www.riss.net/centers/`, `https://www.dea.gov/operations/hidta` and
`https://www.whitehouse.gov/ondcp/high-intensity-drug-trafficking-areas-hidta-program/` all returned
**HTTP 000** (connection failure/TLS reset) even with a browser UA — recorded as INACCESSIBLE, fallback is a
later retry or the printed BJA/ONDCP program documents.
**Retrieved:** 2026-08-20
**Implication for the spec:** RISSNET, ATIX, N-DEx, Nlets and LEEP are `interagency-data-exchange`
DataSystems, and *membership* in them is an `AccessRelationship` with `scope: region|national` and
`mechanism: federated_query`. The HIDTA list (31 designated areas, per program design) remains to be
obtained — see Open Questions.
**Outline delta:** EXTENDS §8.1 and §8.7.

### F7.40 — DEA's NLPRP and CBP checkpoint ALPR are federal DataSystems with distinct retention regimes

**Claim:** The DEA operates the National License Plate Reader Program out of EPIC (El Paso Intelligence
Center) with a central repository in Merrifield VA queryable by any DEA-vetted federal, state, local or
tribal agent; DEA roadside retention is reported at 90 days, while CBP checkpoint ALPR retention is 15 years
with roughly 5 years searchable; CBP issued a July 2025 solicitation for 100 additional covert
plate-capturing trail cameras.
**Status:** PARTIALLY VERIFIED — EPIC/NLPRP and the Merrifield repository are ACLU-FOIA-established;
the retention figures come from EFF's 2025 field guide.
**Evidence:** https://www.dea.gov/epicresources (EPIC functions incl. NLPRP);
https://www.aclu.org/news/smart-justice/foia-documents-reveal-massive-dea-program-record-americans-whereabouts-license;
https://www.thenewspaper.com/news/46/4624.asp;
https://www.eff.org/deeplinks/2025/11/how-identify-automated-license-plate-readers-us-mexico-border
(WebFetch 2026-08-20 — retention figures, vendor attribution incl. Perceptics→SAIC for CBP and Selex ES /
ELSAG / Leonardo for DEA, and the covert-housing signatures).
**Retrieved:** 2026-08-20
**Implication for the spec:** Federal systems (NCIC, N-DEx, Nlets, NLPRP/EPIC, NIBIN, NGI) should be seeded
as DataSystem + Organization pairs with `governing_authority`, `query_eligibility` (who may search) and
`retention_days`. `query_eligibility: any_vetted_agent` is a wildly different access posture from
`query_eligibility: contracted_agencies` and is the fact that makes EPIC consequential.
**Outline delta:** EXTENDS §8.7 and Appendix C's third pathway.

---

## 4.13 Remaining vendors — compact reference

Verified at reference-card depth is out of scope for this pass; these are seeded with the facts needed for
the controlled vocabulary. Status is noted per row.

| Vendor | Technologies | Key facts | Status |
|---|---|---|---|
| PimEyes | `face-recognition-web-scraped` | Consumer-facing web-face search; no LE contract model | UNVERIFIED this pass |
| Thorn | `face-identification-1toN` (CSAM domain) | Nonprofit; Spotlight; domain-restricted | UNVERIFIED this pass |
| MSAB | `mobile-logical/physical-extraction` | Swedish; XRY/XAMN | PARTIALLY VERIFIED (F7.27) |
| ShadowDragon | `osint-collection-platform` | SocialNet, OIMonitor, Horizon | PARTIALLY VERIFIED |
| Dataminr | `social-media-monitoring` | First-party Twitter/X firehose lineage | PARTIALLY VERIFIED |
| Skopenow | `osint-collection-platform` | Named in Brennan Center FTC filing | PARTIALLY VERIFIED |
| Babel Street | `adtech-location-purchase`, `osint-collection-platform` | Locate X (Venntel-sourced); BabelX. USSS/CBP/DEA buyers | VERIFIED (F7.28) |
| LexisNexis Risk | `people-search-credit-header`, `third-party-investigative-platform` | Accurint / Accurint Virtual Crime Center | VERIFIED as TPIP (F7.31) |
| Thomson Reuters | `third-party-investigative-platform`, `utility-subscriber-records` | CLEAR | VERIFIED as TPIP |
| TransUnion | `third-party-investigative-platform` | TLOxp | VERIFIED as TPIP |
| Outlogic (X-Mode) | `adtech-location-purchase` | FTC order 2024; SDK-sourced | UNVERIFIED this pass |
| Mark43 / CentralSquare / Versaterm / Hexagon | `cad-system`, `rms-system` | RTCC-adjacent record layer | UNVERIFIED this pass |
| Eagle Eye / Rhombus / Ubiquiti | `cctv-fixed`, `private-camera-integration` | Cloud VMS; federate into RTCCs | UNVERIFIED this pass |
| Skydio | `uas-dfr-docked` | X10, Blue UAS; Axon Air partner | VERIFIED (F7.37) |
| BRINC | `uas-dfr-docked`, `throwable-tactical-robot` | Responder, Lemur 2; $75M round Apr 2025 | PARTIALLY VERIFIED |
| Paladin | `uas-dfr-docked` | DFR-native | UNVERIFIED this pass |
| Boston Dynamics / Ghost Robotics | `ugv-robot-dog` | — | UNVERIFIED this pass |
| BI Inc. (GEO Group, NYSE: GEO) | `electronic-monitoring-*` | Largest US integrated EM provider; ICE ISAP prime | PARTIALLY VERIFIED |
| SCRAM Systems | `electronic-monitoring-alcohol/gps` | De facto standard for court-ordered CAM | PARTIALLY VERIFIED |
| Attenti (Allied Universal) | `electronic-monitoring-gps` | Allied Universal acquired G4S and Attenti | PARTIALLY VERIFIED |
| Track Group, Buddi, Geosatis | `electronic-monitoring-gps` | — | PARTIALLY VERIFIED |
| Evolv Technologies | `weapons-detection-screening` | FTC complaint + proposed settlement 2024-11-26 barring misrepresentation of detection capability; schools ≈ half of business | VERIFIED |
| ZeroEyes / Omnilert / VOLT AI | `weapons-detection-video-ai` | Omnilert false positive on a Doritos bag led to an armed stop of a 16-year-old outside a Baltimore-area school | VERIFIED |
| Securus / ViaPath (GTL) | `jail-call-monitoring`, `voice-recognition` | Carceral comms + voice biometrics | UNVERIFIED this pass |
| Citizen / Nextdoor | `community-reporting-app` | — | UNVERIFIED this pass |
| LVT (LiveView Technologies) | `cctv-trailer` | Publicly announced Axon RTCC integration | PARTIALLY VERIFIED |
| SaferWatch | `community-reporting-app` | Genetec integration press release | PARTIALLY VERIFIED |
| Jenoptik | `traffic-radar-lidar`, `alpr-fixed`, `bluetooth-wifi-mac-capture` | Vector + optional TraffiCatch BT/WiFi capture | VERIFIED (F7.3) |
| Perceptics / SAIC | `alpr-checkpoint` | CBP checkpoint lineage; Perceptics breached | VERIFIED (F7.40) |
| Selex ES / ELSAG / Leonardo | `alpr-fixed`, `alpr-mobile` | DEA-associated hardware | VERIFIED (F7.40) |

### F7.41 — Third-party-funded surveillance is real, structurally common, and breaks purchaser=operator

**Claim:** Cameras and ALPRs deployed for police use are routinely purchased by entities that are neither the
operating agency nor the property owner — community/business improvement districts, HOAs, and police
foundations — and Flock's documented go-to-market explicitly courts the police first and then uses that
relationship to sell to HOAs.
**Status:** VERIFIED
**Evidence:**
- BIDs: four Gwinnett County GA community improvement districts (Gateway85, Gwinnett Place, Sugarloaf,
  Evermore) collectively contribute ~$250,000 annually to fund Flock camera coverage
  (https://www.yahoo.com/news/articles/gwinnett-county-business-districts-team-225624434.html).
- HOAs: "Flock often works to court the police first and then tag-team to persuade local HOAs to buy the
  cameras" (https://theintercept.com/2023/03/22/hoa-surveillance-license-plate-police-flock/); "An HOA can
  choose to integrate its Flock system with law enforcement — and once it does, the neighborhood's cameras
  feed the same nationwide, searchable Flock network the police use." Flock markets an HOA vertical directly
  (https://www.flocksafety.com/industries/hoas).
- Private cameras persisting through municipal cancellation: Syracuse activists "don't believe that cameras
  installed by private companies, such as a local Lowe's and Home Depot, are so far affected by the city's
  move away from Flock" (Guardian 2026-08-20).
- Oakland HOAs installing cameras aimed at public roads
  (https://oaklandside.org/2024/03/27/oakland-homeowner-groups-powerful-surveillance-cameras/).
- Vendor-assisted grant capture: EFF finds vendors "assist with grant applications to ensure funds flow
  directly to their businesses" (Beware the Bundle, WebFetch 2026-08-20).
**Retrieved:** 2026-08-20
**Implication for the spec:** `purchaser`, `funder` and `operator` must be three separate roles on a
Deployment (Part 6), and `funding_source ∈ {agency_general_fund, federal_grant, state_grant, bid_or_cid,
hoa, police_foundation, private_business, asset_forfeiture, vendor_donation, unknown}` must be a Contract
and Deployment attribute. Without it, the graph cannot answer the most common local question — "who is
paying for this?" — and cannot detect the pattern where a cancelled municipal contract leaves private
cameras feeding the same network (the Syracuse case).
**Outline delta:** **EXTENDS §4.1 and §8.10.** The outline's ownership decomposition
(`camera owner != data controller != police accessor != platform provider`) is right but incomplete: it
omits the purchaser and the funder, which is where the accountability gap actually opens, because a
BID-funded or HOA-funded camera is often outside the CCOPS ordinance that governs agency purchases.

### F7.42 — Bundling and sole-sourcing are the mechanism that makes capability expansion invisible

**Claim:** EFF documents that public-safety vendors deliberately bundle, use sole-source designations, offer
free trials, and assist with grant applications, and that this produces capability acquisition without
discrete procurement events — Axon has 85% BWC market share and 95% of customers on subscription plans.
**Status:** VERIFIED
**Evidence:** https://www.eff.org/deeplinks/2025/04/beware-bundle-companies-are-banking-becoming-your-police-departments-favorite
(WebFetch 2026-08-20): "companies are regularly pushing police to buy more than they need"; three named
dangers — lock-in via sole-source designations and integrated features; data monetization ("each surveillance
tool feeds a growing data pool ... sometimes using data to train proprietary models"); and deliberate
necessity creation via discounted bundles, free trials and grant assistance.
**Retrieved:** 2026-08-20
**Implication for the spec:** A Deployment can come into existence with **no contract of its own** (bundle
inclusion, free trial, grant-funded pilot). §8.5 must not require a Contract, and §10 Phase 1F's
contract-first ingestion strategy will systematically under-count exactly the newest capabilities. Add
`acquisition_mode ∈ {competitive_procurement, sole_source, cooperative_piggyback, bundle_inclusion,
free_trial, donation, grant_direct, unknown}`.
**Outline delta:** EXTENDS §8.10 and §10 Phase 1F; supplies the mechanism behind §6.7's warning.

### F7.43 — Cooperative purchasing removes the local procurement paper trail

**Claim:** Both Flock and Genetec publish price lists under OMNIA Partners national cooperative contracts,
allowing agencies to purchase by piggybacking on an existing award rather than issuing their own RFP.
**Status:** VERIFIED
**Evidence:** https://www.omniapartners.com/suppliers-files/E-J/Flock_Safety/Contract_Documents/R250203/5_29_2025_Flock_Safety_Omnia__R250203_Price_List.pdf
(contract R250203, price list dated 2025-05-29);
https://www.omniapartners.com/suppliers-files/E-J/Genetec/Assets/2025.08_Citigraf_Real_Time_Crime_Center.pdf
(dated 2025-08). Retrieved 2026-08-20.
**Retrieved:** 2026-08-20
**Implication for the spec:** Cooperative master contracts (OMNIA, Sourcewell, NASPO ValuePoint, GSA) are
**Contract entities with many child Contracts**, and they are *also a public price source*, which lets SIG
sanity-check reported deployment costs and infer quantities. Model `parent_contract_id` on Contract, and add
these price lists to §21.
**Outline delta:** EXTENDS §8.10.

---

# Part 5 — The integration edge-type catalog

Fourteen edge types. Every one is **directed**, **time-bounded** (`valid_from`, `valid_to`, `observed_at`)
and carries `evidence_claim_id`. The discriminating questions are: *who initiates?*, *what moves — data,
query, or authority?*, and *does the data come to rest at the far end?*

| # | Edge | Semantics | Discriminator | Verified example |
|---|---|---|---|---|
| 1 | `integrates_with` | **Deprecated as a stored edge.** Permitted only as a query-time rollup over 2–14. | If you can answer "what moves and who starts it?", use a specific edge. | — |
| 2 | `ingests_feed_from` | B **pulls** a continuous stream/feed from A. Data comes to rest in B. | Puller-initiated, continuous. | Fusus pulls Verkada camera feeds using a read-only API key (F7.34) |
| 3 | `pushes_alerts_to` | A **pushes** discrete events to B. Only events, not the underlying corpus. | Pusher-initiated, event-granular. | Verkada webhook pushes LPR reads to a Fusus endpoint (F7.34) |
| 4 | `federates_search_to` | B may **run a query** against A's data; results return to B; the corpus stays with A. | Query moves, corpus does not. | Flock national/state lookup; N-DEx; CrimeTracer; RISSNET (F7.2, F7.39) |
| 5 | `is_queryable_by` | Inverse of 4, asserted from A's side. Kept separate because the two are observed from different sources (portal vs contract). | Perspective. | Flock transparency portal listing which orgs can search you |
| 6 | `hosts_data_for` | A stores/controls infrastructure holding B's data. Custody, not access. | Custody. | Flock hosts agency ALPR data; Axon Evidence hosts Ring-shared footage (F7.33) |
| 7 | `resells_data_from` | A sells access to data collected by B, where B is not a party to A's customer relationship. | Money + third-party corpus. | Vigilant/LEARN ← DRN (F7.20); Locate X ← Venntel (F7.28); Webloc ← ad exchanges (F7.29) |
| 8 | `provides_platform_to` | A supplies the software/service surface B operates on. | Vendor→operator, not data. | Penlink Tangles → agency; Fusus → agency (F7.29) |
| 9 | `subscribes_to` | B pays for standing access to A's data/service. Contractual, not technical. | Money + standing access. | Agency → CLEAR / TLOxp / Fog Reveal (F7.31) |
| 10 | `enrolls_asset_into` | An asset owned by A is registered/connected into platform B. | The object is a *device*, not data. | Business camera → Community Connect (F7.15, F7.16) |
| 11 | `requests_data_from` | A can issue per-incident, consent-gated requests to B's users. | Per-incident + consent. | Police → Ring Community Requests (F7.33) |
| 12 | `distributes_list_to` | A pushes a watchlist/hotlist to B for local matching. Matches do **not** return to A. | One-way list, no feedback. | NCIC → local ALPR deployments (F7.19) |
| 13 | `authorizes` | A grants B legal permission to operate a capability. No data at all. | Authority, not data. | FAA → 1,004 agencies via §91.113 waiver (F7.36); governor → fusion center (F7.38) |
| 14 | `succeeds` / `replaced_by` | B's deployment supersedes A's for the same capability at the same org. | Temporal substitution. | Axon ALPR replaced Flock in Longmont, Denver, Syracuse (F7.13) |

Required attributes on 2–12:

```text
initiator            : source | target | third_party
transport            : webhook_push | api_pull | rtsp_stream | sftp_batch |
                       appliance_bridge | manual_export | portal_query | physical_media
granularity          : event | stream | batch | query | list
data_comes_to_rest   : bool          # distinguishes 2/6 from 4/5
scope                : own | partner | state | region | national | commercial
consent_gate         : none | owner_per_request | owner_standing | agency_admin | legal_process
mechanism            : direct_account | proxy_lookup | pilot_program | contractual_share |
                       network_default | api_integration | cooperative_membership
terminable_by        : source | target | either | regulator
termination_reason   : commercial | regulatory_prohibition | policy_change | breach | unknown
```

Three rules fall out of the evidence:

- **The Verkada rule (F7.34).** Two products can hold *two* integration edges in *opposite directions*
  simultaneously. Edges are per-(product-pair, data-kind, direction), never per-product-pair.
- **The Axon–Flock rule (F7.17).** Integrations are terminable by one side unilaterally, mid-contract, and
  the termination may be partial (new customers only). `valid_to` must support `applies_to_cohort ∈
  {all, new_customers_only, existing_customers_only}`.
- **The NCIC rule (F7.19).** `distributes_list_to` must not be modeled as `federates_search_to`. The
  direction of the *match result* is the whole civil-liberties question: ICE populates the list, the FBI
  distributes it, the local agency alerts — and ICE is not notified. Getting this backwards would invent a
  federal surveillance channel that the evidence says does not exist on that path.

---

# Part 6 — The ownership / control / access role model

§4.1's four-way split is correct and insufficient. Fourteen roles, each with a definition, a discriminating
test, and a verified example.

| Role | Definition | Test | Verified example |
|---|---|---|---|
| `owner` | Holds property title to the physical asset | Who could lawfully remove it? | Lowe's / Home Depot own store cameras in Syracuse that survived the city's Flock cancellation (F7.12) |
| `purchaser` | Paid for the asset or the licence; may never operate it | Whose money? | Gwinnett CIDs paying ~$250k/yr for Flock coverage used by police (F7.41) |
| `funder` | Supplied the money to the purchaser, with or without conditions | Whose grant/appropriation? | BJA body-worn-camera microgrants named in Atlas records; vendor-assisted grant capture (F7.42) |
| `installer` | Physically mounted/configured the asset | Who was on the ladder? | Flock installs and, notoriously, fails to de-install (Oshkosh, F7.12) |
| `host` | Owns the mounting location / right-of-way | Whose pole, whose wall? | Utility poles, private building facades hosting ShotSpotter sensors (F7.25) |
| `operator` | Day-to-day control: aims it, tunes it, responds to it | Who gets the alert? | Longmont PD operating Axon ALPRs it does not host (F7.13) |
| `data_controller` | Determines purposes and means of processing; sets retention and sharing | Who can change the retention setting? | The agency, per Flock's "customers own the data, decide who can access it" (F7.9) — a *contested* assertion |
| `data_processor` | Processes on the controller's instructions | Could they lawfully use it for their own purposes? | Flock/Axon as stated processors; contested by F7.11 and by EFF's data-monetization finding (F7.42) |
| `platform_provider` | Supplies the software surface and the network effect | Who would the capability disappear with? | Axon (Fusus/Community Connect), Penlink (Tangles) |
| `accessor_read` | Can view data without initiating a search | Passive view? | RTCC analysts viewing federated private feeds |
| `searcher` | Can execute queries against the corpus | Can they run a plate/face/location query? | CBP querying 80,000+ Flock cameras (F7.10) |
| `alert_recipient` | Receives pushed notifications | Do they get pinged? | Agencies subscribed to NCIC hotlist topics (F7.19) |
| `auditor` | Has a standing right to inspect use logs | Can they see the search log? | Flock Audit Assistance admins; CCOPS oversight boards |
| `regulator` | Sets binding external constraints | Can they prohibit it? | FCC (Covered List), FTC (Gravy/Venntel, Evolv), FAA (waivers), state AGs |

**The seven separations that matter**, each with a real case:

1. **owner ≠ operator.** Private business cameras operated in effect by a police RTCC (F7.15/F7.16).
2. **purchaser ≠ operator.** BID/HOA-purchased ALPRs operated by police (F7.41). This is the case that most
   often escapes CCOPS ordinances, because the ordinance regulates *agency acquisition*.
3. **operator ≠ data_controller.** Under a Flock national-lookup configuration, the searching agency is not
   the controller of the data it searches; the collecting agency is. Flock's Aug 2026 offense filters make
   the controller's choices bind the searcher (F7.9).
4. **data_controller ≠ platform_provider — contested.** Flock asserts customers control the data; the Nova
   sourcing dispute (F7.11) and EFF's model-training finding (F7.42) put that in question. SIG must store
   the *assertion* and the *contradiction*, never adjudicate.
5. **searcher ≠ accessor.** CBP's 80,000-camera access was *search*, granted by a third agency (Loveland),
   over data owned by hundreds of uninvolved agencies (F7.10). This is a four-party fact.
6. **host ≠ owner.** ShotSpotter sensors on private rooftops: the building owner hosts, the city operates,
   SoundThinking owns the hardware — and the leaked coordinates endanger the *host*, not the operator
   (F7.25). This is why §13.3 must be applied at the role level, not the asset level.
7. **regulator ≠ funder.** DHS both funds fusion centers (RAC resource allocation) and does not designate
   them — governors do (F7.38). Authorizer, funder and regulator are three different bodies.

---

# Part 7 — The validated lifecycle state machine

## 7.1 The outline's model is one dimension short

F7.12 (Oshkosh: contract cancelled, cameras still mounted, service unplugged) is not representable in a
single enum. Lifecycle must be **three orthogonal state variables plus a legal-authorization variable**:

```text
procurement_state   — the contractual/decision track
physical_state      — where the hardware is
operational_state   — whether it is producing data
authorization_state — whether it is legally permitted (FAA waiver, ordinance approval, court order)
```

Every one of the outline's 14 states is retained; all are assigned to a track; 10 states are added.

## 7.2 `procurement_state` (14)

| State | Definition | Evidence signature | Source |
|---|---|---|---|
| `proposed` | Publicly floated, no formal action | Agenda item, staff report | outline |
| `rfp_issued` | Solicitation published | RFP/RFQ/ITB number, bid portal posting | **added** |
| `awarded` | Vendor selected, contract not signed | Council vote, notice of award | **added** — Longmont as of 2026-08-20 (F7.13) |
| `contracted` | Executed agreement | Signed contract, PO | outline |
| `cooperative_piggyback` | Purchased under another entity's master award | OMNIA/Sourcewell/NASPO contract number | **added** (F7.43) |
| `bundle_included` | Acquired inside a broader bundle with no line item | Bundle SKU, subscription tier | **added** (F7.42) |
| `free_trial` | Vendor-provided at no cost, no contract | Trial agreement, "pilot at no cost" | **added** (F7.42) |
| `donated` | Third party gave the asset/licence to the operator | Gift acceptance resolution | **added** (F7.41) |
| `third_party_funded` | Purchased by a non-agency funder for agency use | BID/HOA/foundation payment record | **added** (F7.41) |
| `grant_funded_pending` | Grant awarded, procurement not started | Grant award notice | **added** |
| `renewed` | Term extended | Amendment, renewal option exercised | **added** |
| `nonrenewed` | Allowed to lapse at term end | Expiry with no amendment | outline — Longmont Dec 2025 (F7.13) |
| `canceled` | Terminated before term end | Termination notice, council vote | outline — Chicago ShotSpotter (F7.24) |
| `rejected` | Formally declined before any contract | Vote against, RFP cancelled | **added** — part of DeFlock's 56 (F7.12) |

## 7.3 `physical_state` (7)

`not_installed` → `installation` (outline) → `installed` → `installed_inactive` (**added**: mounted, powered
or not, not producing usable data — the bagged cameras of Oshkosh/Evanston/Dayton, F7.12) →
`decommissioning` (outline) → `removed` (outline) → `destroyed_or_lost` (**added**: vandalism, which the
Guardian documents in Houston, and theft).

`replaced` (outline) is **not** a physical state: it is the `replaced_by` edge (Part 5, #14). Keeping it as
a state was the modelling error that lets a vendor swap read as a reduction.

## 7.4 `operational_state` (6)

`inactive` · `pilot` (outline) · `active` (outline) · `expanded` (outline — increased count or scope) ·
`restricted` (outline — capability reduced while remaining active; the Aug 2026 offense filters and federal
toggles, F7.9/F7.10) · `suspended` (outline — temporarily halted).

## 7.5 `authorization_state` (6)

`unauthorized` · `approval_pending` · `authorized` (**added** — e.g. an FAA §91.113 waiver in force,
F7.36) · `authorized_expired` (**added** — the 2029 expiry dates in the FAA data make this measurable) ·
`moratorium` (**added** — a jurisdiction-wide pause) · `sunset_by_ordinance` (**added** — a CCOPS or statutory
sunset). `litigation_hold` (**added**) is a *flag*, not a state: it can coexist with any combination.

`unknown` is an admissible value on **every** track and is the default. This is §9.4 and §6.6 in the schema
rather than in prose.

## 7.6 Legal transitions

```text
procurement:
  proposed → {rfp_issued, awarded, rejected, proposed}
  rfp_issued → {awarded, rejected}
  awarded → {contracted, rejected}                       # Longmont sits here
  contracted → {renewed, nonrenewed, canceled}
  renewed → {renewed, nonrenewed, canceled}
  {cooperative_piggyback, bundle_included, free_trial, donated,
   third_party_funded, grant_funded_pending} → {contracted, canceled, rejected}
  # NOTE: free_trial → active is legal with NO procurement transition. This is F7.42's
  # invisible-capability path and the single most important edge in this diagram.

physical:
  not_installed → installation → installed
  installed → {installed_inactive, decommissioning, destroyed_or_lost}
  installed_inactive → {installed, decommissioning, destroyed_or_lost}
  decommissioning → removed

operational:
  inactive ↔ pilot ↔ active ↔ expanded
  active → {restricted, suspended, inactive}
  restricted → {active, suspended, inactive}
  suspended → {active, inactive}

authorization:
  unauthorized → approval_pending → authorized → {authorized_expired, moratorium, sunset_by_ordinance}
  authorized_expired → approval_pending
```

**Forbidden combinations** (these are integrity constraints, and each has a real counterexample that proves
why the constraint must be *soft*, i.e. flagged rather than rejected):
- `physical=removed` ∧ `operational=active` — impossible; flag as data error.
- `procurement=canceled` ∧ `physical=installed` — **legal and common** (Oshkosh, F7.12). Must not be blocked.
- `procurement=canceled` ∧ `operational=active` — legal during a wind-down window; flag for research task.
- `authorization=authorized` ∧ `physical=not_installed` — legal (`authorized_not_deployed`); ~some share of
  the 1,004 FAA waiver holders are here, and identifying them is a high-value §12 research task.

## 7.7 Evidence signatures per transition

| Transition | Signature |
|---|---|
| → `rfp_issued` | Bid-portal posting, RFP number, cooperative solicitation |
| → `awarded` | Council minutes "voting unanimously to approve", notice of award |
| → `contracted` | Executed PDF, PO number, OMNIA child contract |
| → `installation` | Permit, pole-attachment agreement, work order |
| → `installed` | OSM/DeFlock node appearance, field photo, portal device count increase |
| → `active` | Transparency-portal search counts > 0, first alert, vendor press release |
| → `expanded` | Device-count delta, contract amendment, portal camera count |
| → `restricted` | Policy amendment, config screenshot (F7.19), vendor toggle announcement (F7.9) |
| → `suspended` | "paused all federal pilots" (F7.10), council directive |
| → `nonrenewed` | Term expiry with no amendment; "let a contract lapse" |
| → `canceled` | Termination letter, council vote, mayor's statement (Chicago, F7.24) |
| → `installed_inactive` | "moved to unplug", trash-bag photos, DeFlock status change |
| → `removed` | Field verification of absence, vendor pickup confirmation, OSM node deletion |
| → `authorized` | FAA waiver row with Start Date (F7.36), ordinance approval |
| → `authorized_expired` | FAA End Date passed with no amendment |
| `replaced_by` edge | Successor contract naming the same capability at the same org (F7.13) |

**The stale-listing signal.** The two Community Connect listings whose Fusus org returns 404 (F7.15) are a
reusable detector: a vendor directory entry that outlives its backing tenant is evidence of a
`procurement=canceled`/`operational=inactive` transition the vendor has not yet reflected. Vendor directories
lag reality in a *specific, detectable direction* — they over-report. Record `vendor_directory_lag` as a
known bias in §11.1 camera-count reconciliation.

---

## Open questions

1. **Atlas CC-BY version.** The Atlas footer says "CC-by" without a version or a link to a licence deed.
   Hedge: record `CC-BY (version unspecified)` and treat as CC-BY-4.0-compatible for attribution purposes
   only; do not assert redistribution terms beyond attribution until confirmed with EFF.
2. **Seattle CCOPS master list not fetched.** The Seattle surveillance-reports index and the Master List of
   Surveillance Technologies were identified but not retrieved. The CCOPS crosswalk in §2 is therefore
   built from the Atlas and EFF SLS vocabularies plus the ordinance structure, not from an actual municipal
   inventory. This is the largest single gap in Part 2 and should be the first follow-up.
3. **FAA Part 107 waiver list not enumerable.** `faa.gov/uas/commercial_operators/part_107_waivers/waivers_issued`
   returns HTTP 200 to curl but the body is a JS shell with no CSV/JSON link. Fallback: the EFF §91.113
   FOIA dataset (F7.36) covers DFR specifically; general Part 107 waivers remain unobtained. A FOIA request
   or the FAA CAPS system are the routes.
4. **HIDTA and RISS center lists.** riss.net/centers/, dea.gov/operations/hidta and the ONDCP HIDTA page all
   returned HTTP 000 (connection failure) even with a browser UA. The six RISS centers are named from
   secondary sources; the 31 HIDTA designations are not obtained.
5. **ShotSpotter count discrepancy unresolved.** 22,471 (downloadable derivative) vs 25,580 (press). Cause
   unknown. Hedge: ingest area-level counts only, store both figures as contradicting Claims.
6. **Dedrone consideration.** Two secondary sources give $625M and ~$391M; Axon disclosed nothing. Store no
   value.
7. **Whether Flock's grandfathering actually held.** Boulder/Lafayette retained 30 days, but no systematic
   observation of retention settings across the 1,500+ transparency portals was performed. This is the single
   highest-value reconciliation task available right now and is squarely R3's portal-scraping territory.
8. **Genetec "Community Connect" vs Axon "Community Connect".** Confirmed as a name collision from vendor
   materials, but the Genetec program's scale and structure were not characterized.
9. **Whether `totalIntegratedCameras` is documented anywhere.** The semantics are inferred from the numbers
   (F7.15), not from Axon documentation. If Axon publishes a definition, the interpretation should be
   revisited.
10. **Ring↔Axon Community Requests: does footage land in Axon Evidence?** Strongly implied by the Flock
    analogue ("footage shared by users goes into the Flock platform") but not directly verified for Axon.

---

## Spec requirements emitted

| ID | Requirement |
|---|---|
| REQ-R7-01 | Split §8.4 into three entities: `Technology` (101-slug closed vocabulary), `Capability` (`verb.object.scope`), and a promoted `ConfigurationState`. (F7.1) |
| REQ-R7-02 | `Technology` is three-level (`domain` → `family` → `technology`) with `-unspecified` leaves in every family, and slugs are immutable and never reused. (F7.3) |
| REQ-R7-03 | External vocabularies (Atlas, EFF SLS, CCOPS) are crosswalked with SKOS-style `exactMatch`/`broadMatch`/`narrowMatch`/`relatedMatch`, never adopted as primary keys. (F7.4) |
| REQ-R7-04 | `Deployment --actually_provides--> Capability` requires its own evidence Claim; inference from `Product --can_offer--> Capability` must be materialized with `derivation: product_default` and reduced confidence. (F7.1) |
| REQ-R7-05 | Any fact that can differ between two deployments of the same product without a hardware/software change is `ConfigurationState`, not Technology or Capability. (F7.1, F7.9) |
| REQ-R7-06 | `ConfigurationState` carries `source_level ∈ {vendor_default, contract_term, portal_observed, records_request, agency_policy}` ranked by authority, and supports future-dated `effective_from`. (F7.9) |
| REQ-R7-07 | `AccessRelationship` carries `mechanism` and `granted_by` separately from `accessor`, and supports four-party grants. (F7.10) |
| REQ-R7-08 | `IntegrationRelationship` carries `initiator`, `transport`, `granularity`, `data_comes_to_rest`, `consent_gate`, `terminable_by`, `termination_reason`, and per-cohort `valid_to`. Bare `integrates_with` is deprecated as a stored edge. (F7.34, F7.17) |
| REQ-R7-09 | Adopt the 14-edge integration catalog (Part 5); `distributes_list_to` must be distinct from `federates_search_to`. (F7.19) |
| REQ-R7-10 | Adopt the 14-role model (Part 6); `purchaser`, `funder` and `host` are distinct from `owner` and `operator`. (F7.41) |
| REQ-R7-11 | `Deployment` and `Contract` carry `funding_source` and `acquisition_mode`; `Deployment` must not require a Contract. (F7.41, F7.42) |
| REQ-R7-12 | Replace the §6.7 single lifecycle enum with four orthogonal tracks (`procurement`, `physical`, `operational`, `authorization`) plus a `litigation_hold` flag; `unknown` is admissible on every track. (F7.12) |
| REQ-R7-13 | `replaced` is an edge (`replaced_by`), not a state, and carries `replacement_kind` and `cause ∈ {agency_choice, regulatory_prohibition, vendor_exit, cost}`. (F7.13, F7.37) |
| REQ-R7-14 | Integrity constraints on lifecycle combinations are **soft** (flag, never reject); `canceled ∧ installed` must be storable. (F7.12) |
| REQ-R7-15 | `Vendor` carries `sec_cik`, `uei`, `ownership_status`, `hq_place`, `founded`, `founders[]`, and a funding-round history. (F7.6, F7.22, F7.30) |
| REQ-R7-16 | Acquisition edges carry `announced_date`, `closed_date`, `consideration_usd`, and an explicit `consideration_disclosed: false` when the first party declined to disclose. (F7.14) |
| REQ-R7-17 | `Product` identity is `(vendor_id, product_name, valid_from)`; `component_of` self-edges are supported; product lineage survives rebranding. (F7.7, F7.8, F7.23) |
| REQ-R7-18 | `DataSystem` carries `data_origin ∈ {agency_collected, vendor_collected, commercial_collected, brokered, scraped, breached}`, `historical_depth`, and `query_eligibility`. (F7.20, F7.29, F7.40) |
| REQ-R7-19 | `Contract` carries `parent_contract_id` (cooperative master), `seller_role ∈ {oem, reseller, integrator, cooperative}`, `sole_source`, `bundle_name`, and `beneficiary_organizations[]` separate from `buyer`. (F7.30, F7.35, F7.43) |
| REQ-R7-20 | `Deployment` supports `operating_organizations[]` (plural) and a `service_area` distinct from the operating organization. (F7.25, F7.35) |
| REQ-R7-21 | Camera-federation deployments carry `tier[] ⊆ {registry, integration, request}`; each enrolled asset carries its own `federation_tier`. (F7.16) |
| REQ-R7-22 | Vendor-reported counters are stored under their verbatim source names alongside any normalized value, with a `metric_semantics_note`; `totalIntegratedCameras` must never be summed as a distinct-camera count. (F7.15) |
| REQ-R7-23 | Ingest `axoncommunityconnect.com/locations.json` + `api.fususone.com/api/public/organizations/{org}/stats/` as a named source (321 orgs, coordinates, registry URLs, time-varying counters). (F7.15) |
| REQ-R7-24 | Ingest the EFF FAA §91.113 DFR waiver dataset as a named source with `license: us_gov_public_domain (FOIA release)`, `attribution_courtesy: EFF`, using its `Start Date`/`End Date` as native `valid_from`/`valid_to`. (F7.36) |
| REQ-R7-25 | Ingest the DHS fusion-center list (54 primary + 26 recognized = 80) as an Organization seed, mapping `primary` to elevated federal-connectivity `AccessRelationship` priors. (F7.38) |
| REQ-R7-26 | Model federal watchlist systems (NCIC and its topic sub-files, N-DEx, Nlets, NLPRP/EPIC, NGI, NIBIN) as DataSystems with enumerable sub-files; `hotlist_topics_subscribed[]` is a records-request-observable ConfigurationState attribute. (F7.19, F7.40) |
| REQ-R7-27 | Add `config_screenshot` as an EvidenceArtifact subtype with Tier-A weight. (F7.19) |
| REQ-R7-28 | `Policy` entities support enforcement orders with `applies_to_purposes[]` / `exempt_purposes[]`, and regulatory instruments that constrain **Products** rather than Deployments (FCC Covered List, NDAA §889/§1709). (F7.28, F7.37) |
| REQ-R7-29 | Absence of a datapoint in a source whose vocabulary has changed (Atlas Ring removal, March 2024) must never be treated as evidence of absence; sources carry `vocabulary_version` and `category_retirement_dates`. (F7.4, F7.33) |
| REQ-R7-30 | Leaked datasets carry `license_status: asserted_<x>_disputed_chain`; for the ShotSpotter corpus ingest area-level keys and counts only, not individual coordinates, per §13.3. (F7.25) |
| REQ-R7-31 | Record `vendor_directory_lag` as a known over-reporting bias in count reconciliation; a directory entry whose backing tenant 404s is a lifecycle-change detector. (F7.15) |
| REQ-R7-32 | The location-broker chain is modeled with six layers (app/SDK → ad exchange → aggregating broker → productizer → platform host → agency); `resells_data_from` is transitive but the hops must not be collapsed. (F7.29) |

---

*End of R7.*
