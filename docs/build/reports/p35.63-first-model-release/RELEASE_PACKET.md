# P35.63 — first model release publish packet (prepared, not executed)

Ticket `341_P35.63__first-model-release-to-production.md` / R11-ACT-24 —
the `D-R10-PUBLISH-1` release-exposure return pass: the first model
release's staged cut, staging-origin verification, drafted readout,
promotion and live rollback rehearsal. **Status:
`prepared_not_executed` — nothing was staged, nothing was promoted,
nothing was verified on a staging or public origin, nothing became
reachable, and no signature was requested or given.** Both live legs
are queued; the verbatim re-run prompt below re-dispatches them when
the preconditions hold.

Machine-readable twin: `RELEASE_PACKET.json`
(`first-model-release-return-pass/1`).

## Authority — NEVER pre-authorised (the never-listed set)

Publication is in the GATE-G4 **never-list** verbatim: GATE DECISIONS
(LEDGER.md, 2026-10-09T17:32Z, GATE-G4 §4, kind `pre-authorization`)
records "the never-list stands (P35.11, P35.14b, P36.12, P35.61,
P35.63 and every HG-03 flip)". No OM-20 line covers this row and none
may be assumed. A Class S promotion is the **operator's** act: an
agent may never promote Class S, never sign, never renew, and never
treat silence as approval (G3 §7.3, verbatim in effect). The authority
is the operator's verbatim signed HG-11 candidate-specific readout +
the operator go — the GATE-G3 signature on `p-17b713…` is superseded
(E2-17 / Q-E2-18) and never transfers, never re-signed.

**The signature does not exist at this record.** `D-P35.60-1`
(operator adoption of the standing-go text and the first signed
Class-S readout) is OPEN — every agent-drafted readout's signature
slot is empty by construction, and an agent may only record what is
owed, never request or sign on the operator's behalf.

## Leg dispositions (both QUEUED)

- **L1 (dispatch): QUEUED** — stage the cut over the hosted registry →
  the full V1–V15 suite on the private staging origins → classify
  (expected `class_s`) → the agent-drafted candidate-specific
  readout. Zero production mutations, zero hosted writes, zero staged
  objects, zero verification reads ran.
- **L2 (operator): QUEUED — blocked on the signature** — the queued
  promote step (`conf/<gen+1>`, `latest.json`, rolls by digest, LB
  rules live, all queued) → the queued post-promote checks on the
  public origins → the queued live rollback rehearsal, each leg
  reversed and receipted. The leg waits for the
  operator's verbatim signed HG-11 readout, which does not exist;
  an agent may never promote Class S, so L2 queues in RETURN PASS.

## Precondition verdicts at 2026-10-25T03:1xZ (Sunday)

- **The HG-11 signature: UNMET** — no signed candidate-specific
  readout exists; `D-P35.60-1` OPEN; an agent never signs.
- **The staged candidate: UNMET** — `live:P35.62`'s staging leg is
  queued (packet `prepared_not_executed`, PR #360); read-only probes
  at this record found the private release bucket absent (404) — no
  staged candidate bytes exist.
- **The staged home: UNMET** — `live:P35.53` (`D-P35.53-1` OPEN,
  operator-owned OP-24) is still queued: bucket 404, both IAM-only
  staging services absent, the `sig-release` job and `sig-release-rt`
  absent (NOT_FOUND).
- **The dark cutover: UNMET** — `live:P35.59`'s leg is queued (window
  guard exit 42 on a Saturday outside the preferred band; its
  `live:P35.53` + `live:P34.40` L2 requirements are also queued); the
  release layout is not serving anywhere.
- **The upstream chain: UNMET** — `live:P35.61` (the snapshot input),
  `live:P34.46` (+ 48 h soak) and `live:P34.43` L1+L2 are all queued;
  probes found the `sig-quality-probe-rt` SA and both login secrets
  absent (NOT_FOUND).
- **P35.57 (API release parity): UNMET — recorded, never satisfied.**
  A listed dep that is currently an unlanded manifest row in
  `returnPass`: its API-roll leg is queued, and `D-P35.57-1` OPEN
  means no release yet carries the `sig.api-slice/1` set — V7 records
  `deferred` on the first real candidate and the slice emission rides
  the queued leg as an owed input.
- **Runtime environment: UNMET** — `SIG_GCP_PROJECT`,
  `SIG_EXEC_IMAGE`, `SIG_HOSTED_DSN`, `SIG_RELEASE_REGISTRY` and any
  login passwords are all unset; the gcloud default project is not
  the operator's.
