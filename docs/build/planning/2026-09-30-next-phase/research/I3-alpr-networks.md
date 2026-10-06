# I3 — ALPR and public-private camera networks (deep source research)

Row **I3** of `META_PLAN.md` §6 (Stream I, Stage P). Owner class **R** (web research). Run 2026-09-30T17:58Z →
18:41Z (`date -u`) by Claude Code (Opus 5.5) in the planning worktree, branch `claude/next-phase-planning`.
Protocol: `design/I2-source-search-protocol.md` (read in full). Nothing committed.

**Outputs:**
- this note;
- `data/candidates_I3.csv`: 90 rows, §8.6 plus the I2 §7.3 extension columns;
- `data/query_log_I3.csv`: 217 lines, I2 §8 format;
- `findings/incoming/I3.csv`: NEW-1…NEW-4.

Bulky captures sit under `docs/build/logs/next-phase/I3/` (gitignored). Each capture is keyed by the sha256 given in the
query log.

**Evidence classes.**
- Every factual sentence below cites a query or fetch id (`I3-Q###`, `I3-F###`) or a local operation (`I3-L###`)
  from `data/query_log_I3.csv`, or a repo `file:line`.
- Computed numbers are labelled.
- Search-engine snippets were used as leads only. Nothing is cited that was not fetched.

---

## 1. Summary

**Budget used.**

| Item | Used | Budget |
|---|---|---|
| Queries | 93 | 150 |
| Fetches | 107 | 250 |
| Pages | 10 | — |
| Local operations | 7 | — |

The row stopped early for a reason outside its control. The planning session's shared **WebSearch budget ran out
(200/200) at 18:15:10Z**, after this row had issued only 5 web searches (`I3-Q018`). Every cell whose only discovery
channel is a search engine is therefore unsaturated or not started (§3). The rest of the row used documented public
APIs and the local Atlas and Eyes on Flock captures:

- ArcGIS Hub search;
- Socrata discovery and SODA;
- the Legistar Web API;
- OSM taginfo;
- the GitHub API;
- the Federal Register API;
- CourtListener.

**Candidates.** There are **90**:
- **53 `new`**, 35 `related:` and 2 `same-as:` against the registry, the 27-row acquisition queue and the six-streams
  candidates;
- by level: 54 `target`, 16 `channel`, 13 `publisher` and 7 `family`;
- by Part VIII verdict: 42 `pass`, 39 `flag` and 9 `block`.

**The most important results.**

1. **Minnesota already publishes a statutory state-wide ALPR list.** Minn. Stat. 13.824 subd. 8 requires the BCA to
   publish "a list of law enforcement agencies using automated license plate readers … including locations of any
   fixed stationary automated license plate readers" (`I3-F066`). The BCA page has 116 agency panels; 88 of them
   list stationary sites, about 726 list items (`I3-F067`; count by the local parse `I3-L003`). The biennial
   independent audits are deposited at the Legislative Reference Library and name the vendor and the device counts
   (`I3-F068`). SIG has no origin row for either (I3-C039, I3-C040).
2. **Virginia created a full reporting regime in 2025.** Va. Code 2.2-5517 requires three things (`I3-F070`):
   - each agency reports to VSP by April 1, *and publicly posts its policy and report* (subsections I and K);
   - VSP aggregates the reports by July 1 (J);
   - data may not be shared with other-state, federal or private databases (F).

   The Crime Commission's January 2026 survey: 159 responding agencies use ALPR. By vendor: Flock Safety 137,
   Leonardo 12, Motorola 12, Thomson Reuters/CLEAR LPR 6 (`I3-F071`). VA is **absent** from SIG's frozen 2022
   statute seed (I3-C041…C044).
3. **Florida DOT independently inventories Flock cameras on state right-of-way.** The layers are:
   - "D3 Flock Camera Data": 407 points, with permit-compliance fields;
   - "FLOCK removal status layer": 523 points, with County, StateRoad and Status;
   - a District 4 ROW camera survey whose types include LPR (`I3-F017`, `I3-F040`, `I3-F041`, `I3-F052`,
     `I3-F053`).

   A state agency auditing another vendor's network is the strongest independent Flock origin found (I3-C002…C004).
