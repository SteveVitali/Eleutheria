---
search:
  boost: 10.0
---

# Class: ProvenanceEdge 


_Provenance relationships among claims, captures, artifacts, and sources (§12.7)._



<div data-search-exclude markdown="1">



URI: [sig:class/ProvenanceEdge](https://ontology.sig-project.org/schema/class/ProvenanceEdge)





```mermaid
 classDiagram
    class ProvenanceEdge
    click ProvenanceEdge href "../../classes/ProvenanceEdge/"
      Edge <|-- ProvenanceEdge
        click Edge href "../../classes/Edge/"
      
      ProvenanceEdge : asserted_by
        
      ProvenanceEdge : edge_type
        
          
    
        
        
        ProvenanceEdge --> "1" EdgeType : edge_type
        click EdgeType href "../../enums/EdgeType/"
    

        
      ProvenanceEdge : id
        
      ProvenanceEdge : observed_at
        
      ProvenanceEdge : source
        
      ProvenanceEdge : sources
        
      ProvenanceEdge : target
        
      ProvenanceEdge : valid_from
        
      ProvenanceEdge : valid_from_kind
        
          
    
        
        
        ProvenanceEdge --> "0..1" TemporalBoundKind : valid_from_kind
        click TemporalBoundKind href "../../enums/TemporalBoundKind/"
    

        
      ProvenanceEdge : valid_to
        
      ProvenanceEdge : valid_to_kind
        
          
    
        
        
        ProvenanceEdge --> "0..1" TemporalBoundKind : valid_to_kind
        click TemporalBoundKind href "../../enums/TemporalBoundKind/"
    

        
      
```





## Inheritance
* [Edge](../classes/Edge.md)
    * **ProvenanceEdge**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | [Edge](../classes/Edge.md) |
| [source](../slots/source.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The asserting/originating node (directed — §12 | [Edge](../classes/Edge.md) |
| [target](../slots/target.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | [Edge](../classes/Edge.md) |
| [edge_type](../slots/edge_type.md) | 1 <br/> [EdgeType](../enums/EdgeType.md) | Typed from the closed catalog (§12 | [Edge](../classes/Edge.md) |
| [valid_from](../slots/valid_from.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | [Edge](../classes/Edge.md) |
| [valid_to](../slots/valid_to.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | [Edge](../classes/Edge.md) |
| [valid_from_kind](../slots/valid_from_kind.md) | 0..1 <br/> [TemporalBoundKind](../enums/TemporalBoundKind.md) | Snapshot sharing carries unknown/ongoing (SIG-ONTO-044) | [Edge](../classes/Edge.md) |
| [valid_to_kind](../slots/valid_to_kind.md) | 0..1 <br/> [TemporalBoundKind](../enums/TemporalBoundKind.md) |  | [Edge](../classes/Edge.md) |
| [observed_at](../slots/observed_at.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | [Edge](../classes/Edge.md) |
| [sources](../slots/sources.md) | * <br/> [Uriorcurie](../types/Uriorcurie.md) | At least one supporting claim (§12 | [Edge](../classes/Edge.md) |
| [asserted_by](../slots/asserted_by.md) | 0..1 <br/> [Uriorcurie](../types/Uriorcurie.md) | Which party asserted it — perspectival (§12 | [Edge](../classes/Edge.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:ProvenanceEdge |
| native | sig:ProvenanceEdge |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ProvenanceEdge
description: Provenance relationships among claims, captures, artifacts, and sources
  (§12.7).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Edge

```
</details>

### Induced

<details>
```yaml
name: ProvenanceEdge
description: Provenance relationships among claims, captures, artifacts, and sources
  (§12.7).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Edge
attributes:
  id:
    name: id
    from_schema: https://ontology.sig-project.org/schema/edges
    identifier: true
    owner: ProvenanceEdge
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
    owner: ProvenanceEdge
    domain_of:
    - Edge
    range: uriorcurie
    required: true
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
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
    owner: ProvenanceEdge
    domain_of:
    - Edge
    range: EdgeType
    required: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_from_kind:
    name: valid_from_kind
    description: Snapshot sharing carries unknown/ongoing (SIG-ONTO-044).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
    domain_of:
    - Edge
    range: TemporalBoundKind
  valid_to_kind:
    name: valid_to_kind
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
    domain_of:
    - Edge
    range: TemporalBoundKind
  observed_at:
    name: observed_at
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
    domain_of:
    - Edge
    range: edtf
  sources:
    name: sources
    description: At least one supporting claim (§12.1.4, SIG-CHART-013).
    from_schema: https://ontology.sig-project.org/schema/edges
    owner: ProvenanceEdge
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
    owner: ProvenanceEdge
    domain_of:
    - Edge
    range: uriorcurie

```
</details></div>