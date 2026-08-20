## 29. The reconciliation workflows

### 29.1 Camera-count reconciliation

Discharges OL-11.1-01, OL-11.1-02, OL-11.1-03.

**SIG-RECON-026 (MUST).** The count predicates MUST be **distinct and never conflated**. The
outline's §11.1 (OL-11.1) nearly collapses them; the collapse is the error the whole workflow exists to
prevent.

| Predicate | Means | `D1` source | Volatility |
|---|---|---|---|
| `contracted_device_count` | Quantity the contract obliges | Executed contract | IMMUTABLE per contract |
| `invoiced_device_count` | Quantity actually billed | Invoice | IMMUTABLE per invoice |
| `installed_device_count` | Physically mounted, working or not | Inventory; field survey | MODERATE |
| `active_device_count` | Producing data now | Portal; audit `Camera Count`; vendor statement | FAST |
| `mapped_device_count` | Independently field-observed and mapped | OSM/DeFlock | **A lower bound only** |
| `claimed_device_count` | What someone said in public | Press release; council presentation | FAST |

**SIG-RECON-027 (MUST).** `mapped_device_count` MUST be treated as a **lower bound**, never as an
estimate of the true count. Mapping coverage is opportunistic and incomplete by construction.

**SIG-RECON-028 (MUST).** Phase 2.3 MUST refuse to compare claims with different `count_basis`,
emitting `PREDICATE_CONFLATION` instead.

**The worked case, and why it dissolves.** The outline's own Appendix B presents "42 contracted vs
38 portal-reported vs 31 mapped" as a contradiction to be resolved. Under this model it is **not a
contradiction at all**. The contract's 42 is `contracted_device_count` at `W4` (R1 · D1 · I1 · C1,
since contract quantity is IMMUTABLE). The *same artifact* for `active_device_count` is R1 · **D5**
· I1 · C3 → **W1**. The portal's 38 is R2 · D1 · I1 · C1 → **W3**, and wins `active_device_count`
by two weight classes. The OSM 31 is a lower bound on a third predicate.

So there are three correct answers to three different questions — plus **one genuine finding**: an
unresolved delta of 4 between contracted and active, and a gap of at least 7 between active and
mapped. Those deltas are the research tasks. This is what the outline means by "reconciliation, not
aggregation," made mechanical.

**SIG-RECON-029 (MUST).** The output object MUST carry every count predicate with its own
resolution, plus `unresolved_delta` values with their interpretation, plus the evidence for each,
plus the generated research tasks. It MUST NOT emit a single "true count."

### 29.2 Device attribution

Discharges OL-11.2-01, OL-11.2-02. This is the workflow that addresses the ~116,800 mapped ALPRs
with no operator (SC-08.1).

**SIG-RECON-030 (MUST).** Candidate generation MUST consider: spatial containment in a
jurisdiction; distance to the nearest deployment of a matching technology; road-network context
(a device on a county road inside a city is ambiguous by construction); jurisdiction adjacency;
manufacturer/vendor match against the deployment's product; and unexplained count gaps in the
jurisdiction (a deployment with 8 unmapped devices makes nearby orphans more likely to be its).

**SIG-RECON-031 (MUST).** Output MUST be an **inference at L4**, labelled `probable`, never an
observation. It MUST NOT be written into the asset's `operator` as though observed, and MUST NOT be
pushed to OSM automatically (§35.2).

**SIG-RECON-032 (MUST).** The hard cases MUST be modelled rather than resolved by default:

| Case | Required handling |
|---|---|
| Device on a county road inside city limits | Multiple candidate operators; do not default to the containing jurisdiction |
| State-police device inside a city | Containment is not attribution |
| Device operated by A on behalf of B | Both roles recorded (§12.4); attribution names the *role* it attributes |
| Multi-agency shared deployment | Multiple operators is a valid answer, not a conflict |
| Device on a jurisdiction boundary | Ambiguous by construction; enqueue rather than pick |

