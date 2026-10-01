## 44. Threat model and security

### 44.1 The premise

**SIG-SEC-001 (MUST).** The threat model of §44.2 MUST be a **maintained, versioned artifact**
reviewed at every phase gate, and every adversary row MUST name at least one mitigation that maps to
a defined requirement id. A row with no mapped mitigation fails the gate.

*Rationale (not itself testable).* SIG is adversarial by nature: vendors, agencies, and hostile
individuals have incentives to attack, discredit, subpoena, or poison it, and a design that assumes
goodwill is negligent here. The maintained threat model above is how that assumption is kept
operative rather than rhetorical.

### 44.2 The threat model

| Adversary | Objective | Primary mitigations |
|---|---|---|
| Vendor / agency counsel | Suppress or discredit | Rigorous provenance; a real corrections process (§45); conservative crawler conduct (§26); counsel relationships. **Not hypothetical:** an ecosystem project run by one developer on ~$80/month has already faced **two vendor takedown attempts, one still pending** |
| Legal process against SIG | Compel contributor identity | **Do not collect it** (SIG-CONTRIB-005); short log retention; transparency reporting |
| Doxxer using SIG | Locate or target an individual | Categorical exclusions (§43.2); the officer test (§43.4); no per-person query surface (SIG-API-012) |
| Data-poisoning contributor | Insert false presence *or false absence* | Provenance-required writes; review queues; anomaly detection; full revert (§34.4) |
| Entity-resolution attacker | Corrupt the graph by forcing bad merges | Deterministic-first cascade; auto-write demotion on precision loss (§14.7) |
| Scraper / re-host | Take the data without attribution | Open licences make this mostly legitimate; attribution obligations pass downstream (§42.4) |
| Infrastructure attacker | Take SIG offline | Static-first architecture; mirrors; offline distribution (§46.5) |
| Insider | Exfiltrate sealed material | RLS (§16.8); access logging (SIG-EVID-012); least privilege |
| State actor | Surveil SIG's researchers | Minimal retention; pseudonymity; the whole architecture assumes this |

### 44.3 Warrant-resistant architecture

**SIG-SEC-002 (MUST).** SIG's strongest protection for contributors is **not holding data about
them**. Retention minimization is a security control and MUST be implemented as one, not treated as
a privacy nicety.

**SIG-SEC-003 (MUST).** SIG MUST publish a transparency report covering legal demands received,
complied with, and refused, and SHOULD maintain a warrant canary. The response posture for demands
directed at SIG MUST be documented **before** the first demand arrives.

**Round-11 amendment (A-4, Q-E2-09 = c; ADR-166; recorded 2026-10-01).** SIG meets this requirement
with a written demand-response posture published on the site — what SIG holds and how it minimises
what it holds, who receives legal process (the operator, as the interim legal home; the
SIG-GOV-012/013 note), how preservation requests are handled, the user-notice policy and the
publication of counts — stated as not legal advice and not reviewed by counsel, and with published
counts of legal demands received, complied with and refused (counts only; no requester identity or
case detail). The warrant canary, a SHOULD, is declined: one maintainer cannot guarantee scheduled
re-publication, a lapsed canary is itself a false signal, and SIG has no counsel to answer the legal
questions a canary raises. The "before the first demand" clause stays owed until the posture is
published (P37.8).

### 44.4 Access control

**SIG-SEC-004 (MUST).** Sensitivity tiers enforced by restrictive RLS; public API role without
`BYPASSRLS`; export roles running with row security **off** so a would-be-filtered export fails
loudly (SIG-STORE-023). RLS policy tests are CI-blocking (SIG-STORE-024).

**SIG-SEC-005 (MUST).** Access to `restricted`/`sealed` bytes MUST be logged with requester,
purpose, and time — and that log MUST itself have a retention limit, so it does not become a
surveillance record of SIG's own researchers (SIG-EVID-012).

### 44.5 Standard practice

**SIG-SEC-006 (MUST).** Secrets in a manager, never in the repository; dependency and container
scanning in CI; SBOM per release; signed releases; least-privilege service accounts; documented
incident response with a disclosure commitment.

---

## 45. Corrections, disputes, and takedown (Q32)

### 45.1 Intake

**SIG-GOV-001 (MUST).** A public intake channel MUST exist, reachable **in one click from any
claim** (SIG-UI-033), accepting: factual error; privacy harm; legal demand; security concern;
copyright claim.

