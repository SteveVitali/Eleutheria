# I7 — Candidate consolidation and the prioritized acquisition backlog

Row **I7** of `META_PLAN.md` Stream I (owner R/D). It merges every source candidate found by I3–I6, the I9a/I9b
saturation pass and the 27 Round-10 acquisition-queue candidates into one de-duplicated set, resolves lineage,
captures terms, runs the Part VIII preflight, assesses feasibility, scores with `acq-score/1`, and ends in a tiered
acquisition backlog. The operator-ready HG-03 packets are in `design/I7-rights-packets.md`.

- **Written** 2026-09-30, work window (`date -u`) 21:01:57Z → 21:37:14Z, by Claude Code (Opus 5.5) in the planning worktree
  (`claude/next-phase-planning`, HEAD `8e25b48e`). Nothing was committed, no control file was edited and no production
  system was touched. `sources.toml` was read only.
- **Outputs** (and nothing else):
  - this note;
  - `data/candidates_consolidated.csv`: 694 rows, one per unique candidate, 72 columns (the §8.6 fields, the I2 §7.3
    extension columns, the I7 columns, the tier and the proposed registry row);
  - `design/I7-rights-packets.md`;
  - `findings/incoming/I7.csv`: NEW-1…NEW-8.
- **Scratch** (gitignored): `docs/build/logs/next-phase/I7/` holds `consolidate2.py`, `overrides2.py` (+ the first
  attempt's `overrides.py`), `terms2.py`, `gen_tables.py`, `mine/linkmine.py`, `fetch.sh`, `fetch_index.tsv` and the raw
  captures `raw/I7-F001…F078`.

> **Planning only.** Proposed registry rows are data in the CSV and are never written to `sources.toml`; every proposed
> row has `ingestion_permitted = false`. Rights lanes are classifications of captured evidence, never decisions: HG-03
> belongs to the operator (P4, P15, R5). Nothing here is legal advice.

**Evidence rule.** A factual sentence cites a fetch id (`I7-F###`, or an upstream row's `I3…I9b-F###` through its
candidate id), a candidate id whose row holds the evidence, or a repo `file:line`. Inferences are labelled.

**P16.** Every I7 fetch was a plain GET with curl's default user-agent (`fetch.sh`); no request carried a name, e-mail,
contact string or other identifier. No keyed or contact-string service was called (no SEC EDGAR). The consolidated CSV,
this note and the packets were scanned for e-mail and IPv4 patterns (0 hits); contact names seen in fetched pages
(e.g. I7-F029, I7-F041) were elided with `[…]`.

---

## 1. Summary

**Inputs → unique candidates.**

| input | rows |
|---|---|
| `candidates_I3.csv` · `I4` · `I5` · `I6` | 90 · 189 · 225 · 43 |
| `candidates_I9a.csv` · `I9b` | 52 · 111 |
| Round-10 acquisition queue (`acquisition_queue.toml`, SRC-001…027) | 27 |
| **total input rows** | **737** |
| merged away (24 merge groups, §3.1) | 43 |
| **unique candidates** | **694** |

**Against the registry, the queue and each other:** **532 new**, **147 related** (a tenant, sibling dataset or same
publisher of a registered source, or a member of another candidate's family), **15 same-as** (the candidate *is* a
registry row or registered tenant: 4 improve an already-live source by configuration, 6 are gated rows that would be flipped, 5 are gated rows that stay as they are). Two same-as
matches were missed by the row-level greps and are raised as NEW-1 (NYC City Record Online = `procportal_nyc_ny`;
Edmonton `7fnd-72gr` = `camreg_edmonton_ab`).

**Lineage.** 593 origin · 79 derived-from · 19 mirror-of · 3 origin-unverified (agency-looking ArcGIS layers with no
agency organisation shown). 98 candidates are **not independent** and score `I = 0`; none is counted as independent
corroboration (ADR-130). OSM remains the origin of the national ALPR layer (I3-C069, widening group W).

**Tiers** (§6):

| tier | n | meaning |
|---|---|---|
| **1** | **108** | high value, reuses an existing connector family, rights covered by an executed precedent, Part VIII pass |
| **W** | **46** | cheap widening of already-live, already-flipped sources: keyword/tenant/filter configuration, label corrections, the statute-seed refresh |
| **2** | **281** | needs a new or extended connector, an individual rights decision, a Part VIII screen design, or a verification step first (27 have no blocker and sit just below the Tier-1 value bar) |
| **3** | **259** | blocked or deferred: Part VIII block (25 + 1 queue row), captured terms prohibit (16), access blocked or lead-only (88), discovery surface with nothing matched (58), derived single-item leads whose origin should be acquired instead (34), mirrors (11), duty leads (5), derived inventories (2), low value (6), other overrides (14) |

**Part VIII preflight:** 507 pass · 161 flagged (a named screen is needed) · **26 blocked** (metadata only; §6.4).
No Tier-1 candidate is flagged; 3 W items carry a screen that the live connector already applies or owes (§6.2).

**Rights lanes (I7 classification):** 463 US public-record factual (of which federal works are marked), 104 restricted
terms (©-only expression, or an operative prohibition), 84 explicit open licence or public-domain statement, 25 non-US
database right, 18 unknown. GL-GATE-07 coverage (E4 vocabulary): 585 PRECEDENT, 48 EXECUTED, 40 ARGUABLE, 21 NOT
COVERED. **Every Tier-1 row is PRECEDENT**; every W row is EXECUTED.

**Terms capture.** 62 new fetches (`I7-F017…F078`, within the ≤ 80 cap) plus the first attempt's 16 (`F001…F016`, reused,
not repeated) captured or checked terms for 85 candidates; 127 more carry terms captured by their row. A local link-miner
over the rows' existing raw captures (no network) located most terms pages before any fetch. Highlights: NL official
publications are free to re-use under Auteurswet art. 11 (I7-F078); GOV.UK content is OGL (I7-F024); DOJ, CBP and
Guam publish public-domain statements (I7-F033, F070, F032); WTSC states its content "may be copied, downloaded, or
distributed" (I7-F073); **four more publishers carry non-commercial clauses** (Honolulu PD, Canada.ca, OPC Canada, CNIL
images; NEW-2); BidNet Direct's terms page refused (403), so E4 R6a's owed capture is still owed (NEW-4).

**Top 15 Tier-1 candidates** (acq-score order, one representative per family; the full list is §6.1):

| # | candidate | score | blind spot it closes |
|---|---|---|---|
| 1 | I3-C077 Cook County awarded-contracts register (Socrata, "Public Domain") | 32 | I1#1 + I1#6: Flock awards via reseller, Axon BWC/DEMS, in a top county |
| 2 | I5-C003 DelDOT FirstMap traffic cameras (445 points, daily) | 31 | I1#5 DOT registry in tier-A **DE** (replaces the contaminated DE dossier, I1 NEW-1) |
| 3 | I6-C010 Washington DES master-contract sales by customer | 31 | I1#6 vendor→customer purchases incl. cities, counties and tribes |
| 4 | I3-C084 DC private security-camera rebate programme (aggregate) | 29 | I1#2 public-private camera subsidy; tier-B **DC** |
| 5 | I4-C052 DC automated safety cameras, violations per camera-month (+ I4-C051 locations, CC-BY-4.0) | 29 | NEW-8 ATE whole class; DC |
| 6 | I5-C001 VTrans ITS device list (88 CCTV) | 29 | I1#5 in tier-A **VT** (highest-weight state) |
| 7 | I5-C009 WVDOH CCTV layer | 29 | I1#5 in tier-A **WV** |
| 8 | I5-C002 MDOT MiDrive cameras (681; stale since 2021, check freshness) | 28 | I1#5 in tier-A **MI** (a no-dossier state) |
| 9 | I3-C002 + I3-C003 FDOT D3 Flock inventory and Flock removal-status layer | 27 | I1#1 Flock at origin + the first removal/currency ledger (I9a NEW-2) |
| 10 | I3-C007 Pueblo CO, representing 13 more agency Flock/LPR layers (I3 FAM-AGOL-ALPR) | 27 | I1#1 Flock/LPR at origin for 14 agencies in 11 states |
| 11 | I9b-C053 Maine DPS annual law-enforcement UAV report | 27 | I1#8 drones in tier-A **ME** |
| 12 | I9b-C078 Hawai'i Judiciary report on interception-order applications (HRS 803-47(b)) | 27 | I1#4 statutory reporting in tier-B **HI** |
| 13 | I4-C103 Arvada PD facial-recognition accountability report (+ I4-C102 CO family) | 27 | I1#4 + I1#8 FRT reporting |
| 14 | I9a-C036 Washington AGO registered ALPR systems (76 agencies + policies) | 26 | I1#1 + I1#4: a statutory statewide operator list |
| 15 | I3-C039 Minnesota BCA list of LPR agencies | 26 | I1#4 + I1#1 statutory list (MN) |

Close behind: I9a-C052 Haskell AR Flock resolution (tier-A **AR**), I9a-C011 Nebraska Crime Commission's 89 ALPR reports,
I9a-C012 Vermont DPS ALPR reports, I9b-C056 FLHSMV statewide red-light report, I9b-C065 Maryland cell-site-simulator
report, I9b-C088 Anchorage's surveillance ordinance (GL1 city, CCOPS family).

**Widening group W (46).** Legistar keyword/vocabulary passes over already-verified tenants (26, incl. the 5 tenant-label
corrections), USAspending vendor/class/ALN vocabulary (5), OSM Overpass widening to the ALPR origin, speed cameras and AU
(3), NYC City Record vendor terms (1), and the 2025–26 statute-seed refresh (11). §6.2.

**Coverage delta headline** (§7). Tier 1 + W reach **7 of 10 tier-A states** (adds DOT/official registries for DE, VT,
WV and MI; ME and AR through reports and resolutions; NH through a tenant-label fix), **3 of 5 tier-B**, **13 of 36 thin
large cities**, **28 of 29 technology classes** and 12 of the 14 I1 blind spots. Adding Tier 2 reaches 8/10 and 4/5,
25/36 cities, all 29 classes, all 13 searchable blind spots (#3 is internal attribution, for I8) and 18 countries. **What stays dark:** MS, WY, MT, KS and SD (Tier 3 or
nothing), American Samoa and the Northern Mariana Islands, North Las Vegas, Flock's own customer and sharing data at
origin (refused), vendor disclosures that need EDGAR (Q-30), and person-level sources (by design).

---

## 2. Method, and deviations

**Inputs read.** META_PLAN §3 (P1–P16), Stream I (I1–I9, I9a/I9b), §7 (Q-19…Q-23, Q-30), §7.1, §8.2, §8.6;
`design/I2-source-search-protocol.md` §0–§1, §6–§7, §11–§12; `research/I1-source-coverage.md` §1, §7–§8; the six
candidate notes (I3 §6/§10, I4 §4/§10, I5 §6/§11, I6 §6/§9, I9a and I9b in full) and all six candidate CSVs;
`design/E4-rights-packets.md` §0–§4; `research/J4-redistribution-matrix.md` §0, §2, §4, §9;
`tasks/src/tasks/data/acquisition_queue.toml` and `tasks/src/tasks/acquisition.py:89-105` (weights);
`connectors/src/connectors/data/sources.toml`, `agenda_tenants.toml` (read only); the six-streams
`source-candidates.csv`; the other rows' fetch indexes and raw captures (local, for link mining).

**Reuse of the first I7 attempt** (stopped by a usage limit before it wrote any committed output). Reused after re-checking:
the merge list (22 groups), the rule engine, 85 hand overrides with written reasons, `fetch.sh` and the 16 terms captures
F001–F016 (not re-fetched). Changed on re-check against the 163 I9 rows and the larger set:
- the input set grew from I3–I6 + queue (574 rows) to 737; 2 merge groups were added (CT PA 26-14; FAA Part 91.113);
- the five tenant-label corrections moved from a forced Tier 1 to the widening group W (they are configuration);
- the access test treated any "403" in an access note as blocking, so families with reachable members (I9a-C001,
  I9a-C035, I4-C167 …) had been dropped to Tier 3; a row now counts as reachable if any fetch answered 200 without a
  challenge/login/JS wall (NEW-8);
- a federal-publisher pattern misread "US school districts" and "U.S. Virgin Islands …" as federal works; fixed;
- derived single-item leads (journalism/NGO articles about a council or agency record) now go to Tier 3 with the origin
  named, instead of crowding Tier 2; multi-jurisdiction compilations (IIHS, WHYF, KSUALPRS, the ACLU CSS map) stay Tier 2;
- tribal publishers and territorial public records got their own lanes (the GL-GATE-07 execution never reached either);
- a host + dataset-id re-check of all 710 rows against `sources.toml` found 2 missed same-as matches (NEW-1) and 4
  host-level relations.

