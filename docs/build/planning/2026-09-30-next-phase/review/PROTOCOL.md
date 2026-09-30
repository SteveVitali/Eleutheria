# C1 — Review protocol and rubric for the live product (C2, reused by C3/C4)

Row **C1** of `META_PLAN.md` (Stage P, owner P/D). Authored 2026-09-30T16:54Z (`date -u`) by a fresh subagent in the
planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `6266f393`;
web/api/ops/exports code byte-identical to chain tip `b051732c`, checked with `git diff --stat b051732c HEAD -- web api ops exports`).
Companion inventory: [`ROUTES.csv`](ROUTES.csv) (48 rows). `PD` below = `docs/build/planning/2026-09-30-next-phase`.

**Independence.** This protocol was designed from the spec, the product source, the public release bytes and route
probes only. `META_PLAN.md` Appendix A and `PD/findings/**` were **not read**. The operator's own review requests arrive later
as the D1 answer to Q-D1-24 (§10). The C2 reviewer should not read Appendix A or `findings/**` before finishing its pass.

**What this is not.** An agent walkthrough is not user research (P4, P5, SIG-FIND-007). Nothing C2/C3/C4 produces counts toward
`D-R10-USERS-1` or any human-evaluation obligation. Label the narratives *agent walkthrough*.

---

## 0. Inputs read (P1: nothing cited that was not read)

| input | where |
|---|---|
| Principles, C-stream rows, finding schema, evidence storage | `META_PLAN.md` §3, §6 C1–C6 (+D1–D3), §7.1, §8.2, §8.4, §9 |
| Baseline | `PD/baseline/BASELINE.md` (freeze 2026-09-30T16:31:55Z) |
| Charter, questions, defining standard | `docs/2_canonical_design_spec.md` §1 (L211–285), §2 (L287–382), §3.1–3.3 (L384–438) |
| Absence / epistemic vocabulary | spec §9.5 (L986–1005), §10.7 (L1385–1431) |
| Geo sensitivity, attribution | spec §19.4–19.6 (L3293–3338) |
| Denominators, freshness | spec §32.2–32.4 (L5049–5073) |
| API, exports | spec §37–§38 (L5558–5710) |
| Product surfaces, personas, design centre | spec §39.0–§41 (L5711–6041): SIG-UI-001…050 (all 55 ids enumerated with `grep`) |
| Part VIII | spec §42–§46.3 (L6043–6560) |
| Round-10 extension | spec §55 (L7273–7390): SIG-FIND-001…008, SIG-DOS-001…005 |
| Frozen surface contracts | `docs/build/reports/PUBLIC_SURFACE_DATA_CONTRACTS.md` |
| P32.24 kit | `…/p32.24-investigation-journey-verification/{USABILITY_TASK_PROTOCOL.md, JOURNEY_PORTFOLIO.md, README.md}`; `JOURNEY_PORTFOLIO.json` skimmed |
| Budgets | `web/lighthouserc.json`, `docs/build/reports/p32.15-island-budgets.md`, `web/tests/e2e/island-budgets.json` |
| Route inventory | `web/src/pages/**` (36 files) at chain tip; `git ls-tree 5c0648812053 -- web/src/pages` (32 files) |
| Deployed site | `gcloud storage ls -l -r gs://zeta-medley-508121-u7-sig-web/**` (289 objects, 2026-09-30T16:40:19Z) |
| Public release | `gs://zeta-medley-508121-u7-sig-public/manifest.json` + 9 small `web/*.json` / `datapackage.json` (read with `gcloud storage cat/cp`, 16:42–16:47Z) |
| Deploy record | `docs/build/reports/REPUBLISH_LIVE_2026-09-27.md` §0–§3 |
| Serving code | `web/src/layouts/BaseLayout.astro`, `web/src/lib/data.ts`, `web/src/pages/dispute.astro`, `web/astro.config.mjs`, `ops/web/nginx.conf`, `api/src/api/{cli,app,intake}.py`, `ops/src/ops/cli.py`, `api/AGENTS.md`, `web/AGENTS.md`, `ops/config.toml [intake]` |

---

## 1. What is under review

| item | value | evidence |
|---|---|---|
| Public origin | `https://surveillancegraph.org` (LB → Cloud Run `sig-web`, nginx over gcsfuse `sig-web` bucket); also `https://sig-web-e5ctyx36jq-uc.a.run.app` | BASELINE.md "Production"; REPUBLISH_LIVE §2 |
| API origin (no custom domain) | `https://sig-api-e5ctyx36jq-uc.a.run.app` — reads the **live spine**, not the release | BASELINE.md; `api/src/api/cli.py` |
| Public release | `sig-2026-09-27-ce480ab1`, manifest sha256 `717aeb4499523acf22987428b29f3a46b5ed3aa27a91b1b6e055c7e65aa872d6`, 132 artifacts, as-of world/belief 2026-09-27, ruleset `p27.3/1.0.0`, resolver `0.0.0` | `gcloud storage cat` 16:42:52Z; matches A1 |
| Deployed web build | 208 HTML pages + 56 JSON + 12 PMTiles + 11 `_astro` + `watch/citations.txt` + robots = 289 objects, all dated 2026-09-27T01:33:56–59Z | bucket listing |
| Web source of the deployed build | **inference**: commit `5c0648812053` (P31.16; the `sig-web` image tag in REPUBLISH_LIVE §2), 32 page files — i.e. **older than the chain tip** | `git ls-tree` |
| Chain-tip web source | `b051732c`, 36 page files (adds `/releases/`, `/research-dossier/` ×3) | `find web/src/pages` |

Consequence: a live defect may already be fixed, or differently broken, at the chain tip. Every C2 finding records a
`chain_tip=` note in its evidence (§6.6).

### 1.1 Route inventory summary (full table: `ROUTES.csv`)

- **Source (chain tip): 36 route patterns** (36 page files) + 3 non-page outputs (tiles, `_astro`, robots).
- **Deployed: 23 route patterns materialised**: 16 singleton HTML pages, `/map/style.json`, `/watch/citations.txt`,
  `/data-freshness/[...sort]` ×4, `/dossier/[slug]/` ×55, `/dossier/[slug]/print/` ×55, `/dossier/[slug].json` ×55 and
  `/task/new/[slug]/` ×78. `5c0648812053` is an ancestor of the chain tip; 7 commits touch `web/src/pages` between them.
- **13 mismatches (source pattern with 0 live instances):**
  - 4 chain-tip-only Round-10 pages, never deployed: `/releases/`, `/research-dossier/`, `/research-dossier/[slug]/`,
    `/research-dossier/[slug].json` (live 404 at 16:43Z) → **C4**.
  - 6 `/curate/**` patterns, removed from the public bucket by Track 0.2 (must stay 404).
  - 3 generated-empty: `/evidence/[id]/` (release `web/evidence.json` has 255 artifacts but 0 `claim_views`),
    `/watch/[jurisdiction].ics` and `.xml` (release `web/watch.json` is `[]`).
- **Deployed-only:** no page routes; only build outputs (12 compartment tiles, 11 assets, robots). Absent: `sitemap.xml`,
  `sitemap-index.xml` (404), a `404.html` (nginx `error_page 404 /404.html` has no target; unknown routes return a 146-byte body),
  a `/task/` index (403).

---

## 2. Ground rules (apply P1–P14 to the review)

1. **Read-only production (P3).** Allowed: GET navigation, clicking links, client-side controls (map layers, zoom, filters,
   network expand), typing in client-side search boxes, keyboard navigation, print preview. **Forbidden:** submitting any `<form>`
   to a server, any POST/PUT/DELETE, sign-ups, the intake receiver, curation, load or stress testing, crawling beyond the page
   sample, gcloud writes, changing site data.
2. **Politeness.** Wait at least 3 s between page navigations. Run requests one at a time; do not run jobs in parallel against
   the live origin. Budgets for C2: at most 450 page navigations (Chrome and headless combined), at most 16 Lighthouse runs, at most
   10 API GETs. Budgets for C3: at most 150 MB of release downloads. Never download `web/research_queue.json` (144 MB) or any
   `*.geojson`/`*.jsonld` over 50 MB. Egress is the operator's cost (SIG-EXPORT-008).
3. **Clock (P2).** Every timestamp comes from `date -u` or a tool timestamp. Record any date the site shows that is **later than
   `date -u`** as a finding (category `freshness`).
4. **Evidence (P1, §8.4).** Every observation cites URL + viewport + `observed_at` + evidence class. Commit text evidence under
   `PD/review/`. Put screenshots, PDFs, HAR files and Lighthouse JSON in `docs/build/logs/next-phase/<row>/` (gitignored). Cite each by
   sha256, and list them all in `docs/build/logs/next-phase/<row>/SHA256SUMS`.
5. **Evidence classes:** `live-read` (seen on the live site), `recorded-execution` (Lighthouse/headless/axe output),
   `code` (cross-checked in source), `inference` (interpretation — say so), `operator-statement`.
