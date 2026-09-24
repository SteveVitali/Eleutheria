# ADR-104 — Camera-registry predicates in the predicate registry: genres, per-predicate epistemics, an absolute coordinate tolerance, and capture-time dating

- **Status:** Accepted
- **Phase / ticket:** Phase 30 / P30.2a (`docs/tickets/P30.2a__camera-predicate-registry.md`) — Round 8 `GO-LIVE.2a`, inserted 2026-09-24 ("Fix resolution first, then launch"); the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-24
- **Related:** ADR-031 (weight/currency), ADR-092 (compute-on-read fallback), ADR-099 (materialize resolution at scale), ADR-101 (surface reads the materialized graph), ADR-103 (hosted materialization, `sig_materialize`, in-GCP execution); deferrals **D-P30.2-3** (advanced here — §28 half done; entity-dedup half owed to P30.2b), **D-R6.1-EVAL** (first-principles half still OPEN), and **D-P30.2a-1** / **D-P30.2a-2** (opened here); backlog home **BL-057**.

## Context

P30.2 ran the §28 resolution materializer over the whole hosted spine and wrote 8 envelopes for 1,955,004
`(subject, predicate)` groups: **0 resolved sites of 230,267**. The measured cause (committed inventory
`docs/build/reports/p30.2a-hosted/predicate_inventory_before.json`, 2026-09-24T05:48Z) is sharper than
"missing registry rows":

- The hosted spine carries **116** distinct predicates over 2,280,784 tier-0 claims; only **13** have a
  registry row, and only **9 claims** in the whole spine have a directness entry for their evidence genre —
  so only 9 claims could ever be admissible (§28 Phase 1.3).
- The 14 **camera-registry predicates** (`camera_*` ×13 + `external_id`) carry **2,050,954** claims and had
  **no** registry row.
- Their evidence genres are `camera_registry` (2,034,714 claim-evidence links) and `connector_run`
  (236,195) — **neither** is on the registry's nine-genre directness axis, so even a registry row would not
  have made them admissible.
- **2,106,319** tier-0 claims (all camera claims) have `observed_at` NULL, by design: the registry connectors
  keep the per-run retrieval time out of the claim so an unchanged registry does not mint duplicate claims
  (the reason is recorded on each claim, `observed_unknown_reason`). Every reader substituted the
  1970-01-01 placeholder, which makes the claim HISTORICAL (C4 → W1) — so a 2026 registry row would have been
  published as "insufficient evidence" (U1), a false statement.
- Every camera subject is scoped to one source's row (`traffic_camera:<source>:<target>:<ref>`); the
  inventory measured **0** camera groups with claims from more than one source. Multi-claim groups (10,603)
  are the same source re-captured.

## Decision

1. **Two genres join the directness axis** — `camera_registry` and `connector_run` — because they are what
   the hosted spine actually records. Every pre-existing predicate reads **D6** for both: the conservative
   default, identical in effect to the pre-P30.2a exclusion (a missing row was also dropped). Assessing
   those cells is owed (**D-P30.2a-1**), not guessed here.

2. **Register the 14 measured camera-registry predicates** in the ontology source
   (`ontology/vocab/predicates.yaml` → `make gen` → the generated registry + SKOS), never in
   `ontology/generated`. Choices, mirroring the §28.3 table's nearest analogues:

   | predicate | volatility / h | strategy | tolerance | `camera_registry` / `connector_run` |
   |---|---|---|---|---|
   | `camera_latitude`, `camera_longitude` | SLOW / 2y (= fixed asset location) | `latest_observation_wins` (= `fixed_asset_location`) | **absolute 0.0005°** | D2 / D3 |
   | `camera_coordinate_source` | SLOW / 2y (travels with the coordinate) | `latest_observation_wins` | — | D1 / D3 |
   | `camera_external_ref`, `external_id` | IMMUTABLE / ∞ | `authoritative_source_wins` (identity, exact match) | — | D1 / D1 |
   | `camera_operator` | SLOW / 3y (= `asset_operator`) | `max_support` (categorical) | — | D3 / D3 |
   | `camera_jurisdiction` | GLACIAL / 10y (= `organization_jurisdiction`) | `max_support` | — | D3 / D3 |
   | `camera_county` | GLACIAL / 10y | `max_support` | — | D2 / D3 |
   | `camera_roadway`, `camera_name`, `camera_direction`, `camera_type`, `camera_mount` | SLOW / 2y | `max_support` | — | D2 / D3 |
   | `camera_status` | FAST / 6mo (= `operational_state`) | `latest_observation_wins` | — | D2 / D3 |

   **Directness rationale.** A registry row is a first-party report of a listed camera (D2), and the
   authoritative record only of its own key and of how its coordinate was extracted (D1). Operator and
   jurisdiction are attributed per registry *target* (the publisher), not per row, so they are a close proxy
   (D3). `connector_run` is an unclassified connector-pull genre, so every descriptive camera fact is D3 there;
   a record's own identifier is still D1. For the nine legacy genres the rows follow one rule set, not
   case-by-case: contracts/invoices/minutes describe a planned or procured camera (D4 for physical and
   descriptive facts, D6 for status/identifiers); a transparency portal is D3; an OSM node set is a field
   observation (D2 for position/type/mount/facing, D3 otherwise); news is D3; policy/audit-log/vendor pages
   are D6; identifiers and extraction metadata are D6 outside the issuing registry. With R3 sources and I1,
   D1/D2 compose to W3 and D3 to W2 — every registry fact is resolvable (> W1) and none is W4 (dispositive).

