# J1 — Current exposure inventory

Row **J1** of `META_PLAN.md` §6 Stream J (owner R, read-only, depends A1). Written 2026-09-30 by Claude Code
(Opus 5.5) in the planning worktree (`claude/next-phase-planning`). Window `date -u`: **2026-09-30T16:44:40Z →
16:54:43Z** (live reads), write-up after. Findings: `findings/incoming/J1.csv` (NEW-1…NEW-13).

**Method.** (1) Live reads of the public bucket, the static site and the read API: **38 HTTP GETs** (budget 60), UA
`SIG-planning-J1/1.0`. (2) Read-only `gcloud` listings/describes of the three buckets, the LB and Cloud Logging, plus
`cat` of four small restricted objects (3 run rows, 1 OCFL `metadata.json`; keys described only, values not copied).
(3) Repo reads at planning HEAD (tree == chain tip `b051732c` for everything cited). Three read-only research passes
swept `db/deploy`, `exports/src` and `web/src` + `api/src`. I re-read every load-bearing line myself. Lines only the
research passes read are marked **(R)**.
**Evidence classes:** `live-read` (bucket, site, API, gcloud), `code` (file:line), `inference` (labelled).
**Release under inspection:** `sig-2026-09-27-ce480ab1`. The public `manifest.json` sha256 `717aeb44…` equals the A1
baseline value, so the release has not changed since the freeze.

Captured files (session scratch, not committed; sha256 prefix): `manifest.json 717aeb4499523acf`,
`datapackage.json 0492b342be379ae4`, `provenance.ttl 3cd2378ce1366181`, `web/freshness.json c5a343820633a125`,
`web/evidence.json 3df209d5545846cd`, `openapi.json 0ad37629b85238bf`, `exclusions.json 2454162c6e35bcf3`.

---

## 0. Summary

- **Public today:**
  - A complete, checksummed, licence-separated bulk release: 132 artifacts, 1,048,876,904 bytes, 14 compartments,
    7 formats. It is in an anonymously listable bucket, but **no page on the site links to it**.
  - A static site of 20 routes, whose data-freshness page shows 3 facts per source with bare source ids.
  - An evidence page that shows **no** claim evidence.
  - A read API with 18 routes. Its best provenance endpoint (`/v1/evidence`) returns a **synthetic** capture and
    claims `bytes_available: true`.
- **Biggest internal assets not exposed:**
  - 350 real OCFL captures (upstream URL, retrieval time, digest, bytes; 75.7 MiB).
  - 387 write-once run rows across 208 sources (robots decisions, disappearances, document outcomes, refusals).
  - `ingest_run_completion` counts, which the public API role is already granted.
  - The 342-row source registry (341 with homepage URLs).
  - Prior releases (2 × 2026-09-24).
  - The P32.13 release/record tree (≈475k files) and the P32.14 per-compartment search, both built and undeployed.
- **Three live truth defects surfaced by the audit:**
  - 3,272 of 4,834 rows in the CC-BY-4.0 `sig_graph` download are attributed to "DeFlock community map" although
    they come from Iowa DOT, Washington DC and Gold Coast registries. The live API does the same for the EFF Atlas.
  - 61,603 public rows carry an empty attribution although attribution is required.
  - Every page's "belief-pinned permalink" ignores its as-of parameters, and no public release archive exists.

---

## A. What a member of the public can get today

### A.1 Bulk downloads — `https://storage.googleapis.com/zeta-medley-508121-u7-sig-public/`

The bucket grants `roles/storage.objectViewer` to `allUsers`, and public access prevention is `inherited`
(`gcloud storage buckets get-iam-policy`). An anonymous `GET ?max-keys=5` returns **200** with an XML listing, so
anyone who knows the bucket name can enumerate and download it. It holds 134 objects: the 132 manifest artifacts,
`manifest.json` and `LICENCES.json`. There are no release-id prefixes: each deploy overwrites the paths in place with
`rsync` (`ops/src/ops/deploy.py:93-98`).

**Common to every compartment below:**
- The formats are csv, geojson, jsonl, jsonld, parquet, pmtiles and sqlite, plus a web tile at
  `web/tiles/<c>-sites.pmtiles` (the `sig_graph` compartment differs; see its row).
- Every artifact carries `sha256`, `byte_size`, `license`, `media_type` and `row_count` in `manifest.json`.
- The release id appears only in `manifest.json`, `datapackage.json` and `LICENCES.json`, never in the paths.
- There is no data dictionary: 0 of 104 `datapackage.json` resources carry a Table Schema.

