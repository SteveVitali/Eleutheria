-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:camera_site_derivation to pg
-- P35.46 / ADR-153 + ADR-L3-B (ruleset v3: derivation collapse + possible
-- duplicates, GQ-23/GQ-24/GQ-25):
--
--   * `camera_site_match.relation_type` widens to the emitted link
--     vocabulary — 'derived_from' (a C0/C1/C2 collapse: provable copies of
--     one upstream record carrying the SHARED site id, never an identity
--     merge), 'possible_duplicate' (every inferential match: recorded with
--     distance and reason, never clustered), 'same_as' (a B5-certified
--     inferential edge or a human accept), 'cannot_link' (a human reject).
--     The link's basis and evidence travel in match_evidence (link_kind,
--     site_id/site_ids, copy_checks, attribute_differences).
--   * `camera_site_match.site_id` — nullable; the shared site id a merged
--     (derived_from / same_as) edge's records carry. Possible-duplicate and
--     cannot-link rows keep NULL — their two sites are the row's entities.
--   * NEW append-only `camera_site_census` — the GQ-23 derivation census of
--     every completed run: the collapse edges re-verified, the failures, the
--     demotion set the NEXT run consumes, and the GQ-25
--     origin-distinctness violation count. One row per run_key; the
--     camera_site_run completion row lands first.
--   * NEW append-only `camera_site_demotion` — (run_key, token, tier,
--     reason): the (lineage-or-source, tier) pairs the NEXT run must keep
--     review-only. A census failure demotes automatically; the demotion a
--     run CONSUMED is part of that run's inputs (in its run key).
--
-- Everything stays append-only: PK/UNIQUE conflicts make re-runs +0, and no
-- role holds UPDATE or DELETE. `sig_materialize` writes the census and the
-- demotions and reads the latest demotion set; `sig_export` selects
-- alongside camera_site_match (the camera-site machinery is off the
-- public_read_allowlist surface by design).

BEGIN;

-- 1) The emitted link vocabulary on the decision log.
DO $$
DECLARE
  con_name text;
BEGIN
  SELECT conname INTO con_name FROM pg_constraint
   WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
     AND pg_get_constraintdef(oid) LIKE '%relation_type%';
  IF con_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE camera_site_match DROP CONSTRAINT %I', con_name);
  END IF;
END $$;
ALTER TABLE camera_site_match
  ADD CONSTRAINT camera_site_match_relation_type_check
  CHECK (relation_type IN ('same_as', 'cannot_link', 'derived_from', 'possible_duplicate'));

ALTER TABLE camera_site_match ADD COLUMN site_id text;
COMMENT ON COLUMN camera_site_match.site_id IS
  'P35.46 (ruleset v3): the shared site id a merged (derived_from | same_as) '
  'edge carries — the resolved-cluster root both records join. NULL on '
  'possible_duplicate / cannot_link rows: their two sites are the row''s '
  'entities. Never an identifier rewrite — the site id is the cluster root '
  'subject id, not a minted entity.';

-- 2) The append-only GQ-23 derivation census: one row per completed run.
CREATE TABLE camera_site_census (
  run_key                     text PRIMARY KEY REFERENCES camera_site_run(run_key),
  checked                     integer NOT NULL CHECK (checked >= 0),
  gq23_failures               integer NOT NULL CHECK (gq23_failures >= 0),
  origin_distinct_violations  integer NOT NULL CHECK (origin_distinct_violations >= 0),
  summary                     jsonb NOT NULL,   -- failures, demote_next_run, clusters
  recorded_at                 timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE camera_site_census IS
  'P35.46 (GQ-23): the derivation census of one completed camera-site ER '
  'run — every applied collapse edge re-verified against the run record '
  'set. gq23_failures counts edges whose conditions no longer verify; '
  'summary carries the per-edge failures, the (token, tier) demotion set '
  'the next run consumes, and the GQ-25 origin-distinctness cluster list. '
  'Append-only: one row per run_key.';

-- 3) The append-only demotion log: the (lineage-or-source, tier) pairs the
--    NEXT run keeps review-only. A census failure demotes automatically.
CREATE TABLE camera_site_demotion (
  run_key     text NOT NULL REFERENCES camera_site_run(run_key),
  token       text NOT NULL,   -- shared source id (C0) | shared lineage token (C1/C2)
  tier        smallint NOT NULL CHECK (tier BETWEEN 0 AND 5),
  reason      text NOT NULL,   -- the census failure reason(s), comma-joined
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (run_key, token, tier)
);

COMMENT ON TABLE camera_site_demotion IS
  'P35.46 (GQ-23): the demotion set a camera-site ER run emitted — the '
  '(lineage-or-source, tier) pairs whose last-run census failed. The next '
  'run reads the latest completed run''s rows and keeps those pairs '
  'review-only (possible_duplicate:census_demoted), so a stale declaration '
  'can collapse for at most one run. Append-only: PK conflicts are +0.';

-- Read surface matches camera_site_match AFTER public_read_allowlist: the
-- camera-site machinery is off the public surface — sig_export selects (the
-- export read role), sig_materialize writes the census/demotions and reads
-- the prior run's demotion set.
GRANT SELECT ON camera_site_census, camera_site_demotion TO sig_export;
GRANT SELECT, INSERT ON camera_site_census, camera_site_demotion TO sig_materialize;

COMMIT;
