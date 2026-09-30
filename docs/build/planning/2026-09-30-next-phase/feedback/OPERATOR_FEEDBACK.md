# Operator feedback — D1 (unanchored) and D2 (reactions)

Collected interactively in the Claude Code planning session, one question at a time (operator decision, META_PLAN §7.1).
Operator answers are recorded **verbatim** with `U-nnn` ids. Anything the agent drafts is labelled **agent-drafted**
and stays provisional until the operator confirms or edits it. Corrections are appended, never overwritten.

Note on anchoring: before D1 began, the operator had already seen the 2026-09-30 orientation summary (production and
memory findings). D1 is unanchored with respect to the Stream-C browser review (C2/C6), which has not been shared.

## D1 answers

### U-001 — Q-D1-01 · What is SIG for?
- **Operator, verbatim (2026-09-30T17:10:49Z):** *"As for what SIG is for, you can draft that yourself."*
- **Agent-drafted answer (on the operator's delegation; drawn from spec §1.1–1.4 — pending operator confirmation):**
  SIG is a public, evidence-first reconciliation layer over the surveillance-transparency ecosystem. It joins independent
  public sources — crowdsourced maps, agency and vendor disclosures, contracts, policies, grants and records releases —
  into one graph that shows what surveillance capabilities exist where, who controls and can access them, what rules and
  contracts govern them, how that has changed over time, and exactly which evidence supports or contradicts each claim.
  It is built first for a local advocate who needs a printable, sourced dossier before a council meeting, and it links to
  existing projects rather than rebuilding what they already do well.
- **Status:** **confirmed by the operator** (2026-09-30T17:29:54Z), verbatim: *"I confirm U-001."*

### U-002 — Q-D1-02 · Is the design-center user still who we build for first?
- **Operator, verbatim (2026-09-30T17:29:54Z):** *"yes for Q-D1-02 but also think investigative journalists and other organizers"*
- **Agent interpretation (labelled):** the local advocate with a council meeting in days stays the design center
  (SIG-UI-002), with **investigative journalists** and **other organizers** as co-primary audiences to design for —
  C1's personas already include a journalist (P9) and organizer-like roles; D3 decides how "co-primary" changes priorities.

### U-003 — Q-D1-03 · What should a first-time visitor be able to do or find out within 10 minutes?
- **Operator, verbatim (2026-09-30T21:28:52Z):**
  *"A first-time user of SIG should be able to do all of the things currently advertised / attempted on the current
  surveillancegraph.org deployment but the functionality should actually work the way a user expects in terms of UI/UX,
  features, and so on. For example, but not limited to: (1) the current Infrastructure map at "/map" does not even display a
  map layer so it's just a zoomable pane with a bunch of dots on it with no indication of where those dots actually are; (2)
  the network explorer is confusing and very opaque, for one thing, the UUIDs are meaningless, e.g.
  '01a0d751-0901-7a6c-8789-06bab8c7456e' should be replaced with something human-readable, and perhaps these can link to
  detail pages with metadata on the underlying referenced entity, or whatever makes sense, and moreover, I think we would
  strongly prefer a global graph or set of graphs, perhaps searchable/navigable or perhaps not that truly lays bare all that
  we know and makes it explorable -- and we need to think and research and reason carefully about perhaps breaking with our
  no-JS constraints to buil these features and related ones; (3) the search functionality at "/search" is extremely crude
  and naive, and ideally a user would be able to search in a much more flexible way across the whole knowledge graph, of
  course we don't have to boil the ocean for the first pass, but we can definitely improve over what we have; (4) the
  "/dossier" list should be grouped by country so that US states are grouped together under US and clearly separate from
  country-specific dossiers; (5) on individual dossier detail pages users should be able to browse/explore what sources
  contributed what when to this jurisdiction and perhaps navigate to details for these sources and their ingestion and so on;
  (6) individual jurisdiction dossier pages should probably also include by default some sort of network and/or map-based
  visualization(s) for interactive exploration and perhaps also search; (7) it's not clear that the "/watch" feature
  actually works, so we should probably do some QA there; (8) the "/evidence" page doesn't actually seem to show anything
  yet, but this may just be that everything is stuck in the research queue; (9) the "data-freshness" section should have
  downloadable source data links per source, ideally even the ability to browse and download versions of the data ingested
  for a particular source across time, but bare minimum, the source list should have sortable columns and include links to
  downloadable data of most recent ingested data for that source as well as additional ingestion metrics and metadata about
  what was ingested and how much, and ideally also link to the 'ground truth' source URL or homepage or whatever for where
  we got this data from the internet; (10) individual sources from the 'data freshness' table should be clickable and the
  user should be able to view full details for a particular source, including all the metadata from the data freshness
  table for that source and more as well as ingestion history and ideally downloadable links for each ingested file and
  whatever else; (11) the Research queue as-is is currently unusable, bare minimum the UUIDs like
  01a0a720-9b9a-7890-a8ae-99705e6b5368 need to be replaced with human readable identifiers and linked to detail page. Please
  make sure that you very carefully and systematically log and do dedicated reseacrch/design/synthesis/etc. for every single
  one of these specific asks. But more generally, keep in mind that the high-level general ask is that the site be more user
  friendly and have richer, more interactive, searchable, traversable, inspectable, etc. functionality, so that as much about
  what the data says, where we got it from, etc. is as laid bare as possible. You should use your own critical judgement and
  proactively and creatively come up with your own ideas, as well, based on your own web research and your own agentic
  browser-user of https://surveillancegraph.org/ itself to augment the full additions to the plan"*
- **Decomposition (agent, labelled; each item maps to a dedicated Stream-K row in META_PLAN §6):**

| id | operator ask (paraphrase; verbatim above) | Stream-K row |
|---|---|---|
| U-003.1 | `/map` has no basemap/place context — needs a real map | K1 |
| U-003.2 | network explorer opaque: human-readable labels not UUIDs, entity detail pages, a global graph (or set of graphs), searchable/navigable, laying bare all we know; research whether to break the no-JS constraint | K2 (+ K0) |
| U-003.3 | `/search` crude — flexible search across the whole knowledge graph (incremental first pass OK) | K3 (+ K0) |
| U-003.4 | `/dossier` list grouped by country (US states under US, separate from country dossiers) | K4 |
| U-003.5 | dossier pages: browse which sources contributed what, when; navigate to source + ingestion details | K5 |
| U-003.6 | dossier pages: default embedded map and/or network visualizations for interactive exploration, perhaps search | K6 |
| U-003.7 | `/watch` may not work — QA it | K7 |
| U-003.8 | `/evidence` shows nothing — diagnose (maybe stuck in the research queue) | K8 |
| U-003.9 | data-freshness: sortable columns; per-source latest-data downloads; ideally versions over time; ingestion metrics/metadata; ground-truth links | K9 (+ J3) |
| U-003.10 | per-source detail pages: all freshness metadata + ingestion history + per-file downloads + more | K10 (+ J3) |
| U-003.11 | research queue unusable: human-readable ids + detail pages | K11 |
| U-003.G | general: more user-friendly, richer, interactive, searchable, traversable, inspectable — lay bare what the data says and where it came from | K12, K13 |
| U-003.X | agent to add its own ideas from web research and its own browser use of the live site | K12a (web research), K12b (browser) |

- **Decisions implied (to ratify at S5):** reverses the Round-9 "no basemap" answer (Q8, 2026-09-24) → new ADR at T1; the
  zero-JS-on-content-pages rule (AGENTS.md gotcha 6; ADR-068/091/097/134; SIG-UI-036/050) to be re-decided through K0.
- **Note on anchoring:** by U-003 the operator had seen several S0 findings reported during Stage P (not the C6 synthesis).