**Merge rules.** Same origin URL or dataset id (ArcGIS item/layer, Socrata 4×4, Legistar tenant, SEC query channel, USAspending
endpoint) → one unit; the primary keeps its fields and the others are listed in `cand_ids_merged` and in `notes`
("I7 MERGED: …"). Families and their targets are **not** merged: a family row (e.g. I3-C001, I9a-C001, I4-C065) is kept as
the channel and each member is its own unit, related by `family_id`. Registry `same-as` rows are units that propose a flip or a
configuration of the existing row, never a new row.

**Lineage rules** (I2 §7.5; ADR-130). A mirror (`same_bytes`, `republished_document`) never counts as independent and is sent
to its origin (Tier 3 "acquire the origin"). Derived summaries (EFF Atlas-style compilations, journalism, NGO trackers) score
`I = 0`. Personal-account or consultant-account ArcGIS layers are presumed non-origin unless an agency origin is shown: two
Flock layers passed on operator-held fields (I3-C026 serial numbers and operating agency; I3-C015 Flock-style fields under the
city account), three did not (I3-C016, I3-C021, I5-C040 → Tier 2, NEW-5). OSM is the origin of the national ALPR layer; the two
ArcGIS republishes stay mirrors (I1 NEW-5) and OzWatch (I5-C343) is an OSM viewer (W: acquire AU ALPR via `osm_overpass`).

**Part VIII preflight** (I2 §7.4, J4 §9). The row verdicts were kept except where I7 applied a recorded rule:
- *incremental-exposure rule*: a configuration of an already-live connector whose J4 class rule already applies (Legistar
  matter metadata under P8-3; USAspending/procportal award rows under P8-6) is judged on the incremental data only, so a
  `private-person-name` flag on matter titles does not block a keyword pass (W);
- the first attempt's re-verdicts are kept: I5-C104 and I5-C014 block → flagged under an `outFields` allowlist (editor-tracking
  usernames are GIS staff ids, never requested), I4-C001 (FAA Part 107) block → flagged under a column-drop screen;
- tribal-sovereignty is treated as a governance flag (I9b-C095).

**Scoring.** `acq-score/1` unchanged: `3G + 3R + 2I + 2U + T + J − 2E − 2A − 2S` (`tasks/src/tasks/acquisition.py:103-105`).
The 27 queue rows keep their `acq-seed/1` dimensions; every other row is assessed under a new assessment version
`acq-assess/I7-1` (§5). The model is **not** extended (§5 gives the reasoning).

**Deviations.**
1. *Fetch hygiene.* F066 (PennDOT "Privacy & Disclaimers") redirected to the landing page (same sha256 as F050); it is recorded
   as not captured. Two guessed terms paths returned 404 (F075 SoundThinking, F076 utah.gov) and one linked page 404 (F019
   alabama.gov). Six hosts answered 403 and were stop-listed after the first refusal (NEW-4); no retry, no mirror, no archive.
2. *No web searches* were run; only terms pages or the landing pages that link to them were fetched.
3. *Snippet-only facts* listed by I9a §9 (CT PA 26-14 retention, MO EO text, the FDOT memo OCR, Urbana, Austin's final
   ordinance, MN HF 3198, the Texas order) were not verified by I7: they are not terms captures and the budget is reserved for
   terms. They stay leads in their rows.

---

## 3. Consolidation

### 3.1 Merge groups (24)