4. **Registered platforms already carry ALPR customer evidence.** A MatterTitle keyword filter on the Legistar Web
   API found Flock, Motorola/Vigilant or LPR decisions in 10 of 13 registered tenants. Among them (`I3-Q019…Q033`):
   - Cleveland: Flock contracts, 2025–26;
   - Dallas: Flock contract and programme updates;
   - Columbus: Flock contract and audit hearings;
   - St Paul: a resolution to end Flock contracts;
   - Brazoria County: Texas DPS and Houston HIDTA LPR MOUs;
   - Louisville: council-funded LPR leases.

   Columbus also has four Vigilant **commercial** plate-data subscription ordinances (T04; `I3-Q092`).
5. **The origin of the national ALPR layer is OSM, which SIG already has but uses only for Oklahoma City** (NEW-5
   answered; finding NEW-4). OSM has 154,814 `surveillance:type=ALPR` objects; `manufacturer=Flock Safety` accounts
   for 113,726 (`I3-Q059`, `I3-Q060`). The ingested ArcGIS republish has 132,689 rows (registry note). 17 of 18
   ALPR map repositories on GitHub are OSM/DeFlock viewers (`I3-Q063`), so no independent crowd origin exists.
6. **The Flock sharing graph is already in the ingested mirror.**
   - 917 of 1,528 Eyes on Flock portals list shared-with organisations: 474,184 edges to 6,849 distinct targets
     (`I3-L005`). The gap is resolution (I8), not acquisition.
   - A records-derived, CC0-normalised set of Flock network-sharing reports exists independently of the portals
     (KSUALPRS, I3-C063, `I3-F080`).
7. **Part VIII hazards are sitting on public ArcGIS** (finding NEW-1, S1):
   - Flock "search results" layers with Plate, Capture_Time and location, in the City of Oakland GIS org and a Lakeway TX
     account (`I3-F020`, `I3-F021`);
   - a Mark43-hosted "LPR Hits" layer (`I3-F034`);
   - a Flower Mound TX camera registry exposing registrants' names, addresses, phones and e-mails (`I3-F102`).

   All were schema-read only. The rows were never read.

---

## 2. Method, and deviations from I2

**Order.** Inventory-first where an inventory existed:
- ArcGIS Hub for layers;
- LAPPA/NAMSDL 2025 for statutes;
- `agenda_tenants.toml` for Legistar clients;
- the Socrata catalog for contract registers;
- the Atlas and Eyes on Flock captures for snowballing.

Each candidate was fetched at origin: layer or metadata JSON, statute page, report PDF, or README. Per R6, schemas
were read and rows never were.

**Dedupe (§7.6)** was done mechanically against:
- `sources.toml` (342 source tables);
- `camera_registry_targets.toml` item ids and service URLs;
- `agenda_tenants.toml`;
- `acquisition_queue.toml`;
- the six-streams `source-candidates.csv`;
- `source_coverage.csv`.

**Deviations** (each is recorded in the query log):

1. **Output filename.** The dispatch prompt named `research/I3-alpr-networks.md`; I2 §9 names `I3-alpr-ppn.md`. The
   dispatch wins.
2. **Search budget.** WebSearch was exhausted at 18:15:10Z after 5 searches by this row (shared session cap). Cells
   whose seed templates depend on a search engine (`site:`/`filetype:` queries for SB 34 policies, camera-registry
   pages, vendor newsrooms, procurement PDFs) could not run (§3).
3. **Fetch mechanics.** Fetches were plain `curl` GETs, so the raw bytes could be sha256-hashed. The `engine_or_tool`
   column says `WebFetch` for these GETs and names the API for API queries:
   - `arcgis-hub-search`, `socrata-discovery`, `socrata:<host>`, `legistar-api:<client>`, `ckan:<host>`.

   The default curl user-agent was used and never changed (R4).
4. **API query lines.** For API discovery (hub, Socrata, Legistar, FR, GitHub, taginfo) the query line *is* the
   metadata fetch. Candidates found only that way cite the query id as their fetch line.
5. **One R4 lapse.** Two DocumentCloud requests went out in the same batch, about 2 s apart, before the first 403
   was seen (`I3-Q055`, `I3-Q056`). No further request was sent to that host.
6. **Query-design error.** Four Legistar camera-registry queries used `substringof('Ring')`, which matched "hearing"
   and "engineering" (`I3-Q042…Q045`). They were re-issued with specific terms and are counted as inconclusive.
7. **Two wrong Legistar client ids.** The ids `albuquerque` and `cleveland` returned HTTP 500 (`I3-Q020`,
   `I3-Q021`). The registry ids are `cabq` and `cityofcleveland`.
8. **Q-20.** D1 Q-D1-13 was unanswered, so the I2 §4 geography weights ordered the work.

