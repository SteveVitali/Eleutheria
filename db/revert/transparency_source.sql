-- SPDX-License-Identifier: Apache-2.0
-- Revert sig:transparency_source from pg

BEGIN;

DROP VIEW IF EXISTS v_transparency_source;
DROP VIEW IF EXISTS source_redistribution_current;
DROP TRIGGER IF EXISTS source_redistribution_immutable ON source_redistribution;
DROP FUNCTION IF EXISTS source_redistribution_immutable();
DROP TABLE IF EXISTS source_redistribution;

COMMIT;
