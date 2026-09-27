<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Human-campaign marker packet — P32.9 (SIG-EVAL-001/002, ADR-128)

The **durable marker** a campaign carries so the project always knows —
without asking — exactly where human participation stands. Agents may
prepare a ready marker; **only actual human attestations advance reference
completion**. A waiting marker keeps `D-R6.1-EVAL`, `D-P30.2b-1` and
`D-R10-HUMAN-1` open with precise evidence instead of silent staleness.

## 1. States

| State | Meaning | May be entered by |
|---|---|---|
| `tooling_ready` | schema, CLI, packets, docs landed; no campaign preregistered or no humans | agent (this ticket) |
| `awaiting_humans` | campaign preregistered + sample drawn; zero human attestations | agent |
| `in_progress` | ≥1 attestation + ≥1 human label recorded | **human activity only** |
| `reference_locked` | label watermark frozen; all sampled units accounted | custodian event |
| `evaluated` | unsealed once; evaluation decision recorded | custodian event |
| `incomplete` | stopping rule unmet / campaign abandoned honestly | custodian event |
| `superseded` | a new preregistration replaced this campaign | custodian event |

A campaign moves forward through the states; it never moves backwards —
a regression is a new marker row, not an edit.

## 2. Required marker fields

Every marker (a row/record the custodian or tooling emits per campaign)
carries:

| Field | Content |
|---|---|
| `campaign_id` | the preregistered id |
| `protocol_digest` / `packet digests` | from `human_eval_campaign` / `human_eval_packet` |
| `frame date` | `frame_snapshot` identity |
| `requested roles` | reviewers/custodian/method-reviewer seats needed |
| `eligible scope` | what this campaign may evaluate (tiers, ruleset digest) |
| `target sample design` | the manifest's strata/partition sizes + denominators |
| `actual completion counts` | labels per round, adjudications, open items |
| `blockers` | human-readable + structured reasons |
| `owner of the return decision` | the gate (e.g. `HUMAN-H4`, `P32.22a`) that resumes work |
| `next observable event` | the concrete thing that would change state |
| `state` | one of §1 |
| `measured time` | rollup from [`measured-time-worksheet.md`](./measured-time-worksheet.md) |

## 3. The current marker

```json
{
  "campaign_id": null,
  "state": "tooling_ready",
  "protocol_digest": "eval-rubric/1 + human_eval.py@P32.9 (see ADR-128)",
  "requested roles": "2+ independent human reviewers, 1 custodian/adjudicator, 1 method reviewer",
  "eligible scope": "camera-site pair identity, sealed_final holdout, per SIG-EVAL-001/002",
  "target sample design": "none drawn — awaiting campaign preregistration",
  "actual completion counts": {"labels": 0, "attestations": 0, "adjudications": 0},
  "blockers": ["D-R10-HUMAN-1: real human participation required; agents cannot substitute"],
  "owner of the return decision": "HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23",
  "next observable event": "first human_eval_attestation row under a preregistered campaign",
  "measured time": "no sessions yet"
}
```

This marker is the honest headline: **engineering ready, zero human labels,
nothing certified**.

## 4. What a marker must never say

- `evaluated` without a recorded `human_eval_release` row and frozen
  watermark.
- `in_progress` without attestation + label rows — fixture/test rows do not
  count (test campaign ids and fixture data are not campaign participation).
- Any human-gate signature — markers carry evidence, never ticks.
