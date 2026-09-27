# ADR-123 — One shared bitemporal occurrence-selection contract (P32.4)

- Date: 2026-10-11
- Status: accepted (engineering; offline-only — no live fetch, publication or gate action)
- Ticket: P32.4 (Round 10 / S1, row 164; requirement SIG-TRUST-005; closes `D-P31.1-1`)
- Base: `348764c` (the P32.3 tip `devin/p32-3-roles-counts-and-organization-identity`, PR #158)

## Context

Every reader invented its own "latest":

1. **The undated-claim fallback diverged.** The API and the reconcile materializer dated an
   undated claim from `max(retrieved_at)` over *every* `claim_evidence` link — no belief bound,
   no role filter — while the camera-site reader picked `DISTINCT ON … ORDER BY claim_id DESC`
   (a claim id is not a clock) and the resolver kept its own candidate semantics. A→B→A
   re-sightings therefore selected differently depending on which surface read them.
2. **Belief was not bound uniformly.** A later capture, replay link, or correction could reach
   backward and re-date an already-served read: evidence bindings carried no knowledge bound in
   the readers, so a "frozen" past-belief output could silently change.
3. **Materialization completion had no per-execution record.** `camera_site_run` is keyed by the
   full input digest — a re-run over an unchanged spine reuses the row (+0 by design) — so an
   A→B→A reversion that landed on an older digest left no record that a *new execution*
   completed; readers could stay on B.
4. **`D-P31.1-1`.** `/v1/contradiction` and `/v1/task` counted six spine relations per request
   (~10 s, ~48 s median under 8-way concurrency) only to compute a freshness watermark — a
   bounded, correctly-invalidated freshness source did not exist.

## Decision

**`temporal-read/1` — one contract, three carriers.** `db.occurrences` is the owned module
(`CONTRACT_VERSION = "temporal-read/1"`); the pure conformance model, the shared SQL fragments
(`occurrence_lateral`, `claim_source_cte`), and the sqitch `eligible_occurrence` function are
three renderings of *one* selection rule, kept identical by fixture/PG parity tests
(`tests/db/test_temporal_contract.py`):

1. **Eligible occurrence.** A claim's occurrence is its latest *eligible* establishing
   `claim_evidence` binding: `role='establishes'` only (a corroborating or contradicting link
   never re-dates the claim) with `bound_at <= belief` — the *same* belief instant that bounds
   the assertion's `sys_period` (`sys_period @> belief`). `belief=NULL` means current knowledge.
   Order is `retrieved_at DESC NULLS LAST, capture_id ASC` — a row id breaks an exact-time tie
   for determinism but is never used *as* time.
2. **Dating with a labelled fallback.** A dated claim keeps its asserted `observed_at`
   (`basis="claim"`); an undated claim is dated from the selected occurrence's `retrieved_at`
   (`basis="capture_retrieved_at_latest"` — an inference, labelled in `rules_fired`, ADR-104's
   documented fallback updated to the latest sighting by ADR-R9-RESIGHT); a claim with neither
   stays at the 1970 placeholder — historical, never silently current. The *ordering* instant is
   carried at full precision (`observed_instant`) alongside the date-precision display value, so
   same-day A→B→A re-sightings order correctly while date-only source values stay date-only.
   Because the ordering instant is decision input, it is part of `Claim.digest_token()` — a
   same-day re-sighting mints a new resolution (SIG-RECON-020).
3. **Per-lineage concurrent candidates.** Envelope candidates are the latest eligible claim
   *per source lineage* (`lineage_candidates`): two independent sources disagreeing at one
   instant remain concurrent candidates (visible contradiction, §3.1); a superseded same-source
   assertion stays visible as labelled history in `observations`/`considered_claim_ids` without
   posing as a current candidate.
4. **Atomic coordinate pairs.** A lat/lon pair is a point only when the two selected claims were
   established in *one common capture* (`_PAIR_BINDINGS_SQL` intersects eligible binding sets);
   no common sighting → no point (the axis claims remain cited, the pair never mixes
   occurrences across captures).
5. **Wired into every consumer.** `reconcile.materialize.read_claim_groups` (belief-pinned
   lateral), `reconcile.resolve.Claim` (`observed_instant` + occurrence refs), `api.store_pg`
   (`_public_claim_groups`, per-subject and per-claim reads — one belief instant bounds claims
   and bindings), `resolution.camera_sites_pg` (`_RECORDS_SQL` orders by the contract instant,
   `claim_id` last-resort), and `exports.shaping`/`exports.spine_export` (the `claim_source`
   CTE + `lineage_candidates`, belief pinned to the same instant for both the assertion
   `sys_period` and the CTE `bound_at`).
6. **Per-execution completion refs.** `camera_site_execution(execution_id, run_key,
   completed_at, input_count, summary)` is append-only: every materialization execution appends
   one row — including an A→B→A reversion that reuses an older `camera_site_run` — and
   `read_resolved_site_runs` selects the run of the *latest completed execution*, never the
   latest distinct run. `execution_id` is the idempotency key (retry appends +0). Existing runs
   were backfilled one execution row each at deploy.
7. **`D-P31.1-1` — a trigger-maintained watermark, not a scan.** `spine_watermark` holds one row
   per watched relation facet (`row_count`, `closed_count`, `latest_instant`, monotone `bump`);
   statement-level `SECURITY DEFINER` triggers bump the facet on `INSERT`, on the one permitted
   `UPDATE` (a `sys_period` close adjusts `closed_count` only — no new row), and on `TRUNCATE`.
   Readers do an O(27 rows) probe (`db.occurrences.spine_watermark`) — bounded by construction,
   snapshot-consistent, and never stale (a watched write changes the key in the same
   transaction). The watched set is the superset of every relation the cached compute-on-read
   paths read plus every materialization relation: a new claim, a correction, or a completed
   materialization invalidates exactly the affected cached state. A spine deployed before this
   change falls back to the legacy six-count read.

## Alternatives considered

- **A per-reader `latest` with documented semantics** — rejected: that *is* the defect;
  divergence is not tolerable when evidence integrity is the point (SIG-TRUST-005).
- **`RESERVED`/`SERIALIZABLE` reads or a global revision counter** — rejected: heavier than the
  problem; the belief bound inside the queries is cheaper and works on pooled connections.
- **Keying `camera_site_run` by execution instead of input digest** — rejected: it would destroy
  the deliberate +0 idempotency on unchanged inputs; the execution/completion split keeps both
  guarantees.
- **A TTL or approximate watermark for `D-P31.1-1`** — rejected: a stale-read risk traded for
  latency is the wrong direction for evidence; the trigger-maintained table is exact *and*
  bounded.
- **A per-claim materialized "latest occurrence" table** — rejected for now: the lateral
  `DISTINCT ON` reads are bounded by the new partial index
  (`claim_evidence(claim_id) WHERE role='establishes'` + `evidence_capture(retrieved_at)`); a
  denormalized occurrence table is the next lever if the P31-scale plan budget is exceeded.

## Consequences

- `Claim.digest_token()` now includes `observed_instant`: the committed
  `l3_rebuild_sample.json` was repinned (deliberate — a same-day re-sighting must move the
  digest).
- `ShapingClaim`/`ValueObservation` carry `observed_basis` + occurrence refs; envelope
  `n_sources`/`distinct_values` count candidates, `observations`/`considered` keep all history.
- `spine_watermark` is a new always-maintained table (81 statement-level triggers across 27
  facets); each watched write costs one `UPDATE` per statement, not per row.
- `exports` gains a workspace dependency on `sig-db` (the shared contract module).

## Revisit trigger

Revisit when a reader needs a different occurrence definition (extend the contract version and
all three carriers together — a private "latest" is the defect this ADR closes), when the
lateral `DISTINCT ON` reads exceed the serving budget on the measured fixture (materialize the
per-claim occurrence into a maintained table), when a new relation joins the cached-read set
(add a `spine_watermark` facet + triggers in the same change), or when PG's transition-table or
trigger semantics change the per-event delta rules (the INSERT/UPDATE/TRUNCATE split in
`spine_watermark_touch`).
