-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:seal_register to pg
--
-- P34.49 / ADR-185 (F-406, SIG-PUB-003/003a/011–014a, SIG-STORE-025,
-- SIG-GOV-007): the append-only protective-seal register `capture_seal` — one
-- row per protective action on one stored capture. It is the spine side of
-- the seal deny set (the object side is `sig.seal-deny/1` on the restricted
-- bucket — two carriers, one rule, the ADR-124 discipline):
--
--   * a `seal` row marks a capture protectively suppressed — the serving
--     path returns the sealed representation (existence + digest only,
--     SIG-EVID-010) and the export refuses to bind it, on every
--     publishable path;
--   * an `unseal` row is the superseding record an authorized review writes
--     later — a NEW row, never an edit (the table's immutability trigger +
--     the privilege set admit no UPDATE/DELETE).
--
-- Seal = suppress, never delete: the bytes stay content-addressed in the
-- OCFL store (SIG-EVID-006 Object Lock). True purge stays the operator's
-- WV-11 action (ADR-181 control 2, ADR-189) — this table carries no
-- delete/purge action by design.
--
-- Least privilege: the public read roles see capture_id + action + rules
-- (why, at class granularity — never the flagged material); the elevated
-- roles see all; writes go to the NOLOGIN `sig_seal_writer` (the L2 leg's
-- write surface) — INSERT only, no UPDATE/DELETE anywhere.

BEGIN;

CREATE TABLE capture_seal (
  seal_seq         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  capture_id       uuid NOT NULL REFERENCES evidence_capture(capture_id),
  content_digest   text NOT NULL,               -- the sealed OCFL object's digest (multihash)
  action           text NOT NULL
                   CHECK (action IN ('seal','unseal')),
  rules            text[] NOT NULL DEFAULT '{}', -- the F-406/I7/PUB-002 class ids that fired
  author           text NOT NULL,                -- the recorded operator id
  audit_report     text NOT NULL DEFAULT '',     -- the sig.at-rest-audit/1 object that flagged it
  recorded_at      timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE capture_seal IS
  'P34.49/ADR-185 (F-406): the append-only protective-seal register. A `seal` '
  'row suppresses a capture on every publishable path (sealed representation '
  'on the API, no export binding, the bucket deny set); an `unseal` row is '
  'the superseding record an authorized review writes later. The table '
  'admits no UPDATE/DELETE — no byte it names is ever deleted by this path '
  '(WV-11 purge stays the operator''s in-ticket action).';

CREATE INDEX capture_seal_capture_idx ON capture_seal (capture_id, recorded_at DESC, seal_seq DESC);
CREATE INDEX capture_seal_digest_idx ON capture_seal (content_digest);

-- The "currently sealed" helper — one query the serving/export consults inline
-- (latest action per capture: `seal` wins unless a later `unseal` supersedes).
CREATE FUNCTION capture_currently_sealed(p_capture_id uuid)
RETURNS boolean AS $$
  SELECT COALESCE(
    (SELECT s.action = 'seal'
       FROM capture_seal s
      WHERE s.capture_id = p_capture_id
      ORDER BY s.recorded_at DESC, s.seal_seq DESC
      LIMIT 1),
    false)
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION capture_currently_sealed(uuid) IS
  'P34.49/ADR-185: the current seal state of one capture — the latest recorded '
  'action wins (`seal` unless a later `unseal` supersedes). The serving and '
  'export consults use the same rule as the deny-set object.';

-- Append-only: a seal is recorded once, never mutated.
CREATE FUNCTION capture_seal_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'capture_seal rows are immutable (append-only, ADR-185); append a NEW row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER capture_seal_immutable
  BEFORE UPDATE OR DELETE ON capture_seal
  FOR EACH ROW EXECUTE FUNCTION capture_seal_immutable();

-- ---------------------------------------------------------------------------
-- The sealing writer — a NOLOGIN role whose whole write surface is this table
-- (the L2 leg connects as an owner that routes the writes; the role exists so
-- the grant set is auditable and a least-privilege login can be granted
-- membership later without a schema change).
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sig_seal_writer') THEN
    CREATE ROLE sig_seal_writer NOLOGIN;
  END IF;
END
$$;

-- Readers: the public/API path consults the current seal state on capture
-- reads (capture_id + action + rules + the ordering columns — never the
-- flagged material, author or audit ref); elevated roles see the full row.
GRANT SELECT (seal_seq, capture_id, action, rules, recorded_at)
  ON capture_seal TO sig_read_public, sig_export;
GRANT SELECT ON capture_seal
  TO sig_read_restricted, sig_read_sealed, sig_materialize;

-- Writer: INSERT only — the L2 leg's write surface.
GRANT INSERT (capture_id, content_digest, action, rules, author, audit_report)
  ON capture_seal TO sig_seal_writer;
GRANT USAGE ON SEQUENCE capture_seal_seal_seq_seq TO sig_seal_writer;

-- SIG-STORE-012 discipline: no application role may UPDATE/DELETE here either.
REVOKE UPDATE, DELETE ON capture_seal FROM PUBLIC;
REVOKE UPDATE, DELETE ON capture_seal
  FROM sig_ingest, sig_read_public, sig_read_restricted, sig_read_sealed,
       sig_export, sig_materialize, sig_seal_writer;

-- ---------------------------------------------------------------------------
-- spine_watermark facet: a recorded seal changes what the serving/export
-- surfaces may emit, so the register joins the watched relation set
-- (INSERT/TRUNCATE bump; UPDATE is impossible by trigger).
-- ---------------------------------------------------------------------------
INSERT INTO spine_watermark (facet, row_count, closed_count, latest_instant)
VALUES ('capture_seal',
        (SELECT count(*) FROM capture_seal), 0,
        (SELECT max(recorded_at) FROM capture_seal));

CREATE TRIGGER spine_watermark_insert
  AFTER INSERT ON capture_seal
  REFERENCING NEW TABLE AS new_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('recorded_at', 'false');
CREATE TRIGGER spine_watermark_update
  AFTER UPDATE ON capture_seal
  REFERENCING NEW TABLE AS new_rows
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('recorded_at', 'false');
CREATE TRIGGER spine_watermark_truncate
  AFTER TRUNCATE ON capture_seal
  FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch('recorded_at', 'true');

COMMIT;
