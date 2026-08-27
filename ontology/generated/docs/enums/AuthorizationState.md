---
search:
  boost: 2.0
---


# Enum: AuthorizationState 




_Track 4 — authorization (§13.4)._



<div data-search-exclude markdown="1">

URI: [sig:enum/AuthorizationState](https://ontology.sig-project.org/schema/enum/AuthorizationState)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| unknown | None |  |
| unauthorized | None |  |
| approval_pending | None |  |
| authorized | None |  |
| authorized_expired | None |  |
| moratorium | None |  |
| sunset_by_ordinance | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [authorization_state](../slots/authorization_state.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: AuthorizationState
description: Track 4 — authorization (§13.4).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  unknown:
    text: unknown
  unauthorized:
    text: unauthorized
  approval_pending:
    text: approval_pending
  authorized:
    text: authorized
  authorized_expired:
    text: authorized_expired
  moratorium:
    text: moratorium
  sunset_by_ordinance:
    text: sunset_by_ordinance

```
</details>

</div>