# Readout — GATE-G2 (Go-public / GL-GATE-05) — DNS/host cutover + v0.2.0

- **Chain row:** P23.6 · **Kind:** gate marker · **Gate register:** Go-public (operator)
- **Ticket:** `docs/tickets/P23.6__go-public-dns-cutover.md`
- **Dispositioned:** 2026-09-10 by orchestrate-build (operator-deferred per the resume prompt rule 3)

## Verdict: SKIPPED-BY-OPERATOR (deferred — reserved to the human, NOT pre-answered)

Go-public is the operator's explicit final step: the DNS/host cutover and the `v0.2.0` "first public
jurisdiction" tag. It is **not** pre-answered (GL-GATE-05). Per the operator resume prompt it is
recorded SKIPPED → RETURN PASS and the chain continues — it does NOT block the remaining
productionize work (Round 4), which lands to GCP staging/private without a public cutover.

## What would pass it (all required before cutover)
1. A **real** named legal home superseding the GL-GATE-01 interim posture (HG-01 / `D-P21.4-1`).
2. Operating governance live: two reviewer roles + written concurrence + a live takedown/corrections
   contact (HG-11 / `D-P21.4-2`).
3. LIVE.2 green to a GCP staging/private target with a real live fetch (HG-09 tokens + network;
   `D-P21.3-2`, `D-P21.4-3`), `PUBLICATION_CHECKLIST.md` complete, `/terms` + `robots.txt` served,
   officer-naming + publication tiers verified on live data.
4. Counsel review of the interim engineering disposition recommended before real public exposure
   (`D-LEGAL.1-1`).

On Go-public the operator cuts over and bumps `0.2.0`, recording the gate cleared here (verdict flips from SKIPPED to cleared only then).

## Consequence recorded
Kept in LEDGER RETURN PASS (`P23.6 / Go-public`). DEFERRALS rows `D-P21.4-1/2/3`, `D-P21.3-2`,
`D-LEGAL.1-1` remain OPEN — all publication-scoped, so this gate cannot pass while they are open
(DEFERRALS rule 4). Not `blockedOn` (a deferred human milestone is a pause, not a block).
