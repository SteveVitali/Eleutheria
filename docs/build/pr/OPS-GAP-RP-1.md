# OPS-GAP-RP-1 — execute the operator's GAP-RP-1 disposition: fresh `[[row.legs]]` homes for the four recorded-QUEUED legs (`D-P38.2-1` → DONE)

**Operator authorisation (verbatim):** LEDGER `## GATE DECISIONS` row
`2026-11-20T00:15Z | GATE-ACCEPT-R11 | post-gate unblock — GAP-RP-1
disposition (`D-P38.2-1`)` — answer **"Fresh go for the legs"** (signed
commit `99018e1b`): *"disposition (b) from the D-P38.2-1 packet line: real
`[[row.legs]]` RETURN PASS entries are created for the four named legs
under this fresh verbatim listing — each entry records this GATE
DECISIONS row as its `go` plus its own window/preconditions (ADC +
`SIG_GCP_PROJECT`, AR-2/AR-3 bands); `D-P38.2-1` closes once all four have
a map home and `return_pass.py check` stays green."*

This PR is the recorded execution of that row — records only; no leg runs.

## What lands

- **Four `[[row.legs]]` entries** in
  `docs/build/tools/record_policy/return_pass.toml`, one `kind = "leg"`
  row per landed ticket that owes the leg:
  - `P35.22-truthful-claim-identity-live` (row `P35.22`) — legs L2/L3:
    next scheduled runs mint under the truthful claim identity + the
    `/status/` API-basis notice + the dedup-parity report; window `next
    scheduled runs; camera-registry batches days 6–13`; hosted acts under
    ADC + `SIG_GCP_PROJECT` inside AR-3+AR-2, never inside the AR-3
    freeze 12-06→12-13T12:00Z.
  - `P35.27-resolver-input-live` (row `P35.27`) — rematerialize +
    `/status/` + contradiction-state distribution report; AR-3+AR-2, AR-2
    restore point first; rides `live:P35.26`; never inside the freeze.
  - `P35.32-ingest-run-report-live` (row `P35.32`) — hosted `sqitch
    deploy --verify` of `ingest_run_report` + writer on next run +
    `backfill-run-reports` + `+0` + read-back; AR-3+AR-2 (preferred
    weekday 14:00-20:00Z, never 03:00-06:30Z); never inside the freeze.
  - `P35.46-er-run-live` (row `P35.46`) — the append-only ruleset-v3 ER
    run on the hosted spine (`ops/gcp/er-rerun.sh`); AR-3+AR-2, AR-2
    restore point → dry-run census → `--apply` → GQ-23/GQ-25 → read-back
    → `+0`; never concurrent with `sig-materialize`. **Naming honesty:**
    the records carry only "the P35.46 GATE-G4-named ER-run leg" — no
    `P35.46-*` id existed; the id is minted at this listing and the row's
    gates cell says so.
  - Every `go` cites the 2026-11-20T00:15Z GATE DECISIONS row verbatim
    (`verbatim-go:`) — the fresh listing is the go; nothing pre-authorised
    on silence (OM-20). `live_dependants` is empty for all four — no
    recorded `live:` edge names them.
- **Regenerated RETURN PASS region + `returnPass:`** (the LEDGER's exempt
  generated surface; `return_pass.py generate`). 93 rows · 92 key ids.
- **`D-P38.2-1` → DONE** — event `D-P38.2-1:e1` appended
  (OPEN→DONE, evidence: the GATE DECISIONS row + the map + this run);
  DEFERRALS status cell flips with the old cell preserved verbatim.
- Run ledger `docs/build/runs/OPS-GAP-RP-1.md`.

## Checks

- `return_pass.py check` — **OK — evaluated 281 obligations (196 owed,
  each in exactly one home) · 93 table rows · returnPass 92 ids · region
  byte-identical.**
- `obligation_events.py check` — green.
- `memory_guard all --staged` — 0 violations; `check-build-memory.sh` —
  clean.

## Boundaries

Records-only. No GATE DECISIONS row added (the go is the operator's signed
row, cited — OP-25), no readout `Status:` touched, no
`ingestion_permitted` flip, no hosted/`live` act, no production mutation.
The four legs remain QUEUED for the OM-19 leg-runner/operator inside each
recorded window.

Harness: devin-desktop/swe-2-high/subagent
