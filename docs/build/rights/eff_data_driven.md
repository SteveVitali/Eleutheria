# Rights-review packet — `eff_data_driven` (EFF/MuckRock Data Driven release)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `eff_data_driven`
- **Homepage:** https://www.eff.org/deeplinks/2018/11/eff-and-muckrock-release-records-and-data-200-law-enforcement-agencies-automated
- **Terms URL(s):** https://www.eff.org/copyright — **not fetched this pass** (record for the reviewer)
- **robots.txt:** honor — not fetched this pass.

## Terms (verbatim)

> **Not fetched this pass.** The 2018 Data Driven release is a joint EFF/MuckRock
> publication of records and data on ~200 law enforcement agencies' automated
> licence-plate reader use. EFF's site content is generally CC BY (see `eff_copyright`
> / `eff_atlas_of_surveillance`), but the Data Driven **data files** are compiled from
> agency public-records responses obtained through MuckRock FOIA requests, and the
> per-artifact licence of the underlying records is not stated on the release page.
> The reviewer must confirm the licence of the **data file artifacts** (SIG-INGEST-043b:
> the article URL is a dead end with no data links; the data lives at separate file
> paths) rather than assuming the site-wide CC BY applies to the compiled dataset.

## SPDX candidate

`UNDETERMINED` (accepted expressions per `policy/data/licenses.toml`). Candidate on
confirmation: `CC-BY-4.0` for the EFF compilation layer; the underlying agency records
are US-government public records (no copyright reservation) but MuckRock's compilation /
hosting terms must be checked.

## redistributable analysis

Separately reviewed; **not** derived from the SPDX string (SIG-LIC-003). The corpus is
ingested as **per-agency aggregates only** (§23.9, §18.1, RISK-P0-08): even if the
compiled data is redistributable, SIG re-publishes only aggregate scan/hit/degree/
retention figures, never per-search/per-plate/per-person rows and never a sharing edge
list (SIG-INGEST-043c). redistributable=UNDETERMINED pending review.

## derivative_permitted analysis

Aggregation + historical claim extraction is the derivative SIG produces. No SIG-INGEST-048b
linking hazard: sharing is recorded as **degree only**, so no operator-joinable edge
surface is created. derivative_permitted=UNDETERMINED pending review.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

**MIRROR** candidate — the release is a static, dated historical artifact worth
mirroring (content-addressed per release version, SIG-INGEST-043b). Registry row set to
`custody_posture = MIRROR`, `ingestion_permitted` false until this packet is decided.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: ____   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**PARTIAL — SIG-LIC-009:** confirm the licence of the compiled **data file artifacts**
(distinct from EFF's site-wide CC BY) and MuckRock's hosting/compilation terms; a recorded
reviewer role is not a legal opinion. MuckRock is the **co-publisher** of this joint
release, not a distinct registry source (the `muckrock` row is the live records-API
channel, a different thing — ADR-070).