**SIG-GOV-002 (MUST).** Intake MUST NOT require identifying the submitter, except where a legal
demand requires standing.

**Round-11 waiver — WV-05, e-mail-only intake (ADR-180; recorded 2026-10-01).** For Round 11 the
operator waived one-click, unidentified intake in their adopted sentence recorded in ADR-180 (A-23
part 2, GATE-P log round 9; agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z; sha256
`bf1f65d5aaa1…`), with B-8 "Email, no time promises" (GATE-P log round 12, 2026-10-01T04:35:53Z).
**Waived:** SIG-GOV-001's "reachable in one click from any claim" clause, and SIG-GOV-002 in full
(an e-mail discloses the sender's address). **Stands:** SIG-GOV-001's public intake channel — the
e-mail address the dispute page names — accepting all five categories. **Scope:** Round 11.
**Compensating controls:** the dispute and corrections pages name the intake address, say plainly
that senders disclose their address, promise no response time and publish the handling priority (the
SIG-GOV-003 note); every "one-click" and "anonymous" promise is removed and `/intake/` is labelled
not operating; the intake receiver stays non-operational (`503 receiver_not_operating`); Part VIII
and safety takedowns are honoured by the operator through the withdrawal barrier. **Revisit
(ADR-180):** the announcement (a keep/lift answer at GATE-ANNOUNCE); a privacy-harm report, or a
sender harmed by having had to disclose an address; a public intake form opening; the end of Round
11; a second maintainer.

### 45.2 Handling

**SIG-GOV-003 (MUST).** Published SLAs by category, with **privacy-harm and safety claims
prioritized above all others**, including above factual corrections.

**Round-11 waiver — WV-08, the SLA-time clause (ADR-186; recorded 2026-10-01).** The operator waived
this requirement's response-time SLAs in their adopted sentence recorded in ADR-186 (S6-F1, GATE-P
log round 24; agent-drafted, adopted by the operator at 2026-10-01T06:05:22Z; sha256
`806faae385d9…`). **Waived:** "Published SLAs by category" in so far as an SLA is a response-time
commitment — no response time is published or promised. **Met differently:** the priority clause —
the corrections and intake page publishes the handling order: privacy-harm and safety reports first,
then factual corrections, then everything else, with no time commitment
(`MET-DIFFERENTLY(ADR-186)`). **Scope:** every intake channel while ADR-186 stands (in Round 11,
e-mail only — the SIG-GOV-001/002 note). **Compensating controls:** the published order; the e-mail
notice of WV-05; Part VIII and safety takedowns honoured by the operator through the withdrawal
barrier (a 15-minute technical withdrawal). **Revisit (ADR-186):** the first public intake form; the
announcement; a second maintainer.

**SIG-GOV-004 (MUST).** Permitted outcomes: correct; annotate; **suppress from public view while
retaining internally**; delete entirely; or **refuse with published reasoning**. Refusal MUST be a
real, exercisable option — a process that cannot say no is a heckler's veto.

### 45.3 Corrections preserve history

**SIG-GOV-005 (MUST).** A correction is a **new assertion**, never a deletion (SIG-STORE-020,
SIG-TIME-009). A query at a prior `as_of_belief` MUST still return the erroneous value, so a
citation made before the correction remains reproducible and the correction remains visible.

**SIG-GOV-006 (MUST).** Every correction MUST appear in the **public corrections log**
(SIG-UI-032).

### 45.4 Suppression as a distinct primitive

