-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:rights_decisions from pg

BEGIN;

DROP TRIGGER IF EXISTS rights_decision_immutable ON rights_decision;
DROP FUNCTION IF EXISTS rights_decision_immutable();
DROP TABLE IF EXISTS rights_decision;

COMMIT;