6. **No secrets (P14).** Do not copy cookies, auth headers or tokens. The public site needs none.
7. **Stop on S0.** If an observation plausibly meets the S0 bar (§9), stop, record it, and report it to the planning
   orchestrator at once. Do not act on production yourself.
8. **Drift guard.** At the start and end of C2 and C3, record `curl -sI https://surveillancegraph.org/` `Last-Modified` and the manifest
   sha256 (2 GETs). The baseline values are `Sun, 27 Sep 2026 01:33:43 GMT` and `717aeb44…72d6`. If either changes mid-review, pause,
   tell the orchestrator, and re-derive §5.3 with the same rules.
9. **Chrome hygiene (Q-5).** Load the `anthropic-skills:chrome-browser` skill before the first Chrome step. Work in a new
   tab/window of the operator's Chrome. Never read or act in the operator's other tabs. Never sign in. Avoid native dialogs. Print is
   done headless (§6.4).

---

## 3. Personas and task scripts

Hand each task to the persona as a **goal**, never as instructions. Start from the stated URL, which is usually `/`, so that
discoverability is tested. Expected answers come from release `sig-2026-09-27-ce480ab1` bytes, verified by sha256 against the
manifest. C2 re-verifies them at run time. If they differ, record the new value, **not** the old one.
Outcome codes follow P32.24: `completed | completed_with_detour | abandoned`, plus `wrong_conclusion_risk` (y/n: would a reasonable
person leave with a false belief?). There are **12 personas and 31 tasks**. P1–P8 come from SIG-UI-001, and P1 is the design
centre (SIG-UI-002). P9–P12 were added by this row.

Release facts the expected answers rely on. Artifact sha256 prefixes are from the manifest:

| fact | source |
|---|---|
| 55 dossiers: 54 jurisdiction codes (US states, countries, sub-national ISO codes) + `unresolved`; **no city/county-level dossier; no `ok`** | `web/dossier_index.json` `a4938e68…` |
| TX: "3994 of 3996 evaluable geolocated site observations in TX", 3,996 publishable subjects, sources `camreg_austin_tx, camreg_friendswood_tx, camreg_mctx_tx, camreg_txdot_rep_tx`; gaps: sharing partners NOT_RESEARCHED, coordinate conflicts UNRESOLVED; `termination`/`authorization`/`legal_regime` all null | `web/dossiers.json` `d4fafc19…` |
| FL: "8001 of 9965 …", 9,965 subjects, 4 source families, UNRESOLVED coordinate gap. GA: "7049 of 7049", no UNRESOLVED gap. MD: "2752 of 2753", 7 source families, UNRESOLVED. PT: "0 of 1", 1 subject, UNRESOLVED. `unresolved`: "166142 of 166210", 58 source families | same |
| every dossier `asOf` = world/belief 2026-09-27, `belief_pinned: false`, ruleset `p27.3/1.0.0` | same |
| renewal watch empty: `web/watch.json` = `[]`; `decision_point: null`, "0 contracts on the renewal watch" | `37517e5f…`, `web/analytics/decision_point.json` `28874e76…` |
| corrections log empty: `web/corrections.json` = `[]` | `37517e5f…` |
| evidence: 255 artifacts, 0 claim views | `web/evidence.json` `3df209d5…` |
| "How we know this": site 255 artifacts, date range 2020-01-28→2026-09-26, denominator "2423194 publishable tier-0 claims…"; corrections 0; research queue 243,761 tasks, all `unreviewed` | `web/analytics/provenance.json` `4a5d8ed7…` |
| coverage: 127 metrics, all `is_population_total: false`; first = "2423200 of 2423200" published tier-0 claims with a resolvable evidence artifact | `web/coverage.json` `b69c03fd…` |
| bulk data: 12 licence compartments (`ccby3` CC-BY-3.0 … `osm_physical` ODbL-1.0 154,705 rows … `portal` CC-BY-SA-4.0 … `sig_graph` CC-BY-4.0 4,834 site rows, 632 sharing edges, 55 jurisdiction rows) | `manifest.json` |
| API: `/terms` 200, `/openapi.json` 200, `/v1/dossier/fl` 200 (16:43Z) | route probes |

### P1 — Local advocate, council meeting in 6 days (design centre)
Arrives with: "What is deployed here, what does it cost, when does it renew?" Would distrust the site if it reads as advocacy.

| id | task (goal handed to persona) | start | evidence-grounded expected answer / success criterion | spec ids |
|---|---|---|---|---|
| P1-T1 | "You live in Austin, Texas. Find what this site records about surveillance where you live." | `/` | No city-level record exists. The finest scope is `/dossier/tx/`. **Success:** it is reached in ≤4 clicks, and the persona can say (a) "3,994 of 3,996 evaluable geolocated site observations", with the note that this is an observation count and not a census, (b) that the record is state-level, not city-level, and the site says so, (c) which sources it rests on. **Fail:** the persona concludes there is nothing about Austin, or takes the count as a device census. | SIG-UI-048, -049, -012, SIG-METRIC-003, SIG-UI-043 |
| P1-T2 | "What does it cost, when does it renew, and what is your real deadline to act?" | `/dossier/tx/` | Unknown at this release: TX contract, authorization and legal-regime fields are null, and the watch is empty. **Success:** the page says *unknown*, names the kind of absence (not researched vs no evidence found), shows `next_decision_date` as unknown, and does not imply that no contract exists. | SIG-UI-010, -011, -014a, -014b, -015, -026, SIG-TIME-012 |
| P1-T3 | "Print something you can hand a council member." | `/dossier/tx/` | `/dossier/tx/print/` exists. **Success:** the PDF is paginated, every page carries the as-of date **and** the permalink, sources are listed, "what we don't know" and the incompleteness banner appear in print, attribution/licence is present, the tone is neutral, and nothing is truncated. | SIG-UI-013, -011, -012, SIG-GEO-013, SIG-UI-042, -043 |
| P1-T4 | "Which documents should you bring to the meeting?" | `/dossier/tx/` | There is no decision point (`decision_point: null`), and 255 evidence artifacts exist nationally. **Success:** the site gives a ranked, TX-relevant citation list with permalinks and as-of dates, **or** says plainly that none is available for this scope. **Fail:** a generic or unrelated list presented as a recommendation, or ranking by persuasion. | SIG-UI-027a, -027b, -027c, J-3 (SIG-CHART-008) |

### P2 — Investigative journalist on deadline (verifying a number)
Would distrust the site if a number appears with no source, or if the page changes under a citation.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P2-T1 | "Quote the site's headline national figure in one sentence you could defend to your editor." | `/` | Every headline figure has a named denominator, an as-of date, a "not a census" framing (`is_population_total: false`), and a path to its source artifact in ≤3 clicks. C3 confirms the value matches the release. **Fail:** a bare total, or two different values for the "same" figure. | SIG-UI-049, SIG-METRIC-003/009/010, SIG-UI-044, -035 |
| P2-T2 | "Florida: can you say '8,001 of 9,965'? What is 'evaluable', where does it come from, and how do you cite it so the citation won't move?" | `/dossier/fl/` | The row value matches `dossiers.json`. **Success:** the persona finds the definition of the denominator, the four sources, and a cite-this-page with the as-of pair and ruleset `p27.3/1.0.0` that is belief-pinned (or visibly states it is not), and can explain the 1,964 gap. | SIG-UI-014, -035, -043 (rule 5), SIG-CHART-013 |
| P2-T3 | "Is anything on this page disputed?" | `/dossier/fl/` | FL has an UNRESOLVED gap, "Subjects with conflicting coordinate evidence". **Success:** a persistent contested/unresolved marker appears where the affected figure appears, the competing claims (or at least their count and a link) are reachable, and the gap is not buried. | SIG-UI-008, -009, §31, SIG-TIME-010 |

### P3 — Academic researcher (national picture, denominators, downloading data)
Would distrust the site if coverage is implied to be complete.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P3-T1 | "Download the national dataset of mapped sites. What licence(s) apply and how many rows?" | `/` | The manifest lists 12 compartment files with per-file licences and checksums. **Success:** reached **from site links** (not by guessing bucket URLs) in ≤4 clicks, with per-file licence, checksum and row count visible. | SIG-EXPORT-001/002/005/006, SIG-LIC-012, SIG-UI-049 |
| P3-T2 | "Which jurisdictions are covered, and how complete is coverage?" | `/` | 55 index entries, including `unresolved` (166,210 subjects, the largest bucket), and 127 coverage metrics with named denominators. **Success:** the persona states that an unlisted jurisdiction is not the same as no infrastructure, and notices the size of the unresolved bucket. | SIG-UI-048, SIG-METRIC-003/004, SIG-UI-012 |
| P3-T3 | "Find the methods and the reproducibility inputs for what you downloaded." | `/` | Methodology linked from every dossier. **Success:** all four manifest values (as-of belief 2026-09-27, snapshot 2026-09-27, resolver `0.0.0`, ruleset `p27.3/1.0.0`) are found on-site and agree with the manifest. | SIG-UI-034, SIG-EXPORT-003, SIG-UI-049 |

