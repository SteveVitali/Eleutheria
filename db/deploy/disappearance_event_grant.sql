-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:disappearance_event_grant to pg
-- P37.5b / SIG-INGEST-009/010 + SIG-EVID-013 (§17.6, C.3): the disappearance
-- writer's permission surface. A disappearance is an EVENT on the artifact —
-- `disappeared_observed_at` plus the failing `capture_status` — recorded by an
-- UPDATE of exactly those two event columns, never a delete and never any
-- other column. The grant is column-scoped so the append-only posture holds
-- inside the permission itself: `sig_ingest` gains UPDATE on the event
-- columns only; every other evidence_artifact column stays un-writable and
-- DELETE stays un-granted (the ingest role's insert-only posture is unchanged).

BEGIN;

GRANT UPDATE (capture_status, disappeared_observed_at)
  ON public.evidence_artifact TO sig_ingest;

COMMIT;
