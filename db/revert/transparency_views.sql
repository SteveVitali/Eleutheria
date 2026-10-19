-- SPDX-License-Identifier: Apache-2.0
-- Revert eleutheria-claims:transparency_views from pg

BEGIN;

DROP VIEW IF EXISTS v_transparency_capture;
DROP VIEW IF EXISTS v_transparency_run;

COMMIT;
