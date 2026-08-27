---
search:
  boost: 2.0
---


# Enum: DetectionMethod 




_How a candidate asset was detected (§11.9, SIG-ONTO-030)._



<div data-search-exclude markdown="1">

URI: [sig:enum/DetectionMethod](https://ontology.sig-project.org/schema/enum/DetectionMethod)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| rf_oui_match | None |  |
| wigle_observation | None |  |
| imagery_detection | None |  |
| contributor_report | None |  |
| model_inference | None |  |
| count_gap_inference | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [detection_method](../slots/detection_method.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: DetectionMethod
description: How a candidate asset was detected (§11.9, SIG-ONTO-030).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  rf_oui_match:
    text: rf_oui_match
  wigle_observation:
    text: wigle_observation
  imagery_detection:
    text: imagery_detection
  contributor_report:
    text: contributor_report
  model_inference:
    text: model_inference
  count_gap_inference:
    text: count_gap_inference

```
</details>

</div>