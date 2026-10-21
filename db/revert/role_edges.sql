-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:role_edges from pg
-- Restores the spec-§C.5 sketch shape of entity_role (the table carries no
-- data in any deployed environment — the reshape was additive-safe) and the
-- pre-P35.26 relationship surface.

BEGIN;

REVOKE EXECUTE ON FUNCTION close_superseded_relationships(uuid[])
  FROM sig_materialize;
REVOKE EXECUTE ON FUNCTION close_superseded_entity_roles(uuid[])
  FROM sig_materialize;
DROP FUNCTION close_superseded_relationships(uuid[]);
DROP FUNCTION close_superseded_entity_roles(uuid[]);

ALTER TABLE relationship
  DROP CONSTRAINT relationship_no_epoch_zero,
  DROP CONSTRAINT relationship_observed_no_epoch_zero,
  DROP COLUMN supersedes;

REVOKE SELECT, INSERT ON entity_role FROM sig_materialize;

DROP INDEX entity_role_live_subject_idx;
DROP INDEX entity_role_input_digest_key;

ALTER TABLE entity_role
  DROP CONSTRAINT entity_role_supersedes_fkey,
  DROP CONSTRAINT entity_role_pkey,
  DROP CONSTRAINT entity_role_actor_required_for_roles,
  DROP CONSTRAINT entity_role_closed_vocabulary,
  DROP CONSTRAINT entity_role_bound_kinds,
  DROP CONSTRAINT entity_role_no_epoch_zero,
  DROP CONSTRAINT entity_role_observed_no_epoch_zero,
  ALTER COLUMN actor_id SET NOT NULL,
  DROP COLUMN entity_role_id,
  DROP COLUMN valid_from_kind,
  DROP COLUMN valid_to_kind,
  DROP COLUMN observed_at,
  DROP COLUMN asserted_by,
  DROP COLUMN supersedes,
  DROP COLUMN superseded_by_claim,
  DROP COLUMN input_digest,
  DROP COLUMN sys_period,
  ADD CONSTRAINT entity_role_pkey PRIMARY KEY (entity_id, actor_id, role, valid_period);

COMMIT;
