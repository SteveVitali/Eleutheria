# I4 — Other technology classes (deep web research)

Row **I4** of `META_PLAN.md` §6, Stream I (owner class R, web research), executed under the I2 protocol
(`design/I2-source-search-protocol.md`). Run window 2026-09-30T17:58:43Z → 18:44:06Z (`date -u`), worktree
`claude/next-phase-planning` at `07657ccb`, by Claude Code (Opus 5.5). Outputs written:
- this note;
- `data/candidates_I4.csv` (189 rows; §8.6 columns + the I2 §7.3 extension columns + `value_note`);
- `data/query_log_I4.csv` (474 lines);
- `findings/incoming/I4.csv` (NEW-1 … NEW-12).

Scratch lives under `docs/build/logs/next-phase/I4/` (gitignored). Nothing was committed and no other file was
edited.

Evidence ids: `I4-F###` is a fetch, `I4-Q###` a query (for API queries the JSON response itself was read), and
`I4-L###` a local read. Every fact below cites one of them. Search snippets are never cited as evidence.
Vendor statements are reported as "the vendor states".

---

## 0. Summary

**Budget.**

| Item | Used | Cap | Notes |
|---|---|---|---|
| Query ids | 170 | 170 | 162 executed. 8 were refused because the session's shared WebSearch quota ran out (NEW-10). |
| Fetches | 240 | 250 | |
| Local reads | 62 | — | |

**Candidates.** 189 in total.
- By registry match: **124 `new`**, 62 `related:` and 3 `same-as:`.
- 40 are LEAD-ONLY: blocked, login-walled, or a statutory duty with no publication found.
- By level: 68 channel, 47 publisher, 11 family, 63 target.
- By Part VIII verdict: 108 pass, 70 flag, **11 block**. The blocked rows are recorded as metadata only.

**Headline.** Three kinds of source matter most.

1. **Reconfiguring connectors SIG already runs gives the largest, cheapest gains.**
   - *USAspending.* Two changes to the `usaspending` connector would open:
     - both zero-channel classes it can see: mobile forensics (3,538 contracts on four vendor terms, I4-Q170) and
       social-media monitoring (1,899 contracts, I4-Q080);
     - the named local buyers behind them, through sub-awards;
     - data brokers, BWC grants, weapons screening, counter-UAS, and vendor-named FR/CSS awards.
     The two changes are vendor and class keywords plus one Assistance Listing filter.
   - *Agenda vocabulary.* The same kind of change to the agenda content vocabulary would surface forensics, SMM,
     ATE, video-analytics and biometric approvals. These sit on roughly 306 Legistar tenants SIG already
     enumerates (NEW-5, NEW-6).
2. **Statutory state reports and structured federal files give recurring, jurisdiction-keyed census data.**
   - State drone reports: IL, MN, CA AB 481 (drones *and* robots), VT.
   - State FR regimes: MD, CO. Detroit's weekly FR report.
   - ATE reports: the WA statewide report (416 cameras), plus the MD, NY, VA, OR and RI report duties.
   - The ICE 287(g) roster: 2,608 agencies in one XLSX.
   - The US Courts wiretap tables.
   - The federal AI use-case inventories and the DHS privacy-document indexes.
3. **One new public-private channel: drone-as-first-responder flight-transparency dashboards.**
   - An aggregator counts Skydio 102, AirData 20, CAPE 5 and SFPD 1 agencies. Flock Aerodome's 68 belong to I3.
   - This is the drone analogue of the Flock portals and carries the same Part VIII address risk.

**Saturation is honest but incomplete.**
- The session's WebSearch quota of 200 calls, shared with the concurrent rows, ran out at 18:14:50Z. I4 had used
  76 of them by then, so every later I4 query was a documented-API query.
- 49 of 74 cells closed `capped-unsaturated`. 6 enumerations are partial. 2 cells are `blocked(access)` and 2 are
  `not-started(budget)`.
- Of the 15 `saturated` cells, only **3 are substantively saturated** (T11-C05, T11-C09, TRES-C01). The other 12
  closed after narrow API-only probes (marked †).
- The predefined **I4b split** (T19–T28 and residuals), with a fresh search quota, is recommended. See §9.

**Negative findings** (§5) are a result in their own right. No public deployment dataset exists for:
- gunshot-sensor locations (secret by design; the only source is a refused leak);
- current cell-site-simulator possession (the ACLU map is frozen at 2018-12-14);
- mobile-forensics or SMM agency lists (the NGO lists derive from the paid GovSpend and are unpublished or date
  from 2016);
- broker customers (Fog, Venntel);
- school monitoring. School monitoring exists only as district-level agreements; board platforms block
  automation, and federal awards are not a channel.

---

## 1. Method, and deviations from the I2 protocol

**Scope.**
- The row covers the 74 I4 cells of `data/search_matrix.csv` (5 P1, 28 P2, 41 P3; Σ q_min 117), for classes
  T09–T28 in the US (I2 §10 brief).
- Flock products (T29), all ALPR including commercial and private-operator plate data (T04; I2 boundary rule 4),
  and Axon Fleet/Fusus belong to **I3**. They were captured only incidentally and tagged `out-of-cell→`.
- CCOPS reports, cooperatives and generic records-corpus searches belong to I6.

**Execution.** The integrator (this row) dispatched the cells to 7 fresh-context batches in parallel. The batches
follow I2's predefined split lines; I4a is batches A–C and I4b is D–G.

| Batch | Classes | Queries | Fetches | Candidates |
|---|---|---|---|---|
| A | T14/T15/T16 | 25 | 35 | 29 |
| B | T09/T10/T12/T13/T18 | 25 | 35 | 42 |
| C | T11/T17 | 25 | 35 | 25 |
| D | T19/T20 | 33 | 28 | 22 |
| E | T25/T26/T24 | 27 | 35 | 22 |
| F | T21/T22/T23/T27/T28 | 20 | 35 | 29 |
| G | 11 residual cells | 13 | 20 | 23 |

- Each batch had a reserved id block (queries, fetches, candidates and local ops) and per-host fetch caps.
- All batches shared one brief (scratch `BRIEF.md`) restating I2 R1–R11, §5.4, §6 and §7.
- The integrator then:
  - merged the batches and applied the §7.6 dedupe (3 within-row merges);
  - redacted staff account identifiers;
  - corrected claims against the repository;
  - independently spot-checked 7 top claims (I4-F252–F257, I4-Q169/Q170). **All confirmed** (§4).
- Candidate ids therefore have gaps between blocks. I4-C306, C314 and C303 were merged into C084, C091 and C020.

**Deviations, all disclosed.**

1. **Output filename.** This note is `research/I4-other-technologies.md`, as the dispatch instruction required. I2
   §9 named it `I4-technology-classes.md`.
2. **WebSearch quota (NEW-10).** The tool enforces 200 WebSearch calls per session. The quota ran out at 18:14:50Z,
   while I4 had used 76 (the last one ran at 18:14:45Z).
   - Eight query ids were refused and are logged as not performed: I4-Q013, Q048, Q065, Q093, Q125–Q127 and Q147.
   - Later queries used documented APIs only: USAspending 21, Socrata discovery 20, Legistar 18, ArcGIS Hub 6,
     EDGAR FTS 6, Federal Register 4, CKAN 1, and API GETs via curl 5.
   - This biases late cells toward API-reachable channels.
