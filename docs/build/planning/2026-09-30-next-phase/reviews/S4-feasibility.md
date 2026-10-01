# S4 — Adversarial review: feasibility, sizing, ordering, calendar and cost

- **Row:** S4 (Stage P), lens **feasibility**. Fresh context; the reviewer did not write the plan.
- **Written:** 2026-10-01T01:40Z → see footer (`date -u`), in `~/Eleutheria-next-phase` (`claude/next-phase-planning`,
  clean tree). **Read-only:** this file is the only write. Nothing was committed, no control file or production system was
  touched, and no external request was made.
- **Artifact under review:** `NEXT_PHASE_PLAN.md` (DRAFT, S3), `data/round11_plan.csv` (333 rows, chain rows 201–462),
  `design/S2-round-structure.md`.
- **Tested against:** `~/agent-skills/skills/{orchestrate-build,decompose-spec,implement-spec}/SKILL.md`;
  `data/ticket_catalog.csv` (scope, size, deps); `research/B5-orchestration-retro.md`; `design/H2-branch-ci.md`;
  `design/G2-activation.md`; `design/I8-acquisition-design.md` §7; `research/G1-ops.md` §0, §1, §3.8; `design/G3-release-model.md`
  (grep); `design/L3-confidence-program.md` §3.2–3.3; `design/K13-ux-synthesis.md` (grep); `design/S1c-decision-catalog.md`
  (grep); `META_PLAN.md` §7.1 and the 09-30 usage-limit entry. Codebase spot checks are listed in §6.
- **Method.** CSV facts come from scripts over `round11_plan.csv` and `ticket_catalog.csv` (scratch only). File sizes come
  from `wc -c` on the tree. Weekdays come from Python `datetime`. Anything else is labelled *(inference)*.

---

## 0. Verdict

**Ratifiable-with-fixes. Not ratifiable as drafted.** The structure is sound: one serial loop, four gated sub-rounds,
CI at every boundary, the live-leg queue, and bounded pre-authorisation. The engineering rows are mostly well-cut, and
the code paths they assume exist (§6).

As drafted, though, a fresh `orchestrate-build` session would hit three hard failures:

1. **Stage B cannot produce its own output.** SEED-13 has to write about 277 full contracts in 4 runs, which is about
   2 MB of contract text. GATE-B is unreachable at that size, or reachable only with thin contracts.
2. **Wave B cannot run in its window.** By the plan's own timeline, the Wave-B code rows come after GATE-G5, and the
   window closes before eight family-days fit.
3. **OM-19's gate rule deadlocks GATE-G4.** It does so against P34.39's three-week read-back window, which costs Wave A.
   The operator is asked to ratify OM-19 verbatim (S5-1).

All three are fixable by bounded edits to the plan and the CSV before S5. With FEA-01…03 fixed and FEA-04…12 answered,
this lens would rate the plan ratifiable.

| severity | count | ids |
|---|---:|---|
| BLOCKER | 3 | FEA-01, FEA-02, FEA-03 |
| MAJOR | 9 | FEA-04 … FEA-12 |
| MINOR | 7 | FEA-13 … FEA-19 |

---

## 1. BLOCKER findings

### FEA-01 — Stage B is not seed-sized. T3 cannot write ≈ 277 contracts in 4 runs, and T1/T4 are also over-scoped

- **Problem.**
  - SEED-13 (T3, 4.0 runs, split T3a/T3b) must write "one contract per chain row from `_TEMPLATE.md` (+ `harness:` header +
    B5 §6.2 block): `Run:` line, `live_verification`, `Live window:`, OM-14 mutation list, `live:` edges, requirement ids"
    for every row. That is ≈ 277 rows after splits (plan §8.5; Appendix A T3).
  - The plan sizes for a non-compacting subagent: CF-16 cites "one fresh subagent context, a hard ceiling".
    `decompose-spec` rule 1 says a ticket's working set must stay "well under half" the window.
- **Evidence.**
  - Round-10 contracts in `docs/tickets/` measure median 5,595 B and mean 5,462 B (n = 41). B5 §6.2's block adds ≈ 1.2 KB, and
    the `Live window:`, mutation list and `live:` edges add more.
  - Estimate: ≈ 7 KB × 277 ≈ **1.9 MB ≈ 450–500k output tokens** *(inference)*. That is ≈ 230–250k tokens per T3 half, before
    reading any of the design notes (K13, L3, I8, G3, J3) the contracts are written from.
  - Round 10's 41 contracts came out of a whole multi-session Codex package (B5 §1).
  - The other seed units are over-scoped too:
    - **SEED-11:** 31 ADRs (plan §7) at 3 runs, against a measured ≈ 9.4 KB per recent ADR (ADR-120…145 mean 9,425 B).
    - **SEED-12:** §56 with "on the order of 250 draft requirement ids" plus ≈ 25 amendments, App F, App G.7 and the
      go-live spec, at 3 runs. The plan's own R-13 records this risk.
    - **SEED-14:** 2 runs to annotate a 339 KB `DEFERRALS.md` and add four columns to a 202 KB, 715-row
      `COVERAGE_MATRIX.csv`. It must also re-verdict "the 61 unsampled boilerplate MET-DIFFERENTLY rows … row by row"
      (§6.6). Their true state is "unknown until then" (F-238), so this is investigation, not transcription.
