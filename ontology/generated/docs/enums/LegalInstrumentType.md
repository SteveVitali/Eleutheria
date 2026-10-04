---
search:
  boost: 2.0
---


# Enum: LegalInstrumentType 




_Legal instrument type, internationalized and country-namespaced (§11.14, §13.7, SIG-ONTO-068). The dotless terms are the shared abstract parents; national instruments are `<cc>.*` children linked by `is_a`, added under a national namespace rather than by widening a US-shaped enum (§5.3). P18.2 is the first consumer (the French arrêté préfectoral / CNIL decision)._



<div data-search-exclude markdown="1">

URI: [sig:enum/LegalInstrumentType](https://ontology.sig-project.org/schema/enum/LegalInstrumentType)

## Permissible Values
| Value | Meaning | Description | Additional Info |
| --- | --- | --- | --- |
| statute | None |  ||
| ordinance | None |  ||
| regulation | None |  ||
| executive_order | None |  ||
| court_order | None |  ||
| consent_decree | None |  ||
| dpa_decision | None | A data-protection authority decision (abstract parent) ||
| code_of_practice | None |  ||
| prefectoral_order | None | A prefectoral order (abstract parent); e ||
| directive | None |  ||
| fr.arrete_prefectoral | None | France — arrêté préfectoral (the published authorization instrument, §52 Phas... | Is-A: NONE<br>|
| fr.cnil_decision | None | France — a CNIL (data-protection authority) decision | Is-A: NONE<br>|
| uk.surveillance_camera_code | None | United Kingdom — the Surveillance Camera Code of Practice | Is-A: NONE<br>|
| eu.ai_act | None | European Union — an EU AI Act obligation | Is-A: NONE<br>|
| de.landesdatenschutzgesetz | None | Germany — a Land data-protection statute | Is-A: NONE<br>|
| be.loi_cameras | None | Belgium — loi caméras (21 March 2007) governing installation and use of surve... | Is-A: NONE<br>|













## Identifier and Mapping Information





### Schema Source


* from schema: https://ontology.sig-project.org/schema/sig






## LinkML Source

<details>
```yaml
name: LegalInstrumentType
description: Legal instrument type, internationalized and country-namespaced (§11.14,
  §13.7, SIG-ONTO-068). The dotless terms are the shared abstract parents; national
  instruments are `<cc>.*` children linked by `is_a`, added under a national namespace
  rather than by widening a US-shaped enum (§5.3). P18.2 is the first consumer (the
  French arrêté préfectoral / CNIL decision).
from_schema: https://ontology.sig-project.org/schema/sig
rank: 1000
permissible_values:
  statute:
    text: statute
  ordinance:
    text: ordinance
  regulation:
    text: regulation
  executive_order:
    text: executive_order
  court_order:
    text: court_order
  consent_decree:
    text: consent_decree
  dpa_decision:
    text: dpa_decision
    description: A data-protection authority decision (abstract parent).
  code_of_practice:
    text: code_of_practice
  prefectoral_order:
    text: prefectoral_order
    description: A prefectoral order (abstract parent); e.g. a French arrêté préfectoral.
  directive:
    text: directive
  fr.arrete_prefectoral:
    text: fr.arrete_prefectoral
    description: France — arrêté préfectoral (the published authorization instrument,
      §52 Phase 18).
    is_a: prefectoral_order
  fr.cnil_decision:
    text: fr.cnil_decision
    description: France — a CNIL (data-protection authority) decision.
    is_a: dpa_decision
  uk.surveillance_camera_code:
    text: uk.surveillance_camera_code
    description: United Kingdom — the Surveillance Camera Code of Practice.
    is_a: code_of_practice
  eu.ai_act:
    text: eu.ai_act
    description: European Union — an EU AI Act obligation.
    is_a: regulation
  de.landesdatenschutzgesetz:
    text: de.landesdatenschutzgesetz
    description: Germany — a Land data-protection statute.
    is_a: statute
  be.loi_cameras:
    text: be.loi_cameras
    description: Belgium — loi caméras (21 March 2007) governing installation and
      use of surveillance cameras.
    is_a: statute

```
</details>

</div>