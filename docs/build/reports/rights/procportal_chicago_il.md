# Rights-review packet — `procportal_chicago_il` (City of Chicago — Socrata 'Contracts')

> P26.10 (SOURCES.9) review 2026-09-18. Facts are separated from judgement; this
> packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `procportal_chicago_il`
- **Homepage:** https://data.cityofchicago.org/d/rsxa-ify5
- **Terms URL(s) fetched:** https://data.cityofchicago.org/api/views/rsxa-ify5 — retrieved 2026-09-18
- **robots.txt:** honor — `User-agent: *` / `Crawl-delay: 1`; only `/browse?*`
  faceted-search paths are disallowed — the documented `/resource/*.json` rows
  API is allowed. Robots is not the blocker here; the missing licence is.

## Terms (verbatim)

Dataset metadata (`/api/views/rsxa-ify5`, retrieved 2026-09-18):

> `name`: "Contracts" — `license`: **absent** (no `license`/`licenseId` field on
> the dataset record) — `attribution`: "City of Chicago"

Unlike the four flipped P26.10 Socrata datasets, this dataset carries NO
licence metadata — there is no verbatim dedication for the reviewer to
evaluate, so the GL-GATE-06 clear-licence basis does not apply. The city Terms
of Use were not captured verbatim this pass; this packet makes no licence
assertion (defining standard §3.1 — no synthetic certainty).

## SPDX candidate

`UNDETERMINED`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

Unreviewed — `redistributable = false` until a reviewer resolves the terms.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until a reviewer resolves the terms.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

LINK — municipal procurement records (awarded contracts/modifications since
1993). Verified surveillance-relevant rows exist ("VIDEO/SURVEILLANCE CAMERA
SERVICES", "VIDEO SURVEILLANCE MANAGEMENT SYSTEM") — the tenant row is
registered so a future flip needs no registry change; the gate refuses fetches
meanwhile.

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `UNDETERMINED`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

PENDING REVIEW (D-SOURCES.9-1) — gated on missing licence metadata: the city
Terms of Use must be captured verbatim and reviewed before any flip (HG-03
class). The source stays `ingestion_permitted=false`.
