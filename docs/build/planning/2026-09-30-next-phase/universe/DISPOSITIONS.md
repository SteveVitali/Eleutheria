# S1b — Universe consolidation and dispositions

> **Row:** S1b (META_PLAN §6.S), depends on S1a, A3, A2, D1, F1, F2a/b, F3, I7. **Rendered:** 2026-10-01T00:33:37Z (`date -u`) by Claude Code
> (Opus 5.5) in the planning worktree on `claude/next-phase-planning`. **Outputs:** `universe/UNIVERSE_DISPOSED.csv`
> (one row per item, 1159 rows), this note, `tools/check_dispositions.py` and `tools/test_check_dispositions.py`.
> **Read-only:** no control file, spec, ADR, manifest, LEDGER, UNIVERSE.csv or production system was touched (P3, P10);
> nothing was committed. Evidence class of every disposition: `inference` from the cited row outputs (P1). Nothing here is
> an operator decision: items that wait on one point at its S1c `dec_id`.

---

## 0. Bottom line

- **1159 items, each with exactly one disposition:** 528 universe items (U-0001…U-0528) · 538 findings (F-01…F-538) ·
  28 operator-feedback items (U-001…U-015, U-003.1…11, U-003.G, U-003.X) · **65 candidate groups** covering all 694
  consolidated candidates (one group per acquisition-plan build ticket or deferral trigger).
- **Check:** `python3 tools/check_dispositions.py` → **OK, 0 errors** (rules a–e below); `uv run python -m pytest tools/test_check_dispositions.py` → 36 passed.
- **S0/S1 coverage (113 = 9 S0 + 104 S1):** 101 land on a stage-B seed or first-R11-wave unit, 3 on an operator decision, 1 already done, and 8 on a later-wave fix that names a first-wave interim mitigation (§3). None is later-phase or wontfix.
- **Decision-dependent items: 41** (§4). **Wontfix: 14**, **later-phase: 153** (§5; every later-phase names its trigger). **Undisposed: 0** (§6).
- **Orphan catalog units:** 25 of 317 are pointed at by no item; all 25 come from a design row's own outline (§7).
- **Baseline:** the A1 delta (`a1_delta.py delta`, sha256 `c71ce1df…` as recorded in BASELINE.md) ran 2026-10-01T00:31:01Z →
  **0 changed keys**; `extract_universe.py --check` → OK (all control files match A1). Nothing to fold in.
- **Findings register re-merged first** (as instructed): `tools/merge_findings.py` added F-535…F-538 (L3 NEW-1…4) to
  `findings/FINDINGS.csv` and `findings/REGISTER.md` (534 → 538 rows; the first 534 rows are byte-identical).

## 1. Method

1. **Sources, re-derived by the checker:** `universe/UNIVERSE.csv` (A3), `findings/FINDINGS.csv` (merged), the U-ids in
   `feedback/OPERATOR_FEEDBACK.md`, and `data/acquisition_plan.csv` × `data/candidates_consolidated.csv` (I7/I8).
2. **Recommendations used, in this order of authority:** the row that adjudicated the item (column `stream`): F1
   (`owed_register_adjudication.csv`) for the 36 owed deferrals; F2a/F2b (`coverage_delta_F2*.csv`) for requirements; F3
   (`backlog_triage.csv`) for BL, RISK and ADR-trigger rows; L3 §6 for rows 184–187, HUMAN-H4/H5 and SIG-EVAL-*; B3 for
   RETURN PASS; I8 for candidates; K13 §5 for the operator asks and K-row findings; C6 §2 (RI-01…RI-60) for C2/C3/C4
   findings; and **S1a's `merged_from`** (a finding or universe ref cited by a catalog unit lands on that unit). Where a later
   row supersedes an earlier one (L3 over F4; Q-E2-12's default over F2b's waiver) the later row wins and the rationale says so.
3. **Primary owner.** Each item has one disposition kind; `disposition_ref` lists its landing unit first, then any other
   catalog units that carry part of it. `links` carries secondary owners, `gate:<dec_id>` (an S1c decision that gates but does
   not change the disposition), `interim:<cat_id>` (a first-wave mitigation for an S0/S1 whose fix lands later), and RI ids.
4. **When an item is `decision(…)` rather than a ticket:** only when the S1c decision chooses *which* disposition the item gets
   (build vs waive vs later vs wontfix), or the catalog home differs from S1c's recommendation, or every catalog home is
   conditional on the answer. A decision that merely gates a planned ticket stays a `gate:` link.
5. **Rights rows:** a decline/WONTFIX or flip of a source is the operator's HG-03 line, so F1's proposed wontfix for
   D-SOURCES.2-2, D-SOURCES.9-2 and D-JURIS.2-1 is shown as `decision(E4-…)` (S1c default: status unchanged).
6. **Record-only DONE rows that later rows contest** (D-P21.4-1/-2, D-LEGAL.1-1, D-P30.3-COUNSEL; D-P31.1-1, D-P31.5-2)
   are not `already-done`: the first four wait on the governance package (Q-7 members), the last two have an owed live leg.

**Enum.** §8.1's ten kinds plus `decision(<dec_id>)`. Written `kind(arg)`; `arg` is the cat_id / dec_id / item id for
ticket, live-return-pass, decision and merged-into, the action for operator-action, the trigger for later-phase, the
reason for wontfix, the evidence for already-done, and the requirement/section for spec-amendment (lands in SEED-12) or the
draft ADR for adr-waiver (lands in SEED-11).

## 2. Counts by disposition × source kind

| source kind | ticket | live-return-pass | spec-amendment | adr-waiver | operator-action | human-marker | already-done | wontfix | later-phase | merged-into | decision | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `deferral` | 10 | 11 |  |  |  |  | 53 | 4 | 9 |  | 10 | **97** |
| `requirement` | 109 | 8 | 3 |  |  |  | 17 | 8 | 12 |  | 4 | **161** |
| `backlog` | 17 |  |  |  |  |  | 11 |  | 4 | 1 | 3 | **36** |
| `risk` | 18 |  | 1 | 1 |  |  | 20 |  | 11 | 7 | 4 | **62** |
| `adr_trigger` | 54 | 6 | 2 |  |  |  | 26 |  | 56 |  |  | **144** |
| `ledger_finding` |  |  | 1 |  |  |  |  |  |  |  |  | **1** |
| `return_pass` |  |  |  |  | 1 |  | 11 |  |  | 7 |  | **19** |
| `readout` |  |  |  |  |  |  |  |  | 2 |  |  | **2** |
| `manifest_row` |  |  |  |  |  |  |  | 1 | 4 | 1 |  | **6** |
| `finding` | 496 | 1 |  |  | 6 |  | 5 | 1 | 11 | 6 | 12 | **538** |
| `feedback` | 22 |  |  |  | 1 |  | 3 |  | 1 | 1 |  | **28** |
| `candidate_group` | 13 |  |  |  |  |  |  |  | 43 | 1 | 8 | **65** |
| **total** | **739** | **26** | **7** | **1** | **8** | **0** | **146** | **14** | **153** | **24** | **41** | **1159** |

