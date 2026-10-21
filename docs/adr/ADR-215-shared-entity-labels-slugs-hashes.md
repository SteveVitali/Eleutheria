# ADR-215 — The shared entity label registry (P35.29)

- Date: 2026-10-18
- Status: accepted
- Ticket: P35.29 (Round 11 / P35 sub-round 11B, manifest row
  `R11-K13-GX-01`, row 307 — K2 §3, K13 §7.1; cites **A-10** (the operator's
  recorded answer, gate answer `b + c`), ADR-159, SIG-PUB-008,
  K2 §3 L-1…L-7, SIG-UI-D20–D25, SIG-IDENT-031/032, UXR-17)
- Base: `r11/P35.27-resolver-input-truth`
- Related: ADR-124 (the shared publication-eligibility selector the label
  path renders, never re-decides), ADR-159 (the registry auto-allow ADR
  A-10 rides), ADR-112 (partner-organisation entity mints the label
  candidates join), ADR-132/133 (the release/record surfaces the labels
  feed), ADR-110 (subject keys as label hints — never label text).

## Context

Before this row the public surface derived names in four different places,
each with its own silent policy:

- `api.store_pg._label_for` / the search-page labels: the org's
  `cached_canonical_name`, else **the entity's first identifier value** — a
  connector key on the public surface (K2 §3 L-2, SIG-UI-D20).
- `spine_export`'s `entity_labels` read: identifier *values* as dossier/
  coverage attribution and network-node names — the same leak, plus a
  `site.label or site.entity_id` map fallback that emitted a raw UUID.
- `release_pages`: `Unnamed {entity_type}` — the "Unnamed deployment"
  string K2 §2 names as a defect.
- `shaping`: `camera_name` or nothing — no typed fallback, no screening.

K2 §3 requires ONE derivation (L-1) carrying `label`, `descriptor`,
`label_basis`, `label_source_id`, `slug`, `hash`, `url` per entity, with
the person-name screen over every input (L-6) and the A-10 organisation
rule (matched/allowed orgs label; every other org shows a typed
"not yet reviewed" state; non-organisation labels ship).

## Decision

### One leaf-package module

`policy/src/policy/labels.py` is the one derivation: `LabelFacts` in,
`EntityLabel` (`sig.entity-label/1` row) out. `policy` is a leaf package —
the person-name screen is therefore **injected** as a `person_screen`
callable: production call sites pass
`resolution.partner_identity.natural_person_signal` (the affirmative
person-signal the identity layer already owns); the built-in default is a
conservative fail-closed heuristic for call sites that cannot inject. A
screen that raises refuses the candidate (fail closed).

### Raw-identifier fallbacks die; the fallback is typed

Every derivation that runs out of words ends in
`"<kind words> #{hash4}"` (`Record #abc1`, `Surveillance camera #x9zz`) —
the D-K2-5 posture — never a UUID, connector key, source id, or handle.
`Unnamed <type>` is retired in `release_pages` for the same typed form.
Identifier schemes in `BLOCKED_KEY_SCHEMES` (`sourceid`, `serialno`,
`platformid`, `wikipediaid`, `handle`) are never `key_name` sources.

### Typed absence is a row, not a gap

- `person` entities and entities the shared selector denies emit **no**
  artifact row — no label, no node, no slug, no URL (A-10 c).
- Review-pending organisations emit a row with `label_state:
  "not_yet_reviewed"` and null label/slug/hash (A-10 b — the state is
  visible, the label is not). The org eligibility rule is rendered from
  the same inputs `entity_eligible_sql` consults (disposition, org status,
  `publication_review_required`) — the label layer renders the selector's
  outcome; it never re-decides eligibility.

### Slug + hash

- `hash` = Crockford base32 of `sha256(canonical UUID text)`, 7 chars /
  35 bits; the slug-registry collision extension (one more digit) is a
  caller decision — issued hashes are frozen.
- `slug` = ASCII-folded `[a-z0-9]+` tokens of the display label plus the
  K4 state display slug (`-usa-tx`) when the entity carries a canonical
  place key; capped at 56 chars on a token boundary. The alpha-2 → alpha-3
  map covers the ISO table inline; an unknown code honestly omits the
  suffix (recorded in the run ledger — JUR registry display slugs replace
  the map when JUR lands).
- URL: `/entity/<type>/<name-slug>--<hash>/`; the hash is authoritative,
  the slug cosmetic.

### The artifact and the call sites

`labels/<compartment>.jsonl` files each entity's rows under every
compartment its label-input claims license to — the same compartment law
as `record_claims` (an ODbL-sourced name lands in the ODbL file, never
co-mingled); an entity with no publishable label inputs defaults to the
SIG compartment. Withheld/person rows are never written.

Consumers rewired to the registry/module: site rows (`label` +
`label_basis`), the map asset label, network node labels, dossier
jurisdiction attribution, published-record label basis, release-page
fallbacks, and the API label path (`_label_for` + the search-page label
set — one set-based join carrying the page's facts, preserving the
4-statement page bound).

## Consequences

- The same `LabelFacts` produce the same label in exporter, API and
  pages — parity is a property of the module, not a convention.
- New entity kinds register by extending `_candidates`/`KIND_WORDS` in the
  module and `_LABEL_FACT_PREDICATES` in the export read — one place each.
- `subject_key` rides the emitted row as the provenance anchor; `sig_id`
  stays null until the SIG identifier scheme lands (recorded, not
  improvised).

## Revisit trigger

Revisit when the JUR registry's canonical place display names/slugs land
(retire the inline alpha-3 map), when the SIG public identifier scheme is
minted (populate `sig_id`), or when a new public entity family needs a
`§3.2` derivation row beyond the current kind set.
