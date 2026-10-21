-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:declared_lineage to pg
-- P35.25 / R11-L3-CP4 (SIG-CONF-014, CONF-04; design CP-4 "Declared lineage and
-- independence"):
--
-- 1. `source_lineage` mirrors the committed source-registry lineage
--    declarations (`connectors/data/sources.toml` [sources.*.lineage] blocks)
--    so readers that cannot import the connectors package (resolution,
--    reconcile, exports) resolve the same declared classes the emit path
--    stamps. Versioned per registry_version; rows are immutable — a changed
--    declaration lands as a NEW (source_id, registry_version) row, never an
--    UPDATE.
--
-- 2. `claim_lineage` is the append-only per-claim lineage record: the claim's
--    source, its declared `id_namespace` (the identifier space its upstream
--    references compare inside — `undeclared` when none is declared), the
--    declared `lineage_kind`, the resolved `independence_class`
--    (`unclassified` when lineage is undeclared/unresolvable — undeclared
--    material is NEVER independent corroboration), a `basis` token naming
--    where the values came from (emit `registry:<version>` | the
--    `rematerialize:<version>` backfill | `undeclared`), and
--    `derived_from_claim_ids` — recovered derivation ancestry the
--    rematerialize leg can back-populate append-only (the claim row itself is
--    never UPDATEd).
--
-- 3. Every claim gets AT MOST one lineage row (PRIMARY KEY claim_id +
--    immutability): the first recorded declaration stands; corrections are
--    new claim rows with their own lineage. `undeclared`/`unclassified`
--    tokens are stored explicitly (never NULL) so the L3 completeness check
--    is a plain NOT NULL scan.
--
-- Locking: two CREATE TABLEs + two CREATE INDEXes — additive only; nothing
-- existing is altered. Deployed when no ingest execution is running;
-- back-compatible (readers treat a missing row as undeclared lineage, the
-- same honest state old claims carry until the rematerialize leg runs).

BEGIN;

-- A claim record declaring an `id_namespace` outside the committed
-- vocabulary (db/data/id_namespaces.toml) fails closed into
-- assertion_quarantine under the new `unknown_id_namespace` reason — never
-- silently namespaced. The reason CHECK widens; existing rows are untouched.
ALTER TABLE assertion_quarantine
  DROP CONSTRAINT assertion_quarantine_reason_check;
ALTER TABLE assertion_quarantine
  ADD CONSTRAINT assertion_quarantine_reason_check
  CHECK (reason IN ('bad_digest','unknown_predicate','unknown_genre',
                    'unknown_subject_scheme','unknown_object_type',
                    'unknown_value_kind','missing_capture_binding',
                    'unsupported_locator','extractor_failure',
                    'version_mismatch','missing_required_field',
                    'unknown_qualifier','unknown_id_namespace'));

CREATE TABLE source_lineage (
  source_id          text NOT NULL REFERENCES source_registry(source_id),
  registry_version   text NOT NULL,              -- sources.toml declaration version
  kind               text NOT NULL,              -- primary|mirror|derived|syndicated|undeclared
  origin             text NOT NULL DEFAULT '',   -- free-text upstream when not a registry source
  mirror_of          text NOT NULL DEFAULT '',   -- registry source id this row mirrors
  derived_from       jsonb NOT NULL DEFAULT '[]',-- registry source ids this row derives from
  independence_class text NOT NULL DEFAULT 'unclassified', -- resolved class (emit-side resolution)
  id_namespace       text NOT NULL DEFAULT 'undeclared',   -- declared shared id space | src:<id> | undeclared
  collection_method  text NOT NULL DEFAULT '',             -- §10.8 collection method label
  evidence           text NOT NULL DEFAULT '',             -- documentary basis of the declaration
  recorded_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (source_id, registry_version),
  CHECK (kind IN ('primary','mirror','derived','syndicated','undeclared')),
  CHECK (independence_class <> ''),
  CHECK (id_namespace <> '')
);

COMMENT ON TABLE source_lineage IS
  'P35.25 (SIG-CONF-014): versioned mirror of the committed source-registry '
  'lineage declarations (sources.toml [lineage] blocks). One row per '
  '(source, registry_version); immutable — a changed declaration is a new '
  'row. The resolved independence_class is stamped at write time; readers '
  'join the latest version. Undeclared sources carry an explicit undeclared '
  'row only when the registry itself declares nothing AND the rematerialize '
  'leg records that state — absent rows are simply unknown.';

-- The latest-declared row per source — the read seam resolution/reconcile
-- consume without knowing registry versioning.
CREATE VIEW source_lineage_current AS
SELECT DISTINCT ON (source_id) *
  FROM source_lineage
 ORDER BY source_id, recorded_at DESC, registry_version DESC;

CREATE TABLE claim_lineage (
  claim_id              uuid PRIMARY KEY REFERENCES claim(claim_id),
  source_id             text NOT NULL,
  id_namespace          text NOT NULL DEFAULT 'undeclared',
  lineage_kind          text NOT NULL DEFAULT 'undeclared',
  independence_class    text NOT NULL DEFAULT 'unclassified',
  basis                 text NOT NULL,           -- registry:<ver> | rematerialize:<run> | undeclared
  derived_from_claim_ids uuid[],                 -- recovered ancestry the claim row cannot re-record
  recorded_at           timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (lineage_kind IN ('primary','mirror','derived','syndicated','undeclared')),
  CHECK (id_namespace <> ''),
  CHECK (independence_class <> ''),
  CHECK (basis <> '')
);

COMMENT ON TABLE claim_lineage IS
  'P35.25 (SIG-CONF-014): the append-only per-claim lineage record. One row '
  'per claim, immutable — id_namespace (the identifier space its upstream '
  'references compare inside; undeclared is explicit), the source-declared '
  'lineage_kind, the resolved independence_class (unclassified = never '
  'independent corroboration), the basis of the values, and recovered '
  'derived_from ancestry. The claim row itself is never UPDATEd to carry '
  'this — a missing row reads as undeclared lineage.';

CREATE INDEX claim_lineage_independence_class_idx ON claim_lineage (independence_class);
CREATE INDEX claim_lineage_source_idx ON claim_lineage (source_id);

-- Append-only (P1-P3): declarations and per-claim lineage are recorded facts.
CREATE FUNCTION source_lineage_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'source_lineage rows are immutable (append-only, P1-P3); a changed declaration is a new registry_version row';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER source_lineage_immutable
  BEFORE UPDATE OR DELETE ON source_lineage
  FOR EACH ROW EXECUTE FUNCTION source_lineage_immutable();

CREATE FUNCTION claim_lineage_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'claim_lineage rows are immutable (append-only, P1-P3); corrections land as new claim rows';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER claim_lineage_immutable
  BEFORE UPDATE OR DELETE ON claim_lineage
  FOR EACH ROW EXECUTE FUNCTION claim_lineage_immutable();

-- The emit path (sig_ingest) writes one lineage row per new claim and reads
-- the declarations; the rematerialize operator runs under the materialize
-- role (bounded batches, INSERT-only). Readers resolve independence classes
-- through the current view. The §37 *public* surface is NOT widened —
-- sig_read_public gains no grant here (the published-surface allowlist is
-- exact); restricted + export readers may SELECT. No role gets
-- UPDATE/DELETE — the triggers and the grant surface
-- agree (append-only, P1-P3).
GRANT SELECT ON source_lineage TO sig_ingest;
GRANT SELECT, INSERT ON claim_lineage TO sig_ingest;
GRANT SELECT, INSERT ON source_lineage TO sig_materialize;
GRANT SELECT, INSERT ON claim_lineage TO sig_materialize;
GRANT SELECT ON source_lineage_current TO sig_ingest;
GRANT SELECT ON source_lineage_current TO sig_materialize;
GRANT SELECT ON source_lineage, source_lineage_current, claim_lineage TO sig_read_restricted;
GRANT SELECT ON source_lineage, source_lineage_current, claim_lineage TO sig_export;

COMMIT;
