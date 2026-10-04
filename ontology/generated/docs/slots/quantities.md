---
search:
  boost: 5.0
---

# Slot: quantities 

<div data-search-exclude markdown="1">



URI: [sig:slot/quantities](https://ontology.sig-project.org/schema/slot/quantities)
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
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Contract](../classes/Contract.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:quantities |
| native | sig:quantities |




## LinkML Source

<details>
```yaml
name: quantities
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Contract
domain_of:
- Contract
range: integer
multivalued: true

```
</details></div>