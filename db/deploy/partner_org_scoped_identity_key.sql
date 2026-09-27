-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:partner_org_scoped_identity_key to pg
-- P32.3 / ADR-122 (SIG-TRUST-004): the scope-qualified partner-name scheme joins
-- the identity guard.
--
-- The legacy `sig.org.name` key is GLOBAL: two records normalising to the same
-- name union into one organisation even across jurisdictions. ADR-122 replaces
-- it for new mints with `sig.org.name_scoped`, whose value is
-- `jur:<jurisdiction>|<name>` when the jurisdiction is evidenced else
-- `src:<source>|<name>` — identical names in different scopes never collide, so
-- nothing auto-unions (resolution.partner_identity.scoped_name_key pins the
-- format; tests/db/test_partner_entity_refs.py pins the scheme list to
-- db.identity_guard.PARTNER_ORG_SCHEMES).
--
-- ADR-110's revisit trigger (d) requires a new guarded scheme to ship with the
-- backfill of its existing identifiers in the same change. No
-- `sig.org.name_scoped` identifier exists on any spine yet (the scheme first
-- mints in this ticket), so the backfill keys 0 rows; it is written so the
-- change is correct on any spine. Additive: no table, column or existing row
-- changes; the legacy `sig.org.name` rows are NOT re-keyed — each is repaired by
-- a recorded identity disposition, informed by the `partner-name-audit` dry-run
-- report, never by an in-place rewrite (SIG-TRUST-004).

BEGIN;

INSERT INTO entity_identity_key (scheme, value, entity_id, backfilled)
SELECT DISTINCT ON (ei.scheme, ei.value) ei.scheme, ei.value, ei.entity_id, true
  FROM entity_identifier ei
  JOIN entity e ON e.entity_id = ei.entity_id
 WHERE ei.scheme = 'sig.org.name_scoped'
 ORDER BY ei.scheme, ei.value, e.created_at, ei.entity_id
ON CONFLICT (scheme, value) DO NOTHING;

-- The backfill covers every existing scoped-name identifier. Fail otherwise.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM entity_identifier ei
     WHERE ei.scheme = 'sig.org.name_scoped'
       AND NOT EXISTS (SELECT 1 FROM entity_identity_key k
                        WHERE k.scheme = ei.scheme AND k.value = ei.value)
  ) THEN
    RAISE EXCEPTION 'partner_org_scoped_identity_key backfill left an identifier unkeyed';
  END IF;
END
$$;

COMMIT;