### P4 — Civil-liberties attorney (provenance chain)
Would distrust the site if inference is presented as observation.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P4-T1 | "Pick any claim on a dossier and show me the document it rests on, with the page anchor and acquisition history." | `/dossier/md/` | The release has 0 claim views, so no `/evidence/<id>/` page exists. **Success:** the persona reaches an artifact record with capture date, digest, acquisition method and locator, **or** the site states what is unavailable and why. Record whether *any* link path from a dossier figure to evidence exists. | SIG-UI-028, -030, -014 |
| P4-T2 | "Is any inference here presented as observation?" | `/network/`, `/map/`, `/dossier/md/` | Derived facts are labelled as derived. The three access-edge types are distinct and never merged by default. Derived map layers are toggled separately. **Success:** every derived statement on the three pages carries a label. | SIG-CHART-013, SIG-UI-016, -024, -025 |

### P5 — Council staffer ("is what the vendor told us consistent with the record?")
Would distrust the site if the tone is hostile to their institution.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P5-T1 | "A vendor told council the state has 5,000 cameras. What does SIG's record say, and is that a contradiction?" | `/dossier/ga/` | GA: "7049 of 7049 evaluable geolocated site observations", an observation count from named sources, not a device census. **Success:** the persona can say what SIG's number measures, and that a different quantity (contracted vs observed) is not necessarily a disagreement. | SIG-UI-009, P11 (§3.2), §29.1, SIG-UI-043 |
| P5-T2 | "Would you forward this page to the police chief as neutral?" | `/dossier/ga/`, `/methodology/` | **Success:** no characterizing verbs, no allegation stated as fact, evaluative statements attributed, and the methodology states SIG's position on avoidance in its own voice. | SIG-UI-042, -043, -045, SIG-GOV-019 |

### P6 — Resident ("is there surveillance near me, and who runs it?")
Would distrust the site if absence looks like proof of absence.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P6-T1 | "Is there surveillance near downtown Canberra, and who runs it?" | `/` | AU-ACT has 1,299 of 1,328 geolocated. Operators and sharing partners are largely NOT_RESEARCHED. **Success:** a plain answer with an honest gap statement. The coverage underlay is bound to the points. An empty area does not read as "none here". "Who runs it" is answered or shown as unknown, with the kind of absence. | SIG-UI-017, -018, -019, -020, -007, SIG-TIME-012 |
| P6-T2 | "Find the same answer without using the map." | `/map/` | **Success:** the tabular or no-JS equivalent on `/map/` (or via search) gives the list for the area. | SIG-UI-037, -050 |

### P7 — Downstream developer ("can I build on this?")
Would distrust the site if identifiers move.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P7-T1 | "Find the API documentation, the terms of use and a stable identifier you can dereference." | `/` | The API lives at the `run.app` host (`/openapi.json`, `/terms`, `/id/{type}/{uuid}`), and robots.txt says terms are "at /terms (the API)". **Success:** found by following site links, with rate limits and an acceptable-use remedy stated. | SIG-API-008, -011, -013, SIG-IDENT-031 |
| P7-T2 | "Get one jurisdiction's dossier as machine-readable data and check its as-of and licence." | `/dossier/au-act/` | `/dossier/au-act.json` exists (55 are deployed). **Success:** it is linked from the HTML page, carries the as-of pair, licence and attribution, and has stable ids. | SIG-API-002/004/005, SIG-EXPORT-006 |
| P7-T3 | "Subscribe your newsroom's calendar to renewals for Texas." | `/watch/` | No `.ics` or `.xml` feed is deployed, because the watch is empty. **Success:** the site explains that feeds exist per jurisdiction once there are items, **or** offers a valid empty feed. **Fail:** dead feed links, or feeds missing with no explanation. | SIG-UI-027, SIG-UI-014b |

### P8 — SIG contributor ("what needs doing near me?")
Would distrust the site if work disappears into a queue with no effect.

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P8-T1 | "Find a concrete research task for Maryland and what would close it." | `/` | The research queue holds 243,761 tasks (per provenance). **Success:** a task card states the closing condition, evidence sought, assignee class and effort, and a geographic filter works without JS. | SIG-UI-031, SIG-TASK-002 |
| P8-T2 | "On a dossier, click something the site says it doesn't know. Where does it lead?" | `/dossier/md/` | Gaps link to `/task/new/<slug>/` (71 jurisdiction-level task pages exist). **Success:** the task page is for that exact gap, with no dead end, and explains how to contribute without a form. | SIG-UI-007, -011 |

### P9 — OSM / DeFlock contributor

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P9-T1 | "Does this site use OpenStreetMap data? Under what licence, and how is it attributed?" | `/map/` | The `osm_physical` compartment is ODbL-1.0 and is served as tiles and bulk files. **Success:** "© OpenStreetMap contributors" and the ODbL are visible on the map, on downloads and in printed or static contexts, and the compartment separation is legible. | SIG-GEO-013, SIG-LIC-006, -008, SIG-EXPORT-005 |
| P9-T2 | "Does SIG give anything back to OSM? How would you see it?" | `/` | `/contribution-back/` holds the leverage metric. **Success:** the count has a date and definition, and the CC0 licence of the contributed subset is stated. | SIG-CONTRIB-016e, SIG-LIC-007a/b/c |

### P10 — Agency or vendor representative seeking a correction (hostile reader)

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P10-T1 | "Your agency's count on the Maryland page is wrong. Get it corrected. What will happen?" | `/dossier/md/` | A dispute link on every page leads to `/dispute/`: categories, priority order, no identity needed, outcomes including refusal. The receiver is not operating. **Success:** reached in 1 click from the claim, the non-operating state is stated honestly with any interim channel (or "none"), and the persona expects review, not an instant change. **Do not submit anything.** | SIG-UI-033, SIG-GOV-001…004, SIG-FIND-006 |
| P10-T2 | "The claim is accurate but misleading. Can you attach your response? Has SIG ever refused or corrected anything?" | `/dispute/` | The Annotate outcome exists. The corrections log is empty (`[]`). **Success:** both are found, and the transparency counts (including refusals) are shown as zero rather than missing. | SIG-GOV-010, -011, SIG-UI-032 |
| P10-T3 | "Read your agency's page as its counsel and list every sentence you'd challenge." | `/dossier/md/`, `/dossier/unresolved/` | **Success:** 0 characterizing statements, and every figure is attributed and dated. | SIG-UI-042, -043, -045 |

### P11 — Skeptic checking provenance ("prove it")

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P11-T1 | "Pick a number on the home page and trace it to raw data you can download yourself." | `/` | **Success:** the chain page → export JSON (manifest sha256) → bulk file completes using on-site links only (done jointly with C3). | §3.1, SIG-CHART-011, SIG-METRIC-005 |
| P11-T2 | "Compare the 'How we know this' box on three different pages. Is it about the page you're on?" | `/`, `/dossier/fl/`, `/corrections/` | Per SIG-UI-044 each box is page-specific: artifact counts, tier distribution, source independence, date range, rules and human-review status. **Success:** the numbers reconcile with coverage (e.g. 2,423,194 vs 2,423,200) or the difference is explained, and review status is stated honestly. | SIG-UI-044, SIG-METRIC-003 |
| P11-T3 | "Has this site ever corrected itself? Show me." | `/` | The log is empty. **Success:** it honestly says 0 corrections, with the start date of the log and the transparency counts. No sample entries. | SIG-UI-032, SIG-GOV-006, -011 |

### P12 — Mobile-only visitor (390×844)

| id | task | start | expected / success | spec ids |
|---|---|---|---|---|
| P12-T1 | "On your phone, find what's known about your state and send a friend a link." | `/` (mobile) | **Success:** the dossier is reached; the navigation is usable by touch and keyboard; there is no horizontal scroll; targets are ≥24×24 CSS px; the shared link is the canonical permalink. | SIG-UI-049, WCAG 1.4.10, 2.5.8 |
| P12-T2 | "Open the map and find cameras near you. If it's slow, get the list instead." | `/map/` (mobile) | `/map/` document is 3.46 MB raw plus the island. **Success:** usable under Lighthouse mobile throttling, and the tabular fallback can be reached without loading the island. Record LCP, TBT and bytes. | SIG-UI-041, -050, SIG-FIND-005 |

### 3.1 P32.24 T1–T7 reuse
T1–T7 (`USABILITY_TASK_PROTOCOL.md`) target the release archive (`/r/<pub>/…`). That archive is not deployed live, so **C4** runs
T1–T7 verbatim as agent scripts against the local registries (§8). The expected answers come from that file, and the outcome codes
are the same. On the live site C2 exercises the closest analogues: T2 → P6-T1/T2, T5 → search for an absent term on `/search/` (§5.4),
T6 → P10-T1, T7 → P2-T3/P11-T2.

