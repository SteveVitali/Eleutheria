# Rights-review packet — `gao_surveillance_reports` (U.S. Government Accountability Office)

> Facts (the standing legal basis + retrieval date) are separated from judgement (the
> Decision line). This packet asserts no legal conclusion (defining standard §3.1). No
> source *content* was fetched in this run — the verbatim terms-page capture (SIG-LIC-002)
> is part of the deferred live half (D-R7.3-BREADTH); this packet records the review basis.

- **Source id:** `gao_surveillance_reports`
- **Homepage:** https://www.gao.gov/
- **Terms URL:** https://www.gao.gov/about/reports-testimonies/copyright — retrieved 2026-09-23 (documented posture, not yet captured)
- **Class:** federal oversight (accountability/governance dimension) — GAO reports on facial
  recognition (e.g. GAO-21-518, GAO-23-105607), ALPR, and the DHS Homeland Security Grant Program.

## Basis (the standing legal fact)

GAO is a U.S. federal government agency; its reports are works of the United States Government.
Under **17 U.S.C. §105**, works prepared by an officer or employee of the U.S. Government as part
of that person's official duties are **not subject to copyright protection in the United States**
and are in the public domain. GAO's own copyright page documents that its material is generally in
the public domain (third-party material within a report may carry separate rights, which SIG does
not re-host — SIG stores derived facts + locators, never the expressive third-party inclusions).

## SPDX candidate

`CC0-1.0` — the registry-accepted expression of a U.S.-federal public-domain work
(`policy/data/licenses.toml`; the same basis as `usaspending`, `sam_gov`, `congress_gov`). Per the
P29.3 gate answer, a recorded per-source packet wins over the GL-GATE-07 US default
(`LicenseRef-PublicRecord-FactualCompilation`); the 17 U.S.C. §105 public-domain basis is the more
accurate expression here.

## redistributable analysis

Separately reviewed (never derived from the SPDX string, SIG-LIC-003): a public-domain federal work
carries no copyright restriction on reuse; `redistributable = true`, `derivative_permitted = true`.
Attribution to GAO is recorded on the source row as good practice, not a licence obligation.

## Procured / reviewed ≠ deployed

An oversight finding is an `AccountabilityEvent` (§11.17) — it is never a deployment, device count,
or operational-state claim. The connector allowlist enforces this.

## Decision

Flip `ingestion_permitted = true` under **GL-GATE-07 / HG-03** (LEDGER GATE DECISIONS 2026-09-23),
reviewer `maintainer (delegated)`, 2026-09-23, `CC0-1.0`. The live fetch + terms capture + dedup into
the resolved graph is deferred under the OSM-land contention (**D-R7.3-BREADTH**).
