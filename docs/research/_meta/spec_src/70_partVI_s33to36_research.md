# Part VI — Research coordination

The outline calls automatic research-lead generation "one of the most distinctive project
features" (OL-12-00) and says it turns the graph into a research coordination system rather than a
passive database (OL-3-07). This part specifies that machinery.

## 33. Research-task generation

### 33.1 The detector specification language

**SIG-TASK-001 (MUST).** Every task type MUST be declared as data, with all of:

| Field | Meaning |
|---|---|
| `task_type` | Stable slug |
| `detector` | A versioned query over the graph |
| `priority_fn` | How urgency is computed |
| `closing_condition` | **What evidence would close it** — testable |
| `assignee_class` | `field_mapper`, `records_requester`, `document_reviewer`, `analyst`, `local_group`, `curator`, `developer` |
| `effort_estimate` | |
| `dispositions[]` | The permitted outcomes (§33.4) |
| `geographic_scope` | For queue assignment |

**SIG-TASK-002 (MUST).** A task type with no testable `closing_condition` MUST NOT be registered.
"Research this" is not a task; "obtain a document establishing X, or record that the agency states
no such document exists" is.

### 33.2 The task catalog

**SIG-TASK-003 (MUST).** At minimum the following MUST be implemented. The first seven are the
outline's (OL-12-01…07); the remainder are required additions.

| # | Task type | Detector | Assignee |
|---|---|---|---|
| 1 | Missing physical devices | `active_device_count` > `mapped_device_count` | field_mapper / local_group |
| 2 | Missing contract | Deployment evidenced, no procurement evidence | records_requester |
| 3 | Conflicting retention | Policy vs configuration divergence | records_requester |
| 4 | Stale evidence | Currency STALE/HISTORICAL for the predicate class | analyst |
| 5 | Orphaned device | Asset with manufacturer, no operator | field_mapper / records_requester |
| 6 | New sharing node | Organization in a network list, absent from the registry | analyst |
| 7 | Vendor replacement | Cancellation + new deployment in window | analyst |
| 8 | Portal disappeared | Artifact disappearance event | analyst |
| 9 | Portal appeared, no known deployment | New portal, no deployment record | analyst |
| 10 | Contract expiring | `end_date` within N days, no renewal evidence | local_group / analyst |
| 11 | **Sharing asymmetry** | Edge asserted by one side only | analyst |
| 12 | Device/jurisdiction mismatch | Asset in A attributed to B | field_mapper |
| 13 | Retention changed without policy change | Config change, no policy claim | records_requester |
| 14 | Network org without jurisdiction | Org resolved, no jurisdiction | analyst |
| 15 | Adoption without corroboration | Atlas row; no portal, contract, or device | records_requester |
| 16 | Grant with no deployment | Surveillance grant awarded, no follow-up evidence | analyst |
| 17 | Vendor acquisition relink | Acquisition event; products need re-linking | curator |
| 18 | Sole-source / Tier-F support | A claim's only support is `R5`/`R6` | analyst |
| 19 | Long-unverified claim | `unreviewed` beyond threshold | curator |
| 20 | **Link rot** | Artifact URL now 404s | developer / analyst |
| 21 | Re-extraction available | Better parser version exists for stored captures | developer |
| 22 | Candidate duplicate entities | ER tier 4/5 pair | curator |
| 23 | Litigation without docket | Proceeding with no court record link | analyst |
| 24 | Incident with only secondary sources | No `R1`/`R2` support | records_requester |
| 25 | Unmapped vocabulary value | Source value outside the vocabulary | curator |
| 26 | **Authorized but not deployed** | `authorization=authorized` ∧ `physical=not_installed` | analyst |
| 27 | Canceled but installed | `procurement=canceled` ∧ `physical=installed` | field_mapper |
| 28 | Free-trial capability | `operational=active` with no procurement transition | records_requester |
| 29 | Cooperative contract unexplored | Piggyback contract with no master record | document_reviewer |
| 30 | Coverage hole | Jurisdiction with population above threshold and zero evidence | local_group |
| 31 | Unresolved contradiction aging | Open contradiction beyond threshold | curator |
| 32 | Candidate asset awaiting verification | `CandidateAsset` corroborated, unpromoted | field_mapper |
| 33 | **Contract amendment chain incomplete** | A contract's terms are contradicted by a later source (extended `end_date`, changed quantity, exercised renewal) with no `amends_contract` child on file | records_requester |
| 34 | **Sharing snapshot stale** | The newest `configured_access` observation for a deployment exceeds the FAST volatility threshold | records_requester |

