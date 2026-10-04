---
search:
  boost: 5.0
---

# Slot: domain 


_The domain-level slug this rolls up to._



<div data-search-exclude markdown="1">



URI: [sig:slot/domain](https://ontology.sig-project.org/schema/slot/domain)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Technology](../classes/Technology.md) | A three-level technology (domain→family→technology, §11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [TechnologyCode](../types/TechnologyCode.md) |
| Domain Of | [Technology](../classes/Technology.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Technology](../classes/Technology.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:domain |
| native | sig:domain |




## LinkML Source

<details>
```yaml
name: domain
description: The domain-level slug this rolls up to.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Technology
domain_of:
- Technology
range: technology_code

```
</details></div>