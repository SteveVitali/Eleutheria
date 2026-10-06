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

### Consolidated round — operator answers, verbatim (2026-09-30T21:58:23Z)

| id | item | operator, verbatim |
|---|---|---|
| U-004 | C-1 what works / keep | *"I like how technically precise the language is and how clear the definitions, editorial standards, methodology, etc. are articulated, so that the project can pass open source scrutiny muster."* |
| U-005 | C-2 would you send it | *"I would not share https://surveillancegraph.org/ as it exists today mainly due to how confusing and verbose the information on the UI (all the things already covered in an earlier long response from me); journalists need to be able to really truly explore the knowledge graph, answer questions that they might have by querying/exploring the data interactively, always with full explicit transparent evidence/lineage/etc."* |
| U-006 | C-3 trust | *"I'm not that confident because I haven't done a deep audit of the mechanism by which disparate sources with disparate schemas are synthesized into a deduplicated knowledge graph of relations between entities."* |
| U-007 | C-4 outcomes and scope | *"the main outcomes we want are feature richness (beautiful and useful and intuitive UI/UX that makes it possible to query/explore/navigate the knowledge graph interactively in powerful ways, while maintaining strict standards of evidence/lineage/etc.), correctness and comprehensiveness of the knowledge graph data itself (expansion of _high quality_ sources to maximal degree and increased confidence in algorithms used to turn raw ingested data into synthesized knowledge graph), and generally it just needs to be better at making itself as a website/platform clear to the user so that anyone who visits the site has a beautiful experience and is able to intuitively navigate its rich functionality and so on while also making it very clear what the project is and why it exists and what its capabilities are and so on. And on dataset coverage questions, use your best judgement, but the focus is on rich, US nationwide data on Flock and Axon and likely other vendors which you can use existing or new repo or web research to discover and make judgements about."* |
| U-008 | C-5 resources | *"don't worry about time limits; ideally we can keep monthly compute/storage/hosting/etc. costs below $300/mo, basically as low as possible, but we are flexible here, and certain features may merit spending upwards of $1,000/mo if we absolutely have to, but we need to take care to reason about these tradeoffs carefully and always check with me before proceeding with increased spend above $300/mo; otherwise, for now, assume we have no humans on our team other than me augmented by agents running frontier models."* |
| U-009 | C-6 visibility | *"we will announce surveillancegraph.org publicly without holding back when the time is right."* |
| U-010 | C-7 red lines / reopen | *"nothing to note for now."* |
| U-011 | C-8 autonomy | *"agents should have maximal autonomy but budgets on money spent should always be made clear and transparent to human who approves any budgets or increases, and no one should be contacted outside the project."* |
| U-012 | C-9 process | *"previous builds worked pretty well so we can follow the existing patterns."* |
| U-013 | F-1 counsel | *"\"counsel\" so far is just me (Steven Vitali), we don't have counsel and for now we should just err on the side of not blocking on counsel decisions."* |
| U-014 | F-2 contact string | *"contact should always just be Steven Vitali at 14stevevitali@gmail.com for now, but actually, maybe we do want to set up a contact@surveillancegraph.org email."* |
| U-015 | F-3 harness history | *"I have no idea about these questions about round 9 and 10, but the strongest likelihood is that it was Devin who drove this build, but I'll need you to carefully investigate and sort these questions out on your own."* |

**Agent interpretation (labelled; to be ratified at S5):**
- U-005/U-007: the journalist exploration journey ("query/explore the data interactively … always with full explicit
  transparent evidence/lineage") becomes a primary acceptance journey alongside the design-center advocate (U-002).
- U-006/U-007: confidence in the synthesis pipeline (ingest → claims → resolution/dedup → reconciliation → materialized
  graph) is an explicit outcome → new **Stream L** (audit, measurement, confidence program).
- U-007: "beautiful", intuitive, and clear about what SIG is/why/capabilities → new row **K14** (visual design + onboarding
  narrative); coverage priority = US-nationwide Flock/Axon/other vendors (feeds I8 ordering).
- U-008 + U-011: cost ceiling **$300/mo** without approval; anything above needs the operator's explicit go with the
  trade-off shown; **no humans besides the operator** → independent human evaluation (F4 Option B) is infeasible → re-plan in
  Stream L; recruiting (Q-28) = no; **no outside contact** → Stage-0 outreach, records-request sending, contribution-back
  posting and volunteer recruiting are not done (waiver/deferral candidates at S5).
- U-011: "maximal autonomy" for agents within those limits (money transparency; no outside contact) — informs Round-11 gates.
- U-013: past "counsel" records were the operator's own determinations → records and public text must stop implying counsel
  exists (record-integrity + honesty fix); counsel-dependent spec MUSTs → waiver candidates ("don't block on counsel").
- U-014: the operator's address is the approved project contact string for services that require one (amends P16); a
  `contact@surveillancegraph.org` alias is to be planned (ops ticket).
- U-015: harness attribution for untrailered Round 9–10 commits to be established by the agent → new row **B7**.