3. **Integrator brief error.** The brief said the `usaspending` keyword list was only `live_targets.toml:55` (10
   terms). Batch C found the second list, `procurement_vocab.toml [usaspending_sweep]` (19 terms; I4-L009).
   - Every "keyword gap" candidate was re-checked and annotated at integration (C024, C090, C150, C152, C216,
     C250, C258).
   - The gap is real but narrower than the brief implied: **vendor names** plus the forensics, SMM, ATE, weapons,
     electronic-monitoring and biometric classes (NEW-5).
4. **Fetch hashing.** WebFetch returns a summary, not bytes, so its lines carry `sha256=n/a(webfetch)`. curl
   fetches carry the first 12 hex digits of the sha256.
5. **Registry and product checks.** The integrator made 11 fetches of registered-source URLs and of the public read
   API (I4-F241–F251). These answer §8.2 defect questions rather than search a cell, so they are logged
   `cell=integrator-QA(… no cell)`.
6. **Timestamps.** Local reads that were first run unstamped were re-executed and re-stamped with `date -u`; the
   log notes say so. Batch G stamped its local reads with the latest preceding `date -u`. Four WebFetch
   spot-checks (F253–F257) carry the batch `date -u` taken immediately before them.
7. **Conduct.**
   - The retries the batches report were network errors, not 403s: a TX socket error was retried once (A).
   - ilga.gov answered 403 to non-browser clients. Its own 403 page points automated clients to `ftp.ilga.gov`,
     which batch E used as the origin-offered channel. This is a judgement call against R4, recorded here.
   - Legistar received 5 API queries in batch F, against a nominal per-host cap of 4 (API queries, not fetches).
   - **One privacy incident (NEW-11).** Batch A sent the operator's e-mail address as the SEC EDGAR contact
     User-Agent without permission. It is in no file (grep at 18:42:51Z).
8. **Operator hook Q-20** (places, vendors or technologies to prioritise) had not been applied to I4 when the row
   ran. The I2 order held: zero-channel classes and ATE first; then UAS, GSD, FRT and CSS; then DATA and INV; then
   the probes.

---

## 2. Cell coverage table (74 cells)

Columns:
- **Queries (not run):** query ids logged under the cell; the number of refused ids is in brackets.
- **New:** the batch-reported `new=` sum.
- **Cands:** candidate rows whose `cell_id` is this cell.

Status markers: † = closed `saturated` after API-only probes (one Legistar tenant, EDGAR, USAspending or the
Federal Register) after the WebSearch quota ran out. That is mechanical saturation of a narrow channel, not of the
cell.

Totals: 170 query ids, 223 batch fetches plus 17 integrator fetches.

Statuses: 49 capped-unsaturated, 6 enumerated (partial), 15 saturated (12 of them †), 2 blocked(access),
2 not-started(budget).

| Cell | Tier | Batch | Queries (not run) | Fetches | New | Cands | Closing status |
|---|---|---|---|---|---|---|---|
| `I4-T25-C07-G0` | P1 | E_sch | 7 | 5 | 5 | 5 | capped-unsaturated |
| `I4-T19-C09-G0` | P1 | D_for_smm | 10 | 11 | 9 | 9 | capped-unsaturated |
| `I4-T20-C09-G0` | P1 | D_for_smm | 3 | 0 | 0 | 0 | capped-unsaturated |
| `I4-T25-C09-G0` | P1 | E_sch | 5 | 18 | 6 | 6 | capped-unsaturated |
| `I4-T14-C16-G0` | P1 | A_uas | 7 | 8 | 4 | 6 | capped-unsaturated |
| `I4-T19-C07-G0` | P2 | D_for_smm | 3 | 2 | 3 | 3 | capped-unsaturated |
| `I4-T13-C07-G0` | P2 | B_gsd_ate | 4 | 2 | 2 | 2 | capped-unsaturated |
| `I4-T13-C09-G0` | P2 | B_gsd_ate | 2 | 4 | 3 | 4 | capped-unsaturated |
| `I4-T14-C04-GS` | P2 | A_uas | 5 | 19 | 6 | 7 | enumerated(4 found / 2 negative / 4 not-reached) |
| `I4-T09-C03-G0` | P2 | B_gsd_ate | 6 | 3 | 17 | 17 | capped-unsaturated |
| `I4-T19-C14-G0` | P2 | D_for_smm | 2 (1) | 3 | 1 | 2 | capped-unsaturated |
| `I4-T20-C07-G0` | P2 | D_for_smm | 2 | 1 | 0 | 0 | saturated† |
| `I4-T14-C07-G0` | P2 | A_uas | 3 (1) | 0 | 2 | 2 | capped-unsaturated |
| `I4-T11-C04-GS` | P2 | C_frt_css | 4 | 14 | 8 | 8 | enumerated(5 found / 0 negative / 10 not-reached) |
| `I4-T11-C05-G0` | P2 | C_frt_css | 3 | 3 | 1 | 1 | saturated |
| `I4-T11-C09-G0` | P2 | C_frt_css | 4 | 2 | 3 | 3 | saturated |
| `I4-T11-C16-G0` | P2 | C_frt_css | 3 | 4 | 2 | 2 | capped-unsaturated |
| `I4-T13-C04-G0` | P2 | B_gsd_ate | 2 | 2 | 1 | 1 | capped-unsaturated |
| `I4-T17-C05-GS` | P2 | C_frt_css | 2 | 5 | 4 | 4 | enumerated(2 found / 0 negative / 4 not-reached) |
| `I4-T20-C14-G0` | P2 | D_for_smm | 1 | 2 | 0 | 1 | capped-unsaturated |
| `I4-T20-C16-G0` | P2 | D_for_smm | 3 | 5 | 2 | 3 | capped-unsaturated |
| `I4-T25-C14-G0` | P2 | E_sch | 3 | 5 | 4 | 4 | capped-unsaturated |
| `I4-T25-C16-G0` | P2 | E_sch | 2 | 4 | 2 | 2 | capped-unsaturated |
| `I4-T14-C05-G0` | P2 | A_uas | 4 | 2 | 5 | 6 | capped-unsaturated |
| `I4-T17-C09-G0` | P2 | C_frt_css | 2 | 0 | 2 | 2 | capped-unsaturated |
| `I4-T17-C13-G0` | P2 | C_frt_css | 3 (1) | 2 | 0 | 2 | blocked(access) |
| `I4-T09-C04-GS` | P2 | B_gsd_ate | 2 | 15 | 9 | 9 | enumerated(7 found / 2 negative / 18 not-reached) |
| `I4-T19-C13-G0` | P2 | D_for_smm | 1 | 0 | 0 | 0 | blocked(access) |
| `I4-T19-C16-G0` | P2 | D_for_smm | 5 | 0 | 2 | 2 | saturated† |
| `I4-T20-C13-G0` | P2 | D_for_smm | 1 | 2 | 0 | 1 | capped-unsaturated |
| `I4-T25-C04-GS` | P2 | E_sch | 2 | 3 | 3 | 3 | enumerated(3 found / 0 negative / 5 not-reached) |
| `I4-T18-C04-G0` | P2 | B_gsd_ate | 2 | 4 | 3 | 3 | capped-unsaturated |
| `I4-T23-C10-G0` | P2 | F_data_bwc | 7 | 7 | 7 | 7 | capped-unsaturated |
| `I4-T11-C07-G0` | P3 | C_frt_css | 1 | 0 | 0 | 1 | saturated† |
| `I4-T11-C14-G0` | P3 | C_frt_css | 1 | 4 | 0 | 2 | saturated† |
| `I4-T13-C02-G0` | P3 | B_gsd_ate | 2 | 1 | 1 | 1 | capped-unsaturated |
| `I4-T14-C09-G0` | P3 | A_uas | 2 | 0 | 2 | 2 | capped-unsaturated |
| `I4-T21-C09-G0` | P3 | F_data_bwc | 2 (1) | 0 | 0 | 0 | saturated† |
| `I4-T21-C16-G0` | P3 | F_data_bwc | 1 | 2 | 1 | 3 | capped-unsaturated |
| `I4-T13-C14-G0` | P3 | B_gsd_ate | 1 | 2 | 1 | 2 | capped-unsaturated |
| `I4-T14-C14-G0` | P3 | A_uas | 0 | 3 | 0 | 2 | not-started(budget) |
| `I4-T17-C16-G0` | P3 | C_frt_css | 2 | 1 | 0 | 0 | saturated† |
| `I4-T19-C02-G0` | P3 | D_for_smm | 2 | 2 | 1 | 1 | saturated† |
| `I4-T25-C02-G0` | P3 | E_sch | 1 (1) | 0 | 0 | 0 | not-started(budget) |
| `I4-T28-C16-G0` | P3 | F_data_bwc | 1 | 5 | 3 | 5 | capped-unsaturated |
| `I4-T21-C14-G0` | P3 | F_data_bwc | 0 | 2 | 0 | 1 | capped-unsaturated |
| `I4-T10-C07-G0` | P3 | B_gsd_ate | 1 | 1 | 1 | 2 | capped-unsaturated |
| `I4-T10-C09-G0` | P3 | B_gsd_ate | 1 | 1 | 1 | 1 | capped-unsaturated |
| `I4-T27-C04-GS` | P3 | F_data_bwc | 1 | 5 | 2 | 2 | enumerated(2 found / 2 negative / 47 not-reached) |
| `I4-T14-C02-G0` | P3 | A_uas | 1 | 2 | 1 | 2 | capped-unsaturated |
| `I4-T21-C02-G0` | P3 | F_data_bwc | 0 | 3 | 0 | 2 | capped-unsaturated |
| `I4-T22-C09-G0` | P3 | F_data_bwc | 1 | 0 | 0 | 0 | saturated† |
| `I4-T22-C14-G0` | P3 | F_data_bwc | 0 | 2 | 0 | 1 | capped-unsaturated |
| `I4-T28-C14-G0` | P3 | F_data_bwc | 0 | 3 | 0 | 1 | capped-unsaturated |
| `I4-T23-C05-G0` | P3 | F_data_bwc | 2 | 2 | 3 | 3 | capped-unsaturated |
| `I4-T26-C07-G0` | P3 | E_sch | 2 (1) | 0 | 0 | 0 | capped-unsaturated |
| `I4-T26-C09-G0` | P3 | E_sch | 2 | 0 | 1 | 1 | saturated† |
| `I4-T27-C16-G0` | P3 | F_data_bwc | 2 | 4 | 3 | 4 | capped-unsaturated |
| `I4-TRES-C01-G0` | P3 | G_resid | 3 | 4 | 4 | 3 | saturated |
| `I4-TRES-C02-G0` | P3 | G_resid | 1 | 2 | 2 | 2 | capped-unsaturated |
| `I4-TRES-C03-G0` | P3 | G_resid | 1 | 1 | 2 | 6 | capped-unsaturated |
| `I4-TRES-C04-G0` | P3 | G_resid | 1 | 3 | 2 | 2 | capped-unsaturated |
| `I4-TRES-C04-GS` | P3 | G_resid | 1 | 1 | 1 | 1 | capped-unsaturated |
| `I4-TRES-C05-G0` | P3 | G_resid | 1 | 2 | 1 | 1 | capped-unsaturated |
| `I4-TRES-C05-GS` | P3 | G_resid | 1 | 1 | 1 | 1 | capped-unsaturated |
| `I4-TRES-C07-G0` | P3 | G_resid | 1 | 1 | 2 | 1 | capped-unsaturated |
| `I4-TRES-C09-G0` | P3 | G_resid | 1 | 1 | 1 | 1 | capped-unsaturated |
| `I4-TRES-C15-G0` | P3 | G_resid | 1 | 2 | 1 | 1 | capped-unsaturated |
| `I4-TRES-C16-G0` | P3 | G_resid | 1 | 2 | 1 | 1 | capped-unsaturated |
| `I4-T12-C09-G0` | P3 | B_gsd_ate | 2 (1) | 0 | 0 | 0 | capped-unsaturated |
| `I4-T16-C07-G0` | P3 | A_uas | 1 | 0 | 0 | 0 | saturated† |
| `I4-T24-C09-G0` | P3 | E_sch | 3 (1) | 0 | 1 | 1 | saturated† |
| `I4-T28-C07-G0` | P3 | F_data_bwc | 3 | 0 | 0 | 0 | saturated† |
| `I4-T15-C16-G0` | P3 | A_uas | 2 | 1 | 2 | 2 | capped-unsaturated |

