-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:extensions to pg
-- Required extensions. uuidv7() is a core PG18 function (SIG-STORE-010), so no
-- extension is needed for it. PostGIS supplies the geometry type (ADR-001);
-- btree_gist supplies the equality operator classes the resolution non-overlap
-- exclusion constraint needs alongside the range && operator (§16.4).

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS btree_gist;

COMMIT;
