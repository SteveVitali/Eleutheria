# K11 — Research queue usability · operator ask U-003.11

Row **K11** of `META_PLAN.md` §6 Stream K (owner R/D, depends C2). Written 2026-09-30 by Claude Code (Opus 5.5) in the
planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `e69f3fde`). Every
code path cited is byte-identical to chain tip `b051732c`. Work window (`date -u`): **2026-09-30T21:36:08Z → 22:01:07Z**
(the same session as K7 and K8). `PD` = `docs/build/planning/2026-09-30-next-phase`. Findings are in
`findings/incoming/K7K8K11.csv`.

> **Design only (P3/P10).** Production was only read; K7's header gives the budget and the UA. The 144 MB queue file was
> **not** downloaded. It was sampled with 33 HTTP `Range` reads (24 evenly spaced 24 KiB slices plus 9 binary-search
> probes of 8 KiB; ≈0.66 MB in total). Nothing here is `engineered` or `live-executed` (P5). Public sentences are
> **agent-drafted**. Scratch evidence: `docs/build/logs/next-phase/K7K8K11/` (`json/rq_sample_summary.json`,
> `json/rq_sample_examples.json`, `tools/rq_sample.py`).

**Operator ask (U-003.11, verbatim):** *"the Research queue as-is is currently unusable, bare minimum the UUIDs like
01a0a720-9b9a-7890-a8ae-99705e6b5368 need to be replaced with human readable identifiers and linked to detail page."*

**Inputs read.**
- `META_PLAN.md` §3; the K block.
- C2 JOURNEYS P8-T1/P8-T2 and ROUTES R18/R21.
- C3 DATA_TRUTH §4.7, §4.12, §7.
- PROTOCOL P8.
- FINDINGS F-112, F-113, F-274, F-365.
- J3 §6/§12 (downloads, TX-10/11).
- Code:
  - `web/src/pages/research-queue.astro`, `web/src/pages/task/new/[slug].astro`;
  - `web/src/lib/{research-queue,task,data}.ts`;
  - `exports/src/exports/spine_export.py` (`research_tasks`, `entity_labels`, `_research_queue`);
  - `exports/src/exports/analytics.py` (queue_meta, provenance);
  - `tasks/src/tasks/{catalog,detect,research_pg,records_request,maproulette}.py`, `tasks/src/tasks/data/{records_law,request_templates}.toml`;
  - `inference/src/inference/materialize.py`, `inference/**/peer_classes.toml`;
  - `db/deploy/{graph_annotations,research_task_trigger}.sql`;
  - `api/src/api/{app,store_pg}.py` (dereference, labels);
  - spec §33 and §39.7 (SIG-UI-031, SIG-TASK-002/007/008/010–012/018).

---

## 0. Summary

**Measured.** `/research-queue/` is a single 689,410-byte page. It shows the first **500 of 243,761** tasks (0.2%):
- 13,609 DOM nodes; ≈275 screen-heights on desktop and 366 on mobile.
- **No links** in the cards (0 in the 50 measured; no `/task/` link anywhere on the page); every heading is a raw subject
  UUID.
- One filter option, "Unscoped — 243761".
- 500 duplicate `id="jurisdiction-"` attributes.
- Every card says assignee "contributor" and effort "unknown".
- Every "How this task can be dispositioned" disclosure opens to nothing.

The full queue is only a 144 MB JSON file. Estimated from sampling (**inference**, byte-offset boundaries; the sum check
lands within 635 B of the real size), the queue is:

| task type | tasks | share |
|---|---|---|
| per-camera `coverage_hole` | ≈243,035 | **99.7%** |
| `missing_contract` | ≈595 | |
| `sharing_snapshot_stale` (counted exactly) | 130 | |
| `conflicting_retention` | 1 | |

Not one task has a jurisdiction: the filter is computed over all 243,761 tasks and finds only the empty value.

**Root cause: UUIDs are the symptom, not the cause.**
1. **The export throws away what the engine knows** (NEW-10). The exporter emits placeholders (`contributor`, `unknown`,
   `[]`) and the subject UUID as the label, with **no task id**. Yet the task catalog holds each type's assignee, effort,
   scope and dispositions, the export already reads entity labels, and the API derives readable labels (for example
   "data_driven:agency:Acworth Police Department") from the same table.
2. **The detector design floods the queue** (NEW-11, NEW-12, NEW-13). One task per camera site comes from peer-class
   negative space, such as an OSM node missing a `brand` tag. Coverage routing is a substring match: "retention" and
   "sharing" gaps become `missing_contract`, which asks for a contract. Contradiction and stale-edge tasks are minted
   with jurisdiction `None`.
3. **The surface has no identity, pages or pagination** (NEW-14). There is no task page (the `/task/new/…` pages are
   static "generate a task" mock-ups, F-113/F-274), `/v1/task/{id}` is unreachable without an id, and the page is capped
   at 500.