---

## 4. Heuristic checklist (H01–H18)

Each heuristic is **pass** (every criterion met on the sampled pages), **fail** (any criterion unmet, which produces a finding), or
**n/a** (with a reason). "Everywhere" means every page in the §5 sample.

| id | heuristic | pass criteria (all must hold) | how to check | spec ids |
|---|---|---|---|---|
| H01 | **Truthfulness of every number** | Every material number shows its unit and denominator, sits within an as-of context, and is traceable to a release artifact value. The same metric has the same value everywhere. No figure is a population total unless it is labelled so. | C2 lists numbers per page in the page log (§6.5). C3 traces them (§7). | §3.1, SIG-CHART-011, -013, SIG-METRIC-003, -005, -008…010, SIG-UI-014, SIG-EXPORT-003 |
| H02 | **Epistemic legibility** | Support is shown as a 4-step glyph plus text plus evidence count plus downgrade reason. The four fields (status/support/agreement/currency) are independently visible. Nothing relies on colour alone. No green for epistemic state. Exactly one hatch texture means absence, the four absence kinds are distinguishable, and each is clickable to a task. Contested markers appear at every appearance. Contradictions show a value range with competing claims. An incompleteness banner shows the count of unresearched fields. "What we don't know" appears in the summary and in print. Unknown values say "unknown" rather than being omitted. Inference is labelled. Provisional or evaluation-deferred status is disclosed. | Visual plus accessibility tree plus source text (`/visual-language/` is the reference) | SIG-UI-003…009, -011, -012, -015, SIG-TIME-010…012, SIG-EPIS-023…025, SIG-CHART-013 |
| H03 | **Task success** | Each §3 task is `completed` with `wrong_conclusion_risk=n` inside its click budget (design centre ≤4 clicks per step) | §6.2 journey pass | SIG-UI-001, -002, SIG-CHART-008 |
| H04 | **IA and navigation** | Navigation is grouped, uncluttered, keyboard-accessible and identical on every page. The national landing summarises with named denominators, jurisdiction reach and entry points to every surface. There is no single-jurisdiction demo entry point. Every sampled route can be reached from `/` in ≤3 clicks, with no orphan routes. Methodology, freshness and coverage are linked from every dossier. There is a dispute link on every page. | Click-depth map from `/`; grep live HTML for nav links | SIG-UI-048, -049, -034, -033 |
| H05 | **Copy clarity and plain language** | Register rules 1–6 hold. There is no unexplained internal jargon in public copy: requirement ids, snake_case source keys, schema names, bare ISO codes without names. Headings say what the section answers. The design-centre pages read at roughly grade 10 or below (spot-check 3 paragraphs). | Read aloud; list jargon tokens per page | SIG-UI-002, -043, -045, -046 |
| H06 | **WCAG 2.2 AA spot checks** | Keyboard reaches all functionality with no trap (2.1.1/2.1.2). The skip link works (2.4.1). Focus is visible and not obscured (2.4.7/2.4.11). There is one `h1`, heading order is logical, and landmarks exist (1.3.1/2.4.6). Titles are unique (2.4.2). Link purpose is clear (2.4.4). Contrast is ≥4.5:1 for text and ≥3:1 for UI, glyphs and focus rings (1.4.3/1.4.11). Images and glyphs have alternatives (1.1.1). Content reflows at 320 CSS px with no 2-D scroll except data tables and maps (1.4.10). Text spacing works (1.4.12). Targets are ≥24×24 (2.5.8). Map panning has a non-drag alternative (2.5.7). `lang` is set (3.1.1). Navigation is consistent (3.2.3). Island controls have name/role/value (4.1.2), and status messages are announced (4.1.3). Lighthouse accessibility scores 1.0 on budget URLs. | §6.3 keyboard pass; accessibility-tree read; Lighthouse (axe) JSON; headless 320 px | SIG-FIND-005, SIG-UI-005, WCAG 2.2 |
| H07 | **Performance and JS budgets** | Zero-JS content pages have 0 `<script>`, Lighthouse `total-byte-weight` ≤153,600, performance ≥0.9, accessibility 1.0. `/map/`: script ≤2,000,000 raw / ≤600,000 gzip, total ≤2,300,000 raw / ≤750,000 gzip, document ≤153,600. `/network/` and `/search/`: script ≤400,000 raw / ≤140,000 gzip, total ≤450,000 / ≤160,000, document ≤153,600, performance ≥0.5 (advisory). Record Lighthouse measures against the `lighthouserc` numbers and raw object bytes (`ROUTES.csv`) against `island-budgets.json`. Note that CI measured **fixtures** (`/dossier/oklahoma-city/` does not exist live), so this is the first real-data measurement. | Lighthouse desktop and mobile (§6.4); bucket sizes | SIG-UI-036, -041, -050, SIG-FIND-005, ADR-134 |
| H08 | **Responsive and mobile** | At 390×844: no horizontal page scroll; navigation usable; tables scroll inside their container or reflow; body text ≥16 px; map usable or its fallback reachable; no content hidden by fixed elements | Chrome mobile viewport plus headless iPhone 14 | SIG-UI-049, WCAG 1.4.10 |
| H09 | **Printed dossier** | The print PDF is paginated. Every page carries the as-of date and the permalink. Sources, "what we don't know" and the incompleteness banner are present. OSM and licence attribution appear where relevant. No navigation chrome is printed. Tables are not cut. It stays legible in greyscale. Record the page count. | Headless `emulateMedia(print)` plus `page.pdf` (§6.4) | SIG-UI-013, -011, -012, SIG-GEO-013 |
| H10 | **Citations, permalinks, as-of** | Every page has a belief-pinned permalink and a cite-this-page block with the as-of pair and ruleset. These values equal the manifest `reproducibility_inputs`. The permalink resolves with 200 and is canonical (`<link rel=canonical>` equals the permalink). Trailing-slash behaviour is stable (301 to the slash form). The release id is shown or derivable. | Compare page text with the manifest; one GET per sampled permalink | SIG-UI-035, -049, SIG-FIND-001/002, SIG-TIME-008 |
| H11 | **Licensing and attribution** | A licence is shown wherever data appears (map, downloads, dossiers, JSON). Each share-alike compartment (`osm_physical` ODbL-1.0, `portal` CC-BY-SA-4.0, `dot511_ccbysa2` CC-BY-SA-2.0) is separate and attributed, and its public serving is authorised by the current ADR chain. Check ADR-096, which kept share-alike restricted at the P27.8 cut-over, and every successor decision; the spec cites ADR-118 for per-compartment tile archives, SIG-GEO-012. OSM attribution appears in every rendering context, including print and static images. There is a site licence statement (code Apache-2.0, data CC-BY-4.0, docs CC-BY-4.0). | `/map/style.json` attribution strings; page footers; downloads; `git grep` the ADR chain (code evidence) | SIG-LIC-004a, -006, -008, -011, SIG-EXPORT-004…006, SIG-GEO-013 |
| H12 | **Part VIII safety** | None of the following appear anywhere, **including inside source identifiers, labels, file names, task slugs, tile properties or JSON**: plate numbers, private-person names or account handles, home addresses, operator/user identifiers. Any named individual is backed by a recorded five-prong, two-reviewer decision. Coordinate precision matches the tier: no current position for mobile assets, no C3/C4 locations. Candidate or RF assets stay out of device layers, and RF wording does not imply a known device. Free text from records is screened. There is no liveness or per-person lookup, and no evasion instructions. The methodology states the avoidance position. No internal or curation surface is public (`/curate/` 404). | Read the "Sources"/"How we know this" rows of **every** sampled dossier, decode task slugs, count coordinate decimals in the map table and popups, `grep` the downloaded JSON | SIG-PUB-001…017, SIG-GEO-008…010, SIG-API-012, SIG-GOV-017…019, RISK-P21-10 |
| H13 | **Provenance and trust signals** | "How we know this" is page-specific and complete (SIG-UI-044 fields). The freshness page shows per-source last run, last change, status and stale count. Human-review status is stated honestly: no "human-verified" or "reviewed" wording unless human review was completed (P4/P5). Evaluation status (provisional or deferred) is disclosed where it applies. | Page text vs `provenance.json` and `freshness.json` | SIG-UI-044, -034, SIG-METRIC-007, SIG-EVAL-006 |
| H14 | **Empty, error and 404 states** | Empty collections (watch, corrections, evidence viewer, feeds) say what "empty" means and why, without implying that nothing exists. The 404 page is branded, gives a route home and uses no dead-end wording. `/task/` (403) is explained or not linked. Each island degrades to its fallback when JS is off or fails. | Visit `/watch/`, `/corrections/`, `/evidence/`, an unknown route, `/task/`; islands with JS off | SIG-UI-037, -050, -048 |
| H15 | **Discoverability** | `<title>` is unique and descriptive. There is a meta description, a canonical link, `lang`, and a sitemap (404 at C1 time). robots.txt is correct. Social or Dataset metadata is optional; if absent, file it as `NEW-NEED`. Jurisdiction names are human-readable (e.g. "Texas", "England"), not only codes. HTTP redirects to HTTPS cleanly. | View source; `curl -sI` | SIG-UI-049 (IA), SIG-UI-037 (archivability) |
| H16 | **Consistency across pages** | The same metric has the same value and label everywhere. Terminology is consistent (site/device/observation/subject). Date format and as-of are the same on every page. Navigation and footer are identical. Dossier section order matches SIG-UI-010 on every sampled dossier. | Cross-page table in the page log | SIG-UI-010, -049 |
| H17 | **Freshness and release coherence** | The as-of shown equals the manifest. The age of the data is disclosed relative to today. No date is later than `date -u`. The release id is the same across site, manifest and dossier JSON. | Page log vs manifest | P2, SIG-METRIC-006, SIG-FIND-001 |
| H18 | **No demo or fixture leakage** | No fixture or demo artefacts on production pages: strings such as `demo`, `fixture`, `example`, `okc-seed`, placeholder ids, lorem ipsum. Decode every sampled `/task/new/` slug; 6 decode to `agency:okcpd` with `demo_*` predicates. | Text search of captured pages | SIG-UI-048, -049 ("never a frozen demo constant") |

