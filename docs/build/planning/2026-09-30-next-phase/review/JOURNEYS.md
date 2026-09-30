# C2 — Persona journeys on production (headless Chrome)

> **Agent walkthrough, not user research** (P4/P5). Nothing here counts toward `D-R10-USERS-1` or any
> human-evaluation obligation, and `D-R10-USERS-1` stays OPEN. The personas are scripted goals that an agent
> carried out. Where this file estimates how long a person would take, it says so, and that estimate is an
> inference.

Row **C2** of `META_PLAN.md` (Stage P, read-only). Protocol: [`PROTOCOL.md`](PROTOCOL.md) (C1). Findings:
[`../findings/incoming/C2.csv`](../findings/incoming/C2.csv) (34 rows, `NEW-1`…`NEW-34`). Page index:
[`C2_PAGE_INDEX.csv`](C2_PAGE_INDEX.csv) (123 rows). Evidence: `docs/build/logs/next-phase/C2/`, which is gitignored.
It holds 438 files, all hashed in `SHA256SUMS` (sha256 `6acd8e11…d647f`).

Independence: META_PLAN Appendix A, `PD/findings/**` (other rows' files), `DATA_TRUTH.md` and the other rows'
research were not read. The operator's U-002 answer was read, as instructed, and the journeys weight investigative
journalists and organizers as co-primary audiences.

---

## 1. Environment and run facts

| item | value |
|---|---|
| Run window (`date -u`) | 2026-09-30T17:30:20Z → 2026-09-30T18:10:18Z |
| Site | `https://surveillancegraph.org` (release `sig-2026-09-27-ce480ab1`) |
| Drift guard, start (17:30:56Z) | `Last-Modified: Sun, 27 Sep 2026 01:33:43 GMT`, ETag `"6ab87277-14f54"`; `gcloud storage cat …/manifest.json` sha256 `717aeb4499523acf22987428b29f3a46b5ed3aa27a91b1b6e055c7e65aa872d6` |
| Drift guard, end (18:04:47Z) | same `Last-Modified`, same ETag, same manifest sha256, so there was **no drift** |
| Browser | **Google Chrome 154.0.8037.59**, headless, driven by **Playwright 1.62.1** (`channel: "chrome"`) from the main checkout's `web/node_modules`, used read-only. Claude-in-Chrome was not connected, so the orchestrator chose this route. A fresh temporary profile was used for every context; the operator's profile was never touched |
| Viewports | desktop 1440×900 at DPR 1 (measured `innerWidth×innerHeight` = 1440×900). Mobile: Playwright `iPhone 14` emulation at 390×844 (DPR 3, touch, mobile UA); measured 390×844 on every page except `/coverage-metrics/` (446×966) and `/visual-language/` (501×1085), where overflowing content widened the layout viewport. Reflow: 320×800 |
| Accessibility | **axe-core 4.13.0** via `@axe-core/playwright` 4.13.0, tags `wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa, best-practice`, run on 14 pages |
| Lighthouse | **12.6.1** (main checkout `web/node_modules/.bin/lighthouse`) with `CHROME_PATH` = Google Chrome 154, `--headless=new`, desktop preset and default mobile emulation, 16 runs |
| PDF inspection | Chrome `page.pdf({format:"Letter", printBackground:true})` under `emulateMedia({media:"print"})`; pages read with **PyMuPDF 1.28.2** (`uv run --no-project --with pymupdf`, installed only in the user uv cache) |
| Tools written | `docs/build/logs/next-phase/C2/tools/{crawl,search,map,kbd}.mjs`, `pdfcheck.py` (gitignored) |
| Politeness | Requests ran one at a time, at least 3 s apart. **About 140 page loads in total:** 87 headless captures, 9 interaction sessions (1 search, 6 map, 2 keyboard), 24 `curl` route checks (3 of them API GETs), 2 drift-guard HEAD/GETs, 2 JSON/byte-compare GETs and 16 Lighthouse runs. No form was submitted, nothing was POSTed and there was no login |
| Deviations from PROTOCOL §6 | (a) Headless Chrome was used instead of Claude-in-Chrome, so no interactive-only (hover) state was captured beyond the scripted ones. (b) The page log is `C2_PAGE_INDEX.csv`, as the orchestrator instructed, instead of `C2_PAGE_LOG.csv`; it has no `numbers_seen` column, but the key figures are quoted in §3–§5 below. (c) `f_id` is `NEW-n`, as instructed. (d) Lighthouse ran on `/`, `/dossier/tx/`, `/methodology/`, `/research-queue/`, `/map/`, `/network/`, `/search/` and a 404, following the orchestrator's representative set; `/coverage-metrics/` and `/data-freshness/` were not Lighthouse-audited. (e) `ga` was added as a 9th dossier (P5), with its HTML and print captured |
| S0 handling | Two findings meet the S0 bar (`NEW-1`, `NEW-2`). They were written to `C2.csv` as soon as they were observed (about 17:40Z and 17:49Z). This subagent cannot message the orchestrator mid-run and has no production action to take, so the review continued. Both findings are flagged at the top of the return |

---

## 2. Headline

- **Task results for 31 tasks:** 5 success, 15 partial, 11 fail. The worst journeys are the resident's (P6: no
  basemap, and place names are not searchable), the skeptic's and the researcher's download paths (P11-T1,
  P3-T1: nothing is linked), the agency seeking a correction (P10-T1: the dispute page has no channel), and the
  journalist's headline figure (P2-T1).
- **What works:** static content pages are fast (Lighthouse performance 1.0 with 0 scripts), keyboard-clean
  (skip link, 3-px focus ring, no traps) and honest about empty states. The sampled dossier values match the release
  expectations exactly: TX 3994/3996, FL 8001/9965, GA 7049/7049, MD 2752/2753, PT 0/1, unresolved 166142/166210,
  AU-ACT 1299/1328. Every dossier says the count is "not a resolved device census".
