-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:camera_site_resolution from pg

BEGIN;

REVOKE INSERT, SELECT ON review_item FROM sig_materialize;
DROP TABLE IF EXISTS camera_site_match;
DROP TABLE IF EXISTS camera_site_run;

COMMIT;