---

## 3. Cell coverage and saturation (all 40 I3 cells)

**Columns.**
- Q = issued queries, F = fetches, L = local operations. All three are mechanical from `query_log_I3.csv`.
- "New" = the new-candidate sequence from the `new=` values.
- The status vocabulary is I2 §5.4.

### P1 cells

| Cell | Q | F | L | New seq. | Cands | Closing status |
|---|---|---|---|---|---|---|
| T01-C03-G0 | 12 | 62 | 1 | 22,3,0,13,0,0,1,0,0,0,0,0 | 37 | **saturated** (last 3 zero) |
| T06-C05-G0 | 0 | 2 | 0 | — | 1 | **blocked(access: WebSearch budget)**. Atlas-snowball fetches only. Chicago OEMC found; Fremont 403. |
| T01-C05-GS | 0 | 1 | 1 | — | 1 | **enumerated(1 found [VA duty] / 0 negative / 49 not-reached)**. Blocked by the WebSearch budget; CA Chula Vista 403. |
| T01-C07-G0 | 15 | 0 | 0 | 1,0,0,1,1,1,1,1,1,0,1,0,1,0,1 | 11 | **capped-unsaturated** (q_max 15; 10 of 13 tenants yield) |
| T01-C09-G0 | 7 | 0 | 0 | 1,0,1,1,0,0,0 | 3 | **saturated** within Socrata registers. PDF/contract web search not run. |
| T05-C07-G0 | 8 | 0 | 0 | 0,1,1,0,0,0,0,0 | 2 | **saturated** |
| T05-C09-G0 | 4 | 0 | 0 | 0,0,0,0 | 0 | **saturated** (3 Socrata registers only) |
| T06-C01-G0 | 1 | 5 | 1 | 0 | 4 | **blocked(access: WebSearch budget)**. Snowball found CityProtect, CrimeWatch, Flock community pages and ACC terms. |
| T01-C04-GS | 5 | 15 | 2 | 1,2,0,4,0 | 8 | **enumerated(6 found [MN, VA, NJ-dead, NH, MD, CA] / 1 negative [NC] / 44 not-reached [VT page empty, NE DNS failure, others])** |
| T01-C11-GS | 1 | 3 | 0 | 1 | 2 | **enumerated** via one national inventory (LAPPA 2025, 50 states + DC + territories). Per-state verification: VA found (missing from the seed); the others are not-reached. |
| T01-C01-G0 | 0 | 0 | 1 | — | 0 | **blocked(origin refused)**. Locally saturated: 486 of 487 Atlas-cited portal slugs are already in Eyes on Flock (`I3-L006`). |
| T03-C01-G0 | 0 | 0 | 1 | — | 0 | **n/a(acquisition)**. The ingested mirror already holds 474,184 sharing edges (`I3-L005`); the gap is resolution. |
| T06-C07-G0 | 9 | 0 | 0 | 0,0,0,0,1,0,0,0,0 | 1 | **saturated** (the first 4 are inconclusive: query-design error) |
| T01-C15-G0 | 4 | 5 | 0 | 0,0,3,1 | 5 | **capped-unsaturated** (stopped for budget allocation; results are mirror-heavy) |
| T03-C13-G0 | 3 | 0 | 0 | 0,0,0 | 0 | **blocked(access)**: DocumentCloud Cloudflare 403; MuckRock 403 |

### P2 cells

| Cell | Q | F | L | New seq. | Cands | Closing status |
|---|---|---|---|---|---|---|
| T01-C14-G0 | 2 | 4 | 0 | 3,1 | 4 | **capped-unsaturated** |
| T29-C07-G0 | 2 | 0 | 0 | 0,0 | 0 | **saturated**, with a caveat: "Raven" matches street and person names |
| T29-C09-G0 | 2 | 0 | 0 | 0,0 | 0 | **saturated** (registers only) |
| T04-C02-G0 | 0 | 0 | 0 | — | 0 | **blocked(access)**: EDGAR 403 (`I3-Q066`); WebSearch exhausted |
| T04-C09-G0 | 2 | 0 | 0 | 0,0 | 0 | **saturated** |
| T02-C07-G0 | 2 | 0 | 0 | 0,0 | 0 | **saturated**. Dallas Axon items are in-car video and BWC (I4-T23). |
| T02-C09-G0 | 2 | 0 | 0 | 0,0 | 0 | **saturated** (Axon rows are Taser/BWC/DEMS) |
| T05-C02-G0 | 0 | 1 | 0 | — | 0 | **blocked(access)**: EDGAR 403; the vendor posts cited by the Atlas have rotted (NEW-2) |
| T07-C03-G0 | 2 | 7 | 0 | 7,1 | 8 | **capped-unsaturated** (high yield) |
| T03-C16-G0 | 2 | 2 | 0 | 1,0 | 1 | **capped-unsaturated** |
| T01-C02-G0 | 1 | 0 | 0 | 0 | 0 | **blocked(access)**: EDGAR 403 |

