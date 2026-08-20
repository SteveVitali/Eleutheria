## 20. Ontology, vocabulary, and schema versioning

The ontology *will* change. A surveillance-technology taxonomy written in 2026 will be wrong by
2029. The requirement is not stability; it is that change never invalidates or silently rewrites
history.

### 20.1 One source of truth

**SIG-STORE-034 (MUST).** The ontology MUST be authored in **LinkML** and MUST generate JSON
Schema, OWL/SHACL, Python dataclasses/Pydantic, SQL DDL scaffolding, and documentation from one
YAML source. CI MUST fail if committed generated artifacts differ from a fresh generation.
*(REQ-R6-44; R6-F50.)*

Rationale: SIG must publish its schema in at least five forms for five audiences (SQL for
implementers, JSON Schema for API consumers, OWL/SHACL for semantic-web reuse, Pydantic for its
own pipeline, prose for humans). Hand-maintaining five forms guarantees drift; drift in a schema
that carries epistemic semantics is a correctness bug, not a documentation bug.

### 20.2 Published vocabularies

**SIG-STORE-035 (MUST).** Controlled vocabularies MUST be published as **versioned SKOS concept
schemes** with stable per-version IRIs, and each published version MUST be archived in the
evidence store. *(REQ-R6-46; R6-F51.)*

**SIG-STORE-036 (MUST).** Vocabulary terms MUST be **immutable once published**. Corrections
deprecate and supersede; they never redefine. *(REQ-R6-47.)* Redefining `surveillance_type:alpr`
in 2029 would retroactively change the meaning of every claim made under it — the silent
overwrite the defining standard forbids, executed at maximum blast radius.

**SIG-STORE-037 (MUST).** Vocabulary changes MUST ship with crosswalk rows using SKOS mapping
relations (`exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`) and an
explicit **`lossy` flag**. Queries traversing a lossy crosswalk MUST propagate that flag into
result metadata. *(REQ-R6-48.)*

**SIG-STORE-038 (MUST NOT).** Historical claims MUST NOT be rewritten to a newer vocabulary. Bulk
re-classification, where warranted, MUST be performed as **new claims** with
`extraction_method = 'vocabulary_migration'` and `revises_claim` links. *(REQ-R6-49.)*

### 20.3 Crosswalks to external taxonomies

**SIG-STORE-039 (MUST).** SIG MUST maintain published crosswalks from its own technology
vocabulary to every external taxonomy it ingests, at minimum: EFF Atlas categories, EFF
Street-Level Surveillance topics, ALPR Accountability Atlas issue categories, OSM
`surveillance:type` / `surveillance` / `camera:type` values, CCOPS inventory categories, and the
French Technopolice vocabulary. *(Discharges OL-10.1C-02 — "do not overwrite Atlas taxonomy
blindly; create mappings".)*

**SIG-STORE-040 (MUST).** Each crosswalk row MUST carry the mapping relation and the `lossy`
flag. Mapping Atlas's single "Automated License Plate Readers" category onto SIG's finer ALPR
family is `broadMatch` and lossy; asserting `exactMatch` would fabricate precision.

### 20.4 Physical migrations

**SIG-STORE-041 (MUST).** Physical schema migrations MUST be managed with **sqitch**, with
`deploy`, `revert`, and `verify` scripts for every change. Migrations touching `claim` MUST be
**additive**. *(REQ-R6-45; R6-F49.)*

**SIG-STORE-042 (MUST).** A migration that would drop or retype a `claim` column MUST instead add
a new column and a migration claim-set, and MUST be reviewed as an ADR. There is no in-place
rewrite path for the claim table, by design.

### 20.5 Outward identifiers

**SIG-STORE-043 (MUST).** SIG entities MUST carry outward-linkable identifiers **as claims with
provenance**, not as bare columns: Wikidata QIDs, ORI codes, GEOIDs, LEIs, UEIs, OSM element
refs, upstream project ids. *(REQ-R6-50; discharges OL-Q37, OL-24-08.)*

**SIG-STORE-044 (MUST).** Wikidata QIDs SHOULD be treated as a **first-class** crosswalk
identifier rather than an optional one. Measurement justifies this: `manufacturer:wikidata` is
present on **83.4%** of the world's mapped ALPRs and `operator:wikidata` on 12.3% (SC-08.2). The
OSM community has already performed vendor entity resolution and published it; inheriting it is
free precision, and it gives SIG an immediate, neutral join key to a general-purpose identifier
hub.

---
