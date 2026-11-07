<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# True deletion and the operator-only purge function

**Status:** adopted design — the mechanism is engineered and fixture-verified
on a clone only (P37.71, manifest row 429, R11-GOV-06). **Written:**
2026-11-06 (`date -u`). The two governing decisions are recorded operator
words: **WV-06** (ADR-181 — two-person authorisation waived; the operator
alone authorises) and **WV-11** (ADR-189 — one operator-only purge function,
the sole SIG-STORE-011 exception). This note designs and bounds the mechanism
under them; it decides nothing they did not.

**Nothing in this file has run.** The mechanism has never executed, the new
sqitch change has never deployed to the hosted spine, and the operator-held
role has never been granted to any login. The deploy itself is a
never-pre-authorised in-ticket go (`D-P37.71-1`), and every *use* is a
separate in-ticket go naming the material.

## The operator's words (quoted, never re-decided)

- WV-06 (A-23 part 2, adopted 2026-10-01T04:28:49Z; sha256 `dbf7a851e9d5…`):

  > I waive two-person authorisation for true deletion (SIG-GOV-008): I alone
  > may authorise a deletion, publicly logged with its reason.

- WV-11 (S6R-03, adopted 2026-10-01T06:51:11Z; sha256 `04e7b77f8db7…`):

  > I approve one operator-only purge function as the sole exception to
  > SIG-STORE-011, limited to material SIG must not hold (GOV-008), leaving a
  > tombstone and a public log entry.

## Scope — what may be deleted at all

SIG-GOV-008's scope clause stands unchanged: true deletion is reserved for
**material SIG must not hold at all** — chiefly SIG-PUB-002 categorical
material (per-person data, plate data) that entered the store by defect and
was sealed by the P34.49 at-rest audit (`capture_seal`; counts only are
recorded, never the material). Those sealed rows are the first candidates
for an operator purge decision. Suppression (SIG-GOV-007 — the `sealed`
tier, flag + recorded decision) remains the primitive for **everything
else**: a privacy harm that does not meet the categorical bar is suppressed,
a disputed claim is corrected or annotated, a licence problem is withdrawn.

Two operation names keep the layers distinct (the public decision log's
classes, `sig.editorial-decision/1`):

- **deletion** — removing *material* (evidence bytes, restricted objects,
  derived artifacts) that SIG must not hold;
- **purge** — removing a *claim row* through the one DB function
  (the WV-11 exception).

## The design problem — keeping the audit record

Three earlier decisions collide here, and the design exists to reconcile
them honestly:

1. **The claim spine is append-only** (SIG-STORE-011, ADR-002): DELETE and
   most UPDATE are forbidden by the `claim_append_only_trg` trigger — the
   whole point is that the record cannot be silently rewritten.
2. **The evidence store is write-once** (ADR-023): captures live in an
   OCFL 1.1 object store whose semantics are versioned accretion; object
   lock is **governance mode, not compliance mode** (SIG-GOV-009) precisely
   so legitimate removal stays possible.
3. **P37.3's evidence-bucket retention is 365-day unlocked** (ADR-177,
   B-14 = a): a deliberate choice so takedowns and this deletion path
   remain possible — the retention policy prevents *accidental* deletion
   inside the window, it does not prevent a governed one.

The resolution is the same on every layer: **a governance-mode delete
removes the material and keeps its own audit record.** The append-only
store is what records *that* a deletion happened, *why* it was authorised,
and *what category* it was — never the deleted content. Concretely:

- **In the claim spine**, `sig_purge_claims()` is the only delete path. It
  is `SECURITY DEFINER`, executable only by the `sig_purge_operator` role
  (a NOLOGIN role created by the `operator_purge` sqitch change and granted
  to no one by any migration — the operator provisions a login member
  themselves, credential in Secret Manager only). Inside one transaction it
  writes the tombstone and audit rows **first**, disables only the *user*
  triggers on the four bundle tables (foreign-key constraint triggers stay
  armed — a missed dependent still blocks the delete), removes the rows,
  and re-arms the triggers. The landed `claim_append_only_trg` is never
  edited; it keeps raising for every other role and path.
