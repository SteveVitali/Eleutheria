---
search:
  boost: 5.0
---

# Slot: effective_from 

<div data-search-exclude markdown="1">



URI: [sig:slot/effective_from](https://ontology.sig-project.org/schema/slot/effective_from)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Policy](../classes/Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |  no  |
| [LegalInstrument](../classes/LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Policy](../classes/Policy.md), [LegalInstrument](../classes/LegalInstrument.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:effective_from |
| native | sig:effective_from |




## LinkML Source

<details>
```yaml
name: effective_from
domain_of:
- Policy
- LegalInstrument
range: string

```
</details></div>