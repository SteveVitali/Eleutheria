---
search:
  boost: 5.0
---

# Slot: mobility 

<div data-search-exclude markdown="1">



URI: [sig:slot/mobility](https://ontology.sig-project.org/schema/slot/mobility)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](../classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Mobility](../enums/Mobility.md) |
| Domain Of | [PhysicalAsset](../classes/PhysicalAsset.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [PhysicalAsset](../classes/PhysicalAsset.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:mobility |
| native | sig:mobility |




## LinkML Source

<details>
```yaml
name: mobility
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: PhysicalAsset
domain_of:
- PhysicalAsset
range: Mobility

```
</details></div>