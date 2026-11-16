# ADR-247 — WACZ capture for the HTML-document jobs: a deterministic packager default, the `wacz` cadence declaration, and the named job set (P37.56)

- Date: 2026-11-14
- Status: accepted
- Ticket: P37.56 (R11-TRANS-02, BL-026 — on `r11/P37.56-wacz-capture-html-sources`)
- Base: `r11/P37.55-archival-deposits`
- Requirement stamps: SIG-EVID-007 (owned), SIG-INGEST-003, SIG-STORE-048 (cited)
- Supersedes: nothing

## Context

BL-026 asks that `--wacz` appear in the HTML-document jobs, that captures land
under the evidence bucket, and that capture availability surface honestly.
The seam already existed (`OcflCaptureStore(capture_wacz=, wacz_builder=)`,
`run_source(wacz=)`, the CLI's `--wacz`) but the `wacz_builder` was never
supplied on the runner path, so `--wacz` was inert — a flag that promised a
WACZ and produced none. Three decisions were this ticket's to make.

## Decision

1. **The fetched bytes are packaged into a deterministic single-response WACZ
   1.1.1 by default.** Under `capture_wacz=True` with no `wacz_builder`
   supplied, `OcflCaptureStore` builds the WACZ itself via
   `evidence.capture.build_wacz` over the response exactly as the fetch stage
   observed it — the real status and headers, never a synthesized render and
   never a fabricated 200 (a caller bypassing the fetch stage records a
   truthful `status: null` on the sidecar). The `wacz_builder` seam still
   wins when wired — the P02.2 Playwright path remains the answer for a
   JS-rendered capture, which §17.4 requires for JS-rendered artifacts. The
   WACZ's own multihash is recorded on the metadata sidecar (`wacz.digest`,
   `wacz.byte_size`) and returned on `CaptureRef.wacz_digest`, so the
   availability record binds the real member — never implied by presence.

2. **`wacz = true` is a cadence declaration, not a heuristic.** The flag is
   declared per `[[sources]]`/`[[batches]]` row in `ops/cadence.toml`;
   `scheduled-ops.sh` deploys the job's `--wacz` arg from it and the
   `wacz-capture.sh` leg script reads the same declaration for its named job
   set — one source of truth, no mode-sniffing of connectors. The flag is
   media-type self-limiting inside the capture store (only `text/html` /
   `application/xhtml+xml` captures gain a `page.wacz` member), so a mixed
   batch enables it without changing non-HTML members' output.

3. **The named set is the 14 dedicated HTML-document jobs plus the six
   Round-11 document batches carrying HTML members.** The all-HTML batches
   (`r11-disclosures-01`, `r11-disclosures-02`, `r11-documents-01`) and the
   mixed tier-2 batches (`r11-tier2-01..03`) declare `wacz = true`; the tier-2
   flag is configuration-only for non-HTML members (no extra execution, no
   changed output). Sources whose jobs are not HTML-document jobs — the
   JSON/API/bulk rows — declare nothing and are untouched. The run row
   records `wacz` (the enablement bit, so "enabled, produced none" is
   distinguishable from "disabled") and `wacz_captures`
   (`capture_digest → wacz_digest`).

## Alternatives

- **Wire the Playwright builder as the default.** Rejected for this ticket:
  the connector's live path holds no rendered browser session; packaging the
  fetched response records exactly what was retrieved. The builder seam is
  preserved for the §17.4 JS-rendered requirement, which needs a browser.
- **A `CaptureStore.wacz()` accessor instead of a ref field.** Rejected: the
  run row's availability binding wants the digest at capture time, on the
  ref the pipeline already returns — additive, no second read path.
- **Naming the job set inside the leg script.** Rejected: a second list would
  drift from the cadence declaration the deployer reads; the script derives
  its set from `wacz = true` rows.

## Revisit trigger

- §17.4's JS-rendered artifact requirement is exercised for a live source —
  then wire a Playwright `wacz_builder` behind the same flag (the packaging
  default stays for the non-rendered shape).
- The first `live_verification=true` run produces its WACZ members and run
  rows — the probe leg's declared shape is verified against them.
- A source class emerges where WACZ belongs on non-HTML captures (e.g. PDF
  bundles) — the media-type gate in `_should_capture_wacz` widens then, by
  its own ADR.
