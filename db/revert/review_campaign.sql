-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:review_campaign from pg

BEGIN;

REVOKE INSERT ON review_decision FROM sig_materialize;
REVOKE SELECT, INSERT ON review_campaign, review_campaign_item FROM sig_materialize;
REVOKE SELECT ON review_campaign, review_campaign_item FROM sig_read_public, sig_export;
DROP TABLE IF EXISTS review_campaign_item;
DROP TABLE IF EXISTS review_campaign;

COMMIT;
