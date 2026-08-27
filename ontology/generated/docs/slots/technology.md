---
search:
  boost: 5.0
---

# Slot: technology 

<div data-search-exclude markdown="1">



URI: [sig:slot/technology](https://ontology.sig-project.org/schema/slot/technology)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Technology](../classes/Technology.md) | A three-level technology (domain→family→technology, §11 |  no  |
| [Deployment](../classes/Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [Technology](../classes/Technology.md), [Deployment](../classes/Deployment.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information






## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:technology |
| native | sig:technology |




## LinkML Source

<details>
```yaml
name: technology
domain_of:
- Technology
- Deployment
range: string

```
</details></div>