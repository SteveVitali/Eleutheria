---
search:
  boost: 5.0
---

# Slot: period 

<div data-search-exclude markdown="1">



URI: [sig:slot/period](https://ontology.sig-project.org/schema/slot/period)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [FundingInstrument](../classes/FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |  no  |
| [UsageAggregate](../classes/UsageAggregate.md) | Aggregated usage; direction is the point (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [FundingInstrument](../classes/FundingInstrument.md), [UsageAggregate](../classes/UsageAggregate.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:period |
| native | sig:period |




## LinkML Source

<details>
```yaml
name: period
domain_of:
- FundingInstrument
- UsageAggregate
range: string

```
</details></div>