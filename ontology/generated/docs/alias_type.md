---
search:
  boost: 5.0
---

# Slot: alias_type 

<div data-search-exclude markdown="1">



URI: [sig:alias_type](https://ontology.sig-project.org/schema/alias_type)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Organization](Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [AliasType](AliasType.md) |
| Domain Of | [Organization](Organization.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Organization](Organization.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:alias_type |
| native | sig:alias_type |




## LinkML Source

<details>
```yaml
name: alias_type
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Organization
domain_of:
- Organization
range: AliasType
multivalued: true

```
</details></div>