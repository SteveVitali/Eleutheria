# ADR-158: Graph exploration as aggregated overviews — overview graphs of at most 3,000 nodes, entity egos and `/explore/`, descriptive only

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P — A-11 (2026-10-01T04:09:43Z, round 5) and A-22 (2026-10-01T04:25:48Z, round 8); operator
  decisions recorded verbatim below
- **Requirement ids:** SIG-UI-021, SIG-UI-022, SIG-UI-023, SIG-UI-024, SIG-UI-025, SIG-IDENT-030, SIG-INGEST-043c,
  SIG-TRUST-006, SIG-LIC-004a, SIG-LIC-009a, SIG-LIC-010; drafts SIG-UI-D29…D34 and SIG-EXPORT-D20/D21 (K2 §8; adopted
  by K13 as UXR-A03, numbered by PLAN-11C)
- **Spec:** `docs/2_canonical_design_spec.md` §14.7, §23.9, §39.3–§39.4, §42.2, §42.4, §55.2
- **Implemented by:** P35.29, P35.30, P36.29, P36.41, P36.75, P37.21, P37.22, P37.23, P37.24, P37.25, P37.26, P37.27;
  acceptance P37.64 and the ACC-EXPLORE leg of P37.65b (`PD/data/round11_plan.csv`)
- **Sources:** `PD` = `docs/build/planning/2026-09-30-next-phase/`. `PD/feedback/RATIFICATION_LOG.md` rounds 5, 8, 11;
  `PD/data/decision_catalog.csv` rows D-K13-1, D-K0-6, D-K2-2, D-K2-3, D-K2-4, OD-24; `PD/design/K0-interactive-architecture.md`
  §4, §6–§7, §11; `PD/design/K2-graph-and-entities.md` §0, §3.4, §5–§8, §11; `PD/design/K13-ux-synthesis.md` §10.1;
  `PD/NEXT_PHASE_PLAN.md` §4.2, §5.5, §5.7, §7
- **Relationship to landed ADRs:** supersedes, amends, qualifies and extends none (PLAN §7 lists no status line for
  ADR-158). Related: ADR-051 (honest rendering of the map and network explorer), ADR-097 and ADR-134 (the network island
  and the workspace-state contract, whose explore rules ADR-155 re-decides), ADR-124 (one publication eligibility policy),
  ADR-153 (derivation, not identity), ADR-155 (HTML-first page types; `/explore/` is a T2 surface), ADR-159
  (organisation publication), ADR-169 (the rights basis, including the delegated `eyes_on_flock` review).
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records
  operator decisions taken at GATE-P; the record text is agent-drafted.

## Context

The operator asked, among the eleven U-003 asks (2026-09-30T21:28:52Z), for a network explorer with human-readable
labels, entity detail pages and *"a global graph or set of graphs … that truly lays bare all that we know"*
(U-003.2, as quoted in K13 §10.1 and D-K13-1), and later that *"journalists need to be able to really truly explore the
knowledge graph … always with full explicit transparent evidence/lineage"* (U-005, 2026-09-30T21:58:23Z).

Three spec MUSTs constrain the answer:

- **SIG-UI-021:** sharing edges MUST NOT be drawn as a national hairball; the default is an ego network, with matrix
  and arc views as alternatives.
- **SIG-UI-022:** the network explorer's default view is an ego network with expansion, not a global graph.
- **SIG-IDENT-030:** no network-analytics surface may ship before the entity-resolution gates pass. The UI MUST carry an
  ER-quality disclosure wherever centrality or hub statistics appear (also SIG-UI-023).

What K2 measured on the spine (§0, §1, §5.2; planning-time reads, cited, not re-run here):

- **Size.** 42,488 entity-to-organisation edges over 41,897 nodes, in 354 components. The largest component is a
  26,840-node star caused by a modelling error ("OpenStreetMap contributors" recorded as a camera operator, K2 NEW-2).
- **Dates.** 0 edges have a bounded valid period; 500 (1.2 %) carry any date.
- **Flock share lists.** The lists in the Eyes on Flock mirror hold 474,184 edges (I3). They are not claims yet.
- **Labels.** 82.8 % of released records have no label.
- **Live `/network/` copy.** It asserts "deterministic identity resolution", and degree "exact … never an estimate",
  although no organisation-level ER runs (K2 NEW-6).

