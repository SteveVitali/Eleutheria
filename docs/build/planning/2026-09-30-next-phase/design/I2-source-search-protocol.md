# I2 — Source-search protocol and taxonomies

Row **I2** of `META_PLAN.md` §6 (Stream I, Stage P). Owner class **D** (design). Authored 2026-09-30T17:21Z →
17:51Z (`date -u`) by Claude Code (Opus 5.5) in the planning worktree, branch `claude/next-phase-planning`
(planning HEAD `41ab9521` at authoring). Outputs: this protocol and `data/search_matrix.csv` (190 cells).
Nothing else was written; nothing was committed.

This is the rulebook that the four parallel fresh-context research rows follow:
- **I3**: ALPR and public-private camera networks;
- **I4**: the other technology classes;
- **I5**: geography gaps;
- **I6**: cross-cutting evidence channels.

It is written so that their searches are **exhaustive** (every technology × channel × geography combination
belongs to a cell), **non-overlapping** (every combination belongs to exactly one cell, and every cell to exactly
one row), **reproducible** (every query is logged and every candidate is fetched and hashed), and **comparable**
(every row uses one schema, one weight formula and one stopping rule).

**Inputs read:**
- `META_PLAN.md`: §3, the Stream I section, §7.1, §8.6 and §9.
- `research/I1-source-coverage.md`, `data/source_coverage.csv` (369 rows) and `findings/incoming/I1.csv`
  (NEW-1…NEW-9).
- Six-streams `research/S5-source-strategy.md` and `data/source-candidates.csv` (SRC-001…027).
- `tasks/src/tasks/data/acquisition_queue.toml` and `tasks/src/tasks/acquisition.py:89-195`: the `acq-score/1`
  weights, the lineage vocabulary and the Part VIII excluded categories.
- `ontology/vocab/technology.yaml` v1.0.0 (14 domains / 36 families / 104 technologies), `capability.yaml`, and
  `predicates.yaml:1536-1680`.
- `connectors/src/connectors/runner.py` `CONNECTOR_FOR_SOURCE` (19 connector families), `registry.py:42-92`,
  and `data/{sources,agenda_tenants,procurement_portal_tenants,camera_registry_targets,state_alpr_statute_seed}.toml`.
- Spec `docs/2_canonical_design_spec.md`:
  - §22.2–22.7 (lines 3578–4062);
  - §26 (4470–4499);
  - §43 (6229–6400);
  - §18.1 (3184–3193);
  - SIG-ACQ-001…004 (7353–7359).
- Local I1 captures (gitignored) under `docs/build/logs/next-phase/I1/`:
  - `atlas.csv`, sha256 `dcbf8bc1…`, the same bytes as I1 used;
  - `eyesonflock.json`, sha256 `eccb336a…`;
  - `sub-est2024.csv`, sha256 `af9cd483…`.
- Calibration: 15 web calls (13 searches + 2 catalog-API fetches), logged in Appendix A.

**Evidence classes (P1)** are used throughout: `code`, `recorded-execution`, `live-read`, `operator-statement`
and `inference`. Search-engine result summaries are labelled **search-summary (unfetched)**. They are
*calibration signals only*: I3–I6 must fetch the origin before citing any of them (§7.7).

---

## 0. Summary

| Item | Size |
|---|---|
| Technology taxonomy | **29 technology classes + `T00` MULTI** (§2). Together they map every one of the ontology's 36 families. Two classes have no ontology concept: `T09` automated traffic enforcement (NEW-8) and `T27` fusion centres (an organisation role). `T28` is cross-family. `T29` is the operator-requested Flock carve-out. |
| Discovery-channel taxonomy | **16 channels** (§3), each with its typical access mode, rights posture, Part VIII risk and SIG connector reuse, plus an international-equivalents crosswalk for the UK, Canada, Australia/NZ, EU/EEA and the rest of the world. |
| Geography frame | **14 geography groups** (§4). The 51 US jurisdictions are weighted from I1's measured gaps: tier A has 10 states (VT, NH, DE, MS, RI, WV, ME, WY, AR, MI), tier B has 5 (HI, ND, DC, MT, NM) and tier C has 36. There are 36 thin and 64 other top-100 cities, about 88 top-100 counties, the territories and tribal nations, and three international tiers. |
| Search matrix | **190 cells**: I3 40, I4 74, I5 53, I6 23. By priority: P1 27, P2 65, P3 98. A mechanical partition check passed: every class × channel × geography triple maps to exactly one cell, and every cell is reachable (§5.2). |
| Budgets (issued queries / fetches) | I3 150/250 · I4 170/250 · I5 150/250 · I6 130/200. The sum of per-cell minimums is 96, 117, 76 and 46, which is ≤ 70% of each budget. The rest is adaptive. |

The notable calibration discoveries are in Appendix A. Items 3–7 below are search-summary signals, not fetched evidence (§7.7). In short:
1. ArcGIS Hub alone matches **1,266** items for "flock". Most of the first page are agency-published Flock
   location layers.
2. Socrata's catalog search for "license plate reader" returns mostly **per-read ALPR datasets**. That is a Part
   VIII block.
3. Minnesota's Legislative Reference Library hosts the §13.824 ALPR audits at a stable URL pattern.
4. A 2025 national ALPR-statute summary (NAMSDL) supersedes the NCSL seed, which was frozen in 2022.
5. Virginia has a new State-Police ALPR reporting duty.
6. "Connect ‹Place›" Fusus registries and city camera-registry pages are findable at scale.
7. FAA DFR waivers are a large, fast-growing channel (the figure is from a search summary, unverified).
8. The EFF Atlas has 26,294 citation links. They give a partitionable snowball corpus with 507 links to Flock
   portals, 3,809 to DocumentCloud and 1,162 to MuckRock.

---

## 1. Binding rules for I3–I6 (read before the first query)

- **R1 — Evidence (P1, P15).**
  - Every candidate row and every factual sentence in a research note cites a URL the row itself fetched (with
    its fetch id), or a repo `file:line`.
  - Search-result snippets and summaries are **leads**, never evidence.
  - Nothing is cited that was not fetched.
- **R2 — Clock (P2).**
  - Every `run_at` and `retrieved_at` comes from `date -u` or a tool timestamp. Run `date -u` at least once per
    batch of calls.
  - Never infer a date, and never back-fill a timestamp.
- **R3 — Read-only world (P3).** Allowed: GET requests to public URLs and documented public APIs.
  Forbidden:
  - form submissions, logins or account creation (including "free" API keys: LegiScan, ICPSR, GovSpend,
    Pavilion accounts);
  - paid services (Q-21 is "assume zero");
  - public-records requests or outreach of any kind (SIG-ACQ-004);
  - writes to any SIG system or bucket.
- **R4 — Conduct.** The spec's conduct rules apply to research fetches (§26 rules 3–5, SIG-INGEST-036/037):
  - At most 1 request per second per host. At most 25 fetches per host per row, except documented APIs within
    their published limits.
  - A `403`, `429` or challenge page stops that host for the rest of the row. Record the status; never retry
    past a challenge.
  - No challenge-solving, no proxy or user-agent games, no paywall evasion.
  - Do not use the Wayback Machine, archive.today or another mirror to reach content whose origin refuses
    access. `internet_archive_wayback` excludes `*.flocksafety.com`, and `flock_transparency_portals` is
    registry-**refused**.
  - Prefer the offered channel (API or bulk download) over HTML.
- **R5 — Availability is not rights (P15, SIG-ACQ-002).**
  - Capture terms verbatim.
  - Never write a rights decision. Every rights field is a guess, labelled as such.
  - Municipal publication does not make a source CC0 (ADR-130).
- **R6 — Metadata-first, never bulk rows.**
  - During I3–I6, read landing pages, metadata endpoints, schemas and at most one sample document per
    candidate.
  - Never download dataset rows from a candidate flagged or suspected under Part VIII (§7.4).
  - Store raw captures only under `docs/build/logs/next-phase/I<n>/` (gitignored), keyed by sha256 (§8.4 of the
    META_PLAN).
  - Never copy plate numbers, operator or user identifiers, officer names from audit rows, search reasons,
    student data or private addresses into any committed artifact. I1 set this precedent with the Eyes on Flock
    search-reason fields.
- **R7 — Scope discipline.**
  - A row issues queries **only under its own cells** (§5.2).
  - A row may *capture* an out-of-scope candidate it meets while following its own results. It tags the cell
    that found it and notes the owning cell.
  - It never runs queries in another row's cells.
- **R8 — Single writer (§9).**
  - A row writes only `research/I<n>-<slug>.md`, `data/candidates_I<n>.csv` and `data/query_log_I<n>.csv`.
  - Optionally it also writes `findings/incoming/I<n>.csv` (the §8.2 schema) for defects it observes, for
    example a registered source whose URL is dead.
  - It never edits the registry, `sources.toml`, the META_PLAN or another row's files.
- **R9 — Named gap first (SIG-ACQ-001).**
  - Every candidate carries a `gap_ref`: an I1 blind-spot rank, an I1 state or city row, or a NEW-n finding.
  - Candidates are valued by the gap they close and the independent lineage they add, never by raw row volume.
- **R10 — No secrets (P14).**
- **R11 — Budget and context guard (P12).**
  - Stop issuing queries at the row budget, at the fetch cap, or when context use passes about 60%. Then write
    outputs with honest cell statuses.
  - If P1 cells are still unsaturated, return `in-progress` and recommend the predefined split (§10,
    `split_if_needed` column).

---

## 2. Technology taxonomy

Codes are stable identifiers for this planning round. Concept ids are `technology.yaml` slugs; the IRI is
`https://ontology.sig-project.org/vocab/technology/1.0.0/<slug>`. The **I1 hosted** column gives I1's §2.2
counts (ingested-live / all statuses) for the nearest I1 class. The **Atlas** column gives the upstream Atlas
`Technology` label and its row count in the local capture. The vendor and product lists are **seed lists from
agent prior knowledge (inference)**: rows verify them before citing, and a vendor's appearance here asserts
nothing about any deployment.

