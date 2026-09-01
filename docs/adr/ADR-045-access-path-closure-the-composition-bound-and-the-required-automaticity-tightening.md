# ADR-045: Access-path closure — the composition/scope/temporal bound, the speculative label, and the required-`automaticity` tightening

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P12.2
- **Requirement ids:** SIG-ONTO-042, SIG-ONTO-043, SIG-ONTO-044, SIG-ONTO-049; SIG-RECON-047, SIG-RECON-048, SIG-RECON-049, SIG-RECON-050 (SIG-RECON-037 non-implication is owned/tested in P08.2, referenced here). Realizes the §12.5 `AccessRelationship` attributes (`scope`, `direction`, `automaticity`, `access_kind`, `asserted_by`).
- **Spec:** docs/2_canonical_design_spec.md §12.2 (the three sharing edge types), §12.5 (`AccessRelationship`), §30.2 (access-path closure and its limits). Builds on ADR-031/ADR-036 (the reconcile value-object modules) and the P08.2 sharing-edge reconciler.

## Context

§30.2 calls access-path closure "SIG's most powerful and most dangerous inference": the answer to
"can organization A reach organization B's data, through any chain?" It MUST be implemented and it
MUST be bounded (SIG-RECON-048/049), because an unbounded or unlabelled closure manufactures
findings — a false "A can search C" built from "A searched B and B searched C", or an unexplained
seven-hop theoretical path rendered as if it were a shared-data relationship (SIG-RECON-050).

The edge model already existed: `AccessKind` (the three §12.2 kinds) and `AccessRelationship` landed
in the ontology in an earlier phase, and the P08.2 reconciler (`reconcile.sharing`) already keeps the
three kinds strictly separate and owns the non-implication rule (SIG-RECON-037). What P12.2 adds is
the **closure bound itself** — the L4 inference that composes edges under the §30.2 limits — plus two
edge-model corrections.

## Decision

**1. Closure ships as a pure value-object module, `inference.access_paths`.** It follows the
established pattern (ADR-031/ADR-036): frozen dataclasses with validation, no persistence, aligned
with the L4 `reconcile.model.Inference` shape (`derivation_rule` / `rule_version` / `input_claim_ids`
/ `derived_at`, SIG-RECON-047). It lives in `inference/` (the §47 home for L4 derivations), which
already depends on `sig-reconcile`, so it **reuses** `reconcile.sharing.ACCESS_KINDS` rather than
re-declaring the three kinds. It does not fork the P08.2 reconciler that lands the edges.

**2. Only `configured_access` and `federates_search_to` compose** (`COMPOSABLE_LABELS`,
SIG-RECON-049 #1/#2). `observed_use` (use is not access) and `declared_policy` (a statement is not a
channel) never compose; `distributes_list_to` never composes in the query direction (a hotlist flows
outward, creating no inbound search path). A hop keeps the `edge_label`/`access_kind` it was given —
closure never merges, collapses, or defaults one §12.2 kind into another (SIG-ONTO-042).

