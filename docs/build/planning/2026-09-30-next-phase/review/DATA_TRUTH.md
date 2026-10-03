# C3 — Data-truth audit of displayed numbers

Row **C3** of `META_PLAN.md` (Stage P, R, read-only). Run window **2026-09-30T17:00:03Z → 17:27:18Z** (`date -u`), in the planning
worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`). `PD` = `docs/build/planning/2026-09-30-next-phase`.
Protocol: `PD/review/PROTOCOL.md` §7 (C3), §9 (severity). Companion files: `PD/data/number_trace.csv` (453 rows) and
`PD/findings/incoming/C3.csv` (21 findings, `NEW-1…NEW-21`). Scratch evidence: `docs/build/logs/next-phase/C3/` (gitignored; every file
hashed in its `SHA256SUMS`, 140 entries).

**Independence (P6).** I did not read `META_PLAN.md` Appendix A or any file under `PD/findings/**`. I did list the file names in
`findings/incoming/` once, while checking the output location. I read no file contents there.

**Release under audit.** Public manifest `sig-2026-09-27-ce480ab1`, sha256 `717aeb44…72d6`, 132 artifacts, as-of world/belief 2026-09-27,
ruleset `p27.3/1.0.0`, resolver `0.0.0`. The site's deployed web build is inferred to be `5c064881` (PROTOCOL §1). Code references give that
commit, or the chain tip `b051732c` for exporter and API code. Every finding records whether the chain tip changed the relevant file.

**Drift guard (PROTOCOL §2.8).** At the start (17:00:28Z) and the end (17:16:29Z), `/` returned `Last-Modified: Sun, 27 Sep 2026 01:33:43 GMT`
with ETag `"6ab87277-14f54"`, and the manifest sha256 was `717aeb44…72d6`. Neither changed. The home HTML sha256 is `a007e380…02ab`, which
equals the A1 baseline.

---

## 1. Method

**Pages traced.** The pages were `/`, `/methodology/`, `/coverage-metrics/`, `/data-freshness/` (plus `/status/`), `/corrections/`,
`/contribution-back/`, `/research-queue/`, `/map/`, `/network/` and `/dossier/`. The dossiers were the 8 PROTOCOL §5.3 strata (`unresolved`,
`fl`, `tx`, `md`, `pt`, `gb-eng`, `au-act`, `ca`) plus 3 that C3 picked:

- **`il`**: a large US state. It has 3,509 subjects, and its "573 of 3509" is the lowest geolocated share among the large states.
- **`ks`**: a small US state. It has 97 subjects, and its code is not ambiguous with ISO 3166.
- **`th`**: the largest non-US country bucket (2,110 subjects).

For each dossier I checked the HTML page and the static `/dossier/<slug>.json`. For the 8 protocol dossiers I also checked the print view,
and for all 11 I checked the API `/v1/dossier/<slug>`. `/watch/` and `/evidence/` were read for cross-page checks.

**Capture.** There were 65 polite HTTP requests, run one at a time, 0.8–1 s apart, with UA `SIG-planning-C3-data-truth/1 (read-only)`:

- 46 GETs to the site plus 2 HEADs for the drift guard
- 17 GETs to the API
- 1 `Range: bytes=0-1999` request on `web/research_queue.json`

The log is `docs/build/logs/next-phase/C3/fetch_log.tsv`. Pages were converted to text with a tag stripper that keeps headings and sections
(`tools/html2txt.py`). **No browser was used**, so states that exist only on the client (map and network islands after JavaScript runs) are
out of C3's view. The no-JS tables and lists, which the site calls "the equivalent", were traced instead.

**Release files.** I read 31 artifacts, about 38 MB, with `gcloud storage cp`:

- all `web/*.json` except `research_queue.json` (144 MB; only its first 2 KB were read)
- `web/analytics/*.json`
- `datapackage.json` and `exclusions.json`
- `sig_graph/{coverage,freshness,jurisdictions,sharing_edges,sites}.csv`
- all 12 `*/sites.parquet`

**Every file's sha256 matched the manifest** (`sha_verify.txt`). Recomputation used DuckDB 1.5.5 from the worktree `.venv` over the 12 site
parquets, plus Python checks of HTML ↔ JSON ↔ CSV. The generators are `tools/build_trace.py` and `tools/build_findings.py`.

**API.** `sig-api-e5ctyx36jq-uc.a.run.app` reads the **live spine**, not the release. Its watermark at 17:07Z was 2,514,683 claims, against
2,423,200 in the release, so drift there is expected. I did not call `/v1/task`: the handler returns the whole task list (about 243k), which
would be an unfair load.

**Spine.** Not queried. No read-only path exists without new credentials, and PROTOCOL §7 requires an operator go. Numbers that only the
spine could confirm are marked `release-artifact-only` in the notes of `match` rows.

**Verdicts** in `number_trace.csv`:

| verdict | used when |
|---|---|
| `match` | The displayed value equals the release artifact (and the API, where one applies). Where bulk data allowed, I also recomputed it. Formatting or rounding differences are counted as match and noted. |
| `mismatch` | The displayed value, or the claim it makes, contradicts a traced source or my recomputation. This includes a correct number whose label asserts something false. |
| `ambiguous-meaning` | The value traces, but its label or context invites a meaning the value does not have. |
| `untraceable` | No public release artifact or API response carries the value. |
| `stale` | The value predates the release it is shown with. |

**Schema note.** `number_trace.csv` uses the column set the orchestrator specified: `trace_id, url, section, displayed_text, claimed_meaning,
traced_to, recomputed_value, verdict, evidence_path, note`. PROTOCOL §7's longer column list is folded in as follows:

- the source sha256 goes into `evidence_path` (`#sha256:` prefix)
- the API value goes into `traced_to` / `recomputed_value`
- observation times are in `fetch_log.tsv`

