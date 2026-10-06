# I6 — Cross-cutting evidence channels

Row **I6** of `META_PLAN.md` §6 (Stream I, Stage P). Owner class **R** (web research). Run 2026-09-30T17:59Z →
18:35Z (`date -u`) by Claude Code (Opus 5.5) in the planning worktree, branch `claude/next-phase-planning`.
It follows `design/I2-source-search-protocol.md` (the "protocol"). Outputs:

- this note;
- `data/candidates_I6.csv` (43 rows; §8.6 columns + the I2 §7.3 extension columns);
- `data/query_log_I6.csv` (135 lines: 41 queries, 4 local operations, 90 fetches);
- `findings/incoming/I6.csv` (NEW-1…NEW-4).

Raw captures, the fetch log and the scratch generators are under `docs/build/logs/next-phase/I6/` (gitignored).
Nothing else was written; nothing was committed.

**Row status: `in-progress`.** The shared session WebSearch cap (200 calls) ran out after 32 I6 searches
(findings NEW-2). After that, the row could use only documented APIs and direct fetches. Four P1 cells are not
saturated. I recommend re-running the predefined split **I6a** (C06, C08, C10, C11) in a fresh session with its own
search budget (§8, Q1).

Evidence classes follow P1. A claim cites a fetch id (`I6-F###`), a query id (`I6-Q###`) or a local operation
(`I6-L###`); all are listed in the query log. Search-engine summaries are labelled **lead (unfetched)**.

---

## 1. Summary

- **43 candidates**: 31 new to the registry, 8 `related:` and 4 `same-as:`. By level: 26 publisher, 14 channel,
  3 target. 11 rows are LEAD-ONLY because they are blocked, paid or a duty without a feed.
- **The strongest new channels are structured spending records that link a vendor to a named public buyer.**
  The registry has no state-level register of this kind today. Below the federal level it has only four city
  procurement portals and the agenda tenants (I1 §2.3).
  - **Treasury SLFRF project data** (I6-C025): 196,984 project rows. 271 of them name an LPR, Flock, an RTCC,
    ShotSpotter or Fusus. They come from 219 recipients in 38 states, including 7 of the 10 tier-A gap states.
  - **Texas DIR cooperative-contract sales** (I6-C007): 12.8M purchase lines, by customer, vendor and brand.
  - **Washington DES master-contract sales by customer** (I6-C010). Its customers include cities, counties and
    tribes.
  - **State checkbooks for Delaware and Connecticut** (I6-C008/C009). Both carry a Public Domain licence field.
    - Delaware shows state payments to Flock Group, Clearview AI, Cellebrite and LexisNexis Risk.
    - These payments are the first channel for the mobile-forensics class (FOR), which I1 lists as having none.
