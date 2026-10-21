-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:role_edges to pg
-- P35.26 / R11-L3-CP7 (SIG-TRUST-003, SIG-ONTO-028, SIG-ONTO-029/030/032,
-- SIG-EPIS-029; ADR-112/ADR-122 posture kept): the role/time backend for
-- materialized edges.
--
-- What this change lands:
--
-- 1. `entity_role` is reshaped from the spec-§C.5 sketch into the real
--    role-edge table. The sketch table has never had a writer or a reader
--    (P32.3 registered the role taxonomy; nothing materialized it — L2 is
--    zero rows on hosted), so the composite natural PK `(entity_id, actor_id,
--    role, valid_period)` is replaced by a surrogate `entity_role_id` PK:
--    `actor_id` must be nullable because the explicit-unknown marker state
--    (`role='operator_unknown'`, actor NULL) is a first-class row, and a PK
--    column cannot be NULL. The natural uniqueness moves to `input_digest`
--    (partial unique index — same posture as `relationship` /
--    `entity_type_decision`). Recorded in ADR-214.
--
--    Added columns mirror the relationship/claim temporal vocabulary:
--      valid_from_kind / valid_to_kind — closed kind vocabulary, extended
--        with `undated` (the explicit no-evidenced-date marker — GQ-15 /
--        SIG-ONTO-030; never a fabricated bound);
--      observed_at — the latest evidenced observation date, NULL when the
--        evidence is undated;
--      asserted_by — the asserting entity (the same provenance field claim
--        and relationship carry);
--      supersedes / superseded_by_claim — the recorded succession chain
--        (SIG-EPIS-029): when a later claim evidences a role change the prior
--        edge's valid_to is set by the correcting claim and the rows link;
--      input_digest — append-only idempotency (a re-materialization of an
--        unchanged claim set is +0);
--      sys_period — belief time (the sanctioned temporal mutation closes it
--        on supersession — never an in-place valid-time edit).
--
--    CHECKs: the role vocabulary is CLOSED (the fourteen §12.4 roles ∪ the
--    OrganizationRole taxonomy ∪ `maintainer` ∪ `operator_unknown` — the
--    list of truth is `db.organization_roles.EDGE_ROLE_VOCABULARY` and the
--    unit suite asserts parity); `actor_id` is NULL only for the
--    `operator_unknown` marker; epoch-zero is REJECTED at write
--    (`NOT VALID` — binds new writes while pre-existing rows, if any, wait a
--    named VALIDATE follow-up; the same posture as
--    `entity_typing_mobility_check`). A `1970-01-01` bound or observation is
--    a placeholder, never a date (SIG-ONTO-030).
--
-- 2. `relationship` gains `supersedes` (the same recorded succession link)
--    plus the epoch-zero NOT VALID CHECKs on `valid_period`/`observed_at` —
--    the P28.2 materializer's 1970-01-01 undated fallback is removed and the
--    constraint guards the table for any future writer.
--
-- 3. Two SECURITY DEFINER close functions mirror
--    `close_superseded_resolutions` (resolution_supersede): they perform the
--    ONE temporal mutation the model sanctions — closing a live row's
--    sys_period when a superseding row lands. Callers never need UPDATE on
--    the edge tables; `sig_materialize` keeps its INSERT-only posture plus
--    EXECUTE on the closures.
--
-- 4. `sig_materialize` reads+writes `entity_role` directly: the table is off
--    the §37 public read surface (same posture as `relationship` — read by
--    the materializer, never the public reader).

BEGIN;

-- --- entity_role reshape ----------------------------------------------------

ALTER TABLE entity_role DROP CONSTRAINT entity_role_pkey;

