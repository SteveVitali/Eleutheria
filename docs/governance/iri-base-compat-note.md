# Identifier base compatibility note — the IRI base move (2026-10-20)

*P35.38b / ADR-217 · operator decision Q-E2-03 [B-6] *"Move UA, don't buy
domain"* · findings F-184, ED-38/39/40 · companion to the crawler-contact fix
(P35.38a) and the `/data-collection/` page.*

## What changed

Every identifier SIG mints in **new** releases now carries the owned domain
`surveillancegraph.org` (and `ontology.surveillancegraph.org` for the ontology
and vocabulary families):

- the LinkML schema ids and the `sig:` prefix (OWL, SHACL, JSON Schema,
  Pydantic and docs the generator emits),
- the §13 SKOS vocabulary IRIs (technology, capability, predicate and the
  structural enum schemes),
- the PROV-O lineage namespace (`…/prov/`) written into `provenance.ttl`,
- the JSON-LD `@vocab`/`sig` context (`…/ns/`) behind every `.jsonld` artifact,
- the `/id/{type}/{uuid}` subject IRIs the API dereference surface emits, and
- the watch-feed `.ics`/`.xml` subscription UIDs and the OCFL inventory
  `user.address` default.

## What did not change

- **Nothing already published was rewritten.** Released bundles, OCFL
  inventories, the hosted claim spine and deployed migrations are immutable
  (ADR-132): identifiers minted before this change keep the names they shipped
  with, and they keep meaning what they meant.
- **The old identifiers are still valid names.** The machine-readable
  [`iri-base-alias-map.json`](iri-base-alias-map.json) maps every retired base
  to the base new releases mint that family under. It is append-only — the
  map only gains lines.
- **The map is a name mapping, not a redirect.** SIG does not claim the old
  IRIs dereference over HTTP to SIG infrastructure. A resolver that meets an
  old-base identifier should resolve it through the map — treat the old IRI
  as a key, not a live URL.

## The honest residual

`sig-project.org` and `sig.example` were never registered to this project, and
the operator declined defensive registration (B-6): the domains remain
unregistered and a third party could still claim them. That risk is recorded —
in ADR-217 and `docs/risk_register.md` (RISK-R11-29) — not hidden. Nothing
inbound depends on the old domains: new minting is on the owned base, the old
names resolve through this map, and the emitted surfaces never dereference the
old hosts. The crawler's contact URL was already moved to
`https://surveillancegraph.org/data-collection/` (P35.38a); the `/data-collection/`
page is the public explanation of what SIG's collection traffic is.

## In one line

**New identifiers mint under `surveillancegraph.org`; every identifier SIG
ever published still names the thing it always named — look it up in the
alias map.**
