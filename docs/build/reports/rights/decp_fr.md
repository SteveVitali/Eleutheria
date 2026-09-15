# Rights-review packet — `decp_fr` (Données essentielles de la commande publique — DECP)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.
> Authored by P24.6 (JURIS.2) as the second jurisdiction's rights artifact — the
> packet is the preparatory step; the flip is the HG-03 operator gate.

- **Source id:** `decp_fr`
- **Homepage:** https://www.data.gouv.fr/fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides/
- **Terms URL(s):** https://www.data.gouv.fr/fr/datasets/donnees-essentielles-de-la-commande-publique-fichiers-consolides/ (not fetched verbatim this pass — recorded for the reviewer)
- **robots.txt:** honor.

## Terms (verbatim)

> UNDETERMINED — no resolved rights block in the registry (SIG-LIC-004; fails the
> export gate closed). The DECP consolidated files on data.gouv.fr are published
> under the **Licence Ouverte 2.0** (Etalab) — the French government's open-data
> licence — but `Licence Ouverte` is **not an SPDX expression in
> `policy/data/licenses.toml`**, so the registry records nothing and this packet
> does not guess. The nearest accepted candidates for the reviewer are `ODbL-1.0`
> and `CC-BY-4.0`; the compatibility question (LO 2.0 ≈ CC-BY-4.0 per Etalab's own
> guidance) is a rights judgement for the reviewer/counsel, not this packet.

## SPDX candidate

`UNDETERMINED` — Licence Ouverte 2.0 is outside the accepted SPDX set; the
reviewer decides whether an accepted expression applies or the accepted set needs
an amendment (a `licenses.toml` data change + ADR, not a silent map).

## redistributable analysis

Not asserted (UNDETERMINED). If Licence Ouverte 2.0 maps onto an accepted
permissive expression: redistributable with attribution.  → registry stays unset.

## derivative_permitted analysis

Not asserted (UNDETERMINED). No SIG-INGEST-048b linking hazard identified at this
posture (REFERENCE, not re-hosted).

## ODbL compartment implications

Not OSM-derived. If the reviewer resolves LO 2.0 to ODbL-1.0 the rows join the
ODbL compartment (share-alike travels); under CC-BY-4.0 they would join the
graph. Until then the P24.6 export keeps DECP content **out** of the published
bundle (recorded as a gap — the gate exercised, not bypassed).

## Custody posture recommendation

REFERENCE (national open-data index; re-host only what the resolved licence
permits). France/Belgium path; `ingestion_permitted=false` by design until the
HG-03 review records a reviewer + date.

## Decision

- [ ] permit ingestion — reviewer: maintainer (delegated) date: 2026-09-15 — **rights RESOLVED, flip HELD**
- SPDX recorded: `LicenceOuverte-2.0` (confirmed `fr-lo` via the data.gouv.fr API 2026-09-15;
  added to the accepted SPDX set by ADR-084, `relicensable_to` self-only pending HG-02 on
  LO↔CC-BY compatibility). The source is **not flipped**: the France-cohort gate
  (P24.6/D-JURIS.2-1) holds it for the P25.5 review. rights_reviewed_by: maintainer (delegated)   rights_reviewed_on: 2026-09-15

## Counsel-needed flag

**YES — Licence Ouverte 2.0 disposition: the accepted SPDX set has no LO
expression; the reviewer/counsel decides the mapping (HG-02-adjacent).**