---

## 2. Summary

### 2.1 Counts by verdict (453 traced items)

| page | match | mismatch | ambiguous-meaning | untraceable | stale | total |
|---|---|---|---|---|---|---|
| `/` | 131 | 2 | 6 | 0 | 0 | 139 |
| `/methodology/` | 9 | 3 | 1 | 0 | 1 | 14 |
| `/coverage-metrics/` | 124 | 3 | 3 | 0 | 0 | 130 |
| `/data-freshness/` | 18 | 1 | 1 | 0 | 0 | 20 |
| `/data-freshness/status/` | 1 | 0 | 0 | 0 | 0 | 1 |
| `/corrections/` | 3 | 0 | 0 | 0 | 0 | 3 |
| `/contribution-back/` | 0 | 0 | 1 | 1 | 0 | 2 |
| `/research-queue/` | 3 | 0 | 2 | 0 | 0 | 5 |
| `/map/` | 13 | 2 | 4 | 1 | 0 | 20 |
| `/network/` | 5 | 0 | 2 | 0 | 0 | 7 |
| `/dossier/` | 0 | 0 | 2 | 0 | 0 | 2 |
| `/dossier/<slug>/` (+ print, `.json`) × 11 | 71 | 25 | 0 | 0 | 0 | 96 |
| API (live spine) | 0 | 13 | 0 | 0 | 0 | 13 |
| bulk download (manifest) | 0 | 1 | 0 | 0 | 0 | 1 |
| **all** | **378** | **50** | **22** | **2** | **1** | **453** |

The home page and `/coverage-metrics/` each repeat all 127 coverage metrics, so row counts overweight those pages. Many rows share one root
cause, so the root causes are counted separately: **21 findings: 2 × S0, 8 × S1, 11 × S2** (`findings/incoming/C3.csv`).

### 2.2 What holds up (positive observations, not findings)

- **Coverage metrics.** All 127 are byte-identical across `web/coverage.json`, `sig_graph/coverage.csv`, `/coverage-metrics/` and the home
  page, in the same order.
- **Jurisdiction figures.** All 55 reconcile exactly between `web/dossiers.json`, `sig_graph/jurisdictions.csv` and a recompute over the 12
  bulk parquets. This covers subjects, geolocated count, conflicted count and source set. Σ subjects = 232,625, which is the home figure for
  "observation-level records". Σ geolocated = 227,335, and Σ conflicted = 5,290.
- **Dossier formats.** For the 11 dossiers, the HTML, the static `.json` and the print view carry identical values.
- **Map tables.** The per-jurisdiction summary on `/map/` (54 lines, Σ 227,335) and its 16 "no published point" indicators (Σ 5,290) equal
  the dossier figures. All 10 seeded rows of the located-asset table (seed 20260930) match the parquets.
- **Freshness.** The 178-row table equals `freshness.json` and `freshness.csv`. The only difference is one formatting change: `not-recorded`
  is shown as "not recorded".
- **Network.** `/network/` agrees exactly with `network.json` and `centrality.json`: 130 edges, 131 nodes, a hub of degree 130, 0 paths.
- **Contradictions.** The count, 2, is the same in the release and on the live API.
- **As-of and ruleset.** The as-of pair and ruleset equal the manifest on every page. No displayed date is later than `date -u`.
- **Empty surfaces.** The corrections log, the renewal watch and the evidence viewer are honestly empty and match their files (`[]`, `[]`,
  0 claim views).
- **Page-specific provenance where it exists.** The "How we know this" block on `/corrections/` and `/research-queue/` is page-specific.

