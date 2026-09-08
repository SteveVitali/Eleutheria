---
search:
  boost: 2.0
---


# Enum: OrganizationType 




_Organization type, namespaced and extensible (§11.2, §13.7, SIG-ONTO-068). "vendor" is a ROLE, not a subtype (SIG-ONTO-012); it appears here only as an organization-classification convenience and never specializes the entity. `law_enforcement` is the shared abstract parent every country's police-force types map onto; national forces are `<cc>.*` children linked by `is_a`, added under a national namespace rather than by widening the `us.*` set._



<div data-search-exclude markdown="1">

URI: [sig:enum/OrganizationType](https://ontology.sig-project.org/schema/enum/OrganizationType)

## Permissible Values
| Value | Meaning | Description | Additional Info |
| --- | --- | --- | --- |
| law_enforcement | None | Abstract parent of every country's law-enforcement organization types (SIG-ON... ||
| government | None | Abstract parent of every country's civil-government body types (SIG-ONTO-068) ||
| us.le.municipal_police | None |  | Is-A: NONE<br>|
| us.le.sheriff | None |  | Is-A: NONE<br>|
| us.le.state_police | None |  | Is-A: NONE<br>|
| us.le.university_police | None |  | Is-A: NONE<br>|
| us.le.transit_police | None |  | Is-A: NONE<br>|
| us.le.school_district_police | None |  | Is-A: NONE<br>|
| us.le.tribal_police | None |  | Is-A: NONE<br>|
| us.le.federal | None |  | Is-A: NONE<br>|
| us.gov.municipality | None |  | Is-A: NONE<br>|
| us.gov.county | None |  | Is-A: NONE<br>|
| us.gov.special_district | None |  | Is-A: NONE<br>|
| us.fusion_center | None |  | Is-A: NONE<br>|
| private.company | None |  ||
| private.hoa | None |  ||
| private.security_firm | None |  ||
| private.bid | None |  ||
| nonprofit | None |  ||
| hospital | None |  ||
| university | None |  ||
| school_district | None |  ||
| utility | None |  ||
| transit_agency | None |  ||
| vendor | None |  ||
| data_broker | None |  ||
| fr.police_municipale | None | France — police municipale | Is-A: NONE<br>|
| fr.gendarmerie | None | France — gendarmerie nationale | Is-A: NONE<br>|
| uk.territorial_police | None | United Kingdom — a territorial police force | Is-A: NONE<br>|
| de.landespolizei | None | Germany — a Land police force | Is-A: NONE<br>|




## Slots

| Name | Description |
| ---  | --- |
| [organization_type](../slots/organization_type.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: OrganizationType
description: Organization type, namespaced and extensible (§11.2, §13.7, SIG-ONTO-068).
  "vendor" is a ROLE, not a subtype (SIG-ONTO-012); it appears here only as an organization-classification
  convenience and never specializes the entity. `law_enforcement` is the shared abstract
  parent every country's police-force types map onto; national forces are `<cc>.*`
  children linked by `is_a`, added under a national namespace rather than by widening
  the `us.*` set.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  law_enforcement:
    text: law_enforcement
    description: Abstract parent of every country's law-enforcement organization types
      (SIG-ONTO-068).
  government:
    text: government
    description: Abstract parent of every country's civil-government body types (SIG-ONTO-068).
  us.le.municipal_police:
    text: us.le.municipal_police
    is_a: law_enforcement
  us.le.sheriff:
    text: us.le.sheriff
    is_a: law_enforcement
  us.le.state_police:
    text: us.le.state_police
    is_a: law_enforcement
  us.le.university_police:
    text: us.le.university_police
    is_a: law_enforcement
  us.le.transit_police:
    text: us.le.transit_police
    is_a: law_enforcement
  us.le.school_district_police:
    text: us.le.school_district_police
    is_a: law_enforcement
  us.le.tribal_police:
    text: us.le.tribal_police
    is_a: law_enforcement
  us.le.federal:
    text: us.le.federal
    is_a: law_enforcement
  us.gov.municipality:
    text: us.gov.municipality
    is_a: government
  us.gov.county:
    text: us.gov.county
    is_a: government
  us.gov.special_district:
    text: us.gov.special_district
    is_a: government
  us.fusion_center:
    text: us.fusion_center
    is_a: government
  private.company:
    text: private.company
  private.hoa:
    text: private.hoa
  private.security_firm:
    text: private.security_firm
  private.bid:
    text: private.bid
  nonprofit:
    text: nonprofit
  hospital:
    text: hospital
  university:
    text: university
  school_district:
    text: school_district
  utility:
    text: utility
  transit_agency:
    text: transit_agency
  vendor:
    text: vendor
  data_broker:
    text: data_broker
  fr.police_municipale:
    text: fr.police_municipale
    description: France — police municipale.
    is_a: law_enforcement
  fr.gendarmerie:
    text: fr.gendarmerie
    description: France — gendarmerie nationale.
    is_a: law_enforcement
  uk.territorial_police:
    text: uk.territorial_police
    description: United Kingdom — a territorial police force.
    is_a: law_enforcement
  de.landespolizei:
    text: de.landespolizei
    description: Germany — a Land police force.
    is_a: law_enforcement

```
</details>

</div>