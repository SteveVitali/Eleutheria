# Round 9 — post-launch engineering follow-ups: design and plan

> **Status: DRAFT for operator ratification, 2026-09-24.** Written on the planning branch
> `devin/round9-planning`, forked from the P30.4 tip (`devin/p30-4-post-launch-closeout` @ `0a715fc`).
> **Nothing here is on the chain.** `docs/build/LEDGER.md` CURRENT STATE and `docs/tickets/00_MANIFEST.md`
> are unchanged. The draft contracts live in `docs/build/reports/round9-drafts/`, not in `docs/tickets/`,
> because the build-memory validator requires every file in `docs/tickets/` to have a manifest chain row
> (`scripts/docs/check-build-memory.sh` §2), and adding rows would seed the chain. ADR numbers are
> placeholders (`ADR-R9-*`). The next free number at seed time is ADR-108. Row numbers 142 onward are
> proposals.
>
> Method: `decompose-spec mode=extend`, drafts only. Format precedent: `ROUND6_7_DEPTH_ACTIVATION_DESIGN.md`.
>
> **Update 2026-09-24 — RATIFIED + Wave A SEEDED.** The operator answered §6 (recorded verbatim in §10 and in
> `docs/build/LEDGER.md` § GATE DECISIONS). Wave A (P31.1–P31.4) is on the chain as manifest rows **142–145** on
> branch `devin/round9-seed`; its four contracts moved to `docs/tickets/`. Wave B + tail stay drafts here until Wave A
> lands. Two answers CHANGED the plan (Q5 re-sightings uncapped; Q11 human review deferred → Opus 5.5 LLM first pass,
> P31.18 → Round 10); the §3 table is updated to match. The draft text of §0–§9 is otherwise kept as written.

## 0. Why this round exists

The national site is live on https://surveillancegraph.org (launch record `LAUNCH_RECORD_2026-09-24.md`), and
ACCEPT-R8 is signed. `projectStatus` is still `IN-PROGRESS` for one reason: the P30.4 sweep
(`DEFERRALS.md` § "P30.4 sweep") left about 19 **engineering** deferrals with a backlog home (BL-055/056/057)
but no scheduled ticket. Under BM-TAIL-03, a backlog home is not a landing. This round gives each of them a
ticket, an explicit deferral, or an operator decision.

The go-live also taught us a lot about running on the live system. The contracts below build those lessons in,
so the next run does not have to learn them again (§5).

## 1. Inventory — every OPEN engineering deferral, verified

Verified against `docs/tickets/DEFERRALS.md` at `0a715fc` and against the code (anchors re-confirmed
2026-09-24; re-confirm again at build time).

| # | row | what is owed (one line) | verified code fact | Round-9 ticket |
|---|---|---|---|---|
| 1 | D-P30.4-1 | `sig-api` does not reconnect after a DB restart | `api/src/api/store_pg.py:152`: one `psycopg.connect(..., autocommit=True)` per instance, no pool, no liveness check, no health endpoint in `api/src` | **P31.1** |
| 2 | D-P30.4-2 | `/v1/search` has no bound and times out | `store_pg.py:459-480`: `ILIKE '%q%'`, no LIMIT, 1 + up to 3N follow-up queries (`_label_for` `:285`, `_source_ids_for_entity` `:298`); `pg_trgm` is used nowhere in `db/` | **P31.1** |
| 3 | D-P30.3-1 | ingest-run rows never close, so freshness shows `not-recorded` | nothing in the repo sets `ingest_run.finished_at`/`status`; `claim_sink.py:277-305` `_ensure_run` **reuses** one row per (connector, version, commit, is_replay), so one row covers many executions | **P31.2** |
| 4 | D-P30.4-3 | entity-creation race; 3 duplicate `(scheme, value)` pairs | `claim_sink.py:423-448` `_entity_for_subject`: check, then `INSERT entity`, with no lock and no uniqueness guard | **P31.3** |
| 5 | D-P30.1-1 | batched or pipelined sink writes | `claim_sink.py:452-541`: 3 or more round trips per claim; `_ensure_predicate` is not cached | **P31.3** |
| 6 | D-P30.1-2 | incremental restarts | `connectors/.../pipeline.py:163-250`: all claims are held in memory, then **one** `assert_claims` at the end; no capture-skip or resume | **P31.4** |
| 7 | D-P30.2-2 | 0 claims carry `object_entity`, so 0 edges and 0 accountability links | the sink hard-codes `object_type='literal'` (`claim_sink.py:501-529`); procurement buyer/seller are text (`procurement.py:2976-2995`); `configured_access_edge` records (`flock_portal.py:726`, `audit_structural.py:780`) are **dropped** by the sink (`claim_sink.py:208-214`) | **P31.5 + P31.6** |
| 8 | D-P30.2a-2 | re-sightings are not recorded | `claim_sink.py:530-532`: a duplicate returns before the `claim_evidence` link | **P31.7** |
| 9 | D-P30.2a-1 | about 100 non-camera predicates have no registry row, and genre directness is unassessed | `ontology/vocab/predicates.yaml` (ADR-104 pattern); pre-existing predicates are D6 for `camera_registry`/`connector_run` | procurement family → **P31.5**; the rest → **P31.8** |
| 10 | D-P30.2-1 | the negative-space peer class would emit 26.7M rows | `inference/.../materialize.py:327-374`: peer class = `entity_type`, and every hosted entity is `deployment`; `materialize.sh:82` always passes `--no-negative-space` | **P31.9** |
| 11 | D-P30.2b-1 | review decisions do not feed camera-site clustering | the curation API queue is a **demo seed** (`api/.../curation.py:590-602`) that writes JSONL, not PG `review_decision`; `review_pg.py:177-215` `decide` exists, but **nothing reads `review_decision`** (`review_pg.py:23-25`) | review surface → **P31.10**; clustering wiring → **P31.11**; humans → **P31.17**; closure (hosted clustering of real decisions) → **P31.18** |
| 12 | D-P30.2b-3 | a source republishes its own layer twice | constraint (a) in `camera_sites.py:685-692` | **P31.11** |
| 13 | D-P30.2b-2 | name-level device-kind and place soft conflicts; needs a fresh holdout | rules `camera_site_rules.toml` v2; gold `camera-2` | **P31.18** (skeleton, with the human holdout) |
| 14 | D-R6.1-EVAL (first-principles half) | re-derive the auto-vs-human balance from human ground truth | 11,625 review items (11,235 proposed pairs + disagreement and disputed items), **0 decisions** | **P31.17** (human) → **P31.18** (skeleton) |
| 15 | D-R7.3-BREADTH | the 8 flipped sources have no connector | all 8 are absent from `CONNECTOR_FOR_SOURCE` (`runner.py:67-363`); class connectors exist: `accountability` (gao, dhs_oig, dhs_fusion, uk_scc), `government_mandated_disclosure` (ccops ×3), `procurement` federal-assistance (fema_hsgp) | **P31.12 + P31.13** |
| 16 | D-SOURCES.12-1 (engineering remainder) | 68 probe-error rows to retry (the wave tail is already closed via D-SOURCES.17-1, DONE) | the rights half is DONE; 67 of the 68 rows carry `spdx=null` and have **no** rights basis, so a successful retry is registered `ingestion_permitted=false` for review and never wired | **P31.13** (bounded tail) |
| 17 | D-P30.3-3 (+ D-P27.5-1) | presentation analytics are not emitted by the export | `web/src/lib/data.ts:509-562` reads optional `web/presentation/*.json`; `ops/publish.py:126-129` **refuses** to publish `web/presentation/` (demo guard) | **P31.14** |
| 18 | D-P30.3-2 | no zoomable vector tiles, no basemap, no compression | `exports/tiles.py:186-241`: pure-Python z0 only; no tippecanoe in `ops/Dockerfile`; `sig-web` is stock `nginx:1.27-alpine`, with no nginx config in the repo | **P31.15** |
| 19 | D-P30.4-4 | the armed project-id leak check fails on 45 build-memory files | `tests/connectors/test_secrets.py:95-114` greps **every** tracked file | policy decision → **P31.19** |