**SIG-TASK-004 (MUST).** Every contradiction detector (§31) MUST map to a task type. Detection
without a route to resolution is just an alarm.

### 33.3 Lifecycle

**SIG-TASK-005 (MUST).** `generated → triaged → claimed → in_progress → submitted → verified →
closed`, with `reopened` and `invalidated` transitions.

**SIG-TASK-006 (MUST).** Tasks MUST auto-invalidate when their detector no longer fires — evidence
arriving by another route MUST silently close the task rather than leaving stale work in the queue.

**SIG-TASK-007 (MUST).** Duplicate suppression MUST be by `(task_type, subject)`, and claiming MUST
have a timeout so an abandoned claim returns to the pool.

### 33.4 Dispositions — the queue must be able to shrink

**SIG-TASK-008 (MUST).** Every task MUST support a **disposition vocabulary** richer than "done":

| Disposition | Meaning |
|---|---|
| `resolved_evidence_found` | The evidence was obtained; claims landed |
| `resolved_no_evidence_exists` | Searched; the record does not exist. **Writes a `CoverageRecord`** |
| `blocked_access_denied` | Request denied; records the denial as evidence |
| `blocked_fee` | A fee demand blocks it; records the amount |
| `blocked_awaiting_response` | Filed, pending |
| `not_actionable` | The detector fired on a modelling artifact |
| `superseded` | Another task subsumes it |
| `deferred` | Valid but not now, with a review date |

**SIG-TASK-009 (MUST).** `resolved_no_evidence_exists` MUST write a `CoverageRecord` with
`absence_kind = searched_not_found` and the sources searched. **This is the mechanism by which
negative results become data instead of nothing** — and without it, the queue can only grow, which
is how contributor systems die.

### 33.5 Geographic queues (Q36)

**SIG-TASK-010 (MUST).** A local group MAY **claim a jurisdiction**, which grants visibility,
notification, and priority in queue ordering. It MUST NOT grant exclusivity.

**SIG-TASK-011 (MUST).** Claims MUST expire without renewal, and any contributor MUST remain able
to work any open task. Geographic claiming is a coordination affordance; if it hardens into
territorial gatekeeping it defeats the federation principle, and the expiry is the safeguard.

### 33.6 Anti-abuse

**SIG-TASK-012 (MUST).** Tasks MUST NOT be gamified with public leaderboards ranking contributors
by volume. Volume incentives in an evidence system produce low-quality submissions at scale.
Recognition SHOULD be qualitative and tied to verified contributions.

**SIG-TASK-013 (MUST).** Task generation MUST be rate-limited per subject so that one badly-modelled
entity cannot flood the queue.

### 33.7 The local-group registry

**SIG-TASK-014 (MUST).** SIG MUST maintain its **own** registry of local surveillance-accountability
groups — name, jurisdiction, URL, contact, activity status, claimed queues — and MUST NOT depend on
an external directory's availability. *(The external directory the outline names did not respond
when tested, F1.9.)*

---

## 34. Contributors

### 34.1 Tiers

**SIG-CONTRIB-001 (MUST).**

| Tier | May write | Review requirement |
|---|---|---|
| Anonymous | Submissions to a queue | All reviewed before landing |
| Registered | Claims at `R5`, task dispositions | Sampled review |
| Trusted reviewer | Verify others' submissions; promote candidates | Sampled audit |
| Curator | Human assertions, resolution overrides, sensitivity classification, `Person` creation | Peer review for §43.4 decisions |
| Maintainer | Ruleset, vocabulary, schema | ADR + review |

