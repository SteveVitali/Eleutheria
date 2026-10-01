# K5 — Dossier source-contribution explorer (operator ask U-003.5)

Row **K5** of `META_PLAN.md` §6 Stream K (owner D, depends J3, C3). Written by Claude Code (Opus 5.5) in the planning
worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `e69f3fde` at writing).
Work window (`date -u`): **2026-09-30T21:30:46Z → see footer**, shared with K4. `PD` = `docs/build/planning/2026-09-30-next-phase`.
Companion: **K4** (`PD/design/K4-dossier-index.md`), which supplies the jurisdiction keys this note groups by. Findings:
`PD/findings/incoming/K4K5.csv` (NEW-8, NEW-9 are K5's).

> **Design only (P3/P10).** Nothing here changes production.
>
> - **Evidence.** Measurements are **recorded-execution** over the sha-verified copies of release `sig-2026-09-27-ce480ab1`
>   (manifest `717aeb44…72d6`, re-read unchanged at 21:32:40Z). K4's point-in-polygon placement supplied the jurisdiction
>   keys. Code facts are cited at file:line. Sizes not measured are **inference**. Nothing is `engineered` (P5).
> - **Copy.** Public copy is **agent-drafted**.
> - **Part VIII.** Source ids that look like personal account handles are not reproduced here (C3 NEW-2; DR-C3-13).

**The operator's ask (U-003.5, verbatim excerpt):** *"on individual dossier detail pages users should be able to
browse/explore what sources contributed what when to this jurisdiction and perhaps navigate to details for these sources
and their ingestion and so on"*. The row block adds:

- counts by predicate and technology;
- links to source pages and ingestion runs (J3 / K10);
- per-figure provenance that fixes the site-wide "How we know this" block.

The task adds:

- first and last seen per run;
- counts by entity type;
- contribution over time;
- contradictions between sources;
- filters and sort;
- downloads with provenance under licence (J4);
- the export's data contract with sizes;
- the page layout.

**Inputs read.** Reused, not redone:

- META_PLAN §3 and the Stream K block;
- U-003;
- `review/DATA_TRUTH.md` §4.2, §4.9, §4.12, §5, §6;
- `design/J3-transparency-design.md` §1–§6 and §10–§12;
- `research/J1-exposure-inventory.md` (run rows, grants);
- `research/J4-redistribution-matrix.md`, via J3;
- `design/G3-release-model.md` §5–§6;
- `research/F5-eng-debt.md` PKG-10/12.

Code read:

- `db/src/db/claim_sink.py` (re-sightings `:41-46, :293-330`; synthetic capture `:1167-1236`)
- `exports/src/exports/{shaping.py, spine_export.py, analytics.py}`
- `web/src/components/HowWeKnowThis.astro`
- `web/src/layouts/BaseLayout.astro:43`
- `web/src/lib/dossier.ts`

---

## 0. Summary

**What a dossier shows today about its sources.** Two things.

1. A "How we know this" row: `Sources: camreg_fl511_fl, camreg_gainesville_fl, …`. These are bare registry ids with no
   links, counts or dates (`spine_export.py:1495-1501`).
2. A second "How we know this" block with **national** totals: 255 artifacts, 218 sources, 2.42 M claims
   (`BaseLayout.astro:43` falls back to `surfaces.site`; C3 NEW-3).

There is no count per source, no date, no run, and no link. The public site files carry **no temporal field** at all
(NEW-9). Every published site row has exactly **one** source, and the co-location key that would show where independent
sources corroborate one another is computed but never published (NEW-8).

**What the spine already knows** (code, chain tip). Every claim links to the capture of each run that asserted it:

- the first sighting inserts the claim;
- each later sighting appends a `claim_evidence` link to that execution's synthetic capture (P31.7 / ADR-R9-RESIGHT,
  `claim_sink.py:293-330`);
- every capture records `retrieved_by_run_id` and `retrieved_at` (`:1204-1230`).

Per claim, **first seen, last seen, first run, last run and number of sighting runs** are therefore derivable in the
export's one snapshot. Aggregating them by (jurisdiction key, source, predicate, run) answers "what, from whom, when".
Hosted presence of the re-sighting links is not verified; the design has an honest fallback (§3.3).

**Design.**

- **Artifact.** The exporter emits one **`sig.dossier-sources/1`** artifact per dossier, plus a runs file. It computes them
  in the same statements pass J3 TX-08a adds, so there is no second read path. The same rows serve J3's source pages
  ("Contribution to dossiers"), so the two directions cannot disagree (SIG-TRANSP-D08).
- **Page.** Each dossier gets a **"Where this comes from"** section: a dossier-scope "How we know this" with all six
  SIG-UI-044 components, and the top sources. It links to a full **explorer page**, `/dossier/<path>/sources/`, which has:
  - the contribution table;
  - per-source detail;
  - contribution over time;
  - where sources agree or disagree;
  - placement;
  - downloads;
  - cite.
- **Figures.** Every material figure carries a **by-source breakdown** that sums to the figure, a definition and an
  artifact pointer (J3 TX-09 `<Figure>`).
- **Budget.** Everything works with zero JS. Sorting, filtering and chart interaction are the optional enhanced layer, gated
  on K0.

