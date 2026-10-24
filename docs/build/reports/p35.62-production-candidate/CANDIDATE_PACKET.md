# P35.62 — production-candidate staging return packet (prepared, not executed)

Ticket `339_P35.62__round10-production-candidate.md` / R11-ACT-15 —
the `D-P32.23a-1` return pass: the real production release candidate
over the hosted frozen snapshot, staged into private namespaces.
**Status: `prepared_not_executed` — no candidate build ran, no
staged object was written, no hosted read was attempted and nothing
was published.** The one staging leg is queued; the re-run prompt
below re-dispatches it when the preconditions hold.

Machine-readable twin: `CANDIDATE_PACKET.json`
(`candidate-staging-return-pass/1`).

## OM-20 authority (the listing stands)

GATE DECISIONS (LEDGER.md, 2026-10-09T17:32Z, GATE-G4 §4, kind
`pre-authorization`) names this row verbatim — the 19-row 11B list
includes **P35.62**; the operator answer was "Approve all 19 (rec.)".
The authorised mutation set is exactly: write the staged release
candidate (materialize under the active decided ruleset → the
compartmented export → the staged release-namespace bytes under
`staged/` in the private `…-sig-release` bucket → the export-mode web
build artifacts staged on the IAM-only staging origins). **No
publication, no `latest.json` change, nothing publicly reachable.**
The listing expires at the next sub-round gate (GATE-G5, or GATE-G4b
if the re-split rule fires) and is voided by any later operator row —
if the queued leg runs after expiry a fresh listing is owed, never
assumed.

## Precondition verdicts at 2026-10-24T20:20Z (Saturday)

