# Independent source and dossier plan review

Review date: 2026-09-25. Review scope: S2/S5 research, candidate inventory, DESIGN and PLAN; no implementation or ingestion. Reviewed only the isolated planning worktree. The active original checkout was not touched.

**Disposition:** the research is careful about evidence scope, but several safeguards needed explicit execution owners and acceptance rules. Findings below distinguish the initially reviewed plan from corrections made by the root during this review. Generated ticket contracts and the eventual canonical amendment still need to preserve those corrections.

## Findings and required corrections

### SP-01 — Pilot completion was weaker in PLAN than in its research rubric (P1; correction observed)

**Observed:** S2's “Completion and unknowns rubric” distinguishes reviewable from evidence-complete: twelve questions, at least 28/36, and questions 1/5/7/8 at least 2. The initial P32.17 acceptance instead allowed researched unknowns to pass without this lower bound. P32.18–20 were titled “Complete” despite permitting unresolved procurement/governance answers. Thus an honestly all-unknown dossier could pass the engineering acceptance without meeting the promised pilot outcome. This is a contract inconsistency, not a finding that any dossier currently fails a completed evaluation.

**Correction observed on reread:** P32.17 now states the fixed threshold, and GATE-G3 requires the three dossiers to meet it or records a reduced/incomplete publication scope without pilot-completion credit. Keep the rubric in generated contracts. Explicitly retain all six program profiles and their applicability boundaries in the matrix: a Flock answer must not silently satisfy the Axon question, nor UVED authority satisfy OKCPD applicability. A city-level score needs profile-specific evidence beneath it.

### SP-02 — Documentary human adjudication did not have an executable owner (P1; correction partly observed)

**Observed:** S2 requires independent human review of all material governance, relationship and contract assertions and assigns it “under S3.” S3/P32.9 originally supplied same-device/different-device/insufficient identity labels, sampling and blinding. That rubric cannot adjudicate retention exceptions, legal applicability, execution status, or contractual precedence. Calling a review “independent” in the three dossier tickets did not establish its human role, input packet, completion receipt or gate.

**Correction observed:** HUMAN-H4 now separately assigns semantic reviewers and explicitly says identity-review competence does not automatically establish legal-applicability competence; GATE-G3 requires independent semantic review. Finish this by naming the documentary review manifest/readout, required reviewed-assertion coverage, unresolved-disagreement outcome, and the condition that missing documentary review leaves pilot completion pending. P32.18–20 may finish prepared engineering packets before H4, but must not record human acceptance then. No new legal conclusion is demanded merely to satisfy a score: unresolved applicability remains unresolved.

### SP-03 — Audit-workbook preflight could cross the acquisition boundary it is intended to enforce (P1; correction requested)

**Observed:** S2 and SRC-027 expressly limit the San Diego network audits to link metadata pending content admissibility; the candidate is P3 metadata-only. P32.20 instead makes structural/schema preflight of audit spreadsheets a deliverable. “Without prohibited rows” is not an acquisition mechanism. An ordinary XLSX fetch acquires an archive that can contain cell values and shared strings before a parser decides which rows to retain. Header inspection after download would not meet the stated no-acquisition boundary.

**Required correction:** make the pilot's default preflight use only an independently available schema, publisher metadata, or a separately approved safe aggregate artifact. A raw audit-file URL must cause no transport call before the explicit content decision; test that refusal. Do not make acquiring SRC-027 necessary for San Diego dossier completion. A safe aggregate that is later approved is a separately bounded target with its own rights/content decision and lineage, not an implicit extension of approval for annual reports. No audit workbook was fetched in this review.

### SP-04 — The incremental source-pilot cap could expand from two families to five (P1 scope correction requested)

**Observed:** S5 caps the round at three dossier packages plus two non-portfolio families, ten sampled documents/rows per additional family, and two new adapter protocols. P32.21 runs after the three dossiers but initially said “first batch <=5 candidate families.” It did not state whether the completed cities were included. Read literally as five additional families, it permits eight overall and loses the sample/protocol caps. P32.18–20 also did not carry S2's 12/12/16-document, six-profile and 120-assertion ceilings into their acceptance.

**Required correction:** encode the incremental/total distinction and caps in PLAN and generated contracts, plus an explicit stop/return-pass outcome at the limit. Use the proposed ceilings or document an intentional replacement; do not leave them implicit in research prose. The root has acknowledged this mismatch and said it will narrow P32.21 to two incremental non-portfolio families; that edit was not yet present at my last PLAN reread.

### SP-05 — A field-to-ontology mapping owner and a bounded adapter package are still needed (P2; correction requested)

