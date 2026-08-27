---
search:
  boost: 10.0
---

# Class: Organization 


_The single entity for ALL institutional actors; "vendor" is a role, not a subtype (§11.2, SIG-ONTO-012). canonical_name is a claim, not a column (§8.2)._



<div data-search-exclude markdown="1">



URI: [sig:class/Organization](https://ontology.sig-project.org/schema/class/Organization)





```mermaid
 classDiagram
    class Organization
    click Organization href "../../classes/Organization/"
      Entity <|-- Organization
        click Entity href "../../classes/Entity/"
      
      Organization : address
        
      Organization : alias
        
      Organization : alias_type
        
          
    
        
        
        Organization --> "*" AliasType : alias_type
        click AliasType href "../../enums/AliasType/"
    

        
      Organization : canonical_name
        
      Organization : government_domain
        
      Organization : id
        
      Organization : identifier
        
      Organization : identifier_system
        
      Organization : jurisdiction
        
          
    
        
        
        Organization --> "0..1" Jurisdiction : jurisdiction
        click Jurisdiction href "../../classes/Jurisdiction/"
    

        
      Organization : name_lang
        
      Organization : organization_type
        
          
    
        
        
        Organization --> "0..1" OrganizationType : organization_type
        click OrganizationType href "../../enums/OrganizationType/"
    

        
      Organization : parent_organization
        
          
    
        
        
        Organization --> "0..1" Organization : parent_organization
        click Organization href "../../classes/Organization/"
    

        
      Organization : publication_review
        
      Organization : succession
        
          
    
        
        
        Organization --> "*" Organization : succession
        click Organization href "../../classes/Organization/"
    

        
      Organization : succession_kind
        
          
    
        
        
        Organization --> "*" SuccessionKind : succession_kind
        click SuccessionKind href "../../enums/SuccessionKind/"
    

        
      Organization : valid_from
        
      Organization : valid_to
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **Organization**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [canonical_name](../slots/canonical_name.md) | 0..1 <br/> [String](../types/String.md) | A claim, not an authoritative column (§8 | direct |
| [alias](../slots/alias.md) | * <br/> [String](../types/String.md) |  | direct |
| [alias_type](../slots/alias_type.md) | * <br/> [AliasType](../enums/AliasType.md) |  | direct |
| [name_lang](../slots/name_lang.md) | * <br/> [Bcp47](../types/Bcp47.md) |  | direct |
| [organization_type](../slots/organization_type.md) | 0..1 <br/> [OrganizationType](../enums/OrganizationType.md) |  | direct |
| [parent_organization](../slots/parent_organization.md) | 0..1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [jurisdiction](../slots/jurisdiction.md) | 0..1 <br/> [Jurisdiction](../classes/Jurisdiction.md) |  | direct |
| [identifier](../slots/identifier.md) | * <br/> [String](../types/String.md) | Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-00... | direct |
| [identifier_system](../slots/identifier_system.md) | * <br/> [String](../types/String.md) |  | direct |
| [government_domain](../slots/government_domain.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [address](../slots/address.md) | * <br/> [String](../types/String.md) |  | direct |
| [valid_from](../slots/valid_from.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [valid_to](../slots/valid_to.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [succession](../slots/succession.md) | * <br/> [Organization](../classes/Organization.md) |  | direct |
| [succession_kind](../slots/succession_kind.md) | * <br/> [SuccessionKind](../enums/SuccessionKind.md) |  | direct |
| [publication_review](../slots/publication_review.md) | 0..1 <br/> [Boolean](../types/Boolean.md) | Routes surrogate-only orgs through §43 | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Organization](../classes/Organization.md) | [parent_organization](../slots/parent_organization.md) | range | [Organization](../classes/Organization.md) |
| [Organization](../classes/Organization.md) | [succession](../slots/succession.md) | range | [Organization](../classes/Organization.md) |
| [Product](../classes/Product.md) | [vendor](../slots/vendor.md) | range | [Organization](../classes/Organization.md) |
| [Deployment](../classes/Deployment.md) | [deploying_organization](../slots/deploying_organization.md) | range | [Organization](../classes/Organization.md) |
| [Deployment](../classes/Deployment.md) | [vendor](../slots/vendor.md) | range | [Organization](../classes/Organization.md) |
| [PhysicalAsset](../classes/PhysicalAsset.md) | [manufacturer](../slots/manufacturer.md) | range | [Organization](../classes/Organization.md) |
| [DataSystem](../classes/DataSystem.md) | [operator](../slots/operator.md) | range | [Organization](../classes/Organization.md) |
| [DataSystem](../classes/DataSystem.md) | [vendor](../slots/vendor.md) | range | [Organization](../classes/Organization.md) |
| [DataSystem](../classes/DataSystem.md) | [holds_data_collected_by](../slots/holds_data_collected_by.md) | range | [Organization](../classes/Organization.md) |
| [Contract](../classes/Contract.md) | [buyer](../slots/buyer.md) | range | [Organization](../classes/Organization.md) |
| [Contract](../classes/Contract.md) | [seller](../slots/seller.md) | range | [Organization](../classes/Organization.md) |
| [FundingInstrument](../classes/FundingInstrument.md) | [funder](../slots/funder.md) | range | [Organization](../classes/Organization.md) |
| [FundingInstrument](../classes/FundingInstrument.md) | [recipient](../slots/recipient.md) | range | [Organization](../classes/Organization.md) |
| [Policy](../classes/Policy.md) | [adopting_body](../slots/adopting_body.md) | range | [Organization](../classes/Organization.md) |
| [LegalInstrument](../classes/LegalInstrument.md) | [enacting_body](../slots/enacting_body.md) | range | [Organization](../classes/Organization.md) |
| [ConfigurationState](../classes/ConfigurationState.md) | [sharing_partner](../slots/sharing_partner.md) | range | [Organization](../classes/Organization.md) |
| [UsageAggregate](../classes/UsageAggregate.md) | [searching_org](../slots/searching_org.md) | range | [Organization](../classes/Organization.md) |
| [UsageAggregate](../classes/UsageAggregate.md) | [source_org](../slots/source_org.md) | range | [Organization](../classes/Organization.md) |
| [AccountabilityEvent](../classes/AccountabilityEvent.md) | [organizations](../slots/organizations.md) | range | [Organization](../classes/Organization.md) |
| [LegalProceeding](../classes/LegalProceeding.md) | [court](../slots/court.md) | range | [Organization](../classes/Organization.md) |
| [RecordsRequest](../classes/RecordsRequest.md) | [requesting_party](../slots/requesting_party.md) | range | [Organization](../classes/Organization.md) |
| [RecordsRequest](../classes/RecordsRequest.md) | [target_agency](../slots/target_agency.md) | range | [Organization](../classes/Organization.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:Organization |
| native | sig:Organization |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Organization
description: The single entity for ALL institutional actors; "vendor" is a role, not
  a subtype (§11.2, SIG-ONTO-012). canonical_name is a claim, not a column (§8.2).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  canonical_name:
    name: canonical_name
    description: A claim, not an authoritative column (§8.2, SIG-ONTO-003).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: string
  alias:
    name: alias
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: string
    multivalued: true
  alias_type:
    name: alias_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: AliasType
    multivalued: true
  name_lang:
    name: name_lang
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Jurisdiction
    - Organization
    range: bcp47
    multivalued: true
  organization_type:
    name: organization_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: OrganizationType
  parent_organization:
    name: parent_organization
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: Organization
  jurisdiction:
    name: jurisdiction
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    - Deployment
    - LegalInstrument
    range: Jurisdiction
  identifier:
    name: identifier
    description: Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-006).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: string
    multivalued: true
  identifier_system:
    name: identifier_system
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: string
    multivalued: true
  government_domain:
    name: government_domain
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: string
  address:
    name: address
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: string
    multivalued: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/entities
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  succession:
    name: succession
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: Organization
    multivalued: true
  succession_kind:
    name: succession_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: SuccessionKind
    multivalued: true
  publication_review:
    name: publication_review
    description: Routes surrogate-only orgs through §43.4 before public exposure (SIG-ONTO-013).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Organization
    range: boolean

```
</details>

### Induced

<details>
```yaml
name: Organization
description: The single entity for ALL institutional actors; "vendor" is a role, not
  a subtype (§11.2, SIG-ONTO-012). canonical_name is a claim, not a column (§8.2).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  canonical_name:
    name: canonical_name
    description: A claim, not an authoritative column (§8.2, SIG-ONTO-003).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: string
  alias:
    name: alias
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: string
    multivalued: true
  alias_type:
    name: alias_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: AliasType
    multivalued: true
  name_lang:
    name: name_lang
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: Organization
    domain_of:
    - Jurisdiction
    - Organization
    range: bcp47
    multivalued: true
  organization_type:
    name: organization_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: OrganizationType
  parent_organization:
    name: parent_organization
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: Organization
  jurisdiction:
    name: jurisdiction
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    - Deployment
    - LegalInstrument
    range: Jurisdiction
  identifier:
    name: identifier
    description: Repeatable (scheme,value) pairs, qualified by identifier_system (SIG-IDENT-006).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: string
    multivalued: true
  identifier_system:
    name: identifier_system
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: string
    multivalued: true
  government_domain:
    name: government_domain
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: string
  address:
    name: address
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: string
    multivalued: true
  valid_from:
    name: valid_from
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: Organization
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  valid_to:
    name: valid_to
    from_schema: https://ontology.sig-project.org/schema/entities
    owner: Organization
    domain_of:
    - Jurisdiction
    - Organization
    - Edge
    range: edtf
  succession:
    name: succession
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: Organization
    multivalued: true
  succession_kind:
    name: succession_kind
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: SuccessionKind
    multivalued: true
  publication_review:
    name: publication_review
    description: Routes surrogate-only orgs through §43.4 before public exposure (SIG-ONTO-013).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Organization
    domain_of:
    - Organization
    range: boolean
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: Organization
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>