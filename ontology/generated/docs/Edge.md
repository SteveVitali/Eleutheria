---
search:
  boost: 10.0
---

# Class: Edge 


_Universal edge requirements (§12.1): directed, typed, time-bounded, evidenced, and perspectival._



<div data-search-exclude markdown="1">


* __NOTE__: this is an abstract class and should not be instantiated directly


URI: [sig:Edge](https://ontology.sig-project.org/schema/Edge)





```mermaid
 classDiagram
    class Edge
    click Edge href "../Edge/"
      Edge <|-- AccessRelationship
        click AccessRelationship href "../AccessRelationship/"
      Edge <|-- IntegrationEdge
        click IntegrationEdge href "../IntegrationEdge/"
      Edge <|-- RoleAssignment
        click RoleAssignment href "../RoleAssignment/"
      Edge <|-- StructuralEdge
        click StructuralEdge href "../StructuralEdge/"
      Edge <|-- ProvenanceEdge
        click ProvenanceEdge href "../ProvenanceEdge/"
      
      Edge : asserted_by
        
      Edge : edge_type
        
          
    
        
        
        Edge --> "1" EdgeType : edge_type
        click EdgeType href "../EdgeType/"
    

        
      Edge : id
        
      Edge : observed_at
        
      Edge : source
        
      Edge : sources
        
      Edge : target
        
      Edge : valid_from
        
      Edge : valid_from_kind
        
          
    
        
        
        Edge --> "0..1" TemporalBoundKind : valid_from_kind
        click TemporalBoundKind href "../TemporalBoundKind/"
    

        
      Edge : valid_to
        
      Edge : valid_to_kind
        
          
    
        
        
        Edge --> "0..1" TemporalBoundKind : valid_to_kind
        click TemporalBoundKind href "../TemporalBoundKind/"
    

        
      
```





## Inheritance
* **Edge**
    * [AccessRelationship](AccessRelationship.md)
    * [IntegrationEdge](IntegrationEdge.md)
    * [RoleAssignment](RoleAssignment.md)
    * [StructuralEdge](StructuralEdge.md)
    * [ProvenanceEdge](ProvenanceEdge.md)


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) |  | direct |
| [source](source.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | The asserting/originating node (directed — §12 | direct |
| [target](target.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) |  | direct |
| [edge_type](edge_type.md) | 1 <br/> [EdgeType](EdgeType.md) | Typed from the closed catalog (§12 | direct |
| [valid_from](valid_from.md) | 0..1 <br/> [Edtf](Edtf.md) |  | direct |
| [valid_to](valid_to.md) | 0..1 <br/> [Edtf](Edtf.md) |  | direct |
| [valid_from_kind](valid_from_kind.md) | 0..1 <br/> [TemporalBoundKind](TemporalBoundKind.md) | Snapshot sharing carries unknown/ongoing (SIG-ONTO-044) | direct |
| [valid_to_kind](valid_to_kind.md) | 0..1 <br/> [TemporalBoundKind](TemporalBoundKind.md) |  | direct |
| [observed_at](observed_at.md) | 0..1 <br/> [Edtf](Edtf.md) |  | direct |
| [sources](sources.md) | * <br/> [Uriorcurie](Uriorcurie.md) | At least one supporting claim (§12 | direct |
| [asserted_by](asserted_by.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) | Which party asserted it — perspectival (§12 | direct |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:Edge |
| native | sig:Edge |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Edge
description: 'Universal edge requirements (§12.1): directed, typed, time-bounded,
  evidenced, and perspectival.'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
abstract: true
attributes:
  id:
    name: id
    from_schema: https://ontology.sig-project.org/schema/edges
    identifier: true
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
  source:
    name: source
    description: The asserting/originating node (directed — §12.1.1).
    from_schema: https://ontology.sig-project.org/schema/edges
    rank: 1000
    domain_of:
    - Edge
    range: uriorcurie
    required: true
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/edges
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
    domain_of:
    - Edge
    range: EdgeType
    required: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/edges
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/edges
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_from_kind:
    name: valid_from_kind
    description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
    from_schema: https://ontology.sig-project.org/schema/edges
    domain_of:
    - Edge
    range: TemporalBoundKind
  valid_to_kind:
    name: valid_to_kind
    from_schema: https://ontology.sig-project.org/schema/edges
    domain_of:
    - Edge
    range: TemporalBoundKind
  observed_at:
    name: observed_at
    from_schema: https://ontology.sig-project.org/schema/edges
    domain_of:
    - Edge
    range: edtf
  sources:
    name: sources
    description: At least one supporting claim (§12.1.4, SIG-CHART-013).
    from_schema: https://ontology.sig-project.org/schema/edges
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
    domain_of:
    - Edge
    range: uriorcurie

```
</details>

### Induced

<details>
```yaml
name: Edge
description: 'Universal edge requirements (§12.1): directed, typed, time-bounded,
  evidenced, and perspectival.'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
abstract: true
attributes:
  id:
    name: id
    from_schema: https://ontology.sig-project.org/schema/edges
    identifier: true
    owner: Edge
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
    owner: Edge
    domain_of:
    - Edge
    range: uriorcurie
    required: true
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
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
    owner: Edge
    domain_of:
    - Edge
    range: EdgeType
    required: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_from_kind:
    name: valid_from_kind
    description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
    domain_of:
    - Edge
    range: TemporalBoundKind
  valid_to_kind:
    name: valid_to_kind
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
    domain_of:
    - Edge
    range: TemporalBoundKind
  observed_at:
    name: observed_at
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
    domain_of:
    - Edge
    range: edtf
  sources:
    name: sources
    description: At least one supporting claim (§12.1.4, SIG-CHART-013).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: Edge
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
    owner: Edge
    domain_of:
    - Edge
    range: uriorcurie

```
</details></div>