**SIG-RECON-033 (MUST).** Promotion from `probable` to asserted requires human confirmation or a
`D1`/`D2` documentary source. A high inference score MUST NOT promote itself.

### 29.3 Sharing-edge reconciliation

Discharges OL-11.3-01, OL-11.3-02.

**SIG-RECON-034 (MUST).** The three edge types of §12.2 MUST be reconciled **separately**. There is
no operation that merges them.

**SIG-RECON-035 (MUST).** **Asymmetry is a finding, not an error.** Where A's configuration export
lists B, and B's export does not list A, SIG MUST record both observations, emit a
`SHARING_ASYMMETRY` contradiction, and generate a research task. Possible explanations — one export
is stale, one direction was disabled, the exports have different semantics, one organization is
misidentified — are all interesting, and picking one silently destroys the signal.

**SIG-RECON-036 (MUST).** A sharing edge from a single snapshot carries `valid_from_kind =
'unknown'` (SIG-ONTO-044). SIG MUST NOT infer a start date from first observation.

**SIG-RECON-037 (MUST).** An `observed_use` edge MUST NOT create or imply a `configured_access`
edge, and vice versa — even though use logically implies access existed at the time of use. The
inference is available at L4, clearly labelled; it is not permitted at L1.

### 29.4 Deployment lifecycle reconciliation

Discharges OL-11.4-01, and the §22.5 requirement to distinguish removal from replacement.

**SIG-RECON-038 (MUST).** Each of the four tracks (§13.4) MUST be resolved **independently** at each
point in time. A single-timeline reconciliation is impossible because the tracks are orthogonal.

**SIG-RECON-039 (MUST).** Event-log transitions, where available, are the highest-quality evidence
and MUST be preferred over inferred transitions (REQ-R2-09).

**SIG-RECON-040 (MUST).** Fuzzy-dated events MUST be ordered using EDTF envelopes, and where two
events' envelopes overlap such that their order is indeterminate, the timeline MUST record them as
**unordered-within-window** rather than picking an order.

**SIG-RECON-041 (MUST).** The vendor-replacement pattern MUST be detected and rendered explicitly:
where a deployment reaches `procurement:canceled|nonrenewed` and another deployment of the same
technology family begins at the same organization within a configured window, SIG MUST create a
`replaced_by` edge and MUST render the pair as **"vendor replaced"**, never as "surveillance
removed."

**SIG-RECON-042 (MUST).** Where `procurement:canceled` coexists with `physical:installed`, the UI
and API MUST state both plainly: *"contract canceled; hardware still present as of <date>."* This
is the single most politically consequential distinction the system makes (OL-22.5-02), and it MUST
NOT be smoothed into either summary.

### 29.5 Retention reconciliation

**SIG-RECON-043 (MUST).** `policy_written_retention_days`, `configured_retention_days`, and
`vendor_default_retention_days` are **three predicates**. Their disagreement is a finding (P10).
Vendor defaults MUST NOT populate configuration (SIG-ONTO-036), and a vendor's default change does
not retroactively change existing deployments — a distinction that has real-world instances.

### 29.6 Policy-versus-configuration reconciliation

**SIG-RECON-044 (MUST).** SIG MUST detect and surface policy/configuration divergence as a
first-class finding, with both sides' evidence, and MUST NOT editorially collapse it
(OL-8.12-02). The canonical instance — a written policy prohibiting immigration-related use
alongside an enabled immigration hotlist — MUST be expressible and renderable.

### 29.7 Snapshot-diff reconciliation

**SIG-RECON-045 (MUST).** Consecutive captures of the same artifact MUST be diffed at the
**extracted-field level**, producing per-field change events with both values and both dates. This
is what makes "what changed, and when" answerable, and it is the basis of the change feed and of
several research-task detectors.

### 29.8 Additional workflows

