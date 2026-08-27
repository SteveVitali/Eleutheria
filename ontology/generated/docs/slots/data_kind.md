---
search:
  boost: 5.0
---

# Slot: data_kind 


_The kind of data that moves (part of the edge key, SIG-ONTO-046)._



<div data-search-exclude markdown="1">



URI: [sig:slot/data_kind](https://ontology.sig-project.org/schema/slot/data_kind)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IntegrationEdge](../classes/IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [IntegrationEdge](../classes/IntegrationEdge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IntegrationEdge](../classes/IntegrationEdge.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:data_kind |
| native | sig:data_kind |




## LinkML Source

<details>
```yaml
name: data_kind
description: The kind of data that moves (part of the edge key, SIG-ONTO-046).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: IntegrationEdge
domain_of:
- IntegrationEdge
range: string
required: true

```
</details></div>