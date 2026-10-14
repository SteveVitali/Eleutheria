<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- P34.46 L1 draft — the /status/ maintenance notice for the L2 slot.
     This is a NEW sentence (not one of N-1…N-7): it ships only as a copy
     batch confirmed verbatim before the slot (B-2), published through
     P34.10's path under the slot's go, and withdrawn with N-7 after
     verification. The <slot> times fill when the operator picks the slot. -->

# /status/ maintenance notice — DRAFT (not yet shipped)

Proposed sentence (new copy, outside the N-1…N-7 allowance — the
operator confirms this verbatim or supplies the final text before the
slot):

> "The API is under scheduled maintenance <slot start>–<slot end> UTC;
> some responses may be briefly unavailable."

Context (for the confirmation, never part of the sentence): during the
deploy, requests that block on the `claim_evidence` schema lock fail
within `lock_timeout`/statement timeouts; the rehearsed hold is
`<rehearsal bound>` s. The notice sits alongside N-7 for the slot and
leaves with it when verification passes.
