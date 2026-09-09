<!--
TICKET DOC TEMPLATE — do not run this file. Copy for each ticket; fill every field.
These docs are a DERIVED BUILD ARTIFACT of docs/2_canonical_design_spec.md. They CITE canonical
sections, never copy their design. To change a requirement, amend the canonical spec (SIG-ENG-003),
not the ticket. Ticket files own only: scope framing, ordering, and the AC subset for this unit.
-->
# <TICKET-ID> — <short title>

- **Sequence:** <n> of N
- **Phase:** <Part X phase name>
- **base_branch:** current checkout — the branch the previous ticket left checked out (stacked PR chain); `main` for P00.1
- **Depends on (must land earlier in the stack):** <prior TICKET-IDs, or "P00.1 skeleton only">
- **Run:** `implement-spec spec=docs/tickets/<file>.md`   # base = current branch → PR stacks on the previous ticket

## Goal
<One or two sentences: the single coherent, independently-landable concern this ticket delivers.>

## Load (read these canonical sections — do not re-read others; SIG-ENG-001)
- `docs/2_canonical_design_spec.md` §§ <list>
- Always-in-scope context: Part 0, Part I §3 (invariants), Appendix E glossary.
- Companion research cache (only if a cited § points into it): `docs/research/<Rn>...`

## In scope — deliverables
1. <deliverable> — <the canonical requirement IDs it satisfies, e.g. SIG-STORE-00X>
2. ...

## Out of scope (scope-creep guard — do NOT do these here)
- <thing a later ticket owns; name the ticket>

## Acceptance criteria (testable; from the phase's Part X ACs, sub-set to this ticket)
- [ ] <AC>  — *(deterministic | agentic)*
- [ ] ...
- [ ] **Phase-gate (§51.3):** CI green incl. data-quality checks; new requirements have automated tests (SIG-ENG-004); ADRs written for any deviation; traceability matrix updated; risk-register entries for this phase updated. *(deterministic)*

## Requirement IDs to satisfy and stamp in the PR (Definition of Done §0.6)
<SIG-XXX-000, ...>  — each must appear in the commit/PR and be covered by an automated test.

## Cross-cutting invariants — re-check before opening the PR (apply to EVERY ticket)
- **Defining standard (§3.1):** no unexplained dots/edges; no silent overwrites; no synthetic certainty; every node has identity; every state has time; every claim has evidence; every inference is labelled; every contradiction stays visible.
- **Part VIII is binding (§0.7):** no plate/trip/per-person storage or lookup; officer-naming test gates any person-named claim; sensitivity tiers + coordinate rules enforced; licence gate + ODbL separation hold.
- **Append-only & provenance (P1–P3):** no writable "current value" columns; raw_value preserved; corrections are new assertions, never overwrites.
- **Additive/back-compat:** do not break a prior ticket's wire names, IDs, or schema contracts; new fields optional with today's-behavior defaults.

## Notes
<Any shared decision this ticket OWNS that later tickets reference; any anchor to re-confirm at build time.>
