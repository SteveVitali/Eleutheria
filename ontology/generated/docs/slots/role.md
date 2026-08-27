---
search:
  boost: 5.0
---

# Slot: role 

<div data-search-exclude markdown="1">



URI: [sig:slot/role](https://ontology.sig-project.org/schema/slot/role)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [RoleAssignment](../classes/RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Role](../enums/Role.md) |
| Domain Of | [RoleAssignment](../classes/RoleAssignment.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [RoleAssignment](../classes/RoleAssignment.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:role |
| native | sig:role |




## LinkML Source

<details>
```yaml
name: role
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: RoleAssignment
domain_of:
- RoleAssignment
range: Role
required: true

```
</details></div>