**Data contract sizes.**

| dossier | sources | size |
|---|---|---|
| largest: `iso3166-1:US` | 100 | core artifact ≈120–150 KB; runs file ≈40 KB today and ≈1 MB/year of weekly runs (≈0.15 MB gz) |
| largest state: California | 11 | ≈15 KB |

**Whole release.**

- ≈9.0k (dossier, source) rows across ≈5.6k dossiers, ≈11 MB.
- Per-dossier download slices were measured at site level. The claim-level size is inference.

| dossier | rows | parquet | csv.gz | claim-level (inference) |
|---|---|---|---|---|
| California | 28,357 | 2.4 MB | 2.6 MB | ≈3–7.5 MB (90,467 claims) |
| US | 204,575 | 17.6 MB | 18.9 MB | ≈24–60 MB (718,138 claims) |
| Harris County | 5,032 | 0.40 MB | 0.43 MB | — |
| Houston | 3,113 | 0.25 MB | 0.27 MB | — |

**Tickets (§9): DSRC-01…06.**

| key | title | size |
|---|---|---|
| DSRC-01 | Contribution export | M |
| DSRC-02 | Dossier section + explorer page | M |
| DSRC-03 | Per-dossier downloads | M |
| DSRC-04 | Agreement/disagreement view | S |
| DSRC-05 | Enhanced interactions | S, K0-gated |
| DSRC-06 | Acceptance | S |

**Ownership.** DSRC-01 absorbs PKG-10's per-dossier "How we know this" item (merged-into, P9).

**Ordering.** It depends on:

- K4 JUR-02b (keys);
- J3 TX-02/03/04 (source metadata, run records);
- TX-08a (statements);
- TX-09 (`<Figure>`).

Downloads also wait on TX-11 (zero-egress mirror), ACT-07/PKG-08 (attribution) and D-J3-5 (terms withdrawals).

---

## 1. Ground truth

| # | fact | evidence |
|---|---|---|
| K5-G1 | Dossier source display = `"Sources": ", ".join(group.source_ids)` in the `how_we_know_this` section, plus `source_families` (bare ids) in the JSON (`spine_export.py:1495-1501, 1535`). The live `/dossier/fl.json` (21:34:02Z) has `source_families` = 4 bare ids and no counts, dates or links. | code; live-read |
| K5-G2 | The shared `HowWeKnowThis` component renders six components (SIG-UI-044): artifacts, tier distribution, "independent sources", date range, rules, human review. It uses `Astro.props.provenance ?? DEFAULT_PROVENANCE`. The layout passes `getSiteProvenance()` unless a page overrides it (`BaseLayout.astro:43`). The exporter emits only the `site`, `corrections` and `research_queue` surfaces (`analytics.py:562-622`, per C3). | code |
| K5-G3 | Public site rows (`*/sites.parquet`, `sig_graph/sites.csv`) have 21 columns: `claim_ids, entity_id, entity_type, geometry, jurisdiction, label, n_observation_claims, n_sources, point_status, precision, rights_*` (×8), `source_id, spdx, tier`. **None is temporal.** | recorded-execution (`DESCRIBE`) |
| K5-G4 | Every published row has `n_sources = 1` (232,625 of 232,625). All 5,290 `point_status = conflicted` subjects are single-source, so every coordinate conflict is **intra-source**. Meanwhile 1,534 exact coordinates and 3,839 ≈10 m cells (4-decimal grid) hold records from ≥2 sources. Shaping computes `observation_group` (`shaping.py:1086-1093`) and `observation_groups_multi_source` (`:515, :1204-1205`), but no public file carries either (grep over the release copies = 0). | recorded-execution; code |
| K5-G5 | Re-sightings are recorded. `record_resightings` appends one `claim_evidence` link per re-asserted claim to the execution's capture. The link is uncapped and unfiltered, one per (claim, capture), and replays write nothing (`claim_sink.py:41-46, 293-330`). The synthetic capture is one per (connector, source, genre, run), with `retrieved_by_run_id`, `retrieved_at = clock_timestamp()` and `capture_classification = 'synthetic'` (`:1167-1236`). **Hosted deployment of P31.7 is not verified here.** | code |
| K5-G6 | Run metrics come from `ingest_run_completion` (status, `finished_at`, considered/inserted/duplicate; granted to `sig_read_public`) and 387 WORM run rows over 208 sources, dated 2026-09-16…09-30 (J1 §B). J3 brings them into the spine as `ingest_run_report` (TX-04) and publishes `runs.jsonl` (TX-03). | cited (J1, J3) |
| K5-G7 | Disappearances are detected but written only to the run JSON, never to the spine (F-229). J3's `ingest_run_report.disappearances` is a per-run count, not per record. | cited |
| K5-G8 | Contradiction table: 2 open, on one subject (`claimed_device_count`, `use_restriction`) (C3 §4.11). | cited |
| K5-G9 | After K4's placement: the largest dossiers by records are US 200,222 (100 sources, Census state polygons incl. PR/VI) and California 28,334 (11). The top (dossier, source) pair is California × the OSM/DeFlock ALPR layer, with 22,930 records. (dossier, source) pairs: country 242 · US state 186 · non-US admin-1 (≥10 records) 284 · county 3,567 · place (≥10) 4,730 = **9,009**. California spans 4 licence compartments: `osm_physical` 22,930 · `public_record` 5,294 · `operator_accepted` 87 · `portal` 46. | recorded-execution |
| K5-G10 | Site-level slices by K4 key, measured with parquet (zstd) and csv.gz: California 2,420,992 / 2,583,852 B; US 17,578,570 / 18,913,304 B; Harris County 404,830 / 434,817 B; Houston 249,929 / 269,621 B. | recorded-execution |