### P3 cells

| Cell | Q | F | L | New seq. | Cands | Closing status |
|---|---|---|---|---|---|---|
| T29-C02-G0 | 0 | 0 | 0 | — | 0 | **not-started(tool budget)**. Flock is private, so it has no SEC filings. |
| T01-C12-G0 | 1 | 0 | 0 | 1 | 1 | **capped-unsaturated**: the probe yielded and was not continued |
| TRES-C01-G0 | 0 | 0 | 0 | — | 0 | **not-started(WebSearch budget)** |
| TRES-C02-G0 | 0 | 0 | 0 | — | 0 | **blocked(access)**: EDGAR |
| TRES-C03-G0 | 1 | 0 | 0 | 0 | 0 | **closed**. The probe returned 0 because Hub full-text does not support boolean OR. The registry programmes were captured via `I3-Q086` (I3-C086). |
| TRES-C04-G0 | 0 | 0 | 0 | — | 0 | **not-started(WebSearch budget)** |
| TRES-C04-GS | 0 | 0 | 0 | — | 0 | **not-started(WebSearch budget)** |
| TRES-C05-G0 | 0 | 0 | 0 | — | 0 | **not-started(WebSearch budget)** |
| TRES-C05-GS | 0 | 0 | 0 | — | 0 | **not-started(WebSearch budget)** |
| TRES-C07-G0 | 1 | 0 | 0 | 1 | 1 | **capped-unsaturated**: the probe yielded (Columbus Vigilant commercial data) and was not continued |
| TRES-C09-G0 | 1 | 0 | 0 | 0 | 0 | **closed** (probe, 0) |
| TRES-C15-G0 | 1 | 0 | 0 | 0 | 0 | **closed**: same-as OSM (3,744 gunshot_detector nodes) |
| TRES-C16-G0 | 1 | 0 | 0 | 0 | 0 | **closed** (probe, 0) |
| T07-C09-G0 | 1 | 0 | 0 | 0 | 0 | **saturated** |

**Not saturated, blocked or not started.** 23 cells:
- P1 (8): T06-C05, T01-C05-GS, T01-C07, T06-C01, T01-C15, T03-C13, T01-C01 (origin refused), T01-C11-GS
  (per-state verification);
- P2 (6): T01-C14, T07-C03, T03-C16, T04-C02, T05-C02, T01-C02;
- P3 (9): T29-C02, T01-C12, TRES-C01, TRES-C02, TRES-C04-G0, TRES-C04-GS, TRES-C05-G0, TRES-C05-GS, TRES-C07.

T03-C01 is n/a: the mirror already holds the data.

**Recommendation.** Continue in an **I3a/I3b split (I2 §10)** once WebSearch is available again:
- **I3a** (T01–T04): C05-GS SB 34/VA postings; C04-GS for the 44 not-reached states; C02; C13 via an alternative
  records host.
- **I3b** (T05–T07, T29, residuals): C05/C01 registry pages; RTCC contracts outside Socrata; the TRES cells.

---

## 4. Candidates by class, channel and geography

**Levels:** 54 target, 16 channel, 13 publisher, 7 family.

**Classes.** A candidate can carry several classes.

| Class | Candidates |
|---|---|
| T01 | 70 |
| T03 | 18 |
| T04 | 14 |
| T02 | 13 |
| T05 | 13 |
| T06 | 11 |
| T07 | 11 |
| T29 | 1 |
| T00 | 1 |

**Publisher types:**

| Publisher type | Candidates |
|---|---|
| gov-open-data | 42 |
| agenda | 15 |
| statutory-report | 9 |
| ngo | 5 |
| vendor-portal | 4 |
| crowdsourced | 3 |
| procurement | 3 |
| legislation | 2 |
| records-release | 2 |
| other | 2 |
| journalism | 1 |
| academic | 1 |
| court | 1 |

**Families.**

