# K10 — Per-source detail pages · operator ask U-003.10

Row **K10** of `META_PLAN.md` §6 Stream K (owner D, depends K9, J3). Written 2026-09-30 by Claude Code (Opus 5.5) in the
planning worktree (branch `claude/next-phase-planning`, HEAD `921d2c0c`; cited code byte-identical to chain tip `b051732c`).
Work window (`date -u`): **2026-09-30T21:31:15Z → see footer** (shared with K9). `PD` =
`docs/build/planning/2026-09-30-next-phase`. Companion: `design/K9-sources-table.md` (read it first: §1 ground truth K-1…K-14,
§2 changes C-1…C-12, §3 source definition, §5 freshness, §7 versions). Findings: `findings/incoming/K9K10.csv`.

> **Design only (P3/P10).** Same reads as K9 (no additional production access). Nothing here is `engineered` or
> `live-executed` (P5). Every public sentence quoted is **agent-drafted** and must be confirmed verbatim by the operator
> (META_PLAN §2). **This note extends J3 §4.3–§4.5 (source page, captures, run log); it does not redo them.** J3's field
> table, absence tokens, scrub rules (J4 S-1…S-14), lanes, "view original" table (J3 §5.3) and withdrawal rules (J3 §9)
> stay authoritative except where §2 names a change.

**Operator ask (U-003.10, verbatim):** *"individual sources from the 'data freshness' table should be clickable and the user
should be able to view full details for a particular source, including all the metadata from the data freshness table for
that source and more as well as ingestion history and ideally downloadable links for each ingested file and whatever
else"*.