| Code | Class | Row | Ontology concepts | Seed vendors / products | I1 hosted | Atlas |
|---|---|---|---|---|---|---|
| T00 | MULTI: multi-class or class-agnostic source | I6 (I5 when place-anchored) | any | multi-product vendors (see vendor-only rule) | — | — |
| T01 | ALPR-FIX: fixed, trailer, covert and checkpoint ALPR, incl. vehicle fingerprinting | I3 | `alpr-fixed`, `alpr-trailer`, `alpr-covert`, `alpr-checkpoint`, `alpr-unspecified`, `vehicle-fingerprint-reid`, `vehicle-fingerprint-unspecified` | Flock Safety (Falcon, Sparrow, Vehicle Fingerprint); Motorola Solutions / Vigilant; Genetec AutoVu; Rekor (Scout); Leonardo / ELSAG; Neology; SoundThinking PlateRanger; Verkada LPR; Jenoptik; Kapsch; intl: Adaptive Recognition, Vaxtor, Tattile, Hikvision/Dahua ANPR | ALPR 24/80 | ALPR 4,094 |
| T02 | ALPR-MOB: mobile / in-car ALPR | I3 | `alpr-mobile` | Axon Fleet 3 ALPR; Vigilant mobile; WatchGuard in-car ALPR; Genetec AutoVu mobile and parking; ELSAG MPH-900; repossession fleets (DRN) | mALPR 1/1 | (in ALPR) |
| T03 | ALPR-SHARE: sharing networks, national lookup, state repositories | I3 | the `alpr` family + predicates `configured_sharing_partner(_set)` and `national_lookup_enabled`; capabilities `search.plate.{partner,state,region,national}` and `disclose.results.{to_partner,to_federal}` | Flock Network / National Lookup; Vigilant LEARN; state and regional ALPR repositories (to verify per state); federal access by ICE/CBP to local data | SHARE 2/18 | — |
| T04 | ALPR-COM: commercial and private-operator plate data | I3 | `plate-data-commercial-purchase`, `plate-data-commercial-unspecified`, `alpr-fixed` (private operator); capability `search.plate.commercial` | DRN Data (Motorola Solutions); Vigilant commercial data; Flock HOA, business and retail customers sharing into police networks; toll and parking operators | — (new) | — |
| T05 | RTCC: real-time crime centres, camera federation, CAD/RMS integration | I3 | `rtcc-platform`, `rtcc-unspecified`, `camera-federation-hub`, `federation-hub-unspecified`, `cad-rms-integration`, `cad-rms-unspecified` | Axon Fusus (FususONE/CORE); Genetec Citigraf / Security Center; Motorola CommandCentral Aware; Flock FlockOS; Peregrine; Milestone XProtect; Mark43; Hexagon; Tyler | RTCC 3/4 | RTCC 242 |
| T06 | PCAM: private-camera registries, integration, per-incident requests | I3 | `private-camera-registry`, `private-camera-integration`, `private-camera-per-incident-request`, `private-camera-integration-unspecified`; capabilities `view.livestream.private_camera`, `control.ptz.private_camera` | Fusus "Connect ‹Place›" registries; Ring / Neighbors (Community Requests, historic Public Safety Service); Motorola CommandCentral Community; Flock business-camera integrations; Project Green Light (Detroit); SafeCam (Philadelphia); city registration programmes | PREG 2/4 | Camera Registry 756 |
| T07 | CCTV: public / police fixed and PTZ cameras and camera trailers | I3 | `camera-fixed-cctv`, `camera-ptz`, `fixed-camera-unspecified`, `camera-trailer-video`, `camera-trailer-unspecified` | LiveView Technologies (trailers); Verkada; SkyCop-type pole pods; city CCTV networks | CCTV 98/125 | — |
| T08 | DOT: traffic and 511 cameras (transportation operator) | **I5** | `camera-ptz`, `camera-fixed-cctv` (operator role: transportation agency) | state DOT / 511 systems | DOT 83/87 | — |
| T09 | ATE: automated traffic enforcement (speed, red-light, bus-lane, school-zone) | I4 | **no concept** (NEW-8). Provisionally `fixed-camera-unspecified`, tagged with a proposed `traffic-enforcement` family | Verra Mobility; Conduent / Modaxo; Sensys Gatso; Jenoptik; RedSpeed; Altumint; Hayden AI; Blue Line Solutions | — (new) | — |
| T10 | VA: video analytics | I4 | `video-analytics-object`, `video-analytics-loitering`, `video-analytics-unspecified` | BriefCam (Canon); Avigilon (Motorola); Veritone; Vintra; ZeroEyes and Omnilert (gun detection on video) | VA 1/6 | Video Analytics 85 |
| T11 | FRT: face recognition | I4 | `face-verification-1to1`, `face-identification-1ton`, `face-retrospective`, `face-live`, `face-clustering`, `face-recognition-unspecified` | Clearview AI; Rank One Computing; NEC NeoFace; Idemia; DataWorks Plus (FACE Plus); Cognitec; Paravision; Vigilant FaceSearch; Thales | FRT 10/25 | Face Recognition 980 (+6 "FRT") |
| T12 | BIO: other biometrics | I4 | `fingerprint-*`, `iris-*`, `dna-forensic`, `rapid-dna`, `dna-unspecified`, `tattoo-recognition`, `gait-recognition`, `voice-recognition`, `other-biometric-unspecified` | Idemia / Thales (mobile fingerprint); ANDE and Thermo Fisher RapidHIT (Rapid DNA); BI2 Technologies (iris) | — (new) | — |
| T13 | GSD: gunshot detection and acoustic sensing | I4 | `gunshot-detection-fixed`, `gunshot-detection-unspecified`, `acoustic-sensing-general`, `acoustic-sensing-unspecified` | SoundThinking (ShotSpotter); EAGL; Databuoy; Shooter Detection Systems; Safety Dynamics; Louroe. *Flock Raven → T29* | GSD 7/17 | Gunshot Detection 248 |
| T14 | UAS: drones and drone-as-first-responder | I4 | `uas-general`, `drone-as-first-responder`, `uas-unspecified` | Skydio; Brinc; DJI; Axon Air / Dedrone; Paladin; Parrot; Autel; Teal. *Flock Aerodome → T29* | UAS 7/18 | Drones 1,828 |
| T15 | AERO: aerostats and persistent / manned aerial surveillance | I4 | `tethered-aerostat`, `persistent-aerial-surveillance`, `aerostat-unspecified` | Persistent Surveillance Systems; TCOM; Logos Technologies; CBP TARS | — (new) | — |
| T16 | ROB: ground robotics and security robots | I4 | `ugv`, `robot-dog`, `ground-robotics-unspecified` | Boston Dynamics (Spot); Knightscope; Ghost Robotics | — (new) | — |
| T17 | CSS: cell-site simulators | I4 | `cell-site-simulator-general`, `cell-site-simulator-unspecified` | L3Harris (StingRay, Hailstorm); DRT "dirtbox"; KeyW / Jacobs; Octasic | CSS 1/3 | Cell-site Simulator 83 |
| T18 | LI: lawful intercept, metadata, tower dumps, Wi-Fi/BT tracking | I4 | `wiretap-content`, `metadata-interception`, `tower-dump`, `lawful-intercept-unspecified`, `wifi-bluetooth-sensor`, `wifi-bluetooth-tracking-unspecified` | carrier intercept (vendor-agnostic); traffic Bluetooth / Wi-Fi sensor vendors | — (new) | — |
| T19 | FOR: mobile forensics and exploit services | I4 | `extraction-logical`, `extraction-physical`, `cloud-account-extraction`, `exploit-service`, `mobile-forensics-unspecified` | Cellebrite; Magnet Forensics (GrayKey, AXIOM); MSAB (XRY); Oxygen Forensics; Belkasoft; Paragon; NSO | FOR 0/1 | — |
| T20 | SMM: social-media and OSINT monitoring | I4 | `social-media-monitoring`, `osint-platform`, `osint-monitoring-unspecified` | Babel Street; Dataminr; ShadowDragon; Skopenow; Voyager Labs; Media Sonar; Cobwebs / Penlink; Fivecast; Zignal Labs; Navigate360 (Social Sentinel); Geofeedia (historic) | SMM 0/0 | — |
| T21 | DATA: location-data and records brokers | I4 | `adtech-location-purchase`, `location-data-subscription`, `geofence-warrant-data`, `location-data-unspecified`, `person-records-broker`, `utility-records`, `records-broker-unspecified` | Fog Data Science (Fog Reveal); Venntel; Anomaly Six; Babel Street Locate X; Penlink; Thomson Reuters CLEAR; LexisNexis Accurint; TransUnion TLO; company transparency reports (geofence) | DB 3/4 | (in Third-party Investigative Platforms) |
| T22 | INV: investigative platforms and predictive / risk analytics | I4 | `third-party-investigative-platform`, `investigative-platform-unspecified`, `predictive-policing-*`, `risk-assessment`, `behavioral-analytics`, `risk-analytics-unspecified` | Palantir; SoundThinking CrimeTracer and ResourceRouter (Geolitica / PredPol); LexisNexis Accurint Virtual Crime Center; Cognyte; ForceMetrics | (DB, OTH) | Third-party Investigative Platforms 1,062; Predictive Policing 200 |
| T23 | BWC: body-worn and in-car video and evidence platforms | I4 | `bwc-recorded`, `bwc-livestream`, `body-worn-camera-unspecified`, `in-car-video-recorded`, `in-car-video-unspecified` | Axon (Body, Evidence.com); Motorola WatchGuard; Getac; Utility; Wolfcom; Reveal | BWC 1/1 | Body-worn Cameras 5,470 |
| T24 | EM: electronic and custodial monitoring | I4 | `electronic-monitoring-ankle`, `electronic-monitoring-unspecified`, `jail-communications-monitoring`, `custodial-monitoring-unspecified` | BI Inc (GEO Group); SCRAM; SuperCom; Track Group; Attenti; Securus; ViaPath; LEO Technologies (Verus) | — (new) | — |
| T25 | SCH: school surveillance suites | I4 | `school-surveillance-suite`, `school-surveillance-unspecified` | Gaggle; GoGuardian (Beacon); Securly; Lightspeed (Alert); Bark for Schools; Navigate360; Raptor; HALO sensors | SCH 2/2 (AU only) | — |
| T26 | WPN: weapon detection / facility screening | I4 | `weapon-detection-scanner`, `weapon-detection-unspecified` | Evolv; Xtract One; CEIA; Liberty Defense | — (new) | — |
| T27 | FUS: fusion centres and intelligence-sharing organisations | I4 | **no technology concept**: an organisation role | DHS-recognised fusion centres (spec §22.3: "54 primary + 26 recognized = 80", line 3702); HIDTA ISCs; RISS | FUS 4/5 | Fusion Center 81 |
| T28 | BORD: federal border and immigration surveillance and data access | I4 | cross-family: `alpr-checkpoint`, `plate-data-commercial-purchase`, `location-data-subscription`, `face-identification-1ton`, `persistent-aerial-surveillance` (as used by DHS / ICE / CBP) | ICE (287(g), ERO contracts); CBP (autonomous surveillance towers, Anduril; Elbit; TARS; OPSG); DHS HART | — (new) | — |
| T29 | FLOCK-XP: Flock Safety products in I4 classes | I3 | `gunshot-detection-fixed` / `acoustic-sensing-general` (Raven); `drone-as-first-responder` (Aerodome); `third-party-investigative-platform` (Nova) | Flock Raven; Flock Aerodome; Flock Nova | (in Atlas vendor 2,748) | — |

**Proof of completeness (code).** The 36 families map to the codes as follows:
- `alpr`: T01, T02, T03, T04 via the checkpoint/private-operator senses.
- `vehicle-fingerprint`: T01. `plate-data-commercial`: T04.
- `fixed-camera` and `camera-trailer`: T07, plus T08 by operator role.
- `private-camera-integration`: T06. `video-analytics`: T10.
- `body-worn-camera` and `in-car-video`: T23.
- `face-recognition`: T11. `fingerprint`, `iris`, `dna` and `other-biometric`: T12.
- `gunshot-detection` and `acoustic-sensing`: T13. `uas`: T14. `aerostat`: T15. `ground-robotics`: T16.
- `cell-site-simulator`: T17. `lawful-intercept` and `wifi-bluetooth-tracking`: T18. `mobile-forensics`: T19.
- `location-data` and `records-broker`: T21.
- `predictive-policing`, `risk-analytics` and `investigative-platform`: T22. `osint-monitoring`: T20.
- `rtcc`, `cad-rms` and `federation-hub`: T05.
- `electronic-monitoring` and `custodial-monitoring`: T24. `weapon-detection`: T26. `school-surveillance`: T25.

That is 36 of 36 families.

**Classes added beyond the operator's list:**
- ALPR-COM (T04). Private-operator plate data is the core of "public-private" networks.
- ATE (T09). It is the ontology gap, NEW-8.
- BIO, AERO, ROB, LI, EM and WPN (T12, T15, T16, T18, T24, T26). These are ontology families with no I1 class.
- The Flock carve-out (T29).

**Boundary rules.** These decide ties; the cell partition in §5 relies on them.
1. **The Flock carve-out.** Every Flock Safety product is I3's:
   - ALPR goes to T01–T04; FlockOS goes to T05; Flock camera integrations go to T06;
   - Raven, Aerodome and Nova go to T29.
   - I4's GSD, UAS, INV and DATA cells exclude Flock products.
2. **Axon split.** Axon Fleet ALPR goes to T02, Fusus to T05/T06, and Ring Community Requests via Axon to T06
   (all I3). Axon Body, Evidence.com, Axon Air and Dedrone go to T23/T14 (I4).
3. **Motorola split.** Vigilant, LEARN, DRN and the CommandCentral Aware/Community products go to T01–T06 (I3).
   WatchGuard goes to T23 and Avigilon analytics to T10 (I4).
4. **ALPR stays with ALPR.** Local-agency ALPR sharing with federal agencies, and federal purchase of commercial
   plate data, are **T03/T04 (I3)**, never T28. T28 covers the other federal border and immigration programmes.
