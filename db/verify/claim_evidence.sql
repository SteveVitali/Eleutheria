-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim_evidence on pg
SELECT claim_id, capture_id, role FROM claim_evidence WHERE false;
SELECT claim_id, qualifier_id FROM claim_qualifier WHERE false;
