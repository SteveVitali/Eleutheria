# ADR-245 — Detector routing by the predicate table; catalog rows 35/36; `predicate_ids` + supersede-by-disposition (P37.35)

- Date: 2026-11-11
- Status: accepted
- Ticket: P37.35 (K11 RQ-02, manifest row 459 — on `r11/P37.35-detector-routing`)
- Base: `r11/P37.34-watch-feeds-v2`
- Requirement stamps: SIG-RQ-005, SIG-RQ-006 (cited — owned by P36.58), SIG-TASK-002/003/007/008, SIG-STORE-041/042, §33.2 rows 35/36
- Decision implemented verbatim: `D-K11-1 [B-22] = as recommended` (GATE-G6 §4, 2026-11-05T15:20Z)
- Supersedes: nothing

## Context

K11 measured the research queue (RC-2/RC-3/RC-4): per-subject peer-class
negative space floods it (~243k per-camera `coverage_hole` rows = 99.7%), the
coverage router is a substring match that sends retention/sharing gaps to
`missing_contract` (whose closing text asks for a procurement record), and
contradiction/stale-edge candidates mint with jurisdiction `None`. P36.58
landed the committed `gap_routing.toml` predicate→lane table and declared
`retention_unknown`/`sharing_unknown` catalog-pending. D-K11-1 was answered
**"as recommended"**: OSM-mappable field gaps present as aggregated mapping
campaigns; registry-only field gaps stay coverage metrics; per-object field
gaps are never individual research tasks.

## Decision

1. **The routing table is the detector's authority (SIG-RQ-005).**
   `tasks.detect` routes every coverage gap through `gap_routing.toml`. A
   per-object gap (§32.1 peer-class subject) follows its declared lane:
   `research` mints the asserted task type and records `predicate_ids`;
   `campaign`/`metric` never mint a task. A predicate the table does not name
   keeps the pre-RQ-02 records-obtainable fallback — the matrix test pins
   every tracked predicate, so the fallback fires only off the declared
   surface.
2. **Catalog rows 35/36.** `retention_unknown` and `sharing_unknown` join
   §33.2 (spec amended: catalog enumerates 36; Phase-10 AC note appended;
   corrections row R11-X4). Both are `records_requester`/jurisdiction-scoped
   with testable closing conditions (SIG-TASK-002/003).
3. **`research_task.predicate_ids text[]` + `disposition_reason text`**
   (additive sqitch `research_task_predicates`; nullable, no default —
   SIG-STORE-042).
4. **Jurisdiction attribution.** The materialize read supplies a
   subject→jurisdiction map from evidenced claims whose `object_entity` is a
   `jurisdiction:`-keyed entity; contradiction, stale-edge, coverage and
   contract candidates mint placed where attributable, else `unplaced` (K4).
5. **Campaign aggregation.** Per-object campaign-lane gaps aggregate by
   `(jurisdiction, predicate, subject_class)` in the run; the export derives
   campaign members from the materialized coverage rows directly (card members
   dedup on subject, never double-counted), so superseded per-camera rows stay
   history while the campaigns live on.
6. **Supersede by disposition, never a delete.** Persisted `coverage_hole`
   rows citing a campaign/metric-routed coverage record, and rows whose
   recorded type differs from the table's asserted `route`, get
   `status='closed'` + `disposition='superseded'` + a recorded reason via the
   new column-scoped `UPDATE` grant to `sig_materialize` — the
   `disappearance_event_grant` event-surface precedent: the disposition is the
   designed update surface, every other column and DELETE stay un-granted.
   Closed/superseded rows leave every public queue lane.

## Consequences

- A detector re-run over an unchanged spine stays +0/idempotent: dedup holds,
  already-superseded rows are terminal.
- The named mutation (the hosted detector re-run) is OM-20 gate-pending: it
  ran only under a GATE-G6 pre-authorisation window (AR-3 + AR-2); this
  engineering dispatch records `QUEUED prepared_not_executed` while the AR-3
  monthly batch window (days 6–13) is open.

## Revisit trigger

Revisit when: the first post-change hosted detector re-run reports a
supersede/write count materially divergent from the dry projection; a peer
class or routing row is added that makes the lane vocabulary insufficient;
MapRoulette registration (HG-08) turns campaigns into live challenges; or a
§33.2 count change requires a further spec amendment.
