# ADR-114 — Claim re-sightings on the spine, and latest-capture dating (the design's ADR-R9-RESIGHT)

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.7 (`docs/tickets/P31.7__claim-re-sightings.md`) — Round 9 `DEEPEN.3`.
- **Date:** 2026-10-02
- **Related:** §16 (claim/evidence), §28 (`latest_observation_wins`), ADR-104 §4 (capture-time dating — the
  interim basis this ADR revises), ADR-110 Decision 6(a) (the `on_duplicates` hook seam), ADR-111 (per-capture
  flush, `is_replay`, digest-pinned job images), ADR-113 (the asserting replay that deliberately does NOT wire
  this hook), ADR-107 (`sig-pg` at `db-custom-1-3840`, **15 GB PD-SSD** — the disk the budget is measured
  against; the operator's ratification cites a stricter 10 GB comparison point, also reported). Deferral
  **D-P30.2a-2** (closed here). The **ratified operator decision** (Q5, 2026-09-24, LEDGER § GATE DECISIONS):
  record **every** re-sighting — no cadence-window cap, no digest-changed filter — and *measure* the real
  growth against the live Cloud SQL disk rather than assume it.

## Context

- **A re-asserted claim was invisible.** `PgClaimSink` dedupes on `content_digest`
  (`ON CONFLICT DO NOTHING`); a claim the spine already held returned before its `claim_evidence` link, so
  every claim was linked to exactly one capture — its first sighting. A source that restated a value every
  run left no mark of it; an A → B → A revert kept A's original date, so `latest_observation_wins` preferred
  the stale B.
- **ADR-104's capture-dating was written before the links existed.** Its `min(ec2.retrieved_at)` choice was
  explicit ("stable as later captures accrue … this must be revisited once re-sightings are linked"). P31.7
  links them, so the interim basis is now wrong for the reverting-value case it was conservative about.
- **A changed input needs a supersession write path.** The resolver's SIG-RECON-020 `input_digest` covers a
  claim's `observed_at`; once re-sightings move an undated claim's date, re-materializing produces a *new*
  digest — and `resolution_materialize` already says a changed input "yields a superseding decision (close
  the prior `sys_period` first)", enforced in the database by `resolution_no_overlap`. Until now inputs
  never changed, so the close step was never implemented; `sig_materialize` deliberately holds no UPDATE.

## Decision

1. **Every live re-sighting is recorded, uncapped (ratified option a).** The production `on_duplicates`
   hook is `db.claim_sink.record_resightings`, wired by `connectors.sinks.make_claim_sink('pg')` (a caller
   may still override). For each chunk's already-present claims it appends `claim_evidence` rows
   (`role='establishes'`) linking the stored claim to this execution's synthetic per-`(source, genre, run)`
   `evidence_capture` — inside the chunk transaction, one `INSERT … unnest … ON CONFLICT
   (claim_id, capture_id, role) DO NOTHING` statement, reusing `_LINK_EVIDENCE`. **Granularity:** one link
   per (claim, capture, execution) — at most one per claim per execution per genre (the Wave-A capture
   granularity, per the ticket; per-page OCFL captures are not linked). **Idempotency:** a resumed
   execution reuses its run's capture, so a re-flushed capture links +0; the PK forbids a duplicate link.
   `claim_evidence` stays insert-only — no UPDATE/DELETE is introduced anywhere.
