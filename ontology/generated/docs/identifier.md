---
search:
  boost: 5.0
---

# Slot: identifier 


_Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-006)._



<div data-search-exclude markdown="1">



URI: [sig:identifier](https://ontology.sig-project.org/schema/identifier)
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
| self | sig:identifier |
| native | sig:identifier |




## LinkML Source

<details>
```yaml
name: identifier
description: Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-006).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Organization
domain_of:
- Organization
range: string
multivalued: true

```
</details></div>