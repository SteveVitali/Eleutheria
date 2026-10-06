# I5 — Geography gaps: deep web research

This is row **I5** of `META_PLAN.md` §6, Stream I, Stage P. Owner class **R**: read-only web research.

- **Authoring.** Claude Code (Opus 5.5) wrote this row in the planning worktree on branch
  `claude/next-phase-planning` (HEAD `07657ccb` at authoring). Research ran 2026-09-30T17:58:55Z → 18:44Z, with every
  time taken from `date -u` or `fetch_index.tsv`.
- **Protocol.** `design/I2-source-search-protocol.md` (I2). Its I5 brief is §10 and its cells are the 53 `I5-*` rows of
  `data/search_matrix.csv`.
- **Outputs.** Four files, and nothing else was written or committed:
  - this note;
  - `data/candidates_I5.csv`: 225 candidates, §8.6 plus the I2 §7.3 columns;
  - `data/query_log_I5.csv`: 396 lines;
  - `findings/incoming/I5.csv`: NEW-1…NEW-8.
- **Scratch.** Raw captures sit under `docs/build/logs/next-phase/I5/` (gitignored). Each is keyed by fetch id, with
  its sha256 in `fetch_index.tsv`.

**Evidence classes (P1).** Every factual sentence cites one of these:
- a fetch or query id (`I5-F###` / `I5-Q###`): `live-read` of bytes this row fetched;
- a local operation (`I5-L###`);
- a repo `file:line`.

Search-engine snippets were used only as leads. Anything inferred is labelled *(inference)*.

---

## 1. Summary

- **Budget.** The row used **150 of 150 queries**:
  - 40 WebSearch;
  - 110 catalog or API queries: ArcGIS Online/Hub, Socrata, CKAN, Legistar, Opendatasoft, data.europa.eu, UK
    Parliament WQA, SUTRA.

  It also used **223 of 250 fetches** and 23 local operations. It produced **225 candidates**: 202 `new`, 21
  `related:`, 2 `same-as:`. By level they are 134 channel, 80 target, 7 publisher and 4 family. Part VIII verdicts:
  191 pass, 30 flag, 4 block.
- **The operator's suspicion is partly confirmed.**
  - SIG *is* missing entire geographies, but mostly because it never looked:
    - **Five of the 12 states without a DOT source** have key-free camera layers: VT, MI, DE and WV are state-origin,
      and NM's publishing account still needs its authority verified. TX has a TxDOT-origin layer.
    - **Puerto Rico and the US Virgin Islands** have findable legislation, procurement or deployment channels.
    - **Every one of the 36 thin cities** now has an identified open-data and/or agenda channel.
  - What is truly dark is narrower:
    - **MS, SC, NH, ME, WY and AR** have no key-free DOT surface. NH, ME and VT are keyed through newengland511. AR is
      token-secured. MS is POST-only.
    - **American Samoa and the Northern Mariana Islands** have no public channel found.
    - **Most tribal nations** have none either.
    - **UK and NZ ANPR camera locations** are withheld by policy, so only counts are reachable.
- **Headline candidates:**
  - DelDOT FirstMap cameras: 445, updated daily (I5-C003).
  - MDOT MiDrive: 681 (C002).
  - VTrans: 88 CCTV (C001).
  - A TxDOT-origin ITS layer: 4,243 CCTV (C008). It answers the `dot_511_tx` provenance question and surfaces TxDOT's
    no-redistribution licence text (finding NEW-3).
  - Detroit Project Green Light: 1,134 (C101).
  - Clark County LVMPD Metrocams and ShotSpotter layers (C104).
  - The Nashville ALPR council reports (C100).
  - Puerto Rico's 2026 legislative investigations into face recognition, ALPR and biometrics (C228/C229), and its
    contract register (C226).
  - NZ Police's annual ANPR-platform audits, which cover the Auror and SaferCities public-private networks (C301).
  - The UK Parliament Written Questions API as the national count channel for UK ANPR and LFR (C345).
- **Registry defects surfaced (findings).** Two mis-attributed Legistar tenants hide agenda coverage for Charlotte NC
  and San Bernardino County (NEW-1, NEW-2, S2). There is a TxDOT rights tension on an already-flipped republish
  (NEW-3, S2). Further tenant labels are wrong, unresolved or truncated (NEW-4), and an NCDOT authority
  misclassification (NEW-5).
- **Row status: `in-progress (budget-exhausted)`.** All 3 P1 cells were enumerated, but two still have not-reached
  items: C03-GL1 has 2 (Lincoln and St. Petersburg, both access failures) and C07-GL1 has 3 (Henderson, Virginia Beach
  and St. Petersburg, also access failures). A shared WebSearch cap was exhausted at 18:15Z (NEW-8), which left 12
  P2/P3 cells below `q_min`. Per I2 R11 the recommendation is a top-up split, **I5a-2** (US, §11).

---

## 2. Method and deviations

**Protocol followed.** The I2 rules R1–R11, the §5.4 stopping rules, §6 inclusion, the §7 capture procedure
(including §7.6 mechanical dedupe with `dedupe.sh`) and the §8 query-log format.

**Execution: one row, five writers into scratch, one merger.** The row owner split I5's 53 cells into four
**non-overlapping sub-parts**, each run in its own fresh context under a shared brief (`BRIEF.md`, scratch). Each part
had disjoint id ranges (`RANGES.txt`), and the owner merged and validated the results (`merge.py`, 0 errors).

| Part | Scope (cells) | Query ids | Fetch ids | Candidates |
|---|---|---|---|---|
| A | US states: `T08-C03-GD` (P1), `T08-C03-G0`, `T00-C03-GD`, `CRES-GD`, GL4 (`C03`/`C07`/`C05`/`CRES`) | Q001–Q043 | F001–F067 | C001–C042 |
| B | 36 thin cities, GL1 (`C03`/`C07` P1; `C05`/`C09`/`C04`/`C13`/`C14`/`CRES`), plus GL2 (OKC first) | Q046–Q090 | F076–F153 | C100–C168 |
| C | Counties (GL3) plus territories and tribal nations (GT) | Q091–Q112 | F156–F190 | C200–C242 |
| D | International: GI1, GI2, GI3, GIW | Q113–Q146 | F191–F227 | C300–C367 |
| owner | inventory, local operations, verification top-ups | Q044, Q045, Q147–Q150 | F068, F246–F250 | C400–C402 |

This is a deviation from "one fresh context per row" (P12). It was chosen to keep each context within the R11 guard.
The cell partition is exact: each I5 cell was owned by one part. Budgets were sub-allocated: A 45/75, B 45/80, C 22/35,
D 34/55, owner 4/5. The unused part ids were re-used by the owner and are logged as such.

**Fetching.** Every GET went through `fetch.sh`, a curl wrapper. It:
- sends the honest documented UA `sig-planning-research/0.1 (+https://sig-project.org/data-collection)`, modelled
  on `connectors/src/connectors/net.py:61,154`;
- holds a per-host lock of 1 request per second;
- caps each host at 25 requests per row, or 40 for documented catalog APIs;
- saves raw bytes and records the sha256;
- adds any host that answers 403, 429 or a challenge page to a stop-list.

The WebFetch tool was not used, so every capture is byte-exact and hashed. Wayback and other mirrors were never used.

**P16 (coordinator rule; it arrived after the 18:44:04Z `date -u` reading, when all sub-parts had finished).** The rule forbids sending the operator's
e-mail, name or any personal identifier to an external service. The owner audited this row's traffic after the fact:
- The only contact string sent was the project URL in the UA above. It identifies no person.
- None of the 333 requested URLs in `fetch_index.tsv` contains an e-mail address or a personal name. A grep for the
  operator's name found only false hits on the place name "South Kesteven".
- No service that requires a contact string was called: no SEC EDGAR, and no keyed or registration-gated API.
- Every capture in `raw/` has an entry in `fetch_index.tsv`, so no request bypassed `fetch.sh`.

The sub-workers were dispatched before P16 existed. None is still running, and no further workers were dispatched.

