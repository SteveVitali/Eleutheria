-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_enums to pg
-- The enum types the claim (§16.2) and resolution (§16.4) tables use.

BEGIN;

CREATE TYPE value_kind    AS ENUM ('value', 'somevalue', 'novalue');
CREATE TYPE claim_rank    AS ENUM ('preferred', 'normal', 'deprecated');
CREATE TYPE review_status AS ENUM ('unreviewed','machine_accepted','human_verified','disputed','retracted');

COMMIT;
