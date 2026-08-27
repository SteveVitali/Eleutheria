---
search:
  boost: 5.0
---

# Slot: deployments 

<div data-search-exclude markdown="1">



URI: [sig:slot/deployments](https://ontology.sig-project.org/schema/slot/deployments)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccountabilityEvent](../classes/AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Deployment](../classes/Deployment.md) |
| Domain Of | [AccountabilityEvent](../classes/AccountabilityEvent.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
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
| self | sig:deployments |
| native | sig:deployments |




## LinkML Source

<details>
```yaml
name: deployments
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccountabilityEvent
domain_of:
- AccountabilityEvent
range: Deployment
multivalued: true

```
</details></div>