5. **SoundThinking.** ShotSpotter goes to T13, CrimeTracer and ResourceRouter to T22, and PlateRanger to T01.
6. **Classify by function, not by site.** ZeroEyes and Omnilert are T10 even when they are sold to schools.
   Evolv is T26 even in schools. T25 is the student-monitoring suite itself.
7. **Vendor-only queries** (a vendor name with no class term) are attributed to the vendor's primary class:
   Flock → T01, Axon → T05, Motorola Solutions → T01, Genetec → T01, Rekor → T01, SoundThinking → T13,
   LexisNexis and Thomson Reuters → T21, Palantir → T22, Cellebrite → T19, Idemia and NEC → T11,
   Verkada → T07, Avigilon → T10.

**Operator-type facet (not a class).** Record it in `notes` as `operators=`. The values are:
`police`, `sheriff`, `state-police`, `dot`, `school-district`, `campus`, `transit`, `housing`, `hoa`,
`business`, `retail`, `federal`, `tribal` and `territorial`. Many public-private findings are about
*who operates* a device, not which technology it is.

---

## 3. Discovery-channel taxonomy

**Ownership type.**
- *Class-owned* channels are searched by the class row (I3 or I4) for single-class queries, and by I6 for
  multi-class (T00) queries.
- *Cross-cutting* channels belong to I6 unless a class holds a dedicated cell in that channel.
- **GS** marks channels that support a 51-jurisdiction state sweep.

**Reuse** names the existing connector family, from `runner.CONNECTOR_FOR_SOURCE`, or `new:<protocol>`.

| Code | Channel | Examples | Typical access | Typical rights posture | Part VIII risk | SIG reuse | Type · GS |
|---|---|---|---|---|---|---|---|
| C01 | VEND-PORTAL: vendor transparency portals and customer / community listings | Flock per-agency portals (`transparency.flocksafety.com/<slug>`); Axon Community Connect; Fusus "Connect ‹Place›" registration portals; Ring Neighbors agency lists; CommandCentral Community | HTML or JS app; often bot-managed | vendor ToS. Flock's forbids bulk extraction and its origin is **refused**. Axon Community Connect is gated REFERENCE | **High**: Flock portals can carry public search audits (case number, search reason, offense type, anonymised user id; search-summary, Appendix A C05) | `flock_portal` (Eyes on Flock mirror only); `new:vendor_listing` | class-owned |
| C02 | VEND-DISC: vendor disclosures | SEC EDGAR full-text search (10-K, 20-F: Axon, Motorola Solutions, Rekor, SoundThinking, Cellebrite, Evolv); newsrooms and case studies; company transparency reports (geofence, law-enforcement requests) | API (EDGAR FTS) or HTML | federal filings are factual; press releases are ©, so facts only | low | `new:sec_edgar_fts`; `dossier_documents:html_text` | class-owned |
| C03 | OPEN-DATA: government open-data catalogues and GIS | ArcGIS Hub / ArcGIS Online search; Socrata Discovery API; CKAN `package_search` (catalog.data.gov, state portals, open.canada.ca, data.gov.uk, data.gov.au); Opendatasoft Explore | JSON APIs | per-item licence or `licenseInfo`; personal-account republishes unknown (NEW-5; E1 NEW-13) | **High** for per-read ALPR, ATE violation and registrant layers; residential points get C3 demotion (SIG-PUB-005) | `dot_511:arcgis_query`, `dot_511:socrata_rows`; `new:ckan_package_search`, `new:opendatasoft_explore` | class-owned |
| C04 | STAT-REPORT: statutory, mandated and oversight reports | state legislative reference libraries (e.g. `lrl.mn.gov/docs/<yr>/mandated/…`); state police annual reports (e.g. VA §2.2-5517(J)); state auditors and IGs; city auditors; police commissions; DPAs and commissioners (intl) | PDF / HTML | public records; state and local works may carry © (not §105), so facts plus link | medium: names of auditors and officers (institutional test); no per-search rows | `dossier_documents:pdf_text`; `accountability` | class-owned · **GS** |
| C05 | POLICY-PROGRAM: published use policies and agency programme pages | CA SB 34 ALPR usage and privacy policies (Civ. Code §1798.90.51); CSS policies (CA Gov. Code §53166); drone, FR and BWC policies; camera-registry programme pages; Lexipol and PowerDMS manuals | PDF / HTML | agency text; Lexipol-authored text is Lexipol ©, so facts only | low (C3 for registrant pages) | `dossier_documents`; `okcpd_policy` pattern | class-owned · **GS** |
| C06 | CCOPS: surveillance-ordinance disclosures | annual surveillance reports, impact reports and use policies in CCOPS jurisdictions (Seattle, NYC POST, SF 19B, Oakland, Berkeley, Davis, Cambridge, Somerville, Boston, Baltimore, Nashville, Grand Rapids …) | PDF (none machine-readable, SIG-INGEST-049a) | public record; rights UNDETERMINED at class level (registry precedent) | medium: aggregated usage counts; annexes may name staff | `government_mandated_disclosure` | cross-cutting (**I6 everywhere**) |
| C07 | AGENDA: council, commission, school-board and county-board agendas and minutes | Legistar, PrimeGov, CivicClerk, eScribe (live); Granicus / IQM2, CivicPlus AgendaCenter, NovusAgenda, BoardDocs, Swagit (gated); Simbli / Diligent (school boards); ModernGov (UK) | APIs (Legistar), HTML, PDF attachments | public meeting records; vendor attachments carry their own © | medium: residents' names in minutes → redact at extraction | `procurement:{legistar,primegov,civicclerk,escribe}`; `new:{boarddocs,granicus,civicplus,novusagenda,moderngov}` | class-owned |
| C08 | PROC-VEHICLE: contract vehicles above the agency | cooperatives (Sourcewell, NASPO ValuePoint, GSA eLibrary / Advantage, HGACBuy, OMNIA, BuyBoard, TIPS, Equalis, S.A.V.E. / Tempe, NPPGov); state central procurement and statewide contracts; state checkbooks; aggregators (Pavilion, CivicIQ; GovSpend is paid) | HTML / PDF; some public files | the cooperative's own terms; the contract is a public record of the lead agency | low | `procurement:{sam_gov,usaspending,ted_eu}`; `new:coop_contract_docs`, `new:state_contract_register` | cross-cutting · **GS** |
| C09 | PROC-LOCAL: agency and local procurement, contracts and payments | city and county bid portals (OpenGov, Bonfire, BidNet, PlanetBids, DemandStar, Periscope), contract registers, executed agreements, sole-source justifications, vendor-payment checkbooks | HTML / PDF / portal APIs | public records; vendor exhibits carry separate rights | low–medium: signature blocks (institutional) | `procurement:{procportal_*,opengov,bonfire,bidnet}`; `dossier_documents:pdf_text` | class-owned |
| C10 | GRANT: federal and state grants | OJP award search (BJA, COPS, NIJ); FEMA HSGP / UASI / OPSG / TSGP; Treasury SLFRF project data; USAspending sub-awards (live); state administering agencies; state crime-reduction and auto-theft grants | APIs / CSV / PDF | federal works generally fall under 17 U.S.C. §105, with qualifications; state works vary | low | `procurement:fema_hsgp_allocations`; `usaspending`; `new:{ojp_awards,slfrf,state_grant_lists}` | cross-cutting · **GS** |
| C11 | LEG: legislation and legislation trackers | state legislature sites; OpenStates (live); NCSL; NAMSDL (legislativeanalysis.org); EPIC and IAPP trackers; LegiScan (API key = operator action); municipal codes; Federal Register | HTML / API | statute text is generally treated as public (government-edicts doctrine; verify, not a rights decision); tracker terms vary (verify) | low | `accountability:{openstates,congress_gov}`; `state_statute_seed` | cross-cutting · **GS** |
| C12 | COURT: court records | CourtListener / RECAP (gated); state appellate opinions; PACER is paid, so excluded | API / HTML | opinions are generally public (edicts doctrine; verify); dockets carry fees and terms | **High**: party names → metadata-level | `accountability:courtlistener_recap` | cross-cutting · **GS** |
| C13 | RECORDS: records-request corpora and reading rooms | MuckRock (projects, released files; WAF-403 to the hosted connector per I1); DocumentCloud; NextRequest / GovQA / JustFOIA public portals; federal FOIA libraries (DLA, ICE, CBP, FBI Vault); intl Alaveteli instances | HTML / API | uploader-controlled, per document; released documents are agency records | **High**: raw logs, e-mails, free text (SIG-PUB-014a) | `records:{muckrock,documentcloud}`; `new:{nextrequest,govqa,alaveteli}` | cross-cutting |
| C14 | CIVIL-DATA: NGO, journalism and academic datasets and repositories | EFF Atlas / SLS / Who Has Your Face; ACLU (CCOPS, CSS map, affiliates); Georgetown CPT; Upturn; Brennan Center; Bard CSD; Lucy Parsons Labs; S.T.O.P.; Oakland Privacy; Surveillance Watch; 404 Media; The Markup; CDT; Dataverse / Zenodo / GitHub / ICPSR | CSV / HTML / PDF | each dataset's licence (EFF CC-BY-4.0 with a third-party caveat, SC-09); journalism is © (facts only) | medium–high: some datasets are person-level | `atlas`; `data_driven`; `pathways`; `curated_index`; `coarse_international` | cross-cutting |
| C15 | CROWD: crowdsourced maps and community projects | OSM / DeFlock; Eyes on Flock; ALPR Watch; flock-finder; Surveillance under Surveillance; local "Eyes Off" groups; WiGLE (RF) | API / exports | ODbL, CC-BY-SA or unknown; small-project compact: ask first (§26 rule 6) | **High**: RF-derived candidates (SIG-PUB-011…014); residential intersections (SIG-PUB-013) | `osm`; `flock_portal` | class-owned |
| C16 | FED-REG: federal regulatory, compliance and statistical records | FAA Part 107 / DFR waivers and COAs (SRC-025); DHS PIAs and SORNs; federal AI use-case inventories; DLA LESO 1033 (SRC-024); BJS LEMAS / CSLLEA; NCES SSOCS / CRDC; ICE 287(g) list; US Courts wiretap reports | PDF / CSV / API | federal works generally §105, with qualifications; ICPSR downloads need an account (prior knowledge, verify; creating one is an operator action) | medium: FAA waivers carry remote-pilot personal fields (SRC-025 `screening_required`) | `agency_registry`; `new:{faa_waivers,ai_inventory,lemas,uscourts_tables,ice_287g_list,nces_tables}` | class-owned |

**Discovery tools, not channels.** These are logged as `engine_or_tool` (§8):
- search engines (the `WebSearch` tool; `site:` / `filetype:` operators);
- `hub.arcgis.com/api/search/v1/collections/dataset/items?q=`, which supports `bbox=` and `limit=`;
- `api.us.socrata.com/api/catalog/v1?q=`, which supports `domains=`;
- `…/api/3/action/package_search?q=` (CKAN);
- `…/api/explore/v2.1/catalog/datasets?where=search("…")` (Opendatasoft);
- `efts.sec.gov/LATEST/search-index?q=` (EDGAR full-text);
- local captures (`local:`).

**International equivalents crosswalk (I5 only).** Cells with no mechanism for a country go to that group's
`CRES` residual cell.

