---
search:
  boost: 10.0
---

# Class: Contract 


_A contract; acquisition_channel and parent_cooperative_contract are REQUIRED model elements (§11.11, SIG-ONTO-032)._



<div data-search-exclude markdown="1">



URI: [sig:class/Contract](https://ontology.surveillancegraph.org/schema/class/Contract)





```mermaid
 classDiagram
    class Contract
    click Contract href "../../classes/Contract/"
      Entity <|-- Contract
        click Entity href "../../classes/Entity/"
      
      Contract : acquisition_channel
        
          
    
        
        
        Contract --> "0..1" AcquisitionChannel : acquisition_channel
        click AcquisitionChannel href "../../enums/AcquisitionChannel/"
    

        
      Contract : amends_contract
        
          
    
        
        
        Contract --> "0..1" Contract : amends_contract
        click Contract href "../../classes/Contract/"
    

        
      Contract : amount
        
      Contract : auto_renews
        
      Contract : buyer
        
          
    
        
        
        Contract --> "0..1" Organization : buyer
        click Organization href "../../classes/Organization/"
    

        
      Contract : currency
        
      Contract : document
        
      Contract : end_date
        
      Contract : id
        
      Contract : notice_window_days
        
      Contract : parent_cooperative_contract
        
          
    
        
        
        Contract --> "0..1" Contract : parent_cooperative_contract
        click Contract href "../../classes/Contract/"
    

        
      Contract : products
        
          
    
        
        
        Contract --> "*" Product : products
        click Product href "../../classes/Product/"
    

        
      Contract : quantities
        
      Contract : renewal_options
        
      Contract : renewal_term_months
        
      Contract : seller
        
          
    
        
        
        Contract --> "0..1" Organization : seller
        click Organization href "../../classes/Organization/"
    

        
      Contract : signed_date
        
      Contract : start_date
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **Contract**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [buyer](../slots/buyer.md) | 0..1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [seller](../slots/seller.md) | 0..1 <br/> [Organization](../classes/Organization.md) |  | direct |
| [amount](../slots/amount.md) | 0..1 <br/> [Money](../types/Money.md) |  | direct |
| [currency](../slots/currency.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [signed_date](../slots/signed_date.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [start_date](../slots/start_date.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [end_date](../slots/end_date.md) | 0..1 <br/> [Edtf](../types/Edtf.md) |  | direct |
| [renewal_options](../slots/renewal_options.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [auto_renews](../slots/auto_renews.md) | 0..1 <br/> [Boolean](../types/Boolean.md) | Whether the contract renews automatically absent notice — the dated renewal c... | direct |
| [notice_window_days](../slots/notice_window_days.md) | 0..1 <br/> [Integer](../types/Integer.md) | Days before term end by which non-renewal notice is due (P37 | direct |
| [renewal_term_months](../slots/renewal_term_months.md) | 0..1 <br/> [Integer](../types/Integer.md) | Length in months of each stated renewal term (P37 | direct |
| [products](../slots/products.md) | * <br/> [Product](../classes/Product.md) |  | direct |
| [quantities](../slots/quantities.md) | * <br/> [Integer](../types/Integer.md) |  | direct |
| [document](../slots/document.md) | 0..1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | direct |
| [acquisition_channel](../slots/acquisition_channel.md) | 0..1 <br/> [AcquisitionChannel](../enums/AcquisitionChannel.md) |  | direct |
| [parent_cooperative_contract](../slots/parent_cooperative_contract.md) | 0..1 <br/> [Contract](../classes/Contract.md) | The master award being ridden (SIG-ONTO-032) | direct |
| [amends_contract](../slots/amends_contract.md) | 0..1 <br/> [Contract](../classes/Contract.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Contract](../classes/Contract.md) | [parent_cooperative_contract](../slots/parent_cooperative_contract.md) | range | [Contract](../classes/Contract.md) |
| [Contract](../classes/Contract.md) | [amends_contract](../slots/amends_contract.md) | range | [Contract](../classes/Contract.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.surveillancegraph.org/schema/sig




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
from_schema: https://ontology.surveillancegraph.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  buyer:
    name: buyer
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Organization
  seller:
    name: seller
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Organization
  amount:
    name: amount
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    - FundingInstrument
    range: money
  currency:
    name: currency
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: string
  signed_date:
    name: signed_date
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: edtf
  start_date:
    name: start_date
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: edtf
  end_date:
    name: end_date
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: edtf
  renewal_options:
    name: renewal_options
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: string
  auto_renews:
    name: auto_renews
    description: Whether the contract renews automatically absent notice — the dated
      renewal clause value the decision calendar derives a renewal_deadline from (P37.31
      / K7 WX-02).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: boolean
  notice_window_days:
    name: notice_window_days
    description: Days before term end by which non-renewal notice is due (P37.31).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: integer
  renewal_term_months:
    name: renewal_term_months
    description: Length in months of each stated renewal term (P37.31).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: integer
  products:
    name: products
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Product
    multivalued: true
  quantities:
    name: quantities
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: integer
    multivalued: true
  document:
    name: document
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    - Policy
    range: uriorcurie
  acquisition_channel:
    name: acquisition_channel
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: AcquisitionChannel
  parent_cooperative_contract:
    name: parent_cooperative_contract
    description: The master award being ridden (SIG-ONTO-032).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    domain_of:
    - Contract
    range: Contract
  amends_contract:
    name: amends_contract
    from_schema: https://ontology.surveillancegraph.org/schema/entities
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
from_schema: https://ontology.surveillancegraph.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  buyer:
    name: buyer
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Organization
  seller:
    name: seller
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Organization
  amount:
    name: amount
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    - FundingInstrument
    range: money
  currency:
    name: currency
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: string
  signed_date:
    name: signed_date
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: edtf
  start_date:
    name: start_date
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: edtf
  end_date:
    name: end_date
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: edtf
  renewal_options:
    name: renewal_options
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: string
  auto_renews:
    name: auto_renews
    description: Whether the contract renews automatically absent notice — the dated
      renewal clause value the decision calendar derives a renewal_deadline from (P37.31
      / K7 WX-02).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: boolean
  notice_window_days:
    name: notice_window_days
    description: Days before term end by which non-renewal notice is due (P37.31).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: integer
  renewal_term_months:
    name: renewal_term_months
    description: Length in months of each stated renewal term (P37.31).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: integer
  products:
    name: products
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Product
    multivalued: true
  quantities:
    name: quantities
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: integer
    multivalued: true
  document:
    name: document
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    - Policy
    range: uriorcurie
  acquisition_channel:
    name: acquisition_channel
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: AcquisitionChannel
  parent_cooperative_contract:
    name: parent_cooperative_contract
    description: The master award being ridden (SIG-ONTO-032).
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Contract
  amends_contract:
    name: amends_contract
    from_schema: https://ontology.surveillancegraph.org/schema/entities
    rank: 1000
    owner: Contract
    domain_of:
    - Contract
    range: Contract
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.surveillancegraph.org/schema/sig
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