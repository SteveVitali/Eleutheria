# ADR-061: Capstone gap closure — the derivative export gate, jurisdiction-conditional web render, and ER over PostgreSQL

- **Status:** Accepted
- **Date:** 2026-09-09
- **Phase:** P19.5
- **Requirement ids:** SIG-LIC-004, SIG-LIC-010, SIG-INGEST-048b, SIG-PUB-017, SIG-IDENT-020, SIG-IDENT-021, SIG-IDENT-025, SIG-IDENT-026, SIG-ENG-030, SIG-ENG-031

## Context

P19.5 closes the small/medium CODE gaps the whole-spec capstone analysis
(`CAPSTONE_GAP_ANALYSIS.md` §(i)) routed to closure, plus the ER-over-PostgreSQL work P19.4 deferred
to here under its size guard (ADR-059 §6, `LD-F04`). Three of those closures make design choices worth
recording; the documentation gaps (ADR-060, the ADR-044 amendment, the §53 sections) are recorded in
their own places.

## Decision

1. **The `derivative_permitted` export gate lives in `policy.licensing`, fail-closed, with a
   non-raising partition companion (LD-F08 / SIG-INGEST-048b, SIG-LIC-004/010).** `assert_export_permitted`
   gains a third fail-closed condition after UNDETERMINED and non-redistributable: a source with
   `derivative_permitted=false` (e.g. the AGPL-3.0 `sm_alpr` / `deflock_app_repo` — redistributable but
   not derivable) is refused, because an export bundle is a derived/aggregated work. The machine-stable
   reason string is `derivative_permitted=false`. A companion `partition_exportable(records)` returns
   `(exportable, refused-with-reasons)` so a mixed export set drops the non-derivative source rather
   than aborting. Both honour Part VIII §0.7 — the change can **only reduce** what leaves the system;
   a derivative-permitted, redistributable source is unaffected (back-compat).

2. **Jurisdiction-conditional web render is a build-time decision, mirrored in TypeScript (LD-V12 /
   SIG-PUB-017).** The shell is static-first (SIG-UI-036) and calls no live API at build, so
   `web/src/lib/publication.ts` is a faithful mirror of `policy.jurisdiction.adapter_publication_permitted`
   / `policy.publication.publication_permitted`: a public-employee name is publishable only if BOTH the
   subject's and the record-origin's jurisdictions permit it, unknown → conservative no-publish.
   `dossier.applyPublicationPolicy` runs in the dossier page's build-time data path and **withholds**
   (clears + marks, never adds) a name that FR-GDPR / BE-GDPR forbid; the FR/BE dossiers render in their
   BCP-47 language with localised section titles. The US OKC dossier publishes the equivalent name
   unchanged. The zero-JS budget (script size 0) and WCAG 2.2 AA are preserved — the gate is baked into
   the HTML, not a client script.

3. **ER over PostgreSQL reuses the P19.4/ADR-059 names unchanged (LD-F04).** `sig-resolution match
   --dsn … --jurisdiction <id>` reads organisation candidates from the PG spine, scores them with the
   existing `ProbabilisticMatcher` (tier-4/5 PROPOSED only, never an auto-write, SIG-IDENT-020), and
   enqueues them as `review_item` rows. A new additive sqitch change `review_queue` adds `review_item`
   (idempotent proposals) and an **append-only** `review_decision` table; `PgReviewQueue`
   (`resolution/src/resolution/review_pg.py`) is a JSONL-compatible backend selected by `--dsn`, and
   `sig-resolution review decide --dsn` appends **exactly one** `review_decision` row per call —
   deciding the same item again appends a new row (a decision *history*), never an UPDATE/DELETE, with
   `decided_at` set by the database (SIG-IDENT-026, P1–P3). The JSONL/in-memory `ReviewQueue` remains
   the default for every existing test. This flips the composed-stack `LD-F04` xfail (S4) to a real pass.

## Consequences

- The export gate now withholds `sm_alpr`/`deflock_app_repo` from any export set; the composed
  `tests/e2e` drops to one remaining xfail (`LD-V08` → P21.4). New tests:
  `tests/resolution/test_pg_backend.py`, `tests/inference/test_cli.py`,
  `web/tests/e2e/jurisdiction.spec.ts` (+ `.nojs`), and the added export-gate/publication cases.
- The compute-on-read seam (ADR-059) is unchanged; persisting ER results / annotations remains P21.2.

## Alternatives considered

- **Enforce `derivative_permitted` only via a separate partition function, not the gate itself.**
  Rejected: the gate is the single fail-closed choke point; a source that forbids derivatives must not
  slip through a caller that forgets to partition. The partition helper is the additive convenience,
  the gate is the guarantee.
- **Re-run the Python publication policy at web build via a codegen/JSON step.** Rejected for now: a
  small, tested TypeScript mirror keeps the web build hermetic and zero-dependency; the mirror is
  pinned to the same jurisdiction table semantics and unit-tested against the FR/BE/US cases. (If the
  jurisdiction table grows, generating the TS table from the Python data is the documented next step.)
- **A fresh naming for the ER-over-PG CLI / tables.** Rejected: ADR-059 fixed `review_decision`,
  `--dsn`, and `sig-resolution match/review`; P19.5 reuses them unchanged.

## Revisit trigger

Revisit if: an export legitimately needs a derivative-forbidden source under a narrowly-scoped grant
(then the grant, not the gate, records the exception); the jurisdiction publication table must diverge
between Python and TypeScript (generate the TS table from the Python data); or P21.2 materialises ER
results and the `review_item`/`review_decision` compute-on-read/enqueue seam is replaced by persisted
annotations.