Owed deferrals (36 = 32 OPEN + 4 PARTIAL): already-done 2, decision 6, later-phase 9, live-return-pass 9, ticket 10.

Where the ticket-like dispositions land (primary unit): first waves 542, r11 224, operator 7.

### 2.1 First R11 waves (the set rule (c) uses)

`first_waves()` = 133 catalog units: every seed row and every `early R11` row (S1a §2), K13's W0/W1 tickets
(`k13_tickets.csv`), the units each design itself places in wave 0/1 — **G2 §4** steps 0, 1 and step 4's "engineering from
Round-11 day 1" (ACT-01…11, ACT-16…20, ACT-17b), **L3 §9** waves 0–1 (CONF-02, CONF-01, CONF-03a, CONF-08), **I8 Wave A**
(ACQ-01, 02, 04–07), **F5 §4** order steps 1–5 (PKG-02/13/01/09a/03/04/05/06/08/10/11/07 owners) — plus their transitive hard
prerequisites. S2 has not yet merged the waves; a unit in this set that S2 places later would break rule (c), so the S0/S1
owners in §3 are an **ordering constraint for S2**.

## 3. S0 and S1 findings

`landing`: seed · early (S1a early R11) · W1 (design wave 0/1 or prerequisite) · decision · done · later+interim.

