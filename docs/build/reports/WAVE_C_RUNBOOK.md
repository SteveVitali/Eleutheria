<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# WAVE_C_RUNBOOK — P37.2 Wave C: OSM becomes the origin of the national ALPR layer (I8 §4.3/§7.4/§7.7/§8; OM-19)

*The scripted runbook for the national OSM acquisition wave. The
machinery — `ops/src/ops/wave_c.py` (`sig.wave-c-gate/1` +
`sig.wave-c-plan/1`), the `ops/gcp/wave-c.sh` driver, the declared
cadence diff (`osm_overpass` monthly `12 8 24 * *` + the four
`paused_until` rows, FEA-15) and the committed mirror-retirement diff
(`camera_registry_targets.toml` `[[enumerated]]`) — is engineered and
fixture-tested; **all five legs stay queued** until the window opens
under the recorded ING-GO-C. The operator packet:
`docs/build/reports/p37.2-wave-c/WAVE_C_PACKET.{json,md}` +
`WAVE_C_PROBE_RUN.json` (suppressed, not a pass).*

## Contract (ticket 345)

- **Window:** 2026-11-16 → 2026-11-20 (future-ok: scheduled: contract
  window); earliest 2026-10-26 **iff** P37.1, PKG-07 and Q-23 are all
  recorded landed early. AR-3's daily never-band 03:00–06:30Z binds
  every leg; L4's read-only soak may read inside the window or the 48 h
  grace after it (a run landing 11-20 soaks inside the grace).
- **ING-GO-C — recorded at GATE-G5** (GATE DECISIONS,
  2026-10-25T18:40Z, §3): *"Approve ING-GO-C (rec.)"* (AskUserQuestion
  selection). The gate requires the recorded text **byte-exact** — a
  paraphrase is a refusal; silence is never consent. P37.2 was **not**
  named on the OM-20 list — every leg is an in-ticket pause.
- **The tier-bump go is a separate in-ticket pause** — asked when L2
  is due, recorded verbatim in the close inputs. ING-GO-C is the
  wave's go, never the tier's; a borrowed text refuses.
- **Q-23 (B-11) = a:** autoresize cap 40 GB, pre-grow to 25 GB,
  temporary tier bump. The disk grow is **one-way** — a resumed run
  reads the current size and records a SKIP, never re-grows blindly.
- **S5-4:** the national run keeps non-US objects (US-first ordering)
  — never a US-only fetch. **HG-11 rides P37.65** — nothing publishes.
