-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:publication_dispositions to pg
--
-- P32.5 / ADR-124 (SIG-TRUST-006): the append-only publication-disposition
-- registry and its SQL twin of the shared eligibility selector
-- (policy/publication-eligibility/1, db.dispositions / policy.eligibility).
--
--   1. publication_disposition — one row per recorded publication decision
--      (allow | withhold | restrict | withdraw) on a target (entity | claim |
--      artifact | release_artifact), carrying the policy version, authority,
--      public-safe reason category, decision instant, optional evidence/correction
--      linkage and an optional supersedes pointer. The registry is APPEND-ONLY:
--      a changed decision is a new row; no UPDATE/DELETE route exists (trigger +
--      privilege).
--
--   2. effective_disposition — the SQL twin of
--      policy.eligibility.latest_disposition: the latest row decided_at <= the
--      given instant (NULL = current access time). Readers always evaluate the
--      CURRENT effective disposition — a withhold recorded in release R2 still
--      denies the data under a rollback to R1, on every origin/cache/archive
--      path. dispositions do not have belief-time validity for public access;
--      the belief/as-of contract (temporal-read/1) governs the assertion
--      history, the disposition governs CURRENT access.
--
--   3. spine_watermark facet — a recorded disposition invalidates the cached
--      label/search/shape reads, so the registry joins the watched set
--      (INSERT/TRUNCATE bumps; UPDATE is impossible by trigger).
--
-- Least privilege: the public read/export roles see the public-safe columns
-- only (reason category + authority + policy version — never the free-text
-- rationale or decided_by, which stay with the elevated/review roles). Writes
-- go through sig_materialize (the review/curation write role, same pattern as
-- review_decision); the table grants no UPDATE or DELETE to any role.

BEGIN;

CREATE TABLE publication_disposition (
  disposition_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  disposition_seq  bigint GENERATED ALWAYS AS IDENTITY,
  target_kind      text NOT NULL
                   CHECK (target_kind IN ('entity','claim','artifact','release_artifact')),
  -- text uniformly: entity/claim/artifact ids are uuids (::text at the join
  -- site), a release_artifact is keyed by its logical release-object name.
  target_id        text NOT NULL,
  disposition      text NOT NULL
                   CHECK (disposition IN ('allow','withhold','restrict','withdraw')),
  reason_category  text NOT NULL
                   CHECK (reason_category IN (
                     'pending_publication_review','withheld_after_review',
                     'rights_withdrawal','safety_withdrawal',
                     'policy_restriction','suppressed')),
  authority        text NOT NULL,          -- who/what decided (gate, reviewer, policy)
  decided_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  decided_by       text,                   -- the recording actor (privileged)
  rationale        text,                   -- free-text record (privileged — never public)
  evidence_claim_id uuid REFERENCES claim(claim_id),
  supersedes       uuid REFERENCES publication_disposition(disposition_id),
  policy_version   text NOT NULL           -- e.g. 'publication-eligibility/1'
);

COMMENT ON TABLE publication_disposition IS
  'P32.5/ADR-124 (SIG-TRUST-006): the append-only publication-disposition '
  'registry. Every publication decision — allow/withhold/restrict/withdraw — '
  'is one new row carrying policy version, authority, safe reason category, '
  'decision instant and evidence/correction linkage. A changed decision is a '
  'new row (supersedes links it); the table admits no UPDATE/DELETE. Readers '
  'apply the CURRENT effective disposition at access time, so a withhold '
  'recorded in release R2 still denies under a rollback to R1.';

-- The per-target effective-disposition lookup is the hot read.
CREATE INDEX publication_disposition_target_idx
  ON publication_disposition (target_kind, target_id, decided_at DESC, disposition_seq DESC);

-- ---------------------------------------------------------------------------
-- The SQL twin of policy.eligibility.latest_disposition.
-- ---------------------------------------------------------------------------
CREATE FUNCTION effective_disposition(p_target_kind text, p_target_id text,
                                      p_at timestamptz DEFAULT NULL)
