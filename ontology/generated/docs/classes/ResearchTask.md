---
search:
  boost: 10.0
---

# Class: ResearchTask 


_[NEW] A research task as an object (§11.22, behaviour at §33.2)._



<div data-search-exclude markdown="1">



URI: [sig:class/ResearchTask](https://ontology.sig-project.org/schema/class/ResearchTask)





```mermaid
 classDiagram
    class ResearchTask
    click ResearchTask href "../../classes/ResearchTask/"
      Entity <|-- ResearchTask
        click Entity href "../../classes/Entity/"
      
      ResearchTask : closing_condition
        
      ResearchTask : id
        
      ResearchTask : resolved
        
      ResearchTask : target
        
      ResearchTask : task_type
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **ResearchTask**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [task_type](../slots/task_type.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [target](../slots/target.md) | 0..1 <br/> [Uriorcurie](../types/Uriorcurie.md) |  | direct |
| [closing_condition](../slots/closing_condition.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [resolved](../slots/resolved.md) | 0..1 <br/> [Boolean](../types/Boolean.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |















## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:ResearchTask |
| native | sig:ResearchTask |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: ResearchTask
description: '[NEW] A research task as an object (§11.22, behaviour at §33.2).'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  task_type:
    name: task_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - ResearchTask
    range: string
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - ResearchTask
    - Edge
    range: uriorcurie
  closing_condition:
    name: closing_condition
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - ResearchTask
    range: string
  resolved:
    name: resolved
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - ResearchTask
    range: boolean

```
</details>

### Induced

<details>
```yaml
name: ResearchTask
description: '[NEW] A research task as an object (§11.22, behaviour at §33.2).'
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  task_type:
    name: task_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: ResearchTask
    domain_of:
    - ResearchTask
    range: string
  target:
    name: target
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: ResearchTask
    domain_of:
    - ResearchTask
    - Edge
    range: uriorcurie
  closing_condition:
    name: closing_condition
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: ResearchTask
    domain_of:
    - ResearchTask
    range: string
  resolved:
    name: resolved
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: ResearchTask
    domain_of:
    - ResearchTask
    range: boolean
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: ResearchTask
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>