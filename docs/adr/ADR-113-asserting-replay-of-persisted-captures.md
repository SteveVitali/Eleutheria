# ADR-113 — Access-edge claims on the spine, and the asserting replay of persisted captures

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.6 (`docs/tickets/P31.6__access-edges-and-hosted-link-materialization.md`) — Round 9 `DEEPEN.2`. This is the design's `asserting re-interpretation` decision the ticket requires as a named ADR.
- **Date:** 2026-09-26
- **Related:** §12.2 (access edges), §29.3 (sharing-edge reconciliation, owned by P08.2), §3.1 (the defining standard), ADR-026 (network-isolated, non-asserting replay — SIG-INGEST-017/018/019), ADR-104 (predicate registration), ADR-110 (the identity guard + the object seam), ADR-111 (restart/resume, `ingest_run_capture` marks, `is_replay`, pinned job images), ADR-112 (partner-organisation entity-refs). Deferral **D-P30.2-2** (closed here), **D-P31.5-1** (advanced here).

## Context

- **The hosted spine holds zero access-edge claims.** `flock_portal` and `audit_structural` emit their
  reconciled §29.3 edges as `record_kind="configured_access_edge"` records — a *non-claim* kind the claim sink
  drops. The relationship is computed and thrown away at the boundary, so the P28.2 edge materializer honestly
  writes 0 `relationship` rows (D-P30.2-2, D-P31.5-1).
- **Replay is deliberately non-asserting** (ADR-026): `connectors.replay.replay` re-derives claims from stored
  captures for verification only — asserting is not in its contract (SIG-INGEST-017/018/019). A connector change
  that adds strictly *more* claim kinds therefore cannot reach the hosted spine through `replay()`.
- **The DB↔OCFL linkage exists** (ADR-111): `ingest_run_capture` marks name the content-addressed digests a
  recorded execution flushed, `ingest_run.is_replay` marks replay executions, and `resume_marks` already excludes
  `is_replay` runs from cadence resume. `PgClaimSink(is_replay=True)` is an existing seam no caller used.
- **A live re-fetch is the wrong tool.** The affected sources include quota-bound APIs; re-fetching to land a
  code change manufactures new *evidence* where only *reinterpretation* was needed, and burns quota the cadence
  budgets (P26.19).

## Decision

1. **Access edges are claims.** Both connectors' `_sharing_edge_rows` emit `record_kind="claim"` rows under the
   newly-registered predicate **`configured_sharing_partner`** (`object_kind: entity_ref`), directed
   `subject → to_org` with the §29.3 qualifiers (`access_kind`, `valid_from_kind`, `corroborated`,
   `observations_count`) travelling as claim attributes folded into the content digest. `value`/`raw_value` carry
   the partner key verbatim (P2). `index_only`, `research_task` and the other non-claim kinds are unchanged.
