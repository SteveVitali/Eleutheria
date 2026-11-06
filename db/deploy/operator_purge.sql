-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:operator_purge to pg
--
-- P37.71 / ADR-181 (WV-06) + ADR-189 (WV-11) — the ONE DB-enforced, operator-only
-- purge function, the sole exception to SIG-STORE-011's append-only claim table,
-- scoped to material SIG must not hold at all (SIG-GOV-008; suppression,
-- SIG-GOV-007, stays the primitive for everything else).
--
--   1. sig_purge_operator — the NOLOGIN operator-held role. This change CREATES
--      it and grants it EXECUTE on the function and nothing else; membership is
--      NEVER granted by a migration or an agent — the operator provisions a
--      LOGIN member themselves (credential in Secret Manager only, HG-09) at
--      first use. Until then nothing can execute the function.
--
--   2. purge_tombstone — the append-only PUBLIC-safe tombstone: that a deletion
--      occurred, its category and its date — never the content (SIG-GOV-008's
--      tombstone clause stands). Joins spine_watermark so a recorded purge
--      invalidates cached reads.
--
--   3. purge_audit — the append-only INTERNAL audit record of the authorisation
--      and the act (ADR-181's compensating control): the in-ticket go it ran
--      under, the executing session/role, the claim ids removed and per-table
--      counts. Restricted roles only; never public.
--
--   4. sig_purge_claims() — SECURITY DEFINER. Refuses any caller that is not a
--      member of sig_purge_operator (a superuser or the owner bypasses EXECUTE
--      grants but never this check). Refuses a claim that any recorded decision
--      or cross-reference outside the set points at — those keep their audit
--      trail; suppression is the path for them. Deletes the claim bundle
--      (claim + claim_evidence + claim_qualifier + claim_lineage) inside one
--      transaction after writing tombstone + audit FIRST, with only USER
--      triggers disabled — foreign-key constraint triggers stay armed, so an
--      unenumerated dependent fails loudly instead of dangling.
--
-- Every other role and path stays append-only: claim_append_only_trg is never
-- edited, and the trigger-disabled window exists only inside this function's
-- transaction. tests/db/test_operator_purge.py proves it.

BEGIN;

-- 1. The operator-held role ----------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sig_purge_operator') THEN
    CREATE ROLE sig_purge_operator
      NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

COMMENT ON ROLE sig_purge_operator IS
  'P37.71/ADR-189: the operator-held role — the ONLY executor of '
  'sig_purge_claims(). NOLOGIN; membership is provisioned by the operator '
  '(Secret Manager credential, HG-09), never by a migration or an agent.';

-- 2. The public-safe tombstone -------------------------------------------------
CREATE TABLE purge_tombstone (
  tombstone_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tombstone_seq    bigint GENERATED ALWAYS AS IDENTITY,
  operation        text NOT NULL CHECK (operation IN ('deletion','purge')),
  target_kind      text NOT NULL CHECK (target_kind IN
                     ('claim','evidence_bytes','restricted_object',
                      'derived_artifact')),
  -- The closed category vocabulary — mirrors PURGE_CATEGORIES in
  -- db/src/db/operator_purge.py + ops/src/ops/operator_deletion.py.
  category         text NOT NULL CHECK (category IN
                     ('categorically_excluded','privacy_harm','legal_demand',
                      'security_concern','copyright_claim','rights_withdrawal')),
  occurred_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
  authority_ref    text NOT NULL,          -- the in-ticket go naming the material
  rows_removed     integer NOT NULL DEFAULT 1,
  decision_entry_id text                   -- the sig.editorial-decision/1 id
);

COMMENT ON TABLE purge_tombstone IS
  'P37.71/ADR-189 (SIG-GOV-008 tombstone clause): the append-only PUBLIC '
  'tombstone — that a deletion occurred, its category and its date, never its '
  'content. Written only inside sig_purge_claims(); read by the public/export '
  'read surfaces.';

CREATE FUNCTION purge_tombstone_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'purge_tombstone rows are immutable (append-only, P1-P3); a correction is a new row';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER purge_tombstone_immutable
  BEFORE UPDATE OR DELETE ON purge_tombstone
  FOR EACH ROW EXECUTE FUNCTION purge_tombstone_immutable();

-- Public-safe by construction (category + date + count — no content, no ids):
GRANT SELECT ON purge_tombstone TO sig_read_public, sig_export;
REVOKE INSERT, UPDATE, DELETE ON purge_tombstone
  FROM sig_read_public, sig_export, sig_materialize, sig_ingest,
       sig_read_restricted, sig_read_sealed;

-- spine_watermark facet: a recorded purge invalidates cached reads.
INSERT INTO spine_watermark (facet, row_count, closed_count, latest_instant)
VALUES ('purge_tombstone',
        (SELECT count(*) FROM purge_tombstone), 0,
        (SELECT max(occurred_at) FROM purge_tombstone));

CREATE TRIGGER spine_watermark_insert
  AFTER INSERT ON purge_tombstone
  REFERENCING NEW TABLE AS new_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('occurred_at', 'false');
CREATE TRIGGER spine_watermark_update
  AFTER UPDATE ON purge_tombstone
  REFERENCING NEW TABLE AS new_rows OLD TABLE AS old_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('occurred_at', 'false');
CREATE TRIGGER spine_watermark_truncate
  AFTER TRUNCATE ON purge_tombstone
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('NULL', 'false');

-- 3. The internal audit record -------------------------------------------------
CREATE TABLE purge_audit (
  audit_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_seq      bigint GENERATED ALWAYS AS IDENTITY,
  tombstone_id   uuid NOT NULL REFERENCES purge_tombstone(tombstone_id),
  operation      text NOT NULL,
  category       text NOT NULL,
  authority_ref  text NOT NULL,            -- the in-ticket go (verbatim ref)
  executed_by    text NOT NULL,            -- session_user at execution
  executed_role  text NOT NULL,            -- current_user (the operator role)
  executed_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  claim_ids      uuid[] NOT NULL DEFAULT '{}',
  detail         jsonb NOT NULL DEFAULT '{}'::jsonb  -- per-table counts + misses
);

COMMENT ON TABLE purge_audit IS
  'P37.71/ADR-181 compensating control: the append-only INTERNAL audit record '
  'of the authorisation and the act — restricted roles only, never public.';

CREATE FUNCTION purge_audit_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'purge_audit rows are immutable (append-only, P1-P3); a correction is a new row';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER purge_audit_immutable
  BEFORE UPDATE OR DELETE ON purge_audit
  FOR EACH ROW EXECUTE FUNCTION purge_audit_immutable();

GRANT SELECT ON purge_audit TO sig_read_sealed, sig_read_restricted;
REVOKE INSERT, UPDATE, DELETE ON purge_audit
  FROM sig_read_public, sig_export, sig_materialize, sig_ingest,
       sig_read_restricted, sig_read_sealed;

-- 4. The purge function --------------------------------------------------------
CREATE FUNCTION sig_purge_claims(
  p_claim_ids          uuid[],
  p_category           text,
  p_authority_ref      text,
  p_decision_entry_id  text DEFAULT NULL
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $func$
DECLARE
  ids        uuid[];
  missing    uuid[];
  blockers   text[];
  tomb       uuid;
  invoking   text;
  n_evidence integer := 0;
  n_qual     integer := 0;
  n_lineage  integer := 0;
BEGIN
  -- (a) Only the operator-held role may run this. The EXECUTE grant is the
  --     first line; this check is the second — and it names the INVOKING
  --     role (the SET ROLE value, else the session login), not current_user,
  --     which inside SECURITY DEFINER is always the function owner. Strict
  --     equality holds even for a superuser session: only a member may
  --     SET ROLE to sig_purge_operator, and the role itself is NOLOGIN, so
  --     'sig_purge_operator' can never be a login name. The operator runs
  --     it as their provisioned login + SET ROLE sig_purge_operator.
  invoking := coalesce(nullif(current_setting('role', true), 'none'), session_user);
  IF invoking <> 'sig_purge_operator' THEN
    RAISE EXCEPTION
      'purge refused: the invoking role % is not sig_purge_operator — '
      'connect as the operator login and SET ROLE sig_purge_operator',
      invoking
      USING ERRCODE = 'insufficient_privilege';
  END IF;

  -- (b) Inputs are required and scoped — a purge without a named material set
  --     or a named go is refused.
  IF p_claim_ids IS NULL OR cardinality(p_claim_ids) = 0 THEN
    RAISE EXCEPTION 'purge refused: no claim ids named'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF p_category IS NULL OR p_category NOT IN
       ('categorically_excluded','privacy_harm','legal_demand',
        'security_concern','copyright_claim','rights_withdrawal') THEN
    RAISE EXCEPTION 'purge refused: category % is not in the closed vocabulary',
      p_category USING ERRCODE = 'restrict_violation';
  END IF;
  IF p_authority_ref IS NULL OR btrim(p_authority_ref) = '' THEN
    RAISE EXCEPTION 'purge refused: the in-ticket go must be named'
      USING ERRCODE = 'restrict_violation';
  END IF;

  SELECT array_agg(DISTINCT cid ORDER BY cid)
    INTO ids
    FROM unnest(p_claim_ids) AS cid;

  SELECT array_agg(cid ORDER BY cid)
    INTO missing
    FROM unnest(ids) AS cid
   WHERE NOT EXISTS (SELECT 1 FROM claim c WHERE c.claim_id = cid);

  -- (c) Blocker scan: a claim any recorded decision or cross-reference outside
  --     the set points at is refused — the decision's audit trail stands;
  --     suppression (SIG-GOV-007) is the path for it. Intra-set links are fine:
  --     a claim and its correction may purge together under one go.
  SELECT array_agg(b.relation ORDER BY b.relation)
    INTO blockers
    FROM (
      SELECT 'claim.revises_claim' AS relation, 1 AS ord
       WHERE EXISTS (SELECT 1 FROM claim c
                      WHERE c.revises_claim = ANY(ids)
                        AND NOT (c.claim_id = ANY(ids)))
      UNION ALL
      SELECT 'claim.retraction_of', 2
       WHERE EXISTS (SELECT 1 FROM claim c
                      WHERE c.retraction_of = ANY(ids)
                        AND NOT (c.claim_id = ANY(ids)))
      UNION ALL
      SELECT 'claim.derived_from_claim_ids', 3
       WHERE EXISTS (SELECT 1 FROM claim c
                      WHERE c.derived_from_claim_ids && ids
                        AND NOT (c.claim_id = ANY(ids)))
      UNION ALL
      SELECT 'claim_lineage.derived_from_claim_ids', 4
       WHERE EXISTS (SELECT 1 FROM claim_lineage l
                      WHERE l.derived_from_claim_ids && ids
                        AND NOT (l.claim_id = ANY(ids)))
      UNION ALL
      SELECT 'resolution', 5
       WHERE EXISTS (SELECT 1 FROM resolution r
                      WHERE r.winning_claim = ANY(ids)
                         OR r.considered_claims && ids
                         OR r.dissenting_claims && ids)
      UNION ALL
      SELECT 'relationship.evidence_claim', 6
       WHERE EXISTS (SELECT 1 FROM relationship x
                      WHERE x.evidence_claim = ANY(ids))
      UNION ALL
      SELECT 'entity_role', 7
       WHERE EXISTS (SELECT 1 FROM entity_role e
                      WHERE e.evidence_claim = ANY(ids)
                         OR e.superseded_by_claim = ANY(ids))
      UNION ALL
      SELECT 'organization_relation.evidence_claim', 8
       WHERE EXISTS (SELECT 1 FROM organization_relation o
                      WHERE o.evidence_claim = ANY(ids))
      UNION ALL
      SELECT 'entity_identifier.asserted_by_claim', 9
       WHERE EXISTS (SELECT 1 FROM entity_identifier i
                      WHERE i.asserted_by_claim = ANY(ids))
      UNION ALL
      SELECT 'jurisdiction.boundary_source_claim', 10
       WHERE EXISTS (SELECT 1 FROM jurisdiction j
                      WHERE j.boundary_source_claim = ANY(ids))
      UNION ALL
      SELECT 'person.public_interest_basis_claim', 11
       WHERE EXISTS (SELECT 1 FROM person p
                      WHERE p.public_interest_basis_claim = ANY(ids))
      UNION ALL
      SELECT 'publication_disposition.evidence_claim_id', 12
       WHERE EXISTS (SELECT 1 FROM publication_disposition d
                      WHERE d.evidence_claim_id = ANY(ids))
      UNION ALL
      SELECT 'intake.application', 13
       WHERE EXISTS (SELECT 1 FROM intake.application a
                      WHERE a.target_claim_id = ANY(ids)
                         OR a.result_claim_id = ANY(ids))
      UNION ALL
      SELECT 'recovery_application', 14
       WHERE EXISTS (SELECT 1 FROM recovery_application ra
                      WHERE ra.claim_id = ANY(ids)
                         OR ra.result_claim_id = ANY(ids))
    ) AS b;

  IF blockers IS NOT NULL AND cardinality(blockers) > 0 THEN
    RAISE EXCEPTION
      'purge refused: the named claims are referenced by recorded decisions — % (suppress, do not purge)',
      array_to_string(blockers, ', ')
      USING ERRCODE = 'restrict_violation';
  END IF;

  -- (d) Counts BEFORE the delete: tombstone + audit rows land first inside the
  --     same transaction — if the delete fails, everything rolls back together.
  SELECT count(*) INTO n_lineage
    FROM claim_lineage l WHERE l.claim_id = ANY(ids);
  SELECT count(*) INTO n_evidence
    FROM claim_evidence e WHERE e.claim_id = ANY(ids);
  SELECT count(*) INTO n_qual
    FROM claim_qualifier q WHERE q.claim_id = ANY(ids);

  INSERT INTO purge_tombstone (operation, target_kind, category, authority_ref,
                               rows_removed, decision_entry_id)
  VALUES ('purge', 'claim', p_category, p_authority_ref,
          cardinality(ids) - COALESCE(cardinality(missing), 0),
          p_decision_entry_id)
  RETURNING tombstone_id INTO tomb;

  INSERT INTO purge_audit (tombstone_id, operation, category, authority_ref,
                           executed_by, executed_role, claim_ids, detail)
  VALUES (tomb, 'purge', p_category, p_authority_ref,
          session_user, invoking, ids,
          jsonb_build_object(
            'claim', cardinality(ids) - COALESCE(cardinality(missing), 0),
            'claim_evidence', n_evidence,
            'claim_qualifier', n_qual,
            'claim_lineage', n_lineage,
            'missing', COALESCE(to_jsonb(missing), '[]'::jsonb)));

  -- (e) The sanctioned delete. USER triggers only — FK constraint triggers
  --     stay armed, so a missed dependent still fails the statement.
  ALTER TABLE claim DISABLE TRIGGER USER;
  ALTER TABLE claim_evidence DISABLE TRIGGER USER;
  ALTER TABLE claim_qualifier DISABLE TRIGGER USER;
  ALTER TABLE claim_lineage DISABLE TRIGGER USER;

  DELETE FROM claim_lineage WHERE claim_id = ANY(ids);
  DELETE FROM claim_evidence WHERE claim_id = ANY(ids);
  DELETE FROM claim_qualifier WHERE claim_id = ANY(ids);
  DELETE FROM claim WHERE claim_id = ANY(ids);

  ALTER TABLE claim ENABLE TRIGGER USER;
  ALTER TABLE claim_evidence ENABLE TRIGGER USER;
  ALTER TABLE claim_qualifier ENABLE TRIGGER USER;
  ALTER TABLE claim_lineage ENABLE TRIGGER USER;

  RETURN tomb;
END;
$func$;

COMMENT ON FUNCTION sig_purge_claims(uuid[], text, text, text) IS
  'P37.71/ADR-189 (WV-11): the ONE operator-only purge function — the sole '
  'exception to SIG-STORE-011. Executable only by sig_purge_operator; scope '
  'SIG-GOV-008; every use needs the operator''s in-ticket go naming the '
  'material and leaves a tombstone + audit + public log entry.';

REVOKE ALL ON FUNCTION sig_purge_claims(uuid[], text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sig_purge_claims(uuid[], text, text, text)
  TO sig_purge_operator;

COMMIT;
