---
search:
  boost: 5.0
---

# Slot: last_observed 

<div data-search-exclude markdown="1">



URI: [sig:last_observed](https://ontology.sig-project.org/schema/last_observed)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Datetime](Datetime.md) |
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
| self | sig:last_observed |
| native | sig:last_observed |




## LinkML Source

<details>
```yaml
name: last_observed
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: PhysicalAsset
domain_of:
- PhysicalAsset
range: datetime

```
</details></div>