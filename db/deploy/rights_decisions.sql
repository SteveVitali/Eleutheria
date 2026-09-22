-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:rights_decisions to pg
-- P27.2 / ADR-095: the append-only RIGHTS-RESOLUTION log. The claim spine is
-- append-only — a claim's recorded rights_id is provenance of what was known at
-- assertion time and is never rewritten. A licence review that resolves claims
-- asserted under UNDETERMINED rights is therefore recorded as a NEW decision row
-- (source -> resolved rights_record), never an UPDATE. Readers resolve a claim's
-- effective rights as: the latest decision whose (source_id, prior_rights_id)
-- matches the claim's recorded rights_id, else the recorded record — so a
-- decision can only lift UNDETERMINED-recorded rights, never relicense an
-- already-resolved (e.g. ODbL) claim.
--
-- Rows are immutable (P1–P3): a changed disposition is a NEW decision row with
-- a later decided_at; supersession is by ordering, never by mutation. `reviewer`
-- carries a ROLE (e.g. 'maintainer (delegated)'), never a personal name
-- (Part VIII §0.7). `decided_at` is DB-clock-set, not caller-supplied.

BEGIN;

CREATE TABLE rights_decision (
  decision_id     uuid PRIMARY KEY DEFAULT uuidv7(),
  source_id       text NOT NULL REFERENCES source_registry(source_id),
  rights_id       uuid NOT NULL REFERENCES rights_record(rights_id),   -- the resolved record
  prior_rights_id uuid NOT NULL REFERENCES rights_record(rights_id),   -- the record it resolves (UNDETERMINED)
  basis           text NOT NULL,      -- gate + legal basis citation (e.g. 'HG-03 2026-09-22 under GL-GATE-07: …')
  reviewer        text NOT NULL,      -- role, never a personal name (Part VIII §0.7)
  review_packet   text,               -- repo-relative rights packet (SIG-LIC-001)
  terms_url       text,               -- the terms page the reviewer read (convenience copy)
  terms_capture_id uuid REFERENCES evidence_capture(capture_id),  -- the ARCHIVED terms (SIG-LIC-002)
  decided_at      timestamptz NOT NULL DEFAULT clock_timestamp()
);

-- Latest-decision-per-(source, prior) lookup used by every effective-rights reader.
CREATE INDEX rights_decision_source_idx
  ON rights_decision (source_id, prior_rights_id, decided_at DESC, decision_id DESC);

-- Append-only enforcement: a rights decision is a recorded adjudication; it is
-- never edited or deleted — supersession is a new row (P1–P3).
CREATE FUNCTION rights_decision_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'rights_decision rows are immutable (append-only, P1-P3); record a NEW decision row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER rights_decision_immutable
  BEFORE UPDATE OR DELETE ON rights_decision
  FOR EACH ROW EXECUTE FUNCTION rights_decision_immutable();

-- The ingest role appends decisions via the pipeline; readers resolve them.
GRANT SELECT, INSERT ON rights_decision TO sig_ingest;
GRANT SELECT ON rights_decision TO sig_read_public, sig_read_restricted, sig_read_sealed, sig_export;

COMMIT;