**Redesign headline.** The queue becomes a navigable **work board** with three changes.
- **Readable handles and titles.** For example `T-usa-ga-acworth-share-pd-7k2q` with the title "Update Acworth Police
  Department's data-sharing list (last snapshot {date}, over a year old)". The UUID moves into "technical details" and redirects.
- **Task detail pages.** Each states what is unknown, why it matters, the place and entity links, the evidence so far,
  suggested sources, a ready-to-file **records-request draft** (DRAFT, never sent, SIG-TASK-018), the closing condition,
  status and history, and how to act.
- **A restructured queue.** About 727 agency-level research tasks move to the front, sliced by place, type and role
  through pre-rendered, paginated routes of ≤50 cards and ≤150 KiB. The ~243k per-camera tag gaps become **mapping
  campaigns** aggregated by place × missing field, or leave the queue altogether (D-K11-1).

The same handle grammar serves watch items (K7) and evidence artifacts (K8).

**Tickets (§11):** RQ-00…RQ-06. **Operator decisions (§12):** D-K11-1…D-K11-6.

---

## 1. Measurements (2026-09-30T21:38–21:44Z)

### 1.1 The page

| metric | value | evidence |
|---|---|---|
| HTTP | 200, `text/html`, 689,410 B decoded, 20,073 B transferred (compressed), `last-modified` 2026-09-27T01:33:43Z | live-read; `curl/research_queue.headers`; body sha256 `0b62c05e…`; navigation timing in `json/scen_pages_rq_metrics.json` |
| cards | 500 (`MAX_TABLE_ROWS = 500`, `data.ts:635`); truncation note "Showing the first 500 of 243761 open tasks…" | live-read + code |
| DOM | 13,609 nodes; scrollHeight 247,611 px at 1440×900 (≈275 screens) and 308,491 px at 390×844 (366 screens); 0 scripts; no horizontal overflow | live-read (headless Chrome) |
| per card | ≈1,375 B of HTML | live-read |
| links in cards | 0 in the first 50 (and 0 `/task/` links on the page) | live-read |
| headings | `<h3>` = subject UUID; 500 distinct | live-read |
| filter | 1 option, "Unscoped — 243761 task(s)", href `#jurisdiction-`; clicking scrolls to the first card | live-read (`afterFilterClick` scrollY 648) |
| duplicate ids | `id="jurisdiction-"` × 500 (`research-queue.astro:85` builds the id from the jurisdiction, which is empty for every card) | live-read + code |
| disposition disclosure | 500 `<details>`, **0** items inside (`card.dispositions` = `[]`) | live-read; screenshot `shots/20260930T214332Z_scen_pages_rq_details_open_desktop.png` sha256 `1b640fb3…` |
| card field values | assignee `contributor` (500/500), effort `unknown` (500/500), geographic scope "—", trigger `<kind> <uuid>` | live-read |
| types in the first 500 | `sharing_snapshot_stale` 130, `conflicting_retention` 1, `coverage_hole` 369 | live-read |

### 1.2 The whole queue (`web/research_queue.json`, 144,060,710 B, release `sig-2026-09-27-ce480ab1`)

The file is ordered `priority DESC, task_id` (`spine_export.py:148-159`). Sampling it gave these results.

| measure | value | how |
|---|---|---|
| tasks | 243,761 | `queue_meta.json` denominator (live-read) |
| parsed sample | 976 complete task objects from 24 evenly spaced slices | recorded-execution (`tools/rq_sample.py`) |
| priority bands | 1.0: `sharing_snapshot_stale` (slice 0); 0.5: all later slices | sample |
| `coverage_hole` | ≈243,035 (99.70%): the tasks from priority 0.5 up to byte 143,713,228, less the counted top rows | byte boundary found by binary search (9 probes), divided by the mean object size (591.0 B) |
| `missing_contract` | ≈595: the last 347,482 B at a mean of 584.0 B | same |
| `sharing_snapshot_stale` | 130 (exact: the top of the file, on the page) | live-read |
| `conflicting_retention` | 1 (exact, on the page) | live-read |
| consistency | 130×607 + 243,035×591 + 595×584 ≈ 144,060,075 B vs 144,060,710 B actual (Δ 635 B ≈ 1 object) | arithmetic |
| jurisdiction set | 0 of 976 sampled; the page filter shows 0 of 243,761 | sample + live |
| dispositions | `[]` in 976 of 976 | sample |
| `subject_label == subject_id` | 976 of 976 | sample |
| fields | `assignee_class, closing_condition, dispositions, effort_estimate, evidence_sought, geographic_scope, jurisdiction, priority, subject_id, subject_label, task_type, trigger{kind,ref}`. There is **no `task_id`** | sample |
| distinct subjects | 976 of 976 (one task per subject; the dedup key is `(task_type, subject)`, `graph_annotations.sql:49`) | sample |

