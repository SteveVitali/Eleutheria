---
search:
  boost: 5.0
---

# Slot: posture 

<div data-search-exclude markdown="1">



URI: [sig:slot/posture](https://ontology.sig-project.org/schema/slot/posture)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LegalProceeding](../classes/LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ProceedingPosture](../enums/ProceedingPosture.md) |
| Domain Of | [LegalProceeding](../classes/LegalProceeding.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [LegalProceeding](../classes/LegalProceeding.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:posture |
| native | sig:posture |




## LinkML Source

<details>
```yaml
name: posture
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: LegalProceeding
domain_of:
- LegalProceeding
range: ProceedingPosture

```
</details></div>