**Excluded as operator-only** (noted, not scheduled): D-P21.3-2 (HG-09 export tokens), D-P21.5-1 (HG-07
Zenodo token), **D-P21.7-1** (HG-08 OSM OE page), D-JURIS.2-1 (HG-04 eID), D-SOURCES.2-2/-2-4/-7-1/-7-2/-8-1/
-8-2/-9-1/-9-4 (reviewer/operator rights and keys), D-SOURCES.9-2/-9-3 (external), D-FEDERAL.1-1 (scheduled cron),
D-R7.1-AUTH (a deliberate later decision), **D-R7.2-SEND** (records-request send, operator-gated), the
**MapRoulette key rotation**, and the **PR-stack merge #112–#136** (INTEGRATION_PLAN). D-P21.4-3 is already
landed (a formatting artefact). D-P30.3-COUNSEL is DONE by attestation (0a715fc).

## 2. Prioritization and rationale

The order puts risk to the live site first, then things with a deadline, then depth, then presentation:

1. **Wave A — keep the live site honest and safe (P31.1–P31.4). Ratify now.**
   - **P31.1 API resilience + bounded search.** At present, *any* Cloud SQL maintenance window takes every
     DB-backed `/v1` endpoint down until someone manually recycles it. That is the highest-probability
     outage we have, and it can happen without anyone touching the system. `/v1/search?q=<common term>` hangs
     until the request timeout. It is a cheap DoS vector on a public API. Both fixes are in one file
     (`store_pg.py`) and ship in one deploy: the first new `sig-api` image since 2026-09-16 (see §6 Q2).
   - **P31.2 Run completion → real freshness.** The public `/data-freshness/` page says `not-recorded`
     for all 178 sources, which undersells the data and reads as neglect. It is honest, but it is wrong in
     spirit. The fix is small and has high visible value.
   - **P31.3 Sink identity guard + batched writes** and **P31.4 incremental restarts** have a date. The
     monthly OSM replay `sig-sched-camreg-batch-05` fires **2026-10-10** on the scaled-down 1-vCPU
     `db-custom-1-3840` (ADR-107). The last full replay took 5h10m on 2 vCPU with a latency-bound sink,
     held about 1.37M claims in memory, and restarts from zero if interrupted. The race guard goes in with
     batching because both rewrite the same prerequisite-insert path, and the deferral asks for exactly this
     pairing ("ideally with D-P30.1-1").