Enumeration outcomes (per-state items are in the query-log `item=`/`outcome=` notes):

| Cell | Found | Negative | Not reached |
|---|---|---|---|
| **T14-C04-GS**, drone reports | MN, IL, VT, CA | NV, OR (duty exists, nothing published) | TX (host unreachable), FL (source 404), UT, ME |
| **T11-C04-GS**, FR reporting | WA, CO, VA (now repealed), MD, ME | — | 10 |
| **T17-C05-GS**, CSS | CA §53166, MN §626A.42 | — | 4 |
| **T09-C04-GS**, ATE | WA, NY, MD, VA, OR, RI, plus the GHSA inventory | CA §22425, DE | 18 |
| **T25-C04-GS**, school safety | IL SOPPA, CT §10-234bb, OH §3319.327 | — | 5 |
| **T27-C04-GS**, fusion centres | ME (statutory annual report), DE (privacy SOP) | WA, WI | 47 |

---

## 3. Per-class coverage (what exists, with evidence)

Candidate counts per class count a multi-class row once in each class it covers.

### Summary by class

| Class | Candidates (new / known) | Best channels found | Cells | Verdicts (pass/flag/block) |
|---|---|---|---|---|
| T09 ATE | 33 (20 / 13) | DC ASC layer; WA WTSC statewide report; per-camera counts on Socrata; state report duties; EDGAR; OSM | C03, C04-GS unsaturated | 27 / 4 / 2 |
| T10 VA | 5 (3 / 2) | contracts only (BriefCam, ZeroEyes); Iowa approved-vendor rule | P3, unsaturated | 3 / 2 / 0 |
| T11 FRT | 21 (15 / 6) | MD/CO/WA regimes; Detroit weekly report; AI inventories; USAspending vendors | C04-GS partial; C16 unsaturated | 17 / 2 / 2 |
| T12 BIO | 3 (1 / 2) | none (probe refused) | effectively unsearched | 2 / 1 / 0 |
| T13 GSD | 16 (11 / 5) | Legistar lifecycle; contracts with sq mi; 10-K denominator; historic alert data | all unsaturated | 5 / 11 / 0 |
| T14 UAS | 30 (17 / 13) | FAA Part 91.113 table (LEAD); EFF FOIA sheet; state reports; DFR dashboards | P1 C16 unsaturated (faa.gov 403) | 11 / 16 / 3 |
| T15 AERO | 5 (3 / 2) | CBP TARS contracts; FAA NPRM; CBP BSS PIA | unsaturated | 3 / 1 / 1 |
| T16 ROB | 1 (0 / 1) | CA AB 481 reports | † | 0 / 1 / 0 |
| T17 CSS | 8 (4 / 4) | CA §53166; USAspending federal; HSGP sub-award | C13 blocked | 7 / 1 / 0 |
| T18 LI | 5 (4 / 1) | US Courts Wiretap Report; CA AG report | unsaturated | 3 / 2 / 0 |
| T19 FOR | 18 (13 / 5) | USAspending prime and sub-awards; Socrata payee datasets; agenda matters | P1 C09 unsaturated; C13 blocked | 5 / 13 / 0 |
| T20 SMM | 18 (11 / 7) | USAspending prime and sub-awards; payees; DHS component PIAs | P1 C09 below q_min | 6 / 10 / 2 |
| T21 DATA | 7 (2 / 5) | USAspending vendors; CBP PIA-080; Google geofence CSV | unsaturated | 6 / 1 / 0 |
| T22 INV | 4 (2 / 2) | The Markup repository (historic) | † / unsaturated | 2 / 2 / 0 |
| T23 BWC | 12 (10 / 2) | USAspending ALN 16.835 (613); IL GATA award list; state programmes | C10 unsaturated | 10 / 1 / 1 |
| T24 EM | 2 (1 / 1) | Cook County Legistar contract chain | † | 1 / 1 / 0 |
| T25 SCH | 19 (12 / 7) | SDPC per-district registry; IL SOPPA; Legistar school tenants | P1 C07/C09 unsaturated | 7 / 10 / 2 |
| T26 WPN | 8 (4 / 4) | USAspending (39); Iowa rule | unsaturated | 4 / 4 / 0 |
| T27 FUS | 6 (4 / 2) | DHS roster (live, gated); ME MIAC report; CalOES AOR polygons | enumeration 2/2/47 | 5 / 1 / 0 |
| T28 BORD | 12 (7 / 5) | ICE 287(g) XLSX; DHS PIAs; CBP towers | unsaturated | 10 / 2 / 0 |

