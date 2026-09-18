# Rights-review packet — `camreg_austin_tx` (Austin traffic-camera registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_austin_tx`
- **Homepage:** https://datahub.austintexas.gov/d/b4k4-adkb
- **Terms URL(s) fetched:** https://api.us.socrata.com/api/catalog/v1?domains=datahub.austintexas.gov&ids=b4k4-adkb — retrieved 2026-09-18 (Socrata catalog metadata for the dataset, owner City of Austin Transportation and Public Works).
- **robots.txt:** honor — `datahub.austintexas.gov/robots.txt` answers 200; `/resource/*` is not disallowed (only browse/catalog/odata paths are). API MODE under the recorded `api_allowlist.toml` entry.

## Terms (verbatim)

> The dataset's Socrata metadata declares licence **"Public Domain"** on the
> catalog record (dataset `b4k4-adkb` 'Traffic Cameras').

## SPDX candidate

`CC0-1.0` — the SIG expression for a public-domain dedication (the P26.7 DOT public-record precedent).

## redistributable analysis

Public Domain dedication: no licence conditions restrict redistribution. → `redistributable = true`.

## derivative_permitted analysis

Public Domain permits derivative works. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. `CC0-1.0` is relicensable into the `sig_graph` (CC-BY-4.0) compartment — no separate compartment needed.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Public Domain dedication declared by the publisher.**
