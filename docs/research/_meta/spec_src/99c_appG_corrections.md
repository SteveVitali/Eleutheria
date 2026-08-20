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
