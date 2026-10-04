---
search:
  boost: 5.0
---

# Slot: confirmation_status 

<div data-search-exclude markdown="1">



URI: [sig:slot/confirmation_status](https://ontology.sig-project.org/schema/slot/confirmation_status)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](../classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ConfirmationStatus](../enums/ConfirmationStatus.md) |
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
| self | sig:confirmation_status |
| native | sig:confirmation_status |




## LinkML Source

<details>
```yaml
name: confirmation_status
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: PhysicalAsset
domain_of:
- PhysicalAsset
range: ConfirmationStatus

```
</details></div>