**SIG-CONTRIB-002 (MUST).** No tier may write a claim without provenance. Contributor submissions
enter at **L0** as evidence (a photo, a document, a report), never directly at L1.

### 34.2 Onboarding

**SIG-CONTRIB-003 (MUST).** Before the contributor system is declared complete, a **moderated
usability study** MUST be run with at least five participants who have no prior knowledge of the
ontology, measuring time from landing page to accepted first contribution. The **median MUST be at
or under ten minutes**, and the study protocol and results MUST be published. Re-run on any change
to the contribution flow.

The intended path is: pick a nearby open task, or submit an observation with a photo and a
location.

**SIG-CONTRIB-004 (MUST).** For **device observations specifically**, SIG MUST route contributors
to OSM/DeFlock rather than capturing the observation itself (non-goal N7, OL-1.2-03). SIG's own
capture is for the things OSM does not hold: operator evidence, signage, contracts, agenda items.

### 34.3 Safety

**SIG-CONTRIB-005 (MUST).** SIG MUST NOT collect or retain: precise contributor geolocation beyond
the submitted observation; contributor real names as a requirement; device identifiers; or IP logs
beyond a short operational window. **What is not stored cannot be subpoenaed**, and this is a
design requirement, not a preference.

**SIG-CONTRIB-006 (MUST).** Pseudonymous contribution MUST be fully supported, including for
trusted-reviewer tier.

**SIG-CONTRIB-007 (MUST).** SIG MUST publish know-your-rights guidance for lawful photography in
public, and MUST explicitly instruct contributors not to trespass, tamper, or interfere
(non-goal N5, OL-13.5-02). Guidance MUST be jurisdiction-aware.

**SIG-CONTRIB-008 (MUST).** SIG MUST have a published policy for what it does if a contributor is
detained, arrested, or harassed in connection with contributing — including who to contact and what
SIG will and will not disclose.

### 34.4 Vandalism and poisoning resistance

**SIG-CONTRIB-009 (MUST).** Every contribution MUST be revertible as a unit, with the revert
recorded as a new assertion (never a deletion).

**SIG-CONTRIB-010 (MUST).** Anomaly detection MUST run on contribution patterns — bursts, coordinated
similar submissions, submissions that conveniently resolve contested claims — and MUST route to
review rather than auto-reject.

**SIG-CONTRIB-011 (MUST).** A coordinated campaign asserting *false absence* (that a deployment
does not exist) is as damaging as one asserting false presence, and MUST be equally guarded. This
threat is easy to overlook because it looks like helpfulness.

**SIG-CONTRIB-011a (MUST).** The **vendor operating-territory check** is a first-class plausibility
rule: a claim that vendor V operates a device in country or region C, where SIG holds no independent
evidence that V operates in C at all, MUST be held at the lowest confidence and MUST generate a
verification task rather than entering the graph as an observation.

**This threat is observed, not hypothetical, and it is currently active** (R12-F12.28). As of
2026-08-17 the OSM community was dealing with fabricated ALPR nodes across Canada, Germany, Poland,
the UK and Northern Ireland — devices attributed to a vendor in countries where it does not operate,
in locations including inside a shopping mall, an apartment courtyard, and a church. The dominant
live failure mode in this domain is therefore **inflationary**: panic-driven or adversarial
*over*-reporting, not under-reporting. A data-quality model that assumes honest error will not catch
it.

**SIG-CONTRIB-011b (MUST).** SIG MUST NOT be the proximate cause of a mass revert. Community
members have publicly proposed bot-removal of implausible nodes; any SIG-fed suggestion later judged
implausible would risk a revert that damages SIG, the mapper who applied it, and the upstream
project that relayed it. This is the strongest operational argument for the
suggestion-not-write posture of SIG-CONTRIB-015, independent of the licensing and
code-of-conduct arguments.

