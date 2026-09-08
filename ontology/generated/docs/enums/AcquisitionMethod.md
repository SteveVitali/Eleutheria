---
search:
  boost: 2.0
---


# Enum: AcquisitionMethod 




_Acquisition method, internationalized (§13.8, SIG-ONTO-068). foia_request is US-specific; the abstract parent `records_request` carries national children linked by `is_a`, plus `no_equivalent_available` for jurisdictions with no access regime (itself a coverage fact worth recording)._



<div data-search-exclude markdown="1">

URI: [sig:enum/AcquisitionMethod](https://ontology.sig-project.org/schema/enum/AcquisitionMethod)

## Permissible Values
| Value | Meaning | Description | Additional Info |
| --- | --- | --- | --- |
| records_request | None | Abstract parent of all public-records regimes ||
| us.foia | None |  | Is-A: NONE<br>|
| us.state_public_records | None |  | Is-A: NONE<br>|
| fr.cada | None |  | Is-A: NONE<br>|
| uk.foi | None |  | Is-A: NONE<br>|
| eu.access_to_documents | None |  | Is-A: NONE<br>|
| no_equivalent_available | None | No access regime exists in the jurisdiction — a recorded coverage fact, not a... ||













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: AcquisitionMethod
description: Acquisition method, internationalized (§13.8, SIG-ONTO-068). foia_request
  is US-specific; the abstract parent `records_request` carries national children
  linked by `is_a`, plus `no_equivalent_available` for jurisdictions with no access
  regime (itself a coverage fact worth recording).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  records_request:
    text: records_request
    description: Abstract parent of all public-records regimes.
  us.foia:
    text: us.foia
    is_a: records_request
  us.state_public_records:
    text: us.state_public_records
    is_a: records_request
  fr.cada:
    text: fr.cada
    is_a: records_request
  uk.foi:
    text: uk.foi
    is_a: records_request
  eu.access_to_documents:
    text: eu.access_to_documents
    is_a: records_request
  no_equivalent_available:
    text: no_equivalent_available
    description: No access regime exists in the jurisdiction — a recorded coverage
      fact, not a records-request child.

```
</details>

</div>