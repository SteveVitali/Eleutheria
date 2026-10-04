---
search:
  boost: 5.0
---

# Slot: automaticity 


_Required; direction/scope/automaticity/kind are all required (SIG-ONTO-049)._



<div data-search-exclude markdown="1">



URI: [sig:slot/automaticity](https://ontology.sig-project.org/schema/slot/automaticity)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccessRelationship](../classes/AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Automaticity](../enums/Automaticity.md) |
| Domain Of | [AccessRelationship](../classes/AccessRelationship.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [AccessRelationship](../classes/AccessRelationship.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:automaticity |
| native | sig:automaticity |




## LinkML Source

<details>
```yaml
name: automaticity
description: Required; direction/scope/automaticity/kind are all required (SIG-ONTO-049).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccessRelationship
domain_of:
- AccessRelationship
range: Automaticity
required: true

```
</details></div>