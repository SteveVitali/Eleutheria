-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:coverage_materialize to pg
-- P28.4 / ADR-099 (materialize-at-scale posture). The Appendix C.6 `coverage_record`
-- table (negative space made queryable, §32.1) has existed since P02.1 but has never
-- held a row — the launch posture computed coverage on read (ADR-092/ADR-038). P28.4
-- runs the §32 coverage inference (`inference.coverage`/`denominators`/`completeness`/
-- `freshness`) over the real (resolved) spine and WRITES honest coverage as durable
-- rows, append-only (ADR-005): counted quantities with NAMED denominators, records-
-- derived bounds, per-agency reconciliation ratios, measured survey recall — each
-- carrying its denominator — and negative space (absence_kind). NEVER a total or a
-- population estimate (SIG-METRIC-008/009/010).
--
-- Two additive concerns land here, both nullable + back-compatible (SIG-STORE-042), so
-- any pre-existing / hand-inserted coverage_record row (input_digest IS NULL) is
-- unaffected and excluded from the partial index:
--
-- 1. The idempotency contract the append-only materializer needs, exactly as
--    `resolution_materialize`/`relationship_materialize`/`contradiction_materialize`
--    (ADR-099) and `claim_content_digest` (ADR-059): a nullable `input_digest` (a
--    sha256 over the coverage row's reproducible content) plus a partial UNIQUE index,
--    so the materializer can `INSERT ... ON CONFLICT DO NOTHING` and a re-run over an
--    unchanged spine inserts each coverage record exactly once (+0).
--
-- 2. The §32.2/32.3/32.5 counted-quantity shape. The base coverage_record is the §32.1
--    negative-space shape only; a counted quantity with a named denominator
--    (SIG-METRIC-003/009) needs its numerator/denominator/method/named-denominator
--    columns. A metric row MUST carry a named denominator, and that denominator MUST
--    NOT be a "denominator of reality" (SIG-METRIC-010) — pinned by a CHECK so a
--    population total can never be inserted, not even by hand.

BEGIN;

ALTER TABLE coverage_record
  ADD COLUMN input_digest      text,
  ADD COLUMN metric_method     text,     -- §32.5 CompletenessMethod; NULL for pure negative-space rows
  ADD COLUMN metric_label      text,     -- the human label of the counted quantity
  ADD COLUMN numerator         numeric,  -- the count satisfying the predicate
  ADD COLUMN denominator       numeric,  -- the EVALUABLE population (never reality)
  ADD COLUMN not_evaluable     numeric,  -- excluded for lack of evidence (§32.2)
  ADD COLUMN named_denominator text,     -- the explicit named denominator string
  ADD COLUMN metric_value      numeric;  -- the ratio / recall / share where applicable

-- The no-total invariant, pinned at the DB (SIG-METRIC-009/010): a counted-quantity
-- coverage_record (metric_method IS NOT NULL) MUST carry a named denominator, and that
-- denominator MUST NOT imply the denominator of reality. A population total therefore
-- cannot be inserted at all — the ban is a constraint, not a review-time hope. The
-- forbidden set mirrors `inference.completeness._REALITY_DENOMINATORS`.
ALTER TABLE coverage_record
  ADD CONSTRAINT coverage_metric_named_denominator CHECK (
    metric_method IS NULL
    OR (
      named_denominator IS NOT NULL
      AND btrim(lower(named_denominator)) NOT IN (
        '', 'reality', 'true population', 'all devices', 'total', 'everything', 'the world'
      )
    )
  );

-- A counted quantity cannot beat its evaluable denominator (§32.2, SIG-METRIC-010).
ALTER TABLE coverage_record
  ADD CONSTRAINT coverage_metric_numerator_le_denominator CHECK (
    numerator IS NULL OR denominator IS NULL OR numerator <= denominator
  );

-- The idempotency key: one persisted coverage row per reproducible content. Partial so
-- pre-existing / hand-inserted rows (digest NULL) never collide.
CREATE UNIQUE INDEX coverage_record_input_digest_key
  ON coverage_record (input_digest) WHERE input_digest IS NOT NULL;

COMMIT;
