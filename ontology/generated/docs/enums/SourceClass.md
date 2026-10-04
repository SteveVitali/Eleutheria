---
search:
  boost: 2.0
---


# Enum: SourceClass 




_The six evidence source classes of OL-2E-AL-03 (§11.17, SIG-ONTO-039). An accountability incident MUST be linkable to all six, with the class RECORDED on the evidence link, so a claim resting only on advocacy analysis is distinguishable from one resting on a court record. These are epistemic classes of the reporting, NOT the R1..R6 reliability tiers (§10.4)._



<div data-search-exclude markdown="1">

URI: [sig:enum/SourceClass](https://ontology.sig-project.org/schema/enum/SourceClass)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| primary_record | None | A primary document — the underlying record itself (a contract, a filing exhib... |
| court_record | None | A court/docket record — a filing, order, or docket entry (CourtListener/RECAP... |
| agency_statement | None | A statement by the agency involved (press release, official response, testimo... |
| vendor_statement | None | A statement by the vendor involved (product page, press response, spokesperso... |
| investigative_article | None | Investigative journalism reporting the incident |
| advocacy_analysis | None | Advocacy-organization analysis or a curated accountability index entry |




## Slots

| Name | Description |
| ---  | --- |
| [source_classes](../slots/source_classes.md) | The OL-2E-AL-03 class of each entry in `sources`, index-aligned (as `parties`... |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: SourceClass
description: The six evidence source classes of OL-2E-AL-03 (§11.17, SIG-ONTO-039).
  An accountability incident MUST be linkable to all six, with the class RECORDED
  on the evidence link, so a claim resting only on advocacy analysis is distinguishable
  from one resting on a court record. These are epistemic classes of the reporting,
  NOT the R1..R6 reliability tiers (§10.4).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  primary_record:
    text: primary_record
    description: A primary document — the underlying record itself (a contract, a
      filing exhibit, an incident report).
  court_record:
    text: court_record
    description: A court/docket record — a filing, order, or docket entry (CourtListener/RECAP).
  agency_statement:
    text: agency_statement
    description: A statement by the agency involved (press release, official response,
      testimony).
  vendor_statement:
    text: vendor_statement
    description: A statement by the vendor involved (product page, press response,
      spokesperson quote).
  investigative_article:
    text: investigative_article
    description: Investigative journalism reporting the incident.
  advocacy_analysis:
    text: advocacy_analysis
    description: Advocacy-organization analysis or a curated accountability index
      entry.

```
</details>

</div>