ALTER TABLE entity_role
  ALTER COLUMN actor_id DROP NOT NULL,
  ADD COLUMN entity_role_id uuid NOT NULL DEFAULT uuidv7(),
  ADD COLUMN valid_from_kind text NOT NULL DEFAULT 'unknown',
  ADD COLUMN valid_to_kind text NOT NULL DEFAULT 'unknown',
  ADD COLUMN observed_at timestamptz,
  ADD COLUMN asserted_by uuid REFERENCES entity(entity_id),
  ADD COLUMN supersedes uuid,
  ADD COLUMN superseded_by_claim uuid REFERENCES claim(claim_id),
  ADD COLUMN input_digest text,
  ADD COLUMN sys_period tstzrange NOT NULL
          DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),
  ADD CONSTRAINT entity_role_pkey PRIMARY KEY (entity_role_id),
  ADD CONSTRAINT entity_role_actor_required_for_roles
    CHECK (actor_id IS NOT NULL OR role = 'operator_unknown'),
  ADD CONSTRAINT entity_role_closed_vocabulary CHECK (role IN (
    -- db.organization_roles.EDGE_ROLE_VOCABULARY — the Python module is the
    -- list of truth; the unit suite asserts this literal set stays in sync.
    'operator', 'operator_unknown',
    'owner', 'purchaser', 'buyer',
    'host', 'maintainer', 'installer',
    'vendor', 'platform_provider', 'prime',
    'funder',
    'access', 'accessor_read',
    'recipient', 'alert_recipient',
    'regulated', 'regulator',
    'auditor',
    'participant',
    'publisher',
    'data_controller', 'data_processor',
    'searcher'
  )),
  ADD CONSTRAINT entity_role_bound_kinds CHECK (
    valid_from_kind IN ('exact','ongoing','unknown','before','after','never','undated')
    AND valid_to_kind IN ('exact','ongoing','unknown','before','after','never','undated')
  ),
  -- Epoch-zero is a placeholder, never a date (SIG-ONTO-030). NOT VALID binds
  -- every new write now; pre-existing rows wait the named VALIDATE follow-up
  -- (the same posture entity_typing_mobility_check took).
  ADD CONSTRAINT entity_role_no_epoch_zero
    CHECK (lower(valid_period) IS NULL
           OR lower(valid_period) <> '1970-01-01 00:00:00+00'::timestamptz) NOT VALID,
  ADD CONSTRAINT entity_role_observed_no_epoch_zero
    CHECK (observed_at IS NULL
           OR observed_at <> '1970-01-01 00:00:00+00'::timestamptz) NOT VALID,
  ADD CONSTRAINT entity_role_supersedes_fkey
    FOREIGN KEY (supersedes) REFERENCES entity_role(entity_role_id);

CREATE UNIQUE INDEX entity_role_input_digest_key
  ON entity_role(input_digest) WHERE input_digest IS NOT NULL;

-- The materializer + the role-state readers walk live rows per subject/role.
CREATE INDEX entity_role_live_subject_idx
  ON entity_role(entity_id, role) WHERE upper_inf(sys_period);

GRANT SELECT, INSERT ON entity_role TO sig_materialize;

-- --- relationship: the succession link + epoch-zero guard --------------------

ALTER TABLE relationship
  ADD COLUMN supersedes uuid REFERENCES relationship(relationship_id),
  ADD CONSTRAINT relationship_no_epoch_zero
    CHECK (lower(valid_period) IS NULL
           OR lower(valid_period) <> '1970-01-01 00:00:00+00'::timestamptz) NOT VALID,
  ADD CONSTRAINT relationship_observed_no_epoch_zero
    CHECK (observed_at IS NULL
           OR observed_at <> '1970-01-01 00:00:00+00'::timestamptz) NOT VALID;

-- --- the sanctioned temporal mutations ---------------------------------------

-- Close the sys_period of live entity_role rows a superseding materialization
-- replaces — the belief-time interval ends; the row stays as history (readers
-- filter upper_inf(sys_period) for the current edge set). Mirrors
-- close_superseded_resolutions: SECURITY DEFINER so the caller keeps an
-- INSERT-only posture on the table itself.
CREATE FUNCTION close_superseded_entity_roles(p_role_ids uuid[])
RETURNS TABLE(entity_role_id uuid, action text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $fn$
BEGIN
  RETURN QUERY
    WITH closed AS (
      UPDATE public.entity_role r
         SET sys_period = pg_catalog.tstzrange(
               pg_catalog.lower(r.sys_period), pg_catalog.clock_timestamp(), '[)')
       WHERE r.entity_role_id = ANY(p_role_ids)
         AND pg_catalog.upper_inf(r.sys_period)
     RETURNING r.entity_role_id
    )
    SELECT c.entity_role_id, 'closed'::text FROM closed c;
END;
$fn$;

REVOKE ALL ON FUNCTION close_superseded_entity_roles(uuid[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION close_superseded_entity_roles(uuid[]) TO sig_materialize;

-- The same sanctioned closure for relationship edges: a changed input digest
-- lands as a superseding row and the prior live row's sys_period closes —
-- 0 live duplicate edges per (from, to, kind) (GQ-15).
CREATE FUNCTION close_superseded_relationships(p_relationship_ids uuid[])
RETURNS TABLE(relationship_id uuid, action text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $fn$
BEGIN
  RETURN QUERY
    WITH closed AS (
      UPDATE public.relationship r
         SET sys_period = pg_catalog.tstzrange(
               pg_catalog.lower(r.sys_period), pg_catalog.clock_timestamp(), '[)')
       WHERE r.relationship_id = ANY(p_relationship_ids)
         AND pg_catalog.upper_inf(r.sys_period)
     RETURNING r.relationship_id
    )
    SELECT c.relationship_id, 'closed'::text FROM closed c;
END;
$fn$;

REVOKE ALL ON FUNCTION close_superseded_relationships(uuid[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION close_superseded_relationships(uuid[]) TO sig_materialize;

COMMIT;
