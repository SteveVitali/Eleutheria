-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:domain_entities from pg
BEGIN;
DROP TABLE IF EXISTS records_request;
DROP TABLE IF EXISTS legal_proceeding;
DROP TABLE IF EXISTS accountability_event;
DROP TABLE IF EXISTS configuration_state;
DROP TABLE IF EXISTS legal_instrument;
DROP TABLE IF EXISTS policy;
DROP TABLE IF EXISTS funding_instrument;
DROP TABLE IF EXISTS contract;
DROP TABLE IF EXISTS data_system;
DROP TABLE IF EXISTS candidate_asset;
DROP TABLE IF EXISTS physical_asset;
DROP TABLE IF EXISTS deployment;
DROP TABLE IF EXISTS capability;
DROP TABLE IF EXISTS technology;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS person;
DROP TABLE IF EXISTS organization_relation;
DROP TABLE IF EXISTS entity_identifier;
DROP TABLE IF EXISTS organization;
DROP TABLE IF EXISTS jurisdiction;
COMMIT;
