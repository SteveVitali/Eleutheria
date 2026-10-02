# ADR-128 — The preregistered, dependency-disjoint, blinded human-evaluation campaign surface (P32.9)

- Date: 2026-10-16
- Status: accepted (engineering; campaign tooling only — `D-R10-HUMAN-1` stays open; zero human participation is claimed or required)
- Ticket: P32.9 (Round 10 / S3, row 169; requirements SIG-EVAL-001, SIG-EVAL-002; annotates `D-R10-HUMAN-1`, `D-P30.2b-1`, `D-R6.1-EVAL`)
- Base: the P32.8 closeout tip (`devin/p32-8-memory-concurrency-and-recovery`, PR #163)

## Context

SIG-EVAL-001 requires resolution evaluation to run over a **preregistered
campaign**: frozen source snapshot, explicit target population, sampling
frame, inclusion probabilities, strata, dependency-grouped disjoint
train/development/sealed-final partitions, seed and ruleset identity — with
tuning on the test set prohibited. SIG-EVAL-002 requires **independent human
labels** recorded append-only under pseudonymous reviewer identity, blinded
to model predictions and to each other's first-pass labels, with a
two-independent-labels + adjudication path that preserves disagreements and
abstentions — and an explicit wall between reference labels and operational
`review_decision` accept/reject.

The P31.10/P31.11 machinery is *operational review*: `review_item` proposals
and `accept`/`reject` decisions feeding clustering. The S3 research
(`docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md`)
enumerates why that surface cannot answer "same defined object": score/tier
columns leak the answer under assessment, `unsure` is deliberately not
persisted, and pair-level splitting leaks entity/component/lineage across
train and test.

This ticket's scope is **preparation**: protocol, schema, packet tooling and
reviewer/operator documentation. It must not recruit reviewers, mint labels,
or let an agent impersonate human adjudication, and it must not silently
certify or replace P31's `PROVISIONAL` posture.

## Decision

**One additive `human_eval_*` surface, three evaluation roles, true
first-pass blinding, and append-only everything — with the operational
channel untouched.**

### Preregistration and disjoint sampling (`resolution/human_eval.py`)

- `preregister_campaign` validates + digests the immutable design record:
  purpose, `protocol_digest`, `frame_snapshot`, `ruleset_digest`, `seed`,
  target population, `group_spec`, `sample_spec`, `rubric_version`. A changed
  rubric/ruleset/frame is a **new** campaign — the design object has no
  mutable fields.
- **Dependency groups, not pairs, are the split unit.** Pairs are grouped by
  shared subject entities, shared candidate components and duplicated
  upstream-record lineage (republisher families), then strata are homogenized
  per group so one group lands whole in one partition — no
  entity/component/lineage can cross train↔sealed_final.
- `draw_eval_sample` assigns partitions per stratum by seeded SHA-256 order
  with per-stratum fraction targets, draws the seeded sample, and records an
  explicit **inclusion probability + weight + denominators on every row**
  (estimand, stratum id, stratum size, group count, selection count). The
  manifest digest covers every sampled id, probability, stratum, population
  size, dependency group, packet reference and partition; `verify_manifest`
  recomputes it over live rows — tampering is detected, never tolerated.
- Sample ids are opaque `hev-<digest>` handles that encode neither partition
  nor tier.

### Blinded packets

- `build_blinded_packet` emits only the evidence a reviewer needs: raw +
  normalized observation fields, authorized source name and upstream id,
  capture dates with uncertainty, excerpt/locator, lineage facts, neutral
  geometry — with deterministic left/right randomization and item order.
  `assert_blinded` hard-fails on any of: matcher tier, score, predicted
  disposition, cluster membership, model/agent labels or rationale, other
  reviewers' labels, queue confidence text, generated merge conclusions.
- Every packet row carries `packet_digest`; labels pin the digest they were
  issued against. A packet revision is a new row and a new digest — never a
  quiet edit of the sealed set.

### The database surface (`db/sqitch.plan` `human_eval_campaign`)

- Tables: `human_eval_campaign`, `human_eval_manifest`,
  `human_eval_sample`, `human_eval_packet`, `human_eval_assignment`,
  `human_eval_attestation`, `human_eval_label`, `human_eval_adjudication`,
  `human_eval_release` — all append-only (immutability triggers, no
  UPDATE/DELETE grants; supersession is a new row).
- `human_eval_label` constrains `label ∈
  same | different | insufficient_evidence`, pins `rubric_version`,
  `packet_digest`, `attestation_id` (a label **cannot** exist without the
  reviewer's human-attestation row), and `label_digest` chaining a
  campaign **watermark** (`sig-resolution eval watermark`).
- Roles: `sig_eval_admin` (prepare/read-released), `sig_eval_reviewer`
  (own assignments/packets/labels via RLS on `sig.eval_reviewer`),
  `sig_eval_custodian` (read-all + adjudication + release, **no** label
  grant — a custodian cannot mint a label and the DB proves it).
- `sig_materialize`, `sig_read_*`, `sig_export`, `sig_ingest` receive **no**
  grant on any `human_eval_*` object. Released views exist per scope and
  stay **empty** until `human_eval_release` records the custodian decision —
  `sealed_final` labels are unreachable from clustering/model-development
  views before authorized unsealing, by construction.
- `consensus()`: two equal `same`/`different` judgments yield the reference
  label; **any** disagreement or `insufficient_evidence` routes to
  adjudication, whose outcomes (`same`/`different`/`insufficient_evidence`/
  `unresolved`) are recorded separately and preserve both first-pass votes.

### The CLI and the marker

`sig-resolution eval {frame,prepare,packets,assign,status,export,attest,
import-labels,adjudicate,unseal,verify,watermark}` — each subcommand `SET
ROLE`s to the appropriate evaluation role, writes append-only rows, and
never authors a label (labels arrive only via `import-labels` under
`sig_eval_reviewer` + `sig.eval_reviewer`).

`docs/evaluation/` ships the reviewer rubric (`eval-rubric/1`), the
training/pilot packet, pseudonymous reviewer provisioning, the measured-time
worksheet, and the human-campaign marker packet whose current state is
`tooling_ready` — honest preparation, zero claimed participation.

## Consequences

- Zero human labels leaves a campaign `prepared`/`awaiting_humans` — never
  certified. `consensus([])` is `awaiting_labels`, and `insufficient_evidence`
  can never auto-accept a pair.
- P31 operational review is untouched: `review_decision` keeps its
  accept/reject constraint; nothing in `human_eval_*` writes to clustering
  inputs.
- `D-R10-HUMAN-1` stays open (real human labels are HUMAN-H4 → P32.22a →
  HUMAN-H5 → P32.23); `D-P30.2b-1` and `D-R6.1-EVAL` are annotated — tooling
  is ready, closure still requires real human decisions.
- The migration is reversible: `sqitch revert` drops only the eval surface
  and keeps all prior history (proved by the revert drill test over a seeded
  spine).

## Alternatives considered

- **Extend `review_decision` with a third vocabulary.** Rejected: the S3
  research names the leak paths — operational rows carry score/tier and feed
  clustering; a shared table cannot be blinded without breaking both
  consumers. A separate channel with separate roles is the only design that
  keeps operational triage and reference evaluation honest simultaneously.
- **Pair-level splits like the provisional evaluator.** Rejected: pair-level
  random splitting shares entities/components/lineage across train and test;
  dependency-group splitting is the requirement (EVAL-A4/SIG-EVAL-001).
- **`NULL`/`unsure` non-persistence like P31.** Rejected: abstentions must
  stay in denominators (EVAL-A5); `insufficient_evidence` is a first-class
  persisted label.

## Revisit trigger

Revisit when: `D-R10-HUMAN-1` advances (real human reviewers provisioned —
verify provisioning docs + attestation flow against real accounts); the
rubric changes (new `eval-rubric/N` ⇒ new `protocol_digest` ⇒ new campaign);
a label is corrected after unseal (the old evaluation result is invalidated
and a new decision is required); or a new estimand needs whole-source-family
holdout beyond the current entity/component/lineage grouping (extend
`group_spec` in a new ADR).
