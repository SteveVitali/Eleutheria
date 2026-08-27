---
search:
  boost: 5.0
---

# Slot: geometry 


_Optional (SIG-GEO-004)._



<div data-search-exclude markdown="1">



URI: [sig:geometry](https://ontology.sig-project.org/schema/geometry)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [GeometryWkt](GeometryWkt.md) |
| Domain Of | [PhysicalAsset](PhysicalAsset.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [PhysicalAsset](PhysicalAsset.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:geometry |
| native | sig:geometry |




## LinkML Source

<details>
```yaml
name: geometry
description: Optional (SIG-GEO-004).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: PhysicalAsset
domain_of:
- PhysicalAsset
range: geometry_wkt

```
</details></div>