A raw national node-link graph would therefore draw duplicated, undated and mislabelled edges at a scale no browser
budget allows, and would break SIG-UI-021/022 and SIG-IDENT-030.

K0 (D-K0-6), K2 (D-K2-2) and K13 (D-K13-1) recommended the same answer: a *set* of aggregated overview graphs, each with
at most 3,000 nodes, plus entity ego graphs and an explorer at `/explore/`, descriptive only. At A-22 the operator also
decided whether SIG may use the Flock share lists that the `eyes_on_flock` mirror already holds.

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

| line | round time (UTC) | question as presented (summary, log) | operator answer, verbatim | sha256 of the answer text |
|---|---|---|---|---|
| A-11 | 2026-10-01T04:09:43Z (round 5) | "global graph" form — options *Overviews + egos (Recommended) · Also a full national graph · Egos only* | **Overviews + egos (Recommended)** | `9665b90cb9b3987f260a1561e46424d811f5f1bf457307ab8a6e0257819a5e96` |
| A-22 | 2026-10-01T04:25:48Z (round 8) | Eyes on Flock mirror — options *Keep + use share lists (Recommended) · Keep, no extension · Suspend pending my review* | **Keep + use share lists (Recommended)** | `c22738ea7d3b60ddc521b44137ffa024ec708e59f0ca5c597e1f5571dd02ba96` |

Each answer is an option label selected by the operator. Label: **agent-drafted, adopted by the operator at
2026-10-01T04:09:43Z** (A-11) and **at 2026-10-01T04:25:48Z** (A-22). The sha256 is
`printf '%s' "<answer>" | shasum -a 256`, computed at writing.

The decision rows those answers settle (`PD/data/decision_catalog.csv`, `operator_answer`, verbatim):

- **D-K13-1:** *"a — aggregated overview graphs (≤ 3,000 nodes) + entity egos + /explore/, descriptive only; revisit at
  > 3,000 labelled nodes"*.
- **D-K0-6:** *"yes"*. The question was "The 'global graph' is a set of aggregated overview graphs, not a raw national
  node-link graph (amends SIG-UI-021/022 wording)".
- **D-K2-2:** *"a — descriptive views only; no centrality, rankings or labelled communities"*.
- **D-K2-4:** *"yes — Flock share lists become organisation-level configured_access claims after a §43.2a/Part VIII
  screen"*.
- **OD-24:** *"b — keep the Eyes on Flock mirror live on its CC-BY-SA-4.0 basis, the 09-16 review disclosed as delegated,
  and use its share lists (D-K2-4 yes)"*.

D-K2-3 (degree-only facts as node attributes only) and D-K2-5/6/7 were accepted with the B-22 batch, answered
**"Accept all five (Recommended)"** at 2026-10-01T04:33:54Z (round 11).

### What is decided

1. **"Global" means a set of aggregated overviews, never a national hairball.** Each overview answers one question.
   The catalogue below is K2 §5.2's design, which the overview builders P37.24–P37.25 implement:
   - **O0** — types: what SIG holds, by kind, gaps included.
   - **O1** — supply: who sells surveillance technology to whom. Unclassified procurement is excluded (D-K2-5).
   - **O2** — access: who can search whose data.
   - **O3** — funding.
   - **O4** — operators by place.
   - **O5** — governance: laws and instruments, by technology and jurisdiction.
   - **O7** — adoption: agency by technology, after placement.

   Each overview has at most **3,000 nodes** and is aggregated by construction. A build fails if an overview exceeds
   the cap without an aggregation rule (draft SIG-UI-D30). Every overview drills down to entity egos (SIG-UI-022).
2. **Three forms from one release file.** Each overview ships as:
   - a T1 static page at `/graphs/<id>/` with an SVG, a paginated adjacency table and per-compartment CSV/JSON;
   - single-facet no-JS pages per state;
   - the T2 explorer view `/explore/?v=2&overview=<id>`.

   Entity pages carry a static 1-hop graph. Everything is a release artifact (`sig.graph-overview/1`,
   `sig.graph-components/1`, `sig.entity-page/1`, `sig.entity-label/1`, `sig.slug-history/1`; draft SIG-EXPORT-D20),
   built from the export's one snapshot. **Explore surfaces never read live-spine routes.**
