-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:entity_identifier_value_trgm from pg
-- Non-transactional, like the deploy: DROP INDEX CONCURRENTLY cannot run in a
-- transaction block. The extension is dropped RESTRICT, so a revert fails loudly
-- (rather than cascading) if anything else has come to depend on pg_trgm.

DROP INDEX CONCURRENTLY IF EXISTS entity_identifier_value_trgm_idx;

DROP EXTENSION IF EXISTS pg_trgm;
