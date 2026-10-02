---
search:
  boost: 5.0
---

# Slot: blob_digest 


_The deduplicated evidence_blob identity the bytes dedup to (SIG-EVID-004)._



<div data-search-exclude markdown="1">



URI: [sig:slot/blob_digest](https://ontology.sig-project.org/schema/slot/blob_digest)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [EvidenceCapture](../classes/EvidenceCapture.md) | A content-addressed capture of an artifact at a time (§10 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [EvidenceCapture](../classes/EvidenceCapture.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [EvidenceCapture](../classes/EvidenceCapture.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:blob_digest |
| native | sig:blob_digest |




## LinkML Source

<details>
```yaml
name: blob_digest
description: The deduplicated evidence_blob identity the bytes dedup to (SIG-EVID-004).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: EvidenceCapture
domain_of:
- EvidenceCapture
range: string

```
</details></div>