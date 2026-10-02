-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:human_eval_campaign to pg
--
-- P32.9 / ADR-128 (SIG-EVAL-001, SIG-EVAL-002): the independent blinded human
-- evaluation campaign surface. This is a DIFFERENT channel from the P31.10/.11
-- operational review queue: review_item/review_decision carry model-assisted
-- proposals and accept/reject verdicts that steer clustering; these tables
-- carry *reference labels* — an independent human's answer to "do these two
-- records describe the same defined object" — which are never operational
-- decisions and never visible to the clustering path until an authorized
-- release row unseals them.
--
--   1. human_eval_campaign / human_eval_manifest — the immutable
--      preregistration: frozen source snapshot, target population, strata,
--      grouping/split spec, seed and ruleset/protocol digests; one manifest
--      row pins the tamper-evident digest over design + whole sample
--      membership plus the persisted per-(partition,stratum) denominators.
--   2. human_eval_sample — the drawn membership: opaque hev-* sample ids
--      (they encode no stratum/tier/score), partition, estimand, stratum,
--      dependency-group id, upstream lineage ids, explicit
--      selection_probability + weight + draw_order, and the reference basis
--      (what "same" means for the pair).
--   3. human_eval_packet — the only artifact a reviewer sees: the sanitized
--      two-sided evidence payload + its digest. Model tier/score/weight,
--      prior labels, strata, probabilities and predictions live in
--      human_eval_sample, which reviewers cannot read.
--   4. human_eval_assignment — reviewer × sample × pass (two independent
--      first passes), the RLS driver for what a reviewer may see.
--   5. human_eval_attestation — append-only human-marker events; a label MUST
--      cite a 'human_identity' attestation for its reviewer (agents and LLMs
--      cannot impersonate human adjudication).
--   6. human_eval_label — the append-only reference labels: same /
--      different / insufficient_evidence (insufficient is a first-class
--      persisted outcome, never an implicit accept), pseudonymous
--      reviewer_id, reason codes, evidence refs, rubric version, the packet
--      digest the reviewer actually saw, supersedes pointer (a correction is
--      a NEW row; the superseded row stays) and a per-label digest that
--      feeds the campaign watermark chain.
--   7. human_eval_adjudication — append-only adjudications ('unresolved'
--      allowed: disagreement the adjudicator cannot settle is recorded,
--      never forced). One non-superseded adjudication per sample.
--   8. human_eval_release — the authorized unsealing decision, one row per
--      (campaign, scope): 'development_only' | 'final' | 'operational'.
--      Until a release exists, sealed_final labels/adjudications are
--      invisible to the model-development views; only 'operational' makes
--      them visible to sig_materialize.
--
-- Roles (NOLOGIN groups, same convention as access_control/materialize_role):
--   * sig_eval_admin — the preparation surface: SELECT+INSERT on the
--     prep tables, SELECT on the RELEASED views only. It cannot read the
--     base label/adjudication tables at all — sealed_final labels do not
--     exist for the model-development surface until a custodian release.
--   * sig_eval_reviewer — RLS-scoped to `current_setting('sig.eval_reviewer')`:
--     sees own assignments, own attestations, packets for assigned samples
--     and own labels only; inserts labels + attestations under a WITH CHECK
--     that pins reviewer_id to the session GUC. No access to
--     human_eval_sample (strata/probabilities), adjudications or releases.
--   * sig_eval_custodian — the sealing authority: SELECT on every eval
--     table, INSERT on release/adjudication/attestation.
--   * sig_materialize / sig_read_* / sig_export / sig_ingest — NO grants on
--     the eval tables. sig_materialize may SELECT human_eval_label_operational
--     / human_eval_adjudication_operational only, which are EMPTY until an
--     operational-scope release is recorded — sealed labels are unreachable
--     from clustering by construction, not by convention.
--
-- Every table is append-only: an immutability trigger refuses UPDATE/DELETE
-- for every role including the owner; corrections supersede by append.

BEGIN;

