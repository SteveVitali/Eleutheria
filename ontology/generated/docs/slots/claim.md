---
search:
  boost: 5.0
---

# Slot: claim 

<div data-search-exclude markdown="1">



URI: [sig:slot/claim](https://ontology.sig-project.org/schema/slot/claim)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ClaimEvidence](../classes/ClaimEvidence.md) | One claim↔capture evidence link (§16 |  no  |
| [ClaimQualifier](../classes/ClaimQualifier.md) | One typed qualifier statement on a claim (§16 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [ClaimEvidence](../classes/ClaimEvidence.md), [ClaimQualifier](../classes/ClaimQualifier.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:claim |
| native | sig:claim |




## LinkML Source

<details>
```yaml
name: claim
domain_of:
- ClaimEvidence
- ClaimQualifier
range: string

```
</details></div>