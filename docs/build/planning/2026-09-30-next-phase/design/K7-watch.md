# K7 — `/watch` QA and redesign · operator ask U-003.7

Row **K7** of `META_PLAN.md` §6 Stream K (owner R/D, depends C1). Written 2026-09-30 by Claude Code (Opus 5.5) in the
planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `e69f3fde`). Every
code path cited is byte-identical to chain tip `b051732c` (`git diff --stat b051732c HEAD -- exports/ web/src db/ api/ ops/
connectors/ inference/ reconcile/ tasks/ ontology/` is empty). The deployed site was built on 2026-09-27 (`last-modified:
Sun, 27 Sep 2026 01:33:43 GMT` on `/watch/`). Between C3's inferred deploy base `5c064881` and the chain tip, the watch
code (`watch.astro`, `watch/*`, `lib/watch.ts`, `lib/recommender.ts`, `_watch`, `_evidence`, `_decision_point`) is unchanged.
`data.ts`, `empty.ts` and other parts of `spine_export.py` did change, but not in the watch paths. Work window (`date -u`): **2026-09-30T21:36:08Z →
22:01:07Z**. `PD` = `docs/build/planning/2026-09-30-next-phase`. Companion notes from the same session: `design/K8-evidence.md`
and `design/K11-research-queue.md`. Findings for all three rows are in `findings/incoming/K7K8K11.csv` (NEW-1…NEW-15).

> **Design only (P3/P10).** Production was only read. The whole session made 49 HTTP GET/HEAD requests with curl (7 to the
> site, 35 to the public bucket, 7 to the read API; a 50th was rejected locally by curl and never sent) and 5
> headless-Chrome page loads. The user agent was
> `SIG-planning-K7K8K11-review/1 (read-only)` and carried no personal identifier (P16). There were no form submissions and no
> DB, bucket or scheduler writes. Nothing here is `engineered`, `staging-verified` or `live-executed` (P5). Every public
> sentence below is **agent-drafted**. Scratch evidence is in `docs/build/logs/next-phase/K7K8K11/` (gitignored), with
> `fetch_log.tsv`, `loads.tsv` and hashes. **Evidence classes (P1):** `code` (file:line), `live-read`,
> `recorded-execution` (commands run locally, listed in §13), `inference` (labelled).

**Operator ask (U-003.7, verbatim):** *"it's not clear that the "/watch" feature actually works, so we should probably do some
QA there"*. The general ask U-003.G also applies: richer, more traversable, more inspectable.

**Inputs read.**
- `META_PLAN.md`: §3, the Stream K block, §8.2.
- `feedback/OPERATOR_FEEDBACK.md`: U-002 and U-003.
- `review/ROUTES.csv`: R23–R26.
- `review/PROTOCOL.md`: §3 (the watch rows), P1-T2, P1-T4, P7-T3 and H14.
- `review/JOURNEYS.md`: P1-T4 and P7-T3.
- `review/DATA_TRUTH.md`: §3–§4.
- `research/C5-landscape.md`: A3, A6 and C5-G3 (alpr.watch).
- `research/J1-exposure-inventory.md` and `design/J3-transparency-design.md`: §1, §5, §7 and §12.
- `design/G2-activation.md` and `design/G3-release-model.md`: §4.4 and §7.2.
- `data/source_coverage.csv`, `findings/FINDINGS.csv` (titles).
- Code:
  - `web/src/pages/watch.astro`, `watch/{[jurisdiction].ics.ts,[jurisdiction].xml.ts,citations.txt.ts}`;
  - `web/src/lib/{watch,recommender,data,empty,fixtures}.ts`;
  - `exports/src/exports/{spine_export,analytics}.py`;
  - `tasks/src/tasks/{catalog,detect}.py`;
  - `connectors/src/connectors/procurement.py`, `connectors/src/connectors/data/procurement_vocab.toml`;
  - `ontology/vocab/predicates.yaml`, `ontology/src/ontology/schema/entities.yaml` (Contract);
  - `db/deploy/domain_entities.sql`, `ops/cadence.toml`, `ops/web/nginx.conf`;
  - spec §39.5/§39.5a (SIG-UI-026/027/027a–c) and SIG-UI-014b.

---

## 0. Summary

**Does `/watch` work?** The page works as an honest empty shell. It returns 200, has no scripts, and its empty states
are clear. Nothing behind it works:
- The contract list is empty.
- No iCal or RSS feed exists; every probed `/watch/<j>.ics|.xml` returns the bare 146-byte nginx 404.
- The evidence recommender has no decision point.
- `citations.txt` is one line.

**Root cause: code first, then the data model, then scope. Publication eligibility is not the cause.**

1. **No producer (code, deterministic).** `_watch()` and `_decision_point()` read `raw["contract_watch"]`, but no export
   query ever fills that key. The only writers are three test fixtures. So the watch is empty **whatever the spine holds**
   (NEW-1, S1).
2. **Data model.** A watch item needs an expiry, an auto-renewal flag and a notice window. No predicate carries the last
   two, the agenda path makes contracts with only `proposed`/`awarded` dates, and every jurisdiction dossier hard-codes
   termination as unknown. A producer would therefore find almost nothing to watch (NEW-2, *inference*: the spine was not
   queried).
3. **Scope.** SIG already ingests dated, decision-relevant records, and none of them is modelled as a watch item:
   - SAM.gov notices with `posted_date` and `response_deadline`, seen live;
   - council agenda items with surveillance content terms and document links, seen live;
   - OpenStates bills, TED/DECP notices, and federal grants with award periods.

   Agenda sources run **monthly** and only 3 Legistar tenants are verified, so an agenda watch would miss most meetings
   (NEW-3).
