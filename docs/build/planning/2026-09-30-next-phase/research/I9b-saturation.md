# I9b — Search saturation pass: technology classes (I4) and geography gaps (I5)

Row **I9b** of `META_PLAN.md` §6 (Stream I, Stage P). Owner class R (web research). The run happened in two sessions:
- The first ran from 2026-09-30T18:57:25Z and stopped on a usage limit at 19:10:37Z (`session.log`, scratch).
- The resume session ran from 20:12:11Z. This note was written at 20:58Z (`date -u`).

Planning worktree, branch `claude/next-phase-planning`; HEAD was `a4db7228` when this note was written. Nothing was committed by this row.

The row wrote only four files:
- this note;
- `data/candidates_I9b.csv`;
- `data/query_log_I9b.csv`;
- `findings/incoming/I9b.csv`.

Scratch (gitignored) is under `docs/build/logs/next-phase/I9b/`.

**Inputs read:**
- `META_PLAN.md`: §3 (P1–P16), the Stream I section (I1–I9, I7), §8.2 and §8.6.
- `design/I2-source-search-protocol.md`: §1, §5, §6, §7 and §8–§10.
- `data/search_matrix.csv`.
- The unsaturated-cell lists in `research/I4-other-technologies.md` (§2 and §10.1) and `research/I5-geography-gaps.md` (§3 and §11.1, including I5a-2).
- For deduplication: `data/candidates_I3…I6.csv`, the sibling `candidates_I9a.csv`, `connectors/src/connectors/data/*.toml`, `tasks/src/tasks/data/acquisition_queue.toml`, the six-streams `source-candidates.csv` and `data/source_coverage.csv`. All were read-only.

---

## 1. Summary

**Budget used:**
- **132 query ids**: 119 WebSearch calls plus 13 catalog/API queries (Socrata discovery or SoQL ×5, ArcGIS Hub ×7, Federal Register ×1). Id Q047 was never issued; the numbering simply skips it.
- **143 fetch lines**: 142 byte-exact curl GETs, each hashed, plus one WebFetch retry.
- **111 candidates.**

**Candidates, new against known:**
- Against the registry and queue: **103 `new`**, 8 `related:`, 0 `same-as:`.
- Against I3–I6: 0 exact duplicates were captured. Duplicates were counted in each query's `dup=` and not re-added.
- Several are *related* to I3–I6 rows (same publisher or organisation); these are noted per row for I7.
- By level: 14 channel, 31 publisher, 3 family, 63 target.
- 10 are LEAD-ONLY: the origin was blocked, unreachable or JS-only.
- Part VIII verdicts: 83 pass, 26 flag, **2 block**.

**Coverage movement:**
- **The four I5 P1 not-reached items now resolve.** Lincoln and St. Petersburg (open data) and St. Petersburg and Virginia Beach (agendas) now have identified channels. Henderson is a documented lead via the Nevada state notice site.
- **New state-level report channels:**
  - Florida's statewide red-light-camera report (38 jurisdictions, 10 editions).
  - Pennsylvania's work-zone ATE report.
  - Iowa's HF 2681 ATE permit regime.
  - Texas Gov't Code 423.008 drone reports (a family).
  - Maine DPS drone reports.
  - Maryland State Police cell-site-simulator deployment counts.
  - Minnesota's court-administrator report on interception, pen-register and tracking warrants. This corrects an I4 negative (finding NEW-3).
  - Hawaii's wiretap report.
- **International:**
  - **The Netherlands publishes its national police ANPR camera plan in the Staatscourant**, with about 1,202 geocoded rows. SIG has no equivalent; the UK and NZ withhold ANPR locations.
  - The UK Home Office publishes monthly live-FR deployment CSVs.
  - CanadaBuys and PSPC collaborative vehicles.
  - CNIL enforcement on BriefCam.
- **Territories:** first origin documents for Guam, the US Virgin Islands and the Tohono O'odham Nation. American Samoa remains dark; the Northern Mariana Islands remain near-dark.

**Saturation:**
- Of the 5 I4 P1 cells, two closed saturated or blocked: **T20-C09 saturated** (the last 3 queries yielded 0 new) and **T14-C16 saturated-or-blocked** (the last 4 yielded 0 new; the faa.gov origin still refuses).
- **T19-C09, T25-C07 and T25-C09 remain `capped-unsaturated`.** They keep yielding new *targets* (one agency approval per query). That is unbounded by construction, so §2 applies a channel-level reading.
- Among the I4/I5 P2 cells, 7 closed saturated. The rest are capped with honest statuses (§3).

---

## 2. Method, and deviations from the I2 protocol

