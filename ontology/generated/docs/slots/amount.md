---
search:
  boost: 5.0
---

# Slot: amount 

<div data-search-exclude markdown="1">



URI: [sig:slot/amount](https://ontology.sig-project.org/schema/slot/amount)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Contract](../classes/Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |
| [FundingInstrument](../classes/FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Contract](../classes/Contract.md), [FundingInstrument](../classes/FundingInstrument.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:amount |
| native | sig:amount |




## LinkML Source

<details>
```yaml
name: amount
domain_of:
- Contract
- FundingInstrument
range: string

```
</details></div>