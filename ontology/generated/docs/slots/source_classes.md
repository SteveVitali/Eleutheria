---
search:
  boost: 5.0
---

# Slot: source_classes 


_The OL-2E-AL-03 class of each entry in `sources`, index-aligned (as `parties`/`party_role` on LegalProceeding). Recording the class on the evidence link is what makes a claim resting only on advocacy analysis distinguishable from one resting on a court record (SIG-ONTO-039)._



<div data-search-exclude markdown="1">



URI: [sig:slot/source_classes](https://ontology.sig-project.org/schema/slot/source_classes)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccountabilityEvent](../classes/AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [SourceClass](../enums/SourceClass.md) |
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
| self | sig:source_classes |
| native | sig:source_classes |




## LinkML Source

<details>
```yaml
name: source_classes
description: The OL-2E-AL-03 class of each entry in `sources`, index-aligned (as `parties`/`party_role`
  on LegalProceeding). Recording the class on the evidence link is what makes a claim
  resting only on advocacy analysis distinguishable from one resting on a court record
  (SIG-ONTO-039).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccountabilityEvent
domain_of:
- AccountabilityEvent
range: SourceClass
multivalued: true

```
</details></div>