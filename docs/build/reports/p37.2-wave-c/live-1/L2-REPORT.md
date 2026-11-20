<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.2 Wave-C — L2 leg report (`P37.2-l2-tier-bump`) — GREEN

Run: `r11/P37.2-live-1`, runner `devin-desktop/swe-2-high/subagent`,
`SIG_GCP_PROJECT=zeta-medley-508121-u7`, ADC `14stevevitali@gmail.com`.

## Authority

- ING-GO-C `"Approve ING-GO-C (rec.)"` recorded 2026-10-25T18:40Z
  (GATE-G5 §3 GATE DECISIONS, byte-exact gate input) — the wave's go,
  never the tier's.
- Post-gate unblock `2026-11-20T00:15Z | GATE-ACCEPT-R11` — `"Run them
  now"` (signed commit `99018e1b`).
- **The in-ticket tier go:** GATE DECISIONS row
  `2026-11-20T06:45Z | GATE-ACCEPT-R11` — verbatim
  `"Bump the tier"` (signed commit `d3c72f51`). The same commit records
  `"Acknowledged"` for the structural consequence that l5 queues past
  the strict window after l4's 24 h soak. ING-GO-C was never used as
  the tier go — the gate refuses byte-equality against it.
- `return_pass.toml` `P37.2-l2-tier-bump` `go` cell: the operator's
  verbatim in-ticket go + `sig-ops wave-c-gate --inputs <json>` admit
  go (exit 0).

## Commands and receipts (`date -u` stamps)

| step | command | stamp (UTC) | result |
|---|---|---|---|
| admit | `sig-ops wave-c-gate --inputs inputs-l2-admit.json` (`now=2026-11-20T08:32:41Z`) | 08:32 | **exit 0 GO** — L2 next after green L1; inside window; ING-GO-C byte-exact; Q-23 answered; review green; exclusions false; no active manual run; `run_set` empty; FEA-15 pause held; tier go `"Bump the tier"` recorded 2026-11-20T06:45Z (`gates/l2-admit-2026-11-20T0832Z.json`) |
| driver | `bash ops/gcp/wave-c.sh --apply --leg L2 --inputs inputs-l2-admit.json` | start 08:32:48 | re-gated admit green; ran L2.1–L2.3 |
| pre-state read | `gcloud sql instances describe sig-pg` | 08:32 | `RUNNABLE db-custom-1-3840 25 40` (`prestate-l2/instance-readback.txt`) |
| L2.2 tier patch | `gcloud sql instances patch sig-pg --tier=db-custom-2-7680 --async` → op `59778cf4-9a94-44d6-aa76-872200000032` | issued 08:32:54, DONE 08:37:41 | `db-custom-1-3840` → `db-custom-2-7680` (`poststate-l2/op-59778cf4.json`) — exactly the tier patch, no other production change |
| L2.3 read-back + health | `gcloud sql instances describe` + `curl /health` | 08:37 | tier `db-custom-2-7680` read back; `GET /health` → **HTTP 200** |
| close gate | `sig-ops wave-c-gate --inputs inputs-l2-close.json` (`now=2026-11-20T08:37:55Z`) | 08:37 | **exit 0 GO** — `tier: settings.tier=db-custom-2-7680 recorded — the bump holds`; no failing criteria (`gates/l2-close-2026-11-20T0837Z.json`) |
| driver close | `wave-c.sh --apply --leg L2 --inputs inputs-l2-close.json` | 08:38 | `leg L2 close gated green` |
| post-state re-read | `gcloud sql instances describe` + `curl /health` | 08:44 | `RUNNABLE db-custom-2-7680 25 40`; `/health` → HTTP 200 — the bump persists (`poststate-l2/`) |

Leg elapsed: admit 08:32:41 → patch op DONE 08:37:41 → close gated
green 08:38. The instance restart inside the patch is the recorded
I8 §7.4 risk — `/health` 200 at first read and again at 08:44.

## Verdict

**L2 GREEN (live-executed).** `sig-pg` runs `db-custom-2-7680`;
disk 25 GB / autoresize limit 40 unchanged from L1. The bump is
temporary-only (Q-23): l5's revert to `db-custom-1-3840` is the
recorded queue item — the operator's `"Acknowledged"` (signed
`d3c72f51`, GATE DECISIONS 2026-11-20T06:45Z) already records that l5
cannot fit inside the strict `<2026-11-21T00:00Z` admission boundary
after l4's mandatory 24 h soak, so the revert leg stays queued for a
later, separately reauthorized run.
