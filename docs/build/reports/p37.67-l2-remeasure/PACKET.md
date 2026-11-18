# P37.67 — Stream-L acceptance packet (L2 re-measurement, R11-CONF-14)

The CONF-14 tail row of the L3 confidence program (ADR-152/154): re-run L2's
graph-quality measurements over the Round-11 release, flip every ratchet whose
named fixing rows landed, and report the §9 success criteria. Every row below
names the BM-STATUS-01 layer the evidence reached — engineered /
fixture-verified results only; nothing here claims a staging, live or public
verdict (SIG-ENG-042).

## Leg ledger

| leg | stage | verdict | layer |
|---|---|---|---|
| `acceptance-record` | deterministic | ran in this dispatch — `exports/src/exports/data/streaml_acceptance.json` (`sig.streaml-acceptance/1`) generated over committed inputs; `docs/build/reports/P37.67_streaml_acceptance.md` is its readout | engineered |
| `fixture-r-report` | deterministic | ran in this dispatch — the real placement-R harness (`ops.quality.run_quality_probe`) over the fixed quality-page corpus is bound into the record as `measurement.bound_reports[]`; every unavailable seam reports `not_evaluable` | fixture-verified |
| `ratchet-flips` | registry change | landed — 9 checks flipped `ratchet → enforce` where every named fixing row is landed and a measurement seam exists (GQ-01, GQ-03, GQ-04, GQ-07, GQ-10, GQ-11, GQ-13, GQ-14, GQ-15); `sig-exports quality diff --ticket P37.67` → 0 violations | engineered |
| `live-remeasure` | live | **prepared_not_executed** — queues as `D-P37.67-1` | deferred |
| `seam-completion` | engineering | **owed** — the 11 kept ratchets' blocks named in `kept_reason` | deferred (`D-P37.67-2`) |

## Why the live leg could not run

The ticket asks to re-measure L2 on **the Round-11 release**. Under
`live_verification=false` that population does not exist to this dispatch:

- **The Round-11 release candidate is not cut or promoted.** `D-P37.65a-1`
  (the release-cut + live-crawl legs) and `D-P37.65b-1` (the HG-11 promote leg)
  are both OPEN — the cut is the operator's windowed production mutation and
  the promote runs only on the operator's verbatim go.
- **The hosted spine read handle is an OM-19 live window.** The M-placement
  checks measure over `sig_audit` (read-only, statement-timeout); no DSN, no
  SIG-project ADC and no recorded authorisation exist in this environment.
- The baseline apply path is **`sig-exports quality apply-baselines`** — the
  only baseline writer — and it only accepts measured records; there is no
  honest way to synthesise them.

The leg is deferred as `D-P37.67-1` (kind V) with the verbatim re-run prompt
`implement-spec spec=docs/tickets/496_P37.67__stream-l-re-measure.md
live_verification=true`. On the re-run: run `sig-ops quality baseline` over
the hosted `sig_audit` DSN + the promoted release dir (M and R placements),
then `sig-exports quality apply-baselines --report … --out …`, re-generate
`streaml_acceptance.json` bound to the measured reports, and re-verdict the
§9 criteria from measured values — never from the L2 historicals.

## What the engineered half proves

- **The flips are legal and landed-cause only.** `sig-exports quality diff
  --old <pre-flip registry> --new <registry> --ticket P37.67` reports zero
  violations: no mode moved without `P37.67` in `fixing`, no baseline moved,
  no threshold loosened.
- **Kept ratchets are disclosed, not silent.** Each of the 11 kept ratchets
  carries a `kept_reason` naming its block (an owed evaluator seam, an
  unconsumed V-check output, a first-run population, or a gate activation) —
  ADR-154 R-3: a ratchet is a named debt, never a permanent excuse.
- **The §9 criteria are measured, not asserted.** The acceptance record
  verdicts each criterion `met`/`miss` only over a bound measurement
  (fixture/engineered today) or `not_measured` naming the owed live leg —
  13 `not_measured`, 4 met over the fixture corpus, 2 honest fixture misses
  (GQ-27's wording scan over the fixture's own committed artifacts).
- **Nothing here is a release claim.** The fixture corpus is a two-row
  deterministic scan dir; the L2 column is the historical
  `sig-2026-09-27-ce480ab1` census — labelled, never re-asserted.
