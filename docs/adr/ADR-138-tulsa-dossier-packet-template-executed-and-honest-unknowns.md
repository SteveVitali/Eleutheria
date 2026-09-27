# ADR-138 — The Tulsa dossier packet: template-vs-executed separation and honest bounded unknowns (P32.19)

- Date: 2026-10-01
- Status: accepted (engineering; live source capture, rights review, records-request filing and independent review stay gated — `live_verification=false`)
- Ticket: P32.19 (Round 10 / S2, manifest row 180; requirement SIG-DOS-004)
- Base: the P32.18 chain tip `devin/p32-18-okc-evidence-dossier` (PR #175)

## Context

SIG-DOS-004 asks for the *completed* Tulsa dossier from three committed
fixtures: TPD Policy **113C** (ALPR — two distinct products, Flock Safety
fixed + Axon Fleet 3 in-car), TPD Policy **113E** (ALPR data use/sharing),
and the public private-camera integration **MOU template**. The ticket's
load-bearing distinctions are exactly the ones the evidence corpus makes
hard to keep honest:

- the MOU is a **blank template** — its Licensor/Licensee/Date fields are
  present-but-empty, so it proves *offered structure and terms* only. It
  must never mint an executed contract, named participants, a buyer, a
  signature date, or an actual sharing edge;
- the corpus contains **no executed instrument, no count, no spend, no
  roster and no observed use** — every one of those must stay `unknown`
  with a documented search basis and a precise follow-up ("searched, not
  found" is never "does not exist" and never a silent zero);
- each policy's **stated effective date is a document date** (2023-07-07
  / 2023-10-04), distinct from the replay's 2026-10-01
  retrieved/observed date, and captured 2023 files are not asserted to be
  the current enforceable versions;
- Policy 113C's only numeric retention clause is scoped to **manually
  entered** LPR data — it is never a universal scan-retention rule, and
  113E's absent uniform period stays a reviewed `absent` field-state.

The corpus is therefore a deliberately *partial* dossier: unlike OKC
(mechanical_complete 34/36), the honest Tulsa outcome keeps the
contract-chain completion gate unresolved — the packet must report that
rather than pad answers toward the 28/36 threshold.

## Decision

**One authored `sig.dossier-packet/1` built by
`ops.tulsa_dossier_packet` — connector replay verbatim, one authored
operator claim, packet-level declarations for every gap — plus an
additive `sig-ops dossier-packet-tulsa` verb, a drafted (never sent)
follow-up/request queue, and a prepared-not-executed live RETURN PASS.**

1. **The connector replay is consumed verbatim.** The
   `dossier_documents` connector runs over the three committed Tulsa
   fixtures through its normal eight-stage path; the 15 emitted claims +
   3 evidence artifacts land in the packet unmodified (only the
   connector-transient `claim_id`/`sys_period` are dropped). The replay's
   in-memory `ingestion_permitted` flip is the documented fixture-runner
   carve-out — the registry row stays `ingestion_permitted=false`
   (D-R10-SOURCES-1 OPEN); a rights flip is never code.
2. **One authored claim: the operator attribution.** The packet adds
   `asset_operator = Tulsa Police Department` cited to Policy 113C's page
   (locator + capture digest + stated `valid_from` 2023-07-07) — the
   department's own enacted ALPR policy is the operator attribution. It
   asserts who runs the program; it says nothing about a buyer, funder,
   executed instrument or the MOU's blank parties, and q1 is declared
   `partial` with follow-ups.
3. **The template stays a template, by construction and by guard.** The
   MOU's two offered-term records emit only D6 claims under
   non-execution predicates (`written_policy_value`, `use_restriction`);
   its Licensor/Licensee/Date fields emit `present_but_empty`
   `disclosure_field_state` records. No claim anywhere in the packet
   carries an executed-instrument predicate (`buyer`/`seller`/
   `signed_date`/`contract_value`/`amends_contract`) or an actual-access
   predicate (`configured_access_edge`/`pooled_lookup_participation`/
   `sharing_partner_degree`) — the emit-time template guard and the
   release-side re-check both enforce it, and the offered purpose clause
   lands on q6 as terms, never a q4 access edge.
4. **Unknowns are documented and bounded, never zero.** q3 (inventory),
   q4 (external access), q5 (procurement/spend) and q10 (oversight) each
   render `unknown` with named sources searched (the three captured
   documents plus the reviewed leads — the TPD Flock page, the policies
   index, the Commercial Corridor Safety Guide excerpt, the 2026-09-25
   bounded research pass), a search date, the `searched_not_found`
   outcome, and a follow-up carrying a precise action + closing
   condition. q6 (authority beyond department policy), q7 (non-manual
   configured retention) and q8 (actual sharing actors/mode) are declared
   `partial` — the honest sub-scores, not padded affirmatives.
5. **The two instruments' stated dates stay distinct document dates.**
   Both `effective_from` claims ride their own `valid_from` windows
   (2023-07-07 for 113C, 2023-10-04 for 113E) while `observed_at`/
   `retrieved_date` stay the 2026-10-01 replay date. The same-scope
   conflict rule surfaces the two values co-visibly under `disputed`
   rather than silently collapsing two instruments into one timeline —
   the packet's search entry names the two-document structure so the
   flag reads as *two stated dates, both kept*, not a hidden winner.
   Currentness is never asserted: the policies-index re-check is a live-
   pass bounded question.
6. **The gap follow-ups are drafted through the real machinery — never
   sent.** `FOLLOW_UP_DRAFTS.json` is built by running `tasks.detect`'s
   detector pool over the packet's recorded coverage gaps: the executed-
   contract gap routes to `missing_contract` → the Oklahoma Open Records
   Act `alpr_contract` draft for Tulsa Police Department; the rest stay
   `coverage_hole` research tasks. Every draft is `status="drafted"`,
   the filer/consent is never fabricated (SIG-TASK-018), and
   `records_requests_sent` is 0 — there is no transmit path.
7. **No fabricated review, no live fetch.** `review.status=not_run`
   (D-R10-HUMAN-1 OPEN) keeps `pilot_complete` honestly false; the
   mechanical gate reports `total < 28/36` and `q5 < 2` as blocking —
   the designed outcome for a still-partial dossier, never smoothed
   over. The bounded live obligation is recorded as
   `sig.dossier-live-return-pass/1` (`prepared_not_executed`, deferral
   `D-P32.19-1`): the three registered target URLs plus the three
   reviewed leads, with HG-03/Part-VIII preconditions and explicit
   non-goals (no rights flip, no gate completion, no request sent, no
   publication).
8. **Committed artifacts.** `sig-ops dossier-packet-tulsa --out
   docs/build/reports/p32.19-tulsa-dossier/` regenerates byte-
   identically: the packet, dossier, portfolio, print HTML,
   `FOLLOW_UP_DRAFTS.json`, `EVIDENCE_PACK.md` and
   `LIVE_RETURN_PASS.json` — deterministic output a reviewer can diff
   against the committed set.

## Alternatives considered

- **Generalizing `ops.dossier_packet` (the OKC module) to take a city
  parameter.** Rejected: that module is OKC-specific by construction —
  its constants (the P06.1 pack, shadow-document fixtures, count
  partition, correction packet) are city-bound; parameterizing it would
  entangle two unrelated evidence corpora. A Tulsa-specific module
  consuming the *same shared machinery* keeps each packet's authored
  surface reviewable.
- **Authoring `supported` answers for q3/q4/q5/q10 to reach mechanical
  completeness.** Rejected: that is exactly the fabricated-affirmative
  the schema's release validation exists to refuse — the honest
  `searched_not_found` unknown with a named next action is the S2
  semantics' designed output for a still-partial corpus.
- **Marking the packet `pilot_complete` or a review `completed`.**
  Rejected: D-R10-HUMAN-1 is OPEN — no independent reviewer exists on
  this build; `not_run` is the honest mark.
- **Collapsing the two `effective_from` values (or hiding one).**
  Rejected: they are distinct instruments' stated dates; the same-scope
  conflict rule keeps both rendered and marked rather than a silent
  reconciliation — and any document-partitioned conflict rule would
  defeat the detector's real purpose (two sources reporting *the same*
  instrument differently).
- **Sending or staging the records request.** Rejected: requests are
  drafted only; sending is a public act attributable to a filer at
  filing time (SIG-TASK-018) and is explicitly out of scope —
  `records_requests_sent` stays 0.

## Revisit trigger

The live RETURN PASS executes (`live_verification=true` re-dispatch of
the same contract after HG-03 review decides the targets' lanes) —
captured bytes replace stand-ins and the packet is rebuilt from real
captures; an independent reviewer completes D-R10-HUMAN-1 and the review
mark flips from `not_run`; an executed City–Flock instrument, executed
MOU, inventory or oversight artifact is captured (the unknowns are
re-graded); the TPD policies index shows 113C/113E superseded (the
timeline gains a lifecycle record); or the dossier machinery's
same-scope rule grows instrument-level partitioning — revisit under a
new ADR or a scoped amendment, never an in-place edit.
