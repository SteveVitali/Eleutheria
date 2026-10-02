---
search:
  boost: 2.0
---


# Enum: CaptureClassification 




_What an evidence_capture row actually is (SIG-TRUST-002). 'legacy' is the honest default for rows whose provenance predates the classification._



<div data-search-exclude markdown="1">

URI: [sig:enum/CaptureClassification](https://ontology.sig-project.org/schema/enum/CaptureClassification)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| actual | None | A byte-bearing capture of a real source URI |
| synthetic | None | The connector sink's per-(source, genre, run) placeholder |
| legacy | None | Pre-classification rows whose class is unverifiable |




## Slots

| Name | Description |
| ---  | --- |
| [capture_classification](../slots/capture_classification.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: CaptureClassification
description: What an evidence_capture row actually is (SIG-TRUST-002). 'legacy' is
  the honest default for rows whose provenance predates the classification.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  actual:
    text: actual
    description: A byte-bearing capture of a real source URI.
  synthetic:
    text: synthetic
    description: The connector sink's per-(source, genre, run) placeholder.
  legacy:
    text: legacy
    description: Pre-classification rows whose class is unverifiable.

```
</details>

</div>