<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# WAVE_B_RUNBOOK — P36.12 Wave-B activation (I8 §7.2–7.8; OM-19/OM-20)

*The scripted runbook for the Round-11 Tier-1 ingestion wave. The
machinery — `ops/src/ops/wave_b.py` (`sig.wave-b-gate/1` +
`sig.wave-b-plan/1`), the `ops/gcp/wave-b.sh` driver, the
`vocab_enforcement_count` Sqitch change and
`docs/build/reports/WAVE_B_FLIP_LIST.md` — is engineered and
fixture-tested; **all eleven legs stay queued** until the window opens
under the recorded verbatim ING-GO-B.*

## Contract (ticket 290)

- **Window:** 2026-10-26 → 2026-11-05, 14:00–20:00Z each day (future-ok:
  scheduled: contract window) — no weekday restriction; one family per
  day paces the wave (ACQ-11 + ACQ-15 may share a day). Production
  writes only inside it, under ING-GO-B (GATE-G4 §3 — "Window + flips
  at open"; the verbatim go recorded 2026-10-15T15:26Z in GATE
  DECISIONS): *"ING-GO-B: go — Wave B legs ACQ-08…ACQ-15 + the Flock
  probe may run inside the 2026-10-26→11-05 window; I execute the flips
  per OP-26"*.
- **One-shot authorisation:** a re-entry after a close re-collects
  ING-GO-B verbatim — it is never a standing go. The gate requires the
  recorded text **byte-exact**; a paraphrase is a refusal.
- **Exclusions (fail closed):** nothing inside an AR-3 freeze (the
  11-06 → 11-13 freeze follows the window), the daily 03:00–06:30Z band,
  or a cut day; at most one new manual job at a time; never concurrent
  with `sig-materialize` or a G2 step 1–3 slot; never with the peel-on
  first fire 2026-10-29T12:00Z (a leg that day records the fire cleared
  before it runs).
- **The OP-26 flip list (HG-03)** is `docs/build/reports/WAVE_B_FLIP_LIST.md`
  — 96 flagged rows + widen-target context. The flips are the
  operator's execution (a signed commit or GATE DECISIONS row naming
  each source id); until a family's flips land its leg stays queued and
  is reported, never silently skipped. This row flips nothing itself.
- **Legs (in order — a missed leg is reported, never silently skipped;
  legs whose go is held run even while the chain waits, OM-19):**
  1. **L0 — wave opening:** OM-14 pre-state → AR-2 backup `SUCCESSFUL`
     → `roll-jobs --record` on one pinned digest →
     `scheduled-ops.sh --apply --paused` creates the seven `r11-*` batch
     jobs → the hosted `vocab_*` registration of `enforcement_count`
     (operator-run) → the complete flip list handed to the operator.
  2. **L1–L8 — family days** ACQ-08…ACQ-15: the day's flips recorded →
     manual first runs one source at a time → per-source I8 §7.7
     verification → `+0` re-runs (`claims_added == 0`).
  3. **L9 — Flock probe (P36.74, WV-10):** the probe-only run over the
     committed 917-portal set; `sig.probe-run/1` lands every
     served|refused outcome + kind. Expected yield ≈ 0 is a recorded
     outcome.
  4. **L10 — closing:** `sig-materialize` → coverage delta vs the
     pre-wave snapshot → resume the seven paused triggers; each batch's
     next fire is computed and recorded at resume.

## Machinery

| artifact | role |
|---|---|
| `sig-ops wave-b-plan [--json]` | the deterministic `sig.wave-b-plan/1` step list (~326 steps) — every step admission-gated, operator-run steps marked |
| `sig-ops wave-b-gate --inputs <json>` | `sig.wave-b-gate/1` verdict over **recorded** inputs; `action: admit` before a leg's first mutation, `action: close` before it is recorded green; exit `0` go / `42` no-go (queued, never silent) / `2` usage |
| `ops/gcp/wave-b.sh --check` | plan-only print; no ADC, no network, exit `0` |
| `ops/gcp/wave-b.sh --apply --leg <L0…L10> --inputs <json>` | gates then executes the named leg's admit-phase steps; `action=close` gates the recorded evidence only |
| `db/deploy|revert|verify/vocab_enforcement_count.sql` | the INSERT-only hosted registration of `enforcement_count` — the L0 operator-run step |
| `docs/build/reports/WAVE_B_FLIP_LIST.md` | the complete operator-facing OP-26 list with per-family confirmation fields |

