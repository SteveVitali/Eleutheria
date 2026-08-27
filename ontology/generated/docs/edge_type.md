---
search:
  boost: 5.0
---

# Slot: edge_type 


_Typed from the closed catalog (§12.1.2)._



<div data-search-exclude markdown="1">



URI: [sig:edge_type](https://ontology.sig-project.org/schema/edge_type)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Edge](Edge.md) | Universal edge requirements (§12 |  no  |
| [AccessRelationship](AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |
| [IntegrationEdge](IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |
| [RoleAssignment](RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |
| [StructuralEdge](StructuralEdge.md) | Organizational/structural relationships (§12 |  no  |
| [ProvenanceEdge](ProvenanceEdge.md) | Provenance relationships among claims, captures, artifacts, and sources (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [EdgeType](EdgeType.md) |
| Domain Of | [Edge](Edge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Edge](Edge.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:edge_type |
| native | sig:edge_type |




## LinkML Source

<details>
```yaml
name: edge_type
description: Typed from the closed catalog (§12.1.2).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Edge
domain_of:
- Edge
range: EdgeType
required: true

```
</details></div>