| f_id | sev | origin | finding | disposition | landing | interim / gates |
|---|---|---|---|---|---|---|
| F-01 | S0 | A2 | Cloud SQL sig-pg had automated backups disabled and 0 backups while ADR-081 says managed backup… | `ticket(R11-ACT-04)` | early |  |
| F-02 | S0 | A2 | /curate/ demo curation pages (forms posting to 127.0.0.1:8001) were publicly served because the… | `ticket(R11-ACT-05)` | early |  |
| F-03 | S0 | A2 | Every page advertises a one-click, no-account dispute/correction channel, but live /dispute/ ha… | `ticket(R11-ACT-06)` | early |  |
| F-096 | S0 | C2:NEW-1 | Visual-language page asserts unlabelled fixture facts about real named agencies and a vendor | `ticket(R11-ACT-06)` | early |  |
| F-097 | S0 | C2:NEW-2 | Public source identifiers embed what appear to be personal ArcGIS account handles (redacted) | `ticket(R11-SAFE-01)` | early |  |
| F-130 | S0 | C3:NEW-1 | Public API dossier endpoint returns the same 25 unrelated subjects and sources for every scope | `ticket(R11-ACT-08)` | early |  |
| F-131 | S0 | C3:NEW-2 | Personal ArcGIS account handles appear inside public source identifiers | `ticket(R11-SAFE-01)` | early |  |
| F-183 | S0 | E1:NEW-1 | Live /editorial-standards/ presents a fixture hostile-reader review ('two reviewers independent… | `ticket(R11-ACT-06)` | early | gate:Q-E2-01 |
| F-387 | S0 | J1:NEW-2 | Public downloads and the live API misattribute third-party data to "DeFlock community map" (3,2… | `ticket(R11-ACT-07)` | early |  |
| F-04 | S1 | A2 | No Oklahoma dossier; 'unresolved' is one of 55 dossier jurisdictions and holds 71.4% of publish… | `ticket(R11-K13-JUR-02b)` | W1 |  |
| F-05 | S1 | A2 | The 'How we know this' module shows the same site-wide totals on every page (e.g. /dossier/al/ … | `ticket(R11-K13-UXW0-1)` | early |  |
| F-050 | S1 | B1:NEW-1 | Recorded dates were deliberately decoupled from the clock by a self-invented 'chain date' conve… | `ticket(R11-ACT-12)` | early |  |
| F-051 | S1 | B1:NEW-2 | The GATE-G3-signed candidate carries 2026-10-19 in its publication id, release id and as-of, no… | `ticket(R11-ACT-12)` | early |  |
| F-052 | S1 | B1:NEW-3 | Dossier packets, the research-dossier web fixture and the signed candidate state retrieval, obs… | `ticket(R11-ACT-12)` | early |  |
| F-053 | S1 | B1:NEW-4 | Hazard: build memory's latest dates (2026-10-19 to 10-21) make the 2026-10-10 OSM replay look o… | `ticket(SEED-17)` | seed |  |
| F-057 | S1 | B2:NEW-1 | F-22 refinement: the deleted GATE DECISIONS rows were the sole or authoritative record for deci… | `ticket(SEED-06)` | seed |  |
| F-06 | S1 | A2 | /methodology/ reports pairwise P/R/F1 1.000 on 'the frozen, human-verified holdout' directly be… | `ticket(R11-ACT-06)` | early |  |
| F-07 | S1 | A2 | Belief-pinned as-of permalinks do not pin: the static nginx ignores the query string, so every … | `ticket(R11-K13-TX-13a)` | W1 |  |
| F-074 | S1 | B4:NEW-1 | The Round-11 planning ledger repeats F-21 today: 24 META_PLAN §11 change-log entries are stampe… | `ticket(SEED-00)` | seed |  |
| F-098 | S1 | C2:NEW-3 | Dispute page offers no way to submit and does not say the receiver is not operating | `ticket(R11-ACT-06)` | early |  |
| F-099 | S1 | C2:NEW-4 | Belief-pinned permalinks are not pinned: the server ignores as_of and ruleset parameters | `ticket(R11-K13-TX-13a)` | W1 |  |
| F-100 | S1 | C2:NEW-5 | Dossier 'unknown' values omit the kind of absence; five sections render as empty headings | `ticket(R11-K13-UXW0-1)` | early |  |
| F-101 | S1 | C2:NEW-6 | Print dossier omits as-of and permalink on page 1, has an orphan page, and no licence | `ticket(R11-K13-TX-13a)` | W1 |  |
| F-102 | S1 | C2:NEW-7 | No link path from any displayed figure to its evidence; evidence viewer is empty | `ticket(R11-K13-TX-09)` | W1 |  |
| F-103 | S1 | C2:NEW-8 | Bulk data, manifest, API and terms are not linked anywhere on the site | `ticket(R11-K13-UXW0-4)` | early |  |
| F-104 | S1 | C2:NEW-9 | Interactive map renders only a few dozen points on a blank canvas; streets show nothing | `ticket(R11-K13-MAP-01a)` | W1 |  |
| F-105 | S1 | C2:NEW-10 | Jurisdictions shown only as bare codes; place-name searches return 0 though dossiers exist | `ticket(R11-K13-UXW0-5)` | early |  |
| F-106 | S1 | C2:NEW-11 | Network explorer names no entity: 131 UUID nodes, one edge type, no access-type filter | `ticket(R11-K13-GX-02)` | W1 |  |
| F-107 | S1 | C2:NEW-12 | Editorial-standards page presents a fixture two-reviewer review of a non-existent dossier | `ticket(R11-ACT-06)` | early |  |
| F-108 | S1 | C2:NEW-13 | Methodology calls the ER holdout 'human-verified' while the same page says LLM/agent-labelled | `ticket(R11-ACT-06)` | early |  |
| F-109 | S1 | C2:NEW-14 | 'How we know this' shows site-wide totals on every dossier; tier sum is 6 short of claims | `ticket(R11-K13-UXW0-1)` | early |  |
| F-110 | S1 | C2:NEW-15 | Sources appear only as internal keys with no publisher, link, date or licence | `ticket(R11-K13-TX-02)` | W1 |  |
| F-111 | S1 | C2:NEW-16 | Map attribution credits third-party licensed compartments to '© SIG contributors' | `ticket(R11-ACT-07)` | early |  |
| F-132 | S1 | C3:NEW-3 | Every dossier shows the national 'How we know this' totals instead of dossier-specific provenan… | `ticket(R11-K13-UXW0-1)` | early |  |
| F-133 | S1 | C3:NEW-4 | Methodology calls the resolver holdout 'human-verified' and shows P/R/F1 1.000 from a single pa… | `ticket(R11-ACT-06)` | early |  |
| F-134 | S1 | C3:NEW-5 | Coverage says all 232625 subjects have a resolved latitude while 5290 are withheld as conflicti… | `ticket(R11-DATA-04)` | W1 |  |
| F-135 | S1 | C3:NEW-6 | Dossier 'geolocated in <jurisdiction>' counts include points located elsewhere (CA, GB-ENG, TH,… | `ticket(R11-K13-JUR-02b)` | W1 |  |
| F-136 | S1 | C3:NEW-7 | Dossier banner says '1 unresearched field' while 12 fields show 'unknown' and 5 sections are em… | `ticket(R11-K13-UXW0-1)` | early |  |
| F-137 | S1 | C3:NEW-8 | Freshness page shows 0 stale entities for all 178 sources although staleness was never evaluabl… | `ticket(R11-K13-UX9-2)` | W1 |  |
| F-138 | S1 | C3:NEW-9 | Map attribution credits third-party share-alike and OGL tile data to 'SIG contributors' | `ticket(R11-ACT-07)` | early |  |
| F-139 | S1 | C3:NEW-10 | API coverage endpoint reports complete coverage with zero evaluated for jurisdictions with open… | `ticket(R11-ACT-08)` | early |  |
| F-151 | S1 | C4:NEW-1 | Release-archive relative links are one level too shallow: browse and evidence links 404 | `ticket(R11-ACT-16)` | W1 |  |
| F-152 | S1 | C4:NEW-2 | Research dossiers present hand-authored stand-in documents as captured sources, undisclosed | `ticket(R11-ACT-18)` | W1 |  |
| F-153 | S1 | C4:NEW-3 | Research dossier headline says 'Reviewed research dossier' while independent review is not_run | `ticket(R11-ACT-18)` | W1 |  |
| F-154 | S1 | C4:NEW-4 | Empty release-search state calls a no-match a 'recorded absence, not missing research' | `ticket(R11-ACT-19)` | W1 |  |
| F-155 | S1 | C4:NEW-5 | Release-archive pages have no dispute/correction link and no site navigation | `ticket(R11-ACT-16)` | W1 |  |
| F-156 | S1 | C4:NEW-6 | Archive records render configured and observed access edges both as untyped 'sharing_access' | `ticket(R11-ACT-16)` | W1 |  |
| F-157 | S1 | C4:NEW-7 | Released dossier pages omit the provisional/eval-deferred posture and are unreachable by links | `ticket(R11-ACT-16)` | W1 |  |
| F-158 | S1 | C4:NEW-8 | Reviewer detail route returns HTTP 500 with the PostgreSQL intake store (UUID not serialisable) | `ticket(R11-ACT-20)` | W1 |  |
| F-159 | S1 | C4:NEW-9 | No production wiring for release search or intake: /v1 and /intake 404 on the web origin | `ticket(R11-ACT-17)` | W1 |  |
| F-16 | S1 | A2 | Round-10 dossier pilots are built from hand-authored stand-in documents (disclosed), yet SIG-TR… | `ticket(R11-ACT-18)` | W1 |  |
| F-160 | S1 | C4:NEW-10 | Web deploy rsync --delete would erase the staged release tree; /releases/index.html collides | `ticket(R11-ACT-05)` | early |  |
| F-161 | S1 | C4:NEW-11 | GATE-G3-accepted staging candidate is a fixture: 0 records, example.test evidence, future as-of | `ticket(SEED-08)` | seed | gate:Q-12 |
| F-184 | S1 | E1:NEW-2 | Crawler user-agent contact URL points at an unregistered domain (sig-project.org, NXDOMAIN) on … | `operator-action(defensively register sig-project.org)` | early | gate:Q-E2-03 |
| F-185 | S1 | E1:NEW-3 | GL-GATE-02's promised label ('operator/engineering disposition pending counsel; counsel review … | `ticket(R11-ACT-06)` | early |  |
| F-186 | S1 | E1:NEW-4 | Public map and downloadable datasets omit upstream attribution required by their own licences (… | `ticket(R11-ACT-07)` | early |  |
| F-189 | S1 | E1:NEW-7 | Governance doc (public repo) asserts an editorial board 'exists, distinct from the technical ma… | `ticket(R11-GOV-01)` | early |  |
| F-190 | S1 | E1:NEW-8 | Coverage matrix records MET for requirements whose human, counsel, outreach or live leg never h… | `ticket(SEED-14)` | seed |  |
| F-191 | S1 | E1:NEW-9 | Three consequential records rest on operator words that are interrogative, tentative or instruc… | `decision(OD-12)` | decision | gate:Q-E2-21 |
| F-192 | S1 | E1:NEW-10 | Org-resolution eval is published as 'LLM adjudicator vs maintainer seed κ 0.714' on 'the frozen… | `ticket(R11-ACT-06)` | early |  |
| F-198 | S1 | E2:NEW-1 | The SIG-UI-042 hostile-reader gate can only pass with two or more reviewer names and gates only… | `ticket(R11-ACT-06)` | early |  |
| F-20 | S1 | A2 | The chain never consulted GitHub CI: both build skills exclude CI polling by design, and no led… | `ticket(R11-CI-02)` | early |  |
| F-201 | S1 | E3:NEW-1 | Public /editorial-standards/ presents a completed two-reviewer hostile-reader review (SIG-UI-04… | `ticket(R11-ACT-06)` | early |  |
| F-21 | S1 | A2 | Future-dated build records: Round-9/10 events are recorded as 2026-10-01…10-21 in commits made … | `ticket(SEED-07)` | seed |  |
| F-22 | S1 | A2 | c2055d96 (2026-09-18) deleted the 53-row append-only GATE DECISIONS table (HG-14 signatures, HG… | `ticket(SEED-06)` | seed |  |
| F-23 | S1 | A2 | LEDGER is 679 KB with a 123 KB CURRENT STATE of PRIOR chains; its header says 'gitignored, neve… | `ticket(SEED-10)` | seed |  |
| F-238 | S1 | F2b:NEW-1 | The 75-row MET-DIFFERENTLY "process/governance" family is a classifier default, not verified de… | `ticket(SEED-14)` | seed |  |
| F-27 | S1 | A2 | Every build-memory validator passes on a tree containing F-21…F-26 (they check structure, not t… | `ticket(SEED-18)` | seed |  |
| F-272 | S1 | G1:NEW-1 | All Cloud Run services (3, each allUsers-invokable) and all 88 Cloud Run jobs run as the defaul… | `ticket(R11-OPS-01)` | W1 |  |
| F-273 | S1 | G1:NEW-2 | sig-probe has failed every 6-hourly sweep since 2026-09-27T06:00Z (14 consecutive) on stale bak… | `ticket(R11-ACT-02)` | early |  |
| F-275 | S1 | G1:NEW-4 | No bucket has object versioning, a retention policy or lifecycle rules (only the 7-day default … | `ticket(R11-ACT-01)` | early |  |
| F-277 | S1 | G1:NEW-6 | Root cause of the /curate/ republish regression: the exclusion is a post-build deletion inside … | `ticket(R11-ACT-05)` | early |  |
| F-285 | S1 | G1:NEW-14 | The production spine has never been restored at scale: the only 'restore drill' (2026-09-15) wa… | `ticket(R11-ACT-04)` | early |  |
| F-29 | S1 | A2 | The GATE-G3 and GATE-ACCEPT (ACCEPT-R10) readouts were written by the agent from one-line appro… | `ticket(R11-MEM-07)` | early |  |
| F-30 | S1 | A2 | 69 not-MET requirement ids; 55 appear in no BACKLOG, DEFERRALS or manifest row; 19 still route … | `ticket(SEED-14)` | seed |  |
| F-31 | S1 | A2 | Spec MUSTs contradicted by operator decisions or operated state: SIG-PUB-008 (sole-maintainer w… | `decision(Q-7)` | decision |  |
| F-321 | S1 | I1:NEW-1 | Public jurisdiction index and dossiers merge ISO-3166 country codes with USPS state codes: 'DE'… | `ticket(R11-K13-JUR-01)` | W1 |  |
| F-322 | S1 | I1:NEW-2 | Published site coordinates and jurisdiction labels are wrong for at least 7 registry sources: l… | `ticket(R11-DATA-01)` | W1 |  |
| F-324 | S1 | I1:NEW-4 | Jurisdiction attribution exists only for geolocated camera-registry sources: 22 states (incl. O… | `ticket(R11-K13-JUR-02b)` | W1 |  |
| F-329 | S1 | I1:NEW-9 | Every camera-registry record is labelled 'traffic_camera' in the hosted spine, including Flock … | `ticket(R11-DATA-02)` | W1 |  |
| F-330 | S1 | I3:NEW-1 | Public ArcGIS layers found by the same keyword/owner discovery SIG uses for camera registries e… | `ticket(R11-ACQ-01)` | W1 | gate:Q-19 gate:I7-X2 |
| F-36 | S1 | A2 | Gates were largely pre-answered, blanket, pre-authorized or delegated; blockedOn was '(nothing)… | `ticket(R11-MEM-07)` | early |  |
| F-366 | S1 | I8:NEW-1 | Widening osm_overpass cannot by itself make OpenStreetMap the origin of the national ALPR layer… | `already-done(I8 re-planned the OSM origin as code (R11-ACQ-1` | done |  |
| F-374 | S1 | I9a:NEW-1 | SIG's state ALPR statute layer is stale past the 2025 LAPPA inventory: five 2026 enactments (WA… | `ticket(R11-ACQ-06)` | W1 |  |
| F-386 | S1 | J1:NEW-1 | Full licence-separated bulk release (132 artifacts, 1.05 GB, sha256-checksummed) is publicly do… | `decision(D-J3-4)` | decision | gate:Q-31 |
| F-389 | S1 | J1:NEW-4 | Public evidence provenance is synthetic: /evidence/ shows no claim evidence (claim_views always… | `ticket(R11-K13-UXW0-2)` | early |  |
| F-390 | S1 | J1:NEW-5 | Every page's 'Belief-pinned permalink (reproducible after SIG corrects itself)' ignores its as-… | `ticket(R11-K13-TX-13a)` | W1 |  |
| F-399 | S1 | J3:NEW-1 | Chain-tip citations stay unpinned even after P32.13 deploys: BaseLayout never passes a release … | `ticket(R11-K13-TX-13a)` | W1 |  |
| F-400 | S1 | J3:NEW-2 | The P32.2 actual-capture writer hard-codes storage_tier='public' and /v1/evidence serves source… | `ticket(R11-K13-TX-01)` | W1 |  |
| F-403 | S1 | J4:NEW-1 | Six live camera-registry sources whose own item terms (captured in SIG's 2026-09-18 catalog swe… | `ticket(R11-SAFE-02)` | early | gate:Q-J4-2 gate:D-J3-5 |
| F-405 | S1 | J4:NEW-3 | Attribution census: 21 of 27 live sources whose licence requires attribution fail it (17) or me… | `ticket(R11-ACT-07)` | early |  |
| F-414 | S1 | K1:NEW-1 | Root cause of F-100 (C2 NEW-9): the live overlay tiles are rendered by tippecanoe with default … | `ticket(R11-K13-MAP-01a)` | W1 |  |
| F-420 | S1 | K12b:NEW-1 | Network hides entity names SIG already holds: hub is 'Vigilant Solutions (LEARN)' and a spoke '… | `ticket(R11-K13-GX-02)` | W1 |  |
| F-421 | S1 | K12b:NEW-2 | Network edges omit evidence date, source and currency: 130 'configured access' edges rest on on… | `ticket(R11-K13-GX-02)` | W1 |  |
| F-422 | S1 | K12b:NEW-3 | TX dossier says data-sharing partners 'Not researched — SIG has not looked yet' while the recor… | `ticket(R11-K13-UXW0-1)` | early |  |
| F-431 | S1 | K12b:NEW-12 | Sources behind sharing, evidence, procurement and legislation claims appear on no page: the sou… | `ticket(R11-K13-UX9-1)` | W1 |  |
| F-44 | S1 | A2 | Jurisdiction-code collisions merge different places into one public dossier: /dossier/id/ combi… | `ticket(R11-K13-JUR-01)` | W1 |  |
| F-452 | S1 | K2:NEW-1 | All 969 referenced organisations are publication-review-flagged, so P32.5's gate will withhold … | `ticket(R11-ACT-10)` | W1 | gate:D-K2-1 |
| F-469 | S1 | K4K5:NEW-2 | Point-in-polygon places 91.5% of the 'unresolved' dossier bucket (152,058 of 166,210 records) i… | `ticket(R11-K13-JUR-02b)` | W1 |  |
| F-481 | S1 | K7K8K11:NEW-1 | The renewal watch has no producer: no EXPORT_QUERIES key (or any other code) fills raw['contrac… | `ticket(R11-K13-WX-01)` | W1 |  |
| F-504 | S1 | L1:NEW-1 | Claim identity includes row position, page URL, capture digest, fetch date and OSM version, so … | `ticket(R11-CONF-03a)` | W1 |  |
| F-506 | S1 | L1:NEW-3 | Subject keys collide or drift: Legistar contract keys are not tenant-scoped, Atlas and EFF agen… | `ticket(R11-CONF-03b)` | later+interim | interim:R11-CONF-01 |
| F-507 | S1 | L1:NEW-4 | Independence is never declared in production: the PG readers never set independence_class, deri… | `ticket(R11-CONF-04)` | later+interim | interim:R11-CONF-01 |
| F-511 | S1 | L1:NEW-8 | No cross-source deduplication reaches any published record: camera-site ER output is used only … | `ticket(R11-CONF-07b)` | later+interim | interim:R11-CONF-01 |
| F-512 | S1 | L1:NEW-9 | The camera-site gold set is labelled twice by the same model (verifier and 'blind' adjudicator … | `ticket(R11-CONF-02)` | early |  |
| F-518 | S1 | L2:NEW-1 | Non-unique upstream refs merge distinct cameras into one subject: 5,278 camera subjects carry d… | `ticket(R11-CONF-03b)` | later+interim | interim:R11-CONF-01 |
| F-519 | S1 | L2:NEW-2 | The resolver labels every multi-claim value 'uncontested': 0 dissent in 19,121 sampled multi-cl… | `ticket(R11-CONF-05)` | later+interim | interim:R11-CONF-01 |
| F-520 | S1 | L2:NEW-3 | Cross-layer duplicates: 13.5% of published points have a point from another source or layer wit… | `ticket(R11-CONF-07a)` | later+interim | interim:R11-CONF-01 |
| F-521 | S1 | L2:NEW-4 | Publisher recorded as camera operator for 74% of camera subjects; an 'OpenStreetMap contributor… | `ticket(R11-CONF-06)` | later+interim | interim:R11-CONF-01 |
| F-522 | S1 | L2:NEW-5 | No claim is bound to real captured bytes: all 2,782,187 claim-evidence bindings point at 285 ze… | `live-return-pass(R11-ACT-14)` | later+interim | interim:R11-K13-UXW0-2 |
| F-523 | S1 | L2:NEW-6 | Technology typing quantified: 77.4% of 'traffic_camera' subjects are ALPR (152,102), police CCT… | `ticket(R11-DATA-02)` | W1 |  |
| F-529 | S1 | L2:NEW-12 | Geometry gate quantified with polygons: 2,370 points lie more than 25 km outside their dossier'… | `ticket(R11-K13-JUR-02b)` | W1 |  |
| F-531 | S1 | L2:NEW-14 | 630 of 632 published sharing-edge rows (EFF & MuckRock CC-BY-4.0 data) are attributed '© The SI… | `ticket(R11-ACT-07)` | early |  |

**Later-wave fixes with a first-wave interim (8).** L1/L2's data-correctness S1s are fixed by L3's wave-2/3 chain
(CONF-03b → CONF-04 → CONF-05/06 → CONF-07a/b); their wave-1 interim is R11-CONF-01's quality suite in ratchet mode (L3 §3.3:
no regression past today; hard-enforce when the fixing ticket lands), and F-522's is UXW0-2 (synthetic captures labelled
"SIG did not store this document"). S2 should decide whether any of these chain units move into wave 1.

**F-366 is `already-done`** as a finding: it is I8's own correction of I7's plan (widening `osm_overpass` alone cannot
make OSM the ALPR origin). The plan now carries the code as R11-ACQ-17, a hard prerequisite of the Wave-C activation
R11-ACQ-18, so the defect cannot reach production; the code work itself is owned by R11-ACQ-17 (also F-325's home).

## 4. Items whose disposition is an operator decision (41)

| dec_id | S1c part | question (short) | items |
|---|---|---|---|
| D-J3-4 | A | Distribution host and monthly egress ceiling for downloads (with kill switch).… | F-386 |
| I7-C1 | A | TxDOT's origin terms ('distribution to third parties without TxDOT's written consent is strictly prohibited'; … | F-348 |
| I7-C6 | A | One operator statement: are SIG's use and exports non-commercial? (governs Bellevue, Honolulu PD, Canada.ca, O… | F-359 |
| Q-24 | A | Confirmatory evaluation aim: certify the 0.98 auto-write gate, or measure/disclose only?… | F-262 |
| Q-7 | A | Governance stance: adopt the disclosed single-maintainer, no-counsel posture package (A-4 members Q-E2-06/07/0… | F-31 |
| Q-E2-06 | A | SIG-PUB-008 (two independent reviewers before naming an individual) vs the sole-maintainer 'waiver'.… | U-0019 (D-P21.4-2), U-0295 (RISK-P0-05) |
| Q-E2-07 | A | 'An editorial board exists' (governance doc, API terms) vs none.… | U-0185 (SIG-GOV-015), U-0274 (BL-036), U-0297 (RISK-P0-10) |
| Q-E2-08 | A | Legal home: individual in personal capacity vs sponsor/entity before launch.… | U-0018 (D-P21.4-1), U-0183 (SIG-GOV-012), U-0184 (SIG-GOV-013), U-0272 (BL-034) |
| Q-E2-10 | A | Counsel requirements vs no counsel document (U-013: 'counsel' = the operator; don't block).… | U-0009 (D-LEGAL.1-1), U-0273 (BL-035), U-0332 (RISK-P10-17) |
| Q-E2-11 | A | Robots: re-confirm GL-GATE-08 (robots.txt recorded but not obeyed; 125 disregarded fetches on 122 hosts incl. … | F-199 |
| Q-E2-13 | A | GL-GATE-07 blanket approval vs fail-closed rights review and the database right (94 non-US compilations, 21,68… | F-195, F-471 |
| Q-E2-14 | A | ODbL residual: one map over all compartments on an operator-reported clearance (ADR-106).… | U-0045 (D-P30.3-COUNSEL), U-0350 (RISK-P16-16) |
| Q-E2-22 | A | SIG-CHART-025 'narrowly excellent at US ALPR' vs national/international all-camera breadth.… | U-0119 (SIG-CHART-025) |
| Q-L3-1 | A | Adopt 'derivation, not identity' (auto-collapse only mechanically verified copies C0–C2; inferential tiers nev… | F-208 |
| D-P30.2b-1 | B | Operator curation of 50–100 camsite seed items in the loopback app (2–8 h): do it, or supersede by L3's per-re… | U-0039 (D-P30.2b-1) |
| D-P32.3-1 | B | Legacy sig.org.name keys (keep/split/same_as per key; 1.7–42 h): fold into the D-K2-1 degree-ordered review an… | U-0057 (D-P32.3-1) |
| D-SOURCES.7-2 | B | Register the free per-platform US 511 API keys (operator sign-ups, stored in Secret Manager; HG-09) so the gat… | U-0087 (D-SOURCES.7-2) |
| E4-R1 | B | HG-03 D-JURIS.2-1 — declarationcamera_be (Belgian-eID leg only): which option? (GL-GATE-07: n/a (rights alread… | U-0007 (D-JURIS.2-1) |
| E4-R2a | B | HG-03 D-SOURCES.2-2 — documentcloud: which option? (GL-GATE-07: NOT COVERED (P26.16: "GL-GATE-07's camera-regi… | U-0083 (D-SOURCES.2-2) |
| E4-S2 | B | HG-03 D-SOURCES.9-2 — bonfire (status + decision): which option? (GL-GATE-07: ARGUABLE)… | U-0092 (D-SOURCES.9-2) |
| I7-C5 | B | Conflict C5: Revocation / destroy-on-request (NEW-3)… | F-360 |
| I7-C8 | B | Conflict C8: CourtListener bulk vs the deferred courtlistener_recap (I6 NEW-1; E4 R2b)… | F-354 |
| I8-Q5 | B | Round-11 acquisition scope: core ACQ-01…18 + 28 only, or also the conditional Tier-2 Wave D (ACQ-19…27)?… | CG-ACQ-19, CG-ACQ-20, CG-ACQ-21, CG-ACQ-22, CG-ACQ-23, CG-ACQ-24, CG-ACQ-25, CG-ACQ-26 |
| OD-12 | C | Backward confirmations (E2-X1) in your own words: (1) the 2026-09-16/24 'counsel' determinations were your own… | F-191 |

## 5. Wontfix and later-phase

### 5.1 Wontfix (14)

| item | source | reason | evidence |
|---|---|---|---|
| U-0003 | D-CCOPS.1-2 | operator skipped Stage-0 outreach (WONTFIX 2026-09-16) | docs/tickets/DEFERRALS.md:118 WONTFIX (events.jsonl head D-CCOPS.1-2:e |
| U-0008 | D-JURIS.2-2 | operator skipped Stage-0 outreach (WONTFIX 2026-09-16) | docs/tickets/DEFERRALS.md:103 WONTFIX (events.jsonl head D-JURIS.2-2:e |
| U-0015 | D-P21.1-2 | operator skipped Stage-0 outreach (WONTFIX 2026-09-16); requirement side waits on Q-E2-12 | docs/tickets/DEFERRALS.md:36 WONTFIX (events.jsonl head D-P21.1-2:e0) |
| U-0023 | D-P21.7-2 | operator declined the moderated usability study (WONTFIX); live-site study is LATER-02 | docs/tickets/DEFERRALS.md:44 WONTFIX (events.jsonl head D-P21.7-2:e0) |
| U-0121 | SIG-CHART-031 | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-CHART-031 |
| U-0124 | SIG-CHART-035 | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-CHART-035 |
| U-0182 | SIG-GEO-007 | rationale paragraph; obligation carried by SIG-GEO-006 | data/coverage_delta_F2a.csv SIG-GEO-007 |
| U-0204 | SIG-INGEST-044 | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-INGEST-044 |
| U-0205 | SIG-INGEST-045b | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-INGEST-045b |
| U-0209 | SIG-INGEST-048a | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-INGEST-048a |
| U-0210 | SIG-LIC-007 | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-LIC-007 |
| U-0247 | SIG-STORE-033 | N/A-RATIONALE: rationale statement with no build obligation | docs/build/COVERAGE_MATRIX.csv SIG-STORE-033 |
| U-0523 | MANIFEST-158 | unused row number: P31.17 DROPPED | docs/tickets/00_MANIFEST.md:343 |
| F-385 | I9b:NEW-6 | planning logging gap; the 8 query strings cannot be reconstructed (disclosed) | research/I9b-saturation.md |

### 5.2 Later-phase (153), grouped by landing

Every later-phase row names its trigger in `disposition`; a catalog `LATER-nn` unit carries the work when it fires.
Quiet ADR revisit triggers (F3 `trigger-quiet`) stay on the ADR's own trigger and are watched through the ADR trigger
register (SEED-15).

| landing | n | trigger (as written) | items |
|---|---:|---|---|
| LATER-01 — T-EVAL-IND segment: reviewer surface, pilot, freez | 24 | T-EVAL-IND: >=2 independent labellers available + outside contact authorised (L3 §6.5) | U-0040 D-P30.2b-2, U-0066 D-R6.1-EVAL, U-0076 D-R10-HUMAN-1, U-0129 SIG-DOS-002, U-0173 SIG-EVAL-002, U-0174 SIG-EVAL-005, U-0176 SIG-EVAL-007, U-0253 SIG-TRUST-010, U-0320 RISK-P5-05, U-0321 RISK-P5-06, U-0323 RISK-P5-11, U-0474 ADR-099, U-0491 ADR-116, U-0503 ADR-128, U-0504 ADR-129, U-0521 HUMAN-H4, U-0522 HUMAN-H5, U-0525 MANIFEST-184, U-0526 MANIFEST-185, U-0527 MANIFEST-186, U-0528 MANIFEST-187, F-202, F-203, F-260 |
| LATER-02 — Usability study on the live site | 6 | participants available and outside contact authorised | U-0081 D-R10-USERS-1, U-0254 SIG-UI-001, U-0278 BL-040, U-0345 RISK-P16-06, U-0468 ADR-093, F-205 |
| LATER-03 — Contribution-back to OSM/MapRoulette | 5 | operator opts into contribution-back (U-011 revisited; HG-08 key + OE page) | U-0022 D-P21.7-1, U-0277 BL-039, U-0355 RISK-P18-14, U-0431 ADR-055, U-0444 ADR-069 |
| LATER-04 — Outreach, records-request sending and recruiting | 7 | operator authorises outside contact (Q-E2-12 a: outreach becomes an owed later-phase obligation by ADR) | U-0074 D-R7.2-SEND, U-0122 SIG-CHART-033, U-0125 SIG-CONTRIB-012, U-0126 SIG-CONTRIB-012a, U-0127 SIG-CONTRIB-013, U-0192 SIG-GOV-024, U-0347 RISK-P16-13 |
| LATER-05 — Counsel packet and written opinion | 1 | operator obtains counsel (one-off ≈$0 pro bono or ≈$3.5k-10.5k paid). | F-204 |
| LATER-06 — Authenticated contributor accounts (D-R7.1-AUTH) | 2 | demonstrated demand beyond the vetted curator set + moderation plan + threat model | U-0072 D-R7.1-AUTH, U-0475 ADR-100 |
| LATER-07 — Know-your-rights content (BL-041) | 2 | the correction-intake receiver opens (Q-27 b) or contributor onboarding launches | U-0279 BL-041, U-0346 RISK-P16-08 |
| LATER-08 — Cloud SQL permanent scale-up and HA; disk partitio | 2 | ADR-022 trigger: measured claim scan/maintenance over budget (Round-11 capacity plan, Q-23) | U-0261 BL-003, U-0398 ADR-022 |
| LATER-09 — Acquisition long tail: Tier-2 remainder (130), Tie | 46 | per-family trigger in each group's disposition (I8 §6.3, I7) | 43 candidate groups (389 candidates); F-363, F-377, F-380 |
| LATER-10 — Non-US keyed traffic APIs (QLDTraffic, NSW) (D-SOU | 1 | non-US keyed traffic APIs wanted (D3 US-first revisited; D-SOURCES.8-2 answered a) | U-0090 D-SOURCES.8-2 |
| LATER-11 — OCR/model-assisted parsing (BL-025 OCR part) | 3 | a Stream-I source needs model-assisted extraction (SIG-LLM-001) | U-0322 RISK-P5-10, U-0325 RISK-P7-05, U-0506 ADR-131 |
| LATER-12 — Deferred UX: claim-text/entity-scoped search, ZIP  | 1 | CAP-01 passes and entity-scoped search is prioritised (K3 SRCH-09) | F-466 |
| LATER-13 — Closeout journal cutover (closeout-op/1) | 3 | parallel dispatch, a multi-worktree build or a second harness writing memory concurrently. | U-0502 ADR-127, F-069, F-070 |
| LATER-17 — OpenGov procurement source (D-SOURCES.9-3) | 1 | a documented public OpenGov Procurement endpoint with reviewable terms emerges | U-0093 D-SOURCES.9-3 |
| LATER-22 — Round-11 announcement and public launch | 1 | CAP-02 announce-readiness passes and the operator says go (D3 §5) | U-009 |
| ADR revisit trigger (quiet) | 45 | each ADR's own `## Revisit trigger` (quiet today) | ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-018, ADR-019, ADR-020, ADR-023, ADR-024, ADR-025, ADR-043, ADR-044, ADR-045, ADR-072, ADR-078, ADR-087, ADR-089, ADR-091, ADR-094, ADR-095, ADR-097, ADR-108, ADR-109, ADR-112, ADR-113, ADR-115, ADR-118, ADR-119, ADR-121, ADR-123, ADR-124, ADR-133, ADR-134, ADR-135, ADR-136, ADR-143, ADR-144 |
| RISK-P14-10 trigger (F3) | 1 | consumer demand for GraphQL (SIG-API-010 SHOULD) | U-0340 RISK-P14-10 |
| RISK-P4-08 trigger (F3) | 1 | a later claim contradicts an Atlas row | U-0317 RISK-P4-08 |
| ontology technology-vocabulary version bump | 1 | next technology-vocabulary version of the ontology | U-0223 SIG-ONTO-057a |

## 6. Items that could not be disposed

**None.** Every universe row, finding, feedback item and candidate group has exactly one valid disposition (rule a/b).
Residue that S2/S3 must still settle is carried explicitly instead of being left undisposed:
- the 8 S0/S1 later-wave fixes (§3) and the wave-ordering constraint on the §2.1 set;
- 41 decision-dependent items (§4) — their final kind is fixed when the operator answers at S5;
- the 61 unsampled boilerplate MET-DIFFERENTLY requirements go to SEED-14 for a row-by-row re-verdict (F2b §4), so their
  true state (MET / PARTIAL / MISSING) is not known until T4.

## 7. Orphan catalog units (no item points at them)

25 of 317 units. Each is justified by the design row named in its `merged_from` — they are process,
acceptance or enabling units that no owed item, finding or ask names directly:

| cat_id | class | title | justified by (design row) |
|---|---|---|---|
| SEED-01 | seed | C0 seed preflight: operator go for control-ledger edits, A1 delta, <PR | B3 §5.1 C0; B2 Q3 |
| SEED-04 | seed | C1 reports/memory-repair: README, date_corrections.csv, append_only_re | B3 C1; B1 §5.1 (register promotion); B2 §6 |
| SEED-19 | seed | T6 orient dry-run, HANDOFF.md, GATE-B; C10 flips the LEDGER to IN_PROG | B3 §5.3; B3 C10; T6 |
| R11-MEM-10 | r11 | Round-close record checks (G9 + capstone two-sum + tail probe-sweep co | B4 rec-tail; B4 G9; B4 G7 item 5; B4 G10 (tail contract); DRAFT-ENG-5; F2b §2.4 capstone r |
| R11-ACT-17b | r11 | Withdrawal-barrier bytes: tombstones, alias coverage, entity stubs, /r | F5 PKG-03b (nginx half, ED-18..ED-20 part); DR-C4-08; DR-C4-09; DR-C4-10; G3 §11 ('PKG-03b |
| R11-OPS-05 | r11 | Ops runbook (docs/ops/RUNBOOK.md) + stale ops doc fixes | G1-15; G1 §3.10; SIG-OPS-010 |
| R11-REL-04a | r11 | Verification suite A: V1-V5, V11-V13 (REL-04a) | G3 REL-04a; G3 §5.5 |
| R11-REL-11 | r11 | Second-release acceptance (REL-11) | G3 REL-11 |
| R11-CONF-08 | r11 | Real-data regression corpus + perturbation and hard-negative harnesses | L3 CONF-08; L3 §3.5 |
| R11-CONF-10 | r11 | Agent review lane (two blind contexts; never gates) | L3 CONF-10; L3 §4.3 |
| LATER-14 | later | Whole-LEDGER rotation per round | B3 §3.14; B6 tier D |
| LATER-15 | later | Operator-only signing key for gate signatures (G4c) | B4 G4c; Q-B4-2; B6 tier D |
| LATER-16 | later | Whole-graph canvas (>3,000 labelled nodes) | D3 §4 later list; K0 revisit trigger 3; D-K13-1 |
| LATER-18 | later | Second model family for agent review | L3 Q-L3-4 |
| LATER-20 | later | Legacy bucket retirement | G3 D-G3-7 |
| LATER-21 | later | Move CI runners to Ubuntu 26 | H2 TC-PIN item 4 note |
| OP-02 | operator | Apply skill changes Tier B-must (SK-01, 02, 03, 06, 09, 10) | B6 SK-01, SK-02, SK-03, SK-06, SK-09, SK-10 |
| OP-03 | operator | Apply skill changes Tier B-should (SK-04, 05, 07, 08, 11, 12, 15 min) | B6 SK-04, SK-05, SK-07, SK-08, SK-11, SK-12, SK-15 (items 1, 2, 10) |
| OP-04 | operator | Apply skill changes Tier C (SK-15 rest, 16, 21, 23, 24, 25) | B6 SK-15 (rest), SK-16, SK-21, SK-23, SK-24, SK-25 |
| OP-05 | operator | GitHub settings before the seed push: stack ruleset (S-2) + merge sett | H2 §5 S-2, S-3; H1 §3.1 |
| OP-17 | operator | Maintainer check (OPCHECK) per Class-S release | L3 §4.4; Q-L3-3 |
| OP-20 | operator | Create and hold the release-signing key (minisign) in Secret Manager | D-J3-8 |
| OP-21 | operator | Held-out search relevance set (≈30 min) | D-K3-7 |
| OP-22 | operator | Operator walkthroughs and sign-offs: journeys, 'beautiful' gallery, co | D3 §2; D-K14-9; D-J3-12; G2 §6 claim rules |
| OP-23 | operator | Push the planning branch as an off-disk backup (optional) | H2 Q-H2-6 |

Referenced units: 292 of 317; units that are some item's **primary** landing: 209.

## 8. The check (`tools/check_dispositions.py`)

Stdlib only; reads the sources, never writes. `python3 docs/build/planning/2026-09-30-next-phase/tools/check_dispositions.py`
exits 0 when all rules pass. Rules:

- **(a) exactly once** — the expected id set is re-derived from UNIVERSE.csv, FINDINGS.csv, OPERATOR_FEEDBACK.md and the
  acquisition plan; each appears once with the right `source_kind`/`source_ref`; candidate-group sizes match; every candidate
  id sits in exactly one plan row and every consolidated candidate is in the plan.
- **(b) enum and references** — `kind(arg)` parses; kind ∈ enum; ticket → seed/r11 unit, live-return-pass → r11,
  operator-action → OP-nn, spec-amendment → SEED-12, adr-waiver → SEED-11, decision → S1c dec_id, later-phase → explicit
  trigger and (if a catalog ref) a LATER unit; merged-into targets exist and are not merged themselves; every link token
  (cat id, `gate:`, `interim:`, U-/F-/CG- ids) resolves.
- **(c) S0/S1** — after merged-into, a first-wave unit (§2.1), a decision, already-done evidence, or a later fix with a
  first-wave `interim:`; never wontfix.
- **(d) operator asks** — U-003.1…11 each resolve to ≥ 1 seed/R11 ticket (they cite 6–17 K13 tickets each, K13 §5.1).
- **(e) owed deferrals** — all 36 OPEN/PARTIAL rows disposed; later-phase ones name a trigger.

Output at render time:

```
rows 1159 {'deferral': 97, 'requirement': 161, 'backlog': 36, 'risk': 62, 'ledger_finding': 1, 'return_pass': 19, 'adr_trigger': 144, 'readout': 2, 'manifest_row': 6, 'finding': 538, 'feedback': 28, 'candidate_group': 65}; first-wave units 133
S0/S1 resolution {'first-wave unit': 101, 'decision': 3, 'already-done': 1, 'later fix + first-wave interim': 8}; owed deferrals 36 -> {'ticket': 10, 'decision': 6, 'already-done': 2, 'live-return-pass': 9, 'later-phase': 9}
check_dispositions: OK (0 errors)
```

Tests: `uv run python -m pytest docs/build/planning/2026-09-30-next-phase/tools/test_check_dispositions.py` (36 tests: one
fixture per rule and failure mode; not collected by `make check`, whose testpaths are `tests/`).

## 9. Inputs (sha256, first 16 hex)

- `universe/UNIVERSE.csv` `e2776930d08211ec`
- `findings/FINDINGS.csv` `1cbdc67ef08f9d69`
- `feedback/OPERATOR_FEEDBACK.md` `4dec0ffe20b11fe4`
- `data/ticket_catalog.csv` `cc6465e299c45071`
- `data/decision_catalog.csv` `b1beef7d62a904a6`
- `data/owed_register_adjudication.csv` `a603650b3048efc2`
- `data/coverage_delta_F2a.csv` `c66adbe30f549018`
- `data/coverage_delta_F2b.csv` `8c673f624cb0cdf8`
- `data/backlog_triage.csv` `e111b724f5a953da`
- `data/acquisition_plan.csv` `dd4bde7e748cdf0e`
- `data/candidates_consolidated.csv` `1340006905bb00bd`
- `data/k13_tickets.csv` `af71a9832b1eb723`
- `universe/UNIVERSE_DISPOSED.csv` `7d297a1855df1cfb`

The CSV was produced by a scratch builder outside the repository (hand decisions are in its tables, each citing the row
whose recommendation it applies); the CSV itself is the artifact, and the checker re-validates it from the sources.
