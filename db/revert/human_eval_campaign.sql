-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:human_eval_campaign from pg
--
-- Drops ONLY the P32.9 eval surface. The operational review spine
-- (review_item/review_decision/review_campaign), the claim spine and every
-- earlier artifact are untouched — reverting deletes no history (the eval
-- tables are additive leaf tables referenced by nothing else; any rows they
-- held are eval records under the caller's explicit revert decision, and the
-- role objects survive so prior GRANTs never dangle).

BEGIN;

DROP VIEW IF EXISTS human_eval_adjudication_operational;
DROP VIEW IF EXISTS human_eval_label_operational;
DROP VIEW IF EXISTS human_eval_adjudication_released;
DROP VIEW IF EXISTS human_eval_label_released;

DROP TABLE IF EXISTS human_eval_release;
DROP TABLE IF EXISTS human_eval_adjudication;
DROP TABLE IF EXISTS human_eval_label;
-- packet before assignment: the packet's reviewer RLS policy references
-- human_eval_assignment in its EXISTS check (dependency).
DROP TABLE IF EXISTS human_eval_packet;
DROP TABLE IF EXISTS human_eval_assignment;
DROP TABLE IF EXISTS human_eval_attestation;
DROP TABLE IF EXISTS human_eval_sample;
DROP TABLE IF EXISTS human_eval_manifest;
DROP TABLE IF EXISTS human_eval_campaign;

DROP FUNCTION IF EXISTS human_eval_immutable();

COMMIT;