---

## 5. Page sample

### 5.1 Every live route pattern (from `ROUTES.csv`)
- **20 singleton URLs**, each at desktop and mobile with the full heuristic pass: `/`, `/contribution-back/`, `/corrections/`,
  `/coverage-metrics/`, `/data-freshness/` (plus `/data-freshness/status/`), `/dispute/`, `/dossier/`, `/editorial-standards/`,
  `/evidence/`, `/map/`, `/methodology/`, `/network/`, `/research-queue/`, `/search/`, `/style-guide/`, `/visual-language/`,
  `/watch/`, and the text or JSON routes `/map/style.json`, `/watch/citations.txt` (content check only).
- **Non-page checks (1 GET each):** `/curate/` (must be 404), `/releases/` and `/research-dossier/` (404: record as *not deployed* and
  route to C4, not as broken), `/sitemap.xml`, one unknown route (the 404 page), `/task/` (403), `http://` → https, a slug
  without its trailing slash (301), `/robots.txt`, one tile `Range: bytes=0-99` request.

### 5.2 Task pages (`/task/new/[slug]/`, 78 live)
Sample 9: one jurisdiction NOT_RESEARCHED (reached by clicking a gap on `/dossier/md/`), one jurisdiction UNRESOLVED (clicked from
`/dossier/fl/`), and all 7 `agency:*` / `device:*` pages. List all 78 slugs from the `/dossier/` gap links or the bucket listing, and
decode each as base64url JSON `[subject, predicate, kind, label]`.

### 5.3 Stratified dossier sample (8 × HTML, print, JSON)
Rules (re-derive from `web/dossiers.json` if the manifest changed). Rank by the "Publishable subjects" row:

| stratum | slug | why | subjects | UNRESOLVED gap |
|---|---|---|---|---|
| unresolved-jurisdiction bucket (largest overall) | `unresolved` | edge case named by C1; 58 source families | 166,210 | yes |
| largest named jurisdiction / has contradictions | `fl` | max named; 8,001 of 9,965 geolocated | 9,965 | yes |
| design-centre anchor (P1) | `tx` | large US state, UNRESOLVED | 3,996 | yes |
| most sources among named / contradictions | `md` | 7 source families | 2,753 | yes |
| smallest | `pt` | 1 subject, "0 of 1" | 1 | yes |
| non-US #1 | `gb-eng` | 11 source families | 1,710 | yes |
| non-US #2 | `au-act` | sub-national ISO code | 1,328 | yes |
| label-ambiguity probe / control (no UNRESOLVED gap) | `ca` | two-letter code shared by a US state and an ISO country (also `ga id pa co ma de il al la mo mn sd va`); check the page says which | 6,139 | no |

Optional if budget remains: `ga` (P5), `us` (country-level bucket, 629), `co-met`.

### 5.4 Islands
`/map/`, `/network/`, `/search/`. Each gets: JS on at desktop and mobile; JS off (headless); keyboard pass; Lighthouse at desktop and mobile.
- **Map:** national zoom (density binning, SIG-UI-019), zoom to TX and AU-ACT, open one popup (count coordinate decimals, look for a
  licence), toggle every layer, check that the coverage underlay is bound to the points (SIG-UI-017), and check that assets without
  coordinates are represented (SIG-UI-020).
- **Network:** default ego view (not a hairball), expand once, filter each access-edge type, read any centrality statistic and its
  entity-resolution quality disclosure (SIG-UI-021…025).
- **Search:** a present term (`Austin`), an absent term (`zzqx-nonexistent`, the T5 analogue: must not read as "no surveillance"),
  a jurisdiction code (`TX`). Search boxes only; never a server form.

### 5.5 Downloads
Is each one **linked from the site**, does it carry a licence and a checksum, and does its size or row count match the manifest? Items:
`manifest.json`, `datapackage.json`, `exclusions.json`, `provenance.ttl` (HEAD only), `/dossier/<slug>.json` ×8, `/map/style.json`,
`sig_graph/jurisdictions.csv` (20 KB, 55 rows), one tile Range request. Bulk traces belong to C3 (§7).

**Sample size:** about 20 + 9 + 24 + 3 + about 10 = **about 66 URLs**, × 2 viewports for pages. That is about 130 Chrome views plus about 70 headless captures
plus 16 Lighthouse runs.

---

## 6. C2 execution procedure (Claude in Chrome)

### 6.1 Pre-flight (blocking)
1. The operator has connected Claude in Chrome (`/chrome`). A1 recorded that it was *not* connected. Load the
   `anthropic-skills:chrome-browser` skill. Open a new window or tab and leave the operator's tabs alone.
2. `date -u`. Run the drift guard (§2.8). Create `docs/build/logs/next-phase/C2/{shots,pdf,lh,text}/`.
3. Extract the headless helper (§6.4) to `docs/build/logs/next-phase/C2/tools/capture.mjs`.
4. Viewports:
   - **Desktop 1440×900:** resize the window, then record `window.innerWidth × innerHeight` and `devicePixelRatio`. Record the actual values if they are smaller.
   - **Mobile 390×844:** resize the window. macOS Chrome may clamp the minimum width (unknown U2). If `innerWidth` is greater than 390, use the zoom method: window width 1170 at 300 % zoom is about 390 CSS px. Take canonical mobile screenshots headless with iPhone 14 emulation.
   - **Reflow 320:** window 1280 wide at 400 % zoom, per WCAG 1.4.10, plus headless at 320 px.

### 6.2 Pass 1 — persona journeys (unanchored)
Run the §3 tasks in order, P1 first. Do not consult §4 until each journey's notes are written. For each task, log in order: the
URLs visited (with `date -u`), clicks per step, wrong turns, time, the answer the persona leaves with (one sentence, as the persona
would say it), whether evidence is cited (y/n), `wrong_conclusion_risk`, and trust or distrust triggers (SIG-UI-001 column 4).
Every step that fails a success criterion becomes a finding.

### 6.3 Pass 2 — page sweep with the heuristics
For each page in §5, at desktop and then mobile, apply H01–H18 and fill the page log (§6.5). Run the keyboard and accessibility-tree
spot checks on `/`, `/dossier/tx/`, `/dossier/tx/print/`, `/map/`, `/network/`, `/search/` and `/dispute/`:
- Tab through the first 30 stops from page load and note skip link, focus visibility, order and traps.
- Press Escape out of the map.
- Read the accessibility tree for landmarks, heading outline, accessible names and alt text.

Label these as an *accessibility-tree proxy*. They are not a test with real assistive technology.
Read console messages (errors) after each load.

### 6.4 Pass 3 — instrumented checks
**Headless capture helper.** Verified 2026-09-30T16:49Z against `file://` copies only, not yet against the live origin. It uses
the Playwright 1.62.1 and Chromium already installed in the main checkout, in **read-only** fashion. Output goes to the logs dir.

