<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Measured-time worksheet — P32.9 (SIG-EVAL-002, ADR-128)

The campaign's honest cost record. Reviewers time their own work; the
custodian aggregates it. Planned envelopes (S3 research) are a *budget*, the
measured numbers are the *record* — the two are never conflated.

## 1. Per-item sheet (reviewer fills per packet)

| Field | Entry |
|---|---|
| `campaign_id` | e.g. `human-er-pilot-2026-10` |
| `sample_id` | the opaque `hev-*` id on the packet |
| `reviewer_id` | pseudonymous handle (`rev-a`) |
| `label_round` | `independent_1` / `independent_2` / `adjudication` |
| `started_at` / `ended_at` | clock times, or `elapsed_minutes` |
| `label` | `same` / `different` / `insufficient_evidence` |
| `reason_category` | rubric §2 categories |
| `evidence_sufficient?` | y/n — packet quality signal |
| `follow-up needed?` | packet-revision request, if any |

Planning envelope per item: **8–15 minutes** (S3 research, pilot stage).

## 2. Per-session sheet

| Field | Entry |
|---|---|
| session date / duration | |
| items attempted / completed | |
| interruptions | |
| packet issues seen | (feed back to evidence acquisition — S1 contract) |

## 3. Campaign rollup (custodian fills)

| Stage | Planned | Measured | Source |
|---|---|---|---|
| Training | — | __ reviewer-hours | session sheets |
| Pilot (40 items × 2 reviewers) | 20–40 reviewer-hours | __ | session sheets |
| Final (design-sized) | per `design` | __ | session sheets |
| Adjudication | per disagreement count | __ | adjudication rows |

The rollup travels on the campaign marker
([`human-campaign-marker-packet.md`](./human-campaign-marker-packet.md)) under
`actual completion counts` and `blockers` — a campaign that ran long or
stalled says so.

## 4. Rules

1. **Measured, not estimated.** A rollup filled with the planning numbers is
   a falsification; leave the field empty until sheets exist.
2. **Time is evidence.** Label rows are timestamped at write; the worksheet
   numbers reconcile against `recorded_at` ranges, and a discrepancy is a
   marker note, not an edit of history.
3. **No per-person performance claim.** Time data calibrates budgets and
   flags packet problems; it is not a reviewer-ranking instrument.
4. Worksheets are campaign records — keep them with the packet
   (committed or archived alongside `human_eval_*` exports); they cite
   campaign/sample/reviewer handles, never real names.