4. **Latent defects behind the empty page.**
   - `.ics` would be served as `application/octet-stream`; the UIDs use `@sig.example`; DTSTAMP is the fixture date; RSS
     items carry no per-item link (NEW-4).
   - The recommender would rank all 255 national artifacts with `NaN` scores for any decision (NEW-5).
   - The empty-state copy blames a "research gap" and sends readers to a research queue that holds no watch-related task
     (NEW-6).

**Redesign headline.** Replace the single-purpose "renewal watch" with a **decision calendar**: upcoming public decisions
about surveillance technology, **by place, vendor and technology**. It covers five kinds of decision: contract renewals
and expiries, solicitation deadlines, council agenda items, legislative actions, and grant periods. Every item:
- names its date, **what kind of date** it is and **how certain** that date is;
- links to its evidence and to the next action;
- is subscribable per place, vendor, technology or kind as iCal, RSS/Atom, JSON Feed or OPML. SIG keeps no email list.

The pages are static and zero-JS, with pre-rendered filter routes; an optional filter island is left for K0 to decide. A
daily **watch lane** reuses J3's status-lane pattern so that agenda items reach subscribers before the meeting, not a
month later.

**Tickets (§10):** WX-01…WX-07. Three S, three M, one L. **Operator decisions (§11):** D-K7-1…D-K7-6.

---

## 1. Live QA (2026-09-30T21:38–21:44Z)