| compartment (prefix) | licence (SPDX) | rows (sites) | bytes (all formats + tile) |
|---|---|---|---|
| `osm_physical/` | ODbL-1.0 | 154,705 | 562,168,797 |
| `public_record/` | LicenseRef-PublicRecord-FactualCompilation | 39,921 | 154,450,629 |
| `operator_accepted/` | LicenseRef-OperatorAccepted-DBRight | 21,682 | 85,763,406 |
| `portal/` | CC-BY-SA-4.0 | 10,054 | 51,452,023 |
| `sig_graph/` | CC-BY-4.0 | sites 4,834 · coverage 127 · **freshness 178** · jurisdictions 55 · sharing_edges 632 | 22,436,708 |
| `ogl_uk3/` | OGL-3.0 | 1,514 | 5,731,496 |
| `dot511_ccbysa2/` | CC-BY-SA-2.0 | 3,000 | 16,798,188 |
| `ccby3/` | CC-BY-3.0 | 861 | 3,337,034 |
| `ogc_canada2/` | OGL-Canada-2.0 | 160 | 766,038 |
| `ottawa_odl2/` | LicenseRef-Ottawa-ODL-2.0 | 146 | 704,677 |
| `stalbert_odl1/` | LicenseRef-StAlbert-ODL-1.0 | 80 | 345,166 |
| `peel_odl1/` | LicenseRef-Peel-ODL-1.0 | 37 | 154,581 |
| `metadata` (root) | CC-BY-4.0 | `datapackage.json`, `exclusions.json`, `provenance.ttl` | 212,994 |
| `web/` | CC-BY-4.0 | 13 site JSONs (`evidence`, `freshness`, `coverage`, `dossiers`, `network`, `research_queue` **144,060,710 B**, …) | 144,555,167 |

**Row schema of `<c>/sites.*`** (CSV header, range-read): `claim_ids, entity_id, entity_type, geometry,
jurisdiction, label, n_observation_claims, n_sources, point_status, precision, rights_attribution,
rights_attribution_required, rights_id, rights_license, rights_share_alike, rights_source_id, rights_terms_url,
rights_upstream_license, source_id, spdx, tier`.
- Each row carries claim ids, source id and per-row rights (SIG-EXPORT-006).
- Each row lacks the upstream record URL, retrieval time and capture digest.
- Per-row attribution is unreliable (§A.1a).

**A.1a Per-row attribution quality.** Downloaded `sites.sqlite` for 4 compartments (live-read):

| compartment | rows | attribution required but empty | terms_url empty | notes |
|---|---|---|---|---|
| `sig_graph` | 4,834 | 0 | 3,272 | **3,272 rows attributed "DeFlock community map"**: `dot_511_ia` 1,708, `camreg_washington_dc` 940, `camreg_goldcoast_au` (NEW-2) |
| `public_record` | 39,921 | **39,921 (100%)** | 39,921 | 59 sources (NEW-3) |
| `operator_accepted` | 21,682 | **21,682 (100%)** | 21,682 | 92 sources (NEW-3) |
| `portal` | 10,054 | 0 (10,004 rows `attribution_required=0`) | 8,841 | |

**Root cause (code).** `db/src/db/claim_sink.py:955-973` looks up a `rights_record` **by SPDX only**
(`… WHERE spdx_expression = %s ORDER BY rights_id LIMIT 1`). Every source with that SPDX inherits the
first-inserted row's `attribution_text`. `ops/src/ops/seed.py:86` seeds CC-BY-4.0 with the attribution "DeFlock
community map". That this seed row was the first CC-BY-4.0 row is an **inference**.

### A.2 Release metadata (public bucket root and `web/`)

| file | what it gives the public | what it lacks |
|---|---|---|
| `manifest.json` (35,157 B) | `release_id`, `content_key`, `reproducibility_inputs{as_of_snapshot, as_of_belief 2026-09-27, ruleset p27.3/1.0.0, resolver 0.0.0}`, 132 artifacts with sha256/size/licence/rows | a link from the site; release history |
| `LICENCES.json` | per compartment: licence, `license_url`, `share_alike`, `attribution` ("…plus the per-row source attribution each record carries (SIG-EXPORT-006)"), paths | per-source licences (it is per compartment) |
| `datapackage.json` (Frictionless, 33,458 B) | 104 resources with `hash`, `bytes`, `licenses`, `format` | **no `schema` on any resource**; no `sources`; 28 manifest artifacts (the web JSONs, tiles, the metadata files) not listed |
| `exclusions.json` (266 B) | `refused: []`, totals 0; note *"P31.16 national re-export … HG-11 pre-gate restricted only"* | the note calls a public file "restricted only" (it may be copy drift) |
| `provenance.ttl` (PROV-O N-Triples, 179,270 B) | 178 `prov:Agent` sources (`"connector source <id>"`), 178 capture `prov:Entity`s, 1 run activity | every capture's `generatedAtTime` = **export time `2026-09-27T00:53:57Z`**; no upstream URL or digest; IRIs under `https://sig-project.org/prov/` (**NXDOMAIN**, `dig`) (NEW-8) |
| `web/freshness.json` | 178 rows: `source, last_successful_run, last_content_change, status, stale_entity_count, volatility_class` | cadence, source name, URL, licence, run counts, errors; all 178 `ok`/`unknown` (F-08) |
| `web/evidence.json` | 255 artifacts: `artifact_id, artifact_type, source, capture_status, permalink, as_of, directness…` | **0 of 255 permalinks are http(s)**: 228 are `sig:connector:…` and 27 are `sig:terms:…`. `title == artifact_id` for 255 of 255, and `claim_views: []` (NEW-4) |
| `/dossier/<slug>.json` (sig-web bucket; linked as "JSON (API form)") | per-jurisdiction dossier JSON | source ids only |

### A.3 Site pages (`https://surveillancegraph.org`, served from `gs://…-sig-web`, deployed 2026-09-27T01:33:57Z)

The bucket holds 20 top-level routes. Beyond A1's list, **`/downloads/`, `/data/`, `/sources/`, `/about/` and
`/sitemap.xml` all return 404**. The sig-web bucket has no `releases/`, `research-dossier/` or `r/` tree (0 matches).
The 8 pages fetched link externally only to themselves. The only download link on any of them is
`/dossier/al.json`. Their visible text never mentions "download", "licence", "API", "manifest" or a release id.

