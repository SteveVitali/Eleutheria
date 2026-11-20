<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.2 Wave-C — L1 leg report (`P37.2-l1-pregrow-disk`) — GREEN

Run: `r11/P37.2-live-1`, runner `devin-desktop/swe-2-high/subagent`,
`SIG_GCP_PROJECT=zeta-medley-508121-u7`, ADC `14stevevitali@gmail.com`.

## Authority

- ING-GO-C `"Approve ING-GO-C (rec.)"` recorded 2026-10-25T18:40Z
  (GATE-G5 §3 GATE DECISIONS, byte-exact gate input).
- Post-gate unblock `2026-11-20T00:15Z | GATE-ACCEPT-R11` — `"Run them
  now"` (signed commit `99018e1b`): L1…L5 in order under their own
  `go` cells; l2's in-ticket tier-bump go NOT pre-authorised.
- `return_pass.toml` `P37.2-l1-pregrow-disk` `go` cell:
  `verbatim-go: ING-GO-C (byte-exact) + sig-ops wave-c-gate --inputs
  <json> admit go (exit 0)`.

## Commands and receipts (`date -u` stamps)

| step | command | stamp (UTC) | result |
|---|---|---|---|
| OM-14 pre-state | `gcloud sql instances describe sig-pg` + 3 job describes + scheduler list + file sha256 + `sig-ops cadence --check` → `prestate/` | captured 04:05:11 | `dataDiskSizeGb=15`, `storageAutoResizeLimit=0`, tier `db-custom-1-3840`; cadence check exit 0 |
| admit probe (in-band) | `sig-ops wave-c-gate --inputs inputs-l1-admit.json` (`now=04:05:30`) | 04:05 | **exit 42 NO-GO** — `window` (never-band 03:00–06:30Z active) + `backup` (none yet); every other criterion green → waited out the band, never ran inside it (`gates/l1-admit-2026-11-20T0405Z.json`) |
| AR-2 on-demand backup | `gcloud sql backups create --instance sig-pg --async` → op `093bdc45-3e02-46aa-a5cb-adaf00000032` | issued 06:31:12, DONE 06:32:43 | backup `1795156272127` ON_DEMAND **SUCCESSFUL** (windowStart 06:31:12.127) |
| admit | `sig-ops wave-c-gate --inputs inputs-l1-admit.json` (`now=06:33:03`) | 06:33 | **exit 0 GO** — all 11 criteria green (`gates/l1-admit-2026-11-20T0633Z.json`) |
| driver | `bash ops/gcp/wave-c.sh --apply --leg L1 --inputs inputs-l1-admit.json` | start 06:33:09 | re-gated admit green; ran L1.1–L1.5 |
| L1.2 backup (driver) | `gcloud sql backups create` → op `78c8589d-3c4a-4d33-80f2-412800000032` | issued 06:33:15, DONE 06:34:47 | backup `1795156395816` ON_DEMAND **SUCCESSFUL** (the driver's own restore-point take, in addition to the admit-time `1795156272127`) |
| L1.3 disk pre-grow | `gcloud sql instances patch sig-pg --storage-size=25 --async` → op `9566e478-6d77-4fba-b24b-cd8200000032` | issued 06:34:54, DONE 06:35:46 | 15 → 25 GB (one-way; first grow, not a re-grow) |
| L1.4 autoresize limit | `gcloud sql instances patch sig-pg --storage-auto-increase-limit=40 --async` → op `f3166b78-33cf-4696-9b63-5f4e00000032` | issued 06:35:50, DONE 06:36:23 | 0 → 40 GB cap (Q-23 B-11 posture) |
| L1.5 read-back | `gcloud sql instances describe sig-pg --format='value(settings.dataDiskSizeGb,settings.storageAutoResizeLimit,settings.tier)'` | 06:36:4x | `25  40  db-custom-1-3840` — independent re-read 06:36:49: `25 40 db-custom-1-3840 RUNNABLE` |
| close gate | `sig-ops wave-c-gate --inputs inputs-l1-close.json` (`now=06:36:53`) | 06:36 | **exit 0 GO** — `disk: dataDiskSizeGb=25 ≥ 25 and storageAutoResizeLimit=40 == 40 recorded` (`gates/l1-close-2026-11-20T0636Z.json`) |
| driver close | `wave-c.sh --apply --leg L1 --inputs inputs-l1-close.json` | 06:37 | `wave-c.sh: leg L1 close gated green` |

Leg elapsed: first admit probe 04:05 → driver start 06:33:09 → close
gated green 06:37 (the wait 04:05→06:31 was the excluded never-band,
recorded — never run inside it).

## Verdict

**L1 GREEN (live-executed).** Restore points: backups `1795156272127`
+ `1795156395816` (both ON_DEMAND SUCCESSFUL); the disk grow is
one-way by design (recorded, never blindly re-grown); the tier stays
`db-custom-1-3840` until l2's own go.

## Environment note

macOS lacks GNU `sha256sum`; a compatible shim
(`/tmp/sig-wavec-bin/sha256sum` → `shasum -a 256`, byte-identical
output format) was placed on PATH for the driver only — the committed
`ops/gcp/wave-c.sh` is unmodified.
