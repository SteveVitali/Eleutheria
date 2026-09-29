# Rights-review packet — `fema_hsgp_allocations` (FEMA Homeland Security Grant Program)

> Facts (the standing legal basis + retrieval date) are separated from judgement (the
> Decision line). This packet asserts no legal conclusion (§3.1). No source content was fetched
> in this run — the verbatim terms-page capture (SIG-LIC-002) is part of the deferred live half
> (D-R7.3-BREADTH); this packet records the review basis.

- **Source id:** `fema_hsgp_allocations`
- **Homepage:** https://www.fema.gov/grants/preparedness/homeland-security
- **Terms URL:** https://www.fema.gov/about/website-information/foia — retrieved 2026-09-23 (documented posture, not yet captured)
- **Class:** federal FUNDING (accountability/governance) — the FEMA Homeland Security Grant Program /
  Urban Area Security Initiative allocation tables record which agencies / urban areas receive federal
  grant funding that flows to fusion centers and Real-Time Crime Centers.

## Basis (the standing legal fact)

FEMA is a U.S. federal government agency; its allocation announcements are works of the United States
Government, not subject to copyright in the U.S. under **17 U.S.C. §105** (public domain).

## SPDX candidate

`CC0-1.0` — U.S.-federal public-domain work (per-source PD packet wins over the GL-GATE-07 US default).

## redistributable analysis

Separately reviewed (SIG-LIC-003): no copyright restriction; `redistributable = true`,
`derivative_permitted = true`.

## Funded ≠ deployed

A grant allocation is **funding** evidence only — the funding leg of the accountability chain
(deployment→vendor→contract→FUNDING→policy→oversight, P28.6). It is never a deployment, device count,
or operational-state claim; procured/funded ≠ deployed is enforced at the genre/predicate level.
Relationship-weighted: the recipient agency resolves onto an existing operator entity.

## Connector class

The `procurement` connector's federal-assistance/allocation path — distinct from the sub-award keyword
path `usaspending` owns. No bespoke adapter; wiring deferred (D-R7.3-BREADTH).

## Decision

Flip `ingestion_permitted = true` under **GL-GATE-07 / HG-03** (2026-09-23), reviewer
`maintainer (delegated)`, `CC0-1.0`. Live fetch + terms capture + dedup deferred (**D-R7.3-BREADTH**).
