# ADR-142 — The release candidate under deferred evaluation: one pinned identity, the changed-input stop, and unpublished-by-construction staging (P32.23a)

- Date: 2026-10-19
- Status: accepted (engineering; `live_verification=false` — fixture/test-PG only; the production candidate is the operator-gated live pass under `D-R10-LIVE-1`, still OPEN)
- Ticket: P32.23a (Round 10 / S1, row 188; requirement SIG-TRUST-010; annotates `D-R10-HUMAN-1`, `D-R6.1-EVAL`, `D-R10-LIVE-1`, `D-R10-PUBLISH-1`; opens `D-P32.23a-1`)
- Base: `devin/p32-22-bounded-recovery` tip (PR chain of P32.22 / ADR-141)

## Context

P32.22 froze `sig.repaired-snapshot/1` — a `frozen_unpublished`,
`provisional_preview`, explicitly `not_a_release_candidate` frame for
HUMAN-H4. P32.23a owns the next stage: **one release candidate** built from that
frozen input.

On 2026-10-19 the operator deferred the whole S3 human-evaluation spine
(HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) wholesale — *"let's defer all the
human review steps and proceed"* — so **there is no final evaluation
decision** for this candidate to consume. SIG-TRUST-010 (§55.8) phrases its
contract as *"after the final evaluation decision … regenerate all affected
artifacts into one new release candidate … every artifact must pin the same
evaluation result, ruleset and snapshot; pre-evaluation previews cannot
satisfy release acceptance; any changed evaluation-relevant inputs require an
explicit reassessment decision."*

The design therefore had to answer five questions:

1. **What does "the evaluation result" mean when the decision is deferred?**
   Deferred is the contract's inconclusive case: the candidate must pin an
   honest evaluation state — `deferred`, provisional basis — not a fabricated
   decision, and its disclosures must be the safe provisional/review-only kind,
   never reuse a previously optimistic resolved count.
2. **How does "every artifact pins the same identity" become checkable?** The
   export BuildSpec, the release descriptor, the analytics payloads, the
   ingest_run row, the disclosure, the rollback packet and the roll-up
   manifest must all agree — not by convention but by one shared identity
   object.
3. **What stops stale eligibility riding forward?** A changed input affecting
   the sample population or semantics must *stop* the build for reassessment —
   §55.8's explicit requirement — not just log a warning.
4. **How does "unpublished" become a property, not a promise?** The publication
   pointer is a mutable `latest.json`; the candidate must stage the immutable
   namespace while proving the pointer never moved — and make activation
   structurally absent from its flow.
5. **Where does the production half live?** The fixture build is engineering
   evidence; the hosted candidate still needs the hosted repaired spine —
   `D-R10-LIVE-1` stays OPEN and needs a pinned, machine-checkable return-pass.

## Decision

### `sig.candidate-identity/1` — one identity, deterministic

`ops.release_candidate.candidate_identity` emits a versioned identity object
pinning: `ruleset_version = provisional-ruleset/1` (the provisional basis is
the identity itself, not a footnote — the camera-site auto-write tiers and the
historical 0.98 point-gate remain PROVISIONAL-active under `D-R6.1-EVAL`, so
the ruleset *is* named provisional), the frozen `sig.repaired-snapshot/1`
digest + population digest, `code_commit`, and the evaluation block:
`status=deferred`, `decision=null`, `decision_ref=null`, `basis=
provisional-policy`, `policy_id=eval-confidence/1`, `mode=shadow`,
`applied=[]`, the verbatim 2026-10-19 deferral note, and the full
`EVAL_DISCLOSURE` string. The identity carries `published=false`,
`provisional=true`, `review_only=true`, and its own
`identity_digest` (canonical-JSON sha256) — deterministic in its inputs, so
every artifact that cites it can be checked to agree.

`assert_shadow_evaluator` re-reads the live `eval-confidence/1` posture
through the same `build_provisional_vs_shadow` P32.22 emits: if the installed
policy ever reports `mode != shadow` or a non-empty `applied`, the candidate
build **refuses** (`activated_policy`) — a candidate cannot cite a shadow
identity against an activated gate, and P32.10's confidence policy is never
activated here.

### The changed-input stop — `verify_population_frame`

Before any materializer runs, the frame's recorded `claim_ids` are reloaded
through the shared `db.evidence_audit.load_audit_input`: a missing claim, a
population-digest drift (`sha256` over the sorted id list, recomputed exactly
as the audit computes it), or an eligibility-set drift (the shared
`publication-eligibility/1` selector over the same ids) raises
`CandidateError("changed_input")` with the full check detail. The build stops
— old eligibility is never carried forward over a changed sample population.
A real post-freeze withhold disposition changes eligibility → the build
refuses (proven by `test_candidate_refuses_when_a_real_disposition_changes_eligibility`).

### `sig.candidate-materialization/1` — ordered, `+0` on rerun, history appended

