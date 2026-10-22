# ADR-217 — IRI base on the owned domain, the append-only alias map, and the compat note (P35.38b)

- **Status:** Accepted
- **Ticket:** P35.38b (Round 11 / P35 sub-round 11B, manifest row 317,
  `R11-SAFE-06` — F5 PKG-09b (ED-38/39/40) + design E2-08; cites **Q-E2-03
  [B-6]** — the operator's recorded answer *"Move UA, don't buy domain"* —
  ADR-168, ADR-132, ADR-178, SIG-INGEST-016, SIG-EXPORT-002, F-184 (the
  b-half))
- **Base:** `r11/P35.37-figure-to-evidence-pointers`
- **Date:** 2026-10-20 (`date -u`)
- **Related:** ADR-168 (the collection-conduct / E2 chain this row's gate
  answer rides — it already names plan rows P35.38a/b), ADR-132 (immutable
  releases — the reason the fix is an alias map, never a rewrite), ADR-178
  (the append-only alias mechanism precedent: old names stay valid, the map
  only gains lines), ADR-213 (declared namespaces and independence classes),
  P35.38a (the a-half: crawler UA contact URL + the `/data-collection/`
  page), RISK-R11-29 (the recorded squatting residual).

## Context

SIG's identity base was minted on domains the project does not own.
`ontology.sig-project.org` carried every schema id, `sig:`-prefix URI and
§13 SKOS vocabulary/predicate IRI; `sig-project.org/prov/` and
`sig-project.org/ns/` carried the PROV-O lineage namespace and the JSON-LD
`@vocab` context; `sig.example` carried the API `/id/` subject IRIs and the
watch-feed subscription UIDs. `sig-project.org` also named the crawler
User-Agent contact URL (F-184) and the OCFL inventory `user.address`
default. Both `sig-project.org` and `sig.example` are **unregistered** —
NXDOMAIN: anyone can still register them (RISK-R11-29).

At GATE-P the operator answered **Q-E2-03 [B-6]** *"Move UA, don't buy
domain"*: every `sig-project.org` reference is removed from code and docs,
the residual squatting risk is recorded rather than bought away, and the
IRI base for **new** releases is `surveillancegraph.org` — while
already-published releases stay immutable and keep their IRIs, resolvable
through an append-only alias map and a compat note. The crawler-contact
half landed as P35.38a; this row is the identity half.

A second defect in the same surface: `provenance.ttl` stamped every
capture's `retrieved_at` with the export build's `generated_at` — a
fabricated retrieval time (F5 PKG-09b's acceptance clause is *retrieval
times equal retrieval times, with upstream URLs and digests*).

## Decision

1. **One declared identity base per surface, owned.** New minting uses
   `https://surveillancegraph.org` (API `/id/` namespace, PROV-O namespace,
   JSON-LD context, OCFL user address, watch-feed UID domain) and
   `https://ontology.surveillancegraph.org/` (schema ids, the `sig:`
   prefix, all vocabulary scheme IRIs). Each surface carries exactly one
   declared constant (`generate.BASE`, `provo.SIG`, `formats.SIG_NS`,
   `dereference.SIG`, `ocfl.DEFAULT_USER_ADDRESS`, `WATCH_UID_DOMAIN`,
   `build_predicates.BASE`) — a repo check fails a new `sig-project.org`
   literal or a second hard-coded base.
2. **Already-published IRIs are never rewritten.** The append-only
   machine-readable `docs/governance/iri-base-alias-map.json`
   (`sig.iri-alias-map/1`) records old-base → new-base for every identifier
   family the tree ever emitted; `docs/governance/iri-base-compat-note.md`
   is the published human note. The map is a **name mapping**, never an
   HTTP-redirect claim — SIG does not assert the old IRIs dereference.
3. **Provenance tells the truth.** `provenance.ttl` emits the real bound
   captures (from `claim_binding_detail`): the recorded `retrieved_at`,
   the real `ingest_run` (connector, version, start/finish), the content
   digest, and the S-6-gated upstream reference — the same
   `upstream_block` vocabulary the statements path emits. The export run
   `prov:used` every bound capture.
4. **The residual is recorded, not bought away.** The old domains stay
   unregistered by operator decision; this ADR, the compat note and
   RISK-R11-29 carry the risk; nothing inbound depends on them. Deployed
   `vocab_*` sqitch migrations and the hosted vocabulary rows they seeded
   keep the old IRIs (they are the published artifacts of their day) — the
   hosted re-mint is filed `D-P35.38b-1`.

## Consequences

- Every `sig-project.org` literal is gone from shipped code/config/schema
  source; a git-grep guard plus a per-emitter single-constant check keep
  it that way. `sig.example` is likewise gone from shipped code
  (PKG-09b's AC covers both) — except the two `D-P35.38b-2`-exempt
  organised-editing files, whose repoint needs a provisioned contact
  address, real target routes, and the external OSM-wiki edit.
- The watch-feed UIDs stamp `@surveillancegraph.org` — `D-P35.3-1` closes;
  its `watch-feed-uid` sentinel compartment is deleted.
- `ontology/generated` regenerates wholesale under the new base;
  `make verify-gen` pins source↔artifact.
- New releases mint IRIs nothing external can claim; old published
  releases keep their names through the map.
- `provenance.ttl` grows: real captures and ingest runs replace the
  per-source synthetic entities — the artifact is bounded by real
  evidence, not by a fabricated-per-source constant.
- The `/id/` namespace change means API-issued subject IRIs differ
  pre/post cut — the map records the family; `/v1/*` route honesty itself
  stays P34.25's.

## Alternatives considered

- **Register `sig-project.org` defensively** — rejected by the operator
  (B-6): the project does not buy domains it does not need; the recorded
  residual is accepted knowingly.
- **Rewrite published releases / deployed migrations to the new base** —
  rejected: violates release immutability (ADR-132) and the append-only
  spine/posture; the alias map exists precisely so nothing is rewritten.
- **Keep per-source synthetic capture entities in provenance.ttl** —
  rejected: they stamped the export clock as `retrieved_at` — a fabricated
  fact under §3.1.
- **A single cross-package identity constant** — rejected: the workspace
  packages are independent surfaces; one declared constant *per surface*
  is the contract (a second hard-coded base in any surface fails).

## Revisit trigger

Revisit if any of these land: (a) a third party registers
`sig-project.org` or `sig.example` and uses them in a way that demands a
response beyond the recorded posture (e.g. impersonation of SIG's
published IRIs); (b) the operator revises B-6 (domain purchase becomes a
live question); (c) `D-P35.38b-1`'s hosted vocabulary re-mint is picked
up, at which point the deployed-migration exception to the grep guard is
re-scoped; (d) `D-P35.38b-2` closes — the organised-editing exemption is
deleted in the same change that repoints the contact+URLs; (e) a new
identifier family is minted — the alias map and the guard's family
coverage must gain a row/test in the same change; (f) an external
consumer is found resolving old-base IRIs in the wild in a way
the compat note does not cover.
