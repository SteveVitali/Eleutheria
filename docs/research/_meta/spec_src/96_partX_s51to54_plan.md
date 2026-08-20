# Part X — The implementation plan

## 51. Phasing

### 51.1 Philosophy

**SIG-ENG-030 (MUST).** Every phase in §51.2 MUST declare which risk-register entries (§53) it
retires or reduces, and each of the four critical risks R-01…R-04 MUST be named by at least one
phase at or before Phase 6. A phase plan in which a critical risk is unretired by Phase 6 fails
review.

*Rationale (not itself testable).* The ordering principle is risk retirement rather than visible
value; the declaration requirement above is how conformance to it is checked.

Four things can kill this project, and all four are resolved or materially de-risked by Phase 6:

1. An ODbL mistake that makes the dataset unpublishable.
2. Entity resolution that silently corrupts every network statistic.
3. A claim/temporal model that cannot express contradiction.
4. Upstream projects declining collaboration — which, given that the Flock portal layer has no
   lawful automated access path (F2.1), determines whether a core layer exists at all.

Five further principles:

- **The ontology is code before it is data.** Schema-as-source-of-truth generates DDL, JSON Schema,
  RDF, types, and docs; vocabulary changes are versioned migrations.
- **Nothing is populated before it can be proven.** No connector lands claims before the evidence
  store, lineage, and licence gate exist.
- **One vertical slice early.** After the first two connectors, a single jurisdiction is driven
  end-to-end through J-1 — to *falsify the design* before it is replicated twenty thousand times.
- **Internal surfaces precede public ones.** The curation UI is required by ER review long before
  the public site.
- **Every phase ends green.** Build, tests, data-quality checks, and the acceptance queries in
  scope all pass.

### 51.2 The phases

| Ph | Name | Outline stage | Retires |
|---|---|---|---|
| **0** | Foundations, governance, ecosystem coordination | Stage 0 | Risk 4 |
| **1** | Ontology as code + vocabularies | — | Ontology churn |
| **2** | Bitemporal claim + evidence spine | — | Risk 3 |
| **3** | Identity registry + deterministic ER | Stage 1A | Risk 2 (part 1) |
| **4** | Connector framework + OSM + Atlas | Stage 1B/1C | Risk 1 |
| **5** | Probabilistic ER + review queue + curation UI | Stage 1A | Risk 2 (part 2) |
| **6** | **Vertical slice: one jurisdiction end-to-end** | — | Design falsification |
| **7** | Records, procurement, document parsing | Stage 1F | — |
| **8** | Reconciliation engine + contradictions | Stage 2 | — |
| **9** | Coverage, completeness, negative space | — | — |
| **10** | Research-task generation | — | — |
| **11** | Flock portal layer **(UNBLOCKED — aggregator API verified)** | Stage 1D | — |

*(Every outline stage is mapped: Stage 0 → Phase 0; 1A → 3 and 5; 1B/1C → 4; 1D → 11; 1E → 12; 1F → 7; 1G → 13; Stage 2 → 8; Stage 3 → 12; Stage 4 → 13; Stage 5 → 17; Stage 6 → 18. Phases with no stage column are infrastructure the outline assumes but does not stage.)*
| **12** | Usage and network layer | **Stage 1E**, Stage 3 | — |
| **13** | Accountability, policy, legal instruments | **Stage 1G**, Stage 4 | — |
| **14** | Public API + exports + dataset publication | — | — |
| **15** | Public web surfaces | — | — |
| **16** | Contributor system + contribution-back | — | — |
| **17** | Broader surveillance technologies | Stage 5 | — |
| **18** | International adapter #1 | Stage 6 | — |

### 51.3 Universal phase gate

**SIG-ENG-031 (MUST).** No phase is complete until: every acceptance criterion passes; CI is green
including data-quality checks; new requirements have automated tests (SIG-ENG-004); ADRs are
written for every deviation; the traceability matrix is updated; and the phase's own risk-register
entries are updated.

---

## 52. Phase specifications