```js
// docs/build/logs/next-phase/C2/tools/capture.mjs
// node capture.mjs <out_dir> <label> <url> [desktop|mobile|reflow320] [--nojs] [--print]
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { readFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
const require = createRequire("/Users/stevenvitali/Eleutheria/web/package.json");
const { chromium, devices } = require("@playwright/test");
const [outDir, label, url, vpName = "desktop", ...flags] = process.argv.slice(2);
const noJs = flags.includes("--nojs"), doPrint = flags.includes("--print");
const VP = { desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 },
  mobile: { ...devices["iPhone 14"], viewport: { width: 390, height: 844 } },
  reflow320: { viewport: { width: 320, height: 800 }, deviceScaleFactor: 1 } }[vpName];
mkdirSync(outDir, { recursive: true });
const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
const base = join(outDir, `${stamp}_${label}_${vpName}${noJs ? "_nojs" : ""}`);
const browser = await chromium.launch();
const ctx = await browser.newContext({ ...VP, javaScriptEnabled: !noJs,
  userAgent: `${VP.userAgent ?? "Mozilla/5.0"} SIG-planning-C2-review/1 (read-only)` });
const page = await ctx.newPage(); const consoleErrors = [], failed = [];
page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 300)); });
page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e).slice(0, 300)}`));
page.on("requestfailed", (r) => failed.push(`${r.url()} ${r.failure()?.errorText ?? ""}`));
page.on("response", (r) => { if (r.status() >= 400) failed.push(`${r.status()} ${r.url()}`); });
const resp = await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1500);
const shot = `${base}.png`; await page.screenshot({ path: shot, fullPage: true });
const info = await page.evaluate(() => ({ title: document.title,
  h1: [...document.querySelectorAll("h1")].map((h) => h.textContent.trim()).join(" | ").slice(0, 200),
  inner: `${window.innerWidth}x${window.innerHeight}`, dpr: window.devicePixelRatio,
  scripts: document.querySelectorAll("script").length,
  hscroll: document.documentElement.scrollWidth > window.innerWidth }));
const out = { observed_at: new Date().toISOString().replace(/\.\d+Z$/, "Z"), url, final_url: page.url(),
  status: resp?.status() ?? null, viewport: vpName, js: !noJs, ...info, console_errors: consoleErrors,
  failed_requests: failed, screenshot: shot, screenshot_sha256: sha(shot) };
if (doPrint) { await page.emulateMedia({ media: "print" }); const pdf = `${base}.pdf`;
  await page.pdf({ path: pdf, format: "Letter", printBackground: true });
  out.print_pdf = pdf; out.print_pdf_sha256 = sha(pdf); }
await browser.close(); console.log(JSON.stringify(out));
```
Run it for every page in §5 at `desktop` and `mobile`. Add `--nojs` for the 3 islands plus `/dossier/tx/`. Run `reflow320` for the 7
keyboard-pass pages. Add `--print` for the 8 `/dossier/<slug>/print/` pages, in desktop mode. Append each JSON line to
`docs/build/logs/next-phase/C2/capture.jsonl`. The headless print PDF lacks Chrome's own dialog headers and footers, so judge "as-of and
permalink on every page" from the page's own content.

**Lighthouse.** CLI 12.6.1 was verified against a local static server at 2026-09-30T16:49:47Z. Run it on 8 URLs, each at desktop and mobile
(16 runs), in sequence:

```sh
export CHROME_PATH="$HOME/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
LH=/Users/stevenvitali/Eleutheria/web/node_modules/.bin/lighthouse
for u in / /dossier/tx/ /coverage-metrics/ /data-freshness/ /research-queue/ /map/ /network/ /search/; do
  n=$(echo "$u" | tr '/' '_'); for ff in desktop mobile; do
    P=$([ $ff = desktop ] && echo --preset=desktop || echo "")
    $LH "https://surveillancegraph.org$u" $P --only-categories=performance,accessibility,best-practices,seo \
      --output=json --output-path="docs/build/logs/next-phase/C2/lh/${ff}${n}.json" --chrome-flags="--headless=new" --quiet
  done; done
```
From each report, record the category scores, `total-byte-weight`, `resource-summary` script and total bytes, LCP, TBT and CLS. Compare
them with H07. `/dossier/tx/` replaces the fixture-only `/dossier/oklahoma-city/`, and `/research-queue/` is added as the largest zero-JS page.

### 6.5 Per-page capture record → `PD/review/C2_PAGE_LOG.csv` (committed text evidence)
Columns: `cap_id,observed_at,url,final_url,http_status,viewport,inner_size,js,title,h1,as_of_text,release_or_ruleset_text,
key_claims_excerpt,numbers_seen,console_errors,failed_requests,screenshot_path,screenshot_sha256,pdf_path,pdf_sha256,notes`.
- `key_claims_excerpt`: the visible headline claims, verbatim, at most 1,000 characters, `"`-escaped.
- `numbers_seen`: every material number, verbatim and `;`-separated. This is C3's census input.

Full page text (from the Chrome page-text tool, or `curl` + tag strip) goes to `docs/build/logs/next-phase/C2/text/<cap_id>.txt` and is
cited by sha256. Name screenshots `shots/<UTCstamp>_<route_id>_<slug>_<viewport>.png`. Chrome screenshots are not files, so the
headless PNG is the file of record. A state visible **only** interactively (a hover, a focus ring) is described verbatim, with
`shot=none(interactive-only)`.

### 6.6 Recording findings → `PD/findings/incoming/C2.csv` (§8.2 schema, UTF-8, RFC 4180)
Header (exact):
`f_id,title,stream,surface,observed_at,evidence_class,evidence,severity,category,spec_ids,status,routed_to,operator_priority`

| field | rule |
|---|---|
| `f_id` | `C2-001`, `C2-002`, … (the orchestrator assigns canonical ids when merging) |
| `title` | ≤100 characters, a neutral statement of the defect ("Print dossier omits permalink on pages 2–3"), not a fix |
| `stream` | `C2` |
| `surface` | a representative URL, optionally `@desktop`/`@mobile`, plus `(+N)` when the same root cause appears on N more pages (list them in `evidence`) |
| `observed_at` | `date -u +%Y-%m-%dT%H:%M:%SZ` at the moment of observation |
| `evidence_class` | `live-read` · `recorded-execution` · `code` · `inference` (the interpretive part of any finding is labelled) |
| `evidence` | `;`-separated `key=value`: `url=`, `viewport=`, `shot=<path> sha256=<64hex>`, `text="<verbatim ≤300 chars>"`, `console=<n>`, `lh=<path> sha256=`, `persona_task=P1-T3`, `heuristic=H09`, `chain_tip=` one of `same`, `changed`, `unknown` (did chain-tip source `b051732c` change the relevant file after `5c064881`? `git log 5c0648812053..b051732c -- <file>`), `also=<urls>` |
| `severity` | `S0`–`S3` per §9. When in doubt pick the higher, and give the reason in `evidence` as `why=` |
| `category` | one of `truth · epistemic · task · ia · copy · a11y · perf · mobile · print · citation · licensing · safety · provenance · states · discoverability · consistency · freshness · fixture-leak · ops` |
| `spec_ids` | `;`-separated ids (e.g. `SIG-UI-013;SIG-UI-035`); `NEW-NEED` if no existing requirement covers it |
| `status` | `proposed` |
| `routed_to` | suggested: `C6` (default), `C3` (number trace), `C4` (unreleased surface), `G1` (ops/infra), `E1` (spec contradiction), `orchestrator-S0` |
| `operator_priority` | empty (D2 fills it) |

**Dedupe:** one finding per root cause. The same defect on many pages is one row, not N rows.
**Positive observations** (a criterion passed) are not findings. Record them in the page log `notes` and in JOURNEYS.md so C6 can
say what works.

Example row:
```
C2-007,Dossier print view omits permalink on continuation pages,C2,https://surveillancegraph.org/dossier/tx/print/ (+7),<date -u>,recorded-execution,"url=https://surveillancegraph.org/dossier/tx/print/; viewport=desktop; pdf=docs/build/logs/next-phase/C2/pdf/<UTCstamp>_R09_tx_desktop.pdf sha256=<64hex>; text=""page 2 footer: (none)""; persona_task=P1-T3; heuristic=H09; chain_tip=unknown; also=/dossier/fl/print/ …",S1,print,SIG-UI-013,proposed,C6,
```
*(Illustrative format only. This is not an observation.)*

### 6.7 Per-persona narrative → `PD/review/JOURNEYS.md`
Header: "Agent walkthrough, not user research (P4/P5, D-R10-USERS-1 stays OPEN)", the run window (`date -u` start and end), the release,
the drift-guard values and the Chrome/viewport facts. Then one section per persona (P1–P12):
- who they are and what they arrived with
- for each task: start URL, path (numbered URLs), clicks, time, outcome code, `wrong_conclusion_risk`, the answer they leave with, whether evidence was cited, trust triggers, finding ids
- a 3–5 sentence verdict: would this persona come back, and what single change would matter most

End with a table of persona × task × outcome, a count of findings by severity and category, and the evidence manifest (the `SHA256SUMS` path).

