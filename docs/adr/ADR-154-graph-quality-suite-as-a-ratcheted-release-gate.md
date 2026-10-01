# ADR-154: Graph-quality suite as a ratcheted release gate

- **Status:** Accepted
- **Date:** 2026-10-01T04:03:25Z (decided by the operator at GATE-P — A-6, log round 3)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Decided by:** the operator at GATE-P (`docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`):
  - **A-6** (log round 3, 2026-10-01T04:03:25Z) — question *"evaluation: supersede rows 184–187; auto-merge only C0–C2;
    waive SIG-EVAL-004 lower bound for C0–C2"*; options "Adopt waiver sentence (Recommended) · No waiver"; answer
    **"Adopt waiver sentence (Recommended)"**. The adopted sentence (quoted with its sha256 in ADR-153) accepts "derivation,
    not identity … as ADR-L3-B describes"; L3's program, of which this suite is the mechanical half (ADR-L3-C), is what A-6
    adopted (agent interpretation, labelled; plan §7 row 154 lists A-6 as this ADR's S5 line). Decision-catalog members
    answered at A-6: Q-L3-1, Q-L3-2, Q-24, Q-25, Q-E2-15, Q-F4-1/2/3.
  - Related, not this ADR's decision line: **B-31** (log round 15, 2026-10-01T04:43:37Z, **"No maintainer check"**) answered
    Q-L3-5 = yes — `/quality/` public, including failing and ratchet checks — which governs how this suite's results are
    shown (ADR-152).
- **Requirement ids:** draft SIG-CONF-D06 (graph-quality suite: a versioned check registry and a release-bound
  `quality.json`), D07 (ratchet discipline), D08 (real-data regression corpus), D09 (upstream reconciliation), D13
  (least-privilege audit path) → SIG-CONF-0nn with the same numbers (SIG-CONF-D01 → SIG-CONF-001 …) in SEED-12's id map `PD/stageB/T1_id_map.csv`, read at writing (SEED-12 owns the final ids); feeds SIG-EVAL-003 and
  SIG-EVAL-006 → MET once CONF-09/CONF-12 land (plan §6.6), SIG-EPIS-029 and SIG-RECON-018 → MET when GQ-11/GQ-12 pass live;
  the release-gate placement lives in the SIG-REL family (G3 V-suite; plan §5.8).
- **Spec:** proposed Part XII §56 for the SIG-CONF drafts and the SIG-REL release-gate family (SEED-12).
- **Supersedes:** none — no landed ADR (plan §7 lists none for this ADR).
- **Amends / qualifies / extends:** none. Any appended status line on a landed ADR is written by SEED-11d, not here.
- **Sources:** plan §5.4 (design and acceptance, FEA-11), §5.8 (acceptance), §6.2 (SIG-CONF row), §6.6, §7 row 154;
  `PD/design/L3-confidence-program.md` §0 item 3, §3.1–§3.6, §5.1, §5.4, §7 (D06–D09, D13) and ADR-L3-C (§8);
  `PD/reviews/S4-feasibility.md` FEA-11 and `PD/reviews/REVIEW_CLOSURE.md` (FEA-11 closed); `PD/data/round11_plan.csv`
  rows P34.44a/b, P35.23, P35.63, P37.45, P37.67 (`PD` = `docs/build/planning/2026-09-30-next-phase/`).
- **Recorded:** 2026-10-01T07:35:39Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — agent-drafted
  record of the operator's decision; operator words quoted verbatim from `PD/feedback/RATIFICATION_LOG.md`.

## Context

Release validation checks integrity only, so every synthesis defect L2 measured "ships green" (L1 NEW-13). L1 proposed 17
invariants and L2 14 checks; 29 of L2's 45 metrics fail today. G3's promotion gate is all-or-nothing ("any failure or skip
blocks promotion; a waiver is possible only with Class S"), so adopting the checks as hard V-checks would force a choice
between never releasing and waiving every release (L3 NEW-3). B4's G10 places probes but defines no data-truth suite. With
no independent human evaluation available (ADR-152), the mechanical suite is the only thing that can hold the fixes the
round makes, and L3's rule is that only mechanical checks gate.

## Decision

1. **The suite (`sig.quality-suite/1`): 27 checks.** L1's 17 invariants and L2's 14 checks deduplicate to 23 (L2's C14 is
   an evaluation method, not an invariant), L3 adds 4 (GQ-23 derivation census, GQ-24 inferential auto-write lock, GQ-25
   origin distinctness, GQ-26 metamorphic ER invariants), and GQ-27 (basis labels and claim markers) is listed but owned by
   B4 G10 — 27 in all (L3 §3.1–§3.2). They are declared in a versioned registry,
   `exports/src/exports/data/quality_checks.toml`: id, statement, population, placement (I ingest/sink · M nightly spine
   probe · R release gate · P pull request · S scheduled public probe), mode, baseline, threshold, `flips_in` ticket and
   basis class. A change to the registry is reviewed like a ruleset.
2. **Three modes.** **enforce** — a failure blocks the run, materialization or promotion; **ratchet(b)** — the baseline is
   L2's measured value, any regression beyond it fails, improvement is recorded, and the check flips to `enforce` in the
   ticket that removes its cause (the repo's `LD-` xfail convention applied to data); **report** — published, never gating
   (used where the evidence is agent or maintainer judgment, e.g. GQ-22 relevance, or where no target is settled). **Only
   mechanical checks gate**; a check that needs judgment can neither block nor unblock a release.
3. **Ratchet discipline.** A baseline may move only toward its threshold. **Loosening a baseline or a threshold needs a new
   ADR** (SIG-ENG-003; draft SIG-CONF-D07) — the same rule as never loosening an xfail's assertion.
4. **Release gate V15 "graph quality".** V15 runs the R-placed checks over the candidate files in G3's verify stage and
   writes `quality.json` into the release; it **consumes** V6 (GQ-16), V8 (GQ-17), V9 (GQ-08), V13 (GQ-27) and V14 (GQ-20),
   which keep their owners, rather than re-implementing them. The descriptor gains a `quality` block (suite digest, report
   digest, `enforce_failures`, `ratchet_regressions`, `basis_counts` with B5 = 0, source-mix and ruleset digests).
   - **V15 passes at 0 ratchet regressions + 0 enforce failures** (FEA-11). The first model release, P35.63, runs the full
     V1–V15 suite (CF-05), and its gate is "0 ratchet regressions and 0 failures on checks that landed rows have flipped
     to `enforce`"; any residual miss against an absolute target is a known-issue line in the readout, not a block.
   - A ratchet regression, or a `report` metric moving the wrong way beyond its alert band, makes the candidate **Class S**
     (an operator-signed readout listing the deltas); Class R requires 0 enforce failures and 0 ratchet regressions, and the
     Class R standing go is void on any ratchet regression (B-9; ADR-161).
5. **Lanes.** Ingest/sink checks fail only the target's run; a nightly spine probe runs read-only through the `sig_audit`
   login with a statement timeout and writes a `probe-run/1` record per run (B4 G10; draft SIG-CONF-D13); PR tests run over
   the **real-data regression corpus** (P35.23), whose oracles are computed from the captured source bytes by code
   independent of the pipeline, with snapshot changes approved by an explicit commit and non-redistributable (e.g. ODbL)
   slices kept in the restricted bucket with only digests committed; upstream count reconciliation per target per run
   (GQ-19; |Δ| ≤ 1 % or explained, enforced once promoted). **No-vacuous-pass (B4 G11)** applies to every check:
   candidates > 0 with evaluated = 0 fails. Estimated extra spend ≤ $5/month (L3 §3.4, an estimate).
6. **Rows (plan §5.4; `round11_plan.csv`).** P34.44a/b (CONF-01: registry, harness and the L2 baseline in ratchet mode;
   nightly probe) → each fixing row flips its checks → P35.63 (first model release, V15) → P37.45 (CONF-12: `/quality/`
   renders every check from `quality.json`, failing and ratchet checks shown, stating "no human check performed") → P37.67
   (CONF-14: re-measure L2 on the final release against the round targets of plan §5.4; every miss names its fixing row).

## Consequences

- Every fix ticket's acceptance includes flipping its checks to `enforce`; a silent regression becomes red.
- The first releases can ship while 29 of 45 metrics still fail, without hiding a regression or claiming an unearned pass;
  the absolute targets are round targets measured at P37.67, not release blockers (FEA-11).
- `/quality/` and the release descriptor have one source of truth (`quality.json`), and every number on the page traces to
  a check, a population and a basis class.
- One more scheduled job (the nightly probe) and its Cloud SQL load, scheduled off-peak with capped concurrency.
- Each check flip is a reviewable registry change; loosening is a new ADR, so the suite cannot be relaxed quietly.

## Alternatives considered

- **Adopt the checks as hard V-checks at once:** rejected — with 29 of 45 metrics failing, no release could ship without
  waivers (L3 NEW-3).
- **Report-only:** rejected — it does not hold the fixes the round makes.
- **P35.63 gated at `enforce` on every Stream-L target** (the pre-S4c acceptance): rejected at S4c (FEA-11) — one residual
  miss would delay the release, and with it the later sub-rounds and waves on the calendar's critical path.

## Revisit trigger

- Every ratchet check has flipped to `enforce` (the ratchet mode can then be retired by a new ADR).
- Nightly-probe cost on Cloud SQL exceeds 5 % of instance time.
- A check shows persistent false positives (≥ 3 releases).
- Any proposal to loosen a baseline or threshold, or to let a `report` (judgment-based) check gate.