**SIG-CONTRIB-011c (MUST).** SIG MUST NOT render an unverified community observation with the same
visual weight as a records-derived claim. The ecosystem has independently converged on this remedy —
affected projects responded to the incident by adding provenance disclaimers, restricting default
views to confirmed devices, and prompting for a source before submission. That convergence is
corroboration that §10.7's explainable-confidence model is the right one, arrived at from the
opposite direction.

---

## 35. Contribution back to the ecosystem

### 35.1 Stage 0 outreach

**SIG-CONTRIB-012 (MUST).** Before any connector is written for an ecosystem project, SIG MUST have
attempted contact and recorded the outcome (SIG-CHART-033, SIG-INGEST-029), using a published
template that states: what SIG is; what it wants; **what it will not do** (non-competition,
non-duplication, no re-hosting of their differentiator); what it offers (corrections upstream,
traffic, targeted research tasks, methodology co-authorship, mirroring); and an explicit opt-out.

**SIG-CONTRIB-012a (SHOULD).** Where an upstream project has **publicly asked for help with a
problem SIG is already solving**, that request SHOULD be the opening offer, ahead of any data ask.

A concrete, dated instance exists: during the fabricated-node incident of SIG-CONTRIB-011a, a
maintainer publicly stated they would *"love to have more eyeballs"* on their internal monitoring
tool for implausible submissions. That is precisely the plausibility detector SIG builds anyway
(§34.4). The correct first approach is therefore to **offer to run those checks at graph scale and
feed the results back, free, with no attribution required and no reciprocal data access requested**.

This is also the cheapest possible demonstration of the federation compact: it gives before it asks,
it improves the upstream commons (P5), and it costs SIG nothing it was not already building.

**SIG-CONTRIB-013 (MUST).** The offer MUST include **archival succession**: SIG will hold a mirror
that survives the project's disappearance, on terms the project sets. Several of these projects are
single-maintainer efforts, and the relevant vendor domains are excluded from the general web
archive (§22.2) — so if these projects vanish, the record vanishes with them. This is one of the
most valuable things SIG can offer, and it costs SIG almost nothing.

### 35.2 To OpenStreetMap (Q33)

**SIG-CONTRIB-014 (MUST NOT).** SIG MUST NOT perform direct automated writes to OSM
(REQ-R1-13).

**SIG-CONTRIB-015 (MUST).** Contribution back MUST go through a **human-mediated suggestion
workflow** — a task challenge that a human mapper reviews and applies, in their own account, with
their own judgment. SIG supplies the evidence (a contract naming the operator, a council document,
a signage photo); the mapper decides.

**SIG-CONTRIB-015a (SHOULD).** The verified mechanism is a **MapRoulette cooperative challenge**.
Its API is live and its object model fits SIG's requirements directly (SC-15):

| SIG requirement | MapRoulette field |
|---|---|
| The mandatory changeset hashtag (SIG-CONTRIB-016e) | **`checkinComment`** |
| Originating-tool attribution | `checkinSource` |
| Surfacing the evidence to the mapper | `instruction`, `description`, `blurb` |
| Task priority (§33.1) | `defaultPriority`, `highPriorityRule`, `highPriorityBounds` |
| Geographic queues (§33.5) | `highPriorityBounds`, `isGlobal` |
| The §7 leverage metric | `completionMetrics`, `completionPercentage` |
| Task retirement (§33.3) | `isArchived`, `deleted`, `enabled` |

**`cooperativeType` is the decisive capability.** A cooperative challenge proposes a *specific tag
change* the mapper accepts, rejects, or edits — rather than sending them to edit freehand. That is
exactly the operator-attribution case: *"this node has no `operator`; SIG's evidence suggests
`operator=X`; decide."* It preserves individual human review, which is what keeps SIG outside the
Automated Edits Code's scope (SIG-CONTRIB-016b), while reducing the mapper's cost to roughly one
decision per device — the objective SIG-CONTRIB-017a sets.