- **Statutory and ordinance reporting (I1 #4).** Five municipalities publish CCOPS-type reports and have no
  registry row: Madison WI, Detroit MI, St. Louis MO, Dayton OH and Columbia MO (I6-C014…C018).
  - Restore the Fourth publishes a **text** list of 20 ordinances with links to the primary texts (I6-C012).
    SIG-INGEST-049a says the national list exists only as an image.
  - The registry's "~26 jurisdictions" denominator is therefore stale (NEW-3).
- **State grant programmes that name the vendor per grantee.** Two were found:
  - Texas MVCPA (I6-C028): FY2026 lines such as "Flock Safety Automated License Plate Reading Cameras".
  - California BSCC Organized Retail Theft (I6-C029).
- **Courts.** CourtListener's **bulk data** carries "free of known copyright restrictions" plus the Public Domain
  Mark (I6-C038). That is a different route from the membership-API terms under which `courtlistener_recap` was
  refused, and the E4 R2b options do not consider it (NEW-1).
- **Closed or paywalled** (§7): GovSpend, Starbridge and CivicIQ (paid); Pavilion (challenge, and an account is
  needed); OMNIA contract documents (member-gated); MuckRock (Cloudflare 403); DocumentCloud (refused, E4 R2a);
  NCSL (403); the NJ OAG release (403). Sourcewell's and OMNIA's terms forbid robots.

---

## 2. Method and deviations

**Protocol followed.** The row ran only inside its own 23 cells (`search_matrix.csv`, row I6). It logged every
query with `cell=` and used a `date -u` stamp for each line (R2). It did metadata-first reads (R6), and computed
the registry and queue dedupe mechanically (§7.6, a grep over `sources.toml`, the target TOMLs,
`acquisition_queue.toml`, `source-candidates.csv` and `source_coverage.csv`). Terms were captured verbatim where a
page carried them.

**Inputs read:**
- META_PLAN §3 (P1–P15), Stream I, §8.2 and §8.6;
- the protocol in full;
- `research/I1-source-coverage.md` §1, §3, §4, §6 and §7;
- `data/source_coverage.csv`;
- six-streams `source-candidates.csv` (SRC-001…027);
- `design/E4-rights-packets.md` (R2a/R2b);
- `live_targets.toml` (usaspending);
- `procurement_vocab.toml [usaspending_sweep]`.

**Local operations** (not counted against the budget), all on the I1 Atlas capture `atlas.csv` (sha256 `dcbf8bc13d14`):
- **L001: partition size.** The I6 records-corpora partition is **5,017 links** (I2 counted 4,971 with a different
  unwrap). By technology: ALPR 1,781, FRT 1,287, BWC 924, INV 503, UAS 294.
- **L002: what is behind the MuckRock links.** The 969 MuckRock `/foi/` links span 147 jurisdiction slugs. The
  heaviest are statewide multi-agency releases:
  - "surveillance-technology-procured-by-va-law-enforcement-agencies": 114 Atlas rows;
  - Oregon "public-body-drone-registrations": 50;
  - Georgia "applications-to-install-license-plate-readers": 44;
  - "lacris-member-list-2024": 38.
- **L003: grant links across the whole Atlas.** This found the state grant lists the Atlas itself relies on: NJ OAG
  ALPR grants, TxDMV MVCPA, the Georgia governor's awards, PA PCCD, the Texas governor's JAG and HSGP lists, and
  CA BSCC.
- **L004: the most-cited records artefact in the whole Atlas.** It is a Flock "shared devices list" released by the
  Pittsboro PD and hosted on DocumentCloud: 1,197 Atlas rows in 33 states (I6-C032, out-of-cell for I3).

**Budget used:**
- **Queries.** 41 query lines: 32 WebSearch sent, 2 WebSearch **not sent** (the tool refused them), and 7
  documented-API queries (Socrata discovery ×3, EDGAR FTS, Federal Register ×2, OpenFEMA).
- **Fetches.** 90 of 200.
- **Stop reason.** The session WebSearch cap was reached at about 18:16Z (I6-Q033/Q034). R11 applies.

**Deviations from the protocol (disclosed):**

1. **Search cap.** WebSearch was unavailable after I6-Q032. The cells C04, C05, C07, C09, C12, C13, C14 and C16
   were then worked only through direct fetches of known or prior-knowledge URLs and documented APIs. Where a
   candidate was reached without a query (for example the CA statutes and the federal AI inventory), its notes say
   so. Those candidates were led by prior knowledge (inference) and confirmed by a live-read.
2. **Tooling.** Most fetches used `curl` (engine `curl` in the log), not WebFetch, so that raw bytes and a sha256
   could be stored. WebFetch was used twice (I6-F006/F007).
   - `federalregister-api` and `openfema-api` are documented public APIs that are not in the protocol §8 engine list.
   - A single honest user-agent (`SIG-planning-research/0.1`) was used throughout, with no UA switching. One retry
     sent an `Accept: text/html` header after a 406 (I6-F036); this is content negotiation, not a challenge bypass.
3. **MuckRock.** Two GETs were issued in the same batch before the first status (Cloudflare 403) was seen
   (I6-F062/F063). The host was stopped after that.
4. **Aggregates.** Four Socrata SoQL `count(*) … group by vendor` GETs were run (I6-F013/F052/F054/F056).
   - They return aggregates only. No rows were downloaded.
   - Person-name columns (Customer Contact, Vendor Contact, individual payees) were never selected.
5. **SLFRF workbook.** The Treasury SLFRF workbook (58.7 MB, I6-F045) was the candidate's one sample document (R6).
   - Keyword counts were computed locally over Project Name and Description.
   - The dataset holds government projects, with no person-level fields. No row text is committed.
6. **Atlas partition.** L003 mined grant-link patterns across the **whole** Atlas, not only the I6 records
   partition, because C10 is I6-owned for every class.
   - Four grant URLs fetched from that list sit in I3/I4 partition rows (NJ OAG, TX PSO, GA, PA PCCD).
   - None of them yielded bytes except the PCCD redirect.
7. **One candidate without a fetch line.** I6-C032 (the Pittsboro list) has only a local-operation line.
   DocumentCloud is refused for SIG (E4 R2a), so it was not fetched.
8. **Owner-row overlap.** The brief's named NGO and journalism sources partly belong to other rows under I2
   §5.7: Georgetown CPT, Bard, Brennan, The Markup and CDT are I4's snowball sources; 404 Media, NAMSDL and NCSL
   ALPR are I3's. I6 captured only their multi-class or legislation-channel aspects:
   - LAPPA (formerly NAMSDL) as a publisher, with a non-ALPR negative;
   - NCSL (blocked);
   - S.T.O.P., Lucy Parsons Labs and Surveillance Watch.

**One lesson for P15 (not a SIG defect).** The I6-Q023 search summary stated Colorado's "SAFE Act … requires" as if
it were law. The fetched origin (I6-F036) shows SB26-071 was **postponed indefinitely on 2026-05-06**. Snippets stay
leads.

---

## 3. Cell coverage table

"New" is computed mechanically from the query log (`new=` summed per cell). A candidate first found in C06-G0 counts
as new there, not in C06-GP.

| Cell | Tier | Queries (sent) | Fetches | New | Cands | Closing status |
|---|---|---|---|---|---|---|
| I6-T00-C06-GP | P1 enum | 7 | 10 | 3 | 7 | `enumerated(6 found / 3 negative / 1 blocked / ≥14 not-reached)`, capped by the search cap. Found: Madison, Detroit, St. Louis, Dayton, Columbia MO, and the MA list via ACLUM. Negative: Palo Alto (no annual report located), New Orleans (2020 ordinance is a ban; reporting was stripped, lead), Yellow Springs (reports not located). Blocked: Syracuse (403). Not reached: the Medford/Lawrence/Northampton reports, Urbana, Sebastopol, BART (SRC-018), Santa Clara Co. (SRC-021), San Diego (SRC-003), and currency checks of the 6 gated plus SF registry rows. |
| I6-T00-C08-G0 | P1 sweep | 8 | 15 | 4 | 6 | `saturated` mechanically (the last K=3 yielded 0 new). Caveat: no HGACBuy, BuyBoard, TIPS, Equalis or GSA eLibrary contract page was reached. The web results for them were news and agenda pages only (I6-Q006/Q008). |
| I6-T00-C06-G0 | P1 sweep | 4 | 3 | 5 | 2 | `capped-unsaturated`: new per query 1, 4, 0, 0; K=3 zeros not reached. |
| I6-T00-C11-GS | P1 enum | 3 | 11 | 4 | 4 | `capped-unsaturated` (3 < q_min 4). Inventory-first results: LAPPA is ALPR-only (negative for FR, UAS, CSS); GHSA and IIHS cover ATE; NCSL is blocked; SIA's FRT guide and CDT's tracker are leads, not fetched; S.T.O.P. covers NY. |
| I6-T00-C08-GS | P2 enum | 3 (+2 not sent) | 13 | 4 | 4 | `enumerated(4 found TX/DE/CT/WA / 0 negative / 47 not-reached)`. OH was attempted but not sent. Leads not fetched: OR, NY OGS. |
| I6-T00-C10-G0 | P2 sweep | 6 | 12 | 3 | 3 | `saturated` (K=2 met at I6-Q027), then `extended` by 2 probes; OpenFEMA yielded a `related:` row. |
| I6-T00-C10-GS | P2 enum | 4 | 8 | 3 | 3 | `enumerated(2 found TX-MVCPA/CA-BSCC / 1 negative PA-PCCD (moved) / 3 blocked NJ, TX-PSO, GA / 1 not-reached OH / 44 not-reached)`. |
| I6-T00-C11-G0 | P2 sweep | 2 | 0 | 1 | 1 | `capped-unsaturated` (new per query 0, 1). |
| I6-T00-C13-G0 | P2 sweep | 0 | 2 | 0 | 2 | `blocked(access)` for MuckRock (403) and DocumentCloud (refused). Local ops L001/L002/L004 done. NextRequest, GovQA and federal reading rooms: `not-started(search cap)`. |
| I6-T00-C14-G0 | P2 sweep | 0 | 5 | 0 | 3 | `not-started(search cap)`. Only direct probes of I6 snowball sources (S.T.O.P., LPL, Surveillance Watch). EFF SLS, EPIC, Oakland Privacy and the NYU Policing Project were not reached. |
| I6-T00-C16-G0 | P2 sweep | 0 | 2 | 0 | 2 | `not-started(search cap)`. Direct: AI inventory, LEMAS. DHS PIA index and DLA LESO (SRC-024) not reached. |
| I6-T00-C04-G0 | P2 sweep | 0 | 0 | 0 | 0 | `not-started(search cap)` |
| I6-T00-C04-GS | P2 enum | 0 | 2 | 0 | 1 | `enumerated(1 found VA / 1 negative MN landing / 49 not-reached)` |
| I6-T00-C07-G0 | P2 sweep | 0 | 0 | 0 | 0 | `not-started(search cap)`. The registry already enumerates 793 tenants. |
| I6-T00-C09-G0 | P2 sweep | 0 | 0 | 0 | 0 | `not-started(search cap)`. The city checkbooks surfaced by I6-Q035 (LA, Atlanta, Baton Rouge, Mesquite, Mesa, KCMO, College Station, Denver) are place-anchored: out-of-cell→I5. |
| I6-T00-C12-G0 | P3 sweep | 0 | 1 | 0 | 1 | `not-started(search cap)`. CourtListener bulk terms captured. |
| I6-T00-C12-GS | P3 enum | 0 | 4 | 0 | 1 | `enumerated(0 states / CAP bulk only)` |
| I6-T00-C03-G0 | P3 sweep | 1 | 0 | 0 | 0 | `saturated` (1 probe, 0 new: all public-health false positives) |
| I6-T00-C05-GS | P3 enum | 0 | 2 | 0 | 2 | `enumerated(1 found CA / 50 not-reached)`. Inference-led. |
| I6-T00-C05-G0 | P3 sweep | 0 | 0 | 0 | 0 | `not-started(search cap)` |
| I6-T00-C02-G0 | P3 residual | 1 | 0 | 1 | 1 | The probe yielded, so this becomes a P3 sweep, `capped` at 1 by the search cap. |
| I6-T00-C01-G0 | P3 residual | 0 | 0 | 0 | 0 | `not-started(search cap)` |
| I6-T00-C15-G0 | P3 residual | 0 | 0 | 0 | 0 | `not-started(search cap)`. The registry's OSM layers already cover `man_made=surveillance`. |

**Saturation of the P1 cells.** Only C08-G0 is mechanically saturated. C06-G0, C06-GP and C11-GS are not.

---

## 4. Candidates by channel, class and geography

**By channel:**

| Channel (cell) | New | Known (`same-as`/`related`) | Candidate ids |
|---|---|---|---|
| Cooperatives and aggregators (C08-G0) | 2 (Pavilion, Starbridge) | 4 (Sourcewell, OMNIA, NASPO, GovSpend) | C001–C006 |
| State contract registers and checkbooks (C08-GS) | 4 | 0 | C007–C010 |
| CCOPS national lists (C06-G0) | 1 | 1 (ACLU) | C011, C012 |
| CCOPS per-jurisdiction (C06-GP) | 7 | 0 | C013–C019 |
| State legislation inventories (C11-GS) | 3 | 1 (NCSL) | C020–C022, C033 (IIHS, found via GHSA) |
| Federal legislation (C11-G0) | 1 | 0 | C024 |
| Federal grants (C10-G0) | 1 (SLFRF) | 2 (OJP, OpenFEMA) | C025–C027 |
| State grants (C10-GS) | 3 | 0 | C028–C030 |
| Records corpora (C13-G0) | 0 | 2 (MuckRock; Pittsboro via DocumentCloud) | C031, C032 |
| NGO / civil data (C14-G0) | 2 | 1 (S.T.O.P. → openstates) | C023, C034, C035 |
| Federal regulatory and statistical (C16-G0) | 2 | 0 | C036, C037 |
| Courts (C12) | 1 (CAP) | 1 (CourtListener bulk) | C038, C039 |
| Statutory reports (C04-GS) | 1 | 0 | C040 |
| Policy and programme duties (C05-GS) | 2 | 0 | C041, C042 |
| Vendor disclosures (C02) | 1 | 0 | C043 |

**Other counts:**
- **Publisher type:** procurement 7, ngo 7, ccops-report 6, legislation 6, grant 6, other 4, statutory-report 3,
  records-release 2, court 2.
- **Format:** html 16, other 8, pdf 7, socrata 4, api 4, bulk-file 4.
- **Geography:** US national 23; state or place 19 (CA 3, TX 2, MO 2, NY 2, and 1 each for DE, CT, WA, MA, WI, MI,
  OH, NJ, IL, VA); US-TRIBAL 1 (OpenFEMA Tribal HSGP); INTL 1 (Surveillance Watch).
- **Technology classes:** T00 on 34 rows. The class tags that follow from vendor or keyword evidence are
  T01 13, T05 8, T23 8, T07 6, T14 6, T11 5, T29 3, T13 3, T02 3, T09 2, T19 2 and T17 2. SMM (T20) and school
  suites (T25) have no I6 evidence beyond the AI inventory (T20).

**Back-chaining ids recorded for I3/I4 (unverified unless fetched):**
- `contract_ids`: 101223-AXN (fetched); 010720-WCH, R250203 and T21-119-01 (leads); WA 05720, 02315, 06316, 04220,
  06913, 00318 and 02702 (from the WA aggregate).
- `award_ids`: 15PBJA-24-GG-05307-JAGX and 15PBJA-24-GG-04969-JAGX (leads); the MVCPA FY2026 grant numbers
  608-26-… (fetched PDF).

---

## 5. Movement against the I1 blind spots

| I1 # | Blind spot | What I6 adds (candidate → evidence) |
|---|---|---|
| 1 | Flock at origin and at scale | Buyer-side evidence independent of the refused portals: SLFRF 98 "Flock" projects (C025); MVCPA grants that name Flock per city (C028); BSCC ORT summaries with 7 Flock mentions (C029); Delaware state payments to Flock Group (C008); a DIR Flock sale (C007); the OMNIA supplier page (C002). Pointer: the Pittsboro Flock shared-devices list, 1,197 Atlas rows (C032, → I3). |
| 2 | Axon/Fusus, RTCC | Sourcewell 101223-AXN, whose page attaches a Fusus appendix (C001); WA DES Axon contracts by customer (C010); CT/DE Axon payments (C008/C009); SLFRF Axon 81 and Fusus 5 (C025); Axon 10-K RTCC language (C043, a vendor assertion). |
| 4 | Statutory and ordinance reporting | 5 new CCOPS publishers (C014–C018), the RT4 20-ordinance text list (C012), the ACLUM MA list (C013); the VA report deposit (C040); CA PC 13650 and Gov. Code 7070–7075 duties (C041/C042); ATE statute inventories (C021, C033). |
| 6 | Procurement | Three cooperative publishers (C001/C002/C004); two state vendor→customer sales registers (C007, C010); two state checkbooks (C008/C009); five grant channels (C025–C029). |
| 7 | Zero-channel classes | **FOR:** Cellebrite payments in the DE (Safety & Homeland Security, Legal, Corrections) and CT (DESPP, Corrections) checkbooks. **ATE (T09):** IIHS lists 358 red-light communities (C033); GHSA state law (C021). SMM and SCH: nothing new. |
| 8 | UAS / GSD / FRT / CSS | SLFRF drone 149 and ShotSpotter/gunshot 21 (C025); a Detroit cell-site simulator STSR (C015); Delaware payments to Clearview AI (C008); the CA AB 481 drone and robot reports duty (C042). |
| 9 | Thin cities | Detroit (GL1, 0.52) via CIOGS (C015). A Winston-Salem JAG award for LPRs is a lead only (unverified). |
| 10 | Mobile ALPR and sharing | NASPO Category 3 ALPR, with Axon Fleet on Sourcewell (C004/C001). The sharing lists (C032) go to I3. |
| 12 | Records and courts | CourtListener bulk under a Public Domain Mark (C038); CAP (C039); MuckRock remains blocked (C031). |
| 13 | Data brokers | Delaware LexisNexis Risk payments across departments (C008); AI inventory (C036). |
| 14 | Territories and tribal | OpenFEMA Tribal HSGP recipients: 229 of the first 1,000 filtered rows (C027); WA DES sales to tribes (C010). |

**Tier-A states given a new channel:**
- DE: checkbook C008 and SLFRF;
- MI: Detroit C015 and SLFRF (6);
- AR 3, NH 4, MS 1, WV 1, WY 1: SLFRF keyword matches (C025).

---

## 6. Ranked shortlist (value × feasibility × rights)

The ranking is a planning judgement (inference). It is not `acq-score/1`, which I7 assigns. **Value** is how many
named gaps and independent institutions a source covers. **Feasibility** is its access mode and whether a SIG
connector can be reused. **Rights** is the guessed lane, which is never decided.

| Rank | Candidate | Value | Feasibility | Rights (guess) | Gap it closes |
|---|---|---|---|---|---|
| 1 | **I6-C025 Treasury SLFRF project data** | 271 surveillance projects, 219 recipients, 38 states, multi-class, vendor-named | one quarterly xlsx; one new parser | federal work, likely-open; free-text screen | I1 #6, #1, #8; tier-A AR/DE/MI/MS/NH/WV/WY |
| 2 | **I6-C007 Texas DIR vendor sales** | PO-level vendor→public-customer for every DIR buyer (cities, counties, ISDs) | Socrata; `socrata_rows` reuse; monthly | no licence field: undetermined | I1 #6, #1 (TX) |
| 3 | **I6-C008 / C009 DE and CT checkbooks** | state-agency payments to Flock, Clearview, Cellebrite, Axon, Motorola, LexisNexis | Socrata aggregates by vendor | "Public Domain" licence field | I1 #7 (FOR), #13, #6; DE tier-A |
| 4 | **I6-C010 WA DES master-contract sales by customer** | vendor→customer incl. cities, counties, tribes; bridges NASPO PA 05720 | Socrata; quarterly | no licence field | I1 #6, #14 |
| 5 | **CCOPS new publishers I6-C014–C018** (Madison, Detroit, St. Louis, Dayton, Columbia MO) + **C012** list | per-technology inventories, sharing and usage counts, by ordinance | PDF/HTML; `government_mandated_disclosure` reuse; annual | the municipal-mandated-disclosure precedent (ADR-085 derived facts) | I1 #4; Detroit GL1; MI tier-A |
| 6 | **I6-C028 TxDMV MVCPA grant listing** | per-grantee programme names that name Flock and ALPR | PDF; annual; `dossier_documents` | state work, undetermined | I1 #1, #6 (TX) |
| 7 | **I6-C029 CA BSCC ORT** | ~55 grantee narratives (ALPR, drones, RTCC) | PDFs; quarterly and annual | state work, undetermined | I1 #1, #6, #8 (CA) |
| 8 | **I6-C038 CourtListener bulk** | evidence-of-use lane across opinions and dockets | large offline filter; new connector | Public Domain Mark (bytes likely-open); party names mean metadata only | I1 #12 |
| 9 | **I6-C033 IIHS red-light (and speed) communities** | the only community-level list for a class with no ontology concept | one HTML table; monthly | © IIHS; facts likely-open | I1 #7; NEW-8 (T09) |
| 10 | **I6-C036 Federal AI Use Case Inventory** | annual machine-readable CSV of federal FR, LPR and SMM uses | bulk CSV; annual | federal work, likely-open | I1 #8, #13 |

**Also useful:**
- C004 NASPO (the list of 31 participating-addendum states; eligibility, not purchase);
- C041/C042 CA statutes (statewide duty leads);
- C027 OpenFEMA (a tribal channel);
- C001 Sourcewell (master-contract ids only; its terms forbid robots).

---

## 7. Closed, paywalled and inaccessible channels

**Terms recorded verbatim where fetched:**

| Channel | Status | Terms / evidence |
|---|---|---|
| Sourcewell (C001) | open HTML; terms restrictive | "You may not reproduce, distribute, modify, create derivative works from, publicly display, publicly perform, republish, download, store, or transmit any material from the Digital Assets except as permitted below" and a prohibited use: "Use automated tools such as robots or spiders to access or copy content." (I6-F008). Use it as a pointer for master-contract ids only. |
| OMNIA Partners (C002) | supplier page open; contract documents member-gated | "you shall not: (a) use any robot, spider, or other automatic or manual device or process for the purpose of “scraping,” “crawling,” harvesting, or compiling information on the Site for purposes other than for a generally available search engine" (I6-F075). |
| NASPO ValuePoint (C004) | open | "All contents of the www.naspo.org Web Site are: Copyright National Association of State Procurement Officers and/or its suppliers. All rights reserved" (I6-F076). |
| Pavilion (C003) | **closed**: 405 "Human Verification"; an account is needed | NONE-FOUND |
| GovSpend (C005) | **paid**; TLS reset to a plain GET | NONE-FOUND; the registry already says "paywalled — LINK" |
| Starbridge (C006), CivicIQ | **paid** sales-intelligence platforms | Starbridge terms path 404 (I6-F078); CivicIQ not fetched |
| MuckRock (C031) | **blocked**: Cloudflare 403, even on robots.txt | ToS verbatim in E4 (the "data mining, robots … excluded" clause) |
| DocumentCloud (C032) | **refused** (E4 R2a) | not fetched |
| CourtListener API | **refused/deferred** (membership terms, E4 R2b) | the bulk route (C038) is separate: "free of known copyright restrictions" |
| NCSL (C022) | **blocked** (403) | none |
| OJP award detail pages (C026) | redirect to `/user/login` for SIG's UA | the dashboards are Tableau |
| PACER, LegiScan, ICPSR, GSA eBuy | excluded by protocol (paid, or account / API key = operator action) | not fetched |

**INACCESSIBLE list (host, status, time; no retry past a challenge):**

| Host | Status | Time (UTC) | Fetch |
|---|---|---|---|
| withpavilion.com | 405 challenge | 18:01:49 | F003 |
| data.texas.gov (archive SoQL aggregate) | timeout 40 s (the FY26 aggregate worked) | 18:03:25 | F012 |
| syr.gov | 403 | 18:07:09 | F019 |
| ecode360.com | 403 | 18:08:05 | F025 |
| www.ncsl.org | 403 | 18:09:50 | F035 |
| leg.colorado.gov | 406, then 200 with `Accept: text/html` | 18:09:50 | F034/F036 |
| catalog.data.gov CKAN API | 404 on package_show/package_search | 18:11:12 / 18:11:16 | F038/F039 |
| bja.ojp.gov award page | 302 → /user/login | 18:11:21 | F040 |
| www.muckrock.com | 403 Cloudflare | 18:19:03 | F062/F063 |
| govspend.com | TLS SSL_ERROR_SYSCALL | 18:21:12 | F077 |
| gov.texas.gov | TLS SSL_ERROR_SYSCALL | 18:22:42 | F084 |
| www.njoag.gov | 403 | 18:22:58 | F085 |
| gov.georgia.gov | DNS failure | 18:23:02 | F086 |
| medfordma.portal.civicclerk.com | JS shell (1.3 KB) | 18:24:13 | F088 |
| codelibrary.amlegal.com | 403 | 18:24:14 | F089 |
| surveillancewatch.io; case.law | JS-only apps | 18:19:31; 18:18:33 | F064; F058/F059 |
| files.sourcewell.org PDF | glyph-encoded text (not extractable) | 18:02:10 | F004/F006 |

---

## 8. Part VIII log (counts only, no content)

**Flags across 43 candidates:**
- none-observed 30;
- private-person-name 11: contact columns, individual payees, uploader or requester names, docket parties;
- free-text-narrative 4: SLFRF descriptions, CT payment descriptions, MuckRock, LPL;
- per-search-audit 1 (MuckRock released files).

**Verdicts:** pass 30, flag 13, **block 0**.

**No committed file contains** a plate, an operator id, an officer name from audit data, a search reason, a student
datum or a private address. Specifically:
- The Socrata aggregates never selected the Customer Contact, Vendor Contact or payee-person columns.
- The SLFRF keyword counts are aggregates only.
- The Pittsboro list was not opened.
- Staff contact names seen on Sourcewell and IIHS pages were not copied.

**Hazards for I7/I8:**
- **Checkbooks:** individual payees → a vendor allow-list at extraction.
- **DIR:** contact columns → drop them.
- **SLFRF:** free text → a pre-publication screen (SIG-PUB-014a).
- **CourtListener:** party names → metadata-level only.
- **Tribal rows** (OpenFEMA, WA DES) → the tribal-sovereignty publication note.
- **ATE (IIHS):** community-level programme facts only. Violation data is plate-level and blocked.

---

## 9. Open questions for I7 and the operator

1. **Re-run I6a.** C06, C08, C10 and C11 should be re-run in a fresh session with its own WebSearch budget
   (NEW-2). The same cap likely truncated I3–I5; check their logs.
2. **Portals with no licence field.** Texas DIR (C007) and WA DES (C010) have none. Delaware and Connecticut
   assert "Public Domain" in Socrata. ADR-130 says municipal publication is not CC0. Which lane applies?
3. **Cooperative terms.** Sourcewell and OMNIA forbid robots and reproduction. Should they be used only as
   master-contract-id pointers, with ingestion from agency-side records (checkbooks, agendas, state sales
   registers)?
4. **CourtListener bulk.** Does the bulk route (C038) reopen D-SOURCES.2-2 (R2b) under a new per-source basis
   (NEW-1)?
5. **Accounts.** An operator must decide on ICPSR (LEMAS), a free Pavilion account, OMNIA membership (contract
   documents) and a LegiScan key. Agents may not create them (R3).
6. **The Pittsboro/JCSO Flock sharing lists** (C032) go to I3-T03-C13. The origin agencies' releases should be
   sought outside DocumentCloud.
7. **Semantic guards.** An SLFRF project is funding, not a verified deployment. A NASPO participating addendum is
   eligibility, not a purchase. A grant award is not spending. I8 should model these as distinct claim types.

---

## Appendix — reproduction

- **Queries and fetches:** `data/query_log_I6.csv`. Raw bytes are at `docs/build/logs/next-phase/I6/raw/<id>.bin`,
  addressed by the sha256 prefix in each fetch line.
- **SoQL aggregates** (all `GET`, no key):
  - `data.texas.gov/resource/a743-wj72.json?$select=vendor_name,count(*),sum(purchase_amount)&$where=upper(vendor_name) like '%…%'&$group=vendor_name`
  - Delaware `7bip-nb4g` and CT `ajdm-rvz7`, grouped by vendor and department;
  - WA `n8q6-4twj`, grouped by vendor_name, contract_number and customer_type.
- **SLFRF counts:** the "Projects (Q1 2026)" sheet of the April-2026 workbook (sha256 `64cff7a4e0b5`).
  - The patterns were matched case-insensitively over Project Name + Project Description:
    `license plate|\bLPR\b|\bALPR\b`, `\bflock\b`, `real[- ]time crime`, `shotspotter|gunshot detection|soundthinking`,
    `\bdrones?\b|\bUAS\b`, `camera`, `\baxon\b`, `fusus`, `facial recognition`, `body[- ]worn|body cam`.
  - Combined set: LPR|Flock|RTCC|ShotSpotter|Fusus. Recipients are counted by Recipient-ID and states by
    State/Territory.
- **Atlas local operations:** see the L001–L004 lines. The scripts are regex over `Link n` and `Other Links`, with
  `web.archive.org` prefixes unwrapped.
- **Dedupe:** a host grep, per §7.6, over `sources.toml`, `camera_registry_targets.toml`, `dot_511_targets.toml`,
  `live_targets.toml`, `agenda_tenants.toml`, `procurement_portal_tenants.toml`, `acquisition_queue.toml`,
  six-streams `source-candidates.csv` and `source_coverage.csv`. Hits: sourcewell, omnia, naspo, govspend, aclu
  (CCOPS), ncsl, courtlistener/free.law, muckrock, documentcloud, and `detroitmi` (eScribe agenda tenant only).

**Self-check (I2 §9):**
- 43 unique `cand_id`s. **Pass.**
- Every query line has a `cell=` from I6's 23 cells. **Pass.**
- `rights_lane` never says `decided`. **Pass.**
- Every date came from `date -u` or a tool stamp. **Pass.**
- No Part VIII content is committed. **Pass.**
- `registry_match` was computed per §7.6. **Pass.**
- **Exceptions:**
  - I6-C032 has a local-operation line, not a fetch line (deviation 7).
  - The P1 cells C06-G0, C06-GP and C11-GS, and the P2 cells C04-G0, C07-G0, C09-G0, C13-G0, C14-G0 and C16-G0, are
    below `q_min` or unsaturated, with honest statuses (§3).