- **AR-2: not taken** — a queued leg never reaches the restore-point
  step; recorded, not fabricated.
- **Window: note.** The run clock is a Sunday inside the never-mutate
  03:00–06:30Z band and outside 14:00–20:00Z; the release cut never
  runs inside AR-3 windows and the promote window needs the operator
  available — the signature and upstream preconditions bind first in
  any case.
- **PLAN-11C's scheduled window: met** — the planning row landed
  2026-10-25 as this row's PR base; the contract scheduled its writes
  during this row's wait.

**Exactly-once:** a re-staged cut of the same candidate is
byte-identical — immutability is enforced by the single writer,
versioning and the monthly digest audit (the contract's re-run line,
verbatim in effect); `staged/` writes stay create-only under
`if-generation-match=0` (SIG-REL-005).

## Re-run

**Re-run prompt (queued only — nothing in this row executed; no
probe-run/1 record exists):** `implement-spec spec=docs/tickets/341_P35.63__first-model-release-to-production.md live_verification=true` — queued, not executed. The contract's re-run line, verbatim: when the signature has not been given at run end, the follow-up resumes at the promote leg.

Next valid slot: the next weekday 14:00–20:00Z window with the
operator available, and only after every upstream leg has run —
`live:P35.53`, `live:P35.61`, `live:P35.62`, `live:P35.59`,
`live:P34.40` L2, `live:P34.46` + 48 h soak, `live:P34.43` L1+L2 —
and the operator's verbatim signed HG-11 readout exists for the
candidate's publication id. The release cut never runs inside AR-3
windows.

## Ordered command sequence (G2 step 7 + the landed verbs)

**L1 — the dispatch leg (all queued):**