**Observed:** P32.3 owns general role/count semantics; P32.12 owns a common adapter interface and field-to-locator goldens; P32.17 owns dossier answers. S2 explicitly leaves lifecycle encoding as a future S1/S2 decision. No deliverable currently names the per-document crosswalk from source span to existing predicate/qualifier, subject/role, valid-time/applicability basis and passport field, or owns a missing-predicate disposition. “Three pilot source families” names cities, while their inputs span HTML, statutes, policy manuals, templates, contracts/exhibits, annual reports and oversight recommendations. This is insufficiently bounded for an agent to know which format handlers and semantic mappings finish P32.12.

**Required correction:** give P32.12 ownership of a versioned mapping manifest for a named, bounded fixture/target list, consuming P32.3's semantics; make P32.17 consume the manifest. Each row should identify the existing ontology encoding or an explicit abstention/additive-schema proposal. Pin supported handlers and document shapes; a scan/OCR/new protocol outside that list gets a scoped follow-up, not silent general-purpose parser work. Include exception/context spans and signature-status assessments in goldens. Do not invent enum/predicate names through passport fields. The planned gate can be agent-ready without promising general legal extraction.

### SP-06 — Queue verification and method claims need precise labels (P2; bounded correction)

**Observed:** all 27 CSV rows parse; 16 are explicitly `primary_search_excerpts`, and others include sampled sections or failed retrievals. DESIGN's “verified shortlist” is stronger than that review depth. S5 correctly calls rank editorial and declines to fabricate numeric scores. P32.11 preserves this distinction. S5 also proposes a matched, timed generic-query versus gap-driven experiment, while P32.21 currently specifies only a before/after acquisition funnel.

**Correction:** call this a researched candidate inventory with per-row review depth. Either carry the matched comparison/time budget/blinded error review into P32.21 or explicitly label its outcome a descriptive pilot; a before/after funnel alone cannot show that the strategy caused better yield. This does not require expanding the experiment or treating editorial priorities as scientific rankings.

## Primary-source spot checks and preserved safeguards

All external observations below were made on 2026-09-25 using read-only web retrieval. They are not stored evidence captures, full legal reviews, or production assertions.