- **One manual job at a time** (P36.12's sequencing rule); never
  concurrent with `sig-materialize`, a G2 slot or another manual run.
- **FEA-15:** the four Wave-B batch rows whose monthly dom-16…19 crons
  fall inside the window — `r11-layers-01`, `r11-layers-02`,
  `r11-ate-01`, `r11-procurement-01` — carry the declared
  `paused_until = "2026-11-20"` bound and are read back paused before
  the national run.

## Legs (in order — a missed leg is reported, never silently skipped)

1. **L1 — pre-grow:** OM-14 pre-state (instance + job declarations +
   scheduler list + `sources.toml` sha256 + `sig-ops cadence --check`)
   → AR-2 on-demand backup polled to DONE, read back `SUCCESSFUL` →
   disk to 25 GB + autoresize limit at 40 GB.
2. **L2 — tier bump after the go:** the verbatim in-ticket go →
   `--tier=db-custom-2-7680` → poll UPDATE DONE → api `/health` →
   tier read-back.
3. **L3 — national run:** the four early-fire rows recorded held →
   `scheduled-ops.sh --apply` reconciles the jobs on one pinned digest
   and republishes the declaration bundle (the retarget + pause rows
   bind at publish — SIG-OPS-005) → `osm_overpass` reads the declared
   `12 8 24 * *` → the first national fetch **manual** → the §7.7
   verify set → the `+0` re-run → the camera-site ER rematerialize →
   the mirror-retirement record.
4. **L4 — 24 h soak read:** ≥24 h after the recorded run end —
   instance health + no overlapping materialization + the record.
5. **L5 — revert:** `--tier=db-custom-1-3840` → poll UPDATE → api
   `/health` → post-state capture + closeout.

## Machinery

| artifact | role |
|---|---|
| `sig-ops wave-c-plan [--json]` | the deterministic `sig.wave-c-plan/1` step list — every step admission-gated, the L2 operator pause marked |
| `sig-ops wave-c-gate --inputs <json>` | `sig.wave-c-gate/1` verdict over **recorded** inputs; `action: admit` before a leg's first mutation, `action: close` before it is recorded green; exit `0` go / `42` no-go (queued, never silent) / `2` usage |
| `ops/gcp/wave-c.sh --check` | plan-only print incl. the recorded-inputs template; no ADC, no network, exit `0` |
| `ops/gcp/wave-c.sh --apply --leg L1…L5 --inputs <json>` | requires `SIG_GCP_PROJECT` + usable ADC (exit 3 absent — never fabricates), gates, then executes the named leg's steps |
| `docs/build/reports/p37.2-wave-c/` | the `prepared_not_executed` packet + the suppressed `sig.probe-run/1` |
| `connectors/src/connectors/data/camera_registry_targets.toml` | the committed retirement diff: the two ALPR mirrors under `[[enumerated]]` (`status = "retired_mirror"`, fetch fields kept verbatim as the restore record), the four CCTV targets still under `[[targets]]` |
| `ops/cadence.toml` | the declared retarget (`osm_overpass` → monthly `12 8 24 * *`, task timeout `3h`) + the four `paused_until` rows |

## Gate criteria (each refuse-on-fail)

`go` (ING-GO-C byte-exact + `recorded_at`) · `window` (supplied `now`
inside the window — or the earliest window only when P37.1/PKG-07/Q-23
are all recorded landed; never inside 03:00–06:30Z; L4 may read inside
the soak grace) · `q23` (the adopted posture recorded) · `review`
(`osm_overpass`'s review-status read green — **read, never written**;
the row flips nothing) · `order` (`completed` covers every earlier leg
— green or held-reported; the leg not already green) · `scope`
(`run_set` == `["osm_overpass"]` on L3, empty elsewhere) ·
`exclusions` (no materialize/G2/cut-day active) · `serialize` (one
manual job at a time) · `wave_b_pause` (all four early-fire rows
recorded held — FEA-15) · `prestate`/`backup` (L1) · `tier_go` (L2 —
byte-exact, never the ING-GO-C text) · `soak_ready` (L4 — ≥24 h after
the recorded run end) · close-only: `disk` (≥25 GB, cap 40) · `tier`
(read-backs `db-custom-2-7680`/`db-custom-1-3840`) · `rebuild` (one
sha256 digest across both jobs, `declared_published`) · `retarget`
(`12 8 24 * *`) · `run` (ok + `claims_added` > 0) · `tiles` (±2 % of
discovery, ≤ 154,814 taginfo) · `privacy` (`user_uid_captures == 0`) ·
`plus0` (`claims_added == 0`) · `er` (`merge_pct ≥ 95.0`, measured
integer `net_new`, `lineage_recorded`) · `retire` (exactly the two
named targets, the four CCTV targets still scheduled, `derived_from`
recorded, a non-empty `next_fire`) · `soak` (L4) · `revert` (L5
post-state).

## The national run (L3) — step order

1. **FEA-15 read-back:** all four early-fire triggers/declarations
   recorded paused.
2. **Reconcile on one pinned digest:** `scheduled-ops.sh --apply` —
   `sig-ingest-osm-overpass` carries P37.1's national-tile code;
   `sig-ingest-camreg-batch-05` carries the committed mirror-retirement
   diff; the declaration bundle republishes.
3. **Retarget verify:** the OSM schedule reads `12 8 24 * *` (monthly,
   dom-24, 08:12Z) with the `3h` task bound.
4. **The manual first run:** `gcloud run jobs execute
   sig-ingest-osm-overpass --args
   scheduled-ingest,--source,osm_overpass,--sink,pg --wait` — US-first
   tile ordering (`out count;` discovery per US state/DC, then non-zero
   countries), `out body center qt;` fetches (never `out meta`),
   180 s fetch timeout, ≈1 query / 30 s.
5. **§7.7 verify:** run row `ok` + capture bytes; tile totals within
   ±2 % of discovery and within taginfo's 154,814; **zero `user`/`uid`
   bytes** across captures; `claims_added > 0`.
6. **`+0` re-run:** the identical execute again — `claims_added == 0`.
7. **ER rematerialize:** `sig-materialize` over the camera-site pool —
   ≥95 % of the 132,689 republish rows merge onto OSM origin sites;
   the **measured** net-new count recorded (≈22k is the planning
   inference, never asserted); `infer_lineages` records one shared
   lineage — mirror↔origin claims never corroborate independently.
   **§7.8: below the bound the republish targets stay scheduled and
   the retirement does not close.**
8. **Retirement record:** exactly `osm_surveillance_deflock` +
   `osm_surveillance_alpr_nationwide` will read out of the live fetch set;
   `derived_from` lineage recorded (PKG-12 ED-49); the batch's next
   fire read back **after** the retirement.

## Rollback / forward-fix (append-only posture)

- **Tier:** L5 reverts; a mid-window abort reverts immediately and
  reports the wave held.
- **Disk:** one-way by design (Q-23) — stays 25 GB under the 40 GB
  autoresize cap.
- **Instance:** the L1 AR-2 backup is the restore point; corruption →
  PITR clone, never in-place restore/deletion.
- **Targets:** the `[[enumerated]]` rows carry the fetch fields
  verbatim — restoring a mirror is a revert of the committed diff.
- **Claims:** forward-fix only; nothing is UPDATE/DELETE'd.

## Deferred / excluded (recorded, not implicit)

- Publication — rides P37.65 under HG-11; nothing publishes here.
- `D-R11-LATER-04` (ADR-171 Stage-0 outreach) — inapplicable and OPEN:
  the wave fetches an already-permitted source under its standing
  rights posture and contacts no source owner.
- The four CCTV republish targets — stay scheduled until each origin
  is separately checked; never swept into this retirement.
- RF-derived nodes — keep the 3-decimal coarsening (the P35.66 screen
  is owed elsewhere).

## Re-run prompt

`implement-spec spec=docs/tickets/345_P37.2__wave-c-osm-national-alpr-layer.md
live_verification=true` — each leg needs the recorded ING-GO-C, the
window, its own gate inputs and (L2) the operator's verbatim in-ticket
go; the disk pre-grow is one-way — a resumed run reads the current
state, never re-grows blindly.
