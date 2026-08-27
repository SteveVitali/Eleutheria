---
search:
  boost: 5.0
---

# Slot: valid_from 


_When the fact/relationship became true (valid time, §9.2)._



<div data-search-exclude markdown="1">



URI: [sig:slot/valid_from](https://ontology.sig-project.org/schema/slot/valid_from)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Jurisdiction](../classes/Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |
| [Organization](../classes/Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |
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
| Range | [Edtf](../types/Edtf.md) |
| Domain Of | [Jurisdiction](../classes/Jurisdiction.md), [Organization](../classes/Organization.md), [Edge](../classes/Edge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:valid_from |
| native | sig:valid_from |




## LinkML Source

<details>
```yaml
name: valid_from
description: When the fact/relationship became true (valid time, §9.2).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
domain_of:
- Jurisdiction
- Organization
- Edge
range: edtf

```
</details></div>