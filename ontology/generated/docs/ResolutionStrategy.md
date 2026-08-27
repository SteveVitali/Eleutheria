---
search:
  boost: 2.0
---


# Enum: ResolutionStrategy 




_Per-predicate resolution strategy (§28.4, SIG-RECON-012)._



<div data-search-exclude markdown="1">

URI: [sig:ResolutionStrategy](https://ontology.sig-project.org/schema/ResolutionStrategy)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| latest_observation_wins | None |  |
| authoritative_source_wins | None |  |
| interval_union | None |  |
| interval_intersection | None |  |
| max_support | None |  |
| never_resolve | None | Recorded but deliberately not adjudicated (§12 |













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: ResolutionStrategy
description: Per-predicate resolution strategy (§28.4, SIG-RECON-012).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  latest_observation_wins:
    text: latest_observation_wins
  authoritative_source_wins:
    text: authoritative_source_wins
  interval_union:
    text: interval_union
  interval_intersection:
    text: interval_intersection
  max_support:
    text: max_support
  never_resolve:
    text: never_resolve
    description: Recorded but deliberately not adjudicated (§12.4 contested facts).

```
</details>

</div>