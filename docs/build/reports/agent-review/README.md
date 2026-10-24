# Agent review lane — records (P35.48, SIG-CONF-002)

Append-only records of the **agent review lane** (ADR-152/ADR-153; gate
`Q-L3-4 [B-31] = no` — same-family blind contexts only; labelled, never
gating). This directory is *not* a `human_eval_*` table (ADR-128) and no
file here is ever read by an auto-write gate, eval-status promotion, or a
release gate (SIG-CONF-003).

## What lives here

| path | record family | writer |
|---|---|---|
| `universes/` | `sig.agent-review-corpus/1` — the corpus a packet draws over (keyed by digest) | the lane's weekly run |
| `packets/` | `sig.agent-review-packet/1` — the drawn 50-site + 30-edge stratified packet | `resolution.agent_review.build_packet` |
| `labels/` | `sig.agent-review/1` JSONL — two blind-context verdicts per item | `resolution.agent_review.append_records` |
| `maintainer-queue-s4.jsonl` | `sig.maintainer-queue-entry/1` JSONL — disagreements routed to the §4.4 S4 maintainer queue | `resolution.agent_review.append_queue_entries` |
| `reports/` | `sig.agent-review-report/1` — weekly consensus, agent–agent κ, queue appends | `resolution.agent_review.lane_report` |

## The rules these records carry

- `labeller_kind` is always `"agent"` with `model_id`, `prompt_digest`,
  `context_id` (`a`/`b` — two fresh same-family contexts, each blind to the
  other's verdict and to matcher internals), `seed`, and `corpus_digest`.
- Agreement records `agent_consensus` — never "correct". The report's κ is
  **agreement between two AI runs**, never accuracy: same-family agreement
  is correlated by construction (B-31).
- A disagreement mints an S4 **queue entry, never a decision** — the
  maintainer queue decides.
- Items in a B5-reserved partition (`calibration`, `pilot`, `sealed_final`)
  are never labelled — the sampler refuses them (SIG-EVAL-001).
- The committed `universe-d03decacb801.json` + `packet-arp-6203980e9c3b2948`
  run is `capture_kind: stand-in` — authored demonstration data, never a hosted measurement (leg runs: 0).

GQ-22 reads `labels/` through `ops.quality.eval_gq22` (S placement,
`mode = "report"`, warn-only `>= 0.9`, basis B3) — report-only, never a
gate.
