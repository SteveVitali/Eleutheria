# ADR-125 — The offline legacy-evidence audit and bounded recovery-plan contract (P32.6)

- Date: 2026-10-13
- Status: accepted (engineering; offline-only — no live fetch, publication or gate action)
- Ticket: P32.6 (Round 10 / S1, row 166; requirement SIG-TRUST-007; annotates `D-R10-LIVE-1`)
- Base: `a705a58` (the P32.5 implementation tip `devin/p32-5-publication-dispositions-and-filtering`, PR #160)

## Context

SIG-TRUST-007 (§55) requires a historical provenance and semantic audit over the pre-roll
evidence population: captures taken before the **2026-09-25 gcsfuse persistent-storage roll**
(ADR-111) lived on ephemeral container disks and could be lost. The audit must report a
reproducible sampling frame and denominators for exact replayability, locatability, unsupported
role mappings, count comparability and publication eligibility — and recovery requires preserved
bytes plus provable lineage. Three conflation risks were visible in the baseline:

1. **Availability vs lineage vs semantics are different axes.** A claim can have verified bytes
   but no typed locator (`document_locatable`), a typed locator but digest-mismatched bytes
   (`unrecoverable` + finding), or real bytes under a predicate that never maps to an
   operational role (`unsupported_role_mapping`). Collapsing them into one score would hide the
   failure modes the audit exists to expose.
2. **A new fetch is never the old capture.** Broad re-scrape could manufacture identical-looking
   bytes that do not share the recorded `content_digest`, retrieval time or OCFL version — and
   silently adopting them would be an unexplained overwrite of history.
3. **Legacy synthetic bindings must stay.** P32.2's `legacy_synthetic` binding marks an
   assertion without a captured artefact; removing or silently "upgrading" it would erase the
   record that the evidence was never captured.

The planning contract demands: a reproducible stratified frame (source family × pre/post-roll
epoch × predicate role × licence compartment), denominators that reconcile to the selected
population, no exact-replayability derived solely from `source_id`, zero writes for ambiguous
lineage, preserved unrecoverable states, restart-safe plans, estimates citing real resource
ceilings, and the three semantic-support forms reported separately with unresolved claims held
in the denominator.

## Decision

**`evidence-audit/1` + `recovery-plan/1` — a read-only audit that keeps three axes independent,
and a dry-run-only planner whose resume marker is the action digest.**

### `evidence-audit/1` (read-only by construction)

- **Loader** (`db.evidence_audit`, `evidence-audit-rows/1`): one chunked SELECT over
  claim → claim_evidence → evidence_capture → evidence_artifact → ingest_run, plus
  `ingest_run_capture` marks by digest, the `spine_watermark` snapshot and claim eligibility via
  the shared `db.dispositions.claim_eligible_sql` fragment (the P32.5 selector — reused, never a
  second definition). The DB path runs under `default_transaction_read_only=on` so a code bug
  cannot write. Plain dict rows out — the same loader shape the committed `fixture_spine.json`
  carries, so fixture and live populations travel one contract.
- **Frame**: every sampled unit's stratum is `(source_family, capture_epoch, predicate_role,
  compartment)`. `capture_epoch` derives from `retrieved_at` vs the recorded roll boundary —
  never inferred from source identity. Deterministic sampling: `sha256(seed|claim_id)` order,
  per-stratum proportional draw, recorded seed + population digest + watermark. Census buckets
  along all four axes must sum back to the claim count (`reconciles`), else the report fails.
- **Five grades, plus findings**: `exact_replayable` (verified bytes at the pinned OCFL version,
  typed locator, recorded extractor identity, mechanical replay of the located bytes succeeds),
  `document_locatable`, `source_attributed_only`, `unrecoverable`, `restricted_not_public`.
  Digest mismatch, missing object, unsupported role mapping, ambiguous lineage and
  dangling-capture linkage are **findings** — audit results, never silent states.
- **Byte verification is real**: the probe resolves the *pinned* `ocfl_version` (never head when
  a pinned version is recorded) and recomputes the connectors' own multihash over the bytes.
  Restricted reads that cannot be verified stay `UNVERIFIED` — never downgraded to `missing`.
- **Semantic trio, held honestly**: support over ALL sampled eligible claims (unresolved counts
  as not established), conditional adjudicated fidelity over adjudicated units only, and
  adjudication yield — three separate numbers. Evidence-unavailable units stay in the fidelity
  denominator via `unresolved_evidence_unavailable`, so missing evidence can never inflate
  fidelity by disappearing. Unsupported predicate→role mappings never establish support.

### `recovery-plan/1` (dry-run by construction)

- Every action proposal maps to an **insert-only** surface: `claim` (repair row), `claim_evidence`
  (bind-verified), `publication_disposition` (withhold), or the disclosure channel. There is no
  write path in the tool — "apply" is a separate future stage owned by P32.22.
- **Zero-write rules**: ambiguous lineage, unrecoverable, restricted, and digest-mismatched units
  receive *no* mutation proposal — only recorded status. A matched claim/capture pair whose
  recorded binding is synthetic-only can be proposed a `bind` to the *verified original* capture
  (same digest — never new bytes).
- **Bounded, resumable**: batches cap assertions and distinct bytes; each action carries a
  deterministic digest; feeding prior digests back (`--applied`) yields `already_applied` and a
  `+0` re-plan — restart can never duplicate a disposition.
- **Estimates cite real ceilings**: row/disk/time growth per batch references the measured
  ingestion/replay rates and storage ceilings from ADR-107/111/114 and the S1 recovery bounds,
  not invented throughput.
- **Live return-pass packet**: a prepared-but-unexecuted JSON contract pinning the audit input
  digest, code commit, policy version, runtime sqitch state, mounted OCFL root, exact commands,
  ceilings and checklist — explicitly stating the no-refetch rule and that production mutation
  is reserved for P32.22.

## Alternatives considered

- **Broad re-scrape to "recover" missing bytes** — rejected: the old capture's retrieval time,
  digest and version cannot be recreated; new bytes are new evidence with new lineage, and
  pretending otherwise is exactly the unexplained overwrite §3.1 forbids.
- **A single "evidence health" score** — rejected: it would let one axis (verified bytes) mask
  another (unsupported role or missing locator), defeating the audit's diagnostic purpose.
- **Immediate mutation mode with a `--live` flag** — rejected: live mutation belongs to the
  separately-scoped P32.22 stage under `D-R10-LIVE-1`; shipping a dormant write path invites
  unreviewed execution.
- **Dropping unresolved units from fidelity** — rejected: that is precisely how missing evidence
  inflates reported quality.

## Consequences

- The audit is deterministic: same input + seed ⇒ byte-identical `audit_report.json` (verified
  by regeneration of the committed fixture packet).
- Exact-replayability claims are cheap to defend — every `exact_replayable` unit names the OCFL
  object, pinned version, verified digest and the replay that succeeded.
- The unrecoverable population is now *named and counted* rather than silently absent, which is
  the honest input the P32.22 live stage and the final-candidate evaluation need.
- Cost: one OCFL read per sampled capture (byte-budgeted, recorded `bytes_read`), one chunked
  SELECT per claim batch — both bounded and recorded in the report.

## Revisit trigger

- If the live pass (P32.22, `D-R10-LIVE-1`) finds the grade taxonomy insufficient for a real
  population — e.g. a partial-WACZ state or a mark-present/row-absent divergence the fixture
  never covered — extend the grade/findings vocabulary under `evidence-audit/2`, never by
  redefining the landed grades.
- If repairs need claim-level conflict resolution between two *verified* captures (not covered:
  ambiguous lineage is zero-write today), that adjudication semantics change is a new ADR.
- If a future stage wants the planner to *apply* dispositions, the apply path is a new contract
  with its own authority/audit surface — this ADR deliberately ships no mutation.
- If `recovery-plan` batch bounds prove too tight/loose against measured live timings, adjust
  the constants and record the new measured ceiling — the cite-actual-ceilings rule stands.