Each phase states its **goal**, **deliverables**, **acceptance criteria** (testable), **spec
sections to load**, and **dependencies**. Sections not cited need not be read (SIG-ENG-001).

---

### Phase 0 — Foundations, governance, ecosystem coordination

**Goal.** Make it possible to build lawfully and collaboratively. Write no ingestion code.

**Deliverables.**
1. Repository skeleton (§47), CI, dependency management, licence headers.
2. **Adopted policy documents**, as code where executable: Crawler Conduct (§26); Publication
   Policy incl. the coordinate matrix and officer test (§43); Takedown & Correction (§45); Threat
   Model (§44); Licensing Decision (§42); Contributor Safety (§34.3); Governance & Code of Conduct
   (§46.2); the anti-misuse statement (SIG-GOV-019).
3. **Source registry seeded** with every source in OL-21 plus §22.3, each with rights record, SPDX
   expression, reviewed `redistributable`, custody posture, `compact_status`, `ingestion_permitted`.
4. **Stage 0 outreach executed** to all nineteen federation-compact projects, with outcomes
   recorded — including `no_response`.
5. ADR-001…ADR-012 written (§15.5).
6. Legal home identified (SIG-GOV-012).

**Acceptance criteria.**
- [ ] `ingestion_permitted` defaults to false and a test proves a connector refuses to run without it.
- [ ] The rights record for every registered source is populated or explicitly `UNDETERMINED`.
- [ ] `UNDETERMINED` fails the export gate — proven by test.
- [ ] Every policy document is published and every executable rule has a test.
- [ ] **Eyes on Flock outreach outcome is recorded** (SIG-INGEST-030) — the Phase 11 blocker.
- [ ] Every ADR names a revisit trigger (SIG-STORE-007).
- [ ] The canonical DeFlock host is resolved (REQ-R1-14).
- [ ] The local-group registry exists and is seeded (SIG-TASK-014).

**Load:** §0, §1–§7, §22, §26, §42–§46, §47.

---

### Phase 1 — Ontology as code

**Goal.** One schema source generating all downstream forms.

**Deliverables.** LinkML ontology for every §11 entity and §12 edge; §13 vocabularies as SKOS;
the predicate registry with volatility, strategy, and directness rows; generators for SQL DDL,
JSON Schema, OWL/SHACL, Pydantic, docs; the generalization conformance suite (SIG-CHART-028).

**Acceptance criteria.**
- [ ] CI fails if committed generated artifacts differ from a fresh generation.
- [ ] The generalization suite passes: acoustic sensor; capability with no asset; reference
      database; commercial data-access relationship; integration hub — all expressible.
- [ ] Every predicate has volatility, strategy, and a directness row (SIG-ONTO-067).
- [ ] Every technology family has an `-unspecified` leaf.
- [ ] No vendor name appears in any schema identifier.
- [ ] Vocabularies publish at stable per-version IRIs.

**Load:** §8, §11, §12, §13, §20. **Depends:** 0.

---

### Phase 2 — The bitemporal claim and evidence spine

**Goal.** The layer that makes every invariant enforceable.

**Deliverables.** L0/L1/L2/L3 schema (§16); append-only enforcement; OCFL evidence store; capture
and extraction pipeline; EDTF encoding with pinned envelope derivation; as-of functions; PROV-O
export; ingest-run lineage.

**Acceptance criteria.**
- [ ] UPDATE/DELETE on `claim` rejected except closing `sys_period` — proven by test.
- [ ] Entity tables contain no attribute columns — schema test.
- [ ] The §16.6 correction scenario passes: `as_of_belief` before the correction returns the old value.
- [ ] Property tests over temporal invariants TI-1…TI-8 pass.
- [ ] `valid_to_kind` distinguishes `ongoing` from `unknown`; the API surfaces it.
- [ ] EDTF round-trips; "early 2025" does not become `2025-01-01`.
- [ ] Resolution overlap prevented by exclusion constraint, not application code.
- [ ] An OCFL object is readable without SIG's code.
- [ ] Sealed captures expose metadata-only public representations.
- [ ] RLS tests pass for every role × tier.