3. **Descriptive only.**
   - Overviews show evidenced edges and counts.
   - **No centrality, "hub" or "most connected" ranking and no labelled communities.** Build-time community detection
     may position nodes but is never shown as a finding.
   - The live `/network/` centrality statistic and its "deterministic identity resolution" copy are withdrawn (K2
     NEW-6).
   - SIG-IDENT-030 is met by abstention (PLAN §6.6) until its ER gates pass.
   - Every count carries the ER-quality disclosure (SIG-UI-023; K2 H-8). Counts say "records" until the dedup ships
     (B-26).
4. **Honesty rules bind every overview, ego and explorer view** (K2 §7 H-1…H-13). In summary:
   - No UUID or connector key as a label.
   - Every edge states its relation, direction, access kind, date (or "undated"), currency, sources and an evidence
     link.
   - Historical and undated edges are visible and never present-tense.
   - **Degree-only facts are node attributes, never edges** (SIG-INGEST-043c; D-K2-3).
   - The three access kinds stay separate (SIG-UI-024).
   - Paths are published to at most 3 hops, with per-hop evidence. Longer paths are labelled speculative, and "no path"
     is a typed answer (SIG-UI-025).
   - Mirrors count once.
   - A source is never shown as an operator.
   - Every edge reaches the provenance panel of each supporting claim in at most 2 actions, with or without JS.
5. **The state × state Flock-sharing overview (A-22 with A-11).** P36.75 turns the share lists into organisation-level
   `configured_access` claims under these limits:
   - **Inputs.** The lists come from the `eyes_on_flock` mirror, plus any Flock portal that ADR-188's probe finds
     served without a challenge.
   - **Screen.** Only after the §43.2a / Part VIII screen: no operator ids, search reasons or audit rows
     (SIG-PUB-003a).
   - **Use.** P37.25 builds O2's national form from those claims as a **state × state matrix** (at most 56 × 56
     weighted cells, the matrix view SIG-UI-021 names), plus per-agency egos grouped by state and type. It is never a
     national node-link graph.
   - **Compartment (S6R-12, `PD/reviews/S6r-closure.md`).** The overview is built from CC BY-SA 4.0 claims, so it is
     published in the CC BY-SA compartment with share-alike attribution (SIG-LIC-009a), or built per compartment.
     SIG-LIC-010's build check must pass. It is never merged into the CC-BY graph (SIG-LIC-004a).
   - **Disclosure.** The `eyes_on_flock` rights record and source page disclose that its 2026-09-16 review was
     delegated (OD-24; recorded by ADR-169).
6. **Eligibility is consumed, never bypassed** (SIG-TRUST-006; ADR-124).
   - Organisation labels and nodes appear only for organisations publishable under ADR-159. Every other organisation
     is in the typed "not yet reviewed" state.
   - No overview, ego or path may expose a withheld endpoint through a label or through edge topology.
   - *Agent interpretation:* whether a withheld endpoint is excluded from a matrix cell or counted only as an unlabelled
     aggregate is decided by P37.24–P37.25 against SIG-TRUST-006. It is never labelled or linked.
7. **Budgets and URL state are not decided here.** `/explore/` is a T2 surface under ADR-155 (initial JS at most
   120 KiB; per-overview data at most 200 KiB; a server-rendered first view and a complete no-JS equivalent). Its URL
   state is `sig.workspace-state/2` (ADR-155, extending ADR-134).

### Spec wording this ADR relies on, and who applies it

- D-K0-6 is recorded "amends SIG-UI-021/022 wording". K0 §7 drafts the amendment: *keep the ban on a national node-link
  hairball and add that aggregated overview graphs … of at most a few thousand nodes MAY serve as the global entry
  point, each carrying the ER-quality disclosure and drilling down to entity egos*.
