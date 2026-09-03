-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:domain_entities on pg
SELECT entity_id FROM jurisdiction WHERE false;
SELECT entity_id FROM organization WHERE false;
SELECT entity_id FROM person WHERE false;
SELECT technology_id FROM technology WHERE false;
SELECT entity_id FROM physical_asset WHERE false;
SELECT entity_id FROM records_request WHERE false;
