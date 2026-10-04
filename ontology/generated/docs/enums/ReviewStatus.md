---
search:
  boost: 2.0
---


# Enum: ReviewStatus 




_The claim's review state (append-only; a review lands as a new claim)._



<div data-search-exclude markdown="1">

URI: [sig:enum/ReviewStatus](https://ontology.sig-project.org/schema/enum/ReviewStatus)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| unreviewed | None |  |
| machine_accepted | None |  |
| human_verified | None |  |
| disputed | None |  |
| retracted | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [review_status](../slots/review_status.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: ReviewStatus
description: The claim's review state (append-only; a review lands as a new claim).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  unreviewed:
    text: unreviewed
  machine_accepted:
    text: machine_accepted
  human_verified:
    text: human_verified
  disputed:
    text: disputed
  retracted:
    text: retracted

```
</details>

</div>