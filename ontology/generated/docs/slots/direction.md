---
search:
  boost: 5.0
---

# Slot: direction 


_Required; never symmetric by default (SIG-ONTO-049)._



<div data-search-exclude markdown="1">



URI: [sig:slot/direction](https://ontology.sig-project.org/schema/slot/direction)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccessRelationship](../classes/AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Direction](../enums/Direction.md) |
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
| self | sig:direction |
| native | sig:direction |




## LinkML Source

<details>
```yaml
name: direction
description: Required; never symmetric by default (SIG-ONTO-049).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccessRelationship
domain_of:
- AccessRelationship
range: Direction
required: true

```
</details></div>