---
search:
  boost: 5.0
---

# Slot: asset_type 


_A Technology reference, not a free string._



<div data-search-exclude markdown="1">



URI: [sig:asset_type](https://ontology.sig-project.org/schema/asset_type)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [TechnologyCode](TechnologyCode.md) |
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
| self | sig:asset_type |
| native | sig:asset_type |




## LinkML Source

<details>
```yaml
name: asset_type
description: A Technology reference, not a free string.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: PhysicalAsset
domain_of:
- PhysicalAsset
range: technology_code

```
</details></div>