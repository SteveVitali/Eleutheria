# R10 — UI/UX Design and the Public Product Surfaces (and the web/geo stack that serves them)

**Workstream:** R10
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (agent R10)
**Outline sections covered:** §6.5, §9.2, §9.3, §9.4, §12, §13.3, §15 (15.1–15.7), §19.4, §19.6, §19.12, Appendix B
**Outline questions answered:** Q36 (geographic research queues), Q37 (stable IDs for inbound linking), partial Q30/Q31 (publication policy as a UI surface), partial Q32 (takedown/correction UX), partial Q33/Q35 (upstream correction flow as a queue affordance)
**Confidence in this file overall:** high for the verified stack facts (every version/license below was fetched today); medium-high for the design specifications, which are engineering proposals grounded in verified prior art rather than empirical findings.

---

## 0. Decision summary (read this first)

| Decision | Recommendation | Why (short) |
|---|---|---|
| Frontend framework | **Astro 7.x with islands, SSR-capable adapter in production, `prerender` for ~95% of routes** | Zero-JS-by-default is the only framework default that structurally guarantees the "useful without JS" requirement (F10.31, F10.32). |
| Fallback if the team is React-only | Next.js 16 App Router with RSC, `output: 'export'` for the archive build | Verified static-export limitation list is manageable (F10.30) but forces two builds. |
| Map renderer | **MapLibre GL JS 6.4.1** (BSD-3-Clause) | Verified current (F10.25). ESM-only in v6 — a real migration constraint (F10.26). |
| Tiles | **PMTiles v3 on object storage + `@protomaps/basemaps` 5.7.2 styles + self-hosted Protomaps v4 planet build** | Single-file, no tile server, ODbL-clean, ~$5/mo storage (F10.27, F10.28, F10.29). |
| Large point/edge overlay | **deck.gl 9.3.10 `MapboxOverlay` in `interleaved` mode** | Verified MapLibre compatibility (F10.33, F10.34). |
| Graph viz | **Sigma.js 3.0.3 + graphology 0.26.0** for the explorer; **Cytoscape.js 3.34.1** for small curated ego-graphs | Both MIT. **Do not use Cosmograph — CC-BY-NC-4.0** (F10.36). |
| Data grid | **TanStack Table 9.1.2** (headless, MIT). Datasette 1.0a38 as an internal/expert fallback only | AG Grid's useful features are the $999/dev Enterprise tier (F10.37, F10.38). |
| Design system | Tailwind CSS 4.3.3 + Radix Primitives (MIT) via shadcn 4.18.0 codegen; React Aria Components 1.20.0 where a11y is load-bearing | (F10.39, F10.40) |
| Search | **PostgreSQL 18 FTS first; Typesense 30.x only if typo tolerance becomes a measured need** | Postgres FTS has no typo tolerance (F10.41); Typesense is GPL-3.0 server / Apache-2.0 client (F10.42); Meilisearch is now `MIT AND BUSL-1.1` (F10.43) — a real governance hazard. |
| Print/PDF | **WeasyPrint 69.0** (BSD-3) server-side for the council-packet PDF; browser print stylesheet for everything else | Paged.js npm is stale at 0.4.3/2023 (F10.44). |
| Confidence model | **Four orthogonal axes, not one enum** (support × conflict × currency × absence-kind), IPCC-style evidence×agreement derivation | The outline's single six-value list conflates three dimensions (F10.9, Outline delta: CORRECTS §9.3). |
| Color policy | **Ink ramp for support; exactly two saturated hues in the entire product (amber = contested, red = retracted); no green** | Saturated color is a scarce resource reserved for epistemic state (§B.6). |

---

# Part A — Users and jobs-to-be-done

## A.1 Persona table

| # | Persona | Entry point | The 3 questions they arrive with | "Done" looks like | What makes them distrust the site |
|---|---|---|---|---|---|
| P1 | **Investigative journalist on deadline** (2–48h) | Google search for `"<city> flock cameras"`; a tip; a colleague's link | (1) Does this agency use ALPR/RTCC/FR, and since when? (2) What can I *print* without getting sued? (3) Who do I FOIA and for what? | A dossier permalink + 3 primary-source PDFs downloaded + a named contact/records path + a citation string with an as-of date | Any claim without a document behind it; a number that changed between two visits with no changelog; a confident total that a source contradicts; "last updated: unknown" |
| P2 | **Academic researcher, national analysis** (weeks–months) | Paper citing SIG; the `/api` or `/data` page; a conference talk | (1) What is the population and denominator? (2) What is the coverage bias by state/agency size? (3) Can I get a versioned, citable snapshot? | A DOI-or-equivalent versioned dump + a codebook + a documented coverage matrix + reproducible query | Coverage presented as completeness; no versioning; entity IDs that change between releases; graph centrality stats offered without an entity-resolution caveat (§19.6) |
| P3 | **Local advocate, council meeting in 6 days** | A neighbor's text; a Mastodon/Reddit post; DeFlock | (1) What exactly is in *my* city and what did it cost? (2) When does the contract expire? (3) What do I say in 2 minutes at the podium? | A printed 2-page dossier PDF, contract expiration date, three sourced sentences they can read aloud, and a "what we don't know" list | Anything the chief can call "activist exaggeration" in the room; missing dates; a map dot in the wrong place; tone that sounds like a press release |
| P4 | **Civil-liberties attorney building a records case** | Referral from an org; a docket search; the evidence viewer | (1) What did the agency publicly assert, and when? (2) Do I have a chain of custody for that assertion? (3) Where is the gap that justifies a request or a claim? | A snapshot permalink with content hash + WARC/PDF + capture timestamp + a declaration-grade provenance record | Any evidence artifact without a capture timestamp and hash; a claim edited without an audit trail; inability to reproduce what the page said last March |
| P5 | **City council staffer / municipal analyst** | Sent the link by a constituent; searching before a vote | (1) Is what my constituents are saying accurate? (2) What do peer cities do? (3) What does our own department say? | A defensible comparison table + a correction path if the data is wrong about their city | Errors about their city with no visible way to fix them; adversarial framing; no named editorial policy; no correction log |
| P6 | **Curious resident** | Social share; local news link; "is there a camera on my street?" | (1) Is there surveillance near me? (2) Who is watching and who can they share it with? (3) Is this legal / can I do anything? | Understood the sharing chain; found the map dot; knows the next civic step | Jargon; a wall of caveats with no answer; a map that implies precision it doesn't have; anything that feels like a conspiracy site |
| P7 | **Downstream developer** (newsroom tool, dashboard, route app) | `/api`, GitHub, a "built with SIG" showcase | (1) Is there a stable schema and stable IDs? (2) What is the license and the rate limit? (3) Can I bulk-download instead of crawling? | A working request in <5 min, a pinned schema version, a bulk dump URL, an attribution snippet they can paste | Undocumented breaking changes; unclear ODbL contamination boundary; hidden rate limits discovered in production |
| P8 | **SIG contributor / reviewer** (the research queue) | `/queue`, a task link from Discord/Matrix, a geographic queue claim | (1) What is a task I can actually finish tonight? (2) How do I know I did it right? (3) Did my work land? | Task claimed → evidence attached → submitted → reviewed → visible on a public page with their attribution | Silent rejection; a queue that never empties; review latency > a week; leaderboards that reward volume over correctness |

## A.2 Notes the persona table forces

