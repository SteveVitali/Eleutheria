# Run ledger — OPS-GAP-RP-1 — execute the operator's GAP-RP-1 disposition (`D-P38.2-1`, disposition b)

- **Harness:** devin-desktop/swe-2-high/subagent
- **Scope:** records-only execution of an operator-recorded disposition — no
  ticket contract, no code, no hosted act, no `live` leg claimed. This run
  adds committed RETURN PASS map homes; it runs none of the legs.
- **Operator authorisation (verbatim):** LEDGER `## GATE DECISIONS` row
  `2026-11-20T00:15Z | GATE-ACCEPT-R11 | post-gate unblock — GAP-RP-1
  disposition (`D-P38.2-1`)` — answer **"Fresh go for the legs"**
  (AskUserQuestion selection, Devin Desktop orchestration session,
  2026-11-20), signed commit `99018e1b`: *"disposition (b) from the
  D-P38.2-1 packet line: real `[[row.legs]]` RETURN PASS entries are created
  for the four named legs under this fresh verbatim listing — each entry
  records this GATE DECISIONS row as its `go` plus its own
  window/preconditions (ADC + `SIG_GCP_PROJECT`, AR-2/AR-3 bands);
  `D-P38.2-1` closes once all four have a map home and `return_pass.py
  check` stays green."*
- **Base / branch:** `99e79e5b` (chain tip) → `r11/ops-gap-rp-1-returnpass`
  (PR base `r11/P38.3c-round11-integration-plan-2`).
- **Started:** 2026-11-20 (`date -u`)
- **Closed:** 2026-11-20 (`date -u` at closeout — see §Heads)

## What this run lands

1. **Four `[[row.legs]]` homes in
   `docs/build/tools/record_policy/return_pass.toml`** — one `kind = "leg"`
   `[[row]]` per landed ticket that owes the leg (the T5 γ keying), each
   `go` citing the 2026-11-20T00:15Z GATE DECISIONS row as the fresh
   verbatim listing, each carrying the leg's own window/preconditions:

   | row key | leg id | window / preconditions recorded |
   |---|---|---|
   | `P35.22` | `P35.22-truthful-claim-identity-live` | next scheduled runs of affected sources (camera-registry days-6–13 batches inside the surface); hosted verify + `/status/` + parity acts under ADC + `SIG_GCP_PROJECT` inside AR-3+AR-2; never inside the AR-3 freeze 12-06→12-13T12:00Z |
   | `P35.27` | `P35.27-resolver-input-live` | AR-3+AR-2 (AR-3 band 14:00-20:00Z weekdays), AR-2 restore point first; rides `live:P35.26` (the P35.26 row's leg lists P35.27 as its live dependant); never inside the freeze |
   | `P35.32` | `P35.32-ingest-run-report-live` | AR-3+AR-2 (preferred 14:00-20:00Z weekdays, never 03:00-06:30Z), AR-2 restore point first; never inside the freeze |
   | `P35.46` | `P35.46-er-run-live` | AR-3+AR-2 (AR-3 band 14:00-20:00Z weekdays), AR-2 restore point → dry-run census → `--apply` → GQ-23/GQ-25 → read-back → `+0`; never concurrent with `sig-materialize`; never inside the freeze |

   **Naming honesty:** the records name the fourth leg only as "the P35.46
   GATE-G4 §4-named ER-run leg" (PHASE LOG 2026-10-22 "ER leg QUEUED";
   `D-P38.2-1`; the GATE-ACCEPT-R11 packet §1e) — no `P35.46-*` leg id was
   ever committed. `P35.46-er-run-live` is minted at this listing under the
   sibling `-live` convention and the row's `gates_cell` says so verbatim.

2. **Regenerated region:** `return_pass.py generate` rewrote the LEDGER's
   `### RETURN PASS — current` region + the CURRENT STATE `returnPass:` key
   (93 rows · 92 key ids — P35.22/P35.27/P35.32/P35.46 now carry ids).
   `return_pass.py check`: **OK — evaluated 281 obligations (196 owed,
   each in exactly one home) · 93 table rows · returnPass 92 ids · region
   byte-identical.**

3. **`D-P38.2-1` → DONE:** `obligation_events` appended
   `D-P38.2-1:e1` (OPEN→DONE, `WORKTREE` source stamp — the landing rides
   this commit); the DEFERRALS status cell flips `OPEN` → `DONE` with the
   old cell preserved verbatim (the `D-P35.53-1` / `D-P30.1-2` precedent).

## Records touched

- `docs/build/tools/record_policy/return_pass.toml` — 4 `[[row]]` +
  4 `[[row.legs]]` appended at tail (the map's commit order).
- `docs/build/LEDGER.md` — generated `### RETURN PASS — current` region +
  `returnPass:` only (the exempt generated surface; nothing else edited).
- `docs/build/reports/obligations/events.jsonl` — `D-P38.2-1:e1` appended.
- `docs/tickets/DEFERRALS.md` — `D-P38.2-1` status cell only.
- `docs/build/runs/OPS-GAP-RP-1.md`, `docs/build/pr/OPS-GAP-RP-1.md` — this
  ledger + the PR body.

## What this run does not do

- Runs no leg. All four stay `QUEUED` — now with map homes and a named go;
  their re-run prompts are the recorded `implement-spec …
  live_verification=true` lines (owner: the OM-19 leg-runner or the
  operator, inside each leg's window).
- Adds no GATE DECISIONS row, touches no readout `Status:` line, flips no
  `ingestion_permitted` — the go record is the operator's own signed row,
  cited, never authored here (OP-25/Gotcha 9).
- Decides nothing the operator did not already decide — the disposition is
  verbatim execution of `99018e1b`'s row.

## Guards

| check | result |
|---|---|
| `return_pass.py check` | OK — 281 obligations, 196 owed, each in exactly one home · 93 rows · returnPass 92 ids · region byte-identical |
| `obligation_events.py check` | green (see commit record) |
| `memory_guard all --staged` | 0 violations (see commit record) |
| `scripts/docs/check-build-memory.sh .` | clean (see commit record) |

## Heads / CI

- Head `45704317` · PR **#542** (base
  `r11/P38.3c-round11-integration-plan-2`) — opened 2026-11-20.
- **Attempt 1 — `ci: fail #542@4570431`** (run 44672810298): security 45s
  · docs 2m33s · composed 4m31s · python 20m28s — all green; `web` failed
  at 1h1m34s on the `map` **dark-1440** visual cell
  (`toHaveScreenshot(map--dark-1440.png)` — **96,179 px (0.08) differ**):
  the byte-identical adjudicated `VISUAL-MAP-DARK-1` env-flake signature
  (the #524/#532 count; unlisted in `ci_flakes.toml` — the allow-list call
  is the operator's; this diff touches zero `web/` bytes). `failure` +
  `rerun-requested` rows appended to `docs/build/reports/ci/flake_log.csv`;
  the one B-15 same-head `gh run rerun --failed` issued 05:20Z
  (attempt 2).
- **Attempt 2:** in flight at this commit — the landing verdict row is
  recorded in `flake_log.csv`; the `ci:` verdict line lands at the next
  record entry.
