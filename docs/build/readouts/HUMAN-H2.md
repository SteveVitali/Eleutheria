# Readout — HUMAN-H2 (LEGAL.1 / GL-LEGAL-01) — Counsel sign-off

- **Chain row:** P23.3 · **Kind:** human marker · **Gate register:** HG-02
- **Ticket:** `docs/tickets/P23.3__counsel-signoff.md`
- **Dispositioned:** 2026-09-10 by orchestrate-build (applying pre-recorded GL-GATE-02)

## Verdict: INTERIM ENGINEERING DISPOSITION (recorded) — publish-permitting, NOT a legal opinion

Per GL-GATE-02: publication of the SIG graph, the OSM-derived compartment (ODbL — separate +
attribution + share-alike), and the OKC dossiers is **permitted as an engineering disposition**,
resting on the *structural* safeguards already built and tested:

- Part VIII: no plate/trip/per-person storage or lookup; officer-naming gate; sensitivity tiers +
  coordinate rules.
- Per-compartment licences (ODbL compartment kept separate); publication tiers; honest-rendering.

**Every artifact that relies on this is labelled "operator/engineering disposition pending counsel;
counsel review recommended before real public exposure."** This is **NOT a legal opinion.** A real
counsel opinion supersedes it before public exposure. Provenance: operator-delegated engineering
disposition (2026-09-09), NOT counsel.

## What would pass it
Counsel records dated opinions (ODbL 4.4(b) / RISK-P0-01, officer-naming gate, publication tiers +
sensitive-coordinate rules, Part VIII of the published surface) in a governance doc + a GATE
DECISIONS opinion summary; if any tightens the interim posture, the affected COVERAGE_MATRIX/ADR
note is updated (append-only) and INFRA.1/LIVE.2 consume it.

## Consequence recorded
DEFERRALS row `D-LEGAL.1-1` (HG-02) remains OPEN. INFRA.1 (P21.5) OSM export + LIVE.2 (P21.4)
publish rely on the interim disposition; real public exposure waits on counsel + Go-public.

## Addendum — DATE CORRECTION (SEED-08, appended 2026-10-01T08:21:03Z; ADR-146; append-only)

- *Agent record (labelled): written by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B unit SEED-08.* The text above is unchanged; this changes no status.
- **DC-RO-04.** Line 5's disposition date is a Round-3 "chain date": recorded 2026-09-10 → true 2026-09-13T19:40:01Z (retro: the writing commit `eb72be5f`; `docs/build/runs/P21.5.md` line 23: "Environment clock read 2026-09-13; chain date for this re-run = 2026-09-10"). Register rec 1022.
- **Harness and model (B7 §3 S4).** The disposition was written in the Devin CLI session `polydactyl-author` with model `claude-opus-4-8-medium` (retro: B7 §1–§3). It applied the pre-recorded GL-GATE-02 answer, not an answer given at this gate's pause. The annotation of the restored GATE DECISIONS block in `docs/build/LEDGER.md` (SEED-06) classes this gate's restored entry R39 as clock-false, delegated and a counsel-gate answer given without counsel.
## Annotations (append-only)

- **2026-10-04 — P34.27 (B2; grandfathered readout):** this readout
  predates the guard-sentence convention; the sentence is appended,
  never retrofitted into the record — *An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval.*
  The `Status:` line is not edited.
