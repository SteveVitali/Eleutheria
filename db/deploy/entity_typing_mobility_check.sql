-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:entity_typing_mobility_check to pg
--
-- P35.14b — entity typing + hosted CHECK-NOT-VALID (L1 NEW-5 / FM-17,
-- SIG-IDENT-025, SIG-GEO-005, SIG-ONTO-027; row 273).
--
-- Two halves, both additive:
--
-- 1. `entity_type_decision` — the append-only typed-identity correction log.
--    Before P35.14b every `sig.connector.subject` minted entity_type
--    'deployment' (the sink's _DEFAULT_ENTITY_TYPE). The spine is append-only,
--    so the correction is NOT an UPDATE of the mistyped `entity` rows: it is a
--    NEW decision row per affected subject, stamped with the version of the
--    committed subject_entity_types.toml map that decided it. Readers resolve
--    an entity's current type through `entity_current_type` (latest decision
--    wins, falling back to the recorded column); history is preserved, and a
--    wrong decision is superseded by a NEW row, never edited (immutability
--    trigger; no UPDATE/DELETE grants). UNIQUE (scheme, value, entity_type,
--    map_version) is the idempotency barrier — a re-run of the same map
--    version lands +0.
--
-- 2. `physical_asset_mobility_vocab` — CHECK (mobility IN <Mobility enum>)
--    NOT VALID on the existing `physical_asset` table (SIG-GEO-005: the OSM
--    writer recorded the out-of-vocabulary 'mobile'; P35.14a fixes the source
--    mapping, this constraint binds NEW writes immediately while pre-existing
--    rows are validated in a named follow-up — VALIDATE CONSTRAINT is
--    deliberately NOT part of this change). The Mobility enum is declared in
--    ontology/src/ontology/schema/common.yaml (no vocab table exists for it,
--    so the six permissible values are spelled out and the constraint comment
--    names the enum). The ALTER takes ACCESS EXCLUSIVE on physical_asset —
--    that is why this change is on the never-pre-authorised OM-20 list and
--    runs only on the operator's verbatim in-ticket go with `lock_timeout`
--    set (the SET below bounds every lock wait in the deploy; the hosted leg
--    pins the same bound at the session level).
--
-- The `assertion_quarantine` reason CHECK gains 'unknown_subject_scheme' —
-- the fail-closed refusal a subject whose scheme prefix no map entry covers
-- lands under (db.subject_types + PgClaimSink).
--
-- Conformance-audit scope note (row 273 names every flagged column here):
-- the audit's measured out-of-vocabulary case is `physical_asset.mobility`.
-- No other vocab-valued column on the existing tables was flagged for a
-- hosted CHECK this row; broadening beyond the Mobility enum is explicitly
-- out of scope (a later sqitch row if the audit needs one).

BEGIN;

-- Bound every lock wait in this deploy. The ALTER below needs ACCESS
-- EXCLUSIVE on physical_asset — brief on an idle table, but a queued wait
-- behind a long reader must fail fast rather than stall ingest.
SET LOCAL lock_timeout = '5s';

-- ---------------------------------------------------------------------------
-- 1. The append-only typed-identity decision table.
-- ---------------------------------------------------------------------------
CREATE TABLE entity_type_decision (
  decision_seq  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  scheme        text NOT NULL,
  value         text NOT NULL,
  entity_id     uuid NOT NULL REFERENCES entity(entity_id),
  prior_type    text NOT NULL,               -- effective type the decision supersedes
  entity_type   text NOT NULL REFERENCES vocab_entity_type(entity_type),
  map_version   text NOT NULL,               -- the subject_entity_types.toml version
  decided_by    text NOT NULL,               -- a writer identity/role, never a personal name
  basis         text NOT NULL,               -- the written basis for the correction
  decided_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  -- The decision names an existing keyed identity — it never mints or re-keys.
  FOREIGN KEY (scheme, value) REFERENCES entity_identity_key (scheme, value),
  -- Idempotency barrier: one decision per (subject, type, map version); the
  -- writer's INSERT ... ON CONFLICT DO NOTHING makes a re-run +0.
  UNIQUE (scheme, value, entity_type, map_version),
  -- A decision that "corrects" to the same type is noise — the writer only
  -- ever proposes differing types; enforce it so a hand-rolled row cannot.
  CHECK (entity_type <> prior_type)
);

