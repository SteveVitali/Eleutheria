# C6 — Review synthesis: product themes and draft requirements

Row **C6** of `META_PLAN.md` (Stage P, owner P). Written 2026-09-30T18:26Z onward (`date -u`) in the planning worktree
`/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `07ef0142`). `PD` below means
`docs/build/planning/2026-09-30-next-phase`. Companion data: [`../data/review_themes.csv`](../data/review_themes.csv)
(one row per theme).

> **Hold from the operator until D1 is complete (P8).** At the time of writing, `feedback/OPERATOR_FEEDBACK.md` holds
> U-001 and U-002 only; Q-D1-03 onward is unanswered. D2 is where the operator reacts to this file.
>
> **Agent synthesis, not user research (P4/P5).** It rests on agent walkthroughs (C2, C4) and a number trace (C3). Nothing
> here counts toward `D-R10-USERS-1` or any human-evaluation obligation. Every requirement below is **agent-drafted**
> (`DR-C6-nn`, provisional ids). S2/S3 own the ids and wording, and the operator ratifies at S5.

**Inputs read.**
- `META_PLAN.md`: §3, the C-stream and D-stream rows, §7 and §7.1, §8.2.
- `review/PROTOCOL.md` (C1): personas, heuristics, severity calibration.
- `review/JOURNEYS.md` and `findings/incoming/C2.csv` (34 rows).
- `review/DATA_TRUTH.md` and `findings/incoming/C3.csv` (21 rows).
- `review/R10_PREVIEW.md` and `findings/incoming/C4.csv` (32 rows).
- `findings/FINDINGS.md` and `FINDINGS.csv` (F-01…F-44).
- Titles and routing of every other `findings/incoming/*.csv`, plus the full text of the rows cited as linked.
- `feedback/OPERATOR_FEEDBACK.md`.
- `design/G2-activation.md` §0, §5 and the ACT table.
- `design/E2-governance-options.md` §0.1 (H-1…H-9).
- `research/F5-eng-debt.md` §0 and PKG-03…PKG-12.
- `research/J1-exposure-inventory.md` §0.
- Spec text for SIG-UI-001/002/013/014/014a/014b/026/027/027a/033/035/044 and SIG-CHART-008 (J-1…J-4).
- `docs/build/COVERAGE_MATRIX.csv` verdict column, for every spec id cited by C2/C3/C4.

**Not read.** `research/C5-landscape.md` (C5 was still running when this row started). S1 merges C5.

**Production.** No production reads. The only code read was `exports/src/exports/spine_export.py:994-995` and
`web/src/pages/network.astro:49`, to find the cause of the UUID labels.

**Part VIII.** Personal account handles, and one surname used as a source id, are **not** reproduced here. They appear as
`[redacted]`, following C2/C3.

---

## 0. Summary

- **87 C-stream findings resolve to 60 unique product issues** (`RI-01…RI-60`, §2):

  | severity | unique issues | raw C-stream findings (C2 + C3 + C4) |
  |---|---|---|
  | S0 | **6** | 4 |
  | S1 | **26** | 33 |
  | S2 | **26** | 45 |
  | S3 | **2** | 5 |

  S0 grows from 4 raw findings (3 root causes) to 6 unique issues. Three issues take the higher rating already recorded
  on a linked row:
  - the dispute channel (F-03, re-rated S0 by A2);
  - the fixture editorial review (E1 NEW-1, S0);
  - misattribution (E2 H-2 citing J1 NEW-2, and §7.1's list of S0 hotfixes).

  Two S1 issues become **S0 on exposure**: RI-23 (stand-in research dossiers) and RI-24 (the fixture release candidate).
- **Spec pressure.** C2/C3/C4 cite **89 distinct spec ids**. **86 of them read `MET`** in `COVERAGE_MATRIX.csv`; the
  others are SIG-CHART-011 `MET-DIFFERENTLY`, SIG-EVAL-006 `MISSING` and SIG-UI-010 `AT-RISK-INTEGRATION` (code
  evidence, §4). Most live product failures are therefore **violations of requirements recorded as met**, not new
  needs. That is direct input to F2/T4 (§8.3 `MET-ENGINEERED`/`PARTIAL`).
- **Themes, ranked (§3):**
  1. TH-02 Rights, attribution and Part VIII safety (S0)
  2. TH-01 Honesty of public claims and fixtures shown as real (S0)
  3. TH-13 Corrections and disputes (S0)
  4. TH-07 Downloads, API and data access (S0)
  5. TH-03 Provenance and evidence linkage (S1)
  6. TH-04 Jurisdiction, geometry and count correctness (S1)
  7. TH-05 Findability, IA, navigation and search (S1)
  8. TH-12 Epistemic legibility: absence, contradictions, freshness (S1)
  9. TH-10 The printed dossier (S1)
  10. TH-08 Citations, permalinks and release identity (S1)
  11. TH-06 Map and network (S1)
  12. TH-16 Round-10 surfaces readiness (S1, S0 on exposure)
  13. TH-09 Journalist workflow: sourced headline numbers (S2 owned, fails via 3/5/10)
  14. TH-11 Organizer workflow: local action (S2 owned, fails via 4/6/8/11)
  15. TH-14 Performance budgets (S2)
  16. TH-15 Accessibility (S2)
- **The co-primary audiences fare worst** (C2 §4):
  - journalist: 0 of 3 tasks succeeded;
  - organizer-like personas (resident, contributor, OSM contributor): 0 of 6;
  - design centre (P1): 0 of 4 full successes;
  - 10 of 31 tasks carry wrong-conclusion risk.

  The site shows the *shape* of an evidence-first record (glyphs, cite blocks, gap markers), but a reader cannot reach
  the *substance*. Nothing is named, no figure leads to evidence or data, and the permalinks, the review and the dispute
  channel are asserted rather than operated.
- **The five draft requirements that matter most:**
  1. **DR-C6-05/06, no fixture or unbound status word in production.** A build and publish guard, plus status words
     derived only from recorded state.
  2. **DR-C6-01/02, a publish-time rights and Part VIII gate.** Neutral source ids, and per-source upstream
     attribution on every row, tile and API obligation.
  3. **DR-C6-18/19, figure → named source → evidence in ≤2 clicks.** This is the defining standard, and the
     journalist's core task.
  4. **DR-C6-21/22/23, jurisdiction and geometry correctness.**
     - One canonical key.
     - A point-in-polygon gate.
     - `unresolved` is not a jurisdiction.
  5. **DR-C6-27/30, the design centre's first two minutes.**
     - A place name finds its record.
     - Every unknown states its kind of absence and what would close it.
- **Quick wins (§6).** About 15 copy and small-code fixes, all shippable in G2's ACT-06 republish:
  - fixtures removed;
  - editorial standards say "not yet performed";
  - an honest dispute notice;
  - methodology wording;
  - the "reproducible" claim dropped until it is true, and the release id shown;
  - "How we know this" labelled site-wide;
  - jurisdiction display names;
  - a 404 page and a sitemap;
  - honest task-page copy.
- **Before any public promotion (§7).** All six S0s closed and verified live. No unbound status claims. Jurisdiction and
  geometry correctness. The §5 acceptance journeys pass for the design centre, journalists and organizers with no
  wrong-conclusion risk. Downloads linked only behind the low-egress path. Round-10 surfaces kept dark until G2 step 7
  (HG-11).

---

## 1. Method

**Deduplication.**
- One unique issue (RI) per root cause, following PROTOCOL §6.6.
- A finding that spans two root causes is split and marked `(part)`.
- Rows from other streams are **linked**, not re-counted. Each RI lists the C2/C3/C4 findings it absorbs and the
  F-/other-row ids it overlaps, so S1 can dispose of them together (P9).
- Id convention: `C2 NEW-n` means `findings/incoming/C2.csv` row NEW-n, and the same for other rows.

**Severity.**
- An RI takes the **highest** severity among its sources, including linked rows already rated by A2 or a design row
  (§8.2). When it inherits a higher rating, it says so.
- Within a severity band, RIs are ranked by impact on the design centre, journalist and organizer tasks
  (wrong-conclusion risk first), then by breadth.

**Themes.**
- Each RI has exactly **one** primary theme; cross-theme effects are noted.
- Themes are ranked by maximum severity, then by the same persona impact.
- Personas follow PROTOCOL §3:
  - P1 local advocate (the design centre)
  - P2 journalist
  - P3 researcher
  - P4 attorney
  - P5 council staffer
  - P6 resident
  - P7 developer
  - P8 contributor
  - P9 OSM/DeFlock contributor
  - P10 agency or vendor
  - P11 skeptic
  - P12 mobile visitor

  Per U-002, "organizers" means P1 plus the organizer lens on P6, P8 and P9.

**Requirements.**
- `DR-C6-nn` are drafted as MUST/SHOULD, each with a testable acceptance criterion and a measurable target.
- Where C3 or C4 already drafted the same requirement (`DR-C3-nn`, `DR-C4-nn`), this file **adopts** it by id rather
  than restating it.

**Sizes** (agent effort, excluding operator gates):
- **S**: ≤1 agent-day, usually copy or small code in one republish.
- **M**: one ticket.
- **L**: one F5-sized package, 2–3 tickets.
- **XL**: several packages, or work gated on live, operator or human steps.

**Evidence class.** This file's clustering, ranking and drafting are **inference** over the cited findings. The
verdict tallies (§4) and the network-label cause (TH-06) are **code** evidence, read at HEAD `07ef0142`.

**Chain tip vs live** (PROTOCOL U4). The live web build is `5c064881`; the chain tip is `b051732c`.
- **Changed at the chain tip but still open:**
  - dispute copy (RI-04): the tip adds "not yet operating" but no channel, and says "anonymous";
  - permalinks (RI-14): release namespaces exist but are undeployed;
  - islands (RI-16, RI-22, RI-48): P32.15 changed them, and they are measured on fixtures only.
- Every other theme's root cause is unchanged at the chain tip (C2/C3 `chain_tip=same`), or is a data or export
  defect.

---

## 2. Unique product issues, severity-ranked

`(y)` marks a C2/C4 task that carries wrong-conclusion risk.

| RI | sev | issue | absorbs (C-stream) | linked (other rows) | theme | persona / task (C2/C4 verdict) |
|---|---|---|---|---|---|---|
| RI-01 | **S0** | Personal ArcGIS account handles embedded in public source ids (58 `camreg_*` keys; 31 look personal) | C2 NEW-2; C3 NEW-2 | J4 NEW-6 (a surname used as a source id, `[redacted]`) | TH-02 | P10-T3 success; data subjects |
| RI-02 | **S0** | Public API `/v1/dossier/<any>` returns the same 25 unrelated subjects and 10 sources (incl. OKC fixture ids); `/v1/coverage` says `complete:true` with 0 evaluated | C3 NEW-1; C3 NEW-10 | G2 NEW-6; F3 NEW-6; J4 NEW-6; E2 H-5 | TH-07 | P7; P2 |
| RI-03 | **S0**¹ | Third-party data credited to "© SIG contributors" or "DeFlock community map"; 61,603 rows have a required attribution left empty | C2 NEW-16; C3 NEW-9 | E1 NEW-4; J1 NEW-2; J1 NEW-3; J4 NEW-3; E2 H-2 | TH-02 | P9-T1 partial |
| RI-04 | **S0**² | Every page promises a one-click correction channel; `/dispute/` has no channel and no notice | C2 NEW-3; C4 NEW-20 | F-03; G2 NEW-5; E2 H-3 | TH-13 | P10-T1 **fail** (y) |
| RI-05 | **S0** | `/visual-language/` asserts unlabelled fixture facts about real named agencies and a vendor; 6 demo `agency:okcpd` task pages are served; fixture builds use real names with no marker | C2 NEW-1; C2 NEW-12 (part); C4 NEW-27 | G1 NEW-7 | TH-01 | P11; P10; the named agencies |
| RI-06 | **S0**³ | `/editorial-standards/` presents a fixture two-reviewer "Releasable" review of a non-existent dossier | C2 NEW-12 (part) | E1 NEW-1; E3 NEW-1; E2 NEW-1; E2 H-1 | TH-01 | P10; P11; P5-T2 partial |
| RI-07 | S1 | No path from any displayed figure to its evidence; `/evidence/` is empty; the "2423200 of 2423200 … resolvable evidence" headline cannot be checked | C2 NEW-7; C3 NEW-12 (part) | J1 NEW-4; J1 NEW-8; J1 NEW-10 | TH-03 | P2-T1 **fail**; P4-T1 **fail**; P11-T1 **fail** |
| RI-08 | S1 | Sources shown only as internal keys, with no publisher, link, date or licence | C2 NEW-15 | J1 NEW-7 | TH-03 | P1-T1 (y); P2-T2 (y); P10-T3 |
| RI-09 | S1 | Jurisdictions shown only as bare codes; place-name search ("Maryland", "Canberra") returns 0 | C2 NEW-10 | F-04 (part) | TH-05 | P1-T1 (y); P6-T1 **fail** (y); P5-T1 |
| RI-10 | S1 | Code collisions merge different places into one dossier (ID = Idaho + Indonesia, MN = Minnesota + Mongolia, DE, CO/CO-MET); schemes are mixed | C3 NEW-14 (part); C3 NEW-6 (part) | F-44; F-04; I1 NEW-1 | TH-04 | P1; P2; P5 |
| RI-11 | S1 | "Geolocated in <J>" counts include points located elsewhere: 838 central-Florida points in CA, 562 axis-swapped in GB-ENG, 155 Hong Kong points in TH, 15 at (0,0), sign flips | C3 NEW-6 | I1 NEW-2 | TH-04 | P2; P5-T1 |
| RI-12 | S1 | Dossier "unknown" values omit the kind of absence; 5 sections render as bare headings; the banner says "1 unresearched field" while 12 show unknown | C2 NEW-5; C3 NEW-7 | F2a NEW-1 (Timeline has no production writer) | TH-12 | P1-T2 (y); P6-T1 |
| RI-13 | S1 | Printed dossiers: no as-of or permalink on page 1 (research-dossier prints: none on any page); orphan and empty pages; no licence | C2 NEW-6; C4 NEW-23 | — | TH-10 | P1-T3 partial |
| RI-14 | S1 | "Belief-pinned" permalinks ignore their as-of and ruleset parameters; canonical ≠ permalink | C2 NEW-4 | F-07; J1 NEW-5 | TH-08 | P2-T2 (y) |
| RI-15 | S1 | Bulk data, manifest, API and terms are linked nowhere; site `/terms` is 404; the export index points at a 404 | C2 NEW-8 | J1 NEW-1; F-09 (part) | TH-07 | P3-T1 **fail**; P7-T1 **fail**; P11-T1 **fail** |
| RI-16 | S1 | The map renders a few dozen points on a blank canvas, with no basemap, and nothing at street zoom | C2 NEW-9 | — | TH-06 | P6-T1/T2 **fail** (y); P12-T2 **fail** (y) |
| RI-17 | S1 | "How we know this" shows national totals on every dossier (218 sources on a 4-source page); labels misdescribe their values; the tier sum is 6 short, unexplained | C2 NEW-14; C3 NEW-3; C3 NEW-13; C3 NEW-12 (part) | F-05 | TH-03 | P11-T2 **fail** (y) |
| RI-18 | S1 | Methodology calls the holdout "human-verified"; P/R/F1 = 1.000 rests on one pair; the κ row is malformed; the figures predate the release | C2 NEW-13; C3 NEW-4; C3 NEW-20 | F-06; E1 NEW-10; E2 H-4 | TH-01 | P11; P3-T3; P2 |
| RI-19 | S1 | The `unresolved` bucket (71.4% of subjects, all 154,528 OSM ALPR nodes) counts as one of 55 "jurisdictions"; 22 US states, including the Oklahoma pilot, have no dossier | C3 NEW-14 (part); C2 NEW-30 (part) | F-04; I1 NEW-4 | TH-04 | P3-T2; P1 |
| RI-20 | S1 | "Resolved" is computed two ways: coverage says 232,625 of 232,625 have a resolved latitude while 5,290 are withheld as conflicting; the numerator is clamped | C3 NEW-5 | I1 NEW-3 | TH-04 | P3; P2 |
| RI-21 | S1 | Freshness shows "178 ok / 0 stale" where staleness was never evaluable; no data age; 41 evidence sources have no row | C2 NEW-29; C3 NEW-8; C3 NEW-21 | F-08; G1 NEW-13 | TH-12 | P3; P11 |
| RI-22 | S1 | The network names no entity (131 UUID nodes) and shows one edge type with no access-type filter; archive records do not type their edges | C2 NEW-11; C4 NEW-6 | F-09 (part) | TH-06 | P4-T2 partial; C4 T4 (y) |
| RI-23 | S1⁴ | Research dossiers present hand-authored stand-in documents as captures, with real URLs and future retrieval dates | C4 NEW-2; C4 NEW-32 | F-16; B1 NEW-3; E3 NEW-3 | TH-16 | C4 P1-T1/T2 (y) |
| RI-24 | S1⁴ | No real production candidate exists. The G3 candidate holds 0 records, with `example.test` evidence, a future as-of and "Completeness: complete". The export-mode build fails | C4 NEW-11; C4 NEW-26; C4 NEW-31 | F-15; B1 NEW-2; F5 NEW-5 | TH-16 | all Round-10 tasks |
| RI-25 | S1 | The research dossier is headed "Reviewed" while `review_status=not_run` | C4 NEW-3 | — | TH-16 | C4 T7 (y) |
| RI-26 | S1 | Release-archive links are one level too shallow: 150 of 164 crawled URLs are non-200 | C4 NEW-1 | — | TH-16 | C4 T1, T3 abandoned |
| RI-27 | S1 | No production wiring exists for `/v1` release search or `/intake` | C4 NEW-9 | F-14 | TH-16 | C4 T2, T6 |
| RI-28 | S1 | The web deploy's `rsync --delete` would erase the release tree; `/releases/index.html` has two generators | C4 NEW-10 | F-02; G1 NEW-6 | TH-16 | P2 (citations) |
| RI-29 | S1 | Release-archive pages have no dispute link and no navigation | C4 NEW-5 | — | TH-16 | C4 T6 abandoned |
| RI-30 | S1 | Released dossiers omit the provisional posture and nothing links to them | C4 NEW-7 | — | TH-16 | C4 T7 (y) |
| RI-31 | S1 | Empty release search asserts "recorded absence, not missing research" | C4 NEW-4 | — | TH-16 | C4 T5 (y) |
| RI-32 | S1 | The moderation reviewer detail route returns HTTP 500 with the PostgreSQL intake store | C4 NEW-8 | — | TH-13 | C4 T6 |
| RI-33 | S2 | Home and `/coverage-metrics/` are 126 "N of N" tiles with snake_case names and requirement ids; the reader's figure comes last (36,036 px on a phone) | C2 NEW-17 | F-09 (part) | TH-09 | P2-T1 **fail**; P3-T2 |
| RI-34 | S2 | Three different "site" counts appear under similar labels (232,625 / 227,335 / 223,901) | C2 NEW-18 | — | TH-09 | P2-T1 (y) |
| RI-35 | S2 | Contested figures carry no marker on dossiers; "2 open of 2" contradictions omits 5,290 coordinate conflicts | C2 NEW-20; C3 NEW-11 | — | TH-12 | P2-T3 partial |
| RI-36 | S2 | "Resolved sites" is shown without the PROVISIONAL disclosure the methodology promises | C2 NEW-19 | — | TH-01 | P2 |
| RI-37 | S2 | Several displayed numbers cannot be traced to any public release artifact (hard-coded eval constants, restricted `leverage.json` and density bins) | C3 NEW-18 | F2b NEW-8 | TH-09 | P11-T1 **fail** |
| RI-38 | S2 | Coverage and methodology copy promise bounds, per-agency ratios and survey recall that the release does not contain | C2 NEW-30 (part); C3 NEW-15 | — | TH-01 | P3-T2 |
| RI-39 | S2 | No page shows the release id, resolver version, snapshot date, a definition of "evaluable", or SIG's avoidance position | C2 NEW-28 | F-11 | TH-08 | P3-T3; P5-T2; P2-T2 |
| RI-40 | S2 | The research queue has one filter option ("Unscoped — 243,761"), UUID cards and no geographic scope | C2 NEW-21 | — | TH-11 | P8-T1 **fail** |
| RI-41 | S2 | Task pages claim a task "has been generated" on a static GET and say nothing about how to help | C2 NEW-22 | G1 NEW-7 | TH-11 | P8-T2 (y) |
| RI-42 | S2 | No licence, attribution or release id on dossier pages, JSON, prints, or research and released dossiers; no site licence statement | C2 NEW-31; C4 NEW-22 | — | TH-02 | P7-T2; P9-T1; P1-T3 |
| RI-43 | S2 | Portal bulk files duplicate 4,369 site rows; manifest `row_count` counts rows, not sites; no data dictionary | C3 NEW-17 | J1 NEW-11 | TH-07 | P3 |
| RI-44 | S2 | 23,566 same-source exact-duplicate points (3,161 with the same label), possibly double ingestion (S1 if confirmed) | C3 NEW-19 | — | TH-04 | P2; P5 |
| RI-45 | S2 | Map "Layers" are inert labels; the legend lists layers with no public data; popups show a UUID or "unresolved" with no source, date or licence | C2 NEW-23 | — | TH-06 | P4-T2; P6 |
| RI-46 | S2 | The map table prints counts the figure suppresses (601 low-coverage cells) under a "Devices" header | C3 NEW-16 | — | TH-06 | P6; P2 |
| RI-47 | S2 | Mobile map: the attribution covers a tiny viewport, and the list exists only on the 3.4 MB island page | C2 NEW-32 | — | TH-14 | P12-T2 (y) |
| RI-48 | S2 | Islands exceed their byte budgets or shift layout (CLS 0.31/0.33); budgets were never measured on real data | C2 NEW-24; C4 NEW-25 | — | TH-14 | P12-T2 |
| RI-49 | S2 | Reflow fails at 320 px; label-in-name mismatch on every page; duplicate landmarks; 5,290 tab stops on `/map/` | C2 NEW-25; C4 NEW-21 | — | TH-15 | P12 |
| RI-50 | S2 | Internal identifiers in public copy: requirement ids, snake_case names, UUIDs, raw enums, gate names | C4 NEW-28; C4 NEW-20 (part); C2 H05 scorecard | — | TH-05 | all |
| RI-51 | S2 | No sitemap; one generic meta description; duplicate titles; no Dataset metadata; no HSTS or CSP | C2 NEW-27 | F-09 (part) | TH-05 | P3; P7 |
| RI-52 | S2 | Error states are raw server output: bare nginx 404/403, JSON errors to HTML clients, 403 at `/r/<pub>/` | C2 NEW-26; C4 NEW-13; C4 NEW-29 | — | TH-05 | all |
| RI-53 | S2 | Workspace "Investigation views" links drop the query; the no-JS quick filter is empty | C4 NEW-24 | — | TH-06 | P6; P2 |
| RI-54 | S2 | Withdrawn routes get nginx's generic 410; the `/index.html` alias bypasses the deny map | C4 NEW-14 | G2 NEW-2 | TH-16 | P10; data subjects |
| RI-55 | S2 | Release-search scope counts omit runtime withdrawals | C4 NEW-12 | — | TH-16 | P3 |
| RI-56 | S2 | Reporter status shows only "resolved": no outcome, response or correction link | C4 NEW-17 | — | TH-13 | P10 |
| RI-57 | S2 | The intake form defaults to "Privacy harm", lacks a viewport meta and needs hand-typed record ids | C4 NEW-19 | — | TH-13 | P10 |
| RI-58 | S2 | The intake gate opens without an owner or staffing; the limiter keys on the proxy peer; demo tokens are accepted; an approved proposal can be unapplicable | C4 NEW-15; C4 NEW-16; C4 NEW-30; C4 NEW-18 | — | TH-13 | P10; data subjects |
| RI-59 | S3 | Contribution-back links to `/methodology/` for content it lacks; CC0 is not stated | C2 NEW-33 | F2b NEW-8 | TH-05 | P9-T2 partial |
| RI-60 | S3 | The corrections log gives no start date and does not say why its counts are structurally zero | C2 NEW-34 | — | TH-13 | P11-T3 partial |

Notes:
1. C2/C3 rated RI-03 S1. It is S0 per E2 H-2 (citing the J1 NEW-2 ruling) and the §7.1 "attribution takedown" S0
   hotfix.
2. C2 rated RI-04 S1; A2 re-rated F-03 to S0.
3. C2 rated RI-06 S1; E1 NEW-1 rated it S0, and §7.1 lists it among the S0 hotfixes.
4. **S0 on exposure** (C4). No Round-10 route is public today.

**Coverage check.** Every one of the 87 C-stream rows maps to at least one RI:
- C2: NEW-1…34;
- C3: NEW-1…21;
- C4: NEW-1…32.

The inverse map is the "absorbs" column above.

**Linked findings from other rows that land in these themes but are not C-stream issues** (S1 should dispose of them
with the theme):
- TH-02: J4 NEW-1 (S1: six sources whose own terms forbid redistribution are in the public downloads); E1 NEW-12
  (latent: the web gate allows US public-employee names); F1 NEW-3 (the API names a withheld organisation).
- TH-01: E1 NEW-7 (an "editorial board exists" and the API `/terms` refers to one); E1 NEW-3 (the GL-GATE-02 label
  appears in no artifact); F2b NEW-5 (the contributor-safety policy claims a monitored contact path).
- TH-04: I1 NEW-9 (every camera record is typed `traffic_camera`, including Flock/DeFlock ALPR).
- TH-11: I1 NEW-7 (vendors are not modelled); I1 NEW-4 (agenda, procurement and CCOPS claims never reach a jurisdiction
  page).
- TH-07: J1 NEW-12 (no low-egress path for linked downloads).
- TH-03: J4 NEW-5 (capture bytes are mostly digest-only).
- TH-12: F2a NEW-1 (lifecycle is unwired).

---

## 3. Themes (ranked)

Each theme gives:
- problem → evidence → personas and tasks (C2/C4 verdicts);
- spec ids **violated** vs **new needs**;
- draft requirements, with acceptance tests;
- size → dependencies.

### TH-02 — Rights, attribution and Part VIII safety at publish time · **S0** · RI-01, RI-03, RI-42

**Problem.** The publish path checks structure, not content.
- Public identifiers carry personal account handles (RI-01).
- Third-party data is credited to SIG or to the wrong upstream, and required attribution is empty on 61,603 rows
  (RI-03).
- No dossier page, JSON, print or research dossier states a licence, and the site has no licence statement (RI-42).

These are harms to data subjects and licensors, not polish.

**Personas.**
- P9-T1 partial (the OSM credit is right; every other compartment is "© SIG contributors").
- P7-T2 partial (the JSON has no licence).
- P1-T3 partial (the print has no licence).
- P10-T3 succeeded, but its source keys expose handles.

**Violated.** SIG-PUB-002/003, SIG-LIC-004a/006/008/011, SIG-EXPORT-005/006, SIG-GEO-013, SIG-CONTRIB-020, SIG-API-004.
All read `MET`.

**New needs.**
- A neutral source-identifier policy, with a re-key and redirect plan.
- A publish-time content screen over identifiers and labels, not only over free text.

**Draft requirements.**
- **DR-C6-01 (MUST)** No public identifier, label, file name, slug, tile property or JSON field contains a personal
  name, account handle or email-derived token. Registry ids derived from ArcGIS item owners are re-keyed to neutral ids.
  Old slugs return 301/410 **without echoing the old token**. Adopts DR-C3-13.
  - *Acceptance:* a publish-time screen over every public artifact and the built HTML, matched against registry owner
    fields and a reviewed deny list, finds 0 hits. Each of the 58 ArcGIS-owner-derived `camreg_*` ids (C3's list) is
    reviewed, and every personal-looking one (31 by C3's inspection) is re-keyed.
- **DR-C6-02 (MUST)** Every exported row, tile source and API licence obligation names its upstream rights holder and
  terms URL from the registry, keyed per source rather than per SPDX id. Adopts DR-C3-09 and the PKG-08 AC.
  - *Acceptance:* 0 rows with `attribution_required=1` and an empty attribution. 0 rows whose attribution differs from
    their registry source. The map attribution names each compartment's licensors. Every `datapackage.json` licence URL
    returns 200.
- **DR-C6-03 (MUST)** Every place data appears shows its licence and attribution:
  - the dossier footer;
  - the dossier JSON (`license`, `attribution`, `release_id`);
  - every printed page;
  - research and released dossiers;
  - a site licence statement (code, data, docs) in every page footer.
  - *Acceptance:* a lint over every page class and the JSON finds the fields. PDF text on every page contains the
    licence line.
- **DR-C6-04 (MUST)** A publish-time rights gate refuses any public artifact that holds rows from a source whose
  recorded terms forbid redistribution (J4 NEW-1; SIG-LIC-003/004).
  - *Acceptance:* a planted forbidden-terms row aborts the publish. The six J4 sources are withheld or re-decided under
    HG-03.

**Size:** L (PKG-08 is L; the re-key is M; licence display is S).

**Depends on:**
- G2 ACT-06 (republish #1) and ACT-07 (the attribution defect: a hosted write plus republish #2, two operator gos);
- E2 H-2 and E2-12;
- F5 PKG-08;
- J4 (the redistribution matrix);
- HG-03 decisions for the J4 NEW-1 sources;
- an operator decision on the re-key redirect policy.

### TH-01 — Honesty of public claims and fixtures shown as real · **S0** · RI-05, RI-06, RI-18, RI-36, RI-38

**Problem.** Pages assert things that are not true in production:
- fixture facts about real, named agencies and a vendor ("Oklahoma City PD operates devices from Flock Safety …
  confirmed (4 of 4)"), plus six demo task pages;
- a fixture two-reviewer "Releasable" review;
- a "human-verified" holdout that is LLM- or agent-labelled;
- a provisional figure shown without its flag;
- copy that promises metric kinds the release lacks.

**Root cause.** Templates render fixture modules and hand-written status words in production builds. Nothing checks
that a status word is bound to a recorded state. E2 NEW-1 shows the hostile-reader gate *rejects* a truthful "no review
performed" record.

**Personas.**
- P11-T2 failed (y).
- P5-T2 partial.
- P3-T3 partial.
- P2 trust lost ("human-verified" beside "LLM-bootstrapped").
- The named agencies and the vendor are affected parties.

**Violated.** SIG-UI-042/043/045/048/049, SIG-UI-012, SIG-CHART-013, SIG-METRIC-004/008b/009/010, and SIG-EVAL-006
(the one id in this set already `MISSING`).

**New needs.**
- A fixture-leak build guard.
- Fixtures that use invented, visibly synthetic entities (C4 NEW-27).
- A status-word binding rule.

**Draft requirements.**
- **DR-C6-05 (MUST)** A production build or publish fails when a public page renders data from a `*-fixture` module, or
  contains a denylisted fixture token (`okc-seed`, `demo_`, `Reviewer A`, `example.test`, `https://fixture/`, …).
  Illustrative UI examples use invented entities labelled "Illustrative — not a real agency".
  - *Acceptance:* a planted token aborts the publish. A post-publish crawl of the live site finds 0 tokens. The
    `task/new/` demo slugs are absent from the bucket.
- **DR-C6-06 (MUST)** Status words are derived, never authored. "reviewed", "human-verified", "Releasable",
  "reproducible", "one click", "operating" and "complete" render only when bound to a recorded state:
  - `review_status`;
  - a human-completion marker;
  - a pinned permalink;
  - `[intake].operational`;
  - an evaluated completeness.

  A truthful empty review record must build (E2 NEW-1).
  - *Acceptance:* a unit test enumerates the phrase list and fails on any unbound render. `/editorial-standards/` shows
    "Not yet performed" (E2 H-1).
- **DR-C6-07 (MUST)** Every evaluation figure shows:
  - n (pairs and positives);
  - the labeller type (human, agent, LLM or rule-based);
  - the run, ruleset and window it measures;
  - PROVISIONAL while D-R6.1-EVAL is open.

  Every figure that depends on the provisional resolver (223,901 resolved sites) carries the flag wherever it appears.
  Adopts DR-C3-03.
  - *Acceptance:* the C3 re-trace of `/methodology/` gives 0 `mismatch`. "resolved sites" appears with "(provisional)"
    on every page.
- **DR-C6-08 (MUST)** Copy names only metric kinds the release carries.
  - *Acceptance:* a build check compares the kinds named in `/coverage-metrics/` and `/methodology/` copy with those
    present in `coverage.json` and fails on any difference.

**Size:** M. The wording fixes are S, inside ACT-06. The guard and binding test are M.

**Depends on:**
- E2 H-1, H-4, H-5, H-6;
- G2 ACT-06, with the operator confirming the copy verbatim;
- E3/F4, which decide when "human-verified" can ever be true (Q-8, Q-24).

### TH-13 — Corrections and disputes · **S0** · RI-04, RI-32, RI-56, RI-57, RI-58, RI-60

**Problem.** Every page promises "one click, no account required". The live `/dispute/` has a "Submit" heading and
nothing under it. The chain-tip copy says the receiver is not operating, but it offers no interim channel and calls the
receiver "anonymous", which the operating packet forbids (G2 NEW-5).

Behind it, the Round-10 receiver works end to end locally, but:
- moderation detail returns 500;
- the reporter never sees the outcome;
- the form is hostile on mobile;
- the operating gate ignores owner and staffing;
- the limiter mis-keys;
- demo tokens pass.

**Personas.**
- P10-T1 failed (y).
- P10-T2 succeeded (the Annotate outcome, and zero counts including refusals).
- P11-T3 partial.
- C4 T6 was abandoned in the production posture.
- Data subjects are affected: privacy-harm reports have no route.

**Violated.** SIG-UI-033, SIG-UI-032, SIG-GOV-001/003/004/011, SIG-FIND-006/008. All read `MET`.

**New needs.**
- A handling rule for the interim e-mail channel: what not to send, retention, no plates or third-party personal data.
  This follows from Q-29 and G2 NEW-5.
- A per-record "report this" deep link.

**Draft requirements.**
- **DR-C6-09 (MUST)** `/dispute/` states the operated truth above the fold:
  - whether the receiver is operating;
  - the interim channel (Q-29: the operator's address, "for now") with its handling rule and a single-maintainer
    response time;
  - never "anonymous".

  The every-page footer says "Report an error — how corrections work", and no page says "one click" or "no account"
  while `[intake].operational=false`.
  - *Acceptance:* the built HTML has 0 "one click" strings. P10-T1 completes in ≤2 clicks from a claim, with a stated
    channel and an expectation of review.
- **DR-C6-10 (MUST)**, before `operational` flips:
  - reviewer detail returns 200 over PostgreSQL;
  - the gate requires `owner` and `staffed`;
  - demo tokens are refused whenever a DSN is set;
  - the limiter keys on the edge-normalised client, and refusals are not charged;
  - the proposal shape is validated at proposal time.

  Adopts DR-C4-11 and the PKG-05 AC.
  - *Acceptance:* the PKG-05 Docker test passes, and a composed e2e runs through the web origin.
- **DR-C6-11 (MUST)** The reporter sees the outcome kind, the approved public response and the correction or release
  link. Adopts DR-C4-12.
- **DR-C6-12 (SHOULD)** Every record and dossier page has "Report a problem with this record", pre-filling the
  publication id and record key. The form has no default category, has a viewport meta, and fits 320 px.
  - *Acceptance:* the C4 NEW-19 checks pass, and P10-T1 does not require typing an id.
- **DR-C6-13 (SHOULD)** `/corrections/` gives the log's start date and says that counts are zero because intake is not
  operating.

**Size:**
- S for the honest notice (wave 0);
- M for PKG-05;
- L for operation (ACT-23: owner, SLAs, retention and log exclusions).

**Depends on:**
- Q-29 (answered; G2 NEW-5's risk is recorded as operator-accepted);
- Q-27 (a backup moderator);
- G2 ACT-06, ACT-17 (routing), ACT-20, ACT-23;
- HG-11 (G2 step 7);
- D-P32.16-1.

### TH-07 — Downloads, API and data access · **S0** · RI-02, RI-15, RI-43

**Problem.**
- The public, OpenAPI-documented API answers every jurisdiction with the same placeholder sample: fixture OKC and French
  sources, plus a surname used as a source id. It reports complete coverage with zero evaluated.
- The site never links the complete, checksummed, licence-separated bulk release: 132 artifacts, 1.05 GB.
- robots.txt points to a `/terms` that is 404 on the site.
- Portal files double-count rows, and no resource has a schema.

**Mitigation today (code).** Site dossiers link the correct static JSON, not the API.

**Personas.**
- P3-T1 failed.
- P7-T1 failed.
- P11-T1 failed.
- P7-T2 partial.
- P2 cannot get the rows behind a figure.

**Violated.** SIG-API-002/003/004/008/013, SIG-EXPORT-001/002/006/013, SIG-METRIC-004, SIG-UI-049.

**New needs.**
- A "Data and downloads" page (mechanism by J3).
- Table Schemas.
- schema.org Dataset / DCAT metadata.
- A low-egress distribution **before** linking (SIG-EXPORT-008 exists; the need is sequencing).

**Draft requirements.**
- **DR-C6-14 (MUST)** `/v1/dossier/{scope}` and `/v1/coverage/{scope}` return the release-backed jurisdiction record or
  404, never a sample. Coverage returns `complete:false` when `evaluated=0`. No `sig.example` IRI ships. Adopts
  DR-C3-12, DR-C3-07 (API part) and the PKG-09 AC.
  - *Acceptance:* for each of the 55 slugs, the API subject set is a subset of the release dossier's subjects for that
    slug. A parity test against the static JSON passes. A grep finds 0 placeholder literals.
- **DR-C6-15 (MUST)** A "Data and downloads" page is linked from the global navigation and every dossier. It lists each
  release artifact with:
  - licence and attribution;
  - row count, with the unit stated;
  - bytes, sha256 and format;
  - the release id.

  It links `manifest.json`, `datapackage.json`, `LICENCES.json`, the API docs and terms. `/terms` resolves on the site
  origin (200, or a 301 to the API terms).
  - *Acceptance:* P3-T1 and P7-T1 complete from `/` in ≤3 clicks with 0 dead links. The robots.txt statement is true.
- **DR-C6-16 (MUST)** Bulk files hold one row per entity, or declare their unit. Every `datapackage.json` resource
  carries a Table Schema. Adopts DR-C3-10 and J1 NEW-11.
  - *Acceptance:* the portal `row_count` equals its distinct `entity_id` count or is disclosed as rows. 104 of 104
    resources have a schema.
- **DR-C6-17 (MUST; gates DR-C6-15)** Bulk downloads are linked only through the zero- or low-egress path, with a
  budget alert in place (SIG-EXPORT-008; J1 NEW-12; G1 QA-10).
  - *Acceptance:* the linked URLs resolve to the low-egress origin, and the budget alert exists.

**Size:** L (API code M; the page S–M; schemas M; egress infrastructure M).

**Depends on:**
- the API fix reaches production only with an image roll: ACT-08 code, then ACT-11 deploy after hosted L44–52 and the
  ADR-124 allows, or an operator-approved hotfix (G2 NEW-6);
- F5 PKG-09 and PKG-06a (the jurisdiction key);
- J3 (the page design) and J4;
- G1 ACT-03 / QA-10;
- Q-10 (cost ceiling).

### TH-03 — Provenance and evidence linkage · **S1** · RI-07, RI-08, RI-17

**Problem.** The defining standard (§3.1) is not reachable from the interface:
- No displayed figure links to a claim, a source or an artifact.
- `/evidence/` has 0 claim views.
- The home page asserts that 100% of claims have a "resolvable evidence artifact".
- Sources are snake_case keys (the registry holds 341 homepage URLs that are never exported).
- The "How we know this" module is national on every dossier (a 1-subject PT dossier is "backed by" 255 artifacts and
  218 independent sources), and its labels misdescribe their values.

**Personas.**
- P2-T1 failed.
- P4-T1 failed.
- P11-T1 failed.
- P11-T2 failed (y).
- P2-T2 partial (y).
- P1-T1 partial (y).

This is the theme that most blocks the journalist co-primary audience.

**Violated.** SIG-UI-014/028/030/043/044, SIG-CHART-011 (`MET-DIFFERENTLY`), SIG-METRIC-003/005, SIG-CONTRIB-020,
SIG-EVID-009/010 (J1).

**New needs.**
- Per-source public pages (the J3 source explorer).
- Per-dossier provenance summaries emitted by the exporter.
- Public capture metadata for the 350 real OCFL captures (J1).

**Draft requirements.**
- **DR-C6-18 (MUST)** Every material figure on a dossier reaches, in ≤2 clicks:
  - (a) the claims or rows behind it;
  - (b) for each, a named source page and an evidence record: capture date, digest, locator, and a "view original"
    upstream URL where the licence allows.

  Otherwise the figure states what is unavailable and why.
  - *Acceptance:* an agent crawl from each of the 9 C2 dossiers reaches an evidence record for ≥1 figure in ≤2 clicks.
    `claim_views` in `evidence.json` is non-empty. P4-T1 and P11-T1 complete.
- **DR-C6-19 (MUST)** Sources render by publisher name with a homepage link, licence, first and last capture date, and a
  per-source page. Raw ids appear only as secondary text.
  - *Acceptance:* 0 dossier, freshness, search or print pages show a source id without its name. Every public source
    has a page.
- **DR-C6-20 (MUST)** "How we know this" is page-specific on every dossier, or labelled "Site-wide". Labels match their
  values (for example "source ids", unless lineage-deduplicated). The tier split sums to its stated denominator, or the
  difference is stated. Adopts DR-C3-02 and C3 NEW-13.
  - *Acceptance:* the box equals C3's page-specific recompute (PT 1/1, FL 4/4, TX 4/5, MD 7/8, GB-ENG 11/12,
    unresolved 58/58).

**Size:** XL (the evidence path and source pages are L–XL; per-dossier provenance is M).

**Depends on:**
- J3 (source explorer and per-record provenance);
- J4 (what capture bytes may be shown);
- F5 PKG-10 (number derivations) and PKG-12 (run telemetry);
- G3 (release model);
- a republish.

### TH-04 — Jurisdiction, geometry and count correctness · **S1** · RI-10, RI-11, RI-19, RI-20, RI-44

**Problem.** A point's jurisdiction comes from a claim, with no geometry check, and code schemes are mixed. The results:
- Idaho's dossier includes Indonesia.
- California's includes 838 Florida cameras.
- 562 Nottingham points plot in the Indian Ocean.
- The `unresolved` bucket (71.4% of subjects, including all the OSM/DeFlock ALPR nodes) is presented as one of 55
  "jurisdictions".
- 22 US states, including the Oklahoma pilot, have no dossier.

"Resolved" means different things on different pages, and 23,566 exact duplicate points may inflate counts. The
dossier *values* match the release exactly (C2 §2, C3 §2.2). The problem is what the values are *about*.

**Personas.**
- P1-T1 partial (y): the Oklahoma pilot has no page.
- P3-T2 partial.
- P5-T1 succeeded, but on a GA count that includes (0,0) and sign-flipped points.
- P2 quoting any state figure.

**Violated.** SIG-IDENT-006, SIG-ONTO-010, SIG-UI-048, SIG-UI-008, SIG-METRIC-003/004/009, SIG-RECON-058.

**New needs.**
- A geometry QA gate (C3 NEW-6 `NEW-NEED`).
- Technology typing, so ALPR is distinguishable from traffic cameras (I1 NEW-9, PKG-07).
- Sub-state scope (city or county) for the design centre (C2 P1-T1).

**Draft requirements.**
- **DR-C6-21 (MUST)** One canonical jurisdiction key, `(scheme, code)`, mapped to ISO 3166-2. No dossier mixes schemes.
  Every title, H1, index entry and search result shows the full place name plus the code and scheme. Old slugs redirect.
  Adopts DR-C3-11 and PKG-06a.
  - *Acceptance:* 0 dossiers whose sources span 2 schemes. ID, MN, DE, CO, SA, GA and CA each name one place.
- **DR-C6-22 (MUST)** An export geometry gate. Points at (0,0), with swapped axes or sign errors, or outside the claimed
  jurisdiction's polygon are quarantined into a disclosed state and counted as "N geolocated, of which M located outside
  <J>". Corrections are new claims. Adopts DR-C3-05.
  - *Acceptance:* C3's check, re-run with polygons, finds 0 undisclosed outside points. The Nottingham, `trafficops_ca`
    and TH cases are corrected or disclosed.
- **DR-C6-23 (MUST)** `unresolved` is not counted or listed as a jurisdiction. The index states how many subjects have
  no jurisdiction and why.
  - *Acceptance:* the "N jurisdictions" figures on the home and index exclude it, and an explanatory row is present.
  - **SHOULD:** geolocated subjects in `unresolved` are assigned by point-in-polygon, so OSM ALPR sites reach their state
    dossiers (I1 NEW-4).
- **DR-C6-24 (MUST)** Coverage ratios, dossiers and the map share one definition per predicate of resolved, geolocated
  and conflicted. Numerators are restricted by join, not clamped. Adopts DR-C3-04.
  - *Acceptance:* the latitude ratio equals the dossier and map geolocated total (227,335 of 232,625 in this release).
- **DR-C6-25 (SHOULD)** An export-time uniqueness check flags same-source exact-point duplicates, and same-label pairs
  are resolved before counts are displayed (C3 NEW-19).
- **DR-C6-26 (MUST)** Every public site row carries a technology class (for example ALPR, CCTV, traffic camera, unknown)
  from its source target. Dossiers and the map facet by it. PKG-07 AC.
  - *Acceptance:* Flock and DeFlock layers read ALPR, and nothing is typed `traffic_camera` unless its target says so.

**Size:** XL (PKG-06 L, PKG-07 L plus a ~200k-claim append-only backfill, PKG-11 M).

**Depends on:**
- F5 PKG-06, PKG-07, PKG-11;
- I8, since new sources need the same QA;
- F4 NEW-5 (the resolver input mix changes);
- a republish (G2/G3).

### TH-05 — Findability, IA, navigation and search · **S1** · RI-09, RI-50, RI-51, RI-52, RI-59

**Problem.**
- "Maryland" and "Canberra" return 0 results, and "Austin" returns only a source key. The search index covers 500 of
  232,625 sites.
- Every place is a code, and "CA" never says California.
- Public copy is full of requirement ids, snake_case names, UUIDs and gate names.
- There is no sitemap, and every page has the same meta description.
- Error pages are bare nginx output.
- P1 reached `/dossier/tx/` in one click only by scrolling past 126 tiles.

**Personas.**
- P1-T1 partial (y): the persona concludes SIG has nothing on Austin.
- P6-T1 failed (y).
- P3-T2 partial.
- P5-T1: "GA" is never expanded.
- P12-T1 succeeded.
- P9-T2 partial.

**Violated.** SIG-UI-043/045/046/048/049, SIG-UI-037/050, SIG-CONTRIB-016e, SIG-LIC-007a.

**New needs.**
- A gazetteer-backed place search that maps a city or county to its containing record, with an honest "no city-level
  record" answer.
- A sitemap and Dataset metadata.
- A branded 404.

**Draft requirements.**
- **DR-C6-27 (MUST)** Search resolves place names. Every jurisdiction name and common alias returns its dossier first.
  A city or county with no record returns: "SIG has no <city>-level record; the nearest published record is <state> (N
  observation records from <named sources>)", with a link. The search state is kept in the URL.
  - *Acceptance:* a test set of the 55 jurisdiction names plus 20 US city names, including Austin and Oklahoma City,
    resolves 100% to a dossier or to the honest nearest-record answer. "Canberra" finds AU-ACT.
- **DR-C6-28 (MUST)** Public prose contains no requirement ids, gate names, snake_case field names, UUIDs or raw enums
  outside a "technical details" disclosure. Design-centre pages read at about US grade 10 or below.
  - *Acceptance:* a lint over the built HTML body text finds 0 `SIG-[A-Z]+-[0-9]+`, `GATE-`, `HG-` or snake_case tokens
    outside `<code>` or `<details>`. A readability spot check is recorded.
- **DR-C6-29 (SHOULD)** The site has:
  - `sitemap.xml`;
  - a unique title and meta description per page;
  - schema.org `Dataset` on the data page;
  - branded 404/403/410 pages with a route home;
  - a favicon;
  - HSTS.
  - *Acceptance:* the sitemap lists all dossiers, there are 0 duplicate titles, and a Lighthouse audit of the 404 page
    runs.

**Size:** M.

**Depends on:**
- DR-C6-21 (names);
- J3 (Dataset metadata);
- G1 (headers);
- ACT-06.

### TH-12 — Epistemic legibility: absence, contradictions, freshness · **S1** · RI-12, RI-21, RI-35

**Problem.** The site has an excellent absence vocabulary on `/visual-language/` but does not apply it where it
matters:
- 12–13 dossier fields read a bare "unknown", while the banner says "1 unresearched field".
- "Who else can see the data", "Configuration and retention", "Usage" and "Timeline" render as empty headings. An empty
  sharing section reads as "no one".
- Freshness reports "0 stale" where staleness was never evaluable.
- Contested figures carry no marker.
- The headline "2 open of 2 contradictions" hides 5,290 coordinate conflicts.

**Personas.**
- P1-T2 partial (y).
- P6-T1 ("who runs it" is unanswered).
- P2-T3 partial.
- P11-T2 failed.
- P3.

**Violated.** SIG-TIME-010/012, SIG-UI-003/004/007/008/009/010/011/012/014a, SIG-METRIC-006/007/009.

**New needs.** None. This theme is pure spec conformance.

**Draft requirements.**
- **DR-C6-30 (MUST)** Every field without a value states its absence kind (not researched · searched, none found ·
  evidence conflicts · not applicable) and links to the task that would close it. The interim copy must not assert a
  kind the data does not carry. No section renders as a bare heading. The banner counts every absence-labelled field.
  Adopts DR-C3-06.
  - *Acceptance:* 0 bare "unknown" strings and 0 empty sections across all 55 dossiers. The banner count equals the
    number of labelled fields.
- **DR-C6-31 (MUST)** Freshness shows "not evaluable (n)" rather than 0 stale, shows volatility classes, covers every
  evidence source, and states the data age against the build clock ("data as of 2026-09-27 — N days old"). Adopts
  DR-C3-07.
  - *Acceptance:* `freshness.json` carries `staleness_not_evaluable`, and the home page and freshness page show the data
    age.
- **DR-C6-32 (MUST)** A contested or unresolved value carries its marker wherever the figure appears (page, print,
  JSON). The contradictions headline includes coordinate conflicts, or names exactly what it counts. Adopts DR-C3-08.
  - *Acceptance:* the FL "8,001 of 9,965" figure carries a marker linking to its 1,964 conflicted subjects.

**Size:** L.

**Depends on:**
- F5 PKG-10;
- PKG-12 (wiring lifecycle into the Timeline, F2a NEW-1);
- a republish.

### TH-10 — The printed dossier (council-meeting task) · **S1** · RI-13

**Problem.** Every sampled print is 5 Letter pages, whatever the content (PT has 1 subject).
- Page 1 has no as-of date or permalink.
- Page 2 is an orphan citation block.
- Page 3 is three empty headings.
- No page carries a licence, the site name or a print date.
- Sources are keys.
- Research-dossier prints carry no permalink at all.

C2's inference is that a council member would receive something "neutral but not actionable".

**Personas.** P1-T3 partial: this is the design centre's defining task (SIG-UI-002).

**Violated.** SIG-UI-013 ("the as-of date and permalink on every page"), SIG-UI-011/012/035, SIG-GEO-013, SIG-LIC-004a,
SIG-DOS-002.

**New need.** A one-page council brief as page 1.

**Draft requirements.**
- **DR-C6-33 (MUST)** Every printed page, on every print path (dossier, research dossier, released dossier), carries a
  running footer with:
  - the site name;
  - the full jurisdiction name;
  - the as-of pair and release id;
  - the permalink;
  - the licence line;
  - "page n of m".

  No page holds only chrome or empty headings, and the page count scales with content.
  - *Acceptance:* a PyMuPDF check of the 9 sampled PDFs finds the as-of, permalink and licence text on every page, and 0
    pages with fewer than 200 characters of body text. PT prints on ≤2 pages.
- **DR-C6-34 (SHOULD)** Page 1 is a council brief:
  - the named place;
  - what is recorded (named agencies, technology classes and sources);
  - the next decision date or its typed absence;
  - the top three unknowns, each with "how to find out" (a records request);
  - the sources by name.
  - *Acceptance:* AJ-A3 (§5).

**Size:** M.

**Depends on:** TH-04 (names, technology), TH-03 (source names), TH-12 (absence kinds), TH-08 (release id).

### TH-08 — Citations, permalinks and release identity · **S1** · RI-14, RI-39

**Problem.**
- Every page says "Belief-pinned permalink (reproducible after SIG corrects itself)". Yet `?as_of_world=2020-01-01
  &ruleset=bogus` returns bytes identical to the plain page, and `<link rel=canonical>` is the bare URL.
- No public release archive exists yet (P32.13 is built but undeployed).
- The release id, resolver version and snapshot date appear on no page.
- "Evaluable" is undefined.
- SIG's avoidance position is not stated.

**Personas.**
- P2-T2 partial (y): the persona trusts the permalink.
- P3-T3 partial.
- P5-T2 partial.
- P7-T2 partial.

**Violated.** SIG-UI-034/035, SIG-TIME-008, SIG-FIND-001/002, SIG-EXPORT-003, SIG-GOV-019.

**New needs.** None (the release namespaces are the spec's own design).

**Draft requirements.**
- **DR-C6-35 (MUST)** Until a release-pinned route is live, no page claims reproducibility. Once it is live:
  - "Cite this page" gives a release-namespaced URL;
  - that URL returns identical bytes after a later release, or a 410 tombstone after withdrawal;
  - `rel=canonical` equals it;
  - an as-of that cannot be honoured shows a visible "not available; showing release X" notice.
  - *Acceptance:* the cite URL has the same sha256 before and after a staged republish. The live `as_of` probe shows
    the notice.
- **DR-C6-36 (MUST)**
  - Every page, JSON document and printed page shows the release id beside the as-of pair.
  - `/methodology/` lists every manifest reproducibility input (both as-of dates, the snapshot, `resolver_version` and
    the ruleset).
  - `/methodology/` defines "evaluable" and states SIG's avoidance position.
  - Adopts DR-C3-14.
  - *Acceptance:* the C3 re-trace finds all five manifest inputs on site, agreeing with the manifest.

**Size:** L. The interim honest copy is S (ACT-06); the archive is G2 steps 3–7.

**Depends on:**
- G3 (release model; pending);
- F5 PKG-03 and PKG-04;
- G2 ACT-16, ACT-17, ACT-24;
- HG-11.

### TH-06 — Map and network · **S1** · RI-16, RI-22, RI-45, RI-46, RI-53

**Problem.**
- The map claims 227,335 located records but draws about 20 points on a blank canvas: no coastline, roads or labels,
  and nothing at z12 over a camera its own table lists.
- The layers are inert text, and the legend lists layer types no public artifact backs.
- Popups are UUIDs. The table prints counts the figure suppresses, under "Devices".
- The network shows 131 UUID nodes, one edge type and no filter; 372 unclassified sharing claims are neither shown nor
  counted. Archive records do not type their edges.

**Cause of the UUID labels (code).** Node labels are `source_names.get(id, id)` (`exports/src/exports/spine_export.py:994-995`;
the web falls back to the id, `network.astro:49`). Entity names are never joined, so this is a join gap, not deliberate
withholding. Showing organisation names must still respect ADR-124 `publication_review_required` (F1 NEW-3).

**Personas.**
- P6-T1 failed (y).
- P6-T2 failed (y).
- P12-T2 failed (y).
- P4-T2 partial.
- Journalist and organizer "who shares with whom": not answerable.

**Positive.** The network's "Never implies: That anyone used it" legend is strong epistemic design (C2 §9).

**Violated.** SIG-UI-016…025, SIG-GEO-006, SIG-UI-037/050, SIG-FIND-004, SIG-CHART-013.

**New needs.**
- A basemap (tile source, licence and egress decision).
- Lightweight local lists outside the island.

**Draft requirements.**
- **DR-C6-37 (MUST)** The map draws:
  - every published point at a resolvable zoom;
  - over an attributed basemap with place labels;
  - density bins at national zoom, and the coverage underlay.

  An empty viewport says whether the area is uncovered, or covered with no records.
  - *Acceptance:* at z12 on 10 sampled published coordinates, each frame shows ≥1 point. The Austin and Canberra frames
    show points. AJ-O3 passes.
- **DR-C6-38 (MUST)** Per-jurisdiction and per-area lists exist as their own no-JS pages (≤150 KiB, with CSV download),
  reachable without loading the island (SIG-UI-050).
  - *Acceptance:* P6-T2 and P12-T2 complete with the island blocked.
- **DR-C6-39 (MUST)** Network nodes and edges carry entity names; an organisation held under ADR-124 shows as "organisation
  withheld pending review". The three access-edge types are filterable and distinct, including on archive records
  (adopts DR-C4-06). Unclassified sharing claims are counted.
  - *Acceptance:* 0 UUID-only labels on `/network/`. P4-T2 and "who shares with <agency>" are answered.
- **DR-C6-40 (SHOULD)**
  - Layers are real toggles, or are dropped from the legend when no data backs them.
  - Popups show the name, technology, named source, date and licence.
  - Escape closes a popup.
  - The table never prints a suppressed count, and says "observation records", not "Devices" (C3 NEW-16).
- **DR-C6-41 (SHOULD)** Workspace view links carry the live query, and the no-JS quick filter is populated (C4 NEW-24).

**Size:** L.

**Depends on:**
- a basemap licence and egress decision (J4/G1; Q-10);
- DR-C6-21 and DR-C6-26;
- the ADR-124 allows (G2 ACT-10);
- F5 PKG-10 (map-table suppression);
- TH-14.

### TH-16 — Round-10 surfaces readiness · **S1** (S0 on exposure) · RI-23…RI-31, RI-54, RI-55

**Problem.** C4 rates the surfaces **5 blocked, 7 needs-work, 1 ready** (only the intake's closed 503 state).

The two exposure-S0s are:
- research dossiers built from undisclosed stand-in documents, headed "Reviewed";
- a GATE-G3 candidate that is a 0-record fixture with future dates.

The release engine itself is sound: correct 404/409/410/422/503 states, a withdrawal barrier, idempotent receipts, and a
Part VIII plate refusal. The defects are in wiring, publishing and disclosure. G2 already sequences the fixes (ACT-12,
ACT-15…ACT-19, ACT-24). This theme adds the product bar.

**Personas.** C4 task outcomes:
- T1 abandoned;
- T3 abandoned;
- T4 abandoned (y);
- T5 completed (y);
- T6 abandoned;
- T7 abandoned (y);
- re-aimed P1-T1 and P1-T2 (y).

**Violated.** SIG-FIND-001…006/008, SIG-DOS-001/002, SIG-UI-012/013/024/033/044, SIG-EVAL-006.

**New needs.**
- Per-assertion acquisition labels (DR-C4-03).
- One owner of the publish (DR-C4-07).
- A build-time future-date guard (DR-C4-15).

**Draft requirements.** Adopt **DR-C4-01…DR-C4-15** as the Round-10 exposure bar, and add:
- **DR-C6-42 (MUST)** No Round-10 route is exposed (HG-11) until all of these hold:
  - a real candidate (superseding `p-17b713…`) builds in export mode;
  - the link crawl finds 0 unexpected non-200s;
  - research dossiers show per-assertion acquisition labels and the derived review status;
  - C4's T1–T7 plus the re-aimed P1 tasks, re-run on that candidate, show 0 wrong-conclusion risk.
  - *Acceptance:* a C4-protocol re-run report is attached to the G2 step-7 readout.

**Size:** XL (G2 steps 3–7).

**Depends on:**
- G2 ACT-12 to ACT-24;
- F5 PKG-03, PKG-04, PKG-05;
- B1 date fixes;
- HG-03 (live captures, ACT-22);
- HG-11;
- Q-9, Q-12, Q-27.

### TH-09 — Journalist workflow: sourced headline numbers · **S2 owned** · RI-33, RI-34, RI-37

**Problem.** The journalist's first screen is 126 tautological "N of N subjects with a resolved <snake_case> value"
tiles, each followed by the same caveat and a requirement id. The quotable figure comes last and has no provisional
flag. The same idea is counted three ways on three pages. Several numbers (evaluation metrics, contribution-back, map
bins) come from constants or restricted artifacts, so a skeptic cannot trace them.

This theme's own issues are S2. The journalist's task failures come mostly from TH-03 (no trail), TH-08 (permalinks) and
TH-01 (the "human-verified" claim).

**Personas.**
- P2-T1 abandoned (fail, y).
- P11-T1 failed.
- P3-T2 partial.

**Violated.** SIG-UI-049, SIG-METRIC-003/005, SIG-CHART-011, SIG-EXPORT-003.

**New needs.**
- A "key figures" block in quotable form.
- A glossary of counted units.
- Per-figure machine pointers (DR-C3-01).

**Draft requirements.**
- **DR-C6-43 (MUST)** The home page leads with ≤6 key figures. Each is rendered as one quotable sentence (value, unit,
  denominator, "not a census" where applicable, as-of, release id, provisional flag) with a "where this comes from" link
  to its artifact field and the rows behind it. The 127 coverage ratios move to `/coverage-metrics/`, grouped by
  plain-language topic.
  - *Acceptance:* **the journalist persona completes P2-T1 from `/` in ≤5 minutes with a sourced figure, whose source
    artifact is reached in ≤3 clicks.** The home page is ≤5 screens tall at 390 px (it is 36,036 CSS px today).
- **DR-C6-44 (MUST)** One label per quantity, site-wide, backed by a glossary:
  - "observation records" (232,625);
  - "geolocated observation records" (227,335);
  - "resolved sites (provisional)" (223,901).
  - *Acceptance:* the C2 §7 cross-page table shows one label per value.
- **DR-C6-45 (MUST)** Every displayed number renders from a public release artifact, with a machine-readable pointer. CI
  recomputes the headline, dossier and map figures from the bulk files and fails on any disagreement. Adopts DR-C3-01
  and DR-C3-15.
  - *Acceptance:* a re-run of C3's `number_trace` finds 0 `mismatch` and 0 `untraceable` on the traced pages.

**Size:** L.

**Depends on:** F5 PKG-10; TH-03; TH-08 (release id); G3.

### TH-11 — Organizer workflow: local action · **S2 owned** · RI-40, RI-41 (+ new needs)

**Problem.** The organizer-like personas succeeded at 0 of 6 tasks, and an organizer's four questions go unanswered:
- **Who decides?** `authorization` is null on every sampled dossier.
- **When does it renew?** `termination_mechanics` is null, and the watch is empty (0 dated decision points).
- **What lever exists?** `legal_regime` is null.
- **What can I do?**
  - The research queue has a single filter option, "Unscoped — 243,761".
  - Task pages claim something was "generated" and offer no next step.
  - Records-request generation (SIG-TASK-015/016, recorded `MET`) is not exposed publicly.

There is also no agency list, no technology type, no local list, and no cross-jurisdiction comparison (C2 organizer
lens on P1 and P6).

I1 NEW-4 explains most of the emptiness. Agenda, procurement, CCOPS and Atlas claims are in the spine but **never reach
a jurisdiction page**. So this is as much a data-routing gap as a UI one.

**Personas.**
- P8-T1 failed.
- P8-T2 partial (y).
- P1-T4 partial.
- P7-T3 succeeded (the watch explains its emptiness).
- The organizer lens on P1 and P6.

**Violated.** SIG-UI-007/011/014a/014b/026/027/027a/031, SIG-TASK-002/010/015/016, SIG-CONTRIB-019, most recorded
`MET`.

**New needs.**
- Public records-request templates per gap.
- A per-dossier agency and approving-body list.
- A comparison view (2–5 jurisdictions, with CSV).
- A no-account "how to help" path. The curation surface is loopback-only (ADR-068).

**Draft requirements.**
- **DR-C6-46 (MUST)** The research queue filters by jurisdiction without JS. Each task card shows:
  - the plain-language subject;
  - what is sought and the closing condition;
  - the effort;
  - "how to help" (no account needed).
  - *Acceptance:* P8-T1 completes in ≤3 minutes, and the filter lists every jurisdiction that has tasks.
- **DR-C6-47 (MUST)** Gap and task pages never claim a task was filed on a GET. They state "tracked as task <id>" only
  when the task exists. They offer:
  - the evidence that would close the gap;
  - a ready-to-file records request, with the jurisdiction's records law (SIG-TASK-015/016);
  - where to send findings (TH-13's channel).
  - *Acceptance:* the copy of all 78 task pages is verified. P8-T2 carries no wrong-conclusion risk.
- **DR-C6-48 (SHOULD)**
  - Each dossier names the agencies and operators, technology classes and approving bodies SIG has records for, with
    sources, or states the typed absence.
  - The dossier links its jurisdiction's watch.
  - A comparison view with CSV export exists.
  - Governance claims (agenda, procurement, CCOPS) are routed to jurisdiction pages (I1 NEW-4).
  - *Acceptance:* AJ-O1…AJ-O4 (§5).

**Size:** L (UI), plus XL for the data routing and acquisition.

**Depends on:**
- TH-04 (names, technology);
- TH-12 (absence kinds);
- TH-03 (sources);
- Stream I (I2, I7, I8: renewal, contract and agenda data);
- J3;
- a decision on a public contributor channel (the ADR-068 posture).

### TH-14 — Performance budgets · **S2** · RI-47, RI-48

**Problem.**
- The real-data `/map/` document is 3.43 MB raw: 271 KB transferred against a 153,600 B budget, and 816 KB total
  against a 750,000 B gzip ceiling.
- Mobile performance is 0.86 (0.44 on the fixture build).
- `/network/` and `/search/` have CLS 0.31 and 0.33.
- The CI budgets were measured on fixtures only, and the Round-10 pages sit outside the Lighthouse matrix.
- On mobile, the attribution covers the map, and the list exists only on the heavy page.

**Positive.** Content pages score 1.0 with 0 scripts at 7–24 KB (C2 §6.2). Preserve this.

**Personas.** P12-T2 failed (y); P6.

**Violated.** SIG-UI-036/041/050, SIG-FIND-005, ADR-134.

**Draft requirements.**
- **DR-C6-49 (MUST)** Budgets are enforced in CI on a **real-data, export-mode** build (adopts DR-C4-13):
  - `/map/` document ≤153,600 B;
  - totals within the ADR-134 ceilings;
  - CLS ≤0.1 on every island;
  - mobile performance ≥0.9 on content pages.
  - *Acceptance:* Lighthouse CI over the export-mode build passes, and the live re-measure agrees.
- **DR-C6-50 (SHOULD)** On mobile:
  - the attribution collapses;
  - the map takes ≥50% of viewport height;
  - a link to the list sits above the fold (with DR-C6-38).

**Size:** M.

**Depends on:** F5 PKG-03a (the export-mode CI build) and DR-C6-38.

### TH-15 — Accessibility · **S2** · RI-49

**Problem.**
- Reflow at 320 px fails on `/coverage-metrics/` (446 px), `/visual-language/` (501 px) and the Round-10 pages (807 px
  unbroken ids).
- `label-content-name-mismatch` fails on every page.
- Two "How we know this" landmarks appear on every dossier, and the print view has no `main`.
- `/map/` has 5,290 "Unresolved" tab stops.
- Hatched absence backgrounds need a manual contrast check.

**Positive.** 0 serious or critical axe violations. The skip link, 3-px focus ring, labelled and announced search, and
the absence of keyboard traps all hold.

**Personas.** P12; keyboard and screen-reader users.

**Violated.** SIG-FIND-005, SIG-UI-005, WCAG 2.2 AA 1.4.10, 2.5.3, 1.3.1.

**Draft requirement.**
- **DR-C6-51 (MUST)**
  - Every public page reflows at 320 CSS px; only data tables and maps scroll, inside their own containers.
  - Long ids wrap (adopts DR-C4-14).
  - axe, including moderate and best-practice rules, finds 0 violations on the sampled set.
  - Label-in-name passes.
  - Each page, print included, has one `main`.
  - The `/map/` unresolved list collapses behind one control.
  - *Acceptance:* axe plus a headless 320-px check run in CI on the sampled set, and a manual hatch-contrast check is
    recorded.

**Size:** S–M.

**Depends on:** none. It can ship with ACT-06.

---

## 4. Spec-id pressure: violated-but-`MET` vs new needs

**Violated-but-`MET`** (code: `COVERAGE_MATRIX.csv` verdict column at HEAD `07ef0142`, read between 18:14:56Z and
18:26:05Z).
- C2/C3/C4 cite 89 distinct spec ids. 86 read `MET`, 1 `MET-DIFFERENTLY` (SIG-CHART-011), 1 `MISSING` (SIG-EVAL-006)
  and 1 `AT-RISK-INTEGRATION` (SIG-UI-010).
- The most-cited `MET` ids are:
  - SIG-UI-049 (12 findings);
  - SIG-UI-044 (10);
  - SIG-FIND-001 and SIG-FIND-006 (9 each);
  - SIG-UI-048 (9);
  - SIG-UI-050, SIG-UI-012, SIG-METRIC-003, SIG-FIND-003 (6 each).
- A citation is a per-finding judgement, and some ids are cited as context rather than as the id violated. Even so, the
  pattern is unambiguous:
  - the matrix records engineered-and-tested behaviour;
  - the live site shows it is not delivered;
  - the Round-10 surfaces show it is not yet exposable.
- **Route to F2/T4.** Re-verdict these ids with the §8.3 vocabulary: `MET-ENGINEERED` where the code exists and a live
  leg is owed, `PARTIAL` where the live product contradicts the requirement.

**New needs** (not covered by an existing id; S3 drafts spec text, E-stream checks for conflicts):

| need | from | theme |
|---|---|---|
| Fixture-leak build and publish guard; fixtures use invented entities | RI-05, C4 NEW-27 | TH-01 |
| Status-word binding rule | RI-06, RI-25, RI-14 | TH-01 |
| Neutral source-identifier policy, re-key and redirect | RI-01 | TH-02 |
| Publish-time rights and redistribution gate | RI-03, J4 NEW-1 | TH-02 |
| Export geometry QA gate (point-in-polygon, axis, null island) | C3 NEW-6 | TH-04 |
| Technology class on every site row | I1 NEW-9, PKG-07 | TH-04 |
| Sub-state (city/county) scope, or an explicit "no city-level record" answer | C2 P1-T1 | TH-04/05 |
| Gazetteer place search | RI-09 | TH-05 |
| Sitemap, per-page meta, Dataset/DCAT metadata | C2 NEW-27, J2 | TH-05/07 |
| "Data and downloads" page; Table Schemas | RI-15, J1 NEW-11 | TH-07 |
| Per-source public pages; per-dossier provenance summaries | RI-08, RI-17 | TH-03 |
| Per-assertion acquisition labels (live capture / transcription / stand-in) | C4 NEW-2, DR-C4-03 | TH-16 |
| One owner of the web bucket publish | C4 NEW-10, DR-C4-07 | TH-16 |
| Build-time future-date guard | C4 NEW-32, DR-C4-15 | TH-16 |
| Council brief (print page 1) | C2 §8 | TH-10 |
| Quotable key-figures block and unit glossary | RI-33, RI-34 | TH-09 |
| Number-truth CI (recompute displayed figures from bulk) | DR-C3-15 | TH-09 |
| Public records-request templates; comparison view; no-account help path | C2 organizer lens | TH-11 |
| Interim e-mail channel handling rule | G2 NEW-5 | TH-13 |
| Basemap; no-JS local lists outside the island | RI-16, RI-47 | TH-06 |

---

## 5. Persona-centric view: the first 10 minutes (Round-11 capstone acceptance journeys)

**Status.** These journeys are *agent-drafted*.
- The operator's own answer to **Q-D1-03** ("what should a first-time visitor be able to do or find out within 10
  minutes?") is **pending**. D2 reconciles these drafts with it.
- D3 decides how "co-primary" (U-002) reweights them against the design centre.
- Each journey starts at `/` on a cold visit (no prior knowledge of codes), on desktop and at 390 px.
- **Pass** means: completed within the time and click budget, with wrong-conclusion risk `n`, and with every figure the
  persona leaves with carrying a named source, an as-of date and a release id.

**How to measure.**
- **Agent walkthroughs** (the C2 protocol, fresh context, live site) gate the capstone.
- **They are not user research** (P4). If the operator authorizes human work (Q-8, E3, D-R10-USERS-1), run ≥1 moderated
  session per audience on the live site. E3 NEW-5 notes that the P32.24 protocol is restricted to staged synthetic
  releases, so the capstone needs a **live-site protocol**; that is a Round-11 item.
- Times are agent-estimated for a first-time human (an inference) until a human session measures them.

### 5.1 Design centre: local advocate, council meeting in 6 days (P1, SIG-UI-002)

| id | within | the site must let them… | pass criteria | C2 today | gated by |
|---|---|---|---|---|---|
| AJ-A1 | 1 min, ≤3 clicks | find the record for their place by typing its name | "Austin" or "Oklahoma City" → the containing record, with an explicit "no city-level record" line; the page is titled with the place **name** | partial (y) | DR-C6-21, 27; DR-C6-23 (the OK dossier) |
| AJ-A2 | +3 min | say what is deployed, who operates it, who approved it, and when it next comes up for decision | each of: technology classes and counts; operators named with sources; `authorization`; `next_decision_date` — **or** each shown as a typed absence with "what would close this"; no empty section | partial (y) | DR-C6-26, 30, 48; TH-11 data routing |
| AJ-A3 | +2 min | print something a council member can hold | a PDF with a council brief on page 1; the as-of, release id, permalink and licence on every page; named sources; no empty page; ≤2 pages for thin states | partial | DR-C6-33, 34, 03 |
| AJ-A4 | +3 min | know what to bring and what to ask for | a place-scoped document list with permalinks (SIG-UI-027a) **or** a plain "none available for this scope", plus one ready-to-file records request for the top unknown | partial | DR-C6-47; SIG-UI-027a data; TH-11 |

**Total:** ≤10 minutes. **Also required:** P5 (staffer) can forward the same page as neutral (no internal ids, and the
avoidance position is stated: DR-C6-28, DR-C6-36).

### 5.2 Investigative journalist, on deadline (P2, co-primary per U-002)

| id | within | the site must let them… | pass criteria | C2 today | gated by |
|---|---|---|---|---|---|
| AJ-J1 | 5 min, ≤3 clicks to the source | quote a national headline figure they can defend | one quotable sentence with unit, denominator, "not a census", as-of, release id and provisional flag; its artifact field and rows reached in ≤3 clicks; one label per quantity site-wide | **fail** (y) | DR-C6-43, 44, 45, 07 |
| AJ-J2 | +3 min | verify a state figure (FL "8,001 of 9,965") and cite it so the citation won't move | "evaluable" defined; the 4 sources named and linked; the 1,964 gap explained on the page; a release-pinned permalink that returns identical bytes after a republish | partial (y) | DR-C6-18, 19, 35, 36 |
| AJ-J3 | +2 min | know whether it is disputed | a contested marker on the figure; the competing claims or conflicted subjects reachable in 1 click; the contradiction headline counts what it says | partial | DR-C6-32 |

**Also required:** J-1 (SIG-CHART-008), "city → agency → deployment → contract → sharing", becomes the journalist's
capstone stretch journey. It needs TH-11's data routing and live contract data, so the capstone records it as *owed*
unless that data lands.

### 5.3 Organizers (U-002: coalition and neighbourhood organizers, contributors)

| id | within | the site must let them… | pass criteria | C2 today | gated by |
|---|---|---|---|---|---|
| AJ-O1 | 3 min | list who runs surveillance in their jurisdiction, and what kind | named agencies or operators, with technology class (ALPR vs CCTV vs traffic camera) and counts, sourced, or typed absence | **fail** (P6-T1, y) | DR-C6-21, 26, 39, 48 |
| AJ-O2 | 2 min | know who decides and when, and get reminded | the approving body and `next_decision_date`, or typed absence; a per-jurisdiction iCal/RSS subscription, or a plain "none tracked yet" (today's honest watch copy is a pass pattern) | partial | DR-C6-30, 48; SIG-UI-027 data |
| AJ-O3 | 2 min | get a local list for a flyer or spreadsheet without the map | a no-JS per-area list with CSV, licence and attribution, under 150 KiB | **fail** (P6-T2, P12-T2) | DR-C6-38, 02, 03 |
| AJ-O4 | 3 min | pick one gap and do something about it | a jurisdiction-filtered task with a closing condition, a ready-to-file records request, and where to send the result; no false "task filed" | **fail** / partial (y) | DR-C6-46, 47; TH-13 channel |

**Stretch (SHOULD):** compare 2–5 jurisdictions side by side, with CSV (DR-C6-48).

---

## 6. Quick wins vs structural work

**Quick wins.** Each is S (≤1 agent-day). They are copy or small code, all shippable in **one** republish (G2 ACT-06, the
wave-0 "production safety and honesty" tickets the operator approved in principle, §7.1). Every public sentence needs
the operator's verbatim confirmation (META_PLAN §2).

| # | change | closes / reduces |
|---|---|---|
| QW-1 | `/visual-language/` examples use invented, labelled entities; the demo `task/new/` pages are removed from the bucket and the publish allow-list | RI-05 |
| QW-2 | `/editorial-standards/` shows "Not yet performed", and the build gate accepts a truthful empty record (E2 H-1) | RI-06 |
| QW-3 | `/dispute/` and every-page footer: the operated truth, the interim channel with its handling rule, no "one click", no "anonymous" (E2 H-3; Q-29; G2 NEW-5) | RI-04 (to S2); RI-60 |
| QW-4 | Methodology: accurate labeller and n, the κ row fixed, PROVISIONAL on "resolved sites" everywhere, promises of absent metric kinds removed (E2 H-4) | RI-18, RI-36, RI-38 |
| QW-5 | Cite block: drop "reproducible" until pinned; show the release id, resolver and snapshot; define "evaluable"; state the avoidance position | RI-14 (interim), RI-39 |
| QW-6 | "How we know this" on dossiers labelled "Site-wide", and its labels corrected, pending per-dossier provenance | RI-17 (to S2) |
| QW-7 | Dossier: count every unknown in the banner; hide empty sections or label them "No record in SIG" without asserting a kind the data lacks | RI-12 (partial) |
| QW-8 | Jurisdiction display names (a lookup table) on titles, H1s, the index and the search index | RI-09 (partial), RI-10 (labels only) |
| QW-9 | Home: key figures first; the 126 tiles moved to `/coverage-metrics/`; one label per quantity | RI-33, RI-34 |
| QW-10 | Task pages: no "has been generated"; a "how to help" paragraph | RI-41 |
| QW-11 | A branded 404/403 page, favicon, sitemap, unique titles and meta descriptions; `/terms` redirects to the API terms | RI-51, RI-52 (partial), RI-15 (partial) |
| QW-12 | Map: the table says "observation records"; legend entries without data dropped; no suppressed counts printed | RI-45 (partial), RI-46 |
| QW-13 | Accessibility: label-in-name, a unique landmark name, wrapped ids, print `main` | RI-49 (partial) |
| QW-14 | Contribution-back: the link fixed and CC0 stated; the corrections log start date | RI-59, RI-60 |
| QW-15 | Remove "human-verified", "editorial board" and similar wording from the API `/terms` and governance docs (E2 H-5). This needs an API redeploy | TH-01 linked |

**Not quick, though it looks it:** linking the bulk downloads (RI-15). It is one link, but it must wait for the
low-egress path and a budget alert (DR-C6-17, J1 NEW-12, Q-10).

**Structural work** (multi-ticket; mapped to existing packages):

| work | themes | size | vehicle |
|---|---|---|---|
| Rights attribution integrity plus the source-id re-key | TH-02 | L | PKG-08; ACT-07; E2-12 |
| API truth and placeholder purge (code now, deploy with the image roll) | TH-07 | L | PKG-09; ACT-08 → ACT-11 |
| Jurisdiction identity, geometry QA, technology typing | TH-04 | XL | PKG-06, PKG-07, PKG-11; I8 |
| Evidence trail: claim views, public capture metadata, source pages | TH-03 | XL | J3; J4; PKG-12 |
| Per-scope provenance, number derivations, freshness and absence kinds | TH-03, TH-09, TH-12 | L | PKG-10 (co-owned with C6/C3) |
| Release-pinned citations and a public archive | TH-08, TH-16 | XL | G3; PKG-03, PKG-04; ACT-16, ACT-17, ACT-24 |
| Map basemap and local lists; network naming | TH-06 | L | new tickets; ADR-124 allows (ACT-10) |
| Organizer tools plus governance-data routing | TH-11 | L + XL | new tickets; Stream I (I2, I7, I8) |
| Intake operation | TH-13 | L | PKG-05; ACT-20, ACT-23 |
| Real-data budgets in CI | TH-14 | M | PKG-03a |
| Live-site acceptance protocol (agent, plus human if authorized) | §5 | M | E3; F4; Q-8 |

---

## 7. What must precede public promotion of the site

The site has been public since 2026-09-16 (E1 NEW-11). "Promotion" here means directing journalists, organizers or
press to it: outreach, social posts, a launch. The following gate is agent-drafted for D2/D3/S2:

- **PG-1: every S0 closed and verified live** (live-read evidence) — RI-01…RI-06. For RI-02 this needs the API image roll
  or an operator-approved hotfix (G2 NEW-6). While the API is wrong, it must not be linked or promoted.
- **PG-2: no unbound status claim anywhere** (DR-C6-06). That covers "reproducible", "one click", "human-verified",
  "Reviewed", "Releasable" and "complete".
- **PG-3: no dossier counts another place's cameras** (DR-C6-21, 22, 23): 0 mixed-scheme dossiers and 0 undisclosed
  outside points.
- **PG-4: the §5 journeys AJ-A1–A3, AJ-J1–J3, AJ-O1 and AJ-O4 pass** in a fresh-context agent walkthrough on the live
  site, with 0 wrong-conclusion risk. **Plus**, if the operator authorizes human work (Q-8), ≥1 moderated session per
  audience. An agent pass alone is recorded as `agent-verified`, never "user-tested".
- **PG-5: C3 number-trace re-run** on the home, methodology, coverage and all dossiers: 0 `mismatch` and 0
  `untraceable`.
- **PG-6: downloads linked only behind the low-egress path** with a budget alert (DR-C6-17), because promotion multiplies
  egress.
- **PG-7: Round-10 surfaces stay dark** until G2 step 7 (HG-11, DR-C6-42). Promotion must not point at `/releases/`,
  `/research-dossier/` or `/intake/`.
- **PG-8: G1's production-safety quick actions are done** (restore drill, alerts, deletion protection). Promotion raises
  the cost of an outage or data loss (G1 QA-1…QA-10; the operator approved them in principle, §7.1).

**Minimum honest alternative.** If the operator wants to promote before PG-3…PG-5, the quick wins (§6) plus PG-1, PG-2
and PG-8 are the floor. The promotion copy must then say that the site is an early, provisional record with known
jurisdiction and geometry defects.

---

## 8. What works — preserve it (C2 §9, C3 §2.2, C4 §0)

- Content pages are truly zero-JS: Lighthouse 1.0/1.0/0.96/1.0 at 7–24 KB, and identical with JS off.
- The register is neutral throughout. The census disclaimers and "absence is not evidence of absence" are applied
  consistently. The decision-date framing on `/watch/` is excellent.
- Empty states are honest: `/watch/`, `/corrections/` (zero counts, including `refused: 0`), `/evidence/`, and the
  zero-result search.
- The network's access-edge legend ("Never implies: That anyone used it").
- Every sampled dossier value matches the release. All 127 coverage metrics are byte-identical across the JSON, the CSV,
  the home page and `/coverage-metrics/`. All 55 jurisdiction figures reconcile with a recompute from the bulk
  parquets. Freshness, network and map tables equal their files.
- Keyboard basics: a skip link, a 3-px focus ring, a labelled search announced through `role=status`, and no traps.
- Round-10 engine behaviour:
  - release search states are correct;
  - the withdrawal barrier is honoured in search;
  - receipts are idempotent;
  - apply is exactly-once;
  - moderation fails closed;
  - the Part VIII screen refuses a plate string before storage;
  - the intake CSP is `default-src 'none'`.

---

## 9. Routing and open questions (for S1, D2, D3)

- **For S1:**
  - fold the 60 RIs and their linked rows into the universe, with exactly one disposition each;
  - merge C5's differentiation findings, which may re-rank TH-09 and TH-11;
  - reconcile RI-to-F-id mapping once the orchestrator assigns canonical ids to the C2/C3/C4 rows.
- **For D2:**
  - the operator marks RI-01…RI-58 (S0–S2) agree, disagree or priority;
  - the operator's Q-D1-03 answer replaces or amends the §5 journeys;
  - Q-D1-24 (review focus) may add journeys.
- **For D3:**
  - whether "co-primary" puts the journalist journeys (AJ-J*) and organizer journeys (AJ-O*) in the capstone on equal
    footing with the design centre;
  - whether sub-state scope (city or county) is in Round 11, or answered honestly as "not yet";
  - national breadth vs local depth for TH-11's data routing.
- **Operator questions this synthesis leans on:**
  - Q-8 (human work);
  - Q-9 (Round-10 features);
  - Q-10 (cost ceiling, egress, basemap);
  - Q-22 (raw bytes and run logs);
  - Q-27 (backup moderator);
  - Q-29 (answered: the personal address; G2 NEW-5 risk);
  - a new decision: the source-id re-key and redirect policy (DR-C6-01).
- **For J3** (running next): DR-C6-15, 16, 18, 19, 31, 36 and 45 are the product-level acceptance criteria that J3's
  mechanism design should meet.

---

## 10. Provenance of this synthesis

| time (`date -u`) | action |
|---|---|
| 2026-09-30T18:14:56Z | Start (`date -u`) |
| between 18:14:56Z and 18:26:05Z | Read, in order:<br>• META_PLAN §3, the C and D rows, §7/§7.1, §8.2; OPERATOR_FEEDBACK; PROTOCOL §3, §4, §6.6, §9–§11<br>• JOURNEYS.md, DATA_TRUTH.md and R10_PREVIEW.md in full; C2/C3/C4 CSVs in full<br>• FINDINGS.md S0/S1 and all F-id titles; the titles of every other incoming CSV and the full rows linked above<br>• G2-activation §0 and the ACT table; E2 §0.1 (H-1…H-9); F5 §0 and PKG-03…12; J1 §0<br>• spec SIG-UI/CHART text (targeted `sed -n`); COVERAGE_MATRIX verdicts (read-only Python tally)<br>• `spine_export.py:994-995` and `network.astro:49`<br>No intermediate timestamps were taken; none are inferred here (P2) |
| 2026-09-30T18:26:05Z | Writing started (`date -u`; HEAD `07ef0142`). C5's output had appeared untracked and was not read |

Files written by this row: `review/REVIEW_SYNTHESIS.md` and `data/review_themes.csv` only. Nothing was committed, and no
production system was contacted.
