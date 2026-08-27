---
search:
  boost: 5.0
---

# Slot: source_org 

<div data-search-exclude markdown="1">



URI: [sig:source_org](https://ontology.sig-project.org/schema/source_org)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [UsageAggregate](UsageAggregate.md) | Aggregated usage; direction is the point (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Organization](Organization.md) |
| Domain Of | [UsageAggregate](UsageAggregate.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [UsageAggregate](UsageAggregate.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:source_org |
| native | sig:source_org |




## LinkML Source

<details>
```yaml
name: source_org
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: UsageAggregate
domain_of:
- UsageAggregate
range: Organization
required: true

```
</details></div>