### 2.3 Leads named in the C3 row block

| lead | result |
|---|---|
| Site-wide "How we know this" block | **Confirmed, systemic** (§4.2, NEW-3). Every dossier shows the national block. Only `/corrections/` and `/research-queue/` override it. |
| "Tier sum 6 short" | **Explained, not disclosed** (§4.10, NEW-12). The tier distribution sums to 2,423,194. That is the export's redistributable, publication-gated claims. The 2,423,200 headline counts every tier-0 current claim. The 6-claim difference is a population difference, and no page says so. |
| "Human-verified holdout" wording | **Confirmed mismatch** (§4.3, NEW-4). The gold set is LLM-bootstrapped. D-R6.1-EVAL says human ground truth "does not exist yet". The P/R/F1 = 1.000 rests on a single true pair. |

---

## 3. Cross-page and cross-format agreement

| figure | `/` | `/coverage-metrics/` | release JSON / CSV | dossier HTML / `.json` / print | map / network | live API |
|---|---|---|---|---|---|---|
| observation-level records 232,625 | ✓ | ✓ | ✓ coverage.json; Σ jurisdictions.csv; distinct `entity_id` in parquet | Σ of 55 "Publishable subjects" ✓ | — | — (no national endpoint) |
| geolocated 227,335 | — | — | ✓ jurisdictions.csv; parquet `resolved` | ✓ per dossier | ✓ bins Σ, located-summary Σ | — |
| conflicted 5,290 | not shown | contradicted: "232625 of 232625 resolved" latitude | ✓ | ✓ as UNRESOLVED gaps | ✓ 5,290 ⚠Unresolved | — |
| resolved sites 223,901 | ✓ | ✓ | ✓ coverage.json (not recomputable) | — | — | — |
| contradictions 2 | ✓ | ✓ | ✓ | — | — | ✓ 2 |
| published tier-0 claims | 2,423,200 | 2,423,200 | 2,423,200 (coverage) vs 2,423,194 (provenance) | "How we know this" tier sum 2,423,194 | same | watermark 2,514,683 (drift) |
| sources | "178 tracked" | — | 178 freshness; 219 in evidence.json; 218 provenance | "Independent sources 218" on every dossier | "218" | API dossier: 10 unrelated, the same for every scope ✗ |
| site rows in bulk | — | — | manifest Σ 236,994 rows (portal 10,054 rows for 5,685 entities) | — | — | — |
| TX sources | — | — | 4 | Sources row 4 ✓; "Independent sources 218" ✗ | — | 10 unrelated ✗ |

---

## 4. Items that are not `match`, explained

Evidence classes follow PROTOCOL §2.5. "Inference" is labelled wherever I interpret.

### 4.1 The public API's dossier endpoint returns the same placeholder for every scope (NEW-1, S0)

The API was called for 11 scopes: `fl`, `tx`, `md`, `pt`, `gb-eng`, `au-act`, `ca`, `unresolved`, `il`, `ks` and `th`. Each
`GET /v1/dossier/<slug>` returned 200 with the title `Dossier for <slug>`. All 11 responses contained **the same 25 subject ids**. They also
contained the same 10 sources: `okc_council_statement, decp_fr, deflock, madada, ok_statute, okc-contract-c241032, okcpd_policy, osm, osm_overpass,
raa_prefectures`. These are Oklahoma City, French procurement and OSM sources. The release says Florida rests on four Florida camera
registries. The cause is in code: `api/src/api/store_pg.py:927-956`. When the scope is not an entity id, the handler falls back to "the first
25 tier-0 subjects".

- Evidence: live-read (`api/api_v1_dossier_*.json`) and code.
- Mitigation (not a fix): the site does not link to the API, and each site dossier's "JSON (API form)" link goes to the static
  `/dossier/<slug>.json`, which is correct.
- Severity: rated **S0** under PROTOCOL §9 as a false public claim presented as fact on a public, unauthenticated, OpenAPI-documented
  surface. The orchestrator should confirm the rating.

The same fallback shape affects `/v1/coverage/fl` and `/v1/coverage/tx` (NEW-10, S1). Both answer `"complete": true, "evaluated": 0,
"records": []`, which asserts complete coverage for jurisdictions whose site dossiers show NOT_RESEARCHED and UNRESOLVED gaps. This
violates SIG-API-003 (a coverage statement of what was evaluable).

### 4.2 "How we know this" on dossiers is national, not page-specific (NEW-3, S1)

Every sampled dossier renders two H2s headed "How we know this":

