---
search:
  boost: 2.0
---


# Enum: AccessKind 




_The three edge types that MUST NEVER be merged (§12.2)._



<div data-search-exclude markdown="1">

URI: [sig:enum/AccessKind](https://ontology.sig-project.org/schema/enum/AccessKind)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| configured_access | None | The system is set up to permit it |
| observed_use | None | Someone actually did it |
| declared_policy | None | Someone said it is permitted or forbidden |




## Slots

| Name | Description |
| ---  | --- |
| [access_kind](../slots/access_kind.md) | Configured vs observed vs declared — never defaulted into one another (SIG-ON... |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: AccessKind
description: The three edge types that MUST NEVER be merged (§12.2).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  configured_access:
    text: configured_access
    description: The system is set up to permit it.
  observed_use:
    text: observed_use
    description: Someone actually did it.
  declared_policy:
    text: declared_policy
    description: Someone said it is permitted or forbidden.

```
</details>

</div>