# Rights-review packet — `dot_511_mo` (MoDOT traffic-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `dot_511_mo`
- **Homepage:** https://services2.arcgis.com/jWXb6JPWtBjOCalT/arcgis/rest/services/MODOT_Traffic_Cameras/FeatureServer/1 — **the camera layer is FeatureServer/1, not /0** (layer 0 does not exist; `/1` = "MODOT Traffic Cameras As HFS", 871 features).
- **Terms URL(s) fetched:** https://www.arcgis.com/sharing/rest/content/items/38774183927d423488f9e2e707a6eca5 (item metadata, owner `creaml_MOSEMA` — Missouri state org) + Missouri Terms of Use — retrieved 2026-09-17.
- **robots.txt:** honor — `services2.arcgis.com/robots.txt` answers 403 (no policy — ADR-087). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> Missouri's Terms of Use: the user agrees to stated conditions; the state disclaims
> completeness/accuracy warranties and reserves the right to modify or discontinue
> feeds and to require termination of use — a **conditional public grant**:
> access is offered, conditioned on the stated terms, revocable at the publisher's
> option. Evaluated under the published public terms — no outreach was performed
> (Stage-0 record: `public_terms_only`).

## SPDX candidate

`CC0-1.0` — state public record; the conditions govern *continued access*, not the records' redistribution.

## redistributable analysis

State public record published for public use; no redistribution bar asserted. → `redistributable = true`.

## derivative_permitted analysis

No condition on derivatives asserted. → `derivative_permitted = true`.

## Condition compliance (recorded)

- **Revocation clause:** honoured — append-only claims persist as evidence; new
  fetches stop on restriction.
- **Accuracy disclaimer:** honoured by the evidence model itself — claims cite the
  source row verbatim and never assert more than the evidence carries.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-17
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-17

## Counsel-needed flag

**PARTIAL — resolved under GL-GATE-06 as a conditional public grant; if Missouri's terms are later read as withholding redistribution permission, the row reverts to gated pending HG-03.**
