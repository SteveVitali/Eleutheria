<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P37.36 — the raw-archive lane packet (`prepared_not_executed`)

`sig.raw-archive-packet/1` — see `packet.json` for the machine row.

## The named mutation

The plan cell (row 460, verbatim): **"IN-TICKET PAUSE (never pre-authorised
under OM-20: archive write touching Part VIII-screened families); explicit
verbatim go · D-J3-1 [B-19] = yes: raw bytes for raw-ok sources only, after
the Part VIII byte screen · append-only write = · exposure rides P37.65
HG-11"**.

The leg is never pre-authorised — it runs only on the operator's explicit
verbatim go, inside `AR-3 + AR-2`.

The `hosted` append-only archive write, three legs in order:

1. `sig-exports raw-archive build` — the raw-ok lane over the `hosted`
   evidence store: `raw/<multihash>` objects + `raw/index.json`
   (`sig.raw-archive-index/1`), raw-ok sources only, after the Part VIII
   byte screen (`evidence.screen.screen_blob` under the committed
   `ops/at_rest_audit.toml` declaration, fail closed). P8-5/P8-6/P8-8
   captures emit field-allowlist re-serialisations recorded as **new
   captures** (`sig.raw-reserialisation/1`; the original is never served,
   never mutated — SIG-PUB-015/016, append-only).
2. `sig-exports push` — the raw objects to the R2 mirror and the GCS origin
   under content-hash keys with immutable `Cache-Control` (append-only;
   a re-push of identical bytes is a no-op).
3. `sig-ops raw-withdrawal rehearse` — the delete/purge/tombstone
   rehearsal receipt: the object deleted from mirror + origin, the CDN
   purge by URL, the `withdrawals.json` disposition and the 410 tombstone
   at the web path (D20 verbatim: 410 web / 404 mirror).

`D-J3-1 [B-19] = yes` decides the scope verbatim — raw bytes for raw-ok
sources only, after the Part VIII byte screen. Never a broader lane, never
a bypass. Exposure rides P37.65 HG-11 — the leg lands bytes on the
distribution host, but nothing links them publicly before that readout
(the view-original wiring only mints locators for objects the served index
actually carries).

## Why queued

`live_verification=false` dispatch + the archive write is **never
pre-authorised** (OM-20): no operator verbatim go exists and the hosted
env is absent (no ADC, `SIG_GCP_PROJECT` unset). The builder
(`exports/raw_archive.py`), the rehearsal machinery
(`ops/raw_withdrawal.py`), the runner (`ops/gcp/raw-archive.sh`), the
view-original wiring and this packet land; the leg itself is recorded
`prepared_not_executed` and filed `D-P37.36-1` — never run, never
fabricated.

## Re-run prompt (exact)

```
implement-spec spec=docs/tickets/460_P37.36__raw-archive.md live_verification=true
```

resuming at `ops/gcp/raw-archive.sh --apply` (append-only by construction —
a resumed run re-derives the archive and pushes only objects not already
served).

## Preconditions the leg-runner checks

- The operator's verbatim go recorded — `SIG_RAWARCHIVE_AUTHOR` exported
  (env only, HG-09); silence is never consent.
- ADC + `SIG_GCP_PROJECT` present (lib.sh `require_adc`/`require_project`).
- The `AR-3 + AR-2` window guard clear — the runner refuses (exit 42)
  inside the daily 03:00-06:30Z freeze or an AR-3 batch window.
- The byte-screen declaration (`ops/at_rest_audit.toml`,
  `sig.at-rest-audit-decl/1`) parses — a build with no declaration refuses
  rather than serve an unscreened byte.