**Load:** §9, §10, §16, §17, §20. **Depends:** 1.

---

### Phase 3 — Identity registry and deterministic ER

**Goal.** Stable identity before anything is counted.

**Deliverables.** Jurisdiction registry with geometry and temporal versioning; organization
registry; identifier crosswalk; `normalize_org_name()` with test vectors; cascade tiers 0–3;
public ID minting with merge/split events and tombstones.

**Acceptance criteria.**
- [ ] `normalize_org_name()` passes all committed vectors; sheriff variants collapse; acronyms
      resolve by exact lookup only.
- [ ] GEOIDs fixed-width with explicit level.
- [ ] ORI validated by pattern, not by positional state assumption; the UCR↔USPS table exists.
- [ ] A zero-record ingest **fails the run**.
- [ ] Municipality and its police department are distinct, joined by `parent_of`.
- [ ] The five succession fixtures pass; a rename produces no succession relation.
- [ ] Public identifiers survive a simulated cluster split with redirects and tombstones.
- [ ] Agency centroids are rejected for point-in-polygon use.

**Load:** §11.1–11.3, §14, §16. **Depends:** 2.

---

### Phase 4 — Connector framework, OSM, Atlas

**Goal.** Two connectors of maximally different shape prove the framework, and the ODbL split is
real in the schema.

**Deliverables.** The eight-stage interface; rate-limiter/robots layer; the licence gate; replay in
network isolation; shadow-mode diffing; source-disappearance events; `osm` and `atlas` connectors;
the **separate ODbL asset table**.

**Acceptance criteria.**
- [ ] A network call after `capture()` **fails the run**.
- [ ] Replay over pinned digests produces byte-identical claims modulo id and sys_period.
- [ ] Shadow mode reports a diff without asserting.
- [ ] A source returning 404 produces an event row and a task, not an exception.
- [ ] Robots-unretrievable ⇒ connector refuses to run.
- [ ] OSM connector handles nodes, ways, relations; splits semicolon multi-values; normalizes across
      all four surveillance keys; preserves element id **and version**.
- [ ] OSM output lands in the ODbL table; a test asserts an export mixing it with CC-BY **fails**.
- [ ] Atlas rows preserve upstream attribution and vocabulary version; a retired category is
      recorded as retirement, not as a world change.
- [ ] Each connector has committed fixtures and a canary.

**Load:** §8.4, §17, §21, §22, §23.2–23.3, §42. **Depends:** 3.

---

### Phase 5 — Probabilistic ER, review queue, curation UI

**Goal.** Close risk 2. Nothing uncertain writes itself.

**Deliverables.** Splink-based matcher; blocking with sizing; gold set with double adjudication and
frozen holdout; tiers 4–5 to review; the internal curation UI; cluster-shape alerts.

**Acceptance criteria.**
- [ ] Tiers 4/5 produce `PROPOSED` claims only — proven by test.
- [ ] Every match records tier, evidence, weight, and per-comparison decomposition.
- [ ] Holdout precision/recall reported; auto-write demotes on breach.
- [ ] Cluster-shape alerts fire on seeded implausible clusters.
- [ ] Blocking rules sized; oversized rules rejected.
- [ ] LLM output reaches only the review queue; model and prompt version logged with each decision.

**Load:** §14.6–14.8, §25, §27. **Depends:** 4.

---

### Phase 6 — Vertical slice: one jurisdiction end-to-end

**Goal.** **Falsify the design on real data before scaling it.**

**Deliverables.** One jurisdiction with genuinely disagreeing sources, carried from evidence to
rendered dossier: assets, organizations, a deployment, a contract, a portal-derived or
records-derived configuration, and at least one real contradiction.

