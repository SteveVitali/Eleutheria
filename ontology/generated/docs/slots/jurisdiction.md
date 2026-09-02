---
search:
  boost: 5.0
---

# Slot: jurisdiction 

<div data-search-exclude markdown="1">



URI: [sig:slot/jurisdiction](https://ontology.sig-project.org/schema/slot/jurisdiction)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Organization](../classes/Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |
| [Deployment](../classes/Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |  no  |
| [LegalInstrument](../classes/LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Organization](../classes/Organization.md), [Deployment](../classes/Deployment.md), [LegalInstrument](../classes/LegalInstrument.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:jurisdiction |
| native | sig:jurisdiction |




## LinkML Source

<details>
```yaml
name: jurisdiction
domain_of:
- Organization
- Deployment
- LegalInstrument
range: string

```
</details></div>