**SIG-RECON-046 (MUST).** The following MUST also be implemented: **cost/contract-value**
reconciliation (contract vs invoices vs budget line vs cooperative SKU pricing);
**organization-existence** reconciliation (an organization named in a network list that no registry
knows — §14.4); **capability** reconciliation (does org X have capability Y, across disagreeing
sources, respecting the marketed-vs-configured distinction of SIG-ONTO-018); and
**geographic-coverage** reconciliation.

---

## 30. The inference layer

**SIG-RECON-047 (MUST).** Inferences live at L4 in a separate namespace, carry `derivation_rule`,
`derived_at`, and `input_claim_ids`, are labelled in every surface, and are droppable and
recomputable (§8.1, SIG-GEO-006).

### 30.1 The inference catalog

| Inference | Inputs | Confidence treatment | Invalidation trigger |
|---|---|---|---|
| Device→deployment attribution | §29.2 | Never above `probable` without human confirmation | Any input claim changes |
| Field-of-view geometry | Asset point + direction + mount + assumed optics | Always labelled modelled; assumptions published | Asset geometry or direction changes |
| Jurisdiction assignment | Asset geometry + jurisdiction boundary | High, but boundary-temporal | Boundary or geometry changes |
| Org hierarchy transitivity | `parent_of` chains | High; bounded depth | Any edge changes |
| **Access-path closure** | Access + integration edges | See §30.4 | Any edge on the path changes |
| Network centrality | Resolved edges | Gated on ER quality (P6) | Any edge changes |
| Product-default capability | `Product.can_offer` | `product_default`, low (SIG-ONTO-018) | Configuration evidence arrives |
| Coverage estimates | §32 | Explicit method disclosure | Any input changes |

### 30.2 Access-path closure — SIG's most powerful and most dangerous inference

**SIG-RECON-048 (MUST).** "Can organization A reach organization B's data, through any chain?" is
the transitive-closure question that OL-22.4-01 identifies as central. It MUST be implemented,
and it MUST be bounded.

**SIG-RECON-049 (MUST).** Closure MUST obey these limits:

1. **Only `configured_access` and `federates_search_to` edges compose.** `observed_use` does not
   compose — that A searched B and B searched C does not mean A can search C.
2. **`distributes_list_to` does not compose in the query direction.** A hotlist flowing outward
   creates no inbound search path (§12.3 rule 3).
3. **Scope must be respected.** A partner-scoped edge does not chain into a national-scoped one.
4. **Every hop must be currently valid** at the as-of time; a path through an expired edge is a
   *historical* path and MUST be labelled as such.
5. **Path length MUST be capped and reported.** Every published path MUST show its full hop list
   with each hop's evidence. An unexplained "A can reach B" is exactly the "unexplained edge" the
   defining standard forbids.
6. **Confidence is the minimum over the path**, never the average — a chain is as strong as its
   weakest hop.

**SIG-RECON-050 (MUST).** Beyond a published hop count, closure output MUST be labelled
**speculative** and excluded from headline figures. The difference between "these two agencies
share data" and "a seven-hop theoretical path exists" is the difference between a finding and an
insinuation, and SIG must not blur it — including when the blurred version would be more striking.

### 30.3 Prohibited inferences

**SIG-RECON-051 (MUST NOT).** SIG MUST NOT infer: any natural person's identity, location, or
movements; that a device is active because it exists; that configuration matches policy; that a
vendor default applies to a specific deployment; that absence of evidence is evidence of absence;
that a candidate asset is real; or that an organization's surveillance posture resembles its
neighbours'.

### 30.4 Labelling

**SIG-RECON-052 (MUST).** Every inference MUST be visually and structurally distinguishable from
observation in the UI, the API, and every export — including derived map layers, where the
distinction must survive at a glance (§39.1).

---

## 31. Contradiction as a first-class object

Discharges OL-6.5-01, OL-6.5-02, OL-24-11.

**SIG-RECON-053 (MUST).** `Contradiction` MUST be a materialized entity with:

