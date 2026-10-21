-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_sightings to pg
-- P35.44 (R11-K13-DSRC-01 / K5 §3.1, J3 T-2): the explicit-column claim-sighting
-- edge list the dossier-contribution export reads. One row per
-- (claim, capture, role='establishes') binding joined to its capture + artifact —
-- the claim's identity/gate columns (claim_id, subject_id, object_entity,
-- predicate_id, sensitivity_tier, rights_id, sys_period) beside the sighting's
-- own provenance (capture, role, binding_status, bound_at, artifact, the
-- sighting's source = the capture artifact's source, the retrieving run, the
-- retrieval instant). Explicit columns only, never SELECT *; GRANT SELECT to
-- sig_export only — the public never reaches raw claim_evidence rows, and the
-- emitted columns are the same allow-list
-- ``policy.transparency.CLAIM_SIGHTING_VIEW_COLUMNS`` carries (the closure test
-- fails the build on any drift).
--
-- Read-only relation over the append-only spine: the view adds nothing,
-- rewrites nothing, and the aggregate the export runs over it applies the
-- shared publishable-claim gates ({PUB_CLAIM_GATE} / effective rights /
-- artifact + capture-seal gates) at query time — the same seam every sibling
-- claim read uses.
--
-- Never-exported fields stay off the list (J3 §3.5 + S-2…S-4):
-- claim_evidence.locator/excerpt/weight_note (S-8 excerpts are never-exported),
-- extraction identity details, evidence_capture.request_fingerprint/content
-- digests/ocfl locators, and evidence_artifact.url (the S-6 scrub happens at
-- emission, not in the view).

BEGIN;

CREATE VIEW v_claim_sightings AS
SELECT
    c.claim_id,
    c.subject_id,
    c.object_entity,
    c.predicate_id,
    c.sensitivity_tier,
    c.rights_id,
    c.sys_period,
    ce.capture_id,
    ce.role,
    ce.binding_status,
    ce.bound_at,
    ec.artifact_id,
    ea.source_id,
    ec.retrieved_by_run_id AS run_id,
    ec.retrieved_at
FROM claim c
JOIN claim_evidence ce ON ce.claim_id = c.claim_id
JOIN evidence_capture ec ON ce.capture_id = ec.capture_id
JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id
WHERE ce.role = 'establishes';

GRANT SELECT ON v_claim_sightings TO sig_export;

COMMIT;
