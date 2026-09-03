# ADR-024: A pinned, deterministic, in-repo EDTF envelope derivation

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P02.3
- **Requirement ids:** SIG-STORE-021, SIG-STORE-022, SIG-TIME-006
- **Spec:** docs/2_canonical_design_spec.md §16.7

## Context

ADR-004 chose EDTF for uncertain dates. §16.7 further requires that each stored
EDTF string (`valid_edtf`, `observed_edtf`, `published_at_edtf`) also carry a
machine-usable `tstzrange` envelope derived by a **pinned, versioned,
deterministic** function whose widening rules are recorded in `ruleset_version`
— so a re-derivation is reproducible and "early 2025" never sharpens to
`2025-01-01`. The available third-party EDTF libraries either target other date
libraries, are not deterministic across releases, or do not expose the widening
policy as a versioned, inspectable artifact.

## Decision

Own the envelope derivation in-repo (`db.edtf`), stdlib-only, as a total function
over the EDTF Level 1 subset SIG uses. The widening rules (approximate `~`/`%`
widen; uncertain `?` does not; per-precision slop constants) are the entire
content of a single pinned identifier, `ENVELOPE_RULESET_VERSION`
(`"edtf-envelope-1"`), which an `ingest_run` stamps in `ruleset_version`. The same
EDTF string always yields the same envelope; a mismatched `ruleset_version` is
refused rather than silently re-widened.

## Consequences

The derivation is dependency-free and cannot drift with a third-party release;
the widening policy is auditable and versioned; every read path shares one
envelope function. SIG carries the (small) maintenance of a Level 1 parser, and
Level 2 EDTF is explicitly unsupported until a requirement needs it.

## Alternatives considered

A third-party EDTF library (non-deterministic across versions; widening policy
not versioned or inspectable); deriving the envelope in SQL (EDTF parsing in
PL/pgSQL is brittle and hard to test); storing only the envelope and discarding
the EDTF string (loses the imprecision EDTF exists to preserve — a P4 violation).

## Revisit trigger

A maintained, deterministic, permissively-licensed EDTF Level 1 library exposes a
versionable widening policy, or SIG data requires EDTF Level 2 features.