1. The dossier's own row, "Sources: …". For TX that is 4 source ids.
2. The shared `.sig-hwkt` component, showing *Artifacts 255 · 2245390×untiered, 2690×W1, 175114×W3 · Independent sources 218 · 2020-01-28 –
   2026-09-26*. These are the national `surfaces.site` values from `web/analytics/provenance.json`.

A reader of `/dossier/pt/` is told 255 artifacts and 218 independent sources stand behind a 1-subject dossier. The page-specific recompute
from public data gives: PT 1 source, 1 evidence artifact; FL 4 and 4; TX 4 and 5; MD 7 and 8; GB-ENG 11 and 12; `unresolved` 58 and 58.

**Cause (code).**

- `web/src/layouts/BaseLayout.astro:43`: `const provenance = Astro.props.provenance ?? getSiteProvenance();`. Only `corrections.astro` and
  `research-queue.astro` pass their own.
- The exporter emits only three surfaces (`site`, `corrections`, `research_queue`; `exports/analytics.py:562-622`), so no per-dossier
  summary exists to pass.

The chain tip is unchanged. The site-wide block also appears, arguably acceptably, on `/methodology/`, `/coverage-metrics/`,
`/data-freshness/`, `/map/`, `/network/`, `/dossier/`, `/watch/`, `/evidence/` and `/contribution-back/`. On `/contribution-back/` it
attaches a national claim-tier distribution to an OSM changeset count.

### 4.3 Methodology evaluation metrics (NEW-4 S1, NEW-20 S2)

The values are hardcoded in `web/src/lib/resolution-eval.ts`, the same at `5c064881` and `b051732c`. They are **not in the release
manifest**. Traced to `docs/build/reports/P28.1_resolution_eval.md`:

- **"pairwise precision / recall / F1 at tier ≤ 3 (auto-write) P 1.000 · R 1.000 · F1 1.000 — the frozen, human-verified holdout"**
  - Report lines 3 and 10–18: the holdout has **6 pairs**, and the metric has **tp=1, pp=1, ap=1**, so the perfect score comes from one
    pair. The gold set is "LLM-bootstrapped with a small maintainer seed". The "LLM" adjudicator's id is `llm:rulebased@v1`.
  - `docs/tickets/DEFERRALS.md:331` (D-R6.1-EVAL, OPEN) says real human-labelled ground truth "does not exist yet".
  - The same page's "How we know this" says "Not yet human-reviewed".
  - Verdict: `mismatch` for the wording, `ambiguous-meaning` for the unqualified 1.000.
  - The PROVISIONAL disclosure above the table is accurate, but the table then contradicts it.
- **Checks that pass.** κ 0.714 (on 17 labelled pairs, and n is not shown), the floor 0.980, B-cubed (F1 recomputes to 0.9756 from
  R=20/21), and tier-0 precision all match the report. The camera-site rows also match: κ 0.669 on 540 pairs; 1g 70/70 with a Wilson lower
  bound I recomputed as 0.9480; 3g 69/70 with a recomputed bound of 0.9234.
  - One oddity in the report itself: the B-cubed line prints `tp=42, pp=42, ap=42` next to R=0.952.
- **Stale (NEW-20).** The page says "These are the current holdout metrics". The camera-site figures come from the P30.2b hosted run of
  2026-09-24 (run-6 lineage, 2,332 merges). The released headline, 223,901 resolved sites, comes from **run 7** (8,724 merges, 2026-09-27;
  `REPUBLISH_DIFF_2026-09-27.md:56-66`), and no re-measurement is recorded for run 7. If rules v2 and the frozen holdout were unchanged, the
  precision still holds. The page names no run, window or source mix (SIG-EVAL-006).
- **Methodology copy.** It says the coverage page carries "records-derived bounds … and measured survey recall" and that freshness has
  "stale-entity counts measured against predicate volatility". Both are false for this release (§4.7, §4.12).

### 4.4 "Resolved" means two different things (NEW-5, S1)

`/coverage-metrics/` and `/` say **"232625 of 232625 subjects with a resolved camera_latitude value"**, and the same for longitude. The
release's own site shaping disagrees. It marks **5,290** of those subjects `point_status=conflicted` and publishes no point for them. The
dossiers call them "Subjects with conflicting coordinate evidence — Unresolved: evidence exists and disagrees; no resolution is defensible".
The map lists all 5,290 as ⚠Unresolved.

**Cause (code), in two parts:**

1. The two surfaces use different definitions. The coverage ratio counts spine `resolution` rows. The map and dossiers use the exporter's
   observation envelope (`exports/shaping.py:1000-1040`).
2. The reconciliation numerator (`inference/src/inference/materialize.py:273-328`) counts distinct subjects with **any** resolution row
   that has a winning claim. There is **no tier-0 or currency filter**, and the result is clamped with `min(resolved, claimed)`.

   So a 100 % ratio can hide a numerator that exceeded its denominator. 113 of the 124 ratios read exactly "N of N".

