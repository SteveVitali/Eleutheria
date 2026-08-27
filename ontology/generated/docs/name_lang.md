---
search:
  boost: 5.0
---

# Slot: name_lang 

<div data-search-exclude markdown="1">



URI: [sig:name_lang](https://ontology.sig-project.org/schema/name_lang)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Jurisdiction](Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |
| [Organization](Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](String.md) |
| Domain Of | [Jurisdiction](Jurisdiction.md), [Organization](Organization.md) |

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