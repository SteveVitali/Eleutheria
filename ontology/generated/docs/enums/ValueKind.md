---
search:
  boost: 2.0
---


# Enum: ValueKind 




_RDF-style value kind — known value, unknown value, or no value (§9.5)._



<div data-search-exclude markdown="1">

URI: [sig:enum/ValueKind](https://ontology.sig-project.org/schema/enum/ValueKind)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| value | None |  |
| somevalue | None | A value exists but is unknown |
| novalue | None | There is provably no value |




## Slots

| Name | Description |
| ---  | --- |
| [value_kind](../slots/value_kind.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: ValueKind
description: RDF-style value kind — known value, unknown value, or no value (§9.5).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  value:
    text: value
  somevalue:
    text: somevalue
    description: A value exists but is unknown.
  novalue:
    text: novalue
    description: There is provably no value.

```
</details>

</div>