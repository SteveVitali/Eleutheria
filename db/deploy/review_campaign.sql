-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:review_campaign to pg
--
-- Reworked under @r11-read-allowlist (P34.25, ADR-196): the tables and grants
-- are unchanged at deploy time — the repair is the *verify* script, whose
-- sig_read_public SELECT assertion stops being true once
-- public_read_allowlist narrows the public role to the published §37 surface
-- (the campaign machinery is internal curation state, off the public read
-- surface; sig_materialize's campaign read/write is re-granted directly by
-- that change). The real DDL lives in review_campaign@r11-read-allowlist.sql,
-- which a fresh database still runs for the tagged instance; this deploy is a
-- deliberate no-op so an already-deployed database only gains the new change
-- record.

BEGIN;

SELECT 1;

COMMIT;
