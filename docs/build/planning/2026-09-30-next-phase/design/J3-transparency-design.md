# J3 — Transparency and export design

Row **J3** of `META_PLAN.md` §6 Stream J (owner D, depends J1, J2, J4, C2). Written 2026-09-30 by Claude Code (Opus 5.5)
in the planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD
`07ef0142`). Work window (`date -u`): **2026-09-30T18:15:23Z → see footer**. `PD` = `docs/build/planning/2026-09-30-next-phase`.

> **Design only (P3/P10).** Nothing here was executed against production. No live GET, gcloud or DB read was made by
> this row; every production fact is cited from J1/J4/C2/C3/G1/G2/F5, which read it. Every code path cited below is
> byte-identical to chain tip `b051732c` (`git diff --stat b051732c HEAD -- exports/ web/src db/ api/ evidence/` is
> empty). Nothing here is `engineered`, `staging-verified` or `live-executed` (P5). Every public sentence quoted in
> this note is **agent-drafted** and must be confirmed verbatim by the operator before it ships (META_PLAN §2). The
> operator's contact address is referred to as **‹operator address›** (value in META_PLAN §7.1).

**Inputs read.** META_PLAN §3, the Stream J block, §7 (Q-22, Q-29), §7.1, §8.2, §11; `research/J1-exposure-inventory.md`
(whole); `research/J2-prior-art.md` §0–§7; `research/J4-redistribution-matrix.md` (whole) + `data/redistribution.csv`
(345 rows, columns only + lane counts); `review/JOURNEYS.md` §2–§4, §7–§11; `review/DATA_TRUTH.md` §3–§6;
`design/G2-activation.md` §0, §1, §4 steps 3–7, §5, §6; `research/F5-eng-debt.md` §4; `feedback/OPERATOR_FEEDBACK.md`
U-001/U-002; the titles of every `findings/incoming/*.csv` row (to avoid re-raising). Code: `exports/src/exports/`
(`release.py`, `spine_export.py`, `shaping.py`, `frictionless.py`, `distribution.py`, `push.py`, `torrent.py`,
`published_record.py`), `api/src/api/{routes.py,app.py,store_pg.py}`, `evidence/src/evidence/tiers.py`,
`db/src/db/claim_sink.py`, `db/deploy/{ingest_run_completion,ingest_run_capture,rights_sources_lineage,evidence,claim_assertion_bindings}.sql`,
`web/src/{components/Citation.astro,layouts/BaseLayout.astro,lib/data.ts,pages/**}`, `web/lighthouserc.json`,
`ops/web/nginx.conf`, `ops/src/ops/publish.py`, `ops/cadence.toml`, `connectors/src/connectors/data/sources.toml`
(`tomllib` counts only), ADR-132, spec §32.3–32.4, §38, §39.6/39.9, §40 (SIG-UI-036/037/050), §42.4–42.5, §43.7–43.8,
§45.3–45.6, §49 (SIG-ENG-020), SIG-EVID-009/010, SIG-FIND-001…006.

**Evidence classes (P1).** `code` (file:line at HEAD), `recorded-execution`/`live-read` (only as cited from other rows,
with the row named), `inference` (labelled). Sizes and costs are **inference** unless a row measured them.

**Outputs.** This file and `findings/incoming/J3.csv` (NEW-1…NEW-4).

---

## 0. Summary

**What the operator asked for** (§7.1): explore each third-party source, link to the ground truth, download the raw
data, and see ingestion logs, metrics and timestamps. **What exists** (J1): a checksummed 1.05 GB licence-separated
release that nothing links to; a freshness table of 178 bare ids; an evidence page with no evidence; a 342-row registry,
350 real captures and 387 run rows that are all internal. **What blocks a naive "just publish it"** (J4, C2, C3): the
attribution and terms defects (5,110 rows whose own terms forbid redistribution; 171 of 218 live sources fail
attribution), Part VIII hazards in raw bytes and logs, uncapped GCS egress, and permalinks that do not pin.

**Design in one paragraph.** Every transparency surface is a **static artifact produced at export time** from one
read-only spine snapshot plus scrubbed run records, **bound into the immutable release** (ADR-132) and rendered
zero-JS by the existing Astro site; the only new moving parts are (a) an append-only `ingest_run_report` table that
brings the WORM run-row metrics into the spine, (b) a 6-hourly **status lane** job (a batch job, not a service) that
republishes only scrubbed operational metadata between releases, and (c) a **zero-egress distribution host** (R2
mirror, already coded in `exports/push.py`) in front of downloads. Rights are keyed on the **source** (J4 lanes), never
on the compartment; attribution is rendered from the **registry**, never the rights join; every log field passes a
fail-closed scrub (J4 S-1…S-14); every withdrawal reuses the one ADR-132/ADR-124 barrier.

**Components.**

| # | component | route(s) | ships when |
|---|---|---|---|
| C1 | Source explorer | `/sources/` (+ facet routes), `/sources/<id>/`, `…/runs/`, `…/captures/`, JSON twins | after attribution fix (ACT-07) + NEW-1 withdrawal decision; no dependency on release exposure |
| C2 | Record provenance panel + figure→evidence | panel on `/r/<pub>/…/entity/…`, evidence anchors, `data-figure` pointers on every page | honest "run-level only" state first; real captures after G2 step 1–2 (L44–52 + actual bindings) |
| C3 | Downloads center | `/data/`, `/releases/<pub>/data/`, `/data/dictionary/`, `/data/api/` | after the distribution host + egress guard (ACT-03) |
| C4 | Ingestion status + issues log | `/status/`, `/status/issues/`, `/status/state.json` | status lane after the single publish path (ACT-05) |
| C5 | Releases & citations | `/releases/<pub>/` changelog + id diffs, `/s/<pub>/…` site snapshots, edge selector map | with G2 step 7 (HG-11) |
| C6 | Generation architecture | exporter queries/views, `ingest_run_report`, scrub module, descriptor v2 | first (code-only) |

**Round-11 ticket outline (§12):** 16 tickets, TX-01…TX-16 — 3 S, 9 M, 4 L (TX-05, TX-08, TX-10, TX-13; each split a/b at T3).
A **transparency MVP** (TX-01/02/03/04/05/07/10b-lite/11) can go public in the first product wave without waiting for
G2 step 7; provenance with real captures, the raw archive, site snapshots and release diffs follow G2 steps 1–7.

**Operator decisions (§13):** D-J3-1 raw bytes (Q-22a) · D-J3-2 scrubbed run logs incl. robots-disregard disclosure
(Q-22b) · D-J3-3 commit hashes while the repo is private · D-J3-4 distribution host + egress ceiling (Q-10) · D-J3-5 NEW-1
sources withdrawn before launch · D-J3-6 per-release site snapshots (new ADR) · D-J3-7 JSON-LD as linked files (no
zero-JS exemption) · D-J3-8 signing key custody · D-J3-9 Zenodo scope · D-J3-10 prior releases as history · D-J3-11
status-lane cadence and gated-source visibility · D-J3-12 known-issue text approval.

**Top risks (§14):** transparency amplifies existing defects (sequence fixes first); raw bytes/logs leak Part VIII
material (fail-closed scrub, phased raw rollout); egress blow-up once links exist (mirror + kill switch before links);
downloaded/deposited bytes cannot be recalled (gate before release, per-source slices); two clocks confuse readers
(release as-of vs status time, both labelled).

**New findings (§16):** NEW-1 (S1) chain-tip citations stay unpinned even after P32.13 deploys; NEW-2 (S1, latent) the
actual-capture writer marks every capture `public`, so `/v1/evidence` will advertise public bytes and raw URLs for
derived-only/restricted sources once L44–52 go live; NEW-3 (S3) "last content change" means "last run that added a
claim"; NEW-4 (S3) date-granular selectors make same-day releases ambiguous.

---

## 1. Ground truth that constrains the design