| Field | Notes |
|---|---|
| `subject_id`, `predicate_id` | What is disputed |
| `contradiction_type` | `value_disagreement`, `predicate_conflation`, `value_domain_mismatch`, `sharing_asymmetry`, `policy_configuration_divergence`, `temporal_impossibility`, `count_basis_mismatch`, `identity_ambiguity`, `undeclared_copying` |
| `claim_ids[]` | The disagreeing claims |
| `severity` | `informational`, `notable`, `blocking` |
| `status` | `open`, `under_research`, `resolved`, `accepted_unresolvable`, `superseded` |
| `resolution_note`, `resolved_by`, `resolved_at` | |
| `research_task_ids[]` | What was generated to close it |

**SIG-RECON-054 (MUST).** `severity = blocking` MUST force `UNRESOLVED` (`U7`). This is the manual
brake: a curator who believes a value is unsafe to publish can stop it without deleting anything.

**SIG-RECON-055 (MUST).** A resolved contradiction MUST remain **visible in history**. Resolution
sets status; it does not delete (OL-24-20).

**SIG-RECON-056 (MUST).** `accepted_unresolvable` MUST be a legitimate terminal state. Some
disagreements cannot be settled with available evidence, and saying so is more honest than an
indefinite open task.

**SIG-RECON-057 (MUST).** Every contradiction detector MUST emit a research task with a defined
closing condition (§33.3). The detector→task contract is what turns disagreement into work
(OL-6.5-02).

---

## 32. Coverage, completeness, and quality metrics

Discharges Goal 6 (OL-7.1-06) and the negative-claims doctrine (OL-9.4).

### 32.1 The coverage record

**SIG-METRIC-001 (MUST).** `CoverageRecord` MUST make negative claims **queryable**:

| Field | Notes |
|---|---|
| `subject_id` / `subject_class` | An entity, or a class within a jurisdiction |
| `predicate_id` | What was sought |
| `absence_kind` | `not_researched`, `searched_not_found`, `evidence_of_absence`, `not_applicable` |
| `sources_searched[]` | **Required for `searched_not_found`** |
| `searched_at`, `searched_by` | |
| `search_method` | |

**SIG-METRIC-002 (MUST).** "Not in the Atlas" and "not in the Atlas, not in any portal, and not in
three years of council minutes" are very different statements, and `sources_searched[]` is what
distinguishes them (§9.5). Without it, coverage is rhetoric.

**SIG-METRIC-002a (MUST).** Discovery probes MUST **retain their negatives**. Where SIG enumerates a
candidate identifier space — portal slugs, agency identifiers, tenant names — every probe that
returned "does not exist" MUST be stored as a `CoverageRecord` with `absence_kind =
searched_not_found`, not discarded.

This is not bookkeeping. An ecosystem project's published database demonstrates the value directly:
it retains **5,011 confirmed-absent slugs alongside 495 confirmed-present ones** (R2-F2.15). The
negatives are what convert "we found 495 portals" into "we tested 5,506 candidates and 495 exist" —
which is a denominator (SIG-METRIC-003), a measure of enumeration completeness, and a way to detect
a *new* portal appearing later without re-probing the entire space. Discarding negatives throws away
the more informative half of the result.

### 32.2 Published denominators

**SIG-METRIC-003 (MUST).** **Every** published aggregate MUST carry its denominator and the count
excluded for lack of evidence. "37 agencies share data outside their state" is non-conformant.
"37 of 214 evaluable agencies; 1,109 not evaluable for lack of evidence" is conformant.

**SIG-METRIC-004 (MUST).** Per-jurisdiction coverage MUST be computed and published: agencies
known; agencies with any deployment evidence; deployments with contract evidence; with portal
evidence; with mapped devices; mean evidence age; open contradiction count; and the claim
weight-class distribution.

### 32.3 Provenance completeness

**SIG-METRIC-005 (MUST).** The share of published claims with a resolvable evidence artifact MUST
be measured, published, and **targeted at 100%**. Any shortfall is a defect list, not a statistic.

