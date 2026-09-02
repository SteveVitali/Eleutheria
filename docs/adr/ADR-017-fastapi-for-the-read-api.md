# ADR-017: FastAPI for the read API

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-API-001
- **Spec:** docs/2_canonical_design_spec.md §47, §37

## Context

SIG needs a documented, typed read API with as-of handling and an OpenAPI contract; this is a lower-stakes default.

## Decision

Use FastAPI for the read API, with generated OpenAPI and Pydantic models.

## Consequences

Typed request/response models, automatic OpenAPI, good async support. Ties the API layer to FastAPI/Starlette.

## Alternatives considered

Flask (no built-in typing/OpenAPI); Django REST (heavier than a read-only API needs).

## Revisit trigger

The API grows needs FastAPI cannot serve, or its maintenance posture changes materially.
