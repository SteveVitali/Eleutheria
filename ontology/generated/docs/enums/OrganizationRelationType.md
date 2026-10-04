---
search:
  boost: 2.0
---


# Enum: OrganizationRelationType 




_The seven-value vocabulary of the reified, bitemporal OrganizationRelation (§14.5, SIG-IDENT-016). Organizational change is modelled as first-class relation records carrying valid + transaction time, never as a mutable column. A pure rename is deliberately NOT here: renaming produces a new version and a dated alias, never a succession relation (SIG-IDENT-017)._



<div data-search-exclude markdown="1">

URI: [sig:enum/OrganizationRelationType](https://ontology.sig-project.org/schema/enum/OrganizationRelationType)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| same_as | None | The two records denote the same real-world organization |
| succeeded_by | None | A organization was succeeded by B (temporal substitution) |
| merged_into | None | A was merged into B (A ceases; B continues/created) |
| split_into | None | A split into B (and usually others) |
| absorbed | None | A was absorbed by B (e |
| parent_of | None | A is the parent body of B (a municipality is parent_of its police department,... |
| acquired | None | A acquired B (e |













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: OrganizationRelationType
description: 'The seven-value vocabulary of the reified, bitemporal OrganizationRelation
  (§14.5, SIG-IDENT-016). Organizational change is modelled as first-class relation
  records carrying valid + transaction time, never as a mutable column. A pure rename
  is deliberately NOT here: renaming produces a new version and a dated alias, never
  a succession relation (SIG-IDENT-017).'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  same_as:
    text: same_as
    description: The two records denote the same real-world organization.
  succeeded_by:
    text: succeeded_by
    description: A organization was succeeded by B (temporal substitution).
  merged_into:
    text: merged_into
    description: A was merged into B (A ceases; B continues/created).
  split_into:
    text: split_into
    description: A split into B (and usually others).
  absorbed:
    text: absorbed
    description: A was absorbed by B (e.g. a disbanded PD taken over by a county sheriff).
  parent_of:
    text: parent_of
    description: A is the parent body of B (a municipality is parent_of its police
      department, SIG-IDENT-009).
  acquired:
    text: acquired
    description: A acquired B (e.g. a vendor acquisition transferring product ownership).

```
</details>

</div>