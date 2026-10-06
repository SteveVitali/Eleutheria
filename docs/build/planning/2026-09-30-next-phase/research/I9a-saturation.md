# I9a — Search saturation pass over the unsaturated I3 and I6 cells

Row I9a of `META_PLAN.md` Stream I. It re-runs the P1 and P2 cells that I3 (`research/I3-alpr-networks.md` §3) and I6
(`research/I6-evidence-channels.md` §3) left unsaturated after the shared session WebSearch cap ran out, then spends
the remaining budget on a few P3 probes. It follows `design/I2-source-search-protocol.md` (the protocol).

**Outputs** (and nothing else):
- this note;
- `data/candidates_I9a.csv` — 52 rows, the §8.6 columns plus the I2 §7.3 extension columns;
- `data/query_log_I9a.csv` — 185 lines: 98 queries, 84 fetches, 3 local operations;
- `findings/incoming/I9a.csv` — NEW-1…NEW-6.

Raw captures, the fetch index and the generator scripts are under `docs/build/logs/next-phase/I9a/` (gitignored).
Nothing was committed. No production system was touched.

**Evidence rule.** Every factual sentence cites a fetch (`I9a-F###`), a query line (`I9a-Q###`), a local operation
(`I9a-L###`) or a repo `file:line`. Search-engine summaries are labelled **lead** and are never evidence. Vendor
statements are genre D6 assertions ("the vendor states").

**Timing.** The row ran in two sessions:
- The first run started 2026-09-30T18:57:22Z and was stopped by an account usage limit at 19:10:35Z, after
  `I9a-Q020`/`I9a-F030` (session log in the scratch directory).
- This resumed run began at 20:12:08Z. It kept every earlier row, continued the ids from `Q021`/`F031`/`C021`/`L002`,
  and repeated no logged query. The last search ran at 20:41:38Z. This note was written at 20:44:24Z, from `date -u`.

---

## 1. Summary

**Budget used.** No budget was fixed for I9a. The row used the unspent I3 + I6 budgets (146 queries, 253 fetches) as its
ceiling.
- 98 queries: 94 WebSearch, 2 ArcGIS Hub API, 2 Federal Register API.
- 84 fetches.
- 3 local operations.
- The context guard (R11) was never reached.

**Candidates.** 52 in total.
- Against the registry, the queue and I3–I6: 29 `new`, 23 `related:`, 0 `same-as:`. Cross-row duplicates were merged
  into notes and got no row.
- By level: 19 publisher, 18 channel, 10 target, 5 family.
- By Part VIII verdict: 38 pass, 12 flag, 2 block.
- 12 rows are `LEAD-ONLY`: blocked, a duty with no publication found, or a bill not verified as enacted.

**Cells.** Every I3 and I6 P1/P2 cell on the two unsaturated lists now has an honest closing status (§3).
- P1 sweeps: 5 of the 6 are now `saturated`. `I3-T01-C07-G0` closes `extended, capped-unsaturated`.
- P1 enumerations: all 5 are enumerated against their inventory shortlists.
- P1 origin-refused: `T01-C01` stays `n/a (origin refused)`.
- P2 cells: all 16 worked cells (6 I3, 10 I6) are `saturated` or enumerated.

**The most important results.**

1. **Washington now publishes a statutory statewide ALPR operator list** (`I9a-C036`).
   - RCW 10.130 (ESSB 6002, 2026) requires every agency to register its ALPR system with the Attorney General before
     operating it.
   - The AGO page lists 76 registered agencies (67 police, 9 sheriff), each with a submitted date and a linked ALPR
     policy (`I9a-F059`; parse `I9a-L003`).
   - It is the Washington analogue of Minnesota's BCA list (I3-C039). SIG has no row for it (finding NEW-3).
