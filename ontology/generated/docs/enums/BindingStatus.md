---
search:
  boost: 2.0
---


# Enum: BindingStatus 




_How a claim↔capture evidence link was bound (SIG-TRUST-002). The honest classifications — a link is never presented as byte-anchored provenance it is not._



<div data-search-exclude markdown="1">

URI: [sig:enum/BindingStatus](https://ontology.sig-project.org/schema/enum/BindingStatus)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| actual_capture | None | Typed locator into the actual captured bytes consumed |
| replayed | None | A replay binding to the ORIGINAL capture occurrence |
| document_only | None | The explicit document-scoped limitation — no finer anchor exists |
| legacy_synthetic | None | The pre-P32 |




## Slots

| Name | Description |
| ---  | --- |
| [binding_status](../slots/binding_status.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: BindingStatus
description: How a claim↔capture evidence link was bound (SIG-TRUST-002). The honest
  classifications — a link is never presented as byte-anchored provenance it is not.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  actual_capture:
    text: actual_capture
    description: Typed locator into the actual captured bytes consumed.
  replayed:
    text: replayed
    description: A replay binding to the ORIGINAL capture occurrence.
  document_only:
    text: document_only
    description: The explicit document-scoped limitation — no finer anchor exists.
  legacy_synthetic:
    text: legacy_synthetic
    description: The pre-P32.2 per-run synthetic capture path; honest legacy.

```
</details>

</div>