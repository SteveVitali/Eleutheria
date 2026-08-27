---
search:
  boost: 5.0
---

# Slot: applies_to_cohort 


_Partial termination cohort — all / new_customers_only / existing_customers_only (SIG-ONTO-046)._



<div data-search-exclude markdown="1">



URI: [sig:slot/applies_to_cohort](https://ontology.sig-project.org/schema/slot/applies_to_cohort)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IntegrationEdge](../classes/IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [CohortApplicability](../enums/CohortApplicability.md) |
| Domain Of | [IntegrationEdge](../classes/IntegrationEdge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IntegrationEdge](../classes/IntegrationEdge.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:applies_to_cohort |
| native | sig:applies_to_cohort |




## LinkML Source

<details>
```yaml
name: applies_to_cohort
description: Partial termination cohort — all / new_customers_only / existing_customers_only
  (SIG-ONTO-046).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: IntegrationEdge
domain_of:
- IntegrationEdge
range: CohortApplicability

```
</details></div>