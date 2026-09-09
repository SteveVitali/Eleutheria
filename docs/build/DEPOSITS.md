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
