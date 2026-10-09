-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:intake_storage from pg
--
-- P32.16 / ADR-135 (SIG-FIND-006): drop the isolated intake schema, its guards,
-- functions and view, and the two service roles. Reverting removes the whole
-- receiver surface — quarantined payloads and the audit log included — which is
-- the correct teardown for a not-yet-operational surface (deployment is gated;
-- D-R10-PUBLISH-1). A LIVE receiver's retention schedule owns any payload
-- handling before a revert — the operator packet says so.

BEGIN;

DROP VIEW IF EXISTS intake.report_public;
-- Tables first: their triggers depend on the guard functions, so the
-- functions can only drop once the owning tables (and triggers) are gone.
DROP TABLE IF EXISTS intake.event;
DROP TABLE IF EXISTS intake.receipt;
DROP TABLE IF EXISTS intake.reporter_contact;
DROP TABLE IF EXISTS intake.report;
DROP FUNCTION IF EXISTS intake.public_state(text);
DROP FUNCTION IF EXISTS intake.expunge_report(uuid);
DROP FUNCTION IF EXISTS intake.redact_report(uuid,text[],text);
DROP FUNCTION IF EXISTS intake.contact_mutation_guard();
DROP FUNCTION IF EXISTS intake.report_mutation_guard();
DROP FUNCTION IF EXISTS intake.append_only_guard();
DROP FUNCTION IF EXISTS intake.event_writer_guard();
DROP SCHEMA IF EXISTS intake;

DROP ROLE IF EXISTS sig_intake_receiver;
DROP ROLE IF EXISTS sig_intake_reviewer;

COMMIT;
