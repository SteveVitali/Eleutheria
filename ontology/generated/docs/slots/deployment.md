---
search:
  boost: 5.0
---

# Slot: deployment 

<div data-search-exclude markdown="1">



URI: [sig:slot/deployment](https://ontology.sig-project.org/schema/slot/deployment)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](../classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |
| [ConfigurationState](../classes/ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [PhysicalAsset](../classes/PhysicalAsset.md), [ConfigurationState](../classes/ConfigurationState.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:deployment |
| native | sig:deployment |




## LinkML Source

<details>
```yaml
name: deployment
domain_of:
- PhysicalAsset
- ConfigurationState
range: string

```
</details></div>