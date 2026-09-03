-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:graph_annotations on pg
SELECT contradiction_id FROM contradiction WHERE false;
SELECT coverage_id FROM coverage_record WHERE false;
SELECT task_id FROM research_task WHERE false;
