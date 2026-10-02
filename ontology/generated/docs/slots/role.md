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
| [ClaimEvidence](../classes/ClaimEvidence.md) | One claim↔capture evidence link (§16 |  no  |
| [RoleAssignment](../classes/RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [ClaimEvidence](../classes/ClaimEvidence.md), [RoleAssignment](../classes/RoleAssignment.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:role |
| native | sig:role |




## LinkML Source

<details>
```yaml
name: role
domain_of:
- ClaimEvidence
- RoleAssignment
range: string

```
</details></div>