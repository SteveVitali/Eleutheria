-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:entity_typing_mobility_check on pg
--
-- P35.14b. Asserts the three landed pieces: the append-only decision table
-- (shape + idempotency barrier + keyed-identity FK + immutability trigger +
-- watermark facet), the Mobility NOT VALID CHECK (rejects an
-- out-of-vocabulary insert, still NOT VALID), and the widened
-- quarantine-reason CHECK.

BEGIN;

-- 1. Table shape: every column the writer lands must exist.
SELECT decision_seq, scheme, value, entity_id, prior_type, entity_type,
       map_version, decided_by, basis, decided_at
  FROM entity_type_decision
 WHERE false;

-- The idempotency barrier: UNIQUE (scheme, value, entity_type, map_version).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'entity_type_decision'::regclass AND contype = 'u'
       AND pg_get_constraintdef(oid)
           LIKE 'UNIQUE (scheme, value, entity_type, map_version)%'
  ) THEN 1 ELSE 0 END);

-- The keyed-identity FK into entity_identity_key (a decision names an
-- existing keyed identity; it never mints or re-keys).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'entity_type_decision'::regclass AND contype = 'f'
       AND confrelid = 'entity_identity_key'::regclass
  ) THEN 1 ELSE 0 END);

-- The prior_type <> entity_type guard.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'entity_type_decision'::regclass AND contype = 'c'
       AND pg_get_constraintdef(oid) LIKE '%entity_type <> prior_type%'
  ) THEN 1 ELSE 0 END);

-- The immutability trigger is armed.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'entity_type_decision'
       AND t.tgname = 'entity_type_decision_immutable'
       AND NOT t.tgisinternal
  ) THEN 1 ELSE 0 END);

-- The effective-type view resolves (decision wins, else the column).
SELECT entity_id, entity_type FROM entity_current_type WHERE false;

-- The watermark facet is registered with all three triggers.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM spine_watermark WHERE facet = 'entity_type_decision'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'entity_type_decision'
       AND t.tgname LIKE 'spine_watermark_%'
  ) = 3 THEN 1 ELSE 0 END);

-- 2. The Mobility CHECK exists and is still NOT VALID (validating existing
--    rows is the named follow-up, not this change).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'physical_asset'::regclass
       AND conname = 'physical_asset_mobility_vocab'
       AND convalidated = false
  ) THEN 1 ELSE 0 END);

-- It rejects an out-of-vocabulary insert on a new write (SIG-GEO-005's
-- 'mobile' case) — the exception block rolls the probe inserts back inside
-- this DO block (the verify itself is ROLLBACK'd regardless).
DO $$
DECLARE
  probe uuid;
BEGIN
  INSERT INTO entity (entity_id, entity_type) VALUES (uuidv7(), 'physical_asset')
    RETURNING entity_id INTO probe;
  INSERT INTO physical_asset (entity_id, mobility) VALUES (probe, 'mobile');
  RAISE EXCEPTION 'physical_asset_mobility_vocab did not reject out-of-vocabulary mobility';
EXCEPTION
  WHEN check_violation THEN NULL;  -- the CHECK fired — expected
END $$;

-- Every in-vocabulary value passes the same CHECK (the rows stand until
-- ROLLBACK — the verify deletes nothing anyway).
DO $$
DECLARE
  probe uuid;
  member text;
BEGIN
  FOREACH member IN ARRAY
    ARRAY['fixed','redeployable','vehicle_mounted','airborne','handheld','unknown']
  LOOP
    INSERT INTO entity (entity_id, entity_type) VALUES (uuidv7(), 'physical_asset')
      RETURNING entity_id INTO probe;
    INSERT INTO physical_asset (entity_id, mobility) VALUES (probe, member);
  END LOOP;
END $$;

-- 3. The quarantine-reason CHECK admits unknown_subject_scheme (the insert
--    standing to ROLLBACK is the proof — the table's own immutability
--    trigger refuses a delete probe by design). The probe mints a minimal
--    ingest_run first: run_id is a NOT NULL FK on the quarantine table.
DO $$
DECLARE
  probe_run uuid;
BEGIN
  INSERT INTO ingest_run
    (connector_name, connector_version, code_commit, ruleset_version,
     vocab_version, parameters, environment, input_digests)
  VALUES
    ('verify', '0', 'verify-probe-p35.14b', '0', '0',
     '{}'::jsonb, '{}'::jsonb, '{}')
    RETURNING run_id INTO probe_run;
  INSERT INTO assertion_quarantine
    (run_id, reason, connector_name, payload, payload_digest)
  VALUES
    (probe_run, 'unknown_subject_scheme', 'verify', '{}'::jsonb,
     'verify-probe-p35.14b');
END $$;

ROLLBACK;