- **The OM-20 listing: MET** — named verbatim on GATE-G4 §4 (above).
- **The input snapshot: UNMET.** The candidate pins
  `<live-apply>/REPAIRED_SNAPSHOT.json` — a
  `sig.repaired-snapshot/1` `frozen_unpublished` record that
  `live:P35.61`'s L3 leg would produce — and every `live:P35.61`
  leg is still queued (its `LIVE_PASS_PACKET` is
  `prepared_not_executed`, PR #359). No hosted repaired snapshot
  exists; the only in-tree `REPAIRED_SNAPSHOT.json` files are the
  P32.22/P32.23a fixture artifacts, never a hosted one.
- **Upstream `live:` rows: UNMET.** `live:P34.46` (the Round-10 schema
  deploy + roll + 48 h soak) and `live:P34.43` L1/L2 (the exec host
  and the `sig_audit`/`sig_recovery` logins) are still queued —
  read-only probes at this record found the `sig-quality-probe-rt`
  runtime SA and both login secrets absent (NOT_FOUND).
- **The staged home: UNMET.** `live:P35.53`'s release-infra leg
  (`D-P35.53-1` OPEN) is still queued — read-only probes at this
  record found the private release bucket absent (404), both
  IAM-only staging services absent, the `sig-release` job absent
  and `sig-release-rt` absent (all NOT_FOUND).
- **Runtime environment: UNMET.** `SIG_GCP_PROJECT`,
  `SIG_EXEC_IMAGE`, `SIG_HOSTED_DSN` and any login passwords are all
  unset in this shell; the gcloud default project is not the
  operator's.
- **AR-2 restore point: not taken** — a queued leg never reaches the
  restore-point step; recorded, not fabricated.
- **AR-3 window: note.** The run clock is a Saturday ~20:20Z —
  outside the preferred weekday 14:00–20:00Z slot; the credential
  and host-state preconditions bind first in any case.

**Exactly-once:** a second stage of the same candidate is a no-op
diff under `if-generation-match=0` — identical bytes resume-skip
(counted, never rewritten) and a same-named object with different
bytes is a name-collision refusal (SIG-REL-005).

## Re-run

**Re-run prompt (queued only — nothing in this row executed; no
probe-run/1 record exists):** `implement-spec spec=docs/tickets/339_P35.62__round10-production-candidate.md live_verification=true` — queued, not executed.

Next valid slot: the next weekday 14:00–20:00Z once every
precondition holds — earliest Monday 2026-10-26T14:00Z, and only if
`live:P34.46` (+ its 48 h soak), `live:P34.43` L1+L2, `live:P35.61`
(the snapshot input) and `live:P35.53` (the staged home + staging
origins) have all run by then — later in practice.

## Ordered command sequence (G2 §4 step 3 verbatim + the stage verb)

0. Pre-state capture (the contract's OM-14 line): the bucket
   `staged/` listing, `latest.json`'s bytes (byte-identical after),
   the frozen snapshot digest, `date -u`.
1. The queued candidate build —
   `uv run sig-ops release-candidate --dsn $SIG_HOSTED_DSN`
   `--snapshot <live-apply>/REPAIRED_SNAPSHOT.json --plan <plan>`
   `--audit <audit> --apply-report <live-apply>/APPLY_REPORT.json`
   `--registry <release registry> --out <candidate>/` — frame-verify
   fail-closed on changed input, +0 rematerialize, the compartmented
   export (`web/leverage.json`, `web/tiles/*-sites.pmtiles`,
   `web/releases.json`), the staged release namespace, disclosure +
   rollback packet + manifest.
2. The queued staged write (the authorised mutation) —
   `sig-ops release stage --registry $SIG_RELEASE_REGISTRY_URI`
   `--work-dir <candidate>/candidate_release --apply`:
   `staged/{r,v,s,releases}/<pub>/` + the staged `releases/` index,
   `if-generation-match=0` create-only; the export-mode web build
   artifacts staged on the IAM-only staging origins for the
   crawl/budget legs.
3. The queued export-mode web build —
   `SIG_DATA_SOURCE=export SIG_EXPORT_DIR=<candidate>/candidate_export`
   `npx astro build` (the C4 command).
4. The queued verification legs over the staging origins
   (identity-token access, never public): the DR-C4-01 link crawl
   (no non-200 same-origin link except declared 410s), real-data
   island budgets + Lighthouse (DR-C4-13, C4 NEW-25), and the
   unauthenticated probe of both staging origins refused.
5. Post-state verification (the contract's line): the manifest
   validates — `consistent` frame, `materialization.plus_zero`,
   validation `complete`, `pointer_unchanged: true`,
   `published: false`; every manifest cites the same identity
   digest; `eval-confidence/1` shadow with `applied=[]`; the
   disclosure provisional/review-only; no date later than the build
   clock anywhere in the tree; `latest.json` byte-identical
   before/after.
6. The executed records land beside
   `docs/build/reports/p32.23a-release-candidate/LIVE_RETURN_PASS.json`
   (append — the prepared record is never rewritten), then the
   closing re-dispatch (G2 verbatim): `implement-spec
   spec=docs/tickets/188_P32.23a__post-evaluation-release-candidate.md
   live_verification=true`.

## Verify (what a green pass looks like)

The candidate packet exists with the pinned snapshot digest, the
recorded ruleset and the executed command sequence before the
staging write lands; the population frame reconciles digest-for-digest
to the snapshot the queued leg pins; rematerialization is dependency-ordered
with a `+0` rerun; the release namespace validates `complete` and
every manifest cites the same identity digest;
`eval-confidence/1` stays shadow with `applied=[]`; the disclosure
is provisional/review-only and quotes no prior preview count; no
date later than the build clock appears anywhere in the tree;
`latest.json` is byte-identical before/after; the unauthenticated
probe of both staging origins is refused — a staged candidate is
not publicly reachable; nothing is promoted — the `live:` edge runs
to P35.63, whose first model release names this candidate's
publication id.

## Explicit reservations

- `D-P32.23a-1` stays OPEN until the candidate actually lands —
  this row reports a queued leg, not a landed pass; no lead-token
  change and no `obligation-event/1` transition is owed.
- No publication, no HG-11 tick, no source-rights flip, no human
  label, no signature — the GATE-G3 signature on `p-17b713…` is
  superseded (B-4) and never transfers; the appended supersession
  record stands, never re-signed, never edited.
- `activate()`/`rollback()` are never called; the publication
  pointer is read before and after staging and a drift is a hard
  failure.
- Credentials and secrets stay environment-only (HG-09); the
  project id and bucket names are never literal in any tracked
  file.
- The queued hosted reads run inside AR-3 etiquette; the staging
  writes carry the AR-2 restore point as any bucket write does.
- A defect found mid-pass pauses and records — machinery is never
  patched during the leg.
- A resumed-S3 measured evaluation decision replaces
  `status=deferred` in a NEW candidate — never a mutation of this
  one (the deferral's own rule).
- Release trees and staging registries are evicted from the public
  repository (G3 NEW-5) — the candidate tree never commits; the
  executed packet records land beside the prepared one.
- The five-measure metrics verification (SIG-CHART-034's open
  PARTIAL) rides this leg on the real candidate — recorded as owed,
  never implied done.
- `D-R10-LIVE-1` and `D-P35.53-1` stay OPEN with their owners — the
  snapshot input and the staged home are still owed upstream legs.
