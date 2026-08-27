---
search:
  boost: 5.0
---

# Slot: retention_days 


_Duration OR ordinal bucket; MUST accept both (SIG-ONTO-035a)._



<div data-search-exclude markdown="1">



URI: [sig:retention_days](https://ontology.sig-project.org/schema/retention_days)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ConfigurationState](ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DurationIso](DurationIso.md) |
| Domain Of | [ConfigurationState](ConfigurationState.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ConfigurationState](ConfigurationState.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:retention_days |
| native | sig:retention_days |




## LinkML Source

<details>
```yaml
name: retention_days
description: Duration OR ordinal bucket; MUST accept both (SIG-ONTO-035a).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: ConfigurationState
domain_of:
- ConfigurationState
range: duration_iso

```
</details></div>