---
search:
  boost: 5.0
---

# Slot: document 

<div data-search-exclude markdown="1">



URI: [sig:document](https://ontology.sig-project.org/schema/document)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Contract](Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |
| [Policy](Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](String.md) |
| Domain Of | [Contract](Contract.md), [Policy](Policy.md) |

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