3. **An absolute value tolerance, not a new strategy.** The §28.4 strategy set is closed (SIG-RECON-012), and
   SIG-RECON-014 U4 already speaks of "the predicate's tolerance". A registry row MAY now carry
   `value_tolerance: {kind: absolute, value, unit}`; the resolver (`Ruleset.absolute_tolerance`) then
   (a) pools numeric values that agree within it (deterministic single-linkage over sorted values) into one
   candidate that carries its **representative claim's own observed value — never a mean** (averaging repeated
   coordinate observations is how published imprecision is undone, §19.4 / SIG-GEO-009), labelled
   `SIG-RECON-014:value_tolerance`; and (b) replaces the relative U4 spread with the absolute spread taken over
   **every admissible member value**, so a second pool or a long chain whose total span exceeds the tolerance
   is UNRESOLVED (`unresolved_conflict`, both values kept visible). "Every member value" means every weighed
   (W > 0) numeric claim value; a group that mixes numeric and non-numeric values is not pooled (exact
   candidates, as before). 0.0005° is ≈ 55 m north–south (tighter
   east–west away from the equator); latitude and longitude are adjudicated independently. Predicates without
   the field keep exact-value candidates and the relative U4 — no behaviour change.

4. **Undated claims are dated from their earliest capture, and the inference is labelled.** Every reader that
   builds resolver claims (`reconcile.materialize.read_claim_groups`, the `reconcile resolve` CLI, and the three
   `api.store_pg` readers) uses `coalesce(claim.observed_at, min(evidence_capture.retrieved_at))`
   (`CAPTURE_TIME_JOIN` / `observation_time`, the capture's UTC calendar date). Today every claim has exactly
   one capture — `PgClaimSink` returns on a duplicate claim before linking the new capture — so the earliest
   capture is simply the first sighting; `min` is chosen so the date stays stable (no decision churn) if
   re-sightings are ever linked, and conservative (currency ages from the first sighting). A claim dated this way
   carries `observed_at_basis = capture_retrieved_at`, and the resolver fires
   `SIG-RECON-008:observed_at=capture_retrieved_at` into the stored envelope's `rules_fired`. A claim with neither
   date keeps the 1970 placeholder (HISTORICAL) — undated evidence is never treated as current.

5. **Throughput and observability of the write path.** The resolution materializer upserts the three FK vocab
   rows once per distinct `(strategy, rationale, confidence)` triple per pass instead of three round-trips per
   envelope (still `INSERT … ON CONFLICT DO NOTHING`), writes envelopes in batches (one transaction per 1,000
   rows — a failed batch rolls back whole and a re-run completes it), and the CLI reports progress on stderr so
   a long hosted pass shows its ETA. No change to the append-only / `input_digest` idempotency contract.

## Consequences

- The 14 camera predicates become resolvable; the hosted re-materialization (P30.2a run ledger + committed
  `docs/build/reports/p30.2a-hosted/resolution_scale.json`) writes their envelopes append-only, +0 on re-run.
- **What the new numbers mean — and do not.** They are §28 **value resolution within one subject**: for each
  camera record, which of that record's own claims stands for each attribute. Because every hosted camera
  subject is one source's row, nearly every envelope is a single-source, uncontested decision (re-captures are
  superseded, §28 Phase 1.4). They are **not** deduplication: no two records of the same physical camera from
  different sources are merged (entity merges = 0). Cross-source camera-site entity resolution is **P30.2b**.