The six shared materializers run in the recorded dependency order
(`resolution → camera-sites → edges → contradictions → coverage →
accountability` — the same `REMATERIALIZE_ORDER` P32.22 pins), then a second
pass must insert `+0`; any error or non-zero rerun refuses the build
(`materialization_failed` / `materialization_not_idempotent`). The execution
mints its own `ingest_run` (`connector_name=sig.release-candidate`,
`ruleset_version=provisional-ruleset/1`, `input_digests` =
identity/snapshot/plan digests) and appends `ingest_run_completion`
(`ok` on clean +0, `failed` otherwise — recorded *before* the refusal is
raised, so even a bad run leaves honest history). The P32.22 apply receipts
and this run's rows coexist append-only — nothing rewrites history.

### One build surface, unpublished by construction

The candidate composes the *existing* release machinery rather than forking
it: `run_spine_export` (one `REPEATABLE READ READ ONLY` snapshot) under
`ruleset_version=provisional-ruleset/1` with the deferral-carrying note →
`exports.release.build_release` (the real `r/<publication_id>` namespace,
descriptor, integrity manifest, catalog entry) → `validate_release`.
`activate()` and `rollback()` are never called; `latest.json` is read before
and after staging and a drift raises `pointer_mutation`. The committed
fixture shows `pointer_unchanged: true` with no pointer existing — a registry
with a prior `latest.json` is covered by the byte-identical test.

### `sig.candidate-disclosure/1` — the safe inconclusive disclosures

The final unpublished disclosure records: the change facts (4 applied /
0 skipped / 0 failed, +0 rerun — from the recorded apply report, not
recomputed), the suppression facts (3 dispositions + the export's refused-slice
totals, loudly, from `exclusions.json`), and the verbatim
`EVAL_DISCLOSURE`. `resolved_sites_figure` parses **only** this build's
`web/coverage.json`; a metric framed as a population total is refused
(`optimistic_count`) — the deferred evaluation can never inherit a previously
optimistic resolved count (`prior_preview_counts_reused: false`).

### `sig.candidate-rollback/1` + `candidate-return-pass/1`

The rollback packet is `prepared_not_needed`: it records the candidate's
publication id + manifest/descriptor/disclosure digests, the pointer content
before and after (byte-identical), and the pointer-reversal plan (the mutable
`latest.json` flips back — or is removed when no prior pointer existed — while
the immutable `r/<pub>` namespace is retained as history; preconditions name
P32.25 activation + the HG-11/GATE-G3 chain). The return-pass packet is
`prepared_not_executed`: the production commands (hosted bounded apply +
freeze under `D-R10-LIVE-1`, then `sig-ops release-candidate` over the hosted
snapshot), the verification checklist, and the explicit reservations.

`sig-ops release-candidate` is an additive verb; committed artifacts under
`docs/build/reports/p32.23a-release-candidate/`.

## Consequences

- The candidate exists as a **staged, validated, unpublished** namespace
  (`p-17b713…` on the fixture): P32.24 validates `CANDIDATE_MANIFEST.json`,
  GATE-G3/HG-11 decides, P32.25 publishes — none of which this build ran.
- Every artifact that names the candidate names the same `identity_digest`;
  a drift anywhere is a test failure, not a reviewer hope.
- A changed sample population or eligibility semantics is a **build-stop**
  (`changed_input`), not a warning — the reassessment requirement is
  structural.
- The provisional basis is legible inside the release bytes themselves
  (`provisional-ruleset/1` in the descriptor/manifest/analytics + the deferral
  note in `exclusions.json`), and the packet docs carry the full
  `EVAL_DISCLOSURE` — the candidate cannot be mistaken for a decided one.
- `D-R10-LIVE-1` keeps the production half honestly open: the return-pass
  packet is machine-checkable, not a claim.

## Alternatives considered

- **Reuse the preview snapshot as the candidate**: rejected — P32.22's frame is
  explicitly `not_a_release_candidate` by design (ADR-141); a distinct
  identity/namespace is the whole point of this stage.
- **A new lightweight "candidate builder" instead of `build_release`**:
  rejected — a second release path would duplicate the namespace/integrity
  contract and drift from it; composing the real builder and *stopping before
  `activate()`* keeps one rule.
- **Log-only changed-input detection**: rejected — §55.8 requires the changed
  input to *stop* the build for reassessment; a warning would silently carry
  old eligibility, the exact failure the clause names.
- **Defer the rollback packet to P32.25**: rejected — the ticket requires the
  rollback packet *in* the candidate; `prepared_not_needed` records the plan
  without mutating anything.
- **Name the ruleset after the frozen snapshot or a version number**: rejected —
  the honest version of these rules *is* "provisional"; a numeric version would
  launder the provisional basis into a finished-looking identity.

## Revisit trigger

- The operator resumes the S3 human-evaluation spine (HUMAN-H4 → P32.22a →
  HUMAN-H5 → P32.23): a measured decision lands, `eval-confidence/1` can
  activate under its recorded authority, and `evaluation.status=deferred` +
  `provisional-ruleset/1` must be replaced by the decision's own identity —
  this ADR's identity shape is the provisional branch.
- P32.24/GATE-G3 reject an element of the disclosure or rollback packet shape —
  the schema is versioned (`/1`) so a `/2` extension is additive.
- The live return pass surfaces a frame-check or materialization failure class
  the fixture cannot express (e.g. a hosted-only eligibility edge, a
  `sig_materialize` grant gap on the Cloud SQL role lattice).
