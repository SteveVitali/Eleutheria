<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# `docs/evaluation/` — the independent human-evaluation campaign packet

These are the P32.9 **preparation-time** artifacts for independent blinded human
evaluation of entity resolution (SIG-EVAL-001/002, ADR-128; research basis:
`docs/build/planning/2026-09-25-six-streams/research/S3-human-evaluation.md`).

They prepare a campaign. They do **not** recruit anyone, produce labels, or claim
human evaluation has occurred. `D-R10-HUMAN-1` (real human reference labels, owned
by HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) stays open; a waiting marker from
[`human-campaign-marker-packet.md`](./human-campaign-marker-packet.md) is the
durable, honest state of a campaign no human has yet joined.

| Document | Mode | Purpose |
|---|---|---|
| [`rubric.md`](./rubric.md) | living (versioned) | `eval-rubric/1` — the identity question and the `same` / `different` / `insufficient_evidence` decision rules every reviewer applies. |
| [`training-pilot-packet.md`](./training-pilot-packet.md) | living | How the 40-item pilot and reviewer training run, what counts as training vs. final evidence, and the freeze checklist. |
| [`reviewer-provisioning.md`](./reviewer-provisioning.md) | living | Operator instructions for pseudonymous reviewer accounts (`sig_eval_reviewer`), the `sig.eval_reviewer` tier token, attestations, and deprovisioning. |
| [`measured-time-worksheet.md`](./measured-time-worksheet.md) | living | The per-item and per-campaign time sheet reviewers and the custodian fill so the campaign's true cost is on the record. |
| [`human-campaign-marker-packet.md`](./human-campaign-marker-packet.md) | living | The durable campaign marker: states (`tooling_ready`, `awaiting_humans`, …), required fields, and the owned waiting path that keeps deferrals honest. |

## What this packet is not

- Not a certification. Tooling readiness is `tooling_ready`, not `evaluated`.
- Not operational review. P31.10/P31.11 `review_decision` accept/reject keeps its
  own table and semantics; reference labels live in `human_eval_*` and never
  flow into clustering or model-development views until a custodian-recorded
  release (`human_eval_release` + `sig_eval_*` views).
- Not agent-performed. An agent or LLM cannot mint a `human_eval_label` — the
  schema enforces attestation-pinned, reviewer-scoped writes under
  `sig_eval_reviewer`, and `sig_eval_custodian`/`sig_eval_admin`/`sig_materialize`
  hold no label grant.
