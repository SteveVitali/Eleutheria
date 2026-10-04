---
search:
  boost: 5.0
---

# Slot: vendor 

<div data-search-exclude markdown="1">



URI: [sig:slot/vendor](https://ontology.sig-project.org/schema/slot/vendor)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Product](../classes/Product.md) | A product; MUST NOT be equated with a Technology (§11 |  no  |
| [Deployment](../classes/Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |  no  |
| [DataSystem](../classes/DataSystem.md) | Reference databases as infrastructure — representable even where SIG holds no... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Product](../classes/Product.md), [Deployment](../classes/Deployment.md), [DataSystem](../classes/DataSystem.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:vendor |
| native | sig:vendor |




## LinkML Source

<details>
```yaml
name: vendor
domain_of:
- Product
- Deployment
- DataSystem
range: string

```
</details></div>