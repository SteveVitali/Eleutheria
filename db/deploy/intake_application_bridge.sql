-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:intake_application_bridge to pg
--
-- P32.16a (§55.5 SIG-FIND-008; S4 research §8; ADR-135's stated follow-up): the
-- authorized bridge that applies a *reviewed, explicitly approved* intake
-- proposal through the CANONICAL S1 disposition path — never a parallel write.
--
--   * `correct` is the §16.6/SIG-STORE-020 correction pair in one transaction:
--     close the old claim's sys_period (the only update the append-only trigger
--     permits) and INSERT a new claim carrying revises_claim + correction_reason
--     + asserted_by (the approving curator) + the bridge's own ingest_run.
--   * `annotate` asserts a non-superseding claim on the same subject.
--   * `suppress`/`delete` record ONE publication_disposition row each via the
--     P32.5 append-only registry (withhold|restrict / withdraw — the strongest
--     non-destructive gate; byte-level deletion stays the separately gated
--     two-person process, never this bridge).
--   * `refuse` never reaches the bridge — denial writes nothing canonical.
--
-- `intake.application` is the APPLIED RECEIPT: one append-only row per applied
-- operation, keyed by a caller-supplied-or-derived UNIQUE `operation_id`, so a
-- crash-then-retry reconciles to exactly one canonical record and one stable
-- receipt. The row is inserted in the SAME transaction as the canonical write
-- and the `applied` lifecycle event — an apply either lands all three or none.
--
-- `sig_intake_bridge` is the third least-privilege intake role and the ONLY
-- role the event writer guard now admits `applied`/`published` under. It holds
-- the sealed-reader membership (`sig_read_sealed`) so FORCED claim RLS admits
-- the target row at whatever sensitivity tier the report cited — the apply
-- re-checks the tier before writing. Its canonical grants are narrow:
-- INSERT claim, UPDATE (sys_period) ONLY on claim
-- (close prior belief — the append-only trigger still guards every other
-- column), claim_evidence SELECT+INSERT (re-bind the same captures to the new
-- assertion), entity/entity_identifier/entity_identity_key writes for the
-- guarded curator-entity mint, ingest_run + publication_disposition writes,
-- and read-only vocabulary/rights/target validation selects. NO review_decision,
-- capture, extraction or intake-payload write; the receiver and reviewer roles
-- gain nothing.
--
-- `sig.curator.handle` joins the entity-identity guard (ADR-110): the approving
-- curator's pseudonymous handle resolves to exactly ONE person entity (§11.3 —
-- "SIG's own attributable curators") used as `asserted_by`, stable across
-- applications and safe under concurrent applies. The change ships the scheme
-- backfill (0 rows on a fresh spine — no such identifiers predate the role).

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_intake_bridge') THEN
    CREATE ROLE sig_intake_bridge NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. The applied-receipt table. Append-only; every committed row IS a
--    completed apply (it commits atomically with the canonical writes + the
--    `applied` event), so there is no mutable status column.
-- ---------------------------------------------------------------------------
CREATE TABLE intake.application (
  application_id  uuid PRIMARY KEY DEFAULT uuidv7(),      -- the applied receipt id
  report_id       uuid NOT NULL REFERENCES intake.report,
  operation_id    text NOT NULL UNIQUE
                  CHECK (operation_id ~ '^[A-Za-z0-9_:.=-]{8,128}$'),
  approval_seq    bigint NOT NULL REFERENCES intake.event(event_seq),
  proposal_seq    bigint NOT NULL REFERENCES intake.event(event_seq),
  outcome         text NOT NULL CHECK (outcome IN ('correct','annotate','suppress','delete')),
  approved_by     text NOT NULL,       -- the disposition_approved actor (the authority)
  applied_by      text NOT NULL,       -- the curator handle that ran the apply
  target_kind     text NOT NULL
                  CHECK (target_kind IN ('claim','entity','artifact','release_artifact')),
  target_claim_id uuid REFERENCES claim(claim_id),          -- the disputed/old claim
  target_id       text,                -- the disposition target for non-claim kinds
  result_claim_id uuid REFERENCES claim(claim_id),          -- the new correction/annotation
  disposition_id  uuid REFERENCES publication_disposition(disposition_id),
  ingest_run_id   uuid REFERENCES ingest_run(run_id),       -- the bridge's own run row
  detail          jsonb NOT NULL DEFAULT '{}'::jsonb,       -- proposal fingerprint echo
  applied_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
  -- ONE canonical record per application, shaped by outcome.
  CHECK (
    (outcome IN ('correct','annotate')
       AND result_claim_id IS NOT NULL AND disposition_id IS NULL)
    OR (outcome IN ('suppress','delete')
       AND disposition_id IS NOT NULL AND result_claim_id IS NULL)
  )
);

CREATE INDEX intake_application_report_idx ON intake.application (report_id);

COMMENT ON TABLE intake.application IS
  'P32.16a (SIG-FIND-008): the applied-receipt log — ONE append-only row per '
  'applied moderation operation, UNIQUE(operation_id) as the exactly-once '
  'barrier. Inserted in the same transaction as the canonical write (§16.6 '
  'correction claim pair or publication_disposition row) and the applied '
  'lifecycle event: a crash before commit leaves nothing; a crash after commit '
  'reconciles by operation_id lookup — never a blind re-apply.';

