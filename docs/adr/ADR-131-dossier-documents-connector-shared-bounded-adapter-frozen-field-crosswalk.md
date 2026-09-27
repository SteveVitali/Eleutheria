# ADR-131 — The `dossier_documents` connector: one shared bounded adapter over a frozen field crosswalk (P32.12)

- Date: 2026-09-27
- Status: accepted (engineering; all three sources stay `ingestion_permitted=false` — fixture success is not a rights decision, a gate flip, or publication approval)
- Ticket: P32.12 (Round 10 / S5, row 172; requirement SIG-ACQ-003; annotates `D-R10-SOURCES-1`)
- Base: `30d401d` (the P32.11 chain tip `devin/p32-11-gap-driven-source-discovery`, PR #167)

## Context

The three pilot dossier source families — `dossier_okc`,
`dossier_tulsa`, `dossier_san_diego` — publish the same epistemic shape of
material (contracts, policies, templates, subscriptions, disclosure index
pages) through per-source layouts that differ in detail. §55.6 requires a
bounded acquisition interface per source family: fixed protocol caps, a
frozen named-target crosswalk, genre-aware semantics, and explicit failure —
never best-effort partial extraction.

Without a contract, the known failure modes recur: a blank MOU *template*
reads as an executed instrument (a participant, a purchase, a deployment —
the S2 research showed real municipal copies); a Vigilant *subscription*
reads as owned local hardware; a signature date on one party's block reads
as full execution; a mandated-but-absent field is silently skipped instead
of recorded as unanswered; and an oversized, encrypted or drifted document
is half-parsed into affirmative claims the bytes cannot support. Each is a
fabricated-certainty failure the defining standard (§3.1) forbids.

## Decision

**One registered connector, `dossier_documents`
(`connectors/src/connectors/dossier_documents.py`), serves all three pilot
source families; per-source behaviour is data, not code
(`connectors/src/connectors/data/dossier_documents_vocab.toml` +
`dossier_field_crosswalk.toml`, SIG-ENG-001). The adapter runs the existing
eight-stage pipeline (ADR-026) over committed fixtures — no new parser
stack, no OCR, no third protocol.**

1. **Bounded by construction.** Two document protocols only — `html_text`
   (layer-2 selector extraction) and `pdf_text` (layer-3 digital-native PDF
   text) — under hard resource bounds (1 MiB document bytes, 40 PDF pages,
   64 configured fields, 512 KiB extracted text, 128 index links). Two
   format handlers only — `clause_fields` (per-document field extraction)
   and `index_listing` (link fan-out with `document`/`title`/`posted_date`
   rows). An unsupported format, bound violation, malformed document or
   encrypted/unreadable PDF is an explicit `ContentDrift` failure: no
   partial affirmative claims are emitted for it.
2. **Reviewed literals must exist in the captured bytes.** Every configured
   `answered` field's reviewed literal is located in the stored capture and
   carries a typed locator (byte ranges for HTML/index evidence, page
   locators for PDF). A configured literal that cannot be found in the
   bytes is content drift between reviewed metadata and the capture — an
   explicit failure, never a guessed value.
3. **`dossier-field-crosswalk/1` is the only field→predicate route.** Each
   configured field resolves to a row naming the existing predicate,
   qualifier semantics, organisation role (`db.organization_roles` —
   a publisher can never mint an operational role, SIG-TRUST-003),
   valid-time class (`publication|effective|coverage|as_of|none`), the S2
   dossier rubric field (q1…q12) and an applicability rationale. A
   configured field with no row, or a `required` field whose row is
   `needs_amendment`, fails `check_crosswalk()` — review fails closed, and
   the only route for a new field is the scoped amendment recorded on the
   row, never an ad-hoc ontology addition. Mapped predicates are validated
   against the committed ontology vocabulary via the new public
   `ontology.generate.load_vocab()` accessor — no duplicated predicate
   list. `execution_state` is admitted as `needs_amendment` with the scoped
   proposal recorded (`instrument_execution_state` over the closed enum
   {verified_executed, partially_signed, unsigned_template,
   not_visually_verified} — a reviewer assessment, never an inferred
   state); it emits only field-state evidence until a future schema ticket
   consumes the proposal.
4. **Genre is a mechanical epistemic guard.** The derived genre (from the
   bytes) and the reviewed evidence genre are both recorded. The
   `template_execution_guard` bars executed-instrument predicates
   (parties, signatures, values, term dates, lifecycle) on `template`
   documents; the `subscription_hardware_guard` bars local-hardware
   predicates on `subscription` documents — database access is never sensor
   inventory. ADR-122 non-probative genres (`template`, `recommendation`,
   `subscription`, `vendor_default_page`) stamp every emitted claim
   `claim_directness = "D6"` — the P32.3 construction made mechanical
   instead of conventional.
5. **Completeness without synthetic certainty.** The field-state vocabulary
   is closed: `answered` emits a typed value claim; `present_but_empty` and
   `absent` emit `disclosure_field_state` claims (a mandated-but-unanswered
   field is recorded evidence, never silently skipped); `redacted` emits a
   `somevalue` claim — a value exists but is withheld — never a fabricated
   literal.
6. **Consumed, not forked.** The Part VIII forbidden-token and
   person-naming guard is the shared `okc_documents` implementation; name-
   only partner claims mint `partner_identity` entity-ref twins carrying
   the crosswalk's role, scoped to the asserting source and its
   jurisdiction (SIG-TRUST-004) — candidates, never merged identities.
   Post-capture stages are pure functions of stored capture bytes; replay
   is byte-identical with zero assertions and opens no socket.

## Consequences

- Three registry rows (`dossier_okc`, `dossier_tulsa`,
  `dossier_san_diego`) exist with `ingestion_permitted=false`, rights
  UNDETERMINED, and no review metadata — the loader gate refuses them and
  `run --mode live` exits 3 exactly as for any unreviewed source.
- `sig-connectors validate` now additionally runs `check_crosswalk()`:
  every configured field resolvable, every mapped predicate in the
  ontology vocabulary, every object role canonical, every `needs_amendment`
  row carrying its scoped proposal.
- `D-R10-SOURCES-1` stays OPEN: the bounded adapter is the engineering
  precondition; the exact-target rights/evidence-use review, HG-03 flip,
  and bounded live pilot remain with P32.18–P32.21 and the operator.
- The `instrument_execution_state` proposal is owed work — recorded on the
  crosswalk row as a scoped amendment for the next schema/vocab ticket; no
  claim mints it meanwhile.

## Alternatives considered

- **Three bespoke connectors (copy the OKC connector per family).**
  Rejected: three near-identical stacks would fork the Part VIII guard,
  the field-state bookkeeping and the genre guards — the exact drift
  surface §55.6's shared-adapter clause rules out. One connector over
  per-source TOML keeps family differences as reviewable data.
- **A third protocol (OCR/image extraction) for the Tulsa policy scans.**
  Rejected: the ticket caps the adapter at ≤2 protocols; OCR is a
  separately sized contract with its own error model. Unreadable or
  image-only captures fail explicitly today — a deferred capability, not a
  silent gap (recorded under `D-R10-SOURCES-1`).
- **Emitting `execution_state` from signature-block heuristics.**
  Rejected: presence of one signature date is not execution; S2 forbids
  inferring instrument state. The field emits field-state evidence only
  until the scoped amendment lands a reviewer-assessed predicate.
- **Per-field ad-hoc predicates.** Rejected: every emitted predicate must
  already exist in the ontology vocabulary; an unmapped field is a schema
  conversation, not a string.

## Revisit trigger

A pilot family requires a third document protocol (OCR or an office
format), the `instrument_execution_state` amendment is consumed by a schema
ticket (the crosswalk row then maps to the landed predicate and
`needs_amendment` clears), or a live pilot under the P32.18–P32.21 reviews
shows a bound (bytes/pages/fields/links) mis-sized for real captures —
revisit under a new ADR or scoped amendment, never an in-place edit.
