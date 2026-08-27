---
search:
  boost: 10.0
---

# Class: RoleAssignment 


_Assigns one of the fourteen roles (§12.4, SIG-ONTO-047) from a party to an asset/deployment/system. Modelled separately so the seven load-bearing separations (SIG-ONTO-048) are each independently representable, and so §43.3 coordinate sensitivity can be evaluated at the ROLE level (host≠owner)._



<div data-search-exclude markdown="1">



URI: [sig:RoleAssignment](https://ontology.sig-project.org/schema/RoleAssignment)





```mermaid
 classDiagram
    class RoleAssignment
    click RoleAssignment href "../RoleAssignment/"
      Edge <|-- RoleAssignment
        click Edge href "../Edge/"
      
      RoleAssignment : asserted_by
        
      RoleAssignment : edge_type
        
          
    
        
        
        RoleAssignment --> "1" EdgeType : edge_type
        click EdgeType href "../EdgeType/"
    

        
      RoleAssignment : id
        
      RoleAssignment : observed_at
        
      RoleAssignment : over
        
      RoleAssignment : party
        
      RoleAssignment : role
        
          
    
        
        
        RoleAssignment --> "1" Role : role
        click Role href "../Role/"
    

        
      RoleAssignment : source
        
      RoleAssignment : sources
        
      RoleAssignment : target
        
      RoleAssignment : valid_from
        
      RoleAssignment : valid_from_kind
        
          
    
        
        
        RoleAssignment --> "0..1" TemporalBoundKind : valid_from_kind
        click TemporalBoundKind href "../TemporalBoundKind/"
    

        
      RoleAssignment : valid_to
        
      RoleAssignment : valid_to_kind
        
          
    
        
        
        RoleAssignment --> "0..1" TemporalBoundKind : valid_to_kind
        click TemporalBoundKind href "../TemporalBoundKind/"
    

        
      
```





## Inheritance
* [Edge](Edge.md)
    * **RoleAssignment**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [role](role.md) | 1 <br/> [Role](Role.md) |  | direct |
| [party](party.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | The Organization (or, rarely and reviewed, Person) holding the role | direct |
| [over](over.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | The PhysicalAsset / Deployment / DataSystem the role is held over | direct |
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
| self | sig:RoleAssignment |
| native | sig:RoleAssignment |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: RoleAssignment
description: Assigns one of the fourteen roles (§12.4, SIG-ONTO-047) from a party
  to an asset/deployment/system. Modelled separately so the seven load-bearing separations
  (SIG-ONTO-048) are each independently representable, and so §43.3 coordinate sensitivity
  can be evaluated at the ROLE level (host≠owner).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Edge
attributes:
  role:
    name: role
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - RoleAssignment
    range: Role
    required: true
  party:
    name: party
    description: The Organization (or, rarely and reviewed, Person) holding the role.
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - RoleAssignment
    range: uriorcurie
    required: true
  over:
    name: over
    description: The PhysicalAsset / Deployment / DataSystem the role is held over.
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - RoleAssignment
    range: uriorcurie
    required: true

```
</details>

### Induced

<details>
```yaml
name: RoleAssignment
description: Assigns one of the fourteen roles (§12.4, SIG-ONTO-047) from a party
  to an asset/deployment/system. Modelled separately so the seven load-bearing separations
  (SIG-ONTO-048) are each independently representable, and so §43.3 coordinate sensitivity
  can be evaluated at the ROLE level (host≠owner).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Edge
attributes:
  role:
    name: role
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: RoleAssignment
    domain_of:
    - RoleAssignment
    range: Role
    required: true
  party:
    name: party
    description: The Organization (or, rarely and reviewed, Person) holding the role.
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: RoleAssignment
    domain_of:
    - RoleAssignment
    range: uriorcurie
    required: true
  over:
    name: over
    description: The PhysicalAsset / Deployment / DataSystem the role is held over.
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    owner: RoleAssignment
    domain_of:
    - RoleAssignment
    range: uriorcurie
    required: true
  id:
    name: id
    from_schema: https://ontology.sig-project.org/schema/edges
    identifier: true
    owner: RoleAssignment
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
    owner: RoleAssignment
    domain_of:
    - Edge
    range: uriorcurie
    required: true
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
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
    owner: RoleAssignment
    domain_of:
    - Edge
    range: EdgeType
    required: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_from_kind:
    name: valid_from_kind
    description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
    domain_of:
    - Edge
    range: TemporalBoundKind
  valid_to_kind:
    name: valid_to_kind
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
    domain_of:
    - Edge
    range: TemporalBoundKind
  observed_at:
    name: observed_at
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
    domain_of:
    - Edge
    range: edtf
  sources:
    name: sources
    description: At least one supporting claim (§12.1.4, SIG-CHART-013).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: RoleAssignment
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
    owner: RoleAssignment
    domain_of:
    - Edge
    range: uriorcurie

```
</details></div>