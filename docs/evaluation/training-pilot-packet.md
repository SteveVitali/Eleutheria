<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Training and pilot packet — P32.9 (SIG-EVAL-001/002, ADR-128)

How the calibration stage of a human-evaluation campaign runs. This document
instructs; it does not certify that any training or pilot has occurred.

## 1. Purpose and hard boundary

Training and the pilot exist to (a) teach reviewers the rubric, (b) expose
rubric ambiguities while they are still cheap, and (c) size the real time cost
before the final frame is drawn. Everything labeled in this stage is
**`development` partition evidence only** — it can never enter the final
holdout, and it can never certify a ruleset.

| Stage | Partition | Labels feed | May certify the final ruleset? |
|---|---|---|---|
| Training | `training` / `development` | rubric refinement, reviewer calibration | **never** |
| Pilot | `development` (drawn **outside every final-test dependency group**) | rubric freeze decisions, time budget | **never** |
| Final campaign | `sealed_final` | the certification evaluation | yes, once, at unseal |

The partitions are **dependency-group disjoint**: no entity, component, or
republisher-lineage group appears in more than one partition. If a campaign
cannot draw the pilot outside the final test groups, the frame must be
redesigned — the boundary is not adjustable afterward.

## 2. Pilot design (default)

- **Size:** 40 items (a starting point, not a certificate).
- **Draw:** `sig-resolution eval prepare --design pilot.json` with the
  pilot's own `seed`; dependency groups flagged `development` only.
- **Per item:** two **independent** reviewers, blinded packets
  ([`rubric.md`](./rubric.md) §3), expected 8–15 minutes each, measured with
  [`measured-time-worksheet.md`](./measured-time-worksheet.md).
- **Calibration session:** after both independent submissions, reviewers may
  discuss pilot disagreements to improve instructions. Discussion happens
  **only** on `development` items, never on `sealed_final` items.
- **Pilot budget:** 20–40 reviewer-hours total is the planning envelope
  (S3 research); record actuals on the worksheet.

## 3. Training material provenance

Allowed training material, each **labeled as such** in the packet
(`training_origin`):

| Origin | Use |
|---|---|
| Retired agent/model sets | illustration only; headers must say `agent` |
| Known edge cases (from prior operational review) | discussion cases |
| Explicit synthetic examples | mechanics drills; headers must say `synthetic` |
| Previously adjudicated `development` pairs | worked examples |

Synthetic or agent labels **cannot** become final human truth by relabeling
the file header — the schema has no path for it, and `training_origin` is
part of the packet payload digest.

## 4. Freeze checklist (custodian + method reviewer sign-off)

Before the final campaign is prepared, all of the following are frozen and
digest-pinned into `human_eval_campaign` / `human_eval_manifest`:

- [ ] rubric version (`eval-rubric/N`) — no open ambiguities left
- [ ] eligible-evidence policy (which tiers/excerpts packets may show)
- [ ] protocol version + `protocol_digest`
- [ ] sampling frame + `frame_snapshot` identity
- [ ] exclusions and their reasons
- [ ] analysis code + version (the evaluator that will read the labels)
- [ ] ruleset + `ruleset_digest` (the thing being evaluated)
- [ ] stopping plan (sample size, completion rule, adjudication rule)

Anything changed after this point ⇒ a **new** preregistration, a new
campaign id, and a new sample. The old campaign stays readable as history.

## 5. Rules-author firewall

Rules authors and operators receive **only `training`/`development` labels**
until the final run is frozen and unsealed. Schema enforcement: the
`development` released views are the only views rules tooling is granted;
`sealed_final` rows exist in no development-scope view.

## 6. Failure exits (record, don't paper over)

- Reviewers cannot reach a stable rubric reading ⇒ campaign stays
  `awaiting_humans`/`incomplete`; the blocker goes on the marker
  ([`human-campaign-marker-packet.md`](./human-campaign-marker-packet.md)).
- Pilot shows the evidence packets are routinely insufficient ⇒ fix evidence
  acquisition upstream (S1 contract), then re-pilot; do not proceed to a
  final drawn on weak packets.
- No humans available ⇒ the marker state stays `tooling_ready` /
  `awaiting_humans`; `D-R10-HUMAN-1` stays open and visible.
