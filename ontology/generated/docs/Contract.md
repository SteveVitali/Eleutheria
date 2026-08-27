---
search:
  boost: 10.0
---

# Class: Contract 


_A contract; acquisition_channel and parent_cooperative_contract are REQUIRED model elements (§11.11, SIG-ONTO-032)._



<div data-search-exclude markdown="1">



URI: [sig:Contract](https://ontology.sig-project.org/schema/Contract)





```mermaid
 classDiagram
    class Contract
    click Contract href "../Contract/"
      Entity <|-- Contract
        click Entity href "../Entity/"
      
      Contract : acquisition_channel
        
          
    
        
        
        Contract --> "0..1" AcquisitionChannel : acquisition_channel
        click AcquisitionChannel href "../AcquisitionChannel/"
    

        
      Contract : amends_contract
        
          
    
        
        
        Contract --> "0..1" Contract : amends_contract
        click Contract href "../Contract/"
    

        
      Contract : amount
        
      Contract : buyer
        
          
    
        
        
        Contract --> "0..1" Organization : buyer
        click Organization href "../Organization/"
    

        
      Contract : currency
        
      Contract : document
        
      Contract : end_date
        
      Contract : id
        
      Contract : parent_cooperative_contract
        
          
    
        
        
        Contract --> "0..1" Contract : parent_cooperative_contract
        click Contract href "../Contract/"
    

        
      Contract : products
        
          
    
        
        
        Contract --> "*" Product : products
        click Product href "../Product/"
    

        
      Contract : quantities
        
      Contract : renewal_options
        
      Contract : seller
        
          
    
        
        
        Contract --> "0..1" Organization : seller
        click Organization href "../Organization/"
    

        
      Contract : signed_date
        
      Contract : start_date
        
      
```





## Inheritance
* [Entity](Entity.md)
    * **Contract**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [buyer](buyer.md) | 0..1 <br/> [Organization](Organization.md) |  | direct |
| [seller](seller.md) | 0..1 <br/> [Organization](Organization.md) |  | direct |
| [amount](amount.md) | 0..1 <br/> [Money](Money.md) |  | direct |
| [currency](currency.md) | 0..1 <br/> [String](String.md) |  | direct |
| [signed_date](signed_date.md) | 0..1 <br/> [Edtf](Edtf.md) |  | direct |
| [start_date](start_date.md) | 0..1 <br/> [Edtf](Edtf.md) |  | direct |
| [end_date](end_date.md) | 0..1 <br/> [Edtf](Edtf.md) |  | direct |
| [renewal_options](renewal_options.md) | 0..1 <br/> [String](String.md) |  | direct |
| [products](products.md) | * <br/> [Product](Product.md) |  | direct |
| [quantities](quantities.md) | * <br/> [Integer](Integer.md) |  | direct |
| [document](document.md) | 0..1 <br/> [Uriorcurie](Uriorcurie.md) |  | direct |
| [acquisition_channel](acquisition_channel.md) | 0..1 <br/> [AcquisitionChannel](AcquisitionChannel.md) |  | direct |
| [parent_cooperative_contract](parent_cooperative_contract.md) | 0..1 <br/> [Contract](Contract.md) | The master award being ridden (SIG-ONTO-032) | direct |
| [amends_contract](amends_contract.md) | 0..1 <br/> [Contract](Contract.md) |  | direct |
| [id](id.md) | 1 <br/> [Uriorcurie](Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](Entity.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Contract](Contract.md) | [parent_cooperative_contract](parent_cooperative_contract.md) | range | [Contract](Contract.md) |
| [Contract](Contract.md) | [amends_contract](amends_contract.md) | range | [Contract](Contract.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:Contract |
| native | sig:Contract |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: Contract
description: A contract; acquisition_channel and parent_cooperative_contract are REQUIRED
  model elements (§11.11, SIG-ONTO-032).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  buyer:
    name: buyer
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Organization
  seller:
    name: seller
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Organization
  amount:
    name: amount
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    - FundingInstrument
    range: money
  currency:
    name: currency
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: string
  signed_date:
    name: signed_date
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: edtf
  start_date:
    name: start_date
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: edtf
  end_date:
    name: end_date
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: edtf
  renewal_options:
    name: renewal_options
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: string
  products:
    name: products
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Product
    multivalued: true
  quantities:
    name: quantities
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: integer
    multivalued: true
  document:
    name: document
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    - Policy
    range: uriorcurie
  acquisition_channel:
    name: acquisition_channel
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: AcquisitionChannel
  parent_cooperative_contract:
    name: parent_cooperative_contract
    description: The master award being ridden (SIG-ONTO-032).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Contract
  amends_contract:
    name: amends_contract
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Contract

```
</details>

### Induced

<details>
```yaml
name: Contract
description: A contract; acquisition_channel and parent_cooperative_contract are REQUIRED
  model elements (§11.11, SIG-ONTO-032).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  buyer:
    name: buyer
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Organization
  seller:
    name: seller
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Organization
  amount:
    name: amount
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    - FundingInstrument
    range: money
  currency:
    name: currency
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: string
  signed_date:
    name: signed_date
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: edtf
  start_date:
    name: start_date
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: edtf
  end_date:
    name: end_date
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: edtf
  renewal_options:
    name: renewal_options
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: string
  products:
    name: products
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Product
    multivalued: true
  quantities:
    name: quantities
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: integer
    multivalued: true
  document:
    name: document
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    - Policy
    range: uriorcurie
  acquisition_channel:
    name: acquisition_channel
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: AcquisitionChannel
  parent_cooperative_contract:
    name: parent_cooperative_contract
    description: The master award being ridden (SIG-ONTO-032).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Contract
  amends_contract:
    name: amends_contract
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Contract
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: Contract
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>