- **Resume.** Neither committed CSV existed at resume, but the first session's scratch did:
  - `qlog.csv` held Q001–Q014;
  - `fetch_index.tsv` held F001–F027;
  - `cands/b01–b02.json` held C001–C012.

  All of those rows are kept. The resume continued at Q015, F028 and C013 and repeated no logged query.
- **Fetching** used the first session's `f.py`. It:
  - makes read-only GETs through curl;
  - sends the project User-Agent `sig-planning-research/0.1 (+https://sig-project.org/data-collection)`, which carries no personal identifier (P16);
  - holds 1 request per second per host;
  - caps each host at 25 fetches, or 40 for catalog APIs;
  - stop-lists a host on 403 or 429.

  The row also stop-listed some hosts by hand: 400 on BoardBook, 406 on Finalsite district sites, 405 on the Oireachtas human-verification page, and the Little Rock bot interstitial. No challenge was retried, no mirror or archive was used, and no Flock portal was touched.
- **P16 audit.** No request carried an e-mail, name or other identifier. No keyed or contact-string service was called (no EDGAR). The CSV validator (`build.py`) also scans every committed cell for e-mail-like strings and found 0.
- **Clock (P2).** Every `run_at` comes from `date -u`, or from the fetch tool's own timestamp.
  - WebSearch lines carry the `date -u` reading taken immediately before their batch.
  - The one WebFetch retry (I9b-F143) carries the next `date -u` reading as an upper bound, labelled in its line.
- **Stopping rule (I2 §5.4), with one declared reading.** For the agency-purchase sweeps (C07 and C09 cells), every buying agency is a new `target`, so "new" never reaches zero. The protocol `new=` counts are kept in the log unchanged.
  - The closing status additionally notes whether the last queries yielded any new **channel or publisher**-level candidate. That is the unit that makes a class enumerable at scale.
  - Cells still yielding targets at their q_max close as `capped-unsaturated (target-unbounded)`.
- **Scope (R7).** Queries were issued only under I4 and I5 cells: the P1/P2 cells listed as unsaturated in I4 §10.1 and I5 §3/§11, plus the I5a-2 named P3 items (GT, C13-GL1, C14-GL1) and I4's unsearched T12 probe.
  - Candidates met while following results were captured with `out-of-cell->` tags: I6 cooperatives and grants, I3 ALPR and PCAM, CCOPS.
  - One sweep query (Q032) found only an international candidate. It is logged `new=0` for the US cell and the candidate is tagged for I5-T00-C08-GI1.
- **Deviation 1: the lost query strings of the interrupted run.** Eight fetches (F020–F027, 19:10:30Z–19:10:35Z) were made after searches whose strings were never logged. They are kept and logged with "originating query unrecorded". Five of them support candidates C013–C017. This is disclosed as finding **NEW-6**. No query text was invented.
- **Deviation 2: an unindexed GET.** The first session noted an unindexed test GET of the Little Rock PDF at about 19:02Z, made while its tool was being set up (the `fnotes` entry for F001).
- **Deviation 3: WebFetch.** WebFetch was used once (F143), for a TLS-incompatible host (archive.legmt.gov). It failed and was not retried. No other WebFetch was used.
- **Deviation 4: summary figures.** Figures that appeared only in search-result summaries are never cited as fact. Candidates quote live-read text with a fetch id, and summary figures are labelled "(unverified)" or "lead". This matters; see finding **NEW-5**.

---

## 3. Per-cell saturation table

How to read the columns:
- `q` counts I9b queries (WebSearch/API) in the cell.
- `new seq` is the per-query `new=` sequence, in order.
- `f` counts fetch lines logged under the cell.
- `cands` counts candidate rows whose `cell_id` is the cell.
- "Prior" is the I4 or I5 closing status.

All values are computed by `stats.py` (scratch) from the committed log's `cell=` and `new=` keys.

