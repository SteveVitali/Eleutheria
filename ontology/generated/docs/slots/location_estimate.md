---
search:
  boost: 5.0
---

# Slot: location_estimate 


_With estimate_radius_m — never a bare point._



<div data-search-exclude markdown="1">



URI: [sig:slot/location_estimate](https://ontology.sig-project.org/schema/slot/location_estimate)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CandidateAsset](../classes/CandidateAsset.md) | [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NO... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [GeometryWkt](../types/GeometryWkt.md) |
| Domain Of | [CandidateAsset](../classes/CandidateAsset.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [CandidateAsset](../classes/CandidateAsset.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:location_estimate |
| native | sig:location_estimate |




## LinkML Source

<details>
```yaml
name: location_estimate
description: With estimate_radius_m — never a bare point.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: CandidateAsset
domain_of:
- CandidateAsset
range: geometry_wkt

```
</details></div>