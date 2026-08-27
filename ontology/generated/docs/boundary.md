---
search:
  boost: 5.0
---

# Slot: boundary 


_MultiPolygon, 4326._



<div data-search-exclude markdown="1">



URI: [sig:boundary](https://ontology.sig-project.org/schema/boundary)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Jurisdiction](Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [GeometryWkt](GeometryWkt.md) |
| Domain Of | [Jurisdiction](Jurisdiction.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Jurisdiction](Jurisdiction.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:boundary |
| native | sig:boundary |




## LinkML Source

<details>
```yaml
name: boundary
description: MultiPolygon, 4326.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Jurisdiction
domain_of:
- Jurisdiction
range: geometry_wkt

```
</details></div>