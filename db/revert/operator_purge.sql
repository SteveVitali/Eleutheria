-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:operator_purge from pg
--
-- Removes the purge function, both record tables (their triggers ride the DROP
-- TABLE), the watermark facet row and the operator-held role. The claim spine's
-- append-only enforcement is untouched and stays armed.

BEGIN;

DROP FUNCTION IF EXISTS sig_purge_claims(uuid[], text, text, text);
DROP TABLE IF EXISTS purge_audit;
DROP TABLE IF EXISTS purge_tombstone;
DROP FUNCTION IF EXISTS purge_tombstone_immutable();
DROP FUNCTION IF EXISTS purge_audit_immutable();
DELETE FROM spine_watermark WHERE facet = 'purge_tombstone';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sig_purge_operator') THEN
    DROP ROLE sig_purge_operator;
  END IF;
END $$;

COMMIT;