2. **The partner's identity is deterministic per source.** Eyes on Flock names partners by **portal slug** — an
   identifier, not a name — so the `object_ref` is the partner's own portal key
   (`sig.connector.subject` / `flock_portal:<slug>`): when the partner is itself a portal subject the guard
   resolves the SAME entity its own claims key on (ADR-110). Audit workbooks name partners by free-text
   organisation name → ADR-112's `partner_identity` decides: accepted names get a `sig.org.name` organisation
   ref; refused names stay literal claims the materializer counts `skipped_unmapped`, never fabricated nodes.
   `eff_data_driven` emits `vendor` (the release's stated vendor) and `configured_sharing_partner` for the NVLS
   pooled-lookup flag — the partner is the single dataset-constant vendor, never an enumerated partner list (the
   SIG-INGEST-043c aggregate-only boundary holds) — with ADR-112 `partner_ref_rows` twins.
3. **Asserting reinterpretation is a separate, named path** — `connectors.replay.asserting_replay`, driven by
   `connectors.runner.replay_ingest` and the `sig-ops replay-ingest` verb. It reads ONLY `ingest_run_capture`
   marks (`--run-id` rows, else every non-replay run of the source's logical-run prefix), resolves each distinct
   digest's bytes from the OCFL capture store (the mounted restricted bucket on hosted), and runs the post-capture
   stages under `network_isolated()` — a digest absent from the store is reported `missing_captures`, skipped,
   and **never fetched**. Claims assert through a fresh `is_replay=True` sink whose `logical_run` is a
   replay-scoped key (`<source>@replay-p31-6` or `--replay-key`) and whose `parameters` name the replayed-from
   run ids (`replay_of_runs`). Per capture, the run records a lineage mark under `replay:<target_key>` carrying
   the **original** capture digest, source URI, byte size and retrieval time. Claims the spine already holds
   dedupe to +0 by `content_digest`; only the new claim kinds insert. A second run over the same captures is all
   duplicates — the +0 proof. `replay()` itself is untouched.
4. **Hosted rollout:** replay the sources whose persisted captures exist (e.g. `camreg_osm_surveillance`,
   `dot_511_ut`); a source without stored bytes waits for its next **cadence** run on the rolled image
   (`eyes_on_flock`, `eff_data_driven`) — recorded as a cadence deferral, never an ad-hoc fetch. Then the P28.2
   edge and P28.6 accountability materializers run (`--apply`) and re-run (+0), closing D-P30.2-2. Republication
   of edges/links is out of scope (P31.16 / HG-11).

## Consequences

- **The spine gains the claims it always described.** Eyes on Flock snapshots and audit SharedNetworks rows now
  land `configured_sharing_partner` entity-ref claims; the P28.2 materializer turns them into `relationship`
  rows (`edge_type=access_kind='configured_access'`), and ADR-112's vendor/operator refs let the P28.6
  materializer write `has_vendor`/`procured_under_contract`/`funded_by`/`overseen_by` links.
- **Replays mint subject-side entities once.** A partner slug that never appears as a portal subject still keys
  one `deployment`-typed entity (the connector-subject placeholder, §11.7) — the same entity the partner's own
  portal claims would key on if it ever appears, so the endpoint is stable rather than per-edge.
- **The +0 contract is the safety property.** Because assertion is digest-deduped, a replay run is re-runnable by
  construction; a non-+0 re-run means either the code or the capture set changed and is a finding, not a cleanup.
- **A failed capture is recorded, not retried live.** Per-capture reinterpretation failures land in the report's
  `errors` and the batch continues (earlier captures committed; the re-run converges).
- **Non-claim kinds stay non-claims.** `index_only` / `research_task` still never reach the spine; only the edge
  kind changed (and is gone as a record kind).

## Alternatives considered

- **Make `replay()` assert.** Rejected: replay's guarantee is byte-reproducibility without side effects
  (SIG-INGEST-017/019); assertion is the named, separate decision this ADR records.
- **Re-fetch the sources live to land the new claims.** Rejected: quota-bound APIs are burned for a code change,
  a fetch manufactures new evidence where reinterpretation was needed, and the cadence budgets govern it anyway.
- **Keep `configured_access_edge` as a non-claim record consumed directly by the materializers.** Rejected:
  non-claim records never reach the spine — the relationship layer stays empty, which is exactly the D-P30.2-2 gap.
- **Emit edges as boolean `configured_access_edge` claims.** Rejected: the ticket rules it out — the relationship
  semantics are `configured_sharing_partner` with `access_kind` as a qualifier, not a boolean.

## Revisit trigger

Revisit when any of: (a) a second ticket needs asserting replay — decide whether `replay_ingest` generalises
(per-predicate filtering, dry-run, multi-source sweep); (b) marks predate the P31.4 capture roll — synthetic
`ingest_run_capture` rows without OCFL objects may need a distinct disposition from `missing_captures`;
(c) another connector gains entity-ref predicates that only exist on replay paths; (d) live targets drift from
the stored captures' `source_uri`s so post-capture target resolution fails — decide whether lineage should carry
the original target row; (e) a replay re-run ever reports non-+0 — the dedupe contract is the safety; investigate
before assuming drift.
