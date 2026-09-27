# Independent design review and closure

Review date: 2026-09-25. Four review artifacts preserve their original findings. “Addressed” below means the **design/contract** now has an explicit correction and acceptance owner; it does not mean future implementation has passed that test. The three fresh-context reviewers were not authors of the root plan. The product/memory reviewer separately challenged the root synthesis and corrected a flaw in its own earlier S4 proposal.

| Review finding | Correction and owner | Design disposition |
|---|---|---|
| Product P1: release id hashes itself through rendered links | Pre-render namespace plus separate final integrity digest; acyclic dependency test, P32.13 and SIG-FIND-001 | Addressed |
| Product P1: global latest occurrence erases independent disagreement | Per-source assertion/record-lineage candidate sets, paired fields, separate resolver choice; P32.4/SIG-TRUST-005 | Addressed |
| Product P1: rollback restores withheld artifacts | Current withdrawal barrier across origin/CDN/HTML/JSON/search/tiles/downloads; whole-artifact denial if necessary; P32.5/.13/.25 | Addressed |
| Product P1: locks/CAS insufficient across stale worktrees and worker closeout | Stable chain authority; pre-PR operation id; prepared/external-known/memory-committed/acknowledged state machine; one accepted git tree/commit; actual writer-entry-point cutover, P32.8 | Addressed; live cutover remains D-R10-MEMORY-1 |
| Product P2: deterministic projection reads itself or embeds future commit/time | Explicit acyclic source set; input revision/digests; separate receipt; useful conflict report plus nonzero exit, P32.7 | Addressed |
| Product P2: events and compatibility table become competing truths | Shadow phase; one migration anchor per legacy row; single transactional writer after validated cutover; explicit assessment supersession, P32.7/.8 | Addressed |
| Product P2: search/intake imply unapproved service capacity and operation | Existing API + read-only compartment FTS5 benchmark; static fallback; separate receiver credentials/store; staffing/retention/exposure packet, P32.13–16/GATE-G3 | Addressed; deployment decisions remain gated |
| Plan F1 P1: candidate predates evaluation/rules changes | Added P32.23a and SIG-TRUST-010; every final artifact rebuilt after P32.23, then exact-candidate P32.24/G3 | Addressed |
| Plan F2 P2 / evaluation ER-4: sample frozen before repairs | P32.9 is tooling; P32.22 freezes population; HUMAN-H4 develops/calibrates; P32.22a freezes candidate then draws final sample; HUMAN-H5 labels it | Addressed |
| Plan F3 P2 / source SP-05: document semantic mapping has no early owner | P32.2 owns typed field/schema map before adapters; P32.12 owns named-target field→predicate/qualifier/role/time→dossier crosswalk; P32.17 consumes it; bounded protocols/fixtures | Addressed |
| Plan F4 P2: moderation does not apply a real correction | Added P32.16a and SIG-FIND-008: restricted idempotent canonical application/receipt/release link; whole-chain acceptance in P32.24 | Addressed |
| Source SP-01 P1: all-unknown dossier could count complete | Fixed twelve-question rubric, ≥28/36, required questions ≥2, explicit incomplete-publication distinction; P32.17/SIG-DOS-002/G3 | Addressed |
| Source SP-02 P1: camera labels mistaken for documentary review | HUMAN-H4 separately assigns competent semantic reviewers; contract/legal applicability does not inherit device-label authority | Addressed; actual human work remains owed |
| Source SP-03 P1: “schema preflight” fetches unsafe workbook bytes | P32.20 uses independently supplied safe schema/link metadata only; no raw XLSX/ZIP shared strings before authorization; SRC-027 optional, not needed for completion | Addressed |
| Source SP-04 P1: pilot cap expands from two additional families to five | P32.21 ≤2 incremental non-portfolio families, ≤10 documents/aggregate rows each, ≤2 protocols; ≤5 total including cities | Addressed |
| Source SP-06 P2: “verified shortlist” and causal yield overclaim | Researched inventory with row-level review depth; descriptive pilot unless optional matched timed comparison is run; no causal superiority claim, P32.11/.21 | Addressed |
| Evaluation ER-1 P1: new gate silently replaces live provisional policy before humans | Shadow/inactive evaluator initially; explicit operational decision for any pre-campaign demotion; post-human measured activation in P32.23/.23a | Addressed |
| Evaluation ER-2 P1: baseline eval can expose holdout before tuning | H4 development → P32.22a candidate/frame freeze → H5 final labels → P32.23 one evaluation; no post-sample candidate selection. New SIG-EVAL-007 and new-candidate-positive-frame regression | Addressed |
| Evaluation ER-3 P2: independent reference-label schema/RLS owner missing | P32.9 owns campaign/sample/assignment/attestation/label/adjudication additive schema, PG/RLS access and sealed-label isolation tests | Addressed |
| Evaluation ER-5 P2: repeated bytes and recurring result need occurrence/completion tests | One blob/two immutable occurrences; no mutable-head sidecar; A→B→A reuses result but appends current execution completion, P32.2/.4 | Addressed |
| Evaluation ER-6 P2: semantic fidelity excludes unresolved sample units | All-sampled support plus conditional adjudicated fidelity and adjudication yield, weighted appropriately; research correction and P32.6 acceptance | Addressed |

No design blocker in these reports is intentionally waived. Human availability, legal/source review, measured service capacity, global workflow cutover and production publication are not research errors to “close” with prose; their pending state is explicit in DEFERRALS and readouts. Final automated checks validate dependency/ownership/spec integration; independent follow-up review checks the material corrections before delivery.

A follow-up statistical review found that freezing labels alone was insufficient while candidate selection still followed sampling. The final plan adds P32.22a and HUMAN-H5 so the final inclusion probabilities refer to the actual evaluated matcher; the final closure check must confirm the generated contracts as well as the narrative.

Final fresh-context follow-ups: plan F1–F4 and source SP-01–06 were confirmed addressed. The statistical follow-up confirmed candidate-before-frame ordering in actual contracts 184–188, §55 and SIG-EVAL-007; one stale P32.10 activation reference was corrected to post-HUMAN-H5 / P32.23. No substantive P1 remained in those bounded reviews.
