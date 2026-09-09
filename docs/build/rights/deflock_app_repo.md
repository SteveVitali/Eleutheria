# Rights-review packet — `deflock_app_repo` (DeFlock — app repo (FoggedLens/deflock-app))

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `deflock_app_repo`
- **Homepage:** https://github.com/FoggedLens/deflock-app
- **Terms URL(s):** https://github.com/FoggedLens/deflock-app/blob/main/LICENSE
- **robots.txt:** honor (GitHub).

## Terms (verbatim)

> GNU Affero General Public License v3.0 canonical text (SPDX: AGPL-3.0), applied to
> this repository's LICENSE file (terms_url below; not fetched verbatim this pass):
>
> "This is free software: you are free to change and redistribute it ... if you modify
> the Program, your modified version must prominently offer all users interacting with
> it remotely through a computer network ... an opportunity to receive the Corresponding
> Source of your version."
>
> HAZARD (SIG-INGEST-048b): AGPL-3.0 code MUST NOT be linked into SIG's Apache-2.0
> codebase; its methods may be studied freely. derivative_permitted=false records the
> linking hazard (not a data restriction).

## SPDX candidate

`AGPL-3.0`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

AGPL-3.0 is redistributable under its copyleft terms. redistributable=true.  → registry `redistributable = true`.

## derivative_permitted analysis

derivative_permitted=false in the registry records the SIG-INGEST-048b LINKING hazard: AGPL code MUST NOT be linked into SIG's Apache-2.0 codebase. Methods may be studied; code may not be linked/derived-into SIG.  → registry `derivative_permitted = false`.

## ODbL compartment implications

Not OSM-derived. No ODbL implication; the hazard is the AGPL network-copyleft/linking rule.

## Custody posture recommendation

REFERENCE (study only; never link into SIG's build).

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `AGPL-3.0`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**YES — AGPL-3.0 linking/network-copyleft disposition (SIG-INGEST-048b).**