## Gate criteria (each refuse-on-fail)

`go` (verbatim ING-GO-B byte-exact + `date -u` recorded_at) · `window`
(supplied `now` in-window, 14:00–20:00Z) · `exclusions` (no
materialize/G2/cut-day active; peel-on fire recorded cleared on
10-29) · `order` (`completed` {leg,day} records cover every earlier leg
— green or held-reported; days non-decreasing; the leg not already
green) · `pacing` (family legs one day each; only L4+L8 may share) ·
`scope` (`run_set` == the leg's declared set exactly; `doj_ctas_awards`
and the tribal S8 lane never) · `flips` (family legs: every gated
source in the leg's recorded OP-26 flips + the family confirmation
present; widen hosts ride existing flips) · `serialize` (no manual run
in flight) · `prestate`/`backup` (L0: OM-14 capture + AR-2 `SUCCESSFUL`)
· `vocab_gate` (L3: `enforcement_count` registered+verified — even when
L0 recorded it) · close-only: `roll`/`jobs`/`vocab`/`handoff` (L0) ·
`runs`/`plus0`/`evidence` (family legs: ok run rows, zero-claim runs
carry `empty_run_notes`, `+0` proves idempotence, `changed_count`
recorded) · `probe` (L9: `sig.probe-run/1` covers all 917, kinds
reconcile) · `closing`/`coverage`/`resume` (L10: materialize ran, delta
recorded, all seven triggers resumed, next-fires == the computed values,
the four pre-11-20 fires carry FEA-15 dispositions).

## Leg L0 — step order (10-26, wave open)

1. **Pre-state (OM-14):** per-source job + trigger JSON (`gcloud run
   jobs describe`, `gcloud scheduler jobs list`), `sources.toml`
   sha256, `uv run sig-ops cadence --check` green — recorded under the
   leg's prestate dir.
2. **AR-2:** `gcloud sql backups create --instance $SIG_SQL_INSTANCE` →
   record the newest backup `SUCCESSFUL`.
3. **Roll:** `SIG_JOB_IMAGE=<pinned sha256 digest> uv run sig-ops
   roll-jobs --record` — one digest across the fleet (ADR-111);
   before/after recorded.
4. **Paused create:** `ops/gcp/scheduled-ops.sh --apply --paused` —
   creates `r11-layers-01/02`, `r11-ate-01`, `r11-procurement-01`,
   `r11-disclosures-01/02`, `r11-documents-01` jobs + triggers, all
   paused. cadence.toml ships inside the image (G1 NEW-10): the rows
   ride the rolled digest.
