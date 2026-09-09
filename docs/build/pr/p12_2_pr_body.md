## Summary

Implements **P12.2 — access edges and access-path closure** (`docs/tickets/P12.2__network-inference.md`), the §30.2 inference the spec calls "SIG's most powerful and most dangerous." It answers "can organization A reach organization B's data, through any chain?" and is bounded so it manufactures neither a false "A can search C" nor an unlabelled theoretical path.

Closure ships as the pure value-object module `inference.access_paths` (following the ADR-031/036 reconcile pattern), consuming — never forking — the P08.2 sharing-edge reconciler that lands the edges.

## What changed

- **`inference/src/inference/access_paths.py`** (new) — `AccessEdge`, `AccessPath`, `AccessPathClosure`, and `close_access_paths()`.
- **`ontology/src/ontology/schema/edges.yaml`** — `AccessRelationship.automaticity` is now `required: true` (SIG-ONTO-049); regenerated `ontology/generated/*`.
- **`tests/inference/test_access_paths.py`** (new, 27 tests) + a new generalization test for required `automaticity`.
- **`docs/adr/ADR-045…md`**, **`docs/traceability.md`**, **`docs/risk_register.md`** (Phase 12, RISK-P12-08..14).

## Design decisions (ADR-045)

- **Only `configured_access` and `federates_search_to` compose.** `observed_use`, `declared_policy`, and query-direction `distributes_list_to` never do; a hop keeps its `edge_label` verbatim — the three §12.2 kinds are never merged (SIG-ONTO-042).
- **Edges are normalized into accessor→provider terms** before closure; the engine stays direction-agnostic.
- **Bounds computed on the path, not caller-overridable:** scope may not broaden along a chain (path scope = narrowest hop); every hop must be valid at the as-of time (future hop not traversed; an expired hop taints the path `historical`); confidence is the path **minimum**; enumeration is capped at `MAX_PATH_HOPS`; beyond `SPECULATIVE_HOP_THRESHOLD` a path is `speculative` and excluded from headline figures.
- **Every hop carries evidence** (enforced at construction) and the full hop list survives into `public_view()` and the L4 `Inference` (SIG-RECON-047).
- **`automaticity` tightened to required** — SIG-ONTO-049 always required it; the one prior test omitting it was updated.

## Verification

- `make check` — lint + format + mypy (152 files) + **1882 tests pass** + `verify-gen` clean post-commit.
- Live end-to-end: an `observed_use` chain yields **no** reachability (no false "A can reach C"); a 4-hop configured chain is `speculative` and excluded from `reachable(headline_only=True)`; the L4 inference carries the path-minimum confidence and `derivation_rule=access_path_closure/§30.2`.

## Acceptance criteria → evidence

| AC (spec) | Status | Evidence |
|---|---|---|
| The three access edge types are never merged/collapsed/defaulted | met | `COMPOSABLE_LABELS`/`NON_COMPOSING_ACCESS_KINDS`; hop `edge_label` preserved · `test_only_configured_access_and_federation_compose`, `test_closure_never_relabels_a_hop_kind`, `test_access_edge_kinds_stay_distinct_and_are_not_defaulted` |
| Closure respects hop limits, scope, non-composition; `observed_use`/query-dir `distributes_list_to` no compose; scope mismatch no chain; expired hop → historical; confidence = min | met | `test_observed_use_does_not_compose`, `test_distributes_list_to_does_not_compose_in_the_query_direction`, `test_scope_may_not_broaden_along_a_chain`, `test_expired_hop_yields_a_historical_labelled_path`, `test_confidence_is_the_minimum_over_the_path_never_the_average`, `test_path_length_is_capped` |
| Paths beyond the published hop threshold are speculative + excluded from headlines; every published path shows its full hop list with per-hop evidence | met | `test_paths_beyond_threshold_are_speculative_and_excluded_from_headlines`, `test_every_published_path_carries_its_full_hop_list_with_per_hop_evidence`, `test_a_hop_without_evidence_is_rejected` |
| Phase-gate (§51.3): CI green, tests for new reqs, ADR for deviation, traceability + risk register updated | met | `make check` green; ADR-045; `docs/traceability.md` P12.2; `docs/risk_register.md` RISK-P12-08..14 |

### Requirement IDs stamped

SIG-ONTO-042/043/044/049, SIG-RECON-047/048/049/050. §12.5 `AccessRelationship` attributes realized: `scope`, `direction`, `automaticity`, `access_kind` (all required), `asserted_by` (inherited, asymmetry). SIG-RECON-037 non-implication is owned/tested in P08.2 and referenced here.

## Deferrals / notes

- Persisting the L4 closure inferences into `inference.derived_fact` and the map/UI render (§30.4, §39.1, SIG-UI-025) are downstream (P15.x); `to_inference()`/`public_view()` are aligned with those shapes (RISK-P12-13).
- Mapping raw §12.5/§12.3 edges into the normalized `AccessEdge` (per each edge type's native direction) is the caller's responsibility (RISK-P12-14).
- **Heads-up:** the working tree had pre-existing uncommitted changes under `db/` (`analytics.py`, `suppression.py` + tests, P12.1 area) that are **not** part of this ticket; they were left untouched and unstaged.

Implements `docs/tickets/P12.2__network-inference.md`.

Generated with [Devin](https://devin.ai)