**Acceptance criteria.**
- [ ] **J-1 executes end to end** for the slice jurisdiction.
- [ ] Every material fact resolves to a document at a locator.
- [ ] At least one genuine contradiction is detected and rendered without collapse.
- [ ] The count predicates are distinct; `PREDICATE_CONFLATION` fires on a deliberate conflation.
- [ ] A written retrospective is committed, recording what the design got wrong.
- [ ] **The slice jurisdiction satisfies the hardness precondition**, declared *before* the slice
      begins: at least three independent source families; at least two claims on one predicate that
      disagree; at least one asset with no operator; and at least one lifecycle transition
      evidenced by a dated document. A jurisdiction failing any precondition MUST NOT be used.

*Rationale.* The precondition replaces the unfalsifiable formulation "a slice that surfaces no
design problems was too easy" with a checkable property of the chosen jurisdiction, declared in
advance so it cannot be rationalized afterwards.

**Load:** all prior + §29.1, §39.2. **Depends:** 5.

---

### Phase 7 — Records, procurement, and document parsing

**Deliverables.** Parsing stack with locators; file classification; records connectors; procurement
connectors including cooperative vehicles and federal sub-awards; the agenda-platform tenant
registry; `RecordsRequest`; `FundingInstrument`.

**Acceptance criteria.**
- [ ] Every extraction emits a locator; locator-less extractions are rejected.
- [ ] `raw_value` preserved for unparseable values.
- [ ] Mixed-format archives classified before parsing.
- [ ] Cooperative piggyback contracts set `parent_cooperative_contract`.
- [ ] Federal sub-awards traced to a local deployment for at least one real case.
- [ ] `no_responsive_records` writes a `CoverageRecord`.
- [ ] Rate-limited APIs used as targeted lookups; no crawl attempted.

**Load:** §11.11–11.12, §11.19, §22, §23.5–23.6, §24. **Depends:** 6.

---

### Phase 8 — Reconciliation engine and contradictions

**Deliverables.** The §28 resolver; the ruleset as versioned data; the four axes; the ambiguity
test; rationale templates; `Contradiction`; the workflows of §29.

**Acceptance criteria.**
- [ ] Resolution is deterministic; no random tie-break; total order proven by test.
- [ ] A Tier-A contract does **not** win `active_device_count` against a `D1` portal snapshot.
- [ ] `D6` claims are excluded, not down-weighted.
- [ ] **`U5` fires**: a stale unchallenged value returns `UNRESOLVED` with `last_known` and a date.
- [ ] `unresolved_conflict` is publishable via the API.
- [ ] Three sources copying one upstream count as **one** independence class.
- [ ] Rationales are quotable and never mix a support and an agreement term in one sentence.
- [ ] Full L3 rebuild is byte-identical.
- [ ] Human override records author and rationale, and does not hide the algorithmic result.
- [ ] Sharing asymmetry produces a finding, not a merge.
- [ ] Vendor replacement renders as replacement, never as removal.

**Load:** §10.4–10.9, §16.4, §28, §29, §31. **Depends:** 7.

---

### Phase 9 — Coverage and negative space

**Acceptance criteria.**
- [ ] `CoverageRecord` with `sources_searched[]` required for `searched_not_found`.
- [ ] **Every published aggregate carries a denominator** — enforced by test.
- [ ] The four absence kinds are distinguishable in API and UI.
- [ ] Freshness is computed relative to predicate volatility.
- [ ] Any completeness estimate publishes its violated assumptions, or is omitted.

**Load:** §9.5, §32. **Depends:** 8.

---

### Phase 10 — Research-task generation

**Acceptance criteria.**
- [ ] All 32 task types implemented, each with a testable closing condition.
- [ ] Every contradiction detector maps to a task.
- [ ] `resolved_no_evidence_exists` writes a `CoverageRecord`.
- [ ] Tasks auto-invalidate when their detector stops firing.
- [ ] Geographic claims expire and never grant exclusivity.
- [ ] Records-request generation emits the correct statute for the jurisdiction.

**Load:** §33, §36. **Depends:** 9.

---

### Phase 11 — Flock portal layer **(ungated 2026-08-20)**