- **Consequence.**
  - Seed runs grow from 23.2 to ≈ 40–55 *(inference)*, so R0 moves from ≈ 10-06 to ≈ 10-10…10-14. That lands squarely on
    FEA-12's cliff for Wave A.
  - The alternative is thin contracts. Workers then re-derive design, which is the "hidden cross-dependency" failure
    `decompose-spec` exists to prevent.
- **Fix (before S5). Re-scope the seed, and move work into the round where it is cheaper.**
  1. **T3a = 11A only, in full:** ≈ 53 contracts after the P34 L-splits, ≈ 4 runs. Every row 201–462 still goes into the
     manifest, and the 11B–11D rows get `Kind: skeleton` contracts (BM-TICKET-03).
  2. **Add three chain rows that run `decompose-spec mode=extend`** with a Phase-4 sizing review, against the
     already-ratified CSV. Planning stays inside "rows only from a reviewed plan" (OM-03).
     - **PLAN-11B** goes early in 11A. It fills the idle time while hosted legs wait for the 10-06→10-13 freeze (§5.1).
       ≈ 6–8 runs.
     - **PLAN-11C** goes before GATE-G5.
     - **PLAN-11D** goes before GATE-G6.
  3. **Shrink SEED-11 to the decisions that need the operator's words or bind the whole round:** ADR-146–150, 152–153,
     163–173. The engineering ADRs (151, 156–158, 161, 174–176) move to their owning tickets, which also fixes FEA-06.
  4. **Write the K13 and TRANSP requirement families with PLAN-11C,** not in SEED-12. SEED-12 keeps the MEM, ENG, OPS, SEC,
     REL and CONF families.
  5. **Move SEED-14's 61-row re-verdict into an 11A ticket** (≈ 1–2 runs). GATE-B's validators do not need it.
  6. **Re-state the seed estimate and R0 with these changes,** and size every seed unit at ≤ 1 run per context with a
     named seam.

### FEA-02 — Wave B cannot fit its window, and the slip cascades into Wave C and the final release

- **Problem.**
  - Wave B (P36.12) needs eight family-days. The CSV gives "one family per day (ACQ-08→15)", 14:00–20:00Z, "never with
    peel-on 10-29T12:00Z", inside **10-26 (Mon) → 11-05 (Thu)**. That leaves 8–9 usable weekdays, so the leg must start
    on 10-26 or 10-27.
  - The leg depends on P36.1–P36.11 (robots register, owed rights batch, ATE concept and eight family tickets), which add
    up to **10.5 runs**. They sit at the head of 11C, **after GATE-G5**.
  - ING-GO-B is also collected at G5.
- **Evidence.**
  - S2 §5.4 expects 11B to end ≈ **10-27→10-30**. Mechanically, 11B is 62.5 runs (CSV) after GATE-G4 (≈ 10-16 at best). At
    6–10 runs a day plus the P35.63 HG-11 pause and G5, the earliest Wave-B start is ≈ 10-24 and the expected start is
    ≈ 10-29…11-02. That leaves **3–6 of the 8 family-days** before 11-05.
  - The remaining families cannot run during 11-06→11-13 12:00Z (AR-3). The next weekdays, 11-16→11-20, are Wave C's
    window, and I8 §7.2 allows "at most one new manual job at a time".
  - P37.2 (Wave C) depends on P36.12 (CSV; catalog ACQ-18 → ACQ-16). So Wave C moves to 11-23…12-04, and P37.65 must
    then be cut before 12-06 or after 12-13 12:00Z.
  - CF-13's ≥ 2 activated releases and P36.70's second-release acceptance wait too.
  - The Wave-B release cut must also fall outside 11-06→11-13. In practice that puts it on top of P36.72 (≥ 11-13 12:00Z) and the
    Sunday 11-15 cadence slot (FEA-09).
- **Fix.**
  1. Move P36.1–P36.11 into 11B, before the P35.46→P35.63 spine/release chain. Their only prerequisites are P35.6,
     P35.14, P35.15, P34.38 and SEED-11, all of which are earlier in 11B or in 11A.
  2. Collect ING-GO-B at **GATE-G4**, so OM-19 can run the Wave-B leg from the queue on 10-26, whatever G5's timing.
  3. Move P37.1 (the OSM origin code) into 11C, so Wave C's leg is queued before G6.
  4. Mark explicitly whether P36.12 needs Wave A's **live** result, and whether P37.2 needs Wave B's (`live:` edges).
     If neither does, decouple them so a slip in one wave does not quantize the next.
  5. Allow two small families per day (ACQ-11, ACQ-15) to recover days.
  6. Re-run S2's §12 checks and re-state the expected dates.

### FEA-03 — OM-19's gate rule deadlocks GATE-G4 behind P34.39's 10-10…10-29 read-back window

- **Problem.**
  - OM-19, which the operator ratifies verbatim at S5-1, says: *"No GATE packet is presented while an opened window's leg
    is unexecuted."* §13.1 adds that the acceptance row "cannot pass with … an opened window whose leg is unexecuted".
  - P34.39's window (CSV) is "after the 10-10T03:35Z replay …; **remaining first-fire read-backs to 10-21T06:09Z and peel-on
    10-29T12:00Z** via the live-leg queue". That window is open at P34.47 (≈ 10-15) and stays open until 10-21. Read
    literally, P34.47 and GATE-G4 cannot complete before ≈ 10-21, and the peel-on leg then blocks G5 until 10-29.
  - GATE-G4 is a serial-chain marker (row 248). No 11B row can dispatch before it, and ING-GO-A is collected there.
    Wave A's window (10-19→10-23, 14:00–20:00Z) needs P35.1–P35.10 (≈ 9.5 runs, CSV) first.
