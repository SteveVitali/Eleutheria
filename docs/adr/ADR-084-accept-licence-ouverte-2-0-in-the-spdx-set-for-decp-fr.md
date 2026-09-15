# ADR-084 — Accept `LicenceOuverte-2.0` in the SPDX set for DECP (France/Belgium open procurement)

- **Status:** Accepted
- **Phase / ticket:** operator determination (2026-09-15), the B rights-review pass; resolved by P25.5's France work
- **Date:** 2026-09-15
- **Related:** `decp_fr` rights packet (`docs/build/reports/rights/decp_fr.md`), `policy/data/licenses.toml`, SIG-LIC-001/003/004/009, P24.6/D-JURIS.2-1 (the France-cohort gate), HG-02 (counsel), ADR-083.

## Context

`decp_fr` (Données essentielles de la commande publique — the French national open
procurement dataset) was confirmed via the data.gouv.fr dataset API (2026-09-15) to be
published under `fr-lo` — **Licence Ouverte / Open Licence** (Etalab). The accepted
SPDX set in `policy/data/licenses.toml` had no Licence Ouverte expression, so the
source's rights were recorded UNDETERMINED — an accurate state, but it blocked any
disposition of the second jurisdiction's procurement path. The alternatives were:
silently map LO to `CC-BY-4.0` (Etalab's own guidance says LO 2.0 is CC-BY-compatible,
but a silent map erases the provenance of the actual licence — against the defining
standard), or leave the source UNDETERMINED until counsel (HG-02) rules.

## Decision (operator determination, 2026-09-15)

Add **`LicenceOuverte-2.0`** to the accepted licence set in `policy/data/licenses.toml`
as its own expression — `kind = "data"`, `attribution_required = true`,
`share_alike = false`, and `relicensable_to = ["LicenceOuverte-2.0"]` (deliberately
self-only). The source records the licence it is actually published under; whether LO
content may be *folded into* the CC-BY-4.0 export compartment (per Etalab's
compatibility guidance) is left to counsel rather than assumed. The `decp_fr` registry
row carries the resolved rights block; it is **not flipped** — the France-cohort gate
(P24.6/D-JURIS.2-1) still holds the flip for the P25.5 review.

## Consequences

- The DECP rights question is resolved honestly (real licence recorded, no silent
  mapping); export placement stays compartmented — LO content can only export under
  `LicenceOuverte-2.0` until counsel confirms a wider `relicensable_to`.
- Precedent for other data.gouv.fr sources (`raa_prefectures` confirmed `odc-odbl`
  separately; future `fr-lo`/`lov2` datasets use this expression).
- Counsel (HG-02) should confirm the LO↔CC-BY compatibility reading before LO content
  joins a published compartment.

## Revisit trigger

Revisit if: counsel (HG-02) confirms Licence Ouverte 2.0 is CC-BY-4.0-compatible —
then widen `relicensable_to`; **or** Etalab's published compatibility position
changes; **or** a data.gouv.fr source appears under a *different* LO version
(`fr-lo` v1 vs `lov2`) whose terms differ.
