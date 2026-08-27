-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:inference_schema on pg
SELECT derived_id FROM inference.derived_fact WHERE false;
SELECT derived_id FROM inference.derived_geometry WHERE false;
