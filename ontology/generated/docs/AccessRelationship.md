---
search:
  boost: 10.0
---

# Class: AccessRelationship 


_A sharing/access relationship; direction, scope, automaticity, and kind are all required — never reduced to `shares_with` (§12.5, SIG-ONTO-049). The three access kinds (§12.2) are never merged (SIG-ONTO-042)._



<div data-search-exclude markdown="1">



URI: [sig:AccessRelationship](https://ontology.sig-project.org/schema/AccessRelationship)





```mermaid
 classDiagram
    class AccessRelationship
    click AccessRelationship href "../AccessRelationship/"
      Edge <|-- AccessRelationship
        click Edge href "../Edge/"
      
      AccessRelationship : access_kind
        
          
    
        
        
        AccessRelationship --> "1" AccessKind : access_kind
        click AccessKind href "../AccessKind/"
    

        
      AccessRelationship : asserted_by
        
      AccessRelationship : automaticity
        
          
    
        
        
        AccessRelationship --> "0..1" Automaticity : automaticity
        click Automaticity href "../Automaticity/"
    

        
      AccessRelationship : direction
        
          
    
        
        
        AccessRelationship --> "1" Direction : direction
        click Direction href "../Direction/"
    

        
      AccessRelationship : edge_type
        
          
    
        
        
        AccessRelationship --> "1" EdgeType : edge_type
        click EdgeType href "../EdgeType/"
    

        
      AccessRelationship : id
        
      AccessRelationship : observed_at
        
      AccessRelationship : scope
        
          
    
        
        
        AccessRelationship --> "1" CapabilityScope : scope
        click CapabilityScope href "../CapabilityScope/"
    

        
      AccessRelationship : source
        
      AccessRelationship : sources
        
      AccessRelationship : target
        
      AccessRelationship : valid_from
        
      AccessRelationship : valid_from_kind
        
          
    
        
        
        AccessRelationship --> "0..1" TemporalBoundKind : valid_from_kind
        click TemporalBoundKind href "../TemporalBoundKind/"
    

        
      AccessRelationship : valid_to
        
      AccessRelationship : valid_to_kind
        
          
    
        
        
        AccessRelationship --> "0..1" TemporalBoundKind : valid_to_kind
        click TemporalBoundKind href "../TemporalBoundKind/"
    

        
      
```





## Inheritance
* [Edge](Edge.md)
    * **AccessRelationship**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [scope](scope.md) | 1 <br/> [CapabilityScope](CapabilityScope.md) |  | direct |
| [direction](direction.md) | 1 <br/> [Direction](Direction.md) | Required; never symmetric by default (SIG-ONTO-049) | direct |
| [automaticity](automaticity.md) | 0..1 <br/> [Automaticity](Automaticity.md) |  | direct |
| [access_kind](access_kind.md) | 1 <br/> [AccessKind](AccessKind.md) | Configured vs observed vs declared — never defaulted into one another (SIG-ON... | direct |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) |  | [Edge](Edge.md) |
| [source](source.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | The asserting/originating node (directed — §12 | [Edge](Edge.md) |
| [target](target.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) |  | [Edge](Edge.md) |
| [edge_type](edge_type.md) | 1 <br/> [EdgeType](EdgeType.md) | Typed from the closed catalog (§12 | [Edge](Edge.md) |
| [valid_from](valid_from.md) | 0..1 <br/> [Edtf](Edtf.md) |  | [Edge](Edge.md) |
| [valid_to](valid_to.md) | 0..1 <br/> [Edtf](Edtf.md) |  | [Edge](Edge.md) |
| [valid_from_kind](valid_from_kind.md) | 0..1 <br/> [TemporalBoundKind](TemporalBoundKind.md) | Snapshot sharing carries unknown/ongoing (SIG-ONTO-044) | [Edge](Edge.md) |
| [valid_to_kind](valid_to_kind.md) | 0..1 <br/> [TemporalBoundKind](TemporalBoundKind.md) |  | [Edge](Edge.md) |
| [observed_at](observed_at.md) | 0..1 <br/> [Edtf](Edtf.md) |  | [Edge](Edge.md) |
| [sources](sources.md) | * <br/> [Uriorcurie](Uriorcurie.md) | At least one supporting claim (§12 | [Edge](Edge.md) |
| [asserted_by](asserted_by.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | Which party asserted it — perspectival (§12 | [Edge](Edge.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:AccessRelationship |
| native | sig:AccessRelationship |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: AccessRelationship
description: A sharing/access relationship; direction, scope, automaticity, and kind
  are all required — never reduced to `shares_with` (§12.5, SIG-ONTO-049). The three
  access kinds (§12.2) are never merged (SIG-ONTO-042).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Edge
attributes:
  scope:
    name: scope
    from_schema: https://ontology.sig-project.org/schema/edges
    domain_of:
    - Capability
    - AccessRelationship
    - IntegrationEdge
    range: CapabilityScope
    required: true
  direction:
    name: direction
    description: Required; never symmetric by default (SIG-ONTO-049).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - AccessRelationship
    range: Direction
    required: true
  automaticity:
    name: automaticity
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - AccessRelationship
    range: Automaticity
  access_kind:
    name: access_kind
    description: Configured vs observed vs declared — never defaulted into one another
      (SIG-ONTO-042).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - AccessRelationship
    range: AccessKind
    required: true

```
</details>

### Induced

<details>
```yaml
name: AccessRelationship
description: A sharing/access relationship; direction, scope, automaticity, and kind
  are all required — never reduced to `shares_with` (§12.5, SIG-ONTO-049). The three
  access kinds (§12.2) are never merged (SIG-ONTO-042).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Edge
attributes:
  scope:
    name: scope
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - Capability
    - AccessRelationship
    - IntegrationEdge
    range: CapabilityScope
    required: true
  direction:
    name: direction
    description: Required; never symmetric by default (SIG-ONTO-049).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: AccessRelationship
    domain_of:
    - AccessRelationship
    range: Direction
    required: true
  automaticity:
    name: automaticity
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: AccessRelationship
    domain_of:
    - AccessRelationship
    range: Automaticity
  access_kind:
    name: access_kind
    description: Configured vs observed vs declared — never defaulted into one another
      (SIG-ONTO-042).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: AccessRelationship
    domain_of:
    - AccessRelationship
    range: AccessKind
    required: true
  id:
    name: id
    from_schema: https://ontology.sig-project.org/schema/edges
    identifier: true
    owner: AccessRelationship
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true
  source:
    name: source
    description: The asserting/originating node (directed — §12.1.1).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: AccessRelationship
    domain_of:
    - Edge
    range: uriorcurie
    required: true
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - ResearchTask
    - Edge
    range: uriorcurie
    required: true
  edge_type:
    name: edge_type
    description: Typed from the closed catalog (§12.1.2).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: AccessRelationship
    domain_of:
    - Edge
    range: EdgeType
    required: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_from_kind:
    name: valid_from_kind
    description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - Edge
    range: TemporalBoundKind
  valid_to_kind:
    name: valid_to_kind
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - Edge
    range: TemporalBoundKind
  observed_at:
    name: observed_at
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - Edge
    range: edtf
  sources:
    name: sources
    description: At least one supporting claim (§12.1.4, SIG-CHART-013).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: AccessRelationship
    domain_of:
    - AccountabilityEvent
    - Edge
    range: uriorcurie
    multivalued: true
  asserted_by:
    name: asserted_by
    description: Which party asserted it — perspectival (§12.1.5).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: AccessRelationship
    domain_of:
    - Edge
    range: uriorcurie

```
</details></div>