---
search:
  boost: 5.0
---

# Slot: instrument_type 

<div data-search-exclude markdown="1">



URI: [sig:slot/instrument_type](https://ontology.sig-project.org/schema/slot/instrument_type)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [FundingInstrument](../classes/FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |  no  |
| [LegalInstrument](../classes/LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [FundingInstrument](../classes/FundingInstrument.md), [LegalInstrument](../classes/LegalInstrument.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:instrument_type |
| native | sig:instrument_type |




## LinkML Source

<details>
```yaml
name: instrument_type
domain_of:
- FundingInstrument
- LegalInstrument
range: string

```
</details></div>