### 1.3 What the subjects are (public API `/id/entity/<uuid>`)

| task type | example subject → label (live) | what it is |
|---|---|---|
| `coverage_hole` | `01a0cbe5-8234-…` → `traffic_camera:camreg_osm_surveillance:osm_surveillance_deflock:19514` | one OSM/DeFlock camera node |
| `missing_contract` | `01a0bd3b-6275-…` → `flock_portal:wooster-oh-pd` | an agency's vendor-portal deployment |
| `sharing_snapshot_stale` | `01a0a720-9b9a-…` (the UUID in the operator's ask) → `data_driven:agency:Acworth Police Department` | an EFF Data Driven agency row |

All of them are typed `deployment` (canonical path `/v1/entity/deployment/…`). The dereference page prints the placeholder
IRI `https://sig.example/id/entity/…` (F-247). **The operator's example UUID is Acworth Police Department.** A readable
label existed all along, one join away.

### 1.4 What a task contains today vs what the engine knows

| card field | exported value | what exists | where |
|---|---|---|---|
| identity | none (no `task_id`) | `research_task.task_id` (uuidv7) | `graph_annotations.sql:38` |
| label | subject UUID | entity label from `entity_identifier` (the export already queries it as `entity_labels`) | `spine_export.py:134-141`; `store_pg.py:658-668` |
| assignee | `"contributor"` (not a vocabulary value) | per type in the catalog, e.g. `missing_contract` → `records_requester` | `catalog.py:106-128`; `spine_export.py:1259` |
| effort | `"unknown"` | per type, e.g. `quick`/`moderate`/`substantial` | same |
| geographic scope | the jurisdiction id (empty) | per type: `jurisdiction`/`region`/`global` | same |
| dispositions | the row's current disposition, so `[]` | the reachable set by assignee (`_DISPOSITIONS_BY_ASSIGNEE`) | `catalog.py:56-85`; `research-queue.ts:117-135` |
| evidence sought | the task-type slug | the missing predicate(s) (coverage record `predicate_id`) | trigger → `coverage_record` |
| jurisdiction | `""` | the subject's attributed jurisdiction (site→jurisdiction map built for dossiers; organisation claims) | `spine_export.py:1396`, dossier attribution |
| records request | none | statute + citation for 51 US jurisdictions (50 states + DC) and 6 template families, drafted per task by `records_request_drafts` and **not published** | `detect.py:113-125, 430`; `records_request.py`; `data/records_law.toml` (51 `[jurisdictions.*]` tables); `data/request_templates.toml` (6); `research_pg.py:242,278` |

---

## 2. Root causes

| # | cause | class | evidence |
|---|---|---|---|
| RC-1 | The exporter maps rows to cards with placeholders and never joins labels, the catalog, jurisdiction or the task id | code | `spine_export.py:1241-1270` |
| RC-2 | The queue is flooded by per-subject peer-class negative space: every entity in a declared peer class that lacks any tracked predicate becomes one `coverage_hole` task. OSM nodes track 16 predicates, DOT registries 12 | detector design | `inference/materialize.py:335-398`; `peer_classes.toml`; `detect.py:311-338` |
| RC-3 | Coverage routing uses a substring match (`_RECORDS_OBTAINABLE_MARKERS` = contract, procurement, retention, policy, funding, grant, sharing). `configured_retention_days` and `configured_sharing_partner` gaps become `missing_contract`, whose closing text asks for "the procurement record (contract/purchase order)". The dedup key hides which predicate(s) are missing | detector design | `detect.py:94-102, 325-326`; `research_pg.py:60-89` |
| RC-4 | Contradiction and stale-edge candidates carry jurisdiction `None`, and per-subject coverage records have none | code | `detect.py:307, 357`; `materialize.py:385-397` |
| RC-5 | No identity, detail page or pagination on the public surface. The `/task/new/<base64>/` pages are a static intake mock-up: "A research task has been generated…", although nothing is generated (F-113), and six demo fixture pages are live (F-274) | surface | `task/new/[slug].astro:36-56`; ROUTES R21 |
| RC-6 | Coverage-hole closing text speaks of "the jurisdiction" while the subject is one camera | copy | `research_pg.py:71-74` |

---

## 3. Human-readable identifiers (the shared handle grammar)

K2 owns **entity** labels. This section defines **handles** for the non-entity objects the public surface lists: tasks
(`T`), mapping campaigns (`M`), watch items (`W`, K7) and evidence artifacts (`E`, K8). K13 reconciles the two.

```
handle  = kind "-" place "-" code "-" slug "-" hash
kind    = "T" | "M" | "W" | "E"
place   = the K4 display-slug path (design/K4-dossier-index.md §3.1: alpha-3 country, ISO 3166-2 suffix, then the
          Census name slug) joined with "-", dropping the GEOID suffix and, for places only, the trailing LSAD word
          (city/town/village/cdp); counties keep "county". The hash disambiguates:
          usa, usa-ga, usa-ga-acworth, usa-tx-travis-county, gbr-eng, … | "unplaced" (= K4's `unresolved` bucket)
code    = per-type mnemonic, 1 token, [a-z]{2,10} (table below; registry file tasks/data/task_codes.toml)
slug    = subject slug: public label → strip scheme prefixes ("data_driven:agency:", "flock_portal:") → ASCII-fold
          (NFKD, drop marks) → lowercase → [a-z0-9]+ tokens → drop tokens equal to the place's last component →
          abbreviate org suffixes (police department→pd, sheriff's office→so, department of→dept, county→co) →
          join with "-" → cut at 24 chars on a token boundary; empty → omitted
hash    = Crockford base32 of sha256(canonical UUID), first 4 chars; extended to 5…8 on a collision within the release
length  ≤ 64 chars; the handle is an opaque key for machines (resolved by exact lookup), readable for people
```

| task type | code | example handle (from live subjects) | title template (agent-drafted) |
|---|---|---|---|
| `sharing_snapshot_stale` | `share` | `T-usa-ga-acworth-share-pd-7k2q` | "Update who {agency} shares data with (last snapshot {date}, {age} old)" |
| `missing_contract` | `contract` | `T-usa-oh-wooster-contract-pd-3m9x` | "Find the {technology} contract or purchase order for {agency}" |
| `conflicting_retention` | `retention` | `T-usa-ok-oklahoma-city-retention-pd-q1c4` | "Resolve {agency}'s retention period: policy {a} days vs configuration {b} days" |
| `contract_expiring` (K7) | `renewal` | `T-usa-tx-austin-renewal-flock-8h2d` | "Find the renewal terms for {agency}'s {vendor} contract ending {date}" |
| `sharing_asymmetry` | `asym` | — | "Confirm whether {a} really shares data with {b}" |
| `candidate_duplicate_entities` | `dup` | — | "Are {x} and {y} the same {type}?" |
| campaign (per place × field) | the field name | `M-usa-tx-operator-osm-5f0a` | "Add the operator of {n} OSM surveillance cameras in {place}" |

Hashes in the examples are illustrative. Places depend on K4 keys and on attribution (§4.3).

**Stability and redirects.**
- The canonical identity stays the UUID (`task_id`).
- If a label or place changes, the handle changes. The export keeps a `handles_history` map, and nginx serves 301 from
  every earlier handle, generated as an include like J3's withdrawal include.
- `/task/<uuid>/` redirects to the current handle.
- `/v1/task/{task_id}` stays the machine route. The task page shows the UUID, subject UUID, trigger ref and API URL under
  "Technical details".

**Part VIII.**
- Slugs are built only from organisation, jurisdiction, place, product or vendor labels.
- If the subject is person-typed, or its label fails the person-name screen (the officer-naming gate), the slug is
  omitted: `T-usa-ok-retention-q1c4`.
- Handles never carry plate, device-owner or address data. Camera subjects appear only inside campaigns, and
  C3–C5 geometry is excluded (`maproulette.py` rule).

---

## 4. Restructuring the queue (the unit of work)

### 4.1 Three lanes

| lane | what | today | public surface |
|---|---|---|---|
| **Research tasks** | agency, contract, policy and contradiction work: records requests, analysis, verification | ≈727 (595 + 130 + 1 + K7's renewal tasks) | the main queue; one page per task |
| **Mapping campaigns** | field gaps on individual mapped objects, aggregated by (place, peer class, missing predicate) | ≈243k per-camera tasks → at most a few hundred campaigns (**inference**: 51 US states + other places × ≤16 predicates) | a campaign page with a count, a sample and a download; OSM guidance; MapRoulette once HG-08 is registered |
| **Curation** | ER pairs, vocabulary mapping, long-unverified claims (curator/developer roles) | not in the export today | counts only on the hub; the work happens in the loopback curation app (ADR-068) (D-K11-5) |

**Detector changes (RQ-02).**
- Per-subject peer-class gaps stop minting `coverage_hole` research tasks. D-K11-1 decides between two options:
  - **(a)** mint them as campaign rows;
  - **(b)** leave them as coverage metrics only (§32).

  `research_task` rows are append-only in spirit: existing rows get a `superseded` disposition with a reason, never a
  delete.
- Routing uses an explicit **predicate → task type** table instead of substrings:

  | predicate | task type | request template |
  |---|---|---|
  | `configured_retention_days` | `retention_unknown` (new; records requester) | `surveillance_policy` |
  | `configured_sharing_partner` | `sharing_unknown` (new) | `data_sharing_agreement` |
  | contract predicates | `missing_contract` | `alpr_contract` |

  The task records **which** predicate(s) it seeks (an additive `research_task.predicate_ids` column; a new sqitch
  change).
- Every task gets a jurisdiction when the subject is attributable (RC-4). Otherwise it goes to `unplaced`, shown as a
  data-quality bucket (K4).

### 4.2 Priority and ordering

Within the research lane the ordering is:
1. claimed jurisdictions first (SIG-TASK-010), once claiming exists;
2. then priority;
3. then **decision proximity**: a task on a subject with a K7 watch item inside 90 days ranks up;
4. then age.

There is no leaderboard (SIG-TASK-012). Sort routes offer priority, newest and "oldest evidence" (stale first).

### 4.3 Placement

A task's place is the subject's attributed jurisdiction, taken in this order:
1. the resolved `organization_jurisdiction`;
2. the dossier site→jurisdiction map;
3. the agenda tenant's registered jurisdiction;
4. otherwise `unplaced`.

A label like "Acworth Police Department" is never parsed into a place. It can only become a *candidate* for review.

---

## 5. Pages (static zero-JS baseline; enhanced version noted)

### 5.1 `/research-queue/` hub

1. **What the queue is** (≤60 words) and **how to help**, a three-step strip: pick → do → report.
2. **Start here**, one entry point per persona:
   - "Tasks in your state" (place list with counts);
   - "Records you can request" (records-requester tasks with drafts);
   - "Open disagreements" (contradiction tasks).
3. **Research tasks.** Counts by type (plain-language names) and by role ("File a records request", "Analyse data",
   "Check on the ground"). Then the top 20 by priority as compact cards.
4. **Mapping campaigns.** The top campaigns by count, with a link to all campaigns.
5. **Downloads.** Sharded JSONL.gz per lane and place (J3 TX-10b, through the low-egress host TX-11; replaces the 144 MB
   single file, F-365).
6. "How we know this", page-specific (the labels are fixed per C3 NEW-13: "Tasks", "Detectors", not "Artifacts" and
   "Independent sources").

**Card (≤1 KB, one link per card).** Title (→ `/task/<handle>/`), handle, place breadcrumb, type label, role, effort,
status, a one-line "why it matters", trigger age ("snapshot from 2019"), an evidence count, and a "draft request
available" badge.

### 5.2 Facet, sort and pagination routes (pre-rendered)

Routes:
- `/research-queue/place/<key>/`, with children listed (state → cities);
- `/research-queue/type/<code>/`;
- `/research-queue/role/<assignee>/`;
- `/research-queue/place/<key>/type/<code>/`, only for places with more than 50 tasks.

Each route has `…/page/<n>/` and `…/sort/<key>/`, at **50 cards per page**. The budget is ≤150 KiB total transfer and 0
scripts, estimated ≈70 KB of HTML per page (**inference**: 50 × ~1 KB + chrome).

Scale: research tasks ≈727 → about 15 pages per sort order. Campaigns are paginated the same way.

**Enhanced (only if K0 allows).** A filter island reuses `/search/` (J3 G-11) with task facets: place typeahead,
type × role × effort multi-select, and sort. It reads the per-place shard (≤200 KB). The no-JS routes remain the source
of truth (SIG-UI-037/050).

### 5.3 Task detail page `/task/<handle>/` (+ `.json` twin)

| block | content |
|---|---|
| title + handle + status | status from `research_task.status`/`disposition`, e.g. "Open · unclaimed · anyone may work this task" |
| What's unknown | the missing fact(s) in plain language, with the absence kind: "SIG has not looked" (not_researched) vs "SIG looked and found nothing" (searched_not_found, with the sources searched) |
| Why it matters | a per-type template linked to the design-centre question it serves: sharing → "who else can see the data" (A5); contract → "what does it cost, when does it renew" (A3); retention → "how long is data kept" |
| Subject and place | entity card (K2 page link), dossier link, place breadcrumb (K4), related watch items (K7) |
| What SIG already has | claims about the subject that bear on the gap, each with J3's provenance panel link; for stale snapshots, the snapshot date and source (K8 artifact page) |
| Triggered by | the coverage record / relationship / contradiction in words ("EFF Data Driven lists this agency's sharing partners as of 2019-…"), with a link |
| Suggested sources | registry sources that cover this place and technology, with lane and status (K9/K10 source pages); the jurisdiction's agenda portal (K7 coverage); vendor transparency portals; a link to search MuckRock for prior requests (an outbound link, per C5's link policy) |
| Records-request draft | for records-requester and document-reviewer tasks: statute + citation (`records_law_for(state)`), the current template version, a request text with placeholders, a residency note where the state restricts requesters, and "SIG sends nothing; you file it; the filer is left blank" (SIG-TASK-018). Download as `.txt`. **DRAFT, NEVER SEND** |
| Closing condition | the testable condition (SIG-TASK-002), naming the predicate |
| How to act | steps per role; "Report what you found": a link to the intake form prefilled by GET (`?task=<handle>`), **only when the receiver operates** (today `/dispute/` says it does not). Until then, the channel the operator names (D-K11-4); the page never invents one |
| Possible outcomes | the reachable dispositions for this role, with plain meanings (fixes the empty disclosure), including "searched, found nothing" (SIG-TASK-008/009) |
| History | generated_at, detector version, status changes, the outcome and resulting claims or corrections once closed |
| Related | other tasks on the same subject, place or type |
| Technical details | task UUID, subject UUID, trigger ref, `/v1/task/<id>`, JSON twin |

### 5.4 Campaign page `/research-queue/campaign/<handle>/`

This page shows:
- the field, its source class (OSM, DOT registry), the place and the count;
- why it matters (for example, operator tags feed "who runs this camera");
- how to contribute: an OSM tagging guide link, and a MapRoulette cooperative challenge only once HG-08 registration
  exists (`maproulette.py` refuses otherwise);
- a paginated subject list (labels → K2 pages, no C3–C5 geometry) and a download.

For DOT-registry fields the honest note is: "this field is not published by the source; there is nothing to map".
D-K11-1 may drop these campaigns entirely.

### 5.5 Retire the mock intake pages

`/task/new/<base64>/` pages stop being generated in export mode:
- fixture pages never ship (F-274);
- dossier gap links point to the **real** task handle for that gap. If no task exists, the gap shows a named absence:
  "no task yet: gaps of this kind are not queued because …".

The "has been generated" copy goes (F-113).

---

## 6. Contributor workflow (end to end)

1. **Find.** Pick from the hub or a facet; or from a dossier gap, a watch item (K7) or an evidence page (K8); all link to
   task handles.
2. **Understand.** The detail page gives the unknown, why it matters, the sources and the closing condition.
3. **Do.** The contributor files the draft request themselves, checks the portal, or maps in OSM. SIG never transmits.
4. **Report.** Through the intake receiver when it operates (a plain HTML form: no account, no scripts, ≤3 https
   evidence links, Part VIII auto-refusal; `/dispute/` describes it). The task handle is prefilled.
5. **Review.** A curator works it in the loopback curation app (ADR-068). The disposition comes from the full vocabulary
   (§33.4).
6. **See the outcome.** The next release or status-lane run shows the new status, the disposition and any new claims on
   the task page. Corrections also appear on `/corrections/`.
7. **Recognition.** Qualitative, tied to verified contributions; no volume leaderboard (SIG-TASK-012).

**Claiming** (SIG-TASK-010/011) needs community identity. `queue_meta` says jurisdiction claims are state the spine does
not carry. So v1 shows "Anyone may work this task" and no claim control (D-K11-6).

---

## 7. Relation to `/evidence/` and the watch

- **Task → evidence:** the trigger's evidence and the subject's claims link to K8 artifact and claim pages. A closed task
  links to the new evidence.
- **Evidence → task:** each artifact page lists "open tasks this could close". This also sets the recommender's
  `answers_open_task` (K7 §5.7), which is `false` for all 255 artifacts today.
- **Watch → task:** `contract_expiry` items with unknown terms open `renewal` tasks (K7 WX-06). Tasks on subjects with
  imminent decisions rank up (§4.2).
- **Not a gate:** research tasks never gate publication of evidence (K8 §0). The queue is where the work to *add*
  evidence is coordinated.

---

## 8. Draft requirements (provisional `SIG-RQ-Dnn`; T1 folds them into SIG-UI-031 and SIG-TASK)

| id | requirement | acceptance criteria |
|---|---|---|
| SIG-RQ-D01 | Every public task, campaign, watch item and evidence artifact MUST have a handle and title per §3. No public queue or task page may use a raw UUID as a label or heading. | golden tests for the slug and hash rules (including transliteration, collision extension, the person-name fallback); crawl: no `<h1>`–`<h3>` matches the UUID pattern on `/research-queue/**` or `/task/**` |
| SIG-RQ-D02 | Every public task MUST have a detail page with the §5.3 blocks. Each block MUST be a value or a named absence. | JSON Schema `sig.task-page/1` validates for all tasks; every card links to a 200 page |
| SIG-RQ-D03 | Exported cards MUST carry the catalog's assignee class, effort, scope and reachable dispositions for their type, and the subject's jurisdiction when attributable. Placeholder values are forbidden. | export test over a fixture spine: no `contributor`/`unknown`; dispositions equal `_DISPOSITIONS_BY_ASSIGNEE[assignee]`; attributed-jurisdiction test |
| SIG-RQ-D04 | The queue MUST be paginated (≤50 cards and ≤150 KiB per page), with no-JS routes by place, type and role, and totals that reconcile. | lhci budget on sampled routes; the sum of facet counts equals the lane total (test); HTML validator: 0 duplicate ids |
| SIG-RQ-D05 | Coverage-gap routing MUST use an explicit predicate→task table. Each task MUST name its missing predicate(s), and its closing condition MUST match its subject grain. | a routing matrix test over every tracked predicate; a copy test (no "jurisdiction" wording on subject-grain tasks) |
| SIG-RQ-D06 | Per-object field gaps MUST be presented as aggregated campaigns (or excluded, D-K11-1), not as individual research tasks. | the research lane contains no peer-class `coverage_hole` rows (test) |
| SIG-RQ-D07 | Records-requester and document-reviewer tasks MUST show a DRAFT request (statute, citation, template version, residency note) with no requester identity and no transmit path. | draft rendered for 100% of eligible US tasks; a test asserts there is no network call or form post; `records_requests_sent` stays 0 |
| SIG-RQ-D08 | Dossier gap links MUST resolve to the real task page for that gap or to a named absence. Static "task has been generated" pages MUST NOT ship in export builds. | crawl: 0 `/task/new/` routes in export mode; every gap link 200 |
| SIG-RQ-D09 | Handles MUST be stable within a release and redirect (301) across releases when they change. `/task/<uuid>/` MUST redirect to the handle. | redirect-map test; live probe after republish |
| SIG-RQ-D10 | Bulk queue downloads MUST be sharded (≤25 MB per file) and served from the low-egress host. | manifest check; no single queue file larger than 25 MB |

**Spec amendments proposed.**
- **SIG-UI-031:** adds "every task has a detail page and a human-readable handle", and replaces the geographic filter with
  place facet routes.
- **SIG-TASK:** adds the campaign concept (a per-object gap is not a research task).

---

## 9. Acceptance journeys (agent walkthroughs; P4)

| id | persona | task | success |
|---|---|---|---|
| KJ11-1 | contributor (P8-T1) | "Find a concrete research task for Maryland and what would close it" | ≤3 clicks, no JS: hub → place `usa/md` → a task page with the closing condition, role, effort and draft request; or a named absence "no open research tasks for Maryland" with the reason |
| KJ11-2 | contributor (P8-T2) | click "? Not researched" on `/dossier/md/` | lands on the real task (or a named absence), never "a task has been generated" |
| KJ11-3 | operator's example | find `01a0a720-9b9a-7890-a8ae-99705e6b5368` | `/task/<uuid>/` → 301 → `T-usa-ga-acworth-share-pd-…` titled with Acworth Police Department, with the stale snapshot date and the EFF Data Driven source |
| KJ11-4 | organizer | "Give me every records request I can file in Texas" | `/research-queue/place/usa/tx/role/records_requester/` plus a bundle download of the drafts |
| KJ11-5 | mapper | "Where can I help map in Ohio?" | the campaigns list for `usa/oh` with counts and OSM guidance; no camera geometry above C2 |
| KJ11-6 | journalist | "Which agencies' sharing lists are most out of date?" | the `share` type sorted by oldest evidence, with the snapshot dates visible |

---

## 10. Budgets

| surface | today | target |
|---|---|---|
| `/research-queue/` | 689,410 B HTML, 500 cards, 13,609 nodes | ≤150 KiB total, ≤50 cards; hub + top 20 |
| task page | none | ≤60 KB HTML (**inference**) |
| bulk file | one 144 MB JSON in the CC-BY `web/` compartment (F-365 egress) | sharded JSONL.gz per lane/place, each ≤25 MB, through TX-11 |
| static pages generated | 1 page + 78 `/task/new/` pages | ≈727 task pages + facet pages + campaign pages (thousands at most) |

---

## 11. Round-11 ticket outline

| key | title | size | scope | depends | live / gate |
|---|---|---|---|---|---|
| RQ-00 | Queue truth fixes (safety wave) | S | unique ids and no dead anchor; the disposition list from the catalog vocabulary instead of `[]`; "not yet classified" instead of `contributor`/`unknown`; retire `/task/new/` fixture pages and the "has been generated" copy (F-113, F-274); page-specific provenance labels (C3 NEW-13) | none | republish |
| RQ-01 | Task export v2 | M | `research_tasks` read adds `task_id`, trigger detail and predicate; join `entity_labels`; catalog metadata; jurisdiction attribution; handle + title derivation (§3) with `handles_history`; lane/place shards; `queue_meta` v2 | PKG-06a/K4 place keys; K2 label rules; TX-01 scrub | — |
| RQ-02 | Detector routing + campaigns | M | predicate→task table; new `retention_unknown`/`sharing_unknown` types in the catalog; `predicate_ids` column (additive sqitch change); jurisdiction for contradiction/stale candidates; campaign aggregation; supersede per-camera `coverage_hole` rows by disposition (append-only, never a delete) | RQ-01; D-K11-1; sqitch CI (PKG-01) | hosted detector re-run + sqitch change: op go |
| RQ-03 | Queue pages | L (03a hub + facet/pagination/sort routes + cards; 03b task detail + campaign pages + redirects + dossier gap links) | §5 | RQ-01; K4; K13 templates; J3 TX-08a panel links; K0 (enhanced island only) | republish |
| RQ-04 | Records-request drafts on tasks | S | persist `records_request_drafts` output into the export (DRAFT); render and download; residency notes; bundle per place | RQ-01; D-K11-3 | republish |
| RQ-05 | Contribution path wiring | S | "How to act" per role; intake prefill by GET once the receiver operates; the interim channel per D-K11-4 | intake receiver activation (operator gate); D-K11-4 | — |
| RQ-06 | `contract_expiring` wiring (shared with K7 WX-06) | — | **merged into K7 WX-06** (one owner, P9) | — | — |

**Order.**
1. RQ-00 in the safety wave, with K7 WX-07 and K8 EV-01.
2. In the first product wave: RQ-01, then RQ-03a, then RQ-04.
3. RQ-02 after D-K11-1 and the sqitch CI.
4. RQ-03b.
5. RQ-05 when intake opens.

---

## 12. Operator decisions needed

| id | question | recommendation |
|---|---|---|
| D-K11-1 | Are per-object field gaps (≈243k, OSM and DOT) research tasks? | no. Show OSM-field gaps as **campaigns** (routed to MapRoulette under HG-08 later). Show DOT-registry field gaps as coverage metrics only (there is nothing to research) |
| D-K11-2 | Approve the handle grammar (§3) for tasks, campaigns, watch items and evidence artifacts | approve; K13 aligns it with K2's entity labels |
| D-K11-3 | Publish records-request drafts (statute + SIG template) on public task pages? | yes: statutes are public law, the templates are SIG's own text, no requester data, never sent |
| D-K11-4 | Until the intake receiver operates, what reporting channel may task pages name? | the operator names one, or pages say "reporting opens with the intake form"; never an invented address |
| D-K11-5 | Are curation-lane tasks (ER pairs, vocabulary) public? | counts only; the work stays in the loopback curation app |
| D-K11-6 | Jurisdiction claiming (SIG-TASK-010/011) needs identity. Defer? | defer; v1 shows "anyone may work this task" |

---

## 13. Risks

- **R1: Handle churn.** Labels and places improve over time (K4, F-320), so handles change. Mitigation: 301 history and
  the UUID as the canonical key.
- **R2: Hiding real gaps.** Aggregating 243k tasks into campaigns might read as "no work". Mitigation: campaign counts
  appear on the hub, and the coverage metrics keep the negative space (SIG-METRIC-002).
- **R3: Legal-advice perception** of the drafts. Mitigation: "template, not legal advice", the source statute cited, and
  the template version and success sample shown (`request_outcomes.toml`).
- **R4: Misplaced tasks.** A wrong jurisdiction sends volunteers to the wrong records office. Mitigation: resolved
  attribution only (§4.3), and `unplaced` is visible.

## 14. Interfaces

- **K2:** entity labels and pages.
- **K4:** place keys and the `unplaced` bucket.
- **K7:** renewal tasks, decision proximity, the shared handle grammar.
- **K8:** evidence links both ways.
- **K9/K10:** suggested sources.
- **K13:** templates and navigation.
- **K0:** the enhanced island.
- **J3:** TX-01 scrub, TX-08a panel, TX-10b/TX-11 downloads.
- **G2:** hosted detector re-run window.
- **C2/C3 findings:** F-112 (refined by NEW-10 and NEW-13), F-113 and F-274 (RQ-00), C3 NEW-13 labels.

## 15. New findings (`findings/incoming/K7K8K11.csv`)

| id | title (short) | sev |
|---|---|---|
| NEW-10 | The task export discards catalog metadata, labels, jurisdiction and the task id; every card shows placeholders and an empty disposition list (refines F-112) | S2 |
| NEW-11 | 99.7% of the queue (≈243,035 of 243,761) is per-camera tag gaps; the ≈727 agency-level tasks are buried | S2 |
| NEW-12 | Substring routing sends retention and sharing gaps to `missing_contract`; tasks never name the missing predicate | S2 |
| NEW-13 | No task carries a jurisdiction (contradiction and stale candidates minted with `None`); the only filter is "Unscoped"; 500 duplicate ids | S2 |
| NEW-14 | The queue page is one 689 KB list of 0.2% of the tasks, with no pagination, no links and ~275–366 screen-heights | S2 |
| NEW-15 | Records-request drafts are never published and `contract_expiring` never runs (shared with K7) | S2 |

## 16. Limits

- Task-type counts other than the top 131 are **estimates** from sampled byte offsets. The spine was not queried.
- The number of campaigns after aggregation, and the per-state distribution of research tasks, are unknown until RQ-01
  runs.
- Titles, "why it matters" and "how to act" copy are agent-drafted.
- Records-request drafts are legal-process templates. SIG does not give legal advice. The operator and E-stream review
  the wording.
