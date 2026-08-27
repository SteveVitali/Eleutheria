---
search:
  boost: 5.0
---

# Slot: subscribed_hotlist_topic 

<div data-search-exclude markdown="1">



URI: [sig:slot/subscribed_hotlist_topic](https://ontology.sig-project.org/schema/slot/subscribed_hotlist_topic)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ConfigurationState](../classes/ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [String](../types/String.md) |
| Domain Of | [ConfigurationState](../classes/ConfigurationState.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ConfigurationState](../classes/ConfigurationState.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:subscribed_hotlist_topic |
| native | sig:subscribed_hotlist_topic |




## LinkML Source

<details>
```yaml
name: subscribed_hotlist_topic
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
owner: ConfigurationState
domain_of:
- ConfigurationState
range: string
multivalued: true

```
</details></div>