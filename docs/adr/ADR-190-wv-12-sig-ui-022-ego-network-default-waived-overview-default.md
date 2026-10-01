# ADR-190: WV-12 — SIG-UI-022's ego-network default waived; the explorer may open on an aggregated overview

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-12 (Round-11 Stage B, T1 — unit SEED-12c)
- **Requirement ids:** SIG-UI-022 (its default-view clause WAIVED, scoped as below; "not a global graph" stands); SIG-UI-021, SIG-UI-023, SIG-UI-024, SIG-UI-037 and SIG-IDENT-030 stand unchanged
- **Spec:** docs/2_canonical_design_spec.md §39.4 — SIG-UI-022 at line 5840; §39.3 — SIG-UI-021 at lines 5835–5836 (as built at `71e8bc83`; source `docs/research/_meta/spec_src/81_partVII_s39to41_ui.md`, which carries the waiver note)
- **Decision:** the operator's answer to SB-1 (waiver WV-12), 2026-10-01T13:46:58Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 27; it builds on A-11 (2026-10-01T04:09:43Z, round 5)
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.2 (A-11), §5.7, §6.5 (the waiver rule), §7 row 158; `docs/build/planning/2026-09-30-next-phase/stageB/CARRY.md` (items from SEED-11b, SEED-12b and round 27)
- **Related:** ADR-158 (graph exploration as aggregated overviews — it left the default-view wording to the spec unit), ADR-155 (HTML-first page types; `/explore/` is a T2 surface), ADR-150 (an amendment that weakens a MUST is a waiver), ADR-124 and ADR-159 (publication eligibility), ADR-097 (the `/network/` island); spec Appendix G.7 rows R11-A2, R11-W13 and G.7.5
- **Recorded:** 2026-10-01T13:55:55Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-12c. Everything in this record except the quoted operator words is agent-drafted.

## Context

At A-11 the operator chose "Overviews + egos (Recommended)": the "global graph" asked for in U-003.2 is a set of
aggregated overview graphs of at most 3,000 nodes each, plus entity ego graphs and an explorer at `/explore/`
(ADR-158). D-K0-6 recorded that this "amends SIG-UI-021/022 wording", and K0 §7 drafted the amendment: aggregated
overview graphs "MAY serve as the global entry point". The approved design opens the explorer on an overview: K2's
route table redirects `/network/` (301) to `/explore/?v=2&overview=access`, and K13 adopted it (conflict C-16; GX-09a,
row P37.26).

SIG-UI-022 says the network explorer's default view is an ego network with expansion, not a global graph. SEED-12b's
MUST-weakening test (plan §6.5; ADR-150) found that letting an overview replace the ego network as the explorer's
default weakens that MUST. It therefore applied only the non-weakening reading (Appendix G.7 R11-A2: overviews as
alternative views, the ego default kept) and listed the entry-point clause in Appendix G.7.5 as needing the operator's
words. The orchestrator put the question to the operator in round 27 as SB-1, with the options "Overview as default
(Recommended)" and "Keep ego default".

## Decision

### The operator's words

- **Answer to SB-1, verbatim:** "Overview as default (Recommended)" — round 27, 2026-10-01T13:46:58Z; sha256 of the
  label `add2aec7c0d6f221f4f5e6ba42a48a913f9d40d5d87da59cd5458cddc4514237`.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T13:46:58Z:**

  > I waive SIG-UI-022's ego-network default: the explorer may open on an aggregated overview, with every node drilling to its ego view.

  sha256 `1ce44d4df7f631e4ec891e52a4191fe0f15e32900991b99b43ce7398f7ef76b8` — `printf '%s' "<sentence>" | shasum -a 256`
  over the text between the log's italic quote marks, computed by SEED-12c at writing. The sentence was selected from
  an agent-drafted option, which the log records as the operator adopting it as their words (log round 24 note; plan
  §1.3).

### The requirement and the clause waived

> **SIG-UI-022 (MUST).** Default view is an **ego network with expansion**, not a global graph.

— `docs/2_canonical_design_spec.md:5840`

- **Waived:** "Default view is an ego network with expansion". The network explorer (`/explore/`, and `/network/`
  while it redirects there) may open on an aggregated overview graph instead of an ego network.