### 6.8 Done when
All 31 tasks have an outcome. All §5 pages have desktop and mobile page-log rows. H01–H18 each have pass, fail or n/a per page class.
The 16 Lighthouse reports and all PDFs are hashed. The drift guard has been run at start and end. `C2.csv`, `C2_PAGE_LOG.csv` and
`JOURNEYS.md` are written. `git status` shows only those three files plus `docs/build/logs/` (ignored). The ≤300-word return
to the orchestrator lists finding counts by severity and any S0.

---

## 7. C3 — data-truth audit: selecting and tracing numbers

**Selection.**
1. **Census:** every material number in `C2_PAGE_LOG.csv` `numbers_seen`. If C3 runs first, extract from the live HTML with 1 GET per
   page in the §5 sample, strip tags, and match numbers, percentages, dates and version strings. Material means counts, ratios, money,
   event dates, denominators, as-of dates, and ruleset or release ids. Incidental numbers (list ordinals, requirement ids) are listed but not traced.
2. **Full trace** on the must pages: `/`, `/dossier/`, the 8 sampled dossiers (HTML, print and JSON), `/watch/`, `/corrections/`,
   `/evidence/`, `/contribution-back/`, the "How we know this" block on `/`, `/dossier/fl/` and `/corrections/`, and the headings, legends and summaries of the islands.
3. **Seeded samples** for long tables. Coverage: all headline figures plus 20 of 127 metrics. Freshness: 15 of 178 rows. Research queue: header
   plus 10 cards. Map table: header plus 10 rows. Use `python3 -c "import random; random.seed(20260930); …"` over the sorted row ids and record the seed and ids.
   Always add rows that look anomalous: 0, 100 %, numerator equal to denominator, or values that differ across pages.
4. **Leads named in the C3 row block** must be traced: the site-wide "How we know this" block, "a tier sum 6 short" (compare
   `provenance.json` 2,423,194 with `coverage.json` 2,423,200), and the "human-verified holdout" wording.

**Trace sources, in order.** Verify every file's sha256 against the manifest (`717aeb44…`) before use.

| surface | release artifact (bucket `zeta-medley-508121-u7-sig-public`) | recompute from | API cross-check (live spine; expect drift) |
|---|---|---|---|
| landing, dossier index | `web/dossier_index.json`, `web/coverage.json`, `web/analytics/provenance.json` | `sig_graph/jurisdictions.csv` (55 rows) | `/v1/coverage/{scope}` |
| dossier `/dossier/<slug>/` (+ print, `.json`) | `web/dossiers.json`; `/dossier/<slug>.json` | `<compartment>/sites.parquet` grouped by jurisdiction (inspect columns first; `datapackage.json` lists no field schemas) | `/v1/dossier/<slug>` |
| map | `web/tiles/<compartment>-sites.pmtiles` (`web/map.json` is **restricted**, not public) | `<compartment>/sites.parquet` | — |
| network | `web/network.json`, `web/analytics/centrality.json` | `sig_graph/sharing_edges.csv` (632 rows) | `/v1/entity/...` |
| freshness | `web/freshness.json` | `sig_graph/freshness.csv` (178) | — |
| coverage | `web/coverage.json` | `sig_graph/coverage.csv` (127) | `/v1/coverage/{scope}` |
| watch, recommender | `web/watch.json`, `web/analytics/decision_point.json` | — | — |
| evidence | `web/evidence.json` | — | `/v1/evidence/{artifact}/{capture}` |
| corrections | `web/corrections.json` | — | — |
| research queue | `web/analytics/queue_meta.json`, `provenance.json` (do **not** download the 144 MB `research_queue.json`) | — | `/v1/task` |

`match` vocabulary: `exact` · `formatted` (separators or rounding within the stated precision) · `derived-ok` (arithmetic shown
from traced inputs) · `mismatch` · `untraceable` · `api-drift` (the release and the live API differ, which is expected because the API reads the live
spine; classify it, and do not call it a site error unless the page claims to show live data).

**Spine queries** need Cloud SQL access (secret plus proxy) and are **not** authorised by default under P3. Use them only with an explicit
operator go relayed by the orchestrator, and then only as: the `sig_read_public` role, `SET default_transaction_read_only = on`,
SELECT only, and every query text, row count and `date -u` logged in `DATA_TRUTH.md`. Without a go, record `untraceable-without-spine`.

**Outputs.**
- `PD/review/DATA_TRUTH.md`.
- `PD/data/number_trace.csv` with columns
  `n_id,page_url,viewport,displayed_text,displayed_value,displayed_unit_or_denominator,as_of_displayed,source_artifact,
  source_sha256,source_locator,source_value,recompute_method,recomputed_value,api_url,api_value,match,material,spec_ids,
  finding_ref,observed_at`.
- `PD/findings/incoming/C3.csv` (§6.6 schema, `stream=C3`).
- Downloads go under `docs/build/logs/next-phase/C3/`, with `SHA256SUMS`, capped at 150 MB.

---

## 8. C4 — pre-release review of the unreleased Round-10 surfaces (local)

**Scope.** `/releases/`, `/releases/<pub>/`, `/r/<pub>/c/<comp>/{,browse,entity,evidence,jurisdiction}/…`, `/r/<pub>/dossier/<scope>/`,
the `/entity/…` convenience stub, release search (JSON and no-JS HTML), the coordinated workspace islands (`sig.workspace-state/1` URL
state; back/forward), `/research-dossier/` (+ `[slug]` and `.json`), the chain-tip `/dispute/`, and `/intake/new` and `/intake/status`.
Apply H01–H18, P32.24 **T1–T7** verbatim, and P1-T1…T3, P2-T2 and P10-T1 re-aimed at these surfaces.

Label each result with its layer, `fixture-verified` or `staging-verified` (P5), and evidence class `recorded-execution`. The P32.24 corpus is
**synthetic by declaration**. The staging registry's catalog pins as-of **2026-10-19** and `data_release_id sig-2026-10-19-518afbaf`,
both later than `date -u` 2026-09-30. Record that under P2 and do not rely on those dates.

Run from `/Users/stevenvitali/Eleutheria-next-phase`. Every server binds to `127.0.0.1`.

| # | step | command | status |
|---|---|---|---|
| 1 | Release-search API over the synthetic corpus (75 records; `sig_graph` 63 + `osm_physical` 12) | `uv run sig-api serve --host 127.0.0.1 --port 8010 --release-registry docs/build/reports/p32.24-investigation-journey-verification/corpus_registry` then `curl -s 'http://127.0.0.1:8010/v1/releases/p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd/compartments/sig_graph/search?q=deployment&limit=2'` and `…&format=html` | **verified** (C1 run, port 8766: `/health` 200 in-memory; JSON 200 with `indexed_records: 63`; HTML 200) |
| 2 | Release-search API over the P32.25 staging registry (the GATE-G3 candidate: **0 records, 0 compartments**) | `uv run sig-api serve --host 127.0.0.1 --port 8011 --release-registry docs/build/reports/p32.25-accepted-release-verification/staging_registry` | unverified (expect honest empty or 404 answers; there is no top-level `withdrawals.json` in that registry) |
| 3 | Static release trees | `python3 -m http.server 8091 --bind 127.0.0.1 --directory docs/build/reports/p32.25-accepted-release-verification/staging_registry/staged` and `python3 -m http.server 8092 --bind 127.0.0.1 --directory docs/build/reports/p32.24-investigation-journey-verification/corpus_registry/staged` | 8092-style serving **verified** (C1 served the corpus tree for Lighthouse). Caveat: `http.server` does **not** apply the nginx withdrawal map (`staged/conf/withdrawn_routes.conf`; `ops/web/nginx.conf` includes `withdrawn_*.conf`). Judge withdrawn or tombstone routes with `uv run sig-ops release-serve check --registry <registry> --route <route>` (help verified, behaviour unverified) |
| 4 | Research dossiers (reviewed P32.18–P32.20 print HTML) | open `docs/build/reports/p32.18-okc-dossier/okc_dossier.print.html`, `…/p32.19-tulsa-dossier/tulsa_dossier.print.html`, `…/p32.20-san-diego-dossier/san_diego_dossier.print.html` (`file://` or via `http.server`) | files exist (C1); rendering unverified |
| 5 | Chain-tip web app (fixtures mode) | `npm --prefix web ci` → `SIG_RELEASE_SEARCH_BASE=http://127.0.0.1:8010 npm --prefix web run build` → `npm --prefix web run preview -- --host 127.0.0.1 --port 4321` (or `python3 -m http.server 4321 --bind 127.0.0.1 --directory web/dist`) | **unverified** (needs a network install; writes gitignored `web/node_modules`, `web/dist`). Fixtures mode renders `/releases/` from `web/src/lib/releases-fixture.ts` (placeholder publication `p-000…001`), so its search forms point at a publication **neither** local registry holds. Review the page design there and exercise search via step 1 |
| 5b | Export-mode build from the P32.23a candidate | `SIG_DATA_SOURCE=export SIG_EXPORT_DIR=docs/build/reports/p32.23a-release-candidate/candidate_export npm --prefix web run build` | **unverified; expected to fail loudly**: that export's `web/` has no `leverage.json` or `releases.json`, and its manifest lists no `web/tiles/*-sites.pmtiles`. Record the outcome and do not patch around it |
| 6 | Intake receiver (non-operational, as designed) | `uv run sig-ops up --no-static` (Docker: PG18+PostGIS + sqitch deploy; also starts `sig-api serve` on :8000 and the loopback curation service on :8001), then `SIG_INTAKE_ENABLED=1 uv run sig-api serve-intake --host 127.0.0.1 --port 8002 --dsn postgresql://sig:sig@127.0.0.1:5432/sig` | **unverified**. Expected: `GET /intake/new` → 503 `receiver_not_operating`; `GET /intake/status` → 200; `GET /` shows `operational: false` |
| 6b | Optional local operational preview (to review the form markup; **orchestrator OK required**) | Copy `ops/config.toml` to the scratchpad with `[intake] operational = true`, then `SIG_INTAKE_ENABLED=1 SIG_INTAKE_OPERATIONAL=1 SIG_INTAKE_FORM_SECRET="$(openssl rand -hex 32)" SIG_INTAKE_ABUSE_SECRET="$(openssl rand -hex 32)" uv run sig-api serve-intake --host 127.0.0.1 --port 8002 --dsn postgresql://sig:sig@127.0.0.1:5432/sig --ops-config <scratch copy>` | **unverified**. Secrets are generated in the shell and never written to a file (P14/HG-09). Local submissions only, with synthetic text and no personal data |
| 7 | Tear-down | stop the servers; `uv run sig-ops down`; `git status --porcelain` must be empty | — |