| route | what the user sees (live) | per-source / per-claim provenance shown | source (code) |
|---|---|---|---|
| `/data-freshness/` (+`/stale/ /status/ /volatility/` sorts) | 178 rows: source (raw id such as `camreg_achd_id`), last successful run, last content change, status, stale entities, volatility class | no link, name, cadence, counts or errors; frozen at the release (latest `last_successful_run` 2026-09-26T06:02Z, while `ops/runs/` has rows dated 09-28…09-30; see F-08) | `web/src/pages/data-freshness/[...sort].astro:58` (R); `exports/src/exports/shaping.py:457-478` |
| `/evidence/` | explains the viewer, then shows "**No claims with a full evidence view yet**", plus the How-we-know-this block (Artifacts 255, independent sources 218, date range 2020-01-28…2026-09-26) | none; no `/evidence/<id>/` pages exist (the bucket holds only `evidence/index.html`) | `claim_views` hardcoded `[]` at `exports/src/exports/spine_export.py:1185` |
| `/methodology/` (12,288 B) | fixed prose on tiers, reconciliation, mirrors-not-independent | no source list and no links | `methodology.astro` (R) |
| `/coverage-metrics/` | counted quantities with named denominators, e.g. "2,423,200 of 2,423,200 published tier-0 claims with a resolvable evidence artifact" | none per source | `coverage-metrics.astro:19` (R) |
| `/dossier/<slug>/` (166 objects incl. print and json) | fields, unknowns, "How we know this — Sources: `dot_511_al`" | source ids only; no `[source]` links on real data (inference R: only demo `web_dossier.py` sets `documentUrl`) | `spine_export.py:1495-1501` (R) |
| `/watch/` (+ `citations.txt`) | empty watch; `citations.txt` holds a one-line gap statement | none | |
| `/search/` | client island (2 scripts, 0 forms): a filter over dossiers, sites and sources; source hits go to `/data-freshness/` | none; the P32.14 per-compartment forms are **not** deployed (F-14) | |
| every page | **Cite this page** block: "Belief-pinned permalink (reproducible after SIG corrects itself)" with `?as_of_world=…&as_of_belief=…&ruleset=…` | `GET /evidence/?as_of_world=2020-01-01&as_of_belief=2020-01-01` is **byte-identical** to `/evidence/` (sha256 `b6fc5cdf…`); the params are ignored and no archived release is public (NEW-5) | `web/src/components/Citation.astro:60` |

**Does any page list all third-party sources with links to their upstream?** **No.**
- `/data-freshness/` lists 178 bare ids.
- Registry `homepage_url` is non-empty for **341 of 342** registry sources (`connectors/src/connectors/data/sources.toml`,
  `tomllib` parse; 236 have `ingestion_permitted = true`),
  but no code in `api/`, `exports/` or `web/` references it.
- The only source query in the export is `SELECT source_id, name FROM source_registry`
  (`exports/src/exports/spine_export.py:130-135`) (NEW-7).

### A.4 Read API (`https://sig-api-e5ctyx36jq-uc.a.run.app`, revision `sig-api-00011-wic`)

`/openapi.json` ("SIG public read API" 1.0.0) lists **18 routes**:
- `GET /v1/resolution/{s}/{p}`, `/v1/entity/{t}/{id}`, `/v1/claim/{id}`, `/v1/evidence/{artifact}/{capture}`
- `/v1/search`, `/v1/dossier/{scope}`, `/v1/coverage/{scope}`
- `/v1/contradiction[/{id}]`, `/v1/task[/{id}]`, `/v1/crosswalk`
- `/v1/export`, `/v1/changes`
- `/id/{type}/{uuid}`, `/terms`, `/health`, `/`

**No route lists sources, runs, freshness or releases.**
`GET /v1/releases/x/compartments/y/search` → **404**: the P32.14 route is not in the deployed image, and even the
code default would 503 without `--release-registry` (`ops/Dockerfile:112`).

| route (sampled) | status | response shape (provenance-relevant) |
|---|---|---|
| `/v1/export` | 200 | `{exports:[{name:"entities", format:"parquet", href:"/exports/entities.parquet"}], note, coverage, as_of}`. The href is **404** (confirms F-09); it is hardcoded (`api/src/api/routes.py:466-488`) and does not point at the real bucket. |
| `/v1/changes?since=2026-09-01` | 200 | `events: []`, always (`api/src/api/store_pg.py:872-875`) |
| `/v1/search?q=austin&limit=2` | 200 | `results[{entity_id, entity_type, label, href}]`, plus `license{effective_license, compartments, obligations[{source_id, attribution, license, attribution_required, share_alike, terms_url, upstream_license}]}`. The `eff_atlas_of_surveillance` obligation reads attribution **"DeFlock community map"** with `terms_url ""` (NEW-2). |
| `/v1/entity/deployment/01a0a720-…` | 200 | `facts[{predicate_id, envelope{value, resolution_status, support, supporting_claim_ids, considered_claim_ids, ruleset_version "2026.1", resolver_version, input_digest…}}]`, `attribution[…]`, `as_of` (defaults to *now*, not the release) |
| `/v1/claim/01a0d751-0961-…` | 200 | `{claim_id, predicate_id, value, raw_value, observed_at, source_id, attribution[], genre, review_status "unreviewed", evidence_capture_ids[], resolution_ref}`. It gives no `artifact_id`, so a user cannot build the `/v1/evidence/{artifact}/{capture}` URL from a claim. |
| `/v1/evidence/01a0a720-9c65-…/01a0d751-089b-…` | 200 (66 KB) | `{tier:"public", bytes_available:true, representation{source_uri:"sig:connector:data_driven:eff_data_driven:connector_run", retrieved_at:"2026-09-25", content_digest, media_type:"application/octet-stream", byte_size:null, claims_supported:[1,675 ids]}}` |
| `/terms` | 200 | usage tiers (anonymous / registered / partner bulk) and re-identification prohibitions |

