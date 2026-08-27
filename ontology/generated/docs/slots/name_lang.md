---
search:
  boost: 5.0
---

# Slot: name_lang 

<div data-search-exclude markdown="1">



URI: [sig:slot/name_lang](https://ontology.sig-project.org/schema/slot/name_lang)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Jurisdiction](../classes/Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |
| [Organization](../classes/Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Jurisdiction](../classes/Jurisdiction.md), [Organization](../classes/Organization.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:name_lang |
| native | sig:name_lang |




## LinkML Source

<details>
```yaml
name: name_lang
domain_of:
- Jurisdiction
- Organization
range: string

```
</details></div>