5. **Hosted vocabulary (OPERATOR-RUN — never the driver's):**
   `sqitch deploy vocab_enforcement_count` against the hosted spine,
   then `sqitch verify`. INSERT-only (one `vocab_predicate` row + its
   20-genre `directness_matrix` row). Must land before L3's first
   ATE-family emit.
6. **Hand-off:** the complete `WAVE_B_FLIP_LIST.md` to the operator;
   the OP-26 execution is recorded per family — never performed here.

## Legs L1–L8 — family-day shape

Each day, in order (`admit` gate → steps → `close` gate):

1. **Flips recorded:** the gate inputs' `flips[leg]` names the family's
   executed flips + the OP-26 record ref. Absent → the leg queues,
   reported.
2. **Manual first runs, one at a time, verified between:**
   `gcloud run jobs execute <job> --args
   scheduled-ingest,--source,<id>,--sink,pg --wait`. Batch members run
   on the family batch job; the six registered `ccops_*` and the probe
   run on `sig-ingest-r11-documents-01`; widen executions on the
   existing jobs (`sig-ingest-camreg-batch-02` for Denver HALO +
   Chicago aggregates, `sig-ingest-camreg-batch-06` for Seattle CCTV,
   `sig-ingest-openstates` for the pinned bill queries). After each:
   latest execution read + the `gs://…-sig-restricted/ops/runs/<source>/`
   run row — `ok`, captures landed bytes, claims recorded, per-source
   I8 §7.7 checks (`sig-ops wave-verify`). A failed verify stops the
   leg and is reported. A zero-claim first run carries a recorded
   `empty_run_notes` reason.
3. **`+0` re-runs:** each run source re-executed immediately; each run
   row must read `claims_added == 0` on unchanged inputs.
4. **Record:** the family-day report — run rows, `changed_count`,
   §7.7 verifications, `+0` diffs — lands in `docs/build/runs/P36.12.md`.

## Leg L9 — the Flock probe

`gcloud run jobs execute sig-ingest-r11-documents-01 --args
scheduled-ingest,--source,flock_transparency_portals,--sink,pg --wait`
— one polite request per committed portal (917; Eyes on Flock snapshot
2026-09-23T10:15:16.751Z), under the project UA (P35.38a), robots per
GL-GATE-08 on every host, stop-and-record on any challenge (WV-10 /
ADR-188). The `sig.probe-run/1` record lands: every portal
served|refused + refusal kind; served = 0 is an honest recorded
outcome, never a failure. No `+0` re-probe (the record is the
evidence).

## Leg L10 — closing

1. **`sig-materialize`** — manual run after the last first run and
   outside ingest runs; reconcile's sharing-edge build adds
   `sharing_partner` where WA AGO/statute claims name partners.
2. **Coverage delta** — `sig-ops coverage-delta` against the pre-wave
   snapshot (P35.6, I8 §7.7), recorded.
3. **Resume** — `gcloud scheduler jobs resume` for the seven
   `sig-sched-r11-*` triggers; each batch's next fire is computed and
   recorded at resume against FEA-15 ("new monthly batch crons set to
   fire after 11-20"): the dom-16…19 crons land 2026-11-16…19T07:17Z —
   inside Wave C's 11-16→11-20 pause window — so each carries a
   recorded disposition (surfaced in the run ledger, never silently
   accepted); the dom-21/22/23 crons land after 11-20 as designed.

## Rollback / forward-fix (append-only posture)

- **Image:** re-point the previous digest from the roll record.
- **Job/trigger:** re-pause; deletion only in a ticket-scoped live
  stage.
- **Source:** a new dated rights decision sets
  `ingestion_permitted=false` — the next run exits 3; claims stay
  (append-only); the next release withdraws.
- **Vocabulary:** `sqitch revert vocab_enforcement_count` removes the
  seeded rows only where no live row references them — a predicate
  claims already resolve through stays (recorded registry history).
- **Anomalous data:** forward-fix claims; corruption → PITR clone,
  never in-place restore/deletion.

## Deferred / excluded (recorded, not implicit)

- `doj_ctas_awards` (AP-T2-093) — not tribal; `D-R11-LATER-09` stays
  OPEN; the gate refuses it in any run set.
- Tribal S8 — the ADR-185 screened lane landed at P35.11 (Wave A);
  Wave B's flip list carries no tribal candidate;
  `CG-LATER-tribal-data-governance-rule-i7-new-6` stays OPEN.
- `D-R11-OSMUID-1` — handed to P37.1; no OSM connector change here.
- Outreach (ADR-171, `D-R11-LATER-04`) — the Stage-0 set owed and unmet
  at launch; no outside contact is made.
- Public surfacing — Wave-B data publishes in P36.72b's Class S
  release (no separate Wave-B release cut); nothing public ships here.

## Re-run prompt

`implement-spec spec=docs/tickets/290_P36.12__wave-b-activation.md
live_verification=true` — each leg needs the recorded ING-GO-B, the
window, its own gate inputs and its family's executed OP-26 flips; the
flip list is the operator's, never this row's.
