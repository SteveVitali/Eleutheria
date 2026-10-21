# ADR-213 — Declared lineage, identifier namespaces, and declared independence classes (P35.25)

- Date: 2026-10-18
- Status: accepted
- Ticket: P35.25 (Round 11 / P35 sub-round 11B, manifest row `R11-L3-CP4`,
  ticket 304 — the L3-confidence-program's CP-4; owner requirement
  **SIG-CONF-014**; cites SIG-EPIS-009, SIG-EPIS-029, SIG-IDENT-005, CONF-04,
  S6 A-20, GQ-11, ADR-211/ADR-212)
- Base: `r11/P35.24-truthful-subject-keys-and-re-keying`
- Related: ADR-110 (identity keys are identity-bearing, append-only),
  ADR-211 (claim-identity classes), ADR-212 (truthful subject keys — the
  dependency: lineage binds after keys are truthful), ADR-146 (the
  materialization layer's append discipline the rematerialize inherits),
  GQ-11 (the camera lineage/copy-disclosure quality rule this row feeds).

## Context

Corroboration is only as truthful as the independence it asserts. Two
defects let the graph overstate its support:

1. **Mirrored data read as independent.** A registry that republishes
   another source's rows (a mirror, a syndicated copy, a derived pack)
   asserted each row as its own observation. Two rows with one upstream
   origin counted as two voices — the copied record corroborated its
   original — because the lineage relation was never declared or stored.
2. **Bare identifiers merged across namespaces.** An upstream id is
   meaningful only inside its namespace. Two sources' coincidentally-equal
   local ids (`ref = "101"`) read as one upstream row: the camera-site
   resolver's tier-1g shared-ref evidence and any identifier-equality join
   treated the bare value as namespace-free, merging unrelated records.

Downstream, reconcile's corroboration count and confidence scoring read
row counts, not independence — so copied or undeclared content inflated
confidence (SIG-CONF-014's violation). SIG-EPIS-009 already declares
`derived_from_claim_ids` at the typed-assertion layer, but the value was
not persisted per claim, so derivation ancestry was not recoverable.

## Decision

Lineage, namespace, and independence become **declared, persisted,
immutable facts**, with honest defaults and fail-closed unknowns.

### Declared source lineage (registry)

`sources.toml` rows gain additive lineage fields — `kind`
(`primary`/`mirror`/`derived`/`syndicated`/`undeclared`), `origin`,
`mirror_of`, `derived_from`, `independence_class` (`src:<source-id>`,
`ext:<slug>`, or `unclassified`), and `id_namespace`. `connectors.registry`
fails closed on dangling lineage references, self-references, invalid
kinds/classes/namespaces, and declared-but-unfounded mirrors
(missing evidence). `assert_loadable` is untouched: lineage metadata
never changes `ingestion_permitted`. A source without a declaration is
`undeclared`/`unclassified` — **unknown lineage never reads as
independent**.

### Per-claim lineage (spine)

Sqitch `declared_lineage` lands:

- `source_lineage` — versioned `(source_id, registry_version)` mirror of
  the committed declarations; immutable (UPDATE/DELETE triggers refuse).
- `source_lineage_current` — the latest declaration per source.
- `claim_lineage` — one row per claim: `source_id`, `id_namespace`,
  `lineage_kind`, `independence_class`, `basis` (what the row was derived
  from — registry mirror, per-claim override, rematerialize inference),
  `derived_from_claim_ids` (SIG-EPIS-009 persisted), `recorded_at`.
  One-row-per-claim barrier via the primary key; unknowns are explicit
  non-null tokens (`undeclared`/`unclassified`), never NULL-as-independent.

`PgClaimSink` inserts each new claim's lineage in the same transaction as
the claim (`ON CONFLICT DO NOTHING` for idempotent replays). A claim-level
`id_namespace` override is honoured only against the committed vocabulary
in `db/src/db/data/id_namespaces.toml` (`sig.id-namespaces/1`); anything
else quarantines `unknown_id_namespace` (a new reason the quarantine
CHECK widens to admit — restoring every predecessor reason, including
`unknown_genre`/`unknown_subject_scheme`). Grants: `sig_ingest` SELECTs
declarations + INSERTs claim rows; `sig_materialize` INSERTs both (the
rematerialize role); `sig_read_restricted`/`sig_export` SELECT.
**`sig_read_public` gains no grant** — the §37 published-surface allowlist
is exact and this row does not widen it.

### Namespace-qualified identity

Identifier equality now composes `(id_namespace, value)`. The camera-site
resolver's tier-1g shared-ref rule fires only inside a **shared declared
namespace** — a mirror carrying its upstream's id space declares that
namespace (e.g. `dot_511`); equal bare refs in different or undeclared
namespaces never join. `undeclared` never matches `undeclared` as shared
evidence: two unknowns are not one known.

### Independence-aware corroboration

Reconcile/materialize reads `independence_class` from the declared map:
corroboration counts across **distinct declared classes** only; claims in
one class (a mirror and its original sharing `src:<upstream>` or a
declared `ext:` upstream) are one voice; `unclassified` claims are
disclosed and never counted as independent. Export observation envelopes
disclose `n_independence_classes` and `n_unclassified_candidates` so the
published basis is inspectable.

### The append-only rematerialize

`sig-db lineage-rematerialize` (`db/lineage_rematerialize.py`) mirrors
the committed declarations into `source_lineage` and back-populates
`claim_lineage` for claims lacking a row — resolving each claim's source
through `claim_evidence → evidence_capture → evidence_artifact.source_id`,
copying any persisted `derived_from_claim_ids`, and writing explicit
`undeclared`/`unclassified` where resolution is absent or ambiguous
(no lineage is ever fabricated). Plan (dry-run) is the default; `--apply`
writes; `--limit`/`--batch-size` bound; the scan is keyset-ordered and
resumable; reruns are +0 (existing rows are skipped, never updated or
deleted). The hosted run is a queued OM-19/OM-20 leg.

### Basis disclosure (S6 A-20)

Because back-populating lineage changes the independence basis of some
API answers, the change is disclosed rather than silent: the basis
middleware carries opt-in notices (`SIG_API_BASIS_NOTICES` →
`basis.notices`), and the `/status/` sentence is staged in copy batch 02
(`ST-11`, pending operator confirmation — never shipped as pending copy).

## Consequences

- Two upstream ids now need a declared shared namespace to merge — the
  P31.10/P31.11 test fixtures declare `dot_511` on their ref-claim
  lineage, which is also the honest modelling of what those fixtures
  meant (a mirror carrying the DOT feed's own ids).
- `assertion_quarantine`'s reason CHECK is rewritten to the full union of
  predecessor reasons plus `unknown_id_namespace`; revert restores the
  predecessor vocabulary.
- The public read surface is unchanged; restricted/export readers see
  lineage tables.
- Live legs (merge, registry mirror + rematerialize on the hosted spine,
  `/status/` notice, L3 completeness verification) are queued under
  RETURN PASS; OM-20 names P35.25 conditionally (GATE-G4 §4,
  2026-10-09T17:32Z).

## Revisit trigger

Revisit when a claim must carry lineage from **multiple** upstream
sources at once (one row per claim suffices while each claim has one
asserting source), when a genuinely unknown upstream gains enough
evidence to declare (new registry declaration + rematerialize run, never
a guess), or when `sig_read_public` needs lineage visibility (requires a
§37 surface decision and a new ADR).
