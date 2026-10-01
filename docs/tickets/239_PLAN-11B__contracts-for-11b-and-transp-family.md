<!-- Kind: skeleton. Generated 2026-10-01 by docs/build/planning/2026-09-30-next-phase/tools/s13/gen_t3.py (SEED-13a, Round-11 Stage B T3) from data/round11_plan.csv row 239; planning is not execution evidence. -->
# PLAN-11B — decompose-spec mode=extend — full 11B contracts from the ratified PLAN rows + SIG-TRANSP family append

- **Sequence:** 239 of 510 · **Phase:** Round 11 / P34 (sub-round 11A) · **Kind:** skeleton
- **Row kind (manifest):** plan
- **Harness:** devin-desktop/swe-2-high/subagent
- **base_branch:** current checkout
- **Depends on:** P34.33
- **Gate status (GATE-P answer as recorded in the plan row):** none (plan only; rows only from the ratified plan, OM-03)
- **OM-20 status:** not an OM-20 row
- **Live stage:** none
- **Live window (plan `window_constraints`):** during the 10-06 -> 10-13 AR-3 freeze (hosted legs idle)
- **Live legs:** none (leg runs: 0)
- **Est. runs:** 7.0
- **Completed by:** SEED-13c
- **Catalog:** NEW (S4c) · plan §8.5; §6.2 (SIG-TRANSP)
- **Plan row notes:** `docs/build/planning/2026-09-30-next-phase/data/round11_plan.csv` row 239 (`notes` column)
- **Carried in at T3:** SEED-12a: append the SIG-TRANSP family to spec §56.8's plan and register its prefix in §0.3 (append-only `spec_src` change, rebuilt by BUILD.sh).
- **Carried in at T3:** SEED-12a owners to re-confirm when writing the 11B contracts (T3 confirmed them at skeleton level): SIG-SEC-008 → P35.1a/b, SIG-SEC-009 → P35.4, SIG-CONF-010 → P35.60.
- **Carried in at T3:** Plan §8.1 re-split rule: four 11B rows already look oversized (P35.1b, P35.61, P35.63, P36.12); if the sizing review pushes 11B past 85 engineering rows or 75 runs, add GATE-G4b at the Wave-B activation boundary (after row 290, where the manifest already has a banner boundary) by `decompose-spec mode=extend`.

> Skeleton only — the full contract is written by Stage-B unit **SEED-13c** (plan Appendix A T3: full contracts for the 60 11A rows, token-counted against the 256k window) before GATE-B. Do not implement this file until then; it carries no run line. The rewrite keeps this file name (the manifest row binds it).

## Scope (one line)
PLAN-11B: decompose-spec mode=extend — full 11B contracts from the ratified PLAN rows + SIG-TRANSP family append

## Spec §§
- None cited by the plan row or catalog; the contract author cites the sections (plan §8.5; §6.2 (SIG-TRANSP)).

## REQ coverage
- None named yet; the contract author maps the row's scope to requirement ids.
