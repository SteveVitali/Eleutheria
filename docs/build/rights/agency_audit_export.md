# Rights-review packet — `agency_audit_export` (Agency Flock audit exports (public records))

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `agency_audit_export`
- **Homepage:** https://eleutheria.example/records/agency-audit-export
- **Terms URL(s):** https://eleutheria.example/records/agency-audit-export
- **robots.txt:** not_applicable (obtained as public records, not crawled).

## Terms (verbatim)

> UNDETERMINED — no resolved rights block in the registry (SIG-LIC-004; fails the
> export gate closed). This row models an agency's OWN Flock audit CSVs obtained as public records (not the derived HIBF bulk exports; SIG-INGEST-046a). The registry records CC0-1.0 as the posture for government-produced public records, but the records-release terms are agency-specific and were not fetched this pass.
>
> Terms were NOT fetched verbatim for this source this pass; the terms_url is
> recorded for the reviewer to fetch and quote before any flip. This packet makes
> no assertion about the licence (defining standard §3.1 — no synthetic certainty).

## SPDX candidate

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Government public records; CC0-1.0 posture recorded. redistributable=true, but audit CSVs carry PII-minimisation obligations (aggregates-only, §43.6) that are a DATA-HANDLING rule, separate from the rights posture.  → registry `redistributable = true`.

## derivative_permitted analysis

Derivatives permitted for the public-record data; structural aggregates only (N4/N9).  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR (structural aggregates only; never re-host plate-level detail).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `CC0-1.0`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**YES — public-records PII handling + the N4/N9 no-plate-level-search boundary.**
