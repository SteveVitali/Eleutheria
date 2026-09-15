-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:read_surface_grants to pg
-- P24.1 live deploy (DEPLOY.1 / GL-DEPLOY-01, ADR-081): the read API SET ROLEs to
-- `sig_read_public` (RLS stays on) and queries the FULL §37 read surface — not only
-- the five tables access_control granted (claim/resolution/entity/evidence_artifact/
-- evidence_capture). On a hosted Cloud SQL spine the connecting login is NOT a
-- superuser, so SELECT is denied on the rest (entity_identifier, the domain-entity
-- and graph-annotation tables, the L4 inference schema, …) and the API 500s. Locally
-- the compose superuser bypassed grants, so this never surfaced. Grant SELECT on the
-- whole read surface to the read roles; the RESTRICTIVE tier ceilings from
-- access_control still bind (a read role only ever sees sensitivity_tier <=
-- sig_visible_max_tier()). Append-only is unaffected: read roles get no write.

BEGIN;

-- Schema usage for the read roles (public already usable; inference was not).
GRANT USAGE ON SCHEMA public    TO sig_read_public, sig_export;
GRANT USAGE ON SCHEMA inference TO sig_read_public, sig_export;

-- SELECT across the full read surface (existing tables) …
GRANT SELECT ON ALL TABLES IN SCHEMA public    TO sig_read_public, sig_export;
GRANT SELECT ON ALL TABLES IN SCHEMA inference TO sig_read_public, sig_export;

-- … and for any tables added by later changes (forward-compatible).
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO sig_read_public, sig_export;
ALTER DEFAULT PRIVILEGES IN SCHEMA inference
  GRANT SELECT ON TABLES TO sig_read_public, sig_export;

COMMIT;