### Evidence by class

**T09 automated traffic enforcement.** This is a zero-concept class (NEW-8, NEW-9).
- **Open data.**
  - DC DDOT "Automated Safety Cameras" names 7 enforcement types. Its Hub licence is CC BY 4.0, and it has a
    monthly violation-count table (C051/C052; F036/F037).
  - Chicago publishes daily per-camera counts (C053/C054; Q027/Q028). Montgomery County MD publishes quarterly
    per-site totals (C055/C056). MTA ACE publishes its enforced routes (C058).
  - 11 US ATE layers are already registered (L031).
  - Violation-level tables are **blocked**: MTA ACE with `vehicle_id` (C059) and NOLA citations (C060).
- **Statutory.**
  - The WTSC statewide report, verified at I4-F257, gives: "29 incorporated municipalities"; "Of the 416 cameras
    in operation as of December 31, 2025"; 846,133 infractions; vendors Novoa and Verra; reported under RCW
    46.63.220 (C067; F041).
  - Duties verified at origin: NY VTL §1180-b (C070), MD Transp. §21-809 statewide per-camera report (C071; not
    located), VA (C072), OR (C073), RI (C074).
  - Inventory: GHSA (C075; only page 1 of 6 was read).
- **Vendor.**
  - EDGAR "photo enforcement" 10-K search: 54 hits from 9 filers (C305; Q159).
  - Verra's FY2025 10-K: Government Solutions was "approximately $460.7 million … approximately 47%" of revenue,
    and "NYCDOT represented approximately 17.9%" (C304; F230).
- **Crowd.** OSM has `highway=speed_camera` 1,383 US nodes and `enforcement=red_light_camera` 236 (C316;
  F233/F234). These tags sit outside the registered `man_made=surveillance` path.
- **Agendas.** Culver City approved a 5-year Verra agreement, NTE $4,554,000, at 12 intersections (merged into
  C091; F231).

**T13 gunshot detection.**
- **Agendas.** Oakland's Legistar has 19 matters from 2006 to 2025 (C076; Q036). The registered connector
  already matches `shotspotter`.
- **Contracts.**
  - Pasadena: sole source, $661,500 over 3 years, funded by asset forfeiture (C077; F047).
  - Fresno: 17.26 sq mi at $1,046,675 a year (C078; F051).
  - Detroit: 34.48 sq mi, $9,058,788 (C079; F052).
- **Evaluation.** SIUE/SLMPD evaluated the programme under a BJA SPI grant (C081; F054).
- **Vendor.** The FY2025 10-K: "178 cities and 22 universities and corporations", "over 1,092 square miles"
  (C082; F055). This is the only national denominator.
- **Data.**
  - Chicago's alert dataset has 222,108 alerts from 2017 to 2024; Chicago "ended its use of ShotSpotter on
    9/22/2024" (C084 with merged C306; F067/F224; flagged).
  - Oakland published 5 historic ShotSpotter datasets (PRR 11288, 2013–2015; C307 family; Q160).
- **Sensor locations are secret by design.** The WIRED leak stays refused.

**T14 drones and DFR.**
- **FAA.**
  - The Part 107 "Waivers Issued" list is an HTML-only table of about 2,199 rows. It holds **unexpired waivers
    only**. Certificate-of-Waiver PDF filenames embed names, so the verdict is **block** (C001 = SRC-025; F001/F002).
  - The DFR channel is the separate **Part 91.113 "Waivers Issued" table**. It is a LEAD: faa.gov returned 403 at
    18:06:30Z (C011; Q007; F004).
- **The ">1,000 agencies" lead** was traced to EFF, not the FAA. EFF (F003): "over 1,000 public safety
  agencies … had received Federal Aviation Administration (FAA) waivers". Also "Only 976 DFR waivers had been
  granted … through April 2025", which EFF attributes to "an FAA representative" (F005). The underlying data is
  EFF's FOIA sheet (C002), whose schema needs checking first. **No FAA publication of these counts was found.**
- **State reports.**
  - MN 2025 BCA report: 135 agencies; "a total of 9,080 UAV uses in circumstances where a warrant was not
    required" (C005; F013).
  - IL ICJIA SFY22: 546 agencies responded and 122 reported 321 drones. It includes zero-drone agencies, which
    gives negatives (C006; F016).
  - VT (C009; F023).
  - CA AB 481 military-equipment reports list drones and ground robots (C012; F034).
- **DFR transparency.**
  - The aggregator's per-source counts were verified (C300; F221, F255).
  - Skydio dashboards are a JavaScript shell (C301; F226/F240). AirData portals (C302; F225). CAPE is merged into
    C020 (JS behind Incapsula; F027/F028).
- **Agency flight-log layers.** Bloomington IN's Socrata log has pilot certificate numbers and addresses, so it is
  **blocked** (C015). ArcGIS flight-log family: C016–C019.
- **Bard CSD** "Public Safety Drones" 3rd edition (2020): "1,578 … agencies" (C022; F030/F031). The Atlas drone
  layer is largely derived from Bard (808 of 1,828 rows cite it; L022).
- **Funding.**
  - Counter-UAS grants FY2026: 12 state awards totalling $250,000,000 (C025; Q020).
  - UAS vendor keywords (C024).

**T15 aerostats and persistent aerial surveillance.**
- FAA NPRM 2025-16236 for a CBP tethered aerostat at South Padre Island (C027; F032).
- CBP TARS O&M, Peraton, $47,453,903.39 (C028; Q024).
- CBP Border Surveillance Systems PIA (C269; F207). EFF's CBP tower map (C268; F220).
- No municipal persistent-aerial contract surfaced.

**T16 ground robots.** The only channel found is CA AB 481 reports: Sacramento's lists a Remotec Andros F6A and a
Qinetiq Dragon Runner 20 (C012; F034). The SF Legistar probe was negative (Q022).

