-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:rights_sources_lineage on pg
SELECT rights_id FROM rights_record WHERE false;
SELECT source_id FROM source_registry WHERE false;
SELECT run_id FROM ingest_run WHERE false;