**SIG-CONTRIB-015b (MUST).** Phase 16 MUST locate the current MapRoulette API documentation (the
expected `swagger.json` and docs-site URLs both returned 404 when checked) and establish who holds
SIG's MapRoulette account, since challenge creation requires authentication and that account falls
under the Organised Editing disclosure (SIG-CONTRIB-016d).

**SIG-CONTRIB-016 (MUST).** The compliance analysis MUST be recorded as an ADR (ADR-017). The
Automated Edits Code of Conduct has now been **read and analysed** (SC-12); the analysis below is
normative and supersedes the earlier open item.

**The scope test is the whole answer.** The Code of Conduct covers *"all edits where changes are
made to objects in the database **without review individually by the person controlling the
edits**"* — and it explicitly names Overpass-driven bulk retagging and "manually changing tags
without adequate review". Ignoring it *"will be treated as vandalism"*.

**SIG-CONTRIB-016a (MUST).** Operator attribution is **not** covered by any of the Code's
exceptions. Those are limited to blatant typos, reverting vandalism, correcting one's own work, and
reverting unapproved automated edits; the Code states that disagreeing with a tagging schema *"does
not count as typo"*. Adding `operator=*` from contracts and public records is new information from
an external source, which additionally engages the OSM import guidelines. At ~116,800 candidate
nodes it is unambiguously in scope.

**SIG-CONTRIB-016b (MUST).** Therefore the human-mediated suggestion workflow of SIG-CONTRIB-015 is
**not a cautious alternative to compliance — it is what keeps SIG outside the policy's scope
entirely.** A mapper reviewing each proposed change individually, in their own account, exercising
their own judgment, is by definition not making an automated edit. SIG supplies evidence; a person
decides. That is the compliant architecture, and there is no version of a SIG bot account that is
simpler.

**SIG-CONTRIB-016c (MUST).** If SIG ever proposes a genuinely bulk contribution, it MUST first
satisfy every documented requirement: a proposal page under `Automated edits/<username>` naming a
contactable human, the motivation, **the exact selection algorithm**, the consultation record, the
cadence, and **an opt-out mechanism**; registration in the automated-edits log; and a **permanent
record of community discussion and decision on an OSMF-run forum or wiki** — chat-platform
consensus explicitly does not count. Approval is **never blanket**: any later extension of scope
requires fresh community approval.

**SIG-CONTRIB-017 (MUST).** Operator attribution — the ~116,800-device backlog — is the
highest-value contribution SIG can make upstream, and the ODbL posture (§42.3) obliges SIG to share
it anyway. The licence and the mission point the same way here.

**SIG-CONTRIB-016d (MUST).** Escaping the Automated Edits Code of Conduct does **not** escape the
**Organised Editing Guidelines**, which apply to *"any edits that involve more than one person and
can be grouped under one or more sizeable, substantial, coordinated editing initiatives"* (SC-14).
A SIG-run task challenge directing volunteers at the orphaned-device backlog is squarely in scope.
SIG MUST therefore publish an activity page under `Organised Editing/Activities/`, registered in the
activities list, disclosing: the coordinating organisation and a contact; **a unique changeset
hashtag**; the goal and why it is pursued; the timeframe; **every non-standard tool and data source
with its usage conditions**, and links to them; participating accounts that wish to be identified;
any performance metrics used; and any training material issued.

**SIG-CONTRIB-016e (MUST).** SIG MUST declare a **changeset hashtag** and require it on every edit
originating from a SIG task. This is not merely compliance — it is the measurement instrument for
the §7 leverage metric *"SIG-originated operator-attribution suggestions accepted upstream"*, which
is otherwise unmeasurable except by inferring SIG's own influence from tag-count deltas. A declared
hashtag makes SIG's contribution stream **publicly auditable by third parties, including by SIG's
critics**, which is precisely the property that makes the metric credible. The same mechanism is how
SIG identifies *other* projects' organised edits.