**T11 face recognition.**
- **State regimes.**
  - WA RCW 43.386 accountability reports are posted by the agencies themselves; the state page holds a single NOI
    (C100; F073/F075). WA judicial FR-warrant reports name officers, so they are **blocked** (C101).
  - CO C.R.S. 24-18-301 accountability reports. Arvada: 97 of 13,396 investigations used FR in 2025 (C102/C103;
    F080).
  - **VA's local reporting duty is removed from 2026-07-01** (C104; F079).
  - MD SB 182/2024: a GOCPP report to the General Assembly by October 1 (C105; F081). The publication was not
    fetched.
  - ME §6001 search logs are public but name employees, so they are **blocked** (C106; F082).
  - MA report: 403 (C107).
- **Programme reports.** Detroit sends a weekly FR report to the Board of Police Commissioners. It is aggregate,
  covers 2020–2025, and counts policy violations (C108; F085/F087).
- **Federal.**
  - DHS AI inventory: 214 use cases (C115; F090).
  - OMB consolidated 2024 inventory: 1,757 rows from 37 agencies, including 19 FR rows, 12 with PIIDs. **DOJ and
    DoD are absent** (C116; F092/F093).
  - USAspending: 22 Clearview awards, including ICE at $7,687,500 (C111; Q059).
  - HSGP sub-award descriptions name local FR buys (C112; Q075).
- **Civil society.**
  - Perpetual Line-Up (2016, "all rights reserved"; C118; F101).
  - EFF WHYF CSV, CC-BY (C119; F102).
  - The BuzzFeed Clearview table was **excluded** for leak provenance (NEW-4).

**T17 cell-site simulators.**
- **CA Gov. Code §53166** requires a posted use policy and council approval of acquisition. It is the only
  state-scale CSS self-disclosure regime found (C120; F094). Exemplars: OCSD Policy 610 and Pasadena Policy 620,
  both Lexipol-authored (C109/C110).
- MN §626A.42 tracking-warrant reports (C121; F096).
- **Federal buys** via USAspending: ATF–L3Harris, ICE "CELL SITE SIMULATOR VEHICLES", and FBI–Octasic $1,985,280
  on 2026-09-30 (C122; Q060).
- **HSGP sub-award:** "a cell site simulator for the Dallas Fusion Center", $900,000 (C112; Q072).
- The ACLU map says "75 agencies in 27 states" and was last updated 2018-12-14, with no table (C123; F099).
- The records channel is blocked: DocumentCloud and MuckRock both returned 403.

**T18 lawful intercept.**
- US Courts Wiretap Report 2024 (C085/C086; F043–F045), verified at F254: "A total of 2,297 wiretaps … 1,290 …
  federal … 1,007 … state"; 11 xlsx tables.
- CA AG interceptions report: 18 of 58 counties (C087; F046).
- Pen-register reporting has no public tables (F043).

**T19 mobile forensics** (zero-channel before this row).
- **USAspending.**
  - Primes: 3,538 contracts on four vendor terms (C150; Q170, re-counted by the integrator).
  - Sub-awards name local buyers: Adams County NE, Houston, WA DOC, Johnson County KS and Seattle PD (C151;
    Q078/Q079).
- **Socrata vendor-payment family (C164; Q096: 212 datasets).**
  - Chicago: Cellebrite 29 payments, $1,298,626.80 (C165; Q097).
  - Delaware (C170; Q099) and NJ (C171; Q105).
  - WA statewide checkbook (C156).
- **Documents.**
  - Maine sole-source justification: $77,628.80 (C155; F107).
  - Miami-Dade SS-10291: $6,817,350 (C160; F115).
  - Placer County GrayKey: $184,000 (C161; F116).
  - Jefferson County MO renewal chain (C158; F113).
  - Phoenix Cellebrite matters on a registered tenant (C162; Q094).
  - Michigan State Police Order 07-09 is a statewide Cellebrite policy (C312; F229).
- **Vendor.** Cellebrite's 20-F: the vendor states more than 90% public-sector revenue, with US federal about 16%
  in 2025 (C153; F106).
- **NGO.** Upturn states ">2,000 agencies", but that list is **unpublished**. The only data is Appendix C (84
  agencies), and it derives from the paid GovSpend (C163; F117/F118).

**T20 social-media and OSINT monitoring** (zero-channel before this row).
- **USAspending primes** (C152; Q080/Q081): 1,899 contracts. Examples: ICE Pen-Link $26.2M; DEA ShadowDragon
  $12.6M; ICE Babel Street through a reseller $10.3M; ICE ZeroFox $13.0M; USAF Dataminr $298.8M.
- **Sub-awards** (C154; Q082): Marion County Sheriff–Skopenow $133,000; IMPD–Dataminr $80,000; WY AG–Cobwebs
  $182,000.
- **Payees.**
  - Found in Chicago, Delaware and CT (Q098/Q099/Q106).
  - LA shows **no SMM vendor as payee**, which points to reseller masking (Q102).
- **Governance.**
  - DHS component PIAs: CBP-058, ICE-064, OPS-004, FEMA-041 and USSS-026 (C167; F124/F125).
  - Portland City Auditor 2022 audit of police intelligence-gathering (C308; F238).
  - SFPD DGO 6.21 (C311; F239).
- **Baseline.** Brennan Center: 158 jurisdictions, and a 151-agency PO index updated 2016-11-14, built from
  SmartProcure, now the paid GovSpend (C166; F119/F120).
- ACLU NorCal's Geofeedia records centre on monitored people, so they are **blocked** (C169).

**T21 data brokers and location data.**
- USAspending: 9 vendor terms match 952 contracts. One is ICE's 2026 purchase of "BABEL STREET INSIGHTS
  LICENSES, LOCATION AND IDENTITY APPLICATION PROGRAMMING INTERFACES" (C258; Q143).
- CBP PIA-080 "Commercial Telemetry Data Evaluation" (C260; F208).
- Google's geofence warrants by jurisdiction, 2018–2020: a CSV of 52 rows (C262; F209/F210).
- Apple's CSVs are country-level only (C263; F211).
- EFF Fog: "at least 18 … clients", with **no structured list** (C264; F213).

**T22 investigative and predictive platforms.**
- The Markup's PredPol repository (BSD-3-Clause) has `departments.csv` (38 departments) and usage dates. Its
  `arrests.csv` and `uof.csv` must never be ingested (C265; F214/F215).
- Local Legistar probes were negative (Q150).

**T23 body-worn cameras and evidence platforms.**
- **USAspending ALN 16.835** (the BWC Policy and Implementation Program): **613 grants**, verified at Q169 (C250;
  Q138).
- BJA award pages now sit behind a login (C251; F186).
- **Illinois** GATA CSFA 569-00-3496 publishes a per-award table of about 176 rows (C252; F187/F188).
- **Other states.**
  - OH: average award $34,694.52 (C253; F189).
  - SC: "291 qualifying entities … $44.85 million since FY 2017", with no list (C254; F190).
  - MA: 144 departments and more than 4,800 cameras (C255; F192).
  - CO: 403 (C256).
- The 2016 LCCHR/Upturn scorecard origin is dead (C257; F193/F194).
- NOPD's BWC metadata carries per-video lat/long, so it is **blocked** (C277).

**T24 electronic and custodial monitoring.**
- Cook County Legistar holds the contract chain for 2014–2024 (C218; Q128):
  - RF electronic monitoring: 3M, then Attenti, then Allied;
  - GPS monitoring: Sentinel, then Track Group;
  - jail telephones: Securus.