### 32.4 Freshness

**SIG-METRIC-006 (MUST).** Freshness MUST be measured **relative to predicate volatility**, not in
absolute days. A two-year-old contract date is fresh; a two-year-old active count is historical.

**SIG-METRIC-007 (MUST).** A public data-freshness page MUST show, per source: last successful
run, last content change, current status, and the count of entities whose evidence is stale for
their predicate class. A freshness dashboard is itself a trust affordance.

### 32.5 Completeness estimation — and why capture–recapture is prohibited

**SIG-METRIC-008 (MUST NOT).** SIG MUST NOT publish a capture–recapture estimate of device
population from volunteer mapping and vendor portal reporting. **Not with a caveat, not with a wide
interval.** *(This supersedes an earlier permissive formulation; the correction is R13 §12.4.)*

The Lincoln–Petersen estimator `N̂ = n₁n₂/m₂` fails here on four counts, and the first is
dispositive on its own:

1. **Linkage is impossible, so `m₂` is undefined.** Recapture requires knowing *which* individuals
   appear in both samples. Transparency portals publish a **count, not an inventory** — no device
   identifier, no location, no matchable attribute. Estimating `m₂` from the two totals assumes the
   answer. No version of the analysis survives this.
2. **Closure fails.** `active_device_count` is FAST (six-month half-life). Any window wide enough to
   accumulate both lists exceeds the closure horizon, and the samples are not even contemporaneous:
   an OSM observation time is an *edit* time, a systematically optimistic upper bound on when a
   human actually looked.
3. **Independence fails, in the worst direction.** Portal publication is opt-in and self-selected;
   agencies that publish are disproportionately those under local scrutiny — which is also where
   volunteer mappers are. The capture probabilities are **positively correlated**, which inflates
   `m₂` and therefore **deflates `N̂`**. The estimator would not be noisy; it would be **biased low
   by an unknown amount**. A public-interest project must not publish a number whose known failure
   mode is *understating the thing it exists to document*.
4. **Capture heterogeneity is structured and shared.** Roadside survey misses rear-facing,
   obscured, and private-property devices; portal reporting misses whatever the vendor does not
   instrument. Both blind spots track the same urban/rural and salience gradients.

**SIG-METRIC-008a (MUST NOT).** Multi-list log-linear models MUST NOT be used as a rescue. They
require three or more lists **with individual-level linkage**, and they cannot identify the
highest-order interaction — which is precisely the one that matters here, since every available list
shares a single latent "public visibility" factor.

**SIG-METRIC-008b (MAY).** There is exactly one legitimate application. Where SIG holds a
**records-derived installation list with locations** for a specific jurisdiction — the only true
device-level inventory available in this domain — a two-sample estimate against a **blind** field
survey of that jurisdiction is defensible, because linkage is possible and the processes are
genuinely independent when the survey is conducted without sight of the list.

Even then it MUST be understood and labelled as measuring **the field survey's recall in that
jurisdiction**, not the device population. It MUST be pre-registered, conducted inside a window
shorter than the predicate's half-life, and published as a **measurement of SIG's method**. It MUST
NOT be extrapolated to any other jurisdiction. Validation exercises do not extrapolate.

**SIG-METRIC-009 (MUST).** What SIG publishes instead: counted quantities with **named
denominators**; records-derived **bounds** where an inventory exists; per-agency reconciliation
ratios; and measured survey recall on a named calibration subset. **Never a total.**

**SIG-METRIC-010 (MUST NOT).** SIG MUST NOT publish a completeness percentage that implies it knows
the denominator of reality. The defensible claim is coverage of *known* entities plus an explicit
statement that the true population is unknown (SIG-CHART-019).

### 32.6 Ecosystem leverage metrics

**SIG-METRIC-011 (MUST).** The leverage measures of §7 MUST be instrumented and published, because
the project's stated definition of success depends on them and an unmeasured goal is a slogan.

---
