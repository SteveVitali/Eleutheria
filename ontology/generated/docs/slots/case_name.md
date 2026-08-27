---
search:
  boost: 5.0
---

# Slot: case_name 

<div data-search-exclude markdown="1">



URI: [sig:slot/case_name](https://ontology.sig-project.org/schema/slot/case_name)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LegalProceeding](../classes/LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
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
| self | sig:case_name |
| native | sig:case_name |




## LinkML Source

<details>
```yaml
name: case_name
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: LegalProceeding
domain_of:
- LegalProceeding
range: string

```
</details></div>