---
search:
  boost: 5.0
---

# Slot: canonical_name 


_A claim, not an authoritative column (§8.2, SIG-ONTO-003)._



<div data-search-exclude markdown="1">



URI: [sig:canonical_name](https://ontology.sig-project.org/schema/canonical_name)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Organization](Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](String.md) |
| Domain Of | [Organization](Organization.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
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
| self | sig:canonical_name |
| native | sig:canonical_name |




## LinkML Source

<details>
```yaml
name: canonical_name
description: A claim, not an authoritative column (§8.2, SIG-ONTO-003).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Organization
domain_of:
- Organization
range: string

```
</details></div>