# ADR-211 — Truthful claim identity: volatile fields leave the digest (P35.22)

- Date: 2026-10-18
- Status: accepted
- Ticket: P35.22 (Round 11 / P35 sub-round 11B, manifest row `R11-L3-CP1` —
  owned finding **F-504** (S1), the re-observation re-minting inflation)
- Base: `r11/P35.20b-freshness-classes-and-map-table-suppression`
- Related: SIG-INGEST-003 (truthful ingest — a re-observed fact binds to its
  claim), SIG-INGEST-004 (dedup parity — the claim-minting-diff harness),
  SIG-EPIS-009 (context only; the `derived_from_claim_ids` binding rule is
  P35.25's), ADR-059 (the `claim_content_digest` idempotency mechanism this
  ADR extends), ADR-R9-RESIGHT (re-sighting `claim_evidence` linkage), ADR-110
  (chunked insert boundary), ADR-136/ADR-141 (the correction/recovery apply
  paths' stored-row digests), CONF-03a (the L3 program label)

## Context

`claim.content_digest` is the claim spine's identity: the
`claim_content_digest_key` partial unique index makes it the dedup key, and a
re-observation of the same fact must re-bind to that claim (a `claim_evidence`
sighting via the `on_duplicates`/`record_resightings` hook), never mint a new
id. Before this change the digest was a whole-record sha256 minus
`claim_id`/`sys_period`/`recorded_at` — so **volatile acquisition detail** sat
in identity: row position (`row_index`/`feature_index`), page/capture URL,
capture digest and fetch time (`capture_digest`/`retrieved_at`/
`retrieved_date`), and upstream record-version counters (`osm_version`,
`release_digest`, …). Any of those churning minted a second claim for an
unchanged fact — F-504 measured ≈2.2 M unresolved `camera_operator` claims and
≈1.9 M `located_in`-family claims, each re-mint falsely counted as an
independent support class.

The defect had a second half: emitter-side minting and sink-side minting were
two copies of the rule (`evidence.ingest_run.canonical_claim_tuple` vs
`db.claim_sink.content_digest`), so they could silently diverge — and the
correction/recovery apply paths used the same `content_digest` for two
different jobs (staleness pinning a stored ROW vs minting a new claim's
identity), which the new scheme must split apart.

## Decision

1. **One identity function, shared.** `evidence/src/evidence/claim_identity.py`
   holds the single digest function (`claim_digest` → `digest_base` → sha256
   over compact sorted-keys JSON). `db.claim_sink.content_digest` delegates to
   it; `connectors.claim_identity_ingest.emitted_claim_digest` calls it;
   `evidence.ingest_run.canonical_claim_tuple` projects with it (so replay
   fingerprints and shadow diffs compare what the sink mints). A divergence
   between emitter-side and sink-side minting is a bug, not a tolerated
   difference — the dedup-parity harness compares them.

2. **Volatile fields never enter identity.** `NEVER_IDENTITY_KEYS` covers the
   named classes — row position (`row_index`, `feature_index`, `page`,
   `position`, …), capture/page URLs (`source_url`, `page_url`,
   `capture_url`, `locator`, `data_file_urls`), capture/binding identity
   (`capture_digest`, `capture_id`, `evidence_id`, `ocfl_*`,
   `ingest_run_id`, `extraction_id`, `assertion_map_*`, `run_id`), fetch time
   (`retrieved_at`, `retrieved_date`, `fetched_at`, `captured_at`,
   `bound_at`, …), upstream version counters (`osm_version`,
   `release_version`, `release_digest`, `source_version`, …) — plus the
   generated/envelope fields (`claim_id`, `sys_period`, `recorded_at`,
   `content_digest`, `record_kind`, `assertion_schema_version`,
   `payload_version`). The projection is recursive at every level of the
   record EXCEPT inside `value_json` (the asserted payload is opaque — a
   `retrieved_at` inside it is content someone asserted), and a nested mapping
   that loses every member to the projection is identical to an absent key.
   Nothing is deleted — every one of those values still lands in
   `claim_evidence`/`evidence_capture` (locator, capture digest,
   `retrieved_at`, OCFL version); only their identity role ends.

3. **The `obs`/`ref` split is registry-read, never guessed.** A predicate's
   identity class derives from its `vocab_predicate` row:
   `is_windowed` OR `resolution_strategy ∈ {interval_union,
   interval_intersection}` (the §28.4 SIG-RECON-011 windowed family — the
   window IS the claim) marks `obs`; the temporal qualifier
   (`valid_from`/`valid_to`/`valid_edtf`/`valid_*_kind`, `valid_period`,
   `observed_at`/`observed_edtf`/`observed_at_kind`/`observed_unknown_reason`)
   stays in identity for `obs` and leaves for `ref`. Two registry facts this
   decision records: (a) `vocab_predicate.is_windowed` exists in the DDL but
   is never seeded by the vocab migrations — the operative signal today is
   `resolution_strategy`, with `is_windowed` honoured for when the registry
   populates it; (b) `latest_observation_wins` and `max_support` are **ref**
   class by design — ADR-R9-RESIGHT's mechanism is that registry connectors
   deliberately keep `observed_at` OFF the claim so resolution reads the
   latest sighting's capture `retrieved_at` from `claim_evidence`; keeping the
   qualifier in identity for them would re-create F-504 (every new fetch date
   mints). The F-504 predicates (`camera_operator`, `camera_latitude`,
   `fixed_asset_location`, …) are exactly those strategies. A `ref` claim's
   differing declared qualifier is preserved on the stored row and the
   evidence binding — it just stops minting ids.

4. **`value_json` canonicalisation.** The stored form the digest consumes is
   canonicalised (`canonical_json` in `assertion_from_record`, after the
   `candidate_identifier` merge): mapping keys recursively sorted, compact
   separators, strings NFC-normalised, integral floats inside the exact-double
   range collapse to ints, `Decimal` renders its shortest exact form,
   datetimes/dates render ISO, and `null` ≡ absent (a `None` member drops).
   Serialised-string `value_json` (a stored row read back) canonicalises
   identically to the dict form, so stored-vs-emitted parity holds.

5. **`payload_version` seals the scheme.** The digest base carries
   `payload_version: "sig.claim-payload/1"`; the new nullable
   `claim.payload_version` column (sqitch change `claim_payload_version`,
   appended to `append_only_guard`) records which normalisation produced each
   row. Any future change to the function is a declared new shape — a new
   version mints distinct digests by construction, never silent drift. The
   migration never recomputes a stored digest: pre-existing rows keep their
   ids and carry `payload_version IS NULL` (CP-1's no-mass-re-mint invariant).
   No new index — `claim_content_digest_key` remains the dedup key.

6. **The legacy whole-row digest survives as a pin, never a mint.**
   `db.claim_sink.legacy_row_digest` reproduces the pre-P35.22 serialisation
   byte-for-byte. It serves the two places that must verify RECORDED
   old-scheme digests: `intake_apply.claim_state_digest` (the
   correction-proposal staleness pin — proposals recorded before this change
   still verify) and `ops.seed_correction` (locates pre-P32.3 seed rows by
   their stored old-scheme digest); the partner-fixture goldens likewise
   verify under it. The apply paths' NEW claim rows mint under the identity
   digest + `payload_version` like every other claim.

7. **The claim-minting-diff harness.** `connectors.claim_identity_ingest`
   defines the `ingest_claim_reconcile.csv` schema (`RECONCILE_FIELDS`:
   `side,row_key,source_id,predicate_id,subject_key,object_key,value_repr,
   content_digest,payload_version`), the row codec, and `diff_minting` —
   joining on the logical row key and reporting `rebound` / `minted` /
   `divergent` per key. `connectors.replay.diff_claim_sets` /
   `replay_fingerprint` are class-aware (registry-loaded
   `predicate_temporal_classes`). The L3 dedup-parity leg is a live probe over
   this schema (queued — P34.44b nightly job); the committed fixture at
   `tests/connectors/fixtures/claim_identity/ingest_claim_reconcile.csv`
   exercises the three verdict classes.

8. **The `/status/` API-basis notice is drafted, not posted.** The disclosure
   is leg L2 — it belongs on `/status/` when the next scheduled runs actually
   mint under the new identity (S6 A-20). The sentence is drafted verbatim
   with its sha256 in the run ledger (`docs/build/runs/P35.22.md`), so the
   live leg ships verbatim-confirmed copy, and the engineering change renders
   nothing public ahead of the behaviour it describes. It is deliberately NOT
   a copy-batch row: batch rows are `data-copy`-bound to rendered elements,
   and binding a pending disclosure on `/status/` now would publish a claim
   about behaviour that has not landed yet — the live leg chooses its carrier
   (notice string or confirmed batch row) at its sitting.

## Deviations and contract-artifact gaps (recorded, not silent)

- **ADR-159 anchor.** The contract cites "ADR-159 (the claim-digest mechanism
  this row modifies)" — the landed ADR-159 is
  *organisation-publication-registry-auto-allow*; the digest mechanism the row
  actually modifies is ADR-059 (`claim_content_digest`). Recorded; the
  contract citation stands as an anchor mismatch, not a design input.
- **`obs`/`ref` is not a literal registry field.** The contract says the class
  is "read from the registry, never guessed" — no `obs`/`ref` column exists;
  the class is derived from the registry's DECLARED fields
  (`resolution_strategy`, `is_windowed`) per decision 3, which is the
  registry-read path the contract intends (the alternative — minting a new
  registry field — would BE a registry change the contract forbids).
- **`ingest_claim_reconcile.csv` under `docs/build/planning/…/data/`** does
  not exist in the repository. The harness defines the schema
  (`RECONCILE_FIELDS`) and the fixture ships under `tests/connectors/
  fixtures/claim_identity/`; the planning-data artifact is an absent contract
  artifact — the schema is now declared and the probe leg writes to it.
- **`value_json` storage normalisation.** Stored `value_json` is now the
  canonical form — e.g. `30.0` stores as `1`-style integer `30`, `null`
  members drop. jsonb already normalises numbers and `null`-membership reads
  identically on every consumer path; recorded because it is a storage-form
  change, not a silent one.

## Consequences

- A re-observation of an unchanged fact re-binds (insert +0, one more
  `claim_evidence` sighting) for every predicate class — F-504's inflation
  stops at the mint boundary; the ≈2.2 M / ≈1.9 M historical duplicates keep
  their ids (P35.23's merge/alias pass consumes this stable identity).
- New claims mint under `payload_version = 'sig.claim-payload/1'`; nothing
  recomputes a stored digest — the additive migration is the only schema
  delta.
- Tests that pinned the inflation (`whole-new-dated-set` expectations in the
  coarse-adapter and data-driven suites) now assert the truthful semantics:
  only genuinely changed facts mint.
- The GQ-02 seam text updates to name what remains (the rotating-source
  capture-replay telemetry leg); GQ-02 itself is still deferred — replay
  telemetry is live work, not landed code.
- Downstream: the `/status/` notice (ST-11, pending) posts at leg L2; the
  dedup-parity report (leg L3) runs `diff_minting` over the probe's CSV.

## Revisit trigger

Revisit when (a) the predicate registry gains a first-class identity-class or
`is_windowed` is populated — the strategy-derived mapping should be re-based
onto it; (b) a predicate's semantics genuinely need the temporal qualifier in
identity but its strategy is non-interval (the class mapping would need
reopening); (c) `payload_version` bumps — a second normalisation shape is a
new ADR; or (d) P35.23's merge/alias pass needs a persisted claim-alias layer
that changes what "the same claim" means for the historical duplicates.
