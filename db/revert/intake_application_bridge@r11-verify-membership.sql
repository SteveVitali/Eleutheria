-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:intake_application_bridge from pg
--
-- P32.16a (SIG-FIND-008): drop the applied-receipt table and the bridge role,
-- and restore the P32.16 writer guard that refuses `applied`/`published` for
-- every role. Canonical writes the bridge already committed (correction
-- claims, disposition rows, curator entities, ingest_run rows, intake events)
-- are append-only history and are deliberately NOT touched — a revert removes
-- the bridge's ability to write more, never the record that it did.

BEGIN;

DROP TABLE IF EXISTS intake.application;

CREATE OR REPLACE FUNCTION intake.event_writer_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$
DECLARE
  session_role text := current_setting('role', true);
BEGIN
  IF NEW.event IN ('applied','published') THEN
    RAISE EXCEPTION
      'intake event % is reserved for the P32.16a authorized bridge role (SIG-FIND-008)',
      NEW.event
      USING ERRCODE = 'insufficient_privilege';
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
  'P32.16/ADR-135: `received` only under sig_intake_receiver; reviewer events '
  'only under sig_intake_reviewer; applied/published reserved for the P32.16a '
  'bridge — refused for every current role.';

-- DROP ROLE refuses while the role still holds privileges on other objects,
-- so the narrow grant set + the sealed-reader membership are revoked first.
-- Its committed canonical rows (claims, dispositions, entities, runs, events)
-- are history — untouched.
REVOKE ALL PRIVILEGES ON SCHEMA intake FROM sig_intake_bridge;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA intake FROM sig_intake_bridge;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM sig_intake_bridge;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM sig_intake_bridge;
REVOKE sig_read_sealed FROM sig_intake_bridge;
DROP ROLE IF EXISTS sig_intake_bridge;

COMMIT;
