-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:subject_rekey on pg
-- P35.24 / ADR-212: the two tables exist with the immutability triggers, the
-- pin seeds mirror the committed registry version, the decision table
-- enforces its idempotency barrier, and the claim_id index exists.

BEGIN;

-- Tables, triggers and the index exist (division by zero fails when absent).
SELECT 1/COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND tablename = 'subject_key_pin';
SELECT 1/COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND tablename = 'subject_rekey_decision';
SELECT 1/COUNT(*) FROM pg_trigger WHERE tgname = 'subject_key_pin_immutable';
SELECT 1/COUNT(*) FROM pg_trigger WHERE tgname = 'subject_rekey_decision_immutable';
SELECT 1/COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'claim_evidence_claim_idx';

-- Seeds mirror the committed registry (6 pins, all versioned sig.subject-key-pins/1).
DO $$
BEGIN
  IF (SELECT COUNT(*) FROM subject_key_pin) <> 6
     OR EXISTS (SELECT 1 FROM subject_key_pin WHERE registry_version <> 'sig.subject-key-pins/1') THEN
    RAISE EXCEPTION 'subject_key_pin seeds do not mirror sig.subject-key-pins/1';
  END IF;
END
$$;

-- The idempotency barrier: a second identical decision conflicts.
DO $$
DECLARE
  probe_old text;
BEGIN
  SELECT k.value INTO probe_old FROM entity_identity_key k
   WHERE k.scheme = 'sig.connector.subject' LIMIT 1;
  IF probe_old IS NULL THEN
    RETURN;  -- empty spine: barrier semantics still covered by schema tests
  END IF;
  INSERT INTO subject_rekey_decision
    (scheme, old_value, new_value, claims_moved, registry_version, decided_by, basis)
  VALUES
    ('sig.connector.subject', probe_old, probe_old || ':verifyprobe', 0,
     'sig.subject-key-pins/1', 'verify/subject_rekey', 'deploy verify probe');
  BEGIN
    INSERT INTO subject_rekey_decision
      (scheme, old_value, new_value, claims_moved, registry_version, decided_by, basis)
    VALUES
      ('sig.connector.subject', probe_old, probe_old || ':verifyprobe', 0,
       'sig.subject-key-pins/1', 'verify/subject_rekey', 'duplicate probe');
    RAISE EXCEPTION 'subject_rekey_decision uniqueness barrier did not fire';
  EXCEPTION WHEN unique_violation THEN
    NULL;  -- expected
  END;
END
$$;

ROLLBACK;
