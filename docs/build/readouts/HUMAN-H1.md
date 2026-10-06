# Readout — HUMAN-H1 (GOV.1 / GL-GOV-01) — Legal home & operating governance

- **Chain row:** P23.2 · **Kind:** human marker · **Gate register:** HG-01, HG-11
- **Ticket:** `docs/tickets/P23.2__legal-home-and-governance.md`
- **Dispositioned:** 2026-09-10 by orchestrate-build (applying pre-recorded GL-GATE-01)

## Verdict: INTERIM (recorded) — HG-01 interim posture applied; HG-11 remains genuine operator work

- **HG-01 (legal home) — INTERIM per GL-GATE-01.** "SIG operates as an independent open-source
  project under maintainer stewardship pending a formal legal-home designation." This unblocks the
  artifacts. **Not a substitute for legal counsel.** A **real** legal home remains a human action
  **before the actual public cutover (Go-public / GATE-G2)**. Provenance: operator-delegated
  engineering/interim disposition (2026-09-09), NOT counsel.
- **HG-11 (governance) — NOT pre-answered.** Two reviewer roles + written-concurrence workflow
  (`ReviewerConcurrence`, SIG-PUB-008) and a live takedown/corrections contact are genuine operator
  work, still owed. Tracked by `D-P21.4-2` (HG-11) — OPEN.

## What would pass it
Operator names the real legal home in `docs/governance/governance-and-code-of-conduct.md`, defines
the two reviewer roles + concurrence workflow, stands up the takedown/corrections contact, and ticks
`docs/build/reports/PUBLICATION_CHECKLIST.md` HG-01/HG-11 with evidence links.

## Consequence recorded
LIVE.2 public publish (P21.4) stays gate-pending on real HG-01 + HG-11 → RETURN PASS; DEFERRALS
rows `D-P21.4-1` (HG-01), `D-P21.4-2` (HG-11) remain OPEN. Go-public (GATE-G2) stays human.

## Update — 2026-09-15 (operator post-chain action)

- **HG-01 (legal home) — NAMED.** The operator named the legal home: **Steven Vitali**, an
  individual maintainer operating in a personal capacity, recorded in
  `docs/governance/governance-and-code-of-conduct.md § Legal home` (SIG-GOV-012). This resolves the
  GL-GATE-01 interim posture with a real named home. `PUBLICATION_CHECKLIST.md` item 1 is ticked;
  `D-P21.4-1` flipped to **DONE**; GATE DECISIONS records HG-01 (2026-09-15). Honest scope: an
  individual as legal home is an **interim** designation carrying personal exposure and is **not**
  legal advice; a more durable home + HG-02 counsel are recommended before real public exposure.
- **HG-11 (governance roles + written concurrence + live takedown contact) — DEFERRED by operator.**
  No named independent reviewers exist yet; the operator chose to defer. `D-P21.4-2` stays **OPEN**
  (RETURN PASS, not a block). Consequence: Go-public (GATE-G2) remains impossible until HG-11 is
  established (checklist items 2–3) and counsel supersedes item 4 (HG-02, also deferred).

## Addendum — DATE CORRECTION (SEED-08, appended 2026-10-01T08:21:03Z; ADR-146; append-only)

- *Agent record (labelled): written by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B unit SEED-08.* The text above is unchanged; this changes no status.
- **DC-RO-03.** Line 5's disposition date is a Round-3 "chain date": recorded 2026-09-10 → true 2026-09-13T19:40:01Z (retro: the writing commit `eb72be5f`; `docs/build/runs/P21.5.md` line 23: "Environment clock read 2026-09-13; chain date for this re-run = 2026-09-10"). Register rec 1021.
- **Harness and model (B7 §3 S4).** The disposition was written in the Devin CLI session `polydactyl-author` with model `claude-opus-4-8-medium` (retro: B7 §1–§3). It applied the pre-recorded GL-GATE-01 answer, not an answer given at this gate's pause. The annotation of the restored GATE DECISIONS block in `docs/build/LEDGER.md` (SEED-06) classes this gate's restored entry R38 as clock-false and delegated.
