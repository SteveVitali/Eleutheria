---
search:
  boost: 5.0
---

# Slot: predicate 

<div data-search-exclude markdown="1">



URI: [sig:predicate](https://ontology.sig-project.org/schema/predicate)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Claim](Claim.md) | An append-only assertion (subject, predicate, value,  |  no  |
| [Resolution](Resolution.md) | A stored current-best decision record (§16 |  no  |
| [Contradiction](Contradiction.md) | A first-class, addressable contradiction object (§31) |  no  |
| [CoverageRecord](CoverageRecord.md) | [NEW] Makes negative claims queryable (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](String.md) |
| Domain Of | [Claim](Claim.md), [Resolution](Resolution.md), [Contradiction](Contradiction.md), [CoverageRecord](CoverageRecord.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:predicate |
| native | sig:predicate |




## LinkML Source

<details>
```yaml
name: predicate
domain_of:
- Claim
- Resolution
- Contradiction
- CoverageRecord
range: string

```
</details></div>