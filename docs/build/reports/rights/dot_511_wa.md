# Rights-review packet — `dot_511_wa` (WSDOT travel-information cameras)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_wa`
- **Homepage:** https://data.wsdot.wa.gov/arcgis/rest/services/TravelInformation/TravelInfoCamerasWeather/FeatureServer/0
- **Terms URL(s) fetched:** WSDOT ArcGIS service access information + item `f562fc9a382549c68093b664d000dc15` — retrieved 2026-09-17.
- **robots.txt:** honor — `data.wsdot.wa.gov/robots.txt` answers 404 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> WSDOT's access information describes the feed as **"intended for low volume use"**
> and reserves that **"WSDOT may cancel or restrict access"** — a conditional public
> grant: access is offered, conditioned on low-volume consumption, revocable at the
> publisher's option. The grant is evaluated under the published public terms — no
> outreach was performed (Stage-0 record: `public_terms_only`), so
> `compact_status` records the public-terms posture, not a fabricated permission.

## SPDX candidate

`CC0-1.0` — state public record; the condition is an *access* condition (volume), not a restriction on the records' redistribution.

## redistributable analysis

State public record published for public use; no redistribution bar asserted. → `redistributable = true`.

## derivative_permitted analysis

No condition on derivatives asserted. → `derivative_permitted = true`.

## Condition compliance (recorded)

- **Low volume:** the source's cadence row is **monthly** (`ops/cadence.toml`,
  `0 6 26 * *`) — well under any reasonable reading of "low volume use"; the shared
  politeness layer rate-limits regardless.
- **Revocation:** append-only claims already emitted persist as evidence; new fetches
  stop the moment the publisher restricts access — the honour system plus the gate
  make revocation self-executing.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR — registry rows only. Two layers in scope: the WSDOT-hosted feed (1,705 rows)
and the King County–hosted KC/WSDOT layer (125 rows), both enumerated in
`data/dot_511_targets.toml`.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**PARTIAL — resolved under GL-GATE-06 as a conditional public grant whose recorded condition (low-volume monthly pull) is satisfied; if WSDOT's wording is later read as requiring affirmative permission, the row reverts to gated pending HG-03.**
