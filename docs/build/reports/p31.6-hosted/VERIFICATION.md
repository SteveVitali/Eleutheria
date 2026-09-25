# P31.6 hosted verification — access edges + accountability links materialized

Ticket: `P31.6 / DEEPEN.2` — `docs/tickets/P31.6__access-edges-and-hosted-link-materialization.md`
ADR: ADR-113 (asserting replay of persisted captures).
Host: project `zeta-medley-508121-u7`, region `us-central1`, Cloud SQL `sig-pg`.
Every query below ran `SET TRANSACTION READ ONLY` over cloud-sql-proxy as `sig`;
writes ran as the least-privilege `sig_materialize` role inside Cloud Run job
executions next to the database (ADR-103). Nothing was `UPDATE`d or `DELETE`d.

## Images (digest-pinned, ADR-111)

| job | image | digest |
|---|---|---|
| `sig-replay-ingest`, `sig-ingest-eyes-on-flock`, `sig-ingest-eff-data-driven` | `sig/sig-api:p31-6-184e3644adea` | `sha256:ad06e964a4119fc7c1135826114e2314bb1bbb8813d8d45b3d522a24823e6f99` |
| `sig-materialize` | `sig/sig-api:materialize-40b530332f6b` | `sha256:f79577fcff83657e03e4ada6c88f773b9cba9a0c1c0bf407405ad82e0fa8a971` |

Ingest image built by Cloud Build `1658b5c3-6d2c-4994-b143-7b6fb9d4a79f` (56 s);
materialize image by `0053a191-9a8f-4b87-a803-979cc42679c2` (58 s). Both rolled jobs
confirmed on the pinned digest before and after execution.

## Baseline → after (`inventory_before.json` → `inventory_after.json`)

| measure | before | after |
|---|---|---|
| claims | 2,350,634 | 2,391,551 |
| claims with `object_entity` | 0 | 29,826 |
| `camera_operator` claims / with ref | 255,832 / 0 | 285,328 / 29,496 |
| `configured_sharing_partner` claims / with ref | 0 / 0 | 260 / 130 |
| `vendor` claims / with ref | 0 / 0 | 400 / 200 |
| entities (deployment / organization) | 248,496 / 0* | 248,507 / 8 |
| `relationship` rows | 0 | 130 |
| `inference.derived_fact` rows | 0 | 200 |

\* the before-file measured organizations after the camreg/ut/or replay already
began in the same session; pre-replay organizations were 0 for partner purposes.

## Asserting replays (`sig-ops replay-ingest`, fresh `is_replay=true` runs)

| run_id | source | logical_run | replay_of_runs | considered | inserted | duplicate | status / missing |
|---|---|---|---|---|---|---|---|
| `01a0d74b-4213-719a-8627-5eef5b2e972a` | camreg_osm_surveillance | `camreg_osm_surveillance@replay-p31-6` | `01a0d5cf-…`, `01a0d5d3-…` | 246,848 | 26,839 | 193,170 | ok / 0 |
| `01a0d74e-99ef-7700-9e42-0b5cc8919458` | dot_511_ut | `dot_511_ut@replay-p31-6` | `01a0d6bc-…` | 13,285 | 1,469 | 10,347 | ok / 0 |
| `01a0d74e-9a7a-7467-9e19-e33bf14b0e8a` | dot_511_or | `dot_511_or@replay-p31-6` | `01a0d72a-…` | 13,068 | 1,188 | 10,692 | ok / 0 |

- Missing-capture disposition: `ingest_run_completion.detail` is NULL on all three —
  zero persisted capture digests absent from the OCFL store (the replay records a
  non-empty detail and `partial` status otherwise; `runner.py:1340-1356`).
- Lineage: `is_replay=true`, `replay_source`/`replay_of_runs` parameters, WORM
  run-record JSON under `ops/runs/<source>/2026-09-25/…`, and 35 `replay:`-prefixed
  `ingest_run_capture` marks carrying the original capture digests.
- `replay_of_runs` lists the runs contributing distinct capture digests; duplicate
  marks are deduplicated for selection while the original marks preserve full
  lineage (documented in ADR-113).
- No network: replay resolves only `gs://…-sig-restricted/evidence/captures/` bytes;
  missing digests are skipped, never re-fetched.

## Rolled live jobs (new access-edge + vendor claims landing)

| job execution | source | logical_run | considered | inserted | duplicate | finished |
|---|---|---|---|---|---|---|
| `sig-ingest-eyes-on-flock-xt4fq` | flock_portal | `eyes_on_flock@2026-09-23T05:00Z` | 11,976 | 9,746 | 1,517 | 06:46:54Z ok |
| `sig-ingest-eff-data-driven-smldn` | data_driven | `eff_data_driven@2026-09-04T05:00Z` | 1,863 | 1,675 | 0 | 06:46:47Z ok |

Both executions `EXECUTION_SUCCEEDED` on the pinned digest. The EoF inserted claims
include the 260 `configured_sharing_partner` edges (130 with `sig.connector.subject`
/`flock_portal:<slug>` refs; refused audit-side names stay literal, unmapped — never
fabricated); EFF's include the 400 `vendor`/`configured_sharing_partner` claims
(200 with `sig.org.name` refs → the NVLS vendor org).

## Materialization (least-privilege `sig_materialize`, Cloud Run `sig-materialize`)

| step | execution | first run | re-run |
|---|---|---|---|
| `materialize-edges` | `sig-materialize-vk8wp` (07:05Z) | **130** `configured_access` rows | `sig-materialize-z7nx8` (07:09Z) → **+0** (130 rows / 130 digests) |
| `materialize-accountability-links` | `sig-materialize-jprfv` (07:11Z) | **200** `accountability_link:has_vendor` facts (`accountability_linkage/§13`, rule `p28.6/1`) | `sig-materialize-4fbql` (07:14Z) → **+0** (200 rows / 200 digests) |

Evidence backing (read-only joins):

- `relationship` × `claim` on `evidence_claim`: **130/130** edges cite a claim with
  `object_entity IS NOT NULL`; every edge is directed `a_to_b`,
  `access_kind='configured_access'`, from the agency deployment entity to the
  partner entity, with the claim's `valid_from_kind`/`valid_to_kind` preserved.
- `inference.derived_fact` × `claim` on `input_claim_ids[1]`: **200/200** links cite
  a `vendor` claim with `object_entity IS NOT NULL`; `value_json.establishing_claims`
  names the claim and `object_id` the vendor organization entity.

## Dispositions

- **D-P30.2-2 → DONE.** Hosted `count(object_entity)` = 29,826 > 0; edges 130 > 0,
  links 200 > 0, both re-runs +0; every materialized row cites an entity-ref claim.
- **D-P31.5-1 → DONE** (edges > 0 from emitted claims — closed by this ticket).
- **D-P31.5-2 → OPEN** (read-surface `publication_review_required`; owned by P31.16/HG-11).
- **D-P30.2a-1 → OPEN** (remaining predicate families; owned by P31.8).
