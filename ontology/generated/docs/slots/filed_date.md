---
search:
  boost: 5.0
---

# Slot: filed_date 

<div data-search-exclude markdown="1">



URI: [sig:slot/filed_date](https://ontology.sig-project.org/schema/slot/filed_date)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [LegalProceeding](../classes/LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |  no  |
| [RecordsRequest](../classes/RecordsRequest.md) | [NEW] A public-records request SIG both cites as provenance and generates as ... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [LegalProceeding](../classes/LegalProceeding.md), [RecordsRequest](../classes/RecordsRequest.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:filed_date |
| native | sig:filed_date |




## LinkML Source

<details>
```yaml
name: filed_date
domain_of:
- LegalProceeding
- RecordsRequest
range: string

```
</details></div>