**Deviations and constraints, in full:**
1. **WebSearch cap.** From 18:15:04Z the WebSearch tool refused further calls ("session cap 200/200"). I5 had issued
   40, so the cap is evidently shared across the parallel I3–I6 wave *(inference)*. About 8 searches were refused
   and got no id. After that, parts worked through catalog APIs, site-scoped search endpoints, Atlas-citation leads
   and fetch probes. Cells left below `q_min` are listed in §3 (finding NEW-8).
2. **ArcGIS search cap.** The per-row cap of 40 for `www.arcgis.com` (sharing search) was reached at about 18:22Z.
3. **Challenge-detector false positives.** Five hosts answered HTTP 200 with genuine pages but were stop-listed
   because the page source contains the word "captcha", for example a reCAPTCHA script tag: dot.ri.gov,
   tarrantcountytx.gov, stat.stpete.org, dashboard.plano.gov and virginislandsdailynews.com. The tool failed closed.
   - After reviewing the raw bytes (I5-F026), the owner un-stop-listed **dot.ri.gov only** (`unstoplist_log.txt`) and
     fetched `cameras.js` once (I5-F246).
   - The other four remain stop-listed. The rule was never applied to a real challenge.
   - One missed challenge (statewatch.org, a JS interstitial) was stop-listed by hand.
4. **Stopping-rule deviations:**
   - `I5-T00-C04-GI1` ran 9 queries against a `q_max` of 8.
   - `I5-T00-C11-GT` ran 5 against a `q_max` of 3. These were cheap on-origin SUTRA phrase searches, and the last one
     was still yielding.
   - `I5-T00-C08-GI1` ran 1 query against a `q_min` of 2; its channels were verified by direct fetch instead.
5. **Local-operation timestamps.** For L001, L002 and L004, `run_at` is the output file's birth time (a tool
   timestamp). L003 was read before a stamp was taken, so its `run_at` is the `date -u` reading at hashing. All of
   this is recorded in the log's `notes`.
6. **Part VIII harmonisation.** The owner raised I5-C014 from `flag` to `block`, because I2 §7.4 says
   operator-identifier ⇒ block. This makes it consistent with I5-C104. In both cases the trigger is a GIS
   editor-tracking column, which is an open question for I7 (§10).
7. **Q-20.** D1 Q-D1-13 (operator place priorities) was unanswered when this row ran, so the I2 §4 weights ordered the
   work.

**Scope boundary (dispatcher instruction and I2 R7).** I5's US cells are **multi-class** and cover channel identity.
Class-specific channels that the brief lists belong to other rows:
- state ALPR statutes and reports → I3 `T01-C04/C11-GS`;
- CCOPS → I6 `C06`;
- state procurement and grants → I6 `C08/C10-GS`;
- fusion centres → I4 `T27`.

I5 issued **no** queries in those cells. When such sources surfaced while following I5's own results (including the
Atlas-citation snowball, which I2 §5.7 assigns exclusively to I5 for tier-A/B states, GL1 cities and territories),
they were captured with `out-of-cell→` / `handoff→` tags: 19 candidates, handed to I3 ×19, I6 ×10, I4 ×5. Every
per-geography row in §4 lists those hand-offs.

---

## 3. Cell coverage (all 53 I5 cells)

`q/f/new` are computed mechanically from the `cell=` and `new=` fields of `query_log_I5.csv`. Closing statuses use the
I2 §5.4 vocabulary.

