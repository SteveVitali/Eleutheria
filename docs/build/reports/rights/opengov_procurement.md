# Rights-review packet — `opengov_procurement` (OpenGov Procurement — public agency solicitation portals)

> P26.2 skeleton → P26.10 (SOURCES.9) probe update 2026-09-18. Facts are separated
> from judgement; this packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `opengov_procurement`
- **Homepage:** https://procurement.opengov.com/
- **Terms URL(s) fetched:** none reachable — see access posture
- **robots.txt:** honor — `/robots.txt` returns HTTP 200 but serves the SPA HTML
  shell, not a robots policy (verified 2026-09-18). No `User-agent`/`Disallow`
  directives exist to evaluate; treated conservatively, not as permission.

## Access posture (verified 2026-09-18, SIG `procurement/1.0.0` UA)

Every probed `/portal/<agency>` path (salt-lake-city, boulder, austin, detroit,
sacramento, raleigh, fort-worth, scottsdale, tempe, oklahoma-city) answers
**HTTP 403 with `cf-mitigated: challenge`** — a Cloudflare managed challenge —
to programmatic requests (SIG UA and a stock browser UA alike). The challenge is
a recorded refusal/disappearance under SIG-INGEST-013 and is never defeated.

One tenant row (`salt_lake_city_ut`) is registered in
`data/procurement_portal_tenants.toml` to carry the recorded live outcome; the
remaining enumerated slugs are registry `platform_census` `waf_challenged` rows.

## Terms (verbatim)

> No terms document was reachable this pass — the challenge wall answers before
> any content does. This packet makes no assertion about the licence (defining
> standard §3.1 — no synthetic certainty).

## SPDX candidate

`UNDETERMINED`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Unreviewed — `redistributable = false` until a reviewer resolves the terms.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until a reviewer resolves the terms.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK — a per-agency public solicitation portal platform (records/procurement
surface), currently unreachable to automated review.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `UNDETERMINED`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

PENDING REVIEW (D-SOURCES.9-3) — gated twice over: (1) the WAF challenge makes
the surface unreachable to automated fetch (a recorded outcome, never defeated),
and (2) no terms or licence text was reachable to review. The source stays
`ingestion_permitted=false` until a legitimate, documented public path and
reviewed terms exist (HG-03 class).
