-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:graph_annotations from pg
BEGIN;
DROP TABLE IF EXISTS research_task;
DROP TABLE IF EXISTS coverage_record;
DROP TABLE IF EXISTS contradiction;
COMMIT;
