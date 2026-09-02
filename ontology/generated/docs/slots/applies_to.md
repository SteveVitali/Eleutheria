---
search:
  boost: 5.0
---

# Slot: applies_to 


_Organization, Deployment, or Product — polymorphic and repeatable._



<div data-search-exclude markdown="1">



URI: [sig:slot/applies_to](https://ontology.sig-project.org/schema/slot/applies_to)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Policy](../classes/Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Uriorcurie](../types/Uriorcurie.md) |
| Domain Of | [Policy](../classes/Policy.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Policy](../classes/Policy.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:applies_to |
| native | sig:applies_to |




## LinkML Source

<details>
```yaml
name: applies_to
description: Organization, Deployment, or Product — polymorphic and repeatable.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Policy
domain_of:
- Policy
range: uriorcurie
multivalued: true

```
</details></div>