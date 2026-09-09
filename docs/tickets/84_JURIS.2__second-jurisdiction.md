<!--
  Lane C (new code) contract — productionize Round 4. Filled by decompose-spec mode=extend over
  ~/MetaHarness/sig-golive-spec.md (2026-09-09). CITES the spec's §§ and GL-* ids.
-->
# JURIS.2 — Second jurisdiction (GL-JURIS-01)

- **Sequence:** 84 of 87 · **Phase:** 22+ (productionize) · **Kind:** ticket
- **Tag:** golive-round4
- **base_branch:** current checkout
- **Depends on:** META.1 (row 83) — the previous Round-4 step; a live OKC (the federation baseline)
- **Run:** `implement-spec spec=docs/tickets/84_JURIS.2__second-jurisdiction.md live_verification=true`
- **Gate status:** HG-03/HG-04 per new source (rights review + outreach for the second jurisdiction's sources) — orchestrate-build pauses; skip runs over fixtures + packets
- **Live stage:** operator-gated: real fetch of the second jurisdiction's green sources

> **Candidate selection is deferred to the operator at JURIS.2 time** (spec Appendix B item 6,
> non-blocking). The ticket ships the templating + adapter exercise regardless of which
> jurisdiction is chosen.

## Goal
Prove the federation design generalizes: pick the next jurisdiction, rights-review its sources
(new packets, HG-03/04 per source), and run its `run_<juris>.sh` (templated from `run_okc.sh`)
end-to-end through the jurisdiction-adapter framework (P18.1) — surfacing any OKC-specific
assumptions.

## Load (read these — do not re-read others)
- `~/MetaHarness/sig-golive-spec.md` Part II § JURIS.2 (GL-JURIS-01); Part I §3 (D7).
- `docs/tickets/P18.1__international-framework.md` (jurisdiction-adapter framework);
  `docs/tickets/P21.4__first-jurisdiction-ingest-and-publish.md` (`run_okc.sh` template);
  `docs/2_canonical_design_spec.md` Part on federation / jurisdiction adapters.

## In scope — deliverables
1. Pick the next jurisdiction; author its rights packets + review (HG-03/04 per source) (GL-JURIS-01).
2. `run_<juris>.sh` templated from `run_okc.sh` (GL-JURIS-01).
3. End-to-end ingest → resolve → publish through the jurisdiction-adapter framework (P18.1), with
   the jurisdiction's own acceptance queries (GL-JURIS-01).

## Out of scope
- A third jurisdiction (JURIS.3+, a later round). The CCOPS connector — CCOPS.1 (row 85).
- Re-writing the adapter framework — reuse P18.1; record any needed hack as backlog.

## Acceptance criteria
- [ ] the second jurisdiction ingests → resolves → publishes with its own acceptance queries green *(deterministic; live-gated — DEFERRALS row if HG-03/04 skipped)*
- [ ] the adapter framework needed no per-jurisdiction hack (or the hacks are recorded as backlog) *(agentic)*
- [ ] Part VIII honored on the new jurisdiction's data *(deterministic)*
- [ ] verification green; every new behaviour has a test that fails if it is removed; requirement ids stamped in the PR; anything not automatically verifiable is a `DEFERRALS.md` row with its compensating control; ADRs written for every deviation and owned decision; `BUILD_INDEX.md` row and `LEDGER.md` advanced. *(agentic — the universal phase-gate AC)*

## Requirement IDs to satisfy and stamp in the PR
GL-JURIS-01.

## Cross-cutting invariants
- Cited from `docs/tickets/00_MANIFEST.md § Cross-cutting invariants`.

## Notes
- Owns the second-jurisdiction candidate decision (recorded at build time). Re-confirm the P18.1
  adapter seam at build time.
