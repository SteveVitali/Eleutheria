-- SPDX-License-Identifier: Apache-2.0
-- Deploy sig:transparency_source to pg
--
-- P35.35 (ticket row 313) / J3 §3.3 item 3 + J4 §9 + D-J3-1 [B-19]:
--   * NEW append-only ``source_redistribution`` — the DB mirror of each
--     ``sources.toml [sources.<id>.redistribution]`` declaration, appended
--     by PgClaimSink through the lane resolver at capture-write time. A
--     changed declaration lands a NEW row under a new ``registry_version``,
--     never an UPDATE/DELETE (append-only, P1–P3 / SIG-STORE-042).
--   * ``source_redistribution_current`` — the latest mirror row per source;
--     the join seam ``v_transparency_source`` and the API read path share.
--   * NEW explicit-column ``v_transparency_source`` — J3 §3.3 item 3's
--     ``source_registry ⋈ rights_record ⋈ latest rights_decision ⋈ current
--     redistribution ⋈ last-seen execution/capture``. Every column is on
--     policy.transparency.TRANSPARENCY_SOURCE_VIEW_COLUMNS (the closure
--     test pins the SELECT list to it verbatim); GRANT SELECT TO sig_export
--     only — the artifact, not the view, is the publication boundary.
--
-- Deliberately absent: classified upstream terms text, registry notes /
-- contact / auth_model / access_method, rights_record.reviewed_by (the
-- *decision* row carries the reviewer ROLE — Part VIII §0.7 — the raw
-- record's person-shaped column never joins), and every never-exported
-- name (J3 §3.5). A P8-1 payload is never a column: the view carries only
-- the recorded class token, never the material it classifies.

BEGIN;

CREATE TABLE source_redistribution (
    source_id         text NOT NULL REFERENCES source_registry(source_id),
    registry_version  text NOT NULL,
    lane              text NOT NULL,
    part_viii_class   text,
    evidence          text,
    evidence_uri      text,
    decision_authority text,
    review_needed     boolean NOT NULL DEFAULT false,
    packet_limited    boolean NOT NULL DEFAULT false,
    sig_labelled_cc0  boolean NOT NULL DEFAULT false,
    recorded_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (source_id, registry_version),
    -- The closed vocabularies are the same frozensets
    -- policy.transparency names (REDISTRIBUTION_LANES, PART_VIII_CLASSES
    -- plus the recorded clear values) — a lane outside the set cannot be
    -- written, so the read path never re-validates invented rights.
    CHECK (lane IN ('raw-ok', 'derived-only', 'link-only', 'restricted', 'unknown')),
    CHECK (part_viii_class IN (
        'P8-1', 'P8-2', 'P8-3', 'P8-4', 'P8-5', 'P8-6', 'P8-7', 'P8-8', 'P8-9',
        'clear', 'none-known'
    ))
);

COMMENT ON TABLE source_redistribution IS
  'P35.35 (row 313, J4 B-19): the append-only DB mirror of sources.toml '
  '[sources.<id>.redistribution] declarations. One row per '
  '(source, registry_version); a changed declaration is a NEW row under a '
  'new registry_version — never an UPDATE. The lane is a RECORDED verdict '
  '(a recorded ''unknown'' names why no positive lane could be evidenced, '
  'distinct from an absent row = undeclared); part_viii_class carries the '
  'most restrictive recorded J4 §9 class or a recorded clear value — the '
  'evidence a raw-ok lane needs before public is derivable. Written by '
  'PgClaimSink through the lane resolver; read by v_transparency_source '
  'and the API capture read path (lane + part_viii_class floor the served '
  'storage tier — tighten only, never relax).';

-- The latest-declared row per source — the read seam the transparency view
-- and the API capture path consume without knowing registry versioning.
CREATE VIEW source_redistribution_current AS
SELECT DISTINCT ON (source_id)
       source_id,
       registry_version,
       lane,
       part_viii_class,
       evidence,
       evidence_uri,
       decision_authority,
       review_needed,
       packet_limited,
       sig_labelled_cc0,
       recorded_at
  FROM source_redistribution
 ORDER BY source_id, recorded_at DESC, registry_version DESC;

COMMENT ON VIEW source_redistribution_current IS
  'P35.35: the latest recorded [redistribution] declaration per source — '
  'the registry-of-record lane the read paths consult. A missing row means '
  'undeclared (the interim rights-record basis applies), never a default '
  'lane.';

-- Append-only (P1–P3): a lane declaration is a recorded verdict; a changed
-- one is a new registry_version row.
CREATE FUNCTION source_redistribution_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'source_redistribution rows are immutable (append-only, P1-P3); a changed declaration is a new registry_version row';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER source_redistribution_immutable
  BEFORE UPDATE OR DELETE ON source_redistribution
  FOR EACH ROW EXECUTE FUNCTION source_redistribution_immutable();

-- Grants: the ingest sink appends mirror rows and reads the current view
-- when resolving a source's recorded lane; the materialize role runs bounded
-- backfill legs; sig_read_public joins the CURRENT VIEW only — the API
-- capture() path needs the lane + Part VIII fields for the served-tier
-- floor (the same fields sources.json publishes), never the append-only
-- base table. No role gets UPDATE/DELETE — the trigger and the grant
-- surface agree (append-only, P1–P3).
GRANT SELECT, INSERT ON source_redistribution TO sig_ingest;
GRANT SELECT, INSERT ON source_redistribution TO sig_materialize;
GRANT SELECT ON source_redistribution_current
    TO sig_ingest, sig_read_public;

-- J3 §3.3 item 3: the source-metadata view — registry of record + rights
-- record + latest rights decision + the recorded lane fields + the
-- last-seen columns. Explicit columns only (S-12); the two "last change"
-- columns (K9 C-6) are RELEASE-DIFF semantics computed at emission over
-- the capture marks — the view carries the last-seen freshness
-- (last_execution_at, last_capture_at) the emission basis names.
CREATE VIEW v_transparency_source AS
WITH latest_decision AS (
    SELECT DISTINCT ON (rd.source_id)
           rd.source_id,
           rd.basis,
           rd.reviewer,
           rd.decided_at
      FROM rights_decision rd
     ORDER BY rd.source_id, rd.decided_at DESC, rd.decision_id DESC
),
last_execution AS (
    SELECT c.source_id, max(c.finished_at) AS last_execution_at
      FROM ingest_run_completion c
     WHERE c.source_id IS NOT NULL
     GROUP BY c.source_id
),
last_capture AS (
    SELECT ea.source_id, max(ec.retrieved_at) AS last_capture_at
      FROM evidence_capture ec
      JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
     GROUP BY ea.source_id
)
SELECT
    sr.source_id,
    sr.name,
    sr.source_kind,
    sr.homepage_url,
    sr.custody_posture,
    sr.compact_status,
    sr.ingestion_permitted,
    sr.robots_policy,
    sr.last_verified_at,
    rr.spdx_expression,
    rr.attribution_text,
    rr.redistributable,
    rr.derivative_permitted,
    rr.terms_url,
    (rr.reviewed_at IS NOT NULL) AS terms_reviewed,
    rr.reviewed_at AS terms_reviewed_at,
    rr.retrieval_date,
    ld.basis AS rights_decision_basis,
    ld.reviewer AS rights_decision_reviewer,
    ld.decided_at AS rights_decided_at,
    srd.lane,
    srd.evidence AS lane_evidence,
    srd.evidence_uri AS lane_evidence_uri,
    srd.decision_authority AS lane_decision_authority,
    srd.review_needed AS lane_review_needed,
    srd.part_viii_class,
    srd.packet_limited,
    srd.sig_labelled_cc0,
    le.last_execution_at,
    lc.last_capture_at
  FROM source_registry sr
  JOIN rights_record rr ON rr.rights_id = sr.rights_id
  LEFT JOIN latest_decision ld ON ld.source_id = sr.source_id
  LEFT JOIN source_redistribution_current srd ON srd.source_id = sr.source_id
  LEFT JOIN last_execution le ON le.source_id = sr.source_id
  LEFT JOIN last_capture lc ON lc.source_id = sr.source_id;

COMMENT ON VIEW v_transparency_source IS
  'P35.35 (J3 §3.3 item 3): the sig_export-facing source-metadata view — '
  'registry identity/posture, the rights record, the latest rights '
  'decision (basis + reviewer ROLE + decided_at), the recorded '
  '[redistribution] lane fields, and last-seen freshness. Explicit-column '
  'allow-list only; sensitive fields (notes, contact, auth model/access '
  'method, reviewer identity, classified terms text, P8-1 restricted '
  'content) are structurally absent — the artifact, not the view, is the '
  'publication boundary.';

-- sig_export only (J3 §3.3 item 2's pairing rule): no sig_read_public —
-- the published artifact is built from this view by the export role.
GRANT SELECT ON v_transparency_source TO sig_export;

COMMIT;
