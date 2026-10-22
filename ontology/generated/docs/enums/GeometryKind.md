---
search:
  boost: 2.0
---


# Enum: GeometryKind 




_The geometry shape kind a record declares for its subject (§19, SIG-GEO-003): the asset model MUST NOT assume a point. A record whose publisher's geometry is a zone or programme area declares `area` — automated-traffic-enforcement zones and published camera programme areas are areas, never device points — and a route-shaped record declares `line`. The `geometry_kind` predicate (ontology/vocab/predicates.yaml) carries this vocabulary's member on the claim surface; an area-shaped record MUST NOT be flattened to a device point._



<div data-search-exclude markdown="1">

URI: [sig:enum/GeometryKind](https://ontology.surveillancegraph.org/schema/enum/GeometryKind)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| point | None | A point geometry — one coordinate site (a device point) |
| line | None | A linear geometry — an enforced route or corridor segment |
| area | None | An area geometry — a zone or programme area (e |













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.surveillancegraph.org/schema/sig






## LinkML Source

<details>
```yaml
name: GeometryKind
description: 'The geometry shape kind a record declares for its subject (§19, SIG-GEO-003):
  the asset model MUST NOT assume a point. A record whose publisher''s geometry is
  a zone or programme area declares `area` — automated-traffic-enforcement zones and
  published camera programme areas are areas, never device points — and a route-shaped
  record declares `line`. The `geometry_kind` predicate (ontology/vocab/predicates.yaml)
  carries this vocabulary''s member on the claim surface; an area-shaped record MUST
  NOT be flattened to a device point.'
from_schema: https://ontology.surveillancegraph.org/schema/sig
rank: 1000
permissible_values:
  point:
    text: point
    description: A point geometry — one coordinate site (a device point).
  line:
    text: line
    description: A linear geometry — an enforced route or corridor segment.
  area:
    text: area
    description: An area geometry — a zone or programme area (e.g. an ATE zone or
      a published camera coverage polygon); never a device point (SIG-GEO-003).

```
</details>

</div>