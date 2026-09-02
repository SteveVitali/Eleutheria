---
search:
  boost: 2.0
---


# Enum: TemporalBoundKind 




_How a temporal bound is known (§9.5)._



<div data-search-exclude markdown="1">

URI: [sig:enum/TemporalBoundKind](https://ontology.sig-project.org/schema/enum/TemporalBoundKind)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| known | None | A specific known bound |
| unknown | None | Bound exists but is not known |
| ongoing | None | The fact is still in force (open interval) |




## Slots

| Name | Description |
| ---  | --- |
| [valid_from_kind](../slots/valid_from_kind.md) | Whether valid_from is known, unknown, or ongoing (§9 |
| [valid_to_kind](../slots/valid_to_kind.md) | Whether valid_to is known, unknown, or ongoing (§9 |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: TemporalBoundKind
description: How a temporal bound is known (§9.5).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  known:
    text: known
    description: A specific known bound.
  unknown:
    text: unknown
    description: Bound exists but is not known.
  ongoing:
    text: ongoing
    description: The fact is still in force (open interval).

```
</details>

</div>