- **Consequence.** A literal orchestrator loses most or all of Wave A. A permissive one breaks a ratified rule. Either way
  it is the Round-10 failure mode the rule was written to stop.
- **Fix.**
  1. Split P34.39:
     - **P34.39a** = the 10-10 replay read-back, the only prerequisite of P34.46;
     - **P34.39b** = the first-fire wave to 10-21 plus peel-on 10-29, as a non-blocking monitoring leg.
  2. Re-word OM-19 to say: *a GATE is not presented while a leg is **due** (its earliest time has passed, its go is held, and
     it has not run). A leg whose window extends past the GATE is listed in the packet and carried.*
  3. Apply the same wording to §13.1.

---

## 2. MAJOR findings

### FEA-04 — More rows than the 15 L rows will overflow one context, and the dispatch ceiling is never declared

- **Problem.** T3 splits only the rows sized L. Several M/S rows are L or bigger by their own catalog scope, and several
  live rows span days or an operator pause, so they cannot be one run. The plan also never states `dispatch_target` or
  the context-window ceiling the sizes were judged against. CF-16 assumes a subagent; `orchestrate-build` §0 tells the
  orchestrator to warn on a dispatch/sizing mismatch.
- **Evidence (catalog scope, quoted).**
  - **P36.42:** "Entity pages A and the Organizations hub: **L** — 06a … 06b …". The plan sizes it M, 1.0.
  - **P36.66:** "**L** (13a … 13b /s/<pub>/ build/staging/withdrawal index + selectors.conf + descriptor v2 ADR)" plus "a
    `withBase()` refactor of **85 path sites**" (G3:312). The plan sizes it M.
  - **P37.68 CAP-01:** "13 journeys × {390, 1440 px} × {JS on, JS off}" (up to 52 walkthroughs), plus per-ask checks, budgets,
    axe and an operator packet. Sized M.
  - **P38.1 CAP.1:** an independent gap analysis over ≈ 277 landed rows, plus CI for every PR. Sized M.
  - **P36.72:** merges six acceptance sets (crawl, parity, number truth, budgets, axe in both JS states, walkthroughs) and a
    Class S readout. Sized M.
  - **P37.65:** final release, crawl, scrub audit, three journey re-runs and the final HG-11 readout. Sized **S, 0.5**.
  - **P34.44:** 27-check registry, harness, a baseline reproducing L2's 45 metrics, and a nightly production job. Sized M.
  - **P36.9:** 23 heterogeneous statutory-report sources. Sized M.
  - **P38.3:** sized L (2.0) but left out of T3's "all 15 L rows" list ("T3 may split", §13.4). There are **16** rows at 2.0.
  - **Multi-leg rows,** where one context cannot span the wall-clock time: P35.61 (G2:256, "Total ≈ 1–3 working days", with
    1–4 h of operator review mid-way), P36.12 (8 family-days), P37.2 (pre-grow → tier bump → run → 24 h soak → revert),
    P35.11 (5-day wave), P37.54 (two windows), P34.39 (3 legs), and every in-ticket pause row (≥ 2 runs each).
- **Fix.**
  1. Declare `dispatch_target` (recommended: `subagent`-safe sizing even if dispatch is headless) in T5 and in the plan.
  2. Add to the mandatory pre-T3 split list:
     - P36.42 a/b;
     - P36.66 a/b, with its withBase half moved early (FEA-06);
     - P36.72 a/b;
     - P37.65 → M a/b;
     - P37.68 split per persona (A/J/O) plus the U-003 checks;
     - P38.1 split per sub-round, or made a fan-in over the four acceptance records;
     - P38.3 a/b/c;
     - P34.44 a/b;
     - P36.9 a/b by genre.
  3. Model the multi-leg rows with explicit leg counts in `est_runs`.
  4. Expect the §8.1 re-split rule (> 75 runs or > 85 rows) to fire for 11C and 11D once this is honest. Say so in the plan
     now, so the extra GATEs are not a surprise. The full sample is in §4.

### FEA-05 — The live-leg queue has no execution mechanics: branch/PR policy, re-run count and a backstop

- **Problem.** OM-19 says the orchestrator "re-runs the owning ticket in live mode", but three things are missing:
  - **Where the re-run commits.** §12 says agents "never push to a branch once a successor exists". A live leg run days
    later has nowhere defined to commit its run ledger, `probe-run/1` record or DEFERRALS transition, and no PR on which
    to read CI (OM-05).
  - **What it costs.** The plan counts 15–25 re-runs (§10.4). The CSV has **73 rows with AR-3 windows** and 85
    production-touching or publish rows. Add the 11 pauses, the multi-leg rows of FEA-04, and the acceptance rows that
    "ride" a later release (P36.71 rides P36.72; P37.63/P37.64 ride P37.65), which can only verify after promotion. The
    realistic count is ≈ 40–70 *(inference)*.
  - **What happens when the chain is not moving.** Legs run only "at every ticket boundary". During a GATE wait, a
    `blockedOn`, a usage-limit stop (the planning session hit one on 09-30, META_PLAN change log 20:12Z) or an idle
    night, there are no boundaries, so a window can open and close unrun. That is R-1 again.
