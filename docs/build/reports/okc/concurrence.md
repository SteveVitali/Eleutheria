# OKC publication — two-reviewer concurrence (SIG-PUB-008, HG-11)

This is the signed-checklist file the publication gate reads for the Oklahoma City
dossier (`ReviewerConcurrence`, RISK-P0-05). SIG-PUB-008 requires **two
independent reviewer *roles*** to record a written position; disagreement (or fewer
than two) defaults to **no-publish**.

## Gate state: **OPERATOR-RESOLVED — sole-maintainer concurrence (2026-09-16)**

The operator has elected a **sole-maintainer posture**: both reviewer roles are
filled by the same named person, and the *independence* requirement of SIG-PUB-008
is **waived by explicit operator decision** — not satisfied. This file records that
decision truthfully; it does not fabricate independence. A future independent
second reviewer is always adoptable — the posture is revisable.

| Reviewer role | Filled by | Independent | Agrees | Written rationale | Date |
|---|---|---|---|---|---|
| Reviewer 1 — maintainer | Steven Vitali (operator, legal home, takedown contact of record) | n/a (first role) | yes | Maintains the codebase end-to-end; reviewed the published surface against Part VIII, the predicate allowlists, and the publication gates it enforces. | 2026-09-16 |
| Reviewer 2 — operations | Steven Vitali (same person — **not independent**; independence waived by operator) | **no** | yes | Operator-directed self-concurrence under the recorded sole-maintainer posture; the independence requirement is waived, not met. | 2026-09-16 |

**Honest consequence:** `policy.officer._concurrence_ok` still returns `False` —
the two positions are not *independent*, and the code correctly refuses to treat
self-concurrence as the two-reviewer bar. On the OKC surface this is moot by
construction: **no un-permitted public-employee name is published** (claims
attribute to source roles/records; `applyPublicationPolicy` runs over every dossier
at build time — SIG-PUB-017). The officer-naming gate remains default-no-publish.

## What a future strengthening looks like

1. Operator recruits a second *independent* reviewer post-launch.
2. That reviewer records a real `agrees`/`disagrees` position here with a date.
3. The gate then satisfies SIG-PUB-008 as designed — no operator waiver needed.