**SIG-ENG-032 (MUST). — GATE LIFTED 2026-08-20.** A lawful access path exists: the aggregator's
public CC BY-SA 4.0 API (SC-18). The phase proceeds against that API. The fallbacks of
SIG-INGEST-031 MUST still be implemented, because the API is a single dependency and the vendor's
own domains are unarchivable — if it goes away, so does the only route to this layer.

**Acceptance criteria.**
- [ ] No challenge-defeating code exists in the repository — proven by review and by a test that
      the connector honours a challenge response as a refusal.
- [ ] Portal data is ingested from the aggregator API into a **separate CC BY-SA 4.0 compartment**;
      a test asserts an export merging it with the CC-BY graph **fails the build** (SIG-LIC-004a).
- [ ] Change detection keys on the upstream's snapshot field, not fetch time; a test asserts SIG
      does not poll faster than the upstream refresh (SIG-INGEST-030c).
- [ ] Historical back-fill is sourced from archived captures of the API endpoint (SIG-INGEST-030b).
- [ ] `ai_training_permitted = false` is recorded and enforced for this source (SIG-LIC-004b).
- [ ] Portal disappearance produces an event and a task.
- [ ] Snapshot diffing produces per-field change events.
- [ ] Sharing edges land as **configured access only**, directional, with blank cells as negatives.
- [ ] Audit `Camera Count` lands as an independent count claim.
- [ ] `***` redaction is distinguished from empty.

**Load:** §22.5, §23.4, §23.7, §26, §29.3, §29.7. **Depends:** 10.

---

### Phase 12 — Usage and network layer

**Acceptance criteria.**
- [ ] No per-search or per-plate row exists anywhere — schema test.
- [ ] The three access edge types are never merged.
- [ ] Small-cell suppression applies with the correct rationale; institutional small counts publish.
- [ ] Analytics joins to the graph by UUID and period only, never by name.
- [ ] Aggregate partitions are registered as evidence artifacts.
- [ ] Access-path closure respects hop limits, scope, and non-composition rules.

**Load:** §11.16, §12.2, §12.5, §18, §30.2. **Depends:** 11.

---

### Phase 13 — Accountability, policy, legal instruments

**Acceptance criteria.**
- [ ] `epistemic_status` required and preserved end to end.
- [ ] An allegation never renders with a factual verb.
- [ ] Incidents link to all six source classes with class recorded.
- [ ] Policy/configuration divergence is a rendered finding.
- [ ] A curated index can be held without normalization.

**Load:** §11.13–11.14, §11.17–11.18, §23.8, §29.6. **Depends:** 12.

---

### Phase 14 — API and exports

**Acceptance criteria.**
- [ ] No endpoint returns a bare value without its resolution envelope.
- [ ] Both as-of parameters accepted and echoed.
- [ ] A belief-pinned request is reproducible after a correction.
- [ ] Export licence computed; incompatible mix fails the build.
- [ ] ODbL assets ship as a separate file; per-row rights present.
- [ ] Crosswalk export published.
- [ ] Zenodo deposit with concept and version DOIs.
- [ ] No prohibited endpoint exists (SIG-API-012).

**Load:** §37, §38, §42.4. **Depends:** 13.

---

### Phase 15 — Public web surfaces

**Acceptance criteria.**
- [ ] All seven outline surfaces exist, **plus the corrections log**.
- [ ] Core content usable **without JavaScript**; every map has a tabular equivalent.
- [ ] WCAG 2.2 AA automated checks pass; no colour-only encoding.
- [ ] The four epistemic fields are independently visible; no fused badge.
- [ ] Absence renders as one texture, is clickable, and generates a task.
- [ ] Contested values are marked at every appearance.
- [ ] The dossier prints to a usable PDF with sources, as-of date, and permalink per page.
- [ ] "What we don't know" appears in summary, print, and API.
- [ ] Centrality statistics carry an ER-quality disclosure inline.
- [ ] Every page has a belief-pinned permalink and a citation affordance.
- [ ] The three example editorial cases render as specified.