-- ---------------------------------------------------------------------------
-- Roles (cluster-global; guard CREATE ROLE, grants repeat safely).
-- ---------------------------------------------------------------------------
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_eval_admin') THEN
    CREATE ROLE sig_eval_admin NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_eval_reviewer') THEN
    CREATE ROLE sig_eval_reviewer NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_eval_custodian') THEN
    CREATE ROLE sig_eval_custodian NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. Preregistration + manifest.
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_campaign (
  campaign_id    text PRIMARY KEY,             -- caller-chosen label
  purpose        text NOT NULL,                -- never a person
  protocol_digest text NOT NULL,               -- digest of the rubric/protocol packet
  frame_snapshot text NOT NULL,                -- frozen source-snapshot identity
  ruleset_digest text NOT NULL,                -- the rules/candidate identity under eval
  seed           text NOT NULL,                -- the draw + blinding seed
  design         jsonb NOT NULL DEFAULT '{}',  -- population/strata/grouping/split/quotas
  created_by     text NOT NULL,                -- the tool/engineering actor
  created_at     timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE human_eval_campaign IS
  'P32.9/ADR-128 (SIG-EVAL-001): the immutable human-evaluation campaign '
  'preregistration — frozen snapshot, target population, strata, grouping and '
  'split spec, seed and ruleset/protocol digests. A changed ruleset or an '
  'unblinded test set requires a NEW campaign, never an edit.';

CREATE TABLE human_eval_manifest (
  campaign_id      text PRIMARY KEY REFERENCES human_eval_campaign(campaign_id),
  manifest_digest  text NOT NULL,   -- digest over campaign design + full membership
  membership_digest text NOT NULL,  -- digest over the draw-order-sorted sample rows
  sample_count     integer NOT NULL CHECK (sample_count >= 0),
  denominators     jsonb NOT NULL DEFAULT '{}',  -- per partition×stratum universe+drawn
  created_by       text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE human_eval_manifest IS
  'P32.9/ADR-128: one tamper-evident manifest per campaign — the recomputed '
  'digest over design + membership must equal this row (tampering is detected '
  'by re-verification), and the per-(partition,stratum) denominators the '
  'selection probabilities were drawn against are persisted here.';

-- ---------------------------------------------------------------------------
-- 2. Sample membership (the sealed-identifier surface).
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_sample (
  campaign_id          text NOT NULL REFERENCES human_eval_campaign(campaign_id),
  sample_id            text NOT NULL,        -- opaque hev-* digest id
  pair_id              text NOT NULL,        -- internal pair identity (never reviewer-visible)
  left_ref             text NOT NULL,
  right_ref            text NOT NULL,
  packet_digest        text,                 -- informational; packet table is authoritative
  partition            text NOT NULL
                       CHECK (partition IN
                         ('training','development','calibration','pilot','sealed_final')),
  estimand             text NOT NULL,
  stratum_id           text NOT NULL,
  dependency_group_id  text NOT NULL,        -- lineage/component-disjoint group
  source_lineage_ids   text[] NOT NULL DEFAULT '{}',
  selection_probability double precision NOT NULL
                       CHECK (selection_probability > 0
                              AND selection_probability <= 1),
  weight               double precision CHECK (weight > 0),
  draw_order           integer NOT NULL,
  reference_basis      text NOT NULL
                       CHECK (reference_basis IN
                         ('source_record_identity','physical_identity','site_identity')),
  created_at           timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (campaign_id, sample_id),
  UNIQUE (campaign_id, draw_order)
);

COMMENT ON TABLE human_eval_sample IS
  'P32.9/ADR-128: the drawn evaluation sample — opaque hev-* ids, partition '
  '(sealed_final is the confirmatory holdout), estimand, stratum, dependency '
  'group, upstream lineage ids and the explicit inclusion probability/weight/'
  'draw order each row was drawn under. Reviewer roles hold no grant here: '
  'strata, probabilities and partitions are exactly what blinding hides.';

CREATE INDEX human_eval_sample_partition_idx
  ON human_eval_sample (campaign_id, partition, stratum_id);

-- ---------------------------------------------------------------------------
-- 3. Blinded packets — the reviewer-visible surface.
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_packet (
  campaign_id   text NOT NULL,
  sample_id     text NOT NULL,
  packet_digest text NOT NULL,
  payload       jsonb NOT NULL,              -- sanitized two-sided evidence
  created_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (campaign_id, sample_id),
  FOREIGN KEY (campaign_id, sample_id)
    REFERENCES human_eval_sample (campaign_id, sample_id)
);

COMMENT ON TABLE human_eval_packet IS
  'P32.9/ADR-128: the ONLY artifact a reviewer sees — the orientation-'
  'randomized, model/label/stratum-stripped evidence payload plus its digest. '
  'A label must cite this digest, so a stale or rebuilt packet cannot be '
  'silently labeled.';

-- ---------------------------------------------------------------------------
-- 4. Assignments (reviewer × sample × pass).
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_assignment (
  campaign_id text NOT NULL,
  sample_id   text NOT NULL,
  reviewer_id text NOT NULL,                 -- pseudonymous handle, never a person record
  pass_no     smallint NOT NULL CHECK (pass_no IN (1, 2)),
  assigned_by text NOT NULL,                 -- the tooling actor, never a person
  created_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (campaign_id, sample_id, reviewer_id, pass_no),
  FOREIGN KEY (campaign_id, sample_id)
    REFERENCES human_eval_sample (campaign_id, sample_id)
);

COMMENT ON TABLE human_eval_assignment IS
  'P32.9/ADR-128: which pseudonymous reviewer labels which sample on which '
  'independent pass. Drives the reviewer RLS: a reviewer sees only their own '
  'assignments and the packets those assignments cover.';

-- ---------------------------------------------------------------------------
-- 5. Attestations — the human marker.
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_attestation (
  attestation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id    text REFERENCES human_eval_campaign(campaign_id),
  reviewer_id    text NOT NULL,
  kind           text NOT NULL
                 CHECK (kind IN ('human_identity','training_complete',
                                 'conflict_declaration','blinding_breach',
                                 'withdrawn')),
  detail         jsonb NOT NULL DEFAULT '{}',
  recorded_by    text NOT NULL,              -- the actor recording the event
  recorded_at    timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE human_eval_attestation IS
  'P32.9/ADR-128 (SIG-EVAL-002): append-only human-marker events — a '
  'human_identity attestation is a hard prerequisite of every label row '
  '(agents and LLMs cannot impersonate human adjudication); blinding breaches '
  'and withdrawals are recorded, never erased.';

-- ---------------------------------------------------------------------------
-- 6. Reference labels — append-only, reviewer-scoped.
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_label (
  label_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  label_seq           bigint GENERATED ALWAYS AS IDENTITY,
  campaign_id         text NOT NULL,
  sample_id           text NOT NULL,
  reviewer_id         text NOT NULL,         -- pseudonymous handle
  label_round         text NOT NULL
                      CHECK (label_round IN ('independent_1','independent_2','repeat')),
  label               text NOT NULL
                      CHECK (label IN ('same','different','insufficient_evidence')),
  reason_codes        text[] NOT NULL DEFAULT '{}',
  evidence_refs       jsonb NOT NULL DEFAULT '[]',
  rubric_version      text NOT NULL,
  packet_digest       text NOT NULL,         -- the packet version actually labeled
  attestation_id      uuid NOT NULL REFERENCES human_eval_attestation(attestation_id),
  supersedes_label_id uuid REFERENCES human_eval_label(label_id),
  label_digest        text NOT NULL,         -- content digest feeding the watermark
  recorded_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (campaign_id, sample_id)
    REFERENCES human_eval_sample (campaign_id, sample_id)
);

COMMENT ON TABLE human_eval_label IS
  'P32.9/ADR-128 (SIG-EVAL-002): independent reference labels — same | '
  'different | insufficient_evidence, append-only with append-only supersession '
  '(a correction is a new row pointing at the old; the old stays). These are '
  'NOT operational accept/reject decisions: nothing here writes review_decision '
  'or camera_site_match, and insufficient_evidence can never auto-accept a pair.';

-- At most one non-superseding label per (sample, reviewer, round): a second
-- first-pass label must supersede by append, never overwrite or twin.
CREATE UNIQUE INDEX human_eval_label_current_uq
  ON human_eval_label (campaign_id, sample_id, reviewer_id, label_round)
  WHERE supersedes_label_id IS NULL;

-- ---------------------------------------------------------------------------
-- 7. Adjudications — separate from labels AND from operational decisions.
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_adjudication (
  adjudication_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  adjudication_seq  bigint GENERATED ALWAYS AS IDENTITY,
  campaign_id       text NOT NULL,
  sample_id         text NOT NULL,
  adjudicator_id    text NOT NULL,           -- pseudonymous handle
  phase             text NOT NULL CHECK (phase IN ('independent','resolution')),
  label             text NOT NULL
                    CHECK (label IN
                      ('same','different','insufficient_evidence','unresolved')),
  reason            text NOT NULL,
  evidence_refs     jsonb NOT NULL DEFAULT '[]',
  supersedes_adjudication_id uuid
                    REFERENCES human_eval_adjudication(adjudication_id),
  recorded_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (campaign_id, sample_id)
    REFERENCES human_eval_sample (campaign_id, sample_id)
);

COMMENT ON TABLE human_eval_adjudication IS
  'P32.9/ADR-128: the separate adjudication channel for disagreements and '
  'abstentions — unresolved stays unresolved. Adjudicated same/different may '
  'become operational accept/reject only through a recorded, authorized '
  'promotion after an operational release, never automatically.';

CREATE UNIQUE INDEX human_eval_adjudication_current_uq
  ON human_eval_adjudication (campaign_id, sample_id)
  WHERE supersedes_adjudication_id IS NULL;

-- ---------------------------------------------------------------------------
-- 8. Authorized unsealing.
-- ---------------------------------------------------------------------------
CREATE TABLE human_eval_release (
  release_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id   text NOT NULL REFERENCES human_eval_campaign(campaign_id),
  scope         text NOT NULL
                CHECK (scope IN ('development_only','final','operational')),
  authorized_by text NOT NULL,
  detail        jsonb NOT NULL DEFAULT '{}',
  authorized_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (campaign_id, scope)
);

COMMENT ON TABLE human_eval_release IS
  'P32.9/ADR-128: the authorized unsealing decision. Until a row exists, '
  'sealed_final labels and adjudications are invisible to every '
  'model-development and operational surface; operational promotion requires '
  'scope = operational. One row per (campaign, scope), append-only.';

-- ---------------------------------------------------------------------------
-- Released/operational views — the only non-custodian read path to labels.
-- The view owner reads all rows (superuser bypasses RLS); the WHERE clause
-- is the seal: sealed_final rows appear only after an authorized release.
-- ---------------------------------------------------------------------------
CREATE VIEW human_eval_label_released AS
  SELECT l.label_id, l.label_seq, l.campaign_id, l.sample_id, l.reviewer_id,
         l.label_round, l.label, l.reason_codes, l.evidence_refs,
         l.rubric_version, l.packet_digest, l.attestation_id,
         l.supersedes_label_id, l.label_digest, l.recorded_at
    FROM human_eval_label l
    JOIN human_eval_sample s
      ON s.campaign_id = l.campaign_id AND s.sample_id = l.sample_id
   WHERE s.partition <> 'sealed_final'
      OR EXISTS (SELECT 1 FROM human_eval_release r
                  WHERE r.campaign_id = l.campaign_id);

COMMENT ON VIEW human_eval_label_released IS
  'P32.9/ADR-128: the model-development label surface — every non-sealed label '
  'plus sealed_final labels only after a custodian release row exists. The '
  'sealed half is unreachable here (and everywhere) until that decision.';

CREATE VIEW human_eval_adjudication_released AS
  SELECT a.adjudication_id, a.adjudication_seq, a.campaign_id, a.sample_id,
         a.adjudicator_id, a.phase, a.label, a.reason, a.evidence_refs,
         a.supersedes_adjudication_id, a.recorded_at
    FROM human_eval_adjudication a
    JOIN human_eval_sample s
      ON s.campaign_id = a.campaign_id AND s.sample_id = a.sample_id
   WHERE s.partition <> 'sealed_final'
      OR EXISTS (SELECT 1 FROM human_eval_release r
                  WHERE r.campaign_id = a.campaign_id);

CREATE VIEW human_eval_label_operational AS
  SELECT l.label_id, l.campaign_id, l.sample_id, l.label, l.reason_codes,
         l.label_round, l.rubric_version, l.packet_digest, l.recorded_at
    FROM human_eval_label l
   WHERE EXISTS (SELECT 1 FROM human_eval_release r
                  WHERE r.campaign_id = l.campaign_id
                    AND r.scope = 'operational');

COMMENT ON VIEW human_eval_label_operational IS
  'P32.9/ADR-128: the ONLY eval-label surface sig_materialize may read — '
  'labels under an explicit operational-scope release, for the authorized '
  'promotion path to clustering. Empty until that release exists; sealed '
  'labels can never appear here.';

CREATE VIEW human_eval_adjudication_operational AS
  SELECT a.adjudication_id, a.campaign_id, a.sample_id, a.label, a.reason,
         a.phase, a.recorded_at
    FROM human_eval_adjudication a
   WHERE EXISTS (SELECT 1 FROM human_eval_release r
                  WHERE r.campaign_id = a.campaign_id
                    AND r.scope = 'operational');

-- ---------------------------------------------------------------------------
-- Append-only enforcement: every eval table refuses UPDATE/DELETE, for every
-- role including the owner (same posture as publication_disposition).
-- ---------------------------------------------------------------------------
CREATE FUNCTION human_eval_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'human-eval rows are immutable (append-only, SIG-EVAL-001/002); append a NEW superseding row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER human_eval_campaign_immutable
  BEFORE UPDATE OR DELETE ON human_eval_campaign
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_manifest_immutable
  BEFORE UPDATE OR DELETE ON human_eval_manifest
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_sample_immutable
  BEFORE UPDATE OR DELETE ON human_eval_sample
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_packet_immutable
  BEFORE UPDATE OR DELETE ON human_eval_packet
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_assignment_immutable
  BEFORE UPDATE OR DELETE ON human_eval_assignment
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_attestation_immutable
  BEFORE UPDATE OR DELETE ON human_eval_attestation
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_label_immutable
  BEFORE UPDATE OR DELETE ON human_eval_label
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_adjudication_immutable
  BEFORE UPDATE OR DELETE ON human_eval_adjudication
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();
CREATE TRIGGER human_eval_release_immutable
  BEFORE UPDATE OR DELETE ON human_eval_release
  FOR EACH ROW EXECUTE FUNCTION human_eval_immutable();

-- ---------------------------------------------------------------------------
-- Row-level security — ENABLE + FORCE on every eval table; the permissive
-- policies name exactly which role may do what, and every other role is
-- denied by default.
-- ---------------------------------------------------------------------------
ALTER TABLE human_eval_campaign ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_campaign FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_manifest ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_manifest FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_sample ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_sample FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_packet ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_packet FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_assignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_assignment FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_attestation ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_attestation FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_label ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_label FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_adjudication ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_adjudication FORCE ROW LEVEL SECURITY;
ALTER TABLE human_eval_release ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_eval_release FORCE ROW LEVEL SECURITY;

-- Prep surface: sig_eval_admin reads/writes the preparation tables.
CREATE POLICY hec_admin ON human_eval_campaign
  AS PERMISSIVE FOR ALL TO sig_eval_admin USING (true) WITH CHECK (true);
CREATE POLICY hem_admin ON human_eval_manifest
  AS PERMISSIVE FOR ALL TO sig_eval_admin USING (true) WITH CHECK (true);
CREATE POLICY hes_admin ON human_eval_sample
  AS PERMISSIVE FOR ALL TO sig_eval_admin USING (true) WITH CHECK (true);
CREATE POLICY hep_admin ON human_eval_packet
  AS PERMISSIVE FOR ALL TO sig_eval_admin USING (true) WITH CHECK (true);
CREATE POLICY hea_admin ON human_eval_assignment
  AS PERMISSIVE FOR ALL TO sig_eval_admin USING (true) WITH CHECK (true);
CREATE POLICY hat_admin ON human_eval_attestation
  AS PERMISSIVE FOR ALL TO sig_eval_admin USING (true) WITH CHECK (true);

-- Reviewer isolation: the session GUC sig.eval_reviewer names the one
-- pseudonymous reviewer id this session may act as. Own assignments, own
-- attestations, own labels — and packets only for assigned samples.
CREATE POLICY hea_reviewer ON human_eval_assignment
  AS PERMISSIVE FOR SELECT TO sig_eval_reviewer
  USING (reviewer_id = nullif(current_setting('sig.eval_reviewer', true), ''));
CREATE POLICY hat_reviewer ON human_eval_attestation
  AS PERMISSIVE FOR ALL TO sig_eval_reviewer
  USING (reviewer_id = nullif(current_setting('sig.eval_reviewer', true), ''))
  WITH CHECK (reviewer_id = nullif(current_setting('sig.eval_reviewer', true), ''));
CREATE POLICY hel_reviewer ON human_eval_label
  AS PERMISSIVE FOR ALL TO sig_eval_reviewer
  USING (reviewer_id = nullif(current_setting('sig.eval_reviewer', true), ''))
  WITH CHECK (reviewer_id = nullif(current_setting('sig.eval_reviewer', true), ''));
CREATE POLICY hep_reviewer ON human_eval_packet
  AS PERMISSIVE FOR SELECT TO sig_eval_reviewer
  USING (EXISTS (
    SELECT 1 FROM human_eval_assignment a
     WHERE a.campaign_id = human_eval_packet.campaign_id
       AND a.sample_id = human_eval_packet.sample_id
       AND a.reviewer_id = nullif(current_setting('sig.eval_reviewer', true), '')
  ));

-- Custodian: the sealing authority reads every eval table; writes only the
-- release decisions, adjudications and attestation records (labels are
-- reviewer-written only — the custodian cannot mint a human label).
CREATE POLICY hec_custodian ON human_eval_campaign
  AS PERMISSIVE FOR SELECT TO sig_eval_custodian USING (true);
CREATE POLICY hem_custodian ON human_eval_manifest
  AS PERMISSIVE FOR SELECT TO sig_eval_custodian USING (true);
CREATE POLICY hes_custodian ON human_eval_sample
  AS PERMISSIVE FOR SELECT TO sig_eval_custodian USING (true);
CREATE POLICY hep_custodian ON human_eval_packet
  AS PERMISSIVE FOR SELECT TO sig_eval_custodian USING (true);
CREATE POLICY hea_custodian ON human_eval_assignment
  AS PERMISSIVE FOR SELECT TO sig_eval_custodian USING (true);
CREATE POLICY hat_custodian ON human_eval_attestation
  AS PERMISSIVE FOR ALL TO sig_eval_custodian USING (true) WITH CHECK (true);
CREATE POLICY hel_custodian ON human_eval_label
  AS PERMISSIVE FOR SELECT TO sig_eval_custodian USING (true);
CREATE POLICY hadj_custodian ON human_eval_adjudication
  AS PERMISSIVE FOR ALL TO sig_eval_custodian USING (true) WITH CHECK (true);
CREATE POLICY hrel_custodian ON human_eval_release
  AS PERMISSIVE FOR ALL TO sig_eval_custodian USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- Grants — privileges AND RLS both bind (never either/or).
-- ---------------------------------------------------------------------------
GRANT SELECT, INSERT ON human_eval_campaign, human_eval_manifest,
     human_eval_sample, human_eval_packet, human_eval_assignment,
     human_eval_attestation TO sig_eval_admin;
GRANT SELECT ON human_eval_label_released, human_eval_adjudication_released
  TO sig_eval_admin;

GRANT SELECT ON human_eval_packet, human_eval_assignment,
     human_eval_attestation, human_eval_label TO sig_eval_reviewer;
GRANT INSERT ON human_eval_label, human_eval_attestation TO sig_eval_reviewer;

GRANT SELECT ON human_eval_campaign, human_eval_manifest, human_eval_sample,
     human_eval_packet, human_eval_assignment, human_eval_attestation,
     human_eval_label, human_eval_adjudication, human_eval_release,
     human_eval_label_released, human_eval_adjudication_released
  TO sig_eval_custodian;
GRANT INSERT ON human_eval_release, human_eval_adjudication,
     human_eval_attestation TO sig_eval_custodian;

-- The clustering/materialization role may read ONLY the operational-scope
-- released views — which are empty until an authorized operational release.
-- No grant on any base eval table: sealed labels are unreachable.
GRANT SELECT ON human_eval_label_operational,
     human_eval_adjudication_operational TO sig_materialize;

-- No UPDATE/DELETE/TRUNCATE for any application role (SIG-STORE-012).
REVOKE UPDATE, DELETE, TRUNCATE ON human_eval_campaign, human_eval_manifest,
  human_eval_sample, human_eval_packet, human_eval_assignment,
  human_eval_attestation, human_eval_label, human_eval_adjudication,
  human_eval_release
  FROM PUBLIC, sig_eval_admin, sig_eval_reviewer, sig_eval_custodian,
       sig_materialize, sig_read_public, sig_read_restricted, sig_read_sealed,
       sig_export, sig_ingest;

-- The deploying login may SET ROLE into all three eval roles (test + tooling).
DO $$ BEGIN
  EXECUTE format('GRANT sig_eval_admin TO %I', current_user);
  EXECUTE format('GRANT sig_eval_reviewer TO %I', current_user);
  EXECUTE format('GRANT sig_eval_custodian TO %I', current_user);
END $$;

COMMIT;
