# ADR-244 — Dated decision predicates: `meeting_date` and the Contract renewal triple (P37.31)

- Date: 2026-11-10
- Status: accepted
- Ticket: P37.31 (K7 WX-02, manifest row 455 — on
  `r11/P37.31-dated-decision-predicates`)
- Base: `r11/P37.30-evidence-recommender-repair`
- Requirement stamps: SIG-WATCH-007, SIG-WATCH-008 (the owned §56 rows — stamped
  in the PR), SIG-ONTO-066/067 (predicate registry), SIG-PARSE-003/004/007,
  SIG-INGEST-033, SIG-STORE-011, §0.7/§43.2
- Supersedes: nothing

This ADR records the owned decisions for the four new predicates the K7
decision-calendar watch reads — the vocabulary rows, the emit paths, and the
supersession shape. The governing contracts (append-only, fail-closed
ingestion, Part VIII, the §10.5 directness convention) are unchanged.

## Context

K7 WX-02 names the data-model half of the watch repair: the decision-calendar
items (K7 §5.2) need dated predicates the spine never carried — a
`meeting_date` claim on agenda items (the platform's own record held the date
in its `introduced` fields, never as a claim) and the Contract renewal triple
`auto_renews` / `notice_window_days` / `renewal_term_months` (the dossier's
termination model needed them; no predicate existed). The landed P35.43 watch
producer already reads all four predicate ids, so their absence on a pre-WX-02
spine is honest zero — this ticket makes the spine produce them.

## Decision

1. **Four predicates, one registry row each.** `meeting_date` (edtf, MODERATE /
   12mo / `latest_observation_wins` — a meeting can be rescheduled; the new
   observation supersedes), and `auto_renews` (boolean), `notice_window_days`
   (integer), `renewal_term_months` (integer) — all IMMUTABLE / infinite /
   `authoritative_source_wins`, mirroring `renewal_options`/`end_date` (signed
   contract terms do not drift; a restated term is a different capture or a
   correction). The `Contract` LinkML class gains the three renewal slots;
   agenda items have no class (subject-key typed) so `meeting_date` is a
   registry row only. Directness cells are assessed per row (`# P37.31
   assessment:`), the emitting genres set explicitly: `agenda_document` for the
   agenda-document and index paths, `connector_run` the default elsewhere.
2. **The agenda normaliser emits `meeting_date` as a claim.** The
   `agenda_index` row kept the date only in its `introduced` locator field; the
   same reviewed alias set now emits a `record_kind: "claim"` on the
   `agenda_item` subject — ISO date as the typed value, the platform literal as
   `raw_value` (an unparseable literal emits `value: null`, never a coerced
   date). A moved meeting supersedes by a NEW claim on re-ingest — append-only,
   never an UPDATE (SIG-STORE-011).
3. **The Contract surface carries the stated triple.** `Contract` gains
   `auto_renews`/`notice_window_days`/`renewal_term_months`; they emit only
   when the record states them (`auto_renews: false` is a stated value, not an
   absence). The procurement allowlist gains all four ids (SIG-INGEST-033).
4. **The P07.1 parser reads the triple verbatim from captured contract
   clauses.** `parsing.renewals` is a deterministic regexp reader over the
   reviewed, versioned pattern set `data/renewal_clauses.toml` (§20) — the same
   data-not-code convention as the agenda content vocabulary. Every emitted
   value is a verbatim slice with a byte-range (or page) locator
   (SIG-PARSE-003/004): a year-stated term converts at exactly 12 months, a
   month-stated notice window stays unstated (months are never a 30-day guess),
   an unreadable number stands unread. A negated clause ("does not
   automatically renew") governs its own span — an affirmative surface form
   inside a negative span is suppressed; two genuinely disagreeing clauses in
   disjoint spans both record (§3.1 — the disagreement stays visible). The
   wiring lands where a captured document already maps to a contract subject —
   the agenda-document path for contract-kind matters — and runs the same
   Part VIII forbidden-token guard as `content_term` literals: a literal
   carrying a token is suppressed and recorded on the document row, never
   emitted (§0.7/§43.2, P35.28(S2)).
5. **The wrong-predicates supersession is recorded append-only.** Pre-WX-02
   facts are never edited in place: a corrected meeting date or renewal term
   lands as a new claim row that the append-only supersession pair
   (`revises_claim`/`retraction_of`) and the producer's `_latest` ordering read
   — the watch item then marks `status: superseded` (the date moved) rather
   than silently updating.

## Consequences

- The hosted re-ingest writing these predicates onto the existing spine is the
  ticket's named production mutation (gate-pending under OM-20 — the GATE-G6
  11D list names this row verbatim, expiry GATE-ACCEPT-R11).
- The watch producer (P35.43) picks the new claims up unchanged on its next
  export — its `_WATCH_PREDICATES` read list already names all four ids.
- The renewal-clause pattern set is versioned data: a pattern change is a new
  `version` and a bulk re-read rides NEW claims (SIG-STORE-038), never a
  rewrite.

## Revisit trigger

- A materially different renewal-clause dialect (non-English contract text, or
  a captured-contract family whose renewal language the reviewed set misses)
  lands in the ingest plan → new patterns land as a new TOML `version` and this
  ADR is revisited.
- `meeting_date` proves to need a distinct `*_hearing_date` predicate (a body
  that schedules hearings separately from the meeting date) → new predicate
  row + new ADR.
- The directness assessments are measured against real extracted volume and a
  cell is demonstrably mis-graded → reassessed in a follow-up registry row
  edit, recorded in a new ADR.