| Family | Size | Contents | Verdict |
|---|---|---|---|
| FAM-AGOL-ALPR | 26 targets + 1 family row | Agency or agency-staff Flock/LPR location layers. They include Flock export fields (Org_Name, Org_Type, Network_Name, Serialnumber) and a recognisable Flock site-survey template (Product, Pole, Permit_*, Flock_Sign) in Thomasville, Gastonia and Rocky Mount. Only 5 hub Flock layers were already registered. | mixed |
| FAM-LEGISTAR-ALPR | 14 | Council matters on registered tenants | mixed |
| FAM-SOCRATA-PROC | 3 | Cook County Sheriff Flock awards, USD 900,000 via reseller Insight Public Sector (2026) and USD 74,750 (2022); Mesa Flock payments, USD 711,746.03 summed from 10 expenditure rows (`I3-Q069`, `I3-Q070`) | mixed |
| FAM-AGOL-CCTV | 6 | Police CCTV layers and the DC camera-rebate aggregates | mixed |
| FAM-AGOL-PREG | 1 (about 25 programmes) | Police private-camera registration programmes on Survey123 | block (rows) |
| FAM-HAZARD | 6 | Metadata-only blocks | block |

**Vendors.**

| Vendor | Evidence found |
|---|---|
| Flock Safety | 26 layers, including FDOT's; 6 Legistar tenants; 2 Socrata registers; MN audits; VA survey; KSUALPRS; FlockRadar |
| Flock product lines | Condor PTZ (Gastonia, I3-C011); FlockOS integration feeds (I3-C028); a Flock community camera-registry product (I3-C090). **No Raven, Aerodome or Nova evidence** found in agendas or registers. |
| Motorola Solutions / Vigilant | Leon County SO "VIGILANT Fixed LPRs" (I3-C013); an EBRSO Vigilant layer (I3-C008); Detroit 2016 LPR contract; Columbus commercial plate data (T04); VA survey (12); CityProtect registry pages |
| Axon | Community Connect listing and Terms of Use; no Fleet 3 ALPR evidence (Dallas, Cook and Mesa Axon rows are BWC/Taser/DEMS) |
| Leonardo / ELSAG | VA survey only (12 agencies) |
| Thomson Reuters CLEAR LPR | VA survey (6 agencies; T04) |
| Genetec, Rekor, Neology | **none** (0 hub hits, `I3-Q012`) |
| Others | Insight Public Sector (reseller: Cook, Columbus); STS 360 (Dallas); NuPark mobile parking LPR (Madison); ForceMetrics (Columbus Flock add-on) |

---

## 5. Movement against the I1 blind spots

**I1 #1: Flock at origin and at scale.** This is the largest movement. New independent origins:
- a state DOT inventory (FL, 523 plus 407 points);
- a statutory state list (MN, 116 agencies, about 726 fixed sites);
- a state survey with vendor counts (VA: 137 Flock agencies);
- MN per-agency audits naming the vendor;
- 26 agency layers;
- Legistar ALPR matters in 10 tenants (Flock named in 4: Cleveland, Dallas, Columbus, St Paul);
- 2 contract registers.

The refused portal origin stays closed. The Atlas adds 1 slug beyond Eyes on Flock (`I3-L006`).

**I1 #2: Axon/Fusus, private-camera registries and RTCC.**
- Channels identified:
  - Motorola CityProtect registry pages (111 agencies cited by the Atlas);
  - CrimeWatch registry forms (ToS forbids automated access);
  - Flock's own community registry pages;
  - about 25 police registration programmes visible as Survey123 items;
  - DC's camera-rebate aggregates by PSA (T06 public subsidy);
  - Chicago OEMC's Private Sector Camera Initiative;
  - Detroit Green Light and RTCC contracts;
  - Leon County SO's Overwatch viewer.
- Axon's Terms of Use prohibit robots, spiders and page-scraping (`I3-F078`). That bears directly on HG-03 for the
  gated `axon_community_connect` row.

**I1 #4: Statutory reporting.**
- NCSL-seed replacement: the LAPPA 2025 inventory (I3-C038).
- New origin publications: MN BCA list and LRL audits; VA VSCC, VSP and agency postings.
- Duty leads: NH, MD, CA-CHP.
- NJ: the audit is now 404.
- NC: the only duty is internal reporting, so negative.

**I1 #6: Procurement.**
- The Legistar keyword pass (on an already-registered platform);
- Socrata contract registers (Cook County, Mesa);
- contract ids recorded for I6 back-chaining: Detroit 3004870 and 6000336; Detroit RTCC 6000294 and 2888789; Dallas
  Axon via Sourcewell 010720-AXN and 101223-AXN.

