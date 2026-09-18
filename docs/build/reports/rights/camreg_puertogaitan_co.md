# Rights-review packet — `camreg_puertogaitan_co` (Puerto Gaitán municipal CCTV registry)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1).

- **Source id:** `camreg_puertogaitan_co`
- **Homepage:** https://www.datos.gov.co/d/fvdt-ftkz
- **Terms URL(s) fetched:** https://www.datos.gov.co/api/views/fvdt-ftkz — retrieved 2026-09-18 (Socrata dataset metadata "MAPA DE CAMARAS (CCTV) DEL MUNICIPIO", publisher Alcaldía de Puerto Gaitán, Meta — Colombia national open-data portal; P26.13 catalog sweep, `docs/build/reports/catalog_sweep_2026-09-18_reviewed.json`).
- **robots.txt:** honor — `www.datos.gov.co/robots.txt` answers 200; `/resource/` is not among the disallowed paths and the policy sets `Crawl-delay: 1` — inside the pinned `api_allowlist.toml` rate. API MODE under the recorded allowlist entry.

## Terms (verbatim)

> The Socrata dataset's licence metadata declares **"Creative Commons
> Attribution | Share Alike 4.0 International"** verbatim, with terms link
> `http://creativecommons.org/licenses/by-sa/4.0/legalcode`.

## SPDX candidate

`CC-BY-SA-4.0`.

## redistributable analysis

CC-BY-SA-4.0 is an explicit redistributable licence with attribution + share-alike obligations — honoured by the compartment below. → `redistributable = true`.

## derivative_permitted analysis

CC-BY-SA-4.0 permits derivatives under share-alike. → `derivative_permitted = true`.

## ODbL compartment implications

Not OSM-derived and not ODbL — but share-alike is a hard boundary: `CC-BY-SA-4.0`
claims land in the existing `portal` compartment (the CC-BY-SA-4.0 bucket in
`policy/src/policy/data/licenses.toml`), never merged into the CC-BY `sig_graph`
compartment.

## Custody posture recommendation

MIRROR — registry rows only.

## Decision

- [x] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-18
- SPDX recorded: `CC-BY-SA-4.0`   rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-18

## Counsel-needed flag

**NO — explicit Creative Commons licence declared on the national portal's dataset metadata; share-alike honoured by compartment separation.**
