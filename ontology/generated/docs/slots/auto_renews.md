---
search:
  boost: 5.0
---

# Slot: auto_renews 


_Whether the contract renews automatically absent notice — the dated renewal clause value the decision calendar derives a renewal_deadline from (P37.31 / K7 WX-02)._



<div data-search-exclude markdown="1">



URI: [sig:slot/auto_renews](https://ontology.surveillancegraph.org/schema/slot/auto_renews)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Contract](../classes/Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Boolean](../types/Boolean.md) |
| Domain Of | [Contract](../classes/Contract.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Contract](../classes/Contract.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.surveillancegraph.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:auto_renews |
| native | sig:auto_renews |




## LinkML Source

<details>
```yaml
name: auto_renews
description: Whether the contract renews automatically absent notice — the dated renewal
  clause value the decision calendar derives a renewal_deadline from (P37.31 / K7
  WX-02).
from_schema: https://ontology.surveillancegraph.org/schema/sig
rank: 1000
owner: Contract
domain_of:
- Contract
range: boolean

```
</details></div>