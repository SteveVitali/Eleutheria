-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:partner_org_identity_key on pg

BEGIN;

-- Every partner-scheme identifier is keyed by the guard.
SELECT 1 / (CASE WHEN NOT EXISTS (
    SELECT 1 FROM entity_identifier ei
     WHERE ei.scheme IN ('sig.org.name', 'gleif.lei', 'us.sam.uei', 'dnb.duns',
                         'us.dla.cage', 'us.cgac.agency_code')
       AND NOT EXISTS (SELECT 1 FROM entity_identity_key k
                        WHERE k.scheme = ei.scheme AND k.value = ei.value)
  ) THEN 1 ELSE 0 END);

ROLLBACK;
