-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:seed_vocab on pg
DO $$ BEGIN
  IF (SELECT count(*) FROM vocab_source_reliability) < 6 THEN RAISE EXCEPTION 'R scale not seeded'; END IF;
  IF (SELECT count(*) FROM vocab_object_type) < 9 THEN RAISE EXCEPTION 'object types not seeded'; END IF;
  IF (SELECT count(*) FROM vocab_entity_type) < 1 THEN RAISE EXCEPTION 'entity types not seeded'; END IF;
END $$;
