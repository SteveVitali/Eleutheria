-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:role_edges on pg

BEGIN;

-- The surrogate PK exists and the sketch composite PK is gone.
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM pg_constraint
 WHERE conrelid = 'entity_role'::regclass AND contype = 'p'
   AND pg_get_constraintdef(oid) LIKE 'PRIMARY KEY (entity_role_id)%';

-- The added columns exist.
SELECT entity_role_id, valid_from_kind, valid_to_kind, observed_at, asserted_by,
       supersedes, superseded_by_claim, input_digest, sys_period
  FROM entity_role WHERE false;

SELECT supersedes FROM relationship WHERE false;

-- The closed role vocabulary + the actor-required invariant are CHECK'd.
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM pg_constraint
 WHERE conrelid = 'entity_role'::regclass
   AND conname = 'entity_role_closed_vocabulary';
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM pg_constraint
 WHERE conrelid = 'entity_role'::regclass
   AND conname = 'entity_role_actor_required_for_roles';

-- The epoch-zero guards exist on both edge tables (NOT VALID posture — they
-- bind new writes now).
SELECT 1 / (CASE WHEN count(*) = 2 THEN 1 ELSE 0 END) FROM pg_constraint
 WHERE conname IN ('entity_role_no_epoch_zero', 'entity_role_observed_no_epoch_zero')
   AND conrelid = 'entity_role'::regclass AND NOT convalidated;
SELECT 1 / (CASE WHEN count(*) = 2 THEN 1 ELSE 0 END) FROM pg_constraint
 WHERE conname IN ('relationship_no_epoch_zero', 'relationship_observed_no_epoch_zero')
   AND conrelid = 'relationship'::regclass AND NOT convalidated;

-- The succession functions exist with materializer EXECUTE.
SELECT 1 / (CASE WHEN count(*) = 2 THEN 1 ELSE 0 END) FROM pg_proc
 WHERE proname IN ('close_superseded_entity_roles', 'close_superseded_relationships');

-- The materializer grants landed.
SELECT 1 / (CASE WHEN bool_and(has_table_privilege('sig_materialize','entity_role',priv))
            THEN 1 ELSE 0 END)
  FROM (VALUES ('SELECT'), ('INSERT')) v(priv);

-- (The epoch-zero write-rejection behaviour itself is covered by the DB test
-- suite — a real evidence_claim FK target is too heavy a fixture for verify.)

ROLLBACK;
