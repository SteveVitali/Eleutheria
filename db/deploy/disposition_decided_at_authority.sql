-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:disposition_decided_at_authority to pg
--
-- P32.10a (SIG-TRUST-006 defect repair inside the ADR-124 publication-eligibility
-- family — no new requirement id, no ADR amendment): ONE clock authority for
-- publication_disposition.decided_at — the database's.
--
-- The defect: `policy.eligibility.new_disposition` stamped `decided_at`
-- host-side (`datetime.now(UTC)`) and `db.dispositions.record_disposition`
-- always sent it on the INSERT, while the shared eligibility fragments filter
-- `d.decided_at <= clock_timestamp()` evaluated on the SERVER clock. Under any
-- skew where the writer's clock runs ahead of the database's (the Docker
-- Desktop VM clock lag that intermittently red'd
-- tests/db/test_publication_dispositions.py — P32.10's suite evidence), a
-- just-recorded disposition is transiently future-dated and invisible to the
-- selector.
--
-- The column already carried `DEFAULT clock_timestamp()` from
-- `publication_dispositions`; the writer never let it apply. This change
-- re-asserts the default so the authority cannot silently drift, and records
-- the contract on the column itself. The writer side (`record_disposition`)
-- now omits `decided_at` for normal writes — an explicit value is accepted
-- only as a documented replay/migration input (recorded history, never "now").

BEGIN;

ALTER TABLE publication_disposition
  ALTER COLUMN decided_at SET DEFAULT clock_timestamp();

COMMENT ON COLUMN publication_disposition.decided_at IS
  'P32.10a (ADR-124 family): the decision instant is stamped by the DATABASE '
  '(DEFAULT clock_timestamp()) — the single clock authority the eligibility '
  'fragments evaluate (decided_at <= clock_timestamp()). Writers omit the '
  'column; an explicit value is a replay/migration input for recorded history '
  'only — the host clock never decides a live write.';

COMMIT;