**3. Edges are normalized into accessor→provider reachability terms** (`from_org` accesses
`to_org`'s data) before closure. Mapping the raw §12.5 `AccessRelationship` / §12.3 integration edges
into that form — respecting each edge type's native direction — is the caller's responsibility. This
keeps the closure engine direction-agnostic and its rules legible, rather than special-casing every
edge type's polarity inside the traversal.

**4. The three bounds are computed, never caller-overridable, on the path:**
- **Scope may not broaden along a chain** (SIG-RECON-049 #3). Scopes are ranked by breadth
  (`SCOPE_ORDER`, `subject < own < partner < state < region < national < commercial`); a hop is
  refused when its scope is strictly broader than the previous hop's. A path's scope is the narrowest
  hop's. This is the conservative reading of the spec's single worked example ("a partner-scoped edge
  does not chain into a national-scoped one"): a chain reaches only as broadly as its tightest hop.
- **Every hop must be valid at the as-of time** (SIG-RECON-049 #4). A *future* hop (known
  `valid_from` after as-of) cannot extend a chain and is not traversed; an *expired* hop (known
  `valid_to` before as-of) is allowed but taints the whole path `historical`. A single-snapshot
  sharing edge (`valid_from_kind='unknown'`, `valid_to_kind='ongoing'`, SIG-ONTO-044) is always
  valid — its start is never inferred from first observation.
- **Confidence is the path minimum, never the average** (SIG-RECON-049 #6), over the ordered scale
  `possible < probable < certain` (the `probable` default is §29.2's).

**5. Two published bounds, both parameters with documented defaults.** `MAX_PATH_HOPS = 8` is the
hard enumeration cap (SIG-RECON-049 #5): closure never builds a longer path. `SPECULATIVE_HOP_THRESHOLD
= 3` is the published hop count beyond which a path is labelled **speculative** and excluded from
headline figures (SIG-RECON-050): `is_headline` is true only for a live, non-speculative, multi-hop
path, and `AccessPathClosure.reachable(headline_only=True)` excludes the speculative/historical set.
Nothing is silently dropped — a long or historical path is still returned, with its full hop list, so
a surface can show it *labelled* rather than blurred.

**6. Every hop carries evidence, enforced at construction.** An `AccessEdge` with no evidence/claim
id is rejected: an unexplained hop is exactly the unexplained edge the defining standard forbids
(§3.1). `AccessPath.public_view()` always emits the full hop list with per-hop evidence (SIG-UI-025),
and `to_inference().input_claim_ids` is the ordered union of the hops' evidence.

**7. `automaticity` is now REQUIRED on `AccessRelationship` (SIG-ONTO-049).** The ontology previously
left it optional even though SIG-ONTO-049 makes direction, scope, automaticity, **and** kind all
required. P12.2 owns SIG-ONTO-049, so the LinkML schema (`edges.yaml`) now marks it `required: true`;
generated artifacts are regenerated and the generalization suite gains a test asserting the omission
is a `ValidationError`. `asserted_by` remains inherited-optional from `Edge` — §12.5 lists it as an
attribute (asymmetry detection) but SIG-ONTO-049 requires only the four.

## Consequences

- Closure is provably bounded and every path is self-explaining; the difference between "these two
  agencies share data" and "a seven-hop theoretical path exists" survives into every surface that
  consumes `AccessPath`/its L4 inference.
- The `automaticity` tightening is a schema-contract change (optional → required). It is additive to
  the spec's intent, not a break of it: SIG-ONTO-049 always required it. The one prior test that
  constructed an `AccessRelationship` without `automaticity` was updated.
- Persisting the L4 closure inferences and rendering the map/UI (§30.4, §39.1) remain downstream
  (P15.x); this ticket delivers the bound and its labelled output, aligned with the persisted
  `inference.derived_fact` shape.
- The scope-breadth ranking and the two published constants are engineering choices within the
  spec's limits; they are parameters, so a confirmed policy value is a one-line change.

## Alternatives considered

- **Compose every edge type and rely on labels to warn.** Rejected: SIG-RECON-049 #1 is explicit that
  only two labels compose. Composing `observed_use` would manufacture the exact false "A can search C"
  the rule exists to forbid, and no label undoes a fabricated edge.
- **Fold reachability direction into each edge type inside the traversal.** Rejected in favour of a
  normalized accessor→provider `AccessEdge`: encoding every §12.3/§12.5 edge type's native polarity in
  the closure loop would make the safety rules unreadable and easy to get subtly wrong.
- **Average the hop confidences.** Rejected by SIG-RECON-049 #6 — a chain is as strong as its weakest
  hop; averaging launders a `possible` hop into a `probable` path.
- **Drop paths longer than the threshold.** Rejected: SIG-RECON-050 requires the long path be *shown*
  and *labelled* speculative, not hidden — hiding it is its own kind of editorial collapse.
- **Leave `automaticity` optional.** Rejected: SIG-ONTO-049 makes it required; P12.2 owns that
  requirement, so the schema is corrected rather than the requirement quietly under-met.

## Revisit trigger

Revisit if: the published hop threshold or the hard cap needs to change once real network data shows
their effect on precision (both are parameters today); a confirmed scope-composition policy replaces
the conservative "never broaden" ranking; a new composable edge type is added to §12.3/§12.2 (update
`COMPOSABLE_LABELS`); or the L4 closure inferences gain a persistence/render owner (P15.x), at which
point the value-object → `inference.derived_fact` wiring and the §30.4/§39.1 map labelling land.
