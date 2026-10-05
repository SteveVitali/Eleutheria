# ADR-140 — The acquisition pilot: family-granularity batch selection, the measurement schemas, and the gate packets (P32.21)

- Date: 2026-09-27
- Status: accepted (engineering; the bounded live slices, rights decisions and the matched comparison stay gated — `live_verification=false`)
- Ticket: P32.21 (Round 10 / S5, manifest row 182; requirement SIG-ACQ-004)
- Base: the P32.20 chain tip `devin/p32-20-san-diego-evidence-dossier` (PR #177)

## Context

SIG-ACQ-004 asks for a *measured* gap-closing acquisition pilot: select a
small first batch from the P32.11 reviewed queue after P31 reconciliation,
prioritizing dossier missing relationships and independent evidence
lineage; execute approved bounded live slices *or* produce exact gate
packets; record the capture/extraction/link/publication funnel plus
maintenance burden; and recommend continue/stop/improve per family.

The ticket's bounded live stage caps the pilot at ≤2 incremental
non-portfolio families, ≤10 approved documents/aggregate rows per family,
≤2 new protocol families, and ≤5 total families *including the three pilot
cities*. `live_verification=false` and no approval reference exists
anywhere in the queue — every rights lane is `undetermined` — so the live
obligation is gate packets pinned to OPEN return-pass rows, never
executed slices.

The design questions this ADR resolves:

1. **What is a "family" for the ceiling count?** The inventory's 27 rows
   are targets, not publishers; the only unit the three-pilot-city
   constraint can count is the *institutional provenance family* — the
   queue's `lineage_group` (okc-municipal, tulsa-municipal,
   san-diego-municipal are the three pilot-city families; all three San
   Diego municipal candidates are ONE family).
2. **Which two incremental families?** The S5 research prescribes testing
   two different acquisition *shapes* — one structured
   funding/acquisition family and one independent oversight family —
   while the ticket prioritizes dossier missing relationships and
   independent evidence lineage. A deterministic rule must reconcile
   both and survive re-derivation.
3. **Where does SRC-027 sit?** It is *inside* the san-diego-municipal
   family but must stay *outside the acquired batch* — the exclusion is
   per-candidate within a selected family, not a family rejection.
4. **How does the funnel stay honest?** Offline fixture replay proves the
   machinery works, but `captured_live` is 0 everywhere; measured minutes
   are never fabricated; and the preregistered matched comparison was not
   run, so everything is descriptive only.
5. **How does a selected family handle in-family members?** A provenance
   family (e.g. oklahoma-state) can hold an acquisition-shape winner, a
   P0-dossier authority candidate, and award-discovery members whose S5
   precondition is unmet — the slice membership and the in-family
   exclusions both need a recorded rule.

## Decision

**`tasks.acquisition_pilot` — one deterministic pilot stage over the P32.11
reviewed queue emitting five versioned artifacts, with the batch selected
by `acq-pilot-select/1` and every invariant fail-closed.**

1. **Family = `lineage_group`.** The ≤5-family ceiling counts provenance
   families: the three pilot-city municipal groups (portfolio, fixed by
   P32.18/.19/.20 — measured, never re-selected) plus ≤2 selected
   incremental groups. Within a selected family, the acquired-batch slice
   names its member candidates; in-family members outside the slice are
   recorded as exclusions, exactly as SRC-027 sits inside
   san-diego-municipal but outside the acquired batch.

2. **`acq-pilot-select/1` — four recorded rules.** P-SEL-1 fixes the
   portfolio triple. P-SEL-2 picks the top-ranked eligible non-portfolio
   family in the *structured acquisition/procurement* shape (contract./
   procurement./funding.-chain predicates minus award-discovery markers).
   P-SEL-3 picks the top-ranked eligible family in the *independent
   oversight* shape (oversight./governance. predicates). P-SEL-4 enforces
   all ceilings and *raises* on violation — selection fails closed, never
   silently truncates. Result on the real queue: **oklahoma-state**
   (SRC-006 OMES statewide contracts + SRC-007 DAC UVED program — the
   P0-dossier authority chain — in the acquired slice; SRC-008/009 award
   members excluded under the unmet S5 funding precondition) and
   **california-state-auditor** (SRC-011 — the only non-municipal
   provenance class among oversight candidates). SRC-010 sourcewell is
   the ranked next-in-line, recorded under `capacity`.

3. **Eligibility is fail-closed before shape.** A candidate is rejected
   with a recorded reason when it joins to a P31.12/.13-owned source
   (SRC-023/SRC-026 hit this in the live inventory), is a literal
   duplicate, carries a blocked disposition, has a
   `prohibited_until_review`/`screening_required` Part VIII status, or is
   an award-discovery family while no dossier gap ledger records a
   traceable award gap (verified programmatically against the recorded
   follow-ups and drafts). Award-family *members* of a selected family
   are excluded from its slice the same way.

