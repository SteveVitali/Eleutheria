-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:access_control on pg
DO $$ BEGIN
  IF to_regprocedure('sig_visible_max_tier()') IS NULL THEN RAISE EXCEPTION 'tier fn missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='sig_read_public' AND NOT rolbypassrls) THEN
    RAISE EXCEPTION 'sig_read_public missing or holds BYPASSRLS'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname='claim' AND relrowsecurity) THEN
    RAISE EXCEPTION 'RLS not enabled on claim'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='claim' AND policyname='claim_tier_ceiling') THEN
    RAISE EXCEPTION 'claim tier policy missing'; END IF;
END $$;
