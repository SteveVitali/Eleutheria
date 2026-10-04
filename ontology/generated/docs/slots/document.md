---
search:
  boost: 5.0
---

# Slot: document 

<div data-search-exclude markdown="1">



URI: [sig:slot/document](https://ontology.sig-project.org/schema/slot/document)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Contract](../classes/Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |
| [Policy](../classes/Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Contract](../classes/Contract.md), [Policy](../classes/Policy.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:document |
| native | sig:document |




## LinkML Source

<details>
```yaml
name: document
domain_of:
- Contract
- Policy
range: string

```
</details></div>