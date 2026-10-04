---
search:
  boost: 5.0
---

# Slot: sources 


_Supporting evidence artifacts/sources; every fact is evidenced (SIG-CHART-013)._



<div data-search-exclude markdown="1">



URI: [sig:slot/sources](https://ontology.sig-project.org/schema/slot/sources)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccountabilityEvent](../classes/AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |
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
| Range | [Uriorcurie](../types/Uriorcurie.md) |
| Domain Of | [AccountabilityEvent](../classes/AccountabilityEvent.md), [Edge](../classes/Edge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:sources |
| native | sig:sources |




## LinkML Source

<details>
```yaml
name: sources
description: Supporting evidence artifacts/sources; every fact is evidenced (SIG-CHART-013).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
domain_of:
- AccountabilityEvent
- Edge
range: uriorcurie
multivalued: true

```
</details></div>