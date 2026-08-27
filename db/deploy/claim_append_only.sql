-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_append_only to pg
-- §16.3 / SIG-STORE-011/013: append-only enforcement in the database, not by
-- convention. DELETE is forbidden outright; the ONLY permitted UPDATE is closing
-- the transaction-time interval (setting sys_period's upper bound once, while its
-- lower bound stays fixed). Corrections are new rows with revises_claim (§16.6).
--
-- The set of columns that may NOT change is kept in `append_only_guard`, POPULATED
-- FROM THE LIVE SCHEMA (every claim column except sys_period). This is the
-- "explicit column list generated from the schema" §16.3 requires so that adding
-- a column cannot silently widen what is mutable; a CI schema test asserts the
-- guard list still matches the live schema (SIG-STORE-011 / §48).

BEGIN;

CREATE TABLE append_only_guard (
  table_name  text NOT NULL,
  column_name text NOT NULL,
  PRIMARY KEY (table_name, column_name)
);

INSERT INTO append_only_guard (table_name, column_name)
SELECT 'claim', column_name
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name = 'claim'
   AND column_name <> 'sys_period';

CREATE OR REPLACE FUNCTION claim_append_only() RETURNS trigger AS $$
DECLARE
  guarded text;
  old_j   jsonb := to_jsonb(OLD);
  new_j   jsonb := to_jsonb(NEW);
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'claim rows are immutable: DELETE forbidden (claim_id=%)', OLD.claim_id
      USING ERRCODE = 'restrict_violation';
  END IF;

  -- Every guarded (non-sys_period) column MUST be unchanged. The list is data,
  -- generated from the schema, so a newly-added column is guarded automatically.
  FOR guarded IN
    SELECT column_name FROM append_only_guard WHERE table_name = 'claim'
  LOOP
    IF (old_j -> guarded) IS DISTINCT FROM (new_j -> guarded) THEN
      RAISE EXCEPTION
        'claim rows are immutable: only sys_period may be closed (attempted change to %, claim_id=%)',
        guarded, OLD.claim_id
        USING ERRCODE = 'restrict_violation';
    END IF;
  END LOOP;

  -- The one permitted mutation: closing the open transaction-time interval.
  IF NEW.sys_period IS DISTINCT FROM OLD.sys_period THEN
    IF lower(NEW.sys_period) IS DISTINCT FROM lower(OLD.sys_period) THEN
      RAISE EXCEPTION 'sys_period lower bound is immutable (claim_id=%)', OLD.claim_id
        USING ERRCODE = 'restrict_violation';
    END IF;
    IF NOT upper_inf(OLD.sys_period) THEN
      RAISE EXCEPTION 'claim already closed (claim_id=%)', OLD.claim_id
        USING ERRCODE = 'restrict_violation';
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER claim_append_only_trg
  BEFORE UPDATE OR DELETE ON claim
  FOR EACH ROW EXECUTE FUNCTION claim_append_only();

COMMIT;
