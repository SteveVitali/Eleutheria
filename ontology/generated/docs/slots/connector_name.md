---
search:
  boost: 5.0
---

# Slot: connector_name 

<div data-search-exclude markdown="1">



URI: [sig:slot/connector_name](https://ontology.sig-project.org/schema/slot/connector_name)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AssertionQuarantine](../classes/AssertionQuarantine.md) | The append-only fail-closed landing for a rejected assertion (SIG-TRUST-001):... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [AssertionQuarantine](../classes/AssertionQuarantine.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [AssertionQuarantine](../classes/AssertionQuarantine.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:connector_name |
| native | sig:connector_name |




## LinkML Source

<details>
```yaml
name: connector_name
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AssertionQuarantine
domain_of:
- AssertionQuarantine
range: string

```
</details></div>