- **What fails:** the site shows the *shape* of an evidence-first record (glyph vocabulary, cite blocks, gap
  markers) but, for a real reader, most of the *substance* cannot be reached. There are no names (jurisdictions,
  agencies, sources), no path from a figure to evidence or downloads, no working dispute channel, a map that renders
  almost nothing, and permalinks that are not actually pinned.

---

## 3. Persona narratives

Click counts start at the stated URL. "Effort" is an **inference** of a first-time human visitor's time, not a
measurement.

### P1 — Local advocate, council meeting in 6 days (design centre)
**Goal:** "What is deployed in Austin, what does it cost, when does it renew, and what can I hand the council?"

- **P1-T1 (Austin):** The persona typed "Austin" into `/search/` at 17:33:40Z. The only result was the source key
  `camreg_austin_tx` with `status: ok`: no dossier, no place. That was a wrong turn. Back on `/`, they scrolled
  past 126 metric tiles to the "Jurisdiction reach" list, where "Surveillance infrastructure — TX — TX" is a single
  link, and reached `/dossier/tx/` in **1 click from `/`** (2 with the search detour). They leave with: *"SIG has
  3,994 of 3,996 geolocated camera observations for Texas, which is an observation count and not a census, from four
  sources, one of which is apparently Austin's."* The page never says that no city-level record exists, and nothing
  on it names Austin except the key. **Outcome:** `completed_with_detour`, **partial**,
  wrong_conclusion_risk **y**: the persona is likely to believe SIG has nothing Austin-specific. Findings: NEW-10,
  NEW-15.
- **P1-T2 (cost, renewal, deadline):** 0 clicks. "Cost and expiry" shows *Auto-renews unknown, Notice window
  unknown, Contract expiry unknown, Next decision date unknown*, and the note "The decision date is the figure that
  matters…" is excellent framing. But "unknown" never says whether SIG has not looked or looked and found nothing.
  "Who else can see the data", "Configuration and retention", "Usage" and "Timeline" are bare headings with nothing
  under them. The banner says "1 unresearched field" although 13 fields are unknown. **Outcome:**
  `completed_with_detour`, **partial**, wrong_conclusion_risk **y**: an empty "Who else can see the data" section
  reads as "no one". Findings: NEW-5.
- **P1-T3 (print):** 1 click to "Print / PDF version". The result is 5 Letter pages. Page 1 has no as-of date or
  permalink, page 2 is almost blank, page 3 is three empty headings, and no page has a licence (see §8).
  **Outcome:** `completed`, **partial**, wrong_conclusion_risk n. Findings: NEW-6.
- **P1-T4 (documents to bring):** The dossier has no link to the watch. The persona used the nav (1 click) to reach
  `/watch/`, which states plainly that "No evidence to rank yet … a research gap, not a judgement that no evidence
  exists" and offers a citation file (`/watch/citations.txt`, 87 B, same message). This is honest, but it is national
  and not scoped to TX. **Outcome:** `completed_with_detour`, **partial**, wrong_conclusion_risk n.
- **Trust:** Trust was *gained* by the neutral register, the census disclaimer and the decision-date framing. It was
  *lost* by the bare codes, the empty sections and a printout that is mostly "unknown".
- **Organizer lens (U-002):** An organizer building a coalition packet for several cities gets the same template for
  every state. There is nothing to compare across jurisdictions, no agency list, and no way to bring the
  underlying rows into a spreadsheet.
- **Verdict:** The persona would come back only for the print framing. **The single most useful change** is a
  dossier that names the place, and the agencies and sources in it, with each unknown labelled by its kind of
  absence and linked to the task that would close it.

### P2 — Investigative journalist on deadline (co-primary, U-002)
**Goal:** "Quote a defensible number, understand its denominator, cite it so the citation won't move."

- **P2-T1 (headline figure):** On `/`, the first three tiles are "55 jurisdictions with a published dossier", "178
  sources tracked" and "2423200 of 2423200 published tier-0 claims with a resolvable evidence artifact". After those
  come 123 more "N of N subjects with a resolved <snake_case> value" tiles, each followed by the same caveat and
  `(SIG-METRIC-008)`. The figure a reporter actually wants ("223901 resolved sites (from 232625 observation-level
  records; dedup ratio 0.038)") sits at the bottom, with no PROVISIONAL flag, although the methodology says it must
  carry one. Elsewhere the same idea appears as "232625 mapped sites" (`/search/`) and "227335 located assets"
  (`/map/`). The persona then tried to reach the source artifact: there is no link (0 of 3 clicks possible).
  **Outcome:** `abandoned`, **fail**, wrong_conclusion_risk **y**: "100 % of claims have evidence" and three
  "site" counts. Findings: NEW-7, NEW-8, NEW-17, NEW-18, NEW-19.
