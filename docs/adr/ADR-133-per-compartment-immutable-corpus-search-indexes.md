# ADR-133 — Per-compartment immutable corpus search: emitted SQLite FTS5 index artifacts, verified read-only mount, cursor-bounded queries, access-time withdrawal filtering (P32.14)

- Date: 2026-09-27
- Status: accepted (engineering; **offline tooling only** — nothing is deployed or published; public exposure stays with GATE-G3)
- Ticket: P32.14 (Round 10 / S4, row 174; requirement SIG-FIND-003)
- Base: the P32.13 chain tip `devin/p32-13-immutable-release-namespaces` (PR #169, stacked on P32.12)

## Context

P32.13 made released corpora citable byte-for-byte but left discovery: the
`/search` surface ran against a capped current/sample projection (the old
island enumerated at most 500 committed sites and grouped at most 100 hits)
and nothing could answer "which records of release R, compartment C match
`q`" or walk the tail of a ~237k-record corpus. SIG-FIND-003 requires
searching the *full eligible released* corpus of a selected
(publication, compartment) — including unlocated sites and
`jurisdiction: unknown` records — with bounded responses, exact-identifier
lookup, facets, and pagination that provably reaches the tail.

Four constraints pin the design:

1. **Immutability.** The index must be an artifact *of* the release —
   reproduced byte-for-byte from the released records, covered by the
   integrity manifest, versioned with the namespace (ADR-132). An index
   built from the live spine would drift from the bytes it claims to
   serve and would silently fall back to a *current* projection — the
   exact defect the ticket names.
2. **Compartment purity.** Licence compartments may never be searched
   together (§42.3, ADR-124): one index per compartment makes a
   cross-compartment query structurally impossible and keeps an ODbL
   fault from degrading every compartment.
3. **Rollback safety.** A withdrawal recorded after a release must deny
   its records even when an older release is mounted (ADR-124's
   access-time rule). The index therefore stores *what was released*, and
   withdrawal is filtered at serve time over the current disposition
   registry — exactly the barrier ADR-132 applies to artifacts.
4. **Blast radius.** The ticket forbids a search cluster. At ~0.24M
   records per compartment, an embedded engine serves the corpus from a
   single file per compartment with no new runtime service.

## Decision

**One deterministic SQLite FTS5 index per compartment is an emitted,
hashed release artifact; the API mounts it read-only after verifying the
integrity manifest, descriptor and index contract, and filters every
result through the current disposition registry at query time.**

### 1. The index artifact (`exports/src/exports/search_index.py`)

`sig-exports release` runs `build_search_index` per compartment after the
record tree is emitted:

- `records_fts` — FTS5 (`unicode61`, contentless) over the searchable
  columns `label`, `entity_id`, `source_id`, `jurisdiction`, sharing
  rowids with `records`.
- `records` — the normalized projection (record_seq/record_key,
  entity_id/type, label + `label_sort` sort key, jurisdiction NULL →
  `unreported`, `location_kind`, source, technology, claim ids), with
  covering indexes for the keyset order and every filter column.
- **One record per namespace.** `record_key` is `UNIQUE`, which surfaced
  a latent input defect: the national `portal` compartment carries 4,369
  duplicate site rows for the same `(entity_type, entity_id)` — the same
  deployment re-extracted through a second rights registration. The
  release build now deduplicates site rows *before* projection
  (`_iter_unique_site_rows`: first occurrence wins, `claim_ids` unioned,
  drops counted in `duplicate_rows_dropped`/`site_rows` so
  export→index→route totals still reconcile); the projection root,
  emitted tree and search index all see the same unique record set.
- `identifiers` — `(norm_id, record_key)` over entity id, the full
  record key and every claim id, so an identifier query resolves the
  record regardless of FTS tokenization.
- `facets` — `(facet, value, record_key)` rows for `kind`, `jurisdiction`,
  `source`, `location` (`public-point` / `no-public-point`) and
  `technology` — the last honestly absent on the national corpus: the
  facet exists, its counts do not pretend.
- `meta` — the contract stamp (`sig.release-search-index/1`, format
  version `release-search-index/1`, tokenizer/sort/cursor versions,
  scope counts, the recording SQLite version).
- **Determinism** — insertion order is canonical (`record_key` order in
  one transaction), no wall-clock is written, page size,
  `application_id` and `user_version` are pinned: two builds of the same
  input on the same SQLite library are **sha256-identical** (asserted by
  test; the recording version is pinned in `meta` + the descriptor so a
  library change is visible, never silent). `search_index.json` and
  `search_index.sqlite` both enter `sig.release-integrity/1`;
  `search_index_version` joins the publication descriptor, so a format
  bump mints a new namespace rather than silently changing an old one.

### 2. The query engine

- Word `q` → FTS5 `MATCH` (each token a quoted string, space = AND — no
  FTS grammar is ever exposed to the caller); an identifier-equal `q`
  short-circuits through `identifiers` first.
- No `q` ⇒ **browse mode**: `ORDER BY (label_sort, entity_type,
  entity_id)` scan under the same cursor/bounds — the complete corpus
  tail is enumerable and the same route backs the complete static browse
  pagination.
- Filters AND-join on the normalized columns; an unmatched value yields
  honest empty — the filter is never silently dropped.
- **Keyset cursor (format v1)**: base64url canonical JSON binding
  publication, compartment, a normalized query+filter fingerprint and the
  last emitted `(label_sort, entity_type, entity_id)` key. Malformed ⇒
  422 `malformed_cursor`; a release, compartment, query or filter change
  ⇒ 409 `cursor_context_mismatch` — a foreign cursor can never skip or
  duplicate rows for the release it addresses.
- Hard bounds enforced inside the engine: `limit ≤ 50`, canonical-JSON
  body ≤ 100 KiB (tail rows dropped with `truncated: true` and the cursor
  re-minted rather than ever exceeded), a 2-second deadline enforced by
  progress handler *and* per-row check ⇒ explicit `query_timeout` (503 +
  Retry-After); `q > 200` code points ⇒ 422 `query_too_long`; a bare
  text token under 3 chars ⇒ 422 `query_too_short` unless it is an exact
  identifier or a jurisdiction facet value; unknown params/filter values
  ⇒ 422 `unsupported_query`.

### 3. Access-time withdrawal (`api/src/api/release_search.py`)

The index is evidence of what was released, never of what may be shown.
Every serving path recomputes denied entity/claim targets from the
release registry and drops denied rows *before* pagination (pages stay
dense, the cursor tracks the last emitted key — nothing withheld leaks,
nothing is duplicated); a withheld whole release or index artifact
returns `withdrawn` (410) per ADR-132. A rollback to R1 under an R2
withdraw therefore denies under R1 — the same access-time disposition
rule, now applied to a derived index.

### 4. The mount contract

`ReleaseSearchStore` stages only verified local files: it checks the
publication-id shape, the integrity-manifest entry (bytes + sha256)
against the on-disk file, then `check_index_contract` against `meta` plus
the embedded publication/compartment identity, and opens
`file:…?mode=ro` into a bounded LRU (bytes under a namespace can never
change). Missing, corrupt, mismatched or cold ⇒ **503 + Retry-After**
with a named readiness code (`index_not_staged`,
`index_verification_failed`, `index_contract`) — never a silent fall back
to current PostgreSQL; the release-scoped routes cannot reach the
`/v1/search` store at all.

### 5. The no-JS surface

The same engine backs the no-JS representation of
`GET /v1/releases/<pub>/compartments/<comp>/search` (`format=html` or an
`Accept: text/html` GET) — `release_pages.search_page`: a
`<form method="get">`, results linking **release-scoped** record URLs,
cursor Prev/Next links, honest unsupported/empty/error states — zero
scripts, inside the zero-JS budget (ADR-068). The `/search` Astro page
carries one static GET form per compartment (with `format=html` so the
representation needs no Accept header) and keeps its island as
progressive enhancement; every record href it emits is release-scoped —
search links never point at the generic current alias.

## Alternatives considered

- **Extend `PgReadStore` search.** Rejected — it would serve the *current*
  projection rather than the pinned release, the exact failure
  SIG-FIND-003 names; the release scope would drift silently.
- **One cross-compartment index.** Rejected — a single query could then
  leak across licence compartments; per-compartment files also bound the
  blast radius of a corrupt index to one compartment.
- **Tantivy / external engine or search cluster.** Out of scope per the
  ticket; adds a runtime service, an opaque binary format and network
  operations for a corpus far below the need.
- **Offset pagination.** Rejected — offsets drift under a re-staged
  index and cannot express "page N of this release's this query"; the
  bound keyset cursor can.
- **Bake withdrawal verdicts into the index.** Rejected (ADR-124) — baked
  verdicts resurrect withdrawn records under rollback; the build-time
  `withdrawn` column is a pre-filter only and serve-time is the
  authority.

## Consequences

- Indexing adds modest build cost and ~20% to tree bytes, measured on the
  national corpus (build+manifest over `exports/out/national`):
  **232,625 unique released records** (236,994 site rows − 4,369 portal
  duplicates), 474,960 files / 2,483,673,491 B in **102.65 s** at ~1.08
  GiB peak RSS; the twelve `search_index.sqlite` files total **488.6 MB**
  (largest: `osm_physical` 301.4 MB for 154,705 records).
- Measured serving on the same build (8 concurrent readers, per-request
  verified ro connections): warm p95 — browse 15.5 ms, FTS 10.5 ms,
  exact-id 3.7 ms, facet 13.9 ms, mixed 21.5 ms — all far inside the
  500 ms target; cold staging verify is 0.5–283 ms per index (sha256 of
  the whole file, done once per namespace); a complete cursor walk of
  `osm_physical` enumerated all 154,705 records over 3,095 pages in ~30 s
  with zero duplicates/omissions.
- `search_index_version` is part of `publication_id`: a format bump
  forces a new namespace rather than a confusing in-place change.
- Serving needs the staged tree to actually contain the index files; a
  release built by an older exporter reports honest cold `503`, not a
  crash or a PG fallback.
- Facets are `AND` and single-valued per facet name in this version; a
  multi-select facet is a later ADR if a requirement asks for it.

## Revisit trigger

Revisit when (a) a compartment exceeds ~5M records and FTS5 warm-p95
breaches the 500 ms bound at 8 readers, (b) a cross-compartment search
requirement is authorized — it needs a new ADR and a licence-join design,
(c) the index format or cursor contract must change — bump
`SEARCH_INDEX_VERSION`/`CURSOR_VERSION`, which mints a new publication
namespace per ADR-132, or (d) serving moves off a local filesystem to
object storage, requiring a different verification/mount story.
