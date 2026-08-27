---
search:
  boost: 5.0
---

# Slot: party 


_The Organization (or, rarely and reviewed, Person) holding the role._



<div data-search-exclude markdown="1">



URI: [sig:party](https://ontology.sig-project.org/schema/party)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [RoleAssignment](RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Uriorcurie](Uriorcurie.md) |
| Domain Of | [RoleAssignment](RoleAssignment.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [RoleAssignment](RoleAssignment.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:party |
| native | sig:party |




## LinkML Source

<details>
```yaml
name: party
description: The Organization (or, rarely and reviewed, Person) holding the role.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: RoleAssignment
domain_of:
- RoleAssignment
range: uriorcurie
required: true

```
</details></div>