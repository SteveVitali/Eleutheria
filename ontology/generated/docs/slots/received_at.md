---
search:
  boost: 5.0
---

# Slot: received_at 

<div data-search-exclude markdown="1">



URI: [sig:slot/received_at](https://ontology.sig-project.org/schema/slot/received_at)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AssertionQuarantine](../classes/AssertionQuarantine.md) | The append-only fail-closed landing for a rejected assertion (SIG-TRUST-001):... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Datetime](../types/Datetime.md) |
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
| self | sig:received_at |
| native | sig:received_at |




## LinkML Source

<details>
```yaml
name: received_at
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AssertionQuarantine
domain_of:
- AssertionQuarantine
range: datetime

```
</details></div>