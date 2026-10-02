---
search:
  boost: 5.0
---

# Slot: bound_at 


_When the binding was asserted — distinct from the capture's retrieval time._



<div data-search-exclude markdown="1">



URI: [sig:slot/bound_at](https://ontology.sig-project.org/schema/slot/bound_at)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ClaimEvidence](../classes/ClaimEvidence.md) | One claim↔capture evidence link (§16 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Datetime](../types/Datetime.md) |
| Domain Of | [ClaimEvidence](../classes/ClaimEvidence.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ClaimEvidence](../classes/ClaimEvidence.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:bound_at |
| native | sig:bound_at |




## LinkML Source

<details>
```yaml
name: bound_at
description: When the binding was asserted — distinct from the capture's retrieval
  time.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: ClaimEvidence
domain_of:
- ClaimEvidence
range: datetime

```
</details></div>