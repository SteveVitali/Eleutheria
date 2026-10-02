---
search:
  boost: 5.0
---

# Slot: ocfl_object_id 


_The OCFL object the capture's bytes were committed under._



<div data-search-exclude markdown="1">



URI: [sig:slot/ocfl_object_id](https://ontology.sig-project.org/schema/slot/ocfl_object_id)
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
| self | sig:ocfl_object_id |
| native | sig:ocfl_object_id |




## LinkML Source

<details>
```yaml
name: ocfl_object_id
description: The OCFL object the capture's bytes were committed under.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: EvidenceCapture
domain_of:
- EvidenceCapture
range: string

```
</details></div>