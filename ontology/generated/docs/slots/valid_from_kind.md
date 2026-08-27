---
search:
  boost: 5.0
---

# Slot: valid_from_kind 


_Whether valid_from is known, unknown, or ongoing (§9.5, SIG-ONTO-044)._



<div data-search-exclude markdown="1">



URI: [sig:slot/valid_from_kind](https://ontology.sig-project.org/schema/slot/valid_from_kind)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
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
| Range | [TemporalBoundKind](../enums/TemporalBoundKind.md) |
| Domain Of | [Edge](../classes/Edge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:valid_from_kind |
| native | sig:valid_from_kind |




## LinkML Source

<details>
```yaml
name: valid_from_kind
description: Whether valid_from is known, unknown, or ongoing (§9.5, SIG-ONTO-044).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
domain_of:
- Edge
range: TemporalBoundKind

```
</details></div>