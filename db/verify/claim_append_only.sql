-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim_append_only on pg
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='claim_append_only_trg') THEN
    RAISE EXCEPTION 'append-only trigger missing'; END IF;
  IF to_regprocedure('claim_append_only()') IS NULL THEN
    RAISE EXCEPTION 'append-only function missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM append_only_guard WHERE table_name='claim') THEN
    RAISE EXCEPTION 'append_only_guard not populated for claim'; END IF;
END $$;