**I1 #10: Mobile ALPR and sharing currency.**
- KSUALPRS sharing reports (records-derived, CC0 normalisation);
- Brazoria County's Texas DPS and Houston HIDTA LPR MOUs;
- DHS SORNs referencing LPR data (ICE-009, ICE-008, CBP-007, CBP-006);
- the CHP duty to report LPR disclosure recipients;
- Columbus commercial Vigilant data (T04);
- Madison's NuPark mobile parking LPR.

**I1 #12: Records and courts.**
- CourtListener: 12 opinions citing Flock (metadata level);
- the Broward County records archive (CC0 mirror);
- two blocked corpora: FlockWatch (99.4 M search rows) and the MI portal archive.

**States gaining a candidate channel:**
- **tier A:** MI (Detroit ×3; MI archive is block-only), NH (duty lead). MS, VT, DE, RI, WV, ME, WY and AR stay unreached. AR's statistics duty appears only in the LAPPA note.
- **tier B:** DC (MPD cameras, rebate aggregates), NM (Albuquerque), ND (registration programmes).
- **tier C:** FL, GA, NC, VA, MN, CO, LA, TN, IN, TX, CT, NY, IL, AL, OH, MO, MD, KY, AZ, WA, CA.

**GL1 thin cities gaining a channel:**
- Cleveland, Detroit, St. Paul, Madison, Albuquerque and Nashville, all via Legistar;
- Norfolk, Chesapeake and Virginia Beach: journalism lead only (I3-C033);
- the Tampa / Hillsborough RTCC was seen only in an Atlas vendor post that has since rotted.

---

## 6. Candidate shortlist: value × feasibility × rights

This is a qualitative rank (inference). It is **not** `acq-score/1`, which I3 must not compute (I2 §11).

**Axes.**
- V = blind-spot value;
- F = access plus connector reuse;
- R = rights posture guessed from the captured terms (**never a decision**; HG-03 decides).

| # | Candidate | V | F | R | Why |
|---|---|---|---|---|---|
| 1 | I3-C039 MN BCA statutory ALPR list | H | H | M–H | Closes I1#4 and I1#1 for MN. A statutory public list of agencies plus fixed sites. One HTML page (JSON embedded). Locations are text and need geocoding. |
| 2 | I3-C002/C003 (+C004) FDOT Flock inventory and removal status | H | H | M | A state agency's independent count of Flock cameras (407 + 523 points in 2 layers; overlap not checked). `arcgis_query` reuse. Permit-compliance status is an accountability signal. |
| 3 | I3-C041–C044 Virginia 2.2-5517 regime | H | M | H | Statute, VSP spec, VSCC vendor aggregates and a posting duty. Covers about 159 agencies. VA is missing from the seed. The VSP aggregate report and agency postings still need locating. |
| 4 | I3-C048 Legistar ALPR keyword pass over the 294 verified tenants | H | H | M | The platform is registered and the connector exists. 10 of 13 tenants yield contract, ordinance or audit evidence. |
| 5 | I3-C069 OSM origin (widen `osm_overpass` to US ALPR) | H | H | H | 154,814 objects at origin against 132,689 in the stale republish. Vendor tags answer NEW-7. ODbL compartment. |
| 6 | I3-C040 MN LRL biennial audits | H | M | H | Per-agency vendor, device counts and compliance. Results are public by statute. Needs the LRL index. |
| 7 | I3-C063 KSUALPRS normalised Flock sharing reports | H | H | M | T03 currency, independent of the portal mirror. CC0 normalisation; the source records' rights are unknown. |
| 8 | I3-C001 family: 26 agency Flock/LPR layers | M–H | H | M | Direct origin for 26 agencies. The Org_Type fields evidence T04 private operators (C3 screen needed). |
| 9 | I3-C076–C078 Socrata procurement registers | M | H | M | Spend and award evidence for Cook County and Mesa. A vendor `$q` filter generalises to other registers. |
| 10 | I3-C087 Columbus Vigilant commercial plate-data subscriptions | M–H | H | M | First evidence of **T04** (commercial plate data) in SIG. Legistar reuse. |

