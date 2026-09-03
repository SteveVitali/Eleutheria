-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:access_control to pg
-- §16.8 / §44.4 / ADR-012: sensitivity tiers enforced by RESTRICTIVE row-level
-- security. The public API role holds no BYPASSRLS (SIG-STORE-023); export/dump
-- roles are meant to run with row_security = off so a would-be-filtered export
-- FAILS LOUDLY instead of silently publishing a subset. Application roles hold no
-- DELETE on the append-only tables (SIG-STORE-012). RLS policy tests are
-- CI-blocking (SIG-STORE-024).
--
-- Tier model: claim.sensitivity_tier / evidence_artifact.sensitivity_tier are
-- smallints (0 public, 1 restricted, 2 sealed); evidence_capture.storage_tier is
-- the matching text ladder. Roles are hierarchical so a sealed reader also reads
-- restricted and public.

BEGIN;

-- Roles are NOLOGIN groups (least privilege); connections SET ROLE / are members.
-- CREATE ROLE is not transactional-safe to repeat, so guard each with a DO block.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_read_public') THEN
    CREATE ROLE sig_read_public NOLOGIN NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_read_restricted') THEN
    CREATE ROLE sig_read_restricted NOLOGIN NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_read_sealed') THEN
    CREATE ROLE sig_read_sealed NOLOGIN NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_export') THEN
    CREATE ROLE sig_export NOLOGIN NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_ingest') THEN
    CREATE ROLE sig_ingest NOLOGIN NOBYPASSRLS;
  END IF;
END $$;

-- Visibility ladder: a sealed reader inherits restricted inherits public.
GRANT sig_read_public     TO sig_read_restricted;
GRANT sig_read_restricted TO sig_read_sealed;

-- The highest sensitivity tier the current role may see (-1 = no access).
CREATE OR REPLACE FUNCTION sig_visible_max_tier() RETURNS smallint
  LANGUAGE sql STABLE AS $$
  SELECT (CASE
    WHEN pg_has_role(current_user, 'sig_read_sealed',     'USAGE') THEN 2
    WHEN pg_has_role(current_user, 'sig_read_restricted', 'USAGE') THEN 1
    WHEN pg_has_role(current_user, 'sig_read_public',     'USAGE') THEN 0
    ELSE -1
  END)::smallint;
$$;

-- Table privileges (RLS is enforced ON TOP of these, never instead of them).
GRANT SELECT ON claim, resolution, entity, evidence_artifact, evidence_capture
  TO sig_read_public, sig_export;
GRANT SELECT, INSERT, UPDATE ON claim TO sig_ingest;
GRANT SELECT, INSERT ON entity, resolution, evidence_artifact, evidence_capture, extraction
  TO sig_ingest;

-- SIG-STORE-012: no application role may DELETE from the append-only tables.
REVOKE DELETE ON claim, extraction, evidence_artifact, evidence_capture FROM PUBLIC;
REVOKE DELETE ON claim, extraction, evidence_artifact, evidence_capture
  FROM sig_ingest, sig_read_public, sig_read_restricted, sig_read_sealed, sig_export;

-- ---- claim: restrictive tier RLS ------------------------------------------
ALTER TABLE claim ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim FORCE ROW LEVEL SECURITY;
-- A permissive base grant, then a restrictive tier ceiling (SIG-STORE-023).
CREATE POLICY claim_base ON claim
  AS PERMISSIVE FOR ALL
  TO sig_read_public, sig_read_restricted, sig_read_sealed, sig_ingest
  USING (true) WITH CHECK (true);
CREATE POLICY claim_tier_ceiling ON claim
  AS RESTRICTIVE FOR SELECT
  USING (sensitivity_tier <= sig_visible_max_tier());

-- ---- evidence_artifact: same tier model -----------------------------------
ALTER TABLE evidence_artifact ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_artifact FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_artifact_base ON evidence_artifact
  AS PERMISSIVE FOR ALL
  TO sig_read_public, sig_read_restricted, sig_read_sealed, sig_ingest
  USING (true) WITH CHECK (true);
CREATE POLICY evidence_artifact_tier_ceiling ON evidence_artifact
  AS RESTRICTIVE FOR SELECT
  USING (sensitivity_tier <= sig_visible_max_tier());

-- ---- evidence_capture: storage_tier ladder mapped to the numeric tiers ----
ALTER TABLE evidence_capture ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_capture FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_capture_base ON evidence_capture
  AS PERMISSIVE FOR ALL
  TO sig_read_public, sig_read_restricted, sig_read_sealed, sig_ingest
  USING (true) WITH CHECK (true);
CREATE POLICY evidence_capture_tier_ceiling ON evidence_capture
  AS RESTRICTIVE FOR SELECT
  USING (
    (CASE storage_tier
       WHEN 'public'     THEN 0
       WHEN 'restricted' THEN 1
       WHEN 'sealed'     THEN 2
       ELSE 2
     END) <= sig_visible_max_tier()
  );

COMMIT;
