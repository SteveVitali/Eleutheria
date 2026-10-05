# ADR-139 — The San Diego dossier packet: subscription-vs-hardware, prime-vs-component, proposed recommendation, and the metadata-only Part VIII preflight (P32.20)

- Date: 2026-09-27
- Status: accepted (engineering; live source capture, rights review, records-request filing and independent review stay gated — `live_verification=false`)
- Ticket: P32.20 (Round 10 / S2, manifest row 181; requirement SIG-DOS-005)
- Base: the P32.19 chain tip `devin/p32-19-tulsa-evidence-dossier` (PR #176)

## Context

SIG-DOS-005 asks for the *completed* San Diego dossier from four committed
fixtures: the 2025 SDPD Annual Surveillance Report (the **Vigilant LEARN
hosted-database subscription** section), the City–Ubicquia public-safety
agreement, the SDPD surveillance-technology index, and the Privacy Advisory
Board reports index. The ticket's load-bearing distinctions are the corpus's
two-layer structure — a *physical* streetlight/ALPR contract alongside a
*subscription* to an external hosted database — plus the honesty traps the
fixtures deliberately contain:

- the ASR is a **subscription/access** document: SDPD subscribes to the
  vendor-hosted Vigilant LEARN pool ("owns no ALPR cameras or hardware under
  this arrangement"). It must never mint a local SDPD device, count,
  deployment-existence or location claim — and its bounded non-ownership
  sentence is scoped to the subscription arrangement, never generalized to
  the streetlight program;
- the Ubicquia agreement names **two different roles**: Ubicquia, Inc. is
  the contracting party (`seller`/prime); Flock Safety, Inc.'s terms are
  incorporated by reference (the component supplier, `vendor`). Collapsing
  either into the other would fabricate a role the instrument does not
  establish — a vendor mention is never an operational relationship;
- the agreement's signature block is **asymmetric**: "Vendor Date:
  12/15/2023" is a vendor-side date while "City Date:" is
  present-but-empty — so the instrument is a contract with unverified
  execution, never an `executed_contract`;
- the PAB listing evidences the **existence of a recommendation** — a
  proposed oversight action — not its adoption, enactment or policy force;
- the ALPR index's 2024–2026 **network-audit spreadsheet links** (SRC-027,
  `prohibited_until_review`) may carry plates, person-level queries and
  officer identities — Part VIII permits only a metadata-only preflight;
  no workbook byte, XLSX/ZIP container or `sharedStrings` stream is ever
  transported.

The corpus therefore combines a *subscription* surface (access edges into a
shared vendor pool), an *unexecuted-looking contract* surface (roles,
ceiling, contracted units, asymmetric signatures) and a *portal* surface
(index listings) — each with distinct directness, scope and role semantics.

## Decision

**One authored `sig.dossier-packet/1` built by
`ops.san_diego_dossier_packet` — connector replay verbatim, seven authored
claims recording the ticket's load-bearing distinctions, packet-level
declarations for every gap — plus an additive `sig-ops
dossier-packet-san-diego` verb, a drafted (never sent) follow-up/request
queue, a `sig.part-viii-preflight/1` for SRC-027, and a prepared-not-executed
live RETURN PASS.**

1. **The connector replay is consumed verbatim.** The `dossier_documents`
   connector runs over the four committed San Diego fixtures through its
   normal eight-stage path; the 30 emitted claims + 4 evidence artifacts
   land in the packet unmodified (only the connector-transient
   `claim_id`/`sys_period` are dropped). The replay's in-memory
   `ingestion_permitted` flip is the documented fixture-runner carve-out —
   the registry row stays `ingestion_permitted=false` (D-R10-SOURCES-1
   OPEN); a rights flip is never code.
2. **Seven authored claims record what the corpus proves — no more.**
   Each is cited to a committed span (locator + capture digest + stated
   dates):
   `asset_operator = San Diego Police Department` (the ASR is the
   department's own report — it asserts who operates, nothing about a
   funder or an executed chain); the physical program's
   `technology = ALPR Program` (the index listing's verbatim label); the
   ASR's bounded non-ownership statement as `written_policy_value` scoped
   verbatim to the subscription arrangement; the prime-vs-component split
   (Ubicquia contracting party ≠ Flock component supplier) and the
   agreement as the recorded contracting instrument; the PAB
   recommendation's `authorization_state = proposed` cited to its index
   anchor; and the ASR's sharing-mode sentence (the vendor-hosted pool
   shared across subscribing agencies) as q8's inbound-access evidence.
   Authored claims mirror the emitted two-genre convention —
   `document_genre` describes the captured document
   (`deployment_report`/`procurement_record`), `evidence_genre` the
   adapter's declared evidence genre (`official_statement`/`contract`/
   `portal_document`).
