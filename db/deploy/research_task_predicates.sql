-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:research_task_predicates to pg
--
-- P37.35 (K11 RQ-02 / R11-K13-RQ-02, D-K11-1 "as recommended"; SIG-RQ-005).
-- The detector's explicit predicate→task routing table (`tasks/data/gap_routing.toml`)
-- replaces the retired substring match: a task records WHICH predicate(s) it seeks,
-- and per-object coverage_hole rows minted under the old routing are superseded
-- by disposition — append-only, never a delete.
--
--   * `predicate_ids text[]` — the missing predicate(s) the task seeks (nullable:
--     a pre-change / hand-inserted row carries NULL, never a fabricated list).
--   * `disposition_reason text` — the recorded reason a superseded/closed row
--     carries (K11: "existing rows get a `superseded` disposition with a reason").
--   * Column-scoped UPDATE on (status, disposition, disposition_reason) to
--     sig_materialize — the same event-surface precedent as
--     `disappearance_event_grant`: the disposition is the designed update
--     surface (an EVENT, never a delete); every other column and DELETE stay
--     un-granted.
--
-- Additive & back-compatible (SIG-STORE-042): both columns are nullable with no
-- default, so every existing research_task row is unaffected.

BEGIN;

ALTER TABLE research_task
  ADD COLUMN predicate_ids text[],
  ADD COLUMN disposition_reason text;

COMMENT ON COLUMN research_task.predicate_ids IS
  'The missing predicate(s) the task seeks (SIG-RQ-005; P37.35) — NULL for pre-change rows.';
COMMENT ON COLUMN research_task.disposition_reason IS
  'The recorded reason a closed task carries its disposition (K11 RQ-02 supersede-by-disposition).';

-- The disposition event surface (disappearance_event_grant precedent): the
-- detector run marks superseded rows through exactly these columns.
GRANT UPDATE (status, disposition, disposition_reason)
  ON research_task TO sig_materialize;

COMMIT;
