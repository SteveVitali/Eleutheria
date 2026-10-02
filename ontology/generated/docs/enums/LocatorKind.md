---
search:
  boost: 2.0
---


# Enum: LocatorKind 




_The six addressable ways a claim's evidence link points into the captured bytes it was extracted from (§24.1, SIG-PARSE-003). Unknown kinds fail closed — never silently re-anchored to the whole document._



<div data-search-exclude markdown="1">

URI: [sig:enum/LocatorKind](https://ontology.sig-project.org/schema/enum/LocatorKind)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| page | None |  |
| bbox | None |  |
| cell | None |  |
| row | None |  |
| byte_range | None |  |
| dom_path | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [locator_kind](../slots/locator_kind.md) | The kind of the typed locator row (locator fields live in the physical jsonb ... |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: LocatorKind
description: The six addressable ways a claim's evidence link points into the captured
  bytes it was extracted from (§24.1, SIG-PARSE-003). Unknown kinds fail closed —
  never silently re-anchored to the whole document.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  page:
    text: page
  bbox:
    text: bbox
  cell:
    text: cell
  row:
    text: row
  byte_range:
    text: byte_range
  dom_path:
    text: dom_path

```
</details>

</div>