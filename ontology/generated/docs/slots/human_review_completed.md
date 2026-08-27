---
search:
  boost: 5.0
---

# Slot: human_review_completed 


_Person creation MUST have been through human review (SIG-ONTO-016)._



<div data-search-exclude markdown="1">



URI: [sig:slot/human_review_completed](https://ontology.sig-project.org/schema/slot/human_review_completed)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Person](../classes/Person.md) | [NEW] Tightly constrained (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Boolean](../types/Boolean.md) |
| Domain Of | [Person](../classes/Person.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Person](../classes/Person.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:human_review_completed |
| native | sig:human_review_completed |




## LinkML Source

<details>
```yaml
name: human_review_completed
description: Person creation MUST have been through human review (SIG-ONTO-016).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Person
domain_of:
- Person
range: boolean
required: true

```
</details></div>