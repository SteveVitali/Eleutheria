<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# `eval-rubric/1` — independent identity rubric for reviewer packets

> P32.9, SIG-EVAL-002, ADR-128. Versioned — a rubric change is a new
> `eval-rubric/N`, a new `protocol_digest`, and therefore a **new preregistered
> campaign**, never an in-place edit mid-campaign.

## 1. The question

For each sampled pair of records the reviewer answers one question:

> **Do these two records refer to the same physical device at a compatible
> observation period?**

The resolved-unit definition is the deployed rules contract
(`resolution/src/resolution/data/camera_site_rules.toml`): a resolved camera
site is records of the **same physical device**. A pole, an intersection, a
facility, a stream endpoint, a registry row, and a device are **not**
interchangeable answers.

- Do not blend "same site" and "same device" truth in one label.
- Absence of an inventory entry is **not by itself** proof of `different`.
- A mirrored record can prove two rows are **copies of one source observation**
  without independently confirming the device exists — that still answers the
  pair question, but cite the mirror lineage, not invented fieldwork.
- If protection rules (tier, geometry coarsening) remove information essential
  to a decision, the answer is `insufficient_evidence`. **Never defeat the
  protection to obtain a binary label.**

Every label carries `reference_basis` ∈
`source_record_identity | physical_identity | site_identity`, recorded on the
label row. Evaluate only the basis the endpoint claims.

## 2. The three labels

| Label | Meaning | Minimum rationale (required in `reason`) |
|---|---|---|
| `same` | Positive evidence supports the same defined identity, including temporal compatibility. | Cited upstream IDs / source lineage or source evidence that distinguishes the device from its neighbours. **Exact coordinates alone are insufficient.** |
| `different` | Positive evidence supports distinct identities, or an incompatible identity claim. | Distinct simultaneously-operating devices, incompatible authoritative IDs, non-overlapping object definitions, or other cited distinguishing evidence. **Distance alone may be insufficient** for mobile/replaced assets. |
| `insufficient_evidence` | The available evidence cannot decide under this rubric. | Say which: missing capture, ambiguous shared label/ref, coarse coordinates, unclear device-vs-site, temporal replacement uncertainty, unresolved source conflict. |

`insufficient_evidence` is a real, recorded outcome — it stays in every
denominator and can never be silently converted into `same` or `different`.
An abstention is not evidence either way.

## 3. What the packet shows you (and never shows)

Each `human_eval_packet.payload` is digest-pinned (`packet_digest`) and
contains, per side: the original observation fields (raw **and** normalized —
the normalization is part of what is being checked), authorized source name and
upstream ID, observation/capture dates with uncertainty, excerpt/locator,
source-lineage facts, and neutral geometry at the allowed tier.

**Source identity is legitimate evidence and is not hidden.**

The blinded packet **never** contains: matcher tier, score, predicted
disposition, derived cluster membership, model/agent labels or rationale,
other reviewers' labels, queue-confidence text, or any auto-generated merge
conclusion. Left/right orientation and item order are deterministically
randomized; opaque `hev-*` sample ids do not encode partition or tier.

> Residual awareness note: a pair's presence in a model-positive sample can
> itself reveal selection. Neutral control/development items are mixed in
> where the protocol permits. This is true first-pass blinding, **not**
> claimed perfect blinding.

## 4. Rules of work (first pass)

1. **Work alone.** Do not discuss individual items with the other reviewer or
   the rules authors before both independent submissions exist.
2. **Judge the packet in front of you.** You may cite additional
   already-authorized preserved evidence; anything newly needed is a packet
   revision request to the custodian — it cannot quietly alter the sealed set.
3. **Abstain when you must.** `insufficient_evidence` with a reason is a
   complete, creditable answer.
4. **Record your time.** Fill the measured-time worksheet
   ([`measured-time-worksheet.md`](./measured-time-worksheet.md)) per item and
   per session.
5. **Corrections append.** A wrong label is corrected by a **new** label row
   (supersession with reason), never an edit. After unseal, a corrected label
   invalidates the old result and forces a new evaluation decision.
6. **Never** look for the "expected" answer in matcher output, previous
   labels, or operational `review_decision` rows — the interface does not
   show them; do not seek them out of band.

## 5. Adjudication

Two equal `same`/`different` first-pass judgments yield the reference label.
**Any** disagreement, **any** `insufficient_evidence`, or non-completion goes
to the custodian-mediated adjudication:

1. The adjudicator first records an **independent** judgment blind to the
   prior votes.
2. Only then may the adjudicator inspect the disagreement and evidence to
   resolve it (`same` / `different` / `insufficient_evidence` /
   `unresolved` — `unresolved` is a permanent valid outcome).
3. Both first-pass labels, the adjudication, and all reasons are preserved
   forever. Nothing is overwritten to manufacture agreement.

## 6. What a label is not

A reference label answers "same defined object". It is **not** an operational
accept/reject decision (`review_decision` keeps that contract unchanged), not
publication approval, and not a person-level assertion. Reviewer identity is
pseudonymous ([`reviewer-provisioning.md`](./reviewer-provisioning.md)); no
contact or employment data enters the graph.
