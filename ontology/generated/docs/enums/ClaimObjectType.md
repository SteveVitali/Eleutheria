---
search:
  boost: 2.0
---


# Enum: ClaimObjectType 




_The declared shape of a claim's object — declared, never inferred (§10.3.5)._



<div data-search-exclude markdown="1">

URI: [sig:enum/ClaimObjectType](https://ontology.sig-project.org/schema/enum/ClaimObjectType)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| literal | None |  |
| entity_ref | None |  |
| vocab_term | None |  |
| quantity | None | REQUIRES unit (claim_unit_required) |
| money | None |  |
| geometry | None |  |
| duration | None |  |
| interval | None |  |
| document_ref | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [object_type](../slots/object_type.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: ClaimObjectType
description: The declared shape of a claim's object — declared, never inferred (§10.3.5).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  literal:
    text: literal
  entity_ref:
    text: entity_ref
  vocab_term:
    text: vocab_term
  quantity:
    text: quantity
    description: REQUIRES unit (claim_unit_required).
  money:
    text: money
  geometry:
    text: geometry
  duration:
    text: duration
  interval:
    text: interval
  document_ref:
    text: document_ref

```
</details>

</div>