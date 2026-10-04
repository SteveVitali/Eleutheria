---
search:
  boost: 10.0
---

# Class: CoverageRecord 


_[NEW] Makes negative claims queryable (§11.23, §32.2)._



<div data-search-exclude markdown="1">



URI: [sig:class/CoverageRecord](https://ontology.sig-project.org/schema/class/CoverageRecord)





```mermaid
 classDiagram
    class CoverageRecord
    click CoverageRecord href "../../classes/CoverageRecord/"
      Entity <|-- CoverageRecord
        click Entity href "../../classes/Entity/"
      
      CoverageRecord : absence_kind
        
          
    
        
        
        CoverageRecord --> "0..1" AbsenceKind : absence_kind
        click AbsenceKind href "../../enums/AbsenceKind/"
    

        
      CoverageRecord : coverage_period
        
      CoverageRecord : denominator_published
        
      CoverageRecord : id
        
      CoverageRecord : predicate
        
      CoverageRecord : subject
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **CoverageRecord**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [subject](../slots/subject.md) | 0..1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | direct |
| [predicate](../slots/predicate.md) | 0..1 <br/> [PredicateCode](../types/PredicateCode.md) |  | direct |
| [absence_kind](../slots/absence_kind.md) | 0..1 <br/> [AbsenceKind](../enums/AbsenceKind.md) |  | direct |
| [coverage_period](../slots/coverage_period.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [denominator_published](../slots/denominator_published.md) | 0..1 <br/> [Boolean](../types/Boolean.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:CoverageRecord |
| native | sig:CoverageRecord |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: CoverageRecord
description: '[NEW] Makes negative claims queryable (§11.23, §32.2).'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  subject:
    name: subject
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: uriorcurie
  predicate:
    name: predicate
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: predicate_code
  absence_kind:
    name: absence_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Claim
    - CoverageRecord
    range: AbsenceKind
  coverage_period:
    name: coverage_period
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - UsageAggregate
    - CoverageRecord
    range: string
  denominator_published:
    name: denominator_published
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - CoverageRecord
    range: boolean

```
</details>

### Induced

<details>
```yaml
name: CoverageRecord
description: '[NEW] Makes negative claims queryable (§11.23, §32.2).'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  subject:
    name: subject
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: CoverageRecord
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: uriorcurie
  predicate:
    name: predicate
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: CoverageRecord
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: predicate_code
  absence_kind:
    name: absence_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: CoverageRecord
    domain_of:
    - Claim
    - CoverageRecord
    range: AbsenceKind
  coverage_period:
    name: coverage_period
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: CoverageRecord
    domain_of:
    - UsageAggregate
    - CoverageRecord
    range: string
  denominator_published:
    name: denominator_published
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: CoverageRecord
    domain_of:
    - CoverageRecord
    range: boolean
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: CoverageRecord
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>