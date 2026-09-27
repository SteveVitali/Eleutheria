# S2 — Three local dossiers as an evidence-to-answer acceptance portfolio

Research date: 2026-09-25. Planning baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`. This is research and a proposed design, not an ingestion, publication, legal determination, independently adjudicated dataset, or report of completed implementation.

## Decision

Build three small, unusually defensible dossiers for Oklahoma City, Tulsa, and San Diego before expanding the number of source families. Their differences test the graph's central promise: an accountable answer must distinguish ownership, procurement, policy, configuration, access, and evidence of actual use. A map point cannot answer these questions alone.

Use the existing ontology and claim spine. The proposed agency/program passport is a versioned export/view composition, not a new canonical `Program` entity or another database. `Organization`, `Deployment`, `DataSystem`, `Contract`, `FundingInstrument`, `Policy`, `LegalInstrument`, `ConfigurationState`, `Claim`, `Resolution`, `ResearchTask`, and `CoverageRecord` already provide much of the vocabulary in `ontology/src/ontology/schema/entities.yaml`. Any genuinely missing predicate or relation must be proposed explicitly through the ontology/spec process; a passport field does not silently become an ontology predicate.

Initial ceiling: three lead agencies, six program profiles, forty documentary captures, and 120 candidate normalized assertions. Allocate up to twelve documents each to OKC and Tulsa and sixteen to San Diego; these are ceilings, not volume targets. Use two profiles per city: OKCPD Flock and the distinct Oklahoma UVED authority context; Tulsa fixed Flock and Axon Fleet/in-car ALPR; San Diego streetlight/ALPR and Vigilant database access. UVED belongs to a different administering organization and must never be represented as a second OKCPD deployment. Supporting contracts, policies and organizations do not count as additional programs. Expand this portfolio only after the evidence and user-task gates below pass.

## What was actually inspected

All web observations below were made on 2026-09-25. “Opened text” means the tool returned the page/PDF text; it is not an OCFL capture or a visual verification of a signature. Long documents were sampled at the stated sections, not read in their entirety. Search-only and failed retrievals are explicitly marked. No audit spreadsheets containing potential query or personal data were fetched. URLs and page references are research leads; implementation must acquire permitted evidence through the normal gate and record actual bytes, digests and locators.

### Oklahoma City: a strong local temporal and applicability case

| Document | Review and usable evidence | Limit / next verification |
|---|---|---|
| [OKC Flock usage page](https://www.okc.gov/Services/Public-Safety/Police/Flock-Safety-license-plate-reader-LPR-usage-in-Oklahoma-City) | Opened HTML. Separates 90 city-owned readers in 2026 from 109 partner agencies as of August 18; announces retention changing from 30 to 7 days effective October 1, 2026, with an investigation exception. Links the council packet. | Agency assertions; partner count is not a device count or a list of individually established sharing edges. Announced future operation requires later verification. |
| [August 18, 2026 council memo](https://www.okc.gov/files/assets/city/v/1/police/documents/flock/flock-council-memo-august-2026.pdf) | Opened both pages. Agenda IX.B, Amendment 1/Renewal 3, contract C241032; $270,000 for July 2026–June 2027. Identifies funding and amendment context. | Memo includes inconsistent original-approval dates; preserve both until council minutes/original agreement resolve them. A memo is not execution evidence. |
| [August 2026 amendment](https://www.okc.gov/files/assets/city/v/1/police/documents/flock/flock-amendment-august-2026.pdf) | Two-page extracted text was accessible in an earlier read; later retrieval returned 403. Actor-specific federal disclosure restrictions, compulsory-process exceptions and precedence are the important clauses. | Signature block text was incomplete/garbled; execution and effective date are **not verified**. Obtain authorized bytes and inspect all signature fields. Do not infer a prohibition on every City sharing action from a restriction on Flock. |
| [June 15, 2026 police manual](https://www.okc.gov/files/assets/city/v/2/police/documents/operations-manual-6th-edition-june-15-2026.pdf) | Existing repository target in `connectors/src/connectors/data/live_targets.toml`; connector maps a retention ceiling and approval condition. Target configuration/code was inspected; this pass did not independently read the entire manual. | Reacquire/version through gate, identify exact section and applicability, compare ceiling versus configured period. A URL version and retrieval date are not policy effective dates. |
| [OSCN statutory page](https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=478582) | Opened text. Page identifies a version effective January 1, 2027 and defines the UVED program. | Must retrieve the version effective for the dossier's world date. Program-specific language cannot become a universal restriction on an unrelated OKCPD deployment without an applicability link. |
| [DAC UVED program](https://oklahoma.gov/dac/about/staff/about-the-uved-program.html) | Opened HTML. Supplies the administering authority and insurance-enforcement program context. | Statewide intent does not establish deployment in every jurisdiction. Do not acquire plate or insurance records. |

The usage page also links a renewal letter and availability-of-funds document. Those links were discovered; the renewal retrieval failed and their contents were not reviewed. Treat them as unfinished discovery tasks, not supporting citations.

Repository observation: `connectors/src/connectors/okc_documents.py` builds claims from configured targets and uses the retrieval date as observation time; `live_targets.toml` assigns the statutory target to `sig:deployment:okc-okcpd-flock` and normalizes an insurance-use restriction. The configured raw statutory fragment contains an additional legal exception. This is a **semantic review hypothesis** requiring S1's captured-byte trace, historical statute and subject-applicability adjudication, not a demonstrated legal violation or a executed regression test. Do not rewrite historical claims; a confirmed correction must append a superseding claim and resolution.

First answer card: “What does OKCPD own, what can it access, who can authorize sharing, and what changes on October 1?” Distinguish 90 owned devices, 109 partner agencies, and the earlier project's 299 metro/190 city device assertions. They have different units, ownership, geography and dates; numerical disagreement alone is not a contradiction. The earlier counts are audit leads, not freshly verified counts for this dossier.

### Tulsa: separate product, camera ownership and connection modes

| Document | Review and usable evidence | Limit / next verification |
|---|---|---|
| [TPD Flock page](https://www.tulsapolice.org/flock-safety) | Opened HTML. Describes operation since summer 2022, camera registration versus business integration, and the RTIC organizational context. | Registration/contact permission and live integration are different relationships. This page does not prove a particular business joined. |
| [Camera integration MOU](https://www.tulsapolice.org/_files/ugd/a38616_1ba001cbd33c42a0b7865625318d0dfa.pdf) | Opened three-page text including signature and Attachment A fields. Published **blank licensor template**, with terms tied to a separate City agreement. | Not a signed participant MOU, City purchase agreement, participant roster or proof of installed cameras. No participant or organization edge may be fabricated from blank fields. |
| [Policies index](https://www.tulsapolice.org/policies-and-procedures) and [113C ALPR policy](https://www.tulsapolice.org/_files/ugd/a38616_35b77a7578bc48ec86119fe85d64094b.pdf) | Index and all three pages of 113C opened. Document shows July 7, 2023 effective/approval date, distinguishes Flock fixed systems from Axon Fleet 3, and describes access/request handling. | Published index does not establish that a 2023 file is the latest enforceable version. Retention language for manually entered data must not be generalized to every scan. |
| [113E Public Safety Technology policy](https://www.tulsapolice.org/_files/ugd/a38616_f8b3b9208064440d87032e9e26eefe88.pdf) | Opened all three pages; October 4, 2023 date. Approval, access, sharing and purpose-related retention are documented. | Does not supply a uniform numeric retention period. General institutional rule and product configuration remain separate. |
| [Commercial Corridor Safety Guide](https://www.cityoftulsa.org/government/departments/planning-and-neighborhoods/community-planning/commercial-corridor-safety-guide/) | Primary search excerpt only; a device-count lead and multiagency-network description were found. | Not accepted as a current count. Open page, establish date/scope and follow supporting records before using. |

Bounded searches did not find an executed Tulsa City Flock purchase contract in this pass. Record `searched_not_found` with query/date/site scope, never “no contract exists.” Priority next leads are the City clerk/council packet linked by contract number, finance purchase order and renewal records. Existing agenda-tenant discovery already identifies Tulsa's Granicus family; do not describe this as discovery of a wholly new agenda platform. Do not send a records request as part of this plan.

First answer card: “Which technology does Tulsa operate, what is a business actually agreeing to, and what remains undocumented?” Showing the missing executed contract is an honest useful answer, but the contract-chain completion gate must remain unresolved.

### San Diego: procurement, public reports and independent oversight

| Document | Review and usable evidence | Limit / next verification |
|---|---|---|
| [SDPD technology inventory](https://www.sandiego.gov/police/data-transparency/technology) and [ALPR detail](https://www.sandiego.gov/police/data-transparency/technology/view?tech=Automated+License+Plate+Recognition+(ALPR)) | Opened HTML indexes. Discover annual reports, use policies and audit links with version labels. | Index label alone is not the document's effective date. Latest linked use-policy retrieval returned 403. |
| [2025 annual surveillance report](https://www.sandiego.gov/sites/default/files/2026-02/sdpd-annual-surveillance-report-2025.pdf) | Opened selected sections of 132-page PDF: Vigilant, ALPR, and UAS. Vigilant is described as subscription access without hardware assets; ALPR section reports approximately 500 locations and a retention exception. | Agency-reported 2025 activity, not independent efficacy evidence. Do not turn database access into local sensor points or transfer this year's counts to another date. |
| [Revised 2024 report](https://www.sandiego.gov/sites/default/files/2026-03/sdpd-annual-surveillance-report-2024-revised-260306.pdf) | Primary search excerpt only; revision/upload labels differ. | Discover revision lineage and compare targeted sections; not reviewed as a complete report. |
| [City–Ubicquia agreement](https://www.sandiego.gov/sites/default/files/cosd-public-safety-agreement-ubicquia.pdf) | Opened selected text of 85-page agreement: main agreement, signature page and initial scope/definitions. Names the prime contractor, incorporates Flock terms, sets contractual precedence, five-year term from effective execution, $11,662,500 ceiling and initial 500 units. | Vendor date appears in extracted signature text; City execution and attorney approval are not visually verified. The contract ceiling is not expenditure; a contracted unit is not necessarily an active ALPR sensor. Preserve prime/subvendor/product roles and attachment precedence. |
| [December 10, 2025 council memorandum](https://www.sandiego.gov/sites/default/files/2025-12/rfi-alpr-technology-contract-memorandum-12.10.25.pdf) | Opened one-page text; requests procurement reconsideration and identifies the existing vendor/subvendor arrangement. | Memorandum's description is not independent proof of the agreement's complete execution chain. |
| [May 20, 2026 budget responses](https://www.sandiego.gov/sites/default/files/2026-05/fy27-brc-referral-responses-day5-may-2026-with-attachment.pdf) | Opened relevant pages 2–3 of ten-page PDF. Page 3 identifies ALPR RFI 30000062-26-E and citywide video RFI 30000063-26-E, and planned separate competitive procurement. | RFI, anticipated procurement, executed agreement, appropriation and payment must remain distinct. Page 2's proposed spending is not an award. |
| [Privacy Advisory Board reports](https://www.sandiego.gov/pab/reports) and [2025 ALPR recommendation PDF](https://www.sandiego.gov/sites/default/files/2026-05/pab-final-recommendation-alpr-2025-asr-00235352xbde34.pdf) | Reports index opened; primary search excerpt of recommendation reviewed. Direct PDF retrieval failed due to tool's content-length limit (~16 MB). | Oversight recommendation is not an enacted ban or evidence Council adopted it. Full recommendation has not been read; acquire via an approved method before normalization. |
| [FY2024 City contracts](https://www.sandiego.gov/purchasing/bids-contracts/contracts2024) | Opened HTML table and coverage statement; document links and procurement types are available. | FY heading, row award dates and displayed total are not reliably interchangeable. Page includes dates outside its stated FY range; validate rows individually. Do not treat every “security” purchase as surveillance. |

The ALPR index exposes 2024–2026 network-audit spreadsheets. Only link metadata was reviewed. Before fetching any such file, determine whether the existing acquisition boundary permits its content, because query logs can contain identifiers, people, incident details or officer names. A label saying “redacted” is not a sufficient admissibility check. If a safe agency-level sharing summary can be isolated through an approved workflow, it could close the declared-versus-observed relationship gap; otherwise use aggregate reports and document the unknown.

First answer card: “Who supplies the combined system, who buys it, what can police access without owning cameras, and what did oversight actually recommend?”

## Passport and assertion contract

The passport is a projection keyed by stable agency identity, scoped program identity, world date, belief/release revision and output compartment. A program grouping is initially an export grouping of existing Deployment/DataSystem entities. It must carry its grouping rationale and member identities rather than making a product name a universal identity key.

| Section | Required fields / behavior |
|---|---|
| Identity and remit | Stable organization ID, jurisdiction IDs, aliases with source, governing/operating/buying/funding organizations separately, technology/product/vendor identities, grouping rationale. |
| Scope | Geographic boundary and resolution, owner class, sensor/system/access unit, active/planned/contracted status, fixed/mobile status, inclusion/exclusion rules, count universe and date. Unknown geography does not become a centroid. |
| Procurement and money | Contract identifier, parties and roles, master/local/amendment relation, lifecycle events with evidence, amount type/currency/period, line-item allocation or explicitly unknown. Award ceiling, budget, invoice and payment are distinct. |
| Capabilities and use | What the system can do, what policy allows, agency-reported use and independent observation separately; DataSystem access can exist without local devices. |
| Governance | Exact policy/version, adopting body, permitted purpose, retention scope/exceptions, sharing authorizer and recipient class, oversight status and response. Record legal applicability rationale or unresolved status. |
| Relationship | Subject/object identities, direction, data categories, mode (asserted, contractually permitted, configured, observed), period and evidence. Do not infer named edges from an aggregate partner count. |
| Time | Source publication/revision date; capture/observation date; claim valid interval and bound kinds; decision/ingestion time; pinned release. Never fill unknown valid dates with fetch dates. |
| Evidence and uncertainty | Claim/evidence/resolution IDs, original and derived hashes, locator/context, evidence role/directness, lineage family, mapping version, admissibility/review status, unresolved research task. |

Lifecycle labels such as proposed, council-approved, vendor-signed, fully-executed, effective, renewed and terminated are separate evidenced events. Do not collapse them into a single Boolean. Their exact canonical encoding is an S1/S2 design decision, not a claim that every label already exists in the ontology.

Unknown handling: map actual assertion absence to existing `AbsenceKind` values after schema review. Keep research workflow status (`not_researched`, `searched_not_found_in_scope`, `access_blocked`, `version_unverified`, `not_applicable`) in a companion research record, not invented canonical absence enums. Each unknown states what was searched, when, why it matters, next evidence needed and closing condition. “No record found” must never become “no system,” “no sharing” or “zero devices.”

## Trace and extraction design

Every normalized assertion must traverse this chain:

`publisher URL → authorized raw capture/hash → derived text artifact/hash + extractor/version → raw page/bbox/DOM/cell locator and supporting text span → literal + normalization/mapping version → subject/scope/applicability decision → claim → resolution decision → pinned export release → user-visible citation`.

`parsing/src/parsing/locator.py` currently validates exactly six locator shapes: page, bbox, cell, row, byte range and DOM path. PDF pages are one-based; sheet cells/rows are zero-based; byte ranges are half-open into raw capture bytes. Do not insert new freeform keys into that strict locator structure or use offsets from web-tool/PDF text extraction as raw-PDF byte offsets. Store a derived artifact plus explicit transformation linkage, or make a reviewed additive schema extension. Evidence viewers must name which artifact their offset addresses.

For clauses, keep the governing heading, lead-in, exception, definition and relevant cross-reference as contextual spans. Normalize actor, modal force (may/must/must not), object, condition and exception separately before producing a short user sentence. Composite claims require all supporting spans, including attachment precedence and effective-date prerequisites. If the mapping cannot express a material exception, emit a bounded literal or abstain; do not emit a stronger convenient predicate.

Signatures require authorized page rendering plus a recorded reviewer assessment of parties, dates, blanks and approval conditions. A DocuSign envelope ID or one extracted signature date is insufficient. No names of individual officers are required in the public passport; institution/role is enough. Signature review is about document execution, not collecting personal signatures for publication.

Deduplicate raw bytes by digest; link differing bytes that reproduce the same origin document as a lineage family; keep revisions and amendments distinct. A City-hosted agreement, agenda attachment and cooperative-contract copy are not three independent confirmations. Citation choice can prefer the best official copy while preserving all captures. Clause changes do not overwrite previous versions.

## Completion and unknowns rubric

For each agency answer twelve questions: (1) operator/buyer/funder; (2) technologies and products; (3) owned inventory and count universe; (4) external database/network access; (5) procurement and money basis; (6) authority and applicability; (7) retention and exceptions; (8) sharing actors and mode; (9) effective/change timeline; (10) oversight findings and institutional response; (11) independent support versus agency statements; (12) unresolved evidence and correction route.

Each question earns 0 unresearched; 1 bounded documented unknown; 2 traceable partial answer; 3 traceable sufficiently scoped answer. A dossier is **reviewable** only when all twelve have status, every displayed factual assertion has a working trace, and no material unsupported inference survives review. A dossier is **evidence-complete for the pilot** at ≥28/36, with questions 1, 5, 7 and 8 at least 2 and no unresolved material execution/applicability issue disguised as fact. This threshold is a proposed pilot rule, not scientific validation. Lower-scoring dossiers may be published only as explicitly incomplete research views under separate publication approval; they do not pass the pilot completeness gate.

Do not optimize the score by deleting hard questions or counting ten mirrors. Report the full matrix, number of source lineage families, and known-search denominator. All material governance/relationship/contract assertions receive independent human review under S3. If humans or permitted captures are unavailable, mark that stage `not_run` and retain a return path; software tests cannot claim human acceptance.

## Exact acceptance cases to carry into ticket contracts

1. **Scope:** fixture values 90 owned readers, 109 partner agencies and historical metro/city counts remain separate; count reconciliation produces no contradiction merely because values differ. A same-scope, same-period conflicting pair does produce a reviewable contradiction.
2. **Time:** a September 25, 2026 view does not assert the announced October 1 retention change as already operational. A later world-date query still labels it announced until operation has support. Historical release replay preserves its earlier belief.
3. **Meaning:** a retention ceiling, default configuration and investigation hold are separate assertions. A shorter default is not automatically a policy breach or contradiction.
4. **Actor:** restricting vendor disclosure does not automatically forbid City-authorized disclosure; compulsory-process exceptions remain visible. Omission of a material exception rejects the normalized claim.
5. **Applicability:** a future-effective UVED statutory provision does not become a current OKCPD rule without both correct version and evidenced applicability. Rejection produces a research task, not a fabricated negative.
6. **Execution:** blank Tulsa MOU emits template terms only and zero participant-sharing edges. Partially evidenced signatures leave execution unknown. Approval memo alone never satisfies executed-contract evidence.
7. **Identity:** Tulsa Flock fixed and Axon Fleet systems remain separate unless an explicit supported relationship connects them. San Diego's subscription-only database access emits no invented local sensor geometry.
8. **Procurement:** RFI, sole-source justification, contract ceiling, proposed spending and expenditure are distinct. Prime/subvendor/product roles survive export. Duplicated contracts across portals do not inflate independent-source support.
9. **Oversight:** PAB recommendation does not mutate adoption/operational status. Agency response and reviewer finding retain their authorship and disagreement.
10. **Trace:** every display assertion reopens the exact pinned permitted artifact and locator; transform-offset mismatch or missing hash fails. A changed live URL cannot alter the historical citation. No search snippet is admissible as a production evidence capture.
11. **Correction:** a confirmed semantic correction appends supersession/resolution and produces a new release; the prior release stays retrievable with its original claim and subsequent correction notice.
12. **Privacy/rights:** no plates, trips, individual query records or ungated officer names enter the pilot fixture/public export. Source availability does not authorize acquisition or redistribution; restricted material has a visible citation/metadata-only fallback if permitted.

These are proposed tests, not results of tests run in this planning session.

## Newsroom and community acceptance workflow

Prepare two short tasks per city with the answer rubric hidden: identify a defensible factual sentence with exact supporting page; explain one tempting but unsupported conclusion. Add a shared “what changed between these dates?” task and a correction task. Recruit, with operator authorization, at least two newsroom/research users and two community-accountability users; target six participants for practical diversity, without representing this as a statistically representative study. Do not contact participants during implementation without authorization.

Run sessions against a frozen release, record completion and the actual cited evidence with consent, and ask each participant to mark what they would confidently publish, investigate or challenge. Suggested pass: at least 80% of core tasks completed correctly, median verified-citation time ≤3 minutes, every participant can identify a prominent uncertainty, and zero material false conclusions induced by the interface that remain unaddressed. Small-sample rates are descriptive; report numerator/denominator and failures. Use at least one screen-reader/keyboard session through S4's accessibility evaluation. Simulated agents may dry-run the script but do not count as humans.

Human adjudication controls truth labels (S3); these sessions evaluate usefulness and comprehension. Failures route to semantics/trace work (S1), editorial grouping (S2), or navigation/citation work (S4), with a new frozen release for retest. Publication requires the existing gates independently of usability success.

## Proposed engineering units and dependencies

| Unit (proposal, not final ticket ID) | Concrete deliverable | Dependency and close condition |
|---|---|---|
| S2-A passport projection and trace contract | Versioned JSON/view contract, ontology mapping table, explicit unknowns, fixtures for the twelve cases | S1 artifact/temporal/correction interfaces; no new canonical entities without review. All trace and scope cases pass on deterministic authorized fixtures. |
| S2-B1 OKC evidence packet | ≤12 documents, historical-law/applicability review, contract-amendment timeline, scoped count table | Existing source authorization revalidated for exact targets; blocked execution/version questions stay explicit. Independent semantic review and rubric recorded. |
| S2-B2 Tulsa evidence packet | ≤12 documents, product split and template-versus-executed chain | Rights/access decisions and a bounded contract search. Cannot declare evidence-complete while the contract requirement remains below threshold. |
| S2-B3 San Diego evidence packet | ≤16 documents, vendor role chain, oversight/reply timeline, database-access profile | Safe document acquisition, signature review, no raw network logs. Rights and execution unknowns preserved. |
| S2-C frozen portfolio and user acceptance | Three rendered dossiers, question matrix, exact citations, session kit and recorded results or explicit pending-human state | S3 independent adjudication and S4 citation/navigation. Publication is a separately gated live stage with a return path. |

Seattle OIG annual reports or Berkeley's policy/report/MOU collection are credible replacements if a city's rights/access gate cannot be resolved after two bounded research sessions. Use the same questions and score; do not switch merely to conceal a hard negative. See S5 for primary links and precise novelty. The pilot's value is proving complete evidence-backed answers, not claiming exhaustive city inventories.
