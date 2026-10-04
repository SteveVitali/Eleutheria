---
search:
  boost: 10.0
---

# Class: UsageAggregate 


_Aggregated usage; direction is the point (§11.16). NO per-search, per-plate, or per-person row may exist here or anywhere in SIG (SIG-ONTO-037, §18.1)._



<div data-search-exclude markdown="1">



URI: [sig:class/UsageAggregate](https://ontology.sig-project.org/schema/class/UsageAggregate)





```mermaid
 classDiagram
    class UsageAggregate
    click UsageAggregate href "../../classes/UsageAggregate/"
      Entity <|-- UsageAggregate
        click Entity href "../../classes/Entity/"
      
      UsageAggregate : audit_source_type
        
          
    
        
        
        UsageAggregate --> "0..1" AuditSourceType : audit_source_type
        click AuditSourceType href "../../enums/AuditSourceType/"
    

        
      UsageAggregate : count
        
      UsageAggregate : coverage_period
        
      UsageAggregate : id
        
      UsageAggregate : period
        
      UsageAggregate : reason_category
        
      UsageAggregate : reason_raw_value
        
      UsageAggregate : search_scope
        
          
    
        
        
        UsageAggregate --> "0..1" CapabilityScope : search_scope
        click CapabilityScope href "../../enums/CapabilityScope/"
    

        
      UsageAggregate : searching_org
        
          
    
        
        
        UsageAggregate --> "1" Organization : searching_org
        click Organization href "../../classes/Organization/"
    

        
      UsageAggregate : source_org
        
          
    
        
        
        UsageAggregate --> "1" Organization : source_org
        click Organization href "../../classes/Organization/"
    

        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **UsageAggregate**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [searching_org](../slots/searching_org.md) | 1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [source_org](../slots/source_org.md) | 1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [period](../slots/period.md) | 0..1 <br/> [String](../types/String.md) | Minimum granularity one month for published data (§18 | direct |
| [count](../slots/count.md) | 0..1 <br/> [Integer](../types/Integer.md) | Subject to small-cell suppression (§18 | direct |
| [search_scope](../slots/search_scope.md) | 0..1 <br/> [CapabilityScope](../enums/CapabilityScope.md) |  | direct |
| [reason_category](../slots/reason_category.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [reason_raw_value](../slots/reason_raw_value.md) | 0..1 <br/> [String](../types/String.md) | Normalized reason_category retains the raw value (P2) | direct |
| [audit_source_type](../slots/audit_source_type.md) | 0..1 <br/> [AuditSourceType](../enums/AuditSourceType.md) |  | direct |
| [coverage_period](../slots/coverage_period.md) | 0..1 <br/> [String](../types/String.md) | What span the underlying audit covered — distinct from period | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:UsageAggregate |
| native | sig:UsageAggregate |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: UsageAggregate
description: Aggregated usage; direction is the point (§11.16). NO per-search, per-plate,
  or per-person row may exist here or anywhere in SIG (SIG-ONTO-037, §18.1).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  searching_org:
    name: searching_org
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: Organization
    required: true
  source_org:
    name: source_org
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: Organization
    required: true
  period:
    name: period
    description: Minimum granularity one month for published data (§18.4).
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - FundingInstrument
    - UsageAggregate
    range: string
  count:
    name: count
    description: Subject to small-cell suppression (§18.4).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: integer
  search_scope:
    name: search_scope
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: CapabilityScope
  reason_category:
    name: reason_category
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: string
  reason_raw_value:
    name: reason_raw_value
    description: Normalized reason_category retains the raw value (P2).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: string
  audit_source_type:
    name: audit_source_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    range: AuditSourceType
  coverage_period:
    name: coverage_period
    description: What span the underlying audit covered — distinct from period.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - UsageAggregate
    - CoverageRecord
    range: string

```
</details>

### Induced

<details>
```yaml
name: UsageAggregate
description: Aggregated usage; direction is the point (§11.16). NO per-search, per-plate,
  or per-person row may exist here or anywhere in SIG (SIG-ONTO-037, §18.1).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  searching_org:
    name: searching_org
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: Organization
    required: true
  source_org:
    name: source_org
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: Organization
    required: true
  period:
    name: period
    description: Minimum granularity one month for published data (§18.4).
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: UsageAggregate
    domain_of:
    - FundingInstrument
    - UsageAggregate
    range: string
  count:
    name: count
    description: Subject to small-cell suppression (§18.4).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: integer
  search_scope:
    name: search_scope
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: CapabilityScope
  reason_category:
    name: reason_category
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: string
  reason_raw_value:
    name: reason_raw_value
    description: Normalized reason_category retains the raw value (P2).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: string
  audit_source_type:
    name: audit_source_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    range: AuditSourceType
  coverage_period:
    name: coverage_period
    description: What span the underlying audit covered — distinct from period.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: UsageAggregate
    domain_of:
    - UsageAggregate
    - CoverageRecord
    range: string
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: UsageAggregate
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>