-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:er_rerun_login to pg
--
-- P34.45 (ADR-153, ADR-206; OM-20 pre-authorised "Both + list + P34.45"): the
-- least-privilege WRITE-capable login the v3-interim camera-site ER re-run
-- connects as on the P34.43 execution host. `sig_materialize_login` is a
-- distinct LOGIN member of the existing NOLOGIN `sig_materialize` group — its
-- write surface is exactly the group's: INSERT-only on the materialized
-- tables (camera_site_run / camera_site_match / camera_site_execution /
-- review_item, the Round-6 resolution tables, ingest_run_completion,
-- publication_disposition) with UPDATE/DELETE/TRUNCATE revoked group-wide and
-- no claim-spine write of any kind. Append-only by GRANT, never by promise.
--
--   * The CREATE is guarded because the P34.45 leg runs these same catalog
--     statements ahead of the deploy on hosted (a role is cluster-global;
--     the deploy converges every spine it reaches).
--   * Its password is provisioned by the leg out of Secret Manager
--     (sig-er-rerun-password; accessor: the exec SA only) — never in this
--     file, never in a commit (HG-09, ADR-202).
--   * NO session defaults are set: the login is write-capable by design (the
--     one pre-authorised append-only mutation), so it deliberately carries no
--     `default_transaction_read_only` — the INSERT grants bound it, not a
--     session flag.

BEGIN;

SET LOCAL lock_timeout = '5s';

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_materialize_login') THEN
    CREATE ROLE sig_materialize_login LOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 2;
  END IF;
END $$;

-- The whole write surface is the group role's — never duplicated grant by
-- grant here (same shape as sig_recovery_login on L52's sig_recovery).
GRANT sig_materialize TO sig_materialize_login;

COMMIT;
