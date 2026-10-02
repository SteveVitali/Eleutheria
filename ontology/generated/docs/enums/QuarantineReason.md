---
search:
  boost: 2.0
---


# Enum: QuarantineReason 




_Why an assertion failed closed into assertion_quarantine (SIG-TRUST-001). Distinct reasons keep extractor failure separate from an unsupported locator and an unknown type separate from a missing binding._



<div data-search-exclude markdown="1">

URI: [sig:enum/QuarantineReason](https://ontology.sig-project.org/schema/enum/QuarantineReason)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| bad_digest | None |  |
| unknown_predicate | None |  |
| unknown_object_type | None |  |
| unknown_value_kind | None |  |
| missing_capture_binding | None |  |
| unsupported_locator | None |  |
| extractor_failure | None |  |
| version_mismatch | None | The binding's OCFL version disagrees with the stored occurrence |
| missing_required_field | None |  |
| unknown_qualifier | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [reason](../slots/reason.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: QuarantineReason
description: Why an assertion failed closed into assertion_quarantine (SIG-TRUST-001).
  Distinct reasons keep extractor failure separate from an unsupported locator and
  an unknown type separate from a missing binding.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  bad_digest:
    text: bad_digest
  unknown_predicate:
    text: unknown_predicate
  unknown_object_type:
    text: unknown_object_type
  unknown_value_kind:
    text: unknown_value_kind
  missing_capture_binding:
    text: missing_capture_binding
  unsupported_locator:
    text: unsupported_locator
  extractor_failure:
    text: extractor_failure
  version_mismatch:
    text: version_mismatch
    description: The binding's OCFL version disagrees with the stored occurrence.
  missing_required_field:
    text: missing_required_field
  unknown_qualifier:
    text: unknown_qualifier

```
</details>

</div>