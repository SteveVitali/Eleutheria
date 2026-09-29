-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:research_task_trigger to pg
-- P29.2 — the detector/records-request loop on real data. The §33.2 catalog + the
-- research-task engine (P10.1/P10.2) have existed since Phase 10; the `research_task`
-- table (graph_annotations, P02.1) has held no row because task-queue persistence was
-- deferred (ADR-039, §33.2). P29.2 runs the detector catalog over the Round-6
-- MATERIALIZED graph (contradictions/coverage/relationships) and WRITES the research
-- queue as durable `research_task` rows.
--
-- A cross-cutting §33 invariant is that **every generated task cites its trigger** —
-- the materialized detector output (a contradiction, a coverage gap, a stale sharing
-- edge) that made the detector fire. This change adds that citation to the row:
-- nullable `trigger_kind` (contradiction | coverage | relationship) + `trigger_ref`
-- (the materialized row's id). The existing UNIQUE (task_type, subject_id) is the
-- idempotency contract the append-only research-queue materializer needs (it
-- INSERTs ... ON CONFLICT (task_type, subject_id) DO NOTHING, so an idempotent re-run
-- over an unchanged spine is +0) — no new digest column is needed.
--
-- Additive & back-compatible (SIG-STORE-042): both columns are nullable with no
-- default, so any pre-existing / hand-inserted research_task row (trigger_kind IS
-- NULL) is unaffected, and the public research-queue surface reads the trigger only
-- when present.

BEGIN;

ALTER TABLE research_task
  ADD COLUMN trigger_kind text,   -- contradiction | coverage | relationship (the detector output kind)
  ADD COLUMN trigger_ref  text;   -- the materialized row id the task cites as its trigger

COMMIT;
