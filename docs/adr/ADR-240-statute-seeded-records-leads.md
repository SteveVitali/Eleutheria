# ADR-240 — Statute-seeded records leads: the mandate→gap generator, the one-time auditor-survey artifact, and the LegalInstrument session/text publish gate (P37.14)

- Date: 2026-11-07
- Status: accepted
- Ticket: P37.14 (Round 11 / P37, row 436 — F2a group 11 / R11-SRC-05;
  SIG-INGEST-025a, SIG-INGEST-025b, SIG-INGEST-025c)
- Base: `r11/P37.13-registry-completeness-and-discovery-sweep`
- Related: SIG-INGEST-025a/b/c (§22.3), SIG-INGEST-025b (§36's records-request
  generator seeded from the statute), SIG-INGEST-047 (`state_auditor_survey`),
  SIG-INGEST-050 (the duty rows), SIG-METRIC-001/002 (searched sources named),
  P35.10 (the `statute_seed/2` asset this builds on), F2a-verdicts §5 group 11
  and §6.7 (the session-less `SB 34` citation flagged latent), ADR-130 (the
  reviewed acquisition queue), R11-K13-RQ-04 (the RecordsRequest→task link —
  another row's scope).

## Context

SIG-INGEST-025a makes state reporting mandates **records-acquisition leads,
not data feeds**: a statutory duty to do something is not a duty to publish
it. SIG-INGEST-025b adds the generator shape ("this jurisdiction is required
to hold X, therefore X is requestable") and the one-time-artifact rule: a
one-off artifact is captured/modelled as an artifact with its own
`capture_status`, never creates an expectation of recurrence, and the absence
of a follow-up is itself a `CoverageRecord`. SIG-INGEST-025c requires a
`LegalInstrument` claim to cite session and text; a citation that cannot be
resolved to text MUST NOT be published — the California case showed bill
numbers reused across sessions and subjects. The F2a verdict measured the
session-less `SB 34` citation sitting latent on the seed paths with tests
asserting the unsafe behaviour as correct.

P35.10's `statute_seed/2` asset carries the 50-state duty table whose
`duties` name the six registered `future_statutory_disclosure_*` sources —
the mandate surface this generator consumes.

## Decision

1. **The mandate→gap generator is a pure, fail-closed join — one output per
   duty.** `tasks.statute_leads` reads the committed leads table
   `data/statute_leads.toml` (`sig.statute-leads/1`) — one reviewed
   `[[duties]]` row per `future_statutory_disclosure_*` id the seed's duty
   table names — and emits, per statute duty, exactly one output: a
   `StatuteRecordsLead` **gap row** for a commenced duty whose mandated
   record is requestable (VA I/J/K, AL .07/.10, AR 150-103(f), UT
   77-23e-106(3)(a)), or a `CoverageRecord` for a duty whose honest output is
   a coverage fact — `not_applicable` while first reports are not yet due
   (NM 2027-04-01; a lawful absence before the due date, the registry rows'
   own rule) and `not_researched` while the mandate itself is unverified
   (MN HF 3198, contingent — a bill is not an appropriation, S5 guard). A
   seed duty with no leads row, a leads row naming an unregistered or
   non-seed duty, or a malformed row raises `StatuteLeadsError` — the
   acceptance shape ("each statute duty produces a gap row or a
   CoverageRecord") is a hard invariant, not a convention.
2. **The one-time auditor survey is desk-research modelled, never fetched.**
   The CA State Auditor 2019-118 survey is recorded as a
   `state_auditor_survey` artifact (§23.6, SIG-INGEST-047) with
   `capture_status = not_attempted` — the two registered source rows stay
   `ingestion_permitted=false` (the operator's HG-03 line owns the flip;
   desk research only, no capture). `recurrence_expected = false` is a
   checked invariant (a one-time artifact MUST NOT create an expectation of
   recurrence), and the absent follow-up emits a `searched_not_found`
   CoverageRecord naming the desk-research surfaces searched (SIG-METRIC-001).
3. **Session + text ride the `LegalInstrument` claim surface; the publish
   gate is stamped on the record.** `LegalInstrument` gains `session` and
   `text_ref` (both additive, allowlisted, §20 versioned — vocab
   `2026.11.07-p37.14`), and `publish_verdict()` decides publication under
   `legal-instrument-publish/1`: a legislative instrument
   (`statute`/`ordinance`) withholds without a recorded session, and every
   instrument withholds when its citation cannot resolve to text — the two
   `SESSION_REQUIRED_INSTRUMENT_TYPES` are the session-law citations; an
   administrative rule has no session but still needs text. The verdict
   (`publishable` + named `reasons`) is stamped onto the emitted
   `legal_instrument` record so the gate travels with the claim. The
   `statute_seed` connector stamps `text_ref` from each v2 entry's verified
   `origin_url`; the asset does not record sessions, so the seed's citations
   — including the F2a-flagged session-less `SB 34` — evaluate
   `publishable = false`, the honest INGEST-025c posture.
4. **Leads are leads, never acts.** Nothing is filed, sent, fetched, or
   flipped: the leads feed the records-request queue downstream; the
   RecordsRequest→task link is R11-K13-RQ-04's scope; sending stays
   operator-gated (`D-R7.2-SEND`); every cited source row stays
   `ingestion_permitted=false`.

## Consequences

- The six registered duties yield 4 requestable gap rows + 2 coverage rows
  (1 `not_applicable`, 1 `not_researched`) plus the auditor survey's
  `searched_not_found` — each duty's disposition is reviewed data in the
  leads table, never a heuristic on `duty_notes` prose.
- The `legal_instrument` entity record gains `publishable` /
  `publish_gate` / `publish_gate_reasons` fields — additive provenance the
  partner-fixture golden digest normalizes out (same class as P35.16's
  `axis_order`/`geometry_defect` stamps; claim content unchanged).
- The france_belgium vocab moves to `2026.11.07-p37.14` (`-pNN.N` suffix —
  `dot_511` was already at `2026.11.07`, a bare-version collision would have
  mis-normalized the golden digest); `session`/`text_ref` join the
  legal-instrument predicate allowlist.
- Downstream surfaces that publish `LegalInstrument` citations now have a
  machine verdict to consult; seed instruments stay withheld until session
  data is recorded (a later data-review ticket's work, not this one's).

## Alternatives considered

- **Derive `session` from the seed's citation strings** ("HB 58 (2026 RS)") —
  rejected: heuristic parsing of citation prose is fragile across
  legislatures and would fabricate sessions the asset never reviewed; the
  gate's honest answer for session-less records is `publishable = false`.
- **Emit both a lead and a `searched_not_found` coverage per commenced duty**
  — rejected: the catalog's shape is "a gap row **or** a CoverageRecord";
  one output per duty keeps the join auditable, and the lead already carries
  the desk-review `searched` note for not-located publications.
- **A new connector for the leads** — rejected: the generator consumes
  committed artifacts (seed + leads table) and emits typed records for the
  §36 queue's input surface; it is tasks-side machinery, not an acquisition
  connector, and opens no fetch path.

## Revisit trigger

Revisit when: (a) a new `future_statutory_disclosure_*` duty is registered —
the fail-closed join forces a leads-table row and a reviewed disposition; (b)
the seed asset records `session` per entry — the publish gate's verdicts for
seed instruments can then flip to publishable and the withheld set shrinks;
(c) the RecordsRequest→task link (R11-K13-RQ-04) wires the emitted gap rows
into queued tasks; (d) a follow-up auditor survey appears — the
`searched_not_found` record and `recurrence_expected` invariant are then
wrong and must be corrected as new records; or (e) a publication surface
consumes `publishable` — verify it honours the gate rather than the citation
alone.
