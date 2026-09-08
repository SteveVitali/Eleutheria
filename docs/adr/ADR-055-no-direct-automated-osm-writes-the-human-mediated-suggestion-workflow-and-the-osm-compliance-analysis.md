# ADR-055: No direct automated OSM writes — the human-mediated suggestion workflow and the OSM compliance analysis

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P16.2
- **Records:** the compliance analysis the canonical spec's Appendix F calls **ADR-017**
  ("No direct automated OSM writes", §35.2). The repository numbers ADRs sequentially as
  tickets land, so the spec's conceptual ADR-017 is recorded here as repo ADR-055; repo
  ADR-017 (FastAPI) is unrelated.
- **Requirement ids:** SIG-CONTRIB-014, SIG-CONTRIB-015, SIG-CONTRIB-015a, SIG-CONTRIB-015b,
  SIG-CONTRIB-016, SIG-CONTRIB-016a, SIG-CONTRIB-016b, SIG-CONTRIB-016c, SIG-CONTRIB-016d,
  SIG-CONTRIB-016e, SIG-CONTRIB-016f, SIG-CONTRIB-016g, SIG-CONTRIB-017, SIG-CONTRIB-017a,
  SIG-CONTRIB-018, SIG-CONTRIB-020; SIG-LIC-007a, SIG-LIC-007b, SIG-LIC-007c
- **Spec:** docs/2_canonical_design_spec.md §35.2 (to OpenStreetMap), §35.3 (to other projects),
  §7 / §32.6 (the leverage metric), §42.3a (the contribution licence conflict)
- **Relates to:** ADR-011 (the ODbL posture — the separate ODbL asset compartment this contributes
  back to), ADR-027 (the OSM connector + ODbL landing), ADR-048 (the export licence compartments
  and `compute_export_license` reused by the contribution gate), ADR-054 (the contributor system
  and the suggestion-not-write posture of SIG-CONTRIB-011b this generalises), ADR-047 (the read API
  the per-claim attribution extends)

## Context

P16.2 owns contribution back to the ecosystem (§35). The design has one non-negotiable
shape — SIG proposes, a human decides — and two OSM compliance surfaces that shape it.

1. **The Automated Edits Code of Conduct scope test is the whole answer.** The Code
   covers *"all edits where changes are made to objects in the database without review
   individually by the person controlling the edits"*, and explicitly names Overpass-driven
   bulk retagging. Operator attribution is **not** within any of the Code's exceptions
   (those are blatant typos, reverting vandalism, correcting one's own work, reverting
   unapproved automated edits); adding `operator=*` from contracts and public records is new
   external information, and at ~116,800 candidate nodes it is unambiguously in scope
   (SIG-CONTRIB-016/016a).

2. **The human-in-the-loop workflow is what keeps SIG outside that scope entirely**
   (SIG-CONTRIB-016b) — it is not a cautious alternative to compliance. A mapper reviewing
   each proposed change individually, in their own account, is by definition not making an
   automated edit. There is no version of a SIG bot account that is simpler.

3. **Escaping the Automated Edits Code does not escape the Organised Editing Guidelines**
   (SIG-CONTRIB-016d). A SIG-run task challenge directing volunteers at the backlog is a
   coordinated editing initiative and requires a registered activity page.

4. **The contribution path has its own licence gate** (SIG-CONTRIB-016f, §42.3a), distinct
   from the §42.4 export gate: publishing a task built on a source whose terms forbid deriving
   an OSM edit would make SIG the proximate cause of a licence breach. OSM additionally does not
   accept plain CC-BY-4.0 without an added waiver, so SIG's contributed subset is dual-licensed
   CC0-1.0 (SIG-LIC-007a).

5. **The engine is modelled in memory, ahead of persistence** — the established
   `tasks`/`policy.governance` pattern (ADR-054): this ticket owns the rules and their tests;
   DB wiring and a live MapRoulette client are downstream.

## Decision

1. **No direct automated OSM writes exist (SIG-CONTRIB-014).** `tasks.contribution` has no
   code path that writes to OSM. `write_to_osm` exists only to raise `AutomatedOsmWriteError`,
   and an `AppliedEdit` cannot record SIG as the applier (a `mapper_account` of "SIG" raises).
   The posture is structural, not a convention a later change could erode by prose.