- The FFJC 50-state survey found that "43 states have statutes or rules explicitly authorizing fees" (C310;
  F228).

**T25 school surveillance** (zero-channel in the US before this row).
- **SDPC Registry.** 13,177 districts and 244,291 active data-privacy agreements (F154). Per-district listings are
  public, verified at F256. The API and state search need a member login, and the terms bar distribution
  (C200).
- **Statutory posting duties.**
  - IL SOPPA: operator list plus agreements within 10 business days (C201; F163).
  - CT §10-234bb(g) (C202, LEAD).
  - OH §3319.327: parent notice of "general monitoring" of school devices (C215; F179).
- **Agendas.** OUSD's Legistar shows GoGuardian 21-0665 and 23-2577 (NTE $92,012.20) (C205/C206; Q117).
- **Oversight.**
  - Warren–Markey report (C210; F173).
  - Gaggle's letter: the vendor states more than 1,500 districts. It quotes redacted alerts, so it is **blocked**
    (C220).
- **Statistics.** NCES SSOCS public-use files, 9 waves (C211; F174/F175).
- **Federal awards are not a channel:** 0 genuine monitoring-suite primes (C217; Q130).

**T26 weapons-detection screening.**
- USAspending: 39 awards, 12 of them direct to Evolv (C216; Q129).
- The Iowa HSEMD rule requires posting approved "unholstered weapons detection systems" (C214; F178).

**T27 fusion centres.**
- The DHS roster is live, "Last Updated: 09/04/2026", with 54 + 26 = 80 centres (C270 = `dhs_fusion_centers`,
  gated; F196).
- **Maine MIAC** statutory annual report 2025: 224 RFIs, 90 ALPR requests, 3 FR requests (C273; F200).
- Delaware DIAC privacy SOP (C274; F203).
- CalOES fusion-centre AOR polygons (C275; Q155).
- HIDTA returned a challenge (C271) and RISS was unreachable (C272).

**T28 border and immigration.**
- **ICE 287(g) participating agencies** (C280; F205/F206, verified F252):
  - file `participatingAgencies09282026.xlsx`; the filename rotates with each issue;
  - 2,608 rows, split TFM 1,849 / WSO 564 / JEM 184;
  - agency-level only.
- Monthly encounter PDFs are flagged (C281).
- HART PIA (C261). DHS PIA family (C259).
- Agenda probes were negative (Q148/Q151/Q152).

---

## 4. Ranked shortlist (for I7)

Ranking follows I2's order: zero-channel classes and ATE first; then I1#8 classes; then DATA/INV; then probes.
Within that order, rows are weighted by structure and recurrence, national scale, connector reuse and a
manageable Part VIII posture.

Rights columns are **guesses**, never decisions (R5). Each ✔ marks a spot-check the integrator re-fetched
independently and found to match.