| # | fact | evidence | design consequence |
|---|---|---|---|
| G-1 | The export runs every read inside one `REPEATABLE READ READ ONLY` snapshot; supplementary reads are a keyed dict of `to_regclass`-guarded SELECTs with shared eligibility gates (`{PUB_CLAIM_GATE}`, `{PUB_ARTIFACT_GATE}`…) | `exports/src/exports/spine_export.py:130-233, 235-291, 2043-2128` (code) | transparency reads are **new keys in `EXPORT_QUERIES`**, inheriting snapshot consistency, belief pinning and the ADR-124 gates — no second read path |
| G-2 | The only source query in the export is `SELECT source_id, name FROM source_registry` | `spine_export.py:130-135` (code); J1 NEW-7 | source metadata must be joined to `sources.toml` truth (sink-created registry rows carry placeholder values, J1 §B.1) |
| G-3 | Freshness comes from `ingest_run_completion`: `last_successful_run` = latest ok/partial/quota completion; `last_content_change` = latest completion with `claims_inserted > 0` | `exports/src/exports/shaping.py:1597-1602` (code) | "last content change" is mislabelled (NEW-3); capture digests must drive it |
| G-4 | Volatility is `unknown` when a source has no **dated** observation on a registry-known predicate | `shaping.py:1283-1345` (code) | fixing "volatility unknown" is a data-model question (what dates a presence observation), owned by PKG-10; J3 shows cadence and volatility as **different** things |
| G-5 | Run metrics live in 387 WORM GCS rows (7.0 MB, 208 sources) and in `ingest_run_completion` (counts, status, `finished_at`; already granted to `sig_read_public`); `ingest_run_capture` holds per-target digests, URIs, sizes, `retrieved_at` (export/restricted roles only) | J1 §B.1, §B.3 (live-read); `db/deploy/ingest_run_completion.sql:31-82`, `ingest_run_capture.sql:32-63` (code) | the run log needs the WORM fields inside the spine (§3.3); `fetched`/per-fetch bytes are empty today (J1 NEW-6 → PKG-12) |
| G-6 | Every claim written by the live sink binds to a **synthetic** per-source-per-run capture (0 bytes, digest = `sha256(connector|source|run)`, tier `public`); real per-capture bindings (`binding_status = actual_capture`) arrive only with P32.2 / sqitch L44 | `db/src/db/claim_sink.py:1170-1236` (code); `db/deploy/claim_assertion_bindings.sql:1-30` (code); G2 step 1 (L44–52 undeployed) | the claim-level provenance panel shows **run-level provenance only** for all existing claims until G2 steps 1–2; the panel must say so, never imply a document |
| G-7 | The P32.2 actual-capture writer inserts every capture with `storage_tier 'public'`; artifacts default to `sensitivity_tier 0`; the API returns `source_uri` for every tier and `bytes_available = tier is PUBLIC` | `claim_sink.py:573-580, 1478-1498`; `db/deploy/evidence.sql:28`; `evidence/src/evidence/tiers.py:32-33, 62-83, 93-105`; `api/src/api/store_pg.py:777-795` (code) | **NEW-2**: the tier must be derived from the source lane + Part VIII class at write or at read, before L44–52 go live |
| G-8 | ADR-132 releases: `publication_id` hashes an ID-free descriptor; `r/<pub>/…` immutable; mutable `catalog/latest/compat_index/withdrawals`; access-time withdrawal via a generated nginx exact-match deny include | `exports/src/exports/release.py:1-35, 166-206, 326-745, 1025-1050`; `ops/web/nginx.conf:117-145` (code); ADR-132 | transparency artifacts that belong to a release must enter the **descriptor** (a v2 bump — an ADR-132 revisit trigger) |
| G-9 | Every Astro page renders `Citation` from `BaseLayout` **without** a `release` prop, so it always shows the legacy "Belief-pinned permalink (reproducible after SIG corrects itself)"; the selector resolver exists only as `sig-exports release resolve` | `web/src/layouts/BaseLayout.astro:129`; `web/src/components/Citation.astro:39-76`; `exports/src/exports/cli.py:1265-1272`; `ops/web/nginx.conf` has no selector handling (code) | **NEW-1**: deploying P32.13 does not pin site pages; J3 adds release-pinned citation for every page (§8) |
| G-10 | P32.13 at national scale: 236,994 records → 475,112 files / 2.0 GB / ~98 s; ≈$2.4 in object writes per full upload | ADR-132; G2 step 3/7 (inference on price) | transparency must not multiply per-claim pages; provenance hangs off record and evidence-anchor pages |
| G-11 | Public content pages: 0 script bytes and ≤150 KiB (153,600 B) total transfer; islands only `/map/`, `/network/`, `/search/` with per-island ceilings; tables sort via pre-rendered GET routes and cap at 500 rows | `web/lighthouserc.json` (code); `web/src/pages/data-freshness/[...sort].astro:1-50`; `web/src/lib/data.ts:635-653` | every J3 page is zero-JS, paginated, with facet routes pre-rendered one dimension at a time; multi-facet filtering reuses the **existing** `/search/` island (no fourth island, no ADR) |
| G-12 | Egress: public bucket served straight from GCS, no CDN, anonymously listable; ≈$0.13 per full-release download; abuse scenario ≈$2.8k/month; R2 $0 egress; `push.py` writes content-hash keys with immutable cache headers; `distribution.assert_low_egress` rejects `gcs` | J4 §6–§7 (live-read + inference); `exports/src/exports/distribution.py:30-36`, `push.py:1-60` (code) | the download center goes live only behind the zero-egress host (§6.8) |
| G-13 | Registry: 342 sources, 236 `ingestion_permitted`; `cadence` present on 191 rows; `ops/cadence.toml` schedules 70 sources + 8 batches (151 members) = 221 of 236 permitted; 15 permitted sources have no schedule (OSM policy corpus, code repos, `gleif`, `wikidata_sparql`, `okc_council`, …) | `tomllib` counts over `sources.toml` and `ops/cadence.toml` at HEAD (code) | declared cadence = `cadence.toml` (ops truth) with registry fallback; "not scheduled" is an explicit state |
| G-14 | Source counts on public pages disagree: 178 (home, freshness), 218 (provenance "independent sources"), 219 (distinct sources in `evidence.json`), 208 (run-row sources), 218 (I1 ingested-live), 236 permitted, 342 registered | C2 §7 NEW-14; C3 §3, NEW-13, NEW-21; J1 §D; I1 (cited) | §4.1 defines one counting funnel and requires every displayed count to name its definition |

---

## 2. Design principles (binding on every J3 ticket)

- **T-1 Static, export-time, release-bound.** Every transparency artifact is emitted by the exporter (or the status
  job) as files; nothing is computed per request from the live spine. The API serves the same files (§6.10). This keeps
  site and API from disagreeing (C3 systemic cause 6) and keeps ADR-132's "static records + edge deny map" posture.
- **T-2 One snapshot, explicit columns.** New reads are `EXPORT_QUERIES` entries over **explicit-column views** granted
  to `sig_export` only; nothing new reads through the blanket `sig_read_public` grant (J1 NEW-9, J4 S-12).
- **T-3 Rights are per source, not per compartment.** The raw-bytes lane (`raw-ok · derived-only · link-only ·
  restricted · unknown`, J4 §2) is a reviewed registry field, keyed on `source_id`; the compartment licence never
  decides a byte download (J4 §4.2).
- **T-4 Attribution from the registry.** Every attribution string on every page, file and tile comes from the
  per-source registry text, never from the `rights_record` join (J4 §5). A publish gate fails on any required-but-empty
  attribution (PKG-08 owns the gate; J3 consumes it).
- **T-5 Honest absence.** Every field is a value or a named absence kind (`not_recorded`, `not_evaluable`,
  `not_scheduled`, `not_redistributable`, `withdrawn`, `rights_not_reviewed`, `run_level_only`); never an empty cell,
  never `0` for "not measured", never "unknown" without a reason (C3 systemic cause 5).
- **T-6 Scrub fails closed.** Every log, URL and header passes J4's S-1…S-14 in one policy module; a secret-shaped
  value anywhere in the publish set **blocks the publish** (J4 S-1).
- **T-7 Two clocks, both labelled.** Release pages say "as of release `<pub>` (data as of `<as_of_world>`)"; status pages
  say "status as of `<status_time>` — newer than the release; not a citation". No page mixes them silently.
- **T-8 Withdrawal first.** Every per-record, per-capture and per-source artifact is reachable only through the one
  ADR-124 `access_decision` rule (release tree + nginx deny include + the SQL twins).
- **T-9 Zero-JS.** No new island. Machine-readable metadata is linked (`<link rel="alternate"|"describedby">`), not
  inlined as `<script type="application/ld+json">` (J2 §7 Q1; decision D-J3-7).
- **T-10 No new runtime service unless justified.** Justified exceptions: the status lane (freshness is its purpose;
  daily full releases would cost ≈$2.4 each in object writes, G-10) and the distribution host (SIG-EXPORT-008). Both are
  a batch job and object storage, not servers.
- **T-11 Nothing names a person.** Reviewers appear by role; officer and private-person names never appear in logs,
  URLs, filenames or samples (Part VIII §43.2/§43.4; J4 S-7, P8-2/P8-3).

---

## 3. Generation architecture

### 3.1 Data flow

```
 sources.toml ─┐   ops/cadence.toml ─┐   PD-reviewed lane table ─┐   known_issues.toml ─┐
               │                     │   (registry [redistribution])                   │
               ▼                     ▼                          ▼                      ▼
   ┌──────────────────────────── sig-exports build --from-spine (one RR READ ONLY snapshot) ─────────────────────┐
   │ EXPORT_QUERIES + new explicit-column views:                                                                   │
   │   v_transparency_source      (source_registry ⋈ latest rights_decision, role-only reviewer)                   │
   │   v_transparency_run         (ingest_run ⋈ ingest_run_completion ⋈ ingest_run_report — scrubbed fields)       │
   │   v_transparency_capture     (ingest_run_capture ⋈ evidence_capture actual/synthetic, classification, tier)  │
   │   v_transparency_binding     (claim_evidence binding_status per claim, gated)                                 │
   │   v_transparency_quarantine  (assertion_quarantine counts by reason class — never payload)                   │
   │ → policy.transparency.scrub (S-1…S-14, fail closed) → transparency/*.json[l] + per-source slices + statements │
   └──────────────┬──────────────────────────────────────────────────────────────────────────────────────────────┘
                  ▼
   sig-exports release build  → r/<pub>/… (records + provenance panel + evidence anchors)
                              → r/<pub>/transparency/… (sources, runs, captures, issues, changes)   [descriptor v2]
                              → releases/<pub>/{descriptor,integrity_manifest,catalog_entry,data/…}
                  ▼
   Astro (SIG_DATA_SOURCE=export) → latest view  /sources/ /data/ /status/(release copy) …
                                  → snapshot     /s/<pub>/…  (same build, base=/s/<pub>/; D-J3-6)
                  ▼
   sig-ops publish (the ONE allow-listed path, ACT-05/PKG-04) → sig-web + sig-public (origin of record)
                                                             → R2 mirror (content-hash keys; downloads)

   Status lane (Cloud Run job, every 6 h): read-only v_transparency_run/capture since the release
     → scrub → status/state.json, status/sources/<id>.json, status/index.html, status/issues/index.html,
       status/archive/<date>.json → same publish path with a status/** allow-list
```

### 3.2 Artifacts

