---
search:
  boost: 5.0
---

# Slot: target 

<div data-search-exclude markdown="1">



URI: [sig:slot/target](https://ontology.sig-project.org/schema/slot/target)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ResearchTask](../classes/ResearchTask.md) | [NEW] A research task as an object (§11 |  no  |
| [Edge](../classes/Edge.md) | Universal edge requirements (§12 |  no  |
| [AccessRelationship](../classes/AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |
| [IntegrationEdge](../classes/IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |
| [RoleAssignment](../classes/RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |
| [StructuralEdge](../classes/StructuralEdge.md) | Organizational/structural relationships (§12 |  no  |
| [ProvenanceEdge](../classes/ProvenanceEdge.md) | Provenance relationships among claims, captures, artifacts, and sources (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [ResearchTask](../classes/ResearchTask.md), [Edge](../classes/Edge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:target |
| native | sig:target |




## LinkML Source

<details>
```yaml
name: target
domain_of:
- ResearchTask
- Edge
range: string

```
</details></div>