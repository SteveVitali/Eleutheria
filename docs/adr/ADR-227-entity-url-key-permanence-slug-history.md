# ADR-227 — entity URL-key permanence: frozen hash, verbatim append-only slug history, and the `/id/` redirect semantics (P36.29)

- Date: 2026-10-29
- Status: accepted
- Ticket: P36.29 (R11-K13-GX-03, manifest row 369 — on
  `r11/P36.29-entity-url-keys-and-slug-history`)
- Base: `r11/P36.28-static-figure-kit-graphs-charts-legends-v2`
- Requirement stamps: SIG-UI-067 (one identifier module), SIG-UI-109
  (one entity label), SIG-UI-111 (unique labels per kind), SIG-UI-112
  (person-name screen), SIG-UI-113 (entity URL scheme and permanence),
  SIG-EVUI-010 (artifact handles) — owned; SIG-UI-039 / SIG-UI-040 /
  SIG-ENG-042 (cited); K2 §3.3/§6.5 (the URL scheme and the history
  record shape), K13 §7 W1 (GX-03), JUR-05 (the single redirect
  generator this history feeds, P36.35), ADR-155 (page-type posture —
  `/entity/**` is already classified T1), ADR-215 (the P35.29 label
  registry this row reads)
- Supersedes: nothing.

## Context

K2 §3.3 fixes the scheme — `/entity/<type>/<name-slug>--<hash7>/`,
hash authoritative, slug cosmetic — and §6.5 the record shape
`{hash, uuid, url_type, slug, from_pub, to_pub, status, target}` over
the closed vocabulary `current | renamed | merged | split | withdrawn`.
P35.29 (ADR-215) landed the shared label/slug/hash primitives and
explicitly left the history artifact and `/id/` semantics to this row.
The questions the row owned:

1. **What does "append-only" mean for a retired key's `current` row?**
   Two readings exist: mutate the issued row to stamp `to_pub`, or
   carry every issued row verbatim and let an appended terminal row
   retire the key. Mutating emitted bytes breaks the one property a
   consumer can verify cheaply — every row of release N reappears
   byte-identical in release N+1.
2. **What status does `/id/<type>/<uuid>` answer with?** K2 says it
   "redirects to the current URL" without naming a code. A 301 would
   be wrong: the target is *currently* canonical, not permanently —
   the very next release can rename the entity and a cached permanent
   redirect would strand the permanent identifier.
3. **When is a hash "already issued"?** K2 freezes a hash once issued
   and extends on collision. Naively, an entity whose own 7-char hash
   appears in the prior history "collides" — and would be extended to
   8 characters every release, rewriting the frozen key.
4. **What does a recorded terminal entity with no visible prior key
   emit?** A merge or withdrawal recorded before any bound release
   issued the entity a key still needs a truthful `/id/` answer —
   but the record has no slug to report.
5. **Where does SIG-UI-111's bound land?** `resolve_disambiguators`
   already guarantees the full-display-label uniqueness inside
   `(kind, release)`; the question is whether a violation is a ship
   blocker or a shrug.
6. **Which artifact does the history emit as?** The jurisdiction tree
   already ships `web/jurisdiction_slug_history.json`; the entity
   history needed a parallel, manifest-listed home.

## Decision

1. **Rows are carried verbatim; retirement is a row, not a rewrite.**
   A prior `current` row keeps `status: current` forever — the
   appended `renamed`/`merged`/`split`/`withdrawn` row naming the
   same key is what retires it. Liveness is therefore computed, never
   read from `status` alone: a `current` row is *live* iff no terminal
   row names the same `(uuid, hash, url_type, slug)`. `history_doc`
   refuses a registry with two *live* keys for one uuid or two
   terminal rows for one key.
2. **`/id/<type>/<uuid>` answers 302 to the current key while the
   entity is live** — the target is movable, so the redirect is
   temporary. A `renamed` entity with no live row resolves `/id/`
   through the renamed row's successor (still 302); `merged` answers
   301 to the survivor, `split` 300 with the successor list,
   `withdrawn` 410, an unknown uuid the honest 404. `/entity/` requests
   resolve hash-authoritative: an exact current key serves (200), any
   other slug with the same hash 301s to the canonical key, a retired
   key answers its terminal status.
