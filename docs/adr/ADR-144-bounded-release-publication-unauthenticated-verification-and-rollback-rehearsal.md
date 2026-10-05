# ADR-144 — Bounded release publication, unauthenticated verification, and rollback rehearsal (P32.25)

- Date: 2026-10-20
- Status: accepted (engineering; `live_verification=false` — the bounded
  staging namespace only; production exposure stays under `D-R10-LIVE-1` /
  the production half of `D-R10-PUBLISH-1`, still OPEN)
- Ticket: P32.25 (Round 10 / S1, row 191; requirement SIG-TRUST-009;
  annotates `D-R10-PUBLISH-1`, `D-P32.23a-1`, `D-R10-LIVE-1`, `D-P32.16-1` —
  all stay OPEN)
- Base: `devin/p32-24-investigation-journey-verification` tip (PR chain of
  P32.24 / ADR-143)
- Gate: GATE-G3 (SIGNED 2026-10-19 — publish approved with recorded scope)

## Context

GATE-G3 signed the acceptance of the P32.23a fixture candidate — publication
`p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`, identity
`sha256:bc20d4bf…`, frozen snapshot `sha256:138714a6…` — under an explicitly
recorded scope: reduced/incomplete dossiers (`review.status=not_run`,
`pilot_complete=False`), intake receiver non-operational, evaluation
`deferred`. The gate's consequence line names P32.25: *execute the publish +
verify + rollback rehearsal for `p-17b713…`*.

The questions this ADR answers:

- What does "publish the accepted release" mean mechanically, such that a
  wrong byte, a partial deploy, or a mutated pointer can never masquerade as
  the signed acceptance?
- How are *unauthenticated public reads* verified — across compartments and
  citations — without a production serve existing to probe?
- What is the rollback contract for the **first** immutable release, which
  has no predecessor pointer to re-point at?
- How are the rehearsal's moving parts (a stand-in "prior release",
  withdrawal application, a corrupted deploy) kept honest — never conflated
  with the accepted subject, never mutating committed evidence?

One engineering fact surfaced during this work and drove part of the
decision: `exports.release` stages immutable bytes into a registry as
**hardlinks** into the release input dir, and `apply_withdrawals` wrote
tombstones *through* those links — silently mutating the release input
(P32.24's committed `corpus_release/` was corrupted this way: four record
routes carried `sig.tombstone/1` bytes while its integrity manifest still
pinned the record digests, so the committed dir no longer validated). The
P32.25 publish path cannot tolerate a machinery step that rewrites
supposedly immutable inputs.

## Decision

### `sig.release-publish-verification/1` — one proof over four layers

`ops.release_publish_verify` emits `PUBLISH_PROOF.json` +
`PUBLIC_VERIFICATION.md` with evidence-classed checks using the same
discipline as the journey portfolio (owner+landing enforced structurally on
any non-pass; verdict is fail-closed):

- **PF.\*** preflight — fail-closed pins before anything moves a pointer:
  the signed GATE-G3 readout must exist and name the exact publication,
  identity and snapshot; `CANDIDATE_MANIFEST` must equal the accepted pins
  (publication id, descriptor sha, release/export manifest shas, ruleset
  `provisional-ruleset/1`, evaluation `deferred`/`shadow`/`applied=[]`,
  `published=false`, validation `complete`); every one of the 18 manifest
  artifacts is re-hashed byte-for-byte; `DISCLOSURE` must carry the
  provisional/deferred posture (`resolved_sites=null`,
  `prior_preview_counts_reused=false`, 3 recorded dispositions); every
  dossier carries `review.status=not_run` + `pilot_complete=False`.
- **P.\*** publish — `activate()` on a **fresh** bounded registry only (a
  non-empty registry is refused so the pointer transition is observable):
  validate-first, `latest.json` last, `null → p-17b713…` recorded, catalog
  entry pinned, post-publish re-validation of the whole staged tree, the
  activation receipt.
- **V.\*** public verification — every manifest artifact re-hashes over the
  served tree *and* over real unauthenticated HTTP GETs from a throwaway
  static server (no credentials exist to send — "unauthenticated" is the
  honest shape); citations (`/r/<pub>` 'cite this URL' marking, the
  compat-index selector redirect, the bare-selector convenience answer, an
  honestly-`unavailable` pre-release selector); honest absences on this
  0-record fixture candidate (no record routes or entity stubs, search
  404 `unknown_compartment`/`unknown_publication` with no current-spine
  fallback, no tiles); the withdrawal barrier state (zero dispositions,
  empty deny map, every route permitted); suppressed slices loudly recorded
  in `exclusions.json`/`DISCLOSURE`; the provisional basis present on the
  published surface and *no* artifact asserting a completed pilot, a final
  evaluation, or a certified resolved-sites count; intake honestly
  unavailable (config flag, both env gates, 503 `receiver_not_operating`,
  no live submission link anywhere in the published bytes, no synthetic
  submission — none are authorized); zero-JS on every published page.
