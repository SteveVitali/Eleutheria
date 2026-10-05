-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:recovery_apply to pg
--
-- P32.22 (§55 SIG-TRUST-008; S1 research §6; ADR-141): the authorized
-- application half of the bounded integrity recovery whose planning half is
-- P32.6's `recovery-plan/1`. The plan is dry-run-only by contract — every
-- proposed write is an INSERT against the append-only spine tables. This
-- change ships the two things an apply needs that a plan does not:
--
--   * `recovery_application` — the APPLIED RECEIPT / resume marker: ONE
--     append-only row per executed plan action, keyed by the planner's own
--     deterministic `action_digest` (UNIQUE = the exactly-once barrier, the
--     same shape `intake.application.operation_id` gives the P32.16a bridge).
--     The row commits atomically with the action's canonical write: a crash
--     before commit leaves nothing; a crash after commit lets a restart
--     reconcile to exactly one receipt — feeding recorded digests back into
--     `recovery-plan` yields a +0 re-plan, so interruption and restart can
--     never produce a duplicate repair.
--   * `sig_recovery` — the least-privilege applier role (mirrors
--     sig_intake_bridge's grant shape): INSERT claim + UPDATE(sys_period)-ONLY
--     claim close (the §16.6 correction pair's sole permitted update), INSERT
--     claim_evidence (typed re-bindings and the repair's re-bound captures),
--     INSERT publication_disposition (the ONLY access mechanism), INSERT
--     ingest_run (the apply's own recorded run), the guarded adjudicator-entity
--     mint (entity/entity_identifier/entity_identity_key), and validation
--     SELECTs + sig_read_sealed read-scope for FORCED claim RLS. NO capture/
--     extraction/blob/source writes, no UPDATE/DELETE anywhere, no OCFL or
--     network access — missing bytes can never trigger a refetch by privilege.
--
-- Scope the apply actually executes is bounded twice: the operator-selected
-- action subset (batch/kind/claim) AND the plan's recorded batch ceilings
-- (10 000 assertions / 250 MiB distinct bytes / one worker), re-checked by the
-- applier before any write.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_recovery') THEN
    CREATE ROLE sig_recovery NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. The applied-receipt table. Append-only; every committed row IS an
--    executed action (it commits atomically with the canonical write), so
--    there is no mutable status column. `outcome` records what the apply
--    actually did — `applied` (new canonical rows), `conflict_existing` (the
--    action's row already existed: claim_evidence's (claim_id,capture_id,role)
--    PK deduplicated an already-bound capture — recorded, never fabricated as
--    a new row) — so the receipt is honest about +0 cases.
-- ---------------------------------------------------------------------------
CREATE TABLE recovery_application (
  application_id  uuid PRIMARY KEY DEFAULT uuidv7(),   -- the applied receipt id
  action_digest   text NOT NULL UNIQUE                 -- the plan action identity
                  CHECK (action_digest ~ '^[0-9a-f]{64}$'),
  execution_id    text NOT NULL                        -- the bounded apply execution
                  CHECK (execution_id ~ '^[A-Za-z0-9_:.=-]{4,128}$'),
  batch_id        text,                                -- the plan's batch partition
  kind            text NOT NULL
                  CHECK (kind IN
                    ('bind_verified_capture','repair_claim','record_disposition')),
  claim_id        uuid NOT NULL REFERENCES claim(claim_id),  -- the action's claim
  outcome         text NOT NULL
                  CHECK (outcome IN ('applied','conflict_existing')),
  result_claim_id uuid REFERENCES claim(claim_id),     -- repair: the NEW claim
  disposition_id  uuid REFERENCES publication_disposition(disposition_id),
  binding_key     text,                                -- bind: claim_id|capture_id|role
  plan_digest         text,                            -- the reconciled plan digest
  audit_input_digest text,                             -- the audited population digest
  authority           text NOT NULL,                   -- the operator authorization
  ingest_run_id       uuid REFERENCES ingest_run(run_id), -- the apply's own run row
  detail              jsonb NOT NULL DEFAULT '{}'::jsonb,   -- provenance + outcome echo
  applied_at          timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX recovery_application_claim_idx ON recovery_application (claim_id);
CREATE INDEX recovery_application_execution_idx ON recovery_application (execution_id);

COMMENT ON TABLE recovery_application IS
  'P32.22 (SIG-TRUST-008, ADR-141): the bounded recovery applied-receipt log — '
  'ONE append-only row per executed recovery-plan action, UNIQUE(action_digest) '
  'as the exactly-once barrier. Inserted in the same transaction as the '
  'action''s canonical write (claim_evidence rebind, §16.6 correction pair, or '
  'publication_disposition row): a crash before commit leaves nothing; a crash '
  'after commit reconciles by action_digest — never a blind re-apply, and a '
  're-plan over the recorded digests proposes +0.';

-- Append-only like every other spine audit row (the shared guard shape).
CREATE FUNCTION recovery_application_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'recovery_application rows are immutable (append-only, SIG-TRUST-008); '
    'a new receipt is appended, never edited';
END $$ LANGUAGE plpgsql;

CREATE TRIGGER recovery_application_immutable
  BEFORE UPDATE OR DELETE ON recovery_application
  FOR EACH ROW EXECUTE FUNCTION recovery_application_immutable();

-- ---------------------------------------------------------------------------
-- 2. Grants — least privilege for the applier; nothing new for any other role.
-- ---------------------------------------------------------------------------

-- The receipt itself.
GRANT SELECT, INSERT ON recovery_application TO sig_recovery;

-- Canonical reads for validation only: the action's claim + its current
-- bindings, the capture occurrence the bind names, the disposition registry's
-- current state, the adjudicator-entity guard, and every parent table a claim/
-- claim_evidence/disposition INSERT references (Postgres requires SELECT-or-
-- REFERENCES on the parent side of each checked FK).
GRANT SELECT ON claim, claim_evidence, entity, entity_identifier,
              entity_identity_key, publication_disposition, ingest_run,
              ingest_run_capture, vocab_predicate, vocab_normalization,
              rights_record, evidence_capture, evidence_artifact, extraction,
              vocab_evidence_role, vocab_entity_type, vocab_object_type,
              vocab_source_reliability, vocab_claim_directness,
              vocab_artifact_integrity
  TO sig_recovery;

-- Canonical writes, as narrow as the schema allows: the §16.6 correction
-- INSERT + the prior-belief close (ONE guarded column — every other claim
-- column stays trigger-immutable), typed claim_evidence bindings, the guarded
-- adjudicator-entity mint, the apply's own ingest_run rows, and the
-- disposition registry. NO capture/extraction/blob/source writes, no
-- review_decision writes, and no UPDATE/DELETE anywhere.
GRANT INSERT ON claim TO sig_recovery;
GRANT UPDATE (sys_period) ON claim TO sig_recovery;
GRANT INSERT ON claim_evidence TO sig_recovery;
GRANT INSERT ON entity, entity_identifier, entity_identity_key TO sig_recovery;
GRANT INSERT ON ingest_run TO sig_recovery;
GRANT INSERT ON publication_disposition TO sig_recovery;
GRANT USAGE ON SEQUENCE publication_disposition_disposition_seq_seq TO sig_recovery;

-- Row-level security on `claim` is FORCED: a bounded repair can target a
-- claim at any sensitivity tier the audit cited, so the role reads through
-- the same sealed-reader membership the other internal writers hold.
-- Membership is read-scope only; the write surface stays the narrow set above.
GRANT sig_read_sealed TO sig_recovery;

-- The deploying login (the schema owner) may SET ROLE to it — the same shape
-- materialize_role uses; operator-selected applier sessions get membership by
-- a separate operator grant, never by this migration granting broadly.
DO $$ BEGIN
  EXECUTE format('GRANT sig_recovery TO %I', current_user);
END $$;

COMMIT;
