---
search:
  boost: 10.0
---

# Class: PhysicalAsset 


_A field-observed device; geometry is OPTIONAL and operator absence is a first-class countable state (§11.8, SIG-ONTO-027/028). Accommodates ways and relations, not only nodes, and MUST NOT force sensors into a camera abstraction._



<div data-search-exclude markdown="1">



URI: [sig:class/PhysicalAsset](https://ontology.sig-project.org/schema/class/PhysicalAsset)





```mermaid
 classDiagram
    class PhysicalAsset
    click PhysicalAsset href "../../classes/PhysicalAsset/"
      Entity <|-- PhysicalAsset
        click Entity href "../../classes/Entity/"
      
      PhysicalAsset : asset_type
        
      PhysicalAsset : confirmation_status
        
          
    
        
        
        PhysicalAsset --> "0..1" ConfirmationStatus : confirmation_status
        click ConfirmationStatus href "../../enums/ConfirmationStatus/"
    

        
      PhysicalAsset : deployment
        
          
    
        
        
        PhysicalAsset --> "0..1" Deployment : deployment
        click Deployment href "../../classes/Deployment/"
    

        
      PhysicalAsset : first_observed
        
      PhysicalAsset : geometry
        
      PhysicalAsset : id
        
      PhysicalAsset : last_observed
        
      PhysicalAsset : manufacturer
        
          
    
        
        
        PhysicalAsset --> "0..1" Organization : manufacturer
        click Organization href "../../classes/Organization/"
    

        
      PhysicalAsset : mobility
        
          
    
        
        
        PhysicalAsset --> "0..1" Mobility : mobility
        click Mobility href "../../enums/Mobility/"
    

        
      PhysicalAsset : model
        
      PhysicalAsset : osm_version
        
      PhysicalAsset : sensitivity_tier
        
      PhysicalAsset : upstream_id
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **PhysicalAsset**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [asset_type](../slots/asset_type.md) | 0..1 <br/> [TechnologyCode](../types/TechnologyCode.md) | A Technology reference, not a free string | direct |
| [geometry](../slots/geometry.md) | 0..1 <br/> [GeometryWkt](../types/GeometryWkt.md) | Optional (SIG-GEO-004) | direct |
| [mobility](../slots/mobility.md) | 0..1 <br/> [Mobility](../enums/Mobility.md) |  | direct |
| [manufacturer](../slots/manufacturer.md) | 0..1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [model](../slots/model.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [deployment](../slots/deployment.md) | 0..1 <br/> [Deployment](../classes/Deployment.md) | May be absent — the orphaned-device case | direct |
| [first_observed](../slots/first_observed.md) | 0..1 <br/> [Datetime](../types/Datetime.md) |  | direct |
| [last_observed](../slots/last_observed.md) | 0..1 <br/> [Datetime](../types/Datetime.md) |  | direct |
| [upstream_id](../slots/upstream_id.md) | * <br/> [String](../types/String.md) | Qualified by system (osm | direct |
| [osm_version](../slots/osm_version.md) | 0..1 <br/> [Integer](../types/Integer.md) |  | direct |
| [sensitivity_tier](../slots/sensitivity_tier.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [confirmation_status](../slots/confirmation_status.md) | 0..1 <br/> [ConfirmationStatus](../enums/ConfirmationStatus.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:PhysicalAsset |
| native | sig:PhysicalAsset |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: PhysicalAsset
description: A field-observed device; geometry is OPTIONAL and operator absence is
  a first-class countable state (§11.8, SIG-ONTO-027/028). Accommodates ways and relations,
  not only nodes, and MUST NOT force sensors into a camera abstraction.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  asset_type:
    name: asset_type
    description: A Technology reference, not a free string.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: technology_code
  geometry:
    name: geometry
    description: Optional (SIG-GEO-004).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: geometry_wkt
  mobility:
    name: mobility
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: Mobility
  manufacturer:
    name: manufacturer
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: Organization
  model:
    name: model
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: string
  deployment:
    name: deployment
    description: May be absent — the orphaned-device case.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    - ConfigurationState
    range: Deployment
  first_observed:
    name: first_observed
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: datetime
  last_observed:
    name: last_observed
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: datetime
  upstream_id:
    name: upstream_id
    description: Qualified by system (osm.node, osm.way, osm.relation, deflock.id,
      ...).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: string
    multivalued: true
  osm_version:
    name: osm_version
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: integer
  sensitivity_tier:
    name: sensitivity_tier
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: string
  confirmation_status:
    name: confirmation_status
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - PhysicalAsset
    range: ConfirmationStatus

```
</details>

### Induced

<details>
```yaml
name: PhysicalAsset
description: A field-observed device; geometry is OPTIONAL and operator absence is
  a first-class countable state (§11.8, SIG-ONTO-027/028). Accommodates ways and relations,
  not only nodes, and MUST NOT force sensors into a camera abstraction.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  asset_type:
    name: asset_type
    description: A Technology reference, not a free string.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: technology_code
  geometry:
    name: geometry
    description: Optional (SIG-GEO-004).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: geometry_wkt
  mobility:
    name: mobility
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: Mobility
  manufacturer:
    name: manufacturer
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: Organization
  model:
    name: model
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: string
  deployment:
    name: deployment
    description: May be absent — the orphaned-device case.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    - ConfigurationState
    range: Deployment
  first_observed:
    name: first_observed
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: datetime
  last_observed:
    name: last_observed
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: datetime
  upstream_id:
    name: upstream_id
    description: Qualified by system (osm.node, osm.way, osm.relation, deflock.id,
      ...).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: string
    multivalued: true
  osm_version:
    name: osm_version
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: integer
  sensitivity_tier:
    name: sensitivity_tier
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: string
  confirmation_status:
    name: confirmation_status
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: PhysicalAsset
    domain_of:
    - PhysicalAsset
    range: ConfirmationStatus
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: PhysicalAsset
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>