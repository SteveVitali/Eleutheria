# ADR-095 — Append-only `rights_decision` log for resolving UNDETERMINED-recorded claims

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.2 (`docs/tickets/P27.2__maximize-publishable-scope.md`) — the mechanism ADR-094's "new `rights_record` rows + source links" lands as
- **Date:** 2026-09-22
- **Related:** ADR-094 (the rights-resolution decision), ADR-061 (the `review_decision` precedent this mirrors), ADR-002/P1–P3 (append-only), SIG-LIC-004 (fail-closed export gate), SIG-LIC-001/002 (packets + archived terms), Part VIII §0.7 (reviewer roles, never names).

## Context

P27.1's audit found ~256k claims recorded under a shared UNDETERMINED `rights_record`.
Their sources were already rights-reviewed (`sources.toml` carries per-source dispositions +
packets), but the *claims'* `rights_id` is assertion-time provenance and the spine forbids
`UPDATE` (`claim_append_only`). A licence review therefore cannot "flip" a claim in place; it
must be recorded as an append-only event that readers resolve through.

## Decision

1. **New `rights_decision` table** (`db/deploy/rights_decisions.sql`): an append-only
   adjudication log — `(source_id, prior_rights_id) -> rights_id` (the resolved record) with
   `basis` (gate + legal basis citation), `reviewer` (a **role**, never a personal name —
   Part VIII §0.7), `review_packet`, `terms_url`, `terms_capture_id` (the archived terms,
   SIG-LIC-002), and DB-clock `decided_at`. A trigger forbids `UPDATE`/`DELETE`; a changed
   disposition is a NEW row whose later `decided_at` wins.
2. **Effective-rights rule.** A claim's effective rights = the latest decision whose
   `prior_rights_id` equals the claim's recorded `rights_id` and whose `source_id` is the
   claim's `claim_evidence('establishes') → evidence_artifact.source_id`; else the recorded
   record. A decision's `prior_rights_id` must reference an UNDETERMINED record (writer-enforced),
   so a decision **can only lift unresolved rights — it can never relicense** an already-resolved
   claim (recorded ODbL stays ODbL).
3. **Writers/readers.** `db.rights_decisions` (the `sig-db rights-decisions` verb) appends the
   reviewed rows from a committed dispositions artifact
   (`docs/build/reports/rights/p272_dispositions.json`); `api.store_pg.rights_for` and
   `exports.audit` resolve effective rights through the same rule. The audit reports BOTH the
   recorded (as-asserted) and effective (post-decision) postures — never conflated.

## Consequences

- UNDETERMINED claims become publishable **with an auditable decision trail** — every flip names
  the source, the resolved record, the basis, the reviewer role, and the DB-clock time.
- The fail-closed gate is untouched: a source with no decision keeps its recorded UNDETERMINED
  rights and still fails closed.
- P27.3/P27.4 (export shaping/bundle) consume the same effective-rights rule.

## Alternatives considered

- **`UPDATE claim.rights_id` / `UPDATE source_registry.rights_id`.** Rejected — forbidden by the
  append-only invariant; it would erase assertion-time provenance.
- **Re-assert corrected claims.** Rejected — doubles claim volume to change metadata the claims
  don't carry wrongly (their recorded rights were honestly UNDETERMINED *at assertion*); the
  resolution is a governance event, not new claim content.
- **Free-standing view only.** Rejected — a view carries no basis/reviewer/packet trail; the
  decision must be a stored, immutable record.

## Revisit trigger

- A rights disposition changes for a source (narrowing, objection, counsel revision) — append a
  NEW `rights_decision`; never edit a row.
- A consumer needs per-claim (not per-source) resolution — extend the log with a claim-scoped
  decision kind in a new ADR.
