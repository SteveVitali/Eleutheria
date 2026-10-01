# L2 — Measured quality of the live graph

Row **L2** of `META_PLAN.md` §6 Stream L (R, read-only). Run window **2026-09-30T21:59:42Z → 22:52:25Z** (`date -u`), in the planning
worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`). Author: Claude Code (Opus 5.5). `PD` =
`docs/build/planning/2026-09-30-next-phase`.

Outputs:

- this note;
- `PD/data/l2_metrics.csv`: 45 metrics (`L2-M01…M45`), each with a definition, value, method, data source, target and status;
- `PD/findings/incoming/L2.csv`: 17 findings (`NEW-1…NEW-17`, §8.2 schema).

Scratch evidence lives in `docs/build/logs/next-phase/L2/`, which is gitignored. It holds the scripts (`tools/`), the SQL text and result
of every database query (`db/sql/`, `db/results/`, `db/query_log.tsv`), every HTTP request (`fetch_log.tsv`), the derived tables (`out/`)
and the agent sample (`sample/`). Each file is hashed in `SHA256SUMS` (305 entries; its own sha256 is `c87159328f70…63a3a`).

**Evidence classes (P1).** `recorded-execution` covers my own scripts over downloaded files and my read-only queries. `live-read` covers
upstream GETs. `code` means file:line. `inference` is labelled where it is used.

**Part VIII / P14 / P16.** No person-level data is reproduced here. About 31 public source ids look like personal account handles (C3
NEW-2). They are written as `[handle id]` and never named, and the same goes for layer (target) ids that contain handles. One operator value
is an account handle; it is counted, not quoted. No secret value was printed or written. The database password lived only in process memory.
The User-Agent on every request was `SIG-planning-L2-…/1 (read-only)` and carried no personal identifier.

---

## Summary

**Data access.** All three sources were reachable read-only, and no roles or grants were created:

- **The public release, sha-verified.** `sig-2026-09-27-ce480ab1`; manifest sha256 `717aeb44…72d6`, the same as the A1 baseline. 37
  artifacts were read.
- **The restricted national exports.** Read-only copies of `web/map.json` and `density_bins.json`, plus the 2026-09-24 site parquets
  used for the id-stability check.
- **The hosted spine.** This used the path the API itself uses:
  - `cloud-sql-proxy` with the operator's ADC;
  - the existing `sig` login, whose password is the `sig-pg-password` secret;
  - `SET ROLE sig_read_public`, then `default_transaction_read_only=on` and `statement_timeout=60s`, each query inside
    `BEGIN READ ONLY … ROLLBACK`.

  44 queries were logged. Heavy tables were sampled with `TABLESAMPLE`. The public API was not needed.

**Headline measurements.** "Release" is the published graph. "Spine" is the stored graph.

| dimension | headline value |
|---|---|
| Duplicates | **13.5 %** of published points have a point from a different source or layer within 25 m. The resolver merged **3.75 %**. The exact-coordinate floor alone is 11.9 %. The single-linkage dedup ratio runs from 0.119 at 0 m to 0.224 at 25 m, 0.371 at 100 m and 0.511 at 250 m, and never flattens. |
| Identity | **5,278** camera subjects (2.3 %) are *several cameras collapsed onto one id* by non-unique upstream refs; 4,520 of them span ≥ 10 km. They are exactly the 5,290 points withheld as "conflicted". There is no cross-source agency identity: ≥ 171 of 200 EFF agencies also exist as Atlas subjects, with 0 links. |
| Agreement | Only **4.2 %** of points are corroborated by another source within 25 m. Dossier counts are row counts, overstated **up to 2.25×** (KY), and 1.71× for FL. **2** contradictions are recorded, against ≥ 5,278 subjects with divergent coordinates. The resolver labels every multi-claim value "uncontested". |
| Spatial | **4.6 %** of points assigned to a jurisdiction lie > 2 km outside it (2,807 of 61,193), and 3.9 % lie > 25 km outside. Of those: 562 axis swaps, 14 at (0,0), 5 sign flips. 15 dossiers have errors beyond 25 km. **92 %** of "unresolved" points sit inside a US state. |
| Types and roles | **77 %** of `traffic_camera` subjects are ALPR, police CCTV or enforcement cameras by their own registry target. **74 %** of camera subjects name a *publisher* as operator. 10,238 non-deployments are typed `deployment`. |
| Structure | 251,019 nodes and 41,962 distinct edges. **83 %** of nodes are isolated, the rest are stars (largest 26,840), and there is no multi-hop structure. 98.8 % of edges and 100 % of claims carry no valid time. 82.8 % of published sites are unlabeled. |
| Provenance | 100 % of claims have an evidence binding, but **0 %** of the 2.78 M bindings reach a byte-bearing capture, a locator or an excerpt. 28.4 % of published entities lack attribution where their licence requires it. 630 sharing rows credit "The SIG project" instead of EFF & MuckRock. |
| Freshness | 178/178 sources show "ok" and 0 stale because nothing is evaluable. SIG's "last content change" is its own insert time: the upstream edit dates of 10 of 10 sampled layers are 34 days to 5.7 years older. |
| Concentration | One republished OSM ALPR layer is **66 %** of all sites. The entity-weighted anomaly rate is 21 %, and 24 of 178 sources exceed 50 %. |

**Agent sample** (agent review, *not* human-verified; seed 20260930):

- **Sites.** 50 of 50 sampled published sites reproduce their upstream record exactly (the same ref, 0 m apart). This tests fidelity to
  the copy, not the existence of the camera. At the OSM origin, 29 of 29 reachable points have a surveillance node within 30 m. All 29
  are ALPR-tagged, although SIG types them `traffic_camera`.
- **Access edges.** 10 of 10 match the EFF NVLS column. They are dated 2020 for 2016–2017 records.
- **Operator edges.** 6 of 10 record the publisher as operator.
- **Procurement edges.** The parties check out: 6 confirmed, 3 inconclusive, 1 unverifiable. But **0 of 9** retrieved contracts concern
  surveillance.

**Conclusion.** The rows are faithful copies of their upstreams. The *synthesis* is weak: identity, deduplication, typing, roles, time,
contradiction and evidence binding are where the errors are. §4 lists 14 continuous checks that would have caught every problem above.

---

## 0. Data access

| path | used | how | notes |
|---|---|---|---|
| (1) Public release files | yes | `curl` of `manifest.json` and 36 artifacts: 12 `*/sites.parquet`, the `sig_graph/*.csv` files, all `web/*.json` including the 144 MB research queue, `datapackage.json`, `exclusions.json`, `provenance.ttl` | Every sha256 equals the manifest (`fetch_log.tsv`, tag `sha-ok`). The release has not changed since A1. |
| (2) Restricted national export | yes | `gcloud storage cp` (read-only) of `exports/national/2026-09-27T005153Z/{web/map.json, web/analytics/density_bins.json, manifest.json}` and of the 12 site parquets of `2026-09-24T154017Z` | Only aggregates appear here. `map.json` confirms 192,536 of its 232,625 assets are labelled with their UUID. |
| (3) Public API | no | — | Not needed, because the spine was readable. |
| (4) Hosted Cloud SQL `sig-pg` | yes | The existing path, set out below. | No new role, grant, user or secret. |

The path in row (4):

1. `cloud-sql-proxy --address 127.0.0.1` for `zeta-medley-508121-u7:us-central1:sig-pg`, authorised by the operator's ADC.
2. LOGIN `sig`, with its password fetched from Secret Manager `sig-pg-password` into process memory. This is the same credential the API
   uses.
3. `SET ROLE sig_read_public`. This is the API's role, with SELECT-only grants and the RLS tier ceiling at 0.
4. `default_transaction_read_only=on`, `statement_timeout=60s`, `BEGIN READ ONLY … ROLLBACK`.

The runner is `tools/q.py`. It refuses anything that is not SELECT, WITH, SHOW or EXPLAIN, and it logs each query's id, UTC start and end,
row count, status and SQL sha256. 44 queries ran, all `ok`, the longest taking about 19 s, between 22:02:22Z and 22:28:41Z. The instance is
`db-custom-1-3840`. The two tables above 1 GB, `resolution` (2.7 GB) and `claim` (1.6 GB), were read with `TABLESAMPLE SYSTEM(n)
REPEATABLE` where a full scan was not needed.

**Caveat (NEW-16).** No least-privilege *login* exists. The only credential is the owner login `sig`, and read-only behaviour here depended
on `SET ROLE` and read-only transactions. `ingest_run_capture` and `entity_identity_key` are not granted to `sig_read_public`, so they were
not read.

**Two populations.** The spine is live: 2,514,683 current claims at 22:05Z. The release is a 2026-09-27 cut: 2,423,200 claims and 232,625
site entities. Every metric names which one it uses.

---

## 1. Method

The scripts are in `docs/build/logs/next-phase/L2/tools/`. They run with a scratch venv (`.venv`, with shapely 2, scipy, duckdb, pandas,
networkx and pyshp) or the worktree `.venv` (duckdb, psycopg).

| script | what it does |
|---|---|
| `q.py` | The read-only query runner and logger described in §0. |
| `release_quality.py` | Loads the 12 site parquets (236,994 rows, 232,625 entities) and parses the coordinates and their decimals. It then runs point-in-polygon against Census `cb_2023_us_state_500k` and Natural Earth 10 m admin-0 and admin-1 (public domain, fetched with a hash in `fetch_log.tsv`). For each point it compares the location with the *intended* geography of its source, taken from I1's registry column in `PD/data/source_coverage.csv`, with a 2 km tolerance. It tests axis swap, sign flip and (0,0), and finds duplicates with a KD-tree on ECEF coordinates, `query_pairs` and union-find at 0.01–250 m. It also produces the per-source and per-jurisdiction tables and `pair_overlap.csv`. |
| `round2.py`, `round2b.py` | Cross-layer duplicate clusters, where a pair counts only if its source or upstream layer differs. Per-jurisdiction agreement. Freshness, from the release against `ingest_run_completion`. Attribution by compartment. Distance buckets for outside points. Where the "unresolved" points fall. |
| `graph_structure.py` | A networkx graph over every stored entity (`Q030`, `Q010`) plus every claim with an `object_entity` (`Q028`, 42,488 claims). It computes isolates, components and degree. |
| `per_source_summary.py` | Contribution and anomaly rate per source. The committed view is redacted. |
| `draw_sample.py`, `verify_sample.py`, `layer_counts.py` | The agent sample (§3). |

**Confidence.**

- **High.** Exact counts over complete data: the release files, full-table spine counts, the entity and identifier cross-tabs.
- **Medium.** Sampled spine estimates (TABLESAMPLE), polygon tests (generalised boundaries, plus I1's hand-assigned intended geography),
  technology classes (keyword rules over registry metadata) and distance-based duplicate estimates, where a multi-camera mount can be a
  true co-location.
- **Low.** The agent sample. n = 50 sites and 30 edges, an agent judge, no human (P4).

---

## 2. Results

Full definitions, targets and statuses are in `PD/data/l2_metrics.csv`. The tables below give the values and the evidence.

### 2.1 Duplicates and identity (M01–M11)

| metric | value | status |
|---|---|---|
| Exact-coordinate duplicate share (0.01 m) | 26,943 excess points / 227,335 = **0.1185**. Same-source 0.1064, cross-source 0.0199. | fail |
| Cross-layer duplicate share (a different source *or* upstream layer) | **0.1053** at 1 m · **0.1178** at 10 m · **0.1346** at 25 m · **0.1569** at 50 m | fail |
| Single-linkage dedup-ratio curve | 0.119 (0 m) · 0.135 (1 m) · 0.157 (5 m) · 0.173 (10 m) · 0.224 (25 m) · 0.292 (50 m) · 0.371 (100 m) · 0.511 (250 m) | warn |
| Resolver, latest run `camsite:5ddfe312…` (2026-09-26T19:58:58Z) | dedup 0.0375 · 8,724 merges · 11,106 auto-write pairs · 33,907 proposed awaiting review · 0 human decisions · 26,168 pairs held by `cluster_constraint:max_span` | fail |
| Subject-key collisions: subjects with ≥ 2 distinct current latitudes | **5,278** (2.27 %) · 4,520 ≥ 10 km · 604 at 1–10 km · a maximum of 242 claims on one subject | fail |
| Claim redundancy: exact (subject, predicate, value) repeats | **439,408 / 2,514,683 = 17.5 %** | fail |
| Same agency under several ids | ≥ 171 of 200 EFF agencies also exist as Atlas subjects (170) or Flock-portal slugs (71) · **0 links** | fail |
| Duplicate identifiers | 3 values map to 2 entities each | warn |
| Id stability, 2026-09-24 → 09-27 exports | 230,330 / 230,330 retained · 65 geometries changed | **ok** |

**What the curve means.** Even exact-coordinate duplicates make up 11.9 %, more than three times the resolver's merge rate. Beyond about 10
m, single-linkage starts chaining distinct cameras that stand close together. No distance threshold alone can define "the same site", so the
answer depends mostly on *which layers are copies of which* (§2.2). The resolver already lists 11 mirror lineages in its run summary, yet the
release still publishes every observation row: `n_sources` is 1 on all 236,994 rows.

**Collisions (NEW-1).** Distinct upstream records share a subject key `traffic_camera:<source>:<layer>:<ref>` when the chosen `ref` field
is not unique within the layer (`connectors/src/connectors/dot_511.py:541`, `:1005-1016`):

- IL DOT: 2,936 of 3,000 subjects (97.9 %).
- Two FL 511 republished layers: 1,964.
- DC street CCTV: 97.
- Surrey BC: 92.
- One Portuguese layer: 242 records under ref `0`.

In one case a single FL ref (`1000`) received two records 170 km apart in the same run (`Q039`). These subjects are the release's 5,290
"conflicted" points, which the dossiers describe as "evidence exists and disagrees". The evidence does not disagree: different cameras were
merged.

**Redundancy (NEW-7).** Every EFF Data Driven claim is stored twice. Procurement claims appear 2–3 times, and one camera ref was
re-inserted 58 times within one run. As a result `sharing_edges.csv` is 29.4 % duplicate rows (632 rows, 446 distinct), and "370
sharing_partner_degree" is really 185.

### 2.2 Cross-source agreement and mirrors (M05, M12–M14)

**Mirror double counting**, as the share of layer A's points with a layer-B point within 25 m (`out/pair_overlap.csv`):

| A → B | share |
|---|---|
| OSM ALPR "nationwide" republish → OSM DeFlock republish (both are the same source id, `camreg_osm_surveillance`) | **0.695** (13,238 / 19,044) |
| Nottingham layer ↔ Mark43 layer | 0.998 |
| Toronto ↔ CoT GeoHub | 0.975 / 0.935 |
| MD open data → Esri dashboard / → MD CHART (DOT 511) | 0.942 / 0.865 |
| KY 511 → Louisville LOJIC | 0.819 |
| UCSD-published layer → PennDOT | 0.782 |
| 7 layers ingested twice under two target ids (UCSD, MD open data, NZTA ×3, KY 511, one `[handle id]`) | **1.000** |
| DeFlock republish vs GA 511 (a genuinely independent pair) | 0.002–0.05 |

**Corroboration.** Only **4.2 %** of published points have a point from a *different source* within 25 m. The resolver's own summary counts
274 independently corroborated multi-record sites against 6,237 with a single lineage.

**Dossier inflation**, as published rows divided by distinct points after a 25 m cross-layer union (`out/jurisdiction_agreement.csv`):

| dossier | ratio |
|---|---|
| KY | **2.25×** (839 → 373) |
| NZ | 2.08× (1,060 → 509) |
| FL | 1.71× (8,001 → 4,692) |
| MD | 1.46× |
| DC | 1.42× |
| GA | 1.26× |
| MO | 1.24× |
| TX, IA, AU-QLD, MA, SA | at most 1.01× |

**Contradiction recall (NEW-2).** The spine holds **2** contradiction rows. In a 10 % sample of `resolution`, 19,121 current resolutions
consider more than one claim, and **all** of them are `uncontested` with empty `dissenting_claims`.

A 3 % sample checked whether those considered claims actually agree:

| predicate | multi-claim resolutions that differ |
|---|---|
| `camera_latitude` | 172 of 330 (at 4 dp, about 11 m) |
| `camera_name` | 106 of 272 |
| `camera_direction` | 60 of 124 |
| `camera_operator`, `camera_jurisdiction` | 0 |

A 10 % latitude sample puts 434 of 1,060 multi-claim resolutions ≥ 10 km apart. The resolver's contradiction detection does not engage on
this data at all.

### 2.3 Spatial sanity (M15–M20)

**Scope.** These are points whose jurisdiction is not `unresolved`: 61,193 geolocated. Each is tested against the polygon of its source's
intended geography, with 2 km tolerance.

| dossier | geolocated | > 2 km out | > 25 km out | dominant cause |
|---|---|---|---|---|
| CA | 6,139 | 947 | 908 | FDOT D5 layer registered as California; 838 of its points are in Florida. CalOES webcams in NV, ID and MT. |
| GB-ENG | 1,661 | 562 | 562 | The Nottingham layer's axes are swapped (it plots off East Africa). |
| BD | 447 | 447 | 447 | 432 points in Singapore. |
| TH | 2,109 | 159 | 155 | 138 points in Hong Kong. |
| IE-DL | 123 | 118 | 114 | Elsewhere in Ireland, not Donegal. |
| NZ | 1,060 | 54 | 54 | The "Wellington" layer lies in the UK (inference: a UK Wellington). |
| NL | 54 | 54 | 54 | In Belgium. |
| MO | 1,107 | 227 | 29 | Kansas City, KS side. Mostly legitimate border coverage. |
| OR / WA | 1,419 / 2,755 | 37 / 59 | 17 / 7 | Neighbouring states. |
| GA | 7,049 | 14 | 14 | 10 at (0,0), 1 sign flip, 3 elsewhere. |
| AZ / FL / DC / MA | — | 4 / 21 / 1 / 1 | 4 / 3 / 1 / 1 | Sign flips, (0,0). |
| AU-QLD, MD, KY, US, MN, IA | — | 48, 28, 17, 5, 2, 2 | 0 | Coastline or border; within 25 km. |

**Totals.** 2,807 points (4.59 %) are more than 2 km out and 2,370 (3.87 %) more than 25 km out. 2,079 are more than 1,000 km out. 21 of 54
dossiers are affected and 15 have errors beyond 25 km. Detectors: **562 axis swaps, 14 null-island points, 5 longitude sign flips.**

**Beyond C3 and I1 (NEW-12).** Polygons rather than bounding boxes add the Wellington, Donegal and Oosgis placements. They also separate
border spill-over (437 points within 25 km) from real errors.

**Null geometry.** 5,290 entities (2.27 %). All of them are collision subjects (§2.1).

**Unresolved points (NEW-13).** 166,210 entities (71.4 %) carry the jurisdiction `unresolved`. Of the 166,142 that are geolocated,
**153,050 (92.1 %) lie inside a US state** (53 states, DC and PR). The largest non-US groups are GB 3,377, TW 1,825 and BE 1,378.

**Precision.** The median is 7 dp. 1,681 points (0.74 %) have ≤ 3 dp, which is about 100 m or worse. 21,405 (9.4 %) have ≥ 12 dp, which is
spurious precision from reprojection. The `precision` column reads `full_precision` on every row.

**Storage.** Coordinates are stored as *text* literals (`camera_latitude`, `camera_longitude`). `value_geom` is NULL on every one of the
2.5 M claims (`Q012`), which works against SIG-GEO-001 and SIG-GEO-002.

### 2.4 Type sanity (M21–M24)

**Technology.** All 232,628 camera subjects are keyed `traffic_camera`. By the keyword class of their own registry target (id, agency,
notes; `out/type_by_target.csv`):

| class | subjects | targets |
|---|---|---|
| ALPR | **152,102** | 12 |
| CCTV / police | 23,989 | 84 |
| enforcement | 3,945 | 26 |
| traffic | 48,945 | 76 |
| unknown | 3,647 | 34 |

That makes **≥ 180,036 (77.4 %) mistyped**. Only 616 subjects carry `asset_type='ALPR'`, and that is a literal, not a Technology reference
as §8.6 requires. The exports have no technology column. This quantifies I1 NEW-9 (NEW-6).

**Entity types (NEW-8).** 10,238 entities typed `deployment` are really something else:

| kind | entities |
|---|---|
| procurement notices | 5,376 |
| contracts | 1,872 |
| agenda items | 1,364 |
| funding instruments | 1,079 |
| bills | 308 |
| jurisdictions | 195 |
| legal instruments | 30 |
| CCOPS reports | 9 |
| accountability events | 4 |
| records request | 1 |

The 17 typed entity tables (`jurisdiction`, `contract`, `product`, `technology`, `person`, `policy`, …) hold **0 rows**. The stored graph
has two entity types in practice: `deployment` (250,046) and `organization` (973).

**Operator role (NEW-4).** Of the 139 distinct `camera_operator` values, those that name a publisher, community or account cover **172,588
of 232,627 subjects (74.2 %)**. The largest is `OpenStreetMap contributors (republished man_made=surveillance nodes)` on 154,528. One value is
a personal account handle (not quoted). This conflicts with SIG-TRUST-003, which keeps publisher and operator as distinct roles, and
SIG-ONTO-028, which requires absence of an operator to be a first-class state.

**Other domain misuse.** `camera_status='false'` appears on 793 subjects. NVLS pool membership is encoded as a `configured_access` edge from
agency to vendor, with the partner set to the dataset's vendor constant. That is a documented modelling choice (`data_driven.py:620-650`,
ADR-113), but it is dated with the release date (§2.7).

### 2.5 Graph structure (M25–M31)

| metric | value |
|---|---|
| Nodes | 251,019: 250,046 `deployment`, 973 `organization`. 969 organizations are named via `sig.org.name`; 4 are unnamed "agency" stubs with no claims. |
| Edges (claims with `object_entity`) | 42,488 claims, 41,962 distinct. `camera_operator` 38,871 · `seller` 1,287 · `buyer` 1,127 · `recipient` 340 · `vendor` 200 · `configured_sharing_partner` 130 · `event_organizations` 7. The `relationship` table holds 130 rows, all `configured_access`, from one source. |
| Isolated nodes | **209,122 (83.3 %)** |
| Components of size ≥ 2 | 354. The largest has 26,840 nodes: the star around the OSM "operator" organization. Then 1,706 (WSDOT), 1,470 (UDOT), 1,329 (ACT JACS) and so on. 229 components have 2 nodes. |
| Degree | Maximum 26,839. 40,874 nodes have degree 1. 680 of 969 organizations have in-degree 1. **No path is longer than 2 hops**: every component is a star. |
| Unlabeled | 192,536 of 232,625 published sites (82.8 %) have no label; `map.json` uses the UUID. In the spine, 189,289 camera subjects lack `camera_name`. No organization is unnamed. |
| Orphans | 5 entities with no claim in either direction. The 969 organizations have no claims of their own; only their name identifier. |
| Undated | 41,988 of 42,488 edge claims (98.8 %) have neither valid time nor `observed_at`. |
| Historical-only | 130 of 130 access edges rest on one 2016–2017 dataset. |

### 2.6 Provenance completeness (M32–M36)

| metric | value | status |
|---|---|---|
| Claims with an evidence binding (`claim_evidence`, role `establishes`) | 2,514,683 / 2,514,683 | ok |
| Bindings whose capture has bytes and an upstream URI | **0 / 2,782,187** | fail |
| Bindings with a locator, excerpt or `extraction_id` | 0 / 0 / 0 | fail |
| What the bindings point at | 285 synthetic captures (`capture_method=connector`, `byte_size=0`, no http URI), one per source run | fail |
| Captures with an http URI and bytes | 27 of 325, all licence or terms pages, none bound to a claim | fail |
| Artifacts with an http URL | 27 of 255. The public `evidence.json` has 0 of 255 http permalinks. | fail |
| Published entities missing required attribution | **66,138 of 232,625 (28.4 %)**: public_record 39,921, operator_accepted 21,682, dot511_ccbysa2 3,000, ogl_uk3 1,368 and others | fail |
| Rows without a terms URL | 228,537 (96.4 %) | fail |
| Misattribution | 3,272 site rows say "DeFlock community map" (J1 NEW-2). **630 of 632 sharing rows** credit "© The SIG project" where the upstream is EFF & MuckRock (NEW-14). | fail |
| Spine `source_registry` | 0 of 220 rows carry `homepage_url`. 167 of 215 connector sources point at a rights record with no attribution text. | fail |

`ingest_run_capture` holds the per-target URL and digest (J1: "350 real captures"). `sig_read_public` cannot read it, so it was not
measured.

### 2.7 Freshness (M37–M40)

- **The release.** `freshness.json` shows 178 of 178 `ok`, 178 volatility `unknown` and 0 stale. At the cut, the last content change was a
  median 7 days old (maximum 9). Nothing can be evaluated: **all 2,514,683 claims have an unbounded `valid_period`, and 2,334,331 (92.8 %)
  have `observed_at` NULL.**
- **What "last content change" means.** It is SIG's insert time. For the 10 sampled layers that expose `editingInfo`, the upstream last edit
  is older than SIG's date by 34 days to 5.7 years:
  - the DeFlock republish that SIG ingests: 2026-08-22
  - the ALPR "nationwide" republish: 2025-04-17
  - UDOT: 2021-03-29
  - GDOT: 2020-12-29

  14 of the 15 sampled layers still hold exactly the feature count recorded at enumeration (WSDOT has +1), so the republished mirrors are static while the origin (OSM)
  moves (inference).
- **Edges.** The 130 access edges carry `observed_at 2020-01-28`. That is the EFF release date; the records cover 2016–2017
  (`data_driven_vocab.toml:100`). This conflicts with SIG-TIME-002 and SIG-ONTO-041.
- **Spine against release.** 20 sources inserted claims after the cut: the spine holds 2,514,683 claims against 2,423,200 in the release.
  As of 2026-09-30, 149 of 177 sources had inserted nothing for more than 7 days (median 11 days). 24 sources report `claims_inserted >
  claims_considered` (NEW-17).

### 2.8 Per-source contribution and anomaly rate (M41–M42)

The anomaly rate is the share of a source's entities that carry at least one of: a collision (null point), a location more than 25 km
outside the jurisdiction, or a same-source exact duplicate. The full table is `out/per_source_anomaly.csv` (gitignored).

- **Concentration.** 178 sources. The largest, the OSM ALPR republish, holds **66.4 %** of entities. The top 5 hold 76.6 %. Only 7 sources
  reach 1 % or more.
- **Anomaly rate.** 49,735 entities are flagged, **21.4 %** entity-weighted. The median source rate is 0.45 %. 87 sources are clean, 62
  exceed 5 % and 24 exceed 50 %.

| source (redacted where handle-like) | share of entities | anomaly rate | main anomaly |
|---|---|---|---|
| OSM ALPR republish | 66.4 % | 17.6 % | 27,240 same-source exact duplicates; 13,238 "nationwide" points duplicate DeFlock-republish points (§2.2) |
| FL 511 (3 republished layers) | 4.0 % | 73.4 % | 1,964 collisions; 4,891 exact duplicates |
| GA 511 | 3.0 % | 2.9 % | 196 exact duplicates; 10 at (0,0) |
| CalOES (CA) | 1.9 % | 31.4 % | exact duplicates; 70 points > 25 km out |
| IL DOT | 1.3 % | **97.9 %** | collisions |
| TxDOT republish | 1.2 % | 3.9 % | — |
| IA DOT | 0.7 % | **99.2 %** | exact-coordinate pairs |
| FDOT D5 (published as CA) | 0.6 % | 65.0 % | 838 points in Florida |
| Nottingham, Bangladesh, Oosgis NL, Chattanooga, one `[handle id]` | < 0.3 % each | **100 %** | swap / Singapore / Belgium / duplicates |

---

## 3. Agent sample — agent review (not human-verified)

This is an **agent review**. It is not a human label and does not count toward any SIG-EVAL or human-evaluation obligation (P4, P5).

**Draw.** `tools/draw_sample.py`, seed 20260930:

- 50 distinct site `entity_id`s, simple random, from the 232,625 published. 35 of the 50 are OSM-derived.
- 30 distinct stored edges, stratified: 10 `configured_sharing_partner`, 10 `camera_operator`, 10 procurement `seller`/`buyer`.

**Checks.** `tools/verify_sample.py` and `tools/layer_counts.py` made 134 GETs plus one EFF ZIP download, sequential and at least 1.5 s
apart (Overpass 3 s):

- **ArcGIS layers.** A spatial query within 75 m of the published point, then a match on any id alias equal to the stored ref. A
  `where <oid>=<ref>` query was the fallback.
- **Socrata.** `$q=<ref>`.
- **OSM-derived rows.** One Overpass `around:30` query for `man_made=surveillance` at the origin.
- **Edges.** The EFF 2016–2017 release CSV (NVLS column); the OSM operator tag; the procurement portal record (`$q=<external id>`).

Upstream attribute values stay in the gitignored `sample/raw/`.

| stratum | n | result |
|---|---|---|
| Sites: fidelity to the upstream layer | 50 | **50 confirmed**. The same ref was found upstream at 0 m from the published point. |
| Sites: OSM origin | 35 | 29 have a surveillance node within 30 m. 6 were unverifiable (Overpass 504). Of the 29: **29 ALPR-tagged** (SIG says `traffic_camera`), 25 carry a manufacturer tag SIG drops, and 6 carry an operator tag. |
| Sites: upstream completeness (15 sampled layers) | 15 | 11 exact counts. SIG is short in 3 layers: Surrey −92 (13 %), ACT speed cameras −53 (4.2 %), TxDOT −4. WSDOT has +1. |
| Edges: `configured_sharing_partner` | 10 | **10 confirmed.** The agency row exists with `D. NVLS = Y`, and the release has exactly 130 `Y` rows for 130 edges. Two faults remain: the date (2020 release, not 2016–2017) and the missing state (Pasadena and Cypress are ambiguous between CA and TX). |
| Edges: `camera_operator` | 10 | 4 match the registry agency (WSDOT ×3, UDOT). **6 are publisher-as-operator** (OSM). In 4 of those 6, the OSM origin node names a real operator. |
| Edges: procurement party | 10 | 6 confirmed, with the party named in the portal record. 3 inconclusive: a multi-vendor contract, where the first returned lines did not include the party. 1 unverifiable (timeout). **Topical precision 0 of 9**: no retrieved record concerns surveillance technology. Titles include tree planting, pump-out services, shelter services and health-plan administration. |

**Reading.** The copying layer is faithful, and its errors are few and systematic (layer omissions). The meaning SIG adds is where it
goes wrong: technology, operator, date, identity and topical relevance.

---

## 4. Recommended continuous checks

Each check runs automatically over real data, at ingest, at materialisation or as a release gate. Each is a candidate L3 invariant and
names the metric it guards. None of them needs a human. All of them need a read-only audit login (NEW-16).

| # | check | where | fails when | would have caught |
|---|---|---|---|---|
| C1 | **Subject-key uniqueness.** Within one capture, one ref maps to one upstream record. | ingest (per layer) | any ref maps to more than one distinct record | M07 (5,278 collisions) |
| C2 | **Geometry gate.** Point-in-polygon against the jurisdiction (2 km tolerance) plus detectors for axis swap, sign flip and (0,0). Assign `unresolved` points by polygon, with the method disclosed. | export | an unexplained outside point; any swap or (0,0) | M16–M19 |
| C3 | **Cross-layer duplicate monitor.** The M02 share at 10 and 25 m against the resolver merge ratio, plus a mirror registry with measured overlap per declared lineage. | after materialise | gap greater than 1 pp; an undeclared layer pair with more than 50 % overlap | M02–M05, M13 |
| C4 | **Claim redundancy.** The exact-repeat share per run. A re-sighting must be a dated observation. | ingest | above 1 % | M08, M36 |
| C5 | **Contradiction recall.** Any resolution with at least 2 distinct values beyond the predicate's tolerance must be contested or carry dissent. | materialise (DB test on the live spine) | any violation | M14 |
| C6 | **Technology and entity type.** Every target declares a technology term. Subject kind must be compatible with entity type, and the export carries the technology. | ingest + export | a mistyped subject; a non-deployment kind typed `deployment` | M21, M22 |
| C7 | **Role check.** Operator must be an agency entity or explicit `unknown` (SIG-ONTO-028). Publisher strings are blocklisted. | ingest | any publisher-as-operator | M23 |
| C8 | **Evidence binding.** The share of claims bound to a byte-bearing capture with a locator, published per release. | release | the share does not rise, or falls | M33, M34 |
| C9 | **Time coverage.** The share of claims and edges with `observed_at` or valid time. The upstream change date is taken from `editingInfo`, `Last-Modified` or a content digest, never from SIG's insert time. | ingest + release | an undated edge; freshness "ok" while not evaluable | M30, M37, M38 |
| C10 | **Attribution completeness** per row (attribution required means non-empty, and names the upstream). | export | any empty or SIG-credited upstream row | M35 |
| C11 | **Upstream reconciliation.** Upstream feature count against SIG subjects, per layer per run. | ingest | unexplained delta above 1 % | M40 |
| C12 | **Release diff.** Id retention, per-dossier count deltas, the top-N largest changes. | release | retention below 99.9 %; an unexplained dossier delta above 5 % | M11, regression guard |
| C13 | **Relevance filter** for procurement, agenda and grant feeds: a topical classifier or keyword gate, with its precision measured on the rotating sample. | ingest | measured topical precision below the target set at L3 | M44 |
| C14 | **Rotating agent sample.** Weekly, seeded, 50 sites and 30 edges, labelled "agent review". Track fidelity, type, role and date correctness over time; never report it as human verification. | weekly | fidelity below 95 % or any drop | M43, M44 |

---

## 5. Limits

- **Two populations.** Release metrics describe the 2026-09-27 cut. Spine metrics describe the live spine at 22:02–22:29Z. Neither is
  labelled as the other.
- **Sampled spine estimates.** `resolution` figures come from `TABLESAMPLE SYSTEM` (block sampling), so they are clustered estimates. The
  conclusion is not sensitive to that: 0 dissent in 19,121 resolutions.
- **Boundaries.** Natural Earth 10 m and Census 500k are generalised, hence the 2 km tolerance. The intended geography per source is I1's
  classification (inference).
- **Types and relevance.** Technology classes come from keyword rules over registry metadata (inference). The OSM layers' ALPR class is
  corroborated at the origin (29/29 in the sample). Procurement relevance was judged by keywords plus reading the titles (agent judgement).
- **Distance-based duplicates.** They include legitimate co-located multi-camera mounts. The cross-layer metric (M02) excludes same-layer
  pairs to limit this.
- **Not measured.** `ingest_run_capture` and `entity_identity_key`, which the read role cannot see; person-level data; the 144 MB research
  queue beyond counting; any browser state.

## 6. Findings raised (`PD/findings/incoming/L2.csv`)

| id | sev | title (short) |
|---|---|---|
| NEW-1 | S1 | Non-unique refs merge distinct cameras (5,278 subjects) — the real cause of the 5,290 "conflicted" points |
| NEW-2 | S1 | Resolver labels every multi-claim value "uncontested"; 2 contradictions recorded |
| NEW-3 | S1 | Cross-layer duplicates 13.5 % against 3.75 % merged; mirrors double-published; dossiers up to 2.25× |
| NEW-4 | S1 | Publisher recorded as operator on 74 % of camera subjects; OSM "operator" hub of 26,839 edges |
| NEW-5 | S1 | 0 of 2.78 M claim-evidence bindings reach real bytes; no locator or excerpt |
| NEW-6 | S1 | 77 % of `traffic_camera` subjects are ALPR, CCTV or enforcement (quantifies I1 NEW-9) |
| NEW-7 | S2 | 17.5 % of claims are exact repeats; `sharing_edges.csv` 29 % duplicate rows |
| NEW-8 | S2 | 10,238 non-deployments typed `deployment`; typed entity tables empty |
| NEW-9 | S2 | No cross-source agency identity (≥ 171 of 200 EFF agencies duplicated; 0 links; state dropped) |
| NEW-10 | S2 | No time on claims and edges; "last content change" is SIG's insert time |
| NEW-11 | S2 | Procurement ingestion has no topical filter (0 of 9 sampled contracts on-topic) |
| NEW-12 | S1 | Geometry gate quantified with polygons: 2,370 points > 25 km out across 15 dossiers |
| NEW-13 | S2 | 92 % of "unresolved" points are inside a US state and could be assigned by polygon |
| NEW-14 | S1 | 630 sharing rows credit "The SIG project" instead of EFF & MuckRock |
| NEW-15 | S2 | Tier-3 auto-write rests on 0.986 precision; the run's own LLM labels give 0.784 |
| NEW-16 | S2 | No least-privilege read login to the spine |
| NEW-17 | S3 | 24 sources report more claims inserted than considered |

---

## Appendix — reproduction

From `docs/build/logs/next-phase/L2/`:

1. Start `cloud-sql-proxy --address 127.0.0.1 --port 5439 zeta-medley-508121-u7:us-central1:sig-pg`. The operator's ADC is needed.
2. Re-run any query with `../../../../../.venv/bin/python tools/q.py <id> @db/sql/<id>.sql`.
3. Run `.venv/bin/python tools/release_quality.py`, then `tools/round2.py`, `tools/round2b.py`, `tools/graph_structure.py` and
   `tools/per_source_summary.py`.
4. Run `tools/draw_sample.py`, then `tools/verify_sample.py` and `tools/layer_counts.py`. These make network GETs; use the same pacing.

Inputs:

- the release files under `bucket/` (sha-verified in `fetch_log.tsv`);
- boundaries under `ref/`: Census `cb_2023_us_state_500k.zip`, Natural Earth `ne_10m_admin_0_countries.geojson` and
  `ne_10m_admin_1_states_provinces.geojson`, hashes in `fetch_log.tsv`;
- the restricted copies under `restricted/`.

Evidence manifest (gitignored, hashed in `SHA256SUMS`):

| path | contents |
|---|---|
| `bucket/` | 37 release files |
| `restricted/` | 3 files from 2026-09-27, plus 12 parquets from 2026-09-24 |
| `ref/` | boundary sets |
| `db/` | SQL, results, query log, proxy log |
| `out/` | derived tables |
| `sample/` | ids, results, raw upstream responses |
| `upstream/` | EFF release ZIP |
| `tools/` | scripts |
| `fetch_log.tsv` | every HTTP request |