- **In the object stores** (evidence bucket, restricted bucket, release
  artifacts), the `sig-ops deletion` verb deletes named objects — the OCFL
  object root included — because the retention is unlocked by design
  (ADR-177) and the object lock is governance-mode by design (SIG-GOV-009).
  The OCFL store's write-once semantics live at the *object-version* layer;
  a governance delete removes the object root and is recorded as an
  operator act, never an OCFL operation.
- **The audit record is triple-redundant and append-only:** the
  `purge_tombstone` (public-safe) + `purge_audit` (restricted) DB rows, the
  `sig.deletion-tombstone/1` + `sig.deletion-audit/1` registry records, and
  a `sig.editorial-decision/1` entry the operator commits to the public
  decision log (P37.7, ADR-164) with the same go.

## What the purge function may and may not remove

The claim bundle is the claim's own material — deleted with it:

- the `claim` row;
- its `claim_evidence` and `claim_qualifier` rows;
- its `claim_lineage` row.

A claim is **refused** — the function raises, naming the blocking relation —
when any *recorded decision or cross-reference* outside the purged set
points at it:

- another claim's `revises_claim` / `retraction_of` /
  `derived_from_claim_ids` (outside the set — intra-set links purge together);
- a `resolution` (`winning_claim`, `considered_claims`, `dissenting_claims`);
- a `relationship`, `entity_role`, or `organization_relation` edge;
- an `entity_identifier`, `jurisdiction`, or `person` projection;
- a `publication_disposition` or an `intake.application` correction;
- a `recovery_application` action;
- another claim's `claim_lineage.derived_from_claim_ids` ancestry.

The refusal is the design: a claim that a recorded decision depends on
cannot vanish without falsifying the decision. The honest paths are
suppression (SIG-GOV-007), or a wider authorised set the operator's go
names explicitly (a claim and its correction purge together). Foreign-key
constraints stay armed during the purge, so an unenumerated dependent
fails loudly rather than dangling.

Evidence-store capture and artifact **rows** (`evidence_capture`,
`evidence_artifact`) are deliberately *not* purged: they are the audit
surface of the evidence store — they record that a capture existed, its
digest, and its seal state. The bytes go (object leg); the fact of the
capture stays (audit). A capture row that itself carries the material is a
scope question for a new ADR — widening is a revisit trigger.

## The controls that hold when the waiver is exercised

- **Never pre-authorised.** The function is never on an OM-20 list; the
  hosted deploy of the `operator_purge` change and *every single use* are
  separate in-ticket gos naming the material (`sig.deletion-order/1` +
  a `sig.operator-authority/1` record, verified — never created — by the
  mechanism, the SIG-SEC-010 pattern).
- **Never agent-initiated.** No code path reaches the function without the
  operator role; `sig_ingest`, `sig_materialize`, the read roles, the
  deploy login — none holds EXECUTE. The DB test proves the trigger still
  raises for every other role and path.
- **Publicly logged.** Each use lands a tombstone (category + date, never
  content) and a `sig.editorial-decision/1` entry citing the go, in
  `web/src/lib/editorial-decisions.ts` — classes `deletion` / `purge`.
- **Counts only, never content.** Tombstone and audit records carry
  categories, dates, counts and ids; the deleted material's content is
  never restated in any record.
- **Revisit triggers armed** (ADR-181, ADR-189): any use; a request to
  widen scope or add a second purge path; a second maintainer; a contested
  deletion.

## What stays unchanged

- Corrections are still new claims (SIG-GOV-005); the `sys_period`-close
  path is untouched.
- SIG-STORE-012 stands: no application role gains `DELETE` — the function
  is the only path, and it is not a grant.
- `PgClaimSink`, `PgReadStore` and every connector/export path stay
  insert-only; nothing in code calls the function.
- OCFL object versioning and the 365-day retention posture are unchanged —
  the deletion lane is an operator act *outside* those semantics by
  recorded design, not a hole in them.
