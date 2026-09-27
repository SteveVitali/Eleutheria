---
search:
  boost: 5.0
---

# Slot: observed_unknown_reason 


_REQUIRED when observed_at is absent — an absent observation time always says why._



<div data-search-exclude markdown="1">



URI: [sig:slot/observed_unknown_reason](https://ontology.sig-project.org/schema/slot/observed_unknown_reason)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Claim](../classes/Claim.md) | An append-only assertion (subject, predicate, value,  |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Claim](../classes/Claim.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Claim](../classes/Claim.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:observed_unknown_reason |
| native | sig:observed_unknown_reason |




## LinkML Source

<details>
```yaml
name: observed_unknown_reason
description: REQUIRED when observed_at is absent — an absent observation time always
  says why.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Claim
domain_of:
- Claim
range: string

```
</details></div>