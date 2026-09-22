-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:review_queue to pg
-- P19.5 / ADR-061 (moved from P19.4 / ADR-059 §6 by the size guard): the PG backend
-- for the internal review queue (§14.6, §25, §27; SIG-IDENT-020/025/026). Until now
-- the ReviewQueue was JSON-serialisable value objects only (the P05.1-deferred
-- persistence); this change gives the tier-4/5 probabilistic-ER matches (and, later,
-- model-assisted extractions) a durable home so `sig-resolution match --dsn` can
-- persist proposals read from the PG spine and `sig-resolution review decide --dsn`
-- can record human adjudications.
--
-- Two tables:
--   * `review_item`     — the pending proposal (idempotent: matching the same
--     candidate set twice re-proposes the same item_id, ON CONFLICT DO NOTHING).
--   * `review_decision` — the APPEND-ONLY adjudication log. One row per `decide`
--     call; deciding the same item again appends a new row (history on repeat),
--     never an UPDATE/DELETE. `decided_at` is set BY THE DATABASE (P1–P3,
--     SIG-IDENT-026). A model-assisted decision carries the model/prompt provenance.
--
-- Additive & back-compatible: new tables only; the JSONL/in-memory ReviewQueue
-- remains the default for every existing test. No existing object is altered.

BEGIN;

CREATE TABLE review_item (
  item_id         text PRIMARY KEY,               -- deterministic proposal id (er_match:… / model_extraction:…)
  kind            text NOT NULL,                  -- er_match | model_extraction
  summary         text NOT NULL,
  confidence      jsonb NOT NULL DEFAULT '[]',    -- the per-comparison decomposition (SIG-IDENT-025)
  overall_weight  double precision,               -- match weight for an ER match; NULL for an extraction
  model_id        text,                           -- set for model-assisted items (SIG-IDENT-026)
  prompt_version  text,
  payload         jsonb NOT NULL DEFAULT '{}',
  created_at      timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE review_decision (
  decision_id     uuid PRIMARY KEY DEFAULT uuidv7(),
  item_id         text NOT NULL REFERENCES review_item(item_id),
  decision        text NOT NULL CHECK (decision IN ('accept', 'reject')),
  reviewer        text NOT NULL,                  -- the human adjudicator (SIG-IDENT-026)
  model_id        text,                           -- copied from the item for model-assisted proposals
  prompt_version  text,
  rationale       text,                           -- an optional note; never an authority (SIG-LLM-001)
  decided_at      timestamptz NOT NULL DEFAULT clock_timestamp()  -- set by the DB, never the caller
);

-- Read path for the queue: the pending items and the decision history per item.
CREATE INDEX review_decision_item_idx ON review_decision (item_id, decided_at);

COMMIT;
