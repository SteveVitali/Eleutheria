# ADR-096 — National public cut-over publishes only the non-share-alike published compartment

- **Status:** Accepted
- **Phase / ticket:** Phase 27 / P27.8 (`docs/tickets/P27.8__deploy-and-public-cutover.md`) — the national deploy + public cut-over
- **Date:** 2026-09-22
- **Related:** §42 / §42.3 (SIG-LIC-005/006 — the ODbL posture), §38 (exports), ADR-090/094 (national surface + rights resolution), the publication gates HG-01/HG-11/HG-02, `D-LEGAL.1-1` (counsel), `D-P27.8-1` (the deferred hosted cut-over).

## Context

`sig-ops deploy --target gcp` syncs the static site (`web/dist`) plus the licence-compartmented
export to GCS: `exports/out/public` → the public-read `…-sig-public` bucket, `exports/out/restricted`
→ the PRIVATE `…-sig-restricted` bucket. But nothing produced that public/restricted split — the
export writes **per-compartment** subtrees (`sig_graph/` CC-BY-4.0, `osm_physical/` ODbL-1.0,
`portal/` CC-BY-SA-4.0, `web/`, …) and no code classified them into a public vs private set. The
OKC demo cut-over (2026-09-16) synced the *whole* per-jurisdiction export — including the ODbL
`osm_physical/` layer — to `…-sig-public/okc`, resting on §42.3's "publish the ODbL layer as a
separate file." Taking the whole **national** surface public (~1.06M claims, 210 sources) raises the
share-alike obligation and the sensitive-data exposure by orders of magnitude, while the second
independent reviewer (HG-11) and dated counsel opinions (HG-02, incl. the ODbL 4.4(b) opinion) are
still owed. A national cut-over needs a conservative, fail-closed definition of "the published
compartment" and a proof that nothing else leaks into a public object (§42 / Part VIII).

## Decision

1. **A compartment is public iff its licence is non-`share_alike` and carries no recorded export
   exclusion; otherwise it is restricted.** The rule is data-driven off `policy/data/licenses.toml`
   (`ops/src/ops/publish.py:classify_compartment`), so ODbL-1.0 and CC-BY-SA-4.0 (both
   `share_alike = true`), every `UNDETERMINED`/unknown licence, and any counsel-pending excluded
   licence resolve to **restricted** — the national CC-BY published graph + the `web/` surfaces +
   metadata go **public**. Adding a source under a new share-alike licence stays restricted with no
   code change.
2. **The producer partitions, and a guard proves the result.** `partition_export` copies each
   manifest artifact into `exports/out/public` or `exports/out/restricted` by that rule;
   `assert_public_clean` re-scans the public tree and fails loud (`CompartmentLeak`) on any
   share-alike / UNDETERMINED / excluded artifact — belt-and-suspenders so a producer bug cannot push
   a restricted byte to a public object. The deploy runs build → partition → assert-clean **before**
   any sync.
3. **The public build reads the real national export or fails loud.** `web/dist` is built with
   `SIG_DATA_SOURCE=export` against `exports/out/national` (the P27.4 bundle); there is never a
   fixtures fall-back for the public build (§38.1).

## Consequences

- The ODbL national OSM-derived layer is **not** published in the CC-BY public bucket at this cut-over
  — it stays in the private restricted compartment. This is a deliberate, conservative tightening over
  §42.3 (which *permits* publishing the ODbL layer as a separate file): §42.3 governs **how** the ODbL
  layer is published if/when it is, not that it must ship in the same public bucket as the CC-BY graph.
  Its public release is a dedicated, gated decision pending the ODbL 4.4(b) counsel opinion
  (`D-LEGAL.1-1`) and the share-alike attribution/serving posture; until then it is compartmented
  private, consistent with the P27 launch posture ("ODbL/share-alike stay compartmented", ADR-094).
- "Only the published compartment goes public" becomes an enforced, tested invariant rather than an
  operator convention — a national-scale safeguard.
- The classification is licence-driven, so it needs no per-compartment flag and adapts as new licences
  are added to `licenses.toml`.

## Alternatives considered

- **Publish every redistributable compartment (incl. ODbL) to `…-sig-public`, per the OKC precedent.**
  Rejected for the national surface while HG-11/HG-02 remain owed: it maximises the share-alike +
  Part VIII exposure exactly when the governance safeguards are least complete. Revisitable once
  counsel signs off (see the trigger).
- **Add a `public`/`restricted` flag to every `[compartments.*]` row.** Rejected — more data churn and
  a second source of truth that can drift from the licence facts; the `share_alike` flag already
  encodes the distinction that matters here.
- **Classify at sync time in the shell script.** Rejected — the classification is a fail-closed policy
  decision that belongs in tested Python with a leak guard, not in an un-unit-testable `gcloud` step.

## Revisit trigger

- HG-02 counsel records a dated ODbL 4.4(b) opinion (`D-LEGAL.1-1`) and the operator decides to
  publish the national ODbL layer — add an ODbL public compartment/bucket and widen the classifier in
  a new ADR (the ODbL layer then ships as a separate public file per §42.3).
- A new non-share-alike licence must nonetheless stay private (e.g. a sensitive government feed) — the
  licence-only rule no longer suffices and a per-compartment restriction flag is introduced in a new ADR.