4. **The slice membership rule.** A selected family's acquired batch =
   its eligible members matching the slot's shape **or** carrying a
   dossier-gap priority (a P0/P1 dossier gap inside a selected provenance
   family always rides the slice), bounded ≤10 documents/aggregate rows.
   oklahoma-state's slice is therefore SRC-007+SRC-006 — both recorded
   OKC dossier gaps (the q5 contract-channel leads and the q6 UVED
   authority chain), 4 targets.

5. **`acq-pilot-funnel/1` — seven stages per family** (discovery →
   candidate_qualification → approval_gate → capture → extraction →
   link_support → publication_eligibility), every number carrying its
   basis label: `offline_replay` for committed-stand-in counts read from
   the dossier packets, `research_estimate` for inventory values,
   `pending_live` for incrementals. `captured_live` is 0 for every
   family; `measured_minutes` is `None` with the basis string — an
   estimate is never relabelled. Maintenance burden records
   protocol/target counts, expected refresh cadence, effort owner, a
   per-target retry budget (2, with recorded failure observations: the SD
   ALPR-policy 403, the ~16 MB PAB PDF, the SRC-001 amendment 403) and
   the blocked/error handling route.

6. **`sig.acq-pilot-return-pass/1`** — the exact gate packet for the two
   incremental slices: per-target doc_id/URL/goal/kind, the document cap,
   the two existing protocols (0 new protocol families), retry budget,
   `approval_refs: []` (none exist — never fabricated), preconditions
   (HG-03 per target, Part VIII screening, municipal-publication review,
   replay-identical resource bounds, hard caps) and explicit non-goals
   (no rights flip, no gate completion, no records request, no spend, no
   publication, no blind crawler, no workbook/XLSX/ZIP/sharedStrings or
   row-level plate/person/query transport — SRC-027 stays metadata-only).
   The packet is pinned to **D-P32.21-1** (OPEN); the three portfolio
   slices stay pinned to D-P32.18-1 / D-P32.19-1 / D-P32.20-1.

7. **`acq-pilot-gap-ledger/1` — the before/after reconciliation.** Before
   = each family's recorded gap state (dossier missing questions /
   follow-ups; passport named gaps). After = assertion-attributed unique
   support per portfolio family — a question supported solely by the
   family counts unique, shared questions never double-count, and
   uniqueness is measured at (question, predicate, value) fact granularity
   so a mirror could never mint uniqueness. Incrementals stay
   `pending_live` — expectations are never counted as closures.
   Reconciliation fields assert `double_counted=0`,
   `mirror_as_independent=0`, `p31_duplicate_onboarding=0`.

8. **Recommendations are deterministic + descriptive.** Portfolio
   verdicts follow the dossier's own outcome (`continue` where
   mechanical_complete, `improve` for Tulsa's honest 24/36 partial);
   incremental verdicts weigh unique relationship/provenance value
   against recorded effort/access estimates, each with conditions and
   named stop conditions. Expansion beyond the batch is a new scope
   decision. Because the matched comparison was not run, every artifact
   carries the descriptive-only label.

9. **`check_pilot` is the CI gate** — it recomputes the ceiling, exclusion,
   no-fabrication (no live capture, no approval ref, no measured minutes),
   SRC-027, deferral and shape invariants and fails loudly; the CLI adds
   `sig-tasks acquisition pilot` (readout + artifacts) and
   `pilot-check`.

## Consequences

- The batch is derivable from the committed queue — changing the ranked
  pool changes the selection deterministically, and every loser is a
  recorded rejection (removing oklahoma-state promotes sourcewell under
  the same rule, which the tests pin).
- The readout is honest by construction: no number can be read as a live
  acquisition measurement, a causal finding, or an approval.
- The live obligation is machine-checkable: `ACQ_PILOT_RETURN_PASS.json`
  plus the OPEN `D-P32.21-1` row; fixture success cannot close it.
- Deferred and visible: the HG-03 rights decisions, Part VIII screening,
  the two bounded slices themselves, the matched comparison, and the
  follow-on batch (SRC-010, SRC-012, the funding families pending a
  recorded award gap) — all named, all outside this ticket's scope.

## Revisit trigger

The D-P32.21-1 bounded live slices execute (`live_verification=true`
re-dispatch after HG-03 decides the lanes and the Part VIII screens run)
— real captures, measured minutes and link-support numbers replace the
pending_live funnel; the matched discovery comparison runs (the
descriptive-only label lifts where its protocol applies); a new
provenance family is proposed beyond the batch (the selection rules and
ceilings are re-scoped under a new scope decision); the funding-family
precondition becomes met by a recorded award gap (SRC-008/009/022 are
re-examined); or the `lineage_group` family definition proves wrong for
ceiling counting (e.g. one institution split across groups) — revisit
under a new ADR or a scoped amendment, never an in-place edit.
