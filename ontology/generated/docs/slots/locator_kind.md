---
search:
  boost: 5.0
---

# Slot: locator_kind 


_The kind of the typed locator row (locator fields live in the physical jsonb row)._



<div data-search-exclude markdown="1">



URI: [sig:slot/locator_kind](https://ontology.sig-project.org/schema/slot/locator_kind)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ClaimEvidence](../classes/ClaimEvidence.md) | One claim↔capture evidence link (§16 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [LocatorKind](../enums/LocatorKind.md) |
| Domain Of | [ClaimEvidence](../classes/ClaimEvidence.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ClaimEvidence](../classes/ClaimEvidence.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:locator_kind |
| native | sig:locator_kind |




## LinkML Source

<details>
```yaml
name: locator_kind
description: The kind of the typed locator row (locator fields live in the physical
  jsonb row).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: ClaimEvidence
domain_of:
- ClaimEvidence
range: LocatorKind

```
</details></div>