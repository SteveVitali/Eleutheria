# Appendix G — Corrections and material extensions to the source outline

The outline instructs the downstream agent to "re-verify the ecosystem yourself" and to "contact
assumptions with evidence" (OL-24-01, OL-24-03). This appendix records what that produced. **Nothing
here removes an outline obligation**; every item either corrects a fact, sharpens a model, or adds
something the outline did not have.

## G.1 Factual corrections

| # | Outline says | Verified reality | Consequence |
|---|---|---|---|
| C-01 | ~~DeFlock is at `deflock.org`~~ | **WITHDRAWN — the outline was right.** An intermediate finding claimed `deflock.me` was canonical; it is not. `deflock.me` 301-redirects to `deflock.org` behind a Cloudflare challenge that fires first, so a compliant client sees only the 403 (G.4.2 #1, SC-19) | **Use `deflock.org`.** Registry carries both hosts and both observed behaviours |
| C-02 | ALPR Watch is a FOIA→SQL→Superset pipeline (OL-2C-AW-01) | It is now substantially an ALPR-avoidance routing and offline-data project built on DeFlock; **code is on GitLab, not GitHub**; the Superset dashboard persists as one component | Connector and collaboration targets change |
| C-03 | FlockReporter is the local-group directory (OL-3-02, OL-18-13) | **Did not respond** when tested | SIG maintains its own registry (SIG-TASK-014); risk R-12 |
| C-04 | Flock portals demand "snapshotting and temporal preservation" (OL-2B-FP-04) | **403 on every path including `robots.txt`** — a managed challenge. No lawful path *to the vendor* | **Superseded in part:** the layer is obtainable from a public CC BY-SA 4.0 aggregator API (SC-18), so Phase 11 is ungated. Direct vendor capture remains impossible, and the fallbacks stand |
| C-05 | MuckRock API (OL-Q07) | It is **api_v2**, not v1; **401 on every data endpoint**; 5-minute JWT; ~15 req/min | Connector design and expectations change |
| C-06 | A crowdsourced figure of 850,000+ private cameras across 324 communities (OL-4.1-04) | Independent enumeration found **321 communities**, and the 850k figure sums two incommensurable counters (registered + "integrated"), where "integrated" counts what an org can *see* through federation, not distinct cameras | The outline's own instruction to verify before treating as canonical, vindicated |
| C-07 | `Fusus integrates Flock ALPR` as a canonical example (OL-C-01, OL-4.1-02) | Axon **severed** API interoperability with Flock in 2025 | The outline's flagship integration example describes a terminated relationship; `applies_to_cohort` is required on edge termination |
| C-08 | ShotSpotter leak of "more than 25,000" sensors (OL-4.5-01) | The downloadable derivative holds **22,471** points | Do not repeat the press figure |
| C-09 | Ring/Neighbors partnerships as a category (OL-ES-16, OL-2D-AT-05) | The model is **two policy reversals stale**; and the Atlas *retired* the Ring category in 2024, deleting ~2,530 datapoints | **Absence of Ring data after 2024 means "category retired", not "program ended"** — SIG-ONTO-059 |
| C-10 | A circulating figure of ~336K ALPRs on OSM | Measured `surveillance:type=ALPR` = **144,312** | Not corroborated; unusable without a primary source |
| C-11 | Atlas licence unclear across research | **`CC-BY-4.0` with an explicit third-party-content caveat**, attributed to EFF + Reynolds School of Journalism | `redistributable` must be separately reviewed, not derived (SC-09) |
| C-12 | Web archiving as a general fallback (OL-2B-IND-01) | **`*.flocksafety.com` is excluded from the Wayback Machine** | There is no third-party archive fallback; SIG's archival role becomes ecosystem-critical |
| C-13 | Court records as an ingestion source (OL-2E) | Open endpoints are rate-limited to ~5/min, 50/hr, 125/day | Targeted lookup only; bulk court ingestion is void |
| C-14 | Data-quality tooling assumptions | Several widely-recommended tools have moved to source-available licences | Licence must be re-verified at adoption (SIG-ENG-018) |

## G.2 Model corrections

| # | Outline model | Correction | Section |
|---|---|---|---|
| M-01 | `Claim.source` — one source per claim (OL-8.16-02) | A claim has an **evidence set with roles**, including `contradicts` and `attests_absence` | §10.3.6 |
| M-02 | Two implied time dimensions (OL-6.3-02, OL-9.2-01) | **Five** dimensions across two layers; only two are `AS OF` axes; observation time is an ordering scalar | §9.2 |
| M-03 | No transaction time at all | Without it SIG **cannot reproduce its own past publications** or honour a citation of itself | §9.4, §16.2 |
| M-04 | `valid_to = NULL` (OL-6.3-02) | Ambiguous between "ongoing" and "unknown" — **opposite research tasks**. `valid_to_kind` is required | §9.3 |
| M-05 | Resolution as a computed view (OL-6.5-01) | A **stored decision record** with rationale, author, and an independently versioned ruleset | §16.4 |
| M-06 | Tier A–F as a reliability scale (OL-9.1) | It is a **genre** scale. A contract and a field observation are not equally reliable; they are reliable about *different things*. Four axes replace it | §10.4–10.6 |
| M-07 | Six flat confidence labels (OL-9.3-02) | Three of the six are on different dimensions; the enum cannot express "strongly supported but contested". Replaced by three orthogonal fields — a strict superset | §10.7 |
| M-08 | One lifecycle enum, 14 states (OL-6.7-01) | **Four orthogonal tracks**; "cancelled + still installed + unplugged" is three simultaneous states. All 14 retained, 10 added. **`replaced` is an edge, not a state** | §13.4 |
| M-09 | "Technology / capability" as one entity (OL-8.4) | **Three** entities: Technology (three-level, 101 terms), Capability (verb.object.scope), and a promoted ConfigurationState | §11.5–11.6, §11.15 |
| M-10 | Four ownership roles (OL-4.1-05) | **Fourteen** roles, with seven load-bearing separations — including that coordinate sensitivity must be assessed at the **role** level, because a rooftop sensor's coordinates endanger the *host* | §12.4 |
| M-11 | NULL for "unknown" | NULL cannot distinguish four epistemic states; `value_kind` (`value`/`somevalue`/`novalue`) plus `CoverageRecord` are required | §9.5, §32.1 |
| M-12 | No model of evidence decay | **Predicate volatility** with half-lives; and the `U5` rule, which is what stops SIG publishing a stale unchallenged number | §28.3, §28.5 |
| M-13 | Corroboration by counting sources | Sources copy each other. Corroboration counts **independence classes**, and SIG *declares* dependence rather than inferring it | §10.8 |
| M-14 | Append-only with no suppression (OL-19.3) | The first valid privacy demand would force a destructive delete. **Suppression is a distinct primitive** | §45.4 |
| M-15 | Public-interest balancing for all officer data (OL-13.2) | Correct for names; **wrong for home addresses**, which must be categorical | §43.2 |
| M-16 | Seven product surfaces (OL-15) | An eighth is required: a **public corrections log** | §39.8 |
| M-17 | Tasks that only say "go find X" (OL-12) | Without a **disposition vocabulary**, "searched, found nothing" is unrecordable and the queue can only grow | §33.4 |
| M-18 | Strategy A as a viable ODbL posture (OL-14.1) | Separation alone does not avoid share-alike: a join key **is** a reference, and physical separation is expressly insufficient | §42.3 |

## G.3 Material additions

| # | Addition | Why it matters |
|---|---|---|
| A-01 | **Cooperative purchasing vehicles** | A dominant acquisition channel that publishes full competitive records for free — while the agencies riding them generate **no local RFP** |
| A-02 | **Federal grant sub-award tracing** | Identifies deployments that appear in no local procurement record |
| A-03 | **Civic agenda platforms are real APIs** | Legistar, PrimeGov, CivicClerk, NextRequest all called successfully; **no municipality→platform directory exists and SIG should build one** |
| A-04 | **Municipal surveillance-ordinance inventories** | Statutory equipment inventories published on a legal cycle |
| A-05 | **Federal drone-authorization releases** | A regulator's dated records with native validity intervals — an unusually clean `authorization_state` source |
| A-06 | **The orphaned-device backlog, quantified** | Only **19.1%** of 144,312 mapped ALPRs carry an `operator` — ~116,800 devices. This is SIG's largest single body of addressable work and the clearest statement of its distinct value |
| A-07 | **Wikidata as a first-class crosswalk key** | `manufacturer:wikidata` on **83.4%** of mapped ALPRs — OSM has already done vendor entity resolution |
| A-08 | **`FundingInstrument` and third-party-funded surveillance** | BID/HOA/foundation purchases escape ordinances that regulate *agency* acquisition |
| A-09 | **`LegalInstrument`** | The outline lists laws among what must be represented but never models them |
| A-10 | **`CandidateAsset` as a separate entity** | If candidates share a table with assets, they eventually share a map |
| A-11 | **The `free_trial → active` path** | Capability acquired with no procurement paper trail — the most important edge in the state machine for discovery |
| A-12 | **Export/onward-disclosure capabilities** | Systematically absent from every public taxonomy, and where the harm actually lives |
| A-13 | **OSM already holds non-camera surveillance** | 3,250 gunshot detectors and 67 AFR nodes — the non-ALPR physical layer is free at Stage 1 |
| A-14 | **Shadow-mode replay** | A parser change that silently alters 40,000 claims must be seen before it lands |
| A-15 | **Archival succession for single-maintainer upstreams** | Several dependencies are one-person projects and the key vendor domains are unarchived; if they vanish, the record vanishes |
| A-16 | **The anti-misuse tension, addressed openly** | A project that hides from its hardest question is not credible on the easier ones |

## G.4 Research completeness

**Status as of 2026-08-20 (completion pass): all thirteen research workstreams are complete.**

An earlier version of this section recorded six open items caused by seven workstreams being
terminated mid-run by an account spend limit. The limit was lifted and the work was finished. The
record of what was outstanding, and how each was closed, is retained below — deleting it would erase
the evidence that the specification once rested on gaps.

| # | Was outstanding | Disposition |
|---|---|---|
| 1 | OSM Automated Edits Code of Conduct and Organised Editing Guidelines not read | **CLOSED.** Both read (SC-12, SC-14, R1-F1.27/28). The human-mediated design falls *outside* the Code's scope; the Guidelines apply and supply the changeset hashtag. Risk R-14 closed |
| 2 | Overpass and OSM element-history endpoints not tested | **CLOSED.** Both tested live (SC-17, R1-F1.17–F1.26). Q19 verified, and testing surfaced the element-repurposing dating trap (SIG-INGEST-045a) |
| 3 | Eyes on Flock internals, licence, collaboration posture unresolved | **CLOSED.** Public unauthenticated JSON API verified (SC-18, R2-F2.6); **CC BY-SA 4.0**; contact published. Phase 11 unblocked, risk R-02 closed |
| 4 | HIBF, ALPR Watch, Accountability Atlas, Abuse Library licences unresolved | **CLOSED, negatively for three of four** (R2-F2.16/18/19/20). Two state **no licence at all**; one is **mixed** (copyleft on some repos, nothing on the data tree); one adds an **affirmative refusal** with an EU DSM Art. 4 reservation. All now `UNDETERMINED` or `refused`, and the export gate is closed against them |
| 5 | DeFlock repository, export, and changeset signature undetermined | **CLOSED.** Canonical repos identified; the outline's cited repo belongs to a **different project**; **DeFlock has no data API** — there is no connector to build, the data is OSM; changeset signature is `created_by = "DeFlock <semver>"`, on ~75% of sampled ALPR edits |
| 6 | Seven workstreams terminated; R1/R2 reduced, R3 partial | **CLOSED.** All thirteen files now carry findings, open questions, and emitted requirements. R1 437→1,908 · R2 250→1,708 · R3 546→1,760 · R12 1,546→2,385 · R13 1,904→2,791. Cache total **26,818 lines, 501 findings, 667 requirements** |

### G.4.1 What the completion pass changed in the specification

The finished research did not merely confirm the draft. It produced eight corrections, four of
which changed requirements rather than confidence:

| Correction | Effect |
|---|---|
| The portal layer **is** lawfully obtainable | Phase 11 ungated; risk R-02 closed; the fallback chain retained because the API is a single dependency |
| The licence architecture is **N-compartment**, not two-way | A third share-alike regime (CC BY-SA 4.0) exists; a merged export would have been an invisible violation (SIG-LIC-004a) |
| **CC-BY-4.0 blocks upstream contribution** | OSM forbids importers claiming additional copyright; the contributed subset is dual-licensed **CC0** (SIG-LIC-007a) |
| **Capture–recapture is impossible here**, not merely caveated | `m₂` is undefined and the bias runs *downward*; prohibited, with one validation-only exception (SIG-METRIC-008) |
| A live **de-pseudonymisation join** exists in the ecosystem | Specific prohibition added; "already public" rejected as justification (SIG-PUB-003a–d) |
| Share-alike obligations **travel silently** | Provenance-aware rights gate; defaults to the stricter regime (SIG-LIC-009a) |
| Retention is reported as an **ordinal bucket** | Schema accepts duration *or* bucket; midpoints must not be fabricated (SIG-ONTO-035a) |
| OSM elements are **repurposed** | `first_observed` must come from the history walk, not the creation date (SIG-INGEST-045a) |

### G.4.2 Corrections to this document's own earlier findings

Recorded because a specification that hides its own error rate is not credible about anyone else's:

1. **`deflock.me` is not canonical.** An earlier spot-check (SC-04) read a `403` as evidence of
   canonicality and "corrected" the outline's `deflock.org` citation. **The outline was right.** The
   403 is a Cloudflare challenge firing ahead of a 301 to `.org` (SC-19). Withdrawn.
2. **"HIBF publishes no bulk export"** was inferred from three 404s; the export is one path level
   deeper (R2-F2.18). The conclusion sharpened rather than reversed — exports exist, a licence does
   not, and `robots.txt` forbids the path.
3. **The circulating "336K ALPRs" figure** has a probable origin: an unmaintained, unlicensed project
   whose headline claims it. Direct measurement gives 144,312 (SC-03, SIG-INGEST-048a).

### G.4.3 Residual open questions

These remain genuinely open and are carried in the risk register (§53) rather than presented as
settled:

1. Whether the aggregator's CC BY-SA grant is intended to cover the **API payload** as well as site
   content — material to §42.3's compartment boundary. A Stage-0 question for the operator.
2. Whether SIG's dual-licensing of the contributed subset (SIG-LIC-007a) satisfies the OSM community
   in practice, which is a consultation outcome and cannot be determined unilaterally.
3. The residual ODbL questions of §42.3 requiring counsel — unchanged, and correctly so.
4. Per-source licence positions for several newly discovered projects, two of which state none.

## G.5 Post-build reconciliation (2026-09)

After the 46-ticket build (P00.1–P18.2) and the capstone passes (P19–P20.1), the spec and the
built system were reconciled (ticket P20.2, ADR-062, gate HG-13). Nothing here removes an
obligation: seven items are **ticked normative amendments** (each with an ADR, so no requirement is
weakened silently — defining standard §3.1), and the remainder are non-normative index/wording
corrections. The reconciliation plan (`docs/build/SPEC_RECONCILIATION_PLAN.md`) carries the full
before/after text and the ticket-added disposition tables (`docs/build/TICKET_VS_SPEC.md`).

### G.5.1 Ticked normative amendments applied to `spec_src`

| # | Section | Change | ADR |
|---|---|---|---|
| A1 | §40 (SIG-UI-038, +SIG-UI-047) | A zero-JS static map is the **conforming default**; the interactive MapLibre renderer is an **optional progressive-enhancement island** (SIG-UI-047, MAY), not a precondition of conformance | ADR-051, ADR-018 |
| A2 | §32.1 (SIG-METRIC-001) / §33 (SIG-TASK-016a) | The residency barrier is recorded with `absence_kind = not_researched`; the closed absence vocabulary and its `not_researched` vs `searched_not_found` distinction made explicit | ADR-041 |
| A3 | §11.2 (`Organization`) | `canonical_name` is a **scalar** resolved label; the competing names it is chosen from remain claims | ADR-056 |
| A4 | §16.2 design-point #6 | Claim-table partitioning is **MAY** (deferred); it MUST preserve the `claim_id` PK/FK contract | ADR-022 |
| A5 | §31 (SIG-RECON-053), §32 (SIG-METRIC-001), §33 (SIG-TASK-002) | `Contradiction`, `CoverageRecord`, and research tasks MAY be **computed on read** or materialized; compute-on-read is the accepted Phase-8/9/10 form, persistence deferred to Phase 21 | ADR-037/038/039 |
| A6 | §34 (SIG-CONTRIB-002), §39.7 (SIG-UI-031) | A **CLI + JSONL** curation/review queue is a conforming Phase-5 form; the web surface is deferred to Phase 21 | ADR-030 |
| A7 | §47 (SIG-ENG-012) | `evidence/` added as a member package of the frozen layout | ADR-023 |
| A8 | — | No further `P20.2:spec`-routed normative item exists beyond A1 (`SIG-UI-038` is the only such routing in `COVERAGE_MATRIX.csv`/`CAPSTONE_*`); the enumerated set is empty | — |

### G.5.2 Fold-back requirement ids (approved ticket-added scope folded into the spec)

New ids appended to their prefix sequences (never reused, never renumbered — §0.3):

| New id | Section | What it captures | Origin |
|---|---|---|---|
| SIG-UI-047 (MAY) | §40 | Interactive MapLibre progressive-enhancement map island (optional; deferred to Phase 21) | A1 / ADR-051 / P15.3 ticket-added |
| SIG-EVID-020 (MUST) | §17 | The `evidence/` package's content-addressed blob-vs-capture dedup contract | ADR-023 / P02.2 ticket-added |
| SIG-ENG-039 (MUST) | §47 | Every `docs/adr/ADR-*.md` MUST have an Appendix F row in the same PR, checked in CI | ADR-062 |

### G.5.3 Non-normative corrections

| # | Correction | Effect |
|---|---|---|
| N-01 | **Appendix F rebuilt to repository ADR numbering.** The old logical 18-decision table is replaced by all repository ADRs (ADR-001…062) with title + phase, sourced from `docs/adr/README.md` | Fixes LD-X04 / LD-D03 (logical-vs-repo numbering drift); `check_spec_src.py` enforces file-set == index-set going forward (SIG-ENG-039) |
| N-02 | `docs/adr/README.md` index gained the missing **ADR-056** and **ADR-057** rows | The index now lists every ADR file |
| N-03 | §52 Phase-10 acceptance criterion "All **32** task types" → "All **34** task types" | Aligns Part X with the §33.2 catalog (34 rows) and ADR-040; the 2026-08-26 manifest note now matches the spec text |


## G.6 Round-10 landed-design reconciliation (P33.5, 2026-09-28, ADR-145)

The Round-10 tail audited the canonical text against the landed system (ADR-120…144 plus the
standing record through ACCEPT-R10). Nothing here removes an obligation; every item either aligns
the text to an already-landed ADR or records a dated state. The landed ADR bodies and the
P20.2 reconciliation history above are unchanged.

### G.6.1 Amendments applied to `spec_src`

| # | Section | Change | Authorising ADR |
|---|---|---|---|
| R10-A1 | §21.5 (SIG-INGEST-012) | Robots verdicts are probed, classified per RFC 9309 §2.3.1.4 and recorded on every fetch; a `disallowed`/`unretrievable` verdict does not refuse — the fetch is stamped `robots_disregarded` (the operator's GL-GATE-08 disposition). The fail-closed rights gate (`ingestion_permitted`, HG-03) is untouched; challenges stay prohibited | ADR-088 (keeps ADR-087) |
| R10-A2 | §26 rule 2 (SIG-INGEST-036) | "Honor robots.txt" → the probe-and-record posture above; the documented-API allow-list mode (previously only in the ADR register) is written into the policy text | ADR-088, ADR-083 |
| R10-A3 | §23.7 (SIG-INGEST-046b) | The upstream-specialist robots disallow is a **recorded** verdict, not an enforced refusal; the affirmative-rights-reservation duty (SIG-INGEST-046c) and ask-first posture stand | ADR-088 |
| R10-A4 | §19.5 (SIG-GEO-012) | PMTiles archives are per-compartment and produced by the pinned tippecanoe build **or** the deterministic pure-Python v3 fallback — not "by tippecanoe" alone | ADR-067, ADR-118 |
| R10-A5 | §37.2 (SIG-API-005) | Release-namespaced reads bind the as-of pair structurally (the immutable `r/<publication>` pin); legacy `as_of_*` selectors resolve via `sig.compat-index/1` or fail honestly | ADR-132, ADR-133, ADR-144 |
| R10-A6 | §55.1, §55.8 (SIG-TRUST-009, SIG-TRUST-010), §55.9 | The dated landed-status record: wholesale S3-spine deferral (2026-10-19 dispatch amendment), provisional-basis candidate with `evaluation.status=deferred`, shadow-only evaluator, non-operational intake, GATE-G3's reduced-scope signature, ACCEPT-R10 — all as recorded obligations, not completions | ADR-142, ADR-144 |

### G.6.2 Recorded deviations where the requirement stands

These were audited and deliberately **not** amended — the normative text remains the bar and the
deviation is an operated-state disposition recorded elsewhere:

| Item | Why no spec change |
|---|---|
| `SIG-PUB-008` two-reviewer concurrence | The requirement stands; the sole-maintainer posture is a recorded operator waiver (`D-P21.4-2`, `PUBLICATION_CHECKLIST.md` — WAIVED-BY-OPERATOR). The published surface makes no two-reviewer claim |
| `SIG-EVAL-001/002` (PARTIAL) and `SIG-EVAL-005/006/007`, `SIG-MEM-004` (MISSING) | Honestly-recorded capstone verdicts over deferred/scheduled owners — obligations, not stale text (`D-R10-HUMAN-1`, `D-R6.1-EVAL`; P33.8) |
| Deferred/gated live halves (hosted recovery, production candidate/publication, source rights, intake operation, human labels, usability sessions) | Owed work with owners and return passes in `DEFERRALS.md`; the spec never claims them done |
| P32.10a (inserted ticket) and P33.1's in-ticket repairs | Recorded deviations with no spec-requirement change (manifest, BUILD_INDEX, `CAPSTONE_CLOSURE.md` §(f4)) |

No new requirement id was minted (no new requirement ownership — the count stays **715**);
requirement verdicts and their dated historical assessments are untouched.

## G.7 Round-11 corrections and extensions (Stage B, 2026-10-01; plan §6)

Round 11's ratified plan (`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`, canonical; the operator's
answers are logged verbatim with their round times in `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`)
extends and amends this specification. **Unlike G.5 and G.6, this section records waivers.** Where the operator waived
a MUST clause in their adopted words, the waived requirement's text is kept and a dated waiver note is added in its
owning section, citing the ADR that records the operator's sentence (with its sha256), the scope, the compensating
controls and the revisit trigger; the coverage verdict becomes `WAIVED(ADR)` with the scope in `accepted_scope`
(SIG-ENG-041). An amendment that would remove or weaken a MUST without such words is **not applied** (plan §6.5: an
amendment that weakens a MUST is a waiver; ADR-150) — those drafts are listed in G.7.5 with the requirement standing.
Every other item adds a dated note or a superseding sentence and removes no obligation. The G.5 and G.6 history,
R10-A6 and every landed ADR body above are unchanged.

### G.7.1 Part XII added

| # | Section | Change | Authority |
|---|---|---|---|
| R11-X1 | Part XII, §56 (new); §0.3 | Round-11 contract extension: SIG-MEM-005…012, SIG-ENG-040…046, SIG-OPS-001…012, SIG-STORE-048, SIG-SEC-007…011, SIG-REL-001…015 and SIG-CONF-001…014 — 62 new ids, append-only, draft → final map in `docs/build/planning/2026-09-30-next-phase/stageB/T1_id_map.csv`; `SIG-OPS-*` opened and the `REL` and `CONF` families registered in §0.3. The transparency and UX families are appended later by their planning rows (§56.8) | plan §6.1–§6.2 (ratified at GATE-P); ADR-146…150, ADR-152…154 |

### G.7.2 Waivers adopted by the operator

Each sentence was agent-drafted and adopted by the operator by selection, recorded verbatim in the cited ADR; the
sha256 is `printf '%s' "<sentence>" | shasum -a 256` over the logged text (prefix shown).

| # | Section (id) | Clause waived · scope | Operator's words (line, log round time, sha256) | ADR |
|---|---|---|---|---|
| R11-W1 | §55.4 (SIG-EVAL-004) | the preregistered 0.98 lower-bound clause, for the derivation-collapse tiers C0–C2 only; inferential tiers stay review-only (met fail-safe) | A-6, 2026-10-01T04:03:25Z, `03c0a79ef3b8…` | ADR-153 |
| R11-W2 | §45.1 (SIG-GOV-001, SIG-GOV-002) | SIG-GOV-001's one-click clause and all of SIG-GOV-002, for Round 11 (e-mail intake; senders disclose their address) | WV-05 (A-23), 2026-10-01T04:28:49Z, `bf1f65d5aaa1…` | ADR-180 |
| R11-W3 | §45.2 (SIG-GOV-003) | the response-time (SLA) clause; the priority clause is met differently by the published handling order | WV-08 (S6-F1), 2026-10-01T06:05:22Z, `806faae385d9…` | ADR-186 |
| R11-W4 | §45.4 (SIG-GOV-008) | the two-person clause; the scope and tombstone clauses stand | WV-06 (A-23), 2026-10-01T04:28:49Z, `dbf7a851e9d5…` | ADR-181 |
| R11-W5 | §46.1 (SIG-GOV-012, SIG-GOV-013) | a legal home before launch and retained legal-defence resources, "for now" (an individual legal home, disclosed) | WV-01 (A-23), 2026-10-01T04:28:49Z, `b9dc5a9128ac…` | ADR-165 |
| R11-W6 | §46.2 (SIG-GOV-015) | the editorial board (interim single-maintainer authority + public decision log) | WV-02 (A-23), 2026-10-01T04:28:49Z, `bee2cd2b1501…` | ADR-164 |
| R11-W7 | §43.4 (SIG-PUB-008) and HG-11 | the HG-11 second-reviewer role, for Round-11 releases; SIG-PUB-008's naming concurrence stands (nobody is named) | WV-03 (A-23), 2026-10-01T04:28:49Z, `44644f6bd6ff…` | ADR-163 |
| R11-W8 | §41 (SIG-UI-042) | the release block; the hostile-reader review stays owed and is recorded "not yet performed" | WV-04 (A-23), 2026-10-01T04:28:49Z, `2a0339a96d57…` | ADR-179 |
| R11-W9 | §42.3a (SIG-LIC-009), §26 (SIG-INGEST-037) | the counsel-referral and counsel-requiring clauses; SIG-LIC-009's risk-register clause and SIG-INGEST-037's ADR-level-decision clause stand | WV-07 (A-23), 2026-10-01T04:28:49Z, `c5a71e9d7fd9…` | ADR-182 |
| R11-W10 | §26 rule 6 (SIG-INGEST-036) | "ask first", for DocumentCloud/MuckRock only; rules 1–5, 7 and 8 bind every source | WV-09 (S6-F2), 2026-10-01T06:05:22Z, `94f061234c41…` | ADR-187 |
| R11-W11 | §23.4 (SIG-INGEST-035) | the no-direct-capture clause, for Flock transparency portals, probe-only; the aggregator-source and compartment clauses stand | WV-10 (S6R-01), 2026-10-01T06:51:11Z, `82487f7b3f0d…` | ADR-188 |
| R11-W12 | §16.3 (SIG-STORE-011) | append-only, for one operator-only purge function only; every other role and path stays append-only | WV-11 (S6R-03), 2026-10-01T06:51:11Z, `04e7b77f8db7…` | ADR-189 |
| R11-W13 | §39.4 (SIG-UI-022) | the default-view clause ("Default view is an ego network with expansion"): the explorer may open on an aggregated overview meeting R11-A2's rules, every overview node drilling to its ego view, with no-JS parity; "not a global graph" (no national node-link graph) stands. Supersedes G.7.5's SIG-UI-022 row (kept) | WV-12 (SB-1), 2026-10-01T13:46:58Z, `1ce44d4df7f6…` | ADR-190 |

### G.7.3 Amendments applied to `spec_src` (none weakens a MUST)

| # | Section (id) | Change | Authority |
|---|---|---|---|
| R11-A1 | §5.1 (SIG-CHART-025) | US-nationwide multi-vendor and multi-technology breadth with per-class and per-geography quality labels, so breadth is never read as depth; the generalisation duty unchanged; classed non-weakening by plan §5.10 | A-17 (Q-E2-22 = a); ADR-172 |
| R11-A2 | §39.3–§39.4 (SIG-UI-021, SIG-UI-022) | the "global graph" is a set of aggregated overviews (≤ 3,000 nodes, descriptive, ER-disclosed, drilling to egos), offered as alternative views; both requirements unchanged, including the ego default (the default-view clause later waived: R11-W13, 2026-10-01T13:56:14Z) | A-11, D-K0-6; ADR-158 |
| R11-A3 | §40 (SIG-UI-036, SIG-UI-050); §55.1 | HTML-first page types (T0–T3 registry, per-type budgets, no-JS parity) replace the named-island rule; zero client JavaScript still holds for T0 pages and T1 pages gain budgeted enhancements — a relaxation the operator chose at A-12 through the new-ADR change path SIG-UI-050 itself names | A-12 (B-22 for Preact); ADR-155 |
| R11-A4 | §39.9 (SIG-UI-035) | immutable, release-bound permalinks (`/s/<pub>/`, `/r/<pub>/`); legacy as-of selectors resolve at the edge or fail | J3 draft D23 (B-19); ADR-162 |
| R11-A5 | §41 (SIG-UI-044) | full module on record pages; elsewhere a one-line summary with the full module on the same page one action away | D-K14-6 (B-22) |
| R11-A6 | §32.4 (SIG-METRIC-007) | cadence / freshness-state / volatility distinctions; digest-based "last content change" | J3 draft D07 (B-19); ADR-162 |
| R11-A7 | §17.5 (SIG-EVID-009) | the storage tier is derived from the redistribution lane and Part VIII class, never defaulted | J3 NEW-2 (B-19); ADR-162 |
| R11-A8 | §38.1 (SIG-EXPORT-012), §29.8 (SIG-RECON-058) | the ADR-092 compute-on-read citation is superseded for the resolved layer by the materialized resolution records of ADR-099/ADR-101; every protection stands | F-34; ADR-099, ADR-101 |
| R11-A9 | §14.7 (SIG-IDENT-028) | census-driven demotion added for copy tiers C0–C2; the holdout report is labelled agent-labelled development data; the holdout-demotion clause is not waived | A-6; ADR-153 |
| R11-A10 | §55.4 (SIG-EVAL-005/006/007), §55.9 | owner re-homing; the Round-11 disposition: rows 184–187 superseded, not executed; T-EVAL-IND replaces the HUMAN-H4/P32.22a/HUMAN-H5/P32.23 path; every obligation stays OPEN | ADR-152, ADR-153 |
| R11-A11 | §44.3 (SIG-SEC-003) | a written demand-response posture and published legal-demand counts; the warrant canary (a SHOULD) declined with its rationale | A-4 (Q-E2-09 = c); ADR-166 |
| R11-A12 | §42.1 (SIG-LIC-004) | rights resolve only by a recorded decision — in Round 11 the operator's own determination, labelled (GL-GATE-07 re-confirmed; express-terms rows kept; new non-commercial sources facts-only; non-US database-right flips); `UNDETERMINED` still fails closed | A-4, A-7, A-8, A-9, B-34; ADR-167, ADR-169, ADR-183 |
| R11-A13 | §42.3 | share-alike compartments for the RB-06b sources under SIG-LIC-004a | B-33; ADR-169 |
| R11-A14 | §26 (SIG-INGEST-036 rules 1, 2, 7; SIG-INGEST-037), §23.7 (SIG-INGEST-046c) | GL-GATE-08 re-confirmed and applied on every host, disregards disclosed as host + count; rule 1 met by an owned explanation URL; the rule-7 opt-out register and the reservation refusal built; the terms-conflicted fetch envelope; SIG-INGEST-037's legal posture restated (RISK-P0-06 closes by ADR-168) | A-5, S6R-08, B-6, B-39; ADR-168, ADR-184 |
| R11-A15 | §6 (SIG-CHART-033), §22.4 (SIG-INGEST-029), §22.5 (SIG-INGEST-030a), §35.1 (SIG-CONTRIB-012/012a/013), §46.5 (SIG-GOV-024) | outreach timing: not amended in substance and not waived — owed as a later-phase obligation with the trigger "the operator authorises outside contact"; unmet and owed wherever a connector precedes outreach. (The plan's "CONTRIB-030a" is SIG-INGEST-030a.) | B-6 (Q-E2-12 = a); ADR-171 |
| R11-A16 | §51.3 (SIG-ENG-031) | additions: green head-bound checks per SIG-MEM-007; the coverage matrix as the traceability matrix; a per-round risk review and revisit-trigger re-evaluation | DRAFT-ENG-5 (B4 §5) |
| R11-A17 | §47 (SIG-ENG-039) | additions: index fields and status, appended status lines on superseded or amended ADRs, `check_spec_src.py` and its tests in `make docs-check` and CI, template headers | DRAFT-ENG-4 (B4 §5); F-32 |

### G.7.4 Date corrections

| # | Section | Correction | Authority |
|---|---|---|---|
| R11-C1 | §55.1, §55.8 (the SIG-TRUST-009 paragraph), §55.9 | The landed-status text recorded "2026-10-19" for two Round-10 events that happened on 2026-09-28. The operator's deferral of the S3 human-evaluation spine: **2026-09-28T01:15:49Z** (operator-confirmed, C-1/Q-B1-2; recorded in commit `a33cd6ec` at 01:27:21Z). The GATE-G3 approval: **2026-09-28T03:49:14Z** (operator-confirmed; signed text committed in `95c8a73f` at 03:49:46Z). Corrected in place with the recorded value struck through, never erased. The same recorded date in R10-A6 above, in Appendix F's ADR-145 row and in the bodies of landed ADR-142…145 is corrected by this row and ADR-146 only — none of them is edited; the "2026-10-01" replay date in Appendix F's ADR-138 row names no event (stand-in captures authored 2026-09-27T12:06Z). No gate approval or decision was given on 2026-10-19. `db/sqitch.plan` lines 44–52 keep their stamped `planned_at` values and are never re-stamped (SIG-ENG-045; C-10) | ADR-146 |

### G.7.5 Checked and deliberately not amended

| Item | Why no spec change |
|---|---|
| SIG-GOV-017 | Not amended, not waived (B-44): the approved "My location" control is built only as a map-pan control after a written SIG-GOV-017 analysis; a failing analysis returns the question to the operator |
| SIG-PUB-002, SIG-PUB-003, SIG-PUB-003a | Not amended: applied before persistence by one rule for every terms-conflicted connector — a redacted rendition plus the upstream URL and the sha256 of the original, or only the pointer and the screened facts (ADR-185) |
| SIG-EVAL-001/002/005/007, SIG-IDENT-027/028's independent legs, SIG-DOS-002's independent checks, SIG-UI-001 usability | Owed, not waived: T-EVAL-IND, or the usability trigger (LATER-02) |
| SIG-EXPORT-002, RO-Crate clause | Left for a decision by the transparency design (J3 §11); no operator decision on it is recorded, so the clause stands as written |
| SIG-LIC-006, "physically separate table" (§42.3) | Plan §6.3 drafts "physical ODbL table → export-boundary compartments" (RISK-P4-07). Removing the stored-table clause would weaken this MUST and no operator decision covers it, so it is not applied: separation holds at the export boundary today and the stored-table split stays owed (RISK-P4-07 → BL-046) |
| SIG-INGEST-004 | The drafted binding-level versioning (ADR-121; the F2a re-audit's NEW-7) would drop "the claim's logical identity MUST include `extractor_version` and `normalizer_version`"; not applied without operator words. The requirement stands; the divergence is owed (the alternative is to add the versions to the identity) |
| SIG-ENG-004 | The drafted alignment ("MET = criteria 1+2; criteria 3–5 recorded per row") would weaken the all-five Definition of Done; not applied. Its verdict (N/A-RATIONALE, as the meta-rule the verdict process applies) needs no text change |
| SIG-ONTO-060 | The scope list conflicts with §11.6's own examples (for example `federal`, `private_camera`, `to_partner`, `required`), and 15 of the 45 realised slugs use scopes outside it. Widening a closed list relaxes it and needs the realised enum read from the ontology; recorded here, not changed |
| SIG-UI-022, default view | The drafted wording "aggregated overview graphs … MAY serve as the global entry point" would let an overview replace the ego-network default; not applied (R11-A2 records the non-weakening reading). An overview as the explorer's default needs the operator's words — applied as R11-W13 at 2026-10-01T13:56:14Z (WV-12, ADR-190) |
