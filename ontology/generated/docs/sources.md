---
search:
  boost: 5.0
---

# Slot: sources 


_Supporting evidence artifacts/sources; every fact is evidenced (SIG-CHART-013)._



<div data-search-exclude markdown="1">



URI: [sig:sources](https://ontology.sig-project.org/schema/sources)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccountabilityEvent](AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |
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
| Range | [Uriorcurie](Uriorcurie.md) |
| Domain Of | [AccountabilityEvent](AccountabilityEvent.md), [Edge](Edge.md) |

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