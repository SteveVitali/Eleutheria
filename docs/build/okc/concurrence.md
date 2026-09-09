# OKC publication — two-reviewer concurrence (SIG-PUB-008, HG-11)

This is the signed-checklist file the publication gate reads for the Oklahoma City
dossier (`ReviewerConcurrence`, RISK-P0-05). SIG-PUB-008 requires **two
independent reviewer *roles*** to record a written position; disagreement (or fewer
than two) defaults to **no-publish**.

## Gate state: **PENDING — HG-11 not established**

Per the P21.4 gate answers, **HG-11 (operating governance) is SKIP — not
established**: no two named reviewer roles with written concurrence exist yet, and
the takedown/corrections contact is not live. Publication is therefore gated; this
ticket ends at **staging**, not go-public.

| Reviewer role | Independent | Agrees | Written rationale | Date |
|---|---|---|---|---|
| _(role 1 — pending appointment under HG-11)_ | — | — | _pending_ | — |
| _(role 2 — pending appointment under HG-11)_ | — | — | _pending_ | — |

Because fewer than two independent reviewers have recorded a written position,
`policy.officer._concurrence_ok` returns `False` ("fewer than two independent
reviewers recorded a written position") and any person-named claim defaults to
no-publish. On the OKC pages this is moot: **no un-permitted public-employee name is
published** (the dossier attributes claims to source *roles*/records, and
`applyPublicationPolicy` runs over every dossier at build time — SIG-PUB-017).

## What unblocks it

1. HG-01 names the legal home (`docs/governance/governance-and-code-of-conduct.md`,
   SIG-GOV-012).
2. HG-11 appoints two independent reviewer roles and a live takedown/corrections
   contact; each role records a written `agrees=true` position here.
3. Re-run this ticket's publication gate; then go-public is a single human decision.
