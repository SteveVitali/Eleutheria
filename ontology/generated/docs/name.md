---
search:
  boost: 5.0
---

# Slot: name 

<div data-search-exclude markdown="1">



URI: [sig:name](https://ontology.sig-project.org/schema/name)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Jurisdiction](Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](String.md) |
| Domain Of | [Jurisdiction](Jurisdiction.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Jurisdiction](Jurisdiction.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:name |
| native | sig:name |




## LinkML Source

<details>
```yaml
name: name
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: Jurisdiction
domain_of:
- Jurisdiction
range: string
multivalued: true

```
</details></div>