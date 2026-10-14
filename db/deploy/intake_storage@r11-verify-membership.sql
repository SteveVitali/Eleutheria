-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:intake_storage to pg
--
-- P32.16 / ADR-135 (§55.5 SIG-FIND-006; S4 research §8): the durable anonymous
-- correction receiver's ISOLATED storage. A separate `intake` schema holds the
-- quarantined payload store, the receipt capability, the append-only reviewer
-- event log and the restricted-contact side table — deliberately OUTSIDE the
-- append-only claim spine and the WORM evidence store because unreviewed input
-- must be expungeable, and deliberately unreachable from every existing role:
-- `sig_intake_receiver` can only INSERT payloads + read the coarse public
-- projection; `sig_intake_reviewer` can only read payloads and append reviewer
-- events; neither can write claim/review_decision/publication_disposition, and
-- no public/read/export/ingest/materialize role holds any intake grant.
--
-- Event vocabulary (policy/data/intake_receiver.toml is the source of truth the
-- CHECK below mirrors): received, triaged, assigned, review_requested,
-- disposition_proposed, disposition_approved, applied, published, closed +
-- housekeeping redacted, expunged. `applied`/`published` are RESERVED for the
-- P32.16a authorized bridge role — the writer-guard trigger refuses them until
-- that role exists and is used.
--
-- Role writes are enforced by session state, not grants alone: the event writer
-- guard reads `current_setting('role')` so a report row's `received` event can
-- only be appended under SET ROLE sig_intake_receiver and reviewer events only
-- under SET ROLE sig_intake_reviewer — a stolen or misused credential cannot
-- cross the boundary.

BEGIN;

-- Roles (NOLOGIN groups; services SET ROLE after connecting with a narrow login
-- that is GRANTed membership — the operating packet records the provisioning).
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_intake_receiver') THEN
    CREATE ROLE sig_intake_receiver NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sig_intake_reviewer') THEN
    CREATE ROLE sig_intake_reviewer NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

CREATE SCHEMA intake;

-- ---------------------------------------------------------------------------
-- 1. The quarantined payload store. One row per accepted report; identity
--    fields (report_id/receipt_id/idempotency_key/category/received_at) are
--    immutable; only the payload columns + expunged_at may change, and only via
--    the SECURITY DEFINER maintenance functions (no UPDATE grant exists).
-- ---------------------------------------------------------------------------
CREATE TABLE intake.report (
  report_id       uuid PRIMARY KEY,
  receipt_id      text NOT NULL UNIQUE
                  CHECK (receipt_id ~ '^rct-[0-9a-f]{32}$'),
  idempotency_key text NOT NULL UNIQUE
                  CHECK (idempotency_key ~ '^[A-Za-z0-9_-]{16,128}$'),
  category        text NOT NULL,
  publication_id  text CHECK (publication_id ~ '^p-[0-9a-f]{64}$'),
  record_key      text CHECK (record_key ~ '^[a-z0-9_-]{1,64}(:[a-z0-9_-]{1,64}){2}$'),
  claim_ids       jsonb NOT NULL DEFAULT '[]'::jsonb,
  description     text NOT NULL,
  evidence_urls   jsonb NOT NULL DEFAULT '[]'::jsonb,
  received_at     timestamptz NOT NULL DEFAULT clock_timestamp(),
  expunged_at     timestamptz
);

COMMENT ON TABLE intake.report IS
  'P32.16/ADR-135 (SIG-FIND-006): the quarantined anonymous-report payload '
  'store — outside the claim spine by design (unreviewed input is expungeable). '
  'Never published, never search-indexed, never evidence-archived. Payload '
  'columns are mutable ONLY through the retention/redaction functions; identity '
  'columns are immutable and rows are never deleted (expunge blanks payloads).';

