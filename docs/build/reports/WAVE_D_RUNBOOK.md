<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# WAVE_D_RUNBOOK — P37.54 Wave-D activation (R11-ACQ-27, I8 §7.2–7.8; OM-19/OM-20)

*The scripted runbook for the Round-11 Tier-2 ingestion wave — "as ACQ-16,
for the Tier-2 families that landed". The machinery —
`ops/src/ops/wave_d.py` (`sig.wave-d-gate/1` + `sig.wave-d-plan/1`), the
`ops/gcp/wave-d.sh` driver and
`docs/build/reports/WAVE_D_FLIP_LIST.md` — is engineered and
fixture-tested; **all twelve legs stay queued `prepared_not_executed`**
until the windows open under the recorded ING-GO-D and the operator's
executed OP-26 flips. This dispatch executed no leg, flipped no source,
fetched no host and ticked no gate.*

## Contract (ticket 481)

- **Windows:** `window 11-23 -> 12-04` then `window 12-14 -> 12-18`,
  14:00–20:00Z UTC each day (future-ok: scheduled: contract windows) —
  the AR-3 freeze 12-06→12-13 separates them. One family per day paces
  the wave; L0 opens and L11 closes and may share a day with a family
  leg. A leg held in the first window (flips not executed, a failed
  verify) runs in the second — reported, never silently skipped (OM-19)
  — and its sources ship in the 2027-01-15 cadence cut, never the 12-15
  cut. The 12-15 14:00Z release cut inside the second window is
  excluded: no leg runs it.
- **Authority:** ING-GO-D — the GATE-G6 GATE DECISIONS answer recorded
  verbatim 2026-11-05T15:20Z on the operator-signed commit `b91f8e58`:
  *"Approve ING-GO-D + flip list (rec.)"*. The §3 Wave-D HG-03 flip-list
  line pre-approves the plan-cell's verbatim set (N1–N21, ACQ-23a/b,
  DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08) for flip
  when its rights review completes; the flips stay operator-executed
  (one signed commit or a signed GATE DECISIONS row naming each source
  id); ids resolving non-clear licences keep their per-source gate. The
  gate requires the recorded answer **byte-exact**; a paraphrase is a
  refusal; silence is never consent.
- **The OP-26 flip list (HG-03)** is
  `docs/build/reports/WAVE_D_FLIP_LIST.md` — **146 flagged rows** (140
  tier-2 batch members + 6 seatless gated sources) + 8 dossier-seat
  context rows. The flips are the operator's execution; until a
  family's flips land its leg stays queued and is reported. This row
  flips nothing itself.
- **Legs (in order — a missed leg is reported, never silently skipped):**
  1. **L0 — wave opening** (window 1): OM-14 pre-state → AR-2 backup
     `SUCCESSFUL` → `roll-jobs --record` on one pinned digest →
     `scheduled-ops.sh --apply --paused` creates the three `r11-tier2-*`
     batch jobs → the complete flip list handed to the operator.
  2. **L1–L9 — family days** in ticket order: ACQ-19 (P37.47, 30 seats),
     ACQ-20 (P37.48, 13), ACQ-21 (P37.49, 8), ACQ-22 (P37.50, 10),
     ACQ-23a (P37.69a, 36), ACQ-23b (P37.69b, 4), ACQ-24 (P37.51, 8),
     ACQ-25 (P37.52, 8), ACQ-26 (P37.53, 23): the day's flips recorded →
     manual first runs one source at a time on the member's batch job →
     per-source I8 §7.7 verification → `+0` re-runs.
  3. **L10 — the S6 extras family day** (P36.76/77/78 + RB-06b):
     `axon_connect`, `documentcloud`, `muckrock_public`, `sourcewell`,
     `omnia_partners`, `camreg_bellevue_wa` — six seatless gated sources
     run single-source on `sig-ingest-r11-tier2-01`. Targets window 1 so
     the sources ship in the next cadence cut.
  4. **L11 — closing:** `sig-materialize` → coverage delta vs the
     pre-wave snapshot → resume the three paused tier-2 schedules
     (cadence `state` paused→enabled + declaration republish — the
     due-dispatcher shape, never a per-source trigger resume) →
     next-fires computed and recorded (2026-12-25/26/27T07:37Z —
     future-ok: scheduled: dom crons; all three land after the 12-15
     cut).

## Machinery

| artifact | role |
|---|---|
| `sig-ops wave-d-plan [--json]` | the deterministic `sig.wave-d-plan/1` step list (467 steps) — every step admission-gated |
| `sig-ops wave-d-gate --inputs <json>` | `sig.wave-d-gate/1` verdict over **recorded** inputs; `action: admit` before a leg's first mutation, `action: close` before it is recorded green; exit `0` go / `42` no-go (queued, never silent) / `2` usage |
| `ops/gcp/wave-d.sh --check` | plan-only print; no ADC, no network, exit `0` |
| `ops/gcp/wave-d.sh --apply --leg <L0…L11> --inputs <json>` | gates then executes the named leg's admit-phase steps; `action=close` gates the recorded evidence only |
| `docs/build/reports/WAVE_D_FLIP_LIST.md` | the complete operator-facing OP-26 list with per-family confirmation fields |

