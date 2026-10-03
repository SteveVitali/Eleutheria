# ADR-130 — Acquisition is a gap-driven reviewed queue: passports as data, hard rights/sensitivity gates outside the score (P32.11)

- Date: 2026-09-27
- Status: accepted (engineering; live acquisition, rights decisions and source flips stay operator-gated under `D-R10-SOURCES-1`)
- Ticket: P32.11 (Round 10 / S5, row 171; requirements SIG-ACQ-001, SIG-ACQ-002; annotates `D-R10-SOURCES-1`)
- Base: `e8f8764` (the P32.10a chain tip `devin/p32-10a-disposition-single-clock-authority`, PR #166)

## Context

§55.6 requires source discovery to be evidence-first, gap-driven and
reviewable — not a raw source or claim-volume collector. The S5 research
(`docs/build/planning/2026-09-25-six-streams/research/S5-source-strategy.md`)
delivered a 27-row candidate inventory
(`docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv`) with
per-row provenance, novelty dispositions, lineage notes, rights unknowns and
negative cases (a mirror is one lineage; a template is not an executed
contract; award eligibility is not a purchase; per-query audit workbooks are
prohibited until an explicit content-admissibility decision).

Without an executable contract, the failure modes are concrete: a mirrored or
republished document scores as independent corroboration; an existing P31
source or registered row is onboarded a second time; a high usefulness score
quietly offsets an undetermined or rejected rights lane; a municipal PDF is
treated as auto-CC0 (17 U.S.C. §105 is federal-only; Compendium §313.6(C)(2)
carves out copyrightable non-edict state/local works); and an estimate is
relabeled as a measurement.

## Decision

**Acquisition is a reviewed queue in `tasks/` (`tasks.acquisition` +
`tasks/src/tasks/data/acquisition_queue.toml`, schema `acquisition-queue/1`)
seeded verbatim from the committed research CSV — data, not code — that joins
every candidate to the live registry and the recorded P31.12/.13
dispositions, and gates every entry outside the score. The queue approves
nothing: it cannot mint a rights decision, cannot flip
`ingestion_permitted`, and performs no fetch.**

1. **Candidate passport.** Every candidate carries the named
   evidence/question/relationship gap it exists to close, authority, target
   predicates, jurisdiction and a content window (scope/time), discovery
   provenance (URLs, access date,
   verbatim review-depth, reviewed scope), the closed S5 lineage vocabulary
   (`same_bytes`, `republished_document`, `derived_summary`, `new_version`,
   `amends`, `response_to`, `independent_account`) plus an institutional
   `lineage_group`, registry links (`same_source` = the candidate *is* that
   row; `related` = dedupe-aware context), three rights lanes, a Part VIII
   preflight, a versioned dimension assessment, and cost.
2. **Lineage is provenance, not URLs.** Only `independent_account` yields
   corroboration; any other lineage class or a shared `lineage_group` makes
   two candidates one provenance (enforced in `independent_corroboration`,
   and a non-independent passport with I>0 fails validation). Normalized-URL
   collision — between candidates or with a registered `homepage_url` — is a
   literal `duplicate` and is refused, never onboarded twice. A `same_source`
   link into a P31.12/.13-owned id resolves to `p31_owned` →
   `consume_existing`; re-onboarding is refused.
3. **Rights and sensitivity are hard gates, not score terms.** Three lanes —
   `document_bytes` (incl. embedded third-party material), `fact_extraction`,
   `derived_publication` — are assessed *separately*. A `decided` lane must
   cite a recorded reviewer disposition (`decision_ref`/role/date/basis); the
   queue itself cannot mint one. Undetermined or rejected lanes, an
   unscreened/prohibited/rejected Part VIII preflight, and observed
   municipal/state publication (the non-edict question, never auto-CC0) are
   `Gate`s AND-ed after scoring — usefulness cannot open them.
4. **Score is a versioned ordinal utility, not a probability.** `acq-score/1`
   computes `3G + 3R + 2I + 2U + T + J − 2E − 2A − 2S` over nine 0–3
   dimensions; `score` returns the per-dimension contribution table,
   `diff_assessments` explains any change between two versioned input sets,
   and unknown dimensions stay unknown — the candidate reports unscored with
   named unknowns rather than a fabricated number. The `acq-seed/1`
   assessment is an engineering estimate derived from the CSV's declared
   fields, labelled `measured=false`, intended to be superseded by reviewer
   assessments under a new version — never edited in place (§20).
5. **Cost honesty and uncertainty.** `CostRecord.measured_minutes` stays
   `None` until an approved run reports real minutes (and then requires a
   measured basis); the estimate is the CSV effort band. `uncertainty` is
   generated from the recorded review depth — search excerpts are leads,
   index metadata draws no content-level claim. Review packets carry the
   whole passport plus the precise missing questions an operator must
   answer, and state plainly that they authorize nothing.
6. **CLI is read-only.** `sig-tasks acquisition queue|explain|packet|check`
   emits the ranked queue (markdown/JSON), per-candidate score explanations
   and versioned-input diffs, review packets, and a CI-checkable
   completeness invariant. It writes reports only; it never mutates the
   registry, the queue data, or any source row.

## Consequences

- The queue is inspectable data: every candidate is one reviewable TOML row,
  seeded from the 27-row research inventory (5 P0 + 7 P1 + 15 P2/P3) — 23
  `net_new` review targets plus the four `same_source` improvements resolved
  onto existing rows (`sourcewell`, `ccops_berkeley`, `ccops_boston`,
  `faa_drone_waivers`); nothing is emitted as new onboarding against a
  registered or P31-owned row.
- SRC-027 (the San Diego ALPR network-audit workbooks) is carried in the
  queue with `prohibited_until_review` — visible, scored (−8), questioned —
  and cannot be acquired until the explicit content-admissibility and rights
  decisions exist.
- `D-R10-SOURCES-1` stays OPEN: this ticket lands the queue precondition;
  exact-target source/evidence-use review and bounded pilot acquisition
  remain with P32.18–P32.21 and the operator.
- A rights lane becomes `decided` only by a recorded reviewer disposition
  artifact — the future P32.18–P32.21 reviews will supply `decision_ref`s;
  no code path fabricates one.

## Alternatives considered

- **Score-with-offsets (rights as a negative weight).** Rejected: an
  undetermined or prohibited state is not a low-scoring state — usefulness
  must never compensate for a rights or sensitivity barrier (SIG-ACQ-002).
- **Registry-row seeding (add `sources.toml` rows now).** Rejected: registry
  rows imply a dispatch identity; the research inventory is a lead list, not
  an ingestion-permission list, and every new row would still sit at
  `ingestion_permitted=false` with nothing to review. The queue is the
  review surface; rows arrive only through the recorded HG-03 decision.
- **Duplicates by registry id only.** Rejected: mirrors collide by URL and
  institutional provenance, not by shared ids — the join checks normalized
  URLs (candidate↔candidate and candidate↔registered homepage) plus
  `lineage_group`.
- **Hidden unknowns (default zero).** Rejected: a missing dimension reports
  `unscored` with named unknowns; a silently-defaulted zero would
  misrepresent the review's coverage.

## Revisit trigger

Revisit when (a) the first reviewer assessment supersedes `acq-seed/1` and a
calibration disagreement emerges that the ordinal model cannot express; (b)
P32.18–P32.21 pilot acquisition produces measured costs that show the effort
bands are systematically wrong; (c) a candidate needs a lineage class outside
the closed S5 vocabulary; or (d) the operator approves a bounded pilot that
requires a live acquisition stage — at which point `live_verification=true`
re-dispatch turns the review outputs into acquisition runs under the existing
loader gate.