| Channel | UK | Canada | Australia / NZ | EU/EEA | Rest of world (GI3) |
|---|---|---|---|---|---|
| C03 open data | data.gov.uk (CKAN); London Datastore | open.canada.ca (CKAN); Ontario and BC catalogues; many city Opendatasoft / ArcGIS | data.gov.au (CKAN); data.govt.nz | data.europa.eu; GovData.de; data.overheid.nl; datos.gob.es; dati.gov.it; data.gouv.fr | national portals; ArcGIS Hub with a country filter |
| C04 reports / regulators | Biometrics and Surveillance Camera Commissioner (live row `uk_surveillance_camera_commissioner`); ICO; HMICFRS; police LFR DPIAs | OPC; provincial IPCs (Ontario, BC OIPC) | OAIC; state ombudsmen / IBAC; NZ OPC; IPCA; NZ Police technology reviews | national DPAs (CNIL, AEPD, Garante, Datatilsynet, Dutch AP, Belgian APD); statutory camera registers (DK, AT, BE — gated rows) | information regulators (e.g. South Africa); national courts |
| C06 CCOPS analogue | UK ATRS (SRC-026); Surveillance Camera Code self-assessments | municipal privacy impact assessments | — | municipal algorithm registers (Amsterdam, Helsinki) | — |
| C07 agendas | ModernGov council minutes | eScribe (live platform), Granicus | InfoCouncil and council agendas | municipal council portals | — |
| C08/C09 procurement | Contracts Finder, Find a Tender (OCDS) | CanadaBuys, MERX, BC Bid | AusTender (OCDS), NZ GETS | TED (live), DECP (live, FR), PLACE (ES), BOAMP (FR) | Colombia SECOP (Socrata), Chile Mercado Público, Brazil PNCP, Mexico CompraNet |
| C11 legislation | legislation.gov.uk | Justice Laws; CanLII | AustLII; legislation.govt.nz | EUR-Lex (AI Act); national gazettes | national gazettes |
| C13 records corpora | WhatDoTheyKnow | ATIP completed-request summaries (open.canada.ca) | Right to Know (AU); FYI.org.nz | FragDenStaat (DE); AskTheEU; Madada (live, FR) | Alaveteli instances where present |
| C14 civil data | Big Brother Watch; Liberty; Privacy International | BCCLA; Citizen Lab | Digital Rights Watch | Statewatch; EDRi; AlgorithmWatch; Technopolice / LQDN (gated rows) | Internet Freedom Foundation (Project Panoptic, IN); CESeC O Panóptico (BR); Right2Know (ZA); R3D (MX); ADC (AR); SMEX (MENA) |

---

## 4. Geography frame

### 4.1 Groups

| Group | Definition | Owner | Order of work |
|---|---|---|---|
| G0 | US national sweep: unanchored queries, or systematic iteration over all states or places used purely as partition keys | class row (I3 / I4); I6 for T00 | iterate places by the gap weights below |
| GS | US state sweep (50 + DC) in the GS channels (C04, C05, C08, C10, C11, C12) | class row; I6 for T00 | inventory-first, then per-state verification by gap weight |
| GP | any CCOPS jurisdiction, place-anchored C06 retrieval | I6 | registry `ccops_*` rows first |
| GD | US state-anchored data channels (all channels except the GS channels) | I5 | state weight, tier A → C |
| GL1 | the 36 thin top-100 cities (≤ 3 I1 sources) | I5 | city weight |
| GL2 | the other 64 top-100 cities | I5 | city weight |
| GL3 | the top-100 county-level entities by Census V2024, minus those consolidated or coterminous with a top-100 city (about 88) | I5 | population |
| GL4 | localities in tier-A/B states that are not in GL1–GL3 | I5 | largest city, then capital, then largest county |
| GL5 | every other US locality (container only) | I5 | by need |
| GT | the territories (PR, GU, VI, AS, MP) and tribal nations | I5 (all classes) | PR first |
| GI1 | UK, Canada, Australia, New Zealand, Ireland | I5 (all classes) | UK, CA, AU, NZ, IE |
| GI2 | EU/EEA + Switzerland | I5 (all classes) | NL, DE, FR, BE, DK, AT, ES, IT, SE, PL, others |
| GI3 | priority rest of world | I5 (all classes) | BR, MX, ZA, IN, AR, CO, CL, IL, AE, SG, JP, KR, TW, PH, TH, MY, ID, SA, KE, NG |
| GIW | other countries and global-unanchored queries (container) | I5 | by need; country-level stays coarse (SIG-INGEST-042) |

**Anchoring rule.**
- A class-specific query about a US place (for example `"Charlotte" "Flock Safety" agreement`) belongs to the
  class row's **G0** cell for that channel. In a GS channel it belongs to the **GS** cell.
- I5's US place cells are **multi-class**: bundle queries plus channel identification (which open-data portal,
  agenda platform, procurement portal, policy manual, oversight body or records portal a place uses).
- Outside the US, and in GT, I5 owns every class.
- C06 belongs to I6 in every geography.

### 4.2 US state gap weight (from I1 §3)

`w_state = 0.25·b + 0.15·dot + 0.10·fl + 0.10·leg + 0.25·e + 0.15·f`, where:
- b = 1 if the state has no official site registry (DOT/CCTV/ALPR = 0/0/0);
- dot = 1 if it has no DOT source;
- fl = 1 if it has no Flock portal in the mirror;
- leg = 1 if it has no state-legislation claims;
- e = clip((8 − n)/4, 0, 1), with n = distinct ingested sources with local evidence;
- f = the missing share of the big-9 classes.

"No dossier" (NEW-4) is excluded on purpose. I1 ranks it a product-attribution fix (#3), not a search gap.
Tiers: **A** ≥ 0.50, **B** 0.30–0.49, **C** < 0.30.

| Tier | States (w) |
|---|---|
| A (10) | VT 0.85 · NH 0.82 · DE 0.78 · MS 0.78 · RI 0.72 · WV 0.72 · ME 0.67 · WY 0.67 · AR 0.56 · MI 0.56 |
| B (5) | HI 0.48 · ND 0.38 · DC 0.34 · MT 0.34 · NM 0.31 |
| C (36) | AK 0.28 · KY 0.18 · SC 0.17 · CT 0.16 · ID 0.11 · SD 0.11 · NE 0.10 · UT 0.10 · WI 0.10 · OH 0.08 · IA 0.03 · OR 0.03 · AL, AZ, CO, KS, MN, NC, NV, OK, TX, VA 0.02 · CA, FL, GA, IL, IN, LA, MA, MD, MO, NJ, NY, PA, TN, WA 0.00 |

Special cases:
- Texas's statewide `dot_511_tx` is gated (rights UNDETERMINED).
- Oklahoma is the pilot: it has no dossier, and `okc_council` is unverified.
- Tier-C states still get I3/I4 statutory sweeps (GS). The weight orders the work; it does not exclude a state.

### 4.3 Top-100 cities (from I1 §4; Census V2024 SUB-EST2024)

`w_city = 0.4·s + 0.2·r + 0.2·g + 0.2·k`, where:
- s = clip((5 − Srcs)/3, 0, 1);
- r = 1 if the city has no official registry in its radius;
- g = 1 if it has no fetched agenda tenant;
- k = 1 − min(classes, 14)/14.

**GL1, the thin cities (36; ≤ 3 sources), by weight:**
Jersey City 0.97 · North Las Vegas 0.97 · Cape Coral 0.94 · Durham 0.93 · Omaha 0.91 · Lincoln 0.91 ·
Anchorage 0.91 · Charlotte 0.90 · Memphis 0.87 · Indianapolis 0.86 · Frisco 0.82 · Tulsa 0.80 · Wichita 0.78 ·
Norfolk 0.78 · Greensboro 0.77 · Chesapeake 0.77 · Virginia Beach 0.75 · Boise 0.61 · Henderson 0.60 ·
St. Petersburg 0.60 · Hialeah 0.60 · Irvine 0.58 · Newark 0.58 · Plano 0.57 · Tampa 0.55 · Honolulu 0.55 ·
Anaheim 0.55 · Madison 0.55 · Winston-Salem 0.55 · Nashville 0.54 · Cleveland 0.54 · St. Paul 0.54 ·
Detroit 0.52 · Albuquerque 0.52 · Las Vegas 0.51 · Houston 0.48.

**GL2** is the other 64 cities. The top of the list is Oklahoma City 0.58 (the pilot: no Flock portal in the
mirror, no dossier), then Gilbert 0.48, Chandler, Fort Wayne, Lubbock and Irving at 0.45, Arlington TX 0.43, and
San Jose, Raleigh, Bakersfield, Cincinnati and Scottsdale at 0.42. The median is 0.25.

### 4.4 Counties (GL3)

I1 did not tabulate counties. I5 derives the list from the I1 capture `sub-est2024.csv` (SUMLEV 050, sorted by
`POPESTIMATE2024`; 3,144 county-level rows). The first entries are Los Angeles, Cook, Harris, Maricopa,
San Diego, Orange CA, Miami-Dade, Dallas, Kings and Riverside. Exclude county-equivalents that are consolidated
or coterminous with a top-100 city: the five NYC boroughs, San Francisco, Denver, Philadelphia, DC,
Nashville-Davidson, Louisville-Jefferson, Indianapolis-Marion, Jacksonville-Duval and Honolulu. The city anchor
wins for those.

Caveats I5 records:
- Connecticut's county-level rows are 2022+ **planning regions** ("Capitol Planning Region"), not governments.
- Several Massachusetts counties have no county government; use sheriffs and regional bodies there.

Default weight: 0.6 until I5 measures each county's coverage.

### 4.5 Territories, tribal nations and international

**Territories and tribal nations.**
- PR has local traces: OSM 166 points, Atlas 13 rows, and OpenStates matches. GU and VI have 2 and 3 Atlas rows;
  AS and MP have nothing. Tribal nations have no source of any status (I1 §5).
- Enumerate tribes from the BIA tribal-leaders directory, fetched by I5; do not assume a count.
- Publication care: tribal sovereignty and data governance. Candidates carry `flag` with the note
  `tribal-sovereignty`.

**International tiers.** These are inference, ordered by I1's local coverage, feasibility (open-records
culture, structured portals) and salience.
- **GI1** has partial coverage already: UK about 17 camera registries (Nottingham axis-swapped, NEW-2), Canada
  about 18, AU 7, NZ 3, IE 1. UK ANPR camera locations are withheld by national policy (search-summary,
  Appendix A C10), so for UK ANPR expect counts, not points.
- **GI2** has TED live, several statutory camera registers that are gated rows (DK, AT, BE, NL cities), and
  strong DPAs.
- **GI3** has coarse-only coverage today (Carnegie AIGS, FR World Map). It contains the notable public-private
  analogue, Vumacam (ZA): a private ALPR/CCTV network with metro-police access (search-summary, C13).
- **GIW** covers China, Russia and the rest. They stay coarse (SIG-INGEST-042); ASPI's China row is WAF-403.

**Operator input hook (Q-20).** When D1 Q-D1-13 is answered (places, agencies, vendors or technologies to
prioritise or avoid), that answer overrides the ordering above. Rows starting before it is answered use this
frame and say so in their notes.

---

## 5. The search matrix (`data/search_matrix.csv`)

### 5.1 Cells

`cell_id = <row>-<class>-<channel>-<geo>`, for example `I3-T01-C03-G0`. `TRES` and `CRES` mark residual cells.
There are four **kinds** of cell:

| Kind | Meaning | Stopping rule |
|---|---|---|
| `sweep` | an open-ended search | the saturation rule (§5.4) |
| `enumerate` | an ordered list of states or places | per-item outcome, including negatives, until `q_max` or the end of the list |
| `residual` | the row's classes or channels without a dedicated cell | one probe query; continue as a P3 sweep only if the probe yields |
| `container` | GL5 and GIW | by need; `q_min` 0 or 1 |

### 5.2 Ownership function (exact partition)

For a (class `t`, channel `c`, geography `g`) triple:

```
if c == C06:                      -> I6-T00-C06-G0 (unanchored) | I6-T00-C06-GP (place-anchored)
if g is a US state anchor:        g := GS if c in {C04,C05,C08,C10,C11,C12} and t != T08 else GD
if g in {GT, GI1, GI2, GI3, GIW}: -> I5 dedicated (T00,c,g) else I5-CRES-CRES-g        # all classes
if g in {GD, GL1..GL5}:
    if t in {T00, T08}:           -> I5 dedicated (t or T00, c, g) else I5-CRES-CRES-g
    else:                         g := GS if c in GS-channels else G0                     # class-specific folds to national
if t == T08:                      -> I5 dedicated (T08,c,g) else I5-CRES-CRES-GD
if dedicated (t,c,g) exists:      -> it
if g == GS and t in {T02,T03,T04} and (T01,c,GS) dedicated: -> that cell               # ALPR state sweeps cover T01–T04
if c is cross-cutting or t == T00: -> I6-T00-c-g
else:                             -> <row(t)>-TRES-c-g
```

