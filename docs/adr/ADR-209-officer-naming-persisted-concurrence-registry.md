# ADR-209 — The persisted officer-naming concurrence registry and the default-deny publication gate (P35.28 — R11-SAFE-03; SIG-PUB-007 owner; cites SIG-PUB-008/009/010/017, ADR-163)

- **Date:** 2026-10-14
- **Status:** accepted
- **Ticket:** P35.28 (Round 11 / P35, sub-round 11B, manifest row 286 —
  officer-naming gate on the publication path, default deny)
- **Base:** `r11/P36.11-grant-council-procurement-documents-bills`
- **Related:** ADR-163 (the sole-maintainer posture — SIG-PUB-008 stands,
  nobody is named, the HG-11 second-reviewer role is waived for Round-11
  releases only), ADR-124 (the `publication_disposition` spine mirror a
  committed policy table rides), ADR-066/ADR-011-era precedent
  `sig.publication-withdrawals/1` (P34.19 — the committed append-only data
  table read verbatim by both the Python policy layer and the TypeScript web
  layer), ADR-152 (no agent-produced label is a human label), SIG-MEM-009.

## Context

§43.4's officer-naming test (SIG-PUB-007's five prongs + SIG-PUB-008's two
independent reviewers concurring in writing, decision recorded) ran only at OKC
ingest (`connectors.okc_documents.assert_person_naming_permitted`). The export
and web publication path applied only the SIG-PUB-017 jurisdiction rule, so a
public-employee-name row could render on jurisdiction alone — E2's H-9 gate
half and F2a §5 group 1's AT-RISK-INTEGRATION finding, plus E1/NEW-12 (the same
defect class, latent while `/dossier/okc/` 404s: `web_dossier.py` hard-coded
"Chief Wade Gourley" shown and `publication.test.ts` asserted a US name is
publishable).

Two further findings landed at build time:

- The web gate was bound at the page only (`dossier/[slug].astro`); the print
  export (`dossier/[slug]/print.astro`) and the JSON endpoint
  (`dossier/[slug].json.ts`) read `getDossiers()` ungated — three surfaces, one
  of them gated.
- The web mirror's jurisdiction map (`web/src/lib/publication.ts`) carried only
  US/FR/BE while `policy/data/jurisdictions.toml` knows US/US-CA/UK/EU/FR/DE/BE
  — the missing codes fell through to the conservative default, so the mirror
  drifted narrow, never permissive.

No recorded two-reviewer naming concurrence exists: the operator's
`docs/build/reports/okc/concurrence.md` posture fills both reviewer roles with
the same person — not independent — so `_concurrence_ok` correctly answers
False. The naming concurrence stands as the operator's recorded human act
(SIG-MEM-009); WV-03/ADR-163 waived only the HG-11 second-reviewer *role* for
Round-11 releases, never the naming rule.

## Decision

1. **The persisted carrier is a committed, append-only data table.**
   `policy/src/policy/data/officer_naming_decisions.json`
   (`sig.officer-naming-decisions/1`) holds one entry per recorded §43.4
   evaluation — subject/predicate match keys, the five prongs' stored
   evaluations, the reviewers' written positions, the carve-out flags, the
   verdict and its reason, `date -u` recording stamps, and a `supersedes`
   pointer for a changed decision. It follows the `sig.publication-withdrawals/1`
   precedent exactly: data, not code (SIG-LIC-004a), read verbatim by both the
   Python policy layer (`policy.officer`) and the TypeScript web layer
   (`web/src/lib/officer-naming.ts` static-imports the one file, never a copy).
   A recorded decision mirrors onto the spine as `publication_disposition` rows
   (ADR-124, `policy_version` `sig.officer-naming-decisions/1`) when a live
   spine carries the claim — the file registry is the build-time carrier the
   static export/web path reads.

2. **The gate replays, never trusts the flag.** `OfficerNamingRecord` carries
   the evaluation's inputs so the publication gate re-runs
   `evaluate_officer_naming` over them (`evaluate_record` /
   `replayNamingDecision` on the web side). A record claiming a permit whose
   stored prongs/reviewers do not concur is inconsistent and withholds — as do
   a missing record, a stored deny, a failed prong, a single reviewer, a
   dissent, missing rationale, and the `home_address`/`routine_audit_row`
   carve-outs (SIG-PUB-009/010 preserved verbatim through the record). The
   latest entry in append order governs; append order IS supersede order.