| Source | Independently observed | Consequence |
|---|---|---|
| [Copyright Act §105](https://www.copyright.gov/title17/92chap1.html#105), with §101 definition | Federal-government authorship has a specific statutory scope; §105 contains qualifications. | S5 is right not to turn an official municipal host into automatic CC0. This does not establish any particular source's infringement or invalidate a scoped prior operator decision. |
| [Copyright Office Compendium §313.6(C)(2), pp. 37–38](https://www.copyright.gov/comp3/chap300/ch300-copyrightable-authorship.pdf) | Distinguishes government edicts from other state/local works that may be registrable. | Preserve separate source-byte, third-party, factual-extraction and output-publication review; do not equate public-record availability with universal reuse permission. |
| [Tulsa private-camera MOU, pp. 2–3](https://www.tulsapolice.org/_files/ugd/a38616_1ba001cbd33c42a0b7865625318d0dfa.pdf) | Extracted text has unfilled licensor/signature/date fields and Attachment A; its term references a separate agreement. | Supports S2's template/no-participant-edge case. No executed City procurement or participant roster was established. I did not visually verify signatures. |
| [City–Ubicquia agreement, PDF p. 4, §§2.3 and 3.1](https://www.sandiego.gov/sites/default/files/cosd-public-safety-agreement-ubicquia.pdf) | Effective date depends on the last party's execution and City Attorney approval; compensation is a not-to-exceed amount. | Supports keeping effective date, signatures, contract ceiling and spending distinct. Only selected text was inspected; complete execution, current operation and all attachment precedence were not adjudicated. |
| [OSCN provision](https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=478582) | This review received an OSCN human-verification page. | Cannot independently reconfirm the 2027 effective-version observation; retain S2's historical-version/applicability task. No challenge bypass attempted. |
| [OKC Flock usage page](https://www.okc.gov/Services/Public-Safety/Police/Flock-Safety-license-plate-reader-LPR-usage-in-Oklahoma-City) | This review received HTTP 403. | Did not independently reconfirm 90/109 counts or the October 1 retention announcement. Preserve their earlier observed research status and require permitted actual captures before production use. |

No contradiction to the research's restrained source summaries was established in these spot checks. Failed retrieval is a review limit, not evidence that a document or policy is absent. Publication/revision, retrieval, claimed world-validity and execution dates must remain separate; S2 correctly forbids using text-extraction offsets as raw-PDF offsets and refuses to treat one signature date as complete execution.

## Novelty and P31 overlap

The parsed baseline registry contains 339 rows. I independently confirmed existing Sourcewell and FAA waiver reference entries and Berkeley/Boston reference entries with ingestion permission not set. Seattle already has a permitted CCOPS row; an OIG-specific target still needs overlap/source-lineage review. P31.12 and P31.13 explicitly own the eight GAO/DHS/UK/FEMA/CCOPS sources and the catalog retry tail identified by S5. These checks support the plan's improve-existing versus genuinely-new distinction; I found no duplicate onboarding instruction in the candidate inventory.

Do not count City SDPD reports and City-hosted copies as independent publishers merely because URLs or genres differ. PAB institutional authorship can add an oversight role while preserving related municipal provenance. The research already states these limits. No numeric priority score or measured independent yield was verified or claimed.

## Review limits and handoff

This review read the root instructions and deferral context, BRIEF, DESIGN, PLAN, S2/S5, the CSV, relevant S3 review contracts, registry entries and P31.12/.13 contracts. PLAN changed during review; corrections observed above are recorded explicitly, while promised changes are not marked verified. Generated tickets and canonical §55 were still being authored and were not audited as final artifacts. No source row, permission, claim, gate, ticket, publication or historical document was changed. Only this review file was written. No tests were run because this is a plan review, not implementation verification; no claim of dossier completion, legal clearance, human adjudication or adapter readiness follows from it.

## Closure recheck — 2026-09-25

Bounded reread after root corrections: PLAN, DESIGN, the generated contracts for P32.2/.11/.12/.17–21, HUMAN-H4 and GATE-G3, and §55 in both `spec_src/96b_partXI_s55_six_streams.md` and the built canonical specification. All ten selected generated contracts contain their PLAN deliverable and acceptance strings with no mismatch. No new browsing, ingestion, implementation or broad review was performed.

| Finding | Status at planning-contract level | Closure evidence |
|---|---|---|
| SP-01 completion | **RESOLVED** | P32.17, DESIGN and SIG-DOS-002 preserve the fixed twelve-question threshold and mandatory subscores. GATE-G3 permits a recorded reduced/incomplete publication scope without awarding pilot-completion credit. S2 remains the cited profile/rubric source; completing a city matrix still requires keeping profile applicability distinct. |
| SP-02 documentary human review | **RESOLVED** | HUMAN-H4 deliverable 5 separately assigns semantic reviewers and records dossier rubrics and unsupported/unknown findings. The generated marker names `docs/build/readouts/HUMAN-H4.md`, requires actual authority/date, and blocks consumers while incomplete. DESIGN separates that review from device labels; GATE-G3 requires it. This is an owned future human stage, not evidence that review happened. |
| SP-03 workbook boundary | **RESOLVED** | P32.20 now limits preflight to independently supplied safe schema/link metadata, expressly forbids workbook transport including shared strings before content authorization, and makes SRC-027 optional metadata-only research. Its acceptance bars raw workbook/person/plate/per-search acquisition. The broader §55 preflight requirement can be satisfied through this safer method; it does not require raw acquisition. |
| SP-04 scope ceilings | **RESOLVED** | P32.21 now permits at most two incremental non-portfolio families, ten approved documents/aggregate rows each, two new protocol families, and five families total including the cities. Its acceptance enforces the ceilings and excludes SRC-027 from the acquired batch. Generated dossier contracts load S2 and require its research/live-packet resource bounds, retaining the 12/12/16-document and 120-assertion portfolio ceilings. |
| SP-05 mapping and adapter sizing | **RESOLVED** | P32.2 explicitly owns the field-to-existing-LinkML/DB mapping before adapters, including lifecycle, money, roles, exceptions and applicability. P32.12 owns the named-target source-span-to-predicate/qualifier/role/time/dossier crosswalk, consumes P32.2/.3, rejects unmapped required fields pending a scoped amendment, and caps its implementation at two existing protocols and twelve representative documents. OCR/additional parser stacks require a separately sized contract. |
| SP-06 labels and method claims | **RESOLVED** | DESIGN now calls the CSV a researched candidate inventory with per-row review depth. P32.21 explicitly labels a non-comparative pilot descriptive and does not claim causal superiority even for its small optional comparison. The final contract's smaller optional timing is a deliberate refinement of the earlier research proposal under §55.1's precedence rule. |

**Closure disposition:** no unresolved P1 source/dossier planning blocker and no new P1 found in this bounded recheck. The initial findings remain above as the audit trail. These closures concern contract adequacy only: exact approved fixtures/targets, actual captured bytes, legal/applicability assessments, independent human readouts, gate decisions and live outcomes remain execution obligations. The original spot-check limitations, including blocked OKC/OSCN retrieval and unverified signatures, remain unchanged.