**Check performed.** 30 classes × 16 channels × 13 geography inputs (G0, a state anchor, GD, GL1–GL5, GT, GI1,
GI2, GI3, GIW), i.e. 6,240 triples. Every triple resolves to an existing cell, and no cell is unreachable.

The `covers` column lists the classes each cell covers. To re-verify from the CSV alone:
1. Apply the fold rules above.
2. For each (class, channel, geo), exactly one row's `covers` must contain the class.

**Query attribution.**
- Each issued query is logged under exactly one cell of the issuing row: its `notes` start with `cell=`.
- The query's class terms, channel mechanism and anchoring must match that cell.
- A query that would fit two cells is split or re-worded.

### 5.3 Priority weight

`w = 0.3·E + 0.3·B + 0.4·Y`. Tiers: **P1** ≥ 0.70, **P2** ≥ 0.50, **P3** otherwise. All three inputs are
stored per cell, so the ranking is reproducible and a reviewer can re-weigh it.

**E, operator emphasis** (the operator's words, §7.1):

| E | Applies to |
|---|---|
| 1.0 | Flock, Axon and other public-private networks: T01–T06 and T29 |
| 0.8 | whole missing classes (SMM, FOR, SCH, ATE) and gap geographies (GD, GL1, GL3, GL4, GT) |
| 0.7 | GI1 |
| 0.6 | Atlas-only classes, CCTV, T00 cross-cutting cells and GI2 |
| 0.5 | GL2 and GI3 |
| 0.4 | BIO, AERO, ROB, LI, EM, WPN and BORD |

**B, blind-spot relevance** = `(15 − rank)/14`, multiplied by 1.0 if I1 §7 names this channel for that blind
spot and by 0.5 if it is only adjacent:

| I1 blind spot | Rank | Channels named |
|---|---|---|
| Flock at origin and at scale | #1 | C01, C03, C04/C05, C07, C08/C09, C13, C15 |
| Axon/Fusus, PPN and RTCC | #2 | C01, C05, C07, C09 |
| Statutory and ordinance reporting | #4 | C04, C06, C11 |
| Official camera / DOT registries | #5 | C03, T08 |
| Procurement | #6 | C08, C09 |
| Zero-channel classes | #7 | C07, C08, C09, C06 |
| UAS / GSD / FRT / CSS | #8 | C16, C09, C05, C04, C13 |
| Thin cities | #9 | C03, C07, C06, C05 |
| Mobile ALPR and sharing currency | #10 | C13, C04, C09, C07 |
| International | #11 | C04, C08/C09, C03 |
| Records and courts | #12 | C13, C12 |
| Data brokers | #13 | C09, C08, C16 |
| Territories and tribal | #14 | C09, C11, C16 |

Rank #3 (jurisdiction attribution) is not a search cell, by I1's own note.

**Y, expected yield:**

| Y | Meaning |
|---|---|
| 1.0 | calibration showed many hits (e.g. ArcGIS "flock" 1,266; camera-registry pages; school-board approvals; FAA waivers; Atlas-cited grant programmes) |
| 0.6–0.8 | plausible multiple candidates |
| ≤ 0.5 | uncertain |

Y is an estimate labelled as such; it is the only input a row may revise. A row that revises Y logs the reason
in its research note. It never re-tiers another row's cells.

### 5.4 Stopping rules

The **new** count for a query is the number of candidates it produced that are new to the row's
`candidates_I<n>.csv` and are not mirrors of one of them. A registry `same-as:` counts as **not** new.

| Tier | `q_min` | K (consecutive zero-new queries) | `q_max` (sweep) | `q_max` (enumerate) |
|---|---|---|---|---|
| P1 | 4 | 3 | 15 | 25 |
| P2 | 2 | 2 | 8 | 15 |
| P3 | 1 | 1 | 3 | 6 |

- **Sweep.** Stop when `queries ≥ q_min` and the last K queries yielded 0 new, **or** at `q_max`. A cell still
  yielding at `q_max` may extend by up to 50% if the row budget allows. Record it as `extended`.
- **Enumerate.**
  1. Go inventory-first: use an existing compilation to shortlist items (e.g. NAMSDL's 2025 ALPR summary, the
     NCSL seed, `agenda_tenants.toml`, catalog APIs with `domains=` or `bbox=` filters).
  2. Verify each shortlisted item at its origin. Origin checks are fetches, not queries.
  3. Record a per-item outcome: `found`, `negative` (searched and found nothing, which is a coverage fact), or
     `not-reached`.
  4. Stop at `q_max` or at the end of the list.
- **Residual.** Run one probe with the class bundle, for the highest-gap uncovered class. If it yields,
  continue under P3 sweep rules.
- **Cell closing status** (research-note table): `saturated`, `extended`, `capped-unsaturated`,
  `enumerated(n found / m negative / r not-reached)`, `blocked(access)`, `not-started(budget)` or
  `n/a(reason)`.
- **Row stop.** The row stops at its query budget, its fetch cap, or the context guard (R11).

### 5.5 What counts

| Unit | Id | Counts against | What it is |
|---|---|---|---|
| Query | `I<n>-Q###` | the query budget | one query string sent to one engine or API |
| Page | `I<n>-Q###.p<k>` | nothing | a page of one query; at most 20 pages or 1,000 results per query |
| Fetch | `I<n>-F###` | the fetch cap | one GET of a specific URL (landing page, metadata endpoint, document) |
| Local operation | `I<n>-L###` | nothing | a read of a local capture or registry file |

A follow-up fetch of a URL surfaced by the row's own query is logged under that query's cell, whatever place it
is about.

### 5.6 Cells, tiers and minimum load per row

| Row | Cells | P1 | P2 | P3 | Σ `q_min` | Query budget | Fetch cap | Split if needed (P12) |
|---|---|---|---|---|---|---|---|---|
| I3 | 40 | 15 | 11 | 14 | 96 | 150 | 250 | I3a = T01–T04 · I3b = T05–T07, T29 and residuals |
| I4 | 74 | 5 | 28 | 41 | 117 | 170 | 250 | I4a = T09–T18 · I4b = T19–T28 and residuals |
| I5 | 53 | 3 | 15 | 35 | 76 | 150 | 250 | I5a = US (GD, GL1–5, GT, T08) · I5b = international |
| I6 | 23 | 4 | 11 | 8 | 46 | 130 | 200 | I6a = C06, C08, C10, C11 · I6b = the rest |

I4 gets 170 queries and I6 130, against the "≤ 150 each" example. I4 spans 20 classes. I6's cells are few, but
each spans many publishers, and its enumerations use their own `q_max`. Total: 600 queries.

### 5.7 Snowballing

- **Backward.** Follow a candidate's own citations and links one hop (two hops for P1 cells). Prefer the origin
  document over any copy.
- **Forward.** P1 cells only: search for pages that cite the candidate's title or identifier.
- **Contract back-chaining** (S5). Local order → cooperative master id → master contract → other local orders.
  - I3 and I4 record master ids they meet in `notes`.
  - I6 owns the cooperative side.
- **Stop.** The same saturation rule applies. Snowball fetches count against the fetch cap.
- **Exclusive snowball sources.** Each source is followed by one row only:

| Row | Snowball sources |
|---|---|
| I3 | Eyes on Flock (local capture); DeFlock / OSM; Have I Been Flocked; ALPR Watch; footnote4a; Drivers Against Flock; local "Eyes Off" groups; 404 Media (ALPR and ICE-lookup reporting); EFF Data Driven; ACLU Flock toolkit; Monahan; NAMSDL and NCSL ALPR summaries; CA State Auditor 2019-118; the SB 34 policy postings |
| I4 | Bard CSD; Upturn *Mass Extraction*; Georgetown CPT (*Perpetual Line-Up*); EFF *Who Has Your Face*; BuzzFeed Clearview table; ACLU CSS map; Brennan Center; The Markup; CDT; EFF *Red Flag Machine*; Just Futures Law / Mijente; Citizen Lab; MacArthur Justice Center; US Courts wiretap reports; FAA waiver lists |
| I5 | international NGOs and FOI corpora (§3 crosswalk); BIA directory; Census place and county lists (I1 captures) |
| I6 | MuckRock; DocumentCloud; EFF Street-Level Surveillance; EPIC; Lucy Parsons Labs; S.T.O.P.; Oakland Privacy; ACLU affiliates' CCOPS trackers; NYU Policing Project; Surveillance Watch; Pavilion / CivicIQ; OJP / COPS / FEMA / Treasury SLFRF; BJS LEMAS; AI inventories; DLA LESO; LegiScan / NCSL / IAPP / EPIC trackers; CourtListener |

**The Atlas citation mine.** This is a local operation on `atlas.csv`: 26,294 links across 4,134 domains.
Links wrapped in `web.archive.org` are resolved to their original host first. Each Atlas row and link goes to
exactly one row, in this order:
1. Domain `documentcloud.org` or `muckrock.com` → **I6** (4,971 links).
2. Atlas `State` in tier A/B, (City, State) in GL1, or a territory → **I5** (2,708).
3. `Technology` ∈ {Automated License Plate Readers, Camera Registry, Real-Time Crime Center} → **I3** (4,677,
   including 507 links to Flock portals).
4. Otherwise → **I4** (13,938; BWC-heavy).

Rows mine *domain frequency tables* for their partition. They then fetch only the government and publisher
domains that suggest a new channel. The Atlas itself is registered and live, so an Atlas link is a lead to an
origin; it is not independent corroboration.

### 5.8 CSV columns (`search_matrix.csv`)

| Column | Meaning |
|---|---|
| `cell_id` | the cell identifier (§5.1) |
| `row` | the owning row: I3, I4, I5 or I6 |
| `split_if_needed` | the predefined P12 split this cell goes to |
| `kind` | `sweep`, `enumerate`, `residual` or `container` |
| `tech_classes` | the class code, or TRES / CRES |
| `covers` | the classes this cell covers; for residuals, the classes resolved by the ownership function |
| `ontology_concepts` | the technology slugs (§2) |
| `channel` | the channel code and name |
| `geo_group`, `geo_scope` | the geography group and its description |
| `gap_refs` | I1 blind-spot rank; `(adjacent)` marks the 0.5 factor |
| `E`, `B`, `Y`, `weight`, `priority` | the priority inputs and result (§5.3) |
| `q_min`, `k_stop`, `q_max` | the stopping parameters (§5.4) |
| `seed_query_templates` | engine-agnostic templates. Placeholders: `{vendor}`, `{product}`, `{kw}`, `{bundle}`, `{place}`, `{city}`, `{county}`, `{state}`, `{statute}`, `{year}`, `{agency}`; alternatives separated by ` \| ` |
| `seed_query_examples` | concrete instances |
| `snowball_sources` | the exclusive snowball sources for the cell |
| `connector_reuse_hint` | the connector family to prefer |
| `part_viii_watch` | the cell-specific Part VIII hazard |
| `notes` | anything else |

**Keyword bundles.**
- The multi-class **bundle** is `surveillance | camera | "license plate" | ALPR | drone | "facial recognition" |
  ShotSpotter | "real time crime" | Flock | Fusus`.
- Each class's own keyword and vendor list is the §2 row.
- For I5, use the local-language equivalents: *ANPR*, *LPR*, *videovigilancia*, *vidéoprotection*,
  *Kennzeichenerfassung*, *reconhecimento facial*, *cámaras de seguridad*, *reconocimiento facial*,
  *cameratoezicht*, *videoovervågning*.

---

## 6. Inclusion and exclusion criteria

**Include** a candidate when all five of these hold:
1. It evidences **institutions and infrastructure** (SIG-PUB-001) for a §2 class: deployments, contracts,
   funding, policies, sharing arrangements, programme registrations, oversight, or usage aggregates.
2. It is **publicly reachable** without login, payment or circumvention.
3. It has an identifiable **publisher**.
4. It has a **stable locator** (URL, API endpoint, or document identifier).
5. It closes or narrows a **named gap** (R9).

Historical and one-time artifacts qualify. Label them with their time window and `update_cadence=static`, and do
not create any expectation of recurrence (SIG-INGEST-025b).

**Include as a lead only.** Set `candidate_level=channel`, put `LEAD-ONLY` in `notes`, and use format `other`.
- **Statutory duties to hold or report records** where no publication was found. A duty is a records-acquisition
  lead, not a feed (SIG-INGEST-025a). Duties enacted but not yet due are registered now, with their
  commencement date (SIG-INGEST-050).
- **Access-blocked sources** (`403`, challenge, login). Record the status observed and do not retry.
- **Paid services** (GovSpend, PACER, Periscope premium). Note `PAID; Q-21 zero budget`.

**Exclude.** Log the exclusion in the query-log `notes`; add no candidate row.
- Leaked or hacked material, or material of leak provenance. The registry precedent is `wired_shotspotter_leak`,
  refused.
- Social-platform posts (Facebook: 825 Atlas links; X; Nextdoor), except an agency's own official page used as
  a pointer to an origin document.
- Pure marketing that names no deployment, customer or contract.
- Duplicates of a candidate already captured. Merge them: add the URL to that candidate's `notes`.
- Anything whose only content is person-level (plate reads, individual travel, per-search audit rows with
  operator ids, student alerts, inmate communications, person-records broker outputs). **Exception:** when such
  a source reveals a channel for an *aggregate* lane (e.g. per-agency search counts), capture a metadata-only
  candidate with `part_viii_verdict=block`, and never touch the rows (R6).

**Temporal preference.** Prefer sources published or updated since 2022 (the Flock expansion era). Older
sources are kept when they are the only evidence, or when they are the historical baseline (EFF Data Driven
2016–17, Bard 2020, Upturn 2020).

---

## 7. Candidate capture procedure

### 7.1 Steps

1. **Find it** in one of your cells.
2. **Fetch the landing page or metadata endpoint.** Examples: ArcGIS `…/FeatureServer?f=json` plus the item
   JSON; Socrata `/api/views/<id>.json`; CKAN `package_show`. Record the fetch id, `run_at`, HTTP status and
   sha256.
3. **Identify the publisher and the origin.** The publisher is the institution that controls the content, not
   the hosting platform. The origin is where the institution itself published it.
4. **Capture the terms verbatim:**
   - the dataset licence field (`licenseInfo`, `license_id`, `accessInformation`);
   - the site terms page;
   - the robots verdict if you read it.
   A quote of at most 600 characters goes in `terms_verbatim_excerpt`.
5. **Run the Part VIII preflight (§7.4)** before reading anything beyond metadata.
6. **Decide lineage (§7.5).**
7. **Dedupe against the registry and queue (§7.6).**
8. **Record connector reuse** (§3 column), or `new:<protocol>`.
9. **Write the row.** Families of many homogeneous targets (e.g. 38 agency Flock layers) are written as one
   `family` row plus one `target` row per member, sharing `family_id`.

### 7.2 The §8.6 fields: how to fill them

| Field | Rule |
|---|---|
| `cand_id` | `I<n>-C###`, unique in the row |
| `name` | the publisher's own title |
| `url` | the canonical origin URL: https, lowercase host, tracking parameters stripped, identifying parameters kept (ArcGIS item id and layer index, Socrata 4×4) |
| `publisher` | the institution (e.g. "City of Pueblo, CO (via ArcGIS Online)") |
| `publisher_type` | the §8.6 enum |
| `technology_classes` | §2 codes, `;`-separated |
| `geographies` | I1 notation: `US`, `US-XX`, `US-XX:City`, `US-XX:<County> County`, `US-TRIBAL:<BIA name>`, `ISO:CC`, ISO 3166-2, `EU/EEA`, `INTL`. Never a bare two-letter code (NEW-1). |
| `coverage_estimate` | a number with its denominator and evidence class, e.g. `12 layers of 1,266 hub hits (live-read)` |
| `format_access` | the §8.6 enum |
| `update_cadence` | `static`, `irregular`, `annual`, `biennial`, `quarterly`, `monthly`, `weekly`, `daily`, `realtime` or `unknown`, with its basis |
| `volume_estimate` | rows, documents or bytes, with its basis (metadata count or page count) |
| `terms_url` | the terms page URL, or `NONE-FOUND(checked: <urls>)` |
| `terms_verbatim_excerpt` | the verbatim quote, or `NONE-FOUND` |
| `licence_guess` | an SPDX id or `LicenseRef-*`, always prefixed `guess:` |
| `rights_lane` | the three ADR-130 lanes, e.g. `bytes=undetermined; facts=likely-open; derived=undetermined`. Lane values: `undetermined`, `likely-open`, `likely-restricted` or `prohibited-by-terms`. A lane is never `decided`. |
| `part_viii_flags` | §7.4 flags, `;`-separated, or `none-observed` |
| `lineage` | `origin`, `mirror-of:<cand_id or source_id>` or `derived-from:<cand_id or source_id>` |
| `registry_match` | `new`, `same-as:<source_id>` or `related:<source_id>`. Queue ids are allowed: `same-as:SRC-0xx`. |
| `connector_reuse` | the §3 vocabulary |
| `retrieved_at` | `date -u` of the fetch |
| `found_by_query_id` | the query and fetch ids, `;`-separated |
| `evidence_class` | `live-read` for anything fetched; `inference` only in `notes` |
| `notes` | free text, plus the tagged keys `operators=`, `access=`, `LEAD-ONLY`, `PAID`, `out-of-cell→<cell_id>`, `contract_ids=` and `award_ids=` |

### 7.3 I2 extension columns

These are appended after `notes`, in this order. They are proposed to the orchestrator for §8.6. I7 may drop
them, but must not reorder the §8.6 columns.

| Column | Meaning |
|---|---|
| `cell_id` | the cell that found the candidate |
| `candidate_level` | `channel` (spans many publishers), `publisher`, `family` or `target` |
| `family_id` | shared by a family row and its members |
| `vendors` | normalised names, `;`-separated |
| `ontology_concepts` | technology slugs; for T09, the proposed concept |
| `lineage_class` | the S5 closed vocabulary (`tasks/acquisition.py:162`): `same_bytes`, `republished_document`, `derived_summary`, `new_version`, `response_to`, `amends` or `independent_account` |
| `part_viii_verdict` | `pass`, `flag` or `block` |
| `access_check` | e.g. `200 GET 2026-…Z; robots=retrieved/allowed` or `403 challenge` |
| `gap_ref` | e.g. `I1#1`, `I1:state=VT`, `I1:city=Charlotte`, `NEW-6` |

### 7.4 Part VIII preflight

Run it before reading beyond metadata. Inspect the schema or metadata, never the rows. The flags and verdicts:

| Flag | Trigger | Verdict |
|---|---|---|
| `plate-level` | plate numbers or reversible derivatives, per-read rows (SIG-PUB-002, SIG-STORE-026) | **block** |
| `per-search-audit` | per-search or per-query audit rows (SIG-STORE-025) | **block** (aggregate lane only) |
| `operator-identifier` | user, operator or account ids, hashed or not (SIG-PUB-003a–c; "it is already public" is no defence) | **block** |
| `officer-name` | officer names in audit rows (SIG-PUB-010) | **block**. Names in institutional roles in reports → `flag`. |
| `private-person-name` | incidental private names (minutes, e-mails, free text) | flag (extraction-time redaction) |
| `home-address` | any home address (SIG-PUB-003; categorical) | **block** |
| `private-registrant-location` | camera-registry registrants, HOA or business device points (SIG-PUB-004 C3) | flag (no location; programme-level facts only) |
| `confidential-facility` | shelters, protective or undercover sites (C4) | **block** location |
| `minor-data` | students, school alerts, juvenile records | **block** |
| `person-level-enforcement` | immigration status, monitoring subjects, broker outputs, risk scores | **block** |
| `free-text-narrative` | records-release or government free text (SIG-PUB-014a) | flag (pre-publication screen) |
| `rf-derived-candidate` | BLE / Wi-Fi / RF device fingerprints (SIG-PUB-011…014) | flag (never a public device layer) |
| `residential-intersection` | points on residential parcels (SIG-PUB-013) | flag |
| `biometric-template` | face or fingerprint templates or images | **block** |
| `leak-provenance` | leaked or hacked origin | exclude (§6) |

**Verdicts.**
- `pass`: no flags.
- `flag`: ingestible only behind a named screen or aggregation, which I7/I8 must design.
- `block`: never ingest raw; the candidate is recorded as metadata only.
- Publication is jurisdiction-conditional (SIG-PUB-017). Candidates from GI groups note the data-protection
  regime.

### 7.5 Lineage

**origin** is the controlling institution's own publication. Examples: an agency ArcGIS layer owned by the
agency's organisation; a statute on the legislature site; a report on the auditor's site.

**mirror-of** (`same_bytes` or `republished_document`) is an identical or republished copy:
- ArcGIS republishes by personal accounts or third parties (NEW-5);
- agenda attachments of a contract that also exists at the purchasing office;
- DocumentCloud uploads and MuckRock-hosted released files. For these, the publisher is the uploader and
  `lineage=mirror-of` the agency record, or `origin-unknown` in `notes`;
- journalism-hosted copies of agency documents. Calibration C07 found an executed Flock contract on a public
  radio station's CDN.

**derived-from** (`derived_summary`) is a compilation of facts:
- EFF Atlas rows, derived from their links;
- Eyes on Flock, derived from the Flock portals;
- NAMSDL and NCSL summaries, derived from statutes;
- Bard CSD, derived from FAA and media records;
- Pavilion and CivicIQ pages, derived from cooperative and agency records.

Revisions, amendments and responses use `new_version`, `amends` and `response_to` against their predecessor.
Only `independent_account` counts as independent corroboration. One institutional `lineage_group` is one
provenance (ADR-130).

**Personal-account and third-party GIS layers** default to `mirror-of` / `derived-from`, unknown origin, until
the item's `accessInformation`, credits or owner organisation shows an agency origin. Compare them with the
DeFlock/OSM origin and the existing `camreg_osm_surveillance` targets.

### 7.6 Registry and queue dedupe (mechanical)

Normalise the host (lowercase, drop `www.`) and the key identifier. Then check, in order, from the worktree
root:

```
grep -n -i "<host>"           connectors/src/connectors/data/sources.toml              # homepage_url -> same-as/related
grep -n -i "<host>\|<item_id>" connectors/src/connectors/data/camera_registry_targets.toml connectors/src/connectors/data/dot_511_targets.toml
grep -n -i "<host>"           connectors/src/connectors/data/{live_targets,agenda_tenants,procurement_portal_tenants}.toml
grep -n -i "<host>"           tasks/src/tasks/data/acquisition_queue.toml docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv
grep -n -i "<host>"           docs/build/planning/2026-09-30-next-phase/data/source_coverage.csv
```

- **`same-as:`** means the same source or target. A tenant of a registered platform is
  `related:<platform_id>`, noted `tenant already enumerated` when it appears in `agenda_tenants.toml`.
- **P31-owned sources** (`tasks/acquisition.py:118`: gao, dhs_oig, dhs_fusion, uk_scc, fema_hsgp,
  ccops_oakland/cambridge/somerville) are **never** new work. Record them `same-as` with the note
  `consume_existing`.
- **Within-row duplicates** are merged. **Cross-row duplicates** are left for I7.

### 7.7 Evidence standards

- **Cite what you fetched.** A claim in a research note cites its fetch id (`I<n>-F###`) or a `file:line`.
- **Quote load-bearing numbers verbatim,** with the fetch id. Label every computed number with its method.
- **Label search summaries as leads,** including the calibration signals in Appendix A, until the row fetches
  the origin.
- **Treat vendor statements as assertions.** They are genre D6 (ADR-122 / ADR-131). Cite them as "the vendor
  states", never as fact.
- **Keep the S5 semantic guards:**
  - cooperative availability is not a local purchase;
  - eligibility is not an award;
  - an award ceiling is not spending;
  - a template is not an executed instrument;
  - a subscription is not local hardware;
  - a historical survey is not current;
  - the absence of a waiver is not the absence of a programme.

---

## 8. Query-log format (`data/query_log_I<n>.csv`)

The header is exactly `query_id,engine_or_tool,query_or_url,run_at,hits_kept,notes`. This is the J2 precedent,
`data/query_log_J2.csv`.

| Column | Rule |
|---|---|
| `query_id` | `I<n>-Q###` (query), `I<n>-Q###.p<k>` (page), `I<n>-F###` (fetch) or `I<n>-L###` (local operation) |
| `engine_or_tool` | one of `WebSearch`, `WebFetch`, `arcgis-hub-search`, `socrata-discovery`, `ckan:<host>`, `opendatasoft:<host>`, `sec-edgar-fts`, `usaspending-api`, `ojp-award-search`, `legistar-api:<tenant>`, `chrome` (public pages only, no forms), `local:<file>` |
| `query_or_url` | the exact string or URL sent, with no secrets |
| `run_at` | ISO-8601 Z from `date -u` or a tool timestamp |
| `hits_kept` | the number of candidate rows created or updated by this line (0 allowed) |
| `notes` | must start with `cell=<cell_id>; new=<n>; dup=<n>;` then free text. Fetch lines: `cell=…; cand=<cand_id or none>; status=<http>; sha256=<first 12>;`. Local operations: `cell=…; file=<path>; sha256=<first 12>;`. Exclusions: `excluded:<reason>`. Enumerations: `item=<state/place>; outcome=found|negative|not-reached`. |

Example lines:

```
I3-Q001,arcgis-hub-search,https://hub.arcgis.com/api/search/v1/collections/dataset/items?q=flock&limit=100,2026-10-01T09:00:03Z,0,cell=I3-T01-C03-G0; new=0; dup=0; 1266 matched; paging
I3-Q001.p1,arcgis-hub-search,…&startindex=1,2026-10-01T09:00:04Z,14,cell=I3-T01-C03-G0; new=14; dup=3; agency-owned layers kept; 8 personal-account layers -> lineage check
I3-F007,WebFetch,https://services1.arcgis.com/…/Flock/FeatureServer?f=json,2026-10-01T09:02:10Z,1,cell=I3-T01-C03-G0; cand=I3-C007; status=200; sha256=…
I5-Q041,WebSearch,"Jersey City" council agenda platform,2026-10-01T10:14:55Z,1,cell=I5-T00-C07-GL1; new=1; dup=0; item=Jersey City; outcome=found
```

Saturation and cell status are computed mechanically from the `cell=` and `new=` values.

---

## 9. Outputs and self-check

**Per row:**
- `research/I<n>-<slug>.md` (I3 `alpr-ppn`, I4 `technology-classes`, I5 `geography`, I6 `evidence-channels`);
- `data/candidates_I<n>.csv` (§8.6 plus the §7.3 extensions);
- `data/query_log_I<n>.csv`;
- optionally `findings/incoming/I<n>.csv`.

**Research-note sections:**
1. Summary
2. Method, with deviations from this protocol
3. **Cell coverage table**: cell, queries, fetches, new, closing status
4. Candidates by class, channel and geography, with level counts
5. Movement against the I1 blind spots: which ranks, states and cities gained a candidate channel
6. Part VIII log: counts of flag and block by flag, and **no content**
7. Access failures (host, status, time)
8. Open questions for I7 and the operator
9. Appendix: reproduction

**Self-check before returning.** All must pass. Report any that fail.
- Every candidate has a fetch line.
- Every query line has `cell=` for one of the row's own cells.
- Every P1 and P2 cell has at least `q_min` queries, or an honest non-saturated status.
- `cand_id`s are unique.
- `registry_match` was computed with §7.6.
- No committed file contains a plate, operator id, officer name from audit data, search reason, student datum or
  private address.
- `rights_lane` never says `decided`.
- Every date came from `date -u`.

---

## 10. Row briefs

### I3 — ALPR and public-private camera networks

- **Scope.** Classes T01–T07 and T29 in the US.
  - G0 national sweeps, which may iterate states and places using the §4 weights.
  - GS state sweeps for ALPR statutes, reports and policies: `I3-T01-C04/C05/C11-GS` cover T01–T04.
  - It does not cover international ALPR (I5), cooperative contracts (I6) or CCOPS documents (I6).
- **Cells.** 40: 15 P1, 11 P2, 14 P3. Σ `q_min` = 96.
- **Budget.** 150 queries and 250 fetches.
- **P1 cells, in weight order:**

| Cell | Target |
|---|---|
| `T01-C03-G0` | ArcGIS Hub / Socrata / CKAN / Opendatasoft layers for Flock and LPR |
| `T06-C05-G0` | camera-registry programme pages |
| `T01-C05-GS` | SB 34 and other policy postings |
| `T01-C07-G0`, `T01-C09-G0` | Flock, Motorola and Axon customer evidence in agendas and contracts |
| `T05-C07-G0`, `T05-C09-G0` | RTCC agendas and contracts |
| `T06-C01-G0` | Fusus "Connect", Ring and CommandCentral registries |
| `T01-C04-GS`, `T01-C11-GS` | statute and reporting regimes |
| `T01-C01-G0`, `T03-C01-G0` | portal slugs and sharing |
| `T06-C07-G0` | camera-registry and integration approvals |
| `T01-C15-G0` | the ORIGIN of the national ALPR layer (NEW-5) |
| `T03-C13-G0` | released sharing and audit records (Part VIII-screened) |

- **Inputs.** The Eyes on Flock capture (1,528 portals; 45 states) and the Atlas I3 partition (4,677 links).
- **Expected yield (inference).**
  - 80–200 `target`-level candidates, dominated by agency Flock layers and registry pages.
  - 10–25 `channel` or `publisher` candidates: state audit libraries, SB 34 policy sets, registry platforms,
    and VA's State-Police report.
  - An answer on the origin channel for the OSM/DeFlock ALPR layer.
- **Watch-outs:**
  - The Flock origin is refused: no portal scraping, no archives, audit tables never read.
  - Socrata "license plate reader" results are mostly Oakland per-read datasets. Block them; schema only.
  - ArcGIS noise ("Crane roost flock", "Little Flock", address-point and sector layers) and personal accounts.
  - Dedupe against `camreg_*_flock` targets and `camreg_osm_surveillance`.
  - Executed versus template contracts.
  - Registrant locations are C3.
  - Journalism claims about National Lookup and ICE, or about new Flock fleets, must be fetched. One calibration
    result *title* mentioned Flock cameras on rideshare vehicles; it is unverified.
- **Outputs.** `research/I3-alpr-ppn.md`, `data/candidates_I3.csv`, `data/query_log_I3.csv`.

### I4 — Other technology classes

- **Scope.** Classes T09–T28 in the US, excluding every Flock product (T29, I3) and all ALPR (I3).
- **Cells.** 74: 5 P1, 28 P2, 41 P3. Σ `q_min` = 117.
- **Budget.** 170 queries and 250 fetches.
- **Order:**
  1. The zero-channel classes, SMM, FOR and SCH, plus the ATE ontology gap.
  2. UAS, GSD, FRT and CSS beyond the Atlas.
  3. DATA and INV.
  4. Probes for BIO, AERO, ROB, LI, EM, WPN, BWC, FUS and BORD.
- **P1 cells:**

| Cell | Target |
|---|---|
| `T25-C07-G0` | school-board approvals (BoardDocs, Simbli, Diligent) |
| `T19-C09-G0` | forensics purchasing |
| `T20-C09-G0` | SMM purchasing |
| `T25-C09-G0` | school purchasing |
| `T14-C16-G0` | FAA DFR / BVLOS waivers and COAs |

- **Strong P2 cells:**
  - state drone and FR reports: `T14-C04-GS`, `T11-C04-GS`;
  - ShotSpotter agendas and contracts: `T13-C07`, `T13-C09`;
  - ATE open data: `T09-C03`;
  - Upturn: `T19-C14`;
  - the US Courts wiretap tables: `T18-C04`;
  - BWC grants: `T23-C10`, carved out of I6.
- **Inputs.** The Atlas I4 partition (13,938 links).
- **Expected yield (inference).** 60–140 candidates. The most structured channels are expected to be the FAA
  waiver records, the US Courts wiretap tables, state drone and FR reports, NCES aggregates and the school-board
  platforms.
- **Watch-outs:**
  - Student data is `minor-data`: block it.
  - FAA waivers carry pilot personal fields (SRC-025 `screening_required`).
  - Broker and person-search outputs are blocked.
  - Spyware leak provenance is excluded.
  - ATE violation datasets contain plates.
  - FR search logs are blocked.
  - The ontology gaps (T09, T27) get the proposed concept tag.
  - Apply the boundary rules: T28 excludes ALPR; the Axon and Motorola splits apply.
- **Outputs.** `research/I4-technology-classes.md`, `data/candidates_I4.csv`, `data/query_log_I4.csv`.

### I5 — Geography gaps

- **Scope:**
  - US place-anchored **multi-class** discovery: GD, GL1–GL5 and GT;
  - DOT/511 (T08) everywhere;
  - all classes internationally (GI1–GI3, GIW).
- **Cells.** 53: 3 P1, 15 P2, 35 P3. Σ `q_min` = 76.
- **Budget.** 150 queries and 250 fetches.
- **P1 cells:**

| Cell | Target |
|---|---|
| `T08-C03-GD` | DOT/511 in the roughly 25 states without a layer, tier A first; plus the `dot_511_tx` rights question |
| `T00-C03-GL1` | thin-city open-data portals |
| `T00-C07-GL1` | thin-city agenda platforms |

- **Method.**
  - Enumerate in weight order, inventory-first. Use Socrata `domains=`, ArcGIS `bbox=`, and
    `agenda_tenants.toml` to skip the 793 known tenants.
  - Record the channel **identity** for every place, even when there is no hit. Together these build the
    municipality→platform directory (SIG-INGEST-026).
  - Record negatives as coverage facts.
- **Expected yield (inference).** 40–120 `channel` or `publisher` candidates, plus a per-place channel table
  covering at least the 36 GL1 cities and the 10 tier-A states.
- **Watch-outs:**
  - Always use `US-XX` versus `ISO:CC` (NEW-1).
  - When a layer is found, check that its points fall in the claimed place (NEW-2).
  - CT planning regions and MA counties (§4.4).
  - Tribal data sovereignty.
  - GDPR and jurisdiction-conditional publication.
  - UK ANPR gives counts only.
  - Vumacam-type private networks.
  - Search in local languages.
- **Outputs.** `research/I5-geography.md`, `data/candidates_I5.csv`, `data/query_log_I5.csv`.

### I6 — Cross-cutting evidence channels

- **Scope:**
  - T00 (multi-class) in every channel at G0 and GS;
  - the cross-cutting channels C08, C10, C11, C12, C13 and C14 for every class without a dedicated cell there.
    That includes **all** cooperative-contract searches, for every vendor including Flock and Axon;
  - C06 (CCOPS) everywhere.
- **Cells.** 23: 4 P1, 11 P2, 8 P3. Σ `q_min` = 46.
- **Budget.** 130 queries and 200 fetches.
- **P1 cells:**

| Cell | Target |
|---|---|
| `C06-G0` | build the CCOPS jurisdiction list from primary ordinance pages; the national list is an image (SIG-INGEST-049a) |
| `C06-GP` | per-jurisdiction annual and impact reports; registry `ccops_*` rows first |
| `C11-GS` | the non-ALPR state surveillance-law inventory, inventory-first |
| `C08-G0` | cooperatives and aggregators across all vendors |

- **Strong P2 cells:**
  - federal grants (`C10-G0`): OJP, COPS, FEMA, Treasury SLFRF;
  - state contracts and checkbooks (`C08-GS`);
  - state grants (`C10-GS`);
  - records corpora (`C13-G0`);
  - multi-class federal records (`C16-G0`): AI inventories, LEMAS, LESO;
  - platform directories for agendas and procurement (`C07-G0`, `C09-G0`).
- **Inputs.** The Atlas records-corpora partition (4,971 links).
- **Expected yield (inference).** 30–80 `channel` or `publisher` candidates. Each can span many agencies. The
  row also produces award and contract id lists for back-chaining.
- **Watch-outs:**
  - MuckRock blocked the hosted connector with a WAF 403 (I1). Record the access mode honestly.
  - DocumentCloud and MuckRock files are mirrors of agency records.
  - Check the aggregators' terms.
  - PAID sources are excluded.
  - Obtaining an ICPSR or LegiScan key is an operator action.
  - Grant eligibility is not an award, and a ceiling is not spending.
  - Court records carry party names.
  - I6 must not run ALPR-sharing records queries (`I3-T03-C13`), or CSS/FOR/SMM records queries (I4's dedicated
    C13 cells).
- **Outputs.** `research/I6-evidence-channels.md`, `data/candidates_I6.csv`, `data/query_log_I6.csv`.

---

## 11. Hand-off to I7 and I8

I7 merges `candidates_I3…I6`. The §7.3 extension columns map directly onto `acquisition-queue/1` passport
fields:

| Candidate field | Passport field |
|---|---|
| `publisher` | `authority` |
| `gap_ref` and its narrative | `gap` |
| `lineage_class` and the institution | `lineage_class`, `lineage_group` |
| `registry_match` | `links` (`same_source` / `related`) |
| publisher is a municipality or state | `municipal_publication = true` |
| `part_viii_flags` and `part_viii_verdict` | `preflight` |
| `connector_reuse` | the E dimension evidence |
| `access_check` | the A dimension evidence |

`acq-score/1` dimensions stay unscored until I7 assesses them. I3–I6 never score; the `acq-seed/1` precedent is
an estimate, and unknown means unscored. `rights_lane` values are guesses for the HG-03 packets (Q-19), and the
queue invariant still holds: no lane is `decided` without a recorded decision.

---

## 12. Notes for the planning orchestrator (single writer)

1. **§8.6 extension.** Consider recording the §7.3 columns in META_PLAN §8.6. They are additive and appended.
2. **Budgets.** I4 170 and I6 130 deviate from the "≤ 150 each" example; the rationale is in §5.6. The
   predefined P12 splits are in the `split_if_needed` column.
3. **Clock observation (P2).**
   - The META_PLAN change log stamps "I1 done" at `2026-09-30T18:41Z`, and other rows at 18:40–18:42Z.
   - The commit that recorded them, `4aff9a48`, has committer date `2026-09-30T13:20:51-04:00`, which is
     17:20:51Z.
   - `date -u` here read 17:23:48Z.
   - So those stamps are about 80 minutes in the future (live-read of `git log` and `date -u`). This is the F-21
     failure class.
4. **Seed currency.** NAMSDL's national ALPR-law summary is dated 2025-09 (search-summary; I3 will fetch it).
   The committed seed `state_alpr_statute_seed.toml` is frozen at 2022-02-03 and lacks Virginia. That is the
   case SIG-INGEST-049f anticipates ("SIG must maintain it onward").
5. **Q-20** (D1 Q-D1-13) is unanswered at authoring. I5 applies it when it arrives.

---

## Appendix A — Calibration log (15 web calls; ≤ 15 allowed)

`run_at` is the `date -u` reading taken immediately before each batch. The calls in a batch were issued in
parallel within the following minute.

**Evidence classes.**
- `WebSearch` rows are **search-summary (unfetched)**: leads only.
- `WebFetch` rows are **live-read** of the API JSON, via the tool's summariser. The counts quoted are the API's
  own `resultSetSize` / `numberMatched`.

| id | tool | query / URL | run_at | kept | notes |
|---|---|---|---|---|---|
| I2-C01 | WebSearch | `state license plate reader statute biennial audit report legislature Minnesota 13.824 audit results` | 2026-09-30T17:24:09Z | 1 | Channel C04. `lrl.mn.gov/docs/<yr>/mandated/<id>.pdf`: St. Louis Park (2025-07-10), South St. Paul (2025-08-11), St. Paul (2023-12-21) ALPR biennial audit results. Stable URL pattern. |
| I2-C02 | WebSearch | `Fusus "register your camera" city camera registry program police real time crime center` | 17:24:09Z | 1 | Channel C05/C01 for T06. Camera-registry pages: Campbell CA; Lexington KY (2023); Greenville County SC "Connect" (dated 2026-05-28 in the URL); Kalamazoo "Connect"; Columbus GA (2024); Tucker GA; OC Sheriff. Two modes, registry and integration (FususCORE). |
| I2-C03 | WebSearch | `ACLU Community Control Over Police Surveillance CCOPS list of cities that have passed surveillance ordinances` | 17:24:09Z | 0 | The summary cites "24 cities" (a 2024 article). No list returned, which confirms the list must be built from primary pages (SIG-INGEST-049a). |
| I2-C04 | WebSearch | `drone as first responder programs list police departments FAA BVLOS waiver DFR count 2025` | 17:24:09Z | 1 | The summary claims ">1,000 public safety agencies" with DFR waivers by Feb 2026, and 976 waivers through Apr 2025. **Unverified.** Channel C16 (FAA) flagged high-yield. |
| I2-C05 | WebSearch | `transparency.flocksafety.com agency transparency portal terms of use search audit` | 17:24:09Z | 1 | Search engines index `transparency.flocksafety.com/<slug>` pages, and agency `.gov` pages link their portals (Arlington WA, Walla Walla WA, Columbia County NY). Flock's blog says portals can include a public search audit (case number, search reason, offense type, anonymised user id): Part VIII. |
| I2-C06 | WebFetch | `https://api.us.socrata.com/api/catalog/v1?q=license%20plate%20reader&limit=25` | 17:24:39Z | 0 | resultSetSize **18**. 15 are `data.oaklandca.gov` "All license plate reader data (ALPR)" sets (2010–2014): **suspected plate-level from their titles; schema not inspected → block**. The rest are false positives: a Thruway toll gantry set, DMV registration transactions, a Seattle freeway file. |
| I2-C07 | WebFetch | `https://hub.arcgis.com/api/search/v1/collections/dataset/items?q=flock&limit=25` | 17:24:39Z | 0 | numberMatched **1,266**. The first 25 include agency or agency-staff Flock layers (Jeffersonville, Pueblo, Johns Creek, Temecula, Shelbyville TN "Flock Cameras – Public", Lewisville TX "Active Flock Cameras", Savannah PD, Peachtree Corners, Marble Falls, Monterey Park and Brazoria staff accounts). The noise includes "Crane roost flock", "Little Flock", Pearland address-point and subdivision layers, sector and city-limit layers, and personal accounts. |
| I2-C08 | WebSearch | `Sourcewell cooperative contract Flock Safety license plate recognition contract number awarded` | 17:24:39Z | 1 | No Sourcewell Flock contract surfaced. Sourcewell `030425-SND` (SoundThinking; the summary says it includes AI LPR). S.A.V.E. (City of Tempe) `T21-119-01`, Flock Group Inc, via the Pavilion aggregator. An executed Flock contract hosted on `npr.brightspotcdn.com` (a journalism-hosted mirror). Riverside County BoS proceedings. |
| I2-C09 | WebSearch | `2025 state law automated license plate reader annual report requirement publish statistics state police Virginia Illinois Washington Colorado` | 17:24:39Z | 1 | Virginia State Police "ALPR Reporting Requirements v2" (2026-03) under Code §2.2-5517(J); VSCC ALPR reports (2025 annual; Jan 2026). **NAMSDL "Automatic License Plate Recognition Systems Summary of State Laws" (2025-09)**. Cardinal News on VA auto-theft-prevention grants going to LPRs (a state grant channel). |
| I2-C10 | WebSearch | `UK National ANPR Service camera locations freedom of information police ANPR camera numbers per force` | 17:24:39Z | 0 | The summary says police do not reveal ANPR locations by national policy, and that per-force counts come from FOI and journalism (samathieson.com; a Cleveland PCC FOI PDF). GI1 UK ANPR gives counts only. |
| I2-C11 | WebSearch | `surveillance.watch map of surveillance companies investors data download` | 17:24:39Z | 1 | Surveillance Watch (surveillancewatch.io; DAIR / Mozilla-fellow project) maps vendor, investor and country links. The Register (2025-11-08) says it grew from 220 to 695 entities. No download confirmed; I6 checks the terms. |
| I2-C12 | WebSearch | `school board approves Gaggle GoGuardian contract student monitoring agenda item renewal district` | 17:25:23Z | 1 | School-board approvals: Lawrence KS Gaggle renewal (2024-07); New Haven GoGuardian ($210k); Elmwood Park IL GoGuardian via MNJ; St. Mary's MD Gaggle. These come through board agendas and local press. The `civiciq.com` public-contract aggregator is a lead. |
| I2-C13 | WebSearch | `Vumacam private camera network licence plate recognition Johannesburg police access public-private` | 17:25:23Z | 1 | The summary: over 2,000 Vumacam LPR cameras; JMPD access to about 8,000 cameras since 2023-07; journalism in Daily Maverick and TechCentral. GI3 public-private analogue. |
| I2-C14 | WebSearch | `Bard College Center for the Study of the Drone public safety drones dataset agencies download` | 17:25:23Z | 1 | Bard CSD "Public Safety Drones" 3rd edition (2020-03): 1,578 agencies per the summary; PDF plus a Google Map; sources are FAA waivers, media and local records → `derived-from`. |
| I2-C15 | WebSearch | `"Automated License Plate Readers" policy "Civil Code 1798.90.51" usage and privacy policy police department website pdf` | 17:25:23Z | 1 | SB 34 policy postings: SJPD, San Bruno, Livermore, Montclair, Barstow, BART annex, UCSD PPM 460-7, UCI. The URL patterns `/DocumentCenter/View/<n>` (CivicPlus) and `showpublisheddocument` (Granicus) are query hooks. |

## Appendix B — Local calibration (no network)

Evidence class: `live-read` bytes captured by I1; the computation is inference.

- **`atlas.csv`** (sha256 `dcbf8bc13d14…`, 15,135 rows).
  - Columns: `Link 1…3`, `Link n Source`, `Link n Type`, `Link n Date` and `Other Links`. The `Link n Type`
    fields are empty in this capture.
  - Technology counts: BWC 5,470; ALPR 4,094; Drones 1,828; Third-party Investigative Platforms 1,062;
    Face Recognition 980 (+6 "FRT"); Camera Registry 756; GSD 248; RTCC 242; Predictive Policing 200; Video
    Analytics 85; CSS 83; Fusion Center 81.
  - 26,294 links; 4,134 distinct domains; 872 government-like domains carrying 5,840 links.
  - Top domains: documentcloud.org 3,809; muckrock.com 1,162; web.archive.org 838; facebook.com 825;
    dronecenter.bard.edu 807; srtbwc.com 638; transparency.flocksafety.com 491 (507 including archive-wrapped);
    nj.gov 468; mass.gov 407; michigan.gov 405; njoag.gov 357; governor.ohio.gov 342; ptb.illinois.gov 261;
    doj.state.wi.us 258; dps.mn.gov 258; perpetuallineup.org 249; lrl.mn.gov 225.
  - The partition in §5.7: I6 4,971 · I5 2,708 · I3 4,677 · I4 13,938.
- **`eyesonflock.json`** (sha256 `eccb336ab89a…`): the I1 figures (1,528 portals) are reused, not re-derived.
- **`sub-est2024.csv`** (sha256 `af9cd4835c93…`): 3,144 SUMLEV-050 rows; the top-100 county ordering in §4.4.
- **Registry reads:**
  - `CONNECTOR_FOR_SOURCE`: 238 sources in 19 families (dot_511 183; procurement 17; accountability 7;
    government_mandated_disclosure 6; …).
  - `agenda_tenants.toml`: platform counts granicus 434, civicplus 355, legistar 318, civicclerk 303,
    novusagenda 156, primegov 140, escribe 74, boarddocs 11.
  - `procurement_portal_tenants.toml`: 17 tenants.
  - `camera_registry_targets.toml`: 223 targets.
  - `state_alpr_statute_seed.toml`: 16 states, `as_of = 2022-02-03`.

## Appendix C — Reproduction

- **Weights:** the formulas in §4.2, §4.3 and §5.3. The inputs are I1's state and city tables (research note §3
  and §4), parsed column-wise.
- **Matrix:** every cell's E, B and Y are in the CSV, so `weight` and `priority` can be recomputed.
- **Partition:** re-check it with the §5.2 function and the `covers` column.
- The scratch generator lived in the session scratchpad. It is not committed, because R8 limits I2 to two
  outputs; the CSV is the authority.
