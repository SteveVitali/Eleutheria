# AGENTS.md — `exports/` (licence-compartmented export bundles)

## Purpose

Builds versioned bulk-export releases from the claim spine (§38): licence-**compartmented** bundles,
PROV-O lineage, Frictionless data packages, dossiers, tiles, and (dry-run-by-default) Zenodo
deposits. The export **gate** is where licensing is computed and enforced — the ODbL/OSM compartment
is kept separate from the rest. Nearest-file-wins: this file adds to the root `AGENTS.md`.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `exports/src/exports/cli.py` | ~500 | `sig-exports` entry point (`build`, `provo`, `deposit`, …) |
| `exports/src/exports/bundle.py` | ~340 | assembles a versioned export bundle + manifest |
| `exports/src/exports/compartments.py` | ~270 | the licence-compartment split (ODbL kept separate) |
| `exports/src/exports/manifest.py` | ~210 | the export manifest / release metadata |
| `exports/src/exports/dossier.py` | ~390 | per-entity dossier rendering (feeds `web/`) |
| `exports/src/exports/provo.py` | ~300 | PROV-O lineage serialisation (§21.6) |
| `exports/src/exports/deposits.py` | ~70 | Zenodo deposit orchestration (dry-run default) |

## Build & Test

- CLI: `uv run python -m exports --help` / `sig-exports build <request.json> -o <dir>`
  (`provo`, `deposit`, `tiles`, … are sub-commands).
- Tests run under the top-level `make check`: `uv run pytest tests/exports`.

## Code Conventions

- Every export bundle carries a manifest and computed per-compartment licence; new formats are new
  serialisers under `exports/src/exports/`, additive to the manifest.

## Critical Gotchas

1. **Licence compartments must not be merged.** OSM-derived (ODbL) data ships in its **own**
   compartment (`compartments.py`, ADR-011/§42.3); an export that co-mingles it with Apache/other-
   licensed data is a licence breach. The export gate **fails closed** on unresolved rights
   (SIG-LIC-004) — don't relax it to make a bundle build.
2. **Deposits default to dry-run.** `deposit` performs a *dry-run* Zenodo deposit unless explicitly
   configured with credentials + a gate (HG-07); never hard-code a real token or force a live push.
3. **Exports read, never mutate.** The export path reads the spine and writes bundle files; it never
   writes back to `db/`.

## Terminology

- **Compartment** — a licence-scoped partition of the exported data.
- **Bundle / manifest** — a versioned export release and its machine-readable index.
- **PROV-O** — the W3C provenance ontology used for lineage documents.

## Do

- Compute licences through `compartments.py`; keep the ODbL compartment separate.
- Add a new export format as an additive serialiser with a manifest entry + `tests/exports` coverage.

## Don't

- Don't co-mingle licence compartments or bypass the fail-closed export gate.
- Don't turn a deposit dry-run into a live push without the HG-07 gate + env credentials.
