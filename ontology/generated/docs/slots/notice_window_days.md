---
search:
  boost: 5.0
---

# Slot: notice_window_days 


_Days before term end by which non-renewal notice is due (P37.31)._



<div data-search-exclude markdown="1">



URI: [sig:slot/notice_window_days](https://ontology.surveillancegraph.org/schema/slot/notice_window_days)
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
| self | sig:notice_window_days |
| native | sig:notice_window_days |




## LinkML Source

<details>
```yaml
name: notice_window_days
description: Days before term end by which non-renewal notice is due (P37.31).
from_schema: https://ontology.surveillancegraph.org/schema/sig
rank: 1000
owner: Contract
domain_of:
- Contract
range: integer

```
</details></div>