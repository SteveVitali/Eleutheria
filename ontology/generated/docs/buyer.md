---
search:
  boost: 5.0
---

# Slot: buyer 

<div data-search-exclude markdown="1">



URI: [sig:buyer](https://ontology.sig-project.org/schema/buyer)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Contract](Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Organization](Organization.md) |
| Domain Of | [Contract](Contract.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Contract](Contract.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:buyer |
| native | sig:buyer |




## LinkML Source

<details>
```yaml
name: buyer
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Contract
domain_of:
- Contract
range: Organization

```
</details></div>