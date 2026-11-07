-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert eleutheria-claims:disappearance_event_grant from pg
--
-- Drop the column-scoped UPDATE grant; sig_ingest returns to its insert-only
-- posture on evidence_artifact.

BEGIN;

REVOKE UPDATE (capture_status, disappeared_observed_at)
  ON public.evidence_artifact FROM sig_ingest;

COMMIT;