---

## 2. Design principles (binding on every DSRC ticket)

- **K5-P1 One computation, both directions.** Dossier → sources and source → dossiers come from one set of rows emitted
  once. A number shown in one direction is identical in the other (SIG-TRANSP-D08).
- **K5-P2 Every figure sums from its sources.** A dossier figure is the sum of its per-source breakdown, or is labelled
  with why it is not (e.g. "distinct records; a record can have claims from several sources").
- **K5-P3 "When" has two clocks, both named.**
  - "First seen by SIG" and "last seen by SIG" come from captures.
  - "Source-reported date" (`observed_at`/`valid_from`) is shown only where the source gives one.
  - Neither may be presented as the installation date.
- **K5-P4 Honest absence.** The absence kinds are the J3 T-5 vocabulary plus `run_level_only`, `not_reasserted`,
  `not_typed` and `not_evaluable`. They are shown where re-sightings, technology typing or co-location are not available.
  The page never shows 0 for "not measured".
- **K5-P5 No bare ids.** Every source appears by name, linked to its source page (J3 TX-05). The id is secondary text.
  Personal-handle ids are renamed first (DR-C3-13; ACT-06).
- **K5-P6 Zero-JS baseline, bounded pages.** The page carries 0 scripts and is ≤150 KiB, with tables of ≤50 rows per page.
  Enhanced interactions are a separate, K0-gated layer.
- **K5-P7 Licence-true downloads.** One file per compartment licence. Attribution is rendered from the registry. Nothing
  is offered before the attribution, terms-withdrawal and egress gates pass (J3 §6.7–§6.8).

---

## 3. The data contract

### 3.1 Computation (exporter, one snapshot)

A new `EXPORT_QUERIES` key, `claim_sightings`, reads the published claims (`{PUB_CLAIM_GATE}`). It runs over an
explicit-column view granted to `sig_export` only (J3 T-2):

```sql
SELECT c.claim_id, c.subject_id, c.predicate_id, ea.source_id,
       min(ec.retrieved_at)                                                  AS first_seen_at,
       max(ec.retrieved_at)                                                  AS last_seen_at,
       (array_agg(ec.retrieved_by_run_id ORDER BY ec.retrieved_at))[1]       AS first_run_id,
       (array_agg(ec.retrieved_by_run_id ORDER BY ec.retrieved_at DESC))[1]  AS last_run_id,
       count(DISTINCT ec.retrieved_by_run_id)                                AS sighting_runs,
       bool_or(ce.binding_status = 'actual_capture')                         AS has_actual_capture
FROM claim c
JOIN claim_evidence ce   USING (claim_id)
JOIN evidence_capture ec USING (capture_id)
JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
WHERE {PUB_CLAIM_GATE}
GROUP BY 1,2,3,4
```

- **Streaming.** The query streams alongside TX-08a's statements pass: 2.42 M rows today, about 150 B each, about
  360 MB through the cursor (inference). Python joins `subject_id → placement` from K4's JUR-02b and accumulates:
  - per (dossier key, source): records, located records, claims, claims by predicate, subjects by entity type, subjects by
    technology (PKG-07), placement basis and check counts, first and last seen, first and last run;
  - per (dossier key, source, run) or per (dossier key, source, month): first-seen claims, re-sighted claims, and
    first-seen records;
  - per (dossier key): the same totals, which are the sums.
- **Roll-up.** A record counts in every ancestor of its placement chain: place → county → admin-1 → country (K4 §5.3).
- **Latest complete run.** "Not re-asserted in the latest complete run" = claims whose `last_run_id` ≠ the source's latest
  run with status `ok`. Partial, `quota_reached` and failed runs are excluded; J3 TX-03 supplies the status. This is a
  derived stand-in for per-record disappearance until F-229 is fixed.
- **Contradictions.** Contradiction records are placed through their subject.
- **Coordinate conflicts.** Counted per source from the shaping envelopes.
- **Co-location.** Once DSRC-04 publishes `observation_group`, cross-source co-location candidates are counted per
  (dossier, source pair).

### 3.2 `sig.dossier-sources/1` (one per dossier, `web/dossier_sources/<slug-path>.json` + release copy)

