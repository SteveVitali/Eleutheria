---
search:
  boost: 5.0
---

# Slot: mfa_required 


_Whether the deployment's access configuration requires multi-factor authentication (SIG-ONTO-035): an observed ConfigurationState fact — asserted from evidence, never assumed._



<div data-search-exclude markdown="1">



URI: [sig:slot/mfa_required](https://ontology.sig-project.org/schema/slot/mfa_required)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ConfigurationState](../classes/ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Boolean](../types/Boolean.md) |
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
| self | sig:mfa_required |
| native | sig:mfa_required |




## LinkML Source

<details>
```yaml
name: mfa_required
description: 'Whether the deployment''s access configuration requires multi-factor
  authentication (SIG-ONTO-035): an observed ConfigurationState fact — asserted from
  evidence, never assumed.'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: ConfigurationState
domain_of:
- ConfigurationState
range: boolean

```
</details></div>