-- Append-only like every other intake audit row.
CREATE TRIGGER intake_application_immutable
  BEFORE UPDATE OR DELETE ON intake.application
  FOR EACH ROW EXECUTE FUNCTION intake.append_only_guard();

-- ---------------------------------------------------------------------------
-- 2. Writer guard: applied/published belong to the bridge role now (every
--    other rule byte-identical to P32.16 — receiver `received`, reviewer rest).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION intake.event_writer_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$
DECLARE
  session_role text := current_setting('role', true);
BEGIN
  IF NEW.event IN ('applied','published') THEN
    IF COALESCE(session_role,'') <> 'sig_intake_bridge' THEN
      RAISE EXCEPTION
        'intake event % is reserved for the authorized bridge role sig_intake_bridge (SIG-FIND-008)',
        NEW.event
        USING ERRCODE = 'insufficient_privilege';
    END IF;
  ELSIF NEW.event = 'received' THEN
    IF COALESCE(session_role,'') <> 'sig_intake_receiver'
       OR NEW.actor <> 'sig-intake-receiver' THEN
      RAISE EXCEPTION
        'the intake received event may be appended only under SET ROLE sig_intake_receiver with actor sig-intake-receiver'
        USING ERRCODE = 'insufficient_privilege';
    END IF;
  ELSE
    IF COALESCE(session_role,'') <> 'sig_intake_reviewer' THEN
      RAISE EXCEPTION
        'intake event % requires SET ROLE sig_intake_reviewer',
        NEW.event
        USING ERRCODE = 'insufficient_privilege';
    END IF;
  END IF;
  RETURN NEW;
END $$;

COMMENT ON FUNCTION intake.event_writer_guard() IS
  'P32.16/ADR-135 as extended by P32.16a: `received` only under '
  'sig_intake_receiver; reviewer events only under sig_intake_reviewer; '
  '`applied`/`published` only under the P32.16a bridge role sig_intake_bridge.';

-- ---------------------------------------------------------------------------
-- 3. The curator-handle identity scheme joins the guard (ADR-110 (d)): a new
--    guarded scheme ships with the backfill of its existing identifiers —
--    none exist on a spine that never had the bridge, so this keys 0 rows.
-- ---------------------------------------------------------------------------
INSERT INTO entity_identity_key (scheme, value, entity_id, backfilled)
SELECT DISTINCT ON (ei.value) ei.scheme, ei.value, ei.entity_id, true
  FROM entity_identifier ei
  JOIN entity e ON e.entity_id = ei.entity_id
 WHERE ei.scheme = 'sig.curator.handle'
 ORDER BY ei.value, e.created_at, ei.entity_id;

-- ---------------------------------------------------------------------------
-- 4. Grants — least privilege for the bridge; nothing new for any other role.
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA intake TO sig_intake_bridge;

-- Intake-side: read report/receipt/event/application (+ the coarse projection
-- for receipts), append the two bridge lifecycle events, mint the receipt row.
GRANT SELECT ON intake.report, intake.receipt, intake.event, intake.application
  TO sig_intake_bridge;
GRANT SELECT ON intake.report_public TO sig_intake_bridge;
GRANT INSERT ON intake.event, intake.application TO sig_intake_bridge;

-- Canonical reads for validation only (claim/evidence/disposition state,
-- predicate/value contract, rights compartment of the disputed claim), plus
-- SELECT on the tables a claim/claim_evidence INSERT references — Postgres
-- requires REFERENCES (or SELECT) on the parent side of every FK it checks:
-- evidence_capture, extraction and vocab_evidence_role for the re-bound
-- claim_evidence rows, entity/ingest_run/rights_record/vocab_predicate for the
-- new claim row itself.
GRANT SELECT ON claim, claim_evidence, entity, entity_identifier,
              entity_identity_key, publication_disposition, ingest_run,
              vocab_predicate, rights_record, evidence_capture, extraction,
              vocab_evidence_role, vocab_entity_type
  TO sig_intake_bridge;

-- Canonical writes, as narrow as the schema allows: the correction INSERT +
-- the prior-belief close (ONE guarded column — every other claim column stays
-- trigger-immutable), re-binding the same captures to the new assertion, the
-- guarded curator mint, the bridge's own ingest_run rows, and the disposition
-- registry. NO review_decision / capture / extraction / source writes and no
-- UPDATE/DELETE anywhere.
GRANT INSERT ON claim TO sig_intake_bridge;
GRANT UPDATE (sys_period) ON claim TO sig_intake_bridge;
GRANT INSERT ON claim_evidence TO sig_intake_bridge;
GRANT INSERT ON entity, entity_identifier, entity_identity_key
  TO sig_intake_bridge;
GRANT INSERT ON ingest_run TO sig_intake_bridge;
GRANT INSERT ON publication_disposition TO sig_intake_bridge;
GRANT USAGE ON SEQUENCE publication_disposition_disposition_seq_seq TO sig_intake_bridge;

-- Row-level security on `claim` (access_control.sql) is FORCED: the permissive
-- base policy names the sig_read_* ladder + sig_ingest, and the restrictive
-- SELECT ceiling resolves through sig_visible_max_tier(). A correction can
-- target a claim of ANY sensitivity tier the report cited, and the apply
-- re-checks the row's current tier before it writes — so the bridge reads the
-- whole ladder like the other internal writer (ingest) does, through the same
-- permissive policies. Membership is read-scope only: the write surface stays
-- the narrow GRANT set above.
GRANT sig_read_sealed TO sig_intake_bridge;

COMMIT;
