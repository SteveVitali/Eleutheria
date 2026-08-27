---
search:
  boost: 5.0
---

# Slot: product_status 

<div data-search-exclude markdown="1">



URI: [sig:slot/product_status](https://ontology.sig-project.org/schema/slot/product_status)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Product](../classes/Product.md) | A product; MUST NOT be equated with a Technology (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ProductStatus](../enums/ProductStatus.md) |
| Domain Of | [Product](../classes/Product.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
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
| self | sig:product_status |
| native | sig:product_status |




## LinkML Source

<details>
```yaml
name: product_status
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Product
domain_of:
- Product
range: ProductStatus

```
</details></div>