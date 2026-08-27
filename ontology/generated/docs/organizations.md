---
search:
  boost: 5.0
---

# Slot: organizations 

<div data-search-exclude markdown="1">



URI: [sig:organizations](https://ontology.sig-project.org/schema/organizations)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccountabilityEvent](AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Organization](Organization.md) |
| Domain Of | [AccountabilityEvent](AccountabilityEvent.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [AccountabilityEvent](AccountabilityEvent.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:organizations |
| native | sig:organizations |




## LinkML Source

<details>
```yaml
name: organizations
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccountabilityEvent
domain_of:
- AccountabilityEvent
range: Organization
multivalued: true

```
</details></div>