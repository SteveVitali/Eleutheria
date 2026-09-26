<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# DEPOSITS — the SIG Zenodo deposit ledger (append-only, §38.2, SIG-EXPORT-002)

Each row is a dated deposit of a bulk-export release. **The `environment` column is
binding:** a `sandbox` DOI (`10.5072/…`) is a throwaway Zenodo *test* identifier minted
on `sandbox.zenodo.org`; it is **not** citable and is **not** the production concept DOI
(`10.5281/…`) — see RISK-P21-08. A `dry-run` row was produced offline by
`FakeZenodoTransport` (no network, no account) and pins the deposit *policy* only.

The first **production** deposit is a one-command operator action
(`sig-exports deposit` without `--sandbox`/`--dry-run`, with `SIG_ZENODO_SANDBOX_TOKEN`
swapped for a production token) that appends its row below.

| date | release_id | environment | concept_doi | version_doi | files |
|---|---|---|---|---|---|
| 2026-09-09 | sig-2026-08-20-95c7a19a | sandbox-dry-run | 10.5072/zenodo.181709756531953 | 10.5072/zenodo.145822404201517 | 17 |
| 2026-09-10 | sig-2026-08-20-95c7a19a | dry-run | 10.5281/zenodo.181709756531953 | 10.5281/zenodo.145822404201517 | 16 |
| 2026-09-15 | sig-2026-08-20-95c7a19a | sandbox | 10.5072/zenodo.603731 | 10.5072/zenodo.603732 | 16 |

## 2026-09-15 — real sandbox deposit published (HG-07, P21.5 re-run)

The operator supplied a correctly-scoped `sandbox.zenodo.org` personal access token
(`deposit:write`+`deposit:actions`; the first token had no scopes → HTTP 403). The
row above (`environment = sandbox`, DOIs under `10.5072/…`) is a **real** Zenodo
sandbox deposition published by `sig-exports deposit --sandbox` — still a *test*
identifier, **not** the production concept DOI (RISK-P21-08). Fixed a real live-API
bug this run: Zenodo's bucket file API 404s on object keys containing `/` (the
export's compartment paths), so deposited filenames are flattened `/`→`__`.
`D-P21.5-1`'s Zenodo half is DONE; object-store push + live egress + SWH save remain
gate-pending (HG-07).

## 2026-09-10 — INFRA.1 (GL-INFRA-01) re-run, prepare-only (append-only)

Re-verified on the current chain tip (`devin/p21-5-infra-rerun`, base
`devin/p23-6-go-public-marker`). **No real (production or sandbox) deposit was made** —
HG-07 credentials are still `provided: no` (P23.4 / ACCT.1, GATE DECISIONS 2026-09-10),
so `SIG_ZENODO_SANDBOX_TOKEN` is absent. The row above is the **offline deterministic
dry-run** (`FakeZenodoTransport`, no network) produced this re-run over a freshly-built
`okc` export; it pins the deposit *policy* only (`10.5281/…` = the default-transport
placeholder, **not** a citable identifier). Environment clock read 2026-09-13; chain date
for this entry = 2026-09-10.

Re-verified free/dry-run behaviour this run (see `runs/P21.5.md#2026-09-10-re-run`):
- `sig-exports deposit --dry-run` → exit 0, records a `dry-run`-marked DOI (above). ✅
- `sig-exports deposit --sandbox` **without** a token → **exit 4** `gate pending: HG-07 —
  SIG_ZENODO_SANDBOX_TOKEN not set … Wrote nothing.` ✅ (no fabricated real DOI).

**Still gate-pending HG-07 (`D-P21.5-1` OPEN):** the real `sandbox.zenodo.org` deposit
(mints a `10.5072/…` concept DOI), the object-store push, `egress-report` against a live
usage API, and the Software Heritage save — none run without the operator's credentials.
