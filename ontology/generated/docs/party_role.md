---
search:
  boost: 5.0
---

# Slot: party_role 

<div data-search-exclude markdown="1">



URI: [sig:party_role](https://ontology.sig-project.org/schema/party_role)
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
| Multivalued | Yes |
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
| self | sig:party_role |
| native | sig:party_role |




## LinkML Source

<details>
```yaml
name: party_role
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: LegalProceeding
domain_of:
- LegalProceeding
range: string
multivalued: true

```
</details></div>