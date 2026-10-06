# K9 — Sources table (was "data freshness") · operator ask U-003.9

Row **K9** of `META_PLAN.md` §6 Stream K (owner D, depends J3, J4). Written 2026-09-30 by Claude Code (Opus 5.5) in the
planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `921d2c0c`; every
code path cited is byte-identical to chain tip `b051732c`: `git diff --stat b051732c HEAD -- exports/ web/src db/ api/ ops/
connectors/ inference/ reconcile/ ontology/generated` is empty). Work window (`date -u`): **2026-09-30T21:31:15Z → see
footer**. `PD` = `docs/build/planning/2026-09-30-next-phase`. Companion note: `design/K10-source-pages.md` (U-003.10).
Findings for both rows: `findings/incoming/K9K10.csv` (NEW-1…NEW-8).

> **Design only (P3/P10).** Production was read, never written: 3 GETs of `surveillancegraph.org`, 3 GETs of public-bucket
> objects, one `gcloud storage ls` of the restricted run-row prefix and one `gcloud storage cat` of one 1,048-byte run row
> (keys and non-sensitive counts noted, no values copied). Nothing here is `engineered`, `staging-verified` or
> `live-executed` (P5). Every public sentence quoted below is **agent-drafted** and must be confirmed verbatim by the
> operator before it ships (META_PLAN §2). **This note extends J3; it does not redo it.** J3 §4 (source explorer) and J4
> (lanes, scrub rules S-1…S-14, costs) stay authoritative except where §2 below names a change.

**Operator ask (U-003.9, verbatim excerpt):** *"the 'data-freshness' section should have downloadable source data links per
source, ideally even the ability to browse and download versions of the data ingested for a particular source across time,
but bare minimum, the source list should have sortable columns and include links to downloadable data of most recent
ingested data for that source as well as additional ingestion metrics and metadata about what was ingested and how much,
and ideally also link to the 'ground truth' source URL or homepage or whatever for where we got this data from the
internet"*.