**`/v1/evidence` is a synthetic stand-in.**
- The `sig:connector:<connector>:<source>:<type>` locator is the one `claim_sink.py:1181` builds for its one
  capture per source per run (`:1199-1236`).
- That capture has `byte_size` 0, digest = `sha256("<connector>|<source>|<run>")` (`:1201-1203`), `storage_tier
  'public'`, and `capture_classification 'synthetic'`.
- `evidence/src/evidence/tiers.py:79` sets `bytes_available = tier is PUBLIC`.
- So the API asserts that bytes are available (spec SIG-EVID-009: "public — Public URL") for a capture that has no
  bytes and no URL, and presents a non-content digest as a `content_digest`. The API does not surface
  `capture_classification` (NEW-4).

---

## B. What exists internally

### B.1 Database (Cloud SQL `sig-pg`, PG18) — provenance, ingestion and publication tables

**Roles** (`db/deploy/access_control.sql:21-41`):
- `sig_read_public` ⊂ `sig_read_restricted` ⊂ `sig_read_sealed`, plus `sig_export` and `sig_ingest`.
- The API runs as `sig_read_public` (`ops/Dockerfile:110`, `SIG_API_ROLE=sig_read_public`).
- RLS (tier ceiling) exists **only** on `claim`, `evidence_artifact` and `evidence_capture` (plus the
  `human_eval_*` tables).

**Blanket grant.** `db/deploy/read_surface_grants.sql:28` runs `GRANT SELECT ON ALL TABLES IN SCHEMA public TO
sig_read_public, sig_export`. It is deployed after `evidence_store` and `review_queue` (`db/sqitch.plan:21,25`), so it
reaches `evidence_access_log`, `review_decision`, `ingest_run` and `extraction` (NEW-9). No DB query was run; the
production grant state is inferred from the plan.

**How to read the "Audience" column:** *grant* = which DB roles can SELECT the table. *Served* = whether any public
route or export actually emits it.

