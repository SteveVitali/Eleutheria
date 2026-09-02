# Takedown, corrections, and suppression policy

*Adopts docs/2_canonical_design_spec.md §45 (SIG-GOV-001…011). The two
load-bearing distinctions in this policy — corrections preserve history, and
suppression is not deletion — are also **executable and tested**:
`policy/src/policy/governance.py`, `tests/unit/test_governance_policy.py`. The
intake categories, SLAs, permitted outcomes, and transparency-report shape are
maintained as data in `policy/src/policy/data/takedown.toml`.*

SIG is a citable source about institutions and infrastructure. That imposes two
obligations that pull in opposite directions: the record must be **durable and
reproducible** (so a citation made last year still resolves to what SIG said last
year), and it must be **answerable** (so a genuine privacy harm or legal demand
can be acted on). This policy is how SIG holds both at once.

## Intake (SIG-GOV-001, SIG-GOV-002)

A public intake channel exists and is reachable **in one click from any claim**
(SIG-UI-033). It accepts, at minimum, these categories:

- **factual error** — a claim is wrong;
- **privacy harm** — a claim harms a person;
- **legal demand** — a formal legal request;
- **security concern** — a claim creates a security risk;
- **copyright claim** — a rights-holder objection.

Intake **does not require identifying the submitter** (SIG-GOV-002). The single
exception is a legal demand that requires standing to act on. A person reporting
a privacy harm never has to name themselves to be heard.

## Handling and SLAs (SIG-GOV-003, SIG-GOV-004)

SIG publishes response SLAs **by category**. **Privacy-harm and safety/security
claims are prioritised above all others, including above factual corrections**
(SIG-GOV-003). The published SLA hours and priority ranks are the data rows in
`takedown.toml`; the ordering is asserted by
`test_sla_prioritises_privacy_and_safety`.

The permitted outcomes of a request are (SIG-GOV-004):

1. **correct** the claim (see below);
2. **annotate** it;
3. **suppress** it from public view while retaining it internally (see below);
4. **delete** it entirely (reserved — see below);
5. **refuse, with published reasoning.**

**Refusal is a real, exercisable option.** A takedown process that cannot say no
is a heckler's veto, and would make the record hostage to whoever complains
loudest. When SIG refuses, it says so and says why, in public.

## Corrections preserve history (SIG-GOV-005, SIG-GOV-006)

**A correction is a new assertion, never a deletion or an overwrite**
(SIG-STORE-020, SIG-TIME-009, §16.6). When SIG corrects an erroneous claim, it
closes its prior belief and appends the corrected one, pointing back at what it
revises and recording why.

The invariant this buys: **a query at a prior `as_of_belief` still returns the
value SIG believed then.** A journalist who cited SIG in June can reproduce
exactly what SIG said in June — *and* can see that SIG later corrected it and
why. That property is the difference between a database and a citable source. It
is enforced in code by `BeliefLog.value_as_of_belief` and proven by
`test_correction_preserves_prior_belief`, which mirrors the §16.6 worked example
("25 cameras" mis-read, corrected to "225"; a June query still returns 25).

Every correction appears in the **public corrections log** (SIG-GOV-006,
SIG-UI-032).

## Suppression is a distinct primitive (SIG-GOV-007, SIG-GOV-008, SIG-GOV-009)

**Suppression exists as a primitive distinct from deletion** (SIG-GOV-007). An
append-only store with no suppression path would force a destructive delete the
first time a valid privacy demand arrived — violating the append-only invariant
under pressure, at the worst possible moment, with no design behind it.

Suppression sets a flag that **removes material from public surfaces and exports
while retaining it internally under the `sealed` tier**, with the decision, its
author, and its rationale recorded. Publicly the claim is gone; internally the
reproducible record survives. This is implemented by `BeliefLog.suppress` /
`public_value_as_of_belief` and proven by
`test_suppression_is_distinct_from_deletion`.

**True deletion is reserved** for material SIG must not hold at all (SIG-GOV-008).
It **requires two-person authorization** and **leaves a tombstone** recording
that a deletion occurred, its category, and its date — **never its content**.
Enforced by `BeliefLog.delete` and proven by
`test_deletion_requires_two_person_auth_and_leaves_tombstone`.

This is why the evidence store's Object Lock is **governance mode, not compliance
mode** (SIG-GOV-009, SIG-EVID-006): compliance mode would make the archive
unimpeachable *and* make legitimate removal technically impossible. SIG chooses
the capability to remove, and compensates with transparency reporting.

## Disputes without correction (SIG-GOV-010)

A subject who disputes an *accurate* claim can attach a **response**, published
alongside the claim. Being able to answer is a real remedy, and it costs SIG
nothing but honesty.

## Transparency reporting (SIG-GOV-011)

SIG publishes **periodic counts of requests by category and outcome, including
refusals.** The report's shape (grouped by category × outcome, refusals
included, published quarterly) is data in `takedown.toml` and asserted by
`test_transparency_report_groups_category_by_outcome_including_refusals`.