**Load:** §39, §40, §41. **Depends:** 14.

---

### Phase 16 — Contributors and contribution-back

**Acceptance criteria.**
- [ ] Contributions enter at L0 as evidence, never directly at L1.
- [ ] No contributor PII is retained beyond the documented window.
- [ ] Pseudonymous contribution works at every tier.
- [ ] Every contribution is revertible as a unit; the revert is a new assertion.
- [ ] **No direct automated OSM writes exist**; contribution is human-mediated.
- [ ] The OSM automated-edits compliance ADR is written (SIG-CONTRIB-016).
- [ ] An **Organised Editing activity page** is published and registered, disclosing tools, data
      sources and their usage conditions (SIG-CONTRIB-016d).
- [ ] A **changeset hashtag** is declared, required on SIG-originated edits, and wired to the §7
      leverage metric (SIG-CONTRIB-016e).
- [ ] The **contribution-path licence gate** blocks a task built on a source whose terms forbid
      deriving an OSM edit — proven by a test with a deliberately incompatible source
      (SIG-CONTRIB-016f).
- [ ] Device observations route to OSM/DeFlock, not to SIG capture.
- [ ] Upstream attribution appears in UI, API, and exports.

**Load:** §34, §35. **Depends:** 15.

---

### Phase 17 — Broader surveillance technologies (Stage 5)

Priority order per OL-17.5-01: private-camera federation; facial recognition; cell-site simulators;
mobile-device forensics; gunshot detection; drones; commercial location data; RTCC integration.

**Acceptance criteria.**
- [ ] **Each is populated with no schema change.** Any required change is a Phase-1 defect and MUST
      be recorded as one.
- [ ] Non-camera physical sensors are represented without a camera abstraction.
- [ ] The commercial data-broker chain is representable with distinct aggregator and productizer
      roles.
- [ ] Federal authorization datasets populate `authorization_state` with native validity intervals.

**Load:** §5.2, §11, §13.1, §23. **Depends:** 16.

---

### Phase 18 — International adapter #1 (Stage 6)

**Why France/Belgium is the recommended first adapter.** The Technopolice ecosystem has already
documented and mapped, in a non-US jurisdiction, the same technology span SIG models: CCTV;
**intelligent/algorithmic video (VSA)**; facial-recognition experiments; drones; thermal cameras;
acoustic sensors; and "safe city" integration programs (OL-5.2-01). Two facts make it the highest-value
first adapter rather than merely an available one:

1. **The community explicitly debated using OSM rather than building an isolated
   surveillance-camera database** (OL-5.2-02) — the same architectural choice SIG has made, argued
   independently in another jurisdiction. That debate is a documented precedent for SIG's federation
   posture, and the discussion thread is in the source registry (§22.6 I).
2. **A historical activist database of roughly 12,000 French cameras was imported into OSM for
   verification** (OL-5.2-03). This is the concrete, already-executed path from *local activist
   database* → *common geographic substrate* that SIG's whole federation thesis depends on, and it
   is the strongest available evidence that the thesis works. Phase 18 MUST study this import — its
   conventions, its community consultation, and its outcome — before proposing any SIG-originated
   contribution at scale (SIG-CONTRIB-016).

The French evidence base is also structurally different in a way that stress-tests the model:
authorization is carried by **published prefectural orders** rather than by contracts, and
procurement is carried by a **national open-data procurement dataset** rather than by thousands of
municipal systems. Both map onto `LegalInstrument` and `Contract` respectively, and if they do not,
that is a §5.3 defect to be found here rather than in production.

**SIG-ENG-036 (MUST).** Coarser international datasets — country-level surveillance indices, global
facial-recognition maps, and vendor-level international datasets (OL-5.3-01) — MUST be ingested as
claims with **explicit coarse granularity** and MUST NOT be disaggregated to agency level by
inference (SIG-INGEST-042, OL-5.3-02).

