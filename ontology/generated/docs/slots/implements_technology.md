---
search:
  boost: 5.0
---

# Slot: implements_technology 

<div data-search-exclude markdown="1">



URI: [sig:slot/implements_technology](https://ontology.sig-project.org/schema/slot/implements_technology)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Product](../classes/Product.md) | A product; MUST NOT be equated with a Technology (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [TechnologyCode](../types/TechnologyCode.md) |
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
| self | sig:implements_technology |
| native | sig:implements_technology |




## LinkML Source

<details>
```yaml
name: implements_technology
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Product
domain_of:
- Product
range: technology_code
multivalued: true

```
</details></div>