- **P3 (six-day advocate) is the design center of gravity.** Every surface should be reachable from a jurisdiction name in ≤2 clicks and should have a print path. The outline's claim that the dossier "may be the single most powerful public-facing primitive" (§15.1) is correct, and P3 is why.
- **P4 (attorney) sets the floor on provenance rigor.** If the evidence viewer satisfies a declaration-grade chain of custody, every other persona is over-served. Design to P4, present to P3.
- **P5 (the subject's own staff) is the hostile-reader test.** Every page must survive being read by the department it describes. This is the constraint behind Part E.
- **P8 is not a "nice to have."** §12 makes the research queue the mechanism by which contradictions become resolutions. A queue with a 3-week review latency kills the data pipeline, not just morale.

---

# Part B — The hard UX problem: communicating epistemic state

## B.1 Prior art, verified

### F10.1 — IPCC calibrated language separates *confidence* (qualitative, from evidence × agreement) from *likelihood* (quantitative probability)

**Claim:** The IPCC's uncertainty framework derives a five-level qualitative confidence label from a two-dimensional evaluation of *evidence* (limited / medium / robust) and *agreement* (low / medium / high), and keeps that label strictly separate from probabilistic likelihood terms.
**Status:** VERIFIED
**Evidence:** `https://www.ipcc.ch/site/assets/uploads/2018/05/uncertainty-guidance-note.pdf` — fetched via `curl` with a browser UA after WebFetch returned 403; extracted with `pypdf` 6.16.1. Paragraph 8: authors "evaluate the associated evidence (summary terms: 'limited,' 'medium,' or 'robust'), and the degree of agreement (summary terms: 'low,' 'medium,' or 'high')." Paragraph 9: "A level of confidence is expressed using five qualifiers: 'very low,' 'low,' 'medium,' 'high,' and 'very high.'" Figure 1 is the 3×3 evidence-by-agreement matrix; "Confidence increases towards the top-right corner." Critically: "Confidence should not be interpreted probabilistically, and it is distinct from 'statistical confidence.'" Table 1 (Likelihood Scale): Virtually certain 99–100%, Very likely 90–100%, Likely 66–100%, About as likely as not 33–66%, Unlikely 0–33%, Very unlikely 0–10%, Exceptionally unlikely 0–1%. Also: "Provide a traceable account describing your evaluation of evidence and agreement in the text of your chapter."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's confidence label must be *derived by a published rule* from two stored inputs — evidence strength (source tier + count + independence) and inter-source agreement — not assigned by an opaque scorer. The IPCC's "traceable account" requirement becomes SIG's "how we know this" module (Part E.2). And SIG must not emit numeric probabilities anywhere; the outline's warning against "opaque '87% confidence'" (§9.3) is correct and now has a normative model behind it.
**Outline delta:** EXTENDS §9.3 — the outline asks for "labels with reasons"; IPCC shows the reasons should themselves be two named, separately-stored ordinal axes, and that the derivation may be *flexible* ("for a given evidence and agreement statement, different confidence levels could be assigned") as long as it is documented.

### F10.2 — GRADE grades a *body* of evidence with explicit downgrade/upgrade domains and a four-level scale

**Claim:** Cochrane/GRADE rates certainty at four levels (high / moderate / low / very low), starting from a study-design prior and applying five downgrade domains and three upgrade domains, with judgments made transparent through explanatory footnotes.
**Status:** VERIFIED
**Evidence:** `https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14` (reached after a 301 from `training.cochrane.org`). Four levels rendered as filled-circle glyphs: High ⊕⊕⊕⊕, Moderate ⊕⊕⊕◯, Low ⊕⊕◯◯, Very low ⊕◯◯◯. Downgrade domains: risk of bias, inconsistency, indirectness, imprecision, publication bias. Upgrade domains: large effects, dose-response gradient, opposing plausible confounding. The handbook notes judgments "should be made transparent through 'explanatory footnotes'." It does **not** prescribe standardized plain-language wording per level.
**Retrieved:** 2026-08-20
**Implication for the spec:** Two transferable mechanics. (a) The **four-segment filled-glyph** is a proven non-color-redundant ordinal encoding — SIG adopts it directly as the support-level badge. (b) The **explicit downgrade reason** pattern: SIG must store *why* a claim is not higher, as an enumerated reason code (`single_source`, `stale`, `vendor_self_report`, `derived_not_observed`, `entity_resolution_uncertain`, `contradicted`) rendered as a footnote next to the badge. A badge without a reason code is a bug.
**Outline delta:** EXTENDS §9.3 — adds the downgrade-reason enumeration, which the outline does not mention.

### F10.3 — Wikidata separates statement *rank* from statement *sourcing*, and provides "no value" vs "unknown value" special snaks

**Claim:** Wikidata models three ranks (preferred / normal / deprecated) orthogonally to references, and models absence with two distinct special values: `no value` (a positive assertion of absence) and `unknown value` (a positive assertion that the value exists but is not recorded).
**Status:** VERIFIED
**Evidence:** `https://www.wikidata.org/wiki/Help:Ranking` — preferred (blue star, green background), normal (grey circle, default), deprecated (red X, red background, "statements that are known to include errors"). Query service defaults to "best rank" (preferred if any, else normal); `wikibase:PreferredRank` / `wikibase:DeprecatedRank` allow explicit filtering. `reason for deprecated rank (P2241)` records *why*. Ranks "communicate consensus opinion about which data is 'most correct,' not just where information originates."
`https://www.wikidata.org/wiki/Help:Statements` — "no value" = Elizabeth I has no value for *child*, "a positive statement that she had no children." "unknown value" = Shakespeare's date of birth, "a positive statement that that information has not been preserved."
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the single most directly transferable model for §9.4. SIG needs **three** absence states, not two: Wikidata's `no value` (evidence of absence), Wikidata's `unknown value` (known-to-exist, unrecorded), and a third that Wikidata does not need — `not yet researched` (SIG has not looked). Wikidata's rank/reference orthogonality also validates separating SIG's conflict axis from its support axis (§B.2). The `P2241`-style "reason" qualifier is the pattern for SIG's downgrade-reason codes.
**Outline delta:** EXTENDS §9.4 — the outline says "absence from a dataset means little" and "the UI/API should make coverage explicit," but does not enumerate the states. This finding supplies a proven three-to-four-state enumeration.

### F10.4 — Value-Suppressing Uncertainty Palettes (Correll, Moritz, Heer, CHI 2018) allocate less visual range to uncertain values

**Claim:** VSUPs are bivariate value×uncertainty palettes that deliberately compress the color range available to high-uncertainty data, and a crowdsourced study found they cause people to weight uncertainty more heavily in decisions.
**Status:** VERIFIED
**Evidence:** Paper identified via search: `https://dl.acm.org/doi/10.1145/3173574.3174216`, PDF at `https://www.domoritz.de/papers/2018-VSUPs-CHI.pdf`. Core mechanic per the authors: VSUPs "allocate larger ranges of a visual channel to data when uncertainty is low, and smaller ranges when uncertainty is high," which "encourages more cautious decision-making when uncertainty is high." Reference implementation: `https://idl.uw.edu/vsup/` — npm package `vsup`, D3-compatible, three quantizations (`linearQuantization`, `squareQuantization`, tree `quantization` with `branchingFactor`/`treeLayers`), three legends (`simpleLegend`, `heatmapLegend`, `arcmapLegend`).
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt the *principle* without the *library*. SIG's choropleths (coverage-by-jurisdiction, device-density) must collapse toward the neutral mid-tone as confidence drops, so a low-confidence county cannot look like a high-confidence county. But SIG's per-claim badges are ordinal-categorical, not continuous, so a bivariate palette is the wrong tool there; the tree-quantized `arcmapLegend` is however exactly right for the **coverage choropleth legend** on the map surface (§C.2).
**Outline delta:** EXTENDS §19.4 ("Uncertainty before false precision") with a specific, cited encoding technique.

### F10.5 — Hypothetical Outcome Plots beat error bars for multivariate reliability judgments; quantile dotplots/CDFs beat density for lay decisions

**Claim:** Animated discrete draws (HOPs) substantially outperform error bars and violin plots when users must judge ordering reliability across two or three quantities; discrete-outcome (frequency-framed) displays improve non-expert decisions.
**Status:** VERIFIED
**Evidence:** Hullman, Resnick & Adar 2015, PLOS ONE — `https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0142444`. 288 MTurk participants, 96 per condition, nine tasks. Abstract: "With HOPs, people made much more accurate judgments about plots of two and three quantities. Accuracy was similar with all three representations for most questions about distributions of a single quantity." Follow-on: Kay, Kola, Hullman & Munson, "When (ish) is My Bus?", CHI 2016, DOI 10.1145/2858036.2858558 (quantile dotplot generation method); Fernandes, Walls, Munson, Hullman & Kay, "Uncertainty Displays Using Quantile Dotplots or CDFs Improve Transit Decision-Making," CHI 2018, DOI 10.1145/3173574.3173718.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG almost never has calibrated distributions, so HOPs are mostly inapplicable — and saying so is itself a finding. The transferable lesson is the *frequency framing*: where SIG shows a reconciled count (§6.5's 20/25/22/18 case), do **not** render a mean with an error bar. Render the four discrete claims as four discrete marks on a small number line — a "claim dotplot." That is the frequency-framing result applied to a case where the underlying quantity is a small set of asserted integers rather than a posterior.
**Outline delta:** EXTENDS §6.5 — supplies the actual visual form for the contradiction case the outline describes only in YAML.

### F10.6 — Wikipedia's inline-template family is a working taxonomy of *reader-visible* doubt

**Claim:** Wikipedia uses a family of distinct inline markers — not one generic "unverified" flag — that separate "no source," "source too weak," "source doesn't support the claim," and "editors dispute this."
**Status:** VERIFIED
**Evidence:** `https://en.wikipedia.org/wiki/Wikipedia:Citation_needed`. Renders inline as `[citation needed]`. Related distinct templates: `{{Dubious}}`, `{{Disputed inline}}`, `{{Better source needed}}`, `{{Failed verification}}`, `{{Failed verification span}}`, `{{Unreliable source?}}`, plus comprehension templates `{{Clarify}}`, `{{Explain}}`, `{{Confusing}}`. Policy framing: the template "is a request for another editor to supply a source for the tagged fact: a form of communication between members of a collaborative editing community," and "is never, in itself, an 'improvement' of an article."
**Retrieved:** 2026-08-20
**Implication for the spec:** Two things. (a) SIG's downgrade-reason codes should map roughly onto this taxonomy — `no_evidence_linked`, `source_tier_too_low`, `excerpt_does_not_support_claim`, `contested`. (b) The policy framing is the design bridge between §9.3 and §12: **every reader-visible doubt marker must be a clickable research-task generator.** Wikipedia's `[citation needed]` is a task; SIG's should be too, literally — clicking the marker opens the pre-filled queue task (§C.6).
**Outline delta:** EXTENDS §12 — the outline lists seven server-side task generators but never connects them to the reader-facing UI. The doubt marker *is* the task-creation entry point.

### F10.7 — ClaimReview / schema.org gives a machine-readable envelope for a rated claim, with a human label carried in `alternateName`

**Claim:** `schema.org/ClaimReview` carries `claimReviewed` (the claim text), `itemReviewed`, `author`, and `reviewRating` (a `Rating` with `ratingValue`, `bestRating`, `worstRating`, and a human-readable `alternateName`).
**Status:** VERIFIED
**Evidence:** `https://schema.org/ClaimReview`. "claimReviewed: A short summary of the specific claims reviewed in a ClaimReview." `Rating.alternateName` carries the human label (schema.org's own example uses PolitiFact-style values). "This design allows fact-checkers to express verdicts both numerically and descriptively."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG should emit `ClaimReview` JSON-LD on dossier and claim-detail pages — it is the only widely-consumed structured vocabulary for "a rated assertion with a source." Map SIG's support level to `ratingValue` 1..4 with `alternateName` = the SIG label, `bestRating: 4`, `worstRating: 1`. **But** `ClaimReview` has exactly one rating axis, so SIG's conflict/currency/absence axes must go into `additionalProperty` on the `itemReviewed`, or into a SIG-specific JSON-LD context. Do not flatten the four axes into `ratingValue`.
**Outline delta:** EXTENDS §15.7 — outline says "machine-readable API/exports" without naming vocabularies.

### F10.8 — PolitiFact demonstrates a tiered corrections policy tied to whether the *rating* changed

**Claim:** PolitiFact publishes six named ratings with one-sentence definitions, and a three-tier corrections policy where the remedy escalates with the severity of the error.
**Status:** VERIFIED
**Evidence:** `http://www.politifact.com/article/2018/feb/12/principles-truth-o-meter-politifacts-methodology-i/` (reached after a 301 from the `truth-o-meter` path). Ratings: TRUE "The statement is accurate and there's nothing significant missing"; MOSTLY TRUE "accurate but needs clarification or additional information"; HALF TRUE "partially accurate but leaves out important details or takes things out of context"; MOSTLY FALSE "contains an element of truth but ignores critical facts that would give a different impression"; FALSE "not accurate"; PANTS ON FIRE "not accurate and makes a ridiculous claim." Corrections: **major errors** → correction mark at top, archived copy of the previous version preserved and linked, "Corrections and updates" tag; **errors of fact not affecting the rating** → mark at bottom + tag; **typos/minor** → fixed silently.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt the three-tier structure verbatim in SIG's corrections policy (Part E.4), with the tiers keyed to SIG's own semantics: **Tier 1** = a support level, a reconciled value, or an entity identity changed → top-of-page notice + link to the prior snapshot + entry in the public corrections log + notification to anyone who subscribed to that entity. **Tier 2** = a fact changed but the reconciled value and level did not → bottom-of-page note + corrections log. **Tier 3** = typo/formatting → silent, but still in the git history. Note also that PolitiFact *preserves and links an archived copy of the previous version* — SIG must do this too and already has the machinery (as-of permalinks, §C.1).
**Outline delta:** EXTENDS §15 — the outline has no corrections surface at all. This is a gap; see REQ-R10-33.

## B.2 The refined confidence vocabulary

### F10.9 — The outline's six-value confidence list conflates three orthogonal dimensions and cannot be rendered coherently

**Claim:** `confirmed / strongly supported / probable / unverified / contradicted / historical` (§9.3) mixes an ordinal support scale, a conflict state, and a temporal state into one enum, which produces unrepresentable combinations.
**Status:** VERIFIED (by construction — this is an analysis of the outline against the models in F10.1/F10.3)
**Evidence:** Counterexample from the outline's own §6.5: portal says 20, contract says 25, presentation says 22, OSM observes 18. The reconciled value `active_device_count = 20` is simultaneously (a) well supported — it is the most recent Tier-A operational source, (b) contradicted — three other sources disagree, and (c) current. In the outline's single enum, an implementer must choose between `strongly supported` and `contradicted` and will lose information either way. Second counterexample: a 2019 contract that four independent sources agree on is both `confirmed` and `historical`. Third: `unverified` and `contradicted` are not adjacent points on any scale — a claim with four disagreeing Tier-A sources has *more* evidence than one with none.
**Retrieved:** 2026-08-20 (analysis)
**Implication for the spec:** Split into four independent, separately-stored axes. Every claim carries all four. The UI composes them; it never collapses them.
**Outline delta:** **CORRECTS §9.3** — replace the single six-value enum with the four-axis model below. The outline's six labels all survive, but redistributed across axes.

### B.2.1 The four axes

**Axis 1 — `support` (ordinal, 4 levels).** Derived, never hand-set. Answers: *how strong is the evidence for this claim, taken on its own?*

| Value | Glyph | Machine value | Derivation rule (normative) | Plain-language gloss shown on hover |
|---|---|---|---|---|
| `confirmed` | ⊕⊕⊕⊕ | 4 | ≥2 **independent** sources, at least one Tier A (direct primary operational evidence), agreeing within tolerance, most recent observation ≤ the claim type's staleness horizon | "Two or more independent sources, including primary evidence, agree." |
| `strongly_supported` | ⊕⊕⊕◯ | 3 | ≥2 independent sources agreeing, highest tier B or C; **or** 1 Tier-A source corroborated by a Tier-D/E observation | "More than one source agrees, but not primary operational evidence." |
| `probable` | ⊕⊕◯◯ | 2 | Exactly 1 source at Tier A–C; **or** ≥2 sources at Tier D–E; **or** a derived value from a documented inference rule over `probable`+ inputs | "One credible source, or several weak ones. Not independently corroborated." |
| `unsupported` | ⊕◯◯◯ | 1 | 1 source at Tier D–F; **or** a lead/heuristic with no confirming evidence | "A single weak or heuristic source. Treat as a lead, not a fact." |

**Hard rules that override the derivation:**
- **R1.** No claim reaches `confirmed` from a single source, regardless of tier. A vendor transparency portal is Tier A but it is *one* source.
- **R2.** A **derived** claim can never exceed the minimum support of its inputs, and is capped at `strongly_supported`. Derived ≠ observed (§9.4, §19.4).
- **R3.** A claim whose only sources are the subject's own statements about itself is capped at `probable` and carries the reason code `subject_self_report`.
- **R4.** Every claim below `confirmed` carries ≥1 **downgrade reason code** (F10.2). Rendering a badge without a reason code is a validation error, not a UI choice.

Downgrade reason codes (closed vocabulary, extensible by RFC): `single_source`, `subject_self_report`, `derived_not_observed`, `stale`, `low_tier_only`, `entity_resolution_uncertain`, `excerpt_does_not_support_claim`, `extraction_unreviewed`, `jurisdiction_ambiguous`, `superseded_pending_review`.

**Axis 2 — `conflict` (categorical, 4 values).** Answers: *do the sources agree?* Orthogonal to support (F10.3's rank/reference orthogonality).

| Value | Meaning | Visual key |
|---|---|---|
| `uncontested` | All linked sources agree within the claim type's tolerance. | (no marker) |
| `contested` | ≥2 sources disagree and none has been adjudicated. The reconciled value is a *choice with a stated rationale*, not a fact. | Amber left-rule + amber `≠` glyph + count `≠4` |
| `resolved` | Sources disagreed; a reviewer applied a documented resolution rule; dissenting claims are retained and visible. | Amber outline `≠` glyph, hollow |
| `retracted` | A previously published claim was withdrawn (bad extraction, misattributed entity, source retracted). Never deleted — always kept, struck through, with reason. | Red strikethrough + red `✕` |

`contested` **replaces** the outline's `contradicted`, moved off the support axis.

**Axis 3 — `currency` (categorical, 4 values).** Answers: *is this still true now?* Enforces §9.2 (observation time ≠ validity time).

| Value | Meaning |
|---|---|
| `current` | Latest observation is within the claim type's staleness horizon and no end date has passed. |
| `stale` | Within its asserted validity window, but the last observation is older than the horizon. Renders identically to `current` except desaturated with a dotted underline and an explicit "last observed" date. |
| `historical` | Validity window has closed (contract expired, deployment decommissioned, portal deleted). The outline's `historical`, moved to this axis. Shown only in timeline/history views by default. |
| `scheduled` | Validity window starts in the future (a signed contract not yet effective; an approved but uninstalled deployment). Never counted in "active" totals. §19.11/§19.12 depend on this. |

Per-claim-type staleness horizons (initial proposal, tunable): device count from a transparency portal — 30 days; retention configuration — 90 days; sharing edges — 30 days; contract terms — until expiry; policy text — 365 days; physical asset existence (OSM) — 365 days; usage aggregates — 30 days; organization identity — 730 days.

**Axis 4 — `absence_kind` (categorical, 4 values, applies only when the value is null).** Answers §9.4 directly. Modeled on F10.3.

| Value | Means | Never says |
|---|---|---|
| `not_researched` | SIG has not looked. **This is the default for every field on every new entity.** | anything about the world |
| `searched_not_found` | SIG performed a *named, dated, reproducible* search procedure and found nothing. Stores the procedure ID and date. | "there is none" |
| `evidence_of_absence` | A source affirmatively asserts the absence (an agency's records-request response stating no responsive records; a portal listing zero cameras; a policy explicitly prohibiting the technology). Requires an evidence artifact, exactly like a positive claim. | "we didn't find one" |
| `not_applicable` | The field is structurally meaningless for this entity (retention period for an entity with no data system). | anything about coverage |

**The rule that makes this matter:** `not_researched` and `searched_not_found` **must never render as an empty cell, a dash, or a zero.** They render as distinct, labeled, clickable affordances. An empty table cell is a lie by omission and is the single most common failure mode in civic-data sites.

### B.2.2 Mapping the outline's six labels onto the four axes

| Outline label (§9.3) | New home |
|---|---|
| `confirmed` | `support = confirmed` |
| `strongly supported` | `support = strongly_supported` |
| `probable` | `support = probable` |
| `unverified` | Split: `support = unsupported` (weak evidence exists) **vs** `absence_kind = not_researched` (no evidence sought). The outline's single word covered both; they are opposite states. |
| `contradicted` | `conflict = contested` |
| `historical` | `currency = historical` |

## B.3 Exact visual encoding

All contrast ratios below were computed today with a WCAG 2.x relative-luminance implementation (script retained at the scratchpad path; formula per WCAG). Every ratio stated is the computed value.

### B.3.1 Palette policy (the anti-rainbow rule)

**Saturated color in SIG is a scarce resource reserved exclusively for epistemic state.** The entire product uses:

- A **neutral ink ramp** for everything structural and for the support axis.
- **Exactly two saturated hues, product-wide**: amber (conflict) and red (retraction/correction). Plus one blue reserved for links and focus rings — never for data.
- **No green anywhere.** Two reasons, both load-bearing: (1) green/red is the worst pairing for the most common color-vision deficiencies, and (2) in a surveillance-accountability context green reads as "good/safe," and a *confirmed* ALPR deployment is not good news. Encoding high confidence as green would editorialize.

### B.3.2 Tokens

**Light theme** — page `--bg #FFFFFF`, surface `--surface #F8FAFC`, subtle `--subtle #F1F5F9`, map paper `--paper #F5F3EE`.

| Token | Hex | Used for | Computed contrast |
|---|---|---|---|
| `--ink-900` | `#0F172A` | Primary text, `confirmed` glyph fill | 17.85:1 on white |
| `--ink-700` | `#334155` | Secondary text, `strongly_supported` glyph fill | 10.35:1 on white |
| `--ink-600` | `#475569` | Meta text, hatch stroke | 7.58:1 on white; 6.92:1 on `--subtle` |
| `--ink-500` | `#64748B` | Tertiary text, **all meaningful borders and dividers** | 4.76:1 on white; 4.55:1 on `--surface` |
| `--ink-300` | `#CBD5E1` | **Decorative only** — 1.48:1 on white, must never carry meaning |
| `--conflict-fg` | `#78350F` | Contested chip text | 8.15:1 on `--conflict-bg` |
| `--conflict-bg` | `#FEF3C7` | Contested chip background (1.11:1 on white — permitted only because the chip carries a 3:1 border) |
| `--conflict-line` | `#B45309` | Contested border, left-rule, `≠` glyph | 5.02:1 on white; 4.51:1 on `--conflict-bg`; 4.53:1 on `--paper` |
| `--retract-fg` | `#7F1D1D` | Retracted text | 8.20:1 on `--retract-bg` |
| `--retract-bg` | `#FEE2E2` | Retracted chip background |
| `--retract-line` | `#B91C1C` | Retracted border, strike rule, `✕` | 6.47:1 on white |
| `--link` / `--focus` | `#1D4ED8` | Links, 2px focus ring | 6.70:1 on white; 6.04:1 on `--paper` |

**Dark theme** — page `--bg #0B1220`, surface `--surface #111A2C`, subtle `--subtle #172033`, map paper `--paper-dark #1A1F2B`.

| Token | Hex | Computed contrast |
|---|---|---|
| `--ink-50` | `#F1F5F9` | 17.09:1 on bg |
| `--ink-200` | `#E2E8F0` | 15.19:1 on bg |
| `--ink-300` | `#CBD5E1` | 12.61:1 on bg |
| `--ink-400` | `#94A3B8` | 7.30:1 on bg; 6.78:1 on surface |
| `--border` | `#64748B` on bg (3.93:1) / `#7C8BA1` on surface (5.02:1) — **`#475569` fails at 2.47:1 and is banned as a border in dark** |
| `--conflict-fg` | `#FDE68A` | 11.70:1 on `--conflict-bg` |
| `--conflict-bg` | `#3B2408` | 1.29:1 on page — permitted only with the 3:1 border |
| `--conflict-line` | `#F59E0B` | 8.72:1 on bg; 6.78:1 on chip; 7.67:1 on `--paper-dark` |
| `--retract-fg` | `#FECACA` | 11.16:1 on `#450A0A` |
| `--retract-line` | `#F87171` | 6.77:1 on bg |
| `--link` / `--focus` | `#93C5FD` | 10.38:1 on bg |

Implementation: define both palettes as custom properties on `:root`, redefine under `@media (prefers-color-scheme: dark)` guarded as `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`. `color-scheme: light dark` on `:root` is Baseline widely available since January 2022 (F10.45), so form controls and scrollbars follow automatically; `light-dark()` is available as a compaction but the three-block pattern is required for the explicit toggle.

### B.3.3 The support badge — exact spec

```
 ┌──────────────────────────────────────────────────────────────────┐
 │  ⊕⊕⊕⊕  Confirmed                                                 │   support = confirmed
 │  ⊕⊕⊕◯  Strongly supported                                        │   support = strongly_supported
 │  ⊕⊕◯◯  Probable · single source                                  │   support = probable  + reason
 │  ⊕◯◯◯  Unsupported · community report only                       │   support = unsupported + reason
 └──────────────────────────────────────────────────────────────────┘
```

- **Form:** four 8px circles, 3px gap, baseline-aligned with the label. Filled circles use `--ink-900` (confirmed), `--ink-700` (strongly supported), `--ink-600` (probable), `--ink-500` (unsupported). Unfilled circles are 1.5px rings in `--ink-500` (4.76:1 — meets SC 1.4.11's 3:1 for graphical objects).
- **Redundancy (SC 1.4.1):** the encoding is *count of filled circles* + *ink density* + *the literal word*. Color alone conveys nothing. Removing all color leaves the badge fully legible — this is the acceptance test.
- **Typography:** label in the UI sans at 12px/16px, `font-weight: 600`, `letter-spacing: 0.01em`, small-caps-like via `font-variant-caps: all-small-caps` **only if** the chosen face has real small caps; otherwise plain sentence case (faux small caps degrade screen-reader pronunciation and print quality).
- **Reason code** renders as ` · <reason gloss>` in `--ink-600` at 11px, never truncated below 3 words.
- **Accessible name:** `<span role="img" aria-label="Confidence: probable. Downgraded because: only one source.">`. Never expose the glyph characters to AT.
- **Print:** circles print as `●●○○`; the reason gloss is never `display:none` in print.
- **Target size (SC 2.5.8):** the badge is a control (it opens the evidence expander), so its hit area is padded to ≥24×24 CSS px even though the glyph is 8px tall.

### B.3.4 The conflict marker — exact spec

```
   ┃ ≠4   Device count: 20        ← contested. Amber 3px left rule on the row.
   ┃      portal 20 · contract 25 · presentation 22 · OSM 18
```

- **Form:** a 3px left rule in `--conflict-line` on the containing row/cell, plus an inline chip `≠4` (the `≠` glyph plus the count of *distinct asserted values*, not the count of sources).
- **Redundancy:** the `≠N` glyph and the left rule are both non-color signals (a rule is a shape; the glyph is a character). In monochrome the rule renders as a 3px black bar and the chip as `[≠4]`.
- **`resolved`** uses the same `≠N` chip with a hollow background and a superscript check: `≠4✓`, plus the resolution rationale one line below in `--ink-600`.
- **`retracted`** uses `--retract-line`: the value gets `text-decoration: line-through 2px`, prefixed by `✕`, followed by ` · retracted 2026-05-04 · reason: misattributed entity`. Retracted claims stay in the DOM and in exports forever.
- **Accessible name:** `aria-label="Sources disagree: 4 different values asserted. Reconciled to 20."` The `≠` character must not be read as "not equals" alone.

### B.3.5 The currency marker

- `current` — no marker.
- `stale` — the value is rendered with `opacity: 1` but in `--ink-600` rather than `--ink-900`, with `text-decoration: underline dotted 1px --ink-500`, followed by ` · last observed 2025-11-02 (291 days ago)`. **Never** hide the age behind a tooltip; SC 1.4.1 aside, P3 needs to read it aloud.
- `historical` — rendered inside a `<del>`-styled but not struck container with a leading `†` and the closed date range `2019-04-01 → 2023-03-31`. Excluded from all default aggregates; a "show historical" toggle is a URL parameter (`?t=all`), not hidden state.
- `scheduled` — leading `→` and `effective 2026-10-01`. Excluded from "active" counts, with a footnote stating the exclusion.

### B.3.6 The absence affordances (this is the §9.4 UI)

Never an empty cell. Four distinct renderings:

```
 ┌───────────────────────────────────────────────────────────────────────────┐
 │  Retention period      ░░░░░░  Not researched            [ Research this ] │  not_researched
 │  Facial recognition    ⌀ No evidence found · searched 2026-07-14  [How?]   │  searched_not_found
 │  Immigration sharing   ⊘ Prohibited by written policy   ⊕⊕⊕◯  [Evidence]  │  evidence_of_absence
 │  Retention period      —  Not applicable (no data system on record)        │  not_applicable
 └───────────────────────────────────────────────────────────────────────────┘
```

- `not_researched`: a **hatched fill** (45° 2px lines, `--ink-600` on `--subtle`, computed 6.92:1) filling the value slot, with the literal words "Not researched" and a primary-styled `[ Research this ]` button that creates the queue task (F10.6). The hatch pattern is the only texture in the product and it means exactly one thing.
- `searched_not_found`: glyph `⌀`, the words "No evidence found," the search date, and a `[How?]` disclosure that names the exact procedure (which sources were queried, with what query, on what date). Without the procedure this state is indistinguishable from `not_researched` and must not be used.
- `evidence_of_absence`: glyph `⊘`, an affirmative sentence, **and a full support badge**, because absence-evidence is evidence and gets graded like everything else.
- `not_applicable`: an em dash **plus the reason in parentheses**. A bare em dash is banned product-wide.

## B.4 The contradiction UI, concretely (§6.5)

The canonical case: portal 20, contract 25, presentation 22, OSM 18.

### B.4.1 In a table cell

```
┌──────────────────┬───────────────────────────────────┬──────────────┐
│ Metric           │ Value                             │ Confidence   │
├──────────────────┼───────────────────────────────────┼──────────────┤
│ ALPR cameras     │ ┃ 20  ≠4                          │ ⊕⊕⊕◯ ▾       │
│ (active)         │ ┃ range across sources: 18 – 25   │ contested    │
└──────────────────┴───────────────────────────────────┴──────────────┘
```

Rules: the reconciled value is typographically dominant; the **range across sources is always printed next to it**, never behind a hover. A hover-only range fails SC 2.1.1 (keyboard), fails on touch, and fails in print. `≠4` is the count of distinct values.

### B.4.2 In the detail panel (the expander)

```
┌─ ALPR cameras, active — Example City PD ───────────────────────── [×] ─┐
│                                                                        │
│  Reconciled: 20      ⊕⊕⊕◯ strongly supported   ┃ ≠4 contested          │
│  Rule applied: most-recent-Tier-A-operational  ·  applied 2026-08-04   │
│  Applied by: reconciliation rule R-CNT-03 (automatic), unreviewed      │
│                                                                        │
│  Claim dotplot (each mark is one asserted value, not a distribution)   │
│                                                                        │
│   16   18   20   22   24   26                                          │
│    ├────●────◆────●─────●───┤                                          │
│         │    │    │     └── contract, 25, Tier B, signed 2025-04-03    │
│         │    │    └── presentation, 22, Tier B, 2026-02-11             │
│         │    └── ◆ portal, 20, Tier A, observed 2026-08-04  ← selected │
│         └── OSM mapped, 18, Tier C, observation not assertion          │
│                                                                        │
│  ⚠ These four numbers may not be measuring the same thing:            │
│     · contract 25 = units purchased (§19.11 contracted ≠ installed)   │
│     · OSM 18 = independently observed devices, a LOWER BOUND, not a    │
│       claim about the total (§9.4 absence ≠ evidence of absence)       │
│                                                                        │
│  [ Why 20? ]  [ Dispute this ]  [ Create research task ]  [ Permalink ]│
└────────────────────────────────────────────────────────────────────────┘
```

Three design decisions worth defending:
1. **The dotplot is explicitly labeled "not a distribution."** Rendering four asserted integers as a density or an error bar would manufacture a posterior that does not exist. F10.5's frequency framing without F10.5's statistical claim.
2. **The semantic-mismatch warning is mandatory, not optional.** In the §6.5 case, the "contradiction" is substantially an artifact of four different definitions. Rendering it as a pure numeric disagreement would teach readers the wrong thing. Every reconciliation rule must declare which of its inputs are *measuring different quantities*, and the UI must surface that above the numbers.
3. **`[ Dispute this ]` is a first-class button available to anyone**, including the subject agency. It creates a public, tracked dispute record. See Part E.5.

### B.4.3 In an export (CSV)

CSV is lossy by nature, so the rule is: **the flat file must be unusable-as-if-certain.** Every reconciled numeric column ships with four sidecar columns and the file ships with a companion `datapackage.json` (F10.46):

```csv
org_id,metric,value,support,conflict,currency,distinct_values,value_min,value_max,as_of,claim_url
sig:org/us-xx-example-city-pd,alpr_active_devices,20,strongly_supported,contested,current,4,18,25,2026-08-04,https://…/claims/c_8f2a…
```

Never emit a bare `value` column. If a consumer wants one, they can select it; SIG will not make it the default shape.

### B.4.4 In an API response (JSON)

```jsonc
{
  "claim_id": "c_8f2a91",
  "subject": "sig:org/us-xx-example-city-pd",
  "predicate": "alpr_active_device_count",
  "value": 20,
  "epistemic": {
    "support": "strongly_supported",
    "support_ordinal": 3,
    "downgrade_reasons": ["single_tier_a_source", "extraction_unreviewed"],
    "conflict": "contested",
    "distinct_asserted_values": 4,
    "currency": "current",
    "observed_at": "2026-08-04",
    "valid_from": "2026-08-04", "valid_to": null,
    "absence_kind": null
  },
  "reconciliation": {
    "rule": "R-CNT-03",
    "rule_url": "https://…/methodology/rules/R-CNT-03",
    "rationale": "Most recent Tier-A operational source preferred over contracted quantity.",
    "reviewed_by": null,
    "semantic_mismatch_note": "contract quantity measures units purchased, not units installed"
  },
  "competing_claims": [
    {"value": 25, "source_tier": "B", "evidence_id": "e_44c1", "observed_at": "2025-04-03",
     "measures": "contracted_quantity", "url": "https://…/evidence/e_44c1#page=3"},
    {"value": 22, "source_tier": "B", "evidence_id": "e_9de0", "observed_at": "2026-02-11", "measures": "asserted_deployed_quantity"},
    {"value": 18, "source_tier": "C", "evidence_id": "e_1b77", "observed_at": "2026-06-30",
     "measures": "independently_observed_lower_bound", "is_lower_bound": true}
  ],
  "_links": {"self": "…", "evidence": "…", "history": "…", "dispute": "…"}
}
```

**Normative API rules:** (a) `value` and `epistemic` are never separable — a response shape that omits `epistemic` must not exist; (b) `competing_claims` is present and non-empty whenever `conflict != "uncontested"`; (c) `measures` is required on every competing claim so consumers can detect the semantic-mismatch case programmatically; (d) `is_lower_bound: true` marks observation-derived counts, which is how §9.4 is enforced machine-side.

## B.5 The coverage / negative-space UI

### B.5.1 The coverage meter

Per jurisdiction and per entity, a fixed-slot meter over the dossier's mandatory field set (the Appendix B schema). Not a percentage bar — a **slot grid**, because a percentage implies a denominator SIG does not have.

```
Coverage — Example City PD                          as of 2026-08-20
┌────────────────────────────────────────────────────────────────────┐
│ Technologies      ████ 4 documented   ░░ 2 not researched          │
│ Contracts         ███  3 documented   ⌀ 1 searched, none found     │
│ Retention config  ██   2 documented   ░░░░ 4 not researched        │
│ Sharing edges     █    1 documented   ░░░░░░░ 7 not researched     │
│ Policy            ███  3 documented                                │
│ Usage/audit       ⌀    searched 2026-07-14, no public data         │
│ Incidents         ░░░░ not researched                              │
├────────────────────────────────────────────────────────────────────┤
│ 13 of 27 fields documented · 12 not researched · 2 searched-empty  │
│ ⚠ Low coverage. Absence of a row below does NOT mean absence of    │
│   the technology. [ What we looked for ]  [ Claim this jurisdiction ]│
└────────────────────────────────────────────────────────────────────┘
```

- Filled blocks `█` = documented; hatched `░` = `not_researched`; `⌀` = `searched_not_found`. Three textures, no color needed.
- The bottom line is **always** present, always states the raw counts, and always carries the §9.4 disclaimer verbatim when coverage < 60%.
- `[ Claim this jurisdiction ]` is the Q36 entry point (§C.6).

### B.5.2 Coverage on the map — the negative-space problem

A map with no dots in a county reads as "no surveillance there." This is the most dangerous single rendering in the product. Mitigations, all required:

1. A **coverage underlay** beneath the point layer: counties/places SIG has never researched are filled with the same 45° hatch, at ~12% opacity, and the legend says "not researched — absence of dots means nothing here."
2. The point layer is **never** rendered without the coverage underlay legend visible. They are one control.
3. A **VSUP-style desaturating choropleth** (F10.4) for any derived density measure: as coverage confidence falls, the fill collapses toward the neutral mid-tone so a low-coverage county cannot read as a low-density county.
4. Zoom-dependent copy in the empty-state overlay: at z ≤ 7, "SIG has documented N of M jurisdictions in view."

---

# Part C — The seven surfaces

Global conventions for all seven:

- **URL scheme root:** every entity has a stable, opaque-but-readable id. `sig:org/us-06-berkeley-pd` → `/org/us-06-berkeley-pd`. IDs never change; renames create an alias redirect. (Answers Q37.)
- **As-of parameter:** every content URL accepts `?as_of=YYYY-MM-DD`. Omitted = now. Present = a bitemporal reconstruction. This is the citation primitive.
- **Format suffix:** `.json`, `.csv`, `.ttl`, `.ics`, `.pdf` on the same path. Content negotiation is supported but the suffix is canonical, because a suffix survives being pasted into a footnote.
- **Every page has:** a "how we know this" module, an as-of stamp, a citation block, a corrections link, and a coverage statement.
- **Progressive enhancement:** every page renders complete and correct with JavaScript disabled. Interactive surfaces (map, graph) degrade to their tabular equivalents, not to blank boxes.

## C.1 Local surveillance dossier (§15.1) — designed in most detail

### C.1.1 Information architecture

Content contract = Appendix B's YAML. Each top-level YAML key becomes a named, anchor-linkable section, in this order (ordered by what P3 needs at a podium):

| # | Section | Anchor | Appendix-B key | Print page |
|---|---|---|---|---|
| 0 | Header + at-a-glance | `#top` | `jurisdiction`, `organizations` | 1 |
| 1 | What is deployed | `#deployments` | `deployments` | 1 |
| 2 | What it costs and when it expires | `#procurement` | `contracts` | 1 |
| 3 | Who else can see the data | `#sharing` | `sharing` | 2 |
| 4 | How long it is kept / how it is configured | `#configuration` | `configuration` | 2 |
| 5 | How much it is used | `#usage` | `usage` | 2 |
| 6 | Where the hardware is | `#assets` | `physical_assets` | 2 |
| 7 | Policy | `#policy` | `policies` | 3 |
| 8 | Accountability events, litigation, incidents | `#accountability` | `accountability_events` | 3 |
| 9 | Timeline | `#timeline` | derived | 3 |
| 10 | **What we don't know** | `#gaps` | `research_gaps` | 3 |
| 11 | How we know this / methodology / citation | `#provenance` | derived | 4 |

**Section 10 is not an appendix.** It appears in the print export, in the summary card, and in the API. In a project whose defining standard is "no synthetic certainty," the gap list is a headline feature.

### C.1.2 Primary screen

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ SIG   Search entities, places, documents…              [ Methodology ] [ API ] [ ⌂ ]  │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│  EXAMPLE CITY, XX  ·  Example City Police Department                                  │
│  Surveillance dossier                                                                 │
│                                                                                       │
│  Snapshot as of 2026-08-20 14:02 UTC   ·   [ view as of ▾ ]   ·   [ ⎙ Print / PDF ]  │
│  Cite this page ▾   ·   Permalink: sig.org/org/us-xx-example-city-pd?as_of=2026-08-20 │
│                                                                                       │
│  ┌── AT A GLANCE ────────────────────────────────────────────────────────────────┐   │
│  │ Technologies documented   4    ALPR · RTCC integration · FR (contracted) · … │   │
│  │ Active deployments        3    ⊕⊕⊕◯                                          │   │
│  │ Devices, active           20   ┃≠4  range across sources 18–25    ⊕⊕⊕◯       │   │
│  │ Annual documented cost    $63,000  ⊕⊕⊕⊕   (2 contracts, 1 not researched ░)  │   │
│  │ Next contract expiry      2027-04-02  · 590 days   [ + calendar ] [ alert ]  │   │
│  │ Outbound sharing (config) 147 orgs ⊕⊕⊕◯  · observed 2026-08-04               │   │
│  │ Inbound sharing (config)  312 orgs ⊕⊕⊕◯                                      │   │
│  │ Coverage                  13 / 27 fields documented  ▓▓▓▓▓▓░░░░░░  [ detail ]│   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                       │
│  ⚠ This page is incomplete by construction. 12 of 27 fields have not been researched. │
│     Absence of a row below is not evidence that a technology is absent. [ Why? ]      │
│                                                                                       │
├──────────┬────────────────────────────────────────────────────────────────────────────┤
│ CONTENTS │  1 · WHAT IS DEPLOYED                                       [ ⌄ collapse ] │
│          │                                                                            │
│ ▸ Deployed│ ┌───────────────┬────────┬──────────┬───────────┬────────┬─────────────┐ │
│ ▸ Cost    │ │ Technology    │ Vendor │ Status   │ Devices   │ Since  │ Confidence  │ │
│ ▸ Sharing │ ├───────────────┼────────┼──────────┼───────────┼────────┼─────────────┤ │
│ ▸ Config  │ │ ALPR (fixed)  │ Flock  │ active   │ ┃20  ≠4   │2023-06 │ ⊕⊕⊕◯ ▾     │ │
│ ▸ Usage   │ │ RTCC integr.  │ Fusus  │ active   │ n/a       │2025-01 │ ⊕⊕◯◯ ▾     │ │
│ ▸ Assets  │ │ Face recog.   │ —      │→scheduled│ —         │2026-10 │ ⊕⊕◯◯ ▾     │ │
│ ▸ Policy  │ │ Gunshot detn. │ ░░░░░░ Not researched                  [Research it]│ │
│ ▸ Events  │ └───────────────┴────────┴──────────┴───────────┴────────┴─────────────┘ │
│ ▸ Timeline│                                                                            │
│ ▸ GAPS ⚠ │   ▾ expanded row: ALPR (fixed) · Flock Safety                             │
│ ▸ How we  │   ┌────────────────────────────────────────────────────────────────────┐ │
│    know   │   │ Reconciled 20 devices  ⊕⊕⊕◯  ┃≠4 contested                        │ │
│          │   │ rule R-CNT-03 · most-recent Tier-A operational · auto, unreviewed   │ │
│          │   │  16  18  20  22  24  26                                             │ │
│          │   │   ├───●───◆───●───●──┤                                              │ │
│          │   │ ◆ portal 20  Tier A  obs 2026-08-04   [doc ▸ p.1]                  │ │
│          │   │ ● contract 25 Tier B  signed 2025-04-03 (units purchased) [doc▸p.3] │ │
│          │   │ ● council presentation 22 Tier B 2026-02-11 [doc ▸ slide 7]        │ │
│          │   │ ● OSM mapped 18 Tier C 2026-06-30 — LOWER BOUND, not a claim       │ │
│          │   │ ⚠ these measure different quantities — see note                    │ │
│          │   │ [ Why 20? ] [ All 4 documents ] [ Dispute ] [ Task ] [ Permalink ]  │ │
│          │   └────────────────────────────────────────────────────────────────────┘ │
└──────────┴────────────────────────────────────────────────────────────────────────────┘
```

Continued below the fold:

```
│  10 · WHAT WE DON'T KNOW                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │ ░ 7+ contracted/reported ALPR units are not located in OSM        [ Task → ] │    │
│  │ ░ No current SharedNetworks.csv on file (last: 2026-05-31)        [ Task → ] │    │
│  │ ░ Gunshot detection: never researched                             [ Task → ] │    │
│  │ ⌀ No public audit data — searched HIBF + portal on 2026-07-14     [ How?  ]  │    │
│  │ ┃ 42 contracted vs 38 portal-reported units unreconciled          [ Task → ] │    │
│  │ ░ Unknown whether inactive cameras were removed or retained       [ Task → ] │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│  [ Claim this jurisdiction's research queue ]   6 open tasks · 0 claimed             │
│                                                                                       │
│  11 · HOW WE KNOW THIS                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │ 19 evidence artifacts · 14 primary documents · 3 vendor portals · 2 datasets │    │
│  │ Oldest source 2023-06-14 · newest 2026-08-04 · median age 71 days            │    │
│  │ Sources by tier:  A ████ 6   B ██████ 9   C ██ 3   D █ 1   E 0   F 0         │    │
│  │ Independence: 4 source families (portal, municipal records, OSM, EFF Atlas)  │    │
│  │ 3 reconciliation rules applied — R-CNT-03, R-SHR-01, R-LIFE-02  [ read them ]│    │
│  │ 0 of 12 numeric claims have been human-reviewed.  ⚠                          │    │
│  │ Licence: this page mixes ODbL (physical assets) and CC-BY-4.0 (everything    │    │
│  │ else). Per-row licence is in the CSV/JSON. [ Licensing ]                     │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│  Cite as: Surveillance Infrastructure Graph, "Example City Police Department          │
│  surveillance dossier," snapshot 2026-08-20, https://sig.org/org/us-xx-…?as_of=…      │
│  [ Copy BibTeX ] [ Copy APA ] [ Copy Chicago ] [ Copy .ris ]                          │
│  Found an error? [ Report a correction ] · Corrections log for this page (0)          │
```

### C.1.3 Key interactions

| Interaction | Behavior | No-JS fallback |
|---|---|---|
| Expand a fact's evidence | Row expander, `<details>/<summary>` semantics, keyboard `Enter`/`Space`, `aria-expanded` | Native `<details>`; server-renders open when `?expand=<claim_id>` |
| View as of a past date | Date picker writes `?as_of=` and reloads | A `<form method="GET">` with a date input |
| Print / PDF | Client print stylesheet; server-side WeasyPrint for the shareable PDF at `/org/{id}.pdf?as_of=` | The `.pdf` URL is a plain link |
| Cite this | Popover with 4 formats + copy | The formats are rendered inline in `#provenance`; copy buttons are the only JS |
| Dispute / correct | Opens `/corrections/new?claim=<id>` | A plain form page |
| Research task | Opens `/queue/new?from=<claim_id>` prefilled | A plain form page |

### C.1.4 States

- **Empty (entity exists, nothing researched):** the dossier renders in full with every section in `not_researched`, the coverage meter at 0/27, and a single large CTA: "SIG has not researched this agency. [ Start the first task ]." It does **not** 404, and it does **not** say "no surveillance found." This is the §9.4 requirement made structural.
- **Partial:** the normal case. Sections with no documented facts still render with their hatched slots.
- **Loading:** server-rendered — there is no loading state for the dossier body. Only the map inset and the sharing graph lazy-load, each with a skeleton that is replaced by the tabular equivalent if the island fails.
- **Error (island failure):** the island's `<noscript>`/fallback content — the table — remains. A dismissible banner: "The interactive map failed to load. The full device list is below."
- **as_of before the entity existed:** "SIG had no record of this organization on 2019-01-01. Earliest snapshot: 2024-03-11. [ view earliest ]."

### C.1.5 URL scheme

```
/org/{org_id}                        canonical dossier (now)
/org/{org_id}?as_of=2026-03-01       bitemporal snapshot
/org/{org_id}.pdf?as_of=…            council-packet PDF
/org/{org_id}.json|.csv|.ttl         machine formats, same as_of semantics
/org/{org_id}/history                changelog of every fact on the page
/org/{org_id}/evidence               all artifacts
/org/{org_id}/gaps                   the gap list alone (also the .ics feed root)
/place/{geoid}                       jurisdiction-level dossier (rolls up N orgs)
/claim/{claim_id}                    a single fact, permanently addressable
/evidence/{evidence_id}#page=3       a document, page-anchored
```

`/place/{geoid}` uses Census GEOIDs so a city dossier is joinable to ACS without a crosswalk. `/org/{org_id}` uses ORI where one exists, else a SIG-minted slug, with the ORI recorded as an alias.

### C.1.6 The print/PDF export

Four pages, US Letter and A4, generated server-side by WeasyPrint 69.0 (F10.44) from the same HTML with a print stylesheet — not a separate template, so drift is impossible.

- **Page 1:** header, as-of stamp, permalink **printed as a URL in monospace**, QR code to the permalink, at-a-glance table, deployments table.
- **Page 2:** procurement, sharing, configuration, usage, a static map image of documented assets.
- **Page 3:** policy, accountability events, timeline, **What we don't know**.
- **Page 4:** How we know this — full evidence list with document titles, dates, capture timestamps, and short hashes; the licensing statement; the citation block; the corrections URL.
- **Running footer on every page:** `Surveillance Infrastructure Graph · snapshot 2026-08-20 · sig.org/org/us-xx-example-city-pd · page N of 4 · This document is a snapshot; check the URL for updates and corrections.`
- Print rules: `@page { size: letter; margin: 18mm 16mm 22mm; }`; every link's `href` printed via `a[href^="http"]::after { content: " (" attr(href) ")" }` in the evidence list only; no expander is collapsed in print; the hatched `not_researched` fill prints as visible hatching (never as white).

### C.1.7 What makes it trustworthy

1. Every number is clickable to a document with a page anchor and a capture timestamp.
2. The gap list is above the fold in the summary and on page 3 in print.
3. The as-of stamp and permalink are in the header, the footer, and every print page.
4. "0 of 12 numeric claims have been human-reviewed" is stated when true. Admitting the pipeline is automated is more credible than implying it isn't.
5. The correction path is on the page, not in a contact form three clicks away.
6. Tone (Part E) never editorializes; the page states what sources say and who said it.

## C.2 Infrastructure map (§15.2)

### C.2.1 The performance problem: 400k+ points

**Solution: pre-baked PMTiles, not runtime GeoJSON.** Build the physical-asset layer with tippecanoe 2.79.0 (F10.29) into a single PMTiles v3 archive (F10.27) served by range requests from object storage. Concrete tippecanoe invocation shape:

```
tippecanoe -o assets.pmtiles \
  --maximum-zoom=15 --minimum-zoom=4 \
  --drop-densest-as-needed --extend-zooms-if-still-dropping \
  --cluster-distance=4 --cluster-maxzoom=10 \
  --accumulate-attribute=count:sum \
  --attribution='© OpenStreetMap contributors, ODbL' \
  --layer=assets assets.geojsonl
```

At z ≤ 10, tippecanoe clustering yields H3-like aggregation without a second pipeline; at z ≥ 11 individual devices render. deck.gl (F10.33) is reserved for the *dynamic* overlays — the currently-filtered selection and the sharing edges — where the data changes per interaction and cannot be pre-baked.

**Switch thresholds (normative):**

| Zoom | Rendering | Rationale |
|---|---|---|
| 0–5 | H3 r4/r5 bins (F10.35: r5 ≈ 252.9 km² average hexagon) as a choropleth of *documented* asset counts, with the coverage hatch underlay | At national scale, individual dots are meaningless and imply precision |
| 6–9 | H3 r6/r7 bins (r7 ≈ 5.16 km²) | Metro-scale density |
| 10–12 | tippecanoe clusters with counts | Cluster labels remain readable |
| 13+ | Individual assets | Street level, where a dot means "this pole" |

**Never** interpolate between bins. The bin boundaries are honest; a smooth heat map is not.

### C.2.2 Status/confidence without a rainbow

Layers and their encodings — note only **one** saturated hue appears:

| Layer | Geometry | Encoding |
|---|---|---|
| Physical devices | point | Fill = `--ink-900`; **1.5px white halo** (17.85:1 against ink) so dots survive any basemap. Size 5px. Confirmed dots are solid; `probable` dots are 60%-opacity fill with a full-opacity ring; `unsupported` dots are hollow rings only. Contrast verified: `--ink-900` on `--paper` = 16.10:1; hollow ring `--ink-700` on `--paper` = 9.34:1. |
| Deployment (org-level, no coords) | — | **Not on the map.** See C.2.4. |
| Status | point | `active` = filled; `scheduled` = hollow with a `→` leader; `decommissioned` = hollow with a 1px cross; `unknown` = hatched. Four *shapes*, zero colors. |
| Contested facts | point/area | The only amber: `--conflict-line` ring, 2px. 4.53:1 on light paper, 7.67:1 on dark paper. |
| RTCC / fusion centers | point | A distinct **shape** (square, 9px) not a distinct color. |
| Service areas | polygon | 1px `--ink-500` outline + 8% fill, **never** a saturated fill. |
| Coverage (not researched) | polygon | 45° hatch at 12% |

Dark-mode map: swap to a dark Protomaps theme with `--paper-dark #1A1F2B`, ink ramp inverted (`--ink-200` dots), amber shifts to `#F59E0B` (7.67:1 verified).

### C.2.3 Sharing edges without a hairball

A national ALPR sharing graph has O(10⁵–10⁶) edges. Drawing them on a map is always wrong. Three modes, selected explicitly by the user, never all-at-once:

1. **Ego mode (default).** No edges at all until a node is selected. On selection, draw only that org's edges, up to a cap of 150 rendered arcs; beyond the cap, collapse the tail into a labeled "…and 262 more organizations [ list ]".
2. **Aggregate mode.** Edges are aggregated to a chosen administrative level (county → county, state → state). A county-to-county chord/arc layer with width = log(edge count) is legible; org-to-org is not.
3. **Great-circle arcs with a *directional gradient*, not arrowheads.** deck.gl `ArcLayer` with source-end at 30% opacity and target-end at 100% — direction reads without arrowheads, which are unreadable at map scale. Bidirectional pairs render as a single arc with a bidirectional marker in the legend and a `⇄` in the tabular equivalent.
4. **Never render an edge whose endpoints are `entity_resolution_uncertain`** without the amber ring on both endpoints. A hairball built on bad entity resolution is worse than no picture (§19.6).

### C.2.4 Assets with no coordinates

A large fraction of SIG's knowledge has no point geometry: a deployment known from a contract, an org with no mapped devices, a mobile asset, a redacted location (§13.3). Rules:

- **Never** place a marker at a jurisdiction centroid. A centroid dot is a fabricated coordinate and violates "no unexplained dots."
- Coordinate-less entities appear in a persistent **"In this view but not on the map (N)"** panel docked beside the map, itself the tabular equivalent required by SC 1.1.1/1.4.1 (F10.24). Every map view has this panel; it is not a fallback, it is a co-equal representation.
- Entities with a *known jurisdiction but no point* render as a **jurisdiction-polygon highlight** with a count label — an honest encoding of "somewhere in this polygon."
- Deliberately withheld coordinates (per the §13.3 publication policy) render in the panel with `⊘ location withheld — private-residence candidate` and a link to the policy. The withholding is disclosed; the location is not.

### C.2.5 Wireframe

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ SIG Map     [ search a place ]                      as of 2026-08-20  [ share ] [⎙]│
├───────────────┬────────────────────────────────────────────────────┬───────────────┤
│ LAYERS        │                                                    │ IN VIEW (612) │
│ ☑ Devices     │        ░░░░░░░░ not researched ░░░░░░              │ ───────────── │
│ ☐ Deployments │      ░░░░╔═══════════════════╗░░░░░                │ ⬤ 431 devices │
│ ☐ RTCCs       │      ░░░░║   ⬤  ⬤     ⬤     ║░░░░░                │   confirmed   │
│ ☐ Sharing ▸   │      ░░░░║  ⬤ ▣RTCC  ○      ║░░░░░                │ ◯  84 probable│
│ ☐ Service     │      ░░░░║    ⬤  ⬤ ⊛contested║░░░░                 │ ⊛  12 contested│
│ ☑ Coverage    │      ░░░░╚═══════════════════╝░░░░░                │ ▣   3 RTCCs   │
│               │                                                    │ ───────────── │
│ STATUS        │            [ + ]  [ − ]   [ ⌖ ]                    │ NOT ON MAP(82)│
│ ☑ active      │                                                    │ 61 deployments│
│ ☑ scheduled   │  ┌───── LEGEND ─────────────────────────────────┐  │  (no coords)  │
│ ☐ decommis.   │  │ ⬤ confirmed  ◯ probable  ⊛ contested        │  │ 18 orgs, no   │
│               │  │ ▣ RTCC  → scheduled  ✕ decommissioned        │  │   device data │
│ CONFIDENCE    │  │ ░ NOT RESEARCHED — absence of dots here      │  │  3 withheld ⊘ │
│ min ⊕⊕◯◯ ▾   │  │   means nothing. [ what we searched ]         │  │ [ view table ]│
│               │  └──────────────────────────────────────────────┘  │               │
│ [ table view ]│  © OpenStreetMap contributors (ODbL) · Protomaps    │               │
└───────────────┴────────────────────────────────────────────────────┴───────────────┘
```

Attribution is permanently visible in the map corner per OSMF guidance (F10.28); it is not collapsed, because SIG has room and because a visible ODbL credit is itself a trust signal.

### C.2.6 URL scheme, states

```
/map                                       default national view
/map?z=13&lat=37.87&lng=-122.27            viewport state in the URL (shareable)
/map?layers=devices,rtcc,sharing&status=active&min_support=2
/map?org=us-xx-example-city-pd             ego mode focused
/map/table?…                               the tabular equivalent, same filters
```

- **No-JS:** `/map` server-renders a static raster of the current viewport plus the full `/map/table` listing. The map is an enhancement over a table, never a replacement.
- **Loading:** basemap first (PMTiles range requests), then the asset layer; a skeleton legend, never a spinner over an empty gray box.
- **Error:** if PMTiles fails, show the table full-width with "Map tiles unavailable."
- **Zero results:** "No documented assets in this view. SIG has researched 2 of 47 jurisdictions here." — never "no surveillance here."

## C.3 Surveillance network explorer (§15.3)

### F10.10 — Force-directed layouts do not stay legible past ~1–2k visible nodes; WebGL renderers change the performance ceiling but not the legibility ceiling

**Claim:** Sigma.js positions itself for "graphs of thousands of nodes and edges" using WebGL, delegating the data model and algorithms to graphology; Cytoscape.js is a full-featured Canvas/SVG graph library at a smaller performance ceiling; Cosmograph is GPU-accelerated at far larger scale but is not open-source licensed.
**Status:** VERIFIED
**Evidence:** `https://www.sigmajs.org/` — "a JavaScript library aimed at visualizing graphs of thousands of nodes and edges," WebGL, "draw larger graphs faster than with Canvas or SVG based solutions"; graphology "handles graph data model & algorithms," sigma "handles graph rendering & interactions." npm `sigma` latest **3.0.3** (2026-04-30, MIT), `graphology` **0.26.0** (2025-01-26, MIT), `cytoscape` **3.34.1** (2026-08-11, MIT), `d3-force` **3.0.0** (2021-06-05, ISC). `@cosmograph/cosmograph` **2.5.1** (2026-08-14) — **license `CC-BY-NC-4.0`**; the underlying `cosmograph-org/cosmos` repo is MIT.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use Sigma 3 + graphology for the explorer; Cytoscape for small curated views; **do not ship `@cosmograph/cosmograph`** — CC-BY-NC-4.0 is not an open-source license, forbids commercial use (ambiguous for a nonprofit with earned revenue), and is incompatible with SIG's own open licensing. If GPU-scale layout is ever needed, use `cosmos` (MIT) directly. And the legibility ceiling, not the render ceiling, is what sets the product default: ego-network-with-expansion.
**Outline delta:** EXTENDS §15.3 — the outline poses four questions but does not constrain the visualization; this finding says the default must not be a whole-graph force layout.

### C.3.1 View types and when each is right

| View | Use when | Why not otherwise |
|---|---|---|
| **Ego network with expansion (DEFAULT)** | Always, unless the user opts out | Answers §15.3's "who can access whose data?" for a *specific* org, which is the only question with an answerable scope |
| **Matrix (adjacency)** | Comparing 10–60 orgs, e.g. all agencies in a county | Immune to hairball; makes reciprocity and clustering readable; keyboard-navigable as a real `<table>` |
| **Sankey / flow** | "How does a local camera become accessible nationally?" — the Appendix C pathway | Shows the *layered* chain (device → org → vendor network → federal) which is what the question actually asks |
| **Arc diagram** | One-dimensional ordering (orgs by state) with edges above | Good for print; degrades to a static SVG |
| **Force-directed whole graph** | Never as a default. Available at `/graph/explore` behind an explicit "this view is not a finding" interstitial | Aesthetic, not analytic; invites over-reading |

### C.3.2 Wireframe (ego + expansion)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Network explorer · Example City PD          [ ego ▾ ] [ matrix ] [ flow ] [ ⎙ ]  │
├──────────────────────────────────────────┬───────────────────────────────────────┤
│                                          │ SELECTED                              │
│           ○ State Police                 │ Example City PD                       │
│          ╱ (in+out)                      │ degree 459 · out 147 · in 312         │
│   ○ ────╱                                │                                       │
│ County  │                                │ ⚠ Centrality is NOT shown by default. │
│ SO      ●━━━━━━━━● Example City PD       │   Degree here counts CONFIGURED       │
│         │   (you are here)               │   sharing, not observed access, and   │
│    ○ ───┘   ▸ expand 147 outbound        │   depends on entity resolution that   │
│  Regional   ▸ expand 312 inbound         │   is ⊕⊕◯◯ for 38 of these nodes.     │
│  Fusion     ▸ expand 3 vendor networks   │   [ show anyway ] [ read §19.6 ]      │
│                                          │                                       │
│   ⊛━━━━⊛  two endpoints with uncertain   │ EDGES (147 outbound)         [ table ]│
│           identity — amber ring          │ ┌───────────────┬──────┬────────────┐ │
│                                          │ │ Target        │ Kind │ Evidence   │ │
│  legend: ● org  ▣ RTCC  ◆ vendor network │ ├───────────────┼──────┼────────────┤ │
│  ─── configured   ═══ observed           │ │ County SO     │ cfg  │ ⊕⊕⊕◯ [doc]│ │
│  ⋯⋯ inferred (dotted, always labeled)    │ │ State Police  │ obs  │ ⊕⊕⊕⊕ [doc]│ │
│                                          │ │ ⊛ "Regional…" │ cfg  │ ⊕⊕◯◯ ⚠ id │ │
│  [ + ] [ − ] [ fit ] [ ⌨ keyboard help ] │ └───────────────┴──────┴────────────┘ │
└──────────────────────────────────────────┴───────────────────────────────────────┘
```

### C.3.3 Centrality, and the §19.6 caveat in the UI

Degree, betweenness, and eigenvector centrality are all computable and all misleading when entity resolution is imperfect. Normative rules:

1. **Centrality is off by default.** The user must click through an interstitial.
2. When on, every centrality number is displayed with an **entity-resolution confidence denominator**: `betweenness 0.41 · computed over 1,204 nodes, 38 of which (3.2%) have unresolved identity`.
3. If >5% of nodes in the computed component have `entity_resolution_uncertain`, the number is rendered `⊕⊕◯◯` and labeled **"unreliable — see methodology"** — not suppressed, but explicitly discounted.
4. Centrality is **never** exported without its denominator fields, and never appears in the API without `entity_resolution_caveat`.
5. `degree` is preferred over `betweenness`/`eigenvector` for public display: it is robust to a single missing edge, whereas betweenness is not, and betweenness on a partially-observed graph is close to meaningless.
6. All three are labeled with what they mean *here*: degree = "number of organizations with a configured or observed access relationship," not "importance."

### C.3.4 Interactions, states, URLs

```
/graph/{org_id}                            ego view
/graph/{org_id}?depth=2&kind=configured    expansion state in the URL
/graph/matrix?place={geoid}                matrix over a county
/graph/flow/{asset_id}                     Appendix-C pathway for one device
/graph/{org_id}/table                      the tabular equivalent (edge list)
```

- Keyboard: `Tab` cycles nodes in degree order; `Enter` selects; `→` expands; `Esc` collapses; `?` opens keyboard help. Node focus updates an `aria-live="polite"` region: "Example City PD, 459 connections, 147 outbound. Press right arrow to expand."
- **No-JS:** `/graph/{id}` server-renders the edge table plus a static SVG of the depth-1 ego network.
- **Empty:** "No access relationships documented for this organization. This does not mean none exist — sharing configuration is documented for 1,142 of ~18,000 U.S. agencies."

## C.4 Procurement / renewal watch (§15.4)

### F10.11 — iCalendar (RFC 5545) gives SIG a durable, subscribable civic-calendar primitive with correct update semantics

**Claim:** RFC 5545 (September 2009) defines VEVENT with `UID`, `DTSTAMP`, `DTSTART`, `DTEND`, `SUMMARY`, `DESCRIPTION`, `URL`, `SEQUENCE`, `STATUS`, and `VALARM`; UID must be stable across copies and modifications, and SEQUENCE must increment on each organizer modification.
**Status:** VERIFIED
**Evidence:** `https://datatracker.ietf.org/doc/html/rfc5545`. UID = "a text value that uniquely identifies the calendar component" consistent across all copies and modifications; "The 'SEQUENCE' number must increment each time the organizer modifies an event."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's contract-expiry feed must set `UID` to the stable claim id (`sig-contract-{contract_id}@sig.org`) so that when a date is corrected, subscribers' calendars *update the existing event* rather than accumulating duplicates — and must bump `SEQUENCE` on every correction. `STATUS:TENTATIVE` is the correct value for a date whose support is below `confirmed`; `STATUS:CONFIRMED` only at `support >= strongly_supported` and `conflict = uncontested`. This is a rare case where an epistemic axis maps cleanly onto an existing standard's field.
**Outline delta:** EXTENDS §15.4 — "actionable civic timing" needs a concrete transport; iCal with correct UID/SEQUENCE semantics is it.

### C.4.1 Wireframe

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Renewal watch          [ my places ▾ ] [ all ] [ ⊞ calendar ] [ ☰ list ]  [ ⎙ ]  │
├───────────────────────────────────────────────────────────────────────────────────┤
│ Filters: place [California ▾] tech [ALPR ▾] window [next 180 days ▾]              │
│                                          Subscribe: [ 📅 iCal ] [ 📡 RSS ] [ ✉ ] │
├───────────────────────────────────────────────────────────────────────────────────┤
│  ⏱ NEXT 30 DAYS                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ 2026-09-02  ·  in 13 days                                                   │ │
│  │ Example City PD — Flock Safety ALPR contract EXPIRES                        │ │
│  │ $126,000 · signed 2025-04-03 · ⊕⊕⊕⊕ confirmed [contract p.1]                │ │
│  │ ▸ Renewal typically requires council action. Last council item: 2026-08-04.  │ │
│  │ ▸ Auto-renew clause: ░ not researched   [ Research this ]                    │ │
│  │ [ + add to calendar ] [ alert me 60/30/7 days before ] [ dossier → ]         │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ 2026-09-14  ·  in 25 days                    ┃ ≠2  dates disagree           │ │
│  │ Riverside County SO — Motorola/Vigilant renewal window OPENS                │ │
│  │ ⊕⊕◯◯ probable · contract says 2026-09-14, agenda packet says 2026-10-01     │ │
│  │ ⚠ SIG shows both. Verify before relying on either. [ see both documents ]    │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
│  📅 60–180 DAYS  (17 events)                                     [ expand ]      │
│  ░ COVERAGE: SIG has contract dates for 84 of ~430 documented CA deployments.    │
│    346 deployments have no procurement evidence.  [ 346 open tasks → ]           │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### C.4.2 Event taxonomy

Six event kinds, each with a distinct `CATEGORIES` value: `contract_expiry`, `renewal_window_opens`, `council_agenda_item`, `policy_review_due`, `procurement_solicitation_closes`, `evidence_staleness_due` (SIG-internal: "this fact will be marked stale on DATE").

The last one is unusual and worth keeping: it lets a local group subscribe to *SIG's own decay*, which is the most reliable generator of useful work.

### C.4.3 Alerts / subscriptions

Three tiers, deliberately ordered by privacy cost:

1. **iCal / RSS (no account, no PII).** `GET /watch.ics?place=us-ca&tech=alpr&window=365`. Any filter combination that produces a list produces a feed. This is the default and the one SIG promotes.
2. **Email digest (email only, double opt-in, no tracking pixels, one-click unsubscribe in the `List-Unsubscribe` header).** Weekly or on-event.
3. **Webhook (for orgs).** POST the same JSON as the API.

Because SIG's non-goals forbid building a surveillance system (§7.2), subscription records are minimized: store the filter, the destination, and a creation timestamp. No open tracking, no click tracking, no IP logs beyond the retention needed for abuse control, and that retention is published.

### C.4.4 Feed shape

```ics
BEGIN:VEVENT
UID:sig-contract-c8f2a91@sig.org
DTSTAMP:20260820T140200Z
DTSTART;VALUE=DATE:20260902
DTEND;VALUE=DATE:20260903
SEQUENCE:2
STATUS:CONFIRMED
CATEGORIES:contract_expiry,ALPR,flock-safety
SUMMARY:Contract expires — Example City PD / Flock Safety ALPR ($126,000)
DESCRIPTION:Confidence: confirmed (2 independent sources).\nSIG snapshot 2026-08-20.\nVerify against the primary document before relying on this date.
URL:https://sig.org/org/us-xx-example-city-pd#procurement
BEGIN:VALARM
TRIGGER:-P30D
ACTION:DISPLAY
DESCRIPTION:30 days until Example City PD ALPR contract expiry
END:VALARM
END:VEVENT
```

RSS/Atom mirrors this at `/watch.xml`, with `<guid isPermaLink="true">` = the claim permalink and the confidence label in the title prefix (`[probable]`) so a headline-only reader still sees the epistemic state.

### C.4.5 States and URLs

```
/watch                              national, next 90 days
/watch?place={geoid}&tech=alpr&window=365
/watch.ics / .xml / .json           same filters
/watch/{event_id}                   one event, permalinked
```

- **Empty:** "No documented procurement events match. SIG has contract dates for 12% of documented deployments — the absence of an event here is much more likely to mean missing evidence than an absent contract. [ 346 open tasks ]"
- **Error:** the `.ics` endpoint must never 500 into a subscriber's calendar client; on backend failure it returns the last good cached feed with a `X-SIG-Stale: true` header and a `SUMMARY` prefix of `[stale feed]`.

## C.5 Evidence viewer (§15.5)

### C.5.1 Wireframe

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Evidence  e_44c1  ·  Example City / Flock Safety agreement (executed)     [ ⤓ ] [⎙]│
├──────────────────────────────────┬────────────────────────────────────────────────┤
│                                  │ ARTIFACT                                       │
│   ┌──────────────────────────┐   │ Title    Master Services Agreement …           │
│   │ …WHEREAS the Department  │   │ Kind     PDF, 14 pp, 2.1 MB                    │
│   │ shall deploy up to       │   │ Source   examplecity.gov/agenda/2025-04-03.pdf │
│   │ ▓▓twenty-five (25)▓▓     │   │ Captured 2025-04-11T09:14:02Z  by SIG crawler  │
│   │ Flock Safety devices…    │   │ SHA-256  a91f…c204  [ verify ]                 │
│   │                          │   │ WARC     w_0c19  [ download 4.4 MB ]           │
│   │  page 3 of 14            │   │ Upstream status  ✓ still live (checked 8h ago) │
│   └──────────────────────────┘   │ Licence  U.S. public record · redistributable  │
│   [◀ p2] [p3] [p4 ▶] [ fit ] [⌕] │ Redactions  none applied by SIG                │
│                                  │                                                │
│   ▓ = highlighted excerpt        │ EXTRACTION                                     │
│                                  │ Method   pdftotext-layout → regex R-EXT-11     │
│  ┌────────────────────────────┐  │ Model    none (deterministic)                  │
│  │ EXCERPT (verbatim)         │  │ Confidence of extraction ⊕⊕⊕◯                  │
│  │ "shall deploy up to        │  │ Human review  ✗ not reviewed  [ review this ]  │
│  │  twenty-five (25) Flock    │  │ Char offsets 4,182–4,241 · page 3              │
│  │  Safety devices"           │  │                                                │
│  │ page 3 · chars 4182-4241   │  │ CLAIMS FROM THIS ARTIFACT (4)                  │
│  │ [ copy with citation ]     │  │ ┃ contracted_quantity = 25  ⊕⊕⊕◯ ┃≠4 [ → ]     │
│  └────────────────────────────┘  │   amount = 126000 ⊕⊕⊕⊕ [ → ]                  │
│                                  │   term_start = 2025-04-03 ⊕⊕⊕⊕ [ → ]           │
│  SNAPSHOT DIFF                   │   term_end = 2027-04-02 ⊕⊕⊕⊕ [ → ]             │
│  [ 2026-05-31 ] ⟷ [ 2026-08-04 ] │                                                │
│  3 changes  ▾                    │ [ Report a problem with this evidence ]        │
└──────────────────────────────────┴────────────────────────────────────────────────┘
```

### C.5.2 The claim ↔ excerpt link

The binding is bidirectional and addressable in both directions:

- From a claim: `/evidence/e_44c1#page=3&chars=4182-4241` scrolls to the page, renders the highlight, and shows the excerpt panel. The fragment is a **plain URL fragment**, so it survives in a footnote and works without JS (the server renders the page image with the highlight burned in when `?render=static`).
- From an excerpt: `[ → ]` on each claim goes to `/claim/{id}`.
- **Copy with citation** yields: `"shall deploy up to twenty-five (25) Flock Safety devices" — Master Services Agreement, City of Example and Flock Safety Inc., executed 2025-04-03, p.3. Captured by SIG 2025-04-11, SHA-256 a91f…c204. https://sig.org/evidence/e_44c1#page=3` — everything P4 needs for a declaration, in one click.

### C.5.3 Extraction-method disclosure (mandatory)

Every claim carries an `extraction` block naming: method (`manual`, `regex`, `table-parse`, `ocr+regex`, `llm-assisted`, `structured-feed`), the rule/model id and version, whether a human reviewed it, and the character offsets. **LLM-assisted extractions are labeled as such, in the UI, always**, are capped at `support = probable` until human-reviewed, and carry the reason code `extraction_unreviewed`. This is non-negotiable for P1 and P4: a journalist must be able to say "a human checked this" or "a model extracted this and no human has checked it," and the second answer must be available rather than hidden.

### C.5.4 The portal-snapshot diff

Transparency portals change silently; §9.2 and §11 depend on detecting that. The diff view:

```
┌─ Example City PD transparency portal ─────────────────────────────────────────────┐
│ [ 2026-05-31 08:00Z ]  ⟷  [ 2026-08-04 08:00Z ]        3 material · 11 cosmetic  │
├───────────────────────────────────┬───────────────────────────────────────────────┤
│ 2026-05-31                        │ 2026-08-04                                    │
│ Cameras                    38     │ Cameras                    20   ▼ −18         │
│ Retention               30 days   │ Retention              365 days   ▲ +335 d ⚠  │
│ Organizations sharing     151     │ Organizations sharing     147   ▼ −4          │
│ Searches (30d)            412     │ Searches (30d)            389                 │
│ (unchanged: 11 fields, hidden)    │                              [ show all ]     │
├───────────────────────────────────┴───────────────────────────────────────────────┤
│ ⚠ Retention changed 30 → 365 days. Written policy on file says 30 days.           │
│   This creates contradiction C-2291 and research task T-8814.  [ open task ]      │
│ Both snapshots archived: WARC w_0a11 (sha 3e8c…), WARC w_0c19 (sha a91f…)         │
└───────────────────────────────────────────────────────────────────────────────────┘
```

Design decisions: two-column, not inline-diff, because portal pages are tabular not prose; **material vs cosmetic** changes are separated and cosmetic ones collapsed by default (whitespace, CSS, ad tokens); every material delta auto-creates the §12 task and the link to it is in the diff. Both WARCs are downloadable with hashes.

### C.5.5 States, URLs, sensitive documents

```
/evidence/{id}                       viewer
/evidence/{id}#page=3&chars=…        deep link
/evidence/{id}.pdf                   the original bytes (or the redacted derivative)
/evidence/{id}/warc                  the WARC, if archived
/evidence/{id}/diff?a=…&b=…          snapshot diff
```

- **Metadata-only artifacts (§13.4):** when a document is archived privately but not republished, the viewer renders the full metadata record, the hash, the capture time, and `⊘ This document is not republished. Reason: contains unredacted personal data. [ policy ] [ request access ]`. The record's *existence* and *provenance* are public even when its bytes are not — that is the §13.4 requirement made concrete.
- **Upstream gone:** `⚠ The source URL no longer resolves (last checked 2026-08-20). SIG's archived copy is the only remaining public record.` — a genuinely valuable state, prominently rendered.
- **No-JS:** page images are served as `<img>` with the highlight rendered server-side; the excerpt panel is plain HTML; pagination is links.

## C.6 Research queue (§15.6)

### F10.12 — Every mature volunteer-work system uses task locking, a separate validation stage, and a "cannot be done" outcome that is distinct from failure

**Claim:** OSM Tasking Manager locks tasks on claim with a timeout and forbids self-validation; MapRoulette provides six task outcomes including "false positive," "already fixed," and "too hard," with points weighted toward correct triage rather than volume; iNaturalist promotes records only on a 2/3 community agreement rule plus a checklist of data-quality criteria.
**Status:** VERIFIED
**Evidence:**
- `https://learnosm.org/en/coordination/tasking-manager/` — "Clicking on the **Start Mapping** button locks the square so that no other mapper can select it until it is released again"; a 2-hour countdown auto-releases; two-stage mapping→validation; "You must not validate your own work - a second pair of eyes will always lead to better quality mapping."
- MapRoulette task statuses via search of `blog.maproulette.org` and the Python client docs: `0 Created, 1 Fixed, 2 False Positive, 3 Skipped, 4 Deleted, 5 Already Fixed, 6 Too Hard`. "Too Hard" leaves the task available to others; "Already Fixed" removes it. Points: "5 points for fixing a task, 3 for marking it as Not an Issue or Already Fixed, and 1 point for marking a task as Too Hard."
- `https://help.inaturalist.org/en/support/solutions/articles/151000169936-…` — Research Grade requires "the community agrees on species-level ID or lower, i.e. when more than 2/3 of identifiers agree on a taxon at species-level," plus a verifiability checklist (accurate date, georeferenced, evidence present, wild/naturalized), and observations revert to Casual on community votes against any criterion.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's queue must have (a) claim-with-timeout locking, (b) a review stage where the reviewer ≠ the submitter, (c) a rich outcome vocabulary in which "I looked and there is nothing" is a *first-class success* worth nearly as much as "I found it," and (d) a promotion rule expressed as an agreement threshold, not a single reviewer's opinion, for contentious claim types. Outcome (c) is what turns volunteer labor into §9.4's `searched_not_found` records — the single highest-value thing the queue can produce and the one most systems fail to capture.
**Outline delta:** **EXTENDS §12 and §15.6 materially.** The outline's seven task generators all produce "go find X" tasks. None of them produce a *disposition vocabulary*, and the outline never says that "searched, found nothing" must be recordable. Without it the queue can only ever grow.

### C.6.1 Task card

```
┌─ T-8814 ────────────────────────────────────────────────────── ⊕⊕ medium ─┐
│ CONTRADICTION · retention configuration                                    │
│ Example City PD (Example City, XX)                          ~25 min · L2   │
├────────────────────────────────────────────────────────────────────────────┤
│ Written policy says 30 days. Transparency portal reported 365 days on      │
│ 2026-08-04. Determine the current configured retention.                    │
│                                                                            │
│ WHAT WOULD RESOLVE THIS (any one):                                         │
│  ☐ A portal capture dated after 2026-08-04 showing the retention field     │
│  ☐ A written agency response stating the configured value                  │
│  ☐ A council packet or audit report stating the value                      │
│                                                                            │
│ WHAT WON'T RESOLVE IT: a news article restating the policy; a vendor        │
│ marketing page; the policy PDF already on file (that's one of the sides).  │
│                                                                            │
│ CONTEXT   [ dossier ] [ policy PDF p.4 ] [ portal snapshot 2026-08-04 ]    │
│ SKILLS    reading a transparency portal · optional: filing a records req.  │
│ BLOCKED BY  none          RELATED  T-8815 (same agency, sharing edges)     │
├────────────────────────────────────────────────────────────────────────────┤
│ [ Claim for 4 hours ]   claimed by 0 · attempted 1 (too hard, 2026-07-02)  │
└────────────────────────────────────────────────────────────────────────────┘
```

"What won't resolve it" is unusual and is the highest-leverage field on the card: it prevents the most common volunteer failure, which is attaching a plausible-looking but circular source.

### C.6.2 Claiming, outcomes, review

- **Claim** locks for a task-class-specific TTL (desk research 4h, field verification 7 days, records request 90 days), auto-releases with a warning at 80% elapsed, and is extendable once without asking.
- **Outcomes** (F10.12), all first-class:

| Outcome | Meaning | Produces | Credit |
|---|---|---|---|
| `resolved` | Evidence attached that answers the task | a claim + evidence artifact | full |
| `searched_not_found` | Named sources checked, nothing found | an `absence_kind = searched_not_found` record **with the procedure** | full — this is the §9.4 generator |
| `not_applicable` | The task's premise is wrong (entity doesn't exist, tech never deployed) | a correction + task retirement | full |
| `partial` | Some evidence found, question not closed | a claim + a narrowed task | partial |
| `too_hard` | Attempted, blocked; notes required | a note on the task, stays open, difficulty re-rated | small |
| `needs_records_request` | Requires FOIA/PRA | a pre-filled request draft + a 90-day parked task | full |
| `skip` | Not for me | nothing | none |

- **Review:** reviewer ≠ submitter, enforced. Reviewer sees the submitted evidence and a checklist mirroring the extraction-disclosure fields. Two review dispositions beyond accept/reject: `accept_with_downgrade` (the evidence is real but weaker than claimed — sets the support level and reason code) and `escalate` (needs a domain reviewer, e.g. anything touching §13 sensitive-data policy). **Target review latency: 72 hours; the queue publishes its actual median.**
- **Promotion rule:** for `contested` claim types, resolution requires either one Tier-A document or two independent reviewers agreeing — an explicit adaptation of iNaturalist's agreement threshold to SIG's evidence tiers.

### C.6.3 Geographic queues (Q36 — answered)

```
┌─ Geographic queues ────────────────────────────────────────────────────────┐
│ [ search a place ]                                    [ map ] [ list ]     │
│                                                                            │
│  ╔══════════════════════╗   Alameda County, CA                             │
│  ║ Alameda County, CA   ║   Claimed by: East Bay Privacy Coalition         │
│  ║ ▓▓▓▓▓▓▓▓░░░░  62%    ║   since 2026-03-04 · 6 contributors               │
│  ║ 41 open · 7 claimed  ║   Coverage 62% · median task age 9 days          │
│  ╚══════════════════════╝   Health: ● active (12 resolutions/30d)          │
│                             [ view queue ] [ contact stewards ]            │
│  ┌──────────────────────┐                                                  │
│  │ Contra Costa County  │   UNCLAIMED · 88 open tasks · coverage 11%       │
│  │ ░░░░░░░░░░░░  11%    │   [ Claim this queue for your group ]            │
│  └──────────────────────┘                                                  │
└────────────────────────────────────────────────────────────────────────────┘
```

Design of the claim: a group claims a **county or place GEOID**, gets a named public steward page, a queue-scoped RSS/iCal feed, and first-refusal (not exclusivity) on tasks in that geography — an unclaimed task in a claimed queue becomes globally available after 14 days idle. **Claiming confers no editorial control**: stewards cannot approve their own submissions, cannot block outside contributions, and cannot hide tasks. Stewardship lapses automatically after 90 days of zero activity, with two warnings. This directly answers Q36 while preserving the §18 principle that SIG coordinates rather than captures local work.

### C.6.4 Anti-burnout, anti-gamification-abuse

The MapRoulette point weighting (5/3/1) is the right instinct — reward correct triage, not throughput. SIG's version:

1. **No public leaderboard of totals.** Public recognition is per-contribution attribution on the entity pages plus a "recent resolutions" feed. Cumulative volume is visible only to the contributor themselves.
2. **Credit is weighted by outcome quality, and `searched_not_found` scores equal to `resolved`.** Any scheme that rewards positive findings over negative ones biases the corpus toward false positives — a fatal flaw for an accountability project.
3. **Review-accepted, not submitted, is the unit of credit.** Submitting 40 unreviewed tasks earns nothing until reviewed.
4. **Rate caps on self-review-adjacent behavior**, and a hard cap on how many tasks one person may hold open (default 5).
5. **Difficulty is community-rated** from `too_hard` outcomes, so hard tasks surface to experienced contributors instead of grinding down newcomers.
6. **Explicit rest affordances:** no streaks, no daily goals, no notification pressure. A "pause my queue" control that suppresses all outreach for a chosen period.
7. **Every task shows its own age and how many people bounced off it.** Tasks with 3+ `too_hard` outcomes are auto-escalated to a staff/expert lane rather than left to demoralize volunteers.
8. **Emotional-load routing:** tasks involving incident/litigation records may contain distressing content; those are labeled and opt-in, never surfaced in a "quick task" recommendation.

### C.6.5 URLs and states

```
/queue                                    recommended tasks (no account needed to browse)
/queue?place={geoid}&kind=contradiction&effort=lt30m&skill=desk
/queue/{task_id}                          one task, permalinked, publicly readable
/queue/geo                                geographic queue map
/queue/geo/{geoid}                        one geographic queue + steward page
/queue/stats                              public health: open, median age, review latency
```

- **Empty (a filter yields nothing):** "No open tasks match. Related: 12 tasks in adjacent counties. [ widen ]" — never "all done."
- **Empty (genuinely no tasks for a place):** "No open tasks here because nothing has been researched here. [ Start the first dossier ]".

## C.7 API / exports (§15.7)

### F10.13 — OpenAPI 3.1.1 (2024-10-24) aligns with JSON Schema 2020-12 and adds an SPDX `identifier` on the License Object

**Claim:** OpenAPI 3.1.1 inherits JSON Schema Draft 2020-12 parsing, adds `webhooks`, and lets the License Object carry an SPDX expression in `identifier`.
**Status:** VERIFIED
**Evidence:** `https://spec.openapis.org/oas/v3.1.1.html` — published 2024-10-24; "inherits the parsing requirements of JSON Schema Specification Draft 2020-12"; `webhooks` field; License Object `identifier` = "SPDX expression for the API."
**Retrieved:** 2026-08-20
**Implication for the spec:** Describe the API in OpenAPI 3.1.1 and reuse the *same* JSON Schema 2020-12 documents for API validation, bulk-export validation, and ingestion validation — one schema source, three consumers. Put the SPDX expression in `info.license.identifier`; for SIG that expression is not a single license (see F10.14), so the API-level identifier describes the *metadata* and per-record license fields carry the rest.
**Outline delta:** EXTENDS §15.7.

### F10.14 — Frictionless Data Package v2 (2026-05-05) expresses per-package licenses and sources as first-class arrays

**Claim:** The Data Package standard v2 requires `resources`, strongly recommends `name`/`id`/`licenses`/`profile`, and expresses `licenses` as an array of `{name (Open Definition id), path, title}` and `sources` as an array of `{title, path, email, version}`.
**Status:** VERIFIED
**Evidence:** `https://datapackage.org/standard/data-package/` — "v2 (current)", dated 2026-05-05; recommended profile `https://datapackage.org/profiles/2.0/datapackage.json`; `created` must be RFC3339; `id` reserved for globally unique identifiers "like UUIDs or DOIs."
**Retrieved:** 2026-08-20
**Implication for the spec:** Every bulk export ships a `datapackage.json` v2 descriptor. Because SIG's graph mixes ODbL-derived OSM physical assets with CC-BY material (§14), the `licenses` array is genuinely plural and the exports **must be split into separately-licensed resources** so a consumer can take the non-ODbL resource without triggering share-alike. That is Strategy A of §14.1 expressed as a file layout: `resources: [{name: "physical_assets_osm", licenses:[ODbL]}, {name: "organizations", licenses:[CC-BY-4.0]}, …]`.
**Outline delta:** EXTENDS §14.1 — supplies the concrete packaging mechanism for keeping OSM logically separable.

### F10.15 — DCAT 3 (W3C Recommendation, 2024-08-22) supplies the catalog vocabulary for discoverability

**Claim:** DCAT 3 defines Catalog, Dataset, Distribution, DataService, and DatasetSeries, with `dct:temporal`, `dct:spatial`, `dct:accrualPeriodicity`, and provenance links.
**Status:** VERIFIED
**Evidence:** `https://www.w3.org/TR/vocab-dcat-3/` — W3C Recommendation 22 August 2024; classes and temporal/spatial/periodicity properties as listed; `DatasetSeries` for "separately published but related datasets."
**Retrieved:** 2026-08-20
**Implication for the spec:** Publish `/data/catalog.jsonld` as a DCAT 3 Catalog; each dated bulk export is a `dcat:Dataset` in a `dcat:DatasetSeries`, which is exactly the right shape for "a snapshot you can cite." `dcat:accrualPeriodicity` publicly commits SIG to an update cadence — a trust signal and a falsifiable promise.
**Outline delta:** EXTENDS §15.7.

### C.7.1 Wireframe (docs + playground)

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ SIG API  v1 (stable)          [ Reference ] [ Playground ] [ Bulk ] [ Licensing ] │
├──────────────────┬────────────────────────────────────────────────────────────────┤
│ GETTING STARTED  │  GET /v1/orgs/{org_id}/claims                                  │
│ ▸ Quickstart     │  Returns every claim about an organization with full epistemic  │
│ ▸ Stable IDs     │  metadata. No key required. 60 req/min anonymous.               │
│ ▸ Epistemics ★   │                                                                │
│ ▸ Licensing ★    │  TRY IT                                                         │
│ ▸ Rate limits    │  org_id [ us-xx-example-city-pd    ]  as_of [ 2026-08-20 ]     │
│ ▸ Versioning     │  ☑ include competing_claims   ☑ include evidence               │
│ ENDPOINTS        │  [ Send ]                                                      │
│ ▸ /orgs          │  ┌──────────────────────────────────────────────────────────┐  │
│ ▸ /places        │  │ curl 'https://api.sig.org/v1/orgs/us-xx-example-city-pd/ │  │
│ ▸ /claims        │  │   claims?as_of=2026-08-20&include=competing,evidence'    │  │
│ ▸ /evidence      │  └──────────────────────────────────────────────────────────┘  │
│ ▸ /assets (ODbL) │  200 OK · 41 ms · 18.4 KB                                      │
│ ▸ /graph         │  X-SIG-Licence: mixed; see _licences                            │
│ ▸ /tasks         │  X-SIG-Snapshot: 2026-08-20T14:02:00Z                           │
│ ▸ /watch.ics     │  { "claims": [ { "value": 20, "epistemic": { … } } ] }          │
│ BULK             │                                                                │
│ ▸ Data packages  │  CITE THIS QUERY                                               │
│ ▸ PMTiles        │  Surveillance Infrastructure Graph, API v1, /orgs/…/claims,    │
│ ▸ Catalog (DCAT) │  retrieved 2026-08-20. https://api.sig.org/… [ copy BibTeX ]   │
└──────────────────┴────────────────────────────────────────────────────────────────┘
```

### C.7.2 Normative API rules

1. **Versioned in the path** (`/v1/`), with a published deprecation policy: 12 months' notice, a `Sunset` header, and a changelog feed.
2. **No key for read.** Anonymous 60 req/min per IP; free key 600 req/min; bulk downloads are unmetered and *preferred* — the docs actively steer heavy users to the dumps, because a crawler is worse for both sides than a 4 GB download.
3. **Rate-limit headers always present**: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`. A 429 body includes the bulk-download URL.
4. **`_licences` on every response**, per-record, plus the `X-SIG-Licence` header. Any response containing OSM-derived geometry is flagged `odbl-derived: true` at the record level so downstream code can strip it programmatically. This is §14.1 Strategy A enforced at the wire.
5. **`X-SIG-Snapshot`** on every response — the as-of time the response reflects, so a consumer can reproduce it.
6. **Stable IDs are permanent** (Q37). Merged entities return `301`-equivalent semantics: `{"moved_to": "sig:org/…", "reason": "duplicate merge", "merged_at": "…"}` with HTTP 200 plus a `Deprecation` header, never a silent redirect that hides the merge.
7. **Every list endpoint has a coverage envelope**: `{"coverage": {"documented": 13, "not_researched": 12, "searched_not_found": 2, "denominator_note": "…"}}`. A consumer must not be able to compute a national total without seeing the denominator caveat in the same payload.
8. **"Cite this"** on every endpoint and every bulk file, emitting BibTeX/APA/Chicago/RIS plus a `CITATION.cff` in the dump.

---

# Part D — The implementing stack (verified 2026-08-20)

## D.1 Verified versions and licenses

Every row was fetched today from the npm registry (`registry.npmjs.org`), the GitHub API via authenticated `gh`, or the project's own docs. Where the GitHub API reported `NOASSERTION`, the LICENSE file was read directly.

| Component | Version | Published | License | Verified via | Verdict |
|---|---|---|---|---|---|
| maplibre-gl | **6.4.1** | 2026-08-18 | BSD-3-Clause (LICENSE.txt read directly; GH API says NOASSERTION) | npm + `gh api repos/maplibre/maplibre-gl-js/releases` | **ADOPT** |
| pmtiles (JS) | **4.5.0** | 2026-08-10 | BSD-3-Clause | npm | ADOPT |
| PMTiles spec | **v3** | — | reference impls BSD-3; **spec itself public domain / CC0** | `repos/protomaps/PMTiles/contents/LICENSE` + spec/v3/spec.md | ADOPT |
| @protomaps/basemaps (styles) | **5.7.2** | 2026-03-10 | BSD-3-Clause | npm | ADOPT |
| protomaps-themes-base | 4.5.0 | 2025-02-17 | BSD-3-Clause | npm | **DEPRECATED** — npm flags it; use `@protomaps/basemaps` |
| Protomaps basemap build | **v4** daily | daily | **ODbL Produced Work, OSM attribution required** | docs.protomaps.com/basemaps/downloads | ADOPT (self-host) |
| tippecanoe (felt) | **2.79.0** | 2025-07-24 | BSD-2-Clause | `gh api repos/felt/tippecanoe/releases` | ADOPT |
| deck.gl | **9.3.10** | 2026-08-11 | MIT | npm | ADOPT (overlay only) |
| Next.js | **16.3.1** | 2026-08-13 | MIT | npm + nextjs.org docs header `version: 16.3.1` | fallback |
| Astro | **7.2.4** | 2026-08-19 | MIT | npm; 7.0 released 2026-06-22 | **ADOPT** |
| Svelte / SvelteKit | 5.56.9 / **2.70.3** | 2026-08-12 / 2026-08-18 | MIT | npm (kit `next` tag = 3.0.0-next.24) | viable, not chosen |
| react-router | **8.3.0** | 2026-07-22 | MIT | npm (v7 line at 7.18.2) | not chosen |
| sigma | **3.0.3** | 2026-04-30 | MIT | npm + GH | ADOPT |
| graphology | **0.26.0** | 2025-01-26 | MIT | npm | ADOPT |
| cytoscape | **3.34.1** | 2026-08-11 | MIT | npm + GH | ADOPT (small views) |
| d3-force | 3.0.0 | 2021-06-05 | ISC | npm | ADOPT (layout only) |
| @cosmograph/cosmograph | 2.5.1 | 2026-08-14 | **CC-BY-NC-4.0** | npm | **REJECT** |
| cosmograph-org/cosmos | — | — | MIT | GH | conditional fallback |
| @tanstack/react-table | **9.1.2** | 2026-08-09 | MIT | npm | **ADOPT** |
| ag-grid-community / -enterprise | 36.1.0 | 2026-08-05 | MIT / **Commercial ($999/dev)** | npm + ag-grid.com/license-pricing | REJECT enterprise |
| Datasette | **1.0a38** | 2026-08-06 | Apache-2.0 | GH releases + changelog | internal only (still alpha) |
| tailwindcss | **4.3.3** | 2026-07-16 | MIT | npm | ADOPT |
| @radix-ui/primitives | 1.1.23 (react-dialog) | 2026-07-24 | MIT | npm + GH | ADOPT |
| shadcn (CLI) | **4.18.0** | 2026-08-13 | MIT | npm + GH | ADOPT |
| react-aria-components | **1.20.0** | 2026-07-31 | Apache-2.0 | npm + GH (adobe/react-spectrum) | ADOPT selectively |
| @base-ui-components/react | 1.0.0-rc.0 | 2025-12-04 | MIT | npm | WAIT (still RC) |
| Typesense (server / client) | **30.2** / 3.0.6 | 2026-04-19 / 2026-04-21 | **GPL-3.0** / Apache-2.0 | GH repo metadata + npm | conditional |
| Meilisearch | **1.53.1** | 2026-08-13 | **`MIT AND BUSL-1.1`** | LICENSE + LICENSE-EE read directly | **CAUTION** |
| OpenSearch | — | 2026-08-20 (pushed) | Apache-2.0 | GH | overkill |
| @orama/orama | 3.1.18 | 2025-12-19 | Apache-2.0 (repo says NOASSERTION) | npm + GH | client-side only |
| PostgreSQL FTS | **18.6 docs** | — | PostgreSQL licence | postgresql.org/docs/18 | **ADOPT first** |
| WeasyPrint | **69.0** | 2026-06-02 | BSD-3-Clause | GH releases | ADOPT |
| pagedjs | 0.4.3 | **2023-07-06** | MIT | npm (repo pushed 2026-04-23) | REJECT for production |
| @turf/turf | 7.4.0 | 2026-08-03 | MIT | npm | ADOPT |

### F10.25/F10.26 — MapLibre GL JS v6 is current and is ESM-only, with several behavior changes that affect SIG directly

**Claim:** MapLibre GL JS 6.4.1 (2026-08-18) is the current release; v6 ships ES modules only, drops the UMD and CSP bundles, changes worker-URL handling, preserves nested GeoJSON properties as real objects, and slices rather than overscales vector tiles by default.
**Status:** VERIFIED
**Evidence:** npm `maplibre-gl` dist-tags `{latest: 6.4.1, v1: 1.15.3, next: 6.0.0-22}`, published 2026-08-18T13:38Z, license field `BSD-3-Clause`; `gh api repos/maplibre/maplibre-gl-js/releases` → v6.4.1 2026-08-18, v6.4.0 2026-08-16, v6.3.0 2026-08-10. `https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/`: "MapLibre GL JS v6 ships as ES modules only. The UMD bundle and the separate CSP build from v5 are gone"; bundle is `maplibre-gl.mjs`; default `import maplibregl from 'maplibre-gl'` no longer works; cross-origin CDN loading "requires `blob:` in `worker-src`"; "Nested objects and arrays in GeoJSON feature properties are now preserved" (remove `JSON.parse()`); "Vector tiles are now sliced instead of overscaled by default, affecting label rendering and `queryRenderedFeatures` results." Options verified on the MapOptions page: `keyboard` (default true, KeyboardHandler), `cooperativeGestures`, `reduceMotion`, `locale`.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The CSP story changed — SIG will run a strict CSP and must whitelist `blob:` in `worker-src` or self-host the worker; plan for this rather than discovering it in review. (b) `queryRenderedFeatures` behavior changed with tile slicing, which matters because SIG's "what is under the cursor / what is in this viewport" panel (C.2.4) depends on it. (c) Nested-property preservation is genuinely useful: a device feature can carry its whole `epistemic` object into the tile without stringify/parse. (d) `keyboard: true` and `reduceMotion` are the hooks for the WCAG work in D.6.
**Outline delta:** N/A (outline does not name a stack).

### F10.27/F10.28/F10.29 — PMTiles v3 + a self-hosted Protomaps v4 planet build is the cheap, correctly-attributed basemap

**Claim:** PMTiles v3 is a single-file pyramid readable by HTTP range requests with a 127-byte header and a root directory guaranteed within the first 16 KiB; Protomaps publishes daily ODbL "Produced Work" planet builds at ~120 GB (z0–15) and explicitly discourages hotlinking; OSMF requires visible "OpenStreetMap" credit linked to the copyright page on browsable maps.
**Status:** VERIFIED
**Evidence:**
- `https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md` — "The Header has a length of 127 bytes and is always at the start of the archive"; "The root directory MUST be contained in the first 16,384 bytes (16 KiB) so that latency-optimized clients can retrieve the root directory in advance"; compressions None/gzip/brotli/zstd; tile types MVT/PNG/JPEG/WebP/AVIF.
- `repos/protomaps/PMTiles/contents/LICENSE` — "The below license (BSD-3) applies to the reference implementations… The PMTiles specification itself is public domain, or CC0 where applicable."
- `https://docs.protomaps.com/basemaps/downloads` — "The Version 4 Protomaps basemap daily build channel is available at maps.protomaps.com/builds"; "A full planet file is roughly **120 gigabytes**, including zoom levels from 0 to 15"; "available as a single PMTiles archive, distributed as an Open Database License Produced Work (OpenStreetMap attribution required)"; "URLs may change and hotlinking to these downloads are discouraged. Instead, you should copy the tileset to your own Cloud Storage." AWS mirror via Source Cooperative `protomaps/openstreetmap`.
- `https://osmfoundation.org/wiki/Licence/Attribution_Guidelines` — credit "OpenStreetMap," indicate ODbL, ideally link to openstreetmap.org/copyright; "For a browsable map… the credit should typically appear in a corner of the map"; collapsing is permitted only with a dismiss interaction, on map interaction, or automatically after five seconds, and the license must remain reachable.
- Alternatives priced: Stadia Maps free tier 200,000 credits/mo, **commercial use not allowed**; Starter $20/mo for 1M credits (+3¢/1k); Standard $80/mo 7.5M; Professional $250/mo 25M; vector basemap = 1 credit/tile. MapTiler free = 5,000 map sessions + 100,000 API requests/mo with a required MapTiler logo; Flex $30/mo = 25k sessions + 500k requests, overage $2.50/1k sessions.
**Retrieved:** 2026-08-20
**Implication for the spec:** Self-host. A 120 GB PMTiles archive on S3-class storage costs on the order of $3/mo plus egress, versus $20–250/mo for a hosted vector basemap whose free tier forbids commercial use (Stadia) or brands the map (MapTiler). More importantly, self-hosting removes a third-party availability and privacy dependency: SIG's users must not have their map viewport reported to a vendor. Cut a **z0–12 regional extract** (a few GB) for the default view and range-request the full planet only for deep zooms. Attribution renders permanently, uncollapsed, bottom-right, linked to openstreetmap.org/copyright. **Do not hotlink `maps.protomaps.com/builds`** — Protomaps says so explicitly.
**Outline delta:** EXTENDS §14.1 — an ODbL "Produced Work" basemap is separable from SIG's own data layer, which is the map-tier expression of Strategy A.

### F10.30/F10.31/F10.32 — Framework: choose Astro; the static-export and islands facts

**Claim:** Next.js 16's `output: 'export'` forbids a specific, verified list of features; Astro strips all client JS by default and requires explicit `client:*` directives; SvelteKit's `prerender`/`ssr`/`csr` page options give equivalent control at a per-route granularity.
**Status:** VERIFIED
**Evidence:**
- `https://nextjs.org/docs/app/guides/static-exports` (page metadata: `version: 16.3.1`, `lastUpdated: 2026-08-09`). Unsupported under `output: 'export'`: dynamic routes with `dynamicParams: true`; dynamic routes without `generateStaticParams()`; Route Handlers that rely on `Request`; Cookies; Rewrites; Redirects; Headers; Proxy; ISR; Image Optimization with the default loader; Draft Mode; Server Actions; Intercepting Routes. Route Handlers export static responses, GET only, and require `export const dynamic = 'force-static'`.
- `https://docs.astro.build/en/concepts/islands/` — "By default, Astro will automatically render every UI component to just HTML & CSS, **stripping out all client-side JavaScript automatically**"; directives `client:load`, `client:idle`, `client:visible`; `server:defer` for server islands so "the outer shell and main content [can] be more aggressively cached."
- `https://astro.build/blog/astro-7/` — Astro 7.0 released **2026-06-22**; Rust `.astro` compiler; Vite 8 + Rolldown; build times 15–61% faster; breaking: the compiler no longer silently corrects invalid markup, JSX-style strictness and whitespace collapsing.
- `https://svelte.dev/docs/kit/page-options` — `prerender` (`true` / `'auto'`), `ssr: false` renders an empty shell and is "not recommended," `csr: false` ships no JS; "For a page to be prerenderable, any two users hitting it directly must get the same content from the server"; `adapter-static` for fully-prerendered apps.
**Retrieved:** 2026-08-20
**Implication for the spec — the decision and the argument:**

**Recommendation: Astro 7.x, decisively.** Reasoning:

1. **The no-JS requirement is a product requirement, not a nicety, and only Astro's default enforces it.** SIG pages are cited in court filings, council packets, academic papers, and web archives. `web.archive.org` and Perma.cc capture HTML far more reliably than they replay hydration. A dossier that renders blank in a 2031 archive replay has failed at the project's stated purpose ("make the final system reproducible enough that a journalist can defend a graph claim"). Astro's zero-JS default means the failure mode is *inverted*: a developer must take an explicit action (`client:load`) to break archivability, and that action is greppable in review. In Next.js and SvelteKit the default is hydration and the discipline must be maintained by vigilance. Over a five-year project with rotating contributors, defaults win.
2. **The content is ~95% static, ~5% interactive.** Dossiers, evidence pages, methodology, corrections, and claim pages are content. The map, the graph, the playground, and the queue are islands. This is precisely the island architecture's target shape.
3. **SEO/permanence.** Every dossier is a landing page for `"<city> surveillance"` searches — P1, P3, and P6 all arrive that way. Full server-rendered HTML with correct `ClaimReview` JSON-LD (F10.7) is the requirement; Astro emits it at build time with no runtime cost.
4. **Archivability as a build target.** Astro can produce a fully static build of the entire site at a given `as_of` — literally "the site as of 2026-08-20" as a directory of HTML — which is the cheapest possible implementation of the permanence promise, and which SIG can deposit with a library or an archive annually.
5. **Framework-agnostic islands** let SIG use React for deck.gl/TanStack islands, and plain TS for the Sigma island, without committing the whole site to one runtime.
6. **The cost:** Astro's server-side story is thinner than Next's, and Astro 7's compiler strictness will surface latent markup bugs on migration. Both are acceptable. Deploy with a Node adapter so the ~5% of genuinely dynamic routes (`?as_of=` reconstruction, `/queue` mutations, the API) are SSR, and `prerender` everything else.

**If the team is React-only and this is non-negotiable:** Next.js 16 App Router with RSC, hosted SSR for the live site, plus a *separate* `output: 'export'` archive build. The verified unsupported list is compatible with an archive build (no cookies, no server actions, no rewrites in that build), but it means maintaining two configurations forever. That is the cost of the second-best choice.

**SvelteKit** is a fine third option and its per-route `csr: false` is the closest analogue to Astro's default; it loses on ecosystem breadth for deck.gl/TanStack and on the framework-agnostic-islands property.

**React Router 8.3.0** (formerly Remix) is a capable framework but offers no advantage here over the two above for a content-dominant site, and its rapid major-version cadence (7.x → 8.x within roughly a year) is a maintenance risk for a project that must still build in 2031.
**Outline delta:** N/A (new).

### F10.33/F10.34 — deck.gl 9.3 interoperates with MapLibre via MapboxOverlay; interleaved mode needs WebGL2

**Claim:** deck.gl's `MapboxOverlay` supports overlaid and interleaved modes; interleaved shares the base map's `WebGL2RenderingContext` and is not supported against WebGL1-only basemaps.
**Status:** PARTIALLY VERIFIED
**Evidence:** `https://deck.gl/docs/api-reference/mapbox/mapbox-overlay` — interleaved mode: "Deck.gl layers are inserted into mapbox-gl's layer stack, and share the same `WebGL2RenderingContext` as the base map"; "interleaving with basemaps such as mapbox-gl-js v1 that only support WebGL 1 is not supported"; references MapLibre's `pixelRatio` constructor option; ordering via `beforeId`/`slot`. The docs site reports version **9.3**; npm `deck.gl` latest **9.3.10** (2026-08-11, MIT). The page does **not** state a supported maplibre-gl version range — that is the unverified part.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use `MapboxOverlay` with `interleaved: true` so SIG's dynamic selection/arc layers sit correctly beneath labels rather than obscuring them, and pin both `deck.gl` and `maplibre-gl` versions in CI with a visual-regression test, since the compatibility matrix is not documented. Keep deck.gl **out** of the static asset layer — that is tippecanoe/PMTiles' job (C.2.1).
**Outline delta:** N/A.

### F10.35 — H3 resolution table (for the density-bin thresholds in C.2.1)

**Claim:** H3 average hexagon areas: r5 ≈ 252.90 km², r6 ≈ 36.13 km², r7 ≈ 5.16 km², r8 ≈ 0.74 km², r9 ≈ 0.11 km², r10 ≈ 0.015 km².
**Status:** VERIFIED
**Evidence:** `https://h3geo.org/docs/core-library/restable/` — r5 2,016,842 cells / 252.90 km² / 9.85 km edge; r6 14,117,882 / 36.13 / 3.72; r7 98,825,162 / 5.16 / 1.41; r8 691,776,122 / 0.74 / 0.53; r9 4,842,432,842 / 0.11 / 0.20; r10 33,897,029,882 / 0.015 / 0.076.
**Retrieved:** 2026-08-20
**Implication for the spec:** r5 (≈253 km², roughly a small county fragment) is the right national bin; r7 (≈5 km², roughly a neighborhood cluster) is the right metro bin. Below r8 the bin is smaller than the positional uncertainty of much of SIG's data and binning stops being honest — that is the point where the UI must switch to individual, individually-sourced assets.
**Outline delta:** N/A.

### F10.36–F10.38 — Graph and grid licensing traps

Covered in F10.10 (Cosmograph CC-BY-NC-4.0) and the D.1 table (AG Grid Enterprise $999/dev, verified at `https://www.ag-grid.com/license-pricing/`; Community is MIT). **Recommendation:** TanStack Table 9.1.2 headless + SIG's own cell renderers, because SIG's cells are not generic — every cell must be able to render a support badge, a conflict rule, a hatched absence slot, and an expander. A pre-styled grid fights that. Datasette 1.0a38 remains valuable as an *internal* exploratory surface over the raw extraction database (its facet mechanics are excellent — suggested facets appear when a column has ≤30 unique values, >1 value, fewer uniques than rows, and the query completes in 50 ms; `?_facet=col`, `default_facet_size` 30, `?_facet_size=100`), but it is still an alpha (1.0a38, 2026-08-06) and must not be a public surface.

### F10.41/F10.42/F10.43 — Search: start with Postgres, and know the license traps

**Claim:** PostgreSQL 18 FTS provides `tsvector`/`tsquery`, phrase operators, GIN/GiST indexes, and ranking, but no built-in typo tolerance or fuzzy matching; Typesense's server is GPL-3.0; Meilisearch is now dual `MIT AND BUSL-1.1` with enterprise modules under a four-year-delayed BUSL.
**Status:** VERIFIED
**Evidence:** `https://www.postgresql.org/docs/18/textsearch-intro.html` (doc version 18.6) — `tsvector`/`tsquery`, `@@`, `<->` FOLLOWED BY, `phraseto_tsquery`, GIN/GiST references; "No built-in typo tolerance or fuzzy matching." `gh api repos/typesense/typesense` → `license: GPL-3.0`, latest release v30.2 (2026-04-19); npm client `typesense` 3.0.6 Apache-2.0. `repos/meilisearch/meilisearch/contents/LICENSE` read directly: "Part of this work fall under the Meilisearch Enterprise Edition (EE) and are licensed under the Business Source License 1.1… The other parts of this work are licensed under the MIT license. `SPDX-License-Identifier: MIT AND BUSL-1.1`"; LICENSE-EE: "Licensed Work: Any file explicitly marked as 'Enterprise Edition (EE)'… residing in enterprise_editions modules/folders"; "Production use of the Licensed Work requires a commercial license agreement"; Change License MIT, Change Date four years.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Start with Postgres 18 FTS.** SIG already needs Postgres/PostGIS for the graph and bitemporal store; a second search service is a second thing to run, back up, and re-index. Postgres FTS covers entity search (names are mostly exact-ish), document full-text over extracted text, and faceting via ordinary SQL. Add `pg_trgm` for the fuzzy-name cases, which is the one real gap. **Only** if measured search quality demands typo tolerance at scale should SIG add Typesense — and if it does, note that Typesense's server is GPL-3.0, which is fine for a self-hosted, separately-deployed service but must not be linked into SIG's own code. **Avoid Meilisearch** as the default: a BUSL component inside the search engine of a transparency project is exactly the kind of governance surprise the project should not sign up for, even though the MIT core would probably suffice. Orama (Apache-2.0) is a good *client-side* index for the docs site and the API reference, shipped as a static JSON index — no server at all.
**Outline delta:** N/A.

### F10.44/F10.45/F10.46 — Print, theming, packaging

- **WeasyPrint 69.0** (2026-06-02, BSD-3-Clause, `gh api repos/Kozea/WeasyPrint`) for server-side PDF. **Paged.js**'s npm release is **0.4.3 from 2023-07-06** despite repo activity through 2026-04-23 — a stale published artifact is a production risk, so Paged.js is rejected for the council-packet path (it remains fine for design prototyping). VERIFIED.
- **`color-scheme` is Baseline "widely available" since January 2022**; `light-dark()` is the modern compaction (`https://developer.mozilla.org/en-US/docs/Web/CSS/color-scheme`). VERIFIED. SIG still writes the three-block pattern in B.3.2 because the explicit theme toggle must win in both directions.
- **Data Package v2 / DCAT 3 / OpenAPI 3.1.1** per F10.13–F10.15.

## D.2 Typography and layout for dense evidence pages

- **Body/prose:** a text face with real small caps, true old-style *and* lining figures, and a large x-height. Recommended: **Source Serif 4** (SIL OFL) for dossier prose at 17px/1.65, **Inter** or **Source Sans 3** (SIL OFL) for UI chrome at 14–15px. Both are self-hosted WOFF2 subsets — no third-party font CDN, for the same privacy reason as the basemap.
- **Numbers are the content.** All numerals in tables and badges use `font-variant-numeric: tabular-nums lining-nums`. Dates are always ISO-8601 in machine contexts and `2026-08-04` in tables; long-form dates only in prose.
- **Excerpts and document text:** a monospace or a distinctly different serif, always inside a bordered block with the source line beneath it, so a verbatim quotation is never visually confusable with SIG's own words. This is an editorial requirement expressed typographically (Part E).
- **Measure:** 62–72 characters for prose; tables are full-width and scroll horizontally inside their own `overflow-x: auto` container so the page body never scrolls horizontally (SC 1.4.10).
- **Density:** 8px spacing grid; table rows 40px minimum (satisfies SC 2.5.8 with room to spare); expanders never reflow content above them.

## D.3 Performance budgets (enforced in CI, build fails on regression)

| Route class | HTML | CSS | JS (initial) | LCP (p75, mid-tier mobile, 4G) | Notes |
|---|---|---|---|---|---|
| Dossier `/org/{id}` | ≤ 120 KB gz | ≤ 18 KB | **≤ 0 KB required**, ≤ 35 KB with islands | ≤ 1.8 s | Must be fully readable with JS blocked |
| Claim / evidence page | ≤ 80 KB | ≤ 18 KB | ≤ 15 KB | ≤ 1.5 s | Page images lazy, `loading="lazy"` |
| Map `/map` | ≤ 40 KB | ≤ 20 KB | ≤ 260 KB (maplibre + deck islands, code-split) | ≤ 3.0 s to first tiles | Budget excludes tiles |
| Graph `/graph/{id}` | ≤ 60 KB | ≤ 20 KB | ≤ 180 KB (sigma + graphology) | ≤ 2.5 s | Edge table renders first, always |
| Queue, API docs | ≤ 60 KB | ≤ 18 KB | ≤ 40 KB | ≤ 1.8 s | |

Additional hard rules: no web font blocks first paint (`font-display: swap` + a metric-matched fallback); no third-party requests of any kind on any page (no analytics CDN, no font CDN, no map vendor); CLS ≤ 0.02 (badges and hatch slots reserve their space); INP ≤ 200 ms.

## D.4 i18n readiness

Not a v1 feature; v1 must not preclude it. Concretely: all UI strings in message catalogs from day one (no string literals in components); ICU MessageFormat for plurals, because "1 source" / "4 sources" appears constantly; `lang` and `dir` on `<html>` driven by a route segment (`/es/org/…`) reserved now; no text baked into images or map sprites; dates rendered with `Intl.DateTimeFormat` and always accompanied by the ISO form; the **epistemic vocabulary is a translation-critical surface** — the four axes' labels must be translated by a domain-competent translator with the glosses, not a string list, because "probable" and "contested" carry precise meanings. Spanish first (largest US non-English population); the Technopolice connection (§5.2) makes French the likely second.

## D.5 Accessibility: WCAG 2.2 Level AA as a hard requirement

### F10.24 — WCAG 2.2 is a W3C Recommendation dated 2024-12-12; the AA criteria SIG must meet, with numbers

**Claim:** WCAG 2.2 became a W3C Recommendation on 12 December 2024; the AA criteria most load-bearing for SIG are 1.4.1, 1.4.3 (4.5:1 / 3:1 large), 1.4.10 (reflow at 320 CSS px), 1.4.11 (3:1 non-text), 1.4.12, 2.1.1, 2.4.7, 2.4.11 (new), 2.5.7 (new), 2.5.8 (new, 24×24 CSS px), 3.3.7 (new), 3.3.8 (new).
**Status:** VERIFIED
**Evidence:** `https://www.w3.org/TR/WCAG22/` — Recommendation 12 December 2024. 1.4.1 "Color is not used as the only visual means of conveying information"; 1.4.3 "a contrast ratio of at least 4.5:1", 3:1 for large text; 1.4.10 reflow without loss at 320 CSS px width / 256 CSS px height; 1.4.11 "a contrast ratio of at least 3:1 against adjacent color(s)" for UI components and graphical objects; 1.4.12 text spacing (line height 1.5×, paragraph 2×, letter 0.12×, word 0.16×); 2.1.1 "All functionality of the content is operable through a keyboard interface"; 2.4.7 focus visible; 2.4.11 Focus Not Obscured (Minimum) — focus not entirely hidden by author content; 2.5.7 Dragging Movements — draggable functionality must have a single-pointer non-path alternative unless dragging is essential; 2.5.8 Target Size (Minimum) 24×24 CSS px; 3.3.7 Redundant Entry; 3.3.8 Accessible Authentication (Minimum). Supplemented by `https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html`: "The term 'graphical object' applies to stand-alone icons such as a print icon (with no text), and the important parts of a more complex diagram such as each line in a graph"; inactive components and essential presentations are exempt. And `https://www.w3.org/WAI/tutorials/images/complex/`: "a two-part text alternative is required. The first part is the short description to identify the image and, where appropriate, indicate the location of the long description. The second part is the long description," with three techniques — adjacent link, `<figure>`/`<figcaption>` structural association, and location reference in `alt`; "Make long descriptions available to everyone to reach a wider audience with your content."
**Retrieved:** 2026-08-20
**Implication for the spec:** The concrete obligations below.

### D.5.1 Concrete obligations

**Maps (the hard case):**
- **SC 1.1.1 + WAI complex-images guidance:** a map is a complex image and requires a two-part alternative. SIG's long description is not a paragraph — it is **the tabular equivalent**, which must be (a) on the same page or one adjacent link away, (b) available to everyone, not hidden behind a screen-reader-only class, and (c) exhaustive of the map's current filter state. This is why `/map/table` is a real, linked, shareable route and why the "In view / Not on map" panel is permanent rather than a fallback.
- **SC 2.1.1 Keyboard:** MapLibre's `keyboard` handler (default `true`, F10.26) gives pan/zoom/rotate. It does **not** give feature traversal. SIG must add: `Tab` into the map container, then `[` / `]` to step through features in the current viewport in a stable order (north-to-south, then west-to-east), `Enter` to open the feature panel, `Esc` to exit the map. Announce each focused feature via `aria-live="polite"`.
- **SC 2.5.7 Dragging Movements:** panning is dragging. Provide `+`/`−` buttons, arrow-key panning, and a "jump to place" search — all single-pointer, none path-based. Drawing a bounding-box filter must have a non-drag alternative (a place picker or numeric bounds inputs).
- **SC 2.5.8 Target Size:** map markers are targets. At z ≥ 13 markers get a 24×24 invisible hit area even though the visible dot is 5–10px. Where markers cluster below 24px apart, the cluster is the target, not the individual marker.
- **SC 1.4.1 Use of Color:** satisfied by C.2.2's shape-based status encoding (filled/hollow/cross/hatch) — the map is fully readable in grayscale, and a grayscale rendering test is in CI.
- **SC 1.4.11:** every map glyph verified ≥3:1 against the basemap paper (B.3.2 computed values); the white halo on dark dots guarantees it against arbitrary imagery.
- **`prefers-reduced-motion`:** map fly-to animations become instant jumps; MapLibre's `reduceMotion` option is set from the media query.

**Graphs:**
- The **edge table is the primary representation**; the node-link view is the enhancement. `/graph/{id}/table` is a real route (SC 1.1.1).
- Full keyboard traversal per C.3.4, with an `aria-live` region announcing focus changes and expansion results ("expanded, 147 nodes added").
- Node identity never encoded by color alone — shape + label + the table (SC 1.4.1).
- Force-layout animation is suppressed under `prefers-reduced-motion`; the layout is computed and then painted once.
- SC 2.5.7: node dragging must not be the only way to do anything.

**Color encoding, product-wide:**
- Every epistemic state has a **glyph + a word**, never color alone (SC 1.4.1). The acceptance test is a CI screenshot run through a grayscale filter and a deuteranopia/protanopia/tritanopia simulation; any state pair that becomes indistinguishable fails the build.
- All text pairs ≥4.5:1, all borders/glyphs/focus rings ≥3:1, verified by the computed table in B.3.2. `--ink-300` (1.48:1) is lint-banned from any meaningful role; `#475569` is lint-banned as a dark-theme border (2.47:1).
- **SC 2.4.11 Focus Not Obscured:** sticky headers, the map legend, and the evidence drawer must never fully cover a focused element; `scroll-margin-top` on all focusable elements equal to the sticky header height.
- **SC 1.4.10 Reflow:** the entire site works at 320 CSS px with no horizontal page scroll; wide tables scroll inside their own container.
- **SC 1.4.12 Text Spacing:** no fixed-height containers around text; badges use padding, not height.
- **SC 3.3.7 / 3.3.8:** contributor sign-in offers a passwordless email link and does not require a cognitive puzzle; no CAPTCHA on any read path, and on the correction form a non-cognitive alternative is offered.
- **SC 2.4.7 Focus Visible:** a 2px `--link`/`--focus` ring with a 2px offset, verified 6.70:1 (light) and 10.38:1 (dark).

**Testing commitment:** axe-core in CI on a representative page of each of the seven surfaces; manual NVDA+Firefox and VoiceOver+Safari passes on the dossier, map, and queue before each release; a published accessibility statement naming the conformance target (WCAG 2.2 AA), the known gaps, and a contact.

---

# Part E — Trust and voice

## E.1 Tone rules (the hostile-reader test)

The test: **a police chief or a vendor's counsel reads their own dossier.** If they can point at one sentence and say "that's activist spin," the page has lost every other reader too. Rules:

1. **Attribute, don't assert.** Not "the department shares data with ICE." Instead: "The department's transparency portal listed an organization identified as [X] among 147 configured sharing partners on 2026-08-04." The subject of the sentence is the *source*, not the agency.
2. **Never use an evaluative adjective about a subject.** No "sprawling," "invasive," "secretive," "aggressive," "massive." Numbers and dates carry the weight. Readers do the evaluating.
3. **Distinguish allegation from finding, always, structurally.** An allegation is something *someone else asserted* — a lawsuit, a complaint, a news report. A finding is what SIG's evidence supports. They render in different components with different labels, and an allegation always names its alleger and its status.
4. **Never characterize intent or motive.** SIG documents configurations, contracts, and events. It does not say why.
5. **Name the limits in the same breath as the number.** "20 devices (portal, 2026-08-04; three other sources say 18, 22, and 25)."
6. **No collective nouns as actors.** Not "police are expanding surveillance." Name the specific organization, or don't say it.
7. **Prefer the passive-voiceless past tense of documents.** "The contract states…" "The portal reported…" "The council approved…"
8. **Corrections are stated plainly and without defensiveness.** No "we regret." State what was wrong, what it is now, and why it changed.
9. **Ban the word "found" for anything derived.** SIG "found" a document. SIG "derived," "reconciled," or "estimated" a number.
10. **Never editorialize through design.** No red for "bad," no green for "good," no alarm icons on deployments (B.3.1). The amber `≠` means *sources disagree*, not *this is alarming*, and its tooltip says so.

## E.2 The mandatory "How we know this" module

Present on every entity page, every claim page, and page 4 of every PDF. Fixed fields, no free text at the top level: artifact count by tier; source-family independence count; date range and median age of evidence; reconciliation rules applied, each linked to its published definition; human-review status ("N of M numeric claims reviewed by a person"); extraction methods used, including whether any were LLM-assisted; the licensing mix; and the coverage counts. It is a **structured disclosure**, not a prose statement, because prose can be shaded and a field count cannot.

## E.3 The methodology page

`/methodology` is a first-class, permalinked, versioned document with: the source tier definitions (§9.1) with examples; the four epistemic axes and their derivation rules, including the hard rules R1–R4 (B.2.1); every reconciliation rule with its id, logic, and rationale; the staleness horizons and how they were chosen; the entity-resolution method and its known failure modes, explicitly including the §19.6 caveat; the publication policy for sensitive locations (§13.3) and documents (§13.4); the correction and dispute process; and a changelog. Rules are cited by id from every page that applies them (`rule R-CNT-03`), so a hostile reader can check whether the rule was applied consistently elsewhere — which is the strongest available proof of good faith.

## E.4 The corrections log as a public page

`/corrections` — reverse-chronological, permanently addressable per entry, with an RSS feed and a per-entity filter. Three tiers adapted from PolitiFact (F10.8):

| Tier | Trigger | Remedy |
|---|---|---|
| **1 — Material** | A support level, a reconciled value, an entity identity, or a date changed | Notice at the top of the affected page for 90 days; link to the prior snapshot (`?as_of=`); entry in `/corrections`; notification to entity subscribers; the API's `history` endpoint records it |
| **2 — Factual, non-material** | A fact changed without changing the reconciled value or level | Note at the bottom of the page; entry in `/corrections` |
| **3 — Cosmetic** | Typo, formatting, broken link | Fixed silently; still in the git history, which is public |

Every entry states: what was wrong, what it now says, how SIG learned of it, who raised it (if they consent to be named), when it was fixed, and the affected claim ids. **SIG publishes its own correction rate** on `/corrections` — total corrections by tier per quarter, against total published claims. A project that hides its error rate is asking to be trusted; a project that publishes it is giving readers the means to calibrate.

## E.5 The dispute process

Distinct from a correction. A **dispute** is a subject (or anyone) asserting that a claim is wrong without yet supplying evidence that settles it. `[ Dispute this ]` on any claim creates a public dispute record with a stable id. The claim then renders with a `⊘ disputed` marker linking to the record. Disputes are answered within 10 business days with one of: correction issued; claim upheld with reasoning; claim downgraded pending evidence; claim retracted. **The subject's statement is published verbatim alongside SIG's response**, whether or not SIG agrees. This costs nothing and is the single most effective defense against the "they never gave us a chance to respond" attack.

## E.6 The snapshot/citation affordance

Every page carries, in the header and the print footer: `Snapshot as of 2026-08-20 14:02 UTC · Permalink: …?as_of=2026-08-20 · [ Cite this page ]`. The citation block offers BibTeX, APA, Chicago, and RIS, each including the as-of date and the retrieval date. The exact copy: **"This page is a snapshot. Facts here reflect the evidence SIG held on 2026-08-20. Cite it with that date. Later evidence may change these values; the permalink above will always show this snapshot."**

## E.7 Example copy for three tricky cases

### Case 1 — An agency's own portal contradicts its own written policy (retention 30 vs 365 days)

> **Retention period** ┃ ≠2 sources disagree
> **30 days** — City of Example Police Department, *ALPR Policy 421.6*, adopted 2024-11-02, §4.3. [document, p.4]
> **365 days** — Flock Safety transparency portal for Example City PD, field "Data retention," as observed by SIG on 2026-08-04. [snapshot, WARC]
>
> SIG has not reconciled these. A written policy states an intended rule; a vendor portal reports a system configuration. They can differ without either being false — a policy may not have been applied to the system, the portal may report a vendor default, or the policy may have been superseded. SIG has an open request to the department to clarify the configured value (task T-8814, opened 2026-08-04). Until that is answered, SIG shows both numbers and asserts neither.
> *Confidence: probable (⊕⊕◯◯) for each individual figure. Contested.*

### Case 2 — A vendor sends a lawyer's letter asserting the dossier is defamatory

Published verbatim on `/corrections/d-0112` and linked from the affected claims:

> **Dispute D-0112 — Vendor Inc., received 2026-07-11**
> Vendor Inc.'s counsel states that SIG's page for [Agency] "falsely implies that Vendor's system transmits data to federal agencies." The full letter is reproduced here: [PDF].
>
> **SIG's response, 2026-07-19.** SIG's page did not state that Vendor's system transmits data to federal agencies. It stated: "The agency's transparency portal listed 3 organizations with federal ORI prefixes among 147 configured sharing partners, as observed 2026-06-02." That statement describes what a portal operated by Vendor reported about a configuration, on a date. SIG has re-checked the underlying snapshot [WARC w_0c19, sha 3e8c…] and confirms the page matches it.
>
> SIG has made one change in response: the sentence now reads "…listed 3 organizations whose names match federal agency identifiers…" because SIG's ORI matching for those three entries is ⊕⊕◯◯ probable, not confirmed, and the previous wording implied more identity certainty than the evidence supports. That is a Tier-1 correction; see C-0431.
>
> SIG has not removed the claim. Vendor Inc. has not supplied evidence that the portal reported otherwise on that date. If it does, SIG will publish it and correct accordingly.

*(Note the structure: reproduce the complaint, quote SIG's actual words, re-verify against the artifact, concede precisely what is conceded and no more, state exactly what would change SIG's mind.)*

### Case 3 — Absence of evidence being read as evidence of absence, in a neighboring town

> **Neighboring Township — no documented surveillance technologies**
>
> ░ **SIG has not researched this jurisdiction.** This page exists because Neighboring Township appears in a Census place file, not because SIG examined it. Nothing on this page should be read as evidence that Neighboring Township operates no surveillance technology.
>
> What SIG *has* done: nothing. What SIG *has not* done: searched the township's procurement records, agenda archives, or any vendor transparency portal; checked OpenStreetMap for mapped devices; checked EFF's Atlas of Surveillance.
>
> By contrast, on the [neighboring city's page] you will see "⌀ No evidence found — searched 2026-07-14," which *does* mean something: it records that SIG ran a named procedure on a named date and found nothing. That is a much stronger statement than this page makes, and it is still not proof of absence.
>
> [ Be the first to research this jurisdiction — 27 open fields ]

---

# Appendix R10-A — Remaining verified findings (F10.16–F10.23, F10.39, F10.40)

*(Finding numbers in this file are grouped by topic, so the sequence is not contiguous in reading order; every number F10.1–F10.46 is defined exactly once.)*

### F10.16 — OCCRP Aleph is the closest existing "investigative entity graph with documents" product; its docs root 403s to WebFetch
**Claim:** Aleph provides document storage, OCR, cross-referencing against many databases, entity network mapping, and timelines, with separate user and developer documentation tracks.
**Status:** PARTIALLY VERIFIED / INACCESSIBLE (deep docs)
**Evidence:** `https://docs.aleph.occrp.org/` returned usable content describing the platform ("help investigative journalists track people and companies"; discover patterns; securely store documents; convert scans to searchable text; map entity relationships; match names against hundreds of databases; build timelines). The FollowTheMoney ontology explorer at `https://followthemoney.tech/explorer/` returned **404** — the FtM schema list could not be verified today; version and license of Aleph were not stated on the page fetched.
**Retrieved:** 2026-08-20
**Implication for the spec:** Two UX borrowings are safe: (a) cross-reference-as-a-first-class-view (SIG's "this organization also appears in N other datasets"), and (b) the document-plus-entity split pane, which SIG's evidence viewer (C.5) mirrors. **Do not** assume FtM compatibility without a separate verification pass; R-workstreams covering the data model should re-check `followthemoney.tech` and the `alephdata/followthemoney` repo.
**Outline delta:** N/A.

### F10.17 — Our World in Data's metadata is organized around snapshot/garden-stage YAML with explicit licenses and processing level, but the field reference was not reachable in one hop
**Claim:** OWID attaches metadata at multiple pipeline stages (snapshots, datasets, tables, indicators) as YAML alongside processing code, and requires licenses, descriptions, and titles on every ingested source.
**Status:** PARTIALLY VERIFIED
**Evidence:** `https://docs.owid.io/projects/etl/architecture/metadata/` — "various data objects (snapshots, datasets that contain tables with indicators, etc.), each of them with different types of metadata"; "The most standard places to have metadata defined are in Snapshot and in Garden"; snapshot stage ensures sources "have licenses, descriptions, titles and other information assigned." The per-field reference (and therefore the exact names behind the public "Sources and processing" tab) was one level deeper and not fetched.
**Retrieved:** 2026-08-20
**Implication for the spec:** The transferable idea is **stage-tagged provenance**: SIG should record metadata separately at snapshot (raw artifact), extraction, normalization, and reconciliation stages, and the UI's "how we know this" module should be able to show which stage introduced a given transformation. This is §24's directive 9 ("separate raw evidence, extracted claims, normalized claims, and derived conclusions") expressed as a UI capability.
**Outline delta:** EXTENDS §24.9 with a UI obligation.

### F10.18 — Datasette's facet mechanics are a good model for SIG's filter UI, including the honesty of *suggested* facets
**Claim:** Datasette requests facets via `?_facet=COLUMN`, suggests facets only when a column has ≤30 unique values, >1 unique value, fewer uniques than filtered rows, and the suggestion query completes within 50 ms; default facet size 30, raisable to 100 via `?_facet_size=`.
**Status:** VERIFIED
**Evidence:** `https://docs.datasette.io/en/stable/facets.html`; version status from `https://docs.datasette.io/en/latest/changelog.html` (latest 1.0a38, 2026-08-06, still alpha; 1.0a38 fixes a SQL-injection issue affecting instances mixing public and private tables).
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt the URL grammar (`?facet=` / `?facet_size=`), and adopt the *self-limiting* behavior: SIG should not offer a facet whose computation is slow or whose cardinality makes it useless. Adopt also the practice of showing facet **counts** next to every option, since a facet count is a coverage statement in disguise. Do not expose Datasette publicly while it is alpha and while it has a recent injection CVE class in the mixed-visibility configuration SIG would need.
**Outline delta:** N/A.

### F10.19 — MapLibre exposes `reduceMotion`, `locale`, and `cooperativeGestures`, which are the hooks for three separate a11y/i18n requirements
**Claim:** MapOptions includes `keyboard` (default true), `cooperativeGestures`, `reduceMotion` (respects the device setting when undefined), and `locale` for UI-text translation.
**Status:** VERIFIED
**Evidence:** `https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/MapOptions/`.
**Retrieved:** 2026-08-20
**Implication for the spec:** `reduceMotion` satisfies the reduced-motion obligation without custom code; `locale` is the i18n hook named in D.4; `cooperativeGestures` should be **on** for maps embedded inside long scrolling pages (the dossier's map inset) and **off** for the full-page `/map`, so scroll-hijacking never happens on a reading page.
**Outline delta:** N/A.

### F10.20 — WCAG's "graphical object" exemption for essential presentations does not exempt SIG's map glyphs
**Claim:** SC 1.4.11 exempts inactive components and cases where "a particular presentation of graphics is essential," including photographs and logos.
**Status:** VERIFIED
**Evidence:** `https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html`.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG cannot claim the "essential" exemption for its device markers or status glyphs — their appearance is a design choice, not an essential presentation. The basemap imagery itself (if satellite tiles are ever offered) *is* exempt, which is precisely why every SIG marker carries a halo: the marker must meet 3:1 against a background SIG does not control.
**Outline delta:** N/A.

### F10.21 — Ordinal epistemic state is legible without color in two independent production systems
**Claim:** GRADE renders four certainty levels as ⊕⊕⊕⊕/⊕⊕⊕◯/⊕⊕◯◯/⊕◯◯◯; Wikidata renders rank as star/circle/X icons *in addition to* background color.
**Status:** VERIFIED (evidence in F10.2 and F10.3)
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's support badge copies GRADE's glyph, inheriting demonstrated legibility in printed evidence tables — which matters because the dossier is a print artifact. Wikidata's icon-*and*-color belt-and-braces is the pattern for the conflict axis (glyph *and* rule *and* hue).
**Outline delta:** N/A.

### F10.22 — iCalendar STATUS has exactly the three values SIG needs to express date confidence in a calendar client
**Claim:** RFC 5545's VEVENT `STATUS` takes `TENTATIVE`, `CONFIRMED`, `CANCELLED`.
**Status:** VERIFIED (RFC 5545 fetched; see F10.11)
**Retrieved:** 2026-08-20
**Implication for the spec:** Map `support < strongly_supported` or `conflict = contested` → `TENTATIVE`; `historical`/withdrawn contract → `CANCELLED`. A subscriber's calendar client will then *visually* distinguish an uncertain date without SIG shipping any UI at all. This is the rare case where an epistemic axis survives export into a foreign application.
**Outline delta:** EXTENDS §15.4.

### F10.23 — Wikipedia frames inline-doubt templates as contributor communication, not reader warnings
**Claim:** `{{Citation needed}}` "is a request for another editor to supply a source… a form of communication between members of a collaborative editing community," and "is never, in itself, an 'improvement' of an article."
**Status:** VERIFIED (evidence in F10.6)
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG inherits both halves: the doubt marker must generate a task, *and* SIG must not treat marker density as progress. A dossier covered in `not_researched` hatching is not well-documented; the coverage meter, not the marker count, is the progress metric.
**Outline delta:** EXTENDS §12.

### F10.39/F10.40 — The design-system layer is fully MIT/Apache and needs no commercial component
**Claim:** Tailwind CSS 4.3.3 (MIT), Radix Primitives (MIT), shadcn CLI 4.18.0 (MIT), React Aria Components 1.20.0 (Apache-2.0) are all current and permissively licensed; MUI Base UI is still at `1.0.0-rc.0` (2025-12-04).
**Status:** VERIFIED
**Evidence:** npm registry queries for each package on 2026-08-20 (versions/dates/licenses in the D.1 table); `gh api repos/shadcn-ui/ui` (MIT, 121,714 stars, pushed 2026-08-20), `repos/radix-ui/primitives` (MIT), `repos/adobe/react-spectrum` (Apache-2.0).
**Retrieved:** 2026-08-20
**Implication for the spec:** Use Tailwind 4 for the token system (the epistemic tokens in B.3.2 become CSS custom properties consumed by Tailwind's `@theme`), shadcn's copy-in-code model for components SIG will heavily customize (every SIG table cell is customized), and React Aria Components specifically for the combobox, menu, dialog, and grid patterns where hand-rolled ARIA is the usual source of a11y regressions. Base UI is not yet stable and should not be adopted this cycle.
**Outline delta:** N/A.

---

## Open questions

1. **Does the four-axis epistemic model survive contact with real reconciliation output?** The support-derivation rules (B.2.1) are a proposal, not a calibration. They must be tested against ~200 hand-graded claims before launch; if human graders disagree with the derived level more than ~20% of the time, the rule set is wrong, not the graders. **Hedge:** ship the axes and the storage; treat the derivation thresholds as configuration, versioned in `/methodology`, so they can change without a schema migration.
2. **What is the right staleness horizon per claim type?** The numbers in B.2.1 are informed guesses. The empirical answer requires observing portal change rates over ≥6 months. **Hedge:** store `observed_at` precisely and compute staleness at read time from a config table, never bake a `stale` boolean into storage.
3. **How should the dossier handle a jurisdiction with many organizations** (a county with 30 municipal PDs plus a sheriff plus a transit authority)? The Appendix B YAML is single-org-shaped. A `/place/{geoid}` roll-up needs an aggregation semantics for contested and absent values that this workstream did not solve. **Hedge:** ship `/org/` first; treat `/place/` as a v1.1 surface with an explicitly-labeled "sum of documented values only" aggregation.
4. **Is `not_researched` at scale demoralizing or clarifying?** A national map that is 95% hatched is honest and may also read as "this site has nothing." No prior art resolved this. **Hedge:** A/B is inappropriate for an epistemic claim; instead, user-test with P3 and P6 before launch and adjust the *copy*, never the underlying state.
5. **FollowTheMoney compatibility is unverified** (F10.16, `followthemoney.tech/explorer/` 404). If SIG wants Aleph interoperability as an export target, a dedicated verification pass is needed.
6. **Does deck.gl 9.3 pin cleanly against maplibre-gl 6.4.x?** The compatibility range is undocumented (F10.33). **Hedge:** pin both, add a visual-regression test, and keep the deck.gl overlay optional so a version conflict degrades to the PMTiles layer rather than breaking the map.
7. **Legal review of the dispute-publication policy (E.5)** — publishing a vendor's demand letter verbatim is defensible and standard practice, but SIG should have counsel confirm the approach and the response SLA before the first letter arrives, not after.
8. **The Markup's methodology commitments could not be extracted** from the series landing page (`https://themarkup.org/series/show-your-work` returned article listings only; `/show-your-work/2020/02/25/the-markup-methodology` 404s). SIG's methodology page should be re-benchmarked against an individual Markup "How We…" piece before publication.
9. **Print PDF at scale.** WeasyPrint rendering ~20,000 dossiers on demand has an unmeasured cost profile. **Hedge:** generate on demand with a cache keyed by `(org_id, as_of)`, and pre-generate only for the top-N most-visited entities.

## Spec requirements emitted

- **REQ-R10-01** Every claim MUST carry four independent epistemic axes — `support` (4-level ordinal), `conflict` (4-value), `currency` (4-value), `absence_kind` (4-value, null when a value is present) — stored separately and never collapsed into a single field in storage, API, or export.
- **REQ-R10-02** `support` MUST be derived by a published, versioned rule from stored evidence-strength and inter-source-agreement inputs, and MUST NOT be hand-set. The derivation rule MUST be reachable by URL from every rendered badge.
- **REQ-R10-03** Hard rules R1–R4 MUST be enforced at write time: no `confirmed` from a single source; derived claims capped at `strongly_supported` and never above their weakest input; subject-self-report capped at `probable`; every sub-`confirmed` claim carries ≥1 downgrade reason code from the closed vocabulary.
- **REQ-R10-04** A null value MUST NEVER render as an empty cell, dash, or zero. It MUST render as one of the four labeled absence affordances, and `searched_not_found` MUST carry a named, dated, reproducible search procedure or be downgraded to `not_researched`.
- **REQ-R10-05** Every contested claim MUST render its reconciled value together with the full range across sources, visible without hover, in the table cell, the detail panel, the print output, the CSV, and the API.
- **REQ-R10-06** Every reconciliation rule MUST declare which of its inputs measure different quantities, and the UI MUST render that semantic-mismatch note above the numeric comparison.
- **REQ-R10-07** No API response containing a `value` may omit its `epistemic` object; `competing_claims` MUST be present whenever `conflict != "uncontested"`; every competing claim MUST carry a `measures` field and an `is_lower_bound` flag where applicable.
- **REQ-R10-08** Every CSV export MUST include `support`, `conflict`, `currency`, `distinct_values`, `value_min`, `value_max`, `as_of`, and `claim_url` alongside every reconciled numeric column, and MUST ship a Frictionless Data Package v2 descriptor.
- **REQ-R10-09** Bulk exports MUST split ODbL-derived resources into separately-licensed Data Package resources so a consumer can take non-ODbL data without triggering share-alike; per-record `_licences` and an `odbl-derived` flag MUST appear in API responses and a `X-SIG-Licence` header on every response.
- **REQ-R10-10** Every content URL MUST accept `?as_of=YYYY-MM-DD` and return a bitemporal reconstruction; every page MUST display the snapshot timestamp, the permalink, and a citation block offering BibTeX, APA, Chicago, and RIS.
- **REQ-R10-11** Every entity MUST have a permanent, never-reused stable ID; merges MUST be disclosed via a `moved_to` payload and a `Deprecation` header, never a silent redirect.
- **REQ-R10-12** Every page MUST render complete and correct with JavaScript disabled. Map and graph surfaces MUST each have a co-equal, linked, shareable tabular route (`/map/table`, `/graph/{id}/table`) that reflects the current filter state.
- **REQ-R10-13** The dossier MUST include a "What we don't know" section rendered above the fold in the summary, in the print export, and in the API — never as an appendix.
- **REQ-R10-14** The dossier MUST offer a server-generated 4-page PDF at `/org/{id}.pdf?as_of=` produced from the same HTML as the web page, with the permalink printed as text, a QR code, and a running footer stating the snapshot date.
- **REQ-R10-15** The dossier MUST provide a per-fact evidence expander that discloses source, tier, observation date, evidence artifact with page anchor, extraction method, and human-review status.
- **REQ-R10-16** An entity with no researched facts MUST render a full dossier in the `not_researched` state and MUST NOT 404 and MUST NOT imply absence of surveillance.
- **REQ-R10-17** The map MUST render a coverage underlay for un-researched jurisdictions whenever the point layer is visible, and its legend MUST state that absence of points is not evidence of absence.
- **REQ-R10-18** The map MUST NOT place any marker at a computed centroid for a coordinate-less entity; such entities MUST appear in a permanent "not on the map" panel with counts and reasons, including disclosed withholdings.
- **REQ-R10-19** Map status and confidence MUST be encoded by shape, fill, and texture such that the map is fully legible in grayscale; a grayscale and CVD-simulation screenshot test MUST run in CI and fail the build on indistinguishable state pairs.
- **REQ-R10-20** Sharing edges MUST default to ego mode with no edges drawn until a node is selected, MUST cap rendered arcs and disclose the truncated remainder, and MUST mark both endpoints of any edge whose entity resolution is uncertain.
- **REQ-R10-21** Graph centrality measures MUST be off by default, MUST display an entity-resolution denominator when shown, MUST be labeled unreliable above a 5% unresolved-identity threshold, and MUST NOT be exported without their caveat fields.
- **REQ-R10-22** OSM attribution MUST be permanently visible in the map corner, uncollapsed, linked to openstreetmap.org/copyright, on every surface displaying OSM-derived tiles or geometry.
- **REQ-R10-23** Basemap tiles MUST be self-hosted PMTiles v3 archives; the system MUST NOT hotlink `maps.protomaps.com/builds` and MUST NOT send user viewport data to any third party.
- **REQ-R10-24** The renewal-watch feed MUST emit RFC 5545 iCalendar with stable `UID`s keyed to claim ids, incrementing `SEQUENCE` on every correction, and `STATUS:TENTATIVE` for any date below `strongly_supported` or with `conflict = contested`.
- **REQ-R10-25** Subscriptions MUST be available without an account via iCal and RSS; email subscriptions MUST use double opt-in, `List-Unsubscribe`, and MUST NOT include open or click tracking.
- **REQ-R10-26** Every claim MUST disclose its extraction method; LLM-assisted extractions MUST be labeled in the UI, capped at `support = probable` until human-reviewed, and carry the `extraction_unreviewed` reason code.
- **REQ-R10-27** The evidence viewer MUST support page-and-character-anchored deep links that work without JavaScript, and MUST offer a one-click "copy with citation" producing quote, document, date, capture time, hash, and URL.
- **REQ-R10-28** Portal snapshot diffs MUST separate material from cosmetic changes, MUST auto-create a research task for each material change, and MUST expose both archived WARCs with hashes.
- **REQ-R10-29** Evidence archived but not republished MUST still expose a public metadata record with hash, capture time, and the stated reason for non-publication.
- **REQ-R10-30** The research queue MUST support claim-with-timeout locking, MUST forbid self-review, MUST implement the seven-outcome vocabulary including `searched_not_found` and `needs_records_request`, and MUST credit `searched_not_found` equally with `resolved`.
- **REQ-R10-31** Geographic queues MUST be claimable by named local groups with a public steward page, MUST NOT confer editorial control or task exclusivity beyond a 14-day first-refusal, and MUST lapse after 90 days of inactivity. (Answers Q36.)
- **REQ-R10-32** The queue MUST NOT publish cumulative-volume leaderboards, MUST cap concurrently held tasks, MUST auto-escalate tasks with 3+ `too_hard` outcomes, and MUST publish its own median review latency.
- **REQ-R10-33** SIG MUST publish a public corrections log with three severity tiers, per-entry permalinks, an RSS feed, links to the prior snapshot for Tier-1 corrections, and a quarterly published correction rate.
- **REQ-R10-34** Any claim MUST be disputable by anyone via a public dispute record; the disputant's statement MUST be published verbatim alongside SIG's response within 10 business days.
- **REQ-R10-35** Every entity and claim page MUST render a structured "How we know this" module with fixed fields (tier counts, source-family independence, evidence date range, rules applied, human-review counts, extraction methods, licensing mix, coverage counts).
- **REQ-R10-36** The site MUST conform to WCAG 2.2 Level AA, including SC 1.4.1, 1.4.3, 1.4.10, 1.4.11, 1.4.12, 2.1.1, 2.4.7, 2.4.11, 2.5.7, 2.5.8, 3.3.7, and 3.3.8, and MUST publish an accessibility statement naming the target, known gaps, and a contact.
- **REQ-R10-37** Map features MUST be keyboard-traversable with focus announced via an `aria-live` region, and all dragging interactions MUST have single-pointer, non-path alternatives.
- **REQ-R10-38** Saturated color MUST be reserved for epistemic state; the product MUST use at most two saturated data hues (amber = contested, red = retracted) plus one link/focus blue, and MUST NOT use green for confidence.
- **REQ-R10-39** All color tokens MUST meet 4.5:1 for text and 3:1 for borders, glyphs, and focus rings in both themes, verified by an automated contrast test; `--ink-300` and dark-theme `#475569` MUST be lint-banned from meaningful roles.
- **REQ-R10-40** Performance budgets in D.3 MUST be enforced in CI; no page may load third-party resources of any kind.
- **REQ-R10-41** All UI strings MUST live in ICU MessageFormat catalogs from the first release; the epistemic vocabulary MUST be translated with its glosses by a domain-competent translator, not as a string list.
- **REQ-R10-42** The API MUST be described in OpenAPI 3.1.1, reusing the same JSON Schema 2020-12 documents used for export and ingestion validation, and MUST publish a DCAT 3 catalog at `/data/catalog.jsonld` with `dcat:accrualPeriodicity`.
- **REQ-R10-43** Every list endpoint MUST include a coverage envelope with documented / not-researched / searched-not-found counts and a denominator note, so no consumer can compute a total without seeing the caveat.
- **REQ-R10-44** Read access MUST NOT require an API key; rate-limit headers MUST always be present; 429 responses MUST include the bulk-download URL.
- **REQ-R10-45** Editorial copy MUST attribute rather than assert, MUST NOT use evaluative adjectives about subjects, MUST structurally distinguish allegations from findings, and MUST NOT characterize intent.
- **REQ-R10-46** Every reader-visible doubt marker (`not_researched`, `contested`, low support) MUST be a one-click research-task creator, binding the epistemic UI to the §12 task system.