3. **Composition is a conjunction, both legs or withhold.**
   `policy.officer.employee_name_publishable` /
   `applyPublicationPolicy` require a persisted concur record naming the row's
   `(subject_id, predicate_id)` AND `publication_permitted`'s jurisdiction leg.
   The gate only ever withholds — it never newly permits (Part VIII §0.7).

4. **The gate binds at the builder and at the data funnel, not the page.**
   `exports.web_dossier.build_web_dossiers` post-passes every emitted dossier
   through the gate (`_gate_public_employee_names`): a withheld row keeps its
   label, clears its value, and records the refusal reason — never silently
   dropped (§3.1). `web/src/lib/data.ts` `getDossiers()` applies
   `applyPublicationPolicy` to every dossier it returns, so the print export,
   the JSON endpoint, and the page all inherit it; the page-level call stays as
   an idempotent second enforcement.

5. **The ingest evaluation emits the same record.**
   `assert_person_naming_permitted` gains additive `subject_id`/`record_sink`/
   `recorded_by` kwargs (existing callers unchanged — `okc_claim` passes the
   sink through), emitting permit AND refusal records via
   `decision_to_record` so ingest-time evaluate and publish-time gate can never
   diverge. `append_decision` is the only write path to the registry:
   schema-checked, consistency-replaying (the stored flag is refused when it
   disagrees with a replay of the record's own inputs), duplicate- and
   orphan-`supersedes`-refusing — the recording act's machinery, used by the
   operator's recorded two-reviewer act, never an agent signature.

6. **The web mirror map is aligned to `jurisdictions.toml`.** The
   `PUBLIC_EMPLOYEE_NAMES_PUBLISHABLE` table names the full committed set
   (US/US-CA/UK true; EU/FR/DE/BE false; unknown → false) and the adapter set
   gains UK — parity with the Python policy, jurisdiction semantics unchanged
   (P37.69a owns the matrix itself; this row composes with it).

## Consequences

- Every `isPublicEmployeeName` row on every publishable surface — export
  dossier rows, web dossier page/print/JSON — needs a recorded concurrence to
  show; the committed registry is empty, so the worked "Approving official"
  name renders withheld (honest: nobody has been named through the gate).
- The e2e US leg now asserts the name is withheld and absent from the HTML —
  the asserting test is fixed, not loosened; the FR/BE legs are unchanged.
- A future recorded concurrence is a data append the operator makes through
  `append_decision` (or a hand-edited append the writer validates) — the gate
  picks it up at the next export/web build; no deploy, no code change.
- `decision_to_record`'s `decision_id` is content-derived (sha256 over the
  canonical payload): the same decision object produced at ingest and recorded
  by the operator lands on the same id, so the two paths converge by
  construction.

## Alternatives considered

- **A spine-side `publication_disposition` table only.** Rejected for this
  surface: the static-first shell reads no live API at build (SIG-UI-036), so
  the gate's evidence must be committed bytes. The ADR-124 mirror stays the
  live-spine projection when a spine carries the claim — the file registry is
  the carrier both build paths already share (the withdrawals precedent).
- **Withhold by dropping the row.** Rejected — §3.1: a withheld name is
  rendered as withheld with the refusal recorded, never silently dropped; the
  row keeps its label, `withheld` marker, note naming the failing leg(s), and
  the governing `namingDecisionId` when a record exists.
- **Refuse the build on an unrecorded name row.** Rejected — the dossier is
  the worked fixture; refusing the bundle would make every export/web build
  red while no concurrence exists (the honest default state under ADR-163).
  Withholding is the recorded-design posture the ticket's staging-verified AC
  allows ("refuses (or withholds, per the recorded design)").
- **Keep the page-level gate only.** Rejected — the print and JSON surfaces
  read `getDossiers()` ungated; gating the funnel plus the builder covers the
  whole class (E1/NEW-12), not the one surface the ticket named.

## Revisit trigger

- The first recorded two-reviewer naming concurrence (the operator's human
  act): append through `append_decision`; verify the worked dossier rows show
  with their `namingDecisionId` at the next build.
- A second reviewer joins the project: the ADR-163 posture revises; the
  registry then records *independent* concurrences unchanged.
- A publishable surface that reads dossiers outside `getDossiers()` or
  `build_web_dossiers` appears — bind it to the gate before it ships (the
  funnel coverage is the point; a new reader must not re-open the ungated
  surface class).
- P37.69a changes the jurisdiction matrix — re-align
  `PUBLIC_EMPLOYEE_NAMES_PUBLISHABLE` to `jurisdictions.toml`.