3. **"Already issued" means issued to a different uuid.** A label
   reusing its own entity's issued hash is the permanence contract,
   not a collision — `freeze_hashes` only extends a key whose hash
   was issued to a different entity or claimed by a sibling in the
   same registry, in deterministic sorted-entity-id order (first-come
   keeps the 7-char form; extension appends one base32 character at a
   time and never rewrites an issued value).
4. **A recorded terminal entity with no visible prior key emits its
   terminal row with `slug: null`** — the hash is still derivable
   (`entity_hash(uuid)`), the type comes from the record, and the
   absent slug is honest absence, never a fabricated key. `person`
   entities emit nothing under any path (SIG-UI-112): no label, no
   key, no history row, and `history_doc` refuses a `person`
   `url_type` row outright.
5. **SIG-UI-111 is a ship blocker.** `check_unique_labels` runs on
   the final resolved registry inside `build_spine_export`; a
   duplicate full display label within a kind refuses the export
   rather than shipping it.
6. **The history emits as `web/entity_slug_history.json`**
   (`sig.slug-history/1`), parallel to the jurisdiction artifact:
   one document, `schema`/`publication`/`generated_at`/`rows`, SIG
   licence + `sig_graph` compartment, rows sorted
   `(uuid, hash, from_pub, status)` for byte-stable output.
   `build_spine_export`/`run_spine_export` take
   `previous_entity_history` — the previous release's emitted rows
   when bound; absent is the honest first-release posture (current
   rows + recorded terminal tombstones).
7. **One resolution vocabulary, two mirrors.** The Python
   `resolve_request` (`policy/slug_history.py`) is the reference the
   JUR-05 generator consumes; the TypeScript `resolveEntityRequest`
   (`web/src/lib/entity-history.ts`) implements the identical
   semantics for the static stubs — same regexes, same liveness rule,
   same status map — so a generated redirect rule and a fixture page
   can never diverge.
8. **Publication withdrawal scrubs; lifecycle withdrawal
   tombstones.** The K2 `withdrawn` status is the honest 410 for an
   entity that left the public surface with no recorded transition.
   A P34.19 **publication** withdrawal (F-337) is stronger — the
   entity's id may not appear in any public artifact — so
   `merge_history` drops every row naming a publication-withdrawn
   uuid rather than tombstoning it, and filters withdrawn entities
   out of merge/split targets (a 410 names less than a successor id).
   Verbatim carry (point 1) applies to every legitimately-issued row;
   a withdrawn entity's rows were never legitimately public.

## Consequences

- A consumer can verify append-only history by diffing row lists —
   every prior row reappears verbatim. The redirect generator (JUR-05,
   P36.35) reads terminal rows for a key, never guesses.
- `to_pub` on a retired `current` row stays `null`; the retirement
   publication lives on the appended terminal row. Tooling that reads
   "was this key live at release R" must apply the liveness rule, not
   `status` alone — documented in `slug_history.py`.
- Splits have no spine mint yet: `merge_history` takes `split_into`
   but no production path binds it — the first recorded split lands
   with the reconcile work that records one.
- `previous_entity_history` is unbound in production today: no prior
   release carried the artifact, so the first bound release emits
   current rows + recorded tombstones and becomes the chain's base.
- The fixture document uses invented entity ids (`agency:okcpd`
   shape) with honestly-derived hashes; the `/id/` regex accepts any
   non-slash uuid segment so canonical-id forms are not restricted by
   the parser.

## Revisit trigger

- JUR-05 (P36.35) lands the redirect generator — confirm it consumes
  `web/entity_slug_history.json` verbatim and mirrors
  `resolve_request`'s semantics rather than re-deriving them.
- The first spine-recorded entity split lands — verify `split_into`
  binding and the 300 choice page.
- A real 7-char hash collision in the registry — verify the
  extension rule on production data and that no issued hash moved.
- The release pipeline binds `previous_entity_history` across
  consecutive releases — verify verbatim carry on real bytes.