2. **A MapRoulette cooperative challenge is the verified mechanism (SIG-CONTRIB-015/015a).**
   A `CooperativeChallenge` is `cooperativeType='tags'`; a `TagSuggestion` proposes a specific
   `TagChange` ("this node has no `operator`; SIG's evidence suggests `operator=X`; decide"),
   surfacing the supporting evidence to the mapper. `apply_by_mapper` is the *only* way a
   suggestion becomes an upstream edit — a person decides, in their own account, and may accept,
   reject, or edit. The MapRoulette field crosswalk (SC-15) is documented as
   `MAPROULETTE_FIELD_CROSSWALK`. The account holder and the located API docs are disclosed
   (SIG-CONTRIB-015b).

3. **The compliance analysis is recorded here (SIG-CONTRIB-016/016a/016b/016c).** The scope
   test above is normative: operator attribution is in scope for the Automated Edits Code, the
   exceptions do not apply, and the individual-human-review workflow is what keeps SIG outside
   the Code. If SIG ever proposes a genuinely bulk contribution it MUST first satisfy every
   documented requirement — a proposal page under `Automated edits/<username>`, the exact
   selection algorithm, a consultation record, an opt-out, registration, and a permanent
   community decision on an OSMF-run forum (chat consensus does not count); approval is never
   blanket (SIG-CONTRIB-016c).

4. **A declared changeset hashtag wired to the §7 metric (SIG-CONTRIB-016e).**
   `CHANGESET_HASHTAG = "#sig_operator_attribution"` is required on every SIG-originated edit
   (`checkinComment`), and `LeverageLedger.accepted_operator_attributions()` reads *accepted*
   upstream changesets bearing it — the §7 measure "SIG-originated operator-attribution
   suggestions accepted upstream". Keying on a public hashtag makes the stream third-party
   auditable, which is what turns the metric from an assertion into a measurement.

5. **The Organised Editing activity page is published and registered (SIG-CONTRIB-016d/016g).**
   `organised_editing_activity()` loads `data/organised_editing.toml` into an
   `OrganisedEditingActivity` whose `__post_init__` refuses a disclosure missing the coordinating
   org, contact, hashtag, goal, timeframe, any non-standard tool or data source with its usage
   conditions, or the metrics — which are stated as task **outcomes, not contributor rankings**
   (SIG-CONTRIB-016g). The human-readable, registered page is
   `docs/governance/organised-editing-activity.md`.

6. **The contribution-path licence gate (SIG-CONTRIB-016f, §42.3a).**
   `policy.licensing.assert_contribution_permitted` blocks a source that is `UNDETERMINED`, that
   forbids derivative works, or whose effective licence is not relicensable to OSM's ODbL-1.0 —
   reusing the same `relicensable_to` relation as the export gate. `tasks.contribution.build_suggestion`
   applies it **before** rendering, so a task on an incompatible source is never constructed.

7. **Structural upstream attribution (SIG-CONTRIB-020).** The API `/claim` response now carries
   `attribution` (the upstream named on the claim, not only on an About page), reusing
   `api.envelope.attribution_for`; exports already stamp per-row `_rights`
   (`downstream_obligations`). Per-project correction channels (`PROJECT_CHANNELS`,
   SIG-CONTRIB-018) use each project's own stated submission channel rather than inventing one.

## Consequences

- Automated OSM writes and SIG-as-applier are *unrepresentable* in the API, so a future change
  cannot regress the compliant architecture by prose alone.
- The §7 leverage metric is now measured from a public, hashtag-keyed signal rather than inferred
  from tag-count deltas, and is auditable by third parties.
- The contribution-path licence gate is a distinct, tested boundary; a licence-incompatible source
  cannot silently feed a contribution task.
- A claim's upstream is now named structurally in the API as well as in exports.

## Deviations

- **The system is modelled in memory, not yet persisted, and no live MapRoulette client is
  built.** Consistent with the `tasks`/`policy.governance` pattern (ADR-054). Challenge creation
  against the live MapRoulette API, and reading OSM's changeset feed to populate `LeverageLedger`,
  are tracked downstream in the risk register.
- **The §7 metric is computed but its published surface is P15.5's fixture-backed metrics page.**
  Wiring the live count into that page is a source swap, recorded in the risk register.

## Revisit trigger

Revisit when the contribution path gains a live MapRoulette client and a live OSM changeset feed
(so `LeverageLedger` reads real changesets), or if the OSM Automated Edits Code / Organised
Editing Guidelines change materially, or if counsel advises differently on the §42.3a residuals
(the CC0 contributed-subset posture). Any change to the declared changeset hashtag, the
no-automated-write posture, or the contribution-path licence gate is a spec amendment
(SIG-ENG-003), not an edit here.