The other 122 ratios could not be recomputed without the spine, so they are `match` (release-artifact-only), with the caveat above.

### 4.5 "Geolocated site observations in X" includes points located elsewhere (NEW-6, S1)

This comes from a bounding-box recompute over the parquets (`bbox_check.txt`). The dossier count is the sources' *jurisdiction claim*, not
where the points are:

- **CA "6139 of 6139"**: 851 of the points lie outside California. `camreg_trafficops_ca` places **838** at 28.35–28.80°N, 81.16–80.10°W,
  which is central Florida. `camreg_caloes_ca` places 13 in AZ, UT, ID or MT.
- **GB-ENG "1661 of 1710"**: 562 `camreg_nottingham_gb` points have **latitude and longitude swapped** (lat −1.2, lon 53.0). They are drawn
  in the Indian Ocean off East Africa.
- **TH "2109 of 2110"**: 155 points sit at 22.2–22.5°N, 113.9–114.3°E, which is **Hong Kong**.
- **ID** (not sampled; found while checking codes): `camreg_indonesia_id` (268, Jakarta and Java) and `camreg_achd_id` (232, Ada County,
  **Idaho**) share one "ID" dossier.
- **Other defects:**
  - 15 points at (0,0): GA 10, FL 3, DC 1, `unresolved` 1
  - sign flips: AZ 4 (lon +111.9), GA 4 (lon +84 and +104)
  - OR 6 outside the state, one at lon −134

TX, MD, IL, KS and AU-ACT passed the check. Evidence: recorded execution (DuckDB) and live-read. For MD, IL, KS, AU-ACT, PT, TX and
`unresolved` the count is `match`; FL is `match` with a note (3 points at (0,0)).

### 4.6 The incompleteness banner undercounts (NEW-7, S1)

All 11 dossiers say "This dossier has **1** unresearched field", and `unresearched_field_count: 1` in the JSON. The same page shows
**12 fields as "unknown"** with no kind of absence:

- auto-renews, notice window, contract expiry, next decision date
- state statute, local ordinance, disclosure duties
- approving body, vote, consent agenda, public comment, date

