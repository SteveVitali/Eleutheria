---
search:
  boost: 5.0
---

# Slot: source_ref 

<div data-search-exclude markdown="1">



URI: [sig:slot/source_ref](https://ontology.sig-project.org/schema/slot/source_ref)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AssertionQuarantine](../classes/AssertionQuarantine.md) | The append-only fail-closed landing for a rejected assertion (SIG-TRUST-001):... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Source](../classes/Source.md) |
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
| self | sig:source_ref |
| native | sig:source_ref |




## LinkML Source

<details>
```yaml
name: source_ref
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AssertionQuarantine
domain_of:
- AssertionQuarantine
range: Source

```
</details></div>