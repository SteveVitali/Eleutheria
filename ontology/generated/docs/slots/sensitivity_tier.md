---
search:
  boost: 5.0
---

# Slot: sensitivity_tier 

<div data-search-exclude markdown="1">



URI: [sig:slot/sensitivity_tier](https://ontology.sig-project.org/schema/slot/sensitivity_tier)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](../classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |
| [Claim](../classes/Claim.md) | An append-only assertion (subject, predicate, value,  |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [PhysicalAsset](../classes/PhysicalAsset.md), [Claim](../classes/Claim.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:sensitivity_tier |
| native | sig:sensitivity_tier |




## LinkML Source

<details>
```yaml
name: sensitivity_tier
domain_of:
- PhysicalAsset
- Claim
range: string

```
</details></div>