**Next tier.**
- I3-C084: DC camera-rebate aggregates. Pass, and it is an aggregate lane.
- I3-C058: Brazoria DPS/HIDTA MOUs.
- I3-C074: MD MCAC annual unit counts since 2016, still to locate.
- I3-C072: DHS SORNs.
- I3-C013: Leon County SO Vigilant layer.
- I3-C043: VA Thomson Reuters CLEAR.
- I3-C088: CourtListener.
- I3-C046, I3-C090: CityProtect and Flock community registries, pending terms.

---

## 7. Notable negative results (coverage facts)

**Open-data catalogues.**
- **Socrata has no Flock data.** `q=flock` returns 2 irrelevant items (`I3-Q006`). `q=ALPR` returns only Oakland
  per-read sets from 2010–2014, which are blocked (`I3-Q007`).
- **The ArcGIS "1,266 flock items" figure is fuzzy full-text.** Only 82 of 902 unique returned items contain "flock"
  (`I3-L001`). I2's calibration count overstates the channel.
- **No Genetec, Rekor or ELSAG layers exist on Hub** (`I3-Q012`, numberMatched 0).
- **catalog.data.gov CKAN** `package_search` returns 404 on both paths tried (`I3-Q009`).

**Agendas.**
- **Legistar negatives** (no ALPR matters in titles): Atlanta (tenant holds only 2021–22), Kansas City, Richmond VA,
  San Antonio, Milwaukee and Phoenix. There were no Raven, Aerodome or DFR titles in Dallas or Columbus.

**Contract registers.**
- **Negatives:** Chicago (Flock = "Christian Fellowship Flock"), Austin ("flocked" gloves); Fusus, DRN and Vigilant
  appear in none of the 3 registers.

**Statutes and federal records.**
- **North Carolina** 20-183.31 requires audit and reporting only to the agency head, not a public report (`I3-F094`).
- **Federal Register**: 0 documents mention "real time crime center" (`I3-Q091`).

**Vendors and origins.**
- **Axon Fleet 3 ALPR**: no evidence in any channel tried.
- **Flock transparency portals**: not fetched (refused origin; operator instruction). The Atlas cannot extend Eyes on
  Flock (486 of 487 slugs overlap, `I3-L006`).

---

## 8. Part VIII log (counts only; no content)

**Verdicts.** 42 pass, 39 flag, 9 block. The blocks are:

| Candidate | What it is |
|---|---|
| I3-C028 | ACCPD incident rows with an Officer field |
| I3-C031 | MO OHS LPR survey (submitter contacts, arrests) |
| I3-C032 | Cuyahoga ALPR request form (names, e-mails) |
| I3-C036 | Public plate-read and search-result layers |
| I3-C037 | Oakland per-read Socrata sets |
| I3-C064 | FlockWatch (officer, plate, reason) |
| I3-C068 | MI portal archive (mirror of the refused origin plus search audits) |
| I3-C085 | Flower Mound registrant PII |
| I3-C086 | Registry programme forms (rows) |

**Flag counts.**

| Flag | Count |
|---|---|
| private-person-name | 26 |
| private-registrant-location | 14 |
| residential-intersection | 5 |
| free-text-narrative | 5 |
| operator-identifier | 4 |
| officer-name | 4 |
| person-level-enforcement | 3 |
| plate-level | 3 |
| per-search-audit | 3 |
| home-address | 2 |
| rf-derived-candidate | 1 |

**Practices.**
- Only schemas, READMEs and item metadata were read.
- No plate, search reason, officer or registrant value was copied into any committed file.
- Staff account usernames and e-mails seen in ArcGIS owner fields were replaced by role descriptions in the
  committed files.
- The one Eyes on Flock computation (`I3-L005`) counted list lengths. It did not read or copy any search-reason field.

**Hazard for SIG's own pipeline (NEW-1).**
- Keyword and owner discovery on ArcGIS and Socrata surfaces plate-level and registrant-PII layers. The registry
  already needed a manual exclusion for one such layer (`camera_registry_targets.toml:4386-4392`).
- I8 should add a mechanical field denylist at registration time.

---

## 9. Access failures and INACCESSIBLE

Times are UTC, 2026-09-30.

