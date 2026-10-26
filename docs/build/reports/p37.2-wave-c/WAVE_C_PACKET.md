# P37.2 — Wave C return packet (prepared, not executed)

Ticket `345_P37.2__wave-c-osm-national-alpr-layer.md` / R11-ACQ-18 —
the single sequenced operation (P36.12's one-manual-job rule) that
turns OSM from mirror-republisher into the origin of the national ALPR
layer. **Status: `prepared_not_executed` — no live fetch ran, no
production mutation ran, no source permission flipped, no mirror
retired, nothing rematerialized, no tier changed and no live
verification was claimed.** All five legs are queued; the re-run
prompt below re-dispatches them inside the window.

Machine-readable twin: `WAVE_C_PACKET.json` (`wave-c-return-pass/1`).
Suppressed probe record: `WAVE_C_PROBE_RUN.json` (`sig.probe-run/1`,
`overall = suppressed` — recorded so this packet cites its own
suppression; suppressed is not a pass).

## Gate authority (verbatim records, not assumed)

- **ING-GO-C — recorded.** GATE DECISIONS (LEDGER.md,
  2026-10-25T18:40Z, GATE-G5 §3, kind `decision`): *"Approve ING-GO-C
  (rec.)"* (AskUserQuestion selection, Devin Desktop session) — the
  wave's legs run in their window under their own preconditions; the
  tier-bump go stays P37.2's own in-ticket pause. The gate
  (`ops/src/ops/wave_c.py`, `GO_VERBATIM`) requires the recorded
  selection byte-exact — a paraphrase is a refusal; silence is never
  consent.
- **OM-20: not named.** P37.2 was not on the GATE-G5 OM-20 list —
  absent an explicit naming, every leg is an in-ticket pause.
- **Q-23 (B-11) = a** — *cap 40 GB, pre-grow to 25 GB, temporary tier
  bump* (adopted "As stated (Recommended)", GATE-P log
  2026-10-01T04:35:53Z).
- **S5-4** — keep non-US acquisition: the national run keeps its
  non-US objects (US-first ordering).
- **HG-11 rides P37.65** — this row never publishes.

## The five legs (verbatim from the plan cell)

| leg | work | restore point |
|---|---|---|
| **L1 pre-grow** | OM-14 pre-state capture (instance + job declarations + scheduler list + `sources.toml` sha256 + `sig-ops cadence --check`) → AR-2 on-demand backup polled to DONE and read back `SUCCESSFUL` → disk pre-grow to **25 GB** + autoresize limit at **40 GB** | the AR-2 backup; the declared cadence state is committed |
| **L2 tier bump after the go** | the operator's **verbatim in-ticket go** (a gate input — asked when the leg is due; ING-GO-C is the wave's go, never the tier's) → `--tier=db-custom-2-7680` → poll UPDATE → api `/health` → read-back | L5 reverts to `db-custom-1-3840`; a mid-window abort reverts immediately |
| **L3 national run** | Wave-B pause posture recorded held for all four early-fire rows (FEA-15) → `scheduled-ops.sh --apply` reconciles the jobs on **one pinned digest** + republishes the declaration bundle → `osm_overpass` reads the declared **`12 8 24 * *`** → the first national fetch **manual** (`gcloud run jobs execute sig-ingest-osm-overpass --args scheduled-ingest,--source,osm_overpass,--sink,pg --wait`; US-first ordering, non-US objects kept — S5-4) → the §7.7 verify set → the **+0** re-run → the camera-site ER rematerialize (≥95 % of the 132,689 republish rows merged; measured net-new recorded; one shared lineage) → the mirror-retirement record | the L1 backup; the committed `[[enumerated]]` rows are the restore record; below the 95 % bound the targets stay scheduled (§7.8) |
| **L4 24 h soak read** | read-only — ≥24 h after the recorded run end, inside the window or the 48 h grace: instance health + no overlapping materialization + the record | read-only — nothing to restore |
| **L5 revert** | `--tier=db-custom-1-3840` → poll UPDATE → api `/health` → post-state capture + the closeout record | the revert itself restores the pre-wave tier; the disk stays 25 GB under the 40 GB cap (one-way) |

## Precondition verdicts at 2026-10-26T04:46Z

- **ING-GO-C: MET at the GATE — never exercised.** Recorded
  2026-10-25T18:40Z; the legs still need the window, the hosted
  environment and (for L2) the in-ticket tier go.
- **The window: NOT OPEN.** The run clock is 2026-10-26. P37.1 landed
  green, but PKG-07's hosted backfill legs (P35.15a/P35.15b) stay queued
  in RETURN PASS — the earliest-window predicate fails, so the
  strict 2026-11-16→11-20 window binds. The gate enforces it.
- **The hosted environment: UNMET.** No gcloud ADC and no
  `SIG_GCP_PROJECT`/`SIG_HOSTED_DSN` are available to this build
  context — the driver's credential gate exits 3 before any
  production command is attempted, and no live read was attempted.
- **The tier-bump go: UNASKED.** The in-ticket pause is collected
  when L2 is due — never assumed, never borrowed from ING-GO-C.
- **FEA-15: declared, not yet live-verified.** `ops/cadence.toml`
  carries `paused_until = "2026-11-20"` on `r11-layers-01`,
  `r11-layers-02`, `r11-ate-01`, `r11-procurement-01`; the FEA-15 pause
  posture is read at L3.1 (the gate requires all four recorded held).
- **AR-2 restore point: not taken — nothing ran.** A queued leg
  never reaches the restore-point step; recorded, not fabricated.
- **AR-3 never-band: n/a — nothing ran.** The gate enforces
  03:00–06:30Z on recorded inputs at run time.

## Re-run

**Re-run prompt (queued only — nothing in this row executed):**
`implement-spec spec=docs/tickets/345_P37.2__wave-c-osm-national-alpr-layer.md live_verification=true`
— resumes at the first unauthorised leg; the disk pre-grow is one-way
by design, so a resumed run reads the current state and never
re-grows blindly.

Driver: `bash ops/gcp/wave-c.sh --check` (plan-only, no credentials)
then per leg `bash ops/gcp/wave-c.sh --apply --leg L1|…|L5 --inputs
<recorded-inputs.json>` — the gate runs first; a no-go exits 42
before any production command. The full operator-facing command list
is in `WAVE_C_PACKET.json`'s `commands` and the runbook
`docs/build/reports/WAVE_C_RUNBOOK.md`.

## Never (the hard lines, carried verbatim)

- No live fetch before the window and the recorded ING-GO-C.
- No `ingestion_permitted` flip — `osm_overpass`'s review-status is
  read by the gate, never written (HG-03 is the operator's act).
- No mapper identity — every capture is `out body center qt;`, never
  `out meta`; zero `user`/`uid` bytes in any capture
  (SIG-INGEST-045e, asserted on the live leg when it runs).
- No mirror retirement beyond `osm_surveillance_deflock` +
  `osm_surveillance_alpr_nationwide` — the four small CCTV republish
  targets stay scheduled until each origin is separately checked.
- No publication, no `latest.json` change, no HG-11 tick.
- No append-only record rewrite; no secrets in files (HG-09).
