---
search:
  boost: 5.0
---

# Slot: epistemic_status 

<div data-search-exclude markdown="1">



URI: [sig:slot/epistemic_status](https://ontology.sig-project.org/schema/slot/epistemic_status)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccountabilityEvent](../classes/AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [EpistemicStatus](../enums/EpistemicStatus.md) |
| Domain Of | [AccountabilityEvent](../classes/AccountabilityEvent.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [AccountabilityEvent](../classes/AccountabilityEvent.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:epistemic_status |
| native | sig:epistemic_status |




## LinkML Source

<details>
```yaml
name: epistemic_status
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccountabilityEvent
domain_of:
- AccountabilityEvent
range: EpistemicStatus
required: true

```
</details></div>