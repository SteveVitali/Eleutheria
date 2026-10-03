# ADR-137 — The Oklahoma City dossier packet + the additive seed-correction packet (P32.18)

- Date: 2026-10-02
- Status: accepted (engineering; live source capture, rights review and independent review stay gated — `live_verification=false`)
- Ticket: P32.18 (Round 10 / S2, manifest row 179; requirement SIG-DOS-003)
- Base: the P32.17 chain tip `devin/p32-17-dossier-schema-completion` (PR #174)

## Context

SIG-DOS-003 asks for the *completed* Oklahoma City dossier — not a schema
exercise but a reviewed evidence packet over real OKC material where every
affirmative or derived answer traces to qualified source spans, the
flagship count confusion is resolved **without rewriting history**, and
every gap is recorded rather than smoothed over. The pre-P32.3 seed wrote
five flagship rows that P32.3 fixed in `ops/seed.py` but that live spines
still hold in legacy form: DeFlock's 299 carrying a `news_article` genre
with no declared universe, the OKCPD chief's row asserting **190 as a source claim**
(the source only ever said "businesses own around 100 within city
limits"), and every count missing its §29.3 `count_scope`. A destructive
fix would violate append-only (P1–P3, §16); doing nothing leaves the
derived sum masquerading as an observation and the metro count reading as
a contradiction of the city figures. The dossier itself must also keep
evidence classes honest: journalism is never an instrument, a council
memo is never executed-contract evidence, an amendment whose signature
block is partially evidenced is never asserted executed, and a statute
scoped to the UVED insurance-enforcement program is never generalized to
the Flock deployment.

## Decision

**Two authored packets under `ops/` — `sig.dossier-packet/1` built by
`ops.dossier_packet` and `sig.seed-correction-packet/1` applied by
`ops.seed_correction` — plus additive `sig-ops` verbs `dossier-packet`
and `seed-correct`. All writes are append-only §16.6 corrections; all
live acquisition is a recorded deferral, never an executed fetch.**

1. **The dossier packet replays the connector, verbatim.** The
   `dossier_documents` connector runs over the three committed OKC
   fixtures (usage page, council memo, Amendment 1) through its normal
   eight-stage path; its emitted claims, evidence artifacts and field
   states land in the packet unmodified — the packet never rewrites
   connector output. Coverage the connector does not reach (the P06.1
   journalism/statements evidence pack and the committed shadow-document
   transcription fixtures — statute, ops manual, procurement record) is
   added as authored records labelled `evidence_origin` and carrying the
   same capture/locator/digest binding so the fact-to-capture ledger
   closes over every rendered fact.
2. **The scope partition is data, not prose.** Every count claim carries
   `count_scope` (+`count_scope_detail`) so the dossier renders DeFlock's
   299 (metro, community map), the official 90 (city-owned), the OKCPD chief's ~100
   (city-limits, privately-owned), the agency's 90 (city-limits,
   agency-operated, *active*), and the contract's 90 (city-limits,
   contracted units) **co-visible with scope labels — never a
   contradiction and never a collapse**. `active_device_count` ≠
   `claimed_device_count` ≠ `contracted_device_count` at value 90 is the
   owned-vs-active distinction the ticket demands.
3. **The "~190" is a labelled derivation, never a claim.** No record in
   either packet asserts 190. The dossier packet declares q3 `derived`
   with named input digests (the 90-active and ~100-private claims) and a
   method/assumptions block; the shared machinery was extended so the
   question's *other* scoped evidence stays rendered as labelled
   `context` — a derived answer may not hide the 299-metro count it must
   be shown beside. The seed-correction packet's `derived_labels[]`
   records the same roll-up through
   `reconcile.count_scope.derive_approximate_sum` (L4, approximate,
   assumptions explicit) so readers may cite the label while the spine
   holds only sourced inputs.
