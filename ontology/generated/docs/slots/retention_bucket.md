---
search:
  boost: 5.0
---

# Slot: retention_bucket 


_The ordinal bucket form; comparison operates on intervals, never a coerced point._



<div data-search-exclude markdown="1">



URI: [sig:slot/retention_bucket](https://ontology.sig-project.org/schema/slot/retention_bucket)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ConfigurationState](../classes/ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [ConfigurationState](../classes/ConfigurationState.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ConfigurationState](../classes/ConfigurationState.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:retention_bucket |
| native | sig:retention_bucket |




## LinkML Source

<details>
```yaml
name: retention_bucket
description: The ordinal bucket form; comparison operates on intervals, never a coerced
  point.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: ConfigurationState
domain_of:
- ConfigurationState
range: string

```
</details></div>