# Frozen launch baseline — 2026-09-24 (P30.1, GO-LIVE.1)

> **What this is.** The settled, as-of launch numbers that P30.2 (materialization) and P30.3
> (national export / cut-over) build from. Taken over the hosted `sig-pg` spine **after** the
> `camreg_osm_surveillance` OSM land (D-SOURCES.17-1) completed and was verified. Every figure is a
> **named-denominator count at `as_of`** over an append-only spine — never a population total
> (§32 / SIG-METRIC-008), never a claim about cameras that exist in the world beyond the evidence
> (§3.1). Counts are **raw claims / observation-level entities, pre-resolution** (cross-source
> duplicate cameras are not yet merged — that is P30.2's resolution materialization).

- **as_of:** `2026-09-24T03:43:19Z` (spine watermark `claims=2274818 closed=0 latest_assertion=2026-09-24T03:35:06.465199+00:00 evidence=2274818/247/247`)
- **spine:** hosted Cloud SQL `zeta-medley-508121-u7:us-central1:sig-pg` (POSTGRES_18, RUNNABLE, tier `db-custom-2-8192` — see *Operator deviation*), read via `cloud-sql-proxy` as DB user `sig`, every statement in a `READ ONLY` transaction
- **source of record:** `docs/build/reports/PUBLIC_SURFACE_AUDIT.md` + `public_surface_audit.json` (schema `p30.1/1.0.0`, `snapshot_status: settled`); shaped intermediate `docs/build/reports/p27.3-shaped/manifest.json` (same as-of)

## 1. OSM land — complete (D-SOURCES.17-1)

| evidence | value |
|---|---|
| Cloud Run execution | `sig-ingest-camreg-batch-05-tjqdq` — **Completed successfully** 2026-09-24T03:35:13Z after 5h9m47s (started 2026-09-23T22:25Z; `succeededCount: 1`) |
| GCS run row | `gs://zeta-medley-508121-u7-sig-restricted/ops/runs/camreg_osm_surveillance/2026-09-23/2026-09-23T22-27-38+00-00.json` — `outcome=ok`, `exit_code=0`, 158 capture digests, `claims_added=1,369,210` (= records **emitted** by the connector, `len(report.claims)`, not rows inserted) |
| OSM claims on the spine | **1,214,682** (distinct claims whose establishing capture's `evidence_artifact.source_id = 'camreg_osm_surveillance'`) |
| OSM entities on the spine | **154,528** (distinct subjects; = `entity_identifier` rows `traffic_camera:camreg_osm_surveillance:%`) |
| duplicate content digests among OSM claims | **0** (unique index `claim_content_digest_key`, `content_digest IS NOT NULL` on every OSM claim) |

**Emitted-vs-landed reconciles exactly.** The `dot_511` ArcGIS path emits, per feature, one
`record_kind="traffic_camera"` entity record plus one `record_kind="claim"` row per predicate;
`PgClaimSink.assert_claims` counts the entity records as `non_claim_records` and writes no L1 row
for them. 1,214,682 claims + 154,528 entity records = **1,369,210** = the run row's `claims_added`.

**The ≈2.43M projection was an over-count, not a shortfall.** 1,059,533 (the recorded pre-land
baseline) + 1,369,210 emitted = 2,428,743 ≈ "2.43M" — it counted the 154,528 non-claim entity
records. The true spine delta reconciles to the row:
1,059,533 + 1,214,682 (OSM) + 337 (`escribe`) + 266 (`sam_gov`) = **2,274,818** = `count(*) FROM claim`.

**Idempotency (the `+0` property) — verified on the hosted spine, without a new multi-hour ingest.**
`tjqdq` was itself a full replay: the earlier execution `…-p964s` (2026-09-22T16:49Z →
cancelled ~22:25Z 2026-09-23) had already committed **930,000** OSM claims — exactly 93 chunks of
`SIG_COMMIT_CHUNK_SIZE=10000` — through the chunked path, and
`tjqdq` re-fetched all 158 pages and re-walked **all** 1,369,210 records. Evidence the re-walk of the
already-committed prefix inserted nothing:

- per-hour inserts of OSM claims (`lower(sys_period)`): steady 22k–40k/h through 2026-09-23 21:00Z,
  6,062 in the 22:00Z hour (p964s before cancellation), **0 in 23:00Z, 00:00Z, 01:00Z** (tjqdq
  fetching + replaying the committed prefix — every insert `ON CONFLICT DO NOTHING`), then 158,458
  (02:00Z) + 126,224 (03:00Z) = 284,682 = 1,214,682 − 930,000 as the replay reached the
  un-committed tail;
- 0 duplicate `content_digest` values among OSM claims, and landed claims = emitted claim rows
  exactly (above) — so each claim landed **once** across two executions (+0 on the replayed prefix);
- the spine held flat after completion: `count(*) FROM claim` = 2,274,818 at 03:40:15Z, 03:41:29Z,
  in the audit (03:43:19Z), in a second byte-identical audit re-run (03:45Z; JSON identical except
  `generated_at`), and in the shaping watermark (03:45:58Z); `0` claims recorded after 03:35:07Z.

## 2. Settled headline (D-P27.1-1) — named denominators

| metric | value |
|---|---|
| claims | 2,274,818 (all current; `closed=0`) |
| entities | 246,738 (246,734 `deployment`, 4 `organization`) |
| sources (hosted `source_registry`) | 212, of which 211 `ingestion_permitted` |
| publishable (as-recorded) | 2,018,043 of 2,274,818 claims (redistributable=yes) (88.71%) |
| UNDETERMINED (as-recorded) | 256,775 of 2,274,818 claims (11.29%) |
| **publishable (effective, post-decision)** | **2,274,812 of 2,274,818 claims (100.0%)** |
| **UNDETERMINED (effective, post-decision)** | **0 of 2,274,818 claims (0.0%)** |
| **geolocated** | **230,007 of 246,738 entities (93.22%)** |
| `observed_at` present | 174,465 of 2,274,818 claims (7.67%) |
| sensitivity tier | 2,274,818 of 2,274,818 claims at tier 0 |
| modeling tables (`resolution`, `relationship`, `contradiction`, `coverage_record`, …) | all EMPTY — the P30.2 materialization gap |

## 3. Launch-scope split (effective rights, claims)

| slice | claims (of 2,274,818) | note |
|---|---:|---|
| ODbL-1.0 (the OSM-derived / share-alike ODbL compartment, §42.3) | 1,220,651 | kept separate from the graph compartment at export (`assert_separated`) |
| CC-BY-SA-2.0 + CC-BY-SA-4.0 (share-alike, non-ODbL) | 58,634 | compartment assignment is the export gate's decision (P30.3), not asserted here |
| other redistributable (CC0, CC-BY-*, OGL-*, PublicRecord, OperatorAccepted, …) | 995,527 | |
| **not redistributable** (`LicenseRef-MuckRock-API-ToS`) | 6 | excluded from any public surface |
| effective UNDETERMINED | 0 | the P27.2 decisions (33 `rights_decision` rows) cover the whole as-recorded UNDETERMINED set (256,775), incl. the +337 as-recorded-UNDETERMINED claims landed since the P27.2 re-measure |

Re-confirmed vs the P27.2 provisional split: the launch scope does **not** change shape — the OSM
land is entirely ODbL-1.0 (as-recorded ODbL = 5,929 pre-land + 1,214,682 OSM = 1,220,611; effective 1,220,651 adds the 40 `raa_prefectures` decision-resolved claims), so it grows the ODbL
compartment only; the non-ODbL redistributable set moves by +337 claims (1,054,161 now vs
1,053,824 in the P27.2 re-measure over 1,109,799 claims), and the 6 non-redistributable claims are
unchanged.

## 4. Shaped intermediate (P27.3 verb, re-derived at the same as-of)

`sig-exports shape` (read-only `REPEATABLE READ READ ONLY` snapshot) → `docs/build/reports/p27.3-shaped/`:
claims read/shaped **800,056 / 800,056** (0 excluded as not publishable), publishable subjects
**230,007**, geolocated **227,660**, conflicted **2,347** (kept visible, `geometry: null`),
multi-source observation groups **2,776**; provenance complete (800,056 of 800,056 published
claims with resolvable evidence). `sites.json`/`sites.geojson` (≈0.9 GB / 0.26 GB) are not
committed, as in P27.3.

## Operator deviation (recorded)

The tickets' default is "no Cloud SQL scaling". The operator approved a **temporary** scale-up of
`sig-pg` **`db-f1-micro` → `db-custom-2-8192`** (~22:25Z 2026-09-23) after `…-p964s` proved
I/O-bound on `db-f1-micro` (~400–470 claims/min, projected to time out ~89% done); `p964s` was
cancelled and `tjqdq` re-executed. The instance is **intentionally left** at `db-custom-2-8192`
through P30.2 materialization and is scaled back at P30.4. P30.1 did not touch the tier.

## Follow-ups opened (not implemented here; BL-057)

- **D-P30.1-1** — batch / pipeline-mode writes in `PgClaimSink` (the replay was latency-bound,
  one round-trip per insert, not DB-bound).
- **D-P30.1-2** — incremental restarts: stream claims to the sink per capture and/or skip
  already-captured pages, so a restart is not a full ~57 MB re-fetch + ~1.37M-record re-walk.

## Reproduce

```bash
cloud-sql-proxy --token "$(gcloud auth print-access-token)" --port 5439 zeta-medley-508121-u7:us-central1:sig-pg &
export PGPASSWORD="$(gcloud secrets versions access latest --secret=sig-pg-password --project zeta-medley-508121-u7)"
uv run python -m exports audit --dsn "postgresql://sig@127.0.0.1:5439/sig?sslmode=disable" \
  --as-of 2026-09-24T03:43:19Z --settled \
  --note "P30.1 settled re-audit — OSM land complete (sig-ingest-camreg-batch-05-tjqdq, 2026-09-24T03:35:13Z); frozen launch baseline" \
  --markdown-out docs/build/reports/PUBLIC_SURFACE_AUDIT.md --json-out docs/build/reports/public_surface_audit.json
```

A later run over the same spine reports larger numbers as scheduled ingests append — that is a new
as-of, not a correction of this one.