| Host / resource | Status | Time | Effect |
|---|---|---|---|
| WebSearch tool (session-wide) | budget exhausted, 200/200 | 18:15:10Z | no further search-engine discovery (`I3-Q018`) |
| cdt.org (NCSL 2026-07 ALPR PDF) | 403 | 18:12:09Z | host stopped; document not read |
| nj.gov NJSP ALPR audit + directory | 404 | 18:16:23Z | dead origin (NEW-2) |
| archive.org availability API | 429 | 18:16:34Z | host stopped |
| api.www.documentcloud.org | 403 Cloudflare | 18:22:45Z | host stopped (a second request was already in flight) |
| www.muckrock.com API | 403 | 18:22:59Z | host stopped |
| efts.sec.gov (EDGAR FTS) | 403 | 18:26:13Z | host stopped: every C02 cell is blocked |
| nebraskalegislature.gov | DNS failure | 18:27:13Z | NE statute not reached |
| legislature.vermont.gov section page | 200, empty chrome | 18:27:08Z | VT statute not reached |
| chulavistaca.gov | 403 | 18:33:59Z | host stopped |
| fremontpolice.gov | 403 | 18:34:02Z | host stopped |
| TDOT ALPR ArcGIS service (STV org) | 499 Token Required | 18:04:26Z | not public (I3-C029) |
| www.arcgis.com portal self (CCSO org) | 403 in body | 18:05:44Z | publisher unresolved (I3-C009) |
| catalog.data.gov CKAN | 404 ×2 | 18:06:43Z | channel unreachable via this path |
| CityProtect / Axon Community Connect | 200, client-rendered shells | 18:16:35Z / 18:23:32Z | data endpoints not probed (R4) |

---

## 10. Open questions for I7 and the operator

1. **WebSearch budget.** Raise it, or dispatch I3a/I3b continuation rows. Otherwise the 14 unsaturated or
   not-started cells stay open, above all SB 34/VA postings and registry programme pages.
2. **HG-03 inputs.** These terms were captured verbatim:
   - Axon: no robots, spiders or page-scrape;
   - CrimeWatch: no automated access without written consent.

   These were not captured:
   - Flock's terms for `refer.flocksafety.com`;
   - CityProtect's terms.
3. **FDOT layers.** What does "removal status" mean (permit enforcement)? FDOT documents are needed before any
   status becomes a claim (S5 guard).
4. **The MN BCA list.** Geocoding intersections needs a policy. Its locations are statutorily public but textual.
5. **Legistar.** Should the procurement connector gain a technology/vendor keyword pass over the 294 verified
   tenants (I8)? The tenant-id defect `carrollton_ga → carrolltontx` (NEW-3) should be fixed first.
6. **KSUALPRS sharing reports vs the Eyes on Flock share lists.** Which is canonical for SIG's sharing edges?
   (I8 resolution design; one institutional provenance per ADR-130.)
7. **Duty leads awaiting their publications:**
   - VA (VSP aggregate, due 2026-07-01, not located);
   - MD (MCAC annual);
   - CA (CHP auto-theft report);
   - NH (DOS);
   - AR (biannual statistics).

   Per SIG-INGEST-025a these are records leads, not feeds.

---

## 11. Appendix: reproduction

- **Query log.** `data/query_log_I3.csv`:
  - Q lines carry `new=`, and the cell tables are computed from them;
  - F lines carry `cand=`, the HTTP status and the first 12 hex digits of sha256;
  - L lines name the local file and its hash.
- **Captures.** Raw bytes are in `docs/build/logs/next-phase/I3/raw/<fetch-file>`. The index, with full sha256, is
  `docs/build/logs/next-phase/I3/fetch_index.tsv`.
- **Helpers** (scratch, not committed): `fetch.sh`, `txt.py`, `leg.sh`, and `cands/*.py`, which generate
  `candidates_I3.csv`.
- **Local inputs:**
  - `docs/build/logs/next-phase/I1/atlas.csv` (sha256 dcbf8bc13d14…);
  - `eyesonflock.json` (eccb336ab89a…).
- **Self-check (I2 §9):**

  | Check | Result |
  |---|---|
  | Every candidate cites a query or fetch line | pass |
  | Every log line carries a `cell=` for an I3 cell | pass (checked mechanically: 0 bad) |
  | `cand_id`s are unique | pass (90) |
  | `registry_match` computed per §7.6 | pass |
  | No `rights_lane` says "decided" | pass |
  | Dates are from `date -u` or tool timestamps | pass |
  | No plates, search reasons, officer names, registrant data or e-mails in committed files | pass (mechanical scan) |
  | P1/P2 cells at q_min | **fail for 10 cells**: T06-C05, T01-C05-GS, T06-C01, T01-C11-GS, T01-C01, T03-C01, T03-C13, T04-C02, T05-C02, T01-C02. Each carries an honest blocked, n/a or enumerated status in §3 (WebSearch budget, refused origin, or blocked hosts). |