2. **Wave B — make the graph deep (P31.5–P31.13). Ratify after Wave A lands.**
   - **Entity links first (P31.5 → P31.6).** 0 edges and 0 accountability links is the biggest gap between
     what SIG says it is ("accountability infrastructure") and what the public sees. Every later depth item
     (network centrality, the accountability dossiers, and the breadth sources' funder/oversight links)
     reads `object_entity`.
   - **Re-sightings (P31.7)** come after batching (P31.3), because they change the same duplicate path.
     They also come after the 10-10 replay, so that replay does not write about 1.37M re-sighting links
     before the storage budget is decided (§6 Q5).
   - **Registry (P31.8)** and **negative space (P31.9)** make coverage and resolution meaningful for the
     non-camera majority of predicates.
   - **The review loop (P31.10 → P31.11)** comes before the human campaign (P31.17). Without it, humans
     have no surface that writes to PG, and their decisions would change nothing.
   - **Breadth (P31.12–P31.13)** comes last in Wave B. New accountability sources should land after entity
     links exist, so they add links from day one rather than more unlinked text.
3. **Wave B tail — the public surface catches up (P31.14–P31.16).** Analytics (which needs edges), tiles and
   compression, then **one** re-materialize + re-export + republish (P31.16) behind HG-11. Batching the
   republish avoids republishing six times.
4. **Gated EVAL track (P31.17 human → P31.18 skeleton)** and the closeout (P31.19).

## 3. Ticket plan (the Round-9 chain)

Each contract is sized for **one fresh-context implement-spec run** at the `subagent` ceiling. Split
permission is written into the larger ones. All are Lane **C** except P31.17 (human marker, Lane A) and
P31.18 (skeleton).

| row | ticket | semantic | one-line goal | closes | gate | size | ADR |
|---|---|---|---|---|---|---|---|
| 142 | P31.1 `api-db-resilience-and-bounded-search` | HARDEN.1 | reconnect/pool with liveness + bounded, indexed, paginated `/v1/search`; roll `sig-api` by digest | D-P30.4-1, D-P30.4-2 | operator OK for the image roll (Q2) | M | R9-API (small; optional) |
| 143 | P31.2 `ingest-run-completion-and-freshness` | HARDEN.2 | per-execution run identity + append-only run completion + a WORM-sourced backfill → real freshness dates | D-P30.3-1 | — (republish is routine, Q3) | M | **R9-RUNLIFE** |
| 144 | P31.3 `sink-identity-guard-and-batched-writes` | HARDEN.3 | entity-creation guard + triage of the 3 duplicate pairs; batched/pipelined claim writes, measured | D-P30.4-3, D-P30.1-1 | — | L | **R9-SINK** |
| 145 | P31.4 `incremental-restart-and-osm-replay-readiness` | HARDEN.4 | stream claims per capture + resume without re-fetching captured pages; measured readiness for 2026-10-10 | D-P30.1-2 | operator: roll onto batch-05 before 10-10? (Q4) | M–L | **R9-RESUME** |
| 146 | P31.5 `entity-ref-claims-procurement` | DEEPEN.1 | the sink writes `object_entity`; procurement/accountability partners become org entity-ref claims; procurement predicates registered | D-P30.2-2 (part), D-P30.2a-1 (procurement) | — | L | **R9-ENTITYREF** |
| 147 | P31.6 `access-edges-and-hosted-link-materialization` | DEEPEN.2 | access edges persisted as claims; hosted replay from captured evidence; edges + accountability materialized > 0 | D-P30.2-2 | — | M | — (ADR-103) |
| 148 | P31.7 `claim-re-sightings` | DEEPEN.3 | link **every** re-asserted claim to the new capture (uncapped, Q5 as ratified) + measure actual row growth vs the Cloud SQL disk; decide the dating basis | D-P30.2a-2 | — (Q5 answered 2026-09-24: record every re-sighting; measure growth) | M | **R9-RESIGHT** |
| 149 | P31.8 `predicate-registry-legislation-portal` | DEEPEN.4 | register the legislation/portal/other families + assess genre directness; hosted re-resolution | D-P30.2a-1 | — | M | — (ADR-104) |
| 150 | P31.9 `negative-space-peer-classes` | DEEPEN.5 | peer class = declared tracked-predicate sets per (entity_type, connector class); materialize hosted negative space | D-P30.2-1 | — | M | **R9-PEERCLASS** |
| 151 | P31.10 `camera-site-review-surface` | DEEPEN.6 | curation review queue over PG `review_item`/`review_decision` + a stratified campaign sampler | D-P30.2b-1 (intake half) | — (loopback app, ADR-068/100) | M | — |
| 152 | P31.11 `review-decisions-into-clustering` | DEEPEN.7 | human same_as/distinct decisions feed the camera-site run; within-source duplicate-target exception | D-P30.2b-3 (advances D-P30.2b-1) | — | M–L | **R9-HUMANER** |
| 153 | P31.12 `accountability-breadth-federal-uk` | BREADTH.1 | wire gao / dhs_oig / dhs_fusion / uk_scc through `accountability`; hosted land + rights apply + re-resolve | D-R7.3-BREADTH (4/8) | — (flipped under GL-GATE-07) | M | — |
| 154 | P31.13 `accountability-breadth-ccops-fema` | BREADTH.2 | wire ccops_oakland/cambridge/somerville + fema_hsgp; the 68 probe-error retries | D-R7.3-BREADTH, D-SOURCES.12-1 | — | M | — |
| 155 | P31.14 `presentation-analytics-from-export` | SURFACE.1 | emit density bins, centrality/focus, watch decision point, provenance summaries, W1–W3 from the spine export | D-P30.3-3, D-P27.5-1 | — | M–L | **R9-ANALYTICS** |
| 156 | P31.15 `vector-tiles-and-compression` | SURFACE.2 | tippecanoe z0–z14 per compartment, compressed `sig-web`, the island reads tiles; basemap per Q8 | D-P30.3-2 | basemap choice (Q8) | M–L | **R9-TILES** |
| 157 | P31.16 `rematerialize-reexport-republish` | SURFACE.3 | re-run every materializer, re-export nationally, republish, probe; verify the surface halves | surface halves of rows above | **HG-11** (Q10) | M | — |
| 158 | P31.17 `llm-annotation-first-pass` | ANNOTATE.1 | **`claude-opus-5-5` LLM annotation first pass** over ~400 stratified camera-site pairs; agreement vs the P30.2b seed/verifier labels + the earlier LLM run. Not human ground truth | advances D-R6.1-EVAL (stays OPEN) | — (Q11 answered 2026-09-24: human review deferred) | M | — |
| ~~159~~ | ~~P31.18 `resolution-eval-from-first-principles`~~ | ~~EVAL.1~~ | **MOVED TO ROUND 10** (Q11, 2026-09-24): the human review campaign + this re-derivation from human labels are Round-10 work; draft kept as the Round-10 starting point | (D-R6.1-EVAL, D-P30.2b-2, D-P30.2b-1 — Round 10) | Round 10 | — | (R10) |
| 160 | P31.19 `round9-closeout` | CLOSE.1 | leak-check policy (Q7), deferral sweep, capstone, `projectStatus` per BM-TAIL-03 | D-P30.4-4 + sweep | — | M | R9-LEAKSCOPE (if Q7=a) |

**19 rows: 17 implement-spec contracts, 1 human marker, 1 skeleton.** All **20** OPEN engineering deferral ids in §1
(19 inventory lines; D-P27.5-1 shares line 17) map to a ticket. D-SOURCES.12-1 and D-P27.5-1 are the two that were not in the operator's candidate
list. I added them because the P30.4 sweep names them as engineering-owned with no chain row.

### Dependencies (backward only; physical order = chain order)

```
P31.1            (independent)
P31.2 ─► P31.3   (both edit `_ensure_run`; the sink records P31.2's per-execution run identity)
P31.3 ─► P31.4   (streams into P31.3's batched sink; resume key = P31.2's run identity; P31.4 rolls ALL ingest jobs by digest)
P31.3 ─► P31.5 (entity-ref writes reuse the batched path + the identity guard for org entities)
P31.5 ─► P31.6 (hosted replay needs the emitters) ─► P31.14 (centrality needs edges)
P31.3 ─► P31.7 (the duplicate path is rewritten by P31.3)
P31.5 ─► P31.8 (procurement family already registered; the remaining families follow the same pattern)
P31.10 ─► P31.11 ─► P31.17 (human) ─► P31.18 (skeleton; also closes D-P30.2b-1)
P31.4 (10-10 outcome recorded) + Q5 ─► P31.7's roll onto batch-05
P31.5/P31.6 ─► P31.12, P31.13 (new sources emit entity links from day one)
P31.2, P31.6, P31.8, P31.9, P31.11–P31.15 ─► P31.16 (one republish)
everything ─► P31.19
```

Out-of-chain/parallel: P31.17 is a **pause, not a block**. It can start as soon as P31.10/P31.11 are
deployed, and the chain continues past it (RETURN PASS). P31.18 stays a skeleton until P31.17 is
dispositioned.

### Shared decisions and their owners (the Phase-4 "fragmented decision" guard)

- **The claim write path** (`PgClaimSink` chunk transaction, prerequisite caching, and the duplicate path) is
  **owned by P31.3**. P31.4 (streaming), P31.5 (`object_entity`) and P31.7 (re-sightings) extend it and must
  not re-design it. P31.3's ADR states the extension points: a per-claim duplicate hook, and entity-ref
  object resolution.
- **Run identity** (one `ingest_run` per execution plus an append-only completion record) is **owned by P31.2**.
  P31.4's resume key reads it. P31.4 must not invent a second run notion.
- **Org entity identity for partners** (identifier scheme, normalization, and the never-a-person rule) is
  **owned by P31.5**, which uses P31.3's guard. P31.6/P31.12/P31.13 consume it.
- **Human ER decision semantics** (`accept` → human same_as, `reject` → distinct, `decided_by`, and
  precedence over later auto decisions) are **owned by P31.11**. P31.10 only writes `review_decision` rows
  through the existing `PgReviewQueue.decide`, so its cut is clean.
- **Rolling the scheduled ingest jobs onto new code** is **owned by P31.4**. `scheduled-ops.sh` deploys by an explicit
  digest (today it hard-codes `${SIG_API_IMAGE}:latest`, `:48`), and all jobs are rolled only after the hosted schema is
  confirmed. P31.5/P31.7/P31.12/P31.13 roll through that mechanism, never through `:latest`.
- **Hosted capture persistence** (whether stored evidence bytes exist on hosted to resume or re-interpret) is
  **owned by P31.4** and consumed by P31.6. Ingest jobs today write captures to a container-local `.sig/captures`
  (`runner.py:840`).
- **Asserting re-interpretation of stored captures** (`replay.py` is deliberately non-asserting) is a named decision
  **owned by P31.6** and recorded in an ADR.
- **Rolling `sig-web`** (compression config + tiles) is **owned by P31.16**.
- **The re-export and republish** of the public surface is **owned by P31.16**. Earlier tickets verify their
  data read-only on the hosted spine and through local export runs, but they do **not** republish. The
  exception is P31.2, which may run a freshness-only republish if the operator approves (Q3).

## 4. ADRs expected (placeholders; real numbers from ADR-108 at seed)

| placeholder | owner | decision |
|---|---|---|
| ADR-R9-RUNLIFE | P31.2 | one `ingest_run` per execution; completion is an **appended** row (new sqitch change), never an `UPDATE` of `ingest_run`; backfill rows carry `source = gs://…/ops/runs/…` WORM provenance and are labelled backfilled |
| ADR-R9-SINK | P31.3 | batched/pipelined writes (multi-row `INSERT … ON CONFLICT DO NOTHING RETURNING` per chunk, or psycopg pipeline mode); the entity-identity guard mechanism (advisory lock per `(scheme, value)` in the chunk transaction, or a new unique side table, since a plain `UNIQUE` cannot build over existing duplicates); recorded same_as/distinct decisions for the 3 pairs |
| ADR-R9-RESUME | P31.4 | restart = resume: claims commit per capture; a restarted execution skips targets already captured under the same logical run, **and still counts them as seen** so disappearance detection and freshness are unchanged |
| ADR-R9-ENTITYREF | P31.5 | partner names become org entity-ref claims **in addition to** the existing text claims (additive); org identity scheme + normalization (`normalize_org_name`, crosswalk); **never a person entity** (Part VIII); the ambiguity rule (unresolvable → text only) |
| ADR-R9-RESIGHT | P31.7 | re-sighting = a `claim_evidence` link to the new capture (+0 claims); dating basis earliest vs latest capture; storage budget / granularity (see Q5); `input_digest` churn accepted |
| ADR-R9-PEERCLASS | P31.9 | peer class = (entity_type, connector class) with a **declared** tracked-predicate set per class (data file); replaces "union of predicates any peer carries" |
| ADR-R9-HUMANER | P31.11 | human decisions precede auto decisions in clustering; re-cluster stability + SIG-IDENT-032 public ids; the within-source **target-duplication** exception to constraint (a), allowed only with target-level lineage evidence (identical target content) |
| ADR-R9-ANALYTICS | P31.14 | resolves D-P27.5-1: analytics are **export-emitted** (a new `web/analytics/` artifact family, not the demo-guarded `web/presentation/`); definitions of density bins, centrality measure, W1–W3 tiers |
| ADR-R9-TILES | P31.15 | tile pipeline (tippecanoe in the export image or a tile job), nginx compression, basemap source (Q8), and the fate of the ACCEPTED combined `/map/points.json` (Q9) — may supersede ADR-106 §5 in part |
| ADR-R9-EVAL | P31.18 | the re-derived auto-vs-human balance (required by D-R6.1-EVAL; SIG-ENG-003 "a new ADR, never a silent threshold edit") |
| ADR-R9-LEAKSCOPE | P31.19 | only if Q7 = (a): the project-id leak check scopes to code + config; build memory is exempt |
| ADR-R9-API (optional) | P31.1 | the search contract (result cap, cursor pagination, `pg_trgm` GIN index) and pool sizing against `max_connections=100` |

Every new ADR carries `## Revisit trigger` (`tests/unit/test_policy_adrs.py`) and adds an Appendix F row in the
same PR (SIG-ENG-039: `spec_src/99a_appF_adr.md` → `BUILD.sh`; `check_spec_src.py` exit 0).

## 5. Hosted-execution lessons, built into every relevant contract

From the P30.1–P30.4 run ledgers and ADR-102/103/107:

1. **Run heavy DB work next to the DB**, as a Cloud Run job, using the `ops/gcp/materialize.sh` / `export.sh`
   pattern. Do not run it on a laptop over `cloud-sql-proxy`: P30.3's local export attempt stalled and moved to
   `sig-export`.
2. **Tag every image by SHA** (`sig-api:<purpose>-<sha>` from `git archive HEAD` via Cloud Build). **Never
   retag or move `:latest`.** Point jobs and services at the digest.
3. **Use the literal connection string.** Write the DSN single-quoted and expand it *inside* the container:
   `postgresql://${SIG_PG_USER}:${SIG_PG_PASSWORD}@/${SIG_PG_DB}?host=/cloudsql/${SIG_CLOUDSQL_CONNECTION}`
   (`materialize.sh:73`). The password comes from a Secret Manager binding. Never put a password on a command
   line, and never write the project id literally (`$SIG_GCP_PROJECT`, D-P30.4-4).
4. **Measure before any long run.** Take a read-only shape/throughput measurement on a bounded sample, give an
   honest ETA, and only then run. Scale up temporarily only in the ADR-102 pattern: record it and scale back.
5. **After any `sig-pg` restart** (tier change, maintenance), redeploy `sig-api` **on the digest it is
   currently serving**. Never do a label-only update: that re-resolves `:latest` (ADR-107 §5). P31.1 aims to
   make this unnecessary, and P31.16's scale-up/down is its production proof.
6. **Every hosted write is re-run for +0** (idempotency proof), and every hosted count is read back read-only.
   No hosted number is fabricated. If something cannot run, it is recorded as OPEN with the exact re-run
   command.
7. **Do not re-fetch quota-bound APIs to replay.** Replay from captured OCFL evidence (`connectors/replay.py`).
   SAM.gov and OpenStates quotas have burned us twice.
8. **Connection budget.** `db-custom-1-3840` has `max_connections=100`. API pools, job concurrency and the
   materializers must fit inside it.
9. **Deploy scripts can hide `:latest`.** `ops/gcp/scheduled-ops.sh:48` deploys every ingest job on
   `sig-api:latest`. Any cadence-row deploy therefore re-resolves `:latest` unless P31.4's digest mechanism is used.
10. **Hosted evidence may not persist.** Ingest-job captures go to a container-local directory, so check whether the
    bytes exist before planning any "replay from evidence" or "skip captured pages" step.
11. **Online DDL.** Build indexes on hot tables `CONCURRENTLY` (non-transactional sqitch change) or when no ingest is
    running. Project the bytes of every large write against the 15 GB disk first.

## 6. Open questions for the operator (answer to ratify)

1. **Ratification shape.** Ratify **Wave A (P31.1–P31.4) now** and Wave B + tail after Wave A lands, as Round
   6/7 did? Or ratify all 19 now? *Recommendation: Wave A now.*
2. **`sig-api` image roll (P31.1).** Live `sig-api` still runs the **2026-09-16** image
   (`sha256:cc680111…`). Any API fix rolls in all P27–P30 API changes at once. Do you approve a SHA-tagged roll,
   verified by `probe-hosted` + a route smoke, with `cc680111…` as the recorded rollback digest? And may the
   hosted reconnect proof **terminate `sig-api`'s own DB backend** (`pg_terminate_backend`, as `postgres`)
   instead of waiting for a maintenance window? *Recommendation: yes to both.*
3. **Freshness republish (P31.2).** May P31.2 do a freshness-driven re-export + republish (routine cadence data
   plus real run dates; it pauses if the diff shows anything else), or should it wait for the single P31.16
   republish? *Recommendation: republish in P31.2, because the page is public-facing now.*
4. **2026-10-10 OSM replay (P31.4).** If P31.3/P31.4 land and measure green before 10-10, should the new image be
   rolled onto `sig-sched-camreg-batch-05` before the replay (faster and resumable), or should 10-10 run on
   the current image as the ADR-107 baseline and the new path be adopted after? A temporary scale-up for the
   hosted measurement run (ADR-102 pattern)? *Recommendation: roll before 10-10 only if the hosted bounded
   measurement is green by 2026-10-08; otherwise keep the baseline.*
5. **Re-sighting storage (P31.7).** Recording every re-sighting adds about one `claim_evidence` row per
   re-asserted claim per cadence run: about 1.37M rows a month from OSM alone, on a 15 GB disk. Options: (a)
   every re-sighting; (b) at most one per claim per cadence window; (c) only when the capture content digest
   changed. *Recommendation: (b), with (c) noted in the ADR.*
6. **Duplicate-entity pairs (P31.3).** `us.state OK` and `fr.insee 01` may be deliberate (e.g. a registry
   entity plus a crosswalk entity) rather than races. Is it OK for engineering to triage them and record
   same_as or distinct decisions with evidence, with no operator sign-off per pair? *Recommendation: yes.*
7. **The project-id leak check (D-P30.4-4).** (a) Narrow it to code + config through an ADR, since a GCP
   project id is not a credential and build memory is append-only history; or (b) redact, which can legitimately
   touch only files that are **not** append-only records (landed ADR bodies, DEFERRALS rows, LEDGER and run-ledger
   history cannot be rewritten, P1–P3). So (b) cannot on its own make the armed check pass. *Recommendation: (a).*
8. **Basemap (P31.15).** (a) No basemap (today's plain background) plus real z0–z14 tiles; (b) a self-hosted
   basemap extract (e.g. a Protomaps US build) in the public bucket, which adds storage and egress cost; or (c) a
   third-party tile service, which sends visitors' viewports to a third party and runs against the privacy
   posture. *Recommendation: (a) now, and (b) as a costed follow-up.*
9. **The combined `/map/points.json` (ACCEPTED R8 deviation).** Once per-compartment tiles serve the map, should
   the combined file be retired? That would return the site to strict licence separation. *Recommendation: yes,
   retire it in P31.15.*
10. **HG-11 for P31.16.** Publishing the first **relationship edges and accountability links** (organisation ↔
    organisation, vendor ↔ agency) and negative-space coverage changes what the site asserts. Should P31.16 pause
    for your sign-off? *Recommendation: yes, pause, with a diff summary.*
11. **The human review campaign (P31.17).** Who adjudicates: you, the P29.1 vetted curators, or both? What is
    the sample target? *Proposal: about 400 stratified pairs across tiers 1g/3g/4g/5g plus the soft-conflict
    and disputed buckets, enough for a Wilson 95% lower bound near 0.98 on the auto tiers at about 150 pairs
    each.* Is P31.18 in this round, or should it move to Round 10?
12. **Backlog home.** Keep the existing homes (BL-055/056/057) and set their `landing` to the P31 rows at seed,
    or mint a BL-058 "Round 9" umbrella in theme T4 (the themes stay capped at 10)? *Recommendation: keep the
    existing homes and add no new BL.*

## 7. Non-goals (Round 9)

- **No operator-only action** (§1 excluded list): no records-request **send** (D-R7.2-SEND), no OSM OE-page
  registration or MapRoulette push (D-P21.7-1), no key rotation, no token export, no rights flip, no HG-nn tick.
- **No merge, tag or push to `main`.** The operator integrates the stack (#112–#136, then the P31 PRs) per
  INTEGRATION_PLAN.
- **No public authenticated contribution** (D-R7.1-AUTH stays a deliberate later decision). No open signup.
- **No new source classes and no untargeted breadth.** Breadth is limited to the 8 already-flipped sources and
  the 68 retries.
- **No change to the resolution thresholds** outside P31.18's ADR. The PROVISIONAL disclosure stays on every
  "resolved" surface until D-R6.1-EVAL closes.
- **No UPDATE/DELETE on the claim spine** (run completion is appended; corrections are new rows). No
  in-place sqitch edits.
- **No client JS on public content pages.** The `/map` island stays inside the ADR-091/097 allowance.

## 8. Proposed manifest block (DRAFT — **not** applied to `00_MANIFEST.md`)

Append after row 139 at seed time. The seed branch forks from the P30.4 tip.

```markdown
> **Round 9 — post-launch engineering follow-ups (rows 142–160, `HARDEN.1…4`, `DEEPEN.1…7`, `BREADTH.1…2`,
> `SURFACE.1…3`, `HUMAN-H4`, `EVAL.1`, `CLOSE.1`).** Seeded <date> by a planning session off the P30.4 tip
> (`devin/p30-4-post-launch-closeout`), from the design branch `devin/round9-planning`
> (`docs/build/reports/ROUND9_FOLLOWUPS_DESIGN.md`). It schedules every engineering deferral the P30.4 sweep left
> with only a backlog home (BM-TAIL-03). **Wave A** (rows 142–145) hardens the live system before the 2026-10-10
> OSM replay: API reconnect + bounded search, real freshness, the sink identity guard + batched writes,
> incremental restarts. **Wave B** (rows 146–157) deepens the graph (entity-ref claims → edges + accountability
> links, re-sightings, registry, negative space, the human review loop, the 8-source breadth), then refreshes the
> public surface once (analytics, tiles, one republish behind HG-11). **Gated tail:** the human review campaign
> (row 158, marker — a pause, not a block) → the first-principles eval skeleton (row 159) → closeout (row 160).
> Waves ratify independently (Wave A now; Wave B after Wave A lands). ADR-108 onward are minted by their owning
> tickets (see the design doc §4). Backlog homes BL-055/056/057 (landing → P31.x). All Lane C except row 158
> (Lane A marker) and row 159 (skeleton).

| # | file | phase | kind | lane | scope | gate |
|---|---|---|---|---|---|---|
| 142 | `P31.1__api-db-resilience-and-bounded-search.md` | 31 | ticket | **C** | **[semantic `HARDEN.1`]** reconnect/pool with liveness + bounded, indexed, paginated `/v1/search`; SHA-tagged `sig-api` roll by digest. Closes **D-P30.4-1**, **D-P30.4-2**. | operator OK for the image roll |
| 143 | `P31.2__ingest-run-completion-and-freshness.md` | 31 | ticket | **C** | **[semantic `HARDEN.2`]** per-execution run identity + append-only completion + WORM backfill → real freshness dates. Closes **D-P30.3-1**. | — |
| 144 | `P31.3__sink-identity-guard-and-batched-writes.md` | 31 | ticket | **C** | **[semantic `HARDEN.3`]** entity-creation guard + triage of 3 duplicate pairs; batched/pipelined claim writes, measured. Closes **D-P30.4-3**, **D-P30.1-1**. | — |
| 145 | `P31.4__incremental-restart-and-osm-replay-readiness.md` | 31 | ticket | **C** | **[semantic `HARDEN.4`]** per-capture streaming + resume without re-fetch; measured 10-10 readiness. Closes **D-P30.1-2**. | operator: roll onto batch-05 |
| 146 | `P31.5__entity-ref-claims-procurement.md` | 31 | ticket | **C** | **[semantic `DEEPEN.1`]** sink writes `object_entity`; partner org entity-ref claims; procurement predicates registered. Advances **D-P30.2-2**, **D-P30.2a-1**. | — |
| 147 | `P31.6__access-edges-and-hosted-link-materialization.md` | 31 | ticket | **C** | **[semantic `DEEPEN.2`]** access edges as claims; hosted replay from evidence; edges + accountability > 0. Closes **D-P30.2-2**. | — |
| 148 | `P31.7__claim-re-sightings.md` | 31 | ticket | **C** | **[semantic `DEEPEN.3`]** re-sightings linked; dating basis + storage budget ADR. Closes **D-P30.2a-2**. | — |
| 149 | `P31.8__predicate-registry-legislation-portal.md` | 31 | ticket | **C** | **[semantic `DEEPEN.4`]** remaining predicate families + genre directness; hosted re-resolution. Closes **D-P30.2a-1**. | — |
| 150 | `P31.9__negative-space-peer-classes.md` | 31 | ticket | **C** | **[semantic `DEEPEN.5`]** declared peer classes; hosted negative space materialized. Closes **D-P30.2-1**. | — |
| 151 | `P31.10__camera-site-review-surface.md` | 31 | ticket | **C** | **[semantic `DEEPEN.6`]** curation review over PG `review_item`/`review_decision` + campaign sampler. Advances **D-P30.2b-1**. | — |
| 152 | `P31.11__review-decisions-into-clustering.md` | 31 | ticket | **C** | **[semantic `DEEPEN.7`]** human decisions feed camera-site clustering; within-source duplicate-target exception. Closes **D-P30.2b-3**; advances **D-P30.2b-1**. | — |
| 153 | `P31.12__accountability-breadth-federal-uk.md` | 31 | ticket | **C** | **[semantic `BREADTH.1`]** gao/dhs_oig/dhs_fusion/uk_scc wired + hosted land + rights apply. Advances **D-R7.3-BREADTH**. | — |
| 154 | `P31.13__accountability-breadth-ccops-fema.md` | 31 | ticket | **C** | **[semantic `BREADTH.2`]** ccops ×3 + fema_hsgp wired + hosted land; 68 probe-error retries (successes registered `ingestion_permitted=false`). Closes **D-R7.3-BREADTH**, **D-SOURCES.12-1**. | — |
| 155 | `P31.14__presentation-analytics-from-export.md` | 31 | ticket | **C** | **[semantic `SURFACE.1`]** export-emitted analytics; getters fail loud. Closes **D-P30.3-3**, **D-P27.5-1**. | — |
| 156 | `P31.15__vector-tiles-and-compression.md` | 31 | ticket | **C** | **[semantic `SURFACE.2`]** z0–z14 per-compartment tiles, compression, island on tiles. Closes **D-P30.3-2**. | basemap choice |
| 157 | `P31.16__rematerialize-reexport-republish.md` | 31 | ticket | **C** | **[semantic `SURFACE.3`]** re-materialize all, national re-export, republish, probe. | **HG-11** |
| 158 | `P31.17__human-review-campaign.md` | 31 | human | **A** | **[marker `HUMAN-H4`]** curators adjudicate a stratified camera-site sample via P31.10. Precondition of **D-R6.1-EVAL**. | human |
| 159 | `P31.18__resolution-eval-from-first-principles.md` | 31 | skeleton | **C** | **[semantic `EVAL.1`]** skeleton — rules v3 + human holdout + re-derived balance. **D-R6.1-EVAL**, **D-P30.2b-2**, **D-P30.2b-1**. | after row 158 |
| 160 | `P31.19__round9-closeout.md` | 31 | ticket | **C** | **[semantic `CLOSE.1`]** leak-check policy, sweep, capstone, `projectStatus`. Closes **D-P30.4-4**. | — |
```

**Plan-extensions line (draft):**

```markdown
- **<date> — ROUND 9 (post-launch engineering follow-ups) seeded** by a planning session off the P30.4 tip
  (`devin/p30-4-post-launch-closeout` @ `0a715fc`) on branch `devin/round9-seed`, from the design branch
  `devin/round9-planning` (`docs/build/reports/ROUND9_FOLLOWUPS_DESIGN.md`) + its 19 draft contracts
  (`docs/build/reports/round9-drafts/`, moved verbatim into `docs/tickets/`, only `base_branch` finalized). New rows
  **142–160** (`P31.1…P31.19`). Wave A ratified <date>; Wave B ratifies after Wave A lands. Every OPEN
  engineering deferral from the P30.4 sweep maps to a row (design §1). ADRs minted by owning tickets from
  ADR-108. `nextTicket: P31.1`; `round: 9`; `chainTip: devin/round9-seed`. No product code, no gate ticked, no
  source flip, no spine write, no merge/tag/push-main — planning session only.
```

**LEDGER changes at seed (draft, not applied):** `nextTicket: P31.1`; `round: 9`; `chainTip: devin/round9-seed`;
`projectStatus` unchanged (`IN-PROGRESS`); a PHASE LOG entry. **DEFERRALS changes at seed:** each row in §1 gets an
appended note "scheduled → P31.x (Round 9 seed)". The rows stay OPEN until their tickets close them.

## 9. Phase-4 adversarial review of this split (recorded)

- **Fragmented decisions:** the sink (P31.3 owns), run identity (P31.2 owns), org identity (P31.5 owns),
  human-decision semantics (P31.11 owns) and the republish (P31.16 owns) each have one owner (§3). Procurement
  predicate registration was **moved into P31.5** rather than P31.8, because "is `buyer` a text or an entity-ref
  predicate?" is the same decision as emitting it.
- **Overflow risk:** P31.3 (race + batching + measurement) and P31.5 (sink + emitters + registry) are the largest.
  Both carry an explicit split seam (P31.3: guard | batching; P31.5: sink/registry | emitters). P31.13 carries
  the D-SOURCES.12-1 retries as a droppable tail.
- **Merged to avoid over-factoring:** reconnect + search (one file, one deploy); ccops + fema (both non-accountability
  class wiring with the same hosted recipe); rules-v3 folded into the EVAL skeleton (both need a *fresh* holdout,
  and a human one serves both). The tradeoff: D-P30.2b-2 now waits on humans. It stays a known over-merge risk at
  tier 3g's measured 0.986, which is acceptable.
- **Orphan seams:** the surface-visible halves of P31.2/P31.6/P31.8/P31.9/P31.11–P31.15 are owned by P31.16. The
  `sig-api` reconnect production proof is owned by P31.1 (backend kill) and re-observed by P31.16 (scale-down
  restart).
- **Ordering:** no forward references; P31.17 is a pause (RETURN PASS), never a `blockedOn`.
- **Fresh-context critique applied (2026-09-24).** A separate read-only reviewer found two blockers and a set of
  fixes, all applied to the drafts: (1) the ingest jobs keep captures on the container's own disk, so "replay from
  evidence" / "skip captured pages" may have nothing to read on hosted → P31.4 measures and fixes capture persistence,
  and P31.6 names the asserting-replay decision and never re-fetches quota APIs; (2) `scheduled-ops.sh` deploys jobs on
  `:latest` → P31.4 owns a digest-based roll of all jobs. Also: the D-P30.2b-1 closure moved to P31.18 (a deferral row
  has no "halves"); the catalog retries register successes `ingestion_permitted=false` (no rights basis) instead of
  wiring them; the wave-tail count was dropped (already closed); P31.3's pass condition was made satisfiable
  append-only and its guard extended to the second entity writer; P31.5 mints `organization` entities, not
  `deployment`; P31.1 builds the trigram index `CONCURRENTLY` and times the heavy routes; P31.2 dates
  `last_content_change` from inserting runs only; P31.7 is barred from batch-05 until the 10-10 outcome is recorded;
  P31.9 projects disk bytes; P31.10 takes its sample size from Q11; split seams added to P31.4/P31.11; P31.16 rolls
  `sig-web` and states when its restart proof applies; P31.12/13 run hosted lands as Cloud Run jobs only; P31.19's
  redaction option is limited to non-append-only files.
- **Revisable:** `orchestrate-build` may split or merge at run time and must write the change back to the manifest
  and the ledger.

## 10. Operator ratification — 2026-09-24

*(Requested as "§7 Operator ratification"; numbered §10 because §7–§9 of this draft already exist. Appended; the
sections above are the draft as written, except the §3 plan-table rows for P31.7/P31.17/P31.18 and the status note.)*

**Operator's words, verbatim:** *"I think I approve all recommendations but I'm not sure we should prematurely
optimize the repeat-sighting storage since overall data size is small and won't grow much"* and, on human review:
*"perhaps we defer human review and use a high powered model like Opus 5.5 to LLM-annotate a sample as a first pass"*.

| Q | answer (2026-09-24) | where it lands |
|---|---|---|
| 1 | **Wave A (P31.1–P31.4) seeded now**; Wave B (P31.5–P31.16) ratified in principle, seeded after Wave A lands. | manifest rows 142–145; LEDGER `nextTicket: P31.1`, `round: 9` |
| 2 | **Approved.** Roll a NEW `sig-api` image by pinned digest, keeping the current digest `sha256:cc6801119e82a72767f03f5955a36419e22f202166fed7b4d9259a25aec7fac8` for rollback; **one** deliberate `pg_terminate_backend` of `sig-api`'s own connection is approved to prove reconnect on hosted. | P31.1 Gate status |
| 3 | **No standalone republish** in P31.2 — wait for the single P31.16 republish; "not recorded" stays the honest display until then. | P31.2 Gate status |
| 4 | Switch the 10-10 OSM replay job (`sig-sched-camreg-batch-05`) to the new sink **only if the hosted bounded test is green by 2026-10-08**; otherwise keep the current pinned image as the baseline. | P31.4 Gate status |
| 5 | **CHANGED by operator:** record **EVERY** re-sighting — no cadence-window cap (data is small). P31.7 keeps a **measurement of actual row growth vs the Cloud SQL disk** so the assumption is checked, not assumed. *(The operator cited a 10 GB disk; ADR-107 records 15 GB PD-SSD — P31.7 reads the provisioned size live and reports headroom against both.)* | `round9-drafts/P31.7__claim-re-sightings.md` (edited) |
| 6 | Engineering may decide the 3 duplicate-entity pairs with evidence — **no per-pair operator sign-off**. | P31.3 Gate status |
| 7 | Leak check: **(a)** narrow the check's scope to code + config (ADR-R9-LEAKSCOPE in P31.19). | P31.19 draft (Wave B tail) |
| 8 | **No basemap** for now ((a): plain background + real z0–z14 tiles). | P31.15 draft |
| 9 | **Retire** the combined `/map/points.json` once per-compartment tiles serve the map (ends ACCEPTED deviation R8-1). | P31.15 draft |
| 10 | P31.16 republish **pauses for HG-11** operator sign-off (first org-to-org edges + accountability links go public). | P31.16 draft |
| 11 | **CHANGED by operator:** human review **deferred**. P31.17 becomes an **LLM annotation first pass using `claude-opus-5-5`** over a stratified sample (~400 camera-site pairs), reporting agreement with the existing labels (the P30.2b seed/verifier labels and the earlier LLM run). It is **NOT** human ground truth: it does **not** close D-R6.1-EVAL, and the public PROVISIONAL disclosure stays. Human review + P31.18 (eval re-derivation from human labels) move to **Round 10**. | `round9-drafts/P31.17__llm-annotation-first-pass.md` (rewritten; replaces `P31.17__human-review-campaign.md`); `P31.18` draft marked "moved to Round 10" |
| 12 | Backlog home: keep **BL-055/056/057**; no new BL row. | no BACKLOG change |

**Consequences recorded at the seed (planning session, `devin/round9-seed`):**

- Round 9 is now **18 rows** (142–160 as proposed, minus P31.18): 142–145 Wave A (seeded), 146–157 Wave B, 158 P31.17
  (now an engineering LLM-annotation ticket, Lane C, not a human marker), 160 P31.19 closeout. Row 159 is left unused
  (row numbers are stable indices; the Round-10 human campaign + eval get new rows at their seed).
- Caveat noted for P31.17: the existing verifier seed labels (`agent:claude-opus-5-5@sig-maintainer-seed`) and the
  earlier LLM run (`llm:claude-opus-5-5@camera-rules-v1-blind`) in `camera_site_gold.json` are the **same model** as the
  first pass, so agreement measures consistency, not correctness — it is not ADR-105's "stronger adjudicator" trigger.
- To reconcile at the **Wave-B seed** (drafts not edited now, by scope): P31.10 (sample size "from Q11" → the ~400-pair
  LLM sample; "doing the reviewing (P31.17, humans)" → Round 10), P31.11 (its RETURN-PASS re-run "after P31.17" → after
  the Round-10 human campaign), P31.19 (`projectStatus` evaluation must treat the moved P31.18 + human campaign as
  Round-10 rows, not Round-9 gate-pending ones), and the §2/§3 dependency sketch (`P31.10 ─► P31.11 ─► P31.17 (human) ─►
  P31.18`).

## 11. Wave B seed 2026-09-25

*(Appended at the Wave-B seed; §0–§10 are kept as written. Where they disagree with this section, this section and the
seeded contracts in `docs/tickets/` win.)*

**Operator answers (LEDGER § GATE DECISIONS 2026-09-25, "Round 9 Wave B ratification + ops decisions"):** (1) **"Seed Wave
B, run it"** — rows 146–157 seeded and driven; P31.16 still pauses for HG-11. (2) **"Drop P31.17"** — an Opus-5.5 first
pass would mostly measure self-consistency (the existing gold labels are Opus-made); the eval stays PROVISIONAL and
D-R6.1-EVAL stays OPEN until a real human review in Round 10. (3) Second reconnect drill run → **D-P30.4-1 DONE**. (4)
`sig-api` min-instances=1 (same digest `sha256:21bb9526…`).

**What was seeded** (branch `devin/round9-waveb-seed`, off the P31.4 tip `9152118`):

| row | ticket | base branch | gate |
|---|---|---|---|
| 146 | P31.5 `entity-ref-claims-procurement` | `devin/round9-waveb-seed` | — |
| 147 | P31.6 `access-edges-and-hosted-link-materialization` | `devin/p31-5-entity-ref-claims-procurement` | — |
| 148 | P31.7 `claim-re-sightings` | `devin/p31-6-access-edges-and-hosted-link-materialization` | — (Q5 answered) |
| 149 | P31.8 `predicate-registry-legislation-portal` | `devin/p31-7-claim-re-sightings` | — |
| 150 | P31.9 `negative-space-peer-classes` | `devin/p31-8-predicate-registry-legislation-portal` | — |
| 151 | P31.10 `camera-site-review-surface` | `devin/p31-9-negative-space-peer-classes` | — (re-scoped) |
| 152 | P31.11 `review-decisions-into-clustering` | `devin/p31-10-camera-site-review-surface` | — (re-scoped) |
| 153 | P31.12 `accountability-breadth-federal-uk` | `devin/p31-11-review-decisions-into-clustering` | — |
| 154 | P31.13 `accountability-breadth-ccops-fema` | `devin/p31-12-accountability-breadth-federal-uk` | — |
| 155 | P31.14 `presentation-analytics-from-export` | `devin/p31-13-accountability-breadth-ccops-fema` | — |
| 156 | P31.15 `vector-tiles-and-compression` | `devin/p31-14-presentation-analytics-from-export` | Q8/Q9 answered (no pause) |
| 157 | P31.16 `rematerialize-reexport-republish` | `devin/p31-15-vector-tiles-and-compression` | **HG-11** (pause) |
| ~~158~~ | ~~P31.17 `llm-annotation-first-pass`~~ | — | **DROPPED** (operator 2026-09-25) |
| ~~159~~ | ~~P31.18 `resolution-eval-from-first-principles`~~ | — | **Round 10** |
| 160 | P31.19 `round9-closeout` | `devin/p31-16-rematerialize-reexport-republish` | — (Q7 = (a)) |

**Re-scopes (nothing in Round 9 depends on a review campaign).**

- **P31.10** is standalone **tooling** for the Round-10 human review: a PG-backed loopback review surface + a seeded
  stratified sampler (the ~400-pair Q11 design is its default for Round 10). It runs no campaign, needs no decisions,
  and claims no eval closure; D-R6.1-EVAL and D-P30.2b-1 stay OPEN.
- **P31.11** consumes whatever `review_decision` rows exist — on hosted, expected **zero** camera-site decisions — and
  must be correct (and tested) with zero; it lands the within-source duplicate-layer fix (D-P30.2b-3) in full. The
  "re-run after P31.17 decisions" RETURN PASS is gone; D-P30.2b-1's closure is a Round-10 item.
- **P31.19** implements Q7 = (a) only, and carries D-R6.1-EVAL (+ the human halves of D-P30.2b-1/-2) as **owned Round-10
  items** with owner + landing in its sweep — never as a blocker it pretends to close. P31.17 counts as consciously
  skipped; P31.18 as moved.
- The §3 dependency line `P31.10 ─► P31.11 ─► P31.17 (human) ─► P31.18` becomes `P31.10 ─► P31.11` in Round 9, with
  `human review campaign ─► P31.18` in Round 10.

**Wave-A reality folded into the contracts** (re-checked against the landed code at `9152118`):

- **Sink (ADR-110).** The object seam exists (`object_resolver` → `EntityRef`, written as `object_type='entity_ref'`, not
  `'entity'`); `_DEFAULT_ENTITY_TYPE` is subject-only; partner schemes must join `GUARDED_SCHEMES` with their backfill.
  `content_digest` does not cover the resolver output, so P31.5 emits a distinct record per entity-ref claim. The
  duplicate hook exists (`on_duplicates` / `DuplicateBatch`) but no production caller wires it. Its `capture_by_digest`
  holds the sink's **synthetic per-(source, genre, run)** `evidence_capture` row, so P31.7's uncapped re-sightings are
  one link per claim per execution, unless its ADR uses `ingest_run_capture` digests.
- **Streaming + resume + captures (ADR-111).** Per-capture flush; `ingest_run_capture` marks; a resumed execution skips
  flushed targets. Hosted captures persist to the restricted GCS bucket only **since the 2026-09-25 job roll**, so
  P31.6's replay-from-evidence covers only sources that have run since then.
- **Jobs (ADR-111 D6).** Every job is digest-pinned (`sig-ops roll-jobs`, `pin_image_digest`). All 76 `sig-api` jobs,
  including `sig-sched-camreg-batch-05`, run `sha256:feff986c…`. P31.7 rolls with `--exclude` for batch-05 until the
  2026-10-10 outcome is recorded (D-P31.4-1). New-source jobs (P31.12/13) are `sig-ops scheduled-ingest` jobs with the
  capture store, created without re-applying `scheduled-ops.sh` over the existing jobs.
- **Runs (ADR-109).** Per-execution `ingest_run` + append-only `ingest_run_completion`. P31.16 also runs the
  `run-completions` step, because the freshness page is its public half (P31.2 did not republish, Q3).
- **API.** `sig-api` is pooled on `sha256:21bb9526…` with min-instances=1, and D-P30.4-1 is DONE. P31.16's
  instance-restart observation is therefore a regression check, not a first proof. Neither drill restarted the Cloud SQL
  instance.
- **`sig-web`** has no repo-owned deploy path (it was hand-made in P30.3). P31.15 adds one; P31.16 rolls it and retires
  `/map/points.json`, which closes R8-1.
- **Disk.** P31.7 and P31.9 read the provisioned disk live (15 GB per ADR-107) instead of assuming it.
- `ops/Dockerfile` installs against `uv.lock` (P31.2). The next free ADR is **ADR-112**.
