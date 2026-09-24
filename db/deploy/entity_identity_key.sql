-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:entity_identity_key to pg
-- P31.3 / ADR-110: the entity-identity guard (D-P30.4-3, formerly ENTITY-RACE-01).
--
-- The claim sink resolved a connector subject to an entity by check-then-insert on
-- entity_identifier, with no uniqueness on (scheme, value). Two concurrent sinks could
-- both miss the lookup and both mint an entity for one subject (the hosted
-- `camreg_camilo_schools:camilo_schools_cctv:1` pair). A plain
-- UNIQUE (scheme, value) on entity_identifier cannot be built: the historical
-- duplicate pairs are still there, and the spine is append-only, so they are never
-- deleted. Some schemes are not identity keys at all either (`us.state`, `fr.insee`
-- are jurisdiction attributes many entities share).
--
-- So the guard is a SIDE TABLE. There is one row per identity-bearing
-- (scheme, value), and its primary key is the uniqueness the database enforces. Every
-- guarded writer (db.identity_guard.resolve_identities) first claims the key with
-- INSERT ... ON CONFLICT DO NOTHING. Only the writer whose INSERT lands mints the
-- entity. A concurrent writer blocks on the uncommitted key, sees it once the first
-- transaction commits, and reuses that entity. The entity FK is DEFERRABLE INITIALLY
-- DEFERRED so the key can be claimed BEFORE its entity row exists, inside the same
-- transaction. A losing writer therefore never leaves an orphan entity behind.
--
-- Backfill: every existing `sig.connector.subject` identifier gets its key, pointing
-- at the EARLIEST-created entity carrying it (created_at, then entity_id). DISTINCT ON
-- picks exactly one entity per value, so the backfill cannot violate the key. The
-- later entity of a historical pair keeps its entity_identifier row and gets a
-- recorded same_as or distinct decision through the review queue (ADR-110). It is
-- never deleted or rewritten.
--
-- Locking: CREATE TABLE ... REFERENCES entity takes SHARE ROW EXCLUSIVE on `entity`
-- until COMMIT. That blocks entity INSERTs, but not reads, for the length of this
-- transaction. On the hosted spine it lasts seconds (measured in docs/build/runs/P31.3.md),
-- and the change is deployed when no ingest execution is running. Nothing else is
-- altered, so the change is additive and back-compatible.

BEGIN;

CREATE TABLE entity_identity_key (
  scheme      text NOT NULL,
  value       text NOT NULL,
  entity_id   uuid NOT NULL REFERENCES entity(entity_id) DEFERRABLE INITIALLY DEFERRED,
  keyed_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  backfilled  boolean NOT NULL DEFAULT false,   -- true = claimed by this change's backfill
  PRIMARY KEY (scheme, value)
);

-- Reverse lookup (which keys an entity holds), e.g. for the duplicate triage.
CREATE INDEX entity_identity_key_entity_idx ON entity_identity_key (entity_id);

INSERT INTO entity_identity_key (scheme, value, entity_id, backfilled)
SELECT DISTINCT ON (ei.value) ei.scheme, ei.value, ei.entity_id, true
  FROM entity_identifier ei
  JOIN entity e ON e.entity_id = ei.entity_id
 WHERE ei.scheme = 'sig.connector.subject'
 ORDER BY ei.value, e.created_at, ei.entity_id;

-- The backfill covers every existing subject identifier. Fail the deploy otherwise.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM entity_identifier ei
     WHERE ei.scheme = 'sig.connector.subject'
       AND NOT EXISTS (SELECT 1 FROM entity_identity_key k
                        WHERE k.scheme = ei.scheme AND k.value = ei.value)
  ) THEN
    RAISE EXCEPTION 'entity_identity_key backfill left a sig.connector.subject identifier unkeyed';
  END IF;
END
$$;

-- Append-only: a key is a recorded identity decision. It is never edited or removed.
-- A later correction is a same_as/distinct decision, not a key rewrite.
CREATE FUNCTION entity_identity_key_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'entity_identity_key rows are immutable (append-only, P1-P3); record a same_as/distinct decision instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entity_identity_key_immutable
  BEFORE UPDATE OR DELETE ON entity_identity_key
  FOR EACH ROW EXECUTE FUNCTION entity_identity_key_immutable();

-- The ingest role writes identities (entity + entity_identifier already); it may
-- claim keys, never change them.
GRANT SELECT, INSERT ON entity_identity_key TO sig_ingest;

COMMIT;