- **R.\*** rollback rehearsals in labelled scratch registries:
  `R.prior_release` (stand-in prior → candidate → `rollback(prior)`:
  pointer restored atomically, the candidate's unaffected bytes keep
  serving identically at their immutable routes — old citations preserved —
  and withdrawals recorded *between* activations keep denying under the
  rollback); `R.no_prior_pointer` (the candidate's real rollback shape);
  `R.refused_deploy` (a tampered bundle is refused by `validate_release`
  before staging — `latest.json`, catalog and served bytes byte-identical).

### `clear_latest_pointer()` — the no-prior-pointer rollback path

The ROLLBACK_PACKET recorded: *if no prior pointer exists, remove
`latest.json`* — never fabricate a predecessor. This lands as an additive
`exports.release.clear_latest_pointer(registry)`: it refuses when the
pointer is already absent (a missing pointer is never silently re-cleared),
re-applies the current withdrawal registry, drops the active-release entity
convenience stubs, removes `latest.json`, re-emits the overlay, and
receipts the action under `activations/`. Activated namespaces stay
reachable as immutable history; the catalog and compat index are untouched.

### Staged-tree writes can never mutate a release input

`apply_withdrawals` now breaks a hardlink (`os.stat().st_nlink > 1` →
`unlink`) before writing tombstone bytes over a staged artifact route —
`.json` routes and `index.html` routes alike. A staged file and its release
source may share an inode; a write-through corrupts the immutable input.
The committed `corpus_release/` damage was repaired deterministically:
`build_release(corpus_export, renderer_revision="p32.24")` regenerates the
corpus release byte-identically (same `p-81f1986a…` namespace), the four
corrupted routes were restored to their manifest-pinned bytes (the staged
`corpus_registry/` tombstone evidence is unchanged — the as-served truth
kept its deny map + tombstones), and the publish harness now stages from a
copy of the release input regardless.

### The stand-in "prior" is regenerated and labelled

`R.prior_release` needs *a* prior activated release; the only honest one in
repo is the committed P32.24 acceptance corpus (`sig.journey-corpus/1`).
The rehearsal regenerates it from the committed `corpus_export` — asserting
the rebuilt publication id equals `p-81f1986a…` — and the record labels it
a stand-in for "whatever pointer production holds at rollback time". It is
never described as a production predecessor: the accepted candidate is the
first immutable release, so its production rollback path is
`clear_latest_pointer`.

### `sig.release-publish-return-pass/1` — prepared, not executed

`LIVE_RETURN_PASS.json` pins the production command sequence (production
candidate under `D-P32.23a-1`; staged-tree deploy + deny map +
`sig-api serve --release-registry` + the unauthenticated probe under the
`D-R10-PUBLISH-1` production half), the live rollback instructions
(`rollback()` / `clear_latest_pointer()` / `record_withdrawal()`), and the
open deferrals verbatim — recorded, never claimed.

## Consequences

- The signed acceptance is proven to publish **atomically**: validate-first,
  pointer-last, and a corrupted deploy leaves the previous pointer
  byte-identical.
- Unauthenticated reads byte-match the approved digests across every
  manifest compartment and citation route; withheld slices and the
  withdrawal barrier behave; intake is verified *only* as honestly
  unavailable — `SIG-TRUST-009` coverage lands with the disclosed boundary.
- The rollback contract is complete for both pointer shapes (prior
  activated release; no prior pointer) plus the refused-deploy case — all
  receipted, all atomic.
- `apply_withdrawals` can no longer corrupt an immutable release input; the
  P32.24 artifact corruption is repaired and disclosed.
- The production public exposure remains exactly what it was: an open
  operator obligation (`D-R10-LIVE-1` return pass + `D-R10-PUBLISH-1`
  production half) — this ADR records the staging proof, never the serve.

## Alternatives considered

- **Verify over `file://` reads only:** rejected — the ticket asks for
  *unauthenticated public reads*; the throwaway HTTP server answers the
  same anonymous-reader question (200 + digest per route) with no
  production dependency.
- **Hand-roll the no-prior rollback in ops:** rejected — the overlay/compat
  semantics live in `exports.release`; a copy in ops would fork the
  contract the ROLLBACK_PACKET names. `clear_latest_pointer` is the
  additive home for it.
- **Activate the committed `corpus_release` as the rehearsal prior:**
  impossible as-committed (it no longer validated — the write-through
  corruption this ADR repairs) and fragile in principle; the deterministic
  rebuild asserts identity by `publication_id`, not by trust in a dir.
- **Report a `partial`/`staged` verdict tier:** rejected — `pass` with the
  recorded boundary + `prepared_not_executed` return pass is honest;
  anything else invites reading the staging proof as production evidence.

## Revisit trigger

- `D-R10-LIVE-1` closes / the operator's production return pass runs: re-run
  `sig-ops release-publish --candidate <production packet>` over the hosted
  registry, then execute the LIVE_RETURN_PASS deploy + probe sequence; the
  `D-R10-PUBLISH-1` production half closes only on a real public serve.
- `D-P32.23a-1` produces the production candidate: the preflight constants
  become *its* pins — a `/2` of this verification schema or a follow-on ADR
  if the accepted-input shape changes.
- A real "second release" exists: `R.prior_release`'s stand-in is replaced
  by the actual prior activation and `R.no_prior_pointer` becomes the
  historical case.
