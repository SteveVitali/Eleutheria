---
search:
  boost: 5.0
---

# Slot: scope 

<div data-search-exclude markdown="1">



URI: [sig:slot/scope](https://ontology.sig-project.org/schema/slot/scope)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Capability](../classes/Capability.md) | A verb |  no  |
| [AccessRelationship](../classes/AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |
| [IntegrationEdge](../classes/IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Capability](../classes/Capability.md), [AccessRelationship](../classes/AccessRelationship.md), [IntegrationEdge](../classes/IntegrationEdge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:scope |
| native | sig:scope |




## LinkML Source

<details>
```yaml
name: scope
domain_of:
- Capability
- AccessRelationship
- IntegrationEdge
range: string

```
</details></div>