- PLAN §6.3 does not list this amendment. *Agent interpretation:* it is owed by the spec-amendment unit (SEED-12) or by
  PLAN-11C with the K13 families (UXR-A03 cites SIG-UI-021/022). Under PLAN §6.5's rule ("an amendment that weakens a
  MUST is a waiver"), the unit that applies it checks whether the MAY relaxes SIG-UI-022's "not a global graph". This
  ADR does not apply that text.

## Consequences

- **U-003.2 gets a concrete answer within the spec's MUSTs.** It is overviews O0–O5/O7 that can be navigated, entity
  pages, egos and a path finder, each with evidence in at most 2 actions. SIG-UI-021, SIG-UI-022 and SIG-IDENT-030 are
  kept: there is no hairball, egos are the drill-down, and there is no analytics.
- **The access question becomes answerable.** "Who can search whose data" scales from one 2020 EFF star (131 nodes,
  historical) to a state × state matrix built from the Flock share lists. It stays organisation-level and screened.
- **The cost is small.** K2 §6.6 estimates (inference) at most about $2/month at 10k explore sessions and at most about
  $10 at 100k; overview files are at most 132.5 KB gzip at the 3,000-node / 10,000-edge cap (measured on synthetic
  shapes at real counts, K2 §6.3).
- **Explore stays thin until upstream rows land.** It depends on labels (P35.29) and on placement, since Data Driven and
  Atlas agencies carry no place today. Until then, entity pages and overviews show typed absences, not guesses (K13
  R-1: the UX must not outrun the data).
- **Today's `/network/` page changes.** Its centrality statistic and resolution claims are removed, and it becomes a
  redirect or a T1 page (K0).
- **The share-list overview carries the mirror's risks.** These are the terms-conflicted vendor-portal origin (the
  operator's accepted risk, PLAN §14 R-18) and the delegated 09-16 review, which is disclosed. A rights or Part VIII
  change to `eyes_on_flock` reaches this overview.
- **"No ranking" is a product limit, stated openly.** Journalists cannot sort agencies by "most connected" until the
  identity gates pass.

## Alternatives considered

- **A single national node-link canvas as well** (A-11 option "Also a full national graph"; D-K13-1 option b). Rejected
  by the operator's answer. It needs SIG-UI-021/022 and SIG-IDENT-030 changed and heavy client JS, and it adds little
  truth while organisations are unmerged and 98.8 % of edges are undated.
- **Egos only** (A-11 option "Egos only"). Rejected by the operator's answer: there would be no global entry point for
  U-003.2.
- **Descriptive views plus centrality under a SIG-IDENT-030 waiver** (D-K2-2 option b). Rejected (D-K2-2 = a). Rankings
  over duplicated, undated edges would be misleading.
- **No use of the Flock share lists** (A-22 options "Keep, no extension" and "Suspend pending my review"). Not chosen.
  The access overview would stay a historical 131-node star.
- **Drawing the share lists as a national node-link graph.** Rejected: SIG-UI-021, plus about 517 partners per Flock
  agency on average (K0 §8, I3).

## Revisit trigger

- **The node cap is reached.** A single view needs more than 3,000 labelled nodes (D-K13-1's revisit, verbatim
  "revisit at > 3,000 labelled nodes"; K0 revisit trigger 3), or the graph renderer would need WebGL 2 only.
- **The identity gates pass.** Then centrality, rankings or communities may be proposed, by a new ADR only (D-K2-2).
- **The operator asks for a national node-link canvas.** That needs a new ADR plus spec changes to SIG-UI-021/022 and
  SIG-IDENT-030.
- **The share-list basis changes.** Any of these reopens item 5:
  - an objection, terms change or block affecting the `eyes_on_flock` mirror or a Flock portal;
  - a Part VIII screen change;
  - a change to the source's rights record (ADR-169);
  - the aggregator ceasing publication (ADR-188's trigger).
- **The `/explore/` budget is missed.** `/explore/` misses ADR-155's T2 budget or Lighthouse floor on the real release
  for two consecutive releases (K0 trigger 1). This is re-decided under ADR-155.
- **A withheld organisation leaks.** One is found exposed through an overview's labels or topology (SIG-TRUST-006). Stop
  publishing the affected overview and record the fix by a new ADR.