COMMENT ON TABLE entity_type_decision IS
  'P35.14b append-only typed-identity corrections (SIG-IDENT-025): a new row per '
  'subject whose declared map type supersedes its recorded entity_type; existing '
  'entity/entity_identity_key rows are never UPDATEd/DELETEd. Read through '
  'entity_current_type (latest decision_seq wins).';

-- Latest-decision-per-entity lookup used by entity_current_type and readers.
CREATE INDEX entity_type_decision_entity_idx
  ON entity_type_decision (entity_id, decision_seq DESC);

-- Append-only enforcement (P1–P3): a wrong decision is superseded by a NEW
-- row, never edited or deleted.
CREATE FUNCTION entity_type_decision_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'entity_type_decision rows are immutable (append-only, P1-P3); record a NEW decision row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entity_type_decision_immutable
  BEFORE UPDATE OR DELETE ON entity_type_decision
  FOR EACH ROW EXECUTE FUNCTION entity_type_decision_immutable();

-- The effective type a reader should see: latest decision wins, else the
-- recorded column (mistyped history stays honest until its decision lands).
CREATE VIEW entity_current_type AS
SELECT e.entity_id,
       COALESCE(
         (SELECT d.entity_type
            FROM entity_type_decision d
           WHERE d.entity_id = e.entity_id
           ORDER BY d.decision_seq DESC
           LIMIT 1),
         e.entity_type
       ) AS entity_type
FROM entity e;

-- The leg's writer and the ingest path append; internal readers resolve.
GRANT SELECT, INSERT ON entity_type_decision TO sig_ingest;
GRANT SELECT ON entity_type_decision TO sig_read_restricted, sig_read_sealed;
GRANT SELECT ON entity_current_type TO
  sig_ingest, sig_read_restricted, sig_read_sealed, sig_materialize;
REVOKE UPDATE, DELETE ON entity_type_decision FROM PUBLIC;
REVOKE UPDATE, DELETE ON entity_type_decision
  FROM sig_ingest, sig_read_public, sig_read_restricted, sig_read_sealed,
       sig_export, sig_materialize;

-- spine_watermark facet: a landed decision changes what type-resolution
-- surfaces may emit, so the table joins the watched relation set.
INSERT INTO spine_watermark (facet, row_count, closed_count, latest_instant)
VALUES ('entity_type_decision',
        (SELECT count(*) FROM entity_type_decision), 0,
        (SELECT max(decided_at) FROM entity_type_decision));

CREATE TRIGGER spine_watermark_insert
  AFTER INSERT ON entity_type_decision
  REFERENCING NEW TABLE AS new_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('decided_at', 'false');
CREATE TRIGGER spine_watermark_update
  AFTER UPDATE ON entity_type_decision
  REFERENCING NEW TABLE AS new_rows OLD TABLE AS old_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('decided_at', 'false');
CREATE TRIGGER spine_watermark_truncate
  AFTER TRUNCATE ON entity_type_decision
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('NULL', 'false');

-- ---------------------------------------------------------------------------
-- 2. The Mobility enum-membership CHECK (SIG-GEO-005), NOT VALID.
-- ---------------------------------------------------------------------------
ALTER TABLE physical_asset
  ADD CONSTRAINT physical_asset_mobility_vocab
  CHECK (mobility IN
    ('fixed', 'redeployable', 'vehicle_mounted', 'airborne', 'handheld', 'unknown'))
  NOT VALID;
COMMENT ON CONSTRAINT physical_asset_mobility_vocab ON physical_asset IS
  'P35.14b / SIG-GEO-005: membership in the ontology Mobility enum '
  '(common.yaml — fixed|redeployable|vehicle_mounted|airborne|handheld|unknown). '
  'NOT VALID: binds new writes immediately; pre-existing rows are validated in a '
  'named follow-up (VALIDATE CONSTRAINT deliberately out of scope for this change).';

-- ---------------------------------------------------------------------------
-- 3. unknown_subject_scheme joins the quarantine-reason CHECK (fail-closed
--    refusal for a subject value no map prefix covers).
-- ---------------------------------------------------------------------------
ALTER TABLE assertion_quarantine DROP CONSTRAINT assertion_quarantine_reason_check;
ALTER TABLE assertion_quarantine ADD CONSTRAINT assertion_quarantine_reason_check
  CHECK (reason IN ('bad_digest','unknown_predicate','unknown_genre',
                    'unknown_subject_scheme','unknown_object_type',
                    'unknown_value_kind','missing_capture_binding',
                    'unsupported_locator','extractor_failure',
                    'version_mismatch','missing_required_field',
                    'unknown_qualifier'));

COMMIT;