3. **Subscription stays access, never hardware.** The ASR target carries
   `access_mode="subscription"`: the connector's hardware guard bars every
   device/location predicate at emit time and the packet contains no local
   SDPD camera, count, deployment-existence or fixed-asset claim sourced
   from the subscription. The only count in the packet is the agreement's
   500 streetlight units carrying `count_scope=contracted_units` —
   contracted is never installed; q3 is declared `partial` (the
   subscription's bounded non-ownership sentence is the agency's own, and
   no installed/active/current count exists in the pack).
4. **Prime and component roles stay separate predicates.** `seller =
   Ubicquia, Inc.` and `vendor = Flock Safety, Inc.` ride different
   predicates on the contract subject; the authored role-split claim keeps
   the distinction explicit. No claim attributes contracting-party facts
   to Flock or component-supply to Ubicquia — a name mention never mints
   a relationship.
5. **Signature stays distinct from execution.** `signed_date` carries the
   vendor-side date verbatim ("Vendor Date: 12/15/2023") while `City
   Date:` is a `present_but_empty` field-state; the document genre is the
   honest `procurement_record`, the evidence genre `contract` — never
   `executed_contract` — and q5 is declared `partial` with an
   execution-chain follow-up (signature pages, council memorandum, FY27
   budget response).
6. **The recommendation stays proposed.** The PAB index evidences
   existence + verbatim title; the authored `authorization_state` renders
   `proposed` — no claim asserts adoption, enactment or effective status,
   and the ASR self-report stays genre-distinct (`official_statement`)
   from the oversight instrument.
7. **Unknowns are documented and bounded, never zero.** Every gap carries
   a declared `partial` with rationale or an honest residual: q8 keeps the
   evidenced *mode* (vendor-hosted shared pool — inbound pooled access)
   while the outbound actors/edges stay unevidenced — its search entries
   use `found` for the mode and name the residual gap, never a fabricated
   `searched_not_found` over an evidenced claim (the release validator
   enforces absence-vs-evidence consistency); follow-ups name the precise
   action + closing condition per question.
8. **The gap follow-ups are drafted through the real machinery — never
   sent.** `FOLLOW_UP_DRAFTS.json` runs `tasks.detect` over the recorded
   coverage gaps: the execution-chain and sharing-instrument gaps route to
   `missing_contract` → the California Public Records Act `alpr_contract`
   draft for San Diego Police Department; the inventory and
   oversight-adoption gaps stay `coverage_hole` research tasks. Every
   draft is `status="drafted"`, no filer/consent is fabricated
   (SIG-TASK-018), and `records_requests_sent` is 0.
9. **Part VIII preflight is metadata-only.** `PART_VIII_PREFLIGHT.json`
   (`sig.part-viii-preflight/1`) records the SRC-027 review basis
   (link/label metadata + the committed queue row only), the prohibited
   content (plates, person/officer identifiers, per-query rows, workbook
   bytes incl. XLSX/ZIP/`sharedStrings`), the permitted metadata, the
   open safe-aggregate path for q8, and the preconditions (explicit
   content-admissibility + rights decision before ANY workbook transport).
   `workbook_transport` is `never`; SRC-027 is optional — the dossier does
   not depend on it.
10. **No fabricated review, no live fetch.** `review.status=not_run`
    (D-R10-HUMAN-1 OPEN) keeps `pilot_complete` honestly false while
    mechanical completeness reaches 29/36 with all required floors —
    the honest strongest result this corpus supports. The bounded live
    obligation is `sig.dossier-live-return-pass/1`
    (`prepared_not_executed`, deferral `D-P32.20-1`): the four registered
    targets plus five reviewed leads (the ALPR detail page, the ALPR Use
    Policy behind its recorded 403, the ~16 MB PAB recommendation PDF,
    the council/budget leads, and the metadata-only network-audit links),
    with HG-03/Part-VIII preconditions and explicit non-goals (no rights
    flip, no gate completion, no request sent, no publication, no workbook
    transport).
