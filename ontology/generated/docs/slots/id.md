---
search:
  boost: 5.0
---

# Slot: id 


_The entity's stable minted identity (L2 identity only, §8.2)._



<div data-search-exclude markdown="1">



URI: [sig:slot/id](https://ontology.sig-project.org/schema/slot/id)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Entity](../classes/Entity.md) | Abstract base — every entity has identity (§3 |  no  |
| [Jurisdiction](../classes/Jurisdiction.md) | [NEW] A first-class jurisdiction with a self-referential hierarchy, a pluggab... |  no  |
| [Organization](../classes/Organization.md) | The single entity for ALL institutional actors; "vendor" is a role, not a sub... |  no  |
| [Person](../classes/Person.md) | [NEW] Tightly constrained (§11 |  no  |
| [Product](../classes/Product.md) | A product; MUST NOT be equated with a Technology (§11 |  no  |
| [Technology](../classes/Technology.md) | A three-level technology (domain→family→technology, §11 |  no  |
| [Capability](../classes/Capability.md) | A verb |  no  |
| [Deployment](../classes/Deployment.md) | The bridge between organizational adoption and individual devices; creatable ... |  no  |
| [PhysicalAsset](../classes/PhysicalAsset.md) | A field-observed device; geometry is OPTIONAL and operator absence is a first... |  no  |
| [CandidateAsset](../classes/CandidateAsset.md) | [NEW] RF/heuristic leads that MUST live in a separate entity type and MUST NO... |  no  |
| [DataSystem](../classes/DataSystem.md) | Reference databases as infrastructure — representable even where SIG holds no... |  no  |
| [Contract](../classes/Contract.md) | A contract; acquisition_channel and parent_cooperative_contract are REQUIRED ... |  no  |
| [FundingInstrument](../classes/FundingInstrument.md) | [NEW] Purchaser != operator != funder (§11 |  no  |
| [Policy](../classes/Policy.md) | An institutional policy; MUST NOT be merged with ConfigurationState (§11 |  no  |
| [LegalInstrument](../classes/LegalInstrument.md) | [NEW] Laws and regulations as a modelled entity (§11 |  no  |
| [ConfigurationState](../classes/ConfigurationState.md) | Promoted to a first-class, time-versioned, per-Deployment entity (§11 |  no  |
| [UsageAggregate](../classes/UsageAggregate.md) | Aggregated usage; direction is the point (§11 |  no  |
| [AccountabilityEvent](../classes/AccountabilityEvent.md) | An accountability event; epistemic_status is REQUIRED and rendered everywhere... |  no  |
| [LegalProceeding](../classes/LegalProceeding.md) | Split from AccountabilityEvent — dockets, parties, filings, posture (§11 |  no  |
| [RecordsRequest](../classes/RecordsRequest.md) | [NEW] A public-records request SIG both cites as provenance and generates as ... |  no  |
| [Source](../classes/Source.md) | A publisher of evidence (§10 |  no  |
| [EvidenceArtifact](../classes/EvidenceArtifact.md) | A specific artifact published by a Source (§10 |  no  |
| [EvidenceCapture](../classes/EvidenceCapture.md) | A content-addressed capture of an artifact at a time (§10 |  no  |
| [Extraction](../classes/Extraction.md) | A run that extracted claims from a capture (§10 |  no  |
| [Claim](../classes/Claim.md) | An append-only assertion (subject, predicate, value,  |  no  |
| [Resolution](../classes/Resolution.md) | A stored current-best decision record (§16 |  no  |
| [Contradiction](../classes/Contradiction.md) | A first-class, addressable contradiction object (§31) |  no  |
| [ResearchTask](../classes/ResearchTask.md) | [NEW] A research task as an object (§11 |  no  |
| [CoverageRecord](../classes/CoverageRecord.md) | [NEW] Makes negative claims queryable (§11 |  no  |
| [Edge](../classes/Edge.md) | Universal edge requirements (§12 |  no  |
| [AccessRelationship](../classes/AccessRelationship.md) | A sharing/access relationship; direction, scope, automaticity, and kind are a... |  no  |
| [IntegrationEdge](../classes/IntegrationEdge.md) | A data-bearing integration edge (§12 |  no  |
| [RoleAssignment](../classes/RoleAssignment.md) | Assigns one of the fourteen roles (§12 |  no  |
| [StructuralEdge](../classes/StructuralEdge.md) | Organizational/structural relationships (§12 |  no  |
| [ProvenanceEdge](../classes/ProvenanceEdge.md) | Provenance relationships among claims, captures, artifacts, and sources (§12 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Uriorcurie](../types/Uriorcurie.md) |
| Domain Of | [Entity](../classes/Entity.md), [Edge](../classes/Edge.md) |

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