## Gate criteria (each refuse-on-fail)

`go` (the recorded ING-GO-D answer byte-exact — `"Approve ING-GO-D +
flip list (rec.)"`, GATE-G6 `b91f8e58` — + `date -u` recorded_at) ·
`window` (supplied `now` inside either window's span **and** the
14:00–20:00Z band, never on the 12-15 cut day; evaluated on the
supplied instant, never the wall clock) · `exclusions` (no
materialize/G2/cut-day active) · `order` (`completed` {leg,day} records
cover every earlier leg — green or held-reported; completed days are
admissible window dates, non-decreasing; the leg not already green) ·
`pacing` (family legs one day each; only L0's opening and L11's closing
may share a family day) · `scope` (`run_set` == the leg's declared set
exactly; the eight P37.16a/b dossier seats, `doj_ctas_awards` and the
tribal S8 lane never) · `flips` (family legs: every gated source in the
leg's recorded OP-26 flips + the family confirmation present) ·
`serialize` (no manual run in flight) · `prestate`/`backup` (L0) ·
close-only: `roll`/`jobs`/`handoff` (L0: pinned-digest roll recorded,
the three jobs created-paused, the complete 146-row flip list handed
off) · `runs`/`plus0`/`evidence` (family legs: ok run rows, zero-claim
runs carry `empty_run_notes`, `+0` proves idempotence, `changed_count`
recorded) · `closing`/`coverage`/`resume` (L11: materialize ran, delta
recorded, all three cadence rows enabled + declaration republished,
next-fires == the computed values).

## Recorded caveats

- **`payee:` stays unmapped** — P37.53's run ledger records that
  P37.48's `payee:` prefix was never registered in
  `subject_entity_types.toml`; the ACQ-20 payment lanes' `payee:`
  subjects quarantine `unknown_subject_scheme` fail-closed on a live emit — never
  a defect, a recorded outcome; the typing decision is
  that family's, never guessed by this row.
- **Enumerated seats** — `D-P37.69a-1`, `D-P37.69a-2`, `D-P37.69b-1`
  hold seats `[[enumerated]]` pending endpoint preflights; D-P37.69b-1's
  owner names this wave's flip-window census under ING-GO-D. An
  enumerated seat's run is a recorded bounded outcome.
- **Zero-claim runs** carry a recorded `empty_run_notes` reason — a
  gated seat's loader refusal, an empty serve or a quarantine is an
  honest recorded outcome, never silently accepted.
- **Seatless executions** — the six L10 sources carry no batch seat;
  they run single-source on `sig-ingest-r11-tier2-01` (the Wave-B
  seatless convention); their next cadence fire is the batch's own.

## Rollback / forward-fix (append-only posture)

- **Image:** re-point the previous digest from the roll record.
- **Job/cadence:** re-pause (cadence `state` → `paused` + republish);
  deletion only in a ticket-scoped live stage — never this row.
- **Source:** a new dated rights decision sets
  `ingestion_permitted=false` — the next run exits 3; claims stay
  (append-only); the next release withdraws.
- **Anomalous data:** forward-fix claims; corruption → PITR clone,
  never in-place restore/deletion.

## Deferred / excluded (recorded, not implicit)

- The eight **P37.16a/b dossier-capture seats** — batch members whose
  flips and captures ride those rows' own in-ticket operator go (the
  Part VIII-screened lane is never pre-authorised); the gate refuses
  them in any Wave-D run set.
- `doj_ctas_awards` (AP-T2-093) — `D-R11-LATER-09` stays OPEN; the gate
  refuses it.
- Tribal S8 — the ADR-185 screened lane landed at P35.11 (Wave A).
- The gated **keyed-API rows** (P37.11/P37.12/P37.70 `D-*-1`) ride
  their own OM-20 windows — never this wave's.
- Outreach (`D-R11-LATER-04`) — no outside contact is made by the wave.
- **Second-window shipping** — sources whose legs land in window 2
  ship in the 2027-01-15 cadence cut, never P37.65's 12-15 cut.

## Re-run prompt

`implement-spec spec=docs/tickets/481_P37.54__wave-d-activation.md
live_verification=true` — each leg needs the recorded ING-GO-D
(GATE-G6 `b91f8e58`), its window, its own gate inputs and its family's
executed OP-26 flips; the flip list is the operator's, never this
row's. The two windowed legs are recorded as RETURN PASS `kind: leg`
obligations: `window 11-23 -> 12-04` and `window 12-14 -> 12-18`.
