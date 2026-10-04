---
search:
  boost: 2.0
---


# Enum: JurisdictionType 




_Jurisdiction type, namespaced per country (§11.1, §13.7, SIG-ONTO-068). The dotless terms are the shared abstract levels every country's hierarchy maps onto; national levels are `<cc>.*` children linked by `is_a`, so a new country plugs its own level names in without widening a US-shaped enum._



<div data-search-exclude markdown="1">

URI: [sig:enum/JurisdictionType](https://ontology.sig-project.org/schema/enum/JurisdictionType)

## Permissible Values
| Value | Meaning | Description | Additional Info |
| --- | --- | --- | --- |
| country | None |  ||
| state_province | None |  ||
| county | None |  ||
| municipality | None |  ||
| township | None |  ||
| special_district | None |  ||
| school_district | None |  ||
| tribal | None |  ||
| federal_region | None |  ||
| judicial_district | None |  ||
| metropolitan_area | None |  ||
| neighborhood | None |  ||
| unincorporated_area | None |  ||
| fr.region | None | France — région | Is-A: NONE<br>|
| fr.departement | None | France — département | Is-A: NONE<br>|
| fr.commune | None | France — commune | Is-A: NONE<br>|
| fr.epci | None | France — EPCI (intercommunal grouping); a non-tree overlapping parent | Is-A: NONE<br>|
| uk.police_force_area | None | United Kingdom — police force area (a non-tree operational grouping) | Is-A: NONE<br>|
| de.bundesland | None | Germany — Bundesland (state) | Is-A: NONE<br>|
| de.kreis | None | Germany — Kreis (district) | Is-A: NONE<br>|
| de.gemeinde | None | Germany — Gemeinde (municipality) | Is-A: NONE<br>|
| be.region | None | Belgium — région / gewest (Brussels-Capital, Flanders, Wallonia) | Is-A: NONE<br>|
| be.province | None | Belgium — province | Is-A: NONE<br>|
| be.commune | None | Belgium — commune / gemeente | Is-A: NONE<br>|
| be.police_zone | None | Belgium — zone de police locale (a non-tree operational grouping of communes) | Is-A: NONE<br>|




## Slots

| Name | Description |
| ---  | --- |
| [jurisdiction_type](../slots/jurisdiction_type.md) |  |










## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: JurisdictionType
description: Jurisdiction type, namespaced per country (§11.1, §13.7, SIG-ONTO-068).
  The dotless terms are the shared abstract levels every country's hierarchy maps
  onto; national levels are `<cc>.*` children linked by `is_a`, so a new country plugs
  its own level names in without widening a US-shaped enum.
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  country:
    text: country
  state_province:
    text: state_province
  county:
    text: county
  municipality:
    text: municipality
  township:
    text: township
  special_district:
    text: special_district
  school_district:
    text: school_district
  tribal:
    text: tribal
  federal_region:
    text: federal_region
  judicial_district:
    text: judicial_district
  metropolitan_area:
    text: metropolitan_area
  neighborhood:
    text: neighborhood
  unincorporated_area:
    text: unincorporated_area
  fr.region:
    text: fr.region
    description: France — région.
    is_a: state_province
  fr.departement:
    text: fr.departement
    description: France — département.
    is_a: county
  fr.commune:
    text: fr.commune
    description: France — commune.
    is_a: municipality
  fr.epci:
    text: fr.epci
    description: France — EPCI (intercommunal grouping); a non-tree overlapping parent.
    is_a: metropolitan_area
  uk.police_force_area:
    text: uk.police_force_area
    description: United Kingdom — police force area (a non-tree operational grouping).
    is_a: special_district
  de.bundesland:
    text: de.bundesland
    description: Germany — Bundesland (state).
    is_a: state_province
  de.kreis:
    text: de.kreis
    description: Germany — Kreis (district).
    is_a: county
  de.gemeinde:
    text: de.gemeinde
    description: Germany — Gemeinde (municipality).
    is_a: municipality
  be.region:
    text: be.region
    description: Belgium — région / gewest (Brussels-Capital, Flanders, Wallonia).
    is_a: state_province
  be.province:
    text: be.province
    description: Belgium — province.
    is_a: county
  be.commune:
    text: be.commune
    description: Belgium — commune / gemeente.
    is_a: municipality
  be.police_zone:
    text: be.police_zone
    description: Belgium — zone de police locale (a non-tree operational grouping
      of communes).
    is_a: special_district

```
</details>

</div>