| Cell | Tier | q | f | new | Cands | Closing status |
|---|---|---|---|---|---|---|
| I5-T08-C03-GD | P1 | 24 | 46 | 14 | 16 | **enumerated(7 found / 2 lead-only / 4 negative / 0 not-reached)** over the 12 no-DOT states plus TX. Found: VT, MI, DE, WV, NM, TX-origin, RI (names only). Lead-only: AR (token), MS (POST, C400). Negative: SC, NH, ME, WY. Tier-C light pass: NV, CT (T09), NE found; AK, OH, WI, NJ, OK, IN negative |
| I5-T00-C03-GL1 | P1 | 29 | 41 | 54 | 40 | **enumerated(31 found / 3 negative / 2 not-reached)**. The owner top-up resolved Newark and Winston-Salem and confirmed Frisco and Hialeah as weak negatives. Lincoln and St. Petersburg are unreachable or stop-listed |
| I5-T00-C07-GL1 | P1 | 11 | 13 | 9 | 16 | **enumerated(33 found / 0 negative / 3 not-reached)**: Henderson, Virginia Beach, St. Petersburg (access) |
| I5-T00-C03-GD | P2 | 8 | 0 | 7 | 7 | enumerated(8 searched / 4 identified via AGOL / 3 not-reached: NH, RI, DC). 0 surveillance datasets in any state portal |
| I5-T00-C04-GI1 | P2 | 9 | 14 | 10 | 10 | capped-unsaturated (q_max overrun by 1) |
| I5-T00-C05-GL1 | P2 | 0 | 7 | 0 | 4 | capped-unsaturated (fetch-only; below q_min, WebSearch cap) |
| I5-T00-C03-GL4 | P2 | 2 | 6 | 6 | 6 | enumerated(6 found / 11 negative) |
| I5-T00-C07-GL4 | P2 | 3 | 3 | 0 | 2 | enumerated(11 registry-known / 2 new / 3 negative / rest not-reached) |
| I5-T08-C03-G0 | P2 | 3 | 7 | 5 | 5 | capped-unsaturated (the last query still yielded) |
| I5-T00-C03-GL3 | P2 | 4 | 0 | 11 | 11 | enumerated(9 found / 3 negative / 75 not-reached). 0 of 12 counties publish surveillance layers |
| I5-T00-C07-GL3 | P2 | 6 | 13 | 8 | 10 | enumerated(11 found / 1 negative / 75 not-reached; about 30 of the 75 have registry tenants, I5-L301) |
| I5-T00-C09-GL1 | P2 | 0 | 6 | 0 | 4 | capped-unsaturated (fetch-only; below q_min) |
| I5-T00-C03-GI1 | P2 | 5 | 1 | 24 | 24 | capped-unsaturated |
| I5-T00-C08-GI1 | P2 | 1 | 4 | 1 | 4 | capped-unsaturated (below q_min) |
| I5-T00-C13-GI1 | P2 | 2 | 2 | 2 | 4 | capped-unsaturated (WDTK and Right to Know blocked) |
| I5-T00-C05-GL4 | P2 | 1 | 2 | 0 | 1 | capped-unsaturated (below q_min) |
| I5-T00-C04-GI2 | P2 | 2 | 3 | 2 | 2 | capped-unsaturated (both queries yielded) |
| I5-T00-C04-GL1 | P2 | 0 | 10 | 0 | 3 | capped-unsaturated (fetch-only; below q_min) |
| I5-T00-C14-GI1 | P3 | 1 | 0 | 0 | 0 | saturated |
| I5-T00-C03-GI2 | P3 | 1 | 3 | 13 | 13 | capped-unsaturated (one multilingual data.europa.eu query, 148 hits) |
| I5-T00-C05-GL3 | P3 | 1 | 1 | 1 | 1 | enumerated(1 found / 1 negative / 3 not-reached) |
| I5-T00-C09-GL3 | P3 | 1 | 2 | 2 | 2 | enumerated(2 found / 3 not-reached) |
| I5-T00-C14-GL1 | P3 | 0 | 0 | 0 | 0 | not-started(budget: WebSearch cap) |
| I5-T00-C03-GL2 | P3 | 6 | 1 | 1 | 4 | enumerated(4 found / 3 not-reached) |
| I5-T00-C07-GL2 | P3 | 2 | 2 | 0 | 0 | enumerated(OKC same-as `okc_council`; Gilbert and Chandler negative on Legistar; Irving not-reached) |
| I5-T00-C14-GI3 | P3 | 1 | 2 | 1 | 2 | capped-unsaturated |
| I5-T00-C13-GL1 | P3 | 0 | 0 | 0 | 0 | not-started(budget) |
| I5-T00-C08-GI2 | P3 | 1 | 1 | 1 | 1 | capped-unsaturated |
| I5-T00-C14-GI2 | P3 | 1 | 0 | 0 | 0 | saturated |
| I5-T00-C09-GT | P3 | 0 | 2 | 0 | 2 | capped-unsaturated (below q_min, WebSearch cap) |
| I5-T00-C11-GT | P3 | 5 | 1 | 7 | 8 | extended/capped (q_max overrun by 2; still yielding) |
| I5-T00-C16-GT | P3 | 0 | 11 | 0 | 3 | capped-unsaturated (below q_min; tribe count enumerated at origin) |
| I5-T00-C07-GI1 | P3 | 1 | 2 | 1 | 1 | blocked(access) (ModernGov tenants 403) |
| I5-T00-C03-GT | P3 | 2 | 1 | 0 | 1 | saturated |
| I5-T00-C13-GI2 | P3 | 2 | 0 | 1 | 1 | capped-unsaturated |
| I5-T00-C08-GI3 | P3 | 1 | 1 | 1 | 1 | capped-unsaturated |
| I5-T00-C04-GL2 | P3 | 0 | 0 | 0 | 0 | not-started(budget) |
| I5-T00-C05-GL2 | P3 | 0 | 0 | 0 | 0 | enumerated(OKC same-as `okcpd_policy`; others not-reached) |
| I5-T00-C09-GL2 | P3 | 0 | 0 | 0 | 0 | enumerated(OKC same-as `okc_procurement`, plus a BidNet tenant from I5-L203; others not-reached) |
| I5-T00-C15-GI1 | P3 | 1 | 1 | 1 | 1 | capped-unsaturated |
| I5-T00-C14-GT | P3 | 1 | 3 | 1 | 4 | capped-unsaturated (Tohono O'odham not reached) |
| I5-CRES-CRES-GD | P3 | 1 | 5 | 1 | 5 | saturated (Atlas snowball gave 4 channels) |
| I5-CRES-CRES-GL1 | P3 | 2 | 0 | 0 | 0 | saturated |
| I5-CRES-CRES-GL3 | P3 | 1 | 1 | 1 | 1 | capped-unsaturated (the probe yielded; no budget to continue) |
| I5-CRES-CRES-GL4 | P3 | 1 | 2 | 1 | 1 | capped-unsaturated |
| I5-CRES-CRES-GT | P3 | 1 | 0 | 0 | 0 | saturated (negative probe) |
| I5-T00-C04-GI3 | P3 | 1 | 0 | 0 | 0 | saturated (no ZA regulator or Vumacam publication) |
| I5-CRES-CRES-GI1 | P3 | 2 | 1 | 2 | 2 | capped-unsaturated |
| I5-CRES-CRES-GI2 | P3 | 1 | 0 | 1 | 1 | capped-unsaturated |
| I5-CRES-CRES-GI3 | P3 | 1 | 2 | 1 | 1 | capped-unsaturated |
| I5-CRES-CRES-GL2 | P3 | 1 | 0 | 0 | 0 | saturated |
| I5-CRES-CRES-GIW | container | 0 | 0 | 0 | 0 | not-started(budget). One GIW item was captured incidentally (C359, Ukraine) |
| I5-CRES-CRES-GL5 | container | 0 | 0 | 0 | 0 | n/a (container; `q_min` 0) |

**Cells below `q_min`** (12): C05-GL1, C09-GL1, C04-GL1, C13-GL1, C14-GL1, C05-GL4, C08-GI1, C09-GT, C16-GT,
C04-GL2, C05-GL2 and C09-GL2. Most of them are explained by the WebSearch cap. None is a P1 cell.

---

## 4. Per-geography results: gap → candidates found → saturation

The "gap" column is the I1 measurement (`research/I1-source-coverage.md` §3–§5). The candidate ids are rows of
`data/candidates_I5.csv`.

### 4.1 Tier-A/B states (I2 §4.2): DOT/511, state portal, largest localities, Atlas snowball

| State (w) | I1 gap | DOT/511 (T08-C03-GD) | State portal (C03-GD) | GL4 localities | Atlas-snowball / out-of-cell (hand-off) | Saturation |
|---|---|---|---|---|---|---|
| VT (0.85) | no DOT/CCTV; 16 Atlas rows; no Flock portal | **found**: C001, VTrans ITS DeviceList. The groupBy gives 88 CCTV and 3 "AI" of 390 ITS devices (I5-F004); state-origin; NEW-2 pass. newengland511 is keyed (`dot_511_targets.toml:445-451`) | C025 data.vermont.gov (Socrata; 0 camera) | Burlington: CivicClerk tenant already in the registry; the BWC directive link returns 404 (F050) | the VIC fusion centre and the Barre PowerDMS portal are unfetched leads (→I4-T27) | T08 closed; C05 unsaturated |
| NH (0.82) | no DOT/CCTV/GSD/FRT; no Flock portal | **negative**: newengland511 keyed; AGOL Q002/Q009 and web Q020 found nothing | not reached | Concord: C041, Legistar `concordnh`, mislabelled as Concord CA (NEW-4). Manchester: CivicClerk tenant already in the registry | C029, Governor & Council agendas (503; state contracts and grants →I6); NHIAC (→I4) | T08 negative (keyed only) |
| DE (0.78) | no DOT/CCTV; its dossier is 24 German cameras (I1 NEW-1) | **found**: C003, FirstMap "Traffic Devices – CAMERA", **445** (I5-F011), daily. Also C004, a TMC feed of 360 cameras with stream URLs on a *staging* host, and C005, 60 red-light cameras (T09 → I3/I4 class) | C026 data.delaware.gov (0 camera) | Wilmington and Dover: no channel beyond a 2016 hub | **C028, DSP 2022 Annual Report**: BWC, LPR, RTCC, drones, FRT case counts, red-light events, DIAC (→I6 report series; I3/I4 classes) | T08 closed |
| MS (0.78) | weakest state (3 sources) | **negative for GET**. **C400**: MDOTtraffic loads cameras through an ASP.NET `PageMethods.LoadCameraData` call (F248), which is POST by framework convention *(inference)*. The terms (F249) grant "non-commercial short-term … revocable use" but also say information "is considered in the public domain" | C020 opendata.gis.ms.gov; data.ms.gov is not Socrata (Q025) | Jackson: CivicClerk tenant already in the registry; no portal | aclu-ms.org BWC policy compilation (unfetched lead →I4) | T08 lead-only (POST); dark for key-free GET |
| RI (0.72) | no DOT/CCTV/FRT | **partial**: C011, RIDOT metro camera page with 61 views and **no coordinates**. The owner's check of `cameras.js` (F246) found only a video-popup helper | not reached (RIGIS) | Providence: C034 GIS hub; **C033, PPD 2023 Annual Report** (Flock, camera-monitoring unit, Ring, speed and red-light, PHA cameras, Accurint/Skopenow); IQM2 connection failed | C031 RI AG BWC grant release (403 →I6); C032 student Flock layer (token-gated →I3) | T08 partial (names only) |
| WV (0.72) | no DOT/CCTV | **found**: C009 WVDOH CCTV, 73 (state server; NEW-2 pass). C010 WV Turnpike CCTV, 15 (**NEW-2 fail**: points near lat 0). wv511 robots unretrievable | IIJA hub (unverified lead) | Charleston: CivicClerk tenant already in the registry | — | T08 closed (partial: 73 against an unfetched claim of ~167) |
| ME (0.67) | no DOT/CCTV/GSD/RTCC/PREG | **negative**: newengland511 keyed; MaineDOT hub `q=camera` returns 0 (Q029, C024) | C024 MaineDOT Data Hub | Portland: CivicClerk tenant already in the registry; Augusta: none | WGME I-Team Flock reporting (lead →I3) | T08 negative |
| WY (0.67) | no DOT/CCTV; 38 Atlas rows | **negative**: the wyoroad map config returns 404 (F032). The only layer is a personal-account Cheyenne subset (Q010, non-state) | WyGISC DataHub (unverified) | Cheyenne: C038 CLCGISC hub; Granicus hosts have robots Disallow | — | T08 negative |
| AR (0.56) | no DOT/CCTV | **negative (key-free)**. ARDOT `ITS_Cameras_Public` returns service-not-found and token-required (F058/F060). The IDrive terms reserve all image rights (C012). A consultant snapshot is derived, not origin (C013) | C022 Arkansas GIS Hub (0 camera) | Little Rock: no Legistar client (Q038) | BJA award pages (login-gated; NEW-7) | T08 negative (secured) |
| MI (0.56) | no DOT/CCTV | **found**: C002 MiDrive Cameras, **681** (F006); state-origin; NEW-2 pass. The data was last edited 2021-01-14, so it is stale | C027 data.michigan.gov (0 camera) | Grand Rapids: C035 GRPD dashboard hub. Lansing: CivicClerk tenant already in the registry | C030 DTMB contract (michigan.gov 403 →I6); MSP SNAP FRT policy and MIOC (→I4) | T08 closed |
| HI (0.48, B) | Atlas thin | DOT present (I1) | C023 opendata.hawaii.gov CKAN (0 camera) | Hawaii County: no Legistar client (Q037) | kauai.gov camera-registry lead (→I3) | portal done |
| ND (0.38, B) | no legislation claims | DOT present (I1) | C021 NDGISHub | C037 Bismarck open data; C042 Fargo agendas | MuckRock FR xlsx (→I4/I6); Fargo SafeCam (→I3) | portal done |
| DC (0.34, B) | best-covered city-state | — | not reached (low priority; 1,591 observations already) | — | MPD CCTV rebate, ShotSpotter, UAS pages (→I3/I4) | not-reached |
| MT (0.34, B) | — | DOT present (I1) | MDT portal (unverified) | C039 Billings Public Safety hub | MT DOJ fusion (→I4) | partial |
| NM (0.31, B) | no DOT/CCTV | **found**: C006 "Statewide CCTV View", 186 (F014). The ArcGIS org "ITS511" still needs its authority verified. C007 MRMPO CCTV, 404 | GCC hub (unverified) | Santa Fe: C036 data portal; **C040, 12 park cameras**. Las Cruces: none | NM police chiefs policy host; DPS UAS policy (→I4) | T08 closed |
| SC (tier C, no DOT) | no DOT | **negative**: 511sc.org offers only apps (F015); no AGOL layer (Q011) | — | — | — | T08 negative |
| TX (gated `dot_511_tx`) | points arrive only via a personal republish | **found TxDOT-origin**: C008. The groupBy gives **CCTV 4,243 / DMS 1,680** (F029). The TxDOT org licence text on sibling items reads "Distribution … to third parties without TxDOT's written consent is strictly prohibited" (Q021, Q012) → NEW-3 | — | — | — | resolved as a rights lead |

### 4.2 The 22 no-dossier states (I1 NEW-4, including Oklahoma)

I1 ranks "no dossier" as an **attribution** fix (blind spot #3), not a search gap. Dossiers are built only from
geolocated registry sources, and states such as IN (2 DOT sources) still have none. I5 therefore asked a narrower
question: does a **new official geolocated layer** exist that would feed a dossier once attribution is fixed?

| Outcome | States |
|---|---|
| New official geolocated candidate | MI (C002; Detroit C101–C103), NV (C014 NDOT ITS masterplan, 1,319 CCTV, a static 2024 snapshot; Clark County C104), NM (C006, C040), NE (C016 NDOT plow dash-cams via Iowa DOT, CC-BY-4.0; Omaha C106 parks 37; Lincoln C107 traffic 55), VT (C001), WV (C009) |
| T09 only | CT (C015, work-zone speed cameras) |
| Official surface without coordinates, or not GET-able | RI (C011, names only), MS (C400, POST), AR (token-secured) |
| Negative | AK (only a MatSu Borough 511 republish), ME, NH, NJ (DOT; city portals C136/C401 found), ND (portals only), MT (hub only), OH (only a Marysville OHGO republish), OK, SC, WI, WY, IN (the INDOT ITS layer has no cameras, F061) |

**Oklahoma (the pilot).**
- The state has no key-free DOT layer.
- The OKC open-data portal has no surveillance layers: C165 found 0 "camera" items against 8 "police" items.
- `okc_council` is still correctly `verified=false`: the anonymous CivicClerk API returns 404 and the portal SPA serves
  (F136/F137).
- OKC's policy and procurement channels are already registered (`okcpd_policy`, `okc_procurement`).
- The OKC gap is attribution (NEW-4) plus the Flock-at-origin blind spot, which belongs to I3. It is not a missing
  local channel.

### 4.3 The 36 thin top-100 cities (GL1), in weight order

Every city has a first-pass C03 and C07 outcome. "reg" means a tenant already in `agenda_tenants.toml` (as `related:`).
"census" means an `agenda_tenants.toml` `[[platform_census]]` Granicus/NovusAgenda/IQM2 host (I5-L202). "nr" means
not reached.

| City (I1 sources) | Open-data portal | Agenda platform | Other channels | Surveillance evidence found | Hand-offs | Saturation |
|---|---|---|---|---|---|---|
| Jersey City NJ (2) | C136 Opendatasoft, 1,536 datasets; bundle 0 (Q089) | C124 CivicWeb | C134 BidNet | none | I6 (NJ AG ALPR audit) | C03/C07 done |
| North Las Vegas NV (2) | negative (Q048/Q055) | reg PrimeGov `cityofnorthlasvegas` | city site 403 (F117) | C104 (Clark County ShotSpotter extent likely overlaps; *inference*) | I3 | access-dark |
| Cape Coral FL (2) | C149 Hub | census NovusAgenda | — | none | I3 (Lee County LPR interlocal) | done |
| Durham NC (2) | C148 Hub | C125 CivicPlus AgendaCenter | — | none (ShotSpotter page 404) | — | partial |
| Omaha NE (2) | C150 DOGIS Hub | C129 clerk.omaha.gov + Laserfiche | **C114 OPD ALPR report** (LEAD-ONLY, 403) | C106 (37 cameras) | I6 (NE ALPR reporting) | partial |
| Lincoln NE (2) | unreachable (F101) | census Granicus (ambiguous slug) | — | C107 (55 traffic cameras) | — | partial |
| Anchorage AK (2) | C151 OIT CSV page | C130 muni.org SharePoint | — | none | I4 (drone ordinance lead) | partial |
| Charlotte NC (2) | C137 Hub | **C116, Legistar `charlottenc`, mislabelled Charlotte IA (NEW-1)** | — | C116: DFR programme, red-light pilot | I4, I3 | done |
| Memphis TN (2) | C138 Hub (camera 0) | C131 memphistn.gov | — | none (SkyCop reporting not reached) | — | partial |
| Indianapolis IN (2) | C139 Hub (camera 0) | census Granicus | — | none | — | partial |
| Frisco TX (3) | weak negative (Q147) | C127 OnBase (reg PrimeGov `friscotexas` may be stale) | BidNet negative | none | I3 (SafeCam) | partial |
| Tulsa OK (3) | C140 Hub (camera 0) | census Granicus | reg `dossier_tulsa` / SRC-002 | none new | — | partial |
| Wichita KS (3) | C141 Hub | census Granicus | — | none | — | partial |
| Norfolk VA (3) | C142 Hub (camera 0) | reg CivicClerk | — | none | I3 (Hampton Roads Flock layer) | partial |
| Greensboro NC (3) | C143 Hub | census Granicus | — | LPR parking hint (person-level; excluded) | I3 | partial |
| Chesapeake VA (3) | C144 Hub | census Granicus | — | none | I3 | partial |
| Virginia Beach VA (3) | C145 Hub (camera 0) | nr (city site unreachable, F122) | — | none | I3 | access-dark |
| Boise ID (3) | C146 Hub | census IQM2 | — | C108 camera partnership (**block**: registrant rows) | I3 | partial |
| Henderson NV (3) | C147 Hub | nr (403, F123) | — | C109 CAPTURE programme (**block**) | I3 | access-dark |
| St. Petersburg FL (3) | stop-listed (false positive, F108) | Legistar negative (Q062) | annual report 404 | none | — | access-dark |
| Hialeah FL (3) | weak negative (Q148) | C126 CivicPlus | C132 BidNet | none | — | partial |
| Irvine CA (3) | C152 Hub | census Granicus | — | none | I6 (AB 481) | partial |
| Newark NJ (3) | **C401 NewGIN Open Data** (owner top-up) | C117, Legistar `newark` resolved to Newark NJ | BidNet negative | C117: ShotSpotter (Sourcewell), ALPR pole cameras | — | done |
| Plano TX (3) | C153 Socrata | census NovusAgenda | — | none | I3 (Community Camera Program) | partial |
| Tampa FL (3) | C154 Hub | C128 OnBase | — | none | I3 (Project REC) | partial |
| Honolulu HI (3) | C155 Hub | census Granicus | C112 HPD policy pages (ALPR) | — | — | partial |
| Anaheim CA (3) | C156 Hub | census Granicus (the L001 tenant is a school district) | C113 Lexipol manual | — | I6 (AB 481) | partial |
| Madison WI (3) | C157 Hub | reg Legistar + C121 | via C121: annual surveillance-technology reports | C121 | I6 | partial |
| Winston-Salem NC (3) | **C402 MapForsyth** (owner top-up) | reg Legistar + C119 | C133 BidNet; C135 RFP | C119: RTCC contract, cameras, Flock, ShotSpotter, DFR | I3 | done |
| Nashville TN (3) | C158 Hub (camera 0) | reg Legistar + C123 | **C100 ALPR council reports 1–3** | C100, C123 | I6 (`ccops_nashville`) | good |
| Cleveland OH (3) | C159 Hub | reg Legistar + C118 | — | **C105 UAS dashboard**; C118 (Flock renewal, ShotSpotter, Ring repeal) | I4 (UAS) | good |
| St. Paul MN (3) | C160 Hub | reg Legistar + C120 | — | C120 | I6 (MN BCA) | partial |
| Detroit MI (3) | C161 Hub | reg Legistar (0 matters since 2022) + eScribe | C115 BOPC; OpenGov (reg, WAF) | **C101 Project Green Light, 1,134**; C102 ShotSpotter incidents, 40,689 (aggregate lane); C103 Street View CCTV, 7,977 | I3 | good |
| Albuquerque NM (3) | C162 ABQ Data | reg Legistar + C122 | C111 APD SOP manual (ALPR SOP 1-22) | C122 | I3 (Community Connect) | partial |
| Las Vegas NV (3) | C163 Hub (camera 0) | reg PrimeGov | — | **C104 LVMPD Metrocams 95 / ShotSpotter 100** (Clark County GISMO) | I3 | partial |
| Houston TX (3) | C164 Hub + CKAN (0) | census NovusAgenda | C110 HPD general orders | none | — | partial |

**GL2 (OKC first).**
- OKC: C165 (above).
- Gilbert (C166) and Chandler (C167): hubs found; neither is on Legistar.
- Arlington TX: C168 hub; census Granicus.
- Fort Wayne: registry CivicClerk.
- Lubbock: Legistar returns 500, not provisioned. Irving: not reached.

The surveillance-layer negatives above come from single-term Hub site searches (`q=camera`), because Hub search does not
support OR (Q071). They are **weak negatives**.

### 4.4 Top counties (GL3)

The 12 largest non-consolidated counties were attempted; the other 75 were not reached. The L004 matcher was loose, and
the registry-read L301 shows about 30 of those 75 already have tenants.

**Result: no county publishes camera, ALPR, RTCC or drone layers on AGOL (Q098).**

| County | Candidates (channel) | Negatives / notes |
|---|---|---|
| Harris TX | C210 open data; C222 Bonfire; **C224 Flock renewal** (about 480 LPRs; →I3); Legistar tenant already in the registry, with its label truncated (NEW-4) | HCSO policy manual not online |
| Maricopa AZ | C202 AgendaOnline; C217 Regional GIS (restrictive licence); C221 MCSO policies; C223 BidNet | Legistar `maricopa` is the City |
| Orange CA | C203 BoS agendas | no county open-data hub |
| Miami-Dade FL | C204 govaction hub | not Socrata; no hub |
| Dallas TX | C205 CivicWeb; C211 hub | — |
| Riverside CA | C209 agendas (LEAD-ONLY, 403); C212 GIS; C220 Corona city cameras (→I3) | rivcocob.org blocked |
| Clark NV | C200 (Legistar `clark` = the county; `same-as`); C213 hub | — |
| Tarrant TX | C206 agenda PDFs; C214 portal | host stop-listed on a false positive |
| San Bernardino CA | **C201: Legistar `sanbernardino` is the County (NEW-2)**; C215 open data | Flock MSA lead (→I3) |
| Bexar TX | C207 AgendaCenter; C216 portal; BidNet already in the registry | SafeCam lead (→I3) |
| Santa Clara CA | C218 Socrata | agenda platform unresolved; LPR expansion lead (→I3) |
| Wayne MI | C208 committee pages (Granicus OpenCities) | no hub |

### 4.5 Territories and tribal nations (GT; I5 owns all classes)

| Geography | I1 gap | Candidates | Negatives / why dark | Saturation |
|---|---|---|---|---|
| US-PR | OSM 166 points; 13 Atlas rows | **C228/C229**: RC0787 and RS0604, legislative investigations into agency and municipal face recognition, ALPR, biometric and AI surveillance (filed 2026-09-01 and 2026-09-18, per the SUTRA search results). C227 SUTRA tracker. C230–C233 (traffic-light cameras, CCTV mandate, port surveillance, electronic monitoring of bail). **C226 OCPR Registro de Contratos** (all agencies; yearly bulk files). C238 BJA ALPR award (login-gated). C240 datos.pr.gov (in maintenance, LEAD-ONLY). C242 CPI (LEAD-ONLY, 403) | the PR Police ArcGIS server holds crime incidence only; datos.pr.gov is in maintenance (F187) | legislation strong; open data blocked |
| US-VI | 3 Atlas rows | C235 ShotSpotter journalism (VIPD, 2025-12-10; →I4); C236 DPP contract page (LEAD-ONLY, 403) | legislature and open data not probed (WebSearch cap) | partial |
| US-GU | 2 Atlas rows | C241 legislature (LEAD-ONLY; JS interstitial) | AGOL 0 hits (Q105); GPD and GSA not reached | near-dark |
| US-AS | nothing | none | Atlas 0 rows (L302); AGOL 0 hits (Q105); the Fono, DPS and procurement were not probed | **DARK** |
| US-MP | nothing | none | Atlas 0 rows; AGOL 0 hits. The Mariana Regional Fusion Center is known only from an Atlas GU row | **DARK** |
| Tribal nations (aggregate) | no source of any status | **C225 BIA Tribal Leaders Directory**: **601 rows = 577 "Tribe" + 24 "Affiliate"** (F184). The BIA landing page states 575 (F173); only non-person fields were read. C237 DOJ CTAS; C238 BJA awards (login-gated, NEW-7) | the Atlas has 140 tribal rows across 111 agencies in 26 states (L302), 95 of them BWC rows whose citations point to login-gated BJA pages; no tribal surveillance layers on AGOL (Q106); BIA OJS pages list districts, not agencies (F185/F190) | capped-unsaturated |
| Specific nations | — | **C234** (ICT/Wisconsin Examiner): Lac du Flambeau (160+ camera network), Oneida Nation (4 Flock cameras), Lac Courte Oreilles (Flock), St. Croix. C239 LCO statement (403) | Tohono O'odham (CBP towers) not reached → I4-T28 with a tribal-geography note | first-pass |

### 4.6 International (GI1–GI3)

| Country / region | I1 gap | Channels found | Negatives / blocked | Saturation |
|---|---|---|---|---|
| UK (`ISO:GB`) | about 17 ad-hoc layers; `uk_surveillance_camera_commissioner` live (P31: consume_existing); no ANPR source | C303 Scottish Biometrics Commissioner (FRT volumes); C307 ICO; **C345 Parliament WQA API** (national ANPR/LFR counts); **C310 data.gov.uk CKAN family → C311–C323** (13 council CCTV layers, including Barnet T09 and contracts); C335 Contracts Finder (OCDS); C344 council CCTV annual report; LEAD-ONLY: C308 Met LFR records (403), C309 National ANPR Service notice (403), C340 WhatDoTheyKnow (403), C342 ModernGov (403) | BBW LFR tracker (Q130); no published SWP/Essex LFR table found (Q121) | capped-unsaturated; **ANPR is counts only** |
| Canada (`ISO:CA`) | about 18 camera registries; no national channel | C304 OPC special report (2021 baseline); C334 federal contracts search; **C338 ATI completed-request summaries** (JSON) | open.canada.ca CKAN 0 (Q122, syntax caveat); no 2024–25 provincial IPC LPR/FRT report surfaced (Q114) | capped-unsaturated |
| Australia (`ISO:AU`) | 7 local | C305 OAIC; **C324 data.gov.au family → C325 Townsville CCTV register**, C326–C331, C332 QLD DJAG camera inventory; C336 AusTender OCDS; C343 OzWatch (OSM viewer); C341 Right to Know (403) | OAIC determinations index curl error | capped-unsaturated |
| New Zealand (`ISO:NZ`) | 3 local | C300 NZ Police emergent-tech releases; **C301 ANPR platform audits** (2022/2024/2025/2026; F192); **C302 ANPR camera counts** (locations withheld under OIA s6(c)); C337 GETS; C339 FYI.org.nz | data.govt.nz CKAN (Incapsula challenge) | capped-unsaturated |
| Ireland | 1 local | C306 Oireachtas FRT bill brief; C333 Dublin traffic CCTV | eTenders curl error | capped-unsaturated |
| EU/EEA | `ted_eu` live (not redone) | **C348 data.europa.eu search API** (148 datasets across about 15 portals) → ES C349/C361, IT C347/C353, SI C354/C360, FR C355, PT C356, DE C357/C362, NO C358, CH C350–C352; NL **C346 Camera in Beeld** (a police-run private-camera registration programme, the analogue of US PCAM registries; LEAD-ONLY) and C363 national Algoritmeregister | Nordic, BE and AT statutory registers not reached; Statewatch blocked | capped-unsaturated |
| Rest of world | coarse only | CO C364 SECOP II (Socrata, 1,196 video-surveillance processes); BR C365 O Panóptico; IN C366 IFF Panoptic; AR C367 SRFP judgment; UA C359 (incidental) | ZA: no Information Regulator or Vumacam publication (Q141); MX, CL, JP, KR, TW, SG, IL, AE, KE, NG, PE, PH, TH, MY, ID, SA **not searched** (budget) | P3 capped |

---

## 5. Candidates by class, channel and level

- **Level:** 134 channel · 80 target · 7 publisher · 4 family.
  - The families are C227 (PR SUTRA), C310 (UK data.gov.uk), C324 (AU data.gov.au) and C348 (data.europa.eu).
  - The publishers are C028, C033, C108, C109, C343, C365 and C366.
- **Publisher type:** gov-open-data 123 · agenda 30 · procurement 18 · statutory-report 12 · other 11 ·
  legislation 10 · records-release 6 · journalism 4 · grant 3 · ngo 2 · academic 1 · crowdsourced 1 · court 1.
- **Technology class** (a candidate may carry several): T00 111 · T07 CCTV 67 · T01 ALPR 37 · T08 DOT 24 · T11 FRT 19
  · T09 ATE 12 · T23 BWC 11 · T14 UAS 10 · T13 GSD 8 · T06 PCAM 7 · T05 RTCC 6 · T03 6 · T10 5 · T02 5 · T27 2 ·
  T12 2 · one each for T17, T18, T19, T22, T24.
- **Format:** arcgis 79 · html 50 · ckan 26 · other 21 · pdf 17 · api 17 · bulk-file 9 · socrata 6.
- **Registry match:** new 202 · related 21 · same-as 2. There are 0 P31-owned rows; C344 is `related:` the UK SCC row.
- **LEAD-ONLY:** 23 in total: access-blocked, POST-only, login-gated, or a duty with no publication found.

---

## 6. Ranked shortlist

Ranking weighs four things: the gap closed (P1 cell and state or city weight first), independent origin, structure
(API or layer beats PDF), and a low Part VIII burden. It is a planning order for I7, not an `acq-score/1` score. I7
scores.

| # | Candidate | Gap it closes | Why |
|---|---|---|---|
| 1 | **I5-C003** DelDOT FirstMap Traffic Devices – CAMERA (445, daily) | I1#5; DE (w 0.78). Replaces the contaminated DE dossier (I1 NEW-1) with real Delaware points | state-origin ArcGIS layer; `dot_511:arcgis_query` reuse |
| 2 | **I5-C002** MDOT MiDrive Cameras (681) | I1#5; MI (w 0.56); a no-dossier state | state-origin, key-free. Stale since 2021, so freshness needs checking |
| 3 | **I5-C001** VTrans ITS DeviceList (88 CCTV) | I1#5; VT, the highest-weight state (0.85) | state-origin; the only structured VT camera source (newengland511 is keyed) |
| 4 | **I5-C008** TxDOT ITS devices (4,243 CCTV) | `dot_511_tx` gated; TX points arrive via a personal republish | the origin layer exists; the TxDOT licence text needs HG-03 review (NEW-3) |
| 5 | **I5-C101** Detroit Project Green Light (1,134) | I1:city=Detroit (no official registry) | city-origin programme layer (PCAM, →I3 class); points are flagged by business type |
| 6 | **I5-C104** Clark County LVMPD Metrocams (95) + ShotSpotter (100) | I1:city=Las Vegas / North Las Vegas | county-published layers; ShotSpotter sensor areas are otherwise secret. **block** (editor ids) until a field-drop rule is set |
| 7 | **I5-C100** Nashville ALPR council reports 1–3 (117 cameras) | I1:city=Nashville; I1#4 | public route to the reports behind the gated `ccops_nashville`; usage aggregates |
| 8 | **I5-C228/C229** PR RC0787 / RS0604 | I1#14; US-PR | the first multi-class PR source; a CCOPS-like legislative inquiry |
| 9 | **I5-C301** NZ Police ANPR-platform audits (annual) | I1#11; NZ | national public-private ANPR aggregates (Auror/SaferCities). NZ Police copyright is restrictive |
| 10 | **I5-C345** UK Parliament Written Questions API | I1#11; the UK ANPR gap | the only national count channel where locations are withheld; keyless API |
| 11 | I5-C226 PR OCPR Registro de Contratos | I1#14; PR procurement | all-agency contract register; the bulk files contain natural persons (flag) |
| 12 | I5-C348 data.europa.eu search API | I1#11; EU/EEA | one keyless API over about 15 national portals, yielding 12 targets |
| 13 | I5-C310 data.gov.uk CKAN CCTV family (13 layers) | I1#11; UK local | council CCTV layers, including contracts |
| 14 | I5-C006 NM Statewide CCTV (186) | I1#5; NM | the "ITS511" org's authority must be verified first |
| 15 | I5-C009 WVDOH CCTV (73) | I1#5; WV | state-origin but partial |
| 16 | I5-C014 NDOT ITS devices (1,319 CCTV) | NV keyed 511 | key-free static snapshot (2024) |
| 17 | I5-C028 DSP 2022 Annual Report | DE multi-class | a state report series (→I6); covers FRT, UAS, BWC, LPR and RTCC |
| 18 | I5-C033 Providence PD 2023 Annual Report | RI multi-class | Flock, ATE, Ring, PHA cameras, Accurint (→I3/I4) |
| 19 | I5-C225 BIA Tribal Leaders Directory | I1#14; tribal spine | an enumerated `US-TRIBAL` label set (601 rows) |
| 20 | I5-C234 ICT/Wisconsin Examiner tribal surveillance | I1#14; 4 tribes | the first tribal-geography deployment evidence (journalism; facts only) |
| 21 | I5-C105 Cleveland Police UAS dashboard | I1:city=Cleveland | flight-level transparency; ODbL share-alike |
| 22 | I5-C116 / C117 / C118 / C119 Legistar matters (Charlotte, Newark, Cleveland, Winston-Salem) | GL1 agendas | contract and approval evidence; `procurement:legistar` reuse |
| 23 | I5-C017 NCDOT_Cameras (1,157) | NC (registry misattribution, NEW-5) | state-owned org, currently recorded as a non-state mirror |
| 24 | I5-C338 Canada ATI summaries (JSON) | I1#11; CA national | the first Canadian national records channel |

---

## 7. Movement against the I1 blind spots

- **#5 Official camera and DOT registries.**
  - The 10 tier-A states without a registry now resolve as follows: 5 have a key-free official candidate (VT, MI, DE,
    WV, RI names-only), and 5 are dark (NH, ME and WY keyed or absent; MS POST-only; AR token).
  - Of the 2 extra no-DOT states, NM is found and SC is dark.
  - TX origin is resolved as a rights lead.
- **#9 Thin cities.** All 36 now have a documented open-data and/or agenda channel. New surveillance-specific evidence
  exists for Detroit, Las Vegas/North Las Vegas, Nashville, Cleveland, Charlotte, Newark, Winston-Salem, Omaha,
  Lincoln, Albuquerque, Madison and St. Paul. Two I1 zeros turn out to be registry labelling errors (NEW-1 Charlotte;
  NEW-4 Newark, Concord).
- **#11 International.**
  - National or discovery channels were found for the UK (counts), NZ (audits and counts), AU, CA, IE and EU/EEA
    (data.europa.eu).
  - GI3 has project-level FRT trackers (BR, IN) and national procurement (CO).
  - Most of Asia, the Middle East and Africa were not searched.
- **#14 Territories and tribal.** PR goes from "OpenStates only" to legislation plus procurement channels. VI gets its
  first deployment evidence. A tribal geography spine now exists, with the first evidence for 4 tribes. AS and MP
  remain dark.
- **#4 Statutory and ordinance reporting** (out-of-cell, handed off): the DSP annual report (DE), the Nashville ALPR
  reports, the Madison surveillance-technology reports, the Omaha ALPR report (403), and the PR legislative
  investigations.
- **#3 Attribution** (not a search cell): I5 adds evidence that some apparent geography gaps are registry labelling
  defects (NEW-1, NEW-2, NEW-4), not missing sources.

---

## 8. Where no public source exists (or none was reachable), and why

| Geography | Status | Evidence of the search | Why |
|---|---|---|---|
| NH, ME (and VT's 511 feed) | no key-free DOT surface | newengland511 is keyed (registry `dot_511_targets.toml:445-451`); MaineDOT hub returns 0 (Q029); AGOL Q002/Q003/Q009 | tri-state Iteris 511 needs an API key (HG-09 operator act) |
| MS | no GET-able camera layer | Q007, Q015, Q031, Q025; F247–F249 | the data is served by a POST page method (C400) |
| SC | none | Q011, Q017; F015 | 511sc.org offers apps only |
| WY | none official | F032 (404), Q010 | only a non-state personal-account subset |
| AR | token-secured | F058, F060; C012 terms | ARDOT service requires a token; images all-rights-reserved |
| RI | names without coordinates | F026, F246 | HTML camera list only; streams via `getStreamUrl.php` |
| American Samoa, Northern Mariana Islands | **dark** | Atlas 0 rows (L302); AGOL 0 (Q105) | no public channel surfaced; legislatures, police and procurement not probed (WebSearch cap) |
| Guam | near-dark | Q105 0; legislature behind an interstitial (Q108) | access |
| Most tribal nations | dark | Q106, F185, F190; L302 | no tribal-published surveillance layers; the BJA award evidence behind the Atlas's tribal rows is login-gated (NEW-7); tribal data sovereignty |
| UK ANPR, NZ ANPR (locations) | withheld by policy | C302 (OIA s6(c)); C345 counts; F194 (403) | national security and policing policy: **counts only** |
| South Africa (Vumacam) | no official source | Q141 | no regulator publication; journalism only (unfetched) |
| County surveillance layers (top 12) | none published | Q098 | counties publish channels (agendas, procurement), not device layers |
| Access-dark cities: North Las Vegas, Henderson, Virginia Beach, St. Petersburg, Omaha PD | **not proven absent** | F117, F123, F122, F108, F125 | 403, WAF or unreachable. These are access gaps, not coverage facts |

---

## 9. Part VIII hazards (counts and categories only; no content)

- **Verdicts.** 191 pass · 30 flag · 4 block.
- **Flags.** private-person-name 12 · free-text-narrative 7 · residential-intersection 6 · tribal-sovereignty 5 ·
  private-registrant-location 4 · officer-name (institutional role, in reports) 3 · operator-identifier 2 ·
  home-address 2 · confidential-facility 1 · rf-derived-candidate 1.
- **Blocks:**
  - **C108 Boise** and **C109 Henderson** private-camera registration services: registrant rows are residents'
    homes. Only a published programme count is admissible.
  - **C104 Clark County** and **C014 NDOT**: GIS editor-username columns (operator-identifier).
- **No rows were read from any flagged or blocked source.** Only `?f=json`, `returnCountOnly` and `outStatistics`
  metadata were read, plus one SECOP `count(*)`. For the BIA directory, only name, component, region and state were
  queried. Leader names, phones and e-mails were not pulled.
- **A scan of the committed CSVs and the part notes found no e-mail addresses or phone numbers.** No plates, operator
  ids, search reasons, student data or home addresses were copied.
- **Hazards I7 and I8 must design for:**
  1. **ArcGIS editor-tracking fields** (`created_user`, `last_edited_user`) appear on many agency layers. I7 should
     decide whether a field-drop at extraction allows re-verdicting them to flag (C014, C104).
  2. **Infrastructure-security fields.** These are not Part VIII categories: `NETWORK_ADDRESS` (C001), `Phone_Number`
     (C009) and live stream URLs (C004). Exclude them at extraction.
  3. **Share-alike licences.** Cleveland UAS (ODbL) and Detroit Street View (CC BY-SA 4.0) may need a compartment
     decision like the OSM one (§42.3).
  4. **Incident-level datasets** are an aggregate lane only: C102, Detroit ShotSpotter CAD records.
  5. **PR OCPR bulk files** list natural-person contractors. Use metadata only, filtered by entity.
  6. **Tribal sovereignty.** Every `US-TRIBAL` candidate is flagged. Publication needs a tribal-data-governance
     decision.
  7. **Minor-data adjacency.** C234 reports tribal police access to school cameras (→ I4 class; block any student
     data).
  8. **Jurisdiction-conditional publication** (SIG-PUB-017) applies to every GI candidate, and each one notes its
     regime (UK-GDPR/DPA 2018, GDPR+LED, PIPEDA and provincial, Privacy Act 1988 (Cth), NZ Privacy Act 2020, LGPD,
     POPIA …). NZ Police copyright says it is "illegal to reproduce or distribute copyrighted material without the
     permission of the copyright owner" (C301).
  9. **Foreign private-camera registries:** Camera in Beeld (C346) gives aggregate counts only, never registrant
     locations.

---

## 10. INACCESSIBLE list (host · status · first run_at · what was sought)

**403, WAF or challenge; host stop-listed:**
- met.police.uk · 403 · 18:08:16Z · Met LFR deployment records.
- find-tender.service.gov.uk · 403 · 18:08:16Z · National ANPR Service notice.
- catalogue.data.govt.nz · Incapsula challenge · 18:10:08Z · NZ CKAN.
- rivcocob.org · 403 Cloudflare · 18:10:46Z · Riverside BoS agendas.
- whatdotheyknow.com · 403 · 18:11:41Z · UK FOI ANPR responses.
- righttoknow.org.au · 403 · 18:11:41Z · AU FOI corpus.
- chichester.moderngov.co.uk · 403 · 18:12:28Z · ModernGov ANPR item.
- democracy.merton.gov.uk · 403 · 18:12:19Z · ModernGov ANPR item.
- statewatch.org · JS interstitial (stop-listed by hand) · 18:13:15Z · Trento DPA coverage.
- dpp.vi.gov · 403 · 18:17:28Z · USVI ShotSpotter contract.
- lco-nsn.gov · 403 Wordfence · 18:17:36Z · LCO statement on Flock.
- cityofnorthlasvegas.com · 403 · 18:18:29Z · agenda link.
- periodismoinvestigativo.com · 403 · 18:18:42Z · CPI PR reporting.
- cityofhenderson.com · 403 · 18:19:08Z · agenda platform.
- police.cityofomaha.org · 403 Akamai · 18:20:21Z · OPD ALPR report.
- michigan.gov · 403 · 18:20:25Z · DTMB contract; MSP SNAP FRT policy.
- riag.ri.gov · 403 · 18:20:31Z · RI AG BWC grant release.

**Stop-listed on false positives** (HTTP 200 genuine page; left stop-listed except dot.ri.gov):
- tarrantcountytx.gov (18:10:47Z).
- stat.stpete.org (18:15:20Z).
- dashboard.plano.gov (18:15:22Z).
- virginislandsdailynews.com (18:20:11Z).
- dot.ri.gov (18:12:10Z). Un-stop-listed; F246 fetched at 18:39:36Z.

**Login- or token-gated:**
- bja.ojp.gov/funding/awards/* · redirect to /user/login · 18:17:29Z.
- gis.ardot.gov · 499 token required · 18:22:55Z.
- services4.arcgis.com/2s7f6roC5RgpcJkx (RI Flock project layer) · 499 · 18:24:57Z.
- api.mdottraffic.com · login (not touched).

**Unreachable, 404, 5xx, or maintenance:**
- sos.nh.gov · 503 · 18:20:20Z.
- caltrans-gis.dot.ca.gov, gisdata.dot.ca.gov · connection failure · 18:14:36Z.
- providenceri.iqm2.com, sccgov.iqm2.com · connection failure or no DNS.
- map.wyoroad.info · 404 · 18:14:06Z.
- the DelDOT production TMC feed · not found (exists on the staging host only).
- opendata.lincoln.ne.gov, ags3.lincoln.ne.gov · curl error.
- virginiabeach.gov · curl error · 18:19:02Z.
- www.oaic.gov.au determinations index · curl error.
- geofiles.be.ch, agi.dij.be.ch · curl error.
- etenders.gov.ie · curl error.
- datos.pr.gov · maintenance redirect · 18:19:06Z.
- guamlegislature.gov · JS interstitial · 18:18:44Z.
- Legistar 2026 attachment hyperlinks (legistar1) · 404 · 18:26:53Z (NEW-6).

**Tool caps:**
- WebSearch · session cap 200/200 · from 18:15:04Z (NEW-8).
- www.arcgis.com · per-row cap of 40 reached · about 18:22Z.

---

## 11. Open questions for I7 and the operator

1. **Row completion (R11).** The P1 cells have 5 not-reached items, all of them access failures, and 12 P2/P3 cells are
   below `q_min` because of the shared WebSearch cap. Recommend **I5a-2**, a US-only top-up of about 40 queries once search capacity exists:
   - GL1 C05/C09/C04/C13/C14;
   - the GT legislatures and procurement for GU, VI, AS and MP;
   - Tohono O'odham;
   - GL4 policy manuals;
   - the NH, RI and DC portals.

   International top-ups (C08-GI1; MX, CL and PNCP; GIW) would form **I5b-2**.
2. **HG-09 keyed 511 feeds.** newengland511 (VT/NH/ME), AK, CT, WI, PA, FL, OH and NV (registry). Would an operator
   key act unlock more than any public layer can? MS (POST) and AR (token) also need an operator-reviewed access
   decision.
3. **TxDOT rights (NEW-3).** Does the TxDOT no-redistribution text govern the location facts in C008 and in the flipped
   `camreg_txdot_rep_tx`? This is an HG-03 packet item. No decision is made here.
4. **NM "ITS511" authority** (C006) and **DE production vs staging** (prefer C003 over C004): both must be settled
   before any `dot_511_nm` or `dot_511_de` row is written.
5. **Tribal denominator and key.** The BIA directory has 577 Tribe rows plus 24 Affiliate rows, but the landing page
   says 575. Which is canonical, the Federal Register list (not fetched) or the directory? What short `US-TRIBAL` key
   should be used?
6. **Editor-tracking fields** (§9.1): should a field-drop rule be adopted, with a re-verdict?
7. **Count-only claims.** Confirm that SIG models UK and NZ ANPR **count claims with no geometry** (C302, C345).
8. **Discovery connectors.** Should the catalog-of-catalogs APIs (data.europa.eu C348; CKAN C310/C324; Hub site
   search) become discovery connectors, always ingesting from the origin portal?
9. **New agenda-platform families.** Should Maricopa AgendaOnline, OC ocagendaext, Miami-Dade govaction, Dallas CivicWeb
   and Jersey City CivicWeb get connector work? They cover counties #4, #6, #7 and #8.
10. **The four remaining false-positive stop-listed hosts** (§10): may a later row fetch them?

---

## 12. Self-check (I2 §9)

| Check | Result |
|---|---|
| Every candidate has a fetch line: `found_by_query_id` ids all exist in `query_log_I5.csv` | **pass** (`merge.py`, 0 errors) |
| Every query line starts `cell=` with an I5 cell | **pass** |
| Every P1/P2 cell has ≥ `q_min` queries or an honest status | **pass with exceptions**: 12 cells are below `q_min` and carry honest statuses (§3). No P1 cell is among them |
| `cand_id`s unique; 32 columns per row | **pass** (225 rows) |
| `registry_match` computed with I2 §7.6 (`dedupe.sh`) | **pass** |
| No plate, operator id, audit officer name, search reason, student datum or private address in committed files | **pass** (scan for e-mails and phones: 0; the flagged sources were not read) |
| `rights_lane` never says `decided`; every licence prefixed `guess:` | **pass** |
| Every date from `date -u` or tool timestamps; Q/F `run_at` equal to `fetch_index.tsv` | **pass** (mechanical); local-operation deviations are disclosed (§2.5) |
| Budget | queries **150/150**; fetches **223/250** |

## Appendix: reproduction

- **Merge and validation:** `docs/build/logs/next-phase/I5/merge.py`. It checks the 32-column schema, the id ranges,
  uniqueness, that every log id is present in `fetch_index.tsv`, that `run_at` equals the fetch index, and the cell
  membership of every line.
- **Raw bytes:** `docs/build/logs/next-phase/I5/raw/<id>.bin`, with sha256 in `fetch_index.tsv` (333 entries =
  110 API queries + 223 fetches). Status counts: 279 × 200 · 19 × 404 · 15 × 403 · 7 × 500 · 1 × 503 · 1 × 400 ·
  11 curl errors.
- **Local operations:**
  - L001: agenda-tenant map for GL1 (`agenda_tenants.toml` sha256 `f59ccb2b8fe1`).
  - L002: Atlas I5-partition domain mine (`atlas.csv` `dcbf8bc13d14`).
  - L003: `dot_511_targets.toml` `171a3d741fcf`.
  - L004: county list (`sub-est2024.csv` `af9cd4835c93`).
  - Part-local reads: L101–L105, L201–L207, L301–L303, L401–L404.
- **Part notes** (scratch, with fuller per-item detail): `docs/build/logs/next-phase/I5/{A,B,C,D}/notes.md`.
