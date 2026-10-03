# ADR-136 — The research-dossier schema: `sig.dossier-packet/1` → `sig.research-dossier/1` → `sig.dossier-portfolio/1`, a distinct eleventh artifact class (P32.17)

- Date: 2026-10-02
- Status: accepted (engineering; publication and live deployment stay gated — the review mark is never fabricated)
- Ticket: P32.17 (Round 10 / S2, row 178; requirements SIG-DOS-001, SIG-DOS-002)
- Base: the P32.16a chain tip `devin/p32-16-reviewed-correction-application` (PR #173)

## Context

The six-stream plan needs three *evidence-complete* local dossiers whose
every answer is reproducible from captured bytes — not the §39.2 inventory
overviews, which are shaped mechanically from published claims and cannot
answer "who operates it, under what authority, what does SIG not know, and
what would close each gap". Without a schema the known failure modes recur:
a blank field inflates completeness or silently implies absence; an
unsupported affirmative claim ships; a template MOU reads as an executed
agreement; a subscription reads as owned hardware; two same-scope counts
collapse into one definitive number; a posting date promotes to an
effective date; and "no record found" becomes "no system". Each is a
fabricated-certainty failure the defining standard (§3.1) forbids.

## Decision

**`exports/src/exports/research_dossier.py` owns the canonical
research-dossier contract — three wire schemas, a six-state answer
vocabulary, a fact-to-capture ledger, an independent completion checklist,
a fixed twelve-question rubric, and fail-closed release validation —
consuming the `dossier_documents` connector's emitted records, never
bypassing them.**

1. **Three wire schemas.** `sig.dossier-packet/1` is the authored input
   (subject, as-of pair, emitted `records`, `declared` n/a/withheld/derived
   answers, `search_log`, `follow_ups`, `restricted`, `review`).
   `sig.research-dossier/1` is the composed dossier.
   `sig.dossier-portfolio/1` wraps the set for the export. `build_spine_export`
   accepts `dossier_packets` and emits `web/research_dossiers.json` only when
   packets are supplied — absent input emits no artifact (honest absence).
2. **Six answer states, never a blank.** Every one of the twelve questions
   renders exactly one state — `supported`, `disputed`, `derived`,
   `unknown`, `withheld`, `not_applicable` — plus a 0–3 rubric score, a
   summary, and its basis. An undocumented unknown's mechanical fill reads
   `not_researched` (the honest worst basis, never a fabricated
   `searched_not_found`).
3. **The fact-to-capture ledger.** Every rendered fact carries
   claim_digest + capture_digest + locator + source_url + retrieved_date —
   the citation a reader can open. A withheld row keeps only the digest;
   the value never leaks into the rendered dossier.
4. **Conflict is classification, not reconciliation.** Same-scope,
   overlapping-window, non-equal claims flip the answer to `disputed` with
   every competing value marked `≠`. Differing scopes are not a
   contradiction — they render co-visible with scope labels. Verbatim
   predicates (clause texts, e.g. `use_restriction`) never conflict: two
   different stated rules are two rules.
5. **Fail-closed release validation.** A dossier is release-invalid on:
   `unsupported_affirmative_claim` (rendered claim without capture/locator/
   digest), `misclassified_instrument` (template asserting
   executed-instrument predicates; subscription asserting local-hardware —
   the emit guard's release-side twin, mirrored verbatim from the connector
   TOML and drift-checked by test), `absence_fabricated` (documented
   not-found on a question holding evidence claims), `blank_answer`,
   `unknown_without_basis`/`unknown_without_followup`,
   `not_applicable_with_evidence`, `withheld_without_basis`,
   `derived_unresolved_inputs`, `derived_hides_conflict`,
   `restricted_claim_rendered`. An honest researched unknown — named
   sources, a documented outcome, a follow-up with a testable closing
   condition — passes.
6. **The rubric and the portfolio gate.** Per-question 0–3: 0 unresearched,
   1 documented unknown, 2 traceable partial, 3 scoped answer.
   `mechanical_complete` = total ≥ 28/36 AND q1/q5/q7/q8 ≥ 2 AND no release
   violations. `pilot_complete` additionally requires
   `review.status == "completed"` — the machinery never fabricates the human
   mark (the independent review is D-R10-HUMAN-1-scoped work).
7. **An eleventh artifact class, not an eleventh frozen surface.** The
   P27.1 contract doc
   (`docs/build/reports/public_surface_contracts.schema.json`) is frozen to
   exactly ten surfaces by `test_public_surface_contracts.py`; the
   portfolio is governed by its own `sig.*` schema ids and the
   `exports.research_dossier` contract tests rather than by an in-place
   edit of the frozen artifact. The web renders it at `/research-dossier/`
   (index, detail, JSON), marked distinctly from the inventory overview —
   which now carries `kind: "inventory_overview"` on its JSON and a marker
   line on its page.
8. **Evidence-backed gaps.** The §39.2 overview's hardcoded
   "Data-sharing partners / NOT_RESEARCHED" row is replaced by gaps derived
   from recorded `coverage_record` negative-space rows (absence kind +
   searched sources); a spine with no recorded absences emits zero gaps.
9. **Original dates stay distinct.** `valid_from/valid_to/valid_edtf` and
   as-of/posted values are the document's own dates; `retrieved_date` /
   `observed_at` are capture dates. Both render side by side — a posting
   date never promotes to an effective date.
10. **Print/no-JS fidelity.** `render_dossier_print_html` paginates the
    dossier with the same qualifiers, scope labels, date pairs, conflict
    markers, citations, checklist and rubric as the JSON and the web page —
    a paper copy stays citable (per-page footer: dossier id + as-of pair +
    score + review status + schema id).

## Alternatives considered

- **Extending the §39.2 `Dossier` contract in place.** Rejected: the
  overview is a mechanically-shaped aggregate; bolting per-question
  states/bases/ledger rows onto it would blur the exact distinction the
  ticket draws between an inventory overview and a reviewed dossier — and
  would force every existing dossier through the new validation.
- **A second, web-only schema.** Rejected: the web mirrors the export
  contract verbatim (`web/src/lib/research-dossier.ts`); a forked shape
  would be "a different dataset wearing the same name" (§38.1).
- **Adding `research_dossier` to the frozen ten-surface contract doc.**
  Rejected: the doc's own test pins exactly ten surfaces; the portfolio
  schema ids and contract tests carry the contract instead.
- **Soft-failing release violations as warnings.** Rejected: an
  unsupported affirmative or a hidden conflict is precisely the fabricated
  certainty the ticket exists to prevent; warnings would let it ship.

## Revisit trigger

A pilot dossier needs a seventh answer state (e.g. a distinct "correction
pending" state), the rubric gate is recalibrated after the first
independent review campaign (D-R10-HUMAN-1 evidence), a future contract
ticket adds the portfolio to a versioned public-surface schema, or a
live-verification pass (`live_verification=true`) shows the
capture/locator binding rule mis-sized for real packets — revisit under a
new ADR or scoped amendment, never an in-place edit.