| table | where | transparency-relevant fields | audience: grant / served | what exposing it would take | governing constraint |
|---|---|---|---|---|---|
| `source_registry` | `rights_sources_lineage.sql:26` (R) | `source_id, name, homepage_url, source_kind, custody_posture, compact_status, ingestion_permitted, robots_policy, crawl_budget, last_verified_at` | grant: public (blanket). served: **none** (export reads `source_id, name` only) | add to the export shaping and a source index/page | **Placeholder rows:** sink-created rows hard-code `ingestion_permitted=true`, `robots_policy='obeyed'`, `compact_status='compact'`, `custody_posture='REFERENCE'` (`claim_sink.py:1150-1165` (R)), so values must be joined to `sources.toml` truth, never published raw. Rights and Part VIII preflight per source. |
| `rights_record` | `rights_sources_lineage.sql:12` (R) | `spdx_expression, attribution_text, redistributable, derivative_permitted, terms_url, terms_capture_id, reviewed_by/at, retrieval_date` | grant: public. served: attribution in API/export rows | fix the per-SPDX dedupe first (NEW-2/3) | `reviewed_by` may name a person, so publish the role only (Part VIII / officer-naming posture) |
| `rights_decision` | `rights_decisions.sql:22` (R), append-only | `source_id, rights_id, prior_rights_id, basis, reviewer (role), review_packet, terms_url, terms_capture_id, decided_at` | grant: all read roles + export. served: effective rights only | per-source "rights-review record" section | `review_packet` content may be operator/legal text: E1 (rights) decides |
| `ingest_run` | `rights_sources_lineage.sql:46` (R) | `run_id, connector name/version, code_commit, ruleset/vocab versions, parameters{execution_id, logical_run, run_record_uri}, environment, input_digests, started_at` | grant: public (blanket). served: via freshness only | per-run log rows | `environment` and `parameters` hold internal paths (`gs://…restricted…`), so scrub them (secrets/internal-paths) |
| `ingest_run_completion` | `ingest_run_completion.sql:31`, grant `:75-76` | `status (ok/partial/quota_reached/failed), finished_at, claims_considered, claims_inserted, claims_duplicate, run_record_uri, detail, recorded_at` | grant: **public**. served: **none** except derived freshness | ready-made public run-metrics feed (counts added/duplicate, outcome, timestamps) | `detail` is free text; `run_record_uri` points into the restricted bucket, so show it as an id, not a link |
| `ingest_run_capture` | `ingest_run_capture.sql:32`, grant `:63` | per-target `state, capture_digest, source_uri, media_type, byte_size, retrieved_at, records, ocfl_object_id/version` | grant: **restricted / sealed / export only**. served: none | per-source capture history (upstream URL + time + hash) through an export view | a new grant or export needs a per-source redistribution verdict (J4) and a query-string secrets check |
| `evidence_artifact` | `evidence.sql:12` (R), RLS | `source_id, url, stable_locator, artifact_type, rights_id, sensitivity_tier, capture_status, disappeared_observed_at` | grant: public with tier RLS. served: `stable_locator` only (`spine_export.py:161-167` (R)) | export `url` as the upstream link | tier RLS and Part VIII; `url` may be a person-level page for some genres |
| `evidence_capture` | `evidence.sql:36` + `evidence_store.sql:28-30` + `claim_assertion_bindings.sql:73` (R), RLS | `content_digest, digest_blake3, byte_size, media_type, retrieved_at, retrieved_by_run_id, http_status, ocfl_object_id/version, storage_tier, capture_method, source_uri, blob_digest, redaction_*, capture_classification` | grant: public with tier RLS. served: API `/v1/evidence` (date-only `retrieved_at`) | expose `capture_classification`, full timestamp and `http_status`; link real captures to claims | synthetic vs actual captures (NEW-4); redaction fields; withdrawal |
| `evidence_blob` | `evidence_store.sql:16` (R) | `blob_digest, source_uri, byte_size, ocfl_*, first_seen_at` | grant: public (`:69`). served: none | dedup registry for a "view original" link | bytes live in the restricted bucket |
| `evidence_access_log` | `evidence_store.sql:51-60`; grants `:70-71` | `requester, purpose, storage_tier, accessed_at, retention_expires_at` | grant: **public, via the blanket** (NEW-9). served: none | should **not** be exposed | privacy and retention (SIG-EVID-012) |
| `claim` | `claim.sql:21` (R), append-only, RLS | `ingest_run_id, rights_id, extraction_id, observed_at, sys_period, sensitivity_tier, content_digest, revises_claim/retraction_of` | grant: public with tier RLS. served: API + export | already exposed | tier RLS, publication disposition |
| `claim_evidence` | `claim_evidence.sql:12` (R), append-only, **no RLS** | `capture_id, role, locator, excerpt, extractor_version, binding_status, bound_at` | grant: public. served: `record_claims.jsonl` bindings (not in the current public release) | claim → capture → locator chain | excerpts of restricted-tier claims are readable by the public role (NEW-9) |
| `publication_disposition` | `publication_dispositions.sql:39`, column grant `:124-129` | `disposition (allow/withhold/restrict/withdraw), reason_category, authority, decided_at, policy_version` | grant: public, safe columns only. served: export gate `{PUB_GATE}` | public tombstone / withdrawal list | this is the **withdrawal barrier** itself: `rationale` and `decided_by` stay elevated |
| `assertion_quarantine` | `claim_assertion_bindings.sql:102` (R) | `run_id, reason, source_id, payload, received_at` | grant: restricted / sealed only | "rejected" counts per run | the payload may carry unvetted content, so publish counts only |
| `spine_watermark` | `shared_temporal_contract.sql:120,298` (R) | per-table row counts and latest timestamps | grant: public. served: API/export | spine-wide "last updated" | none |
| robots verdicts / probe history | not in the DB; only `source_registry.robots_policy` | see B.3 | restricted bucket | aggregate into a run log | internal hostnames, probe targets |

### B.2 OCFL capture store — `gs://zeta-medley-508121-u7-sig-restricted/evidence/captures/`

- **Format:** OCFL 1.1 (`0=ocfl_1.1`). `ocfl_layout.json` uses extension `0003-hash-and-id-n-tuple-storage-layout`.
- **Size:** **350 objects** (`0=ocfl_object_1.1` count), 5,328 files, **79,411,154 B (75.7 MiB)**.
- **Object layout:** `<aa>/<bb>/<cc>/sig%3acapture%3a<multihash>/{inventory.json(.sha512), v1/content/capture,
  v1/content/metadata.json}`.
- **Contents:** `capture` holds the original bytes (e.g. 19,543 B). `metadata.json` has the keys `byte_size, digest,
  headers, media_type, retrieved_at, source_uri`. In the sample, `source_uri` is an `https://v3.openstates.org/bills?…`
  URL, `headers` is `{}`, and the query keys contain no credential.
