-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:partner_org_identity_key to pg
-- P31.5 / ADR-112: the partner-organisation schemes join the identity guard.
--
-- A connector that names a partner (a contract's buyer or seller, a funding
-- instrument's funder or recipient, an accountability event's organisations, a
-- camera's operator) now also writes an entity-ref claim whose object is an
-- `organization` entity. That entity is minted through the identity guard
-- (db.identity_guard, ADR-110), keyed on one of the partner schemes below. ADR-110's
-- revisit trigger (d) requires a new guarded scheme to ship with the backfill of its
-- existing identifiers in the same change, so that the guard adopts a legacy
-- identifier instead of minting a second entity for it. That backfill is this change.
--
-- The schemes are kept byte-identical to db.identity_guard.PARTNER_ORG_SCHEMES
-- (tests/db/test_partner_entity_refs.py pins the two together):
--   sig.org.name          the normalized-name identifier (normalize_org_name)
--   gleif.lei, us.sam.uei, dnb.duns, us.dla.cage, us.cgac.agency_code
--                         external ids that each name exactly one organisation
-- FIPS is deliberately NOT keyed: a place code is shared by every body in the place.
--
-- On today's spines no identifier carries these schemes, so the backfill keys 0 rows;
-- it is written so the change is correct on any spine. It follows entity_identity_key:
-- one key per (scheme, value), pointing at the EARLIEST-created entity that carries
-- the identifier, so it cannot violate the primary key. Additive: no table, column or
-- existing row changes, and no lock beyond the INSERT into entity_identity_key.

BEGIN;

INSERT INTO entity_identity_key (scheme, value, entity_id, backfilled)
SELECT DISTINCT ON (ei.scheme, ei.value) ei.scheme, ei.value, ei.entity_id, true
  FROM entity_identifier ei
  JOIN entity e ON e.entity_id = ei.entity_id
 WHERE ei.scheme IN ('sig.org.name', 'gleif.lei', 'us.sam.uei', 'dnb.duns',
                     'us.dla.cage', 'us.cgac.agency_code')
 ORDER BY ei.scheme, ei.value, e.created_at, ei.entity_id
ON CONFLICT (scheme, value) DO NOTHING;

-- The backfill covers every existing partner identifier. Fail the deploy otherwise.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM entity_identifier ei
     WHERE ei.scheme IN ('sig.org.name', 'gleif.lei', 'us.sam.uei', 'dnb.duns',
                         'us.dla.cage', 'us.cgac.agency_code')
       AND NOT EXISTS (SELECT 1 FROM entity_identity_key k
                        WHERE k.scheme = ei.scheme AND k.value = ei.value)
  ) THEN
    RAISE EXCEPTION 'partner_org_identity_key backfill left a partner identifier unkeyed';
  END IF;
END
$$;

COMMIT;
