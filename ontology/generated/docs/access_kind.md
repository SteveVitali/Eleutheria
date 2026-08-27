---
search:
  boost: 5.0
---

# Slot: access_kind 


_Configured vs observed vs declared — never defaulted into one another (SIG-ONTO-042)._



<div data-search-exclude markdown="1">



URI: [sig:access_kind](https://ontology.sig-project.org/schema/access_kind)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [AccessRelationship](AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [AccessKind](AccessKind.md) |
| Domain Of | [AccessRelationship](AccessRelationship.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [AccessRelationship](AccessRelationship.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:access_kind |
| native | sig:access_kind |




## LinkML Source

<details>
```yaml
name: access_kind
description: Configured vs observed vs declared — never defaulted into one another
  (SIG-ONTO-042).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: AccessRelationship
domain_of:
- AccessRelationship
range: AccessKind
required: true

```
</details></div>