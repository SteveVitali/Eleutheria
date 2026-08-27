-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:rights_sources_lineage from pg
BEGIN;
DROP TABLE IF EXISTS ingest_run;
DROP TABLE IF EXISTS source_registry;
DROP TABLE IF EXISTS rights_record;
COMMIT;