2. **Replay runs record no sightings.** `DuplicateBatch` carries `replay` (the sink's `is_replay`), and the
   hook returns without writing on it: a replay re-reads stored bytes (ADR-113) — it is not the source
   re-asserting the value, and its synthetic capture's `retrieved_at` is the replay execution time, which
   must never masquerade as a fresh sighting. (`replay_ingest` also builds its `PgClaimSink` directly and
   does not wire the hook — belt and braces.)
3. **Dating basis: the LATEST sighting.** An undated claim is dated from `max(claim_evidence.captures
   .retrieved_at)` — the most recent time the source was seen asserting the value — so a restated or
   reverting value resolves on its freshest evidence. The basis label changes to
   **`capture_retrieved_at_latest`** (fired as `SIG-RECON-008:observed_at=capture_retrieved_at_latest` in
   `rules_fired`): a new name keeps pre- and post-P31.7 envelopes distinguishable instead of silently
   redefining `capture_retrieved_at`. `observation_time`, `CAPTURE_TIME_JOIN`, the `PgReadStore` reads and
   `read_claim_groups` all share the constant; the reader-side lateral only runs for undated claims.
4. **Resolution supersession is implemented, append-only.** New sqitch change `resolution_supersede`:
   `close_superseded_resolutions(uuid[], text[], text[])` is a **SECURITY DEFINER** function owned by the
   schema owner, granted EXECUTE to `sig_materialize` only (PUBLIC revoked). Before a flush batch inserts,
   it closes the `sys_period` of every live `decided_by='auto'` row for the batch's `(subject, predicate)`
   pairs whose `input_digest` differs — §16.4's sanctioned supersession: the row stays as history
   (readable under `as_of` belief queries), never edited in place, never deleted. A live **non-auto**
   decision is never closed: the function reports the pair `blocked` and the materializer counts it
   `skipped_pinned` instead of crashing on the exclusion constraint. `MaterializeSummary` gains
   `superseded` + `skipped_pinned`; `read_materialized_resolutions` returns only `upper_inf(sys_period)`
   rows (current decisions). Least privilege holds: `sig_materialize` still has no UPDATE on `resolution`.
5. **Storage growth is measured, not assumed (the Q5 condition).** `claim_evidence` row count,
   `pg_total_relation_size` (table + indexes), whole-DB size and the Cloud SQL disk (`gcloud sql instances
   describe` `settings.dataDiskSizeGb`) are read **live** before and after the first rolled cadence runs;
   bytes-per-link and a 12-month projection at the observed cadence mix (OSM monthly included) are recorded
   in `docs/build/runs/P31.7.md` and the hosted report. Threshold below. No cap is applied pre-emptively;
   no historical re-sightings are backfilled (they were never captured — honest history starts at deploy).
6. **Rollout** follows ADR-111: build → digest-pin → `sig-ops roll-jobs --image <digest>
   --exclude sig-sched-camreg-batch-05` (batch-05 stays on `sha256:feff986c…` until the 2026-10-10 replay
   outcome is recorded, D-P31.4-1), after a bounded link-volume measurement per run; resolution is re-run
   via `materialize.sh --apply run resolution` as a Cloud Run job, re-run +0 on unchanged input, deltas
   recorded; previous digests preserved for rollback.

## Consequences

- **Restated values date correctly.** A value seen again is fresher than one not seen; A → B → A resolves
  to A (proven on real PG in `tests/db/test_resightings.py`).
- **`input_digest` churn is real and expected.** Each re-sighting that lands before a materialize run
  changes the group's digest → one closed + one new resolution row per changed group per materialization.
  The hosted delta is recorded; the churn is bounded by `(groups whose sources re-asserted undated claims
  since the last run)`, and it is honest: the decision's input really did change.
- **`claim_evidence` grows by ≤ (#duplicate claims × executions) — uncapped but measured.** Bounded by
  claims-per-source × runs-per-cadence-window; the 12-month projection below quantifies it.
- **The resolver read path costs one `max()` aggregate** over a claim's evidence set (indexed by PK) —
  bounded, and only evaluated for undated claims.
- **The API's compute-on-read envelopes move in step** — `PgReadStore` shares `CAPTURE_TIME_JOIN`, so the
  ADR-092 fallback posture and the materialized decisions date identically.

## Alternatives considered

- **Earliest capture (keep ADR-104's `min`).** Rejected: it is stable but wrong for the reverting-value
  case that motivated the ticket — A → B → A keeps A's first date and `latest_observation_wins` prefers B.
- **First-seen date + separately exposed last-seen.** Rejected: `latest_observation_wins` must compare the
  last sighting to resolve A → B → A, so the digest churn is identical either way; splitting the fields
  adds a second time axis for no decision benefit. The evidence set itself carries every sighting — the
  first-seen date remains derivable as `min(retrieved_at)` for any consumer that wants it.
- **Cadence-window cap (option b) / digest-changed filter (option c).** Rejected by the operator
  (Q5 ratification): premature optimization; measure instead. The revisit trigger names the threshold that
  would re-open a cap.
- **Skip replay runs by leaving the hook unwired in `replay_ingest`.** Kept (the replay path builds its
  sink directly), but the hook itself also checks `batch.replay` so the invariant survives a future wiring
  change — a replay sighting would corrupt dating by stamping stored bytes with replay time.

## Revisit trigger

Revisit — in a new ADR — when any of:

(a) **the storage budget is crossed** — the measured projection is recorded in `docs/build/runs/P31.7.md`
    and `docs/build/reports/p31.7-hosted/`; the named threshold is **projected `claim_evidence` growth
    exceeding 50% of the provisioned `sig-pg` disk within 12 months** (reported against the live
    `settings.dataDiskSizeGb` — 15 GB per ADR-107 — *and* the operator's stricter 10 GB comparison). If the
    projection crosses it, the follow-up is a re-sighting cap (cadence window or digest-changed filter),
    filed as a deferral — the cap is never applied pre-emptively;
(b) **the churn is worse than measured** — `resolution` supersession volume per materialize run exceeds
    the recorded delta by an order of magnitude, or the exclusion-constraint workload degrades the
    materializer's runtime budget;
(c) **per-page capture granularity is wanted** — if a consumer needs which *page* of a multi-capture
    source re-asserted a claim, link `ingest_run_capture` marks instead of the synthetic run capture;
    additive, never a rewrite of this path;
(d) **a consumer needs first-seen** — expose `min(retrieved_at)` alongside rather than reverting the basis;
(e) **a replay semantics change** — if asserting replays ever represent fresh source contact (they do not
    today), the `batch.replay` exclusion is the single place that policy lives.
