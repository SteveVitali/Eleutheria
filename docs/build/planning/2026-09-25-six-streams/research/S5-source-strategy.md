# S5 — Gap-driven documentary source strategy

Research date: 2026-09-25. Planning baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`. This document and `../data/source-candidates.csv` are a research queue and proposed implementation design. They authorize no onboarding, source-rights change, ingestion, external message, paid account, records request, deployment or publication.

## Recommended investment

Prioritize documentary chains that answer ownership, funding, procurement, retention, sharing and oversight questions over more camera-coordinate rows. Start with the S2 cities, then test one structured funding/acquisition family and one independent oversight family. Preserve the global catalog as a discovery queue; do not treat its row count as coverage or an instruction to ingest everything.

The CSV contains 27 ranked **targets/families**, not 27 independently corroborating publishers. San Diego's technology reports, PAB reports, contracts and network-audit metadata are separate acquisition shapes under related municipal provenance. The first two groups are useful precisely because their roles differ; they must still retain common institutional lineage. “Net-new” means no corresponding specific source row was found in this baseline registry, not that no existing generic connector could handle it or no record from the jurisdiction is already present.

### Baseline and non-duplication

Local observations were made by reading `connectors/src/connectors/data/sources.toml`, connector dispatch, `live_targets.toml`, agenda-tenant data, the ticket manifest, active deferrals and P31.12/P31.13 contracts. Snapshot audit counts from the preceding review: 339 registry rows, 236 permitted, 227 dispatch-mapped and 215 both mapped and permitted. These are distinct states. They do not prove fresh live ingestion, captured-byte persistence, entity resolution or public contribution. Recompute against the integration baseline before ticket execution; the other agent is active.

The earlier hosted reports are historical execution artifacts, not a live database read in this research session. Their large camera-source class includes multiple registry types; do not label all of it DOT data. The strategic concern is the imbalance between many sensor claims and fewer linked organizations/relationships, not an accusation that raw count itself is wrong.

**Already committed to P31.12/P31.13:** `gao_surveillance_reports`, `dhs_oig_reports`, `dhs_fusion_center_assessments`, `uk_surveillance_camera_commissioner`, `fema_hsgp_allocations`, `ccops_oakland`, `ccops_cambridge`, `ccops_somerville`, plus catalog repair/retry work. Do not create replacement tickets for these eight or compete with P31.13's error retries. P31.12 already specifies its connector, capture, live-run, idempotence and cadence work. Round 10 should consume its inventory/results and reuse its framework.

Existing Sourcewell and FAA entries are reference-only; Berkeley and Boston are existing unpermitted CCOPS rows. OKC is an existing target-deepening opportunity. Seattle, NYC, Chicago and San Jose have existing source/agenda coverage; their proposed audit/algorithm-report publishers or specific documentary collections are additions, not newly discovered cities. Tulsa has existing Granicus discovery; San Diego county/port agenda tenants are not interchangeable with City records. Precise notes appear per CSV row.

## Ranked queue and bounded selection

| Rank | Candidate | Why now / what it must not imply |
|---|---|---|
| 1–5 | OKC packet; Tulsa policies/contract chain; San Diego technology reports; City contracts; PAB oversight | Directly close the six-profile S2 portfolio. Read documents as legal/operational/oversight genres, not interchangeable assertions. |
| 6–9 | OMES contracts; UVED authority records; Safe Oklahoma; Oklahoma JAG-LLE | Local spending/authority discovery. Eligibility, statewide availability and an appropriation do not establish a purchase or deployment. |
| 10–12 | Sourcewell cooperative contracts; California State Auditor ALPR audit; Seattle OIG annual reviews | Parent-contract lineage and independent checking. Cooperative availability is not a local order; historical survey is not current ground truth. |
| 13–18 | San Jose privacy/algorithm records; Norman policy; NYC DOI; NYC Comptroller; Chicago OIG; BART | Repeatable governance and oversight evidence. Keep agency responses, findings, recommendations and decisions distinct. |
| 19–22 | Berkeley; Boston; Santa Clara; COPS technology awards | Reuse existing source families where available; close institutional and funding links with limited targets. |
| 23–27 | DHS privacy assessments; DLA LESO; FAA waivers; UK transparency records; San Diego network-audit metadata | Useful alternatives and later probes, with temporal/completeness/privacy caveats. The last candidate is metadata-only pending content screening and approval. |

Detailed primary URLs, access date, review depth, novelty, expected claims, counterexamples, lineage, uncertainty and effort are in the CSV. Each row is a lead, never legal clearance or a ready-to-ingest specification. Search-result excerpts identify plausible official documents; they do not count as full-document reading or production evidence. S2 contains deeper inspection notes for the local packets and the actual City–Ubicquia agreement URL.

Proposed Round 10 cap: the three-city/forty-document S2 portfolio **plus at most two non-portfolio pilot families**, with ≤10 sampled documents/rows per family. Prefer Sourcewell parent/local-contract linking and one independently authored audit (California or Seattle); choose a funding family instead only if a named local procurement has a traceable award gap. Twenty-seven candidates stay in the queue; only five acquisition families at most become initial implementation scope when the three dossier packages are counted as three. New adapter protocols cap at two; most local documentary work should reuse permitted HTTP/PDF/agenda mechanisms. A failed rights/access gate returns a bounded research result, not a mandate to keep crawling until something passes.

Expansion requires: all admitted assertions have reproducible citations; high-risk scope/rights/identity errors are zero in reviewed samples; at least one new independently supported relationship or material governance answer per pilot family; maintenance and review time are measured; no unresolved privacy incident; and operator approval for the next bounded batch. More rows or successful HTTP requests are not expansion criteria.

## Scoring that rewards missing answers

Compute a provisional score only after a candidate has a stated unanswered question and corpus-overlap check:

`3G + 3R + 2I + 2U + T + J − 2E − 2A − 2S`.

Each dimension is ordinal 0–3: G closes an explicit dossier/coverage gap; R yields named institutional relationships/governance; I adds independent provenance; U has reusable extraction structure; T improves timeliness; J serves the current geographic need; E is engineering/review effort; A is access friction; S is sensitive-content exposure. The CSV records editorial rank and priority tier, not fabricated measured scores. Implementation must store the dimension values, assessor, evidence and scoring version before a numeric ranking is displayed. Revisit weights after the experiment; report disagreement rather than treating an ordinal score as probability or scientific truth.

Rights/admissibility are **gates independent of score**. A high score cannot authorize a source. Unknown license is not “low risk,” and easy access is not permission. Net-new content is determined by lineage-aware document/claim comparison against current inventory; a novel URL mirroring an existing report has low independent yield.

A useful acquisition objective is “independently supported agency–program–contract–funding/policy/access links per reviewer-hour,” together with the proportion of twelve S2 questions answerable. Avoid a single scalar hiding false assertions, missing exceptions or difficult communities. Report each dimension and its denominator.

## Discovery procedure and lineage

1. Seed from a named unknown: contract identifier, renewal year, partner agency, budget line, adoption action, policy version or exception. Carry entity and geographic scope into the query.
2. Search the official publisher/records index first, then linked agenda attachments and named parent programs. Use precise identifiers and vendor aliases, not only “camera.” Examples include C241032, 30000062-26-E, 101223-AXN and report 2019-118. Search within the relevant year and jurisdiction without assuming a filename date is an effective date.
3. Follow one hop from a cited agreement to amendment, policy, oversight response or grant award. Record discovered links and stop reasons. Limit an initial session to two hours/site and two sessions per unresolved critical question.
4. Log publisher, document origin, procurement/program ID, evidence genre, publication/revision/coverage dates, content hash when lawfully captured, URL aliases and exact reviewed portion. Hash-deduplicate bytes; use reviewed origin/republication links for near-duplicates. Never automatically collapse a revised report or amended contract.
5. Distinguish `same_bytes`, `republished_document`, `derived_summary`, `new_version`, `response_to`, `amends`, and `independent_account`. These are proposed lineage classifications; map to existing types or extend explicitly. They do not all count as independent support.
6. Produce a research task for a missing executed contract or named partner list. Drafting a records request can be a later operator-approved unit; submitting it is not authorized here. Do not bypass account/WAF/authentication boundaries to satisfy a completion score.

A promising creative loop is **contract back-chaining**: a local approval cites a cooperative master ID; the master identifies vendor/product/terms; the local order supplies buyer, quantity and funding; annual oversight tests actual operation. One carefully linked chain supports far more accountability questions than a new point layer. A second is **governance deltas**: compare a report's covered year, later oversight recommendation, agency response and adopted revision, preserving who said what at each stage. A third is **negative-space queues**: prioritize agencies whose device inventory is present but buyer/retention/sharing evidence is missing, without presenting the missing evidence as absence of infrastructure.

## Source lifecycle and rights model

Use an append-only event history with stable candidate ID, parent lineage ID and explicit transitions:

`DISCOVERED → TRIAGED → RESEARCHED → RIGHTS_REVIEW_REQUIRED → OPERATOR_APPROVED → ADAPTER_READY → SHADOW_VALIDATED → LIVE_VERIFIED → LINKED_REVIEWED → PUBLICATION_REVIEW → PUBLISHED → MONITORED`.

Each stage may instead record duplicate, out-of-scope, blocked-access, insufficient-evidence, declined or deferred with reason and return trigger. A candidate approved under an existing scoped decision can link that decision; it must not fabricate a new approval. Access availability, source-content rights, permissible extraction, sensitivity/admissibility, connector readiness, live execution and publication authorization remain separate fields. Do not overload `ingestion_permitted` to mean all of them. Exact names are a design proposal and require mapping to existing onboarding contracts.

Required invariants: no automatic transition creates an operator decision; registry permission alone cannot produce a live-run receipt; successful live fetch without permitted captured evidence does not mean `LIVE_VERIFIED`; parsed text without correct entity/scope is not `LINKED_REVIEWED`; export generation alone is not publication. Repeated captures retain identity and unchanged-content idempotence. Every status claim cites an artifact or explicit decision.

The rights review packet should separate (a) original document bytes and embedded third-party material; (b) access terms and technical constraints; (c) factual extraction and permitted quotation; (d) license/compartment of derived outputs; (e) publication/citation posture. “Public record” does not automatically mean CC0. [17 U.S.C. §105](https://www.copyright.gov/title17/92chap1.html) concerns U.S. federal government works, with statutory qualifications; the [Copyright Office Compendium, §313.6(C)(2)](https://www.copyright.gov/comp3/chap300/ch300-copyrightable-authorship.pdf) distinguishes copyrightable non-edict state/local works. Those primary authorities justify reviewing automatic municipal-public-record→CC0 metadata; they do not establish that a particular source is infringing or resolve its rights. Vendor attachments, Lexipol policies, photographs and contractor works may have separate provenance. Preserve prior operator decisions and route a supported inconsistency for scoped review rather than rewriting history.

Crawler behavior must follow the current approved conduct policy. Root/package AGENTS prose and later ADRs can differ: ADR-088's recorded robots posture must be read when implementing. This plan does not silently reinstate an obsolete rule or authorize bypassing access controls. A 403, content-size limitation or missing account is logged as a retrieval limitation, not proof that the document does not exist.

## Onboarding experiment and evaluation

Before live acquisition, use only previously permitted fixtures/captures or specifically authorized new samples. Build a matched comparison: two researchers/agents each get four hours and the same three local agency seeds. One uses generic technology/vendor queries; the other uses the gap/contract-chain procedure. Cross over agency assignments to reduce geography effects. The outputs are candidate evidence packets, not auto-admitted claims. Have a separate reviewer label them blind to strategy under S3; model agreement is not independent human ground truth.

Measure unique admissible documents and lineage families, correctly scoped relationships, material question gaps closed, accurate abstentions, false subject/applicability matches, missed exceptions, unsupported currentness, duplicate inflation, capture/locator completeness, and engineering/review minutes. Publish numerator/denominator and the rejected cases. For sampled precision, retain an explicit indeterminate label; do not silently count it as correct. A small pilot is descriptive, not a claim of nationwide recall. Completeness can only be measured against a declared bounded official index/year or reviewed gold packet.

For each selected adapter, evaluate a held-out packet containing native PDF, scanned PDF, a revision, a template, a signed/partially signed document, a multi-technology contract and a third-party attachment. Require 100% valid provenance traces and zero unreviewed material normalization errors; otherwise abstain/queue. Track yield under both raw URL and independent-lineage denominators. Observe one scheduled refresh or a controlled authorized replay and demonstrate unchanged-input zero new semantic claims; changed amendment/revision produces an append-only delta. Existing pipeline test conventions and S1 interfaces remain authoritative.

Proposed promotion thresholds: reviewed normalized assertion precision ≥95% with denominator and uncertainty reported; zero critical actor/time/applicability/privacy failures; 100% locator/hash checks; all unknown rights/access states honored; at least one high-value question or relation closed; realistic maintenance owner/cadence/runbook. A statistical confidence requirement, if desired, belongs in S3's sample-size design; fifty easy assertions cannot establish general safety.

## Proposed ticket units and exact acceptance tests

| Unit | Deliverable | Acceptance examples / dependencies |
|---|---|---|
| S5-A candidate queue and scoring | Versioned queue schema, registry/planned-work reconciliation, lineage IDs, dimension scoring and stop reasons | 27 current research rows parse; every row has URL/date/review depth and novelty; P31.12/13 eight sources are never emitted as new work; same-document mirrors do not increase independent yield; unknown dimensions stay unknown. |
| S5-B workflow and rights packet | Immutable state transitions and evidence/decision references, no new gate bypass | Attempted transition without scoped operator decision fails; permission alone cannot mark live success; denied/blocked states preserve reason/return trigger; sourcebytes/output license remain distinct. |
| S5-C bounded acquisition experiment | ≤2 non-portfolio families, authorized fixture/shadow adapters, scoring comparison and reviewed error analysis | Template→zero actual participants; grant eligibility→zero recipient awards; award ceiling→not spending; historical survey→not current; waiver absence→not no drone program; mirrored report→one lineage; per-query sensitive file stays outside acquisition scope. |
| S5-D conditional live verification and maintenance | Only explicitly approved targets; captured artifacts, receipt, idempotence, monitored refresh and link review | Exact approved source/target/version decision cited; existing gate refuses unapproved fixture-to-live transition; rerun unchanged content creates no new semantic assertions; changed document retains old evidence and separate review; publication remains gated. |

S5-C/D depend on S1's capture/normalization/time/lineage contracts and S3's adjudication design; they must consume P31.12/13 completion rather than replace it. S2 local packet work is separately owned and not charged twice as new source-family development. Root will turn these units into actual tickets and ledger return paths.

## Sources and review limitations

The CSV is the complete primary-source bibliography for the 27 targets, including URLs discovered through official search excerpts. S2 adds exact agreement/amendment/policy references and their reviewed sections. Additional authorities used here are §105 and the Copyright Office Compendium linked above. No source in this planning pass was lawfully ingested merely because it was browsed; no copyright or public-record access determination has been completed. No PDF signature is described as visually verified. Human study, independent adjudication, adapter/live-run and production quality metrics are **proposed, not executed**.
