-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:temporal_invariants to pg
-- §9.4 / §9.6: the DB-side half of P02.3's temporal contract.
--   1. TI-8 support: an explicit, reasoned `temporally_unanchored` flag so a claim
--      is never allowed to float free of all time (§9.6). Additive and
--      back-compatible — default false, so every existing claim (each of which
--      carries observed_at) is unaffected (SIG-TIME-013).
--   2. The as-of query functions (SIG-TIME-007/008/009): the two queryable axes
--      are T1 valid time (`as_of_world` -> valid_period) and T5 assertion time
--      (`as_of_belief` -> sys_period). Observation time (T2) is deliberately NOT
--      an axis (SIG-TIME-016). These functions ARE the shared read-path filter;
--      the fourth (both pinned to the past) form is what makes a past SIG citation
--      reproducible (§16.6, SIG-TIME-009).

BEGIN;

ALTER TABLE claim
  ADD COLUMN temporally_unanchored boolean NOT NULL DEFAULT false,
  ADD COLUMN temporally_unanchored_reason text,
  ADD CONSTRAINT claim_unanchored_reasoned
    CHECK (NOT temporally_unanchored OR temporally_unanchored_reason IS NOT NULL);

-- Keep the append-only guard list complete (SIG-STORE-011, §16.3): the new
-- columns are immutable like every other claim column, so a correction must be a
-- new row, never an in-place edit of these fields.
INSERT INTO append_only_guard (table_name, column_name)
VALUES ('claim', 'temporally_unanchored'),
       ('claim', 'temporally_unanchored_reason');

-- Defaults are explicit (SIG-TIME-007): world and belief both default to the
-- current instant ("today" / "now (latest)"). clock_timestamp() — the real wall
-- clock — is used rather than now() (transaction start) so that "latest belief"
-- means the newest committed claim even inside a long-running transaction. A
-- caller pinning either axis to the past gets exactly one of the four §9.4
-- questions.
CREATE FUNCTION claim_as_of(
  as_of_world  timestamptz DEFAULT clock_timestamp(),
  as_of_belief timestamptz DEFAULT clock_timestamp()
) RETURNS SETOF claim
  LANGUAGE sql
  STABLE
AS $$
  SELECT *
    FROM claim
   WHERE valid_period @> as_of_world
     AND sys_period   @> as_of_belief;
$$;

CREATE FUNCTION resolution_as_of(
  as_of_world  timestamptz DEFAULT clock_timestamp(),
  as_of_belief timestamptz DEFAULT clock_timestamp()
) RETURNS SETOF resolution
  LANGUAGE sql
  STABLE
AS $$
  SELECT *
    FROM resolution
   WHERE valid_period @> as_of_world
     AND sys_period   @> as_of_belief;
$$;

COMMIT;