- **When the bytes landed:** 2026-09-24 30 · 09-25 7 · 09-26 34 · 09-27 2 · 09-28 22 · **09-29 250** · 09-30 5.
- **Audience:** restricted (public access prevention **enforced**; project roles only).
- **What exposure would take:**
  - a per-source redistribution verdict (J4: `raw-ok` / `derived-only` / `link-only`);
  - a public mirror or signed-URL path for `raw-ok` bytes;
  - linking claims to these real captures (today's public evidence points only at synthetic captures);
  - honouring withdrawal/redaction.
- **Constraints:** the upstream licence (bytes are third-party works; most sources allow facts, not bytes); Part VIII
  (captured pages can contain names); secrets in URLs (keys ride headers by policy, `live_targets.toml:434-436`,
  `accountability.py:969-981`, but there is no generic URL scrubber); egress.

### B.3 GCS operational records — `gs://…-sig-restricted/`

| prefix | layout | fields (described, not copied) | audience | constraint for exposure |
|---|---|---|---|---|
| `ops/runs/<source>/<YYYY-MM-DD>/<ISO-ts>.json` | **387 objects, 7,023,338 B**, **208 source prefixes** (camreg 166, dot 12, ccops 4, procportal 4, …), dated 2026-09-16…09-30 (09-19 alone: 225) | top level: `ingest_run_id, kind (scheduled-ingest), mode, outcome, exit_code, claims_added, duration_seconds, capture_digests[], detail, refusal_reason, source, started_at`. `fetch_record`: `connector, logical_run, fetches, claim_count, robots_decisions[{host, outcome, robots_url, status}], robots_disregarded, refusals, rate_limit_events, disappearances, document_drift, document_outcomes[{capture_digest, matched_terms, outcome, platform, tenant_id, url}], quota_reached, budget_reached, sweep_*`, plus `urls/status_codes/byte_counts` | restricted, write-once (`ops/src/ops/scheduled.py`) | The richest ingestion log, and small (≈7 MB). The 3 rows read (`camreg_austin_tx` 09-28, `ccops_somerville` 09-26, `legistar` 09-20) held no secrets. **`urls`, `status_codes` and `byte_counts` are always empty**: the live `FetchRecord` (`connectors/src/connectors/runner.py:1029-1060`) never sets them (defaults at `:628-630`) (NEW-6). Scrub `detail` and any internal paths; aggregate `document_outcomes` per J4. |
| `ops/probes/<date>/<ts>.jsonl` | 60 objects, 48,099 B, 2026-09-16…09-30, ~953 B every 6 h | egress/health probe results | restricted | probe targets and internal hostnames, so aggregate to uptime only |
| `exports/national/<as-of>/` | 3 snapshots: `2026-09-24T150000Z` (145 obj, 881.6 MiB), `2026-09-24T154017Z` (881.7 MiB), `2026-09-27T005153Z` (151 obj, 1.03 GiB) | full release trees, identical in shape to the public one | restricted | **The only copies of prior releases**, so the public release history (SIG-EXPORT-001 "versioned"; SIG-UI-035 permalinks) is recoverable from here (NEW-5). |
| `web/map.json` (59,884,891 B), `web/analytics/density_bins.json` | withheld from public: compound-licence `web` / `web_mixed` compartment (restricted `manifest.json`, 2 artifacts) | | restricted | mixed-licence surface; needs per-licence split (`publish.py` `restriction_reason` (R)) |
| `rollback/sig-web-pre-p30.3-2026-09-24/`, `rollback/sig-web-pre-republish-2026-09-27T0000Z/` | previous site builds | | restricted | shows that prior public pages existed and were replaced |
| `manifest.json` (1,328 B) | restricted-tree manifest | | restricted | — |

**Cloud Logging** (Run jobs, e.g. `sig-ingest-camreg-*`):
- 40 entries since 2026-09-28: 36 `textPayload`, 2 `jsonPayload`, 2 `protoPayload`.
- They contain `gs://…-sig-restricted/ops/runs/…` and container paths (`/usr/local/lib/.sig/ops/runs/…`).
- No DSN and no "password" appeared in the sample. Raw logs are internal and should not be published; the run rows
  above are the structured, safer source.

**GitHub** (public repo): the `observability` workflow is "success" 6/6 on `main`, but its latest run
(36713858053, 2026-09-30T12:18:36Z) logged "staging endpoints unset — probe skipped (offline posture; nothing
measured)". Its artifact is 624 B (NEW-13).

### B.4 Export pipeline — what already emits transparency data

- **Compartmenting and licences**
  - Compartments are computed from source licences (`exports/src/exports/compartments.py:123-196` (R)), and
    `assert_separated` fails a mixed compartment.
  - Formats come from `formats.py:314-333` (R).
  - `LICENCES.json` is written by `ops/src/ops/publish.py:441-491` (R). The public/restricted split is
    `publish.py` `restriction_reason / partition_export / assert_public_clean` (R). Deploy is
    `ops/src/ops/deploy.py:93-98` (operator-run; no CI deploy).
- **Manifest and checksums:** `Manifest.as_json` (`manifest.py:177-184` (R)) and `digest_manifest()` for Zenodo
  (`:190` (R)). Frictionless comes from `frictionless.py:35-47` (R) and has **no Table Schema**.
- **Freshness:** `ShapedSourceFreshness.freshness_row` (`shaping.py:457-478`) reads `ingest_run` and
  `ingest_run_completion` (`:1597-1610` (R)). The row does **not** include counts, cadence, name, URL or licence,
  although the completion counts are one join away.
- **Provenance:** `provenance.ttl` (`spine_export.py:1936-1979` (R)) builds synthetic `{release}:{source}` captures
  stamped with the build time.
- **Records:** `record_claims.jsonl` rows `{claim_id, entity_id, predicate_id, observed_at, source_id,
  evidence[{capture_id, artifact_id, role}]}` (`spine_export.py:658-727` (R)). These are emitted by the builder but
  are **not present** in the public release (0 `record_claims` paths in `manifest.json`).
- **Research dossier:** the richest citation chain (claim digest → capture digest → `source_url` → retrieved date →
  locator → extraction method, plus a search log) is in `research_dossier.py:369-405, 989-1027` (R). It is not deployed
  (404, F-14).
- **Gates already in the path, reusable by any transparency surface:**
  - `ShapingClaim.publishable` (`shaping.py:203-209` (R));
  - `export_refusal_reason` (`policy/licensing.py:121` (R)), which feeds `exclusions.json`;
  - disposition SQL `entity/claim/artifact_eligible_sql` (`db/src/db/dispositions.py:76,95,109` (R));
  - the withdrawal barrier `apply_withdrawals` / `route_access` (`exports/src/exports/release.py:1332, 1461`).

