---
search:
  boost: 5.0
---

# Slot: parent_jurisdiction 


_Multiple parents permitted; hierarchies overlap (SIG-ONTO-010)._



<div data-search-exclude markdown="1">



URI: [sig:slot/parent_jurisdiction](https://ontology.sig-project.org/schema/slot/parent_jurisdiction)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Jurisdiction](../classes/Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Jurisdiction](../classes/Jurisdiction.md) |
| Domain Of | [Jurisdiction](../classes/Jurisdiction.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Jurisdiction](../classes/Jurisdiction.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:parent_jurisdiction |
| native | sig:parent_jurisdiction |




## LinkML Source

<details>
```yaml
name: parent_jurisdiction
description: Multiple parents permitted; hierarchies overlap (SIG-ONTO-010).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Jurisdiction
domain_of:
- Jurisdiction
range: Jurisdiction
multivalued: true

```
</details></div>