**Inputs read.** META_PLAN §3, Stream J and K blocks, §7/§7.1, §8.2; `feedback/OPERATOR_FEEDBACK.md` U-003;
`design/J3-transparency-design.md` (whole); `research/J4-redistribution-matrix.md` (whole) + `data/redistribution.csv`
(345 rows); `research/J1-exposure-inventory.md` §A.2–A.3, §B.1–B.4, §D; `research/J2-prior-art.md` §2.1, §2.5, §2.6, §4
PC-1/PC-2/PC-4/PC-6; `research/G1-ops.md` §1, §2 (G1-05, G1-07, G1-09), §3.4, §3.6; `research/I1-source-coverage.md` §1–§2;
`design/G3-release-model.md` §0, §3, §4, §5.3, §11, §12, §15; `findings/FINDINGS.csv` rows on freshness, sources and
downloads (F-08, F-106, F-120, F-133, F-146, F-280, F-354, F-359, F-360, F-369, F-184, F-196, F-04, F-318, F-321, F-330).
Code: `web/src/pages/data-freshness/[...sort].astro`, `web/src/lib/{data.ts:629-653,tables.ts}`, `web/lighthouserc.json`,
`exports/src/exports/shaping.py` (freshness: 95-107, 449-490, 650-680, 1283-1345, 1510-1625), `exports/src/exports/analytics.py:570-625`,
`inference/src/inference/freshness.py`, `reconcile/src/reconcile/weight.py:178-200`,
`ontology/generated/registry/predicate_registry.json`, `db/deploy/{ingest_run_completion,ingest_run_capture,rights_sources_lineage,rights_decisions}.sql`,
`ops/src/ops/{scheduled.py:455-575,run_completion.py:1-80}`, `ops/cadence.toml`, `connectors/src/connectors/data/{sources.toml,camera_registry_targets.toml,dot_511_targets.toml}`,
`connectors/src/connectors/{dot_511.py:625-645,flock_portal.py:23,188-229}`, `docs/build/runs/P31.2.md:150-172`,
`docs/build/reports/live_runs/` (file list + one record's key shape), spec SIG-METRIC-006/007, SIG-UI-034/037/050,
SIG-INGEST-030c.

**Evidence classes (P1).** `code` (file:line at HEAD) · `live-read` (this row's GETs and bucket listing, 21:34:25–21:36:06Z)
· `recorded-execution` (I1's local copy of all 387 run rows, `docs/build/logs/next-phase/I1/runs_concat.txt`, and I1's local
copies of the public `sites` files — read for key presence, digests and counts only) · `inference` (labelled).

---

## 0. Summary

**What exists.** `/data-freshness/` is a zero-JS, 178-row table of bare source ids with six columns (last successful run,
last content change, status, stale entities, volatility) and four pre-rendered sort routes (live-read: 80,321 B, 8,199 B
gzipped, 0 `<script>`). Every row says `ok · 0 · unknown` (F-08/F-120/F-133). It covers only the 178 sources that have
published *site* records (F-146), links nothing, and has no counts, cadence, licence, downloads or ground-truth links (F-360).

**What K9 specifies.** One **sources table** at `/sources/` that replaces `/data-freshness/` (301 redirects kept): one row per
registry source (342), 17 columns grouped into three pre-rendered **views** (Overview · Runs & freshness · Rights &
downloads), sortable ascending/descending on every column by plain GET links, filterable by single-dimension facet routes,
searchable by an A–Z index and find-in-page on a single un-paginated page (inference: ≈50–90 KiB transferred), and
exportable as `sources.csv` / `sources.json` with a Table Schema. A client-side enhancement (multi-facet filter, instant
text search, column chooser, "download this view") is specified as **additive** to the same HTML and is conditional on K0;
the no-JS table is mandatory whatever K0 decides (SIG-UI-037).

**Columns (§4):** source name → publisher → technology class · publisher type → geography → licence → redistribution
(derived status + raw lane) → lifecycle status → last successful run → last upstream change → last change in SIG's records →
cadence → freshness verdict (with real volatility and staleness) → published claims (+ subjects) → runs → errors/open
issues → download (latest derived extract, + raw where lane `raw-ok` and bytes exist) → ground truth (homepage + terms).

**One definition of "source" (§3).** A source is one row of the source registry (`sources.toml` ↔ `source_registry`). Every
displayed source count is the number of registry rows satisfying a **named** predicate. The table header shows one
**lifecycle partition** (each row in exactly one state) instead of J3's nested funnel, because the sets are not nested
(NEW-1): 178 = sources with published site records; 218 ("Independent sources") = sources with ≥1 publishable claim;
219 = distinct source ids in `evidence.json` (215 live registry sources + 3 unregistered seed ids + gated `deflock`); 208 =
sources with a GCS run row; 236 = `ingestion_permitted`; 342 = registered.

**Freshness fixed (§5).** "Status" becomes a **freshness verdict** computed from cadence (`on_time · late · overdue ·
last_run_failed · never_run · not_scheduled · one_time_load`); **volatility** is the source's predicate mix from the ontology
registry (for camera registries: SLOW 2 y for location/name, GLACIAL 10 y for jurisdiction) and is knowable today — only
*staleness* needs dated observations (NEW-2); "last content change" splits into **last upstream change** (upstream-declared
last-modified where the upstream exposes it, SIG-INGEST-030c, else a canonical *records digest*) and **last change in SIG's
records** (per-source slice hash across releases), because raw capture digests both churn without change and stay identical
while SIG's output changes (NEW-3).

**Downloads and version history (§7).** A **source version** is the source's per-release derived slice (sites and/or
statements), content-addressed and deduplicated on the zero-egress mirror; the per-source version index lists every release
the source appears in, with counts, sha256, size and added/removed/changed record counts; raw capture versions (Transitland
pattern: a new version only when content changes) are downloadable only for `raw-ok` sources whose bytes exist and pass the
Part VIII screen. **Cost:** ≤ ≈1 GB/year of new slice bytes after dedup at a monthly cadence (inference) → ≈ $0 on R2
(10 GB-month free tier; $0.015/GB-month beyond); raw-ok growth 0.1–0.7 GB/month (J4) → < $0.20/month by year 2; egress $0 on
R2 vs $0.12/GB on GCS direct (J4). Today, per-source history can only be reconstructed for site sources from the 3 restricted
snapshots + 1 public release, which carry the NEW-1/attribution defects (D-J3-10 recommends manifests only).

**Changes vs J3 (§2):** 12 named changes, chiefly: nested funnel → lifecycle partition; volatility is not a PKG-10 data-model
question; J3's NEW-3 digest rule needs a records digest; release pages show cadence rules, not "next run"; per-source extracts
must include **statements** slices (40 live non-site sources otherwise have nothing to download); single page instead of
200-row pages; three views instead of one wide table.

**Tickets (§12):** UX9-1 source universe + partition + counts (M, amends TX-02) · UX9-2 freshness semantics v2 (M, amends
TX-03/TX-04, connector change) · UX9-3 `/sources/` table page + exports + redirects (M, supersedes TX-05a index) · UX9-3e
client enhancement (S, after K0 ADR) · UX9-4 per-source extracts + version index (M, amends TX-10b; after TX-11).

**New findings (K9 side):** NEW-1 source sets not nested · NEW-2 volatility "unknown" is a code conflation · NEW-3 capture
digests are not an upstream-change signal. K10 adds NEW-4…NEW-8.

---

## 1. Ground truth that constrains the design

| # | fact | evidence | consequence |
|---|---|---|---|
| K-1 | Live `/data-freshness/`: 178 rows, 0 scripts, 80,321 B (8,199 B gzip -9), sha256 `db8130e5…`; summary "178 ok · Volatility classes: 178 unknown"; sort routes `/`, `status/`, `stale/`, `volatility/` | live-read 21:34:42Z; `web/src/pages/data-freshness/[...sort].astro:24-50` (code) | the pre-rendered GET-sort pattern works and is cheap; K9 generalises it |
| K-2 | Public `web/freshness.json` unchanged since the release (sha256 `c5a34382…`, same as J1/A1): 178 rows, fields `source, last_successful_run, last_content_change, status, stale_entity_count, volatility_class` | live-read 21:34:47Z | the table is frozen at `sig-2026-09-27-ce480ab1` while 387 run rows (latest 2026-09-30T12:03:13Z) keep landing (F-280) |
| K-3 | The freshness universe is sources with publishable claims on the 4 shaping predicates (`camera_latitude/longitude/jurisdiction/name`); "status" is the latest completion's status mapped to `ok/degraded/failing`, not a freshness judgement; `partial` and `quota_reached` count as successful runs but display as `degraded` | `shaping.py:95-107, 1283-1345, 1565-1590` (code) | non-site sources are invisible (F-146); "status" must be renamed and recomputed (§5.1) |
| K-4 | Volatility is voted only over **dated** observations on registry predicates; camera-registry claims are undated, so every row is `unknown`; yet all 4 shaping predicates have registry classes (latitude/longitude/name `SLOW` 2 y, jurisdiction `GLACIAL` 10 y); the registry types 184 predicates (77 IMMUTABLE, 49 SLOW, 22 MODERATE, 18 GLACIAL, 10 VOLATILE, 8 FAST) | `shaping.py:1305-1336` (code); `predicate_registry.json` (code) | NEW-2: volatility is displayable now; only staleness waits on dates (PKG-10) |
| K-5 | "Last content change" = latest completion with `claims_inserted > 0` | `shaping.py:1597-1602` (code); F-369 | J3 NEW-3; refined by K-6 |
| K-6 | Of 157 consecutive successful run pairs (same source, both with digests), 106 have identical capture-digest sets; ≥5 single/few-target sources changed **every** digest within 0.1–8.8 h with identical claim counts (e.g. `camreg_achd_id` 25 min apart); 12 pairs kept **identical** digests while emitted claims rose 7–12 % (e.g. `camreg_baltimore_md` 6,888 → 7,749; `dot_511_mo` 7,839 → 8,710) | recorded-execution (I1 copy of 387 run rows; digests compared, no bytes read) | NEW-3: raw digests false-positive (volatile bytes) and miss SIG-side change; both dates are needed (§5.4) |
| K-7 | Only Eyes on Flock keys change on an upstream-declared field (`data_last_updated`); ArcGIS/Socrata connectors do not read `editingInfo.lastEditDate` / `rowsUpdatedAt` | `flock_portal.py:23, 188-229`; grep over `connectors/src` (code) | SIG-INGEST-030c's pattern generalises; one metadata GET per target per run (inference) |
| K-8 | Source-id sets: registry 342 · permitted 236 · I1 ingested-live 218 · run-row prefixes 208 · `evidence.json` sources 219 · published-site sources 178 · "Independent sources" 218 = distinct `source_id` over publishable tier-0 weight rows | code (`sources.toml`, `analytics.py:590`); live-read (`evidence.json` sha256 `3df209d5…`, 255 artifacts; home + `/evidence/` text); `gcloud storage ls` 21:34:25Z (387 objects, 7,023,338 B, 208 prefixes) | §3 reconciles by id |
| K-9 | The sets are not nested (id-level): 178 ⊂ 219 (all 178 site sources are in `evidence.json`); `evidence.json` − live registry = {`bacy`, `okc-contract-c241032`, `osm`} (unregistered) + `deflock` (gated); live − `evidence.json` = {`fbi_cde_agency_registry`, `osm_element_history`, `primegov`}; run-row sources − live = {`ccops_sf`, `okc_procurement`} (runs, 0 claims); live − run-row = 12 sources; live − permitted = {`state_alpr_statute_inventory`} (one-time seed, `ingestion_permitted=false` by design) | set arithmetic over K-8 inputs + `data/source_coverage.csv` | NEW-1: a funnel misleads; a partition + named attributes does not |
| K-10 | Registry fields: 342 rows; `homepage_url` 341 non-empty; `[rights].terms_url` 241; `cadence` 191 (190 "monthly"); `rights_reviewed_by` = `maintainer (delegated)` 232, `counsel (HG-02)` 5; no `publisher` field (186 camera-registry/DOT sources carry a per-target `agency` string) | `tomllib` over `sources.toml`, `camera_registry_targets.toml` (223 targets / 173 sources), `dot_511_targets.toml` (14 / 13) (code) | ground-truth column is fillable now; publisher needs a field (NEW-7, K10) |
| K-11 | Schedules: `ops/cadence.toml` 70 per-source jobs (63 monthly, 6 weekly, 1 quarterly) + 8 monthly camreg batches (days 6–13, 151 members) = 221 scheduled, all permitted; 15 permitted sources unscheduled (OSM policy corpus, code repos, `gleif`, `wikidata_sparql`, `okc_council`, `agency_audit_export`, `declarationcamera_be`, …) | `tomllib` over `ops/cadence.toml` (code); J3 G-13 | cadence = `cadence.toml` truth; "not scheduled" and "one-time load" are explicit states |
| K-12 | Run rows: 324 of 387 (all started before 2026-09-24T23:49Z) have no `ingest_run_id`; `fetch_record.fetches` present on 58; outcomes ok 375 · error 8 · quota_reached 2 · content_drift 1 · politeness_refusal 1; duration median 81 s, p90 1,425 s, max 71,014 s; Σ `claims_added` 4,757,758 (≈ 2× the 2,423,200-claim watermark: emitted, incl. duplicates) | recorded-execution (key presence and counts only) | "runs" and "claims" columns must use completions (`claims_inserted`), never run-row `claims_added`; execution keying is K10's (NEW-4) |
| K-13 | Every published site inherits one jurisdiction per source (178 sources → 178 source×jurisdiction pairs over 236,994 rows); 58 sources (166,210 rows, 70.1 %, incl. the 154,528-row OSM-derived layer) map wholly to `unresolved`; `camera_jurisdiction` is the target's configured `state` | recorded-execution (I1 copies of the 12 public `sites` files); `dot_511.py:633-640` (code) | geography column = declared geography, labelled; per-point assignment is PKG-06's (NEW-8, K10) |
| K-14 | Budgets: public content pages 0 script bytes, ≤153,600 B transferred, Lighthouse perf ≥0.9, a11y 1.0; tables cap at 500 rows (`MAX_TABLE_ROWS`) | `web/lighthouserc.json`; `web/src/lib/data.ts:635-653` (code) | all 342 rows fit on one page (§6.3) |

---

## 2. Changes to J3's design (explicit)

| # | J3 location | J3 says | K9 changes it to | why |
|---|---|---|---|---|
| C-1 | §4.1 counting funnel | a nested funnel `registered → rights_reviewed_permitted → scheduled → ingested → published_claims → published_sites → independent_lineages` | **one universe (registry rows) + one lifecycle partition + orthogonal named attributes** (§3); non-registry ids are an anomaly list, never counted as sources | the sets are not nested (K-9, NEW-1); a funnel would print negative or impossible "differences" |
| C-2 | §4.2 index columns | one wide table of ~12 columns, ≤200 rows per page | **three pre-rendered views** of 17 columns; **one page** of all rows per view (paginate only if a build check measures > 150 KiB) | find-in-page and whole-set sorting are the best no-JS search; 342 rows fit (§6.3) |
| C-3 | §4.2 sort routes | "sort routes as plain GET links" | **ascending and descending** route per sortable column per view; absence tokens sort last in both directions; facet routes render the default sort only (no facet × sort product) | bounded route count (§6.1) |
| C-4 | §4.3 "Cadence & freshness" on the source page | "next scheduled run (day granularity)" on release pages | release-bound pages show the **cadence rule** ("monthly, day 6"); "next run" and the *current* freshness verdict appear only on status-lane renderings (`/status/…`, 6-hourly) | a release page's "next run" is in the past within a month; T-7 two clocks |
| C-5 | G-4, §4.6 item 3 | volatility "unknown" is a data-model question owned by PKG-10 | **volatility** (predicate mix from the ontology registry) ships now; only **staleness** waits on PKG-10's dating rule | K-4, NEW-2 |
| C-6 | §4.6 last para, D07 AC | last content change = last capture whose digest differs | two columns: **last upstream change** (upstream-declared last-modified, else a canonical records digest per target; a bytes-only change is "formatting change") and **last change in SIG's records** (per-source slice hash differs from the previous release) | K-6, K-7, NEW-3 |
| C-7 | §4.6 item 2 states | `on_time · late · overdue · never_run · not_scheduled · last_run_failed` | adds `one_time_load` (seeded or reference sources never meant to re-run, e.g. `state_alpr_statute_inventory`) and the flag `run_record_missing` (live data with no execution record, NEW-5) | K-9 |
| C-8 | §3.2 / §6.2 per-source bundle | `<comp>/by-source/<id>` slices of **sites** only | per-source extract = `sites` slice (if any) **and** a `statements` slice (always, for every published source) | 40 live non-site sources (legislation, agendas, procurement, `eyes_on_flock`) have no bulk presence (J4 §6) and would show no download |
| C-9 | §4.2 "publisher" | from `sources.toml` `name`/`notes` | a new registry field `publisher` (+ `publisher_type`, §8.6 vocabulary) seeded from target `agency` strings and I1's classification, operator-confirmed in batches | K-10, NEW-7 |
| C-10 | §4.2 status | lifecycle groups as sections | lifecycle is a **column and a facet**; sections replaced by the partition header (counts link to facet routes) | sorting across groups was impossible with sections |
| C-11 | §4.2 `/data-freshness/` "keeps its URL and becomes a sorted view" | same URL | `/sources/` is canonical; `/data-freshness/` and its 3 sort routes answer **301** to the equivalent `/sources/` view/sort (nginx map, G3 `labels.conf`-style include) | the operator renamed it; one canonical URL per view keeps citations stable |
| C-12 | §7.2 status page | a separate per-source status table | `/status/sources/` renders the **same row component** with the "Runs & freshness" view's columns from status-lane data, labelled with the status clock | one set of column definitions for both clocks |

Everything else in J3 §3–§9 (generation architecture, `ingest_run_report`, scrub, lanes, withdrawal, distribution host,
descriptor v2) is adopted unchanged.

---

## 3. One definition of "source", and the reconciliation

### 3.1 Definition (draft spec text, agent-drafted)

> A **source** is one row of SIG's source registry, identified by its `source_id`. A connector, an agenda platform tenant,
> a camera-registry endpoint, a capture host and a mirror are not sources; they are attributes or targets of a source. Every
> count of sources that SIG publishes MUST be the number of registry rows that satisfy a named, published predicate, and
> MUST be rendered with that predicate's name.

Consequences: the 793 agenda tenants are targets of 4 sources (`legistar`, `primegov`, `escribe`, `civicclerk`); the 223
camera-registry endpoints are targets of 173 sources; the 158 OSM slices are targets of `camreg_osm_surveillance`. Ids that
carry data but have no registry row (`bacy`, `okc-contract-c241032`, `osm`; J4 NEW-6) are **not sources**: until ACT-06 removes
or registers them, the table shows them in a separate "Identifiers with data but no registry row" box, never in a count.

### 3.2 The lifecycle partition (exactly one state per registry row)

Computed by one exporter function at the release's belief cut, in this precedence order (first match wins):

| state | predicate | today (best available; recompute at export) |
|---|---|---|
| `withdrawn` | a source-level withdrawal is recorded (e.g. D-J3-5's NEW-1 sources, if the operator decides) | 0 (7 candidates pending D-J3-5) |
| `published` | ≥1 claim from the source passes the publication gate in this release | ≈218 ("Independent sources", `analytics.py:590`) — the id list must be emitted; `evidence.json` suggests 215 live registry sources + `deflock` |
| `ingested_not_published` | ≥1 claim on the spine (or a completion with `claims_inserted > 0`) but none publishable | to compute (candidates: `fbi_cde_agency_registry`, `osm_element_history`, `primegov` are live but absent from `evidence.json`) |
| `permitted_not_ingested` | `ingestion_permitted = true` and no claim | 19 (I1; includes `ccops_sf` and `okc_procurement`, which ran and recorded 0 claims) |
| `gated` | `ingestion_permitted` false/absent, not refused, no claim | 101 (I1; `deflock` moves to `published` with a `rights_not_reviewed` flag if its claims pass the gate) |
| `refused` | the registry records a do-not-ingest decision | 4 |

**Orthogonal attributes** (each a facet and a named count, never a funnel step): `rights: permitted | not permitted`;
`schedule: scheduled | not_scheduled | one_time_load`; `run records: present | missing (NEW-5)`; `site records: yes | no`;
`raw lane` (J4); `attribution: passes | fails` (PKG-08 gate); `open issues ≥ 1`.

### 3.3 How the old numbers map (for the page's one-time explanatory note and the C6 copy)

| number shown before | where | what it actually counted | new name |
|---|---|---|---|
| 178 | home "sources tracked for freshness", `/data-freshness/` | sources with ≥1 published **site** record (all 178 ⊂ `evidence.json` sources) | "sources with published site records" (attribute `site records: yes`) |
| 218 | "Independent sources" on home / `/evidence/` | distinct sources over publishable tier-0 claims — not lineage-independent (C3 NEW-13) | "sources with published claims" (= state `published`) |
| 219 | `web/evidence.json` distinct `source` | 215 live registry sources + 3 unregistered ids + gated `deflock` | not a source count; the 4 extra ids appear in the anomaly box / `rights_not_reviewed` flag |
| 218 | I1 "ingested-live" | evidence of hosted claims (run row with claims, export rows, or committed live-run record) | `published` + `ingested_not_published` |
| 208 | run-row prefixes | sources with ≥1 GCS run row (incl. 2 with 0 claims; excl. 12 live sources) | attribute `run records: present` (GCS) |
| 236 | registry | `ingestion_permitted = true` (excl. the seed-only live source) | attribute `rights: permitted` |
| 342 | registry | all rows | **the universe** — the only headline "sources" number |

Header copy (agent-drafted; `<a>`…`<f>` are filled by the UX9-1 recompute, each a `<Figure>` with its definition, J3
§5.4): *"342 sources are registered. `<a>` have claims published in this release; `<b>` were ingested but nothing from
them is published yet; `<c>` are permitted but not yet ingested; `<d>` are waiting for a rights review; `<e>` were refused;
`<w>` were withdrawn from publication. `<f>` of the published sources contribute mapped sites."* With today's proxies:
a ≈ 218, c = 19, d = 101, e = 4, f = 178.

**Acceptance:** the partition sums to the registry row count; a CI check recomputes every header number from
`sources.json`; a crawl finds no source count outside a named-definition `<Figure>`; each anomaly id is listed by id.

---

## 4. The table

### 4.1 Columns

Values are **as of the release** (belief cut) unless the column says otherwise; the page header prints "as of release
`<label>` (data as of `<as_of_world>`)" (J3 T-7, G3 §3.1). Every cell is a value or a named absence token (J3 T-5).

| # | column (header, agent-drafted) | definition | source of truth | absence tokens | sort key | facet |
|---|---|---|---|---|---|---|
| 1 | **Source** | registry `name`, linked to `/sources/<id>/`; `source_id` beneath in small monospace (post-ACT-06 renamed ids only) | `sources.toml` | — | name, case-folded | A–Z letter |
| 2 | **Publisher** | the organisation that publishes the upstream data | new registry `publisher` (UX10-1) | `publisher_not_recorded` | publisher | `publisher-type` |
| 3 | **Class** | technology classes (PKG-07; I1's plain classes until then) + publisher type (§8.6 vocabulary) | registry + PKG-07 | `not_typed` | first class | `class`, `publisher-type` |
| 4 | **Geography** | declared country → subdivision (PKG-06a keys); multi-jurisdiction sources show "national" / "multi" | registry / target `state` / I1 `geographies` | `unresolved` (named, links to K4's bucket) | country, subdivision | `country`, `subdivision` |
| 5 | **Licence** | upstream SPDX short name; SIG basis marked "SIG basis — facts only" where different (J3 §4.2) | registry `[rights]` + J4 | `rights_not_reviewed` | SPDX | `licence` |
| 6 | **Redistribution** | two values: *derived:* `published` · `withheld pending rights review` · `not published`; *raw:* J4 lane `raw-ok · derived-only · link-only · restricted · unknown` | registry `[redistribution]` (TX-02, from `redistribution.csv`) | — | lane order raw-ok→unknown | `lane` |
| 7 | **Status** | lifecycle state (§3.2) + flags (`rights_not_reviewed`, `run_record_missing`, `attribution_failing`, `withdrawn`) | exporter | — | partition order | `status` |
| 8 | **Last successful run** | latest execution ending `ok`, `partial` or `quota_reached` (UTC minute) | completions + K10 execution table | `never_run`, `not_recorded (loaded before run records)` | time | — |
| 9 | **Last upstream change** | latest time the upstream's content changed (§5.4) | upstream-declared field, else records digest | `not_detectable (no digest)`, `formatting_change_only` | time | — |
| 10 | **Last change in SIG records** | the latest release in which this source's published records differ from the previous release (label + date) | per-source slice hash per release (UX9-4) | `first_release`, `not_published` | time | — |
| 11 | **Cadence** | the declared rule, e.g. "monthly, day 6", "weekly, Monday" | `ops/cadence.toml` (registry `cadence` fallback) | `not_scheduled`, `one_time_load` | interval | `cadence` |
| 12 | **Freshness** | verdict at the release as-of (§5.1) + volatility chip ("SLOW · 2 y") + staleness ("3 of 1,208 stale" or "not evaluable: 1,208 undated") | shared SLA function (ACT-02) + predicate registry + PKG-10 | verdict tokens (§5.1) | verdict severity | `freshness`, `volatility` |
| 13 | **Published claims** | claims from this source in this release; secondary: subjects (sites) | release `statements` / sites | `0` only when truly zero; `not_published` otherwise | count | — |
| 14 | **Runs** | executions recorded, with outcome split ("7 · 6 ok, 1 failed") | K10 execution table | `none_recorded` | count | — |
| 15 | **Errors** | failed executions in the 90 days before the as-of + open issues ("1 failed · 2 open issues") | executions + `issues.jsonl` | — | failures, then issues | `has-issues` |
| 16 | **Download** | latest derived extract: `csv.gz` link + size (parquet in the Rights & downloads view); raw link only if lane `raw-ok` ∧ bytes exist ∧ P8 screen passed | release data manifest (UX9-4) | `not_published`, `download_host_pending` (until TX-11), `withheld` | size | `downloadable` |
| 17 | **Ground truth** | homepage link (host shown as text) + "terms" link; full endpoint URL per S-6 on the source page | registry `homepage_url` (341/342), `[rights].terms_url` (241) | `no_upstream_url_recorded`, `terms_not_captured` | host | — |

Deliberately **not** columns: next scheduled run (status lane only, C-4), rights-review record, robots conduct, capture
counts (source page, K10), claims inserted over all runs (source page). **Never** shown: registry `notes`, `auth_model`,
`access_method`, `contact`, `robots_policy` (K10 §4 publish matrix; F-184).

### 4.2 Views (pre-rendered column sets)

| view | route | columns | purpose |
|---|---|---|---|
| Overview (default) | `/sources/` | 1, 2, 3, 4, 7, 12, 13, 16 | "what sources exist, are they current, can I download" |
| Runs & freshness | `/sources/runs/` | 1, 7, 8, 9, 10, 11, 12, 14, 15 | ingestion metrics (the old freshness page, enriched) |
| Rights & downloads | `/sources/rights/` | 1, 2, 5, 6, 16 (+ parquet, raw), 17 | licences, lanes, ground truth, files |

All 17 columns are in `sources.csv`/`sources.json`; a print stylesheet prints the current view. On narrow screens the
table scrolls inside its wrapper with a sticky first column (CSS only; existing `sig-table-wrap`).

### 4.3 Two clocks

The release view (`/sources/…`) is citable and frozen; its footer links `/status/sources/` ("runs since this release, updated
every 6 hours — not a citation", agent-drafted), which the status lane renders with the Runs & freshness columns plus
**Next run (day)** and the **current** verdict. No release page shows a status-lane value.

---

## 5. Freshness semantics v2

### 5.1 Verdict (replaces the "status" column)

One pure function `freshness_verdict(cadence, executions, at)` shared by the exporter, the status lane and ACT-02 alerting
(J3 §4.6 item 2), evaluated at the release `as_of_world` on release pages and at status time on status pages:

| verdict | rule |
|---|---|
| `on_time` | last successful run ≥ expected time − grace, where expected = previous cron fire before `at`; grace = 0.5 × interval |
| `late` | now > expected + 0.5 × interval with no successful run since |
| `overdue` | > 2 × interval since the last successful run |
| `last_run_failed` | the latest execution failed (even if within interval) |
| `never_run` | scheduled but no execution recorded |
| `not_scheduled` | permitted, no schedule, not a one-time load |
| `one_time_load` | registry marks the source as seeded/reference (new registry flag `one_time_load = true`, e.g. `state_alpr_statute_inventory`) |
| `not_applicable` | gated / refused / withdrawn |

"Silent success" (a successful execution emitting 0 records, SIG-ENG-021) is an **issue** and a flag, not a verdict.

### 5.2 Volatility (ships now; NEW-2)

For each source: the distribution of its **published claims** by predicate volatility class from
`ontology/generated/registry/predicate_registry.json`, displayed as the dominant class with half-life ("SLOW · 2 y") and
the full distribution on the source page. Predicates absent from the registry count as `unregistered_predicate (n)`. This
needs no dated observations. Fix in `shaping.py`: cast votes over **all** the source's claims, not only dated ones.

### 5.3 Staleness (PKG-10 owns the dating rule)

`stale n of m evaluable` where `m` = observations with an `observed_at`; otherwise `not evaluable: m undated observations`
— never "0 stale" (F-133). Whether a capture's `retrieved_at` may date a presence observation remains PKG-10's SIG-TIME
decision; K9 displays whatever PKG-10 emits, with the not-evaluable count always present.

### 5.4 Last upstream change vs last change in SIG's records (NEW-3; refines J3 NEW-3)

1. **Upstream-declared** (preferred, SIG-INGEST-030c generalised): per target, record the upstream's own last-modified
   value — ArcGIS layer `editingInfo.lastEditDate`, Socrata dataset `rowsUpdatedAt`/`dataUpdatedAt`, CKAN
   `metadata_modified`, HTTP `Last-Modified`/`ETag` (S-14 allow-list), Eyes on Flock `data_last_updated` (already read). One
   metadata GET per target per run (inference: +223 GETs per monthly camreg sweep). Shown as "Upstream last updated
   <date> (declared by the publisher)".
2. **Records digest** (fallback, detected by SIG): at flush, the connector computes `records_digest` = sha256 over the
   canonical (sorted, volatile-field-free) records emitted for that target; appended with the flushed mark (additive column
   on `ingest_run_capture` or a field of J3's `ingest_run_report`, PKG-12). "Changed" = `records_digest` differs from the
   previous flushed capture of the same target. A raw-digest change with an unchanged records digest is shown in capture
   history as `formatting change only`, and never moves the date.
3. **Last change in SIG's records**: the per-source slice sha256 differs from the previous activated release's (UX9-4);
   it moves on upstream change **and** on SIG-side change (connector, extractor, ruleset), which the source changelog
   (K10) explains. Until two releases carry slices, the column shows J3's fallback "last run that added claims (not a
   content-change measure)".

### 5.5 Cadence

Declared cadence from `ops/cadence.toml` (per-source or batch membership), rendered as a rule to **day** granularity
("monthly, day 6"); registry `cadence` only as fallback labelled "registry, not scheduled". Observed cadence (median
interval of the last 5 successful executions) appears on the source page. G1-09's live-scheduler drift flag appears on the
status lane only.

---

## 6. Sorting, filtering, search, pagination

### 6.1 No-JS baseline (mandatory; SIG-UI-037)

- **Sort:** every sortable column of a view has two pre-rendered routes: `/sources/<view>/sort/<col>/<asc|desc>/` (the view
  root is the default sort, name ascending). Header cells are links (`aria-sort` set on the active column). Absence tokens
  sort last in both directions; ties break on name. Route count ≈ (8 + 9 + 6) × 2 = 46 pages (inference).
- **Filter:** single-dimension facet routes `/sources/by/<dim>/<value>/` for `status`, `class`, `publisher-type`,
  `country`, `subdivision` (US/CA/AU/GB only), `licence`, `lane`, `cadence`, `freshness`, `volatility`, `downloadable`,
  `has-issues`; each renders the Overview view in default sort, with a facet menu showing counts (≈ 130 pages, inference).
  No facet × sort or facet × facet product (bounded route count); multi-dimension filtering is the enhanced layer or the CSV.
- **Search:** one un-paginated page per view → browser find-in-page; an A–Z jump list; a `<form method="get"
  action="/search/">` with `kind=source` (the `/search/` island's own no-JS fallback applies, SIG-UI-050).
- **Pagination:** none by default. A build check measures each view's transfer size; if any exceeds 120 KiB (headroom under
  150 KiB) the view paginates at 200 rows with sort preserved (`…/sort/<col>/<dir>/page/<n>/`).
- **Row identity:** `<tr id="src-<id>" data-source=… data-status=… data-lane=… …>` so fragment links work and the
  enhancement can read the DOM.

### 6.2 Enhanced (client-side; depends on K0)

Progressive enhancement of the **same** markup, one ES module (budget ≤ 15 KiB gzipped, inference) that: sorts on any
column in place; filters by several facets at once (chips); filters by free text over name, publisher, geography and id;
chooses columns; keeps state in the URL (`?q=&status=&lane=&sort=col:dir`) so filtered views are linkable; offers
"download this view (CSV)" built from the visible rows. Without JS, or if the module fails, the page is exactly the §6.1
page. K0 options: **(a)** static core + islands → no script on `/sources/`; multi-facet filtering goes to the `/search/`
island (`kind=source` facets, J3's plan) and the table stays §6.1; **(b)** progressive enhancement everywhere → the module
ships on `/sources/` under the K0 budget; **(c)** app shell for explore surfaces → the sources explorer lives in the shell,
`/sources/` (§6.1) remains the canonical, printable, citable page; **(d)** SPA → rejected by SIG-UI-037 unless the no-JS table
is kept. The ADR from K0 must name `/sources/` explicitly if (b) or (c).

### 6.3 Size (inference)

Live page: 178 rows × 6 columns = 412 B/row raw, 8.2 KB gzipped. Overview view: ≈ 1.0–1.4 KB/row raw (links, chips) × 342 ≈
350–480 KB raw, ≈ 50–90 KiB gzipped (less repetitive than today). DOM ≈ 342 × 8 cells + links ≈ 4–5k nodes (Lighthouse
flags > 1,500 as a diagnostic; perf score must stay ≥ 0.9 — the build-time check decides pagination).

---

## 7. Downloads per source per release, and version history

### 7.1 What exists today

| artifact | where | scope | versions retained | public? | size (source) |
|---|---|---|---|---|---|
| OCFL raw captures | `gs://…-sig-restricted/evidence/captures/` | 350 objects, 45 sources; 349 of 6,144 recorded digests have bytes | all since 09-25 (100 %), none before; bucket unversioned, no retention policy (G1-05) | no | 73.4 MB (J4 §6) |
| GCS run rows | `…-sig-restricted/ops/runs/<source>/<date>/<ts>.json` | 387 rows, 208 sources, 2026-09-16 → 2026-09-30T12:03:13Z | all (write-once by convention only) | no | 7,023,338 B (live-read) |
| Committed live-run records | `docs/build/reports/live_runs/*.json` | 90 records, 2026-09-16 → 09-19 | in git | repo only | small |
| DB completions / capture marks | `ingest_run_completion` (301 backfilled + live), `ingest_run_capture` | per execution / per target | append-only (triggers) | completions granted to `sig_read_public`, unexposed | — |
| Public release | `gs://…-sig-public/` | `sig-2026-09-27-ce480ab1`, 132 artifacts, per **compartment** (sites rows carry `source_id`) | 1 | yes (unlinked, F-354) | 1.05 GB |
| Prior releases | `…-sig-restricted/exports/national/` | 2026-09-24 × 2, 2026-09-27 | 3 | no | 2.96 GB |
| P32.13 release tree | built, undeployed | records/dossiers | 0 deployed | no | ≈ 2.0 GB, 475k files |
| **Per-source slices** | — | **none exist** | — | — | — |

So today a per-source "version" can only be *filtered* out of a compartment file (site sources only; `source_id` column),
giving at most 4 historical versions (3 restricted + 1 public) that carry the NEW-1 and attribution defects (J4 NEW-1/NEW-3).
Non-site sources have no bulk version at all.

### 7.2 The model

- **Source version (derived)** := the source's slice in one activated release: `r/<pub>/data/by-source/<id>/sites.{parquet,csv.gz}`
  (if any sites) + `statements.{parquet,csv.gz}` (always, C-8), with `datapackage.json` (per-source resource list),
  `ATTRIBUTION.txt` rendered from the registry (J3 T-4), sha256 per file. The slice is **content-addressed on the mirror**
  (`exports/push.py` content-hash keys): an unchanged slice in a new release is a new *listing entry* pointing at the same
  object — zero new bytes.
- **Version index** `r/<pub>/transparency/sources/<id>/versions.json` (`sig.source-versions/1`): one entry per activated
  release containing the source — release label + publication id, `as_of_world`, rows (sites), claims (statements), files
  (name, format, bytes, sha256, mirror URL), and vs the previous entry `added / removed / changed` record counts (from
  J3 TX-14's id-level diff, filtered by source) and `changed: true|false`. Prior (pre-Round-11) releases appear as
  **manifest-only** entries per D-J3-10 (counts + sha256, "not republished — reason"), unless the operator chooses D-K9-2 (b).
- **Capture versions (raw)** — Transitland pattern (J2 §2.5): per target, a new version only when the records digest (or,
  for byte-faithful formats, the raw digest) changes; each lists `retrieved_at`, digest, bytes, media type; **download**
  only if lane `raw-ok` ∧ bytes retained ∧ P8 screen passed (J3 §5.3/§6.9); otherwise "metadata only — <reason>".
- **"Latest"** := the source's version in the latest activated release. It is **not** "the latest run's data": between
  releases, runs land on the spine without passing the release gates (publication, attribution, withdrawal barrier, scrub).
  The table says so (agent-drafted): *"Latest released data (release `<label>`). N runs have completed since; their data
  will appear in the next release."* (N from the status lane on `/status/sources/`.) Interim per-source extracts are
  D-K9-1.
- **Download column** links the latest `csv.gz` (size shown); the Rights & downloads view adds parquet and raw; the source
  page (K10) lists every version.

### 7.3 Retention

- Release slices: immutable forever in the release namespace (ADR-132 / G3), except withdrawal (tombstone + mirror delete +
  purge, J3 §9.2). Per-source slices shrink withdrawal blast radius (J3 §9.2).
- Raw-ok public captures: kept for as long as the source is published; withdrawal deletes them.
- Restricted OCFL captures and run rows: evidence — keep indefinitely; adopt G1-05 (versioning + noncurrent 90 d on
  `sig-restricted`, then a dedicated evidence bucket with a retention policy). Cost is immaterial (73 MB + 7 MB).
- Version index: append-only across releases (each release's `versions.json` is a superset of the previous one's).

### 7.4 Cost (inference unless cited)

| item | size | growth | storage cost | egress |
|---|---|---|---|---|
| per-source slices, all sources, one release | ≈ 60–80 MB (J3 §10) + statements slices ≈ 80–200 MB (J3 §3.2 estimate for 2.42 M claims) | only changed slices add bytes: at a monthly cadence ≈ 20–80 MB/release → ≤ ≈ 1 GB/year | R2 free tier 10 GB-month; beyond $0.015/GB-month (J4 WQ2) → ≈ $0 | R2 $0; GCS direct $0.12/GB (median slice 0.55 MB all formats ≈ $0.00007; OSM 562 MB ≈ $0.067 per download, J4 §7) |
| raw-ok capture versions | ≈ 35 MB today (J4) | 0.1–0.7 GB/month (J4 §6) | < $0.20/month by year 2 | R2 $0 |
| object writes per release | ≈ 342 × 4 files + indexes ≈ 1.5k objects | per release | ≈ $0.01 (R2 Class A $4.50/M; GCS $0.005/1k) | — |
| worst case (scraper loops every version) | — | — | — | bounded by R2 $0 egress + per-IP limits (J3 §6.8); on GCS direct J4's abuse row ≈ $2.8k/month — **no download link before TX-11** |

---

## 8. Table export (`sources.csv`, `sources.json`)

- Paths: `r/<pub>/transparency/sources.{csv,json}` (release-bound, in the descriptor's `transparency_root`, J3 §3.4), linked
  from every view as "Download this table (CSV · JSON)"; `sources.json` is J3's `sig.transparency-sources/1` extended to
  `sig.source-row/1` (below); `sources.csv` is the same rows flattened, UTF-8, RFC 4180, with a Table Schema
  (`sources.schema.json`) generated from the exporter column registry (J3 §6.5; the build fails on an undocumented column).
- Row schema `sig.source-row/1` (one per registry row, 342): `source_id, name, publisher, publisher_type, technology_classes[],
  geography{country, subdivision, scope}, licence{spdx, sig_basis, share_alike, attribution_required}, redistribution{derived,
  raw_lane, lane_basis}, status{state, flags[]}, last_successful_run, last_upstream_change{at, basis}, last_sig_change{release,
  at}, cadence{rule, cron_day, basis}, freshness{verdict, evaluated_at, volatility{dominant, half_life, distribution},
  staleness{stale, evaluable, not_evaluable}}, published{claims, subjects}, executions{total, ok, partial, quota_reached,
  failed, missing_record}, errors{failed_90d, open_issues}, download{csv_gz{url, bytes, sha256}, parquet{…}, raw{…}|absence},
  ground_truth{homepage, homepage_host, terms_url, terms_capture{digest, retrieved_at}|absence}, page_url, as_of{world, belief,
  release}`. Absence tokens are strings from one enum.
- Size (inference): JSON ≈ 342 × 1.2–1.8 KB ≈ 0.4–0.6 MB (≈ 60–90 KB gzipped); CSV ≈ 150–250 KB.
- API parity (J3 §6.10): `/v1/releases/{pub}/sources` serves the same file; a parity test compares HTML ↔ JSON ↔ API.

---

## 9. Generation

1. **Exporter** (one REPEATABLE READ snapshot, J3 G-1): new `EXPORT_QUERIES` keys over J3's explicit-column views
   (`v_transparency_source`, `v_transparency_run`, `v_transparency_capture`) + K10's execution view; computes partition,
   verdicts (at `as_of_world`), volatility, staleness, versions; writes `sources.json/csv`, per-source `versions.json`;
   joins `sources.toml` + `ops/cadence.toml` + the lane table (files recorded by digest in the descriptor's
   `rights_registry_sha256`, G3 §3.2).
2. **Astro** (`SIG_DATA_SOURCE=export`) renders the 3 views + ≈ 46 sort routes + ≈ 130 facet routes into both the latest
   view `v/<pub>/` and the snapshot `s/<pub>/` (G3 §5.3); ≈ 180 pages × ≈ 60 KB ≈ 11 MB per rendering (inference).
3. **Status lane** (J3 TX-07) renders `/status/sources/` with the same row component from its own scrubbed read.
4. **Checks** (G3 V5/V6/V11): partition recompute; every header number = `sources.json`; 0 scripts on every no-JS route;
   transfer ≤ 150 KiB; every link resolves; no registry free-text field in any output (K10 §4).

---

## 10. Draft requirements (provisional `SIG-TRANSP` family, continuing J3's D01–D25)

| id | requirement (draft) | AC |
|---|---|---|
| SIG-TRANSP-D26 | SIG MUST define a source as a registry row and MUST publish every source count as the number of registry rows satisfying a named predicate; identifiers that carry data without a registry row MUST be listed as anomalies and never counted. | recompute check passes; crawl finds no unnamed source count; anomaly ids listed by id |
| SIG-TRANSP-D27 | The sources table MUST assign every registry row exactly one lifecycle state from a published precedence list, and MUST show the partition counts, which MUST sum to the registry row count. | Σ partition = rows in `sources.json` = registry rows |
| SIG-TRANSP-D28 | The sources table MUST offer the §4.1 columns in pre-rendered views, sortable ascending and descending by every sortable column through plain links, and filterable by single-dimension facet pages, all without JavaScript. | 0 `<script>` on every `/sources/**` no-JS route; every sort link returns rows in the stated order (test over `sources.json`); each facet page's rows = filter applied to `sources.json` |
| SIG-TRANSP-D29 | A source's freshness verdict MUST come from one function shared with alerting, evaluated at the release as-of on release pages and at status time on status pages, and MUST never be shown without its evaluation time. | alert and page call the same function (test); every verdict cell carries `evaluated_at` |
| SIG-TRANSP-D30 | Volatility MUST be derived from the ontology predicate registry over all of the source's published claims, and staleness MUST state its evaluable and not-evaluable counts; "unknown" and "0 stale" MUST NOT be shown for an unevaluable source. | 0 `unknown` volatility for sources whose predicates are all registered; fixture with undated claims renders "not evaluable: n" |
| SIG-TRANSP-D31 | "Last upstream change" MUST come from the upstream's declared last-modified value where available, else from a canonical records digest; a byte-only change MUST NOT move it; "last change in SIG's records" MUST be shown separately. | fixture: bytes change, records identical → date unchanged + `formatting_change_only`; records change → date moves; SIG-only change moves only the SIG column |
| SIG-TRANSP-D32 | Every published source MUST have a per-release derived extract (sites where applicable, statements always) with sha256, size, licence and registry attribution, and a version index listing every activated release containing the source, with added/removed/changed counts. | every `published` row has ≥1 download; `versions.json` entries = releases containing the source; unchanged slices share a content hash |
| SIG-TRANSP-D33 | The sources table MUST be downloadable as CSV and JSON with a generated Table Schema, and the API MUST serve the same rows. | `frictionless validate` passes; HTML = JSON = API for a sample of 20 sources |
| SIG-TRANSP-D34 | Release pages MUST NOT show values that depend on the reader's current time (next run, current verdict); those appear only on status-lane pages labelled with the status time. | crawl: no "next run" string under `/sources/`; status pages carry the status clock |

Amendments to J3 drafts (for T1): **D01** (index columns, "filterable without JavaScript") → superseded by D28; **D02**
(funnel) → replaced by D26/D27; **D07** (freshness) → narrowed by D29–D31; **D14** (downloads) gains D32's per-source
statements slice; **SIG-METRIC-007** amended: "last content change" → the two D31 dates; "current status" → the D29 verdict.

---

## 11. Acceptance tests (K9)

| id | test | layer |
|---|---|---|
| AT-K9-01 | Build from a fixture registry of 12 rows covering every lifecycle state + 2 unregistered ids → table has 12 rows, anomaly box 2 ids, partition sums to 12 | unit (exporter + Astro) |
| AT-K9-02 | For each view and each sortable column, the asc and desc routes list rows in the order computed from `sources.json`, absence tokens last | e2e |
| AT-K9-03 | Every facet route's row set equals the facet predicate applied to `sources.json`; facet menu counts equal row counts | e2e |
| AT-K9-04 | Lighthouse on `/sources/`, `/sources/runs/`, `/sources/rights/`, one sort route, one facet route: script 0, transfer ≤ 153,600 B, perf ≥ 0.9, a11y 1.0 | CI |
| AT-K9-05 | `/data-freshness/`, `/data-freshness/status/`, `/stale/`, `/volatility/` answer 301 to the mapped `/sources/` routes | edge probe (post-deploy) |
| AT-K9-06 | Volatility: a source whose claims are all on `camera_latitude/longitude/name/jurisdiction` shows `SLOW · 2 y` with distribution; a source with an unregistered predicate shows `unregistered_predicate (n)` | unit |
| AT-K9-07 | Upstream change: replay two captures with identical records but different bytes → `formatting_change_only`, date unchanged; a records change moves the date; an ArcGIS `lastEditDate` wins when present | unit (connector + exporter) |
| AT-K9-08 | Every `published` source has a `csv.gz` download that resolves (200 on the mirror), whose sha256 matches `versions.json`, and whose `ATTRIBUTION.txt` equals the registry text | e2e + integrity |
| AT-K9-09 | Two consecutive fixture releases where 1 of 3 sources changes → `versions.json` has 2 entries for each; the 2 unchanged sources' second entry reuses the first entry's object key | unit |
| AT-K9-10 | `sources.csv` validates against `sources.schema.json`; HTML cell values equal CSV values for 20 sampled sources | CI |
| AT-K9-11 | No page under `/sources/` contains a registry `notes`, `auth_model`, `access_method`, `contact` value or the string `robots_policy`; the J3 secret scan passes | CI |
| AT-K9-12 | Journey (agent walkthrough, not user research, P4): "find a Texas camera source updated in the last month and download its data" completes without JS in ≤ 5 clicks; with the enhancement (if K0 allows) in ≤ 3 | journey |

---

## 12. Round-11 ticket outline (K9)

Sizes as J3 §12 (S ≈ half a fresh-context run, M one run, L split). Keys are provisional; S1/S2 merge them with J3's TX rows
(exactly-one ownership, P9).

| key | title | size | scope | depends | live / gate |
|---|---|---|---|---|---|
| UX9-1 | Source universe, lifecycle partition, counts | M | `sig.source-row/1`, partition function, anomaly list, recompute check, replace "178 sources tracked" / "Independent sources 218" copy (C6 wording) | TX-01, TX-02 (**amends**: funnel → partition), ACT-06 (seed/handle ids) | via republish |
| UX9-2 | Freshness semantics v2 | M | verdict function (shared with ACT-02), volatility over all claims, staleness counts, `one_time_load`, upstream-declared last-modified for ArcGIS/Socrata/CKAN targets, `records_digest` at flush (additive column), slice-hash SIG change | TX-03/TX-04 (**amends**), PKG-10 (dating rule), PKG-12 (telemetry), UX9-4 for the SIG-change column | connector roll — op go (hosted image) |
| UX9-3 | `/sources/` table page | M | 3 views, asc/desc sort routes, facet routes, A–Z, partition header, anomaly box, `sources.{csv,json}` + schema, `/data-freshness/**` 301 map, Lighthouse URLs, status-lane row component | UX9-1, UX9-2; **supersedes TX-05a's index**; TX-07 (status lane) for C-12 | republish — op go |
| UX9-3e | Client enhancement for `/sources/` | S | the §6.2 module, URL state, download-this-view, budget test | **K0 ADR** (options b/c); UX9-3 | republish |
| UX9-4 | Per-source extracts + version index | M | `by-source/<id>/{sites,statements}`, per-source `datapackage.json` + `ATTRIBUTION.txt`, content-addressed push, `versions.json`, per-source diff filter of TX-14, download column wiring, manifest-only prior releases | TX-10b (**amends**), TX-11 (mirror), TX-14 (diffs; second release), D-J3-5, D-K9-2 | mirror writes — op go |

**Order:** UX9-1 → UX9-2 (code; its connector change rides the next image roll) → UX9-3 (ships with the first republish;
Download column shows `download_host_pending` until UX9-4) → UX9-4 after TX-11 → UX9-3e after K0. The K9 MVP (UX9-1 + UX9-3
with UX9-2's volatility/verdict half) needs none of G2 steps 1–7.

---

## 13. Operator decisions

| id | question | recommendation |
|---|---|---|
| D-K9-1 | Between releases, offer per-source "interim" extracts of newly ingested data (would need the publication, attribution and scrub gates in the status lane)? | **No.** "Latest" = latest release; use G3's early-cut trigger instead |
| D-K9-2 | Per-source history before Round 11: (a) manifest-only entries (D-J3-10); (b) re-derive per-source slices from the 3 restricted snapshots with corrected attribution, labelled "re-derived"; (c) omit | **(a)** — the snapshots carry NEW-1 rows and wrong attribution |
| D-K9-3 | Rename: nav label "Sources", canonical `/sources/`, `/data-freshness/` 301s | Yes |
| D-K9-4 | Confirm the lifecycle state names and the header sentence (§3.3, agent-drafted) | Confirm or edit verbatim |

Reuses (not re-asked): D-J3-1 (raw), D-J3-4 (host/ceiling), D-J3-5 (NEW-1 withdrawals), D-J3-10, D-J3-12 (description batches).

---

## 14. Risks

| id | risk | mitigation |
|---|---|---|
| R-K9-1 | A richer table amplifies wrong data (misattribution, axis swaps, handle ids, NEW-1 rows) | J3 R-1 ordering: ACT-06, ACT-07/PKG-08, D-J3-5, PKG-06b before UX9-3 goes public; `attribution_failing` flag shown until fixed |
| R-K9-2 | Readers treat "latest download" as live data | §7.2 wording; status link; G3 early-cut trigger |
| R-K9-3 | Upstream metadata GETs add load or trip robots/rate limits | one GET per target per run; same politeness path; skip when the platform exposes no field |
| R-K9-4 | A 342-row page fails the perf score | build-time measurement → 200-row pagination fallback |
| R-K9-5 | Route explosion if facets × sorts are later requested | enhancement layer or CSV; never pre-render products |

---

## 15. New findings (K9 side; rows in `findings/incoming/K9K10.csv`)

| id | title | sev |
|---|---|---|
| NEW-1 | The public source counts are not nested sets, so J3's counting funnel cannot reconcile them: 219 `evidence.json` ids = 215 live registry sources + 3 unregistered ids + gated `deflock`; 3 live sources (incl. `primegov`) are absent from it; 12 live sources have no run row; 2 run-row sources have 0 claims; 1 live source is not `ingestion_permitted` | S3 |
| NEW-2 | Freshness volatility "unknown" on all 178 rows is a code conflation, not a data gap: votes are cast only over dated observations, although every shaping predicate has a registry class (SLOW 2 y ×3, GLACIAL 10 y ×1); only staleness needs dates (refines F-133, J3 G-4) | S3 |
| NEW-3 | Capture digests are not an upstream-change signal: ≥5 sources changed every digest within 0.1–8.8 h with identical claim counts, and 12 run pairs kept identical digests while emitted claims rose 7–12 % (SIG-side change); J3 NEW-3's digest rule would mislabel both (refines F-369) | S3 |

Related, not re-raised: F-08, F-120, F-133, F-146, F-280, F-354, F-359, F-360, F-369 (J3 NEW-3), F-04, F-184, J4 NEW-5/NEW-6.

---

## 16. Limits and command log

- The partition's `published` / `ingested_not_published` split needs the exporter's id list (no DB read was made, P3); the
  §3.2 numbers are the best available proxies and are labelled.
- Page sizes, route counts and slice growth are inference from the live page and J3/J4 unit sizes; UX9-3/UX9-4 must measure.
- Digest comparisons (K-6) used digests only; which bytes changed was not inspected (no restricted object downloaded).
- Commands (read-only): `curl -A 'SIG-planning-K9K10/1.0'` × 6 (3 site pages, `web/freshness.json`, `web/evidence.json`,
  `manifest.json`; 21:34:42–21:34:49Z); `gcloud storage ls -l -r 'gs://zeta-medley-508121-u7-sig-restricted/ops/runs/**'`
  (21:34:25Z); `gcloud storage cat …/ops/runs/camreg_achd_id/2026-09-19/2026-09-19T07-09-57+00-00.json` (21:36:06Z; key shape
  only); `tomllib` over `sources.toml`, `cadence.toml`, target files; Python over I1's local run-row and `sites` copies.

Work window closed 2026-09-30T21:53:36Z (`date -u`). Findings file: `findings/incoming/K9K10.csv` (8 rows; NEW-1…NEW-3 from this row).