| Cell | Tier | Prior | q | new seq | f | cands | I9b closing status |
|---|---|---|---|---|---|---|---|
| `I4-T20-C09-G0` SMM purchasing | P1 | capped (3 q) | 12 (10/2) | 1,0,1,0,0,3,0,1,2,**0,0,0** | 17 | 11 | **saturated** (K=3 zero; I4+I9b = 15 = q_max) |
| `I4-T19-C09-G0` forensics purchasing | P1 | capped (10) | 9 | 2,0,2,1,2,0,0,2,1 | 15 | 13 | **extended, capped-unsaturated (target-unbounded)**; channels found late (C024 PO directory, C039) |
| `I4-T25-C07-G0` school-board approvals | P1 | capped (7) | 8 | 1,0,1,0,2,0,1,1 | 16 | 8 | **capped-unsaturated** (I4+I9b = 15 = q_max) |
| `I4-T25-C09-G0` school purchasing | P1 | capped (5) | 8 | 2,1,1,1,2,3,0,1 | 14 | 11 | **capped-unsaturated (target-unbounded)**; 5 cooperative/state vehicles found |
| `I4-T14-C16-G0` FAA waivers | P1 | capped (7) | 7 (5/2) | 0,1,1,**0,0,0,0** | 5 | 2 | **saturated (reachable proxies) / blocked(access)** for the faa.gov origin (NEW-1) |
| `I5-T00-C03-GL1` thin-city open data | P1 | 31 found / 3 negative / 2 not-reached | 3 (0/3) | 0,1,1 | 1 | 2 | **enumerated (33 found / 3 negative / 0 not-reached)**: Lincoln (ArcGIS org; the portal host no longer resolves), St. Petersburg (ArcGIS org; not Socrata) |
| `I5-T00-C07-GL1` thin-city agendas | P1 | 33 / 0 / 3 | 4 | 1,1,0,1 | 3 | 3 | **enumerated (35 found / 0 negative / 1 lead-only)**: St. Petersburg (Revize PDFs), Virginia Beach (Laserfiche eDocs), Henderson (lead-only: NV notice site, TLS failure) |
| `I4-T09-C03-G0` ATE open data | P2 | capped (6) | 2 (0/2) | 0,3 | 4 | 3 | capped-unsaturated (q_max reached) |
| `I4-T09-C04-GS` ATE state reports | P2 | 7 / 2 / 18 | 4 | 1,1,2,0 | 4 | 4 | **enumerated (10 found / 3 negative / 14 not-reached)**: +FL, PA, IA; CO negative |
| `I4-T11-C04-GS` FR state reports | P2 | 5 / 0 / 10 | 2 | 1,1 | 3 | 2 | enumerated (7 found, incl. MT lead-only / 0 / 8 not-reached): +UT (derived), MT (TLS failure) |
| `I4-T11-C16-G0` FR federal | P2 | capped | 2 | 1,1 | 2 | 2 | capped-unsaturated |
| `I4-T13-C04-G0` GSD audits | P2 | capped | 3 | 0,1,2 | 4 | 3 | capped-unsaturated (still yielding) |
| `I4-T13-C07-G0` GSD agendas | P2 | capped | 2 | 2,0 | 3 | 2 | capped-unsaturated (one more zero needed) |
| `I4-T13-C09-G0` GSD purchasing | P2 | capped | 2 | 1,2 | 4 | 3 | capped-unsaturated (still yielding) |
| `I4-T14-C04-GS` drone state reports | P2 | 4 / 2 / 4 | 4 | 1,3,1,0 | 5 | 5 | **enumerated (6 found, incl. UT duty lead / 3 negative / 0 not-reached)**: TX family, ME found; FL negative |
| `I4-T14-C05-G0` UAS policy pages | P2 | capped | 2 | 0,2 | 2 | 2 | capped-unsaturated |
| `I4-T14-C07-G0` UAS agendas | P2 | capped | 1 | 2 | 2 | 2 | capped-unsaturated (below K) |
| `I4-T17-C05-GS` CSS policies/reports | P2 | 2 / 0 / 4 | 2 | 0,1 | 1 | 1 | enumerated (3 found / 1 negative / 3 not-reached): +MD; no non-CA policy-posting mandate |
| `I4-T17-C09-G0` CSS purchasing | P2 | capped | 2 | 0,0 | 0 | 0 | **saturated** (K=2) |
| `I4-T18-C04-G0` LI reports | P2 | capped | 2 | 0,2 | 2 | 2 | capped-unsaturated (MN, HI found) |
| `I4-T19-C07-G0` forensics agendas | P2 | capped | 2 | 0,1 | 1 | 1 | capped-unsaturated |
| `I4-T19-C14-G0` forensics civil data | P2 | capped | 2 | 0,0 | 0 | 0 | **saturated** (K=2; no post-2020 national dataset) |
| `I4-T20-C13-G0` SMM records | P2 | capped | 2 | 0,0 | 0 | 0 | **saturated** (K=2; only MuckRock, which is I6's corpus) |
| `I4-T20-C14-G0` SMM civil data | P2 | capped | 2 | 1,0 | 1 | 1 | capped-unsaturated |
| `I4-T20-C16-G0` SMM federal | P2 | capped | 2 | 1,0 | 2 | 1 | capped-unsaturated |
| `I4-T23-C10-G0` BWC grants | P2 | capped (7) | 2 | 1,2 | 3 | 3 | extended, capped-unsaturated |
| `I4-T25-C04-GS` school-safety state reports | P2 | 3 / 0 / 5 | 1 | 2 | 2 | 2 | enumerated (5 found / 0 negative / 3 not-reached): +AZ, NY (legislation) |
| `I4-T25-C14-G0` school civil data | P2 | capped | 2 | 1,0 | 1 | 1 | capped-unsaturated |
| `I4-T25-C16-G0` NCES/CRDC | P2 | capped | 2 | 0,0 | 0 | 0 | **saturated** (K=2; CRDC refused, and its mirror was not used) |
| `I4-T17-C13-G0`, `I4-T19-C13-G0` records | P2 | blocked(access) | 0 | – | 0 | 0 | not retried: blocked(access), MuckRock/DocumentCloud refused I4; I6 owns the corpora |
| `I5-T00-C03-GD` state portals | P2 | 8 searched / 3 not-reached | 2 (API) | 0,1 | 0 | 1 | enumerated: NH identity found (NH GRANIT, 0 camera layers); RI not-reached; DC not attempted |
| `I5-T00-C05-GL1` thin-city policy | P2 | 0 q (below q_min) | 5 | 1,1,1,0,2 | 5 | 5 | enumerated (2 found + 1 lead / 2 negative / 31 not-reached): Charlotte, Anchorage found; Memphis lead (403); Indianapolis (policy not public) and Jersey City negative |
| `I5-T00-C09-GL1` thin-city procurement | P2 | 0 q | 3 | 1,0,0 | 1 | 1 | enumerated (1 found / 2 negative / 33 not-reached): Memphis found; Omaha, Indianapolis negative |
| `I5-T00-C04-GL1` thin-city oversight | P2 | 0 q | 2 | 1,0 | 1 | 1 | enumerated (1 found / 2 negative / 33 not-reached): Tulsa (journalism); Wichita, Omaha negative |
| `I5-T00-C05-GL4` gap-state locality policy | P2 | 1 q | 2 | 1,1 | 2 | 2 | enumerated (4 found, incl. Bangor ME and Little Rock AR captured out-of-cell from T14-C05 / 0 negative / rest not-reached) |
| `I5-T00-C08-GI1` GI1 procurement | P2 | 1 q (below q_min) | 2 | 2,0 | 3 | 2 | capped-unsaturated (plus out-of-cell NT tender C017 and UK OSINT lead C032) |
| `I5-T00-C04-GI1` GI1 regulator reports | P2 | capped (9) | 2 | 0,1 | 3 | 1 | extended, capped-unsaturated |
| `I5-T00-C03-GI1` GI1 open data | P2 | capped (5) | 1 | 0 | 1 | 0 | capped-unsaturated (Oireachtas challenge) |
| `I5-T00-C13-GI1` GI1 FOI | P2 | capped (2) | 2 | 0,0 | 0 | 0 | **saturated (reachable)**; WDTK, Right to Know, Oireachtas and IPC-Ontario refuse |
| `I5-T00-C04-GI2` EU/EEA regulators | P2 | capped (2) | 2 | 1,1 | 3 | 2 | capped-unsaturated (still yielding: NL, FR) |
| `I5-T08-C03-G0` DOT national sweep | P2 | capped (3) | 2 (API) | 0,0 | 0 | 0 | **saturated** (K=2; every agency layer returned is registered) |
| `I5-T00-C07-GL4`, `I5-T00-C16-GT`, GL2 cells, GIW | P2/P3 | as I5 | 0 | – | 0 | 0 | not-started (budget) |
| `I5-T00-C11-GT` territorial legislation | P3 (I5a-2) | extended (5) | 3 | 1,0,1 | 3 | 2 | extended, capped (GU, VI found; MP negative) |
| `I5-T00-C09-GT` territorial procurement | P3 (I5a-2) | below q_min | 2 | 1,0 | 1 | 1 | saturated (P3 K=1; AS negative) |
| `I5-T00-C14-GT` territorial/tribal civil data | P3 (I5a-2) | capped | 1 | 1 | 1 | 1 | capped (Tohono O'odham found) |
| `I5-T00-C13-GL1` thin-city records portals | P3 (I5a-2) | not-started | 1 | 0 | 0 | 0 | saturated (P3 K=1) |
| `I5-T00-C14-GL1` thin-city investigations | P3 (I5a-2) | not-started | 1 | 1 | 1 | 1 | capped-unsaturated |
| `I4-T12-C09-G0` biometrics | P3 (unsearched in I4) | probe refused | 1 | 1 | 1 | 1 | capped-unsaturated (the probe yielded: Doña Ana NM) |

**Cells still unsaturated after I9b:**
- **P1:** T19-C09, T25-C07, T25-C09 (all target-unbounded).
- **P2:** T09-C03, T11-C16, T13-C04, T13-C07, T13-C09, T14-C05, T14-C07, T18-C04, T19-C07, T20-C14, T20-C16, T23-C10, T25-C14, C08-GI1, C04-GI1, C03-GI1, C04-GI2.
- **Enumerations with items still not reached:** T09-C04-GS (14), T11-C04-GS (8), T17-C05-GS (3), T25-C04-GS (3), and the GL1 C05/C09/C04 lists (31–33 each).
- **Not started:** C07-GL4, C16-GT, the GL2 cells and GIW.

---

## 4. Ranked shortlist (for I7)

Ranking weighs three things:
1. the gap closed (P1/P2, tier and weight);
2. structure and recurrence (a statutory series or a geocoded table beats one article);
3. independent origin and a manageable Part VIII posture.

Rights are guesses, never decisions (R5).

| # | Candidate(s) | Gap it closes | Why |
|---|---|---|---|
| 1 | **C110** NL Staatscourant *Cameraplan ANPR Politie* (Q3-2026) | I1#11 (EU); the ANPR-location analogue the UK and NZ withhold | Statutory (art. 126jj Sv), national, quarterly, with lat/lon and a purpose code per camera. About 1,202 coordinate rows (regex count). Official gazette content (Auteurswet art. 11 public domain is a guess) |
| 2 | **C056** FLHSMV Red Light Camera Report (FY2015–FY2024) | NEW-8 ATE; I1#4 | A state-compiled list of every operating jurisdiction (38 in FY2023-24). Annual, aggregate, pass |
| 3 | **C050** (+C051, C052) TX Gov't Code 423.008 drone reports | I1#8/#4; TX | Use counts, investigations aided and cost for every TX agency in places over 150,000, biennially. Free-text screen needed |
| 4 | **C102** Home Office monthly LFR deployment CSVs | I1#11 (UK) | National, structured, recurring LFR aggregates. Confirm the CSV has no person-level rows |
| 5 | **C077** MN State Court Administrator warrant report (+C078 HI) | I1#4; fills I4's pen-register/trap-trace negative (NEW-3) | Statutory, aggregate, state-wide; a stable LRL URL pattern |
| 6 | **C065** MD State Police CSS deployment report | I1#8 (CSS currency: I4 found no current list) | Annual counts (27 uses in 2024); a statutory report under Chapters 222/223 of 2020 |
| 7 | **C090** Memphis quarterly vendor payments over $100K | I1#9 Memphis; I1#1 (a Flock line at origin) | A recurring city finance report that shows surveillance vendors. Filter natural-person payees |
| 8 | **C088** Anchorage AMC 3.102 (+C089 $11.8M technology contract) | I1#9 Anchorage; CCOPS registry gap (NEW-2) | A surveillance-technology ordinance city that SIG does not track |
| 9 | **C026** Utah Public Notice Website (+C046 Nevada notice, lead) | statewide agenda channel (T00); I1#7 | One host covers every public body in the state, including school boards. Minutes need a free-text screen |
| 10 | **C002** NYC City Record Online (Socrata `dg92-zbpx`, Public Domain) | I1#6/#7 | Daily notices, including SMM (Dataminr) and forensics (Cellebrite) sole sources and award hearings; SoQL aggregates |
| 11 | **C024** San Diego PO PDF directory (related SRC-004) | I1#6/#7 | Every city PO is a PDF, so any class can be discovered by vendor term. Drop staff names |
| 12 | **C062/C063** Iowa HF 2681 ATE permits and city ATE reports; **C057** PennDOT WZSSC report | NEW-8 | A state permit decision per camera location (IA); state ATE programme reports (PA) |
| 13 | **C080** SoundThinking renewal press (+C064 Duke evaluations, C106 New Bedford) | I1#8 GSD | The only public per-city GSD coverage figures (square miles). Vendor claims are D6 assertions |
| 14 | **C040** (+C041–C043, C030) district student-monitoring disclosure pages | I1#7 SCH | District-origin statements of deployment and operating mode |
| 15 | **C029** KY KETS GoGuardian; **C005** WSIPC; **C006** Florida Buy; **C036** OMNIA; **C037** NERIC | I1#7 SCH; I1#6 | Cooperative and statewide K-12 back-chain keys (hand-off to I6) |
| 16 | **C100** CanadaBuys; **C101** PSPC BWC/DEMS (Axon) | I1#11 CA; I1#2 | Canadian tender and award notices, including provincial and municipal buyers; a national Axon vehicle |
| 17 | **C075** Immigration Policy Tracking Project; **C111** CBP biometric-arrival releases; **C073** DHS SMOUT compilation | T28/T11/T20 federal; I1#13 | A dated federal operator layer with documents |
| 18 | **C095** Tohono O'odham Legislative Branch notices; **C093** Guam; **C094** USVI | I1#14 | First origin documents for GU, VI and a tribal nation. Flag for tribal sovereignty |
| 19 | **C053** Maine DPS UAV report; **C098** Portland ME; **C108** Bangor; **C109** Little Rock | tier-A states ME, AR; I1#8 | State and local drone governance in gap states |
| 20 | **C103** CNIL BriefCam formal notices | I1#11 (FR) | DPA enforcement naming state and municipal video-analytics use |

Runners-up:
- C021: Boone County NASPO back-chain.
- C022: Riverside GrayKey.
- C105: Washoe JAG-funded Cellebrite.
- C014 and C023: opioid-settlement-funded forensics, a new funding channel.
- C038: a donated GrayKey (Kauai).
- C066: Plano DFR.
- C067: Victorville DFR, where the city buys and the sheriff operates.
- C107: Houston ShotSpotter.
- C092: Tulsa withholds camera locations.

---

## 5. Candidates by class, channel and geography; movement against the I1 blind spots

**By class.** One row counts in every class it covers:

| Class | Rows |
|---|---|
| T25 SCH | 22 |
| T00 multi | 17 |
| T19 FOR | 16 |
| T14 UAS | 13 |
| T20 SMM | 12 |
| T01 ALPR (hand-offs to I3) | 10 |
| T13 GSD | 9 |
| T09 ATE | 7 |
| T07, T11, T23 | 6 each |
| T28 | 4 |
| T22 | 3 |
| T06, T17, T18 | 2 each |
| T03, T05, T08, T10, T12, T21 | 1 each |

**By publisher type:**

| Type | Rows |
|---|---|
| journalism | 30 (facts only; origin named in `lineage`) |
| procurement | 18 |
| agenda | 14 |
| statutory-report | 14 |
| other (district and police policy pages) | 12 |
| gov-open-data | 6 |
| legislation | 6 |
| grant | 3 |
| records-release | 3 |
| ngo | 2 |
| academic | 1 |
| vendor-portal | 1 |
| ccops-report | 1 |

**Movement against the I1 blind spots:**
- **#7, zero-channel classes (48 gap refs).**
  - SMM: NYC CROL, Savannah PenLink, Houston and Buffalo Dataminr, the DHS SMOUT compilation, and the Brennan DC records.
  - FOR: 13 agency purchase records across 13 states, plus 3 funding channels (opioid settlements; JAG/HIDTA/state DOJ pass-throughs; a private donation).
  - SCH: 5 cooperative/state vehicles (C005, C006, C029, C036, C037), a district-disclosure family, Utah PMN, and two statewide programmes (AZ HB 2574, NY S7037).
- **#8, UAS/GSD/FRT/CSS (27).** TX and ME drone reports; MD CSS counts; UT and MT FR; GSD evaluations and vendor renewals; DFR approvals (Plano, Victorville).
- **#4, statutory reporting (19).** FL, PA and IA ATE; TX and ME drones; MD CSS; MN and HI LI; UT FR; MT FR (lead).
- **#9, thin cities.** New surveillance evidence for:
  - Memphis (C090, C091);
  - Houston (C008, C107);
  - Durham (C019, C060);
  - Anchorage (C088, C089);
  - Plano (C066);
  - Tulsa (C092);
  - Frisco (C018);
  - Indianapolis (C086).

  New channel identity for St. Petersburg, Virginia Beach, Lincoln, Charlotte (policy) and Memphis (policy, lead).
- **#14, territories and tribal nations.** GU (C093, C096 lead), VI (C094), Tohono O'odham (C095). AS is still dark (Q104). MP is near-dark (Q103).
- **#11, international.** NL (C110), UK (C102, C032 lead), CA (C100, C101), FR (C103), AU-NT (C017).
- **Tier-A/B states.**
  - Tier A gained AR (C109; C001 lead; C010), ME (C053, C098, C108), NH (C097 identity; C074 lead), VT (C099), WV (C014) and MI (C013).
  - Tier B gained HI (C038, C078), DC (C035, C076), NM (C071) and MT (C054 lead).
  - DE, MS, RI, WY and ND gained nothing.

---

## 6. Negatives (a finding in themselves)

| Where | What does not exist or was not found | Evidence |
|---|---|---|
| American Samoa | No surveillance-relevant public channel at all | Q104: zero AS-specific results |
| Northern Mariana Islands | Only a drone-overflight restriction bill; no DPS deployment evidence | Q103 |
| Florida (drones) | No statewide drone-use report or reporting duty under s. 934.50 | Q054 |
| Colorado (ATE) | No state AVIS annual report, though a state-run speed programme exists | Q066 |
| Non-CA states (CSS) | No CSS policy-posting mandate like CA 53166 surfaced | Q064 |
| Federal Register | Carries no per-agency 44807 exemption notices | Q030 |
| data.transportation.gov | No UAS waiver dataset | Q031 |
| Forensics datasets | No post-2020 national MDFT dataset; no state crime-lab extraction statistics | Q074, Q122 |
| SMM records | Only MuckRock requests, no new release channel | Q083, Q125 |
| NCES/CRDC | Nothing reachable beyond I4; the CRDC origin refuses automated clients and its university mirror was not used (R4) | Q077, Q123 |
| Board platforms | Simbli and BoardDocs pages are not indexed by the search engine; PrimeGov and CivicClerk items likewise | Q022, Q040, Q073 |
| Thin-city channels | No official contract search for Omaha or Indianapolis; no thin-city NextRequest/GovQA portal surfaced; no 2026 council technology report for Wichita or Omaha | Q096, Q097, Q100, Q126 |
| Indianapolis | The IMPD ALPR use rule exists but is **not public** (a coverage fact) | Q091/F112 |
| Ireland | No data.gov.ie CCTV dataset; scheme counts appear only in parliamentary answers (challenge-protected) | Q127 |

---

## 7. Part VIII hazards (counts and categories only; no content)

- **Verdicts:** 83 pass, 26 flag, 2 block.
  - **C072 is blocked.** It is the AP school-surveillance investigation; the underlying records are student content (minor-data).
  - **C076 is blocked.** It is the Brennan DC MPD SMM records. The monitored individuals and networks are person-level-enforcement.
- **Flags:** private-person-name 22 (institutional staff in minutes, POs and contract pages), free-text-narrative 8, residential-intersection 3, person-level-enforcement 2, minor-data 1, tribal-sovereignty 1.
- **Hazards met but never fetched:**
  - **FAA Part 107 CoW PDF filenames embed individual pilot names** tied to police DFR programmes (Q037). Filenames only were seen, in search results; nothing was copied (NEW-1).
  - Ohio BCI case laboratory reports: person-level (Q122).
  - Lincoln PD traffic-stop layers: titles only (C047).
- **No plate, operator id, audit-row officer name, search reason, student datum or private address** appears in any committed file.
  - The validator's e-mail scan found 0.
  - Staff names read in fetched documents were not copied.
  - Raw captures that contain staff contact details (San Diego PO, Clay County item, KY KETS page, Utah minutes) remain only in gitignored scratch, hashed for reproducibility.
- **Jurisdiction-conditional publication** (SIG-PUB-017) applies to every GI candidate, and each one names its regime: UK-GDPR/DPA 2018 Part 3; GDPR/LED for NL and FR; PIPEDA and provincial law for CA; the Privacy Act 1988 and NT Information Act for AU. US-TRIBAL rows need a tribal-data-governance decision.

---

## 8. INACCESSIBLE list (host · status · run_at · what was sought)

A 403, 429 or challenge stopped the host for this row, with no retry and no mirror.

- **403 or challenge:**
  - faa.gov · 403 · 19:03:27Z · Part 91.113 waivers (again, after I4).
  - wrps.org · 403 · 19:03:27Z · a board packet.
  - lfportal.everettwa.gov · 403 · 19:04:24Z.
  - cityofseward.us · 403 · 19:08:20Z.
  - turner.ic-board.com · 403 · 20:19:41Z.
  - find-tender.service.gov.uk · 403 · 20:22:43Z · Met OSINT award.
  - thisisreno.com · 403 challenge · 20:35:18Z.
  - dos.nh.gov · 403 challenge · 20:37:42Z · NH BWC grant.
  - reimagine.memphistn.gov · 403 · 20:43:26Z · MPD manual.
  - contractsfinder.service.gov.uk · 403 · 20:49:26Z.
  - ipc.on.ca · 403 challenge · 20:49:26Z.
- **Bot pages served with 200 or 405:** littlerock.gov (200 interstitial, 19:03:25Z); oireachtas.ie (405 human verification, 20:53:54Z).
- **400 or 406:** meetings.boardbook.org and manuals.boardbook.org (400); gwosa2.opaguam.org (400); usd230.org, baltimorecityschools.org and westada.org (406, Finalsite).
- **TLS or DNS failure:** tdcj.texas.gov, archive.legmt.gov (also WebFetch), oipc.novascotia.ca, notice.nv.gov and schooldataleadership.org (curl 35); opendata.lincoln.ne.gov (DNS: the host no longer resolves).
- **404 or dead:**
  - ND HHS opioid-settlement report; Sacramento 10-day contract postings (ephemeral, NEW-4); minneapolismn.gov GSD landscape; politie.nl camera-plan page (moved; the Staatscourant copy was used); LTC Illinois; DHS APFS record; Terre Haute minutes.
  - The Baltimore egisdata red-light service returns "Service not found" (a stale Hub item).
  - weldre5j.k12.co.us returned 522.
- **JS-only or wrapper pages:** le.utah.gov xcode statute text; guamlegislature.com (consent-manager wrapper); civiciq.com and Govly meeting pages (not fetched; aggregators).
- **Deliberately not used:**
  - the CRDC university mirror, because the origin refused I4 (R4);
  - FAA, Flock and other mirrors or archives;
  - account-walled aggregators (Govly beyond public pages, BidNet, HigherGov).

---

## 9. Open questions for I7 and the operator

1. **FAA access (NEW-1).** Should the FAA waiver lists be acquired through an operator-approved route (an FAA bulk or FOIA request) rather than by scraping? How are filename-embedded pilot names to be dropped?
2. **Statewide public-notice sites** (Utah PMN, and the Nevada notice site as a lead). Should they become multi-class discovery connectors, keyed by body, with a free-text screen?
3. **Discovery-only aggregators.** Are CitizenPortal.ai (AI meeting summaries), SoundThinking press releases (vendor assertions) and Govly/civiciq pages acceptable as lead generators, provided every claim is re-anchored at the origin?
4. **Ephemeral postings (NEW-4).** Should Sacramento-style 10-day contract postings get a scheduled watcher that writes to the OCFL evidence store?
5. **The Anchorage CCOPS gap (NEW-2).** Should Anchorage be added to the CCOPS family and its 3.102 duties enumerated (I6)?
6. **The NL ANPR plan.** Does SIG want foreign ANPR point layers, which would need a compartment and publication decision (SIG-PUB-017)? Is the Staatscourant copy (quarterly PDF) or an API the canonical origin?
7. **Summary-figure hygiene (NEW-5).** Should I7 adopt a mechanical rule that every numeric claim carries a fetch-id quote?
8. **Unsaturated cells.** Any I9c should take the three target-unbounded P1 cells only if a *channel* strategy is chosen: PO directories, statewide notice sites, cooperative back-chains. More agency-by-agency search adds targets, not coverage.

---

## 10. Self-check (I2 §9)

| Check | Result |
|---|---|
| Every candidate has a fetch or API line; every `found_by_query_id` resolves | **pass** (`build.py`: 0 errors); the 10 LEAD-ONLY rows cite the failed fetch |
| Every query line has `cell=` naming an I4 or I5 cell present in `search_matrix.csv` | **pass** |
| Every P1/P2 cell attempted has at least `q_min` queries or an honest status | **pass** (§3; T14-C07 and C03-GI1 are marked below K or capped) |
| `cand_id`s unique; 32 columns (§8.6 + I2 §7.3) | **pass** (111 rows) |
| `registry_match` computed with the §7.6 greps (`dd.py`) | **pass** |
| No plate, operator id, audit officer name, search reason, student datum or private address in committed files | **pass** (e-mail scan 0; names not copied) |
| `rights_lane` never `decided`; every licence prefixed `guess:` | **pass** (validator) |
| Every date from `date -u` or a tool timestamp | **pass**, with the disclosed WebFetch upper-bound time and 8 lost query strings (NEW-6) |
| P16 | **pass** (project UA only; no contact-string services) |

---

## Appendix: reproduction

- **Scratch:** `docs/build/logs/next-phase/I9b/` (gitignored).
  - `fetch_index.tsv`: every GET, with run_at, status, sha256, bytes and host.
  - `raw/<id>.bin` (+ `.txt` for PDFs, extracted with macOS PDFKit via `pdftxt.js`/`px.py`).
  - `qlog.csv`: the query lines.
  - `fnotes.csv`: the fetch annotations.
  - `cands/b01…b21.json`: the candidate batches.
  - `blocked_hosts.txt`: the stop-list.
- **Tools:**
  - `f.py`: the fetcher (P16 UA, rate limit, caps, stop-list).
  - `dd.py`: the I2 §7.6 dedupe over the registry, queue, I3–I6, I9a and scratch.
  - `t.py`: the text viewer.
  - `build.py`: writes and validates both committed CSVs, and applies the recorded `PATCH` corrections, such as within-row merges and one verdict raise.
  - `stats.py`: the §3 table.
  - `findings.py`: writes `findings/incoming/I9b.csv`.
- **Recompute:** run `python3 build.py && python3 stats.py` from the scratch directory. Cell statistics derive only from the committed log's `cell=` and `new=` keys.