**Acceptance criteria.**
- [ ] Jurisdiction adapter checklist satisfied with no US-shaped assumption.
- [ ] Organization and legal-instrument types added under a national namespace, not by widening a
      US enum.
- [ ] Multilingual labels with BCP 47 tags render correctly.
- [ ] Jurisdiction-conditional publication rules apply (§43.8).
- [ ] The non-US records-request vocabulary is used, including `no_equivalent_available`.

**Load:** §5.3, §13.7–13.8, §43.8. **Depends:** 17.

---

## 53. Risk register

| # | Risk | Severity | Mitigation | Phase |
|---|---|---|---|---|
| R-01 | ODbL misapplication makes the dataset unpublishable | Critical | §42.3; separate tables; licence gate; counsel on §42.3 residuals | 0, 4 |
| R-02 | ~~Flock portal layer has no lawful automated path~~ **CLOSED 2026-08-20** | — | A public CC BY-SA 4.0 aggregator API supplies the layer (SC-18). Residual: it is a **single point of failure**, so the fallbacks of SIG-INGEST-031 and the succession offer stay live | 0, 11 |
| R-03 | ER errors corrupt all network statistics | Critical | §14.7 gates; P6 ordering; UI disclosure | 3, 5 |
| R-04 | Upstream projects decline collaboration | High | Stage 0; recorded `no_response`; fallbacks | 0 |
| R-05 | Re-extraction treated as migration, destroying history | High | §21.2 claim identity | 2, 4 |
| R-06 | Silent parser drift after an upstream redesign | High | Fixtures + nightly canary | 4+ |
| R-07 | Egress cost becomes existential on success | High | §38.4 storage choice | 14 |
| R-08 | Publishing a name or coordinate that causes harm | Critical | §43; two-reviewer test; categorical address rule | 0 |
| R-09 | Legal demand against SIG | High | §44.3, §45, §46.1 | 0 |
| R-10 | Data-poisoning campaign | Medium | §34.4; false-absence guard | 16 |
| R-11 | Zero-cost mode fails silently | Medium | §46.4 keepalive; tested degraded mode | 0 |
| R-12 | **FlockReporter unreachable; ecosystem directory may not exist** | Medium | SIG-TASK-014 own registry | 0 |
| R-13 | An unverifiable requirement ships unchecked | Medium | SIG-ENG-005 register entry + compensating control | all |
| R-14 | ~~OSM automated-edits rules not yet read~~ **CLOSED 2026-08-20** | — | Read and analysed (SC-12); the human-mediated design keeps SIG outside the policy's scope entirely (SIG-CONTRIB-016b). Residual: the ADR must still be written | 16 |
| R-15 | Scholarly/paywalled evidence unretrievable | Low | `capture_status` models it (SC-07) | 2 |
| R-16 | Vendor integration facts go stale fast | Medium | Volatility classes; canaries | 8 |

**SIG-ENG-033 (MUST).** The risk register MUST be reviewed at every phase gate, and each research
file's **Open questions** section MUST be triaged into it rather than left in the cache.

---

## 54. Sequencing and parallelization

**SIG-ENG-034 (MUST).** The critical path is `0 → 1 → 2 → 3 → 4 → 5 → 6 → 8`. Phase 6 is a hard
synchronization point: **no phase after 6 may begin until its retrospective is written.**

Parallelizable once their dependencies land: Phase 7 with 8 (parsing is independent of resolution);
Phase 9 with 10; Phase 13 with 12; Phase 15 surfaces individually; Phase 17 technologies
individually.

**SIG-ENG-035 (MUST).** Phase 11 depends on an **external** source, not on internal work, and it
MUST NOT block phases 12–18, which MUST be able to proceed on other sources. A design in which one
uncooperative or unavailable upstream halts the project is a design failure, and the phase order
avoids it deliberately.

The dependency is now **satisfied** rather than merely mitigated — a public API supplies the layer
(SC-18) — but the ordering constraint stands, because that API is a **single point of failure** and
the vendor's own domains are unarchivable. If it disappears, phases 12–18 must still run.

---
