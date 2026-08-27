---
search:
  boost: 5.0
---

# Slot: retention 


_A ConfigurationState fact where it varies per deployment._



<div data-search-exclude markdown="1">



URI: [sig:retention](https://ontology.sig-project.org/schema/retention)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [DataSystem](DataSystem.md) | Reference databases as infrastructure — representable even where SIG holds no... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DurationIso](DurationIso.md) |
| Domain Of | [DataSystem](DataSystem.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [DataSystem](DataSystem.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:retention |
| native | sig:retention |




## LinkML Source

<details>
```yaml
name: retention
description: A ConfigurationState fact where it varies per deployment.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: DataSystem
domain_of:
- DataSystem
range: duration_iso

```
</details></div>