# Research Cache Conventions

Every research file in `docs/research/` follows this structure so the synthesis pass can
consume them mechanically.

## File header (required)

```markdown
# R<n> — <Workstream title>

**Workstream:** R<n>
**Researched:** <ISO date>
**Researcher:** <agent id>
**Outline sections covered:** <list of § from docs/1_deep_research_overview.md>
**Outline questions answered:** <list of Q## from §20, if any>
**Confidence in this file overall:** high | medium | low
```

## Finding format (required for every material claim)

Each finding is a numbered subsection:

```markdown
### F<n>.<m> — <short claim>

**Claim:** <one sentence>
**Status:** VERIFIED | PARTIALLY VERIFIED | UNVERIFIED | CONTRADICTED | INACCESSIBLE
**Evidence:** <URL(s) actually fetched, with what they said>
**Retrieved:** <ISO date>
**Implication for the spec:** <what the design must do about it>
**Outline delta:** CONFIRMS | CORRECTS | EXTENDS | CONTRADICTS §<x> of the outline — <detail>
```

## Rules

1. **Never assert access you did not test.** If a fetch 403s / 404s / requires JS, record
   `INACCESSIBLE` with the exact failure, and record what the fallback is.
2. **Record the exact URL that worked**, not the one you hoped would work.
3. **Corrections to the outline are the highest-value output.** Flag every one explicitly
   under `Outline delta:`.
4. **Licensing / terms-of-use findings are mandatory** for every external data source: record
   license name, URL of the license statement, attribution requirement, redistribution
   permission, and whether you actually saw the terms or inferred them.
5. **End every file** with:
   - `## Open questions` — what could not be resolved and how the spec should hedge.
   - `## Spec requirements emitted` — a numbered list of concrete, testable requirements
     this workstream contributes to `docs/2_canonical_design_spec.md`, each tagged with a
     stable id `REQ-R<n>-<mm>`.
