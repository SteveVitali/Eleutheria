---
search:
  boost: 2.0
---


# Enum: PredicateVolatility 




_Volatility class governing currency decay (§28.3, SIG-RECON-008)._



<div data-search-exclude markdown="1">

URI: [sig:PredicateVolatility](https://ontology.sig-project.org/schema/PredicateVolatility)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| IMMUTABLE | None | Never changes; half-life infinite; always C1 |
| GLACIAL | None |  |
| SLOW | None |  |
| MODERATE | None |  |
| FAST | None |  |
| VOLATILE | None |  |













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: PredicateVolatility
description: Volatility class governing currency decay (§28.3, SIG-RECON-008).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  IMMUTABLE:
    text: IMMUTABLE
    description: Never changes; half-life infinite; always C1.
  GLACIAL:
    text: GLACIAL
  SLOW:
    text: SLOW
  MODERATE:
    text: MODERATE
  FAST:
    text: FAST
  VOLATILE:
    text: VOLATILE

```
</details>

</div>