-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:entity_identifier_scheme_value from pg
-- Non-transactional, like the deploy: DROP INDEX CONCURRENTLY cannot run in a
-- transaction block.

DROP INDEX CONCURRENTLY IF EXISTS entity_identifier_scheme_value_idx;