2. **The state ALPR statute layer moved in 2026** (finding NEW-1). Each of the following was fetched at origin:
   - five enactments: WA ESSB 6002 (`F026`), NM SB 40 (`F028`, `F060`), OR SB 1516 (`F029`), CT SB 397 = Public Act
     26-14 (`F042`) and KY HB 58 (`F041`);
   - one 2025 enactment missing from the 2022 seed: ID S1180 (`F051`);
   - two executive instruments: Missouri EO 26-18 (`F043`) and the Florida DOT memo EOM26-01 (`F045`, image-only).

   Kentucky HB 58 is the first statute found that regulates commercial ALPR collectors (insurers and repossession
   lenders; T04) alongside police use (`F041`).
3. **New statutory ALPR reporting channels.**
   - Nebraska Crime Commission: 89 per-agency ALPR reports from about 29 agencies, 2018–2026 (`F021`).
   - Vermont DPS annual reports under 23 V.S.A. 1607, tier-A VT (`F016`).
   - Illinois State Police ALPR transparency page and FY23–FY26 reports: 808 expressway cameras and per-county tables
     (`F022`, `F023`).
   - Duties without a publication found (lead only): New Mexico agency reports to DPS, first due on or after
     2027-04-01 (`F060`); Arkansas Highway Police statistics "to allow the general public to review", tier-A AR
     (`F048`); the NC SBI report on ALPRs in NCDOT right-of-way (403); Utah's annual FR report to an interim committee
     (`F078`).
4. **The ALPR footprint is shrinking fast, and SIG has no end-event lane** (finding NEW-2).
   - FDOT ordered all ALPRs removed from state-highway right-of-way (memo 2026-08-31; content via EFF, `F044`/`F045`).
   - Texas halted state funds for Flock (2026-08-28; lead, no written order found).
   - An Institute for Justice database tracks contract cancellations (403, `F047`).
5. **Private-camera registries and Fusus.**
   - A registry-programme family (`I9a-C001`) with 7 members, several on platforms SIG lacks: Polaris CameraKit (`C002`)
     and Genetec Clearance (`C010`, lead).
   - Axon Fusus "Connect ‹Place›" agency sites (`C003`), plus Fusus deployment documents: Cincinnati (`C021`),
     Elizabeth City (`C039`) and an NC council deck (`C038`).
6. **Grant and earmark channels that name LPR and RTCC projects per agency.** Alabama ADECA (`C041`), the Florida
   Legislature Local Funding Initiative Requests (`C043`), House Community Project Funding letters (`C044`), Virginia
   HEAT (`C049`, 403) and Leonardo's list of state contract vehicles for ELSAG (`C040`).

---

## 2. Method, and deviations from I2

**Inputs read.**
- META_PLAN §3 (P1–P16), Stream I §6 (I1–I9), §8.2, §8.6.
- The protocol: §0–§1, §3, §5.4–§5.8, §6–§9, §11–§12.
- `data/search_matrix.csv` (the targeted cells).
- The unsaturated-cell lists in I3 §3 and I6 §3.
- For dedupe: `data/candidates_I3…I6.csv`, `connectors/src/connectors/data/sources.toml` and the other files named in
  protocol §7.6 (read-only).

**Order.**
1. Close P1 sweeps.
2. Run P1 enumerations inventory-first:
   - LAPPA 2025, read locally: `L001` and `L002` on I3's capture `docs/build/logs/next-phase/I3/raw/namsdl_2025.pdf`,
     sha256 `34814c0df94d`;
   - the MultiState 2026 roundup (`C030`);
   - the CDT FRT inventory (`C023`).
3. P2 sweeps.
4. P3 residual probes.

Every candidate was fetched at origin where the origin answered. Schemas and landing pages were read; rows never
were (R6).

**Dedupe** was mechanical (`dd.py` in scratch): a case-insensitive grep over `sources.toml`, the target TOMLs,
`acquisition_queue.toml`, the six-streams `source-candidates.csv`, `source_coverage.csv` and I3–I6 (+I9a).

**Deviations (each is recorded in the query log):**