- **Stands (agent reading of the sentence's scope, labelled):** "not a global graph" in the sense SIG-UI-021 and
  ADR-158 give it — no national node-link graph and no hairball. The overview the explorer opens on is an aggregated
  overview under ADR-158 (at most 3,000 nodes, aggregated by construction, descriptive only, carrying the ER-quality
  disclosure). The ego network with expansion stays the view that every overview node opens.
- **Unchanged:** SIG-UI-021. The access overview is the matrix view it names (a state × state matrix, ADR-158 §5),
  and selecting an entity opens its ego network, which is SIG-UI-021's "default to an ego-network from a selected
  entity" (agent reading, labelled).

### Scope

The explorer's initial view — `/explore/` and the `/network/` redirect (rows P37.26 and P37.27) — for aggregated
overviews that meet ADR-158, while this ADR stands. Nothing else changes: entity pages keep their static 1-hop graph,
and no national node-link graph is drawn anywhere. Coverage: `WAIVED(ADR-190)` for SIG-UI-022's default-view clause,
with "not a global graph" named as standing in `accepted_scope` (recorded by T4, SEED-14).

### Compensating controls

1. **Every overview node drills to its ego view.** Each node of any overview the explorer opens on reaches that
   entity's ego network with expansion in one action, with or without JavaScript, so SIG-UI-022's view stays one
   action away. The explorer rows (P37.26, P37.27) and the explore acceptance (P37.64, the ACC-EXPLORE leg of P37.65b)
   check that every overview node resolves to an ego view.
2. **No-JS parity.** The overview the explorer opens on has a complete no-JavaScript equivalent: its T1 static page
   `/graphs/<id>/` (SVG, paginated adjacency table, per-compartment CSV/JSON) and a server-rendered first view in the
   reserved box (ADR-155's T2 rules; SIG-UI-037). Each node's ego view has one too: the entity page and its static
   1-hop graph. The no-JS parity spec of P35.50 covers the explorer's landing state.
3. **The overview honesty rules bind the default** (ADR-158 items 1, 3 and 4): at most 3,000 nodes, aggregated by
   construction; descriptive only, with no centrality, "hub" or "most connected" ranking and no labelled communities;
   the ER-quality disclosure on every count (SIG-UI-023); access kinds kept separate (SIG-UI-024); historical and
   undated edges marked; never a national node-link hairball (SIG-UI-021).
4. **Eligibility is consumed.** No overview exposes a withheld organisation through a label or through edge topology
   (SIG-TRUST-006; ADR-124, ADR-159).

## Consequences

- The design approved at A-11 stands as K2 and K13 drew it: `/network/` 301 → `/explore/?v=2&overview=access`, and
  the explorer opens on the access overview (built from screened share-list claims, ADR-158 item 5) or on the overview
  named in its URL state.
- The spec keeps the Round-11 note on SIG-UI-021/022 (R11-A2) and the G.7.5 row and adds a waiver note after them
  (R11-W13); the earlier texts are kept, and the waiver supersedes them for the explorer's default view only.
- The exposure: a reader may take an aggregated overview for a complete picture. Controls 1–3 carry it: the
  ER-quality disclosure, counts worded as "records" until the dedup ships (B-26), and an ego view one action from
  every node.
- The plan's waiver list (§6.5; "eleven waivers" in §13.5) gains a twelfth, WV-12. The plan is canonical planning text
  and this unit does not edit it. T4 records the verdict and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv`
  carries this ADR's revisit trigger.

## Alternatives considered

- **Keep the ego default (SB-1's second option).** `/network/` would land on an entity search or a chosen ego, with
  the overviews reachable as alternative views (R11-A2's reading). Not chosen.
- **Apply K0 §7's "MAY serve as the global entry point" wording as a plain amendment.** Rejected by SEED-12b's
  MUST-weakening test (plan §6.5; ADR-150). The wording weakens SIG-UI-022, so it needed the operator's words, which
  this ADR records.
- **A national node-link canvas as the default.** Rejected at A-11 ("Also a full national graph" was not chosen), and
  still barred by SIG-UI-021 and ADR-158.

## Revisit trigger

Revisit — by a new ADR, never an edit of this one — when any of these happens:

- an overview the explorer opens on exceeds ADR-158's 3,000-node cap or loses its aggregation rule, or an overview node
  is found that does not reach an ego view (stop opening on that overview until it is fixed);
- a reader report, a REVIEW-R11 finding or the operator's walkthrough shows the overview default being read as a
  complete national graph or as a ranking;
- the explorer's landing state fails no-JS parity, or misses ADR-155's T2 budget on a real release;
- the identity gates of SIG-IDENT-030 pass and centrality or rankings are proposed for an overview (ADR-158's trigger);
- the operator asks for the ego default back.