**SIG-CONTRIB-016f (MUST).** The disclosure obligation *"any non-standard tools and data sources
used, and their usage conditions"* imposes a **licence gate on the contribution path**, distinct
from the export gate of §42.4. A source whose terms do not permit deriving an OSM edit from it MUST
NOT be surfaced in a contribution task at all, and the task builder MUST check this before
rendering. Publishing a task that invites a mapper into a licence breach would make SIG the
proximate cause of it.

**SIG-CONTRIB-016g (MUST).** Where the guidelines require *"a description of the metrics used"* for
participant performance, SIG's disclosure MUST state that it measures **task outcomes, not
contributor rankings**, consistent with §33.6's prohibition on volume gamification.

**SIG-CONTRIB-017a (MUST).** The binding consequence, which MUST shape the roadmap rather than be
discovered later: **SIG cannot clear this backlog mechanically.** Throughput is bounded by mapper
attention, not by compute. The design objective is therefore to **minimize the human cost per
resolution** — presenting the device, the candidate operator, the supporting contract or record, and
the jurisdiction together in one reviewable unit — and MUST NOT be to maximize automated write
volume. A contribution surface that makes one device resolvable in fifteen seconds is worth more
than any bot SIG is permitted to run.

### 35.3 To other projects (Q34, Q35)

**SIG-CONTRIB-018 (MUST).** SIG MUST maintain per-project correction export formats, and MUST use
each project's own stated submission channel rather than inventing one.

**SIG-CONTRIB-019 (MUST).** Where a research task's closing evidence is a public record, SIG MUST
be able to emit a **ready-to-file records request** (§36) and to record the resulting request as a
`RecordsRequest` linked back to the task.

**SIG-CONTRIB-020 (MUST).** Attribution reciprocity MUST be structural: every claim's upstream is
named in the UI, in API responses, and in exports. Aggregate acknowledgement on an About page is
not sufficient (OL-1.2-08).

---

## 36. Records-request generation

**SIG-TASK-015 (MUST).** Given a research gap, SIG MUST be able to emit a ready-to-file request
with: the correct target agency and its records contact; the correct **statutory citation for that
jurisdiction**; proven request language for the record type; and the specific records sought.

**SIG-TASK-016 (MUST).** SIG MUST maintain a per-jurisdiction records-law reference table covering
all **51 US jurisdictions**: statute name and citation, initial response deadline, fee rules, appeal
path, and whether a **requester-residency requirement** applies.

**SIG-TASK-016a (MUST).** The residency field is **operationally binding, not informational.** Six
states restrict public-records requests to their own residents — **Alabama, Arkansas, Delaware,
Kentucky, Tennessee, and Virginia** — and at least one grants agencies an express right to demand
proof of residency (R12-F12.26). In those jurisdictions a non-resident's request is not merely
likely to fail; it is not a valid request.

Therefore the request generator MUST:

1. **Refuse to emit** a request naming a non-resident filer for a residency-restricted jurisdiction,
   rather than emitting one that will be rejected.
2. **Route the task to the geographic queue** for that jurisdiction (§33.5), where a local
   contributor or partner group can file it. This is the point at which the local-group registry
   (SIG-INGEST-039) stops being a directory and becomes **load-bearing infrastructure**: in six
   states, SIG's records-acquisition capability is *exactly* its local-contributor coverage.
3. **Record the constraint as a coverage fact**, so that thin evidence in a residency-restricted
   state is attributed to the legal barrier rather than read as an absence of surveillance
   (§9.5, §32.2).

**SIG-TASK-016b (MUST).** Where the residency position could not be determined it MUST be recorded
as unknown and MUST default to the restrictive behaviour — route to a local filer — rather than
assuming openness.

**SIG-TASK-017 (MUST).** Request templates MUST be versioned and their **success rates measured**.
Templates that produce denials should be revised, and knowing which language works is itself a
research finding worth publishing.

**SIG-TASK-018 (MUST).** SIG MUST NOT file requests on a contributor's behalf without explicit
consent, and MUST make clear that a filed request is a public act attributable to the filer in most
jurisdictions.

---
