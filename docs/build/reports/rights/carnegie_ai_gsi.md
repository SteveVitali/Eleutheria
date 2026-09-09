# Rights-review packet — `carnegie_ai_gsi` (Carnegie AI Global Surveillance Index)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `carnegie_ai_gsi`
- **Homepage:** https://carnegieendowment.org/publications/interactive/ai-surveillance
- **Terms URL(s):** https://carnegieendowment.org/terms — **not fetched this pass**
- **robots.txt:** honor — not fetched this pass.

## Terms (verbatim)

> **Not fetched this pass.** The AI Global Surveillance (AIGS) Index is a
> Carnegie Endowment for International Peace research publication indexing which
> countries deploy AI surveillance. It is a **country-level** index. Carnegie's site
> content is under its own copyright/terms; the reviewer must confirm whether the
> underlying index dataset is separately licensed and record the terms verbatim.

## SPDX candidate

`UNDETERMINED` (accepted expressions per `policy/data/licenses.toml`).

## redistributable analysis

Separately reviewed (SIG-LIC-003). Coarse **country-level** aggregates only; ingested at
explicit coarse granularity and **never disaggregated to agency level** (§22.7,
SIG-INGEST-042, RISK-P0-08 / P4). redistributable=UNDETERMINED pending review.

## derivative_permitted analysis

SIG would produce country-level claims labelled with the source's granularity; no finer
inference is permitted. derivative_permitted=UNDETERMINED pending review.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

**LINK** — keep link-only until a rights review + operator flip. The REFERENCE-capture
path (`connectors.coarse_international`, P21.8) runs the moment a row is flipped; until
then the loader gate refuses a live fetch (exit 3).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: ____   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**YES — SIG-LIC-009:** confirm the AIGS Index licence/terms before any flip; a recorded
reviewer role is not a legal opinion.