1. **Tooling.**
   - Fetches used Python `urllib` with its default user-agent (engine `urllib-get`), so raw bytes could be hashed. No
     contact header and no identity were sent (P16).
   - `WebFetch` was used 5 times: after a local DNS failure (NE), after a TLS failure (CT), and for the image-only FDOT
     PDF. Its "sha256" is n/a, and `run_at` is the `date -u` just before or after the call, as noted per line.
   - `federalregister-api` follows I6's precedent: a documented public API that is not in the §8 engine list.
2. **Two logged timestamps were corrected before hand-off.**
   - `L002` and `Q063`–`Q066` had first been given times not taken from `date -u`.
   - They now carry the nearest real later timestamp, marked `run_at=upper bound` (P2).
3. **One R4 lapse.** `F050` went out in the same batch as `F049`, about 1 s later, before `F049`'s 403 was read. The
   host got no further request.
4. **Correction of this row's own earlier output.**
   - The first run attributed Connecticut's enactment to HB 5449 from a snippet.
   - The origin shows Public Act 26-14 is SB 397 (`F042`).
   - `I9a-C018` keeps its row, with a correction note. `I9a-C025` is the enacted act.
5. **Family counting.** Members of an already-captured family are recorded as `dup`/members, not `new`, so saturation
   is not inflated. The first run used the same convention.
6. **SEC EDGAR was not called.** EDGAR requires a declared contact User-Agent, and P16 forbids the operator's identity.
   The need is recorded (NEW-4).
7. **Flock transparency portals were not touched.** `I3-T01-C01-G0` stays `n/a (origin refused)`. No archive
   workaround was used anywhere.

---

## 3. Per-cell saturation table

**Columns.**
- Q, F, L = queries, fetches and local operations by I9a, computed mechanically from `query_log_I9a.csv`.
- "Prior" = the owning row's own count and new-sequence from I3 §3 or I6 §3.
- The status vocabulary is I2 §5.4. Sweep status uses the combined sequence (prior + I9a).

### I3 cells — P1

