---
search:
  boost: 10.0
---

# Class: Claim 


_An append-only assertion (subject, predicate, value, ...) — the substance of the graph (§10.3, L1). Physical append-only table is P02._



<div data-search-exclude markdown="1">



URI: [sig:class/Claim](https://ontology.sig-project.org/schema/class/Claim)





```mermaid
 classDiagram
    class Claim
    click Claim href "../../classes/Claim/"
      Entity <|-- Claim
        click Entity href "../../classes/Entity/"
      
      Claim : absence_kind
        
          
    
        
        
        Claim --> "0..1" AbsenceKind : absence_kind
        click AbsenceKind href "../../enums/AbsenceKind/"
    

        
      Claim : evidence_role
        
          
    
        
        
        Claim --> "0..1" EvidenceRole : evidence_role
        click EvidenceRole href "../../enums/EvidenceRole/"
    

        
      Claim : id
        
      Claim : predicate
        
      Claim : raw_value
        
      Claim : subject
        
      Claim : supersedes
        
          
    
        
        
        Claim --> "0..1" Claim : supersedes
        click Claim href "../../classes/Claim/"
    

        
      Claim : value
        
      Claim : value_kind
        
          
    
        
        
        Claim --> "0..1" ValueKind : value_kind
        click ValueKind href "../../enums/ValueKind/"
    

        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **Claim**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [subject](../slots/subject.md) | 0..1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | direct |
| [predicate](../slots/predicate.md) | 0..1 <br/> [PredicateCode](../types/PredicateCode.md) |  | direct |
| [value](../slots/value.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [value_kind](../slots/value_kind.md) | 0..1 <br/> [ValueKind](../enums/ValueKind.md) |  | direct |
| [raw_value](../slots/raw_value.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [absence_kind](../slots/absence_kind.md) | 0..1 <br/> [AbsenceKind](../enums/AbsenceKind.md) |  | direct |
| [evidence_role](../slots/evidence_role.md) | 0..1 <br/> [EvidenceRole](../enums/EvidenceRole.md) |  | direct |
| [supersedes](../slots/supersedes.md) | 0..1 <br/> [Claim](../classes/Claim.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Claim](../classes/Claim.md) | [supersedes](../slots/supersedes.md) | range | [Claim](../classes/Claim.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:Claim |
| native | sig:Claim |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Claim
description: An append-only assertion (subject, predicate, value, ...) — the substance
  of the graph (§10.3, L1). Physical append-only table is P02.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  subject:
    name: subject
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: uriorcurie
  predicate:
    name: predicate
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: predicate_code
  value:
    name: value
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    range: string
  value_kind:
    name: value_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    range: ValueKind
  raw_value:
    name: raw_value
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    range: string
  absence_kind:
    name: absence_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    - CoverageRecord
    range: AbsenceKind
  evidence_role:
    name: evidence_role
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    range: EvidenceRole
  supersedes:
    name: supersedes
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Claim
    range: Claim

```
</details>

### Induced

<details>
```yaml
name: Claim
description: An append-only assertion (subject, predicate, value, ...) — the substance
  of the graph (§10.3, L1). Physical append-only table is P02.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  subject:
    name: subject
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: uriorcurie
  predicate:
    name: predicate
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    - Resolution
    - Contradiction
    - CoverageRecord
    range: predicate_code
  value:
    name: value
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    range: string
  value_kind:
    name: value_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    range: ValueKind
  raw_value:
    name: raw_value
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    range: string
  absence_kind:
    name: absence_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    - CoverageRecord
    range: AbsenceKind
  evidence_role:
    name: evidence_role
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    range: EvidenceRole
  supersedes:
    name: supersedes
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Claim
    domain_of:
    - Claim
    range: Claim
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: Claim
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>