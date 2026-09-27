# ADR-121 — Typed assertion envelope, actual-capture bindings, and safe omission of unregistered predicates (P32.2)

- Date: 2026-09-28
- Status: accepted (engineering; offline-only — no live fetch, publication or gate action)
- Ticket: P32.2 (Round 10 / S1, row 162; requirements SIG-TRUST-001, SIG-TRUST-002; closes the route half of D-P31.1-3; backlog home BL-058)
- Base: `ebd34ce` (the P32.1 tip `devin/p32-1-baseline-and-memory-audit`)

## Context

Before this change every claim written by `PgClaimSink` was bound to a **synthetic** per-`(source, genre, run)` evidence artifact — the connector's real captured bytes (already archived by `OcflCaptureStore` since P21.3/P31.4) never reached `claim_evidence`. Typed connector semantics were also flattened at the sink boundary: units, raw lexical values, temporal bounds, epistemic axes, sensitivity, revision links and qualifiers had no columns to land in, so the spine could not preserve what the adapter contract calls the *assertion* (the §10 record), only its coarse shadow. Three consequences followed: provenance claims were weaker than the bytes that supported them; replay could not demonstrate it was bound to the same occurrence the original extraction consumed; and the entity route (D-P31.1-3) turned an unregistered predicate's `KeyError` into a whole-entity 404, suppressing admissible facts.

## Decision

1. **A versioned typed-assertion envelope, adapted once.** `db.assertion` defines `sig.assertion/1`: the complete field set a connector record may carry (typed value + raw lexical value + raw context, unit + normalization id/version, valid/observed time with explicit bound kinds and unknown-reasons, reliability/directness/integrity + provisional + legacy source tier, polarity/rank/review-status, sensitivity tier, rationale, revision/retraction/correction links, evidence role, extraction method/version/config-digest/model/prompt, locators, qualifiers). The connector→sink mapping is the named, versioned **`sig.assertion.map.v1`**: every field a record did not carry receives its default with an explicit basis string recorded on the claim (`assertion_map_basis`), so a default is never silently evidence-strengthening (absent reliability stays `R3` labelled `absent_default`, absent time stays `unknown` with a recorded unknown-reason).
2. **Actual occurrences are first-class; the binding says which kind.** `evidence_blob` deduplicates identical bytes per artifact (`(blob_digest, artifact)`); `evidence_capture` rows are the immutable acquisition occurrences — keyed on `(artifact_id, content_digest, retrieved_at)` so identical bytes fetched twice are ONE blob and TWO occurrences, each carrying its own `retrieved_at`/`retrieved_by_run_id`/`ocfl_version`/`capture_classification` (`actual` | `synthetic` | `legacy`). `CaptureRef` now carries `ocfl_object_id`/`ocfl_version`/`original_run_id`; `OcflCaptureStore.get/metadata` accept a version pin so a replay resolves the version the original extraction consumed — never a mutable head sidecar.
3. **Replay binds the ORIGINAL occurrence.** A replayed assertion reuses the original `evidence_capture` row (its `retrieved_at` is the source observation time; `retrieved_by_run_id` stays the original run's) and marks `claim_evidence.binding_status = 'replayed'` — the replay's own assertion time lives on `claim.sys_period`/`bound_at`/`ingest_run`. Live claims with a typed locator bind `actual_capture`; a real capture without claim-level locators binds `document_only` (the honest limitation); the no-binding legacy path binds `legacy_synthetic` on a `synthetic` capture — never presented as byte-anchored provenance.
4. **Unknown semantics fail closed into `assertion_quarantine`.** Bad digests, missing capture bindings, unknown object/value kinds, unsupported locator kinds, missing required fields, unknown qualifiers, unknown predicates, version mismatches and extraction failures append a quarantine row (reason + connector + subject/predicate refs + the complete payload + a deterministic `payload_digest` making re-runs +0). The table is append-only and granted to `sig_read_restricted`/`sig_read_sealed` only — auditable internally, never on the public surface. A rejected record never suppresses a valid sibling.
5. **`claim_evidence` is append-only.** The new link columns (locator, binding_status, extractor_version, extraction_config_digest) are written once at insert; the historical delete-and-relink test path is gone — a re-sighting adds a link row, it never rewrites one.
6. **The entity route serves registered facts past unknown predicates (D-P31.1-3 route half).** `/v1/entity/{type}/{id}` resolves each of the entity's predicates independently: registered ones go through the normal eligibility policy; resolver `KeyError`s collect into an explicit `unregistered_predicates` field on `EntityResponse` — never a whole-entity 404, never a guessed definition. The direct `/v1/resolution/{id}/{predicate}` route keeps its honest 404 for an unknown predicate, restricted claims stay withheld and unnamed, and a truly absent entity still 404s.
7. **Registered vocabulary only.** Qualifier ids must exist in `vocab_predicate` before use — the sink registers nothing implicitly; `claim.normalization_id` resolves through `vocab_normalization`. No person entity is minted anywhere on this path (Part VIII; the existing `_REFUSED_OBJECT_TYPES` check stands).

## Alternatives considered

- **Keep synthetic captures for all writes** — rejected: the bytes exist but the spine could not prove the claim was extracted from them; SIG-TRUST-002 requires the actual occurrence.
- **Mutable 'latest' locators** (link claims to the object, resolve head at read time) — rejected: a later acquisition would silently re-anchor every historical claim; the version pin is cheap and immutable.
- **Register unknown predicates automatically at ingest** — rejected: it would fabricate semantics for data the ruleset never reviewed; quarantine keeps the claim auditable without inventing it.
- **Whole-entity 404 on any unknown predicate (status quo)** — rejected: it hides admissible registered facts, the exact D-P31.1-3 defect.
- **In-place edit of deployed migrations** — rejected per SIG-STORE-041/042; `claim_assertion_bindings` is a new additive sqitch change.

## Consequences

- The `ClaimSink` protocol gains a keyword-only `capture` argument; every test/double sink signature updated (additive, back-compat for production sinks through the runner/pipeline pass-through).
- `db` depends on `sig-parsing` for the single-source `LocatorKind` contract (leaf package; no cycle).
- Claims asserted before this change read back exactly as before (`document_only`/`legacy_synthetic` statuses are honest labels, not new data).
- A binding whose declared `ocfl_version` disagrees with the stored occurrence quarantines (`version_mismatch`) instead of silently re-anchoring.

## Revisit trigger

Revisit when a connector needs a locator kind outside `parsing.LocatorKind` (extend the enum + `sig.assertion.map` version), when the `sig.assertion/1` envelope needs a field that changes claim identity (versioned map bump + ADR), when a release/consumer needs quarantine content surfaced (a reviewed disclosure path, never direct exposure), or when the `unregistered_predicates` surface proves insufficient for downstream clients (add typed unresolved-fact envelopes rather than loosening resolution).