| # | Candidate(s) | Gap closed | Access and connector | Rights guess · Part VIII |
|---|---|---|---|---|
| 1 | **USAspending slices** (FAM-USASPENDING-SLICES): C150/C151 FOR, C152/C154 SMM, C258 DATA, C250 BWC ALN 16.835 ✔, C111/C122/C112 FR/CSS, C216 WPN, C025 C-UAS, C024 UAS, C090 GSD rename/ATE | I1#7 (FOR, SMM), I1#13 root cause, first BWC funding channel, WPN (NEW-5) | api; **configure existing** `procurement:usaspending` (vendor and class keywords, ALN filter, recipient disambiguation, bound review) | bytes likely-open (federal) · sub-awards flag (free text) |
| 2 | **Agenda vocabulary** C091 (ATE/VA/BIO, with C314 merged) + C162 (FOR/SMM) | I1#7, NEW-8 across about 306 Legistar tenants (793 agenda tenants) | **configure existing** agenda connectors; word-boundary filters (NEW-6) | facts likely-open · flag (minutes free text) |
| 3 | **Socrata vendor-payment / checkbook family** C164 (+C165 Chicago, C170 DE, C171 NJ, C219, C221) | local purchase evidence for FOR/SMM/SCH/WPN (I1#7, I1#6) | socrata; aggregate SoQL by payee only; reseller masking noted | mixed per-portal licences · flag |
| 4 | **SDPC per-district registry** C200 ✔ + **IL SOPPA** C201 (+OH C215, CT C202) | first national district-keyed school-monitoring channel (I1#7) | html per district; the API is login plus premium, so it is out of scope | bytes **likely-restricted** by terms (clause 1.6) · flag |
| 5 | **FAA Part 91.113 DFR waivers** C011 (LEAD, re-fetch) + **EFF FOIA DFR sheet** C002 (+ SRC-025 Part 107) | DFR half of I1#8 | html-table snapshots (unexpired only) | federal work · **operator-identifier** (pilot names); screen before any rows |
| 6 | **DFR transparency dashboards** C300 ✔ / C301 / C302 / C020 | about 128 non-Flock agencies with flight-level operating evidence (I1#8) | JS apps and an aggregator's monthly snapshot; no licence stated | undetermined · **residential-intersection** flag; programme-level facts only |
| 7 | **ATE package**: C067 WTSC ✔ + C068 city reports; C051/C052 DC (CC BY 4.0); C050/C065 open-data family; C071/C070 MD/NY duties; C316 OSM | NEW-8 whole class; I1#4 | pdf, arcgis, socrata; reuses `dot_511:*` and `osm` | open or likely-open for layers · violation rows **blocked** |
| 8 | **State drone censuses** C006 IL, C005 MN, C012 CA AB 481 (drones and robots), C009 VT | I1#8, I1#4; T16's only channel | `dossier_documents:pdf_text`; annual | state works · VT and AB 481 appendices flagged |
| 9 | **ICE 287(g) roster** C280 ✔ | T28, a zero-source class | bulk xlsx; discover it from the landing page (filename rotates) | federal public domain (guess) · pass |
| 10 | **FR accountability**: C105 MD, C102/C103 CO, C108 Detroit weekly; **AI inventories** C115/C116 | I1#4, I1#8 federal operator layer | pdf and csv; `new:ai_inventory` (I6 owns multi-class) | state and municipal works; federal · pass |
| 11 | **US Courts Wiretap tables** C085 ✔ | T18, first national channel (I1#4) | bulk xlsx, annual | federal · pass (the A-1/B-1 appendix names judges: flag) |
| 12 | **SEC EDGAR family** C082 SoundThinking, C304/C305 Verra and ATE, C153 Cellebrite, C026 DFR | vendor denominators (NEW-7); GSD national scale | `new:sec_edgar_fts`; needs an **operator-approved UA contact** (NEW-11) | facts likely-open · pass |
| 13 | **DHS privacy-document indexes** C259 (+C260 PIA-080, C167 SMM PIAs, C261 HART, C269 BSS) | I1#13 federal anchor; T20/T28 governance | html index to PDFs; widen SRC-023 into a family | federal · pass |
| 14 | **Google geofence-warrant CSV** C262 | the only state-level `geofence-warrant-data` (I1#13) | static CSV (2018–2020) | Google terms undetermined · pass |
| 15 | **CA §53166 CSS policies** C120 | I1#8 / I1#4 CSS self-disclosure | pdf per agency (SB 34 analogue) | state and Lexipol © (facts only) · pass |

Runners-up:
- C252: the Illinois GATA award list, a statewide grants template.
- C273: the Maine MIAC statutory report.
- C218: Cook County EM contracts.
- C084: the Chicago GSD alert history, flagged; aggregate lane only.
- C265: The Markup's 38 departments.

---

## 5. Negatives (a finding in themselves)

| Class | What does not exist publicly | Why, and evidence |
|---|---|---|
| T13 GSD | Sensor or coverage-polygon locations | Secret by design. The only location data is the refused WIRED leak. Two cities' historic alert tables exist (Chicago to 2024-09-22; Oakland 2013–2015; Q160). Socrata has 6 "shotspotter" datasets nationally. |
| T17 CSS | A current agency-possession list | The ACLU map is frozen at 2018-12-14 with no table (F099). CA §53166 has no periodic public report (F094). Local buys appear only when federally funded. |
| T19 FOR | A national agency list | Upturn's 2,000-agency list is unpublished and GovSpend-derived (F117/F118). No GitHub dataset exists (Q107). |
| T20 SMM | A current national list | Brennan's list is 2016, SmartProcure-derived (F119/F120). Resellers hide vendors in payee data (Q102). No department-wide DHS operational PIA exists (F122). |
| T21 DATA | Broker customer lists (Fog, Venntel, Anomaly Six) | EFF holds DocumentCloud records but no list (F213). Venntel, Fog and Anomaly Six are absent from the USAspending top 100 (Q143). Local purchases are invisible. |
| T25 SCH | A cross-district board-platform index; federal award data | BoardDocs returned 403 even for robots.txt (F165); BoardBook 400. There are 0 genuine federal primes for monitoring suites (Q130). The SDPC state search needs a login (F156). |
| T16 ROB | A national robot inventory | Only CA AB 481 reports (F034). |
| T15 AERO | A municipal persistent-surveillance contract | Only DoD and CBP awards surfaced (Q024). |
| T24 EM | A 50-state inventory of reporting duties | Only a fee survey exists (F228). Records are person-level by nature. |
| T27 FUS | A state inventory of fusion-centre annual reports | Only Maine has a statutory annual report (F200). There is no compilation (Q145). |
| T23 BWC | Structured state BWC grant recipient lists, except Illinois | OH, SC and MA publish programme or press-release text only. Socrata has 0 datasets (Q153). |
| T18 LI | Pen-register and trap-and-trace tables | Not in the Wiretap Report (F043). |
| FAA (T14) | Any bulk FAA waiver download; FAA-published DFR counts | The waivers exist as an HTML table only (F001). The counts come from EFF, not the FAA (F003/F005; Q005). |
| T10 VA, T12 BIO | Any dataset | Contracts only. T12 was not meaningfully searched because its probe was refused (Q048). **This is not a negative.** |

---

## 6. Movement against the I1 blind spots

- **#7, zero-channel classes.**
  - SMM, forensics and US school surveillance each now have repeatable channels: USAspending prime and sub-award
    slices; Socrata payee datasets; the SDPC registry and statutory posting duties; Legistar tenants.
  - ATE has 33 candidates and a concept proposal (NEW-9).
  - gap_ref counts: I1#7 50, NEW-8 49.
- **#8, UAS/GSD/FRT/CSS beyond the Atlas.**
  - First non-Atlas channels: FAA Part 91.113 (LEAD), state drone reports, DFR dashboards, the SoundThinking 10-K
    denominator, state FR regimes, CA §53166 and HSGP sub-awards.
  - gap_ref count: I1#8 71.
- **#13, data brokers.** The root cause is confirmed and quantified: the keyword lists have no vendor terms (NEW-5).
  CBP PIA-080 and the Google geofence CSV add federal and state anchors. gap_ref count: 9.
- **#4, statutory reporting.**
  - New regimes: MD/CO/WA FR; WA/NY/MD/VA/OR/RI ATE; IL/MN/VT/CA drone; ME fusion; IL/CT/OH school; US Courts
    wiretap.
  - **VA's FR duty ended on 2026-07-01** and WA's old ATE statute was repealed (NEW-12).
- **States.**
  - Tier A gained: MI 5, DE 3, RI 3, ME 3, VT 1. Tier B gained: DC 2, NM 2.
  - Tier A still has no I4 candidate in NH, MS, WV, WY or AR. Those remain I5's.
  - Most place-anchored rows are in CA (24), IL (12) and WA (10).

---

## 7. Part VIII log (counts only, no content)

- **Verdicts:** pass 108, flag 70, block 11.
- **Blocked rows** (metadata only, rows never read):
  - C001: FAA Part 107 table (names in PDF filenames).
  - C015: Bloomington IN UAV flight log (pilot certificate numbers, addresses).
  - C029: FAA aircraft registry.
  - C059: MTA ACE violations.
  - C060: NOLA citations.
  - C101: WA judicial FR-warrant reports.
  - C106: ME FR search logs.
  - C169: ACLU NorCal Geofeedia records.
  - C213: FL school-safety portal.
  - C220: Gaggle letter (alert excerpts).
  - C277: NOPD BWC video metadata.
- **Flags present** (one row can carry several): free-text-narrative 25, private-person-name 25,
  residential-intersection 21, officer-name 12, home-address 9, operator-identifier 7, person-level-enforcement 7,
  minor-data 5, per-search-audit 3, plate-level 2.
- **Redactions at integration:** 4 personal-style ArcGIS owner account ids (Bellevue, MCPD, Boulder, Alabama
  GeoHub), replaced with `<staff account id redacted>`.
- **Raw captures deleted by batches** because they held names or identifiers: FAA table pages, the VT report,
  Bloomington metadata, the Hub owner JSON, the Elk Grove and Sacramento PDFs, the wiretap A-1 xlsx, the
  Cook County and OUSD matter JSON, the Gaggle letter, a Whitestown quote, and the Maine MIAC text extraction.
- **Exclusions:** the BuzzFeed Clearview table (leak provenance; NEW-4); spyware leak material (none used); social
  posts.
- **Latent exposure raised as NEW-2.** Atlas `attribution_links` carry 152 FAA waiver-PDF URLs whose filenames
  name pilots. The public claim API does not show them (F251).

---

## 8. Access failures and INACCESSIBLE list

A host that returned 403 or a challenge was stopped for the rest of the batch, with no retry and no mirror (R4).

| Host | Status | First seen (UTC) | Effect |
|---|---|---|---|
| www.faa.gov | 403 | 18:06:30 | Part 91.113 table (C011) and aircraft registry (C029) not fetched |
| www.muckrock.com | 403 / challenge | 18:08:02 | CSS and forensics records cells blocked (C004) |
| www.documentcloud.org, api.www.documentcloud.org | 403 | 18:06:27 / 18:16:11 | CSS records; pathways fixture check |
| www.courtlistener.com | 403 | 18:07:09 | fixture check only |
| www.ncsl.org | 403 | 18:07:22 | state-law inventories (drones, ATE) |
| a860-gpp.nyc.gov | 403 | 18:08:33 | NYC reports (C309) |
| mass.gov | 403 | 18:06:19 | MA FR report (C107) |
| michigan.gov | 403 | 18:11:09 | MI SNAP (C113) |
| lasd.org | challenge | 18:11:15 | LACRIS RFP (C114) |
| chulavistaca.gov | 403 | 18:17:08 | Chula Vista DFR (C021) |
| elkgrovepd.org | 403 | 18:18:55 | — |
| nyclu.org | challenge | 18:19:47 | Prying Eyes (C023) |
| capitol.texas.gov, statutes.capitol.texas.gov | socket / SSL errors | 18:11:55 | TX drone reports (C007) |
| go.boarddocs.com | 403 (CloudFront) | 18:09:30 | school boards (C203) |
| meetings.boardbook.org | 400 | 18:09:39 | C204 |
| civiciq.com, cdt.org | challenge | 18:11:10 / 18:11:47 | C207, C208 |
| www.ed.gov | 403 | 18:20:11 | — |
| civilrightsdata.ed.gov | JS shell | 18:13:35 | CRDC (C212) |
| dcj.colorado.gov | 403 | 18:10:04 | CO BWC (C256) |
| www.hidta.org | challenge | 18:12:39 | C271 |
| www.riss.net | TLS failure / socket closed | 18:12:41 | C272 |
| fusion.vsp.virginia.gov | 403 (Wordfence) | 18:13:47 | VA fusion |
| www.bwcscorecard.org | TLS failure | 18:10:46 | C257 (origin appears dead) |
| www.ilga.gov | 403 / TLS | 18:08:03 | used the origin-offered `ftp.ilga.gov` |
| catalog.data.gov CKAN API | 404 | 18:11:04 | NEW-8 |
| docs.southbendin.gov | cookie wall | 18:11:15 | C080 |
| aerial.motorolasolutions.com; cloud.skydio.com | JS-only (Incapsula; shell) | 18:16:44 (F027); 18:11:50 (F240) | C020, C301 content not read |
| WebSearch tool | session quota 200/200 | 18:14:50 | NEW-10 |

**Login, paid or licence-walled** (never attempted; operator action where noted):
- BJA award pages (DOJ SSO).
- SDPC Registry API and state-alliance search (member login plus Premium).
- ICPSR (LEMAS-BWCS, C317).
- NCES SSOCS restricted-use file.
- GovSpend/SmartProcure (PAID; upstream of the Upturn and Brennan lists).
- Commercial ATE camera databases (PAID).
- EFF Red Flag Machine raw data (shared case by case).

---

## 9. Findings raised (`findings/incoming/I4.csv`, all `proposed`)

| Id | Sev | Short title |
|---|---|---|
| NEW-1 | S2 | `pathways_*` fixture URLs dead or placeholder (3/3 EFF 404); production serves an unanchored RESOLVED drone "deployment" attributed to "per-fixture URLs" |
| NEW-2 | S2 | Latent Part VIII exposure: Atlas `attribution_links` include 152 FAA waiver-PDF URLs that name pilots; not exposed by `/v1/claim` today |
| NEW-3 | S3 | Dead Atlas evidence locators: 194 MN and 84 FL drone links return 404 |
| NEW-4 | S2 | Leak-provenance taint: 9 live Atlas FR rows cite the BuzzFeed Clearview article (4 cite nothing else) |
| NEW-5 | S2 | The USAspending connector is blind to vendor names and to the FOR/SMM/ATE/WPN/EM/BIO classes; the counts are quantified |
| NEW-6 | S2 | The agenda vocabulary lacks FOR/ATE/VA/BIO terms and its SMM term is too narrow; substring false positives |
| NEW-7 | S2 | Registry mis-descriptions: `faa_drone_waivers`, `aclu_cell_site_simulators` (2018), `dhs_fusion_centers` (live but gated), tenant `ousd` (Oakland USD labelled "SD") |
| NEW-8 | S3 | catalog.data.gov CKAN API returns 404, but the allowlist and the I2 protocol still name it |
| NEW-9 | S3 | Ontology gaps: counter-UAS, ATE sub-types and zones, fusion-centre organisation roles |
| NEW-10 | S2 | The session WebSearch quota (200) is shared across parallel rows, below Stream I's 600-query plan |
| NEW-11 | S2 | Conduct incident: the operator's e-mail was sent as the EDGAR contact User-Agent without permission; the EDGAR connector needs an approved contact |
| NEW-12 | S3 | Planning seeds cite superseded or wrong identifiers (RCW 46.63.170; VA §15.2-1723.2; DHS/ALL/PIA-058; VT §4622) |

---

## 10. Open questions for I7 and the operator

1. **I4b follow-up.** Should I4b re-run with a fresh WebSearch quota? The unsaturated P1 and P2 cells are:
   - T20-C09 (below q_min), T19-C09, T25-C07, T25-C09 and T14-C16;
   - T20-C13/C14, T19-C13 (blocked) and T17-C13 (blocked);
   - T12 (unsearched);
   - the state enumerations: 10 FR, 18 ATE, 47 fusion, and TX/FL/UT/ME drones.
   Also re-fetch FAA Part 91.113 (C011) from a network where faa.gov answers. Sequence it with I3/I5/I6 so the
   rows do not share one quota (NEW-10).
2. **HG-03 rights packets needed for:**
   - the SDPC registry: its terms bar distribution, so the options are facts-only or a partnership;
   - the DFR vendor dashboards and the AH Datalytics aggregator (no licence stated);
   - EFF's FOIA DFR sheet and WHYF CSV (CC-BY with a third-party caveat);
   - Google's geofence CSV;
   - `dhs_fusion_centers`: origin live, gated only on rights.
3. **EDGAR contact string (NEW-11).** An EDGAR connector needs a declared User-Agent contact. Which contact does the
   operator approve? It must be configuration, never a personal address by default.
4. **Scope.** I4 counted counter-UAS under T14 (FEMA's $250M programme). Should the ontology add `counter-uas`
   (NEW-9)?
5. **Legistar matching.** `substringof` case sensitivity is contradictory between batches D and E. I8 should test
   it before relying on title filters.
6. **Cross-row duplicates to merge in I7:**
   - C116/C115 (AI inventories) are I6's lane.
   - C082/C304/C305/C153/C026 (EDGAR) overlap I6's vendor-disclosure work.
   - The DHS PIA family overlaps SRC-023.
   - C112 (HSGP sub-awards) extends the P31-owned `fema_hsgp_allocations` (consume_existing).

---

## Appendix — reproduction

**Sources.** The authorities are `data/query_log_I4.csv` (chronological) and `data/candidates_I4.csv`. Every
`found_by_query_id` resolves to a log line, and every candidate has a fetch or API-query line, except the
2 lead-only rows C011 and C029, whose evidence class is `lead-only(…)`.

**Integrator scratch** (gitignored, `docs/build/logs/next-phase/I4/`):
- `BRIEF.md`: the batch brief.
- `dedupe.sh`: the I2 §7.6 greps.
- `merge.py`: validator.
- `integrate.py`: merges, corrections and redactions; it writes both CSVs.
- `cells_table_final.md`.
- `integ/`: integrator captures F241–F252 and Q169/Q170 JSON.
- Per-batch folders `A_uas` … `G_resid`, each with `queries.csv`, `candidates.csv`, `cells.csv`, `notes.md` and
  `raw/`.

**Commands.**
- `python3 docs/build/logs/next-phase/I4/merge.py` validates the batch files.
- `python3 docs/build/logs/next-phase/I4/integrate.py` regenerates the committed CSVs.

**Cell statistics.** Recompute from the log's `cell=` and `new=` keys (I2 §8).

**Self-check (I2 §9).**

| Check | Result |
|---|---|
| Every candidate has a fetch or API line | pass (2 labelled lead-only) |
| Every query line has `cell=` | pass (integrator QA lines use `cell=integrator-…`) |
| P1/P2 cells meet `q_min` or carry an honest non-saturated status | pass (T20-C09 is below q_min and marked capped-unsaturated) |
| `cand_id`s unique | pass |
| `registry_match` computed with the §7.6 greps | pass |
| No plate, operator id, officer name from audit data, search reason, student datum or private address in committed files | pass after 4 redactions |
| No rights lane says `decided` | pass |
| Every date from `date -u` | pass, with the re-stamps disclosed in §1 |
