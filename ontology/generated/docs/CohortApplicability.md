---
search:
  boost: 2.0
---


# Enum: CohortApplicability 




_Which cohort an integration termination applies to (§12.3, SIG-ONTO-046)._



<div data-search-exclude markdown="1">

URI: [sig:CohortApplicability](https://ontology.sig-project.org/schema/CohortApplicability)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| all | None |  |
| new_customers_only | None |  |
| existing_customers_only | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [applies_to_cohort](applies_to_cohort.md) | Partial termination cohort — all / new_customers_only / existing_customers_on... |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: CohortApplicability
description: Which cohort an integration termination applies to (§12.3, SIG-ONTO-046).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  all:
    text: all
  new_customers_only:
    text: new_customers_only
  existing_customers_only:
    text: existing_customers_only

```
</details>

</div>