| Cell | Prior Q (seq) | I9a Q/F/L | I9a new seq | Cands | Closing status |
|---|---|---|---|---|---|
| T06-C05-G0 | 0 (blocked) | 4/10/0 | 2,0,0,0 | 8 | **saturated** |
| T06-C01-G0 | 1 (0) | 6/6/0 | 1,0,1,0,0,0 | 3 | **saturated** |
| T01-C05-GS (enum) | 0 | 4/4/2 | 1,1,1,0 | 3 | **enumerated(6 found / 2 negative / 0 not-reached on the LAPPA posting shortlist + 2026 laws)**. Found: CA (C014), UT (C013), WA (C036), NE (report posting, C011), MN (I3-C039), VA (I3-C044). Negative (posting): OR (policy duty, no posting found, Q048), NC (policy duty only, Q032). Not checked: CT and KY posting clauses. |
| T01-C04-GS (enum) | 5 (1,2,0,4,0) | 8/12/1 | 1,0,1,1,1,1,1,1 | 7 | **enumerated(LAPPA's 11 aggregate-report jurisdictions: 10 reached / 1 not-reached [USVI, territory → I5])**. Found: NE (C011), VT (C012), AL (C020 lead), AR (C032 lead), NC (C033 blocked), OK (dup SRC-007); I3 had MN, VA, NH, MD, CA, NJ. Beyond LAPPA: IL (C019), NM (C037, future-dated), WA (C036). |
| T01-C11-GS (enum) | 1 (1) | 10/17/0 | 3,0,0,0,0,2,1,2,0,1 | 11 | **enumerated(8 found / 1 negative / 1 found-without-origin / not-reached: states "to consider next session" IN, NV, OH, UT; SC H4013 status)**. Found: WA, NM, OR, CT, KY (2026); ID (2025); MO EO; FDOT memo. Negative: IL (no 2026 enactment, F034). Without origin: TX governor's order. |
| T01-C07-G0 | 15 (…1,0,1) | 6/5/0 | 1,0,1,0,0,1 | 3 | **extended, capped-unsaturated** (6 of 7 extension queries used; the last still yielded a tier-A AR origin). Search engines ignored `site:boarddocs.com` / `site:granicus.com` (Q035/Q036). |
| T01-C15-G0 | 4 (0,0,3,1) | 3/0/0 | 0,0,0 | 0 | **saturated**. Every remaining project is an OSM/DeFlock viewer or WiGLE-RF-derived. |
| T03-C13-G0 | 3 (0,0,0) | 1/2/0 | 0 | 0 | **saturated, with a caveat**: MuckRock/DocumentCloud stay blocked (not re-tried); no alternative released-records corpus surfaced. |
| T01-C01-G0 | 0 | 0/0/0 | — | 0 | **n/a (origin refused)**: Flock portals, not touched. |

### I3 cells — P2

| Cell | Prior Q (seq) | I9a Q/F/L | I9a new seq | Cands | Closing status |
|---|---|---|---|---|---|
| T01-C14-G0 | 2 (3,1) | 4/3/0 | 1,1,0,0 | 2 (+C028 out-of-cell) | **saturated** |
| T07-C03-G0 | 2 (7,1) | 2/1/0 (Hub API) | 0,0 | 0 | **saturated**. Page 2 of "police cameras" and "public safety cameras" were all dup or out-of-class. |
| T03-C16-G0 | 2 (1,0) | 1/1/0 | 0 | 0 | **saturated** |
| T04-C02-G0 | 0 (blocked) | 2/1/0 | 0,0 | 0 | **saturated**. EDGAR excluded (P16, NEW-4). |
| T05-C02-G0 | 0 (blocked) | 3/3/0 | 2,0,0 | 2 | **saturated** |
| T01-C02-G0 | 1 (0) | 2/0/0 | 0,0 | 0 | **saturated**. Flock is private; the other vendors' posts are marketing. |

### I3 cells — P3 (probes, budget permitting)

| Cell | I9a Q | seq | Status |
|---|---|---|---|
| T01-C12-G0 | 1 | 0 | closed (I3's probe 1 + this 0) |
| TRES-C04-GS | 1 | 1 | **capped-unsaturated** (1 of 3; MN RTCC bill, C051) |
| TRES-C05-GS | 1 | 0 | closed (NY registry bills never enacted) |
| TRES-C07-G0 | 1 | 0 | closed |
| TRES-C01-G0, TRES-C04-G0, TRES-C05-G0 | 0 | — | **not-started (priority)** |
| TRES-C02-G0, T29-C02-G0 | 0 | — | **n/a**: EDGAR (P16); Flock is private |

### I6 cells — P1

| Cell | Prior Q (seq) | I9a Q/F/L | I9a new seq | Cands | Closing status |
|---|---|---|---|---|---|
| C06-G0 | 4 (1,4,0,0) | 4/2/0 | 1,0,0,0 | 1 | **saturated** |
| C06-GP (enum) | 7 | 4/4/0 | 1,0,0,0 | 1 | **enumerated(this row: 3 found [Urbana lead; San Diego and BART current, dup] / 3 negative [Northampton, Lawrence, Medford — no reports found] / 1 blocked [Sebastopol 2026 Ord 1164, 403])**. Still not reached: Santa Clara County currency (lead only), Syracuse (I6 403). |
| C11-GS (enum) | 3 | 5/2/0 | 1,0,0,0,1 | 2 | **enumerated, partial**. FRT via the CDT inventory: CO, MD and WA dup I4; UT found (C050); MT lead. UAS: inventory lead only (EPIC, unfetched). CSS: negative (no current inventory). ATE: I6's GHSA/IIHS. |
| C08-G0 | 8 | 0 | — | 0 | I6 `saturated`; not re-worked |

### I6 cells — P2

| Cell | Prior Q | I9a Q/F/L | I9a new seq | Cands | Closing status |
|---|---|---|---|---|---|
| C04-G0 | 0 | 3/1/0 | 1,0,0 | 1 | **saturated** |
| C04-GS (enum) | 0 | 2/2/0 | 2,0 | 2 | **enumerated(MD found C047; FL blocked C048; MN dup; TX and WA found-lead; VA = I6-C040)** |
| C07-G0 | 0 | 2/0/0 | 0,0 | 0 | **saturated**. Negative: no public tenant directories for BoardDocs, IQM2 or CivicPlus. |
| C08-GS (enum) | 3 | 2/1/0 | 1,0 | 1 | **enumerated(7 found-lead via the vendor page C040 [NY, AR, KY, MD, NM, OH, PA] / 4 negative [GA, TN, SC, IN: no statewide Flock contract])** |
| C09-G0 | 0 | 4/3/0 | 0,2,0,0 | 2 | **saturated** |
| C10-GS (enum) | 4 | 2/2/0 | 1,1 | 2 | **enumerated(AL found C041; VA blocked C049; FL found-lead)** |
| C11-G0 | 2 (0,1) | 2/0/0 (FR API) | 0,0 | 0 | **saturated** |
| C13-G0 | 0 (blocked) | 2/0/0 | 0,0 | 0 | **saturated, with a caveat**: MuckRock/DocumentCloud blocked; no GovQA/NextRequest public archives surfaced. |
| C14-G0 | 0 | 2/0/0 | 0,0 | 0 | **saturated**. The Atlas is still the only multi-class dataset. |
| C16-G0 | 0 | 2/0/0 | 0,0 | 0 | **saturated**. All dup: the DHS PIA hub is I4-C167; LESO is queue SRC-024. |

### I6 cells — P3

| Cell | Status |
|---|---|
| C05-G0 | closed (PowerDMS is registered) |
| C12-G0 | closed (Schmidt v. Norfolk is court metadata only) |
| C12-GS, C05-GS, C01-G0, C15-G0 | not-started (priority) |
| C02-G0 | n/a (EDGAR, P16) |

**Still unsaturated after I9a.**
- `I3-T01-C07-G0`: the agenda sweep is still yielding, especially in tier-A states.
- `I3-TRES-C04-GS`: a P3 probe that yielded.
- Three partial enumerations: `I6-C06-GP` (Santa Clara, Syracuse), `I6-C11-GS` (UAS/CSS per state) and
  `I3-T01-C11-GS` (next-session states).

---

## 4. Candidates by class, channel and geography

**By class.** A row can carry several classes.

| Class | Rows |
|---|---|
| T01 | 32 |
| T03 | 24 |
| T02 | 20 |
| T06 | 14 |
| T04 | 9 |
| T05 | 7 |
| T00 | 4 |
| T11 | 2 |
| T14 | 1 |
| T28 | 1 |

**By finding channel** (the cell's channel).

| Channel | Rows |
|---|---|
| C11 legislation | 13 |
| C05 policy/programme | 11 |
| C04 statutory report | 11 |
| C01 vendor portal | 3 |
| C07 agenda | 3 |
| C06 CCOPS | 2 |
| C02 vendor disclosure | 2 |
| C10 grants | 2 |
| C09 procurement | 2 |
| C14 civil data | 2 |
| C08 contract vehicles | 1 |

**By geography.**
- National: 11 rows.
- FL 4.
- CA, MN, WA, NM, AR and NC: 3 each.
- 2 each: IN, UT, CT, IL, AL, OH, TX, KY, MD.
- 1 each: RI, NE, VT, OR, MO, ID, IA, NY, WI, VA.

**Families.**

| Family | Rows |
|---|---|
| FAM-PREG-PAGES (camera-registry programme pages) | family `C001` + targets `C004`–`C009`, `C021` |
| FAM-ALPR-STATUTE-2026 | 11 publisher rows |
| FAM-AGENDA-ALPR-NONLEGISTAR | `C035` + `C034`, `C052` |
| FAM-FUSUS-DEPLOY | `C038` + `C039` |
| FAM-CA-SB34 | `C014` |
| FAM-UT-ALPR-POLICY | `C013` |

### Ranked shortlist (for I7)

Ranked by gap closed, origin grade and independence. Vendor and journalism rows rank below origins.

| # | Candidate(s) | Why | Gap |
|---|---|---|---|
| 1 | **C036** WA AGO Registered ALPR Systems | Statutory, statewide, agency-level operator list with a policy per agency; a precondition to operating | I1#1, I1#4 |
| 2 | **FAM-ALPR-STATUTE-2026**: C015, C016, C017, C024, C025, C031, C026, C027 (+C030 inventory) | Refreshes the 2022 seed past LAPPA 2025 (SIG-INGEST-049f); adds executive instruments | I1#4 |
| 3 | **C011** Nebraska Crime Commission ALPR reports | 89 per-agency statutory reports, some naming the vendor | I1#4, I1#1 |
| 4 | **C019** Illinois State Police ALPR transparency page and annual reports | State-run network of 808 cameras, per-county counts, named vendor contract | I1#1, I1#4 |
| 5 | **C027** FDOT EOM26-01 (+ I3-C003 removal layer) | The first authoritative *removal* signal; basis for a currency lane | I1#1 (NEW-2) |
| 6 | **C012** Vermont DPS annual ALPR reports | Tier-A VT; statewide unit counts and out-of-state request counts | I1#4, VT |
| 7 | **C037 / C032 / C033** NM DPS reports; AR Highway Police statistics; NC SBI DOT-ROW pilot | Report duties in gap states (NM tier B, AR tier A) plus a state DOT-ROW ALPR programme (NC) | I1#4, NM, AR |
| 8 | **C014 / C013** CA SB 34 and UT posted-policy families | Enumerable per-agency postings for two whole states | I1#4, I1#1 |
| 9 | **C001 / C003 / C021 / C038 / C039** registry programmes and Fusus deployments | T06/T05 programme facts across many agencies and 3 platforms SIG lacks | I1#2, I1#5 |
| 10 | **C043 / C044 / C041 / C049 / C040** grant, earmark and contract-vehicle channels | Per-agency LPR/RTCC project text and state contract ids | I1#6 |

Also notable:
- `C046`: UWCHR, WA Flock sharing with US Border Patrol (T03).
- `C034`: Des Moines, Motorola LPR on body-worn and in-car cameras via Sourcewell 101223-MOT.
- `C042`/`C022`: the Austin ALPR audit and the TRUST Act resolution.
- `C050`: Utah's FR report duty.
- `C047`: the Maryland mandated-reports deposit.

---

## 5. Movement against the I1 blind spots

| Blind spot | Rows | What moved |
|---|---|---|
| I1#4 statutory and ordinance reporting | 28 | Five new state reporting or posting channels (NE, VT, IL, WA, and MD as the deposit); three future or unpublished duties (NM, AR, UT FRT); seven 2026 instruments; two new CCOPS-type jurisdictions (Austin, Urbana) |
| I1#1 ALPR origins beyond the Flock mirror | 18 | WA registry, IL state network, NE reports, agenda targets (Des Moines, Haskell AR), and the FDOT removal signal |
| I1#2 private-camera programmes | 12 | Registry-programme family and platforms (Polaris CameraKit, Genetec Clearance, Axon Fusus Connect sites) |
| I1#10 sharing | 8 | Border Patrol sharing (C046); state repositories (AL registry rule C020; VT database; NM sharing limits) |
| I1#5 RTCC | 5 | — |
| I1#6 procurement and grants | 5 | — |

**Gap states.**
- Tier A:
  - VT: C012.
  - RI: C006.
  - AR: C032, C052, C040.
  - Leads only: WV (Huntington contract), WY (Jackson), MS (Jackson), ME (Lewiston/York; Lincoln ME PD policy on
    PowerDMS).
- Tier B:
  - NM: C016, C037, C040.
  - ND: lead only (Minot, 2026-01).

---

## 6. Negatives (coverage facts)

- **Ring and Flock "Community Requests"**: no public list of participating agencies. `Q004`, `Q007`.
- **CommandCentral Community**: no agency listing. `Q021`.
- **Vendor disclosure**: no Genetec, ELSAG or Rekor customer disclosure found. Motorola's CommandCentral Aware release
  names no customer. `Q053`, `Q070`.
- **Illinois**: no 2026 ALPR enactment; four bills died. `F034`, ISACo 2026-08-18.
- **Texas**: no written order found for the governor's Flock funding halt; spokesman statement only. `Q033`.
- **Massachusetts CCOPS towns**: no annual reports found for Northampton, Lawrence or Medford. `Q026`, `F038`.
- **Cell-site simulator statutes**: no current inventory. `Q045`.
- **State camera-registry statutes**: none enacted; NY bills 2011–2021. `Q093`.
- **Statewide Flock contracts**: none found in GA, TN, SC or IN. `Q077`.
- **Agenda platforms**: BoardDocs, IQM2 and CivicPlus publish no tenant directories. `Q061`, `Q064`.
- **Records portals**: no GovQA or NextRequest public archive surfaced. `Q058`, `Q066`.
- **Repositories**: no Zenodo, Dataverse or figshare multi-class dataset. `Q078`.
- **Federal Register**: no "real-time crime center" documents since 2024. `Q081`.

---

## 7. Part VIII hazards (counts only; no content copied)

**Flags on candidates.**

| Flag | Rows |
|---|---|
| `private-registrant-location` (registry and integration programmes; programme facts only) | 12 |
| `private-person-name` (agenda minutes) | 2 |
| `home-address` (Polaris registrant fields, C002) | 1 |
| `plate-level` + `per-search-audit` + `operator-identifier` (Wausau plate-lookup tool built on audit logs, C045; metadata only) | 1 row, 3 flags |

**Verdicts.** 2 `block` (C002, C045) and 12 `flag`.

**Hazards met but not captured as data.**
- The Spokane County network-audit CSV (per-search rows) was not fetched.
- The released Flock audit logs behind the UWCHR, Wausau and Have I Been Flocked work: only institution-level facts
  are used (C046).
- Skagit Superior Court held Flock images to be public records (2025, reaffirmed 2026-04-17; journalism lead). Any such
  release is plate-level and is never a feed.
- Flower Mound's second private-camera layer (`cameraspublish`, described "Private camera locations as provided to the
  PD") is token-secured (`F077`, HTTP body 499). Only its Hub title is public. Contrast the public I3-C085 hazard.

**Not copied into any committed file:** plates, operator ids, search reasons, registrant names or addresses, officer
names from audit data, staff names or e-mail contacts (the WA AGO contact, ADECA and ITD staff), or network addresses
shown on Cloudflare block pages. A self-check regex over the CSVs found no e-mail or IPv4 address.

---

## 8. INACCESSIBLE list (host · status · time · fetch id)

No host was retried after a refusal, and no user-agent was changed (R4). See NEW-5.

**403 and 406.**

| Host | Fetch | Time (Z) |
|---|---|---|
| scottsdaleaz.gov | F001 | 19:00:28 |
| ocso.com | F005 | 19:00:35 |
| richfieldmn.gov | F006 | 19:00:36 |
| polaris.cameraregistry.net (default Apache page) | F008 | 19:01:25 |
| edinamn.gov (Cloudflare) | F009 | 19:01:26 |
| genetec.com | F013 | 19:02:03 |
| blog.ring.com | F014 | 19:02:04 |
| spokanecounty.gov | F025 | 19:08:47 |
| sebastopol.municipal.codes | F033 | 20:14:36 |
| ecode360.com | F039 | 20:16:48 |
| sos.mo.gov | F046 | 20:17:58 |
| ij.org (Cloudflare 1010) | F047 | 20:18:34 |
| webservices.ncleg.gov (F050 was the R4 lapse) | F049, F050 | 20:21:32 |
| hialeahfl.gov | F054 | 20:23:15 |
| media.rivcocob.org (406) | F055 | 20:23:16 |
| losaltosca.gov (Cloudflare 1010) | F056 | 20:24:33 |
| waghn001.substack.com | F057 | 20:24:34 |
| delraybeachfl.gov | F065 | 20:28:40 |
| wausaupilotandreview.com | F071 | 20:33:07 |
| bart.gov (origin of queue row SRC-018) | F072 | 20:33:08 |
| dos.myflorida.com | F074 | 20:33:58 |
| heatreward.com | F076 | 20:35:13 |
| aclum.org (I6 reached it earlier) | F079 | 20:37:42 |

**Challenge pages.** landline.media (F035, 20:14:39), littlerock.gov (F082, 20:40:12).

**Transport failures.**
- `ncc.nebraska.gov`: DNS failure (F015). Read via WebFetch instead (F019–F021).
- `cga.ct.gov`: TLS failure (F027). Read via WebFetch (F030, F042).
- `ipmnewsroom.org`: TLS failure (F040). Not retried.

**Not machine-readable.** The FDOT EOM26-01 PDF is image-only (F045). No OCR tool is available locally, and WebFetch
could not read it either.

**Not called (P16).** sec.gov / EDGAR (Q072).

---

## 9. Open questions for I7 and the operator

1. **Statute seed.** Should the seed be refreshed from the 2026 origins (NEW-1)? Should executive instruments (the MO
   EO, the FDOT memo) get their own instrument type?
2. **Currency / end-event lane (NEW-2).** Should the FDOT removal layer (I3-C003), contract cancellations (IJ, blocked)
   and council terminations downgrade a site's "active" state?
3. **WA AGO registry (C036).** Does the page's lack of terms text (privacy notice only) allow a facts-lane ingest of
   agency names, dates and policy links? This is an HG-03 packet.
4. **EDGAR (NEW-4).** Does the operator approve a project contact string? Until then, EDGAR-dependent vendor-disclosure
   cells stay closed.
5. **Duties to register now (SIG-INGEST-050).** NM DPS reports (first due on or after 2027-04-01); AR AHP statistics;
   UT FR reports; AL LPR registry and annual report.
6. **Snippet-only facts to verify at I7.**
   - CT PA 26-14 retention terms.
   - MO EO 26-18 text (sos.mo.gov 403).
   - The FDOT memo text (OCR).
   - Urbana's ordinance.
   - Austin's final ordinance.
   - MN HF 3198 enactment.
   - The Texas order.

---

## 10. Appendix — reproduction

**Scratch directory:** `docs/build/logs/next-phase/I9a/` (gitignored).

| File | What it is |
|---|---|
| `fetch.py` | Plain GET; default urllib user-agent; 1 s pause; writes `raw/<fid>.bin` and `fetch_index.tsv` |
| `hub.py` | ArcGIS Hub dataset search |
| `fr.py` | Federal Register search |
| `txt.py`, `pdfgrep.py`, `pdfpages.py` | Local text extraction |
| `dd.py` | Dedupe grep |
| `ql.py`, `fixlog.py` | Query-log append and fix |
| `cands_01.py`…`cands_17.py` | Candidate rows |
| `gen.py` | Writes both CSVs |
| `stats.py` | Per-cell table and self-checks |
| `findings_gen.py` | Writes `findings/incoming/I9a.csv` |

**Self-checks (all passed, `stats.py`).**
- Every candidate has a fetch or local-op line, and every id it cites exists in the log.
- Every log line carries `cell=`.
- `cand_id`s are unique.
- No `rights_lane` says `decided`.
- No e-mail or IPv4 address in the committed CSVs.
- Every `run_at` comes from `date -u` or a tool timestamp. The two upper-bound corrections are noted in §2.
