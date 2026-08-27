# ADR-023: An `evidence/` package, and content-addressed blob dedup for the capture row

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P02.2
- **Requirement ids:** SIG-EVID-004, SIG-EVID-005, SIG-ENG-012
- **Spec:** docs/2_canonical_design_spec.md §17 (implements ADR-006)

## Context

P02.2 implements the OCFL write-once evidence store (§17): content addressing,
the OCFL layout, the capture pipeline, storage tiers, and disappearance handling.
Two decisions were forced by the spec-as-written and are recorded here.

1. **Where the code lives.** The frozen §47 repository layout (SIG-ENG-012) names
   thirteen Python packages; none of them is an obvious home for a cross-cutting,
   connector-facing evidence-store *library* (the OCFL writer/reader, the digest
   codec, the tier model, the capture packager). `db/` is sqitch migrations;
   `connectors/` is one-package-per-source acquisition; `parsing/` is extraction.

2. **The dedup key vs. the capture row.** §17.2 (SIG-EVID-004) states both that
   deduplication is by digest — "a portal page fetched daily that has not changed
   produces one stored blob and **N capture rows**" — and that
   `(content_digest, source_uri)` is unique. P02.1 shipped
   `evidence_capture UNIQUE (content_digest, artifact_id)`, which *blocks* the N
   capture rows: a re-fetch of unchanged bytes would collide. The two statements
   are reconcilable only if the uniqueness lives on the deduplicated **blob**, not
   on the capture row.

## Decision

1. Add a new top-level workspace package **`evidence/`** (`sig-evidence`) as the
   home for the §17 store, rather than overloading `db/`, `connectors/`, or
   `parsing/`. It is registered as a uv workspace member and in
   `tests/support.py::ADR_EXTENSION_PACKAGES`, so the package-layout tests treat
   it as an ADR-sanctioned addition to §47 rather than a violation of it.

2. Introduce **`evidence_blob(blob_digest, source_uri)`** as the deduplicated
   blob registry, with `PRIMARY KEY (blob_digest, source_uri)` carrying the
   SIG-EVID-004 uniqueness. Drop the P02.1
   `evidence_capture UNIQUE (content_digest, artifact_id)` so a daily re-fetch of
   unchanged bytes records another capture row while pointing at the one blob.
   `evidence_capture` gains `source_uri` + `blob_digest` (an FK to the blob) and
   `redaction_version` (SIG-EVID-011). This is a new sqitch change
   (`evidence_store`), never an in-place edit of P02.1 (SIG-STORE-042).

## Consequences

The §17 library is usable by every connector without importing `db` or a
source-specific package. "One blob, N capture rows" is now physically true and
tested against a live PG18. Bytes are still write-once; the layout after this is
migration-only. Live browser capture (Playwright) is an optional `capture` extra
so the store, OCFL layer, and packaging stay usable and testable without a
browser (mirroring how the DB tests gate on Docker).

## Alternatives considered

Putting the library in `parsing/` or `connectors/` (rejected: it is neither
extraction nor a single source's acquisition, and every connector depends on it);
keeping the P02.1 capture uniqueness and forcing one row per distinct bytes
(rejected: it contradicts SIG-EVID-004's "N capture rows" and loses the
per-fetch record §17.6 depends on).

## Revisit trigger

§47 is amended to name an evidence package (fold `evidence/` into it), or the
evidence-store contract moves to per-fetch content addressing that makes the
separate blob registry redundant.
