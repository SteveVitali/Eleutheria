# Rights-review packet — `deflock_repo` (DeFlock — canonical repo (FoggedLens/deflock))

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `deflock_repo`
- **Homepage:** https://github.com/FoggedLens/deflock
- **Terms URL(s):** https://github.com/FoggedLens/deflock/blob/main/LICENSE
- **robots.txt:** honor (GitHub); repo landing fetched, not cloned.

## Terms (verbatim)

> Fetched from https://github.com/FoggedLens/deflock on 2026-09-09 (repo landing,
> not content — permitted research): the repository files navigation shows a "README"
> and an "**MIT license**" badge, and the README states the map "Uses OpenStreetMap
> data to populate a map with crowdsourced locations of ALPRs". The LICENSE file is
> linked at the repo root (terms_url below). MIT license canonical text:
>
> "Permission is hereby granted, free of charge, to any person obtaining a copy of
> this software and associated documentation files (the \"Software\"), to deal in the
> Software without restriction, including without limitation the rights to use, copy,
> modify, merge, publish, distribute, sublicense, and/or sell copies of the Software
> ... THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND."
>
> NOTE: the DeFlock *device data* is contributed to OpenStreetMap and travels under
> ODbL-1.0 (SIG-LIC-009a silently-travelling share-alike), not MIT — MIT covers the
> DeFlock *code* only.

## SPDX candidate

`MIT`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

MIT code is redistributable with the copyright + permission notice retained. redistributable=true (SIG-LIC-003).  → registry `redistributable = true`.

## derivative_permitted analysis

Derivatives permitted under MIT. BUT the DeFlock device *data* travels under OSM's ODbL (SIG-LIC-009a) — MIT covers the code only.  → registry `derivative_permitted = true`.

## ODbL compartment implications

Device data is OSM-derived ⇒ ODbL compartment for the data path (RISK-P0-01/02). Code path is MIT.

## Custody posture recommendation

REFERENCE (code studied; device data reconciled via osm_overpass under ODbL).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `MIT`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**PARTIAL — code is clean MIT; the data path inherits the ODbL/HG-02 question.**
