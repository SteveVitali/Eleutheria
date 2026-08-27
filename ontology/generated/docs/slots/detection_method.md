---
search:
  boost: 5.0
---

# Slot: detection_method 

<div data-search-exclude markdown="1">



URI: [sig:slot/detection_method](https://ontology.sig-project.org/schema/slot/detection_method)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [CandidateAsset](../classes/CandidateAsset.md) | [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NO... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DetectionMethod](../enums/DetectionMethod.md) |
| Domain Of | [CandidateAsset](../classes/CandidateAsset.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [CandidateAsset](../classes/CandidateAsset.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:detection_method |
| native | sig:detection_method |




## LinkML Source

<details>
```yaml
name: detection_method
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: CandidateAsset
domain_of:
- CandidateAsset
range: DetectionMethod

```
</details></div>