Five headings are also empty: At a glance, Who else can see the data, Configuration and retention, Usage, Timeline.
`web/src/lib/dossier.ts:349-360` counts only NOT_RESEARCHED gap rows. For the design-centre task P1-T2 ("what does it cost, when does it
renew"), the banner signals near-completeness where the record is mostly empty (SIG-UI-012, SIG-TIME-012).

### 4.7 The freshness page shows "0 stale" where nothing was evaluable (NEW-8 S1, NEW-21 S2)

`/data-freshness/` shows "178 ok" and "Volatility classes: 178 unknown", and **0 stale entities on every row**.
`exports/shaping.py:1283-1345` sets volatility to `unknown` when a source has no dated observation of a registry-known predicate, so nothing
was evaluable. It does compute a `staleness_not_evaluable` count, but that count is not emitted into `freshness.json`, so the page shows 0.
The same release's research queue holds **130 `sharing_snapshot_stale` tasks**. "ok" is the last ingest-run status. SIG-METRIC-006 requires
freshness measured relative to predicate volatility.

**NEW-21.** The home says "178 sources tracked for freshness — of the sources SIG monitors". But 219 distinct sources have evidence
artifacts, and provenance counts 218. The 41 non-site sources (procurement portals, legislative, CCOPS, federal) have no freshness row.

### 4.8 Map (NEW-9 S1, NEW-16 S2; plus `ambiguous-meaning` rows without findings)

- **Attribution (NEW-9).** The map says "© OpenStreetMap contributors (ODbL) · Surveillance data © SIG contributors". In `/map/style.json`
  all 11 non-OSM tile sources are attributed "Surveillance data © SIG contributors (<licence>)". That includes CC-BY-SA-4.0 (`portal`),
  CC-BY-SA-2.0, OGL-3.0 and OGL-Canada-2.0. The bulk rows carry upstream `rights_attribution`, for example "ACT Government traffic safety
  camera registries (data.act.gov.au)". The licence id is shown, but the rights holder is misattributed. I rated this **S1**, with an S0
  candidacy under §9 if the share-alike and OGL attribution terms are read as unmet. Route to C2 (H11) and E.
- **Suppressed counts printed (NEW-16).** The figure's caption says a low-coverage cell's "count is suppressed". Yet the "tabular
  equivalent" prints counts for all **601 low-coverage cells** (40,913 records, one cell with 2,093). The SVG `<title>` also carries the
  count (`map.astro:196-228` at `5c064881`; the same at the chain tip).
- **Column labels (NEW-16).** The column header is "Devices", but the values are observation-level records. The per-cell "Jurisdiction"
  column sums to CA 662 and TX 1,855, against CA 6,139 and TX 3,994 on the dossiers, because each multi-jurisdiction cell gets one label.
- **Untraceable (NEW-18).** Bin counts and coverage classes come from `web/analytics/density_bins.json`, which is restricted and absent from
  the public manifest.
- **Layers legend (ambiguous, no finding).** The legend lists RTCCs and hubs, service areas, private–public networks and field of view. All
  236,994 public site rows are `entity_type=deployment`, and no public artifact backs those layers.

### 4.9 Same-source duplicate points (NEW-19, S2; inference)

23,566 of 227,335 geolocated entities share **source and exact coordinates** with another entity; for FL it is 3,053 of 8,001. Of these,
3,161 also share a non-null label: IA 846 of 1,858, MD 467 of 2,752, TH 117. Every seeded map row matched two `dot_511_ia` entities.

Some of this is probably several camera views on one pole (inference). Same-label pairs look like double ingestion. If that is confirmed,
the observation counts in IA and MD overstate by up to 45 % and 17 %, and this becomes S1. The data is in `dup_points.txt`.

### 4.10 Provenance headline and the "6 short" (NEW-12, S2)

"**2423200 of 2423200** published tier-0 claims with a resolvable evidence artifact":

- It counts every tier-0 current claim (`materialize.py:248-271`). That includes **6 claims the export does not publish**: the
  redistributable plus publication gate in `spine_export.py:197-213` yields 2,423,194. That is exactly the tier-distribution sum and the
  provenance denominator.
- "Resolvable" means a `claim_evidence` row exists in the spine. The public has **0 claim views** (`evidence.json`), and `/evidence/` says
  no claim has a full evidence view.

### 4.11 "Contradictions kept visible: 2 open of 2" (NEW-11, S2)

The value matches both the release and the live API (claimed_device_count and use_restriction on one subject). But the same release shows
5,290 coordinate-conflicted subjects as Unresolved, and 33,907 proposed merges await review. The headline counts only the contradiction
table, so the label understates the disagreement the record itself shows.

### 4.12 Label semantics and copy (NEW-13, NEW-14, NEW-15, S2)

- **NEW-13, "How we know this" labels:**
  - "Independent sources 218" counts distinct source ids with no lineage de-duplication (`analytics.py:590`). Four OSM-lineage ids are
    counted separately. A public recompute finds 219 sources in `evidence.json`.
  - On `/research-queue/`, "Artifacts 243761" counts tasks, and "Independent sources 1" is the number of detectors.
  - 92.7 % of claims are "untiered" with no explanation. Two "tier" vocabularies (W-classes and the sensitivity "tier-0") appear side by
    side.
- **NEW-14, "55 jurisdictions … researched to a publishable standard":**
  - One of the 55 is the `unresolved` bucket. It holds **71.4 %** of all observation records (all 154,528 OSM nodes plus 11,682
    operator-accepted).
  - The codes mix US postal and ISO-3166: CO is Colorado but CO-MET is Colombia; SA is Saudi Arabia; DE is Germany; ID is Indonesia plus
    Idaho.
  - Titles show codes only.
- **NEW-15, metric kinds promised by copy:** the coverage page promises "records-derived bounds, per-agency reconciliation ratios, and
  measured survey recall". The release has 0 bounds, 0 survey recall, and per-predicate national ratios only. The device-population caveat
  is repeated under `bill_*`, contract and procurement ratios.

### 4.13 Bulk format disagreement (NEW-17, S2)

The manifest gives `portal/sites.*` a `row_count` of **10054**, but the file holds **5,685 distinct entities**. 4,369 entities appear
twice, once per `rights_source_id`: `dot_511_wa` 1,830, `dot_511_or` 1,179, `dot_511_mo` 871, `dot_511_ky` 254, `dot_511_dc` 235. This
looks like a rights-join fan-out. Summing rows over compartments gives 236,994, not the site's 232,625.

### 4.14 Untraceable to the public release (NEW-18, S2)

- **`/contribution-back/` "0 accepted upstream of 0 attributed changesets"** comes from `web/leverage.json`, which is not in the 132-artifact
  public manifest. The build read it from the restricted export (`web/src/lib/data.ts:147-180`). No measurement date is shown.
- **Other numbers an outside reader cannot trace:**
  - map bins (restricted)
  - methodology evaluation numbers (hardcoded; §4.3)
  - the 223,901 resolved sites, which are internally consistent (232,625 − 8,724 merges stated in the metric's own note) but not
    recomputable, since no cluster id is exported

  This blocks the P11 "prove it" path.

### 4.15 Other `ambiguous-meaning` rows without a separate finding

- **`/network/`.** It shows "No edges" for observed use and for declared policy. `sig_graph/sharing_edges.csv` also holds **372
  `unclassified`** sharing claims (370 `sharing_partner_degree`, 2 `sharing_restriction`), which the page neither shows nor counts. All 131
  nodes are labelled only by UUID.
- **`/corrections/` transparency counts (0 requests).** These are structurally 0, because the intake receiver is not operating. The page
  does not say so (row C3-T306; rated `match`).
- **Release id.** It is not shown on any audited page. Only the as-of pair and the ruleset are shown.

### 4.16 Outside C3's number scope, but S0 under PROTOCOL §9 (NEW-2)

Source identifiers shown on `/data-freshness/` and in dossier "Sources" rows include tokens taken from ArcGIS item owners.
`connectors/src/connectors/data/camera_registry_targets.toml:3527` (code evidence) records one public id whose token is the item owner, an
individual's email-derived ArcGIS username. By inspection (inference), 31 of the 58 `camreg_*` ids without a place suffix look like
personal names or handles. That list is kept only in the gitignored `personal_like_ids.txt`; the broader 58-id list is in
`handle_like_ids.txt`. Neither is repeated here, and `number_trace.csv` redacts those ids as `camreg_[personal-handle id redacted]`
(7 places). This is raised for C2/H12 and the orchestrator (SIG-PUB-002/003). C3 took no action.

---

## 5. Systemic causes

1. **A shared layout falls back to site-wide provenance.** `BaseLayout.astro:43` defaults every page to `surfaces.site`, and the exporter
   emits no per-scope provenance. One component therefore turns a national summary into a claim about each dossier (§4.2). The same
   component's fixed labels ("Artifacts", "Independent sources") are reused for tasks and detectors (§4.12).
2. **Displayed numbers do not have to come from the public release.** Evaluation metrics are TypeScript constants. The contribution-back
   metric and the map bins come from restricted artifacts. So those numbers can go stale (§4.3) and cannot be traced (§4.14). Nothing checks
   that a page number maps to a manifest artifact.
3. **"Resolved", "geolocated" and "conflicted" are computed twice, independently.** The coverage ratios use spine `resolution` rows,
   unfiltered and clamped. The dossiers and map use the exporter's envelope shaping. The two disagree for 5,290 subjects (§4.4), and the
   contradiction headline uses a third notion (§4.11).
4. **Jurisdiction comes from a claim, with no geometry check.** Nothing at export compares a point to its claimed jurisdiction or rejects
   (0,0), swapped axes or sign flips. Code schemes are mixed (§4.5, §4.12).
5. **Absence collapses to zero or to complete.** Freshness shows "0 stale" when nothing was evaluable (§4.7). The banner ignores null
   fields (§4.6). The API reports `complete: true` with 0 evaluated (§4.1).
6. **The API is not wired to the release.** `/v1/dossier` and `/v1/coverage` run placeholder logic for jurisdiction slugs, and the API
   reads the live spine. API and site therefore disagree, and the API is wrong (§4.1).
7. **Rights-record joins fan out rows** in bulk exports (§4.13). Data-quality defects upstream (duplicate ingestion, §4.9) pass into
   displayed counts because no export-time uniqueness check exists.

---

## 6. Recommendations (draft requirements for C6 and S)

These are phrased as testable requirements. The ids are provisional, `DR-C3-nn`.

- **DR-C3-01 (traceable numbers).** Every material number on a public page SHALL be rendered from an artifact listed in the public release
  manifest, and SHALL carry a machine-readable pointer (artifact path plus field or JSON pointer). A build check SHALL fail when a page number
  has no pointer (SIG-CHART-011, SIG-METRIC-005). Evaluation metrics and the leverage metric SHALL ship as public release artifacts.
- **DR-C3-02 (page-specific provenance).** The exporter SHALL emit a "How we know this" summary per dossier scope. A page without a
  page-specific summary SHALL label the block "Site-wide". The layout SHALL NOT fall back silently (SIG-UI-044).
- **DR-C3-03 (evaluation claims).** Every published evaluation figure SHALL show n (pairs and positives), the labeller type
  (human / agent / LLM / rule-based), and the run, ruleset and time window it measures. "Human-verified" SHALL appear only with a recorded
  human-completion marker (P4/P5, SIG-EVAL-006, SIG-METRIC-008b).
- **DR-C3-04 (one "resolved").** Coverage ratios, dossiers and the map SHALL share one definition of a resolved value per predicate. The
  reconciliation numerator SHALL be restricted to the denominator's subjects by a join, not clamped. Conflicted envelopes SHALL count as
  unresolved (SIG-METRIC-009).
- **DR-C3-05 (geometry gate).** The export SHALL flag or withhold points at (0,0), points with swapped axes or sign errors, and points
  outside the claimed jurisdiction's boundary. Dossiers SHALL report "N geolocated, of which M located outside <J>" as a visible conflict.
- **DR-C3-06 (incompleteness).** The incompleteness banner SHALL count every field rendered "unknown", and each such field SHALL show its
  absence kind (SIG-UI-012, SIG-TIME-012).
- **DR-C3-07 (not-evaluable is not zero).** Freshness SHALL show "not evaluable (n)" rather than 0. `freshness.json` SHALL carry
  `staleness_not_evaluable`. API coverage SHALL return `complete: false` when `evaluated = 0` (SIG-METRIC-006/007, SIG-API-003).
- **DR-C3-08 (contradiction headline).** The contradiction headline SHALL include coordinate conflicts, or be relabelled to name exactly what
  it counts.
- **DR-C3-09 (attribution).** Map and tile attribution SHALL name each compartment's upstream rights holder from `rights_attribution`, not
  "SIG contributors" (SIG-LIC-004a, SIG-EXPORT-005).
- **DR-C3-10 (bulk unit).** Bulk exports SHALL hold one row per entity, with rights records nested. Manifest `row_count` SHALL equal distinct
  entities, and the datapackage SHALL state the unit (SIG-EXPORT-002).
- **DR-C3-11 (jurisdiction labels).** Dossiers SHALL show a human-readable name plus a code with its scheme. The `unresolved` bucket SHALL
  NOT be counted as a jurisdiction. Colliding codes (ID, CO, CA, GA, DE) SHALL be disambiguated at ingest (SIG-UI-048).
- **DR-C3-12 (API honesty).** `/v1/dossier/{scope}` and `/v1/coverage/{scope}` SHALL either serve the release-backed jurisdiction record or
  return 404. They SHALL never return placeholder subjects.
- **DR-C3-13 (Part VIII identifiers).** Source identifiers SHALL NOT embed personal names or account handles. Existing ids SHALL be mapped to
  neutral ids before publication (SIG-PUB-002/003).
- **DR-C3-14 (release id).** Every page and dossier JSON SHALL display the release id next to the as-of pair (SIG-FIND-001).
- **DR-C3-15 (number-truth CI).** A CI job SHALL, for each release candidate, recompute the headline, dossier and map figures from the bulk
  files and fail on disagreement. This audit's recompute (`tools/build_trace.py` plus the DuckDB queries in §4.5 and §4.9) is a starting
  point.

---

## 7. Limits and what was not traced

- **Spine.** No spine query was run. 122 reconciliation numerators, the 223,901 cluster count, the date range and "Independent sources" are
  `release-artifact-only`.
- **Research queue.** `research_queue.json` was not downloaded (144 MB). The header and the first 2 cards were traced (Range sample). The
  other 498 visible cards were not.
- **No real browser.** Island-only states, such as map popups and the network explorer after expansion, were not seen.
  `/search/` was fetched but is out of C3's page list.
- **Bounding boxes.** Coordinate checks used approximate state and country boxes with 0.3° slack, not polygons. The counts in §4.5 are
  therefore a floor for cross-border errors near borders.
- **Code evidence.** Code evidence for the web build refers to `5c064881`, inferred per PROTOCOL §1. For the exporter, inference and API it
  refers to `b051732c`. Behaviour was confirmed live where it could be observed.

## 8. Evidence manifest

`docs/build/logs/next-phase/C3/` (gitignored; `SHA256SUMS`):

| path | contents |
|---|---|
| `html/` | 33 pages |
| `text/` | stripped text of those pages |
| `json/` | 11 dossier JSONs and `map_style.json` |
| `api/` | 17 responses |
| `bucket/` | 31 release files plus the manifest, sha-verified |
| `fetch_log.tsv` | request log |
| `sha_verify.txt` | sha256 check against the manifest |
| `bbox_check.txt` | coordinate bounding-box results |
| `dup_points.txt` | same-source duplicate-point results |
| `map_sample.json`, `freshness_sample.json` | seed 20260930 samples |
| `dossier_pagespecific.json` | per-dossier source and artifact recompute |
| `handle_like_ids.txt`, `personal_like_ids.txt` | Part VIII lists; do not commit |
| `tools/` | `html2txt.py`, `build_trace.py`, `build_findings.py` |

To regenerate the committed CSVs from the planning worktree root:
`python3 docs/build/logs/next-phase/C3/tools/build_trace.py && python3 docs/build/logs/next-phase/C3/tools/build_findings.py`.