Licence of SIG-authored metadata files: CC-BY-4.0 (SIG's own metadata, spec §42.2). They quote **short** terms
excerpts and link the full terms; they never reproduce third-party bytes. Sizes are **inference** from J4 §6 unit sizes.

| artifact (release path under `r/<pub>/transparency/` unless noted) | schema id (draft) | content | size today (inference) |
|---|---|---|---|
| `sources.json` | `sig.transparency-sources/1` | one object per registry source (342): §4.3 fields | 1–3 MB |
| `sources/<id>.json` | `sig.source-page/1` | the page twin: registry + lane + rights record + cadence + counts + coverage + samples + issues + dossier contributions | 342 × 5–60 KB ≈ 7–20 MB |
| `runs.jsonl` | `sig.run-record/1` | one scrubbed row per execution (§4.5) | ≈3–5 MB (387 rows today + ~470/month) |
| `captures.jsonl` | `sig.capture-record/1` | one row per capture occurrence: digest, bytes, media type, `retrieved_at` (full ISO), classification, lane, bytes-available, changed-vs-prior | ≈1–2 MB (6,144 digests today) |
| `issues.jsonl` | `sig.source-issue/1` | auto-detected + curated issues with open/close dates | <1 MB |
| `counts.json` | `sig.source-counts/1` | the §4.1 funnel with definitions and id lists per difference | <100 KB |
| `changes/` | `sig.release-changes/1` | id-level diff vs the previous activated release (§8.4) | 1–20 MB |
| `<comp>/statements.parquet`, `<comp>/statements.csv.gz` (per compartment) | `sig.statement/1` | one row per published claim: claim, entity, predicate, value, source, binding status, capture digest, `retrieved_at`, upstream host (URL if S-6 allows), extractor version | ≈80–200 MB total for 2.42 M claims (inference) |
| `<comp>/by-source/<id>.{parquet,csv.gz}` | same as sites | per-source derived slices (compact formats only) | ≈60–80 MB total (J4: parquet 36 MB for all sites; csv.gz similar) |
| `data/dictionary.json`, `data/<bundle>/datapackage.json`, `data/catalog.jsonld`, `data/provenance.jsonld`, `SHA256SUMS`, `SHA256SUMS.minisig`, `ATTRIBUTION.txt`, `LICENCE.txt`, `README.md`, `CHANGELOG.md` | Frictionless v2, DCAT 3, PROV-O | §6 | <5 MB |
| `raw/<multihash>` (distribution host only; D-J3-1) | — | raw-ok capture bytes after the P8 screen, or redacted re-serialisations recorded as new captures | ≈35 MB today; +0.1–0.7 GB/month (J4 §6, raw-ok share) |

### 3.3 Database changes (additive; new sqitch changes, never edits)

1. **`ingest_run_report`** (append-only, trigger-enforced like `ingest_run_completion`): one row per execution with the
   **scrubbed, closed-vocabulary** fields of the WORM run row — `fetches`, `records_emitted`, `duration_seconds`,
   `robots_outcomes jsonb {host: {obeyed|disallowed|unavailable|disregarded: n}}`, `refusal_classes jsonb`,
   `rate_limit_events int`, `disappearances int`, `document_outcomes jsonb {outcome: n}`, `quota_reached`,
   `budget_reached`, `error_class` (S-4 vocabulary), `per_fetch jsonb` (PKG-12 telemetry, host + status + bytes,
   URLs only where S-6 allows), `recorded_at`. Writers: `sig-ops scheduled-ingest` (alongside the WORM row) and a
   one-shot `sig-ops backfill-run-reports` over the 387 WORM rows (`backfilled_from` unique → +0 re-run), the P31.2
   pattern. **Why not read GCS at export time:** the export stays one snapshot and belief-pinnable (`recorded_at`), the
   export job needs no restricted-bucket read, and append-only is enforced by a trigger — the buckets are unversioned
   (G1-05), so "WORM" is not enforced there. Alternative kept open for T1: export reads the WORM rows with the listed
   object names + digests recorded in `manifest.reproducibility_inputs`.
2. **Explicit-column views** `v_transparency_*` (§3.1) with `GRANT SELECT … TO sig_export` only. Pairs with PKG-09a's
   cut of the blanket `sig_read_public` grant.
3. **Registry lane field** — not a DB change: `sources.toml [sources.<id>.redistribution] lane = "…", basis = "…",
   reviewed = <date>, decision_ref = "…"` seeded from `PD/data/redistribution.csv` after the operator accepts the lane
   table (D-J3-1). `source_registry` rows are refreshed from it by the existing registry sync.
4. **Capture tier derivation (NEW-2 fix):** the actual-capture writer sets `storage_tier` from the lane + Part VIII
   class (`raw-ok` and P8-clear → `public`; `derived-only`/`link-only` → `restricted`; `restricted`/P8-1/P8-2/P8-4 →
   `sealed`), and the API/exports read the tier, never assume it. Must land **before** the hosted L44–52 deploy (G2
   step 1).

### 3.4 Release descriptor v2 (ADR-132 revisit trigger fires)

Anything the release tree renders must be an intentional input to `publication_id`. J3 adds
`transparency_root` (sha256 over the canonical `sources.json`, `runs.jsonl`, `captures.jsonl`, `issues.jsonl`,
`counts.json`) and `snapshot_renderer` (Astro build identity for `/s/<pub>/`) to the descriptor →
`sig.publication-descriptor/2`. ADR-132's revisit trigger ("`sig.publication-descriptor/1` needs new intentional
inputs") fires; the change needs a **new ADR** (never an edit of ADR-132) and namespaces change globally, which is
correct but must be announced on `/releases/`.

### 3.5 What stays out of the public tree (never exported)

`ingest_run.environment`, `ingest_run.parameters.run_record_uri` (opaque id instead), `evidence_access_log`,
`assertion_quarantine.payload`, `rights_record.reviewed_by` (role only), raw capture headers beyond the S-14 allowlist,
Cloud Logging, probe targets, Eyes on Flock / audit-class bytes (P8-1), private-registrant material (P8-4), and every
field J4 §8 marks **N**.

---

## 4. Source explorer

### 4.1 The counting funnel (reconciles 178 vs 218 before launch)

One exporter function emits `counts.json`; every page that shows a source count renders one of these named quantities,
with its definition in a tooltip-free footnote (zero-JS), and a CI check recomputes them from the release files.

| name | definition | value known today (source) |
|---|---|---|
| `registered` | rows in `sources.toml` | 342 (code) |
| `rights_reviewed_permitted` | `ingestion_permitted = true` | 236 (code) |
| `scheduled` | in `ops/cadence.toml` (per-source or batch member) and permitted | 221 (code) |
| `ingested` | ≥1 completed execution **or** ≥1 claim on the spine | 218 (I1 "ingested-live") — to recompute |
| `published_claims` | ≥1 claim passing the publication gate in this release | 219 distinct in `evidence.json` / 218 in provenance (C3) — the off-by-one must be named by id |
| `published_sites` | ≥1 row in a compartment `sites` file (today's freshness universe) | 178 (C3, J1) |
| `independent_lineages` | `published_claims` collapsed by `derived_from` lineage (mirrors are not independent, P15) | not computable until PKG-12 sets `derived_from` → shown as `not_evaluable` |

Rules: "178 sources tracked" becomes "178 sources with published sites (of 219 with published claims; 342
registered)"; "Independent sources 218" becomes "Sources with published claims: 218" until lineage is computable
(C3 NEW-13). The `/sources/` header shows the funnel with the id list of each step's difference (e.g. the 41
claims-without-sites sources, C3 NEW-21). **Acceptance:** no public page shows a source count without one of these
names; the recompute check passes on the candidate.

### 4.2 `/sources/` index

- One row per **registered** source (342), grouped by lifecycle: *published* · *ingested, nothing published* ·
  *permitted, not yet run* · *gated (rights not reviewed)* · *refused* · *withdrawn from publication*.
- Columns: name (linked), publisher, publisher type (J4/§8.6 vocabulary: `government_portal`, `statutory_report`, …
  mapped from `source_kind`), technology classes (PKG-07; `not_typed` until then), geography (PKG-06a keys; country /
  subdivision), status, upstream licence (SPDX) **and** SIG publication basis where different (e.g.
  `LicenseRef-PublicRecord-FactualCompilation` labelled "SIG basis — facts only, not a licence from the publisher"),
  raw lane, last run, freshness state (§4.6), open issues, published subjects.
- **Filters without JS:** pre-rendered single-dimension facet routes `/sources/by/<dim>/<value>/` for `class`,
  `geography` (country, then US state / subdivision), `publisher-type`, `status`, `licence`, `lane`; sort routes as
  plain GET links (the `/data-freshness/` pattern). Multi-dimension filtering is added to the **existing** `/search/`
  island (P32.14 facets gain `kind=source` rows), so no fourth island and no ADR.
- Paging: ≤200 rows per page; each page ≤150 KiB transferred, 0 scripts.
- `/data-freshness/` keeps its URL and becomes a sorted view of the same rows (redirect not needed); bare ids
  everywhere on the site (dossier "Sources" rows, freshness, search hits, map popups) become linked names (C2 NEW-15).

### 4.3 `/sources/<id>/` page fields

| section | field | source of truth | rule / absence token |
|---|---|---|---|
| Identity | name, publisher, publisher type, description | `sources.toml` `name`, `notes` (first paragraph, operator-reviewed), `source_kind` | description text is agent-drafted per source and operator-confirmed in batches (D-J3-12); until then `description_pending_review` |
| | source id | registry | ids that embed personal handles are replaced by neutral ids first (C2/C3 S0, DR-C3-13); old ids 301 to new |
| Ground truth | homepage, dataset/endpoint URLs, terms URL | `homepage_url` (341/342); `live_targets.toml` / `camera_registry_targets.toml` endpoints; rights `terms_url` | every URL through S-1 (credentials) and S-6 (host always; full URL only if lane ∈ {raw-ok, derived-only} **and** gate-passed); `no_upstream_url_recorded` |
| | terms capture | rights `terms_capture_id` → capture digest + retrieved_at | shows "terms as captured on <date>, sha256 <…>"; the terms bytes themselves are link-out only |
| Licence & redistribution | upstream licence (verbatim SPDX + short excerpt), SIG basis, share-alike, attribution text required, raw lane with reason | registry `[rights]` + `[redistribution]`; J4 lane | attribution rendered from registry text (T-4); `restricted` shows reason class (`terms` · `part_viii` · `not_reviewed`) |
| Rights-review record | basis, gate reference (e.g. GL-GATE-07), reviewer **role**, decided_at, terms reviewed, counsel status | `rights_decision` rows (append-only) + registry `rights_reviewed_on` | dates from `rights_decision.decided_at`; B1 NEW-5 past-dated registry dates show the B1 correction note; "No counsel opinion recorded" where none (E1-05); review packet text only per D-J3-13 |
| Collection conduct | robots outcome per host (obeyed / disallowed / unavailable / disregarded under GL-GATE-08), opt-out status, crawler contact | `ingest_run_report.robots_outcomes`; E2's opt-out register (E2 NEW-3) | robots disregard shown as host + count + policy reference if D-J3-2 says so; opt-out `no_register_yet` until E2's register exists |
| Cadence & freshness | declared cadence, next scheduled run (day granularity), observed cadence, last successful run, last content change, freshness state, volatility per predicate class | §4.6 | `not_scheduled`, `never_run`, `not_evaluable (n)` |
| Run log | last 20 runs + link to `…/runs/` | `runs.jsonl` | §4.5 |
| Capture history | last 20 captures + link to `…/captures/` | `captures.jsonl` | §4.4 |
| Coverage | subjects by jurisdiction (linked to dossiers), by technology, by entity type; time span of observations | release sites/claims grouped by source | `not_typed` until PKG-07; per-source totals equal the sum of the breakdown |
| Contribution to dossiers | per dossier: subjects/observations this source contributes, share of the dossier | per-dossier provenance (PKG-10 / DR-C3-02) | bidirectional: each dossier's "Sources" row links back here with the same number |
| Sample records | ≤10 deterministic released records (lowest record key per top jurisdiction) linked to `/r/<pub>/…` | release records | only gate-passed records; withdrawn → tombstone link; non-site sources show sample **claims** (predicate + value) that passed the gate, never document titles (P8-2/P8-3) |
| Downloads | this source's derived slice(s), statements rows, raw captures (if lane allows) with sizes + sha256 | `data/` manifest | §6 |
| Known issues | open and closed issues | `issues.jsonl` | §7.3 |
| Corrections | corrections affecting this source; "Found an error? Email ‹operator address›" | corrections log; Q-29 | per G2 §6 wording |
| Cite | release-pinned citation | §8 | — |
| Machine twin | `index.json` (`sig.source-page/1`) linked via `<link rel="alternate" type="application/json">` | — | — |

