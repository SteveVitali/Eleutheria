-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:closed_vocabulary to pg
--
-- Reworked under @r11-vocab-verify-scope (OPS-SPINE-SCHEMA-DEPLOY, ADR-196):
-- the repair is the *verify* script, whose unscoped registry-metadata assert
-- divided by zero on sig-pg's 133 runtime-registered vocab_predicate rows
-- whose skos_concept_iri IS NULL — the fresh-vs-existing verify class of
-- D-P34.24b-1. The real DDL lives in
-- closed_vocabulary@r11-vocab-verify-scope.sql, which a spine runs for the
-- tagged instance; this deploy is a deliberate no-op — the change's
-- INSERT-only ON CONFLICT DO NOTHING projection needs no re-run, and its
-- pre-existing rows keep their values verbatim either way.

BEGIN;

SELECT 1;

COMMIT;
