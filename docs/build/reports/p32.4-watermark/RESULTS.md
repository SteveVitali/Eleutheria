# P32.4 watermark measurement — `p31-scale-local` fixture (D-P31.1-1)

Deterministic local evidence for the bounded annotation/shaping watermark.
**Local Docker PG18+PostGIS only — nothing hosted or composed is claimed**;
the composed-stack verify (< 1 s warm / 8-way no-queue under the serving budget)
stays with the scheduled e2e row (P32.24 / P33.2 per the deferral).

## Fixture `p31-scale-local`

- `2,300,000` claims (the hosted defect's measured 2.3M spine size),
  `2,300,000` `claim_evidence` bindings across 100 captures / 100 artifacts —
  `generate_series` bulk loads, one statement batch per 100k claims so the
  watermark triggers accumulate honestly (130.6s +
  52.2s).
- Schema: the full production sqitch plan (same image/deploy path as tests/db).
- Cold = first read on a fresh session after `CHECKPOINT` + `DISCARD ALL`
  (shared buffers retained — a conservative bound on a true cold read).

## Serving budget (named, for this read)

The annotation/shaping freshness probe must not be the serve path's bottleneck:
warm p99 **< 10 ms**, 8-way concurrent p99 **< 50 ms**, and the plan must touch
only the `spine_watermark` table — never a claim-spine scan at any scale.

## Results (ms)

| read | plan actual | cold | warm median | warm p99 | 8-way median | 8-way p99 | 8-way max | 8-way wall |
|---|---|---|---|---|---|---|---|---|
| spine_watermark (bounded) | 2.1 | 23.6 | 0.22 | 1.81 | 0.8 | 37.7 | 46.2 | 138 |
| legacy six-count | 1721.3 | 1646.8 | 1372.59 | 2586.49 | 5035.4 | 11913.2 | 12166.7 | 138693 |

## Plans

- `spine_watermark` (bounded): `Sort -> Seq Scan`;
  shared hit/read blocks 4/0.
- legacy six-count: `Result -> Aggregate -> Gather -> Index Only Scan -> Seq Scan`;
  shared hit/read blocks 20542/170686.

## Verdict

The bounded read holds the budget by ~316x
against the legacy scan it replaced at the same scale; the read's cost is
O(27 facets) and cannot grow with the spine. The hosted defect (~10 s/request,
8-way median 48 s) is removed by construction — composed verification of the
end-to-end serving budget remains the scheduled e2e row's evidence.

Reproduce: `uv run python docs/build/tools/measure_watermark_p31.py`