Gated, refused and `unknown`-lane sources get a **registry-only page** (J4 S-11): name, publisher, status, reason class,
homepage link — no runs, captures, samples or probe details.

### 4.4 Capture history (`/sources/<id>/captures/`)

Columns: `retrieved_at` (full ISO-8601 UTC, S-10), digest (sha256 or multihash, first 12 hex shown, full in JSON),
bytes, media type, state (`changed` / `unchanged` vs the previous capture of the same target), classification
(`actual` · `synthetic run-level stand-in, 0 bytes` · `legacy`), **bytes available** (`download` only if lane
`raw-ok` **and** bytes exist in the public archive **and** the P8 screen passed; else `metadata only — <reason>`),
target host (URL per S-6). Only 349 of 6,144 digests have stored bytes (J4 NEW-5): rows without bytes say
`bytes not retained` — never implying SIG can produce them. Paged at 100 rows.

### 4.5 Run log and metrics (`/sources/<id>/runs/`)

The operator's metric names map to recorded fields; anything not recorded says so.

| operator's metric | field | recorded today? |
|---|---|---|
| started / finished / duration | `ingest_run.started_at`, `ingest_run_completion.finished_at`, report `duration_seconds` | yes (duration via report backfill) |
| outcome | completion `status` (`ok · partial · quota_reached · failed`) or `no completion recorded (execution may have been killed)` | yes |
| fetched | report `fetches`; per-fetch status/bytes | count yes; per-fetch **no** (J1 NEW-6 → PKG-12) |
| parsed | report `records_emitted` / `ingest_run_capture.records` | yes (flushed marks) |
| claims considered / added / duplicate | completion `claims_considered` / `claims_inserted` / `claims_duplicate` | yes (backfilled rows: considered/duplicate `not_recorded`) |
| rejected | `assertion_quarantine` counts by reason class | yes (counts only) |
| errors | S-4 error class + count; refusals by class; rate-limit events | yes after scrub |
| robots / politeness | per-host outcome counts | yes |
| disappearances | count (+ artifact tombstone ids, S-9) | yes |
| code | connector name + version; commit hash per D-J3-3 | yes |

Rows are one line each in a table (≤100 per page), with a zero-JS `<details>` per run for the per-class breakdown.
`runs.jsonl` carries the same fields. **Silent success** (a run that "succeeds" with 0 records, SIG-ENG-021) is an
issue class, not a green row.

### 4.6 Freshness, cadence and the "volatility unknown" fix

Three different things the current page conflates:

1. **Cadence** (how often SIG *checks*): declared = `ops/cadence.toml` cron (221 sources) with registry `cadence` as
   fallback; `not_scheduled` for the 15 permitted-but-unscheduled sources; **next scheduled run** computed from the
   cron and shown to the **day** (not the minute — reduces blocking/targeting risk, §14 R-6); the status lane flags
   live-scheduler drift using the existing `sig-ops cadence --check` comparison (G1 NEW-10: images bake
   `cadence.toml`).
2. **Freshness state** (did the check happen on time): `on_time` · `late` (now > expected + 0.5 × interval) ·
   `overdue` (> 2 × interval) · `never_run` · `not_scheduled` · `last_run_failed`. **One function** computes it and is
   shared with ACT-02 alerting, so the page and the alert can never disagree.
3. **Volatility** (how fast the *facts* go stale, SIG-METRIC-006): per predicate class, with `staleness_not_evaluable`
   counts published (C3 NEW-8 → PKG-10). "Unknown" is replaced by `not_evaluable (n observations undated or on
   unregistered predicates)`. Whether a registry capture's `retrieved_at` may date a presence observation ("observed
   present at retrieval") is a SIG-TIME decision for PKG-10; J3 displays whichever PKG-10 emits.

**Last content change** is redefined from "last run that inserted a claim" to "last capture whose digest differs from
the previous capture of the same target" (NEW-3), falling back to the claims-inserted rule, labelled, where no capture
digests exist.

### 4.7 Budget per page

Source page ≤150 KiB transferred, 0 scripts: fixed sections + two 20-row tables; everything longer is paged. Largest
expected page: `camreg_osm_surveillance` (158 slices, many captures) — paged, so bounded (inference).

---

## 5. Record provenance and figure → evidence

### 5.1 The chain and its honest states

```
figure ─▶ release artifact + JSON pointer ─▶ record list / dossier provenance ─▶ record (/r/<pub>/c/<comp>/entity/…)
        ─▶ claim anchor #claim-<id> ─▶ evidence anchor (/r/<pub>/c/<comp>/evidence/<aid>/) ─▶ capture ─▶ upstream
```

Per claim, the panel states exactly one **binding state** (from `claim_evidence.binding_status`, L44):

| state | meaning shown to the reader (agent-drafted) |
|---|---|
| `actual_capture` | "Captured from <host> on <retrieved_at>; sha256 <…>." + view original (§5.3) |
| `replayed` | "Re-derived on <date> from a capture made on <retrieved_at>." |
| `document_only` | "Extracted from a document; no page capture." |
| `legacy_synthetic` (every claim today, G-6) | "Recorded by run <id> on <date>. SIG did not keep a per-record copy of the source for this run; the source's page lists the run and its captures." |

No state may imply a document SIG does not hold (C4 NEW-2 lesson).

### 5.2 Panel fields (on every released record page, per claim anchor)

Source (linked to `/sources/<id>/`) · binding state · capture `retrieved_at`, digest, bytes, media type · upstream
host (full URL per S-6) · view original (§5.3) · extraction method + extractor version · directness class
(`claim_directness`) · epistemic tier + review status (`review_status`; "Not yet independently reviewed" while
`not_run`) · contradictions (links to the competing claims and the contradiction record) · supersession history
(`revises_claim` / `retraction_of` chain with belief dates) · per-claim rights (SPDX + attribution from the registry) ·
"Equivalent requests": the JSON twin path and the API URL · dispute link (‹operator address›, Q-29).
Implementation: `published_record.py` fills `source_refs.upstream_href` (today hard-coded `None`, J1 NEW-10) from the
S-6-gated URL, and `record_claims.jsonl` (today built but not published, J1 §B.4) ships as the per-compartment
`statements` file, which is also the claim index the panel reads. Evidence anchor pages (`release_pages.evidence_page`)
gain capture history and view original; per-claim pages are **not** generated (2.42 M claims; G-10) — the existing
`/evidence/<claim>/` viewer (SIG-UI-028) is emitted only for claims with `actual_capture` bindings on document genres,
capped per release (e.g. ≤20k pages, inference) with the cap disclosed.

### 5.3 "View original" decision table

| lane | Part VIII class | bytes stored? | view original |
|---|---|---|---|
| `raw-ok` | clear | yes | "Download original (sha256 …, N bytes, retrieved …)" from `raw/<multihash>` |
| `raw-ok` | P8-5 / P8-6 / P8-8 (field screen) | yes | "Download redacted copy" — a re-serialisation recorded as a **new capture** (SIG-PUB-015/016), with method + version; the original is never served |
| `raw-ok` | any | no | "View at source" (URL per S-6) + "SIG did not retain these bytes" |
| `derived-only` | any | any | "View at source" + hash, size, time |
| `link-only` | any | — | "View at source" |
| `restricted` | P8-1 / P8-2 / P8-4 or terms | any | "Not redistributable — reason: <class>"; hash + date only (SIG-EVID-010 metadata representation; **no URL** where the URL itself could name a person, S-6) |
| `unknown` | — | — | "Rights not reviewed" |

### 5.4 Every displayed figure links to its evidence (C2 NEW-7; DR-C3-01)