| I7 id | merged candidates (primary first) | what | tier |
|---|---|---|---|
| I7-U110 | I5-C118, I3-C051 | Cleveland City Council legislation (Legistar cityofcleveland) - survei… | W |
| I7-U111 | I5-C120, I3-C053 | Saint Paul City Council legislation (Legistar stpaul) - surveillance-b… | W |
| I7-U112 | I5-C121, I3-C054 | Madison Common Council legislation (Legistar madison) - surveillance-b… | W |
| I7-U113 | I5-C122, I3-C050 | Albuquerque City Council legislation (Legistar cabq) - surveillance-bu… | W |
| I7-U114 | I5-C123, I3-C049 | Metro Nashville Council legislation (Legistar nashville) - surveillanc… | W |
| I7-U115 | I4-C150, I4-C024, I4-C028, I4-C090, I4-C111, I4-C122, I4-C152, I4-C216, I4-C217, I4-C258 | USAspending spending_by_award - prime contracts/IDVs matching mobile-f… | W |
| I7-U116 | I3-C052, I3-C059, I3-C061 | Detroit City Council - Motorola Solutions LPR contract 3004870 (2016) … | W |
| I7-U117 | I3-C048, I4-C013, I4-C091, I4-C162, I4-C206 | Legistar council matters evidencing ALPR / RTCC / registry decisions a… | W |
| I7-U118 | I4-C151, I4-C154, I4-C112 | USAspending sub-awards (grant pass-through) matching mobile-forensics … | W |
| I7-U122 | I3-C055, I3-C060 | Dallas City Council - Flock Group three-year service contract (2025), … | W |
| I7-U123 | I3-C056, I3-C087 | Columbus City Council - Flock Group lease/install contract (2024), For… | W |
| I7-U128 | I4-C250, I4-C025 | USAspending assistance awards, Assistance Listing 16.835 (BJA Body-Wor… | W |
| I7-U145 | I9a-C025, I9a-C018 | Connecticut substitute SB 397 (2026) - Public Act 26-14 'An Act Concer… | W |
| I7-U149 | I6-C021, I4-C075 | GHSA State Laws & Issues: Speed and Red Light Cameras | W |
| I7-U150 | I3-C038, I6-C020 | Automatic License Plate Recognition Systems: Summary of State Laws (Se… | W |
| I7-U165 | I6-C036, I4-C116 | 2024 Federal Agency AI Use Case Inventory (consolidated CSV/XLS) | 2 |
| I7-U176 | I6-C008, I4-C219, I4-C170 | Delaware Checkbook Expenditure Details (+ State of Delaware Checkbook;… | 2 |
| I7-U231 | I6-C043, I4-C305, I4-C026 | SEC EDGAR full-text search (efts) - multi-vendor surveillance terms | 2 |
| I7-U303 | I6-C038, I3-C088 | CourtListener bulk data files (case law, dockets, oral arguments; S3 b… | 2 |
| I7-U307 | I4-C012, I6-C042 | California AB 481 military equipment use policies and annual reports (… | 2 |
| I7-U312 | I4-C307, I4-C318, I4-C319, I4-C320, I4-C321, I4-C322 | Oakland Police Department Shotspotter Data 2013-2015 (PRR 11288 releas… | 2 |
| I7-U426 | I4-C001, SRC-025 | Part 107 Waivers Issued | 2 |
| I7-U478 | I6-C001, SRC-010 | Sourcewell cooperative contract 101223-AXN (Axon Enterprise, public sa… | 3 |
| I7-U677 | I4-C011, I9b-C007 | Part 91.113 Waivers Issued | 3 |

### 3.2 Registry and queue dedupe

- **Same-as (15).** Four improve an already-live source by configuration (W): `procportal_nyc_ny` (I9b-C002), the Legistar
  tenants `clark` and `san_bernardino_ca` (I5-C200/C201, with label corrections) and `osm_overpass` (I3-C069). Gated rows
  that would be flipped (Tier 2): `camreg_edmonton_ab` (I4-C066; E4 R4a), `dhs_fusion_centers` (I4-C270), `ccops_berkeley`
  (SRC-019), `ccops_boston` (SRC-020), `faa_drone_waivers` (I4-C001 + SRC-025), `aclu_cell_site_simulators` (I4-C123).
  Gated rows that stay as they are (Tier 3): `sourcewell` (I6-C001 + SRC-010; terms prohibit), `axon_community_connect`
  (I3-C062; terms prohibit), `ccops_ordinance_disclosures` (I6-C011; enumeration lead only), `govspend` (I6-C005; paid),
  `muckrock` (I6-C031; refused channel).
- **P31-owned rows** are consumed, never re-onboarded: `fema_hsgp_allocations` is related to I6-C027 (OpenFEMA, a different
  route with its own terms) and I4-C112 (merged into the USAspending sub-award slice, W).
- **Queue.** SRC-001…007, SRC-011 and SRC-027 are already packeted in E4 (B1/B2/B3/B6) and are not re-packeted. SRC-010 and
  SRC-025 merged into I6-C001 and I4-C001. The other 16 (SRC-008, 009, 012–024, 026) are assessed here with their `acq-seed/1`
  dimensions carried unchanged; SRC-023 is a member of the DHS privacy-document family (I4-C259).
- **Registry label defects** met while deduping (already raised by I3 NEW-3 and I5 NEW-1/2/4, not re-raised): the W group
  carries their corrections (§6.2) and `design/I7-rights-packets.md` §5 lists them for one approval line.

---

## 4. Terms and licence capture

| fetch | terms page | candidates | captured (verbatim excerpt, trimmed) / result |
|---|---|---|---|
| I7-F017 | https://transportation.wv.gov/content-disclaimer (checked; none) | I5-C009, I5-C010 | NONE-FOUND(checked I7-F017 https://transportation.wv.gov/content-disclaimer: disclaimer/privacy text only; no copyright or licence clause) |
| I7-F018 | https://legislature.vermont.gov/home/site-resources/disclaimers | I9a-C012, I4-C009 | Footer of the Vermont Legislature disclaimers page: "Copyright 2026 State of Vermont. All rights reserved." (expression reserved; no operative restriction on facts captured) (I7-F018) |
| I7-F019 | https://www.alabama.gov/terms-of-use (checked; none) | I9a-C041 | NONE-FOUND(checked I7-F019 https://www.alabama.gov/terms-of-use: HTTP 404) |
| I7-F020 | https://www.honolulupd.org/disclaimer/ | I5-C112 | Honolulu Police Department disclaimer: "Commercial use of any document or image contained on these web pages is prohibited." Footer: "Copyright © 2026 The Honolulu Police Department. All rights reserved." (I7-F020) |
| I7-F021 | https://www.cabq.gov/abq-data/abq-data-disclaimer-1 | I5-C111 | City of Albuquerque ABQ Data terms (portal-level; the SOP PDFs sit on the same cabq.gov site): "The City may require a user of this data to terminate any and all display, distribution or other use of any or all of the data provide… |
| I7-F022 | https://www.daytonohio.gov/site/copyright (checked; none) | I6-C017 | NONE-FOUND(checked I7-F022 https://www.daytonohio.gov/site/copyright: CivicPlus copyright page body not present in the served HTML) |
| I7-F023 | https://detroitmi.gov/privacy (checked; none) | I4-C108, I6-C015, I4-C079, I5-C115 | NONE-FOUND(checked I7-F023 https://detroitmi.gov/privacy: "Privacy Policy / Disclaimer" page: privacy text only; no copyright or licence clause) |
| I7-F024 | https://www.gov.uk/help/terms-conditions | I9b-C102, SRC-026 | GOV.UK terms: "Most content on GOV.UK is subject to Crown copyright protection and is published under the Open Government Licence ( OGL ), which also sets out which content is exempt." (I7-F024) |
| I7-F025 | https://www.atg.wa.gov/privacy-notice (checked; none) | I9a-C036 | NONE-FOUND(checked I7-F025 https://www.atg.wa.gov/privacy-notice: the only policy page linked from /ALPR; privacy notice, no copyright/licence clause) |
| I7-F026 | https://www.canada.ca/en/transparency/terms.html | I9b-C101, I9b-C100, I5-C334, I5-C338 | Canada.ca terms: "Unless otherwise specified you may reproduce the materials in whole or in part for non-commercial purposes, and in any format, without charge or further permission" and "Unless otherwise specified, you may not re… |
| I7-F027 | https://cnil.fr/fr/mentions-legales | I9b-C103 | CNIL mentions légales: "Les textes disponibles sur le site sont des contenus pédagogiques élaborés par la CNIL qui sont mis à disposition selon les termes de licence CC-BY-ND 4.0 FR" ; images: "mises à disposition selon les termes… |
| I7-F028 | https://www.bidnetdirect.com/tsandcs (checked; none) | I5-C132, I5-C133, I5-C134, I5-C223 | NONE-FOUND(checked I7-F028 https://www.bidnetdirect.com/tsandcs: HTTP 403; host stop-listed - E4 R6a terms capture still owed) |
| I7-F029 | https://www.readfrontier.org/frontier-content-sharing-and-collaboratio… | I9b-C092 | The Frontier: "The Frontier allows other media to republish its work for free under the following terms. Frontier reporters must be credited with a byline along with “The Frontier” both online and in print." (I7-F029) |
| I7-F030 | https://www.wsipc.org/disclaimer-and-fair-use-statement | I9b-C005 | WSIPC: "This page may contain copyrighted material the use of which has not always been specifically authorized by the copyright owner." … "If you wish to use any copyrighted material from this site for purposes of your own that g… |
| I7-F031 | https://www.education.ky.gov/Pages/disclaimers.aspx (checked; none) | I9b-C029 | NONE-FOUND(checked I7-F031 https://www.education.ky.gov/Pages/disclaimers.aspx: HTTP 403; host stop-listed (kentucky.gov also 403, I7-F044)) |
| I7-F032 | https://governor.guam.gov/copyright-policy | I9b-C093 | Governor of Guam copyright policy: "Pursuant to federal law, government-produced materials appearing on this site are not copyright protected." and "Except where otherwise noted, third-party content on this site is licensed under … |
| I7-F033 | https://www.justice.gov/legalpolicies | SRC-022, I5-C237 | DOJ legal policies: "Unless otherwise indicated, information on Department of Justice websites is in the public domain and may be copied and distributed without permission. Citation of the Department of Justice as source of the in… |
| I7-F034 | https://www.priv.gc.ca/en/privacy-and-transparency-at-the-opc/terms-an… | I5-C304 | OPC Canada terms: "Unless otherwise specified, you may reproduce the materials in whole or in part and in any format for non-commercial purposes, without charge or further permission" (I7-F034) |
| I7-F035 | https://www.gets.govt.nz/GetsTermsAndConditions.htm | I5-C337 | NZ GETS terms: "By registering as a User or using GETS you are deemed to have accepted the terms of this Agreement." and users warrant they "will keep confidential all Confidential Information, login information and all informatio… |
| I7-F036 | https://algoritmes.overheid.nl/nl/footer/copyright | I5-C363 | Algoritmeregister copyright: "De inhoud van deze website mag worden hergebruikt. Dit geldt voor alle teksten, tenzij bij een onderdeel (zoals een document) staat dat er auteursrechtelijke beperkingen zijn." (I7-F036) |
| I7-F037 | https://www.chicago.gov/city/en/general/disclaimer.html | I3-C089 | City of Chicago disclaimer: third-party-link and liability disclaimers only; footer "City of Chicago Copyright © 2010 - 2026 City of Chicago" (data-portal terms captured separately as I7-F001) (I7-F037) |
| I7-F038 | https://www.miamidade.gov/global/disclaimer/disclaimer.page (checked; … | I5-C204, I4-C160 | NONE-FOUND(checked I7-F038 https://www.miamidade.gov/global/disclaimer/disclaimer.page: liability disclaimer/user agreement page; no copyright or re-use clause in the served text) |
| I7-F039 | https://www1.nyc.gov/home/terms-of-use.page (checked; none) | SRC-015, SRC-016 | NONE-FOUND(checked I7-F039 https://www1.nyc.gov/home/terms-of-use.page: HTTP 403; host stop-listed) |
| I7-F040 | https://fargond.gov/terms-of-use | I5-C042 | City of Fargo terms of use: "The material on this site is made available as a public service." and "Some images on this Website are licensed for our use by a third-party company. It is illegal for you to copy these images and use … |
| I7-F041 | https://www.durhamnc.gov/4120/Credits-Copyright | I5-C125 | City of Durham credits & copyright: "If you're interested in using content or images on this website, please contact […] to confirm" (contact address elided) (I7-F041) |
| I7-F042 | http://www.ocgov.com/contact/disclaimer (checked; none) | I5-C203 | NONE-FOUND(checked I7-F042 http://www.ocgov.com/contact/disclaimer: disclaimer page; no copyright or re-use clause in the served text) |
| I7-F043 | https://open-okc.hub.arcgis.com/pages/okc-disclaimer (checked; none) | SRC-001 | NONE-FOUND(checked I7-F043 https://open-okc.hub.arcgis.com/pages/okc-disclaimer: ArcGIS Hub page is JS-rendered; disclaimer text not in the served HTML) |
| I7-F045 | https://www.pinole.gov/terms-of-use/ | I9a-C008 | City of Pinole terms of use: "Access to and use of the City of Pinole website is provided subject to these terms and conditions." (disclaimers of liability/endorsement/external links; no re-use restriction captured) (I7-F045) |
| I7-F046 | https://www.washington.edu/online/terms/ | I9a-C046 | University of Washington website terms: "Except as allowed by law (such as fair use) or as expressly permitted in connection with specific content, this website and its contents may not be reproduced, modified, distributed, displa… |
| I7-F047 | https://le.utah.gov/documents/disclaimer.htm | I9a-C050, I9b-C049 | Utah Legislature terms of use: "A person or entity may not use any part of the information on a legislative web site for commercial purposes or publish the information for commercial gain without proper attribution of source." (I7… |
| I7-F048;I7-F072 | https://isp.illinois.gov/ (checked; none) | I9a-C019 | NONE-FOUND(checked I7-F048;I7-F072 https://isp.illinois.gov/ + https://www.illinois.gov/About/Privacy.html: landing page links only the illinois.gov privacy page; disclaimers only, no copyright/licence clause) |
| I7-F065 | https://www.flhsmv.gov/disclaimer/ | I9b-C056 | FLHSMV disclaimer: "Various clipart and image collections appearing on this site are used under license by the Department for this site. These images are for viewing purposes only." Footer: "© Copyright 2014 – 2026 Florida Departm… |
| I7-F050 | https://www.penndot.pa.gov/ | I9b-C057 | PennDOT footer: "Copyright © 2026 Commonwealth of Pennsylvania. All rights reserved." (the "Privacy & Disclaimers" link, I7-F066, redirected to the landing page - terms not captured) (I7-F050) |
| I7-F067 | https://mdsp.maryland.gov/terms-use | I9b-C065 | Maryland State Police terms of use: "Your use of the Maryland State Police Web Site constitutes your agreement to all such terms, conditions, and notices." and "you will not use the Maryland State Police Web Site for any purpose t… |
| I7-F052 | https://www.capitol.hawaii.gov/ (checked; none) | I9b-C078 | NONE-FOUND(checked I7-F052 https://www.capitol.hawaii.gov/: HTTP 403; host stop-listed) |
| I7-F053 | https://legislature.maine.gov/ (checked; none) | I9b-C053 | NONE-FOUND(checked I7-F053 https://legislature.maine.gov/: landing page carries no terms/copyright link) |
| I7-F054 | https://www.lrl.mn.gov/ (checked; none) | I9b-C077, I3-C040 | NONE-FOUND(checked I7-F054 https://www.lrl.mn.gov/: landing page carries no terms/copyright link) |
| I7-F055 | https://dls.maryland.gov/ (checked; none) | I9a-C047 | NONE-FOUND(checked I7-F055 https://dls.maryland.gov/: landing page carries no terms/copyright link) |
| I7-F074 | https://www.flsenate.gov/About/Privacy | I9a-C043 | Florida Senate footer: "Disclaimer: The information on this system is unverified. The journals or printed bills of the respective chambers should be consulted for official purposes." "Copyright © 2000- 2026 State of Florida." (I7-… |
| I7-F068 | https://www.arvadaco.gov/copyright (checked; none) | I4-C102, I4-C103 | NONE-FOUND(checked I7-F068 https://www.arvadaco.gov/copyright: CivicPlus copyright page body not present in the served HTML) |
| I7-F058 | https://www.muni.org/ (checked; none) | I9b-C088, I5-C130 | NONE-FOUND(checked I7-F058 https://www.muni.org/: landing page carries no terms/copyright link in the served HTML) |
| I7-F073 | https://wtsc.wa.gov/privacy-policy/ | I4-C067, I4-C068 | WTSC: "Because the content on this site is considered public information (except secure services), it may be copied, downloaded, or distributed. However, we request that you give appropriate byline/photo/image credits." (I7-F073) |
| I7-F078 | https://www.overheid.nl/help/officiele-bekendmakingen/bestanden-en-her… | I9b-C110 | Overheid.nl: "Artikel 11 van de Auteurswet bepaalt dat er geen auteursrecht rust op wetten, besluiten en verordeningen, door de openbare macht uitgevaardigd. Dit betekent dat deze informatie vrij mag worden hergebruikt, tenzij dat… |
| I7-F061;I7-F076 | https://www.utah.gov/pmn/ (checked; none) | I9b-C026 | NONE-FOUND(checked I7-F061;I7-F076 https://www.utah.gov/pmn/ + https://www.utah.gov/support/terms-of-use.html: landing page has no terms link; guessed terms path HTTP 404) |
| I7-F062;I7-F075 | https://www.soundthinking.com/ (checked; none) | I9b-C080 | NONE-FOUND(checked I7-F062;I7-F075 https://www.soundthinking.com/ + /terms-of-use: landing page links only a privacy policy; guessed terms path HTTP 404) |
| I7-F070 | https://www.cbp.gov/site-policy-notices/copyright-notice | I9b-C111 | CBP copyright notice: "Unless a copyright is indicated, information on the U.S. Customs and Border Protection website is in the public domain and may be reproduced, published or otherwise used without the permission of the CBP. We… |
| I7-F064;I7-F071 | https://dps.mn.gov/ (checked; none) | I3-C039, I4-C005 | NONE-FOUND(checked I7-F064;I7-F071 https://dps.mn.gov/ + /privacy-policy: privacy policy only; no copyright/licence clause) |
| I7-F077 | https://policies.google.com/terms | I4-C262 | Google Terms of Service: "Some of our services include content that belongs to Google … You may use Google’s content as allowed by these terms and any service-specific additional terms , but we retain any intellectual property rig… |
| I7-F010 | https://dir.texas.gov/site-policies (checked; none) | I6-C007 | NONE-FOUND(checked I7-F010 https://dir.texas.gov/site-policies: DIR site-policies index (first attempt): links to privacy/linking/disclaimer pages; no copyright or licence clause; data.texas.gov ToU 404 (I6)) |

Row-level captures from I3–I9b (127 units) and the first attempt's 16 captures (Chicago data terms F001, Treasury F002, ICE
F003, OpenFEMA F004, Cook County F006, Mesa F007, DHS F008, Texas DIR F010, Edmonton F011, Flock API F012, CityProtect F013,
Detroit F016; F005/F009/F014/F015 refused or 404) are carried in each row's `terms_verbatim_excerpt`. For 78 Tier-1 rows the
recorded state is "no licence stated" (ArcGIS `licenseInfo` empty, agency PDFs without site terms): this is the fact pattern
the P26.16 GL-GATE-07 flips were executed on, so it does not hold a row out of Tier 1.

---

## 5. `acq-score/1` assessment `acq-assess/I7-1`

Dimensions are ordinal 0…3, estimates (`measured = false`), assigned mechanically from the row fields by `consolidate2.py`
and overridden only with a written reason (`i7_override_note`):

| dim | weight | rubric (I7-1) |
|---|---|---|
| G gap | +3 | best of the row's `gap_ref`: I1#1, #2, #4, #6, #7, NEW-5/6/8 = 3; I1#5, #8–#10, #12–#14, NEW-7, NEW-T28, class gaps = 2; I1#11 = 1; tier-A state = 3, tier-B = 2, other state = 1; GL1 city = 2; territory/tribal = 2; queue P0/P1/P2/P3 = 3/2/1/0; "adjacent" caps at 1 |
| R claims | +3 | procurement, agenda, grant, statutory or CCOPS report = 3; legislation, court, open data, vendor, records release = 2; NGO, academic, journalism, crowdsourced, other = 1; a class-agnostic open-data channel = 0 |
| I independence | +2 | origin + new = 3; origin + related = 2; origin + same-as = 1; mirror or derived = 0 (queue invariant) |
| U structure | +2 | API/ArcGIS/Socrata/CKAN/bulk = 3; HTML = 2; PDF/other = 1; lead-only = 0 |
| T currency | +1 | realtime…monthly = 3; quarterly…biennial = 2; static 2024–26 = 1; older static = 0; irregular/unknown = 1 |
| J jurisdiction | +1 | territory, tribal, tier-A/B state or GL1 city = 3; US national = 2; other = 1 |
| E effort | −2 | configuration of a live source = 0; reuse of a connector family = 1; extended transport or new connector = 2; new heavy connector (JS app, OCDS, WFS/WMS, Laserfiche, Revize, OCR, EDGAR …) = 3; gated platform = 2 |
| A access | −2 | blocked/lead-only = 3; HTML/PDF = 1; structured endpoint = 0 |
| S sensitivity | −2 | Part VIII block = 3; flagged with ≥ 2 flags or free text = 2; one flag = 1; pass = 0 |

**No model extension.** The existing nine dimensions already carry what I7 needed: rights posture is handled outside the
score (tier rule + packets), which keeps the score comparable with the 27 `acq-seed/1` rows and avoids pricing a rights
guess into a number the queue treats as ordinal evidence. Two rules sit beside the score instead of in it: the Tier-1 bar
(score ≥ 18 and G ≥ 2) and the Tier-3 floor (score < 10). A Round-11 reviewer can supersede any dimension under a new
assessment version (§20 data versioning); nothing here edits a landed version.

---

## 6. The prioritized acquisition backlog

The tier rule, applied in order:
1. **W** — the candidate is a configuration, keyword/filter widening, label correction or seed refresh of an already-live,
   already-flipped (or rights-resolved) source.
2. **Tier 3** — any of: Part VIII block; captured terms affirmatively prohibit; no reachable acquisition path; a mirror; a
   derived single-item lead whose origin should be acquired instead; a discovery surface with nothing matched; score < 10.
3. **Tier 1** — Part VIII pass, GL-GATE-07 EXECUTED/PRECEDENT (not share-alike), not a non-US or unknown lane, reuse of an
   existing connector family (not a gated platform), independent origin, feasible, score ≥ 18 and G ≥ 2.
4. **Tier 2** — everything else, with the blocker named in `tier_reason`.

Every Tier-1/2 row carries a proposed registry row in the CSV (`proposed_source_id`, `proposed_name`, `proposed_publisher`,
`proposed_licence`, `proposed_ingestion_permitted = false`, `proposed_cadence`); W rows carry `config-under:<source_id>`;
same-as rows carry `flip:<source_id>`. Proposed ids follow the registry's prefixes (`dot_511_*`, `camreg_*`, `ccops_*`,
`procportal_*`, plus `statrep_*`, `legis_*`, `grant_*`, `agenda_*`, `policy_*` for document families) and were checked
against the 342 registered ids for collisions.

### 6.1 Tier 1 (108)

By family:

| family | n | members (cand ids) |
|---|---|---|
| A. State DOT / state camera layers | 6 | I5-C003, I5-C001, I5-C009, I5-C002, I5-C107, I5-C017 |
| B. Agency Flock/LPR/ALPR location layers | 16 | I3-C002, I3-C003, I3-C007, I3-C012, I3-C014, I3-C015, I3-C017, I3-C019, I3-C020, I3-C023, I3-C024, I3-C025, I3-C026, I3-C010, I3-C013, I3-C018 |
| C. ATE (speed/red-light/bus-lane) layers and aggregates | 15 | I5-C005, I4-C052, I4-C055, I4-C056, I4-C051, I4-C053, I4-C054, I4-C058, I4-C061, I4-C062, I4-C064, I9b-C084, I9b-C083, I9b-C082, I5-C015 |
| D. Other agency GIS/open-data layers (CCTV, PCAM aggregates, procurement registers) | 7 | I3-C077, I6-C010, I3-C084, I5-C106, I3-C082, I3-C079, I3-C081 |
| E. Statutory, oversight and CCOPS reports | 37 | I4-C103, I6-C018, I9b-C053, I9b-C078, I3-C039, I4-C100, I4-C102, I4-C274, I6-C040, I9a-C036, I3-C042, I3-C043, I4-C067, I4-C068, I4-C167, I4-C259, I6-C016, I6-C017, I9a-C011, I9a-C012, I9b-C056, I9b-C057, I9b-C065, I9b-C077, I9b-C088, I4-C109, I4-C261, I4-C269, I9a-C047, I4-C069, I9a-C019, I4-C005, I4-C006, I9a-C042, SRC-012, I9a-C022, I4-C260 |
| F. Legislation (bills, statutes, codes) | 5 | I3-C072, I9b-C068, I4-C120, I9b-C069, I9b-C093 |
| G. Grant/earmark programme documents | 6 | I6-C028, I6-C029, I9a-C043, I9a-C041, I9b-C058, SRC-009 |
| H. Single council/procurement documents | 7 | I9a-C052, I4-C108, I4-C110, I9a-C034, I9b-C003, I9b-C004, I5-C135 |
| I. Agency and district policy pages | 9 | I9b-C040, I9b-C030, I9b-C041, I9b-C042, I9b-C043, I9b-C108, I5-C110, I5-C111, I9b-C109 |

All 108, in score order:

| # | I7 id | cand | candidate | score | blind spots closed | connector | proposed source_id | licence (proposed) | cadence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | I7-U001 | I3-C077 | Cook County Procurement - Awarded Contracts & Amendments: Fl… | 32 | I1#1, I1#6 | dot_511(socrata_rows) | `procportal_cook_county_il_procurement_awarde` | CC0-1.0 | daily |
| 2 | I7-U002 | I5-C003 | Traffic Devices - CAMERA (DE_Boundary_and_Point layer 26) | 31 | I1#5, state:DE(tier A) | dot_511(arcgis_query) | `dot_511_de` | LicenseRef-PublicRecord-FactualCompilation | daily |
| 3 | I7-U003 | I5-C005 | Traffic Devices - Red Light Signals (DE_Boundary_and_Point l… | 31 | I1#5, state:DE(tier A) | dot_511(arcgis_query) | `camreg_de_traffic_devices_red` | LicenseRef-PublicRecord-FactualCompilation | daily |
| 4 | I7-U004 | I6-C010 | Washington DES Statewide Contract (Master Contract) Sales Da… | 31 | I1#6, I1#14 | dot_511(socrata_rows) | `procportal_wa_washington_des_statewide` | LicenseRef-PublicRecord-FactualCompilation | quarterly |
| 5 | I7-U005 | I3-C084 | Private Security Camera Rebate Program and Voucher Program (… | 29 | I1#2, state:DC(tier B) | dot_511(arcgis_query) | `camreg_dc_private_security_camera` | LicenseRef-PublicRecord-FactualCompilation | monthly |
| 6 | I7-U006 | I4-C052 | Automated Safety Cameras (ASC) Violation Count By Month | 29 | NEW-8, state:DC(tier B) | dot_511(arcgis_query) | `camreg_dc_automated_safety_cameras_2` | CC-BY-4.0 | monthly |
| 7 | I7-U007 | I5-C001 | ITS - DeviceList (DeviceLocDetail) | 29 | I1#5, state:VT(tier A) | dot_511(arcgis_query) | `dot_511_vt` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 8 | I7-U008 | I5-C009 | CCTV_WVDOH (WVDOT Assets MapServer layer 22) | 29 | I1#5, state:WV(tier A) | dot_511(arcgis_query) | `dot_511_wv` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 9 | I7-U009 | I4-C055 | Automated Speed Enforcement Violations | 28 | NEW-8 | dot_511(socrata_rows) | `camreg_montgomery_county_md_automated_speed` | CC0-1.0 | quarterly |
| 10 | I7-U010 | I4-C056 | Automated Red Light Violations | 28 | NEW-8 | dot_511(socrata_rows) | `camreg_montgomery_county_md_automated_red_li` | CC0-1.0 | quarterly |
| 11 | I7-U011 | I5-C002 | MiDrive Cameras | 28 | I1#5, state:MI(tier A) | dot_511(arcgis_query) | `dot_511_mi` | LicenseRef-PublicRecord-FactualCompilation | once |
| 12 | I7-U012 | I3-C002 | D3 Flock Camera Data (FDOT District 3 Safety Information) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_fl_d3_flock_camera` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 13 | I7-U013 | I3-C003 | FLOCK removal status layer (FDOT) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_fl_flock_removal_status` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 14 | I7-U014 | I3-C007 | Flock (City of Pueblo, CO) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_pueblo_co_flock` | LicenseRef-PublicRecord-FactualCompilation | once |
| 15 | I7-U015 | I3-C012 | LPR_Cameras (City of Rocky Mount, NC) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_rocky_mount_nc_lpr_cameras` | LicenseRef-PublicRecord-FactualCompilation | once |
| 16 | I7-U016 | I3-C014 | Flock Cameras - Public (City of Shelbyville, TN) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_shelbyville_tn_flock_cameras` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 17 | I7-U017 | I3-C015 | Flock_WFL1 (City of Temecula, CA) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_temecula_ca_flock_wfl1` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 18 | I7-U018 | I3-C017 | Flock Locations (City of Marble Falls, TX) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_marble_falls_tx_flock_locations` | LicenseRef-PublicRecord-FactualCompilation | once |
| 19 | I7-U019 | I3-C019 | Community Safety Cameras (Prince William County, VA) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_prince_william_cou_va_community_safet` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 20 | I7-U020 | I3-C020 | FlockLPRCam (Milford, CT) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_milford_ct_flocklprcam` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 21 | I7-U021 | I3-C023 | LPR Cameras (City of Elgin, IL) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_elgin_il_lpr_cameras` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 22 | I7-U022 | I3-C024 | LPR Cameras (City of South Fulton, GA) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_south_fulton_ga_lpr_cameras` | LicenseRef-PublicRecord-FactualCompilation | once |
| 23 | I7-U023 | I3-C025 | Stationary LPR (Pittsylvania County, VA) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_pittsylvania_count_va_stationary_lpr` | LicenseRef-PublicRecord-FactualCompilation | once |
| 24 | I7-U024 | I3-C026 | LPR_Cameras (City of Alabaster, AL staff account) | 27 | I1#1 | dot_511(arcgis_query) | `camreg_alabaster_al_lpr_cameras` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 25 | I7-U025 | I4-C051 | Automated Safety Cameras (ASC) | 27 | NEW-8, I1#7, state:DC(tier B) | dot_511(arcgis_query) | `camreg_dc_automated_safety_cameras` | CC-BY-4.0 | unknown |
| 26 | I7-U026 | I4-C053 | Speed Camera Violations | 27 | NEW-8 | dot_511(socrata_rows) | `camreg_chicago_il_speed_camera_violations` | LicenseRef-PublicRecord-FactualCompilation | daily |
| 27 | I7-U027 | I4-C054 | Red Light Camera Violations | 27 | NEW-8 | dot_511(socrata_rows) | `camreg_chicago_il_red_light_camera` | LicenseRef-PublicRecord-FactualCompilation | daily |
| 28 | I7-U028 | I4-C058 | MTA Bus Automated Camera Enforced Routes: Beginning October … | 27 | NEW-8 | dot_511(socrata_rows) | `camreg_new_york_city_ny_mta_bus_automated` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 29 | I7-U029 | I4-C061 | Automated Enforcement Locations (Tacoma) | 27 | NEW-8 | dot_511(arcgis_query) | `camreg_tacoma_wa_automated_enforcement_locat` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 30 | I7-U030 | I4-C062 | SpeedCameras_2024 (MCPD Speed camera Locations as of August … | 27 | NEW-8 | dot_511(arcgis_query) | `camreg_montgomery_county_md_speedcameras_202` | LicenseRef-PublicRecord-FactualCompilation | once |
| 31 | I7-U031 | I4-C064 | SchZoneHighligh (school zones where automated enforcement is… | 27 | NEW-8 | dot_511(socrata_rows) | `camreg_howard_county_md_schzonehighligh` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 32 | I7-U032 | I4-C103 | Facial Recognition Technology - Arvada Police Department (SB… | 27 | I1#4, I1#8 | dossier_documents | `statrep_arvada_co_facial_recognition_technol` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 33 | I7-U033 | I6-C018 | City of Columbia MO: 2025 Annual Surveillance Technology Rep… | 27 | I1#4 | government_mandated_disclosure | `ccops_columbia_mo` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 34 | I7-U034 | I9b-C053 | Annual Report of the Department of Public Safety on Maine La… | 27 | I1#8, I1#4, state:ME(tier A) | dossier_documents | `statrep_me_safety_maine_law` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 35 | I7-U035 | I9b-C078 | Hawai'i Judiciary report under HRS 803-47(b) - applications … | 27 | I1#4, state:HI(tier B) | dossier_documents | `statrep_hi_hawai_judiciary_under` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 36 | I7-U036 | I9b-C084 | Red Light Cameras and Direction (City of Lakeland, FL ArcGIS… | 27 | NEW-8 | dot_511(arcgis_query) | `camreg_lakeland_fl_red_light_cameras` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 37 | I7-U037 | I3-C010 | FLOCK_Location (City of Thomasville, GA) | 26 | I1#1 | dot_511(arcgis_query) | `camreg_thomasville_ga_flock_location` | LicenseRef-PublicRecord-FactualCompilation | once |
| 38 | I7-U038 | I3-C013 | Leon County Sheriff's Office Overwatch Viewer (VIGILANT Fixe… | 26 | I1#1, I1#2, I1#10 | dot_511(arcgis_query) | `camreg_leon_county_fl_overwatch_viewer` | LicenseRef-PublicRecord-FactualCompilation | once |
| 39 | I7-U039 | I3-C018 | Flock_Camera_Location (City of Peachtree Corners, GA) | 26 | I1#1 | dot_511(arcgis_query) | `camreg_peachtree_corners_ga_flock_camera_loc` | LicenseRef-PublicRecord-FactualCompilation | once |
| 40 | I7-U040 | I3-C039 | Agencies that use License Plate Readers (LPR) - Minnesota BC… | 26 | I1#4, I1#1 | dossier_documents | `statrep_mn_agencies_that_use` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 41 | I7-U041 | I4-C100 | Facial Recognition / WaTech (Technology Services Board posti… | 26 | I1#4, I1#8 | dossier_documents | `statrep_wa_facial_recognition_watech` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 42 | I7-U042 | I4-C102 | Colorado agency facial recognition accountability reports (C… | 26 | I1#4, I1#8 | dossier_documents | `statrep_co_colorado_agency_facial` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 43 | I7-U043 | I4-C274 | Delaware Information and Analysis Center (DIAC) Privacy SOP | 26 | I1#4, state:DE(tier A) | dossier_documents | `statrep_de_delaware_information_analysis` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 44 | I7-U044 | I5-C107 | Traffic_Cameras / Traffic Operations - Public Monitoring Cam… | 26 | I1#9, city:Lincoln (GL1 thin) | dot_511(arcgis_query) | `camreg_lincoln_ne_traffic_cameras_traffic` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 45 | I7-U045 | I6-C040 | Virginia Reports to the General Assembly (RGA) - published d… | 26 | I1#4 | dossier_documents | `statrep_va_virginia_general_assembly` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 46 | I7-U046 | I9a-C036 | Washington Attorney General's Office - Automated License Pla… | 26 | I1#1, I1#4 | dossier_documents | `statrep_wa_washington_attorney_general` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 47 | I7-U047 | I9a-C052 | City of Haskell AR Resolution No. 19-2025 - contract with Fl… | 26 | I1#1, state:AR(tier A) | dossier_documents | `agenda_haskell_ar_resolution_no_19` | LicenseRef-PublicRecord-FactualCompilation | once |
| 48 | I7-U048 | I9b-C083 | TPVA Red Light Camera Locations 2015 (Suffolk County, NY Tra… | 26 | NEW-8 | dot_511(arcgis_query) | `camreg_suffolk_county_ny_tpva_red_light` | CC-BY-4.0 | once |
| 49 | I7-U049 | I3-C042 | Virginia State Police - ALPR Reporting Requirements (v2, 202… | 25 | I1#4, I1#10 | dossier_documents | `statrep_va_virginia_alpr_reporting` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 50 | I7-U050 | I3-C043 | Virginia State Crime Commission - Law Enforcement Use of ALP… | 25 | I1#4, I1#1 | dossier_documents | `statrep_va_virginia_crime_commission` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 51 | I7-U051 | I4-C067 | 2026 Automated Safety Enforcement Report (Report to the Legi… | 25 | NEW-8, I1#4 | dossier_documents | `statrep_wa_2026_automated_safety` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 52 | I7-U052 | I4-C068 | WA city/county annual automated traffic safety camera report… | 25 | NEW-8, I1#4 | dossier_documents | `statrep_wa_automated_traffic_safety` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 53 | I7-U053 | I4-C108 | Detroit Police Department Weekly Report on Facial Recognitio… | 25 | I1#8, state:MI(tier A), city:Detroit (GL1 thin) | dossier_documents | `agenda_detroit_mi_weekly_facial_recognition` | LicenseRef-PublicRecord-FactualCompilation | weekly |
| 54 | I7-U054 | I4-C167 | DHS Privacy Impact Assessments hub - operational social-medi… | 25 | I1#7, NEW-8 | accountability | `statrep_us_dhs_privacy_impact` | CC0-1.0 | on-change |
| 55 | I7-U055 | I4-C259 | DHS component privacy compliance document indexes (Privacy D… | 25 | I1#13, I1#4, NEW-T28 | accountability | `statrep_us_dhs_component_privacy` | CC0-1.0 | on-change |
| 56 | I7-U056 | I5-C106 | Parks_Cameras (City of Omaha-maintained cameras; College Wor… | 25 | I1#9, city:Omaha (GL1 thin) | dot_511(arcgis_query) | `camreg_omaha_ne_parks_cameras` | LicenseRef-PublicRecord-FactualCompilation | once |
| 57 | I7-U057 | I6-C016 | City of St. Louis: Police Department Surveillance Technology… | 25 | I1#4 | government_mandated_disclosure | `ccops_st_louis_mo` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 58 | I7-U058 | I6-C017 | City of Dayton OH: Surveillance Technology (annual reports, … | 25 | I1#4 | government_mandated_disclosure | `ccops_dayton_oh` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 59 | I7-U059 | I6-C028 | Texas DMV Motor Vehicle Crime Prevention Authority (MVCPA) g… | 25 | I1#6, I1#1 | dossier_documents | `grant_tx_texas_dmv_motor` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 60 | I7-U060 | I6-C029 | California BSCC Organized Retail Theft (ORT) Prevention Gran… | 25 | I1#6, I1#1 | dossier_documents | `grant_ca_california_bscc_organized` | LicenseRef-PublicRecord-FactualCompilation | quarterly |
| 61 | I7-U061 | I9a-C011 | Nebraska Crime Commission - Automatic License Plate Reader R… | 25 | I1#4, I1#1 | dossier_documents | `statrep_ne_nebraska_crime_commission` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 62 | I7-U062 | I9a-C012 | Vermont Department of Public Safety - annual report on Autom… | 25 | I1#4, state:VT(tier A) | dossier_documents | `statrep_vt_vermont_safety_automated` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 63 | I7-U063 | I9a-C043 | Florida Legislature - Local Funding Initiative Requests (LFI… | 25 | I1#6, I1#1 | dossier_documents | `grant_fl_florida_legislature_local` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 64 | I7-U064 | I9b-C056 | Florida Department of Highway Safety and Motor Vehicles - Re… | 25 | NEW-8, I1#4, I1#7 | dossier_documents | `statrep_fl_florida_highway_safety` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 65 | I7-U065 | I9b-C057 | Pennsylvania Work Zone Speed Safety Camera (WZSSC) Program 2… | 25 | NEW-8, I1#4 | dossier_documents | `statrep_pa_pennsylvania_work_zone` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 66 | I7-U066 | I9b-C065 | Maryland Department of State Police - Report Required by Cha… | 25 | I1#8, I1#4 | dossier_documents | `statrep_md_maryland_required_chapters` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 67 | I7-U067 | I9b-C077 | Minnesota State Court Administrator - Report to Legislature … | 25 | I1#4, I1#8 | dossier_documents | `statrep_mn_minnesota_court_administrator` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 68 | I7-U068 | I9b-C082 | Red Light_Speed Camera (City of Medford, OR ArcGIS organisat… | 25 | NEW-8 | dot_511(arcgis_query) | `camreg_medford_or_red_light_speed` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 69 | I7-U069 | I9b-C088 | Anchorage Municipal Code chapter 3.102 'Municipal Use of Sur… | 25 | I1#9, I1#4, city:Anchorage (GL1 thin) | government_mandated_disclosure | `ccops_anchorage_ak` | LicenseRef-PublicRecord-FactualCompilation | once |
| 70 | I7-U070 | I3-C082 | Hyattsville CCTV Camera Program 2024 | 24 | I1#5 | dot_511(arcgis_query) | `camreg_hyattsville_md_cctv_camera_2024` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 71 | I7-U071 | I4-C109 | Policy 610 Cellular Site Simulator Usage and Privacy - Orang… | 24 | I1#4, I1#8 | dossier_documents | `statrep_orange_county_ca_policy_610_cellular` | LicenseRef-DerivedFacts-Citations | on-change |
| 72 | I7-U072 | I4-C110 | Pasadena Police Department Policy 620 Cellular Site Simulato… | 24 | I1#4, I1#8 | dossier_documents | `agenda_pasadena_ca_policy_620_cellular` | LicenseRef-DerivedFacts-Citations | once |
| 73 | I7-U073 | I4-C261 | DHS/OBIM/PIA-004 Homeland Advanced Recognition Technology Sy… | 24 | NEW-T28 | accountability | `statrep_us_dhs_obim_pia` | CC0-1.0 | on-change |
| 74 | I7-U074 | I4-C269 | DHS/CBP Border Surveillance Systems (BSS) - compliance docum… | 24 | NEW-T28 | accountability | `statrep_us_dhs_cbp_border` | CC0-1.0 | on-change |
| 75 | I7-U075 | I5-C015 | Approximate Speed Safety Camera Locations Public | 24 | I1#5 | dot_511(arcgis_query) | `camreg_ct_approximate_speed_safety` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 76 | I7-U076 | I9a-C041 | Alabama ADECA newsroom - Governor's Project Safe Neighborhoo… | 24 | I1#6, I1#1 | dossier_documents | `grant_al_alabama_adeca_newsroom` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 77 | I7-U077 | I9a-C047 | Maryland Department of Legislative Services Library - Mandat… | 24 | I1#4 | dossier_documents | `statrep_md_maryland_legislative_library` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 78 | I7-U078 | I9b-C058 | New Jersey OAG SFY21 Body-Worn Camera Grant Program - Progra… | 24 | I1#4 | dossier_documents | `grant_nj_new_jersey_oag` | LicenseRef-PublicRecord-FactualCompilation | once |
| 79 | I7-U079 | I3-C072 | DHS System of Records Notices referencing license plate data… | 23 | I1#10 | accountability | `legis_us_dhs_system_records` | CC0-1.0 | on-change |
| 80 | I7-U080 | I4-C069 | 2024-2025 Automated Traffic Safety Camera Program Annual Rep… | 23 | NEW-8, I1#4 | dossier_documents | `statrep_seattle_wa_2024_2025_automated` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 81 | I7-U081 | I9a-C019 | Illinois State Police - Automated License Plate Reader Trans… | 23 | I1#4, I1#1 | dossier_documents | `statrep_il_illinois_automated_license` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 82 | I7-U082 | I9a-C034 | City of Des Moines IA council communication 26-235 (2026-06-… | 23 | I1#1, I1#10 | dossier_documents | `agenda_des_moines_ia_communication_26_235` | LicenseRef-PublicRecord-FactualCompilation | once |
| 83 | I7-U083 | I9b-C003 | Jasper County Council special called meeting agenda e-packet… | 23 | I1#7 | dossier_documents | `agenda_jasper_county_sc_special_called_meeti` | LicenseRef-PublicRecord-FactualCompilation | once |
| 84 | I7-U084 | I9b-C004 | Town of Davie Notice of Intent to Award a Sole Source Procur… | 23 | I1#7 | dossier_documents | `procportal_davie_fl_notice_intent_award` | LicenseRef-PublicRecord-FactualCompilation | once |
| 85 | I7-U085 | I9b-C068 | Arizona HB 2574 (56th Legislature, 2nd Regular Session, 2024… | 23 | I1#7, I1#4 | accountability(openstates) | `legis_az_arizona_hb_2574` | LicenseRef-PublicRecord-FactualCompilation | once |
| 86 | I7-U086 | I3-C079 | Police HALO Cameras (Denver Police Department) | 22 | I1#5 | dot_511(arcgis_query) | `camreg_denver_co_halo_cameras` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 87 | I7-U087 | I3-C081 | Seattle Police Department CCTV Pilot Areas | 22 | I1#5 | dot_511(arcgis_query) | `camreg_seattle_wa_cctv_pilot_areas` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 88 | I7-U088 | I4-C005 | Unmanned Aerial Vehicle (UAV) annual reports (Minn. Stat. 62… | 22 | I1#8 | dossier_documents | `statrep_mn_unmanned_aerial_vehicle` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 89 | I7-U089 | I4-C006 | Illinois Freedom From Drone Surveillance Act annual report (… | 22 | I1#8 | dossier_documents | `statrep_il_illinois_freedom_from` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 90 | I7-U090 | I5-C017 | NCDOT_Cameras | 22 | I1#5 | dot_511(arcgis_query) | `dot_511_nc` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 91 | I7-U091 | I5-C135 | RFP2449 Real-Time Intelligence Center Enterprise Solution | 22 | I1#9, city:Winston-Salem (GL1 thin) | dossier_documents | `procportal_forsyth_county_nc_rfp2449_real_ti` | LicenseRef-PublicRecord-FactualCompilation | once |
| 92 | I7-U092 | I9a-C042 | City of Austin Office of the City Auditor - 'APD License Pla… | 22 | I1#4, I1#1 | dossier_documents | `statrep_austin_tx_auditor_apd_license` | LicenseRef-PublicRecord-FactualCompilation | once |
| 93 | I7-U093 | SRC-012 | Seattle OIG annual surveillance usage reviews | 22 | queue P1 (Round-10 gap) | dossier_documents | `statrep_seattle_wa_oig_surveillance_usage` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 94 | I7-U094 | I4-C120 | California Government Code § 53166 - cellular communications… | 21 | I1#4, I1#8 | dossier_documents | `legis_ca_california_code_53166` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 95 | I7-U095 | I9a-C022 | City of Austin TX - Transparent and Responsible Use of Surve… | 21 | I1#4 | government_mandated_disclosure | `ccops_austin_tx` | LicenseRef-PublicRecord-FactualCompilation | once |
| 96 | I7-U096 | I9b-C040 | District student-monitoring self-disclosure pages (school we… | 21 | I1#7 | dossier_documents | `policy_us_district_student_monitoring` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 97 | I7-U097 | I9b-C069 | New York Senate Bill S7037 (2025): 'social media monitoring … | 21 | I1#7 | accountability(openstates) | `legis_ny_new_york_senate` | LicenseRef-PublicRecord-FactualCompilation | once |
| 98 | I7-U098 | I9b-C093 | Governor of Guam press release: 'Bill for GPD Security Camer… | 21 | I1#14, territory:GU | dossier_documents | `legis_gu_governor_guam_press` | CC0-1.0 | once |
| 99 | I7-U099 | SRC-009 | Oklahoma JAG-LLE local equipment funding | 21 | queue P1 (Round-10 gap) | dossier_documents | `grant_ok_oklahoma_jag_lle` | LicenseRef-PublicRecord-FactualCompilation | unknown |
| 100 | I7-U100 | I4-C260 | DHS/CBP/PIA-080 CBP Commercial Telemetry Data Evaluation | 20 | I1#13 | accountability | `statrep_us_dhs_cbp_pia` | CC0-1.0 | once |
| 101 | I7-U101 | I9b-C030 | St. Cloud Area School District (ISD 742) - 'Securly' parent … | 20 | I1#7 | dossier_documents | `policy_st_cloud_mn_area_school_district` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 102 | I7-U102 | I9b-C041 | Onslow County Schools (NC) - 'Gaggle Safety Management' page… | 20 | I1#7 | dossier_documents | `policy_onslow_county_nc_schools_gaggle_safet` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 103 | I7-U103 | I9b-C042 | Pflugerville ISD (TX) - 'Gaggle' page (Safety & Emergency Ma… | 20 | I1#7 | dossier_documents | `policy_pflugerville_tx_isd_gaggle_page` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 104 | I7-U104 | I9b-C043 | Whitesboro Central School District (NY) - 'Lightspeed Alert'… | 20 | I1#7 | dossier_documents | `policy_whitesboro_ny_central_school_district` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 105 | I7-U105 | I9b-C108 | Bangor Police Department General Order 2-59 'Unmanned Aerial… | 20 | I1#8, state:ME(tier A) | dossier_documents | `policy_bangor_me_general_order_59` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 106 | I7-U106 | I5-C110 | Houston Police Department General Orders | 19 | I1#9, city:Houston (GL1 thin) | dossier_documents | `policy_houston_tx_general_orders` | LicenseRef-PublicRecord-FactualCompilation | on-change |
| 107 | I7-U107 | I5-C111 | APD Standard Operating Procedures (incl. SOP 1-22 Automated … | 18 | I1#9, state:NM(tier B), city:Albuquerque (GL1 thin) | dossier_documents | `policy_albuquerque_nm_apd_standard_operating` | LicenseRef-PublicRecord-FactualCompilation | annual |
| 108 | I7-U108 | I9b-C109 | Little Rock Police Department General Order G.O. 332 'Small … | 18 | I1#8, state:AR(tier A) | dossier_documents | `policy_little_rock_ar_general_order_332` | LicenseRef-PublicRecord-FactualCompilation | on-change |

Notes for I8 on Tier 1:
- **Agency Flock/LPR layers** (14, plus the two FDOT layers): all publish with empty `licenseInfo`; several carry private-operator columns that were
  checked (Org_Type/Owner) and the ones that do are Tier 2 under screen S1. I3-C019 includes *proposed* sites (do not assert
  as installed); I3-C020 states "approximate locations"; I3-C014 has monthly hotlist-hit aggregates (verify what "Hits" means).
- **FDOT** (I3-C002/C003) pairs with the FDOT removal memo I9a-C027 (Tier 2: image-only PDF). Status fields are
  permit-compliance facts, not deployment claims, until FDOT's policy documents are read (S5 guard).
- **ATE layers** (15) need an ontology home first (I1 NEW-8 / I4 NEW-9): the rights and access are ready, the concept is not.
- **Statutory reports** are per-document `dossier_documents` targets. Model registrations (WA AGO, MN BCA) as agency
  assertions of registration, not verified deployments (the AGO says it did not verify the certifications, I9a-C036).
- **Queue rows** SRC-009 and SRC-012 reach Tier 1 on their carried `acq-seed/1` dimensions.

### 6.2 Widening group W (46): configuration of existing connectors

| widening under | n | what to configure | members |
|---|---|---|---|
| `legistar` | 26 | Concord, NH Legistar (tenant concordnh…; Cleveland City Council legislation (Le…; Saint Paul City Council legislation (L…; Madison Common Council legi… | I5-C041, I5-C118, I5-C120, I5-C121, I5-C122, I5-C123, I3-C052, I3-C048, I5-C116, I5-C117, I5-C119, I3-C055, I3-C056, I3-C057, I3-C058, I4-C205, I4-C014, I4-C076, I4-C117, I4-C218, I4-C313, I9b-C105, I4-C078, I5-C200, I5-C201, I6-C023 |
| `usaspending` | 5 | USAspending spending_by_award - prime …; USAspending sub-awards (grant pass-thr…; USAspending assistance awards, Assista…; OJP grant awards (Tableau a… | I4-C150, I4-C151, I4-C250, I6-C026, I4-C266 |
| `procportal_nyc_ny` | 1 | City Record Online (CROL) - NYC Open D… | I9b-C002 |
| `osm_overpass` | 3 | OpenStreetMap highway=speed_camera nod…; OpenStreetMap surveillance:type=ALPR -…; OzWatch — open crowdsourced map of ANP… | I4-C316, I3-C069, I5-C343 |
| `state_alpr_statute_inventory` | 11 | New Mexico SB 40 (2026) Driver Privacy…; Code of Virginia 2.2-5517 Use of autom…; Washington ESSB 6002 (2026) 'Concernin…; Oregon SB 1516 (2026 R1) - … | I9a-C016, I3-C041, I9a-C015, I9a-C017, I9a-C024, I9a-C025, I9a-C026, I9a-C031, I6-C021, I3-C038, I6-C022 |

| I7 id | cand | candidate | score | configuration | Part VIII | blind spots |
|---|---|---|---|---|---|---|
| I7-U109 | I5-C041 | Concord, NH Legistar (tenant concordnh) | 34 | config-under:legistar | pass | I1#5, state:NH(tier A) |
| I7-U110 | I5-C118, I3-C051 | Cleveland City Council legislation (Legistar cityofcleveland… | 34 | config-under:legistar | pass | I1#9, I1#1, city:Cleveland (GL1 thin) |
| I7-U111 | I5-C120, I3-C053 | Saint Paul City Council legislation (Legistar stpaul) - surv… | 34 | config-under:legistar | pass | I1#9, I1#1, city:Saint Paul (GL1 thin) |
| I7-U112 | I5-C121, I3-C054 | Madison Common Council legislation (Legistar madison) - surv… | 34 | config-under:legistar | pass | I1#4, I1#9, I1#10, city:Madison (GL1 thin) |
| I7-U113 | I5-C122, I3-C050 | Albuquerque City Council legislation (Legistar cabq) - surve… | 34 | config-under:legistar | pass | I1#9, I1#4, state:NM(tier B), city:Albuquerque (GL1 thin) |
| I7-U114 | I5-C123, I3-C049 | Metro Nashville Council legislation (Legistar nashville) - s… | 34 | config-under:legistar | pass | I1#9, I1#1, city:Nashville (GL1 thin) |
| I7-U115 | I4-C150, I4-C024, I4-C028, I4-C090, I4-C | USAspending spending_by_award - prime contracts/IDVs matchin… | 33 | config-under:usaspending | pass | I1#7, I1#13, NEW-8, I1#8 |
| I7-U116 | I3-C052, I3-C059, I3-C061 | Detroit City Council - Motorola Solutions LPR contract 30048… | 32 | config-under:legistar | pass | I1#1, I1#6, I1#2, state:MI(tier A), city:Detroit (GL1 thin) |
| I7-U117 | I3-C048, I4-C013, I4-C091, I4-C162, I4-C | Legistar council matters evidencing ALPR / RTCC / registry d… | 31 | config-under:legistar | pass | I1#1, I1#2, I1#6, I1#8, NEW-8, I1#7 |
| I7-U118 | I4-C151, I4-C154, I4-C112 | USAspending sub-awards (grant pass-through) matching mobile-… | 31 | config-under:usaspending | pass | I1#7, I1#13, NEW-8, I1#8 |
| I7-U119 | I5-C116 | Charlotte City Council legislation (Legistar charlottenc) - … | 31 | config-under:legistar | pass | I1#9, city:Charlotte (GL1 thin) |
| I7-U120 | I5-C117 | Newark Municipal Council legislation (Legistar newark) - res… | 31 | config-under:legistar | pass | I1#9, city:Newark (GL1 thin) |
| I7-U121 | I5-C119 | Winston-Salem City Council legislation (Legistar winston-sal… | 31 | config-under:legistar | pass | I1#9, city:Winston-Salem (GL1 thin) |
| I7-U122 | I3-C055, I3-C060 | Dallas City Council - Flock Group three-year service contrac… | 30 | config-under:legistar | pass | I1#1, I1#2 |
| I7-U123 | I3-C056, I3-C087 | Columbus City Council - Flock Group lease/install contract (… | 30 | config-under:legistar | pass | I1#1, I1#2, I1#10 |
| I7-U124 | I3-C057 | Louisville Metro Council - district-fund appropriations to L… | 30 | config-under:legistar | pass | I1#1, I1#2, I1#6 |
| I7-U125 | I3-C058 | Brazoria County Commissioners Court - Texas DPS LPR MOU and … | 30 | config-under:legistar | pass | I1#10, I1#1 |
| I7-U126 | I4-C205 | Oakland USD Board of Education — Legistar files 21-0665 and … | 30 | config-under:legistar | pass | I1#7 |
| I7-U127 | I9b-C002 | City Record Online (CROL) - NYC Open Data dg92-zbpx | 30 | config-under:procportal_nyc_ny | pass | I1#6, I1#7 |
| I7-U128 | I4-C250, I4-C025 | USAspending assistance awards, Assistance Listing 16.835 (BJ… | 29 | config-under:usaspending | pass | I1#6, class:BWC(1/1 hosted, I1#8 |
| I7-U129 | I4-C014 | City of Mesa AZ council matters: police UAS purchases and Dr… | 27 | config-under:legistar | pass | I1#8 |
| I7-U130 | I4-C076 | Oakland ShotSpotter/SoundThinking legislative matters (Legis… | 27 | config-under:legistar | pass | I1#8 |
| I7-U131 | I4-C117 | City of Milwaukee Legistar matters - 'facial recognition' (4… | 27 | config-under:legistar | pass | I1#8 |
| I7-U132 | I4-C316 | OpenStreetMap highway=speed_camera nodes and enforcement rel… | 27 | config-under:osm_overpass | pass | NEW-8, I1#7 |
| I7-U133 | I4-C218 | Cook County Board of Commissioners (Legistar) — electronic m… | 26 | config-under:legistar | flagged | NEW-8 |
| I7-U134 | I4-C313 | City Council Meeting Summary: Approves Red Light Camera Enfo… | 26 | config-under:legistar | pass | NEW-8, I1#7 |
| I7-U135 | I9b-C105 | Washoe County Board of County Commissioners 2026-06-16 item … | 26 | config-under:legistar | pass | I1#7 |
| I7-U136 | I6-C026 | OJP grant awards (Tableau award dashboards; BJA award detail… | 24 | config-under:usaspending | pass | I1#6 |
| I7-U137 | I9a-C016 | New Mexico SB 40 (2026) Driver Privacy and Safety Act - ALPR… | 24 | config-under:state_alpr_statute_inventory | pass | I1#4, state:NM(tier B) |
| I7-U138 | I3-C041 | Code of Virginia 2.2-5517 Use of automatic license plate rec… | 22 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#10 |
| I7-U139 | I4-C078 | Legislation ID 24-1023: Second Amendment to Agreement with S… | 22 | config-under:legistar | pass | I1#8 |
| I7-U140 | I5-C200 | Clark County Board of Commissioners — Legistar InSite tenant… | 22 | config-under:legistar | pass | county:Clark County NV (top county) |
| I7-U141 | I5-C201 | San Bernardino County Board of Supervisors — Legistar InSite… | 22 | config-under:legistar | pass | county:San Bernardino County CA (top county) |
| I7-U142 | I9a-C015 | Washington ESSB 6002 (2026) 'Concerning driver privacy prote… | 22 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#10 |
| I7-U143 | I9a-C017 | Oregon SB 1516 (2026 R1) - ALPR authorized uses, 30-day rete… | 22 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#10 |
| I7-U144 | I9a-C024 | Kentucky HB 58 (2026 RS) 'AN ACT relating to privacy protect… | 22 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#1 |
| I7-U145 | I9a-C025, I9a-C018 | Connecticut substitute SB 397 (2026) - Public Act 26-14 'An … | 22 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#10 |
| I7-U146 | I9a-C026 | Missouri Executive Order 26-18 (2026-09-16) - minimum standa… | 22 | config-under:state_alpr_statute_inventory | pass | I1#4 |
| I7-U147 | I9a-C031 | Idaho S1180 (2025) - automated license plate readers and the… | 22 | config-under:state_alpr_statute_inventory | pass | I1#4 |
| I7-U148 | I3-C069 | OpenStreetMap surveillance:type=ALPR - the ORIGIN of the nat… | 21 | config-under:osm_overpass | flagged | NEW-5, NEW-7, I1#1 |
| I7-U149 | I6-C021, I4-C075 | GHSA State Laws & Issues: Speed and Red Light Cameras | 20 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#7, NEW-8 |
| I7-U150 | I3-C038, I6-C020 | Automatic License Plate Recognition Systems: Summary of Stat… | 16 | config-under:state_alpr_statute_inventory | pass | I1#4, I1#10, territory:GU,PR,VI |
| I7-U151 | I6-C023 | S.T.O.P. Legislative Tracker (New York City Council and New … | 16 | config-under:legistar | pass | I1#4 |
| I7-U152 | I6-C022 | NCSL: Artificial Intelligence and Law Enforcement - the Fede… | 12 | config-under:state_alpr_statute_inventory | pass | I1#4 |
| I7-U153 | I4-C266 | Mijente #NoTechForICE - 'Who's Behind ICE: The Tech and Data… | 11 | config-under:usaspending | pass | NEW-T28, I1#13 |
| I7-U154 | I5-C343 | OzWatch — open crowdsourced map of ANPR/ALPR and public surv… | 6 | config-under:osm_overpass | flagged | I1#11 |

What each W line configures:
- **Legistar (26).** A technology/vendor keyword pass (ALPR, LPR, Flock, Vigilant, Fusus, RTCC, ShotSpotter/SoundThinking,
  drone/UAS, facial recognition, Cellebrite/GrayKey, Dataminr, Gaggle …) over tenants that are already verified, plus the
  agenda-vocabulary additions (I3-C048, I4-C091, I4-C162: ATE, video analytics, biometrics, forensics, SMM with word
  boundaries, I4 NEW-6). Fix the five label defects in the same change (Charlotte `charlottenc` labelled IA; `sanbernardino`
  labelled City but serving the County Board; `concordnh` labelled Concord CA; `newark` and `clark` unresolved) and
  `carrollton_ga → carrolltontx` (I3 NEW-3). Test `substringof` case behaviour first (I4 Q5). Matter metadata only: attachment
  and minute text stay out of scope (J4 P8-3).
- **USAspending (5).** Vendor names (SoundThinking's rename, Cellebrite, Magnet/Grayshift, Dataminr, Babel Street, Skydio,
  BRINC, Axon, Motorola, Flock), product-class keywords, sub-award slices and Assistance Listing filters (ALN 16.835 BWC; FEMA
  C-UAS); drop natural-person recipients (J4 P8-6). Answers I4 NEW-5.
- **OSM Overpass (3).** Widen to the ALPR origin (`surveillance:type=ALPR`, 154,814 objects vs 132,689 in the stale republish,
  I3-C069), `highway=speed_camera` (I4-C316) and AU (I5-C343). Strip `user`/`uid` before capture (J4 P8-8); the RF-derived and
  residential-intersection screen is owed either way, because the same exposure already ships through the ArcGIS republish.
- **NYC City Record Online (1).** Add SMM/forensics/GSD vendor terms with word-boundary matching (I9b-C002 notes two false
  positives) to the live `procportal_nyc_ny`.
- **Statute seed refresh (11).** Add the 2025–26 ALPR enactments and instruments verified at origin by I9a (WA, NM, OR, CT, KY,
  ID; MO EO 26-18) and VA 2.2-5517, citing the legislature origin rather than NCSL; LAPPA 2025, GHSA and the NCSL AI page serve
  as inventories only. The seed row stays `ingestion_permitted = false` by design (P27.2); the refresh path is NEW-7.

### 6.3 Tier 2 (281)

| blocker class | n | highest-scoring members |
|---|---|---|
| 0. Already packeted in E4 (not re-packeted) | 8 | SRC-002 (25), SRC-003 (25), SRC-004 (25), SRC-007 (24), SRC-001 (23), SRC-006 (23), SRC-011 (23), SRC-005 (18) |
| 1. Blocked on Q-30 contact string (P16) + new connector | 4 | I4-C304 (26), I4-C153 (25), I6-C043 (23), I4-C082 (18) |
| 2. Part VIII screen design (± connector/rights) | 109 | I4-C086 (28), I6-C007 (28), I4-C065 (27), I3-C078 (26), I4-C164 (26), I5-C101 (26), I5-C226 (26), I6-C008 (26), I6-C025 (26), I3-C004 (25) |
| 3. Individual rights decision (± connector) | 39 | I6-C027 (28), I4-C063 (25), I4-C066 (25), I5-C319 (24), I9b-C017 (24), I9b-C101 (24), I9a-C040 (23), I5-C227 (22), I5-C328 (21), I9b-C094 (21) |
| 4. New or extended connector (rights covered by precedent) | 79 | I3-C076 (30), I4-C085 (30), I6-C024 (28), I6-C036 (27), I9b-C102 (27), I4-C171 (26), I4-C280 (26), I4-C211 (25), I5-C042 (25), I5-C124 (25) |
| 5. Verification / lineage / data-quality step first | 15 | I5-C010 (29), I3-C016 (27), I3-C021 (27), I5-C006 (26), I5-C040 (26), I9b-C048 (26), I5-C016 (21), I4-C275 (19), I5-C013 (19), I9a-C027 (18) |
| 6. No blocker; below the Tier-1 value bar | 27 | I5-C018 (21), I5-C313 (21), I5-C325 (21), I5-C330 (21), I5-C208 (20), I5-C305 (20), I5-C307 (20), I9b-C103 (20), SRC-015 (19), SRC-016 (18) |

The 40 highest-scoring Tier-2 rows:

| I7 id | cand | candidate | score | blocker | proposed source_id | licence (proposed) |
|---|---|---|---|---|---|---|
| I7-U155 | I3-C076 | Municipal contract / expenditure registers on Socrata a… | 30 | New or extended connector (rights cov | `procportal_us_contract_expenditure_registers` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U156 | I4-C085 | Wiretap Report (annual, 18 U.S.C. §2519) - summary tabl… | 30 | New or extended connector (rights cov | `statrep_us_wiretap_summary_tables` | CC0-1.0 |
| I7-U157 | I5-C010 | CCTV_WVPA (WVDOT Assets MapServer layer 23) | 29 | Verification / lineage / data-quality | `dot_511_wv_2` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U158 | I4-C086 | Wiretap Appendix Tables A-1 (U.S. District Courts) and … | 28 | Part VIII screen design (± connector/ | `statrep_us_wiretap_appendix_tables` | CC0-1.0 |
| I7-U159 | I6-C007 | Texas DIR Cooperative Contracts vendor sales data (VSR … | 28 | Part VIII screen design (± connector/ | `procportal_tx_texas_dir_cooperative` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U160 | I6-C024 | Federal Register API (documents search: notices, rules,… | 28 | New or extended connector (rights cov | `legis_us_federal_register_api` | CC0-1.0 |
| I7-U161 | I6-C027 | OpenFEMA: Non-Disaster and Assistance to Firefighter Gr… | 28 | Individual rights decision (± connect | `grant_us_openfema_non_disaster` | UNDETERMINED |
| I7-U162 | I3-C016 | flock (City of Jeffersonville, IN) | 27 | Verification / lineage / data-quality | `camreg_jeffersonville_in_flock` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U163 | I3-C021 | Flock camera locations / Flock Camera Map (Monterey Par… | 27 | Verification / lineage / data-quality | `camreg_monterey_park_ca_flock_camera_locatio` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U164 | I4-C065 | Additional US agency ATE items on ArcGIS Hub (metadata … | 27 | Part VIII screen design (± connector/ | `camreg_medford_or_additional_agency_ate` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U165 | I6-C036 | 2024 Federal Agency AI Use Case Inventory (consolidated… | 27 | New or extended connector (rights cov | `statrep_us_2024_federal_agency` | CC0-1.0 |
| I7-U166 | I9b-C102 | Home Office - 'Live facial recognition in Immigration E… | 27 | New or extended connector (rights cov | `statrep_gb_home_live_facial` | OGL-3.0 |
| I7-U167 | I3-C078 | City of Mesa AZ - City Expenditures: payments to Flock … | 26 | Part VIII screen design (± connector/ | `procportal_mesa_az_expenditures_payments_flo` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U168 | I4-C164 | Socrata-hosted government vendor-payment / open-checkbo… | 26 | Part VIII screen design (± connector/ | `camreg_us_socrata_hosted_vendor` | ODbL-1.0 |
| I7-U169 | I4-C171 | New Jersey YourMoney - Agency Purchasing (ubnu-tqu7) | 26 | New or extended connector (rights cov | `camreg_nj_new_jersey_yourmoney` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U170 | I4-C280 | ICE 287(g) Participating Agencies (XLSX) | 26 | New or extended connector (rights cov | `statrep_us_ice_287_participating` | CC0-1.0 |
| I7-U171 | I4-C304 | Verra Mobility Corp — Form 10-K for fiscal 2025 (access… | 26 | Blocked on Q-30 contact string (P16)  | `statrep_us_verra_mobility_corp` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U172 | I5-C006 | Statewide CCTV View | 26 | Verification / lineage / data-quality | `dot_511_nm` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U173 | I5-C040 | Park Cameras (City of Santa Fe park camera locations) | 26 | Verification / lineage / data-quality | `camreg_santa_fe_nm_park_cameras` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U174 | I5-C101 | Project Green Light Locations | 26 | Part VIII screen design (± connector/ | `camreg_detroit_mi_project_green_light` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U175 | I5-C226 | Consulta del Registro de Contratos (Oficina de la Contr… | 26 | Part VIII screen design (± connector/ | `procportal_pr_consulta_del_registro` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U176 | I6-C008 | Delaware Checkbook Expenditure Details (+ State of Dela… | 26 | Part VIII screen design (± connector/ | `procportal_de_delaware_checkbook_expenditure` | CC0-1.0 |
| I7-U177 | I6-C025 | Treasury SLFRF quarterly Project and Expenditure data (… | 26 | Part VIII screen design (± connector/ | `grant_us_treasury_slfrf_quarterly` | CC0-1.0 |
| I7-U178 | I9b-C048 | City of St. Petersburg, Florida - ArcGIS Online organis… | 26 | Verification / lineage / data-quality | `camreg_st_petersburg_fl_florida_arcgis_onlin` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U179 | I3-C004 | D4 - Camera Survey (FDOT District 4 ROW camera inventor… | 25 | Part VIII screen design (± connector/ | `camreg_broward_county_fl_d4_camera_survey` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U180 | I3-C005 | Flock_Camera_Locations2 (Savannah Police Department) | 25 | Part VIII screen design (± connector/ | `camreg_savannah_ga_flock_camera_locations2` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U181 | I3-C008 | Flock_Location_Data view (East Baton Rouge Sheriff's Of… | 25 | Part VIII screen design (± connector/ | `camreg_east_baton_rouge_p_la_flock_location` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U182 | I3-C009 | FLOCK_CAMERAS_ASOF_20240318 (CCSO, west Georgia; org un… | 25 | Part VIII screen design (± connector/ | `camreg_ga_flock_cameras_asof` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U183 | I3-C011 | City of Gastonia NC Flock layers: Condor Cameras, LPR, … | 25 | Part VIII screen design (± connector/ | `camreg_gastonia_nc_flock_condor_cameras` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U184 | I4-C063 | Speed Safety Cameras (Bellevue) | 25 | Individual rights decision (± connect | `camreg_bellevue_wa_speed_safety_cameras` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U185 | I4-C066 | Edmonton photo-enforcement datasets (ISD locations, pho… | 25 | Individual rights decision (± connect | `camreg_edmonton_ab` | OGL-3.0 |
| I7-U186 | I4-C153 | Cellebrite DI Ltd. SEC filings (Form 20-F annual report… | 25 | Blocked on Q-30 contact string (P16)  | `vendor_us_cellebrite_di_ltd` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U187 | I4-C156 | Washington State Open Checkbook - vendor payments (fisc… | 25 | Part VIII screen design (± connector/ | `opendata_wa_washington_open_checkbook` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U188 | I4-C211 | NCES School Survey on Crime and Safety (SSOCS) public-u… | 25 | New or extended connector (rights cov | `opendata_us_nces_school_survey` | CC0-1.0 |
| I7-U189 | I5-C042 | Fargo City Commission Agendas & Minutes | 25 | New or extended connector (rights cov | `agenda_fargo_nd_commission_agendas_minutes` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U190 | I5-C124 | Jersey City Digital Agenda (Municipal Council portal) | 25 | New or extended connector (rights cov | `agenda_jersey_city_nj_digital_agenda` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U191 | I5-C125 | Agenda Center - Durham, NC (CivicEngage) | 25 | New or extended connector (rights cov | `agenda_durham_nc_agenda_center` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U192 | I5-C126 | Agenda Center - Hialeah, FL (CivicEngage) | 25 | New or extended connector (rights cov | `agenda_hialeah_fl_agenda_center` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U193 | I5-C127 | Frisco OnBase Agenda Online | 25 | New or extended connector (rights cov | `agenda_frisco_tx_onbase_agenda_online` | LicenseRef-PublicRecord-FactualCompilati… |
| I7-U194 | I5-C128 | Tampa City Council OnBase Agenda Online | 25 | New or extended connector (rights cov | `agenda_tampa_fl_onbase_agenda_online` | LicenseRef-PublicRecord-FactualCompilati… |

New or extended connectors that Tier 2 would need (grouped by the row's own protocol label; many are small HTML/PDF/CSV
readers that I8 can fold into fewer families):

| new/extended connector (proposed) | Tier-2 candidates |
|---|---|
| extend:dot_511(socrata SoQL aggregate) | 11 |
| new:ckan_package_search | 11 |
| new:sutra_medidas | 7 |
| new:coop_contract_docs | 6 |
| new:html_list | 4 |
| new:ogc_wfs | 4 |
| new:sec_edgar_fts | 3 |
| new:civicplus_agendacenter | 3 |
| new:opendatasoft_explore | 3 |
| new:csv_file | 3 |
| new:ogc_wms | 3 |
| new:uscourts_tables | 2 |
| new:ai_inventory | 2 |
| new:ice_287g_list | 2 |
| new:civicweb | 2 |
| new:onbase_agendaonline | 2 |
| new:agendaplus_html | 2 |
| new:ocds | 2 |
| new:csv_bulk | 2 |
| new:open_canada_search | 2 |
| new:geojson_file | 2 |
| new:xlsx_file | 2 |
| new:miamidade_govaction | 2 |
| new:unspecified | 2 |
| new:federal_register_api | 1 |
| … 51 more single-row protocol labels | 51 |

### 6.4 Tier 3 (259)

| primary reason | n | examples |
|---|---|---|
| access blocked / lead-only | 88 | I4-C074, I5-C011, I5-C114, I9b-C054, I5-C029, I5-C030, I5-C031, I9b-C074, I3-C044, I3-C045, I4-C070, I4-C071 |
| discovery surface, 0 surveillance items | 58 | I5-C020, I5-C022, I5-C024, I5-C025, I5-C026, I5-C027, I5-C034, I5-C035, I5-C038, I5-C151, I5-C401, I5-C402 |
| derived single-item lead (acquire origin) | 34 | I3-C034, I3-C033, I9b-C008, I9b-C011, I9b-C014, I9b-C089, I9b-C091, I9b-C098, I4-C124, I9b-C010, I9b-C018, I9b-C038 |
| Part VIII block (metadata only) | 25 | I3-C031, I3-C032, I3-C036, I3-C037, I4-C059, I3-C085, I3-C086, I4-C015, I4-C277, I4-C060, I4-C169, I9b-C076 |
| captured terms prohibit | 16 | I6-C002, I9b-C036, I5-C008, I5-C300, I5-C301, I6-C001, I3-C047, I5-C217, I5-C400, I3-C062, I5-C012, I5-C302 |
| other (override) | 14 | I9b-C097, I5-C007, I4-C221, I5-C004, I9b-C012, I6-C011, I9b-C061, I4-C302, I9b-C039, I4-C301, I6-C012, I6-C013 |
| mirror (acquire origin) | 11 | I3-C071, I3-C035, I4-C003, I9b-C009, I3-C029, I5-C234, I4-C002, I4-C004, I4-C264, I5-C367, I6-C035 |
| low value (score < 10) | 6 | I4-C022, SRC-023, I4-C118, I4-C265, I4-C300, I4-C268 |
| duty lead (register per SIG-INGEST-050) | 5 | I9a-C050, I9a-C020, I9a-C037, I9a-C051, I9a-C032 |
| derived inventory (enumeration aid) | 2 | I9a-C023, I9a-C030 |

Part VIII blocks are recorded as metadata only; `design/I7-rights-packets.md` §3.8 lists them for a single confirmation line.
Duty leads (NM DPS agency reports from 2027-04-01; AL, AR, UT FR/UAS duties; MN HF 3198) should be registered with their
commencement dates under SIG-INGEST-050 — they are records leads, not feeds (SIG-INGEST-025a).

---

## 7. Coverage delta estimate

Cumulative, counting a geography or class as reached when at least one candidate in the tier evidences it (inference from the
`geographies`, `technology_classes`, `gap_ref` and `vendors` columns; Tier 3 is not acquired and adds nothing):

| reached | Tier 1 | + W | + Tier 2 |
|---|---|---|---|
| I1 blind spots (of 14) | 11 (not #3, #11, #12) | 12 (+ #11 via AU) | 13 (+ #12); #3 is internal attribution (I8) |
| tier-A states (of 10) | 6: AR, DE, ME, MI, VT, WV | 7: + NH | 8: + RI |
| tier-B (of 5) | 3: DC, HI, NM | 3 | 4: + ND |
| US states + DC (of 51) | 35 | 40 | 46 |
| territories | GU | + PR, VI (statute level only, via LAPPA) | PR and VI at origin (SUTRA, legvi.org) |
| tribal nations | — | — | Tohono O'odham (governance decision first) |
| thin large cities (GL1, of 36) | 7 | 13 | 25 |
| technology classes (T01–T29) | 25 | 28 | 29 |
| countries beyond the US | 0 | 1 (AU) | 18 |

**By tier, what closes:**
- **Tier 1** is mostly *origins* for the operator's first two targets and the tier-A DOT gap: 29 rows on I1#1 (FDOT, 14 agency
  Flock/LPR layers, WA AGO, MN BCA, NE and VT reports, Cook County, Haskell AR, Des Moines), 34 on I1#4 (statutory and CCOPS
  reporting in WA, MN, NE, VT, IL, VA, MD, ME, HI, PA, FL, CO, MO, OH, TX, CA, DE and AK), 10 on I1#5 (DOT/official camera
  layers in DE, VT, WV, MI, NC and CT, plus police CCTV layers in Denver, Seattle and Hyattsville), 19 on
  NEW-8 (ATE), 12 on I1#7 (forensics purchases, district student-monitoring pages, NY SMM bill), 14 on I1#8 (drones in ME/MN/IL,
  CSS in MD/CA, FRT in WA/CO/Detroit). Vendors newly evidenced at origin: Flock (18 rows), Motorola/Vigilant, Cellebrite, Gaggle,
  Lightspeed, Securly, Verra Mobility, LexisNexis, Thomson Reuters.
- **W** adds breadth cheaply: agenda evidence in 13 thin cities (Cleveland, Saint Paul, Madison, Nashville, Albuquerque,
  Charlotte, Newark, Winston-Salem, Detroit …), federal award evidence for the zero-channel classes and vendor names SIG cannot
  see today (I4 NEW-5; 92 distinct vendors cumulative), the national ALPR origin, and a current statute layer.
- **Tier 2** adds the international set (NL ANPR plan, UK LFR, Canada, EU regulators, AU/NZ), the private-camera programmes
  (under screen S1), procurement registers and checkbooks (TX DIR, DE, CT, NJ, SLFRF), the drone/UAS state censuses, the
  records and court routes (CourtListener bulk), and twelve more thin cities.

**What stays dark after Tier 2:**
- **States:** MS, WY, MT and KS have only Tier-3 evidence (access-blocked 511 feeds or leads); **SD has no candidate at all**.
  NH's DOT cameras stay behind keyed newengland511 (HG-09).
- **Territories and tribes:** American Samoa (no channel exists, I9b Q104) and the Northern Mariana Islands; every tribal nation
  but one; tribal-keyed geography awaits a governance decision (NEW-6).
- **Cities:** North Las Vegas (nothing found); Boise, Cape Coral, Chesapeake, Greensboro, Henderson, Indianapolis, Irvine,
  Norfolk, Plano and Wichita have Tier-3 evidence only.
- **Vendors and networks:** Flock's own customer, sharing and audit data at origin (portals refused; audit rows are Part VIII);
  Axon Fusus and Community Connect (Axon terms prohibit automated access); Motorola CommandCentral, Genetec Clearance and Polaris
  (403 or Part VIII); Rekor and ELSAG customer lists (vendor pointers only); EDGAR vendor disclosures (Q-30).
- **Classes:** T16 robotics has one Tier-2 lead; social-media monitoring and mobile forensics rise from zero to a handful of
  purchase records, not a census; face recognition beyond state reports stays thin.
- **Mobile ALPR and sharing currency (I1#10)** improves only through statutes, the UWCHR Border Patrol analysis and the VT/NE
  reports; per-agency sharing lists remain a records-release question.

---

## 8. Findings raised (`findings/incoming/I7.csv`, all `proposed`)

| id | sev | title (short) |
|---|---|---|
| NEW-1 | S2 | Two candidates recorded `new` are registry sources (NYC CROL = `procportal_nyc_ny`; Edmonton `7fnd-72gr` = `camreg_edmonton_ab`); dedupe must match dataset ids |
| NEW-2 | S2 | One operator statement ("is SIG's use commercial?", E4 R4d) now gates ≥ 5 sources: Honolulu PD, Canada.ca, OPC Canada, CNIL images, Bellevue |
| NEW-3 | S2 | Revocation / destroy-on-request terms (Chicago, Albuquerque, OpenFEMA) conflict with append-only claims; no withdrawal mechanism is specified |
| NEW-4 | S3 | Terms captures still owed for 6 refused hosts (incl. BidNet Direct for E4 R6a) and 5 JS/empty terms pages |
| NEW-5 | S2 | Agency ArcGIS layers carry no licence and rest on the owning account; 3 held at Tier 2 pending an owner-org check |
| NEW-6 | S2 | No rights/governance basis for tribal publishers or tribal-keyed geography; no territorial flip ever executed |
| NEW-7 | S3 | The frozen ALPR statute seed has no recorded refresh path despite SIG-INGEST-049f |
| NEW-8 | S3 | Free-text access status misleads mechanical feasibility scoring; a structured access field is proposed |

Seen, already raised elsewhere, not re-raised: TxDOT no-redistribution terms vs the flipped `camreg_txdot_rep_tx` (I5 NEW-3;
packets §4 C1); agenda-tenant label defects (I3 NEW-3, I5 NEW-1/2/4); the EDGAR contact-string need (I4 NEW-11, I9a NEW-4);
the stale state statute layer (I9a NEW-1); the ALPR removal wave (I9a NEW-2).

---

## 9. Open questions for I8 and the operator

1. **HG-03 batches** (`design/I7-rights-packets.md` §1): nine batch lines plus the individual lines.
2. **The commercial-use question** (NEW-2; E4 R4d) — one answer resolves Bellevue, Honolulu PD, Canada.ca, OPC and CNIL images.
3. **Withdrawal duties** (NEW-3): accept revocable terms with a tombstone-by-new-claim policy, or decline those sources?
4. **Tribal data governance** (NEW-6): who decides, and may SIG publish tribal-keyed facts at all before that?
5. **Q-30 contact string** — until approved, the four EDGAR rows stay Tier 2 and the EDGAR cells stay closed.
6. **ATE ontology** — 15 Tier-1 ATE rows wait on a concept (I1 NEW-8; I4 NEW-9).
7. **I8 sequencing proposal** (inference): W first (configuration only; no new rights decisions), then Tier-1 DOT and agency
   layers on `dot_511:arcgis_query`, then Tier-1 statutory reports on `dossier_documents`, then the Tier-2 connector families
   that unlock the most rows (Socrata SoQL aggregates, CKAN package search, cooperative contract documents, CivicPlus
   AgendaCenter).

---

## 10. Reproduction

From `docs/build/logs/next-phase/I7/` (gitignored):

```
python3 terms2.py          # terms_capture.json from raw/I7-F017..F078 (captures already on disk)
python3 overrides2.py      # overrides2.json (first-attempt overrides + I7 second-attempt judgements, each with a reason)
python3 consolidate2.py    # data/candidates_consolidated.csv + derived2.json
python3 gen_tables.py      # tables.json -> the tables in this note and in the packets
```

`fetch.sh FID URL PURPOSE` performs one plain GET (default curl user-agent, 30 s timeout, 1.2 s pause) and appends
`fid, run_at (date -u), status, sha256, bytes, url, purpose` to `fetch_index.tsv`. `mine/linkmine.py` reads only local raw
captures. Self-checks run on the outputs: 694 unique `i7_id`s; every `cand_id` of the six CSVs and the queue appears exactly once
in `cand_ids_merged`; no `proposed_source_id` collides with a registered id; every proposed row has
`proposed_ingestion_permitted = false`; no e-mail or IPv4 pattern in the committed files.
