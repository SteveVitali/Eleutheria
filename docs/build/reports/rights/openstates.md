# Rights-review packet — `openstates` (OpenStates v3 API)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `openstates`
- **Homepage:** https://v3.openstates.org/
- **Terms URL(s):** https://open.pluralpolicy.com/data/ — retrieved 2026-09-16.
- **robots.txt:** honor — v3.openstates.org is the documented API surface; API mode applies (api_allowlist.toml records the basis).

## Terms (verbatim)

> "Unless otherwise noted data is provided under a public domain dedication but
> attribution is greatly appreciated and very helpful."
> — https://open.pluralpolicy.com/data/, retrieved 2026-09-16.

## SPDX candidate

`CC0-1.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

The documented public-domain dedication resolves the data rights (GL-GATE-06).  → registry `redistributable = true`.

## derivative_permitted analysis

Public-domain dedication — derivatives permitted.  → registry `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

REFERENCE (bounded state-scoped bill queries over the documented v3 API; bills index as index_only evidence links — a pending bill is not a §11.14 LegalInstrument).

## Access note (2026-09-16, honest)

The v3 API is key-gated — the free registered key resolves from
`$SIG_OPENSTATES_KEY` at fetch time (HG-09; env only, never committed). Keyless
the API answers 403 — a recorded challenge, never defeated. Rights (public
domain) and access (key-gated API) are separate questions; the dedication
resolves the former, not the latter.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-16
- SPDX recorded: `CC0-1.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-16

## Counsel-needed flag

**NO — public-domain dedication quoted verbatim resolves the rights under GL-GATE-06.**