- **Pointer contract.** Every material number is rendered by one component, `<Figure value=… artifact=… pointer=…
  definition=… href=…>`, which emits `data-artifact="<manifest path>"` and `data-pointer="<JSON pointer>"` and a visible
  "source" link. A build check fails any page whose rendered numbers (the component's output) lack a manifest-listed
  artifact; a second check fails raw numerals in page templates outside the component for a named list of page
  classes (home, dossier, coverage, freshness, sources, data, status).
- **Where the link goes**, by figure class:

| figure class | link target |
|---|---|
| headline counts (home, coverage) | the definition page anchor + the release artifact (`coverage.json#/…`) + the downloadable file that recomputes it |
| dossier counts ("7049 of 7049 … in GA") | `/r/<pub>/c/<comp>/jurisdiction/<j>/` record list + the dossier's page-specific provenance (per-source counts, PKG-10) + the per-source slices |
| per-source counts | `/sources/<id>/` coverage section |
| freshness / run metrics | the run row in `/sources/<id>/runs/` |
| contradictions | the contradiction record(s) |
| evaluation metrics | the published evaluation artifact (C3 DR-C3-03; today hard-coded TS constants must move into the release) |

- Page-specific "How we know this" (C3 NEW-3) is PKG-10's; J3 consumes it as the dossier link target.

### 5.5 API

`/v1/claim/{id}` adds `artifact_id`, `binding_status` and a `provenance` link (J1: a claim cannot reach
`/v1/evidence` today). `/v1/evidence` reads the derived tier (§3.3 item 4), returns `capture_classification`, full
`retrieved_at`, and the S-6-gated URL; `bytes_available` is true only for public-archive bytes that exist (J1 NEW-4,
NEW-2 here). Both are live-spine routes today; they must answer consistently with the release (C3 systemic cause 6),
which the API parity ticket checks (§6.10).

---

## 6. Downloads center

### 6.1 Routes

- `/data/` — the latest activated release's downloads (a mutable convenience view, labelled "latest; cite the release
  URL below").
- `/releases/<pub>/data/` — the citable, immutable listing (static HTML in the release tree).
- `/data/dictionary/` — data dictionary; `/data/api/` — API + JSON twins documentation with terms, tiers and rate
  limits (fixes the `/terms` 404 on the site and the unlinked API, C2 NEW-8).
- Linked from the global nav ("Data & downloads"), every dossier, every source page and every `Cite` block.

### 6.2 Bundle matrix (per release)

| unit | contents | formats (default → secondary) | licence |
|---|---|---|---|
| per compartment | `sites`, `statements`, per-compartment `datapackage.json`, `ATTRIBUTION.txt`, `LICENCE.txt`, `README.md` | parquet, csv.gz → geojson.gz, jsonl.gz, sqlite, pmtiles | the compartment's one licence (§42.3, SIG-EXPORT-005) |
| per source | `by-source/<id>` slice of each compartment it appears in | parquet, csv.gz | the source's compartment licence; attribution from registry |
| per jurisdiction | existing dossier JSON + a `sites` slice | json, csv.gz | per compartment |
| SIG graph | `sig_graph` files, crosswalk (SIG-EXPORT-007) | parquet, csv.gz, jsonld.gz | CC-BY-4.0 with third-party rows attributed per row |
| transparency metadata | `sources.json`, `runs.jsonl`, `captures.jsonl`, `issues.jsonl`, `counts.json`, `changes/` | json/jsonl.gz | CC-BY-4.0 |
| raw archive | `raw/<multihash>` per capture (raw-ok only), index `raw/index.json` | original media type | the upstream licence, per capture |
| whole-release | `SHA256SUMS`, signature, `catalog.jsonld`, `datapackage.json` (root), `CHANGELOG.md` | text/json | CC-BY-4.0 |

Excluded from downloads: `web/research_queue.json` (144 MB, a page payload; gzip or drop, J4 §7 control 4); the
restricted `web/map.json` / `density_bins.json` (mixed licence, J1 §B.3).

### 6.3 Size caps and formats

Default downloads are compact (parquet + csv.gz); no single file above ≈250 MB (split `osm_physical` by country or
first-level subdivision); files >100 MB also get a `.torrent` (existing `torrent.py`, deterministic, web-seeded from the
mirror) and only for openly licensed compartments (withdrawal cannot recall torrents, §9.3).

### 6.4 Integrity and signing

`SHA256SUMS` over every file in the listing (sha256 already in `manifest.json` and the ADR-132 integrity manifest);
a detached **minisign** signature `SHA256SUMS.minisig` with the public key on `/data/` and in the repo (key in env /
Secret Manager, HG-09; D-J3-8). Frictionless `hash` fields use the `sha256:` prefix (already, `frictionless.py:35-47`).
The release landing shows `publication_id`, `manifest_sha256` and "how to verify" commands.

### 6.5 Data dictionary

Generated, never hand-written: an exporter **column registry** (every emitted column → description, type, unit,
nullability, enum source) whose enum/slot entries come from the LinkML-generated schema (`ontology/generated`) and whose
export-only columns (`rights_*`, `point_status`, `n_sources`, …) are declared beside the writer. Emits
`dictionary.json`, a Table Schema per tabular resource (fixes 0/104, J1 NEW-11) and `/data/dictionary/`. **Build fails
on an undocumented column.** CSVW deferred (J2 S-9).

### 6.6 Machine-readable catalog without `<script>`

- **Frictionless Data Package v2** per bundle: `resources[].schema`, `resources[].sources`, `licenses`,
  `contributors`, `version` = `publication_id`, `created` = activation time; the 28 artifacts missing today are listed
  (J1 NEW-11).
- **DCAT 3** `catalog.jsonld`: `dcat:DatasetSeries` = SIG releases; one `dcat:Dataset` per compartment with
  `dct:license` (per-compartment) and `dct:accessRights`; `dcat:Distribution` with `downloadURL`, `mediaType`,
  `byteSize`, `spdx:checksum`; `dcat:previousVersion`; `prov:wasGeneratedBy` the export run; DCAT-US fields only where
  free (J2 S-4).
- **PROV-O** `provenance.jsonld`: capture `prov:generatedAtTime` = true `retrieved_at` (not export time), upstream
  `prov:hadPrimarySource`, digests; IRI base per PKG-09b (the `sig-project.org` NXDOMAIN namespace is J1 NEW-8 / PKG-09b's).
- **Linking, not inlining:** every page with a dataset or source gets `<link rel="alternate" type="application/ld+json"
  href="…">` and `<link rel="describedby" href="…/datapackage.json">`; `/sitemap.xml` lists the catalog (C2 NEW-27).
  Google Dataset Search prefers inline JSON-LD (J2 §3); if the operator wants that indexing, a **new ADR** would exempt
  non-executable `application/ld+json` blocks on `/data/` only, and the e2e `script` count test would need a
  type-aware rule (D-J3-7). Default: linked files only.

### 6.7 Licences and attribution per file

Each bundle's `ATTRIBUTION.txt` lists every source in that file with its registry attribution text, upstream licence,
terms URL and "changes made by SIG" notice (CC-BY family), the ODbL notice for OSM-derived content, and the OGL
statement for OGL sources — rendered from the registry (T-4). `LICENCE.txt` carries the compartment licence text or URL.
LicenseRef ids link to SIG-hosted explanation pages `/data/licences/<LicenseRef>/` (the spdx.org fallback URLs 404,
ED-35/PKG-08). The publish gate (PKG-08/ACT-07) must pass before any `ATTRIBUTION.txt` ships; **no downloads page goes
live while the J1 NEW-2/NEW-3 attribution defects or the NEW-1 terms conflicts (J4) are in the files** (D-J3-5).

### 6.8 Distribution and egress controls (J4 §7; SIG-EXPORT-008/009)

1. **Mirror:** the release's downloadable files are pushed to R2 (or the operator's alternative, D-J3-4) through
   `exports/push.py` (content-hash keys, immutable `Cache-Control`); `assert_low_egress` runs in the live publish path
   (today it runs only inside `exports/push.py:116`, which the live `ops` publish path never calls — J1 NEW-12). Download links point at the mirror's custom domain; GCS `sig-public` stays the
   origin of record.
2. **Non-listable origin:** remove anonymous listing (keep object reads during transition); the signed `SHA256SUMS` +
   catalog replace listing.
3. **Immutable versioned paths** `…/<pub>/…`; `latest` only as a JSON pointer.
4. **Rate limits:** per-IP concurrency cap and WAF rate rule on the mirror (Wikimedia's 3-connection cap is the
   precedent, J2 §2.15); stated openly on `/data/`.
5. **Kill switch:** billing budget + egress-bytes alert (ACT-03/QA-10) with a documented step (repoint links to
   mirror-only, or make the origin private).
6. **Ceiling:** operator sets a monthly egress ceiling (J4 suggests $50; Q-10).

### 6.9 Raw archive (D-J3-1)

Scope at launch: the `raw-ok` sources with stored bytes whose P8 class is clear (subset of J4's 35 sources, ≈35 MB);
P8-5/P8-6/P8-8 sources follow once their field-allowlist re-serialisation writes redacted **new captures** (hosted
append-only write, SIG-PUB-015); P8-1/P8-2/P8-4 and `restricted` never. Served per capture by content address
(`raw/<multihash>`), size-capped (e.g. ≤50 MB/object; larger → link-out). No "all raw" zip except the raw-ok set.
Withdrawal: delete the object from the mirror and the origin, purge the CDN cache by URL, write a tombstone record in
`withdrawals.json`, and return 410 with the tombstone body at the web-origin path (§9.2).

### 6.10 API parity and documentation

- `/v1/export` returns the real catalog of the latest activated release (from `catalog_entry.json` + integrity
  manifest) with absolute mirror URLs, sizes, sha256 and licences — replacing the hard-coded 404 href
  (`api/src/api/routes.py:466-488`, F-09).
- New read-only routes served **from the release registry files** (the P32.14 registry mount, ACT-17), not the live
  spine: `/v1/releases`, `/v1/releases/{pub}`, `/v1/releases/{pub}/sources[/{id}]`, `/v1/releases/{pub}/sources/{id}/runs`.
- Every J3 HTML page links its JSON twin and prints the "equivalent request" (J2 PC-3); `/data/api/` documents both,
  with numeric rate limits (C2 P7-T1).
- Parity test: for a sample of sources/records, the HTML, the JSON twin and the API response agree field by field.

---

## 7. Ingestion status and issues log

### 7.1 The status lane (justified runtime addition, T-10)

A Cloud Run **job** `sig-status-publish` (schedule every 6 h, D-J3-11) runs as a least-privilege identity (ACT-13
pattern) with read-only access to the `v_transparency_run/capture` views and the scheduler list; it scrubs (same
module), renders zero-JS HTML with the release-page helpers (`release_pages.py` style; no Astro rebuild) and publishes
**only** `status/**` through the single allow-listed publish path (ACT-05/PKG-04). It never touches records, claims or
release trees. Output: `status/state.json` (heartbeat, OSM `state.txt` pattern), `status/index.html`,
`status/sources/<id>.json`, `status/issues/index.html`, `status/archive/<YYYY-MM-DD>.json` (append-only daily). Cost ≈$0
(inference: 4 × ~1 min/day).

### 7.2 `/status/` page

Header: "Status as of <status_time> UTC. This page updates every 6 hours and is not a citation; the published data is
release <pub> (data as of <as_of_world>)." Then: runs in the last 24 h / 7 d by outcome; sources by freshness state
(§4.6); per-source row (last run start/finish, outcome, next scheduled day, freshness state, error classes 7/30 d,
claims added/duplicate/rejected 7 d); scheduler drift flag; probe uptime aggregates (J4: aggregates only, no targets).
Paged at 200 rows; 0 scripts. Gated/refused sources appear only as counts (S-11), unless D-J3-11 decides otherwise.

### 7.3 Issues log (`/status/issues/`, per-source section)

OpenSanctions-style warnings/errors per source (J2 §2.1), statically rendered (their JS-loaded rows are the
anti-pattern, J2 §6.9).

- **Auto-detected classes** (from run records, closed vocabulary): `upstream_http_<code>`, `robots_disallow`,
  `politeness_refusal`, `rate_limited`, `quota_reached`, `budget_reached`, `content_drift`, `disappearance`,
  `zero_records` (silent success), `quarantine_<reason>`, `late`, `overdue`, `never_run`, `scheduler_drift`,
  `capture_not_retained`. Each issue has `opened_at` (first run showing it), `last_seen_at`, `closed_at` (first clean
  run after), counts; history is append-only.
- **Curated known issues** (`known_issues.toml`, committed, keyed by source): e.g. axis-swapped coordinates (I1 NEW-2),
  jurisdiction code collisions (F-44), misattribution (J1 NEW-2), terms conflicts (J4 NEW-1), untyped technology
  (PKG-07). Each carries `issue_id`, class, opened date (true, `date -u`/git), status, a short public text
  (agent-drafted, operator-approved per batch, D-J3-12), links to the correction log entry that closes it.
- The issues log is also a **dataset** (`issues.jsonl`) in each release.

---

## 8. Releases, citations and permalink pinning

### 8.1 Site snapshots `/s/<pub>/` (D-J3-6; new ADR extending ADR-132)

P32.13 pins **records and dossiers** (`/r/<pub>/…`) but not the site pages people actually cite (home, methodology,
coverage, freshness, sources, data). SIG-UI-035 requires *every* page to be citable. Design: at each release the
same export-mode Astro build runs twice — base `/` (latest view) and base `/s/<pub>/` (snapshot) — and the snapshot is
staged into the release namespace, covered by the integrity manifest and withdrawal barrier. Hashed island assets under
`/_astro/` are shared. Size ≈60–150 MB per release (the site bucket is 51.5 MB today, J4 §0; plus ≈1.5–3k J3 pages,
inference) and ≈3–5k objects (≈$0.02 in writes, inference). Withdrawal: the exporter emits `s/<pub>/page_index.json`
(route → embedded entity/claim/source/artifact ids); `apply_withdrawals` extends to it, so a withdrawn record's
snapshot pages answer 410 with the tombstone body, exactly like `/r/` routes.

Cheaper fallback (if the operator declines snapshots): pin the *data* rather than the page — the cite block links the
release landing plus the figure's artifact pointer; the page itself is labelled "latest view".

### 8.2 The citation block

`BaseLayout` passes `release={publicationId, recordPath}` on every page (G-9/NEW-1). The block shows:
"Cite: <title>, SIG release <pub-short> (data as of <as_of_world>, belief <as_of_belief>, ruleset <r>),
<snapshot URL>" and the release id next to the as-of pair (DR-C3-14). The phrase "reproducible after SIG corrects
itself" appears **only** when the link is an immutable `/s/` or `/r/` URL; until G2 step 7 the block says "This page is
the latest view of release <data release id>; an immutable citable copy is not yet published." (agent-drafted).

### 8.3 Legacy `?as_of_world=&as_of_belief=&ruleset=` URLs at the edge

Activation generates `conf/selectors.conf` from `compat_index.json` (same mechanism as `withdrawn_*.conf`): a request
carrying any selector parameter is answered by the edge, never by the static file — exact match → 302 to
`/s/<pub>/<path>` (or `/releases/<pub>/`); no match → 404 page "no release covers that as-of; SIG never substitutes a
different cut" (+ the nearest activated releases); malformed → 400; ambiguous → 409 listing candidates. This is
`resolve_selector`'s contract (`release.py:1553-1629`) moved to the edge, with no app server. Selectors are date-grained
(NEW-4): either forbid two activations per (date, ruleset) or add an optional `as_of_release=<pub>` parameter to new
citations; G3 chooses. URLs already circulated with the 2026-09-27 as-of get the 404 page (they were never pinned) that
names the release that is now current.

### 8.4 Changelog and record-id diffs

At activation, `changes/` against the previous activated release: per compartment `added.parquet`, `removed.parquet`
(with reason class: withdrawn · superseded · source withdrawn · no longer published), `changed.parquet` (record id +
changed columns; sources/confidence not compared, Overture GERS lesson, J2 §2.7); per source: added / retired / newly
failing / lane changed; plus the human `CHANGELOG.md` (sources, counts, schema/ontology/ruleset versions,
deprecations with dates). `/v1/changes` (always empty today, J1) is backed by these files. The first release is a
baseline ("no previous release").

### 8.5 Prior releases (D-J3-10)

The 2026-09-24 ×2 and 2026-09-27 trees exist only in the restricted bucket and carry the NEW-1 and attribution defects
(J4 Q-J4-8). Recommendation: publish their **manifests** (ids, as-of, counts, sha256s) as history records with a
disclosure ("superseded; not republished because they credited some rows to the wrong source and included data whose
terms forbid redistribution"), not their bytes.

### 8.6 Interface with G3

G3 (release model) owns: release cadence, `latest` flip policy, where the registry lives, LB vs nginx topology, tags on
`main`, and the same-day selector rule. J3 requires from G3: (a) descriptor v2 (§3.4), (b) `/s/<pub>/` staging +
withdrawal coverage, (c) edge-generated selector config, (d) status lane as a separate non-release publish class,
(e) a release cadence no faster than the object-write and storage budget allows (P32.13 ≈$2.4 per full upload).

---

## 9. Part VIII, scrubbing and the withdrawal barrier

### 9.1 Scrub (one module, `policy/src/policy/transparency.py`)

Implements J4 S-1…S-14 verbatim as code with tests: credential query-param and header stripping (S-1), internal-path
replacement (S-2), no environment (S-3), closed error vocabulary (S-4), no IPs (S-5), URL gate (S-6), no personal data
(S-7), no record free text (S-8), withdrawal tombstones (S-9), full ISO timestamps (S-10), gated/refused minimal (S-11),
explicit-column views only (S-12), robots disclosure per decision (S-13), header allowlist (S-14). **Publish gate:** a
secret detector (`eyJ…`, `AKIA…`, ≥32 hex after `key=`, `Bearer …`) runs over **every** file in the publish set; one hit
aborts the publish (fail closed). Planted-secret tests cover each rule.

### 9.2 Withdrawal behaviour per surface

| surface | on a claim/entity/artifact withdrawal | on a source withdrawal (e.g. D-J3-5) |
|---|---|---|
| `/r/<pub>/…` records, evidence anchors | 410 + tombstone (ADR-132, existing) | every record from the source tombstoned in every release |
| `/s/<pub>/…` snapshots | pages in `page_index.json` embedding the id → 410 + tombstone | same |
| source page | sample record replaced by a tombstone link; counts from the next release | page stays (existence is publishable); status "withdrawn from publication on <date> — reason <class>"; runs/captures sections collapse to counts |
| bundles (compartment files) | whole artifact denied in affected releases (ADR-132: artifacts are withdrawn whole) — **per-source slices limit the blast radius**: the compartment file is denied, the unaffected sources' slices stay | the source's slices denied; compartment files denied in affected releases; next release omits the rows |
| raw archive | object deleted from mirror + origin, CDN purge, tombstone | all of the source's raw objects |
| status lane / logs | rows keep counts; ids replaced by tombstone ids (S-9) | runs shown as counts only |
| API | `access_decision` on every release-backed route (existing pattern) | same |

### 9.3 Irreversible distribution

Bytes already downloaded, torrented or deposited cannot be recalled (J2 pitfall 10). Therefore: nothing enters a
release until the publication gate, the attribution gate and the scrub gate pass; torrents and Zenodo deposits only for
openly licensed compartments after the attribution fix (D-J3-9); raw bytes only per §6.9; the withdrawal disclosure on
`/data/` states plainly that earlier downloads may still circulate and names the release that corrected them.

### 9.4 Part VIII points specific to transparency

- Raw captures keep what ingest discards (J4 NEW-4): OSM `user`/`uid` (SIG-INGEST-045e), ArcGIS editor usernames,
  Eyes on Flock search reasons → P8 screens before any byte ships; no raw download for a source with any non-C1 asset,
  because raw would undo precision reduction (§43.3, J4 P8-5).
- Logs: document URLs and filenames can name private persons (agenda/records genres) → host + path hash unless the
  document's claims passed the gate (S-6).
- Samples: only gate-passed records; no document titles for P8-2/P8-3 genres.
- Source ids that embed personal handles (C2 NEW-2 / C3 NEW-2, S0) are renamed before `/sources/` exists; old ids never
  appear in any new page, file or URL.
- Jurisdiction-conditional rules (SIG-PUB-017) apply to EU/FR procurement contacts (J4 P8-6).
- Robots disclosure (D-J3-2): publishing "disregarded" per host is honest conduct disclosure but may prompt vendor
  blocking (J4 Q-J4-4); the next-run day granularity (§4.6) avoids publishing a minute-level crawl calendar.

---

## 10. Sizes, costs and performance budgets

All **inference** unless cited.

| item | per release | growth | cost |
|---|---|---|---|
| transparency JSON (sources, runs, captures, issues, counts) | ≈15–30 MB | +2–3 MB/month | storage negligible |
| statements (2.42 M claims, per compartment, parquet + csv.gz) | ≈80–200 MB | with claims | negligible storage; egress on the mirror $0 |
| per-source slices (compact) | ≈60–80 MB | with rows | same |
| site snapshot `/s/<pub>/` | ≈60–150 MB, 3–5k objects | per release | ≈$0.02 writes |
| P32.13 release tree (existing) | 2.0 GB, 475k files | per release | ≈$2.4 writes (G2) — the dominant cost; G3 sets cadence |
| raw archive (raw-ok) | ≈35 MB today | +0.1–0.7 GB/month | R2 $0.015/GB-month (J4) |
| status lane | ≈2–5 MB/run, 4 runs/day | archive ≈1 MB/day | ≈$0 compute |
| downloads egress | — | — | GCS direct $13–600/month (abuse ≈$2.8k); **mirror ≈$0** (J4 §7) |

**Performance budgets (acceptance, all zero-JS pages):** 0 script bytes; ≤150 KiB transferred; Lighthouse performance
≥0.9 and accessibility 1.0; tables ≤200 rows (index/status) or ≤100 rows (runs/captures) per page; new Lighthouse CI URLs
`/sources/`, one `/sources/<id>/`, `/sources/<id>/runs/`, `/data/`, `/status/`, one `/r/<pub>/…/entity/…` with the
provenance panel. **Build budgets:** export +≤5 min (statements streaming dominates), Astro +≤5 min for ≈3k pages, the
snapshot build doubles the Astro time, status job ≤2 min.

---

## 11. Draft requirements

Ids are drafts in a provisional `SIG-TRANSP` family; T1 numbers them or folds them into SIG-EXPORT/UI/METRIC/EVID. Each
has testable acceptance criteria (AC).

| id | requirement (draft spec text) | AC |
|---|---|---|
| SIG-TRANSP-D01 | SIG MUST publish a source index listing every registered source with name, publisher, publisher type, technology classes, geography, lifecycle status, upstream licence, SIG publication basis, raw-bytes lane, last run and freshness state, filterable without JavaScript. | index rows == registry rows (342 at HEAD); each facet page's rows == the filter applied to `sources.json`; 0 `<script>`; every page ≤150 KiB |
| SIG-TRANSP-D02 | Every public count of sources MUST name one definition from a published counting funnel, and the funnel MUST list the source ids behind every difference between adjacent steps. | CI recompute of `counts.json` from release files passes; a crawl finds no source count outside the `<Figure definition=…>` component |
| SIG-TRANSP-D03 | Each source MUST have a page with the fields of §4.3; every field MUST be a value or a named absence kind. | `sig.source-page/1` JSON Schema validates for all sources; no empty field; no bare source id on any page (crawl) |
| SIG-TRANSP-D04 | A source page MUST link to the upstream ground truth (homepage, dataset endpoint, terms) after credential scrubbing, and MUST show the terms capture date and digest where one exists. | 100% of `ingested` sources show ≥1 http(s) upstream link or a named absence; planted-credential URLs never appear in output (test) |
| SIG-TRANSP-D05 | A source page MUST show capture history (full UTC time, digest, bytes, media type, changed/unchanged, classification, bytes-available) and MUST NOT state bytes are available unless the lane is raw-ok and the bytes exist in the public archive. | rows reconcile with `ingest_run_capture` ∪ `evidence_capture` at the belief cut; a synthetic capture is labelled; zero `bytes_available: true` for a non-raw-ok source (test over the release) |
| SIG-TRANSP-D06 | A source page MUST show a per-run log with outcome, times, duration, fetches, records parsed, claims considered/added/duplicate, rejected counts by reason class and error classes from a closed vocabulary. | per-source sums equal `ingest_run_completion` sums; any free-text error fails the export (test); runs without completion show "no completion recorded" |
| SIG-TRANSP-D07 | Freshness MUST distinguish cadence (declared, next scheduled day, observed), freshness state (one shared function with alerting) and predicate volatility (with not-evaluable counts); "last content change" MUST mean an upstream content-digest change. | no "unknown" without a reason class; the alert rule and the page call the same function (test); a digest-unchanged run never moves last content change |
| SIG-TRANSP-D08 | A source page MUST show coverage by jurisdiction and technology and its contribution to each dossier, and each dossier MUST link back to its sources with the same numbers. | per-source breakdown sums to its published subjects; dossier↔source counts equal in both directions (test) |
| SIG-TRANSP-D09 | A source page MUST show the rights-review record (basis, gate reference, reviewer role, decision date, counsel status) and collection conduct (robots outcomes per host, opt-out status) without naming persons. | no person names (pattern test + Part VIII review); dates come from `rights_decision` or carry the B1 correction note |
| SIG-TRANSP-D10 | SIG MUST publish an issues log per source (auto-detected classes + curated known issues) with opened/closed dates, append-only. | every run-record issue class maps to a vocabulary entry; closing an issue appends, never edits (test) |
| SIG-TRANSP-D11 | Every released record MUST carry a per-claim provenance panel (§5.2) stating one binding state and never implying a document SIG does not hold. | for a sample of ≥1,000 claims, every panel row resolves to a `statements` row and a capture or run record; `legacy_synthetic` claims render the run-level text |
| SIG-TRANSP-D12 | "View original" MUST follow the lane × Part VIII × bytes-stored table (§5.3). | a matrix test over one source per cell; no raw link for P8-1/P8-2/P8-4 or restricted lanes |
| SIG-TRANSP-D13 | Every material number on a public page MUST be rendered with a pointer to a manifest-listed artifact and a visible link to its evidence (§5.4). | build check fails on a figure without `data-artifact`; crawl: every figure link resolves (200) |
| SIG-TRANSP-D14 | SIG MUST publish a downloads center per release listing every downloadable file with licence, attribution, size, row count, sha256 and format, plus per-source slices and claim-level statements files. | every integrity-manifest artifact that is downloadable is listed; every link resolves; checksums verify (test downloads a sample) |
| SIG-TRANSP-D15 | Each downloadable bundle MUST carry `ATTRIBUTION.txt` generated from the source registry, and the publish MUST fail on any required-but-empty attribution. | 0 rows with `attribution_required` and empty attribution; bundle attribution == registry text (test) |
| SIG-TRANSP-D16 | SIG MUST publish a data dictionary generated from the ontology and the exporter column registry, and a Table Schema for every tabular resource. | build fails on an undocumented column; `frictionless validate` passes on every bundle |
| SIG-TRANSP-D17 | SIG MUST publish DCAT 3 and PROV-O metadata as linked files; public content pages MUST stay free of `<script>` elements, including JSON-LD, unless a new ADR exempts a named page. | JSON-LD parses; DCAT distributions carry `spdx:checksum`; e2e `script` count 0 on all non-island pages |
| SIG-TRANSP-D18 | Release files MUST be signed (detached signature over `SHA256SUMS`) with a published public key. | `minisign -V` passes in the verification test; key never in the repo or files (HG-09 scan) |
| SIG-TRANSP-D19 | Downloads MUST be served from a zero-or-low-egress host with a non-listable origin, per-file size caps, rate limits and an egress alert with a documented kill switch. | `assert_low_egress` in the live publish path; anonymous listing 403 (probe); alert policy present (probe); no file >250 MB |
| SIG-TRANSP-D20 | Raw captured bytes MAY be published only for raw-ok sources after the Part VIII byte screen; redactions MUST be new captures; withdrawal MUST delete, purge and tombstone. | only raw-ok sources in `raw/index.json`; P8-5/6/8 objects are redacted captures with method + version; a withdrawal rehearsal returns 410 at the web path and 404 at the mirror |
| SIG-TRANSP-D21 | SIG MUST publish a status page and heartbeat updated at least every 6 hours from scrubbed run records, labelled separately from the release as-of. | `state.json` age <12 h (probe); page shows both times; no field outside the J4 §8 publish list |
| SIG-TRANSP-D22 | Every transparency surface MUST pass the scrub gate (S-1…S-14); a secret-shaped value anywhere in the publish set MUST abort the publish. | planted-secret tests per rule; publish dry-run aborts on a planted token |
| SIG-TRANSP-D23 | Every public page MUST cite an immutable URL (`/s/<pub>/` or `/r/<pub>/`) with the release id; a legacy as-of selector MUST resolve at the edge to a real release or answer 400/404/409, never current content. | crawl: each page's cite link resolves under `/s/` or `/r/`; `?as_of_world=1999-01-01` → 404 page, not the current bytes (live probe after step 7) |
| SIG-TRANSP-D24 | Each release MUST publish an id-level diff against the previous activated release and a human changelog; `/v1/changes` MUST be backed by it. | diff counts reconcile (prev + added − removed = current per compartment); `/v1/changes` non-empty when the diff is |
| SIG-TRANSP-D25 | Every transparency page MUST have a JSON twin, and the API MUST serve the same release-backed data (§6.10). | parity test over a sample: HTML == JSON twin == API response |

Amendments proposed (for T1): SIG-METRIC-007 gains D07's three-way split; SIG-EVID-009 gains "the tier is derived from
the source's redistribution lane and Part VIII class, never defaulted" (NEW-2); SIG-UI-035 gains D23's edge rule;
SIG-EXPORT-002's RO-Crate clause is decided at S5 (J1 NEW-11: none published).

---

## 12. Round-11 ticket outline

Sizes: **S** ≈ half a fresh-context run, **M** one run, **L** a run that should be split (a/b) at T3. "Live" = the
ticket has a live stage needing an operator go. Order is dependency order; waves are indicative for S2.

| key | title | size | scope (one line) | depends (G2 step / ACT / F5 PKG / J3) | live / gate |
|---|---|---|---|---|---|
| TX-01 | Transparency scrub module + publish secret gate + capture-tier derivation | M | `policy.transparency` S-1…S-14, fail-closed secret scan in `sig-ops publish`, tier derived from lane + P8 class (NEW-2) | PKG-09a (grant cut) coordinate; **before** G2 step 1 (ACT-11) | — |
| TX-02 | Registry lanes + source metadata export + counting funnel | M | `[redistribution]` fields from the accepted lane table, `v_transparency_source`, `sources.json`, `counts.json` + recompute check | TX-01; ACT-07/PKG-08 (attribution); D-J3-1, D-J3-5; C2/C3 S0 handle renames (ACT-06) | — |
| TX-03 | Run/capture/issue export + freshness redefinition | M | `v_transparency_run/capture`, `runs.jsonl`, `captures.jsonl`, auto issue classes, cadence + freshness-state function (shared with ACT-02), last-content-change by digest | TX-01, TX-04; PKG-10 (volatility, not_evaluable) consumed | — |
| TX-04 | `ingest_run_report` table + writer + WORM backfill | M | sqitch change, `scheduled-ingest` writes, `backfill-run-reports` (+0 rerun), PKG-12 per-fetch fields when present | PKG-01 (sqitch CI); hosted deploy in the G2 step-1 window (not days 6–13) | hosted DB write — op go |
| TX-05 | Source explorer pages | L (05a index + facets + funnel; 05b source/runs/captures pages + JSON twins + linked names site-wide) | Astro routes, facet routes, `/search/` source facets, bare ids → linked names | TX-02, TX-03; PKG-06a (geo keys; `not_typed`/`unresolved` states before), PKG-07 (technology); supersedes ACT-06's interim sources page | republish — op go (HG-11 semantics) |
| TX-06 | Known issues + issues log | S | `known_issues.toml`, `issues.jsonl`, `/status/issues/` + per-source section | TX-03; D-J3-12 | via TX-07 / republish |
| TX-07 | Status lane | M | `sig-status-publish` job (6 h), `status/**` allow-list on the single publish path, heartbeat, archive, drift flag | TX-03; ACT-05/PKG-04 (single publish path); ACT-02 (shared SLA function); ACT-13 (least-privilege identity) | new scheduler job — op go |
| TX-08 | Record provenance panel + statements files | L (08a statements + `upstream_href` + panel with honest states; 08b evidence-anchor capture history + view original + API `/v1/claim`/`/v1/evidence` fixes) | `published_record.py`, `release_pages.py`, `record_claims` → `statements`, API fields | TX-01; real data after G2 step 1–2 (ACT-11/ACT-14: L44–52 + actual bindings); ACT-16 (archive links) | via ACT-24 |
| TX-09 | Figure → evidence pointers | M | `<Figure>` component, pointer build check, link targets per figure class | PKG-10 (page-specific provenance; eval metrics as artifacts); TX-05; TX-08a | republish |
| TX-10 | Downloads center + metadata | L (10a dictionary + column registry + datapackage v2 + DCAT + PROV consumer; 10b `/data/`, `/releases/<pub>/data/`, per-source slices, ATTRIBUTION/LICENCE per bundle, SHA256SUMS + minisign, `/data/api/`) | exporter + Astro + release tree | 10a: PKG-11 (enum hygiene), PKG-09b (IRI base, PROV fix); 10b: TX-11, ACT-03, ACT-07/PKG-08, D-J3-5, D-J3-8 | 10b republish — op go |
| TX-11 | Zero-egress distribution host | M | R2 (or chosen host) via `push.py`, `assert_low_egress` wired, non-listable origin, size caps/splits, torrent for >100 MB open compartments, WAF rate limit, egress alert + kill-switch runbook, withdrawal purge runbook | D-J3-4 (Q-10); ACT-03; PKG-04 | infra create + DNS — op go |
| TX-12 | Raw archive (raw-ok lane) | M | P8 screens (P8-5/6/8 re-serialisation as new captures), `raw/index.json`, view-original wiring, withdrawal delete/purge/tombstone rehearsal | D-J3-1; TX-01, TX-08b, TX-11 | hosted append-only write + exposure under HG-11 |
| TX-13 | Release-pinned citations + site snapshots + edge selectors | L (13a citation block + release id everywhere + honest interim wording; 13b `/s/<pub>/` build/staging/withdrawal index + `selectors.conf` + descriptor v2 ADR) | `BaseLayout`/`Citation`, release build, nginx include generation | 13a: none (ships in the next republish); 13b: G2 step 3 (ACT-15) and step 7 (ACT-24, **HG-11**), ACT-16/17, PKG-03/04; G3 decisions; D-J3-6; new ADR | 13b exposure with ACT-24 |
| TX-14 | Changelog + record-id diffs + `/v1/changes` | M | `changes/`, `CHANGELOG.md`, release landing section, API backing | TX-13b; the **second** activated release (first is the baseline); TX-02/03 | via release |
| TX-15 | API parity | S | `/v1/export` real catalog; `/v1/releases…/sources…` from registry files; parity test | TX-10b, ACT-17 (registry mount), ACT-11 (API roll) | API roll — op go |
| TX-16 | Transparency acceptance + HG-11 readout | S | live crawl, budgets, scrub audit (secret scan over all published transparency files), re-run of the journalist / researcher / skeptic journeys (**agent walkthrough, not user research**, P4/P5) | all of the above that are in scope | **HG-11** (operator signs the readout) |

**Transparency MVP** (first product wave, no dependency on G2 steps 1–7): TX-01 → TX-02 → TX-04 → TX-03 → TX-05 +
TX-06 + TX-07, TX-13a in the same republish, and TX-11 + TX-10b (downloads linked through the mirror) once ACT-03 and the
attribution gate pass. **After G2 steps 1–2:** TX-08, TX-09, TX-12. **With G2 step 7:** TX-13b, TX-15, TX-16. **After the
second release:** TX-14.

Merged or consumed (exactly one owner, P9): ACT-06's interim sources page (G2) is superseded by TX-05 (its content spec is
§4.1 + the licence/terms columns of §4.2); attribution integrity stays with PKG-08/ACT-07; page-specific provenance,
freshness `not_evaluable` and volatility stay with PKG-10; run telemetry (per-fetch URL/status/bytes) and `derived_from`
stay with PKG-12; PROV/IRI base stays with PKG-09b; the grant cut stays with PKG-09a; jurisdiction keys with PKG-06a;
technology typing with PKG-07; the opt-out register with E2; alert delivery with ACT-02.

---

## 13. Operator decisions needed

| id | question | recommendation | feeds |
|---|---|---|---|
| **D-J3-1** (Q-22a, Q-J4-1) | Publish raw captured bytes where the licence permits? Accept J4's lane table as the registry's `[redistribution]` field? | **Yes**, raw-ok only, after the P8 byte screen; P8-5/6/8 as redacted captures; start with the clear raw-ok sources that have stored bytes (≈35 MB); accept J4's lanes as the default, review on request (Q-J4-7) | TX-02, TX-12 |
| **D-J3-2** (Q-22b, Q-J4-4) | Publish scrubbed run logs, including robots disregard under GL-GATE-08? | **Yes** (S-1…S-14); disclose disregard as host + count + GL-GATE-08 reference; accept the vendor-blocking risk | TX-03, TX-05, TX-07 |
| D-J3-3 (Q-J4-5) | Show connector commit hashes while the repo is private? | Yes, version + commit; decide repo visibility separately (E1-21) | TX-03 |
| D-J3-4 (Q-J4-3, Q-10) | Distribution host and monthly egress ceiling | R2 mirror + custom domain; ceiling $50/month; kill switch | TX-11 |
| D-J3-5 (Q-J4-2) | Withdraw the NEW-1 sources (5,267 rows whose terms forbid redistribution or say "demo") before the explorer and downloads launch? | Yes, in the first wave, with a re-review; their source pages say "withdrawn from publication pending rights review" | TX-02, TX-05, TX-10b |
| D-J3-6 | Per-release site snapshots `/s/<pub>/` (new ADR extending ADR-132) | Yes (cheap; the only way every page becomes citable) | TX-13b, G3 |
| D-J3-7 | JSON-LD: linked files only, or an ADR exempting non-executable `application/ld+json` on `/data/` for Dataset Search? | Linked files only now; revisit if Dataset Search indexing matters | TX-10a |
| D-J3-8 | Signing: minisign key custody (operator, Secret Manager) vs Sigstore keyless (needs a CI publish path) | minisign, operator-held key | TX-10b |
| D-J3-9 (Q-J4-6) | Zenodo deposits and torrents: which compartments? | Openly licensed compartments only, after the attribution fix; manual, operator-run; never `operator_accepted` / `public_record` | TX-11, later deposit ticket |
| D-J3-10 (Q-J4-8) | Prior releases as public history? | Publish their manifests + a disclosure, not their bytes | TX-14 |
| D-J3-11 | Status-lane cadence; show gated/refused sources on `/status/`? | Every 6 h; gated/refused as counts only | TX-07 |
| D-J3-12 | Approval flow for per-source descriptions and known-issue texts | Agent drafts in batches of ~25; operator confirms verbatim; pages show `description_pending_review` until then | TX-05, TX-06 |
| D-J3-13 | Publish rights review-packet text? | Basis, gate reference, reviewer role and date now; packet text per packet after operator review (packets are in the private repo) | TX-05 |

Q-29 (answered): the correction contact on source and record pages is ‹operator address› with the G2 §6 wording.

---

## 14. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | Transparency amplifies existing defects: misattribution, terms-forbidden rows, fixture sources, personal handles, axis-swapped points become *more* visible and quotable | hard ordering: ACT-06 (S0 renames, fixtures), ACT-07/PKG-08 (attribution), D-J3-5 (NEW-1), PKG-06b (geometry) before TX-05/TX-10b go public; known issues listed openly on source pages |
| R-2 | Raw bytes or logs leak Part VIII material (plates, search reasons, OSM uids, editor usernames, names in filenames) | fail-closed scrub + secret gate (TX-01); raw only raw-ok + P8 screen, phased (TX-12); samples gate-passed only; HG-11 readout includes a scrub audit (TX-16) |
| R-3 | Egress blow-up once downloads are linked (abuse ≈$2.8k/month on GCS) | no download links before TX-11 + ACT-03; rate limits; kill switch |
| R-4 | Irreversibility: downloaded, torrented or deposited bytes cannot be recalled | gates before release; per-source slices; torrents/Zenodo only for open compartments; disclosure text |
| R-5 | Two clocks confuse readers (status newer than release) | T-7 labelling on every page; status pages never offer a cite block |
| R-6 | Vendor blocking after publishing robots disregard and schedules | operator decision D-J3-2; next-run at day granularity |
| R-7 | Scope: 16 tickets on top of G2's 25 and F5's 13 packages | MVP subset (§12); TX-12/13b/14 are later-wave; S2 sizes the round |
| R-8 | Descriptor v2 changes every namespace; stale citations to v1 namespaces | new ADR + announcement on `/releases/`; old namespaces stay reachable (immutable) |
| R-9 | Real provenance depends on L44–52 + actual bindings (G2 steps 1–2, not before 2026-10-14) | honest `legacy_synthetic` state ships first; TX-01's tier derivation lands before step 1 |
| R-10 | Single maintainer: description/issue-text approvals become a bottleneck | batches of ~25; pages ship with `pending_review` states rather than waiting |
| R-11 | Commit hashes point into a private repo (unverifiable) | D-J3-3; label "code repository not public" |
| R-12 | The status job becomes a second, unreviewed publish path | it can publish only `status/**` through the ACT-05 allow-list; a planted non-status file aborts (test) |

---

## 15. Interfaces

- **G3** (release model): §8.6 list. **G2**: TX tickets slot into steps 0 (TX-01/02/05/13a republish), 1 (TX-01 before
  ACT-11; TX-04 hosted deploy), 2–3 (TX-08 on real data), 7 (TX-13b/15/16 under HG-11). **C6**: the C2/C3 findings
  closed here — C2 NEW-4 (with NEW-1 here), NEW-7, NEW-8, NEW-15, NEW-27, NEW-29, NEW-31; C3 NEW-13, NEW-21 (funnel);
  J1 NEW-1, 4, 5, 6 (display side), 7, 10, 11, 12; J4 NEW-5 (display). **E2**: opt-out register, counsel labels, review
  packet disclosure. **I stream**: every newly ingested source gets its lane, cadence and description at onboarding
  (the I8 onboarding checklist should add "source page fields complete"). **B4**: the date guard also covers
  `known_issues.toml` opened/closed dates.

---

## 16. New findings (`findings/incoming/J3.csv`)

| id | title | sev |
|---|---|---|
| NEW-1 | Chain-tip citations stay unpinned even after P32.13 deploys: `BaseLayout` never passes a release to `Citation`, so every site page keeps the "reproducible after SIG corrects itself" query-string permalink, and the only selector resolver is an offline CLI | S1 |
| NEW-2 | The P32.2 actual-capture writer hard-codes `storage_tier = 'public'`, and `/v1/evidence` serves `source_uri` for every tier with `bytes_available` from that tier — once L44–52 go live, captures of derived-only, restricted and Part VIII sources will be advertised as public downloads with raw upstream URLs (latent) | S1 |
| NEW-3 | Freshness "last content change" is the last run that inserted a claim, not an upstream content change; capture digests that measure change are unused | S3 |
| NEW-4 | Historical selectors and the compat index are date-granular, so two releases activated on one day with the same ruleset make every legacy citation for that day "ambiguous" | S3 |

Related earlier findings, not re-raised: C2 NEW-4/7/8/15/27/29/31; C3 NEW-3/8/13/18/21; J1 NEW-1…13; J4 NEW-1…7;
E1 NEW-4/6; E2 NEW-3; F2a NEW-6; G1 NEW-3/10; G2 NEW-2; ED-34/35 (PKG-08).

---

## 17. Limits

- No live read was made by this row; production facts are as recorded by J1 (16:44–16:54Z), J4 (17:22–17:48Z), C2
  (17:30–18:10Z) and G2 (17:44–17:51Z). Counts derived from the registry and `cadence.toml` are code reads at HEAD.
- Sizes for statements, slices, snapshots and page counts are estimates from J4's unit sizes; the TX tickets must
  measure them (the P32.13 `measure_build` pattern) before rollout.
- Whether registry claims carry `observed_at` (the volatility root cause, G-4) is inferred from code comments, not a
  spine query.
- Nothing here is a legal opinion; lanes and rights labels come from J4's classifications and remain operator decisions
  (P4, HG-03).
- NEW-2 is latent: it describes code that is not yet running on hosted (L44–52 undeployed, G2 §1).

---

Work window closed 2026-09-30T18:32:16Z (`date -u`). Findings file: `findings/incoming/J3.csv` (4 rows).