```jsonc
{
  "schema": "sig.dossier-sources/1",
  "release": {"label": "sig-YYYY-MM-DD.N", "publication_id": "p-…", "as_of_world": "…"},      // G3 REL-02
  "jurisdiction": {"jkey": "iso3166-2:US-CA", "slug_path": "usa/ca", "name": "California",
                   "level": "state_province", "chain": ["iso3166-1:US"], "boundary_vintage": "census.tiger.2025"},
  "definitions": {"records": "published observation-level records placed here", "...": "..."},  // named, footnoted
  "totals": {
    "records": 28334, "located_by_point": 28334, "placed_by_declared": 0,
    "claims": 90467, "sources": 11, "compartments": ["osm_physical","public_record","operator_accepted","portal"],
    "first_seen_at": "…", "last_seen_at": "…",
    "claims_by_predicate": {"camera_latitude": 0, "...": 0},                // from statements (all predicates)
    "records_by_entity_type": {"deployment": 28334},
    "records_by_technology": "not_typed",                                    // until PKG-07
    "coordinate_conflicts_intra_source": 0, "declared_here_located_elsewhere": 919,
    "located_here_declared_elsewhere": 0, "contradictions_open": 0,
    "cross_source_colocated_candidates": {"not_evaluable": "observation_group not yet exported"}
  },
  "provenance_summary": {                                                    // SIG-UI-044, dossier scope (replaces surfaces.site)
    "artifact_count": 11, "tier_distribution": {"untiered": 0, "W1": 0, "W3": 0},
    "sources_with_published_claims": 11, "independent_lineages": {"not_evaluable": "derived_from unset (PKG-12)"},
    "date_range": {"earliest": "…", "latest": "…"}, "rules_applied": ["placement@1","p27.3/1.0.0"],
    "human_review_status": "unreviewed", "scope": "dossier"
  },
  "figures": [                                                               // one per material figure on the dossier page
    {"figure_id": "records", "label": "Records", "value": 28334, "definition": "records",
     "artifact": "web/dossier_sources/usa/ca.json", "pointer": "/totals/records",
     "by_source": [{"source_id": "…", "value": 22930}, "…"], "sum_rule": "sum"}
  ],
  "sources": [
    {"source_id": "…", "name": "…", "publisher": "…", "publisher_type": "…", "lifecycle": "published",
     "source_page": "/sources/<id>/", "runs_page": "/sources/<id>/runs/",
     "licence": {"spdx": "…", "compartment": "…", "attribution": "…"},        // from the registry (J3 T-4)
     "records": 22930, "share": 0.809, "located_by_point": 22930, "placed_by_declared": 0,
     "claims": 68790, "claims_by_predicate": {"...": 0}, "records_by_entity_type": {"deployment": 22930},
     "records_by_technology": "not_typed",
     "placement_checks": {"consistent": 22930, "outside_declared": 0, "axis_swap_suspected": 0},
     "first_seen": {"at": "…", "run_id": "…"}, "last_seen": {"at": "…", "run_id": "…"},
     "sightings": "per_run" ,                                                // | "run_level_only" (fallback, §3.3)
     "latest_run": {"run_id": "…", "finished_at": "…", "status": "ok"}, "freshness_state": "on_time",   // J3 §4.6
     "not_reasserted_in_latest_complete_run": 0,
     "coordinate_conflicts_intra_source": 0, "contradictions": [],
     "series": [{"period": "2026-09", "records_first_seen": 22930, "claims_first_seen": 68790, "claims_resighted": 0}],
     "downloads": [{"compartment": "osm_physical", "format": "parquet", "path": "…", "bytes": 0, "rows": 0, "sha256": "…"}],
     "known_issues": ["…"]}
  ],
  "cross_source": {"colocated_pairs": {"not_evaluable": "…"}, "contradictions": []},
  "placement": {"by_basis": {"point_in_polygon": 28334, "declared": 0},
                "declared_elsewhere_located_here": [], "declared_here_located_elsewhere": [{"jkey": "iso3166-2:US-FL", "records": 838}]},
  "runs_file": "web/dossier_sources/usa/ca.runs.jsonl.gz",
  "downloads": [{"compartment": "…", "licence": "…", "files": ["…"]}]
}
```

**`<slug-path>.runs.jsonl.gz`.** One row per (source, run) at country and admin-1 level:

```
{source_id, run_id, started_at, finished_at, status, claims_first_seen, claims_resighted, records_first_seen}
```

County and place dossiers carry monthly `series` only and link to the source's run log (J3 `/sources/<id>/runs/`) for
run detail.

**Invariants (tested).**

- Σ `sources[].records` = `totals.records`, because each record has exactly one source today. If multi-source records
  appear (after DSRC-04), the rule becomes "distinct records" and the figure's `sum_rule` changes to `distinct`, disclosed.
- Σ `sources[].claims` = `totals.claims`.
- Every `figures[].by_source` sums to `value` under its `sum_rule`.
- The same (dossier, source) numbers appear in J3's `sources/<id>.json` → `contributions[]`.

### 3.3 Fallback when re-sighting links are absent (hosted state unverified)

If a source's claims have exactly one capture link each and that source has more than one completed run, the export
cannot tell "not re-sighted" from "re-sightings not recorded". In that case:

- `sightings = "run_level_only"`;
- `last_seen` = `{not_recorded}`;
- `not_reasserted_in_latest_complete_run` = `{not_evaluable}`;
- only first-seen is shown.

The export runs this check per source and prints the reason on the page. There are no silent zeros (K5-P4).

### 3.4 Sizes