0. Pre-state capture (the contract's OM-14 line): the AR-2 restore
   point (bucket versioning on); the current conf generation and
   `latest.json` bytes; the staged tree's manifest digests;
   `date -u`.
1. The queued release cut over the hosted registry (G2 step 7's
   command shape): `sig-ops release-publish --candidate <dir>
   --out <report>` — the staged half only at L1.
2. The queued full V1–V15 suite on the private staging origins
   (fail-closed — a check that cannot run fails):
   `sig-ops release verify --mode S --work-dir <built tree>
   --origin <staging> --api-origin <api-staging>
   --results-dir <results>` — V1 integrity, V2 identity and clock,
   V3 route allow-list and absence, V4 stamp and manifest, V5–V9
   (the REL-04a/b landed split), V10 withdrawal barrier on every
   alias, V11 zero-JS/budgets/a11y, V12 scrub and secret scan,
   V13 disclosures, V14 diff sanity, V15 (the REL-04b tail).
3. The queued classify (expected `class_s`):
   `sig-ops release classify --publication <pub> --results <results>
   --apply` — consumes the emitted V14/V15 docs verbatim, never
   re-measures; fail-closed `class_s` on the first model release.
4. The queued agent-drafted candidate-specific readout — classify
   `--apply` emits the `sig.release-readout/1` pair under
   `registry/readouts/` naming the new publication id, true dates,
   the approved artifact digests, the disclosures and the route
   list; states verbatim "single maintainer, no second reviewer" and
   "no human check performed"; carries the residual-miss known-issue
   lines; signature slot empty by construction; the pending-readout
   notice rides the alerts seam.
5. The queued P32.25 packet regenerated for the new publication id —
   never `p-17b713…`'s.

**L2 — the operator leg (all queued, blocked on the signature):**

6. The operator signs the drafted readout verbatim (HG-11); the
   signed record lands under `registry/approvals/` — an agent never
   writes it.
7. The queued promotion, post-signature only:
   `sig-ops release promote --publication <pub> --approval
   <signed-readout-object> --apply` — `conf/<gen+1>` writes
   (`promoted.map`, `latest.json`, `withdrawn.conf`,
   `selectors.conf`, `labels.conf`, `releases/`), the `sig-api` then
   `sig-web` rolls by digest (`min-instances=1` through the flip),
   the LB path rules live only after the signature (`/v1/releases/*`
   → the api NEG, `/intake/*` → the receiver — `live:P34.40`'s dark
   topology), and the publish-tree object uploads (~475 k objects)
   through `publish-web --apply`.
8. The queued post-promote checks on the public origins (P-mode
   suite): digest match on every manifest route; the ACT-16 crawl
   live, still a queued read; absence probes for non-allow-listed
   routes; `latest.json` as intended; `/v1/releases/…/search` 200;
   the `+0` re-run.
9. The queued live rollback rehearsal, each leg reversed and
   receipted: (i) `clear_latest_pointer` on the no-prior-pointer
   case → `/releases/` shows no latest while `r/<pub>` stays
   reachable, a queued probe outcome; (ii) a `record_withdrawal` on
   one low-stakes record →
   410 tombstone on every alias after the roll; (iii) prior-release
   pointer rollback — recorded NOT rehearsable on the first real
   release, rehearsed on the second.
10. The queued allow-list expansion — archive + pinned citations +
    release search first (Q-9/G2-HOTFIX [B-7] = a, verbatim);
    research-dossier routes and `/intake/` stay dark under their own
    rows.
11. The queued ratchet read (FEA-11): zero ratchet regressions and
    zero failures on enforce-flipped checks — recorded in the
    readout; absolute Stream-L targets stay moved to P37.67
    (CONF-14); residual misses are known-issue lines, never hidden.
12. The closing re-dispatch (G2's closing command, verbatim):
    `implement-spec spec=docs/tickets/191_P32.25__accepted-release-public-verification.md live_verification=true`.

## Machinery checks — the landable-now half

Every verb the queued legs name is landed and green under the suite
(`sig-ops release {cut,build,stage,verify,promote,classify,rollback,
clear-latest,withdraw,import-floor,cutover,status}` +
`release-publish`; P35.53/54/55/56/58/60, P34.10). The
drafted-readout generation path was exercised end-to-end at this
record on a local fixture-registry copy:
`sig-ops release classify --publication p-aaaa… --apply` →
fail-closed `class_s` on unevaluable suite input (the expected class
for the first model release), the `classified` event journaled, the
`sig.release-readout/1` pair emitted under `registry/readouts/` with
`agent_drafted: true`, `signature: null`, both verbatim statements
present, and the `release.readout-pending` notice fired on the
alerts seam — the draft is agent-labelled and unsigned by
construction, exactly as the contract requires before the operator
signs.

## Verify (what a green pass looks like)

The staged cut's packet exists — candidate dir, registry target, the
regenerated P32.25 packet naming the new publication id, the drafted
readout with the two verbatim statements and the known-issue lines;
the full V1–V15 suite green on the private staging origins with zero
waivers unless the Class S readout records them; the classifier
returns `class_s`; the operator's verbatim signature and go recorded
with `date -u` before any promote; post-promote checks green —
digest match on every manifest route, the live crawl passes, absence
probes refuse non-allow-listed routes, `latest.json` as intended,
`/v1/releases/…/search` 200, the `+0` re-run; the rehearsal recorded
with every leg reversed and receipted (the prior-pointer leg
recorded not-rehearsable); archive, pinned citations and release
search serve the new publication id with nothing else allowed; the
ratchet read reports zero regressions and zero enforce-flipped
failures.

## Explicit reservations

- `D-R10-PUBLISH-1` stays OPEN until the real exposure lands — this
  row reports two queued legs, not a landed release; no lead-token
  change and no `obligation-event/1` transition is owed. The
  receiver half stays owed until the intake operation lands and is
  never silently marked.
- NEVER pre-authorised — publication is in the GATE-G4 never-listed
  set; an agent may never promote Class S, never sign, never renew,
  never treat silence as approval.
- The GATE-G3 signature on `p-17b713…` is superseded (B-4/E2-17) and
  never transfers; the appended supersession record stands, never
  re-signed, never edited.
- No gate tick, no source-rights flip, no human label, no signature
  — HG-01/HG-02/HG-11 stay the operator's.
- Credentials and secrets stay environment-only (HG-09); the project
  id and bucket names are never literal in any tracked file.
- P35.57 stays recorded as an unlanded precondition input — the
  dep is never silently treated as satisfied.
- The candidate `P35.63a`/`P35.63b` split decision is C13's — this
  row is contracted whole and nothing here pre-splits.
- Immutable namespaces are withdrawn, never deleted; a defect found
  mid-leg pauses and records — machinery is never patched during the
  leg.
- Release trees and staging registries are evicted from the public
  repository (G3 NEW-5) — the executed packet records land beside
  the prepared one; the candidate tree never commits.
- `D-P32.23a-1`, `D-R10-LIVE-1`, `D-P35.53-1`, `D-P35.60-1`,
  `D-P35.57-1` and `D-P35.56-1` stay OPEN with their owners — the
  candidate, the snapshot, the staged home, the signature source,
  the api-slice emission and the catalog.jsonld gap are all still
  owed.
