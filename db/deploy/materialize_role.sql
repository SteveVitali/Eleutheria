-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:materialize_role to pg
-- P30.2 (GO-LIVE.2, ADR-103): the least-privilege READ/MATERIALIZE role the Round-6
-- materializers (P28.1 resolution, P28.2 edges, P28.3 contradictions, P28.4 coverage,
-- P28.6 accountability links) and the P29.2 detector research queue run as on the
-- hosted spine (`--role sig_materialize`). Operator-authorized: LEDGER GATE DECISIONS
-- 2026-09-23 ("I authorize you to create postgres role under ADC").
--
-- Least privilege, exactly:
--   * READ = membership in `sig_read_public` — SELECT on the §37 read surface with the
--     access_control RESTRICTIVE tier ceiling still binding (the role sees only
--     sensitivity_tier 0, which is all the materializers read). NOBYPASSRLS.
--   * WRITE = INSERT only, and only on the six materialized tables + the three FK
--     vocab tables the resolution materializer upserts (`ON CONFLICT DO NOTHING`).
--   * NO UPDATE / DELETE / TRUNCATE anywhere, and NO write at all on the claim spine
--     (claim / claim_evidence / evidence_* / entity) — append-only is structural, not
--     a convention (ADR-005, SIG-STORE-012).
--   * NOLOGIN: a connecting login (the schema owner that deploys this change) is
--     granted membership so it can `SET ROLE sig_materialize` for the session.
--
-- Idempotent: CREATE ROLE is guarded (roles are cluster-global); GRANT/REVOKE repeat
-- safely. No secret: the role has no password (NOLOGIN), credentials stay env-only.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_materialize') THEN
    CREATE ROLE sig_materialize NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

-- READ: the public read role (SELECT on the read surface; tier-0 RLS ceiling binds).
GRANT sig_read_public TO sig_materialize;

-- WRITE: INSERT only on the Round-6 materialized tables (+ RETURNING needs the SELECT
-- the read role already holds on them).
GRANT INSERT ON resolution, relationship, contradiction, coverage_record, research_task
  TO sig_materialize;
GRANT INSERT ON inference.derived_fact TO sig_materialize;
-- The resolution materializer's FK vocab prerequisites (INSERT ... ON CONFLICT DO NOTHING).
GRANT INSERT ON vocab_resolution_strategy, vocab_rationale, vocab_confidence
  TO sig_materialize;

-- Belt and braces: no UPDATE / DELETE / TRUNCATE on anything this role can touch.
REVOKE UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public    FROM sig_materialize;
REVOKE UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA inference FROM sig_materialize;

-- The deploying login (the schema owner — `sig` on the hosted spine) may SET ROLE to it.
DO $$ BEGIN
  EXECUTE format('GRANT sig_materialize TO %I', current_user);
END $$;

COMMIT;