11. **Committed artifacts.** `sig-ops dossier-packet-san-diego --out
    docs/build/reports/p32.20-san-diego-dossier/` regenerates byte-
    identically: packet, dossier, portfolio, print HTML,
    `FOLLOW_UP_DRAFTS.json`, `EVIDENCE_PACK.md`, `LIVE_RETURN_PASS.json`
    and `PART_VIII_PREFLIGHT.json` — deterministic output a reviewer can
    diff against the committed set.

### Shared machinery adjustment — subject-partitioned conflict detection

Building the packet surfaced a real defect in
`exports.research_dossier._conflicts`: conflict grouping partitioned claims
by predicate + scope but **not by subject**, so two different vendors
(Vigilant Solutions on the subscription, Flock Safety on the contract)
collided as a false `disputed` q1. The fix partitions conflict detection by
`subject_id` first: same-subject, same-scope, overlapping-window
disagreement still flags `disputed`; different subjects describing
different measured things co-exist. Verified byte-identical on both landed
predecessor dossiers (OKC #175, Tulsa #176) — no landed output changed —
and covered by a new exports-level regression test plus the packet tests.

## Alternatives considered

- **Generalizing the OKC/Tulsa packet modules to take a city parameter.**
  Rejected (same reason as ADR-138): the per-city modules carry city-bound
  constants, locators and authored surfaces; parameterizing would entangle
  unrelated corpora. A San Diego-specific module consuming the shared
  machinery keeps each packet's authored surface reviewable.
- **Modelling q8 as wholly `unknown`.** Rejected: the ASR evidences the
  sharing *mode* verbatim — a vendor-hosted pool shared across subscribing
  agencies. Declaring the whole question unknown would under-report
  captured evidence; the honest shape is an evidenced inbound mode plus a
  declared-partial residual (outbound actors/edges), with `found` search
  entries naming the residual — enforced by the absence-fabrication
  release check.
- **Treating the ASR's non-ownership sentence as a universal absence or as
  streetlight-program evidence.** Rejected: it is scoped verbatim to "this
  arrangement" (the Vigilant subscription) — a `written_policy_value`, not
  a scoped count and not evidence about the physical program's inventory.
- **Calling the agreement executed (or hiding the asymmetric signature
  state).** Rejected: the vendor-side date is verbatim and the City date
  is `present_but_empty`; the honest genre is `procurement_record` +
  `contract`, execution unverified, follow-up drafted.
- **Preflighting the network-audit family by fetching workbook bytes (or
  skipping preflight entirely).** Rejected: Part VIII forbids transporting
  plate/person/query-row content absent an explicit admissibility
  decision, and "no record" would hide a named gated target; the
  metadata-only `sig.part-viii-preflight/1` is the honest middle — the
  gap is recorded with its preconditions and the dossier does not depend
  on it.
- **Marking `pilot_complete` or a completed review.** Rejected:
  D-R10-HUMAN-1 is OPEN — no independent reviewer exists on this build;
  `not_run` is the honest mark even though the rubric is mechanically
  complete.

## Revisit trigger

The live RETURN PASS executes (`live_verification=true` re-dispatch of the
same contract after HG-03 review decides the targets' lanes) — captured
bytes replace stand-ins and the packet is rebuilt from real captures; an
independent reviewer completes D-R10-HUMAN-1 and the review mark flips
from `not_run`; an executed/verified signature page, a council
adoption/rescission record, an installed-count inventory or the PAB
recommendation's full text is captured (the partials are re-graded); the
SRC-027 content-admissibility decision lands and an approved safe
aggregate closes the q8 residual; the technology index shows the 2025 ASR
superseded (the timeline gains a lifecycle record); or the dossier
machinery's subject partition needs refinement (e.g. subject-aliased
conflicts across equivalent subjects) — revisit under a new ADR or a
scoped amendment, never an in-place edit.