| item | today (measured or derived) | growth | notes |
|---|---|---|---|
| (dossier, source) rows, whole release | 9,009 (K4 page set: countries, US states, non-US admin-1 ≥10, counties ≥1, places ≥10) | with sources and places | ≈1.0–1.5 KB each → **≈9–14 MB** of `dossier_sources/*.json` in total (inference) |
| largest core artifact: `iso3166-1:US` | 100 sources | +≈80 B per source-month in `series` | **≈120–150 KB** (inference); within the page-data budget only if the explorer page renders ≤50 rows per page |
| largest runs file: US | ≈190 (source, run) rows today (J1: 387 runs / 208 sources ≈ 1.9 per source) × ≈200 B ≈ 40 KB | weekly cadence → ≈5.2k rows/yr ≈ 1 MB raw / ≈0.15 MB gz | country/admin-1 only (≈712 pairs × 52 ≈ 37k rows/yr ≈ 4.5 MB raw release-wide) |
| California | 11 sources → ≈15 KB | small | — |
| per-dossier download slices, site level | CA 2.4 MB parquet / 2.6 MB csv.gz; US 17.6 / 18.9 MB; Harris 0.40 / 0.43 MB; Houston 0.25 / 0.27 MB | with records | measured (K5-G10) |
| per-dossier download slices, claim level (`statements`) | CA ≈3–7.5 MB; US ≈24–60 MB | with claims | inference from J3's 80–200 MB for 2.42 M claims (≈33–83 B per claim compressed) × 90,467 / 718,138 claims |
| materialising every level | ≈4× the national bytes (country + admin-1 + county + place) ≈ 0.5–1 GB per release | — | **not recommended**; see D-K5-1 |

---

## 4. Page layout

### 4.1 On the dossier page (every level): "Where this comes from"

The section replaces today's "How we know this: Sources: id, id" row and the national block (C3 NEW-3; DR-C3-02).

```
Where this comes from                                            as of release sig-… (data as of …)
  28,334 records from 11 sources · first seen by SIG 2026-09-15 · newest source run 2026-09-26
  [Explore all 11 sources →]  [Download this dossier's data →] (after gates)

  Source (linked)                         Records   Share   First seen   Last seen    Latest run   Licence
  OSM / DeFlock ALPR layer (community)    22,930    81%     2026-09-15   2026-09-26   ok · on time ODbL-1.0
  Cal OES camera layer (state agency)      4,203    15%     …            …            …            …
  … top 5; "6 more →"

  How we know this — for this dossier (not site-wide)
    Artifacts 11 · Tier distribution … · Sources with published claims 11 · Date range … · Rules placement@1, p27.3 ·
    Human review: not yet human-reviewed
```

- **Share bars.** Inline SVG or CSS width, zero JS, with the number printed beside each bar for screen readers and print.
- **Figures.** Each figure on the page is rendered by `<Figure>` (J3 TX-09) and gains a "from 11 sources" link to
  `…/sources/#fig-<id>`, where its breakdown table sits. See §5.

### 4.2 Explorer page `/dossier/<path>/sources/` (and `index.json` twin)

| block | contents | no-JS baseline | enhanced (K0-gated) |
|---|---|---|---|
| Header | totals, named definitions, release stamp, placement vintage, the six-component dossier-scope summary | static | — |
| Contribution table | all sources: name, publisher type, lifecycle, records, share, located / declared, claims, first seen, last seen, latest run + freshness state, conflicts, licence | ≤50 rows per page. Sort via pre-rendered GET routes (`…/sources/sort/{records|first-seen|last-seen|freshness|conflicts|name}/`) **only for dossiers with >25 sources** (the US, a few states); smaller dossiers get one table sorted by records. | client-side sort + text filter + facet chips (publisher type, licence/compartment, technology, lifecycle) over `index.json`. Island ≈≤10 KB JS. |
| Per-source detail | one `<details>` per source: claims by predicate, records by entity type and technology, placement checks, disagreements, the last 10 contributing runs (linked `/sources/<id>/runs/#run-<id>`), downloads, known issues (J3 TX-06), "view on map" (K1 bbox + source filter) | `<details>` (no JS) | none needed |
| Over time | monthly first-seen records per source (top 8 + "other"), as a stacked-bar **static SVG** with a `<table>` twin; each period links to the runs in it | static SVG + table | hover values, brushing a range to filter the table (JS; K6 shares the chart component) |
| Where sources agree or disagree | (a) coordinate conflicts within a source; (b) cross-source contradictions (records, linked); (c) declared vs located (K4); (d) co-located records from ≥2 sources (candidates for the same installation, never merged; `not_evaluable` until DSRC-04) | tables | link-through to K2's graph neighbourhood (JS) |
| Placement | how records reached this jurisdiction: by point vs declared, checks, boundary vintage | table | — |
| Downloads | per compartment: licence, attribution, rows, bytes, sha256, formats; the `dossier_sources` JSON (CC-BY-4.0); API equivalents | links | — |
| Cite, dispute | release-pinned citation (J3 TX-13a), dispute contact (Q-29) | static | — |

**Budgets.**

- Explorer page ≤150 KiB transferred and 0 scripts at baseline.
- The US page (100 sources) pages its table at 50 rows.
- The page is added to Lighthouse CI: one state explorer and the US explorer.