### B.5 P32.13 release/record routes and P32.14 search — what they would expose once deployed

**P32.13** (ADR-132, PR #169) builds an immutable publication tree:
- `/r/<p-sha256>/c/<comp>/entity/<type>/<id>.{json,html}`;
- per compartment: `records.index.jsonl`, browse and jurisdiction pages, and evidence anchors
  `/r/<pub>/c/<comp>/evidence/<aid>/`;
- `/r/<pub>/dossier/<slug>/`;
- `releases/<pub>/{descriptor.json, integrity_manifest.json, catalog_entry.json, index.html}`;
- a mutable layer: `catalog.json, latest.json, compat_index.json, withdrawals.json, activations/`
  (`release.py:326-1133` (R)).

nginx has `/r/`, `/releases/` and `/entity/` locations (`ops/web/nginx.conf:117,124,131`). The code ships; the tree is
**not deployed**: "nothing is deployed, pushed to a bucket, or publicly exposed" (`docs/tickets/DEFERRALS.md:583`,
D-R10-PUBLISH-1 OPEN). The same row measures full-corpus cost at **236,994 records → 475,112 files / 2.0 GB / ~98 s**.

**Provenance ceiling even after deploy:**
- Record `source_refs` hard-code `"upstream_href": None` (`exports/src/exports/published_record.py:233-240`).
- Evidence is `access="metadata_only"`.
- Evidence anchor pages state that release bytes are never served (`release_pages.py:495`).
- Deploying P32.13 as built therefore gives stable per-record URLs and integrity manifests, but **no ground-truth
  links** (NEW-10).

**P32.14** builds `r/<pub>/c/<comp>/search_index.sqlite` + `search_index.json` (`search_index.py:55-56, 199`).
- Indexed fields: `records(key, id, type, label, jurisdiction, location_kind, source_id, technology, claim_ids)`, FTS
  over label/entity_id/source_id/jurisdiction, plus an identifiers table and facets (R).
- Served at `GET /v1/releases/{pub}/compartments/{comp}/search` (≤50 rows / 100 KiB / 2 s; sha256-checked; withdrawal
  on every request).
- Not in the live OpenAPI; live probe 404.

---

## C. Constraint summary

| constraint | what it binds | notes |
|---|---|---|
| **Source licence / redistribution** | raw bytes (OCFL), per-row downloads, attribution | The public bulk files already pass the compartment gate. Raw capture bytes need a per-source `raw-ok / derived-only / link-only / restricted` verdict (J4). **Attribution must be fixed before any source page repeats it** (NEW-2/3). |
| **Part VIII** (no person/plate data, officer naming) | capture bytes, `evidence_artifact.url`, `rights_record.reviewed_by`, document excerpts, run-row `document_outcomes` | publish metadata and aggregates, not bytes, until each source's preflight is green |
| **Restricted compartment** | `web/map.json`, `density_bins.json` (mixed licence) | needs a per-licence split, not a relabel |
| **Withdrawal barrier** | anything served per record or per capture | reuse `publication_disposition` + `apply_withdrawals` / `route_access`; static bucket files cannot 410 by themselves, so the prefix scheme must carry tombstones |
| **Egress cost** (SIG-EXPORT-008) | bulk downloads, bytes | The public bucket is served straight from `storage.googleapis.com`. There are no backend buckets, and the only LB backend (`sig-web-backend`) has **CDN disabled**. The release is ≈1.05 GB, and `web/research_queue.json` alone is 144 MB. The S3/R2 path (`exports/.../push.py:46-58` (R)) is unused (NEW-12). Making downloads discoverable raises egress; standard internet-egress pricing is an **inference**, not measured. |
| **Secrets and internal paths** | run rows, Cloud Logging, `ingest_run.parameters/environment`, `run_record_uri` | No secrets were seen in the samples. Paths into `gs://…-sig-restricted` and container paths appear, so serve structured, scrubbed run rows, never raw logs. |
| **Over-broad DB grant** | any new API route over the spine | The public role can already read internal tables (NEW-9). New transparency routes must use explicit column lists and views, not the blanket grant. |
| **Release / publication gate** | P32.13 tree, P32.14 search, any new public surface | HG-11 plus D-R10-PUBLISH-1 (operator; see E/G) |

---

## D. Gaps against the operator's four goals

| goal | today | gap |
|---|---|---|
| **1. Explore each third-party source** | `/data-freshness/` lists 178 bare ids with 3 dates and a status; the API has no source route | no source index; no per-source page (name, publisher, homepage, licence, redistribution status, rights-review record, cadence, coverage by geography/technology, sample records, known issues); 342 registry rows, 236 marked `ingestion_permitted = true`, 208 with run rows, but only 178 in freshness and 218 "independent sources" on `/evidence/`, with no reconciliation of these counts on any page |
| **2. Link to ground truth** | per-row `rights_terms_url` (often empty); API `terms_url`; evidence locators are `sig:` URNs | 0 of 255 public evidence artifacts carry an upstream http URL; the API evidence route shows a synthetic capture; `claim_views` is empty; P32.13 hard-codes `upstream_href=None`; the 350 real captures that do carry upstream URLs are restricted-only; claim → artifact navigation is impossible from `/v1/claim` |
| **3. Download raw data** | 132 checksummed derived artifacts in a public bucket, 7 formats, licence-separated | no site link, downloads page, sitemap or API pointer (`/v1/export` → 404); no data dictionary / Table Schema; no RO-Crate (SIG-EXPORT-002; 0 `ro-crate` objects in either bucket); no release history (paths overwritten; prior releases restricted-only); no raw capture bytes; `record_claims.jsonl` (the claim → evidence table) is not in the public release |
| **4. Ingestion logs, metrics, timestamps** | 3 timestamps/status per source, frozen at the release | `ingest_run_completion` counts (considered / inserted / duplicate, outcome, `finished_at`) are grantable today but unpublished; run rows (robots decisions, refusals, disappearances, document outcomes, durations) are restricted; run rows never record URLs, status codes or bytes; `/v1/changes` is always empty; the observability job measures nothing; no public status or run-log page |

---

## E. New findings (see `findings/incoming/J1.csv`)

These relate to existing findings F-08 (freshness frozen / all unknown), F-09 (`/v1/export` 404, no sitemap), F-11 (no
release id in HTML) and F-14 (Round-10 surfaces undeployed); J1 does not re-raise them.

| id | title | sev |
|---|---|---|
| NEW-1 | Full licence-separated bulk release (132 artifacts, 1.05 GB, checksummed) is public but unreachable from the site | S1 |
| NEW-2 | Public downloads and the live API misattribute third-party data to "DeFlock community map" (3,272 of 4,834 `sig_graph` rows; EFF Atlas) because rights records are deduplicated by SPDX only | S1 |
| NEW-3 | 61,603 public rows (100% of `public_record` and `operator_accepted`) have attribution required but empty attribution and terms URL | S2 |
| NEW-4 | Public evidence provenance is synthetic: `/evidence/` shows no claim views; `/v1/evidence` asserts `bytes_available: true` and a "content digest" for 0-byte synthetic captures; the 350 real captures are restricted-only | S1 |
| NEW-5 | "Belief-pinned permalink (reproducible after SIG corrects itself)" ignores its as-of parameters; prior releases exist only in the restricted bucket | S1 |
| NEW-6 | Run rows never record per-fetch URLs, status codes or byte counts; the run metrics that exist are not published | S2 |
| NEW-7 | The 342-row source registry (with homepage URLs) is never exported; no public source index | S2 |
| NEW-8 | `provenance.ttl` stamps every capture with the export time and uses an unresolvable `sig-project.org` namespace | S2 |
| NEW-9 | The API role (`sig_read_public`) holds a blanket SELECT that reaches `evidence_access_log`, `review_decision`, `ingest_run.environment` and un-RLS'd `claim_evidence` excerpts | S2 |
| NEW-10 | P32.13 released records hard-code `upstream_href=None` and metadata-only evidence, so deploying them adds no ground-truth links | S2 |
| NEW-11 | Data package has no Table Schema / data dictionary, omits 28 manifest artifacts, and no RO-Crate is published | S2 |
| NEW-12 | Public data is served straight from a standard GCS bucket with no CDN; the S3/R2 low-egress path is unused (egress risk once downloads are linked) | S2 |
| NEW-13 | The scheduled observability workflow reports success while measuring nothing (staging endpoints unset) | S2 |

---

## F. Reproduction (read-only)

- **Public bucket:** `curl https://storage.googleapis.com/zeta-medley-508121-u7-sig-public/{manifest.json,
  datapackage.json, exclusions.json, provenance.ttl, web/freshness.json, web/evidence.json}`;
  `curl -r 0-3000 …/{public_record,sig_graph}/sites.csv`; `curl …/{sig_graph,public_record,portal,operator_accepted}/sites.sqlite`
  then `sqlite3 <f> "select rights_attribution, count(*) … group by 1"`; `curl '…-sig-public?max-keys=5'`.
- **Site:** `curl https://surveillancegraph.org{/, /data-freshness/, /evidence/, /methodology/, /coverage-metrics/,
  /dossier/al/, /watch/, /corrections/}`; the 404 probes; `/evidence/?as_of_world=2020-01-01&as_of_belief=2020-01-01`.
- **API:** `/openapi.json`, `/v1/export`, `/v1/changes?since=2026-09-01`, `/terms`, `/`, `/v1/search?q=austin&limit=2`,
  `/v1/entity/deployment/01a0a720-af12-7946-bfe3-1accab0e34ae`, `/v1/claim/01a0d751-0961-76a4-949f-e27e7fbb08e8`,
  `/v1/evidence/01a0a720-9c65-7732-9e12-dcefe33aab15/01a0d751-089b-7153-9889-2dff4a1dc4af`,
  `/v1/releases/x/compartments/y/search?q=a`, `/exports/entities.parquet`.
- **gcloud:** `storage ls [-l]` on the three buckets; `storage buckets get-iam-policy|describe`; `storage cat` on 3 run
  rows, `ocfl_layout.json`, one OCFL `metadata.json`, the restricted `manifest.json`, `LICENCES.json`; `logging read`
  (40 entries, field shapes only); `compute backend-buckets|backend-services|url-maps list`.
- **GitHub:** `gh run list --workflow observability`; `gh api …/actions/runs/36713858053/artifacts`;
  `gh run view 36713858053 --log`.
