---
search:
  boost: 5.0
---

# Slot: can_offer_capability 


_Defeasible / marketing-level only (SIG-ONTO-018)._



<div data-search-exclude markdown="1">



URI: [sig:slot/can_offer_capability](https://ontology.sig-project.org/schema/slot/can_offer_capability)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Product](../classes/Product.md) | A product; MUST NOT be equated with a Technology (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [CapabilityCode](../types/CapabilityCode.md) |
| Domain Of | [Product](../classes/Product.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Product](../classes/Product.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:can_offer_capability |
| native | sig:can_offer_capability |




## LinkML Source

<details>
```yaml
name: can_offer_capability
description: Defeasible / marketing-level only (SIG-ONTO-018).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Product
domain_of:
- Product
range: capability_code
multivalued: true

```
</details></div>