<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- P34.46 L1 draft — the verbatim go request the operator answers IN-TICKET.
     DRAFT: the rehearsal numbers marked <rehearsal> fill from the fresh-clone
     record (docs/build/logs/restore-drill/drill-*/rehearsal/record.json); the
     slot times fill from the operator's pick inside the window. Nothing here
     is consent — silence is never consent (OM-18); L2 needs the operator's
     verbatim in-ticket go recorded in GATE DECISIONS with `date -u`. -->

# P34.46 — L2 go request (draft; requires verbatim in-ticket go)

The Round-10 schema + API roll, one slot inside the contract window
(weekday 14:00–20:00Z, not before **2026-10-14T14:00Z**, after the
P34.39a 10-10 OSM-replay read-back reports **pass**, operator present).

Quoting the five legs of the slot:

1. `sqitch deploy --verify` of the rehearsed plan tip — plan L44–52
   byte-identical to the base plus the appended tail (incl.
   `@r11-verify-membership`: the D-P34.24b-1 repair that grants the
   deploying `sig` login membership in the NOLOGIN intake roles their
   own verifies SET ROLE) — as rehearsed on
   `sig-pg-drill-20261009t1008z` (deployed plan sha256
   `9ec9511ccc0e80e8db9f6502ead5b5d6a98f0c6e7586e96ed48085cdd0a95c85`,
   deploy exit 0, 141.0 s wall; `sqitch verify` exit 0; clone deleted). `lock_timeout=1200000` ms.
2. Recording the ADR-159 registry auto-allow dispositions —
   `sig-ops disposition record --allow --from <allow-list> --dry-run`
   then `--apply` (INSERT-only; `--decided-by` names the registry rule
   and A-10). P34.26's census found **0 auto_allow_eligible** of 1,559
   flagged — the apply inserts 0 rows unless a re-run census says
   otherwise (re-read at the slot).
3. The `sig-api` roll by digest: build `sig-api:api-<sha12>`, deploy
   `--no-traffic --tag r10`, smoke the tag URL, then
   `update-traffic --to-latest --remove-tags r10`. Rollback target:
   `sig-api@sha256:40a47da8c2cf8f68e84aede7e7e3f9f43a03ed823c83a9924d6535970354b722`
   (the revision live today, `sig-api-00011-wic` — re-confirmed at L1,
   `gcloud run services describe` 2026-10-09).
4. The `/status/` maintenance notice (draft in
   `maintenance-notice-DRAFT.md` — confirmed verbatim before the slot,
   B-2) published through P34.10's path, and the withdrawal of N-7
   after verification.
5. The trigger pause list and its resume — computed at L1 from the
   live scheduler + `ops/cadence.toml`
   (`pause-list-2026-10-09.json`): for the earliest candidate slot
   (10-14 14:00→15:30Z) **zero** spine-writing triggers fire in the
   pause band; the list is recomputed at the chosen slot and resumed
   in reverse order after verification.

## Expected unavailability

Requests that block on the `claim_evidence` ACCESS EXCLUSIVE lock fail
inside `lock_timeout` (20 min ceiling)/statement timeouts. Rehearsed
lock hold **15.927 s** (bound) vs the ≤ 20 min / ≤ 2× 13.844 s
(27.688 s) bound — inside both.
planned slot `<slot start>` → `<planned end>` with a 1 h buffer either
side for the pause band.

## Gates that must hold at the slot (FEA-07, all re-read at L2 start)

- rehearsed lock ≤ 20 min AND ≤ 2× the P34.24b clone measurement
- disk headroom ≥ 2× `claim_evidence` (699,629,568 B post-deploy on the clone →
  ~1.4 GB free required; the 15 GB instance holds ~8.8 GB free)
- `lock_timeout` set for the deploy session
- plan diff vs the rehearsed tip = 0 (else re-rehearse first)
- the P34.39a 10-10 read-back verdict = pass
- AR-2: an on-demand `sig-pg` backup verified SUCCESSFUL first
- the go/no-go checker (`sig-ops roll-gate`) decides `go` on the
  re-read inputs; any refusal stops the leg and asks, never proceeds
