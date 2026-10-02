---
search:
  boost: 10.0
---

# Class: EvidenceCapture 


_A content-addressed capture of an artifact at a time (§10.2, L0)._



<div data-search-exclude markdown="1">



URI: [sig:class/EvidenceCapture](https://ontology.sig-project.org/schema/class/EvidenceCapture)





```mermaid
 classDiagram
    class EvidenceCapture
    click EvidenceCapture href "../../classes/EvidenceCapture/"
      Entity <|-- EvidenceCapture
        click Entity href "../../classes/Entity/"
      
      EvidenceCapture : blob_digest
        
      EvidenceCapture : byte_size
        
      EvidenceCapture : capture_classification
        
          
    
        
        
        EvidenceCapture --> "0..1" CaptureClassification : capture_classification
        click CaptureClassification href "../../enums/CaptureClassification/"
    

        
      EvidenceCapture : captured_at
        
      EvidenceCapture : captures_artifact
        
          
    
        
        
        EvidenceCapture --> "0..1" EvidenceArtifact : captures_artifact
        click EvidenceArtifact href "../../classes/EvidenceArtifact/"
    

        
      EvidenceCapture : content_digest
        
      EvidenceCapture : id
        
      EvidenceCapture : media_type
        
      EvidenceCapture : ocfl_object_id
        
      EvidenceCapture : ocfl_version
        
      EvidenceCapture : source_uri
        
      
```





## Inheritance
* [Entity](../classes/Entity.md)
    * **EvidenceCapture**


## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [captures_artifact](../slots/captures_artifact.md) | 0..1 <br/> [EvidenceArtifact](../classes/EvidenceArtifact.md) |  | direct |
| [captured_at](../slots/captured_at.md) | 0..1 <br/> [Datetime](../types/Datetime.md) |  | direct |
| [content_digest](../slots/content_digest.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [ocfl_object_id](../slots/ocfl_object_id.md) | 0..1 <br/> [String](../types/String.md) | The OCFL object the capture's bytes were committed under | direct |
| [ocfl_version](../slots/ocfl_version.md) | 0..1 <br/> [String](../types/String.md) | The immutable OCFL version this occurrence IS — a binding pins this version, ... | direct |
| [source_uri](../slots/source_uri.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [blob_digest](../slots/blob_digest.md) | 0..1 <br/> [String](../types/String.md) | The deduplicated evidence_blob identity the bytes dedup to (SIG-EVID-004) | direct |
| [capture_classification](../slots/capture_classification.md) | 0..1 <br/> [CaptureClassification](../enums/CaptureClassification.md) |  | direct |
| [byte_size](../slots/byte_size.md) | 0..1 <br/> [Integer](../types/Integer.md) |  | direct |
| [media_type](../slots/media_type.md) | 0..1 <br/> [String](../types/String.md) |  | direct |
| [id](../slots/id.md) | 1 <br/> [Uriorcurie](../types/Uriorcurie.md) | The entity's stable minted identity (L2 identity only, §8 | [Entity](../classes/Entity.md) |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [Extraction](../classes/Extraction.md) | [from_capture](../slots/from_capture.md) | range | [EvidenceCapture](../classes/EvidenceCapture.md) |
| [ClaimEvidence](../classes/ClaimEvidence.md) | [capture](../slots/capture.md) | range | [EvidenceCapture](../classes/EvidenceCapture.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:EvidenceCapture |
| native | sig:EvidenceCapture |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: EvidenceCapture
description: A content-addressed capture of an artifact at a time (§10.2, L0).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  captures_artifact:
    name: captures_artifact
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: EvidenceArtifact
  captured_at:
    name: captured_at
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: datetime
  content_digest:
    name: content_digest
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: string
  ocfl_object_id:
    name: ocfl_object_id
    description: The OCFL object the capture's bytes were committed under.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: string
  ocfl_version:
    name: ocfl_version
    description: The immutable OCFL version this occurrence IS — a binding pins this
      version, never a mutable inventory head.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: string
  source_uri:
    name: source_uri
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: string
  blob_digest:
    name: blob_digest
    description: The deduplicated evidence_blob identity the bytes dedup to (SIG-EVID-004).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: string
  capture_classification:
    name: capture_classification
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: CaptureClassification
  byte_size:
    name: byte_size
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: integer
  media_type:
    name: media_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    domain_of:
    - EvidenceCapture
    range: string

```
</details>

### Induced

<details>
```yaml
name: EvidenceCapture
description: A content-addressed capture of an artifact at a time (§10.2, L0).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
is_a: Entity
attributes:
  captures_artifact:
    name: captures_artifact
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: EvidenceArtifact
  captured_at:
    name: captured_at
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: datetime
  content_digest:
    name: content_digest
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: string
  ocfl_object_id:
    name: ocfl_object_id
    description: The OCFL object the capture's bytes were committed under.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: string
  ocfl_version:
    name: ocfl_version
    description: The immutable OCFL version this occurrence IS — a binding pins this
      version, never a mutable inventory head.
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: string
  source_uri:
    name: source_uri
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: string
  blob_digest:
    name: blob_digest
    description: The deduplicated evidence_blob identity the bytes dedup to (SIG-EVID-004).
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: string
  capture_classification:
    name: capture_classification
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: CaptureClassification
  byte_size:
    name: byte_size
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: integer
  media_type:
    name: media_type
    from_schema: https://ontology.sig-project.org/schema/entities
    rank: 1000
    owner: EvidenceCapture
    domain_of:
    - EvidenceCapture
    range: string
  id:
    name: id
    description: The entity's stable minted identity (L2 identity only, §8.2).
    from_schema: https://ontology.sig-project.org/schema/sig
    rank: 1000
    identifier: true
    owner: EvidenceCapture
    domain_of:
    - Entity
    - Edge
    range: uriorcurie
    required: true

```
</details></div>