- **Headline hazard, recorded for P30.2b / P30.3.** `exports.spine_export.resolved_sites_metric` (ADR-101) counts a
  site as "resolved" when *any* materialized envelope on it picked a winning claim, and labels the result
  "resolved sites (deduplicated from observations)". Over the hosted graph after this ticket it would read
  N ≈ M — a count of value decisions presented as dedup. It must **not** be published as a dedup figure; P30.2b's
  deliverable 1 redefines N as post-ER clusters, and P30.3 publishes that measured metric. This ADR deliberately
  does not redefine the metric (that decision is P30.2b's, with its own ADR); the seeded-spine test now pins
  N = M = 2 with this caveat in place.
- **Known limitation of first-sighting dating (D-P30.2a-2).** Because a re-asserted value re-uses its old claim
  and no re-sighting is recorded, (i) a value that reverts (e.g. `camera_status` A → B → A) keeps A's first
  date, so `latest_observation_wins` would pick B although the source now says A; and (ii) a value the source
  re-states every run still ages from its first sighting, so the FAST `camera_status` will eventually hit U5
  (stale) although it was asserted recently. Both need the sink to record re-sightings (a `claim_evidence` link
  per capture); until then the capture-time date is a lower bound on the last assertion, and it is labelled as
  an inference on every envelope that uses it.
- **Latitude and longitude are adjudicated independently.** With one source per subject (today) they always
  come from the same record. Once P30.2b gives a subject several sources, a published point could take its
  latitude from one claim and its longitude from another — a point no source reported. P30.2b must resolve the
  coordinate pair jointly (or pin both axes to one claim) before any multi-source point is published.
- The DB `vocab_predicate` rows for these predicates remain the `PgClaimSink` placeholders (append-only,
  `ON CONFLICT DO NOTHING`); the resolver's source of truth is the generated registry, as before.
- `records_request.external_id` (a crosswalk id on the request's platform) now shares a name with a registered
  predicate and joins the reviewed SIG-STORE-046 allowlist.
- A change to a predicate's registry epistemics is not part of the envelope `input_digest` (only claims +
  ruleset version are, SIG-RECON-020), so a later registry edit does not by itself supersede stored decisions —
  the same limitation every registry row has had since P08.
- The legacy `docs/build/tools/build_predicates.py` bootstrap script is superseded by the YAML source it once
  generated; re-running it would drop these rows, so it must not be re-run.

## Alternatives considered

- **A new `spatial_tolerance` strategy.** Rejected: the §28.4 strategy set is closed and a tolerance is not an
  ordering rule — it is the U4 "predicate's tolerance" plus Phase 2 canonical agreement.
- **Relative tolerance for coordinates** (the existing volatility-class U4). Rejected: 10% of a latitude is
  ~4° — meaningless for position.
- **Average agreeing coordinates.** Rejected: fabricates a value no source reported and defeats §19.4
  coordinate reduction (SIG-GEO-009).
- **Date undated claims from `claim.sys_period` (ingest time) or the latest capture.** Rejected: ingest time is
  SIG's clock, not the source's; the latest capture equals the earliest today (one capture per claim) and, once
  re-sightings are linked, would change every envelope's digest on every re-ingest — that trade-off belongs to
  D-P30.2a-2, which must decide it with the re-sighting change.
- **Assess every existing predicate × the two new genres now.** Deferred (D-P30.2a-1): the non-camera
  connectors' semantics differ per source and belong with their own registry pass; D6 preserves behaviour.

## Revisit trigger

Revisit when any of: (a) P30.2b lands cross-source camera-site ER — identifiers become per-source
multi-valued on a merged entity (the single-cardinality `authoritative_source_wins` choice for `external_id` /
`camera_external_ref` must then be re-decided), latitude/longitude must be resolved as one point, and
`resolved_sites_metric` is redefined; (a2) the claim sink records re-sightings (D-P30.2a-2) — re-decide
earliest vs latest capture dating; (b) measured
cross-source coordinate disagreements show the 0.0005° tolerance splits true duplicates or pools distinct
cameras (dense intersections); (c) a registry connector starts recording a per-row observation time
(`observed_at` no longer NULL — the capture-time fallback stops applying); (d) D-P30.2a-1 assesses the new
genres for the non-camera predicates; (e) §28.3 volatility is recalibrated from observed change rates
(SIG-RECON-009).