- **Fix.**
  1. Add to OM-19:
     - a live leg runs on a new branch `r11/<id>-live-<n>` stacked on the current tip, with one PR and a head-bound CI read;
     - the leg's ticket contract names its re-run prompt;
     - legs whose go is already held run even while the chain waits at a GATE.
  2. Add a time-based backstop: a scheduled headless check at each window's opening and close, which alerts the operator
     if a due leg has not run.
  3. Re-state the re-run estimate (≈ 40–70) in §10.4 and in each sub-round's run total.

### FEA-06 — Several decisions have two or three owners, and `withBase()` is owned by a ticket that lands after its users

- **Problem.** `decompose-spec` says a cut must never sever a shared implicit decision. The plan's ADR list (§7, written in
  SEED-11) overlaps chain tickets whose catalog scope also says "write the ADR".
- **Evidence (catalog scope).**
  - P35.1 (OPS-03): "ADR superseding ADR-016/076's scheduling path". This duplicates **ADR-174**.
  - P35.12 (REL-01): "one ADR extending ADR-132 that also carries J3's transparency_root/snapshot_renderer fields", and
    P36.66 (TX-13b): "descriptor v2 ADR". Both duplicate **ADR-161** ("descriptor v2 (extends ADR-132, merges J3 fields)").
  - P36.13 (OPS-06): "ADR for the exposure posture". This duplicates **ADR-176**.
  - P34.30 (MEM-06): "ADR recording the split". This duplicates **ADR-148** ("D-R10-MEMORY-1 split (option C)").
  - P34.1: "pinned-test rewrite + ADR". This duplicates **ADR-151**.
  - The release identity is re-decided three times: P34.22 ("identity_digest changes intentionally"), P35.12 (identity v2)
    and P34.23 (one version source).
  - **`withBase()`:**
    - K13:598 requires "New templates use `withBase()` so TX-13b's refactor does not grow";
    - the helper does **not** exist (`grep -r withBase web/src web/scripts` finds nothing);
    - it is created by P36.66 (row 379), *after* the ≈ 30 page rows P36.16–P36.65 that must call it.
- **Fix.**
  1. Make one owner per decision. Either the seed ADR is the decision and the ticket says "implements ADR-nnn", or (better,
     and it shrinks T1) the ADR moves to the ticket.
  2. Fold the release-identity decision into REL-01 and have P34.22 fix dates only.
  3. Move the `withBase()` helper and its CI containment check into P36.18 (chrome) or a new S row before P36.16. Leave
     only the 85-site sweep and `/s/` build in P36.66.

### FEA-07 — Production-write safety gaps in P34.46, the 11B spine writes and the bucket restore points