RETURNS TABLE (
  disposition_id uuid,
  disposition    text,
  reason_category text,
  authority      text,
  decided_at     timestamptz,
  policy_version text
) AS $$
  SELECT d.disposition_id, d.disposition, d.reason_category, d.authority,
         d.decided_at, d.policy_version
    FROM publication_disposition d
   WHERE d.target_kind = p_target_kind
     AND d.target_id = p_target_id
     -- p_at NULL = "current access" (all recorded decisions). A pinned instant
     -- answers "what did policy say THEN" for review, never a public rollback.
     AND d.decided_at <= COALESCE(p_at, clock_timestamp())
   ORDER BY d.decided_at DESC, d.disposition_seq DESC
   LIMIT 1
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION effective_disposition(text, text, timestamptz) IS
  'P32.5/ADR-124 publication-eligibility/1: the latest recorded disposition on a '
  'target at the given instant (NULL = current access time). Pure twin: '
  'policy.eligibility.latest_disposition.';

-- ---------------------------------------------------------------------------
-- Append-only: a disposition is recorded once, never mutated.
-- ---------------------------------------------------------------------------
CREATE FUNCTION publication_disposition_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'publication_disposition rows are immutable (append-only, P1-P3); append a NEW row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER publication_disposition_immutable
  BEFORE UPDATE OR DELETE ON publication_disposition
  FOR EACH ROW EXECUTE FUNCTION publication_disposition_immutable();

-- ---------------------------------------------------------------------------
-- Privileges — least privilege over the tombstone vs the record.
-- ---------------------------------------------------------------------------
-- Public read + export roles: the public-safe columns only. reason_category /
-- authority / policy_version are what an honest tombstone may state; the
-- free-text rationale and the recording actor stay off the public surface.
GRANT SELECT (disposition_id, disposition_seq, target_kind, target_id,
              disposition, reason_category, authority, decided_at,
              evidence_claim_id, supersedes, policy_version)
  ON publication_disposition TO sig_read_public, sig_export;
-- Elevated readers (the authorized-review path) + the recording role see all.
GRANT SELECT ON publication_disposition
  TO sig_read_restricted, sig_read_sealed, sig_materialize;
-- Dispositions are recorded through the materialize/curation write role — the
-- same least-privilege role that appends review_decision rows (P31.10).
GRANT INSERT ON publication_disposition TO sig_materialize;
GRANT USAGE ON SEQUENCE publication_disposition_disposition_seq_seq TO sig_materialize;

-- SIG-STORE-012 discipline: no application role may UPDATE/DELETE here either.
REVOKE UPDATE, DELETE ON publication_disposition FROM PUBLIC;
REVOKE UPDATE, DELETE ON publication_disposition
  FROM sig_ingest, sig_read_public, sig_read_restricted, sig_read_sealed,
       sig_export, sig_materialize;

-- ---------------------------------------------------------------------------
-- spine_watermark facet: a recorded disposition invalidates cached label /
-- search / shape reads, so the registry joins the watched relation set
-- (INSERT + TRUNCATE bump; UPDATE can never happen — the trigger forbids it,
-- and the trigger function's UPDATE branch is created anyway for symmetry).
-- ---------------------------------------------------------------------------
INSERT INTO spine_watermark (facet, row_count, closed_count, latest_instant)
VALUES ('publication_disposition',
        (SELECT count(*) FROM publication_disposition), 0,
        (SELECT max(decided_at) FROM publication_disposition));

CREATE TRIGGER spine_watermark_insert
  AFTER INSERT ON publication_disposition
  REFERENCING NEW TABLE AS new_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('decided_at', 'false');
CREATE TRIGGER spine_watermark_update
  AFTER UPDATE ON publication_disposition
  REFERENCING OLD TABLE AS old_rows NEW TABLE AS new_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('NULL', 'false');
CREATE TRIGGER spine_watermark_truncate
  AFTER TRUNCATE ON publication_disposition
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('NULL', 'false');

COMMIT;