**Print.** The explorer prints as an appendix: the tables, with `<details>` expanded by print CSS.

---

## 5. Per-figure provenance (replacing the site-wide block)

- **What a figure means.** A "material figure" is any number on a dossier (J3 §5.4 classes): records, located share,
  sources, open questions, disagreements, and later contract and cost figures. Each comes from `figures[]`, carrying:
  - the definition;
  - the artifact and JSON pointer (TX-09's `data-artifact` / `data-pointer`);
  - `by_source`;
  - `sum_rule`;
  - a link to the release record list `/r/<pub>/c/<comp>/jurisdiction/<slug-path>/` for the records behind it (K4 §7).
- **No site-wide fallback.** The dossier page passes its own `provenance_summary` to `BaseLayout`. A page that has none
  shows the block titled **"Site-wide (not specific to this page)"**, never unlabelled (DR-C3-02). A build check fails any
  dossier page that renders `surfaces.site`.
- **Honest labels** (from C3 NEW-13):
  - "Independent sources" becomes "Sources with published claims" until lineage de-duplication is computable
    (`derived_from`, PKG-12; F-235).
  - "Artifacts" counts evidence artifacts behind this dossier's claims. Today that is one synthetic per (source, genre),
    so it roughly equals the number of sources, and the footnote says so.
- **Interaction.**

  | mode | behaviour | JS |
  |---|---|---|
  | no-JS baseline | "from N sources" is an in-page anchor to the breakdown table on the explorer page, plus a `<sup>` definition footnote | none |
  | enhanced | an HTML `popover` (declarative; the `popovertarget` attribute needs **no script** in current browsers) showing the breakdown inline | none |

  The anchor stays as the fallback for older browsers and for print. No JS is needed at all.

---

## 6. Downloads (licence-true, J4/J3)

- **Unit.** One file per (dossier, compartment), because compartments are licence partitions (§42.3; J3 §6.2 "per
  jurisdiction" unit). California has 4 files: ODbL, public-record basis, the operator-accepted database-right basis, and
  the portal CC-BY-SA. Each file comes with `ATTRIBUTION.txt` and `LICENCE.txt` rendered from the registry (T-4), plus
  sha256, rows and bytes.
- **Content.** Claim-level rows follow J3's `sig.statement/1` schema, extended with:
  - K4 `jurisdiction_key`, `placement_basis`, `placement_check`;
  - K5 `first_seen_at`, `last_seen_at`, `first_run_id`, `last_run_id`, `sighting_runs`.

  Site-level rows are the sites schema plus the K4 placement columns.
- **Scope.** Only published (gate-passed) claims are included. Raw captured bytes are never offered per dossier; they stay
  on source pages under the J4 lane table (J3 §5.3, §6.9). No per-dossier raw archive.
- **Materialisation (D-K5-1).** Recommended:
  - Country and admin-1 files are materialised on the zero-egress mirror (≈2× the national bytes).
  - County and place slices are **not** materialised. Instead:
    - the national per-compartment files carry `jurisdiction_key` and the chain columns;
    - the page shows a copy-paste DuckDB one-liner, e.g.
      `SELECT * FROM 'osm_physical/statements.parquet' WHERE list_contains(jurisdiction_chain,'us.census.geoid.county:48201')`;
    - optionally, a rate-limited release-backed API export (`/v1/releases/{pub}/statements?jurisdiction=…`, G3 REL-05)
      serves the same rows.
- **Gates.** No link goes live before all of these:
  - TX-11: mirror, `assert_low_egress`, kill switch.
  - ACT-07/PKG-08: attribution integrity.
  - D-J3-5: terms-forbidden sources withdrawn.
  - TX-01: scrub.
  - E4: decision on the US-located database-right rows (K4 NEW-4).

  Until then the section reads "Downloads for this dossier are not yet available: <reason>" (agent-drafted).

---

## 7. Filters and sort (summary)

| control | no-JS baseline | enhanced | JS dependency |
|---|---|---|---|
| sort the contribution table | GET sort routes (dossiers with >25 sources); default sort by records otherwise | client-side sort | ≈3 KB; K0 |
| filter by publisher type, licence, technology, lifecycle | links to J3 facet routes `/sources/by/<dim>/<value>/`, showing all sources in that facet (not dossier-scoped) | in-page facet chips | K0 |
| time range | monthly table + static SVG; the runs table on source pages | brush on the chart filters the table | chart island (shared with K6) |
| find a source | browser find-in-page; A–Z order | text filter | ≈1 KB |

---

## 8. Draft requirements and acceptance tests

Ids are provisional (`SIG-DSRC-Dnn`). T1 folds them into SIG-UI, SIG-EXPORT and SIG-TRANSP.

| id | requirement (draft spec text) | acceptance test |
|---|---|---|
| SIG-DSRC-D01 | For every dossier, the export MUST emit a contribution artifact (`sig.dossier-sources/1`), computed in the release's single read snapshot. Per-source counts MUST sum to the dossier totals under a declared rule. | JSON Schema validates for all dossiers; Σ checks pass; recompute from `statements` + placement = 0 diffs |
| SIG-DSRC-D02 | Each dossier MUST show, per contributing source: name (linked to its source page), publisher type, records, share, located vs declared, claims by predicate, records by entity type and technology (or `not_typed`), licence and latest-run state. It MUST NOT show bare source ids. | crawl: every source mention on dossier pages links `/sources/<id>/`; 0 bare `camreg_*`/`dot_511_*` text nodes outside secondary id spans |
| SIG-DSRC-D03 | Each dossier MUST show when each source contributed: first and last seen by SIG, first and last run (linked to the run log), and a per-period series. Where re-sightings are not recorded it MUST say `run_level_only` instead of showing a last-seen date. | fixture with 3 runs (insert, re-sight, drop): first/last/`not_reasserted` correct; fixture without re-sighting links → `run_level_only` rendered |
| SIG-DSRC-D04 | Every material figure on a dossier MUST carry a definition, an artifact pointer and a per-source breakdown that reconciles to it. The "How we know this" module on a dossier MUST be computed for that dossier; a site-wide block MUST be labelled "Site-wide". | build check: no dossier renders `surfaces.site`; every `<Figure>` on dossier pages has `data-pointer` and a breakdown anchor that resolves; the six SIG-UI-044 components are present with scope = dossier |
| SIG-DSRC-D05 | Each dossier MUST show where sources disagree or overlap: intra-source coordinate conflicts, cross-source contradictions, declared-vs-located disagreements, and co-located records from different sources. Where one of these is not computable it MUST show `not_evaluable` with its reason. | counts equal the release recompute; `not_evaluable` shown until `observation_group` is exported; after DSRC-04, co-located pairs == the recompute over published `observation_group` |
| SIG-DSRC-D06 | The explorer MUST be fully usable without JavaScript: sort (where >25 sources), per-source detail, the over-time chart with a table equivalent, and downloads. Enhanced interactions MUST be optional and within the K0 budget. | 0 `<script>` at baseline; ≤150 KiB; axe 0 violations; the SVG chart has a `<table>` twin with equal values |
| SIG-DSRC-D07 | Dossier data downloads MUST be split by licence compartment, carry registry-rendered attribution and licence, sha256, rows and bytes, and MUST NOT be linked before the attribution, terms-withdrawal and egress gates pass. | every listed file verifies; one file = one licence; 0 download links while any gate is open (config test) |
| SIG-DSRC-D08 | The contribution of a source to a dossier MUST be identical on the dossier's explorer and on the source's page. | parity test over all (dossier, source) pairs (≈9k) |
| SIG-DSRC-D09 | The explorer MUST have a JSON twin, and the release-backed API MUST serve the same data. | HTML == JSON twin == `/v1/releases/{pub}/dossiers/{key}/sources` on a 50-dossier sample (G3 V7 extension) |

**Acceptance journeys** (agent walkthroughs, not user research, P4):

- **Journalist, California.** Opens the California dossier and follows "from 11 sources" beside Records. Finds that 81% of
  records come from the OSM/DeFlock ALPR layer (a community map, ODbL), and 838 records declared "CA" are located in
  Florida. Opens that source's page and its last run. Cites the release-pinned URL.
- **Advocate, Oklahoma City.** Sees "391 records from 1 source", with the evidence types absent. Learns from the source
  row that it is a community map, when SIG first saw it, and that it was re-sighted in the latest run. Prints the dossier
  with the sources appendix.
- **Researcher, Harris County.** Uses the DuckDB one-liner or the API to pull the county's claims with provenance columns
  and licence files. Verifies the sha256.

---

## 9. Round-11 ticket outline

| key | title | size | scope (one line) | depends | live / gate |
|---|---|---|---|---|---|
| **DSRC-01** | Contribution export | M | `claim_sightings` view + query; accumulation per (key, source, predicate, run or month); `dossier_sources/*.json` + runs files; dossier-scope `provenance_summary`; `figures[]`; source-side `contributions[]` from the same rows; invariants as tests | K4 JUR-02b (placement), J3 TX-01 (scrub), TX-03/04 (runs), TX-08a (statements pass); **absorbs PKG-10's per-dossier "How we know this"** | — |
| **DSRC-02** | Dossier section + explorer page | M | "Where this comes from" on every dossier; `/dossier/<path>/sources/` + JSON twin; sort routes (>25 sources); `<details>` per source; SVG chart + table; dossier-scope HWKT; "Site-wide" label rule + build check | DSRC-01; K4 JUR-04 (routes); J3 TX-05 (source pages; interim link to `/data-freshness/#<id>`); TX-09 (`<Figure>`); ACT-06 (handle renames) | via release |
| **DSRC-03** | Per-dossier downloads | M | per-compartment slices at country/admin-1; placement + sighting columns in the national statements; DuckDB/API recipes for county/place; ATTRIBUTION/LICENCE per file; gate wiring | DSRC-01; J3 TX-08a, TX-10b, TX-11; ACT-07/PKG-08; D-J3-5; E4 (K4 NEW-4); D-K5-1 | republish (Class S) |
| **DSRC-04** | Agreement / disagreement view | S | publish `observation_group` + a multi-source cell count (sites files + dictionary); cross-source co-location per dossier; contradiction placement; intra-source conflict counts | DSRC-01; PKG-06b (same-source duplicates, ED-32); resolution cluster-id export (C3 NEW-18 owner) optional | via release |
| **DSRC-05** | Enhanced interactions | S | client-side sort/filter/facets; chart hover/brush; only within K0's ADR budget | DSRC-02; **K0** decision; K6 chart component | via release |
| **DSRC-06** | Acceptance | S | parity (D08, D09), invariants, budgets, crawl for bare ids, journeys | all above; G3 REL-04 checks | with the release |

**Exactly-one ownership (P9).** Other stream items stay with their owners:

| item | owner |
|---|---|
| per-dossier provenance | moves from PKG-10 into DSRC-01 (the rest of PKG-10 stays: coverage clamp, freshness `not_evaluable`, map suppression) |
| figure pointer mechanics | TX-09 |
| source pages | TX-05 |
| run records | TX-03/04 |
| statements | TX-08a |
| raw bytes | TX-12 |
| disappearance records | F-229's owner (PKG-12 telemetry) |
| lineage independence | PKG-12 |
| technology | PKG-07 |
| keys | K4 |

---

## 10. Operator decisions needed

| id | question | recommendation | feeds |
|---|---|---|---|
| D-K5-1 | Which dossier levels get materialised download files | country + admin-1 materialised; county/place via key columns + recipe (+ optional rate-limited API) | DSRC-03 |
| D-K5-2 | Wording for "first/last seen by SIG" vs "source-reported date" | adopt K5-P3 labels; approve the agent-drafted glossary text verbatim | DSRC-02 |
| D-K5-3 | Show sources that no longer contribute (withdrawn, disappeared, not re-asserted) | yes, as "previously contributed" with dates and reason, below the table | DSRC-02 |
| D-K5-4 | Merge PKG-10's per-dossier provenance into DSRC-01 | yes (one owner) | S1 / T3 |

---

## 11. Risks

| id | risk | mitigation |
|---|---|---|
| R-K5-1 | "First seen" is read as "installed on" | K5-P3 labels; source-reported dates shown only when present; glossary |
| R-K5-2 | Re-sighting links absent on hosted → misleading "last seen" | per-source `run_level_only` detection (§3.3); verify at DSRC-01 against a hosted read-only sample (operator go) |
| R-K5-3 | The explorer amplifies existing defects (handle ids, misattribution, terms-forbidden rows) | ordering after ACT-06, ACT-07 and D-J3-5 (J3 R-1) |
| R-K5-4 | Per-dossier downloads multiply bytes and egress | D-K5-1; mirror only; no raw per dossier |
| R-K5-5 | One community layer dominates most state dossiers (e.g. 81% of California), inviting over-reading | share column + publisher type + "community map" label; evidence-type absences shown |
| R-K5-6 | Export time grows with the extra aggregation | same pass as statements; measure in DSRC-01 (J3 budget: export +≤5 min) |

---

## 12. Interfaces

- **K4:** keys, placement columns, slug paths, roll-up rule, the unplaced report (its sources table reuses DSRC-01 rows).
- **J3:**
  - TX-01 scrub;
  - TX-03/04 runs;
  - TX-05 source pages (`contributions[]` from DSRC-01);
  - TX-08a statements;
  - TX-09 `<Figure>`;
  - TX-10/11 downloads + mirror;
  - TX-13a citation.
- **G3:** REL-02 stamp; REL-04 V6 number truth (dossier figures recompute from the release files); V7 API parity;
  REL-05 release-backed routes.
- **K0** (JS budget), **K1** (map deep-link with source filter), **K2** (graph neighbourhood link), **K6** (shared chart
  component), **K10** (source pages), **K13** (IA).
- **F5:** PKG-06b, PKG-07, PKG-10 (partly merged), PKG-12.
- **E4:** rights for the US-located database-right rows before downloads.

---

## 13. Limits

- No spine query (P3). The derivability of first/last seen rests on code at the chain tip. Hosted deployment of the P31.7
  re-sighting hook and the live `claim_evidence` volume were not observed.
- The claim-level (statements) sizes are inference, because no statements file exists yet. Site-level slices were
  measured.
- Per-predicate counts per dossier need the statements pass. Today's site files carry only the four shaping predicates'
  claim ids (`shaping.py:107`), so no per-predicate table was computed here.
- Sizes of the enhanced JS layer are estimates pending K0 and K12a.

---

## 14. New findings (`findings/incoming/K4K5.csv`)

| id | title (short) | sev |
|---|---|---|
| NEW-8 | The co-location key (`observation_group`) and its multi-source count are computed at export but never published. Every published site row has `n_sources = 1` and all 5,290 coordinate conflicts are intra-source, so no public surface can show where independent sources corroborate or disagree, although 3,839 ≈10 m cells (1,534 exact points) hold records from ≥2 sources. | S2 |
| NEW-9 | Published site files carry no temporal field (no first/last seen, retrieval time or run), so no public artifact can say when a record entered SIG or was last confirmed by its source | S2 |

K4's NEW-1…NEW-7 are in the same CSV. Related, not re-raised: C3 NEW-3/12/13/18/19; J1 NEW-4/6/8; J3 NEW-3; F-229; F-235;
ED-31/32.

---

Work window closed **2026-09-30T22:02:52Z** (`date -u`; K4 and K5 written in the same window).