- **Problem / evidence.**
  - **P34.46 has no go/no-go threshold.** G2 §8 R2: L44 forces "a full rewrite under ACCESS EXCLUSIVE lock; … API reads and
    ingest block". The duration is "**unmeasured**", `lock_timeout` is "[unverified]", and "if the rewrite is too long, the
    remedy is a maintainer decision". The contract carries no maximum lock time from the P34.24 rehearsal, no API
    degraded-mode or maintenance notice for the lock, and no tier bump for the slot.
  - **The rehearsal set is not the deploy set.** P34.25 (row 225, *after* P34.24's rehearsal) adds "a new sqitch change"
    for `sig_read_public` grants, and P34.24 itself reworks `shared_temporal_contract`. The hosted deploy is therefore not
    the change set that was rehearsed.
  - **Schema changes are pre-authorised.** P35.14 ("CHECK NOT VALID via a new sqitch change") and P35.32 (new hosted table)
    are hosted schema deploys, yet OM-20's never-list names only "the spine schema change (P34.46)", so they are
    pre-authorised at G4.
  - **11B rematerializations are public before HG-11.** The live API serves the spine (AGENTS.md; G2 step 2: "`--rematerialize`
    refreshes the materialized tables the live API reads … public API numbers move"). The OM-20-pre-authorised 11B writes
    (re-keying 5,278 subjects, typing backfills, P35.25–27 rematerializations, P34.45's ER re-run) therefore change public
    answers 1–2 weeks before P35.57 (API release parity) and P35.63 (HG-11). That is publication without a readout, which
    OM-20 says is never pre-authorised.
  - **Bucket restore points are not guaranteed.** P34.17 and P34.21 do not depend on P34.3, which turns on bucket
    versioning (the restore point for a bucket write). AR-2's command is SQL-only.
- **Fix.**
  1. Have P34.24b rehearse the exact plan tip, after P34.25. Alternatively, P34.46 re-rehearses on a fresh clone in its
     own pre-step.
  2. Have the P34.46 contract state a numeric go/no-go (for example, lock ≤ N min, disk headroom ≥ table size), the
     degraded-mode or notice step, the trigger pause list and the decision if over threshold.
  3. Make OM-20's never-list class-based: "any hosted sqitch change that takes an ACCESS EXCLUSIVE lock or rewrites a
     table".
  4. Either move P35.57 before P35.22, or record in the plan, as an operator line, that API-visible rematerialization in
     11B is accepted. "Never pre-authorised publication" must not silently exclude the API.
  5. Add `live:P34.3` to P34.17 and P34.21, and a bucket pre-copy to AR-2.

### FEA-08 — The DNS move (OP-09) is the highest-blast-radius change in the plan and has no ticket, runbook or probe

- **Problem.** If A-3 = a, the operator moves `surveillancegraph.org` from Squarespace DNS to Cloudflare "by GATE-G4" (OP-09),
  with no agent-prepared zone inventory, TTL step-down, rollback or post-move probe. OM-14 binds only agents.
- **Evidence.**
  - The LB uses a Google-managed certificate, "ACTIVE (apex + www, expires **2026-12-22**, auto-renewing)" (G1:82).
  - If the LB hostnames are proxied through Cloudflare, Google's load-balancer authorisation cannot see the LB IP, and
    renewal (due in the weeks before 12-22) can fail. That lands during Wave C and the final release *(inference from how
    Google-managed certs validate)*.
  - The Cloudflare/R2 bill and the `sig-project.org` registrar sit **outside** the GCP budget alert that P34.5 builds, so
    U-011's "budgets … always made clear" has a blind spot.
- **Fix.**
  1. Add an S row before OP-09 that writes the zone inventory and the cut-over runbook:
     - LB records DNS-only (grey cloud), R2 on a subdomain;
     - TTL lowered 48 h ahead;
     - DNSSEC handling;
     - rollback = revert the nameservers at the registrar.
  2. Add a probe row after OP-09: TLS, the cert's renewal status, every route, and mail if any.
  3. Make P34.5's spend ledger include non-GCP lines.

### FEA-09 — Operator load is undercounted about 1.5–2×, and "continue" turns approval fatigue into silent descopes

- **Problem.** §0/§11.2 say "≈ 12–18 h … batched into about five sittings". The touchpoints are larger and more numerous
  than that, and several are synchronous.
- **Evidence.**
  - **S5 alone is ≈ 91 lines** (A 18, B 42, C 11, D2 16, S5-1…4). Several need the operator's own words (A-6 waiver, C-3
    counsel and robots, C-5 About), against S1c's "about 45 minutes".
  - **Class S sign-off "costs the operator 1–2 hours"** (G3:412). The plan has 5–7 Class S promotions: P35.63, the P36.12
    Wave-B release, P36.70 (Class S by default), P36.72, P37.65, and the 11-15/12-15 cadence cuts unless a standing go
    exists. Each adds an OPCHECK of 20–40 min. That is ≈ 7–19 h for releases alone.
  - **P35.61's plan review is "1–4 h operator"** (G2:256).
  - **Synchronous slots:**
    - P34.46: weekday 14:00–20:00Z, "operator available in the slot";
    - the P37.2 tier-bump go inside a 5-day window;
    - **11-15-2026 is a Sunday**, and REL-07's cron `0 14 15 * *` would cut a Class S release that day;
    - 11-13…11-15 can stack three Class S cuts (P36.12's release, P36.72, the cadence cut).
  - Counted by date, there are **≈ 18–20 distinct touchpoints**:
    - S5, GATE-B, the P34.17 and P34.21 gos, the P34.46 slot, G4, OP-09, P35.61, P35.63, G5, OP-14;
    - the P36.12, P36.70 and P36.72 readouts, G6, the P37.2 tier bump, P37.65;
    - the CAP-01 walkthroughs (13 journeys), GATE-ACCEPT-R11 and GATE-ANNOUNCE.

    A realistic total is ≈ 22–32 h *(inference)*.
  - "`continue` is a complete answer: every line inside takes its own default" (S2 §3.6). Nine defaults descope operator
    asks (§4.4), so a tired "continue" silently descopes.
- **Fix.**
  1. Re-state the operator time and touchpoint calendar by date.
  2. Suppress the cadence cut when a Class S promotion happened within 14 days, and move the slot to a weekday.
  3. Make a GATE's "continue" refuse to apply a **descoping** default without an explicit line, or list those defaults
     first in the packet.
  4. Split S5 into two sittings: Part A plus S5-1…4 first, so the seed can start; then B, C and D2.

### FEA-10 — Agent spend and throughput: the operator gets a volume, not a cost or a feasibility check

- **Problem.** §10.4 says "≈ 300–330 fresh worker contexts" and "dollars where the operator's plan exposes them". The
  calendar assumes 6–10 runs a day for 9–10 weeks (S2 §5.4).
- **Evidence.**
  - The planning session hit an account usage limit on 09-30 (META_PLAN change log 20:12:19Z: "Claude monthly/session spend
    limit"; "planning agents are expensive").
  - The volume estimate rests on "Round 10's experience". Round 10 executed **no** live legs (B5 §3.2; F-14), so it is not
    a base rate for OM-19 re-runs.
  - Counting FEA-01/04/05, the realistic volume is ≈ 360–420 contexts *(inference)*.
- **Fix.**
  1. Before GATE-P, give the operator one line: runs × measured tokens per run (from Stage P transcripts) ≈ usage per week,
     against the plan's limit.
  2. State the throughput the calendar needs (≈ 6–10 runs a day, every day).
  3. At G4, re-project both the calendar and the spend from 11A's measured runs a day, and pause rather than silently
     stretch if usage limits bind.

### FEA-11 — The first model release (P35.63) is hostage to every Stream-L target at `enforce`, and it sits on the calendar's critical path

- **Problem.** §5.4's acceptance puts P35.63 "at `enforce`". Its targets include:
  - technology on **100 %** of site rows;
  - 0 undisclosed out-of-polygon points;
  - byte binding 100 % for re-run sources;
  - 0 collisions;
  - 0 publisher-as-operator;
  - plus 21 `depends_on` (CSV).

  L3 §3.3: "an `enforce` failure blocks promotion".
- **Consequence.** One residual miss means a fix cycle, which delays G5, which delays Wave B (already infeasible, FEA-02),
  which delays Wave C.
- **Fix.** P35.63's gate becomes "0 ratchet regressions + 0 failures on checks flipped to `enforce` by landed rows". The
  absolute targets move to CONF-14 (P37.67) as round targets. Any residual is a known-issue line in the readout, not a block.

### FEA-12 — The calendar does not slip "one-for-one with R0". Window quantization creates cliffs the operator is not shown

- **Problem.** §0 and S2 §5.4 say that the calendar "slips one-for-one with the seed date R0". That is false. Monthly AR-3
  freezes (days 6–13) and "one manual job at a time" turn a slip of a few days into a slip of weeks. I8:917 states that
  its wave dates "assume R0 ≤ 2026-10-14".
- **Evidence (inference, from the CSV run sums and the windows; FEA-02/03 assumed fixed):**

  | first dispatch R0 | 11A end / G4 | Wave A (10-19→23) | Wave B (10-26→11-05) | Wave C (11-16→20) | final release P37.65 |
  |---|---|---|---|---|---|
  | ≤ 10-09 | ≈ 10-15…10-19 | in window | in window *only with* FEA-02's fix | in window | ≈ 12-01…12-05 |
  | 10-10…10-13 | ≈ 10-19…10-21 | partial (1–3 days) | spills past 11-05 | competes with Wave B → 11-23+ | tight before 12-06, else ≥ 12-13 12:00Z |
  | ≥ 10-14 | ≥ 10-21 | missed; runs 10-26+ and displaces Wave B | → 11-16…11-20 (collides with C) | → 11-23…12-04 or 12-14…12-18 | ≥ 12-13; tail and acceptance in late December |

- **Fix.**
  1. Replace "one-for-one" with this cliff table.
  2. Name the latest R0 that keeps each wave (≈ 10-09 for Wave A *as planned*).
  3. Add to Part A a line for the operator: *"if R0 > 10-09, drop Wave A to the 10-26 window and accept Wave C in
     11-23…12-04"* (or similar), so the trade-off is decided rather than discovered.

---

## 3. MINOR findings

- **FEA-13 — Count consistency.**
  - 16 rows have 2.0 runs, not 15: P38.3 is missing from §8.5 and CF-16.
  - The CSV yields 85 production-touching or publish rows (11B 26). §8.1 says 84 (11B 25); P35.13's
    "publish (next republish)" with gate `none` is the likely difference.
  - "33 first fires" (plan §2.1, §8.4) vs "32" (S2 §5.1, I8 §7.2).
  - **Fix:** regenerate the plan's numbers from the CSV builder.
- **FEA-14 — Wave A's image roll collides with an existing trigger.** Wave A rolls one image to the fleet (I8 §7.1), while
  the existing `legistar` trigger `0 5 20 * *` fires on **10-20 at 05:00Z, inside the window**. The widened Legistar pass
  (3 h timeout) would then first-run unobserved at night, inside the 03:00–06:30Z band I8 §7.2 forbids. **Fix:** pause
  the widened existing triggers during their wave, or roll after their fire.
- **FEA-15 — Wave B's first fires overlap Wave C's heavy work.** Wave B's new monthly batches first fire 11-16…11-24 (I8
  §7.3), 07:17–07:27Z with up to 6 h timeouts. That overlaps Wave C's tier-bumped national run and ER rematerialize if
  those overrun 20:00Z, against "never concurrent with `sig-materialize`". **Fix:** have the Wave C contract pause the
  r11 batches for 11-16…11-20, or shift their crons to after 11-20.
- **FEA-16 — P34.1's 10-19 deadline has no fallback.** If R0 > ≈ 10-16 (the FEA-01 risk), P34.1 lands after the runner
  switch. **Fix:** say in T6 that if R0 > 10-16, the seed PR pins `runs-on: ubuntu-24.04` (H2 allows it) and P34.1 keeps
  the rest.
- **FEA-17 — Integration debt grows to ≈ 330 stacked PRs** (#141–#190 plus ≈ 280 Round-11 PRs, plus the live-leg PRs from
  FEA-05). One P38.3 "integration plan" row covers it, and the operator's eventual merge is uncosted. **Fix:** offer an
  optional operator merge of each sub-round's stack after its GATE (agents still never merge), and size P38.3's
  integration leg separately.
- **FEA-18 — Cost.**
  - The ceiling is safe even if G1's unverified ≈ $90–100 baseline is double: ≈ $180–200 + $33 < $300.
  - Three unmeasured lines remain: P37.4's Data Access audit-log volume ("log volume unmeasured"), R2 Class-B operations
    under a request flood (the $50 egress ceiling does not cover operations), and the Wave-C pre-grow, which is one-way.
  - **Fix:** C-7 now, and P34.5 within 11A's first days. Add an audit-log exclusion filter and volume alert to P37.4. Add an
    R2 operations ceiling to P35.5.
- **FEA-19 — P34.45 is classed inconsistently.** L3:867 says CONF-02's republish is "Class S", while the CSV says
  "publication rides the next republish/release (no extra Class S)". S5-3 pre-authorises P34.45 even though it has a
  publish stage and OM-20 never pre-authorises republishes. **Fix:** state that P34.45's public leg rides P35.63's Class S,
  and pre-authorise only its ER re-run.

---

## 4. Sizing sample: 37 rows, all 16 at 2.0 runs plus 21 others

**Legend:**
- **fits** — one fresh context with headroom.
- **T3 a/b** — the planned split is adequate.
- **split before T3** — add the row to the mandatory list in FEA-04.
- **legs** — multi-run by wall clock; model the runs explicitly.

**Rows at 2.0 runs (16):**

| row | size | verdict | seam / note |
|---|---|---|---|
| P34.21 attribution + gate + republish #2 | L | T3 a/b | a: sink rights resolution, backfill code, publish gate · b: re-export + republish #2 (pause → +1 leg) |
| P34.22 date truth in code | L | T3 a/b | a: constants + tree literal test · b: fixtures, `sources.toml` lines, regeneration. The release-identity decision goes to REL-01 (FEA-06) |
| P34.24 sqitch hygiene + clone rehearsal | L | T3 a/b | a: hygiene + round-trip CI · b: rehearsal **after P34.25** (FEA-07) |
| P34.34 archive + export-mode build | L | T3 a/b | a: links, crawl, `leverage.json` · b: CI export build + budgets |
| P34.42 least-privilege identities | L | T3 a/b, 2 legs | a: SAs + 3 services · b: 88 jobs + Editor removal. Both live after 10-13 12:00Z |
| P35.1 scheduler of record | L | T3 a/b | the ADR is a duplicate (FEA-06) · a: live-diff + lint · b: fleet hygiene/cruft (live) |
| P35.14 vocabulary + entity typing | L | T3 a/b | a contains a hosted sqitch change (FEA-07) |
| P35.15 technology typing + backfill | L | T3 a/b | b = 200k-subject live backfill |
| P35.20 public number derivations | L | T3 a/b | — |
| P36.1 robots / opt-out register | L | T3 a/b | **move to 11B** (FEA-02) |
| P37.4 security baseline | L | T3 a/b | b live (audit logs, ENCRYPTED_ONLY) |
| P37.5 ingestion hardening | L | T3 a/b | — |
| P37.16 dossier live captures | L | T3 a/b, legs | four HG-03-gated passes, 2 per half |
| P37.46 organisation identity | L | T3 a/b | 13a / 13b seam is natural |
| P37.57 projection rebuild CI | L | T3 a/b | — |
| P38.3 REC | L | **split before T3 (a/b/c)** | backlog + readiness / spec reconciliation / integration of ≈ 330 PRs |

**Other rows (21):**

| row | size | verdict | seam / note |
|---|---|---|---|
| P34.10 one publish path | M | fits | — |
| P34.17 web honesty + republish #1 | M | fits + 1 leg | the pause makes it ≥ 2 runs |
| P34.25 API honesty code | M | fits | adds a sqitch change; reorder with P34.24b |
| P34.39 first-fire read-backs | S | **legs (3)** | split a/b (FEA-03) |
| P34.44 quality harness + baseline | M | **split before T3** | a: registry, harness, tests · b: L2 baseline run + nightly job (live) |
| P34.46 Round-10 schema + API roll | M | fits + legs | prep / slot / soak read; needs a go/no-go (FEA-07) |
| P35.11 Wave A | S | **legs (≈ 3)** | roll, manual runs, +0, resume |
| P35.24 subject re-keying | M | fits (borderline) | needs the IDOT/FL511 investigation done first |
| P35.46 derivation collapse | M | borderline → a/b | code / production ER run |
| P35.53 release pipeline | M | borderline | state machine + IaC + staging services + SA |
| P35.61 bounded apply | M | **legs (≥ 3)** | audit + plan → operator review → apply + freeze (G2: 1–3 working days) |
| P35.63 first model release | M | **legs (≥ 2)** | stage (1–2 h, G3:291) + V1–V15 + readout → promote + rollback rehearsal |
| P36.5 Flock/ALPR layers (16) | M | fits (borderline) | one connector family (`arcgis_query`) |
| P36.9 statutory disclosures II (23) | M | **split before T3** | by genre: UAV/FRT · CSS/interception/ATE/DHS |
| P36.12 Wave B | M | **legs (8–9)** | one family per day + materialize + release |
| P36.18 layout and chrome | M | fits | best home for the `withBase()` helper (FEA-06) |
| P36.42 entity pages A + hub | M | **split before T3** | the catalog itself says L |
| P36.66 snapshots + withBase | M | **split before T3** | the catalog says L; plus 85 path sites |
| P36.72 ACC-PLACES | M | **split before T3** | crawl/parity/budgets · walkthroughs · Class S |
| P37.65 final release + readout | S | **split before T3 (M a/b)** | the final Class S under-sized at 0.5 |
| P37.68 CAP-01 | M | **split before T3 (×3–4)** | per persona + U-003 checks + operator packet |

Also checked, all fits: P36.37 map shell (M), P37.26 graph explorer A (M), P37.36 raw archive (M, borderline),
P35.58 verification B (M, borderline). P38.1 CAP.1 (M) is split before T3, per sub-round (FEA-04).

---

## 5. The eight requested checks, answered

1. **Sizing.**
   - The 16 two-run rows are correctly flagged. P38.3 must be added to the mandatory list.
   - Nine more rows must split before T3: P34.44, P36.9, P36.42, P36.66, P36.72, P37.65, P37.68, P38.1, plus P38.3. Eleven
     rows are multi-leg by wall clock (FEA-04).
   - No dispatch ceiling is declared.
2. **Order and coupling.**
   - Wave-B code sits after its window opens (FEA-02).
   - P34.25's sqitch change lands after the rehearsal (FEA-07).
   - Five or more ADR decisions have duplicate owners, and `withBase()` is owned by a late ticket (FEA-06).
   - Otherwise the order is sound: guards before records, content before republish, foundations before pages, and spine
     writes before freeze. S2 §12 reports 0 order violations.
3. **Calendar.**
   - Wave A fits only with R0 ≤ ≈ 10-09 and FEA-03 fixed.
   - Wave B does not fit as structured (FEA-02).
   - Slips are cliff-shaped, not one-for-one (FEA-12).
   - Live legs can be "queued but never run" whenever the chain is not moving (FEA-05).
   - Ubuntu 10-19 is safe unless the seed slips past ≈ 10-16 (FEA-16).
4. **Production writes.**
   - In place: restore points (AR-2), the drill before the schema deploy, no hosted revert, the clone rehearsal, and
     never-pre-authorised P34.46/P35.61.
   - Missing: a numeric go/no-go for the L44 lock, rehearsal of the actual deploy set, class-based treatment of other
     hosted schema changes, the API as an un-gated publication channel during 11B, and bucket restore-point ordering
     (FEA-07).
   - The OSM national run has pre-grow (one-way), a tier bump with a restart, and suppression as rollback. Adequate.
5. **Cost.**
   - The $300 ceiling holds with wide margin even at 2× G1's unverified baseline.
   - Open items: R2/DNS creates spend outside the GCP budget alert, and a certificate-renewal risk (FEA-08), and C-7 should
     be answered now (FEA-18).
6. **Operator load.** ≈ 18–20 touchpoints and ≈ 22–32 h, not 5 sittings and 12–18 h. The S5 sitting is under-budgeted.
   "Continue" applies descoping defaults (FEA-09).
7. **Agent spend.** The operator is told a volume (300–330 contexts), not a cost, a usage rate or a throughput check, even
   though a usage limit was already hit. Realistic volume is ≈ 360–420 (FEA-10).
8. **The Stage-B seed is not seed-sized.**
   - Keep in the seed: SEED-00…10, SEED-02/03 (the guard core), SEED-15…19, the operator-word ADRs, MEM–CONF requirement
     families, and the 11A contracts.
   - Move into Round 11: the 11B–11D contracts (PLAN rows), the engineering ADRs (to their tickets), the K13/TRANSP families
     (with PLAN-11C), and the 61-row re-verdict (an 11A ticket) (FEA-01).

---

## 6. Codebase spot checks (do the assumed modules exist?)

**Present**, which supports the catalog's anchors:
- **Ops modules and scripts:**
  - `ops/src/ops/{publish,scheduled,backup,release_candidate,release_publish_verify}.py`;
  - `ops/cadence.toml`;
  - `ops/gcp/{materialize,web,export,scheduled-ops}.sh`.
- **Data and API files:**
  - `db/src/db/dispositions.py`;
  - `db/deploy/shared_temporal_contract.sql`;
  - `api/src/api/cli.py`.
- **Workflows:** `.github/workflows/{reingest,observability}.yml`.
- **Search, release and resolution modules:**
  - `policy/src/policy/crawler.py`, `policy/src/policy/data/crawler_conduct.toml`;
  - `exports/src/exports/release_pages.py`;
  - `resolution/src/resolution/evaluator.py`;
  - `connectors/src/connectors/osm.py` (`physical_asset_rows`).
- **Build-memory tools:** `docs/build/tools/{check_spec_src,check_coverage_matrix,check_backlog,obligation_events,current_projection}.py`.
- **Spec sources:** `docs/research/_meta/spec_src/{99a_appF_adr,99c_appG_corrections}.md` and `docs/3_sig_golive_spec.md`.
- **`sig-ops` verbs** (`ops/src/ops/cli.py`): `probe-hosted`, `backup-drill`, `roll-jobs`, `evidence-audit`,
  `recovery-plan`, `recovery-apply`, `recovery-freeze`, `release-candidate`, `egress-report`.
- **Makefile:** `scan-secrets` and `docs-check*`.

**Absent but planned as new** (fine): `docs/build/tools/memory_guard.py`, `ci_boundary.py`, `ops/public_routes.toml`,
`quality_checks.toml`, `ADR_TRIGGERS.csv` and `docs/ops/RUNBOOK.md`.

**Absent and assumed to exist before its owner lands:** `withBase()` (FEA-06).

`db/sqitch.plan` still carries future `planned_at` values (10-02…10-19). P34.24 and SEED-02's G1 diff mode must treat
these as known corrections, not new violations.

**Sizes that bound the seed** (`wc -c`):

| file | bytes |
|---|---:|
| `docs/build/LEDGER.md` | 679,109 |
| `docs/tickets/DEFERRALS.md` | 339,292 |
| `docs/build/BUILD_INDEX.md` | 295,436 |
| `docs/build/COVERAGE_MATRIX.csv` | 201,858 |
| `docs/tickets/00_MANIFEST.md` | 102,012 |
| `docs/2_canonical_design_spec.md` | 728,916 |

---

*End of review. Written 2026-10-01T01:40:37Z → 2026-10-01T01:43:15Z (`date -u`). The planning orchestrator closes this
review in `reviews/REVIEW_CLOSURE.md`, not here.*
