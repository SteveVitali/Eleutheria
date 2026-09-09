# Rights-review packet — `aspi_mapping_chinas_tech_giants` (ASPI Mapping China's Tech Giants)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `aspi_mapping_chinas_tech_giants`
- **Homepage:** https://chinatechmap.aspi.org.au/
- **Terms URL(s):** https://www.aspi.org.au/copyright — **not fetched this pass**
- **robots.txt:** honor — not fetched this pass.

## Terms (verbatim)

> **Not fetched this pass.** The Australian Strategic Policy Institute's "Mapping
> China's Tech Giants" is a **vendor-level** dataset tracking Chinese technology
> companies' global footprint. ASPI publishes copyright/terms on its site; some ASPI
> datasets are offered under Creative Commons. The reviewer must fetch the terms and
> record the verbatim licence, and confirm whether the map dataset itself is CC-licensed.

## SPDX candidate

`UNDETERMINED` (accepted expressions per `policy/data/licenses.toml`). Candidate on
confirmation: a Creative Commons expression if ASPI states one for the dataset.

## redistributable analysis

Separately reviewed (SIG-LIC-003). Coarse **vendor-level** aggregates only (an
Organization bearing the vendor role, §12.4); ingested at explicit coarse granularity and
**never disaggregated to agency/deployment level** (§22.7, SIG-INGEST-042, RISK-P0-08 /
P4). redistributable=UNDETERMINED pending review.

## derivative_permitted analysis

Vendor-in-country claims labelled with the source's granularity; no finer inference.
derivative_permitted=UNDETERMINED pending review.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

**LINK** — keep link-only until a rights review + operator flip. The REFERENCE-capture
path (`connectors.coarse_international`, P21.8) runs on a flip; the loader gate refuses a
live fetch (exit 3) until then.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: ____   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**YES — SIG-LIC-009:** confirm the ASPI dataset licence/terms before any flip; a recorded
reviewer role is not a legal opinion.
