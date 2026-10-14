-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:audit_login to pg
--
-- P34.43 (SIG-CONF-013; L3 CP-0; G2 ACT-13; ADR-202): the least-privilege
-- DATABASE LOGINS the hosted return-pass/quality-probe execution host
-- connects as. Catalog-only — role rows, memberships and two NEW-16 table
-- grants; never a table definition, never a lock beyond the catalog.
--
--   * `sig_audit` — the SELECT-only audit/quality login (L1): LOGIN,
--     NOBYPASSRLS, CONNECTION LIMIT 4, member of `sig_read_public` (the §37
--     surface P34.25's allow-list carved; the tier-0 RLS ceiling binds), a
--     read-only session by default, a 60s statement timeout, and SELECT on
--     the two NEW-16 capture-store tables the read role omits
--     (ingest_run_capture, entity_identity_key — the audit's declared read
--     surface). Its password is provisioned by the P34.43 leg out of Secret
--     Manager — never in this file, never in a commit (HG-09, ADR-202).
--     The CREATE is guarded because the P34.43 leg runs these same catalog
--     statements ahead of the deploy on hosted (a role is cluster-global;
--     the deploy converges every spine it reaches).
--   * `sig_recovery_login` — the LOGIN member of the `sig_recovery` group
--     role L52 (`recovery_apply`, P32.22) creates (L2, live:P34.46): LOGIN,
--     CONNECTION LIMIT 2, membership in `sig_recovery` only — its bounded
--     apply surface rides the group's grants (P34.43 adds no table grant to
--     it; P35.61 owns the bounded apply). Deployed here so the credential's
--     row exists wherever the plan reaches; the P34.43 L2 leg sets its
--     password only after P34.46 deploys the group on hosted.

BEGIN;

SET LOCAL lock_timeout = '5s';

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_audit') THEN
    CREATE ROLE sig_audit LOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 4;
  END IF;
END $$;

-- READ: the public read role's §37 surface (RLS tier-0 binds; no write of any
-- kind rides this membership).
GRANT sig_read_public TO sig_audit;

-- The NEW-16 capture-store tables the read role omits: the audit login's
-- declared read surface for return-pass evidence.
GRANT SELECT ON ingest_run_capture TO sig_audit;
GRANT SELECT ON entity_identity_key TO sig_audit;

-- Session posture: read-only by default + a bounded statement clock.
ALTER ROLE sig_audit SET default_transaction_read_only = 'on';
ALTER ROLE sig_audit SET statement_timeout = '60s';

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_recovery_login') THEN
    CREATE ROLE sig_recovery_login LOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 2;
  END IF;
END $$;

-- The bounded apply surface is the group role's, never duplicated here.
GRANT sig_recovery TO sig_recovery_login;

COMMIT;
