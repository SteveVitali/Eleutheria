---
search:
  boost: 2.0
---


# Enum: Role 




_The fourteen separately-modelled roles (§12.4). Never collapsed to owner/operator._



<div data-search-exclude markdown="1">

URI: [sig:enum/Role](https://ontology.sig-project.org/schema/enum/Role)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| owner | None | Who could lawfully remove it? |
| purchaser | None | Whose money bought it? |
| funder | None | Whose grant/appropriation supplied that money? |
| installer | None | Who physically mounted it? |
| host | None | Whose pole/wall/right-of-way is it on? |
| operator | None | Who aims, tunes, and responds to it? |
| data_controller | None | Who can change the retention setting? |
| data_processor | None | Could they lawfully use it for their own purposes? |
| platform_provider | None | Who would the capability disappear with? |
| accessor_read | None | Can they view without initiating a search? |
| searcher | None | Can they execute queries against the corpus? |
| alert_recipient | None | Do they get notified? |
| auditor | None | Can they see the search log as of right? |
| regulator | None | Can they prohibit it? |




## Slots

| Name | Description |
| ---  | --- |
| [role](../slots/role.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: Role
description: The fourteen separately-modelled roles (§12.4). Never collapsed to owner/operator.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  owner:
    text: owner
    description: Who could lawfully remove it?
  purchaser:
    text: purchaser
    description: Whose money bought it?
  funder:
    text: funder
    description: Whose grant/appropriation supplied that money?
  installer:
    text: installer
    description: Who physically mounted it?
  host:
    text: host
    description: Whose pole/wall/right-of-way is it on?
  operator:
    text: operator
    description: Who aims, tunes, and responds to it?
  data_controller:
    text: data_controller
    description: Who can change the retention setting?
  data_processor:
    text: data_processor
    description: Could they lawfully use it for their own purposes?
  platform_provider:
    text: platform_provider
    description: Who would the capability disappear with?
  accessor_read:
    text: accessor_read
    description: Can they view without initiating a search?
  searcher:
    text: searcher
    description: Can they execute queries against the corpus?
  alert_recipient:
    text: alert_recipient
    description: Do they get notified?
  auditor:
    text: auditor
    description: Can they see the search log as of right?
  regulator:
    text: regulator
    description: Can they prohibit it?

```
</details>

</div>