# Rights-review packet — `usaspending` (USAspending)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `usaspending`
- **Homepage:** https://api.usaspending.gov/
- **Terms URL(s):** https://api.usaspending.gov/docs/
- **robots.txt:** honor (public REST API; api.data.gov-style etiquette; §26).

## Terms (verbatim)

> Fetched from https://api.usaspending.gov/ on 2026-09-09 (API landing page,
> not award content — permitted research):
>
> "The USAspending API (Application Programming Interface) allows the public to access
> comprehensive U.S. government spending data."
>
> "The U.S. Department of the Treasury is building a suite of open-source tools to help
> federal agencies comply with the DATA Act and to deliver the resulting standardized
> federal spending information back to agencies and to the public."
>
> USAspending is a work of the U.S. federal government published under the DATA Act
> (Pub. L. 113-101). U.S. Government works are not subject to domestic copyright
> protection (17 U.S.C. §105); the data are in the public domain. This packet records
> that fact; the SPDX expression is a reviewer decision (see Decision).

## SPDX candidate

`CC0-1.0 candidate (US-PD)`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

U.S. Government works are not subject to domestic copyright (17 U.S.C. §105) ⇒ public domain ⇒ freely redistributable. This packet records the FACT; the registry row is still UNDETERMINED (no rights block) — adding the block is the reviewer's flip decision (see Decision).  → registry `redistributable = true`.

## derivative_permitted analysis

No copyright ⇒ no derivative restriction. A reviewer flip would set derivative_permitted=true.  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. CC0/US-PD relicensable into any compartment.

## Custody posture recommendation

REFERENCE (prime + sub-awards; federal_award_id tracing). The one source ever fetched live (P07.3, LD-X08) — that trace ran outside the loader gate; a flip closes that gap.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `CC0-1.0 candidate (US-PD)`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**LOW — U.S. federal public-domain works; reviewer confirms the SPDX expression (CC0-1.0 vs US-PD) per licenses.toml (CC0-1.0 is the accepted expression).**