Outputs: `PD/review/R10_PREVIEW.md`, `PD/findings/incoming/C4.csv` (§6.6 schema, `stream=C4`), and evidence under `docs/build/logs/next-phase/C4/`.

---

## 9. Severity calibration (§8.2) for this product

Pick the severity by the worst plausible consequence for the design-centre reader or a data subject, using what the live site shows
**now**. If two levels seem plausible, choose the higher and state why.

| sev | meaning (§8.2) | calibrated examples for SIG |
|---|---|---|
| **S0** | Active harm or risk in production now: data loss, exposure, false public claim | A private person's name, account handle or home address is visible anywhere public, **including inside a source identifier, label, file name, task slug, tile property or JSON field** (SIG-PUB-002/003). A plate string, or a per-search row carrying operator ids (SIG-PUB-003a/b). A location published above its tier's precision: a current position for a mobile asset, or any C3/C4 location (SIG-PUB-004, SIG-GEO-008). A named officer with no recorded two-reviewer decision (SIG-PUB-007/008). A displayed figure that contradicts its own release artifact while being presented as fact (§3.1). A share-alike compartment served without its licence or attribution, or merged into a CC-BY artifact (SIG-LIC-004a, SIG-EXPORT-005). An authenticated, write or curation surface reachable publicly. RF or candidate "cameras" shown as known devices (SIG-PUB-011/014) |
| **S1** | Breaks a core user task or the truth of the record | The design-centre task fails: no printable dossier with as-of and permalink on every page (SIG-UI-013), or a jurisdiction cannot be found and the site does not say why (SIG-UI-048). A contested value is shown without its marker (SIG-UI-008). NOT_RESEARCHED is indistinguishable from NO_EVIDENCE_FOUND (SIG-TIME-012). A headline count reads as a census, with no denominator (SIG-METRIC-003/010). A citation or permalink does not resolve or is not pinned (SIG-UI-035). The dispute path is missing, or claims a receiver is operating when it is not (SIG-UI-033, SIG-GOV-001). An island has no working no-JS fallback (SIG-UI-050). A keyboard trap, or core content unreachable by keyboard. Low coverage reads as low density (SIG-UI-018). "Human-verified" wording with no human-completed evidence (P4/P5) |
| **S2** | Degraded quality or debt | A zero-JS page over its 150 KiB budget, or an island over its ceiling, with the page still usable. Slow mobile LCP. Jurisdictions shown as bare or ambiguous codes. Public copy full of internal keys or requirement ids. No sitemap or meta description. A generic 404. An empty state that is honest but unhelpful. Inconsistent labels or navigation. Missing feeds explained nowhere. Demo or fixture strings on low-traffic pages |
| **S3** | Polish | Typos, spacing, alignment, capitalisation, redundant sentences, minor visual inconsistency that meets WCAG AA |

An S0 is reported to the orchestrator at once (§2.7). The orchestrator decides any Track-0-style action; no review row acts on production.

---

## 10. Operator-requested focus (from Q-D1-24 — to be filled by the planning orchestrator)

> **Placeholder.** The planning orchestrator pastes the operator's verbatim answer to Q-D1-24 here, with its `U-nnn` id from
> `feedback/OPERATOR_FEEDBACK.md`. It then maps each request to added personas, tasks, pages or heuristics, using the ids
> `OP-01…`. Requested items run **after** Pass 1 (§6.2), so the persona journeys stay unanchored, unless the operator asks otherwise.
>
> | OP id | operator request (verbatim, `U-nnn`) | added task / page / heuristic | owner row (C2/C3/C4) |
> |---|---|---|---|
> | OP-01 | *(pending D1)* | | |

---

## 11. Blocking unknowns and limits

| id | unknown | effect | mitigation |
|---|---|---|---|
| U1 | Claude in Chrome was not connected at A1 | **blocks C2** | the operator runs `/chrome`; C2 pre-flight confirms (§6.1) |
| U2 | macOS Chrome may not size a window to 390 or 320 CSS px | mobile and reflow fidelity | zoom method plus headless iPhone 14 / 320 px capture; record the actual `innerWidth` |
| U3 | Chrome screenshots are not files; the print dialog is unsafe to drive | evidence files | headless helper (§6.4) is the file of record; verified on `file://` only, first live use in C2 |
| U4 | The web build on the live site is older than the chain tip (inferred `5c064881`) | routing of fixes | `chain_tip=` evidence key (§6.6); C6 checks the source before proposing work |
| U5 | Spine access for C3 | some numbers are traceable only to the release, not the spine | release artifacts plus bulk recompute; spine only with an operator go (§7) |
| U6 | C4 web build (npm install), export-mode build (expected to fail), intake (Docker) not run by C1 | C4 set-up time; possible re-scope | verified: API release search and static trees. Everything else is flagged unverified in §8 |
| U7 | The staging-registry candidate holds 0 records | no real-data record review is possible pre-release | review the synthetic P32.24 corpus and label it synthetic; say so in `R10_PREVIEW.md` |

---

## 12. Provenance of this protocol (C1 execution record)

| time (`date -u`) | action | result |
|---|---|---|
| 16:39:16Z | start; read META_PLAN §1–§11 (not Appendix A), BASELINE.md | — |
| 16:40:13–16:40:19Z | `gcloud storage ls` / `ls -l -r` on the web bucket (read-only) | 289 objects |
| 16:42:52–16:47Z | `gcloud storage cat/cp` of the public `manifest.json`, `web/{dossiers,dossier_index,watch,corrections,evidence,coverage}.json`, `web/analytics/{provenance,decision_point}.json`, `datapackage.json` → session scratchpad | digests match the manifest |
| 16:43:42–16:43:45Z | **18 polite `curl` GETs** (sequential; UA `SIG-planning-C1-route-check/1`) | see the table below |
| 16:49Z | headless helper tested on `file://` (corpus dossier; desktop+print, mobile JS-off, 320 px) | PNG and PDF produced; no network |
| 16:49:45–16:49:47Z | Lighthouse CLI tested on `127.0.0.1:8765` (corpus `/releases/`, local `http.server`) | OK (JSON report); server stopped |
| ≈16:50:01Z | `sig-api serve --release-registry <corpus_registry>` tested on `127.0.0.1:8766` | `/health`, search JSON + HTML 200; process stopped |

Route probes at 2026-09-30T16:43Z: `/dossier/` 200 · `/dossier/unresolved/` 200 · `/dossier/fl/print/` 200 · `/dossier/pt.json`
200 · `/releases/` 404 · `/research-dossier/` 404 · `/evidence/` 200 · `/watch/` 200 · `/sitemap-index.xml` 404 · `/sitemap.xml`
404 · unknown route 404 (146 B) · `/task/` 403 · `/robots.txt` 200 · `/dossier/gb-eng` 301 → slash · `http://` 301 →
`https://surveillancegraph.org:443/` · API `/terms` 200 · `/v1/dossier/fl` 200 · `/openapi.json` 200 (40,263 B).

Side effect: `uv run` materialised a gitignored `.venv/` in the planning worktree (16:41:28Z). No tracked file changed. C1 wrote
only `PD/review/PROTOCOL.md` and `PD/review/ROUTES.csv`.