4. **Corrections are §16.6, resolved by content digest.** Each
   `corrections[]` entry names the exact legacy record; `apply_packet`
   locates the stored claim by `content_digest(target_record)` — any
   drift between the recorded target and the stored row fails closed —
   closes its belief window with the one permitted `UPDATE` (the
   canonical §16.6 statement, identical to `db.intake_apply`'s), and
   appends each replacement through `PgClaimSink` carrying
   `revises_claim` + `correction_reason` + the declared scope qualifiers.
   Belief closure and the replacement insert commit in **one**
   transaction (the sink binds the same connection; its chunk transaction
   nests as a savepoint), so a crash cannot leave a closed claim without
   its correction. Legacy rows are never deleted — a pre-correction
   query still returns them; `dry_run` resolves and reports only; a
   re-apply reports `already_applied` with +0 rows; a post-P32.3 spine
   reports `no_target` rather than inventing targets. The OSM row keeps
   its ODbL compartment verbatim — licence is not a count fix.
5. **Evidence classes stay honest.** Journalism/statements land
   `claim_directness=D6`, `evidence_genre=news_article` /
   `council_minutes` / `official_statement` — never instruments. The
   council memo's `document_genre=procurement_record`: a governance
   record, not executed-contract evidence. The amendment's
   `signed_date`/`execution_state` emit `present_but_empty` field states
   — a partially-evidenced signature block means execution is
   *unverified*, never inferred; its disclosure restriction stays
   actor-scoped (Company disclosure + compulsory-process exception), and
   its precedence clause is verbatim. 47 O.S. §7-606.1 renders scoped to
   the UVED program; q6 is declared `partial` with a follow-up naming the
   applicability question — no legal conclusion is inferred from the city
   page. The 7-day retention's stated 2026-10-01 effective date stays a
   *stated* date (`announced`, never promoted to operational), kept
   distinct from capture/observation dates.
6. **No fabricated review, no live fetch, no rights flip.** The packet's
   `review.status` is `not_run` (D-R10-HUMAN-1 OPEN) so `pilot_complete`
   is honestly false — `mechanical_complete=True` at 34/36 with zero
   release violations is reported as mechanical completeness, not pilot
   completion. `dossier_okc` stays `ingestion_permitted=false`
   (D-R10-SOURCES-1 OPEN). The bounded live obligation is recorded as
   `sig.dossier-live-return-pass/1` (`prepared_not_executed`, deferral
   `D-P32.18-1`): six reviewed URLs with per-target goals, HG-03/Part-VIII
   preconditions and explicit non-goals (no rights flip, no gate
   completion, no publication) — the RETURN PASS, not a skipped step.
7. **Committed artifacts.** `sig-ops dossier-packet --out
   docs/build/reports/p32.18-okc-dossier/` regenerates byte-identically:
   the packet, dossier, portfolio, print HTML, correction packet,
   `EVIDENCE_PACK.md` and `LIVE_RETURN_PASS.json` — deterministic output
   a reviewer can diff against the committed set.

## Alternatives considered

- **Routing the seed correction through `db.intake_apply` (the P32.16a
  audited bridge).** Rejected for this surface: that bridge exists to
  adjudicate *anonymous public corrections* — its apply path requires an
  intake report, an approval lifecycle and an attributable curator actor
  the ops seed path does not have. The ops packet uses the same §16.6
  primitives (single belief-closure `UPDATE` + `revises_claim` +
  `correction_reason` insert) with the packet itself as the reviewable
  record; the `claim_correction_reasoned` CHECK binds both paths.
- **Editing the seeded rows in place (or re-seeding over them).**
  Rejected: an in-place rewrite is exactly the destructive-history
  pattern the append-only spine forbids, and a blind re-seed would create
  undifferentiated duplicate counts — the legacy rows stay visible behind
  closed belief windows, superseded by declared `revises_claim` links.
- **Recording ~190 as a `derived` *claim* on the spine.** Rejected: a
  derived sum is an L4 *labelled view*
  (`derive_approximate_sum.as_view()`); asserting it as a claim would
  present computed material as observation — the very error the packet
  exists to correct.
- **Marking the amendment `executed` on the fixture's partial signature
  block.** Rejected: `present_but_empty` is the honest field state; the
  connector's `execution_state` field already routes through the recorded
  crosswalk amendment precisely because execution cannot be asserted from
  this capture.
- **Hand-authoring the dossier answers.** Rejected: the packet is the
  authored artifact; `exports.research_dossier` composes states, scores,
  ledger and violations mechanically — a hand-written answer would bypass
  the exact fail-closed review the schema exists to enforce.

## Revisit trigger

The live RETURN PASS executes (`live_verification=true` re-dispatch of
the same contract after HG-03 review decides the six targets' lanes) —
captured bytes replace stand-ins and the packet is rebuilt from real
captures; an independent reviewer completes D-R10-HUMAN-1 and the review
mark flips from `not_run`; a spine migration changes the §16.6
belief-closure contract or the `claim.content_digest` idempotency key; a
new scope universe or count-basis predicate requires the crosswalk/vocab
to grow; or the seed-correction packet is folded into a generic
multi-jurisdiction correction surface — revisit under a new ADR or a
scoped amendment, never an in-place edit.

---
*Status note (2026-10-03, P34.18 / ADR-178, S0 RI-01): a personal surname in
this ADR's body text was redacted to its institutional office ("the OKCPD
chief") under the Part VIII personal-data protection re-key; the recorded
decision is unchanged. Git history retains the original string — see the
P34.18 correction note (`docs/governance/identifier-rekey-note.md`).*
