---
search:
  boost: 5.0
---

# Slot: renewal_term_months 


_Length in months of each stated renewal term (P37.31)._



<div data-search-exclude markdown="1">



URI: [sig:slot/renewal_term_months](https://ontology.surveillancegraph.org/schema/slot/renewal_term_months)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Contract](../classes/Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Integer](../types/Integer.md) |
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
| self | sig:renewal_term_months |
| native | sig:renewal_term_months |




## LinkML Source

<details>
```yaml
name: renewal_term_months
description: Length in months of each stated renewal term (P37.31).
from_schema: https://ontology.surveillancegraph.org/schema/sig
rank: 1000
owner: Contract
domain_of:
- Contract
range: integer

```
</details></div>