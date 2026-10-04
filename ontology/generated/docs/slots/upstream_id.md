---
search:
  boost: 5.0
---

# Slot: upstream_id 


_Qualified by system (osm.node, osm.way, osm.relation, deflock.id, ...)._



<div data-search-exclude markdown="1">



URI: [sig:slot/upstream_id](https://ontology.sig-project.org/schema/slot/upstream_id)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [PhysicalAsset](../classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [PhysicalAsset](../classes/PhysicalAsset.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [PhysicalAsset](../classes/PhysicalAsset.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:upstream_id |
| native | sig:upstream_id |




## LinkML Source

<details>
```yaml
name: upstream_id
description: Qualified by system (osm.node, osm.way, osm.relation, deflock.id, ...).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: PhysicalAsset
domain_of:
- PhysicalAsset
range: string
multivalued: true

```
</details></div>