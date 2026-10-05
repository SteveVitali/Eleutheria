# ADR-143 — The investigation-journey acceptance portfolio: declared corpus, staged scratch release, evidence classes, and honest gaps (P32.24)

- Date: 2026-10-20
- Status: accepted (engineering; `live_verification=false` — committed bytes + a throwaway PG18 testcontainer; production-candidate verification stays under `D-R10-LIVE-1`, still OPEN)
- Ticket: P32.24 (Round 10 / S4, row 189; requirement SIG-FIND-007; annotates `D-R10-USERS-1` (stays OPEN), `D-R10-PUBLISH-1`, `D-R10-HUMAN-1`, `D-P32.23a-1`)
- Base: `devin/p32-23a-release-candidate` tip (PR chain of P32.23a / ADR-142)

## Context

The Round-10 S4 deliverable is the *"verify the public investigation
acceptance portfolio"* gate: the last engineering proof before GATE-G3 that
the public surface answers its six advertised journeys — discover a record,
inspect it, trace evidence, follow a relationship, search, and file a
correction — across three dossiers and the representative
tail/unlocated/withheld records, in **one staged release**, with no-JS,
keyboard, print, back/forward, release-citation and receipt-to-moderation
walkthroughs.

The input candidate is P32.23a's (`p-17b713…`, ADR-142): staged, validated,
**unpublished**, under the deferred-evaluation identity. Two input facts
shaped the design:

1. **The candidate's record surface is empty.** Its fixture-seeded repaired
   spine exports 16 claims but the bound release projection materializes
   **zero** `sig.published-record/1` rows, zero dossier pages, and an empty
   network (`nodes=[]`, `edges=[]`). A "record journey passes" claim against
   it would be fabricated — the portfolio had to find the honest verdict
   shape for this case.
2. **The deferral spine is still open.** `eval=deferred` (S3 human
   evaluation, 2026-10-19), `D-R10-USERS-1` (independent human usability),
   `D-R10-LIVE-1` (hosted production candidate). The ticket's own words —
   *"distinguish automation, agent walkthrough and independent human
   usability evidence"* — require the readout to carry evidence *classes*,
   not just pass/fail.

The questions this ADR answers:

- How do the journey checks run over a real population **without** inventing
  fixture coverage where the candidate is empty — and without pretending the
  corpus is the candidate?
- How do the DB-bound legs (receipt → restart → moderation → canonical
  correction → publish linkage) fold into one portfolio without hiding their
  provenance?
- How does every material failure — or every *disclosed* non-pass — land an
  owner + landing, per the acceptance criterion *"all material failures
  receive exact owners/landings and prevent false portfolio PASS"*?

## Decision

### `sig.journey-corpus/1` — a declared acceptance corpus, never a data release

`ops.journey_verify.build_acceptance_export` emits a real-contract export
(`manifest.json` + compartment `sites.jsonl`/`record_claims.jsonl` +
`web/` payloads) that the **same** `exports.release.build_release` consumes —
the journeys exercise the exact code path that produced the candidate. The
corpus is synthetic and says so inside its own bytes (`corpus.json`,
`purpose` field); it is never described as a data release and never touches
the published registry. It declares, and `corpus.json` records, the
representative cases the journeys need: 75 records over two licence
compartments (`sig_graph`/CC-BY-4.0 + `osm_physical`/ODbL-1.0), a tail record
only reachable on browse page ≥2, five `no-public-point` deployments, five
unreported-jurisdiction deployments, three `unresolved_point` deployments, a
ghost claim (asserted, absent from `record_claims` → `unlocated` anchor), an
evidence leg with no published capture legs, three typed edges across all
three access kinds (`configured_access`, `observed_use`,
`declared_policy`), and a withheld entity + a withheld claim exercised under
real `denied`/`withhold` dispositions.

### `sig.journey-portfolio/1` — checks carry evidence class + owner + landing

Every check row carries `id`, `journey`, `evidence_kind`
(`automated_conformance` | `agent_walkthrough` | `independent_human`),
`status` (`pass` | `fail` | `deferred` | `not_applicable` |
`verified_by_test`), `detail`, `evidence` paths, an `expected_answer` for the
interpretive legs, and **owner + landing** — enforced structurally: a
`fail`/`deferred`/`not_applicable` check constructed without both raises
`PortfolioError`. Verdict = `fail` on any `fail`; `pass` otherwise —
`verified_by_test`, `deferred` and `not_applicable` are honest terminal
states with recorded landings, not silent skips.

