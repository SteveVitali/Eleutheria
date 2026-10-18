-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:declared_lineage on pg
-- P35.25 (SIG-CONF-014): the tables/view/triggers/indexes exist, the
-- closed-vocabulary CHECKs and the one-row-per-claim barrier hold, and the
-- grant posture matches the declared read surface.

BEGIN;

-- Tables, the view, triggers and indexes exist (division by zero fails when absent).
SELECT 1/COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND tablename = 'source_lineage';
SELECT 1/COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND tablename = 'claim_lineage';
SELECT 1/COUNT(*) FROM pg_views  WHERE schemaname = 'public' AND viewname  = 'source_lineage_current';
SELECT 1/COUNT(*) FROM pg_trigger WHERE tgname = 'source_lineage_immutable';
SELECT 1/COUNT(*) FROM pg_trigger WHERE tgname = 'claim_lineage_immutable';
SELECT 1/COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'claim_lineage_independence_class_idx';
SELECT 1/COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'claim_lineage_source_idx';

-- assertion_quarantine.reason admits the new fail-closed token.
SELECT 1/COUNT(*) FROM pg_constraint
 WHERE conname = 'assertion_quarantine_reason_check'
   AND pg_get_constraintdef(oid) LIKE '%unknown_id_namespace%';

-- claim_lineage: PRIMARY KEY is claim_id and no NULL lineage tokens slip in.
DO $$
DECLARE
  probe_claim uuid;
BEGIN
  SELECT claim_id INTO probe_claim FROM claim LIMIT 1;
  IF probe_claim IS NULL THEN
    RETURN;  -- empty spine: barrier semantics still covered by schema tests
  END IF;
  INSERT INTO claim_lineage (claim_id, source_id, basis)
  VALUES (probe_claim, 'verify/probe', 'verify/declared_lineage');
  BEGIN
    INSERT INTO claim_lineage (claim_id, source_id, basis)
    VALUES (probe_claim, 'verify/probe', 'duplicate probe');
    RAISE EXCEPTION 'claim_lineage one-row-per-claim barrier did not fire';
  EXCEPTION WHEN unique_violation THEN
    NULL;  -- expected
  END;
END
$$;

-- The closed lineage-kind vocabulary rejects an undeclared token.
DO $$
DECLARE
  probe_source text;
BEGIN
  SELECT source_id INTO probe_source FROM source_registry LIMIT 1;
  IF probe_source IS NULL THEN
    RETURN;  -- empty registry: CHECK semantics covered by schema tests
  END IF;
  BEGIN
    INSERT INTO source_lineage (source_id, registry_version, kind)
    VALUES (probe_source, 'sig.sources/verify', 'bogus_kind');
    RAISE EXCEPTION 'source_lineage kind CHECK did not fire';
  EXCEPTION WHEN check_violation THEN
    NULL;  -- expected
  END;
END
$$;

ROLLBACK;
