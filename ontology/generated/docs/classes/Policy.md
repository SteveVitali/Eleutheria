---
search:
  boost: 10.0
---

# Class: Policy 


_An institutional policy; MUST NOT be merged with ConfigurationState (§11.13, SIG-ONTO-034). Their disagreement is a first-class finding._



<div data-search-exclude markdown="1">



URI: [sig:class/Policy](https://ontology.sig-project.org/schema/class/Policy)





```mermaid
 classDiagram
    class Policy
    click Policy href "../../classes/Policy/"
      Entity <|-- Policy
        click Entity href "../../classes/Entity/"
      
      Policy : adopting_body
        
          
    
        
        
        Policy --> "0..1" Organization : adopting_body
        click Organization href "../../classes/Organization/"
    

        
      Policy : applies_to
        
      Policy : document
        
      Policy : effective_from
        
      Policy : effective_to
        
      Policy : enforcement_mechanism
        
          
    
        
        
        Policy --> "0..1" EnforcementMechanism : enforcement_mechanism
        click EnforcementMechanism href "../../enums/EnforcementMechanism/"
    

        
      Policy : id
        
      Policy : policy_type
        
          
    
        
        
        Policy --> "0..1" PolicyType : policy_type
        click PolicyType href "../../enums/PolicyType/"
    

        
      Policy : text
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **Policy**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [policy_type](../slots/policy_type.md) | 0..1 <br/> [PolicyType](../enums/PolicyType.md) |  | direct |
| [applies_to](../slots/applies_to.md) | * <br/> [Uriorcurie](../types/Uriorcurie.md) | Organization, Deployment, or Product — polymorphic and repeatable | direct |
| [effective_from](../slots/effective_from.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [effective_to](../slots/effective_to.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [adopting_body](../slots/adopting_body.md) | 0..1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [text](../slots/text.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [document](../slots/document.md) | 0..1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | direct |
| [enforcement_mechanism](../slots/enforcement_mechanism.md) | 0..1 <br/> [EnforcementMechanism](../enums/EnforcementMechanism.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:Policy |
| native | sig:Policy |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Policy
description: An institutional policy; MUST NOT be merged with ConfigurationState (§11.13,
  SIG-ONTO-034). Their disagreement is a first-class finding.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  policy_type:
    name: policy_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    range: PolicyType
  applies_to:
    name: applies_to
    description: Organization, Deployment, or Product — polymorphic and repeatable.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    range: uriorcurie
    multivalued: true
  effective_from:
    name: effective_from
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    - LegalInstrument
    range: edtf
  effective_to:
    name: effective_to
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    - LegalInstrument
    range: edtf
  adopting_body:
    name: adopting_body
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    range: Organization
  text:
    name: text
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    range: string
  document:
    name: document
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Contract
    - Policy
    range: uriorcurie
  enforcement_mechanism:
    name: enforcement_mechanism
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Policy
    range: EnforcementMechanism

```
</details>

### Induced

<details>
```yaml
name: Policy
description: An institutional policy; MUST NOT be merged with ConfigurationState (§11.13,
  SIG-ONTO-034). Their disagreement is a first-class finding.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  policy_type:
    name: policy_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    range: PolicyType
  applies_to:
    name: applies_to
    description: Organization, Deployment, or Product — polymorphic and repeatable.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    range: uriorcurie
    multivalued: true
  effective_from:
    name: effective_from
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    - LegalInstrument
    range: edtf
  effective_to:
    name: effective_to
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    - LegalInstrument
    range: edtf
  adopting_body:
    name: adopting_body
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    range: Organization
  text:
    name: text
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    range: string
  document:
    name: document
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: Policy
    domain_of:
    - Contract
    - Policy
    range: uriorcurie
  enforcement_mechanism:
    name: enforcement_mechanism
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Policy
    domain_of:
    - Policy
    range: EnforcementMechanism
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: Policy
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>