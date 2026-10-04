---
search:
  boost: 5.0
---

# Slot: subject 

<div data-search-exclude markdown="1">



URI: [sig:slot/subject](https://ontology.sig-project.org/schema/slot/subject)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Claim](../classes/Claim.md) | An append-only assertion (subject, predicate, value,  |  no  |
| [Resolution](../classes/Resolution.md) | A stored current-best decision record (§16 |  no  |
| [Contradiction](../classes/Contradiction.md) | A first-class, addressable contradiction object (§31) |  no  |
| [CoverageRecord](../classes/CoverageRecord.md) | [NEW] Makes negative claims queryable (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Claim](../classes/Claim.md), [Resolution](../classes/Resolution.md), [Contradiction](../classes/Contradiction.md), [CoverageRecord](../classes/CoverageRecord.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:subject |
| native | sig:subject |




## LinkML Source

<details>
```yaml
name: subject
domain_of:
- Claim
- Resolution
- Contradiction
- CoverageRecord
range: string

```
</details></div>