Journey A (discover/inspect/trace/search) runs over the staged corpus
release: manifest validation, all-records-reachable, citation digest match,
browse exhaustiveness, the `unreported` jurisdiction page, the released FTS5
index (tail token, exact entity id, `no-public-point` facet, explicit empty),
the three honest location states, evidence anchors (present / `unlocated` /
no-published-legs), the three dossier scopes with provisional-as-of
framing, and static-vs-JSON agreement on a sampled set.

Journey B (typed relationship traversal) checks every edge is typed +
evidenced + claim-resolvable, and reports the candidate's own empty network
as `not_applicable` — never a passing "no relationships" claim. Any
configured≈observed equivalence or certified-resolved-site reading is
`deferred` behind the evaluation spine.

Journey C (correction) consumes `sig.journey-intake-proof/1` — a real-PG
execution of submit → fresh-connection survival → restricted queue →
reviewer propose → curator approve → exactly-once `correct` apply (§16.6
close+revises, one `intake.application` receipt, `applied` event) →
`mark_published` release+correction linkage → resolved public state → live
`sig_intake_receiver` canonical-write refusals. Without a supplied proof the
C checks are `verified_by_test` (pointing at
`tests/db/test_journey_portfolio_pg.py`) — never claimed as run; with one,
they are executed `pass`/`fail`.

The withdrawal legs stage the corpus release into a scratch registry under
the report dir (the same `activate()` machinery — `latest.json` is *this
registry's* pointer, never the published one), record real `denied` +
`withhold` dispositions, and verify every route serving the withdrawn
entity/claim answers `route_deny`/`tombstone` while unaffected routes stay
permitted and `sig.tombstone/1` JSON shape holds.

### Evidence classes are load-bearing, not labels

The markdown readout groups checks and restates `eval=deferred` on every
leg that could read as an evaluation claim; the summary counts by class.
`UX.independent_sessions` is `independent_human` + `deferred` with owner
`D-R10-USERS-1` → `USABILITY_TASK_PROTOCOL.md` — a runnable moderated
protocol as the compensating control. There is no code path that emits a
human-evidence `pass` without a recorded volunteer set.

### `sig-ops journey-verify` / `sig-ops journey-intake`

Two additive verbs: `journey-verify` runs the whole portfolio (read-only over
`--candidate`, defaults to the committed P32.23a packet) and exits 1 printing
owner+landing on every failed check; `journey-intake` executes the PG leg
and emits the proof JSON. Committed artifacts under
`docs/build/reports/p32.24-investigation-journey-verification/`.

## Consequences

- The portfolio is **green with disclosed deferrals**: 31 pass ·
  3 verified_by_test · 2 deferred · 2 not_applicable — and every non-pass row
  names its owner (`D-P32.23a-1`, `D-R10-HUMAN-1`, `D-R10-USERS-1`) and
  landing.
- Record-journey semantics are proven on a real staged release *without*
  misrepresenting the candidate's empty surface; the production re-run is
  pinned to `D-R10-LIVE-1`'s return pass.
- Human usability stays an **open obligation with a runnable protocol** —
  GATE-G3 sees the gap explicitly, never as a fabricated green.
- `sig-ops journey-verify` is re-runnable: corpus bytes are deterministic,
  so the acceptance release's `p-<64>` namespace is stable until the corpus
  declaration itself changes — a deliberate, reviewable event.

## Alternatives considered

- **Seed the candidate itself with synthetic rows and verify *it*:** rejected
  — the candidate is a pinned artifact; mutating its export to create journey
  coverage would falsify exactly what P32.24 is asked to verify.
- **Skip the corpus and mark all record journeys `not_applicable`:** rejected
  — the S4 deliverable is the *investigation surface's* acceptance, not only
  this candidate's; a no-corpus portfolio would verify nothing and let
  GATE-G3 see a vacuous green.
- **Mock the intake bridge:** rejected — the AC is about *the real* durable
  receipt + exactly-once canonical write; the proof runs the real role-scoped
  stores on real PG (the same testcontainer pattern the db suite uses).
- **A `partial` verdict tier:** rejected — it would give a false-PASS-shaped
  escape; `deferred`/`not_applicable`/`verified_by_test` rows already carry
  the honest middle states *with owners*, and `fail` must stay a hard stop.

## Revisit trigger

- `D-R10-LIVE-1` closes: re-run `sig-ops journey-verify --candidate
  <production packet>` — `candidate.record_surface` and `B.candidate_network`
  must flip from `not_applicable` to real pass/fail rows.
- `D-R10-USERS-1` gains volunteers: run `USABILITY_TASK_PROTOCOL.md`, append
  `USABILITY_SESSIONS.json`, and `UX.independent_sessions` re-evaluates —
  any protocol change is a `/2` of this portfolio schema.
- The S3 evaluation spine resumes (per ADR-142's trigger): `B.eval_deferred`
  and the `provisional` stamps are replaced by the decision's own posture.
