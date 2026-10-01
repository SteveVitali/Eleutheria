# ADR-132 — Immutable release namespaces: pre-render identity, acyclic integrity manifest, access-time withdrawal barrier (P32.13)

- Date: 2026-09-27
- Status: accepted (engineering; **offline tooling only** — nothing is deployed or published; public exposure stays with GATE-G3)
- Ticket: P32.13 (Round 10 / S4, row 173; requirements SIG-FIND-001, SIG-FIND-002)
- Base: the P32.12 chain tip `devin/p32-12-dossier-document-adapters` (PR #168, stacked on P32.11)

## Context

The public product must be historically citable: a citation minted against
release R must resolve to the same bytes forever, a later withdrawal must
bite even under a rollback to an earlier release, and licence compartments
must stay separated under the `/r/` namespace exactly as they are in the
export bundle (§42.3, ADR-011). SIG-FIND-001 requires deterministic,
immutable release namespaces; SIG-FIND-002 requires specific, stable,
release-scoped public record routes — beyond any first-500 cap — with
honest tombstones instead of stale or fabricated pages.

Two failure modes define the design space:

1. **The hash cycle.** If the final artifact digest is embedded in a page
   the manifest covers, the digest authenticates bytes that contain the
   digest — uncomputable and forgeable. Release identity therefore cannot
   be "hash of the emitted tree" alone.
2. **Rollback resurrection.** If withdrawal state is baked into a
   release's bytes, selecting an older release silently re-publishes
   withdrawn records. Withdrawal must be enforced against *current*
   dispositions at access time, independent of which release is mounted.

## Decision

**Release identity is two-stage, and mutable serving state lives outside
the hashed bytes** (`exports/src/exports/release.py`,
`published_record.py`, `release_pages.py`).

1. **Pre-render namespace.** `publication_id = "p-" + sha256(canonical
   sig.publication-descriptor/1)` is a pure function of intentional,
   ID-free inputs: the input export manifest digest, data-release id,
   both as-of cuts, ruleset/resolver versions, the publication-eligibility
   policy version, the projection schema id, renderer identity+revision,
   and a per-compartment projection root hashed over
   `sig.published-record/1` documents that contain **no publication id
   and no URLs** (the record is projected first, then *bound* to the
   namespace). Any parser, policy, projection, renderer, or input change
   mints a different namespace; identical inputs reproduce it exactly.
2. **Acyclic post-render integrity.** `manifest_sha256` is computed over
   the canonical `sig.release-integrity/1` manifest listing every emitted
   artifact's (path, media type, compartment, licence, bytes, sha256) —
   after render. It is never embedded in an artifact it covers: the hash
   graph is artifacts → manifest → digest → catalog entry → latest
   pointer. `validate` re-hashes the whole tree and fails closed.
3. **Immutable namespace, mutable registry.** Under
   `r/<publication_id>/` bytes never change after activation —
   a same-namespace/different-bytes stage attempt is refused. The mutable
   state (`catalog.json`, `latest.json`, `compat_index.json`,
   `withdrawals.json`, `activations/` receipts) sits beside it; the
   latest pointer flips via write-then-`os.replace` and rollback re-points
   it to any earlier activated release.
4. **One withdrawal rule, evaluated at access time.** Denial reuses the
   single P32.5 rule — `policy.eligibility.access_decision` over
   `DispositionRecord` rows — applied to the staged tree *and* to the
   generated nginx deny map that matches before any origin file access
   (`ops/web/nginx.conf`, `ops/src/ops/release_serving.py`, and the
   `db.artifact_eligible_sql` twin for serving-side checks). A claim
   withdrawal tombstones every record carrying it; an entity withdrawal
   tombstones that entity's routes in every compartment; a release
   withdrawal denies the whole namespace. Tombstones are honest pages/
   documents (`sig.tombstone/1` + a no-JS HTML page) that state the reason
   class — never a fabricated record, never a silent 404 for a formerly
   cited route.
5. **Specific record routes, zero-JS.** Records are addressable at
   `/r/<pub>/c/<compartment>/entity/<entity_type>/<entity_id>.json` and
   `/…/index.html`, with claim (`#claim-…`) and evidence anchors, plus
   release landing, per-compartment browse, and catalog pages — static
   HTML with no `<script>` (the public zero-JS budget). Convenience URLs
   (`/entity/<type>/<id>`) render stubs that say explicitly they are not
   immutable citations; `release resolve` maps a legacy
   `?as_of_world=&as_of_belief=&ruleset=` selector to a real activated
   release or an honest `invalid`/`unavailable`/`ambiguous` — never a
   guess.

## Consequences

- `sig-exports release` gains `build`, `validate`, `activate`, `rollback`,
  `withdraw`, `apply-withdrawals`, `resolve`, `check-access`, `measure` —
  all offline; publication remains GATE-G3's.
- Measured on the checked-in national export: **236,994 records →
  475,112 files, 2,003,117,283 bytes, ~98 s wall, ~0.9 GiB peak RSS** —
  far beyond the 500-record cap (stored in
  `release/generation_measurement.json`).
- `ops` now depends on `sig-exports` (staged-tree withdrawal application)
  — a runtime composition edge, not a new pipeline stage.
- Every record route beyond the first 500 exists by construction: routes
  are enumerated from the compartment projection, not paginated from a
  capped index.
- A later withdrawal remains effective under rollback because the deny
  decision consults the *current* registry, not bytes frozen at release
  time.

## Alternatives considered

- **Content-hash the whole emitted tree as the release id.** Rejected:
  embedding that digest in a landing/catalog artifact it covers is a hash
  cycle; excluding artifacts ad hoc makes "the release" ill-defined.
  The two-stage split (ID-free descriptor → namespace; emitted tree →
  external manifest digest) keeps both properties.
- **Bake withdrawal state into release bytes.** Rejected: it makes
  rollback a silent republication path and couples an access decision to
  render time. The access-time barrier keeps one policy locus
  (`policy.eligibility`) and one registry.
- **Serve records dynamically from the spine.** Rejected: the public
  surface is static/Astro and zero-JS; dynamic serving would reintroduce
  a mutable path in front of immutable citations. Static records +
  an edge deny map give the same denial semantics without an app server.
- **Redirect convenience URLs straight to `/r/latest/…`.** Rejected:
  `latest` moves, so a `/r/latest/` citation silently retargets; stubs
  that state "not an immutable citation" keep the honesty requirement
  while still being useful.

## Revisit trigger

Revisit if the deployment target cannot express a pre-origin deny map
(the access-time barrier must move into the origin layer), if
`sig.publication-descriptor/1` needs new intentional inputs (descriptor
version bump — namespaces change globally, which is correct but must be
communicated), if 475k-file static trees exceed hosting limits (a
packing/sharding scheme would be a new ADR), or if withdrawals gain
semantics the single `access_decision` rule cannot express.

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): LIKELY FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger likely fired:** public bucket origins bypass the nginx deny map: `sig-web` is
allUsers-readable (G1 NEW-5) and bulk data is served straight from GCS (J1 NEW-12; F3 §5.1). **Answer:** row
P34.3 makes `sig-web` non-public, P34.21b removes anonymous read/list on the 09-27 release tree, P35.5 moves
downloads to the zero-egress R2 host, and P35.12 writes ADR-161 (release model v2) and appends its own
`Extended by ADR-161` line here (plan §7, S6R-24). The decision above stays in force until that answer lands;
this ADR's body is unchanged (SIG-ENG-003).
