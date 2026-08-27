---
search:
  boost: 2.0
---


# Enum: EdgeType 




_The closed catalog of relationship types (§12.1, SIG-ONTO-041). Untyped edges are a schema error. Prohibited edges (§12.8) are intentionally absent._



<div data-search-exclude markdown="1">

URI: [sig:enum/EdgeType](https://ontology.sig-project.org/schema/enum/EdgeType)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| ingests_feed_from | None | B pulls a continuous stream from A; data comes to rest in B |
| pushes_alerts_to | None | A pushes discrete events to B |
| federates_search_to | None | B may query A's data; the corpus stays with A |
| is_queryable_by | None | Inverse asserted from A's side (perspectival) |
| hosts_data_for | None | A stores/controls infrastructure holding B's data (custody) |
| resells_data_from | None | A sells access to data collected by B (money + third-party corpus) |
| provides_platform_to | None | A supplies the software surface B operates on |
| subscribes_to | None | B pays for standing access to A's data/service |
| enrolls_asset_into | None | An asset owned by A is registered into platform B |
| requests_data_from | None | A can issue per-incident, consent-gated requests to B's users |
| distributes_list_to | None | A pushes a watchlist to B; matches do NOT return to A (SIG-ONTO-046) |
| authorizes | None | A grants B legal permission to operate a capability; no data moves |
| replaced_by | None | B's deployment supersedes A's for the same capability at the same org |
| succeeds | None | Temporal substitution (§12 |
| parent_of | None |  |
| child_of | None |  |
| merged_into | None |  |
| split_from | None |  |
| renamed_from | None |  |
| absorbed_by | None |  |
| participates_in | None | Fusion centers, task forces, cooperative purchasing bodies |
| has_jurisdiction_over | None |  |
| operates_within | None | A deployment operating outside the operator's own jurisdiction — first-class,... |
| member_of_network | None |  |
| derived_from_claim | None |  |
| supersedes_claim | None |  |
| contradicts_claim | None |  |
| corroborates_claim | None |  |
| extracted_from_capture | None |  |
| captures_artifact | None |  |
| published_by_source | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [edge_type](../slots/edge_type.md) | Typed from the closed catalog (§12 |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: EdgeType
description: The closed catalog of relationship types (§12.1, SIG-ONTO-041). Untyped
  edges are a schema error. Prohibited edges (§12.8) are intentionally absent.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  ingests_feed_from:
    text: ingests_feed_from
    description: B pulls a continuous stream from A; data comes to rest in B.
  pushes_alerts_to:
    text: pushes_alerts_to
    description: A pushes discrete events to B.
  federates_search_to:
    text: federates_search_to
    description: B may query A's data; the corpus stays with A.
  is_queryable_by:
    text: is_queryable_by
    description: Inverse asserted from A's side (perspectival).
  hosts_data_for:
    text: hosts_data_for
    description: A stores/controls infrastructure holding B's data (custody).
  resells_data_from:
    text: resells_data_from
    description: A sells access to data collected by B (money + third-party corpus).
  provides_platform_to:
    text: provides_platform_to
    description: A supplies the software surface B operates on.
  subscribes_to:
    text: subscribes_to
    description: B pays for standing access to A's data/service.
  enrolls_asset_into:
    text: enrolls_asset_into
    description: An asset owned by A is registered into platform B.
  requests_data_from:
    text: requests_data_from
    description: A can issue per-incident, consent-gated requests to B's users.
  distributes_list_to:
    text: distributes_list_to
    description: A pushes a watchlist to B; matches do NOT return to A (SIG-ONTO-046).
  authorizes:
    text: authorizes
    description: A grants B legal permission to operate a capability; no data moves.
  replaced_by:
    text: replaced_by
    description: B's deployment supersedes A's for the same capability at the same
      org.
  succeeds:
    text: succeeds
    description: Temporal substitution (§12.3).
  parent_of:
    text: parent_of
  child_of:
    text: child_of
  merged_into:
    text: merged_into
  split_from:
    text: split_from
  renamed_from:
    text: renamed_from
  absorbed_by:
    text: absorbed_by
  participates_in:
    text: participates_in
    description: Fusion centers, task forces, cooperative purchasing bodies.
  has_jurisdiction_over:
    text: has_jurisdiction_over
  operates_within:
    text: operates_within
    description: A deployment operating outside the operator's own jurisdiction —
      first-class, not an anomaly.
  member_of_network:
    text: member_of_network
  derived_from_claim:
    text: derived_from_claim
  supersedes_claim:
    text: supersedes_claim
  contradicts_claim:
    text: contradicts_claim
  corroborates_claim:
    text: corroborates_claim
  extracted_from_capture:
    text: extracted_from_capture
  captures_artifact:
    text: captures_artifact
  published_by_source:
    text: published_by_source

```
</details>

</div>