-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:coverage_exclusion_disclosure to pg
-- P35.20a / ED-42 / F-134 (PKG-10 a-half): the per-predicate reconciliation ratio's
-- numerator now counts only subjects with a resolved, publishable, non-conflicted
-- value (tier-0 + currently-valid + publication-eligible winning claim, numerator ⊆
-- denominator BY JOIN — never the dropped min(resolved, claimed) clamp that let
-- "232,625 of 232,625" read true while 5,290 were withheld as conflicting). The
-- excluded classes are DISCLOSED beside the ratio, so a coverage ratio can never
-- read N of N while records are excluded (SIG-METRIC-009/003/008).
--
-- Two additive concerns, both nullable + back-compatible (SIG-STORE-042), so any
-- pre-existing coverage_record row (exclusions IS NULL, a hand-written ratio) is
-- unaffected:
--
-- 1. ``exclusions jsonb`` — the per-class disclosure carried ON the measured row:
--    ``{"conflicted": n, "withheld": n, "non_publishable": n, "filtered": n}``.
--    Exclusion counts are part of the measurement (append-only like the row),
--    not a sentence the surface composes.
--
-- 2. ``coverage_ratio_exclusions_sum`` CHECK — the GQ-16-shape invariant pinned at
--    the DB for reconciliation-ratio rows that DISCLOSE: when ``exclusions`` is
--    carried, numerator + not_evaluable (the excluded total) MUST equal the
--    evaluable denominator. A disclosing ratio whose excluded count does not
--    reconstruct its denominator cannot be inserted, not even by hand. A legacy
--    pre-P35.20a row (``exclusions IS NULL``) is untouched — the deploy never
--    re-adjudicates history written under the old semantics.

BEGIN;

ALTER TABLE coverage_record
  ADD COLUMN exclusions jsonb;  -- per-class exclusion counts beside a ratio

ALTER TABLE coverage_record
  ADD CONSTRAINT coverage_ratio_exclusions_sum CHECK (
    exclusions IS NULL
    OR numerator + COALESCE(not_evaluable, 0) = denominator
  );

COMMIT;
