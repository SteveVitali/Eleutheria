-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim to pg
-- §16.2: the L1 claim table — the substance of the graph. Subject·predicate·object,
-- raw-before-normalized, five temporal dimensions, and the four epistemic axes
-- (R/D/I stored; C derived at query time, SIG-EPIS-020). Append-only enforcement
-- is added by the next change (`claim_append_only`).
--
-- DEVIATION (ADR-013): §16.2 also specifies `PARTITION BY RANGE (observed_at)`.
-- That is incompatible with `claim_id` being a single-column PRIMARY KEY (Postgres
-- requires the partition key in every unique constraint), and claim_id MUST be a
-- single-column PK because claim_evidence, resolution, person, and the
-- revises/retraction self-references all FK to claim(claim_id). observed_at is
-- nullable by design (§16.2 point 4), so it cannot join the PK. No acceptance
-- criterion depends on partitioning; the FK contract is retained and physical
-- partitioning is deferred to a partition-compatible redesign. See ADR-013.

BEGIN;

CREATE TABLE claim (
  claim_id          uuid PRIMARY KEY DEFAULT uuidv7(),

  -- Subject · predicate · object -------------------------------------------
  subject_id        uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id      text NOT NULL REFERENCES vocab_predicate(predicate_id),
  object_entity     uuid REFERENCES entity(entity_id),
  object_type       text NOT NULL REFERENCES vocab_object_type(object_type),
      -- literal|entity_ref|vocab_term|quantity|money|geometry|duration|interval|document_ref
      -- REQUIRED: which value_* column is populated is ambiguous across
      -- quantity / money / duration, so the kind is declared, never inferred (§10.3.5)
  value_kind        value_kind NOT NULL DEFAULT 'value',
  value_text        text,        -- canonical string form; always present when kind='value'
  value_num         numeric,     -- typed shadow for indexed numeric comparison
  value_bool        boolean,
  value_geom        geometry(Geometry, 4326),
  value_json        jsonb,       -- structured values: bounds, intervals, composite money
  unit              text,        -- REQUIRED for object_type='quantity'; not recoverable from value_json

  -- P2: raw before normalized ----------------------------------------------
  raw_value         text NOT NULL,   -- the source's literal text. NO EXCEPTIONS.
  raw_context       jsonb,           -- the citation anchor within the artifact
  normalization_id  text REFERENCES vocab_normalization(normalization_id),
  normalization_version text,

  -- T1 valid time -----------------------------------------------------------
  valid_period      tstzrange NOT NULL DEFAULT tstzrange(NULL, NULL, '[)'),
  valid_edtf        text,
  valid_from_kind   text NOT NULL DEFAULT 'unknown',  -- exact|ongoing|unknown|before|after|never
  valid_to_kind     text NOT NULL DEFAULT 'unknown',

  -- T2 observation time (ordering scalar, not an AS OF axis) ----------------
  observed_at       timestamptz,
  observed_edtf     text,
  observed_at_kind  text NOT NULL DEFAULT 'exact',    -- exact|approximate|bounded_above|unknown
  observed_unknown_reason text,

  -- T5 transaction time (DB-controlled) -------------------------------------
  sys_period        tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),

  -- Epistemics: the four axes of §10.4-§10.6 -------------------------------
  -- NOTE: these are the R/D/I axes. C (currency) is DERIVED AT QUERY TIME and is
  -- deliberately NOT stored (SIG-EPIS-020). W is computed from all four.
  source_reliability text NOT NULL
      REFERENCES vocab_source_reliability(code),   -- R1..R6  (§10.4)
  reliability_provisional boolean NOT NULL DEFAULT false,  -- novel source (SIG-EPIS-015)
  claim_directness   text NOT NULL
      REFERENCES vocab_claim_directness(code),     -- D1..D6  (§10.5)
  artifact_integrity text NOT NULL
      REFERENCES vocab_artifact_integrity(code),   -- I1..I3  (§10.6)
  legacy_source_tier char(1)
      CHECK (legacy_source_tier IS NULL OR legacy_source_tier BETWEEN 'A' AND 'F'),
      -- OPTIONAL. Retained only to carry an upstream's own Tier A-F label where a
      -- source publishes one. It is NEVER used in resolution (§10.4).
  claim_polarity    text NOT NULL DEFAULT 'affirms',   -- affirms|denies
  rank              claim_rank NOT NULL DEFAULT 'normal',
  review_status     review_status NOT NULL DEFAULT 'unreviewed',

  -- Origin ------------------------------------------------------------------
  extraction_id     uuid REFERENCES extraction(extraction_id),
  asserted_by       uuid REFERENCES entity(entity_id),   -- a Person entity (§11.3), not free text
  assertion_rationale text,
  derived_from_claim_ids uuid[],      -- source-dependence chain (§28.6)

  -- Lineage & governance ----------------------------------------------------
  ingest_run_id     uuid NOT NULL REFERENCES ingest_run(run_id),
  revises_claim     uuid REFERENCES claim(claim_id),
  retraction_of     uuid REFERENCES claim(claim_id),
  correction_reason text,
  sensitivity_tier  smallint NOT NULL DEFAULT 0,
  rights_id         uuid NOT NULL REFERENCES rights_record(rights_id),

  CONSTRAINT claim_value_shape CHECK (
      (value_kind = 'value'
         AND (value_text IS NOT NULL OR object_entity IS NOT NULL
              OR value_geom IS NOT NULL OR value_json IS NOT NULL))
   OR (value_kind IN ('somevalue','novalue')
         AND value_text IS NULL AND object_entity IS NULL AND value_num IS NULL
         AND value_bool IS NULL AND value_geom IS NULL)
  ),
  CONSTRAINT claim_origin_present CHECK (
      extraction_id IS NOT NULL OR asserted_by IS NOT NULL
  ),
  CONSTRAINT claim_unit_required CHECK (
      object_type <> 'quantity' OR unit IS NOT NULL
  ),
  CONSTRAINT claim_human_needs_rationale CHECK (
      asserted_by IS NULL OR assertion_rationale IS NOT NULL
  ),
  CONSTRAINT claim_observed_unknown_reasoned CHECK (
      observed_at IS NOT NULL OR observed_unknown_reason IS NOT NULL
  ),
  CONSTRAINT claim_correction_reasoned CHECK (
      revises_claim IS NULL OR correction_reason IS NOT NULL
  ),
  CONSTRAINT claim_observed_not_future CHECK (
      observed_at IS NULL OR observed_at <= clock_timestamp() + interval '1 day'
  )
);

CREATE INDEX claim_spo_observed_idx ON claim (subject_id, predicate_id, observed_at DESC);
CREATE INDEX claim_valid_period_idx ON claim USING gist (valid_period);
CREATE INDEX claim_value_geom_idx   ON claim USING gist (value_geom) WHERE value_geom IS NOT NULL;
CREATE INDEX claim_pred_object_idx  ON claim (predicate_id, object_entity) WHERE object_entity IS NOT NULL;
CREATE INDEX claim_ingest_run_idx   ON claim (ingest_run_id);
CREATE INDEX claim_current_idx      ON claim (subject_id) WHERE upper_inf(sys_period);

COMMIT;