**Inputs read (beyond K9's).** `research/E1-contradictions.md` E1-05, E1-11; `design/E4-rights-packets.md` §0 (GL-GATE-07
verbatim and coverage vocabulary); `design/E2-governance-options.md` E2-11 row; `db/deploy/rights_decisions.sql:22-37`,
`rights_sources_lineage.sql:12-62`, `ingest_run_completion.sql`, `ingest_run_capture.sql`; `ops/src/ops/run_completion.py:1-80`;
`ops/src/ops/scheduled.py:455-575`; `docs/build/runs/P31.2.md:150-172`; `docs/build/reports/live_runs/` (90 files; one
record's key shape); `connectors/src/connectors/runner.py:506, 574` (`code_commit` default); `camera_registry_targets.toml`
header + keys; `dot_511_targets.toml` keys; findings F-184 (registry says "honor robots.txt"), F-196 (no opt-out register),
F-330 (pathways fixture URLs), F-054/B1 NEW-5 (past-dated rights dates), F-04, F-318.

---

## 0. Summary

**The page.** `/sources/<id>/` for each of the 342 registry sources (gated/refused/withdrawn: J3's registry-only page),
rendered per release into the latest view and the citable snapshot (G3 §5.3), with a JSON twin. **Sections:** (1) header +
at-a-glance (every K9 column for this source) · (2) about · (3) ground truth (homepage, endpoints per S-6, terms + terms
capture, upstream-declared last update) · (4) targets / tenants · (5) licence & redistribution · (6) **rights review record**
(every `rights_decision`, with an honest GL-GATE-07 disclosure) · (7) **collection conduct** (robots outcomes per host
incl. disregard per Q-22b, opt-out status, politeness, crawler identity) · (8) cadence & freshness · (9) **ingestion
history** keyed on the *execution* (time, duration, fetched, parsed, claims considered/inserted/duplicate, rejected by class,
errors, disappearances, code identity, link basis) · (10) **captures** with hashes and per-file downloads where the lane
allows, else "view at source" · (11) **versions & downloads** (K9 §7) · (12) contribution to each dossier (shared artifact
with K5) · (13) entities & claims browse · (14) known issues · (15) **changelog** · (16) corrections, cite, machine twin.

**What K10 adds to J3.** Execution-keyed run history across three stores with an explicit link basis (NEW-4, NEW-5); a
field-by-field **registry publish matrix** (several registry fields are unsafe verbatim: NEW-6) and a real `publisher`
field (NEW-7); GL-GATE-07 disclosure text; targets/tenants; versions; dossier contribution with its **assignment basis**
(per-source today, NEW-8); entity browse; a per-source changelog built from release diffs and append-only records (never
git dates).

**Sizes (largest sources, §16.2).** `escribe` 10 executions / 3,080 capture occurrences → 31 capture pages; `camreg_osm_surveillance`
154,528 published sites (entity browse capped at 1,000; the rest via the slice download, API and K3 search) and ≈ 1.2–1.4 M
statements (inference); `primegov` ≈ 231,885 claims per run. Per release ≈ 1.5k source pages per rendering, ≈ 40–60 MB
(inference); ×2 renderings.

**Tickets (§20):** UX10-1 registry publish matrix + metadata fields (S) · UX10-2 execution-keyed history (M, amends TX-03/TX-04)
· UX10-3 source page (L → a/b, extends TX-05b) · UX10-4 source changelog (S).

**New findings (K10 side):** NEW-4 execution history cannot be keyed on `ingest_run` · NEW-5 12 live sources have no GCS
run row (8 repo-only records, 4 none) · NEW-6 registry free-text fields are unsafe to render and have no publish verdict ·
NEW-7 no publisher field · NEW-8 jurisdiction is assigned per source, never per point.

---

## 1. Ground truth specific to K10

| # | fact | evidence | consequence |
|---|---|---|---|
| P-1 | Three execution stores: (a) 387 GCS run rows (324 without `ingest_run_id`, all started before 2026-09-24T23:49Z; `fetch_record.fetches` on 58); (b) `ingest_run_completion` — 301 backfilled from 324 pre-P31.2 rows (197 sources) + live completions since; 23 rows unmatched with reasons (6 failed with no claims in window, 8 zero-claim / tenant sweeps, 7 connector first run later than the row, 2 overlapping retries); (c) 90 committed `docs/build/reports/live_runs/*.json` records (2026-09-16…19) | recorded-execution; `docs/build/runs/P31.2.md:153-172`; `ls` | one execution table must merge all three and say how each row is linked |
| P-2 | Pre-P31.2, one `ingest_run` row was **reused by key** across executions (20 `ingest_run` rows, all still `running`, at P31.2 read-back); since ADR-111 an execution records `code_commit` = the rolled image digest (`SIG_CODE_COMMIT`) when set, default `"unknown"` | `P31.2.md:170-172`; `ops/src/ops/scheduled.py:528-562`; `connectors/src/connectors/runner.py:506` (code) | `ingest_run.started_at` / `code_commit` describe the shared run, not the execution (NEW-4) |
| P-3 | 12 ingested-live sources have no GCS run row: 8 have only a committed live-run record (`carnegie_ai_gsi`, `ccops_nyc_post`, `ccops_seattle`, `facial_recognition_world_map`, `fbi_cde_agency_registry`, `madada`, `pathways_acoustic_drone_location`, `pathways_rtcc_federation`), 4 have none (`eff_atlas_of_surveillance`, `muckrock`, `osm_element_history`, `state_alpr_statute_inventory`); `ccops_seattle`/`ccops_nyc_post` are registered with access method "connector over committed fixtures" yet scheduled monthly (days 8, 9) | set arithmetic (K9 K-9); `sources.toml` `access_method`; `ops/cadence.toml` (code) | NEW-5; the page must say which record, if any, backs the data |
| P-4 | Largest per-source histories (run rows): `escribe` 10 runs / 3,080 capture occurrences / 1,800 document outcomes / 12 robots disregards; `legistar` 1,908 captures; `civicclerk` 1,880 captures, 335 disappearances, largest row 343,689 B; `camreg_osm_surveillance` 7 runs, 1,369,210 claims emitted in one run; `primegov` 5 runs, 231,885 claims max, 220 robots disregards; 6,144 distinct digests overall | recorded-execution (counts only) | §13 sizes; paging |
| P-5 | Rights: `rights_decision` rows are append-only with `basis` (e.g. "HG-03 2026-09-22 under GL-GATE-07: …"), `reviewer` (**role**, never a name), `review_packet`, `terms_url`, `terms_capture_id`, `decided_at`; registry `rights_reviewed_by` = `maintainer (delegated)` 232, `counsel (HG-02)` 5 (`madada`, `declarationcamera_be`, `carnegie_ai_gsi`, `facial_recognition_world_map`, `aspi_mapping_chinas_tech_giants`; operator-reported, no written opinion, E1-05); `rights_reviewed_on` 2026-09-18 ×176, 09-15 ×19, 09-16 ×18, 09-17 ×9, 09-23 ×8, **09-10 ×6** (past-dated, F-054), 09-22 ×1; 228 rows name a review packet | `rights_decisions.sql:22-33` (code); `tomllib` (code); E1-05, E1-11 | §6 honest wording |
| P-6 | GL-GATE-07 (2026-09-18, verbatim): *"We should ungate the D-SOURCES.12-1 257 gated datasets and for all the 'rights review' cases we should err on the side of approving them"*; execution rule US → `LicenseRef-PublicRecord-FactualCompilation`, non-US → `LicenseRef-OperatorAccepted-DBRight`, reviewer `maintainer (delegated)`; flips beyond the recorded rule exist (`camreg_und_001`, `camreg_calgary_ab`; E1-11); 7 sources' captured terms forbid what SIG publishes (J4 NEW-1) | E4 §0 (quoting LEDGER GATE DECISIONS); E1-11; J4 §4 | §6 |
| P-7 | Robots: registry `robots_policy = "honor"` on 340 rows (incl. `primegov`, `escribe`, `ok_statute`), yet run rows record 234 `robots_disregarded` events on those 3 sources under GL-GATE-08; no per-host opt-out register exists | `tomllib` (code); recorded-execution; F-184, F-196; J4 §8 | never render `robots_policy`; render observed conduct (§7) |
| P-8 | Registry free text: `notes` cite internal ticket ids on 239 rows, internal paths on 13, email-like strings on 4; `access_method` names committed fixture paths; `auth_model` names environment variables on 3 rows; `eyes_on_flock` has a `contact` field holding an email address; no field-level publish verdict exists (J4 §8 covers logs only) | pattern counts over `sources.toml` (values not copied) (code) | NEW-6; §4 matrix |
| P-9 | Targets: 223 camera-registry endpoints (173 sources) and 14 DOT endpoints (13 sources) each carry `agency`, `url`/`layer_url`, `state`, `observed_count`, `verified`; 793 agenda tenants under 4 platform sources; 158 OSM slices | `camera_registry_targets.toml`, `dot_511_targets.toml` (code); I1 | §3 targets section; `agency` seeds the publisher field |
| P-10 | Dossier contribution today: every site source maps to exactly one jurisdiction (178 pairs); 58 sources (166,210 rows, 70.1 %) map wholly to `unresolved` because `camera_jurisdiction` is the target's configured `state` | K9 K-13 | NEW-8; §12 shows the basis |

---

## 2. Changes to J3's design (explicit; continues K9's C-1…C-12)

| # | J3 location | J3 says | K10 changes it to | why |
|---|---|---|---|---|
| C-13 | §4.5 run log, "started" | `ingest_run.started_at` | the **execution** is the row: started = run-row `started_at` (else completion `finished_at − duration`); code identity = `ingest_run.code_commit` only when the execution owns its run; otherwise `not_recorded (shared run)` | P-2, NEW-4 |
| C-14 | §3.3 item 1 (`ingest_run_report` backfill "keyed by `backfilled_from`") | one report row per WORM row | report rows also for **unmatched** executions (`run_id` NULL + `link_basis = unmatched:<reason>`, reusing P31.2's matcher verdicts) and for the 90 **repo live-run records** (`link_basis = repo_record`, `clock = git_only`) | P-1, P-3, NEW-5 |
| C-15 | §4.3 Identity: description from `notes` first paragraph | notes-derived text | `notes` is **never** rendered; the description is separate operator-approved text (D-J3-12); a field publish matrix governs every registry field (§4) | P-8, NEW-6 |
| C-16 | §4.3 Identity: publisher | from registry `name`/`notes` | new registry `publisher` field (+ `publisher_type`), seeded from target `agency` strings and I1's typing | P-9, NEW-7 |
| C-17 | §4.3 Rights-review record | basis, gate, role, decided_at, counsel status | + a standard **GL-GATE-07 disclosure**, out-of-rule and terms-conflict flags, the counsel caveat, and date-correction notes (§6) | P-5, P-6 |
| C-18 | §4.3 Collection conduct | robots outcome per host | same, plus: the registry's `robots_policy` is never shown; a mismatch note where the registry says "honor" and runs disregarded | P-7, F-184 |
| C-19 | §4.3 (none) | — | new **Targets / tenants** section | P-9 |
| C-20 | §4.3 Downloads | "this source's derived slice(s), statements rows, raw captures" | the K9 §7 **versions** model (per-release slices, capture versions, version index) | K9 C-8, §7 |
| C-21 | §4.3 Contribution to dossiers | subjects/observations per dossier | + the **assignment basis** (`declared by source` vs `located by point`) and `unresolved` shown as a data-quality bucket; one artifact shared with K5 | P-10, NEW-8 |
| C-22 | §4.3 Sample records | ≤10 samples | samples stay; plus a capped **entity browse** and a claims route to the statements slice / API / K3 search | operator "whatever else" |
| C-23 | §4.3 Corrections | corrections list | + a generated **changelog** (§15) | operator ask; J2 PC-5 |

Unchanged from J3: `…/runs/` and `…/captures/` sub-pages (100 rows/page, `<details>` per run), registry-only pages for
gated/refused/unknown-lane sources (J4 S-11), sample-record rules, view-original table, JSON twin, cite block.

---

## 3. Page map

| route | content | paging | notes |
|---|---|---|---|
| `/sources/<id>/` | sections 1–16 with the latest 20 executions, latest 20 captures, versions summary, dossier table (≤20 rows inline), 10 samples, open issues, last 10 changelog events | — | ≤150 KiB, 0 scripts |
| `/sources/<id>/runs/` | every execution | 100 | per-run `<details>`: errors by class, robots by host, disappearances, document outcomes by class, code identity |
| `/sources/<id>/captures/` | every capture occurrence | 100 | sorted target, then time desc |
| `/sources/<id>/captures/changes/` | only captures whose records digest (or upstream-declared date) changed — the raw "versions" | 100 | Transitland-style list (J2 §2.5) |
| `/sources/<id>/versions/` | per-release derived versions + links to capture versions | — | K9 §7.2 |
| `/sources/<id>/targets/` | targets/tenants when > 20 | 100 | multi-target sources only |
| `/sources/<id>/entities/` | published entities (label, type, jurisdiction, record link) | 100, **capped at 10 pages** | cap disclosed; rest via download/API/K3 |
| `/sources/<id>/dossiers/` | contribution table when > 20 rows | — | shared artifact with K5 |
| `/sources/<id>/changelog/` | all events when > 10 | 100 | — |
| `/sources/<id>/index.json` (+ sub-JSON per route) | machine twins, linked `rel="alternate"` | — | `sig.source-page/2` etc. (§13) |
| `/status/sources/<id>/` | executions since the release, next run (day), current verdict | — | status lane, labelled status clock, not citable |

---

## 4. Registry field publish matrix (NEW-6 fix; applies to every page, file and API route)

P = publish as is · T = publish after the named transform · N = never. Enforced by a registry lint in CI and by the J3
publish scrub (T-6); unknown new fields default to **N** (fail closed).

| field | verdict | rule / rendering |
|---|---|---|
| `source_id` | P | post-ACT-06 renamed ids only; old ids 301 |
| `name` | P | — |
| `source_kind` | T | plain-language label ("government portal", "upstream project", …) |
| `homepage_url` | T | S-1 then show; host always visible |
| `default_tier` (R1–R6) | T | shown as "SIG reliability class" with its `reliability_justification`, after operator review of the justification texts (D-K10-4) |
| `custody_posture` | T | plain-language gloss: MIRROR "SIG keeps a copy", REFERENCE "SIG reads and derives facts", LINK "SIG links only", DERIVE "SIG publishes derived facts only" |
| `compact_status` | T | "publisher not contacted" / "public terms only" / "no response" |
| `robots_policy` | **N** | contradicted by conduct (F-184); §7 renders observed outcomes instead |
| `notes` | **N** | internal ticket ids, paths, email-like strings (P-8); the public description is separate approved text |
| `access_method` | T | closed vocabulary only: `api` · `bulk_file` · `html` · `pdf` · `arcgis` · `socrata` · `ckan` · `document_index`; never paths |
| `auth_model` | T | `none` · `api_key` · `login` · `session`; never variable names |
| `contact` | **N** | may be a person's address (P-8) |
| `rate_limits` | T | the publisher's documented limit only (e.g. "5,000 requests/hour"), never observed failure notes |
| `cadence` | T | fallback only, labelled "registry, not scheduled" (K9 §5.5) |
| `last_verified`, `verified` | P | date + "endpoint verified by SIG"; B1 clock caveat where applicable |
| `ingestion_permitted` | T | part of the rights record (§6), never a bare boolean |
| `rights_reviewed_by` | T | role only (already roles today) |
| `rights_reviewed_on` | T | shown with the B1 correction note where the date is past-dated (the 6 `2026-09-10` rows, F-054) |
| `review_packet` | T | per D-J3-13: packet link only if the packet text is approved for publication; else "review packet held privately" |
| `[rights].spdx`, `attribution`, `redistributable`, `derivative_permitted`, `terms_url`, `retrieval_date` | P / T | attribution text is the **only** attribution source (J3 T-4); `terms_url` through S-1 |
| `[redistribution]` (new, TX-02) | P | lane + basis + reviewed date + decision ref |
| `publisher`, `publisher_type`, `one_time_load`, `description` (new) | P | operator-confirmed in batches (D-J3-12) |
| target fields (`agency`, `url`, `layer_url`, `state`, `observed_count`, `verified`, `platform`) | P / T | URLs through S-1/S-6; `notes` N; `excluded_fields` N |

---

## 5. Header, about, ground truth, targets, licence

- **Header:** name; `source_id`; publisher (linked to its K2 entity page when `source_registry.operator_org_id` is set);
  status chip (K9 §3.2 state + flags); freshness chip (verdict at the release as-of, K9 §5.1); release stamp "as of release
  `<label>` (data as of `<as_of_world>`)"; link "runs since this release →" (status lane).
- **At a glance:** the source's K9 row, all 17 columns, as a definition list (same `<Figure>` pointers into `sources.json`,
  J3 §5.4).
- **About:** approved description (else `description_pending_review`); kind; publisher type; technology classes; geography
  (declared); coverage window = earliest/latest `observed_at` of published claims (`not_dated` when none); volatility
  distribution (K9 §5.2) as a small table.
- **Ground truth:** homepage; upstream endpoints (full URL per S-6 only when lane ∈ {raw-ok, derived-only} and the
  document/record passed the gate, else host + path hash); terms URL + "terms as captured on `<retrieved_at>`, sha256 `<…>`"
  (from `rights_decision.terms_capture_id`; `terms_not_captured` otherwise; bytes link-out only); **upstream last updated**
  (declared by the publisher, K9 §5.4) per target.
- **Targets / tenants:** for multi-target sources, one row per target: target label (agency / tenant / slice), host,
  declared jurisdiction, observed count at enumeration, last capture time, last change, state (`active` · `disappeared` ·
  `enumerated, not fetched`). For agenda platforms the tenant list (≤ 793 rows across 4 sources) is paged.
- **Licence & redistribution:** upstream SPDX verbatim + ≤ 25-word terms excerpt (quoted, linked), SIG basis with the
  "facts only, not a licence from the publisher" gloss, share-alike, required attribution text (registry), **attribution
  status** from the PKG-08 gate ("the files in this release credit this source correctly" / "… do not yet; fix pending"),
  derived status, raw lane + reason class (J4 §2).

---

## 6. Rights review record (honest about delegated flips)

**Rows:** every `rights_decision` for the source, oldest first (append-only): decided_at (UTC), basis (verbatim gate
reference), reviewer **role**, terms reviewed (URL + capture date/digest), packet (per D-J3-13), and — derived — the
**coverage class** from E4's vocabulary (`EXECUTED` under GL-GATE-07 · `PRECEDENT` · `OUTSIDE THE RECORDED RULE` · `per-source
review` · `counsel (operator-reported)`). Where `rights_decision` rows are missing on the spine for a registry-flipped source,
the page shows the registry fields with `recorded_in_registry_only`.

**Standard disclosure texts (agent-drafted; the operator confirms each verbatim, D-K10-1):**

| case | text |
|---|---|
| GL-GATE-07 flip (≈ 176 rows dated 2026-09-18, plus P27.2/P29.3 re-applications) | *"Approved for ingestion on `<date>` under a standing instruction from SIG's operator (GL-GATE-07, 2026-09-18) to "err on the side of approving" sources awaiting rights review. A maintainer applied it under delegation. No per-source legal review and no counsel opinion is recorded for this source. SIG publishes facts from it on the basis `<SIG basis>`, which is SIG's own basis, not a licence from the publisher."* |
| outside the recorded rule (E1-11: e.g. `camreg_und_001` "unresolved jurisdiction", `camreg_calgary_ab` "terms not captured") | adds: *"This approval went beyond the rule as recorded (`<reason class>`). A fresh decision is pending."* |
| captured terms conflict (J4 NEW-1: 7 sources) | adds: *"The publisher's captured terms say: "`<≤25-word excerpt>`". SIG has `<withdrawn this source's data | not yet withdrawn this source's data>` pending a new rights review."* |
| `counsel (HG-02)` (5 sources) | *"Reviewer recorded as counsel. This was reported by SIG's operator; no written counsel opinion is on file (E1-05)."* |
| GL-GATE-06 / per-source HG-03 / federal-work rows | *"Approved on `<date>` after review of the publisher's licence (`<SPDX>`)."* |
| past-dated registry date (F-054) | *"The registry dates this review `<recorded date>`; the change was made on `<executed date>` (correction recorded `<ref>`)."* |
| gated / refused | *"Not yet approved: waiting for a rights review."* / *"SIG decided not to ingest this source: `<reason class>`."* |

Nothing names a person (Part VIII §0.7; J3 T-11). The texts sit in `ops/disclosures.toml` (G3 §3.2 disclosures block), so
the release descriptor hashes the exact approved wording and V13 checks it renders.

---

## 7. Collection conduct

| item | source | rendering |
|---|---|---|
| robots per host | run rows `robots_decisions[]` + `robots_disregarded[]` → `ingest_run_report.robots_outcomes` (J3 §3.3) | per host: obeyed / disallowed / unavailable / **disregarded** counts over all executions and in the latest one |
| disregard disclosure (Q-22b, D-J3-2 pending) | same | if D-J3-2 = yes: *"SIG fetched `<n>` pages on `<host>` that the site's robots.txt disallows, under SIG's crawler policy GL-GATE-08 (`<policy link>`)."* (agent-drafted); if no: *"Robots outcomes for this source are not published (operator decision `<ref>`)."* — never silent |
| registry mismatch | registry `robots_policy` vs observed | where the registry says "honor" and runs disregarded (today `primegov` 220, `escribe` 12, `ok_statute` 2): *"SIG's registry states that SIG honours robots.txt for this source; the run records above show otherwise. Correction pending (F-184)."* until F-184's owner fixes the registry |
| opt-out | E2's opt-out register (F-196) | `no_opt_out_register_yet` until it exists; then status + date of any request (no requester identity) |
| politeness & limits | refusals by class, rate-limit events, quota/budget reached | counts per class and host (S-4, S-6) |
| crawler identity | project UA string (Q-30 contact) | the project's string, never a person's (P16) |
| access | `access_method` / `auth_model` vocabularies (§4) | "API, no login" etc. |

---

## 8. Cadence & freshness

As K9 §5 for this source, plus: observed cadence (median interval of the last 5 successful executions), a pre-rendered
**inline SVG** "runs over time" strip (x = time, bar = claims inserted, colour = outcome; zero JS, `<title>`/`<desc>` and
the runs table as its text equivalent, SIG-UI-037), staleness detail by predicate (evaluable / not evaluable), and the
status-lane link. No "next run" on the release page (K9 C-4).

---

## 9. Ingestion history (execution-keyed)

**Row = one execution.** Merge key: completion `completion_id` when present; else run-row object name; else repo record
path. **Columns** (J3 §4.5 metrics, re-sourced):

| column | source (priority order) | absence |
|---|---|---|
| started (UTC) | run-row `started_at`; completion `finished_at − duration`; repo record `started_at` | `not_recorded` |
| finished / duration | completion `finished_at`; run row `started_at + duration_seconds` | `no completion recorded (execution may have been killed)` |
| outcome | completion `status`; run-row `outcome` mapped (`error`/`content_drift`/`politeness_refusal` → failed) | — |
| mode | run-row `mode` (`live` / `replay`) + `kind` (`scheduled-ingest`, `p265-tenant-sweep`, `replay-ingest`) | — |
| fetched | report `fetches`; per-fetch status/bytes when PKG-12 fills them | `not_recorded` (329 of 387 rows today) |
| parsed | report `records_emitted` / Σ flushed `records` | `not_recorded` |
| claims considered / inserted / duplicate | completion columns | backfilled: considered/duplicate `not_recorded`; **never** run-row `claims_added` (emitted, incl. duplicates; K9 K-12) |
| rejected | `assertion_quarantine` counts by reason class | `0` only when measured |
| errors | S-4 class + count; refusal classes | — |
| disappearances | count (+ tombstone ids, S-9) | — |
| robots | per-host outcome counts (→ §7) | — |
| captures | count + link to the execution's rows in `…/captures/` | — |
| code identity | connector name + version; `ingest_run.code_commit` (image digest, ADR-111) when the execution owns its run; commit hash per D-J3-3 | `not_recorded (shared run)` pre-P31.2; `not_recorded` when `"unknown"` |
| link basis | `live` · `backfill: claims in window` · `backfill: sole candidate` · `unmatched: <reason>` · `repo record (clock: git only)` | — |

**Sources with no execution record** (P-3: 4 today) show a single row: *"SIG holds data from this source, but no record of
the run that loaded it exists. Loaded before `<first claim recorded_at>`."* (agent-drafted) and the `run_record_missing`
flag (K9 C-7). **Silent success** rows (0 records, outcome ok) get the `zero_records` issue (J3 §7.3).

---

## 10. Captures and per-file downloads

J3 §4.4 columns (retrieved_at full ISO, digest, bytes, media type, classification, bytes available, target host) plus:
**change kind** (`records changed` · `formatting change only` · `unchanged` · `first capture`; K9 §5.4), **target**
(label + host), **records** (flushed count), and the **file action** from J3 §5.3's decision table:

| condition | action shown |
|---|---|
| lane `raw-ok`, P8 clear, bytes retained, custody not `REFERENCE` without a posture change (SIG-ONTO-007) | **Download** (`raw/<multihash>` on the mirror; size, sha256) |
| lane `raw-ok`, P8-5/6/8 | **Download redacted copy** (a new capture, method + version) once TX-12 produces it; before that `redaction_pending` |
| lane `raw-ok`, bytes not retained (across all lanes, 5,795 of 6,144 recorded digests have no retained bytes today, J4 NEW-5) | **View at source** + "SIG did not retain these bytes" |
| `derived-only` / `link-only` | **View at source** (URL per S-6) + hash, size, time |
| `restricted` | "Not redistributable — `<reason class>`"; hash + date only; no URL where it could name a person |
| synthetic run-level capture | "Run-level record, not a copy of the source (0 bytes)" |

Today at most ≈ 35 raw-ok sources have downloadable bytes (J4). Every download link waits for TX-11 (mirror) and TX-12
(raw archive); until then the column shows `download_host_pending`.

---

## 11. Versions & downloads

The K9 §7.2 model rendered for one source: (a) **latest released extract** (sites and/or statements; csv.gz + parquet;
size, rows, sha256; `ATTRIBUTION.txt`, `datapackage.json`); (b) **release versions** table (label, as-of, rows, claims,
changed?, added/removed/changed, files); pre-Round-11 releases as manifest-only rows (D-K9-2); (c) **capture versions**
(the `captures/changes/` list; downloads per §10); (d) API equivalents (`/v1/releases/{pub}/sources/{id}` + JSON paths).
Latest ≠ latest run (K9 §7.2 wording).

---

## 12. Contribution to each dossier (interface with K5)

One exporter artifact, owned jointly with K5: `r/<pub>/transparency/contributions.jsonl` (`sig.source-dossier-contribution/1`),
one row per (source, jurisdiction key): `source_id, jurisdiction_key, subjects, claims, share_of_dossier_subjects,
share_of_source_subjects, first_observed, last_observed, first_run, last_run, executions, basis` where `basis` ∈
`declared_by_source` (today: `camera_jurisdiction` = the target's configured `state`) · `located_by_point` (after PKG-06b adds
point-in-polygon assignment) · `document_scope` (agenda tenant, statute, CCOPS city). The source page renders its rows
(linking each to the dossier); the dossier page (K5) renders the same rows filtered by jurisdiction, so the two numbers are
**equal by construction** (J3 D08). Rows with `unresolved` link to K4's data-quality bucket and say *"SIG could not place
these records in a jurisdiction."* Today the table has exactly one row per site source (178 rows total; 58 of them
`unresolved`, 166,210 subjects) — the page must not imply per-place coverage it lacks (NEW-8). Size: ≤ a few thousand rows
after PKG-06b (inference).

---

## 13. Entities & claims browse

- **Entities:** published entities from the source, ordered jurisdiction → label → record key, 100 per page, **10 pages
  maximum** (1,000 rows), each linking to its `/r/<pub>/c/<comp>/entity/<id>/` record; the page states the total and the
  cap and links the full slice, the API and K3 search with a `source:` facet. Median site source (137 rows) needs 2 pages;
  the OSM-derived layer (154,528) hits the cap.
- **By predicate:** claims by predicate with counts, volatility class and directness (small table, all rows).
- **Samples:** J3's ≤ 10 deterministic samples (non-site sources: sample claims, never document titles for P8-2/P8-3
  genres).
- **Claims:** no per-claim pages (J3 G-10); the per-source `statements` slice (K9 C-8) and `/v1/claim/{id}` via the record
  provenance panel (J3 §5).
- Withdrawal: entity-browse pages are listed in `s/<pub>/page_index.json` with their embedded entity ids (J3 §8.1); a
  withdrawn entity turns that browse page into a 410 tombstone naming the next release (rare; accepted cost).

---

## 14. Known issues

J3 §7.3 unchanged (auto-detected classes + curated `known_issues.toml`), plus K10 auto-classes: `run_record_missing`,
`registry_conduct_mismatch` (F-184), `rights_outside_recorded_rule` (E1-11), `terms_conflict` (J4 NEW-1),
`attribution_failing` (PKG-08), `formatting_churn` (digest changes without record changes on ≥ 3 consecutive runs),
`jurisdiction_unresolved`.

---

## 15. Changelog (per source)

Generated, append-only, from records with trustworthy clocks — **never** from git commit dates (B1: past-dated commits
exist). Events and their source of truth:

| event | source | date used |
|---|---|---|
| rights decision (approve/refuse/lane change) | `rights_decision` | `decided_at` |
| first ingest; first publication; withdrawal; re-publication | completions; release catalog; `withdrawals.json` | `finished_at`; activation time |
| registry change visible in the release (name, publisher, lane, cadence, id rename) | diff of consecutive releases' `sources.json` rows | release activation |
| connector version change | `ingest_run.connector_version` change between executions | first execution with the new version |
| records changed in a release (added/removed/changed counts) | per-source slice of TX-14's diff | release activation |
| issue opened/closed | `issues.jsonl` | `opened_at`/`closed_at` |
| correction affecting the source | corrections log | its recorded time |

The first activated release is the baseline: *"History before `<label>`: rights decisions and run records only."*
(agent-drafted). Schema `sig.source-changelog/1`: `{event_id, source_id, kind, at, clock_basis, summary_code, refs[]}` —
summaries are rendered from codes, never free text.

---

## 16. Data contracts, sizes and generation per release

### 16.1 Contracts (all under `r/<pub>/transparency/sources/<id>/`, CC-BY-4.0 SIG metadata; J3 §3.2)

| file | schema | content |
|---|---|---|
| `index.json` | `sig.source-page/2` (J3's /1 + sections 4–15 summaries) | registry public fields (§4), rights rows, conduct summary, cadence, K9 row, latest 20 executions, latest 20 captures, versions summary, dossier rows (≤ 20), samples, open issues, last 10 changelog events, links to the files below |
| `executions.jsonl` | `sig.execution-record/1` (J3 `sig.run-record/1` renamed + `execution_key`, `link_basis`, `code_identity`, `clock_basis`) | every execution (§9) |
| `captures.jsonl` | `sig.capture-record/2` (+ `target_key_hash`, `records_digest`, `change_kind`, `file_action`) | every capture occurrence (§10) |
| `versions.json` | `sig.source-versions/1` (K9) | release + capture versions |
| `entities/<n>.json` | `sig.source-entities/1` | ≤ 10 pages × 100 |
| `targets.json` | `sig.source-targets/1` | targets/tenants |
| `changelog.json` | `sig.source-changelog/1` | §15 |
| `contributions.jsonl` (release-level) | `sig.source-dossier-contribution/1` | §12, shared with K5 |

### 16.2 Sizes (inference from P-4 and J3/J4 unit sizes; UX10-3 measures)

| source | executions | capture rows | entity rows | JSON (all files) | HTML pages |
|---|---|---|---|---|---|
| `escribe` (largest capture history) | 10 | 3,080 | non-site (samples + by-predicate) | ≈ 0.9 MB | main + 1 runs + 31 captures + ≈ 5 changes + versions ≈ 40 |
| `legistar` / `civicclerk` | 4 / 5 | 1,908 / 1,880 | non-site | ≈ 0.6 MB each | ≈ 25 each |
| `camreg_osm_surveillance` (largest data) | 7 | ≈ 1,106 (158 targets × 7) | 154,528 → 1,000 shown | ≈ 0.5 MB | main + 12 captures + 10 entities + 2 targets + versions ≈ 27 |
| `primegov` (largest claims/run) | 5 | ≈ 134 digests (J4) | non-site | ≈ 0.1 MB | ≈ 6 |
| median site source | 1–3 | 1–3 | 137 | ≈ 15 KB | ≈ 6 |
| gated / refused (105) | — | — | — | ≈ 2 KB | 1 |

Downloads for the largest source (inference): OSM-derived `sites.csv.gz` ≈ 15–25 MB, `statements.csv.gz` ≈ 30–50 MB
(≈ 1.2–1.4 M claims), parquet similar; split by country/subdivision above 250 MB (J3 §6.3). **Totals per release:** ≈ 1.5k
source pages per rendering (342 main + ≈ 1.2k sub-pages), ≈ 40–60 MB HTML; ≈ 3k pages / 80–120 MB for latest + snapshot;
source JSON ≈ 10–20 MB (inside J3's 15–30 MB transparency estimate). Growth: +1 execution per scheduled source per month
(+≈ 470 executions/month, J3) → capture pages grow ~linearly; `escribe`-class sources gain ≈ 3 capture pages per run.

### 16.3 Generation per release (G3)

1. `cut` → export (one REPEATABLE READ snapshot): J3 views + an execution view that unions completions, report rows
   (incl. unmatched and repo-record rows, C-14) and run-row metadata imported by `ingest_run_report`; computes everything
   above; scrubs (J3 T-6; registry lint §4); writes `transparency/sources/<id>/…` + `contributions.jsonl`. These files are
   inside `transparency_root`, so they are part of the descriptor v2 hash (J3 §3.4, G3 §3.2).
2. `build` → Astro renders `/sources/<id>/**` into `v/<pub>/` (latest view) and `s/<pub>/` (snapshot, after G3 NEW-6's
   `withBase` refactor; until then the J3 §8.1 fallback wording); emits `page_index.json` entries for every page that
   embeds an entity, capture or claim id.
3. `verify` (G3 V1–V14): budgets, links, parity (HTML = JSON = API `/v1/releases/{pub}/sources/{id}…`), scrub + registry
   lint, disclosure texts render (V13).
4. `promote` → metadata-only (G3). The **status lane** separately renders `/status/sources/<id>/` every 6 h (J3 TX-07) from
   executions after the release's belief cut.
5. **Withdrawal:** J3 §9.2 table; a source withdrawal collapses runs/captures to counts, keeps the page, and states the
   reason and date.

---

## 17. JavaScript: baseline and enhancement

**No-JS baseline (mandatory, SIG-UI-037):** every section is static HTML; tables paged at 100 with links; `<details>` per
execution; the runs-over-time strip is pre-rendered SVG with a table equivalent; entity browse via pages; search via K3's
page and the per-source slice. **Enhanced (K0-dependent):** in-place sort/filter on the runs and captures tables (by outcome,
target, change kind), a zoomable timeline built from `executions.jsonl`, an entity search box scoped to the source (K3 index
with a `source:` facet), lazy loading of later capture pages, and a local-map preview of the source's sites (K1 component,
behind its no-JS tabular fallback). Under K0 option (a) none of these ship on `/sources/<id>/` (the K1/K3 islands are linked
instead); under (b) one shared enhancement module (≤ 15 KiB gz, with K9's) applies; under (c) the page is also reachable
inside the app shell, with this static page canonical and citable.

---

## 18. Draft requirements (continuing SIG-TRANSP)

| id | requirement (draft) | AC |
|---|---|---|
| SIG-TRANSP-D35 | Every registry field MUST carry a publish verdict (publish / transform / never); fields without a verdict MUST NOT be published, and free-text registry notes, contact fields, credential variable names and internal paths MUST never reach a public artifact. | registry lint fails on a field with no verdict; planted email/path/`$VAR` in `notes` never appears in output (test) |
| SIG-TRANSP-D36 | A source page's ingestion history MUST have one row per execution across every execution store, each with its link basis and clock basis; values that describe a shared run MUST NOT be presented as the execution's. | rows = completions ∪ unmatched run rows ∪ repo records (reconcile test); pre-P31.2 rows show `not_recorded (shared run)` for code identity |
| SIG-TRANSP-D37 | A source whose published data has no execution record MUST say so on its page and in the table. | the 4 P-3 sources render `run_record_missing` (fixture test + crawl) |
| SIG-TRANSP-D38 | The rights review record MUST list every rights decision with basis, gate, reviewer role and date, and MUST state plainly when an approval came from a standing delegated rule rather than a per-source review, when it went beyond the recorded rule, when captured terms conflict, and when a counsel review is operator-reported without a written opinion. | every GL-GATE-07 row renders the approved disclosure (V13); E1-11 rows carry the outside-rule text; the 5 counsel rows carry the caveat |
| SIG-TRANSP-D39 | Collection conduct MUST be rendered from observed run records (robots outcomes per host, refusals, rate limits) and never from the registry's declared robots policy; a disclosure decision to withhold robots outcomes MUST itself be stated. | no `robots_policy` value in output; `primegov` page shows 220 disregarded (if D-J3-2 yes) or the withheld statement |
| SIG-TRANSP-D40 | A source's contribution to each dossier MUST come from one artifact shared with the dossier page and MUST state how records were assigned to the jurisdiction. | source↔dossier numbers equal (test); every row has `basis` |
| SIG-TRANSP-D41 | Each capture row MUST state its change kind and the file action allowed by the lane × Part VIII × bytes-stored table; download links MUST exist only for raw-ok, screened, retained bytes. | matrix test (J3 D12) + `formatting_change_only` fixture |
| SIG-TRANSP-D42 | Each source MUST have a changelog generated from append-only records and release diffs, dated by those records' clocks, never by version-control dates. | changelog events all carry `clock_basis` ∈ {decided_at, finished_at, activation, opened_at}; none from git |
| SIG-TRANSP-D43 | Source pages MUST list published entities (capped, with the total and the cap stated) and link to the full per-source data. | cap text present when total > 1,000; slice link resolves |

Amendments to J3 drafts: **D03** gains §4's matrix reference; **D06** is re-keyed by D36; **D09** gains D38/D39's texts.

---

## 19. Acceptance tests (K10)

| id | test | layer |
|---|---|---|
| AT-K10-01 | Fixture spine with: a pre-P31.2 execution on a shared run, a live execution, an unmatched run row, a repo record, and a source with data but no record → the runs table shows 5 rows with the right link bases, code identity `not_recorded (shared run)` on the first, `run_record_missing` on the last | unit + e2e |
| AT-K10-02 | Registry lint: planted `notes` email, `auth_model` `$VAR`, `access_method` path, `contact` → none appears in any HTML/JSON/API output; lint fails on a new unclassified field | CI |
| AT-K10-03 | Rights: a GL-GATE-07 row, an out-of-rule row, a terms-conflict row, a counsel row and a gated row each render the approved disclosure text byte-for-byte (`ops/disclosures.toml` sha256) | CI (V13) |
| AT-K10-04 | Conduct: fixture with registry `robots_policy = "honor"` and 3 disregard events → page shows 3 disregarded on the host + the mismatch note; with D-J3-2 = no → the withheld statement | unit |
| AT-K10-05 | Captures: one fixture row per J3 §5.3 cell + a formatting-only change → actions and change kinds as §10; no download link for any non-raw-ok row | unit |
| AT-K10-06 | Contribution: dossier page (K5) and source page show identical counts for every (source, jurisdiction) pair in the fixture; `unresolved` rows link to K4's bucket | e2e |
| AT-K10-07 | Entity browse: a 1,500-entity fixture renders 10 pages + cap text + slice link; a withdrawn entity turns its page into a 410 tombstone (edge probe after activation) | e2e / probe |
| AT-K10-08 | Changelog: two fixture releases with a lane change, a rights decision and an issue close → 3 events with correct `clock_basis`; no event dated from git | unit |
| AT-K10-09 | Budgets: Lighthouse on `/sources/<osm>/`, `/sources/<escribe>/captures/`, `/sources/<id>/runs/`: 0 scripts, ≤ 150 KiB, perf ≥ 0.9, a11y 1.0 | CI |
| AT-K10-10 | Parity: `index.json` = HTML = `/v1/releases/{pub}/sources/{id}` for 20 sampled sources | CI |
| AT-K10-11 | Journeys (agent walkthrough, not user research, P4): journalist "who approved this source and on what basis?" answered on the page in 1 click; advocate "when did SIG last check this city's cameras and did anything change?" in ≤ 2 clicks | journey |

---

## 20. Round-11 ticket outline (K10)

| key | title | size | scope | depends | live / gate |
|---|---|---|---|---|---|
| UX10-1 | Registry publish matrix + metadata fields | S | field verdict table as code + CI lint; `publisher`, `publisher_type`, `one_time_load`, `description` fields; vocabularies for `access_method`/`auth_model`; seed publisher from target `agency` + I1; batch files for operator approval | D-J3-12 (batches), ACT-06 (renames); F-184's owner for the registry robots text | — |
| UX10-2 | Execution-keyed history | M | execution view; `ingest_run_report` allows `run_id NULL` + `link_basis` + `clock_basis`; import P31.2 unmatched verdicts and the 90 repo records; code-identity rule; `executions.jsonl` | TX-04 (**amends**), TX-03 (**amends**), PKG-12 | hosted DB write (backfill) — op go |
| UX10-3a | Source page, part A | M | header, at-a-glance, about, ground truth, targets, licence, rights record + disclosures, conduct, cadence/freshness + SVG strip | UX10-1, UX9-1, UX9-2, TX-01/02; D-K10-1 texts; **extends TX-05b** | republish — op go |
| UX10-3b | Source page, part B | M | runs, captures (+ changes list, file actions), versions, dossier contribution (shared artifact with K5), entity browse, issues, JSON twins, page_index entries | UX10-2, UX9-4, TX-06, TX-08b (view original), TX-12 (raw), K5 ticket (shared artifact), PKG-06b (basis `located_by_point`) | republish — op go |
| UX10-4 | Source changelog | S | event generator from `rights_decision`, completions, release diffs, issues, corrections; baseline wording | TX-14 (diffs), UX9-1 (`sources.json` per release) | via release |

**Order:** UX10-1 → UX10-2 → UX10-3a (can ship in the transparency MVP republish with K9's UX9-3) → UX10-3b (after TX-11/TX-12
for downloads; renders `download_host_pending` before) → UX10-4 (after the second activated release). Acceptance and the
HG-11 readout fold into J3's TX-16 with AT-K9/AT-K10 added.

**Exactly-one ownership (P9 proposals for S1):** TX-05a's index → UX9-3; TX-05b's page → UX10-3a/b; J3 §4.1 funnel → UX9-1;
TX-03's freshness function → UX9-2; TX-04's report table shape → UX10-2; dossier-side rendering of contributions → K5;
point-level jurisdiction assignment → PKG-06b; registry robots wording → F-184's owner (E stream).

---

## 21. Operator decisions

| id | question | recommendation |
|---|---|---|
| D-K10-1 | Approve the §6 disclosure texts verbatim (GL-GATE-07, outside-rule, terms-conflict, counsel caveat, date correction, gated/refused) | Approve or edit; they ship via `ops/disclosures.toml` |
| D-K10-2 | Entity-browse cap (10 pages / 1,000 rows per source) | Yes; larger sources use the download, API and K3 search |
| D-K10-3 | Show `review_packet` links (packets live in the repo) | Per D-J3-13: basis/role/date now, packet text per packet after review |
| D-K10-4 | Publish SIG's reliability class (`default_tier`) with its justification per source | Yes, after the operator reviews the justification texts in batches |

Reused, not re-asked: D-J3-2 (Q-22b robots disclosure), D-J3-3 (commit hashes), D-J3-12, D-J3-13, D-K9-1/2.

---

## 22. Risks

| id | risk | mitigation |
|---|---|---|
| R-K10-1 | Honest rights text reads as an admission that invites takedowns or blocking | the operator approves each text (D-K10-1); this is the truthful state; takedown path exists (corrections runbook) |
| R-K10-2 | Registry free text leaks through a new field or template | fail-closed lint (§4); scrub gate; AT-K10-02 |
| R-K10-3 | Robots-disregard disclosure prompts vendor blocking | D-J3-2; day-granular schedules; per-host counts, no URLs |
| R-K10-4 | Page count grows with executions (captures pages) | 100-row pages; captures/changes view for humans; JSON for completeness |
| R-K10-5 | Contribution tables imply geographic coverage SIG lacks | `basis` column; `unresolved` bucket; PKG-06b before claims of per-place coverage |

---

## 23. New findings (K10 side; rows in `findings/incoming/K9K10.csv`)

| id | title | sev |
|---|---|---|
| NEW-4 | Execution history cannot be keyed on `ingest_run`: 324 of 387 run rows carry no `ingest_run_id`, pre-P31.2 executions shared 20 reused `ingest_run` rows (so their `started_at`/`code_commit` describe the shared run), 23 rows stay unmatched, and J3 §4.5 maps "started" to `ingest_run.started_at` | S2 |
| NEW-5 | 12 ingested-live sources have no GCS run row: 8 are backed only by committed repo live-run records (2026-09-16…19; git-only clock) and 4 (`eff_atlas_of_surveillance`, `muckrock`, `osm_element_history`, `state_alpr_statute_inventory`) by no execution record at all; `ccops_seattle`/`ccops_nyc_post` are registered as "connector over committed fixtures" yet scheduled monthly | S2 |
| NEW-6 | The source registry has no field-level publish verdict and several fields are unsafe to render verbatim (`notes`: internal ticket ids on 239 rows, internal paths on 13, email-like strings on 4; `access_method` fixture paths; `auth_model` environment-variable names; an email `contact` on `eyes_on_flock`; `robots_policy = "honor"` contradicted by run records) — latent until a source page renders "full metadata" | S2 |
| NEW-7 | The registry has no publisher field: J3's "publisher" column and K9's publisher sort have no source of truth; publisher names exist only as per-target `agency` strings for 186 camera-registry/DOT sources, and 156 sources have none | S3 |
| NEW-8 | Jurisdiction is assigned per source, never per point: all 178 site sources map to exactly one jurisdiction (`camera_jurisdiction` = the target's configured `state`), so 58 sources (166,210 rows, 70.1 %, incl. the national OSM-derived layer) contribute to no geographic dossier and "which sources contributed what to this jurisdiction" (U-003.5/10) is unanswerable for most data; PKG-06b quarantines mismatches but adds no point-level assignment (refines F-04) | S2 |

---

## 24. Limits

- No spine query was run (P3): `rights_decision` row counts, per-source claim totals and the published/ingested split are
  not measured; the pages must compute them.
- Sizes are inference from run-row counts (recorded-execution) and J3/J4 unit sizes; UX10-3 measures with the P32.13
  `measure_build` pattern before rollout.
- Whether the 8 repo-record-only sources were fetched live or from committed fixtures is not provable from the records read
  (mode `live`, 0 robots decisions, 1 capture digest for `ccops_seattle`); NEW-5 states only what the records show.
- Nothing here is a legal opinion; disclosure texts are agent-drafted for the operator (P4).

Work window closed 2026-09-30T21:53:36Z (`date -u`). Findings file: `findings/incoming/K9K10.csv` (8 rows; NEW-4…NEW-8 from this row).
