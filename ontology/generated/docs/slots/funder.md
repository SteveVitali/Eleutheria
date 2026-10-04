---
search:
  boost: 5.0
---

# Slot: funder 

<div data-search-exclude markdown="1">



URI: [sig:slot/funder](https://ontology.sig-project.org/schema/slot/funder)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [FundingInstrument](../classes/FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Organization](../classes/Organization.md) |
| Domain Of | [FundingInstrument](../classes/FundingInstrument.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [FundingInstrument](../classes/FundingInstrument.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:funder |
| native | sig:funder |




## LinkML Source

<details>
```yaml
name: funder
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: FundingInstrument
domain_of:
- FundingInstrument
range: Organization

```
</details></div>