**SIG-GOV-007 (MUST).** **Suppression MUST exist as a primitive distinct from deletion.** An
append-only store with no suppression path forces a destructive delete the first time a valid
privacy demand arrives — which would violate the append-only invariant under pressure, at the worst
possible moment, with no design behind it. *(Corrects an omission in OL-9.2's append-only model.)*

Suppression sets a flag that removes material from public surfaces and exports while retaining it
internally under `sealed` tier, with the decision, its author, and its rationale recorded.

**SIG-GOV-008 (MUST).** True deletion MUST be reserved for material SIG must not hold at all, MUST
require two-person authorization, and MUST leave a tombstone recording that a deletion occurred,
its category, and its date — never its content.

**Round-11 waiver — WV-06, the two-person clause only (ADR-181; recorded 2026-10-01).** The operator
waived two-person authorisation for true deletion in their adopted sentence recorded in ADR-181
(A-23 part 2, GATE-P log round 9; agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z;
sha256 `dbf7a851e9d5…`; chosen over the recommendation to keep it owed). **Waived:** "MUST require
two-person authorization" — the operator alone may authorise a true deletion. **The scope clause and
the tombstone clause stand unchanged:** true deletion is reserved for material SIG must not hold at
all, and every deletion leaves a tombstone recording that a deletion occurred, its category and its
date — never its content; everything outside that scope is suppressed (SIG-GOV-007), not deleted.
**Compensating controls:** each deletion needs the operator's in-ticket go naming the material, is
never pre-authorised and never initiated or run by an agent without that go; it is logged publicly
with its reason in the editorial decision log; the mechanism keeps an internal audit record of the
authorisation and the act; a claim row can be removed only through the one operator-only purge
function (the SIG-STORE-011 note; WV-11, ADR-189). **Revisit (ADR-181):** a second maintainer; a
contested deletion; a deletion requested for material outside this requirement's scope.

**SIG-GOV-009 (MUST).** This is why evidence-store Object Lock is **governance mode, not compliance
mode** (SIG-EVID-006): compliance mode would make SIG's archive unimpeachable *and* make legitimate
removal technically impossible. SIG chooses the capability to remove, and compensates with
transparency reporting.

### 45.5 Disputes without correction

**SIG-GOV-010 (MUST).** A subject who disputes an accurate claim MUST be able to attach a
**response**, published alongside it. Being able to answer is a real remedy, and it costs SIG
nothing but honesty.

### 45.6 Transparency reporting

**SIG-GOV-011 (MUST).** SIG MUST publish periodic counts of requests by category and outcome,
including refusals.

---

## 46. Governance, sustainability, and continuity

### 46.1 Legal entity

**SIG-GOV-012 (MUST).** Before public launch, SIG MUST establish a legal home — a fiscal sponsor or
its own nonprofit — and document what it implies for liability, donations, and legal defence.
Operating a project with this threat profile as an unincorporated individual effort exposes
contributors personally.

**SIG-GOV-013 (MUST).** SIG MUST identify legal-defence resources appropriate to public-interest
research and journalism **before** they are needed.

**Round-11 waiver — WV-01, SIG-GOV-012 and SIG-GOV-013 (ADR-165; recorded 2026-10-01).** The
operator waived both requirements "for now" in their adopted sentence recorded in ADR-165 (A-23 part
1, GATE-P log round 9; agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z; sha256
`b9dc5a9128ac…`). **Waived:** establishing a fiscal sponsor or nonprofit before launch (SIG-GOV-012)
and identifying retained legal-defence resources before they are needed (SIG-GOV-013). SIG's legal
home is the operator as an individual, disclosed on the site; there is no fiscal sponsor, nonprofit
or incorporated entity. **Compensating controls:** the disclosure on the site, in wording the
operator confirms verbatim, which describes the operator no further than the adopted sentence does
until the operator writes that text themselves; public legal-defence referral routes listed (listing
contacts no one), none retained. **Revisit (ADR-165):** the announcement; a first legal demand;
funding; a second maintainer.

### 46.2 Decision-making

**SIG-GOV-014 (MUST).** A published governance document MUST define: who decides schema, ruleset,
and vocabulary changes; how contested claims are adjudicated; a code of conduct with enforcement;
and dispute resolution.

**SIG-GOV-015 (MUST).** An **editorial board** MUST exist for contested claims, officer-naming
decisions (§43.4), and sensitivity classifications, distinct from the technical maintainers. These
are editorial judgments and should not be made by whoever happens to hold commit access.

**Round-11 waiver — WV-02, the editorial board (ADR-164; recorded 2026-10-01).** The operator waived
this requirement in their adopted sentence recorded in ADR-164 (A-23 part 1, GATE-P log round 9;
agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z; sha256 `bee2cd2b1501…`): the
operator holds interim single-maintainer editorial authority over contested claims and sensitivity
classifications, disclosed and never presented as a board. **Compensating controls:** a public,
append-only editorial decision log recording every naming, sensitivity and contested-claim decision
(and every true deletion or purge, as a tombstone entry); officer and person naming stays off and
the web naming gate denies by default (SIG-PUB-008 stands); the Part VIII invariants in code; the
disclosure that no board exists. SIG-GOV-014 is not waived. **Revisit (ADR-164):** a second
maintainer; a naming or sensitivity decision contested publicly; naming of an individual wanted; a
legal-home entity or fiscal sponsor; the operator authorising outside contact.

**SIG-GOV-016 (MUST).** SIG MUST document how it resists capture by any single funder, ideology, or
vendor interest, including a policy on funding sources it will not accept.

### 46.3 Anti-misuse, stated honestly

**SIG-GOV-017 (MUST).** SIG MUST NOT build: a real-time device-liveness feed; a per-person lookup;
an "is a camera watching me right now" surface; or individual-officer tracking as a product
(SIG-API-012, non-goals N1/N3).

**SIG-GOV-018 (MUST).** SIG MUST NOT publish instructions for damaging, disabling, tampering with,
or evading enforcement in the commission of wrongdoing (OL-13.5-02).

**SIG-GOV-019 (MUST).** SIG MUST address the underlying tension **explicitly and in public**,
rather than pretending it does not exist. Mapping surveillance infrastructure does inherently make
avoidance easier. SIG's position is that public knowledge of publicly deployed infrastructure is
legitimate and necessary for democratic oversight; that the same information is already available
to anyone who drives the road and looks; and that the alternative — infrastructure that watches the
public while remaining unknown to it — is the condition the project exists to remedy. The
methodology page MUST say this in SIG's own voice. A project that hides from its hardest question
is not credible on any of its easier ones.

### 46.4 Sustainability

**SIG-GOV-020 (MUST).** SIG MUST define a **degraded-but-alive mode** that runs at approximately
zero marginal cost: static exports, scheduled jobs on free infrastructure, and object storage,
serving the last-published dataset with an honest staleness banner.

**SIG-GOV-021 (MUST).** The degraded mode MUST be **tested**, and its known decay paths documented
— including that free CI schedulers commonly disable dormant scheduled workflows after a period of
repository inactivity, which will silently stop a zero-cost pipeline unless a keepalive is designed
in. A sustainability plan that fails silently is not a plan.

### 46.5 Continuity and succession

**SIG-GOV-022 (MUST).** SIG MUST maintain: geographic mirrors; deposits to Zenodo and Software
Heritage (SIG-EVID-019); an offline distribution path (SIG-EXPORT-009); and a documented plan for
the disappearance of the primary domain.

**SIG-GOV-023 (MUST).** SIG MUST publish a **succession commitment**: if the project ends, the data
and code are released in a form that lets others continue, and the evidence store's OCFL layout
(§17.3) means the archive remains readable **without SIG's software**.

**SIG-GOV-024 (MUST).** SIG MUST offer reciprocal **archival insurance** to single-maintainer
upstream projects (SIG-CONTRIB-013). The need is concrete: the ecosystem's principal audit-analysis
project is **one developer on roughly $80/month who has already faced two vendor takedown attempts,
one still pending**. The failure mode for that project is not indifference or drift — it is a
legal budget mismatch, and it can resolve suddenly. This is not altruism: several of the sources SIG depends on
are one-person efforts, and the relevant vendor domains are excluded from the general web archive
(§22.2). If those projects vanish unmirrored, the historical record vanishes — and SIG's own dataset
loses its provenance chain.

**This requirement is graded MUST rather than SHOULD on the strength of a case observed during this
specification's own research window.** The ecosystem directory the outline designates as SIG's
mechanism for discovering local collaborators (OL-3-02, OL-18-13) ceased to resolve at the DNS level
between 2026-07-28 and 2026-08-20. It had been captured by the general web archive **exactly
once** in its entire history. That single capture is the whole margin by which the directory of
thirteen still-active local research groups — and with it the ecosystem's coordination layer — was
recovered rather than lost. Its community chat room was bound to the same domain and died with it.

Three lessons are encoded elsewhere in this specification as a result: the local-group registry is
seeded from recovered, individually re-verified URLs rather than from names (SIG-INGEST-039);
disappearance is a recorded event rather than a retryable error (SIG-INGEST-009); and the archival
offer is made *before* it is needed, because after is too late. **The projects SIG depends on are
more fragile than the vendors SIG documents.**

**Round-11 status (B-6, Q-E2-12 = a; ADR-171; recorded 2026-10-01).** Not amended and not waived;
owed as a later-phase obligation — see the outreach-timing note in §35.1.

---
