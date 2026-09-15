-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:read_surface_grants from pg

BEGIN;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE SELECT ON TABLES FROM sig_read_public, sig_export;
ALTER DEFAULT PRIVILEGES IN SCHEMA inference
  REVOKE SELECT ON TABLES FROM sig_read_public, sig_export;

REVOKE SELECT ON ALL TABLES IN SCHEMA public    FROM sig_read_public, sig_export;
REVOKE SELECT ON ALL TABLES IN SCHEMA inference FROM sig_read_public, sig_export;
REVOKE USAGE  ON SCHEMA inference FROM sig_read_public, sig_export;

-- Restore the original access_control grants (the broad REVOKE above removed them).
GRANT SELECT ON claim, resolution, entity, evidence_artifact, evidence_capture
  TO sig_read_public, sig_export;

COMMIT;
