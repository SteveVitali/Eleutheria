---
search:
  boost: 5.0
---

# Slot: docket_number 

<div data-search-exclude markdown="1">



URI: [sig:docket_number](https://ontology.sig-project.org/schema/docket_number)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LegalProceeding](LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](String.md) |
| Domain Of | [LegalProceeding](LegalProceeding.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [LegalProceeding](LegalProceeding.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:docket_number |
| native | sig:docket_number |




## LinkML Source

<details>
```yaml
name: docket_number
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: LegalProceeding
domain_of:
- LegalProceeding
range: string

```
</details></div>