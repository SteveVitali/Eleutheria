---
search:
  boost: 2.0
---


# Enum: AcquisitionMethod 




_Acquisition method, internationalized (§13.8). foia_request is US-specific; the abstract parent is records_request with national children, plus no_equivalent_available (itself a coverage fact)._



<div data-search-exclude markdown="1">

URI: [sig:AcquisitionMethod](https://ontology.sig-project.org/schema/AcquisitionMethod)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| records_request | None | Abstract parent of all public-records regimes |
| us.foia | None |  |
| us.state_public_records | None |  |
| fr.cada | None |  |
| uk.foi | None |  |
| eu.access_to_documents | None |  |
| no_equivalent_available | None |  |













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: AcquisitionMethod
description: Acquisition method, internationalized (§13.8). foia_request is US-specific;
  the abstract parent is records_request with national children, plus no_equivalent_available
  (itself a coverage fact).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  records_request:
    text: records_request
    description: Abstract parent of all public-records regimes.
  us.foia:
    text: us.foia
  us.state_public_records:
    text: us.state_public_records
  fr.cada:
    text: fr.cada
  uk.foi:
    text: uk.foi
  eu.access_to_documents:
    text: eu.access_to_documents
  no_equivalent_available:
    text: no_equivalent_available

```
</details>

</div>