| # | check | result | evidence |
|---|---|---|---|
| Q1 | `GET /watch/` | 200, `text/html`, 8,631 B, `last-modified` 2026-09-27T01:33:43Z, `cache-control: max-age=0` | live-read; `curl/watch.headers`; body sha256 `0d384e78…` |
| Q2 | Scripts / JS budget | 0 `<script>` (headless DOM); zero-JS content page as designed | live-read; `json/scen_pages_watch_metrics.json` |
| Q3 | Content | 4 empty states: contracts, subscriptions, recommender, citations. All say "yet" and link to `/research-queue/`. Recommender text: "SIG is not yet tracking a dated upcoming decision… a gap in the record, not a claim that no decision is pending." The neutrality note (SIG-UI-027b) is present | live-read; `text/scen_pages_watch_desktop.txt`; screenshot `shots/20260930T214325Z_scen_pages_watch_fold_desktop.png` sha256 `7b3f45c4…` |
| Q4 | Mobile (390×844) | 4 screen-heights, all empty states; no horizontal overflow | live-read; `json/scen_mobile_watch_mobile_metrics.json` |
| Q5 | Feeds linked from the page | none (0 `.ics`/`.xml` links; 0 `<link rel=alternate>`) | live-read; `json/scen_pages_watch_metrics.json` |
| Q6 | `GET /watch/tx.ics`, `/watch/tx.xml`, `/watch/texas.ics` | 404, `text/html`, 146 B (the bare nginx page, cf. C2's 404 finding) | live-read; `fetch_log.tsv` |
| Q7 | `GET /watch/citations.txt` | 200, `text/plain`, 87 B: "No upcoming decision is tracked yet, so no evidence is ranked (a gap, not an absence)." | live-read |
| Q8 | Release data behind it | `web/watch.json` = `[]` (sha256 `37517e5f…`); `web/analytics/decision_point.json`: `decision_point: null`, denominator "0 contracts on the renewal watch" (sha256 `28874e76…`). Both equal the public `manifest.json` digests for release `sig-2026-09-27-ce480ab1` (re-fetched 21:39Z) | live-read |
| Q9 | Links in from other pages | only the nav; no dossier links to the watch (C2 P1-T4); the watch links to no dossier (0 `/dossier/` links) | live-read; C2 JOURNEYS P1-T4 |
| Q10 | Feed generator validity (fixture) | Fixture feeds for Oklahoma City and Tulsa built from chain-tip code parse with `icalendar` and `feedparser` (bozo=False, rss20). Folding and CRLF are correct. A **zero-event** calendar parses but violates RFC 5545 §3.4 (`icalbody` needs ≥1 component). Findings: UIDs `…@sig.example`; no `URL` per event; RSS has no `atom:link rel=self` and no `lastBuildDate`; every item links to `/watch/`; `pubDate` = the **future** decision date | recorded-execution; `feeds/validation.txt` |
| Q11 | Feed media type once deployed | `ops/web/nginx.conf:30-37` includes the stock `mime.types` and adds only pmtiles/geojson. `nginx:1.27.5-alpine` (the pinned base, `ops/web/Dockerfile:68`) has **no `ics` mapping**, so `.ics` falls to `default_type application/octet-stream`. `.xml` is served `text/xml` | recorded-execution (`docker run nginx:1.27.5-alpine grep`) + code |
| Q12 | DTSTAMP source | `[jurisdiction].ics.ts:13,27` passes `AS_OF.as_of_world` from `lib/fixtures` (`2026-08-20`) even in export builds | code |
| Q13 | Recommender on real data | `recommendEvidence(evidence.json.artifacts, <any decision>)` returns 255 of 255 artifacts with score `NaN`. The top 3 come from the hand-seeded OKC fixture sources (`deflock` and a person-named seed id; cf. F-376) | recorded-execution; `json/recommender_probe.json` |

**Verdict on U-003.7.** The page does not malfunction. It is **structurally unable to show anything**, and its copy points
readers to the wrong remedy. P7-T3 in C2 was scored a success only because the empty state is honest. The design-centre
task P1-T2 ("when does it renew, what is my real deadline") fails at the data layer.

---

## 2. Pipeline trace — why it is empty

```
connectors (procurement: SAM.gov notices, USAspending, agenda tenants; accountability: OpenStates)
   └─ claims in the spine (typed `deployment`, no jurisdiction)             ← data exists (§3)
inference / reconcile ── no watch derivation; tasks.detect never runs `contract_expiring` (catalog #10)
exports.spine_export.fetch_export_raw(EXPORT_QUERIES)   ← no "contract_watch" key  ✗  (root cause 1)
   ├─ _watch(raw) → []                          spine_export.py:1154-1160
   ├─ jurisdiction dossiers: termination = _UNKNOWN_TERMINATION             spine_export.py:1538-1542, 1561
   └─ analytics._decision_point(raw) → null     analytics.py:420-467 (reads raw["contract_watch"] at :434)
web data seam: getWatch() / getDecisionPoint()   data.ts:313-316, 789-797
web pages: watch.astro (empty states) · [jurisdiction].ics/.xml getStaticPaths → 0 paths · citations.txt → gap line
```

| layer | finding | class | evidence |
|---|---|---|---|
| export read | `EXPORT_QUERIES` (`spine_export.py:128-233`) has keys `source_names`, `entity_labels`, `research_tasks`, `evidence_artifacts`, `corrections`, `claim_weights` and `evidence_bindings`. It has **no** `contract_watch`. `grep -rn contract_watch` finds only `spine_export.py:1158`, `analytics.py:434` and `tests/exports/test_export_analytics.py:365,395,409` | **code (root cause)** | code |
| data model | `ContractWatchItem.termination` = {expiry, auto_renews, notice_window_days} (`watch.ts:40-56`). No predicate carries auto-renewal or a notice window: `predicates.yaml` has `contract_end_date`, `end_date` and a free-text `renewal_options` only. The agenda path builds a `Contract` with lifecycle `proposed`/`awarded` only (`procurement.py:2889-2905`) | data model | code |
| dossier | every jurisdiction dossier emits termination with every field `null` ("the spine holds no … termination … facts for a jurisdiction yet", `spine_export.py:1536-1542`) | data | code |
| detectors | `contract_expiring` (catalog #10, `local_group`, fires when `end_date` falls within N days) is registered but `run_detectors` only routes contradictions, coverage gaps and stale edges (`detect.py:291-357`) | code | code |
| eligibility | nothing is filtered out: there are no rows to filter | — | — |
| placement | agenda items and notices are typed `deployment` and carry no jurisdiction (live API). Jurisdiction attribution exists only for geolocated camera registries (F-320) | data | live-read |
| timeliness | `legistar`, `primegov`, `civicclerk` and `escribe` run **monthly** (`ops/cadence.toml:266-296`). Legistar has 3 verified tenants (`:272`). Agendas are typically published days before a meeting (**inference**; not measured here) | ops | code |

**Answer to "data, code or publication eligibility?"** Code first: the producer is missing. The data model is second: a
contract renewal has no inputs to derive a date from. Scope is third: the dated data SIG does hold is not a modelled watch
item. Eligibility plays no part.

---

## 3. What SIG already holds that a decision calendar could use

All counts below are from I1 (`data/source_coverage.csv`, GCS run rows) or from live API reads made in this session. The
spine was not queried (P3), so "how many upcoming items exist" is **unknown** until WX-01's read-only count query runs.

| kind | source(s) | cadence | what the claim carries (live read) | watch use |
|---|---|---|---|---|
| Federal solicitations | `sam_gov` (ingested-live; Σ650 claims over 4 runs; last run 2026-09-28) | weekly | `procurement_notice:sam_gov:3a91b64b…`: `notice_type` "Combined Synopsis/Solicitation", `posted_date` 2026-08-18, `response_deadline` 2026-08-25T17:00-06:00, `buyer` CBP, `document` = sam.gov opportunity URL (`curl/api_entity_notice.body`) | response deadline → **solicitation_deadline** |
| Municipal procurement portals | `procportal_austin_tx`, `procportal_sf_ca` (evidence.json) | per source | `procurement_notice:procportal_austin_tx:austin_tx:NA230000215` (search hit) | same |
| Council agendas | `legistar` (Σ142,740 claims), `primegov` (Σ462,932), `civicclerk` (Σ19,447), `escribe` (Σ160,267) | monthly | `agenda_item:legistar:seattle_wa:CB 121279`: `content_term` = `contract_notice`, `document` = Legistar matter URL. The meeting/intro date sits in the raw row (`"introduced"`, `procurement.py:2864`) and is **not** a claim | meeting date → **agenda_item** (needs a `meeting_date` claim) |
| Legislation | `openstates` (Σ13,690) | weekly | `bill_status`, `bill_status_date` predicates (vocabulary) | status/next action → **legislative_action** |
| Federal grants | `fema_hsgp_allocations`, `usaspending` (Σ77,674 claims) | monthly | `award_date`, `period`, `federal_award_id` | period end → **grant_period_end** |
| EU / FR procurement | `ted_eu` (Σ208,638), `decp_fr` (Σ18,990) | per source | notices, `place_of_performance`, `country` | deadlines/durations → **solicitation_deadline** / **contract_expiry** |
| Contracts | procurement connector `Contract` (`end_date`, `renewal_options`) and the P07.1 parser | — | no populated termination triple seen (dossiers all `null`) | **renewal_deadline** once parsed; **contract_expiry** with `end_date` only |
| Ordinances | `sunset_date`, `effective_from` (vocabulary); CCOPS sources (Seattle, NYC POST, Oakland…) | per source | not read | **ordinance_sunset**, CCOPS annual-report due dates (later) |

**Inference:** the most dependable near-term content is SAM.gov and municipal solicitation deadlines, plus agenda items
from the verified tenants. Renewal deadlines, the spec's headline feature (SIG-UI-014b), need contract-document extraction
(auto-renewal clause, notice window). The spine does not produce that today.

---

## 4. What "watch" should be for advocates, journalists and organizers

The users, from U-002 and C1's personas:
- **Local advocate** (design centre): "What is being decided about surveillance in my city or county, when, and by whom?
  What is my real deadline to comment, and what evidence should I bring?"
- **Investigative journalist**: "Which agencies are buying or renewing from vendor X in the next quarter? What changed
  since last month? Show me the documents."
- **Organizer**: "Put every upcoming decision in my state on our shared calendar. Tell our coalition when a new item
  appears. Let me hand volunteers a per-city list."

**Principles.**
- **W-P1: One decision date, typed and graded.** Every item has exactly one alert date and a `date_kind`: `deadline`,
  `meeting`, `derived_deadline`, `expiry`, `period_end` or `status_change`. It also has a `date_certainty`:
  - `stated` — read from a document;
  - `derived` — expiry minus the notice window, per SIG-UI-014b;
  - `upper_bound` — expiry known, notice window unknown, so the real deadline is **earlier**.

  An `upper_bound` date is never labelled a deadline.
- **W-P2: Absence is named.** Each place's page says which bodies and portals SIG monitors, and when each was last
  checked. "No items" is shown **with** that coverage statement, never alone (SIG-METRIC-010 spirit).
- **W-P3: Evidence first.** Every item links to the claims and the source document behind it. This uses J3's provenance
  panel and J4's "view at source" lane table; nothing is restated without a link.
- **W-P4: Neutral.** The recommender ranks only by directness, recency and dispute status (SIG-UI-027b). The "what you
  can do" text is procedural (the comment deadline, the meeting, how to request records), never persuasive.
- **W-P5: No subscriber data.** SIG holds no email list and no accounts (privacy, P16 spirit, Part VIII). Subscriptions
  are pull feeds; an RSS-to-email relay is documented as an option the reader controls.
- **W-P6: Two clocks, labelled.** Watch items can refresh daily between monthly releases (§7). Every page shows "watch
  checked <time>" apart from "data release <pub>", as J3's `/status/` page does.

---

## 5. Design

### 5.1 The watch item (`sig.watch-item/1`, emitted in `web/watch.json` v2 `sig/watch/2`)

| field | meaning | source |
|---|---|---|
| `handle` | human-readable, stable id: `W-<place>-<kind>-<slug>-<hash4>`, e.g. `W-usa-wa-seattle-agenda-cb-121279-7k2q` (the grammar is shared with tasks and evidence; K11 §3) | derived |
| `title` | plain-language sentence from a per-kind template, e.g. "Seattle City Council: agenda item CB 121279 (contract notice)" | template + labels |
| `kind` | `renewal_deadline` · `contract_expiry` · `solicitation_deadline` · `agenda_item` · `legislative_action` · `grant_period_end` · (later) `ordinance_sunset`, `oversight_report_due` | derivation rule |
| `date`, `date_kind`, `date_certainty` | the one alert date (W-P1) | claims |
| `timeline[]` | other dated facts: posted, intro, award, start, end, prior meetings | claims |
| `place` | K4 canonical place key + breadcrumb (country › state › county/city); `unplaced` is a data-quality bucket | resolution (§5.3) |
| `body` | approving/issuing body: council, agency or procurement office | claims (`buyer`, tenant) |
| `subjects` | linked entities: agency, vendor, product, contract, deployment (K2 entity pages) | claims |
| `technology`, `vendor` | matched technology class and vendor (from `content_term`/`matched_keyword`, never inferred from absence) | claims |
| `status` | `upcoming` · `today` · `recently_decided` (≤30 days past) · `superseded` (the date moved) · `withdrawn` | derived |
| `what_you_can_do` | procedural text per kind: "comment before <date>", "attend the <body> meeting", "request the contract (draft on task T-…)". Agent-drafted, operator-approved templates | template |
| `evidence[]` | claim ids, artifact/evidence handles and upstream document link (J3 §5.3 lane rule) | claims + J3 |
| `contested` | `true` if any claim on the item is in an open contradiction; the `≠` marker appears everywhere (SIG-UI-008) | contradictions |
| `tasks[]` | open research tasks on the same subject (K11 handles), e.g. "renewal terms unknown" | research_task |
| `first_seen`, `last_checked`, `source_ids` | provenance and freshness | runs |

### 5.2 Derivation rules (WX-01, pure Python `exports/watch.py`)

| kind | fires when (publishable, gated by `{PUB_CLAIM_GATE}`) | date | certainty |
|---|---|---|---|
| `renewal_deadline` | contract with `end_date`, `auto_renews = true` and `notice_window_days` | end − window (reuses `analytics._next_decision_date`, one derivation) | `derived` |
| `contract_expiry` | contract with `end_date`, renewal terms unknown | end_date | `upper_bound`; also emits a research task (K11, `contract_expiring`) |
| `solicitation_deadline` | `procurement_notice` with `response_deadline`, and the notice carries a reviewed surveillance `matched_keyword`/`content_term` | response_deadline | `stated` |
| `agenda_item` | `agenda_item` with a `content_term` from the reviewed agenda vocabulary and a `meeting_date` claim (new, WX-02) | meeting_date | `stated` |
| `legislative_action` | bill with a surveillance `bill_matched_keyword` and a scheduled action (hearing) or recent `bill_status_date` | scheduled date, else the status date as `status_change` | `stated` |
| `grant_period_end` | funding instrument with `period` end and a surveillance keyword | period end | `stated` |

**Windows.**
- Items are listed from `first_seen` until 30 days after their date; after that they move to the per-place history
  archive.
- The default list shows the next 90 days. Every future item remains reachable through the place and kind routes.
- `renewal_deadline` and `contract_expiry` are surfaced from **12 months** ahead, because many councils need two or three
  meeting cycles.
- Solicitations are surfaced from `posted_date`.

These windows are **inference**; the operator confirms them at D-K7-4.

### 5.3 Placement

The place is resolved in this order:
1. the claim's resolved jurisdiction;
2. the agenda tenant's registered jurisdiction, from `agenda_tenants.toml`, after the F-328/F-342/F-343/F-345 fixes;
3. the notice's buyer office or `place_of_performance`, mapped through the K4 key. A NUTS code is **not** an ISO 3166-2 code
   (`procurement_vocab.toml:124-130`).
4. otherwise `unplaced`.

Federal items sit under `usa` (K4 key `iso3166-1:US`) with the buyer office as the body. No place is guessed.

### 5.4 Pages (static, zero-JS baseline)

| route | content | size rule |
|---|---|---|
| `/watch/` | "Upcoming decisions": the next 90 days, sorted by date. Each row shows date (kind + certainty glyph), place, body, title, technology/vendor, evidence count, contested marker, and a link to the item. A header counts items by kind and place. A "Subscribe" block. A coverage summary ("SIG checks N agenda portals and M procurement sources; last checked …") | ≤50 rows per page; paginated `/watch/page/<n>/` |
| `/watch/place/<key>/` (+ `/watch/place/<key>/page/<n>/`) | same, for one place and its children (state → counties/cities). Coverage statement for that place: bodies monitored, last checked, known gaps (e.g. "no agenda portal registered for Travis County") | per K4 hierarchy |
| `/watch/kind/<kind>/`, `/watch/vendor/<slug>/`, `/watch/technology/<class>/` | one-dimension facet routes (J3 G-11 rule: facets are pre-rendered one dimension at a time) | ≤50 rows per page |
| `/watch/item/<handle>/` | the item: dates timeline, body, subjects (links to K2 entity pages and dossiers), J3 provenance panel for each claim, "view at source", "what you can do", related tasks (K11), the recommender list scoped to this item's subject (SIG-UI-027a, §5.7), citation block (release-pinned, J3 TX-13a), and "add to calendar" (a per-item `.ics`) | ≤150 KiB |
| `/watch/history/<key>/` | past items for a place (append-only archive) | paginated |
| `/watch/feeds/` | directory of every feed plus an OPML file of all place feeds, and a how-to for calendar apps, feed readers and RSS-to-email relays | — |
| dossier block | each `/dossier/<key>/` shows "Next decisions (N)", the first 3 items and a link to `/watch/place/<key>/` (fixes C2 P1-T4) | — |

**Enhanced version (only if K0 permits JS on this surface).** A filter/sort island over the per-place JSON
(`/watch/place/<key>.json`): multi-facet filtering (kind × technology × date range), a small "upcoming decisions" map
reusing K1's basemap, and a "subscribe to this filtered view" link that points at the nearest pre-rendered feed. The
no-JS baseline above stays complete (SIG-UI-050 pattern). K0 decides whether this is part of the `/search/` island (J3 G-11:
"no fourth island") or a new one.

### 5.5 Feeds

- **Scopes:** `all`, each K4 place (country, state, county, city), each vendor, each technology class, each kind.
- **Formats:** `.ics` (RFC 5545), `.rss` (RSS 2.0 with `atom:link rel=self`), `.json` (JSON Feed 1.1), plus
  `/watch/feeds/all.opml`.
- **Generation:** feeds are generated for **every** place in the dossier index, not only places with items, so a group
  can subscribe before the first item appears (D-K7-5).

**iCal rules.**
- `UID:<handle>@surveillancegraph.org`.
- `SEQUENCE` increments when the date changes. `STATUS:CANCELLED` when an item is withdrawn or superseded (calendar
  clients then remove it).
- `DTSTAMP` = the watch build time (UTC), never a fixture constant.
- All-day `DTSTART;VALUE=DATE`.
- `URL` = the item page.
- `DESCRIPTION` includes kind, certainty ("latest possible date — the real deadline may be earlier"), body, evidence link
  and the contested marker.
- `REFRESH-INTERVAL;VALUE=DURATION:P1D` and `X-PUBLISHED-TTL:P1D`.
- An empty calendar still carries one component (a UTC `VTIMEZONE`) so that it is RFC 5545-valid.

**RSS rules.**
- One `<item>` per watch item. `<link>` = the item page. `<guid>` = the handle URL.
- `pubDate` = `first_seen`, not the future decision date. The decision date goes in the title and the description.
- `lastBuildDate`, `<ttl>1440</ttl>` and `atom:link rel=self`.

**Serving.**
- nginx `types { text/calendar ics; application/rss+xml rss; application/feed+json json; }`, scoped to `/watch/`.
- `cache-control: max-age=3600`.
- Feeds sit behind the zero-egress host once J3 TX-11 exists. They are small (inference: <50 KB each).

**Email.** SIG sends none (W-P5). `/watch/feeds/` explains how to route a feed to email with a relay the reader chooses.
It does not endorse a vendor.

### 5.6 Empty and partial states (replaces the current copy; agent-drafted, operator to approve)

- Place with items: none needed.
- Place with monitoring but no upcoming items: "No upcoming decisions found for <place> as of <last_checked>. SIG checks:
  <bodies/portals>. Decisions in bodies SIG does not check will not appear here."
- Place without monitoring: "SIG does not yet check any agenda or procurement source for <place>." Then a link to the
  research task that would add one (K11 acquisition/coverage task), and, if the operator approves under D-K7-3, links to
  official portals or peer alert services (C5 L4).
- Until WX-01 ships, the interim copy must not say "research gap". Agent-drafted replacement: "The watch is not yet
  connected to SIG's procurement and agenda data. SIG holds some dated records (for example federal solicitations) that
  will appear here once it is." This is WX-07.

### 5.7 Evidence recommender repair (SIG-UI-027a; WX-05)

The recommender (`recommender.ts:252-271`) ranks every artifact it is given, whatever the decision's subject. On the live
file it returns 255 of 255 `NaN` scores (Q13) because `evidence.json` carries different values from what it expects:
- `directness` is `primary`/`secondary`, not D-codes;
- `currency` is empty;
- `capture_status` is `captured` (all rows), not a retrievability value;
- `subject_id` is empty (`spine_export.py:1163-1185`).

Repair:
1. The exporter emits, per (artifact, subject), the claim directness D-class of the predicates at issue (max over the
   artifact's claims), the currency C relative to predicate volatility, and retrievability from
   `capture_status`/`disappeared_observed_at`.
2. The recommender filters to artifacts that support claims about the decision's subject (or its contract/agency
   neighbourhood, one hop in K2's graph).
3. A build-time guard fails on any non-finite score.
4. The ranked list appears on `/watch/item/<handle>/`, not nationally.

`decision_point.json` becomes a per-item list, and the national "earliest decision" is kept only as a headline.

### 5.8 Relation to the research queue and evidence

- A `contract_expiry` item with unknown renewal terms opens a `contract_expiring` / "renewal terms unknown" research task.
  Catalog #10 exists but `detect.py` never runs it (NEW-15). The item links to the task and the task to the item.
- The item's evidence links go to K8's artifact and claim pages. A closed task links to the item it helped date.
- The research queue is **not** the remedy for an empty watch, so the "See the research queue" CTA is removed from the
  watch empty states.

---

## 6. Honesty and Part VIII checks

- Agenda item titles and SAM.gov text are verbatim public-record strings, but they can name people (for example
  appointments or "Chief X presentation"). Titles pass the J4 S-rules scrub. For kinds where a person could be named,
  only matched items (surveillance `content_term`) appear, and the title template uses the matter number plus the matched
  term when the verbatim title fails the person-name screen (Part VIII officer-naming posture). **Inference:** the rate of
  person-named agenda titles has not been measured.
- Solicitations and awards name vendors (organisations). That is allowed.
- "What you can do" never recommends a position (W-P4, SIG-UI-027b).
- Watch items come only from publishable claims (`{PUB_CLAIM_GATE}`, ADR-124). A withdrawal removes the item and emits a
  `STATUS:CANCELLED` event with no reason text (the J3 §9.2 pattern).

---

## 7. Cadence: the watch lane

The monthly release (G3 §7.2) is too slow for agenda items. Proposal (D-K7-2):
1. Watched agenda tenants and `sam_gov` move to a **daily** (agendas) or **twice-weekly** (SAM) ingest cadence. This is a
   scheduler change, so it needs an operator go.
2. A `sig-watch-publish` step runs in J3's status lane (TX-07; G3 §4.4 publish class **status**, allow-list extended to
   `watch/**`). It reads only publishable watch rows through a read-only view, renders the item/place pages and feeds with
   the release-page helpers, and publishes `watch/**`.
3. Pages carry "watch checked <time> · data release <pub>" (W-P6). Items that cite claims newer than the release say so
   and link to the release that will carry them.

The alternative is watch-only-at-release. It is simpler, needs no G3 amendment, and is monthly, so it cannot serve agenda
alerts. The recommendation is the lane. It adds no new service, only a status-lane step.

---

## 8. Draft requirements (provisional `SIG-WATCH-Dnn`; T1 numbers them or folds them into SIG-UI-026/027)

| id | requirement | acceptance criteria |
|---|---|---|
| SIG-WATCH-D01 | The export MUST produce watch items from publishable spine claims for every kind in §5.2 whose inputs exist. A watch surface MUST NOT depend on a raw key that no query fills. | a fixture spine with one contract (auto-renews, 90-day window), one SAM notice, one agenda item and one bill → 4 items with the expected dates and certainties; a unit test fails if any `raw.get(<key>)` read by a surface builder has no `EXPORT_QUERIES` producer (static check) |
| SIG-WATCH-D02 | Every watch item MUST carry one alert date with `date_kind` and `date_certainty`. An `upper_bound` date MUST NOT be labelled a deadline. | schema validation; copy test: pages never render "deadline" next to `upper_bound` |
| SIG-WATCH-D03 | Every item MUST link to its supporting claims and to an upstream document per the J3 §5.3 lane table. | crawl: 100% of item pages have ≥1 evidence link that resolves (200) |
| SIG-WATCH-D04 | Every place in the dossier index MUST have a watch page and feeds with a coverage statement (bodies monitored, last checked). An empty result MUST appear together with that statement. | route count == place count; no empty state without coverage text (HTML test) |
| SIG-WATCH-D05 | Feeds MUST validate: iCal (RFC 5545, including empty calendars), RSS 2.0 (with `atom:link self`) and JSON Feed 1.1. They MUST be served with `text/calendar` / `application/rss+xml` / `application/feed+json`. UIDs MUST be stable across builds and use the production domain. | `icalendar` + `feedparser` + a JSON-schema check in CI over every generated feed; live probe of the `content-type`; two builds → identical UIDs; date change → same UID and `SEQUENCE+1` |
| SIG-WATCH-D06 | Feed timestamps (`DTSTAMP`, `lastBuildDate`) MUST come from the watch build, never from a fixture constant. | build check: no `2026-08-20` literal reaches export-mode feeds; DTSTAMP == `watch.json.generated_at` |
| SIG-WATCH-D07 | The recommender MUST rank only artifacts that bear on the decision's subject, with finite scores computed from D/C/retrievability values the export emits. | property test: non-finite scores fail the build; subject-scoping test |
| SIG-WATCH-D08 | Agenda-derived items MUST reach the public watch within 24 h of the source publishing them for watched tenants. | status-lane heartbeat plus a canary tenant check (live, after WX-03) |
| SIG-WATCH-D09 | Each dossier MUST show its next decisions and link to its place's watch page. | crawl: every dossier has the block; counts equal the place page |
| SIG-WATCH-D10 | Empty-state copy MUST state the actual cause class (not connected / not monitored / none found). It MUST NOT call a pipeline gap a research gap. | copy lint over `empty.ts`; reviewer sign-off |

Spec amendments proposed for T1:
- **SIG-UI-026** is generalised from "every contract" to "every tracked decision point", keeping the contract fields.
- **SIG-UI-027** gains the vendor, technology and kind scopes and the format list.
- **SIG-UI-027a** gains subject scoping.

---

## 9. Acceptance journeys (agent walkthroughs after build; not user research, P4)

| id | persona | task | success |
|---|---|---|---|
| KJ7-1 | advocate | "What surveillance decisions are coming up in Seattle in the next 60 days?" | ≤2 clicks from home or dossier to `/watch/place/usa/wa/seattle-city-<geoid>/` (K4 display path). Each item shows date, kind, certainty, body and a source link. The coverage statement names the Seattle Legistar tenant and its last check |
| KJ7-2 | advocate (P1-T2) | "When does the TX ALPR contract renew and what is my real deadline?" | if known: a `renewal_deadline` with the derivation shown. If not: `contract_expiry` marked "latest possible date", plus the linked task "renewal terms unknown". Never a bare expiry as the deadline |
| KJ7-3 | journalist | "Which federal solicitations for ALPR/face recognition closed or open in the last 90 days?" | `/watch/kind/solicitation_deadline/` with the technology facet; each item links to sam.gov and to SIG's claim |
| KJ7-4 | organizer (P7-T3) | "Subscribe our coalition calendar to Texas" | a `webcal`/https `.ics` for `usa/tx` validates, imports in a desktop calendar (manual check) and refreshes daily. The feed exists even with 0 items |
| KJ7-5 | organizer | "Email me when a new item appears in my county" | `/watch/feeds/` explains RSS-to-email. SIG stores no address |
| KJ7-6 | any | open an item and "bring evidence" | the scoped recommender lists ≥1 artifact with a finite score, or states that none exist; the citation list downloads |

---

## 10. Round-11 ticket outline

Sizes follow J3: **S** ≈ half a fresh-context run, **M** one run, **L** split a/b at T3.

| key | title | size | scope | depends | live / gate |
|---|---|---|---|---|---|
| WX-07 | Watch and evidence empty-state truth fix | S | replace the "research gap" copy on `/watch/` and `/evidence/` with the actual cause; remove the research-queue CTA; add the static check "surface reads a raw key with no producer" | none; ships in the safety wave with K8 EV-01 | republish |
| WX-01 | Watch producer v1 | M | `EXPORT_QUERIES` watch reads (notices, agenda items, contracts, bills, grants); `exports/watch.py` derivation (§5.2); placement (§5.3); `sig/watch/2` + coverage block; gates; a read-only count query for sizing | PKG-06a/K4 place keys; TX-01 scrub (URLs, titles); ACT-07 attribution | — |
| WX-02 | Dated decision predicates | M | ontology: `meeting_date` (agenda), `auto_renews`, `notice_window_days`, `renewal_term_months` (Contract) + `make gen`; agenda normaliser emits `meeting_date` as a claim; parser layer extracts renewal clauses from captured contracts (P07.1) | ontology ADR (new predicates); WX-01 | hosted re-ingest of watched tenants: op go |
| WX-03 | Watch lane + cadence | M | daily/twice-weekly schedules for watched tenants and `sam_gov`; `sig-watch-publish` step in the status lane; `watch/**` allow-list; heartbeat | TX-07, ACT-05/PKG-04, G3 §4.4 amendment (D-K7-2) | scheduler change: op go |
| WX-04 | Watch pages + feeds v2 | L (04a pages and facets, dossier block, item page; 04b feeds, OPML, nginx types, UID/SEQUENCE/STATUS, validation in CI) | §5.4–§5.6 | WX-01; K4; K11 handle grammar; J3 TX-08a panel; TX-13a citations; K0 (enhanced island only) | republish |
| WX-05 | Recommender repair | S | §5.7; D/C/retrievability emitted per (artifact, subject); subject scoping; NaN guard | WX-01; TX-08a | republish |
| WX-06 | `contract_expiring` detector + renewal-terms tasks | S | run catalog #10 in `detect.py` over WX-01 contracts; task ↔ item links | WX-01; K11 RQ-01 | hosted detector run: op go |

**Order.** WX-07 first (safety wave). Then WX-01 → WX-05 → WX-04a in the first product wave, which gives SAM.gov/portal
solicitations and any contracts with `end_date`. Then WX-02 → WX-06 → WX-03 → WX-04b. Agenda alerts and feeds go live
with WX-03 and need the operator's go.

---

## 11. Operator decisions needed

| id | question | recommendation |
|---|---|---|
| D-K7-1 | Which decision kinds are in v1? | solicitations + agenda items + contracts with `end_date` (as `contract_expiry`); renewals as data allows; bills and grants in v1.1 |
| D-K7-2 | Daily watch lane between releases (G3 publish-class **status** extended to `watch/**`), or watch-only-at-release? | the lane; release-only cannot serve agenda alerts |
| D-K7-3 | May place pages with no monitoring link to official portals and peer alert services (alpr.watch, C5 L4/Q-C5-4)? | link to official agenda portals always; peer services per C5's link policy |
| D-K7-4 | Lead-time windows (§5.2) | as proposed; revisit after 2 months of data |
| D-K7-5 | Generate feeds for every place (valid but empty) or only for places with items? | every place, so subscribers can come early |
| D-K7-6 | Title policy for agenda items that may name people | verbatim title only when the person-name screen passes; otherwise matter number + matched term |

---

## 12. Risks

- **R1: False urgency.** A derived date that is wrong (for example a mis-parsed notice window) could make an advocate
  miss the real deadline. Mitigation: show the derivation, the certainty and the source on every item; `upper_bound`
  wording; a contested marker.
- **R2: Volume.** 785k agenda claims suggest many matched items (**inference**). Mitigation: match only reviewed
  surveillance terms; pagination; a per-place scope.
- **R3: Scraping load and robots.** Daily agenda scraping raises request volume. PrimeGov disallows robots platform-wide
  and the fetches proceed under GL-GATE-08 (`ops/cadence.toml:280`). Mitigation: daily runs only for the watched tenants;
  J3 run-log disclosure.
- **R4: Two clocks** (W-P6). Mitigation: explicit labels (J3 §14 lesson).
- **R5: Calendar pollution.** A cancelled or withdrawn item must leave subscribers' calendars. Mitigation:
  `STATUS:CANCELLED` + `SEQUENCE`, tested.

---

## 13. Interfaces and reproduction

**Interfaces.**
- **K0:** the enhanced island.
- **K1:** optional map of upcoming items.
- **K2:** entity pages for body, vendor and contract.
- **K4:** place keys and hierarchy.
- **K8:** evidence links.
- **K11:** handle grammar and `contract_expiring` tasks.
- **K13:** IA placement ("Watch" stays in the Explore nav).
- **J3:** TX-01 scrub, TX-07 status lane, TX-08 panel, TX-13a citation.
- **G3 §4.4:** publish class.
- **C5:** outbound-link policy and alpr.watch.
- **I rows:** agenda tenant registry fixes F-328/F-342/F-343/F-345; the F-335 vocabulary gaps limit which items match.

**Reproduction (read-only).**
- `tools/get.sh`: curl wrapper, 2 s pacing, UA without identity.
- `tools/run.mjs` + `scen_pages.mjs` / `scen_mobile.mjs`: Playwright, adapted from K12b.
- `tools/feedgen.ts` → `feeds/*.ics|*.xml`: esbuild bundle of `web/src/lib/watch.ts` and the fixture.
- `tools/validate_feeds.py`: `uv run --with icalendar --with feedparser`.
- `docker run --rm nginx:1.27.5-alpine grep -E '\bics\b' /etc/nginx/mime.types` (no match).
- The recommender probe: an esbuild bundle of `recommender.ts` run over `bucket/web/evidence.json`.
- `grep -rn contract_watch --include='*.py' --include='*.ts' .`

---

## 14. New findings (`findings/incoming/K7K8K11.csv`)

| id | title (short) | sev |
|---|---|---|
| NEW-1 | The watch has no producer: nothing fills `raw["contract_watch"]`, so watch.json, the decision point, feeds and citations are structurally empty | S1 |
| NEW-2 | Dated decision data (SAM deadlines, agenda items, bills, grants) exists but is not modelled; the renewal triple has no predicates; agenda meeting dates are not claims | S2 |
| NEW-3 | Agenda sources run monthly with 3 verified Legistar tenants, too slow for an upcoming-meeting watch | S2 |
| NEW-4 | Latent feed defects: `.ics` would be served as octet-stream; `@sig.example` UIDs; fixture DTSTAMP; no per-item links; an empty calendar violates RFC 5545 | S2 |
| NEW-5 | The recommender would rank all 255 national artifacts with NaN scores for any decision (vocabulary mismatch, no subject scoping) | S2 |
| NEW-6 | `/watch/` and `/evidence/` empty states blame a "research gap" and point to a queue that cannot fill them | S2 |
| NEW-15 | Records-request drafts are never published and the `contract_expiring` detector never runs (shared with K11) | S2 |

## 15. Limits

- The spine was not queried. The number of watchable upcoming items is unknown until WX-01's read-only count query runs.
- Agenda lead times, the rate of person-named agenda titles, and calendar-client behaviour with `application/octet-stream`
  were not measured. They are labelled inferences.
- The claim that no feed exists live rests on probes of the likely slugs and on zero routes generated from an empty
  `watch.json`. A bucket listing was not repeated (C1/ROUTES R24/R25 recorded 0 instances).