-- The legal-demand contact channel, retained SEPARATELY and restricted to the
-- reviewer role (S4 §8: "retained separately/restricted"). Deleted wholesale by
-- redaction/expunge — a row's existence is the only audit fact; the event log
-- records the action.
CREATE TABLE intake.reporter_contact (
  report_id  uuid PRIMARY KEY REFERENCES intake.report,
  contact    text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

-- The receipt capability: only the keyed digest of the one-purpose bearer
-- status token is stored (never the token). The reporter-facing receipt id
-- lives on intake.report (unguessable, non-enumerating).
CREATE TABLE intake.receipt (
  report_id    uuid PRIMARY KEY REFERENCES intake.report,
  token_digest bytea NOT NULL UNIQUE CHECK (octet_length(token_digest) = 32),
  issued_at    timestamptz NOT NULL DEFAULT clock_timestamp()
);

-- ---------------------------------------------------------------------------
-- 2. The append-only intake event log (S4 §8 step 2). Stores receipt/actor
--    role/times/safe reference ids/sanitized reason — never raw body, contact
--    or network identifiers (the detail keys are validated app-side).
-- ---------------------------------------------------------------------------
CREATE TABLE intake.event (
  event_seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  report_id uuid NOT NULL REFERENCES intake.report,
  event     text NOT NULL
            CHECK (event IN ('received','triaged','assigned','review_requested',
                             'disposition_proposed','disposition_approved',
                             'applied','published','closed',
                             'redacted','expunged')),
  actor     text NOT NULL,
  at        timestamptz NOT NULL DEFAULT clock_timestamp(),
  detail    jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX intake_event_report_idx ON intake.event (report_id, event_seq);

COMMENT ON TABLE intake.event IS
  'P32.16/ADR-135: the restricted append-only intake audit log. applied and '
  'published are reserved for the P32.16a bridge — the writer-guard trigger '
  'refuses them for every current role. Metadata only: no raw body, contact or '
  'network identifiers.';

-- ---------------------------------------------------------------------------
-- 3. Guards.
-- ---------------------------------------------------------------------------

-- The event writer guard: `received` only under SET ROLE sig_intake_receiver
-- (with the fixed receiver actor); every other lifecycle/housekeeping event
-- only under SET ROLE sig_intake_reviewer; applied/preserved refused for all.
CREATE FUNCTION intake.event_writer_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$
DECLARE
  session_role text := current_setting('role', true);
BEGIN
  IF NEW.event IN ('applied','published') THEN
    RAISE EXCEPTION
      'intake event % is reserved for the P32.16a authorized bridge role (SIG-FIND-008)',
      NEW.event
      USING ERRCODE = 'insufficient_privilege';
  ELSIF NEW.event = 'received' THEN
    IF COALESCE(session_role,'') <> 'sig_intake_receiver'
       OR NEW.actor <> 'sig-intake-receiver' THEN
      RAISE EXCEPTION
        'the intake received event may be appended only under SET ROLE sig_intake_receiver with actor sig-intake-receiver'
        USING ERRCODE = 'insufficient_privilege';
    END IF;
  ELSE
    IF COALESCE(session_role,'') <> 'sig_intake_reviewer' THEN
      RAISE EXCEPTION
        'intake event % requires SET ROLE sig_intake_reviewer',
        NEW.event
        USING ERRCODE = 'insufficient_privilege';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER intake_event_writer_guard
  BEFORE INSERT ON intake.event
  FOR EACH ROW EXECUTE FUNCTION intake.event_writer_guard();

-- Append-only for receipt and event (no UPDATE/DELETE ever; no grants either).
CREATE FUNCTION intake.append_only_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% is append-only — UPDATE/DELETE refused', TG_TABLE_NAME
    USING ERRCODE = 'raise_exception';
END $$;

CREATE TRIGGER intake_receipt_immutable
  BEFORE UPDATE OR DELETE ON intake.receipt
  FOR EACH ROW EXECUTE FUNCTION intake.append_only_guard();

CREATE TRIGGER intake_event_immutable
  BEFORE UPDATE OR DELETE ON intake.event
  FOR EACH ROW EXECUTE FUNCTION intake.append_only_guard();

-- The report row is never deleted; UPDATE is reachable only through the
-- SECURITY DEFINER maintenance functions (no UPDATE grant exists) and may
-- touch only the payload columns + expunged_at.
CREATE FUNCTION intake.report_mutation_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'intake.report rows are never deleted — payloads are expunged'
      USING ERRCODE = 'raise_exception';
  END IF;
  IF NEW.report_id IS DISTINCT FROM OLD.report_id
     OR NEW.receipt_id IS DISTINCT FROM OLD.receipt_id
     OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
     OR NEW.category IS DISTINCT FROM OLD.category
     OR NEW.received_at IS DISTINCT FROM OLD.received_at THEN
    RAISE EXCEPTION 'intake.report identity fields are immutable'
      USING ERRCODE = 'raise_exception';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER intake_report_mutation_guard
  BEFORE UPDATE OR DELETE ON intake.report
  FOR EACH ROW EXECUTE FUNCTION intake.report_mutation_guard();

-- The restricted contact row is mutable only for a reviewer-session mutation
-- (the SECURITY DEFINER functions below run under the caller's SET ROLE).
-- DELETE must RETURN OLD — returning NEW (NULL on delete) silently skips the
-- row, which would look like a successful redaction that never happened.
CREATE FUNCTION intake.contact_mutation_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$
DECLARE
  session_role text := current_setting('role', true);
BEGIN
  IF COALESCE(session_role,'') <> 'sig_intake_reviewer' THEN
    RAISE EXCEPTION 'intake.reporter_contact may be mutated only by the reviewer maintenance functions'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER intake_contact_mutation_guard
  BEFORE UPDATE OR DELETE ON intake.reporter_contact
  FOR EACH ROW EXECUTE FUNCTION intake.contact_mutation_guard();

-- ---------------------------------------------------------------------------
-- 4. The maintenance functions (SECURITY DEFINER; EXECUTE revoked from PUBLIC
--    and granted to sig_intake_reviewer only).
-- ---------------------------------------------------------------------------

-- Moderator redaction: clears the named payload fields irreversibly and
-- appends a `redacted` audit event. Reversible-looking alternatives (a shadow
-- copy) would defeat the purpose — the public surface never held them and the
-- restricted copy is what reviewers see until cleared.
CREATE FUNCTION intake.redact_report(
  p_report_id uuid, p_fields text[], p_actor text
) RETURNS void
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = intake, pg_catalog AS $$
BEGIN
  IF 'description' = ANY(p_fields) THEN
    UPDATE intake.report SET description = '[redacted]' WHERE report_id = p_report_id;
  END IF;
  IF 'evidence_urls' = ANY(p_fields) THEN
    UPDATE intake.report SET evidence_urls = '[]'::jsonb WHERE report_id = p_report_id;
  END IF;
  IF 'claim_ids' = ANY(p_fields) THEN
    UPDATE intake.report SET claim_ids = '[]'::jsonb WHERE report_id = p_report_id;
  END IF;
  IF 'publication_id' = ANY(p_fields) THEN
    UPDATE intake.report SET publication_id = NULL WHERE report_id = p_report_id;
  END IF;
  IF 'record_key' = ANY(p_fields) THEN
    UPDATE intake.report SET record_key = NULL WHERE report_id = p_report_id;
  END IF;
  IF 'contact' = ANY(p_fields) THEN
    DELETE FROM intake.reporter_contact WHERE report_id = p_report_id;
  END IF;
  INSERT INTO intake.event (report_id, event, actor, detail)
  VALUES (p_report_id, 'redacted', p_actor,
          jsonb_build_object('fields', to_jsonb(p_fields)));
END $$;

-- Retention expunge: clears every payload field + the contact row, stamps
-- expunged_at, appends the `expunged` audit event. The row stays — the event
-- log is the accountability record that a report existed and was expunged.
CREATE FUNCTION intake.expunge_report(p_report_id uuid) RETURNS void
  LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = intake, pg_catalog AS $$
BEGIN
  UPDATE intake.report
     SET description = '[expunged]',
         evidence_urls = '[]'::jsonb,
         claim_ids = '[]'::jsonb,
         publication_id = NULL,
         record_key = NULL,
         expunged_at = clock_timestamp()
   WHERE report_id = p_report_id;
  DELETE FROM intake.reporter_contact WHERE report_id = p_report_id;
  INSERT INTO intake.event (report_id, event, actor, detail)
  VALUES (p_report_id, 'expunged', 'intake-retention', '{}'::jsonb);
END $$;

REVOKE EXECUTE ON FUNCTION intake.redact_report(uuid,text[],text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION intake.expunge_report(uuid) FROM PUBLIC;

-- ---------------------------------------------------------------------------
-- 5. The coarse public projection — the ONLY thing the receiver role may read.
--    Latest lifecycle event → coarse state; the public_response is surfaced
--    only from an event whose detail marks it public_response_publish (S4 §8:
--    "only coarse status and an approved response").
-- ---------------------------------------------------------------------------
CREATE FUNCTION intake.public_state(p_lifecycle text) RETURNS text
  LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE p_lifecycle
    WHEN 'received' THEN 'received'
    WHEN 'triaged' THEN 'under_review'
    WHEN 'assigned' THEN 'under_review'
    WHEN 'review_requested' THEN 'under_review'
    WHEN 'disposition_proposed' THEN 'under_review'
    WHEN 'disposition_approved' THEN 'decided'
    WHEN 'applied' THEN 'decided'
    WHEN 'published' THEN 'resolved'
    WHEN 'closed' THEN 'closed'
    ELSE 'received'
  END $$;

COMMENT ON FUNCTION intake.public_state(text) IS
  'P32.16/ADR-135: SQL twin of policy.intake.public_state — the data contract '
  '(intake_receiver.toml public_status.map) is the source of truth; the PG '
  'parity test in tests/db asserts the two mappings agree on every lifecycle '
  'event.';

CREATE VIEW intake.report_public WITH (security_invoker = off) AS
SELECT r.report_id,
       r.receipt_id,
       r.idempotency_key,
       r.category,
       r.received_at,
       r.expunged_at,
       COALESCE(le.event, 'received') AS lifecycle_event,
       intake.public_state(COALESCE(le.event, 'received')) AS state,
       pr.response AS public_response
  FROM intake.report r
  LEFT JOIN LATERAL (
    SELECT e.event, e.detail
      FROM intake.event e
     WHERE e.report_id = r.report_id
       AND e.event IN ('received','triaged','assigned','review_requested',
                       'disposition_proposed','disposition_approved',
                       'applied','published','closed')
     ORDER BY e.event_seq DESC
     LIMIT 1
  ) le ON true
  LEFT JOIN LATERAL (
    SELECT e.detail->>'public_response' AS response
      FROM intake.event e
     WHERE e.report_id = r.report_id
       AND e.event IN ('disposition_approved','published','closed')
       AND COALESCE((e.detail->>'public_response_publish')::boolean, false)
     ORDER BY e.event_seq DESC
     LIMIT 1
  ) pr ON true;

COMMENT ON VIEW intake.report_public IS
  'P32.16/ADR-135: the receiver-role projection — report_id/receipt_id, '
  'idempotency_key (dedupe), category, received_at, coarse state and the '
  'reviewer-approved public_response only. Raw narrative, contact, URLs and '
  'network identifiers are unreachable from it by construction.';

-- ---------------------------------------------------------------------------
-- 6. Grants — least privilege, and nothing for any existing role.
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA intake TO sig_intake_receiver, sig_intake_reviewer;

-- The public receiver: INSERT payloads + receipt + its own `received` event;
-- read ONLY the coarse projection (for dedupe + status) and the digest column
-- needed to verify a status token.
GRANT INSERT ON intake.report, intake.reporter_contact, intake.receipt, intake.event
  TO sig_intake_receiver;
GRANT SELECT ON intake.report_public TO sig_intake_receiver, sig_intake_reviewer;
GRANT SELECT (report_id, token_digest) ON intake.receipt TO sig_intake_receiver;

-- The private reviewer: read the quarantined payload + audit log, append
-- reviewer events, run the two maintenance functions. No UPDATE/DELETE on
-- anything; no write outside intake.event.
GRANT SELECT ON intake.report, intake.reporter_contact, intake.receipt, intake.event
  TO sig_intake_reviewer;
GRANT INSERT ON intake.event TO sig_intake_reviewer;
GRANT EXECUTE ON FUNCTION intake.redact_report(uuid,text[],text) TO sig_intake_reviewer;
GRANT EXECUTE ON FUNCTION intake.expunge_report(uuid) TO sig_intake_reviewer;

-- ---------------------------------------------------------------------------
-- 7. Deployer membership (P34.46 / D-P34.24b-1 repair — appended to this
--    tagged copy; the rest of the file is the landed script byte-for-byte).
-- The deploying login (the schema owner — `sig` on the hosted spine) may
-- SET ROLE into both intake roles, so this change's own verify — and the
-- later intake verifies that SET ROLE them — are legal on a non-superuser
-- deploy login (the P34.24b clone rehearsal failed `SET LOCAL ROLE
-- sig_intake_receiver` here; Cloud SQL's `sig` holds no membership).
-- Same pattern as materialize_role / recovery_apply / human_eval_campaign.
-- ---------------------------------------------------------------------------
DO $$ BEGIN
  EXECUTE format('GRANT sig_intake_receiver TO %I', current_user);
  EXECUTE format('GRANT sig_intake_reviewer TO %I', current_user);
END $$;

COMMIT;