- **P2-T2 (Florida 8,001 of 9,965):** The value on `/dossier/fl/` matches. "Evaluable" is defined nowhere. The four
  sources are unlinked keys. The cite block shows the as-of pair and `p27.3/1.0.0` and claims to be
  "reproducible after SIG corrects itself". The persona tested that claim: a request with `as_of_world=2020-01-01
  &ruleset=bogus` returned bytes identical to the plain page (sha256 `f6490953…`), so the parameters are ignored and
  the citation *will* move with the next deploy. The 1,964 gap is explained only on `/map/` ("FL: 1964 assets with
  no published point"), which is 2 clicks away and a text search. **Outcome:** `completed_with_detour`,
  **partial**, wrong_conclusion_risk **y**: the persona trusts the permalink. Findings: NEW-4, NEW-15, NEW-20,
  NEW-28.
- **P2-T3 (disputed?):** The "What we don't know" headline lists "Subjects with conflicting coordinate evidence —
  Unresolved", so the gap is not buried. But the 8,001 figure carries no contested marker, and the gap link opens a
  task page instead of the competing claims. **Outcome:** `completed`, **partial**, wrong_conclusion_risk n.
  Findings: NEW-20.
- **Trust:** Trust was *gained* by "never publishes a total", the census caveats and the honest "Not yet
  human-reviewed". It was *lost* by the tautological 100 % tiles, "218 independent sources" shown in the Texas
  box (the page lists 4), "human-verified holdout" beside "LLM-bootstrapped" on `/methodology/`, and a permalink that
  is not pinned.
- **Verdict:** The persona would not cite SIG on deadline today. **The single most useful change** is a per-figure
  source trail: a named publisher, a link to the evidence and a real release-pinned permalink.

### P3 — Academic researcher
- **P3-T1 (download national dataset):** No page links to `manifest.json`, `datapackage.json` or any compartment
  file. `/map/` and `/search/` say "the full set is in the export bundle and the API" without a link.
  **Outcome:** `abandoned`, **fail**, wrong_conclusion_risk n. Findings: NEW-8.
- **P3-T2 (coverage):** `/dossier/` lists 55 entries and says plainly that an absent jurisdiction "is one SIG has not
  yet published, not one with no surveillance infrastructure", which is good. But the entries are codes with no
  sizes, and the fact that "unresolved" holds 166,210 subjects, far more than any named jurisdiction, is visible
  only by opening that dossier. `/coverage-metrics/` promises "records-derived bounds, per-agency reconciliation
  ratios, and measured survey recall" and shows none of them. **Outcome:** `completed_with_detour`, **partial**,
  wrong_conclusion_risk n. Findings: NEW-30, NEW-17.
- **P3-T3 (methods and reproducibility):** `/methodology/` is linked from every dossier footer. The as-of (2026-09-27)
  and ruleset `p27.3/1.0.0` match the manifest `reproducibility_inputs`. `resolver_version 0.0.0`, `as_of_snapshot`
  and the release id `sig-2026-09-27-ce480ab1` appear on no page. **Outcome:** `completed_with_detour`,
  **partial**. Findings: NEW-28.
- **Verdict:** The persona would go to the API or the bucket directly, if they could find them. **The most useful
  change** is a "Data & downloads" page with per-file licence, checksum and row count, and the release id.

### P4 — Civil-liberties attorney
- **P4-T1 (claim → document):** `/dossier/md/` figures carry no claim, source or evidence link. `/evidence/` (1 nav
  click) says "No claims with a full evidence view yet … a research gap". **Outcome:** `abandoned`, **fail**,
  wrong_conclusion_risk n: the site is honest that nothing is there, but gives no reason. Findings: NEW-7.
- **P4-T2 (inference as observation?):** `/network/` labels every edge "Configured access", with an excellent "Never
  implies: That anyone used it" legend. The dossier says "Observation-level count … not a resolved device census".
  `/map/` has an "Observed vs derived layers" disclosure, but its layer "toggles" are plain text, and popups (UUID
  title, jurisdiction "unresolved", tier 0, `full_precision`) carry no observed/derived or source label.
  **Outcome:** `completed`, **partial**, wrong_conclusion_risk n. Findings: NEW-23.
- **Verdict:** The persona sees the vocabulary for rigour but no chain of custody. **The most useful change** is one
  working path from a dossier figure to an artifact record (capture date, digest, locator).

### P5 — Council staffer
- **P5-T1 (vendor says 5,000 cameras in GA):** `/dossier/ga/` reads "7049 of 7049 evaluable geolocated site
  observations in GA — Observation-level count from named sources — not a resolved device census". The persona can
  say that SIG counts observations from named sources, which is a different quantity from a contracted fleet.
  "GA" is never expanded to "Georgia". **Outcome:** `completed_with_detour`, **success**, wrong_conclusion_risk n.
- **P5-T2 (forward to the chief as neutral?):** The tone is neutral, with no characterizing verbs. But the page is
  mostly "unknown", it uses internal ids (`SIG-RECON-058`), and `/methodology/` never states SIG's position on
  avoidance or evasion. **Outcome:** `completed`, **partial**. Findings: NEW-28.
- **Verdict:** The page is neutral enough to forward, but too thin to change a vote.

### P6 — Resident ("is there surveillance near me, and who runs it?")
- **P6-T1 (downtown Canberra):** `/search/` "Canberra" returned **0 results** (17:33:45Z). `/map/` shows about
  20 orange dots on a blank grey canvas with no coastline, road or label (shot `8e57724f…`). Zooming by double-click
  at Canberra's computed position to z12 showed nothing (shot `477fc8c2…`). The same blank frame appeared at the
  exact coordinate of an Iowa camera that the page's own table lists. Only a visitor who knows that "AU-ACT" means
  the Australian Capital Territory finds `/dossier/au-act/` (1299 of 1328). "Who runs it" is unanswered: "Who else
  can see the data" is empty, with no absence label. **Outcome:** `abandoned` (map) or `completed_with_detour`
  (code-literate), **fail**, wrong_conclusion_risk **y**: the empty map reads as "nothing here". Findings: NEW-9,
  NEW-10, NEW-5.
- **P6-T2 (without the map):** The `/map/` tables show "the first 500 of 227335 located assets", mostly Iowa. AU-ACT
  appears only as H3 cell ids (e.g. `83be72fffffffff … 1294`) and a 29-row "no published point" list. **Outcome:**
  `abandoned`, **fail**, wrong_conclusion_risk **y**. Findings: NEW-9, NEW-32.
- **Organizer lens:** A neighbourhood organizer mapping cameras for a flyer cannot get a local list at all.
- **Verdict:** The persona would not come back. **The most useful change** is a basemap plus a place search that
  resolves to a jurisdiction or area list.

### P7 — Downstream developer
- **P7-T1 (API docs, terms, stable id):** Nothing on the site links to the API. `robots.txt` says terms are "at
  /terms (the API)", but `https://surveillancegraph.org/terms` is **404**. The API host's `/terms` (200) states the
  tiers, prohibitions and a clear remedy, but gives no numeric rate limit. **Outcome:** `abandoned`, **fail**.
  Findings: NEW-8.
- **P7-T2 (`/dossier/au-act.json`):** The "JSON (API form)" link is 1 click. The file carries `as_of_world`,
  `as_of_belief`, `ruleset_version` and `permalink`. It has **no licence, attribution or release id**, and its only
  identifier is `jurisdiction:au-act`. **Outcome:** `completed`, **partial**. Findings: NEW-31.
- **P7-T3 (TX renewal feed):** `/watch/` explains "A per-jurisdiction subscription appears once SIG is tracking a
  dated decision there. None are tracked yet." There are no dead feed links. **Outcome:** `completed`, **success**.

### P8 — SIG contributor (organizer-like)
- **P8-T1 (Maryland task):** `/research-queue/` (1 click) has one filter option, "Unscoped — 243761 task(s)". The
  cards are UUIDs with "Evidence sought `sharing_snapshot_stale`" and "Geographic scope —". **Outcome:**
  `abandoned`, **fail**. Findings: NEW-21.
- **P8-T2 (click an unknown):** On `/dossier/md/`, "? Not researched" (1 click) opens the task page for exactly
  `jurisdiction:md / sharing_partners`, which says "A research task has been generated from this gap. It enters the
  queue…". The page is a static file: nothing was generated, and there is no instruction on how to help.
  **Outcome:** `completed`, **partial**, wrong_conclusion_risk **y**: the persona believes they filed something.
  Findings: NEW-22.
- **Verdict:** The persona would not know what to do next. **The most useful change** is a jurisdiction filter plus a
  concrete "how to contribute this" on each task.

### P9 — OSM / DeFlock contributor
- **P9-T1 (OSM licence and attribution):** The `/map/` control reads "© OpenStreetMap contributors (ODbL)", and the
  static note repeats it, which is good. But every other compartment is credited to "Surveillance data © SIG
  contributors (OGL-3.0 | CC-BY-3.0 | CC-BY-SA-2.0 | CC-BY-SA-4.0 | …)", naming no original licensor. There is no site
  licence statement, and no download or print carries attribution. **Outcome:** `completed`, **partial**. Findings:
  NEW-16.
- **P9-T2 (contribution back):** `/contribution-back/` shows "0 accepted upstream of 0 attributed changesets" and
  defines the count by a public hashtag, which is good. CC0 is not stated, and "Organised Editing activity page"
  links to `/methodology/`, which has no such content. **Outcome:** `completed`, **partial**. Findings: NEW-33.

### P10 — Agency or vendor seeking a correction (hostile reader)
- **P10-T1:** "Dispute or correct this record" is on every page, 1 click from `/dossier/md/`. `/dispute/` lists
  categories by priority, says no identity is needed, and lists the outcomes including refusal. Then comes a heading
  "**Submit**" with no form, no address, no statement that intake is closed, and no interim channel. **Outcome:**
  `abandoned`, **fail**, wrong_conclusion_risk **y**. Findings: NEW-3 (the chain tip already adds a "not yet
  operating" sentence, but it is not deployed).
- **P10-T2:** "Annotate — a response is attached alongside the claim, even when the claim is accurate" is present.
  `/corrections/` shows "Total requests recorded: 0" with zero counts for every category and outcome, including
  `refused: 0`. **Outcome:** `completed`, **success**.
- **P10-T3 (read MD and unresolved as counsel):** The persona found no characterizing sentence. Figures are dated
  through the as-of block. Sentences counsel would still challenge: the unexplained "Subjects with conflicting
  coordinate evidence — Unresolved" (which subjects?), sources given only as keys, and the page titled
  "Surveillance infrastructure — unresolved". **Outcome:** `completed`, **success**. Findings: NEW-15. The
  unresolved page also exposes handle-like source keys: NEW-2 (S0).

### P11 — Skeptic ("prove it")
- **P11-T1:** Home number → export → bulk file is impossible with on-site links. **Outcome:** `abandoned`,
  **fail**. Findings: NEW-7, NEW-8.
- **P11-T2 (compare "How we know this" on `/`, `/dossier/fl/`, `/corrections/`):** `/` and `/dossier/fl/` show the
  **same** site-wide box (255 artifacts, 218 independent sources, 2020-01-28 to 2026-09-26). `/corrections/` shows a
  page-specific box (0 / 0×untiered / 0 / "no dated evidence"). The tier split 2245390 + 2690 + 175114 =
  **2,423,194**, while the claims tile says 2,423,200. "Human review: Not yet human-reviewed" is honest.
  **Outcome:** `completed`, **fail**, wrong_conclusion_risk **y**. Findings: NEW-14.
- **P11-T3:** `/corrections/` is an honest empty log with transparency counts. It does not give the date the log
  started. **Outcome:** `completed`, **partial**. Findings: NEW-34.

### P12 — Mobile-only visitor (390×844)
- **P12-T1:** On `/`, "Surveillance infrastructure — TX" is 1 tap away. The nav wraps into three labelled groups
  that fill about a third of the first screen, and the links are 29 px tall. There is no horizontal scroll on any
  dossier. The address-bar URL is the canonical URL. **Outcome:** `completed`, **success**.
- **P12-T2:** Lighthouse mobile on `/map/` gives performance **0.86**, LCP **2.23 s**, TBT **352 ms**, **816 KB**
  transferred, and a 3.43 MB raw HTML document. The map frame shows 2 points, and the attribution text covers its
  lower third. The list is on the same heavy page and is not local. **Outcome:** `abandoned`, **fail**,
  wrong_conclusion_risk **y**. Findings: NEW-9, NEW-24, NEW-32.

---

## 4. Task results

| task | persona | start | clicks | outcome | verdict | wrong-concl. risk | findings |
|---|---|---|---|---|---|---|---|
| P1-T1 | advocate | `/` | 1 (+search detour) | completed_with_detour | partial | y | NEW-10, NEW-15 |
| P1-T2 | advocate | `/dossier/tx/` | 0 | completed_with_detour | partial | y | NEW-5 |
| P1-T3 | advocate | `/dossier/tx/` | 1 | completed | partial | n | NEW-6 |
| P1-T4 | advocate | `/dossier/tx/` | 1 (nav) | completed_with_detour | partial | n | — |
| P2-T1 | journalist | `/` | — | abandoned | **fail** | y | NEW-7, NEW-8, NEW-17, NEW-18, NEW-19 |
| P2-T2 | journalist | `/dossier/fl/` | 2 | completed_with_detour | partial | y | NEW-4, NEW-15, NEW-20, NEW-28 |
| P2-T3 | journalist | `/dossier/fl/` | 0–1 | completed | partial | n | NEW-20 |
| P3-T1 | researcher | `/` | — | abandoned | **fail** | n | NEW-8 |
| P3-T2 | researcher | `/` | 1–2 | completed_with_detour | partial | n | NEW-30, NEW-17 |
| P3-T3 | researcher | `/` | 1 | completed_with_detour | partial | n | NEW-28 |
| P4-T1 | attorney | `/dossier/md/` | 1 (nav) | abandoned | **fail** | n | NEW-7 |
| P4-T2 | attorney | `/network/`, `/map/`, `/dossier/md/` | 0 | completed | partial | n | NEW-23 |
| P5-T1 | staffer | `/dossier/ga/` | 0 | completed_with_detour | **success** | n | — |
| P5-T2 | staffer | `/dossier/ga/`, `/methodology/` | 1 | completed | partial | n | NEW-28 |
| P6-T1 | resident | `/` | 3+ | abandoned | **fail** | y | NEW-9, NEW-10, NEW-5 |
| P6-T2 | resident | `/map/` | 0 | abandoned | **fail** | y | NEW-9, NEW-32 |
| P7-T1 | developer | `/` | — | abandoned | **fail** | n | NEW-8 |
| P7-T2 | developer | `/dossier/au-act/` | 1 | completed | partial | n | NEW-31 |
| P7-T3 | developer | `/watch/` | 0 | completed | **success** | n | — |
| P8-T1 | contributor | `/` | 1 | abandoned | **fail** | n | NEW-21 |
| P8-T2 | contributor | `/dossier/md/` | 1 | completed | partial | y | NEW-22 |
| P9-T1 | OSM contributor | `/map/` | 0 | completed | partial | n | NEW-16 |
| P9-T2 | OSM contributor | `/` | 1 | completed | partial | n | NEW-33 |
| P10-T1 | agency | `/dossier/md/` | 1 | abandoned | **fail** | y | NEW-3 |
| P10-T2 | agency | `/dispute/` | 1 | completed | **success** | n | — |
| P10-T3 | agency | `/dossier/md/`, `/dossier/unresolved/` | 0 | completed | **success** | n | NEW-15, NEW-2 |
| P11-T1 | skeptic | `/` | — | abandoned | **fail** | n | NEW-7, NEW-8 |
| P11-T2 | skeptic | `/`, `/dossier/fl/`, `/corrections/` | 2 | completed | **fail** | y | NEW-14 |
| P11-T3 | skeptic | `/` | 1 | completed | partial | n | NEW-34 |
| P12-T1 | mobile | `/` (mobile) | 1 | completed | **success** | n | — |
| P12-T2 | mobile | `/map/` (mobile) | 0 | abandoned | **fail** | y | NEW-9, NEW-24, NEW-32 |

**Totals:** 5 success · 15 partial · 11 fail. There are 10 tasks with wrong-conclusion risk. The co-primary
audiences did worst: the journalist had 0 successes in 3 tasks, and the organizer-like personas (resident,
contributor, OSM contributor) had 0 successes in 6.

**P32.24 analogues (PROTOCOL §3.1):** T2 → P6-T1/T2 fail. T5 → `/search/` "zzqx-nonexistent" answered "0
results … Nothing found is not evidence of absence", which is a **pass**. T6 → P10-T1 fail. T7 → P2-T3 partial and
P11-T2 fail.

---

## 5. Heuristic scorecard (H01–H18 × page class)

Page classes: **Home** `/` · **Dossier** (9 sampled) · **Print** (9) · **JSON** (`tx`, `au-act`) · **Lists**
(`/dossier/`, `/coverage-metrics/`, `/data-freshness/`(+status), `/research-queue/`, `/watch/`, `/evidence/`,
`/corrections/`, `/contribution-back/`) · **Reference** (`/methodology/`, `/editorial-standards/`, `/style-guide/`,
`/visual-language/`) · **Islands** (`/map/`, `/network/`, `/search/`) · **Task** (9) · **Dispute** · **Errors**
(404/403).

| H | Home | Dossier | Print | JSON | Lists | Reference | Islands | Task | Dispute | Errors | note / finding |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H01 truth | fail | pass (values) / fail (box) | pass (values) | pass | fail | fail | fail | n/a | n/a | n/a | Dossier values match the release. Failures: tautological tiles, three site counts, a 218-source box on TX, tier sum 6 short, the map shows almost none of 227,335 (NEW-9, 14, 17, 18) |
| H02 epistemic | fail | fail | fail | fail | pass (empty states) | pass (visual-language shows the full vocabulary) | fail (map) / pass (network glyphs) | fail | n/a | n/a | NEW-5, NEW-19, NEW-20, NEW-23 |
| H03 task success | fail | fail | fail | partial | fail | partial | fail | fail | fail | n/a | 5/31 success |
| H04 IA/navigation | fail | pass (footer links methodology/freshness/coverage; dispute link) | n/a | n/a | fail | pass | fail | fail | pass | fail | Nav is identical and grouped on every page. Downloads and API are unlinked (NEW-8); the dossier does not link the watch |
| H05 copy | fail | fail | fail | n/a | fail | fail | fail | fail | fail | n/a | Requirement ids (126 on home), snake_case, UUIDs, bare codes (NEW-10, NEW-17) |
| H06 WCAG 2.2 AA | fail | fail | fail | n/a | fail | fail | fail | fail | pass | n/a | Skip link, focus ring, `lang`, one H1 and no trap all pass. Fails: reflow at 320, label-in-name, duplicate landmarks (NEW-25) |
| H07 perf/JS | pass | pass | pass | n/a | pass | pass | fail | pass | pass | n/a | Content pages: 0 scripts, perf 1.0, 7–24 KB. Islands over budget / CLS (NEW-24) |
| H08 mobile | pass | pass | pass | n/a | fail (coverage 446 px) | fail (visual-language 501 px) | fail (map) | pass | pass | n/a | NEW-25, NEW-32 |
| H09 print | n/a | n/a | fail | n/a | n/a | n/a | n/a | n/a | n/a | n/a | §8, NEW-6 |
| H10 citations | fail | fail | fail | fail | fail | fail | fail | fail | fail | n/a | A cite block is on every page and its as-of and ruleset equal the manifest, but it is not pinned, canonical ≠ permalink and no release id is shown (NEW-4) |
| H11 licensing | fail | fail | fail | fail | fail | fail | fail (misattribution) | n/a | n/a | n/a | NEW-16, NEW-31 |
| H12 Part VIII | pass | fail (unresolved sources) | fail | fail | fail (freshness, search sources) | fail (visual-language named agencies) | pass (6-decimal coordinates on public traffic cameras; no plates seen) | fail (demo agency slugs) | pass | pass (`/curate/` 404) | NEW-2 (S0), NEW-1 (S0) |
| H13 provenance/trust | fail | fail | fail | n/a | fail (freshness) | fail (human-verified) | n/a | n/a | n/a | n/a | "Not yet human-reviewed" is honest everywhere, which passes (NEW-13, 14, 29) |
| H14 empty/error | n/a | fail (silent empty sections) | fail | n/a | pass (watch, corrections, evidence) | n/a | pass (no-JS fallbacks render lists) | fail | fail | fail (bare nginx) | NEW-5, NEW-26, NEW-3 |
| H15 discoverability | fail | fail | fail | n/a | fail | fail | fail | fail | fail | fail | No sitemap, one generic meta description, codes as titles (NEW-10, NEW-27) |
| H16 consistency | fail | pass (identical section order across 9) | pass | pass | fail | pass | fail | pass | pass | n/a | NEW-18 |
| H17 freshness | fail | fail | fail | fail | fail | fail | fail | fail | fail | n/a | As-of equals the manifest and no date is later than `date -u` (both pass), but data age and release id are never shown (NEW-29) |
| H18 fixture leakage | pass | pass | pass | pass | pass | **fail** | pass | **fail** | pass | pass | NEW-1 (S0), NEW-12 |

---

## 6. Automated results

### 6.1 axe-core 4.13.0 (14 pages, desktop)
| rule | impact | nodes | pages |
|---|---|---|---|
| `landmark-unique` | moderate | 4 | `/dossier/tx/`, `/dossier/fl/`, `/dossier/unresolved/`, `/dossier/tx/print/` (two "How we know this" regions) |
| `region` | moderate | 13 | `/dossier/tx/print/` |
| `landmark-one-main` | moderate | 1 | `/dossier/tx/print/` |
| `landmark-no-duplicate-contentinfo` | moderate | 1 | `/dossier/tx/print/` |
| needs review: `color-contrast` | — | 7,295 / 532 / 22 / 4 | `/map/`, `/network/`, `/visual-language/`, dossiers (hatched absence backgrounds; manual check owed) |

There are **0 violations** on `/`, `/coverage-metrics/`, `/dispute/`, `/methodology/`, `/research-queue/`,
`/search/`, `/map/`, `/network/`, `/visual-language/` and the task page. No serious or critical violations were found.

### 6.2 Lighthouse 12.6.1 (Chrome 154 headless)
| URL | preset | perf | a11y | best-pr. | SEO | LCP ms | TBT ms | CLS | transfer B | script B | doc B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `/` | desktop | 1.00 | 1.00 | 0.96 | 1.00 | 326 | 0 | 0 | 10,424 | 0 | 6,418 |
| `/` | mobile | 1.00 | 1.00 | 0.96 | 1.00 | 873 | 0 | 0 | 10,414 | 0 | 6,399 |
| `/dossier/tx/` | desktop | 1.00 | 1.00 | 0.96 | 1.00 | 334 | 0 | 0 | 7,264 | 0 | 3,249 |
| `/dossier/tx/` | mobile | 1.00 | 1.00 | 0.96 | 1.00 | 881 | 0 | 0 | 7,264 | 0 | 3,249 |
| `/methodology/` | desktop | 1.00 | 1.00 | 0.96 | 1.00 | 327 | 0 | 0 | 7,964 | 0 | 3,949 |
| `/methodology/` | mobile | 1.00 | 1.00 | 0.96 | 1.00 | 875 | 0 | 0 | 7,964 | 0 | 3,949 |
| `/research-queue/` | desktop | 1.00 | 1.00 | 0.96 | 1.00 | 376 | 0 | 0 | 24,064 | 0 | 20,049 |
| `/research-queue/` | mobile | 1.00 | 1.00 | 0.96 | 1.00 | 1,188 | 0 | 0 | 24,064 | 0 | 20,049 |
| `/map/` | desktop | 0.97 | 1.00 | 0.96 | 1.00 | 487 | 72 | 0.105 | 817,207 | 328,134 | 271,295 |
| `/map/` | mobile | **0.86** | 1.00 | 0.96 | 1.00 | **2,231** | **352** | 0.099 | 816,352 | 328,152 | 271,304 |
| `/network/` | desktop | **0.85** | 1.00 | 0.96 | 1.00 | 401 | 0 | **0.311** | 88,592 | 67,707 | 16,204 |
| `/network/` | mobile | 0.97 | 1.00 | 0.96 | 1.00 | 1,086 | 44 | 0.115 | 88,592 | 67,707 | 16,213 |
| `/search/` | desktop | **0.84** | 1.00 | 0.96 | 1.00 | 375 | 0 | **0.326** | 84,232 | 66,819 | 12,732 |
| `/search/` | mobile | 0.89 | 1.00 | 0.96 | 1.00 | 1,000 | 0 | 0.230 | 84,214 | 66,801 | 12,741 |
| `/nonexistent-c2-probe/` | both | — | — | — | — | Lighthouse `ERRORED_DOCUMENT_REQUEST` (404) | | | | | |

Best-practices is 0.96 everywhere because of `errors-in-console` (the `/favicon.ico` 404). `label-content-name-mismatch`
fails on every page. Against the H07 budgets: `/map/` exceeds the document budget (271 KB transferred, 3.43 MB raw,
budget 153,600) and the total gzip ceiling (816–817 KB against 750,000). `/network/` and `/search/` are within their
byte ceilings but show poor CLS. Reports: `docs/build/logs/next-phase/C2/lh/*.json`, 16 files, all hashed in
`SHA256SUMS`.

### 6.3 Keyboard and accessibility-tree proxy (not assistive-technology testing)
- `/`: the first Tab reaches "Skip to main content" and Enter moves to `#main`; the next Tab lands on the first
  in-content link. Every link has a 3-px `rgb(11,94,218)` outline.
- `/dossier/tx/`, `/dispute/`, `/search/` and `/network/`: the order is logical and the focus ring is visible. The
  search input is labelled and its result count is announced (`role=status`, `aria-live=polite`, e.g. "0 results for
  “Maryland”.").
- `/map/`: Tab goes skip link → 16 nav links → canvas (named "Interactive map of 227335 located surveillance
  records…") → zoom in (focus-visible box-shadow `rgb(0,150,255) 0 0 2px 2px`) → zoom out → compass → the details
  summary → **5,290** "Unresolved" gap links. There is no layer control to reach. Escape leaves focus on the canvas
  and Tab continues, so there is no trap. Escape does **not** close an open popup.
- `/dossier/tx/print/`: no skip link or nav, which is acceptable for print, but there is no `main` landmark.

---

## 7. Cross-page consistency

| item | `/` | `/search/` | `/map/` | `/coverage-metrics/` | dossiers | verdict |
|---|---|---|---|---|---|---|
| site count | 223,901 resolved / 232,625 observation-level | 232,625 "mapped sites" | 227,335 "located assets" | 223,901 / 232,625 | per-jurisdiction observations | inconsistent labels (NEW-18) |
| claims | 2,423,200 of 2,423,200 | — | — | same | — | vs tier sum 2,423,194 (NEW-14) |
| sources | 178 tracked | 178 | — | — | box: 218 "independent sources" | 178 vs 218 unexplained (NEW-14) |
| contradictions | 2 open of 2 | — | — | 2 of 2 | 16 jurisdictions carry an UNRESOLVED coordinate gap | unexplained (NEW-20, routed to C3) |
| as-of | world/belief 2026-09-27, `p27.3/1.0.0` | same | same | same | same | consistent, and equal to the manifest |
| nav / footer | identical grouped nav on all pages; no `<footer>` landmark or licence line anywhere | | | | | consistent, but no licence (NEW-16) |

---

## 8. Print-dossier review ("hand it to a council member")

Nine PDFs were produced with headless `page.pdf` (Letter, backgrounds on, print media emulated): `tx` `147cdf55…`,
`unresolved` `ca873ded…`, `fl` `2c061f8d…`, `md` `5e0a124c…`, `pt` `e06b6dce…`, `gb-eng` `f0152709…`, `au-act`
`c781e62b…`, `ca` `7c15cf1b…`, `ga` `a8675b5c…`. All are in `pdf/` and listed in `SHA256SUMS`. Chrome's own print
dialog would add a URL header and footer; that was not reproduced here.

| check | result |
|---|---|
| Paginated | Yes: **5 pages every time**, whatever the content (PT has 1 subject; unresolved has 166,210) |
| As-of + permalink on every page | **No.** Page 1 has neither. The as-of/permalink block appears after section groups, not as a running footer, and on pages 2–5 only |
| Orphan pages | Page 2 is only the as-of/permalink block (154 chars). Page 3 is three empty headings ("Who else can see the data", "Configuration and retention", "Usage") plus the block |
| Incompleteness banner + "what we don't know" | Present: the banner and the summary on page 1, the full list on page 5 |
| Sources | Snake_case keys only, with no names, links or dates. On the unresolved print these include handle-like keys (NEW-2) |
| Licence / attribution | **None** on any page: no data licence, no "© SIG", no ODbL/OSM line (no map is printed) |
| Navigation chrome | None printed, which is good. The screen-only "Print or save this page…" toolbar is suppressed |
| Tables cut / greyscale | Nothing was cut. The hatch and absence chips are legible in the colour render (60-dpi page renders viewed). Greyscale was not tested separately; the chips carry text labels, so meaning does not depend on colour |
| Tone | Neutral, with no characterizing verbs. But `SIG-RECON-058` appears in the body and the jurisdiction is a bare code |
| Council-member test (inference) | A council member would receive five pages that say "TX", a count with a disclaimer, about 13 "unknown"s and four source keys. Nothing names the city, the agencies, the contracts or where to get the documents. It is neutral but not actionable. **Verdict: partial / fail** (NEW-6, NEW-5) |

---

## 9. What already works (not findings; for C6)

- Static content pages are genuinely zero-JS. They score 1.0/1.0/0.96/1.0 on Lighthouse with 7–24 KB transferred,
  are fast on mobile, and render identically with JS off (`/dossier/tx/` no-JS text is identical).
- The register is neutral throughout, and the census disclaimers and "absence is not evidence of absence" framing
  are consistent on search, the dossier index, watch, evidence and corrections.
- Empty states are honest: `/watch/` (the decision-date framing is excellent), `/corrections/` (zero transparency
  counts including `refused: 0`), `/evidence/`, and the zero-result search.
- The access-edge legend on `/network/` ("Never implies: That anyone used it") is a strong piece of epistemic design.
- `/curate/` returns 404, `http://` redirects to https, a missing trailing slash gets a 301, and PMTiles Range
  requests return 206.
- Keyboard basics are solid: the skip link, a visible 3-px ring, a labelled and announced search, and a map with no
  keyboard trap.
- All sampled dossier values match the release-derived expected answers in PROTOCOL §3.

---

## 10. Top product-level insights (for advocates, journalists and organizers)

1. **Name things.** Every jurisdiction, agency and source is a code, UUID or snake_case key. A dossier headed
   "Texas", with the agencies and named, linked sources in it, would fix P1-T1, P2-T2, P6-T1, the search failures
   and much of the print problem at once (NEW-10, NEW-11, NEW-15).
2. **Give every figure a trail.** Figure → claim → evidence artifact → downloadable row, with a release-pinned
   permalink that actually pins. This is the defining standard. Today there is no link from any number to anything
   (NEW-4, NEW-7, NEW-8).
3. **Make absence specific and actionable.** Replace bare "unknown" and silent empty sections with the kind of
   absence, a count that matches the banner, and a task with a real way to help. Organizers are the people who would
   close these gaps (NEW-5, NEW-21, NEW-22).
4. **Make the print a council-ready brief:** a running footer with as-of and permalink on every page, named
   sources, licence, no orphan or empty pages, and a one-page summary for the thin states (NEW-6).
5. **A map a resident can use:** a basemap, a place search, points that actually render at street zoom, and a
   local list without the 3.4 MB page (NEW-9, NEW-23, NEW-24, NEW-32).
6. **Remove fixtures and personal handles before any publicity push.** Both S0s are cheap to fix and costly if a
   journalist finds them first (NEW-1, NEW-2, NEW-12).
7. **Open the doors for data users and critics:** a Data & API page (manifest, checksums, licences, terms, rate
   limits), and a dispute page that says honestly whether intake is open and what to do meanwhile (NEW-3, NEW-8).

---

## 11. Findings filed (`../findings/incoming/C2.csv`)

| sev | count | ids |
|---|---|---|
| **S0** | 2 | NEW-1 (visual-language fixture claims about real named agencies/vendor), NEW-2 (handle-like source identifiers, redacted) |
| **S1** | 14 | NEW-3 dispute dead end · NEW-4 permalinks not pinned · NEW-5 unknown without kind / empty sections · NEW-6 print · NEW-7 no figure→evidence path · NEW-8 downloads/API/terms unlinked · NEW-9 map renders almost nothing · NEW-10 bare codes / place search 0 · NEW-11 network all UUIDs · NEW-12 editorial-standards fixture review + demo task pages · NEW-13 "human-verified" wording · NEW-14 site-wide "How we know this" on dossiers, tier sum · NEW-15 sources as keys only · NEW-16 attribution to "SIG contributors" |
| **S2** | 16 | NEW-17 … NEW-32 (tautological tiles, three site counts, provisional flag, dossier glyphs, research-queue filter, task-page copy, inert layers, perf budgets, a11y, 404s, SEO, methodology inputs, freshness, coverage promises, JSON licence, mobile map) |
| **S3** | 2 | NEW-33 contribution-back link, NEW-34 corrections-log start date |

By category: provenance 5 · epistemic 4 · task 3 · fixture-leak 2 · ia 2 · truth 2 · discoverability 2 ·
licensing 2 · copy 2 · states 2 · safety 1 · citation 1 · print 1 · consistency 1 · perf 1 · a11y 1 · freshness 1 ·
mobile 1. Routed: `orchestrator-S0` ×2, `C3` ×6 (NEW-9, 13, 14, 18, 20, 29), `E1` ×1 (NEW-16), `G1` ×1 (NEW-26),
the rest to `C6`. `chain_tip` notes: the dispute (NEW-3), permalink (NEW-4) and island (NEW-9/11/24) code changed
after the deployed commit `5c064881`. The fixture pages, home, methodology and "How we know this" did not change.

## 12. Evidence manifest

`docs/build/logs/next-phase/C2/`: `capture.jsonl` (87 page captures with status, title, H1, meta, canonical, links,
keyboard stops and axe summaries), `interactions.jsonl` (search, map and keyboard sessions), `curl_checks.txt`,
`shots/` (PNG), `pdf/` (9 PDFs plus page renders), `lh/` (16 JSON), `axe/` (14 JSON), `text/` and `html/` (page
text and DOM), `manifest.json` (drift guard), `task_listing.txt` (78 task slugs, read-only bucket listing), `tools/`,
and `SHA256SUMS` (438 entries).
