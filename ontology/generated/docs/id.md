---
search:
  boost: 5.0
---

# Slot: id 


_The entity's stable minted identity (L2 identity only, §8.2)._



<div data-search-exclude markdown="1">



URI: [sig:id](https://ontology.sig-project.org/schema/id)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Entity](Entity.md) | Abstract base — every entity has identity (§3 |  no  |
| [Jurisdiction](Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |
| [Organization](Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |
| [Person](Person.md) | [NEW] Tightly constrained (§11 |  no  |
| [Product](Product.md) | A product; MUST NOT be equated with a Technology (§11 |  no  |
| [Technology](Technology.md) | A three-level technology (domain→family→technology, §11 |  no  |
| [Capability](Capability.md) | A verb |  no  |
| [Deployment](Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |  no  |
| [PhysicalAsset](PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |
| [CandidateAsset](CandidateAsset.md) | [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NO... |  no  |
| [DataSystem](DataSystem.md) | Reference databases as infrastructure — representable even where SIG holds no... |  no  |
| [Contract](Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |
| [FundingInstrument](FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |  no  |
| [Policy](Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |  no  |
| [LegalInstrument](LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |  no  |
| [ConfigurationState](ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |
| [UsageAggregate](UsageAggregate.md) | Aggregated usage; direction is the point (§11 |  no  |
| [AccountabilityEvent](AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |
| [LegalProceeding](LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |  no  |
| [RecordsRequest](RecordsRequest.md) | [NEW] A public-records request SIG both cites as provenance and generates as ... |  no  |
| [Source](Source.md) | A publisher of evidence (§10 |  no  |
| [EvidenceArtifact](EvidenceArtifact.md) | A specific artifact published by a Source (§10 |  no  |
| [EvidenceCapture](EvidenceCapture.md) | A content-addressed capture of an artifact at a time (§10 |  no  |
| [Extraction](Extraction.md) | A run that extracted claims from a capture (§10 |  no  |
| [Claim](Claim.md) | An append-only assertion (subject, predicate, value,  |  no  |
| [Resolution](Resolution.md) | A stored current-best decision record (§16 |  no  |
| [Contradiction](Contradiction.md) | A first-class, addressable contradiction object (§31) |  no  |
| [ResearchTask](ResearchTask.md) | [NEW] A research task as an object (§11 |  no  |
| [CoverageRecord](CoverageRecord.md) | [NEW] Makes negative claims queryable (§11 |  no  |
| [Edge](Edge.md) | Universal edge requirements (§12 |  no  |
| [AccessRelationship](AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |
| [IntegrationEdge](IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |
| [RoleAssignment](RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |
| [StructuralEdge](StructuralEdge.md) | Organizational/structural relationships (§12 |  no  |
| [ProvenanceEdge](ProvenanceEdge.md) | Provenance relationships among claims, captures, artifacts, and sources (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Uriorcurie](Uriorcurie.md) |
| Domain Of | [Entity](Entity.md), [Edge](Edge.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Identifier | Yes |












## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | sig:id |
| native | sig:id |




## LinkML Source

<details>
```yaml
name: id
description: The entity's stable minted identity (L2 identity only, §8.2).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
identifier: true
domain_of:
- Entity
- Edge
range: uriorcurie
required: true

```
</details></div>