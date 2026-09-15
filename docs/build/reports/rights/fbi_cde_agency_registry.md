# Rights-review packet — `fbi_cde_agency_registry` (FBI Crime Data Explorer / data.gov)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.
> Drafted 2026-09-15 in the B rights-review pass (the packet did not exist before).

- **Source id:** `fbi_cde_agency_registry`
- **Homepage:** https://crime-data-explorer.fr.cloud.gov/ (data served via the data.gov API gateway)
- **Terms URL(s) fetched:** api.data.gov key signup terms — the data.gov API is a public
  federal service; the staged `SIG_DATA_GOV_KEY` is this source's key (P25.4 wiring).
- **robots.txt:** honor — API-mode access per ADR-083 (hosts `api.data.gov` and
  `catalog.data.gov` on the allow-list; `counsel_reviewed = false`).

## Terms (verbatim)

> The FBI Crime Data Explorer agency/ORI registry is a work of the U.S. federal
> government (FBI / CJIS). U.S. Government works are not subject to domestic copyright
> protection (17 U.S.C. §105); the data are in the public domain, served through the
> documented data.gov API under its published rate-limit policy. The api.data.gov
> signup terms require only an identifiable application and adherence to rate limits.
> This packet records that fact; the SPDX expression is a reviewer decision.

## SPDX candidate

`CC0-1.0 candidate (US-PD)` (accepted expressions per `policy/data/licenses.toml`) —
the same disposition as `usaspending`.

## redistributable analysis

U.S. federal public-domain ⇒ freely redistributable. → registry `redistributable = true`
on the reviewer's flip.

## derivative_permitted analysis

No copyright ⇒ no derivative restriction. Agency-registry rows (ORI, agency name,
jurisdiction) feed P03.2's identity crosswalk — a lookup table, no linking hazard.

## ODbL compartment implications

Not OSM-derived. CC0/US-PD relicensable into any compartment.

## Custody posture recommendation

**REFERENCE** — the ORI→agency registry as reference data. Code gap: the data.gov-key
auth wiring is P25.4; possessing the key is not the rights basis — the §105
public-domain posture is.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated), operator-approved 2026-09-15 (B pass)
- SPDX to record: `CC0-1.0`   rights_reviewed_by (role, never a name): maintainer (delegated)   rights_reviewed_on: 2026-09-15

## Counsel-needed flag

**LOW — U.S. federal public-domain works; the reviewer confirms the SPDX expression
(CC0-1.0) per licenses.toml.**
