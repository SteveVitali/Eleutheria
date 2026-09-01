---
search:
  boost: 2.0
---


# Enum: ArtifactType 




_The genre of an evidence artifact (§10.3.2). SIG-INGEST-047 additionally carries state_auditor_survey, warrant, and procurement_aggregator_record (§23.6) — the state-auditor surveys are R1 government datasets and the aggregator record is the paywalled procurement-aggregator lead under a LINK custody posture._



<div data-search-exclude markdown="1">

URI: [sig:enum/ArtifactType](https://ontology.sig-project.org/schema/enum/ArtifactType)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| contract | None |  |
| invoice | None |  |
| council_minutes | None |  |
| agenda_packet | None |  |
| audit_export | None |  |
| configuration_export | None |  |
| portal_page | None |  |
| policy_document | None |  |
| court_filing | None |  |
| news_article | None |  |
| dataset | None |  |
| press_release | None |  |
| presentation | None |  |
| email | None |  |
| photograph | None |  |
| osm_element | None |  |
| radio_observation | None |  |
| budget | None |  |
| grant_award | None |  |
| statute | None |  |
| regulation | None |  |
| screenshot | None |  |
| state_auditor_survey | None | A state auditor's periodic survey of agency surveillance-technology holdings ... |
| warrant | None | A warrant artifact (§23 |
| procurement_aggregator_record | None | A record from the paywalled commercial procurement aggregator carried under a... |
| other | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [artifact_type](../slots/artifact_type.md) | The genre of the artifact (§10 |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: ArtifactType
description: The genre of an evidence artifact (§10.3.2). SIG-INGEST-047 additionally
  carries state_auditor_survey, warrant, and procurement_aggregator_record (§23.6)
  — the state-auditor surveys are R1 government datasets and the aggregator record
  is the paywalled procurement-aggregator lead under a LINK custody posture.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  contract:
    text: contract
  invoice:
    text: invoice
  council_minutes:
    text: council_minutes
  agenda_packet:
    text: agenda_packet
  audit_export:
    text: audit_export
  configuration_export:
    text: configuration_export
  portal_page:
    text: portal_page
  policy_document:
    text: policy_document
  court_filing:
    text: court_filing
  news_article:
    text: news_article
  dataset:
    text: dataset
  press_release:
    text: press_release
  presentation:
    text: presentation
  email:
    text: email
  photograph:
    text: photograph
  osm_element:
    text: osm_element
  radio_observation:
    text: radio_observation
  budget:
    text: budget
  grant_award:
    text: grant_award
  statute:
    text: statute
  regulation:
    text: regulation
  screenshot:
    text: screenshot
  state_auditor_survey:
    text: state_auditor_survey
    description: A state auditor's periodic survey of agency surveillance-technology
      holdings — an R1 government dataset (§23.6, SIG-INGEST-047).
  warrant:
    text: warrant
    description: A warrant artifact (§23.6, SIG-INGEST-047).
  procurement_aggregator_record:
    text: procurement_aggregator_record
    description: A record from the paywalled commercial procurement aggregator carried
      under a LINK custody posture (§23.6, SIG-INGEST-047).
  other:
    text: other

```
</details>

</div>